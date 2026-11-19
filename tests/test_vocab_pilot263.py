"""第263弾: 龍マナ武装（マナゾーンのドラゴン・クリーチャー数による条件）。

龍マナ武装 N は、自分のマナゾーンにあるドラゴン・クリーチャーが N 体以上ある時に
能力が働く条件。既存の式 {cmp: [{count: <セレクタ>}, ">=", N]} で表す（忍者の
マナ7枚条件と同型。フィルタに {types: [creature], race_has: ドラゴン} を付ける）。
本弾で足す語彙は次の3つ:
- cond {extra_turn: bool}: このターンが追加ターンか（「これが追加ターンでなければ」。
  GameState.extra_turn を h_turn が extra_turns からの開始時に立てる。Rust 同期込み）。
- セレクタ distinct_names: true: 「名前が異なる」選択（異なる名前の Jack-Pot を好きな数）。
  distinct_costs と同じ積み上げ分岐に乗る。
- 生成時ベイクの拡張: dynamic な modify の範囲フィルタに {cost_of: 変数} を書けるよう、
  _bake_refs が {cost_of / power_of / name_of / races_of} も生成時の値に焼く。
"""
import pytest
from tests.conftest import setup

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card

TABLES = load_tables()


def _defns(e, zone, p):
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _by_defn(e, zone, p):
    return {e.cdef(c).id: c for c in e.zlist(zone, p)}


