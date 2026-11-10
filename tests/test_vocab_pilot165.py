"""語彙パイロット第165弾: ura_ninja_strike（ウラ・ニンジャ・ストライク）。

新エンジン語彙は無し。通常のニンジャ・ストライク（declare 2本: 相手の攻撃時／
ブロック時、マナ枚数以上で無償召喚、ターン終わりに山札の下）の if に
「自分のマナに指定文明がある」を足したもの。指定が2文明（光/水）のものは
両方の exists を並べる。カード側は declare を明示で持ち、変換ツール側の
keyword_patterns.yaml にも ura_ninja_strike_<文明> の6パターンを足した。

検証は通常のニンジャ・ストライク（tests/test_mechanics.py の T019）と同じ流れで、
文明条件の有無だけを切り替える。
"""
from pathlib import Path

import yaml
from conftest import setup, answer

from dmsim.defs import DefError, load_tables, parse_card

TABLES = load_tables()


def names(e, z, p):
    return sorted(e.s.cards[c].defn for c in e.zlist(z, p))


def keys(d):
    return [o["key"] for o in d["options"]]


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    for cid in ("T308", "T309"):
        parse_card(_proto_card(cid), TABLES)
    t308 = parse_card(_proto_card("T308"), TABLES)
    decls = [a for a in t308.abilities if a["kind"] == "declare"]
    assert len(decls) == 2 and {a["when"]["event"] for a in decls} == {"attack", "block"}
    assert decls[0]["if"]["all"][1] == {"exists": {"zone": "mana", "owner": "you", "filter": {"civs": ["water"]}}}
    t309 = parse_card(_proto_card("T309"), TABLES)
    decls309 = [a for a in t309.abilities if a["kind"] == "declare"]
    assert len(decls309[0]["if"]["all"]) == 3   # 枚数＋光＋水


def test_invalid_civ_in_declare():
    card = {"id": "test-ura-bad", "name": "試験文明不良", "types": ["creature"],
            "civs": ["water"], "cost": 4, "power": 3000,
            "source": {"official": "test-ura-bad", "review": "pending"},
            "abilities": [{"kind": "declare", "zone": "hand",
                           "when": {"event": "attack", "subject": {"owner": "opp"}},
                           "if": {"exists": {"zone": "mana", "owner": "you", "filter": {"civs": ["plasma"]}}},
                           "effect": [{"op": "play_free", "select": {"ref": "self"}}]}]}
    try:
        parse_card(card, TABLES)
        raise AssertionError("should have raised")
    except DefError:
        pass


def test_ura_declare_with_civ(rules):
    """マナ3枚に水を含む → 宣言でき、召喚してブロックでき、ターンの終わりに山札の下へ。"""
    e = setup(rules, {"bz": ["T005"]}, {"hand": ["T308"], "mana": ["T063", "T001", "T001"]})
    answer(e, "attack", "attack:T005:player")
    d = e.advance()
    assert d["kind"] == "declare_attack" and d["player"] == 1
    assert any(k.startswith("declare:T308:") for k in keys(d))
    e.answer([next(i for i, k in enumerate(keys(d)) if k.startswith("declare:T308:"))])
    d = e.advance()
    assert d["kind"] == "block" and "bz:T308:0" in keys(d)
    e.answer([keys(d).index("bz:T308:0")])
    d = e.advance()                          # バトル（4000 > 3000）→ ターンの終わり → 相手のターンへ
    assert d["player"] == 1 and names(e, "graveyard", 0) == ["T005"]
    assert names(e, "bz", 1) == [] and e.s.cards[e.zlist("deck", 1)[-1]].defn == "T308"


def test_ura_declare_blocked_without_civ(rules):
    """マナ3枚でも水が無ければ宣言できない（枚数だけでは足りない）。"""
    e = setup(rules, {"bz": ["T005"]}, {"hand": ["T308"], "mana": ["T001", "T001", "T001"]})
    answer(e, "attack", "attack:T005:player")
    d = e.advance()
    assert d["kind"] == "choose_shields"     # 宣言の Decision は出ない


def test_ura_declare_blocked_without_count(rules):
    """水があってもマナ2枚では宣言できない。"""
    e = setup(rules, {"bz": ["T005"]}, {"hand": ["T308"], "mana": ["T063", "T063"]})
    answer(e, "attack", "attack:T005:player")
    d = e.advance()
    assert d["kind"] == "choose_shields"


def test_ura_dual_civ(rules):
    """光/水の2文明指定: 両方そろえば宣言でき、片方欠ければ宣言できない。"""
    e = setup(rules, {"bz": ["T005"]},
              {"hand": ["T309"], "mana": ["T302", "T063", "T001", "T001", "T001", "T001"]})
    answer(e, "attack", "attack:T005:player")
    d = e.advance()
    assert d["kind"] == "declare_attack" and d["player"] == 1
    assert any(k.startswith("declare:T309:") for k in keys(d))

    e = setup(rules, {"bz": ["T005"]},
              {"hand": ["T309"], "mana": ["T063", "T063", "T001", "T001", "T001", "T001"]})
    answer(e, "attack", "attack:T005:player")
    d = e.advance()
    assert d["kind"] == "choose_shields"     # 光が無いので宣言できない
