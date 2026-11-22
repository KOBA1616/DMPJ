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
          "s_trigger", "s_trigger_plus", "super_s_trigger",
          # 増分F: mana_boost_cip はキーワード辞書の展開（出た時に山札の上をマナへ）だけで、
          # エンジン本体が名前を参照しない（data/rules/keywords.yaml の定義のみ）
          "mana_boost_cip"}


_FILTER_LISTS = ("types", "not_types", "civs", "not_civs", "races")
_FILTER_INTS = ("cost_le", "cost_ge", "power_le", "power_ge")
_FILTER_BOOLS = ("tapped", "multicolor", "colorless", "evolution")


def _num_refspec(v) -> bool:
    """式の参照指定（変数名か {ref: 名前}、self / subject も可）。crossed と event.* は除く。"""
    name = v if isinstance(v, str) else (v.get("ref") if isinstance(v, dict) and set(v) == {"ref"} else None)
    return isinstance(name, str) and name != "crossed" and not name.startswith("event.")


def _simple_num_expr(x) -> bool:
    """Rust の eval_num が評価できる数式: 整数、{count: 単純セレクタ}、{sum/mul: [式...]}、
    {cost_of/power_of: 参照}、{declared: 名前}、{civ_count: [文明...]}。"""
    if isinstance(x, int) and not isinstance(x, bool):
        return True
    if not isinstance(x, dict) or len(x) != 1:
        return False
    k, v = next(iter(x.items()))
    if k == "count":
        return _simple_cands(v)
    if k in ("sum", "mul"):
        return isinstance(v, list) and all(_simple_num_expr(e) for e in v)
    if k in ("cost_of", "power_of"):
        return _num_refspec(v)
    if k == "declared":
        return isinstance(v, str)
    if k == "civ_count":
        return isinstance(v, list) and all(isinstance(c, str) for c in v)
    return False


def _simple_filter(f, exprs=False) -> bool:
    """Rust の filter_ok が Python の filter_match と同じ結果になるキーだけ。
    exprs=True の時だけ、解決時に値へ置き換える式の値（bake_filter が効くセレクタ経路用）も通す。"""
    if not isinstance(f, dict):
        return False
    for k, v in f.items():
        if k in _FILTER_LISTS:
            if isinstance(v, dict):
                if exprs and k == "races" and ((set(v) == {"race"} and isinstance(v["race"], str))
                                               or (set(v) == {"declared"} and isinstance(v["declared"], str))):
                    continue   # 解決時に種族のリストへ置き換える
                return False
            if not (isinstance(v, list) and all(isinstance(x, str) for x in v)) and not (k in ("civs", "not_civs") and isinstance(v, str)):
                return False
        elif k in _FILTER_INTS:
            if isinstance(v, dict) and set(v) == {"cost_of"} and k in ("cost_le", "cost_ge") \
                    and (isinstance(v["cost_of"], str) or (isinstance(v["cost_of"], dict) and set(v["cost_of"]) == {"ref"})) \
                    and (v["cost_of"] if isinstance(v["cost_of"], str) else v["cost_of"]["ref"]) not in ("crossed",) \
                    and not str(v["cost_of"] if isinstance(v["cost_of"], str) else v["cost_of"]["ref"]).startswith("event."):
                continue   # 参照カードのコスト（解決時に数へ置き換える。従来から全経路で許可）
            if isinstance(v, dict):
                if exprs and _simple_num_expr(v):
                    continue   # 解決時に数へ置き換える（セレクタ経路だけ）
                return False
            if not isinstance(v, int) or isinstance(v, bool):
                return False
        elif k in _FILTER_BOOLS:
            if not isinstance(v, bool):
                return False
        elif k in ("race_has", "keyword"):
            if not isinstance(v, str):
                return False
        elif k in ("name", "name_has", "not_name"):
            if isinstance(v, dict):
                if exprs and set(v) == {"name_of"} and _num_refspec(v["name_of"]):
                    continue   # 解決時に参照カードの名前へ置き換える
                return False
            if not isinstance(v, str):
                return False
        elif k == "not_race_has":
            if not (isinstance(v, str) or (isinstance(v, list) and all(isinstance(x, str) for x in v))):
                return False
        elif k in ("entered_this_turn", "face_up", "face_down", "twinpact"):
            if not isinstance(v, bool):
                return False
        elif k == "any_of":
            if not (isinstance(v, list) and all(_simple_filter(x, exprs) for x in v)):
                return False
        else:
            return False
    return True


