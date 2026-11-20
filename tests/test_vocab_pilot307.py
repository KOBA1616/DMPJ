"""語彙パイロット第307弾（2026-11-20）の検証。

exlife_shield_left_any（純粋1件: dm26ex2-mc009 不敬合成王
ロマティックダム・アルキング）。詰まりは同カードの誘発
「自分の『EXライフ』シールドが離れた時」— 第190弾の
when.subject {exlife_of: self} は特定クリーチャーへの紐付け照合のみで、
filter の exlife は離脱後の実カード（紐付けは移動で外れる）しか見ない
ため、どのクリーチャーのものでもよい「自分のEXライフシールド全般」を
subject に書けなかった（ラウンド328で提出後に登録を取り消して差し戻し）。

本弾の追加語彙は最小の1点: when.subject の exlife_of に値 "any" を
認める（owner: "any" と同じ流儀）。照合は移動記録の LKI が保持する
移動前の紐付け（exlife_of が None でないこと）だけを見る。エンジン
変更は events._subject_match の分岐追加のみで、スキーマ（when.subject
は無制約）・defs 検証・新規フィールドは変更なし。

確立形（T945）:
- 誘発: {event: move, from: shield, subject: {owner: you,
  exlife_of: any}}
- 効果: 下のカード1枚を墓地へ（move {select: {under_of: self,
  count: 1}, as: buried}、メテオバーンの先例形）→ それが進化でない
  クリーチャーなら墓地から出す（if {exists: {ref: buried,
  filter: {types: [creature], not_types: [evolution]}}} +
  play_free {select: {ref: buried}}）
"""
from conftest import setup

from dmsim.cards.defs import load_tables, parse_card
from tests._conv_cache import proto_card

TABLES = load_tables()
PROTOS = ("T945", "T946", "T947")

TRIGGER = {"kind": "trigger",
           "when": {"event": "move", "from": "shield",
                    "subject": {"owner": "you", "exlife_of": "any"}},
           "effect": [
               {"op": "move",
                "select": {"under_of": "self", "count": 1},
                "to": "graveyard", "reason": "put", "as": "buried"},
               {"op": "if",
                "cond": {"exists": {"ref": "buried",
                                    "filter": {"types": ["creature"],
                                               "not_types": ["evolution"]}}},
                "then": [{"op": "play_free",
                          "select": {"ref": "buried"}}]},
           ]}


def _bz(e, p, defn):
    return [c for c in e.zlist("bz", p) if e.s.cards[c].defn == defn
            and e.s.cards[c].controller == p]


def _shield_linked_to(e, p, creature_cid):
    """p のシールドのうち、クリーチャー creature_cid に紐付いた
    EXライフシールドの cid。"""
    for c in e.zlist("shield", p):
        lo = e.s.cards[c].exlife_of
        if lo is not None and lo[0] == creature_cid:
            return c
    return None


def _run(e, handler, limit=1200, done=None):
    for _ in range(limit):
        if e.s.result is not None or (done and done()):
            return
        d = e.advance()
        if d is None:
            return
        r = handler(e, d)
        if r is not None:
            e.answer(r)
            continue
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["min"] == 0:
            e.answer([])
        else:
            e.answer(list(range(d["min"])))


def _hook(st, plays=(), evo_base=None, casts=(), shield_pick=None):
    """plays / casts: (player, key) を一度だけ実行。shield_pick は
    choose_shields で選ぶシールド cid を返す関数 (e) -> cid | None。"""
    def handler(e, d):
        p = d["player"]
        keys = [o["key"] for o in d["options"]]
        for pl, key in plays:
            if d["kind"] == "main" and p == pl and key in keys \
                    and ("play", pl, key) not in st:
                st[("play", pl, key)] = True
                return [keys.index(key)]
        for cast in casts:
            pl, key = cast[0], cast[1]
            gate = cast[2] if len(cast) > 2 else None
            if d["kind"] == "main" and p == pl and key in keys \
                    and ("cast", pl, key) not in st \
                    and (gate is None or gate(e)):
                st[("cast", pl, key)] = True
                return [keys.index(key)]
        if d["kind"] == "choose_evo_source" and evo_base is not None:
            for i, o in enumerate(d["options"]):
                if o.get("cid") == evo_base:
                    return [i]
        if d["kind"] == "pay_mana":
            return [0]
        if d["kind"] == "yes_no":
            return [0]
        if d["kind"] == "choose_shields" and shield_pick is not None \
                and not st.get("picked"):
            want = shield_pick(e)
            if want is not None:
                for i, o in enumerate(d["options"]):
                    if o.get("cid") == want:
                        st["picked"] = want
                        return [i]
        return None
    return handler


