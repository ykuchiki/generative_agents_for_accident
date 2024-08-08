import os
import sys

from numpy import dot
from numpy.linalg import norm

# 現在のファイルのディレクトリを基に絶対パスを計算してsys.pathに追加
current_file_path = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.join(current_file_path, '..', '..', '..')
sys.path.append(parent_directory)

from backend.global_methods import *
from backend.persona.prompt_template.gpt_structure import *


def log_debug_info(info, file_path='log.txt'):
    # with open(file_path, 'a') as f:
    #     f.write(info + '\n')
    pass

def retrieve(persona, perceived):
    """
    ペルソナが知覚したイベントを入力として受け取り，計画時に考慮する必要がある関連イベントや思考を返す
    :param persona: 対象のペルソナ
    :param perceived: ペルソナの周囲で発生してるイベントを表すConceptNodeのリスト，含まれるのはatt_bandwidthとretention
    :return:辞書型 of 辞書型．第1層はイベントを特定し，第2層は「curr_event」、「events」、および「thoughts」を指定
    """
    # イベントと思考を別々に取り出す
    retrieved = dict()
    for event in perceived:
        log_debug_info(f"Processing event: {repr(event)}")
        retrieved[event.description] = dict()
        retrieved[event.description]["curr_event"] = event

        relevant_events = persona.a_mem.retrieve_relevant_events(
            event.subject, event.predicate, event.object)
        retrieved[event.description]["events"] = list(relevant_events)

        relevant_thoughts = persona.a_mem.retrieve_relevant_thoughts(
            event.subject, event.predicate, event.object)
        retrieved[event.description]["thoughts"] = list(relevant_thoughts)

    return retrieved

def cos_sim(a, b):
    """
    2つの入力ベクトル'a'と'b'間のコサイン類似度を計算する．
    :param a: 1次元配列
    :param b: 一次元配列
    :return: 類似度(スカラー)
    """
    return dot(a, b) / (norm(a) * norm(b))

def normalize_dict_floats(d, target_min, target_max):
    """
    与えられた辞書'd'の浮動小数点をターゲットの最小値と最大値の間に正規化する．
    正規化は，元の値の相対的な比率を維持しながらターゲット範囲に値をスケーリングする
    :param d: 辞書，浮動小数値を正規化する必要がある入力辞書
    :param target_min:　整数または浮動小数点。元の値をスケーリングする最小値
    :param target_max:　整数または浮動小数点。元の値をスケーリングする最大値
    :return: d 同じキーを持つ新しい辞書で正規化されたもの
    """
    min_val = min(val for val in d.values())
    max_val = max(val for val in d.values())
    range_val = max_val - min_val

    if range_val == 0:
        for key, val in d.items():
            d[key] = (target_max - target_min) / 2
    else:
        for key, val in d.items():
            d[key] = ((val - min_val) * (target_max - target_min)
                      / range_val + target_min)
    return d

def top_highest_x_values(d, x):
    """
    辞書dから最も高い上位'x'のキーと値のペアを含む新しい辞書を返す
    :param d: 対象辞書
    :param x:　検出する数
    :return:　辞書 'd' から値が最も高い上位 'x' のキーと値のペアを含む新しい辞書
    """
    top_v = dict(sorted(d.items(),
                        key=lambda item: item[1],
                        reverse=True)[:x])
    return top_v

def extract_recency(persona, nodes):
    """
    現在のペルソナオブジェクトと時系列順のノードリストを取得し，再現性スコアを計算する辞書を出力
    :param persona:　メモリを取得してる現在のペルソナ
    :param nodes: 時系列順のノードオブジェクトのリスト
    :return: ノードIDをキーとして，再現性スコアを値とする辞書
    """
    recency_vals = [persona.scratch.recency_decay ** i
                    for i in range(1, len(nodes) + 1)]

    recency_out = dict()
    for count, node in enumerate(nodes):
        recency_out[node.node_id] = recency_vals[count]

    return recency_out

def extract_importance(persona, nodes):
    """
    現在のペルソナオブジェクトと時系列順のノードリストを取得し，再現性スコアを計算する辞書を出力
    :return: ノードIDをキーとして，重要度スコアを値とする辞書
    """
    importance_out = dict()
    for count, node in enumerate(nodes):
        importance_out[node.node_id] = node.poignancy

    return importance_out

