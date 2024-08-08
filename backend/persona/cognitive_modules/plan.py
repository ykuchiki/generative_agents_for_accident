import os
import datetime
import math
import random
import sys
import time
import pickle

# 現在のファイルのディレクトリを基に絶対パスを計算してsys.pathに追加
current_file_path = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.join(current_file_path, '..', '..', '..')
sys.path.append(parent_directory)

from backend.global_methods import *
from backend.persona.prompt_template.run_gpt_prompt import *
from backend.persona.cognitive_modules.retrieve import *
from backend.persona.cognitive_modules.converse import *


##############################################################################
# CHAPTER 2: Generate
##############################################################################

def log_to_file(file_path, content):
    with open(file_path, 'a') as f:
        f.write(content + '\n')

def generate_wake_up_hour(persona):
    """
    ペルソナが起きる時間を生成します。これはペルソナの日常計画を生成する
    プロセスの重要な部分となります。

    ペルソナの状態: 身元安定セット、ライフスタイル、名前

    INPUT:
      persona: ペルソナクラスのインスタンス
    OUTPUT:
      ペルソナの起床時間を示す整数
    例出力:
      8
    """
    if debug: print("GNS FUNCTION: <generate_wake_up_hour>")
    return int(run_gpt_prompt_wake_up_hour(persona)[0])


def generate_first_daily_plan(persona, wake_up_hour):
    """
    ペルソナの日常計画を生成します。
    基本的には一日の長期計画です。ペルソナが今日行う行動のリストを返します。
    通常、以下の形式で提供されます:
    '6:00 amに起床して朝のルーティンを完了する',
    '7:00 amに朝食を食べる'、など。
    注意: 行動にはピリオドが付きません。

    ペルソナの状態: 身元安定セット、ライフスタイル、現在の日付文字列、名前

    INPUT:
      persona: ペルソナクラスのインスタンス
      wake_up_hour: ペルソナが起きる時間を示す整数
                    (例: 8)
    OUTPUT:
      広範な日常行動のリスト
    例出力:
      ['6:00 amに起床して朝のルーティンを完了する',
       '6:30 amに朝食を取り、歯を磨く',
       '8:00 amから12:00 pmまで絵画プロジェクトに取り組む',
       '12:00 pmに昼食を取る',
       '2:00 pmから4:00 pmまで休憩してテレビを見る',
       '4:00 pmから6:00 pmまで絵画プロジェクトに取り組む',
       '6:00 pmに夕食を取る', '7:00 pmから8:00 pmまでテレビを見る']
    """
    if debug: print("GNS FUNCTION: <generate_first_daily_plan>")
    return run_gpt_prompt_daily_plan(persona, wake_up_hour)[0]


def generate_hourly_schedule(persona, wake_up_hour):
    """
    日常の要求に基づいて、毎時のスケジュールを作成します。一度に1時間ずつ。
    各時間の行動形式は以下のようなものです:
    "ベッドで寝る"

    出力は基本的に、"x は..."というフレーズを完結させることを意味します。

    ペルソナの状態: 身元安定セット、日常計画

    INPUT:
      persona: ペルソナクラスのインスタンス
      wake_up_hour: ペルソナの起床時間を示す整数
    OUTPUT:
      活動とその持続時間を示すリスト
    例出力:
      [['寝る', 360], ['起きて朝のルーティンを始める', 60],
       ['朝食を取る', 60],..
    """
    if debug: print("GNS FUNCTION: <generate_hourly_schedule>")

    hour_str = ["00:00 AM", "01:00 AM", "02:00 AM", "03:00 AM", "04:00 AM",
                "05:00 AM", "06:00 AM", "07:00 AM", "08:00 AM", "09:00 AM",
                "10:00 AM", "11:00 AM", "12:00 PM", "01:00 PM", "02:00 PM",
                "03:00 PM", "04:00 PM", "05:00 PM", "06:00 PM", "07:00 PM",
                "08:00 PM", "09:00 PM", "10:00 PM", "11:00 PM"]
    n_m1_activity = []
    diversity_repeat_count = 3
    for i in range(diversity_repeat_count):
        n_m1_activity_set = set(n_m1_activity)
        if len(n_m1_activity_set) < 5:
            n_m1_activity = []
            for count, curr_hour_str in enumerate(hour_str):
                if wake_up_hour > 0:
                    n_m1_activity += ["sleeping"]
                    wake_up_hour -= 1
                else:
                    n_m1_activity += [run_gpt_prompt_generate_hourly_schedule(
                        persona, curr_hour_str, n_m1_activity, hour_str)[0]]

    # Step 1. Compressing the hourly schedule to the following format:
    # The integer indicates the number of hours. They should add up to 24.
    # [['sleeping', 6], ['waking up and starting her morning routine', 1],
    # ['eating breakfast', 1], ['getting ready for the day', 1],
    # ['working on her painting', 2], ['taking a break', 1],
    # ['having lunch', 1], ['working on her painting', 3],
    # ['taking a break', 2], ['working on her painting', 2],
    # ['relaxing and watching TV', 1], ['going to bed', 1], ['sleeping', 2]]
    _n_m1_hourly_compressed = []
    prev = None
    prev_count = 0
    for i in n_m1_activity:
        if i != prev:
            prev_count = 1
            _n_m1_hourly_compressed += [[i, prev_count]]
            prev = i
        else:
            if _n_m1_hourly_compressed:
                _n_m1_hourly_compressed[-1][1] += 1

    # Step 2. Expand to min scale (from hour scale)
    # [['sleeping', 360], ['waking up and starting her morning routine', 60],
    # ['eating breakfast', 60],..
    n_m1_hourly_compressed = []
    for task, duration in _n_m1_hourly_compressed:
        n_m1_hourly_compressed += [[task, duration * 60]]

    return n_m1_hourly_compressed


def generate_task_decomp(persona, task, duration):
    """
    タスクの説明を与えられたタスクのいくつかのショット分解

    ペルソナの状態: 身元安定セット、現在の日付文字列、名前

    INPUT:
      persona: ペルソナクラスのインスタンス
      task: タスクの説明を文字列形式で与える
            （例：「起きて朝のルーティンを始める」）
      duration: このタスクが継続する時間を示す整数
                （例：60）
    OUTPUT:
      分解されたタスクの説明とその持続時間を含むリストのリスト。
    例出力:
      [['トイレに行く', 5], ['着替える', 5],
       ['朝食を取る', 15], ['メールをチェックする', 5],
       ['日中の準備をする', 15], ['絵画を始める', 15]]
    """
    if debug: print("GNS FUNCTION: <generate_task_decomp>")
    return run_gpt_prompt_task_decomp(persona, task, duration)[0]


def generate_action_sector(act_desp, persona, maze):
    """TODO
    ペルソナとタスクの説明を与えられた場合、アクションセクターを選択します。

    ペルソナの状態: 身元安定セット、n-1日のスケジュール、日常計画

    INPUT:
      act_desp: 新しいアクションの説明（例：「寝る」）
      persona: ペルソナクラスのインスタンス
    OUTPUT:
      action_sector（例：「寝室2」）
    例出力:
      "寝室2"
    """
    if debug: print("GNS FUNCTION: <generate_action_sector>")
    return run_gpt_prompt_action_sector(act_desp, persona, maze)[0]