# ---------------------------------------------------------------- parse

def test_parse_protos():
    for cid in PROTOS:
        parse_card(proto_card(cid), TABLES)
    d945 = parse_card(proto_card("T945"), TABLES)
    assert d945.keywords == ["ex_life"]
    trigs = [a for a in d945.abilities if a.get("kind") == "trigger"]
    assert trigs == [TRIGGER]


# ------------------------------------------ 他のクリーチャーのシールド

def test_other_creatures_exlife_shield_fires_and_resummons(rules):
    """T847（監視者ではない自軍獣）の EXライフシールドが割れる →
    監視者 T945 の誘発が発火し、下の T946 が墓地を経て場に戻る。"""
    e = setup(rules,
              {"hand": ["T847", "T945"], "bz": ["T946"],
               "mana": ["T034"] * 5 + ["T030"] * 6},
              {"hand": ["T850"], "mana": ["T082"]})
    st = {}
    base = e.zlist("bz", 0)[0]
    c847 = None

    def pick(e):
        c = _bz(e, 0, "T847")
        return _shield_linked_to(e, 0, c[0]) if c else None

    def done():
        w = _bz(e, 0, "T945")
        b = _bz(e, 0, "T946")
        return bool(w and b and e.s.cards[b[0]].top_of == -1
                    and e.s.cards[w[0]].under == [])

    _run(e, _hook(st, plays=[(0, "play:T847"), (0, "play:T945")],
                  evo_base=base, casts=[(1, "play:T850")],
                  shield_pick=pick),
         done=done)
    assert done()
    shield_cid = st["picked"]
    assert e.s.cards[shield_cid].zone == "hand"      # 割れたシールドは手札へ
    assert _bz(e, 0, "T847")                          # 紐付け先の獣は無傷
    assert not [c for c in e.zlist("graveyard", 0)
                if e.s.cards[c].defn == "T946"]       # 墓地には残らない


# ------------------------------------------ 監視者自身のシールド

def test_watchers_own_exlife_shield_fires(rules):
    """監視者自身の EXライフシールドが割れても発火する（any は self を含む）。"""
    e = setup(rules,
              {"hand": ["T945"], "bz": ["T946"], "mana": ["T030"] * 6},
              {"hand": ["T850"], "mana": ["T082"]})
    st = {}
    base = e.zlist("bz", 0)[0]

    def pick(e):
        w = _bz(e, 0, "T945")
        return _shield_linked_to(e, 0, w[0]) if w else None

    def done():
        w = _bz(e, 0, "T945")
        b = _bz(e, 0, "T946")
        return bool(w and b and e.s.cards[b[0]].top_of == -1
                    and e.s.cards[w[0]].under == [])

    _run(e, _hook(st, plays=[(0, "play:T945")], evo_base=base,
                  casts=[(1, "play:T850")], shield_pick=pick),
         done=done)
    assert done()
    assert e.s.cards[st["picked"]].zone == "hand"


# ------------------------------------------ 判別: 普通のシールド

