"""語彙パイロット第265弾: 究極進化MAX（ultimate_evolution_max）。

新フィルタキー ultimate_evolution: true|false を追加する。対象カードの
fdef の evolve_from（単一フィルタまたは進化Vのリスト）のいずれかが
「進化クリーチャーを要求する」（types に evolution を含む）場合に真。
公式裁定では「究極進化クリーチャー」は能力（自身の進化条件）で決まり、
バトルゾーンへの出方は問わないため、def レベルの判定とした。
用法: evolve_from: {ultimate_evolution: true}（NEX 4枚の進化条件）。
_evo_sources → _evo_match → filter_match の経路でそのまま働く。
"""
import pytest
from tests.conftest import setup

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card

TABLES = load_tables()


def _defns(e, zone, p):
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _by_defn(e, zone, p):
    return {e.cdef(c).id: c for c in e.zlist(zone, p)}


def _drive(e, stop, choose=None, play=None, limit=800):
    """汎用ドライバ（第264弾のものを流用）。"""
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
        if kind == "attack":
            if "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
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


def _play(defn, seen, max_n=1):
    """main で defn を max_n 回まで出す play フック。"""
    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if f"play:{defn}" in keys and seen["n"] < max_n:
            seen["n"] += 1
            return [keys.index(f"play:{defn}")]
        return None
    return play


def _play_msum(defn, seen):
    """main で defn の :msum 選択肢を出す play フック。"""
    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        hit = [i for i, k in enumerate(keys) if defn in k and "msum" in k]
        if hit and not seen.get("opt"):
            seen["opt"] = True
            return [hit[0]]
        return None
    return play


def _pick_defn(defn):
    """choose_cards で defn のカードを1枚選ぶ。"""
    def choose(e, d):
        idx = [i for i, o in enumerate(d["options"])
               if e.s.cards[o["cid"]].defn == defn]
        assert idx, f"選択対象の {defn} が候補に無い"
        return idx[:1]
    return choose


# ---------- parse / validation ----------

def test_pilot265_protos_parse():
    rules = load_rules()
    assert rules.cards["T729"].evolve_from == {"ultimate_evolution": True}
    assert rules.cards["T730"].evolve_from == {"ultimate_evolution": True}
    assert "summon_from_mana" in rules.cards["T730"].keywords
    assert isinstance(rules.cards["T731"].evolve_from, list)
    assert rules.cards["T731"].evolve_from[0] == {"types": ["evolution"]}
    assert rules.cards["T733"].spell[0]["select"]["filter"] == {"ultimate_evolution": True}
    base = {"id": "TX", "name": "x", "types": ["creature", "evolution"], "civs": ["fire"],
            "cost": 7, "power": 9000, "races": ["テスト"],
            "evolve_from": {"ultimate_evolution": True}}
    parse_card(dict(base), TABLES)
    with pytest.raises(DefError):
        bad = dict(base, evolve_from={"ultimate_evolution": "yes"})
        parse_card(bad, TABLES)
    with pytest.raises(DefError):
        bad = dict(base, evolve_from={"ultimate_evolution": 1})
        parse_card(bad, TABLES)


# ---------- filter_match ----------

def test_filter_match_ultimate_evolution(rules):
    """究極進化クリーチャー（T094）だけが true。普通の進化（T087）・非進化（T001）は false。"""
    e = setup(rules, {"bz": ["T094", "T087", "T001"]}, {})
    by = _by_defn(e, "bz", 0)
    assert e.filter_match(by["T094"], {"ultimate_evolution": True})
    assert not e.filter_match(by["T087"], {"ultimate_evolution": True})
    assert not e.filter_match(by["T001"], {"ultimate_evolution": True})
    assert not e.filter_match(by["T094"], {"ultimate_evolution": False})
    assert e.filter_match(by["T087"], {"ultimate_evolution": False})
    assert e.filter_match(by["T001"], {"ultimate_evolution": False})


