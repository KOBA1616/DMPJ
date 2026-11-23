"""Rust 製エンジンコア（rust/dmcore）との橋渡し（試作）。

dmcore が入っていない環境でも、このモジュールの import は失敗しない（available() が False を返す）。
境界は「状態そのもの」: Rust 側の State を Python から clone / digest / to_json する。ルール・カード定義の読み込みと検証は
Python に残し、準備に必要な最小の情報（new_game_spec）だけを JSON で渡す。
"""
from __future__ import annotations

import json
import os

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
_FILTER_BOOLS = ("tapped", "multicolor", "colorless", "evolution")


def _simple_filter(f) -> bool:
    """Rust の filter_ok が Python の filter_match と同じ結果になるキー（値が式でないもの）だけ。"""
    if not isinstance(f, dict):
        return False
    for k, v in f.items():
        if k in _FILTER_LISTS:
            if not (isinstance(v, list) and all(isinstance(x, str) for x in v)) and not (k in ("civs", "not_civs") and isinstance(v, str)):
                return False
        elif k in _FILTER_INTS:
            if isinstance(v, dict) and set(v) == {"cost_of"} and k in ("cost_le", "cost_ge") \
                    and (isinstance(v["cost_of"], str) or (isinstance(v["cost_of"], dict) and set(v["cost_of"]) == {"ref"})) \
                    and (v["cost_of"] if isinstance(v["cost_of"], str) else v["cost_of"]["ref"]) not in ("crossed",) \
                    and not str(v["cost_of"] if isinstance(v["cost_of"], str) else v["cost_of"]["ref"]).startswith("event."):
                continue   # 参照カードのコスト（解決時に数へ置き換える）
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
    if "under_of" in sel:   # メテオバーン: 自分の下のカード
        return sel["under_of"] == "self" and set(sel) <= {"under_of", "count"} and isinstance(sel.get("count", 1), int) \
            and not isinstance(sel.get("count", 1), bool)
    if not set(sel) <= {"zone", "owner", "count", "from_top", "filter", "chooser", "look", "ref", "up_to", "other"}:
        return False
    if "look" in sel and not isinstance(sel["look"], bool):
        return False
    if "ref" in sel:   # 変数（choose の as）を指す形。特殊な参照名は未対応
        r = sel["ref"]
        if not isinstance(r, str) or r in ("self", "self_moved", "self_entered", "crossed", "subject") or r.startswith("event.") \
                or {"zone", "owner", "from_top"} & set(sel):
            return False
    elif sel.get("zone") not in ("hand", "deck", "graveyard", "mana", "bz", "shield") or sel.get("owner", "you") not in ("you", "opp", "any"):
        return False
    if sel.get("chooser", "you") not in ("you", "opp", "random"):
        return False
    if sel.get("chooser") == "random" and (sel.get("up_to") or sel.get("look") or "total_cost_le" in sel):
        return False
    c = sel.get("count", 1)
    if not (c in ("all", "any") or (isinstance(c, int) and not isinstance(c, bool))):
        return False
    if c == "any" and (sel.get("up_to") or sel.get("chooser") == "random"):
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
    return sel.get("zone") in ("hand", "deck", "graveyard", "mana", "bz", "shield") and sel.get("owner", "you") in ("you", "opp", "any") \
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
        if k == "modify" and set(o) <= {"op", "select", "mod"} and isinstance(o.get("mod"), dict) and set(o["mod"]) == {"power"} \
                and isinstance(o["mod"]["power"], int) and not isinstance(o["mod"]["power"], bool) and isinstance(o.get("select"), dict) \
                and set(o["select"]) == {"ref"} and isinstance(o["select"]["ref"], str) and o["select"]["ref"] not in ("self",):
            continue   # このターンの間のパワー修整（変数で指した対象）
        if k == "modify" and o.get("dynamic") is True and set(o) <= {"op", "select", "mod", "dynamic", "duration"} \
                and o.get("duration", "end_of_turn") == "end_of_turn" and isinstance(o.get("mod"), dict) and set(o["mod"]) == {"deny"} \
                and isinstance(o["mod"]["deny"], list) and all(isinstance(x, str) for x in o["mod"]["deny"]) \
                and isinstance(o.get("select"), dict) and set(o["select"]) <= {"zone", "owner", "filter", "count"} \
                and o["select"].get("zone", "bz") == "bz" and o["select"].get("owner", "you") in ("you", "opp", "any") \
                and o["select"].get("count", "all") == "all" and _simple_filter(o["select"].get("filter", {})):
            continue   # このターンの間の「〜できない」（後から出たクリーチャーにも及ぶ）
        if k == "choose" and set(o) <= {"op", "select", "as"} and isinstance(o.get("as"), str) and _simple_selector(o.get("select")):
            continue   # 子の効果での束縛は、Rust が同じ env を持つタスクすべてに書く（Python の env 共有と同じ結果）
        if k == "play_free" and set(o) <= {"op", "select", "as"} and isinstance(o.get("as", ""), str) and _simple_selector(o.get("select")) and o["select"].get("zone") in ("hand", "graveyard"):
            continue
        if k == "modal" and set(o) <= {"op", "modes", "count"} and isinstance(o.get("count", 1), int) \
                and isinstance(o.get("modes"), list) and 1 <= o.get("count", 1) <= len(o["modes"]) \
                and all(isinstance(m, list) and _simple_effect(m, False) for m in o["modes"]):
            continue
        if k == "end_turn" and set(o) == {"op"}:
            continue
        if k == "win" and set(o) <= {"op", "player"} and o.get("player", "you") in ("you", "opp"):
            continue
        if k == "repeat" and set(o) <= {"op", "times", "body"} and isinstance(o.get("times"), int) and _simple_effect(o["body"], False):
            continue
        if k == "may" and set(o) <= {"op", "body"} and _simple_effect(o["body"], False):
            continue
        if k in ("tap", "untap") and set(o) <= {"op", "select"} and _simple_selector(o.get("select")):
            continue
        if k == "flip_down" and set(o) <= {"op", "select"} and _simple_selector(o.get("select")) and o["select"].get("zone") in ("mana", "shield"):
            continue   # 裏向きにする（マナは無色として払う）。イベントは作らない
        if k == "modify" and set(o) <= {"op", "select", "mod", "duration"} and o.get("duration", "end_of_turn") == "end_of_turn" \
                and o.get("select") == {"ref": "self"} and isinstance(o.get("mod"), dict) and set(o["mod"]) == {"power", "grant"} \
                and isinstance(o["mod"]["power"], int) and not isinstance(o["mod"]["power"], bool) \
                and isinstance(o["mod"]["grant"], list) and o["mod"]["grant"] and set(o["mod"]["grant"]) <= set(_GRANT_BREAKS):
            continue   # このクリーチャーにこのターンの間パワーとブレイカーを与える（龍装者"JET"レミング）
        if k == "move" and "order" in o and not (o["order"] == "choose" and o.get("to") == "deck" and isinstance(o.get("select"), dict)
                                                  and set(o["select"]) == {"ref"}):
            return False   # 並べ替えは、選ばせない参照（変数の全部）を山札へ置く時だけ
        if k == "move" and set(o) <= {"op", "select", "to", "reason", "position", "tapped", "order", "as"} and isinstance(o.get("tapped", False), bool) and o.get("to") in ("hand", "graveyard", "mana", "deck", "shield", "bz") \
                and isinstance(o.get("reason"), str) and o.get("position", "top") in ("top", "bottom") and _simple_selector(o.get("select")) and isinstance(o.get("as", ""), str):
            continue
        return False
    return True


