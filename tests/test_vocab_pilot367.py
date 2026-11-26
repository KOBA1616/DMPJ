"""語彙パイロット第367弾: always_win_battles
（ドリフト）。

センサス（rejects 1,966件を取り直し）: pure 1,819件 /
multi 129行 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
106 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜366弾）は再提案しない。第366弾で
「第61弾の win_all_battles の別名行で表現可能」と
評価済みの候補 always_win_battles（pure 1件、dm14-s01）
を、取り直したセンサスで裏取りして選定した（pure 1件が
最小単位で、本 gap は multi にも現れない）。

対象は pure 1件すべて: dm14-s01 太陽の精霊マルシアス
「このクリーチャーはすべてのバトルに勝つ。(相手
クリーチャーのパワーの方が大きくても、相手クリーチャーは
バトルに負ける。バトルしているクリーチャー両方がこの
能力を持っている場合は、どちらも破壊されない)」。
partial は骨格（abilities 無し、keywords 無し）で、
未解決は unsupported の本 gap 1件だけ。単面カードで
未検証の面は無く、partial に欠けた要素も無い（補完なし）。

結論はドリフト（追加語彙なし）:
- 「すべてのバトルに勝つ」は第61弾の確立 mod
  {win_all_battles: true}（static {affects: self}。
  defs MOD_KEYS 収載、core の chars 集約、combat._battle
  がパワー比較の前に判定）。converted に多数の使用例が
  ある。gap 名 always_win_battles はその別名行。
- combat._battle の判定は「片方だけ持てばパワーに
  関わらずその側が勝ち、両方持てば相打ちなし」で、
  公式テキストの括弧書き2点（相手のパワーが大きくても
  相手が負ける／両方が持てばどちらも破壊されない）と
  完全一致する。

確立形: static {affects: self, mod:
{win_all_battles: true}}。

proto T1104（dm14-s01 型）/ T1105（パワー4000
ブロッカー役）/ T1106（win_all_battles 持ちブロッカー役）/
T1107（能力なしパワー2000アタッカー役＝対照）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED
が復活するので scenario.build を直接包む
（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

STATIC = {"kind": "static", "affects": "self",
          "mod": {"win_all_battles": True}}
FORM = [STATIC]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1104")
    assert c["abilities"] == FORM
    assert not c.get("keywords")
    assert c["types"] == ["creature"]
    assert c["cost"] == 5 and c["power"] == 2000
    d = parse_card(copy.deepcopy(c), TABLES)
    assert STATIC in d.abilities
    for tid in ("T1105", "T1106", "T1107"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX367", "name": "x",
                    "types": ["creature"], "civs": ["light"],
                    "cost": 5, "power": 2000,
                    "races": ["エンジェル・コマンド"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert STATIC in d.abilities


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _cid(e, tid, p):
    return next(c for c in e.bz_tops(p) if e.cdef(c).id == tid)


def test_chars_win_all_battles(rules):
    """特性レベル: T1104 と T1106 には win_all_battles が
    付き、能力なしの T1107 には付かない。"""
    e = _build(rules, {"bz": ["T1106"]}, {"bz": ["T1104", "T1107"]})
    assert e.chars(_cid(e, "T1104", 1))["win_all_battles"] is True
    assert e.chars(_cid(e, "T1106", 0))["win_all_battles"] is True
    assert e.chars(_cid(e, "T1107", 1))["win_all_battles"] is False


def _drive_attack(e, attacker, block_with=None):
    """p1 の attacker でプレイヤーを攻撃する。block_with が
    あればそのブロッカー（p0）でブロックし、無ければ
    ブロックしない。攻撃したターンの2つ先のターンまで
    進めて状態を返す（第366弾の作法）。"""
    state = {"attacked": False, "attack_turn": None}
    for _ in range(1500):
        if state["attacked"] and e.s.turn >= state["attack_turn"] + 2:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack":
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and not state["attacked"]:
                state["attacked"] = True
                state["attack_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            hit = [i for i, k in enumerate(keys)
                   if block_with and k.startswith(f"bz:{block_with}:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return state


def test_weaker_attacker_wins_vs_stronger_blocker(rules):
    """パワー2000の T1104 がパワー4000のブロッカーに
    ブロックされても、すべてのバトルに勝つためブロッカーが
    破壊され、T1104 は残る。シールドはブレイクされない。"""
    e = _build(rules, {"bz": ["T1105"]}, {"bz": ["T1104"]})
    before = len(e.zlist("shield", 0))
    st = _drive_attack(e, "T1104", block_with="T1105")
    assert st["attacked"]
    assert "T1104" in _defns(e, "bz", 1)
    assert "T1105" not in _defns(e, "bz", 0)
    assert "T1105" in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 0)) == before


def test_both_win_all_battles_neither_destroyed(rules):
    """両方が win_all_battles を持つ場合は相打ちなし:
    T1104 が T1106 にブロックされても、どちらも破壊
    されずバトルゾーンに残る（公式テキストの括弧書き）。"""
    e = _build(rules, {"bz": ["T1106"]}, {"bz": ["T1104"]})
    before = len(e.zlist("shield", 0))
    st = _drive_attack(e, "T1104", block_with="T1106")
    assert st["attacked"]
    assert "T1104" in _defns(e, "bz", 1)
    assert "T1106" in _defns(e, "bz", 0)
    assert "T1104" not in _defns(e, "graveyard", 1)
    assert "T1106" not in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 0)) == before


def test_plain_attacker_loses_to_stronger_blocker(rules):
    """対照: 能力なしのパワー2000アタッカーはパワー4000の
    ブロッカーにブロックされるとバトルに負けて破壊される。"""
    e = _build(rules, {"bz": ["T1105"]}, {"bz": ["T1107"]})
    st = _drive_attack(e, "T1107", block_with="T1105")
    assert st["attacked"]
    assert "T1107" not in _defns(e, "bz", 1)
    assert "T1107" in _defns(e, "graveyard", 1)
    assert "T1105" in _defns(e, "bz", 0)


def test_no_block_breaks_shield(rules):
    """ブロックしなければ通常どおりシールドが1枚ブレイク
    される（win_all_battles はブレイク数に影響しない）。"""
    e = _build(rules, {"bz": ["T1105"]}, {"bz": ["T1104"]})
    before = len(e.zlist("shield", 0))
    st = _drive_attack(e, "T1104")
    assert st["attacked"]
    assert len(e.zlist("shield", 0)) == before - 1
    assert "T1104" in _defns(e, "bz", 1)
    assert "T1105" in _defns(e, "bz", 0)
