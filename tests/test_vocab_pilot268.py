"""語彙パイロット第268弾: dogiragon_gacha（ドギラゴン・ガチャ）。

「ドギラゴン・ガチャをN度回す。回すたびに、その能力を使う。」
ガチャは DMD-34 のガチャフィギュアの出目で決まる公開のランダム効果で、
出目と能力の対応表は公式に定まっている（Duel Masters Wiki「Gacha Figure」）:

- 1 ブースト: 自分の山札の上から1枚をマナゾーンに置く
- 2 リプレニッシュ: カードを1枚引く
- 3 ブレイク: 自分のクリーチャー1体がこのターンの終わりまでシールドをさらに1枚ブレイクする
- 4 デストロイ: 相手のコスト7以下のクリーチャー1体を破壊する
- 5 ファイト: 自分のクリーチャー1体と相手のクリーチャー1体をバトルさせる
- 6 ストライク: 自分のマナゾーンから進化ではないクリーチャー1体をバトルゾーンに出す

新語彙は op **`gacha`**（`{op: gacha, kind: dogiragon, times: N}`）。
出目は決定的な乱数（`rng_below`、ゲームの seed に紐づく）で振り、
s.pub に kind: "gacha" で公開記録する（フィギュアの結果は両プレイヤーに見える）。
1回分の振りと効果の解決は専用タスク gacha が1回ずつ行い、
後の出目は前の効果の解決が終わってから振る。
6つの効果はすべて既存語彙の組み合わせ（move / draw / modify breaks_add /
force_battle）で、新しい効果語彙は要らない。
"""
import pytest
from tests.conftest import setup

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card

TABLES = load_tables()

_NAMES = {1: "boost", 2: "replenish", 3: "break", 4: "destroy", 5: "fight", 6: "strike"}


def _defns(e, zone, p):
    # zlist("bz", p) は共有ゾーンで両軍分を含むため、バトルゾーンは bz_tops で絞る
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _by_defn(e, zone, p):
    if zone == "bz":
        return {e.cdef(c).id: c for c in e.bz_tops(p)}
    return {e.cdef(c).id: c for c in e.zlist(zone, p)}


def _drive(e, stop, choose=None, play=None, yes_no=None, order=None, limit=800):
    """汎用ドライバ（第267弾のものを流用）。"""
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


def _pick_t001(e, d):
    """choose_cards で T001 が候補にあれば1枚選ぶ（ガチャの各効果の選択先を固定する）。"""
    idx = [i for i, o in enumerate(d["options"])
           if e.s.cards[o["cid"]].defn == "T001"]
    return idx[:1] if idx else None


def _gacha_done(n):
    """ガチャが n 回ぶん解決し終えたら止める（タスクが消え、公開記録が n 件）。"""
    def stop(e):
        recs = [r for r in e.s.pub if r["kind"] == "gacha"]
        return (len(recs) == n
                and not any(t.get("t") == "gacha" for t in e.s.tasks))
    return stop


def _snap(e):
    """出目の署名になる局面の切り取り。"""
    t001 = _by_defn(e, "bz", 0).get("T001")
    return {
        "mana": len(e.zlist("mana", 0)),
        "hand": len(e.zlist("hand", 0)),
        "deck": len(e.zlist("deck", 0)),
        "bz0": _defns(e, "bz", 0),
        "bz1": _defns(e, "bz", 1),
        "grave0": _defns(e, "graveyard", 0),
        "grave1": _defns(e, "graveyard", 1),
        "breaks": e.chars_ro(t001)["breaks_add"] if t001 is not None else 0,
    }


# ---------- parse / validation ----------

def test_pilot268_protos_parse():
    rules = load_rules()
    t743 = rules.cards["T743"]
    assert t743.abilities == [{"kind": "trigger",
                               "when": {"event": "move", "to": "bz", "subject": "self"},
                               "effect": [{"op": "gacha", "kind": "dogiragon", "times": 1}]}]
    assert rules.cards["T744"].spell == [{"op": "gacha", "kind": "dogiragon", "times": 2}]
    assert rules.cards["T745"].abilities[0]["effect"] == [
        {"op": "gacha", "kind": "dogiragon", "times": 3}]
    base = {"id": "TX", "name": "x", "types": ["creature"],
            "civs": ["fire"], "cost": 3, "power": 1000, "races": ["テスト"],
            "abilities": [{"kind": "trigger",
                           "when": {"event": "move", "to": "bz", "subject": "self"},
                           "effect": [{"op": "gacha", "kind": "dogiragon", "times": 1}]}]}
    parse_card(dict(base), TABLES)
    with pytest.raises(DefError):
        bad = dict(base)
        bad["abilities"] = [{"kind": "trigger",
                             "when": {"event": "move", "to": "bz", "subject": "self"},
                             "effect": [{"op": "gacha", "kind": "dokindam", "times": 1}]}]
        parse_card(bad, TABLES)
    with pytest.raises(DefError):
        bad = dict(base)
        bad["abilities"] = [{"kind": "trigger",
                             "when": {"event": "move", "to": "bz", "subject": "self"},
                             "effect": [{"op": "gacha", "times": 1}]}]
        parse_card(bad, TABLES)


