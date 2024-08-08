import json
import numpy
import datetime
import pickle
import time
import math
import os
import shutil
import sys
import traceback
import requests

from selenium import webdriver
from django.conf import settings
from django.http import JsonResponse

# 現在のファイルのディレクトリを基に絶対パスを計算してsys.pathに追加
current_file_path = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.join(current_file_path, '..')
sys.path.append(parent_directory)

from compress_sim_storage import *
from backend.global_methods import *
from backend.utils import *
from backend.maze import *
from backend.persona.persona import *

# 追加用
from backend.original_events import *

from dotenv import load_dotenv

# # .envファイルの読み込み
# load_dotenv()
# # 環境変数からAPIキーを取得
# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


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



def log_persona_info(persona, file_path='log.txt'):
    """ペルソナの持つ情報をログとして出力"""
    # オブジェクトの全ての属性とその値を取得
    persona_attributes = vars(persona)

    def get_nested_attributes(obj, indent=0):
        """ネストされたオブジェクトの属性を取得"""
        result = ""
        nested_attributes = vars(obj)
        indent_space = "  " * indent
        for nested_attr, nested_value in nested_attributes.items():
            if hasattr(nested_value, '__dict__'):
                result += f"{indent_space}{nested_attr}:\n"
                result += get_nested_attributes(nested_value, indent + 1)
            else:
                result += f"{indent_space}{nested_attr}: {nested_value}\n"
        return result

    def get_concept_node_details(node):
        """ConceptNodeオブジェクトの詳細を取得"""
        return (f"ConceptNode(node_id={node.node_id}, "
                f"embedding_key={node.embedding_key}, "
                f"created={node.created}, "
                f"last_accessed={node.last_accessed})")

    # ファイルに書き込み
    with open(file_path, 'w') as f:
        for attr, value in persona_attributes.items():
            if hasattr(value, '__dict__'):
                f.write(f"{attr}:\n")
                f.write(get_nested_attributes(value, 1))
            else:
                f.write(f"{attr}: {value}\n")

        # 特定の属性の詳細情報も書き込み
        if hasattr(persona, 'a_mem'):
            f.write("\na_mem details:\n")
            f.write(get_nested_attributes(persona.a_mem, 1))
            # ConceptNodeオブジェクトの詳細情報
            f.write("ConceptNode details:\n")
            for node in persona.a_mem.seq_event + persona.a_mem.seq_thought + persona.a_mem.seq_chat:
                f.write(f"  {get_concept_node_details(node)}\n")

        if hasattr(persona, 's_mem'):
            f.write("\ns_mem details:\n")
            f.write(get_nested_attributes(persona.s_mem, 1))

        if hasattr(persona, 'scratch'):
            f.write("\nscratch details:\n")
            f.write(get_nested_attributes(persona.scratch, 1))


def log_debug_info(info, file_path='log.txt'):
     # with open(file_path, 'a') as f:
     #     f.write(info + '\n')
    pass


##############################################################################
#                                  REVERIE                                   #
##############################################################################

