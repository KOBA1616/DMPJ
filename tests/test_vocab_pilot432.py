"""語彙パイロット第432弾: mana_leave_trigger（ドリフト）。

センサス（rejects 1,899件を取り直し）: pure 1,751件
（987家族）/ multi 130件 / 空 gaps 18件。pure の大半は
範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。評価済み却下（第316〜320・
355〜431弾）は原則として再提案しない。残置群
（graveyard_replacement 残り dm25ex2-cho021、
battle_opponent_reference 残り dmr01-049、
untap_restriction 残り2件、does_not_untap 残り
dm25ex2-031、cast_limit_once_per_turn の multi 2件、
summoning_attack_rule 残り dmex07-s01、
entered_turn_attack 残り dmbd11-d05、madness 残り
dmx26-028、after_battle_trigger 残り dmrp09-074、
次点の destroyed_this_turn_condition /
count_cards_drawn_this_turn、後続候補の
distinct_civ_count、将来の新規語彙候補 first_time_tap /
turn_history_entry、専用ステージ送りの
power_threshold_keyword_gain）は覆す根拠が無く
再提案しない。本弾で個別に評価して見送った候補:
same_name_bounce（dmrp04m-048。選択カードへの動的
名参照が selector 側に未確立）、mill_as_breaks
（dmr16g-028。count 式の from_top 対応と breaks_add
への var 束縛の組み合わせが未検証で重い）、
hand_add_event（dmrp04s-s04。from 側の否定照合と
当該カードへの無償詠唱付与が未確立）、
shield_added_condition（dmrp03-048。シールドが
手札に加えられた回数の履歴照合が未確立）、
free_cast_trigger（dmrp12-055。手札ゾーンの攻撃
誘発＋履歴条件の組み合わせが未検証）。

範囲内・最小の **mana_leave_trigger（pure 1件、
multi にも現れない）** を選定した。行の注記「マナ
離脱の照合を表す語彙が無い」は陳腐化した評価で、
全条項が確立部品の組み合わせで表せる（ドリフト。
新規語彙・エンジン・defs・スキーマ変更なし）:
- 「相手のマナゾーンからカードが離れる時」は
  trigger {when: {event: move, from: mana, subject:
  {owner: opp}}}。from: mana の移動監視誘発は
  登録済み dm28-014（自軍マナ・宛先無指定）/
  dm17-030（owner: any）の確立形で、宛先を絞らない
  点も dm28-014 と同じ。
- 「相手のターン中」は if {is_turn: opp}。登録済み
  dm23-027 が move 誘発＋is_turn: opp＋相手シールド
  選択の近接先例を保持する。is_turn は defs 検証・
  selectors 評価・rustcore の三方に定義済み。
- 「相手のシールドをひとつ選び、持ち主の手札に
  加える」は move {select: {zone: shield, owner:
  opp, count: 1}, to: hand, reason: return}。
  シールド→手札の move は登録済み dmex13-073
  （自軍版）の確立形。選択主体は既定でコントローラー
  （相手が選ぶ dm23-027 は chooser: opp を明示する
  のと対照的に、本件は文面どおり自分が選ぶ）。

対象は dmr05-032 メガンス・ワイバーン（火 /
コスト5 / パワー5000 / 種族 アーマード・ワイバーン/
アンノイズ / mana 1）。partial は骨格のみで text は
断片。**補完あり: text（公式全文）＋abilities**。
alias は無し（identity 実測で canon_id は対象自身、
aliases_for = []）。第432弾時点で real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも対象 id は
登録なし。登録ブロッカーの確認（第375弾の教訓）:
rule_convert.split（対象行）は None を返し定型所有は
無い＝ツール側ブロッカーなし。単面カードで未検証の
面は無い。

結論はドリフト: abilities 1件 =
trigger {when: {event: move, from: mana, subject:
{owner: opp}}, if: {is_turn: opp}, effect:
[move {select: {zone: shield, owner: opp, count: 1},
to: hand, reason: return}]}。

proto T1213（dmr05-032 型）。判別役は本弾で追加:
T1214（相手が自分のマナを手札に戻す呪文＝相手
ターン中の離脱）/ T1215（自分のターンに相手の
マナを墓地に置く呪文＝is_turn の判別）/ T1216
（相手が自分のマナ2枚を戻す呪文＝2回誘発の判別）/
T001（通常召喚＝タップだけでは離脱しない判別）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の
作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import (  # noqa: E402
    DefError, load_rules, load_tables, parse_card)
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

TRIGGER = {"kind": "trigger",
           "when": {"event": "move", "from": "mana",
                    "subject": {"owner": "opp"}},
           "if": {"is_turn": "opp"},
           "effect": [{"op": "move",
                       "select": {"zone": "shield", "owner": "opp",
                                  "count": 1},
                       "to": "hand", "reason": "return"}]}
FORM = [TRIGGER]
FULL_TEXT = ("相手のターン中、相手のマナゾーンからカードが離れる時、"
             "相手のシールドをひとつ選び、持ち主の手札に加える。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1213")
    assert c["name"] == "メガンス・ワイバーン"
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 5 and c["power"] == 5000 and c["mana"] == 1
    assert c["races"] == ["アーマード・ワイバーン", "アンノイズ"]
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(copy.deepcopy(c), TABLES)
    assert TRIGGER in d.abilities   # parse で形は変わらない
    for tid in ("T1214", "T1215", "T1216", "T001"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX432", "name": "メガンス・ワイバーン",
                    "types": ["creature"], "civs": ["fire"],
                    "cost": 5, "power": 5000, "mana": 1,
                    "races": ["アーマード・ワイバーン", "アンノイズ"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert TRIGGER in d.abilities


def _bad(mutate):
    c = {"id": "TX432B", "name": "x", "types": ["creature"],
         "civs": ["fire"], "cost": 5, "power": 5000, "mana": 1,
         "abilities": copy.deepcopy(FORM)}
    mutate(c["abilities"][0])
    with pytest.raises(DefError):
        parse_card(c, TABLES)


def test_bad_forms_rejected():
    # when の未知イベントは DefError
    _bad(lambda a: a["when"].update({"event": "moved"}))
    # is_turn は you/opp のみ（defs の明示検証）
    _bad(lambda a: a.update({"if": {"is_turn": "any"}}))
    # effect の未知 op は DefError
    _bad(lambda a: a.update(
        {"effect": [{"op": "movee",
                     "select": {"zone": "shield", "owner": "opp",
                                "count": 1},
                     "to": "hand", "reason": "return"}]}))


# ---------- 駆動ヘルパ ----------

def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _play_and_settle(e, player, play_key, limit=600):
    """player の main 判断で play_key を一度だけ使い、
    解決が終わって通常判断（main / charge / attack）に
    戻るまで進める。使えたかどうかを返す。"""
    cast = False
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if not cast and d["kind"] == "main" \
                and d.get("player") == player and play_key in keys:
            e.answer([keys.index(play_key)])
            cast = True
            continue
        if cast and d["kind"] in ("main", "charge", "attack"):
            return True
        _answer_default(e, d)
    return cast


def test_opp_mana_leaves_on_opp_turn_adds_shield_to_hand(rules):
    """相手のターンに相手のマナゾーンからカードが
    離れると、相手のシールドを1つ選んで持ち主の
    手札に加える（シールド5→4、手札は開始1＋ドロー1
    −呪文1＋マナ回収1＋シールド1＝3、マナ4→3）。"""
    e = _build(rules, {"bz": ["T1213"]},
               {"hand": ["T1214"], "mana": ["T002"] * 4})
    assert _play_and_settle(e, 1, "play:T1214")
    assert len(e.zlist("shield", 1)) == 4
    assert len(e.zlist("hand", 1)) == 3
    assert len(e.zlist("mana", 1)) == 3


def test_opp_mana_leaves_on_your_turn_no_trigger(rules):
    """判別: 自分のターンに相手のマナゾーンから
    カードが離れても、is_turn: opp でないため誘発
    しない（相手のシールドは5枚のまま）。"""
    e = _build(rules, {"bz": ["T1213"], "hand": ["T1215"],
                       "mana": ["T002"] * 2},
               {"mana": ["T002"] * 3})
    assert _play_and_settle(e, 0, "play:T1215")
    assert len(e.zlist("mana", 1)) == 2        # マナは墓地に置かれた
    assert len(e.zlist("graveyard", 1)) == 1
    assert len(e.zlist("shield", 1)) == 5      # 誘発していない


def test_tapping_mana_does_not_trigger(rules):
    """判別: 相手が通常召喚でマナをタップしただけ
    ではカードはマナゾーンを離れないので誘発しない
    （シールド5枚・マナ4枚のまま）。"""
    e = _build(rules, {"bz": ["T1213"]},
               {"hand": ["T001"], "mana": ["T002"] * 4})
    assert _play_and_settle(e, 1, "play:T001")
    assert len(e.bz_tops(1)) == 1             # 召喚は成立している
    assert len(e.zlist("mana", 1)) == 4
    assert len(e.zlist("shield", 1)) == 5


def test_two_mana_leaves_trigger_twice(rules):
    """相手のマナゾーンから2枚離れれば2回誘発し、
    シールドは2枚手札に加わる（5→3）。"""
    e = _build(rules, {"bz": ["T1213"]},
               {"hand": ["T1216"], "mana": ["T002"] * 4})
    assert _play_and_settle(e, 1, "play:T1216")
    assert len(e.zlist("shield", 1)) == 3
    assert len(e.zlist("mana", 1)) == 2
    assert len(e.zlist("hand", 1)) == 5   # 開始1＋ドロー1−1呪文＋2マナ＋2シールド


def test_no_target_in_bz_no_trigger(rules):
    """発生源がバトルゾーンに無ければ誘発しない
    （相手のシールドは5枚のまま）。"""
    e = _build(rules, {},
               {"hand": ["T1214"], "mana": ["T002"] * 4})
    assert _play_and_settle(e, 1, "play:T1214")
    assert len(e.zlist("shield", 1)) == 5
    assert len(e.zlist("mana", 1)) == 3
    assert len(e.zlist("hand", 1)) == 2   # 開始1＋ドロー1−1呪文＋1マナのみ


def test_no_shields_no_error(rules):
    """相手のシールドが0枚でも誘発は空振りして
    ゲームは正常に進む。"""
    e = _build(rules, {"bz": ["T1213"]},
               {"hand": ["T1214"], "mana": ["T002"] * 4,
                "shield": []})
    assert _play_and_settle(e, 1, "play:T1214")
    assert len(e.zlist("shield", 1)) == 0
    assert len(e.zlist("mana", 1)) == 3
    assert len(e.zlist("hand", 1)) == 2   # 開始1＋ドロー1−1呪文＋1マナのみ
