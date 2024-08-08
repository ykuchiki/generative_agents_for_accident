"""
Author: Joon Sung Park (joonspk@stanford.edu)
File: views.py
"""
import os
import ast
import string
import random
import json
import requests
from os import listdir
import sys

# 現在のファイルのディレクトリを基に絶対パスを計算してsys.pathに追加
current_file_path = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.join(current_file_path, '..', '..')
sys.path.append(parent_directory)

import datetime
from django.shortcuts import render, redirect, HttpResponseRedirect
from django.http import HttpResponse, JsonResponse
from django.conf import settings

from frontend.global_methods import *
from backend.reverie import ReverieServer

from django.contrib.staticfiles.templatetags.staticfiles import static
from .models import *

ref = "frontend"
stored_data = {'time': None, 'step': None}

def landing(request):
  context = {}
  template = "landing/landing.html"
  return render(request, template, context)

def input_traits(request):
  template = 'frontend/frontend_server/templates/input_traits/input_traits.html'
  if request.method == 'POST':
    data = {
      "vision_r": request.POST.get('vision_r'),
      "att_bandwidth": request.POST.get('att_bandwidth'),
      "retention": request.POST.get('retention'),
      "curr_time": None,
      "curr_tile": None,
      "daily_plan_req": request.POST.get('daily_plan_req'),
      "name": request.POST.get('name'),
      "first_name": request.POST.get('first_name'),
      "last_name": request.POST.get('last_name'),
      "age": request.POST.get('age'),
      "innate": request.POST.get('innate'),
      "learned": request.POST.get('learned'),
      "currently": request.POST.get('currently'),
      "lifestyle": request.POST.get('lifestyle'),
      "living_area": request.POST.get('living_area'),
      "concept_forget": 100,
      "daily_reflection_time": 180,
      "daily_reflection_size": 5,
      "overlap_reflect_th": 4,
      "kw_strg_event_reflect_th": 10,
      "kw_strg_thought_reflect_th": 9,
      "recency_w": 1,
      "relevance_w": 1,
      "importance_w": 1,
      "recency_decay": 0.995,
      "importance_trigger_max": 150,
      "importance_trigger_curr": 150,
      "importance_ele_n": 0,
      "thought_count": 5,
      "daily_req": [],
      "f_daily_schedule": [],
      "f_daily_schedule_hourly_org": [],
      "act_address": None,
      "act_start_time": None,
      "act_duration": None,
      "act_description": None,
      "act_pronunciatio": None,
      "act_event": ["Isabella Rodriguez", None, None],
      "act_obj_description": None,
      "act_obj_pronunciatio": None,
      "act_obj_event": [None, None, None],
      "chatting_with": None,
      "chat": None,
      "chatting_with_buffer": {},
      "chatting_end_time": None,
      "act_path_set": False,
      "planned_path": []
    }

    env_location = request.POST.get('location')
    path = 'storage/' + env_location + '/personas/Isabella Rodriguez/bootstrap_memory/scratch.json'

    # Save data as JSON in the backend (example: save to a file or database)
    with open(path, 'w') as json_file:
      json.dump(data, json_file, indent=4)

    return JsonResponse(data)
  else:
    return render(request, template)


def set_time_value(request):
  global stored_data
  if request.method == 'POST':
    data = request.POST
    stored_data['time'] = data.get('time')
    stored_data['step'] = data.get('step')
    return JsonResponse({'status': 'success'})  # 修正: JsonResponseを使用してJSON形式で返す
  return JsonResponse({'status': 'failed'})  # 修正: JsonResponseを使用してJSON形式で返す


def get_time_value(request):
  global stored_data
  return JsonResponse(stored_data)