def generate_action_arena(act_desp, persona, maze, act_world, act_sector):
    """TODO
    ペルソナとタスクの説明を与えられた場合、アクションアリーナを選択します。

    ペルソナの状態: 身元安定セット、n-1日のスケジュール、日常計画

    INPUT:
      act_desp: 新しいアクションの説明（例：「寝る」）
      persona: ペルソナクラスのインスタンス
    OUTPUT:
      action_arena（例：「寝室2」）
    例出力:
      "寝室2"
    """
    if debug: print("GNS FUNCTION: <generate_action_arena>")
    return run_gpt_prompt_action_arena(act_desp, persona, maze, act_world, act_sector)[0]


def generate_action_game_object(act_desp, act_address, persona, maze):
    """TODO
    アクションの説明とアクションアドレス（アクションが行われる予定のアドレス）を与えられた場合、ゲームオブジェクトを選択します。

    ペルソナの状態: 身元安定セット、n-1日のスケジュール、日常計画

    INPUT:
      act_desp: アクションの説明（例：「寝る」）
      act_address: アクションが行われるアリーナのアドレス:
                 （例：「dolores double studio:double studio:bedroom 2」）
      persona: ペルソナクラスのインスタンス
    OUTPUT:
      act_game_object:
    例出力:
      "ベッド"
    """
    if debug: print("GNS FUNCTION: <generate_action_game_object>")
    if not persona.s_mem.get_str_accessible_arena_game_objects(act_address):
        return "<random>"
    return run_gpt_prompt_action_game_object(act_desp, persona, maze, act_address)[0]


def generate_action_pronunciatio(act_desp, persona):
    """TODO
    アクションの説明を与えられた場合、少数のショットプロンプトを通じて絵文字文字列の説明を作成します。

    ペルソナから情報を取得する必要はありません。

    INPUT:
      act_desp: アクションの説明（例：「寝る」）
      persona: ペルソナクラスのインスタンス
    OUTPUT:
      アクションの説明を翻訳する絵文字の文字列
    例出力:
      "🧈🍞"
    """
    if debug: print("GNS FUNCTION: <generate_action_pronunciatio>")
    try:
        x = run_gpt_prompt_pronunciatio(act_desp, persona)[0]
    except:
        x = "🙂"

    if not x:
        return "🙂"
    return x


def generate_action_event_triple(act_desp, persona):
    """TODO
    INPUT:
      act_desp: the description of the action (e.g., "sleeping")
      persona: The Persona class instance
    OUTPUT:
      a string of emoji that translates action description.
    EXAMPLE OUTPUT:
      "🧈🍞"
    """
    if debug: print("GNS FUNCTION: <generate_action_event_triple>")
    return run_gpt_prompt_event_triple(act_desp, persona)[0]


def generate_act_obj_desc(act_game_object, act_desp, persona):
    if debug: print("GNS FUNCTION: <generate_act_obj_desc>")
    return run_gpt_prompt_act_obj_desc(act_game_object, act_desp, persona)[0]


def generate_act_obj_event_triple(act_game_object, act_obj_desc, persona):
    if debug: print("GNS FUNCTION: <generate_act_obj_event_triple>")
    return run_gpt_prompt_act_obj_event_triple(act_game_object, act_obj_desc, persona)[0]


def generate_convo(maze, init_persona, target_persona):
    curr_loc = maze.access_tile(init_persona.scratch.curr_tile)

    # convo = run_gpt_prompt_create_conversation(init_persona, target_persona, curr_loc)[0]
    # convo = agent_chat_v1(maze, init_persona, target_persona)
    convo = agent_chat_v2(maze, init_persona, target_persona)
    all_utt = ""

    for row in convo:
        speaker = row[0]
        utt = row[1]
        all_utt += f"{speaker}: {utt}\n"

    convo_length = math.ceil(int(len(all_utt) / 8) / 30)

    if debug: print("GNS FUNCTION: <generate_convo>")
    return convo, convo_length


def generate_convo_summary(persona, convo):
    convo_summary = run_gpt_prompt_summarize_conversation(persona, convo)[0]
    return convo_summary


def generate_decide_to_talk(init_persona, target_persona, retrieved):
    x = run_gpt_prompt_decide_to_talk(init_persona, target_persona, retrieved)[0]
    if debug: print("GNS FUNCTION: <generate_decide_to_talk>")

    if x == "yes":
        return True
    else:
        return False


def generate_decide_to_react(init_persona, target_persona, retrieved):
    if debug: print("GNS FUNCTION: <generate_decide_to_react>")
    return run_gpt_prompt_decide_to_react(init_persona, target_persona, retrieved)[0]


