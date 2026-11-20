"""語彙パイロット第302弾の対象カード検証（ラウンド337で登録済み）。

gachinko_break_count 純粋3件（dm26rp2-tr009 / dmex12-009 = R.S.F.K.
の別々の正本2印刷、dmr05-v02 = 鬼無双 カイザー「勝」）はラウンド337で
登録された。ここでは登録形が第302弾の確立形（FORM_B /
FORM_A_TRIGGER）と完全一致し、ファミリーが rejects から解消した
ことを固定する。実挙動の判別は第302弾本体（プロト）とラウンド337
cards（登録カード自身）で固定済み。

確立形:
- 形B（R.S.F.K.）: attack 誘発 [gachinko {until_lose, stoppable,
  as: wins}, break {player: opp, count: {var: wins}}]（効果ブレイク。
  公式QA qa/42524 ほかで裏取り済み）。
- 形A（カイザー「勝」）: partial の repeat {times: {var: wins}} の
  body に modify {breaks_add: 1}（end_of_turn）を、本文の順序どおり
  パワー修正の後・ブロッカー破壊の前に1ステップ追加した形。

注意:
- dm26rp2-tr009 はツインパクトで、形Bはクリーチャー面にある
  （呪文面は partial のまま不変）。
- conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
  _conv_cache を直接使う（第319弾以降の作法）。
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
TARGETS = ("dm26rp2-tr009", "dmex12-009", "dmr05-v02")

FORM_B = {"kind": "trigger",
          "when": {"event": "attack", "subject": "self"},
          "effect": [
              {"op": "gachinko", "until_lose": True, "stoppable": True,
               "as": "wins"},
              {"op": "break", "player": "opp", "count": {"var": "wins"}}]}

BREAKS_STEP = {"op": "modify", "select": {"ref": "self"},
               "mod": {"breaks_add": 1}, "duration": "end_of_turn"}

FORM_A_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "attack", "subject": "self"},
    "effect": [
        {"op": "gachinko", "until_lose": True, "stoppable": True,
         "as": "wins"},
        {"op": "repeat", "times": {"var": "wins"}, "body": [
            {"op": "modify", "select": {"ref": "self"},
             "mod": {"power": 6000}, "duration": "end_of_turn"},
            BREAKS_STEP,
            {"op": "destroy",
             "select": {"zone": "bz", "owner": "opp", "count": 1,
                        "chooser": "opp",
                        "filter": {"types": ["creature"],
                                   "keyword": "blocker"}}}]}]}


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


def test_targets_registered_in_pilot302_forms():
    rows = _reject_rows()
    for tid in TARGETS:
        assert tid not in rows, tid          # rejects から外れた
        c = _conv(tid)
        assert c is not None, tid            # converted に登録済み
        assert not (c.get("source") or {}).get("unsupported"), tid
        parse_card(c, TABLES)
    # 形B（R.S.F.K. 2印刷とも独立の正本として登録）
    assert _conv("dmex12-009")["abilities"] == [FORM_B]
    tr = _conv("dm26rp2-tr009")
    assert tr["faces"][0]["abilities"] == [FORM_B]
    # 形A（カイザー）: 登録形が確立形と完全一致し、parse 後も repeat
    # body に breaks_add の modify が残る
    v02 = _conv("dmr05-v02")
    assert v02["abilities"] == [FORM_A_TRIGGER]
    d = parse_card(v02, TABLES)
    parsed = next(a for a in d.abilities if a.get("kind") == "trigger")
    assert BREAKS_STEP in parsed["effect"][1]["body"]


def test_gachinko_break_count_cleared_from_rejects():
    rows = _reject_rows()
    holders = {rid for rid, r in rows.items()
               if "gachinko_break_count" in (r.get("gaps") or [])}
    assert holders == set(), holders