def _zone_names_ok(z) -> bool:
    """zone 指定（名前か名前のリスト）が Rust の select / candidates_ro の扱えるゾーンだけか。"""
    names = ("hand", "deck", "graveyard", "mana", "bz", "shield")
    if isinstance(z, str):
        return z in names
    return isinstance(z, list) and len(z) > 0 and all(x in names for x in z)


def _simple_selector(sel) -> bool:
    """段階2-d＋増分D: Rust の select が扱えるセレクタ（参照／ゾーン・持ち主・枚数・上から・選ぶ人・絞り込み、
    EXライフ紐付き・下のカード・除外・極値・別集合と異なるコスト・合計制限つき選択）。"""
    if not isinstance(sel, dict):
        return False
    if sel == {"ref": "self"}:
        return True
    if "under_of" in sel:   # 自分／束変数の下のカード（メテオバーン等）
        if not (isinstance(sel["under_of"], str) and set(sel) <= {"under_of", "count", "filter", "up_to"}):
            return False
        c = sel.get("count", 1)
        if not (c in ("all", "any") or (isinstance(c, int) and not isinstance(c, bool))):
            return False
        up = sel.get("up_to", False)
        if not isinstance(up, bool) or (up and c == "all") or (up and "count" not in sel):
            return False
        return _simple_filter(sel.get("filter", {}), exprs=True)
    # exlife_of（EXライフの紐付きシールド）は Rust の select に実装済みだが、その形を持つ札は
    # 全て ex_life / g_strike 等の別の未実装要素で plain にならず lockstep で検証できないため、
    # ゲートはまだ開けない（検証できる増分で開ける）。
    if not set(sel) <= {"zone", "owner", "count", "from_top", "filter", "chooser", "look", "ref", "up_to", "other",
                        "owner_of", "exclude", "extremal", "distinct_from",
                        "total_cost_le", "total_cost_ge", "total_power_le", "total_power_ge", "distinct_costs"}:
        return False
    if "look" in sel and not isinstance(sel["look"], bool):
        return False
    if "ref" in sel:   # self / subject / event.* / self_moved / self_entered / 変数（choose の as）
        r = sel["ref"]
        if not isinstance(r, str) or r == "crossed" or (r.startswith("event.") and r not in
                ("event.subject", "event.target", "event.attacker", "event.opponent", "event.shield", "event.top", "event.under")):
            return False
        if r in ("self_moved", "self_entered"):
            # candidates が即返しする形: filter / zone / owner / from_top は効かないので併記を禁じる
            if not set(sel) <= {"ref", "count", "up_to", "chooser", "look"}:
                return False
        else:
            if "owner" in sel or "from_top" in sel or "owner_of" in sel or "exclude" in sel or "extremal" in sel or "distinct_from" in sel:
                return False
            if "zone" in sel and not _zone_names_ok(sel["zone"]):
                return False
    elif "owner_of" in sel:   # 束変数のカードの持ち主たち（ターンプレイヤーから順）
        if not isinstance(sel["owner_of"], str) or "owner" in sel or not _zone_names_ok(sel.get("zone")):
            return False
    elif not _zone_names_ok(sel.get("zone")) or sel.get("owner", "you") not in ("you", "opp", "any"):
        return False
    if "exclude" in sel:   # ゾーン経路の候補から引く除外セレクタ（数えるだけの形だけ）
        subs = sel["exclude"] if isinstance(sel["exclude"], list) else [sel["exclude"]]
        if not subs or not all(isinstance(s, dict) and _simple_cands(s) for s in subs):
            return False
    if "extremal" in sel and sel["extremal"] not in ("min_power", "max_power"):
        return False
    if "distinct_from" in sel and not _simple_cands(sel["distinct_from"]):
        return False
    for tk in ("total_cost_le", "total_cost_ge", "total_power_le", "total_power_ge"):
        if tk in sel and not _simple_num_expr(sel[tk]):
            return False
    if "distinct_costs" in sel and sel["distinct_costs"] is not True:
        return False
    if sel.get("chooser", "you") not in ("you", "opp", "opponent", "random"):
        return False
    if sel.get("chooser") == "random" and any(tk in sel for tk in
            ("total_cost_le", "total_cost_ge", "total_power_le", "total_power_ge", "distinct_costs")):
        return False   # ランダム選択では合計制限は Python でも無視されるが、混同を避けて通さない
    c = sel.get("count", 1)
    if not (c in ("all", "any") or (isinstance(c, int) and not isinstance(c, bool))):
        return False
    if c == "any" and (sel.get("up_to") or sel.get("chooser") == "random"):
        return False
    if "from_top" in sel and not _simple_num_expr(sel["from_top"]):
        return False
    if not _simple_filter(sel.get("filter", {}), exprs=True):
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
            and set(sel) <= {"ref", "filter"} and ("filter" not in sel or _simple_filter(sel["filter"], exprs=True))
    return _zone_names_ok(sel.get("zone")) and sel.get("owner", "you") in ("you", "opp", "any") \
        and isinstance(sel.get("from_top", 0), int) and ("filter" not in sel or _simple_filter(sel["filter"], exprs=True)) and isinstance(sel.get("other", False), bool)


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
        if k == "modify" and o.get("dynamic") is True and set(o) <= {"op", "select", "mod", "dynamic", "duration"} \
                and o.get("duration", "end_of_turn") in ("end_of_turn", "until_next_own_turn_start") and _simple_mod(o.get("mod")) \
                and isinstance(o.get("select"), dict) and set(o["select"]) <= {"zone", "owner", "filter", "count", "ref"} \
                and _simple_dyn_zone(o["select"].get("zone", "bz")) and o["select"].get("owner", "you") in ("you", "opp", "any") \
                and _simple_filter(o["select"].get("filter", {})):
            continue   # このターンの間の一時修整（後から入ったカードにも及ぶ範囲指定。範囲は生成時に持ち主を固定してベイクする）
        if k == "modify" and set(o) <= {"op", "select", "mod", "duration"} and o.get("duration", "end_of_turn") in ("end_of_turn", "until_next_own_turn_start") \
                and _simple_mod(o.get("mod")) and _simple_selector(o.get("select")):
            continue   # 一時修整（対象は解決時に固定。110.2e）。until_next_own_turn_start は生成時に
            # until_turn_start:{you} へ変換され、次の自分のターン開始時に消える（Rust の st_start が写す）
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
        if k == "move" and "order" in o and o["order"] not in ("choose", "shuffle"):
            return False   # 並べ替え（choose: 山札へ置く時の順序指定）と無作為化（shuffle）は Rust の op_move が写せている
        # strigger（S・トリガーの印）は Rust に実装済みだが、その形を持つ札は全て escape 等の
        # 別の未実装要素で plain にならず lockstep で検証できないため、ゲートはまだ開けない。
        if k == "move" and set(o) <= {"op", "select", "to", "reason", "position", "tapped", "order", "as", "face_up", "face_down"} and isinstance(o.get("tapped", False), bool) \
                and isinstance(o.get("face_up", False), bool) and isinstance(o.get("face_down", False), bool) \
                and o.get("to") in ("hand", "graveyard", "mana", "deck", "shield", "bz") \
                and isinstance(o.get("reason"), str) and o.get("position", "top") in ("top", "bottom") and _simple_selector(o.get("select")) and isinstance(o.get("as", ""), str):
            continue
        return False
    return True


