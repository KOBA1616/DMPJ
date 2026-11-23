"""再変換ラウンド367（第332弾 destroyed_during_battle_trigger）の記録テスト。

- 新規登録2件: dm24rp4-070 ライラ・理・アイニー /
  dm22rp2x-026 真価と代価のチェスト。いずれも登録形は
  確立形と完全一致。
- dm22rp2x-026 は submit のバリデータ警告で1件修正:
  ターン終わりの帰還は「出す」であり召喚ではないため
  move の reason を summon から put に変更（proto・回答・
  converted の3か所を一致。第329弾と同じ修正）。
- alias 畳み込み0件（dm22rp2x-026 の aliases [dm22rp2-026] は
  submit 時の自動記録で rejects 行ではない）。
- converted 10,282→10,284 / rejects 2,032→2,030、
  canonical 重なり0・漏れ0。destroyed_during_battle_trigger は
  残り0件でファミリー解消。

実挙動は登録カード自身で固定する（バトルで破壊→シールド
ブレイク、バトルで破壊→ターン終わりに帰還、呪文破壊では
どちらも起きない）。ドライバは scenario.build の薄い包みで、
tests.conftest は import しない（第319弾以降の作法）。
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

TRIGGER_070 = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy", "battle": True, "subject": "self"},
    "effect": [{"op": "may", "body": [
        {"op": "break", "player": "opp", "count": 1}]}]}

CIVIL_LIGHT = {
    "kind": "static",
    "affects": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}},
    "if": {"cmp": [{"count": {"zone": "bz", "owner": "you",
                              "filter": {"civs": ["light"],
                                         "types": ["creature", "tamaseed"]}}},
                   ">=", 3]},
    "mod": {"grant": ["blocker"]}}

CIVIL_DARK = {
    "kind": "static",
    "affects": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}},
    "if": {"cmp": [{"count": {"zone": "bz", "owner": "you",
                              "filter": {"civs": ["darkness"],
                                         "types": ["creature", "tamaseed"]}}},
                   ">=", 3]},
    "mod": {"grant": ["slayer"]}}

RETURN_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy", "battle": True,
             "subject": {"owner": "you",
                         "filter": {"types": ["creature"]}}},
    "effect": [
        {"op": "choose", "select": {"ref": "event.subject"},
         "as": "dead"},
        {"op": "delayed_trigger", "when": {"event": "turn_end"},
         "effect": [{"op": "move", "select": {"ref": "dead"},
                     "to": "bz", "reason": "put"}]}]}

FORM_070 = [TRIGGER_070]
FORM_026 = [CIVIL_LIGHT, CIVIL_DARK, RETURN_TRIGGER]


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


def test_round367_disposition():
    rej = _reject_rows()
    assert len(rej) == 2030
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10284
    assert not (ids & set(rej))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dm24rp4-070")
    assert c is not None and c["abilities"] == FORM_070
    assert not (c.get("source") or {}).get("aliases")
    c = _conv_cache.find(CONVERTED, "dm22rp2x-026")
    assert c is not None and c["abilities"] == FORM_026
    assert (c.get("source") or {}).get("aliases") == ["dm22rp2-026"]
    for t in ("dm24rp4-070", "dm22rp2x-026"):
        cc = _conv_cache.find(CONVERTED, t)
        assert not (cc.get("source") or {}).get("unsupported")
        parse_card(cc, TABLES)
    left = {rid for rid, r in rej.items()
            if "destroyed_during_battle_trigger" in (r.get("gaps") or [])}
    assert left == set(), left


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


def _attack_block_drive(e, attacker, stop_at_yes_no=False):
    """attacker で攻撃し T1004 にブロックさせ、バトル後の
    落ち着いた決定（または yes_no）まで進めてその決定を返す。"""
    t = _bz(e, 0, attacker)
    e.s.cards[t].entered_turn = -1
    blocked = False
    for _ in range(400):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 \
                and f"attack:{attacker}:player" in keys:
            e.answer([keys.index(f"attack:{attacker}:player")])
            continue
        if d["kind"] == "block":
            pick = next((k for k in keys if "T1004" in k), None)
            assert pick is not None, keys
            e.answer([keys.index(pick)])
            blocked = True
            continue
        if blocked and d["kind"] == "yes_no" and stop_at_yes_no:
            return d
        if blocked and d["kind"] in ("charge", "main", "attack") \
                and d.get("player") == 1:
            return d
        if blocked and d["kind"] == "charge":
            return d
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("battle did not resolve")


def test_registered_battle_destroy_breaks_shield(rules):
    e = _build(rules, {"bz": ["dm24rp4-070"]}, {"bz": ["T1004"]})
    shields_before = len(e.zlist("shield", 1))
    d = _attack_block_drive(e, "dm24rp4-070", stop_at_yes_no=True)
    assert _in_zone(e, 0, "graveyard", "dm24rp4-070")
    assert d["kind"] == "yes_no"
    keys = _keys(d)
    yes = next((k for k in keys if k.endswith(":yes")), keys[0])
    e.answer([keys.index(yes)])
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] == "charge" and d.get("player") == 1:
            break
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert len(e.zlist("shield", 1)) == shields_before - 1


def test_registered_delayed_return(rules):
    e = _build(rules, {"bz": ["dm22rp2x-026", "T001"]}, {"bz": ["T1004"]})
    _attack_block_drive(e, "T001")
    # ターン終わりに戻り、アンタップで場にある（攻撃したまま
    # 生存したクリーチャーはタップしているはず）
    t1 = _bz(e, 0, "T001")
    assert not e.s.cards[t1].tapped
    assert not _in_zone(e, 0, "graveyard", "T001")
