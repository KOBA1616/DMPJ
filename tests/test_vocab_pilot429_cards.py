"""語彙パイロット第429弾（cards 側）:
drew_this_turn_condition — ラウンド464で登録済み。

対象は dmx22b-038 天災超邪 クロスファイア 2nd
（pure 1件、multi にも現れない）。partial は骨格のみ
（text は断片「このターン、カードを６枚以上引いて
いて」、keywords・free_if 未構築）で、提出形は
partial の骨格に第429弾の確立形 free_if
{all: [{cmp: [{turn_count: {kind: draw, owner: you}},
">=", 6]}, {not: {exists: {zone: bz, owner: you,
filter: {name: 天災超邪 クロスファイア 2nd}}}}]}
（第412弾の free_if turn_count cmp と登録済み
dmex08-226 / dm25ex3-rp4tr6 の同名不在条件の合成）
＋ keywords [speed_attacker, double_breaker] を足し、
unsupported を外したもの。**補完あり: text（公式
全文）＋keywords＋free_if**。abilities は無し。
alias は dmr11-017 / promoy12-063 の2件（canon は
対象自身、source.aliases のみに収載）。形の根拠は
本体テストの docstring 参照。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import copy
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.cards.identity import aliases_for, canon_id  # noqa: E402
from tests._conv_cache import find, proto_card  # noqa: E402
from tests.test_vocab_pilot429 import FREE_IF, FULL_TEXT, KEYWORDS, NAME  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
TARGET = "dmx22b-038"
ALIASES = ["dmr11-017", "promoy12-063"]
GAP = "drew_this_turn_condition"

SUBMIT = {"id": TARGET, "name": NAME, "types": ["creature"],
          "civs": ["water", "fire"], "cost": 7, "power": 7000,
          "races": ["アウトレイジMAX"], "mana": 1,
          "text": FULL_TEXT, "keywords": list(KEYWORDS),
          "free_if": FREE_IF}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_registered_and_family_cleared():
    rows = _reject_rows()
    mine = {r["id"]: r for r in rows}
    fam = sorted(r["id"] for r in rows
                 if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert TARGET not in mine            # 対象行は登録で解消
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert not c.get("abilities")        # abilities は無し
    assert c["keywords"] == KEYWORDS     # keywords そのまま
    assert c["free_if"] == FREE_IF       # free_if が保持されている
    assert c["text"] == FULL_TEXT        # 公式全文
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ALIASES  # alias は source.aliases のみ
    # alias 2件は独自行なし・独立エントリにもならない・正本は対象自身
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == ALIASES
    for a in ALIASES:
        assert a not in mine
        assert canon_id(a) == TARGET
        assert find(CONVERTED, a) is None
    # 判断待ちの stale 行には触っていない
    assert mine["dm02-046"]["gaps"] == [
        "destroy_self_after_attacking_player"]


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.free_if == FREE_IF
    assert d.keywords == KEYWORDS
    assert d.types == ["creature"] and d.civs == ["water", "fire"]
    assert d.cost == 7 and d.power == 7000
    assert d.races == ["アウトレイジMAX"]
    proto = proto_card("T1208")
    for k in ("name", "types", "civs", "cost", "power",
              "races", "mana", "text", "keywords", "free_if"):
        assert proto[k] == SUBMIT[k]
    assert not proto.get("abilities")


def test_official_row_matches_skeleton_and_text():
    off = None
    for line in (ROOT / "data/cards/raw/by_product/x22.jsonl") \
            .read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("id") == TARGET:
            off = r
    assert off is not None
    assert off["name"] == NAME
    assert off["text"] == FULL_TEXT
    assert int(off["cost"]) == 7
    assert int(off["power"]) == 7000
    assert off["race"] == "アウトレイジMAX"
    assert off["civilization"] == "水/火"
