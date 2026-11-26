"""語彙パイロット第408弾の対象カード検証（登録形）。

対象は enters_tapped_rule（pure 1件、multi にも現れない）:
- dmex11-005 その子供、凶暴につき
ラウンド443で登録済み。登録形は提出形と完全一致
（差分は validate が identity.aliases_for から
自動付与した source.aliases のみ）: partial の
骨格（クリーチャー / 火 / コスト4 / パワー4000 /
種族 ヒューマノイド / チルドレン、mana 1、
keywords・abilities ともに無し）に第408弾の
確立形 static 3件〔付与: affects {zone: bz,
owner: you, filter: {types: [creature],
cost_le: 3}}, mod: {grant: [speed_attacker]}／
タップ入り（進化）: affects {zone: bz, owner:
opp, filter: {types: [evolution]}}, mod:
{grant: [enters_tapped]}／タップ入り（スピード
アタッカー）: affects {zone: bz, owner: opp,
filter: {types: [creature], keyword:
speed_attacker}}, mod: {grant: [enters_tapped]}〕
を足し、unsupported を外したもの。abilities は
この3件ちょうど、keywords は無いまま。
**補完あり: text のみ**（partial の text は断片
「タップしてバトルゾーンに出る」のため、登録形の
text は行の公式テキスト全文）。

alias は dmr08s-004 / dmx24-009 / promoy11-066 の
3件で、いずれも rejects に独自行は無く、identity
実測で canon_id は対象・全 alias とも dmex11-005。
enters_tapped_rule は本登録で完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い
（第408弾で実測）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore, identity  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import find, proto_card  # noqa: E402
from tests.test_vocab_pilot408 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmex11-005"
GAP = "enters_tapped_rule"
NAME = "その子供、凶暴につき"
ALIASES = ["dmr08s-004", "dmx24-009", "promoy11-066"]

# 提出形: partial の骨格＋確立形 static 3件（text は公式全文に補完）
SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 4,
    "power": 4000,
    "races": ["ヒューマノイド", "チルドレン"],
    "mana": 1,
    "text": FULL_TEXT,
    "abilities": FORM,
}


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
    fam = sorted(i for i, x in rows.items()
                 if GAP in (x.get("gaps") or []))
    assert fam == []                     # ファミリーは完全解消
    for a in ALIASES:
        assert a not in rows             # alias に独自行は無い
    assert identity.canon_id(TARGET) == TARGET
    for a in ALIASES:
        assert identity.canon_id(a) == TARGET
    assert identity.aliases_for(NAME, TARGET) == ALIASES
    assert find(CONVERTED, TARGET) is not None
    for a in ALIASES:
        assert find(CONVERTED, a) is None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 4 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ヒューマノイド", "チルドレン"]
    assert c["text"] == FULL_TEXT        # 公式全文（text のみ補完）
    # 登録形は提出形と完全一致: abilities は確立形 static 3件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 3
    assert not c.get("keywords")         # submit は text 由来 keyword を union しない
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ALIASES  # validate の自動付与
    d = parse_card(c, TABLES)
    for a in FORM:
        assert a in d.abilities
    assert len(d.abilities) == 3
    assert not d.keywords
    # プロト T1176 と abilities・text・骨格が完全一致
    proto = proto_card("T1176")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power", "races", "mana"):
        assert proto[k] == SUBMIT[k]
    assert not proto.get("keywords")
