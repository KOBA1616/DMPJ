"""再変換ラウンド400（第365弾
entered_this_turn_cannot_attack_opponents）の記録テスト。

- 新規登録1件: dm22ex1-cho37 月砂 フロッガ-1
  （登録形は提出形と完全一致: partial の既存能力
  〔ササゲール1の static {affects: self, mod:
  {sac_reduce: 1}}〕に第365弾の確立形〔static
  {affects: {zone: bz, owner: opp, filter:
  {types: [creature], not_types: [evolution],
  entered_this_turn: true}}, mod: {deny:
  [attack_player, attack_creature]}}〕1能力を
  足した2能力、補完なし）。
- alias 畳み込み0件。正本判定: 対象 id
  dm22ex1-cho37 と alias dmrp19-041 の両方を
  real.yaml / real_akashic.yaml / real_vocab.yaml /
  real_zone.yaml / proto.yaml / converted.yaml と
  照合し、いずれにも登録なし（proto.yaml の
  ヒットは T1098 の notes 内参照のみ）。alias
  dmrp19-041 は partial の source.aliases に
  あるだけで rejects に独自行は無く、登録形の
  source.aliases に記録のみ。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [entered_this_turn_cannot_
  attack_opponents] のため reopen で外してから
  submit（reopen の出力は対象1件ちょうど、
  alias 行の巻き込みなし）。
- converted 10,344→10,345 / rejects 1,968→1,967、
  canonical 重なり0・alias 重なり0・漏れ0。
  entered_this_turn_cannot_attack_opponents は
  ファミリーがこの1件だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_
  attacking_player）は判断待ちのため本ラウンドでも
  触っていない。

実挙動は登録カード自身で固定する。ドライバは
第365弾本体の薄い包みで、tests.conftest は
import しない（第319弾以降の作法）。攻撃側は
proto T1099（進化ではないスピードアタッカー）/
T1100（進化クリーチャーのスピードアタッカー）。
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
TARGET = "dm22ex1-cho37"
ALIAS = "dmrp19-041"
GAP = "entered_this_turn_cannot_attack_opponents"

SAC = {"kind": "static", "affects": "self", "mod": {"sac_reduce": 1}}
STATIC = {"kind": "static",
          "affects": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"],
                                 "not_types": ["evolution"],
                                 "entered_this_turn": True}},
          "mod": {"deny": ["attack_player", "attack_creature"]}}
FORM = [SAC, STATIC]


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


def test_round400_disposition():
    rej = _reject_rows()
    assert len(rej) == 1967
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10345
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0
    assert ALIAS not in rej              # 対象 alias に独自行なし
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")
    assert (c.get("source") or {}).get("aliases") == [ALIAS]
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: 2能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert c["name"] == "月砂 フロッガ-1"
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 2 and c["power"] == 2000
    assert c["races"] == ["デューンゲッコー", "ディスタス"]
    d = parse_card(c, TABLES)
    assert SAC in d.abilities
    assert STATIC in d.abilities
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第365弾本体と同形） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _cid(e, defn, p):
    return next(c for c in e.bz_tops(p) if e.cdef(c).id == defn)


def _drive(e, player, play=None, attack=None):
    seen = {"attack_keys": [], "deny": None, "played": False,
            "attacked": False, "target_turn": None}
    for _ in range(600):
        if seen["target_turn"] is not None \
                and e.s.turn > seen["target_turn"] + 1:
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        pl = d.get("player")
        if kind in ("charge", "main", "attack") \
                and pl == player and seen["target_turn"] is None:
            seen["target_turn"] = e.s.turn
        if kind == "main" and pl == player and play \
                and not seen["played"]:
            hit = [i for i, k in enumerate(keys)
                   if k == f"play:{play}"]
            if hit:
                seen["played"] = True
                seen["target_turn"] = e.s.turn
                e.answer([hit[0]])
                continue
        if kind == "attack" and pl == player \
                and e.s.turn == seen["target_turn"]:
            seen["attack_keys"].extend(keys)
            hit = [i for i, k in enumerate(keys)
                   if attack and k == f"attack:{attack}:player"]
            if hit and not seen["attacked"]:
                seen["attacked"] = True
                e.answer([hit[0]])
                continue
        if kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return seen


def test_registered_blocks_entered_turn_non_evolution_attack(rules):
    """登録カードがいると、相手の進化ではない
    スピードアタッカーは出たターン攻撃できない。"""
    e = _build(rules,
               {"bz": [TARGET, "T1091"]},
               {"hand": ["T1099"], "mana": ["T1099", "T1099"]})
    shields = len(e.zlist("shield", 0))
    seen = _drive(e, player=1, play="T1099")
    assert seen["played"]
    assert not [k for k in seen["attack_keys"]
                if k.startswith("attack:T1099:")]
    assert "T1099" in _defns(e, "bz", 1)
    assert not e.s.cards[_cid(e, "T1099", 1)].tapped
    assert len(e.zlist("shield", 0)) == shields


def test_registered_allows_entered_turn_evolution_attack(rules):
    """登録カードがいても、相手の進化クリーチャーは
    not_types: [evolution] で対象外となり、出た
    ターンに攻撃でき、シールドが1枚減る。"""
    e = _build(rules,
               {"bz": [TARGET, "T1091"]},
               {"bz": ["T1099"], "hand": ["T1100"],
                "mana": ["T1099", "T1099", "T1099", "T1099"]})
    before = len(e.zlist("shield", 0))
    seen = _drive(e, player=1, play="T1100", attack="T1100")
    assert seen["played"] and seen["attacked"]
    assert "T1100" in _defns(e, "bz", 1)
    assert len(e.zlist("shield", 0)) == before - 1


def test_registered_chars_deny_and_sac_reduce(rules):
    """特性レベル: 登録カード自身は sac_reduce 1 を
    持ち、出たターンの相手の非進化クリーチャーには
    deny の両方が付く。"""
    e = _build(rules,
               {"bz": [TARGET, "T1099"]},
               {"bz": ["T1099", "T1100"]})
    src = _cid(e, TARGET, 0)
    assert e.chars(src)["sac_reduce"] == 1
    opp = _cid(e, "T1099", 1)
    evo = _cid(e, "T1100", 1)
    for c in (opp, evo):
        e.s.mut_card(c).entered_turn = e.s.turn
    deny_opp = e.chars(opp)["deny"]
    assert "attack_player" in deny_opp
    assert "attack_creature" in deny_opp
    deny_evo = e.chars(evo)["deny"]
    assert "attack_player" not in deny_evo
    assert "attack_creature" not in deny_evo
