"""再変換ラウンド429（第394弾 only_creature_condition）の記録テスト。

- 新規登録1件: dm26rp3-056 龍装者 クシュトル
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 光 / コスト3 / パワー2500 /
  種族 ドラゴンギルド・メタリカ、mana 1、
  keywords [blocker]、abilities 無し〕に
  第394弾の確立形 static〔if {cmp: [{count:
  {zone: bz, owner: you, filter: {types:
  [creature]}}}, "==", 1]} の間 mod:
  {no_leave: true}〕1件を足し、unsupported を
  外したもの。abilities はこの1件ちょうど、
  keywords は [blocker] のまま。**補完なし**:
  text は partial の公式テキスト全文と一致）。
- 正本判定は通常型: identity 実測で canon_id は
  対象 id 自身が正本、alias は無い。alias
  畳み込み0件・stale クリーンアップ0件・
  差し戻し0件。
- reopen（only_creature_condition）の出力は
  対象1件ちょうど（対象行は reason == "vocab"）。
- converted 10,373→10,374 / rejects 1,939→1,938、
  canonical 重なり0・漏れ0。
  only_creature_condition は完全解消。
- 確立形は mod no_leave（第49弾）を static の
  if で門番する登録先例 dmx22b-040 の門番
  パターンの自己版（新規フィールドではない。
  回帰に test_data_audit を含めて確認済み）。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）は本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第394弾本体と同形（対象を proto T1161 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第394弾の proto を流用: T1157（味方役）/
T056（相手のクリーチャーを破壊する呪文）/
マナ役 T008（闇）。
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
from tests.test_vocab_pilot394 import FORM, FULL_TEXT, STATIC  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm26rp3-056"
GAP = "only_creature_condition"
NAME = "龍装者 クシュトル"


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


def test_round429_disposition():
    rej = _reject_rows()
    assert len(rej) == 1938
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10374
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = {rid for rid, r in rej.items() if GAP in (r.get("gaps") or [])}
    assert fam == set()                  # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 3 and c["power"] == 2500 and c["mana"] == 1
    assert c["races"] == ["ドラゴンギルド", "メタリカ"]
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


# ---------- 実挙動ドライバ（第394弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _mine(e):
    return next(c for c in e.zlist("bz", 0)
                if e.cdef(c).id == TARGET)


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "yes_no":
        e.answer([keys.index("yes")] if "yes" in keys
                 else list(range(d["min"])))
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _cast_by_p1(rules, p0, p1, spell):
    """p1 が spell を唱え、choose では登録カードを選び、
    解決が終わる（p1 のアタックフェイズに入る）まで進める。"""
    e = _build(rules, p0, p1)
    state = {}
    for _ in range(4000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 1 \
                and not state.get("cast"):
            assert f"play:{spell}" in keys, keys
            state["cast"] = True
            e.answer([keys.index(f"play:{spell}")])
            continue
        if state.get("cast") and d["kind"] == "choose_cards" \
                and not state.get("chose"):
            idx = [i for i, o in enumerate(d["options"])
                   if TARGET in o["key"]]
            assert idx, f"{TARGET} が選択肢に無い: {keys}"
            state["chose"] = True
            e.answer([idx[0]])
            continue
        if state.get("cast") and d["kind"] in ("attack", "charge"):
            break   # メインフェイズは終わり解決済み
        _answer_default(e, d)
    assert state.get("cast"), state
    return e


def test_registered_protected_when_alone(rules):
    """登録カード: 自分のクリーチャーがこのクリーチャー
    だけなら no_leave が集約される。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": []})
    cid = _mine(e)
    assert e.chars(cid)["no_leave"]


def test_registered_not_protected_with_ally(rules):
    """登録カード: 味方がもう1体いれば count は2で
    門番が外れる。"""
    e = _build(rules, {"bz": [TARGET, "T1157"]}, {"bz": []})
    cid = _mine(e)
    assert not e.chars(cid)["no_leave"]


def test_registered_destroy_blocked_when_alone(rules):
    """登録カード: 実フローで単独の間は相手の破壊呪文
    でも離れない。"""
    e = _cast_by_p1(rules, {"bz": [TARGET]},
                    {"hand": ["T056"], "mana": ["T008"] * 3},
                    "T056")
    cid = _mine(e)
    assert e.s.cards[cid].zone == "bz"
    assert not any(e.cdef(c).id == TARGET
                   for c in e.zlist("graveyard", 0))


def test_registered_destroy_works_with_ally(rules):
    """登録カード: 実フローで味方がいれば門番が外れ、
    破壊は通る。"""
    e = _cast_by_p1(rules, {"bz": [TARGET, "T1157"]},
                    {"hand": ["T056"], "mana": ["T008"] * 3},
                    "T056")
    assert any(e.cdef(c).id == TARGET
               for c in e.zlist("graveyard", 0))
    assert any(e.s.cards[c].defn == "T1157"
               for c in e.zlist("bz", 0))
