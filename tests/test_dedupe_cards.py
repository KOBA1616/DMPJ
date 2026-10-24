import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import dedupe_cards as dc  # noqa: E402


def test_keep_newest_and_kinds(tmp_path):
    import json
    base = {"card_type": "呪文", "civilization": "水", "cost": "2", "text": "カードを1枚引く。"}
    rows = {
        "new": [{**base, "id": "dm26ex1-001", "official_id": "DM26-EX1-001", "product": "new", "name": "A"}],
        "old": [{**base, "id": "dm01-001", "official_id": "DM-01-001", "product": "old", "name": "A"},
                {**base, "id": "dm01-002", "official_id": "DM-01-002", "product": "old", "name": "B"},
                {**base, "id": "dm01-003", "official_id": "DM-01-003", "product": "old", "name": "C", "text": "別"}],
    }
    for k, v in rows.items():
        (tmp_path / f"{k}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in v), encoding="utf-8")
    res = dc.build({"products": {"new": {}, "old": {}}}, tmp_path)
    assert (res["total_rows"], res["unique"], res["dropped"]) == (4, 2, 2)
    g = res["groups"][0]
    assert g["keep"]["id"] == "dm26ex1-001"
    assert sorted(d["kind"] for d in g["dropped"]) == ["renamed", "reprint"]
