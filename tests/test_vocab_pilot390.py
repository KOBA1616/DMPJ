"""語彙パイロット第390弾: placed_this_turn_condition（ドリフト）。

センサス（rejects 1,943件を取り直し）: pure 1,795件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜389弾）は再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021 と
battle_opponent_reference の残り1件 dmr01-049 は
先行弾の評価を覆す根拠が無く再提案しない。本弾で
個別に評価して見送った候補: enters_tapped_rule
（pure 1、dmex11-005。2条項構成で、第1条項は
コスト3以下の自分のクリーチャーへの speed_attacker
付与、第2条項は相手の進化／speed_attacker 持ちへの
enters_tapped 付与＝フィルタの OR 条件が要り、
partial も stub で text が断片のみ）、
count_cards_drawn_this_turn（pure 1、dm12-010。
turn_count {kind: draw} はあるが、相手のターン終了時
誘発＋相手の手札全捨ての組み立ての検証が要る）、
mana_placed_count_this_turn（pure 1、dmrp06-027。
move to: mana 誘発の if で「その置き方自体を含む
ターン内 mana_put 回数」を評価するタイミング意味論の
検証が要る）、drew_this_turn_condition（pure 1、
dmx22b-038。G・ゼロの条件形の検証が要る）、
shield_added_condition（pure 1、dmrp03-048。
ターン終わりの手札宣言＋shield_left 系カウントの
意味論検証が要る）、destroy_after_battle（pure 1、
dm07-003。起動効果で付与した「このターンにバトルした
自分の闇のクリーチャーはバトルの後に墓地へ」の
継続的効果は、バトルの両側を対象にする遅延効果の
新設が要る）。範囲内・未評価で最小の
placed_this_turn_condition（pure 1件、multi にも
現れない）を選定した。

対象は pure 1件すべて: dmsd07-003 ハンマノ裁徒
（光 / コスト4 / パワー6000 / メタリカ・サバキスト）。
公式テキストは「ブロッカー」「W・ブレイカー」の
キーワード2件と単一条項:
「このターン中にカードが自分のシールドゾーンに
置かれていなければ、このクリーチャーは相手
プレイヤーを攻撃できない。」

結論は完全なドリフト（新規語彙・エンジン・defs・
スキーマ変更なし）:

- 同一条項が登録済み **dmrp08-032 ブロクノ裁徒Z**
  （第205ラウンド登録、同じ裁徒系）の第1能力として
  登録形そのままにある:
  static {affects: self, if: {cmp: [{turn_count:
  {kind: shield_put, owner: you}}, "==", 0]},
  mod: {deny: [attack_player]}}。
  test_vocab_pilot169_cards.py の
  test_dmrp08_032_attack_denied_until_shield_put が
  その特性を固定済み。
- shield_put は履歴 kind として既存（defs の
  TURN_COUNT_KINDS 収載、schema.py は同 enum を
  defs から import し生成済み card.schema.json にも
  収載＝第408ラウンドの教訓どおり両側を確認）。
  events._record_history が move to: shield の
  レコードを置かれたカードのコントローラで集約する
  （hist:shield_put:<controller>）。owner: you は
  「自分のシールドゾーンに置かれた」枚数と一致する。
- deny は attack_player のみ（テキストは「相手
  プレイヤーを攻撃できない」で、クリーチャー攻撃は
  可能。第382弾の両方 deny との判別点）。
- 「条件を満たさない間は攻撃できない」の常在形自体も
  第382弾（promoy21-051 先例と同型）で確立済み。

確立形: abilities = [static {affects: self, if:
{cmp: [{turn_count: {kind: shield_put, owner: you}},
"==", 0]}, mod: {deny: [attack_player]}}] の1件。

partial は骨格完備（keywords [blocker,
double_breaker]、abilities 無し）で、text は行の
公式テキスト全文と一致する（**補完なし**）。
alias は無い。単面カードで未検証の面は無い。
登録ブロッカーの確認（第375弾の教訓）:
rule_convert.split（対象行）は (keywords, text, [])
を返し、part[2] の定型所有は空＝ブロッカー無し
（本弾で実測）。

proto T1155（dmsd07-003 型）。判別役は既存 proto
T245（自盾追加試験呪文: 自分の山札の上から1枚を
自分の新しいシールドとして置く。実フローで
shield_put を起こす役）を流用する。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の作法）。
バトルゾーンは共有ゾーンなので所有は bz_tops(p) /
zlist(zone, p) で見る。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

STATIC = {"kind": "static", "affects": "self",
          "if": {"cmp": [{"turn_count": {"kind": "shield_put",
                                         "owner": "you"}},
                         "==", 0]},
          "mod": {"deny": ["attack_player"]}}
FORM = [STATIC]
FULL_TEXT = ("ブロッカー（このクリーチャーをタップして、相手クリーチャーの"
             "攻撃先をこのクリーチャーに変更してもよい）\n"
             "このターン中にカードが自分のシールドゾーンに置かれて"
             "いなければ、このクリーチャーは相手プレイヤーを攻撃できない。\n"
             "W・ブレイカー（このクリーチャーはシールドを２つブレイクする）")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1155")
    assert c["name"] == "ハンマノ裁徒"
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 4 and c["power"] == 6000 and c["mana"] == 1
    assert c["races"] == ["メタリカ", "サバキスト"]
    assert c["keywords"] == ["blocker", "double_breaker"]
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities      # keywords は static に展開される
    parse_card(proto_card("T245"), TABLES)


def test_bad_forms_rejected(rules):
    # turn_count の kind は TURN_COUNT_KINDS の列挙で検証され、
    # 未知の kind（shield_placed は誤記）は DefError
    bad = copy.deepcopy(proto_card("T1155"))
    bad["abilities"] = [{"kind": "static", "affects": "self",
                         "if": {"cmp": [{"turn_count":
                                         {"kind": "shield_placed",
                                          "owner": "you"}}, "==", 0]},
                         "mod": {"deny": ["attack_player"]}}]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # owner: any は kind destroyed / attack だけ（shield_put では DefError）
    bad2 = copy.deepcopy(proto_card("T1155"))
    bad2["abilities"] = [{"kind": "static", "affects": "self",
                          "if": {"cmp": [{"turn_count":
                                          {"kind": "shield_put",
                                           "owner": "any"}}, "==", 0]},
                          "mod": {"deny": ["attack_player"]}}]
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "yes_no":
        e.answer([keys.index("yes")] if "yes" in keys
                 else list(range(d["min"])))
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _mine(e, defn="T1155"):
    return next(c for c in e.zlist("bz", 0)
                if e.s.cards[c].defn == defn)


def test_denied_without_shield_put(rules):
    # このターンに自分のシールドゾーンにカードが置かれて
    # いなければ、プレイヤー攻撃だけができない
    # （クリーチャー攻撃は可能＝deny の範囲の判別）
    e = _build(rules, {"bz": ["T1155"]}, {"bz": []})
    cid = _mine(e)
    assert not e.permits(cid, "attack_player")
    assert e.permits(cid, "attack_creature")
    assert not any(o["key"].startswith("attack:T1155")
                   for o in e._attack_options(0))


def test_opponent_shield_put_does_not_unlock(rules):
    # owner: you の判別: 相手の shield_put カウントでは
    # 解放されず、自分のカウントで解放される
    # （第169弾 cards の dmrp08-032 テストと同じ特性レベルの作法）
    e = _build(rules, {"bz": ["T1155"]}, {"bz": []})
    cid = _mine(e)
    e.s.turn_counters["hist:shield_put:1"] = 1   # 相手が置いた分
    assert not e.permits(cid, "attack_player")
    e.s.turn_counters["hist:shield_put:0"] = 1   # 自分が置いた分
    assert e.permits(cid, "attack_player")


def test_unlocked_by_real_shield_put_and_breaks(rules):
    # 実フロー: T245（自盾追加試験呪文）を唱えて自分の
    # 山札の上から1枚を自分の新しいシールドとして置くと、
    # 同じターンにハンマノ裁徒がプレイヤーを攻撃でき、
    # W・ブレイカーでシールドを2枚ブレイクする
    e = _build(rules, {"bz": ["T1155"], "hand": ["T245", "T002"],
                       "mana": ["T001", "T001"]},
               {"bz": []})
    cid = _mine(e)
    assert not e.permits(cid, "attack_player")
    shields_before = len(e.zlist("shield", 1))
    own_shields_before = len(e.zlist("shield", 0))
    state = {}
    for _ in range(4000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and not state.get("cast"):
            assert "play:T245" in keys, keys
            state["cast"] = True
            e.answer([keys.index("play:T245")])
            continue
        if state.get("cast") and not state.get("checked"):
            # 呪文の解決後、次の判断の時点で shield_put が記録され、
            # プレイヤー攻撃が解放されている
            if d["kind"] in ("main", "attack"):
                state["checked"] = True
                assert e.s.turn_counters.get("hist:shield_put:0") == 1
                assert len(e.zlist("shield", 0)) == own_shields_before + 1
                assert e.permits(cid, "attack_player")
        if d["kind"] == "attack" and d.get("player") == 0 \
                and state.get("checked") and not state.get("attacked"):
            assert "attack:T1155:player" in keys, keys
            state["attacked"] = True
            e.answer([keys.index("attack:T1155:player")])
            continue
        if state.get("attacked") and d["kind"] == "charge":
            break   # 攻撃は解決済み（次のターンの charge）
        _answer_default(e, d)
    assert state.get("cast") and state.get("checked"), state
    assert state.get("attacked"), state
    assert len(e.zlist("shield", 1)) == shields_before - 2  # W・ブレイカー
    assert e.s.cards[cid].tapped is True


def test_counter_resets_next_turn(rules):
    # カウンタはターン開始にリセットされる: 置いたターンに
    # 解放されても、次の自分のターンでは再び攻撃できない
    e = _build(rules, {"bz": ["T1155"]}, {"bz": []})
    cid = _mine(e)
    e.s.turn_counters["hist:shield_put:0"] = 1
    assert e.permits(cid, "attack_player")
    state = {}
    for _ in range(6000):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] == "charge" and d.get("player") == 1:
            state["opp_turn"] = True
        elif d["kind"] == "charge" and d.get("player") == 0 \
                and state.get("opp_turn"):
            break   # 自分の次のターンに入った
        _answer_default(e, d)
    assert state.get("opp_turn"), state
    assert not e.s.turn_counters.get("hist:shield_put:0")
    assert not e.permits(cid, "attack_player")
