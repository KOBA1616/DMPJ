"""再変換ラウンド355（第320弾 trigger_when_blocked）の記録テスト。

- 新規登録2件: dm26ex2-068 ワダウザノミコト /
  dm26rp1-074 ノーガルディ・ネギオ＆ガルダンディ・ナスオ。
- alias 畳み込み0件（identity の canon_id 実測で2件とも
  自 ID、aliases_for は空）。stale クリーンアップ0件・
  差し戻し0件。
- 対象2行は gaps = [trigger_when_blocked] のため reopen で
  外してから submit（reopen の出力は対象2件ちょうど）。
- converted 10,262→10,264 / rejects 2,055→2,053、
  canonical 重なり0・漏れ0。trigger_when_blocked は
  ファミリーがこの2件だけだったため完全に解消。

登録形は第320弾の確立形と完全一致（submit の連結・
merge_split 由来の混入なし）:
- 形A（074、「ブロックされた時」）: trigger {event: block,
  attacker: self} → break {player: opp, count: 2}
  （第280弾の登録先例形）。
- 形B（068、「ブロックした時」）: trigger {event: block,
  subject: self} → move {ref: self} ＋ move
  {ref: event.attacker} を持ち主の手札へ（dm20-045 の
  登録先例）。併記の離脱条項も同弾の確立形。
dm26rp1-074 の text は partial が切れていたため reject 行の
公式全文に差し替えた。

実挙動は登録カード自身で固定する。ドライバは
scenario.build の薄い包みで、tests.conftest は
import しない（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

GAP = "trigger_when_blocked"

TRIGGER_BLOCKED_BREAK = {
    "kind": "trigger",
    "when": {"event": "block", "attacker": "self"},
    "effect": [{"op": "break", "player": "opp", "count": 2}]}
TRIGGER_BLOCK_BOUNCE = {
    "kind": "trigger",
    "when": {"event": "block", "subject": "self"},
    "effect": [
        {"op": "move", "select": {"ref": "self"},
         "to": "hand", "reason": "return"},
        {"op": "move", "select": {"ref": "event.attacker"},
         "to": "hand", "reason": "return"}]}
TRIGGER_LEAVE_LOOK = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "subject": "self"},
    "effect": [
        {"op": "choose",
         "select": {"zone": "deck", "owner": "you", "from_top": 4,
                    "look": True, "count": "all"},
         "as": "pile"},
        {"op": "choose", "select": {"ref": "pile", "count": 1},
         "as": "pick"},
        {"op": "move", "select": {"ref": "pick", "count": "all"},
         "to": "hand", "reason": "draw"},
        {"op": "repeat",
         "times": {"count": {"ref": "pile", "zone": "deck"}},
         "body": [
             {"op": "choose",
              "select": {"ref": "pile", "zone": "deck", "count": 1},
              "as": "c"},
             {"op": "modal",
              "modes": [
                  [{"op": "move",
                    "select": {"ref": "c", "count": "all"},
                    "to": "deck", "position": "top",
                    "reason": "put"}],
                  [{"op": "move",
                    "select": {"ref": "c", "count": "all"},
                    "to": "deck", "position": "bottom",
                    "reason": "put"}]]}]}]}

TEXT_068 = ("S・トリガー（このカードを自分のシールドゾーンから"
            "手札に加える時、コストを支払わずにすぐ実行してもよい）\n"
            "ブロッカー（このクリーチャーをタップして、相手"
            "クリーチャーの攻撃先をこのクリーチャーに変更してもよい）\n"
            "このクリーチャーがブロックした時、このクリーチャーと"
            "攻撃しているクリーチャーを持ち主の手札に戻す。\n"
            "このクリーチャーが離れた時、自分の山札の上から４枚を"
            "見る。その中から１枚を手札に加え、残りを好きな順序で"
            "山札の上か下に置く。")
TEXT_074 = ("このクリーチャーがブロックされた時、この"
            "クリーチャーは相手のシールドを２つブレイクする。")

FORMS = {
    "dm26ex2-068": {"name": "ワダウザノミコト",
                    "types": ["creature"],
                    "civs": ["light", "water"], "cost": 4,
                    "power": 1000,
                    "races": ["ミズガミ", "ロスト・クルセイダー"],
                    "mana": 1, "keywords": ["s_trigger", "blocker"],
                    "text": TEXT_068,
                    "abilities": [TRIGGER_BLOCK_BOUNCE,
                                  TRIGGER_LEAVE_LOOK],
                    "proto": "T982"},
    "dm26rp1-074": {"name": "ノーガルディ・ネギオ＆ガルダンディ・ナスオ",
                    "types": ["creature"], "civs": ["nature"],
                    "cost": 2, "power": 3000,
                    "races": ["ワイルド・ベジーズ"], "mana": 1,
                    "text": TEXT_074,
                    "abilities": [TRIGGER_BLOCKED_BREAK],
                    "proto": "T983"},
}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _unsup(r):
    return [u.get("need") if isinstance(u, dict) else u
            for u in (((r.get("partial") or {}).get("source") or {})
                      .get("unsupported") or [])]


def test_round355_disposition():
    rej = _reject_rows()
    assert len(rej) == 2053
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10264
    assert not (ids & set(rej))          # canonical 重なり0
    for tid, spec in FORMS.items():
        # 漏れ0: 正本は登録され reject 行に残っていない
        # （alias は両件とも無し）
        assert tid in ids and tid not in rej, tid
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None
        assert not (c.get("source") or {}).get("unsupported")
        assert not (c.get("source") or {}).get("aliases"), tid
        # 登録形の完全一致（連結・merge_split 由来の混入なし）
        for k in ("name", "types", "civs", "cost", "power", "races",
                  "mana", "text", "abilities"):
            assert c.get(k) == spec[k], (tid, k)
        assert c.get("keywords") == spec.get("keywords"), tid
        assert len(c["abilities"]) == len(spec["abilities"]), tid
        # 登録形は対応プロトの abilities と完全一致
        d = parse_card(c, TABLES)
        proto = parse_card(proto_card(spec["proto"]), TABLES)
        assert d.abilities == proto.abilities, tid
    # trigger_when_blocked は完全に解消（ファミリーはこの2件だけ）
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T001", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _deck_defns(e, p):
    return [e.s.cards[c].defn for c in e.zlist("deck", p)]


class _LeavePlan:
    """離脱条項の決定プラン（第320弾本体と同方式）。"""

    def __init__(self, e, pick_pos, placements):
        self.e = e
        self.pick_pos = pick_pos
        self.mode_by_pos = dict(placements)
        self.order = [pos for pos, _ in placements]
        self.pile = None
        self.consumed = set()
        self._pending_mode = None
        self.modes_answered = 0

    def choose(self, d):
        opts = d["options"]
        offered = [self.e.s.cards[o["cid"]].defn for o in opts]
        if self.pile is None:
            self.pile = _deck_defns(self.e, 0)[:4]
            self.consumed.add(self.pick_pos)
            want = self.pile[self.pick_pos]
        else:
            pos = next(p for p in self.order
                       if p not in self.consumed
                       and self.pile[p] in offered)
            self.consumed.add(pos)
            self._pending_mode = self.mode_by_pos[pos]
            want = self.pile[pos]
        return [offered.index(want)]

    def mode(self, d):
        if self._pending_mode is None:
            rest = [p for p in self.order if p not in self.consumed]
            assert len(rest) == 1, rest
            self.consumed.add(rest[0])
            m = self.mode_by_pos[rest[0]]
        else:
            m = self._pending_mode
            self._pending_mode = None
        self.modes_answered += 1
        keys = [o["key"] for o in d["options"]]
        return [keys.index(f"mode:{m}")]

    @property
    def done(self):
        return self.pile is not None \
            and self.modes_answered >= len(self.order)


def _drive(e, attacker=None, attacker_player=1, blocker=None,
           plan=None, stop_when=None, limit=900):
    """第320弾本体と同じ汎用ドライバ（build の決定種別にも対応）。"""
    state = {"attacked": False}
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if stop_when is not None and stop_when(e):
            return state
        if plan is not None and plan.done \
                and kind not in ("choose_cards", "choose_mode"):
            return state
        if kind in ("attack", "declare_attack"):
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and d["player"] == attacker_player \
                    and not state["attacked"]:
                state["attacked"] = True
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind in ("block", "declare_block"):
            hit = [i for i, k in enumerate(keys)
                   if blocker and k.startswith(f"bz:{blocker}:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "choose_cards" and plan is not None:
            e.answer(plan.choose(d))
        elif kind == "choose_mode" and plan is not None:
            e.answer(plan.mode(d))
        elif kind == "choose_shields":
            e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("limit reached")


def test_registered_074_breaks_two_when_blocked(rules):
    """登録形A: dm26rp1-074 が攻撃してブロックされると、
    バトルの前に相手のシールドを2つブレイクし、バトルも
    通常どおり行われる（3000 同士で相打ち）。"""
    e = _build(rules, {"bz": ["dm26rp1-074"]}, {"bz": ["T004"]})
    shields0 = len(e.zlist("shield", 1))
    hand1_0 = len(e.zlist("hand", 1))
    st = _drive(e, attacker="dm26rp1-074", attacker_player=0,
                blocker="T004",
                stop_when=lambda e: "dm26rp1-074" in _defns(e, "graveyard", 0)
                and "T004" in _defns(e, "graveyard", 1))
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == shields0 - 2
    # ブレイクした2枚は相手の手札へ（墓地には行かない）。
    # 観測時点までに相手のターン開始ドローが混ざるため
    # 「2枚以上増えた」で固定する
    assert len(e.zlist("hand", 1)) >= hand1_0 + 2
    assert "dm26rp1-074" in _defns(e, "graveyard", 0)
    assert _defns(e, "graveyard", 1) == ["T004"]


def test_registered_074_no_break_when_other_blocked(rules):
    """登録形Aの対照: 別のクリーチャーがブロックされても
    dm26rp1-074 は誘発しない（attacker: self の照合）。"""
    e = _build(rules, {"bz": ["dm26rp1-074", "T001"]},
               {"bz": ["T004"]})
    shields0 = len(e.zlist("shield", 1))
    st = _drive(e, attacker="T001", attacker_player=0,
                blocker="T004",
                stop_when=lambda e: "T001" in _defns(e, "graveyard", 0))
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == shields0
    assert "T001" in _defns(e, "graveyard", 0)
    assert "dm26rp1-074" in _defns(e, "bz", 0)


def test_registered_068_block_bounces_both_and_leave_looks(rules):
    """登録形B: dm26ex2-068 がブロックすると、自身と攻撃
    クリーチャーが持ち主の手札に戻り、離脱条項（上4枚を
    見て1枚を手札、残りを上下に配置）も連鎖する。"""
    e = _build(rules, {"bz": ["dm26ex2-068"]}, {"bz": ["T001"]})
    plan = _LeavePlan(e, pick_pos=1,
                      placements=[(0, 1), (2, 0), (3, 0)])
    st = _drive(e, attacker="T001", attacker_player=1,
                blocker="dm26ex2-068", plan=plan)
    assert st["attacked"] and plan.done
    pile = plan.pile
    assert pile is not None and len(pile) == 4
    assert "dm26ex2-068" in _defns(e, "hand", 0)
    assert "dm26ex2-068" not in _defns(e, "bz", 0)
    assert "T001" in _defns(e, "hand", 1)
    assert "T001" not in _defns(e, "bz", 1)
    assert pile[1] in _defns(e, "hand", 0)
    deck = _deck_defns(e, 0)
    # 束[0] は一番下。束[3] は一番上に置かれたが、解決後の
    # 最初の決定は自ターン開始ドローの後になるため手札へ
    # （＝一番上に置かれたことの証明）、次が束[2]
    assert pile[3] in _defns(e, "hand", 0)
    assert deck[-1] == pile[0]
    assert deck[0] == pile[2]


def test_registered_068_destroyed_leave_looks_without_bounce(rules):
    """登録形Bの対照: dm26ex2-068 が攻撃してブロックされ
    バトルで破壊された場合は、ブロック条項は発火せず、
    離脱条項だけが発火する。"""
    e = _build(rules, {"bz": ["dm26ex2-068"]}, {"bz": ["T004"]})
    plan = _LeavePlan(e, pick_pos=0,
                      placements=[(1, 1), (2, 1), (3, 1)])
    st = _drive(e, attacker="dm26ex2-068", attacker_player=0,
                blocker="T004", plan=plan)
    assert st["attacked"] and plan.done
    pile = plan.pile
    assert "dm26ex2-068" in _defns(e, "graveyard", 0)
    assert "dm26ex2-068" not in _defns(e, "hand", 0)
    assert "T004" in _defns(e, "bz", 1)
    assert pile[0] in _defns(e, "hand", 0)
    deck = _deck_defns(e, 0)
    assert deck[-3:] == [pile[1], pile[2], pile[3]]
