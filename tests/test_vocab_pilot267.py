"""語彙パイロット第267弾: rinne（輪廻∞）。

「輪廻∞：このカードの呪文側を、バトルゾーンに置いたまま唱えてもよい
（コストは支払う）。そうした時、自分の《天地命動 バラギアラ》１体につき、
自分の山札の上から１枚をマナゾーンに置く。」

新語彙は面項目 **`rinne: true`**（ツインパクトのクリーチャー側に付ける。
第226弾の grave_cast と同型）。エンジン側の変更は turn.py のみ:

- _play_options: バトルゾーンにある自分のツインパクト・クリーチャーで
  クリーチャー側に rinne があれば、呪文側を通常コストで唱える選択肢
  `play:<defn>:1:rinne` を出す（墓地からの grave_cast 分岐と同型）。
- h_play: rinne の時はカードを保留へ移さず、面も変えず、呪文解決後に
  墓地へ置かない。cast イベントには `from: bz` と `via: rinne` を載せる。
- マナ・チャージは誘発のイディオムで表す:
  `{kind: trigger, when: {event: cast, via: rinne, subject: self},
    effect: [repeat {times: {count: {zone: bz, owner: you,
    filter: {name_has: <名>}}}} [move {select: {zone: deck, count: 1},
    to: mana, reason: put}]]}`。
  手札からの通常詠唱や cast_face（スマッシュ・バースト。via 無し）では
  誘発しない。誘発は cast イベントの待機窓で解決するため、呪文の解決の
  後にチャージされる（第226弾の再唱イディオムと同じ順序）。

呪文側の型（すべて既存語彙の組み合わせ）:
- 輪廻虹災: choose {from_top: 5, look: true, count: all} で表向きにし、
  文明ごとに if {exists: {ref: pile, zone: deck, filter: {civs: [X],
  cost_le: 9}}} → may [play_free]（dm24bd1-007 の「各文明１枚ずつは
  文明ごとに分解」と同型）。残りは move {ref: pile, zone: deck,
  count: all, to: deck, position: bottom, order: choose}。
- 輪廻暴炎: destroy {total_power_le: 3000}（第144弾）＋ grant。
- 天上天下輪廻独尊: modify {power, grant: [world_breaker], dynamic: true}
  ＋ modify {must_attack_creature: true, dynamic: true,
  duration: until_next_own_turn_start}（第194弾）。
- 輪廻暴冥: 既存語彙のみ（-4000 は modify、墓地からは move）。
"""
import pytest
from tests.conftest import setup

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card

TABLES = load_tables()


def _defns(e, zone, p):
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _by_defn(e, zone, p):
    return {e.cdef(c).id: c for c in e.zlist(zone, p)}


def _drive(e, stop, choose=None, play=None, yes_no=None, order=None, limit=800):
    """汎用ドライバ（第266弾のものを流用し、order_cards フックを追加）。"""
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
        if kind == "order_cards" and order is not None:
            ans = order(e, d)
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
    """main で指定の play キーを1回出す play フック。"""
    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and not seen.get("opt"):
            seen["opt"] = True
            return [keys.index(key)]
        return None
    return play


def _pick_defn(*defns):
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

