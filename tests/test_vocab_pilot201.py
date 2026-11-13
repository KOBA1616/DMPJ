"""語彙パイロット第201弾: sasageeru（ササゲール）のイディオム確認。

ササゲール本体は既存だった: mod `sac_reduce: N` を持つ自分の場のカードは、
ディスペクター（種族に「ディスペクター」を含む）の召喚時に破壊して
コストを N 軽減するプールになる（turn.py の _sac_pool / _sac_reduced）。
本弾はその挙動と、残っていたカードの他条項の形を固定する:

- 純粋なササゲール・タマシード: static {affects: self, mod: {sac_reduce: N}}
  だけでよい。
- 「ディスタス/ディスペクター・カードを自分のマナゾーンに置いた時、
  そのカードをアンタップする」は move（to: mana）誘発で、対象は
  {ref: event.subject}、フィルタは種族の any_of で表す。多色カードは
  マナゾーンにタップして置かれる（ルール 405.1）ため、誘発で
  アンタップされる様子が観測できる。
- 「ササゲールを使った時、軽減したディスペクターに付与する」節は、
  生贄にした破壊と召喚先を結ぶ印が無いため未対応（sac_reduce_followup）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T506", "T507")


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


def _keys(d):
    return [o["key"] for o in d["options"]]


def test_sac_reduce_makes_summon_affordable(rules):
    """T506: コスト7のディスペクターが、マナ5＋ササゲール2で召喚できる。
    召喚後、ササゲール玉は破壊されている。玉が無ければ召喚できない（判別）。"""
    mana = ["T277", "T082", "T003", "T001", "T277"]   # 火・闇・水・自然をカバー
    e = setup(rules, {"bz": ["T506"], "hand": ["T397"], "mana": mana},
              {"bz": ["T001"]}, filler="T002")
    played = False
    for _ in range(160):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and "play:T397" in keys:
            e.answer([keys.index("play:T397")])
            played = True
            continue
        if played and d["kind"] == "charge":
            break
        if d["kind"] == "choose_cards" and any("T506" in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if "T506" in k)])
            continue
        if d["kind"] == "yes_no" and "yes" in keys:
            e.answer([keys.index("yes")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert played
    assert any(e.s.cards[c].defn == "T397" for c in e.zlist("bz", 0)
               if e.s.cards[c].controller == 0)
    assert any(e.s.cards[c].defn == "T506" for c in e.zlist("graveyard", 0))
    # 判別: 玉が無いとマナ5では召喚できない
    e = setup(rules, {"hand": ["T397"], "mana": mana}, {"bz": ["T001"]},
              filler="T002")
    assert "play:T397" not in [o["key"] for o in e._play_options(0)]


def test_mana_put_trigger_untaps_dispector(rules):
    """T507: 多色ディスペクターをマナに置くと（タップで置かれる）、
    誘発でアンタップする。反応獣がいなければタップのまま（判別）。"""
    def charge_and_check(with_reactor):
        zones = {"hand": ["T397"]}
        if with_reactor:
            zones["bz"] = ["T507"]
        e = setup(rules, zones, {"bz": ["T001"]}, filler="T002")
        for _ in range(80):
            d = e.advance()
            if d is None:
                break
            keys = _keys(d)
            if d["kind"] == "charge" and d.get("player") == 0 \
                    and "charge:T397" in keys:
                e.answer([keys.index("charge:T397")])
                continue
            mana397 = [c for c in e.zlist("mana", 0)
                       if e.s.cards[c].defn == "T397"]
            if mana397 and d["kind"] == "charge":
                return e.s.cards[mana397[0]].tapped
            if "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
        mana397 = [c for c in e.zlist("mana", 0) if e.s.cards[c].defn == "T397"]
        return e.s.cards[mana397[0]].tapped if mana397 else None
    assert charge_and_check(True) is False    # 誘発でアンタップ
    assert charge_and_check(False) is True    # 置いたままタップ
