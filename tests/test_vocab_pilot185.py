"""語彙パイロット第185弾（2026-11-12）の検証: break_bonus（ブレイク・ボーナス）。

- h_break が攻撃番号で区切ったカウンタ broke_count:<cid>:atk<ano> を刻む
  （その攻撃中にそのクリーチャーがブレイクした枚数）。
- 新しい式 {turn_count: {kind: broke_by_self_attack}} がその枚数を読む
  （ターン通しの broke_by_self ではない。効果でブレイクした分は数えない）。
- カードの型: attack_end（broke: true）の誘発＋ repeat {times: broke_by_self_attack}
  ＋ 1回ごとに op may（「１回使ってもよい」）。場に残っていることは
  _collect_triggers の発生源＝バトルゾーンのカードで自動的に保証される。
- 判別: 効果ブレイク分を数えると T440 試験が失敗する（3枚引く）。
  broke ガードを外すとブロック試験が失敗する。場に残る条件を外すと
  S・トリガー試験が失敗する（T436 が破壊されてもミルする）。
"""
from conftest import setup

import yaml
from pathlib import Path

from dmsim.defs import load_tables, parse_card


def _keys(d):
    return [o["key"] for o in d["options"]]


def _drive(e, attacker=None, play=None, block="no_block", declare=None,
           say_yes=True, stop=None, max_steps=400):
    """局面を進める。attacker: p0 がそのキーで攻撃する。play: p0 が手札から
    そのカードを出す（1回）。block: ブロック決定の答え方。declare: p1 が
    宣言する S・トリガーの defn 部分文字列。say_yes=False なら p0 の
    yes_no はすべて no（任意性の辞退）。stop(e) が真になったら止まる。"""
    played = False
    for _ in range(max_steps):
        if stop is not None and stop(e):
            return True
        d = e.advance()
        if d is None:
            return True
        keys = _keys(d)
        if d["kind"] == "attack" and d["player"] == 0 and attacker and attacker in keys:
            e.answer([keys.index(attacker)])
        elif d["kind"] == "main" and d["player"] == 0 and play and not played \
                and f"play:{play}" in keys:
            played = True
            e.answer([keys.index(f"play:{play}")])
        elif d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "block":
            if block == "block":
                idx = next(i for i, k in enumerate(keys) if k != "no_block")
                e.answer([idx])
            else:
                e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "declare_strigger":
            if declare and d["player"] == 1:
                hit = [i for i, k in enumerate(keys) if declare in k]
                e.answer(hit[:1])
            else:
                e.answer([])
        elif d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            want = "yes" if (say_yes and d["player"] == 0) else "no"
            e.answer([keys.index(want)])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return False


def _bz(e, player, defn):
    return next(c for c in e.bz_tops(player) if e.s.cards[c].defn == defn)


def test_parse_proto_cards(rules):
    tables = load_tables()
    data = yaml.safe_load(
        (Path(__file__).parent.parent / "data" / "cards" / "proto.yaml")
        .read_text(encoding="utf-8"))
    cards = {c["id"]: c for c in data["cards"]}
    for defn in ("T436", "T437", "T438", "T439", "T440"):
        assert parse_card(cards[defn], tables).id == defn


def test_break_bonus_mills_twice_for_w_breaker(rules):
    # T436（W・ブレイカー）が2枚ブレイク → ミル4を2回＝8枚。
    e = setup(rules, {"bz": ["T436"]}, {"shield": ["T001", "T001"]})
    t436 = _bz(e, 0, "T436")
    done = _drive(e, attacker="attack:T436:player",
                  stop=lambda e: len(e.zlist("graveyard", 1)) >= 8)
    assert done
    assert len(e.zlist("graveyard", 1)) == 8
    assert e.s.cards[t436].zone == "bz"


def test_break_bonus_mills_once_for_single_break(rules):
    # シールド1枚だけならミル4を1回。
    e = setup(rules, {"bz": ["T436"]}, {"shield": ["T001"]})
    done = _drive(e, attacker="attack:T436:player",
                  stop=lambda e: len(e.zlist("graveyard", 1)) >= 4)
    assert done
    assert len(e.zlist("graveyard", 1)) == 4


def test_break_bonus_destroys_twice(rules):
    # T437（W・ブレイカー）が2枚ブレイク → パワー7000以下破壊を2回。
    e = setup(rules, {"bz": ["T437"]},
              {"bz": ["T004", "T004"], "shield": ["T001", "T001"]})
    # bz_tops は同名2体を両方返すので直接数える
    foes = [c for c in e.bz_tops(1) if e.s.cards[c].defn == "T004"]
    assert len(foes) == 2
    done = _drive(e, attacker="attack:T437:player",
                  stop=lambda e: all(e.s.cards[c].zone == "graveyard" for c in foes))
    assert done
    assert all(e.s.cards[c].zone == "graveyard" for c in foes)


