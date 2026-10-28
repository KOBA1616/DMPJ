"""「ゾーンに入った時」以外の誘発（唱える時・攻撃時・ターン開始・破壊時）で回るループの検出。
静的なゾーン変換グラフ（dmsim.zone_graph）が候補を出し、動的な検出（dmsim.loop / loop_first / solitaire）が
同じ差分を再生で確かめる。架空カードは tests/trigger_loop_cards.yaml（X 始まり）。"""
from pathlib import Path

import pytest
from conftest import find_option, setup

from dmsim.defs import load_rules
from dmsim.defs import card_yaml_files  # noqa: E402
from dmsim.loop import LoopDetector, abstract, draw_keys, verify
from dmsim.loop_first import discover_loops
from dmsim.play import passive_policy
from dmsim.solitaire import round_probe
from dmsim.zone_graph import find_cycles

DATA = Path(__file__).resolve().parent.parent / "data"
MAD = "dmrp06-006"          # マッド・デーモン閣下／デーモン・ハンド
DRAGELION = "dm22ex1-007"   # 超神星DOOM・ドラゲリオン
DARK = "dm01-027"


@pytest.fixture(scope="module")
def xr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "trigger_loop_cards.yaml"])


def cycles_of(rules, card, other=None, max_cards=2):
    """そのカード（と other）だけでできる循環。"""
    want = sorted({card, other} - {None})
    return [c for c in find_cycles(rules, max_cards=max_cards) if c.cards == want]


# ---- 静的: ゾーン変換グラフ ----------------------------------------------------------------

def test_attack_trigger_loops_only_if_it_untaps(xr):
    """攻撃時の誘発は、アンタップして攻撃し直せる時だけ自分で回る（攻撃は1体につき1回）。"""
    (c,) = cycles_of(xr, "X001")
    assert c.period == "in_turn" and c.opp_delta() == {"deck": -1, "graveyard": 1}
    assert cycles_of(xr, "X007") == []                 # 同じ「攻撃時に山札を削る」でもアンタップがなければ回らない


def test_spell_returned_to_hand_is_a_cycle_with_its_mana_cost(xr):
    (c,) = cycles_of(xr, "X002")
    assert c.period == "in_turn" and c.mana() == 1 and c.opp_delta() == {"deck": -1, "graveyard": 1}


def test_cast_trigger_returning_the_spell_pairs_with_any_spell(xr):
    """唱えた時の誘発が墓地の呪文を手札に戻すと、呪文→誘発→呪文 で回る。"""
    (c,) = cycles_of(xr, "X003", "X004")
    assert [b.premise for b in c.bundles if b.origin == "trigger"] == ["cast"]
    assert c.period == "in_turn" and c.sure and c.mana() == 1
    assert c.opp_delta() == {"deck": -1, "graveyard": 1}
    assert cycles_of(xr, "X003", "X001") == []         # 呪文のないカードとは回らない


def test_destroy_and_graveyard_triggers_form_a_cycle_through_the_graveyard(xr):
    (c,) = cycles_of(xr, "X005", max_cards=1)
    assert sorted(b.premise for b in c.bundles) == ["enter:bz", "enter:graveyard"]
    assert c.period == "in_turn" and c.opp_delta() == {"deck": -1, "graveyard": 1}


def test_turn_start_trigger_is_a_per_turn_clock_not_an_in_turn_loop(xr):
    (c,) = cycles_of(xr, "X006", max_cards=1)
    assert c.period == "gated:turn_start" and c.gates() == ["turn_start"]


def test_draw_only_recursion_is_marked_as_luck(xr):
    """ドローで偶然自分を引くだけの循環は、狙って回せない（sure=False）。"""
    (c,) = cycles_of(xr, "T003", max_cards=1)          # 知識の泉: 2枚引く
    assert not c.sure


def test_real_twin_spell_and_creature_form_a_cast_loop(rules):
    """マッド・デーモン閣下／デーモン・ハンド: 呪文面を唱える→（名前にハンドの呪文を唱えた時）墓地から自分を手札へ。"""
    cs = [c for c in cycles_of(rules, MAD, max_cards=1)
          if any(b.premise == "cast" for b in c.bundles) and len(c.bundles) == 2]
    assert len(cs) == 1 and cs[0].period == "in_turn"
    assert cs[0].mana() == 6 and cs[0].opp_delta() == {"bz": -1, "graveyard": 1}   # 唱えるたびに相手のクリーチャーを破壊


