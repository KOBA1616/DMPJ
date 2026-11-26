"""語彙パイロット第371弾: set_power_zero（ドリフト）。

センサス（rejects 1,962件を取り直し）: pure 1,814件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜370弾）は再提案しない。本弾で個別に
評価して見送った候補: power_set（pure 2、dm26rp3-or001 /
dm26rp3-sec001。partial の abilities が無く「パワーが
0以下の間離れない」「各ターン、はじめて攻撃する時」の
他条項が未組立てのため、本 gap 単独では登録形が定まら
ない）、set_power（pure 1、dm32-011。power_set: 500 の
一括形自体は第272弾の mod で届くが、進化元
「自分の『ブロッカー』を持つクリーチャー」が partial に
無く補完の検証が要り本弾の最小ではない。次弾以降の候補
として残す）、slayer_while_attacking_low_cost（pure 1、
dm22ex2-013。「攻撃中」の相手条件つき grant は第364弾の
power_when opponent_filter では power 専用で、grant 側に
同形が無い＝新語彙が要る）、blocker_dies_after_battle_
even_if_wins（pure 1、dm01-028。ターン持続で「自分の
クリーチャーをブロックした相手すべて」をバトル後に
墓地に置く付与形が無い）、battle_loser_not_destroyed_
vs_self（pure 1、dm20-025。バトル敗者の破壊置換（対
自分限定）の語彙が無い）、destroy_after_battle
（pure 1、dm07-003。「このターンにバトルした」クリーチャー
へのバトル後破壊は、バトル履歴の追跡とターン内の遅延
付与が要る）。範囲内・未評価で最小の set_power_zero
（pure 1件、multi にも現れない）を選定した。

対象は pure 1件すべて: dmex15-b025 永遠の無（闇の
呪文 / コスト5）。partial は骨格（types [spell] /
civs [darkness] / cost 5 / mana 1、abilities・spell
ともに無し）で、未解決は unsupported の set_power_zero
1件だけ（partial の注記「パワーを固定値にする語彙が
無いため unsupported に残した」は、第272弾の power_set
と第370弾の確立形で解消済みだった）。単面カードで
未検証の面は無い。partial の text は第2条項の断片
（「そのクリーチャーのパワーを０にする」）だけのため、
提出形では行の公式テキスト全文を text に入れる
（補完あり。ラウンド406への注意に明記）。

条項「相手のクリーチャーを１体選ぶ。このターン、その
クリーチャーのパワーを０にする」はすべて確立済みの
部品で表せる（追加語彙なし）:

- 第370弾 set_power_to_zero の確立形そのもの:
  choose {select: {zone: bz, owner: opp, filter:
  {types: [creature]}, count: 1}, as: victim} →
  modify {select: {ref: victim}, mod: {power_set: 0},
  duration: end_of_turn}。登録先例 dmrp11-zs01（零）と
  dm24ex2-042（第370弾、ラウンド405）は誘発の effect
  内の同形で、本カードは呪文のため同じ2 op を spell に
  置く（呪文の spell に choose を置く形は第368弾
  dm21-011 の登録先例がある）。gap 名 set_power_zero は
  set_power_to_zero の別名行。
- 括弧書き「（パワー０以下のクリーチャーは破壊
  される）」はルール注記で、状況起因処理（703.4c）が
  エンジンに実装済みのため条項としては書かない
  （第370弾と同判断）。

確立形: spell = [choose {owner: opp, as: victim},
modify {power_set: 0, duration: end_of_turn}] の2 op。

proto T1115（dmex15-b025 型）。判別役は既存 proto を
流用: T1105（パワー4000ブロッカー＝素の対象役）、
T1114（自己パワー+3000役＝実効6000。power_set が加算
ごと上書きすることの判別役）、T1107（能力なしパワー
2000＝自分のクリーチャーが候補に入らない対照／第2の
候補役）、T872（闇マナ役）。

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

SPELL = [{"op": "choose",
          "select": {"zone": "bz", "owner": "opp",
                     "filter": {"types": ["creature"]},
                     "count": 1},
          "as": "victim"},
         {"op": "modify",
          "select": {"ref": "victim"},
          "mod": {"power_set": 0},
          "duration": "end_of_turn"}]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1115")
    assert c["spell"] == SPELL
    assert not c.get("abilities")
    assert c["types"] == ["spell"] and c["civs"] == ["darkness"]
    assert c["cost"] == 5 and c["mana"] == 1
    d = parse_card(copy.deepcopy(c), TABLES)
    assert [op["op"] for op in d.spell] == ["choose", "modify"]
    assert d.spell[0]["as"] == "victim"
    assert d.spell[1]["mod"] == {"power_set": 0}
    assert d.spell[1]["duration"] == "end_of_turn"
    for tid in ("T1105", "T1114", "T1107", "T872"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX371", "name": "x",
                    "types": ["spell"], "civs": ["darkness"],
                    "cost": 5, "mana": 1,
                    "spell": copy.deepcopy(SPELL)}, TABLES)
    assert [op["op"] for op in d.spell] == ["choose", "modify"]
    assert d.spell[1]["mod"] == {"power_set": 0}


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _find(e, zone, p, defn):
    cards = e.bz_tops(p) if zone == "bz" else e.zlist(zone, p)
    return next(c for c in cards if e.cdef(c).id == defn)


def _boring(d):
    keys = [o["key"] for o in d["options"]]
    for want in ("pass", "end_turn", "end_attack", "end_phase"):
        if want in keys:
            return [keys.index(want)]
    return [0]


def _cast(rules, p0, p1, choose_defn=None):
    """p0 が T1115 を唱え、choose_defn を選んで解決まで
    進める。（engine, 唱えたか, choose の min）を返す
    （第368弾の作法）。"""
    e = _build(rules, p0, p1)
    cast = False
    chose_min = None
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not cast and d["kind"] == "main" and d.get("player") == 0 \
                and "play:T1115" in keys:
            cast = True
            e.answer([keys.index("play:T1115")])
            continue
        if cast and d["kind"] == "choose_cards":
            chose_min = d["min"]
            idx = [i for i, o in enumerate(d["options"])
                   if choose_defn in o["key"]]
            assert idx, f"{choose_defn} が選択肢に無い: {keys}"
            e.answer(idx[:1])
            continue
        if cast and d["kind"] in ("main", "charge", "attack"):
            break          # 解決が終わり次の通常判断に戻った
        e.answer(_boring(d))
    return e, cast, chose_min


def test_cast_sets_chosen_power_zero_and_destroys(rules):
    """実挙動: T1115 を唱え、相手のパワー4000（T1105）を
    選ぶと、そのパワーが0になり状況起因処理で破壊されて
    墓地に行く。唱えた呪文自身も墓地に置かれる。"""
    e, cast, _ = _cast(rules,
                       {"hand": ["T1115"], "mana": ["T872"] * 5},
                       {"bz": ["T1105"]}, "T1105")
    assert cast
    assert "T1105" not in _defns(e, "bz", 1)
    assert "T1105" in _defns(e, "graveyard", 1)
    assert "T1115" in _defns(e, "graveyard", 0)


def test_cast_power_set_overwrites_power_additions(rules):
    """判別: 実効パワー6000（印刷3000＋static +3000）の
    T1114 を選んでも、power_set は加算ごと上書きして
    0にするため破壊される（印刷パワー分の減算では
    3000が残って破壊されないはず。第370弾と同判別）。"""
    e0 = _build(rules, {}, {"bz": ["T1114"]})
    ch = e0.chars(_find(e0, "bz", 1, "T1114"))
    assert ch["power"] == 6000          # 前提: 加算が効いている
    e, cast, _ = _cast(rules,
                       {"hand": ["T1115"], "mana": ["T872"] * 5},
                       {"bz": ["T1114"]}, "T1114")
    assert cast
    assert "T1114" not in _defns(e, "bz", 1)
    assert "T1114" in _defns(e, "graveyard", 1)


def test_cast_two_candidates_choice_is_mandatory(rules):
    """判別: 候補が2体いれば選択は必須（min=1）で、
    選ばなかった方は残る。"""
    e, cast, chose_min = _cast(
        rules,
        {"hand": ["T1115"], "mana": ["T872"] * 5},
        {"bz": ["T1105", "T1107"]}, "T1105")
    assert cast and chose_min == 1
    assert "T1105" in _defns(e, "graveyard", 1)
    assert "T1107" in _defns(e, "bz", 1)


def test_cast_no_opponent_creature_no_effect(rules):
    """判別: 相手のクリーチャーがいなければ choose の
    候補は無く（自分のクリーチャーは owner: opp で候補に
    入らない）、効果は空振りで解決する。自分の T1107 は
    無事で、呪文は墓地に置かれる。"""
    e, cast, chose_min = _cast(
        rules,
        {"hand": ["T1115"], "mana": ["T872"] * 5, "bz": ["T1107"]},
        {}, None)
    assert cast and chose_min is None    # 選択判断自体が出ない
    assert "T1107" in _defns(e, "bz", 0)
    assert _defns(e, "graveyard", 0) == ["T1115"]
    assert _defns(e, "graveyard", 1) == []