_GRANT_OK = {"blocker", "speed_attacker", "slayer", "guardman", "unblockable", "cannot_attack", "cannot_block",
             "double_breaker", "triple_breaker", "world_breaker", "quad_breaker", "powered_breaker", "s_trigger"}
# 継続的効果で与えてよいキーワード（常在型が許可・禁止・ブレイク数だけで、Rust の kw_static / granted_breaks が写せているもの）


def _simple_mod(mod) -> bool:
    """Rust の継続的効果が扱える一時修整の mod（deny / allow / power / grant だけ、値は単純な形だけ）。
    deny / allow の辞書形は {action, other} だけ（once や max_per_turn つきは特性の並びと使用記録が要るので除く）。"""
    if not isinstance(mod, dict) or not mod or not set(mod) <= {"deny", "allow", "power", "grant"}:
        return False
    if "power" in mod:
        pw = mod["power"]
        if isinstance(pw, bool):
            return False
        if isinstance(pw, dict):
            if not set(pw) <= {"amount", "count"} or not isinstance(pw.get("amount"), int) or isinstance(pw.get("amount"), bool):
                return False
            if "count" in pw and not _simple_power_count(pw["count"]):
                return False
        elif not isinstance(pw, int):
            return False
    for key in ("deny", "allow"):
        if key in mod:
            if not isinstance(mod[key], list):
                return False
            for e in mod[key]:
                act = e if isinstance(e, str) else (e.get("action") if isinstance(e, dict) else None)
                # summon_from_mana の許可はマナゾーンからの play 選択肢（msum）を生むが、Rust には
                # その選択肢生成が無いので対象外（deny 側は plain の範囲に許可源が無いため無害）
                if key == "allow" and act == "summon_from_mana":
                    return False
                if isinstance(e, str):
                    continue
                if not (isinstance(e, dict) and set(e) == {"action", "other"} and isinstance(e.get("action"), str)
                        and _simple_filter(e.get("other", {}))):
                    return False
    if "grant" in mod:
        if not isinstance(mod["grant"], list) or not all(isinstance(x, str) and x in _GRANT_OK for x in mod["grant"]):
            return False
    return True