def extract_relevance(persona, nodes, focal_pt):
    """
    現在のペルソナオブジェクト，時系列順のノードリスト，となる思考やイベントの説明文字列を取得し，関連性スコアを計算する辞書を出力
    :param persona: メモリを取得してる現在のペルソナ
    :param nodes: 時系列順のノードオブジェクトのリスト
    :param focal_pt: 現在の焦点となる思考やイベントを説明する文字列
    :return: ノードIDをキーとして，関連性スコアを値とする辞書
    """
    # まず思考やイベントを説明する文字列を埋め込みベクトル化する
    focal_embedding = get_embedding(focal_pt)

    # 関連性スコアを計算するための辞書を初期化
    relevance_out = dict()
    # 各ノードの埋め込みベクトルを取得し，focal_embeddingとのコサイン類似度を計算
    for count, node in enumerate(nodes):
        node_embedding = persona.a_mem.embeddings[node.embedding_key]
        # ノードidをキーに類似度を値として辞書に格納
        relevance_out[node.node_id] = cos_sim(node_embedding, focal_embedding)

    return relevance_out

def new_retrieve(persona, focal_points, n_count=30):
    """
    現在のペルソナと思考やイベントの焦点を元に，各焦点に対してノードのセットを取得し，辞書として返す

    例:
    persona = <persona> object
    focal_points = ["How are you?", "Jane is swimming in the pond"]

    :param persona:
    :param focal_points: 現在の取得の焦点となる思考やイベントの文字列のリスト
    :param n_count: 取得するノードの数
    :return: 焦点点をキーとし，エージェントの連想記憶内のノードオブジェクトのリストを値とする辞書
    """
    # <retrieved> は返すメインの辞書
    retrieved = dict()
    for focal_pt in focal_points:  # 焦点点の文字列のリストでループ
        # エージェントの記憶（思考とイベントの両方）からすべてのノードを取得し、それらを作成日時でソートします。
        # ((生の会話を聞くことも想像できるだろうが、今のところは))
        nodes = [[i.last_accessed, i]   # 各イベントまたは思考iに関してそのイベントや思考が最後にアクセスされた日時とi自身のリストを作る
                 for i in persona.a_mem.seq_event + persona.a_mem.seq_thought  # イベントと思考のシーケンスを結合させる
                 if "idle" not in i.embedding_key]  # idleという文字列を含まない場合のみ処理する
        nodes = sorted(nodes, key=lambda x: x[0])  # ノードを last_accessed に基づいてソート
        nodes = [i for created, i in nodes]  # ソートされたリストからノードのみを抽出

        # コンポーネント辞書を計算し、それらを正規化
        recency_out = extract_recency(persona, nodes)  # 再現性スコア，最近そのノードがどれだけアクセスされたかを評価
        recency_out = normalize_dict_floats(recency_out, 0, 1)  # 正規化
        importance_out = extract_importance(persona, nodes)  # 重要性スコア(格納されてる感動度)
        importance_out = normalize_dict_floats(importance_out, 0, 1)  # 正規化
        relevance_out = extract_relevance(persona, nodes, focal_pt)  # 関連性スコアノードが焦点点にどれだけ関連してるかのcos_sim
        relevance_out = normalize_dict_floats(relevance_out, 0, 1)  # 正規化

        # コンポーネント値を組み合わせた最終スコアを計算します。
        # 注: 異なる重みをテストします。 [1, 1, 1] はまずまずうまく機能しますが、
        # 将来的には、これらの重みは RL のようなプロセスを通じて学習されるべきです。
        # gw = [1, 1, 1]
        # gw = [1, 2, 1]
        gw = [0.5, 3, 2]  # 再現性，重要性，関連性スコアの重み
        # 各ノードの最終スコアを計算し，辞書に格納するための空辞書
        master_out = dict()
        for key in recency_out.keys():
            # 各スコアに重みをかけて計算される
            master_out[key] = (persona.scratch.recency_w * recency_out[key] * gw[0]
                               + persona.scratch.relevance_w * relevance_out[key] * gw[1]
                               + persona.scratch.importance_w * importance_out[key] * gw[2])

        # マスター辞書から上位のスコアを持つノードを抽出
        master_out = top_highest_x_values(master_out, len(master_out.keys()))
        for key, val in master_out.items():
            # デバック用の確認
            print(persona.a_mem.id_to_node[key].embedding_key, val)
            print(persona.scratch.recency_w * recency_out[key] * 1,
                  persona.scratch.relevance_w * relevance_out[key] * 1,
                  persona.scratch.importance_w * importance_out[key] * 1)

        # 最高値の x 値を抽出します。
        # 最高値の x 値を取得したら、ノードIDをノードに変換し、ノードのリストを返します。
        master_out = top_highest_x_values(master_out, n_count)
        master_nodes = [persona.a_mem.id_to_node[key]
                        for key in list(master_out.keys())]

        for n in master_nodes:
            n.last_accessed = persona.scratch.curr_time

        retrieved[focal_pt] = master_nodes

    return retrieved