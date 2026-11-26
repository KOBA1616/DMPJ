"""再変換ラウンド416（第381弾 opponent_cannot_summon_or_cast_next_turn）の記録テスト。

- 新規登録1件: dm21-014 デビル・リンク・タブー
  （登録形は提出形と完全一致: partial の骨格〔呪文 /
  闇 / コスト10 / mana 1、abilities・keywords ともに
  無し〕に第381弾の確立形〔abilities = シンパシーの
  static 1件（dm21-020 / dm21-011 の登録先例と同形、
  cost {amount: -1, count: {zone: bz, owner: you,
  filter: {races: [グランド・デビル, ディープ・
  マリーン]}}}, cost_min: 1）、spell = modify
  {deny: [summon]} ＋ modify {deny: [cast]} の2 op
  （ファイナル・ストップ dm26sd1-e007 と同型、
  duration: until_next_own_turn_start）〕を足し、
  unsupported を外したもの。abilities は static
  1件ちょうど、spell は2 op ちょうど、keywords は
  無いまま。補完あり: partial の text はロック条項
  のみのため、text には行の公式テキスト全文
  （シンパシー条項を含む）を入れた）。
- alias 畳み込み0件（alias は無い）。正本判定:
  対象 id を real.yaml / real_akashic.yaml /
  real_vocab.yaml / real_zone.yaml / proto.yaml /
  converted.yaml と照合し、いずれにも登録なし
  （proto.yaml のヒットは T1135 の notes 内参照
  のみ）。identity 実測で canon_id(dm21-014) =
  dm21-014、aliases_for は []。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [opponent_cannot_summon_or_
  cast_next_turn] のため reopen で外してから
  submit（reopen の出力は対象1件ちょうど）。
- converted 10,360→10,361 / rejects 1,952→1,951、
  canonical 重なり0・漏れ0。opponent_cannot_
  summon_or_cast_next_turn はファミリーがこの
  1件だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）と dm14-073 の既存データ負債は
  判断待ちのため本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第381弾本体と同形（対象を proto T1135 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第381弾の proto を流用: T1136（グランド・デビル
役）/ T1137（ディープ・マリーン役）/ T001（自然・
コスト2クリーチャー）/ T003（水・コスト2呪文）/
T008（闇・コスト2。マナ役）。
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
from tests.test_vocab_pilot381 import (  # noqa: E402
    DENY_CAST, DENY_SUMMON, FULL_TEXT, SYMPATHY)

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm21-014"
GAP = "opponent_cannot_summon_or_cast_next_turn"
NAME = "デビル・リンク・タブー"


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


def test_round416_disposition():
    rej = _reject_rows()
    assert len(rej) == 1951
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10361
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["spell"] and c["civs"] == ["darkness"]
    assert c["cost"] == 10 and c["mana"] == 1
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    # 登録形は提出形と完全一致: 確立形ちょうど
    assert c["abilities"] == [SYMPATHY]
    assert len(c["abilities"]) == 1     # static 1件ちょうど
    assert c["spell"] == [DENY_SUMMON, DENY_CAST]
    assert len(c["spell"]) == 2         # spell は2 op ちょうど
    assert not c.get("keywords")         # keywords は無いまま
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d is not None
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第381弾本体と同形、対象は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _pay_cost(rules, bz):
    e = _build(rules, {"bz": bz, "hand": [TARGET]}, {})
    cid = next(c for c in e.zlist("hand", 0)
               if e.s.cards[c].defn == TARGET)
    return e.chars_ro(cid)["pay_cost"]


def test_registered_sympathy_pay_cost(rules):
    assert _pay_cost(rules, []) == 10                    # 素は10
    assert _pay_cost(rules, ["T1136"]) == 9              # グランド・デビル1体
    assert _pay_cost(rules, ["T1137"]) == 9              # ディープ・マリーン1体
    assert _pay_cost(rules, ["T1136", "T1137", "T1136"]) == 7   # 混在3体
    assert _pay_cost(rules, ["T001"]) == 10              # 対象外種族は数えない
    assert _pay_cost(rules, ["T1136"] * 12) == 1         # 下限1（cost_min）


def _keys(d):
    return [o["key"] for o in d["options"]]


def _lock_game(rules, cast):
    """p0 が登録カードを唱える（または唱えない）ゲームを進め、
    (p1 の1回目の main の選択肢, p1 の2回目の main の選択肢,
     唱えた直後の p0 の main の選択肢) を返す。"""
    p0 = {"hand": [TARGET, "T003"],
          "mana": ["T008"] + ["T003"] * 11}
    p1 = {"hand": ["T001", "T003"],
          "mana": ["T001", "T003", "T001", "T003"]}
    e = _build(rules, p0, p1)
    cast_done = False
    p0_after_cast = None
    p1_mains = []
    for _ in range(1200):
        d = e.advance()
        assert d is not None, "game ended"
        k = _keys(d)
        if cast and not cast_done and d["kind"] == "main" \
                and d.get("player") == 0 and f"play:{TARGET}" in k:
            cast_done = True
            e.answer([k.index(f"play:{TARGET}")])
            continue
        if cast_done and p0_after_cast is None \
                and d["kind"] == "main" and d.get("player") == 0:
            p0_after_cast = k
        if d["kind"] == "main" and d.get("player") == 1:
            p1_mains.append(k)
            if len(p1_mains) == 2:
                return p1_mains[0], p1_mains[1], p0_after_cast
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in k:
            e.answer([k.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("p1 second main never came")


def test_registered_lock_next_opponent_turn(rules):
    first, second, _ = _lock_game(rules, cast=True)
    # 次の相手ターン中: 召喚も詠唱もできない
    assert "play:T001" not in first, first
    assert "play:T003" not in first, first
    # 自分の次のターン開始で失効し、その後の相手ターンでは戻る
    assert "play:T001" in second, second
    assert "play:T003" in second, second


def test_registered_lock_control_without_cast(rules):
    first, _, _ = _lock_game(rules, cast=False)
    # 対照: 唱えなければ相手は通常どおり召喚・詠唱できる
    assert "play:T001" in first, first
    assert "play:T003" in first, first


def test_registered_lock_does_not_hit_caster(rules):
    # ロックは相手の手札だけに掛かる: 唱えた本人の同じ
    # ターンの main では自分の呪文が通常どおり唱えられる
    _, _, after = _lock_game(rules, cast=True)
    assert after is not None
    assert "play:T003" in after, after
