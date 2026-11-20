"""語彙パイロット第299弾: under_card_removed
（自分の進化クリーチャーの下にあるカードが墓地に置かれた時）。

純粋3件（dm34-014 呪言人形ワヤ / dm34-022 神星の守護者アルト・
コロニス / dm34-032 惑星の勇者ドリッピー）。3件とも同じ能力:
「自分の他のクリーチャーが破壊された時、または自分の進化
クリーチャーの下にあるカードが墓地に置かれた時、<効果>」。

不足は when の組み合わせの未検証だけだった（ドリフト）:
- 破壊側: {event: move, from: bz, to: graveyard, reason: destroy,
  subject: {owner: you, other: true, filter: {types: [creature]}},
  from_under: false}。from_under: false が要るのは、進化
  クリーチャーごと破壊された時、下のカードのレコード（host つき、
  reason も destroy）まで「自分のクリーチャーが破壊された」に
  数えて二重に発火させないため（dmsd06-012 の第3段先例と同じ
  切り分け。下のカードは特性を持たないカードとして墓地に
  置かれるのであって、クリーチャーが破壊されるのではない）。
- 下カード側: {event: move, from: bz, to: graveyard,
  from_under: {owner: you, filter: {types: [evolution]}}}。
  from_under 機構（第3段）には変換済み先例があるが、いずれも
  「自分が下にあったカード自身」の誘発（subject: self）か
  宿主自身の from_under: self で、第三のクリーチャーが場から
  監視する形は未検証だった。本弾でその形を実挙動で固定する。

効果側は3件とも既存イディオム:
- dm34-014: modify {power: -1000} duration: end_of_turn。
- dm34-022: choose {from_top: 1, count: 1} で上を束縛（見る）
  → if {exists: spell} → may [choose {ref, reveal: true} →
  move {ref} to hand]（dmx16-030 の「見て、呪文なら〜」形が
  正本。dmr08-008 が使う choose {count: 0, up_to: true} 形は
  select の mx=0 で常に空に束縛される不発形 — 後述の既存問題）。
- dm34-032: may [choose_number → choose {reveal: true} →
  if {cmp: [cost_of == declared]} then destroy power_le 5000]
  （第210弾 number_choice の宣言プリミティブ）。

プロト: T900（誘発対＋数え用ミル効果）/ T901（素の進化獣）/
T902（攻撃誘発で自分の下カードを単独で墓地へ送る進化獣）/
T903（宿主自身が from_under: self で監視する進化獣＋同駆動）/
T904（dm34-014 実形）/ T905（dm34-032 実形）/ T906（dm34-022
実形）。破壊の駆動は相手の T056。
"""
import copy

import pytest

from dmsim.cards.defs import DefError, load_tables, parse_card
from tests.conftest import setup

TABLES = load_tables()

WHEN_DESTROY = {"event": "move", "from": "bz", "to": "graveyard",
                "reason": "destroy",
                "subject": {"owner": "you", "other": True,
                            "filter": {"types": ["creature"]}},
                "from_under": False}
WHEN_UNDER = {"event": "move", "from": "bz", "to": "graveyard",
              "from_under": {"owner": "you",
                             "filter": {"types": ["evolution"]}}}
MILL = [{"op": "move", "select": {"zone": "deck", "owner": "you",
                                   "count": 1},
         "to": "graveyard", "reason": "put"}]
PAIR_MILL = [{"kind": "trigger", "when": copy.deepcopy(WHEN_DESTROY),
              "effect": copy.deepcopy(MILL)},
             {"kind": "trigger", "when": copy.deepcopy(WHEN_UNDER),
              "effect": copy.deepcopy(MILL)}]

EFFECT_014 = [{"op": "modify",
               "select": {"zone": "bz", "owner": "opp", "count": 1},
               "mod": {"power": -1000}, "duration": "end_of_turn"}]
