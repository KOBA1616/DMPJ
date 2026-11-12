"""語彙パイロット第177弾: choukon_raid（超魂レイド）。

「このクリーチャーが出た時、山札の上から3枚を表向きにする。その中から
このクリーチャーの進化元になれるカードを1枚、この下に置いてもよい。
残りを好きな順序で山札の下に置く」

- 新フィルタキー `evo_source_of`（値は "self" / 変数名）: 候補がその
  クリーチャーの進化元になれる（クリーチャーであること＋evolve_from の
  いずれかに合う）かを照合する。_evo_sources と同型の判定。
- 超魂レイドの書き方: reveal_until {as: pile, filter: {}, count: 3} で
  上3枚を公開し、if exists（適格カードがある時だけ）→ may → put_under
  （onto は {ref: self}）→ 残りを move で山札の下へ（order: choose）。
  下に置いたカードは gen が進むので、残りの move の ref 束縛から外れる。
"""
import pytest
import yaml
from pathlib import Path

from conftest import setup

from dmsim.defs import DefError, load_tables, parse_card

TABLES = load_tables()
ROOT = Path(__file__).parent.parent
IDS = ("T394", "T395", "T396", "T397")


def _proto_card(cid):
    with open(ROOT / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _raid_ability(card):
    return next(a for a in card["abilities"]
                if a.get("kind") == "trigger"
                and a.get("when") == {"event": "move", "to": "bz", "subject": "self"}
                and any(o.get("op") == "reveal_until" for o in a.get("effect", [])))


def test_proto_parse():
    t394 = _proto_card("T394")
    assert parse_card(t394, TABLES).evolve_from == {"civs": ["darkness", "fire", "nature"]}
    raid = _raid_ability(t394)
    eff = raid["effect"]
    assert eff[0] == {"op": "reveal_until", "as": "pile", "filter": {}, "count": 3}
    assert eff[1]["op"] == "if"
    assert eff[1]["cond"] == {"exists": {"ref": "pile", "filter": {"evo_source_of": "self"}}}
    put = eff[1]["then"][0]["body"][0]
    assert put["op"] == "put_under"
    assert put["select"] == {"count": 1, "up_to": True, "ref": "pile",
                             "filter": {"evo_source_of": "self"}}
    assert put["onto"] == {"ref": "self"}
    assert eff[2] == {"op": "move", "select": {"count": "all", "ref": "pile"},
                      "to": "deck", "position": "bottom", "order": "choose", "reason": "put"}
    assert parse_card(_proto_card("T395"), TABLES).evolve_from == {"races": ["テスト"]}
    t396 = parse_card(_proto_card("T396"), TABLES)
    assert t396.evolve_from == [{"civs": ["fire"]}, {"races": ["テスト"]}]
    assert len(_proto_card("T396")["abilities"]) == 2
    t397 = _proto_card("T397")
    atk = [a for a in t397["abilities"]
           if a.get("when") == {"event": "attack", "subject": "self"}]
    assert len(atk) == 1
    assert atk[0]["effect"][0] == {"op": "draw", "count": 2}


def test_bad_forms_rejected():
    base = dict(_proto_card("T394"))
    bad = dict(base)
    bad["abilities"] = [{"kind": "trigger",
                         "when": {"event": "move", "to": "bz", "subject": "self"},
                         "effect": [{"op": "reveal_until", "as": "pile",
                                     "filter": {"evo_source_of": 5}, "count": 3}]}]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad2 = dict(base)
    bad2["abilities"] = [{"kind": "trigger",
                          "when": {"event": "move", "to": "bz", "subject": "self"},
                          "effect": [{"op": "reveal_until", "as": "pile",
                                      "filter": {"evo_source_of": {"ref": "pile"}},
                                      "count": 3}]}]
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)
    bad3 = dict(base)
    bad3["abilities"] = [{"kind": "trigger",
                          "when": {"event": "move", "to": "bz", "subject": "self"},
                          "effect": [{"op": "reveal_until", "as": "pile",
                                      "filter": {"evo_source_ofx": "self"}, "count": 3}]}]
    with pytest.raises(DefError):
        parse_card(bad3, TABLES)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _settle(e, done, drive=None, max_steps=400):
    seen = []
    for _ in range(max_steps):
        if done():
            return True, seen
        d = e.advance()
        if d is None:
            break
        seen.append(d["kind"])
        if done():
            # 状態が満たされた直後の決定は答えずに止める（次の _settle が同じ
            # 決定から再開できる）。答えてしまうとメインを pass してターンが
            # 進み、手札枚数などの前提が崩れる
            return True, seen
        keys = _keys(d)
        if drive and drive(e, d, keys):
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["kind"] == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        else:
            e.answer(list(range(d["min"])))
    return done(), seen


