"""データファイルの型（data/schema/*.schema.json）に実データが合っていること。"""
import json

import pytest
import yaml

jsonschema = pytest.importorskip("jsonschema")
referencing = pytest.importorskip("referencing")

from dmsim.cards import approval as ap  # noqa: E402
from dmsim.cards.cardfiles import card_files  # noqa: E402
from dmsim.cards.defs import DATA, load_tables  # noqa: E402

SCH = DATA / "schema"


def _validator(name):
    reg = referencing.Registry()
    for f in SCH.glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        reg = reg.with_resource(f.name, referencing.Resource.from_contents(d))
    return jsonschema.Draft202012Validator(json.loads((SCH / name).read_text(encoding="utf-8")), registry=reg)


# 「好きな枚数」を count: any と変換したカード。検査（defs）は通るが、型にもエンジンにも無い表現（実行時に bad expr any）。
# 語彙（up_to の上限なし等）が決まったら変換し直して、この一覧を空にする。承認は effectcheck が止める。
KNOWN_UNSUPPORTED: set = set()


def test_card_files_match_schema():
    v = _validator("card_file.schema.json")
    for f in card_files():
        doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        doc["cards"] = [c for c in doc["cards"] if c["id"] not in KNOWN_UNSUPPORTED]
        errs = [e.message[:200] for e in v.iter_errors(doc)][:3]
        assert not errs, (f.name, errs)


def test_approval_entry_matches_schema():
    raw = {"id": "dm01-s01", "name": "x", "types": ["creature"], "civs": ["light"], "cost": 3, "keywords": ["blocker"]}
    led = {"dm01-s01": ap.entry(raw, "approved", "rule", ap.vocab_versions(load_tables()), verify="ok")}
    assert not list(_validator("approvals.schema.json").iter_errors(led))
    bad = {"dm01-s01": {**led["dm01-s01"], "by": "bot"}}
    assert list(_validator("approvals.schema.json").iter_errors(bad))


def test_catalog_and_rejects_schemas_accept_samples():
    assert not list(_validator("catalog_sets.schema.json").iter_errors(
        {"products": {"26ex4": {"name": "n", "code": "dm26ex4", "ids": ["dm26ex4-CHO005"], "listed": True, "total": 1, "fetched": 1}}}))
    assert not list(_validator("rejects_row.schema.json").iter_errors(
        {"id": "dm24ex2-cho042", "name": "n", "text": "", "gaps": [], "error": "能力文が無い"}))
