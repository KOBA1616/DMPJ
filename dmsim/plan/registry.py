"""計画の「種類」と「役割」の登録式（engine/registry.py と同じ流儀）。計画仕様 v0（§4.7）。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KindDef:
    name: str
    doc: str = ""


@dataclass(frozen=True)
class RoleDef:
    """新しい役割には、進み具合の測り方・比べ方・テストの名前を必須とする（実体は後の段階で結ぶ）。"""
    name: str
    progress: str
    compare: str
    test: str


KINDS: dict[str, KindDef] = {}
ROLES: dict[str, RoleDef] = {}


def register_kind(name: str, doc: str = "") -> KindDef:
    if name in KINDS:
        raise ValueError(f"kind already registered: {name}")
    KINDS[name] = KindDef(name, doc)
    return KINDS[name]


def register_role(name: str, *, progress: str, compare: str, test: str) -> RoleDef:
    if not (progress and compare and test):
        raise ValueError("役割には progress / compare / test が必須")
    if name in ROLES:
        raise ValueError(f"role already registered: {name}")
    ROLES[name] = RoleDef(name, progress, compare, test)
    return ROLES[name]


# 初期の種類（実装は LoopSpec の取り込みのみ。他は枠だけ）
register_kind("loop", "周期的に戻るループ（LoopSpec を吸収）。ロックは周期が相手のターンをまたぐループ")
register_kind("combo_sequence", "コンボ手順（枠のみ）")
register_kind("lock", "ターンをまたぐロック（枠のみ）")
register_kind("beat", "ビートダウン（枠のみ）")

# 初期の役割（測り方などは名前だけの仮置き。登録時に必須項目を強制する）
for _n in ("win_path", "disruption", "defense", "resource", "stall"):
    register_role(_n, progress=f"{_n}.progress", compare=f"{_n}.compare", test=f"{_n}.test")
