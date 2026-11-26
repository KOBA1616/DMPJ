"""語彙パイロット第386弾: graveyard_replacement（ドリフト）。

センサス（rejects 1,947件を取り直し）: pure 1,800件 /
multi 129件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
106 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜385弾）は再提案しない。本弾で個別に
評価して見送った候補: does_not_untap（pure 2。
dm22rp1-011 はタマシード条件の攻撃可否とタマシード
出場時のアンタップ誘発が未構築、dm25ex2-031 は
シンパシーと全体破壊 CIP が未構築で、本 gap 単独では
登録形が定まらない）、attack_limit_once_per_turn
（pure 2。ターン内攻撃回数の追跡が要り、dm23bd7-012 は
ツインパクト呪文面＋捨て札からの無料詠唱も残る）、
break_all_except（pure 2。選んだ2つ以外の全ブレイクの
機構が無く、dm24ex3-rp3tr4 は J・O・E と出場制限条項も
残る）、zone_lock（pure 2。ゾーン離脱そのものの deny で
確立形が無い）、battle_intercept（pure 2。攻撃への割り込み
バトルの反応機構が要る。第384弾の first_attack_reaction_
battle 却下と同根）、delayed_return（pure 2。ターン終わりの
遅延回収は出されたクリーチャー集合の追跡が要る）、
cast_from_mana（pure 2。マナゾーンからの詠唱許可の常在形が
無く、モーダル呪文面も残る）、conditional_s_trigger
（pure 2。条件つき S・トリガー付与は第377弾却下の
s_trigger_grant_condition と同根で、他条項も重い）、
power_set（pure 2、∑龍 dm26rp3-or001 / sec001。各ターン
初回攻撃時の誘発と「パワー0以下の間離れない」が残り、
第370〜372弾で解消した set_power 系とは別行）、flying
（pure 2。dm26ex2-pr001 は追加ターン＋全体生贄と複合、
dm26sd1-v007 は「すべての文明を持つかのようにタップ」の
支払い条項が残る）、forced_break（pure 2。相手が選んだ
シールドの指定ブレイク機構が無い）、from_hand_trigger
（pure 2。手札から出た時の照合に加え同名復活／自己マナ置き
置換が残る）、look_reorder（pure 2。partial が空か
self_return と混ざり評価不能）、master_breaker（pure 2。
各ブレイク前の破壊誘発の新機構が要る）、reveal_hand
（pure 2。公開の継続保持の意味論確認が要り最小でない）、
civ_blocker（pure 2。文明限定ブロッカー＋同文明への
バトル敗北無効の2機構が要る）、enters_tapped_optional /
after_battle_trigger（各 pure 2。partial が無く評価不能）。
範囲内・未評価で最小の graveyard_replacement を選定した。

対象はファミリー2件のうち単一条項の dm26ex4-cho046
夜露死苦 キャロル（水/火 / コスト3 / パワー2000 /
アウトレイジ）。partial は骨格のみ（keywords・abilities
無し）で、未解決は unsupported の graveyard_replacement
1件だけ。単面カードで未検証の面は無い。条項
「このクリーチャーがどこからでも墓地に置かれる時、
自分のマナゾーンに水と火文明があれば、かわりに
手札に戻す」は確立済みの部品で表せる（追加語彙なし）:

- 置換の when は {event: move, to: graveyard,
  subject: self} と from を書かない形で「どこからでも」
  を表す（破壊・捨て札・ミル等の全経路に掛かる）。
- 条件「自分のマナゾーンに水と火文明があれば」は
  置換への if（第375弾で確立）に all [exists
  {zone: mana, owner: you, filter: {civs: [water]}},
  exists {zone: mana, owner: you, filter:
  {civs: [fire]}}] を置く形。
- instead は move {select: {ref: subject, count: 1},
  to: hand, reason: return}。
- 決定的な登録先例: 同名カードの別刷り dm23ex1-062
  夜露死苦 キャロルが converted に登録済みで、その
  abilities は本形と完全一致する（本弾で実測）。
  partial の注記「墓地に置く処理の置換を表す語彙が
  無い」は登録時点より前の陳腐化だった。

確立形: abilities = [replace {when: {event: move,
to: graveyard, subject: self}, if: {all: [exists
{zone: mana, owner: you, filter: {civs: [water]}},
exists {zone: mana, owner: you, filter:
{civs: [fire]}}]}, instead: [move {select:
{ref: subject, count: 1}, to: hand, reason: return}]}]
の1件。partial の text は条項の断片（「どこからでも
墓地に置かれる時、かわりに手札に戻す」）のため、
提出形では text に行の公式テキスト全文を入れる
（補完あり。ラウンド421への注意に明記）。

ファミリーのもう1件 dm25ex2-cho021 悠久を統べる者
フォーエバー・プリンセスは本弾の対象外: instead が
「このクリーチャーと自分の墓地を山札に加えて
シャッフル」で形が異なり、第1条項（コストを支払わずに
出た相手クリーチャーをマナゾーンに置く）も partial に
未構築のため、本 gap はラウンド421では解消しない
（1件残る）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無いことを
本弾で実測済み。

**ラウンド421への正本判定の申し送り**: identity では
canon(dm26ex4-cho046) = dm26ex4-cho046 で、alias は
dm23ex1-062 / dmex03-029 / dmex13-056 / dmx14-031 /
promoy12-031 の5件。そのうち dm23ex1-062 は同条項の
登録形を持つ converted の独立エントリとして既に
登録済み（source.aliases には alias を持たない）。
他の4件は converted にも rejects にも現れない。
ラウンド421では、この既登録 alias との関係（新規登録
として source.aliases に入れるか、dm02-046 型の stale
扱いか）を submit 前に実データで判断すること。

**既知のエンジン側制限（本弾で実測、docs に記録）**:
置換の発生源走査（events.py _replacement）は
「バトルゾーン外の発生源は、そのゾーンを宣言した
置換だけ」という規則で、zone は単一ゾーンしか
宣言できない。そのため本形（zone 宣言なし）は
bz 起点（破壊）でのみ発火し、手札から捨てられる・
山札からミルされる起点では発火しないことを実測した
（T117 強奪の呪文で手札から捨てさせると、水＋火が
マナにあっても墓地に行く）。登録済み dm23ex1-062 も
同一形のため同じ制限を持つ。「どこからでも」の
全起点対応は置換走査規則の設計判断（全置換能力に
波及）であり、本弾の最小範囲を超えるため専用
ステージ送りとし、本弾は登録先例と同一形の
ドリフトで確立する。多ゾーン宣言の置換は converted
10,365件中に先例が無い（本弾で実測）。

proto T1149（dm26ex4-cho046 型）。判別役は既存 proto
を流用: T1105（火・パワー4000ブロッカー＝ハンター役）/
T079（水・マナ役）/ T277（火・マナ役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接包む
（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import find, proto_card  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)

REPLACE = {"kind": "replace",
           "when": {"event": "move", "to": "graveyard", "subject": "self"},
           "if": {"all": [
               {"exists": {"zone": "mana", "owner": "you",
                           "filter": {"civs": ["water"]}}},
               {"exists": {"zone": "mana", "owner": "you",
                           "filter": {"civs": ["fire"]}}}]},
           "instead": [{"op": "move",
                        "select": {"ref": "subject", "count": 1},
                        "to": "hand", "reason": "return"}]}
FORM = [REPLACE]
FULL_TEXT = ("このクリーチャーがどこからでも墓地に置かれる時、"
             "自分のマナゾーンに水と火文明があれば、かわりに手札に戻す。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1149")
    assert c["abilities"] == FORM
    assert c["text"] == FULL_TEXT
    assert c["types"] == ["creature"] and c["civs"] == ["water", "fire"]
    assert c["cost"] == 3 and c["power"] == 2000
    assert c["races"] == ["アウトレイジ"] and c["mana"] == 1
    d = parse_card(copy.deepcopy(c), TABLES)
    assert REPLACE in d.abilities
    for tid in ("T1105", "T079", "T277"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX386", "name": "x",
                    "types": ["creature"], "civs": ["water", "fire"],
                    "cost": 3, "power": 2000, "mana": 1,
                    "races": ["アウトレイジ"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert REPLACE in d.abilities


def test_unknown_civ_in_condition_is_def_error():
    """判別: exists フィルタの未知の文明名は DefError。"""
    bad = copy.deepcopy(FORM)
    bad[0]["if"]["all"][0]["exists"]["filter"]["civs"] = ["bogus"]
    with pytest.raises(DefError):
        parse_card({"id": "TX386B", "name": "x",
                    "types": ["creature"], "civs": ["water", "fire"],
                    "cost": 3, "power": 2000, "mana": 1,
                    "races": ["アウトレイジ"], "abilities": bad}, TABLES)


def test_unknown_cond_key_is_def_error():
    """判別: 未知の条件キーは DefError。"""
    bad = copy.deepcopy(FORM)
    bad[0]["if"] = {"bogus_cond": 1}
    with pytest.raises(DefError):
        parse_card({"id": "TX386C", "name": "x",
                    "types": ["creature"], "civs": ["water", "fire"],
                    "cost": 3, "power": 2000, "mana": 1,
                    "races": ["アウトレイジ"], "abilities": bad}, TABLES)


def test_registered_precedent_matches_form():
    """ドリフトの実測: 登録済み dm23ex1-062（同名カードの
    別刷り）の abilities は本形と完全一致する。"""
    c = find(CONVERTED, "dm23ex1-062")
    assert c is not None
    assert c["name"] == "夜露死苦 キャロル"
    assert c["abilities"] == FORM


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive_destroyed_in_battle(e, target="T1149", hunter="T1105"):
    """target（p1）がプレイヤーを攻撃してタップした後、
    p0 の hunter にクリーチャー攻撃されてバトルで破壊
    される経路（第375弾の作法）。choose_replacement の
    諮問が出たら置換を選ぶ。"""
    state = {"charged": False, "hunted": False, "hunt_turn": None}
    for _ in range(1500):
        if state["hunted"] and e.s.turn >= state["hunt_turn"] + 2:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack" and d.get("player") == 1:
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{target}:player"]
            if hit and not state["charged"]:
                state["charged"] = True
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "attack" and d.get("player") == 0:
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{hunter}:{target}"]
            if hit and state["charged"] and not state["hunted"]:
                state["hunted"] = True
                state["hunt_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            # target はブロック可能なので、プレイヤー攻撃は
            # ブロックせず通す（ブロックされるとハンター役が
            # バトルで破壊してしまい経路が変わる）
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "choose_replacement":
            hit = [i for i, k in enumerate(keys)
                   if k.startswith(f"replace:{target}:")]
            assert hit, keys
            e.answer([hit[0]])
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return state


def test_destroy_returns_to_hand_with_water_and_fire_mana(rules):
    """実挙動: 自分のマナゾーンに水と火があれば、バトルで
    破壊される代わりに手札に戻る（墓地には行かない）。"""
    e = _build(rules, {"bz": ["T1105"]},
               {"bz": ["T1149"], "mana": ["T079", "T277"]})
    st = _drive_destroyed_in_battle(e)
    assert st["charged"] and st["hunted"]
    assert "T1149" in _defns(e, "hand", 1)
    assert "T1149" not in _defns(e, "graveyard", 1)
    assert "T1149" not in _defns(e, "bz", 1)


def test_destroy_goes_to_graveyard_with_water_only(rules):
    """対照: マナが水だけでは条件が外れ（火が無い）、
    置換は適用されず破壊され墓地に行く。"""
    e = _build(rules, {"bz": ["T1105"]},
               {"bz": ["T1149"], "mana": ["T079"]})
    st = _drive_destroyed_in_battle(e)
    assert st["charged"] and st["hunted"]
    assert "T1149" in _defns(e, "graveyard", 1)
    assert "T1149" not in _defns(e, "hand", 1)


def test_destroy_goes_to_graveyard_with_fire_only(rules):
    """対照: マナが火だけでは条件が外れ（水が無い）、
    置換は適用されず破壊され墓地に行く。"""
    e = _build(rules, {"bz": ["T1105"]},
               {"bz": ["T1149"], "mana": ["T277"]})
    st = _drive_destroyed_in_battle(e)
    assert st["charged"] and st["hunted"]
    assert "T1149" in _defns(e, "graveyard", 1)
    assert "T1149" not in _defns(e, "hand", 1)