def _simple_power_count(sel) -> bool:
    """mod の power の {amount, count} の count: Rust の candidates_ro が数えられるセレクタで、
    フィルタの値に式が無いものだけ（特性計算の途中では env に変数が無いため、式の値は両エンジンで意味が揃わない）。"""
    if not _simple_cands(sel):
        return False
    f = sel.get("filter", {}) if isinstance(sel, dict) else {}
    return all(not isinstance(v, dict) for v in f.values())


def _simple_dyn_zone(z) -> bool:
    """dynamic な継続的効果の範囲の zone（Python の zones_of が扱う形: 名前 / 名前の配列 / "any"）。"""
    if isinstance(z, list):
        return all(isinstance(x, str) and x in _OK_ZONES for x in z)
    return z == "any" or z in _OK_ZONES


_OK_WHEN = ({"event": "move", "to": "bz", "subject": "self"}, {"event": "attack", "subject": "self"})


_OK_EVENTS = {"move", "attack", "battle_win", "turn_start", "turn_end", "cast",
              "tap", "untap", "block", "battle_start", "battle_lose", "battle_end",
              "attack_end", "break", "summon", "draw", "evolve_base"}
_OK_ZONES = {"hand", "deck", "graveyard", "mana", "bz", "shield"}

# 増分C: when のキー全般（Python の _match_when が見るキーから cause を除く。
# cause はコーパスに実例が無いので見送り。emblem / vivid は真偽の比較だけなので含める）
_OK_WHEN_KEYS = {"event", "from", "to", "reason", "via", "player", "subject", "target",
                 "shield", "attacker", "opponent", "ord", "unpaid", "broke", "blocked",
                 "face_up", "emblem", "vivid", "stacked", "by", "sealed_from", "from_under"}
_BOOL_WHEN_KEYS = ("unpaid", "broke", "blocked", "face_up", "emblem", "vivid", "stacked")


def _simple_filter_trig(f) -> bool:
    """増分C: 誘発の subject フィルタ。Rust の filter_match_trig が Python の filter_match
    （誘発の文脈: base=False、lki ありうる）と一致するキーだけ。_simple_filter のキーに
    civs_all / sealed を加え、式の値（辞書の値）は照合時の評価が要るので除く
    （any_of の中身は再帰で見る）。"""
    if not isinstance(f, dict):
        return False
    for k, v in f.items():
        if k == "any_of":
            if not (isinstance(v, list) and all(_simple_filter_trig(x) for x in v)):
                return False
        elif isinstance(v, dict):
            return False
        elif k == "civs_all":
            if not (isinstance(v, list) and all(isinstance(x, str) for x in v)) and not isinstance(v, str):
                return False
        elif k == "sealed":
            if not isinstance(v, bool):
                return False
        elif not _simple_filter({k: v}):
            return False
    return True


def _simple_subject(pat) -> bool:
    """増分C: when の subject（および target 等の参照指定）の形。Rust の subject_match_trig が
    Python の _subject_match（誘発の文脈）と一致するものだけ: "self" か、owner / other /
    zone / filter だけの辞書。refs / castle_of / castle_only / exlife_of は除く。"""
    if pat == "self":
        return True
    if not isinstance(pat, dict) or not set(pat) <= {"owner", "other", "filter", "zone"}:
        return False
    if "owner" in pat and pat["owner"] not in ("you", "opp", "any"):
        return False
    if "other" in pat and not isinstance(pat["other"], bool):
        return False
    if "zone" in pat and pat["zone"] not in _OK_ZONES:
        return False
    if "filter" in pat and not _simple_filter_trig(pat["filter"]):
        return False
    return True