EFFECT_022 = [{"op": "choose",
               "select": {"zone": "deck", "owner": "you", "from_top": 1,
                          "count": 1},
               "as": "top"},
              {"op": "if",
               "cond": {"exists": {"ref": "top",
                                   "filter": {"types": ["spell"]}}},
               "then": [{"op": "may", "body": [
                   {"op": "choose", "select": {"ref": "top", "count": 1},
                    "as": "hit", "reveal": True},
                   {"op": "move", "select": {"ref": "hit"},
                    "to": "hand", "reason": "draw"}]}]}]
EFFECT_032 = [{"op": "may", "body": [
    {"op": "choose_number", "as": "n"},
    {"op": "choose", "select": {"zone": "deck", "owner": "you",
                                 "count": 1},
     "as": "top", "reveal": True},
    {"op": "if",
     "cond": {"cmp": [{"cost_of": {"ref": "top"}}, "==",
                      {"declared": "n"}]},
     "then": [{"op": "move",
               "select": {"zone": "bz", "owner": "opp",
                          "filter": {"power_le": 5000}, "count": 1},
               "to": "graveyard", "reason": "destroy"}]}]}]


def _pair(effect):
    return [{"kind": "trigger", "when": copy.deepcopy(WHEN_DESTROY),
             "effect": copy.deepcopy(effect)},
            {"kind": "trigger", "when": copy.deepcopy(WHEN_UNDER),
             "effect": copy.deepcopy(effect)}]


FORMS = {"dm34-014": _pair(EFFECT_014), "dm34-022": _pair(EFFECT_022),
         "dm34-032": _pair(EFFECT_032)}


# ---------- ハーネス ----------

