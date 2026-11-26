"""再変換ラウンド432（第397弾 mana_placed_count_this_turn）の記録テスト。

- 新規登録1件: dmrp06-027 マ・スクメーロ・タンク
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 自然 / コスト4 / パワー8000 /
  種族 グランセクト、mana 1、keywords
  [double_breaker, enters_tapped]、abilities は
  static {affects: self, mod: {deny:
  [untap_at_start]}} の1件が構築済み〕に第397弾の
  確立形 trigger〔when {event: move, to: mana,
  subject: {owner: you}, ord: {kind: mana_put,
  ge: 2}} → untap {select: {ref: self}}〕を足し、
  unsupported を外したもの。abilities はこの
  2件ちょうど〔static → trigger の条項順〕、
  keywords は [double_breaker, enters_tapped]
  のまま。**補完なし**: partial の text は行の
  公式テキスト全文と一致）。
- 正本判定は通常型: identity 実測で canon_id は
  対象自身、aliases_for = []（alias は無い）。
  alias 畳み込み0件・stale クリーンアップ0件・
  差し戻し0件。
- reopen（mana_placed_count_this_turn）の出力は
  対象1件ちょうど（対象行は reason == "vocab"）。
- converted 10,376→10,377 / rejects 1,936→1,935、
  canonical 重なり0・漏れ0。
  mana_placed_count_this_turn は完全解消。
- 確立形は登録先例 dm23rp2x-047 の ord {kind:
  mana_put, eq: 2} の比較を ge: 2 に変えた形
  （新規フィールドではない。回帰に test_data_audit
  と hist_counters 本体・第390弾本体を含めて
  確認済み）。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）は本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第397弾本体と同形（対象を proto T1164 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第397弾の proto を流用: T002（CIP で自分の山札の
上から1枚をマナゾーンに置く＝2枚目以降のマナ
置き役）/ T001（自然クリーチャー＝マナ役・
チャージ役）。
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
from tests.test_vocab_pilot397 import FORM, FULL_TEXT, TRIGGER  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmrp06-027"
GAP = "mana_placed_count_this_turn"
NAME = "マ・スクメーロ・タンク"


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


def test_round432_disposition():
    rej = _reject_rows()
    assert len(rej) == 1935
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10377
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = {rid for rid, r in rej.items() if GAP in (r.get("gaps") or [])}
    assert fam == set()                  # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 4 and c["power"] == 8000 and c["mana"] == 1
    assert c["races"] == ["グランセクト"]
    assert c["keywords"] == ["double_breaker", "enters_tapped"]
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完なし）
    # 登録形は提出形と完全一致: 確立形2能力ちょうど（条項順）
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert TRIGGER in d.abilities
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第397弾本体と同形、対象は登録カード） ----------

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


def _mine(e):
    return next(c for c in e.zlist("bz", 0)
                if e.cdef(c).id == TARGET)


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


def test_registered_first_put_does_not_untap_second_does(rules):
    # 登録カード: 召喚するとタップして出て（enters_tapped）、
    # 次の自分のターンのはじめにもアンタップしない
    # （deny untap_at_start）。そのターンのチャージ
    # （1枚目のマナ置き＝ord 1）ではアンタップせず、
    # T002 の CIP（2枚目＝ord 2）でアンタップする。
    # カウンタのターン開始リセットもチャージ時点の
    # 不発で判別する（第397弾本体と同形）
    e = _build(rules,
               {"hand": [TARGET, "T002", "T002"],
                "mana": ["T001"] * 6},
               {"bz": []})
    cid_box = {}

    def script(e, d, st):
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and not st.get("summoned"):
            assert f"play:{TARGET}" in keys, keys
            st["summoned"] = True
            e.answer([keys.index(f"play:{TARGET}")])
            return True
        if st.get("summoned") and not st.get("entered"):
            st["entered"] = True
            cid_box["cid"] = _mine(e)
            # タップして出る（enters_tapped）
            assert e.s.cards[cid_box["cid"]].tapped is True
            return False
        if d["kind"] == "charge" and d.get("player") == 0 \
                and st.get("entered") and not st.get("charged2"):
            # 自分の2ターン目のはじめ: アンタップステップを
            # 過ぎてもタンクはタップしたまま（deny の判別）
            assert e.s.cards[cid_box["cid"]].tapped is True
            st["charged2"] = True
            charges = [k for k in keys if k.startswith("charge:")]
            assert charges, keys
            e.answer([keys.index(charges[0])])
            return True
        if d["kind"] == "main" and d.get("player") == 0 \
                and st.get("charged2") and not st.get("played2"):
            # チャージ直後の main: 1枚目（ord 1）では
            # 発火していないことを確認してから T002 を出す
            assert e.s.turn_counters.get("hist:mana_put:0") == 1
            assert e.s.cards[cid_box["cid"]].tapped is True
            assert "play:T002" in keys, keys
            st["played2"] = True
            e.answer([keys.index("play:T002")])
            return True
        if st.get("played2") and not st.get("after_cip"):
            if d["kind"] in ("main", "attack"):
                st["after_cip"] = True
                # 2枚目（ord 2）で発火してアンタップする
                assert e.s.turn_counters.get("hist:mana_put:0") == 2
                assert e.s.cards[cid_box["cid"]].tapped is False
                st["done"] = True
                return True
            return False
        return False

    _drive(e, script)


def test_registered_third_put_also_untaps_ge_not_eq(rules):
    # 登録カード: ge: 2 の判別 — 3枚目のマナ置きでも
    # 発火する（登録先例 dm23rp2x-047 の eq: 2 では
    # 発火しない）。第397弾本体と同形
    e = _build(rules,
               {"hand": [TARGET, "T002", "T002"],
                "mana": ["T001"] * 6},
               {"bz": []})
    cid_box = {}

    def script(e, d, st):
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and not st.get("summoned"):
            st["summoned"] = True
            e.answer([keys.index(f"play:{TARGET}")])
            return True
        if st.get("summoned") and not st.get("entered"):
            st["entered"] = True
            cid_box["cid"] = _mine(e)
            return False
        if d["kind"] == "charge" and d.get("player") == 0 \
                and st.get("entered") and not st.get("charged2"):
            st["charged2"] = True
            charges = [k for k in keys if k.startswith("charge:")]
            e.answer([keys.index(charges[0])])
            return True
        if d["kind"] == "main" and d.get("player") == 0 \
                and st.get("charged2") and not st.get("played1"):
            st["played1"] = True
            e.answer([keys.index("play:T002")])
            return True
        if d["kind"] == "main" and d.get("player") == 0 \
                and st.get("played1") and not st.get("played2"):
            # 2枚目の CIP でアンタップしていることを確認し、
            # 3枚目の判別のためタップ状態へ戻してから
            # 2体目の T002 を出す
            assert e.s.cards[cid_box["cid"]].tapped is False
            e.s.cards[cid_box["cid"]].tapped = True
            assert "play:T002" in keys, keys
            st["played2"] = True
            e.answer([keys.index("play:T002")])
            return True
        if st.get("played2") and not st.get("after3"):
            if d["kind"] in ("main", "attack"):
                st["after3"] = True
                # 3枚目（ord 3）でも発火する（ge の判別）
                assert e.s.turn_counters.get("hist:mana_put:0") == 3
                assert e.s.cards[cid_box["cid"]].tapped is False
                st["done"] = True
                return True
            return False
        return False

    _drive(e, script)


def test_registered_opponent_mana_put_does_not_untap(rules):
    # 登録カード: owner の判別 — 相手が自分のマナ
    # ゾーンに2枚置いても（相手の ord 2）自分の
    # タンクはアンタップしない。第397弾本体と同形
    e = _build(rules,
               {"bz": [TARGET]},
               {"hand": ["T002", "T002"], "mana": ["T001"] * 4})
    cid = _mine(e)
    e.s.cards[cid].tapped = True   # タップ状態にして観測する

    def script(e, d, st):
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 1 \
                and not st.get("opp_charged"):
            st["opp_charged"] = True
            charges = [k for k in keys if k.startswith("charge:")]
            assert charges, keys
            e.answer([keys.index(charges[0])])
            return True
        if d["kind"] == "main" and d.get("player") == 1 \
                and st.get("opp_charged") and not st.get("opp_played"):
            assert "play:T002" in keys, keys
            st["opp_played"] = True
            e.answer([keys.index("play:T002")])
            return True
        if st.get("opp_played") and not st.get("checked"):
            if d["kind"] in ("main", "attack"):
                st["checked"] = True
                # 相手は2枚置いた（相手のカウンタは2）が、
                # 自分のカウンタは0で、タンクはタップしたまま
                assert e.s.turn_counters.get("hist:mana_put:1") == 2
                assert not e.s.turn_counters.get("hist:mana_put:0")
                assert e.s.cards[cid].tapped is True
                st["done"] = True
                return True
            return False
        return False

    _drive(e, script)
