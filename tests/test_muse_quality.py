"""Muse変換カードの品質リスク修正（レンティア・天動の化身・ステルス・ミハイル）。
カードは converted.yaml の実データをそのまま使う（テスト用の複製は持たない）。
総合ルール: 701.13（バトル）、400.7（同時の移動）、614（置換効果）。"""
import sys
from pathlib import Path

import pytest
import yaml
from conftest import answer, setup

from dmsim.defs import DATA, card_yaml_files, load_rules

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import rule_convert  # noqa: E402

RENTIA, TENDO, MIHAIL, STEALTH = "dm14-072", "dm10-007", "dm09-006", "dm07-012"


@pytest.fixture(scope="module")
def rr(tmp_path_factory):
    allc = yaml.safe_load((DATA / "cards" / "converted.yaml").read_text(encoding="utf-8"))["cards"]
    pick = [c for c in allc if c["id"] in (RENTIA, TENDO, MIHAIL, STEALTH)]
    assert len(pick) == 4
    f = tmp_path_factory.mktemp("q") / "q.yaml"
    f.write_text(yaml.safe_dump({"cards": pick}, allow_unicode=True), encoding="utf-8")
    return load_rules(card_yaml_files() + [f])


def bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def names(e, z, p):
    return sorted(e.s.cards[c].defn for c in e.zlist(z, p))


# ---- 宣凶師レンティア: 「ブロック中」だけ+3000 ----

def test_rentia_gets_power_only_while_blocking(rr):
    """ブロックして T005(3000) とバトル: 2500+3000=5500 で勝つ。ブロックが終わればパワーは元に戻る
    （以前はブロック時の誘発でターン終了まで5500のままだった）。"""
    e = setup(rr, {"bz": ["T005"]}, {"bz": [RENTIA]})
    answer(e, "attack", "attack:T005:player")
    answer(e, "block", f"bz:{RENTIA}:0")
    e.advance()
    assert RENTIA in names(e, "bz", 1) and "T005" in names(e, "graveyard", 0)
    assert e.chars(bz(e, 1, RENTIA))["power"] == 2500


def test_rentia_gets_no_bonus_when_attacked(rr):
    """攻撃されてバトル（ブロックではない）なら+3000は付かず、3000に負ける。"""
    e = setup(rr, {"bz": ["T005"]}, {"bz": [RENTIA]})
    e.s.cards[bz(e, 1, RENTIA)].tapped = True
    answer(e, "attack", f"attack:T005:{RENTIA}")
    e.advance()
    assert RENTIA not in names(e, "bz", 1)


def test_rentia_gets_no_bonus_when_attacking(rr):
    """自分が攻撃するバトルでも+3000は付かない。"""
    e = setup(rr, {"bz": [RENTIA]}, {"bz": ["T005"]})
    e.s.cards[bz(e, 1, "T005")].tapped = True
    answer(e, "attack", f"attack:{RENTIA}:T005")
    e.advance()
    assert RENTIA not in names(e, "bz", 0)


def test_battle_power_only_must_be_known(rr):
    from dmsim.defs import DefError
    bad = {"id": "Q001", "name": "x", "types": ["creature"], "civs": ["fire"], "cost": 1, "power": 1000, "races": ["テスト"],
           "abilities": [{"kind": "static", "affects": "self", "mod": {"battle_power": {"amount": 1, "only": "defending"}}}]}
    f = Path(__file__).parent / "_q_bad.yaml"
    f.write_text(yaml.safe_dump({"cards": [bad]}, allow_unicode=True), encoding="utf-8")
    try:
        with pytest.raises(DefError):
            load_rules([f])
    finally:
        f.unlink()


# ---- 天動の化身: 手札とマナを同時に入れ替える ----

def test_tendo_swaps_hand_and_mana(rr):
    """元のマナは全部手札へ、元の手札（化身の他）は全部タップしてマナへ。"""
    mana = ["T001", "T001", "T004", "T004", "T005", "T005"]
    e = setup(rr, {"hand": [TENDO, "T002"], "mana": mana})
    answer(e, "charge", "pass")
    answer(e, "main", f"play:{TENDO}")
    e.advance()
    assert TENDO in names(e, "bz", 0)
    assert names(e, "hand", 0) == sorted(mana)
    assert names(e, "mana", 0) == ["T002"]
    assert all(e.s.cards[c].tapped for c in e.zlist("mana", 0))


def test_tendo_moves_in_one_batch(rr):
    """together は1つのイベントの束で動かす。化身の定義は together（移動2つ）で、手札→マナは tapped。"""
    op = next(a for a in rr.cards[TENDO].abilities if a["kind"] == "trigger")["effect"][0]
    assert op["op"] == "together" and [m["to"] for m in op["body"]] == ["hand", "mana"]
    assert op["body"][1]["tapped"] is True


