"""ループ部品の組に「蓄積を勝ちに変える札」を足した3枚組を探す（S5、2026-11-14）。

既知の強いコンボ（サガ、アカシック3＋訪れる魔の時刻＋H.D.2.）はどれも「ループ部品＋蓄積を勝ちに変える札」の形なので、
2枚組の静的なふるいで勝ち手段まで求めず、ループの部品と勝ち手段を別々に集めてつなぐ。カード名は見ない（効果データの形だけ）。

(a) collect: 札1枚・2枚組の静的なループ判定（loop_screen.judge_set、条件を読む版）で閉路が閉じる組を広めに集める。
    勝ち手段がない（no_win）組も残し、1周の増減（どのゾーンがどれだけ増える・減るか）を記録する。足切りはせず、
    上限ターン（speed_bound.static_bound）・読めない条件の数・つながりの点を値として持たせる（順位づけに使う）。
(b) attach: 1周の増減を鍵に、蓄積→勝ち手段の索引（gain_index）から札を引いて3枚組にする。
    勝ち手段は物差しの段2に数えられる勝ち方（特殊勝利、相手の山札を動かす）を持つ札だけ。静的な3枚の判定も値として記録する。
(c) measure: 入口の局面（ループの最小パーツだけ。勝ち手段はデッキにある前提）で物差し（ruler.judge）にかけ、
    段1・段2・勝ったターンを測る。対照として同じ部品に勝ち手段の代わりにランダムな札を入れたデッキも測る（組の値＝差）。

入口の定義（ユーザー 2026-11-14）: 入口はループの最小パーツだけ。勝ち手段はデッキにある前提の別の段（段2）。
ここでは部品のうちクリーチャーは場、それ以外は手札に置き、残りの手札・盾・マナはデッキから配る（マナは入口のターン T 枚）。
山札は見えない公平探索（play_game の既定）、乱数はシードで固定。
"""
from __future__ import annotations

import random
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field

from . import gain_index as G
from . import loop_cond as C
from . import loop_screen as F


@dataclass
class Base:
    """ループ部品（1〜2枚）。gains は1周の増減 {(owner, zone): n}。"""
    cards: list[str]
    names: list[str]
    gains: dict
    has_win: bool                 # 部品だけで勝ち手段がある（静的）
    unknown: int                  # 読めない条件の数
    turn: int | None              # 速さの上限（静的）
    score: float = 0.0            # つながりの点（2枚組のみ）
    layout: dict = field(default_factory=dict)   # 入口で部品を置くゾーン {札: zone}（閉路の束から読む）
    grave: list = field(default_factory=list)    # 閉路が自分の墓地から拾う札の条件（入口で墓地に置く素材、filter の並び）

    def key(self):
        return tuple(sorted(self.cards))


@dataclass
class Triple:
    base: list[str]
    win: str
    names: list[str]
    gains: dict
    why: list[str]
    static: str                   # 3枚の静的判定（pass か落ちた理由。足切りには使わない）
    turn: int | None
    layout: dict = field(default_factory=dict)
    grave: list = field(default_factory=list)
    rank_key: tuple = ()
    measured: dict = field(default_factory=dict)

    def cards(self):
        return list(self.base) + [self.win]


def _gains(c) -> dict:
    side = getattr(c, "side", [])
    out = {}
    for k, v in F.net(list(c.bundles) + list(side)).items():
        out[("you", k)] = v
    for k, v in F.net(list(c.bundles) + list(side), "opp").items():
        out[("opp", k)] = v
    return {k: v for k, v in out.items() if v}


def layout_of(c, cards, rules) -> tuple[dict, list]:
    """閉路の束から入口の置き場所を読む。唱える・召喚する束の札は手札、誘発の札はその能力が働くゾーン
    （自分が出た時の誘発なら出す前の手札）。閉路が自分の墓地から（自分自身でなく）拾う移動があれば、その条件を素材として返す。"""
    ids = {rules.cards[x].id: x for x in cards}
    lay, grave = {}, []
    for b in list(c.bundles) + list(getattr(c, "side", [])):
        x = ids.get(b.card)
        if x is None:
            continue
        p = b.prem
        if b.origin in ("spell", "summon") or p is None:
            z = "hand"
        elif p.kind == "move" and p.subject == "self" and p.to == p.zone:
            z = "hand"
        else:
            z = p.zone or "bz"
        lay.setdefault(x, z)
        for m in b.moves:
            if F._zone(m.src) == "graveyard" and m.owner == "you" and not m.ref_self and not m.draw:
                grave.append(dict(m.flt))
    for x in cards:
        if x not in lay:
            lay[x] = "bz" if "creature" in rules.cards[x].types else "hand"
        if lay[x] == "bz" and "creature" not in rules.cards[x].types:
            lay[x] = "hand"
    return lay, grave


def by_card_of(rules) -> dict:
    by = defaultdict(list)
    for b in C.bundles(rules):
        by[b.card].append(b)
    return by


