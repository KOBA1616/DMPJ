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
          "triple_breaker", "cannot_be_attacked", "guardman", "world_breaker", "quad_breaker", "null_breaker",
          "s_trigger", "s_trigger_plus", "super_s_trigger"}


_FILTER_LISTS = ("types", "not_types", "civs", "not_civs", "races")
_FILTER_INTS = ("cost_le", "cost_ge", "power_le", "power_ge")
_FILTER_BOOLS = ("tapped", "multicolor", "colorless")


def _simple_filter(f) -> bool:
    """Rust の filter_ok が Python の filter_match と同じ結果になるキー（値が式でないもの）だけ。"""
    if not isinstance(f, dict):
        return False
    for k, v in f.items():
        if k in _FILTER_LISTS:
            if not (isinstance(v, list) and all(isinstance(x, str) for x in v)) and not (k in ("civs", "not_civs") and isinstance(v, str)):
                return False
        elif k in _FILTER_INTS:
            if not isinstance(v, int) or isinstance(v, bool):
                return False
        elif k in _FILTER_BOOLS:
            if not isinstance(v, bool):
                return False
        elif k in ("race_has", "keyword"):
            if not isinstance(v, str):
                return False
        elif k == "any_of":
            if not (isinstance(v, list) and all(_simple_filter(x) for x in v)):
                return False
        else:
            return False
    return True


def _simple_selector(sel) -> bool:
    """段階2-d: Rust の select が扱えるセレクタ（自身／ゾーン・持ち主・枚数・上から・選ぶ人・types 絞り込み）。"""
    if not isinstance(sel, dict):
        return False
    if sel == {"ref": "self"}:
        return True
    if not set(sel) <= {"zone", "owner", "count", "from_top", "filter", "chooser", "look", "ref", "up_to", "other"}:
        return False
    if "look" in sel and not isinstance(sel["look"], bool):
        return False
    if "ref" in sel:   # 変数（choose の as）を指す形。特殊な参照名は未対応
        r = sel["ref"]
        if not isinstance(r, str) or r in ("self", "self_moved", "self_entered", "crossed", "subject") or r.startswith("event.") \
                or {"zone", "owner", "from_top"} & set(sel):
            return False
    elif sel.get("zone") not in ("hand", "deck", "graveyard", "mana", "bz", "shield") or sel.get("owner", "you") not in ("you", "opp"):
        return False
    if sel.get("chooser", "you") not in ("you", "opp"):
        return False
    c = sel.get("count", 1)
    if not (c == "all" or (isinstance(c, int) and not isinstance(c, bool))):
        return False
    ft = sel.get("from_top", 0)
    if not (isinstance(ft, int) and not isinstance(ft, bool)):
        return False
    if not _simple_filter(sel.get("filter", {})):
        return False
    up = sel.get("up_to", False)
    if not isinstance(up, bool) or (up and c == "all") or (up and "count" not in sel):
        return False
    if "other" in sel and (not isinstance(sel["other"], bool) or "ref" in sel):
        return False
    return True


def _simple_cands(sel) -> bool:
    """数えるだけのセレクタ（Rust の candidates_ro）。"""
    if not isinstance(sel, dict) or not set(sel) <= {"zone", "owner", "from_top", "filter", "ref", "other"}:
        return False
    if "ref" in sel:
        return isinstance(sel["ref"], str) and not sel["ref"].startswith("event.") and sel["ref"] not in ("self_moved", "self_entered", "crossed", "subject") \
            and set(sel) <= {"ref", "filter"} and ("filter" not in sel or _simple_filter(sel["filter"]))
    return sel.get("zone") in ("hand", "deck", "graveyard", "mana", "bz", "shield") and sel.get("owner", "you") in ("you", "opp") \
        and isinstance(sel.get("from_top", 0), int) and ("filter" not in sel or _simple_filter(sel["filter"])) and isinstance(sel.get("other", False), bool)


def _simple_expr(x) -> bool:
    return (isinstance(x, int) and not isinstance(x, bool)) or (isinstance(x, dict) and set(x) == {"count"} and _simple_cands(x["count"]))


def _simple_cond(c) -> bool:
    if not isinstance(c, dict) or len(c) != 1:
        return False
    k, v = next(iter(c.items()))
    if k == "exists":
        return _simple_cands(v)
    if k == "cmp":
        return isinstance(v, list) and len(v) == 3 and _simple_expr(v[0]) and _simple_expr(v[2]) and v[1] in ("<", "<=", "==", ">=", ">")
    if k == "not":
        return _simple_cond(v)
    if k in ("all", "any"):
        return isinstance(v, list) and all(_simple_cond(x) for x in v)
    if k == "is_turn":
        return v in ("you", "opp")
    return False


def _simple_effect(ops, top=True) -> bool:
    for o in ops:
        k = o["op"]
        if k == "if" and set(o) <= {"op", "cond", "then", "else"} and _simple_cond(o.get("cond")) \
                and _simple_effect(o.get("then", []), False) and _simple_effect(o.get("else", []), False):
            continue
        if k == "draw" and set(o) <= {"op", "count", "player"} and o.get("player", "you") in ("you", "opp", "each") and isinstance(o.get("count", 1), int):
            continue
        if k == "shuffle" and set(o) <= {"op", "player"} and o.get("player", "you") in ("you", "opp"):
            continue
        if k == "choose" and top and set(o) <= {"op", "select", "as"} and isinstance(o.get("as"), str) and _simple_selector(o.get("select")):
            continue   # 変数への束縛は最上段だけ（Python は子タスクと env を共有するが、Rust は複製するため）
        if k == "repeat" and set(o) <= {"op", "times", "body"} and isinstance(o.get("times"), int) and _simple_effect(o["body"], False):
            continue
        if k == "may" and set(o) <= {"op", "body"} and _simple_effect(o["body"], False):
            continue
        if k in ("tap", "untap") and set(o) <= {"op", "select"} and _simple_selector(o.get("select")):
            continue
        if k == "move" and set(o) <= {"op", "select", "to", "reason", "position", "tapped"} and isinstance(o.get("tapped", False), bool) and o.get("to") in ("hand", "graveyard", "mana", "deck", "shield", "bz") \
                and isinstance(o.get("reason"), str) and o.get("position", "top") in ("top", "bottom") and _simple_selector(o.get("select")):
            continue
        return False
    return True


