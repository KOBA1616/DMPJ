"""語彙パイロット第282弾: filter_same_name_as_event_card
（イベントのカードと同じ名前のカードを選ぶフィルタ）。

rejects の filter_same_name_as_event_card 純粋3件:
- c48-sec001 邪眼皇アレクサンドルIII世
  （自分の手札または墓地から光・水・闇の呪文を唱えた時、自分の山札から
  唱えた呪文と同じ名前の呪文を1枚、コストを支払わずに唱えてもよい）
- dm24ex3-rp1s10 巨進の超人
  （各ターンに一度、自分の他のクリーチャーが召喚によって出た時、
  それと同じ名前のクリーチャーを1体、自分のマナゾーンから出してもよい）
- dmrp02-006 サイバー・GG・ハルク
  （このクリーチャーまたは自分の他の水のクリーチャーが破壊された時、
  それと同じ名前のクリーチャーを1体、自分の手札から出してもよい）

3件とも不足は「イベントの対象カード（唱えた呪文／出たクリーチャー／
破壊されたクリーチャー）と同じ名前」というフィルタ条件だけ。
フィルタ値の式 {name_of: <参照>} は第140弾で導入済みで、
dm23-005（ラウンド265）で {name: {name_of: event.subject}} の
実戦先例がある（attack_unblocked の攻撃クリーチャー参照）。
本弾は新語彙・エンジン変更なしのイディオム弾で、残る3つの
イベント文脈（cast / 召喚による move / 破壊による move）でも
event.subject 参照がそのまま効くことを実挙動で固定する:

- 詠唱形（c48-sec001）: 誘発 {when: {event: cast, player: you,
  from: [hand, graveyard], subject: {filter: {types: [spell],
  civs: [light, water, darkness]}}}, if: {exists: {zone: bz,
  owner: you, other: true, filter: {race_has: ナイト}}},
  effect: [choose 山札全見 as: pile → choose {ref: pile,
  filter: {name: {name_of: event.subject}, types: [spell]}} as: found
  → if exists found → may [play_free {ref: found}]
  → move pile を山札へ → shuffle]}。
  cast レコードは from（唱えた元のゾーン。第226弾）を保持し、
  when の from はリスト指定で「いずれか」に照合される（events._match_when）。
  「自分のナイトが他に1枚でもあれば」は exists の other: true
  （発生源自身を除く。candidates の既存形）で表す。見つけた呪文の
  詠唱は pile（hold）からの play_free で、唱えた元のゾーンが
  deck/hold になるため、この誘発自体は再発火しない。
- 召喚形（dm24ex3-rp1s10）: 誘発 {once_per_turn: true,
  when: {event: move, to: bz, reason: summon,
  subject: {owner: you, other: true, filter: {types: [creature]}}},
  effect: [may [play_free {select: {zone: mana, owner: you,
  filter: {name: {name_of: event.subject}, types: [creature]},
  count: 1}}]]}。「召喚によって出た」は reason: summon の照合
  （第316弾 dm23ex3-tf03 の先例）。
- 破壊形（dmrp02-006）: 誘発 {when: {event: move, from: bz,
  to: graveyard, reason: destroy, subject: {owner: you,
  filter: {civs: [water], types: [creature]}}},
  effect: [may [play_free {select: {zone: hand, owner: you,
  filter: {name: {name_of: event.subject}, types: [creature]},
  count: 1}}]]}。破壊されたカードは墓地にあっても event.subject の
  参照先として特性（名前）を読める。

Rust: 3形とも _simple_trigger の対象外（when の subject が dict 形／
from リスト／once_per_turn／name_of 式フィルタ／play_free を含むため）
で、この能力を持つカードを含む対局は Python にフォールバックする。
新規 GameState フィールドなし（state.rs 変更なし）。スキーマ再生成なし
（name_of は第140弾で式の語彙に登録済み。when の subject フィルタは
parse_card のキー検証対象外＝第278弾の確認どおり）。
"""
import pytest

from dmsim.cards.defs import DefError, load_tables, parse_card
from dmsim.engine.rustcore import _simple_trigger
from tests.conftest import setup

TABLES = load_tables()

EXPECTED_798 = {
    "kind": "trigger",
    "when": {"event": "cast", "player": "you", "from": ["hand", "graveyard"],
             "subject": {"filter": {"types": ["spell"],
                                    "civs": ["light", "water", "darkness"]}}},
    "if": {"exists": {"zone": "bz", "owner": "you", "other": True,
                      "filter": {"race_has": "ナイト"}}},
    "effect": [
        {"op": "choose",
         "select": {"zone": "deck", "owner": "you", "look": True, "count": "all"},
         "as": "pile"},
        {"op": "choose",
         "select": {"ref": "pile",
                    "filter": {"name": {"name_of": "event.subject"},
                               "types": ["spell"]},
                    "count": 1},
         "as": "found"},
        {"op": "if", "cond": {"exists": {"ref": "found"}},
         "then": [{"op": "may",
                   "body": [{"op": "play_free", "select": {"ref": "found"}}]}]},
        {"op": "move", "select": {"ref": "pile", "count": "all"},
         "to": "deck", "reason": "put"},
        {"op": "shuffle", "player": "you"},
    ],
}