def test_together_rejects_choice_targets(rr):
    e = setup(rr, {"hand": ["T001"]})
    bad = [{"op": "together", "body": [{"op": "move", "select": {"zone": "hand", "owner": "you", "count": 1}, "to": "mana", "reason": "put"}]}]
    run_ops(e, bad)
    with pytest.raises(ValueError):
        e.advance()


# ---- ステルス: キーワードとして keyword_patterns に定義 ----

CIVS = (("light", "光"), ("water", "水"), ("darkness", "闇"), ("fire", "火"), ("nature", "自然"))


def stealth_text(ja):
    return f"{ja}ステルス(相手のマナゾーンに{ja}のカードが１枚でもあれば、このクリーチャーはブロックされない)"


def test_stealth_patterns_for_each_civ():
    for civ, ja in CIVS:
        a = rule_convert.match_pattern(stealth_text(ja))
        assert a == [{"kind": "static", "affects": "self",
                      "if": {"exists": {"zone": "mana", "owner": "opp", "filter": {"civs": [civ]}}},
                      "mod": {"deny": ["be_blocked"]}}]


def test_registered_stealth_cards_equal_pattern_output():
    cards = yaml.safe_load((DATA / "cards" / "converted.yaml").read_text(encoding="utf-8"))["cards"]
    n = 0
    for c in cards:
        for _, ja in CIVS:
            if f"{ja}ステルス(" in c.get("text", ""):
                assert rule_convert.match_pattern(stealth_text(ja)) == [a for a in c["abilities"] if a.get("kind") == "static" and "if" in a], c["id"]
                n += 1
    assert n >= 7


def test_stealth_cannot_be_blocked_only_with_light_in_opp_mana(rr):
    e = setup(rr, {"bz": [STEALTH]}, {"bz": ["T004"], "mana": [RENTIA]})        # 相手マナに光 → ブロックできない
    d = e.advance()
    assert d["kind"] == "attack"
    e.answer([[o["key"] for o in d["options"]].index(f"attack:{STEALTH}:player")])
    d = e.advance()
    assert d is None or d["kind"] != "block"
    e = setup(rr, {"bz": [STEALTH]}, {"bz": ["T004"], "mana": ["T005"]})        # 相手マナに光なし → ブロックできる
    answer(e, "attack", f"attack:{STEALTH}:player")
    answer(e, "block", "bz:T004:0")


# ---- ミハイル: 置換が無限ループにならない ----

def run_ops(e, ops, you=0):
    e.s.tasks.append(e._child(ops, {"you": you, "self": None, "vars": {}}))


def test_mihail_keeps_losing_creature_in_bz(rr):
    """バトルに負けた他のクリーチャーは墓地に行かずに残る。"""
    e = setup(rr, {"bz": [MIHAIL, "T001"]}, {"bz": ["T004"]})
    e.s.cards[bz(e, 1, "T004")].tapped = True
    answer(e, "attack", "attack:T001:T004")
    e.advance()
    assert "T001" in names(e, "bz", 0) and "T001" not in names(e, "graveyard", 0)


def test_mihail_does_not_loop_on_zero_power(rr):
    """パワー0以下の状況起因処理（破壊）が置換で止まっても、同じ処理を無限に繰り返さない。"""
    e = setup(rr, {"bz": [MIHAIL, "T001"]})
    run_ops(e, [{"op": "modify", "select": {"zone": "bz", "owner": "you", "filter": {"name_has": "試験用"}}, "mod": {"power": -2000}, "duration": "end_of_turn"}])
    d = e.advance()                      # 例外・無限ループにならず、次の決定まで進む
    assert d is not None
    assert "T001" in names(e, "bz", 0)


def test_mihail_itself_goes_to_graveyard(rr):
    """「他の」クリーチャーだけが対象。ミハイル自身は墓地へ置かれる。"""
    e = setup(rr, {"bz": [MIHAIL]})
    e._raw_move(bz(e, 0, MIHAIL), "graveyard")
    assert MIHAIL in names(e, "graveyard", 0)


def test_mihail_leaving_lets_zero_power_creature_die(rr):
    """止められていた破壊は、状態が動いたら（ミハイルが離れたら）やり直される。"""
    e = setup(rr, {"bz": [MIHAIL, "T001"]})
    run_ops(e, [
        {"op": "modify", "select": {"zone": "bz", "owner": "you", "filter": {"name_has": "試験用"}}, "mod": {"power": -2000}, "duration": "end_of_turn"},
        {"op": "move", "select": {"zone": "bz", "owner": "you", "filter": {"name_has": "ミハイル"}}, "to": "graveyard", "reason": "destroy"},
    ])
    e.advance()
    assert names(e, "graveyard", 0) == sorted([MIHAIL, "T001"]) and not names(e, "bz", 0)
