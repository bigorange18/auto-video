# -*- encoding: utf-8 -*-
'''
@File    :   test.py
@Time    :   2026/08/09 20:04:58
@Author  :   orange 
@Version :   1.0
@Contact :   chenorange2219@gmail.com
'''




import gradio as gr


def main():
    gr.Interface(
        fn=lambda x: x,
        inputs=gr.Textbox(label="Input Text"),
        outputs=gr.Textbox(label="Output Text"),
        title="Simple Gradio Interface",
        description="This is a simple Gradio interface that echoes the input text.",
    ).launch()


if __name__ == "__main__":
    main()
