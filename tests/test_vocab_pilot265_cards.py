"""語彙パイロット第265弾のカード適用テスト（登録形）。

ラウンド300で ultimate_evolution_max の4件を新規登録、差し戻しなし。
- 登録4件: dm26ex1-020（ロマノフカイザー・NEX。出た時・相手2体破壊＋
  マナ2枚墓地／離れた時・山札サーチ any_of）、dm26ex1-039（ギャラクシー・
  デスティニー。攻撃時・山札からクリーチャー2体まで出す）、
  dm26sd1-y004（ギュンター・ペガサス。マナ召喚＋攻撃時・山札上3枚まで
  マナ＋マナから好きな数出す no_trigger）、dm35-002（ギャラクシー・
  オペレーションθ。攻撃時・山札から呪文1枚を無料唱え／離れた時・墓地の
  呪文すべて手札）。
- 35-sec001 は dm26ex1-020 の同名別版として aliases に折り畳まれ、
  rejects には alias-level stale 行として残る（gaps は究極進化MAX＋
  selector_filter_or のまま。OR は any_of で表せた）。
- converted 10,090 / rejects 2,247、重複0・漏れ0。
"""
import copy
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card
from dmsim.scenario import build

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"


def _setup(rules, p0, p1=None):
    # tests.conftest の setup と同形。conftest を import すると
    # DMSIM_SKIP_CONVERTED=1 が復活するため、ここで直接 build を呼ぶ。
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": "T001",
                         "seed": 1, "deck_size": 20})


REGISTERED = ("dm26ex1-020", "dm26ex1-039", "dm26sd1-y004", "dm35-002")


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _reject(cid):
    for line in open(REJECTS, encoding="utf-8"):
        r = json.loads(line)
        if r["id"] == cid:
            return r
    raise KeyError(cid)


def _triggers(card, event=None):
    return [ab for ab in card.get("abilities") or []
            if ab.get("kind") == "trigger"
            and (event is None or ab["when"].get("event") == event)]


def _drive(e, stop, choose=None, play=None, attack_with=None, attacker=0,
           limit=800):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "choose_evo_source":
            e.answer([0])
            if stop(e):
                return
            continue
        if kind == "choose_cards" and choose is not None:
            ans = choose(e, d)
            if ans is not None:
                e.answer(ans)
                if stop(e):
                    return
                continue
        if kind == "main" and play is not None:
            ans = play(e, d)
            if ans is not None:
                e.answer(ans)
                if stop(e):
                    return
                continue
        if kind == "attack" and attack_with is not None \
                and e.s.active == attacker:
            hit = next((i for i, k in enumerate(keys)
                        if k.startswith(f"attack:{attack_with}:")), None)
            if hit is not None:
                e.answer([hit])
                if stop(e):
                    return
                continue
        if kind == "block":
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "pay_mana":
            e.answer([0])
        elif kind == "yes_no":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if stop(e):
            return
    raise AssertionError("limit reached")


