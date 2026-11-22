"""語彙パイロット第337弾: evolution_base_from_graveyard。

対象（pure 3件）:
- dm25rp1-018 至高の邪騎 スベルニル（出た時、このクリーチャー
  から進化できるコスト5以下の NEO／進化クリーチャーを1体、
  自分の墓地からこのクリーチャーの上に置いてもよい）
- dm25rp2-sp3 魔光神官ルドルフ・アルカディア（出た時、山札の
  上から4枚を墓地に置いてもよい。その後、このクリーチャー
  から進化できるコスト8以下のクリーチャーを1体、自分の
  墓地からこのクリーチャーの上に置いてもよい）
- dm25ex1-069 神滅翔天ポッポ・ジュヴィラ（自分の墓地にある
  クリーチャーの上に重ねつつ出してもよい）

- 069 はドリフト: 第36弾の墓地進化（grave_evo: true＋
  evolve_zone: graveyard＋evolve_from）がそのまま使える。
  進化元に文明の制限は無いので evolve_from は
  {types: [creature]}。
- 018／sp3 は新フィルタ evolves_from（エンジン拡張）:
  evo_source_of（第177弾）の鏡像で、候補自身の evolve_from の
  いずれかに参照カードが合うものを拾う。defs.py の
  FILTER_KEYS＋検証、selectors.py の filter_match、
  schema.py（FILTER_KEYS から生成）の3点。重ね出し自体は
  第173弾の choose＋move {stack_evo: true,
  evo_source: {ref: self}} の確立形。

proto: T1021（スベルニル型）/ T1022（ルドルフ型）/
T1023（ジュヴィラ型）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
scenario.build を直接包む（第319弾以降の作法）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

MOVE_STACK = {"op": "move", "select": {"ref": "p", "count": "all"},
              "to": "bz", "reason": "put", "stack_evo": True,
              "evo_source": {"ref": "self"}}

FORM_018 = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "may", "body": [
        {"op": "choose",
         "select": {"zone": "graveyard", "owner": "you",
                    "filter": {"types": ["creature"], "cost_le": 5,
                               "any_of": [{"neo": True},
                                          {"evolution": True}],
                               "evolves_from": "self"},
                    "count": 1},
         "as": "p"},
        MOVE_STACK]}],
}]

FORM_SP3 = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [
        {"op": "may", "body": [
            {"op": "move",
             "select": {"zone": "deck", "owner": "you", "from_top": 4},
             "to": "graveyard", "reason": "put"}]},
        {"op": "may", "body": [
            {"op": "choose",
             "select": {"zone": "graveyard", "owner": "you",
                        "filter": {"types": ["creature"], "cost_le": 8,
                                   "evolves_from": "self"},
                        "count": 1},
             "as": "p"},
            MOVE_STACK]}],
}]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    c = proto_card("T1021")
    assert c["abilities"] == FORM_018
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = proto_card("T1022")
    assert c["abilities"] == FORM_SP3
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = proto_card("T1023")
    assert c.get("grave_evo") is True
    assert c.get("evolve_zone") == "graveyard"
    assert c.get("evolve_from") == {"types": ["creature"]}
    d = parse_card(c, TABLES)
    assert d.grave_evo is True


def _build(rules, p0, p1=None):
    return scenario.build(rules, {"p0": p0, "p1": p1 or {},
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _defn_in_key(key, defns):
    for dn in defns:
        if f":{dn}:" in key or key.endswith(f":{dn}"):
            return dn
    return None


def _zone_defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _play_and_stack(e, play_key, want_defns, pick_defn):
    """play_key をプレイし、出た時の may を受け入れ、choose の
    選択肢（want_defns と一致するはず）から pick_defn を選ぶ。
    choose の選択肢に現れた defn の集合を返す。"""
    played = False
    seen = None
    yes_count = 0
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if played and seen is not None and d["kind"] == "attack" \
                and d.get("player") == 0:
            return seen
        if d["kind"] == "main" and d.get("player") == 0 and not played \
                and play_key in keys:
            e.answer([keys.index(play_key)])
            played = True
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "charge" and not played:
            e.answer([keys.index("pass")] if "pass" in keys else [0])
            continue
        if d["kind"] == "yes_no":
            yes_count += 1
            e.answer([keys.index("yes")])
            continue
        if d["kind"] == "choose_cards" and seen is None:
            seen = {dn for k in keys
                    for dn in [ _defn_in_key(k, want_defns + [pick_defn]) ]
                    if dn}
            idx = next(i for i, k in enumerate(keys)
                       if _defn_in_key(k, [pick_defn]) == pick_defn)
            e.answer([idx])
            continue
        if d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("play/stack did not resolve")


def _stacked_on(e, top_defn, base_defn, p=0):
    top = next(c for c in e.bz_tops(p) if e.s.cards[c].defn == top_defn)
    base = e.s.cards[top].under
    return base and e.s.cards[base[0]].defn == base_defn


def test_t1021_stacks_neo_or_evolution_from_graveyard(rules):
    e = _build(rules, {"hand": ["T1021"],
                       "mana": ["T053", "T001", "T001", "T001"],
                       "graveyard": ["T057", "T087", "T017", "T001"]})
    seen = _play_and_stack(e, "play:T1021",
                           ["T057", "T087", "T017", "T001"], "T057")
    # 進化元になれるのは T057（NEO・闇から進化）と
    # T087（進化・クリーチャーから進化）だけ
    assert seen == {"T057", "T087"}, seen
    assert _stacked_on(e, "T057", "T1021")
    assert _zone_defns(e, "graveyard", 0) == ["T087", "T017", "T001"]


def test_t1022_mills_four_then_stacks(rules):
    e = _build(rules, {"hand": ["T1022"],
                       "mana": ["T004", "T053", "T001", "T001", "T001"],
                       "graveyard": ["T057", "T394", "T017"]})
    seen = _play_and_stack(e, "play:T1022",
                           ["T057", "T394", "T017"], "T394")
    assert seen == {"T057", "T394"}, seen
    assert _stacked_on(e, "T394", "T1022")
    # 墓地は 3（元）＋4（切削）－1（重ね出し）＝6枚
    assert len(e.zlist("graveyard", 0)) == 6


def test_t1023_grave_evo_option(rules):
    e = _build(rules, {"hand": ["T1023"],
                       "mana": ["T053", "T005", "T001", "T001"],
                       "graveyard": ["T001"]})
    played = False
    seen_main = None
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if played and e.bz_tops(0):
            break
        if d["kind"] == "main" and d.get("player") == 0 and not played:
            seen_main = keys
            assert "play:T1023" in keys          # 通常召喚もできる
            assert "play:T1023:gevo" in keys     # 墓地進化の選択肢
            e.answer([keys.index("play:T1023:gevo")])
            played = True
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "charge" and not played:
            e.answer([keys.index("pass")] if "pass" in keys else [0])
            continue
        if any(_defn_in_key(k, ["T001"]) for k in keys) \
                and d["kind"] not in ("main", "charge"):
            idx = next(i for i, k in enumerate(keys)
                       if _defn_in_key(k, ["T001"]) == "T001")
            e.answer([idx])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert seen_main is not None
    assert _stacked_on(e, "T1023", "T001")
    assert _zone_defns(e, "graveyard", 0) == []