def collect(rules, by_card, *, max_turn: int = 5, singles: bool = True, pairs: bool = True, limit: int = 0, log=None) -> tuple[list[Base], Counter]:
    """(a) 閉路が閉じる札1枚・2枚組。勝ち手段の有無は問わない。落ちた理由の内訳も返す。"""
    from .candidates import candidate_pairs
    from ..eval import speed_bound as S
    ids, _ = F.usable_ids(rules)
    out, drop = [], Counter()
    t0 = time.time()
    sets = []
    if singles:
        sets += [{"cards": [x], "score": 0.0} for x in ids if by_card.get(rules.cards[x].id)]
    if pairs:
        sets += [{"cards": [p["a"], p["b"]], "score": p["score"]} for p in F.unordered(candidate_pairs(rules, ids))]
    if log:
        log(f"(a) 対象 {len(sets)} 組 {time.time()-t0:.0f}s")
    for i, s in enumerate(sets):
        if limit and len(out) >= limit:
            break
        r, cyc = F.judge_set(s["cards"], by_card, rules, max_len=4 if len(s["cards"]) == 2 else 6)
        if r not in (None, "no_win") or not cyc:
            drop[r] += 1
            continue
        t = S.static_bound(rules, s["cards"])["turn"]
        if t is None or t > max_turn:
            drop["slow"] += 1
            continue
        c = cyc[0]
        lay, grave = layout_of(c, s["cards"], rules)
        out.append(Base(cards=s["cards"], names=[rules.cards[x].name for x in s["cards"]], gains=_gains(c),
                        has_win=r is None, unknown=getattr(c, "unknown", 0), turn=t, score=s["score"], layout=lay, grave=grave))
        if log and i % 100000 == 0:
            log(f"  {i}/{len(sets)} 残り {len(out)} {time.time()-t0:.0f}s")
    # 1枚で閉じる札を含む2枚組は、1枚の方に吸収する（同じループの言い換え）
    one = {b.cards[0] for b in out if len(b.cards) == 1}
    kept = [b for b in out if len(b.cards) == 1 or not (set(b.cards) & one)]
    drop["covered_by_single"] = len(out) - len(kept)
    return kept, drop


def win_cards(rules, raw=None) -> set[str]:
    """物差しの段2に数えられる勝ち方の札（特殊勝利・相手の山札を動かす）で、効果データが欠けていないもの。"""
    from .basebuild import _raw_cards, missing_effect
    raw = raw if raw is not None else _raw_cards(rules)
    out = set()
    for cid, d in rules.cards.items():
        if cid.startswith("T") or (cid in raw and missing_effect(d)):
            continue
        if C.win_paths(d):
            out.add(cid)
            continue
        for f in (getattr(d, "faces", None) or [d]):
            effs = [ab.get("effect") or [] for ab in (f.abilities or [])] + [getattr(f, "spell", None) or []]
            if any((op.get("op") == "move" and (op.get("select") or {}).get("owner") == "opp" and (op.get("select") or {}).get("zone") == "deck")
                   or (op.get("op") == "draw" and op.get("player") == "opp")
                   for eff in effs for op, _ in C._all_ops_with_conds(eff)):
                out.add(cid)
                break
    return out


def attach(rules, by_card, bases: list[Base], *, per_base: int = 8, idx=None, wins=None, log=None) -> list[Triple]:
    """(b) 1周の増減から索引で勝ち手段を引いて3枚組（部品1枚なら2枚組）にする。"""
    from ..eval import speed_bound as S
    idx = idx if idx is not None else G.build(rules)
    wins = wins if wins is not None else win_cards(rules)
    out = []
    for b in bases:
        hits = [h for h in G.lookup(idx, b.gains, rules, top=0) if h["id"] in wins and h["id"] not in b.cards]
        for h in hits[:per_base]:
            cs = list(b.cards) + [h["id"]]
            r, _ = F.judge_set(cs, by_card, rules)
            t = S.static_bound(rules, cs)["turn"]
            tr = Triple(base=list(b.cards), win=h["id"], names=[rules.cards[x].name for x in cs], gains=b.gains,
                        why=h["why"], static=r or "pass", turn=t, layout=dict(b.layout), grave=list(b.grave))
            # 順位: 静的に3枚で通る・当たった鍵の数・読めない条件の少なさ・上限ターン・つながりの点
            tr.rank_key = (tr.static != "pass", -len(h["why"]), b.unknown, t if t is not None else 99, -b.score)
            out.append(tr)
    out.sort(key=lambda t: t.rank_key)
    if log:
        log(f"(b) 3枚組 {len(out)}（部品 {len(bases)}）静的に通る {sum(t.static == 'pass' for t in out)}")
    return out


# ---- (c) 物差し -------------------------------------------------------------------------------

def deck_of(rules, cards: list[str], raw=None) -> list[str]:
    from . import basebuild as B
    core = {i: B.COPIES for i in cards}
    fill = B.fillers(rules, core, raw if raw is not None else B._raw_cards(rules)) or ["T022"]   # 文明に合う札が無ければ試験札
    return B.base_deck(core, fill)


