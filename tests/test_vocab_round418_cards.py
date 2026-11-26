"""再変換ラウンド418（第383弾 variable_breaks_by_count）の記録テスト。

- 新規登録1件: dm06-029 シグマ・トゥレイト
  （登録形は提出形と完全一致: partial の組立て済み
  部分〔進化クリーチャー / 火 / コスト6 / パワー
  9000 / 種族 サバイバー、mana 1、evolve_from
  {races: [サバイバー]}〕に第383弾の確立形 static
  1件〔{kind: static, affects: self, mod: {breaks:
  {count: {zone: bz, owner: you, filter: {races:
  [サバイバー]}, other: true}}}}〕（第130弾の
  breaks {count}、登録先例 dmc51-006 / dm26-009 /
  dmr01-002 と同形）を足し、unsupported を外した
  もの。abilities は static 1件ちょうど。補完なし:
  partial の text は行の公式テキストの「 / 」
  連結形で全文と一致）。
- alias 畳み込み0件（alias は無い）。正本判定:
  対象 id を real.yaml / real_akashic.yaml /
  real_vocab.yaml / real_zone.yaml / proto.yaml /
  converted.yaml と照合し、いずれにも登録なし
  （proto.yaml のヒットは T1141 の notes 内参照
  のみ）。identity 実測で canon_id(dm06-029) =
  dm06-029、aliases_for は []。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [variable_breaks_by_count]
  のため reopen で外してから submit（reopen の
  出力は対象1件ちょうど）。
- converted 10,362→10,363 / rejects 1,950→1,949、
  canonical 重なり0・漏れ0。variable_breaks_by_
  count はファミリーがこの1件だけだったため
  完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）と dm14-073 の既存データ負債は
  判断待ちのため本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
第383弾本体と同形（対象を proto T1141 から登録
カードに差し替えたもの）で、tests.conftest は
import しない（第319弾以降の作法）。判別役は
第383弾の proto を流用: T1142（他のサバイバー役）/
T1143（非サバイバー役）。バトルゾーンは共有ゾーン
なので所有は zlist(zone, p) で見る。
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
from tests.test_vocab_pilot383 import FORM, FULL_TEXT  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm06-029"
GAP = "variable_breaks_by_count"
NAME = "シグマ・トゥレイト"


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


def test_round418_disposition():
    rej = _reject_rows()
    assert len(rej) == 1949
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10363
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert c["name"] == NAME
    assert c["types"] == ["creature", "evolution"] and c["civs"] == ["fire"]
    assert c["cost"] == 6 and c["power"] == 9000 and c["mana"] == 1
    assert c["races"] == ["サバイバー"]
    assert c["evolve_from"] == {"races": ["サバイバー"]}
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完なし）
    # 登録形は提出形と完全一致: 確立形 static 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d.abilities == FORM
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第383弾本体と同形、対象は登録カード） ----------

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


def test_registered_breaks_count_chars(rules):
    # 単独では自分を数えず 1枚（other: true の判別）
    e = _build(rules, {"bz": [TARGET]}, {})
    assert _breaks(e, 0, TARGET) == (1, [1])
    # 他のサバイバー1体で 2枚、2体で 3枚
    e = _build(rules, {"bz": [TARGET, "T1142"]}, {})
    assert _breaks(e, 0, TARGET) == (2, [2])
    e = _build(rules, {"bz": [TARGET, "T1142", "T1142"]}, {})
    assert _breaks(e, 0, TARGET) == (3, [3])
    # 非サバイバーは数えない
    e = _build(rules, {"bz": [TARGET, "T1143"]}, {})
    assert _breaks(e, 0, TARGET) == (1, [1])
    # 相手のサバイバーは数えない（owner: you）
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1142"]})
    assert _breaks(e, 0, TARGET) == (1, [1])
    # 同名2体は互いを数える
    e = _build(rules, {"bz": [TARGET, TARGET]}, {})
    assert _breaks(e, 0, TARGET, 0) == (2, [2])
    assert _breaks(e, 0, TARGET, 1) == (2, [2])


def _drive_attack(e, attacker):
    """p0 の attacker でプレイヤーを攻撃し、攻撃した
    ターンの2つ先のターンまで進める（第383弾の作法）。"""
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


def test_registered_attack_breaks_counted_shields(rules):
    # 他のサバイバー2体: 実際にシールドを3枚ブレイクする（5→2）
    e = _build(rules, {"bz": [TARGET, "T1142", "T1142"]}, {})
    st = _drive_attack(e, TARGET)
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 2
    # 単独では1枚（5→4）
    e = _build(rules, {"bz": [TARGET]}, {})
    st = _drive_attack(e, TARGET)
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 4
