"""ラウンド278 登録形: dm23ex3-or2 終極宣言の無トリガー召喚（第243弾）。"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build


def test_or2_final_declaration():
    e = build(load_rules(), {"p0": {"bz": ["dm23ex3-or2"], "graveyard": ["T660"], "hand": ["T001"]},
                             "p1": {"bz": ["T002"]}, "filler": "T001", "seed": 1, "deck_size": 20})
    t660 = next(c for c in e.zlist("graveyard", 0) if e.s.cards[c].defn == "T660")
    h0 = len(e.zlist("hand", 0))
    attack_keys = []
    for _ in range(200):
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "yes_no":
            e.answer([0])
        elif d["kind"] == "choose_cards" and keys:
            e.answer([0])
        elif d["kind"] == "attack":
            attack_keys = keys
            break
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert t660 in e.zlist("bz", 0)                    # 召喚された
    assert len(e.zlist("hand", 0)) == h0               # 出た時ドローはトリガーしない
    assert "attack:T660:player" in attack_keys         # そのターン、プレイヤーを攻撃できる
    assert not any(k.startswith("attack:T660:T002") for k in attack_keys)
