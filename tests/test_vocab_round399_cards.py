"""再変換ラウンド399（第364弾 blocking_power）の記録テスト。

- 新規登録1件: dm34-025 ワダツミ・フィッシュ
  （登録形は提出形と完全一致: partial の骨格
  〔keywords [blocker, cannot_attack]、abilities
  無し〕に第364弾の確立形〔static {affects: self,
  mod: {power_when: {amount: 2000, when: blocking,
  opponent_filter: {not_types: [evolution]}}}}〕
  1能力を足したもの、補完なし）。
- alias 畳み込み0件（alias は無い）。正本判定:
  対象 id dm34-025 を real.yaml / real_akashic.yaml /
  real_vocab.yaml / real_zone.yaml / proto.yaml /
  converted.yaml と照合し、いずれにも登録なし
  （proto.yaml のヒットは T1095 の notes 内参照のみ）。
  identity の canon_id 実測で対象 id が正本そのもの、
  aliases_for(名前, 対象id) = []。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [blocking_power] のため
  reopen で外してから submit（reopen の出力は
  対象1件ちょうど）。
- converted 10,343→10,344 / rejects 1,969→1,968、
  canonical 重なり0・alias 重なり0・漏れ0。
  blocking_power はファミリーがこの1件だけだった
  ため完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）は判断待ちのため本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
scenario.build の薄い包みで、tests.conftest は
import しない（第319弾以降の作法）。攻撃側は
proto T1096（進化ではないパワー4000）/
T1097（進化クリーチャーのパワー4000）。
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
TARGET = "dm34-025"
GAP = "blocking_power"

STATIC = {"kind": "static", "affects": "self",
          "mod": {"power_when": {"amount": 2000, "when": "blocking",
                                 "opponent_filter":
                                     {"not_types": ["evolution"]}}}}
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


def test_round399_disposition():
    rej = _reject_rows()
    assert len(rej) == 1968
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10344
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias 畳み込み0件
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: 1能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert c["name"] == "ワダツミ・フィッシュ"
    assert c["types"] == ["creature"] and c["civs"] == ["water"]
    assert c["cost"] == 3 and c["power"] == 3000
    assert c["races"] == ["フィッシュ", "オリジン"]
    assert c["keywords"] == ["blocker", "cannot_attack"]
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

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
    ブロックしない（第364弾本体の作法）。"""
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


def test_registered_blocks_non_evolution_attacker_wins(rules):
    """登録カードが進化ではないパワー4000の攻撃を
    ブロックすると、+2000 を受けた 5000 でバトルに
    勝ち、攻撃側が破壊される。登録カードは残る。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1096"]})
    st = _drive_attack(e, "T1096", block_with=TARGET)
    assert st["attacked"]
    assert "T1096" in _defns(e, "graveyard", 1)
    assert TARGET in _defns(e, "bz", 0)


def test_registered_blocks_evolution_attacker_no_bonus_loses(rules):
    """登録カードが進化クリーチャーのパワー4000の
    攻撃をブロックしても +2000 は付かず、3000 のまま
    バトルに負けて破壊される。攻撃側は残る。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1097"]})
    st = _drive_attack(e, "T1097", block_with=TARGET)
    assert st["attacked"]
    assert TARGET in _defns(e, "graveyard", 0)
    assert "T1097" in _defns(e, "bz", 1)


def test_registered_no_block_shield_breaks(rules):
    """ブロックしなければシールドが1枚ブレイクされ、
    両者ともバトルゾーンに残る。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1096"]})
    shields = len(e.zlist("shield", 0))
    st = _drive_attack(e, "T1096", block_with=None)
    assert st["attacked"]
    assert len(e.zlist("shield", 0)) == shields - 1
    assert TARGET in _defns(e, "bz", 0)
    assert "T1096" in _defns(e, "bz", 1)
