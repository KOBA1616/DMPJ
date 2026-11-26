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
            if m.from_any("graveyard") and m.owner == "you" and not m.ref_self and not m.draw:
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


def default_zone(rules, i) -> str:
    """閉路から置き場所が読めない部品の既定: 呪文の面を持たないクリーチャーと常在能力だけの札（無償詠唱など）は場、それ以外は手札。"""
    t = rules.cards[i].types
    if F.free_cast(rules.cards[i]):
        return "bz"
    return "bz" if "creature" in t and "spell" not in t else "hand"


def entry_spec(rules, deck, parts: list[str], T: int, seed: int, layout: dict | None = None, grave=(), opp_bz=()) -> dict:
    """入口: 部品を layout のゾーン（無ければクリーチャーは場、それ以外は手札）に1枚ずつ。閉路が墓地から拾うなら、
    条件に合う札を2枚まで墓地へ（部品以外を先に）。残りはデッキから配る（マナ T 枚、手札は計5枚、盾5枚）。"""
    rng = random.Random(seed * 7919 + T)
    layout = layout or {}
    zones = {"bz": [], "hand": [], "graveyard": [], "mana": []}
    for i in parts:
        z = layout.get(i) or default_zone(rules, i)
        zones[z if z in zones else "hand"].append(i)
    rest = list(deck)
    for i in parts:
        rest.remove(i)
    rng.shuffle(rest)
    for flt in list(grave)[:1]:
        from ..search.access import _fits

        def fits(i):          # 条件（種族・コストまで）に合うか。読めない条件は種類だけで見る
            try:
                return _fits(rules, i, {"filter": flt})
            except TypeError:
                return F._admits(flt, rules.cards[i])
        # 素材は条件に合う部品以外を先に、次に条件に合う部品のコピー（部品のコピーは手札に残したい。サガは種族で部品しか合わない）
        pref = [i for i in rest if i not in parts and fits(i)] + [i for i in rest if i in parts and fits(i)]
        for i in pref:
            if len(zones["graveyard"]) >= 2:
                break
            if True:
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
    p1 = {"hand": ["T001"] * 5, "mana": ["T001"] * max(0, T - 1)}
    if opp_bz:
        p1["bz"] = list(opp_bz)
    return {"p0": p0, "p1": p1, "deck_size": 40,
            "deck_exact": [True, False], "deck_left": [None, 40 - 10 - max(0, T - 1) - len(opp_bz)], "seed": seed}


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


# ---- (i) 実エンジンの安い試し打ち（2026-11-14） ----------------------------------------------------

def _once_per_turn(rules, cards) -> bool:
    def walk(x):
        if isinstance(x, dict):
            if x.get("once_per_turn") or "max_per_turn" in x:
                return True
            return any(walk(v) for v in x.values())
        if isinstance(x, list):
            return any(walk(v) for v in x)
        return False
    for i in cards:
        d = rules.cards[i]
        for f in (getattr(d, "faces", None) or [d]):
            if walk(f.abilities or []):
                return True
    return False


def _free_any(rules, cards) -> bool:
    return any(F.free_cast(rules.cards[i]) for i in cards)


def static_flags(base: Base) -> list[str]:
    """静的には閉じても実際に回りにくい形（試し打ちで多かった理由を、静的ふるいの側で先に印として付ける。落とさない）。
    opp_target: 1周で相手の場の札を減らす（相手にクリーチャーがいないと回らない。今の相手はマナチャージだけ）。
    copy_chain: 山札から場へ出す移動で回る（山札にある別のコピーを順に出すだけで、コピーの枚数で止まる）。
    zero: 1周の増減が何もない（何も貯まらず、物差しの段1に数えられない）。"""
    g = base.gains
    out = []
    if g.get(("opp", "bz"), 0) < 0:
        out.append("opp_target")
    if g.get(("you", "bz"), 0) > 0 and g.get(("you", "deck"), 0) < 0:
        out.append("copy_chain")
    if not g:
        out.append("zero")
    return out


