"""語彙パイロット第420弾: does_not_untap（ドリフト）。

対象は pure 2件のうち dm22rp1-011 予言者マンプクルト
（光 / コスト1 / パワー3500 / 種族 ライトブリンガー）。
公式テキスト:
「ブロッカー（このクリーチャーをタップして、相手
クリーチャーの攻撃先をこのクリーチャーに変更してもよい）
このクリーチャーは、自分のターンのはじめにアンタップしない。
自分のタマシードがなければ、このクリーチャーは相手
プレイヤーを攻撃できない。
自分のタマシードが出た時、このクリーチャーをアンタップする。」

第400弾は本ファミリーを「第2・第3条項が未構築」と
して見送ったが、未構築は表現不能ではなく、本弾で
3条項すべてに登録済みの確立形があることを実測した
（第410・411・418弾と同じ覆し型）:

- 第1条項は第400弾の確立形 static {affects: self,
  mod: {deny: [untap_at_start]}}（登録済み dmrp06-027
  の登録形そのもの）。
- 第2条項は登録済み dmrp21-072 マファリッヒ・マシーン
  の同文条項（文面が完全一致）の登録形 static
  {affects: self, if: {not: {exists: {zone: bz,
  owner: you, filter: {types: [tamaseed]}}}},
  mod: {deny: [attack_player]}} そのまま。
- 第3条項は登録済み dm24rp4-031 の監視誘発
  trigger {when: {event: move, to: bz, subject:
  {owner: you, filter, other: true}}, effect:
  [untap {select: {ref: self}}]} の subject を
  タマシードに替えた形。文面に「てもよい」が無い
  ため may は付けない（タップ状態でなければ
  アンタップは無効果で、必須形でも挙動は変わらない）。
  発生源はクリーチャー（タマシードではない）ため
  subject が自身に一致することはなく other は不要。

partial は骨格＋keywords [blocker] まで構築済みで
text は公式全文（補完なし）。alias は無し。
ファミリーの残り1件 dm25ex2-031 は形が異なる
（シンパシー＋出た時メカ以外すべて破壊＋他者への
全般的なアンタップ禁止）ため対象外で、ファミリーは
解消しない（第400弾の untap_restriction と同じ扱い）。

観察（未修正・docs に記録）: when.subject のキーと
そのフィルタは defs 検証で型チェックされず、未知キー・
未知タイプが素通りする（実測。第416弾の selector
other 漏れと同種の検証漏れ）。本弾の形は登録先例と
同一キーしか使わないため影響なし。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (["blocker"], 条項テキスト, []) を
返し、定型所有はキーワードのみで part[2] は空
＝二重付着ブロッカー無し（第419弾と同型）。

proto: T1191（dm22rp1-011 型）。判別役は既存 proto を
流用: T506（自然・コスト2タマシード＝第3条項の発生源役）/
T001（自然バニラ＝対照役・クリーチャー参入役・マナ役）/
T030（光水の多色＝光マナ役）。

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

FORM = [
    {"kind": "static", "affects": "self",
     "mod": {"deny": ["untap_at_start"]}},
    {"kind": "static", "affects": "self",
     "if": {"not": {"exists": {"zone": "bz", "owner": "you",
                              "filter": {"types": ["tamaseed"]}}}},
     "mod": {"deny": ["attack_player"]}},
    {"kind": "trigger",
     "when": {"event": "move", "to": "bz",
              "subject": {"owner": "you",
                          "filter": {"types": ["tamaseed"]}}},
     "effect": [{"op": "untap", "select": {"ref": "self"}}]},
]
FULL_TEXT = ("ブロッカー（このクリーチャーをタップして、相手クリーチャーの"
             "攻撃先をこのクリーチャーに変更してもよい）\n"
             "このクリーチャーは、自分のターンのはじめにアンタップしない。\n"
             "自分のタマシードがなければ、このクリーチャーは相手プレイヤーを"
             "攻撃できない。\n"
             "自分のタマシードが出た時、このクリーチャーをアンタップする。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1191")
    assert c["name"] == "予言者マンプクルト"
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 1 and c["power"] == 3500 and c["mana"] == 1
    assert c["races"] == ["ライトブリンガー"]
    assert c["keywords"] == ["blocker"]
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(copy.deepcopy(c), TABLES)
    for ab in FORM:
        assert ab in d.abilities
    for tid in ("T506", "T001", "T030"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX420", "name": "x",
                    "types": ["creature"], "civs": ["light"],
                    "cost": 1, "power": 3500, "mana": 1,
                    "races": ["ライトブリンガー"],
                    "keywords": ["blocker"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    for ab in FORM:
        assert ab in d.abilities


def test_bad_forms_rejected(rules):
    base = proto_card("T1191")
    # 未知の deny アクションは DefError
    bad = copy.deepcopy(base)
    bad["abilities"][0]["mod"] = {"deny": ["untap_at_strt"]}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # 第2条項の if に未知キーは DefError
    bad2 = copy.deepcopy(base)
    bad2["abilities"][1]["if"] = {"not": {"exists": {
        "zone": "bz", "owner": "you",
        "filter": {"types": ["tamaseed"], "bogus": 1}}}}
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)
    # 第3条項の when の未知ゾーンは DefError
    bad3 = copy.deepcopy(base)
    bad3["abilities"][2]["when"]["to"] = "bogus"
    with pytest.raises(DefError):
        parse_card(bad3, TABLES)
    # 第3条項の effect の未知 op は DefError
    bad5 = copy.deepcopy(base)
    bad5["abilities"][2]["effect"] = [{"op": "untapp",
                                       "select": {"ref": "self"}}]
    with pytest.raises(DefError):
        parse_card(bad5, TABLES)
    # 第3条項の未知イベントは DefError
    bad4 = copy.deepcopy(base)
    bad4["abilities"][2]["when"] = {
        "event": "enter", "to": "bz",
        "subject": {"owner": "you", "filter": {"types": ["tamaseed"]}}}
    with pytest.raises(DefError):
        parse_card(bad4, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "pay_mana":
        e.answer([0])
    elif d["kind"] == "choose_shields":
        e.answer(list(range(d["min"])))
    elif d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _mine(e, defn, player=0):
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn)


def _drive(e, script, max_steps=6000):
    state = {}
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if script(e, d, state):
            if state.get("done"):
                return state
            continue
        _answer_default(e, d)
    raise AssertionError(f"script not finished: {state}")


def _attack_flow(e, defn, cid_box):
    """第400弾の共通フロー: 自ターン1: 召喚。自ターン2:
    攻撃してタップしシールドを1枚ブレイク。自ターン3の
    はじめのタップ状態を cid_box['at_turn3'] に記録する。"""
    def script(e, d, st):
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 0:
            st["charges"] = st.get("charges", 0) + 1
            if st["charges"] == 3:
                cid_box["at_turn3"] = \
                    e.s.cards[cid_box["cid"]].tapped
                st["done"] = True
                return True
            return False
        if d["kind"] == "main" and d.get("player") == 0 \
                and not st.get("summoned"):
            key = f"play:{defn}"
            assert key in keys, keys
            st["summoned"] = True
            e.answer([keys.index(key)])
            return True
        if st.get("summoned") and "cid" not in cid_box:
            cid_box["cid"] = _mine(e, defn)
            return False
        if d["kind"] == "attack" and d.get("player") == 0 \
                and st.get("summoned") and not st.get("attacked"):
            hit = [k for k in keys
                   if k == f"attack:{defn}:player"]
            if hit:
                st["attacked"] = True
                cid_box["shields_before"] = len(e.zlist("shield", 1))
                e.answer([keys.index(hit[0])])
                return True
            return False
        if st.get("attacked") and not st.get("after_attack"):
            if d["kind"] in ("main", "charge", "attack"):
                st["after_attack"] = True
                assert e.s.cards[cid_box["cid"]].tapped is True
                assert len(e.zlist("shield", 1)) \
                    == cid_box["shields_before"] - 1
                return True
            return False
        return False
    return script


def test_stays_tapped_at_own_turn_start(rules):
    # 第1条項の実フロー: タマシードがいるため第2条項の
    # 制限は掛からずプレイヤーを攻撃でき、タップした
    # 状態で次の自ターンのはじめを迎えてもアンタップ
    # しない（deny untap_at_start）。
    e = _build(rules,
               {"bz": ["T506"], "hand": ["T1191"],
                "mana": ["T030", "T001", "T001"]},
               {"bz": []})
    cid_box = {}
    _drive(e, _attack_flow(e, "T1191", cid_box))
    assert cid_box["at_turn3"] is True


def test_control_creature_untaps(rules):
    # 対照: deny を持たない通常クリーチャーは同じ
    # フローで自ターン3のはじめにアンタップしている
    e = _build(rules,
               {"hand": ["T001"],
                "mana": ["T001", "T001", "T001"]},
               {"bz": []})
    cid_box = {}
    _drive(e, _attack_flow(e, "T001", cid_box))
    assert cid_box["at_turn3"] is False


def test_attack_player_denied_without_tamaseed(rules):
    # 第2条項の特性判別: 自分のタマシードがなければ
    # attack_player だけが不許可（attack_creature と
    # block は許可のまま）。タマシードがいれば許可。
    e = _build(rules, {"bz": ["T1191"]}, {"bz": []})
    cid = _mine(e, "T1191")
    assert e.permits(cid, "attack_player") is False
    assert e.permits(cid, "attack_creature") is True
    assert e.permits(cid, "block") is True
    assert e.permits(cid, "untap_at_start") is False
    e2 = _build(rules, {"bz": ["T1191", "T506"]}, {"bz": []})
    cid2 = _mine(e2, "T1191")
    assert e2.permits(cid2, "attack_player") is True
    # 相手のタマシードでは許可されない（owner: you）
    e3 = _build(rules, {"bz": ["T1191"]}, {"bz": ["T506"]})
    cid3 = _mine(e3, "T1191")
    assert e3.permits(cid3, "attack_player") is False


def _play_from_hand(e, player, defn, cid):
    """player の main で defn を出し、解決後に cid の
    タップ状態を返す。"""
    def script(e, d, st):
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == player \
                and not st.get("played"):
            key = f"play:{defn}"
            assert key in keys, keys
            st["played"] = True
            e.answer([keys.index(key)])
            return True
        if st.get("played") and any(
                e.s.cards[c].defn == defn
                for c in e.zlist("bz", player)):
            if d["kind"] in ("main", "charge", "attack"):
                st["tapped"] = e.s.cards[cid].tapped
                st["done"] = True
                return True
            return False
        return False
    st = _drive(e, script)
    return st["tapped"]


def test_tamaseed_entry_untaps_self(rules):
    # 第3条項: タップ状態の発生源がいる盤面で自分の
    # タマシードが出ると、発生源がアンタップする
    # （タップ状態は第397弾の先例どおり直接設定して観測）。
    e = _build(rules,
               {"bz": ["T1191"], "hand": ["T506"],
                "mana": ["T001", "T001", "T001"]},
               {"bz": []})
    cid = _mine(e, "T1191")
    e.s.cards[cid].tapped = True   # タップ状態にして観測する
    assert _play_from_hand(e, 0, "T506", cid) is False


def test_creature_entry_does_not_untap(rules):
    # 対照: 自分のクリーチャーが出ても発火しない
    # （subject フィルタはタマシードのみ）。
    e = _build(rules,
               {"bz": ["T1191"], "hand": ["T001"],
                "mana": ["T001", "T001", "T001"]},
               {"bz": []})
    cid = _mine(e, "T1191")
    e.s.cards[cid].tapped = True
    assert _play_from_hand(e, 0, "T001", cid) is True


def test_opponent_tamaseed_does_not_untap(rules):
    # 対照: 相手のタマシードが出ても発火しない
    # （subject owner: you）。発生源は第1条項で
    # 自ターンのはじめにもアンタップしないため、
    # 相手ターンまでタップしたまま残る。
    e = _build(rules,
               {"bz": ["T1191"], "mana": ["T001"]},
               {"hand": ["T506"],
                "mana": ["T001", "T001", "T001"]})
    cid = _mine(e, "T1191")
    e.s.cards[cid].tapped = True
    assert _play_from_hand(e, 1, "T506", cid) is True
