"""PlanSpec v0: 計画の共通の枠（計画仕様 v0 §4.7）。承認待ちのスケルトン。

- plan_id は正規形（出典を除く）のハッシュ。同じ内容なら同じ ID。
- 未知の項目は extra に保持して往復で捨てない。スキーマ版は schema_version。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from dmsim.base.loopspec import Pred, Route
from .registry import KINDS, ROLES

SCHEMA_VERSION = 1   # v1 = 記録形式の確定版（notes/plan-record-format.md）。v0 は MIGRATIONS で読める。
VALID_OPS = (">=", "<=", "==", ">", "<")
# 版の対応表: 旧版 -> (dict -> dict)。版を上げるときは必ずここに足す。
MIGRATIONS: dict = {0: lambda d: {**d, "schema_version": 1}}


def _canon_pred(d: dict) -> dict:
    return {**d, "zones": sorted(d["zones"])}


def _canon_route(d: dict) -> dict:
    return {**d, "civs": sorted(d["civs"])}


def dumps(obj) -> str:
    """正規形の JSON（キー順固定・空白なし・NaN 不可）。plan_id と保存の両方で使う。"""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def pred_to_dict(p: Pred) -> dict:
    return {"owner": p.owner, "match": p.match, "n": p.n, "op": p.op, "zone": p.zone, "zones": list(p.zones)}


def pred_from_dict(d: dict) -> Pred:
    return Pred(**{**d, "zones": tuple(d.get("zones") or ())})


def route_to_dict(r: Route) -> dict:
    return {"name": r.name, "card": r.card, "from_zone": r.from_zone, "cost": r.cost, "civs": list(r.civs)}


def route_from_dict(d: dict) -> Route:
    return Route(**{**d, "civs": tuple(d.get("civs") or ())})


_KNOWN = {"schema_version", "kind", "roles", "minimal", "routes", "goal", "hazards", "params", "source", "extra"}


@dataclass
class PlanSpec:
    kind: str
    roles: tuple[str, ...] = ("win_path",)
    minimal: list[Pred] = field(default_factory=list)      # 最小盤面 M（相手側の条件も可）
    routes: list[Route] = field(default_factory=list)      # M への到達経路
    goal: list[Pred] = field(default_factory=list)         # 出口 G
    hazards: list[str] = field(default_factory=list)
    params: dict = field(default_factory=dict)             # 種類ごとの固有項目（loop なら delta/limit/deck_floor/loop_kind）
    source: dict = field(default_factory=dict)             # シード・エンジン版・カード定義のハッシュ（plan_id に含めない）
    extra: dict = field(default_factory=dict)              # 未知の項目の保持
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"unregistered kind {self.kind}")
        self.roles = tuple(self.roles)
        for p in (*self.minimal, *self.goal):
            if p.op not in VALID_OPS or p.n < 0:
                raise ValueError(f"invalid Pred {p}")
        for r in self.roles:
            if r not in ROLES:
                raise ValueError(f"unregistered role {r}")

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version, "kind": self.kind, "roles": list(self.roles),
            "minimal": [pred_to_dict(p) for p in self.minimal],
            "routes": [route_to_dict(r) for r in self.routes],
            "goal": [pred_to_dict(p) for p in self.goal],
            "hazards": list(self.hazards), "params": self.params, "source": self.source, "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PlanSpec":
        d = dict(d)
        ver = d.get("schema_version", 0)
        while ver != SCHEMA_VERSION:
            if ver not in MIGRATIONS:
                raise ValueError(f"schema_version {ver} は未対応（版が変わるときは対応表が必須）")
            d = MIGRATIONS[ver](d)
            ver = d["schema_version"]
        extra = {**d.get("extra", {}), **{k: v for k, v in d.items() if k not in _KNOWN}}
        return cls(
            kind=d["kind"], roles=tuple(d.get("roles") or ("win_path",)),
            minimal=[pred_from_dict(p) for p in d.get("minimal", [])],
            routes=[route_from_dict(r) for r in d.get("routes", [])],
            goal=[pred_from_dict(p) for p in d.get("goal", [])],
            hazards=list(d.get("hazards", [])), params=d.get("params", {}),
            source=d.get("source", {}), extra=extra, schema_version=ver,
        )

    def to_json(self) -> str:
        return dumps(self.to_dict())

    @classmethod
    def from_json(cls, s: str) -> "PlanSpec":
        return cls.from_dict(json.loads(s))

    @property
    def plan_id(self) -> str:
        """正規形: 出典を除き、集合として扱う項目（役割・弱点・Pred・Route・zones・civs）は並べ替える。"""
        d = self.to_dict()
        d.pop("source")
        d["roles"] = sorted(d["roles"])
        d["hazards"] = sorted(d["hazards"])
        for k, f in (("minimal", _canon_pred), ("goal", _canon_pred), ("routes", _canon_route)):
            d[k] = sorted((f(x) for x in d[k]), key=dumps)
        return hashlib.sha256(dumps(d).encode()).hexdigest()[:16]


def dump_jsonl(plans, path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for p in plans:
            f.write(p.to_json() + "\n")


def load_jsonl(path) -> list[PlanSpec]:
    with open(path, encoding="utf-8") as f:
        return [PlanSpec.from_json(line) for line in f if line.strip()]
