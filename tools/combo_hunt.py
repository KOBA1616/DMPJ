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
from dmsim.defs import load_rules  # noqa: E402
from dmsim.solitaire import measure  # noqa: E402
from dmsim.zone_graph import Cycle, bundles_of, feeds  # noqa: E402

REGISTERED = ("tenmon", "saga", "knight_dmc", "akashic")


def registered_cards(root: Path = Path("data/decks")) -> set[str]:
    out: set[str] = set()
    for n in REGISTERED:
        p = root / f"{n}.yaml"
        if p.exists():
            y = yaml.safe_load(p.read_text(encoding="utf-8"))
            out |= set(y.get("deck") or (y.get("cards") or {}).keys())
    return out


def score(c) -> float:
    opp = c.opp_delta()
    s = 3.0 * sum(1 for k, v in opp.items() if v < 0 and k in ("deck", "shield", "mana", "hand"))
    s += 2.0 if c.period == "in_turn" else 0.0
    s += 1.0 if c.sure else 0.0
    s -= 0.5 * c.mana()
    s -= 1.0 if c.conditional() else 0.0
    return s


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


def fast_cycles(rules) -> list:
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


def candidates(rules, max_cards: int = 2, max_len: int = 2) -> list[dict]:
    known = registered_cards()
    seen, out = set(), []
    for c in fast_cycles(rules):
        cards = tuple(c.cards)
        if cards in seen or set(cards) <= known or any(x.startswith(("T", "R", "L")) for x in cards):
            continue
        seen.add(cards)
        out.append({"cards": list(cards), "names": [rules.cards[x].name for x in cards], "score": score(c), "period": c.period,
                    "sure": c.sure, "delta": c.delta(), "opp_delta": c.opp_delta(), "mana": c.mana()})
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
    todo, used = [], {}      # 同じ札ばかりの候補に偏らないよう、1枚につき最大2組まで
    for c in cands:
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