def agent_logs(request, sim_code, step, play_speed):
  move_file = f"{ref}/compressed_storage/{sim_code}/master_movement.json"
  meta_file = f"{ref}/compressed_storage/{sim_code}/meta.json"
  step = int(step)
  play_speed_opt = {"1": 1, "2": 2, "3": 4,
                    "4": 8, "5": 16, "6": 32}
  if play_speed not in play_speed_opt:
    play_speed = 2
  else:
    play_speed = play_speed_opt[play_speed]

  # Loading the basic meta information about the simulation.
  meta = dict()
  with open(meta_file) as json_file:
    meta = json.load(json_file)

  sec_per_step = meta["sec_per_step"]
  start_datetime = datetime.datetime.strptime(meta["start_date"] + " 00:00:00",
                                              '%B %d, %Y %H:%M:%S')
  for i in range(step):
    start_datetime += datetime.timedelta(seconds=sec_per_step)
  start_datetime = start_datetime.strftime("%Y-%m-%dT%H:%M:%S")

  # Loading the movement file
  raw_all_movement = dict()
  with open(move_file) as json_file:
    raw_all_movement = json.load(json_file)

  # Loading all names of the personas
  persona_names = dict()
  persona_names = []
  persona_names_set = set()
  for p in list(raw_all_movement["0"].keys()):
    persona_names += [{"original": p,
                       "underscore": p.replace(" ", "_"),
                       "initial": p[0] + p.split(" ")[-1][0]}]
    persona_names_set.add(p)

  # <all_movement> is the main movement variable that we are passing to the
  # frontend. Whereas we use ajax scheme to communicate steps to the frontend
  # during the simulation stage, for this demo, we send all movement
  # information in one step.
  all_movement = dict()

  # Preparing the initial step.
  # <init_prep> sets the locations and descriptions of all agents at the
  # beginning of the demo determined by <step>.
  init_prep = dict()
  for int_key in range(step + 1):
    key = str(int_key)
    val = raw_all_movement[key]
    for p in persona_names_set:
      if p in val:
        init_prep[p] = val[p]
  persona_init_pos = dict()
  for p in persona_names_set:
    persona_init_pos[p.replace(" ", "_")] = init_prep[p]["movement"]
  all_movement[step] = init_prep

  # Finish loading <all_movement>
  for int_key in range(step + 1, len(raw_all_movement.keys())):
    all_movement[int_key] = raw_all_movement[str(int_key)]

  # Load the initial logs for the agents
  # We need 1 action for each agent, so when they get an action, set their position to false.
  persona_action_check = {"Isabella Rodriguez": False, "Klaus Mueller": False, "Maria Lopez": False}
  persona_data = {"Isabella Rodriguez": {"description": "まだ何も", "chat": "まだ何も"},
                  "Klaus Mueller": {"description": "まだ何も", "chat": "まだ何も"},
                  "Maria Lopez": {"description": "まだ何も", "chat": "まだ何も"}}
  for int_key in range(step, 0, -1):
    if bool(all_movement[int_key]):
      for p in all_movement[int_key]:
        if persona_data[p]["description"] != "まだ何も":
          continue
        else:
          persona_data[p] = {"description": all_movement[int_key][p]["description"],
                             "chat": all_movement[int_key][p]["chat"]}
          persona_action_check[p] = True
    if False not in persona_action_check.values():
      break
  persona_data = json.dumps(persona_data)

  context = {"sim_code": sim_code,
             "step": step,
             "persona_names": persona_names,
             "persona_init_pos": json.dumps(persona_init_pos),
             "all_movement": json.dumps(all_movement),
             "starting_logs": persona_data,
             "start_datetime": start_datetime,
             "sec_per_step": sec_per_step,
             "play_speed": play_speed,
             "mode": "demo"}
  template = "agent_logs/agent_logs.html"
  return render(request, template, context)