def why_not(rules, base: Base, rows: list[dict], T: int) -> str:
    """静的には閉じるが実際は回らない理由（試し打ちの記録と効果データから。名前は見ない）。
    error 対局が落ちた / not_played 部品を一度も使わない（cost: 部品のコストが入口のマナを超える、else: 使う手を選ばない）/
    opp_target / copy_chain / zero は static_flags の印 / once 1ターンに1回などの回数制限 / target 閉路が墓地から拾う札がいない（素材が要る）/ cond 読めない条件がある /
    once_only 部品は使ったが2周目に入らない（その他）。"""
    if all(r.get("error") for r in rows):
        return "error"
    fl = [f for f in static_flags(base) if not (f == "opp_target" and any(r.get("opp_bz") for r in rows))]
    if fl:
        return fl[0]
    if not any(r.get("uses") for r in rows):
        costs = [rules.cards[i].cost for i in base.cards if isinstance(rules.cards[i].cost, int)]
        if costs and min(costs) > T and not _free_any(rules, base.cards):
            return "cost"
        return "not_played"
    if _once_per_turn(rules, base.cards):
        return "once"
    if base.unknown:
        return "cond"
    if base.grave:
        return "target"
    return "once_only"


def helper_spell(rules, civs, raw=None) -> str | None:
    """つなぎの呪文: 部品の文明に収まる最も軽い呪文（効果データが欠けていないもの。名前は見ない）。"""
    from . import basebuild as B
    raw = raw if raw is not None else B._raw_cards(rules)
    best = None
    for i, d in sorted(rules.cards.items()):
        if B._test(i) or "spell" not in d.types or "creature" in d.types or not isinstance(d.cost, int):
            continue
        if not set(d.civs) <= set(civs) or (i in raw and B.missing_effect(d)):
            continue
        if best is None or d.cost < rules.cards[best].cost:
            best = i
    return best


def layouts(rules, base: Base, raw=None) -> list[dict]:
    """試し打ちの入口の置き方。cycle: 閉路の束から読んだ置き方。bz_spell: クリーチャーの部品は場、手札につなぎの呪文
    （「呪文を唱えた時」で回る部品は、閉路が呪文の面＝ツインパクトを使うと読んでも、実際はクリーチャーの面で場にいて
    別の呪文で回すことが多い。マチュー＋ベルリン）。"""
    out = [{"name": "cycle", "parts": list(base.cards), "layout": dict(base.layout), "extra": []}]
    cre = [i for i in base.cards if "creature" in rules.cards[i].types]
    if cre:
        civs = {c for i in base.cards for c in rules.cards[i].civs}
        sp = helper_spell(rules, civs, raw)
        lay = {i: ("bz" if i in cre else "hand") for i in base.cards}
        if sp and sp not in base.cards:
            lay[sp] = "hand"
            out.append({"name": "bz_spell", "parts": list(base.cards) + [sp], "layout": lay, "extra": [sp]})
        elif lay != base.layout:
            out.append({"name": "bz", "parts": list(base.cards), "layout": lay, "extra": []})
        # double: 閉路の置き方のまま、常在能力だけの部品（無償で唱えさせる等）は場、手札の部品は2枚ずつ
        # （同じ札の別のコピー同士で回収し合うループ。アカシック3＋訪れる魔の時刻2枚）。ツインパクトは閉路の置き方に従う。
    if True:
        lay = {i: base.layout.get(i) or default_zone(rules, i) for i in base.cards}
        for i in base.cards:
            if F.free_cast(rules.cards[i]):
                lay[i] = "bz"
        hand = [i for i in base.cards if lay.get(i) == "hand"]
        if hand:
            out.append({"name": "double", "parts": list(base.cards) + hand, "layout": lay, "extra": list(hand)})
    return out


def spends_hand(delta: dict, me: int = 0) -> bool:
    """1周で自分の手札が減る繰り返し（手札の札を順に使うだけ。物差しの段1は数えるが、手札が尽きれば止まる有限の消費）。"""
    return (delta or {}).get(f"hand:{me}", 0) < 0