def generate_new_decomp_schedule(persona, inserted_act, inserted_act_dur, start_hour, end_hour):
    # Step 1: Setting up the core variables for the function.
    # <p> is the persona whose schedule we are editing right now.
    p = persona
    # <today_min_pass> indicates the number of minutes that have passed today.
    today_min_pass = (int(p.scratch.curr_time.hour) * 60
                      + int(p.scratch.curr_time.minute) + 1)

    # Step 2: We need to create <main_act_dur> and <truncated_act_dur>.
    # These are basically a sub-component of <f_daily_schedule> of the persona,
    # but focusing on the current decomposition.
    # Here is an example for <main_act_dur>:
    # ['wakes up and completes her morning routine (wakes up at 6am)', 5]
    # ['wakes up and completes her morning routine (wakes up at 6am)', 5]
    # ['wakes up and completes her morning routine (uses the restroom)', 5]
    # ['wakes up and completes her morning routine (washes her ...)', 10]
    # ['wakes up and completes her morning routine (makes her bed)', 5]
    # ['wakes up and completes her morning routine (eats breakfast)', 15]
    # ['wakes up and completes her morning routine (gets dressed)', 10]
    # ['wakes up and completes her morning routine (leaves her ...)', 5]
    # ['wakes up and completes her morning routine (starts her ...)', 5]
    # ['preparing for her day (waking up at 6am)', 5]
    # ['preparing for her day (making her bed)', 5]
    # ['preparing for her day (taking a shower)', 15]
    # ['preparing for her day (getting dressed)', 5]
    # ['preparing for her day (eating breakfast)', 10]
    # ['preparing for her day (brushing her teeth)', 5]
    # ['preparing for her day (making coffee)', 5]
    # ['preparing for her day (checking her email)', 5]
    # ['preparing for her day (starting to work on her painting)', 5]
    #
    # And <truncated_act_dur> concerns only until where an event happens.
    # ['wakes up and completes her morning routine (wakes up at 6am)', 5]
    # ['wakes up and completes her morning routine (wakes up at 6am)', 2]
    main_act_dur = []
    truncated_act_dur = []
    dur_sum = 0  # duration sum
    count = 0  # enumerate count
    truncated_fin = False

    print("DEBUG::: ", persona.scratch.name)
    for act, dur in p.scratch.f_daily_schedule:
        if (dur_sum >= start_hour * 60) and (dur_sum < end_hour * 60):
            main_act_dur += [[act, dur]]
            if dur_sum <= today_min_pass:
                truncated_act_dur += [[act, dur]]
            elif dur_sum > today_min_pass and not truncated_fin:
                # We need to insert that last act, duration list like this one:
                # e.g., ['wakes up and completes her morning routine (wakes up...)', 2]
                truncated_act_dur += [[p.scratch.f_daily_schedule[count][0],
                                       dur_sum - today_min_pass]]
                truncated_act_dur[-1][-1] -= (
                            dur_sum - today_min_pass)  ######## DEC 7 DEBUG;.. is the +1 the right thing to do???
                # truncated_act_dur[-1][-1] -= (dur_sum - today_min_pass + 1) ######## DEC 7 DEBUG;.. is the +1 the right thing to do???
                print("DEBUG::: ", truncated_act_dur)

                # truncated_act_dur[-1][-1] -= (dur_sum - today_min_pass) ######## DEC 7 DEBUG;.. is the +1 the right thing to do???
                truncated_fin = True
        dur_sum += dur
        count += 1

    persona_name = persona.name
    main_act_dur = main_act_dur

    x = truncated_act_dur[-1][0].split("(")[0].strip() + " (on the way to " + truncated_act_dur[-1][0].split("(")[-1][
                                                                              :-1] + ")"
    truncated_act_dur[-1][0] = x

    if "(" in truncated_act_dur[-1][0]:
        inserted_act = truncated_act_dur[-1][0].split("(")[0].strip() + " (" + inserted_act + ")"

    # To do inserted_act_dur+1 below is an important decision but I'm not sure
    # if I understand the full extent of its implications. Might want to
    # revisit.
    truncated_act_dur += [[inserted_act, inserted_act_dur]]
    start_time_hour = (datetime.datetime(2022, 10, 31, 0, 0)
                       + datetime.timedelta(hours=start_hour))
    end_time_hour = (datetime.datetime(2022, 10, 31, 0, 0)
                     + datetime.timedelta(hours=end_hour))

    if debug: print("GNS FUNCTION: <generate_new_decomp_schedule>")
    return run_gpt_prompt_new_decomp_schedule(persona,
                                              main_act_dur,
                                              truncated_act_dur,
                                              start_time_hour,
                                              end_time_hour,
                                              inserted_act,
                                              inserted_act_dur)[0]


def generate_action_game_object_v2(act_game_object, inserted_act, current_state, persona, maze, act_address_):
    """
    アクションの説明とアクションアドレス（アクションが行われる予定のアドレス）を与えられた場合、ゲームオブジェクトを選択します。
    """
    if debug: print("GNS FUNCTION: <generate_action_game_object>")
    if not persona.s_mem.get_str_accessible_arena_game_objects(act_address_):
        return "<random>"
    return run_gpt_prompt_action_game_object_v2(act_game_object, inserted_act, current_state, persona, maze, act_address_)[0]


def generate_action_sector_v2(act_game_object, inserted_act, current_state, persona, maze, new_address):
    """
    :param act_game_object: cooking area
    :param inserted_act: ペルソナの行動
    :param current_state: 対象オブジェクトの状態
    :param persona:
    :param maze:
    :param new_address: 対象オブジェクトのフルアドレス
    :return:
    """
    if debug: print("GNS FUNCTION: <generate_action_sector_v2>")
    return run_gpt_prompt_action_sector_v2(act_game_object, inserted_act, current_state, persona, maze, new_address)[0]


def generate_action_arena_v2(act_game_object, inserted_act, current_state, persona, maze, act_world, act_sector, new_address):
    if debug: print("GNS FUNCTION: <generate_action_arena_v2>")
    return run_gpt_prompt_action_arena_v2(act_game_object, inserted_act, current_state, persona, maze, act_world, act_sector, new_address)[0]


##############################################################################
# CHAPTER 3: Plan
##############################################################################

def revise_identity(persona):
    p_name = persona.scratch.name

    focal_points = [f"{p_name}'s plan for {persona.scratch.get_str_curr_date_str()}.",
                    f"Important recent events for {p_name}'s life."]
    retrieved = new_retrieve(persona, focal_points)

    statements = "[Statements]\n"
    for key, val in retrieved.items():
        for i in val:
            statements += f"{i.created.strftime('%A %B %d -- %H:%M %p')}: {i.embedding_key}\n"

    # print (";adjhfno;asdjao;idfjo;af", p_name)
    plan_prompt = statements + "\n"
    plan_prompt += f"Given the statements above, is there anything that {p_name} should remember as they plan for"
    plan_prompt += f" *{persona.scratch.curr_time.strftime('%A %B %d')}*? "
    plan_prompt += f"If there is any scheduling information, be as specific as possible (include date, time, and location if stated in the statement)\n\n"
    plan_prompt += f"Write the response from {p_name}'s perspective."
    plan_note = ChatGPT_single_request(plan_prompt)
    # print (plan_note)

    thought_prompt = statements + "\n"
    thought_prompt += f"Given the statements above, how might we summarize {p_name}'s feelings about their days up to now?\n\n"
    thought_prompt += f"Write the response from {p_name}'s perspective."
    thought_note = ChatGPT_single_request(thought_prompt)
    # print (thought_note)

    currently_prompt = f"{p_name}'s status from {(persona.scratch.curr_time - datetime.timedelta(days=1)).strftime('%A %B %d')}:\n"
    currently_prompt += f"{persona.scratch.currently}\n\n"
    currently_prompt += f"{p_name}'s thoughts at the end of {(persona.scratch.curr_time - datetime.timedelta(days=1)).strftime('%A %B %d')}:\n"
    currently_prompt += (plan_note + thought_note).replace('\n', '') + "\n\n"
    currently_prompt += f"It is now {persona.scratch.curr_time.strftime('%A %B %d')}. Given the above, write {p_name}'s status for {persona.scratch.curr_time.strftime('%A %B %d')} that reflects {p_name}'s thoughts at the end of {(persona.scratch.curr_time - datetime.timedelta(days=1)).strftime('%A %B %d')}. Write this in third-person talking about {p_name}."
    currently_prompt += f"If there is any scheduling information, be as specific as possible (include date, time, and location if stated in the statement).\n\n"
    currently_prompt += "Follow this format below:\nStatus: <new status>"
    # print ("DEBUG ;adjhfno;asdjao;asdfsidfjo;af", p_name)
    # print (currently_prompt)
    new_currently = ChatGPT_single_request(currently_prompt)
    # print (new_currently)
    # print (new_currently[10:])

    persona.scratch.currently = new_currently

    daily_req_prompt = persona.scratch.get_str_iss() + "\n"
    daily_req_prompt += f"Today is {persona.scratch.curr_time.strftime('%A %B %d')}. Here is {persona.scratch.name}'s plan today in broad-strokes (with the time of the day. e.g., have a lunch at 12:00 pm, watch TV from 7 to 8 pm).\n\n"
    daily_req_prompt += f"Follow this format (the list should have 4~6 items but no more):\n"
    daily_req_prompt += f"1. wake up and complete the morning routine at <time>, 2. ..."

    new_daily_req = ChatGPT_single_request(daily_req_prompt)
    new_daily_req = new_daily_req.replace('\n', ' ')
    print("WE ARE HERE!!!", new_daily_req)
    persona.scratch.daily_plan_req = new_daily_req


