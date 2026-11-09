"""語彙パイロット第149弾: d_d_d_rider（D・D・D によって出た時／D・D・D で唱えたならの照合）。

- op play_self に任意引数 via を追加し、h_play が task の via を move／cast イベントと
  呪文の解決 env（ddd_paid）へ写す。VIAS に d_d_d を追加（when の via で照合できる）。
  via を付けるのは rider を持つカードの D・D・D の declare だけ（変換ルールとして
  docs/vocab-pilot.md に明記）。キリフダッシュの play_self には付けない。
- クリーチャー側は when: {event: move, subject: self, to: bz, via: d_d_d}（革命チェンジの
  via: revolution_change と同型）、呪文側は新 cond 原子 ddd_paid（vivid_paid／alt_paid と同型。
  env のフラグ、または env.event の via == "d_d_d" を読む）。
- ついでに直した潜在バグ: 誘発収集レコード（_apply_one の out）に alt／vivid の印が
  写されておらず、when: {vivid: true} の move 誘発と、誘発の if: {alt_paid: true} が
  実際には発火しなかった。ddd と同じ経路で alt／vivid も収集レコードに伝播させる。
  R108（伝播観測獣）はどちらの効果も「相手のクリーチャーをタップする」で、
  次のターンのドローのような代替説明が効かない判別形にしてある。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import DefError, card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


X_CARDS = """
cards:
  - id: X186
    name: 斬札型ライダー試験獣
    civs: [fire]
    cost: 5
    power: 4000
    types: [creature]
    races: [テスト]
    text: キリフダッシュ[火1]（自分のクリーチャーの攻撃の終わりに、そのクリーチャーがその攻撃中にシールドをブレイクしていれば、このクリーチャーを[火1]支払って召喚してもよい）。このクリーチャーが「D・D・D」によって出た時、カードを１枚引く。
    abilities:
      - kind: trigger
        zone: hand
        optional: true
        when: {event: attack_end, broke: true, subject: {owner: you}}
        effect:
          - {op: may, body: [{op: play_self, cost: 1, civs: [fire]}]}
      - kind: trigger
        when: {event: move, subject: self, to: bz, via: d_d_d}
        effect:
          - {op: draw, count: 1}
  - id: X187
    name: S・トリガーライダー試験呪文
    civs: [water]
    cost: 3
    types: [spell]
    races: [テスト]
    keywords: [s_trigger]
    text: S・トリガー。D・D・D [ww01]（自分のクリーチャーが攻撃する時、このカードを [ww01] 支払って自分の手札から実行してもよい）。カードを１枚引く。この呪文を「D・D・D」で唱えたなら、相手のアンタップしているクリーチャーを１体タップする。
    abilities:
      - kind: declare
        zone: hand
        when: {event: attack, subject: {owner: you, filter: {types: [creature]}}}
        effect:
          - op: may
            body:
              - {op: play_self, cost: 1, civs: [water], via: d_d_d}
    spell:
      - {op: draw, count: 1}
      - op: if
        cond: {ddd_paid: true}
        then:
          - {op: tap, select: {zone: bz, owner: opp, filter: {types: [creature], tapped: false}, count: 1}}
  - id: X188
    name: 全制覇決断試験呪文
    civs: [water]
    cost: 3
    types: [spell]
    races: [テスト]
    text: D・D・D [ww01]（自分のクリーチャーが攻撃する時、このカードを [ww01] 支払って自分の手札から実行してもよい）。次の中から２回選ぶ。（同じものを選んでもよい）この呪文を「D・D・D」で唱えたなら、かわりにすべてを１回ずつ使う。▶カードを１枚引く。▶自分の山札の上から１枚を墓地に置く。▶自分のマナゾーンにあるカードを１枚アンタップする。
    abilities:
      - kind: declare
        zone: hand
        when: {event: attack, subject: {owner: you, filter: {types: [creature]}}}
        effect:
          - op: may
            body:
              - {op: play_self, cost: 1, civs: [water], via: d_d_d}
    spell:
      - op: if
        cond: {ddd_paid: true}
        then:
          - op: modal
            count: 3
            modes: &x188_modes
              - [{op: draw, count: 1}]
              - [{op: mill, owner: you, count: 1}]
              - [{op: untap, select: {zone: mana, owner: you, count: 1}}]
        else:
          - op: modal
            count: 2
            repeat: true
            modes: *x188_modes
