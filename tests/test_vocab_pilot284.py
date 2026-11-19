"""語彙パイロット第284弾: once_per_turn_replacement
（各ターン1度しか使えない置換）

rejects の once_per_turn_replacement 純粋3件
（dm22rp2x-001 真実の精霊ヴァルペキュラ / dm22rp2x-050 霊魂と怨念の
ドライバー / dm23sd1-002 ボルシャック・モルナルク）。3件とも不足は
「置換効果に各ターン1度の回数制限を付ける語彙が無い」という点だけで、
partial の notes は「置換の相談経路は once_per_turn 印を見ない」と
書いている。しかし置換側の once_per_turn 対応は第196弾で入っており
（events._replacement が ab["once_per_turn"] を見て、選ばれた時にだけ
turn_counters へ印を付ける。辞退では消費しない）、第281弾＋ラウンド316で
dm26rp3-001 / dm24ex4-042 が once_per_turn つき置換の登録形として
実証済み。つまり本ファミリーはギャップ名のドリフトであり、本弾は
新語彙を足さず、3件それぞれの instead の形を実挙動で固定する
イディオム弾である:

- 形A（dm22rp2x-001）: 自分のクリーチャーまたはタマシードが破壊される時、
  かわりにその対象をシールド化する。
  {kind: replace, optional: true, once_per_turn: true,
   when: {event: move, from: bz, to: graveyard, reason: destroy,
          subject: {owner: you, filter: {types: [creature, tamaseed]}}},
   instead: [move {select: {ref: event.subject}, to: shield,
                   reason: charge}]}
  対象を {ref: event.subject} で指してシールド化する形は
  dm25ex3-rp1001（進化クリーチャー版）が登録先例。reason: charge は
  シールド化の標準（dmr06-020 等）。
- 形B（dm22rp2x-050）: 自分のクリーチャーが離れる時、かわりにタップして
  マナゾーンに置く。
  {kind: replace, optional: true, once_per_turn: true,
   when: {event: move, from: bz,
          subject: {owner: you, filter: {types: [creature]}}},
   instead: [move {select: {ref: event.subject}, to: mana,
                   reason: put, tapped: true}]}
  when は第281弾の基本形と同じ「離れる時」全般。原文が「タップして
  マナゾーンに置く」のため、move の tapped: true でタップしたまま
  マナゾーンに置く（dm03-005 の mana_put 形はタップ指定なし＝
  アンタップで置くので、そちらとは区別される）。
- 形C（dm23sd1-002）: 自分のアーマード・ドラゴンが破壊される時、
  かわりにファイアー・バードを1枚手札から出す。
  {kind: replace, optional: true, once_per_turn: true,
   when: {event: move, from: bz, to: graveyard, reason: destroy,
          subject: {owner: you, filter: {race_has: アーマード・ドラゴン}}},
   if: {exists: {zone: hand, owner: you,
                 filter: {race_has: ファイアー・バード}}},
   instead: [play_free {select: {zone: hand, owner: you,
                        filter: {race_has: ファイアー・バード},
                        count: 1}}]}
  if のゲートが要る: 手札にファイアー・バードが無い時に諮問して
  選んでしまうと、instead が空振りしてドラゴンが無条件で残って
  しまう（公式では使えない置換は選べない）。escape の
  if: exists（シールド）と同じ役割。
- 付随形（dm22rp2x-001 の第2能力）: 相手のターンのはじめに、自分の
  シールドが相手より多ければ相手のクリーチャーを2体タップする。
  {kind: trigger, when: {event: turn_start, player: opp},
   if: {cmp: [{count: {zone: shield, owner: you}}, ">",
              {count: {zone: shield, owner: opp}}]},
   effect: [tap {select: {zone: bz, owner: opp,
                 filter: {types: [creature]}, count: 2}}]}
  turn_start の player: opp と cmp の両辺 count は既存の組み合わせで、
  本弾で実挙動を固定する。

Rust: 3形とも optional + once_per_turn を含むため _simple_replace の
対象外（dm26rp3-001 等と同じ Python フォールバック）。新しい
GameState フィールドは無い（印は既存の turn_counters。state.rs 変更
なし）。スキーマ再生成なし（once_per_turn は置換のキーとして登録済み）。
"""
import pytest

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card
from dmsim.engine.rustcore import _simple_replace
from dmsim.engine.scenario import build
from tests.conftest import setup

