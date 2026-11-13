"""語彙パイロット第197弾: g_link_four_way（名前指定・4方向 G・リンク）。

起源神・神帝・神王グループのリンクは、位置キーワード（左/中央/右）ではなく
「《A》の右横、《B》の上側」のように相手の名前と方向で決まる。本弾は:

- 新しい面フィールド `link_to: [{name, pos}]`（pos は相手から見た自分の位置:
  right / left / up / down）
- h_g_link に名前指定の分岐を追加: 指定名のゴッドがいるグループにリンクする。
  同じ名前のカードは1グループに1枚まで（星座が一意に決まる）
- リンクの統合（特性・離脱置換・link_count・link_established）は既存の
  グループ機構をそのまま使う
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T487", "T488", "T489", "T490")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)


def test_invalid_link_to():
    base = {"id": "test-lt-bad", "name": "試験不良", "types": ["creature"],
            "civs": ["water"], "cost": 3, "power": 2000, "mana": 1,
            "source": {"official": "test-lt-bad", "review": "pending"}}
    with pytest.raises(DefError):
        parse_card({**base, "link_to": [{"name": "相手", "pos": "diagonal"}]}, TABLES)
    with pytest.raises(DefError):
        parse_card({**base, "link_to": [{"pos": "right"}]}, TABLES)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _cid(e, defn, player=0):
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _drive(e, summons, link_targets, leave_key=None, limit=300, until=None):
    """summons: 出す defn の列。link_targets: {出す defn: リンク先 defn}。
    leave_key: 離脱時に選ぶカードのキー（"bz:T487:0" 等）。"""
    summons = list(summons)
    link_targets = dict(link_targets)
    seen_link_decisions = []
    current = None
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and summons:
            want = f"play:{summons[0]}"
            if want in keys:
                e.answer([keys.index(want)])
                current = summons.pop(0)
                continue
        if d["kind"] == "choose_link_target":
            seen_link_decisions.append(list(keys))
            tgt = link_targets.get(current)
            if tgt is not None and any(tgt in k for k in keys):
                e.answer([next(i for i, k in enumerate(keys) if tgt in k)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
            continue
        if leave_key and d["kind"] == "choose_cards" and leave_key in keys:
            e.answer([keys.index(leave_key)])
            leave_key = None
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if until is not None and until(e):
            break
    return seen_link_decisions


def test_link_by_name_and_merge(rules):
    """名前が一致するゴッドにリンクし、特性が統合される（パワー合計）。"""
    e = setup(rules, {"hand": ["T487"], "mana": ["T030"] * 5, "bz": ["T488"]},
              {"bz": ["T001"]}, filler="T002")
    seen = _drive(e, ["T487"], {"T487": "T488"})
    assert seen, "choose_link_target never appeared"
    aqua, blaze = _cid(e, "T487"), _cid(e, "T488")
    assert e.s.cards[aqua].link and e.s.cards[aqua].link == e.s.cards[blaze].link
    assert sorted(e.s.cards[m].defn for m in e.link_members(aqua)) == ["T487", "T488"]
    rep = e.link_rep(aqua)
    assert e.chars_ro(rep)["power"] == 10000        # 5000 + 5000
    assert len(e.bz_tops(0)) == 1                   # グループは1体として数える


def test_no_partner_no_link(rules):
    """指定名のゴッドがいなければリンク手順は出ない。"""
    e = setup(rules, {"hand": ["T487"], "mana": ["T030"] * 5},
              {"bz": ["T001"]}, filler="T002")
    seen = _drive(e, ["T487"], {})
    assert seen == []
    assert e.s.cards[_cid(e, "T487")].link == 0


def test_wrong_name_no_link(rules):
    """場にいても、指定名でないゴッドにはリンクできない（判別）。"""
    e = setup(rules, {"hand": ["T487"], "mana": ["T030"] * 5, "bz": ["T489"]},
              {"bz": ["T001"]}, filler="T002")
    seen = _drive(e, ["T487"], {"T487": "T488"})
    assert seen == []
    assert e.s.cards[_cid(e, "T487")].link == 0


def test_three_way_group(rules):
    """3体目のゴッドはグループ内の指定名ゴッド経由で合流する。"""
    e = setup(rules,
              {"hand": ["T487", "T489"],
               "mana": ["T030"] * 5 + ["T001"] * 4, "bz": ["T488"]},
              {"bz": ["T001"]}, filler="T002")
    # リンク先の選択肢はグループの代表で提示される（テラはブレイズ経由で合流）
    _drive(e, ["T487", "T489"], {"T487": "T488", "T489": "T488"},
           until=lambda e: any(e.s.cards[c].defn == "T489" and e.s.cards[c].link
                               for c in e.zlist("bz", 0)))
    terra = _cid(e, "T489")
    members = sorted(e.s.cards[m].defn for m in e.link_members(terra))
    assert members == ["T487", "T488", "T489"]
    assert e.chars_ro(e.link_rep(terra))["power"] == 14000


def test_duplicate_name_blocked(rules):
    """同名のゴッドが既にいるグループにはリンクできない。"""
    e = setup(rules, {"hand": ["T487", "T487"], "mana": ["T030"] * 10,
                      "bz": ["T488"]},
              {"bz": ["T001"]}, filler="T002")
    seen = _drive(e, ["T487", "T487"], {"T487": "T488"})
    # リンクの諮問は1回だけ（2体目は同名がいるので対象が無い）
    assert len(seen) == 1
    linked = [c for c in e.zlist("bz", 0)
              if e.s.cards[c].defn == "T487" and e.s.cards[c].link]
    assert len(linked) == 1


def test_named_group_leave_replacement(rules):
    """リンク中のグループが離れる時は1枚だけ離れる（既存機構の共用）。"""
    e = setup(rules, {"hand": ["T487"], "mana": ["T030"] * 5, "bz": ["T488"]},
              {"hand": ["T056"], "mana": ["T082"] * 3, "bz": ["T001"]},
              filler="T002")
    _drive(e, ["T487"], {"T487": "T488"},
           until=lambda e: any(e.s.cards[c].defn == "T487" and e.s.cards[c].link
                               for c in e.zlist("bz", 0)))
    # 相手が破壊呪文でグループを狙う → 離れる1枚を選ぶ（choose_link_leave）
    for _ in range(200):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        gy = [e.s.cards[c].defn for c in e.zlist("graveyard", 0)]
        if "T487" in gy:
            break
        if d["kind"] == "main" and d.get("player") == 1 and "play:T056" in keys:
            e.answer([keys.index("play:T056")])
            continue
        if d["kind"] == "choose_link_leave":
            hit = next(i for i, k in enumerate(keys) if "T487" in k)
            e.answer([hit])
            continue
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    gy = [e.s.cards[c].defn for c in e.zlist("graveyard", 0)]
    assert "T487" in gy
    blaze = _cid(e, "T488")
    assert e.s.cards[blaze].link == 0               # 1枚になればリンク解消


def test_link_established_trigger(rules):
    """T490: リンクした時にドローする（link_established は名前指定でも出る）。"""
    e = setup(rules, {"hand": ["T490"], "mana": ["T343"] * 4, "bz": ["T487"]},
              {"bz": ["T001"]}, filler="T002")
    _drive(e, ["T490"], {"T490": "T487"},
           until=lambda e: len(e.zlist("hand", 0)) >= 1
           and any(e.s.cards[c].defn == "T490" and e.s.cards[c].link
                   for c in e.zlist("bz", 0)))
    luna = _cid(e, "T490")
    assert e.s.cards[luna].link
    assert len(e.zlist("hand", 0)) == 1             # ドローした1枚（T002）
