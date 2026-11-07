"""公開イベントの記録（s.pub）: 誰が何を見たか。公平探索の信念更新の土台。"""
from conftest import setup
from test_vocab_pilot26 import _rig, _settle


def test_new_game_starts_empty(rules):
    e = setup(rules, {"deck": ["T001"] * 5})
    assert e.s.pub == []


def test_note_public_shape_and_clone(rules):
    e = setup(rules, {"deck": ["T073", "T001", "T001"]})
    top = e.s.zones["deck"][0][0]
    e.note_public("look", top, [0])
    e.note_public("shuffle", player=0, zone="deck")
    r = e.s.pub[0]
    assert (r["n"], r["kind"], r["viewers"], r["cid"], r["zone"], r["idx"]) == (0, "look", [0], top, "deck", 0)
    assert e.s.pub[1]["kind"] == "shuffle" and e.s.pub[1]["player"] == 0
    c = e.s.clone()
    c.pub.append({})
    assert len(e.s.pub) == 2          # 複製は独立


def test_gachinko_reveals_both(rules):
    e = setup(rules, {"hand": ["T073"], "mana": ["T004"] * 4, "deck": ["T073", "T001", "T001", "T001"]},
              {"deck": ["T001", "T073", "T001", "T001"]})
    _rig(e, 0, ["T073", "T001"])
    _rig(e, 1, ["T001", "T073"])
    _settle(e, lambda: any(r["kind"] == "reveal" for r in e.s.pub), play="T073")
    rv = [r for r in e.s.pub if r["kind"] == "reveal"]
    assert rv and all(r["viewers"] == [0, 1] and r["zone"] == "deck" for r in rv)
    assert {r["owner"] for r in rv} == {0, 1}
