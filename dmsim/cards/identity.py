"""カード同一性をデータ変換・承認に結びつける（同名は同じカード。最新版の ID と本文を採用し、古い ID は aliases に残す）。

土台は dmsim.canonical。ここでは次を行う。
- canonical_rows: 変換対象を最新版の ID だけに絞る
- aliases_for: 変換したカードの source.aliases に入れる古い ID
- AliasDict: 旧 ID で引いても最新版のカードが返る辞書（Rules.cards 用）
- relocate: 変換済みの旧 ID カードを最新 ID へ寄せる（本文が同じなら承認を引き継ぎ、違えば取り消して再変換に回す）
"""
from __future__ import annotations

from . import approval as ap
from . import canonical


def canon_id(card_id: str) -> str:
    return canonical.alias_to_canonical().get(card_id, card_id)


def canonical_rows(rows: list[dict]) -> list[dict]:
    """原文の行のうち、最新版の ID のもの（同名の古い版は除く）。索引に無い行はそのまま残す。"""
    return [r for r in rows if canon_id(r["id"]) == r["id"]]


def aliases_for(name: str, card_id: str) -> list[str]:
    e = canonical.canonical_index().get(canonical.name_key(name))
    return list(e["aliases"]) if e and e["id"] == card_id else []


class AliasDict(dict):
    """旧 ID で引いても最新版を返す。キーの一覧や反復は最新版の ID だけ。"""

    aliases: dict = {}

    def __init__(self, data=(), aliases: dict[str, str] | None = None):
        super().__init__(data)
        self.aliases = {a: c for a, c in (aliases or {}).items() if not dict.__contains__(self, a) and dict.__contains__(self, c)}

    def __reduce__(self):      # deepcopy / pickle で aliases を失わない
        return (AliasDict, (dict(self), self.aliases))

    def __missing__(self, key):
        if key in self.aliases:
            return self[self.aliases[key]]
        raise KeyError(key)

    def __contains__(self, key):
        return dict.__contains__(self, key) or key in self.aliases

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


def _text_of(card: dict) -> str:
    return canonical.normalize_text(str(card.get("text", "")))


def relocate(cards: list[dict], ledger: dict, versions: dict) -> dict:
    """旧 ID のカードを最新 ID へ寄せる。cards と ledger をその場で更新し、結果の件数を返す。
    - 最新版が既に変換済み: 旧 ID のカードは消す（aliases は最新版の source に足す）
    - 本文（正規化後）が最新版と同じ: ID を最新版に付け替え、承認済みなら引き継ぐ（by=inherit）
    - 本文が違う: 旧カードを消し、承認は取り消す。最新版の原文があらためて変換される（承認も再検証）
    付け替えた ID の弾が変わる場合の置き場所の移動は、cardstore.write が行う。"""
    idx = canonical.canonical_index()
    by_name = {canonical.name_key(c["name"]): c for c in cards}
    have = {c["id"] for c in cards}
    stats = {"renamed": 0, "dropped_dup": 0, "dropped_text_changed": 0, "inherited": 0}
    out = []
    for c in cards:
        e = idx.get(canonical.name_key(c.get("name") or ""))
        if not e or e["id"] == c["id"] or c["id"] not in e["aliases"]:
            out.append(c)
            continue
        new_id, old_id = e["id"], c["id"]
        old_entry = ledger.pop(old_id, None)
        if new_id in have:
            tgt = by_name.get(canonical.name_key(c["name"]))
            if tgt and tgt["id"] == new_id:
                src = tgt.setdefault("source", {})
                src["aliases"] = sorted(set(src.get("aliases", [])) | {old_id} | set(c.get("source", {}).get("aliases", [])))
            stats["dropped_dup"] += 1
            continue
        if _text_of(c) != canonical.normalize_text(e["text"]):
            if old_entry:
                ledger[old_id] = {**old_entry, "status": "pending", "stale": f"最新版({new_id})と本文が違う。再変換して再検証"}
            stats["dropped_text_changed"] += 1
            continue
        src = dict(c.get("source") or {})
        src["official"] = new_id
        src["aliases"] = sorted((set(src.get("aliases", [])) | {old_id} | set(e["aliases"])) - {new_id})
        new = {**c, "id": new_id, "source": src}
        out.append(new)
        have.add(new_id)
        stats["renamed"] += 1
        if old_entry and old_entry.get("status") == "approved":
            ledger[new_id] = ap.entry(new, "approved", "inherit", versions, inherited_from=old_id)
            stats["inherited"] += 1
    cards[:] = out
    return stats
