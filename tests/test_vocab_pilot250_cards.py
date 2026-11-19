"""第250弾の登録形: dmc58-003 / dmc58-004 / dmex17-037（ラウンド284）。"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card
from dmsim.scenario import build

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)


def _converted(cid):
    import yaml
    for c in yaml.safe_load(open(CONVERTED))["cards"]:
        if c["id"] == cid:
            return c
    raise KeyError(cid)


def test_registered_forms():
    for cid in ("dmc58-003", "dmc58-004", "dmex17-037"):
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        assert card.get("link_to"), cid
    assert _converted("dmex17-037")["link_to"][2] == {"side": "center"}


def _drive_play_and_link(e, play_defn, target_defn, limit=600):
    linked_seen = []
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_link_target":
            linked_seen.append(list(keys))
            idx = next((i for i, k in enumerate(keys) if target_defn in k), None)
            if idx is not None:
                e.answer([idx])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "main" and d.get("player") == 0 and f"play:{play_defn}" in keys:
            e.answer([keys.index(f"play:{play_defn}")])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        done = [c for c in e.zlist("bz", 0) if e.s.cards[c].defn == play_defn]
        if done and e.s.cards[done[0]].link:
            break
    return linked_seen


def _cid(e, defn):
    return next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == defn)


def test_registered_omg_links_to_solo_r():
    rules = load_rules()
    e = build(rules, {"p0": {"bz": ["dmc58-004"], "hand": ["dmex17-037"], "mana": ["T034"] * 5},
                      "p1": {"deck": ["T001"] * 12},
                      "filler": "T001", "seed": 1, "deck_size": 20})
    seen = _drive_play_and_link(e, "dmex17-037", "dmc58-004")
    assert seen, "OMG のリンク手順が出ない"
    omg, r = _cid(e, "dmex17-037"), _cid(e, "dmc58-004")
    assert e.s.cards[omg].link and e.s.cards[omg].link == e.s.cards[r].link


def test_registered_m_links_to_c():
    rules = load_rules()
    e = build(rules, {"p0": {"bz": ["dmc58-001"], "hand": ["dmc58-003"], "mana": ["T034"] * 5},
                      "p1": {"deck": ["T001"] * 12},
                      "filler": "T001", "seed": 1, "deck_size": 20})
    seen = _drive_play_and_link(e, "dmc58-003", "dmc58-001")
    assert seen, "M のリンク手順が出ない"
    m, c = _cid(e, "dmc58-003"), _cid(e, "dmc58-001")
    assert e.s.cards[m].link and e.s.cards[m].link == e.s.cards[c].link
