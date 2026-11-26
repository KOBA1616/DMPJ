"""再変換ラウンド428（第393弾 shield_placed_this_turn_condition）の記録テスト。

- 新規登録1件: dmrp06-062 青守銀 ノチェス
  （登録形は提出形と完全一致: 対象行は partial も
  reason も無い素行のため、骨格は partial 由来では
  なく公式データ〔data/cards/raw/by_product/
  rp06.jsonl の同 id 行: クリーチャー / 光 /
  コスト3 / パワー4500 / 種族 メタリカ、mana 1、
  keywords [blocker]、abilities 無し〕から起こし、
  第393弾の確立形 static〔if {cmp: [{turn_count:
  {kind: shield_put, owner: you}}, "==", 0]} の間
  mod: {deny: [attack_player]}〕1件を足したもの。
  abilities はこの1件ちょうど、keywords は
  [blocker] のまま。**補完なし**: text は行の
  公式テキスト全文と一致）。
- 正本判定は通常型: identity 実測で canon_id は
  対象 id 自身が正本、alias は無い。alias
  畳み込み0件・stale クリーンアップ0件・
  差し戻し0件。
- reopen（shield_placed_this_turn_condition）の
  出力は0件（対象行に reason が無いため正常。
  ラウンド423の実測どおり）。cmd_submit が登録
  成功時に rejects から行を外し、対象行の消滅を
  実測確認済み。shield_placed_this_turn_condition
  は完全解消。
- converted 10,372→10,373 / rejects 1,940→1,939
  （submit −1 のみ）、canonical 重なり0・漏れ0。
- 確立形は登録済み dmrp08-032 ブロクノ裁徒Z の
  第1能力と同一（shield_put は既存の履歴 kind で
  新規フィールドではない。回帰に test_data_audit
  を含めて確認済み）。
- dm02-046 の stale 行・dm14-073 の既存データ負債・
  schema.py の turn_count への from 同期漏れ
  （第387弾で観察）は本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第393弾本体と同形（対象を proto T1160 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第393弾の proto T245（自盾追加試験呪文）を流用。
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
from tests.test_vocab_pilot393 import FORM, FULL_TEXT, STATIC  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmrp06-062"
GAP = "shield_placed_this_turn_condition"
NAME = "青守銀 ノチェス"


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


def test_round428_disposition():
    rej = _reject_rows()
    assert len(rej) == 1939
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10373
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消（submit で消滅）
    fam = {rid for rid, r in rej.items() if GAP in (r.get("gaps") or [])}
    assert fam == set()                  # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 3 and c["power"] == 4500 and c["mana"] == 1
    assert c["races"] == ["メタリカ"]
    assert c["keywords"] == ["blocker"]
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完なし）
    # 登録形は提出形と完全一致: 確立形 static 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities      # keywords は static に展開される
    assert len(d.abilities) == 2      # blocker の static＋確立形 static
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第393弾本体と同形、対象は登録カード） ----------

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


def _mine(e):
    return next(c for c in e.zlist("bz", 0)
                if e.cdef(c).id == TARGET)


def test_registered_denied_without_shield_put(rules):
    """登録カード: このターンに自分のシールドゾーンに
    カードが置かれていなければ、プレイヤー攻撃だけが
    できない（クリーチャー攻撃は可能＝deny の範囲の判別）。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": []})
    cid = _mine(e)
    assert not e.permits(cid, "attack_player")
    assert e.permits(cid, "attack_creature")
    assert not any(o["key"].startswith(f"attack:{TARGET}")
                   for o in e._attack_options(0))


def test_registered_opponent_shield_put_does_not_unlock(rules):
    """登録カード: owner: you の判別 — 相手の shield_put
    カウントでは解放されず、自分のカウントで解放される。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": []})
    cid = _mine(e)
    e.s.turn_counters["hist:shield_put:1"] = 1   # 相手が置いた分
    assert not e.permits(cid, "attack_player")
    e.s.turn_counters["hist:shield_put:0"] = 1   # 自分が置いた分
    assert e.permits(cid, "attack_player")


def test_registered_unlocked_by_real_shield_put_and_breaks(rules):
    """登録カード: 実フローで T245（自盾追加試験呪文）を
    唱えて自分のシールドを置くと、同じターンにプレイヤーを
    攻撃でき、シールドを1枚ブレイクする（ブレイカー修整なし）。"""
    e = _build(rules, {"bz": [TARGET], "hand": ["T245", "T002"],
                       "mana": ["T001", "T001"]},
               {"bz": []})
    cid = _mine(e)
    assert not e.permits(cid, "attack_player")
    shields_before = len(e.zlist("shield", 1))
    own_shields_before = len(e.zlist("shield", 0))
    state = {}
    for _ in range(4000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and not state.get("cast"):
            assert "play:T245" in keys, keys
            state["cast"] = True
            e.answer([keys.index("play:T245")])
            continue
        if state.get("cast") and not state.get("checked"):
            if d["kind"] in ("main", "attack"):
                state["checked"] = True
                assert e.s.turn_counters.get("hist:shield_put:0") == 1
                assert len(e.zlist("shield", 0)) == own_shields_before + 1
                assert e.permits(cid, "attack_player")
        if d["kind"] == "attack" and d.get("player") == 0 \
                and state.get("checked") and not state.get("attacked"):
            assert f"attack:{TARGET}:player" in keys, keys
            state["attacked"] = True
            e.answer([keys.index(f"attack:{TARGET}:player")])
            continue
        if state.get("attacked") and d["kind"] == "charge":
            break   # 攻撃は解決済み（次のターンの charge）
        _answer_default(e, d)
    assert state.get("cast") and state.get("checked"), state
    assert state.get("attacked"), state
    assert len(e.zlist("shield", 1)) == shields_before - 1  # 1枚ブレイク
    assert e.s.cards[cid].tapped is True
