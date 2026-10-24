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

from ..defs import CardDef, Rules
from ..state import Card, GameState, rng_below
from .combat import CombatMixin
from .events import EventMixin
from .interpreter import InterpreterMixin
from .registry import TASKS
from .selectors import SelectorMixin
from .turn import TurnMixin


class IllegalAnswer(ValueError):
    pass


class Engine(SelectorMixin, EventMixin, InterpreterMixin, TurnMixin, CombatMixin):
    """ゲーム進行の中核。ルールごとの処理は各 Mixin と、registry に登録された task / op が受け持つ。"""

    def __init__(self, rules: Rules, state: GameState, *, step_limit: int = 20000, turn_limit: int = 80):
        self.rules = rules
        self.s = state
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
        s.tasks.append({"t": "turn", "phase": "start", "cp": True})
        return e

    def clone(self) -> "Engine":
        e = Engine(self.rules, self.s.clone(), step_limit=self.step_limit, turn_limit=self.turn_limit)
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

    def zshared(self, z: str) -> bool:
        return self.rules.zones[z]["shared"]

    def zlist(self, z: str, p: int) -> list[int]:
        return self.s.zones[z][0 if self.zshared(z) else p]

    def bz_tops(self, controller: int | None = None) -> list[int]:
        return [c for c in self.s.zones["bz"][0]
                if self.s.cards[c].top_of < 0 and (controller is None or self.s.cards[c].controller == controller)]

    def chars(self, cid: int) -> dict:
        """特性の計算。複数の継続的効果は同時に適用する（608.1）。MTG のようなレイヤーはない。
        常在型能力の効果は固定されず常に範囲を見直す（608.3a）。解決で生成された効果は生成時の範囲に固定（110.2e）。"""
        c = self.s.cards[cid]
        d = self.cdef(cid)
        ch = {"power": d.power, "cost": d.cost, "civs": list(d.civs), "types": list(d.types),
              "races": list(d.races), "keywords": set(d.keywords), "name": d.name}
        if c.zone != "bz":
            return ch
        mods = []
        for src in self.bz_tops():
            for ab in self.cdef(src).abilities:
                if ab["kind"] == "static" and "mod" in ab:
                    env = {"you": self.s.cards[src].controller, "self": self.s.ref(src)}
                    if self._subject_match(ab.get("affects", {}), cid, env, None, base=True):
                        mods.append(ab["mod"])
        ref = self.s.ref(cid)
        mods += [ce["mod"] for ce in self.s.continuous if ref in ce["affected"]]
        for m in mods:
            ch["power"] += m.get("power", 0)
            ch["keywords"].update(m.get("grant", []))
        return ch

    def ask(self, t: dict, player: int, kind: str, options: list[dict], mn: int = 1, mx: int = 1, prompt: str = ""):
        """(answer, None) か (None, Decision) を返す。選択肢が一意なら決定を出さない。"""
        if "answer" in t:
            return t.pop("answer"), None
        if mn == mx == len(options):
            return list(range(len(options))), None
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
            self.zlist(c.zone, c.controller if self.zshared(c.zone) else c.owner).remove(cid)
        c.gen += 1                                  # 新しいオブジェクトになる（400.5）
        c.zone = to
        c.tapped = to == "mana" and len(self.cdef(cid).civs) > 1   # 多色カードはタップしてマナに置かれる
        c.face_up = self.rules.zones[to]["public"]
        c.controller = c.owner if controller is None else controller
        c.entered_turn = s.turn if to == "bz" else -1
        c.under, c.top_of = [], -1
        dest = self.zlist(to, c.controller if self.zshared(to) else c.owner)
        if position == "top" and self.rules.zones[to]["ordered"]:
            dest.insert(0, cid)
        else:
            dest.append(cid)

    def _to_hold(self, cid: int):
        """保留状態にする（409, 601.1b）。gen は変えない（まだ移動していない）。"""
        c = self.s.cards[cid]
        self.zlist(c.zone, c.owner).remove(cid)
        c.zone = "hold"
        self.s.hold.append(cid)

    @staticmethod
    def _rel(who: str, env: dict) -> int:
        you = env["you"]
        return {"you": you, "opp": 1 - you}[who]
