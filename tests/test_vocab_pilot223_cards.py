"""ラウンド259: 第223弾 power_gachinko_judge の登録形テスト。

対象6件（dm26rp2-004 / 009 / 016 / 020 / 030 / 042）。scenario の deck
指定は逆順に積まれる（指定リストの最後が山札の上）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine import scenario  # noqa: E402

IDS = ("dm26rp2-004", "dm26rp2-009", "dm26rp2-016",
       "dm26rp2-020", "dm26rp2-030", "dm26rp2-042")


def _rules():
    return load_rules()


def _game(p0, p1=None):
    return scenario.build(_rules(), {"p0": p0, "p1": p1 or {},
                                     "filler": "T001", "seed": 1, "deck_size": 20})


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _bz(e, p):
    return [e.s.cards[c].defn for c in e.zlist("bz", p)
            if e.s.cards[c].controller == p and e.s.cards[c].top_of < 0]


def _drive(e, handler=None, turns=1, max_steps=600, stop_when=None):
    for _ in range(max_steps):
        if e.s.turn > turns:
            break
        d = e.advance()
        if d is None:
            break
        if e.s.turn > turns:
            break
        if stop_when is not None and stop_when(e, d):
            break
        if handler and handler(e, d):
            continue
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return e


def _handler(play=None, attack=None, yes_no=(), block=None):
    state = {"played": False, "attacked": False, "blocked": False, "yn": list(yes_no)}

    def h(e, d):
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "main" and play and not state["played"]:
            for i, k in enumerate(keys):
                if k.startswith("play:" + play):
                    state["played"] = True
                    e.answer([i])
                    return True
            return False
        if kind == "attack" and attack and not state["attacked"]:
            for i, k in enumerate(keys):
                if k == attack:
                    state["attacked"] = True
                    e.answer([i])
                    return True
            return False
        if kind == "block" and block and not state["blocked"]:
            for i, k in enumerate(keys):
                if block in k:
                    state["blocked"] = True
                    e.answer([i])
                    return True
            return False
        if kind == "yes_no":
            e.answer([state["yn"].pop(0) if state["yn"] else 0])
            return True
        if kind == "choose_cards":
            e.answer(list(range(d.get("min", 0))))
            return True
        return False

    return h


def test_all_six_registered():
    rules = _rules()
    for cid in IDS:
        assert cid in rules.cards, cid
    assert "double_breaker" in rules.cards["dm26rp2-009"].keywords
    assert "shield_go" in rules.cards["dm26rp2-042"].keywords
    assert "blocker" in rules.cards["dm26rp2-004"].keywords


def test_030_turn_start_judge_win_shieldizes():
    e = _game({"bz": ["dm26rp2-030"], "deck": ["T002", "T002", "T201"]},
              {"deck": ["T201", "T002", "T002"]})
    before = len(_defns(e, "shield", 0))
    _drive(e, _handler(yes_no=[0]))
    assert len(_defns(e, "shield", 0)) == before + 1   # 勝って山札上をシールド化


def test_020_turn_start_judge_win_mana_put_and_all_civs():
    e = _game({"bz": ["dm26rp2-020"], "deck": ["T002", "T002", "T201"]},
              {"deck": ["T201", "T002", "T002"]})
    _drive(e, _handler(yes_no=[0]))
    assert len(_defns(e, "mana", 0)) == 1              # 勝って山札上をマナへ
    cid = e.zlist("mana", 0)[0]
    assert set(e.chars(cid)["civs"]) >= {"light", "water", "fire", "darkness", "nature"}


def test_004_turn_start_judge_win_summon_and_self_bounce():
    e = _game({"bz": ["dm26rp2-004"], "deck": ["T002", "T002", "T201"]},
              {"deck": ["T201", "T002", "T002"]})
    _drive(e, _handler(yes_no=[0, 0]))                 # ジャッジする→召喚する
    assert "T201" in _bz(e, 0)                         # 見せたカードを召喚
    assert "dm26rp2-004" in _defns(e, "hand", 0)       # 自身は手札に戻る


def test_042_cip_judge_lose_self_destroys_and_shield_go():
    e = _game({"hand": ["dm26rp2-042"], "mana": ["T060"],
               "deck": ["T201", "T201", "T002"]},
              {"deck": ["T002", "T002", "T201"]})
    _drive(e, _handler(play="dm26rp2-042"))
    assert "dm26rp2-042" not in _bz(e, 0)              # 負けて破壊される
    assert "dm26rp2-042" in _defns(e, "shield", 0)     # SG: 墓地から表向きでシールド化
    assert "dm26rp2-042" not in _defns(e, "graveyard", 0)


def test_042_cip_judge_win_stays():
    e = _game({"hand": ["dm26rp2-042"], "mana": ["T060"],
               "deck": ["T002", "T002", "T201"]},
              {"deck": ["T201", "T201", "T002"]})
    _drive(e, _handler(play="dm26rp2-042"))
    assert "dm26rp2-042" in _bz(e, 0)


def test_016_cip_opponent_discards_three():
    e = _game({"hand": ["dm26rp2-016"], "mana": ["T050"] * 6},
              {"hand": ["T002", "T006", "T060", "T201"]})
    _drive(e, _handler(play="dm26rp2-016"))
    # 相手は手札4枚から3枚選んで捨てる（残り1枚＋次ターンのドローが手札に残る）
    assert sorted(_defns(e, "graveyard", 1)) == ["T002", "T006", "T060"]
    assert "T201" in _defns(e, "hand", 1)


def test_016_destroyed_judge_win_revives_tapped():
    # 山札の上数枚は同一カードで揃える（途中のドロー等でジャッジ結果が変わらないように）
    e = _game({"bz": ["dm26rp2-016"], "deck": ["T201"] * 6},
              {"bz": ["dm05-s01"], "deck": ["T002"] * 6})
    # 自分のターンに攻撃し、相手のブロッカー（パワー12000）にブロックされて破壊される。
    # 復帰した時点で止める（次の自分のターンのアンタップで tapped が消えるため）
    _drive(e, _handler(attack="attack:dm26rp2-016:player", block="dm05-s01",
                       yes_no=[0]), turns=3,
           stop_when=lambda e, d: "dm26rp2-016" in _bz(e, 0)
           and any(r["kind"] == "reveal" for r in e.s.pub))
    assert "dm26rp2-016" in _bz(e, 0)                  # 勝って墓地から復帰
    cid = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "dm26rp2-016")
    assert e.s.cards[cid].tapped is True               # タップして出る
