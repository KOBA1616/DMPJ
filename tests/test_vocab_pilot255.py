"""第255弾: breaks_scaling イディオム（破壊した数だけパワーとブレイク数が増える）。"""
from tests.conftest import setup
from dmsim.cards.defs import load_rules


def test_destroy_two_gains_power_and_breaks():
    e = setup(load_rules(), {"bz": ["T691", "T001", "T002"]}, {"bz": ["T003"]})
    sh1 = len(e.zlist("shield", 1))
    state = {"destroyed": 0, "broke": 0}
    for _ in range(500):
        state["destroyed"] = len([c for c in e.zlist("graveyard", 0)
                                  if e.s.cards[c].defn in ("T001", "T002")])
        if state["destroyed"] == 2 and len(e.zlist("shield", 1)) <= sh1 - 3:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_cards" and d.get("player") == 0:
            # 破壊選択: 自分自身（T691）ではなく T001 と T002 を選ぶ
            pick = [i for i, o in enumerate(d["options"])
                    if e.s.cards[o["cid"]].defn in ("T001", "T002")]
            e.answer(pick if pick else list(range(d.get("min", 0))))
        elif d["kind"] == "choose_breaker":
            e.answer([len(keys) - 1])   # 最大のブレイク数を選ぶ
        else:
            a = next((i for i, k in enumerate(keys) if k.startswith("attack:") and k.endswith(":player")), None)
            if a is not None:
                e.answer([a])
            elif d["kind"] == "yes_no":
                e.answer([0])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
    assert state["destroyed"] == 2
    assert len(e.zlist("shield", 1)) <= sh1 - 3   # 通常1 + 破壊した2体分 = 3枚ブレイク