TABLES = load_tables()

EXPECTED_A = {
    "kind": "replace", "optional": True, "once_per_turn": True,
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy",
             "subject": {"owner": "you",
                         "filter": {"types": ["creature", "tamaseed"]}}},
    "instead": [{"op": "move", "select": {"ref": "event.subject"},
                 "to": "shield", "reason": "charge"}],
}

EXPECTED_B = {
    "kind": "replace", "optional": True, "once_per_turn": True,
    "when": {"event": "move", "from": "bz",
             "subject": {"owner": "you",
                         "filter": {"types": ["creature"]}}},
    "instead": [{"op": "move", "select": {"ref": "event.subject"},
                 "to": "mana", "reason": "put", "tapped": True}],
}

EXPECTED_C = {
    "kind": "replace", "optional": True, "once_per_turn": True,
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy",
             "subject": {"owner": "you",
                         "filter": {"race_has": "アーマード・ドラゴン"}}},
    "if": {"exists": {"zone": "hand", "owner": "you",
                      "filter": {"race_has": "ファイアー・バード"}}},
    "instead": [{"op": "play_free",
                 "select": {"zone": "hand", "owner": "you",
                            "filter": {"race_has": "ファイアー・バード"},
                            "count": 1}}],
}

EXPECTED_A2 = {
    "kind": "trigger",
    "when": {"event": "turn_start", "player": "opp"},
    "if": {"cmp": [{"count": {"zone": "shield", "owner": "you"}}, ">",
                   {"count": {"zone": "shield", "owner": "opp"}}]},
    "effect": [{"op": "tap",
                "select": {"zone": "bz", "owner": "opp",
                           "filter": {"types": ["creature"]}, "count": 2}}],
}


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


class _Driver:
    """汎用ドライバ（第283弾のものに置換ポリシーの列を持たせたもの）。

    replace_seq: choose_replacement のたびに消費する "accept"/"decline"
    の列。尽きたら "accept"。
    """

    def __init__(self, play=None, replace_seq=(), choose=None):
        self.play = play
        self.replace_seq = list(replace_seq)
        self.choose = choose
        self.seen = []

    def run(self, e, stop, limit=1200):
        for _ in range(limit):
            if e.s.result is not None:
                return
            d = e.advance()
            if d is None:
                return
            kind = d["kind"]
            keys = [o["key"] for o in d["options"]]
            self.seen.append(kind)
            if kind == "choose_replacement":
                pol = self.replace_seq.pop(0) if self.replace_seq else "accept"
                if pol == "accept":
                    hit = [i for i, k in enumerate(keys) if k.startswith("replace:")]
                    assert hit, "置換の諮問に replace 選択肢が無い"
                    e.answer(hit[:1])
                else:
                    e.answer([keys.index("decline")])
                if stop(e):
                    return
                continue
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
                e.answer([keys.index("yes")])
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


def _play_times(key, times):
    seen = {"n": 0}

    def play(e, d):
        keys = [o["key"] for o in d["options"]]
        if key in keys and seen["n"] < times:
            seen["n"] += 1
            return [keys.index(key)]
        return None

    return play


def _choose_targets(*defns):
    """choose_cards で、指定した defn のカードを順に選ぶフック。"""
    queue = list(defns)

    def choose(e, d):
        if not queue:
            return None
        for i, o in enumerate(d["options"]):
            if e.cdef(o["cid"]).id == queue[0]:
                queue.pop(0)
                return [i]
        return None

    return choose


# ---------- parse / validation ----------