"""


@pytest.fixture(scope="session")
def xr(tmp_path_factory):
    p = tmp_path_factory.mktemp("pilot149x") / "x_cards.yaml"
    p.write_text(X_CARDS, encoding="utf-8")
    return load_rules(card_yaml_files() + [p])


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _rule_card(cid):
    with open(Path(__file__).parent / "rule_cards.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _cid(e, zone, p, defn):
    pool = e.bz_tops(p) if zone == "bz" else e.zlist(zone, p)   # bz は共有ゾーンなので bz_tops で引く
    return next(c for c in pool if e.cdef(c).id == defn)


def _answer(e, d, st):
    """標準の答え方。st のキー: play_key（main で1回）／declare_key（提示されたら1回）／
    attack_key（攻撃を1回）／modes（choose_mode の消費列）／pay_exclude（支払いから外す cid）。"""
    keys = [o["key"] for o in d["options"]]
    k = d["kind"]
    if st.get("declare_key") and st["declare_key"] in keys and not st.get("declared"):
        st["declared"] = True
        e.answer([keys.index(st["declare_key"])])
    elif k == "main" and st.get("reveal_key") and st["reveal_key"] in keys:
        e.answer([keys.index(st["reveal_key"])])
    elif k == "main" and st.get("vivid_key") and st["vivid_key"] in keys:
        e.answer([keys.index(st["vivid_key"])])
    elif k == "main" and st.get("play_key") and st["play_key"] in keys and not st.get("played"):
        st["played"] = True
        e.answer([keys.index(st["play_key"])])
    elif k == "pay_mana":
        idx = [i for i, o in enumerate(d["options"]) if o.get("cid") != st.get("pay_exclude")]
        e.answer(idx[:d["max"]])
    elif k == "yes_no":
        e.answer([keys.index("yes") if "yes" in keys else 0])
    elif k == "choose_mode":
        m = st["modes"].pop(0) if st.get("modes") else 0
        e.answer([keys.index(f"mode:{m}")])
    elif k == "attack" and st.get("attack_key") and not st.get("attacked"):
        if st["attack_key"] in keys:
            st["attacked"] = True
            e.answer([keys.index(st["attack_key"])])
        else:
            e.answer([keys.index("pass")])
    elif k == "declare_strigger" and st.get("strigger_defn"):
        hit = [i for i, o in enumerate(d["options"]) if o.get("cid") is not None
               and e.cdef(o["cid"]).id == st["strigger_defn"]]
        e.answer(hit[:1])
    elif k == "choose_shields" and st.get("shield_defn"):
        hit = [i for i, o in enumerate(d["options"]) if o.get("cid") is not None
               and e.cdef(o["cid"]).id == st["shield_defn"]]
        e.answer(hit[:max(d["min"], 1)] if hit else list(range(d["min"])))
    elif k in ("declare_strigger", "declare_sback"):
        e.answer([])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _drive(e, st, stop=None, record=None, hook=None, maxn=400):
    for _ in range(maxn):
        if stop and stop(e):
            return
        d = e.advance()
        if d is None:
            return
        if record is not None:
            record.append(d)
        if hook:
            hook(e, d)
        _answer(e, d, st)


def _capture_at_entry(e, st, defn, snap):
    """defn がバトルゾーンに入った直後（次の Decision の提示時点）で snap(e) を返す。
    誘発は Decision が提示される前にすべて解決されているので、この時点の状態で
    誘発の発火／不発を判別できる（次のターンのドロー等の代替説明が入らない）。"""
    for _ in range(400):
        d = e.advance()
        if d is None:
            break
        if any(e.cdef(c).id == defn for c in e.zlist("bz", 0)):
            return snap(e)
        _answer(e, d, st)
    raise AssertionError(f"{defn} did not enter")


# ---------- parse / 検証 ----------

def test_pilot149_parses():
    for cid in ("T186", "T187", "T188"):
        assert parse_card(_proto_card(cid), TABLES) is not None
    assert parse_card(_rule_card("R108"), TABLES) is not None
    t186 = parse_card(_proto_card("T186"), TABLES)
    dec = next(ab for ab in t186.abilities if ab["kind"] == "declare")
    assert dec["effect"][0]["body"][0] == {"op": "play_self", "cost": 6,
                                           "civs": ["darkness", "fire", "nature"], "via": "d_d_d"}
    rider = next(ab for ab in t186.abilities if ab["kind"] == "trigger")
    assert rider["when"]["via"] == "d_d_d"
    t187 = parse_card(_proto_card("T187"), TABLES)
    assert t187.spell[1]["cond"] == {"ddd_paid": True}
    t188 = parse_card(_proto_card("T188"), TABLES)
    decs = [ab for ab in t188.abilities if ab["kind"] == "declare"]
    assert [ab["zone"] for ab in decs] == ["hand", "mana"]
    assert all(ab["effect"][0]["body"][0]["via"] == "d_d_d" for ab in decs)
    branch = t188.spell[0]
    assert branch["then"][0]["count"] == 3 and branch["else"][0]["count"] == 2


def _creature(abilities):
    return {"id": "test-p149", "name": "試験", "types": ["creature"], "civs": ["fire"], "cost": 2,
            "power": 2000, "races": ["テスト"], "text": "", "abilities": abilities,
            "source": {"official": "test-p149", "review": "pending"}}


def _spell(ops_list, abilities=None):
    card = {"id": "test-p149s", "name": "試験", "types": ["spell"], "civs": ["water"], "cost": 3,
            "races": ["テスト"], "text": "", "spell": ops_list,
            "source": {"official": "test-p149s", "review": "pending"}}
    if abilities:
        card["abilities"] = abilities
    return card


def test_via_and_ddd_validation():
    """when の via と play_self の via は VIAS の値だけ。ddd_paid は bool だけ。"""
    ok_when = [{"kind": "trigger", "when": {"event": "move", "subject": "self", "to": "bz", "via": "d_d_d"},
                "effect": [{"op": "draw", "count": 1}]}]
    assert parse_card(_creature(ok_when), TABLES) is not None
    with pytest.raises(DefError):
        parse_card(_creature([dict(ok_when[0], when={"event": "move", "subject": "self",
                                                     "to": "bz", "via": "bogus"})]), TABLES)
    dec = [{"kind": "declare", "zone": "hand",
            "when": {"event": "attack", "subject": {"owner": "you", "filter": {"types": ["creature"]}}},
            "effect": [{"op": "may", "body": [{"op": "play_self", "cost": 1, "civs": ["fire"], "via": "d_d_d"}]}]}]
    assert parse_card(_creature(dec), TABLES) is not None
    bad = [{"kind": "declare", "zone": "hand",
            "when": {"event": "attack", "subject": {"owner": "you", "filter": {"types": ["creature"]}}},
            "effect": [{"op": "may", "body": [{"op": "play_self", "cost": 1, "civs": ["fire"], "via": "bogus"}]}]}]
    with pytest.raises(DefError):
        parse_card(_creature(bad), TABLES)
    assert parse_card(_spell([{"op": "if", "cond": {"ddd_paid": True},
                               "then": [{"op": "draw", "count": 1}]}]), TABLES) is not None
    with pytest.raises(DefError):
        parse_card(_spell([{"op": "if", "cond": {"ddd_paid": "yes"},
                            "then": [{"op": "draw", "count": 1}]}]), TABLES)


# ---------- 実挙動: クリーチャーの rider ----------

def test_rider_fires_on_d_d_d(rules):
    """(1) T186 を D・D・D で出すと rider が発火し、入場直後に1ドローしている。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T186"],
                      "mana": ["T008", "T005", "T001", "T001", "T002", "T002"]},
              {"shield": ["T001", "T001"]})
    e.s.cards[_cid(e, "bz", 0, "T001")].entered_turn = -1
    st = {"declare_key": "declare:T186:0", "attack_key": "attack:T001:player"}
    hand = _capture_at_entry(e, st, "T186", lambda e_: len(e_.zlist("hand", 0)))
    assert st.get("declared")
    assert hand == 1                                        # 手札0→ rider のドローで1
    assert sum(1 for c in e.zlist("mana", 0) if e.s.cards[c].tapped) == 6   # D・D・D [dfn06] を払った


