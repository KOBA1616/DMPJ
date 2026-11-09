"""評価部品の自動な追加・削除（LLM なし）。勝った局と負けた局の最終局面の差から、足す/外す候補を作る。

- 足す候補: 勝った局に偏って「ある」(ゾーン, 定義ID)で、部品表にまだ無いもの。
- 外す候補: 部品表にあるが、勝った局に偏っていない（勝ちと結びつかない）ID指定の部品。
勝った局が少ない時は、盤面に届いた局（board<=turn）を勝ちの代わりに使う。候補は統計の仮説にすぎないので、
採否は tune.evolve（調整用シード→別シードの再確認）に任せる。遺伝子は候補の添字の集合（frozenset）。"""
from __future__ import annotations

import random
from dataclasses import replace
from statistics import mean

from ..search.leaf_parts import Part, PartsSpec


def _group(m: dict, turn: int, min_pos: int = 3):
    kill = m["kill"]
    pos = [i for i, k in enumerate(kill) if k is not None and k <= turn]
    if len(pos) < min_pos and m.get("board"):
        pos = [i for i, b in enumerate(m["board"]) if b is not None and b <= turn]
    if len(pos) < min_pos and m.get("opp_shield") and all(x is not None for x in m["opp_shield"]):
        # 勝ちも盤面到達も無い時の代用: 相手の盾を多く割った上位1/3 と 少ない下位1/3（差が無ければ空）
        order = sorted(range(len(kill)), key=lambda i: m["opp_shield"][i])
        t = max(min_pos, len(order) // 3)
        top, bot = order[:t], order[-t:]
        if m["opp_shield"][top[-1]] < m["opp_shield"][bot[0]]:
            return top, bot
    neg = [i for i in range(len(kill)) if i not in set(pos)]
    return pos, neg


def _rate(finals, idx, z, d):
    return sum(1 for i in idx if (finals[i].get(z) or {}).get(d, 0) > 0) / len(idx) if idx else 0.0


def part_key(p: Part) -> str:
    return f"{p.zone}:{'|'.join(p.ids)}"


def discover(m: dict, spec: PartsSpec, turn: int = 4, min_group: int = 3, min_diff: float = 0.25, top: int = 4) -> list[dict]:
    """候補の列 [{op: add|drop, key, zone, id, diff, ...}]。m は harness_measure の戻り値（"final" 必須）。"""
    finals = m.get("final")
    if not finals:
        return []
    pos, neg = _group(m, turn, min_group)
    if len(pos) < min_group or len(neg) < min_group:
        return []
    covered = {(p.zone, i) for p in spec.parts for i in p.ids}
    feats = {(z, d) for f in finals for z, dd in f.items() for d in dd}
    adds, drops = [], []
    for z, d in feats:
        diff = _rate(finals, pos, z, d) - _rate(finals, neg, z, d)
        if (z, d) not in covered:
            if diff >= min_diff:
                adds.append({"op": "add", "zone": z, "id": d, "diff": diff})
    for p in spec.parts:
        if not p.ids:
            continue
        diffs = [_rate(finals, pos, p.zone, i) - _rate(finals, neg, p.zone, i) for i in p.ids]
        seen = any(_rate(finals, pos + neg, p.zone, i) > 0 for i in p.ids)
        if seen and mean(diffs) <= 0:
            drops.append({"op": "drop", "key": part_key(p), "zone": p.zone, "id": "|".join(p.ids), "diff": mean(diffs)})
    adds.sort(key=lambda c: -c["diff"])
    drops.sort(key=lambda c: c["diff"])
    return adds[:top] + drops[:top]


def apply_edits(spec: PartsSpec, cands: list[dict], genes) -> PartsSpec:
    """genes（候補の添字の集合）に当たる候補を部品表へ反映。add の重みは既存部品の平均。"""
    if not genes:
        return spec
    w = mean(p.weight for p in spec.parts) if spec.parts else 1.0
    drop = {cands[i]["key"] for i in genes if cands[i]["op"] == "drop"}
    parts = tuple(p for p in spec.parts if part_key(p) not in drop)
    adds = tuple(Part(zone=cands[i]["zone"], ids=(cands[i]["id"],), need=1, weight=w) for i in sorted(genes) if cands[i]["op"] == "add")
    return replace(spec, parts=parts + adds)


def mutate_genes(genes: frozenset, rng: random.Random, n: int) -> frozenset:
    """候補を1つ入れ替える（入っていれば外し、無ければ足す）。"""
    if n == 0:
        return genes
    return genes ^ frozenset([rng.randrange(n)])


def to_store(cands: list[dict], genes) -> dict:
    return {"add": [[cands[i]["zone"], cands[i]["id"]] for i in sorted(genes) if cands[i]["op"] == "add"],
            "drop": [cands[i]["key"] for i in sorted(genes) if cands[i]["op"] == "drop"]}


def apply_store(spec: PartsSpec, edit: dict | None) -> PartsSpec:
    """保存した追加・削除（to_store の形）を部品表へ。"""
    if not edit:
        return spec
    cands = [{"op": "add", "zone": z, "id": d} for z, d in edit.get("add", [])] + [{"op": "drop", "key": k} for k in edit.get("drop", [])]
    return apply_edits(spec, cands, frozenset(range(len(cands))))
