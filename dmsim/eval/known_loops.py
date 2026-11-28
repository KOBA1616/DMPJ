"""既知ループの再発見率: 登録簿の入口盤面（data/loops/entry/*.json）から、手の登録なしで
合成手の find_loop（dmsim/search/compose.py）がループを見つけるかを測る。

起点は「その盤面で最初に選べる攻撃」を自動で取る（札名は書かない）。攻撃を一度も選べない盤面
（呪文だけで回るアカシック・サガ型）は、合成手が攻撃起点のため no_origin（見つからない側に数える）。
見つかった = kind が finite または infinite。"""
from __future__ import annotations
from dmsim.eval import loop_entry as LE

KNOWN = ("akashic", "akashic_hd2", "saga", "jashin_abyss")   # data/loops/entry の現行の入口（*_v1 は旧定義で除く）


def _to_attack(eng, steps: int = 60):
    """pass を選びながら最初の attack 選択まで進める。無ければ None。"""
    for _ in range(steps):
        d = eng.advance()
        if d is None or eng.s.result:
            return None
        if d["kind"] == "attack" and d["player"] == 0:
            ks = [o["key"] for o in d["options"] if o["key"].startswith("attack:")]
            return ks[0] if ks else None
        ks = [o["key"] for o in d["options"]]
        eng.answer([ks.index("pass") if "pass" in ks else 0])
    return None


def measure_one(rules, name: str, seed: int = 1, **kw) -> dict:
    from dmsim.search import compose as C
    try:
        eng = LE.build(rules, LE.load(name), seed)
    except Exception as x:   # 入口が組めない（例: 盤面を持たない型）
        return {"name": name, "found": False, "why": "build_error", "error": repr(x)[:120]}
    origin = _to_attack(eng)
    if origin is None:
        return {"name": name, "found": False, "why": "no_origin"}
    r = C.find_loop(eng, origin, **kw)
    return {"name": name, "found": r["kind"] in ("finite", "infinite"), "why": r["kind"], "origin": origin,
            "laps": r["laps"], "deltas": r["deltas"]}


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