def _long_term_planning(persona, new_day):
    """
    Formulates the persona's daily long-term plan if it is the start of a new
    day. This basically has two components: first, we create the wake-up hour,
    and second, we create the hourly schedule based on it.
    INPUT
      new_day: Indicates whether the current time signals a "First day",
               "New day", or False (for neither). This is important because we
               create the personas' long term planning on the new day.
    """
    # TODO ここ時間かかるので，一応ログ取ってそれを再利用できるようにしてる．もしライフスタイルを変えて，1日の計画自体を変えたい時はこの実装を変更
    # ファイルのパスを定義
    plan_file_path = f"frontend/storage/plans/{persona.scratch.name}_plan.txt"
    thought_file_path = f"frontend/storage/thoughts/{persona.scratch.name}_thought.pkl"

    # 既に計画がファイルに存在する場合、その計画を読み込んで使用
    if os.path.exists(plan_file_path):
        with open(plan_file_path, 'r') as plan_file:
            plan_data = plan_file.read().splitlines()
            persona.scratch.daily_req = plan_data[0].split(', ')
            persona.scratch.f_daily_schedule = eval(plan_data[1])
            persona.scratch.f_daily_schedule_hourly_org = persona.scratch.f_daily_schedule[:]

        # thought情報も読み込む
        if os.path.exists(thought_file_path):
            with open(thought_file_path, 'rb') as thought_file:
                thought_info = pickle.load(thought_file)
                thought, created, expiration, keywords, thought_poignancy, thought_embedding_pair, s, p, o = thought_info
                persona.a_mem.add_thought(created, expiration, s, p, o,
                                          thought, keywords, thought_poignancy,
                                          thought_embedding_pair, None)
    else:
        # We start by creating the wake up hour for the persona.
        wake_up_hour = generate_wake_up_hour(persona)

        # When it is a new day, we start by creating the daily_req of the persona.
        # Note that the daily_req is a list of strings that describe the persona's
        # day in broad strokes.
        if new_day == "First day":
            # Bootstrapping the daily plan for the start of then generation:
            # if this is the start of generation (so there is no previous day's
            # daily requirement, or if we are on a new day, we want to create a new
            # set of daily requirements.
            persona.scratch.daily_req = generate_first_daily_plan(persona,
                                                                  wake_up_hour)
        elif new_day == "New day":
            revise_identity(persona)

            # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - TODO
            # We need to create a new daily_req here...
            persona.scratch.daily_req = persona.scratch.daily_req

        # Based on the daily_req, we create an hourly schedule for the persona,
        # which is a list of todo items with a time duration (in minutes) that
        # add up to 24 hours.
        persona.scratch.f_daily_schedule = generate_hourly_schedule(persona,
                                                                    wake_up_hour)
        persona.scratch.f_daily_schedule_hourly_org = (persona.scratch
                                                       .f_daily_schedule[:])

        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(plan_file_path), exist_ok=True)
        # 計画をファイルに保存
        with open(plan_file_path, 'w') as plan_file:
            plan_file.write(', '.join(persona.scratch.daily_req) + '\n')
            plan_file.write(str(persona.scratch.f_daily_schedule) + '\n')

        # Added March 4 -- adding plan to the memory.
        thought = f"This is {persona.scratch.name}'s plan for {persona.scratch.curr_time.strftime('%A %B %d')}:"
        for i in persona.scratch.daily_req:
            thought += f" {i},"
        thought = thought[:-1] + "."
        created = persona.scratch.curr_time
        expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
        s, p, o = (persona.scratch.name, "plan", persona.scratch.curr_time.strftime('%A %B %d'))
        keywords = set(["plan"])
        thought_poignancy = 5
        thought_embedding_pair = (thought, get_embedding(thought))
        persona.a_mem.add_thought(created, expiration, s, p, o,
                                  thought, keywords, thought_poignancy,
                                  thought_embedding_pair, None)

        # Thought情報をファイルに保存
        os.makedirs(os.path.dirname(thought_file_path), exist_ok=True)
        thought_info = (thought, created, expiration, keywords, thought_poignancy, thought_embedding_pair, s, p, o)
        with open(thought_file_path, 'wb') as thought_file:
            pickle.dump(thought_info, thought_file)
    # print("Sleeping for 20 seconds...")
    # time.sleep(10)
    # print("Done sleeping!")


