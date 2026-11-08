"""墓地への仕込み手段の自動提案（静的）。cards 段階で部品が足りない時、
デッキ案に足す候補として「手札・山札・マナ等から自分の墓地へ置く効果」を持つ札を列挙する。
エンジンとカードデータは読み取りのみ。採否は deckplan.evaluate が決める。
使い方: python tools/suggest_prep.py [--limit N] [--from hand,deck,mana]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC_ZONES = {"hand", "deck", "mana", "shield", "shields"}


def _walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from _walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from _walk(v)


def prep_sources(card: dict) -> set[str]:
    """card の効果が自分の墓地へ送る元ゾーン（hand/deck/mana…）の集合。"""
    out: set[str] = set()
    for d in _walk(card.get("effects", card)):
        if d.get("op") != "move" or d.get("to") != "graveyard":
            continue
        sel = d.get("select")
        if not isinstance(sel, dict):
            continue
        z = sel.get("zone")
        if isinstance(z, str) and z in SRC_ZONES and sel.get("owner", "you") in ("you", "self"):
            out.add(z)
    return out


def scan(paths: list[Path] | None = None) -> list[dict]:
    paths = paths or sorted((ROOT / "data/cards").glob("*.yaml"))
    found, seen = [], set()
    for p in paths:
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        cards = data.get("cards", data) if isinstance(data, dict) else data
        items = cards.values() if isinstance(cards, dict) else cards or []
        for c in items:
            if not isinstance(c, dict) or not c.get("name"):
                continue
            src = prep_sources(c)
            if src and c["name"] not in seen:
                seen.add(c["name"])
                found.append({"name": c["name"], "cost": c.get("cost"), "from": sorted(src), "file": p.name})
    return found


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--from", dest="frm", default="")
    a = ap.parse_args(argv)
    want = set(filter(None, a.frm.split(",")))
    rows = [r for r in scan() if not want or want & set(r["from"])]
    rows.sort(key=lambda r: (r["cost"] if isinstance(r["cost"], int) else 99, r["name"]))
    for r in rows[: a.limit]:
        print(f'{r["name"]}\tcost={r["cost"]}\tfrom={",".join(r["from"])}\t{r["file"]}')
    print(f"# {len(rows)} 件", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