def test_pilot267_protos_parse():
    rules = load_rules()
    t740 = rules.cards["T740"]
    assert t740.faces[0].rinne is True
    assert t740.faces[0].name == "試験バラギアラ"
    assert t740.faces[1].name == "試験輪廻虹災"
    assert t740.faces[1].civs == ["light", "water", "darkness", "fire", "nature"]
    assert t740.faces[1].cost == 10
    trigs = [ab for ab in t740.faces[0].abilities if ab["kind"] == "trigger"]
    assert len(trigs) == 2
    assert trigs[0]["when"] == {"event": "move", "to": "bz", "subject": "self",
                                "reason": "summon"}
    assert trigs[0]["effect"] == [{"op": "untap",
                                   "select": {"zone": "mana", "owner": "you",
                                              "count": "all"}}]
    assert trigs[1]["when"] == {"event": "cast", "via": "rinne", "subject": "self"}
    rep = trigs[1]["effect"][0]
    assert rep["op"] == "repeat"
    assert rep["times"] == {"count": {"zone": "bz", "owner": "you",
                                      "filter": {"name_has": "試験バラギアラ"}}}
    assert rep["body"] == [{"op": "move",
                            "select": {"zone": "deck", "owner": "you", "from_top": 1},
                            "to": "mana", "reason": "put"}]
    # 輪廻虹災の型: choose 1回＋文明ごとの if/may/play_free 5回＋残りの move
    sp = t740.faces[1].spell
    assert sp[0]["op"] == "choose" and sp[0]["as"] == "pile"
    assert sp[0]["select"] == {"zone": "deck", "owner": "you", "from_top": 5,
                               "look": True, "count": "all"}
    assert sp[0]["reveal"] is True
    assert [o["op"] for o in sp[1:6]] == ["if"] * 5
    assert [o["cond"]["exists"]["filter"]["civs"]
            for o in sp[1:6]] == [["light"], ["water"], ["darkness"],
                                  ["fire"], ["nature"]]
    for o in sp[1:6]:
        assert o["then"][0]["op"] == "may"
        pf = o["then"][0]["body"][0]
        assert pf["op"] == "play_free" and pf["select"]["count"] == 1
        assert pf["select"]["filter"]["cost_le"] == 9
    assert sp[6] == {"op": "move",
                     "select": {"ref": "pile", "zone": "deck", "count": "all"},
                     "to": "deck", "reason": "put", "position": "bottom",
                     "order": "choose"}
    assert rules.cards["T741"].rinne is False
    assert rules.cards["T742"].faces[0].rinne is True
    assert rules.cards["T742"].faces[1].spell == [{"op": "draw", "count": 1}]
    base = {"id": "TX", "name": "x", "types": ["creature"],
            "civs": ["fire"], "cost": 3, "power": 1000, "races": ["テスト"]}
    parse_card(dict(base, rinne=True), TABLES)
    with pytest.raises(DefError):
        parse_card(dict(base, rinne="yes"), TABLES)


# ---------- rinne option ----------

def test_rinne_option_offered_only_from_bz_with_mana(rules):
    """バトルゾーンの rinne 持ちだけに呪文側の選択肢が出る。マナ不足では出ない。
    （main は選択肢が pass だけだと自動回答されるため _play_options を直接見る）"""
    e = setup(rules, {"bz": ["T742"], "mana": ["T005"] * 3}, {})
    keys = [o["key"] for o in e._play_options(0)]
    assert "play:T742:1:rinne" in keys
    assert "play:T742:1" not in keys  # 手札に無いので通常の呪文側は出ない
    e = setup(rules, {"bz": ["T742"], "mana": ["T005"] * 2}, {})
    keys = [o["key"] for o in e._play_options(0)]
    assert "play:T742:1:rinne" not in keys
    e = setup(rules, {"bz": ["T741"], "mana": ["T005"] * 3}, {})
    keys = [o["key"] for o in e._play_options(0)]
    assert not [k for k in keys if k.endswith(":rinne")]


# ---------- rinne cast ----------

def test_rinne_cast_basic(rules):
    """輪廻∞で唱える: コストを払い、呪文が解決し、クリーチャーは場に残り、
    バラギアラ1体ぶん山札の上から1枚がマナへ行く。"""
    e = setup(rules, {"bz": ["T742"], "mana": ["T005"] * 3}, {})
    seen = {}
    _drive(e, lambda e: len(e.zlist("hand", 0)) == 1 and len(e.zlist("mana", 0)) == 4,
           play=_play_key("play:T742:1:rinne", seen))
    assert seen["opt"]
    assert "T742" in _defns(e, "bz", 0)
    assert e.s.cards[_by_defn(e, "bz", 0)["T742"]].face == 0
    assert "T742" not in _defns(e, "graveyard", 0)
    assert e.s.turn_counters.get("casts:0") == 1
    assert len(e.zlist("deck", 0)) == 13  # 初期15（仕様4枚＋フィラー20−配札10−シールド5）- 呪文のドロー1 - チャージ1
    tapped = [c for c in e.zlist("mana", 0) if e.s.cards[c].tapped]
    assert len(tapped) == 3  # 払った3枚だけタップ。チャージ分はアンタップ


