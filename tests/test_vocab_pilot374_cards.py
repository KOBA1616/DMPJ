"""語彙パイロット第374弾の対象カード検証（登録形）。

対象は pure な global_s_trigger_lock の全1件:
- dm23rp1-t2 石像男
ラウンド409で登録済み。登録形は提出形と完全一致:
partial の骨格〔闇 / コスト6 / パワー5000 / 種族
ヘドリアン、keywords・abilities ともに無し〕に
第374弾の確立形〔static {affects: {zone: shield,
owner: opp}, if: {all: [cmp count {zone: bz,
owner: you, filter: {types: [creature], civs:
[文明]}} >= 1 ×5文明]}, mod: {deny: [s_trigger]}}〕
1能力を足し、unsupported を外したもの。abilities は
1件ちょうど、keywords は無いまま。partial の text は
行の公式テキスト全文と一致するため補完なし。単面
カードで未検証の面は無い。alias は dm23rp1-tf2 /
dm24-020 の2件で、いずれも rejects に独自行は無く、
登録エントリの source.aliases に記録されている。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import find, proto_card  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dm23rp1-t2"
GAP = "global_s_trigger_lock"
ALIASES = ["dm23rp1-tf2", "dm24-020"]

CIVS5 = ["light", "water", "darkness", "fire", "nature"]


def _all_civs_creatures():
    return {"all": [{"cmp": [{"count": {"zone": "bz", "owner": "you",
                                        "filter": {"types": ["creature"],
                                                   "civs": [c]}}},
                             ">=", 1]}
                    for c in CIVS5]}


LOCK = {"kind": "static",
        "affects": {"zone": "shield", "owner": "opp"},
        "if": _all_civs_creatures(),
        "mod": {"deny": ["s_trigger"]}}
FORM = [LOCK]
FULL_TEXT = ("自分のクリーチャーで、すべての文明が揃っていれば、"
             "相手は自身の「S・トリガー」を使えない。")


def _reject_rows():
    rows = {}
    with open(ROOT / "data/cards/raw/rejects.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                rows[r["id"]] = r
    return rows


def test_target_registered_and_family_cleared():
    rows = _reject_rows()
    assert TARGET not in rows            # 登録により対象行は解消
    fam = [i for i, x in rows.items() if GAP in (x.get("gaps") or [])]
    assert fam == []                     # ファミリーはこの1件だけだった
    assert find(CONVERTED, TARGET) is not None
    # alias 2件は rejects に独自行が無いまま
    for a in ALIASES:
        assert a not in rows


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert not c.get("keywords")                       # keywords は無いまま
    assert c["types"] == ["creature"] and c["civs"] == ["darkness"]
    assert c["cost"] == 6 and c["power"] == 5000
    assert c["races"] == ["ヘドリアン"]
    assert c["mana"] == 1
    assert c["text"] == FULL_TEXT                      # 公式テキスト全文
    # 登録形は提出形と完全一致: abilities は確立形1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")                        # aliases 欄は使わない
    assert (c.get("source") or {}).get("aliases") == ALIASES
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert LOCK in d.abilities
    # プロト T1122 と abilities が完全一致
    proto = proto_card("T1122")
    assert proto["abilities"] == FORM
