"""語彙パイロット第283弾: eternal_kappa（エターナル・Κ）

rejects の eternal_kappa 8件（dm23ex3-or1 / dm23ex3-s06 / dm23ex3-027 /
dm24bd6-002 / dm24bd6-011 / dm24bd6-024 / dm24rp3-td01 / dm24sp2-003）。
共通条項は「エターナル・Κ（このクリーチャーが離れる時、かわりに自分の
マナゾーンにある裏向きのカードを３枚、表向きにしてもよい）」で、dm23ex3-or1
だけが「または自分がゲームに負ける時」も含む変形（クリスターナル・Κ）。

不足はこの置換条項だけで、機構は既存の置換（第277弾 true_escape の
「離れる時」全般・任意形、第281弾 leave_replacement_shield_to_hand）と
「表向きにする」操作（第148弾の op flip_up。docstring に「エターナル・Κ 等」
とあるとおりマナゾーンの裏向きカードを表向きに戻す）で実証済み。
本弾は新語彙としてキーワード eternal_kappa を1つ足すだけのイディオム弾で、
次の形を確立する:

- 基本形（7件）:
  {kind: replace, optional: true,
   when: {event: move, from: bz, subject: self},
   if: {cmp: [{count: {zone: mana, owner: you,
                       filter: {face_down: true}}}, ">=", 3]},
   instead: [flip_up {zone: mana, owner: you,
                      filter: {face_down: true}, count: 3}]}
  when は true_escape と同じ「離れる時」全般（行き先・理由を問わない）。
  if は true_escape と同じ cmp/count ゲートで、裏向きマナが3枚ある時だけ
  諮問する（count＋filter の形は第23弾の FD2 が先例）。instead の flip_up
  は裏向きマナを表向きに戻す既存 op（第148弾）で、イベントを作らないため
  「表向きで置かれた時」は誘発しない（向きを変えただけ）。
- 負ける時形（dm23ex3-or1 のみ）: キーワードとは別に、置換能力を1つ足す。
  {kind: replace, optional: true, when: {event: lose},
   if / instead は基本形と同じ}
  敗北の置換は第188弾の lose_replace 経路（_lose_candidates が bz の
  カードを走査し、敗北する側に諮問する。辞退の選択肢は常にある）。
  「クリスターナル・Κ」は水晶ソウル持ちゼニスの変形名だが、機構は
  エターナル・Κと同一のため同じキーワードで表す。

Rust: 基本形・負ける時形とも optional を含むため _simple_replace の対象外
（escape / true_escape と同じ）で、この能力を持つカードを含む対局は
Python にフォールバックする。新しい GameState フィールドは無い
（state.rs 変更なし）。スキーマはキーワード enum の追加で再生成した。
"""
import pytest

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card
from dmsim.engine.rustcore import _simple_replace
from dmsim.engine.scenario import build
from tests.conftest import setup

TABLES = load_tables()

EXPECTED_KAPPA = {
    "kind": "replace", "optional": True,
    "when": {"event": "move", "from": "bz", "subject": "self"},
    "if": {"cmp": [{"count": {"zone": "mana", "owner": "you",
                             "filter": {"face_down": True}}}, ">=", 3]},
    "instead": [{"op": "flip_up",
                 "select": {"zone": "mana", "owner": "you",
                            "filter": {"face_down": True}, "count": 3}}],
}

EXPECTED_LOSE = {
    "kind": "replace", "optional": True,
    "when": {"event": "lose"},
    "if": {"cmp": [{"count": {"zone": "mana", "owner": "you",
                             "filter": {"face_down": True}}}, ">=", 3]},
    "instead": [{"op": "flip_up",
                 "select": {"zone": "mana", "owner": "you",
                            "filter": {"face_down": True}, "count": 3}}],
}


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


def _face_down_count(e, p):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].face_down)


def _set_face_down(e, p, n):
    """マナゾーンの先頭 n 枚を裏向きにする（第145・154弾と同じ直接設定）。"""
    for c in e.zlist("mana", p)[:n]:
        e.s.cards[c].face_down = True


class _Driver:
    """汎用ドライバ（第281弾のものに lose_replace を足したもの）。"""

    def __init__(self, play=None, replace="accept", lose="accept", choose=None):
        self.play = play
        self.replace = replace
        self.lose = lose
        self.choose = choose
        self.seen = []

    def run(self, e, stop, limit=800):
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
                if self.replace == "accept":
                    hit = [i for i, k in enumerate(keys) if k.startswith("replace:")]
                    assert hit, "置換の諮問に replace 選択肢が無い"
                    e.answer(hit[:1])
                else:
                    e.answer([keys.index("decline")])
                if stop(e):
                    return
                continue
            if kind == "lose_replace":
                if self.lose == "accept":
                    hit = [i for i, k in enumerate(keys) if k.startswith("lose_replace:")]
                    assert hit, "敗北置換の諮問に lose_replace 選択肢が無い"
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


