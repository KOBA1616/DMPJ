"""語彙パイロット第379弾: deck_rule（ドリフト）。

センサス（rejects 1,954件を取り直し）: pure 1,806 /
multi 268 / 空 gaps 18。pure の大半は範囲外（gr_summon
147 / aura 108＝未承認 / hyperdimensional_zone 105 /
dragheart 45 / psychic_filter 45 / hyperdimensional_summon
41 / out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。残りは pure 1〜4件の小家族が多数。
評価済み却下（第316〜320・355〜378弾）は再提案しない。
本弾で個別に評価して見送った候補:
- battle_conditional_power（2件）: dmrp19-008 は partial
  が無くシンカパワーの進化時バトル中倍化で第368弾却下の
  static_double_power と同根、dm22rp1-sp4 は text・
  partial ともに空で評価不能。
- exclude_ref（3件）: dmex14-s04 / dmex14-027 は partial
  が無くアバレチェーン等の重い他条項が残る。dm30-014 は
  クロス先自身を身代わり候補から外す指定で、selector の
  exclude は参照（変数）除外であり常在の発生源除外とは
  形が違う。
- power_comparison（3件）: 各件とも最大パワー比較・
  参照カードのパワー以下・捨てたカードとのパワー比較で
  形が相異なり均一でない。
- cip_trigger_double（2件）: D・D・D／Dスイッチの
  ゲーム中1回消費つき誘発倍化で、トリガー倍化の保留
  機構が要る。
- cost_reduce_per_element（2件）: エレメント数えは
  bz の全カード種を数える count で届く可能性はあるが、
  対象2件とも同一カードの別刷りで、EXライフ＋全体付与＋
  攻撃誘発の複合条項が未組立てで本 gap 単独では登録形が
  定まらない。
- played_free_trigger（2件）: 無料出場の照合は第348弾の
  enter_unpaid 履歴で近づいたが、対象は進化条件・コスト
  増減の他条項が残り均一でない。
- summoning_attack_rule（2件）: 出たターンの攻撃可否を
  自他で付け替える常在形で、第365・366弾却下の
  speed_attacker_rule と同根（付与形の登録先例が無い）。
- all_civs_treatment（3件）: 文明扱いの変更先（bz＋山札／
  進化元判定／マナ＋bz・ターン限定）が各件相異なり均一
  でない。第376弾却下の civ_treatment とも同根。
- force_attack_target（2件）: 呪文の選んだクリーチャー
  への攻撃強制と表向きシールド自身への攻撃強制で形が
  相異なり、攻撃先の強制は第366弾却下の must_be_blocked
  とも別機構。
- madness（2件）: 手札破壊の置換（かわりに出す）は
  discard の置換照合が要り、CIP の複合効果も残る。
- s_back_grant（2件）: S・バック付与は同文明版と
  ツインパクト版で形が相異なり、付与語彙が無い。
- battle_win_power_difference（2件）: バトル勝利時の
  パワー差参照（event.opponent との差）は動的参照が要る。

選定: deck_rule（pure 1件のみ、multi にも現れない）—
dmx22b-110 素晴らしい犬 ワンワンワン。第377弾で次点、
第378弾でも次点として残置された候補で、本弾の指示どおり
実挙動で検証してから選定した。結論は完全なドリフト
（新規語彙・エンジン変更なし）:
- デッキ条項「４枚より多くデッキに入れることができる」は
  デッキ構築ルールで、登録先例 dmex13-057（戯具
  ザンパズル）が同文を text のみで保持し能力化していない
  （notes「デッキ構築ルールはエンジン側に委ねる」）。
  第369弾の4枚条項も同じ扱い。
- パワー条項「バトルゾーンにある自分の他のアウトレイジ犬
  １匹につき、このクリーチャーのパワーを+1111する」は
  常在型 mod power {amount, count} の bz 版。登録先例
  dm22ex2-1a（黒神龍アブライゼ・ドルバ）は同じ mod 形で
  count が墓地セレクタ {zone: graveyard, owner: you,
  filter: {types: [creature]}}。count の評価は
  selectors.count_of が candidates の体数に落ちる汎用
  機構でゾーンに依存しない。自己除外はセレクタの
  other: true（SELECTOR_KEYS の既存キー。candidates の
  ゾーン経路が env の self を落とす）で表す。第378弾が
  候補形とした exclude {ref: self} は選択時の参照除外で
  あり、常在 count には other: true が正しい形。
  schema.py の selector 定義にも other（boolean）が
  定義済み（第408弾の教訓で同期を確認。スキーマ再生成
  不要・Rust ミラー不要・rust_stamp への影響なし）。
- 実挙動の判別（本弾で固定）: 単独では 1111（自分を
  数えれば 2222 になる判別）、他の犬1匹で 2222、2匹で
  3333、同名2体は互いを数えて両方 2222、非犬の味方・
  相手の犬では増えない。バトルでも効く（素では
  パワー2000ブロッカーに負け、犬1匹で勝つ）。

公式テキスト:
「{Dog Souls}《素晴らしい犬 ワンワンワン》は、４枚より
多くデッキに入れることができる。バトルゾーンにある
自分の他のアウトレイジ犬１匹につき、このクリーチャーの
パワーを+1111する。」
partial は stub: 骨格（クリーチャー / 自然 / コスト2 /
パワー1111 / 種族 アウトレイジ犬、mana 1、keywords・
abilities ともに無し）と unsupported の deck_rule
1件だけ。text はデッキ条項の断片のみのため、提出形では
text に行の公式テキスト全文を入れる（補完あり。
ラウンド414への注意に明記）。alias は dmx22b-111
（rejects に独自行は無い）。単面カードで未検証の面は無い。

確立形:
- static {affects: self, mod: {power: {amount: 1111,
  count: {zone: bz, owner: you,
          filter: {races: [アウトレイジ犬]},
          other: true}}}}

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い。
ラウンド414は通常どおり submit できる見込み。

プロト: T1131 = dmx22b-110 型。T1132 = 他のアウトレイジ
犬役（素のクリーチャー）。T1133 = 水・パワー2000
ブロッカー（素1111では負け、+1111=2222 で勝つ判別役）。
非犬の対照は既存 proto T001（自然・パワー2000・種族
テスト）を流用。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
バトルゾーンは共有ゾーンなので所有は bz_tops(p) /
zlist(zone, p) で見る。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

STATIC = {"kind": "static", "affects": "self",
          "mod": {"power": {"amount": 1111,
                            "count": {"zone": "bz", "owner": "you",
                                      "filter": {"races": ["アウトレイジ犬"]},
                                      "other": True}}}}
FORM = [STATIC]
FULL_TEXT = ("{Dog Souls}《素晴らしい犬 ワンワンワン》は、"
             "４枚より多くデッキに入れることができる。"
             "バトルゾーンにある自分の他のアウトレイジ犬１匹につき、"
             "このクリーチャーのパワーを+1111する。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form():
    proto = proto_card("T1131")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    d = parse_card(proto, TABLES)
    assert STATIC in d.abilities
    assert d.types == ["creature"]
    assert d.civs == ["nature"]
    assert d.cost == 2 and d.power == 1111
    assert d.races == ["アウトレイジ犬"]
    assert d.keywords == []
    for tid in ("T1132", "T1133"):
        parse_card(proto_card(tid), TABLES)


def test_bad_count_selector_rejected():
    bad = dict(proto_card("T1131"))
    bad["abilities"] = [{"kind": "static", "affects": "self",
                         "mod": {"power": {"amount": 1111,
                                           "count": {"zone": "bz",
                                                     "owner": "you",
                                                     "bogus": 1}}}}]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _powers(e, tid, p):
    return [e.chars(c)["power"] for c in e.bz_tops(p)
            if e.cdef(c).id == tid]


def test_power_alone_counts_no_self(rules):
    # 単独では自分を数えず 1111 のまま（other: true が
    # 効いていなければ 2222 になる判別）
    e = _build(rules, {"bz": ["T1131"]}, {"bz": []})
    assert _powers(e, "T1131", 0) == [1111]


def test_power_scales_with_other_dogs(rules):
    e = _build(rules, {"bz": ["T1131", "T1132"]}, {"bz": []})
    assert _powers(e, "T1131", 0) == [2222]
    e = _build(rules, {"bz": ["T1131", "T1132", "T1132"]}, {"bz": []})
    assert _powers(e, "T1131", 0) == [3333]


def test_two_copies_count_each_other(rules):
    e = _build(rules, {"bz": ["T1131", "T1131"]}, {"bz": []})
    assert _powers(e, "T1131", 0) == [2222, 2222]


def test_non_dog_and_opponent_dog_do_not_count(rules):
    e = _build(rules, {"bz": ["T1131", "T001"]}, {"bz": ["T1132"]})
    assert _powers(e, "T1131", 0) == [1111]


def _keys(d):
    return [o["key"] for o in d["options"]]


def _battle(e, attacker_p, attacker, blocker):
    """attacker_p の attacker がプレイヤーを攻撃し、相手が
    blocker でブロックする。バトルが終わって attacker_p の
    次の charge が来たら戻る。"""
    state = {}
    for _ in range(3000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == attacker_p \
                and state.get("blocked"):
            return state
        if d["kind"] == "yes_no":
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


def test_battle_loses_without_other_dog(rules):
    # 素パワー1111ではパワー2000ブロッカーに負ける
    e = _build(rules, {"bz": ["T1131"]}, {"bz": ["T1133"]})
    state = _battle(e, 0, "T1131", "T1133")
    assert state.get("attacked") and state.get("blocked"), state
    assert "T1131" in _defns(e, "graveyard", 0)
    assert "T1133" in _tops(e, 1)


def test_battle_wins_with_other_dog(rules):
    # 他の犬1匹で 2222 になりパワー2000ブロッカーに勝つ
    e = _build(rules, {"bz": ["T1131", "T1132"]}, {"bz": ["T1133"]})
    state = _battle(e, 0, "T1131", "T1133")
    assert state.get("attacked") and state.get("blocked"), state
    assert "T1133" in _defns(e, "graveyard", 1)
    assert "T1131" in _tops(e, 0)
