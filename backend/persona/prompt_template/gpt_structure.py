import json
import random
import openai
import os
import time
import sys

from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

current_file_path = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.join(current_file_path, '..', '..', '..')
sys.path.append(parent_directory)

from backend.utils import *

# 環境変数からAPIキーを取得
openai_api_key = os.getenv("OPENAI_API_KEY")

# OpenAI APIキーを設定
openai.api_key = openai_api_key

def temp_sleep(seconds=0.1):
    time.sleep(seconds)


def ChatGPT_single_request(prompt):
    temp_sleep()

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    return completion["choices"][0]["message"]["content"]

# ============================================================================
# #####################[SECTION 1: CHATGPT-3 STRUCTURE] ######################
# ============================================================================

def GPT4_request(prompt):
    """
    プロンプトとGPTパラメータの辞書を与えて，GPT-4の応答を得る
    """
    temp_sleep()

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion["choices"][0]["message"]["content"]

    except:
        print("ChatGPT ERROR")
        return "ChatGPT ERROR"


def ChatGPT_request(prompt):
    """
    プロンプトとGPTパラメータの辞書を与えて，GPT-3.5の-trubo応答を得る
    """
    # temp_sleep()
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion["choices"][0]["message"]["content"]

    except:
        print("ChatGPT ERROR")
        return "ChatGPT ERROR"


def GPT4_safe_generate_response(prompt,
                                example_output,
                                special_instruction,
                                repeat=3,
                                fail_safe_response="error",
                                func_validate=None,
                                func_clean_up=None,
                                verbose=False):
    """
    GPT-4を使って安全にレスポンスを生成する
    :param prompt: strのプロンプト
    :param example_output: str型の期待される出力の例
    :param special_instruction: str型の特別な指示
    :param repeat: int型のリクエストを繰り返す回数(デフォルトは3)
    :param fail_safe_response: str型の失敗した場合のレスポンス(デフォルトは"error")
    :param func_validate: バリデーション用の関数
    :param func_clean_up: クリーンアップ用の関数
    :param verbose: bool型の詳細出力を行うかどうか(デフォルトはFalse)
    :return: 有効な応答が得られた場合はその出力，得られなかった場合はFalse
    """
    prompt = 'GPT-3 Prompt:\n"""\n' + prompt + '\n"""\n'  # TODO ここのGPT-3が正しい確認
    prompt += f"Output the response to the prompt above in json. {special_instruction}\n"
    prompt += "Example output json:\n"
    prompt += '{"output": "' + str(example_output) + '"}'

    if verbose:
        print("CHAT GPT PROMPT")
        print(prompt)

    for i in range(repeat):

        try:
            curr_gpt_response = GPT4_request(prompt).strip()
            end_index = curr_gpt_response.rfind('}') + 1  # 出力された応答の最後の}の場所
            curr_gpt_response = curr_gpt_response[:end_index]  # 最後の}まで文字を切り出す
            curr_gpt_response = json.loads(curr_gpt_response)["output"]  # 上記で得られた文字列をJSON形式で読んでoutputキーの値を抽出

            # 生成された出力が有効かどうかを確認，有効であれば，その値を返す
            if func_validate(curr_gpt_response, prompt=prompt):
                return func_clean_up(curr_gpt_response, prompt=prompt)

            # verboseがTrueあら現在の繰り返し回数と生成された応答をprint
            if verbose:
                print("---- repeat count: \n", i, curr_gpt_response)
                print(curr_gpt_response)
                print("~~~~")

        except:
            pass

    return False

def ChatGPT_safe_generate_response(prompt,
                                   example_output,
                                   special_instruction,
                                   repeat=3,
                                   fail_safe_response="error",
                                   func_validate=None,
                                   func_clean_up=None,
                                   verbose=False):
    """
    GPT-3.5-turboを使って安全にレスポンスを生成する
    :param prompt: strのプロンプト
    :param example_output: str型の期待される出力の例
    :param special_instruction: str型の特別な指示
    :param repeat: int型のリクエストを繰り返す回数(デフォルトは3)
    :param fail_safe_response: str型の失敗した場合のレスポンス(デフォルトは"error")
    :param func_validate: バリデーション用の関数
    :param func_clean_up: クリーンアップ用の関数
    :param verbose: bool型の詳細出力を行うかどうか(デフォルトはFalse)
    :return: 有効な応答が得られた場合はその出力，得られなかった場合はFalse
    """
    # prompt = 'GPT-3 Prompt:\n"""\n' + prompt + '\n"""\n'
    prompt = '"""\n' + prompt + '\n"""\n'
    prompt += f"Output the response to the prompt above in json. {special_instruction}\n"
    prompt += "Example output json:\n"
    prompt += '{"output": "' + str(example_output) + '"}'

    if verbose:
        print("CHAT GPT PROMPT")
        print(prompt)

    for i in range(repeat):

        try:
            curr_gpt_response = ChatGPT_request(prompt).strip()
            end_index = curr_gpt_response.rfind('}') + 1
            curr_gpt_response = curr_gpt_response[:end_index]
            curr_gpt_response = json.loads(curr_gpt_response)["output"]

            # print ("---ashdfaf")
            # print (curr_gpt_response)
            # print ("000asdfhia")

            if func_validate(curr_gpt_response, prompt=prompt):
                return func_clean_up(curr_gpt_response, prompt=prompt)

            if verbose:
                print("---- repeat count: \n", i, curr_gpt_response)
                print(curr_gpt_response)
                print("~~~~")

        except:
            pass

    return False

