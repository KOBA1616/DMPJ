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

import os

from ..defs import CardDef, Face, Rules
from ..state import Card, GameState, rng_below
from .combat import CombatMixin
from .events import EventMixin
from .interpreter import InterpreterMixin
from ..types import Option, check_shape
from .registry import TASK_SHAPES, TASKS
from .selectors import SelectorMixin
from .turn import TurnMixin


CHECK = os.environ.get("DMSIM_CHECK") == "1"


class IllegalAnswer(ValueError):
    pass


class Engine(SelectorMixin, EventMixin, InterpreterMixin, TurnMixin, CombatMixin):
    """ゲーム進行の中核。ルールごとの処理は各 Mixin と、registry に登録された task / op が受け持つ。"""

    def __init__(self, rules: Rules, state: GameState, *, step_limit: int = 20000, turn_limit: int = 80,
                 check: bool | None = None):
        self.rules = rules
        self._in_static_cond = 0
        self._adding = set()
        self._link_merging = False
        self._xcache = rules.__dict__.setdefault("_affects_others_cache", {})   # 定義だけで決まるので複製間で共有
        self.check = CHECK if check is None else check   # タスクの形を毎回検査する（テスト・開発者モード用）
        self.s = state
        self._pw_busy = False
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
        out = [(i, ab) for i, ab in enumerate(self.fdef(cid).abilities)
               if (kind is None or ab["kind"] == kind)
               and (not ab.get("sst") or self.s.cards[cid].sst)   # スーパー・S・トリガーの追加能力は印がある時だけ
               and (not ab.get("stp") or self.s.cards[cid].stp)   # S・トリガー・プラスも同様
               and (not ab.get("odrive") or self.s.cards[cid].odrive)]   # O・ドライブで得る能力も同様
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

    def _ignored_ids(self, cid: int) -> set[str]:
        """id で指定して無視されている能力（「真上の▪️能力を無視する」など）。
        発生源は自身の常在型（条件つき含む）と、このクリーチャーに及ぶ継続的効果。"""
        s = self.s
        c = s.cards[cid]
        if c.zone != "bz":
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
        d = self.fdef(cid)
        r = self._xcache.get(id(d))
        if r is None:
            r = self._xcache[id(d)] = any(
                ab["kind"] == "static" and "mod" in ab and ab.get("affects") != "self" for ab in d.abilities)
        return r

    def chars(self, cid: int, face: int | None = None) -> dict:
        """特性の計算。複数の継続的効果は同時に適用する（608.1）。MTG のようなレイヤーはない。
        常在型能力の効果は固定されず常に範囲を見直す（608.3a）。解決で生成された効果は生成時の範囲に固定（110.2e）。
        許可・禁止（allow / deny）と breaks もここで集める。ルール側はキーワード名を見ない。"""
        c = self.s.cards[cid]
        d = self.fdef(cid, face)
        ch = {"power": d.power, "cost": d.cost, "civs": list(d.civs), "types": list(d.types),
              "races": list(d.races), "keywords": set(d.keywords), "name": d.name,
              "allow": [], "deny": [], "require": [], "breaks": 1, "break_opts": [], "pay_cost": d.cost, "sac_reduce": 0, "opt_reduce": None, "cost_may": []}
        if d.neo and c.zone == "bz" and c.under and "evolution" not in ch["types"]:
            ch["types"].append("evolution")   # NEO進化: カードが下にあればNEO進化クリーチャーとして扱う
        own = self.abilities(cid, "static") if face is None else list(enumerate(d.abilities))
        ref = self.s.ref(cid)
        env_self = {"you": c.controller, "self": ref}
        mods = [ab["mod"] for _, ab in own
                if ab["kind"] == "static" and ab.get("affects") == "self" and ab.get("zone", "bz") == c.zone and "mod" in ab
                and ("if" not in ab or self._static_cond(ab["if"], env_self))]   # 条件つきの常在型（例:「墓地が13枚より少なければ攻撃できない」）は常に見直す
        cards = self.s.cards
        for src in self.s.zones["bz"][0]:   # バトルゾーンの常在型能力（重ねたカードの下は除く）。affects.zone で他のゾーンのカードにも及ぶ
            if cards[src].top_of >= 0 or not self._affects_others(src):
                continue
            for _, ab in self.abilities(src, "static"):
                aff = ab.get("affects", {})
                if ab.get("zone", "bz") != "bz":
                    continue   # 別のゾーンで働く常在型（シールド・ゴーの静的など）は、バトルゾーンの発生源からは働かない
                if "mod" in ab and aff != "self" and (aff.get("zone", "bz") if isinstance(aff, dict) else "bz") == c.zone:
                    env = {"you": self.s.cards[src].controller, "self": self.s.ref(src)}
                    if self._subject_match(aff, cid, env, None, base=True) and \
                            ("if" not in ab or self._static_cond(ab["if"], env)):
                        mods.append(ab["mod"])
        for p in (0, 1):   # シールドゾーンから働く常在型（G・城など。zone: shield を宣言した能力だけ）
            for src in self.s.zones["shield"][p]:
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
        mods += [ce["mod"] for ce in self.s.continuous if self._ce_applies(ce, cid, ref)]
        granted = set()
        for m in mods:
            granted.update(k for k in m.get("grant", []) if k not in ch["keywords"])
        for kw in sorted(granted):   # 与えられたキーワードの常在型能力も働く（1段だけ）
            mods += [ab["mod"] for ab in self.rules.keywords[kw]["abilities"]
                     if ab["kind"] == "static" and ab.get("affects") == "self" and "mod" in ab
                     and ab.get("zone", "bz") == c.zone]
        for m in mods:
            pw = m.get("power", 0)
            if isinstance(pw, dict):   # {amount, count}: 「〜ひとつにつき +N」
                ch["power"] += pw["amount"] * (self.count_of(pw["count"], env_self) if "count" in pw else 1)
            else:
                ch["power"] += pw
            if "power_when" in m:
                ch["power"] += self._power_when(m["power_when"], ref, env_self)
            ch["keywords"].update(m.get("grant", []))
            ch["allow"] += m.get("allow", [])
            ch["deny"] += m.get("deny", [])
            ch["require"] += m.get("require", [])
            for r in m.get("add_races", []):   # 種族追加（「種族に〜を追加する」）
                if r not in ch["races"]:
                    ch["races"].append(r)
            if "breaks" in m:   # ブレイカー能力ごとのブレイク数（509.2b）。使う能力は攻撃時に選ぶ（509.2c）
                ch["break_opts"].append(m["breaks"])
            ch["breaks"] = max(ch["breaks"], m.get("breaks", 1))
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
                ch["breaks"] = max(ch["breaks"], sc["breaks"])
        if any("cost_may" in m for m in mods):   # 任意のコスト軽減（cost_may）の発生源を引く（once の使用記録用）
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
            for m in mods:
                if "cost_may" in m:
                    ch["cost_may"].append({**m["cost_may"], "src": src_of.get(id(m), cid)})
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
                    ch["break_opts"] += p["break_opts"]
                    ch["breaks"] = max(ch["breaks"], p["breaks"])
                    ch["sac_reduce"] += p["sac_reduce"]
        ch["keywords"] = sorted(ch["keywords"])   # 状態（LKI）に入るので JSON にできる形で返す
        return ch

    def _permits_face(self, cid: int, action: str, face: int | None) -> bool:
        return self.permits(cid, action, face=face)

    def permits(self, cid: int, action: str, other: int | None = None, face: int | None = None) -> bool:
        """101.2:「できない」は「できる」に勝つ。禁止 → 許可 → 既定値の順に見る。
        other は相手側のカード（攻撃先・攻撃クリーチャー・ブロッカー）。要素の other フィルタはそれに当てる。"""
        ch = self.chars(cid, face)

        def hit(entries):
            for e in entries:
                if isinstance(e, str):
                    if e == action:
                        return True
                elif e["action"] == action and (other is None or self.filter_match(other, e.get("other", {}))):
                    return True
            return False
        if hit(ch["deny"]):
            return False
        if hit(ch["allow"]):
            return True
        return self.rules.actions[action]["default"]

    def _duration(self, dur: str, env: dict) -> str:
        if dur == "until_next_own_turn_start":
            return f"until_turn_start:{env['you']}"
        return dur

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

    def _shuffle(self, p: int):
        deck = self.s.zones["deck"][p]
        for i in range(len(deck) - 1, 0, -1):
            j = rng_below(self.s, i + 1)
            deck[i], deck[j] = deck[j], deck[i]

    def _raw_move(self, cid: int, to: str, position: str = "top", controller: int | None = None):
        """イベントを通さない移動（ゲーム準備用と、イベント適用の内部処理）。"""
        s = self.s
        c = s.cards[cid]
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
        c.under, c.top_of = [], -1
        c.exlife_of = None                          # 一度離れたシールドは紐付けが外れる
        c.no_untap_next = False                     # ゾーン移動で新しいオブジェクトになるので凍結の印も消える
        c.hyper = False                             # ハイパーモードも新しいオブジェクトでは解ける
        c.sst = False                               # スーパー・S・トリガーの追加能力の印も消える
        c.stp = False                               # S・トリガー・プラスの印も消える
        c.odrive = False                            # O・ドライブの印も消える
        c.bazurenda = 0                             # バズレンダの追加支払い回数も消える
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
    def _rel(who: str, env: dict) -> int:
        you = env["you"]
        return {"you": you, "opp": 1 - you}[who]
