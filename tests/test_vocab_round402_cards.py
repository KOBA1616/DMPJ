"""再変換ラウンド402（第367弾
always_win_battles）の記録テスト。

- 新規登録1件: dm14-s01 太陽の精霊マルシアス
  （登録形は提出形と完全一致: partial の骨格
  〔光 / コスト5 / パワー2000 / 種族
  エンジェル・コマンド、keywords 無し、
  abilities 無し〕に第367弾の確立形〔static
  {affects: self, mod: {win_all_battles:
  true}}〕1能力を足し unsupported を外した
  もの、補完なし）。
- alias 畳み込み0件（alias は無い）。正本判定:
  対象 id dm14-s01 を real.yaml /
  real_akashic.yaml / real_vocab.yaml /
  real_zone.yaml / proto.yaml / converted.yaml
  と照合し、いずれにも登録なし（proto.yaml の
  ヒットは T1104 の notes 内参照のみ）。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [always_win_battles] のため
  reopen で外してから submit（reopen の出力は
  対象1件ちょうど）。
- converted 10,346→10,347 / rejects
  1,966→1,965、canonical 重なり0・漏れ0。
  always_win_battles はファミリーがこの1件
  だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）は判断待ちのため本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第367弾本体の薄い包みで、tests.conftest は
import しない（第319弾以降の作法）。ブロッカー役は
proto T1105（パワー4000）、両持ち役は T1106
（win_all_battles 持ちブロッカー）。
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
TARGET = "dm14-s01"
GAP = "always_win_battles"

STATIC = {"kind": "static", "affects": "self",
          "mod": {"win_all_battles": True}}
FORM = [STATIC]


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


def test_round402_disposition():
    rej = _reject_rows()
    assert len(rej) == 1965
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10347
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias は無い
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: 1能力ちょうど、keywords は無いまま
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("keywords")
    assert c["name"] == "太陽の精霊マルシアス"
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 5 and c["power"] == 2000
    assert c["races"] == ["エンジェル・コマンド"]
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第367弾本体と同形） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive_attack(e, attacker, block_with=None):
    """p1 の attacker でプレイヤーを攻撃する。block_with が
    あればそのブロッカー（p0）でブロックし、無ければ
    ブロックしない。攻撃したターンの2つ先のターンまで
    進めて状態を返す（第367弾の作法）。"""
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


def test_registered_weaker_attacker_wins_vs_stronger_blocker(rules):
    """登録カード: パワー2000でもパワー4000のブロッカーに
    ブロックされるとすべてのバトルに勝つためブロッカーが
    破壊され、登録カードは残る。シールドはブレイクされない。"""
    e = _build(rules, {"bz": ["T1105"]}, {"bz": [TARGET]})
    before = len(e.zlist("shield", 0))
    st = _drive_attack(e, TARGET, block_with="T1105")
    assert st["attacked"]
    assert TARGET in _defns(e, "bz", 1)
    assert "T1105" not in _defns(e, "bz", 0)
    assert "T1105" in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 0)) == before


def test_registered_both_win_all_battles_neither_destroyed(rules):
    """登録カード: 相手ブロッカーも win_all_battles を
    持つ場合は相打ちなしで、どちらも破壊されずバトル
    ゾーンに残る（公式テキストの括弧書き）。"""
    e = _build(rules, {"bz": ["T1106"]}, {"bz": [TARGET]})
    before = len(e.zlist("shield", 0))
    st = _drive_attack(e, TARGET, block_with="T1106")
    assert st["attacked"]
    assert TARGET in _defns(e, "bz", 1)
    assert "T1106" in _defns(e, "bz", 0)
    assert TARGET not in _defns(e, "graveyard", 1)
    assert "T1106" not in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 0)) == before


def test_registered_no_block_breaks_shield(rules):
    """登録カード: ブロックしなければ通常どおりシールドが
    1枚ブレイクされる（対照）。"""
    e = _build(rules, {"bz": ["T1105"]}, {"bz": [TARGET]})
    before = len(e.zlist("shield", 0))
    st = _drive_attack(e, TARGET)
    assert st["attacked"]
    assert len(e.zlist("shield", 0)) == before - 1
    assert TARGET in _defns(e, "bz", 1)
    assert "T1105" in _defns(e, "bz", 0)
