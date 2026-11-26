"""再変換ラウンド427（第392弾 civilization_breaker）の記録テスト。

- 新規登録1件: dm27-010 彩強の巨人
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 自然 / コスト9 / パワー11000 /
  種族 ジャイアント、mana 1、keywords・abilities
  無し〕に第392弾の確立形 static〔affects: self,
  mod: {breaks: {civ_count: {zone: mana,
  owner: you}, base: 0}}〕1件を足し、unsupported を
  外したもの。abilities はこの1件ちょうど、
  keywords は無いまま。**補完あり**: partial の
  text は「文明ブレイカー」だけのため、text には
  行の公式テキスト全文を入れた）。
- 正本判定は通常型: identity 実測で canon_id は
  対象 id 自身が正本、alias は無い。alias
  畳み込み0件・stale クリーンアップ0件・
  差し戻し0件。
- reopen（civilization_breaker）の出力は対象1件
  ちょうど（対象行は reason == "vocab" で
  gaps = [civilization_breaker]）。
  civilization_breaker は完全解消。
- converted 10,371→10,372 / rejects 1,941→1,940
  （reopen −1 のみ）、canonical 重なり0・漏れ0。
- 確立形は mod breaks の式形式 {civ_count:
  セレクタ}（第79弾。登録先例 dmc34-025 は
  「追加で」型で base 既定1の base＋式値）に、
  第145弾で実挙動検証済みの base: 0（バラエティ・
  ブレイカーと同機構）を組み合わせたもの。
  breaks の {civ_count ＋ base: 0} の組み合わせは
  本カードが初の登録（回帰に test_data_audit を
  含めて確認済み）。
- dm02-046 の stale 行・dm14-073 の既存データ負債・
  schema.py の turn_count への from 同期漏れ
  （第387弾で観察）は本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第392弾本体と同形（発生源を proto T1159 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第392弾の proto T001（自然）/ T005（火）/
T008（闇）/ T030（光・水の多色）を流用。
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
from tests.test_vocab_pilot392 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm27-010"
GAP = "civilization_breaker"
NAME = "彩強の巨人"


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


def test_round427_disposition():
    rej = _reject_rows()
    assert len(rej) == 1940
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10372
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = {rid for rid, r in rej.items() if GAP in (r.get("gaps") or [])}
    assert fam == set()                  # ファミリー完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 9 and c["power"] == 11000 and c["mana"] == 1
    assert c["races"] == ["ジャイアント"]
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    # 登録形は提出形と完全一致: 確立形 static 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 1
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第392弾本体と同形、発生源は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn, n=0):
    return [c for c in e.zlist("bz", p)
            if e.s.cards[c].defn == defn][n]


def _breaks(e, p, defn, n=0):
    ch = e.chars(_cid(e, p, defn, n))
    return ch["breaks"], ch["break_opts"]


def test_registered_breaks_civ_count_chars(rules):
    """登録カード: 文明数えの固定 — マナが無ければ
    文明0種でブレイク選択肢は [0]（base: 0 の判別:
    既定 base 1 なら [1] になる）。3種で3、
    多色1枚はそれぞれ数えて2種。"""
    e = _build(rules, {"bz": [TARGET]}, {})
    assert _breaks(e, 0, TARGET) == (1, [0])
    e = _build(rules, {"bz": [TARGET],
                       "mana": ["T001", "T005", "T008"]}, {})
    assert _breaks(e, 0, TARGET) == (3, [3])
    e = _build(rules, {"bz": [TARGET], "mana": ["T030"]}, {})
    assert _breaks(e, 0, TARGET) == (2, [2])


def _drive_attack(e, attacker):
    """p0 の attacker でプレイヤーを攻撃し、攻撃した
    ターンの2つ先のターンまで進める（第392弾の作法）。"""
    state = {"attacked": False, "attack_turn": None}
    for _ in range(1500):
        if state["attacked"] and e.s.turn >= state["attack_turn"] + 2:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack":
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and not state["attacked"]:
                state["attacked"] = True
                state["attack_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return state


def test_registered_attack_breaks_civ_count_shields(rules):
    """登録カード: マナ3種（自然・火・闇）で実際に
    シールドを3枚ブレイクする（5→2）。"""
    e = _build(rules, {"bz": [TARGET],
                       "mana": ["T001", "T005", "T008"]}, {})
    st = _drive_attack(e, TARGET)
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 2


def test_registered_attack_breaks_zero_without_mana_civs(rules):
    """登録カード: マナゾーンが空ならブレイクは0枚 —
    攻撃してもシールドは減らない（5→5）。
    break_opts [0] が実際に解決へ届くことの固定。"""
    e = _build(rules, {"bz": [TARGET]}, {})
    st = _drive_attack(e, TARGET)
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 5
