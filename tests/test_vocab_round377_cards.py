"""再変換ラウンド377（第342弾 battle_power_grant）の記録テスト。

- 新規登録2件: dmr11-016 破戒のインガ シャンツァイ /
  dm23rp2x-006 ボルシャック・ノブリス・ドラゴン。
- alias 畳み込み0件（submit 時に 006 へ aliases 2件が
  自動記録されたが rejects 行ではない）・差し戻し0件。
- converted 10,307→10,309 / rejects 2,007→2,005、
  canonical 重なり0・漏れ0。battle_power_grant の行は
  残っていない（ファミリー解消）。
- submit の事故（第374弾と同型）: 006 は partial の化け形の
  コスト常在型がルール変換側にも残っており、submit が先頭に
  足したため意図した形と完全一致せず dedupe されず4能力で
  登録された。化け形側を除去し意図した3能力に直して固定した
  （converted.yaml の差分は新規2件の追加のみであることを確認）。

実挙動は登録カード自身で固定する（016 の付与でゴッドが勝ち、
006 の付与でアーマードが勝つ）。ドライバは scenario.build の
薄い包みで、tests.conftest は import しない（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402

from tests import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

OPT_REDUCE_016 = {
    "kind": "static", "affects": "self", "zone": "hand",
    "mod": {"opt_reduce": {"amount": 1, "per": True, "floor": 2,
                           "do": {"select": {"zone": "hand",
                                             "owner": "you",
                                             "filter": {"race_has": "ゴッド"}}}}},
}
GRANT_016 = {
    "kind": "static",
    "affects": {"owner": "you",
                "filter": {"any_of": [{"race_has": "オラクル"},
                                      {"race_has": "ゴッド"}]}},
    "mod": {"battle_power": {"amount": 3000}},
}
GRANT_006 = {
    "kind": "static",
    "affects": {"owner": "you", "filter": {"race_has": "アーマード"}},
    "mod": {"battle_power": {"amount": 3000}},
}
COST_006_FIXED = {
    "kind": "static", "zone": "hand", "affects": "self",
    "if": {"cmp": [{"count": {"zone": "bz", "owner": "you",
                              "filter": {"civs": ["fire"]}}},
                    ">=", 3]},
    "mod": {"cost": -3},
}
MEKURADE_006 = {
    "kind": "trigger",
    "when": {"event": "summon", "subject": "self"},
    "effect": [{"op": "mekurade", "filter": {"race_has": "アーマード"},
                "cost_le": 8},
               {"op": "mekurade", "filter": {"race_has": "アーマード"},
                "cost_le": 8}],
}
FORM_016 = [OPT_REDUCE_016, GRANT_016]
FORM_006 = [COST_006_FIXED, MEKURADE_006, GRANT_006]


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


def test_round377_disposition():
    rej = _reject_rows()
    assert len(rej) == 2005
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10309
    assert not (ids & set(rej))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dmr11-016")
    assert c is not None and c["abilities"] == FORM_016
    assert not (c.get("source") or {}).get("unsupported")
    parse_card(c, TABLES)
    c = _conv_cache.find(CONVERTED, "dm23rp2x-006")
    assert c is not None and c["abilities"] == FORM_006
    assert not (c.get("source") or {}).get("unsupported")
    parse_card(c, TABLES)
    left = {rid for rid, r in rej.items()
            if "battle_power_grant" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _battle(e, attacker, defender, limit=300):
    tgt = next(c for c in e.bz_tops(1)
               if e.s.cards[c].defn == defender)
    e.s.cards[tgt].tapped = True
    key = f"attack:{attacker}:{defender}"
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        k = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 \
                and key in k:
            e.answer([k.index(key)])
            continue
        if d["kind"] == "charge" and d.get("player") == 1:
            return
        if d["kind"] == "block" and "no_block" in k:
            e.answer([k.index("no_block")])
            continue
        if d["kind"] == "choose_shields":
            e.answer([])
            continue
        if "pass" in k:
            e.answer([k.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def test_registered_inga_god_bonus(rules):
    e = _build(rules, {"bz": ["dmr11-016", "T053"]}, {"bz": ["T005"]})
    _battle(e, "T053", "T005")          # ゴッド 2000+3000 > 3000
    assert "T053" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    assert [e.s.cards[c].defn
            for c in e.zlist("graveyard", 1)] == ["T005"]


def test_registered_noblesse_armored_bonus(rules):
    e = _build(rules, {"bz": ["dm23rp2x-006", "T277"]}, {"bz": ["T005"]})
    _battle(e, "T277", "T005")          # アーマード 1000+3000 > 3000
    assert "T277" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    assert [e.s.cards[c].defn
            for c in e.zlist("graveyard", 1)] == ["T005"]