class ReverieServer:
    def __init__(self,
                 fork_sim_code,
                 sim_code):
        # FORKING FROM A PRIOR SIMULATION:
        # <fork_sim_code> indicates the simulation we are forking from.
        # Interestingly, all simulations must be forked from some initial
        # simulation, where the first simulation is "hand-crafted".
        self.fork_sim_code = fork_sim_code
        fork_folder = f"{fs_storage}/{self.fork_sim_code}"


        # log.txtを初期化
        with open('log.txt', 'w') as log_file:
            log_file.write('')

        # <sim_code> indicates our current simulation. The first step here is to
        # copy everything that's in <fork_sim_code>, but edit its
        # reverie/meta/json's fork variable.
        self.sim_code = sim_code
        sim_folder = f"{fs_storage}/{self.sim_code}"
        copyanything(fork_folder, sim_folder)
        # ディレクトリが存在しない場合は作成
        if not os.path.exists(sim_folder):
            os.makedirs(f"{sim_folder}/movement")

        with open(f"{sim_folder}/reverie/meta.json") as json_file:
            reverie_meta = json.load(json_file)

        with open(f"{sim_folder}/reverie/meta.json", "w") as outfile:
            reverie_meta["fork_sim_code"] = fork_sim_code
            outfile.write(json.dumps(reverie_meta, indent=2))

        # LOADING REVERIE'S GLOBAL VARIABLES
        # The start datetime of the Reverie:
        # <start_datetime> is the datetime instance for the start datetime of
        # the Reverie instance. Once it is set, this is not really meant to
        # change. It takes a string date in the following example form:
        # "June 25, 2022"
        # e.g., ...strptime(June 25, 2022, "%B %d, %Y")
        self.start_time = datetime.datetime.strptime(
            f"{reverie_meta['start_date']}, 13:00:00",  # スタートタイムはここで変更
            "%B %d, %Y, %H:%M:%S")
        # <curr_time> is the datetime instance that indicates the game's current
        # time. This gets incremented by <sec_per_step> amount everytime the world
        # progresses (that is, everytime curr_env_file is recieved).
        self.curr_time = datetime.datetime.strptime(reverie_meta['curr_time'],
                                                    "%B %d, %Y, %H:%M:%S")
        # <sec_per_step> denotes the number of seconds in game time that each
        # step moves foward.
        self.sec_per_step = reverie_meta['sec_per_step']

        # <maze> is the main Maze instance. Note that we pass in the maze_name
        # (e.g., "double_studio") to instantiate Maze.
        # e.g., Maze("double_studio")
        self.maze = Maze(reverie_meta['maze_name'])

        # <step> denotes the number of steps that our game has taken. A step here
        # literally translates to the number of moves our personas made in terms
        # of the number of tiles.
        self.step = reverie_meta['step']

        # SETTING UP PERSONAS IN REVERIE
        # <personas> is a dictionary that takes the persona's full name as its
        # keys, and the actual persona instance as its values.
        # This dictionary is meant to keep track of all personas who are part of
        # the Reverie instance.
        # e.g., ["Isabella Rodriguez"] = Persona("Isabella Rodriguezs")
        self.personas = dict()
        # <personas_tile> is a dictionary that contains the tile location of
        # the personas (!-> NOT px tile, but the actual tile coordinate).
        # The tile take the form of a set, (row, col).
        # e.g., ["Isabella Rodriguez"] = (58, 39)
        self.personas_tile = dict()

        # # <persona_convo_match> is a dictionary that describes which of the two
        # # personas are talking to each other. It takes a key of a persona's full
        # # name, and value of another persona's full name who is talking to the
        # # original persona.
        # # e.g., dict["Isabella Rodriguez"] = ["Maria Lopez"]
        # self.persona_convo_match = dict()
        # # <persona_convo> contains the actual content of the conversations. It
        # # takes as keys, a pair of persona names, and val of a string convo.
        # # Note that the key pairs are *ordered alphabetically*.
        # # e.g., dict[("Adam Abraham", "Zane Xu")] = "Adam: baba \n Zane:..."
        # self.persona_convo = dict()

        # 追加
        # スケジュールされたイベント
        # self.scheduled_events = []
        # add_kitchen_fire_event(self, "Isabella Rodriguez", 600)

        # Loading in all personas.
        init_env_file = f"{sim_folder}/environment/{str(self.step)}.json"
        init_env = json.load(open(init_env_file))
        for persona_name in reverie_meta['persona_names']:
            persona_folder = f"{sim_folder}/personas/{persona_name}"
            p_x = init_env[persona_name]["x"]
            p_y = init_env[persona_name]["y"]
            curr_persona = Persona(persona_name, persona_folder)

            self.personas[persona_name] = curr_persona
            self.personas_tile[persona_name] = (p_x, p_y)
            self.maze.tiles[p_y][p_x]["events"].add(curr_persona.scratch
                                                    .get_curr_event_and_desc())

        # REVERIE SETTINGS PARAMETERS:
        # <server_sleep> denotes the amount of time that our while loop rests each
        # cycle; this is to not kill our machine.
        self.server_sleep = 0.1

        # SIGNALING THE FRONTEND SERVER:
        # curr_sim_code.json contains the current simulation code, and
        # curr_step.json contains the current step of the simulation. These are
        # used to communicate the code and step information to the frontend.
        # Note that step file is removed as soon as the frontend opens up the
        # simulation.
        curr_sim_code = dict()
        curr_sim_code["sim_code"] = self.sim_code
        with open(f"{fs_temp_storage}/curr_sim_code.json", "w") as outfile:
            outfile.write(json.dumps(curr_sim_code, indent=2))

        curr_step = dict()
        curr_step["step"] = self.step
        with open(f"{fs_temp_storage}/curr_step.json", "w") as outfile:
            outfile.write(json.dumps(curr_step, indent=2))

        # アクシデントイベントをスケジュールする
        self.scheduled_events = []
        self.accident_flag = True
        # 「Hobbs Cafe」の「cooking area」で火事をスケジュール
        # behind the cafe counterで火事起こしたり
        # TODO ブラウザじゃなくて直接実行するときはコメントを外すこと!
        # self.schedule_accident_event("the Ville:Hobbs Cafe:cafe:cooking area", 600, "on fire")

    def save(self):
        """
        Save all Reverie progress -- this includes Reverie's global state as well
        as all the personas.

        INPUT
          None
        OUTPUT
          None
          * Saves all relevant data to the designated memory directory
        """
        # <sim_folder> points to the current simulation folder.
        sim_folder = f"{fs_storage}/{self.sim_code}"

        # Save Reverie meta information.
        reverie_meta = dict()
        reverie_meta["fork_sim_code"] = self.fork_sim_code
        reverie_meta["start_date"] = self.start_time.strftime("%B %d, %Y")
        reverie_meta["curr_time"] = self.curr_time.strftime("%B %d, %Y, %H:%M:%S")
        reverie_meta["sec_per_step"] = self.sec_per_step
        reverie_meta["maze_name"] = self.maze.maze_name
        reverie_meta["persona_names"] = list(self.personas.keys())
        reverie_meta["step"] = self.step
        reverie_meta_f = f"{sim_folder}/reverie/meta.json"
        with open(reverie_meta_f, "w") as outfile:
            outfile.write(json.dumps(reverie_meta, indent=2))

        # Save the personas.
        for persona_name, persona in self.personas.items():
            save_folder = f"{sim_folder}/personas/{persona_name}/bootstrap_memory"
            persona.save(save_folder)

    def start_path_tester_server(self):
        """
        Starts the path tester server. This is for generating the spatial memory
        that we need for bootstrapping a persona's state.

        To use this, you need to open server and enter the path tester mode, and
        open the front-end side of the browser.

        INPUT
          None
        OUTPUT
          None
          * Saves the spatial memory of the test agent to the path_tester_env.json
            of the temp storage.
        """

        def print_tree(tree):
            def _print_tree(tree, depth):
                dash = " >" * depth

                if type(tree) == type(list()):
                    if tree:
                        print(dash, tree)
                    return

                for key, val in tree.items():
                    if key:
                        print(dash, key)
                    _print_tree(val, depth + 1)

            _print_tree(tree, 0)

        # <curr_vision> is the vision radius of the test agent. Recommend 8 as
        # our default.
        curr_vision = 8
        # <s_mem> is our test spatial memory.
        s_mem = dict()

        # The main while loop for the test agent.
        while (True):
            try:
                curr_dict = {}
                tester_file = fs_temp_storage + "/path_tester_env.json"
                if check_if_file_exists(tester_file):
                    with open(tester_file) as json_file:
                        curr_dict = json.load(json_file)
                        os.remove(tester_file)

                    # Current camera location
                    curr_sts = self.maze.sq_tile_size
                    curr_camera = (int(math.ceil(curr_dict["x"] / curr_sts)),
                                   int(math.ceil(curr_dict["y"] / curr_sts)) + 1)
                    curr_tile_det = self.maze.access_tile(curr_camera)

                    # Initiating the s_mem
                    world = curr_tile_det["world"]
                    if curr_tile_det["world"] not in s_mem:
                        s_mem[world] = dict()

                    # Iterating throughn the nearby tiles.
                    nearby_tiles = self.maze.get_nearby_tiles(curr_camera, curr_vision)
                    for i in nearby_tiles:
                        i_det = self.maze.access_tile(i)
                        if (curr_tile_det["sector"] == i_det["sector"]
                                and curr_tile_det["arena"] == i_det["arena"]):
                            if i_det["sector"] != "":
                                if i_det["sector"] not in s_mem[world]:
                                    s_mem[world][i_det["sector"]] = dict()
                            if i_det["arena"] != "":
                                if i_det["arena"] not in s_mem[world][i_det["sector"]]:
                                    s_mem[world][i_det["sector"]][i_det["arena"]] = list()
                            if i_det["game_object"] != "":
                                if (i_det["game_object"]
                                        not in s_mem[world][i_det["sector"]][i_det["arena"]]):
                                    s_mem[world][i_det["sector"]][i_det["arena"]] += [
                                        i_det["game_object"]]

                # Incrementally outputting the s_mem and saving the json file.
                print("= " * 15)
                out_file = fs_temp_storage + "/path_tester_out.json"
                with open(out_file, "w") as outfile:
                    outfile.write(json.dumps(s_mem, indent=2))
                print_tree(s_mem)

            except:
                pass

            time.sleep(self.server_sleep * 10)

    def schedule_accident_event(self, object_name, time_in_seconds, description):
        """
        指定されたオブジェクトでアクシデントイベントをスケジュールします。
        :param object_name: アクシデントが発生するオブジェクトの名前
        :param time_in_seconds: シミュレーション開始からの秒数
        :param description: アクシデントの説明
        """
        accident_time = self.start_time + datetime.timedelta(seconds=time_in_seconds)
        self.scheduled_events.append({
            "type": "accident",
            "time": accident_time,
            "details": {
                "object": object_name,
                "description": description
            }
        })
        log_debug_info(f"Scheduled event for {object_name} at {accident_time} with description: {description}")

    def handle_scheduled_events(self):
        """
        スケジュールされたイベントを確認し、現在の時間と一致する場合に発生させます。
        """
        log_debug_info(f"Current simulation time: {self.curr_time}")
        for event in self.scheduled_events:
            log_debug_info(f"Current time {self.curr_time} against event time {event['time']}")
            if self.curr_time >= event["time"]:
                print("llllm NOOOOOOOOO")
                log_debug_info(f"Event triggered: {event}")
                if event["type"] == "accident":
                    log_debug_info(f"Event time met: {event['time']}")
                    # オブジェクトの位置を取得
                    locations = self.maze.get_tiles_by_object_v2(event["details"]["object"])
                    log_debug_info(f"Location for {event['details']['object']}: {locations}")

                    if locations:
                        for location in locations:
                            # 先にアクシデントを追加する前に，そのタイルの既存のイベントを消す必要がある
                            remove_event = (
                                event["details"]["object"], None, None, None
                            )
                            self.maze.remove_event_from_tile(remove_event, location)

                            # 次にアクシデントイベントを追加する
                            accident_event = (
                                event["details"]["object"], "is being", "on fire", event["details"]["description"])
                            self.maze.add_event_from_tile(accident_event, location)
                            # self.personas['Isabella Rodriguez'].accident_events.append(accident_event)
                            log_debug_info(f"Added event to {location}: {accident_event}")
                            # ここで一旦消してみる
                            # self.personas['Isabella Rodriguez'].accident_events.remove(accident_event)
                    else:
                        log_debug_info(f"Object {event['details']['object']} not found in maze.")
                    self.scheduled_events.remove(event)
                    log_debug_info(f"Event removed from scheduled events: {event}")
                    self.accident_flag = False  # 追加は一度だけ

    def start_server(self, int_counter):
        """
        The main backend server of Reverie.
        This function retrieves the environment file from the frontend to
        understand the state of the world, calls on each personas to make
        decisions based on the world state, and saves their moves at certain step
        intervals.
        INPUT
          int_counter: Integer value for the number of steps left for us to take
                       in this iteration.
        OUTPUT
          None
        """
        # <sim_folder> は現在のシミュレーションフォルダを指す
        sim_folder = f"{fs_storage}/{self.sim_code}"


        # ペルソナがゲームオブジェクトに到達すると，オブジェクトに一意のイベントを付与する
        # e.g., ('double studio[...]:bed', 'is', 'unmade', 'unmade')
        # あとで，このサイクルが終了する前に，それを初期状態に戻す必要がある
        # e.g., ('double studio[...]:bed', None, None, None)
        # そのため追加したイベントを追跡する必要がある
        # <game_obj_cleanup> はこのために使用される
        game_obj_cleanup = dict()

        # タイルイベントの保存ディレクトリを設定
        tile_events_folder = os.path.join(sim_folder, 'tile_events')
        if not os.path.exists(tile_events_folder):
            os.makedirs(tile_events_folder)

        total_steps = int_counter

        self.update_progress(0, total_steps)

        # The main while loop of Reverie.
        while (True):
            print("残りループ回数", int_counter)
            # Done with this iteration if <int_counter> reaches 0.
            log_debug_info(f"Remaining loop count: {int_counter}")
            if int_counter == 0:
                break

            # <curr_env_file> はフロントエンドが出力するファイル
            # フロントエンドがペルソナを移動させたあと，ステップカウントに一致する新しい環境ファイルを配置する．
            # その時に以下のfor文のループを実行，そうでなければ待機
            curr_env_file = f"{sim_folder}/environment/{self.step}.json"
            if check_if_file_exists(curr_env_file):
                log_debug_info("Step 1 completed")
                # 現在の新しい環境ファイルということは，新しい認識入力がペルソナにあることを意味する
                # まずそれを取得
                try:
                    # Try and save block for robustness of the while loop.
                    with open(curr_env_file) as json_file:
                        new_env = json.load(json_file)
                        env_retrieved = True
                except:
                    pass

                if env_retrieved:
                    log_debug_info("Step 2 completed")
                    # ここで<game_obj_cleanup>によって，このサイクルで使用された全てのオブジェクトアクションをクリーンアップする
                    for key, val in game_obj_cleanup.items():
                        #　全てのオブジェクトアクションをブランク形式(None付き)に変更
                        self.maze.turn_event_from_tile_idle(key, val)
                    # game_obj_cleanup を初期化
                    game_obj_cleanup = dict()

                    # まずフロントエンドに合わせて，バックエンド環境でもペルソナを移動させる
                    for persona_name, persona in self.personas.items():
                        # <curr_tile> はペルソナが以前いたタイル
                        curr_tile = self.personas_tile[persona_name]
                        # はこのサイクル中にペルソナが移動するタイル

                        new_tile = (new_env[persona_name]["x"],
                                    new_env[persona_name]["y"])

                        # 実際にバックエンドタイルマップ上でペルソナをここで移動させる
                        self.personas_tile[persona_name] = new_tile
                        self.maze.remove_subject_events_from_tile(persona.name, curr_tile)
                        # 現在のイベントを取得
                        current_event = persona.scratch.get_curr_event_and_desc()

                        # イベントの説明に"fire"が含まれていない場合にのみイベントを追加
                        if not current_event[-1] or "fire" not in current_event[-1]:
                            self.maze.add_event_from_tile(current_event, new_tile)

                        # ペルソナが目的地に到達したら，そのオブジェクトアクションをアクティブにする
                        if not persona.scratch.planned_path:
                            # バックエンドタイルマップに新しいオブジェクトアクションイベントを追加する
                            # 作成時にペルソナのバックエンドに保存される
                            # オブジェクトアクションイベントを追加する際に火事イベントを除外
                            obj_event = persona.scratch.get_curr_obj_event_and_desc()
                            if not obj_event[-1] or "fire" not in obj_event[-1]:
                                game_obj_cleanup[obj_event] = new_tile
                                self.maze.add_event_from_tile(obj_event, new_tile)
                            # 現在のアクションを行っているオブジェクトの一時的なブランクアクションを削除する必要もある
                            blank = (persona.scratch.get_curr_obj_event_and_desc()[0],
                                     None, None, None)
                            self.maze.remove_event_from_tile(blank, new_tile)

                    # 追加
                    # スケジュールされたイベントの確認と発生
                    # if self.accident_flag:
                    #     self.handle_scheduled_events()

                    # 各ステップ終了時にカフェのタイル情報をログに出力
                    # self.maze.log_cafe_tile_info(int_counter)

                    # 各ステップ終了時にタイル情報を保存
                    self.maze.save_tile_events(self.step, tile_events_folder)

                    # 次に，各ペルソナが認識して移動する必要がある．
                    # 各ペルソナの移動はx, y座標の形式で行われる．例：(50,34)
                    # ここでペルソナのコアブレインが呼び出される
                    movements = {"persona": dict(),
                                 "meta": dict()}
                    for persona_name, persona in self.personas.items():
                        # <next_tile> はx,y 座標． e.g., (58, 9)
                        # <pronunciatio> is an 絵文字. e.g., "\ud83d\udca4"
                        # <description> is 移動の文字列説明. e.g.,
                        #   writing her next novel (editing her novel)
                        #   @ double studio:double studio:common room:sofa
                        next_tile, pronunciatio, description = persona.move(
                            self.maze, self.personas, self.personas_tile[persona_name],
                            self.curr_time)
                        movements["persona"][persona_name] = {}
                        movements["persona"][persona_name]["movement"] = next_tile
                        movements["persona"][persona_name]["pronunciatio"] = pronunciatio
                        movements["persona"][persona_name]["description"] = description
                        movements["persona"][persona_name]["chat"] = (persona
                                                                      .scratch.chat)

                    log_debug_info(f"Agent movements: {movements}")

                    # Include the meta information about the current stage in the
                    # movements dictionary.
                    movements["meta"]["curr_time"] = (self.curr_time
                                                      .strftime("%B %d, %Y, %H:%M:%S"))

                    # We then write the personas' movements to a file that will be sent
                    # to the frontend server.
                    # Example json output:
                    # {"persona": {"Maria Lopez": {"movement": [58, 9]}},
                    #  "persona": {"Klaus Mueller": {"movement": [38, 12]}},
                    #  "meta": {curr_time: <datetime>}}
                    curr_move_file = f"{sim_folder}/movement/{self.step}.json"
                    with open(curr_move_file, "w") as outfile:
                        outfile.write(json.dumps(movements, indent=2))

                    # After this cycle, the world takes one step forward, and the
                    # current time moves by <sec_per_step> amount.
                    self.step += 1
                    self.curr_time += datetime.timedelta(seconds=self.sec_per_step)

                    # 次のjsonファイルを作る部分追加
                    # Create the next environment file based on the movements
                    next_env = {}
                    for persona_name, persona_details in movements["persona"].items():
                        next_env[persona_name] = {
                            "maze": self.maze.maze_name,
                            "x": persona_details["movement"][0],
                            "y": persona_details["movement"][1]
                        }
                    next_env_file = f"{sim_folder}/environment/{self.step}.json"
                    with open(next_env_file, "w") as outfile:
                        json.dump(next_env, outfile, indent=2)

                    # 各ステップ終了時にペルソナ情報をログに出力
                    # for persona_name, persona in self.personas.items():
                    #     log_persona_info(persona,
                    #                      file_path=f'backend/log_persona/{persona_name}_step_{self.step}_log.txt')

                    int_counter -= 1

                    # プログレスの更新
                    # TODO もし普通に実行してエラー出たらここのせいかも，そしたらコメントアウト
                    self.update_progress(total_steps - int_counter, total_steps)

            # Sleep so we don't burn our machines.
            time.sleep(self.server_sleep)

    def open_server(self):
        """
        Open up an interactive terminal prompt that lets you run the simulation
        step by step and probe agent state.

        INPUT
          None
        OUTPUT
          None
        """
        print("Note: The agents in this simulation package are computational")
        print("constructs powered by generative agents architecture and LLM. We")
        print("clarify that these agents lack human-like agency, consciousness,")
        print("and independent decision-making.\n---")

        # 計測用
        start_time = time.time()

        # <sim_folder> points to the current simulation folder.
        sim_folder = f"{fs_storage}/{self.sim_code}"

        # Ensure movement directory exists
        movement_folder = f"{sim_folder}/movement"
        if not os.path.exists(movement_folder):
            os.makedirs(movement_folder)

        while True:
            sim_command = input("Enter option: ")
            sim_command = sim_command.strip()
            ret_str = ""

            try:
                if sim_command.lower() in ["f", "fin", "finish", "save and finish"]:
                    # Finishes the simulation environment and saves the progress.
                    # Example: fin
                    self.save()
                    compress(sim_code=self.sim_code)
                    # translate_master_movement(self.sim_code)  # 翻訳を実行
                    print(self.sim_code)

                    break

                elif sim_command.lower() == "start path tester mode":
                    # Starts the path tester and removes the currently forked sim files.
                    # Note that once you start this mode, you need to exit out of the
                    # session and restart in case you want to run something else.
                    shutil.rmtree(sim_folder)
                    self.start_path_tester_server()

                elif sim_command.lower() == "exit":
                    # Finishes the simulation environment but does not save the progress
                    # and erases all saved data from current simulation.
                    # Example: exit
                    shutil.rmtree(sim_folder)
                    break

                elif sim_command.lower() == "save":
                    # Saves the current simulation progress.
                    # Example: save
                    self.save()

                elif sim_command[:3].lower() == "run":
                    # Runs the number of steps specified in the prompt.
                    # Example: run 1000
                    int_count = int(sim_command.split()[-1])
                    rs.start_server(int_count)
                    end_time = time.time()
                    print(end_time - start_time)
                    with open("log.txt", "a") as f:
                        f.write(f"シミュレーション時間：{end_time - start_time}\n")

                elif ("print persona schedule"
                      in sim_command[:22].lower()):
                    # Print the decomposed schedule of the persona specified in the
                    # prompt.
                    # Example: print persona schedule Isabella Rodriguez
                    ret_str += (self.personas[" ".join(sim_command.split()[-2:])]
                                .scratch.get_str_daily_schedule_summary())

                elif ("print all persona schedule"
                      in sim_command[:26].lower()):
                    # Print the decomposed schedule of all personas in the world.
                    # Example: print all persona schedule
                    for persona_name, persona in self.personas.items():
                        ret_str += f"{persona_name}\n"
                        ret_str += f"{persona.scratch.get_str_daily_schedule_summary()}\n"
                        ret_str += f"---\n"

                elif ("print hourly org persona schedule"
                      in sim_command.lower()):
                    # Print the hourly schedule of the persona specified in the prompt.
                    # This one shows the original, non-decomposed version of the
                    # schedule.
                    # Ex: print persona schedule Isabella Rodriguez
                    ret_str += (self.personas[" ".join(sim_command.split()[-2:])]
                                .scratch.get_str_daily_schedule_hourly_org_summary())

                elif ("print persona current tile"
                      in sim_command[:26].lower()):
                    # Print the x y tile coordinate of the persona specified in the
                    # prompt.
                    # Ex: print persona current tile Isabella Rodriguez
                    ret_str += str(self.personas[" ".join(sim_command.split()[-2:])]
                                   .scratch.curr_tile)

                elif ("print persona chatting with buffer"
                      in sim_command.lower()):
                    # Print the chatting with buffer of the persona specified in the
                    # prompt.
                    # Ex: print persona chatting with buffer Isabella Rodriguez
                    curr_persona = self.personas[" ".join(sim_command.split()[-2:])]
                    for p_n, count in curr_persona.scratch.chatting_with_buffer.items():
                        ret_str += f"{p_n}: {count}"

                elif ("print persona associative memory (event)"
                      in sim_command.lower()):
                    # Print the associative memory (event) of the persona specified in
                    # the prompt
                    # Ex: print persona associative memory (event) Isabella Rodriguez
                    ret_str += f'{self.personas[" ".join(sim_command.split()[-2:])]}\n'
                    ret_str += (self.personas[" ".join(sim_command.split()[-2:])]
                                .a_mem.get_str_seq_events())

                elif ("print persona associative memory (thought)"
                      in sim_command.lower()):
                    # Print the associative memory (thought) of the persona specified in
                    # the prompt
                    # Ex: print persona associative memory (thought) Isabella Rodriguez
                    ret_str += f'{self.personas[" ".join(sim_command.split()[-2:])]}\n'
                    ret_str += (self.personas[" ".join(sim_command.split()[-2:])]
                                .a_mem.get_str_seq_thoughts())

                elif ("print persona associative memory (chat)"
                      in sim_command.lower()):
                    # Print the associative memory (chat) of the persona specified in
                    # the prompt
                    # Ex: print persona associative memory (chat) Isabella Rodriguez
                    ret_str += f'{self.personas[" ".join(sim_command.split()[-2:])]}\n'
                    ret_str += (self.personas[" ".join(sim_command.split()[-2:])]
                                .a_mem.get_str_seq_chats())

                elif ("print persona spatial memory"
                      in sim_command.lower()):
                    # Print the spatial memory of the persona specified in the prompt
                    # Ex: print persona spatial memory Isabella Rodriguez
                    self.personas[" ".join(sim_command.split()[-2:])].s_mem.print_tree()

                elif ("print current time"
                      in sim_command[:18].lower()):
                    # Print the current time of the world.
                    # Ex: print current time
                    ret_str += f'{self.curr_time.strftime("%B %d, %Y, %H:%M:%S")}\n'
                    ret_str += f'steps: {self.step}'

                elif ("print tile event"
                      in sim_command[:16].lower()):
                    # Print the tile events in the tile specified in the prompt
                    # Ex: print tile event 50, 30
                    cooordinate = [int(i.strip()) for i in sim_command[16:].split(",")]
                    for i in self.maze.access_tile(cooordinate)["events"]:
                        ret_str += f"{i}\n"

                elif ("print tile details"
                      in sim_command.lower()):
                    # Print the tile details of the tile specified in the prompt
                    # Ex: print tile event 50, 30
                    cooordinate = [int(i.strip()) for i in sim_command[18:].split(",")]
                    for key, val in self.maze.access_tile(cooordinate).items():
                        ret_str += f"{key}: {val}\n"

                elif ("call -- analysis"
                      in sim_command.lower()):
                    # Starts a stateless chat session with the agent. It does not save
                    # anything to the agent's memory.
                    # Ex: call -- analysis Isabella Rodriguez
                    persona_name = sim_command[len("call -- analysis"):].strip()
                    self.personas[persona_name].open_convo_session("analysis")

                elif ("call -- load history"
                      in sim_command.lower()):
                    curr_file = maze_assets_loc + "/" + sim_command[len("call -- load history"):].strip()
                    # call -- load history the_ville/agent_history_init_n3.csv

                    rows = read_file_to_list(curr_file, header=True, strip_trail=True)[1]
                    clean_whispers = []
                    for row in rows:
                        agent_name = row[0].strip()
                        whispers = row[1].split(";")
                        whispers = [whisper.strip() for whisper in whispers]
                        for whisper in whispers:
                            clean_whispers += [[agent_name, whisper]]

                    load_history_via_whisper(self.personas, clean_whispers)

                print(ret_str)

            except:
                traceback.print_exc()
                print("Error.")
                pass

    def start_simulation(self, total_steps):
        try:
            print(f"Starting simulation for {total_steps} steps")

            # 進行状況を初期化
            self.update_progress(0, total_steps)

            # すべてのステップを一度に処理するように変更
            self.start_server(total_steps)

        except Exception as e:
            print(f"Error during simulation: {e}")
            raise

    def update_progress(self, current_step, total_steps):
        """
        進行状況をファイルに保存する（例: JSONファイル）。
        """
        progress_data = {
            'current_step': current_step,
            'total_steps': total_steps,
            'progress': (current_step / total_steps) * 100
        }
        print("Updating progress:", progress_data)  # デバッグ用メッセージ
        with open(f"{fs_temp_storage}/progress.json", "w") as outfile:
            json.dump(progress_data, outfile)

    @staticmethod
    def get_progress():
        """
        シミュレーションの進行状況を返すエンドポイント。
        """
        try:
            with open(f"{fs_temp_storage}/progress.json") as json_file:
                progress_data = json.load(json_file)
                return JsonResponse(progress_data)
        except FileNotFoundError:
            return JsonResponse({'current_step': 0, 'total_steps': 0, 'progress': 0})

    def finish_simulation(self):
        """
        シミュレーションを終了し、データを保存します。
        """
        try:
            self.save()
            compress(sim_code=self.sim_code)
            print(f"Simulation {self.sim_code} finished successfully.")
        except Exception as e:
            print(f"Failed to finish simulation: {e}")


if __name__ == '__main__':
    # rs = ReverieServer("base_the_ville_isabella_maria_klaus",
    #                    "July1_the_ville_isabella_maria_klaus-step-3-1")
    # rs = ReverieServer("July1_the_ville_isabella_maria_klaus-step-3-20",
    #                    "July1_the_ville_isabella_maria_klaus-step-3-21")
    # rs.open_server()

    origin = input("Enter the name of the forked simulation: ").strip()
    target = input("Enter the name of the new simulation: ").strip()

    rs = ReverieServer(origin, target)
    rs.open_server()
