"""再変換ラウンド401（第366弾
conditional_battle_indestructible）の記録テスト。

- 新規登録1件: dm24rp2-054 ケルビ・チゼン
  （登録形は提出形と完全一致: partial の骨格
  〔光 / コスト2 / パワー1500 / 種族
  メカ・デル・ディネロ、keywords [blocker]、
  abilities 無し〕に第366弾の確立形〔static
  {affects: self, if: {exists: {zone: bz,
  owner: you, filter: {race_has: 超化獣}}},
  mod: {battle_indestructible: true}}〕1能力を
  足し unsupported を外したもの、補完なし）。
- alias 畳み込み0件（alias は無い）。正本判定:
  対象 id dm24rp2-054 を real.yaml /
  real_akashic.yaml / real_vocab.yaml /
  real_zone.yaml / proto.yaml / converted.yaml
  と照合し、いずれにも登録なし（proto.yaml の
  ヒットは T1101 の notes 内参照のみ）。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [conditional_battle_
  indestructible] のため reopen で外してから
  submit（reopen の出力は対象1件ちょうど）。
- converted 10,345→10,346 / rejects
  1,967→1,966、canonical 重なり0・漏れ0。
  conditional_battle_indestructible は
  ファミリーがこの1件だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）は判断待ちのため本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第366弾本体の薄い包みで、tests.conftest は
import しない（第319弾以降の作法）。味方役は
proto T1102（超化獣）、攻撃側は T1103
（パワー4000アタッカー）。
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
TARGET = "dm24rp2-054"
GAP = "conditional_battle_indestructible"

STATIC = {"kind": "static", "affects": "self",
          "if": {"exists": {"zone": "bz", "owner": "you",
                            "filter": {"race_has": "超化獣"}}},
          "mod": {"battle_indestructible": True}}
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


def test_round401_disposition():
    rej = _reject_rows()
    assert len(rej) == 1966
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10346
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET not in rej             # 対象行は解消
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias は無い
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: 1能力ちょうど、keywords は [blocker] のまま
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert c["keywords"] == ["blocker"]
    assert c["name"] == "ケルビ・チゼン"
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 2 and c["power"] == 1500
    assert c["races"] == ["メカ・デル・ディネロ"]
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第366弾本体と同形） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _cid(e, tid, p):
    return next(c for c in e.bz_tops(p) if e.cdef(c).id == tid)


def _drive_attack(e, attacker, block_with=None):
    """p1 の attacker でプレイヤーを攻撃する。block_with が
    あればそのブロッカー（p0）でブロックし、無ければ
    ブロックしない。攻撃したターンの2つ先のターンまで
    進めて状態を返す（第366弾の作法）。"""
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


def test_registered_block_loses_battle_but_not_destroyed_with_hyperbeast(rules):
    """登録カード: 自分の超化獣がいれば、パワー4000の攻撃を
    ブロックしてバトルに負けても破壊されずバトルゾーンに
    残る（攻撃側も勝者として残る）。"""
    e = _build(rules, {"bz": [TARGET, "T1102"]}, {"bz": ["T1103"]})
    st = _drive_attack(e, "T1103", block_with=TARGET)
    assert st["attacked"]
    assert TARGET in _defns(e, "bz", 0)
    assert TARGET not in _defns(e, "graveyard", 0)
    assert "T1103" in _defns(e, "bz", 1)


def test_registered_block_without_hyperbeast_destroyed(rules):
    """登録カード: 自分の超化獣がいなければ、パワー4000の
    攻撃をブロックするとバトルに負けて破壊され墓地に
    置かれる。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1103"]})
    st = _drive_attack(e, "T1103", block_with=TARGET)
    assert st["attacked"]
    assert TARGET not in _defns(e, "bz", 0)
    assert TARGET in _defns(e, "graveyard", 0)
    assert "T1103" in _defns(e, "bz", 1)


def test_registered_no_block_breaks_shield(rules):
    """登録カード: ブロックしなければ通常どおりシールドが
    1枚ブレイクされ、両者ともバトルゾーンに残る（対照）。"""
    e = _build(rules, {"bz": [TARGET, "T1102"]}, {"bz": ["T1103"]})
    before = len(e.zlist("shield", 0))
    st = _drive_attack(e, "T1103")
    assert st["attacked"]
    assert len(e.zlist("shield", 0)) == before - 1
    assert TARGET in _defns(e, "bz", 0)
    assert "T1103" in _defns(e, "bz", 1)
