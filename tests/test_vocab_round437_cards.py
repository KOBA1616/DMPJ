"""再変換ラウンド437（第402弾 indestructible_duration）の記録テスト。

- 新規登録1件: promoy13-019 天英雄 ヴァルハラ・デューク
  （登録形は提出形と完全一致: partial の骨格
  〔クリーチャー / 光 / コスト7 / パワー7000 /
  種族 エンジェル・コマンド・ドラゴン、mana 1、
  keywords [double_breaker]〕に第402弾の確立形
  trigger {when: {event: move, to: bz, subject:
  self}, if: {cmp: [{count: {zone: mana, owner:
  you, filter: {civs: [light]}}}, ">=", 7]},
  effect: [modify {select: {zone: bz, owner: you,
  filter: {types: [creature]}, count: all}, mod:
  {indestructible: true}, duration:
  until_next_own_turn_start}]} 1件を足し、
  unsupported を外したもの。abilities はこの
  1件ちょうど〔parse 後の double_breaker 派生
  static を除く〕、keywords は [double_breaker]
  のまま。**補完なし**〔partial の text は公式
  全文と一致。登録後の全文一致も照合済み〕）。
- alias 畳み込み0件（alias は無い。正本判定は
  通常型: 対象 id を real / real_akashic /
  real_vocab / real_zone / proto / converted と
  照合し登録なし〔proto のヒットは T1169 の
  notes 内参照のみ〕、identity 実測で canon_id は
  対象自身、aliases_for = []）。stale
  クリーンアップ0件・差し戻し0件（reopen
  〔indestructible_duration〕の出力は対象1件
  ちょうど）。
- converted 10,381→10,382 / rejects 1,931→1,930、
  canonical 重なり0・漏れ0。indestructible_duration
  は完全解消。
- 確立形は登録済み dm23sd2-013（出た時誘発→
  modify count: all の indestructible、duration:
  end_of_turn）と同型で、duration:
  until_next_own_turn_start との併用は
  dmrp15-030 の先例あり。新規フィールドでは
  ないが、回帰に test_data_audit と第127・366弾
  本体を含めて確認済み。
- dm02-046 の stale 行・dm14-073 の既存データ
  負債・schema.py の turn_count への from
  同期漏れ（第387弾で観察）は本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第402弾本体と同形（対象を proto T1169 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第402弾の proto を流用: T1117（光マナ役）/
T001（相手役・非光マナ役）/ T004（ブロッカー
味方役）/ T1118（パワー7000の攻撃役）/ T056
（相手の破壊呪文役）/ T620（自分の単体破壊
呪文役）。
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
from tests.test_vocab_pilot402 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "promoy13-019"
GAP = "indestructible_duration"
NAME = "天英雄 ヴァルハラ・デューク"


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


def test_round437_disposition():
    rej = _reject_rows()
    assert len(rej) == 1930
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10382
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    fam = sorted(rid for rid, r in rej.items()
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # indestructible_duration は完全解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"]
    assert c["civs"] == ["light"]
    assert c["cost"] == 7 and c["power"] == 7000 and c["mana"] == 1
    assert c["races"] == ["エンジェル・コマンド・ドラゴン"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    assert c["keywords"] == ["double_breaker"]
    # 登録形は提出形と完全一致: 確立形1能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("aliases")        # alias は無い
    assert not src.get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 2         # double_breaker 派生 static ＋ 確立形
    assert d.abilities[1] == FORM[0]
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第402弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _indestructible(e, p, defn):
    cid = next(c for c in e.bz_tops(p) if e.cdef(c).id == defn)
    return e.chars(cid).get("indestructible") is True


def _drive(e, plays0=(), plays1=(), attacker=None, attacker_player=1,
           blocker=None, pick=None, stop=None, limit=1200):
    """汎用ドライバ（第402弾本体と同型）。"""
    state = {"attacked": False, "played": []}
    plays = {0: list(plays0), 1: list(plays1)}
    for _ in range(limit):
        if stop is not None and stop():
            return state
        d = e.advance()
        if d is None:
            return state
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        pl = d.get("player")
        if kind == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d.get("min", 0))))
        elif kind == "main" and pl in plays and plays[pl]:
            hit = next((k for k in plays[pl] if k in keys), None)
            if hit is not None:
                plays[pl].remove(hit)
                state["played"].append(hit)
                e.answer([keys.index(hit)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind in ("attack", "declare_attack"):
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and pl == attacker_player \
                    and not state["attacked"]:
                state["attacked"] = True
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind in ("block", "declare_block"):
            hit = [i for i, k in enumerate(keys)
                   if blocker and k.startswith(f"bz:{blocker}:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif pick and any(pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("limit reached")


def _play_source(e):
    """p0 が登録カードを出し、出た時誘発が解決するまで
    進める（相手ターンに入った時点で解決済み）。"""
    _drive(e, plays0=[f"play:{TARGET}"], stop=lambda: e.s.turn >= 2)
    assert TARGET in _defns(e, "bz", 0)


def test_registered_destroy_effect_blocked_during_window(rules):
    """実挙動: 光マナ7枚で出た時、自分のクリーチャー
    （味方 T001・発生源自身）は特性として indestructible
    を持ち、相手の破壊呪文（T056）でも破壊されない。"""
    e = _build(rules,
               {"bz": ["T001"], "hand": [TARGET],
                "mana": ["T1117"] * 7},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    _play_source(e)
    assert _indestructible(e, 0, "T001")
    assert _indestructible(e, 0, TARGET)
    _drive(e, plays1=["play:T056"], pick="bz:T001",
           stop=lambda: "T056" in _defns(e, "graveyard", 1))
    assert "T001" in _defns(e, "bz", 0)          # 破壊されない
    assert TARGET in _defns(e, "bz", 0)
    assert "T001" not in _defns(e, "graveyard", 0)


def test_registered_battle_loss_blocked_during_window(rules):
    """実挙動: 味方ブロッカー（T004、3000）がパワー
    7000（T1118）の攻撃をブロックしてバトルに負けて
    も、期間中は破壊されない。"""
    e = _build(rules,
               {"bz": ["T004"], "hand": [TARGET],
                "mana": ["T1117"] * 7},
               {"bz": ["T1118"]})
    _play_source(e)
    st = _drive(e, attacker="T1118", attacker_player=1,
                blocker="T004", stop=lambda: e.s.turn >= 3)
    assert st["attacked"]
    assert "T004" in _defns(e, "bz", 0)          # バトルで負けても残る
    assert "T1118" in _defns(e, "bz", 1)


def test_registered_condition_unmet_no_protection(rules):
    """判別: 光マナが6枚（合計7枚でも条件未達）では
    誘発は解決しても効果は付かず、味方（T004）は
    相手の破壊呪文で破壊される。"""
    e = _build(rules,
               {"bz": ["T004"], "hand": [TARGET],
                "mana": ["T1117"] * 6 + ["T001"]},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    _play_source(e)
    assert not _indestructible(e, 0, "T004")
    _drive(e, plays1=["play:T056"], pick="bz:T004",
           stop=lambda: "T056" in _defns(e, "graveyard", 1))
    assert "T004" in _defns(e, "graveyard", 0)   # 破壊される
    assert TARGET in _defns(e, "bz", 0)


def test_registered_window_expires_at_next_own_turn_start(rules):
    """実挙動（期間判別）: 保護は次の自分のターンの
    はじめまで。相手ターン中は有効で、自分のターンが
    再び始まった後は失効し、その後の相手の破壊呪文で
    味方（T001）は破壊される。"""
    e = _build(rules,
               {"bz": ["T001"], "hand": [TARGET],
                "mana": ["T1117"] * 7},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    _play_source(e)
    assert _indestructible(e, 0, "T001")         # 相手ターン中有効
    _drive(e, stop=lambda: e.s.turn >= 4)        # 自分のターンを挟む
    assert not _indestructible(e, 0, "T001")     # 失効
    _drive(e, plays1=["play:T056"], pick="bz:T001",
           stop=lambda: "T056" in _defns(e, "graveyard", 1))
    assert "T001" in _defns(e, "graveyard", 0)   # 破壊される


def test_registered_late_entry_not_in_resolution_set(rules):
    """判別（一括 modify の集合固定）: 出た時誘発の
    解決後にバトルゾーンに出たクリーチャー（同じ
    メインで続けて出した T004）は対象に含まれず、
    相手の破壊呪文で破壊される。発生源自身は守られる
    （dm23sd2-013 の非 dynamic な一括 modify の作法）。"""
    e = _build(rules,
               {"hand": [TARGET, "T004"], "mana": ["T1117"] * 10},
               {"hand": ["T056"], "mana": ["T056"] * 3})
    _drive(e, plays0=[f"play:{TARGET}", "play:T004"],
           stop=lambda: e.s.turn >= 2)
    assert "T004" in _defns(e, "bz", 0)
    assert _indestructible(e, 0, TARGET)
    assert not _indestructible(e, 0, "T004")     # 解決後の登場は対象外
    _drive(e, plays1=["play:T056"], pick="bz:T004",
           stop=lambda: "T056" in _defns(e, "graveyard", 1))
    assert "T004" in _defns(e, "graveyard", 0)
    assert TARGET in _defns(e, "bz", 0)


def test_registered_opponent_creatures_not_protected(rules):
    """判別（owner: you の範囲）: 期間中でも相手の
    クリーチャーは守られない。自分の単体破壊呪文
    （T620）で相手の T001 は破壊される。"""
    e = _build(rules,
               {"bz": ["T004"], "hand": [TARGET, "T620"],
                "mana": ["T1117"] * 7 + ["T620"] * 3},
               {"bz": ["T001"]})
    _drive(e, plays0=[f"play:{TARGET}", "play:T620"], pick="bz:T001",
           stop=lambda: "T620" in _defns(e, "graveyard", 0))
    assert "T001" in _defns(e, "graveyard", 1)   # 相手は破壊される
    assert "T004" in _defns(e, "bz", 0)
    assert TARGET in _defns(e, "bz", 0)