_OK_WHEN = ({"event": "move", "to": "bz", "subject": "self"}, {"event": "attack", "subject": "self"})


_OK_EVENTS = {"move", "attack", "battle_win", "turn_start"}
_OK_ZONES = {"hand", "deck", "graveyard", "mana", "bz", "shield"}


def _simple_when(w) -> bool:
    """Rust の when_match が Python の _match_when と同じ結果になる誘発条件（段階3-b）。"""
    if not isinstance(w, dict) or not set(w) <= {"event", "from", "to", "reason", "player", "subject"}:
        return False
    if w.get("event") not in _OK_EVENTS or w.get("subject", "self") != "self" or w.get("player", "you") not in ("you", "opp"):
        return False
    for k in ("from", "to"):
        v = w.get(k)
        if v is not None and not (v in _OK_ZONES or (isinstance(v, list) and all(x in _OK_ZONES for x in v))):
            return False
    return "reason" not in w or isinstance(w["reason"], (str, list))


def _simple_trigger(ab) -> bool:
    """段階3-b: 単純な誘発条件（_simple_when）で、条件 if も単純、効果が単純（_simple_effect）なもの。バトルゾーンか墓地で働く。"""
    return ab["kind"] == "trigger" and set(ab) <= {"kind", "when", "effect", "if", "zone"} and _simple_when(ab["when"]) \
        and ab.get("zone", "bz") in ("bz", "graveyard") and ("if" not in ab or _simple_cond(ab["if"])) \
        and _simple_effect(ab["effect"])


def _self_mods(d):
    """段階2-c: 自分自身にだけ及ぶ単純な常在型（許可・禁止・ブレイク数）だけの札の (allow, deny, breaks)。他は None。
    段階2-d: 単純な誘発（_simple_trigger）は許す（誘発の中身は Rust 側の effect インタプリタが動かす）。"""
    allow, deny, breaks, shield_allow = [], [], [], []
    for ab in d.abilities:
        if _simple_trigger(ab):
            continue
        if ab["kind"] == "static" and ab.get("zone") == "shield" and ab.get("affects") == "self" and "if" not in ab \
                and ab.get("mod") == {"allow": ["s_trigger"]}:
            shield_allow.append("s_trigger")   # S・トリガー（シールドゾーンにある間だけ働く許可）
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
    return allow, deny, breaks, shield_allow


def _is_plain_spell(d) -> bool:
    """Rust が動かせる呪文（段階3-a）: 効果が単純（_simple_effect）で、S・トリガー以外のキーワード・常在型・特別な唱え方を持たない。"""
    import dataclasses
    from ..cards.defs import CardDef
    if d.types != ["spell"] or not d.spell or not _simple_effect(d.spell):
        return False
    if not set(d.keywords) <= {"s_trigger", "charger"}:
        return False
    if d.resolve_to not in ("graveyard", "mana") or ("charger" in d.keywords) != (d.resolve_to == "mana"):
        return False
    for ab in d.abilities:
        if not (ab["kind"] == "static" and ab.get("zone") == "shield" and ab.get("affects") == "self" and "if" not in ab
                and ab.get("mod") == {"allow": ["s_trigger"]}):
            return False
    skip = {"id", "name", "types", "civs", "cost", "power", "mana", "races", "text", "abilities", "keywords", "source", "spell", "resolve_to"}
    for f in dataclasses.fields(CardDef):
        if f.name in skip:
            continue
        dv = f.default if f.default is not dataclasses.MISSING else f.default_factory()
        if getattr(d, f.name) != dv:
            return False
    return True


SPELLS = True   # 段階3-a の呪文を plain に含めるか（False で従来どおりクリーチャーだけ）


def _is_plain(d) -> bool:
    if SPELLS and d.types == ["spell"]:
        return _is_plain_spell(d)
    return _is_plain_creature(d)


def _is_plain_creature(d) -> bool:
    """Rust が動かせる札（段階2-c）: 常在型は自分自身への単純な許可・禁止・ブレイク数だけ（誘発・置換・起動・特別な出し方は無い）のクリーチャー。"""
    import dataclasses
    from ..cards.defs import CardDef
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
            "zt_zones": sorted({z for v in rules.zone_trigger_defs.values() for z in v}),
            "cards": {i: {"name": d.name, "civs": list(d.civs), "cost": d.cost, "power": d.power,
                          "mana": d.mana, "plain": _is_plain(d), "types": list(d.types), "races": list(d.races),
                          "keywords": list(d.keywords), "abil": d.abilities if _is_plain(d) else [],
                          "spell": list(d.spell) if _is_plain(d) and d.types == ["spell"] else [],
                          "resolve_to": d.resolve_to, "zt": i in rules.zone_trigger_defs,
                          **dict(zip(("allow", "deny", "breaks", "shield_allow"), (_self_mods(d) or ([], [], [], []))))}
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
