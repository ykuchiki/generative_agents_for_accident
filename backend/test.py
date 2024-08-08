import openai
import os
import sys
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

# 環境変数からAPIキーを取得
openai_api_key = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーを設定
openai.api_key = openai_api_key

def ChatGPT_single_request(prompt):
    response = openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=30,
        )
    return response.choices[0].text

if __name__ == '__main__':
    prompt = "What is the weather like today?"
    response = ChatGPT_single_request(prompt)
    print(response)