_GRANT_BREAKS = {"double_breaker": 2, "triple_breaker": 3}   # 継続的効果で与えてよいキーワード（ブレイク数の常在型だけ）


_OK_WHEN = ({"event": "move", "to": "bz", "subject": "self"}, {"event": "attack", "subject": "self"})


_OK_EVENTS = {"move", "attack", "battle_win", "turn_start", "turn_end", "cast"}
_OK_ZONES = {"hand", "deck", "graveyard", "mana", "bz", "shield"}


def _simple_when(w) -> bool:
    """Rust の when_match が Python の _match_when と同じ結果になる誘発条件（段階3-b）。"""
    if not isinstance(w, dict) or not set(w) <= {"event", "from", "to", "reason", "player", "subject"}:
        return False
    subj = w.get("subject", "self")
    if subj != "self" and not (isinstance(subj, dict) and set(subj) == {"owner"} and subj["owner"] in ("you", "opp")
                               and w.get("event") == "move" and isinstance(w.get("from"), str)
                               and w.get("from") in _OK_ZONES - {"bz"}):
        return False   # subject はこのカードか、持ち主だけの指定（バトルゾーン以外から動いたカード。lki を使わない）
    if w.get("event") not in _OK_EVENTS or w.get("player", "you") not in ("you", "opp"):
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


