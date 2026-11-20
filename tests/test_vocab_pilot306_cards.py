"""語彙パイロット第306弾の対象カード検証（ラウンド341で登録済み）。

same_name_sweep は dm17-004 エクスプロード・カタストロフィー
1件のみで、ラウンド341で登録された。第2ギャップ
evolution_cross_gear は第304弾で実装済み。機構は新規語彙なし
のドリフト: バトル勝利の誘発は battle_win 記録 {subject:
勝者, opponent: 敗者} ＋ subject: crossed（cross_gear_effect
イディオム）、敗者と同じ名前のフィルタは {name: {name_of:
event.opponent}}、手札を見るは choose {count: all} の look
束縛、一掃は複数ゾーン select ＋ count: all の move
（to: deck, position: bottom）。実挙動は第306弾本体
（プロト T939）とラウンド341 cards（登録カード自身）で
固定済み。ここでは登録形が第306弾の確立形と完全一致し、
対象行が rejects から解消したことを固定する。

正本判定（ラウンド341で identity を実データ照合）:
- canon_id は dm17-004 自身＝独立正本。aliases_for は空で
  alias は無い（登録カードの source.aliases にも記録なし）。

evolution_cross_gear のギャップ名自体は、他ギャップ併記の
dmc66-034（dynamic_name_reference_filter）/ dm17-s04
（reveal_and_cast_free）の2行に残る（本弾の対象外で、
残ることを確認する）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活
するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
import _conv_cache  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
REJECTS = ROOT / "data" / "cards" / "raw" / "rejects.jsonl"
TABLES = load_tables()

STATIC = {"kind": "static", "affects": "crossed",
          "mod": {"allow": [{"action": "attack_creature",
                             "other": {"tapped": False}}]}}

SWEEP_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "battle_win", "subject": "crossed"},
    "effect": [
        {"op": "choose",
         "select": {"zone": "hand", "owner": "opp", "count": "all"},
         "as": "seen"},
        {"op": "move",
         "select": {"zone": ["hand", "mana", "graveyard", "bz"],
                    "owner": "opp",
                    "filter": {"name": {"name_of": "event.opponent"}},
                    "count": "all"},
         "to": "deck", "position": "bottom", "reason": "put"},
    ],
}


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_target_registered_in_pilot306_form():
    rows = _rows()
    assert "dm17-004" not in rows            # rejects から外れた
    c = _conv_cache.find(CONVERTED, "dm17-004")
    assert c is not None                     # converted に登録済み
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") is None
    assert c["abilities"] == [STATIC, SWEEP_TRIGGER]   # 連結混入なし
    d = parse_card(c, TABLES)
    assert d.types == ["cross_gear", "evolution"]
    assert d.evolve_from == {"civs": ["darkness", "fire"]}
    assert d.civs == ["darkness", "fire"]
    assert d.cost == 3
    # same_name_sweep は解消
    holders = {rid for rid, r in rows.items()
               if "same_name_sweep" in (r.get("gaps") or [])}
    assert holders == set(), holders


def test_other_evolution_cross_gear_rows_remain():
    rows = _rows()
    assert rows["dmc66-034"].get("gaps") == \
        ["evolution_cross_gear", "dynamic_name_reference_filter"]
    assert rows["dm17-s04"].get("gaps") == \
        ["evolution_cross_gear", "reveal_and_cast_free"]
