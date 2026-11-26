"""語彙パイロット第382弾: attack_after_win_condition
（新規語彙: turn_count の履歴 kind に battle_win を追加）。

対象は pure 1件すべて: dm30-033 森の格闘家ガンバレット
（自然 / コスト1 / パワー5000 / ドリームメイト）。
公式テキストは単一条項:
「このターン、自分のクリーチャーがバトルに勝った後で
しか、このクリーチャーは攻撃できない。」

既存部品の確認:
- 「条件を満たさない間は攻撃できない」の常在形は
  promoy21-051 の登録先例（static {affects: self,
  if: {cmp: [{count...}, "<", 3]}, mod: {deny:
  [attack_player, attack_creature]}}、dm23rp2x-044 と
  同型）で確立している。
- しかし条件「このターン自分のクリーチャーがバトルに
  勝った」を見る式が無かった。turn_count の kind に
  battle 系は無く（attack / block / attack_by /
  attack_on だけ）、battle_win レコード自体は combat が
  出しているのに _record_history が集約していなかった。
  よって本弾は最小の新規語彙として履歴 kind
  battle_win を追加する:
  * defs.TURN_COUNT_KINDS に "battle_win" を追加
    （schema は再生成で追随。差分は enum の2行のみ）。
  * events._record_history が battle_win レコードを
    hist:battle_win:<controller> に集約（controller は
    勝者のコントローラ。勝者1体につき1件。相打ちは
    両者とも敗者側（losers_by_power）なのでレコードが
    出ず、数えない。バトルで破壊されなかった敗者も
    勝ちにはならない）。
  * Rust engine.rs の record_history にも同じ集約を
    ミラー（ソース同期のみ。この環境に cargo は無く
    rust_stamp は第364弾以来据え置き＝Python のみ動作）。
  * GameState の新規フィールドは無い（turn_counters は
    既存）ため state.rs のミラーは不要。
    test_rust_schema_sync は Card/GameState の
    フィールド一致だけを見るので影響しない。

確立形:
- abilities = [static {affects: self, if: {cmp:
  [{turn_count: {kind: battle_win, owner: you}},
  "==", 0]}, mod: {deny: [attack_player,
  attack_creature]}}] の1件。
  勝ちが1件でも記録されれば if が落ちて deny が消える。
  カウンタはターン開始にリセットされるため、相手の
  ターンの勝ちは持ち越さない。owner: you なので相手の
  クリーチャーの勝ちは数えない。ガンバレット自身の
  勝ちも（効果で先にバトルした場合など）数に入る
  （公式テキストの「自分のクリーチャー」に含まれる）。

partial は骨格（types [creature] / civs [nature] /
cost 1 / power 5000 / races [ドリームメイト]、
abilities 無し）で、text は条項の短縮メモのため、
提出形では text に行の公式テキスト全文を入れる
（補完あり。ラウンド417への注意に明記）。alias は無い。
単面カードで未検証の面は無い。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い。

proto: T1138（dm30-033 型）。判別役は新規フィクスチャ
T1139（パワー6000の素アタッカー。T1140 に勝つ役）/
T1140（パワー4000ブロッカー。T1139 には負け、
T1105 とは相打ちになる役）と既存 proto T1105
（パワー4000ブロッカー。第367弾。相打ち役として流用）。

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
          "if": {"cmp": [{"turn_count": {"kind": "battle_win",
                                         "owner": "you"}},
                         "==", 0]},
          "mod": {"deny": ["attack_player", "attack_creature"]}}
FORM = [STATIC]
FULL_TEXT = ("このターン、自分のクリーチャーがバトルに勝った"
             "後でしか、このクリーチャーは攻撃できない。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1138")
    assert c["name"] == "森の格闘家ガンバレット"
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 1 and c["power"] == 5000 and c["mana"] == 1
    assert c["races"] == ["ドリームメイト"]
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(c, TABLES)
    assert d.abilities == FORM


def test_unknown_turn_count_kind_rejected(rules):
    # turn_count の kind は TURN_COUNT_KINDS の列挙で検証され、
    # 未知の kind（battle_won は誤記）は DefError
    bad = copy.deepcopy(proto_card("T1138"))
    bad["abilities"] = [{"kind": "static", "affects": "self",
                         "if": {"cmp": [{"turn_count":
                                         {"kind": "battle_won",
                                          "owner": "you"}}, "==", 0]},
                         "mod": {"deny": ["attack_player"]}}]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


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


def test_cannot_attack_before_any_win(rules):
    # 勝ちが無いターンでは攻撃できない: _attack_options は
    # 攻撃可能な選択肢の列挙そのもの（combat._attack_options。
    # 攻撃の選択肢が pass だけの attack 決定は自動回答されて
    # 表面化しないため、直接照合する。第179弾の作法）
    e = _build(rules, {"bz": ["T1138"]}, {"bz": []})
    assert e._attack_options(0) == []
    cid = next(c for c in e.zlist("bz", 0)
               if e.s.cards[c].defn == "T1138")
    assert not e.permits(cid, "attack_player")
    assert not e.permits(cid, "attack_creature")


def test_can_attack_after_ally_battle_win(rules):
    # 味方 T1139（6000）が T1140（4000ブロッカー）に勝った
    # 後では、同じターンの次の attack 決定でガンバレットが
    # 攻撃でき、実際にシールドを1枚ブレイクする
    e = _build(rules, {"bz": ["T1138", "T1139"]}, {"bz": ["T1140"]})
    shields_before = len(e.zlist("shield", 1))
    state = {}
    for _ in range(4000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if e.s.turn_counters.get("hist:battle_win:0"):
            state["won"] = True
            state["win_count"] = e.s.turn_counters["hist:battle_win:0"]
        if d["kind"] == "charge" and d.get("player") == 0 \
                and state.get("ganba_attacked"):
            break
        if d["kind"] == "attack" and d.get("player") == 0:
            if not state.get("first_done"):
                # 1回目: ガンバレットはまだ攻撃できない
                assert not any(k.startswith("attack:T1138")
                               for k in keys), keys
                state["first_done"] = True
                e.answer([keys.index("attack:T1139:player")])
                continue
            if state.get("won") and not state.get("ganba_attacked"):
                # 勝ちの後: ガンバレットの攻撃が選択肢に出る
                assert "attack:T1138:player" in keys, keys
                state["ganba_attacked"] = True
                e.answer([keys.index("attack:T1138:player")])
                continue
            _answer_default(e, d)
        elif d["kind"] == "block":
            pick = [i for i, k in enumerate(keys)
                    if k.startswith("bz:T1140")]
            if pick and not state.get("won"):
                e.answer([pick[0]])
            else:
                e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        else:
            _answer_default(e, d)
    assert state.get("first_done") and state.get("won"), state
    assert state.get("ganba_attacked"), state
    # 勝ちはバトル直後に1件だけ記録されていた（ループ終了時は
    # 次のターンに入ってリセット済みのため、観測値で確認）
    assert state.get("win_count") == 1
    assert "T1140" in [e.s.cards[c].defn
                       for c in e.zlist("graveyard", 1)]
    assert len(e.zlist("shield", 1)) == shields_before - 1


def test_draw_does_not_unlock(rules):
    # 相打ち（4000 vs 4000）は「バトルに勝った」ではない:
    # 勝ちは記録されず、ガンバレットは攻撃できないまま
    e = _build(rules, {"bz": ["T1138", "T1105"]}, {"bz": ["T1140"]})
    state = {}
    for _ in range(4000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 \
                and not state.get("first_done"):
            state["first_done"] = True
            e.answer([keys.index("attack:T1105:player")])
            continue
        if d["kind"] == "block":
            pick = [i for i, k in enumerate(keys)
                    if k.startswith("bz:T1140")]
            if pick:
                state["blocked"] = True
                e.answer([pick[0]])
            else:
                e.answer([keys.index("no_block")])
            continue
        if state.get("blocked") and d["kind"] == "charge":
            break   # バトルは解決済み（次のターンの charge）
        _answer_default(e, d)
    assert state.get("first_done") and state.get("blocked"), state
    assert not e.s.turn_counters.get("hist:battle_win:0")
    assert "T1105" in [e.s.cards[c].defn
                       for c in e.zlist("graveyard", 0)]
    assert "T1140" in [e.s.cards[c].defn
                       for c in e.zlist("graveyard", 1)]
    # 相打ちの後でもガンバレットは攻撃できない
    assert not any(o["key"].startswith("attack:T1138")
                   for o in e._attack_options(0))


def test_opponent_win_on_opponent_turn_does_not_unlock(rules):
    # 相手のターンに相手のクリーチャーが勝っても、
    # 自分の次のターンでは数え直し（リセット＋owner: you）
    # のため、ガンバレットは攻撃できない
    e = _build(rules, {"bz": ["T1138", "T1105"]}, {"bz": ["T1139"]})
    state = {}
    for _ in range(6000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 \
                and not state.get("snapshot"):
            # 自分のターン（勝ちなし）: T1105 だけが攻撃でき、
            # ガンバレットは出ない。攻撃は見送る
            assert not any(k.startswith("attack:T1138")
                           for k in keys), keys
            e.answer([keys.index("pass")])
            continue
        if d["kind"] == "attack" and d.get("player") == 1 \
                and not state.get("opp_attacked"):
            state["opp_attacked"] = True
            e.answer([keys.index("attack:T1139:player")])
            continue
        if d["kind"] == "block" and state.get("opp_attacked") \
                and not state.get("blocked"):
            pick = [i for i, k in enumerate(keys)
                    if k.startswith("bz:T1105")]
            if pick:
                state["blocked"] = True
                e.answer([pick[0]])
                continue
            e.answer([keys.index("no_block")])
            continue
        if state.get("blocked") and d["kind"] == "charge" \
                and d.get("player") == 0:
            break   # 自分の次のターンに入った
        _answer_default(e, d)
    assert state.get("opp_attacked") and state.get("blocked"), state
    # 相手ターン内の勝ちは prev_counters（前のターンの退避）に
    # 相手側の1件だけ残る。自側には記録されていない
    prev = e.s.prev_counters
    assert prev.get("hist:battle_win:1") == 1, prev
    assert not prev.get("hist:battle_win:0"), prev
    # 自分のターンではカウンタはリセットされ、攻撃できない
    assert not e.s.turn_counters.get("hist:battle_win:1")
    assert not any(o["key"].startswith("attack:T1138")
                   for o in e._attack_options(0))
