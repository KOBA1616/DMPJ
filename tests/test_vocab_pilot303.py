"""語彙パイロット第303弾: dragonic_field（ドラゴニック・フィールド）。

センサス（rejects 2,087件）: 在範の純粋ファミリーは最大でも3件で、
大半は評価済み DEEP／延期（ignore_abilities、copy_abilities、
victory_icon_filter、cost_sum_of_revealed 等）。未評価で均一な
dragonic_field 純粋3件（dm26ex3-067 / dmex12-011 = 龍世界
〜龍の降臨する地〜、dmex15-b027 = 切札の里）を選定した。
wd_field 系は第301弾センサスで「場ゾーン新設級」と評価済みのため
対象外。historic_field は初手手札誘発という別機構が本体なので
本弾には含めない。

不足は2層に分かれる:
- 型印: 入力のカードタイプ「ドラゴニック・フィールド」を表す
  語彙が無く、3件とも partial の types は [field] のまま
  unsupported に残っていた。D2フィールドの型印 d2_field
  （第151弾）と同型に、型印 `dragonic_field` を defs の
  CARD_TYPES に追加し、types は [field, dragonic_field] と
  併記する（スキーマ再生成の差分は型 enum の2箇所のみ）。
  変換指示（tools/convert_cards.py）にも併記を明記した。
- 能力形: いずれも既存語彙で足りる（新規 op・フィールドなし）。
  - 形A（龍世界）: フィールドの turn_start 誘発（player: you。
    tick レコードに subject は無い＝第328弾の作法）。山札上1枚を
    墓地へ（明示 move + as: milled。mill マクロは as を転送
    しない）。進化ではないドラゴンなら（exists {ref, filter:
    {race_has: ドラゴン, not_types: [evolution]}}）、may で
    自分を破壊し（明示 move + as: gone）、払えた場合だけ
    （if {exists: {ref: gone}} ＝ dmx18-003 のゲート形）
    play_free {ref: milled} でそのドラゴンを出す。
  - 形B（切札の里）: 常在型2つ。(1) affects {zone: hand,
    filter: {name_has: ボルシャック}} + mod cost_may
    {amount: 2, min: 1}（任意軽減。dm23ex2-097 等の先例形。
    「コストは0以下にはならない」= min: 1）。(2) affects
    {zone: bz, filter: {name_has: ボルシャック}} + mod
    grant [speed_attacker]。

proto: T919 形A / T920 形B / T921 ドラゴン / T922 進化ドラゴン /
T923 ボルシャック獣（コスト5）/ T924 ボルシャック子竜（コスト2、
床の確認用）。山札指定は setup の作法で最後尾が一番上。形Aの
テストは山札を単一デフンで統一し、初手ドロー等の消費に依らず
トップを確定させる。
"""
import os

os.environ.setdefault("DMSIM_SKIP_CONVERTED", "1")

import pytest  # noqa: E402

from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402
from tests.conftest import setup  # noqa: E402

TABLES = load_tables()
IDS = ("T919", "T920", "T921", "T922", "T923", "T924")


def _rules():
    return load_rules()


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _drive(e, handler=None, turns=1, max_steps=400):
    seen = []
    for _ in range(max_steps):
        if e.s.turn > turns:
            break
        d = e.advance()
        if d is None:
            break
        if e.s.turn > turns:   # 次ターンへ跨いだ advance は答えずに止める
            break
        seen.append(d)
        if handler and handler(e, d):
            continue
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return seen


def _yn(answers):
    st = {"a": list(answers)}

    def h(e, d):
        if d["kind"] == "yes_no":
            e.answer([st["a"].pop(0) if st["a"] else 0])
            return True
        return False

    return h


def test_proto_parse_and_types():
    for cid in IDS:
        parse_card(proto_card(cid), TABLES)
    assert proto_card("T919")["types"] == ["field", "dragonic_field"]
    assert proto_card("T920")["types"] == ["field", "dragonic_field"]
    bad = dict(proto_card("T919"))
    bad["types"] = ["field", "bogus_type"]
    with pytest.raises(Exception):
        parse_card(bad, TABLES)


