"""コンボの経路を「段の列」として葉の評価に足す（ロードマップ P3 の先行実験。既定では使わない）。

経路データ data/loops/route/<名前>.yaml: stages = [{name, weight, all: [述語...]} | {name, weight, entry: <入口名>}]。
述語は入口 data/loops/entry/ の minimal と同じ形（zone|zones, match{name|types|civs|races}, n, op, owner=0）。
局面の点は「満たしている段のうち最も後ろの段」までの weight の合計。後の段が前の段の状態を消してもよい。
探索の手順（TurnSearch の候補・払い方）には触れず、葉の評価 value_fn だけを差し替える。カード名はデータ側にだけ書く。
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import yaml

from ..base.store import REPO
from ..engine.view import result_of
from .leaf_eval import Weights, evaluate

ROUTE_DIR = REPO / "data" / "loops" / "route"
ENTRY_DIR = REPO / "data" / "loops" / "entry"
OPS = {">=": lambda k, n: k >= n, "<=": lambda k, n: k <= n, "==": lambda k, n: k == n}


@dataclass(frozen=True)
class Stage:
    name: str
    weight: float
    preds: tuple[dict, ...]
    has_entry: bool = False   # 段の述語に入口（entry:）を含む


def _entry_preds(name: str) -> tuple[dict, ...]:
    d = json.loads((ENTRY_DIR / f"{name}.json").read_text(encoding="utf-8"))
    return tuple(d["minimal"])


def drawout_on() -> bool:
    """DMSIM_DRAWOUT=1: ドロー置換の勝ち手段を場に出す段に「出した後に引き切れる」条件を足す（設計書 §28）。"""
    import os
    return os.environ.get("DMSIM_DRAWOUT", "0") == "1"


def _with_drawout(preds: tuple[dict, ...]) -> tuple[dict, ...]:
    """場に出す述語の札がドロー置換の勝ち手段なら {drawout: その札} を足す。札の形は効果データから読む（名前は見ない）。"""
    from dmsim.cards.defs import load_rules
    from dmsim.search.access import draw_win
    rules = load_rules()
    add = [{"drawout": p["match"]["name"]} for p in preds
           if p.get("zone") == "bz" and "name" in p.get("match", {}) and draw_win(rules, p["match"]["name"])]
    return preds + tuple(add)


def load(name: str, drawout: bool | None = None) -> tuple[Stage, ...]:
    y = yaml.safe_load((ROUTE_DIR / f"{name}.yaml").read_text(encoding="utf-8"))
    dw = drawout_on() if drawout is None else drawout
    out = []
    for s in y["stages"]:
        preds = (_entry_preds(s["entry"]) if "entry" in s else ()) + tuple(s.get("all", ()))   # entry と all は併記できる（入口に加えて…の段）
        if dw:
            preds = _with_drawout(preds)
        out.append(Stage(s["name"], float(s["weight"]), preds, "entry" in s))
    return tuple(out)


def _drawout_frac(eng, cid: str, me: int) -> float:
    """引き切りの進み 0..1。今その札を出したとして、相手のターンのはじめまでに引き切れるなら 1。"""
    from dmsim.search.access import drawout
    d = drawout(eng, cid, me)
    if d is None or d["need"] == 0 or d["dig_before"] == 0:
        return 1.0
    base = d["need_pre"] if d["pre"] and d["dig_before"] < d["need"] - d["own_turn"] - d["scheduled"] else d["need"]
    return max(0.0, 1.0 - d["dig_before"] / max(1, base))


def count(eng, p: dict, me: int = 0) -> int:
    """owner は 0=自分（me）, 1=相手。"""
    s, rules = eng.s, eng.rules
    owner = me if p.get("owner", 0) == 0 else 1 - me
    zones = (p["zone"],) if p.get("zone") else tuple(p.get("zones") or ())
    m = p.get("match", {})
    n = 0
    for z in zones:
        cids = s.zones[z][owner]
        if p.get("top") and z == "bz":       # 場の一番上の札だけ（進化元として下にある札を除く）
            below = {u for c in cids for u in s.cards[c].under}
            cids = [c for c in cids if c not in below]
        for c in cids:
            defn = s.cards[c].defn
            d = rules.cards[defn]
            if "name" in m and m["name"] not in (defn, d.id):
                continue
            if "types" in m and not set(m["types"]) & set(d.types):
                continue
            if "civs" in m and not set(m["civs"]) & set(d.civs):
                continue
            if "races" in m and not set(m["races"]) & set(d.races):
                continue
            n += 1
    return n


def holds(eng, p: dict, me: int = 0) -> bool:
    if "drawout" in p:
        return _drawout_frac(eng, p["drawout"], me) >= 1.0
    return OPS[p.get("op", ">=")](count(eng, p, me), p.get("n", 1))


def reached(eng, stages, me: int = 0) -> int:
    """満たしている段のうち最も後ろの段の番号（1始まり）。どれも満たさなければ 0。"""
    k = 0
    for i, st in enumerate(stages, 1):
        if all(holds(eng, p, me) for p in st.preds):
            k = i
    return k


def route_score(eng, stages, me: int = 0, floor: int = 0) -> float:
    """floor: その対局で既に達成した段（ラチェット）。局面が前の段の状態を消しても、達成済みの段の点は下げない。"""
    k = max(reached(eng, stages, me), floor)
    return sum(st.weight for st in stages[:k])


LIVE_ZONES = ("hand", "graveyard", "bz")   # 名前の札が「まだ経路で使える」とみなす公開・手元のゾーン（部分点用）
AWAY_ZONES = ("mana",)                     # 経路の段がそのゾーンを指していなければ「使えない場所」とみなす（減点用）


def _frac(eng, p: dict, me: int, elsewhere: float) -> float:
    """述語 p の進み具合 0..1。>= の枚数条件は count/n。名前の札が指すゾーンに無くても使える場所にあれば elsewhere。"""
    if "drawout" in p:
        return _drawout_frac(eng, p["drawout"], me)
    if p.get("op", ">=") != ">=":
        return 1.0 if holds(eng, p, me) else 0.0
    n = max(1, p.get("n", 1))
    f = min(count(eng, p, me) / n, 1.0)
    if f < 1.0 and "name" in p.get("match", {}) and elsewhere > 0:
        zones = set((p["zone"],) if p.get("zone") else tuple(p.get("zones") or ()))
        other = {**p, "zone": None, "zones": [z for z in LIVE_ZONES if z not in zones]}
        if other["zones"] and count(eng, other, me) > 0:
            f = max(f, elsewhere)
    return f


def partial_score(eng, stages, me: int = 0, elsewhere: float = 0.25, floor: int = 0) -> float:
    """次の未達成の段（満たした最も後ろの段か floor の次）の進み具合 × その段の weight。"""
    k = max(reached(eng, stages, me), floor)
    if k >= len(stages):
        return 0.0
    preds = stages[k].preds
    return stages[k].weight * sum(_frac(eng, p, me, elsewhere) for p in preds) / len(preds)


def needed_cards(stages) -> dict[str, tuple[int, set]]:
    """経路の段から導く {札の名前: (必要枚数の最大, その札を指すゾーンの集合)}。"""
    out: dict[str, tuple[int, set]] = {}
    for st in stages:
        for p in st.preds:
            nm = p.get("match", {}).get("name")
            if nm is None or p.get("owner", 0) != 0:
                continue
            zones = set((p["zone"],) if p.get("zone") else tuple(p.get("zones") or ()))
            n0, z0 = out.get(nm, (0, set()))
            out[nm] = (max(n0, p.get("n", 1)), z0 | zones)
    return out


def away_penalty(eng, need: dict, me: int = 0) -> float:
    """経路に要る札が、経路の段が指さないゾーン（マナ）に置かれた枚数（必要枚数まで）。"""
    tot = 0
    for nm, (n, zones) in need.items():
        for z in AWAY_ZONES:
            if z not in zones:
                tot += min(count(eng, {"zone": z, "match": {"name": nm}}, me), n)
    return float(tot)


def make_value_fn(stages, weights: Weights | None = None, *, mult: float = 1.0, partial: bool = False,
                  elsewhere: float = 0.25, away: float = 0.0, ratchet: list | None = None,
                  lookahead_last: int = 0, opp_policy=None):
    """evaluate + mult × (経路の点 [+ 次の段の部分点] − away × 使えないゾーンへ送った経路の札の枚数)。
    既定（partial=False, away=0, mult=1）は段を満たした分だけ（PR #423 と同じ）。勝敗が決まった局面には足さない。
    lookahead_last: >0 なら、入口の直前の段まで達成した葉に限り、次の自分のターンを予算 lookahead_last で探索して良い方を採る
      （search.multiturn.make_lookahead_value_fn と同じ。全部の葉にかけないので計算量の増加が小さい）。
    ratchet: [k] を渡すと、その対局で達成済みの段 k を下限にする（呼び出し側が各ターンの後に k を更新する。note_reached）。"""
    w = weights or Weights()
    need = needed_cards(stages) if away else {}
    cont = drawout_on() and bool(drawout_wins(stages))
    if cont:
        wins = drawout_wins(stages)
        e_idx = entry_index(stages)

    def value(eng, me: int) -> float:
        v = evaluate(eng, me, w)
        if result_of(eng) is not None:
            return v
        fl = ratchet[0] if ratchet else 0
        if cont:
            return v + mult * continuous_score(eng, stages, me, fl, wins, e_idx, partial, elsewhere)
        r = route_score(eng, stages, me, fl)
        if partial:
            r += partial_score(eng, stages, me, elsewhere, fl)
        if away:
            r -= away * away_penalty(eng, need, me)
        return v + mult * r
    if not lookahead_last:
        return value
    from .multiturn import make_lookahead_value_fn
    from .turn import charge_only_policy
    deep = make_lookahead_value_fn(value, lookahead_last, opp_policy or charge_only_policy, w)
    last = len(stages) - 1

    def gated(eng, me: int) -> float:
        if result_of(eng) is None and max(reached(eng, stages, me), ratchet[0] if ratchet else 0) >= last:
            return deep(eng, me)
        return value(eng, me)
    return gated


# --- 入口より後ろの連続点（§30、DMSIM_DRAWOUT=1 のときだけ）
DIG_W = 15.0     # 勝ちに必要な残り1枚あたりの点（段の weight 350〜500 に対し、ループ1周＝1枚で手の差がつく大きさ）
EARLY_W = 200.0  # 勝ち手段を早く出しすぎた（場にあるのに残り>0）ときの減点


def drawout_wins(stages) -> list[str]:
    return sorted({p["drawout"] for st in stages for p in st.preds if "drawout" in p})


def entry_index(stages) -> int:
    """入口の述語を含む最初の段（1始まり）。無ければ 0。"""
    for i, st in enumerate(stages, 1):
        if getattr(st, "has_entry", False):
            return i
    return 0


def continuous_score(eng, stages, me, floor, wins, e_idx, partial, elsewhere) -> float:
    """入口に届くまでは今まで通り。入口より後ろの段は、その対局で入口に届いた（floor ≥ 入口の段）か今入口を満たすときだけ数え、
    さらに勝ちに必要な残り（access.remaining）が少ないほど点を上げる。勝ち手段が場にあるのに残りが0でなければ減点（早出しの抑え）。"""
    from .access import remaining
    k_now = reached(eng, stages, me)
    seen = e_idx == 0 or floor >= e_idx or all(holds(eng, p, me) for p in stages[e_idx - 1].preds)
    if not seen:   # 入口を経ずに後ろの段を満たしても数えない（§30 の穴ふさぎ）
        k_now = max([i for i, st in enumerate(stages[:e_idx - 1], 1) if all(holds(eng, p, me) for p in st.preds)], default=0)
    k = max(k_now, floor if seen else min(floor, max(0, e_idx - 1)))
    r = sum(st.weight for st in stages[:k])
    if partial and k < len(stages) and (seen or k + 1 < e_idx):
        preds = stages[k].preds
        r += stages[k].weight * sum(_frac(eng, p, me, elsewhere) for p in preds) / len(preds)
    if seen and e_idx:
        rem = [x for x in (remaining(eng, i, me) for i in wins) if x is not None]
        if rem:
            best = min(rem)
            r -= DIG_W * best
            on_bz = any(count(eng, {"zone": "bz", "match": {"name": i}, "top": True}, me) for i in wins)
            if on_bz and best > 0:
                r -= EARLY_W
    return r


def note_reached(eng, stages, ratchet: list, me: int = 0) -> None:
    """ラチェットの更新: 真の局面で満たした段が今の下限より後ろなら上げる（下げない）。"""
    k = reached(eng, stages, me)
    if drawout_on() and drawout_wins(stages):   # §30: 入口を経ていなければ入口より後ろへは上げない
        e = entry_index(stages)
        if e and ratchet[0] < e and not all(holds(eng, p, me) for p in stages[e - 1].preds):
            k = min(k, max([i for i, st in enumerate(stages[:e - 1], 1) if all(holds(eng, p, me) for p in st.preds)], default=0))
    ratchet[0] = max(ratchet[0], k)


def hand_needs(eng, stages, me: int = 0, floor: int = 0) -> set[str]:
    """まだ達成していない段が手札に要求する札（§21）。段の述語から導き、カード名は見ない。
    - 手札を指す名前の述語（zone: hand、zones に hand を含む）。
    - 場を指す名前の述語で、まだ場に足りない札（手札から出す札）。
    手札にある枚数が必要枚数以下の札だけを返す（必要枚数より多い分は手放してよい）。"""
    k = max(reached(eng, stages, me), floor)
    need: dict[str, int] = {}
    away: set[str] = set()   # 先に墓地・マナなど手札・場以外へ送る段がまだ満たされていない札は残さない（例: 段1「シャコガイルが墓地」）
    for st in stages[k:]:
        for p in st.preds:
            nm = p.get("match", {}).get("name")
            if nm is None or p.get("owner", 0) != 0 or p.get("op", ">=") != ">=":
                continue
            zones = set((p["zone"],) if p.get("zone") else tuple(p.get("zones") or ()))
            n = p.get("n", 1)
            if not zones & {"hand", "bz"} and not holds(eng, p, me) and nm not in need:
                away.add(nm)
                continue
            if nm in away:
                continue
            if "hand" in zones:
                need[nm] = max(need.get(nm, 0), n)
            elif "bz" in zones and count(eng, {"zone": "bz", "match": {"name": nm}}, me) < n:
                need[nm] = max(need.get(nm, 0), n - count(eng, {"zone": "bz", "match": {"name": nm}}, me))
    out = set()
    for nm, n in need.items():
        h = count(eng, {"zone": "hand", "match": {"name": nm}}, me)
        if 0 < h <= n:
            out |= {eng.s.cards[c].defn for c in eng.s.zones["hand"][me]
                    if nm in (eng.s.cards[c].defn, eng.rules.cards[eng.s.cards[c].defn].id)}
    return out


def keep_hand(stages, me: int = 0, ratchet: list | None = None):
    """search.turn.KEEP_HAND に差す関数。自分の選択だけで、hand_needs の札を後回しにする。"""
    def f(eng, p):
        if p != me or not stages:
            return set()
        return hand_needs(eng, stages, me, ratchet[0] if ratchet else 0)
    return f