def trial(rules, base: Base, *, T: int = 4, seeds=(1, 2), budget: int = 100, raw=None, turns: int = 2, opp_bz=()) -> dict:
    """入口（部品だけ）から turns ターン（既定2: 入口のターンに部品を出し、次のターンで回す形を拾う。マチュー＋ベルリン）、小さい予算で実エンジンを回す。段1＝検証済みのループを2周以上。
    置き方（layouts）を順に試し、どれかで通れば通過。記録: 周回数、1周の増減、部品を使った回数。"""
    from ..engine import scenario
    from ..eval.lockcheck import lock_probe
    from ..eval.ruler import judge
    from ..search.game import play_game
    rows = []
    ids = set(base.cards) | {rules.cards[i].id for i in base.cards}
    for lo in layouts(rules, base, raw):
        deck = deck_of(rules, lo["parts"], raw)
        for sd in seeds:
            try:
                e = scenario.build(rules, entry_spec(rules, deck, lo["parts"], T, sd, lo["layout"], base.grave, opp_bz), first_player=0)
                res, eng = play_game(rules, deck, [], sd, first_player=0, max_turn=turns, budget=budget, start=e, lock_judge=lock_probe)
                v = judge(res, eng)
                uses = sum(1 for lg in eng.log if lg.get("p") == 0 and any(i in str(k) for k in lg.get("keys") or [] for i in ids))
                rows.append({"layout": lo["name"], "extra": lo["extra"], "seed": sd, "opp_bz": list(opp_bz), "ok": v.stage1.ok and v.stage1.n >= 2 and not spends_hand(v.stage1.delta),
                             "laps": v.stage1.n, "infinite": v.stage1.infinite, "delta": v.stage1.delta, "uses": uses, "error": res.error})
            except Exception as ex:
                rows.append({"layout": lo["name"], "extra": lo["extra"], "seed": sd, "ok": False, "laps": 0, "infinite": False,
                             "delta": {}, "uses": 0, "error": f"{type(ex).__name__}: {ex}"[:200]})
        if any(r["ok"] for r in rows):
            break
    ok = any(r["ok"] for r in rows)
    return {"ok": ok, "rows": rows, "laps": max(r["laps"] for r in rows),
            "layout": next((r["layout"] for r in rows if r["ok"]), None),
            "reason": None if ok else why_not(rules, base, rows, T)}


# ---- (ii) 山札を掘るループ → デッキ内の任意の勝ち手段（2026-11-14） ----------------------------------

def digs(base: Base) -> bool:
    """1周で自分の山札に触れる（引く・墓地へ落とす・マナへ置く・山札から加える）量が正のループ。"""
    return base.gains.get(("you", "deck"), 0) < 0


def attach_dig(rules, bases: list[Base], *, per_base: int = 8, wins=None, max_cost: int = 8) -> list[Triple]:
    """掘るループに、デッキに入れた勝ち手段なら掘って届くとみなして札を足す（索引の鍵は問わない）。
    届いた札が使えるか: 掘った札が経由するゾーン（増えるゾーン、無ければ手札）から使えること（search.access.usable_from。
    墓地なら墓地進化か、部品・勝ち手段に墓地から出す効果）。ドロー置換の勝ち（access.draw_win）は引くループ（手札が増える）なら
    「引き切り」として先に並べる。順位: 引き切り・部品と文明が重なる・軽い・ID。"""
    from ..search import access as A
    wins = wins if wins is not None else win_cards(rules)
    out = []
    for b in bases:
        if not digs(b):
            continue
        via = [z for z in A.VIA_ZONES if b.gains.get(("you", z), 0) > 0] or ["hand"]
        civs = {c for i in b.cards for c in rules.cards[i].civs}
        rows = []
        for w in sorted(wins):
            d = rules.cards[w]
            if w in b.cards or not isinstance(d.cost, int) or d.cost > max_cost:
                continue
            users = A._grave_users(rules, list(b.cards) + [w])
            zs = []
            for z in via:
                try:
                    if A.usable_from(rules, w, z, users):
                        zs.append(z)
                except TypeError:      # 条件の形が読めない（cost_le が式など）。使えないとみなす
                    pass
            dw = A.draw_win(rules, w)
            if not zs and not dw:
                continue
            why = []
            if dw and b.gains.get(("you", "hand"), 0) > 0:
                why.append("you:deck:- 引くループで山札を引き切る（ドロー置換の勝ち）")
            if zs:
                why.append(f"you:deck:- 掘って {'/'.join(zs)} から使える")
            rows.append((not (dw and b.gains.get(("you", "hand"), 0) > 0), not (set(d.civs) & civs), d.cost, w, why))
        rows.sort()
        for _, _, cost, w, why in rows[:per_base]:
            tr = Triple(base=list(b.cards), win=w, names=[rules.cards[x].name for x in list(b.cards) + [w]], gains=b.gains,
                        why=why, static="dig", turn=b.turn, layout=dict(b.layout), grave=list(b.grave))
            tr.rank_key = (b.turn if b.turn is not None else 99, len(why) and -len(why), cost)
            out.append(tr)
    out.sort(key=lambda t: t.rank_key)
    return out


