"""語彙パイロット第303弾の対象カード検証（ラウンド338で登録済み）。

dragonic_field 純粋3件（dm26ex3-067 / dmex12-011 = 龍世界
〜龍の降臨する地〜、dmex15-b027 = 切札の里）はラウンド338で
登録された。ここでは登録形が第303弾の確立形（FORM_A / FORM_B）と
完全一致し、ファミリーが rejects から解消したことを固定する。
実挙動は第303弾本体（プロト）とラウンド338 cards（登録カード
自身）で固定済み。

正本判定（ラウンド338で identity を実データ照合）:
- canon_id(dmex12-011) = dm26ex3-067 で、aliases_for（067 の
  名前）にも dmex12-011 が含まれる。よって dmex12-011 は独立
  登録せず、dm26ex3-067 の alias として畳み込んだ（067 の
  source.aliases は partial の5件＋dmex12-011 の6件）。
- dmex15-b027 は canon_id が自身で aliases 無し＝独立正本。

確立形:
- 形A（龍世界）: turn_start 誘発（player: you）[move 山札上1枚 →
  墓地 + as: milled、if {exists: {ref: milled, filter:
  {race_has: ドラゴン, not_types: [evolution]}}} → [may [move
  {ref: self} → 墓地, reason: destroy, as: gone]、if {exists:
  {ref: gone}} → [play_free {ref: milled}]]]。
- 形B（切札の里）: 常在型2つ。(1) affects {zone: hand,
  name_has: ボルシャック} + cost_may {amount: 2, min: 1}
  （本文にターン制限なし → once なし）。(2) affects {zone: bz,
  同フィルタ} + grant [speed_attacker]。
- types は [field, dragonic_field] 併記。text は reject 行の
  正式本文（partial の text は型名のみだった）。

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
TABLES = load_tables()
CANON = ("dm26ex3-067", "dmex15-b027")
FOLDED = "dmex12-011"
ALIASES_067 = ["dm23bd4-034", "dm24rp1-td2", "dm25sp2-010",
               "dmex12-011", "dmex16-002", "dmrp22-tr10"]

FORM_A = {"kind": "trigger",
          "when": {"event": "turn_start", "player": "you"},
          "effect": [
              {"op": "move",
               "select": {"zone": "deck", "owner": "you", "from_top": 1},
               "to": "graveyard", "reason": "put", "as": "milled"},
              {"op": "if",
               "cond": {"exists": {"ref": "milled",
                                   "filter": {"race_has": "ドラゴン",
                                              "not_types": ["evolution"]}}},
               "then": [
                   {"op": "may", "body": [
                       {"op": "move", "select": {"ref": "self"},
                        "to": "graveyard", "reason": "destroy",
                        "as": "gone"}]},
                   {"op": "if", "cond": {"exists": {"ref": "gone"}},
                    "then": [{"op": "play_free",
                              "select": {"ref": "milled"}}]}]}]}

FORM_B = [
    {"kind": "static",
     "affects": {"owner": "you", "zone": "hand",
                 "filter": {"types": ["creature"],
                            "name_has": "ボルシャック"}},
     "mod": {"cost_may": {"amount": 2, "min": 1}}},
    {"kind": "static",
     "affects": {"owner": "you", "zone": "bz",
                 "filter": {"types": ["creature"],
                            "name_has": "ボルシャック"}},
     "mod": {"grant": ["speed_attacker"]}}]


def _reject_rows():
    rows = {}
    with open(ROOT / "data/cards/raw/rejects.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                rows[r["id"]] = r
    return rows


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_targets_registered_in_pilot303_forms():
    rows = _reject_rows()
    for tid in CANON + (FOLDED,):
        assert tid not in rows, tid          # rejects から外れた
    for tid in CANON:
        c = _conv(tid)
        assert c is not None, tid            # converted に登録済み
        assert not (c.get("source") or {}).get("unsupported"), tid
        assert c["types"] == ["field", "dragonic_field"], tid
        parse_card(c, TABLES)
    # 形A / 形B の完全一致（submit の連結・混入なし）
    c67 = _conv("dm26ex3-067")
    assert c67["abilities"] == [FORM_A]
    assert c67["text"].startswith("自分のターンのはじめに")
    assert (c67.get("source") or {}).get("aliases") == ALIASES_067
    cb = _conv("dmex15-b027")
    assert cb["abilities"] == FORM_B
    assert "ボルシャック" in cb["text"]
    # dmex12-011 は独立エントリではなく 067 の alias
    assert _conv(FOLDED) is None


def test_dragonic_field_cleared_from_rejects():
    rows = _reject_rows()
    holders = {rid for rid, r in rows.items()
               if "dragonic_field" in (r.get("gaps") or [])}
    assert holders == set(), holders
