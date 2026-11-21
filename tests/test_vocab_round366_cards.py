"""再変換ラウンド366（第331弾 name_addition）の記録テスト。

- 新規登録2件: dm23ex1-039 ボルメテウス・剣誠・ドラゴン /
  dm28-008 竜装 ムシャ・レジェンド。いずれも登録形は確立形と
  完全一致（dm28-008 は partial の形に add_names を足したもの）。
- alias 畳み込み0件（dm23ex1-039 の aliases 4件は partial 由来で
  rejects 行ではない）。
- converted 10,280→10,282 / rejects 2,034→2,032、
  canonical 重なり0・漏れ0。name_addition の行は multi の
  dmx15-002（g_link_360 と複合）だけが残る。

実挙動は登録カード自身で固定する: chars の names に追加の名前が
入ること（本人／クロス先）、G・ゼロの無料召喚、クロスした
クリーチャーの攻撃時誘発（シールドを墓地に置いて破壊）。
ドライバは scenario.build の薄い包みで、tests.conftest は
import しない（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

ADDED = "ボルメテウス・武者・ドラゴン"
OWN = "ボルメテウス・剣誠・ドラゴン"

FREE_IF = {"all": [
    {"cmp": [{"count": {"zone": "bz", "owner": "you",
                        "filter": {"race_has": "サムライ"}}}, ">=", 5]},
    {"not": {"exists": {"zone": "bz", "owner": "you",
                        "filter": {"name": OWN}}}}]}

ATTACK_TRIGGER = {
    "kind": "trigger", "when": {"event": "attack", "subject": "self"},
    "effect": [{"op": "may", "body": [
        {"op": "destroy",
         "select": {"zone": "bz", "owner": "opp",
                    "filter": {"types": ["creature"], "power_le": 6000},
                    "count": 1}}]}]}

FORM_039 = [ATTACK_TRIGGER,
            {"kind": "static", "affects": "self",
             "mod": {"add_names": [ADDED]}}]

GEAR_STATIC = {"kind": "static", "affects": "crossed",
               "mod": {"power": 2000,
                       "add_races": ["アーマード・ドラゴン", "サムライ"],
                       "add_names": [ADDED]}}

GEAR_TRIGGER = {
    "kind": "trigger", "when": {"event": "attack", "subject": "crossed"},
    "effect": [{"op": "may", "body": [
        {"op": "move", "select": {"zone": "shield", "owner": "you",
                                  "count": 1},
         "to": "graveyard", "reason": "put", "as": "paid"},
        {"op": "if", "cond": {"exists": {"ref": "paid"}},
         "then": [{"op": "destroy",
                   "select": {"zone": "bz", "owner": "opp",
                              "filter": {"types": ["creature"],
                                         "power_le": 6000},
                              "count": 1}}]}]}]}

FORM_008 = [GEAR_STATIC, GEAR_TRIGGER]


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


def test_round366_disposition():
    rej = _reject_rows()
    assert len(rej) == 2032
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10282
    assert not (ids & set(rej))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dm23ex1-039")
    assert c is not None and c["abilities"] == FORM_039
    assert c["free_if"] == FREE_IF
    assert (c.get("source") or {}).get("aliases") == \
        ["dmc45-006", "dmc55-006", "dmc59-001", "dmpcd02-a02"]
    c = _conv_cache.find(CONVERTED, "dm28-008")
    assert c is not None and c["abilities"] == FORM_008
    for t in ("dm23ex1-039", "dm28-008"):
        cc = _conv_cache.find(CONVERTED, t)
        assert not (cc.get("source") or {}).get("unsupported")
        parse_card(cc, TABLES)
    left = {rid for rid, r in rej.items()
            if "name_addition" in (r.get("gaps") or [])}
    assert left == {"dmx15-002"}, left


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _in_zone(e, p, zone, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def test_registered_added_name_and_g_zero(rules):
    e = _build(rules, {"bz": ["dm23ex1-039"]}, {})
    names = e.chars(_bz(e, 0, "dm23ex1-039"))["names"]
    assert OWN in names and ADDED in names
    # G・ゼロ: サムライ5体＋同名なしで無料召喚できる
    five = ["T341", "T341", "T342", "T342", "T352"]
    e = _build(rules, {"bz": five, "hand": ["dm23ex1-039"]}, {})
    assert "play:dm23ex1-039:free" in \
        [o["key"] for o in e._play_options(0)]
    # 同名が既にいれば無料にならない
    e = _build(rules, {"bz": ["T341", "T341", "T342", "T342",
                              "dm23ex1-039"],
                       "hand": ["dm23ex1-039"]}, {})
    assert "play:dm23ex1-039:free" not in \
        [o["key"] for o in e._play_options(0)]


def test_registered_crossed_gear(rules):
    """登録形 dm28-008: クロス先に名前・種族が足されパワー+2000。
    クロスしたクリーチャーの攻撃時、シールドを墓地に置くと
    相手のパワー6000以下を破壊する。"""
    e = _build(rules, {"bz": ["T001", "dm28-008"]}, {"bz": ["T001"]})
    host = _bz(e, 0, "T001")
    e.s.cards[_bz(e, 0, "dm28-008")].crossed = e.s.ref(host)
    ch = e.chars(host)
    assert ADDED in ch["names"]
    assert ch["power"] == 4000
    assert "アーマード・ドラゴン" in ch["races"]
    assert "サムライ" in ch["races"]
    e.s.cards[host].entered_turn = -1
    shields_before = len(e.zlist("shield", 0))
    attacked = False
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 \
                and "attack:T001:player" in keys:
            e.answer([keys.index("attack:T001:player")])
            attacked = True
            continue
        if attacked and _in_zone(e, 1, "graveyard", "T001"):
            break
        if d["kind"] == "yes_no":
            yes = next((k for k in keys if k.endswith(":yes")), keys[0])
            e.answer([keys.index(yes)])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert attacked
    assert _in_zone(e, 1, "graveyard", "T001")
    assert len(e.zlist("shield", 0)) == shields_before - 1
    assert len(e.zlist("graveyard", 0)) >= 1
