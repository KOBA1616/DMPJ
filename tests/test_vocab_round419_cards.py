"""再変換ラウンド419（第384弾 creatures_enter_tapped）の記録テスト。

- 新規登録1件: dm06-001 銀界の守護者ル・ギラ・レシール
  （登録形は提出形と完全一致: partial の組立て済み
  部分〔クリーチャー / 光 / コスト5 / パワー4000 /
  種族 ガーディアン、mana 1、keywords [blocker,
  cannot_attack_player]〕に第384弾の確立形 static
  1件〔{kind: static, affects: {zone: bz, owner:
  any, filter: {types: [evolution]}}, mod: {grant:
  [enters_tapped]}}〕（第339弾の grant
  [enters_tapped] 確立形の一般化、登録先例
  dmex19-m20 型）を足し、unsupported を外した
  もの。abilities は static 1件ちょうど、keywords
  は [blocker, cannot_attack_player] のまま。
  補完なし: partial の text は行の公式テキスト
  全文と一致）。
- alias 畳み込み0件（alias は無い）。正本判定:
  対象 id を real.yaml / real_akashic.yaml /
  real_vocab.yaml / real_zone.yaml / proto.yaml /
  converted.yaml と照合し、いずれにも登録なし
  （proto.yaml のヒットは T1144 の notes 内参照
  のみ）。identity 実測で canon_id(dm06-001) =
  dm06-001、aliases_for は []。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [creatures_enter_tapped]
  のため reopen で外してから submit（reopen の
  出力は対象1件ちょうど）。
- converted 10,363→10,364 / rejects 1,949→1,948、
  canonical 重なり0・漏れ0。creatures_enter_
  tapped はファミリーがこの1件だけだったため
  完全に解消。
- 第384弾でエンジン修正（_stack の位相 or 合成）が
  入っているため、本ラウンドの回帰には第384弾
  本体に加えて test_rules・test_mechanics・
  第339弾本体を含めた。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）と dm14-073 の既存データ負債は
  判断待ちのため本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第384弾本体と同形（発生源を proto T1144 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第384弾の proto を流用: T1145（進化ガーディアン
役）/ T1146（非進化ガーディアン役）/ T1147
（自身が enters_tapped を持つ進化役）。
バトルゾーンは共有ゾーンなので所有は
zlist(zone, p) で見る。
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
from tests.test_vocab_pilot384 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm06-001"
GAP = "creatures_enter_tapped"
NAME = "銀界の守護者ル・ギラ・レシール"


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


def test_round419_disposition():
    rej = _reject_rows()
    assert len(rej) == 1948
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10364
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 5 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ガーディアン"]
    assert c["keywords"] == ["blocker", "cannot_attack_player"]
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完なし）
    # 登録形は提出形と完全一致: 確立形 static 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert FORM[0] in d.abilities
    assert len(d.abilities) == 3
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第384弾本体と同形、発生源は登録カード） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _zone_card(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p)
                if e.s.cards[c].defn == defn)


def _play(e, player, play_key, pick=None, limit=600):
    defn = play_key.split(":", 1)[1]
    for _ in range(limit):
        if any(e.s.cards[c].defn == defn
               for c in e.zlist("bz", player)):
            return
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == player \
                and play_key in keys:
            e.answer([keys.index(play_key)])
            continue
        if pick and any(pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("play never happened")


def test_registered_opponent_evolution_enters_tapped(rules):
    """実挙動: 登録カードが場にある間、相手の進化
    クリーチャー（T1145）はタップして出る。"""
    e = _build(rules, {"bz": [TARGET]},
               {"bz": ["T1146"], "hand": ["T1145"],
                "mana": ["T1146", "T001", "T001"]})
    _play(e, 1, "play:T1145", pick="T1146")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1145")].tapped is True


def test_registered_own_evolution_enters_tapped(rules):
    """実挙動: 自分の進化クリーチャー（T1145）も
    タップして出る（owner: any の自分側）。"""
    e = _build(rules, {"bz": [TARGET, "T1146"], "hand": ["T1145"],
                       "mana": ["T1146", "T001", "T001"]},
               {})
    _play(e, 0, "play:T1145", pick="T1146")
    assert e.s.cards[_zone_card(e, "bz", 0, "T1145")].tapped is True


def test_registered_non_evolution_enters_untapped(rules):
    """判別: 進化ではないクリーチャー（T1146）は
    フィルタで外れ、タップせずに出る。"""
    e = _build(rules, {"bz": [TARGET]},
               {"hand": ["T1146"],
                "mana": ["T1146", "T001", "T001"]})
    _play(e, 1, "play:T1146")
    assert e.s.cards[_zone_card(e, "bz", 1, "T1146")].tapped is False


def test_registered_own_keyword_evolution_enters_tapped(rules):
    """実挙動（第384弾のエンジン修正の判別）: 発生源が
    無くても、自身が enters_tapped キーワードを持つ
    進化クリーチャー（T1147）はアンタップ状態の
    進化元でもタップして出る（_stack の or 合成）。"""
    e = _build(rules, {"bz": ["T1146"], "hand": ["T1147"],
                       "mana": ["T1146", "T001", "T001"]},
               {})
    _play(e, 0, "play:T1147", pick="T1146")
    assert e.s.cards[_zone_card(e, "bz", 0, "T1147")].tapped is True
