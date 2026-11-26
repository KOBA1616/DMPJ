"""語彙パイロット第378弾: battle_power_against_high_power。

センサス（rejects 1,955件を取り直し）: pure 1,807 / multi 130 /
空 gaps 18。pure の大半は範囲外（gr_summon 147 / aura 108＝
未承認 / hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。残りは
pure 1件の小家族が多数。評価済み却下（第316〜320・355〜377弾）
は再提案しない。本弾で個別に評価して見送った候補:
- deck_rule（dmx22b-110。第377弾の次点）: デッキ条項は
  dmex13-057 先例でテキストのみで済むが、「他のアウトレイジ犬
  1匹につきパワー+1111」は常在型 mod power {amount, count} ＋
  セレクタ exclude {ref: self} の候補形はあるものの、bz を
  数える count の登録先例は墓地数えのみで、自己除外つきの
  実挙動検証が要る。次点として残す。
- mana_all_civilizations（dm26ex3-033）: 「生徒会組カードを
  実行する時」にスコープされた支払い許可で、第260弾の常在
  キー mana_all_civs（無条件）では表せない。
- double_power（dmex19-m5）: partial が無く、アバレチェーンの
  テキスト書き換え条項が残る。
- destroy_after_battle（dm07-003）: そのターンにバトルした
  自分の闇クリーチャーすべてへの遅延破壊付与で、バトル参加の
  追跡が要る。
- no_untap_rule（dmex08-207）: partial が stub で CIP 自己
  タップとドロー置換アンタップも未構築。
- no_untap_grant（dmex18-034）: アンタップ否定の付与形が
  無く、サバイバーの oS 付与も未構築。
- shield_cycle（dmex01-078）: partial が stub で、シールドの
  山札下戻し＋新規シールド設置＋シールド追加誘発が未構築。
- s_trigger_grant_all（dmr16s-s01）: partial が stub で
  セイバー付与条項も未構築。
- untap_unless_destroy（dmrp03-042）: アンタップステップで
  自分のクリーチャーを破壊する選択に結び付ける機構が無い。
- trigger_after_battle_win_or_lose（dm10-013）: partial 自身が
  「遅延誘発で待てるのは battle_win だけ」と明記。battle_lose
  側の遅延イベントが無い。
- all_mana_multicolor_cond（dmrp10-030）: partial が x/y の
  仮面 stub でツインパクト形が未構築。

選定: battle_power_against_high_power（pure 1件のみ、
multi にも現れない）— dmd15-003 超竜サンバースト・NEX。
第122弾で確立した battle_power {amount, opponent_filter} の
パワー閾値版で、第377弾（文明フィルタ版）と同形の完全な
ドリフト。filter の power_ge は FILTER_KEYS にあり、
filter_match は相手の特性パワー（chars）で照合する。
新規語彙なし・エンジン変更なし。

公式テキスト:
「進化-自分のアーマード・ドラゴン１体の上に置く。／
このクリーチャーがバトルに勝った時、このクリーチャーを
アンタップしてもよい。／パワー12000以上のクリーチャーと
バトル中、このクリーチャーのパワーは+11000される。／
W・ブレイカー」
- 「バトル中」（only 無し）は攻撃・防御の両バトルに効く
  （第122・377弾の確立解釈どおり）。本弾で攻撃側・
  防御側の両方を実挙動で判別する（対象カードは
  ブロッカーを持たないため、防御側はタップ状態で
  攻撃される形で見る）。
- 閾値の照合は相手の現在パワー（特性値）であり、印刷
  パワーではない。filter_match の power_ge は chars の
  power を見る。
partial は完成形に近く、組まれているのは battle_win の
may アンタップ誘発のみ。未解決は unsupported の
battle_power_against_high_power 1件だけ。alias は
dmc62-002 / dmc67-004 / promoy11-027 / promoy8-010
（いずれも rejects に独自行は無い）。text は行の公式
テキスト全文と一致（補完なし）。単面カードで未検証の
面は無い。

確立形:
- static {affects: self, mod: {battle_power:
  {amount: 11000, opponent_filter: {power_ge: 12000}}}}
  （公式テキストの条項順に合わせ、既存のアンタップ誘発の
  後に置く）
defs.py の battle_power 検証は opponent_filter を
filter 検証に通し、schema.py の battle_power 定義にも
opponent_filter があり、filter 定義に power_ge がある
（第408弾の教訓で同期を確認済み。スキーマ再生成は不要）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.split
（対象行）は (["double_breaker"], 残りテキスト, []) を返し、
定型所有は abilities 側に無い。ラウンド413は通常どおり
submit できる見込み。

プロト: T1128 = dmd15-003 型。T1129 = 水・パワー12000
ブロッカー（素11000では負け、+11000 で勝つ判別役。
防御側の判別では攻撃役にも使う）、T1130 = 水・
パワー11000ブロッカー（閾値未満で加算が付かず相打ちに
なる対照役）。

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

UNTAP = {"kind": "trigger",
         "when": {"event": "battle_win", "subject": "self"},
         "effect": [{"op": "may", "body": [
             {"op": "untap", "select": {"ref": "self"}}]}]}
STATIC = {"kind": "static", "affects": "self",
          "mod": {"battle_power": {"amount": 11000,
                                   "opponent_filter": {"power_ge": 12000}}}}
FORM = [UNTAP, STATIC]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form():
    proto = proto_card("T1128")
    assert proto["abilities"] == FORM
    assert proto["evolve_from"] == {"races": ["アーマード・ドラゴン"]}
    assert proto["mana"] == 1
    d = parse_card(proto, TABLES)
    assert STATIC in d.abilities and UNTAP in d.abilities
    assert d.types == ["creature", "evolution"]
    assert d.civs == ["fire"]
    assert d.cost == 7 and d.power == 11000
    assert d.races == ["アーマード・ドラゴン"]
    assert d.keywords == ["double_breaker"]


def test_bad_opponent_filter_rejected():
    bad = dict(proto_card("T1128"))
    bad["abilities"] = [{"kind": "static", "affects": "self",
                         "mod": {"battle_power":
                                 {"amount": 11000,
                                  "opponent_filter": {"bogus": 1}}}}]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _battle(e, attacker_p, attacker, blocker):
    """attacker_p の attacker がプレイヤーを攻撃し、相手が
    blocker でブロックする。バトルが終わって attacker_p の
    次の charge が来たら戻る。may 判断は yes を選ぶ。"""
    state = {}
    for _ in range(3000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == attacker_p \
                and state.get("blocked"):
            return state
        if d["kind"] == "yes_no":
            state.setdefault("yes_no", []).append(keys)
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d["min"])))
        elif d["kind"] == "attack" and d.get("player") == attacker_p \
                and not state.get("attacked"):
            tgt = [k for k in keys if k == f"attack:{attacker}:player"]
            if tgt:
                state["attacked"] = True
                e.answer([keys.index(tgt[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "block":
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
    raise AssertionError("battle never finished")


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _tops(e, p):
    return [e.s.cards[c].defn for c in e.bz_tops(p)]


def test_beats_12000_blocker_with_bonus(rules):
    # パワー12000ブロッカー: 素11000では負けるが
    # +11000=22000 で勝ち、may アンタップ誘発も発火する
    e = _build(rules, {"bz": ["T1128"]}, {"bz": ["T1129"]})
    state = _battle(e, 0, "T1128", "T1129")
    assert state.get("attacked") and state.get("blocked"), state
    assert "T1129" in _defns(e, "graveyard", 1)
    assert "T1128" in _tops(e, 0)
    cid = next(c for c in e.zlist("bz", 0)
               if e.s.cards[c].defn == "T1128")
    assert not e.s.cards[cid].tapped   # may でアンタップした


def test_no_bonus_below_threshold(rules):
    # パワー11000ブロッカー: 閾値12000未満なので加算は
    # 付かず、11000 vs 11000 の相打ちで両方破壊される
    e = _build(rules, {"bz": ["T1128"]}, {"bz": ["T1130"]})
    state = _battle(e, 0, "T1128", "T1130")
    assert state.get("attacked") and state.get("blocked"), state
    assert "T1128" in _defns(e, "graveyard", 0)
    assert "T1130" in _defns(e, "graveyard", 1)


def test_bonus_applies_when_defending(rules):
    # 防御側でも「バトル中」は効く（battle_power は only
    # 無しで両バトルに効く）: T1128 はブロッカーを持たない
    # ため、攻撃してタップしたところをパワー12000の
    # T1129 に攻撃される形で判別する。素11000では負けるが
    # +11000=22000 で勝つ。
    e = _build(rules, {"bz": ["T1128"]}, {"bz": ["T1129"]})
    state = {}
    for _ in range(3000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 0 \
                and state.get("counterattacked"):
            break
        if d["kind"] == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d["min"])))
        elif d["kind"] == "attack" and d.get("player") == 0 \
                and not state.get("attacked"):
            tgt = [k for k in keys if k == "attack:T1128:player"]
            if tgt:
                state["attacked"] = True
                e.answer([keys.index(tgt[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "attack" and d.get("player") == 1 \
                and state.get("attacked") \
                and not state.get("counterattacked"):
            tgt = [k for k in keys if k == "attack:T1129:T1128"]
            if tgt:
                state["counterattacked"] = True
                e.answer([keys.index(tgt[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])   # T1128 はブロッカー無し
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert state.get("attacked") and state.get("counterattacked"), state
    assert "T1129" in _defns(e, "graveyard", 1)
    assert "T1128" in _tops(e, 0)
