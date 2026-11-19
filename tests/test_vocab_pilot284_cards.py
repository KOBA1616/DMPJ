"""語彙パイロット第284弾のカード適用テスト（登録形）。

ラウンド319で once_per_turn_replacement 純粋3件を新規登録:
- dm22rp2x-001 真実の精霊ヴァルペキュラ: partial は abilities を持たない。
  形A（自分のクリーチャーまたはタマシードが破壊される時、かわりに
  対象をシールド化。各ターン1度）＋第2能力（相手のターンのはじめ、
  自分のシールドが相手より多ければ相手のクリーチャーを2体タップ）を
  追加。alias: dm22rp2-001 / dm22rp2x-001x。
- dm22rp2x-050 霊魂と怨念のドライバー: partial は abilities を持たない。
  出た時（自分の山札の上から2枚を墓地に置く）＋形B（自分のクリーチャー
  が離れる時、かわりにタップしてマナゾーンに置く。各ターン1度）を追加。
  alias: dm22rp2-050。
- dm23sd1-002 ボルシャック・モルナルク: partial の出た時（墓地の
  ファイアー・バードをすべて手札に加える）はそのまま、形C（自分の
  アーマード・ドラゴンが破壊される時、かわりにファイアー・バードを
  1枚手札から出す。各ターン1度。if ゲート必須）を追加。alias なし。
- converted 10,160 / rejects 2,173、重複0・漏れ0。once_per_turn_replacement
  は残り0件でファミリー解消。

プロトテスト（test_vocab_pilot284.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが汚染される）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, parse_card, load_tables  # noqa: E402
from dmsim.engine.scenario import build  # noqa: E402


def setup(rules, p0, p1=None, filler="T001", seed=1, deck_size=20):
    """conftest の setup と同じ薄い包み。tests.conftest を import すると
    DMSIM_SKIP_CONVERTED が再設定されて converted が読めなくなるため、
    ここでは直接 scenario.build を包む（第283弾 cards と同じ）。"""
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": filler,
                         "seed": seed, "deck_size": deck_size})

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

TARGETS = ["dm22rp2x-001", "dm22rp2x-050", "dm23sd1-002"]

FORM_A = {
    "kind": "replace", "optional": True, "once_per_turn": True,
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy",
             "subject": {"owner": "you",
                         "filter": {"types": ["creature", "tamaseed"]}}},
    "instead": [{"op": "move", "select": {"ref": "event.subject"},
                 "to": "shield", "reason": "charge"}],
}

FORM_A2 = {
    "kind": "trigger",
    "when": {"event": "turn_start", "player": "opp"},
    "if": {"cmp": [{"count": {"zone": "shield", "owner": "you"}}, ">",
                   {"count": {"zone": "shield", "owner": "opp"}}]},
    "effect": [{"op": "tap",
                "select": {"zone": "bz", "owner": "opp",
                           "filter": {"types": ["creature"]}, "count": 2}}],
}

CIP_B = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "move",
                "select": {"zone": "deck", "owner": "you", "from_top": 2,
                           "count": "all"},
                "to": "graveyard", "reason": "put"}],
}

FORM_B = {
    "kind": "replace", "optional": True, "once_per_turn": True,
    "when": {"event": "move", "from": "bz",
             "subject": {"owner": "you",
                         "filter": {"types": ["creature"]}}},
    "instead": [{"op": "move", "select": {"ref": "event.subject"},
                 "to": "mana", "reason": "put", "tapped": True}],
}

CIP_C = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "move",
                "select": {"zone": "graveyard", "owner": "you",
                           "filter": {"race_has": "ファイアー・バード"},
                           "count": "all"},
                "to": "hand", "reason": "return"}],
}

FORM_C = {
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


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _reject_ids():
    out = set()
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            out.add(json.loads(line)["id"])
    return out


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _quiet(e):
    return (not any(t.get("t") in ("effect", "event") for t in e.s.tasks)
            and not e.s.pending)


class _Driver:
    """汎用ドライバ（第284弾プロトのものと同じ）。"""

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


# ---------- 登録形 ----------

def test_registered_forms():
    rej = _reject_ids()
    for cid in TARGETS:
        assert cid not in rej, cid
        _converted(cid)

    c = _converted("dm22rp2x-001")
    assert c["abilities"] == [FORM_A, FORM_A2]
    assert (c.get("source") or {}).get("aliases") == ["dm22rp2-001", "dm22rp2x-001x"]
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert d.keywords == ["blocker", "triple_breaker"]

    c = _converted("dm22rp2x-050")
    assert c["abilities"] == [CIP_B, FORM_B]
    assert (c.get("source") or {}).get("aliases") == ["dm22rp2-050"]
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert d.keywords == []

    c = _converted("dm23sd1-002")
    assert c["abilities"] == [CIP_C, FORM_C]
    assert (c.get("source") or {}).get("aliases") in (None, [])
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert d.keywords == ["triple_breaker"]


# ---------- 実挙動: dm22rp2x-001 ----------

def test_001_form_a_protects_ally(rules):
    """味方が破壊される時、かわりにシールド化する（形A）。"""
    e = setup(rules, {"bz": ["dm22rp2x-001", "T810"], "mana": ["T001"] * 6},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_times("play:T056", 1),
                  choose=_choose_targets("T810"))
    drv.run(e, lambda ev: "T810" in _defns(ev, "shield", 0) and _quiet(ev))
    assert drv.seen.count("choose_replacement") == 1
    assert "T810" in _defns(e, "shield", 0)
    assert "T810" not in _defns(e, "graveyard", 0)


def test_001_second_ability_taps_two(rules):
    """相手のターンのはじめ、自分のシールドが多ければ相手の獣2体がタップする。"""
    e = build(rules, {"p0": {"bz": ["dm22rp2x-001"], "shield": ["T001"] * 5},
                      "p1": {"bz": ["T001", "T001", "T001"],
                             "shield": ["T001"] * 2},
                      "filler": "T001", "seed": 1, "deck_size": 20})
    drv = _Driver()
    drv.run(e, lambda ev: ev.s.turn >= 2
            and sum(1 for c in ev.bz_tops(1) if ev.s.cards[c].tapped) == 2
            and _quiet(ev))
    tapped = [c for c in e.bz_tops(1) if e.s.cards[c].tapped]
    assert len(tapped) == 2


# ---------- 実挙動: dm22rp2x-050 ----------

def test_050_cip_mills_two(rules):
    """出た時、自分の山札の上から2枚が墓地に置かれる。"""
    e = setup(rules, {"hand": ["dm22rp2x-050"], "mana": ["T001", "T008"]},
              {"mana": ["T001"] * 3})
    drv = _Driver(play=_play_times("play:dm22rp2x-050", 1))
    drv.run(e, lambda ev: "dm22rp2x-050" in _defns(ev, "bz", 0) and _quiet(ev))
    assert "dm22rp2x-050" in _defns(e, "bz", 0)
    assert len(_defns(e, "graveyard", 0)) == 2


def test_050_form_b_bounce_becomes_tapped_mana(rules):
    """味方がバウンスされる代わりに、タップしたままマナゾーンに置かれる（形B）。
    観測は相手ターン内の決定で行う（第284弾の罠）。"""
    e = setup(rules, {"bz": ["dm22rp2x-050", "T810"], "mana": ["T001"] * 3},
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


# ---------- 実挙動: dm23sd1-002 ----------

def test_002_cip_returns_fire_birds(rules):
    """出た時、墓地のファイアー・バードがすべて手札に加わる。"""
    e = setup(rules, {"hand": ["dm23sd1-002"], "graveyard": ["T810"],
                      "mana": ["T034"] * 8},
              {"mana": ["T001"] * 3})
    drv = _Driver(play=_play_times("play:dm23sd1-002", 1))
    drv.run(e, lambda ev: "T810" in _defns(ev, "hand", 0) and _quiet(ev))
    assert "dm23sd1-002" in _defns(e, "bz", 0)
    assert "T810" in _defns(e, "hand", 0)
    assert "T810" not in _defns(e, "graveyard", 0)


def test_002_form_c_summons_bird_and_dragon_stays(rules):
    """アーマード・ドラゴンが破壊される時、手札のファイアー・バードが
    代わりに出て、ドラゴンは残る（形C）。"""
    e = setup(rules, {"bz": ["dm23sd1-002", "T808"], "hand": ["T810"],
                      "mana": ["T001"] * 3},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_times("play:T056", 1),
                  choose=_choose_targets("T808"))
    drv.run(e, lambda ev: "T810" in _defns(ev, "bz", 0) and _quiet(ev))
    assert drv.seen.count("choose_replacement") == 1
    assert "T808" in _defns(e, "bz", 0)
    assert "T810" in _defns(e, "bz", 0)
    assert "T810" not in _defns(e, "hand", 0)


def test_002_form_c_no_bird_no_consult(rules):
    """対照: 手札にファイアー・バードが無ければ諮問自体が起きず、
    ドラゴンは通常破壊される（if ゲート）。"""
    e = setup(rules, {"bz": ["dm23sd1-002", "T808"], "mana": ["T001"] * 3},
              {"hand": ["T056"], "mana": ["T056"] * 3})
    drv = _Driver(play=_play_times("play:T056", 1),
                  choose=_choose_targets("T808"))
    drv.run(e, lambda ev: "T808" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert "T808" in _defns(e, "graveyard", 0)
    assert "choose_replacement" not in drv.seen