def _simple_replace(ab) -> bool:
    """段階3-d: 移動の置換（「〜する時、かわりに」）。発生源はバトルゾーン（Rust の replacement が Python の _replacement と同じ候補を出す範囲）。"""
    w = ab.get("when")
    if ab["kind"] == "replace" and isinstance(w, dict) and w.get("event") == "draw":   # 引く時の置換（シャコガイル）
        return set(ab) <= {"kind", "when", "instead", "if"} and set(w) <= {"event", "player"} and w.get("player", "you") in ("you", "opp") \
            and ("if" not in ab or _simple_cond(ab["if"])) and _simple_effect(ab["instead"], False)
    return ab["kind"] == "replace" and set(ab) <= {"kind", "when", "instead", "if"} and _simple_when(ab["when"]) \
        and ab["when"].get("event") in ("move", "draw") and ("if" not in ab or _simple_cond(ab["if"])) and _simple_effect(ab["instead"], False)


def _self_mods(d):
    """段階2-c: 自分自身にだけ及ぶ単純な常在型（許可・禁止・ブレイク数）だけの札の (allow, deny, breaks)。他は None。
    段階2-d: 単純な誘発（_simple_trigger）は許す（誘発の中身は Rust 側の effect インタプリタが動かす）。"""
    allow, deny, breaks, shield_allow = [], [], [], []
    allow_x = []
    deny_x = []
    cond_seen = False
    for ab in d.abilities:
        if _simple_trigger(ab) or _simple_replace(ab):
            continue
        if ab["kind"] == "static" and ab.get("zone") == "shield" and ab.get("affects") == "self" and "if" not in ab \
                and ab.get("mod") == {"allow": ["s_trigger"]}:
            shield_allow.append("s_trigger")   # S・トリガー（シールドゾーンにある間だけ働く許可）
            continue
        if ab["kind"] == "static" and isinstance(ab.get("affects"), dict) and set(ab.get("mod", {})) == {"gain"} and "if" not in ab:
            continue   # 他のカードに能力を与える常在型（ダーク・ティアラγ）。Python のエンジンは常在型の gain を扱わず効果が無いので、同じく何もしない
        if ab["kind"] == "static" and ab.get("affects") == "self" and "if" in ab and ab.get("zone", "bz") == "bz" \
                and _simple_cond(ab["if"]) and set(ab.get("mod", {})) == {"deny"} and set(ab) <= {"kind", "affects", "if", "mod", "zone"} \
                and all(isinstance(x, str) and x in _OK_DENY for x in ab["mod"]["deny"]):
            cond_seen = True   # 条件つきの自分への禁止（ギガゾウル）。Rust は deny_if として局面ごとに条件を見る
            continue
        if ab["kind"] == "static" and ab.get("affects") == "self" and "if" in ab and ab.get("zone", "bz") == "bz" \
                and _simple_cond(ab["if"]) and set(ab.get("mod", {})) == {"power"} and isinstance(ab["mod"]["power"], int) and set(ab) <= {"kind", "affects", "if", "mod", "zone"} \
                and not isinstance(ab["mod"]["power"], bool):
            continue   # 条件つきのパワー修整（ル・パーレ）。Rust は power_if として局面ごとに条件を見る
        if ab["kind"] != "static" or ab.get("affects") != "self" or "if" in ab or ab.get("zone", "bz") != "bz":
            return None
        if cond_seen:
            return None   # 特性の deny の並びを Python と揃えるため、条件つきの禁止は無条件の常在型より後ろに書かれた札だけ
        for k, v in ab.get("mod", {}).items():
            if k == "allow" and all(isinstance(x, str) and x in _OK_ALLOW for x in v):
                allow += v
            elif k == "allow" and all(isinstance(x, dict) and set(x) <= {"action", "other"} and x.get("action") in _OK_DENY
                                      and "tapped" not in x.get("other", {}) and x["action"] in deny + list(ab["mod"].get("deny", []))
                                      for x in v) and not any(isinstance(y, str) for y in allow):
                # 同じ行動の無条件の禁止がある「〜なら〜できる」（戦男）。禁止が勝つ（101.2）ので効かないが、特性の allow には並ぶ
                allow_x.extend(v)
            elif k == "deny" and all(isinstance(x, str) and x in _OK_DENY for x in v):
                deny += v
            elif k == "deny" and all(isinstance(x, dict) and set(x) == {"action", "other"} and x["action"] in ("be_blocked", "be_attacked")
                                     and _simple_filter(x["other"]) for x in v):
                deny_x.extend(v)   # 相手側のカードで決まる禁止（パワー3000以下にブロックされない等）
            elif k == "breaks" and isinstance(v, int) and not isinstance(v, bool):
                breaks.append(v)
            else:
                return None
    if allow_x and allow:
        return None
    if deny_x and (deny or cond_seen):
        return None   # 特性の deny の並び（辞書の後に文字列）を Python と揃えられる札だけ   # 特性の allow の並び（文字列の後に辞書）を Python と揃えられる札だけ
    return allow, deny, breaks, shield_allow


