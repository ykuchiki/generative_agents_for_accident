import json
import os
import sys
import datetime

# 現在のファイルのディレクトリを基に絶対パスを計算してsys.pathに追加
current_file_path = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.join(current_file_path, '..', '..', '..')
sys.path.append(parent_directory)

from backend.global_methods import *

class ConceptNode:
    """
    生成エージェントの記憶を構成するここの記憶ノードのを表現
    """
    def __init__(self, node_id, node_count, type_count, node_type, depth, created, expiration, s, p, o, description,
                 embedding_key, poignancy, keywords, filling):
        self.node_id = node_id              # ノードの一意なID
        self.node_count = node_count        # ノードのカウント
        self.type_count = type_count        # タイプごとのカウント(イベント，思考，チャット)
        self.type = node_type               # ノードのタイプ(イベント，思考，チャット)
        self.depth = depth                  # ノードの深さ

        self.created = created              # ノードが作成された日時
        self.expiration = expiration        # ノードの有効期限
        self.last_accessed = self.created   # 最後にアクセスされた日時

        self.subject = s                    # 主語
        self.predicate = p                  # 述語
        self.object = o                     # 目的後

        self.description = description      # 記述
        self.embedding_key = embedding_key  # 埋め込みキー
        self.poignancy = poignancy          # 感情的な強さ
        self.keywords = keywords            # キーワードのセット
        self.filling = filling              # 関連するノードのリスト

    def spo_summary(self):
        return (self.subject, self.predicate, self.object)

    def __repr__(self):
        return (f"ConceptNode(node_id={self.node_id}, subject={self.subject}, "
                f"predicate={self.predicate}, object={self.object}, description={self.description})")