EXPECTED_801 = {
    "kind": "trigger", "once_per_turn": True,
    "when": {"event": "move", "to": "bz", "reason": "summon",
             "subject": {"owner": "you", "other": True,
                         "filter": {"types": ["creature"]}}},
    "effect": [
        {"op": "may",
         "body": [{"op": "play_free",
                   "select": {"zone": "mana", "owner": "you",
                              "filter": {"name": {"name_of": "event.subject"},
                                         "types": ["creature"]},
                              "count": 1}}]},
    ],
}

EXPECTED_803_A = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "you", "other": True,
                         "filter": {"civs": ["water"], "types": ["creature"]}}},
    "effect": [{"op": "draw", "count": 1}],
}

EXPECTED_803_B = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy",
             "subject": {"owner": "you",
                         "filter": {"civs": ["water"], "types": ["creature"]}}},
    "effect": [
        {"op": "may",
         "body": [{"op": "play_free",
                   "select": {"zone": "hand", "owner": "you",
                              "filter": {"name": {"name_of": "event.subject"},
                                         "types": ["creature"]},
                              "count": 1}}]},
    ],
}


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _count(e, zone, p, defn):
    return _defns(e, zone, p).count(defn)


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


class _Driver:
    """汎用ドライバ（第281弾のものと同形＋ may の受諾/辞退切替）。"""

    def __init__(self, play=None, choose=None, may=True):
        self.play = play
        self.choose = choose
        self.may = may
        self.seen = []

    def run(self, e, stop, limit=800):
        for _ in range(limit):
            d = e.advance()
            assert d is not None, "game ended"
            kind = d["kind"]
            keys = [o["key"] for o in d["options"]]
            self.seen.append(kind)
            if kind == "choose_cards" and self.choose is not None:
                ans = self.choose(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "main" and self.play is not None:
                ans = self.play(e, d)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            if kind == "declare_strigger":
                e.answer([])
            elif kind == "declare_sback":
                e.answer([])
            elif kind == "choose_breaker":
                e.answer([max(range(len(keys)), key=lambda i: int(keys[i].split(":")[1]))])
            elif kind == "choose_shields":
                e.answer(list(range(d.get("min", 0))))
            elif kind == "pay_mana":
                e.answer([0])
            elif kind == "yes_no":
                e.answer([keys.index("yes" if self.may else "no")])
            elif kind == "order_pending":
                e.answer([0])
            elif kind == "block":
                if "no_block" in keys:
                    e.answer([keys.index("no_block")])
                else:
                    e.answer(list(range(d.get("min", 0))))
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
            if stop(e):
                return
        raise AssertionError("limit reached")


def _play_n(key, n):
    state = {"done": 0}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and state["done"] < n:
            state["done"] += 1
            return [keys.index(key)]
        return None

    return play


def _play_once(key):
    return _play_n(key, 1)


def _choose_defn(defn):
    def choose(e, d):
        for i, o in enumerate(d["options"]):
            if defn in o["key"]:
                return [i]
        return None

    return choose


# ---------- parse / validation ----------

def test_pilot282_protos_parse():
    from dmsim.cards.defs import load_rules
    rules = load_rules()
    t798 = rules.cards["T798"]
    assert [ab for ab in t798.abilities if ab["kind"] == "trigger"] == [EXPECTED_798]
    t801 = rules.cards["T801"]
    assert [ab for ab in t801.abilities if ab["kind"] == "trigger"] == [EXPECTED_801]
    t803 = rules.cards["T803"]
    assert [ab for ab in t803.abilities if ab["kind"] == "trigger"] == [
        EXPECTED_803_A, EXPECTED_803_B]
    # 生の辞書でも3形とも parse できる
    for ab in (EXPECTED_798, EXPECTED_801, EXPECTED_803_A, EXPECTED_803_B):
        d = parse_card({"id": "TX282", "name": "x", "types": ["creature"],
                        "civs": ["water"], "cost": 5, "power": 2000,
                        "abilities": [ab]}, TABLES)
        assert [a for a in d.abilities if a["kind"] == "trigger"] == [ab]


def test_pilot282_unknown_filter_key_rejected():
    # ギャップ名そのものはフィルタキーではない（正表現は name: {name_of: ...}）
    with pytest.raises(DefError):
        parse_card({"id": "TX282", "name": "x", "types": ["creature"],
                    "civs": ["water"], "cost": 5, "power": 2000,
                    "abilities": [{"kind": "trigger",
                                   "when": {"event": "move", "to": "bz",
                                            "subject": "self"},
                                   "effect": [{"op": "play_free",
                                               "select": {"zone": "hand",
                                                          "filter": {"same_name_as_event": True},
                                                          "count": 1}}]}]},
                   TABLES)


def test_pilot282_not_rust_simple():
    # subject の dict 形・from リスト・once_per_turn・name_of 式フィルタ・
    # play_free を含むため _simple_trigger の対象外（Python フォールバック）
    for ab in (EXPECTED_798, EXPECTED_801, EXPECTED_803_A, EXPECTED_803_B):
        assert not _simple_trigger(dict(ab))


# ---------- 実挙動: 詠唱形 T798（c48-sec001 の形） ----------

def test_798_cast_from_hand_finds_same_name(rules):
    """手札から呪文を唱えると、山札の同名呪文をタダで唱える。
    墓地の T800 が2枚（手札から唱えた1枚＋見つけて唱えた1枚）になることで、
    ドローの順序に依らず無償詠唱が起きたことを固定する。"""
    e = setup(rules, {"bz": ["T798", "T799"], "hand": ["T800"],
                      "mana": ["T010", "T010"], "deck": ["T800", "T800"]},
              {"bz": ["T001"]})
    drv = _Driver(play=_play_once("play:T800"), choose=_choose_defn("T800"))
    drv.run(e, lambda ev: _count(ev, "graveyard", 0, "T800") == 2 and _quiet(ev))
    assert _count(e, "graveyard", 0, "T800") == 2
    assert len(e.zlist("hand", 0)) == 2          # 自分の効果1ドロー＋見つけた呪文の1ドロー
    assert "yes_no" in drv.seen                  # may の諮問があった（候補1枚だけだと choose は自動選択で決定が出ない）


def test_798_cast_from_graveyard_finds_same_name(rules):
    """墓地から唱えた時も誘発する（from: [hand, graveyard] の graveyard 側）。
    墓地から唱えた本元は grave_cast で山札の下へ行くため、墓地に残る
    T800 は見つけて唱えた1枚だけになる。"""
    e = setup(rules, {"bz": ["T798", "T799"], "graveyard": ["T800"],
                      "mana": ["T010", "T010"], "deck": ["T800", "T800"]},
              {"bz": ["T001"]})
    drv = _Driver(play=_play_once("play:T800:grave"), choose=_choose_defn("T800"))
    drv.run(e, lambda ev: _count(ev, "graveyard", 0, "T800") == 1
            and len(ev.zlist("hand", 0)) == 2 and _quiet(ev))
    assert _count(e, "graveyard", 0, "T800") == 1
    # 山札: 本元（山札の下）＋ spec 2枚のうち、効果ドローで手札へ1枚・
    # 見つけて唱えた1枚が墓地へ行き、残りは本元を含め1枚だけが山札に残る
    assert _count(e, "deck", 0, "T800") == 1
    assert len(e.zlist("hand", 0)) == 2


def test_798_no_other_knight_no_trigger(rules):
    """自分のナイトが「他に」いなければ誘発しない（T798 自身はナイトだが
    other: true で数えない）。"""
    e = setup(rules, {"bz": ["T798"], "hand": ["T800"],
                      "mana": ["T010", "T010"], "deck": ["T800", "T800"]},
              {"bz": ["T001"]})
    drv = _Driver(play=_play_once("play:T800"), choose=_choose_defn("T800"))
    drv.run(e, lambda ev: _count(ev, "graveyard", 0, "T800") == 1 and _quiet(ev))
    assert _count(e, "graveyard", 0, "T800") == 1
    assert "yes_no" not in drv.seen              # 誘発の may 諮問自体が無い
    assert len(e.zlist("hand", 0)) == 1          # 自分の効果の1ドローだけ


def test_798_decline_keeps_found_spell_in_deck(rules):
    """見つけた呪文を唱えない（may 辞退）と、山札に戻ってシャッフルされる。"""
    e = setup(rules, {"bz": ["T798", "T799"], "hand": ["T800"],
                      "mana": ["T010", "T010"], "deck": ["T800", "T800"]},
              {"bz": ["T001"]})
    drv = _Driver(play=_play_once("play:T800"), choose=_choose_defn("T800"),
                  may=False)
    drv.run(e, lambda ev: _count(ev, "graveyard", 0, "T800") == 1 and _quiet(ev))
    assert _count(e, "graveyard", 0, "T800") == 1
    # 山札の spec 2枚のうち1枚は効果ドローで手札へ、残り1枚は見つけたが
    # 唱えずに戻した。手札の1枚はそのドローした T800 本人
    assert _count(e, "deck", 0, "T800") == 1
    assert _count(e, "hand", 0, "T800") == 1
    assert len(e.zlist("hand", 0)) == 1


# ---------- 実挙動: 召喚形 T801（dm24ex3-rp1s10 の形） ----------

def test_801_summon_puts_same_name_from_mana(rules):
    """自分の他のクリーチャーが召喚によって出た時、同名をマナから出す。"""
    e = setup(rules, {"bz": ["T801"], "hand": ["T802"],
                      "mana": ["T802", "T001", "T001"]},
              {"bz": ["T001"]})
    drv = _Driver(play=_play_once("play:T802"), choose=_choose_defn("T802"))
    drv.run(e, lambda ev: _count(ev, "bz", 0, "T802") == 2 and _quiet(ev))
    assert _count(e, "bz", 0, "T802") == 2       # 召喚した1体＋マナから出た1体
    assert _count(e, "mana", 0, "T802") == 0


def test_801_once_per_turn(rules):
    """各ターンに一度だけ: 2体目の召喚では誘発せず、マナの同名は残る。"""
    e = setup(rules, {"bz": ["T801"], "hand": ["T802", "T802"],
                      "mana": ["T802", "T802", "T001", "T001", "T001", "T001"]},
              {"bz": ["T001"]})
    drv = _Driver(play=_play_n("play:T802", 2), choose=_choose_defn("T802"))
    drv.run(e, lambda ev: _count(ev, "bz", 0, "T802") == 3 and _quiet(ev))
    assert _count(e, "bz", 0, "T802") == 3       # 召喚2体＋マナから1体
    assert _count(e, "mana", 0, "T802") == 1
    assert drv.seen.count("yes_no") == 1


def test_801_opponent_summon_no_trigger(rules):
    """相手のクリーチャーが召喚によって出ても誘発しない（subject owner: you）。"""
    e = setup(rules, {"bz": ["T801"]},
              {"hand": ["T802"], "mana": ["T802", "T001", "T001"]})
    drv = _Driver(play=_play_once("play:T802"), choose=_choose_defn("T802"))
    drv.run(e, lambda ev: _count(ev, "bz", 1, "T802") == 1 and _quiet(ev))
    assert _count(e, "bz", 1, "T802") == 1
    assert _count(e, "mana", 1, "T802") == 1     # マナから出ていない
    assert "yes_no" not in drv.seen


# ---------- 実挙動: 破壊形 T803（dmrp02-006 の形） ----------

def test_803_destroyed_self_puts_same_name_from_hand(rules):
    """このクリーチャーが破壊された時、手札の同名クリーチャーを出す。
    event.subject（墓地にいる破壊されたカード）の名前が読めることの確認。"""
    e = setup(rules, {"bz": ["T803"], "hand": ["T803"]},
              {"hand": ["T056"], "mana": ["T056", "T056", "T056"]})
    drv = _Driver(play=_play_once("play:T056"), choose=_choose_defn("T803"))
    drv.run(e, lambda ev: _count(ev, "bz", 0, "T803") == 1
            and _count(ev, "graveyard", 0, "T803") == 1 and _quiet(ev))
    assert _count(e, "bz", 0, "T803") == 1       # 手札から出た同名
    assert _count(e, "graveyard", 0, "T803") == 1  # 破壊された本元
    assert _count(e, "hand", 0, "T803") == 0


def test_803_ally_enters_draws(rules):
    """自分の他の水のクリーチャーが出た時、1枚引く（dmrp02-006 の第1誘発）。"""
    e = setup(rules, {"bz": ["T803"], "hand": ["T598"],
                      "mana": ["T010", "T010", "T010", "T010", "T010"]},
              {"bz": ["T001"]})
    drv = _Driver(play=_play_once("play:T598"))
    drv.run(e, lambda ev: "T598" in _defns(ev, "bz", 0)
            and len(ev.zlist("hand", 0)) == 1 and _quiet(ev))
    assert "T598" in _defns(e, "bz", 0)
    assert len(e.zlist("hand", 0)) == 1          # 出した1枚が消え、ドローで1枚


def test_803_non_water_destroy_no_trigger(rules):
    """自分の水でないクリーチャーが破壊されても誘発しない（filter の civs）。"""
    e = setup(rules, {"bz": ["T803", "T001"], "hand": ["T803"]},
              {"hand": ["T056"], "mana": ["T056", "T056", "T056"]})
    drv = _Driver(play=_play_once("play:T056"), choose=_choose_defn("T001"))
    drv.run(e, lambda ev: _count(ev, "graveyard", 0, "T001") == 1 and _quiet(ev))
    assert _count(e, "graveyard", 0, "T001") == 1
    assert _count(e, "hand", 0, "T803") == 1     # 出ていない
    assert "yes_no" not in drv.seen
