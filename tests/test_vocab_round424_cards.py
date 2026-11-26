"""再変換ラウンド424（第389弾 mill_count_variable）の記録テスト。

- 新規登録1件: dmex10-014 死罠の杖
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 闇・自然 / コスト4 / パワー5000 /
  種族 ビーストフォーク・不死樹王国、mana 1、
  keywords・abilities ともに無し〕に第389弾の
  確立形1能力〔CIP 誘発 [choose {select: {zone: bz,
  owner: opp, filter: {types: [creature]}, count: 1},
  as: pick}, mana_put {select: {ref: pick}},
  mill {owner: you, count: {cost_of: pick}}]〕を
  足し、unsupported を外したもの。abilities は
  この1件ちょうど、keywords は無いまま。補完あり:
  partial の text は条項の断片のみのため、text には
  行の公式テキスト全文を入れた）。
- 正本判定は通常型: identity 実測で canon_id は
  対象 id 自身が正本、alias は無い。alias
  畳み込み0件・stale クリーンアップ0件・
  差し戻し0件。
- reopen（mill_count_variable）の出力は対象1件
  ちょうど（対象行は reason == "vocab" で
  gaps = [mill_count_variable]）。
  mill_count_variable は完全解消。
- converted 10,368→10,369 / rejects 1,944→1,943
  （reopen −1 のみ）、canonical 重なり0・漏れ0。
- mill の count への式渡し（{cost_of: pick}）は
  本カードが初の登録（回帰に test_data_audit を
  含めて確認済み）。
- dm02-046 の stale 行・dm14-073 の既存データ負債・
  schema.py の turn_count への from 同期漏れ
  （第387弾で観察）は本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第389弾本体と同形（対象を proto T1154 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第389弾の proto を流用: T1110（コスト5）/
T1109（コスト3）/ T127・T001（マナ用）。
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
from tests.test_vocab_pilot389 import FORM, FULL_TEXT, MANA  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmex10-014"
GAP = "mill_count_variable"
NAME = "死罠の杖"


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


def test_round424_disposition():
    rej = _reject_rows()
    assert len(rej) == 1943
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10369
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = {rid for rid, r in rej.items() if GAP in (r.get("gaps") or [])}
    assert fam == set()                  # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"]
    assert c["civs"] == ["darkness", "nature"]
    assert c["cost"] == 4 and c["power"] == 5000 and c["mana"] == 1
    assert c["races"] == ["ビーストフォーク", "不死樹王国"]
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    # 登録形は提出形と完全一致: 確立形1能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 1
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第389弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1=None):
    return scenario.build(rules, {"p0": p0, "p1": p1 or {},
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _boring(d):
    keys = [o["key"] for o in d["options"]]
    for want in ("pass", "end_turn", "end_attack", "end_phase"):
        if want in keys:
            return [keys.index(want)]
    return [0]


def _summon(rules, p1, choose_defn=None):
    """p0 が登録カードを召喚し、CIP の choose に答えて解決まで
    進める。（engine, 召喚したか, choose 判断が出たか）を返す。"""
    e = _build(rules, {"hand": [TARGET], "mana": MANA}, p1)
    played = False
    chose = False
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and d.get("player") == 0 \
                and f"play:{TARGET}" in keys:
            played = True
            e.answer([keys.index(f"play:{TARGET}")])
            continue
        if played and d["kind"] == "choose_cards":
            chose = True
            idx = [i for i, o in enumerate(d["options"])
                   if choose_defn in o["key"]]
            assert idx, f"{choose_defn} が選択肢に無い: {keys}"
            e.answer(idx[:1])
            continue
        if played and d["kind"] in ("main", "charge", "attack"):
            break          # 解決が終わり次の通常判断に戻った
        e.answer(_boring(d))
    return e, played, chose


def _mana_defns(e, p):
    return [e.cdef(c).id for c in e.zlist("mana", p)]


def test_registered_cost5_to_mana_and_mill_five(rules):
    """登録カード: 相手のコスト5（T1110）を選ぶと持ち主の
    マナゾーンに置かれ、自分の山札の上から5枚が墓地に
    置かれる（mill の式 count の初の登録カードでの判別）。"""
    e, played, chose = _summon(rules, {"bz": ["T1110"]}, "T1110")
    assert played
    assert chose is False           # 候補1体では選択判断が出ず自動で決まる
    assert _mana_defns(e, 1) == ["T1110"]       # 持ち主のマナへ
    moved = next(c for c in e.zlist("mana", 1)
                 if e.cdef(c).id == "T1110")
    assert e.s.cards[moved].tapped is False     # 状態は引き継ぐ
    assert len(e.zlist("graveyard", 0)) == 5    # コスト5 → 5枚ミル
    assert TARGET in [e.cdef(c).id for c in e.zlist("bz", 0)]


def test_registered_choose_cost3_mills_three(rules):
    """登録カード: 候補2体からコスト3を選ぶとミルは3枚で、
    コスト5はバトルゾーンに残る。"""
    e, played, chose = _summon(rules, {"bz": ["T1109", "T1110"]},
                               "T1109")
    assert played and chose
    assert _mana_defns(e, 1) == ["T1109"]
    assert len(e.zlist("graveyard", 0)) == 3
    opp_bz = [e.cdef(c).id for c in e.zlist("bz", 1)
              if e.s.cards[c].controller == 1]
    assert opp_bz == ["T1110"]


def test_registered_no_target_no_mill(rules):
    """登録カード: 相手のクリーチャーが無ければ0枚で
    解決が終わる。"""
    e, played, chose = _summon(rules, {})
    assert played
    assert chose is False
    assert len(e.zlist("graveyard", 0)) == 0
    assert TARGET in [e.cdef(c).id for c in e.zlist("bz", 0)]