def demo_(request, sim_code, step, play_speed="2"):
  move_file = f"{ref}/compressed_storage/{sim_code}/master_movement.json"
  meta_file = f"{ref}/compressed_storage/{sim_code}/meta.json"
  step = int(step)
  play_speed_opt = {"1": 1, "2": 2, "3": 4,
                    "4": 8, "5": 16, "6": 32}
  if play_speed not in play_speed_opt: play_speed = 2
  else: play_speed = play_speed_opt[play_speed]

  # シミュレーションの基本メタ情報を読み込む
  meta = dict()
  with open (meta_file) as json_file:
    meta = json.load(json_file)

  sec_per_step = meta["sec_per_step"]
  start_datetime = datetime.datetime.strptime(meta["start_date"] + " 00:00:00",
                                              '%B %d, %Y %H:%M:%S')
  for i in range(step):
    start_datetime += datetime.timedelta(seconds=sec_per_step)
  start_datetime = start_datetime.strftime("%Y-%m-%dT%H:%M:%S")

  # movementファイルの読み込み
  raw_all_movement = dict()
  with open(move_file) as json_file:
    raw_all_movement = json.load(json_file)

  # 全てのペルソナの名前を読み込む
  persona_names = dict()
  persona_names = []
  persona_names_set = set()
  for p in list(raw_all_movement["0"].keys()):
    persona_names += [{"original": p,
                       "underscore": p.replace(" ", "_"),
                       "initial": p[0] + p.split(" ")[-1][0]}]
    persona_names_set.add(p)

  # <all_movement> はフロントエンドに渡す主要な動きの変数。
  # シミュレーション段階ではステップをフロントエンドに送信するためにajaxを使用しますが、
  # このデモでは全ての動き情報を一度に送信します。
  all_movement = dict()

  # 初期ステップを準備する。
  # <init_prep> はデモの開始時に、<step> で決定される全てのエージェントの位置と説明を設定します。
  init_prep = dict()
  for int_key in range(step+1):
    key = str(int_key)
    val = raw_all_movement[key]
    for p in persona_names_set:
      if p in val:
        init_prep[p] = val[p]
  persona_init_pos = dict()
  for p in persona_names_set:
    persona_init_pos[p.replace(" ","_")] = init_prep[p]["movement"]
  all_movement[step] = init_prep

  # <all_movement> の読み込みを完了する。
  for int_key in range(step+1, len(raw_all_movement.keys())):
    all_movement[int_key] = raw_all_movement[str(int_key)]

  context = {"sim_code": sim_code,
             "step": step,
             "persona_names": persona_names,
             "persona_init_pos": json.dumps(persona_init_pos),
             "all_movement": json.dumps(all_movement),
             "start_datetime": start_datetime,
             "sec_per_step": sec_per_step,
             "play_speed": play_speed,
             "mode": "demo"}
  template = "demo/demo.html"

  return render(request, template, context)


def UIST_Demo(request):
  return demo(request, "March20_the_ville_n25_UIST_RUN-step-1-141", 2160, play_speed="3")


def home(request):
  f_curr_sim_code = f"{ref}/temp_storage/curr_sim_code.json"
  f_curr_step = f"{ref}/temp_storage/curr_step.json"

  if not check_if_file_exists(f_curr_step):
    context = {}
    template = "home/error_start_backend.html"
    return render(request, template, context)

  with open(f_curr_sim_code) as json_file:
    sim_code = json.load(json_file)["sim_code"]

  with open(f_curr_step) as json_file:
    step = json.load(json_file)["step"]

  os.remove(f_curr_step)

  persona_names = []
  persona_names_set = set()
  for i in find_filenames(f"{ref}/storage/{sim_code}/personas", ""):
    x = i.split("/")[-1].strip()
    if x[0] != ".":
      persona_names += [[x, x.replace(" ", "_")]]
      persona_names_set.add(x)

  persona_init_pos = []
  file_count = []
  for i in find_filenames(f"{ref}/storage/{sim_code}/environment", ".json"):
    x = i.split("/")[-1].strip()
    if x[0] != ".":
      file_count += [int(x.split(".")[0])]
  curr_json = f'{ref}/storage/{sim_code}/environment/{str(max(file_count))}.json'
  with open(curr_json) as json_file:
    persona_init_pos_dict = json.load(json_file)
    for key, val in persona_init_pos_dict.items():
      if key in persona_names_set:
        persona_init_pos += [[key, val["x"], val["y"]]]

  context = {"sim_code": sim_code,
             "step": step,
             "persona_names": persona_names,
             "persona_init_pos": persona_init_pos,
             "mode": "simulate"}
  template = "home/home.html"
  return render(request, template, context)