def _play_once(key):
    return _play_times(key, 1)


def _choose_targets(*defns):
    """choose_cards で、指定した defn のカードを順に選ぶフック。

    対象選択以外の choose_cards（裏向きマナの3枚選び等）には None を返し、
    ドライバの既定処理に任せる。
    """
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


def _duel(rules, p0, p1, deck_size=20):
    return build(rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                         "deck_size": deck_size,
                         "deck_exact": [True, False]})


# ---------- parse / validation ----------

def test_pilot283_protos_parse():
    rules = load_rules()
    t804 = rules.cards["T804"]
    assert "eternal_kappa" in t804.keywords
    abs_k = [ab for ab in t804.abilities if ab.get("keyword") == "eternal_kappa"]
    assert len(abs_k) == 1
    assert {k: abs_k[0][k] for k in EXPECTED_KAPPA} == EXPECTED_KAPPA
    t805 = rules.cards["T805"]
    assert "eternal_kappa" in t805.keywords
    abs_k = [ab for ab in t805.abilities if ab.get("keyword") == "eternal_kappa"]
    assert len(abs_k) == 1
    assert {k: abs_k[0][k] for k in EXPECTED_KAPPA} == EXPECTED_KAPPA
    lose = [ab for ab in t805.abilities
            if ab["kind"] == "replace" and ab["when"] == {"event": "lose"}]
    assert lose == [EXPECTED_LOSE]
    # 生の辞書でもキーワード展開される
    d = parse_card({"id": "TX283", "name": "x", "types": ["creature"],
                    "civs": ["light"], "cost": 5, "power": 2000,
                    "keywords": ["eternal_kappa"]}, TABLES)
    assert [ab for ab in d.abilities if ab.get("keyword") == "eternal_kappa"]
    # 生の辞書でも負ける時形は parse できる
    d2 = parse_card({"id": "TX283b", "name": "x", "types": ["creature"],
                     "civs": [], "cost": 8, "power": 8000,
                     "keywords": ["eternal_kappa"],
                     "abilities": [EXPECTED_LOSE]}, TABLES)
    assert [ab for ab in d2.abilities
            if ab["kind"] == "replace" and ab["when"] == {"event": "lose"}] == [EXPECTED_LOSE]
    # 未知のキーワードは弾かれる（語彙は閉じている）
    with pytest.raises(DefError):
        parse_card({"id": "TX283c", "name": "x", "types": ["creature"],
                    "civs": ["light"], "cost": 5, "power": 2000,
                    "keywords": ["eternal_kappa_x"]}, TABLES)


def test_pilot283_not_rust_simple():
    # optional を含むため _simple_replace の対象外
    # （escape / true_escape と同じ Python フォールバック）
    assert not _simple_replace(dict(EXPECTED_KAPPA))
    assert not _simple_replace(dict(EXPECTED_LOSE))


# ---------- 実挙動: T804（基本形） ----------

