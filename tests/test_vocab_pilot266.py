"""語彙パイロット第266弾: exile_doron_go（ウルトラ・ドロン・ゴー）。

エグザイル・クリーチャーを表す型印 `exile_creature` を defs の CARD_TYPES
に追加する（第174弾の dream_creature と同型）。types には通常
`["creature", "exile_creature"]` と書く。フィルタ `{types: [exile_creature]}`
は selectors の汎用の集合照合でそのまま働くため、エンジン変更なし。
従来は `types: [exile_creature]` をフィルタに書いた変換済みカードが10箇所
あったが、どのカードの types にもその印が無く、照合は常に偽だった。
今回、変換済みのエグザイル・クリーチャー28枚の types に印を付け、
その10箇所のフィルタが初めて生きる。

ウルトラ・ドロン・ゴーの型（ドロン・ゴーとの差は誘発条件だけ）:
- 誘発 `{event: move, from: bz, subject: self}`（行き先を問わない「離れた時」。
  dm22ex1-055 の「離れた時」と同型）。効果は may [move {select: {zone: hand,
  filter: {types: [exile_creature], name_has?}}, count: 1, to: bz, reason: put}]。
- 出場制限は常在型5つ（hand / graveyard / mana / deck / shield の各ゾーン。
  dmd11-005 のドロン・ゴーと同型）で、filter は
  `{types: [exile_creature], name_has: <名>}`、mod は `{deny: [enter_bz]}`。
- チーム・エグザイルの無視能力（dm22ex1-cho22）は、制限側の常在型の `if` で
  表す: `{not: {exists: {zone: [hand, bz], owner: you,
  filter: {name_has: チーム・エグザイル}}}}`。常在型はバトルゾーンの発生源
  からしか働かず、手札にある時の無視を cho22 自身の能力では表せないため。
  「チーム・エグザイル」を名前に含むカードは原文コーパスに cho22 だけ。
"""
import pytest
from tests.conftest import setup

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card

TABLES = load_tables()

IGNORE_IF = {"not": {"exists": {"zone": ["hand", "bz"], "owner": "you",
                                "filter": {"name_has": "チーム・エグザイル"}}}}


def _defns(e, zone, p):
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _by_defn(e, zone, p):
    return {e.cdef(c).id: c for c in e.zlist(zone, p)}


def _drive(e, stop, choose=None, play=None, yes_no=None, limit=800):
    """汎用ドライバ（第265弾のものを流用し、yes_no フックを追加）。"""
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
        if kind == "yes_no" and yes_no is not None:
            ans = yes_no(e, d)
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


def _play_key(key, seen):
    """main で指定の play キー（ツインパクトの面つき等）を1回出す play フック。"""
    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and not seen.get("opt"):
            seen["opt"] = True
            return [keys.index(key)]
        return None
    return play


def _pick_either(*defns):
    """choose_cards で defns のいずれかが候補にあれば1枚選ぶ。"""
    def choose(e, d):
        for dn in defns:
            idx = [i for i, o in enumerate(d["options"])
                   if e.s.cards[o["cid"]].defn == dn]
            if idx:
                return idx[:1]
        return None
    return choose


# ---------- parse / validation ----------

def test_pilot266_protos_parse():
    rules = load_rules()
    t734 = rules.cards["T734"]
    assert t734.types == ["creature", "exile_creature"]
    assert rules.cards["T735"].types == ["creature", "exile_creature"]
    assert rules.cards["T736"].types == ["creature", "exile_creature"]
    assert rules.cards["T737"].types == ["creature"]
    assert len(t734.abilities) == 6
    trig = t734.abilities[0]
    assert trig["kind"] == "trigger"
    assert trig["when"] == {"event": "move", "from": "bz", "subject": "self"}
    assert trig["effect"][0]["op"] == "may"
    move = trig["effect"][0]["body"][0]
    assert move["op"] == "move" and move["to"] == "bz" and move["reason"] == "put"
    assert move["select"]["filter"] == {"types": ["exile_creature"], "name_has": "試験神"}
    statics = [ab for ab in t734.abilities if ab["kind"] == "static"]
    assert len(statics) == 5
    assert sorted(ab["affects"]["zone"] for ab in statics) == [
        "deck", "graveyard", "hand", "mana", "shield"]
    for ab in statics:
        assert ab["mod"] == {"deny": ["enter_bz"]}
        assert ab["affects"]["filter"] == {"types": ["exile_creature"], "name_has": "試験神"}
        assert ab["if"] == IGNORE_IF
    base = {"id": "TX", "name": "x", "types": ["creature", "exile_creature"],
            "civs": ["fire"], "cost": 3, "power": 1000, "races": ["テスト"]}
    parse_card(dict(base), TABLES)
    with pytest.raises(DefError):
        parse_card(dict(base, types=["creature", "no_such_type"]), TABLES)


# ---------- filter_match ----------

def test_filter_match_exile_creature(rules):
    """エグザイル印のある T734/T735/T736 だけが {types: [exile_creature]} に合う。"""
    e = setup(rules, {"bz": ["T734", "T735", "T736", "T737", "T001"]}, {})
    by = _by_defn(e, "bz", 0)
    for dn in ("T734", "T735", "T736"):
        assert e.filter_match(by[dn], {"types": ["exile_creature"]})
        assert e.filter_match(by[dn], {"types": ["creature"]})
        assert not e.filter_match(by[dn], {"not_types": ["exile_creature"]})
    for dn in ("T737", "T001"):
        assert not e.filter_match(by[dn], {"types": ["exile_creature"]})
        assert e.filter_match(by[dn], {"not_types": ["exile_creature"]})