def test_evolution_v_ultimate_forms(rules):
    """進化V: 片方の分岐が究極進化を要求すれば究極進化クリーチャー（T731）。無ければ false（T732）。"""
    e = setup(rules, {"hand": ["T731", "T732"]}, {})
    by = _by_defn(e, "hand", 0)
    assert e.filter_match(by["T731"], {"ultimate_evolution": True})
    assert not e.filter_match(by["T732"], {"ultimate_evolution": True})
    assert e.filter_match(by["T732"], {"ultimate_evolution": False})


def test_evo_sources_only_ultimate(rules):
    """T729 の進化元候補は究極進化クリーチャー（T094）だけで、普通の進化（T087）・非進化（T001）は入らない。"""
    e = setup(rules, {"bz": ["T094", "T087", "T001"], "hand": ["T729"], "mana": ["T005"] * 7}, {})
    t729 = _by_defn(e, "hand", 0)["T729"]
    t094 = _by_defn(e, "bz", 0)["T094"]
    assert e._evo_sources(t729, 0) == [t094]


# ---------- play ----------

def test_max_evolves_on_ultimate(rules):
    """究極進化MAX: 究極進化クリーチャー（T094）の上に重ねて出せる。重なった下に T094 が残る。"""
    e = setup(rules, {"bz": ["T094"], "hand": ["T729"], "mana": ["T005"] * 7}, {})
    seen = {"n": 0}
    _drive(e, lambda e: "T729" in _defns(e, "bz", 0), play=_play("T729", seen))
    assert seen["n"] == 1
    by = _by_defn(e, "bz", 0)
    t729, t094 = by["T729"], by["T094"]
    assert t094 in e.s.cards[t729].under
    assert e.s.cards[t094].top_of == t729


def test_max_cannot_evolve_on_plain_evolution(rules):
    """究極進化MAX: 普通の進化クリーチャー（T087）の上には出せない（play 選択肢が出ない）。
    出せるカードが無い時は main ステップ自体が決定を出さないため、_play_options で直接見る。"""
    e = setup(rules, {"bz": ["T087"], "hand": ["T729"], "mana": ["T005"] * 7}, {})
    keys = [o["key"] for o in e._play_options(0)]
    assert "play:T729" not in keys


def test_max_cannot_evolve_on_non_evolution(rules):
    """究極進化MAX: 非進化クリーチャー（T001）の上には出せない（play 選択肢が出ない）。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T729"], "mana": ["T005"] * 7}, {})
    keys = [o["key"] for o in e._play_options(0)]
    assert "play:T729" not in keys


def test_max_from_mana(rules):
    """dm26sd1-y004 の組合せ: マナゾーンから究極進化MAXで出せる（:msum 選択肢）。"""
    e = setup(rules, {"bz": ["T094"], "mana": ["T730", "T001", "T001", "T001", "T001", "T001"]}, {})
    seen = {}
    _drive(e, lambda e: "T730" in _defns(e, "bz", 0), play=_play_msum("T730", seen))
    assert seen.get("opt")
    by = _by_defn(e, "bz", 0)
    t730, t094 = by["T730"], by["T094"]
    assert t094 in e.s.cards[t730].under
    assert e.s.cards[t094].top_of == t730


# ---------- select filter ----------

def test_ultimate_evolution_select_filter(rules):
    """select フィルタでも使える: 究極選別呪文の破壊対象は究極進化クリーチャー（T094）だけ。"""
    e = setup(rules, {"bz": ["T094", "T087"], "hand": ["T733"], "mana": ["T003", "T003"]}, {})
    h0 = len(e.zlist("hand", 0))
    seen = {"n": 0, "opts": None}

    def choose(e, d):
        seen["opts"] = [e.s.cards[o["cid"]].defn for o in d["options"]]
        return _pick_defn("T094")(e, d)

    _drive(e, lambda e: "T094" in _defns(e, "graveyard", 0),
           choose=choose, play=_play("T733", seen))
    assert seen["opts"] == ["T094"]
    assert "T087" in _defns(e, "bz", 0)
    assert len(e.zlist("hand", 0)) == h0  # 呪文 -1 + ドロー +1