# ---- 2周目に入らない組の確認: 1周目の手順をそのまま再生する（2026-11-14） ---------------------------

def replay_check(rules, base: Base, *, T: int = 4, seed: int = 1, budget: int = 100, turns: int = 2, layout: str = "cycle",
                 raw=None, max_mains: int = 4, repeats: int = 3) -> dict:
    """試し打ちの1局の決定の記録から、部品を使う最初の手（main）から始まる k 手（k=1..max_mains）を「1周」とみなし、
    同じ意味キー（手札の札は WILD_HAND で引いた札に置き換え可）で repeats 回くり返せるかを、探索に選ばせず直接再生して確かめる。
    くり返せて、各周の終わりの骨格（engine.loop.abstract）が同じで何かが変わる（増減がある）なら「探索が選べないだけ」。"""
    from ..engine import scenario
    from ..engine import loop as LP
    from ..eval.lockcheck import lock_probe
    from ..search.game import play_game
    lo = next((x for x in layouts(rules, base, raw) if x["name"] == layout), None)
    if lo is None:
        return {"result": "no_layout"}
    deck = deck_of(rules, lo["parts"], raw)
    e0 = scenario.build(rules, entry_spec(rules, deck, lo["parts"], T, seed, lo["layout"], base.grave), first_player=0)
    _, eng = play_game(rules, deck, [], seed, first_player=0, max_turn=turns, budget=budget, start=e0.clone(), lock_judge=lock_probe)
    log = list(eng.log)
    ids = set(base.cards) | {rules.cards[i].id for i in base.cards}
    mains = [k for k, lg in enumerate(log) if lg.get("p") == 0 and lg.get("kind") == "main"]
    first = next((k for k in mains if any(i in str(x) for x in lg_keys(log[k]) for i in ids)), None)
    if first is None:
        return {"result": "not_played"}
    hand0 = None
    best = {"result": "cannot_repeat", "k": None, "repeats": 0}
    for n in range(1, max_mains + 1):
        after = [k for k in mains if k > first]
        end = after[n - 1] if len(after) >= n else len(log)
        tmpl = log[first:end]
        if any(lg.get("p") != 0 for lg in tmpl):
            break                                  # 相手の決定が挟まる（ターンをまたぐ）手は1周に数えない
        e = e0.clone()
        try:
            for lg in log[:end]:
                e.answer_by_keys(list(lg["keys"]))
        except Exception:
            break
        hand0 = {e.s.cards[c].defn for c in e.s.zones["hand"][0]}
        sk0, ct0 = LP.abstract(e)
        ok, changed = 0, False
        for _ in range(repeats):
            try:
                for lg in tmpl:
                    if e.s.waiting is None:
                        raise LP.IllegalAnswer("no decision")
                    LP.replay_keys(e, LP.wild_keys(list(lg["keys"]), hand0), hand0)
            except Exception:
                break
            sk, ct = LP.abstract(e)
            if sk != sk0:
                break
            changed = changed or ct != ct0
            ok += 1
        if ok > best["repeats"]:
            best = {"result": "search_miss" if ok >= 2 and changed else ("repeat_no_gain" if ok >= 2 else "cannot_repeat"),
                    "k": n, "repeats": ok}
        if best["result"] == "search_miss":
            break
    return best


