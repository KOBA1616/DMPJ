"""第215弾の登録カード（ラウンド251）の確認。

- 5枚が converted.yaml の登録形で parse できる
- dm34-034: オリジン・マナ4枚が各2として数えられ、コスト8の支払い組み合わせになる
  （非オリジンのマナ4枚では届かない）
- dm34-043: 唱えると山札の上から4枚を見て2枚まで手札に加え、残りを山札の下に戻す
- dm34-048: 出た時、相手の「ブロッカー」を持つクリーチャーを1体破壊する
"""
import os
from pathlib import Path

import pytest

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.scenario import build  # noqa: E402
import tests._conv_cache as _conv_cache  # noqa: E402

TABLES = load_tables()
CONVERTED = Path(__file__).parent.parent / "data" / "cards" / "converted.yaml"
IDS = ("dm34-034", "dm34-037", "dm34-043", "dm34-044", "dm34-048")


@pytest.fixture(scope="module")
def converted():
    return {c["id"]: c for c in _conv_cache.all_cards(str(CONVERTED))}


@pytest.fixture(scope="module")
def rules():
    return _conv_cache.full_rules()


def test_build_forms_parse(converted):
    for cid in IDS:
        assert cid in converted, cid
        parse_card(converted[cid], TABLES)


def _in_bz(e, defn, ctrl):
    return any(e.s.cards[c].defn == defn and e.s.cards[c].controller == ctrl
               for c in e.zlist("bz", 0))


def _in_zone(e, defn, zone, player):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, player))


def test_dm34_034_doubled_payment(rules):
    """オリジン4枚（各2）でコスト8に届き、非オリジン4枚（各1）では届かない。"""
    e = build(rules, {"p0": {"hand": ["dm34-034"],
                             "mana": ["dm34-034", "dm34-037", "dm34-044", "dm34-048"]},
                      "p1": {}, "filler": "T002", "seed": 1, "deck_size": 20})
    cid = next(c for c in e.zlist("hand", 0) if e.s.cards[c].defn == "dm34-034")
    ch = e._mana_choices(cid, 0)
    assert ch and all(len(c) == 4 for c in ch)   # 2+2+2+2 の組だけ
    e = build(rules, {"p0": {"hand": ["dm34-034"], "mana": ["T002"] * 4},
                      "p1": {}, "filler": "T002", "seed": 1, "deck_size": 20})
    cid = next(c for c in e.zlist("hand", 0) if e.s.cards[c].defn == "dm34-034")
    assert e._mana_choices(cid, 0) == []


def _drive(e, player, key, stop, limit=800):
    """player が key の行動を取り、stop() 成立後に次の通常決定まで流す。
    行動直前の (手札枚数, 山札枚数) を返す。"""
    acted = False
    before = None
    settled = False
    for _ in range(limit):
        if acted and stop():
            if settled:
                return before
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not acted and d.get("player") == player and d["kind"] in ("main", "attack") and key in keys:
            before = (len(e.zlist("hand", player)), len(e.zlist("deck", player)))
            e.answer([keys.index(key)])
            acted = True
        elif acted and stop() and d["kind"] in ("main", "charge"):
            settled = True
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d.get("min") == 0 and d.get("max") == 2:
            e.answer([0, 1])   # 「2枚まで手札に加える」は2枚取る
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return before


def test_dm34_043_look_take_bottom(rules):
    e = build(rules, {"p0": {"hand": ["dm34-043"], "mana": ["T030"] * 6},
                      "p1": {}, "filler": "T002", "seed": 1, "deck_size": 20})
    before = _drive(e, 0, "play:dm34-043",
                    lambda: _in_zone(e, "dm34-043", "graveyard", 0))
    assert before is not None
    assert _in_zone(e, "dm34-043", "graveyard", 0)
    # 手札: 呪文が離れて -1、見た4枚から2枚加えて +2 → 行動直前より +1
    assert len(e.zlist("hand", 0)) == before[0] + 1
    # 山札: 4枚見て2枚が手札へ、残り2枚は下に戻る → -2
    assert len(e.zlist("deck", 0)) == before[1] - 2


def test_dm34_048_cip_destroys_blocker(rules):
    e = build(rules, {"p0": {"hand": ["dm34-048"], "mana": ["T060"] * 6},
                      "p1": {"bz": ["dm34-037"]},
                      "filler": "T002", "seed": 1, "deck_size": 20})
    _drive(e, 0, "play:dm34-048",
           lambda: _in_zone(e, "dm34-037", "graveyard", 1))
    assert _in_bz(e, "dm34-048", 0)
    assert _in_zone(e, "dm34-037", "graveyard", 1)
