"""第177弾 choukon_raid の実カード形の検証（ラウンド213 登録形）。

ラウンド213で choukon_raid 14件のうち9件を converted へ登録し、5件を
差し戻した。choukon_raid ギャップは残り0件（CLEARED）。
- dm25ex3-rp2005 → dynamic_power_relative_attack_protection（「このクリーチャー
  よりパワーが小さいクリーチャーに攻撃されない」の動的パワー相対 deny は
  表現不能。パワー静的（下1枚につき+8000）と超魂レイドは partial に銀行）
- dm25ex3-rp2s01 → destroy_under_cards_modal_shieldize（破壊時「下にあった
  カードを墓地から NEO/進化の下に置くか表向きの1つのシールドとしてシールド化」
  の modal＋下カード回収は未確立。CIP シールド化と超魂レイドは partial に銀行）
- dm25rp2-050 → summon_from_mana_alt_cost_no_element（超魂レイドは銀行）
- dm25ex3-rp2003 → under_creatures_total_cost_put（超魂レイドは銀行）
- dm25ex3-rp2dm1 → alt_cost_mana_race_condition（超魂レイドは銀行）
- dm26ex4-sec025: partial の count: {upto: 2} は未定義形のため
  count: 2, up_to: true に修正して登録（race_has "アビス" は有効な部分一致）。
"""
import json
from pathlib import Path

import yaml

from dmsim.cards.defs import load_tables, parse_card

ROOT = Path(__file__).parent.parent
TABLES = load_tables()

REGISTERED = ["dm26ex4-sec025", "dm25ex3-046", "dm25rp2-045", "dm25rp2-036",
              "dm25bd1-005", "dm25ex3-006", "dm25ex3-rp2s04",
              "dm25rp2-029", "dm25rp2-032"]

BOUNCED = {"dm25ex3-rp2005": ["dynamic_power_relative_attack_protection"],
           "dm25ex3-rp2s01": ["destroy_under_cards_modal_shieldize"],
           "dm25rp2-050": ["summon_from_mana_alt_cost_no_element"],
           "dm25ex3-rp2003": ["under_creatures_total_cost_put"],
           "dm25ex3-rp2dm1": ["alt_cost_mana_race_condition"]}


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


def _ops(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _ops(v)
    elif isinstance(node, list):
        for v in node:
            yield from _ops(v)


def _has_raid(card):
    return any(a.get("kind") == "trigger"
               and any(o.get("op") == "reveal_until" for o in a.get("effect", []))
               for a in card.get("abilities") or [])


def test_round213_registered_parse():
    cards = _converted()
    missing = [cid for cid in REGISTERED if cid not in cards]
    assert not missing, f"converted に無い: {missing}"
    for cid in REGISTERED:
        parsed = parse_card(cards[cid], TABLES)
        assert parsed is not None
        assert _has_raid(cards[cid]), cid
        assert cards[cid].get("evolve_from"), cid
    # alias 引き継ぎ
    assert cards["dm25ex3-046"]["source"]["aliases"] == ["dm25rp2-042"]
    assert cards["dm25rp2-036"]["source"]["aliases"] == ["promoy24-031"]
    assert cards["dm25bd1-005"]["source"]["aliases"] == ["dm25bd1-sp3"]
    assert cards["dm25ex3-006"]["source"]["aliases"] == ["dm25rp2-014"]
    assert cards["dm25ex3-rp2s04"]["source"]["aliases"] == [
        "dm25ex3-rp2sec05", "dm25rp2-s04", "dm25rp2-sec05"]
    assert cards["dm25rp2-029"]["source"]["aliases"] == ["promoy24-043"]
    # dm26ex4-sec025: 墓地からの出しは count: 2, up_to: true（{upto: 2} は除去）
    c25 = cards["dm26ex4-sec025"]
    assert "upto" not in yaml.safe_dump(c25)
    atk = [a for a in c25["abilities"]
           if a.get("when", {}).get("event") == "attack"]
    assert len(atk) == 1
    mv = [o for o in _ops(atk[0].get("effect", [])) if o.get("op") == "move"]
    assert len(mv) == 1
    assert mv[0]["select"]["count"] == 2 and mv[0]["select"]["up_to"] is True
    assert mv[0]["select"]["filter"]["race_has"] == "アビス"
    # dm25ex3-rp2s04: CIP 破壊＋攻撃時めくり出しが残っている
    c04 = cards["dm25ex3-rp2s04"]["abilities"]
    assert any(o.get("op") == "destroy" for a in c04 for o in _ops(a.get("effect", [])))
    assert any(o.get("op") == "choose" for a in c04 for o in _ops(a.get("effect", [])))


def test_round213_bounced():
    rows = _rejects()
    for cid, gaps in BOUNCED.items():
        assert cid in rows, f"{cid} が rejects に戻っていない"
        assert rows[cid]["gaps"] == gaps, f"{cid}: {rows[cid]['gaps']}"
        assert _has_raid(rows[cid].get("partial") or {}), cid
    # 解けた節は partial に銀行されている
    p05 = rows["dm25ex3-rp2005"].get("partial") or {}
    stat05 = [a for a in p05.get("abilities") or [] if a.get("kind") == "static"]
    assert len(stat05) == 1
    assert stat05[0]["mod"]["power"] == {"amount": 8000,
                                         "count": {"under_of": "self"}}
    p01 = rows["dm25ex3-rp2s01"].get("partial") or {}
    assert any(o.get("op") == "move" and o.get("to") == "shield"
               for a in p01.get("abilities") or []
               for o in _ops(a.get("effect", [])))
    # choukon_raid ギャップは残り0件
    left = [cid for cid, r in rows.items() if "choukon_raid" in (r.get("gaps") or [])]
    assert left == [], f"choukon_raid 残り: {left}"
