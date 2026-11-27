"""語彙パイロット第440弾（cards 側）: bottom_deck_mill —
ラウンド474で登録済み。

対象は dmx13-010 真実の名 ハデスギル・スキル
（pure 1件）。提出形は partial（骨格〔クリーチャー /
ゼロ / コスト8 / パワー8000 / 種族
ドラゴン・ゾンビ/アンノウン、mana 1、keywords
[double_breaker]、text は公式全文〕）に第440弾の
確立形 abilities 2件〔(1) trigger {when:
{event: move, to: bz, subject: self}, effect:
[may [move {select: {zone: deck, owner: you,
from_bottom: 5}, to: graveyard, reason: put}]]}、
(2) trigger {when: {event: move, from: bz,
to: graveyard, reason: destroy, subject: self},
effect: [may [play_free {select: {zone: graveyard,
owner: you, filter: {types: [creature],
colorless: true, evolution: false, not_name:
真実の名 ハデスギル・スキル}, count: 1}}]]}〕を
足し、unsupported を外したもの。**補完あり:
abilities**（trigger 2件とも。text・keywords の
補完は無い）。山札の下からのミルは第287弾の
確立形（登録先例 dmx13-015 形E・dm26sd1-n006）、
同名除外つき墓地からの play_free は登録済み
dmd19-006、colorless の受けは登録済み dmx13-015
形E＝ドリフト。登録形は提出形と完全一致
〔source 以外の全フィールドを照合〕、abilities は
trigger 2件ちょうど、keywords は [double_breaker]
のまま、text は公式全文。alias は無し（canon は
対象自身、同名の公式行は x13 の1件のみ）。
ファミリーは完全解消。

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
from tests.test_vocab_pilot440 import FORM, FULL_TEXT  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
TARGET = "dmx13-010"
GAP = "bottom_deck_mill"
NAME = "真実の名 ハデスギル・スキル"

SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["zero"],
    "cost": 8,
    "power": 8000,
    "races": ["ドラゴン・ゾンビ", "アンノウン"],
    "mana": 1,
    "text": FULL_TEXT,
    "keywords": ["double_breaker"],
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
    assert len(c["abilities"]) == 2      # abilities は trigger 2件ちょうど
    assert [a["kind"] for a in c["abilities"]] == ["trigger", "trigger"]
    assert c["abilities"] == FORM
    assert c["text"] == FULL_TEXT        # 公式全文
    assert c["keywords"] == ["double_breaker"]
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
    assert d.types == ["creature"]
    assert d.cost == 8 and d.power == 8000
    for a in FORM:
        assert a in d.abilities
    proto = proto_card("T1230")
    for k in ("name", "types", "civs", "cost", "power",
              "races", "mana", "text", "abilities", "keywords"):
        assert proto[k] == SUBMIT[k], k


def test_official_row_consistency():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/x13.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    off = next(r for r in rows if r["id"] == TARGET)
    assert off["name"] == NAME
    assert off["text"] == FULL_TEXT
    assert int(off["cost"]) == 8 and int(off["power"]) == 8000
    assert off["race"] == "ドラゴン・ゾンビ/アンノウン"
    assert off["civilization"] == "ゼロ"