class AssociativeMemory:
    def __init__(self, f_saved):
        """
        保存されたメモリデータ(イベント，思考，チャット，キーワードの強度，埋め込み)をロードする
        """
        self.id_to_node = dict()  # ノードIDからノードオブジェクトを管理する辞書

        # 各種ノードのシーケンスを保持するリスト
        self.seq_event = []
        self.seq_thought = []
        self.seq_chat = []

        # キーワードからノードへのマッピングを保持する辞書
        self.kw_to_event = dict()
        self.kw_to_thought = dict()
        self.kw_to_chat = dict()

        # キーワードの強度を保持する辞書
        self.kw_strength_event = dict()
        self.kw_strength_thought = dict()

        # 埋め込みを保持する辞書をロード
        self.embeddings = json.load(open(f_saved + "/embeddings.json"))

        # ノードデータをロードし，各ノードを初期化して追加
        nodes_load = json.load(open(f_saved + "/nodes.json"))
        for count in range(len(nodes_load.keys())):
            node_id = f"node_{str(count+1)}"
            node_details = nodes_load[node_id]

            node_count = node_details["node_count"]
            type_count = node_details["type_count"]
            node_type = node_details["type"]
            depth = node_details["depth"]

            created = datetime.datetime.strptime(node_details["created"], '%Y-%m-%d %H:%M:%S')
            expiration = None
            if node_details["expiration"]:
                expiration = datetime.datetime.strptime(node_details["expiration"], '%Y-%m-%d %H:%M:%S')

            s = node_details["subject"]
            p = node_details["predicate"]
            o = node_details["object"]

            description = node_details["description"]
            embedding_pair = (node_details["embedding_key"],
                              self.embeddings[node_details["embedding_key"]])
            poignancy = node_details["poignancy"]
            keywords = set(node_details["keywords"])
            filling = node_details["filling"]

            # ノードタイプに応じて適切なメソッドで追加
            if node_type == "event":
                print("kokomo", s)
                self.add_event(created, expiration, s, p, o,
                               description, keywords, poignancy, embedding_pair, filling)
            elif node_type == "chat":
                self.add_chat(created, expiration, s, p, o,
                              description, keywords, poignancy, embedding_pair, filling)
            elif node_type == "thought":
                self.add_thought(created, expiration, s, p, o,
                                 description, keywords, poignancy, embedding_pair, filling)

        # キーワードの強度データをロード
        kw_strength_load = json.load(open(f_saved + "/kw_strength.json"))
        if kw_strength_load["kw_strength_event"]:
            self.kw_strength_event = kw_strength_load["kw_strength_event"]
        if kw_strength_load["kw_strength_thought"]:
            self.kw_strength_thought = kw_strength_load["kw_strength_thought"]

    def save(self, out_json):
        """
        現在の状態を指定されたディレクトリに保存する
        メソッドは各ノードの情報とキーワードの強度をJSONファイルとして保存する
        """
        r = dict()
        for count in range(len(self.id_to_node.keys()), 0, -1):
            node_id = f"node_{str(count)}"
            node = self.id_to_node[node_id]

            r[node_id] = dict()
            r[node_id]["node_count"] = node.node_count
            r[node_id]["type_count"] = node.type_count
            r[node_id]["type"] = node.type
            r[node_id]["depth"] = node.depth

            r[node_id]["created"] = node.created.strftime('%Y-%m-%d %H:%M:%S')
            r[node_id]["expiration"] = None
            if node.expiration:
                r[node_id]["expiration"] = (node.expiration
                                            .strftime('%Y-%m-%d %H:%M:%S'))

            r[node_id]["subject"] = node.subject
            r[node_id]["predicate"] = node.predicate
            r[node_id]["object"] = node.object

            r[node_id]["description"] = node.description
            r[node_id]["embedding_key"] = node.embedding_key
            r[node_id]["poignancy"] = node.poignancy
            r[node_id]["keywords"] = list(node.keywords)
            r[node_id]["filling"] = node.filling

        with open(out_json + "/nodes.json", "w") as outfile:
            json.dump(r, outfile)

        r = dict()
        r["kw_strength_event"] = self.kw_strength_event
        r["kw_strength_thought"] = self.kw_strength_thought
        with open(out_json + "/kw_strength.json", "w") as outfile:
            json.dump(r, outfile)

        with open(out_json + "/embeddings.json", "w") as outfile:
            json.dump(self.embeddings, outfile)

    def add_event(self, created, expiration, s, p, o, description, keywords, poignancy, embedding_pair, filling):
        """新しいイベントをメモリに追加し，関連するデータ構造を更新する"""
        # print("baaaka", s, p, o)
        # ノードIDとカウントの設定
        node_count = len(self.id_to_node.keys()) + 1
        type_count = len(self.seq_event) + 1
        node_type = "event"
        node_id = f"node_{str(node_count)}"
        depth = 0

        # 説明に括弧が含まれていたら，説明をフォーマットする
        if "(" in description:
            description = (" ".join(description.split()[:3])
                            + " "
                            + description.split("(")[-1][:-1])

        # コンセプトノードの作成
        node = ConceptNode(node_id, node_count, type_count, node_type, depth,
                           created, expiration,
                           s, p, o,
                           description, embedding_pair[0],
                           poignancy, keywords, filling)

        # 高速アクセスのための辞書キャッシュの作成
        self.seq_event[0:0] = [node]    # 新しいイベントをリストの先頭に追加
        keywords = [i.lower() for i in keywords]
        for kw in keywords:
            if kw in self.kw_to_event:     # 新しいイベントをキーワードをkeyとして辞書型
                self.kw_to_event[kw][0:0] = [node]
            else:
                self.kw_to_event[kw] = [node]
        self.id_to_node[node_id] = node

        # イベントがis idleじゃない場合，キーワードの強度を更新
        # キーワード強度は特定のキーワードの出現頻度を示す指標
        if f"{p} {o}" != "is idle":
            for kw in keywords:
                if kw in self.kw_strength_event:
                    self.kw_strength_event[kw] += 1
                else:
                    self.kw_strength_event[kw] = 1
        # 埋め込みペアを辞書に追加
        self.embeddings[embedding_pair[0]] = embedding_pair[1]

        return node

    def add_thought(self, created, expiration, s, p, o, description, keywords, poignancy, embedding_pair, filling):
        """
        新しい「思考」ノードを作成し，関連するデータ構造に追加
        このメソッドは，エージェントが新しい思考を生成したときに使用される
        """
        # ノードIDとカウントの設定
        node_count = len(self.id_to_node.keys()) + 1
        type_count = len(self.seq_thought) + 1
        node_type = "thought"
        node_id = f"node_{str(node_count)}"

        # 新しいノードが既存の関連ノードに基づいてどれだけ深い思考や記憶の階層に位置するかを示すもの
        depth = 1
        # fillingは新しいノードの関連するノードリストらしいけど，具体的な使い方を見ないとイメージつきにくい
        try:
            if filling:
                depth += max([self.id_to_node[i].depth for i in filling])
        except:
            pass

        # コンセプトノードの作成
        node = ConceptNode(node_id, node_count, type_count, node_type, depth,
                           created, expiration,
                           s, p, o,
                           description, embedding_pair[0], poignancy, keywords, filling)

        # 辞書キャッシュ
        self.seq_thought[0:0] = [node]
        keywords = [i.lower() for i in keywords]
        for kw in keywords:
            if kw in self.kw_to_thought:
                self.kw_to_thought[kw][0:0] = [node]
            else:
                self.kw_to_thought[kw] = [node]
        self.id_to_node[node_id] = node

        # キーワード強度
        if f"{p} {o}" != "is idle":
            for kw in keywords:
                if kw in self.kw_strength_thought:
                    self.kw_strength_thought[kw] += 1
                else:
                    self.kw_strength_thought[kw] = 1

        # 埋め込みペア
        self.embeddings[embedding_pair[0]] = embedding_pair[1]

        return node

    def add_chat(self, created, expiration, s, p, o,
                 description, keywords, poignancy,
                 embedding_pair, filling):
        # Setting up the node ID and counts.
        node_count = len(self.id_to_node.keys()) + 1
        type_count = len(self.seq_chat) + 1
        node_type = "chat"
        node_id = f"node_{str(node_count)}"
        depth = 0

        # Creating the <ConceptNode> object.
        node = ConceptNode(node_id, node_count, type_count, node_type, depth,
                           created, expiration,
                           s, p, o,
                           description, embedding_pair[0], poignancy, keywords, filling)

        # Creating various dictionary cache for fast access.
        self.seq_chat[0:0] = [node]
        keywords = [i.lower() for i in keywords]
        for kw in keywords:
            if kw in self.kw_to_chat:
                self.kw_to_chat[kw][0:0] = [node]
            else:
                self.kw_to_chat[kw] = [node]
        self.id_to_node[node_id] = node

        self.embeddings[embedding_pair[0]] = embedding_pair[1]

        return node

    def get_summarized_latest_events(self, retention):
        """
        最新のイベントを要約したセットを取得
        :param retention:　取得したい最新イベントの数
        :return: 最新イベントのようやくが含まれたセット．(subject, predicate, object) のタプル形式
        """
        ret_set = set()
        for e_node in self.seq_event[:retention]:
            ret_set.add(e_node.spo_summary())
        return ret_set

    def get_str_seq_events(self):
        """
        すべてのイベントを順番に列挙し、その要約（(subject, predicate, object)）と記述を含む文字列を生成
        各イベントは 「"Event", イベント番号, ": ", (subject, predicate, object), " -- ", 記述」 の形式で記述される
        :return:  イベントのシーケンスの要約が含まれた文字列
        """
        ret_str = ""
        for count, event in enumerate(self.seq_event):
            ret_str += f'{"Event", len(self.seq_event) - count, ": ", event.spo_summary(), " -- ", event.description}\n'
        return ret_str

    def get_str_seq_thoughts(self):
        """
        すべての思考を順番に列挙し、その要約（(subject, predicate, object)）と記述を含む文字列を生成
        各思考は 「"Thought", 思考番号, ": ", (subject, predicate, object), " -- ", 記述」 の形式で記述される
        :return: 思考のシーケンスの要約が含まれた文字列
        """
        ret_str = ""
        for count, event in enumerate(self.seq_thought):
            ret_str += f'{"Thought", len(self.seq_thought) - count, ": ", event.spo_summary(), " -- ", event.description}'
        return ret_str

    def get_str_seq_chats(self):
        """
        すべてのチャットを順番に列挙し、目的語の内容、記述、作成日時、発言者と発言内容を含む文字列を生成
        各チャットは 「"with ", 目的語の内容, " (", 記述, ")\n", 作成日時, "\n", 発言者, ": ", 発言内容」 の形式で記述される
        :return: チャットのシーケンスの要約が含まれた文字列
        """
        ret_str = ""
        for count, event in enumerate(self.seq_chat):
            ret_str += f"with {event.object.content} ({event.description})\n"
            ret_str += f'{event.created.strftime("%B %d, %Y, %H:%M:%S")}\n'
            for row in event.filling:
                ret_str += f"{row[0]}: {row[1]}\n"
        return ret_str

    def retrieve_relevant_thoughts(self, s_content, p_content, o_content):
        """
        主語，述語，目的語に関連する思考を取得
        :param s_content: 主語の内容
        :param p_content: 述語の内容
        :param o_content: 目的語の内容
        :return: 関連する思考のセット
        """
        contents = [s_content, p_content, o_content]

        ret = []
        # 各contentsの要素iがself.kw_to_thought辞書に含まれてる場合は，retリストに追加
        for i in contents:
            if i in self.kw_to_thought:
                ret += self.kw_to_thought[i.lower()]
        # 重複を排除
        ret = set(ret)
        return ret

    def retrieve_relevant_events(self, s_content, p_content, o_content):
        """
        主語，述語，目的語に関連するイベントを検索し取得
        :param s_content: 主語の内容
        :param p_content: 述語の内容
        :param o_content: 目的語の内容
        :return: 関連するイベントのセット
        """
        contents = [s_content, p_content, o_content]

        ret = []
        # 各contentsの要素iがself.kw_to_event辞書に含まれてる場合は，retリストに追加
        for i in contents:
            if i in self.kw_to_event:
                ret += self.kw_to_event[i]

        ret = set(ret)
        return ret

    def get_last_chat(self, target_persona_name):
        """
        指定されたペルソナとの最後のチャットを取得
        :param target_persona_name: 対象のペルソナの名前
        :return: 最後のチャットノード，または存在しない場合はFalse
        """
        # self.kw_to_chat辞書に対象のペルソナの名前が含まれるか，すなわち会話履歴を確認
        if target_persona_name.lower() in self.kw_to_chat:
            return self.kw_to_chat[target_persona_name.lower()][0]
        else:
            return False