def replay(request, sim_code, step):
  sim_code = sim_code
  step = int(step)

  persona_names = []
  persona_names_set = set()
  for i in find_filenames(f"{ref}/storage/{sim_code}/personas", ""):
    x = i.split("/")[-1].strip()
    if x[0] != ".":
      persona_names += [[x, x.replace(" ", "_")]]
      persona_names_set.add(x)

  persona_init_pos = []
  file_count = []
  for i in find_filenames(f"{ref}/storage/{sim_code}/environment", ".json"):
    x = i.split("/")[-1].strip()
    if x[0] != ".":
      file_count += [int(x.split(".")[0])]
  curr_json = f'{ref}/storage/{sim_code}/environment/{str(max(file_count))}.json'
  with open(curr_json) as json_file:
    persona_init_pos_dict = json.load(json_file)
    for key, val in persona_init_pos_dict.items():
      if key in persona_names_set:
        persona_init_pos += [[key, val["x"], val["y"]]]

  context = {"sim_code": sim_code,
             "step": step,
             "persona_names": persona_names,
             "persona_init_pos": persona_init_pos,
             "mode": "replay"}
  template = "home/home.html"
  return render(request, template, context)


def replay_persona_state(request, sim_code, step, persona_name):
  sim_code = sim_code
  step = int(step)

  persona_name_underscore = persona_name
  persona_name = " ".join(persona_name.split("_"))
  memory = f"storage/{sim_code}/personas/{persona_name}/bootstrap_memory"
  if not os.path.exists(memory):
    memory = f"{ref}/compressed_storage/{sim_code}/personas/{persona_name}/bootstrap_memory"

  with open(memory + "/scratch.json") as json_file:
    scratch = json.load(json_file)

  with open(memory + "/spatial_memory.json") as json_file:
    spatial = json.load(json_file)

  with open(memory + "/associative_memory/nodes.json") as json_file:
    associative = json.load(json_file)

  a_mem_event = []
  a_mem_chat = []
  a_mem_thought = []

  for count in range(len(associative.keys()), 0, -1):
    node_id = f"node_{str(count)}"
    node_details = associative[node_id]

    if node_details["type"] == "event":
      a_mem_event += [node_details]

    elif node_details["type"] == "chat":
      a_mem_chat += [node_details]

    elif node_details["type"] == "thought":
      a_mem_thought += [node_details]

  context = {"sim_code": sim_code,
             "step": step,
             "persona_name": persona_name,
             "persona_name_underscore": persona_name_underscore,
             "scratch": scratch,
             "spatial": spatial,
             "a_mem_event": a_mem_event,
             "a_mem_chat": a_mem_chat,
             "a_mem_thought": a_mem_thought}
  template = "persona_state/persona_state.html"
  return render(request, template, context)


def path_tester(request):
  context = {}
  template = "path_tester/path_tester.html"
  return render(request, template, context)


def process_environment(request):
  """
  <FRONTEND to BACKEND>
  This sends the frontend visual world information to the backend server.
  It does this by writing the current environment representation to
  "storage/environment.json" file.

  ARGS:
    request: Django request
  RETURNS:
    HttpResponse: string confirmation message.
  """
  # f_curr_sim_code = "temp_storage/curr_sim_code.json"
  # with open(f_curr_sim_code) as json_file:
  #   sim_code = json.load(json_file)["sim_code"]

  data = json.loads(request.body)
  step = data["step"]
  sim_code = data["sim_code"]
  environment = data["environment"]

  with open(f"{ref}/storage/{sim_code}/environment/{step}.json", "w") as outfile:
    outfile.write(json.dumps(environment, indent=2))

  return HttpResponse("received")