def test_break_bonus_discards_thrice(rules):
    # T438（T・ブレイカー）が3枚ブレイク → ランダム捨てを3回。
    e = setup(rules, {"bz": ["T438"]},
              {"hand": ["T001", "T001", "T001", "T001"],
               "shield": ["T001", "T001", "T001"]})
    assert len(e.zlist("hand", 1)) == 4
    done = _drive(e, attacker="attack:T438:player",
                  stop=lambda e: len(e.zlist("graveyard", 1)) >= 3)
    assert done
    # 手札: 4枚＋ブレイク3枚−捨て3枚＋ターン2のドロー1枚＝5枚。墓地: 捨てた3枚。
    assert len(e.zlist("hand", 1)) == 5
    assert len(e.zlist("graveyard", 1)) == 3


def test_break_bonus_mana_twice(rules):
    # T439（W・ブレイカー）が2枚ブレイク → マナ2枚を2回＝4枚。
    e = setup(rules, {"bz": ["T439"]}, {"shield": ["T001", "T001"]})
    done = _drive(e, attacker="attack:T439:player",
                  stop=lambda e: len(e.zlist("mana", 0)) >= 4)
    assert done
    assert len(e.zlist("mana", 0)) == 4


def test_no_bonus_when_blocked(rules):
    # ブロックされるとブレイク無し → 誘発しない（broke ガード）。
    # ターンが進むまで回してから、ミルが起きていないことを確認する。
    # 墓地の1枚はバトルで破壊されたブロッカー（T004）で、ミルではない。
    e = setup(rules, {"bz": ["T436"]},
              {"bz": ["T004"], "shield": ["T001", "T001"]})
    done = _drive(e, attacker="attack:T436:player", block="block",
                  stop=lambda e: e.s.turn >= 2)
    assert done
    assert len(e.zlist("shield", 1)) == 2
    grave = e.zlist("graveyard", 1)
    assert len(grave) == 1
    assert e.s.cards[grave[0]].defn == "T004"


def test_no_bonus_when_destroyed_by_s_trigger(rules):
    # 2枚ブレイクするが、S・トリガー（T006）で攻撃の終わりまでに破壊される
    # → 場に無いので誘発しない。ターンが進むまで回してから確認する。
    e = setup(rules, {"bz": ["T436"]}, {"shield": ["T006", "T003"]})
    t436 = _bz(e, 0, "T436")
    done = _drive(e, attacker="attack:T436:player", declare="T006",
                  stop=lambda e: e.s.turn >= 2)
    assert done
    assert e.s.cards[t436].zone == "graveyard"
    # 墓地の1枚は使い終わった S・トリガー（T006）で、ミルではない。
    grave = e.zlist("graveyard", 1)
    assert len(grave) == 1
    assert e.s.cards[grave[0]].defn == "T006"
    assert len(e.zlist("hand", 1)) == 2            # ブレイクした2枚が手札へ（ターン2のドローはまだ）


def test_effect_break_not_counted(rules):
    # T440: CIP で効果ブレイク1枚（攻撃外）→ 攻撃で2枚ブレイク。
    # ボーナスは攻撃中の2枚分だけ＝2ドロー（ターン通しなら3ドローになる）。
    e = setup(rules, {"hand": ["T440"],
                      "mana": ["T003", "T003", "T003", "T003"]},
              {"shield": ["T001", "T001", "T001", "T001", "T001"]})
    hand0 = len(e.zlist("hand", 0))
    done = _drive(e, attacker="attack:T440:player", play="T440",
                  stop=lambda e: e.s.turn >= 2)
    assert done
    # 先攻1ターン目はドローなし。手札: T440を出して-1、ボーナス2ドロー＝ hand0 + 1
    assert len(e.zlist("hand", 0)) == hand0 + 1


def test_may_decline_skips_bonus(rules):
    # may をすべて辞退 → ミル無し（任意性）。ターンが進むまで回す。
    e = setup(rules, {"bz": ["T436"]}, {"shield": ["T001", "T001"]})
    done = _drive(e, attacker="attack:T436:player", say_yes=False,
                  stop=lambda e: e.s.turn >= 2)
    assert done
    assert len(e.zlist("graveyard", 1)) == 0