def _self_deny_x(d) -> list:
    return [x for ab in d.abilities if ab["kind"] == "static" and ab.get("affects") == "self" and "if" not in ab
            for x in ab.get("mod", {}).get("deny", []) if isinstance(x, dict)]


def _self_allow_x(d) -> list:
    """_self_mods が許した辞書形の allow（戦男）。特性の allow にそのまま並べる。"""
    return [x for ab in d.abilities if ab["kind"] == "static" and ab.get("affects") == "self" and "if" not in ab
            for x in ab.get("mod", {}).get("allow", []) if isinstance(x, dict)]


def _is_plain_spell(d) -> bool:
    """Rust が動かせる呪文（段階3-a）: 効果が単純（_simple_effect）で、S・トリガー以外のキーワード・常在型・特別な唱え方を持たない。"""
    import dataclasses
    from ..cards.defs import CardDef
    if d.types != ["spell"] or not d.spell or not _simple_effect(d.spell):
        return False
    if not set(d.keywords) <= {"s_trigger", "charger"}:
        return False
    if d.resolve_to not in ("graveyard", "mana", "shield") or ("charger" in d.keywords) != (d.resolve_to == "mana"):
        return False
    for ab in d.abilities:
        if not (ab["kind"] == "static" and ab.get("zone") == "shield" and ab.get("affects") == "self" and "if" not in ab
                and ab.get("mod") == {"allow": ["s_trigger"]}):
            return False
    skip = {"id", "name", "types", "civs", "cost", "power", "mana", "races", "text", "abilities", "keywords", "source", "spell", "resolve_to"}
    for f in dataclasses.fields(type(d)):
        if f.name in skip:
            continue
        dv = f.default if f.default is not dataclasses.MISSING else f.default_factory()
        if getattr(d, f.name) != dv:
            return False
    return True


TWINPACTS = True   # 段階3-c: クリーチャー面と呪文面がどちらも plain なツインパクト


def _is_plain_twin(d) -> bool:
    import dataclasses
    from ..cards.defs import CardDef
    if len(d.faces) != 2 or d.abilities or sorted(d.types) != ["creature", "spell"]:
        return False
    if d.faces[0].types != ["creature"] or not _is_plain_creature(d.faces[0]) or not _is_plain_spell(d.faces[1]):
        return False
    skip = {"id", "name", "types", "civs", "cost", "power", "mana", "races", "text", "abilities", "keywords", "source", "faces", "resolve_to"}
    for f in dataclasses.fields(CardDef):
        if f.name in skip:
            continue
        dv = f.default if f.default is not dataclasses.MISSING else f.default_factory()
        if getattr(d, f.name) != dv:
            return False
    return True


SPELLS = True   # 段階3-a の呪文を plain に含めるか（False で従来どおりクリーチャーだけ）


def _is_plain(d) -> bool:
    if getattr(d, "faces", None):
        return TWINPACTS and _is_plain_twin(d)
    if EVOLUTION and d.types == ["creature", "evolution"]:
        return _is_plain_evo(d)
    if SPELLS and d.types == ["spell"]:
        return _is_plain_spell(d)
    return _is_plain_creature(d)


