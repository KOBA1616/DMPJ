"""語彙パイロット第184弾（2026-11-12）の検証: cast_spell_side_from_battle_zone。

- op cast_face に select を追加: 選んだツインパクト・クリーチャーの呪文面を、
  そのカードをバトルゾーンに置いたままコストを支払わずに唱える。
  select が無い時は従来どおり自分自身。face の既定は -1（呪文面を探す）。
- フィルタに spell_cost_le / spell_cost_ge を追加: ツインパクトの呪文側の
  コストで絞る（dm25ex4-063型「呪文側のコストが自分のマナの枚数以下なら」）。
  値は式を書ける（{count: {zone: mana, owner: you}}）。
- 判別: T432 はツインパクトではない（自分の呪文面を持たない）ため、select が
  効いていなければ試験1はドローせず失敗する。T433 の event.subject 形は
  攻撃者自身の呪文面を唱えることを検証する。
"""
from conftest import setup


def _keys(d):
    return [o["key"] for o in d["options"]]


def _drive(e, attacker=None, play_spell=None, stop=None, max_steps=200):
    """局面を進める。attacker: p0 がそのキーで攻撃する。play_spell: p1 が
    手札からその呪文を唱える（回数分）。yes_no は p0 なら yes、p1 なら no。
    choose_cards は T430 を含む選択肢があればそれを、無ければ先頭 min 枚を選ぶ。
    stop(e) が真になったらそこで止める（終局まで回すとターンのドローで手札が増えるため）。
    戻り値: (止まったか, choose_cards が出た回数, 唱えた呪文の回数)。"""
    choose_cards_seen = 0
    spells_played = 0
    last_d = None
    for _ in range(max_steps):
        if stop is not None and stop(e, spells_played, choose_cards_seen, last_d):
            return True, choose_cards_seen, spells_played
        d = e.advance()
        if d is None:
            return True, choose_cards_seen, spells_played
        last_d = d
        keys = _keys(d)
        if d["kind"] == "attack" and d["player"] == 0 and attacker and attacker in keys:
            e.answer([keys.index(attacker)])
        elif d["kind"] == "main" and d["player"] == 1 and play_spell \
                and spells_played < play_spell[1] and f"play:{play_spell[0]}" in keys:
            spells_played += 1
            e.answer([keys.index(f"play:{play_spell[0]}")])
        elif d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_cards":
            choose_cards_seen += 1
            hit = [i for i, k in enumerate(keys) if "T430" in k]
            e.answer([hit[0]] if hit else list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("yes" if d["player"] == 0 else "no")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return False, choose_cards_seen, spells_played


def _bz(e, player, defn):
    return next(c for c in e.bz_tops(player) if e.s.cards[c].defn == defn)


def test_select_casts_other_twinpact_spell_face(rules):
    # T432（ツインパクトではない）が攻撃し、T430 と T431 から T430 を選んで唱える。
    e = setup(rules, {"bz": ["T432", "T430", "T431"], "hand": []}, {"shield": ["T003"]})
    hand0 = len(e.zlist("hand", 0))
    t430 = _bz(e, 0, "T430")
    done, seen, _ = _drive(e, attacker="attack:T432:player",
                           stop=lambda e, p, s, d: len(e.zlist("hand", 0)) == hand0 + 1)
    assert done
    assert seen >= 1                                        # 2候補の選択が出た
    assert len(e.zlist("hand", 0)) == hand0 + 1             # T430 の呪文面（1ドロー）が解決した
    assert e.s.cards[t430].zone == "bz"                     # T430 はバトルゾーンに残る
    assert e.s.cards[_bz(e, 0, "T431")].zone == "bz"        # 選ばれなかった T431 も残る


def test_single_candidate_casts_without_prompt(rules):
    # 候補が1体だけなら選択は出ず、自動でその呪文面を唱える。
    e = setup(rules, {"bz": ["T432", "T430"], "hand": []}, {"shield": ["T003"]})
    hand0 = len(e.zlist("hand", 0))
    t430 = _bz(e, 0, "T430")
    done, seen, _ = _drive(e, attacker="attack:T432:player",
                           stop=lambda e, p, s, d: len(e.zlist("hand", 0)) == hand0 + 1)
    assert done
    assert seen == 0                                        # 選択は出ない
    assert len(e.zlist("hand", 0)) == hand0 + 1
    assert e.s.cards[t430].zone == "bz"


def test_event_subject_casts_attacking_twinpact_spell_face(rules):
    # T433: 自分のツインパクトクリーチャーが攻撃する時、そのクリーチャーの呪文側を唱える。
    e = setup(rules, {"bz": ["T433", "T430"], "hand": []}, {"shield": ["T003"]})
    hand0 = len(e.zlist("hand", 0))
    t430 = _bz(e, 0, "T430")
    done, _, _ = _drive(e, attacker="attack:T430:player",
                        stop=lambda e, p, s, d: len(e.zlist("hand", 0)) == hand0 + 1)
    assert done
    assert len(e.zlist("hand", 0)) == hand0 + 1             # 攻撃者 T430 自身の呪文面が唱えられた
    assert e.s.cards[t430].zone == "bz"


def test_spell_cost_filter_limits_targets(rules):
    # マナ2枚: 呪文面コスト2の T430 だけが候補（コスト4の T431 は対象外）。
    e = setup(rules, {"bz": ["T434", "T430", "T431"], "mana": ["T001", "T001"], "hand": []},
              {"shield": ["T003"]})
    hand0 = len(e.zlist("hand", 0))
    t430 = _bz(e, 0, "T430")
    done, seen, _ = _drive(e, attacker="attack:T434:player",
                           stop=lambda e, p, s, d: len(e.zlist("hand", 0)) == hand0 + 1)
    assert done
    assert seen == 0                                        # 候補は T430 1体だけなので選択は出ない
    assert len(e.zlist("hand", 0)) == hand0 + 1
    assert e.s.cards[t430].zone == "bz"
    # マナ1枚: どちらも対象外。唱えられず、クラッシュもしない。
    e = setup(rules, {"bz": ["T434", "T430", "T431"], "mana": ["T001"], "hand": []},
              {"shield": ["T003"]})
    hand0 = len(e.zlist("hand", 0))
    done, _, _ = _drive(e, attacker="attack:T434:player",
                        stop=lambda e, p, s, d: d is not None and d["player"] == 1)
    assert done
    assert len(e.zlist("hand", 0)) == hand0


def test_opp_cast_triggers_once_per_turn(rules):
    # T435: 各ターンに1度、相手が呪文を唱えた時、自分のツインパクトの呪文側を唱える。
    e = setup(rules, {"bz": ["T435", "T430"], "hand": []},
              {"hand": ["T003", "T003"], "mana": ["T003", "T003", "T003", "T003"]})
    hand0 = len(e.zlist("hand", 0))
    t430 = _bz(e, 0, "T430")
    done, _, played = _drive(
        e, play_spell=("T003", 2),
        stop=lambda e, p, s, d: p == 2 and d is not None
        and d["kind"] == "main" and d["player"] == 1)
    assert done
    assert played == 2                                       # 相手は呪文を2回唱えた
    assert len(e.zlist("hand", 0)) == hand0 + 1              # T430 の呪文面は1回だけ唱えられた
    assert e.s.cards[t430].zone == "bz"


def test_no_twinpact_no_cast(rules):
    # ツインパクトが場に無ければ何も起きず、クラッシュもしない。
    e = setup(rules, {"bz": ["T432", "T001"], "hand": []}, {"shield": ["T003"]})
    hand0 = len(e.zlist("hand", 0))
    done, _, _ = _drive(e, attacker="attack:T432:player",
                        stop=lambda e, p, s, d: d is not None and d["player"] == 1)
    assert done
    assert len(e.zlist("hand", 0)) == hand0
