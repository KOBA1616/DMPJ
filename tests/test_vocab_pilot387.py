"""語彙パイロット第387弾: attack_count_this_turn
（新規語彙: turn_count {kind: attack} に distinct: true を追加）。

対象は pure 1件すべて: dm25ex3-rp4s04 楽蛇の虚 フミガルド
（火 / コスト5 / パワー6000 / デーモン・コマンド）。
公式テキストの第1条項:
「このターン攻撃したクリーチャー1体につき、この
クリーチャーの召喚コストを2少なくする。ただし、
コストは0以下にはならない。」

公式セマンティクスの確定: 公式QA 47928（2025.12.19、
dm.takaratomy.co.jp/rule/qa/47928）は、同じクリーチャーが
攻撃→アンタップ→再攻撃した後に D・D・D を宣言する
状況で「コストは2だけ少なくなる」と回答している。
すなわちこの条項は攻撃の回数ではなく、攻撃した
クリーチャーの体数（distinct な体数）を数える。

既存部品の確認:
- 手札常在型のコスト軽減はシンパシーの確立形
  static {zone: hand, affects: self, mod: {cost:
  {amount, count}, cost_min}}（第381弾ほか）。
  count の位置に式を置けることは count_spec が
  turn_count を式として受理する点で確認済み。
- しかし turn_count {kind: attack} は hist:attackers
  リストの長さ（攻撃宣言の回数、重複あり）を数える
  ため、再攻撃する同一クリーチャーを二重に数えて
  しまい、公式の体数読みと一致しない。変換データ内の
  既存使用13件はすべて cmp 条件（== 0 / >= 1 が大半で
  重複排除の影響なし。< 2 の dmrp08-023 は第197ラウンドで
  distinct な数えが必要として一度差し戻された経緯が
  あり、その登録形の見直しは本弾の範囲外）。
- よって本弾は最小の新規語彙として、turn_count の
  kind: attack 専用オプション distinct: true を追加する:
  * defs.py: turn_count の受理キーに distinct を追加し、
    other と同型に「kind: attack の時だけ・bool のみ」を検証。
  * schema.py: turn_count の properties に distinct を
    追加し card.schema.json を再生成（差分は3行のみ。
    第408ラウンドの教訓どおり defs と schema の両方を確認）。
  * engine/selectors.py の _turn_count: distinct の時、
    hist:attackers リストを cid で重複排除してから
    other / filter を適用して数える。記録側
    （events._record_history の append）と ord 用の
    攻撃回数カウンタには触らない。
  * Rust 側: hist:attackers の記録は engine.rs に
    同型の push_list があるが、turn_count 式の評価器は
    Rust 側に無く（式評価は Python のみ）、記録自体も
    変えないためミラー不要。GameState の新規フィールドは
    無いので state.rs のミラーも不要。rust_stamp は
    従来どおり据え置き（この環境に cargo 無し、Python のみ動作）。

確立形:
- abilities = [static {zone: hand, affects: self,
  mod: {cost: {amount: -2, count: {turn_count:
  {kind: attack, owner: any, distinct: true}}},
  cost_min: 1}}, declare（partial 構築済み）,
  replace（partial 構築済み）] の3件（条項順）。
  owner はテキストに所有者の限定が無いため any。
  下限は「0以下にはならない」= 最小1で cost_min: 1。
- D・D・D 宣言（may 包みの play_self {cost: 5,
  civs: [fire]}）と、自分のターンに1度・手札1枚以下で
  相手クリーチャーの出る時置換（once_per_turn +
  optional の replace）は partial の構築済み形を
  そのまま使う（ドリフト）。
- D・D・D の支払いはエンジンの代替コスト一様規則
  （代替ベース＋pay_cost の純増減）に従う。本カードは
  代替ベース（5）と印刷コスト（5）が等しいため、
  支払額は軽減後の召喚コストと一致する（実挙動で検証）。

partial は骨格＋宣言・置換まで構築済みで、text は
公式テキスト全文（補完なし）。コスト常在型1件を
条項順の先頭に足すだけで提出形になる。alias は
dm25ex3-rp4sec05 / dm25rp4-s04 / dm25rp4-sec05 の
3件（いずれも自前の reject 行は無い）。単面カードで
未検証の面は無い。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (keywords, text, []) の3要素を返し、
part[2] の定型所有は空＝ブロッカー無し（第387弾で実測）。

proto: T1150（dm25ex3-rp4s04 型）。判別役は新規
フィクスチャ T1151（攻撃終了時に自己アンタップする
連撃獣。公式QA の再攻撃状況を実挙動で作る役）と
既存 proto T001 / T1139（別個体のアタッカー役）、
マナ役は T277 を流用する。

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

COST_STATIC = {"kind": "static", "zone": "hand", "affects": "self",
               "mod": {"cost": {"amount": -2,
                                "count": {"turn_count": {"kind": "attack",
                                                         "owner": "any",
                                                         "distinct": True}}},
                       "cost_min": 1}}
DECLARE = {"kind": "declare", "zone": "hand",
           "when": {"event": "attack",
                    "subject": {"owner": "you",
                                "filter": {"types": ["creature"]}}},
           "effect": [{"op": "may",
                       "body": [{"op": "play_self", "cost": 5,
                                 "civs": ["fire"]}]}]}
REPLACE = {"kind": "replace", "once_per_turn": True, "optional": True,
           "when": {"event": "move", "to": "bz",
                    "subject": {"owner": "opp",
                                "filter": {"types": ["creature"]}}},
           "if": {"all": [{"is_turn": "you"},
                          {"cmp": [{"count": {"zone": "hand",
                                              "owner": "you"}},
                                   "<=", 1]}]},
           "instead": [{"op": "move", "select": {"ref": "event.subject"},
                        "to": "graveyard", "reason": "put"}]}
FORM = [COST_STATIC, DECLARE, REPLACE]
FULL_TEXT = ("このターン攻撃したクリーチャー１体につき、このクリーチャーの"
             "召喚コストを２少なくする。ただし、コストは０以下にはならない。\n"
             "D・D・D [ff05]\n"
             "スピードアタッカー\n"
             "W・ブレイカー\n"
             "自分のターンに１度、相手のクリーチャーが出る時、自分の手札が"
             "１枚以下なら、かわりにそのクリーチャーを墓地に置いてもよい。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1150")
    assert c["name"] == "楽蛇の虚 フミガルド"
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 5 and c["power"] == 6000 and c["mana"] == 1
    assert c["races"] == ["デーモン・コマンド"]
    assert c["keywords"] == ["speed_attacker", "double_breaker"]
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 5   # 3能力＋キーワード2件の展開


def test_fixture_form(rules):
    c = proto_card("T1151")
    assert c["types"] == ["creature"] and c["keywords"] == ["speed_attacker"]
    parse_card(c, TABLES)


def _static_with(spec):
    return [{"kind": "static", "zone": "hand", "affects": "self",
             "mod": {"cost": {"amount": -2, "count": {"turn_count": spec}},
                     "cost_min": 1}}]


def test_distinct_validation(rules):
    base = copy.deepcopy(proto_card("T1150"))
    # distinct は kind: attack でのみ受理される
    base["abilities"] = _static_with({"kind": "attack", "owner": "any",
                                      "distinct": True})
    parse_card(base, TABLES)
    # 他 kind での distinct は DefError
    bad = copy.deepcopy(base)
    bad["abilities"] = _static_with({"kind": "block", "owner": "you",
                                     "distinct": True})
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # distinct は bool のみ
    bad2 = copy.deepcopy(base)
    bad2["abilities"] = _static_with({"kind": "attack", "owner": "any",
                                      "distinct": "yes"})
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)
    # 未知キーは従来どおり DefError
    bad3 = copy.deepcopy(base)
    bad3["abilities"] = _static_with({"kind": "attack", "owner": "any",
                                      "uniq": True})
    with pytest.raises(DefError):
        parse_card(bad3, TABLES)


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


def _hand_cid(e, defn="T1150"):
    return next(c for c in e.zlist("hand", 0)
                if e.s.cards[c].defn == defn)


def test_pay_cost_progression(rules):
    # 攻撃が無い間は素のコスト5。別個体の攻撃が進むごとに
    # 体数ぶん軽減される（1体→3、2体→1）。宣言の提示時点では
    # 攻撃中のクリーチャー自身も記録済みで数に入る。
    e = _build(rules, {"bz": ["T001", "T1139"], "hand": ["T1150"]}, {})
    cid = _hand_cid(e)
    assert e.chars_ro(cid)["pay_cost"] == 5
    readings = []
    queue = ["attack:T001:player", "attack:T1139:player"]
    for _ in range(400):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "declare_attack":
            hist = list(e.s.turn_counters.get("hist:attackers:0", []))
            readings.append((hist, e.chars_ro(cid)["pay_cost"]))
            e.answer([])   # 宣言は見送る
            continue
        if d["kind"] == "attack" and d.get("player") == 0 and queue:
            want = queue.pop(0)
            assert want in keys, keys
            e.answer([keys.index(want)])
            continue
        if d["kind"] == "charge" and d.get("player") == 1:
            break
        _answer_default(e, d)
    assert len(readings) == 2
    (h1, p1), (h2, p2) = readings
    assert len(h1) == 1 and p1 == 3          # 1体目の攻撃中: -2
    assert len(h2) == 2 and len(set(h2)) == 2 and p2 == 1   # 2体で -4


def test_pay_cost_same_creature_twice(rules):
    # 公式QA 47928 の状況: 同じクリーチャーが攻撃→アンタップ→
    # 再攻撃しても、体数は1体のまま（pay_cost は 5-2=3。
    # 回数読みなら 5-4=1 になる判別テスト）。
    e = _build(rules, {"bz": ["T1151"], "hand": ["T1150"]}, {})
    cid = _hand_cid(e)
    attacks = 0
    seen = None
    for _ in range(400):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "declare_attack":
            e.answer([])
            continue
        if d["kind"] == "attack" and d.get("player") == 0:
            if "attack:T1151:player" in keys and attacks < 2:
                attacks += 1
                e.answer([keys.index("attack:T1151:player")])
                continue
            # 2回攻撃した後の攻撃決定で状態を読む
            seen = (list(e.s.turn_counters.get("hist:attackers:0", [])),
                    e.chars_ro(cid)["pay_cost"])
            break
        _answer_default(e, d)
    assert attacks == 2
    assert seen is not None
    hist, pay = seen
    assert len(hist) == 2 and hist[0] == hist[1]   # 記録は同一 cid が2件
    assert pay == 3                                # 数えは1体ぶんだけ


def test_pay_cost_floor(rules):
    # 3体攻撃すると素の計算は 5-6=-1 だが、下限1で止まる
    # （cost_min が無ければ既定の下限0で 0 になる判別テスト）。
    e = _build(rules, {"bz": ["T001", "T1139", "T001"], "hand": ["T1150"]}, {})
    cid = _hand_cid(e)
    seen = None
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        hist = list(e.s.turn_counters.get("hist:attackers:0", []))
        if len(hist) >= 3 and seen is None:
            seen = e.chars_ro(cid)["pay_cost"]
            break
        if d["kind"] == "declare_attack":
            e.answer([])
            continue
        if d["kind"] == "attack" and d.get("player") == 0:
            atk = [k for k in keys if k.startswith("attack:")]
            if atk:
                e.answer([keys.index(atk[0])])
                continue
        _answer_default(e, d)
    assert seen == 1


def test_ddd_declare_pays_reduced_cost(rules):
    # 実挙動: 1体目の攻撃では宣言を見送り、2体目の攻撃で
    # D・D・D を宣言すると、軽減後のコスト1だけを払って
    # フミガルドが出る（代替ベース5＋純増減-4 = 1）。
    e = _build(rules, {"bz": ["T001", "T1139"], "hand": ["T1150"],
                       "mana": ["T277"] * 9}, {})
    queue = ["attack:T001:player", "attack:T1139:player"]
    declares = 0
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "declare_attack":
            declares += 1
            if declares == 2:
                idx = [i for i, k in enumerate(keys)
                       if k.startswith("declare:T1150")]
                assert idx, keys
                e.answer([idx[0]])
            else:
                e.answer([])
            continue
        if d["kind"] == "attack" and d.get("player") == 0 and queue:
            want = queue.pop(0)
            assert want in keys, keys
            e.answer([keys.index(want)])
            continue
        if d["kind"] == "charge" and d.get("player") == 1:
            break
        _answer_default(e, d)
    assert declares >= 2
    assert any(e.s.cards[c].defn == "T1150" for c in e.zlist("bz", 0))
    tapped = sum(1 for c in e.zlist("mana", 0) if e.s.cards[c].tapped)
    assert tapped == 1