def update_environment(request):
  """
  <BACKEND to FRONTEND>
  This sends the backend computation of the persona behavior to the frontend
  visual server.
  It does this by reading the new movement information from
  "storage/movement.json" file.

  ARGS:
    request: Django request
  RETURNS:
    HttpResponse
  """
  # f_curr_sim_code = "temp_storage/curr_sim_code.json"
  # with open(f_curr_sim_code) as json_file:
  #   sim_code = json.load(json_file)["sim_code"]

  data = json.loads(request.body)
  step = data["step"]
  sim_code = data["sim_code"]

  response_data = {"<step>": -1}
  if (check_if_file_exists(f"{ref}/storage/{sim_code}/movement/{step}.json")):
    with open(f"{ref}/storage/{sim_code}/movement/{step}.json") as json_file:
      response_data = json.load(json_file)
      response_data["<step>"] = step

  return JsonResponse(response_data)


def path_tester_update(request):
  """
  Processing the path and saving it to path_tester_env.json temp storage for
  conducting the path tester.

  ARGS:
    request: Django request
  RETURNS:
    HttpResponse: string confirmation message.
  """
  data = json.loads(request.body)
  camera = data["camera"]

  with open(f"{ref}/temp_storage/path_tester_env.json", "w") as outfile:
    outfile.write(json.dumps(camera, indent=2))

  return HttpResponse("received")


from django.shortcuts import render
import ast


def parse_event_data(event_data_str):
  # タプル内の要素をクォートで囲むための処理
  # 例えば、"name" -> "'name'"
  event_data_str = event_data_str.replace("{(", "[('").replace(")}", "')]")
  event_data_str = event_data_str.replace(", ", "', '").replace("', ' ", ", '")  # 適切なカンマの配置

  try:
    event_data = ast.literal_eval(event_data_str)
    return event_data
  except (SyntaxError, ValueError) as e:
    print(f"Error parsing event data: {e}")
    return None


def get_all_tile_events(simulation_name, max_step):
  all_events = {}
  for step in range(max_step + 1):
    file_path = f'frontend/storage/{simulation_name}/tile_events/{step}_maze.txt'
    if os.path.exists(file_path):
      with open(file_path, 'r') as f:
        for line in f:
          parts = line.strip().split(' ', 2)
          if len(parts) == 3:
            x, y, event_data_str = parts
            event_data = parse_event_data(event_data_str)
            if event_data:
              tile_key = f'{x}_{y}'
              if tile_key not in all_events:
                all_events[tile_key] = {}
              if step not in all_events[tile_key]:
                all_events[tile_key][step] = []
              all_events[tile_key][step].extend(event_data)
  return all_events


def demo(request, sim_code, step, play_speed="2"):
  # ファイルパスの設定
  move_file = f"{ref}/compressed_storage/{sim_code}/master_movement.json"
  meta_file = f"{ref}/compressed_storage/{sim_code}/meta.json"
  step = int(step)

  # 再生速度の設定
  play_speed_opt = {"1": 1, "2": 2, "3": 4, "4": 8, "5": 16, "6": 32}
  play_speed = play_speed_opt.get(play_speed, 2)

  # メタ情報の読み込み
  with open(meta_file) as json_file:
    meta = json.load(json_file)

  sec_per_step = meta["sec_per_step"]
  start_datetime = datetime.datetime.strptime(
    meta["start_date"] + " 00:00:00", '%B %d, %Y %H:%M:%S')
  for i in range(step):
    start_datetime += datetime.timedelta(seconds=sec_per_step)
  start_datetime = start_datetime.strftime("%Y-%m-%dT%H:%M:%S")

  # 動きのデータを読み込む
  with open(move_file) as json_file:
    raw_all_movement = json.load(json_file)

  # ペルソナの名前を読み込む
  persona_names = []
  persona_names_set = set()
  for p in list(raw_all_movement["0"].keys()):
    persona_names.append({
      "original": p,
      "underscore": p.replace(" ", "_"),
      "initial": p[0] + p.split(" ")[-1][0]
    })
    persona_names_set.add(p)

  # 全ての動きを一度に送信
  all_movement = {}
  init_prep = {}
  for int_key in range(step + 1):
    key = str(int_key)
    val = raw_all_movement[key]
    for p in persona_names_set:
      if p in val:
        init_prep[p] = val[p]

  persona_init_pos = {p.replace(" ", "_"): init_prep[p]["movement"] for p in persona_names_set}
  all_movement[step] = init_prep

  for int_key in range(step + 1, len(raw_all_movement.keys())):
    all_movement[int_key] = raw_all_movement[str(int_key)]

  # すべてのタイルイベントを取得
  max_step = len(raw_all_movement.keys()) - 1
  all_tile_events = get_all_tile_events(sim_code, max_step)

  context = {
    "sim_code": sim_code,
    "step": step,
    "persona_names": persona_names,
    "persona_init_pos": json.dumps(persona_init_pos),
    "all_movement": json.dumps(all_movement),
    "start_datetime": start_datetime,
    "sec_per_step": sec_per_step,
    "play_speed": play_speed,
    "all_tile_events": json.dumps(all_tile_events),  # すべてのタイルイベントを渡す
    "mode": "demo"
  }

  template = "demo/demo.html"
  return render(request, template, context)

