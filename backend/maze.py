import datetime
import json
import math
import os
import pickle
import time
import sys

import numpy as np

# 現在のファイルのディレクトリを基に絶対パスを計算してsys.pathに追加
current_file_path = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.join(current_file_path, '..')
sys.path.append(parent_directory)

from backend.global_methods import *
from backend.utils import *


class Maze:
    def __init__(self, maze_name=None):
        # root_path = os.getcwd()
        # print("root_path", root_path)

        # ---------------------------------------------------------------------------
        # [SECTION 1]
        # Map情報の読み取り
        meta_info = json.load(open(f'{env_matrix}/maze_meta_info.json'))
        # 元のコードではmaze_nameをコマンドライン引数で渡してる，必要に応じて変更
        self.maze_name = meta_info['world_name']
        # Map size(タイルの数)
        self.maze_width = int(meta_info['maze_width'])
        self.maze_height = int(meta_info['maze_height'])
        # 縦と横の1タイル分のピクセルサイズ，これにwidthやheightをかけた大きさが実際の大きさになる
        self.sq_tile_size = int(meta_info['sq_tile_size'])
        # シミュレーション上に特別な制約を与える時に使うらしい．用途は不明
        self.special_constraint = meta_info['special_constraint']
        # ---------------------------------------------------------------------------

        # ---------------------------------------------------------------------------
        # [SECTION 2]
        # ブロック情報の読み取り

        # ブロック情報のあるディレクトリ
        blocks_folder = f"{env_matrix}/special_blocks"
        # 最初の要素はTiledからエクスポートされたカラー・マーカー・ディジット
        # 次に，ブロックパス（ワールド，セクター，アリーナ，ゲームオブジェクト）が続く
        # これらのパスはReverieのインスタンス内で一意である必要がある
        #
        # world_blocks.csvの例:
        # 32134, the Ville
        _wb = blocks_folder + "/world_blocks.csv"
        wb_rows = read_file_to_list(_wb, header=False)
        wb = wb_rows[0][-1]  # World名が格納されてる

        # 以下ではキーに最初のカラー・マーカー・ディジット，バリューに最後の要素のペアの辞書型を作る
        # sector_blocks.csvの例：
        # 32135, the Ville, artist's co-living space
        _sb = blocks_folder + "/sector_blocks.csv"
        sb_rows = read_file_to_list(_sb, header=False)
        sb_dict = dict()
        for i in sb_rows: sb_dict[i[0]] = i[-1]  # そういえばこんな感じで一行にできるんだった

        # arena_blocks.csvの例：
        # 32148, the Ville, artist's co-living space, Latoya Williams's bathroom
        _ab = blocks_folder + "/arena_blocks.csv"
        _ab_rows = read_file_to_list(_ab, header=False)
        ab_dict = dict()
        for i in _ab_rows: ab_dict[i[0]] = i[-1]

        # game_object_blocks.csvの例:
        # 32227, the Ville, < all >, bed
        _gob = blocks_folder + "/game_object_blocks.csv"
        gob_rows = read_file_to_list(_gob, header=False)
        gob_dict = dict()
        for i in gob_rows: gob_dict[i[0]] = i[-1]

        # sppawning_location_blocks.csvの例：
        # 32285, the Ville, artist's co-living space, Latoya Williams's room, sp-A
        _slb = blocks_folder + "/spawning_location_blocks.csv"
        slb_rows = read_file_to_list(_slb, header=False)
        slb_dict = dict()
        for i in slb_rows: slb_dict[i[0]] = i[-1]
        # ---------------------------------------------------------------------------

        # ---------------------------------------------------------------------------
        # [SECTION 3]
        # 各タイルが有する情報を管理するためのコードブロック
        # 主な目的はシミュレーションの記録や管理のため

        # mazeフォルダーの読み込み
        maze_folder = f"{env_matrix}/maze"

        # 読み込んだ各CSVファイルのリストは幅×高さの長さを持つ一行のリストなので，あとで変換しないといけない
        # 各タイルが衝突可能か，0だったら可能
        _cm = maze_folder + "/collision_maze.csv"
        collision_maze_raw = read_file_to_list(_cm, header=False)[0]
        # 各タイルが属するセクター
        _sm = maze_folder + "/sector_maze.csv"
        sector_maze_raw = read_file_to_list(_sm, header=False)[0]
        # 各タイルが属するアリーナ
        _am = maze_folder + "/arena_maze.csv"
        arena_maze_raw = read_file_to_list(_am, header=False)[0]
        # 各タイルが存在するゲームオブジェクト
        _gom = maze_folder + "/game_object_maze.csv"
        game_object_maze_raw = read_file_to_list(_gom, header=False)[0]
        # 各タイルのスポーニングロケーション
        _slm = maze_folder + "/spawning_location_maze.csv"
        spawning_location_maze_raw = read_file_to_list(_slm, header=False)[0]

        # 一列の配列を二列に整形
        self.collision_maze = []
        sector_maze = []
        arena_maze = []
        game_object_maze = []
        spawning_location_maze = []
        for i in range(0, len(collision_maze_raw), self.maze_width):
            tw = self.maze_width
            self.collision_maze += [collision_maze_raw[i:i + tw]]
            sector_maze += [sector_maze_raw[i:i + tw]]
            arena_maze += [arena_maze_raw[i:i + tw]]
            game_object_maze += [game_object_maze_raw[i:i + tw]]
            spawning_location_maze += [spawning_location_maze_raw[i:i + tw]]

        # マップの各タイル（セル）の詳細情報を格納するために self.tiles という2次元配列を設定
        # 各タイルにはworld, sector, arena, game_object, spawning location, collision情報, およびそのタイルで発生してるevent
        # が辞書形式で保存されてる
        self.tiles = []
        for i in range(self.maze_height):
            row = []
            for j in range(self.maze_width):
                tile_details = dict()
                tile_details['world'] = wb

                tile_details["sector"] = ""
                if sector_maze[i][j] in sb_dict:
                    tile_details["sector"] = sb_dict[sector_maze[i][j]]

                tile_details["arena"] = ""
                if arena_maze[i][j] in ab_dict:
                    tile_details["arena"] = ab_dict[arena_maze[i][j]]

                tile_details["game_object"] = ""
                if game_object_maze[i][j] in gob_dict:
                    tile_details["game_object"] = gob_dict[game_object_maze[i][j]]

                tile_details["spawning_location"] = ""
                if spawning_location_maze[i][j] in slb_dict:
                    tile_details["spawning_location"] = slb_dict[spawning_location_maze[i][j]]

                # 各タイルが衝突可能かどうか
                tile_details["collision"] = False
                if self.collision_maze[i][j] != "0":
                    tile_details["collision"] = True

                tile_details["events"] = set()

                row += [tile_details]
            self.tiles += [row]

        # すべてのゲームオブジェクトがあるタイルに，デフォルトのイベントを設定する
        for i in range(self.maze_height):
            for j in range(self.maze_width):
                if self.tiles[i][j]["game_object"]:
                    object_name = ":".join([self.tiles[i][j]["world"],
                                            self.tiles[i][j]["sector"],
                                            self.tiles[i][j]["arena"],
                                            self.tiles[i][j]["game_object"]])
                    go_event = (object_name, None, None, None)
                    self.tiles[i][j]["events"].add(go_event)


        # 逆引きタイルアクセス
        # self.address_tiles辞書はキーに文字列のアドレス(sectorやarenaなど)，バリューにそれに属するタイルの座標セット
        # これによって特定のアドレスに対応するタイルの座標を効率的に検索できる
        # 例：self.address_tiles['double studio:recreation:pool table'] == {(29, 14), (31, 11), (30, 14), (32, 11), ...}
        self.address_tiles = dict()
        for i in range(self.maze_height):
            for j in range(self.maze_width):
                addresses = []
                if self.tiles[i][j]["sector"]:
                    add = f'{self.tiles[i][j]["world"]}:'
                    add += f'{self.tiles[i][j]["sector"]}'
                    addresses += [add]
                if self.tiles[i][j]["arena"]:
                    add = f'{self.tiles[i][j]["world"]}:'
                    add += f'{self.tiles[i][j]["sector"]}:'
                    add += f'{self.tiles[i][j]["arena"]}'
                    addresses += [add]
                if self.tiles[i][j]["game_object"]:
                    add = f'{self.tiles[i][j]["world"]}:'
                    add += f'{self.tiles[i][j]["sector"]}:'
                    add += f'{self.tiles[i][j]["arena"]}:'
                    add += f'{self.tiles[i][j]["game_object"]}'
                    addresses += [add]
                if self.tiles[i][j]["spawning_location"]:
                    add = f'<spawn_loc>{self.tiles[i][j]["spawning_location"]}'
                    addresses += [add]

                # addressesリスト内の各アドレスについて，そのアドレスに対応するセットにタイル座標を追加
                for add in addresses:
                    if add in self.address_tiles:
                        # jが列方向，すなわちx軸方向なので(j, i)になる
                        self.address_tiles[add].add((j, i))
                    else:
                        self.address_tiles[add] = set([(j, i)])
        # ---------------------------------------------------------------------------

    def turn_cordinate_to_tile(self, px_coordinate):
        """
        ピクセル座標をタイル座標に変換
        :param px_coordinate: ピクセル座標(x, y)
        :return: タイル座標(x, y)
        """
        # ピクセル座標をタイルサイズで割って計算
        x = math.ceil(px_coordinate[0] / self.sq_tile_size)
        y = math.ceil(px_coordinate[1] / self.sq_tile_size)
        return (x, y)

    def access_tile(self, tile):
        """
        指定されたタイル座標に対応するタイルの詳細情報を返す
        :param tile: タイル座標(x, y)
        :return: タイルの詳細情報を含む辞書
        """
        x = tile[0]
        y = tile[1]
        return self.tiles[y][x]

    def get_tile_path(self, tile, level):
        """
        タイルの座標からそのタイルの階層パス(アドレス)を取得
        :param tile: タイル座標(x, y)
        :param level: 取得する階層レベル('world', 'sector', 'arena', 'game_object'）
        :return: 階層パス(アドレス)を示す文字列
        """
        tile = self.access_tile(tile)

        path = f"{tile['world']}"
        if level == "world":
            return path
        else:
            path += f":{tile['sector']}"

        if level == "sector":
            return path
        else:
            path += f":{tile['arena']}"

        if level == "arena":
            return path
        else:
            path += f":{tile['game_object']}"

        return path

    def get_nearby_tiles(self, tile, vision_r):
        """
        指定されたタイル座標を中心とした視界半径内のタイルをリストとして返す
        :param tile: タイル座標(x, y)
        :param vision_r: 視界半径
        :return: 視界半径内のタイル座標のリスト
        """
        left_end = 0  # 左端の境界を計算する用
        if tile[0] - vision_r > left_end:
            left_end = tile[0] - vision_r  # 中心タイルから視野半径を引いた値が左端より大きければ更新

        right_end = self.maze_width - 1  # 右端の境界を計算する用
        if tile[0] + vision_r + 1 < right_end:
            right_end = tile[0] + vision_r + 1

        bottom_end = self.maze_height - 1  # 下端の境界を計算する用
        if tile[1] + vision_r + 1 < bottom_end:
            bottom_end = tile[1] + vision_r + 1

        top_end = 0  # 上端の境界を計算する用
        if tile[1] - vision_r > top_end:
            top_end = tile[1] - vision_r

        nearby_tiles = []
        for i in range(left_end, right_end):
            for j in range(top_end, bottom_end):  # 上端から下端まで
                nearby_tiles += [(i, j)]
        return nearby_tiles

    def add_event_from_tile(self, curr_event, tile):
        """
        指定されたタイルにイベントを追加
        :param curr_event: 追加するイベントのタプル
        :param tile: タイル座標(x, y)
        :return: なし
        """
        # s, p, o, desc = curr_event
        # if not p:
        #     p = "is"
        #     o = "idle"
        #     desc = "idle"
        # else:
        #     desc = f"{s.split(':')[-1]} {p} {o}" if desc is None else desc  # 既にある description を使用
        # curr_event = (s, p, o, desc)
        self.tiles[tile[1]][tile[0]]["events"].add(curr_event)
        # print("なんでやねん", tile[1], tile[0], self.tiles[tile[1]][tile[0]]["events"])


    def remove_event_from_tile(self, curr_event, tile):
        """
        指定されたタイルからイベントを削除
        :param curr_event: 削除するイベントのタプル
        :param tile: タイル座標(x, y)
        :return: なし
        """
        curr_tile_ev_cp = self.tiles[tile[1]][tile[0]]["events"].copy()
        for event in curr_tile_ev_cp:
            if event == curr_event:
                self.tiles[tile[1]][tile[0]]["events"].remove(curr_event)

    def turn_event_from_tile_idle(self, curr_event, tile):
        """
        指定されたイベントを「アイドル状態」にする
        :param curr_event: 変更するイベントのタプル
        :param tile: タイル座標(x, y)
        :return: なし
        """
        curr_tile_ev_cp = self.tiles[tile[1]][tile[0]]["events"].copy()
        for event in curr_tile_ev_cp:
            # イベントの最後の要素に "fire" が含まれていない場合のみアイドル状態にする
            if event == curr_event and "fire" not in event[-1]:
                self.tiles[tile[1]][tile[0]]["events"].remove(curr_event)
                new_event = (event[0], None, None, None)
                self.tiles[tile[1]][tile[0]]["events"].add(new_event)

    def remove_subject_events_from_tile(self, subject, tile):
        """
        指定されたタイルから特定のサブジェクトに関連するすべてのイベントを削除
        :param subject: サブジェクト名(例："Isabella Rodriguez")
        :param tile: タイル座標(x, y)
        :return: なし
        """
        curr_tile_ev_cp = self.tiles[tile[1]][tile[0]]["events"].copy()
        for event in curr_tile_ev_cp:
            if event[0] == subject:
                self.tiles[tile[1]][tile[0]]["events"].remove(event)

    def get_tile_by_object(self, object_name):
        """
        オブジェクト名に基づいて、そのオブジェクトが存在するタイルの座標を取得します。
        :param object_name: オブジェクト名の文字列（例："the Ville:Hobbs Cafe:cafe:cooking area"）
        :return: タイル座標のタプル（例：(10, 15)）
        """
        if object_name in self.address_tiles:
            return list(self.address_tiles[object_name])[0]
        else:
            return None

    def get_tiles_by_object_v2(self, object_name):
        """
        オブジェクト名に基づいて、そのオブジェクトが存在するすべてのタイルの座標を取得します。
        一つのオブジェクトが複数のタイルにまたがる場合があるためこのメソッドを実装

        :param object_name: オブジェクト名の文字列（例："the Ville:Hobbs Cafe:cafe:cooking area"）
        :return: タイル座標のリスト（例：[(10, 15), (10, 16)]）
        """
        if object_name in self.address_tiles:
            return list(self.address_tiles[object_name])
        else:
            return None

    def log_cafe_tile_info(self, step, file_path='log_cafe_tiles.txt'):
        """カフェ内のゲームオブジェクトのタイル情報をログとして出力"""
        cafe_area = "the Ville:Hobbs Cafe:cafe"
        tile_info = []

        for row in self.tiles:
            for tile in row:
                if tile and "world" in tile and "sector" in tile and "arena" in tile:
                    tile_address = f'{tile["world"]}:{tile["sector"]}:{tile["arena"]}'
                    if tile_address.startswith(cafe_area) and (tile["events"] or tile["game_object"]):
                        tile_info.append((tile["game_object"], tile["events"]))

        with open(file_path, 'a') as f:
            f.write(f"Step {step}:\n")
            if not tile_info:
                f.write("No events or game objects found in the cafe area.\n")
            for game_object, events in tile_info:
                f.write(f"Game Object: {game_object}\n")
                for event in events:
                    f.write(f"  Event: {event}\n")
            f.write("\n")

    def get_object_current_state(self, object_name):
        """
        指定されたオブジェクト名に基づいて、そのオブジェクトが存在するタイルの現在の状態を取得します。
        :param object_name: オブジェクト名の文字列（例："the Ville:Hobbs Cafe:cafe:cooking area"）
        :return: オブジェクトの現在の状態を示す文字列
        """
        tiles = self.get_tiles_by_object_v2(object_name)
        if not tiles:
            return None

        # オブジェクトが複数のタイルにまたがっている場合、最初のタイルの状態を使用します
        for tile in tiles:
            events = self.access_tile(tile)["events"]
            for event in events:
                if event[0] == object_name:
                    return event[2]  # event[2] が状態を示していると仮定します

        return None

    def save_tile_events(self, step, file_path='tile_events'):
        """説明が存在するイベントが存在するタイル情報を保存"""
        file_name = os.path.join(file_path, f"{step}_maze.txt")
        tile_data = []

        for y in range(self.maze_height):
            for x in range(self.maze_width):
                events = self.tiles[y][x]["events"]
                # 最後の引数（説明）が None でないイベントのみを保存
                meaningful_events = [event for event in events if event[-1] is not None]
                if meaningful_events:
                    event_strings = [f"({', '.join(map(str, event))})" for event in meaningful_events]
                    tile_info = f"{x} {y} {{{', '.join(event_strings)}}}"
                    tile_data.append(tile_info)

        if tile_data:
            with open(file_name, 'w') as f:
                f.write("\n".join(tile_data))


if __name__ == "__main__":
    maze = Maze()
    print(maze)