def _simple_when(w) -> bool:
    """Rust の when_match が Python の _match_when と同じ結果になる誘発条件（段階3-b＋増分C）。"""
    if not isinstance(w, dict) or not set(w) <= _OK_WHEN_KEYS:
        return False
    if w.get("event") not in _OK_EVENTS:
        return False
    if w.get("player", "you") not in ("you", "opp") or w.get("by", "you") not in ("you", "opp"):
        return False
    for k in ("from", "to"):
        v = w.get(k)
        if v is not None and not (isinstance(v, str) and v in _OK_ZONES
                                  or isinstance(v, list) and all(isinstance(x, str) and x in _OK_ZONES for x in v)):
            return False
    for k in ("reason", "via"):
        if k in w and not isinstance(w[k], (str, list)):
            return False
    if "subject" in w and not _simple_subject(w["subject"]):
        return False
    for k in ("target", "attacker", "opponent", "shield", "sealed_from"):
        if k in w:
            v = w[k]
            if v in ("player", "creature"):
                if k != "target":
                    return False   # player/creature の振り分けは target だけの形（他では Python も一致しない）
            elif not _simple_subject(v):
                return False
    if "ord" in w:
        o = w["ord"]
        if not (isinstance(o, dict) and set(o) <= {"kind", "eq", "ge", "gt", "le", "lt"}
                and isinstance(o.get("kind"), str)
                and all(isinstance(o[kk], int) and not isinstance(o[kk], bool) for kk in o if kk != "kind")):
            return False
    for k in _BOOL_WHEN_KEYS:
        if k in w and not isinstance(w[k], bool):
            return False
    if "from_under" in w:
        fu = w["from_under"]
        if not (isinstance(fu, bool) or fu == "self" or _simple_subject(fu)):
            return False
    return True


def _simple_trigger(ab) -> bool:
    """段階3-b＋増分C: 単純な誘発条件（_simple_when）で、条件 if も単純、効果が単純（_simple_effect）なもの。
    バトルゾーンか墓地で働く。追加キー first_time / once_per_turn は Rust の collect_triggers が
    Python と同じく turn_counters で数え、optional は誘発では Python が読まない（置換だけ）ので素通し。
    増分F: keyword 印（キーワード辞書から展開された能力の出自）は Python の誘発収集でも
    Rust の collect_triggers でも読まれない素通しの印なので、文字列なら通す。"""
    return ab["kind"] == "trigger" and set(ab) <= {"kind", "when", "effect", "if", "zone",
                                                   "first_time", "optional", "once_per_turn", "keyword"} \
        and ("keyword" not in ab or isinstance(ab["keyword"], str)) \
        and all(k not in ab or isinstance(ab[k], bool) for k in ("first_time", "optional", "once_per_turn")) \
        and _simple_when(ab["when"]) \
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


def _simple_filter_x(f) -> bool:
    """常在型の範囲指定（affects の filter、allow/deny の other、battle_power の opponent_filter）に使うフィルタ。
    _simple_filter に加えて、値が式（辞書）でないこと（any_of の中身は再帰で見る）。
    Python の _subject_match は式の値を照合時に評価するが、特性計算の文脈では Rust 側で同じ評価ができないため除く。"""
    if not _simple_filter(f):
        return False
    for k, v in f.items():
        if k == "any_of":
            if not all(_simple_filter_x(x) for x in v):
                return False
        elif isinstance(v, dict):
            return False
    return True


def _simple_affects(aff) -> bool:
    """Rust の subject_match が Python の _subject_match（特性計算から base=True で呼ばれる形）と
    同じ結果になる affects 辞書。zone / owner / other / filter だけを見て、count / name / name_has / ref は
    Python 側でも照合に使われない（filter の中身としてではなく）ので値は何でもよい。"""
    if not set(aff) <= {"zone", "owner", "other", "filter", "count", "name", "name_has", "ref"}:
        return False
    if "zone" in aff and not isinstance(aff["zone"], str):
        return False
    if "owner" in aff and aff["owner"] not in ("you", "opp", "any"):
        return False
    if "filter" in aff and not _simple_filter_x(aff["filter"]):
        return False
    return True


