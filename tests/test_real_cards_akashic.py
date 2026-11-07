"""アカシック系デッキの部品（data/cards/real_akashic.yaml）の動作確認。"""
from conftest import answer, setup

NATURE = "dm06-110"
FIONA = "dm24rp3-tr06"
FIELD = "T069"
MATE = "dm23-035"        # ドリームメイト
HD2 = "dmrp07-009"


def names(e, z, p):
    return sorted(e.s.cards[c].defn for c in e.zlist(z, p))


def bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def test_fiona_cip_puts_field_from_mana(rules):
    e = setup(rules, {"hand": [FIONA], "mana": [NATURE] * 7 + [FIELD]})
    answer(e, "charge", "pass")
    answer(e, "main", f"play:{FIONA}")
    for _ in range(10):
        d = e.advance()
        if d and d["kind"] in ("main", "attack"):
            break
        e.answer([0])
    assert FIELD in names(e, "bz", 0) and FIELD not in names(e, "mana", 0)


def test_fiona_protects_other_dreammates_from_opponent_choice(rules):
    e = setup(rules, {"bz": [FIONA, MATE]})
    assert not e.permits(bz(e, 0, MATE), "be_chosen")      # 自分の他のドリームメイトは選ばれない
    assert e.permits(bz(e, 0, FIONA), "be_chosen")         # 自身は対象外（「他の」）


def test_fiona_no_protection_without_her(rules):
    e = setup(rules, {"bz": [MATE]})
    assert e.permits(bz(e, 0, MATE), "be_chosen")


def _hd2(rules, mode):
    e = setup(rules, {"hand": [HD2], "mana": [NATURE] * 5}, deck_size=20)
    answer(e, "charge", "pass")
    answer(e, "main", f"play:{HD2}:1")
    answer(e, "choose_mode", f"mode:{mode}")
    e.advance()
    return e


def test_hd2_chosen_player_self(rules):
    e = _hd2(rules, 0)
    assert len(e.zlist("mana", 0)) == 7 and len(e.zlist("mana", 1)) == 0   # 山札の上2枚が自分のマナへ


def test_hd2_chosen_player_opponent(rules):
    e = _hd2(rules, 1)
    assert len(e.zlist("mana", 0)) == 5 and len(e.zlist("mana", 1)) == 2   # 相手の山札の上2枚が相手のマナへ