def _determine_action(persona, maze):
    """
    ペルソナの次のアクションシーケンスを作成します。
    この関数の主な目的は、ペルソナのスクラッチスペースに「add_new_action」を実行することです。
    これにより、次のアクションに関連するすべての変数が設定されます。
    これの一環として、必要に応じてペルソナの毎時スケジュールを分解する必要があります。
    INPUT
      persona: アクションを決定している現在の<ペルソナ>インスタンス。
      maze: 現在の<Maze>インスタンス。
    """

    def determine_decomp(act_desp, act_dura):
        """
        アクションの説明とその持続時間を与えられた場合、分解が必要かどうかを判断します。
        エージェントが寝ている場合、通常は分解を行いたくないため、ここでそれをキャッチします。

        INPUT:
          act_desp: アクションの説明（例：「寝る」）
          act_dura: アクションの持続時間を分で示す。
        OUTPUT:
          ブール値。分解が必要な場合はTrue、そうでない場合はFalse。
        """
        if "sleep" not in act_desp and "bed" not in act_desp:
            return True
        elif "sleeping" in act_desp or "asleep" in act_desp or "in bed" in act_desp:
            return False
        elif "sleep" in act_desp or "bed" in act_desp:
            if act_dura > 60:
                return False
        return True

    # この関数の目的は<curr_index>に関連付けられたアクションを取得することです。
    # これの一環として、一部の大規模なチャンクアクションを分解する必要があります。
    # 重要なことに、いつでも少なくとも2時間分のスケジュールを分解しようとします。
    curr_index = persona.scratch.get_f_daily_schedule_index()
    curr_index_60 = persona.scratch.get_f_daily_schedule_index(advance=60)

    # * Decompose *
    # 1日の最初の時間に、2時間分のシーケンスを分解する必要があります。ここでそれを行います。
    if curr_index == 0:
        # これは1日の最初の時間である場合に呼び出されます。
        act_desp, act_dura = persona.scratch.f_daily_schedule[curr_index]
        if act_dura >= 60:
            # 次のアクションが1時間を超える場合、determine_decompで記述されている基準に一致する場合は分解します
            if determine_decomp(act_desp, act_dura):
                persona.scratch.f_daily_schedule[curr_index:curr_index + 1] = (
                    generate_task_decomp(persona, act_desp, act_dura))
        if curr_index_60 + 1 < len(persona.scratch.f_daily_schedule):
            act_desp, act_dura = persona.scratch.f_daily_schedule[curr_index_60 + 1]
            if act_dura >= 60:
                if determine_decomp(act_desp, act_dura):
                    persona.scratch.f_daily_schedule[curr_index_60 + 1:curr_index_60 + 2] = (
                        generate_task_decomp(persona, act_desp, act_dura))

    if curr_index_60 < len(persona.scratch.f_daily_schedule):
        # 1日の最初の時間でない場合、これは常に呼び出されます（1日の最初の時間中にも呼び出されます）。
        # もちろん、分解するものがある場合にのみ、これをチェックします。
        if persona.scratch.curr_time.hour < 23:
            # また、午後11時以降は分解したくありません。
            act_desp, act_dura = persona.scratch.f_daily_schedule[curr_index_60]
            if act_dura >= 60:
                if determine_decomp(act_desp, act_dura):
                    persona.scratch.f_daily_schedule[curr_index_60:curr_index_60 + 1] = (
                        generate_task_decomp(persona, act_desp, act_dura))
    # * End of Decompose *

    # アクションの説明と持続時間から<Action>インスタンスを生成します。この時点で、
    # 関連するすべてのアクションが分解され、f_daily_scheduleに準備されていると想定します。
    print("DEBUG LJSDLFSKJF")
    for i in persona.scratch.f_daily_schedule: print(i)
    print(curr_index)
    print(len(persona.scratch.f_daily_schedule))
    print(persona.scratch.name)
    print("------")

    # 1440
    x_emergency = 0
    for i in persona.scratch.f_daily_schedule:
        x_emergency += i[1]
    # print ("x_emergency", x_emergency)

    if 1440 - x_emergency > 0:
        print("x_emergency__AAA", x_emergency)
    persona.scratch.f_daily_schedule += [["sleeping", 1440 - x_emergency]]

    act_desp, act_dura = persona.scratch.f_daily_schedule[curr_index]

    # Finding the target location of the action and creating action-related
    # variables.
    act_world = maze.access_tile(persona.scratch.curr_tile)["world"]
    # act_sector = maze.access_tile(persona.scratch.curr_tile)["sector"]
    act_sector = generate_action_sector(act_desp, persona, maze)
    act_arena = generate_action_arena(act_desp, persona, maze, act_world, act_sector)
    act_address = f"{act_world}:{act_sector}:{act_arena}"
    act_game_object = generate_action_game_object(act_desp, act_address,
                                                  persona, maze)
    new_address = f"{act_world}:{act_sector}:{act_arena}:{act_game_object}"
    act_pron = generate_action_pronunciatio(act_desp, persona)
    act_event = generate_action_event_triple(act_desp, persona)
    # Persona's actions also influence the object states. We set those up here.
    act_obj_desp = generate_act_obj_desc(act_game_object, act_desp, persona)
    act_obj_pron = generate_action_pronunciatio(act_obj_desp, persona)
    act_obj_event = generate_act_obj_event_triple(act_game_object,
                                                  act_obj_desp, persona)

    # Adding the action to persona's queue.
    persona.scratch.add_new_action(new_address,
                                   int(act_dura),
                                   act_desp,
                                   act_pron,
                                   act_event,
                                   None,
                                   None,
                                   None,
                                   None,
                                   act_obj_desp,
                                   act_obj_pron,
                                   act_obj_event)


def _choose_retrieved(persona, retrieved):
    """
     検索された要素には複数のコア「curr_events」があります。反応するイベントを選びます。
    INPUT
      persona: 現在の<ペルソナ>インスタンス
      retrieved: ペルソナの連想記憶から検索された<ConceptNode>の辞書。
                 この辞書は次の形式をとります:
                 dictionary[event.description] =
                   {["curr_event"] = <ConceptNode>,
                    ["events"] = [<ConceptNode>, ...],
                    ["thoughts"] = [<ConceptNode>, ...] }
    """
    # 反省が終わったら、ここでより複雑な構造を作成したいかもしれません。
    #
    # 自己イベントを取得したくないので、ここでフィルタリングします。
    copy_retrieved = retrieved.copy()
    for event_desc, rel_ctx in copy_retrieved.items():
        curr_event = rel_ctx["curr_event"]
        if curr_event.subject == persona.name:
            del retrieved[event_desc]

    # 最初にペルソナを選択
    priority = []
    for event_desc, rel_ctx in retrieved.items():
        curr_event = rel_ctx["curr_event"]
        if (":" not in curr_event.subject
                and curr_event.subject != persona.name):
            priority += [rel_ctx]
    if priority:
        return random.choice(priority)

    # 待機中のものはスキップ
    for event_desc, rel_ctx in retrieved.items():
        curr_event = rel_ctx["curr_event"]
        if "is idle" not in event_desc:
            priority += [rel_ctx]
    if priority:
        return random.choice(priority)
    return None


def _should_react(persona, retrieved, personas):
    """
    検索された値を考慮して、ペルソナがどの形式の反応を示すべきかを決定します。
    INPUT
      persona: 現在の<ペルソナ>インスタンス
      retrieved: ペルソナの連想記憶から検索された<ConceptNode>の辞書。
                 この辞書は次の形式をとります:
                 dictionary[event.description] =
                   {["curr_event"] = <ConceptNode>,
                    ["events"] = [<ConceptNode>, ...],
                    ["thoughts"] = [<ConceptNode>, ...] }
      personas: ペルソナ名をキー、<ペルソナ>インスタンスを値として含む辞書。
    """

    def lets_talk(init_persona, target_persona, retrieved):
        if (not target_persona.scratch.act_address
                or not target_persona.scratch.act_description
                or not init_persona.scratch.act_address
                or not init_persona.scratch.act_description):
            return False

        if ("sleeping" in target_persona.scratch.act_description
                or "sleeping" in init_persona.scratch.act_description):
            return False

        if init_persona.scratch.curr_time.hour == 23:
            return False

        if "<waiting>" in target_persona.scratch.act_address:
            return False

        if (target_persona.scratch.chatting_with
                or init_persona.scratch.chatting_with):
            return False

        if (target_persona.name in init_persona.scratch.chatting_with_buffer):
            if init_persona.scratch.chatting_with_buffer[target_persona.name] > 0:
                return False

        if generate_decide_to_talk(init_persona, target_persona, retrieved):
            return True

        return False

    def lets_react(init_persona, target_persona, retrieved):
        if (not target_persona.scratch.act_address
                or not target_persona.scratch.act_description
                or not init_persona.scratch.act_address
                or not init_persona.scratch.act_description):
            return False

        if ("sleeping" in target_persona.scratch.act_description
                or "sleeping" in init_persona.scratch.act_description):
            return False

        # return False
        if init_persona.scratch.curr_time.hour == 23:
            return False

        if "waiting" in target_persona.scratch.act_description:
            return False
        if init_persona.scratch.planned_path == []:
            return False

        if (init_persona.scratch.act_address
                != target_persona.scratch.act_address):
            return False

        react_mode = generate_decide_to_react(init_persona,
                                              target_persona, retrieved)

        if react_mode == "1":
            wait_until = ((target_persona.scratch.act_start_time
                           + datetime.timedelta(minutes=target_persona.scratch.act_duration - 1))
                          .strftime("%B %d, %Y, %H:%M:%S"))
            return f"wait: {wait_until}"
        elif react_mode == "2":
            return False
            return "do other things"
        else:
            return False  # "keep"

    # If the persona is chatting right now, default to no reaction
    if persona.scratch.chatting_with:
        return False
    if "<waiting>" in persona.scratch.act_address:
        return False

    # Recall that retrieved takes the following form:
    # dictionary {["curr_event"] = <ConceptNode>,
    #             ["events"] = [<ConceptNode>, ...],
    #             ["thoughts"] = [<ConceptNode>, ...]}
    curr_event = retrieved["curr_event"]

    # アクシデントイベントの場合の反応を追加
    # fire, burn, flameの文字が入ってたらアクシデントとする．
    # log_to_file('current_event.txt', f"current_event: {curr_event}\n")
    if "fire" in curr_event.description or "burn" in curr_event.description or "flame" in curr_event.description:
        return "accident"

    if ":" not in curr_event.subject:
        # this is a persona event.
        if lets_talk(persona, personas[curr_event.subject], retrieved):
            return f"chat with {curr_event.subject}"
        react_mode = lets_react(persona, personas[curr_event.subject],
                                retrieved)
        return react_mode
    return False


