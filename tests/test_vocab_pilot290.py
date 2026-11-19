"""語彙パイロット第290弾: win_prevention（敗北防止と勝利の置換）。

rejects の win_prevention 純粋3件（dmrp06-001 / dmx11-001 / dmr20-038）の
不足は3形に分解できる:

- 形A（T837、dmrp06-001 の敗北防止節）: 常在型 no_lose（第188/238弾）に
  if: 2つの count の cmp（自分のバトルゾーンのクリーチャー数 > 相手）。
  dmex08-221 の単一 count cmp の対項拡張で、新語彙なし。
- 形B（T838、dmx11-001 の敗北防止節）: 常在型 no_lose に
  if: {exists: {ref: self, filter: {tapped: true}}}。dm25bd2-003 に登録
  先例がある形で、新語彙なし。
- 形C（T839、dmr20-038 の勝利置換節）: 手札からの敗北置換
  {kind: replace, zone: hand, optional: true,
   when: {event: lose, reason: [deck_out, state, effect]},
   instead: [手札のこのカードを捨てる]}。
  lose の reason は direct_attack / deck_out / state / effect の4値
  （第188弾）で、「クリーチャーによる攻撃以外の方法で相手が勝つ」
  = 自分の敗北 reason が direct_attack でない3値のリストで表せる。
  手札の発生源走査は第287弾で _lose_candidates に入っている。

残る2節は本弾の小さなエンジン拡張で解ける:

- 形D（T840、dmrp06-001 の第2節）: 「相手の呪文の効果またはクリーチャーの
  能力によって、自分のカードが山札の一番下に置かれた時」。
  (1) move レコードに position を載せる（_record_for と _apply_one の
  両方。片方だけでは置換照合か誘発照合のどちらかが欠ける）。
  (2) when の cause.kind がリストを受け付ける（defn のリスト形と対）。
  when に position を書いた能力は rustcore._simple_when の対象外
  （キー集合の条件）で Python パスになる。
- 形E（T846、dmr20-038 の第1節）: choose で選んだクリーチャーを
  delayed_trigger の subject: {ref: 変数} で束縛し、battle_win で
  アンタップする。新語彙なし（choose op の docstring 通りの型）。

新規 GameState フィールドなし（Rust state.rs の同期は不要）。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import DefError, load_tables, parse_card
from dmsim.engine.rustcore import _simple_when

TABLES = load_tables()

FORM_D_WHEN = {"event": "move", "to": "deck", "position": "bottom",
               "subject": {"owner": "you"},
               "cause": {"by": "opp", "kind": ["spell", "ability"]}}


# ---------- parse と検証 ----------

def test_proto_forms_parse():
    from tests._conv_cache import proto_card
    for tid in ("T837", "T838", "T839", "T840", "T841", "T842", "T843",
                "T844", "T845", "T846"):
        d = parse_card(proto_card(tid), TABLES)
        assert d.id == tid
    # 形D の when は Rust の単純条件の対象外（position / cause を含む）
    assert _simple_when(FORM_D_WHEN) is False


def test_when_position_validation():
    base = {"id": "X1", "name": "x", "types": ["creature"], "civs": ["fire"],
            "cost": 1, "power": 1000, "mana": 1,
            "abilities": [{"kind": "trigger",
                           "when": {"event": "move", "to": "deck",
                                    "position": "middle", "subject": "self"},
                           "effect": [{"op": "draw", "count": 1}]}]}
    with pytest.raises(DefError):
        parse_card(base, TABLES)
    base["abilities"][0]["when"]["position"] = "bottom"
    parse_card(base, TABLES)   # 正しい位置指定は通る


def test_cause_kind_list_validation():
    def card(kind):
        return {"id": "X2", "name": "x", "types": ["creature"],
                "civs": ["fire"], "cost": 1, "power": 1000, "mana": 1,
                "abilities": [{"kind": "trigger",
                               "when": {"event": "move", "to": "deck",
                                        "subject": {"owner": "you"},
                                        "cause": {"by": "opp", "kind": kind}},
                               "effect": [{"op": "draw", "count": 1}]}]}
    parse_card(card(["spell", "ability"]), TABLES)   # リスト形は通る
    parse_card(card("ability"), TABLES)              # 単独形も従来通り
    with pytest.raises(DefError):
        parse_card(card(["spell", "bogus"]), TABLES)
    with pytest.raises(DefError):
        parse_card(card([]), TABLES)


# ---------- 駆動ヘルパ ----------

def _keys(d):
    return [o["key"] for o in d["options"]]


def _drive(e, on_dec, limit=600):
    """on_dec(e, d) の戻り値: "stop" なら止める。True ならその決定は
    on_dec が答え済み（または処理済み）として既定の答えを付けない。
    False/None なら既定の答え（no_block → pass → 先頭から min 個）で進める。
    on_dec が答えたのに False を返すと二重に答えて IllegalAnswer になる。"""
    for _ in range(limit):
        if e.s.result is not None:
            return
        d = e.advance()
        if d is None:
            return
        r = on_dec(e, d)
        if r == "stop":
            return
        if r:
            continue
        keys = _keys(d)
        if "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))


def _cast(e, player, defn, choose_defn=None):
    """player が defn を唱え/召喚し、解決が終わるまで進める。
    choose_defn を渡すと choose_cards ではその defn のカードを選ぶ。"""
    state = {"done": False}

    def on_dec(e, d):
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == player \
                and f"play:{defn}" in keys:
            state["played"] = True
            e.answer([keys.index(f"play:{defn}")])
            return True
        if d["kind"] == "pay_mana":
            e.answer([0])
            return True
        if d["kind"] == "choose_cards" and choose_defn is not None:
            for i, o in enumerate(d["options"]):
                if e.cdef(o["cid"]).id == choose_defn:
                    e.answer([i])
                    return True
            e.answer(list(range(d.get("min", 0))))
            return True
        if state.get("played") and d["kind"] in ("main", "charge") \
                and d.get("player") == player:
            state["done"] = True     # 解決後の自分の決定に戻った
            return "stop"
        return False

    _drive(e, on_dec)
    return state["done"]


def _hand_n(e, p):
    return len(e.zlist("hand", p))


def _deck(e, p):
    return list(e.zlist("deck", p))


def _in_gy(e, defn, p):
    return any(e.cdef(c).id == defn for c in e.zlist("graveyard", p))


# ---------- 形A: 数の条件つき no_lose ----------

def test_form_a_immune_when_outnumbering(rules):
    e = setup(rules, {"bz": ["T837", "T001", "T001"]}, {"bz": ["T001"]})
    for reason in ("deck_out", "direct_attack", "effect", "state"):
        assert e._lose_immune(0, reason) is True
        assert e._lose_immune(1, reason) is False   # 相手は守られない


def test_form_a_not_immune_when_not_outnumbering(rules):
    e = setup(rules, {"bz": ["T837", "T001"]}, {"bz": ["T001", "T001"]})
    assert e._lose_immune(0, "deck_out") is False   # 同数では守られない
    e = setup(rules, {"bz": ["T837"]}, {"bz": ["T001", "T001"]})
    assert e._lose_immune(0, "effect") is False     # 少なければ守られない


def test_form_a_effect_lose_blocked_in_game(rules):
    e = setup(rules, {"bz": ["T837", "T001", "T001"], "hand": ["T845"],
                      "mana": ["T008"]},
              {"bz": ["T001"]})
    _cast(e, 0, "T845")   # 効果による敗北を自分にかける
    assert e.s.result is None          # 数が多い間は敗北しない
    assert _in_gy(e, "T845", 0)        # 呪文自体は解決されている


def test_form_a_effect_lose_applies_when_outnumbered(rules):
    e = setup(rules, {"bz": ["T837"], "hand": ["T845"], "mana": ["T008"]},
              {"bz": ["T001", "T001"]})
    _cast(e, 0, "T845")
    assert e.s.result is not None
    assert e.s.result["winner"] == 1 and e.s.result["reason"] == "effect"


# ---------- 形B: タップ中だけ no_lose ----------

def test_form_b_immune_only_while_tapped(rules):
    e = setup(rules, {"bz": ["T838"]}, {})
    assert e._lose_immune(0, "deck_out") is False
    assert e._lose_immune(0, "direct_attack") is False
    cid = next(c for c in e.zlist("bz", 0) if e.cdef(c).id == "T838")
    e.s.cards[cid].tapped = True
    assert e._lose_immune(0, "deck_out") is True
    assert e._lose_immune(0, "direct_attack") is True
    assert e._lose_immune(1, "deck_out") is False


# ---------- 形C: 手札からの敗北置換（攻撃以外） ----------

def test_form_c_candidates_by_reason(rules):
    e = setup(rules, {"hand": ["T839"]}, {"bz": ["T001"]})
    assert e._lose_candidates(0, "direct_attack") == []   # 攻撃による敗北は対象外
    for reason in ("deck_out", "state", "effect"):
        cands = e._lose_candidates(0, reason)
        assert len(cands) == 1
        assert e.cdef(cands[0][0]).id == "T839"
    assert e._lose_candidates(1, "effect") == []          # 相手の敗北は守らない


def _cast_lose_and_answer(e, accept):
    """T845（効果で自分が負ける）を唱え、lose_replace の諮問に答える。
    戻り値: lose_replace 決定を見たか。"""
    seen = {"v": False}

    def on_dec(e, d):
        keys = _keys(d)
        if seen["v"]:
            return "stop"          # 置換の諮問に答えた後の最初の決定で止める
        if d["kind"] == "main" and d.get("player") == 0 and "play:T845" in keys:
            e.answer([keys.index("play:T845")])
            return True
        if d["kind"] == "pay_mana":
            e.answer([0])
            return True
        if d["kind"] == "lose_replace":
            seen["v"] = True
            if accept:
                e.answer([next(i for i, k in enumerate(keys)
                               if k.startswith("lose_replace:T839"))])
            else:
                e.answer([keys.index("decline")])
            return True
        return False

    _drive(e, on_dec)
    return seen["v"]


def test_form_c_accept_discards_and_survives(rules):
    e = setup(rules, {"hand": ["T839", "T845"], "mana": ["T008"]},
              {"bz": ["T001"]})
    assert _cast_lose_and_answer(e, accept=True)
    assert e.s.result is None                    # 敗北は置換された
    assert _in_gy(e, "T839", 0)                  # かわりに手札のこのカードを捨てた
    assert not any(e.cdef(c).id == "T839" for c in e.zlist("hand", 0))


def test_form_c_decline_loses(rules):
    e = setup(rules, {"hand": ["T839", "T845"], "mana": ["T008"]},
              {"bz": ["T001"]})
    assert _cast_lose_and_answer(e, accept=False)
    assert e.s.result is not None
    assert e.s.result["winner"] == 1 and e.s.result["reason"] == "effect"


def test_form_c_direct_attack_not_replaced(rules):
    e = setup(rules, {"hand": ["T839"], "shield": []},
              {"bz": ["T034"], "mana": ["T001"] * 3})
    seen = {"v": False}

    def on_dec(e, d):
        keys = _keys(d)
        if d["kind"] == "lose_replace":
            seen["v"] = True
            e.answer([keys.index("decline")])
            return True
        if d["kind"] == "attack" and d.get("player") == 1 \
                and "attack:T034:player" in keys:
            e.answer([keys.index("attack:T034:player")])
            return True
        return False

    _drive(e, on_dec)
    assert seen["v"] is False                    # 諮問自体が起きない
    assert e.s.result is not None
    assert e.s.result["winner"] == 1
    assert e.s.result["reason"] == "direct_attack"


# ---------- 形D: 相手の効果で山札の一番下に置かれた時 ----------

def _opp_act(e, defn, choose_defn):
    """相手（P1）が defn を使い choose_defn を対象に取るまで進める。
    P0 の yes_no（形D の「引いてもよい」）を見たら記録して引く。"""
    seen = {"yes_no": False, "played": False}

    def on_dec(e, d):
        keys = _keys(d)
        if d["kind"] == "yes_no" and d.get("player") == 0:
            seen["yes_no"] = True
            e.answer([0])   # 引く
            return True
        if d["kind"] == "main" and d.get("player") == 1 \
                and f"play:{defn}" in keys:
            seen["played"] = True
            e.answer([keys.index(f"play:{defn}")])
            return True
        if d["kind"] == "pay_mana":
            e.answer([0])
            return True
        if d["kind"] == "choose_cards":
            for i, o in enumerate(d["options"]):
                if e.cdef(o["cid"]).id == choose_defn:
                    e.answer([i])
                    return True
            e.answer(list(range(d.get("min", 0))))
            return True
        if seen["played"] and d["kind"] in ("main", "charge", "attack") \
                and d.get("player") == 1:
            return "stop"   # 解決が終わり、相手の次の決定に戻った
        return False

    _drive(e, on_dec)
    assert seen["played"]
    return seen


def test_form_d_opponent_spell_bottom_draws(rules):
    e = setup(rules, {"bz": ["T840", "T001"]},
              {"bz": ["T001"], "hand": ["T841"], "mana": ["T010"] * 4})
    hand0 = _hand_n(e, 0)
    seen = _opp_act(e, "T841", "T001")
    assert seen["yes_no"] is True
    assert _hand_n(e, 0) == hand0 + 1                    # 1枚引いた
    assert e.cdef(_deck(e, 0)[-1]).id == "T001"          # 一番下に置かれた


def test_form_d_opponent_ability_bottom_draws(rules):
    e = setup(rules, {"bz": ["T840", "T001"]},
              {"bz": ["T001"], "hand": ["T843"], "mana": ["T010"] * 5})
    hand0 = _hand_n(e, 0)
    seen = _opp_act(e, "T843", "T001")
    assert seen["yes_no"] is True          # クリーチャーの能力でも発火する
    assert _hand_n(e, 0) == hand0 + 1
    assert e.cdef(_deck(e, 0)[-1]).id == "T001"


def test_form_d_top_does_not_fire(rules):
    e = setup(rules, {"bz": ["T840", "T001"]},
              {"bz": ["T001"], "hand": ["T842"], "mana": ["T010"] * 4})
    hand0 = _hand_n(e, 0)
    seen = _opp_act(e, "T842", "T001")
    assert seen["yes_no"] is False                       # 一番下でなければ不発
    assert _hand_n(e, 0) == hand0
    assert e.cdef(_deck(e, 0)[0]).id == "T001"           # 山札の上に置かれた


def test_form_d_own_spell_does_not_fire(rules):
    e = setup(rules, {"bz": ["T840", "T001"], "hand": ["T844"],
                      "mana": ["T008"] * 4},
              {"bz": ["T001"]})
    seen = {"yes_no": False}
    casted = {"v": False}

    def on_dec2(e, d):
        keys = _keys(d)
        if d["kind"] == "yes_no" and d.get("player") == 0:
            seen["yes_no"] = True
            e.answer([0])
            return True
        if d["kind"] == "main" and d.get("player") == 0 \
                and "play:T844" in keys:
            casted["v"] = True
            e.answer([keys.index("play:T844")])
            return True
        if d["kind"] == "pay_mana":
            e.answer([0])
            return True
        if d["kind"] == "choose_cards":
            for i, o in enumerate(d["options"]):
                if e.cdef(o["cid"]).id == "T001":
                    e.answer([i])
                    return True
            e.answer(list(range(d.get("min", 0))))
            return True
        if casted["v"] and d["kind"] in ("main", "attack") \
                and d.get("player") == 0:
            return "stop"
        return False

    _drive(e, on_dec2)
    assert casted["v"]
    assert seen["yes_no"] is False               # 自分の呪文では不発（by: opp）
    assert e.cdef(_deck(e, 0)[-1]).id == "T001"  # 一番下には置かれている


# ---------- 形E: 選んだクリーチャーがバトルに勝った時アンタップ ----------

def _form_e(rules, attack_player):
    e = setup(rules, {"bz": ["T001", "T827"], "hand": ["T846"],
                      "mana": ["T034"] * 3},
              {"bz": ["T002"]})
    t001 = next(c for c in e.zlist("bz", 0) if e.cdef(c).id == "T001")
    t002 = next(c for c in e.zlist("bz", 1) if e.cdef(c).id == "T002")
    st = {"chose": False, "cast": False, "attacked": False, "done": False}

    def on_dec(e, d):
        keys = _keys(d)
        if not st["chose"]:
            if d["kind"] == "main" and d.get("player") == 0 \
                    and "play:T846" in keys:
                e.answer([keys.index("play:T846")])
                return True
            if d["kind"] == "pay_mana":
                e.answer([0])
                return True
            if d["kind"] == "choose_cards":
                for i, o in enumerate(d["options"]):
                    if o["cid"] == t001:
                        e.answer([i])
                        st["chose"] = True
                        return True
                e.answer(list(range(d.get("min", 0))))
                return True
            return False
        if not st["cast"]:
            st["cast"] = True        # 解決後の決定に戻った
            if not attack_player:
                e.s.cards[t002].tapped = True   # 攻撃できるようタップさせる
            # この決定自体は下の攻撃処理か既定の答えに回す
        if not st["attacked"]:
            if d["kind"] == "attack" and d.get("player") == 0:
                want = "attack:T001:player" if attack_player \
                    else "attack:T001:T002"
                if want in keys:
                    st["attacked"] = True
                    e.answer([keys.index(want)])
                    return True
                if "pass" in keys:
                    e.answer([keys.index("pass")])
                    return True
            return False
        if d["kind"] in ("main", "charge", "attack") and d.get("player") == 0:
            st["done"] = True
            return "stop"
        return False

    _drive(e, on_dec)
    assert st["cast"] and st["attacked"] and st["done"]
    return e, t001, t002


def test_form_e_untaps_after_battle_win(rules):
    e, t001, t002 = _form_e(rules, attack_player=False)
    assert e.s.cards[t002].zone == "graveyard"   # バトルに負けた側は破壊される
    assert e.s.cards[t001].tapped is False       # 勝ったのでアンタップした


def test_form_e_no_battle_no_untap(rules):
    e, t001, _ = _form_e(rules, attack_player=True)
    assert e.s.cards[t001].tapped is True        # バトルしていないのでタップしたまま
