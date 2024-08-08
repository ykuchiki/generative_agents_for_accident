import sys
import os
import math
import datetime
import random

# 現在のファイルのディレクトリを基に絶対パスを計算してsys.pathに追加
current_file_path = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.join(current_file_path, '..', '..')
sys.path.append(parent_directory)

from backend.global_methods import *

from backend.persona.memory_structures.spatial_memory import *
from backend.persona.memory_structures.associative_memory import *
from backend.persona.memory_structures.scratch import *

from backend.persona.cognitive_modules.perceive import *
from backend.persona.cognitive_modules.retrieve import *
from backend.persona.cognitive_modules.plan import *
from backend.persona.cognitive_modules.reflect import *
from backend.persona.cognitive_modules.execute import *
from backend.persona.cognitive_modules.converse import *


def log_debug_info(info, file_path='log.txt'):
    # with open(file_path, 'a') as f:
    #     f.write(info + '\n')
    pass

class Persona:
    def __init__(self, name, folder_mem_saved=False):
        # nameはペルソナ固有のもので，重複しない
        self.name = name

        # s_mem はペルソナの空間記憶
        f_s_mem_saved = f"{folder_mem_saved}/bootstrap_memory/spatial_memory.json"
        self.s_mem = MemoryTree(f_s_mem_saved)

        # a.mem はペルソナの長期記憶のコアである「連想記憶」
        f_a_mem_saved = f"{folder_mem_saved}/bootstrap_memory/associative_memory"
        self.a_mem = AssociativeMemory(f_a_mem_saved)

        # scratch はペルソナの短期記憶
        scratch_save = f"{folder_mem_saved}/bootstrap_memory/scratch.json"
        self.scratch = Scratch(scratch_save)

        self.accident_events = []  # アクシデントイベントを保持するリスト

    def save(self, save_folder):
        """ペルソナの現在の状態(記憶)を保存する"""
        # Spatial Memory(空間記憶)はJSON形式の木構造を有してる
        # e.g., {"double studio":
        #         {"double studio":
        #           {"bedroom 2":
        #             ["painting", "easel", "closet", "bed"]}}}
        f_s_mem = f"{save_folder}/spatial_memory.json"
        self.s_mem.save(f_s_mem)

        # Associative Memory(連想記憶)は以下のような形式でcsvとして保存される
        # [event.type, event.created, event.expiration, s, p, o]
        # e.g., event,2022-10-23 00:00:00,,Isabella Rodriguez,is,idle
        f_a_mem = f"{save_folder}/associative_memory"
        self.a_mem.save(f_a_mem)

        # ペルソナに関連する短期的なデータをJSON形式で保存する．
        # 読み込む時はPythonの変数として
        f_scratch = f"{save_folder}/scratch.json"
        self.scratch.save(f_scratch)

    def perceive(self, maze):
        return perceive(self, maze)

    def retrieve(self, perceived):
        return retrieve(self, perceived)

    def plan(self, maze, personas, new_day, retrieved):
        # log_debug_info(f"{self.name} retrieved for planning: {retrieved}")

        # アクシデントイベントが含まれているかを確認
        for key, value in retrieved.items():
            if "catches fire" in key:
                # 火事の場合の行動計画を決定
                log_debug_info(f"{self.name} detected a fire: {key}")
                # return "Evacuate the building due to fire"

        # 通常の行動計画
        # log_debug_info(f"{self.name} proceeding with regular planning")
        return plan(self, maze, personas, new_day, retrieved)

    def execute(self, maze, personas, plan):
        return execute(self, maze, personas, plan)

    def reflect(self):
        reflect(self)

    def move(self, maze, personas, curr_tile, curr_time):
        self.scratch.curr_tile = curr_tile

        # We figure out whether the persona started a new day, and if it is a new
        # day, whether it is the very first day of the simulation. This is
        # important because we set up the persona's long term plan at the start of
        # a new day.
        new_day = False
        if not self.scratch.curr_time:
            new_day = "First day"
        elif (self.scratch.curr_time.strftime('%A %B %d')
              != curr_time.strftime('%A %B %d')):
            new_day = "New day"
        self.scratch.curr_time = curr_time

        # Main cognitive sequence begins here.
        log_debug_info(f"{self.name} is perceiving the environment at tile {curr_tile}")
        perceived = self.perceive(maze)
        log_debug_info(f"{self.name} perceived: {perceived}")

        log_debug_info(f"{self.name} is retrieving memories based on perception")
        retrieved = self.retrieve(perceived)
        log_debug_info(f"{self.name} retrieved: {retrieved}")

        log_debug_info(f"{self.name} is planning actions")
        plan = self.plan(maze, personas, new_day, retrieved)
        log_debug_info(f"{self.name} plan: {plan}")

        # print("plan終わり！")
        self.reflect()
        # print("reflect終わり！")

        # <execution> is a triple set that contains the following components:
        # <next_tile> is a x,y coordinate. e.g., (58, 9)
        # <pronunciatio> is an emoji. e.g., "\ud83d\udca4"
        # <description> is a string description of the movement. e.g.,
        #   writing her next novel (editing her novel)
        #   @ double studio:double studio:common room:sofa
        return self.execute(maze, personas, plan)

    def open_convo_session(self, convo_mode):
        open_convo_session(self, convo_mode)