def agent_detail(request, sim_code):
  # ペルソナの詳細情報を取得
  move_file = f"{ref}/compressed_storage/{sim_code}/master_movement.json"

  # 動きのデータを読み込む
  with open(move_file) as json_file:
    raw_all_movement = json.load(json_file)

  # ペルソナの名前を動的に取得
  persona_names = []
  for p in list(raw_all_movement["0"].keys()):
    persona_names.append({
      "original": p,
      "underscore": p.replace(" ", "_"),
      "initial": p[0] + p.split(" ")[-1][0]
    })

  context = {
    'persona_names': persona_names,
    'sim_code': sim_code,
  }
  return render(request, 'agent_detail/agent_detail.html', context)


def agent_detail_data(request, persona_underscore, step, sim_code):
  move_file = f"{ref}/compressed_storage/{sim_code}/master_movement.json"

  with open(move_file) as json_file:
    raw_all_movement = json.load(json_file)

  # ペルソナ名の設定
  persona_name = persona_underscore.replace("_", " ")

  # 現在のステップの情報を取得
  step_data = raw_all_movement.get(str(step), {}).get(persona_name, {})

  # 現在のステップにデータがない場合は前のステップから取得
  while not step_data and step > 0:
    step -= 1
    step_data = raw_all_movement.get(str(step), {}).get(persona_name, {})

  # データが存在する場合のみ処理
  if step_data:
    description = step_data.get('description', '')
    current_action, target_address = description.split("@") if "@" in description else (description, '')
    target_address = target_address.replace('<persona>', '').strip()

    # 行動場所の形式を「建物: 部屋: オブジェクト」から「建物\n部屋\nオブジェクト」に変更
    if target_address.startswith('the Ville:'):
      target_address = target_address.replace('the Ville:', '', 1).strip()
    location_parts = target_address.split(':')

    # 各階層にラベルを追加
    formatted_target_address = []
    labels = ["建物", "部屋", "オブジェクト"]
    for i, part in enumerate(location_parts):
      part = translate_text(part)
      if i < len(labels):
        formatted_target_address.append(f"{labels[i]}: {part}")

    formatted_target_address = '<br>'.join(formatted_target_address) if formatted_target_address else target_address

    chat_data = step_data.get('chat', [])
    chat = "<br>".join([f"{c[0]}: {c[1]}" for c in chat_data]) if chat_data else "<em>None at the moment</em>"

    # 翻訳を実行
    current_action_translated = translate_text(current_action)
    formatted_target_address_translated = translate_text(formatted_target_address)
    chat_translated = translate_text(chat)

  else:
    # データが見つからない場合は空の情報を返す
    current_action_translated = ''
    formatted_target_address_translated = ''
    chat_translated = "<em>None at the moment</em>"

  data = {
    'current_action': current_action_translated,
    'target_address': formatted_target_address_translated,
    'chat': chat_translated
  }
  return JsonResponse(data)


simulations = {}