def _in_zone(e, zone, p, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def _count_zone(e, zone, p, defn):
    return sum(1 for c in e.zlist(zone, p)
               if e.s.cards[c].defn == defn)


def _play(defn, seen, max_n=1, player=0):
    def play(e, d):
        if e.s.active != player:
            return None
        keys = [o["key"] for o in d["options"]]
        if f"play:{defn}" in keys and seen["n"] < max_n:
            seen["n"] += 1
            return [keys.index(f"play:{defn}")]
        return None
    return play


def _pick_defn(defn, max_n=None):
    """choose_cards で defn のカードを選ぶ（最大 max_n 枚、既定は決定の max）。"""
    def choose(e, d):
        idx = [i for i, o in enumerate(d["options"])
               if e.s.cards[o["cid"]].defn == defn]
        assert idx, f"選択対象の {defn} が候補に無い"
        n = max_n if max_n is not None else d.get("max", len(idx))
        return idx[:n]
    return choose


def test_registered_forms():
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        assert (card.get("source") or {}).get("official") == cid
        assert card["evolve_from"] == {"ultimate_evolution": True}


def test_round300_specific_forms():
    c = _converted("dm26ex1-020")
    assert c["keywords"] == ["world_breaker"]
    assert (c.get("source") or {}).get("aliases") == ["35-sec001", "dm35-s04"]
    trig = _triggers(c, "move")
    assert len(trig) == 2
    cip = trig[0]
    assert cip["when"] == {"event": "move", "to": "bz", "subject": "self"}
    assert cip["effect"][0] == {
        "op": "destroy",
        "select": {"zone": "bz", "owner": "opp",
                   "filter": {"types": ["creature"]}, "count": 2}}
    assert cip["effect"][1] == {
        "op": "move",
        "select": {"zone": "mana", "owner": "opp", "count": 2},
        "to": "graveyard", "reason": "put"}
    leave = trig[1]
    assert leave["when"] == {"event": "move", "from": "bz",
                             "subject": "self"}
    may = leave["effect"][0]
    assert may["op"] == "may"
    mv = may["body"][0]
    assert mv["op"] == "move" and mv["to"] == "bz"
    assert mv["select"]["filter"] == {
        "types": ["creature"],
        "any_of": [{"races": ["アーマード・ドラゴン"]},
                   {"name_has": "ロマノフ"}]}
    assert leave["effect"][1] == {"op": "shuffle"}

    c = _converted("dm26ex1-039")
    assert c["keywords"] == ["triple_breaker"]
    assert (c.get("source") or {}).get("aliases") == ["dm23ex2-026", "dm35-005"]
    atk = _triggers(c, "attack")
    assert len(atk) == 1
    assert atk[0]["when"] == {"event": "attack", "subject": "self"}
    may = atk[0]["effect"][0]
    assert may["op"] == "may"
    mv = may["body"][0]
    assert mv["select"]["filter"] == {"types": ["creature"]}
    assert mv["select"]["count"] == 2 and mv["select"]["up_to"] is True
    assert atk[0]["effect"][1] == {"op": "shuffle"}

    c = _converted("dm26sd1-y004")
    assert c["keywords"] == ["summon_from_mana", "triple_breaker"]
    assert (c.get("source") or {}).get("aliases") == ["dm23ex2-cho012",
                                                      "dmex16-076"]
    atk = _triggers(c, "attack")
    assert len(atk) == 1
    rep = atk[0]["effect"][0]
    assert rep["op"] == "repeat" and rep["times"] == 3
    mv = rep["body"][0]["body"][0]
    assert mv["select"]["from_top"] == 1 and mv["to"] == "mana"
    put = atk[0]["effect"][1]
    assert put["select"]["count"] == "any"
    assert put["to"] == "bz" and put["no_trigger"] is True

    c = _converted("dm35-002")
    assert c["keywords"] == ["triple_breaker"]
    assert (c.get("source") or {}).get("aliases") is None
    atk = _triggers(c, "attack")
    assert len(atk) == 1
    eff = atk[0]["effect"]
    assert eff[0]["op"] == "choose" and eff[0]["as"] == "sp"
    assert eff[0]["select"]["filter"] == {"types": ["spell"]}
    assert eff[1] == {"op": "shuffle"}
    assert eff[2]["op"] == "if"
    assert eff[2]["cond"] == {"exists": {"ref": "sp"}}
    assert eff[2]["then"][0]["body"][0] == {
        "op": "play_free", "select": {"ref": "sp"}}
    leave = _triggers(c, "move")
    assert len(leave) == 1
    assert leave[0]["effect"][0] == {
        "op": "move",
        "select": {"zone": "graveyard", "owner": "you",
                   "filter": {"types": ["spell"]}, "count": "all"},
        "to": "hand", "reason": "return"}


def test_35_sec001_alias_level_stale():
    """35-sec001 は dm26ex1-020 の aliases に折り畳まれ、rejects には
    alias-level stale 行として残る（既存の同種の行と同じ扱い）。"""
    c = _converted("dm26ex1-020")
    assert "35-sec001" in (c.get("source") or {}).get("aliases", [])
    r = _reject("35-sec001")
    assert r["gaps"] == ["ultimate_evolution_max", "selector_filter_or"]


def test_020_cip_destroys_and_mana_to_grave():
    """dm26ex1-020: 出た時、相手クリーチャー2体破壊＋相手マナ2枚を墓地へ。
    究極進化クリーチャー（T094）の上に究極進化MAXで出す。"""
    e = _setup(load_rules(),
               {"bz": ["T094"], "hand": ["dm26ex1-020"],
                "mana": ["T005"] * 7},
               {"bz": ["T001", "T001", "T001"],
                "mana": ["T001", "T001", "T001"]})
    seen = {"n": 0}
    _drive(e, lambda e: _count_zone(e, "graveyard", 1, "T001") == 4,
           choose=_pick_defn("T001", max_n=2),
           play=_play("dm26ex1-020", seen))
    assert seen["n"] == 1
    assert _in_zone(e, "bz", 0, "dm26ex1-020")
    assert _count_zone(e, "graveyard", 1, "T001") == 4


def test_020_leave_searches_by_name():
    """dm26ex1-020: 離れた時、山札から名前に《ロマノフ》とある
    クリーチャー（山札の2枚目）を出せる。T256 で破壊して誘発させる。"""
    e = _setup(load_rules(),
               {"bz": ["dm26ex1-020"], "deck": ["dm26ex1-020"]},
               {"hand": ["T256"], "mana": ["T008"] * 3})
    seen = {"n": 0}

    def choose(e, d):
        # T256 の破壊対象と離れた時のサーチは dm26ex1-020 を選ぶ。
        # 新しく出た dm26ex1-020 の出た時能力（相手マナ2枚を墓地へ）の
        # 選択は任意のマナ2枚でよい。
        idx = [i for i, o in enumerate(d["options"])
               if e.s.cards[o["cid"]].defn == "dm26ex1-020"]
        if idx:
            return idx[:1]
        return list(range(d.get("min", 0)))

    _drive(e, lambda e: _in_zone(e, "bz", 0, "dm26ex1-020")
           and _in_zone(e, "graveyard", 0, "dm26ex1-020"),
           choose=choose,
           play=_play("T256", seen, player=1))
    assert seen["n"] == 1
    assert _count_zone(e, "bz", 0, "dm26ex1-020") == 1
    assert _count_zone(e, "graveyard", 0, "dm26ex1-020") == 1


def test_039_attack_puts_two_from_deck():
    """dm26ex1-039: 攻撃時、山札からクリーチャーを2体まで出す。"""
    e = _setup(load_rules(), {"bz": ["dm26ex1-039"]}, {"bz": []})
    _drive(e, lambda e: _count_zone(e, "bz", 0, "T001") == 2,
           choose=_pick_defn("T001", max_n=2),
           attack_with="dm26ex1-039", attacker=0)
    assert _count_zone(e, "bz", 0, "T001") == 2


def test_y004_attack_mana_then_puts():
    """dm26sd1-y004: 攻撃時、山札の上から3枚までマナへ、その後マナの
    クリーチャーを好きな数出す（T001 1体＋T005 4体がバトルゾーンへ）。"""
    e = _setup(load_rules(),
               {"bz": ["dm26sd1-y004"], "mana": ["T001", "T005"],
                "deck": ["T005", "T005", "T005"]},
               {"bz": []})

    def choose_all(e, d):
        return list(range(len(d["options"])))

    _drive(e, lambda e: _count_zone(e, "bz", 0, "T001") == 1
           and _count_zone(e, "bz", 0, "T005") == 4,
           choose=choose_all,
           attack_with="dm26sd1-y004", attacker=0)
    assert _count_zone(e, "bz", 0, "T001") == 1
    assert _count_zone(e, "bz", 0, "T005") == 4
    assert len(e.zlist("mana", 0)) == 0


def test_002_attack_casts_spell_from_deck():
    """dm35-002: 攻撃時、山札から呪文1枚を選び、シャッフル後に無料で唱える。
    T003（知識の泉）が唱えられて墓地へ行き、手札が2枚増える。"""
    e = _setup(load_rules(),
               {"bz": ["dm35-002"], "deck": ["T003"]},
               {"bz": []})
    h0 = len(e.zlist("hand", 0))
    _drive(e, lambda e: _in_zone(e, "graveyard", 0, "T003"),
           choose=_pick_defn("T003", max_n=1),
           attack_with="dm35-002", attacker=0)
    assert _in_zone(e, "graveyard", 0, "T003")
    assert len(e.zlist("hand", 0)) == h0 + 2


def test_002_leave_returns_all_spells():
    """dm35-002: 離れた時、墓地の呪文をすべて手札に戻す（クリーチャーは
    墓地に残る）。T256 で破壊して誘発させる。"""
    e = _setup(load_rules(),
               {"bz": ["dm35-002"], "graveyard": ["T003", "T001"]},
               {"hand": ["T256"], "mana": ["T008"] * 3})
    seen = {"n": 0}
    _drive(e, lambda e: _in_zone(e, "hand", 0, "T003")
           and _in_zone(e, "graveyard", 0, "T001"),
           choose=_pick_defn("dm35-002", max_n=1),
           play=_play("T256", seen, player=1))
    assert seen["n"] == 1
    assert _in_zone(e, "hand", 0, "T003")
    assert _in_zone(e, "graveyard", 0, "T001")
