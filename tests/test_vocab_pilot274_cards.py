"""語彙パイロット第274弾のカード適用テスト（登録形）。

ラウンド309で soulshift の pure 行4件を再変換。
- 新規登録4件: dmx10-035、dmx11-050、dmx12b-056、dmx22a-013。差し戻し0件。
- converted 10,124 → 10,128 / rejects 2,209 → 2,205、重複0・漏れ0。
- 4枚とも soul_shift {floor} を付けた（035/050/056 は floor 1、013 は floor 0）。
- partial の欠落・ずれは reject 行の公式全文から補った:
  - dmx11-050: 「自分よりパワーの小さいクリーチャーにブロックされない」
    （deny be_blocked の other に power_le: {sum: [{power_of: self}, -1]}）
  - dmx12b-056: evolve_from を原文どおり any_of（ジャイアント/ドリームメイト/
    オリジン）に修正し、欠けていた破壊時誘発（自分の進化クリーチャーが破壊された時、
    進化ではない同種族いずれかをマナゾーンから出してもよい）を補った
  - dmx22a-013: W・ブレイカーと呪文ロック（各プレイヤーは自身の墓地にある呪文と
    同じ文明を持つ呪文を唱えられない）を補った。ロックは文明×自分/相手の計10枚の
    常在型（affects 手札の呪文 + if 墓地に同文明の呪文 + deny cast）で表した
- text は4枚とも partial の切り詰めでなく reject 行の公式全文。

プロトテスト（test_vocab_pilot274.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが汚染される）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.scenario import build  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
IDS = ["dmx10-035", "dmx11-050", "dmx12b-056", "dmx22a-013"]

FULL_TEXT = {
    "dmx10-035": "ブロッカー\n"
                 "進化-自分の「ブロッカー」を持つクリーチャー１体の上に置く。\n"
                 "ソウルシフト(このクリーチャーを召喚する時、このクリーチャーの進化元クリーチャーを選ぶ。"
                 "このクリーチャーのコストは、その選んだクリーチャーのコストだけ少なくなる。"
                 "ただし、このクリーチャーのコストは１より少なくならない)\n"
                 "自分のターンの終わりに、このクリーチャーをアンタップする。\n"
                 "W・ブレイカー(このクリーチャーはシールドを２枚ブレイクする)",
    "dmx11-050": "進化-自分のジャイアント１体の上に置く。\n"
                 "ソウルシフト(このクリーチャーを召喚する時、このクリーチャーの進化元クリーチャーを選ぶ。"
                 "このクリーチャーのコストは、その選んだクリーチャーのコストだけ少なくなる。"
                 "ただし、このクリーチャーのコストは１より少なくならない)\n"
                 "このクリーチャーは、このクリーチャーよりパワーの小さいクリーチャーにブロックされない。\n"
                 "W・ブレイカー",
    "dmx12b-056": "進化-自分のジャイアント、ドリームメイト、オリジンいずれか１体の上に置く。\n"
                  "ソウルシフト（このクリーチャーを召喚する時、このクリーチャーの進化元クリーチャーを選ぶ。"
                  "このクリーチャーのコストは、その選んだクリーチャーのコストだけ少なくなる。"
                  "ただし、このクリーチャーのコストは１より少なくならない）\n"
                  "自分の進化クリーチャーが破壊された時、自分の進化ではないジャイアント、ドリームメイト、"
                  "またはオリジンのいずれか１体をマナゾーンからバトルゾーンに出してもよい。\n"
                  "W・ブレイカー（このクリーチャーはシールドを２枚ブレイクする）",
    "dmx22a-013": "進化-自分のサイバー１体の上に置く。"
                  "ソウルシフト（このクリーチャーを召喚する時、このクリーチャーの進化元クリーチャーを選ぶ。"
                  "このクリーチャーのコストは、その選んだクリーチャーのコストだけ少なくなる。"
                  "ただし、このクリーチャーのコストは０以下にならない）"
                  "W・ブレイカー（このクリーチャーはシールドを２つブレイクする）"
                  "各プレイヤーは、自身の墓地にある呪文と同じ文明を持つ呪文を唱えられない。",
}
ALIASES = {
    "dmx10-035": ["dm32-071", "dm32-071hc"],
    "dmx11-050": [],
    "dmx12b-056": ["dm32-009"],
    "dmx22a-013": ["dm32-017", "dmx10-020"],
}
KEYWORDS = {
    "dmx10-035": ["blocker", "double_breaker"],
    "dmx11-050": ["double_breaker"],
    "dmx12b-056": ["double_breaker"],
    "dmx22a-013": ["double_breaker"],
}
FLOORS = {"dmx10-035": 1, "dmx11-050": 1, "dmx12b-056": 1, "dmx22a-013": 0}

_UNBLOCKABLE = {"kind": "static", "affects": "self",
                "mod": {"deny": [{"action": "be_blocked",
                                  "other": {"power_le": {"sum": [{"power_of": "self"}, -1]}}}]}}
_ZENON_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "to": "graveyard", "reason": "destroy",
             "subject": {"owner": "you", "filter": {"types": ["evolution"]}}},
    "effect": [{"op": "play_free",
                "select": {"zone": "mana", "owner": "you",
                           "filter": {"types": ["creature"], "evolution": False,
                                      "any_of": [{"races": ["ジャイアント"]},
                                                 {"races": ["ドリームメイト"]},
                                                 {"races": ["オリジン"]}]},
                           "count": 1, "up_to": True}}],
}
_CIVS = ["light", "water", "darkness", "fire", "nature"]


def _setup(rules, p0, p1=None):
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": "T001",
                         "seed": 1, "deck_size": 20})


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _reject_ids():
    return {json.loads(line)["id"] for line in open(REJECTS, encoding="utf-8")
            if line.strip()}


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_generic(e, d):
    keys = _keys(d)
    if d["kind"] in ("pay_mana", "choose_evo_source"):
        e.answer(list(range(d["min"])))
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def _play_until_bz(e, play_key, defn, max_steps=120):
    """play_key でプレイし、defn がバトルゾーンに出るまで進める。"""
    played = False
    for _ in range(max_steps):
        if defn in _defns(e, "bz", 0):
            return True
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if not played and d["kind"] == "main" and play_key in keys:
            e.answer([keys.index(play_key)])
            played = True
            continue
        _answer_generic(e, d)
    return defn in _defns(e, "bz", 0)


def _tapped_mana(e, p=0):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


def test_round309_registered_forms():
    rejects = _reject_ids()
    for cid in IDS:
        assert cid not in rejects, cid
        card = _converted(cid)
        parse_card(card, TABLES, where=cid)      # 登録形がパースできる
        assert card["text"] == FULL_TEXT[cid], cid   # 公式全文（partial の切り詰めでない）
        assert card.get("keywords") == KEYWORDS[cid], cid
        assert card["soul_shift"] == {"floor": FLOORS[cid]}, cid
        assert card["source"].get("aliases", []) == ALIASES[cid], cid
        assert "unsupported" not in card["source"], cid
    # dmx10-035: 進化元はブロッカー持ち、ターン終了時アンタップ誘発
    c035 = _converted("dmx10-035")
    assert c035["evolve_from"] == {"types": ["creature"], "keyword": "blocker"}
    trig = [a for a in c035["abilities"] if a["kind"] == "trigger"]
    assert len(trig) == 1 and trig[0]["when"] == {"event": "turn_end", "player": "you"}
    # dmx11-050: 進化元はジャイアント、小さいパワーにブロックされない
    c050 = _converted("dmx11-050")
    assert c050["evolve_from"] == {"races": ["ジャイアント"]}
    assert c050["abilities"] == [_UNBLOCKABLE]
    # dmx12b-056: 進化元は3種族 any_of、破壊時誘発
    c056 = _converted("dmx12b-056")
    assert c056["evolve_from"] == {"any_of": [{"races": ["ジャイアント"]},
                                              {"races": ["ドリームメイト"]},
                                              {"races": ["オリジン"]}]}
    assert c056["abilities"] == [_ZENON_TRIGGER]
    # dmx22a-013: 進化元はサイバー、呪文ロック常在型が文明×両プレイヤー分そろう
    c013 = _converted("dmx22a-013")
    assert c013["evolve_from"] == {"types": ["creature"], "race_has": "サイバー"}
    locks = c013["abilities"]
    assert len(locks) == 10
    seen = set()
    for ab in locks:
        assert ab["kind"] == "static" and ab["mod"] == {"deny": ["cast"]}
        owner = ab["affects"]["owner"]
        civ = ab["affects"]["filter"]["civs"][0]
        assert ab["affects"]["zone"] == "hand"
        assert ab["affects"]["filter"]["types"] == ["spell"]
        assert ab["if"] == {"exists": {"zone": ["graveyard"], "owner": owner,
                                       "filter": {"types": ["spell"], "civs": [civ]}}}
        seen.add((owner, civ))
    assert seen == {(o, c) for o in ("you", "opp") for c in _CIVS}


def test_registered_dmx10_035_soulshift_play():
    """登録形: ブロッカー（コスト3）の上に 11−3=8 で置ける。"""
    e = _setup(load_rules(), {"bz": ["T004"], "hand": ["dmx10-035"],
                              "mana": ["T004"] * 8})
    assert _play_until_bz(e, "play:dmx10-035", "dmx10-035")
    top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "dmx10-035")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T004"]
    assert _tapped_mana(e) == 8


def test_registered_dmx11_050_soulshift_play():
    """登録形: ジャイアント（コスト3）の上に 10−3=7 で置ける。"""
    e = _setup(load_rules(), {"bz": ["T341"], "hand": ["dmx11-050"],
                              "mana": ["T001"] * 7})
    assert _play_until_bz(e, "play:dmx11-050", "dmx11-050")
    top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "dmx11-050")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T341"]
    assert _tapped_mana(e) == 7


def _attack_player(e, atk_defn, max_steps=400):
    """atk_defn でプレイヤー攻撃する。ブロック決定が見えたらその選択肢を返す
    （無ければ None）。攻撃側のシールドブレイクまで進める。"""
    attacked = False
    block_keys = None
    for _ in range(max_steps):
        if attacked and len(e.zlist("shield", 1)) < 5:
            return block_keys
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if not attacked and f"attack:{atk_defn}:player" in keys:
            e.answer([keys.index(f"attack:{atk_defn}:player")])
            attacked = True
            continue
        if attacked and d["kind"] == "block":
            block_keys = keys
            e.answer([keys.index("no_block")] if "no_block" in keys
                     else list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return block_keys


def test_registered_dmx11_050_smaller_blocker_cannot_block():
    """登録形: パワー3000のブロッカーは星飯（11000）をブロックできない。"""
    e = _setup(load_rules(), {"bz": ["dmx11-050"]}, {"bz": ["T004"]})
    block_keys = _attack_player(e, "dmx11-050")
    assert block_keys is None or not any(k.startswith("bz:T004") for k in block_keys)
    assert len(e.zlist("shield", 1)) == 3   # W・ブレイカーが通った


def test_registered_dmx11_050_equal_blocker_can_block():
    """登録形: パワー11000のブロッカーは星飯（11000）をブロックできる
    （「小さい」クリーチャーだけが排除される）。ブロッカー役は登録済みの
    dmx10-035（パワー11000・ブロッカー）。"""
    e = _setup(load_rules(), {"bz": ["dmx11-050"]}, {"bz": ["dmx10-035"]})
    block_keys = _attack_player(e, "dmx11-050")
    assert block_keys is not None
    assert any(k.startswith("bz:dmx10-035") for k in block_keys)


def _destroy_and_put(e, target_defn, max_steps=300):
    """T620 で target_defn を破壊し、誘発でマナの T341 を出す。"""
    played = False
    for _ in range(max_steps):
        if target_defn in _defns(e, "graveyard", 0) and "T341" in _defns(e, "bz", 0):
            return True
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if not played and d["kind"] == "main" and "play:T620" in keys:
            e.answer([keys.index("play:T620")])
            played = True
            continue
        if d["kind"] in ("choose_cards", "choose_card", "choose"):
            pref = [i for i, k in enumerate(keys) if target_defn in k]
            if not pref:
                pref = [i for i, k in enumerate(keys) if "T341" in k]
            e.answer([pref[0]] if pref else list(range(d["min"])))
            continue
        if d["kind"] == "yes_no":
            e.answer([0])
            continue
        _answer_generic(e, d)
    return False


def test_registered_dmx12b_056_destroy_other_evolution():
    """登録形: 自分の他の進化クリーチャーが破壊された時、マナからジャイアントを出す。"""
    e = _setup(load_rules(), {"bz": ["dmx12b-056", "T370"], "hand": ["T620"],
                              "mana": ["T341", "T034", "T034", "T034"]})
    assert _destroy_and_put(e, "T370")


def test_registered_dmx12b_056_destroy_self():
    """登録形: ゼノン自身が破壊された時も誘発し、マナからジャイアントを出す。
    破壊はバトルで行う（T763 パワー99999 にブロックさせる。T620 は
    パワー4000以下しか破壊できないため使えない）。"""
    e = _setup(load_rules(), {"bz": ["dmx12b-056"], "mana": ["T341"]},
               {"bz": ["T763"]})
    attacked = False
    for _ in range(300):
        if "dmx12b-056" in _defns(e, "graveyard", 0) and "T341" in _defns(e, "bz", 0):
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if not attacked and "attack:dmx12b-056:player" in keys:
            e.answer([keys.index("attack:dmx12b-056:player")])
            attacked = True
            continue
        if d["kind"] == "block":
            guard = [i for i, k in enumerate(keys) if k.startswith("bz:T763")]
            e.answer([guard[0]] if guard else [keys.index("no_block")])
            continue
        if d["kind"] in ("choose_cards", "choose_card", "choose"):
            pref = [i for i, k in enumerate(keys) if "T341" in k]
            e.answer([pref[0]] if pref else list(range(d["min"])))
            continue
        if d["kind"] == "yes_no":
            e.answer([0])
            continue
        _answer_generic(e, d)
    assert "dmx12b-056" in _defns(e, "graveyard", 0)
    assert "T341" in _defns(e, "bz", 0)


def _main_keys(e, player, max_steps=300):
    """player のメイン決定まで進め、その選択肢キーを返す。"""
    for _ in range(max_steps):
        d = e.advance()
        if d is None:
            return None
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == player:
            return keys
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return None


def test_registered_dmx22a_013_locks_own_spell():
    """登録形: 自分の墓地に水の呪文がある間、自分は水の呪文を唱えられない
    （火の呪文は唱えられる）。"""
    e = _setup(load_rules(), {"bz": ["dmx22a-013"], "graveyard": ["T003"],
                              "hand": ["T003", "T620"],
                              "mana": ["T010", "T010", "T034", "T034", "T034"]})
    keys = _main_keys(e, 0)
    assert keys is not None
    assert "play:T003" not in keys
    assert "play:T620" in keys


def test_registered_dmx22a_013_locks_opponent_spell():
    """登録形: 相手の墓地に水の呪文がある間、相手も水の呪文を唱えられない。
    相手の手札には唱えられる自然のクリーチャー（T001）も入れ、メイン決定が
    現れること自体を確認してから T003 の不在を見る。"""
    e = _setup(load_rules(), {"bz": ["dmx22a-013"]},
               {"graveyard": ["T003"], "hand": ["T003", "T001"],
                "mana": ["T010", "T010", "T001", "T001"]})
    keys = _main_keys(e, 1)
    assert keys is not None
    assert "play:T001" in keys
    assert "play:T003" not in keys


def test_registered_dmx22a_013_no_lock_without_matching_graveyard_spell():
    """登録形: 墓地に呪文が無い／文明が違えば、水の呪文を唱えられる。"""
    e = _setup(load_rules(), {"bz": ["dmx22a-013"], "hand": ["T003"],
                              "mana": ["T010", "T010"]})
    keys = _main_keys(e, 0)
    assert keys is not None and "play:T003" in keys
    e = _setup(load_rules(), {"bz": ["dmx22a-013"], "graveyard": ["T620"],
                              "hand": ["T003"], "mana": ["T010", "T010"]})
    keys = _main_keys(e, 0)
    assert keys is not None and "play:T003" in keys
