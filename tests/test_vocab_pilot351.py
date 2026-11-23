"""語彙パイロット第351弾: battle_power_against_specific_race
（ドリフト）。

対象（pure 2件すべて）:
- dm08-006 光器サーシャ（ドラゴン・ブロッカー＋ドラゴンと
  バトルする時パワー+6000）
- dm16-021 光器スヴェータ（デーモン・コマンドまたは
  ドラゴンとバトルする時パワー+4000）

形: バトル中の種族条件つきパワー増は battle_power:
{amount, opponent_filter} の確立形（第349弾のゼニス条項と
同型）。opponent_filter は any_of で複数種族を束ねられる。
ドラゴン・ブロッカーは、block の許可（既定 false）を
other フィルタつきの allow 項目で与える:
{affects: self, mod: {allow: [{action: block,
other: {race_has: ドラゴン}}]}}。キーワード blocker は
無制限のブロック許可になるため使わない。

proto: T1056（006型）/ T1057（021型）。

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

DRAGON_BLOCK = {
    "kind": "static", "affects": "self",
    "mod": {"allow": [{"action": "block",
                       "other": {"race_has": "ドラゴン"}}]},
}
BATTLE_006 = {
    "kind": "static", "affects": "self",
    "mod": {"battle_power": {"amount": 6000,
                             "opponent_filter": {"race_has": "ドラゴン"}}},
}
BATTLE_021 = {
    "kind": "static", "affects": "self",
    "mod": {"battle_power": {"amount": 4000,
                             "opponent_filter": {"any_of": [
                                 {"race_has": "デーモン・コマンド"},
                                 {"race_has": "ドラゴン"}]}}},
}

FORM_006 = [DRAGON_BLOCK, BATTLE_006]
FORM_021 = [BATTLE_021]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    for tid, form in (("T1056", FORM_006), ("T1057", FORM_021)):
        c = proto_card(tid)
        assert c["abilities"] == form, tid
        parse_card(c, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _attack_and_maybe_block(e, attacker, blocker, state):
    """p0 の attacker がプレイヤーを攻撃する。block 判断が
    出たら state に記録し、blocker が選択肢にあればブロック
    する。p1 の charge まで進める。"""
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 1:
            return
        if d["kind"] == "attack" and d.get("player") == 0 \
                and not state.get("attacked"):
            tgt = [k for k in keys
                   if k == f"attack:{attacker}:player"]
            if tgt:
                state["attacked"] = True
                e.answer([keys.index(tgt[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "block":
            state["block_decision"] = keys
            pick = [i for i, k in enumerate(keys)
                    if k.startswith(f"bz:{blocker}")]
            if pick:
                state["blocked"] = True
                e.answer([pick[0]])
            else:
                e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("attack never finished")


def test_dragon_blocker_only_blocks_dragons(rules):
    # 非ドラゴン（T005）の攻撃はブロックできない
    e = _build(rules, {"bz": ["T005"]}, {"bz": ["T1056"]})
    state = {}
    _attack_and_maybe_block(e, "T005", "T1056", state)
    assert state.get("attacked")
    assert not state.get("block_decision"), state
    # ドラゴン（T156）の攻撃はブロックでき、バトルに勝つ
    e = _build(rules, {"bz": ["T156"]}, {"bz": ["T1056"]})
    state = {}
    _attack_and_maybe_block(e, "T156", "T1056", state)
    assert state.get("blocked"), state
    assert "T156" in [e.s.cards[c].defn for c in e.zlist("graveyard", 0)]
    assert "T1056" in [e.s.cards[c].defn for c in e.bz_tops(1)]


def test_battle_power_only_vs_specific_races(rules):
    # ドラゴン（4000）とのバトル: 4000+4000 で勝つ
    e = _build(rules, {"bz": ["T156"]}, {"bz": ["T1057"]})
    state = {}
    _attack_and_maybe_block(e, "T156", "T1057", state)
    assert state.get("blocked"), state
    assert "T156" in [e.s.cards[c].defn for c in e.zlist("graveyard", 0)]
    assert "T1057" in [e.s.cards[c].defn for c in e.bz_tops(1)]
    # 非該当（T1014、17000）とのバトル: 加算なしで負ける
    e = _build(rules, {"bz": ["T1014"]}, {"bz": ["T1057"]})
    state = {}
    _attack_and_maybe_block(e, "T1014", "T1057", state)
    assert state.get("blocked"), state
    assert "T1057" in [e.s.cards[c].defn for c in e.zlist("graveyard", 1)]