def _create_react(persona, inserted_act, inserted_act_dur,
                  act_address, act_event, chatting_with, chat, chatting_with_buffer,
                  chatting_end_time,
                  act_pronunciatio, act_obj_description, act_obj_pronunciatio,
                  act_obj_event, act_start_time=None):
    """エージェントの行動を更新し、新しいアクションをスケジュールに追加するためのもの"""
    p = persona

    min_sum = 0
    for i in range(p.scratch.get_f_daily_schedule_hourly_org_index()):
        min_sum += p.scratch.f_daily_schedule_hourly_org[i][1]
    # start_hour は、スケジュールの開始時間を計算します。
    start_hour = int(min_sum / 60)

    if (p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()][1] >= 120):
        end_hour = start_hour + \
                   p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()][1] / 60

    elif (p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()][1] +
          p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index() + 1][1]):
        end_hour = start_hour + (
                    (p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()][1] +
                     p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index() + 1][
                         1]) / 60)

    else:
        end_hour = start_hour + 2
    end_hour = int(end_hour)

    dur_sum = 0
    count = 0
    start_index = None
    end_index = None
    for act, dur in p.scratch.f_daily_schedule:
        if dur_sum >= start_hour * 60 and start_index == None:
            start_index = count
        if dur_sum >= end_hour * 60 and end_index == None:
            end_index = count
        dur_sum += dur
        count += 1

    ret = generate_new_decomp_schedule(p, inserted_act, inserted_act_dur,
                                       start_hour, end_hour)
    p.scratch.f_daily_schedule[start_index:end_index] = ret
    p.scratch.add_new_action(act_address,  # ここフルアドレス説っぽい？
                             inserted_act_dur,
                             inserted_act,
                             act_pronunciatio,
                             act_event,
                             chatting_with,
                             chat,
                             chatting_with_buffer,
                             chatting_end_time,
                             act_obj_description,
                             act_obj_pronunciatio,
                             act_obj_event,
                             act_start_time)

def _create_react_v2(persona, inserted_act, inserted_act_dur,
                  act_address, act_event, chatting_with, chat, chatting_with_buffer,
                  chatting_end_time,
                  act_pronunciatio, act_obj_description, act_obj_pronunciatio,
                  act_obj_event, act_start_time=None):
    """エージェントの行動を更新し、新しいアクションをスケジュールに追加するためのもの"""
    p = persona

    min_sum = 0
    for i in range(p.scratch.get_f_daily_schedule_hourly_org_index()):
        min_sum += p.scratch.f_daily_schedule_hourly_org[i][1]
    # start_hour は、スケジュールの開始時間を計算します。
    start_hour = int(min_sum / 60)

    if (p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()][1] >= 120):
        end_hour = start_hour + \
                   p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()][1] / 60

    elif (p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()][1] +
          p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index() + 1][1]):
        end_hour = start_hour + (
                    (p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()][1] +
                     p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index() + 1][
                         1]) / 60)

    else:
        end_hour = start_hour + 2
    end_hour = int(end_hour)

    dur_sum = 0
    count = 0
    start_index = None
    end_index = None
    for act, dur in p.scratch.f_daily_schedule:
        if dur_sum >= start_hour * 60 and start_index == None:
            start_index = count
        if dur_sum >= end_hour * 60 and end_index == None:
            end_index = count
        dur_sum += dur
        count += 1

    ret = generate_new_decomp_schedule(p, inserted_act, inserted_act_dur,
                                       start_hour, end_hour)
    p.scratch.f_daily_schedule[start_index:end_index] = ret


def _chat_react(maze, persona, focused_event, reaction_mode, personas):
    # There are two personas -- the persona who is initiating the conversation
    # and the persona who is the target. We get the persona instances here.
    init_persona = persona
    target_persona = personas[reaction_mode[9:].strip()]
    curr_personas = [init_persona, target_persona]

    # Actually creating the conversation here.
    convo, duration_min = generate_convo(maze, init_persona, target_persona)
    convo_summary = generate_convo_summary(init_persona, convo)
    inserted_act = convo_summary
    inserted_act_dur = duration_min

    act_start_time = target_persona.scratch.act_start_time

    curr_time = target_persona.scratch.curr_time
    if curr_time.second != 0:
        temp_curr_time = curr_time + datetime.timedelta(seconds=60 - curr_time.second)
        chatting_end_time = temp_curr_time + datetime.timedelta(minutes=inserted_act_dur)
    else:
        chatting_end_time = curr_time + datetime.timedelta(minutes=inserted_act_dur)

    for role, p in [("init", init_persona), ("target", target_persona)]:
        if role == "init":
            act_address = f"<persona> {target_persona.name}"
            act_event = (p.name, "chat with", target_persona.name)
            chatting_with = target_persona.name
            chatting_with_buffer = {}
            chatting_with_buffer[target_persona.name] = 800
        elif role == "target":
            act_address = f"<persona> {init_persona.name}"
            act_event = (p.name, "chat with", init_persona.name)
            chatting_with = init_persona.name
            chatting_with_buffer = {}
            chatting_with_buffer[init_persona.name] = 800

        act_pronunciatio = "💬"
        act_obj_description = None
        act_obj_pronunciatio = None
        act_obj_event = (None, None, None)

        _create_react(p, inserted_act, inserted_act_dur,
                      act_address, act_event, chatting_with, convo, chatting_with_buffer, chatting_end_time,
                      act_pronunciatio, act_obj_description, act_obj_pronunciatio,
                      act_obj_event, act_start_time)




