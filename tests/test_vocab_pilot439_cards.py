"""語彙パイロット第439弾（cards 側）: untap_prevention —
ラウンド473で登録済み。

対象は dmr14-006 聖霊龍王 スタグネイト（pure 1件）。
提出形は partial（骨格〔クリーチャー/進化 / 光 /
コスト5 / パワー10500 / 種族 エンジェル・コマンド・
ドラゴン、mana 1、evolve_from {civs: [light],
race_has: ドラゴン}〕）に text の公式全文と
keywords [double_breaker] と第439弾の確立形
ability 1件〔static {affects: {zone: bz, owner: opp,
filter: {types: [creature]}}, if: {exists:
{ref: self, filter: {tapped: true}}}, mod:
{deny: [untap_at_start]}}〕を足し、unsupported を
外したもの。**補完あり: text＋keywords＋abilities**。
条件の if は登録済み dmx02-027 の static の形
そのもの、deny [untap_at_start] は第400弾の
確立形＝ドリフト。登録形は提出形と完全一致
〔source 以外の全フィールドを照合〕、abilities は
static 1件ちょうど、keywords は [double_breaker]
のまま、evolve_from も保持、text は公式全文。
alias は無し（canon は対象自身、同名の公式行は
r14 の1件のみ）。ファミリーは完全解消。

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
from tests._conv_cache import PROTO, find, proto_card  # noqa: E402
from tests.test_vocab_pilot439 import FORM, FULL_TEXT  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
TARGET = "dmr14-006"
GAP = "untap_prevention"
NAME = "聖霊龍王 スタグネイト"

SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature", "evolution"],
    "civs": ["light"],
    "cost": 5,
    "power": 10500,
    "races": ["エンジェル・コマンド・ドラゴン"],
    "mana": 1,
    "text": FULL_TEXT,
    "keywords": ["double_breaker"],
    "evolve_from": {"civs": ["light"], "race_has": "ドラゴン"},
    "abilities": FORM,
}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_registered_and_family_cleared():
    rows = _reject_rows()
    mine = {r["id"]: r for r in rows}
    assert TARGET not in mine            # 対象行は登録で解消
    # ファミリーは pure 1件のみで完全解消
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == []
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 1      # abilities は static 1件ちょうど
    assert c["abilities"][0] == FORM[0]
    assert c["text"] == FULL_TEXT        # 公式全文
    assert c["keywords"] == ["double_breaker"]
    assert c["evolve_from"] == {"civs": ["light"],
                                "race_has": "ドラゴン"}
    src = c.get("source") or {}
    assert not src.get("unsupported")
    # alias 無し・正本は対象自身
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []
    assert find(str(PROTO), TARGET) is None
    # 判断待ちの stale 行には触っていない
    assert mine["dm02-046"]["gaps"] == [
        "destroy_self_after_attacking_player"]


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.types == ["creature", "evolution"]
    assert d.cost == 5 and d.power == 10500
    assert FORM[0] in d.abilities
    proto = proto_card("T1229")
    for k in ("name", "types", "civs", "cost", "power",
              "races", "mana", "text", "abilities", "keywords",
              "evolve_from"):
        assert proto[k] == SUBMIT[k], k


def test_official_row_consistency():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/r14.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    off = next(r for r in rows if r["id"] == TARGET)
    assert off["name"] == NAME
    assert off["text"] == FULL_TEXT
    assert int(off["cost"]) == 5 and int(off["power"]) == 10500
    assert off["race"] == "エンジェル・コマンド・ドラゴン"
