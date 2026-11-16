"""登録済みデッキ以外から、ゾーン移動が噛み合う組を自動で拾い、1人回しで本当に勝てるか確かめる（目的①の入口）。

  PYTHONPATH=. python tools/combo_hunt.py --top 20 --seeds 6 --turns 4 [--max-cards 2] [--out logs/combohunt.jsonl]
流れ: zone_graph の循環（確実に受け渡せるもの）を列挙 → 登録デッキの札だけで成る組は除く → 点数順 → 組の札4枚ずつ＋同文明の軽い札で40枚 → solitaire.measure。
点数は「相手のゾーンを削る（山札・シールド・マナ）／ターン内で回る／払うマナが少ない」を高く見る。結果は --out に追記（既に測った組は飛ばす）。
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.scenario import build  # noqa: E402
from dmsim.play_api import InfoLevel, PlayConfig, play  # noqa: E402
from dmsim.eval.measure import measure  # noqa: E402
from dmsim.engine.zone_graph import Cycle, bundles_of, feeds  # noqa: E402

REGISTERED = ("tenmon", "saga", "knight_dmc", "akashic")


def registered_cards(root: Path = Path("data/decks")) -> set[str]:
    out: set[str] = set()
    for n in REGISTERED:
        p = root / f"{n}.yaml"
        if p.exists():
            y = yaml.safe_load(p.read_text(encoding="utf-8"))
            out |= set(y.get("deck") or (y.get("cards") or {}).keys())
    return out


def score(c, freq: dict | None = None) -> float:
    """勝ち筋に直結する効果（山札・シールドを削る／マナを削るロック）を高く、汎用札（多くの候補に出る札）と自分の山札切れを低く見る。"""
    import math
    opp = c.opp_delta()
    s = 4.0 * (opp.get("deck", 0) < 0) + 3.0 * (opp.get("shield", 0) < 0) + 2.0 * (opp.get("mana", 0) < 0)
    s += 1.0 * (opp.get("graveyard", 0) > 0)
    s += 2.0 if c.period == "in_turn" else 0.0
    s += 1.0 if c.sure else 0.0
    s -= 0.5 * c.mana()
    s -= 1.0 if c.conditional() else 0.0
    s -= 1.0 if c.delta().get("deck", 0) < 0 else 0.0      # 自分の山札を削る（山札切れの恐れ）
    if freq:
        s -= sum(0.8 * math.log10(max(1, freq.get(x, 1))) for x in c.cards)
    return s


OPP_DECK = 30     # 通常の開幕（40枚 − 手札5 − シールド5）に合わせる
MANA5 = ["T001", "T003", "T004", "T005", "T008"]


def verify_lock(rules, cards: list[str], seeds, turns: int = 3, budget: int = 100) -> dict:
    """ロック候補の成立確認。手札に2枚＋十分なマナ（5文明）、相手は山札30枚・マナ6枚の局面から実エンジンで回し、
    ロックの確立または山札切れ勝ちが出るかを見る。自分の山札切れ負けが出たら lost に数える（自分の山札切れ対策）。"""
    spec = {"p0": {"hand": list(cards), "mana": MANA5 * 2}, "p1": {"mana": ["T001"] * 6}, "deck_size": OPP_DECK, "shuffle_deck": True}
    ok = lost = err = 0
    kinds: set = set()
    for s in seeds:
        try:
            start = build(rules, {**spec, "seed": s})
            res = play(start, PlayConfig(seed=s, max_turn=turns, budget=budget), InfoLevel.CHEAT, rules=rules).game   # ロック判定つきの1人回し（真の山札順）
        except Exception as ex:      # 1局の失敗で止めない
            err += 1
            kinds.add(f"error:{type(ex).__name__}")
            continue
        if res.kill_turn is not None and (res.kind in ("lock", "deck_out", "loop_deck_out") or res.origin == "lock"):
            ok += 1
            kinds.add(f"{res.origin}/{res.kind}")
        if res.lost:
            lost += 1
    n = len(list(seeds)) if not isinstance(seeds, range) else len(seeds)
    return {"games": n, "lock_wins": ok, "self_lost": lost, "errors": err, "kinds": sorted(kinds)}


def build_deck(rules, cards: list[str], rng: random.Random, size: int = 40) -> list[str]:
    civs = set()
    for cid in cards:
        civs |= set(getattr(rules.cards[cid], "civs", []) or [])
    pool = sorted(i for i, cd in rules.cards.items() if not i.startswith(("T", "R", "L"))
                  and (getattr(cd, "cost", 9) or 9) <= 3 and set(getattr(cd, "civs", []) or []) & civs
                  and "creature" in (getattr(cd, "types", []) or []) and i not in cards)
    deck = [c for c in cards for _ in range(4)]
    guard = 0
    while len(deck) < size and pool and guard < 10000:
        guard += 1
        c = rng.choice(pool)
        if deck.count(c) < 4:
            deck.append(c)
    return deck


def fast_cycles(rules, max_cycle3: int = 300000) -> list:
    """長さ1〜2の循環（自己ループと2枚の相互受け渡し）だけを、前提で絞ってから調べる。全組を総当たりしないのでメモリも時間も小さい。"""
    bs = bundles_of(rules)
    by_to: dict = {}      # 前提の種類・行き先ごとの受け手
    for j, b in enumerate(bs):
        p = b.prem
        if p is not None:
            by_to.setdefault((p.kind, p.to if p.kind == "move" else None), []).append(j)
    succ: dict = {}
    for i, a in enumerate(bs):
        keys = {("move", m.dst) for m in a.moves} | {("draw", None), ("cast", None)}
        cand = {j for k, js in by_to.items() if k in keys or k[0] not in ("move", "draw", "cast") for j in js}
        succ[i] = {j: v for j in cand if (v := feeds(a, bs[j], rules))}
    out, seen = [], set()
    # 3枚の循環 i→j→k→i（i が最小）。数が膨らむので上限を置く
    small = {i for i, s in succ.items() if 0 < len(s) <= 150}     # 受け手が多すぎる汎用札は3枚循環の起点にしない（爆発を防ぐ）
    for i in sorted(small):
        for j in succ[i]:
            if j <= i or j not in small:
                continue
            for k in succ[j]:
                if k > i and i in succ[k] and len({bs[i].card, bs[j].card, bs[k].card}) == 3 and len(out) < max_cycle3:
                    out.append(Cycle([bs[i], bs[j], bs[k]], succ[i][j] == 2 and succ[j][k] == 2 and succ[k][i] == 2))
    for i in range(len(bs)):
        for j, v in succ[i].items():
            if j < i or (j != i and i not in succ.get(j, {})):
                continue
            key = (i, j)
            if key in seen:
                continue
            seen.add(key)
            path = [bs[i]] if i == j else [bs[i], bs[j]]
            out.append(Cycle(path, v == 2 and (i == j or succ[j][i] == 2)))
    return out


def lock_pairs(rules, per: int = 400) -> list[dict]:
    """ターンをまたぐロックの組: 相手のマナを動かす札 A と、相手の山札を減らす／引かせる札 B。自分の山札を削る札は減点（自分の山札切れ対策）。"""
    bs = bundles_of(rules)
    known = registered_cards()
    mana_a = {b.card: b for b in bs if any(m.owner == "opp" and m.src == "mana" for m in b.moves)}
    deck_b = {b.card: b for b in bs if any(m.owner == "opp" and (m.src == "deck" or m.draw) for m in b.moves)}
    out = []
    for ca, a in mana_a.items():
        for cb, b in deck_b.items():
            if ca == cb or {ca, cb} <= known or ca.startswith(("T", "R", "L")) or cb.startswith(("T", "R", "L")):
                continue
            selfdeck = sum(1 for x in (a, b) for m in x.moves if m.owner != "opp" and m.src == "deck")
            s = 8.0 - 1.5 * selfdeck - 0.3 * (a.cost + b.cost)
            out.append({"cards": sorted([ca, cb]), "names": [rules.cards[x].name for x in sorted([ca, cb])], "score": round(s, 2),
                        "period": "lock", "sure": False, "delta": {}, "opp_delta": {"mana": -1, "deck": -1}, "mana": a.cost + b.cost})
    out.sort(key=lambda d: -d["score"])
    return out[:per]


def candidates(rules, max_cards: int = 2, max_len: int = 2) -> list[dict]:
    known = registered_cards()
    seen, out = set(), []
    cyc = fast_cycles(rules)
    freq: dict = {}
    for c in cyc:
        for x in c.cards:
            freq[x] = freq.get(x, 0) + 1
    for c in cyc:
        cards = tuple(c.cards)
        if cards in seen or set(cards) <= known or any(x.startswith(("T", "R", "L")) for x in cards):
            continue
        seen.add(cards)
        out.append({"cards": list(cards), "names": [rules.cards[x].name for x in cards], "score": round(score(c, freq), 2), "period": c.period,
                    "sure": c.sure, "delta": c.delta(), "opp_delta": c.opp_delta(), "mana": c.mana()})
    out.extend(lock_pairs(rules))
    out.sort(key=lambda d: -d["score"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--budget", type=int, default=100)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--max-cards", type=int, default=2)
    ap.add_argument("--max-len", type=int, default=4)
    ap.add_argument("--locks", type=int, default=0, help="ロック候補の成立確認だけを、上位この件数ぶん回す（軽いので多く回せる）")
    ap.add_argument("--list-only", action="store_true", help="候補の一覧だけ出す（測らない）")
    ap.add_argument("--cache", default=".cache/combohunt_cycles.json")
    ap.add_argument("--out", default="data/combohunt/results.jsonl")
    a = ap.parse_args(argv)
    rules = load_rules()
    cache = Path(a.cache)
    key = [a.max_cards, a.max_len, max((p.stat().st_mtime for p in Path("data/cards").glob("*.yaml")), default=0)]
    cands = None
    if cache.exists():   # 循環の列挙は数分かかるので、カードデータが変わるまで使い回す
        j = json.loads(cache.read_text(encoding="utf-8"))
        if j.get("key") == key:
            cands = j["cands"]
    if cands is None:
        cands = candidates(rules, a.max_cards, a.max_len)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"key": key, "cands": cands}, ensure_ascii=False), encoding="utf-8")
    print(f"{len(cands)} 候補（登録デッキ外）", flush=True)
    out = Path(a.out)
    done = set()
    if out.exists():
        done = {tuple(json.loads(l)["cards"]) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()}
    if a.locks:
        out.parent.mkdir(parents=True, exist_ok=True)
        hits = []
        for c in [x for x in cands if x["period"] == "lock" and tuple(x["cards"]) not in done][:a.locks]:
            v = verify_lock(rules, c["cards"], range(1, a.seeds + 1), turns=3, budget=a.budget)
            rec = {**c, **v, "turns": 3, "verified": "lock_setup"}
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if v["lock_wins"]:
                hits.append(rec)
                print(f"lock {v['lock_wins']}/{v['games']} lost={v['self_lost']} {' + '.join(c['names'])} {v['kinds']}", flush=True)
        print(f"ロック成立 {len(hits)} 組", flush=True)
        return
    todo, used = [], {}      # 同じ札ばかりの候補に偏らないよう、1枚につき最大2組まで
    locks = [c for c in cands if c["period"] == "lock"]
    others = [c for c in cands if c["period"] != "lock"]
    mixed = [x for pair in zip(locks, others) for x in pair] + locks[len(others):] + others[len(locks):]   # ロックと循環を交互に（片方に偏らない）
    for c in mixed:
        if tuple(c["cards"]) in done or any(used.get(x, 0) >= 2 for x in c["cards"]):
            continue
        for x in c["cards"]:
            used[x] = used.get(x, 0) + 1
        todo.append(c)
        if len(todo) >= a.top:
            break
    if a.list_only:
        for c in todo:
            print(f"{c['score']:5.1f} {' + '.join(c['names'])} [{c['period']}] 相手={c['opp_delta']} マナ={c['mana']}")
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    for c in todo:
        t0 = time.time()
        if c["period"] == "lock":
            v = verify_lock(rules, c["cards"], range(1, a.seeds + 1), turns=3, budget=a.budget)
            rec = {**c, **v, "turns": 3, "seconds": round(time.time() - t0, 1), "verified": "lock_setup"}
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"lock {v['lock_wins']}/{v['games']} lost={v['self_lost']} err={v['errors']} {' + '.join(c['names'])} ({rec['seconds']}s) {v['kinds']}", flush=True)
            continue
        deck = build_deck(rules, c["cards"], random.Random(1))
        rs = measure(deck, ["T001"] * 40, range(1, a.seeds + 1), rules=rules, workers=a.workers, max_turn=a.turns, budget=a.budget)
        kills = [r for r in rs if r.kill_turn is not None]
        rec = {**c, "deck": deck, "games": len(rs), "kills": len(kills), "kill_rate": round(len(kills) / max(1, len(rs)), 3),
               "kinds": sorted({f"{r.origin}/{r.kind}" for r in kills}), "errors": [r.error for r in rs if r.error][:2],
               "turns": a.turns, "seconds": round(time.time() - t0, 1)}
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"{rec['kill_rate']:.2f} {' + '.join(c['names'])} ({rec['seconds']}s) {rec['kinds']}", flush=True)


if __name__ == "__main__":
    main()