EVOLUTION = True   # 段階3-e: 通常の進化（バトルゾーン）と超無限墓地進化（墓地の好きな数、1体ごとにコスト軽減）


def _is_plain_evo(d) -> bool:
    import dataclasses
    if d.types != ["creature", "evolution"] or d.power <= 0:
        return False
    ef = d.evolve_from
    if not isinstance(ef, dict) or not _simple_filter({k: v for k, v in ef.items() if k != "zone"}):
        return False
    if d.evolve_zone not in ("bz", "graveyard") or ef.get("zone", d.evolve_zone) != d.evolve_zone:
        return False
    if not set(d.keywords) <= _OK_KW or _self_mods(d) is None:
        return False
    skip = {"id", "name", "types", "civs", "cost", "power", "mana", "races", "text", "abilities", "keywords", "source",
            "evolve_from", "evolve_zone", "evolve_count", "evolve_any", "cost_reduce_per_evo"}
    for f in dataclasses.fields(type(d)):
        if f.name in skip:
            continue
        dv = f.default if f.default is not dataclasses.MISSING else f.default_factory()
        if getattr(d, f.name) != dv:
            return False
    return True


def _is_plain_creature(d) -> bool:
    """Rust が動かせる札（段階2-c）: 常在型は自分自身への単純な許可・禁止・ブレイク数だけ（誘発・置換・起動・特別な出し方は無い）のクリーチャー。"""
    import dataclasses
    from ..cards.defs import CardDef
    if d.types != ["creature"] or d.power <= 0:
        return False
    if not set(d.keywords) <= _OK_KW or _self_mods(d) is None:
        return False
    skip = {"id", "name", "types", "civs", "cost", "power", "mana", "races", "text", "abilities", "keywords", "source"}
    for f in dataclasses.fields(type(d)):
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
            "cards": _with_aliases(rules, {i: _card_bundle(d, i in rules.zone_trigger_defs) for i, d in rules.cards.items()})}


def _with_aliases(rules, cards: dict) -> dict:
    """旧 ID（再録・改名の別名）でも引けるようにする。Python の AliasDict と同じく、局面の defn が旧 ID のままでも動く。"""
    for a, c in getattr(rules.cards, "aliases", {}).items():
        if c in cards and a not in cards:
            cards[a] = cards[c]
    return cards


def _card_bundle(d, zt=False, mana=None) -> dict:
    plain = _is_plain(d) if mana is None else True
    out = {"name": d.name, "civs": list(d.civs), "cost": d.cost, "power": d.power,
           "mana": d.mana if mana is None else mana, "plain": plain, "types": list(d.types), "races": list(d.races),
           "keywords": list(d.keywords), "abil": d.abilities if plain else [],
           "spell": list(d.spell) if plain and d.types == ["spell"] else [],
           "resolve_to": d.resolve_to, "zt": zt,
           **dict(zip(("allow", "deny", "breaks", "shield_allow"), (_self_mods(d) or ([], [], [], [])))),
           "allow_x": _self_allow_x(d) if plain else [],
           "deny_x": _self_deny_x(d) if plain else [],
           "deny_if": [[ab["if"], list(ab["mod"]["deny"])] for ab in d.abilities
                       if plain and ab["kind"] == "static" and ab.get("affects") == "self" and "if" in ab and "deny" in ab["mod"]],
           "power_if": [[ab["if"], ab["mod"]["power"]] for ab in d.abilities
                        if plain and ab["kind"] == "static" and ab.get("affects") == "self" and "if" in ab and "power" in ab["mod"]]}
    if plain and "evolution" in d.types:
        out.update(evolve_from={k: v for k, v in d.evolve_from.items() if k != "zone"}, evolve_zone=d.evolve_zone,
                   evolve_count=d.evolve_count, evolve_any=d.evolve_any, cost_reduce_per_evo=d.cost_reduce_per_evo)
    if plain and getattr(d, "faces", None):
        out["faces"] = [_card_bundle(f, mana=d.mana) for f in d.faces]
    return out


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
        return cls(_open_core(st.to_json(), json.dumps(bundle) if bundle is not None else _bundle_json(rules)))

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