# views.py
def start_simulation_view(request):
    if request.method == "POST":
        try:
            # フォーク元のシミュレーションコードを固定
            origin = "base1"
            target = request.POST.get('target')
            innate = request.POST.get('innate')

            directory = f"frontend/storage/{origin}/personas/Isabella Rodriguez/bootstrap_memory"
            file_path = os.path.join(directory, 'scratch.json')
            accident_time = int(request.POST.get('accidentTime'))

            # JSONファイルを読み込み
            try:
              with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                # innateの値を更新
                data['innate'] = innate

                # 更新したデータをファイルに書き込み
                try:
                  with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception as e:
                  return JsonResponse({'status': 'failed', 'error': f'Failed to write JSON: {str(e)}'})
            except Exception as e:
              pass


            # ステップ数の選択
            duration_option = request.POST.get('duration')
            duration_mapping = {
                '30': 30,   # 5分
                '180': 180, # 30分
                '270': 270, # 45分
                '360': 360, # 1時間
                '1080': 1080, # 3時間
                '2160': 2160, # 6時間
                '8640': 8640 # 24時間
            }

            # ステップ数計算
            total_steps = duration_mapping.get(duration_option, 360)  # デフォルトを360分とする

            # デバッグ用ログ
            print(f"Starting simulation with target: {target}, total_steps: {total_steps}")

            # シミュレーションの開始
            # 新しいシミュレーションのインスタンスを作成して保存
            rs = ReverieServer(origin, target)
            simulations[target] = rs
            rs.schedule_accident_event("the Ville:Hobbs Cafe:cafe:cooking area", accident_time, "on fire")
            rs.start_server(total_steps)  # ここで一度だけ呼び出し、全ステップを実行

            return JsonResponse({'status': 'started'})
        except Exception as e:
            # エラーの詳細をログに出力
            print(f"Error starting simulation: {e}")
            return JsonResponse({'status': 'failed', 'error': str(e)})

    # GETリクエストの場合の処理
    return render(request, 'start_simulation/start_simulation.html')



def get_progress_view(request):
  """
  シミュレーションの進行状況を取得するビュー。
  """
  try:
    with open("frontend/temp_storage/progress.json") as json_file:
      progress_data = json.load(json_file)
      print("Progress data sent:", progress_data)  # デバッグ用ログコンソールそのー
      return JsonResponse(progress_data)
  except FileNotFoundError:
    return JsonResponse({'current_step': 0, 'total_steps': 0, 'progress': 0})

def update_progress(self, current_step, total_steps):
  """
  進行状況をファイルに保存する（例: JSONファイル）。
  """
  progress_data = {
    'current_step': current_step,
    'total_steps': total_steps,
    'progress': (current_step / total_steps) * 100
  }
  with open("frontend/temp_storage/progress.json", "w") as outfile:
    json.dump(progress_data, outfile)


def finish_simulation_view(request):
  if request.method == "POST":
    try:
      target = request.POST.get('target')  # 終了するシミュレーションのコードを取得
      rs = simulations.get(target)  # メモリ上のオブジェクトを取得
      if rs is None:
        return JsonResponse({'status': 'failed', 'error': 'Simulation not found'})

      rs.finish_simulation()  # 取得したオブジェクトでメソッドを呼び出す
      del simulations[target]  # メモリからオブジェクトを削除
      return JsonResponse({'status': 'finished'})
    except Exception as e:
      # エラーメッセージを返す
      return JsonResponse({'status': 'failed', 'error': str(e)})

  return HttpResponse("Invalid request", status=405)


from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()
# 環境変数からAPIキーを取得
# 二度と使わん(使い方ミスると数時間で10万円以上のトークン消費量になる)
# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# def translate_text(text, target_lang='ja'):
#   url = "https://translation.googleapis.com/language/translate/v2"
#   params = {
#     'q': text,
#     'target': target_lang,
#     'key': GOOGLE_API_KEY
#   }
#   response = requests.get(url, params=params)
#   result = response.json()
#   return result['data']['translations'][0]['translatedText']