def _amount_count_ok(v) -> bool:
    """mod の {amount, count} 形（power / cost）: amount は整数、count は数えるだけのセレクタ（式は除く）。"""
    return isinstance(v, dict) and set(v) <= {"amount", "count"} \
        and isinstance(v.get("amount"), int) and not isinstance(v.get("amount"), bool) \
        and ("count" not in v or _simple_cands(v["count"]))


_STATIC_GRANT_OK = {"blocker", "speed_attacker", "slayer", "guardman", "unblockable", "cannot_attack",
                    "cannot_attack_player", "cannot_be_attacked", "cannot_block", "cannot_untap",
                    "double_breaker", "triple_breaker", "quad_breaker", "world_breaker", "powered_breaker",
                    "null_breaker", "s_trigger", "s_trigger_plus", "super_s_trigger", "must_attack",
                    "hunting", "enters_tapped"}


def _static_entry_ok(e, is_allow: bool) -> bool:
    """常在型 mod の allow / deny の項目。文字列か、{action, other} / {action} / {action, once} の辞書だけ。
    墓地・マナからの召喚の許可は Rust に出す選択肢の生成が無いので、増分Aの CE mod と同じく許可側だけ除く。"""
    if isinstance(e, str):
        return not (is_allow and e in ("summon_from_graveyard", "summon_from_mana", "evolve_base"))
    if not isinstance(e, dict) or not set(e) <= {"action", "other", "once"} or not isinstance(e.get("action"), str):
        return False
    if is_allow and e["action"] in ("summon_from_graveyard", "summon_from_mana", "evolve_base"):
        return False
    return "other" not in e or _simple_filter_x(e["other"])


def _static_mod_ok(mod) -> bool:
    """増分B: Rust の特性計算（chars）が Python の _chars_calc_body と同じ畳み込みになる mod だけ。
    対象外のキー（cost_may / opt_reduce / sac_reduce / add_races / add_civs / no_leave / must_* /
    battle_indestructible / indestructible / crystal_soul / mana_number / ignore* 等）は従来どおり落とす。"""
    if not isinstance(mod, dict) or not mod:
        return False
    for k, v in mod.items():
        if k == "power":
            if not (isinstance(v, int) and not isinstance(v, bool)) and not _amount_count_ok(v):
                return False
        elif k == "power_when":
            if not (isinstance(v, dict) and set(v) <= {"amount", "when", "count"}
                    and isinstance(v.get("amount"), int) and not isinstance(v.get("amount"), bool)
                    and v.get("when") in ("attacking", "blocking")
                    and ("count" not in v or _simple_cands(v["count"]))):
                return False
        elif k in ("allow", "deny"):
            if not (isinstance(v, list) and all(_static_entry_ok(e, k == "allow") for e in v)):
                return False
        elif k in ("breaks", "breaks_add", "breaks_per_power", "cost_min"):
            if not (isinstance(v, int) and not isinstance(v, bool)):
                return False
        elif k == "grant":
            # 与えたキーワードの効果が特性の畳み込み（常在型・ブレイク数・タップして出る）だけで完結するものだけ。
            # escape / shield_saver / cyclone / mega_last_burst / g_strike や墓地・マナ召喚のキーワードは
            # 特性の外の仕組み（置換・選択肢の生成）を Python が動かすので除く
            if not (isinstance(v, list) and all(isinstance(x, str) and x in _STATIC_GRANT_OK for x in v)):
                return False
        elif k == "cost":
            if not (isinstance(v, int) and not isinstance(v, bool)) and not _amount_count_ok(v):
                return False
        elif k == "require":
            if not (isinstance(v, list) and all(isinstance(x, str) for x in v)):
                return False
        elif k == "gain":
            # 常在型の gain は Python の特性計算が畳み込まず効果が無い（Rust も読まない）。
            # 中身（得る能力）は実行されないので形は見ない。ただし if 条件は Python が評価するので検証は要る
            if not isinstance(v, list):
                return False
        elif k == "win_all_battles":
            if v is not True:
                return False
        elif k == "battle_power":
            if not (isinstance(v, dict) and set(v) <= {"amount", "count", "only", "opponent_filter"}
                    and isinstance(v.get("amount"), int) and not isinstance(v.get("amount"), bool)
                    and ("count" not in v or _simple_cands(v["count"]))
                    and ("only" not in v or isinstance(v["only"], str))
                    and ("opponent_filter" not in v or _simple_filter_x(v["opponent_filter"]))):
                return False
        else:
            return False
    return True