# ---------- ultra trigger ----------

def test_ultra_trigger_on_destroy(rules):
    """破壊で離れた時：may に「はい」で T735 が手札から出る。T734 は墓地へ。"""
    e = setup(rules, {"bz": ["T734"], "hand": ["T011", "T735"],
                      "mana": ["T005"] * 3}, {})
    seen = {"n": 0}
    _drive(e, lambda e: "T735" in _defns(e, "bz", 0),
           choose=_pick_either("T734", "T735"), play=_play("T011", seen))
    assert seen["n"] == 1
    assert "T734" in _defns(e, "graveyard", 0)
    assert "T735" not in _defns(e, "hand", 0)


def test_ultra_trigger_on_bounce(rules):
    """手札に戻って離れた時も誘発する：相手の T018 で戻し、may で T735 が出る。"""
    e = setup(rules, {"bz": ["T734"], "hand": ["T735"]},
              {"hand": ["T018"], "mana": ["T003", "T003"]})
    seen = {}
    # 手札に戻った T734 自身も名前に《試験神》とあるエグザイルなので出し先の候補に
    # 入る。T735 を優先して選ぶ。
    _drive(e, lambda e: "T735" in _defns(e, "bz", 0),
           choose=_pick_either("T735", "T734"), play=_play_key("play:T018:1", seen))
    assert seen.get("opt")
    assert "T734" in _defns(e, "hand", 0)
    assert "T735" not in _defns(e, "hand", 0)


def test_trigger_play_blocked_by_other_restriction(rules):
    """同じ制限を持つ別の T734 が場に残る時、誘発の出し先は出せないまま。
    出し先の選択は候補が1枚だけなので自動回答され、移動自体が permits で止まる。"""
    e = setup(rules, {"bz": ["T734", "T734"], "hand": ["T011", "T735"],
                      "mana": ["T005"] * 3}, {})
    seen = {"n": 0, "may": False}

    def yes_no(e, d):
        seen["may"] = True
        return [0]

    _drive(e, lambda e: seen["may"] and "T734" in _defns(e, "graveyard", 0),
           choose=_pick_either("T734"), play=_play("T011", seen), yes_no=yes_no)
    assert seen["n"] == 1 and seen["may"]
    assert "T735" in _defns(e, "hand", 0)
    assert _defns(e, "bz", 0).count("T734") == 1
    assert _defns(e, "graveyard", 0).count("T734") == 1


# ---------- restriction ----------

def _play_keys(e, p=0):
    return [o["key"] for o in e._play_options(p)]


def test_restriction_blocks_summon(rules):
    """T734 が場にいる間、名前に《試験神》とある T735 は召喚できない。
    名前の違うエグザイル（T739）・非エグザイル（T737）は出せる。
    （T736 は無視能力の持ち主なので、このテストの手札には入れない）"""
    e = setup(rules, {"bz": ["T734"], "hand": ["T735", "T739", "T737"],
                      "mana": ["T005"] * 3}, {})
    keys = _play_keys(e)
    assert "play:T735" not in keys
    assert "play:T739" in keys
    assert "play:T737" in keys


def test_restriction_lifts_after_leave(rules):
    """T734 が離れた後（誘発の may を断った場合）は T735 を召喚できる。"""
    e = setup(rules, {"bz": ["T734"], "hand": ["T011", "T735"],
                      "mana": ["T005"] * 6}, {})
    seen = {"n": 0, "m": 0, "declined": False}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if "play:T011" in keys and seen["n"] < 1:
            seen["n"] += 1
            return [keys.index("play:T011")]
        if "play:T735" in keys and seen["declined"]:
            seen["m"] += 1
            return [keys.index("play:T735")]
        return None

    def yes_no(e, d):
        if not seen["declined"]:
            seen["declined"] = True
            return [1]  # may を断る
        return [0]

    _drive(e, lambda e: "T735" in _defns(e, "bz", 0),
           choose=_pick_either("T734"), play=play, yes_no=yes_no)
    assert seen["n"] == 1 and seen["declined"] and seen["m"] == 1
    assert "T734" in _defns(e, "graveyard", 0)


def test_ignore_from_hand(rules):
    """無視能力の持ち主（T736）が手札にある時、制限は働かない。"""
    e = setup(rules, {"bz": ["T734"], "hand": ["T735", "T736"],
                      "mana": ["T005"] * 3 + ["T004"] * 2}, {})
    assert "play:T735" in _play_keys(e)


def test_ignore_from_bz(rules):
    """無視能力の持ち主（T736）がバトルゾーンにある時も、制限は働かない。"""
    e = setup(rules, {"bz": ["T734", "T736"], "hand": ["T735"],
                      "mana": ["T005"] * 3}, {})
    assert "play:T735" in _play_keys(e)


# ---------- select filter ----------

def test_exile_select_filter_spell(rules):
    """T738 の破壊対象はエグザイル（T735）だけで、非エグザイル（T001）は出ない。"""
    e = setup(rules, {"bz": ["T735", "T001"], "hand": ["T738"],
                      "mana": ["T003", "T003"]}, {})
    h0 = len(e.zlist("hand", 0))
    seen = {"n": 0, "opts": None}

    def choose(e, d):
        seen["opts"] = [e.s.cards[o["cid"]].defn for o in d["options"]]
        return _pick_either("T735")(e, d)

    _drive(e, lambda e: "T735" in _defns(e, "graveyard", 0),
           choose=choose, play=_play("T738", seen))
    assert seen["opts"] == ["T735"]
    assert "T001" in _defns(e, "bz", 0)
    assert len(e.zlist("hand", 0)) == h0  # 呪文 -1 + ドロー +1