def ChatGPT_safe_generate_response_OLD(prompt,
                                   repeat=3,
                                   fail_safe_response="error",
                                   func_validate=None,
                                   func_clean_up=None,
                                   verbose=False):
  if verbose:
    print ("CHAT GPT PROMPT")
    print (prompt)

  for i in range(repeat):
    try:
      curr_gpt_response = ChatGPT_request(prompt).strip()
      if func_validate(curr_gpt_response, prompt=prompt):
        return func_clean_up(curr_gpt_response, prompt=prompt)
      if verbose:
        print (f"---- repeat count: {i}")
        print (curr_gpt_response)
        print ("~~~~")

    except:
      pass
  print ("FAIL SAFE TRIGGERED")
  return fail_safe_response

# ============================================================================
# ###################[SECTION 2: ORIGINAL GPT-3 STRUCTURE] ###################
# ============================================================================
def GPT_request(prompt, gpt_parameter):
    """指定したパラメータでGPTの出力得る"""
    temp_sleep()
    try:
        response = openai.Completion.create(
            model=gpt_parameter["engine"],
            prompt=prompt,
            temperature=gpt_parameter["temperature"],
            max_tokens=gpt_parameter["max_tokens"],
            top_p=gpt_parameter["top_p"],
            frequency_penalty=gpt_parameter["frequency_penalty"],
            presence_penalty=gpt_parameter["presence_penalty"],
            stream=gpt_parameter["stream"],
            stop=gpt_parameter["stop"], )
        return response.choices[0].text
    except:
        print("TOKEN LIMIT EXCEEDED")
        return "TOKEN LIMIT EXCEEDED"

def generate_prompt(curr_input, prompt_lib_file):
    """
    指定された入力とプロンプトファイルを使用して，プロンプト文を作成する
    :param curr_input:  プロンプトに挿入する入力(str型かlist型)，リスト型なら複数の入力を指定できる
    :param prompt_lib_file: プロンプトファイルのパス
    :return: 生成されたプロンプト文
    """
    if type(curr_input) == type("string"):
        curr_input = [curr_input]  # strなら一旦リスト型に変換
    curr_input = [str(i) for i in curr_input]  # 文字列に変換，リストの中身が数値やboolであっても文字列に変わる

    f = open(prompt_lib_file, "r")
    prompt = f.read()
    f.close()
    for count, i in enumerate(curr_input):
        prompt = prompt.replace(f"!<INPUT {count}>!", i)  # タグの置き換え
    if "<commentblockmarker>###</commentblockmarker>" in prompt:  # コメントがある時，そこ以降を抽出
        prompt = prompt.split("<commentblockmarker>###</commentblockmarker>")[1]
    return prompt.strip()

def safe_generate_response(prompt,
                           gpt_parameter,
                           repeat=5,
                           fail_safe_response="error",
                           func_validate=None,
                           func_clean_up=None,
                           verbose=False):
  if verbose:
    print (prompt)

  for i in range(repeat):
    curr_gpt_response = GPT_request(prompt, gpt_parameter)
    if func_validate(curr_gpt_response, prompt=prompt):
      return func_clean_up(curr_gpt_response, prompt=prompt)
    if verbose:
      print ("---- repeat count: ", i, curr_gpt_response)
      print (curr_gpt_response)
      print ("~~~~")
  return fail_safe_response


def get_embedding(text, model="text-embedding-ada-002"):
  text = text.replace("\n", " ")
  if not text:
    text = "this is blank"
  return openai.Embedding.create(
          input=[text], model=model)['data'][0]['embedding']

if __name__ == '__main__':
  gpt_parameter = {"engine": "text-davinci-003", "max_tokens": 50,
                   "temperature": 0, "top_p": 1, "stream": False,
                   "frequency_penalty": 0, "presence_penalty": 0,
                   "stop": ['"']}
  curr_input = ["driving to a friend's house"]
  prompt_lib_file = "backend/persona/prompt_template/test_prompt_July5.txt"
  prompt = generate_prompt(curr_input, prompt_lib_file)

  def __func_validate(gpt_response):
    if len(gpt_response.strip()) <= 1:
      return False
    if len(gpt_response.strip().split(" ")) > 1:
      return False
    return True
  def __func_clean_up(gpt_response):
    cleaned_response = gpt_response.strip()
    return cleaned_response

  output = safe_generate_response(prompt,
                                 gpt_parameter,
                                 5,
                                 "rest",
                                 __func_validate,
                                 __func_clean_up,
                                 True)

  print (output)