def test_real_cards_without_untap_do_not_loop_on_attack(rules):
    """ドラゲリオンはメテオバーンで攻撃時に動くが、アンタップがないので攻撃時だけでは回らない。"""
    assert cycles_of(rules, DRAGELION, max_cards=1) == []


def test_real_turn_start_cards_are_clocks(rules):
    gated = {rules.cards[x].name for c in find_cycles(rules, max_cards=1) if c.gates() for x in c.cards}
    assert {"絶望神サガ", "水上第九院 シャコガイル"} <= gated


# ---- 動的: 再生で確かめる ----------------------------------------------------------------

def found(rules, p0, deck_left=(30, 6), p1=None):
    e = setup(rules, p0, p1, deck_left=list(deck_left))
    fs = discover_loops(e, 0, 400)
    assert all(f.verified for f in fs)
    return fs


def test_attack_loop_is_found_dynamically_and_matches_the_static_delta(xr):
    (f,) = found(xr, {"bz": ["X001"]})
    assert f.cert.delta["deck:1"] == -1 and f.cert.delta["graveyard:1"] == 1       # 静的グラフの相手側の収支
    assert f.cert.delta["shield:1"] == -1 and f.cert.win_by == "opp_deck_out"      # 攻撃は相手のシールドも割る
    assert found(xr, {"bz": ["X007"]}) == []                                       # アンタップなしは回らない


def test_spell_loop_is_limited_by_mana(xr):
    (f,) = found(xr, {"hand": ["X002"], "mana": ["T003"] * 6})
    assert f.cert.delta == {"deck:1": -1, "graveyard:1": 1, "mana_untapped:0": -1}
    assert f.cert.limit == 5 and f.cert.win_by == "opp_deck_out"                   # 山札6枚: 6回目が必要、周回できるのは5回まで（+初回）


def test_cast_trigger_loop_is_found_dynamically(xr):
    (f,) = found(xr, {"hand": ["X004"], "bz": ["X003"], "mana": ["T003"] * 6})
    assert f.cert.delta == {"deck:1": -1, "graveyard:1": 1, "mana_untapped:0": -1}
    assert len(f.cert.actions) == 2                                                # 唱える + 誘発の may


def test_graveyard_trigger_loop_is_found_dynamically(xr):
    (f,) = found(xr, {"hand": ["X005"], "mana": [DARK] * 3})
    assert f.cert.delta == {"deck:1": -1, "graveyard:1": 1} and f.cert.limit == float("inf")


def test_turn_start_clock_shows_up_as_a_round_cycle(xr):
    """ターン開始時の誘発は、ラウンド周期（自分＋相手のターン）の差分に現れる。基準（両者のドロー）より1枚多く削る。"""
    base = round_probe(setup(xr, {"bz": ["X007"]}, deck_left=[30, 20]), 0)
    clock = round_probe(setup(xr, {"bz": ["X006"]}, deck_left=[30, 20]), 0)
    assert base.delta["deck:1"] == -1 and clock.delta["deck:1"] == -2
    assert clock.verified == 2 and clock.win_by == "opp_deck_out"


def test_real_cast_loop_is_detected_when_reported_unfiltered(rules):
    """実カード: デーモン・ハンドの唱え直し。相手に何も起きない空回りは既定では報告しない（資源を失うだけ）が、
    report_all なら骨格の回帰として見え、再生で確かめられる。"""
    e = setup(rules, {"bz": [MAD], "hand": [MAD], "mana": [DARK] * 12}, deck_left=[30, 30])
    det = LoopDetector(me=0, period="in_turn", hand_keys=draw_keys(e, 0), report_all=True)
    cert, snaps = None, {}
    for _ in range(80):
        d = e.advance()
        snaps.setdefault(abstract(e, "in_turn", det.hand_keys)[0], e.clone())     # 骨格を最初に見た局面
        cert = det.observe(e)
        if cert is not None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["player"] != 0:
            e.answer(passive_policy(e, d))
        elif d["kind"] == "charge":
            e.answer([find_option(d, "pass")])
        elif d["kind"] == "main" and f"play:{MAD}:1" in keys:
            e.answer([find_option(d, f"play:{MAD}:1")])      # 呪文面を唱える
        elif d["kind"] == "choose_cards" and any("graveyard" in k for k in keys):
            e.answer([0])                                    # 墓地のクリーチャー（自分）を手札へ
        else:
            e.answer(passive_policy(e, d))
    assert cert is not None
    assert cert.delta == {"mana_untapped:0": -6}
    assert cert.limit == 1                                         # 1周目で6マナ払った後に検出するので、残りはあと1周
    assert verify(snaps[cert.start_skeleton], cert, times=1).verified == 1