def test_rinne_charge_counts_two_baragiaras(rules):
    """バラギアラが2体いればチャージは2枚。"""
    e = setup(rules, {"bz": ["T742", "T741"], "mana": ["T005"] * 3}, {})
    seen = {}
    _drive(e, lambda e: len(e.zlist("hand", 0)) == 1 and len(e.zlist("mana", 0)) == 5,
           play=_play_key("play:T742:1:rinne", seen))
    assert "T742" in _defns(e, "bz", 0)
    assert "T741" in _defns(e, "bz", 0)


def test_rinne_cip_untaps_mana(rules):
    """召喚によって出た時、マナをすべてアンタップする。"""
    e = setup(rules, {"hand": ["T742"], "mana": ["T001"] * 9}, {})
    seen = {}
    _drive(e, lambda e: "T742" in _defns(e, "bz", 0)
           and not any(e.s.cards[c].tapped for c in e.zlist("mana", 0)),
           play=_play_key("play:T742:0", seen))
    assert seen["opt"]


def test_hand_cast_no_charge(rules):
    """手札から呪文側を普通に唱えてもチャージは起きない。唱えた後は墓地へ。"""
    e = setup(rules, {"hand": ["T742"], "mana": ["T005"] * 3}, {})
    seen = {}
    _drive(e, lambda e: "T742" in _defns(e, "graveyard", 0),
           play=_play_key("play:T742:1", seen))
    assert len(e.zlist("mana", 0)) == 3
    assert len(e.zlist("hand", 0)) == 1  # 呪文のドロー1枚


# ---------- 輪廻虹災 ----------

def test_rinne_spell_kousei(rules):
    """輪廻虹災: 上から5枚を表向きにし、各文明1枚ずつ実行し、残りを山札の下へ。
    その後、バラギアラ1体ぶんチャージされる（呪文の解決の後）。"""
    e = setup(rules, {"bz": ["T740"],
                      "mana": ["T004", "T009", "T008", "T005", "T001"] * 2,
                      "deck": ["T005", "T008", "T009", "T004", "T015"]}, {})
    seen = {}
    _drive(e, lambda e: "T015" in _defns(e, "deck", 0)
           and len(e.zlist("mana", 0)) == 11,
           choose=_pick_defn("T004"), play=_play_key("play:T740:1:rinne", seen))
    assert seen["opt"]
    assert "T740" in _defns(e, "bz", 0)
    for dn in ("T004", "T009", "T008", "T005"):
        assert dn in _defns(e, "bz", 0), dn
    # 残りの T015 は山札の一番下へ
    assert e.zlist("deck", 0)[-1] == _by_defn(e, "deck", 0)["T015"]
    # 払った10枚はタップ、チャージの1枚はアンタップ
    tapped = [c for c in e.zlist("mana", 0) if e.s.cards[c].tapped]
    assert len(tapped) == 10


def test_rinne_spell_rest_order(rules):
    """残りが2枚あれば「好きな順序で山札の下に置く」の order_cards が出る。
    水の may を断ると T009 が残り、T015 と並べる。"""
    e = setup(rules, {"bz": ["T740"],
                      "mana": ["T004", "T009", "T008", "T005", "T001"] * 2,
                      "deck": ["T005", "T008", "T009", "T004", "T015"]}, {})
    seen = {}
    n_yes_no = {"n": 0}

    def yes_no(e, d):
        n_yes_no["n"] += 1
        return [1] if n_yes_no["n"] == 2 else [0]  # 2番目（水）だけ断る

    def order(e, d):
        keys = [o["key"] for o in d["options"]]
        # T009 を先に、T015 を後に（一番下が T015）
        return [[i for i, o in enumerate(d["options"])
                 if e.s.cards[o["cid"]].defn == dn][0]
                for dn in ("T009", "T015")]

    _drive(e, lambda e: len(e.zlist("mana", 0)) == 11
           and e.zlist("deck", 0)[-1] == _by_defn(e, "deck", 0).get("T015", -1),
           choose=_pick_defn("T004"), play=_play_key("play:T740:1:rinne", seen),
           yes_no=yes_no, order=order)
    assert "T009" not in _defns(e, "bz", 0)
    assert "T009" in _defns(e, "deck", 0)
    deck = e.zlist("deck", 0)
    assert e.s.cards[deck[-1]].defn == "T015"
    assert e.s.cards[deck[-2]].defn == "T009"