# ---------- 6出目すべて（seed を振って網羅） ----------

def _run_once(rules, seed):
    """T743 を出し、ガチャ1回を解決して (出目, 解決後の局面) を返す。"""
    e = setup(rules, {"hand": ["T743"], "bz": ["T001"], "mana": ["T005", "T005", "T001"]},
              {"bz": ["T001", "T741"]}, seed=seed)
    seen = {}
    _drive(e, _gacha_done(1), choose=_pick_t001, play=_play_key("play:T743", seen))
    assert seen["opt"]
    recs = [r for r in e.s.pub if r["kind"] == "gacha"]
    assert len(recs) == 1
    roll = recs[0]["result"]
    assert 1 <= roll <= 6
    assert recs[0]["name"] == _NAMES[roll]
    assert recs[0]["player"] == 0
    assert recs[0]["viewers"] == [0, 1]
    return roll, _snap(e)


def test_gacha_sweep_all_six_outcomes(rules):
    """seed を変えて1回ガチャを回し、6出目すべてが出て、それぞれの効果が
    対応する局面変化になることを確かめる。"""
    expected = {
        1: {"mana": 4, "hand": 0, "deck": 14, "bz0": ["T001", "T743"],
            "bz1": ["T001", "T741"], "grave0": [], "grave1": [], "breaks": 0},
        2: {"mana": 3, "hand": 1, "deck": 14, "bz0": ["T001", "T743"],
            "bz1": ["T001", "T741"], "grave0": [], "grave1": [], "breaks": 0},
        3: {"mana": 3, "hand": 0, "deck": 15, "bz0": ["T001", "T743"],
            "bz1": ["T001", "T741"], "grave0": [], "grave1": [], "breaks": 1},
        4: {"mana": 3, "hand": 0, "deck": 15, "bz0": ["T001", "T743"],
            "bz1": ["T741"], "grave0": [], "grave1": ["T001"], "breaks": 0},
        5: {"mana": 3, "hand": 0, "deck": 15, "bz0": ["T743"],
            "bz1": ["T741"], "grave0": ["T001"], "grave1": ["T001"], "breaks": 0},
        6: {"mana": 2, "hand": 0, "deck": 15, "bz0": ["T001", "T001", "T743"],
            "bz1": ["T001", "T741"], "grave0": [], "grave1": [], "breaks": 0},
    }
    seen = {}
    for seed in range(1, 49):
        roll, snap = _run_once(rules, seed)
        assert snap == expected[roll], (seed, roll, snap)
        seen[roll] = seen.get(roll, 0) + 1
    assert sorted(seen) == [1, 2, 3, 4, 5, 6], seen


# ---------- 複数回 ----------

def test_gacha_spell_times_two(rules):
    """呪文で2度回す: 公開記録が2件、呪文は墓地へ、ガチャタスクは残らない。"""
    e = setup(rules, {"hand": ["T744"], "bz": ["T001"], "mana": ["T005", "T005", "T005", "T001"]},
              {"bz": ["T001", "T001", "T741"]})
    seen = {}
    _drive(e, _gacha_done(2), choose=_pick_t001, play=_play_key("play:T744", seen))
    assert seen["opt"]
    recs = [r for r in e.s.pub if r["kind"] == "gacha"]
    assert len(recs) == 2
    assert all(1 <= r["result"] <= 6 for r in recs)
    assert all(r["name"] == _NAMES[r["result"]] for r in recs)
    assert "T744" in _defns(e, "graveyard", 0)
    assert not any(t.get("t") == "gacha" for t in e.s.tasks)
    d = e.advance()
    assert d is not None  # 対局は続く


def test_gacha_times_three(rules):
    """クリーチャーの CIP で3度回す: 公開記録が3件。"""
    e = setup(rules, {"hand": ["T745"], "bz": ["T001"], "mana": ["T005"] * 5},
              {"bz": ["T001", "T741"]})
    seen = {}
    _drive(e, _gacha_done(3), choose=_pick_t001, play=_play_key("play:T745", seen))
    assert seen["opt"]
    recs = [r for r in e.s.pub if r["kind"] == "gacha"]
    assert len(recs) == 3
    assert all(1 <= r["result"] <= 6 for r in recs)
    assert "T745" in _defns(e, "bz", 0)
    assert not any(t.get("t") == "gacha" for t in e.s.tasks)
    d = e.advance()
    assert d is not None  # 対局は続く
