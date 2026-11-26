"""語彙パイロット第377弾: battle_power_against_specific_civ。

センサス（rejects 1,956件を取り直し）: pure 1,808 / multi 130 /
空 gaps 18。範囲内の pure は大半が1件ファミリーで、新規機構が
必要なものが大半を占める。却下候補:
- unblockable_while_condition（dm23bd4-030）: 条件付き条項が
  4つ連なり partial に素体以外ほぼ何も組まれていない。
- conditional_s_trigger_grant（dm23rp3-004）/
  s_trigger_grant_condition（dm26rp3-sp001）: ターン履歴・革命2
  条件＋未構築の重いモーダル呪文面。
- power_threshold_keyword_gain（dm24-011）: 現在パワーで変わる
  キーワード付与＋未構築条項。
- attack_condition（dmx19-s04）: ターン履歴（このターン
  ブロッカーを出したか）を前提とする攻撃可否。
- summon_from_mana_once（dm24ex3-037）: partial 自身が
  「ターン1回消費をエンジンが追跡していない」と明記。
- draw_until_count（dm24ex3-rp1s03）: 超次元面の攻撃誘発
  「手札が5枚になるまで引いてもよい」でリスクが高い。
- deny_g_strike_during_attack（dm26ex2-044）: 超魂X 付与＋
  攻撃中スコープの deny。
- deck_rule（dmx22b-110）: デッキ条項は dmex13-057 先例で
  テキストのみだが、partial が stub でパワー条項も未構築。
  次点として残す。

選定: battle_power_against_specific_civ（pure 1件のみ、
multi にも現れない）— dmd05-001 無限鉄拳オニナグリ。
第122弾で確立した battle_power {amount, opponent_filter}
（対ブロッカー版）と battle_indestructible の
opponent_filter {civs: [fire]}、第349弾の opponent_filter
{race_has: ゼニス}、第351弾 battle_power_against_specific_race
（同じ形の種族版）と同形で、文明フィルタ版は完全なドリフト。
新規語彙なし・エンジン変更なし。

公式テキスト:
「マナゾーンに置く時、このカードはタップして置く。／
進化-自分のハンター・クリーチャー１体の上に置く。／
光のクリーチャーとバトル中、このクリーチャーのパワーは
+2000される。／このクリーチャーがバトルに勝った時、この
クリーチャーをアンタップする。／W・ブレイカー」
- 「マナゾーンに置く時タップして置く」は多色ルールの
  リマインダで canonical が吸収する（登録済み383件が
  テキストのみで保持）。語彙は不要。
- 「バトル中」（only 無し）は攻撃・防御の両バトルに効く
  （第122弾周辺の確立解釈どおり）。
partial は完成形に近く、組まれているのは battle_win
アンタップ誘発のみ。未解決は unsupported の
battle_power_against_specific_civ 1件だけ。alias は無い。
単面カードで未検証の面は無い。

確立形:
- static {affects: self, mod: {battle_power:
  {amount: 2000, opponent_filter: {civs: [light]}}}}
  （公式テキストの条項順に合わせ、既存のアンタップ誘発の
  前に置く）
defs.py の battle_power 検証は opponent_filter を
filter 検証に通し、schema.py の battle_power 定義にも
opponent_filter がある（第408弾の教訓で同期を確認済み。
スキーマ再生成は不要）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.split
（対象行）は (["double_breaker"], 残りテキスト, []) を返し、
定型所有は abilities 側に無い。ラウンド412は通常どおり
submit できる見込み。

プロト: T1125 = dmd05-001 型。T1126 = 光・パワー8000
ブロッカー（素7000では負け、+2000で勝つ判別役）、
T1127 = 火・パワー8000ブロッカー（対照役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
バトルゾーンは共有ゾーンなので所有は bz_tops(p) /
zlist(zone, p) で見る。parse_card は double_breaker
キーワードを breaks 常在型に展開するので、parse 後の
abilities は包含で確認する（第372弾の作法）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

STATIC = {"kind": "static", "affects": "self",
          "mod": {"battle_power": {"amount": 2000,
                                   "opponent_filter": {"civs": ["light"]}}}}
UNTAP = {"kind": "trigger",
         "when": {"event": "battle_win", "subject": "self"},
         "effect": [{"op": "untap", "select": {"ref": "self"}}]}
FORM = [STATIC, UNTAP]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form():
    proto = proto_card("T1125")
    assert proto["abilities"] == FORM
    assert proto["evolve_from"] == {"races": ["ハンター"]}
    assert proto["mana"] == 1
    d = parse_card(proto, TABLES)
    assert STATIC in d.abilities and UNTAP in d.abilities
    assert d.types == ["creature", "evolution"]
    assert d.civs == ["darkness", "fire"]
    assert d.cost == 6 and d.power == 7000
    assert d.races == ["ヒューマノイド", "ハンター", "エイリアン"]
    assert d.keywords == ["double_breaker"]


def test_bad_opponent_filter_civ_rejected():
    bad = dict(proto_card("T1125"))
    bad["abilities"] = [{"kind": "static", "affects": "self",
                         "mod": {"battle_power":
                                 {"amount": 2000,
                                  "opponent_filter": {"civs": ["bogus"]}}}}]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _attack_and_block(e, attacker, blocker, state):
    """p0 の attacker がプレイヤーを攻撃し、block 判断が
    出たら blocker でブロックする。p1 の charge まで進める。"""
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 1:
            return
        if d["kind"] == "attack" and d.get("player") == 0 \
                and not state.get("attacked"):
            tgt = [k for k in keys
                   if k == f"attack:{attacker}:player"]
            if tgt:
                state["attacked"] = True
                e.answer([keys.index(tgt[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "block":
            state["block_decision"] = keys
            pick = [i for i, k in enumerate(keys)
                    if k.startswith(f"bz:{blocker}")]
            if pick:
                state["blocked"] = True
                e.answer([pick[0]])
            else:
                e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("attack never finished")


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def test_beats_light_blocker_with_bonus(rules):
    # 光ブロッカー8000: 素7000では負けるが +2000=9000 で勝つ
    e = _build(rules, {"bz": ["T1125"]}, {"bz": ["T1126"]})
    state = {}
    _attack_and_block(e, "T1125", "T1126", state)
    assert state.get("attacked") and state.get("blocked"), state
    assert "T1126" in _defns(e, "graveyard", 1)
    assert "T1125" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    # バトルに勝ったので partial 既存のアンタップ誘発も発火する
    cid = next(c for c in e.zlist("bz", 0)
               if e.s.cards[c].defn == "T1125")
    assert not e.s.cards[cid].tapped


def test_loses_to_non_light_blocker(rules):
    # 火ブロッカー8000: 文明フィルタに合わず +2000 は付かない
    e = _build(rules, {"bz": ["T1125"]}, {"bz": ["T1127"]})
    state = {}
    _attack_and_block(e, "T1125", "T1127", state)
    assert state.get("attacked") and state.get("blocked"), state
    assert "T1125" in _defns(e, "graveyard", 0)
    assert "T1127" in [e.s.cards[c].defn for c in e.bz_tops(1)]
