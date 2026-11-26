"""再変換ラウンド395（第360弾 breaks_plus_one）の記録テスト。

- 新規登録1件: dm14-s08 ファイナル・ドラグアーマー
  （登録形は提出形と完全一致: partial の既存 static
  {affects: crossed, mod: {power_when +5000/attacking,
  add_races [アーマード・ドラゴン]}} の mod に
  breaks_add: 1 を足したもの、abilities 1件ちょうど、
  partial に keywords は無く登録エントリにも無い）。
- alias 畳み込み0件（identity の canon_id 実測で自 ID、
  aliases_for は空、登録エントリに aliases なし。対象 id は
  real.yaml / real_akashic.yaml / real_vocab.yaml /
  real_zone.yaml / converted.yaml のいずれにも無く、
  proto.yaml のヒットは T1083 の notes 内参照のみ）。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [breaks_plus_one] のため reopen で
  外してから submit（reopen の出力は対象1件ちょうど）。
- converted 10,339→10,340 / rejects 1,973→1,972、
  canonical 重なり0・alias 重なり0・漏れ0。
  breaks_plus_one はファミリーがこの1件だけだったため
  完全に解消。
- dm02-046 の stale 行（destroy_self_after_attacking_player）
  は判断待ちのため本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
scenario.build の薄い包みで、tests.conftest は
import しない（第319弾以降の作法）。ホストは proto
T1084（パワー2000）、対照ブロッカーは T1085
（パワー6000）。
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

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
TARGET = "dm14-s08"
GAP = "breaks_plus_one"

FORM = [{"kind": "static", "affects": "crossed",
         "mod": {"power_when": {"amount": 5000, "when": "attacking"},
                 "breaks_add": 1,
                 "add_races": ["アーマード・ドラゴン"]}}]


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


def test_round395_disposition():
    rej = _reject_rows()
    assert len(rej) == 1972
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10340
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias 畳み込み0件
    assert not (c.get("source") or {}).get("unsupported")
    assert c["abilities"] == FORM        # 登録形 == 提出形（FORM）
    assert len(c["abilities"]) == 1
    assert not c.get("keywords")         # partial に keywords は無い
    d = parse_card(c, TABLES)
    assert FORM[0] in d.abilities
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（scenario.build 直包み、第360弾本体と同型） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn):
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn)


def _defns(e, zone, p):
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _cross(e, gear=TARGET, host="T1084", p=0):
    e.s.cards[_cid(e, p, gear)].crossed = \
        e.s.ref(_cid(e, p, host))


def _drive_attack(e, attacker, block_with=None):
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
            hit = [i for i, k in enumerate(keys)
                   if block_with and k.startswith(f"bz:{block_with}:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
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


def test_registered_crossed_host_chars(rules):
    """登録したドラグアーマーをクロスすると breaks_add 1
    （ブレイク数2）・種族追加が及び、非攻撃時のパワーは
    素のまま。"""
    e = _build(rules, {"bz": ["T1084", TARGET]}, {})
    host = _cid(e, 0, "T1084")
    ch = e.chars(host)
    assert ch["breaks"] == 1 and ch["breaks_add"] == 0
    assert "アーマード・ドラゴン" not in ch["races"]
    _cross(e)
    ch = e.chars(host)
    assert ch["breaks_add"] == 1 and ch["breaks"] == 2
    assert ch["break_opts"] == [2]
    assert "アーマード・ドラゴン" in ch["races"]
    assert ch["power"] == 2000


def test_registered_crossed_host_breaks_two_shields(rules):
    """登録ギアをクロスしたホストの攻撃はシールドを
    2枚ブレイクする（5→3）。クロスしなければ1枚（5→4）。"""
    e = _build(rules, {"bz": ["T1084", TARGET]}, {})
    _cross(e)
    st = _drive_attack(e, "T1084")
    assert st["attacked"]
    assert len(_defns(e, "shield", 1)) == 3

    e = _build(rules, {"bz": ["T1084", TARGET]}, {})
    st = _drive_attack(e, "T1084")
    assert st["attacked"]
    assert len(_defns(e, "shield", 1)) == 4


def test_registered_crossed_host_wins_battle(rules):
    """登録ギアをクロスしたホストは攻撃時パワー7000に
    なり、パワー6000のブロッカーにバトルで勝つ。
    クロスしなければ2000で負けて破壊される。"""
    e = _build(rules, {"bz": ["T1084", TARGET]}, {"bz": ["T1085"]})
    _cross(e)
    st = _drive_attack(e, "T1084", block_with="T1085")
    assert st["attacked"]
    assert "T1085" in _defns(e, "graveyard", 1)
    assert "T1084" in _defns(e, "bz", 0)

    e = _build(rules, {"bz": ["T1084", TARGET]}, {"bz": ["T1085"]})
    st = _drive_attack(e, "T1084", block_with="T1085")
    assert st["attacked"]
    assert "T1084" in _defns(e, "graveyard", 0)
    assert "T1085" in _defns(e, "bz", 1)


def test_registered_real_generate_and_cross_flow(rules):
    """実フロー: 登録ギアをジェネレート→コストをもう一度
    払ってクロスすると、ホストに breaks_add が及ぶ。"""
    e = _build(rules,
               {"hand": [TARGET], "bz": ["T1084"],
                "mana": ["T005"] * 6},
               {})
    crossed = False
    for _ in range(300):
        gear = next((c for c in e.zlist("bz", 0)
                     if e.s.cards[c].defn == TARGET), None)
        if gear is not None and e.s.cards[gear].crossed:
            crossed = True
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "main" and d["player"] == 0:
            cross = [k for k in keys if k.startswith(f"cross:{TARGET}:")]
            if cross:
                e.answer([keys.index(cross[0])])
            elif f"play:{TARGET}" in keys:
                e.answer([keys.index(f"play:{TARGET}")])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert crossed
    ch = e.chars(_cid(e, 0, "T1084"))
    assert ch["breaks_add"] == 1 and ch["breaks"] == 2
