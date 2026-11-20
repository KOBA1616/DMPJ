"""語彙パイロット第298弾: same_name_cast
（最新版形: 同名呪文を表向きにし、シャッフルしてから唱える）。

rejects の same_name_cast 純粋2件は同一カード
邪眼皇アレクサンドルIII世の2印刷:
- dm26ex4-cho010（最新版・canon）: 自分の手札または墓地から光・水・闇の
  呪文を唱えた時、自分の他のナイトがあれば、自分の山札を見る。その中から、
  唱えた呪文と同じ名前の呪文を1枚表向きにし、山札をシャッフルしてから
  その呪文をコストを支払わずに唱えてもよい。
- c48-sec001（旧印刷）: 本文は「選んで唱え、その後シャッフル」の順で、
  第282弾の詠唱形イディオム（T798）で解決済み・partial に銀行済み。
  submit は最新版 ID でしか登録できないため、本行は cho010 の登録時に
  alias として畳み込まれる（ラウンド317の記録）。

本弾の問いは最新版形の手順差だけ:
(1) 見つけた呪文を「表向きにする」= choose の reveal: true（バンドC1 U39。
    束縛したカードを全プレイヤーに公開し、s.pub に reveal 記録が残る）。
(2) シャッフルが詠唱より前、しかも見つけた場合に限る
    （c48 形は末尾の無条件シャッフル。最新版は「表向きにし、シャッフル
    してから…唱えてもよい」の連鎖なので、見つからなければシャッフルも
    起きない形に置く）。
(3) シャッフルを挟んでも found の ref（cid, gen）は不変で、
    play_free {ref: found} がそのまま効く（shuffle は山札リストの
    並べ替えのみで生成を進めない）。
(4) pile の戻し move は不要（choose はカードを動かさず ref を束縛する
    だけ。c48 形の move {ref: pile → deck} は「見た束を戻す」手続きで、
    最新版形では公開→シャッフルの連鎖に吸収される）。

新語彙・エンジン変更なしのドリフト弾。プロト T899（T799 = 他のナイト、
T800 = 同名呪文・grave_cast を流用）。

Rust: when の subject が dict 形／from リスト／name_of 式フィルタ／
play_free を含むため _simple_trigger の対象外（第282弾と同形）。
新規 GameState フィールドなし（state.rs 変更なし）。スキーマ再生成なし
（reveal は choose の既存引数、shuffle は既存 op）。
"""
import pytest

from dmsim.cards.defs import DefError, load_tables, parse_card
from dmsim.engine.rustcore import _simple_trigger
from tests.conftest import setup

TABLES = load_tables()

EXPECTED_899 = {
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
         "as": "found", "reveal": True},
        {"op": "if", "cond": {"exists": {"ref": "found"}},
         "then": [
             {"op": "shuffle", "player": "you"},
             {"op": "may",
              "body": [{"op": "play_free", "select": {"ref": "found"}}]},
         ]},
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


def _pub(e, n0, kind, defn=None, zone=None):
    """setup 直後（n0 以降）の公開記録から kind 一致を順序どおりに返す。"""
    out = []
    for r in e.s.pub:
        if r["n"] < n0 or r.get("kind") != kind:
            continue
        if defn is not None and r.get("defn") != defn:
            continue
        if zone is not None and r.get("zone") != zone:
            continue
        out.append(r)
    return out


class _Driver:
    """汎用ドライバ（第282弾のものと同形。may の受諾/辞退切替つき）。"""

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

def test_pilot298_proto_parse():
    from dmsim.cards.defs import load_rules
    rules = load_rules()
    t899 = rules.cards["T899"]
    assert [ab for ab in t899.abilities if ab["kind"] == "trigger"] == [EXPECTED_899]
    # 生の辞書でも parse できる
    d = parse_card({"id": "TX298", "name": "x", "types": ["creature"],
                    "civs": ["darkness"], "cost": 7, "power": 6000,
                    "abilities": [EXPECTED_899]}, TABLES)
    assert [a for a in d.abilities if a["kind"] == "trigger"] == [EXPECTED_899]


def test_pilot298_unknown_op_arg_rejected():
    # reveal は choose の引数であって select のキーではない
    bad = {"kind": "trigger",
           "when": {"event": "cast", "player": "you",
                    "subject": {"filter": {"types": ["spell"]}}},
           "effect": [{"op": "choose",
                       "select": {"zone": "deck", "owner": "you",
                                  "reveal": True, "count": "all"},
                       "as": "pile"}]}
    with pytest.raises(DefError):
        parse_card({"id": "TX298", "name": "x", "types": ["creature"],
                    "civs": ["darkness"], "cost": 7, "power": 6000,
                    "abilities": [bad]}, TABLES)


def test_pilot298_not_rust_simple():
    # subject の dict 形・from リスト・name_of 式フィルタ・play_free を
    # 含むため _simple_trigger の対象外（Python フォールバック。第282弾と同形）
    assert not _simple_trigger(dict(EXPECTED_899))


# ---------- 実挙動: 最新版形 T899（dm26ex4-cho010 の形） ----------