def _arrange_deck(e, p, top_defns):
    """山札の上から top_defns の順に並べ替え、その cid リストを返す。"""
    rest = list(e.s.zones["deck"][p])
    chosen = []
    for dfn in top_defns:
        c = next(c for c in rest if e.s.cards[c].defn == dfn)
        rest.remove(c)
        chosen.append(c)
    e.s.zones["deck"][p] = chosen + rest
    return chosen


def _drive_raid(e, d, keys, defn, under_defn=None, bottom_order=None, may_answer="yes"):
    if d["kind"] == "charge" and "pass" in keys:
        e.answer([keys.index("pass")])
        return True
    if d["kind"] == "main" and f"play:{defn}" in keys:
        e.answer([keys.index(f"play:{defn}")])
        return True
    if d["kind"] == "pay_mana":
        e.answer([0])
        return True
    if d["kind"] == "yes_no":
        e.answer([keys.index(may_answer)])
        return True
    if d["kind"] == "choose_cards" and under_defn:
        # 山札のカードのキーはすべて "deck"（look=False）なので、cid から defn で選ぶ
        hit = [i for i, o in enumerate(d["options"])
               if o.get("cid") is not None and e.s.cards[o["cid"]].defn == under_defn]
        if hit:
            e.answer([hit[0]])
            return True
    if d["kind"] == "order_cards" and bottom_order:
        idx = [next(i for i, k in enumerate(keys) if dfn in k) for dfn in bottom_order]
        e.answer(idx)
        return True
    if d["kind"] in ("declare_strigger", "declare_sback"):
        e.answer([])
        return True
    return False


def _play_and_resolve(e, defn, cond, drive):
    def _drive(e, d, keys):
        return _drive_raid(e, d, keys, defn, **drive) if isinstance(drive, dict) else drive(e, d, keys)
    ok, seen = _settle(e, cond, _drive)
    return ok, seen


def _cid(e, defn):
    return next(i for i, c in enumerate(e.s.cards) if c.defn == defn)


def test_raid_picks_eligible_and_rest_to_bottom(rules):
    """T394: 上3枚のうち火・自然のクリーチャー2体が適格。T005 を下に置き、
    残り（T001・T003）を答えた順で山札の下へ。呪文 T003 は適格でない。"""
    e = setup(rules, {"hand": ["T394"], "mana": ["T005"] * 3,
                      "deck": ["T005", "T003", "T001"]}, {})
    top, spell, other = _arrange_deck(e, 0, ["T005", "T003", "T001"])
    me = _cid(e, "T394")
    deck_n = len(e.s.zones["deck"][0])
    ok, _ = _play_and_resolve(
        e, "T394",
        lambda: top in e.s.cards[me].under and e.s.zones["deck"][0][-2:] == [other, spell],
        {"under_defn": "T005", "bottom_order": ["T001", "T003"]})
    assert ok, "超魂レイドが解決しなかった"
    assert e.s.cards[top].zone == "bz" and e.s.cards[top].top_of == me
    assert e.s.cards[spell].zone == "deck" and e.s.cards[other].zone == "deck"
    assert len(e.s.zones["deck"][0]) == deck_n - 1  # 下に置いた1枚だけ山札を離れた
    assert e.s.cards[me].zone == "bz"


def test_raid_no_eligible_skips_may(rules):
    """T394: 上3枚がすべて呪文なら適格カードは無く、may の問いが出ない。
    3枚とも山札の下へ（並びは答えた順）。"""
    e = setup(rules, {"hand": ["T394"], "mana": ["T005"] * 3,
                      "deck": ["T003", "T012", "T006"]}, {})
    a, b, c = _arrange_deck(e, 0, ["T003", "T012", "T006"])
    me = _cid(e, "T394")
    ok, seen = _play_and_resolve(
        e, "T394",
        lambda: e.s.zones["deck"][0][-3:] == [c, b, a],
        {"bottom_order": ["T006", "T012", "T003"]})
    assert ok, "残りの山札の下への移動が終わらなかった"
    assert "yes_no" not in seen, f"適格なしなのに may が出た: {seen}"
    assert e.s.cards[me].under == []
    assert all(e.s.cards[x].zone == "deck" for x in (a, b, c))