def _wait_react(persona, reaction_mode):
    p = persona

    inserted_act = f'waiting to start {p.scratch.act_description.split("(")[-1][:-1]}'
    end_time = datetime.datetime.strptime(reaction_mode[6:].strip(), "%B %d, %Y, %H:%M:%S")
    inserted_act_dur = (end_time.minute + end_time.hour * 60) - (
                p.scratch.curr_time.minute + p.scratch.curr_time.hour * 60) + 1

    act_address = f"<waiting> {p.scratch.curr_tile[0]} {p.scratch.curr_tile[1]}"
    act_event = (p.name, "waiting to start", p.scratch.act_description.split("(")[-1][:-1])
    chatting_with = None
    chat = None
    chatting_with_buffer = None
    chatting_end_time = None

    act_pronunciatio = "⌛"
    act_obj_description = None
    act_obj_pronunciatio = None
    act_obj_event = (None, None, None)

    _create_react(p, inserted_act, inserted_act_dur,
                  act_address, act_event, chatting_with, chat, chatting_with_buffer, chatting_end_time,
                  act_pronunciatio, act_obj_description, act_obj_pronunciatio, act_obj_event)


previously_added_events = []
def _accident_react(maze, persona, focused_event, reaction_mode):
    """アクシデントに対応するリアクション"""

    # act_world = maze.access_tile(persona.scratch.curr_tile)["world"]
    # act_sector = maze.access_tile(persona.scratch.curr_tile)["sector"]
    # ほんとは操作する対象オブジェクトは動的に作りたかったけど，意味のわからないオブジェクトを操作始めるのでやめ
    # act_sector = generate_action_sector(inserted_act, persona, maze)
    # act_arena = generate_action_arena(inserted_act, persona, maze, act_world, act_sector)
    # act_address = f"{act_world}:{act_sector}:{act_arena}"
    act_address = "the Ville:Hobbs Cafe:cafe"

    # act_game_object = generate_action_game_object("cooking area" + inserted_act, act_address, persona, maze)
    act_game_object = "cooking area"
    # act_game_object ="behind the cafe counter"

    # location = location_.split(":")[-1]  # 最後だけ抽出

    new_address = "the Ville:Hobbs Cafe:cafe:cooking area"
    # new_address = "the Ville:Hobbs Cafe:cafe:behind the cafe counter"

    # アクシデントの具体的な対応内容を設定
    # ここはアクシデントの対応はペルソナの性格によるようにしたい
    inserted_act, _ = run_gpt_prompt_act_obj_innate_desc(act_game_object, "being on fire", persona)

    # アクション時間を動的に求める
    inserted_act_dur, _ = run_gpt_prompt_get_action_duration(persona, act_game_object, inserted_act)  # アクションの持続時間を分単位で設定
    # 短すぎるとシミュレーション時間が長くなるので最低15分
    if inserted_act_dur < 5:
        inserted_act_dur = 5

    if inserted_act_dur > 15:
        inserted_act_dur = 15

    # ここに対象のオブジェクトの状態をタイルから得るコードを入れる
    current_state = maze.get_object_current_state(new_address)
    if current_state is None:
        current_state = "unknown"  # デフォルトの状態を設定するか、エラーハンドリングを追加
        print("masakadaro")

    # アクションのアドレスを設定
    # act_address = location_
    # new_address = f"{act_world}:{act_sector}:{act_arena}:{act_game_object}"
    # log_to_file('accident_act_address.txt', f"act_address: {new_address}\n")
    act_obj_event = generate_act_obj_event_triple(act_game_object, inserted_act, persona)

    print("アクシデントにより生成されたイベントトリプル")
    act_event = generate_action_event_triple(inserted_act, persona)
    # Persona's actions also influence the object states. We set those up here.
    act_obj_desp = generate_act_obj_desc(act_game_object, inserted_act, persona)

    # TODO ここはもっとわかりやすく，ペルソナの感情を表す絵文字を出すようにしないと
    act_obj_pronunciatio = generate_action_pronunciatio(act_obj_desp, persona)

    chatting_with = None
    chat = None
    chatting_with_buffer = {}
    chatting_end_time = persona.scratch.curr_time + datetime.timedelta(minutes=inserted_act_dur)

    # アクションのその他の属性を設定
    act_pronunciatio = generate_action_pronunciatio(inserted_act, persona)
    act_obj_description = focused_event['curr_event'].description
    # act_obj_pronunciatio = None
    # act_obj_event の生成
    # act_obj_event = generate_act_obj_event_triple(location, act_obj_description, persona)

    # TODO オブジェクトの状態を変えるのはcooking areaだけだけど，移動先はそれによらない気がする

    # 行動を起こす場所だけ取得
    act_world_ = maze.access_tile(persona.scratch.curr_tile)["world"]
    # act_sector_ = maze.access_tile(persona.scratch.curr_tile)["sector"]
    # 火事のオブジェクトのフルアクセスと，ペルソナ，とその行動，あと移動可能先セクター
    act_sector_ = generate_action_sector_v2(act_game_object, inserted_act, current_state, persona, maze, new_address)
    # TODO ここで得られるarenaのレベルがgema_objectになってる
    act_arena_ = generate_action_arena_v2(act_game_object, inserted_act, current_state, persona, maze, act_world_, act_sector_, new_address)
    if act_sector_ == "Ryan Park's apartment":
        if act_arena_ == "cooking area":
            act_arena_ = "main room"
    elif act_sector_ == "Hobbs Cafe":
        if act_arena_ == "cooking area":
            act_arena_ = "cafe"
    act_address_ = f"{act_world_}:{act_sector_}:{act_arena_}"
    act_game_object_ = generate_action_game_object_v2(act_game_object, inserted_act, current_state, persona, maze, act_address_)
    new_address_ = f"{act_world_}:{act_sector_}:{act_arena_}:{act_game_object_}"

    # エージェントの行動によって，オブジェクトの状態がどうなるかを決定する
    updated_obj_state, _ = run_gpt_prompt_update_obj_state(persona, act_game_object, current_state, inserted_act, new_address_)


    # -------------------------------------------------------------------------

    # ログをファイルに残す
    log_content = (
        f"ペルソナの名前：{persona.name}\n"
        f"アクションの説明：{inserted_act}\n"
        f"アクションの持続時間：{inserted_act_dur}分\n"
        f"アクションのオブジェクト: {act_game_object}\n"
        f"対象オブジェクト(cooking area)の現在の状態: {current_state}\n"
        f"アクションによって影響があるオブジェクトのアドレス：{new_address}\n"
        f"行動する先のアドレス：{new_address_}\n"
        f"アクションのイベント：{act_event}\n"
        f"アクションのオブジェクトイベント：{act_obj_event}\n"
        f"アクションのオブジェクト説明(act_obj_desp)：{act_obj_desp}\n"
        f"アクションのオブジェクト説明(act_obj_description)：{act_obj_description}\n"
        f"アクションのオブジェクト発音：{act_obj_pronunciatio}\n"
        f"アクションの発音: {act_pronunciatio}\n"
        f"行動後のオブジェクトの状態: {updated_obj_state}\n"
    )
    # log_to_file("iroiro.txt", log_content)

    # エージェントの行動によって，オブジェクトの状態を動的に変更する部分
    locations = maze.get_tiles_by_object_v2(new_address)

    # TODO タイルのイベント追加がうまくいってない，いらんところにcooking are is on fireが保存されて，その時のオブジェクト名は存在しない
    if locations:
        for location in locations:
            # 現在のイベントを削除
            maze.remove_event_from_tile((new_address, None, None, None), location)

            # これで無理やり追加したアクシデントは消す
            # TODO 動的に全ての既存の対象アドレスのイベントは削除すべき？
            # ('the Ville:Hobbs Cafe:cafe:cooking area', 'catches', 'fire', 'on fire')
            # maze.remove_event_from_tile((new_address, "catches", "on fire", f"on fire"), location)

            # 消火された場合のみタイルイベントを削除
            if (("idle" in updated_obj_state or
                 "safe" in updated_obj_state or
                 "extinguished" in updated_obj_state or
                 "clean" in updated_obj_state or
                 "calm" in updated_obj_state) and
                "escap" not in updated_obj_state and
                "flee" not in updated_obj_state
                 ):
                maze.turn_event_from_tile_idle((new_address, None, None, None), location)
                maze.remove_event_from_tile((new_address, "is being", "on fire", "on fire"), location)
                # 以前追加したイベントを削除
                for event in previously_added_events:
                    maze.remove_event_from_tile(event, location)
            else:
                # 新しいイベントを追加
                description = f"{updated_obj_state} by {persona.name}"
                # print("watasidesu", description)

                new_event = (new_address, "is", updated_obj_state, description)
                maze.add_event_from_tile(new_event, location)

                # 追加したイベントをリストに記録
                previously_added_events.append(new_event)

    # 移動先の指定はここじゃなかった
    persona.scratch.add_new_action(new_address_,
                                   int(inserted_act_dur),
                                   inserted_act,
                                   act_pronunciatio,
                                   act_event,
                                   None,
                                   None,
                                   None,
                                   None,
                                   act_obj_desp,
                                   act_obj_pronunciatio,
                                   act_obj_event)

    # _create_reactメソッドを呼び出して、アクションを実行
    _create_react_v2(
        persona,
        inserted_act,
        inserted_act_dur,
        new_address_,  # TODO 移動先はこれ？
        act_event,
        chatting_with,
        chat,
        chatting_with_buffer,
        chatting_end_time,
        act_pronunciatio,
        act_obj_description,
        act_obj_pronunciatio,
        act_obj_event
    )


