"""語彙パイロット第145弾: distinct_cost_count（異なるコストの種類数）。

新式 {distinct_cost_count: <セレクタ>}: 対象カード群にあるコストの種類数（civ_count のコスト版）。
バラバラエティ（「コストが異なる自分のエレメントが3つ以上あれば、この能力を与える」）と
バラエティ・ブレイカー（「コストが異なる自分のクリーチャーの数、シールドをブレイクする」）に対応する。
数えるコストは chars の cost（印刷コスト。コスト軽減などの支払うコストの増減は cost を変えない）。
ブレイク数は breaks dict の base（既定1）で土台を変え、base: 0 でちょうど種類数になる。

評価の再入ガード: 数える対象に発生源自身が含まれるのがこのファミリーの常形で、素朴に chars を呼ぶと
自身の常在条件・ブレイク数の評価から再入して無限再帰する。評価中（_distinct_costing）のカードは
定義（印刷）特性・コストで見る。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()
ELEM = {"distinct_cost_count": {"zone": ["bz", "mana"], "owner": "you"}}


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _rule_card(cid):
    with open(Path(__file__).parent / "rule_cards.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_distinct_cost_count_parses():
    """各形（常在の if／誘発の if／breaks の base／free_if／draw の count）が parse できること。"""
    for cid in ("T173", "T174", "T175", "T176"):
        card = parse_card(_proto_card(cid), TABLES)
        assert card is not None
    assert "distinct_cost_count" in str(parse_card(_proto_card("T173"), TABLES).abilities)
    breaks = parse_card(_proto_card("T174"), TABLES).abilities[0]["mod"]["breaks"]
    assert breaks["base"] == 0 and "distinct_cost_count" in breaks
    assert "distinct_cost_count" in str(parse_card(_proto_card("T175"), TABLES).free_if)
    card = parse_card(_rule_card("R103"), TABLES)
    assert "distinct_cost_count" in str(card.abilities[0]["if"])


def test_variety_condition_counts_elements(rr):
    """エレメント（バトルゾーン＋マナゾーン）の異なるコストの種類数で常在型の deny が切り替わる。

    R103 自身（コスト4）もエレメントとして数える。同じコストのカードが2枚あっても種類数は1。
    """
    e = setup(rr, {"bz": ["R103"]}, {})
    mine = e.bz_tops(0)[0]
    assert e.eval_expr(ELEM, {"you": 0}) == 1          # 自身だけなら1種類
    assert not e.permits(mine, "attack_player")          # 3未満なので攻撃できない

    e = setup(rr, {"bz": ["R103"], "mana": ["T001", "T001"]}, {})   # コスト2が2枚
    mine = e.bz_tops(0)[0]
    assert e.eval_expr(ELEM, {"you": 0}) == 2          # 重複は数えない（{4, 2}）
    assert not e.permits(mine, "attack_player")

    e = setup(rr, {"bz": ["R103"], "mana": ["T001", "T004"]}, {})   # コスト2と3
    mine = e.bz_tops(0)[0]
    assert e.eval_expr(ELEM, {"you": 0}) == 3          # {4, 2, 3}
    assert e.permits(mine, "attack_player")              # 3以上で攻撃できる


def test_variety_condition_face_down_mana_counts(rr):
    """マナゾーンで裏向きのカードもエレメントとして数える（コストは印刷コスト）。"""
    e = setup(rr, {"bz": ["R103"], "mana": ["T001", "T004"]}, {})
    cid4 = next(c for c in e.zlist("mana", 0) if e.cdef(c).id == "T004")
    e.s.cards[cid4].face_down = True                   # 水晶武装などで裏向きになったマナ
    assert e.eval_expr(ELEM, {"you": 0}) == 3
    assert e.permits(e.bz_tops(0)[0], "attack_player")


def test_distinct_cost_count_uses_printed_cost(rr):
    """コスト軽減（cost_may）が付いていても、数えるのは印刷コスト。

    T044 の軽減対象である T004（光・コスト3）と対象外の T005（火・コスト3）が手札にある時、
    種類数は {3} の1。支払いコストで数えれば {2, 3} の2になってしまう。
    """
    e = setup(rr, {"bz": ["T044"], "hand": ["T004", "T005"]}, {})
    by = {e.cdef(c).id: c for c in e.zlist("hand", 0)}
    assert e.chars(by["T004"])["cost_may"]             # T004 には軽減が付いている
    assert not e.chars(by["T005"])["cost_may"]
    assert e.chars(by["T004"])["cost"] == 3            # chars の cost は印刷コストのまま
    sel = {"distinct_cost_count": {"zone": "hand", "owner": "you", "filter": {"types": ["creature"]}}}
    assert e.eval_expr(sel, {"you": 0}) == 1


def test_variety_breaker_base0(rr):
    """バラエティ・ブレイカー: ブレイク数はちょうど種類数（base: 0。1+種類数ではない）。"""
    e = setup(rr, {"bz": ["T174"]}, {})
    mine = e.bz_tops(0)[0]
    assert e.chars(mine)["breaks"] == 1               # 自身だけなら種類数1 → ブレイク1（2ではない）

    e = setup(rr, {"bz": ["T174", "T001", "T004"]}, {})
    mine = next(c for c in e.bz_tops(0) if e.cdef(c).id == "T174")
    assert e.chars(mine)["breaks"] == 3               # コスト {5, 2, 3} の3種類


def test_two_variety_breakers_terminate(rr):
    """バラエティ・ブレイカーが2体いても相互再帰せず、同じコスト同士は1種類に数える。"""
    e = setup(rr, {"bz": ["T174", "T174"]}, {})
    assert [e.chars(c)["breaks"] for c in e.bz_tops(0)] == [1, 1]
