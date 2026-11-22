"""再変換ラウンド384（第349弾 summon_lock）の記録テスト。

- 新規登録3件: promoy11-083 鬼丸「Ｅｎｄ」 /
  promoy12-036 激流剣砲 カツ∞キング /
  promoy12-085 漢のキズナ カツブードン（登録形は意図した
  形と完全一致）。
- converted 10,322→10,325 / rejects 1,991→1,988、
  canonical 重なり0・漏れ0。
- summon_lock は dmx25-s07 にだけ残る（原文断片のみの
  ため対象外。reopen で外れた行は原文どおり復帰済み）。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない（第319弾以降の作法）。
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


def _lock5(name_has):
    return [{"kind": "static",
             "affects": {"zone": z, "owner": "you",
                         "filter": {"types": ["exile_creature"],
                                    "name_has": name_has}},
             "mod": {"deny": ["enter_bz"]}}
            for z in ("hand", "graveyard", "mana", "deck", "shield")]


LOCK_ZENITH = {
    "kind": "static",
    "affects": {"zone": "hand", "owner": "any",
                "filter": {"types": ["creature"], "race_has": "ゼニス"}},
    "mod": {"deny": ["summon"]},
}
BATTLE_ZENITH = {
    "kind": "static", "affects": "self",
    "mod": {"battle_power": {"amount": 11000,
                             "opponent_filter": {"race_has": "ゼニス"}}},
}
CIP_036 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "destroy",
                "select": {"zone": "bz", "owner": "opp",
                           "filter": {"types": ["creature"],
                                      "keyword": "blocker"},
                           "count": "all"}},
               {"op": "may", "body": [{"op": "draw", "count": 1}]}],
}
CIP_085 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "may",
                "body": [{"op": "move",
                          "select": {"zone": "bz", "owner": "you",
                                     "filter": {"types": ["creature"]},
                                     "count": 1,
                                     "exclude": [{"ref": "self"}]},
                          "to": "graveyard", "reason": "destroy",
                          "as": "dead"}]},
               {"op": "if",
                "cond": {"cmp": [{"count": {"ref": "dead"}}, ">=", 1]},
                "then": [{"op": "choose",
                          "select": {"zone": "deck", "owner": "you",
                                     "look": True,
                                     "filter": {"types": ["exile_creature"]},
                                     "count": 1},
                          "as": "found"},
                         {"op": "may",
                          "body": [{"op": "move",
                                    "select": {"ref": "found",
                                               "count": "all"},
                                    "to": "hand", "reason": "draw"}]},
                         {"op": "shuffle"}]}],
}
FORM_083 = [LOCK_ZENITH, BATTLE_ZENITH]
FORM_036 = [CIP_036] + _lock5("剣砲")
FORM_085 = [CIP_085] + _lock5("漢のキズナ カツブードン")


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


def test_round384_disposition():
    rej = _reject_rows()
    assert len(rej) == 1988
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10325
    assert not (ids & set(rej))          # canonical 重なり0
    for tid, form in (("promoy11-083", FORM_083),
                      ("promoy12-036", FORM_036),
                      ("promoy12-085", FORM_085)):
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None and c["abilities"] == form
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    left = {rid for rid, r in rej.items()
            if "summon_lock" in (r.get("gaps") or [])}
    assert left == {"dmx25-s07"}, left


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _drive_to_main(e, player=0, limit=300):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] == "main" and d.get("player") == player:
            return d, _keys(d)
        if "pass" in _keys(d):
            e.answer([_keys(d).index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("main never came")


def test_registered_onimaru_locks_zenith(rules):
    zmana = ["T789", "T001", "T001"]     # ゼロ文明のマナを含む
    e = _build(rules, {"bz": ["promoy11-083"]},
               {"hand": ["T787"], "mana": zmana})
    d, keys = _drive_to_main(e, player=1)
    assert "play:T787" not in keys
    e = _build(rules, {}, {"hand": ["T787"], "mana": zmana})
    d, keys = _drive_to_main(e, player=1)
    assert "play:T787" in keys


def test_registered_katsuking_lock_and_cip(rules):
    # ロック: 剣砲エグザイル T1053 を出せない
    e = _build(rules, {"bz": ["promoy12-036"], "hand": ["T1053"],
                       "mana": ["T001", "T001", "T001"]}, {})
    d, keys = _drive_to_main(e)
    assert "play:T1053" not in keys
    # CIP: 相手のブロッカーをすべて破壊する
    e = _build(rules, {"hand": ["promoy12-036"],
                       "mana": ["T009", "T005"] + ["T001"] * 7},
               {"bz": ["T004", "T004", "T005"]})
    d, keys = _drive_to_main(e)
    assert "play:promoy12-036" in keys
    e.answer([keys.index("play:promoy12-036")])
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 1:
            break
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("yes")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert [e.s.cards[c].defn for c in e.bz_tops(1)] == ["T005"]
