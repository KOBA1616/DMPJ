"""第250弾: 名前指定 + 位置キーワードの G・リンク（邪神ロマノフ三体）。"""
from tests.conftest import setup


def _keys(d):
    return [o["key"] for o in d["options"]]


def _cid(e, defn, player=0):
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _drive(e, summons, link_targets, limit=400):
    summons = list(summons)
    link_targets = dict(link_targets)
    seen = []
    current = None
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and summons:
            want = f"play:{summons[0]}"
            if want in keys:
                e.answer([keys.index(want)])
                current = summons.pop(0)
                continue
        if d["kind"] == "choose_link_target":
            seen.append(list(keys))
            tgt = link_targets.get(current)
            if tgt is not None and any(tgt in k for k in keys):
                e.answer([next(i for i, k in enumerate(keys) if tgt in k)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "choose_unlink":
            e.answer([keys.index("done")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return seen


def test_m_links_to_named_c(rules=None):
    from dmsim.cards.defs import load_rules
    e = setup(load_rules(), {"hand": ["T675"], "mana": ["T034"] * 5 + ["T030"] * 5, "bz": ["T677"]},
              {"bz": ["T001"]}, filler="T002")
    seen = _drive(e, ["T675"], {"T675": "T677"})
    assert seen, "choose_link_target never appeared"
    m, c = _cid(e, "T675"), _cid(e, "T677")
    assert e.s.cards[m].link and e.s.cards[m].link == e.s.cards[c].link


def test_m_no_link_to_wrong_name_center():
    from dmsim.cards.defs import load_rules
    e = setup(load_rules(), {"hand": ["T675"], "mana": ["T034"] * 5 + ["T030"] * 5, "bz": ["T678"]},
              {"bz": ["T001"]}, filler="T002")
    seen = _drive(e, ["T675"], {"T675": "T678"})
    assert seen == []                      # 名前が違う中央ゴッドにはリンクできない
    assert e.s.cards[_cid(e, "T675")].link == 0


def test_r_tri_link_joins_pair():
    from dmsim.cards.defs import load_rules
    e = setup(load_rules(), {"hand": ["T675", "T676"], "mana": ["T034"] * 7 + ["T008"] * 7, "bz": ["T677"]},
              {"bz": ["T001"]}, filler="T002")
    seen = _drive(e, ["T675", "T676"], {"T675": "T677", "T676": "T675"}, limit=900)
    assert len(seen) >= 2, "M と R のリンク手順が出ない"
    r = _cid(e, "T676")
    members = e.link_members(r)
    assert sorted(e.s.cards[m].defn for m in members) == ["T675", "T676", "T677"]
    assert len(e.bz_tops(0)) == 1


def test_omg_links_to_sideless_named_god():
    from dmsim.cards.defs import load_rules
    e = setup(load_rules(), {"hand": ["T679"], "mana": ["T034"] * 5 + ["T030"] * 5, "bz": ["T676"]},
              {"bz": ["T001"]}, filler="T002")
    seen = _drive(e, ["T679"], {"T679": "T676"})
    assert seen, "位置キーワードを持たない名前指定ゴッドへのリンク手順が出ない"
    m, r = _cid(e, "T679"), _cid(e, "T676")
    assert e.s.cards[m].link and e.s.cards[m].link == e.s.cards[r].link


def test_omg_links_to_any_center_god():
    from dmsim.cards.defs import load_rules
    e = setup(load_rules(), {"hand": ["T679"], "mana": ["T034"] * 5 + ["T030"] * 5, "bz": ["T678"]},
              {"bz": ["T001"]}, filler="T002")
    seen = _drive(e, ["T679"], {"T679": "T678"})
    assert seen, "中央 G・リンク持ち（名前指定なし）へのリンク手順が出ない"
    m, c = _cid(e, "T679"), _cid(e, "T678")
    assert e.s.cards[m].link and e.s.cards[m].link == e.s.cards[c].link


def test_omg_no_link_to_left_god():
    from dmsim.cards.defs import load_rules
    e = setup(load_rules(), {"hand": ["T679"], "mana": ["T034"] * 5 + ["T030"] * 5, "bz": ["T675"]},
              {"bz": ["T001"]}, filler="T002")
    seen = _drive(e, ["T679"], {"T679": "T675"})
    assert seen == []                      # 左 G・リンク持ちは OMG の指定外
    assert e.s.cards[_cid(e, "T679")].link == 0