def plan(persona, maze, personas, new_day, retrieved):
    """
    エージェントののメイン認知機能。これにより、検索された記憶と知覚、迷路、および最初の日の状態を使用して、
    ペルソナの長期計画と短期計画の両方を実行します。

    INPUT:
      maze: 世界の現在の<Maze>インスタンス。
      personas: ペルソナ名をキー、Personaインスタンスを値として含む辞書。
      new_day: これは3つの値のいずれかを取ることができます。
        1) <ブール> False -- 「新しい日」サイクルではありません（そうであれば、
           ペルソナの長期計画シーケンスを呼び出す必要があります）。
        2) <文字列>「最初の日」 -- シミュレーションの開始日です。
           したがって、新しい日であるだけでなく、最初の日でもあります。
        2) <文字列>「新しい日」 -- 新しい日です。
      retrieved: 辞書の辞書。最初のレイヤーはイベントを指定し、後者のレイヤーは
                 「curr_event」、「events」、および関連する「thoughts」を指定します。
    OUTPUT
      ペルソナのターゲットアクションアドレス（persona.scratch.act_address）。
    """
    # PART 1: 時間ごとのスケジュールを生成する
    # print("First")
    if new_day:
        print("new day")
        _long_term_planning(persona, new_day)

    # PART 2: 現在のアクションが終了してる場合，新しい計画を作成
    # print("second")
    if persona.scratch.act_check_finished():
        print("persona.scratch.act_check_finished  wayyyyyy")
        _determine_action(persona, maze)

    # PART 3: イベントを知覚し，それに対応する必要がある場合(他のペルソナをみた場合),および関連情報を検索した場合．
    # Step 1: 検索されたデータには複数のイベントが表示される場合があります。
    #         ここでの最初の仕事は、ペルソナに対してどのイベントに焦点を当てるかを決定することです。
    #         <focused_event>は次の形式の辞書を取ります:
    #         辞書 {["curr_event"] = <ConceptNode>,
    #               ["events"] = [<ConceptNode>, ...],
    #               ["thoughts"] = [<ConceptNode>, ...]}
    # log_to_file('retrieved.txt', f"retrieved: {retrieved}\n")
    # print("Third")
    focused_event = False
    if retrieved.keys():
        print("retrieved.key")
        focused_event = _choose_retrieved(persona, retrieved)
    # log_to_file('focused_event.txt', f"focused_event: {focused_event}\n")

    # Step 2: イベントを選択したら、ペルソナがその知覚されたイベントに対して行動を取るかどうかを決定する必要があります。
    #              _should_reactによって返される反応モードには3つの可能性があります。
    #              a) "{target_persona.name}とチャットする"
    #              b) "反応"
    #              c) False
    # print("Fourth")
    if focused_event:
        print("focused_event")
        reaction_mode = _should_react(persona, focused_event, personas)
        # log_to_file('reaction_mode.txt', f"reaction_mode: {reaction_mode}\n")
        if reaction_mode:
            print("reaction mode")
            # If we do want to chat, then we generate conversation
            if reaction_mode[:9] == "chat with":
                print("_chat_react")
                _chat_react(maze, persona, focused_event, reaction_mode, personas)
            elif reaction_mode[:4] == "wait":
                print("wait")
                _wait_react(persona, reaction_mode)
            elif reaction_mode[:8] == "accident":
                print("アクシデント")
                _accident_react(maze, persona, focused_event, reaction_mode)
            # elif reaction_mode == "do other things":
            #   _chat_react(persona, focused_event, reaction_mode, personas)

    # ステップ3: チャット関連の状態のクリーンアップ。
    # ペルソナが誰ともチャットしていない場合、ここでチャット関連のすべての状態をクリーンアップします。
    # print("Fifth")
    # log_to_file('scratch.txt', f"ペルソナの名前:{persona.name} \n\nscratch: {str(persona.scratch)}\n\n\n")
    if persona.scratch.act_event[1] != "chat with":
        print("chat_with")
        persona.scratch.chatting_with = None
        persona.scratch.chat = None
        persona.scratch.chatting_end_time = None
    # ペルソナが互いに無限ループで会話し続けないようにしたいです。
    # したがって、chatting_with_bufferは、1度会話した後に同じターゲットとすぐに話すのを防ぐ形式のバッファを維持します。
    # ここでバッファ値を追跡します。
    curr_persona_chat_buffer = persona.scratch.chatting_with_buffer
    for persona_name, buffer_count in curr_persona_chat_buffer.items():
        if persona_name != persona.scratch.chatting_with:
            persona.scratch.chatting_with_buffer[persona_name] -= 1

    # print("wwwwwwwwŵ    wwwwwww")
    return persona.scratch.act_address