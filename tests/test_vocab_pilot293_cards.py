"""語彙パイロット第293弾のカード適用テスト（登録形）: ラウンド328/329の結果。

対象は進化元のゾーン拡張クラスタ26行。結果は:
- 登録20件（自 id）: 形A 進化V＋ゾーン dm22ex2-003 / dm26ex2-027 /
  dm38-027 / dm28-s05 / dmc55-021 / dm34-002 / dm28-s01（ラウンド330で
  登録。差し戻し理由だった super_shield_plus は第295弾で解消）、形B 進化GV＋ゾーン
  dm25ex1-044 / dm26ex2-mc005 / dm23bd4-017 / dmc63-009 / dm25ex1-023 /
  dm25ex1-016、形C 進化GV・Ω dm23ex3-tr07、形D デッキ進化GV
  dm22ex2-4a / dm25ex1-010、形E 超無限 dm24bd5-012（ラウンド329で登録）/
  dm23ex3-tr02 / dmr20-s04 / dm26ex1-011
- alias 畳み込み3件: dmc66-008 → dmpcd03-b02（canon が変換済みのため
  alias 追加のみ）、dmartkiwami03-005 → dm25ex1-010、dm26ex4-sec009 →
  dm26ex4-012（alias は既存で reject 行の除去のみ）
- 差し戻し3件（解けた進化面は partial に銀行済み）: dm28-s09 → static_if_own_current_power、
  dm26ex2-mc009 → exlife_shield_left_any、dm26ex2-pr003 →
  per_evolution_base_cost_reduction

登録形の進化面は本ファイルの FORMS が正本（パイロット段階の提出形と
同じ）。実挙動の検証は tests/test_vocab_round328_cards.py /
test_vocab_round329_cards.py で行う。

プロトテスト（test_vocab_pilot293.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが
汚染される）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

FORMS = {
    # 形A: evolve_from リスト形＋evolve_zone
    "dm22ex2-003": {"evolve_zone": "graveyard",
                    "evolve_from": [{"civs": ["darkness"]}, {"civs": ["darkness"]}]},
    "dm26ex2-027": {"evolve_zone": "graveyard",
                    "evolve_from": [{"civs": ["darkness", "fire"]},
                                    {"civs": ["darkness", "fire"]}]},
    "dm38-027": {"evolve_zone": "graveyard",
                 "evolve_from": [{"races": ["ファイアー・バード"]},
                                 {"races": ["ファイアー・バード"]}]},
    "dm28-s05": {"evolve_zone": "mana",
                 "evolve_from": [{"civs": ["darkness"]}, {"civs": ["darkness"]}]},
    "dm28-s01": {"evolve_zone": "mana",
                 "evolve_from": [{"civs": ["light"]}, {"civs": ["light"]}]},
    "dmc55-021": {"evolve_zone": "mana",
                  "evolve_from": [{"civs": ["fire"]}, {"civs": ["fire"]}]},
    "dm34-002": {"evolve_zone": "hand",
                 "evolve_from": [{"civs": ["water"]}, {"civs": ["water"]}]},
    # 形B: evolve_count: 3＋evolve_zone
    "dm25ex1-044": {"evolve_zone": "graveyard", "evolve_count": 3,
                    "evolve_from": {"types": ["creature"]}},
    "dm26ex2-mc005": {"evolve_zone": "graveyard", "evolve_count": 3,
                      "evolve_from": {"civs": ["darkness", "fire"]}},
    "dm23bd4-017": {"evolve_zone": "mana", "evolve_count": 3,
                    "evolve_from": {"race_has": "ドラゴン"}},
    "dmc63-009": {"evolve_zone": "mana", "evolve_count": 3,
                  "evolve_from": {"civs": ["darkness"]}},
    "dm25ex1-023": {"evolve_zone": "hand", "evolve_count": 3,
                    "evolve_from": {"types": ["creature"]}},
    "dm25ex1-016": {"evolve_zone": "shield", "evolve_count": 3,
                    "evolve_from": {}},
    # 形C: フィルタ別 zone（面フィールドの単純照合対象は無い）
    "dm23ex3-tr07": {"evolve_from": [{"zone": "graveyard", "types": ["creature"]},
                                     {"zone": "mana", "types": ["creature"]},
                                     {"zone": "bz", "types": ["creature"]}]},
    # 形D: deck_evolution stack_all
    "dm22ex2-4a": {"deck_evolution": {"count": 3, "blind": True,
                                      "stack_all": True},
                   "evolve_from": {"types": ["creature"]}},
    "dm25ex1-010": {"deck_evolution": {"count": 3, "blind": True,
                                        "stack_all": True},
                    "evolve_from": {"types": ["creature"]}},
    # 形E: 超無限
    "dm24bd5-012": {"evolve_any": True,
                    "evolve_zones": ["graveyard", "mana", "bz"],
                    "evolve_from": {"races": ["スノーフェアリー"]}},
    "dm23ex3-tr02": {"evolve_any": True,
                     "evolve_zones": ["graveyard", "mana", "bz"],
                     "evolve_from": {"races": ["ガーディアン"]}},
    "dmr20-s04": {"evolve_any": True, "evolve_zone": "graveyard",
                  "evolve_from": {"civs": ["darkness"]}},
    "dm26ex1-011": {"evolve_any": True,
                    "evolve_from": {"types": ["creature"]}},
}

REGISTERED = sorted(FORMS)

ALIASES = {
    "dmc66-008": "dmpcd03-b02",
    "dmartkiwami03-005": "dm25ex1-010",
    "dm26ex4-sec009": "dm26ex4-012",
}

STILL_REJECTED = {
    "dm28-s09": ["static_if_own_current_power"],
    "dm26ex2-mc009": ["exlife_shield_left_any"],
    "dm26ex2-pr003": ["per_evolution_base_cost_reduction"],
}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_registered_forms():
    rej = _reject_rows()
    for cid in REGISTERED:
        c = _conv_cache.find(CONVERTED, cid)
        assert c is not None, cid                    # 登録された
        assert cid not in rej, cid                   # rejects に残らない
        assert "unsupported" not in (c.get("source") or {}), cid
        form = FORMS[cid]
        d = parse_card(c, TABLES)
        f = d.face(None)
        if "evolve_zone" in form:
            assert f.evolve_zone == form["evolve_zone"], cid
        if "evolve_count" in form:
            assert f.evolve_count == form["evolve_count"], cid
        if "evolve_max" in form:
            assert f.evolve_max == form["evolve_max"] and f.evolve_any, cid
        if "deck_evolution" in form:
            assert f.deck_evolution == form["deck_evolution"], cid
        if "evolve_zones" in form:
            assert list(f.evolve_zones) == form["evolve_zones"], cid
        if "evolve_total_cost_ge" in form:
            assert f.evolve_total_cost_ge == form["evolve_total_cost_ge"], cid
        if form.get("evolve_any"):
            assert f.evolve_any, cid


def test_aliases_folded():
    rej = _reject_rows()
    for aid, canon in ALIASES.items():
        assert aid not in rej, aid                        # reject 行は無い
        assert _conv_cache.find(CONVERTED, aid) is None, aid   # 自 id では登録されない
        c = _conv_cache.find(CONVERTED, canon)
        assert c is not None, canon
        assert aid in ((c.get("source") or {}).get("aliases") or []), aid


def test_still_rejected_with_refined_gaps():
    rej = _reject_rows()
    for cid, gaps in STILL_REJECTED.items():
        if cid not in rej:      # 後続の再変換で登録済みになった札は対象外
            assert _conv_cache.find(CONVERTED, cid) is not None, cid
            continue
        assert rej[cid].get("gaps") == gaps, (cid, rej[cid].get("gaps"))
        assert _conv_cache.find(CONVERTED, cid) is None, cid
