import gradio as gr
import pandas as pd
import tempfile
import csv
from http import HTTPStatus
import dashscope
from dashscope import Generation
import os
from testAny import check_df_english, check_df_tags
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")  # Vincent's API key


# todo: delete instruction part or make it optional
def response(prompt, instruction=None):
    messages = [{'role': 'user', 'content': prompt}]
    if instruction is not None:  # 如果提供了指令，则添加到messages中
        messages.insert(0, {'role': 'system', 'content': instruction})

    response = Generation.call(model='qwen-plus',
                               messages=messages,
                               seed=1234,
                               result_format='message',
                               stream=False,
                               incremental_output=False,
                               temperature=1.8,
                               top_p=0.9,
                               top_k=999
                               )
    if response.status_code == HTTPStatus.OK:
        message = response.output.choices[0]['message']['content']
        return message
    else:
        print('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
            response.request_id, response.status_code,
            response.code, response.message
        ))
        return f"Error: Could not generate response with Status code: {response.status_code}, error code: {response.code}"


def format_full_prompt(df, introduction):
    # 为每个 row 创建 context
    df['context'] = df.apply(lambda row: f"{row['RAG1']}-{row['RAG2']}", axis=1)

    # 准备用于 format 的字典
    format_dict = df[['business_use_mark', 'context', 'question']].apply(lambda x: dict(zip(x.index, x)), axis=1)
    if len(introduction) >= 100:
        df['full_prompt'] = introduction
    # 使用 apply() 和 lambda 函数格式化 full_prompt 列
    df['full_prompt'] = df.apply(lambda row: row['full_prompt'].format(**format_dict[row.name]), axis=1)

    # 可选：删除临时创建的 context 列
    df.drop(columns=['context'], inplace=True)
    return df


def process_xlsx(xlsx_file, instruction=None):  # 这里也使instruction参数变成可选
    # 读取xlsx文件到pandas DataFrame
    df = pd.read_excel(xlsx_file)
    # 格式化prompts
    formatted_df = format_full_prompt(df, instruction)
    # 假设我们要处理的提示是DataFrame的'full_prompt'列
    # 调用response时，根据instruction是否为None自动处理
    formatted_df['Response'] = formatted_df['full_prompt'].apply(lambda prompt: response(prompt, instruction))

    # 使用tempfile创建一个临时文件路径保存处理后的xlsx
    tmp_path = tempfile.NamedTemporaryFile(delete=True, suffix='.xlsx').name
    formatted_df.to_excel(tmp_path, index=False, engine='openpyxl')

    return formatted_df, tmp_path


def main():
    with gr.Blocks() as demo:
        gr.Markdown("### 大模型xlsx处理工具")
        with gr.Accordion("输入说明"):
            gr.Markdown("请上传一个xlsx文件，文件应包含prompts。")
            system_instruction = gr.Textbox(label="System Instruction", lines=2,
                                            value=" ")

        file_input = gr.File(label="上传xlsx文件")
        submit_button = gr.Button("处理xlsx")

        output_table = gr.Dataframe(label="处理后的数据")
        output_file = gr.File(label="下载处理后的文件")
        clear_data = gr.ClearButton(components=[output_table, output_file], value="Clear processed data")
        clear_all = gr.ClearButton(components=[file_input, output_table, output_file], value="Clear console")
        check_tags_button = gr.Button("检查xlsx文件-tags")
        check_english_button = gr.Button("检查xlsx文件-英文")
        def update_output(xlsx_file, instruction):
            if xlsx_file is not None:
                formatted_df, tmp_path = process_xlsx(xlsx_file, instruction)
                return formatted_df, tmp_path  # 返回DataFrame和文件路径

        submit_button.click(fn=update_output, inputs=[file_input, system_instruction],
                            outputs=[output_table, output_file])
        check_tags_button.click(fn=check_df_tags, inputs=[output_table], outputs=[output_table])

    demo.launch()


if __name__ == "__main__":
    main()

