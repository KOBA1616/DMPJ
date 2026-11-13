"""中核を固定して基盤を選ぶ（S5 発見のデッキ構築、最小版。docs/basebuild-design.md）。

入力: 中核の札 {ID: 枚数} と入口局面の名前（揃う・入口の判定に使う）。出力: 40枚のデッキと選んだ経過。
1. 基盤の候補（candidates）: カードデータの実カード（試験札 T/R/L 番台を除く）を deckplan.pool.classify の役割
   （search・draw・prep=墓地肥やし・accel=マナ加速）で分け、中核の文明に収まる・コスト MAX_COST 以下・中核でない札を、
   役割ごとにコストの軽い順（同コストは ID 順）で PER_ROLE 種まで。カード名の手書きリストは使わない。
2. チャージ用の札（filler）: 役割も能力も持たないクリーチャーのうち、中核の文明でコストの最も軽いものを文明ごとに1種。
   中核で埋まらない枠を文明の順に4枚ずつで埋める。
3. 貪欲（build）: 今のデッキを測り、候補1種4枚をチャージ用の札4枚と入れ替えたデッキを全部測って、点が最も良く上がった1種を採る。
   上がらなくなるか枠が尽きたら止める。測定は eval.api.measure_assembly（通常開幕・FAIR、軽い設定 FAST）。
   点（score）= 入口到達の局数×3 + 揃った局数 + 揃ったターンの早さ（(上限+1−ターン)/(上限+1) の和）。勝敗と V は使わない。
承認状況: 選んだ札それぞれについて cards.approval の台帳を通るかを結果に記録する（2026-11-13 時点で承認済みの実カードは1枚だけなので、
候補を承認済みに絞らない。指揮役へ報告済み）。
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ..deckplan.pool import classify
from ..eval.api import measure_assembly

ROLES = ("search", "draw", "prep", "accel")
MAX_COST = 4
PER_ROLE = 3
COPIES = 4
DECK = 40
FAST = {"budget": 20, "n_det": 1, "max_turn": 6}
FAST_GAMES = 20


@dataclass
class Build:
    deck: list[str]
    added: list[dict] = field(default_factory=list)      # [{id, name, roles, score_before, score_after}]
    score: float = 0.0
    measured: dict = field(default_factory=dict)


def _test(i: str) -> bool:
    return i.startswith(("T", "R", "L"))


def _raw_cards(rules) -> dict:
    """ID -> カードデータの生の辞書（役割の分類に使う）。"""
    import yaml
    from ..cards.defs import card_yaml_files
    out = {}
    for f in card_yaml_files():
        for raw in (yaml.safe_load(open(f, encoding="utf-8")) or {}).get("cards") or []:
            if isinstance(raw, dict) and raw.get("id") in rules.cards:
                out.setdefault(raw["id"], raw)
    return out


def core_civs(rules, core: dict) -> set[str]:
    return {v for i in core for v in rules.cards[i].civs} - {"zero"}


def candidates(rules, core: dict, raw: dict | None = None) -> dict[str, list[str]]:
    raw = raw if raw is not None else _raw_cards(rules)
    civs = core_civs(rules, core)
    names = {rules.cards[i].name for i in core}
    out: dict[str, list[str]] = {r: [] for r in ROLES}
    seen: set[str] = set()
    for i in sorted(raw, key=lambda i: (rules.cards[i].cost or 0, i)):
        c = rules.cards[i]
        if _test(i) or i in core or c.name in names or c.name in seen or not c.cost or c.cost > MAX_COST:
            continue
        if not set(c.civs) - {"zero"} or not set(c.civs) <= civs or c.evolve_from:
            continue
        roles = classify(raw[i])
        for r in ROLES:
            if r in roles and len(out[r]) < PER_ROLE:
                out[r].append(i)
                seen.add(c.name)
                break
    return out


def fillers(rules, core: dict, raw: dict | None = None) -> list[str]:
    raw = raw if raw is not None else _raw_cards(rules)
    out = []
    for v in sorted(core_civs(rules, core)):
        best = None
        for i in sorted(raw):
            c = rules.cards[i]
            if _test(i) or not c.is_creature or c.abilities or c.keywords or c.evolve_from or list(c.civs) != [v] or not c.cost:
                continue
            if classify(raw[i]):
                continue
            if best is None or (c.cost, i) < (rules.cards[best].cost, best):
                best = i
        if best:
            out.append(best)
    return out


def base_deck(core: dict, fill: list[str]) -> list[str]:
    deck = [i for i, k in core.items() for _ in range(k)]
    j = 0
    while len(deck) < DECK:
        deck += [fill[j % len(fill)]] * min(COPIES, DECK - len(deck))
        j += 1
    return deck


def score(rows: list[dict], horizon: int) -> float:
    s = 0.0
    for r in rows:
        if r["entry_turn"] is not None:
            s += 3
        if r["cards_turn"] is not None:
            s += 1 + (horizon + 1 - r["cards_turn"]) / (horizon + 1)
    return s


def summary(rows: list[dict]) -> dict:
    n = len(rows)
    ct = [r["cards_turn"] for r in rows if r["cards_turn"] is not None]
    return {"games": n, "cards": f"{len(ct)}/{n}", "cards_turns": dict(sorted(Counter(ct).items())),
            "entry": f"{sum(r['entry_turn'] is not None for r in rows)}/{n}", "stage2": f"{sum(r['stage2'] for r in rows)}/{n}",
            "via": dict(Counter(str(r["via"]) for r in rows))}


def _swap(deck: list[str], fill: list[str], new: str) -> list[str] | None:
    """チャージ用の札を COPIES 枚 new に替える（多く残っている文明から）。足りなければ None。"""
    d = list(deck)
    left = Counter(x for x in d if x in fill)
    k = 0
    for f, _ in left.most_common():
        while k < COPIES and f in d:
            d[d.index(f)] = new
            k += 1
    return d if k == COPIES else None


def build(rules, core: dict, entry: str, *, seeds=None, settings: dict | None = None, max_steps: int = 6, log=None) -> Build:
    settings = dict(FAST, **(settings or {}))
    seeds = list(seeds or range(1, FAST_GAMES + 1))
    raw = _raw_cards(rules)
    fill = fillers(rules, core, raw)
    cands = candidates(rules, core, raw)
    pool = [i for r in ROLES for i in cands[r]]
    deck = base_deck(core, fill)
    hz = settings["max_turn"]

    def meas(d):
        return score(measure_assembly(rules, entry, d, seeds, **settings), hz)
    cur = meas(deck)
    b = Build(deck, score=cur, measured={"fillers": fill, "candidates": cands, "settings": settings, "seeds": seeds})
    for _ in range(max_steps):
        best = None
        for i in pool:
            if i in deck:
                continue
            d2 = _swap(deck, fill, i)
            if d2 is None:
                continue
            s = meas(d2)
            if log:
                log(f"  候補 {i} {rules.cards[i].name}: {s:.2f}（今 {cur:.2f}）")
            if s > cur and (best is None or s > best[0]):
                best = (s, i, d2)
        if best is None:
            break
        s, i, d2 = best
        b.added.append({"id": i, "name": rules.cards[i].name, "roles": sorted(classify(raw[i])), "score_before": round(cur, 2), "score_after": round(s, 2)})
        if log:
            log(f"採用 {i} {rules.cards[i].name} {cur:.2f} → {s:.2f}")
        deck, cur = d2, s
    b.deck, b.score = deck, cur
    return b


def approval_status(ids) -> dict:
    from ..cards import approval
    from ..cards.defs import load_tables
    ledger, versions = approval.load(), approval.vocab_versions(load_tables())
    raw = {}
    import yaml
    from ..cards.defs import card_yaml_files
    for f in card_yaml_files():
        for c in (yaml.safe_load(open(f, encoding="utf-8")) or {}).get("cards") or []:
            if isinstance(c, dict) and c.get("id") in ids:
                raw.setdefault(c["id"], c)
    return {i: approval.is_usable(raw[i], ledger, versions) if i in raw else None for i in sorted(set(ids))}
