"""Rust 製エンジンコア（rust/dmcore）との橋渡し（試作）。

dmcore が入っていない環境でも、このモジュールの import は失敗しない（available() が False を返す）。
境界は「状態そのもの」: Rust 側の State を Python から clone / digest / to_json する。ルール・カード定義の読み込みと検証は
Python に残し、準備に必要な最小の情報（new_game_spec）だけを JSON で渡す。
"""
from __future__ import annotations

import json

try:
    import dmcore  # maturin develop / pip install rust/dmcore/target/wheels/*.whl
except ImportError:  # pragma: no cover - dmcore が無い環境
    dmcore = None


def available() -> bool:
    return dmcore is not None


def new_game_spec(rules, decks: list[list[str]], seed: int, first_player: int) -> dict:
    z = rules.zones
    return {"decks": decks, "zones": list(z),
            "public": {k: v["public"] for k, v in z.items()},
            "ordered": {k: v["ordered"] for k, v in z.items()},
            "shared": {k: v["shared"] for k, v in z.items()},
            "multi_civ": {k: len(c.civs) > 1 for k, c in rules.cards.items()},
            "steps": list(rules.steps), "seed": seed, "first_player": first_player}


def new_game(rules, decks: list[list[str]], seed: int, first_player: int = 0):
    """Engine.new_game と同じ準備を Rust で行い、State を返す。"""
    return dmcore.State.new_game(json.dumps(new_game_spec(rules, decks, seed, first_player)))


# ---- 段階1: エンジン本体（Rust）----
_OK_ALLOW = {"block", "attack_summoning_sick", "slayer", "guardman"}
_OK_DENY = {"attack_player", "attack_creature", "be_blocked", "be_attacked"}
_OK_KW = {"blocker", "cannot_attack_player", "cannot_attack", "double_breaker", "speed_attacker", "slayer", "unblockable",
          "triple_breaker", "cannot_be_attacked", "guardman", "world_breaker", "quad_breaker", "null_breaker"}


def _simple_effect(ops) -> bool:
    for o in ops:
        k = o["op"]
        if k == "draw" and set(o) <= {"op", "count", "player"} and o.get("player", "you") in ("you", "opp", "each") and isinstance(o.get("count", 1), int):
            continue
        if k == "shuffle" and set(o) <= {"op", "player"} and o.get("player", "you") in ("you", "opp"):
            continue
        if k == "may" and set(o) <= {"op", "body"} and _simple_effect(o["body"]):
            continue
        if k in ("tap", "untap") and o.get("select") == {"ref": "self"} and set(o) <= {"op", "select"}:
            continue
        return False
    return True


_OK_WHEN = ({"event": "move", "to": "bz", "subject": "self"}, {"event": "attack", "subject": "self"})


def _simple_trigger(ab) -> bool:
    """段階2-d: 「出た時」「攻撃する時」の誘発で、効果が 引く・（任意で）引く・自身のタップ/アンタップ だけのもの。"""
    return ab["kind"] == "trigger" and set(ab) <= {"kind", "when", "effect"} and ab["when"] in _OK_WHEN \
        and _simple_effect(ab["effect"])


def _self_mods(d):
    """段階2-c: 自分自身にだけ及ぶ単純な常在型（許可・禁止・ブレイク数）だけの札の (allow, deny, breaks)。他は None。
    段階2-d: 単純な誘発（_simple_trigger）は許す（誘発の中身は Rust 側の effect インタプリタが動かす）。"""
    allow, deny, breaks = [], [], []
    for ab in d.abilities:
        if _simple_trigger(ab):
            continue
        if ab["kind"] != "static" or ab.get("affects") != "self" or "if" in ab or ab.get("zone", "bz") != "bz":
            return None
        for k, v in ab.get("mod", {}).items():
            if k == "allow" and all(isinstance(x, str) and x in _OK_ALLOW for x in v):
                allow += v
            elif k == "deny" and all(isinstance(x, str) and x in _OK_DENY for x in v):
                deny += v
            elif k == "breaks" and isinstance(v, int) and not isinstance(v, bool):
                breaks.append(v)
            else:
                return None
    return allow, deny, breaks


def _is_plain(d) -> bool:
    """Rust が動かせる札（段階2-c）: 常在型は自分自身への単純な許可・禁止・ブレイク数だけ（誘発・置換・起動・特別な出し方は無い）のクリーチャー。"""
    import dataclasses
    from .defs import CardDef
    if d.types != ["creature"] or d.power <= 0:
        return False
    if any("コマンド" in r for r in d.races):   # 出た時に封印の解放（seal_release）が走る
        return False
    if not set(d.keywords) <= _OK_KW or _self_mods(d) is None:
        return False
    skip = {"id", "name", "types", "civs", "cost", "power", "mana", "races", "text", "abilities", "keywords", "source"}
    for f in dataclasses.fields(CardDef):
        if f.name in skip:
            continue
        dv = f.default if f.default is not dataclasses.MISSING else f.default_factory()
        if getattr(d, f.name) != dv:
            return False
    return True


def rules_bundle(rules) -> dict:
    return {"actions": {k: bool(v["default"]) for k, v in rules.actions.items()},
            "zones": [[k, {"public": v["public"], "ordered": v["ordered"], "shared": v["shared"]}]
                      for k, v in rules.zones.items()],
            "steps": list(rules.steps),
            "cards": {i: {"name": d.name, "civs": list(d.civs), "cost": d.cost, "power": d.power,
                          "mana": d.mana, "plain": _is_plain(d), "types": list(d.types), "races": list(d.races),
                          "keywords": list(d.keywords), "abil": d.abilities if _is_plain(d) else [],
                          **dict(zip(("allow", "deny", "breaks"), (_self_mods(d) or ([], [], []))))}
                      for i, d in rules.cards.items()}}


class RustSession:
    """engine_api.Session と同じ操作（decision / apply / fork / digest / observe）を Rust エンジンで満たす。
    未移植の語彙に当たったら dmcore.Unsupported を送出する。"""

    def __init__(self, eng, n: int = 0):
        self.eng, self._n = eng, n

    @classmethod
    def open(cls, rules, spec: dict, bundle: dict | None = None) -> "RustSession":
        if spec.get("kind", "new_game") != "new_game":
            raise dmcore.Unsupported("scenario")
        st = new_game(rules, spec["decks"], spec.get("seed", 1), spec.get("first_player", 0))
        return cls(dmcore.Engine.open(st.to_json(), json.dumps(bundle or rules_bundle(rules))))

    def decision(self):
        t = self.eng.advance()
        return None if t is None else {**json.loads(t), "id": self._n}

    def result(self):
        r = self.eng.result()
        return None if r is None else json.loads(r)

    def digest(self) -> str:
        return self.eng.digest()

    def observe(self, view: str = "full") -> dict:
        if view != "full":
            raise dmcore.Unsupported("observe " + view)
        return json.loads(self.eng.to_json())

    def apply(self, answer, digest: bool = False) -> dict:
        d = self.decision()
        if d is None:
            raise RuntimeError("no decision pending")
        if isinstance(answer, dict):
            keys = [o["key"] for o in d["options"]]
            answer = [keys.index(k) for k in answer["keys"]]
        self.eng.answer(list(answer))
        self._n += 1
        out = {"applied": json.loads(self.eng.log())[-1], "decision": self.decision(), "result": self.result()}
        if digest:
            out["digest"] = self.digest()
        return out

    def fork(self) -> "RustSession":
        return RustSession(self.eng.fork(), self._n)
