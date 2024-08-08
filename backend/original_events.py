import datetime
import time
import os
import sys
import csv

# 現在のファイルのディレクトリを基に絶対パスを計算してsys.pathに追加
current_file_path = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.join(current_file_path, '..', '..', '..')
sys.path.append(parent_directory)

from backend.maze import *

def detect_and_add_accidents_to_tiles(persona, maze):
    """
    アクシデントを検出し、対応するタイルに追加する
    :param persona: 現在のペルソナを表すインスタンス
    :param maze: ペルソナの存在するマップ情報を取得するクラス
    """
    accident_events = detect_accidents(persona, maze)

    for accident_event in accident_events:
        # アクシデントイベントをタイルに追加
        coordinates = accident_event[2]  # アクシデントが発生した座標
        maze.add_event_to_tile(coordinates, accident_event)

def detect_accidents(persona, maze):
    """
    アクシデントを検出するメソッド
    :param persona: 現在のペルソナを表すインスタンス
    :param maze: ペルソナの存在するマップ情報を取得するクラス
    :return: 検出されたアクシデントイベントのリスト
    """
    accident_events = []
    nearby_tiles = maze.get_nearby_tiles(persona.scratch.curr_tile, persona.scratch.vision_r)

    for tile in nearby_tiles:
        tile_details = maze.access_tile(tile)
        if some_accident_condition(tile_details):  # アクシデントを検出するための条件
            accident_event = ("accident", "occurred", tile, "An accident occurred")  # アクシデントイベントの詳細
            accident_events.append(accident_event)

    return accident_events


def some_accident_condition(tile_details):
    return True
