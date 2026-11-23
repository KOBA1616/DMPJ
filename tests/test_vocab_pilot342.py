"""語彙パイロット第342弾: battle_power_grant（エンジン拡張）。

対象（pure 2件）:
- dmr11-016 破戒のインガ シャンツァイ（バトル中、自分の
  オラクルとゴッドのパワーは+3000される）
- dm23rp2x-006 ボルシャック・ノブリス・ドラゴン（自分の
  アーマードすべては、バトル中パワーを+3000する）

拡張: _battle_bonus はこれまで戦闘するカード自身の常在型
（affects: self）しか見ておらず、affects 辞書形で他へ付与する
battle_power は一切効いていなかった（dm21-031 で実測:
3000同士のバトルが引き分けになった）。chars の集約と同じく、
バトルゾーン／シールドゾーンの発生源から affects が合う
常在型を集めるようにした。{ref: self} 形も _subject_match で
本人だけに合うため、既登録の同型15件すべてが実働化する。

付与形: {kind: static, affects: {owner: you, filter: ...},
mod: {battle_power: {amount: N}}}。only: attacking /
opponent_filter / count の扱いは本人の常在型と同じ。

proto: T1034（016型）/ T1035（006型）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
scenario.build を直接包む（第319弾以降の作法）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

GRANT_016 = [{
    "kind": "static",
    "affects": {"owner": "you",
                "filter": {"any_of": [{"race_has": "オラクル"},
                                      {"race_has": "ゴッド"}]}},
    "mod": {"battle_power": {"amount": 3000}},
}]

GRANT_006 = [{
    "kind": "static",
    "affects": {"owner": "you", "filter": {"race_has": "アーマード"}},
    "mod": {"battle_power": {"amount": 3000}},
}]

FORM_016 = GRANT_016
FORM_006 = GRANT_006


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    c = proto_card("T1034")
    assert c["abilities"] == FORM_016
    parse_card(c, TABLES)
    c = proto_card("T1035")
    assert c["abilities"] == FORM_006
    parse_card(c, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _battle(e, attacker, defender, limit=300):
    """attacker（p0, セットアップ配置）で defender を攻撃し、
    次の p1 の charge まで進める。"""
    tgt = next(c for c in e.bz_tops(1)
               if e.s.cards[c].defn == defender)
    e.s.cards[tgt].tapped = True
    key = f"attack:{attacker}:{defender}"
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        k = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 \
                and key in k:
            e.answer([k.index(key)])
            continue
        if d["kind"] == "charge" and d.get("player") == 1:
            return
        if d["kind"] == "block" and "no_block" in k:
            e.answer([k.index("no_block")])
            continue
        if d["kind"] == "choose_shields":
            e.answer([])
            continue
        if "pass" in k:
            e.answer([k.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def test_t1034_god_ally_gets_bonus(rules):
    e = _build(rules, {"bz": ["T1034", "T053"]}, {"bz": ["T005"]})
    _battle(e, "T053", "T005")          # ゴッド 2000+3000 > 3000
    assert "T053" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    assert _defns(e, "graveyard", 1) == ["T005"]


def test_t1034_non_matching_ally_no_bonus(rules):
    e = _build(rules, {"bz": ["T1034", "T001"]}, {"bz": ["T005"]})
    _battle(e, "T001", "T005")          # 自然 2000 < 3000: 付与なし
    assert _defns(e, "graveyard", 0) == ["T001"]
    assert "T005" in [e.s.cards[c].defn for c in e.bz_tops(1)]


def test_t1035_armored_ally_gets_bonus(rules):
    e = _build(rules, {"bz": ["T1035", "T277"]}, {"bz": ["T005"]})
    _battle(e, "T277", "T005")          # アーマード 1000+3000 > 3000
    assert "T277" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    assert _defns(e, "graveyard", 1) == ["T005"]


def test_registered_dm21_031_now_works(rules):
    # 既登録の同型（only: attacking の付与）が実働化したことの固定。
    # 攻撃側: 3000+4000 > 3000 で勝つ。
    e = _build(rules, {"bz": ["dm21-031"]}, {"bz": ["T005"]})
    _battle(e, "dm21-031", "T005")
    assert "dm21-031" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    assert _defns(e, "graveyard", 1) == ["T005"]
