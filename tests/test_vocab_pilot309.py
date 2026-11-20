"""語彙パイロット第309弾: rinne_infinity（ギャップ名ドリフト）。

dmrp21-tr2 天地命動 バラギアラ / 輪廻暴冥 はギャップ名
`rinne_infinity` で残っているが、機構そのものは第267弾の
面項目 **`rinne: true`**＋ cast `via: rinne` 誘発イディオムで
実装済み（第267弾の対象は dm26rp3-s011 輪廻虹災 /
dmex08-258 輪廻暴炎 / dmrp08-mh05 天上天下輪廻独尊で、
ギャップ名は `rinne`。tr2 は輪廻暴冥の印刷で、共通文言は
同一だがギャップ名だけが違ったため対象外になっていた）。

本弾は新規語彙・エンジン変更なし。tr2 の全条項が第267弾の
確立形で書けることを、暴冥型プロト T956 で固定する:

- クリーチャー面: rinne: true ＋ CIP
  {event: move, to: bz, subject: self, reason: summon}
  → untap {zone: mana, owner: you, count: all} ＋
  {event: cast, via: rinne, subject: self} →
  repeat {times: {count: {zone: bz, owner: you,
  filter: {name_has: 天地命動 バラギアラ}}}} の
  move {from_top: 1} → mana（T740 / 登録済み
  dm26rp3-s011 と同型）。
- 呪文面（輪廻暴冥、闇コスト6、S・トリガー）:
  choose {zone: bz, owner: opp, count: 1} as x →
  modify {ref: x, power: -4000, duration: end_of_turn} ＋
  move {zone: graveyard, owner: you,
  filter: {types: [creature], cost_le: 5}, count: 1}
  → bz, reason: put（墓地からは move、第267弾の設計どおり）。

partial の faces はプレースホルダ（x / y、火コスト1）で
実データではない。実形は公式データ（rp21）から取る:
クリーチャー面 = 自然コスト9・パワー17000・
マスター・ハザード/グランセクト、呪文面 = 闇コスト6。
"""
from tests.conftest import setup

from dmsim.cards.defs import load_rules, load_tables

TABLES = load_tables()


def _defns(e, zone, p):
    return sorted(e.cdef(c).id for c in e.zlist(zone, p)
                  if zone != "bz" or e.s.cards[c].controller == p)


def _by_defn(e, zone, p):
    return {e.cdef(c).id: c for c in e.zlist(zone, p)
            if zone != "bz" or e.s.cards[c].controller == p}


def _drive(e, stop, choose=None, play=None, limit=800):
    """汎用ドライバ（第267弾のものを流用）。"""
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
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


def _play_key(key, seen):
    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and not seen.get("opt"):
            seen["opt"] = True
            return [keys.index(key)]
        return None
    return play


def _pick_defn(*defns):
    def choose(e, d):
        for dn in defns:
            idx = [i for i, o in enumerate(d["options"])
                   if e.s.cards[o["cid"]].defn == dn]
            if idx:
                return idx[:1]
        return None
    return choose


# ---------- parse / 確立形 ----------

def test_pilot309_proto_parse():
    rules = load_rules()
    t956 = rules.cards["T956"]
    f0, f1 = t956.faces
    assert f0.rinne is True
    assert f0.name == "試験バラギアラ"
    assert f0.keywords == ["triple_breaker"]
    trigs = [ab for ab in f0.abilities if ab["kind"] == "trigger"]
    assert len(trigs) == 2
    assert trigs[0]["when"] == {"event": "move", "to": "bz", "subject": "self",
                                "reason": "summon"}
    assert trigs[0]["effect"] == [{"op": "untap",
                                   "select": {"zone": "mana", "owner": "you",
                                              "count": "all"}}]
    assert trigs[1]["when"] == {"event": "cast", "via": "rinne",
                                "subject": "self"}
    rep = trigs[1]["effect"][0]
    assert rep["op"] == "repeat"
    assert rep["times"] == {"count": {"zone": "bz", "owner": "you",
                                      "filter": {"name_has": "試験バラギアラ"}}}
    assert rep["body"] == [{"op": "move",
                            "select": {"zone": "deck", "owner": "you",
                                       "from_top": 1},
                            "to": "mana", "reason": "put"}]
    # 輪廻暴冥の型: S・トリガー、闇コスト6、choose → -4000 → 墓地から出す
    assert f1.name == "試験輪廻暴冥"
    assert f1.civs == ["darkness"] and f1.cost == 6
    assert f1.keywords == ["s_trigger"]
    sp = f1.spell
    assert [o["op"] for o in sp] == ["choose", "modify", "move"]
    assert sp[0]["select"] == {"zone": "bz", "owner": "opp",
                               "filter": {"types": ["creature"]}, "count": 1}
    assert sp[0]["as"] == "x"
    assert sp[1] == {"op": "modify", "select": {"ref": "x"},
                     "mod": {"power": -4000}, "duration": "end_of_turn"}
    assert sp[2] == {"op": "move",
                     "select": {"zone": "graveyard", "owner": "you",
                                "filter": {"types": ["creature"],
                                           "cost_le": 5},
                                "count": 1},
                     "to": "bz", "reason": "put"}


