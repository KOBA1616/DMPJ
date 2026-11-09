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
def _is_plain(d) -> bool:
    """能力・キーワード・特別な出し方を一切持たないクリーチャー（段階1で Rust が動かせる札）。"""
    import dataclasses
    from .defs import CardDef
    if d.types != ["creature"]:
        return False
    skip = {"id", "name", "types", "civs", "cost", "power", "mana", "races", "text"}
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
                          "mana": d.mana, "plain": _is_plain(d)} for i, d in rules.cards.items()}}


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
