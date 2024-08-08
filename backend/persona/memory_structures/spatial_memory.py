import json
import os
import sys

# 現在のファイルのディレクトリを基に絶対パスを計算してsys.pathに追加
current_file_path = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.join(current_file_path, '..', '..', '..')
sys.path.append(parent_directory)

from backend.global_methods import *
from backend.utils import *

class MemoryTree:
    """
    エージェントがゲーム内の空間をどのように認識し，記憶し，アクセスするかを管理する
    """
    def __init__(self, f_saved):
        self.tree = {}
        if check_if_file_exists(f_saved):
            self.tree = json.load(open(f_saved))

    def print_tree(self):
        """
        ツリー全体を表示する
        """
        def _print_tree(tree, depth):
            """
            回帰的にツリー全体を表示する
            """
            dash = " >" * depth  # 深さに応じてインデント
            if type(tree) == type(list()):
                if tree:
                    print(dash, tree)
                return

            for key, val in tree.items():
                if key:
                    print(dash, key)
                _print_tree(val, depth + 1)

        _print_tree(self.tree, 0)

    def save(self, our_json):
        with open(our_json, 'w') as f:
            json.dump(self.tree, f)

    def get_str_accessible_sectors(self, curr_world):
        """
        現在のワールドでアクセス可能なセクターのリストを返す
        :param curr_world: 指定されたワールド
        :return: アクセス可能セクターのリスト
        """
        x = ", ".join(list(self.tree[curr_world].keys()))
        return x

    def get_str_accessible_sector_arenas(self, sector):
        """
        指定されたセクター内のアクセス可能なアリーナのリストを返す
        :param sector: 指定されたセクター
        :return: アクセス可能なアリーナのリスト
        """
        curr_world, curr_sector = sector.split(":")
        if not curr_sector:
            return ""
        x = ", ".join(list(self.tree[curr_world][curr_sector].keys()))
        return x

    def get_str_accessible_arena_game_objects(self, arena):
        """
        指定されたアリーナ内でアクセス可能なゲームオブジェクトのリストを返す
        :param arena: 指定されたアリーナ
        :return: アクセス可能なゲームオブジェクトのリスト
        """
        curr_world, curr_sector, curr_arena = arena.split(":")
        if not curr_arena:
            return ""

        try:
            x = ", ".join(list(self.tree[curr_world][curr_sector][curr_arena]))
        except:
            if curr_arena == "cooking area" or curr_arena == "behind the cafe counter":
                curr_arena = "cafe"
            x = ", ".join(list(self.tree[curr_world][curr_sector][curr_arena.lower()]))  # 大文字と小文字の違いによるエラー回避
        return x


if __name__ == '__main__':
  x = f"frontend/storage/the_ville_base_LinFamily/personas/Eddy Lin/bootstrap_memory/spatial_memory.json"
  x = MemoryTree(x)
  x.print_tree()

  print (x.get_str_accessible_sector_arenas("dolores double studio:double studio"))