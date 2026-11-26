"""再変換ラウンド431（第396弾 power_per_civilization）の記録テスト。

- 新規登録1件: dm25-055 虹色の霊光
  （登録形は提出形と完全一致: partial の骨格
  〔呪文 / 自然 / コスト3、mana 1、keywords・
  abilities・spell ともに無し〕に第396弾の
  確立形 spell 4 op〔choose {owner: you,
  as: pick} → set_var {name: p_up, value:
  {mul: [{civ_count: {ref: pick}}, 2000]}} →
  modify {ref: pick, power {amount: {var: p_up}},
  duration: end_of_turn} → draw 1〕を足し、
  unsupported を外したもの。spell はこの4 op
  ちょうど、keywords は無いまま。**補完あり:
  text のみ** — partial の text は条項の断片
  のため、登録形の text は行の公式テキスト全文）。
- 正本判定は通常型: identity 実測で canon_id は
  対象自身、aliases_for = []（alias は無い）。
  alias 畳み込み0件・stale クリーンアップ0件・
  差し戻し0件。
- reopen（power_per_civilization）の出力は
  対象1件ちょうど（対象行は reason == "vocab"）。
- converted 10,375→10,376 / rejects 1,937→1,936、
  canonical 重なり0・漏れ0。
  power_per_civilization は完全解消。
- 確立形は第79弾の式 civ_count を第322弾の
  set_var で修整の生成前に数えて束縛する形
  （新規フィールドではない。回帰に test_data_audit
  を含めて確認済み）。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）は本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第396弾本体と同形（対象を proto T1163 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第396弾の proto を流用: T030（光・水の多色＝
文明2つ役）/ T1157（火・単色＝文明1つ役）/
T001（自然＝マナ役）。
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
from tests.test_vocab_pilot396 import EXPANDED, FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm25-055"
GAP = "power_per_civilization"
NAME = "虹色の霊光"


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


def test_round431_disposition():
    rej = _reject_rows()
    assert len(rej) == 1936
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10376
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = {rid for rid, r in rej.items() if GAP in (r.get("gaps") or [])}
    assert fam == set()                  # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["spell"] and c["civs"] == ["nature"]
    assert c["cost"] == 3 and c["mana"] == 1
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり: text のみ）
    # 登録形は提出形と完全一致: 確立形 spell 4 op ちょうど
    assert c["spell"] == FORM
    assert len(c["spell"]) == 4
    assert not c.get("abilities")
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d.spell == EXPANDED           # マクロ展開後の形（＝提出形）
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第396弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1=None):
    return scenario.build(rules, {"p0": p0, "p1": p1 or {},
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _count(e, zone, p):
    if zone == "bz":
        return len(e.bz_tops(p))
    return len(e.zlist(zone, p))


def _power(e, defn, p=0):
    for c in e.bz_tops(p):
        if e.cdef(c).id == defn:
            return e.chars(c)["power"]
    raise AssertionError(f"{defn} がバトルゾーンに無い")


def _boring(d):
    keys = [o["key"] for o in d["options"]]
    for want in ("pass", "end_turn", "end_attack", "end_phase"):
        if want in keys:
            return [keys.index(want)]
    return [0]


def _cast(rules, p0, p1=None, choose_defn=None):
    """p0 が登録カードを唱え、choose が出れば choose_defn を
    選んで解決まで進める。（engine, 唱えたか, choose
    判断が出たか, 詠唱直前の手札枚数）を返す。"""
    e = _build(rules, p0, p1)
    cast = False
    chose = False
    hand0 = None
    play = f"play:{TARGET}"
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not cast and d["kind"] == "main" and d.get("player") == 0 \
                and play in keys:
            cast = True
            hand0 = _count(e, "hand", 0)
            e.answer([keys.index(play)])
            continue
        if cast and d["kind"] == "choose_cards":
            chose = True
            if choose_defn is not None:
                idx = [i for i, o in enumerate(d["options"])
                       if choose_defn in o["key"]]
                assert idx, f"{choose_defn} が選択肢に無い: {keys}"
                e.answer(idx[:1])
                continue
            e.answer([0])
            continue
        if cast and d["kind"] in ("main", "charge", "attack"):
            break          # 解決が終わり次の通常判断に戻った
        e.answer(_boring(d))
    return e, cast, chose, hand0


def test_registered_cast_multicolor_gets_plus_4000_and_draws(rules):
    """登録カード: 多色クリーチャー（光・水＝文明2つ）の
    T030（パワー2000）を選ぶと、このターンのパワーは
    2000＋2×2000＝6000 になる。カードも1枚引く
    （候補1体では自動選択）。"""
    e, cast, chose, hand0 = _cast(
        rules,
        {"hand": [TARGET], "mana": ["T001"] * 3, "bz": ["T030"]},
        choose_defn="T030")
    assert cast and not chose   # 候補1体では自動選択
    assert _power(e, "T030") == 6000
    assert _count(e, "hand", 0) == hand0   # −1（詠唱）＋1（ドロー）
    assert TARGET in _defns(e, "graveyard", 0)


def test_registered_cast_monocolor_gets_plus_2000(rules):
    """登録カード: 単色クリーチャー（火＝文明1つ）の
    T1157（パワー2000）を選ぶと +2000 の 4000 になる。"""
    e, cast, chose, _ = _cast(
        rules,
        {"hand": [TARGET], "mana": ["T001"] * 3, "bz": ["T1157"]},
        choose_defn="T1157")
    assert cast and not chose   # 候補1体では自動選択
    assert _power(e, "T1157") == 4000


def test_registered_choice_determines_amount(rules):
    """登録カード: 候補が2体（多色 T030 と単色 T1157）
    いて単色を選ぶと単色だけが +2000 され、多色は元の
    パワーのまま。"""
    e, cast, chose, _ = _cast(
        rules,
        {"hand": [TARGET], "mana": ["T001"] * 3,
         "bz": ["T030", "T1157"]},
        choose_defn="T1157")
    assert cast and chose
    assert _power(e, "T1157") == 4000
    assert _power(e, "T030") == 2000


def test_registered_no_creature_still_draws(rules):
    """登録カード: 自分のクリーチャーが無ければ修整は
    生成されず、ドローだけが解決する。"""
    e, cast, _, hand0 = _cast(
        rules,
        {"hand": [TARGET], "mana": ["T001"] * 3})
    assert cast
    assert _count(e, "hand", 0) == hand0
    assert TARGET in _defns(e, "graveyard", 0)