def test_rider_silent_on_normal_summon(rules):
    """(1) 通常召喚では rider は発火しない（入場直後の手札は0のまま）。"""
    e = setup(rules, {"hand": ["T186"], "mana": ["T005", "T005"]}, {})
    st = {"play_key": "play:T186"}
    hand = _capture_at_entry(e, st, "T186", lambda e_: len(e_.zlist("hand", 0)))
    assert hand == 0


def test_rider_silent_on_kirifudash(xr):
    """(2) キリフダッシュ型の play_self（via 無し）で出しても rider は発火しない。"""
    e = setup(xr, {"bz": ["T005"], "hand": ["X186"], "mana": ["T005"]}, {"shield": ["T001"]})
    e.s.cards[_cid(e, "bz", 0, "T005")].entered_turn = -1
    st = {"attack_key": "attack:T005:player"}
    hand = _capture_at_entry(e, st, "X186", lambda e_: len(e_.zlist("hand", 0)))
    assert hand == 0                                        # X186 が手札を離れただけで、ドローは無い
    assert e.s.cards[_cid(e, "mana", 0, "T005")].tapped     # キリフダッシュ [火1] は払った


# ---------- 実挙動: 呪文の ddd_paid ----------

def test_spell_draws_extra_on_d_d_d(rules):
    """(3) T187: D・D・D で唱えると ddd_paid が真になり、追加の1ドローが付く。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T187"], "mana": ["T003"]}, {"shield": ["T001"]})
    e.s.cards[_cid(e, "bz", 0, "T001")].entered_turn = -1
    st = {"declare_key": "declare:T187:0", "attack_key": "attack:T001:player"}
    _drive(e, st, stop=lambda e_: any(e_.cdef(c).id == "T187" for c in e_.zlist("graveyard", 0)))
    assert st.get("declared")
    assert len(e.zlist("hand", 0)) == 2                     # 本体1＋ddd_paid の追加1


def test_spell_no_extra_on_normal_cast(rules):
    """(3) T187: 通常に唱えると ddd_paid は偽で、本体の1ドローだけ。"""
    e = setup(rules, {"hand": ["T187"], "mana": ["T003", "T003", "T003"]}, {})
    st = {"play_key": "play:T187"}
    _drive(e, st, stop=lambda e_: any(e_.cdef(c).id == "T187" for c in e_.zlist("graveyard", 0)))
    assert len(e.zlist("hand", 0)) == 1


def test_spell_no_ddd_paid_on_s_trigger(xr):
    """(4) S・トリガーで唱えた呪文は play_self を経由しないので ddd_paid は立たない。"""
    e = setup(xr, {"shield": ["X187"], "mana": ["T003"]},
              {"bz": ["T005", "T001"], "shield": ["T001"]})
    e.s.cards[_cid(e, "bz", 1, "T005")].entered_turn = -1
    victim = _cid(e, "bz", 1, "T001")
    st = {"attack_key": "attack:T005:player", "strigger_defn": "X187", "shield_defn": "X187"}
    _drive(e, st, stop=lambda e_: any(e_.cdef(c).id == "X187" for c in e_.zlist("graveyard", 0)))
    assert not e.s.cards[victim].tapped   # ddd_paid の追加効果（タップ）は起きていない


# ---------- 実挙動: modal の回数切り替え ----------

def test_modal_count_two_normal_three_on_d_d_d(rules):
    """(7) T188（rp3s08 型）: 通常は modal 2回、D・D・D では3回選べる。"""
    e = setup(rules, {"hand": ["T188"], "mana": ["T004", "T003", "T001", "T001"]}, {})
    st = {"play_key": "play:T188", "modes": [0, 0]}
    _drive(e, st, stop=lambda e_: any(e_.cdef(c).id == "T188" for c in e_.zlist("graveyard", 0)))
    assert len(e.zlist("hand", 0)) == 2                     # mode 0（1ドロー）を2回

    e = setup(rules, {"bz": ["T001"], "hand": ["T188"],
                      "mana": ["T004", "T003", "T001", "T001", "T001"]}, {"shield": ["T001"]})
    e.s.cards[_cid(e, "bz", 0, "T001")].entered_turn = -1
    st = {"declare_key": "declare:T188:0", "attack_key": "attack:T001:player", "modes": [0, 0, 0]}
    _drive(e, st, stop=lambda e_: any(e_.cdef(c).id == "T188" for c in e_.zlist("graveyard", 0)))
    assert st.get("declared")
    assert len(e.zlist("hand", 0)) == 3                     # mode 0 を3回


def test_modal_all_modes_once_on_d_d_d(xr):
    """(7) X188（rp3011 型）: D・D・D では「すべてを1回ずつ」になり、3モードが各1回ずつ解決される。"""
    e = setup(xr, {"bz": ["T001"], "hand": ["X188"], "mana": ["T003"]}, {"shield": ["T001"]})
    e.s.cards[_cid(e, "bz", 0, "T001")].entered_turn = -1
    st = {"declare_key": "declare:X188:0", "attack_key": "attack:T001:player", "modes": [0, 1, 2]}
    _drive(e, st, stop=lambda e_: any(e_.cdef(c).id == "X188" for c in e_.zlist("graveyard", 0)))
    assert st.get("declared")
    assert len(e.zlist("hand", 0)) == 1                     # mode 0 の1ドロー
    assert len(e.zlist("graveyard", 0)) == 2                # X188 自身＋mode 1 で墓地に置いた1枚
    assert not any(e.s.cards[c].tapped for c in e.zlist("mana", 0))   # mode 2 で支払ったマナがアンタップ


def test_modal_repeat_normal_cast(xr):
    """(7) X188: 通常に唱えると modal 2回（同じものを選んでもよい）。"""
    e = setup(xr, {"hand": ["X188"], "mana": ["T003", "T003", "T003"]}, {})
    st = {"play_key": "play:X188", "modes": [0, 0]}
    _drive(e, st, stop=lambda e_: any(e_.cdef(c).id == "X188" for c in e_.zlist("graveyard", 0)))
    assert len(e.zlist("hand", 0)) == 2
    assert len(e.zlist("graveyard", 0)) == 1                # X188 自身だけ


def test_declare_from_mana(rules):
    """(5) T188 はマナゾーンからも declare でき、D・D・D で唱えれば ddd_paid が真（modal 3回）。"""
    e = setup(rules, {"bz": ["T001"],
                      "mana": ["T188", "T004", "T003", "T001", "T001", "T001"]},
              {"shield": ["T001"]})
    e.s.cards[_cid(e, "bz", 0, "T001")].entered_turn = -1
    t188 = _cid(e, "mana", 0, "T188")
    record = []
    st = {"declare_key": "declare:T188:1", "attack_key": "attack:T001:player",
          "modes": [0, 0, 0], "pay_exclude": t188}
    _drive(e, st, record=record,
           stop=lambda e_: any(e_.cdef(c).id == "T188" for c in e_.zlist("graveyard", 0)))
    assert st.get("declared")
    assert any(o["key"] == "declare:T188:1" for d in record for o in d["options"])
    assert len(e.zlist("hand", 0)) == 3                     # modal 3回ぶんのドロー
    assert t188 not in e.zlist("mana", 0)


# ---------- 実挙動: 印の伝播（vivid／alt の潜在バグ根治） ----------

def _watch_own_turn(e, st, watch):
    """自分のターンの間だけ進め、各 Decision の提示時点で watch(e) の値を集めて返す。
    相手のターンに入る（＝アンタップ等で状態が戻る）前に止めるので、タップの有無を
    そのまま誘発の発火／不発として判別できる。"""
    seen = []
    for _ in range(400):
        d = e.advance()
        if d is None or d.get("player") == 1:
            break
        seen.append(watch(e))
        _answer(e, d, st)
    return seen


def test_vivid_mark_reaches_move_trigger(rr):
    """R108: 自分のクリーチャーがビビッドローで召喚された時、相手のクリーチャーをタップする。
    when: {vivid: true} が誘発収集レコードに届くようになったことで初めて発火する（判別形）。"""
    e = setup(rr, {"bz": ["R108"], "hand": ["T092"], "mana": ["T003", "T005"]},
              {"bz": ["T001"], "shield": ["T001"]})
    t092 = _cid(e, "hand", 0, "T092")
    e._raw_move(t092, "deck", "top")   # 最初のドローで引かせる
    opp = _cid(e, "bz", 1, "T001")
    st = {"reveal_key": "reveal:T092", "vivid_key": "play:T092:vivid"}
    _drive(e, st, stop=lambda e_: e_.s.cards[opp].tapped)
    assert e.s.cards[opp].tapped
    assert e.s.active == 0              # 自分のターンのうちにタップした（誘発の解決）


def test_vivid_mark_absent_on_normal_summon(rr):
    """通常召喚では R108 の vivid 誘発は発火せず、自分のターンの間、相手のクリーチャーは
    一度もタップされない。"""
    e = setup(rr, {"bz": ["R108"], "hand": ["T092"], "mana": ["T003", "T005", "T001", "T001"]},
              {"bz": ["T001"], "shield": ["T001"]})
    opp = _cid(e, "bz", 1, "T001")
    st = {"play_key": "play:T092"}
    seen = _watch_own_turn(e, st, lambda e_: e_.s.cards[opp].tapped)
    assert any(e.cdef(c).id == "T092" for c in e.zlist("bz", 0))   # 召喚自体は成立している
    assert seen and not any(seen)


def test_alt_mark_reaches_enter_trigger_if(rr):
    """R108: 代替コストで召喚した時だけ、出た時誘発の if: {alt_paid: true} が成り立つ（判別形）。"""
    e = setup(rr, {"bz": ["T001"], "hand": ["R108"], "mana": ["T001"]},
              {"bz": ["T001"], "shield": ["T001"]})
    opp = _cid(e, "bz", 1, "T001")
    st = {"play_key": "play:R108:alt"}
    _drive(e, st, stop=lambda e_: e_.s.cards[opp].tapped)
    assert e.s.cards[opp].tapped
    assert e.s.active == 0


def test_alt_mark_absent_on_normal_summon(rr):
    """R108 を通常召喚した時は if: {alt_paid: true} が成り立たず、自分のターンの間、
    相手のクリーチャーは一度もタップされない。"""
    e = setup(rr, {"bz": ["T001"], "hand": ["R108"], "mana": ["T001", "T001", "T001"]},
              {"bz": ["T001"], "shield": ["T001"]})
    opp = _cid(e, "bz", 1, "T001")
    st = {"play_key": "play:R108"}
    seen = _watch_own_turn(e, st, lambda e_: e_.s.cards[opp].tapped)
    assert any(e.cdef(c).id == "R108" for c in e.zlist("bz", 0))
    assert seen and not any(seen)
