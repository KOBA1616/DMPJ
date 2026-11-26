"""語彙パイロット第366弾: conditional_battle_indestructible
（ドリフト）。

センサス（rejects 1,967件を取り直し）: pure 1,819件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜365弾）は再提案しない。本弾で個別に
評価して見送った候補: summon_turn_attack_restriction
（pure 1、dmr22-s04。第365弾で見送った
speed_attacker_rule と同機構＝keyword フィルタ＋
owner: any の常在付与で、登録先例が無い）、
no_leave_except_destroy（pure 1、promoy22-spd1001。
no_leave {except_destroy: true} は defs にあるが
「自分のターン中」の条件とハイパー化の併記があり
本弾の最小ではない）、hand_add_event（pure 1、
dmrp04s-s04。「山札以外のゾーンから」を move 誘発の
from で除外する書き方が無く、加わった呪文そのものを
無償で唱える参照も要る）、shield_leave_event
（pure 1、dmrp04m-002。離脱誘発に加え「ブレイクする
シールドを相手のかわりに自分が選ぶ」条項が partial に
能力として組まれておらず、本 gap 単独では登録形が
定まらない）、mana_leave_trigger（pure 1、dmr05-032。
「相手のターン中」のターン条件を move 誘発に付ける
確立形が無い）、move_to_deck_bottom_trigger
（pure 1、dmex04-025。move レコードに置き場所
（上／下）の区別が無い）、grant_mach_fighter_keyword
（pure 1、dm24ex3-rp1s09。mach_fighter は grant の
対象キーワードに無く、ハイパー化条項も併記される）、
always_win_battles（pure 1、dm14-s01。第61弾の
win_all_battles の別名行で表現可能だが、本弾では
条件つき形を優先した。次弾以降の候補として残す）。
範囲内・未評価で最小の conditional_battle_indestructible
（pure 1件、multi にも現れない）を選定した:
dm24rp2-054 ケルビ・チゼン「自分の超化獣クリーチャーが
あれば、このクリーチャーはバトル中破壊されない」。
partial は骨格（keywords [blocker] のみ、abilities 無し）
で、未解決は unsupported の本 gap 1件だけ。単面カードで
未検証の面は無く、partial に欠けた要素も無い（補完なし）。

結論はドリフト（追加語彙なし）:
- 「バトル中破壊されない」は第59弾の確立 mod
  {battle_indestructible: true}（combat._battle が
  パワー敗者から除外する。勝敗判定自体はパワーどおりで、
  第59弾の記録どおり）。converted に多数の使用例がある。
- 「自分の超化獣クリーチャーがあれば」は static の
  if {exists: {zone: bz, owner: you, filter:
  {race_has: 超化獣}}} で、第356弾の確立形そのもの
  （登録先例 dm21-s04 の条件つき slayer 付与と同文の
  照合。第59弾の記録も「条件付きは if で書く」と明記）。
  本カード自身の種族はメカ・デル・ディネロで超化獣では
  ないため、条件は他の自分の超化獣でだけ満たされる。

確立形: static {affects: self, if: {exists: {zone: bz,
owner: you, filter: {race_has: 超化獣}}}, mod:
{battle_indestructible: true}}。

proto T1101（dm24rp2-054 型）/ T1102（超化獣の味方役）/
T1103（パワー4000アタッカー役）。

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
          "if": {"exists": {"zone": "bz", "owner": "you",
                            "filter": {"race_has": "超化獣"}}},
          "mod": {"battle_indestructible": True}}
FORM = [STATIC]
KEYWORDS = ["blocker"]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1101")
    assert c["abilities"] == FORM
    assert c["keywords"] == KEYWORDS
    assert c["types"] == ["creature"]
    assert c["cost"] == 2 and c["power"] == 1500
    d = parse_card(copy.deepcopy(c), TABLES)
    assert STATIC in d.abilities
    for tid in ("T1102", "T1103"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX366", "name": "x",
                    "types": ["creature"], "civs": ["light"],
                    "cost": 2, "power": 1500,
                    "races": ["メカ・デル・ディネロ"],
                    "keywords": list(KEYWORDS),
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


def test_chars_condition_own_hyperbeast_only(rules):
    """特性レベル: 自分の超化獣がバトルゾーンにいる時だけ
    battle_indestructible が付く。相手の超化獣では付かず、
    自分だけ（本カードの種族は超化獣ではない）でも付かない。"""
    e = _build(rules, {"bz": ["T1101", "T1102"]}, {"bz": ["T1103"]})
    assert e.chars(_cid(e, "T1101", 0))["battle_indestructible"] is True
    e = _build(rules, {"bz": ["T1101"]}, {"bz": ["T1102", "T1103"]})
    assert e.chars(_cid(e, "T1101", 0))["battle_indestructible"] is False
    e = _build(rules, {"bz": ["T1101"]}, {"bz": ["T1103"]})
    assert e.chars(_cid(e, "T1101", 0))["battle_indestructible"] is False


def _drive_attack(e, attacker, block_with=None):
    """p1 の attacker でプレイヤーを攻撃する。block_with が
    あればそのブロッカー（p0）でブロックし、無ければ
    ブロックしない。攻撃したターンの2つ先のターンまで
    進めて状態を返す（第364弾の作法）。"""
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


def test_block_loses_battle_but_not_destroyed_with_hyperbeast(rules):
    """自分の超化獣がいれば、パワー4000の攻撃をブロックして
    バトルに負けても T1101 は破壊されずバトルゾーンに残る
    （攻撃側も勝者として残る）。"""
    e = _build(rules, {"bz": ["T1101", "T1102"]}, {"bz": ["T1103"]})
    st = _drive_attack(e, "T1103", block_with="T1101")
    assert st["attacked"]
    assert "T1101" in _defns(e, "bz", 0)
    assert "T1101" not in _defns(e, "graveyard", 0)
    assert "T1103" in _defns(e, "bz", 1)


def test_block_without_hyperbeast_destroyed(rules):
    """自分の超化獣がいなければ、パワー4000の攻撃をブロック
    した T1101 はバトルに負けて破壊され墓地に置かれる。"""
    e = _build(rules, {"bz": ["T1101"]}, {"bz": ["T1103"]})
    st = _drive_attack(e, "T1103", block_with="T1101")
    assert st["attacked"]
    assert "T1101" not in _defns(e, "bz", 0)
    assert "T1101" in _defns(e, "graveyard", 0)
    assert "T1103" in _defns(e, "bz", 1)


def test_no_block_breaks_shield(rules):
    """ブロックしなければ通常どおりシールドが1枚ブレイク
    され、両者ともバトルゾーンに残る（対照）。"""
    e = _build(rules, {"bz": ["T1101", "T1102"]}, {"bz": ["T1103"]})
    before = len(e.zlist("shield", 0))
    st = _drive_attack(e, "T1103")
    assert st["attacked"]
    assert len(e.zlist("shield", 0)) == before - 1
    assert "T1101" in _defns(e, "bz", 0)
    assert "T1103" in _defns(e, "bz", 1)
