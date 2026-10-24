"""取得済みの生データから、効果が完全に一致するカードをまとめ、最新の収録だけを残す一覧を作る。

    python tools/dedupe_cards.py            # data/cards/catalog/dedupe.json を書く

- 一致の判定: 名前とIDを除く全項目（種類・文明・コスト・パワー・種族・効果文・ツインパクトの各面）が同じ。
- kind: reprint（名前も同じ＝再録） / renamed（名前だけ違う、効果は完全一致）。renamed は人が見て採否を決める。
- 最新: 台帳の商品の並び（新しい弾が先）で先頭にあるもの。
- 除外したカードは dropped に残るだけで、生データは消さない。
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import catalog_sets as cs  # noqa: E402
import fetch_cards as fc  # noqa: E402

SKIP = {"id", "official_id", "product", "name", "set_no", "set_notation"}


def signature(row: dict) -> str:
    body = {k: v for k, v in row.items() if k not in SKIP and k != "faces"}
    body["faces"] = [{k: v for k, v in f.items() if k != "name"} for f in row.get("faces", [])]
    return json.dumps(body, ensure_ascii=False, sort_keys=True)


def names(row: dict) -> list[str]:
    return [row["name"]] + [f.get("name", "") for f in row.get("faces", [])]


def build(led: dict, raw_dir: Path) -> dict:
    order = {v: i for i, v in enumerate(led["products"])}
    rows = []
    for f in raw_dir.glob("*.jsonl"):
        rows += [fc.repair(json.loads(x)) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
    rows.sort(key=lambda r: (order.get(r["product"], 10**6), r["official_id"]))
    groups = defaultdict(list)
    for r in rows:
        groups[signature(r)].append(r)
    out, dropped = [], 0
    for g in groups.values():
        if len(g) < 2:
            continue
        keep, rest = g[0], g[1:]
        dropped += len(rest)
        out.append({
            "keep": {"id": keep["id"], "name": keep["name"], "product": keep["product"]},
            "dropped": [{"id": r["id"], "name": r["name"], "product": r["product"],
                         "kind": "reprint" if names(r) == names(keep) else "renamed"} for r in rest],
        })
    return {"total_rows": len(rows), "unique": len(rows) - dropped, "dropped": dropped, "groups": out}


def main():
    led = cs.load()
    res = build(led, ROOT / "data" / "cards" / "raw" / "by_product")
    p = ROOT / "data" / "cards" / "catalog" / "dedupe.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"取得 {res['total_rows']} 行 → 残す {res['unique']} / 除外 {res['dropped']}（{len(res['groups'])}組）")


if __name__ == "__main__":
    main()
