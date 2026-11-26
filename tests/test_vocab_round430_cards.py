"""再変換ラウンド430（第395弾 civ_count_of_destroyed）の記録テスト。

- 新規登録1件: dmex15-b099 生魂転霊
  （登録形は提出形と完全一致: partial の骨格
  〔呪文 / 自然 / コスト2、mana 1、keywords
  [s_trigger]、abilities・spell ともに無し〕に
  第395弾の確立形 spell 4 op〔choose {owner: you,
  as: victim} → set_var {name: n_civs, value:
  {civ_count: {ref: victim}}} → destroy
  {ref: victim} → mana_put {from_top:
  {var: n_civs}}〕を足し、unsupported を外した
  もの。spell はこの4 op ちょうど、keywords は
  [s_trigger] のまま。**補完なし**: text は
  partial の公式テキスト全文と一致）。
- 正本判定は通常型: identity 実測で canon_id は
  対象・全 alias とも dmex15-b099、aliases_for は
  [dm24-110, promoy24-026] で partial の
  source.aliases と一致。alias はいずれも rejects
  に独自行が無く、登録時の source.aliases は
  validate が自動付与した。alias 畳み込み0件・
  stale クリーンアップ0件・差し戻し0件。
- reopen（civ_count_of_destroyed）の出力は
  対象1件ちょうど（対象行は reason == "vocab"）。
- converted 10,374→10,375 / rejects 1,938→1,937、
  canonical 重なり0・漏れ0。
  civ_count_of_destroyed は完全解消。
- 確立形は第79弾の式 civ_count を破壊前に
  第322弾の set_var で数えて束縛する「移動前に
  数えて束縛する」パターン（新規フィールドでは
  ない。回帰に test_data_audit を含めて確認済み）。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）は本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第395弾本体と同形（対象を proto T1162 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第395弾の proto を流用: T030（光・水の多色＝
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
from tests.test_vocab_pilot395 import EXPANDED, FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dmex15-b099"
GAP = "civ_count_of_destroyed"
NAME = "生魂転霊"
ALIASES = ["dm24-110", "promoy24-026"]


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


def test_round430_disposition():
    rej = _reject_rows()
    assert len(rej) == 1937
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10375
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = {rid for rid, r in rej.items() if GAP in (r.get("gaps") or [])}
    assert fam == set()                  # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["spell"] and c["civs"] == ["nature"]
    assert c["cost"] == 2 and c["mana"] == 1
    assert c["keywords"] == ["s_trigger"]
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完なし）
    # 登録形は提出形と完全一致: 確立形 spell 4 op ちょうど
    assert c["spell"] == FORM
    assert len(c["spell"]) == 4
    assert not c.get("abilities")
    assert not c.get("aliases")
    assert (c.get("source") or {}).get("aliases") == ALIASES
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d.spell == EXPANDED           # マクロ展開後の形
    for a in ALIASES:                    # alias に独自行・登録は無い
        assert a not in rej
        assert _conv_cache.find(CONVERTED, a) is None
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第395弾本体と同形、対象は登録カード） ----------

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


def _boring(d):
    keys = [o["key"] for o in d["options"]]
    for want in ("pass", "end_turn", "end_attack", "end_phase"):
        if want in keys:
            return [keys.index(want)]
    return [0]


def _cast(rules, p0, p1=None, choose_defn=None):
    """p0 が登録カードを唱え、choose が出れば choose_defn を
    選んで解決まで進める。（engine, 唱えたか, choose
    判断が出たか, 詠唱直前の (マナ数, 山札数)) を返す。"""
    e = _build(rules, p0, p1)
    cast = False
    chose = False
    base = None
    play = f"play:{TARGET}"
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not cast and d["kind"] == "main" and d.get("player") == 0 \
                and play in keys:
            cast = True
            base = (_count(e, "mana", 0), _count(e, "deck", 0))
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
    return e, cast, chose, base


def test_registered_cast_multicolor_puts_two(rules):
    """登録カード: 多色クリーチャー（光・水＝文明2つ）の
    T030 を破壊すると、山札の上から2枚がマナゾーンに
    置かれる（破壊前に set_var で数えた civ_count が
    2 になることの検証。候補1体では自動選択）。"""
    e, cast, chose, (mana0, deck0) = _cast(
        rules,
        {"hand": [TARGET], "mana": ["T001"] * 2, "bz": ["T030"]},
        choose_defn="T030")
    assert cast and not chose   # 候補1体では自動選択
    assert "T030" not in _defns(e, "bz", 0)
    assert "T030" in _defns(e, "graveyard", 0)
    assert _count(e, "mana", 0) == mana0 + 2
    assert _count(e, "deck", 0) == deck0 - 2
    assert TARGET in _defns(e, "graveyard", 0)


def test_registered_cast_monocolor_puts_one(rules):
    """登録カード: 単色クリーチャー（火＝文明1つ）の
    T1157 を破壊すると、置かれるのは1枚だけ。"""
    e, cast, chose, (mana0, deck0) = _cast(
        rules,
        {"hand": [TARGET], "mana": ["T001"] * 2, "bz": ["T1157"]},
        choose_defn="T1157")
    assert cast and not chose   # 候補1体では自動選択
    assert "T1157" in _defns(e, "graveyard", 0)
    assert _count(e, "mana", 0) == mana0 + 1
    assert _count(e, "deck", 0) == deck0 - 1


def test_registered_choice_determines_count(rules):
    """登録カード: 候補が2体（単色 T1157 と多色 T030）
    いて多色を選ぶと2枚置かれ、選ばなかった単色は残る。"""
    e, cast, chose, (mana0, deck0) = _cast(
        rules,
        {"hand": [TARGET], "mana": ["T001"] * 2,
         "bz": ["T1157", "T030"]},
        choose_defn="T030")
    assert cast and chose
    assert "T030" in _defns(e, "graveyard", 0)
    assert "T1157" in _defns(e, "bz", 0)
    assert _count(e, "mana", 0) == mana0 + 2
    assert _count(e, "deck", 0) == deck0 - 2


def test_registered_no_creature_resolves_empty(rules):
    """登録カード: 自分のクリーチャーが無ければ呪文は
    空で解決する（civ_count は空の ref で 0＝0枚）。"""
    e, cast, _, (mana0, deck0) = _cast(
        rules,
        {"hand": [TARGET], "mana": ["T001"] * 2})
    assert cast
    assert _count(e, "mana", 0) == mana0
    assert _count(e, "deck", 0) == deck0
    assert TARGET in _defns(e, "graveyard", 0)