def _defns(e, zone, p=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _wire(e, host_defn, under_defns, p=0):
    """bz に置いた札同士で進化スタックを組む（第294弾と同じ作法）。"""
    host = next(c for c in e.zlist("bz", p) if e.s.cards[c].defn == host_defn
                and e.s.cards[c].top_of < 0)
    unders = []
    for ud in under_defns:
        u = next(c for c in e.zlist("bz", p) if e.s.cards[c].defn == ud
                 and e.s.cards[c].top_of < 0 and c != host)
        e.s.cards[u].top_of = host
        unders.append(u)
    e.s.cards[host].under = unders
    e.s.cards[host].stack_bases = list(unders)
    return host, unders


def _drive(e, done, cast=None, cast_player=1, target_defn=None,
           pick_defn=None, attack_with=None, yes=True, num_key=None,
           steps=400):
    """done(e) が真になるまで汎用に答える（第294弾 _drive の拡張:
    choose_one（数字宣言）と攻撃駆動を追加）。"""
    st = {"cast": False, "attacked": False}
    for _ in range(steps):
        if done(e):
            return st
        d = e.advance()
        assert d is not None, "game ended before done"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "main" and cast and not st["cast"] \
                and d.get("player") == cast_player and f"play:{cast}" in keys:
            e.answer([keys.index(f"play:{cast}")])
            st["cast"] = True
        elif kind == "attack" and attack_with and not st["attacked"]:
            cand = [k for k in keys if k.startswith(f"attack:{attack_with}:")
                    and k.endswith(":player")]
            if cand:
                e.answer([keys.index(cand[0])])
                st["attacked"] = True
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
        elif kind == "choose_cards":
            idx = None
            for want in (pick_defn, target_defn):
                if not want:
                    continue
                for o in d["options"]:
                    if e.s.cards[o["cid"]].defn == want:
                        idx = keys.index(o["key"])
                        break
                if idx is not None:
                    break
            e.answer([idx] if idx is not None else list(range(d["min"])))
        elif kind == "choose_one" and num_key is not None:
            e.answer([keys.index(num_key)])
        elif kind == "yes_no":
            want = "yes" if yes else "no"
            e.answer([keys.index(want)] if want in keys
                     else list(range(d["min"])))
        elif kind == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("drive budget exhausted")


def _pub(e, kind, defn=None):
    return [r for r in e.s.pub if r["kind"] == kind
            and (defn is None or r.get("defn") == defn)]


P1_DESTROY = {"hand": ["T056"], "mana": ["T008"] * 3}


def _mills(e, event_cards):
    """p0 の墓地の増加から、出来事そのもので落ちた枚数を引いた残り
    ＝ T900／T903 のミル効果の発火回数。"""
    return len(e.zlist("graveyard", 0)) - event_cards


# ---------- parse / validation ----------

def test_pilot299_protos_parse(rules):
    d = rules.cards["T900"]
    assert d.abilities == PAIR_MILL
    d = rules.cards["T903"]
    assert {"kind": "trigger",
            "when": {"event": "move", "from": "bz", "to": "graveyard",
                     "from_under": "self"},
            "effect": MILL} in d.abilities
    assert rules.cards["T904"].abilities == FORMS["dm34-014"]
    assert rules.cards["T905"].abilities == FORMS["dm34-032"]
    assert rules.cards["T906"].abilities == FORMS["dm34-022"]


def test_pilot299_forms_raw_parse():
    for cid, abilities in FORMS.items():
        d = parse_card({"id": "TX299", "name": "x", "types": ["creature"],
                        "civs": ["darkness"], "cost": 3, "power": 1000,
                        "abilities": copy.deepcopy(abilities)}, TABLES)
        assert d.abilities == abilities, cid


def test_pilot299_validation():
    # from_under の owner は you/opp/any のみ
    bad = {"kind": "trigger",
           "when": {"event": "move", "to": "graveyard",
                    "from_under": {"owner": "bogus"}},
           "effect": copy.deepcopy(MILL)}
    with pytest.raises(DefError):
        parse_card({"id": "TX299", "name": "x", "types": ["creature"],
                    "civs": ["darkness"], "cost": 3, "power": 1000,
                    "abilities": [bad]}, TABLES)
    # from_under の未知キーは拒否される
    bad2 = {"kind": "trigger",
            "when": {"event": "move", "to": "graveyard",
                     "from_under": {"owner": "you", "bogus": 1}},
            "effect": copy.deepcopy(MILL)}
    with pytest.raises(DefError):
        parse_card({"id": "TX299", "name": "x", "types": ["creature"],
                    "civs": ["darkness"], "cost": 3, "power": 1000,
                    "abilities": [bad2]}, TABLES)


# ---------- 実挙動: 誘発対（T900） ----------

def test_destroy_other_creature_fires_once(rules):
    """自分の他のクリーチャーが破壊されたら1回だけ発火する。"""
    e = setup(rules, {"bz": ["T900", "T001"]}, dict(P1_DESTROY),
              filler="T002")
    _drive(e, lambda e: "T001" in _defns(e, "graveyard") and _quiet(e),
           cast="T056", target_defn="T001")
    assert _mills(e, 1) == 1


def test_stack_destroy_fires_destroy_and_under_once_each(rules):
    """進化クリーチャーごと破壊: 破壊側1回＋下カード側1回。
    下カードのレコードが破壊側にも数えられると3回になる。"""
    e = setup(rules, {"bz": ["T900", "T901", "T001"]}, dict(P1_DESTROY),
              filler="T002")
    _wire(e, "T901", ["T001"])
    _drive(e, lambda e: "T901" in _defns(e, "graveyard") and _quiet(e),
           cast="T056", target_defn="T901")
    assert "T001" in _defns(e, "graveyard")
    assert _mills(e, 2) == 2


def test_stack_destroy_two_unders_fires_per_card(rules):
    """下カードが2枚あれば、下カード側は1枚につき1回ずつ発火する
    （「カードが墓地に置かれた時」のレコード単位の発火）。"""
    e = setup(rules, {"bz": ["T900", "T901", "T001", "T007"]},
              dict(P1_DESTROY), filler="T002")
    _wire(e, "T901", ["T001", "T007"])
    _drive(e, lambda e: "T901" in _defns(e, "graveyard") and _quiet(e),
           cast="T056", target_defn="T901")
    assert _mills(e, 3) == 3     # 破壊側1回＋下カード側2回


def test_single_under_move_fires_under_only(rules):
    """下カードが単独で（reason: put で）墓地に置かれたら
    下カード側だけが発火する。"""
    e = setup(rules, {"bz": ["T900", "T902", "T001"],
                      "shield": ["T001"] * 5}, {}, filler="T002")
    host, unders = _wire(e, "T902", ["T001"])
    _drive(e, lambda e: "T001" in _defns(e, "graveyard") and _quiet(e),
           attack_with="T902")
    assert e.s.cards[host].zone == "bz"          # 宿主は場に残る
    assert _mills(e, 1) == 1


def test_opponent_stack_does_not_fire(rules):
    """相手の進化クリーチャーとその下カードは監視対象外。"""
    e = setup(rules, {"bz": ["T900"], "hand": ["T056"],
                      "mana": ["T008"] * 3},
              {"bz": ["T901", "T001"]}, filler="T002")
    _wire(e, "T901", ["T001"], p=1)
    _drive(e, lambda e: "T901" in _defns(e, "graveyard", 1) and _quiet(e),
           cast="T056", cast_player=0, target_defn="T901")
    # p0 の墓地は唱えた T056 のみ（ミルは発火していない）
    assert _defns(e, "graveyard") == ["T056"]


def test_watcher_itself_destroyed_does_not_fire(rules):
    """監視者自身が破壊されても発火しない（other: true）。"""
    e = setup(rules, {"bz": ["T900", "T001"]}, dict(P1_DESTROY),
              filler="T002")
    _drive(e, lambda e: "T900" in _defns(e, "graveyard") and _quiet(e),
           cast="T056", target_defn="T900")
    assert _mills(e, 1) == 0


# ---------- 実挙動: 宿主自身の from_under: self（T903） ----------

def test_host_self_single_under_fires_once(rules):
    """宿主がまだ場にいる状態で下カードが単独で離れても、
    宿主の from_under: self 誘発は1回だけ発火する
    （通常の発生源と host_only 発生源の二重収集が無いこと）。"""
    e = setup(rules, {"bz": ["T903", "T001"], "shield": ["T001"] * 5}, {},
              filler="T002")
    host, unders = _wire(e, "T903", ["T001"])
    _drive(e, lambda e: "T001" in _defns(e, "graveyard") and _quiet(e),
           attack_with="T903")
    assert e.s.cards[host].zone == "bz"
    assert _mills(e, 1) == 1


def test_host_self_stack_destroyed_fires_once(rules):
    """宿主ごと破壊された時は、宿主の lki 発生源（host_only）から
    1回だけ発火する。"""
    e = setup(rules, {"bz": ["T903", "T001"]}, dict(P1_DESTROY),
              filler="T002")
    _wire(e, "T903", ["T001"])
    _drive(e, lambda e: "T903" in _defns(e, "graveyard") and _quiet(e),
           cast="T056", target_defn="T903")
    assert _mills(e, 2) == 1


# ---------- 実挙動: dm34-014 実形（T904） ----------

def test_form_014_modify_power_minus_1000(rules):
    """破壊を監視して相手クリーチャー1体のパワーを -1000 する
    （そのターンの間）。"""
    e = setup(rules, {"bz": ["T904", "T001"]},
              {"bz": ["T004"], "hand": ["T056"], "mana": ["T008"] * 3},
              filler="T002")
    tgt = next(c for c in e.zlist("bz", 1) if e.s.cards[c].defn == "T004")
    assert e.chars(tgt)["power"] == 3000
    _drive(e, lambda e: "T001" in _defns(e, "graveyard") and _quiet(e),
           cast="T056", target_defn="T001")
    assert e.chars(tgt)["power"] == 2000


# ---------- 実挙動: dm34-032 実形（T905） ----------

def _top_cost(e, rules):
    top = e.s.zones["deck"][0][0]
    return rules.cards[e.s.cards[top].defn].cost, e.s.cards[top].defn


def test_form_032_number_match_destroys(rules):
    """数字を選んで山札の上を表向きにし、コストが一致したら
    相手のパワー5000以下を破壊する。"""
    e = setup(rules, {"bz": ["T905", "T001"]},
              {"bz": ["T004"], "hand": ["T056"], "mana": ["T008"] * 3},
              filler="T002")
    cost, top_defn = _top_cost(e, rules)
    _drive(e, lambda e: "T004" in _defns(e, "graveyard", 1) and _quiet(e),
           cast="T056", target_defn="T001", pick_defn="T004",
           num_key=f"num:{cost}")
    assert _pub(e, "reveal", defn=top_defn)   # 上のカードは表向きにされた


def test_form_032_number_mismatch_no_destroy(rules):
    """コストが一致しなければ破壊は起きない（表向きにはする）。"""
    e = setup(rules, {"bz": ["T905", "T001"]},
              {"bz": ["T004"], "hand": ["T056"], "mana": ["T008"] * 3},
              filler="T002")
    cost, top_defn = _top_cost(e, rules)
    miss = cost + 1 if cost < 10 else cost - 1
    _drive(e, lambda e: "T001" in _defns(e, "graveyard") and _quiet(e),
           cast="T056", target_defn="T001", pick_defn="T004",
           num_key=f"num:{miss}")
    assert "T004" in _defns(e, "bz", 1)
    assert _pub(e, "reveal", defn=top_defn)


def test_form_032_decline_does_nothing(rules):
    """数字を選ばなければ、表向きにも破壊にもならない。"""
    e = setup(rules, {"bz": ["T905", "T001"]},
              {"bz": ["T004"], "hand": ["T056"], "mana": ["T008"] * 3},
              filler="T002")
    _drive(e, lambda e: "T001" in _defns(e, "graveyard") and _quiet(e),
           cast="T056", target_defn="T001", yes=False)
    assert "T004" in _defns(e, "bz", 1)
    assert not _pub(e, "reveal")


# ---------- 実挙動: dm34-022 実形（T906、山札を固定して検証） ----------

def _build_exact(rules, deck_card):
    """山札を指定カード4枚だけにする（1ターン目のドローで1枚引いても
    上が同じカードに保たれ、デッキ切れにもならない）。"""
    from dmsim.engine import scenario
    return scenario.build(
        rules, {"p0": {"bz": ["T906", "T001"], "deck": [deck_card] * 4},
                "p1": dict(P1_DESTROY), "filler": "T002", "seed": 1,
                "deck_exact": [True, False]})


def test_form_022_takes_spell_from_top(rules):
    """山札の上が呪文なら、見せてから手札に加える。"""
    e = _build_exact(rules, "T003")
    assert [e.s.cards[c].defn for c in e.s.zones["deck"][0]] == ["T003"] * 4
    # 手札の T003 が「ターン1のドロー1枚＋効果で加えた1枚」＝2枚になる
    _drive(e, lambda e: _defns(e, "hand").count("T003") == 2 and _quiet(e),
           cast="T056", target_defn="T001", pick_defn="T003")
    assert _pub(e, "reveal", defn="T003")     # 相手に見せた記録
    assert len(e.s.zones["deck"][0]) == 2     # ドロー1＋効果で1枚減った


def test_form_022_creature_on_top_stays(rules):
    """山札の上が呪文でなければ、何も起きない（見ただけ）。"""
    e = _build_exact(rules, "T004")
    _drive(e, lambda e: "T001" in _defns(e, "graveyard") and _quiet(e),
           cast="T056", target_defn="T001", pick_defn="T004")
    assert _defns(e, "hand") == ["T004"]      # ターン1のドロー分だけ
    assert len(e.s.zones["deck"][0]) == 3     # 上は動いていない
    assert e.s.cards[e.s.zones["deck"][0][0]].defn == "T004"
    assert not _pub(e, "reveal", defn="T004")