def _static_ok(ab) -> bool:
    """増分B: Rust が特性計算で写せる常在型能力か。追加キー（sst / sforce / choukon 等のゲートつき）は
    abilities() の絞り込みを Rust が持たないため除く（現行 plain の札には無いことを確認済み）。"""
    if not set(ab) <= {"kind", "affects", "mod", "zone", "if", "keyword"}:
        return False
    if "zone" in ab and not isinstance(ab["zone"], str):
        return False
    mod = ab.get("mod")
    if "if" in ab and not _simple_cond(ab["if"]):
        return False
    aff = ab.get("affects", {})
    if aff != "self" and not (isinstance(aff, dict) and _simple_affects(aff)):
        return False
    if mod is None:
        return True   # mod の無い常在型は特性に影響しない
    return _static_mod_ok(mod)


def _statics_ok(d) -> bool:
    """増分B の plain 判定（常在型の部分）: 誘発・置換が単純か、常在型が _static_ok な札だけ。
    従来の _self_mods（自分自身への許可・禁止・ブレイク数だけ）と違い、affects 辞書の常在型・
    self の power / power_when・コスト修整・require・全バトル勝利・バトル中パワーまで含む。
    特性の並びは Rust が abil から能力順に畳むので、従来のような並びの制約（条件つきは後ろ等）は要らない。"""
    for ab in d.abilities:
        if _simple_trigger(ab) or _simple_replace(ab):
            continue
        if ab["kind"] != "static" or not _static_ok(ab):
            return False
    return True


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
    if not set(d.keywords) <= _OK_KW or not _statics_ok(d):
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
    """Rust が動かせる札: 常在型は _statics_ok の範囲（自分自身への許可・禁止・ブレイク数に加え、増分Bで
    affects 辞書の常在型・self の power / power_when・コスト修整・require・全バトル勝利・バトル中パワーまで）。
    誘発・置換は単純なものだけ（起動・特別な出し方は無い）のクリーチャー。"""
    import dataclasses
    from ..cards.defs import CardDef
    if d.types != ["creature"] or d.power <= 0:
        return False
    if not set(d.keywords) <= _OK_KW or not _statics_ok(d):
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
           "deny_if": [[ab["if"], list(ab.get("mod", {})["deny"])] for ab in d.abilities
                       if plain and ab["kind"] == "static" and ab.get("affects") == "self" and "if" in ab and "deny" in ab.get("mod", {})],
           "power_if": [[ab["if"], ab.get("mod", {})["power"]] for ab in d.abilities
                        if plain and ab["kind"] == "static" and ab.get("affects") == "self" and "if" in ab and "power" in ab.get("mod", {})]}
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


def expand_turn(reng, params: dict):
    """増分E・段階1: RustEngine のコアでターン内展開ループ（dmcore の expand_turn）を回す。

    params は exhaustive_crossturn 側が組み立てる（予算・葉上限・重み・候補生成の
    記述・ゾーンの counter 表など）。戻り値は (メタ情報 dict, 葉の dmcore.Engine の列)。
    メタ情報は {leaves: [{value, log, digest, ckpt?}], truncated, nodes, left, leaf_count,
    certs} で、葉の列はメタ情報の leaves と同じ順。certs は段階2のループ検出が
    返した証明書（playback.cert_to_dict と同じ形、検出順）の列。ckpt は段階3の
    局面内チェックポイント用で track_path のときだけ各葉につく（path・nodes・
    left・la_left・macro_nodes・leaf_key・seen_new）。params.resume があるときは
    ガイドを再生してチェックポイントの葉まで飛ばす。dmcore が古い・未対応の
    語彙に当たった場合やガイドが食い違った場合（GuideMismatch）は None を返し、
    呼び出し側が Python ループに倒す（maybe_rust と同じ作法）。"""
    if not isinstance(reng, RustEngine) or reng._c is None:
        return None
    try:
        meta, cores = reng._c.expand_turn(json.dumps(params))
    except Exception:
        return None
    return json.loads(meta), cores


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
        self._c = _core if _core is not None else dmcore.Engine.open(state.to_json(), _bundle_json(rules))

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
