"""組の候補の自動選択。効果データから各カードの入出力（どのゾーンへ動かすか／どのゾーンの動きで誘発するか）を取り、つなげる。

- writes: 効果が起こす移動の行き先（to）と移動元（from）。draw は手札へ、discard・destroy は墓地へ、bounce は手札へ、mana_put はマナへ。
- consumes: 誘発の条件が見ているゾーンの動き（when.event: move の to / from）と、ゾーンに居ることで働く能力（zone: graveyard 等）。
- 候補 (A, B) は「A の writes が B の consumes に当たる」組。粗い拾い上げで、偽陽性は多い。確かめるのは実エンジン（advantage.combo_report）。
"""
from __future__ import annotations

OP_TO = {"draw": "hand", "discard": "graveyard", "destroy": "graveyard", "bounce": "hand", "mana_put": "mana", "mill": "graveyard"}


def _walk_ops(ops):
    for op in ops or []:
        if not isinstance(op, dict):
            continue
        yield op
        for key in ("body", "then", "else", "win", "lose", "draw", "effect"):
            if isinstance(op.get(key), list):
                yield from _walk_ops(op[key])
        for m in op.get("modes") or []:
            yield from _walk_ops(m)


def _faces(cd):
    return list(getattr(cd, "faces", None) or []) or [cd]


def card_io(rules, cid: str) -> dict:
    cd = rules.cards[cid]
    wt, wf, ct, cf, zones = set(), set(), set(), set(), set()
    for f in _faces(cd):
        for ab in getattr(f, "abilities", None) or []:
            z = ab.get("zone", "bz")
            if z != "bz":
                zones.add(z)
            when = ab.get("when") or {}
            if ab.get("kind") == "trigger" and when.get("event") == "move" and when.get("subject") != "self":   # 自分自身の移動で誘発するもの（出た時など）は他のカードの出力では動かない
                if when.get("to"):
                    ct.add(when["to"])
                if when.get("from"):
                    cf.add(when["from"])
            for op in _walk_ops(ab.get("effect")):
                name = op.get("op")
                if name == "move":
                    wt.add(op["to"])
                    sel = op.get("select") or {}
                    if isinstance(sel, dict) and isinstance(sel.get("zone"), str):
                        wf.add(sel["zone"])
                elif name in OP_TO:
                    wt.add(OP_TO[name])
        for sp in (getattr(f, "spell", None) or []):
            if isinstance(sp, dict) and sp.get("op") == "move":
                wt.add(sp["to"])
    return {"writes_to": wt, "writes_from": wf, "consumes_to": ct, "consumes_from": cf, "reads_zones": zones}


def links(io_a: dict, io_b: dict) -> list[str]:
    """A の出力が B の入力に当たる点。"""
    out = [f"to:{z}" for z in io_a["writes_to"] & io_b["consumes_to"]]
    out += [f"from:{z}" for z in io_a["writes_to"] & io_b["consumes_from"]]
    out += [f"read:{z}" for z in io_a["writes_to"] & io_b["reads_zones"]]
    return sorted(out)


def candidate_pairs(rules, cards: list[str], top: int | None = None, ignore=("read:hand",)) -> list[dict]:
    """cards の順序つきの組から、つながりのあるものを、つながりの珍しさ（IDF）の合計が大きい順に返す。
    どのカードにもあるつながり（手札で働く能力など）は点が低い。ignore のつながりは数えない。"""
    import math
    io = {c: card_io(rules, c) for c in cards}
    prod: dict[str, list[str]] = {}
    cons: dict[str, list[str]] = {}
    for c, x in io.items():
        for z in x["writes_to"]:
            prod.setdefault(z, []).append(c)
        for z in x["consumes_to"]:
            cons.setdefault(f"to:{z}", []).append(c)
        for z in x["consumes_from"]:
            cons.setdefault(f"from:{z}", []).append(c)
        for z in x["reads_zones"]:
            cons.setdefault(f"read:{z}", []).append(c)
    n = max(1, len(cards))
    score: dict[tuple, list] = {}
    for key, bs in cons.items():
        if key in ignore:
            continue
        z = key.split(":", 1)[1]
        w = math.log(n / (1 + len(bs))) + math.log(n / (1 + len(prod.get(z, []))))   # 消費側と生産側、両方が珍しいほど高い
        for a in prod.get(z, []):
            for b in bs:
                if a != b:
                    e = score.setdefault((a, b), [0.0, []])
                    e[0] += max(w, 0.0)
                    e[1].append(key)
    out = [{"a": a, "b": b, "links": sorted(v[1]), "score": round(v[0], 2)} for (a, b), v in score.items()]
    out.sort(key=lambda x: (-x["score"], x["a"], x["b"]))
    return out[:top] if top else out


def discover_combos(rules, cards: list[str], base: dict | None = None, opp: dict | None = None, top: int = 10, **kw) -> list[dict]:
    """候補の自動選択 → 実エンジンでの確認。つながりの多い上位 top 件を scan_pair_report で測り、成立する置き場所があるものを返す。"""
    from .advantage import scan_pair_report
    out = []
    for c in candidate_pairs(rules, cards)[:top]:
        rep = scan_pair_report(rules, c["a"], c["b"], base=base, opp=opp, **kw)
        if rep["works"]:
            out.append({"a": c["a"], "b": c["b"], "links": c["links"], "works": rep["works"], "converts": rep["converts"]})
    return out