# ---------- rinne cast（暴冥） ----------

def test_rinne_boumei_cast(rules):
    """輪廻∞で暴冥を唱える: -4000 で相手獣が落ち、墓地のコスト5以下が
    出て、カードは場に残り、バラギアラ1体ぶんチャージされる。"""
    e = setup(rules, {"bz": ["T956"], "mana": ["T008"] * 6,
                      "graveyard": ["T001", "T741"]},
              {"bz": ["T004"]})
    seen = {}
    _drive(e, lambda e: "T001" in _defns(e, "bz", 0)
           and len(e.zlist("mana", 0)) == 7,
           choose=_pick_defn("T004", "T001"),
           play=_play_key("play:T956:1:rinne", seen))
    assert seen["opt"]
    # 唱えたカードは場に残り、面も変わらず、墓地へ行かない
    assert "T956" in _defns(e, "bz", 0)
    assert e.s.cards[_by_defn(e, "bz", 0)["T956"]].face == 0
    assert "T956" not in _defns(e, "graveyard", 0)
    # -4000: パワー3000 → -1000 で破壊され相手の墓地へ
    assert "T004" not in _defns(e, "bz", 1)
    assert "T004" in _defns(e, "graveyard", 1)
    # 墓地からはコスト5以下の T001 だけが出る（コスト9の T741 は残る）
    assert "T001" in _defns(e, "bz", 0)
    assert "T741" in _defns(e, "graveyard", 0)
    # 支払い6枚タップ＋チャージ1枚（アンタップ）
    tapped = [c for c in e.zlist("mana", 0) if e.s.cards[c].tapped]
    assert len(tapped) == 6
    assert e.s.turn_counters.get("casts:0") == 1


def test_rinne_boumei_charge_counts_two(rules):
    """バラギアラが2体いればチャージは2枚。"""
    e = setup(rules, {"bz": ["T956", "T741"], "mana": ["T008"] * 6,
                      "graveyard": ["T001"]},
              {"bz": ["T004"]})
    seen = {}
    _drive(e, lambda e: "T001" in _defns(e, "bz", 0)
           and len(e.zlist("mana", 0)) == 8,
           choose=_pick_defn("T004", "T001"),
           play=_play_key("play:T956:1:rinne", seen))
    assert "T741" in _defns(e, "bz", 0)


def test_hand_cast_boumei_no_charge(rules):
    """手札から暴冥を普通に唱えてもチャージは起きない。唱えた後は墓地へ。"""
    e = setup(rules, {"hand": ["T956"], "mana": ["T008"] * 6,
                      "graveyard": ["T001"]},
              {"bz": ["T004"]})
    seen = {}
    _drive(e, lambda e: "T956" in _defns(e, "graveyard", 0)
           and "T001" in _defns(e, "bz", 0),
           choose=_pick_defn("T004", "T001"),
           play=_play_key("play:T956:1", seen))
    assert seen["opt"]
    assert len(e.zlist("mana", 0)) == 6  # チャージなし
    assert "T004" in _defns(e, "graveyard", 1)


def test_rinne_boumei_cip_untaps_mana(rules):
    """召喚によって出た時、マナをすべてアンタップする。"""
    e = setup(rules, {"hand": ["T956"], "mana": ["T001"] * 9}, {})
    seen = {}
    _drive(e, lambda e: "T956" in _defns(e, "bz", 0)
           and not any(e.s.cards[c].tapped for c in e.zlist("mana", 0)),
           play=_play_key("play:T956:0", seen))
    assert seen["opt"]
