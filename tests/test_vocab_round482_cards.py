"""再変換ラウンド482（第448弾 s_trigger_suppression）の記録テスト。

- 新規登録1件: dm28-025 ヤミノリミット
  （提出形は partial の骨格〔名称・文明・コスト4・
  パワー4000・種族 ダーク・モンスター・マナ1〕に
  公式全文の text と第448弾の確立形 abilities
  1件〔static {affects: {zone: shield, owner: opp},
  if: {cmp: [count {zone: shield, owner: opp} >= 4]},
  mod: {deny: [s_trigger]}}〕を足し、unsupported を
  外したもの。登録形は提出形と完全一致
  〔source 以外の全フィールド〕、abilities は
  static 1件ちょうど、keywords は無し、text は
  公式全文）。
- 補完あり: text（公式全文。partial の text は
  条件部を落とした断片のみ）＋abilities（static 1件）。
- alias 畳み込み0件（alias は無し。正本判定: 対象 id
  を real / real_akashic / real_vocab / real_zone /
  proto / converted と照合し登録なし〔proto の
  T1239 は対象型の判別役で対象 id とは別〕、identity
  実測で canon は対象自身、aliases_for = []）。
- stale クリーンアップ0件・差し戻し1件
  （reopen〔s_trigger_suppression〕の出力は2件で、
  ファミリーの残り1件 dm27-051 は発生源紐づけの
  別機構のため、元行をそのまま差し戻し、行全体が
  HEAD とバイト単位で完全一致することを照合済み。
  s_trigger_suppression は完全解消しない）。
- converted 10,428→10,429 / rejects 1,883→1,882、
  canonical 重なり0・漏れ0。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from 同期
  漏れ（第387弾で観察）・distinct_type_count の
  count_spec 未同期（第405弾で観察）は本ラウンド
  でも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第448弾本体と同形（対象を proto T1239 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
既存 proto を流用: T006（S・トリガー呪文）/
T1107（パワー2000・1ブレイク）/ T005
（W・ブレイカー・パワー3000・2ブレイク）/
T001（盾役・対照役）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.cards.identity import aliases_for, canon_id  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests import _conv_cache  # noqa: E402
from tests.test_vocab_pilot448_cards import SUBMIT  # noqa: E402
from tests.test_vocab_pilot448 import NAME, TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm28-025"
OTHER = "dm27-051"
GAP = "s_trigger_suppression"


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


def test_round482_disposition():
    rej = _reject_rows()
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert not (ids & set(rej))          # canonical 重なり0
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == [OTHER]                # ファミリーは解消しない
    assert TARGET not in rej             # 対象行は登録で解消（漏れ0）
    assert OTHER in rej                  # 差し戻し行は残留
    assert rej[OTHER]["gaps"] == [GAP]
    assert rej[OTHER].get("reason") == "vocab"
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 1
    assert c["abilities"][0]["kind"] == "static"
    assert not c.get("keywords")         # keywords は付いていない
    assert c["text"] == TEXT             # text は公式全文
    assert not (c.get("source") or {}).get("unsupported")
    assert not (c.get("source") or {}).get("aliases")
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []
    d = parse_card(c, TABLES)
    assert d.name == NAME
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第448弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _find(e, zone, p, defn, skip=0):
    hits = [c for c in e.zlist(zone, p) if e.cdef(c).id == defn]
    return hits[skip]


def _drive(e, attacker, player, break_defns, use_strigger=False):
    """player の attacker でプレイヤーを攻撃し、break_defns の
    順でシールドを選んでブレイクする。declare_strigger の
    判断ログ [(kind, player, keys), ...] を返す（第374弾の作法）。"""
    log = []
    attacked = False
    for _ in range(1500):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack" and d.get("player") == player and not attacked:
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit:
                attacked = True
                e.answer([hit[0]])
                continue
        if kind == "choose_shields" and break_defns:
            shields = e.zlist("shield", 1 - player)
            want = list(break_defns)
            idx = []
            for i, c in enumerate(shields):
                if e.cdef(c).id in want:
                    idx.append(i)
                    want.remove(e.cdef(c).id)
            e.answer(idx)
            continue
        if kind == "declare_strigger":
            log.append((kind, d.get("player"), keys))
            e.answer(list(range(len(keys))) if use_strigger else [])
            continue
        if kind == "choose_cards":
            hit = [i for i, k in enumerate(keys) if attacker in k]
            if hit:
                e.answer(hit[:1])
                continue
        if kind == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
            continue
        e.answer(list(range(d.get("min", 0))))
        if attacked and kind == "main" and d.get("player") == player:
            break
    return log


# ---------- 登録カード dm28-025 ----------

def test_registered_chars_denied_at_4_not_at_3(rules):
    """登録カード: 特性レベルで相手シールド4枚では
    deny が付き、3枚では付かない。"""
    e = _build(rules, {"bz": [TARGET]},
               {"shield": ["T006", "T001", "T001", "T001"]})
    assert "s_trigger" in e.chars(_find(e, "shield", 1, "T006"))["deny"]
    e = _build(rules, {"bz": [TARGET]},
               {"shield": ["T006", "T001", "T001"]})
    assert "s_trigger" not in e.chars(_find(e, "shield", 1, "T006"))["deny"]


def test_registered_chars_own_shield_not_denied(rules):
    """登録カード: 抑制は相手のシールドだけ。自分の
    シールドには deny が付かない。"""
    e = _build(rules, {"bz": [TARGET], "shield": ["T006"]},
               {"shield": ["T006", "T001", "T001", "T001"]})
    assert "s_trigger" not in e.chars(_find(e, "shield", 0, "T006"))["deny"]
    assert "s_trigger" in e.chars(_find(e, "shield", 1, "T006"))["deny"]


def test_registered_break_from_4_usable(rules):
    """登録カード: 相手シールド4枚から1枚ブレイク →
    宣言時点は3枚で条件不成立となり、S・トリガーを
    宣言できる。使えば攻撃側（パワー2000）が破壊される。"""
    e = _build(rules,
               {"bz": [TARGET, "T1107"]},
               {"shield": ["T006", "T006", "T001", "T001"]})
    log = _drive(e, "T1107", 0, ["T006"], use_strigger=True)
    st = [x for x in log if x[0] == "declare_strigger"]
    assert st and st[0][1] == 1 and "strigger:T006" in st[0][2]
    assert "T1107" in _defns(e, "graveyard", 0)
    assert "T006" in _defns(e, "graveyard", 1)
    assert len(e.zlist("shield", 1)) == 3
    rest = _find(e, "shield", 1, "T006")
    assert "s_trigger" not in e.chars(rest)["deny"]


def test_registered_break_from_5_denied(rules):
    """登録カード: 相手シールド5枚から1枚ブレイク →
    宣言時点は4枚で条件成立のまま、宣言判断自体が
    出ずカードは手札へ。攻撃側は破壊されない。"""
    e = _build(rules,
               {"bz": [TARGET, "T1107"]},
               {"shield": ["T006", "T001", "T001", "T001", "T001"]})
    log = _drive(e, "T1107", 0, ["T006"], use_strigger=True)
    assert not [x for x in log if x[0] == "declare_strigger"]
    assert "T006" in _defns(e, "hand", 1)
    assert "T1107" in _defns(e, "bz", 0)
    assert len(e.zlist("shield", 1)) == 4


def test_registered_break_two_from_5_usable(rules):
    """登録カード: W・ブレイカーで5枚から2枚同時
    ブレイク → 宣言時点は3枚で条件不成立、宣言できる。
    使えば攻撃側（パワー3000）が破壊される。"""
    e = _build(rules,
               {"bz": [TARGET, "T005"]},
               {"shield": ["T006", "T001", "T001", "T001", "T001"]})
    log = _drive(e, "T005", 0, ["T006", "T001"], use_strigger=True)
    st = [x for x in log if x[0] == "declare_strigger"]
    assert st and st[0][1] == 1 and "strigger:T006" in st[0][2]
    assert "T005" in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 1)) == 3


def test_registered_break_two_from_6_denied(rules):
    """登録カード: 6枚から2枚同時ブレイク →
    宣言時点は4枚で条件成立のまま、宣言できない。
    カードは手札へ。"""
    e = _build(rules,
               {"bz": [TARGET, "T005"]},
               {"shield": ["T006", "T001", "T001", "T001", "T001", "T001"]})
    log = _drive(e, "T005", 0, ["T006", "T001"], use_strigger=True)
    assert not [x for x in log if x[0] == "declare_strigger"]
    assert "T006" in _defns(e, "hand", 1)
    assert len(e.zlist("shield", 1)) == 4
