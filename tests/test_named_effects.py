"""名前つき効果（注釈つきキーワード）のエンジン側の挙動。条文: 405.1 / 507.1a, 507.2b / 509.2 / 509.5e / 609。
架空カードは tests/named_cards.yaml（N 始まり）。"""
from pathlib import Path

import pytest
from conftest import answer, setup

from dmsim.defs import DATA, load_rules


@pytest.fixture(scope="module")
def rr():
    return load_rules(sorted((DATA / "cards").glob("*.yaml")) + [Path(__file__).parent / "named_cards.yaml"])


def top(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def test_multicolor_enters_mana_tapped_monocolor_untapped(rr):
    """405.1: 多色はタップして置く。単色はアンタップ（テキストの注釈には頼らない）。"""
    e = setup(rr, {"hand": ["T018", "T001"]})
    answer(e, "charge", "charge:T018")
    e.advance()
    assert [e.s.cards[c].tapped for c in e.zlist("mana", 0)] == [True]
    e = setup(rr, {"hand": ["T018", "T001"]})
    answer(e, "charge", "charge:T001")
    e.advance()
    assert [e.s.cards[c].tapped for c in e.zlist("mana", 0)] == [False]


def test_powered_breaker_breaks_one_per_6000_power(rr):
    """パワー12000 → 1 + 2 = 3、5000 → 1。パワーが変わればブレイク数も変わる。"""
    e = setup(rr, {"bz": ["N001", "N002"]})
    assert e.chars(top(e, 0, "N001"))["breaks"] == 3
    assert e.chars(top(e, 0, "N002"))["breaks"] == 1
    e2 = setup(rr, {"bz": ["N002"]})
    e2.s.continuous.append({"mod": {"power": 1000}, "affected": [e2.s.ref(top(e2, 0, "N002"))], "duration": "permanent",
                            "expires": None, "owner": 0})
    assert e2.chars(top(e2, 0, "N002"))["breaks"] == 2           # 6000 → 2 枚


def test_powered_breaker_attack_breaks_three_shields(rr):
    e = setup(rr, {"bz": ["N001"]})
    answer(e, "attack", "attack:N001:player")
    d = e.advance()
    assert d["kind"] == "choose_shields" and len(d["options"]) == 5
    e.answer([0, 1, 2])
    e.advance()
    assert len(e.zlist("shield", 1)) == 2


def test_guardman_redirects_attack_to_itself_without_being_a_blocker(rr):
    """507.1a: 攻撃されているクリーチャーがいる時、ガードマンを選んで攻撃先を変更できる。507.2b: ブロッククリーチャーにはならない。"""
    e = setup(rr, {"bz": ["T001"]}, {"bz": ["N003", "T004"]})
    e.s.cards[top(e, 1, "T004")].tapped = True
    answer(e, "attack", "attack:T001:T004")
    answer(e, "block", "guard:N003")
    e.advance()
    assert e.s.cards[top(e, 1, "T004")].zone == "bz"    # 本来の攻撃先は無事
    assert not [c for c in e.bz_tops(0) if e.s.cards[c].defn == "T001"]   # 2000 < 3000 で攻撃側が負けた


def test_guardman_unavailable_when_attacking_player(rr):
    """507.1a の例: プレイヤーを攻撃している時はガードマンを選べない。"""
    e = setup(rr, {"bz": ["T001"]}, {"bz": ["N003"]})
    answer(e, "attack", "attack:T001:player")
    d = e.advance()
    assert d["kind"] != "block" or "guard:N003" not in [o["key"] for o in d["options"]]


def test_g_strike_stops_chosen_creature_from_attacking(rr):
    """509.5e: シールドから手札に加える時、相手のクリーチャー1体を選ぶ。このターン、そのクリーチャーは攻撃できない。"""
    e = setup(rr, {"bz": ["T001", "T004"]}, {"shield": ["N004"]})
    answer(e, "attack", "attack:T001:player")
    answer(e, "yes_no", "yes")
    answer(e, "choose_cards", "bz:T004:0")
    d = e.advance()
    assert d["kind"] == "charge" and d["player"] == 1       # T001 はタップ済み、T004 は攻撃不可 → 攻撃の選択がなくターンが終わる


def test_g_strike_is_optional(rr):
    e = setup(rr, {"bz": ["T001", "T004"]}, {"shield": ["N004"]})
    answer(e, "attack", "attack:T001:player")
    answer(e, "yes_no", "no")
    d = e.advance()
    assert "attack:T004:player" in [o["key"] for o in d["options"]]


def test_g_strike_does_not_trigger_when_drawn(rr):
    """シールドゾーン以外（山札）から手札に加わっても誘発しない。"""
    e = setup(rr, {}, {"hand": []}, filler="N004")
    answer(e, "charge", "pass")
    assert not e.s.pending
    e.s.active = 1
    e.apply_batch([{"ev": "draw", "player": 1}])
    assert not e.s.pending


def test_shield_saver_destroys_itself_instead_of_shield_break(rr):
    """609: ブレイクされる時、かわりにこのクリーチャーを破壊してもよい。シールドは残り、手札に加わらない。"""
    e = setup(rr, {"bz": ["T001"]}, {"bz": ["N005"]})
    answer(e, "attack", "attack:T001:player")
    answer(e, "choose_shields", "shield")
    answer(e, "choose_replacement", "replace:N005:0")
    e.advance()
    assert not any(e.s.cards[c].defn == "N005" for c in e.bz_tops(1))
    assert len(e.zlist("shield", 1)) == 5 and len(e.zlist("hand", 1)) == 1      # 手札1枚は次のターンのドロー


def test_shield_saver_can_be_declined(rr):
    e = setup(rr, {"bz": ["T001"]}, {"bz": ["N005"]})
    answer(e, "attack", "attack:T001:player")
    answer(e, "choose_shields", "shield")
    answer(e, "choose_replacement", "decline")
    e.advance()
    assert len(e.zlist("shield", 1)) == 4 and len(e.zlist("hand", 1)) == 2      # ブレイクされた1枚とドロー
    assert top(e, 1, "N005") is not None


def test_escape_replaces_destruction_with_shield_to_hand(rr):
    """破壊される時、墓地に置くかわりにシールドを1つ手札に加える。クリーチャーはバトルゾーンに残る。"""
    e = setup(rr, {"bz": ["T004"]}, {"bz": ["N006"]})
    e.s.cards[top(e, 1, "N006")].tapped = True
    answer(e, "attack", "attack:T004:N006")
    answer(e, "choose_replacement", "replace:N006:0")
    answer(e, "choose_cards", "shield")
    e.advance()
    assert top(e, 1, "N006") is not None
    assert len(e.zlist("shield", 1)) == 4 and len(e.zlist("hand", 1)) == 2      # 加えた1枚とドロー


def test_escape_unavailable_without_shields(rr):
    e = setup(rr, {"bz": ["T004"]}, {"bz": ["N006"], "shield": []})
    e.s.cards[top(e, 1, "N006")].tapped = True
    answer(e, "attack", "attack:T004:N006")
    e.advance()
    assert not any(e.s.cards[c].defn == "N006" for c in e.bz_tops(1))



def test_modal_choose_one_runs_only_chosen_mode(tmp_path):
    """「次のうちいずれか1つを選ぶ」: 選んだモードだけを解決する。"""
    import yaml
    from dmsim.defs import DATA, load_rules
    f = tmp_path / "m.yaml"
    f.write_text(yaml.safe_dump({"cards": [{"id": "M001", "name": "選択呪文", "types": ["spell"], "civs": ["nature"], "cost": 1, "text": "x",
                 "spell": [{"op": "modal", "modes": [[{"op": "draw", "count": 1}], [{"op": "draw", "count": 3}]]}]}]}, allow_unicode=True))
    rr = load_rules(sorted((DATA / "cards").glob("*.yaml")) + [f])
    e = setup(rr, {"hand": ["M001"], "mana": ["T001"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:M001")
    answer(e, "choose_mode", "mode:1")
    e.advance()
    assert len(e.zlist("hand", 0)) == 3          # 呪文を使って0枚 → モード2で3枚引く（もう一方のモードは解決しない）


def test_modal_repeat_allows_same_mode_twice(tmp_path):
    import yaml
    from dmsim.defs import DATA, load_rules
    f = tmp_path / "m.yaml"
    f.write_text(yaml.safe_dump({"cards": [{"id": "M002", "name": "二回選ぶ呪文", "types": ["spell"], "civs": ["nature"], "cost": 1, "text": "x",
                 "spell": [{"op": "modal", "count": 2, "repeat": True, "modes": [[{"op": "draw", "count": 1}], [{"op": "mark", "name": "b"}]]}]}]}, allow_unicode=True))
    rr = load_rules(sorted((DATA / "cards").glob("*.yaml")) + [f])
    e = setup(rr, {"hand": ["M002"], "mana": ["T001"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:M002")
    answer(e, "choose_mode", "mode:0")
    answer(e, "choose_mode", "mode:0")
    e.advance()
    assert len(e.zlist("hand", 0)) == 2          # 同じモードを2回選んで2枚引く