def test_899_cast_from_hand_reveals_shuffles_then_casts(rules):
    """手札から呪文を唱えると、山札の同名呪文が (1) 表向きにされ、
    (2) 山札がシャッフルされ、(3) その後で無償詠唱される。
    公開記録の順序 reveal（山札の T800）< shuffle で (1)<(2) を固定し、
    墓地の T800 が2枚になることでシャッフル後も ref が効いて
    詠唱できたことを固定する。"""
    e = setup(rules, {"bz": ["T899", "T799"], "hand": ["T800"],
                      "mana": ["T010", "T010"], "deck": ["T800", "T800"]},
              {"bz": ["T001"]})
    n0 = len(e.s.pub)
    drv = _Driver(play=_play_once("play:T800"), choose=_choose_defn("T800"))
    drv.run(e, lambda ev: _count(ev, "graveyard", 0, "T800") == 2 and _quiet(ev))
    assert _count(e, "graveyard", 0, "T800") == 2
    assert len(e.zlist("hand", 0)) == 2          # 自分の効果1ドロー＋見つけた呪文の1ドロー
    assert "yes_no" in drv.seen                  # may の諮問があった
    reveals = _pub(e, n0, "reveal", defn="T800", zone="deck")
    shuffles = _pub(e, n0, "shuffle")
    assert reveals and shuffles
    assert reveals[0]["n"] < shuffles[0]["n"]     # 公開 → シャッフルの順


def test_899_cast_from_graveyard_finds_same_name(rules):
    """墓地から唱えた時も誘発する（from: [hand, graveyard] の graveyard 側）。
    墓地から唱えた本元は grave_cast で山札の下へ行くため、墓地に残る
    T800 は見つけて唱えた1枚だけになる。"""
    e = setup(rules, {"bz": ["T899", "T799"], "graveyard": ["T800"],
                      "mana": ["T010", "T010"], "deck": ["T800", "T800"]},
              {"bz": ["T001"]})
    n0 = len(e.s.pub)
    drv = _Driver(play=_play_once("play:T800:grave"), choose=_choose_defn("T800"))
    drv.run(e, lambda ev: _count(ev, "graveyard", 0, "T800") == 1
            and len(ev.zlist("hand", 0)) == 2 and _quiet(ev))
    assert _count(e, "graveyard", 0, "T800") == 1
    assert _count(e, "deck", 0, "T800") == 1
    assert len(e.zlist("hand", 0)) == 2
    assert _pub(e, n0, "reveal", defn="T800", zone="deck")
    assert _pub(e, n0, "shuffle")


def test_899_decline_after_reveal_and_shuffle(rules):
    """見つけた呪文を唱えない（may 辞退）場合でも、公開とシャッフルは
    諮問より前に済んでいる（最新版形の連鎖）。呪文はシャッフルされた
    山札の中に残る。"""
    e = setup(rules, {"bz": ["T899", "T799"], "hand": ["T800"],
                      "mana": ["T010", "T010"], "deck": ["T800", "T800"]},
              {"bz": ["T001"]})
    n0 = len(e.s.pub)
    drv = _Driver(play=_play_once("play:T800"), choose=_choose_defn("T800"),
                  may=False)
    drv.run(e, lambda ev: _count(ev, "graveyard", 0, "T800") == 1 and _quiet(ev))
    assert _count(e, "graveyard", 0, "T800") == 1
    # 山札の spec 2枚のうち1枚は効果ドローで手札へ、残り1枚は見つけて
    # 公開したが唱えずに山札へ戻った（シャッフル済み）
    assert _count(e, "deck", 0, "T800") == 1
    assert _count(e, "hand", 0, "T800") == 1
    assert len(e.zlist("hand", 0)) == 1
    reveals = _pub(e, n0, "reveal", defn="T800", zone="deck")
    shuffles = _pub(e, n0, "shuffle")
    assert reveals and shuffles
    assert reveals[0]["n"] < shuffles[0]["n"]


def test_899_no_same_name_in_deck_no_reveal_no_shuffle(rules):
    """山札に同名呪文が無ければ、公開もシャッフルも詠唱諮問も無い
    （シャッフルは見つけた場合の連鎖の中にある）。"""
    e = setup(rules, {"bz": ["T899", "T799"], "hand": ["T800"],
                      "mana": ["T010", "T010"], "deck": ["T003", "T003"]},
              {"bz": ["T001"]})
    n0 = len(e.s.pub)
    drv = _Driver(play=_play_once("play:T800"), choose=_choose_defn("T800"))
    drv.run(e, lambda ev: _count(ev, "graveyard", 0, "T800") == 1 and _quiet(ev))
    assert _count(e, "graveyard", 0, "T800") == 1
    assert len(e.zlist("hand", 0)) == 1          # 自分の効果の1ドローだけ
    assert "yes_no" not in drv.seen
    assert not _pub(e, n0, "reveal", zone="deck")
    assert not _pub(e, n0, "shuffle")


def test_899_no_other_knight_no_trigger(rules):
    """自分のナイトが「他に」いなければ誘発しない（T899 自身はナイトだが
    other: true で数えない）。公開・シャッフルも起きない。"""
    e = setup(rules, {"bz": ["T899"], "hand": ["T800"],
                      "mana": ["T010", "T010"], "deck": ["T800", "T800"]},
              {"bz": ["T001"]})
    n0 = len(e.s.pub)
    drv = _Driver(play=_play_once("play:T800"), choose=_choose_defn("T800"))
    drv.run(e, lambda ev: _count(ev, "graveyard", 0, "T800") == 1 and _quiet(ev))
    assert _count(e, "graveyard", 0, "T800") == 1
    assert len(e.zlist("hand", 0)) == 1
    assert "yes_no" not in drv.seen
    assert not _pub(e, n0, "reveal", zone="deck")
    assert not _pub(e, n0, "shuffle")
