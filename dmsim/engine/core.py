"""ルールエンジン本体（総合ゲームルール Ver.1.53 準拠を目標とするプロトタイプ）。

構造（設計判断③⑤）:
- すべての処理は state.tasks（純データのスタック）上のタスクとして進む。Python のジェネレータや
  コールバックで「途中の処理」を持たないので、決定待ちのどの時点でも state を複製・保存・再開できる。
- 選択はすべて Decision として外に出す。エンジンが自分で決めるのは「選択肢が1つしかない」場合だけ。
- 状態変化は event タスクを通す: 置換（各イベント1回, 101.5/609.3）→ 同時に適用 → 状況起因処理 → 誘発して待機。
- 待機中の効果は「解決窓」ごとに持つ。通常は checkpoint（ターン進行・攻撃進行のタスク）で窓0を
  605.1 の順に解決し、効果の解決中には割り込まない（101.4d）。
  バトルの結果で誘発した効果（701.13b）や、効果中のブレイクで出た S・トリガー（101.4g）は
  内側の窓を開いて、その場で解決する。"""
from __future__ import annotations

import contextlib
import os

from ..cards.defs import CardDef, Face, Rules
from .state import Card, GameState, rng_below
from .combat import CombatMixin
from .events import EventMixin
from .interpreter import InterpreterMixin
from ..base.types import Option, check_shape
from .registry import TASK_SHAPES, TASKS
from .selectors import SelectorMixin
from .turn import TurnMixin


CHECK = os.environ.get("DMSIM_CHECK") == "1"
_MUTABLE_CHARS = ("civs", "types", "races", "keywords", "allow", "deny", "require", "break_opts", "cost_may",
                  "no_leave", "battle_indestructible_filters")   # chars() の結果のうち、呼び出し側が書き換えうる可変の値


class IllegalAnswer(ValueError):
    pass


