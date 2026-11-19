"""語彙パイロット第285弾のカード適用テスト（登録形）。

ラウンド320で free_play_event 純粋3件を新規登録:
- dmex10-006 ウソと盗みのエンターテイナー: partial は abilities を
  持たず text も切れていた。text を reject 行の公式全文に戻し、
  第1条項（自分の他のクリーチャーがあれば攻撃されない）を
  cannot_be_attacked キーワードの展開形 {static, affects: self,
  mod: {deny: [be_attacked]}} に if {exists {zone: bz, owner: you,
  other: true, filter: creature}} の条件を付けた形で、第2条項を
  unpaid 照合の相手形誘発で追加。
  alias: dmx22b-135 / promoy11-070 / promoy17-065 / promoy17-068。
- dmex12-064 キャタピラ親方: partial は完全（J・O・E の opt_reduce
  常在型＋speed_attacker）。全員形の誘発を足すだけ。
  alias: dmbd03-008。
- dmsp01-033 早撃人形マグナム: partial は speed_attacker のみ。
  全員形の誘発を足すだけ。
  alias: dmr07-030 / dmx22b-036 / promoy12-060。
- converted 10,163 / rejects 2,170、重なり0・漏れ0。free_play_event
  は残り0件でファミリー解消。

プロトテスト（test_vocab_pilot285.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが汚染される）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
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

TARGETS = ["dmex10-006", "dmex12-064", "dmsp01-033"]

# 登録形（converted.yaml の生の形。destroy はマクロのまま保持される）
STATIC_NO_ATTACK = {
    "kind": "static", "affects": "self", "mod": {"deny": ["be_attacked"]},
    "if": {"exists": {"zone": "bz", "owner": "you", "other": True,
                      "filter": {"types": ["creature"]}}},
}

TRIG_OPP = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "opp", "filter": {"types": ["creature"]}},
             "unpaid": True},
    "effect": [{"op": "destroy", "select": {"ref": "event.subject"}}],
}

TRIG_ANY = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"filter": {"types": ["creature"]}},
             "unpaid": True},
    "effect": [{"op": "destroy", "select": {"ref": "event.subject"}}],
}

OPT_REDUCE = {"kind": "static", "affects": "self", "zone": "hand",
              "mod": {"opt_reduce": {"amount": 1, "then": "deck_bottom_draw"}}}

# parse 後の展開形（destroy マクロは move に展開される）
FORM_OPP_X = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "opp", "filter": {"types": ["creature"]}},
             "unpaid": True},
    "effect": [{"op": "move", "select": {"ref": "event.subject"},
                "to": "graveyard", "reason": "destroy"}],
}

FORM_ANY_X = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"filter": {"types": ["creature"]}},
             "unpaid": True},
    "effect": [{"op": "move", "select": {"ref": "event.subject"},
                "to": "graveyard", "reason": "destroy"}],
}

KW_SA = {"kind": "static", "affects": "self",
         "mod": {"allow": ["attack_summoning_sick"]},
         "keyword": "speed_attacker"}

TEXT_006 = ("バトルゾーンに自分の他のクリーチャーがあれば、このクリーチャーは"
            "攻撃されない。相手がコストを支払わずにクリーチャーをバトルゾーンに"
            "出した時、そのクリーチャーを破壊する。")


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
    """汎用ドライバ（第285弾プロトのものと同じ）。"""

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


def _p1_attack_options(e, p0_attackers):
    """P0 が指定した獣でプレイヤーを攻撃し（全てタップさせる）、
    P1 の最初の攻撃決定の選択肢キーを返す。"""
    queue = list(p0_attackers)
    for _ in range(600):
        if e.s.result is not None:
            raise AssertionError("game ended before P1 attack decision")
        d = e.advance()
        if d is None:
            raise AssertionError("no decision before P1 attack decision")
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "attack":
            if e.s.turn >= 2:
                return keys
            pick = None
            for i, k in enumerate(keys):
                if queue and k.startswith(f"attack:{queue[0]}:"):
                    pick = i
                    queue.pop(0)
                    break
            if pick is not None:
                e.answer([pick])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
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
    raise AssertionError("limit reached")


# ---------- 登録形 ----------

def test_registered_forms():
    rej = _reject_ids()
    for cid in TARGETS:
        assert cid not in rej, cid
        _converted(cid)

    c = _converted("dmex10-006")
    assert c["abilities"] == [STATIC_NO_ATTACK, TRIG_OPP]
    assert c["text"] == TEXT_006
    assert (c.get("source") or {}).get("aliases") == [
        "dmx22b-135", "promoy11-070", "promoy17-065", "promoy17-068"]
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert d.abilities == [STATIC_NO_ATTACK, FORM_OPP_X]
    assert d.keywords == []

    c = _converted("dmex12-064")
    assert c["abilities"] == [OPT_REDUCE, TRIG_ANY]
    assert (c.get("source") or {}).get("aliases") == ["dmbd03-008"]
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert d.abilities == [KW_SA, OPT_REDUCE, FORM_ANY_X]
    assert d.keywords == ["speed_attacker"]

    c = _converted("dmsp01-033")
    assert c["abilities"] == [TRIG_ANY]
    assert (c.get("source") or {}).get("aliases") == [
        "dmr07-030", "dmx22b-036", "promoy12-060"]
    assert "unsupported" not in (c.get("source") or {})
    d = parse_card(c, TABLES)
    assert d.abilities == [KW_SA, FORM_ANY_X]
    assert d.keywords == ["speed_attacker"]


# ---------- 実挙動: dmex10-006 ----------

def test_006_destroys_opponent_effect_put(rules):
    """相手が効果でクリーチャーを出す（T815 の play_free）と破壊される（相手形）。"""
    e = setup(rules, {"bz": ["dmex10-006"], "mana": ["T001"] * 3},
              {"hand": ["T815", "T816"], "mana": ["T010"] * 2})
    drv = _Driver(play=_play_times("play:T815", 1),
                  choose=_choose_targets("T816"))
    drv.run(e, lambda ev: "T816" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T816" in _defns(e, "graveyard", 1)
    assert "T816" not in _defns(e, "bz", 1)
    assert "dmex10-006" in _defns(e, "bz", 0)


def test_006_ignores_own_effect_put(rules):
    """相手形は自分の効果出しには発火しない（subject の owner: opp）。"""
    e = setup(rules, {"bz": ["dmex10-006"], "hand": ["T815", "T816"],
                      "mana": ["T010"] * 2},
              {"mana": ["T001"] * 3})
    drv = _Driver(play=_play_times("play:T815", 1),
                  choose=_choose_targets("T816"))
    drv.run(e, lambda ev: "T816" in _defns(ev, "bz", 0) and _quiet(ev))
    assert "T816" in _defns(e, "bz", 0)
    assert "T816" not in _defns(e, "graveyard", 0)


def test_006_not_attacked_with_other_creature(rules):
    """第1条項: 自分の他のクリーチャーがいれば、タップしていても
    攻撃対象に選ばれない（相手の攻撃選択肢に出ない）。"""
    e = setup(rules, {"bz": ["dmex10-006", "T816"], "mana": ["T001"] * 6},
              {"bz": ["T034"], "mana": ["T001"] * 3})
    keys = _p1_attack_options(e, ["dmex10-006", "T816"])
    assert "attack:T034:T816" in keys          # タップした味方は対象になる
    assert not any(k.endswith(":dmex10-006") for k in keys)


def test_006_attacked_when_alone(rules):
    """対照: 他のクリーチャーがいなければ通常どおり攻撃対象になる。"""
    e = setup(rules, {"bz": ["dmex10-006"], "mana": ["T001"] * 6},
              {"bz": ["T034"], "mana": ["T001"] * 3})
    keys = _p1_attack_options(e, ["dmex10-006"])
    assert "attack:T034:dmex10-006" in keys


# ---------- 実挙動: dmex12-064（全員形） ----------

def test_064_destroys_own_effect_put(rules):
    """全員形は自分の効果出しにも発火する（「いずれかのプレイヤー」）。"""
    e = setup(rules, {"bz": ["dmex12-064"], "hand": ["T815", "T816"],
                      "mana": ["T010"] * 2},
              {"mana": ["T001"] * 3})
    drv = _Driver(play=_play_times("play:T815", 1),
                  choose=_choose_targets("T816"))
    drv.run(e, lambda ev: "T816" in _defns(ev, "graveyard", 0) and _quiet(ev))
    assert "T816" in _defns(e, "graveyard", 0)
    assert "T816" not in _defns(e, "bz", 0)
    assert "dmex12-064" in _defns(e, "bz", 0)   # 発生源は残る


# ---------- 実挙動: dmsp01-033（全員形） ----------

def test_033_destroys_opponent_effect_put(rules):
    """全員形は相手の効果出しにも発火する。"""
    e = setup(rules, {"bz": ["dmsp01-033"], "mana": ["T001"] * 3},
              {"hand": ["T815", "T816"], "mana": ["T010"] * 2})
    drv = _Driver(play=_play_times("play:T815", 1),
                  choose=_choose_targets("T816"))
    drv.run(e, lambda ev: "T816" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "T816" in _defns(e, "graveyard", 1)
    assert "T816" not in _defns(e, "bz", 1)
    assert "dmsp01-033" in _defns(e, "bz", 0)


def test_033_self_entry_destroys_itself(rules):
    """発生源自身が効果で出た時、その誘発は自身を破壊する。"""
    e = setup(rules, {"mana": ["T001"] * 3},
              {"bz": ["T816"], "hand": ["T815", "dmsp01-033"],
               "mana": ["T010"] * 2})
    drv = _Driver(play=_play_times("play:T815", 1),
                  choose=_choose_targets("dmsp01-033"))
    drv.run(e, lambda ev: "T815" in _defns(ev, "graveyard", 1) and _quiet(ev))
    assert "dmsp01-033" in _defns(e, "graveyard", 1)
    assert "dmsp01-033" not in _defns(e, "bz", 1)
    assert "T816" in _defns(e, "bz", 1)   # 先にいた獣は無事
