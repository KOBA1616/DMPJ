"""第260弾: mana_all_civs（支払い時だけマナを全文明として扱う）。"""
from tests.conftest import setup
from dmsim.cards.defs import load_rules


def _drive(e, limit=120):
    """play 選択肢を拾いながら進め、(T699 が場に出たか, play:T699 が提示されたか) を返す。"""
    offered = False
    for _ in range(limit):
        if any(e.s.cards[c].defn == "T699" for c in e.zlist("bz", 0)):
            return True, True
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if any(k.startswith("play:T699") for k in keys):
            offered = True
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T699"))])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return any(e.s.cards[c].defn == "T699" for c in e.zlist("bz", 0)), offered


def test_global_grant_makes_two_civ_summon_payable():
    # 水マナ2枚しかないのに、付与獣がいれば光/火の T699 を召喚できる
    e = setup(load_rules(), {"bz": ["T698"], "hand": ["T699"], "mana": ["T010", "T010"]}, {})
    entered, offered = _drive(e)
    assert offered and entered


def test_without_grant_not_payable():
    e = setup(load_rules(), {"hand": ["T699"], "mana": ["T010", "T010"]}, {})
    entered, offered = _drive(e, limit=12)
    assert not offered and not entered


def test_self_grant_in_mana():
    # マナゾーンの T700 自身が全文明扱い（光として数え、火マナと合わせて払える）
    e = setup(load_rules(), {"hand": ["T699"], "mana": ["T700", "T034"]}, {})
    entered, offered = _drive(e)
    assert offered and entered