class Engine(SelectorMixin, EventMixin, InterpreterMixin, TurnMixin, CombatMixin):
    """ゲーム進行の中核。ルールごとの処理は各 Mixin と、registry に登録された task / op が受け持つ。"""

    def __init__(self, rules: Rules, state: GameState, *, step_limit: int = 20000, turn_limit: int = 80,
                 check: bool | None = None):
        self.rules = rules
        self._in_static_cond = 0
        self._threshold_busy = set()   # {power_ge: N} の評価中にパワーを見ているカード（再入防止。第3段・共通基盤）
        self._distinct_costing = set()   # distinct_cost_count の評価中に特性を見ているカード（再入防止、第145弾）
        self._chars_busy = set()   # chars() の評価中に特性を計算しているカード（再入防止。第170弾。参照先が評価中の時は印刷特性で見る）
        self._adding = set()
        self._link_merging = False
        self._xcache = rules.__dict__.setdefault("_affects_others_cache", {})   # 定義だけで決まるので複製間で共有
        self.check = CHECK if check is None else check   # タスクの形を毎回検査する（テスト・開発者モード用）
        self.s = state
        self._pw_busy = False
        self._affc: tuple | None = None   # chars_scope() の間だけ有効: 他のカードに mod を及ぼす常在型の発生源（バトルゾーン・シールド）と能力の一覧
        self._affc_building = False
        self._chcache: dict | None = None   # chars_scope() の間だけ有効な特性キャッシュ（状態が変わらない区間専用）
        self.step_limit = step_limit
        self.turn_limit = turn_limit
        self.log: list[dict] = []

    @classmethod
    def new_game(cls, rules: Rules, decks: list[list[str]], seed: int, first_player: int = 0, **kw) -> "Engine":
        cards: list[Card] = []
        zones = {z: [[], []] for z in rules.zones}
        for p, deck in enumerate(decks):
            for d in deck:
                if d not in rules.cards:
                    raise KeyError(f"unknown card {d}")
                c = Card(cid=len(cards), defn=d, owner=p, controller=p, zone="deck")
                cards.append(c)
                zones["deck"][p].append(c.cid)
        s = GameState(cards=cards, zones=zones, rng=seed & ((1 << 64) - 1), first_player=first_player,
                      active=first_player, turn=1)
        e = cls(rules, s, **kw)
        for p in (0, 1):
            e._shuffle(p)
            for _ in range(5):                       # 113.1 / 103
                e._raw_move(s.zones["deck"][p][0], "shield")
            for _ in range(5):
                e._raw_move(s.zones["deck"][p][0], "hand")
        s.deck_emptied = []
        s.pub = []                                   # 準備中のシャッフル等は公開イベントに数えない
        s.tasks.append(e.turn_task())
        return e

    def clone(self) -> "Engine":
        e = Engine(self.rules, self.s.clone(), step_limit=self.step_limit, turn_limit=self.turn_limit,
                   check=self.check)
        e.log = list(self.log)
        return e

    def advance(self) -> dict | None:
        """次の Decision まで進める。ゲーム終了なら None。"""
        s = self.s
        while s.result is None:
            if s.waiting is not None:
                return s.waiting
            if not s.tasks:
                raise RuntimeError("task stack empty")
            t = s.tasks[-1]
            if t.get("cp") and any(p["win"] == 0 for p in s.pending):
                s.tasks.append({"t": "resolve_pending", "win": 0, "only_st": False})
                continue
            if self.check and TASK_SHAPES.get(t["t"]):
                check_shape(t, TASK_SHAPES[t["t"]])
            d = TASKS[t["t"]](self, t)
            if d is not None:
                s.waiting = d
                return d
            s.steps_this_turn += 1
            if s.steps_this_turn > self.step_limit:
                s.result = {"winner": None, "reason": "step_limit", "turn": s.turn}  # 強制ループ扱い → 無効試合
        return None

    def answer(self, choice: list[int] | int):
        d = self.s.waiting
        if d is None:
            raise IllegalAnswer("no decision pending")
        if isinstance(choice, int):
            choice = [choice]
        choice = list(choice)
        if len(set(choice)) != len(choice) or not (d["min"] <= len(choice) <= d["max"]) \
                or any(not 0 <= i < len(d["options"]) for i in choice):
            raise IllegalAnswer(f"bad choice {choice} for {d['kind']}")
        self.s.tasks[-1]["answer"] = choice
        self.s.waiting = None
        self.log.append({"p": d["player"], "kind": d["kind"], "choice": choice,
                         "keys": [d["options"][i]["key"] for i in choice]})

    def answer_by_keys(self, keys: list[str]):
        """選択肢をカードID ではなく意味（key）で指定する。ループの再生に使う。"""
        d = self.s.waiting
        opts = [o["key"] for o in d["options"]]
        choice, used = [], set()
        for k in keys:
            for i, ok in enumerate(opts):
                if ok == k and i not in used:
                    choice.append(i)
                    used.add(i)
                    break
            else:
                raise IllegalAnswer(f"key {k} not available in {opts}")
        self.answer(choice)

    def cdef(self, cid: int) -> CardDef:
        return self.rules.cards[self.s.cards[cid].defn]

    def fdef(self, cid: int, face: int | None = None) -> "CardDef | Face":
        """今使っている面の定義（ツインパクトはバトルゾーンではクリーチャー側, 810.4）。face で面を指定できる。"""
        c = self.s.cards[cid]
        if face is None and c.face >= 0:
            face = c.face
        return self.rules.cards[c.defn].face(face)

    def zshared(self, z: str) -> bool:
        return self.rules.zones[z]["shared"]

    def zlist(self, z: str, p: int) -> list[int]:
        return self.s.zones[z][0 if self.zshared(z) else p]

    def is_hyper(self, cid: int) -> bool:
        """ハイパーモードか（ハイパー化、または Zラッシュで解放された旗）。"""
        return self.s.cards[cid].hyper

    def bz_tops(self, controller: int | None = None) -> list[int]:
        return [c for c in self.s.zones["bz"][0]
                if self.s.cards[c].top_of < 0 and (controller is None or self.s.cards[c].controller == controller)
                and (not self.s.cards[c].link or self.link_rep(c) == c)]

    # ---- G・リンク ----
    LINK_SIDES = {"left_g_link": 0, "center_g_link": 1, "right_g_link": 2}

    def link_side(self, cid: int) -> int | None:
        """ゴッドのリンク位置（左0・中央1・右2）。ゴッドでなければ None。"""
        for kw, side in self.LINK_SIDES.items():
            if kw in self.fdef(cid).keywords:
                return side
        return None

    def link_spec(self, cid: int) -> list:
        """名前指定 G・リンク（第197弾）のリンク先指定 [{name, pos}]。無ければ空リスト。
        位置キーワード（左/中央/右）とは別系統で、対象はカード名で決まる。"""
        return self.fdef(cid).link_to or []

    def link_members(self, cid: int) -> list[int]:
        """cid がリンクしているグループの全カード（左→中央→右の順）。リンクしていなければ [cid]。"""
        c = self.s.cards[cid]
        if not c.link:
            return [cid]
        ms = [m for m in self.s.zones["bz"][0] if self.s.cards[m].link == c.link]
        return sorted(ms, key=lambda m: (self.link_side(m) is None, self.link_side(m) or 0))

    def link_rep(self, cid: int) -> int:
        """グループの代表（中央がいれば中央、なければ一番左）。グループはこの1体として扱う。"""
        ms = self.link_members(cid)
        for m in ms:
            if self.link_side(m) == 1:
                return m
        return ms[0]

    def unlink(self, cid: int):
        """1枚のリンクを外す。残りが1枚だけになれば、その1枚のリンクも解消する。"""
        c = self.s.cards[cid]
        gid = c.link
        c.link = 0
        if gid:
            rest = [m for m in self.s.zones["bz"][0] if self.s.cards[m].link == gid]
            if len(rest) <= 1:
                for m in rest:
                    self.s.cards[m].link = 0

    # ---- 特性・許可 ----
    def _ignored(self) -> dict[int, set[str]]:
        """無視されている能力（cid → 能力の種類の集合）。608.4 / 608.5。
        無視の発生源をタイムスタンプ順（先にバトルゾーンに出た／先に解決された順）に適用し、
        すでに無視された発生源の無視効果は働かない。これで無視し合うループは起きない。"""
        s = self.s
        ig = self.rules.ignore_defs
        cards = s.cards
        # 速い判定: 無視の発生源が無ければ空（バトルゾーンの全カードで見る。重なった下のカードを含む上位集合なので結果は同じ）
        if not any(cards[o].defn in ig for o in s.zones["bz"][0]) and \
                not any(ce["mod"].get("ignore") for ce in s.continuous):
            return {}
        srcs = []
        tops = self.bz_tops()
        if not any(ce["mod"].get("ignore") for ce in s.continuous) and \
                not any(s.cards[o].defn in self.rules.ignore_defs for o in tops):
            return {}
        for o in tops:
            for ab in self.fdef(o).abilities:
                if ab["kind"] == "static" and "ignore" in ab.get("mod", {}):
                    srcs.append((s.cards[o].entered_seq, o, ab))
        for ce in s.continuous:
            if "ignore" in ce["mod"]:
                srcs.append((ce["id"], None, ce))
        out: dict[int, set[str]] = {}
        for _, o, x in sorted(srcs, key=lambda z: z[0]):
            if o is not None and out.get(o, set()) & {"static", "all"}:
                continue
            kinds = x["mod"]["ignore"]
            for c in self.bz_tops():
                if o is not None:
                    env = {"you": s.cards[o].controller, "self": s.ref(o)}
                    hit = self._subject_match(x.get("affects", {}), c, env, None, base=True)
                else:
                    hit = self._ce_applies(x, c, s.ref(c))
                if hit:
                    out.setdefault(c, set()).update(kinds)
        return out

    def _power_when(self, pw: dict, ref, env_self) -> int:
        """攻撃中／ブロック中だけのパワー修整（mod power_when）。攻撃クリーチャーに指定されてから攻撃の終わりまで、
        ブロッククリーチャーはブロックの宣言からその攻撃の終わりまでが対象（バトルをしていない間も含む）。"""
        for t in self.s.tasks:
            if t["t"] != "attack":
                continue
            if (t["attacker"] if pw["when"] == "attacking" else t["target"] if t.get("blocked") else None) == ref:
                if "count" not in pw:
                    return pw["amount"]
                if self._pw_busy:   # 数える対象の特性を調べる途中で、またこの修整を計算しない（無限再帰を避ける。数え方にパワーの条件があれば修整前の値で見る）
                    return 0
                self._pw_busy = True
                try:
                    return pw["amount"] * self.count_of(pw["count"], env_self)
                finally:
                    self._pw_busy = False
        return 0

    def _ce_applies(self, ce, cid, ref) -> bool:
        if ce["affected"] is not None:
            return ref in ce["affected"]
        f = ce["filter"]
        c = self.s.cards[cid]
        if c.zone not in self.zones_of(f["zone"]):
            return False
        if f["owner"] != "any" and c.controller != f["owner"]:
            return False
        return self.filter_match(cid, f["filter"], base=True)

    def abilities(self, cid: int, kind: str | None = None) -> list[tuple[int, dict]]:
        """(添字, 能力) の列。無視されている能力は除く（608.4）。
        継続的効果の mod.gain で得た能力は負の添字（-1, -2, ...）で返す。"""
        if self.s.cards[cid].zone == "bz" and self.s.cards[cid].seals:
            return []   # 封印されているクリーチャーの能力は機能しない（封印が外れた時点から見える）
        out = [(i, ab) for i, ab in enumerate(self.fdef(cid).abilities)
               if (kind is None or ab["kind"] == kind)
               and (not ab.get("sst") or self.s.cards[cid].sst)   # スーパー・S・トリガーの追加能力は印がある時だけ
               and (not ab.get("stp") or self.s.cards[cid].stp)   # S・トリガー・プラスも同様
               and (not ab.get("dswitch")
                    or (not self.s.cards[cid].dswitched and self.permits(cid, "d_switch")))   # Dスイッチ（第151弾）: 使用済み・禁止中は能力自体が出ない（kind 照合の後ろで permits を見るので chars 計算とは再帰しない）
               and (not ab.get("sforce") or self._sforce_active(cid))   # シールド・フォース（第166弾）: 紐付いたシールドがシールドゾーンにある間だけ機能する
               and (not ab.get("accel") or self._accel_active(cid))   # アクセル（第175弾）: クロスギアがクロスされている間だけ機能する
               and (not ab.get("fort_e") or self._fort_e_active(cid, ab["fort_e"]))   # フォートE（第168弾）: 召喚時に指定種族のマナをタップしていた時だけ機能する
               and (not ab.get("odrive")
                    or (ab["odrive"] is True and self.s.cards[cid].odrive)
                    or (isinstance(ab.get("odrive"), str) and ab["odrive"] in self.s.cards[cid].odrive_civs))]   # O・ドライブで得る能力（odrive: <文明> はその文明をタップした時だけ）
        if self.s.cards[cid].zone == "bz" and kind != "static":
            ref = self.s.ref(cid)
            k = 0
            for ce in self.s.continuous:
                for ab in ce["mod"].get("gain", []):
                    k += 1
                    if (kind is None or ab["kind"] == kind) and self._ce_applies(ce, cid, ref):
                        out.append((-k, ab))
                src = ce.get("add_from")      # ダイナモ: 発生源のクリーチャーの能力（ダイナモ自身は除く）を加える
                if src and src[0] != cid and self.s.alive(src) and kind != "static" and self._ce_applies(ce, cid, ref):
                    for ab in self.fdef(src[0]).abilities:
                        if ab.get("keyword") != "dynamo" and (kind is None or ab["kind"] == kind) and ab["kind"] != "static":
                            k += 1
                            out.append((-k, ab))
        if self.s.cards[cid].zone == "bz" and self.s.cards[cid].under:
            k = 5000   # 超魂X: 下に重なっているカードの choukon 印つき能力は、一番上のクリーチャーが得る
            for u in self.s.cards[cid].under:
                for ab in self.fdef(u).abilities:
                    if ab.get("choukon") and (kind is None or ab["kind"] == kind):
                        k += 1
                        out.append((-k, ab))
        if out and self.s.cards[cid].zone == "bz":
            ign = self._ignored().get(cid)
            if ign:
                out = [(i, ab) for i, ab in out if not ({"all", ab["kind"]} & ign)]
            iids = self._ignored_ids(cid)
            if iids:
                out = [(i, ab) for i, ab in out if ab.get("id") not in iids]
        return out

    def _fort_e_tapped(self, cid: int, spec: dict) -> list:
        """フォートE: 召喚時にタップしたマナのうち、指定種族に合うものの参照（[cid, gen] の列）。

        種族は召喚時のスナップショットで照合する（タップしたマナが後から動いても、
        召喚という出来事の条件は変わらない）。power_of は複数参照で最大値を返すため、
        「タップした〜のいずれかよりパワーが小さい」は power_le: {sum: [power_of, -1]} で書ける。
        """
        races = set(spec.get("races", []))
        return [list(e["ref"]) for e in self.s.cards[cid].summon_tapped
                if races & set(e.get("races", [])) and self.s.alive(e["ref"])]

    def _fort_e_active(self, cid: int, spec) -> bool:
        if not isinstance(spec, dict):
            return False
        return bool(self._fort_e_tapped(cid, spec))

    def _accel_active(self, cid: int) -> bool:
        """アクセル: このクリーチャーにクロスギアが1枚でもクロスされているか（第175弾）。
        状態だけを見るので chars() の評価中でも再帰しない。"""
        return bool(self.crossed_gears(self.s.ref(cid)))

    def _ace_active(self, cid: int) -> bool:
        """ACEタマシード（第179弾）: 自分の、同じ文明のクリーチャーまたはタマシードが
        バトルゾーンに合計4つ以上あればクリーチャーとして扱う。自分自身も数える。
        定義の特性（fdef）だけで数えるので chars() の評価中でも再帰しない。"""
        c = self.s.cards[cid]
        if c.zone != "bz":
            return False
        civs = set(self.fdef(cid).civs)
        n = 0
        for other in self.s.zones["bz"][0]:   # bz は共有ゾーン: controller で絞る
            oc = self.s.cards[other]
            if oc.controller != c.controller:
                continue
            od = self.fdef(other)
            if (("creature" in od.types) or ("tamaseed" in od.types)) and (set(od.civs) & civs):
                n += 1
        return n >= 4

    def _sforce_active(self, cid: int) -> bool:
        """シールド・フォース: このクリーチャーに紐付いたシールドが今もシールドゾーンにあるか。"""
        s = self.s
        ref = list(s.ref(cid))
        for sh in s.zones["shield"][s.cards[cid].controller]:
            sf = s.cards[sh].sforce_of
            if sf is not None and list(sf) == ref:
                return True
        return False

    def _ignored_ids(self, cid: int) -> set[str]:
        """id で指定して無視されている能力（「真上の▪️能力を無視する」など）。
        発生源は自身の常在型（条件つき含む）と、このクリーチャーに及ぶ継続的効果。"""
        s = self.s
        c = s.cards[cid]
        if c.zone != "bz":
            return set()
        k = ("ign_ids", c.defn, c.face)
        has = self._xcache.get(k)
        if has is None:   # 定義だけで決まる: この面に ignore_ids の常在型があるか
            has = self._xcache[k] = any(ab["kind"] == "static" and ab.get("mod", {}).get("ignore_ids")
                                        for ab in self.fdef(cid).abilities)
        if not has and not s.continuous:
            return set()
        out: set[str] = set()
        env_self = {"you": c.controller, "self": s.ref(cid)}
        for ab in self.fdef(cid).abilities:
            if ab["kind"] == "static" and ab.get("affects") == "self" and ab.get("zone", "bz") == c.zone \
                    and ab.get("mod", {}).get("ignore_ids") \
                    and ("if" not in ab or self._static_cond(ab["if"], env_self)):
                out.update(ab["mod"]["ignore_ids"])
        ref = s.ref(cid)
        for ce in s.continuous:
            if ce["mod"].get("ignore_ids") and self._ce_applies(ce, cid, ref):
                out.update(ce["mod"]["ignore_ids"])
        return out

    def _static_cond(self, cond, env) -> bool:
        """常在型能力の条件。条件の評価中にさらに別の常在型の条件を評価する入れ子では、カード数えを定義の特性で見る（互いの条件を参照し合って再帰しない）。"""
        self._in_static_cond += 1
        try:
            return self.eval_cond(cond, env)
        finally:
            self._in_static_cond -= 1

    def _affects_others(self, cid: int) -> bool:
        """この面が他のカードに及ぶ mod 付きの常在型能力を持つか（定義だけで決まるのでキャッシュする）。"""
        c = self.s.cards[cid]
        r = self._xcache.get((c.defn, c.face))      # 面の定義は (defn, face) で決まる。fdef の面オブジェクト生成を避ける
        if r is not None:
            return r
        d = self.fdef(cid)
        r = self._xcache.get(id(d))
        if r is None:
            r = self._xcache[id(d)] = any(
                ab["kind"] == "static" and "mod" in ab and ab.get("affects") != "self" for ab in d.abilities)
        self._xcache[(c.defn, c.face)] = r
        return r

    @contextlib.contextmanager
    def chars_scope(self):
        """状態を一切変更しない区間（選択肢の列挙など）で chars() の結果を使い回す。
        区間内で状態を書き換える処理を呼んではならない。DMSIM_CHECK=1 では使い回した値を毎回再計算と比べる。
        入れ子の評価中（_in_static_cond / _pw_busy）は値が変わるので使わない。区間の入れ子は外側が優先。"""
        if self._chcache is not None:
            yield
            return
        self._chcache = {}
        self._affc = None
        try:
            yield
        finally:
            self._chcache = None
            self._affc = None

    def chars(self, cid: int, face: int | None = None) -> dict:
        """特性の計算（chars_scope の間は同一状態の結果を使い回す）。返す辞書は呼び出し側が自由に書き換えてよい（コピーを返す）。"""
        cc = self._chcache
        if cc is None or self._in_static_cond or self._pw_busy:
            return self._chars_calc(cid, face)
        out = self.chars_ro(cid, face).copy()
        for k2 in _MUTABLE_CHARS:
            v = out.get(k2)
            if v is not None:
                out[k2] = v.copy()
        return out

    def chars_ro(self, cid: int, face: int | None = None) -> dict:
        """chars() と同じ値を、書き換えない前提でコピーなしに返す（読み取り専用の呼び出し側向け。返した辞書を変更してはならない）。"""
        cc = self._chcache
        if cc is None or self._in_static_cond or self._pw_busy:
            return self._chars_calc(cid, face)
        k = (cid, face)
        r = cc.get(k)
        if r is None:
            r = cc[k] = self._chars_calc(cid, face)
        elif self.check:
            fresh = self._chars_calc(cid, face)
            assert fresh == r, f"chars cache stale: cid={cid} face={face}"
        return r

    def _aff_sources(self):
        """他のカードに mod を及ぼす常在型の発生源。(バトルゾーン, シールド) それぞれ [(発生源, 能力)]。
        chars_scope の間だけ使い回す（状態が変わらない区間）。入れ子の評価中や作成中は None（毎回その場で見る）。"""
        if self._chcache is None or self._in_static_cond or self._pw_busy or self._affc_building:
            return None
        if self._affc is None:
            self._affc_building = True
            try:
                cards = self.s.cards
                aff = self._affects_others
                bz = [(src, ab) for src in self.s.zones["bz"][0] if cards[src].top_of < 0 and aff(src)
                      for _, ab in self.abilities(src, "static")]
                sh = [(src, ab) for p in (0, 1) for src in self.s.zones["shield"][p] if aff(src)
                      for _, ab in self.abilities(src, "static")]
                self._affc = (bz, sh)
            finally:
                self._affc_building = False
        return self._affc

    def _threshold_power(self, cid: int) -> int:
        """条件アトム {power_ge: N} 用の「再帰しないパワー」: 印刷パワーに、適用範囲が合う常在型と
        継続的効果の power 修整（power_when 含む）を重ねた値。常在型の if は通常どおり評価するが、
        評価の連鎖がこのカード自身に戻ってきたら（_threshold_busy）印刷パワーだけを返すため、
        条件を評価している常在型自身の修整は数に入らない（＝「印刷パワー＋他の常在修整」）。
        {power_of: "self"} を常在型の if に書くと chars が再入して無限再帰する（ラウンド187で実証）のへの対処。"""
        if cid in self._threshold_busy:
            return self.fdef(cid).power
        self._threshold_busy.add(cid)
        try:
            c = self.s.cards[cid]
            d = self.fdef(cid)
            if c.zone == "bz" and c.seals:
                return d.power   # 封印されているクリーチャーはパワーも印刷どおり（chars と同じ扱い）
            p = d.power
            ref = self.s.ref(cid)
            env_self = {"you": c.controller, "self": ref}
            own = self.abilities(cid, "static")
            mods = [ab["mod"] for _, ab in own
                    if ab["kind"] == "static" and ab.get("affects") == "self" and ab.get("zone", "bz") == c.zone and "mod" in ab
                    and ("if" not in ab or self._static_cond(ab["if"], env_self))]
            cards = self.s.cards
            for src in self.s.zones["bz"][0]:   # _chars_calc と同じ集め方（バトルゾーン→シールドゾーン→継続的効果→付与キーワード）
                if cards[src].top_of >= 0 or not self._affects_others(src):
                    continue
                for _, ab in self.abilities(src, "static"):
                    aff = ab.get("affects", {})
                    if ab.get("zone", "bz") != "bz":
                        continue
                    if "mod" in ab and aff != "self" and (aff.get("zone", "bz") if isinstance(aff, dict) else "bz") == c.zone:
                        env = {"you": self.s.cards[src].controller, "self": self.s.ref(src)}
                        if self._subject_match(aff, cid, env, None, base=True) and \
                                ("if" not in ab or self._static_cond(ab["if"], env)):
                            mods.append(ab["mod"])
            for zp in (0, 1):
                for src in self.s.zones["shield"][zp]:
                    if not self._affects_others(src):
                        continue
                    for _, ab in self.abilities(src, "static"):
                        aff = ab.get("affects", {})
                        if ab.get("zone") != "shield" or "mod" not in ab or aff == "self":
                            continue
                        if (aff.get("zone", "bz") if isinstance(aff, dict) else "bz") != c.zone:
                            continue
                        env = {"you": self.s.cards[src].controller, "self": self.s.ref(src)}
                        if self._subject_match(aff, cid, env, None, base=True) and \
                                ("if" not in ab or self._static_cond(ab["if"], env)):
                            mods.append(ab["mod"])
            mods += [{**ce["mod"], "power": ce["mod"].get("power", 0) + ce["double_power"].get(cid, 0)}
                     if "double_power" in ce else ce["mod"]
                     for ce in self.s.continuous if self._ce_applies(ce, cid, ref)]
            granted = set()
            for m in mods:
                granted.update(k for k in m.get("grant", []) if k not in self.fdef(cid).keywords)
            for kw in sorted(granted):
                mods += [ab["mod"] for ab in self.rules.keywords[kw]["abilities"]
                         if ab["kind"] == "static" and ab.get("affects") == "self" and "mod" in ab
                         and ab.get("zone", "bz") == c.zone]
            for m in mods:
                pw = m.get("power", 0)
                if isinstance(pw, dict):
                    p += pw["amount"] * (self.count_of(pw["count"], env_self) if "count" in pw else 1)
                else:
                    p += pw
                if "power_when" in m:
                    p += self._power_when(m["power_when"], ref, env_self)
            return p
        finally:
            self._threshold_busy.discard(cid)

    def _chars_calc(self, cid: int, face: int | None = None) -> dict:
        """特性の計算。複数の継続的効果は同時に適用する（608.1）。MTG のようなレイヤーはない。
        常在型能力の効果は固定されず常に範囲を見直す（608.3a）。解決で生成された効果は生成時の範囲に固定（110.2e）。
        許可・禁止（allow / deny）と breaks もここで集める。ルール側はキーワード名を見ない。"""
        c = self.s.cards[cid]
        d = self.fdef(cid, face)
        if face is None and c.zone == "bz" and c.seals:
            # 封印されているクリーチャーは無視される: 種族・タイプ・キーワードを持たず、能力も機能しない
            # （パワーは印刷どおり返し、パワー0の状況起因処理で破壊されないようにする）
            return {"power": d.power, "cost": d.cost, "civs": list(d.civs), "types": [], "races": [],
                    "keywords": set(), "name": d.name, "names": [d.name], "allow": [], "deny": [], "require": [],
                    "breaks": 0, "break_opts": [], "breaks_add": 0, "pay_cost": d.cost, "sac_reduce": 0,
                    "opt_reduce": None, "cost_may": [], "no_leave": [], "must_be_attacked": False,
                    "must_be_attacked_first": False, "must_be_chosen": False, "must_attack_creature": False,
                    "must_attack_creature_first": False,
                    "battle_indestructible": False, "win_all_battles": False, "crystal_soul": 0}
        ch = {"power": d.power, "cost": d.cost, "civs": list(d.civs), "types": list(d.types),
              "races": list(d.races), "keywords": set(d.keywords), "name": d.name, "names": [d.name],
              "allow": [], "deny": [], "require": [], "breaks": 1, "break_opts": [], "breaks_add": 0, "pay_cost": d.cost, "sac_reduce": 0, "opt_reduce": None, "cost_may": [], "no_leave": [], "must_be_attacked": False, "must_be_attacked_first": False,
              "must_be_chosen": False, "must_attack_creature": False, "must_attack_creature_first": False,
              "battle_indestructible": False, "battle_indestructible_filters": [], "win_all_battles": False,
              "indestructible": False, "crystal_soul": d.crystal_soul}
        tkey = self._chars_template_key(cid, face, c, d)
        if tkey is not None:
            t = self._xcache.get(tkey)
            if t is not None:
                out = t.copy()
                for k2 in _MUTABLE_CHARS:
                    v = out.get(k2)
                    if v is not None:
                        out[k2] = v.copy()
                if self.check:
                    self._chars_busy.add(cid)
                    try:
                        fresh = self._chars_calc_body(cid, face, c, d, ch)
                    finally:
                        self._chars_busy.discard(cid)
                    assert fresh == out, f"chars template stale: cid={cid} {tkey}"
                return out
        self._chars_busy.add(cid)
        try:
            r = self._chars_calc_body(cid, face, c, d, ch)
        finally:
            self._chars_busy.discard(cid)
        if tkey is not None:
            t = r.copy()
            for k2 in _MUTABLE_CHARS:
                v = t.get(k2)
                if v is not None:
                    t[k2] = v.copy()
            self._xcache[tkey] = t
        return r

    def _chars_template_key(self, cid, face, c, d):
        """特性が定義とゾーンだけで決まる時の使い回しの鍵（状態をまたいで使える）。決まらない時は None。
        条件: 継続的効果が無い・他に及ぶ常在型の発生源が無い・この面に mod つきの常在型が無い・ACE／G・リンクでない。
        この時 mod は空で、特性は (定義, 面, ゾーン, 下にカードがあるか) で決まる。DMSIM_CHECK=1 では毎回計算と比べる。"""
        if self.s.continuous or c.link:
            return None
        fd = self.fdef(cid, face)
        sk = ("static_mod", c.defn, c.face, face)
        has = self._xcache.get(sk)
        if has is None:
            def fixed(ab):   # 自分自身への、条件もゲートも数え上げも無い定数の mod（ブロッカー等のキーワードの常在型）
                if ab["kind"] != "static" or "mod" not in ab:
                    return True
                if ab.get("affects") != "self" or "if" in ab or any(ab.get(g) for g in ("sst", "stp", "dswitch", "sforce", "accel", "fort_e", "odrive")):
                    return False
                m = ab["mod"]
                if "power_when" in m or "cost_may" in m or "ignore" in m or "ignore_ids" in m or "grant" in m:
                    return False
                if any(isinstance(m.get(k), dict) for k in ("power", "breaks", "breaks_add", "cost")):
                    return False
                return not any(isinstance(e, dict) and e.get("once") for e in m.get("allow", []))
            abs_ = list(fd.abilities) + list(self.rules.cards[c.defn].abilities)
            has = self._xcache[sk] = bool(getattr(d, "ace", False)) or not all(fixed(ab) for ab in abs_)
        if has:
            return None
        ig = self.rules.ignore_defs
        if ig and any(self.s.cards[o].defn in ig for o in self.s.zones["bz"][0]):
            return None
        asrc = self._aff_sources()
        if asrc is None:
            cards = self.s.cards
            aff = self._affects_others
            if any(cards[src].top_of < 0 and aff(src) for src in self.s.zones["bz"][0]) or \
                    any(aff(src) for p in (0, 1) for src in self.s.zones["shield"][p]):
                return None
        elif asrc[0] or asrc[1]:
            return None
        return ("chars_t", c.defn, c.face, face, c.zone, bool(c.under), bool(c.seals))

    def _chars_calc_body(self, cid: int, face: int | None, c, d, ch: dict) -> dict:
        """_chars_calc の本体（_chars_busy に cid を入れた状態で呼ぶ）。"""
        if (d.neo or d.grave_evo) and c.zone == "bz" and c.under and "evolution" not in ch["types"]:
            ch["types"].append("evolution")   # NEO進化・墓地進化: カードが下にあれば進化クリーチャーとして扱う
        if d.ace and c.zone == "bz" and "creature" not in ch["types"] and self._ace_active(cid):
            ch["types"].append("creature")   # ACEタマシード（第179弾）: 条件を満たす間だけクリーチャーとして扱う
        own = self.abilities(cid, "static") if face is None else list(enumerate(d.abilities))
        ref = self.s.ref(cid)
        env_self = {"you": c.controller, "self": ref}
        mods = [ab["mod"] for _, ab in own
                if ab["kind"] == "static" and ab.get("affects") == "self" and ab.get("zone", "bz") == c.zone and "mod" in ab
                and ("if" not in ab or self._static_cond(ab["if"], env_self))]   # 条件つきの常在型（例:「墓地が13枚より少なければ攻撃できない」）は常に見直す
        cards = self.s.cards
        aff_others = self._affects_others
        asrc = self._aff_sources()
        if asrc is not None:
            bz_list, sh_list = asrc
        else:
            bz_list = [(src, ab) for src in self.s.zones["bz"][0] if cards[src].top_of < 0 and aff_others(src)
                       for _, ab in self.abilities(src, "static")]
            sh_list = [(src, ab) for p in (0, 1) for src in self.s.zones["shield"][p] if aff_others(src)
                       for _, ab in self.abilities(src, "static")]
        for src, ab in bz_list:   # バトルゾーンの常在型能力（重ねたカードの下は除く）。affects.zone で他のゾーンのカードにも及ぶ
            aff = ab.get("affects", {})
            if ab.get("zone", "bz") != "bz":
                continue   # 別のゾーンで働く常在型（シールド・ゴーの静的など）は、バトルゾーンの発生源からは働かない
            if "mod" in ab and aff != "self" and (aff.get("zone", "bz") if isinstance(aff, dict) else "bz") == c.zone:
                env = {"you": self.s.cards[src].controller, "self": self.s.ref(src)}
                if self._subject_match(aff, cid, env, None, base=True) and \
                        ("if" not in ab or self._static_cond(ab["if"], env)):
                    mods.append(ab["mod"])
        for src, ab in sh_list:   # シールドゾーンから働く常在型（G・城など。zone: shield を宣言した能力だけ）
            aff = ab.get("affects", {})
            if ab.get("zone") != "shield" or "mod" not in ab or aff == "self":
                continue
            if (aff.get("zone", "bz") if isinstance(aff, dict) else "bz") != c.zone:
                continue
            env = {"you": self.s.cards[src].controller, "self": self.s.ref(src)}
            if self._subject_match(aff, cid, env, None, base=True) and \
                    ("if" not in ab or self._static_cond(ab["if"], env)):
                mods.append(ab["mod"])
        mods += [{**ce["mod"], "power": ce["mod"].get("power", 0) + ce["double_power"].get(cid, 0)}
                 if "double_power" in ce else ce["mod"]
                 for ce in self.s.continuous if self._ce_applies(ce, cid, ref)]
        granted = set()
        for m in mods:
            granted.update(k for k in m.get("grant", []) if k not in ch["keywords"])
        for kw in sorted(granted):   # 与えられたキーワードの常在型能力も働く（1段だけ）
            mods += [ab["mod"] for ab in self.rules.keywords[kw]["abilities"]
                     if ab["kind"] == "static" and ab.get("affects") == "self" and "mod" in ab
                     and ab.get("zone", "bz") == c.zone]
        src_of = None   # 発生源つきで記録する mod（cost_may / 回数制限つき allow）の発生源マップ
        if any("cost_may" in m or any(isinstance(e, dict) and e.get("once") for e in m.get("allow", [])) for m in mods):
            src_of = {}
            for _, ab in own:
                if ab["kind"] == "static" and ab.get("affects") == "self" and ab.get("zone", "bz") == c.zone and "mod" in ab:
                    src_of[id(ab["mod"])] = cid
            for src in self.s.zones["bz"][0]:
                if cards[src].top_of >= 0 or not self._affects_others(src):
                    continue
                for _, ab in self.abilities(src, "static"):
                    if "mod" in ab:
                        src_of[id(ab["mod"])] = src
            for ce in self.s.continuous:   # 継続的効果（modify）の mod も発生源に帰属させる（第50弾）
                if ce.get("src") is not None:
                    src_of[id(ce["mod"])] = ce["src"]
        for m in mods:
            pw = m.get("power", 0)
            if isinstance(pw, dict):   # {amount, count}: 「〜ひとつにつき +N」
                ch["power"] += pw["amount"] * (self.count_of(pw["count"], env_self) if "count" in pw else 1)
            else:
                ch["power"] += pw
            if "power_when" in m:
                ch["power"] += self._power_when(m["power_when"], ref, env_self)
            ch["keywords"].update(m.get("grant", []))
            for e in m.get("allow", []):   # 回数制限つき許可は発生源を付けて記録する（選択肢側で使用済みを判定）
                ch["allow"].append({**e, "src": (src_of or {}).get(id(m), cid)}
                                    if isinstance(e, dict) and e.get("once") else e)
            ch["deny"] += m.get("deny", [])
            ch["require"] += m.get("require", [])
            if "no_leave" in m:   # 「バトルゾーンを離れない」（第49弾）。true は無条件、辞書は例外の指定
                nl = m["no_leave"]
                ch["no_leave"].append({} if nl is True else dict(nl))
            _mba = m.get("must_be_attacked")
            if isinstance(_mba, dict):   # 「各ターン、相手のクリーチャーがはじめて攻撃するなら、可能ならこのクリーチャーを攻撃する」（第160弾）: そのクリーチャーの初回攻撃だけ攻撃先を制限する
                ch["must_be_attacked_first"] = True
            elif _mba:   # 「相手のクリーチャーが攻撃する時、可能ならこのクリーチャーを攻撃する」（第51弾）
                ch["must_be_attacked"] = True
            if m.get("must_be_chosen"):   # 「相手が選ぶ時、可能ならこのクリーチャーを選ぶ」（第199弾）
                ch["must_be_chosen"] = True
            _mac = m.get("must_attack_creature")
            if isinstance(_mac, dict):   # 「可能ならクリーチャーを攻撃する」（第171弾）: そのクリーチャーの初回攻撃だけ、攻撃できるクリーチャーがいればプレイヤーを攻撃できない
                ch["must_attack_creature_first"] = True
            elif _mac:   # 常時: 攻撃できるクリーチャーがいればプレイヤーを攻撃できない
                ch["must_attack_creature"] = True
            if m.get("battle_indestructible") is True:   # 「バトル中、このクリーチャーは破壊されない」（第59弾）
                ch["battle_indestructible"] = True
            elif isinstance(m.get("battle_indestructible"), dict):   # 「〜とのバトル中、破壊されない」（第122弾）: 相手はバトル時に判定
                ch["battle_indestructible_filters"].append(m["battle_indestructible"]["opponent_filter"])
            if m.get("win_all_battles"):   # 「このクリーチャーはすべてのバトルに勝つ」（第61弾）
                ch["win_all_battles"] = True
            if m.get("indestructible"):   # 「破壊されない」（第127弾）
                ch["indestructible"] = True
            if m.get("crystal_soul"):   # 水晶ソウルの付与（第154弾）: 自前宣言と競合したら大きい方
                ch["crystal_soul"] = max(ch["crystal_soul"], m["crystal_soul"])
            for cv in m.get("add_civs", []):   # 文明追加（第62弾）
                if cv not in ch["civs"]:
                    ch["civs"].append(cv)
            for r in m.get("add_races", []):   # 種族追加（「種族に〜を追加する」）
                if r not in ch["races"]:
                    ch["races"].append(r)
            for nm in m.get("add_names", []):   # 名前の追加（「名前は《〜》も持つ」。バンドC2 U97）。主名（name）は変えず、名前の集合（names）に足す
                if nm not in ch["names"]:
                    ch["names"].append(nm)
            if "breaks_add" in m:   # 「シールドをさらにN枚ブレイクする／N枚少なくブレイクする」相対指定（負値も可）。集約の最後に break_opts の各値へ加算する
                # 辞書形 {amount, count}（第170弾）: 「〜1枚につき、さらに1枚ブレイクする」（dmc59-006 型）
                ba = m["breaks_add"]
                if isinstance(ba, dict):
                    ch["breaks_add"] += ba["amount"] * self.count_of(ba["count"], env_self)
                else:
                    ch["breaks_add"] += ba
            if "breaks" in m:   # ブレイカー能力ごとのブレイク数（509.2b）。使う能力は攻撃時に選ぶ（509.2c）
                b = m["breaks"]
                if isinstance(b, dict):   # dict 形式はすべて「base + 値」（base は既定1、第145弾）: {count} は base+数（クルー・ブレイカー、第130弾）、
                    # {amount, count} は base+係数×数（dmd10-008 型）、式形式 {civ_count: ...} は base+式の値（第79弾、dmc34-025 型）。
                    # バラエティ・ブレイカーは {distinct_cost_count: ..., base: 0} でちょうど種類数になる
                    v = b.get("amount", 1) * self.count_of(b["count"], env_self) if "count" in b else self.count_of(b, env_self)
                    n = b.get("base", 1) + v
                    ch["break_opts"].append(n)
                    ch["breaks"] = max(ch["breaks"], n)
                else:
                    ch["break_opts"].append(b)
                    ch["breaks"] = max(ch["breaks"], b)
            elif "breaks" not in m:
                ch["breaks"] = max(ch["breaks"], 1)
        for ce in self.s.continuous:     # ダイナモ: 発生源のクリーチャーのパワーと能力（常在型の許可・禁止・ブレイク数・キーワード）を加える
            src = ce.get("add_from")
            if src and src[0] != cid and self.s.alive(src) and src[0] not in self._adding and self._ce_applies(ce, cid, ref):
                self._adding.add(src[0])
                try:
                    sc = self.chars(src[0])
                finally:
                    self._adding.discard(src[0])
                ch["power"] += sc["power"]
                ch["keywords"].update(sc["keywords"])
                for k in ("allow", "deny", "require", "break_opts"):
                    ch[k] += sc[k]
                ch["no_leave"] += sc["no_leave"]
                ch["must_be_attacked"] = ch["must_be_attacked"] or sc["must_be_attacked"]
                ch["must_be_attacked_first"] = ch["must_be_attacked_first"] or sc.get("must_be_attacked_first", False)
                ch["must_attack_creature"] = ch["must_attack_creature"] or sc["must_attack_creature"]
                ch["must_attack_creature_first"] = ch["must_attack_creature_first"] or sc.get("must_attack_creature_first", False)
                ch["battle_indestructible"] = ch["battle_indestructible"] or sc["battle_indestructible"]
                ch["battle_indestructible_filters"] += sc.get("battle_indestructible_filters", [])
                ch["win_all_battles"] = ch["win_all_battles"] or sc["win_all_battles"]
                ch["indestructible"] = ch["indestructible"] or sc.get("indestructible", False)
                ch["breaks"] = max(ch["breaks"], sc["breaks"])
        if any("cost_may" in m for m in mods):   # 任意のコスト軽減（cost_may）の発生源を引く（once の使用記録用）
            for m in mods:
                if "cost_may" in m:
                    ch["cost_may"].append({**m["cost_may"], "src": (src_of or {}).get(id(m), cid)})
        cost_min = 0
        for m in mods:      # 支払うコストの増減（コスト参照の cost は変えない: 「コスト5以下」はカードのコストで見る）
            if "cost" in m:
                cm = m["cost"]
                if isinstance(cm, dict):
                    n = self.count_of(cm["count"], env_self) if "count" in cm else 1
                    ch["pay_cost"] += cm["amount"] * n
                else:
                    ch["pay_cost"] += cm
            cost_min = max(cost_min, m.get("cost_min", 0))
            ch["sac_reduce"] += m.get("sac_reduce", 0)
            if "opt_reduce" in m:
                ch["opt_reduce"] = m["opt_reduce"]
        ch["pay_cost"] = max(cost_min, ch["pay_cost"])        # コストは0より小さくならない（既定）
        for m in mods:      # パワード・ブレイカー: 最終パワー N ごとに1つ多くブレイクする（ブレイカー能力の1つ）
            if m.get("breaks_per_power"):
                n = 1 + max(0, ch["power"]) // m["breaks_per_power"]
                ch["break_opts"].append(n)
                ch["breaks"] = max(ch["breaks"], n)
        if ch["breaks_add"]:   # 相対ブレイク（breaks_add）: max 合成の後に、使う能力の値すべて（能力が無い場合の既定1を含む）へ加算する。
            # 509.2c の選択肢も加算後の集合になる。0 未満にはならない。breaks_add が 0 のカードでは従来と完全一致する
            if not ch["break_opts"]:
                ch["break_opts"] = [ch["breaks"]]
            ch["break_opts"] = [max(0, v + ch["breaks_add"]) for v in ch["break_opts"]]
            ch["breaks"] = max(ch["break_opts"])
        if c.link and c.zone == "bz" and not self._link_merging:   # G・リンク: グループ全員の特性を統合する
            members = [m for m in self.link_members(cid) if m != cid]
            if members:
                self._link_merging = True
                try:
                    parts = [self.chars(m) for m in members]
                finally:
                    self._link_merging = False
                for p in parts:
                    ch["power"] += p["power"]
                    ch["cost"] += p["cost"]
                    ch["pay_cost"] += p["pay_cost"]
                    ch["civs"] += [x for x in p["civs"] if x not in ch["civs"]]
                    ch["types"] += [x for x in p["types"] if x not in ch["types"]]
                    ch["races"] += [x for x in p["races"] if x not in ch["races"]]
                    ch["keywords"].update(p["keywords"])
                    ch["allow"] += p["allow"]
                    ch["deny"] += p["deny"]
                    ch["require"] += p["require"]
                    ch["no_leave"] += p["no_leave"]
                    ch["break_opts"] += p["break_opts"]
                    ch["breaks"] = max(ch["breaks"], p["breaks"])
                    ch["breaks_add"] = max(ch["breaks_add"], p["breaks_add"])   # リンク統合でも伝播させる（breaks と同じく max。メンバー側の break_opts は各メンバーの計算で加算済み）
                    ch["crystal_soul"] = max(ch["crystal_soul"], p["crystal_soul"])
                    ch["sac_reduce"] += p["sac_reduce"]
        ch["keywords"] = sorted(ch["keywords"])   # 状態（LKI）に入るので JSON にできる形で返す
        return ch

    def _permits_face(self, cid: int, action: str, face: int | None) -> bool:
        return self.permits(cid, action, face=face)

    def permits(self, cid: int, action: str, other: int | None = None, face: int | None = None) -> bool:
        """101.2:「できない」は「できる」に勝つ。禁止 → 許可 → 既定値の順に見る。
        other は相手側のカード（攻撃先・攻撃クリーチャー・ブロッカー）。要素の other フィルタはそれに当てる。"""
        ch = self.chars_ro(cid, face)

        def hit(entries):
            for e in entries:
                if isinstance(e, str):
                    if e == action:
                        return True
                elif e["action"] == action and (other is None or self.filter_match(other, self._other_filter(e.get("other", {}), cid))):
                    if "max_per_turn" in e:   # 第182弾（実行制限・回数型）: そのターンに count 種の出来事を
                        # max_per_turn 回以上していれば禁止。count 省略時は action 名を履歴 kind とする
                        kind = e.get("count", e["action"])
                        if self.s.turn_counters.get(f"hist:{kind}:{self.s.cards[cid].controller}", 0) >= e["max_per_turn"]:
                            return True
                    else:
                        return True
            return False
        if hit(ch["deny"]):
            return False
        if hit(ch["allow"]):
            return True
        return self.rules.actions[action]["default"]

    def _other_filter(self, f: dict, cid: int) -> dict:
        """allow/deny の other フィルタ: 値が式なら許可側のカード（self）を基準に評価する（第126弾。candidates と同じ前評価）。"""
        if not any(isinstance(v, dict) for v in f.values()):
            return f
        env = {"you": self.s.cards[cid].controller, "self": self.s.ref(cid)}
        return {k: self.eval_expr(v, env) if isinstance(v, dict) else v for k, v in f.items()}

    def _duration(self, dur: str, env: dict) -> str:
        if dur == "until_next_own_turn_start":
            return f"until_turn_start:{env['you']}"
        return dur

    def _mark_key(self, name: str, scope: str, env: dict) -> str:
        """mark の印のキー合成（op mark と cond marked で共用。バンドB 基盤 mark-scope）。
        scope: turn（既定。turn_counters に名前そのまま）/ attack（その攻撃の中だけ。current_attack で修飾）/
        game（game_counters に名前そのまま。ターン開始で消えない）。of_self の接尾辞は op_mark 側で付ける。"""
        if scope == "attack":
            return f"{name}:atk{self.s.turn_counters.get('current_attack', 0)}"
        return name

    def ask(self, t: dict, player: int, kind: str, options: list[dict], mn: int = 1, mx: int = 1, prompt: str = ""):
        """(answer, None) か (None, Decision) を返す。選択肢が一意なら決定を出さない。"""
        if "answer" in t:
            return t.pop("answer"), None
        if mn == mx == len(options) and kind != "order_cards":
            return list(range(len(options))), None
        if self.check:
            for o in options:
                check_shape(o, Option)
        return None, {"player": player, "kind": kind, "options": options, "min": mn, "max": mx, "prompt": prompt}

    def _push(self, *tasks):
        """引数の先頭から順に実行されるように積む。"""
        for t in reversed(tasks):
            self.s.tasks.append(t)

    def _pop(self, t):
        assert self.s.tasks[-1] is t
        self.s.tasks.pop()

    def note_public(self, kind: str, cid: int | None = None, viewers=None, *, player: int | None = None,
                    zone: str | None = None):
        """公開イベントを s.pub に追記する（公平探索が「誰が何を見たか」を信念に残すための記録）。
        kind: "reveal"（相手にも見せた）/ "look"（viewers だけが見た）/ "face_up"（表向きにした）/
              "shuffle"（player の zone を切り直した。それまでの位置の知識は無効）。
        viewers: 見たプレイヤーのリスト。None なら全員。cid があれば、その時点の gen・defn・zone・位置を記録する。"""
        s = self.s
        rec = {"n": len(s.pub), "turn": s.turn, "kind": kind,
               "viewers": [0, 1] if viewers is None else sorted(viewers)}
        if cid is not None:
            c = s.cards[cid]
            lst = s.zones[c.zone][0 if self.zshared(c.zone) else c.owner] if c.zone in s.zones else []
            rec.update(cid=cid, gen=c.gen, defn=c.defn, owner=c.owner, zone=c.zone,
                       idx=lst.index(cid) if cid in lst else -1)
        if player is not None:
            rec["player"] = player
        if zone is not None:
            rec["zone"] = zone
        s.pub.append(rec)

    def _shuffle(self, p: int):
        self.note_public("shuffle", player=p, zone="deck")
        deck = self.s.zones["deck"][p]
        for i in range(len(deck) - 1, 0, -1):
            j = rng_below(self.s, i + 1)
            deck[i], deck[j] = deck[j], deck[i]

    def _raw_move(self, cid: int, to: str, position: str = "top", controller: int | None = None):
        """イベントを通さない移動（ゲーム準備用と、イベント適用の内部処理）。"""
        s = self.s
        c = s.cards[cid]
        frm = c.zone
        if c.zone == "hold":
            s.hold.remove(cid)
        else:
            lst = self.zlist(c.zone, c.controller if self.zshared(c.zone) else c.owner)
            if cid in lst:      # シールドの束の下のカードはゾーンの並びに入っていない（113.2）
                lst.remove(cid)
            if not (to == "deck" and c.zone == "deck"):   # 山札の中での並べ替え（見たカードを下に置く等）は山札から離れない
                self._note_deck(c)
        if c.link and to != "bz":                   # G・リンク: バトルゾーンを離れたらリンクから外れる
            self.unlink(cid)
        c.gen += 1                                  # 新しいオブジェクトになる（400.5）
        if to != "mana":
            c.face_down = False                     # 裏向きはマナゾーンにある間だけの状態（水晶武装）
        c.zone = to
        c.tapped = to == "mana" and len(self.cdef(cid).civs) > 1   # 多色カードはタップしてマナに置かれる（405.1）
        c.face_up = self.rules.zones[to]["public"]
        c.controller = c.owner if controller is None else controller
        c.entered_turn = s.turn if to == "bz" else -1
        c.face = -1
        if to == "bz":
            s.seq += 1
            c.entered_seq = s.seq
            if self.cdef(cid).faces:
                c.face = 0          # ツインパクトはクリーチャー側としてバトルゾーンにある（810.4）
        if c.top_of >= 0:   # 下のカードだけが動く時は、上のカードの under から外す（メテオバーン等で下だけが離れる場合）
            t = s.cards[c.top_of]
            if cid in t.under:
                t.under.remove(cid)
        c.under, c.top_of = [], -1
        c.exlife_of = None                          # 一度離れたシールドは紐付けが外れる
        c.sforce_of = None                          # シールド・フォースの紐付けも同様
        c.fortifies = None                          # 城の要塞化先も同様（第178弾）
        c.no_untap_next = False                     # ゾーン移動で新しいオブジェクトになるので凍結の印も消える
        c.hyper = False                             # ハイパーモードも新しいオブジェクトでは解ける
        if to != "hand" and frm in ("hand", "hold"):
            c.strigger_off = False                  # S・トリガーの印は手札にある間だけ有効（手札を離れたら消える。バンドC2 U68）
            c.strigger_on = False
        c.sst = False                               # スーパー・S・トリガーの追加能力の印も消える
        c.stp = False                               # S・トリガー・プラスの印も消える
        c.odrive = False                            # O・ドライブの印も消える
        c.odrive_civs = []
        c.summon_tapped = []                        # フォートEの召喚時タップ記録も消える
        c.summon_fuel = []                          # 第189弾: 召喚時の支払い行動で選んだカードも消える
        c.bazurenda = 0                             # バズレンダの追加支払い回数も消える
        c.vivid = False                             # ビビッドローの表向きも消える（引いたターンの記録 drawn_turn は残す）
        c.dswitched = False                         # Dスイッチの使用済みも消える（新しいオブジェクトとして出直したら再び使える。第151弾）
        dest = self.zlist(to, c.controller if self.zshared(to) else c.owner)
        if position == "top" and self.rules.zones[to]["ordered"]:
            dest.insert(0, cid)
        else:
            dest.append(cid)

    def _to_hold(self, cid: int):
        """保留状態にする（409, 601.1b）。gen は変えない（まだ移動していない）。"""
        c = self.s.cards[cid]
        self.zlist(c.zone, c.owner).remove(cid)
        self._note_deck(c)
        c.zone = "hold"
        self.s.hold.append(cid)

    def _note_deck(self, c: Card):
        """山札の最後の1枚が離れた瞬間を記録する。後で山札にカードが戻っても敗北は取り消されない（104.2b）。"""
        if c.zone == "deck" and not self.s.zones["deck"][c.owner] and c.owner not in self.s.deck_emptied:
            self.s.deck_emptied.append(c.owner)

    @staticmethod
    def _rel(who, env: dict) -> int:
        if isinstance(who, dict):   # {var: 名前}: choose_player（第192弾）が入れた相対指定を引く
            return Engine._rel(env["vars"][who["var"]], env)
        you = env["you"]
        return {"you": you, "opp": 1 - you}[who]
