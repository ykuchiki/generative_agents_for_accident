import json
import os
import sys
import datetime

# 現在のファイルのディレクトリを基に絶対パスを計算してsys.pathに追加
current_file_path = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.join(current_file_path, '..', '..', '..')
sys.path.append(parent_directory)

from backend.global_methods import *

class Scratch:
    def __init__(self, f_saved):
        # ペルソナのハイパーパラメータ
        self.vision_r = 4  # ペルソナの周囲見れるタイルの数
        self.art_bandwidth = 3  # TODO 注意帯域幅
        self.retention = 5  # TODO 記憶保持力

        # ワールド情報
        self.curr_time = None  # ワールドの時間
        self.curr_tile = None  # ペルソナの現在のx,yタイル座標
        self.daily_plan_req = None  # ペルソナの1日の計画

        # ペルソナの基本情報
        self.name = None
        self.first_name = None
        self.last_name = None
        self.age = None

        # 自然言語で記述された性格特性
        self.innate = None  # L0 永続的なコア特性
        self.learned = None  # L1 安定した特性
        self.currently = None  # L2 外部実装
        self.lifestyle = None
        self.living_area = None

        # ==================================================================================
        # 性格特性の例
        # "innate": "open-minded, curious, determined",
        # "learned": "Abigail Chen is a digital artist and animator who loves to explore how technology can be used to
        #                           express ideas. She is always looking for new ways to combine art and technology.",
        # "currently": "Abigail Chen is working on an animation project for a client. She is also experimenting with
        #                           different tools and techniques to create interactive art.",
        # "lifestyle": "Abigail Chen goes to bed around midnight, awakes up around 8am, eats dinner around 6pm.",
        # "living_area": "the Ville:artist's co-living space:Abigail Chen's room",
        # ==================================================================================

        # リフレクション変数
        self.concept_forget = 100
        self.daily_reflection_time = 60 * 3
        self.daily_reflection_size = 5
        self.overlap_reflect_th = 2
        self.kw_strg_event_reflect_th = 4
        self.kw_strg_thought_reflect_th = 4

        # 新しいリフレクション変数
        self.recency_w = 1
        self.relevance_w = 1
        self.importance_w = 1
        self.recency_decay = 0.99
        self.importance_trigger_max = 150
        self.importance_trigger_curr = self.importance_trigger_max
        self.importance_ele_n = 0
        self.thought_count = 5

        # ペルソナの計画
        # self.daily_reqはペルソナが今日達成しようとする様々な目標のリスト
        # 例：['展示会のために絵を描く',
        #      'テレビを見て休憩する',
        #      '自分のためにランチを作る',
        #      'さらに絵を描く',
        #      '早めに寝る']
        # これらは日が終わるまでに更新する必要があり，そのため生成された時点を追跡している
        self.daily_req = []

        # self.f_daily_scheduleは長期計画の一形態を表しており，これはペルソナの日々の計画も意味する
        # 長期計画と短期分解アプローチをとっており，まず時間単位のスケジュールをレイアウトし，徐々に分解していく
        # 以下の例で注意すべき3つの点：
        # 1) "睡眠"は分解されていないことがわかる．一般的なイベント、特に睡眠は分解できないようにハードコードされている。
        # 2) いくつかの要素は分解され始めている．時間が経つにつれて、さらに多くのものが分解されていく（分解されると、元の時間単位の行動説明がそのまま残る）
        # 3) 後の要素は分解されていない．イベントが発生すると、分解されていない要素は消える
        # 例：[['睡眠', 360],
        #       ['起床して... (起床してストレッチ...)', 5],
        #       ['起床して朝のルーティンを開始 (ベッドから起きる)', 10],
        #       ...
        #       ['ランチを取る', 60],
        #       ['絵を描く', 180], ...]
        self.f_daily_schedule = []

        # <f_daily_schedule_hourly_org>はf_daily_scheduleのレプリカであり，最初は時間単位のスケジュールの元の非分解版を保持
        # 例：[['睡眠', 360],
        #      ['起床して朝のルーティンを開始', 120],
        #      ['絵を描く', 240], ... ['寝る', 60]]
        self.f_daily_schedule_hourly_org = []

        # 現在の行動
        # address 行動が行われる場所の文字列アドレス．
        # 形式は"{world}:{sector}:{arena}:{game_objects}"
        # 負のインデックス（例：[-1]）を使用せずにアクセスすることが重要．後のアドレス要素が存在しない場合がある．
        self.act_address = None
        # <start_time>は行動が開始された時間を示すPythonのdatetimeインスタンス
        self.act_start_time = None
        # <duration>は行動が継続する分数を示す整数値
        self.act_duration = None
        # <description>は行動の文字列記述
        self.act_description = None
        # <pronunciatio>はself.descriptionの説明表現です。現在は絵文字として実装
        self.act_pronunciatio = None
        # <event_form>は現在PERSONAが従事しているイベントのトリプルを表す
        self.act_event = (self.name, None, None)

        # <obj_description>はオブジェクト行動の文字列記述
        self.act_obj_description = None
        # <obj_pronunciatio>はオブジェクト行動の説明表現。現在は絵文字として実装されている
        self.act_obj_pronunciatio = None
        # <obj_event_form>はアクションオブジェクトが現在従事しているイベントのトリプルを表す
        self.act_obj_event = (self.name, None, None)

        # <chatting_with>は現在のPERSONAがチャットしているPERSONAの名前の文字列。存在しない場合はNone
        self.chatting_with = None
        # <chat>は2つのPERSONA間の会話を保存するリストのリスト。形式は：[["Dolores Murphy", "Hi"],
        #                                             ["Maeve Jenson", "Hi"] ...]
        self.chat = None
        # <chatting_with_buffer>は視野範囲にあるPERSONAを保存する辞書。例：["Dolores Murphy"] = self.vision_r
        self.chatting_with_buffer = dict()
        self.chatting_end_time = None

        # <path_set>は既にPERSONAがこの行動を実行するために取るパスを計算済みである場合はTrue
        # そのパスはPERSONAのscratch.planned_pathに保存される
        self.act_path_set = False
        # <planned_path>はPERSONAが<curr_action>を実行するために取るパスを示すx y座標のタプル（タイル）のリスト
        # リストにはPERSONAの現在のタイルは含まれず，目的地のタイルが含まれる
        # 例：[(50, 10), (49, 10), (48, 10), ...]
        self.planned_path = []

        if check_if_file_exists(f_saved):
            # bootstrap fileがある場合はここで読み込む
            scratch_load = json.load(open(f_saved))

            self.vision_r = scratch_load["vision_r"]
            self.att_bandwidth = scratch_load["att_bandwidth"]
            self.retention = scratch_load["retention"]

            if scratch_load["curr_time"]:
                self.curr_time = datetime.datetime.strptime(scratch_load["curr_time"],
                                                            "%B %d, %Y, %H:%M:%S")
            else:
                self.curr_time = None
            self.curr_tile = scratch_load["curr_tile"]
            self.daily_plan_req = scratch_load["daily_plan_req"]

            self.name = scratch_load["name"]
            self.first_name = scratch_load["first_name"]
            self.last_name = scratch_load["last_name"]
            self.age = scratch_load["age"]
            self.innate = scratch_load["innate"]
            self.learned = scratch_load["learned"]
            self.currently = scratch_load["currently"]
            self.lifestyle = scratch_load["lifestyle"]
            self.living_area = scratch_load["living_area"]

            self.concept_forget = scratch_load["concept_forget"]
            self.daily_reflection_time = scratch_load["daily_reflection_time"]
            self.daily_reflection_size = scratch_load["daily_reflection_size"]
            self.overlap_reflect_th = scratch_load["overlap_reflect_th"]
            self.kw_strg_event_reflect_th = scratch_load["kw_strg_event_reflect_th"]
            self.kw_strg_thought_reflect_th = scratch_load["kw_strg_thought_reflect_th"]

            self.recency_w = scratch_load["recency_w"]
            self.relevance_w = scratch_load["relevance_w"]
            self.importance_w = scratch_load["importance_w"]
            self.recency_decay = scratch_load["recency_decay"]
            self.importance_trigger_max = scratch_load["importance_trigger_max"]
            self.importance_trigger_curr = scratch_load["importance_trigger_curr"]
            self.importance_ele_n = scratch_load["importance_ele_n"]
            self.thought_count = scratch_load["thought_count"]

            self.daily_req = scratch_load["daily_req"]
            self.f_daily_schedule = scratch_load["f_daily_schedule"]
            self.f_daily_schedule_hourly_org = scratch_load["f_daily_schedule_hourly_org"]

            self.act_address = scratch_load["act_address"]
            if scratch_load["act_start_time"]:
                self.act_start_time = datetime.datetime.strptime(
                    scratch_load["act_start_time"],
                    "%B %d, %Y, %H:%M:%S")
            else:
                self.curr_time = None
            self.act_duration = scratch_load["act_duration"]
            self.act_description = scratch_load["act_description"]
            self.act_pronunciatio = scratch_load["act_pronunciatio"]
            self.act_event = tuple(scratch_load["act_event"])

            self.act_obj_description = scratch_load["act_obj_description"]
            self.act_obj_pronunciatio = scratch_load["act_obj_pronunciatio"]
            self.act_obj_event = tuple(scratch_load["act_obj_event"])

            self.chatting_with = scratch_load["chatting_with"]
            self.chat = scratch_load["chat"]
            self.chatting_with_buffer = scratch_load["chatting_with_buffer"]
            if scratch_load["chatting_end_time"]:
                self.chatting_end_time = datetime.datetime.strptime(
                    scratch_load["chatting_end_time"],
                    "%B %d, %Y, %H:%M:%S")
            else:
                self.chatting_end_time = None

            self.act_path_set = scratch_load["act_path_set"]
            self.planned_path = scratch_load["planned_path"]

    def __str__(self):
        attrs = vars(self)
        return '\n'.join(f"{key}: {value}" for key, value in attrs.items())

    def save(self, out_json):
        """
        ペルソナのスクラッチメモリを保存する
        :param out_json: ペルソナの状態を保存するファイル
        """
        scratch = dict()
        scratch["vision_r"] = self.vision_r
        scratch["att_bandwidth"] = self.att_bandwidth
        scratch["retention"] = self.retention

        scratch["curr_time"] = self.curr_time.strftime("%B %d, %Y, %H:%M:%S")
        scratch["curr_tile"] = self.curr_tile
        scratch["daily_plan_req"] = self.daily_plan_req

        scratch["name"] = self.name
        scratch["first_name"] = self.first_name
        scratch["last_name"] = self.last_name
        scratch["age"] = self.age
        scratch["innate"] = self.innate
        scratch["learned"] = self.learned
        scratch["currently"] = self.currently
        scratch["lifestyle"] = self.lifestyle
        scratch["living_area"] = self.living_area

        scratch["concept_forget"] = self.concept_forget
        scratch["daily_reflection_time"] = self.daily_reflection_time
        scratch["daily_reflection_size"] = self.daily_reflection_size
        scratch["overlap_reflect_th"] = self.overlap_reflect_th
        scratch["kw_strg_event_reflect_th"] = self.kw_strg_event_reflect_th
        scratch["kw_strg_thought_reflect_th"] = self.kw_strg_thought_reflect_th

        scratch["recency_w"] = self.recency_w
        scratch["relevance_w"] = self.relevance_w
        scratch["importance_w"] = self.importance_w
        scratch["recency_decay"] = self.recency_decay
        scratch["importance_trigger_max"] = self.importance_trigger_max
        scratch["importance_trigger_curr"] = self.importance_trigger_curr
        scratch["importance_ele_n"] = self.importance_ele_n
        scratch["thought_count"] = self.thought_count

        scratch["daily_req"] = self.daily_req
        scratch["f_daily_schedule"] = self.f_daily_schedule
        scratch["f_daily_schedule_hourly_org"] = self.f_daily_schedule_hourly_org

        scratch["act_address"] = self.act_address
        scratch["act_start_time"] = (self.act_start_time
                                     .strftime("%B %d, %Y, %H:%M:%S"))
        scratch["act_duration"] = self.act_duration
        scratch["act_description"] = self.act_description
        scratch["act_pronunciatio"] = self.act_pronunciatio
        scratch["act_event"] = self.act_event

        scratch["act_obj_description"] = self.act_obj_description
        scratch["act_obj_pronunciatio"] = self.act_obj_pronunciatio
        scratch["act_obj_event"] = self.act_obj_event

        scratch["chatting_with"] = self.chatting_with
        scratch["chat"] = self.chat
        scratch["chatting_with_buffer"] = self.chatting_with_buffer
        if self.chatting_end_time:
            scratch["chatting_end_time"] = (self.chatting_end_time
                                            .strftime("%B %d, %Y, %H:%M:%S"))
        else:
            scratch["chatting_end_time"] = None

        scratch["act_path_set"] = self.act_path_set
        scratch["planned_path"] = self.planned_path

        with open(out_json, "w") as outfile:
            json.dump(scratch, outfile, indent=2)

    def get_f_daily_schedule_index(self, advance=0):
        """
        self.f_daily_scheduleの現在のインデックスを取得
        self.f_daily_scheduleとは
            ・主に現在までに分解されたアクションシーケンスと，今日残りのアクションシーケンスを格納するリスト
            ・アクションが進行するにつれて更新される

        self.f_daily_scheduleはこれまでの分解されたアクションシーケンスと，今日の残り時間のアクションシーケンスを格納．
        self.f_daily_scheduleはリストで，さらにその中のリストが[task, duration]で構成されていると仮定してる．
        このメソッドは"if elapsed > today_min_elapsed" の条件に達するまでdurationを加算し続ける
        :param advance: 未来の時間を分単位で指定する整数値．この値を指定することで未来のタイムフレームのインデックスを取得できる．
        :return: self.f_daily_scheduleの現在のインデックスを示す整数値
        """
        # まず今日の経過時間を計算
        today_min_elapsed = 0    # 今日の午前0時から現在までの経過時間（分単位）
        today_min_elapsed += self.curr_time.hour * 60
        today_min_elapsed += self.curr_time.minute
        today_min_elapsed += advance

        # f_daily_schedule と f_daily_schedule_hourly_org の duration の合計を計算
        # いらなさそうなので，コメントアウト
        # x = 0
        # for task, duration in self.f_daily_schedule:
        #     x += duration
        # x = 0
        # for task, duration in self.f_daily_schedule_hourly_org:
        #     x += duration

        # 次にその経過時間に基づいて現在のインデックスを計算
        # self.daily_scheduleの各タスクのdurationを加算し，elapsedがtoday_min_epasedを超えた時点でcurr_indexを返す
        # そうでなければcurr_indexをインクリメントし続ける
        curr_index = 0    # スケジュールの中で現在の時間がどのタスクに対応するかを示すインデックス
        elapsed = 0
        for task, duration in self.f_daily_schedule:
            elapsed += duration
            if elapsed > today_min_elapsed:
                return curr_index
            curr_index += 1

        return curr_index

    def get_f_daily_schedule_hourly_org_index(self, advance=0):
        """
        上記のメソッドに似てるが，操作対象のデータが違う
        self.f_daily_schedule_hourly_orgとは
            ・初期状態の1日分の計画を保持するリスト
            ・更新されることなく，常に元の計画を保持
        """

        # まず今日の経過時間を計算
        today_min_elapsed = 0
        today_min_elapsed += self.curr_time.hour * 60
        today_min_elapsed += self.curr_time.minute
        today_min_elapsed += advance

        # # インデックスの計算
        curr_index = 0
        elapsed = 0
        for task, duration in self.f_daily_schedule_hourly_org:
            elapsed += duration
            if elapsed > today_min_elapsed:
                return curr_index
            curr_index += 1
        return curr_index

    def get_str_iss(self):
        """
        ペルソナの基本的な特徴や現在の状態をまとめた文字列を返す．
        この情報は，他の関数やプロンプトがペルソナの詳細を知るために利用される．
        :return: ペルソナの詳細情報が入った文字列
        """
        commonset = ""
        commonset += f"Name: {self.name}\n"
        commonset += f"Age: {self.age}\n"
        commonset += f"Innate traits: {self.innate}\n"
        commonset += f"Learned traits: {self.learned}\n"
        commonset += f"Currently: {self.currently}\n"
        commonset += f"Lifestyle: {self.lifestyle}\n"
        commonset += f"Daily plan requirement: {self.daily_plan_req}\n"
        commonset += f"Current Date: {self.curr_time.strftime('%A %B %d')}\n"
        return commonset

    def get_str_name(self):
        return self.name

    def get_str_firstname(self):
        return self.first_name

    def get_str_lastname(self):
        return self.last_name

    def get_str_age(self):
        return str(self.age)

    def get_str_innate(self):
        return self.innate

    def get_str_learned(self):
        return self.learned

    def get_str_currently(self):
        return self.currently

    def get_str_lifestyle(self):
        return self.lifestyle

    def get_str_daily_plan_req(self):
        return self.daily_plan_req

    def get_str_curr_date_str(self):
        """self.curr_time から現在の日付を取得し，"%A %B %d" の形式（例: "Monday January 01"）で返す"""
        return self.curr_time.strftime("%A %B %d")

    def get_curr_event(self):
        if not self.act_address:
            return (self.name, None, None)
        else:
            return self.act_event

    def get_curr_event_and_desc(self):
        if not self.act_address:
            return (self.name, None, None, None)
        else:
            return (self.act_event[0],
                    self.act_event[1],
                    self.act_event[2],
                    self.act_description)

    def get_curr_obj_event_and_desc(self):
        if not self.act_address:
            return ("", None, None, None)
        else:
            return (self.act_address,
                    self.act_obj_event[1],
                    self.act_obj_event[2],
                    self.act_obj_description)

    def add_new_action(self, action_address, action_duration, action_description, action_pronunciatio, action_event,
                       chatting_with, chat, chatting_with_buffer, chatting_end_time, act_obj_description,
                       act_obj_pronunciatio, act_obj_event, act_start_time=None):
        """
        新しいアクションの設定
        ペルソナの新しいアクションを設定し、そのアクションに関連するすべての情報を更新するために使用される
        """
        # アクションの場所のアドレスを設定
        self.act_address = action_address
        # アクションの継続時間を設定
        self.act_duration = action_duration
        # アクションの説明を設定
        self.act_description = action_description
        # アクションの発音を設定
        self.act_pronunciatio = action_pronunciatio
        # アクションに関連するイベントを設定
        self.act_event = action_event

        # チャット相手の名前を設定
        self.chatting_with = chatting_with
        # チャットの内容を設定
        self.chat = chat
        # チャット相手のバッファを更新
        if chatting_with_buffer:
            self.chatting_with_buffer.update(chatting_with_buffer)
        # チャットの終了時間を設定
        self.chatting_end_time = chatting_end_time

        # オブジェクトアクションの説明を設定
        self.act_obj_description = act_obj_description
        # オブジェクトアクションの発音を設定
        self.act_obj_pronunciatio = act_obj_pronunciatio
        # オブジェクトアクションに関連するイベントを設定
        self.act_obj_event = act_obj_event

        # アクションの開始時間を現在の時間に設定
        self.act_start_time = self.curr_time

        # アクションのパスが設定されていないことを示すフラグを設定
        self.act_path_set = False

    def add_time_str(self):
        """
        現在のアクションの開始時間を文字列として返す
        :return: アクションの開始時間の文字列．例:"14:05 P.M."
        """
        return self.act_start_time.strftime("%H:%M %p")

    def act_check_finished(self):
        """
        現在のアクションが終了したかどうかをチェックする
        :return:Boolean [True]: アクションは終了した．[False]: アクションはまだ進行中である．
        """
        if not self.act_address:  # アクションが設定されてない時
            return True

        if self.chatting_with:  # チャットが存在する時end_timeの設定
            end_time = self.chatting_end_time
        else:
            x = self.act_start_time
            if x.second != 0:  # 秒数が0じゃないなら，分単位に繰り上げる
                x = x.replace(second=0)
                x = (x + datetime.timedelta(minutes=1))
            end_time = (x + datetime.timedelta(minutes=self.act_duration))

        if end_time.strftime("%H:%M:%S") == self.curr_time.strftime("%H:%M:%S"):
            return True
        return False

    def act_summarize(self):
        """
        現在のアクション情報を辞書形式で返す
        :return: 辞書型のアクション情報
        """
        exp = dict()
        exp["persona"] = self.name
        exp["address"] = self.act_address
        exp["start_datetime"] = self.act_start_time
        exp["duration"] = self.act_duration
        exp["description"] = self.act_description
        exp["pronunciatio"] = self.act_pronunciatio
        return exp

    def act_summary_str(self):
        """
        現在のアクション情報を文字列形式で返す
        :return: 文字列のアクション情報
        """
        start_datetime_str = self.act_start_time.strftime("%A %B %d -- %H:%M %p")
        ret = f"[{start_datetime_str}]\n"
        ret += f"Activity: {self.name} is {self.act_description}\n"
        ret += f"Address: {self.act_address}\n"
        ret += f"Duration in minutes (e.g., x min): {str(self.act_duration)} min\n"
        return ret

    def get_str_daily_schedule(self):
        """
        ペルソナの日常スケジュールを時間ごとにまとめて，文字列形式で返す
        :return: ペルソナの日常スケジュール(文字列)
        """
        ret = ""
        curr_min_sum = 0
        for row in self.f_daily_schedule:
            curr_min_sum += row[1]
            hour = int(curr_min_sum / 60)
            minute = curr_min_sum % 60
            ret += f"{hour:02}:{minute:02} || {row[0]}\n"
        return ret

    def get_str_daily_schedule_hourly_org_summary(self):
        """
        元の非分解のスケジュールを時間ごとにまとめて，文字列形式で返す．
        :return: ペルソナの非分解版日常スケジュール(文字列)
        """
        ret = ""
        curr_min_sum = 0
        for row in self.f_daily_schedule_hourly_org:
            curr_min_sum += row[1]
            hour = int(curr_min_sum / 60)
            minute = curr_min_sum % 60
            ret += f"{hour:02}:{minute:02} || {row[0]}\n"
        return ret