def lg_keys(lg) -> list:
    return list(lg.get("keys") or [])


# ---- 3. ループ部品を3枚まで広げる（2026-11-14） ---------------------------------------------------

def peaky(rules, ids) -> list[str]:
    """ピーキーな効果を持つ札: 無償で唱えさせる・出させる常在能力、または効果で無償で使う（play_free: コスト踏み倒し、
    出し直し・唱え直しを含む）。名前は見ない。"""
    out = []
    for i in ids:
        d = rules.cards[i]
        if F.free_cast(d):
            out.append(i)
            continue
        for f in (getattr(d, "faces", None) or [d]):
            effs = [ab.get("effect") or [] for ab in (f.abilities or [])] + [getattr(f, "spell", None) or []]
            if any(op.get("op") == "play_free" for eff in effs for op, _ in C._all_ops_with_conds(eff)):
                out.append(i)
                break
    return out


def triangle_sets(rules, by_card, ids, seeds: list[str], log=None, anchors: list[str] | None = None, need: dict | None = None) -> list[list[str]]:
    """a → b → c → a（3枚とも seeds の札）と束が狙って受け渡す（zone_graph.feeds == 2）3枚の組。2枚では閉じない3枚の閉路の候補。
    受け渡しは束の前提を見るだけの過大近似で、組ごとに judge_set（3枚の静的判定）を通す。"""
    from ..engine import zone_graph as Z
    t0 = time.time()
    # 3枚とも seeds（ピーキーな札）の中で探す。全札を相手にすると1枚目だけで数十万組になる（2026-11-14 実測）
    allb = [(rules.cards[x].id, x, b) for x in seeds for b in by_card.get(rules.cards[x].id, [])]
    succ_cache = {}

    def succ(x):
        if x not in succ_cache:
            mine = by_card.get(rules.cards[x].id, [])
            succ_cache[x] = {y for _, y, b in allb if y != x and any(Z.feeds(a, b, rules) == 2 for a in mine)}
        return succ_cache[x]

    out = set()
    first = anchors if anchors is not None else seeds    # anchors: 1枚目をこの札に限る（3枚のうち少なくとも1枚がこれ）
    for n, a in enumerate(first):
        sa = succ(a)
        mine = by_card.get(rules.cards[a].id, [])
        pred = {y for _, y, b in allb if y != a and any(Z.feeds(b, m, rules) == 2 for m in mine)}
        nd = (need or {}).get(a)     # need[a]: 残り2枚のどちらかがこの集合の札であること（重い札とそれを出す札）
        for b in sa:
            for c in succ(b) & pred:
                if c != b and (nd is None or b in nd or c in nd):
                    out.add(tuple(sorted((a, b, c))))
        if log and n % 50 == 0:
            log(f"  三角 {n}/{len(first)} 組 {len(out)} {time.time()-t0:.0f}s")
    return [list(x) for x in sorted(out)]


def collect3(rules, by_card, *, seeds=None, log=None) -> tuple[list[Base], Counter]:
    """3枚の部品: triangle_sets の組を judge_set にかけ、閉じる組を Base にする（速さの上限は値として記録、足切りしない）。"""
    from ..eval import speed_bound as S
    ids, _ = F.usable_ids(rules)
    seeds = seeds if seeds is not None else peaky(rules, ids)
    sets = helper_sets(rules, by_card, ids, log=log)
    seen = {tuple(x) for x in sets}
    sets += [x for x in triangle_sets(rules, by_card, ids, [x for x in seeds if by_card.get(rules.cards[x].id)], log=log)
             if tuple(x) not in seen]
    if log:
        log(f"(3) 三角の組 {len(sets)}（種 {len(seeds)}）")
    out, drop = [], Counter()
    for cs in sets:
        r, cyc = F.judge_set(cs, by_card, rules)
        if r not in (None, "no_win") or not cyc:
            drop[r] += 1
            continue
        c = cyc[0]
        lay, grave = layout_of(c, cs, rules)
        out.append(Base(cards=cs, names=[rules.cards[x].name for x in cs], gains=_gains(c), has_win=r is None,
                        unknown=getattr(c, "unknown", 0), turn=S.static_bound(rules, cs)["turn"], layout=lay, grave=grave))
    return out, drop