def test_pilot284_protos_parse():
    rules = load_rules()
    t806 = rules.cards["T806"]
    assert t806.abilities == [EXPECTED_A]
    t807 = rules.cards["T807"]
    assert t807.abilities == [EXPECTED_B]
    t808 = rules.cards["T808"]
    assert t808.abilities == [EXPECTED_C]
    t809 = rules.cards["T809"]
    assert t809.abilities == [EXPECTED_A2]
    # 生の辞書でも3形とも parse できる（once_per_turn は置換のキーとして受理される）
    for i, form in enumerate((EXPECTED_A, EXPECTED_B, EXPECTED_C)):
        d = parse_card({"id": f"TX284{i}", "name": "x", "types": ["creature"],
                        "civs": ["light"], "cost": 5, "power": 2000,
                        "abilities": [form]}, TABLES)
        assert d.abilities == [form]
    d = parse_card({"id": "TX284z", "name": "x", "types": ["creature"],
                    "civs": ["light"], "cost": 4, "power": 4000,
                    "abilities": [EXPECTED_A2]}, TABLES)
    assert d.abilities == [EXPECTED_A2]
    # 未知のキーワードは弾かれる（語彙は閉じている）
    with pytest.raises(DefError):
        parse_card({"id": "TX284c", "name": "x", "types": ["creature"],
                    "civs": ["light"], "cost": 5, "power": 2000,
                    "keywords": ["once_per_turn_replacement"]}, TABLES)


def test_pilot284_not_rust_simple():
    # optional + once_per_turn を含むため _simple_replace の対象外
    # （dm26rp3-001 / dm24ex4-042 と同じ Python フォールバック）
    assert not _simple_replace(dict(EXPECTED_A))
    assert not _simple_replace(dict(EXPECTED_B))
    assert not _simple_replace(dict(EXPECTED_C))


# ---------- 実挙動: 形A（T806、シールド化） ----------

def test_806_protects_ally_once_per_turn_and_resets_next_turn(rules):
    """味方をシールド化して守る。同ターン2体目は諮問されず破壊され、
    次の相手ターンには再び諮問される（印はターンごとに消える）。
    味方役は T810（シールドの filler T001 と defn が重ならない）。
    相手のマナは6枚（T056 は1ターンに2枚まで）にして、3枚目を
    次の相手ターンに回す。"""
    e = setup(rules, {"bz": ["T806", "T810", "T810", "T810"],
                      "mana": ["T001"] * 6},
              {"hand": ["T056", "T056", "T056"], "mana": ["T056"] * 6})
    drv = _Driver(play=_play_times("play:T056", 3),
                  choose=_choose_targets("T810", "T810", "T810"))
    drv.run(e, lambda ev: _defns(ev, "shield", 0).count("T810") == 2
            and _defns(ev, "graveyard", 0).count("T810") == 1 and _quiet(ev))
    assert drv.seen.count("choose_replacement") == 2
    assert _defns(e, "shield", 0).count("T810") == 2     # 1体目と3体目
    assert _defns(e, "graveyard", 0).count("T810") == 1  # 2体目は通常破壊
    assert "T806" in _defns(e, "bz", 0)


def test_806_decline_does_not_consume(rules):
    """辞退しても印は付かない: 同ターン次の破壊で再び諮問される。"""
    e = setup(rules, {"bz": ["T806", "T810", "T810"], "mana": ["T001"] * 6},
              {"hand": ["T056", "T056"], "mana": ["T056"] * 6})
    drv = _Driver(play=_play_times("play:T056", 2), replace_seq=["decline"],
                  choose=_choose_targets("T810", "T810"))
    drv.run(e, lambda ev: _defns(ev, "shield", 0).count("T810") == 1
            and _defns(ev, "graveyard", 0).count("T810") == 1 and _quiet(ev))
    assert drv.seen.count("choose_replacement") == 2
    assert _defns(e, "graveyard", 0).count("T810") == 1  # 辞退した1体目
    assert _defns(e, "shield", 0).count("T810") == 1     # 受諾した2体目


def test_806_protects_tamaseed_ally(rules):
    """対象はタマシードも含む: タマシードが破壊される時もシールド化する。"""
    e = setup(rules, {"bz": ["T806", "T811"], "mana": ["T001"] * 6},
              {"hand": ["T812"], "mana": ["T008"] * 3})
    drv = _Driver(play=_play_times("play:T812", 1),
                  choose=_choose_targets("T811"))
    drv.run(e, lambda ev: "T811" in _defns(ev, "shield", 0) and _quiet(ev))
    assert drv.seen.count("choose_replacement") == 1
    assert "T811" in _defns(e, "shield", 0)
    assert "T811" not in _defns(e, "graveyard", 0)