# ---- 段階4: 対局・探索への接続（扱えない札を含む局は Python のまま／途中で当たったら Python に戻す） ----

def state_from_json(js: str):
    """Rust の to_json（Python の GameState.to_json と同じ形）から GameState を作る。"""
    from .state import Card, GameState
    d = json.loads(js)
    d["cards"] = [Card(**c) for c in d["cards"]]
    return GameState(**d)


_BUNDLES: dict = {}


def _bundle_json(rules) -> str:
    k = id(rules)
    b = _BUNDLES.get(k)
    if b is None or b[0] is not rules:
        b = _BUNDLES[k] = (rules, json.dumps(rules_bundle(rules)))
    return b[1]


_TEMPLATES: dict = {}


def _open_core(state_json: str, bundle_json: str):
    """dmcore.Engine を開く。ルール一式（11MB 級の JSON）のパースが局ごとの支配的コストなので、
    同じバンドルではテンプレートを1つだけ開いて with_state（状態だけ差し替え・ルールは共有）で使い回す。"""
    import hashlib
    k = hashlib.sha1(bundle_json.encode()).hexdigest()
    t = _TEMPLATES.get(k)
    if t is None:
        c = dmcore.Engine.open(state_json, bundle_json)
        _TEMPLATES[k] = c
        return c
    return t.with_state(state_json)


def enabled() -> bool:
    """対局・探索のエンジンを Rust にするか。既定は有効（dmcore があり、全札が Rust で動く局だけ）。
    DMSIM_RUST=0 で無効（従来どおり Python だけ）。この1か所で切り替える。"""
    import os
    return available() and os.environ.get("DMSIM_RUST", "1") != "0" and _fresh_build() and _verified()


# Rust が一致を確かめた Python エンジンの版（rust/dmcore/verified_engine.txt）。Python のエンジンのファイルが変わると
# 一致の保証が無くなるので、確かめ直す（tools/rust_stamp.py）まで Rust を使わない。Rust の無い環境で Python だけ直した変更が
# 黙って Rust とずれるのを防ぐ。
ENGINE_FILES = ("combat.py", "core.py", "events.py", "interpreter.py", "ops.py", "selectors.py", "state.py", "turn.py", "rustcore.py")
STAMP = os.path.join(os.path.dirname(__file__), "..", "..", "rust", "dmcore", "verified_engine.txt")
_VERIFIED: bool | None = None