def _in_zone(e, zone, p, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def _drive(e, stop, choose=None, play=None, attack_with=None, attacker=0, limit=800, note=None):
    """汎用ドライバ。choose/play は (e, d) -> answer|None のフック。"""
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if note is not None:
            note(e, d)
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
        if kind == "attack" and attack_with is not None and e.s.active == attacker:
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


# ---------- parse / validation ----------

def test_pilot263_protos_parse():
    rules = load_rules()
    assert rules.cards["T708"].abilities[0]["if"]["cmp"][1] == ">="
    assert rules.cards["T709"].abilities[0]["if"]["all"][1] == {"extra_turn": False}
    assert rules.cards["T712"].spell[0]["then"][0]["select"]["distinct_names"] is True
    assert rules.cards["T715"].abilities[0]["zone"] == "shield"
    assert rules.cards["T716"].abilities[0]["effect"][1]["then"][0]["dynamic"] is True


def test_distinct_names_and_extra_turn_validation():
    base = {"id": "test-263", "name": "試験", "types": ["creature"], "civs": ["fire"],
            "cost": 3, "power": 3000, "races": ["テスト"], "text": "",
            "source": {"official": "test-263", "review": "pending"}}

    def card(sel=None, cond=None):
        ab = {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
              "effect": [{"op": "move", "select": sel or {"zone": "graveyard", "owner": "you"},
                          "to": "hand", "reason": "return"}]}
        if cond is not None:
            ab["if"] = cond
        return dict(base, abilities=[ab])

    gy = {"zone": "graveyard", "owner": "you", "filter": {"types": ["creature"]}}
    with pytest.raises(DefError):   # count が無い
        parse_card(card(dict(gy, distinct_names=True)), TABLES)
    with pytest.raises(DefError):   # distinct_names は true のみ
        parse_card(card(dict(gy, count="any", distinct_names=False)), TABLES)
    with pytest.raises(DefError):   # count: all 単独は不可
        parse_card(card(dict(gy, count="all", distinct_names=True)), TABLES)
    parse_card(card(dict(gy, count="any", distinct_names=True)), TABLES)
    parse_card(card(dict(gy, count="all", up_to=True, distinct_names=True)), TABLES)
    with pytest.raises(DefError):   # extra_turn は bool のみ
        parse_card(card(cond={"extra_turn": 1}), TABLES)
    parse_card(card(cond={"extra_turn": True}), TABLES)
    parse_card(card(cond={"all": [{"extra_turn": False},
                                 {"cmp": [{"count": gy}, ">=", 2]}]}), TABLES)


# ---------- 龍マナ武装の数え上げ（T708） ----------

def test_mana_dragons_gate_attack_trigger():
    """マナにドラゴン2体あれば攻撃誘発が働き、相手クリーチャーを破壊する。"""
    e = setup(load_rules(), {"bz": ["T708"], "mana": ["T708", "T709"]},
              {"bz": ["T001"]})

    def choose(e, d):
        idx = [i for i, o in enumerate(d["options"])
               if e.s.cards[o["cid"]].defn == "T001"]
        assert idx, "破壊対象の T001 が候補に無い"
        return idx[:1]

    _drive(e, lambda e: _in_zone(e, "graveyard", 1, "T001"),
           choose=choose, attack_with="T708", attacker=0)
    assert _in_zone(e, "graveyard", 1, "T001")


def test_mana_dragons_below_threshold_no_trigger():
    """マナのドラゴンが1体だけなら攻撃誘発は働かない。"""
    e = setup(load_rules(), {"bz": ["T708"], "mana": ["T709"]},
              {"bz": ["T001"]})
    _drive(e, lambda e: e.s.turn == 2, attack_with="T708", attacker=0)
    assert _in_zone(e, "bz", 1, "T001")


# ---------- 追加ターン（T709 / T711） ----------

def test_extra_turn_spell_sets_flag():
    """追加ターン呪文を唱えると次のターンが追加ターンになり、旗が立つ。"""
    e = setup(load_rules(), {"hand": ["T711"], "mana": ["T709"]}, {})
    seen = {}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if "play:T711" in keys and "t711" not in seen:
            seen["t711"] = True
            return [keys.index("play:T711")]
        return None

    def note(e, d):
        if e.s.turn == 2 and "turn2" not in seen:
            seen["turn2"] = (e.s.active, e.s.extra_turn)

    _drive(e, lambda e: e.s.turn == 3, play=play, note=note)
    assert seen["turn2"] == (0, True)   # 追加ターンは同じプレイヤーで旗が立つ
    assert e.s.active == 1 and e.s.extra_turn is False   # その次は通常ターン


def test_destroy_trigger_grants_extra_turn():
    """通常ターンに破壊されれば追加ターンを得る（マナのドラゴン2体）。"""
    e = setup(load_rules(), {"bz": ["T709"], "hand": ["T710"], "mana": ["T709", "T709"]},
              {"bz": ["T001"]})
    played = {"n": 0}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if "play:T710" in keys and played["n"] == 0 and e.s.turn == 1:
            played["n"] += 1
            return [keys.index("play:T710")]
        return None

    def choose(e, d):
        idx = [i for i, o in enumerate(d["options"])
               if e.s.cards[o["cid"]].defn == "T709"]
        return idx[:1] if idx else []

    _drive(e, lambda e: e.s.turn == 2, play=play, choose=choose)
    assert e.s.active == 0 and e.s.extra_turn is True   # 追加ターンに入った


def test_destroy_trigger_blocked_in_extra_turn():
    """追加ターン中の破壊では {extra_turn: false} が偽になり、追加ターンは付かない。"""
    e = setup(load_rules(), {"bz": ["T709", "T709"], "hand": ["T710", "T710"],
                             "mana": ["T709", "T709"]}, {"bz": ["T001"]})
    played = {"n": 0}
    seen = {}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if "play:T710" in keys:
            if e.s.turn == 1 and played["n"] == 0:
                played["n"] += 1
                return [keys.index("play:T710")]
            if e.s.turn == 2 and played["n"] == 1:
                played["n"] += 1
                return [keys.index("play:T710")]
        return None

    def choose(e, d):
        idx = [i for i, o in enumerate(d["options"])
               if e.s.cards[o["cid"]].defn == "T709"]
        return idx[:1] if idx else []

    def note(e, d):
        if e.s.turn == 2 and "t2" not in seen:
            seen["t2"] = (e.s.active, e.s.extra_turn)

    _drive(e, lambda e: e.s.turn == 3
           and len([c for c in e.zlist("graveyard", 0)
                    if e.s.cards[c].defn == "T709"]) == 2,
           play=play, choose=choose, note=note)
    assert seen["t2"] == (0, True)                    # ターン2は追加ターンだった
    assert e.s.active == 1 and e.s.extra_turn is False   # 2体目の破壊では追加ターンは付かない


# ---------- distinct_names（T712） ----------

def test_distinct_names_play_free():
    """異なる名前の Jack-Pot だけ好きな数出せる。同名の2枚目は候補に出ない。"""
    e = setup(load_rules(), {"hand": ["T712", "T713", "T713", "T714"],
                             "mana": ["T708", "T708"]}, {})
    played = {"n": 0}
    picked = {"n": 0}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if "play:T712" in keys and played["n"] == 0:
            played["n"] += 1
            return [keys.index("play:T712")]
        return None

    def choose(e, d):
        opts = d["options"]
        if picked["n"] == 0:
            idx = next(i for i, o in enumerate(opts)
                       if e.s.cards[o["cid"]].defn == "T713")
            picked["n"] += 1
            return [idx]
        if picked["n"] == 1:
            assert all(e.s.cards[o["cid"]].defn != "T713" for o in opts), \
                "同名の2枚目が候補に残っている"
            idx = next(i for i, o in enumerate(opts)
                       if e.s.cards[o["cid"]].defn == "T714")
            picked["n"] += 1
            return [idx]
        return []

    _drive(e, lambda e: _in_zone(e, "bz", 0, "T713")
           and _in_zone(e, "bz", 0, "T714"), play=play, choose=choose)
    assert picked["n"] == 2
    assert _defns(e, "bz", 0).count("T713") == 1
    assert _defns(e, "hand", 0).count("T713") == 1   # 同名のもう1枚は手札に残る


def test_distinct_names_spell_fizzles_below_threshold():
    """マナのドラゴンが1体だけなら龍マナ武装の if が偽で、何も出ない。"""
    e = setup(load_rules(), {"hand": ["T712", "T713", "T714"], "mana": ["T708", "T001"]}, {})
    played = {"n": 0}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if "play:T712" in keys and played["n"] == 0:
            played["n"] += 1
            return [keys.index("play:T712")]
        return None

    _drive(e, lambda e: _in_zone(e, "graveyard", 0, "T712"), play=play)
    assert _in_zone(e, "hand", 0, "T713") and _in_zone(e, "hand", 0, "T714")


# ---------- シールドゾーンの常在付与（T715） ----------

def test_shield_static_grants_s_trigger():
    """マナのドラゴン2体でシールド中の T715 に S・トリガーが付く。1体では付かない。"""
    rules = load_rules()
    e = setup(rules, {"shield": ["T715"], "mana": ["T708", "T709"]}, {})
    cid = next(c for c in e.zlist("shield", 0) if e.s.cards[c].defn == "T715")
    assert "s_trigger" in e.chars(cid)["keywords"]
    e2 = setup(rules, {"shield": ["T715"], "mana": ["T709"]}, {})
    cid2 = next(c for c in e2.zlist("shield", 0) if e2.s.cards[c].defn == "T715")
    assert "s_trigger" not in e2.chars(cid2)["keywords"]


def test_shield_static_s_trigger_declared_on_break():
    """ブレイク時に S・トリガーが宣言でき、クリーチャーとして無料で出る。"""
    e = setup(load_rules(), {"shield": ["T715"], "mana": ["T708", "T709"]},
              {"bz": ["T001"]})
    seen = {"declared": False}

    def choose_shields(e, d):
        idx = [i for i, o in enumerate(d["options"])
               if e.s.cards[o["cid"]].defn == "T715"]
        assert idx, "T715 のシールドが選べない"
        return idx[:1]

    for _ in range(800):
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "attack" and e.s.active == 1:
            hit = next((i for i, k in enumerate(keys)
                        if k.startswith("attack:T001:")), None)
            if hit is not None:
                e.answer([hit])
                continue
        if kind == "choose_shields":
            e.answer(choose_shields(e, d))
        elif kind == "declare_strigger":
            assert any(k.startswith("strigger:T715") for k in keys), \
                f"S・トリガーが宣言できない: {keys}"
            seen["declared"] = True
            e.answer([next(i for i, k in enumerate(keys)
                          if k.startswith("strigger:T715"))])
        elif kind == "block":
            e.answer([keys.index("no_block")] if "no_block" in keys
                     else list(range(d.get("min", 0))))
        elif kind == "pay_mana":
            e.answer([0])
        elif kind == "yes_no":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if _in_zone(e, "bz", 0, "T715"):
            break
    assert seen["declared"]
    assert _in_zone(e, "bz", 0, "T715")


# ---------- dynamic + cost_of ベイク（T716） ----------

def test_dynamic_cost_of_bake():
    """表向きにした Jack-Pot（コスト2）以下の相手クリーチャーは攻撃できない。
    後から出たコスト2のクリーチャーにも及ぶ（dynamic）。"""
    e = setup(load_rules(),
              {"hand": ["T716", "T713"], "mana": ["T001", "T001", "T001"]},
              {"bz": ["T001", "T004"], "hand": ["T002"]})
    played = {"n": 0}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if "play:T716" in keys and played["n"] == 0:
            played["n"] += 1
            return [keys.index("play:T716")]
        return None

    def choose(e, d):
        idx = [i for i, o in enumerate(d["options"])
               if e.s.cards[o["cid"]].defn == "T713"]
        return idx[:1] if idx else []

    _drive(e, lambda e: any("cannot_attack" in (ce.get("mod") or {}).get("grant", [])
                            for ce in e.s.continuous),
           play=play, choose=choose)
    by = _by_defn(e, "bz", 1)
    assert e.permits(by["T001"], "attack_player") is False   # コスト2 → 攻撃できない
    assert e.permits(by["T004"], "attack_player") is True    # コスト3 → 攻撃できる
    # 後から出たコスト2のクリーチャーにも及ぶ
    t002 = _by_defn(e, "hand", 1)["T002"]
    e._raw_move(t002, "bz", controller=1)
    assert e.permits(t002, "attack_player") is False
