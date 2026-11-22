"""語彙パイロット第354弾: forced_attack_target（ドリフト）。

対象（pure 2件すべて）:
- dm16-s03（進化: 相手のクリーチャーは、可能であれば
  このクリーチャーを攻撃する）
- dm10-s07 不落の超人（相手のターン中、タップされていて、
  そのターンにまだ攻撃を受けていない場合に同じ誘引）

形: 誘引は mod の must_be_attacked（第51弾で実装済み。
攻撃先の候補がタップした誘引持ちに限られる）。
dm10-s07 の条件は、is_turn: opp ＋「自分がタップしている」
を exists の ref セレクタに filter {tapped: true} を重ねて、
「まだ攻撃を受けていない」を turn_count の attack_on
（クリーチャー単位、第228弾系）== 0 で表す。

proto: T1063（s07型）/ T1064（s03型）/ T1065（進化元）。

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

STATIC_S03 = {"kind": "static", "affects": "self",
              "mod": {"must_be_attacked": True}}
STATIC_S07 = {
    "kind": "static", "affects": "self",
    "if": {"all": [
        {"is_turn": "opp"},
        {"exists": {"ref": "self", "filter": {"tapped": True}}},
        {"cmp": [{"turn_count": {"kind": "attack_on", "ref": "self"}},
                 "==", 0]}]},
    "mod": {"must_be_attacked": True},
}

FORM_S03 = [STATIC_S03]
FORM_S07 = [STATIC_S07]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    c = proto_card("T1063")
    assert c["abilities"] == FORM_S07
    parse_card(c, TABLES)
    c = proto_card("T1064")
    assert c["abilities"] == FORM_S03
    parse_card(c, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _p0_first_attack_options(e, attacker):
    """p0 の最初の攻撃判断で attacker の選択肢キーを返す。"""
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0:
            return [k for k in keys if k.startswith(f"attack:{attacker}:")]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("attack decision never came")


def test_conditional_taunt_only_when_tapped(rules):
    # タップしている時: プレイヤーを攻撃できず、このクリーチャーを
    # 攻撃しなければならない
    e = _build(rules, {"bz": ["T005"]}, {"bz": ["T1063"]})
    cid = e.bz_tops(1)[0]
    e.s.cards[cid].tapped = True
    opts = _p0_first_attack_options(e, "T005")
    assert "attack:T005:player" not in opts, opts
    assert "attack:T005:T1063" in opts, opts
    # アンタップの時: 誘引は働かず、プレイヤーを攻撃できる
    e = _build(rules, {"bz": ["T005"]}, {"bz": ["T1063"]})
    opts = _p0_first_attack_options(e, "T005")
    assert "attack:T005:player" in opts, opts


def test_evolution_taunt(rules):
    e = _build(rules, {"bz": ["T005"]},
               {"hand": ["T1064"], "bz": ["T1065"],
                "mana": ["T053", "T053", "T053", "T053",
                         "T053", "T053", "T053"]})
    state = {}
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if (d["kind"] == "attack" and d.get("player") == 0
                and state.get("p1_attacked")):
            opts = [k for k in keys if k.startswith("attack:T005:")]
            assert "attack:T005:player" not in opts, opts
            assert "attack:T005:T1064" in opts, opts
            return
        if (d["kind"] == "main" and d.get("player") == 1
                and "play:T1064" in keys):
            state["played"] = True
            e.answer([keys.index("play:T1064")])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif (d["kind"] == "attack" and d.get("player") == 1
                and "attack:T1064:player" in keys):
            state["p1_attacked"] = True
            e.answer([keys.index("attack:T1064:player")])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("taunt check never reached")