def engine_hash() -> str:
    import hashlib
    h = hashlib.sha256()
    for f in ENGINE_FILES:
        with open(os.path.join(os.path.dirname(__file__), f), "rb") as fh:
            h.update(f.encode() + b"\0" + fh.read().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()[:16]


def _verified() -> bool:
    global _VERIFIED
    if _VERIFIED is None:
        import warnings
        try:
            with open(STAMP, encoding="utf-8") as fh:
                want = fh.read().split()[0]
        except (OSError, IndexError):
            want = ""
        _VERIFIED = want == engine_hash()
        if not _VERIFIED:
            warnings.warn("Python のエンジンが Rust で一致を確かめた版から変わっているので Rust を使わない"
                          "（tests/test_rust_*.py を通してから python tools/rust_stamp.py で記録し直す）")
    return _VERIFIED


_FRESH: bool | None = None


def _fresh_build() -> bool:
    """組み込まれた dmcore が rust/dmcore/src より新しいか（古いビルドで Python とずれた結果を出さないための安全弁）。
    ソースが無い環境（配布物）では真。古ければ1度だけ警告して Rust を使わない（maturin develop で作り直す）。"""
    global _FRESH
    if _FRESH is None:
        import os
        import warnings
        src = os.path.join(os.path.dirname(__file__), "..", "..", "rust", "dmcore", "src")
        try:
            newest = max(os.path.getmtime(os.path.join(src, f)) for f in os.listdir(src))
            built = os.path.getmtime(dmcore.__file__) if getattr(dmcore, "__file__", None) else newest
            _FRESH = built >= newest
        except OSError:
            _FRESH = True
        if not _FRESH:
            warnings.warn("dmcore のビルドが rust/dmcore/src より古いので Rust を使わない（maturin develop で作り直す）")
    return _FRESH


def run_batch(rules, states, policy: str = "random", seed: int = 1) -> list[dict]:
    """複数局を Rust 内部で一括実行する（Phase 3）。states は初期 GameState の並び。
    policy: "random"（一様乱択）| "first"（最小数を先頭から）。戻りは局ごとの
    {winner, turn, decisions} または {error} のリスト。決定ごとの Python 往復が無い。"""
    if dmcore is None:
        raise RuntimeError("dmcore が無い")
    states_json = json.dumps([s.to_json() for s in states])
    out = dmcore.run_batch(_bundle_json(rules), states_json, policy, seed)
    return json.loads(out)


def supports(rules, state) -> bool:
    """この局の札がすべて Rust で動くか（_is_plain）。未対応の札が1枚でもあれば False。"""
    cards = rules.cards
    return all(_is_plain(cards[c.defn]) for c in state.cards)


def maybe_rust(eng):
    """eng（Python の Engine）を、Rust が扱える局なら RustEngine に包み直す。扱えなければ eng をそのまま返す。"""
    if not enabled() or isinstance(eng, RustEngine) or eng.s.trace is not None or not supports(eng.rules, eng.s):
        return eng
    try:
        return RustEngine(eng.rules, eng.s.clone(), list(eng.log), eng.step_limit, eng.turn_limit)
    except Exception:   # dmcore.Unsupported（局面の途中状態など）: Python のまま
        return eng


class _LazyState:
    """RustEngine.s の軽い代役: よく読む小さな値（active / turn / first_player / step / result）は Rust から直接読み、
    それ以外に触れた時だけ状態全体を Python の GameState に変換する。result への代入は Rust に書く。"""
    __slots__ = ("_e",)

    def __init__(self, e):
        object.__setattr__(self, "_e", e)

    def __getattr__(self, name):
        e = self._e
        if e._fb is None and e._py is None and e._c is not None:
            if name in ("active", "turn", "first_player", "step"):
                q = e._c.quick()
                return q[("active", "turn", "first_player", "step").index(name)]
            if name == "result":
                r = e._c.result()
                return None if r is None else json.loads(r)
        return getattr(e._view().s, name)

    def __setattr__(self, name, value):
        e = self._e
        if name == "result" and e._fb is None and e._c is not None and value is not None:
            e._c.set_result(json.dumps(value))
            e._py = None
            return
        setattr(e._view().s, name, value)


class RustEngine:
    """Engine（dmsim.engine.core）と同じ使い方で、進行（advance / answer / clone）を Rust で行う。
    読むだけの操作（s・zlist・chars_ro など）は、その時点の状態から作った Python の Engine に任せる（書き込みは反映しない）。
    Rust が扱えない語彙に当たったら、起点の状態から決定を Python で再生して、以後は Python の Engine として振る舞う。"""

    def __init__(self, rules, state, log, step_limit=20000, turn_limit=80, _core=None):
        self.rules, self.step_limit, self.turn_limit = rules, step_limit, turn_limit
        self._base, self._base_n = state, len(log)      # 起点（Python に戻す時の再生用）
        self._log = log
        self._py = None                                 # 読み取り用の Python Engine（状態が動いたら作り直す）
        self._raw = None                                # skel_raw の写し（状態が動いたら捨てる）
        self._fb = None                                 # Python に戻した後の Engine（__init__ の最初で None にしておく: log が読む）
        self._c = _core if _core is not None else _open_core(state.to_json(), _bundle_json(rules))

    @property
    def log(self):
        return self._fb.log if self._fb is not None else self._log

    @log.setter
    def log(self, v):
        if self._fb is not None:
            self._fb.log = v
        else:
            self._log = v

    # -- Python に戻す --
    def _fallback(self):
        if self._fb is None:
            from .core import Engine
            e = Engine(self.rules, self._base.clone(), step_limit=self.step_limit, turn_limit=self.turn_limit)
            e.log = list(self.log[:self._base_n])
            for ent in self.log[self._base_n:]:
                e.advance()
                e.answer(ent["choice"])
            self._fb, self._c, self._py = e, None, None
        return self._fb

    def _view(self):
        if self._fb is not None:
            return self._fb
        if self._py is None:
            from .core import Engine
            self._py = Engine(self.rules, state_from_json(self._c.to_json()), step_limit=self.step_limit,
                              turn_limit=self.turn_limit)
            self._py.log = self.log
        return self._py

    @property
    def s(self):
        if self._fb is not None:
            return self._fb.s
        if self._py is not None:
            return self._py.s
        return _LazyState(self)

    @s.setter
    def s(self, state):   # 状態の差し替え（決定化の注入）。新しい起点にする
        if self._fb is not None:
            self._fb.s = state
            return
        try:
            self._c = self._c.with_state(state.to_json())
            self._base, self._base_n, self._py, self._raw = state, len(self.log), None, None
        except Exception:
            from .core import Engine
            e = Engine(self.rules, state, step_limit=self.step_limit, turn_limit=self.turn_limit)
            e.log = self.log
            self._fb, self._c, self._py = e, None, None

    _MUTATORS = ("_raw_", "_push", "_defer", "_pop", "_expire", "_sba", "_move", "_put", "_set")

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        if name.startswith(self._MUTATORS):
            # 局面を直接書き換える内部の操作（準備用の移動など）は、読み取り用の写しに書いても Rust に届かないので、
            # Python に戻してからそちらで行う（結果は Python と同じ。遅くなるだけ）
            return getattr(self._fallback(), name)
        return getattr(self._view(), name)

    # -- 探索が局面ごとに読む欄（状態を作り直さずに Rust から直接引く。Python に戻した後は None） --
    def skel_raw(self):
        if self._fb is not None:
            return None
        if self._raw is None:
            self._raw = json.loads(self._c.skel_raw())
        return self._raw

    def zone_ids(self, z, owner):
        """区域の札の id の並び（Python に戻した後は None）。"""
        return None if self._fb is not None else self._c.zone_ids(z, owner)

    def card_sig(self, cid):
        """(定義名, 下にある札の定義名の並べ替え済みタプル)。Python に戻した後は None。"""
        if self._fb is not None:
            return None
        d, u = self._c.card_sig(cid)
        return d, tuple(u)

    def waiting_fast(self):
        r = self.skel_raw()
        return None if r is None else (r["waiting"], True)

    def zone_names(self, z, owner, top=False):
        """区域の札の定義名の並び（Python に戻した後は None）。"""
        if self._fb is not None:
            return None
        return self._c.zone_names(z, owner, bool(top))

    def tkey_extra(self):
        """探索の局面の鍵の残り（search.turn の mana_left・sizes と同じ値）。Python に戻した後は None。"""
        r = self.skel_raw()
        if r is None:
            return None
        z = r["zones"]
        return (tuple(sorted((d, t) for d, t in r["mana"])),
                tuple(len(z[k][p]) if k != "bz" else r["bz_n"][p] for p in (0, 1) for k in ("hand", "shield", "graveyard", "bz")))

    def eval_feats(self, me):
        if self._fb is not None:
            return None
        r = self._c.result()
        return (None if r is None else json.loads(r)), self._c.eval_feats(me)

    # -- 進行 --
    def clone(self):
        if self._fb is not None:
            return self._fb.clone()
        return RustEngine(self.rules, self._base, list(self.log), self.step_limit, self.turn_limit, _core=self._c.fork()) \
            ._with_base_n(self._base_n)

    def _with_base_n(self, n):
        self._base_n = n
        return self

    def advance(self):
        if self._fb is not None:
            return self._fb.advance()
        try:
            t = self._c.advance()
        except dmcore.Unsupported:
            return self._fallback().advance()
        self._py = self._raw = None
        return None if t is None else json.loads(t)

    def answer(self, choice):
        if self._fb is not None:
            return self._fb.answer(choice)
        if isinstance(choice, int):
            choice = [choice]
        self._c.answer(list(choice))
        self.log.append(json.loads(self._c.last_log()))
        self._py = self._raw = None

    def answer_by_keys(self, keys):
        if self._fb is not None:
            return self._fb.answer_by_keys(keys)
        d = self.advance()
        if self._fb is not None:
            return self._fb.answer_by_keys(keys)
        opts = [o["key"] for o in d["options"]]
        choice, used = [], set()
        for k in keys:
            for i, ok in enumerate(opts):
                if ok == k and i not in used:
                    choice.append(i)
                    used.add(i)
                    break
            else:
                from .core import IllegalAnswer
                raise IllegalAnswer(f"key {k} not available in {opts}")
        self.answer(choice)