def test_marker_filter_consequence():
    # 併記の帰結: {types: [dragonic_field]} はドラゴニックだけを、
    # {types: [field]} は通常フィールドもドラゴニックも拾う（第151弾と同型）。
    e = setup(_rules(), {"bz": ["T919", "T069"]}, {"deck": ["T002"] * 4})
    by = {e.s.cards[c].defn: c for c in e.zlist("bz", 0)}
    assert e.filter_match(by["T919"], {"types": ["dragonic_field"]})
    assert e.filter_match(by["T919"], {"types": ["field"]})
    assert e.filter_match(by["T069"], {"types": ["field"]})
    assert not e.filter_match(by["T069"], {"types": ["dragonic_field"]})


# ---- 形A（T919 = 龍世界型） ----

def _setup_a(deck):
    return setup(_rules(), {"bz": ["T919"], "deck": deck,
                            "mana": ["T034"] * 3},
                 {"deck": ["T002"] * 4})


def test_a_accept_destroys_field_and_summons_dragon():
    e = _setup_a(["T921"] * 8)
    _drive(e, _yn([0]), turns=1)
    assert "T919" in _defns(e, "graveyard", 0)      # フィールドは破壊された
    assert "T921" in _defns(e, "bz", 0)             # ドラゴンが出た
    assert "T921" not in _defns(e, "graveyard", 0)  # 墓地に残っていない


def test_a_decline_keeps_field_and_dragon_stays_in_graveyard():
    e = _setup_a(["T921"] * 8)
    _drive(e, _yn([1]), turns=1)
    assert "T919" in _defns(e, "bz", 0)
    assert "T921" in _defns(e, "graveyard", 0)
    assert "T921" not in _defns(e, "bz", 0)


def test_a_non_dragon_mills_without_choice():
    e = _setup_a(["T001"] * 8)
    seen = _drive(e, _yn([0]), turns=1)
    assert not any(d["kind"] == "yes_no" for d in seen)
    assert "T001" in _defns(e, "graveyard", 0)
    assert "T919" in _defns(e, "bz", 0)


def test_a_evolution_dragon_is_excluded():
    e = _setup_a(["T922"] * 8)
    seen = _drive(e, _yn([0]), turns=1)
    assert not any(d["kind"] == "yes_no" for d in seen)
    assert "T922" in _defns(e, "graveyard", 0)
    assert "T922" not in _defns(e, "bz", 0)
    assert "T919" in _defns(e, "bz", 0)


def test_a_does_not_fire_on_opponents_turn():
    e = _setup_a(["T921"] * 8)
    seen = _drive(e, _yn([1]), turns=2)   # ターン1で辞退、ターン2（相手）まで
    # ターン2（相手のターン）では誘発しない: yes_no はターン1の1回だけ。
    # （ターン3へ跨いだ advance は未回答で止めるため数に入らない）
    assert sum(1 for d in seen if d["kind"] == "yes_no") == 1
    assert "T921" in _defns(e, "graveyard", 0)   # ターン1に落ちた1枚


# ---- 形B（T920 = 切札の里型） ----

def test_b_cost_may_in_chars_only_with_field():
    e = setup(_rules(), {"bz": ["T920"], "hand": ["T923"],
                         "mana": ["T034"] * 5}, {"deck": ["T002"] * 4})
    cid = [c for c in e.zlist("hand", 0)][0]
    cm = e.chars_ro(cid)["cost_may"]
    assert len(cm) == 1 and cm[0]["amount"] == 2 and cm[0]["min"] == 1
    e2 = setup(_rules(), {"hand": ["T923"], "mana": ["T034"] * 5},
               {"deck": ["T002"] * 4})
    cid2 = [c for c in e2.zlist("hand", 0)][0]
    assert e2.chars_ro(cid2)["cost_may"] == []


def _tapped_mana(e, p=0):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