def test_806_protects_self(rules):
    """発生源自身が破壊される時も諮問される（subject は self を含む）。"""
    e = setup(rules, {"bz": ["T806"], "mana": ["T001"] * 6},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_times("play:T056", 1),
                  choose=_choose_targets("T806"))
    drv.run(e, lambda ev: "T806" in _defns(ev, "shield", 0) and _quiet(ev))
    assert drv.seen.count("choose_replacement") == 1
    assert "T806" in _defns(e, "shield", 0)
    assert "T806" not in _defns(e, "graveyard", 0)


def test_806_does_not_protect_opponent(rules):
    """相手のクリーチャーの破壊には諮問されない。"""
    e = setup(rules, {"bz": ["T806"], "hand": ["T056"], "mana": ["T056"] * 3},
              {"bz": ["T001"], "mana": ["T001"] * 3})
    drv = _Driver(play=_play_times("play:T056", 1),
                  choose=_choose_targets("T001"))
    drv.run(e, lambda ev: "T001" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T001" in _defns(e, "graveyard", 1)
    assert "choose_replacement" not in drv.seen


# ---------- 実挙動: 形B（T807、タップしてマナへ） ----------

def test_807_bounce_becomes_tapped_mana(rules):
    """バウンスされる代わりに、タップしたままマナゾーンに置かれる。
    味方役は T810（初期マナの T001 と defn が重ならない）。
    観測の罠: 置換が相手ターンに解決すると、次の自分のターン開始の
    アンタップでタップが消えてから次の決定が提示される。相手の獣に
    攻撃決定を残し、相手ターン内の決定で観測する。"""
    e = setup(rules, {"bz": ["T807", "T810"], "mana": ["T001"] * 3},
              {"bz": ["T001"], "hand": ["T140"], "mana": ["T140"] * 3})

    def _tapped_in_mana(ev):
        return any(ev.cdef(c).id == "T810" and ev.s.cards[c].tapped
                   for c in ev.zlist("mana", 0))

    drv = _Driver(play=_play_times("play:T140", 1),
                  choose=_choose_targets("T810"))
    drv.run(e, lambda ev: ev.s.turn == 2 and _tapped_in_mana(ev))
    assert drv.seen.count("choose_replacement") == 1
    assert "T810" in _defns(e, "mana", 0)
    assert "T810" not in _defns(e, "hand", 0)
    cid = next(c for c in e.zlist("mana", 0) if e.cdef(c).id == "T810")
    assert e.s.cards[cid].tapped is True


def test_807_destroy_also_mana_and_once_per_turn(rules):
    """破壊も「離れる時」に含まれる。同ターン2体目は諮問されず墓地へ。"""
    e = setup(rules, {"bz": ["T807", "T810", "T810"], "mana": ["T001"] * 3},
              {"hand": ["T056", "T056"], "mana": ["T056"] * 6})
    drv = _Driver(play=_play_times("play:T056", 2),
                  choose=_choose_targets("T810", "T810"))
    drv.run(e, lambda ev: "T810" in _defns(ev, "mana", 0)
            and "T810" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert drv.seen.count("choose_replacement") == 1
    assert _defns(e, "mana", 0).count("T810") == 1     # 守った1体だけ
    assert _defns(e, "graveyard", 0).count("T810") == 1


def test_807_decline_bounce_goes_hand(rules):
    """辞退すれば通常どおり手札に戻る。"""
    e = setup(rules, {"bz": ["T807", "T810"], "mana": ["T001"] * 3},
              {"hand": ["T140"], "mana": ["T140"] * 3})
    drv = _Driver(play=_play_times("play:T140", 1), replace_seq=["decline"],
                  choose=_choose_targets("T810"))
    drv.run(e, lambda ev: "T810" in _defns(ev, "hand", 0) and _quiet(ev))
    assert drv.seen.count("choose_replacement") == 1
    assert "T810" in _defns(e, "hand", 0)
    assert "T810" not in _defns(e, "mana", 0)


# ---------- 実挙動: 形C（T808、身代わり召喚） ----------

def test_808_summons_bird_and_dragon_stays(rules):
    """アーマード・ドラゴンが破壊される時、手札のファイアー・バードが
    代わりに出て、ドラゴンはバトルゾーンに残る。"""
    e = setup(rules, {"bz": ["T808", "T808"], "hand": ["T810"],
                      "mana": ["T001"] * 3},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_times("play:T056", 1),
                  choose=_choose_targets("T808"))
    drv.run(e, lambda ev: "T810" in _defns(ev, "bz", 0) and _quiet(ev))
    assert drv.seen.count("choose_replacement") == 1
    assert _defns(e, "bz", 0).count("T808") == 2   # 対象のドラゴンは残る
    assert "T810" in _defns(e, "bz", 0)            # 身代わりが出る
    assert "T810" not in _defns(e, "hand", 0)


def test_808_no_bird_no_consult(rules):
    """手札にファイアー・バードが無ければ諮問自体が起きず、通常破壊される
    （if ゲートが無いと空振りでドラゴンが残ってしまう）。"""
    e = setup(rules, {"bz": ["T808"], "mana": ["T001"] * 3},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_times("play:T056", 1),
                  choose=_choose_targets("T808"))
    drv.run(e, lambda ev: "T808" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert "T808" in _defns(e, "graveyard", 0)
    assert "choose_replacement" not in drv.seen


def test_808_decline_then_second_consult(rules):
    """辞退では消費しない: 1体目は破壊され、同ターン2体目で再び諮問される。"""
    e = setup(rules, {"bz": ["T808", "T808"], "hand": ["T810"],
                      "mana": ["T001"] * 3},
              {"hand": ["T056", "T056"], "mana": ["T056"] * 6})
    drv = _Driver(play=_play_times("play:T056", 2), replace_seq=["decline"],
                  choose=_choose_targets("T808", "T808"))
    drv.run(e, lambda ev: "T810" in _defns(ev, "bz", 0)
            and "T808" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert drv.seen.count("choose_replacement") == 2
    assert _defns(e, "graveyard", 0).count("T808") == 1  # 辞退した1体目
    assert _defns(e, "bz", 0).count("T808") == 1         # 守られた2体目
    assert "T810" in _defns(e, "bz", 0)


def test_808_does_not_protect_non_dragon(rules):
    """アーマード・ドラゴンでない味方の破壊には諮問されない。"""
    e = setup(rules, {"bz": ["T808", "T001"], "hand": ["T810"],
                      "mana": ["T001"] * 3},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_times("play:T056", 1),
                  choose=_choose_targets("T001"))
    drv.run(e, lambda ev: "T001" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert "T001" in _defns(e, "graveyard", 0)
    assert "choose_replacement" not in drv.seen


# ---------- 実挙動: 付随形（T809、相手ターン頭のタップ） ----------

def _duel809(rules, shield0, shield1):
    return build(rules, {"p0": {"bz": ["T809"], "shield": shield0},
                         "p1": {"bz": ["T001", "T001", "T001"],
                                "shield": shield1},
                         "filler": "T001", "seed": 1, "deck_size": 20})


def test_809_taps_two_at_opponent_turn_start(rules):
    """相手のターンのはじめ、自分のシールドが多ければ相手の獣2体がタップする。"""
    e = _duel809(rules, ["T001"] * 5, ["T001"] * 2)
    drv = _Driver()
    drv.run(e, lambda ev: ev.s.turn >= 2
            and sum(1 for c in ev.bz_tops(1) if ev.s.cards[c].tapped) == 2
            and _quiet(ev))
    tapped = [c for c in e.bz_tops(1) if e.s.cards[c].tapped]
    assert len(tapped) == 2


def test_809_no_tap_when_shields_not_more(rules):
    """対照: 自分のシールドが相手以下なら発火しない。"""
    e = _duel809(rules, ["T001"] * 2, ["T001"] * 5)
    drv = _Driver()
    drv.run(e, lambda ev: ev.s.turn >= 2 and _quiet(ev))
    tapped = [c for c in e.bz_tops(1) if e.s.cards[c].tapped]
    assert tapped == []
