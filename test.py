import unittest
import json
import os
from unittest.mock import patch
from dotenv import load_dotenv
import requests

# .envファイルをロード
load_dotenv()

# 環境変数からAPIキーを取得
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def translate_text(target: str, text: str) -> str:
    """指定された言語にテキストを翻訳します。

    Args:
        target (str): 翻訳先の言語（ISO 639-1形式）
        text (str): 翻訳するテキスト

    Returns:
        str: 翻訳されたテキスト
    """
    url = "https://translation.googleapis.com/language/translate/v2"
    params = {
        "q": text,
        "target": target,
        "key": GOOGLE_API_KEY
    }
    response = requests.get(url, params=params)

    # HTTPリクエストが成功したか確認
    if response.status_code != 200:
        raise Exception(f"Translation API error: {response.text}")

    # レスポンスをJSONとして解析
    result = response.json()

    # 'data'キーが存在するか確認
    if 'data' not in result:
        raise KeyError("'data' key not found in the response.")

    return result['data']['translations'][0]['translatedText']

def translate_master_movement(sim_code: str):
    """指定されたシミュレーションコードのmaster_movement.jsonファイルを翻訳します。

    Args:
        sim_code (str): シミュレーションコード
    """
    # ファイルパスを設定
    move_file = f"frontend/compressed_storage/{sim_code}/master_movement.json"

    # JSONファイルを読み込む
    with open(move_file, 'r', encoding='utf-8') as f:
        movements = json.load(f)

    # 各ステップの各ペルソナのデータを翻訳
    for step, personas in movements.items():
        for persona, details in personas.items():
            translated_persona = translate_text("ja", persona)
            translated_description = translate_text("ja", details.get("description", ""))
            details["description"] = translated_description
            if "chat" in details and details["chat"]:
                for chat in details["chat"]:
                    chat[0] = translate_text("ja", chat[0])  # 発言者の名前を翻訳
                    chat[1] = translate_text("ja", chat[1])  # 発言内容を翻訳

    # 翻訳されたデータを新しいJSONファイルに保存
    translated_file = f"frontend/compressed_storage/{sim_code}/master_movement_translated.json"
    with open(translated_file, 'w', encoding='utf-8') as f:
        json.dump(movements, f, ensure_ascii=False, indent=2)


class TestTranslation(unittest.TestCase):

    @patch('requests.get')
    def test_translate_master_movement(self, mock_get):
        # モックの返り値を設定
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'data': {
                'translations': [{'translatedText': 'こんにちは'}]
            }
        }

        # ダミーデータを用意
        mock_data = {
            "0": {
                "Klaus Mueller": {
                    "movement": [127, 50],
                    "pronunciatio": "\ud83d\udcac",
                    "description": "Klaus is working on a paper",
                    "chat": [
                        ["Maria Lopez", "Hey Klaus, how's the paper going?"]
                    ]
                }
            }
        }

        # ダミーのファイルパス
        test_sim_code = "test_simulation"
        test_file_path = f"frontend/compressed_storage/{test_sim_code}/master_movement.json"
        translated_file_path = f"frontend/compressed_storage/{test_sim_code}/master_movement_translated.json"

        # 必要なディレクトリを作成
        os.makedirs(os.path.dirname(test_file_path), exist_ok=True)

        # ダミーデータをファイルに保存
        with open(test_file_path, 'w', encoding='utf-8', errors='backslashreplace') as f:
            json.dump(mock_data, f, ensure_ascii=False, indent=2)

        # テスト関数を実行
        translate_master_movement(test_sim_code)

        # 翻訳されたファイルを読み込んで確認
        with open(translated_file_path, 'r', encoding='utf-8') as f:
            translated_data = json.load(f)

        # アサーションで翻訳結果を確認
        self.assertEqual(translated_data["0"]["Klaus Mueller"]["description"], "こんにちは")
        self.assertEqual(translated_data["0"]["Klaus Mueller"]["chat"][0][1], "こんにちは")

        # 作成したファイルとディレクトリを削除
        os.remove(test_file_path)
        os.remove(translated_file_path)
        os.rmdir(os.path.dirname(test_file_path))

if __name__ == '__main__':
    unittest.main()