def helper_sets(rules, by_card, ids, log=None) -> list[list[str]]:
    """無償で唱えさせる・出させる常在能力の札 h（アカシック3など）と、h が対象にする札どうしで束が狙って受け渡し合う2枚
    （x→y→x、または x が自分を戻す）の3枚組。2枚では「マナが閉じない」で落ちる組を、マナの穴を埋める3枚目で補う形。"""
    from ..engine import zone_graph as Z
    t0 = time.time()
    out = set()
    for h in ids:
        fl = F.free_cast(rules.cards[h])
        if not fl:
            continue
        nodes = [x for x in ids if x != h and any(F._admits(f, rules.cards[x]) for f in fl) and by_card.get(rules.cards[x].id)]
        bs = {x: by_card.get(rules.cards[x].id, []) for x in nodes}
        # 回収する札（自分の墓地から手札・場へ狙って戻す束を持つ札）を片方に要る。総当たりを避ける
        rec = [x for x in nodes if any(m.from_any("graveyard") and m.dst in ("hand", "bz") and not m.blind
                                       for b in bs[x] for m in b.moves)]
        for x in rec:
            for y in nodes:
                if y == x:
                    continue
                if any(Z.feeds(a, b, rules) == 2 for a in bs[x] for b in bs[y]) and \
                        any(Z.feeds(b, a, rules) == 2 for a in bs[x] for b in bs[y]):
                    out.add(tuple(sorted((x, y, h))))
        if log:
            log(f"  補助 {rules.cards[h].name}: 対象 {len(nodes)} 回収 {len(rec)} 組 {len(out)} {time.time()-t0:.0f}s")
    return [list(x) for x in sorted(out)]


def zero_extend(rules, by_card, base: Base, wins, k: int = 10) -> list[Base]:
    """1周の増減がない閉路（同じ状態に戻るだけ。アカシック3＋訪れる魔の時刻＋ナウ・オア・ネバー）に、閉路が毎周誘発させて
    何かを動かす札（勝ち手段の札のうち、足すと静的判定を通るもの）を1枚足した部品。増減がないと物差しの段1に数えられないため。"""
    out = []
    for w in sorted(wins, key=lambda x: (rules.cards[x].cost if isinstance(rules.cards[x].cost, int) else 99, x)):   # 軽い順
        if w in base.cards:
            continue
        cs = list(base.cards) + [w]
        r, cyc = F.judge_set(cs, by_card, rules)
        if r is not None or not cyc:
            continue
        g = _gains(cyc[0])
        if not g:
            continue
        lay, grave = layout_of(cyc[0], cs, rules)
        lay = {**base.layout, **{x: z for x, z in lay.items() if x not in base.layout}}
        out.append(Base(cards=cs, names=[rules.cards[x].name for x in cs], gains=g, has_win=True, unknown=getattr(cyc[0], "unknown", 0),
                        turn=base.turn, layout=lay, grave=list(base.grave)))
        if len(out) >= k:
            break
    return out


def cheap_seeds(rules, by_card, ids, max_cost: int = 4) -> list[str]:
    """軸がコスト max_cost 以下の部品の種: その札が無償で使わせる・出す（peaky）か、自分の墓地・マナ・盾・場から手札・場へ
    狙って札を動かす束を持つ（ゾーン間移動を補完し合う札）。名前は見ない。"""
    cheap = [i for i in ids if isinstance(rules.cards[i].cost, int) and rules.cards[i].cost <= max_cost and by_card.get(rules.cards[i].id)]
    pk = set(peaky(rules, cheap))

    def mover(i):
        return any(m.owner == "you" and not m.blind and m.from_any("graveyard", "mana", "shield", "bz") and m.dst in ("hand", "bz")
                   for b in by_card[rules.cards[i].id] for m in b.moves)
    return [i for i in cheap if i in pk or mover(i)]