def entry_spec(rules, deck, parts: list[str], T: int, seed: int, layout: dict | None = None, grave=()) -> dict:
    """入口: 部品を layout のゾーン（無ければクリーチャーは場、それ以外は手札）に1枚ずつ。閉路が墓地から拾うなら、
    条件に合う札を2枚まで墓地へ（部品の別のコピーを先に）。残りはデッキから配る（マナ T 枚、手札は計5枚、盾5枚）。"""
    rng = random.Random(seed * 7919 + T)
    layout = layout or {}
    zones = {"bz": [], "hand": [], "graveyard": [], "mana": []}
    for i in parts:
        z = layout.get(i) or ("bz" if "creature" in rules.cards[i].types else "hand")
        zones[z if z in zones else "hand"].append(i)
    rest = list(deck)
    for i in parts:
        rest.remove(i)
    rng.shuffle(rest)
    for flt in list(grave)[:1]:
        pref = [i for i in rest if i in parts] + [i for i in rest if i not in parts]
        for i in pref:
            if len(zones["graveyard"]) >= 2:
                break
            if F._admits(flt, rules.cards[i]):
                zones["graveyard"].append(i)
                rest.remove(i)
    need = set()
    for i in parts:
        need |= set(rules.cards[i].civs)
    mana = zones["mana"]
    for c in sorted(need):
        for i in rest:
            if c in rules.cards[i].civs and len(mana) < T:
                mana.append(i)
                rest.remove(i)
                break
    while len(mana) < T:
        mana.append(rest.pop())
    hand = zones["hand"]
    while len(hand) < 5:
        hand.append(rest.pop())
    shield = [rest.pop() for _ in range(5)]
    p0 = {"bz": zones["bz"], "hand": hand, "mana": mana, "shield": shield, "graveyard": zones["graveyard"], "deck": sorted(rest)}
    return {"p0": p0, "p1": {"hand": ["T001"] * 5, "mana": ["T001"] * max(0, T - 1)}, "deck_size": 40,
            "deck_exact": [True, False], "deck_left": [None, 40 - 10 - max(0, T - 1)], "seed": seed}


def measure(rules, deck, parts, *, T: int = 3, seeds=range(1, 5), budget: int = 1500, last_turn: int = 4, win_ids=None,
            layout=None, grave=()) -> dict:
    """入口のターン T から自分の last_turn ターン目の終わりまで。段1・段2・勝ったターン（入口の T を足した自分のターン）。"""
    from ..engine import scenario
    from ..eval.lockcheck import lock_probe
    from ..eval.ruler import judge
    from ..search.game import play_game
    rows = []
    for sd in seeds:
        try:
            e = scenario.build(rules, entry_spec(rules, deck, parts, T, sd, layout, grave), first_player=0)
            res, eng = play_game(rules, deck, [], sd, first_player=0, max_turn=last_turn + 1 - T, budget=budget, start=e,
                                 lock_judge=lock_probe)
            v = judge(res, eng, win_ids=win_ids)
            wt = None if v.stage2.win_turn is None else v.stage2.win_turn + T - 1
            rows.append({"seed": sd, "stage1": v.stage1.ok, "laps": v.stage1.n, "infinite": v.stage1.infinite,
                         "stage2": v.stage2.ok, "via": v.stage2.via, "kill": v.stage2.kill, "win_turn": wt, "error": res.error})
        except Exception as ex:   # 効果データが未対応で局面が作れない・対局が落ちる
            rows.append({"seed": sd, "stage1": False, "laps": 0, "infinite": False, "stage2": False, "via": None, "kill": False,
                         "win_turn": None, "error": f"{type(ex).__name__}: {ex}"[:200]})
    n = len(rows)
    wts = [r["win_turn"] for r in rows if r["stage2"] and r["win_turn"] is not None]
    return {"games": n, "stage1": sum(r["stage1"] for r in rows), "stage2": sum(r["stage2"] for r in rows),
            "kill": sum(r["kill"] for r in rows), "beat": sum(1 for r in rows if r["via"] == "beat"),
            "fast_stage2": sum(1 for w in wts if w <= last_turn), "best_turn": min(wts) if wts else None,
            "max_laps": max((r["laps"] for r in rows), default=0), "errors": sum(1 for r in rows if r["error"]), "rows": rows}


def control_card(rules, pool: list[str], exclude, rng) -> str:
    while True:
        x = rng.choice(pool)
        if x not in exclude:
            return x


def value(m: dict, ctrl: dict) -> dict:
    """組の値: 段1・段2・速い段2の率と、対照（勝ち手段の代わりにランダムな札）との差。足切りはしない。"""
    g = max(1, m["games"])
    return {"stage1_rate": m["stage1"] / g, "stage2_rate": m["stage2"] / g, "fast_rate": m["fast_stage2"] / g,
            "best_turn": m["best_turn"], "delta_stage2": (m["stage2"] - ctrl["stage2"]) / g,
            "delta_stage1": (m["stage1"] - ctrl["stage1"]) / g}


def as_row(t: Triple) -> dict:
    d = asdict(t)
    d["gains"] = {f"{o}:{z}": v for (o, z), v in t.gains.items()}
    d.pop("rank_key", None)
    return d
