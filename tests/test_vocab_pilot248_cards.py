"""第248弾の登録形: dmr04-003 無限王ハカイ・デストロイヤー（ラウンド282）。"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build


def test_registered_intercept():
    rules = load_rules()
    assert "dmr04-003" in rules.cards
    e = build(rules, {"p0": {"bz": ["dmr04-003"]},
                      "p1": {"shield": ["T672", "T001", "T001"]},
                      "filler": "T001", "seed": 1, "deck_size": 20})
    sp = next(c for c in e.zlist("shield", 1) if e.s.cards[c].defn == "T672")
    hand0 = len(e.zlist("hand", 0))
    for _ in range(300):
        if sp in e.zlist("graveyard", 1):
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        atk = next((i for i, k in enumerate(keys) if k.startswith("attack:")), None)
        if atk is not None:
            e.answer([atk])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert sp in e.zlist("graveyard", 1)                 # シールドの呪文は持ち主の墓地へ
    assert len(e.zlist("hand", 0)) == hand0 + 2          # 唱えた P0 が2枚引く
    assert sp not in e.zlist("hand", 1)