def collect_cheap(rules, by_card, *, max_cost: int = 4, max_turn: int = 4, log=None) -> tuple[list[Base], Counter]:
    """(2) 軸がコスト max_cost 以下の札だけで閉じる3枚の部品（cheap_seeds どうしの三角）。速さの上限 max_turn 以内だけ残す
    （3〜4ターンキルが目標なので、この段では上限ターンでふるう。指揮役の指示 2026-11-15）。"""
    from ..eval import speed_bound as S
    ids, _ = F.usable_ids(rules)
    seeds = cheap_seeds(rules, by_card, ids, max_cost)
    sets = triangle_sets(rules, by_card, ids, seeds, log=log)
    if log:
        log(f"(2) 安い三角 {len(sets)}（種 {len(seeds)}）")
    out, drop = [], Counter()
    for cs in sets:
        t = S.static_bound(rules, cs)["turn"]
        if t is None or t > max_turn:
            drop["slow"] += 1
            continue
        r, cyc = F.judge_set(cs, by_card, rules)
        if r not in (None, "no_win") or not cyc:
            drop[r] += 1
            continue
        c = cyc[0]
        lay, grave = layout_of(c, cs, rules)
        out.append(Base(cards=cs, names=[rules.cards[x].name for x in cs], gains=_gains(c), has_win=r is None,
                        unknown=getattr(c, "unknown", 0), turn=t, layout=lay, grave=grave))
    return out, drop


# ---- 早く出せる重い札（指揮役 2026-11-16）: 印刷コストではなく「実際に出せる早さ」で範囲を広げる ----
SELF_FAST = ("free_if", "alt_cost", "mana_bakutan", "fushigi", "mugen_climb", "cost_reduce_per_evo", "tap_reduce")


def _self_fast(d, max_cost: int) -> str | None:
    """重い札 d が自分の能力で早く出る経路の名前（G・ゼロ、代替コスト、マナ爆誕、フシギバース、ムゲンクライム、軽減）。無ければ None。"""
    from ..eval import speed_bound as S
    for f in S._faces(d):
        for k in SELF_FAST:
            v = getattr(f, k, None)
            if not v:
                continue
            if k == "mana_bakutan" and not (isinstance(v, int) and v <= max_cost):
                continue
            if k in ("alt_cost", "mugen_climb", "fushigi") and isinstance(v, dict) and isinstance(v.get("cost"), int) and v["cost"] > max_cost:
                continue
            return k
    return None


def fast_heavy_pairs(rules, by_card, ids, *, min_cost: int = 5, max_cost: int = 4) -> dict:
    """{"self": {H: 経路}, "pairs": [(H, E, 経路)]}。H は印刷コスト min_cost 以上で束を持つ札。
    self: H 自身の能力で max_cost 以下の負担で出せる。pairs: コスト max_cost 以下の札 E の効果（play_free、
    手札・墓地・山札・マナ・盾から場への move）のフィルタが H を通す（cost_le などで H を弾かない）。名前は見ない。"""
    from ..eval import speed_bound as S
    cards = rules.cards
    heavy = [i for i in ids if isinstance(cards[i].cost, int) and cards[i].cost >= min_cost and by_card.get(cards[i].id)]
    cheap = [i for i in ids if isinstance(cards[i].cost, int) and cards[i].cost <= max_cost]
    self_ = {h: r for h in heavy for r in [_self_fast(cards[h], max_cost)] if r}
    pairs = []
    for e in cheap:
        for op in S._ops(cards[e]):
            sel = op.get("select") or {}
            if not (sel.get("zone") in S.PUT_FROM and sel.get("owner", "you") in ("you", "self")):
                continue
            if not (op.get("op") == "play_free" or (op.get("op") == "move" and op.get("to") == "bz")):
                continue
            flt = sel.get("filter") or {}
            if not flt:
                continue        # 無条件で何でも出す札は組が爆発する。フィルタを持つ札だけ（狙って重い札を出す）
            route = f"{op.get('op')}:{sel.get('zone')}"
            for h in heavy:
                if h != e and S._admits(flt, cards[h]):
                    pairs.append((h, e, route))
    return {"self": self_, "pairs": sorted(set(pairs))}


