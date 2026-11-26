"""語彙パイロット第433弾: opponent_mana_trigger（ドリフト）。

センサス（rejects 1,898件を取り直し）: pure 1,750件
（986家族）/ multi 130件 / 空 gaps 18件。pure の大半は
範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。評価済み却下（第316〜320・
355〜432弾）は原則として再提案しない。残置群
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
cast_event_trigger（dmr23-006。詠唱イベントの
subject への cost 比較を selector フィルタに入れる
形が未検証の複合）、attack_event_trigger
（dmrp07-026。partial が骨格のみで全条項が未構築で
重い）、turn_draw_trigger（dm14-039。turn_draw
フラグは第219弾で存在するが、効果の行為主体が
「引いたプレイヤー」に切り替わる形が未確立）、
mana_enters_untapped（dm25-028。多色マナ配置の
タップ状態を変える置換の確立形が無い）、
last_shield_trigger（dmx26-v01。「最後の1枚」の
照合が未検証＋進化＋全体タップの複合）。

範囲内・最小の **opponent_mana_trigger（pure 1件、
multi にも現れない）** を選定した。行の注記「相手の
マナ置きを照合する語彙が無い」は陳腐化した評価で、
全条項が確立部品の組み合わせで表せる（ドリフト。
新規語彙・エンジン・defs・スキーマ変更なし）:
- 「相手の山札または墓地から、カードがマナゾーンに
  置かれた時」は trigger {when: {event: move,
  to: mana, from: [deck, graveyard], subject:
  {owner: opp}}}。to: mana の移動監視誘発は第397弾
  （登録済み dmrp06-027 等、subject {owner: you}）の
  確立形、from のリスト指定は defs の when 検証
  （リスト＝いずれか）とエンジン _match_when の
  両側で対応済み。手札からのマナチャージは
  from: hand のため対象外で、文面どおり山札／
  墓地のみに絞れる。
- 「相手は自身のマナゾーンからカードを1枚選んで
  山札の一番下に置く」は move {select: {zone: mana,
  owner: opp, count: 1, chooser: opp}, to: deck,
  reason: put, position: bottom}。chooser: opp は
  selector の既存キー（defs SELECTOR_KEYS と
  schema.py の両側に定義済み。第432弾で対照した
  dm23-027 の明示形）、山札の一番下への move は
  登録済みニンジャ・ストライク形（dm22bd1-017 等）
  の確立形。

対象は dm39-015 穿神兵ジェットドリル（火 /
コスト3 / パワー2000 / 種族 アーマロイド / mana 1）。
partial は骨格のみで text は断片。**補完あり:
text（公式全文）＋abilities**。alias は無し
（identity 実測で canon_id は対象自身、
aliases_for = []）。第433弾時点で real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも対象 id は
登録なし。登録ブロッカーの確認（第375弾の教訓）:
rule_convert.split（対象行）は None を返し定型所有は
無い＝ツール側ブロッカーなし。単面カードで未検証の
面は無い。

結論はドリフト: abilities 1件 =
trigger {when: {event: move, to: mana,
from: [deck, graveyard], subject: {owner: opp}},
effect: [move {select: {zone: mana, owner: opp,
count: 1, chooser: opp}, to: deck, reason: put,
position: bottom}]}。

proto T1217（dm39-015 型）。判別役は本弾で追加:
T1218（相手の山札の上から相手のマナへ置く呪文＝
山札起点）/ T1219（相手の墓地から相手のマナへ置く
呪文＝墓地起点）/ T1220（相手の手札から相手のマナへ
置く呪文＝from の判別）/ T1221（自分の山札の上から
自分のマナへ置く呪文＝subject owner の判別）/
T1222（相手の山札の上2枚を相手のマナへ置く呪文＝
2回誘発の判別）。

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
           "when": {"event": "move", "to": "mana",
                    "from": ["deck", "graveyard"],
                    "subject": {"owner": "opp"}},
           "effect": [{"op": "move",
                       "select": {"zone": "mana", "owner": "opp",
                                  "count": 1, "chooser": "opp"},
                       "to": "deck", "reason": "put",
                       "position": "bottom"}]}
FORM = [TRIGGER]
FULL_TEXT = ("相手の山札または墓地から、カードがマナゾーンに置かれた時、"
             "相手は自身のマナゾーンからカードを１枚選んで"
             "山札の一番下に置く。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1217")
    assert c["name"] == "穿神兵ジェットドリル"
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 3 and c["power"] == 2000 and c["mana"] == 1
    assert c["races"] == ["アーマロイド"]
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(copy.deepcopy(c), TABLES)
    assert TRIGGER in d.abilities   # parse で形は変わらない
    for tid in ("T1218", "T1219", "T1220", "T1221", "T1222"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX433", "name": "穿神兵ジェットドリル",
                    "types": ["creature"], "civs": ["fire"],
                    "cost": 3, "power": 2000, "mana": 1,
                    "races": ["アーマロイド"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert TRIGGER in d.abilities


def _bad(mutate):
    c = {"id": "TX433B", "name": "x", "types": ["creature"],
         "civs": ["fire"], "cost": 3, "power": 2000, "mana": 1,
         "abilities": copy.deepcopy(FORM)}
    mutate(c["abilities"][0])
    with pytest.raises(DefError):
        parse_card(c, TABLES)


def test_bad_forms_rejected():
    # when の未知イベントは DefError
    _bad(lambda a: a["when"].update({"event": "moved"}))
    # from の未知ゾーンは DefError（リスト要素も検証される）
    _bad(lambda a: a["when"].update({"from": ["deck", "vault"]}))
    # chooser の不正値は DefError（defs の明示検証）
    _bad(lambda a: a["effect"][0]["select"].update(
        {"chooser": "someone"}))
    # effect の未知 op は DefError
    _bad(lambda a: a.update(
        {"effect": [{"op": "movee",
                     "select": {"zone": "mana", "owner": "opp",
                                "count": 1, "chooser": "opp"},
                     "to": "deck", "reason": "put",
                     "position": "bottom"}]}))


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


def _play_and_settle(e, player, play_key, choose=None, record=None,
                     limit=600):
    """player の main 判断で play_key を一度だけ使い、
    解決が終わって通常判断（main / charge / attack）に
    戻るまで進める。choose(d, keys) がインデックス列を
    返せば choose_cards 決定にそれで答える。record には
    choose_cards 決定の提示先プレイヤーを記録する。"""
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
        if cast and d["kind"] == "choose_cards":
            if record is not None:
                record.append(d.get("player"))
            if choose is not None:
                ans = choose(d, keys)
                if ans is not None:
                    e.answer(ans)
                    continue
        if cast and d["kind"] in ("main", "charge", "attack"):
            return True
        _answer_default(e, d)
    return cast


def _pick_defn(defn):
    """相手（player 1）の選択で defn を含むキーを選ぶ。"""
    def choose(d, keys):
        if d.get("player") != 1:
            return None
        hit = [i for i, k in enumerate(keys) if f":{defn}:" in k]
        return hit[:1] or None
    return choose


def test_deck_to_mana_triggers_and_opp_chooses_bottom(rules):
    """相手の山札からカードが相手のマナゾーンに置かれる
    と誘発し、相手自身が選んだマナのカードが山札の
    一番下に置かれる（マナ 3+1-1=3、山札は枚数不変で
    一番下が選んだ T001 になる。選択決定は相手に
    提示される＝chooser: opp の判別）。"""
    e = _build(rules, {"bz": ["T1217"], "hand": ["T1218"],
                       "mana": ["T002"] * 2},
               {"mana": ["T001", "T002", "T002"]})
    deck_before = len(e.zlist("deck", 1))
    record = []
    assert _play_and_settle(e, 0, "play:T1218",
                            choose=_pick_defn("T001"), record=record)
    assert record == [1]                 # 選択は相手に1回だけ提示
    assert len(e.zlist("mana", 1)) == 3
    assert len(e.zlist("deck", 1)) == deck_before
    bottom = e.zlist("deck", 1)[-1]
    assert e.s.cards[bottom].defn == "T001"   # 選んだカードが一番下
    assert all(e.s.cards[c].defn != "T001"
               for c in e.zlist("mana", 1))


def test_graveyard_to_mana_triggers(rules):
    """相手の墓地からカードが相手のマナゾーンに置かれて
    も誘発する（墓地 1→0、マナ 2+1-1=2、置かれた
    カード自体も選択肢に入り、一番下に置ける）。"""
    e = _build(rules, {"bz": ["T1217"], "hand": ["T1219"],
                       "mana": ["T002"] * 2},
               {"mana": ["T002", "T002"], "graveyard": ["T001"]})
    deck_before = len(e.zlist("deck", 1))
    record = []
    assert _play_and_settle(e, 0, "play:T1219",
                            choose=_pick_defn("T001"), record=record)
    # 誘発の選択は相手に1回提示される（呪文の墓地選択は
    # 候補1枚のため自動解決される場合がある）
    assert record.count(1) == 1 and record[-1] == 1
    assert len(e.zlist("graveyard", 1)) == 0
    assert len(e.zlist("mana", 1)) == 2
    assert len(e.zlist("deck", 1)) == deck_before + 1
    bottom = e.zlist("deck", 1)[-1]
    assert e.s.cards[bottom].defn == "T001"


def test_hand_to_mana_does_not_trigger(rules):
    """判別: 相手の手札からカードが相手のマナゾーンに
    置かれても、from: hand は from リストに無いため
    誘発しない（マナは+1、山札は枚数・一番下とも
    不変で、相手への選択提示も無い）。"""
    e = _build(rules, {"bz": ["T1217"], "hand": ["T1220"],
                       "mana": ["T002"] * 2},
               {"mana": ["T002", "T002"], "hand": ["T002"]})
    deck_before = list(e.zlist("deck", 1))
    record = []
    assert _play_and_settle(e, 0, "play:T1220", record=record)
    assert 1 not in record               # 相手への選択提示なし
    assert len(e.zlist("mana", 1)) == 3
    assert e.zlist("deck", 1) == deck_before


def test_own_deck_to_mana_does_not_trigger(rules):
    """判別: 自分の山札から自分のマナゾーンに置いても、
    subject {owner: opp} に一致しないため誘発しない
    （相手のマナ・山札は不変）。"""
    e = _build(rules, {"bz": ["T1217"], "hand": ["T1221"],
                       "mana": ["T002"] * 2},
               {"mana": ["T002", "T002"]})
    p1_mana = list(e.zlist("mana", 1))
    p1_deck = list(e.zlist("deck", 1))
    record = []
    assert _play_and_settle(e, 0, "play:T1221", record=record)
    assert 1 not in record
    assert len(e.zlist("mana", 0)) == 3   # 自分のマナは+1
    assert e.zlist("mana", 1) == p1_mana
    assert e.zlist("deck", 1) == p1_deck


def test_two_puts_trigger_twice(rules):
    """相手の山札から2枚置かれれば2回誘発し、相手は
    2回選んで2枚を山札の一番下に置く（マナ 3+2-2=3、
    山札は枚数不変）。"""
    e = _build(rules, {"bz": ["T1217"], "hand": ["T1222"],
                       "mana": ["T002"] * 2},
               {"mana": ["T002"] * 3})
    deck_before = len(e.zlist("deck", 1))
    record = []
    assert _play_and_settle(e, 0, "play:T1222", record=record)
    assert record == [1, 1]              # 誘発ごとに相手が選ぶ
    assert len(e.zlist("mana", 1)) == 3
    assert len(e.zlist("deck", 1)) == deck_before


def test_no_source_no_trigger(rules):
    """発生源がバトルゾーンに無ければ誘発しない
    （相手のマナは+1、山札は-1で、一番下への
    移動は起きない）。"""
    e = _build(rules, {"hand": ["T1218"], "mana": ["T002"] * 2},
               {"mana": ["T002", "T002"]})
    deck_before = list(e.zlist("deck", 1))
    record = []
    assert _play_and_settle(e, 0, "play:T1218", record=record)
    assert record == []
    assert len(e.zlist("mana", 1)) == 3
    # 山札の一番下は不変（場に発生源が無いため、攻撃
    # ステップが自動で進み相手のターンドローが挟まる
    # ので、枚数ではなく一番下の cid で判別する）
    assert e.zlist("deck", 1)[-1] == deck_before[-1]
