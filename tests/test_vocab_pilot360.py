"""語彙パイロット第360弾: breaks_plus_one（ドリフト）。

センサス（rejects 1,973件を取り直し）: pure 1,825件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜359弾）は再提案しない。本弾で個別に
評価して見送った候補: variable_breaks_by_count（pure 1。
breaks_add の辞書形 {amount, count}（第170弾）で届く
可能性はあるが、進化＋クルー・ブレイカーの数え上げ
（other: true 込み）の検証が要り固定+1より大きい）、
count_face_up_shields（pure 1。表向きシールドの
count と「1枚につき引いてもよい」の repeat 形の
組み合わせ検証が要る）、power_per_civilization
（pure 1。選んだ対象への civ_count 参照（第2弾の式）の
検証が要る）、trigger_when_played_free（pure 1、
dm25ex4-t01。条項自体は第353弾の unpaid 形の候補だが
呪文面が超次元ホールで範囲外）、
first_time_cast_or_summon（pure 1。partial の注記どおり
first_time の共有キーが無く、2能力に分けると両方
誘発しうる）。範囲内・未評価で最小の breaks_plus_one
（pure 1件、multi にも現れない）を選定した:
dm14-s08 ファイナル・ドラグアーマー「これをクロスした
クリーチャーは『パワーアタッカー+5000』を得、シールドを
もう1枚ブレイクし、種族にアーマード・ドラゴンを追加する」。
partial は static {affects: crossed, mod: {power_when
+5000, add_races}} を既に持ち、未解決は unsupported の
本 gap 1件だけ。

結論はドリフト（追加語彙なし）:
- 「シールドをもう1枚ブレイクする」は相対ブレイク
  mod `breaks_add: 1`。breaks_add 統一機構の検証
  （tests/test_vocab_breaks_add.py）のヘッダが
  breaks_plus_one をその対象名として明記しており、
  crossed ホストへの付与は第224弾の T588 が
  mod {power: 2000, breaks_add: 1} で登録先例化済み。
- 追加先は partial の既存 static の mod そのもの
  （power_when / add_races と同じ mod に足す）。

proto T1083（dm14-s08型）/ T1084（ホスト）/
T1085（パワー6000ブロッカー）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接包む（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

STATIC = {"kind": "static", "affects": "crossed",
          "mod": {"power_when": {"amount": 5000, "when": "attacking"},
                  "breaks_add": 1,
                  "add_races": ["アーマード・ドラゴン"]}}
FORM = [STATIC]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1083")
    assert c["abilities"] == FORM
    assert c["types"] == ["cross_gear"]
    d = parse_card(copy.deepcopy(c), TABLES)
    assert STATIC in d.abilities


def test_form_raw_parse():
    d = parse_card({"id": "TX360", "name": "x",
                    "types": ["cross_gear"], "civs": ["fire"],
                    "cost": 3,
                    "abilities": [copy.deepcopy(STATIC)]}, TABLES)
    assert STATIC in d.abilities


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn):
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn)


def _defns(e, zone, p):
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _cross(e, gear="T1083", host="T1084", p=0):
    e.s.cards[_cid(e, p, gear)].crossed = \
        e.s.ref(_cid(e, p, host))


def test_crossed_host_chars(rules):
    """クロスすると breaks_add 1（ブレイク数2）・種族追加が
    及び、非攻撃時のパワーは素のまま（power_when は攻撃時）。"""
    e = _build(rules, {"bz": ["T1084", "T1083"]}, {})
    host = _cid(e, 0, "T1084")
    ch = e.chars(host)
    assert ch["breaks"] == 1 and ch["breaks_add"] == 0
    assert "アーマード・ドラゴン" not in ch["races"]
    _cross(e)
    ch = e.chars(host)
    assert ch["breaks_add"] == 1 and ch["breaks"] == 2
    assert ch["break_opts"] == [2]
    assert "アーマード・ドラゴン" in ch["races"]
    assert "ヒューマノイド" in ch["races"]
    assert ch["power"] == 2000


def _drive_attack(e, attacker, block_with=None):
    """p0 の attacker でプレイヤーを攻撃する。block_with が
    あればそのブロッカー（p1）でブロックする。攻撃した
    ターンの2つ先のターンまで進めて状態を返す。"""
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


def test_crossed_host_breaks_two_shields(rules):
    """クロスしたホストの攻撃はシールドを2枚ブレイクする
    （5→3）。クロスしなければ1枚（5→4）。"""
    e = _build(rules, {"bz": ["T1084", "T1083"]}, {})
    _cross(e)
    st = _drive_attack(e, "T1084")
    assert st["attacked"]
    assert len(_defns(e, "shield", 1)) == 3

    e = _build(rules, {"bz": ["T1084", "T1083"]}, {})
    st = _drive_attack(e, "T1084")
    assert st["attacked"]
    assert len(_defns(e, "shield", 1)) == 4


def test_crossed_host_wins_battle_via_power_attacker(rules):
    """クロスしたホストは攻撃時パワー7000になり、パワー
    6000のブロッカーにバトルで勝つ。クロスしなければ
    2000で負けて破壊される（power_when の対照）。"""
    e = _build(rules, {"bz": ["T1084", "T1083"]}, {"bz": ["T1085"]})
    _cross(e)
    st = _drive_attack(e, "T1084", block_with="T1085")
    assert st["attacked"]
    assert "T1085" in _defns(e, "graveyard", 1)
    assert "T1084" in _defns(e, "bz", 0)

    e = _build(rules, {"bz": ["T1084", "T1083"]}, {"bz": ["T1085"]})
    st = _drive_attack(e, "T1084", block_with="T1085")
    assert st["attacked"]
    assert "T1084" in _defns(e, "graveyard", 0)
    assert "T1085" in _defns(e, "bz", 1)


def test_real_generate_and_cross_flow(rules):
    """実フロー: ジェネレート→コストをもう一度払って
    クロスすると、ホストに breaks_add が及ぶ。"""
    e = _build(rules,
               {"hand": ["T1083"], "bz": ["T1084"],
                "mana": ["T005"] * 6},
               {})
    crossed = False
    for _ in range(300):
        gear = next((c for c in e.zlist("bz", 0)
                     if e.s.cards[c].defn == "T1083"), None)
        if gear is not None and e.s.cards[gear].crossed:
            crossed = True
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "main" and d["player"] == 0:
            cross = [k for k in keys if k.startswith("cross:T1083:")]
            if cross:
                e.answer([keys.index(cross[0])])
            elif "play:T1083" in keys:
                e.answer([keys.index("play:T1083")])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert crossed
    ch = e.chars(_cid(e, 0, "T1084"))
    assert ch["breaks_add"] == 1 and ch["breaks"] == 2