def _play(e, defn, choice):
    """手札から defn を実行し、着地した時点の状態を返す。
    支払いはコスト確定後に自動でマナがタップされる作法（全火マナの
    ように選択の余地が無い場合、pay_mana 決定は出ない）なので、
    軽減の提示（choose_cards の reduce / normal）と着地後の
    タップ済みマナ数で観測する。"""
    st = {"offer": False, "tapped": None}
    for _ in range(120):
        d = e.advance()
        if d is None:
            break
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "charge" and "pass" in keys:
            e.answer([keys.index("pass")])
        elif kind == "main" and f"play:{defn}" in keys:
            e.answer([keys.index(f"play:{defn}")])
        elif kind == "choose_cards" and "reduce" in keys:
            st["offer"] = True
            e.answer([keys.index(choice or "normal")])
        elif kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if defn in _defns(e, "bz", 0):
            st["tapped"] = _tapped_mana(e)
            break
    return st


def test_b_pay_with_reduction():
    e = setup(_rules(), {"bz": ["T920"], "hand": ["T923"],
                         "mana": ["T034"] * 5}, {"deck": ["T002"] * 4})
    st = _play(e, "T923", "reduce")
    assert st["offer"] and st["tapped"] == 3     # 5 - 2 = 3 を支払う


def test_b_pay_without_reduction():
    e = setup(_rules(), {"bz": ["T920"], "hand": ["T923"],
                         "mana": ["T034"] * 5}, {"deck": ["T002"] * 4})
    st = _play(e, "T923", "normal")
    assert st["offer"] and st["tapped"] == 5     # 軽減を使わなければ素のコスト


def test_b_reduction_floor_is_one():
    e = setup(_rules(), {"bz": ["T920"], "hand": ["T924"],
                         "mana": ["T034"] * 2}, {"deck": ["T002"] * 4})
    st = _play(e, "T924", "reduce")
    assert st["offer"] and st["tapped"] == 1     # 2 - 2 だが「0以下にはならない」


def test_b_no_field_no_offer():
    e = setup(_rules(), {"hand": ["T923"], "mana": ["T034"] * 5},
              {"deck": ["T002"] * 4})
    st = _play(e, "T923", "reduce")
    assert not st["offer"] and st["tapped"] == 5


def test_b_non_bolshack_name_gets_nothing():
    e = setup(_rules(), {"bz": ["T920"], "hand": ["T001"],
                         "mana": ["T001", "T001", "T034"]},
              {"deck": ["T002"] * 4})
    st = _play(e, "T001", "reduce")
    assert not st["offer"] and st["tapped"] == 2   # T001 はコスト2の素払い


def _attack_keys_after_play(e, defn, choice="normal"):
    """defn を手札から実行し、実行したターンの最初の攻撃ステップの
    選択肢キーを返す（攻撃ステップが無いままターンが進んだら []）。"""
    landed_turn = None
    for _ in range(120):
        if landed_turn is not None and e.s.turn > landed_turn:
            return []
        d = e.advance()
        if d is None:
            break
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "attack":
            return keys
        if landed_turn is None and defn in _defns(e, "bz", 0):
            landed_turn = e.s.turn
        if kind == "charge" and "pass" in keys:
            e.answer([keys.index("pass")])
        elif kind == "main" and f"play:{defn}" in keys:
            e.answer([keys.index(f"play:{defn}")])
        elif kind == "choose_cards" and "reduce" in keys:
            e.answer([keys.index(choice)])
        elif kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return []


def test_b_speed_attacker_grant_allows_same_turn_attack():
    # setup で bz に置いたクリーチャーは召喚酔いの対象にならないため、
    # 手札から実行したターンに攻撃できるかで判別する。
    e = setup(_rules(), {"bz": ["T920"], "hand": ["T923"],
                         "mana": ["T034"] * 5}, {"deck": ["T002"] * 4})
    keys = _attack_keys_after_play(e, "T923")
    assert "attack:T923:player" in keys


def test_b_without_field_no_same_turn_attack():
    e = setup(_rules(), {"hand": ["T923"], "mana": ["T034"] * 5},
              {"deck": ["T002"] * 4})
    keys = _attack_keys_after_play(e, "T923")
    assert "attack:T923:player" not in keys