def test_804_protects_self_from_destroy(rules):
    """破壊される時、裏向きマナ3枚を表向きにして残る。"""
    e = setup(rules, {"bz": ["T804"], "mana": ["T001"] * 6},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    _set_face_down(e, 0, 3)
    assert _face_down_count(e, 0) == 3
    drv = _Driver(play=_play_once("play:T056"), choose=_choose_targets("T804"))
    drv.run(e, lambda ev: "T804" in _defns(ev, "bz", 0)
            and _face_down_count(ev, 0) == 0 and _quiet(ev))
    assert "T804" in _defns(e, "bz", 0)
    assert "T804" not in _defns(e, "graveyard", 0)
    assert _face_down_count(e, 0) == 0
    assert drv.seen.count("choose_replacement") == 1


def test_804_declined_destroyed(rules):
    """辞退すれば通常どおり破壊され、裏向きマナは残る。"""
    e = setup(rules, {"bz": ["T804"], "mana": ["T001"] * 6},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    _set_face_down(e, 0, 3)
    drv = _Driver(play=_play_once("play:T056"), replace="decline",
                  choose=_choose_targets("T804"))
    drv.run(e, lambda ev: "T804" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert "T804" in _defns(e, "graveyard", 0)
    assert _face_down_count(e, 0) == 3
    assert drv.seen.count("choose_replacement") == 1


def test_804_protects_self_from_bounce(rules):
    """「離れる時」全般: バウンス（手札に戻す効果）も置換できる。"""
    e = setup(rules, {"bz": ["T804"], "mana": ["T001"] * 6},
              {"hand": ["T140"], "mana": ["T140"] * 3})
    _set_face_down(e, 0, 3)
    drv = _Driver(play=_play_once("play:T140"), choose=_choose_targets("T804"))
    drv.run(e, lambda ev: "T804" in _defns(ev, "bz", 0)
            and _face_down_count(ev, 0) == 0 and _quiet(ev))
    assert "T804" in _defns(e, "bz", 0)
    assert "T804" not in _defns(e, "hand", 0)
    assert drv.seen.count("choose_replacement") == 1


def test_804_unavailable_with_two_face_down(rules):
    """裏向きマナ2枚では3枚払えないため、諮問自体が起きず破壊される。"""
    e = setup(rules, {"bz": ["T804"], "mana": ["T001"] * 6},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    _set_face_down(e, 0, 2)
    drv = _Driver(play=_play_once("play:T056"), choose=_choose_targets("T804"))
    drv.run(e, lambda ev: "T804" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert "T804" in _defns(e, "graveyard", 0)
    assert _face_down_count(e, 0) == 2
    assert "choose_replacement" not in drv.seen


def test_804_chooses_three_of_five_face_down(rules):
    """裏向きマナ5枚の時は3枚だけを選び、残り2枚は裏向きのまま。"""
    e = setup(rules, {"bz": ["T804"], "mana": ["T001"] * 6},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    _set_face_down(e, 0, 5)
    assert _face_down_count(e, 0) == 5
    drv = _Driver(play=_play_once("play:T056"), choose=_choose_targets("T804"))
    drv.run(e, lambda ev: "T804" in _defns(ev, "bz", 0)
            and _face_down_count(ev, 0) == 2 and _quiet(ev))
    assert "T804" in _defns(e, "bz", 0)
    assert _face_down_count(e, 0) == 2
    assert drv.seen.count("choose_replacement") == 1


# ---------- 実挙動: T805（負ける時形） ----------

def test_805_protects_self_from_destroy(rules):
    """T805 もキーワードの離れる時置換で破壊から残る（追加能力との共存）。"""
    e = setup(rules, {"bz": ["T805"], "mana": ["T001"] * 6},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    _set_face_down(e, 0, 3)
    drv = _Driver(play=_play_once("play:T056"), choose=_choose_targets("T805"))
    drv.run(e, lambda ev: "T805" in _defns(ev, "bz", 0)
            and _face_down_count(ev, 0) == 0 and _quiet(ev))
    assert "T805" in _defns(e, "bz", 0)
    assert drv.seen.count("choose_replacement") == 1


def test_805_lose_replaced_by_flipping_mana(rules):
    """山札切れで負ける時、裏向きマナ3枚を表向きにして負けない。"""
    e = _duel(rules, {"bz": ["T805"], "mana": ["T001"] * 6, "deck": []},
              {"bz": ["T001"]})
    _set_face_down(e, 0, 3)
    assert _face_down_count(e, 0) == 3
    drv = _Driver()
    drv.run(e, lambda ev: ev.s.result is None
            and _face_down_count(ev, 0) == 0 and _quiet(ev))
    assert e.s.result is None
    assert "T805" in _defns(e, "bz", 0)
    assert _face_down_count(e, 0) == 0
    assert drv.seen.count("lose_replace") == 1


def test_805_lose_declined_loses(rules):
    """敗北置換を辞退すれば山札切れで負ける。"""
    e = _duel(rules, {"bz": ["T805"], "mana": ["T001"] * 6, "deck": []},
              {"bz": ["T001"]})
    _set_face_down(e, 0, 3)
    drv = _Driver(lose="decline")
    drv.run(e, lambda ev: ev.s.result is not None)
    assert e.s.result is not None and e.s.result["winner"] == 1
    assert e.s.result["reason"] == "deck_out"
    assert _face_down_count(e, 0) == 3
    assert drv.seen.count("lose_replace") == 1


def test_805_lose_unavailable_with_two_face_down(rules):
    """裏向きマナ2枚では敗北置換は諮問されず、山札切れで負ける。"""
    e = _duel(rules, {"bz": ["T805"], "mana": ["T001"] * 6, "deck": []},
              {"bz": ["T001"]})
    _set_face_down(e, 0, 2)
    drv = _Driver()
    drv.run(e, lambda ev: ev.s.result is not None)
    assert e.s.result is not None and e.s.result["winner"] == 1
    assert e.s.result["reason"] == "deck_out"
    assert _face_down_count(e, 0) == 2
    assert "lose_replace" not in drv.seen
