"""デッキ案の記録形式（計画仕様 §4.7 の拡張規則に合わせる: 未知項目は保持、スキーマ版つき、単一ラベル分類にしない）。

カード名は人が書いた表記のまま保持し、ID への解決は resolver（差し替え式）が行う。
エンジンとカードデータは読み取りのみで、ここからは書かない。"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

SCHEMA_VERSION = 1
KNOWN = {"schema_version", "name", "entries", "tags", "source", "notes", "status"}
CONFIRMED, UNCONVERTED, UNRESOLVED = "confirmed", "unconverted", "unresolved"


@dataclass
class Entry:
    name: str                      # 人が書いたカード名
    count: int
    card_id: str | None = None     # 人または resolver が確定した ID（任意）


@dataclass
class DeckProposal:
    name: str
    entries: list[Entry]
    tags: list[str] = field(default_factory=list)     # 自由タグ（複数可。単一ラベル分類にしない）
    source: str = ""                                   # 提案者・出典
    notes: str = ""
    status: str = "proposed"                           # proposed / adopted / rejected（採否の記録は ledger 側が正）
    schema_version: int = SCHEMA_VERSION
    extra: dict = field(default_factory=dict)          # 未知項目は捨てずに保持

    def size(self) -> int:
        return sum(e.count for e in self.entries)

    def plan_id(self) -> str:
        """内容（名前と枚数の多重集合）から決まる ID。並び順・タグ・メモは影響しない。"""
        key = json.dumps(sorted((e.card_id or e.name, e.count) for e in self.entries), ensure_ascii=False)
        return hashlib.sha256(key.encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        d = {"schema_version": self.schema_version, "name": self.name, "tags": self.tags, "source": self.source,
             "notes": self.notes, "status": self.status,
             "entries": [{"name": e.name, "count": e.count, **({"card_id": e.card_id} if e.card_id else {})} for e in self.entries]}
        return {**self.extra, **d}


def from_dict(d: dict) -> DeckProposal:
    v = d.get("schema_version", SCHEMA_VERSION)
    if v > SCHEMA_VERSION:
        raise ValueError(f"新しいスキーマ版 {v}（対応は {SCHEMA_VERSION} まで。版を上げるときは対応表を足す）")
    return DeckProposal(name=d["name"], entries=[Entry(e["name"], int(e["count"]), e.get("card_id")) for e in d.get("entries", [])],
                        tags=list(d.get("tags", [])), source=d.get("source", ""), notes=d.get("notes", ""),
                        status=d.get("status", "proposed"), schema_version=v,
                        extra={k: x for k, x in d.items() if k not in KNOWN})


def load(path: str | Path) -> DeckProposal:
    return from_dict(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def save(p: DeckProposal, path: str | Path) -> None:
    Path(path).write_text(yaml.safe_dump(p.to_dict(), allow_unicode=True, sort_keys=False), encoding="utf-8")


Resolver = Callable[[Entry], "tuple[str | None, str]"]   # Entry -> (card_id|None, CONFIRMED/UNCONVERTED/UNRESOLVED)


def check(p: DeckProposal, resolver: Resolver | None = None, deck_size: int = 40, copy_limit: int = 4) -> dict:
    """検査。copy_limit 超過・枚数違いは問題として返す。未確定のカードを含むデッキは unverified=True（主指標・自動採用に使わない）。"""
    issues, cards = [], []
    seen: dict[str, int] = {}
    for e in p.entries:
        seen[e.name] = seen.get(e.name, 0) + e.count
        cid, st = resolver(e) if resolver else (e.card_id, UNRESOLVED)
        cards.append({"name": e.name, "count": e.count, "card_id": cid, "state": st})
    issues += [f"{n} が {c} 枚（上限 {copy_limit}）" for n, c in seen.items() if c > copy_limit]
    if p.size() != deck_size:
        issues.append(f"合計 {p.size()} 枚（{deck_size} 枚が必要）")
    unverified = any(c["state"] != CONFIRMED for c in cards)
    return {"plan_id": p.plan_id(), "issues": issues, "cards": cards, "unverified": unverified}
