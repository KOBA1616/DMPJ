"""語彙パイロット第215弾: mana_count_doubled（マナの数字の倍加）のイディオム確認。

「このクリーチャーを召喚する時／この呪文を唱える時、自分のマナゾーンにある
オリジンのマナの数字は、1のかわりに2になる」（DM34 のオリジン一族）は、
第212弾で新設した面フィールド mana_boost の必須形
{filter: {races: [オリジン]}, value: 2} でそのまま表せる。新規語彙は無し。

検証の要点:
- 支払い組み合わせ: オリジン2枚が 2+2 として数えられコスト4に届く。
  混在（2+1+1）でも届く。オリジンでないマナは通常どおり1。
- 面フィールドは出すカード自身の支払いにだけ効く: ブーストを持たない
  カードの支払いではオリジンのマナは1として数える（漏洩しない）。
- 呪文形（「この呪文を唱える時」）でも同じ面フィールドが効く。
- 実プレイ: 2枚のオリジン・マナをタップして実際に召喚／唱えることができる。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T552", "T553", "T554")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)


def _cid_of(e, defn, zone, player=0):
    return next(c for c in e.zlist(zone, player)
                if e.s.cards[c].defn == defn)


def _choices(e, defn):
    cid = _cid_of(e, defn, "hand")
    return e._mana_choices(cid, 0)


def test_creature_choices_doubled(rules):
    """オリジン2枚 = 2+2 でコスト4に届く（T553 必須形）。"""
    e = setup(rules, {"hand": ["T553"], "mana": ["T552", "T552"]},
              {}, filler="T002")
    ch = _choices(e, "T553")
    assert len(ch) == 1 and len(ch[0]) == 2
    # 混在: オリジン1枚（2）＋通常2枚（1+1）でも届く
    e = setup(rules, {"hand": ["T553"], "mana": ["T552", "T002", "T002"]},
              {}, filler="T002")
    ch = _choices(e, "T553")
    assert len(ch) == 1 and len(ch[0]) == 3
    # オリジンでないマナだけでは 1+1 で届かない
    e = setup(rules, {"hand": ["T553"], "mana": ["T002", "T002"]},
              {}, filler="T002")
    assert _choices(e, "T553") == []
    # 通常マナ4枚なら通常どおり払える（ブーストが支払いを妨げない）
    e = setup(rules, {"hand": ["T553"], "mana": ["T002", "T002", "T002", "T002"]},
              {}, filler="T002")
    assert _choices(e, "T553")


def test_no_leak_to_other_cards(rules):
    """ブーストは出すカード自身の支払いだけ: T534（ブースト無し・コスト5）は
    オリジン2枚＋通常1枚 = 1+1+1 で届かない。"""
    e = setup(rules, {"hand": ["T534"], "mana": ["T552", "T552", "T002"]},
              {}, filler="T002")
    assert _choices(e, "T534") == []


def test_spell_choices_doubled(rules):
    """呪文形（T554）でも面 mana_boost が効く。"""
    e = setup(rules, {"hand": ["T554"], "mana": ["T552", "T552"]},
              {}, filler="T002")
    ch = _choices(e, "T554")
    assert len(ch) == 1 and len(ch[0]) == 2


def _in_bz(e, defn, ctrl=None):
    return any(e.s.cards[c].defn == defn and (ctrl is None or e.s.cards[c].controller == ctrl)
               for c in e.zlist("bz", 0))


def _drive(e, player, key, stop, limit=400):
    """player が key の行動を取り、stop() が真になって次の通常決定が来るまで流す。
    行動直前の (手札枚数, 山札枚数) を返す。"""
    acted = False
    before = None
    settled = False
    for _ in range(limit):
        if acted and stop():
            if settled:
                return before
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not acted and d.get("player") == player and d["kind"] in ("main", "attack") and key in keys:
            before = (len(e.zlist("hand", player)), len(e.zlist("deck", player)))
            e.answer([keys.index(key)])
            acted = True
        elif acted and stop() and d["kind"] in ("main", "charge"):
            settled = True
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return before


def test_actual_summon_with_doubled_mana(rules):
    """実プレイ: オリジン2枚をタップして T553 を召喚できる。"""
    e = setup(rules, {"hand": ["T553"], "mana": ["T552", "T552"]},
              {}, filler="T002")
    _drive(e, 0, "play:T553", lambda: _in_bz(e, "T553", 0))
    assert _in_bz(e, "T553", 0)
    origins = [c for c in e.zlist("mana", 0) if e.s.cards[c].defn == "T552"]
    assert len(origins) == 2 and all(e.s.cards[c].tapped for c in origins)


def test_actual_cast_spell_with_doubled_mana(rules):
    """実プレイ: オリジン2枚をタップして T554 を唱え、1枚引く。"""
    e = setup(rules, {"hand": ["T554"], "mana": ["T552", "T552"]},
              {}, filler="T002")
    before = _drive(e, 0, "play:T554",
                     lambda: any(e.s.cards[c].defn == "T554" for c in e.zlist("graveyard", 0)))
    assert before is not None
    assert any(e.s.cards[c].defn == "T554" for c in e.zlist("graveyard", 0))
    # 山札が1枚減り（ドロー）、手札は呪文が離れて1枚引いたので同数
    assert len(e.zlist("deck", 0)) == before[1] - 1
    assert len(e.zlist("hand", 0)) == before[0]
    origins = [c for c in e.zlist("mana", 0) if e.s.cards[c].defn == "T552"]
    assert len(origins) == 2 and all(e.s.cards[c].tapped for c in origins)
