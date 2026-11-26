"""再変換ラウンド417（第382弾 attack_after_win_condition）の記録テスト。

- 新規登録1件: dm30-033 森の格闘家ガンバレット
  （登録形は提出形と完全一致: partial の骨格〔自然 /
  コスト1 / パワー5000 / 種族 ドリームメイト、
  mana 1、keywords・abilities ともに無し〕に
  第382弾の確立形 static 1件〔{affects: self,
  if: {cmp: [{turn_count: {kind: battle_win,
  owner: you}}, "==", 0]}, mod: {deny:
  [attack_player, attack_creature]}}〕（promoy21-051
  の登録先例と同形。条件の履歴 kind battle_win は
  第382弾で追加した新規語彙）を足し、unsupported を
  外したもの。abilities は static 1件ちょうど、
  keywords は無いまま。補完あり: partial の text は
  条項の短縮メモのため、text には行の公式テキスト
  全文を入れた。本カードは新規 kind battle_win を
  使う初の登録カード）。
- alias 畳み込み0件（alias は無い）。正本判定:
  対象 id を real.yaml / real_akashic.yaml /
  real_vocab.yaml / real_zone.yaml / proto.yaml /
  converted.yaml と照合し、いずれにも登録なし
  （proto.yaml のヒットは T1138 の notes 内参照
  のみ）。identity 実測で canon_id(dm30-033) =
  dm30-033、aliases_for は []。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [attack_after_win_condition]
  のため reopen で外してから submit（reopen の
  出力は対象1件ちょうど）。
- converted 10,361→10,362 / rejects 1,951→1,950、
  canonical 重なり0・漏れ0。attack_after_win_
  condition はファミリーがこの1件だけだったため
  完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）と dm14-073 の既存データ負債は
  判断待ちのため本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第382弾本体と同形（対象を proto T1138 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第382弾の proto を流用: T1139（パワー6000の素
アタッカー。勝ち役）/ T1140（パワー4000ブロッカー）/
T1105（パワー4000ブロッカー。相打ち役）。
バトルゾーンは共有ゾーンなので所有は bz_tops(p) /
zlist(zone, p) で見る。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests import _conv_cache  # noqa: E402
from tests.test_vocab_pilot382 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm30-033"
GAP = "attack_after_win_condition"
NAME = "森の格闘家ガンバレット"


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_round417_disposition():
    rej = _reject_rows()
    assert len(rej) == 1950
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10362
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 1 and c["power"] == 5000 and c["mana"] == 1
    assert c["races"] == ["ドリームメイト"]
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    # 登録形は提出形と完全一致: 確立形 static 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("keywords")         # keywords は無いまま
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d.abilities == FORM
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第382弾本体と同形、対象は登録カード） ----------

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


def test_registered_cannot_attack_before_any_win(rules):
    # 勝ちが無いターンでは登録カードは攻撃できない
    e = _build(rules, {"bz": [TARGET]}, {"bz": []})
    assert e._attack_options(0) == []
    cid = next(c for c in e.zlist("bz", 0)
               if e.s.cards[c].defn == TARGET)
    assert not e.permits(cid, "attack_player")
    assert not e.permits(cid, "attack_creature")


def test_registered_can_attack_after_ally_battle_win(rules):
    # 味方 T1139（6000）が T1140（4000ブロッカー）に勝った
    # 後では、同じターンの次の attack 決定で登録カードが
    # 攻撃でき、実際にシールドを1枚ブレイクする
    e = _build(rules, {"bz": [TARGET, "T1139"]}, {"bz": ["T1140"]})
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
                # 1回目: 登録カードはまだ攻撃できない
                assert not any(k.startswith(f"attack:{TARGET}")
                               for k in keys), keys
                state["first_done"] = True
                e.answer([keys.index("attack:T1139:player")])
                continue
            if state.get("won") and not state.get("ganba_attacked"):
                # 勝ちの後: 登録カードの攻撃が選択肢に出る
                assert f"attack:{TARGET}:player" in keys, keys
                state["ganba_attacked"] = True
                e.answer([keys.index(f"attack:{TARGET}:player")])
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
    assert state.get("win_count") == 1
    assert "T1140" in [e.s.cards[c].defn
                       for c in e.zlist("graveyard", 1)]
    assert len(e.zlist("shield", 1)) == shields_before - 1


def test_registered_draw_does_not_unlock(rules):
    # 相打ち（4000 vs 4000）は「バトルに勝った」ではない:
    # 勝ちは記録されず、登録カードは攻撃できないまま
    e = _build(rules, {"bz": [TARGET, "T1105"]}, {"bz": ["T1140"]})
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
    # 相打ちの後でも登録カードは攻撃できない
    assert not any(o["key"].startswith(f"attack:{TARGET}")
                   for o in e._attack_options(0))


def test_registered_opponent_win_on_opponent_turn_does_not_unlock(rules):
    # 相手のターンに相手のクリーチャーが勝っても、
    # 自分の次のターンでは数え直し（リセット＋owner: you）
    # のため、登録カードは攻撃できない
    e = _build(rules, {"bz": [TARGET, "T1105"]}, {"bz": ["T1139"]})
    state = {}
    for _ in range(6000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 \
                and not state.get("snapshot"):
            # 自分のターン（勝ちなし）: T1105 だけが攻撃でき、
            # 登録カードは出ない。攻撃は見送る
            assert not any(k.startswith(f"attack:{TARGET}")
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
    # 相手ターン内の勝ちは prev_counters に相手側の1件だけ残る
    prev = e.s.prev_counters
    assert prev.get("hist:battle_win:1") == 1, prev
    assert not prev.get("hist:battle_win:0"), prev
    # 自分のターンではカウンタはリセットされ、攻撃できない
    assert not e.s.turn_counters.get("hist:battle_win:1")
    assert not any(o["key"].startswith(f"attack:{TARGET}")
                   for o in e._attack_options(0))
