import json
import os
import sys
import datetime
import math
from operator import itemgetter

# 現在のファイルのディレクトリを基に絶対パスを計算してsys.pathに追加
current_file_path = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.join(current_file_path, '..', '..', '..')
sys.path.append(parent_directory)

from backend.global_methods import *
from backend.persona.prompt_template.gpt_structure import *
from backend.persona.prompt_template.run_gpt_prompt import *


def log_debug_info(info, file_path='log.txt'):
    # with open(file_path, 'a') as f:
    #     f.write(info + '\n')
    pass

def log_to_file(file_path, content):
    with open(file_path, 'a') as f:
        f.write(content + '\n')

def generate_poig_score(persona, event_type, description):
    """イベントやチャットの記述に基づいて感動スコアを生成"""
    if description is not None:
        if "is idle" in description:
            return 1

    if event_type == "event":
        return run_gpt_prompt_event_poignancy(persona, description)[0]
    elif event_type == "chat":
        return run_gpt_prompt_chat_poignancy(persona,
                                             persona.scratch.act_description)[0]


def perceive(persona, maze):
    """
    エージェントの周囲のイベントと空間を認識し，それらをメモリに保存
    :param persona: 現在のペルソナを表すインスタンス
    :param maze:　ペルソナの存在するマップ情報を取得するクラス
    :return:知覚された新しいイベントのリスト，それぞれのイベントはConceptNodeインスタンスとして連想記憶に追加される
    """
    # PERCEIVE SPACE
    # エージェントの視覚範囲内のタイルを取得し
    nearby_tiles = maze.get_nearby_tiles(persona.scratch.curr_tile,
                                         persona.scratch.vision_r)

    # 知覚された空間を保存
    # ペルソナのs_memは辞書を使って構築されたツリー形式であることに注意
    for i in nearby_tiles:
        i = maze.access_tile(i)  # タイルiの情報取得
        if i["world"]:
            if (i["world"] not in persona.s_mem.tree):
                persona.s_mem.tree[i["world"]] = {}
        if i["sector"]:
            if (i["sector"] not in persona.s_mem.tree[i["world"]]):
                persona.s_mem.tree[i["world"]][i["sector"]] = {}
        if i["arena"]:
            if (i["arena"] not in persona.s_mem.tree[i["world"]]
            [i["sector"]]):
                persona.s_mem.tree[i["world"]][i["sector"]][i["arena"]] = []
        if i["game_object"]:
            if (i["game_object"] not in persona.s_mem.tree[i["world"]]
            [i["sector"]]
            [i["arena"]]):
                persona.s_mem.tree[i["world"]][i["sector"]][i["arena"]] += [
                    i["game_object"]]

    # PERCEIVE EVENTS.
    # エージェントのいる現在のアリーナパスを取得
    curr_arena_path = maze.get_tile_path(persona.scratch.curr_tile, "arena")
    # 同じイベントを複数回知覚しないようにするためのセットを初期化
    percept_events_set = set()
    # 距離に基づいて優先度をつけるためのイベントリとを初期化
    percept_events_list = []
    # 重複管理用のリスト
    # existing_events = {e[1][0]: e for e in percept_events_list}
    # 近くのタイルの詳細を取得し，そのタイルにイベントが存在するか確認
    for tile in nearby_tiles:
        tile_details = maze.access_tile(tile)
        if tile_details["events"]:
            if maze.get_tile_path(tile, "arena") == curr_arena_path:
                # イベントが存在し，かつそのアリーナパスがエージェントのパスと一致する場合
                # エージェントの現在のタイルからの距離を計算
                dist = math.dist([tile[0], tile[1]],
                                 [persona.scratch.curr_tile[0],
                                  persona.scratch.curr_tile[1]])
                # 距離とともにイベントをリストに追加
                for event in tile_details["events"]:
                    if event not in percept_events_set:
                        percept_events_list += [[dist, event]]
                        percept_events_set.add(event)

    ## TODO アクシデントは距離を0としてイベントに追加すればいいんじゃないかな？

    # ここでアクシデントイベントを追加
    # for accident_event in persona.accident_events:
    #     dist = 0  # アクシデントは常に重要なので距離を0に設定
    #     percept_events_list.append([dist, accident_event])
    #     percept_events_set.add(accident_event)

    # subjectだけの比較でダブりをチェック
    # アクシデントイベントを追加
    for accident_event in persona.accident_events:
        print("waiyo", accident_event)
        dist = 0  # アクシデントイベントの距離は常に0と設定
        # print("kkkk", accident_event)
        event_subject = accident_event[0]
        # 同じ場所で既に知覚されたイベントがある場合、それを削除
        percept_events_list = [e for e in percept_events_list if e[1][0] != event_subject]
        percept_events_list.append([dist, accident_event])
        percept_events_set.add(accident_event)

    # log_debug_info(f"percept_events_listtttttttttttttt : {percept_events_list}")
    # log_to_file("percept_events_list.txt", f"ペルソナ: {persona.name}\npercept_events_list: {percept_events_list}\n")
    # log_to_file("percept_events_set.txt", f"ペルソナ: {persona.name}\npercept_events_set: {percept_events_set}\n")

    # イベントリストを感動スコアに基づいてソートし，エージェントの近く帯域幅に基づいて最も重要なイベントのみを知覚
    # ここで毎回感情スコアを計算してるとGPTのトークン消費量がえぐいことになる
    # percept_events_list_with_scores = []
    # for dist, event in percept_events_list:
    #     s, p, o, desc = event
    #     score = generate_poig_score(persona, "event", desc)
    #     percept_events_list_with_scores.append([score, event])

    # percept_events_list_with_scores.sort(key=itemgetter(0), reverse=True)
    # perceived_events = []
    # for score, event in percept_events_list_with_scores[:persona.scratch.att_bandwidth]:
    #     perceived_events += [event]

    # イベントリストを距離に基づいてソートし，エージェントの近く帯域幅に基づいて最も近いイベントのみを知覚
    # TODO 近くだけじゃなくて，重要度によってもソートを変えるべき
    percept_events_list = sorted(percept_events_list, key=itemgetter(0))
    perceived_events = []
    for dist, event in percept_events_list[:persona.scratch.att_bandwidth]:
        perceived_events += [event]

    # Storing events.
    # <ret_events> is a list of <ConceptNode> instances from the persona's associative memory.
    # 知覚したイベントを記憶に保存
    ret_events = []
    for p_event in perceived_events:
        # print("nani", p_event)
        s, p, o, desc = p_event
        # print("honto", s)
        if not p:
            # イベントが存在しない場合はデフォルト値を設定
            p = "is"
            o = "idle"
            desc = "idle"
        desc = f"{s.split(':')[-1]} is {desc}"
        p_event = (s, p, o)

        # 直近のイベントを取得し，知覚したイベントが新しいものであるかを確認
        latest_events = persona.a_mem.get_summarized_latest_events(
            persona.scratch.retention)
        if p_event not in latest_events:
            # 新しいイベントの場合，キーワードの管理，イベントの埋め込みの取得，感動スコアの計算を行う
            keywords = set()
            sub = p_event[0]
            obj = p_event[2]
            if ":" in p_event[0]:
                sub = p_event[0].split(":")[-1]
            if ":" in p_event[2]:
                obj = p_event[2].split(":")[-1]
            keywords.update([sub, obj])

            # イベント埋め込みの取得
            # descはイベントの説明
            # 例：("Alice", "talks with", "Bob", "about the new project")
            # desc: "Alice talks with Bob about the new project"
            desc_embedding_in = desc
            # descにかっこが含まれてたら，イベントの詳細で重要な説明を含むので抽出
            if "(" in desc:
                desc_embedding_in = (desc_embedding_in.split("(")[1]
                                     .split(")")[0]
                                     .strip())
            # すでにその記憶がある場合，その記憶から埋め込みを引っ張ってくる
            if desc_embedding_in in persona.a_mem.embeddings:
                # persona.a_mem.embeddings[desc_embedding_in]ではテキストがキー，埋め込みが値になってる
                event_embedding = persona.a_mem.embeddings[desc_embedding_in]
            else:
                event_embedding = get_embedding(desc_embedding_in)
            event_embedding_pair = (desc_embedding_in, event_embedding)

            # 感動スコアの計算
            event_poignancy = generate_poig_score(persona,
                                                  "event",
                                                  desc_embedding_in)

            # エージェントの自己チャットを観察した場合，そのチャットを記憶に含める
            chat_node_ids = []
            if p_event[0] == f"{persona.name}" and p_event[1] == "chat with":
                curr_event = persona.scratch.act_event
                if persona.scratch.act_description in persona.a_mem.embeddings:
                    chat_embedding = persona.a_mem.embeddings[
                        persona.scratch.act_description]
                else:
                    chat_embedding = get_embedding(persona.scratch
                                                   .act_description)
                chat_embedding_pair = (persona.scratch.act_description,
                                       chat_embedding)
                chat_poignancy = generate_poig_score(persona, "chat",
                                                     persona.scratch.act_description)
                chat_node = persona.a_mem.add_chat(persona.scratch.curr_time, None,
                                                   curr_event[0], curr_event[1], curr_event[2],
                                                   persona.scratch.act_description, keywords,
                                                   chat_poignancy, chat_embedding_pair,
                                                   persona.scratch.chat)
                chat_node_ids = [chat_node.node_id]

            # 最後に，現在のイベントをエージェントの記憶に追加
            # print("usoda", s)
            ret_events += [persona.a_mem.add_event(persona.scratch.curr_time, None,
                                                   s, p, o, desc, keywords, event_poignancy,
                                                   event_embedding_pair, chat_node_ids)]
            # エージェントの現在の重要度トリガーをイベントの感動スコア分だけ減少
            # これによってエージェントが新しい重要なベントに対する感度が調整できる
            persona.scratch.importance_trigger_curr -= event_poignancy
            # エージェントが知覚した重要なイベントの数を1増加させる
            persona.scratch.importance_ele_n += 1

    return ret_events