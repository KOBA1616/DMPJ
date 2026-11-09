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
from dmsim.zone_graph import find_cycles  # noqa: E402

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


def candidates(rules, max_cards: int, max_len: int) -> list[dict]:
    known = registered_cards()
    seen, out = set(), []
    for c in find_cycles(rules, max_cards, max_len):
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
    ap.add_argument("--out", default="logs/combohunt.jsonl")
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
    todo = [c for c in cands if tuple(c["cards"]) not in done][:a.top]
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
