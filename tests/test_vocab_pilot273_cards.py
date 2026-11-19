"""語彙パイロット第273弾のカード適用テスト（登録形）。

ラウンド308で evolution_base_any の4枚を再変換。
- 新規登録4件: dmex08-137、dmex16-014、dmx21-062、dmx22a-041。差し戻し0件。
- converted 10,120 → 10,124 / rejects 2,213 → 2,209、重複0・漏れ0。
- 4枚とも partial の text が切り詰められていたため、登録形の text は
  reject 行の公式全文に差し替えた。
- dmex08-137 の破壊時誘発は第273弾の提出形どおり play_free で表した
  （submit の lint は助言のみ）。

プロトテスト（test_vocab_pilot273.py）とは別プロセスで実行すること
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
IDS = ["dmex08-137", "dmex16-014", "dmx21-062", "dmx22a-041"]

_ALLOW = {"kind": "static", "affects": "self", "mod": {"allow": ["evolve_base_any"]}}
_EVO_REDUCE = {"kind": "static", "affects": "self", "mod": {"evo_reduce": {"amount": 1}}}

FULL_TEXT = {
    "dmex08-137": "このクリーチャーの上に、どの種族の進化クリーチャーを置いてもよい。\n"
                  "このクリーチャーが破壊された時、ドラゴンを１体、自分の手札からバトルゾーンに出してもよい。",
    "dmex16-014": "スピードアタッカー\nW・ブレイカー\n"
                  "このクリーチャーの上に、どの種族の進化クリーチャーを置いてもよい。\n"
                  "このクリーチャーから進化する進化クリーチャーの召喚コストを１少なくする。ただし、コストは０以下にはならない。",
    "dmx21-062": "好きな種族の進化クリーチャーを、このクリーチャーの上に置いてもよい。",
    "dmx22a-041": "ブロッカー（このクリーチャーをタップして、相手クリーチャーの攻撃先をこのクリーチャーに変更してもよい）"
                  "このクリーチャーは攻撃できない。このクリーチャーの上に、どの種族の進化クリーチャーを置いてもよい。",
}
ALIASES = {
    "dmex08-137": ["dm27-017", "dmc55-047"],
    "dmex16-014": ["dmsp02-012"],
    "dmx21-062": ["dm06-069", "dmc27-034"],
    "dmx22a-041": ["dm32-082"],
}
KEYWORDS = {
    "dmex16-014": ["speed_attacker", "double_breaker"],
    "dmx22a-041": ["blocker", "cannot_attack"],
}


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


def _drive_to_main(e, want_key, max_steps=60):
    """want_key で始まるキーが main 選択肢に出るまで進める。出なければ None。"""
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main":
            if any(k.startswith(want_key) for k in keys):
                return d, keys
            e.answer([keys.index("pass")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return None, None


def _finish_play(e, max_steps=80):
    for _ in range(max_steps):
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        if d["kind"] in ("pay_mana", "choose_evo_source"):
            e.answer(list(range(d["min"])))
        elif d["kind"] == "main":
            return
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))


def _play_evolution(e, evo, base):
    d, keys = _drive_to_main(e, f"play:{evo}")
    assert d is not None, f"{evo} のプレイ選択肢が出ない"
    e.answer([next(i for i, k in enumerate(keys) if k.startswith(f"play:{evo}"))])
    _finish_play(e)
    assert evo in _defns(e, "bz", 0)
    top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == evo)
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == [base]


def test_round308_registered_forms():
    rejects = _reject_ids()
    for cid in IDS:
        assert cid not in rejects, cid
        card = _converted(cid)
        parse_card(card, TABLES, where=cid)      # 登録形がパースできる
        assert card["text"] == FULL_TEXT[cid], cid   # 公式全文（partial の切り詰めでない）
        assert _ALLOW in card["abilities"], cid
        assert card["source"].get("aliases", []) == ALIASES[cid], cid
        assert "unsupported" not in card["source"], cid
        if cid in KEYWORDS:
            assert card.get("keywords") == KEYWORDS[cid], cid
    # dmex16-014 は evo_reduce も持つ
    assert _EVO_REDUCE in _converted("dmex16-014")["abilities"]
    # dmex08-137 は破壊時誘発（ドラゴンを手札から出す）を持つ
    trig = [a for a in _converted("dmex08-137")["abilities"] if a["kind"] == "trigger"]
    assert len(trig) == 1 and trig[0]["when"]["reason"] == "destroy"


def test_registered_dmex16_014_evo_reduce():
    """登録形: 許可＋evo_reduce の進化元からはコスト4進化を3マナで置ける。"""
    e = _setup(load_rules(), {"bz": ["dmex16-014"], "hand": ["T627"],
                              "mana": ["T551"] * 3})
    d, keys = _drive_to_main(e, "play:T627")
    assert d is not None
    e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T627"))])
    for _ in range(40):   # T627 が場に出た瞬間に止める（ターンを跨ぐとマナが起きる）
        if "T627" in _defns(e, "bz", 0):
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] in ("pay_mana", "choose_evo_source"):
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    top = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T627")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["dmex16-014"]
    mana = e.zlist("mana", 0)
    assert sum(1 for c in mana if e.s.cards[c].tapped) == 3   # 軽減後の3を全て支払った


def test_registered_dmx21_062_any_of_branch_waived():
    """登録形: any_of の種族枝も肩代わりする（自然の許可持ちにドラゴン/水進化）。"""
    e = _setup(load_rules(), {"bz": ["dmx21-062"], "hand": ["T768"],
                              "mana": ["T002"] * 4})
    _play_evolution(e, "T768", "dmx21-062")


def test_registered_dmex08_137_destroy_trigger():
    """登録形: 破壊された時、手札からドラゴンを出してもよい。"""
    e = _setup(load_rules(), {"bz": ["dmex08-137"], "hand": ["T620", "T769"],
                              "mana": ["T551"] * 3})
    for _ in range(120):
        if "T769" in _defns(e, "bz", 0):
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main":
            hit = [i for i, k in enumerate(keys) if k.startswith("play:T620")]
            e.answer([hit[0]] if hit else [keys.index("pass")])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif d["kind"] in ("choose_cards", "choose_card"):
            pref = [i for i, k in enumerate(keys) if "dmex08-137" in k or "T769" in k]
            e.answer([pref[0]] if pref else list(range(d["min"])))
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "dmex08-137" in _defns(e, "graveyard", 0)
    assert "T769" in _defns(e, "bz", 0)
