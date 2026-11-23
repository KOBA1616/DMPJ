"""再変換ラウンド359（第324弾 breaks_equal_creature_count）の記録テスト。

- 新規登録1件: dm26ex4-cho021 ジョジョジョ・マキシマム。
- alias 畳み込み1件: dm24ex2-024（旧印刷。canon_id は dm26ex4-cho021
  で、reopen で行を外し、cho021 の登録時に validate の aliases_for
  が source.aliases = [dm24ex2-024, dmex19-002, dmrp04m-001] を
  自動付与した。dm24ex2-024 は converted の独立エントリではなく
  alias として引け、reject 行も残らない）。
  stale クリーンアップ0件・差し戻し0件。
- 対象2行は gaps = [breaks_equal_creature_count] のため reopen
  で外してから submit（reopen は dm24ex2-024 の1件だけが外れた。
  dm26ex4-cho021 の rejects 行には reason が無く reopen の条件に
  合わなかったためで、submit で rejects から外れた）。
- converted 10,270→10,271 / rejects 2,047→2,045、
  canonical 重なり0・漏れ0。breaks_equal_creature_count は
  ファミリーがこの2行だけだったため完全に解消。

登録形は第324弾の確立形と完全一致（submit の連結・merge_split 由来の
混入なし）:
- dm26ex4-cho021: free_if {cmp: [{count: {zone: [bz, mana], owner: you,
  filter: {race_has: ジョーカーズ}}}, '>=', 11]} +
  [set_var n {count: {zone: bz, owner: you, filter: {types: [creature]}}};
  choose {zone: bz, owner: you, filter: {types: [creature]}, count: 1}
  as chosen; modify {ref: chosen} {breaks_add: {var: n}} end_of_turn;
  delayed_trigger {event: attack, subject: {ref: chosen}} ->
  [modify {zone: hand, owner: opp, filter: {types: [spell]}}
  {deny: [cast]} during_attack] end_of_turn, once: false]

実挙動は登録カード自身で固定する。ドライバは scenario.build の薄い包みで、
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

GAP = "breaks_equal_creature_count"
CID = "dm26ex4-cho021"

FREE_IF = {
    "cmp": [{"count": {"zone": ["bz", "mana"], "owner": "you",
                       "filter": {"race_has": "ジョーカーズ"}}},
            ">=", 11]}

SPELL = [
    {"op": "set_var", "name": "n",
     "value": {"count": {"zone": "bz", "owner": "you",
                         "filter": {"types": ["creature"]}}}},
    {"op": "choose",
     "select": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}, "count": 1},
     "as": "chosen"},
    {"op": "modify", "select": {"ref": "chosen"},
     "mod": {"breaks_add": {"var": "n"}}, "duration": "end_of_turn"},
    {"op": "delayed_trigger",
     "when": {"event": "attack", "subject": {"ref": "chosen"}},
     "effect": [{"op": "modify",
                 "select": {"zone": "hand", "owner": "opp",
                            "filter": {"types": ["spell"]}},
                 "mod": {"deny": ["cast"]},
                 "duration": "during_attack"}],
     "duration": "end_of_turn", "once": False},
]


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


def test_round359_disposition():
    rej = _reject_rows()
    assert len(rej) == 2045
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10271
    assert not (ids & set(rej))          # canonical 重なり0
    assert CID in ids and CID not in rej
    assert "dm24ex2-024" not in ids and "dm24ex2-024" not in rej
    c = _conv_cache.find(CONVERTED, CID)
    assert c is not None
    assert c["free_if"] == FREE_IF
    assert c["spell"] == SPELL
    assert (c.get("source") or {}).get("aliases") == [
        "dm24ex2-024", "dmex19-002", "dmrp04m-001"]
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d.free_if is not None
    assert len(d.spell) == 4
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
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


def _main_keys(e, max_steps=30):
    """次の main 決定（player 0）の選択肢を返す。"""
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended before main"
        if d["kind"] == "main" and d.get("player") == 0:
            return _keys(d)
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys
                 else list(range(d["min"])))
    raise AssertionError("main decision did not appear")


def _cast_spell(e, choose_key="bz:T001:"):
    """main で登録呪文を唱え、クリーチャーを1体選ぶ。pay_mana・
    choose_cards に汎用的に答える。"""
    cast = False
    for _ in range(120):
        d = e.advance()
        assert d is not None, "game ended before cast"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and not cast \
                and f"play:{CID}" in keys:
            e.answer([keys.index(f"play:{CID}")])
            cast = True
            continue
        if cast and d["kind"] == "choose_cards" \
                and any(k.startswith("bz:") for k in keys):
            hit = [i for i, k in enumerate(keys)
                   if k.startswith(choose_key)]
            assert hit, keys
            e.answer([hit[0]])
            return
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("spell did not resolve")


def _attack_player(e, attacker_defn):
    for _ in range(30):
        d = e.advance()
        assert d is not None, "game ended before attack"
        if d["kind"] == "attack":
            keys = _keys(d)
            e.answer([keys.index(f"attack:{attacker_defn}:player")])
            return
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys
                 else list(range(d["min"])))
    raise AssertionError("attack decision did not appear")


def _drive_combat(e, probe=None, max_steps=200):
    """攻撃の解決が終わるまで進める。probe(cid) が与えられれば、
    攻撃中の各決定でそのカードの cast 可否を記録する。"""
    probes = []
    for _ in range(max_steps):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main", "attack"):
            return probes
        if probe is not None:
            probes.append(e.permits(probe, "cast"))
        keys = _keys(d)
        if d["kind"] == "block":
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("combat did not settle")


def test_registered_free_if_with_eleven_jokers(rules):
    """登録形: G・ゼロでジョーカーズ11枚なら無料で唱えられる
    （マナはタップされない）。"""
    e = _build(rules, {"hand": [CID], "mana": ["T408"] * 11}, {})
    keys = _main_keys(e)
    assert f"play:{CID}:free" in keys
    e.answer([keys.index(f"play:{CID}:free")])
    for _ in range(60):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main", "attack"):
            break
        keys = _keys(d)
        if d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert all(not e.s.cards[c].tapped for c in e.zlist("mana", 0))


def test_registered_grants_breaks_equal_creature_count(rules):
    """登録形: 自分のクリーチャーが3体いれば、選んだ1体は余分に3枚割る
    （通常1枚＋3枚＝4枚）。"""
    e = _build(rules, {"bz": ["T001", "T002", "T004"],
                       "hand": [CID], "mana": ["T030"] * 9}, {})
    for dfn in ("T001", "T002", "T004"):
        e.s.cards[_bz(e, 0, dfn)].entered_turn = -1
    _cast_spell(e)
    before = len(e.zlist("shield", 1))
    _attack_player(e, "T001")
    _drive_combat(e)
    assert len(e.zlist("shield", 1)) == before - 4


def test_registered_denies_cast_during_chosen_attack(rules):
    """登録形: 選んだクリーチャーの攻撃中、相手は呪文を唱えられない。
    攻撃が終われば唱えられるようになる。"""
    e = _build(rules, {"bz": ["T001", "T002"],
                       "hand": [CID], "mana": ["T030"] * 9},
               {"hand": ["T006"]})
    for dfn in ("T001", "T002"):
        e.s.cards[_bz(e, 0, dfn)].entered_turn = -1
    t006 = next(c for c in e.zlist("hand", 1)
                if e.s.cards[c].defn == "T006")
    assert e.permits(t006, "cast")
    _cast_spell(e)
    _attack_player(e, "T001")
    probes = _drive_combat(e, probe=t006)
    assert probes and not all(probes), probes
    assert e.permits(t006, "cast")
