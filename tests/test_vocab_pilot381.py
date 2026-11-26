"""語彙パイロット第381弾: opponent_cannot_summon_or_cast_next_turn
（ドリフト）。

対象は pure 1件すべて: dm21-014 デビル・リンク・タブー
（闇の呪文、コスト10）。

残る条項は2つとも登録先例の確立形で届く:
- シンパシー：グランド・デビルとディープ・マリーン は
  dm21-020 / dm21-011 の登録先例と同形の static
  {zone: hand, affects: self, mod: {cost: {amount: -1,
  count: {zone: bz, owner: you, filter: {races:
  [グランド・デビル, ディープ・マリーン]}}}, cost_min: 1}}。
  partial の notes 自身が「シンパシー自体は書ける」と
  明記している。
- 「相手は、次の自分自身のターンにクリーチャーを
  召喚できず、呪文を唱えることもできない」は、
  ファイナル・ストップ（dm26sd1-e007、第33弾）の
  登録形 modify {select: {zone: hand, owner: opp,
  filter: {types: [spell]}}, mod: {deny: [cast]},
  duration: until_next_own_turn_start} と同型で、
  召喚側は dm23bd7-030（「次の相手のターン中、相手は
  コスト2以下のクリーチャーを召喚できない」→
  deny: [summon] + until_next_own_turn_start）の
  コスト上限なし版。両 op の併記は dmex17-024
  （このターン版、duration: end_of_turn）の登録先例
  と同系。duration の読み（until_next_own_turn_start
  ＝次の相手のターンの終わりまで）は第33弾以来の
  プロジェクトの確立した読みで、本カードの
  「次の自分自身のターンに」も同じ範囲。

確立形:
- abilities = [シンパシーの static] の1件。
- spell = [modify deny summon（クリーチャー）,
  modify deny cast（呪文）] の2 op（公式テキストの
  条項順）。
- text は行の公式テキスト全文（partial の text は
  ロック条項だけのため、ラウンド416ではシンパシー
  条項を含む全文で補完すること）。

proto: T1135（dm21-014 型）。判別役は新規フィクスチャ
T1136（グランド・デビル役）/ T1137（ディープ・
マリーン役）と既存 proto T001（自然・コスト2
クリーチャー）/ T003（水・コスト2呪文）/ T008
（闇・コスト2。マナ役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

SYMPATHY = {
    "kind": "static", "zone": "hand", "affects": "self",
    "mod": {"cost": {"amount": -1,
                     "count": {"zone": "bz", "owner": "you",
                               "filter": {"races": ["グランド・デビル",
                                                    "ディープ・マリーン"]}}},
            "cost_min": 1},
}
DENY_SUMMON = {
    "op": "modify",
    "select": {"zone": "hand", "owner": "opp",
               "filter": {"types": ["creature"]}},
    "mod": {"deny": ["summon"]},
    "duration": "until_next_own_turn_start",
}
DENY_CAST = {
    "op": "modify",
    "select": {"zone": "hand", "owner": "opp",
               "filter": {"types": ["spell"]}},
    "mod": {"deny": ["cast"]},
    "duration": "until_next_own_turn_start",
}
FULL_TEXT = ("シンパシー：グランド・デビルとディープ・マリーン"
             "(この呪文を唱える時支払うコストは、バトルゾーンにある"
             "自分のグランド・デビルまたはディープ・マリーン１体に"
             "つき１少なくなる。ただし、コストは１より少なくならない)\n"
             "相手は、次の自分自身のターンにクリーチャーを召喚できず、"
             "呪文を唱えることもできない。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1135")
    assert c["name"] == "デビル・リンク・タブー"
    assert c["types"] == ["spell"] and c["civs"] == ["darkness"]
    assert c["cost"] == 10 and c["mana"] == 1
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == [SYMPATHY]
    assert c["spell"] == [DENY_SUMMON, DENY_CAST]
    parse_card(c, TABLES)


def test_unknown_deny_action_rejected(rules):
    # deny のアクション名は permissions の action 表で検証され、
    # 未知のアクションは DefError（defs の allow/deny 検証）
    c = proto_card("T1135")
    bad = copy.deepcopy(c)
    bad["spell"] = [dict(DENY_SUMMON, mod={"deny": ["dance"]}),
                    DENY_CAST]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _pay_cost(rules, bz):
    e = _build(rules, {"bz": bz, "hand": ["T1135"]}, {})
    cid = next(c for c in e.zlist("hand", 0)
               if e.s.cards[c].defn == "T1135")
    return e.chars_ro(cid)["pay_cost"]


def test_sympathy_pay_cost(rules):
    assert _pay_cost(rules, []) == 10                    # 素は10
    assert _pay_cost(rules, ["T1136"]) == 9              # グランド・デビル1体
    assert _pay_cost(rules, ["T1137"]) == 9              # ディープ・マリーン1体
    assert _pay_cost(rules, ["T1136", "T1137", "T1136"]) == 7   # 混在3体
    assert _pay_cost(rules, ["T001"]) == 10              # 対象外種族は数えない
    assert _pay_cost(rules, ["T1136"] * 12) == 1         # 下限1（cost_min）


def _keys(d):
    return [o["key"] for o in d["options"]]


def _lock_game(rules, cast):
    """p0 が T1135 を唱える（または唱えない）ゲームを進め、
    (p1 の1回目の main の選択肢, p1 の2回目の main の選択肢,
     唱えた直後の p0 の main の選択肢) を返す。"""
    p0 = {"hand": ["T1135", "T003"],
          "mana": ["T008"] + ["T003"] * 11}
    p1 = {"hand": ["T001", "T003"],
          "mana": ["T001", "T003", "T001", "T003"]}
    e = _build(rules, p0, p1)
    cast_done = False
    p0_after_cast = None
    p1_mains = []
    for _ in range(1200):
        d = e.advance()
        assert d is not None, "game ended"
        k = _keys(d)
        if cast and not cast_done and d["kind"] == "main" \
                and d.get("player") == 0 and "play:T1135" in k:
            cast_done = True
            e.answer([k.index("play:T1135")])
            continue
        if cast_done and p0_after_cast is None \
                and d["kind"] == "main" and d.get("player") == 0:
            p0_after_cast = k
        if d["kind"] == "main" and d.get("player") == 1:
            p1_mains.append(k)
            if len(p1_mains) == 2:
                return p1_mains[0], p1_mains[1], p0_after_cast
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in k:
            e.answer([k.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("p1 second main never came")


def test_lock_next_opponent_turn(rules):
    first, second, _ = _lock_game(rules, cast=True)
    # 次の相手ターン中: 召喚も詠唱もできない
    assert "play:T001" not in first, first
    assert "play:T003" not in first, first
    # 自分の次のターン開始で失効し、その後の相手ターンでは戻る
    assert "play:T001" in second, second
    assert "play:T003" in second, second


def test_lock_control_without_cast(rules):
    first, _, _ = _lock_game(rules, cast=False)
    # 対照: 唱えなければ相手は通常どおり召喚・詠唱できる
    assert "play:T001" in first, first
    assert "play:T003" in first, first


def test_lock_does_not_hit_caster(rules):
    # ロックは相手の手札だけに掛かる: 唱えた本人の同じ
    # ターンの main では自分の呪文が通常どおり唱えられる
    _, _, after = _lock_game(rules, cast=True)
    assert after is not None
    assert "play:T003" in after, after