def test_normal_shield_does_not_fire(rules):
    """EXライフでない普通のシールドが割れても発火しない。"""
    e = setup(rules,
              {"hand": ["T945"], "bz": ["T946"], "mana": ["T030"] * 6},
              {"hand": ["T850"], "mana": ["T082"]})
    st = {}
    base = e.zlist("bz", 0)[0]

    def pick(e):
        for c in e.zlist("shield", 0):
            if e.s.cards[c].exlife_of is None:
                return c
        return None

    def done():
        return bool(st.get("picked")) and \
            e.s.cards[st["picked"]].zone == "hand"

    _run(e, _hook(st, plays=[(0, "play:T945")], evo_base=base,
                  casts=[(1, "play:T850")], shield_pick=pick),
         done=done)
    assert done()
    w = _bz(e, 0, "T945")[0]
    assert e.s.cards[base].top_of == w               # 下のカードは動かない
    assert e.s.cards[w].under == [base]
    assert not [c for c in e.zlist("graveyard", 0)
                if e.s.cards[c].defn == "T946"]


# ------------------------------------------ 判別: 相手のシールド

def test_opponents_exlife_shield_does_not_fire(rules):
    """相手の EXライフシールドが離れても発火しない（owner: you）。"""
    e = setup(rules,
              {"hand": ["T945", "T850"], "bz": ["T946"],
               "mana": ["T030"] * 6 + ["T082"]},
              {"hand": ["T847"], "mana": ["T034"] * 5})
    st = {}
    base = e.zlist("bz", 0)[0]

    def pick(e):
        c = _bz(e, 1, "T847")
        return _shield_linked_to(e, 1, c[0]) if c else None

    def done():
        return bool(st.get("picked")) and \
            e.s.cards[st["picked"]].zone == "hand"

    _run(e, _hook(st, plays=[(0, "play:T945"), (1, "play:T847")],
                  evo_base=base,
                  casts=[(0, "play:T850", lambda e: bool(_bz(e, 1, "T847")))],
                  shield_pick=pick),
         done=done)
    assert done()
    assert e.s.cards[st["picked"]].controller == 1
    w = _bz(e, 0, "T945")[0]
    assert e.s.cards[base].top_of == w               # 下のカードは動かない
    assert e.s.cards[w].under == [base]


# ------------------------------------------ 下が進化クリーチャー

def test_evolution_under_card_stays_in_graveyard(rules):
    """下のカードが進化クリーチャーなら、墓地に置かれるだけで出ない。"""
    e = setup(rules,
              {"hand": ["T945"], "bz": ["T947"], "mana": ["T030"] * 6},
              {"hand": ["T850"], "mana": ["T082"]})
    st = {}
    base = e.zlist("bz", 0)[0]

    def pick(e):
        w = _bz(e, 0, "T945")
        return _shield_linked_to(e, 0, w[0]) if w else None

    def done():
        return bool(_bz(e, 0, "T945")) and \
            e.s.cards[base].zone == "graveyard"

    _run(e, _hook(st, plays=[(0, "play:T945")], evo_base=base,
                  casts=[(1, "play:T850")], shield_pick=pick),
         done=done)
    assert done()
    assert not _bz(e, 0, "T947")                      # 場には戻らない
    assert e.s.cards[_bz(e, 0, "T945")[0]].under == []


# ------------------------------------------ 下にカードが無い場合

def test_no_under_card_is_noop(rules):
    """下にカードが無い監視者でも、誘発は空振りで安全に終わる。"""
    e = setup(rules,
              {"hand": ["T847"], "bz": ["T945"], "mana": ["T034"] * 5},
              {"hand": ["T850"], "mana": ["T082"]})
    st = {}

    def pick(e):
        c = _bz(e, 0, "T847")
        return _shield_linked_to(e, 0, c[0]) if c else None

    def done():
        return bool(st.get("picked")) and \
            e.s.cards[st["picked"]].zone == "hand"

    _run(e, _hook(st, plays=[(0, "play:T847")],
                  casts=[(1, "play:T850")], shield_pick=pick),
         done=done)
    assert done()
    assert _bz(e, 0, "T945")                          # 監視者は無傷で残る
    assert len(e.zlist("graveyard", 0)) == 0          # 何も墓地へ行かない
