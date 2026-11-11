"""段階目標の有向グラフ（前提関係つきの段の集合）。固定順の鎖を一般化して、順序の前後・並列・選択肢を表す。
各段（Node）は id・target（reach_target 形式 {ゾーン: {ID or "*": 枚数}}）・requires（前提）を持つ。
- requires: 前提の段の id の列。段 A が済んでいないと B は狙えない。
  要素がリストなら「どれか1つが済んでいればよい」（選択肢）。例: requires: [a, [b, c]] = a と、b か c のどちらか。
- 前提が無い（requires: []）段どうしは並列で、順序は探索が決める。
- target は「その段で満たすべき局面」で、探索では「済んだ段の target」も足して（手札などを崩さないように）狙う。
ファイル形式（data/eval/stages/*.yaml）: 段に id / requires が1つも無ければ従来の鎖（各段が直前の段を前提、target は累積）。
1つでもあれば、requires を省いた段は「直前の段」ではなく前提なし。"""
from __future__ import annotations

from dataclasses import dataclass, field


def merge_targets(a: dict, b: dict) -> dict:
    """2つの目標をまとめる（同じ (ゾーン, 札) は大きい方の枚数）。"""
    out = {z: dict(v) for z, v in a.items()}
    for z, v in b.items():
        for i, n in v.items():
            out.setdefault(z, {})[i] = max(out.get(z, {}).get(i, 0), n)
    return out


@dataclass(frozen=True)
class Node:
    id: str
    target: dict
    requires: tuple = ()      # 要素は id か、選択肢のリスト（どれか1つ）
    name: str = ""


@dataclass
class StageGraph:
    nodes: list = field(default_factory=list)

    def __post_init__(self):
        ids = [n.id for n in self.nodes]
        if len(set(ids)) != len(ids):
            raise ValueError("段の id が重複している")
        known = set(ids)
        for n in self.nodes:
            for r in n.requires:
                for x in (r if isinstance(r, (list, tuple)) else (r,)):
                    if x not in known:
                        raise ValueError(f"段 {n.id} の前提 {x} が無い")
        self.nodes = self.topo()      # 前提が先に来る順（同じ段階の並びは元の順）

    def topo(self) -> list:
        by = {n.id: n for n in self.nodes}
        out, seen, onstack = [], set(), set()

        def visit(n):
            if n.id in seen:
                return
            if n.id in onstack:
                raise ValueError(f"前提が循環している: {n.id}")
            onstack.add(n.id)
            for r in n.requires:
                for x in (r if isinstance(r, (list, tuple)) else (r,)):
                    visit(by[x])
            onstack.discard(n.id)
            seen.add(n.id)
            out.append(n)
        for n in self.nodes:
            visit(n)
        return out

    @staticmethod
    def req_met(node: Node, sat: set) -> bool:
        return all((any(x in sat for x in r) if isinstance(r, (list, tuple)) else r in sat) for r in node.requires)

    def ready(self, done: set) -> list:
        """まだ済んでいなくて、前提が済んでいる段（今狙える段）。"""
        return [n for n in self.nodes if n.id not in done and self.req_met(n, done)]

    def is_chain(self) -> bool:
        """各段が直前の段だけを前提とする鎖か（従来の reach_chain で扱える）。"""
        return all(n.requires == ((self.nodes[k - 1].id,) if k else ()) for k, n in enumerate(self.nodes))

    def targets(self) -> list:
        return [n.target for n in self.nodes]

    def by_id(self) -> dict:
        return {n.id: n for n in self.nodes}

    @classmethod
    def from_chain(cls, targets: list) -> "StageGraph":
        """目標の列（従来の鎖）から。各段は直前の段を前提とする。"""
        return cls([Node(f"s{k}", t, (f"s{k - 1}",) if k else ()) for k, t in enumerate(targets)])

    @classmethod
    def from_stage_dicts(cls, stages: list) -> "StageGraph":
        """YAML の stages（{name, target, id?, requires?}）から。id も requires も無ければ従来の鎖。"""
        if not any("requires" in s or "id" in s for s in stages):
            return cls.from_chain([s["target"] for s in stages])
        nodes = []
        for k, s in enumerate(stages):
            req = tuple(tuple(r) if isinstance(r, list) else r for r in (s.get("requires") or ()))
            nodes.append(Node(str(s.get("id", f"s{k}")), s["target"], req, s.get("name", "")))
        return cls(nodes)

    def to_stage_dicts(self) -> list:
        return [{"id": n.id, "name": n.name or n.id, "requires": [list(r) if isinstance(r, tuple) and not isinstance(r, str) else r for r in n.requires],
                 "target": n.target} for n in self.nodes]


def search_target(graph: StageGraph, node: Node, done: set) -> dict:
    """段 node を狙う時の探索目標: 済んだ段の目標も足す（済んだ段の盤面を崩さない）。"""
    by = graph.by_id()
    tg = node.target
    for i in done:
        tg = merge_targets(tg, by[i].target)
    return tg