def test_raid_may_decline(rules):
    """T394: may で「いいえ」を選ぶと何も下に置かず、3枚とも山札の下へ。"""
    e = setup(rules, {"hand": ["T394"], "mana": ["T005"] * 3,
                      "deck": ["T005", "T003", "T001"]}, {})
    a, b, c = _arrange_deck(e, 0, ["T005", "T003", "T001"])
    me = _cid(e, "T394")
    ok, seen = _play_and_resolve(
        e, "T394",
        lambda: e.s.zones["deck"][0][-3:] == [a, b, c],
        {"may_answer": "no", "bottom_order": ["T005", "T003", "T001"]})
    assert ok, "may 拒否後の移動が終わらなかった"
    assert "yes_no" in seen
    assert e.s.cards[me].under == []
    assert all(e.s.cards[x].zone == "deck" for x in (a, b, c))


def test_raid_race_form(rules):
    """T395: evolve_from が種族形。種族 [テスト] のクリーチャーだけが適格で、
    火の呪文（文明は合う）は適格でない。"""
    e = setup(rules, {"hand": ["T395"],
                      "mana": ["T004"] * 4 + ["T005"] * 3,
                      "deck": ["T011", "T004", "T008"]}, {})
    spell, light, dark = _arrange_deck(e, 0, ["T011", "T004", "T008"])
    me = _cid(e, "T395")
    ok, _ = _play_and_resolve(
        e, "T395",
        lambda: dark in e.s.cards[me].under and e.s.zones["deck"][0][-2:] == [spell, light],
        {"under_defn": "T008", "bottom_order": ["T011", "T004"]})
    assert ok, "種族形の超魂レイドが解決しなかった"
    assert e.s.cards[dark].top_of == me
    assert e.s.cards[spell].zone == "deck"  # 火の呪文はクリーチャーでないので不適格


def test_raid_list_form_evolve_from(rules):
    """T396: evolve_from がリスト形。火のクリーチャー（civs 側）も
    [テスト] 種族（races 側）も適格。火の呪文は不適格。"""
    e = setup(rules, {"hand": ["T396"], "mana": ["T005"] * 5,
                      "deck": ["T006", "T005", "T004"]}, {},
              )
    spell, fire, light = _arrange_deck(e, 0, ["T006", "T005", "T004"])
    me = _cid(e, "T396")
    ok, _ = _play_and_resolve(
        e, "T396",
        lambda: fire in e.s.cards[me].under and e.s.zones["deck"][0][-2:] == [light, spell],
        {"under_defn": "T005", "bottom_order": ["T004", "T006"]})
    assert ok, "リスト形の超魂レイドが解決しなかった"
    assert e.s.cards[fire].top_of == me
    assert e.s.cards[spell].zone == "deck"


def test_raid_with_second_cip_trigger(rules):
    """T396: 超魂レイドと CIP 破壊が両方誘発する。相手のコスト3以下を破壊し、
    かつ適格カードを下に置く。"""
    e = setup(rules, {"hand": ["T396"], "mana": ["T005"] * 5,
                      "deck": ["T005", "T003", "T001"]},
              {"bz": ["T008"]})
    top, spell, other = _arrange_deck(e, 0, ["T005", "T003", "T001"])
    me = _cid(e, "T396")
    opp = _cid(e, "T008")
    ok, _ = _play_and_resolve(
        e, "T396",
        lambda: (top in e.s.cards[me].under
                 and e.s.cards[opp].zone == "graveyard"
                 and e.s.zones["deck"][0][-2:] == [other, spell]),
        {"under_defn": "T005", "bottom_order": ["T001", "T003"]})
    assert ok, "レイド＋CIP 破壊の両方が解決しなかった"
    assert e.s.cards[opp].zone == "graveyard"


def test_raid_attack_trigger(rules):
    """T397: 場に出ている状態から攻撃すると、攻撃時誘発で2ドロー2捨て。
    相手のシールドが1枚ブレイクされる。"""
    e = setup(rules, {"bz": ["T397"], "hand": ["T001", "T002"]}, {})
    me = _cid(e, "T397")
    assert e.s.cards[me].entered_turn == 0

    def drive(e, d, keys):
        if d["kind"] == "charge" and "pass" in keys:
            e.answer([keys.index("pass")])
            return True
        if d["kind"] == "main" and "pass" in keys:
            e.answer([keys.index("pass")])
            return True
        if d["kind"] == "attack" and "attack:T397:player" in keys:
            e.answer([keys.index("attack:T397:player")])
            return True
        if d["kind"] in ("declare_strigger", "declare_sback"):
            e.answer([])
            return True
        return False

    ok, _ = _settle(e, lambda: len(e.zlist("shield", 1)) == 4, drive)
    assert ok, "攻撃がブレイクまで進まなかった"
    assert len(e.zlist("graveyard", 0)) == 2, "2枚捨てられていない"
    assert len(e.zlist("hand", 0)) == 2, "2ドロー2捨て後の手札が2枚でない"
