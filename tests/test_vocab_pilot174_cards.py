"""第174弾 dream_creature の実カード形の検証（ラウンド210 登録形）。

ラウンド210で dream_creature 単独ギャップ13件のうち8件を converted へ登録し、
5件を洗練したギャップ名で差し戻した。
- 登録: dm24ex2-dm01/dm24ex2-dm03/dm25ex2-dm1/dm25ex2-dm2/dm25ex3-rp1dm1/
  dm26rp1-dm001/dm26rp3-dm001/dm26rp3-dm001sec
- 差し戻し: dm24ex2-dm02/dm25ex2-dm4/dmartkiwami01-001（hyperdimensional_zone）、
  dm25ex3-rp4dm1（ddd_conditional_grant）、dm26rp2-dm001（final_revolution_game_used）
"""
import json
from pathlib import Path

import yaml

from dmsim.defs import load_tables, parse_card

ROOT = Path(__file__).parent.parent
TABLES = load_tables()

REGISTERED = ["dm24ex2-dm01", "dm24ex2-dm03", "dm25ex2-dm1", "dm25ex2-dm2",
              "dm25ex3-rp1dm1", "dm26rp1-dm001", "dm26rp3-dm001", "dm26rp3-dm001sec"]
BOUNCED = {"dm24ex2-dm02": ["hyperdimensional_zone"],
           "dm25ex2-dm4": ["hyperdimensional_zone"],
           "dmartkiwami01-001": ["hyperdimensional_zone"],
           "dm25ex3-rp4dm1": ["ddd_conditional_grant"],
           "dm26rp2-dm001": ["final_revolution_game_used"]}


def _converted():
    d = yaml.safe_load((ROOT / "data" / "cards" / "converted.yaml").read_text(encoding="utf-8"))
    cards = d.get("cards") if isinstance(d, dict) else d
    return {c["id"]: c for c in cards}


def _rejects():
    rows = {}
    for line in (ROOT / "data" / "cards" / "raw" / "rejects.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r["id"]] = r
    return rows


def test_round210_registered_parse():
    cards = _converted()
    missing = [cid for cid in REGISTERED if cid not in cards]
    assert not missing, f"converted に無い: {missing}"
    for cid in REGISTERED:
        parsed = parse_card(cards[cid], TABLES)
        assert "dream_creature" in parsed.types, cid
    # G-NEO進化は types に evolution を含めず neo＋evolve_from（第174弾の注意）
    rp = parse_card(cards["dm25ex3-rp1dm1"], TABLES)
    assert rp.neo is True and "evolution" not in rp.types
    assert rp.evolve_from is not None
    # キリフダッシュ3件は attack_end＋broke の手札誘発を持つ
    for cid in ("dm25ex2-dm1", "dm26rp3-dm001", "dm26rp3-dm001sec"):
        abs_ = cards[cid].get("abilities") or []
        assert any(a.get("kind") == "trigger" and a.get("zone") == "hand"
                   and (a.get("when") or {}).get("event") == "attack_end" for a in abs_), cid
    # Zラッシュはキーワードの印
    assert "z_rush" in (cards["dm26rp1-dm001"].get("keywords") or [])


def test_round210_bounced_gaps():
    rows = _rejects()
    for cid, gaps in BOUNCED.items():
        assert cid in rows, f"rejects に無い: {cid}"
        assert rows[cid]["gaps"] == gaps, f"{cid}: gaps={rows[cid]['gaps']}"
        p = rows[cid]["partial"]
        assert "dream_creature" in p["types"], cid
        parsed = parse_card(p, TABLES)
        assert "dream_creature" in parsed.types, cid
    # 超次元3件のうち dm25ex2-dm4 はマッハファイターの節が銀行済み
    assert (rows["dm25ex2-dm4"]["partial"].get("abilities") or [])
    # G-NEO の rp4dm1 は neo＋evolve_from が銀行済み
    assert rows["dm25ex3-rp4dm1"]["partial"].get("neo") is True
    assert rows["dm25ex3-rp4dm1"]["partial"].get("evolve_from") == {"civs": ["light", "fire", "nature"]}