def collect_fast_heavy(rules, by_card, *, max_cost: int = 4, max_turn: int = 6, per_heavy: int = 15, log=None) -> tuple[list[Base], Counter]:
    """(4) 早く出せる重い札を含む3枚の部品。重い札 H（印刷コスト max_cost+1 以上）が、自分の能力（G・ゼロ等）で早く出るか、
    組の中の安い札 E の効果で出される組だけを残す。種は安い種（cheap_seeds）と、早く出せる重い札・それを出す札。
    上限ターンは max_turn まで残す（5〜6ターンは捨てずに値つきで記録する方針）。読めない経路の組（turn None）も残す。"""
    from ..eval import speed_bound as S
    ids, _ = F.usable_ids(rules)
    fp = fast_heavy_pairs(rules, by_card, ids, min_cost=max_cost + 1, max_cost=max_cost)
    by_h: dict[str, set] = {}
    for h, e, _r in fp["pairs"]:
        by_h.setdefault(h, set()).add(e)
    heavy = sorted(set(fp["self"]) | set(cheap_seeds(rules, by_card, sorted(by_h), max_cost=99)))
    enab = sorted({e for es in by_h.values() for e in es})
    # 残り2枚は安い種と出す札から選ぶ（重い札は1組に1枚。重い札どうしを組ませると束の過大近似で数百万組になる、2026-11-16 実測）
    seeds = sorted(set(cheap_seeds(rules, by_card, ids, max_cost)) | set(enab))
    need = {h: by_h.get(h, set()) for h in heavy if h not in fp["self"]}
    sets = triangle_sets(rules, by_card, ids, seeds, log=log, anchors=heavy, need=need)
    if log:
        log(f"(4) 重い札の三角 {len(sets)}（重い種 {len(heavy)}・出す札 {len(enab)}・種 {len(seeds)}）")
    out, drop = [], Counter()
    for cs in sets:
        fast = [h for h in cs if h in fp["self"] or by_h.get(h, set()) & set(cs)]
        slow_heavy = [h for h in cs if isinstance(rules.cards[h].cost, int) and rules.cards[h].cost > max_cost and h not in fast]
        if not fast or slow_heavy:
            drop["heavy_not_fast"] += 1
            continue
        r, cyc = F.judge_set(cs, by_card, rules)     # 静的判定が安いので先に（1組 0.4ms）
        if r not in (None, "no_win") or not cyc:
            drop[r] += 1
            continue
        t = S.static_bound(rules, cs)["turn"]
        if t is not None and t > max_turn:
            drop["slow"] += 1
            continue
        c = cyc[0]
        lay, grave = layout_of(c, cs, rules)
        out.append(Base(cards=cs, names=[rules.cards[x].name for x in cs], gains=_gains(c), has_win=r is None,
                        unknown=getattr(c, "unknown", 0), turn=t, layout=lay, grave=grave))
    return cap_per_heavy(rules, out, max_cost, per_heavy, drop), drop


def cap_per_heavy(rules, bases: list, max_cost: int, per_heavy: int, drop: Counter | None = None) -> list:
    """同じ重い札の組は per_heavy 組まで（勝ち手段を含む組、上限ターンが早い組を先に）。一部の札が数千組を占めるのを防ぐ（2026-11-16: 6万組中上位5枚で7千組）。"""
    if not per_heavy:
        return bases
    key = lambda b: (not b.has_win, b.turn if b.turn is not None else 4.5, b.cards)   # noqa: E731  読めない経路（None）は4と5の間
    n, out = Counter(), []
    for b in sorted(bases, key=key):
        h = next((x for x in b.cards if isinstance(rules.cards[x].cost, int) and rules.cards[x].cost > max_cost), None)
        if n[h] >= per_heavy:
            if drop is not None:
                drop["per_heavy"] += 1
            continue
        n[h] += 1
        out.append(b)
    return out
