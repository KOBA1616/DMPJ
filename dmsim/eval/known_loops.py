"""既知ループの再発見率: 登録簿の入口盤面（data/loops/entry/*.json）から、手の登録なしで
合成手の find_loop（dmsim/search/compose.py）がループを見つけるかを測る。

起点は自動で取る（札名は書かない）: 最初に選べる攻撃、無ければメインの play: 行動を順に試す。
見つかった = kind が finite または infinite。"""
from __future__ import annotations
from dmsim.eval import loop_entry as LE

KNOWN = ("akashic", "akashic_hd2", "saga", "jashin_abyss")   # data/loops/entry の現行の入口（*_v1 は旧定義で除く）


def _origins(eng, steps: int = 60) -> list[tuple]:
    """pass を選びながら進め、最初の main 選択（play: の行動）と最初の attack 選択（攻撃）の起点候補を
    (その時点のエンジン, key) で返す。攻撃を先に試す。"""
    mains, atk = [], []
    for _ in range(steps):
        d = eng.advance()
        if d is None or eng.s.result:
            break
        ks = [o["key"] for o in d["options"]]
        if d["player"] == 0 and d["kind"] == "main" and not mains:
            mains = [(eng.clone(), k) for k in ks if k.startswith("play:")]
        if d["player"] == 0 and d["kind"] == "attack":
            atk = [(eng.clone(), k) for k in ks if k.startswith("attack:")][:1]
            break
        eng.answer([ks.index("pass") if "pass" in ks else 0])
    return atk + mains


def measure_one(rules, name: str, seed: int = 1, max_origins: int = 8, **kw) -> dict:
    from dmsim.search import compose as C
    try:
        eng = LE.build(rules, LE.load(name), seed)
    except Exception as x:   # 入口が組めない（例: 盤面を持たない型）
        return {"name": name, "found": False, "why": "build_error", "error": repr(x)[:120]}
    origins = _origins(eng)[:max_origins]
    if not origins:
        return {"name": name, "found": False, "why": "no_origin"}
    best = None
    for e0, o in origins:
        r = C.find_loop(e0, o, **kw)
        row = {"name": name, "found": r["kind"] in ("finite", "infinite"), "why": r["kind"], "origin": o,
               "laps": r["laps"], "deltas": r["deltas"], "tried": len(origins)}
        if best is None or (row["found"], row["laps"]) > (best["found"], best["laps"]):
            best = row
        if row["found"]:
            break
    return best


def measure(rules=None, names=KNOWN, seed: int = 1, **kw) -> dict:
    if rules is None:
        from dmsim.cards.defs import load_rules
        rules = load_rules(only_approved=False)
    rows = [measure_one(rules, n, seed, **kw) for n in names]
    hit = sum(r["found"] for r in rows)
    return {"found": hit, "total": len(rows), "rate": hit / len(rows) if rows else 0.0, "rows": rows}


if __name__ == "__main__":
    import json
    m = measure(max_nodes=1500, laps_max=3, tries=3)
    print(f"再発見 {m['found']}/{m['total']} ({m['rate']:.0%})")
    for r in m["rows"]:
        print(json.dumps(r, ensure_ascii=False))
