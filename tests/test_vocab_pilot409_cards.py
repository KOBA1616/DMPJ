"""語彙パイロット第409弾の対象カード検証（登録形）。

対象は enters_tapped_grant（pure 1件、multi にも現れない）:
- dm26ex3-010 永遠のリュウセイ・カイザー
ラウンド444で登録済み。登録形は提出形と完全一致
（差分は validate が identity.aliases_for から
自動付与した source.aliases のみ）: partial の
骨格（クリーチャー / 火 / コスト8 / パワー8000 /
種族 レッド・コマンド・ドラゴン / ハンター、
mana 1、keywords [double_breaker]、abilities は
第1条項の static 1件が構築済み）に第409弾の
確立形 abilities 3件〔第1条項: static {affects:
{owner: you, filter: {types: [creature]}}, mod:
{grant: [speed_attacker]}}（partial 構築済み）／
第2条項: static {affects: {zone: bz, owner: opp,
filter: {types: [creature]}}, mod: {grant:
[enters_tapped]}}（登録済み dmc52-007・第340弾と
完全一致）／第3条項: replace {zone: hand,
optional: true, when: {event: move, from: hand,
to: graveyard, reason: discard, subject: self,
by: opp}, instead: [move {select: {ref: self,
count: 1}, to: bz, reason: put}]}（同一文面の
登録済み dm26ex3-dcr005 と完全一致）〕を足し、
unsupported を外したもの。abilities はこの
3件ちょうど、keywords は [double_breaker] のまま。
**補完なし**（partial の text は公式全文と一致）。

alias は dm23bd4-015 / dm26sd1-j002f /
dmbd05-003 / dmbd09-006 / dmd13-009 / dmd20-016 /
dmex15-a029 / dmex17-cho19 / dmr02-s03 /
dmx22b-094 / promoy15-051 の11件で、いずれも
rejects に独自行は無く、identity 実測で canon_id は
対象・全 alias とも dm26ex3-010。
enters_tapped_grant は本登録で完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (['double_breaker'], 条項テキスト,
[第1条項の static]) を返し、part[2] の定型所有は
第1条項の static 1件のみ。提出形の当該 static は
part[2] と完全一致のため merge_split の完全一致
dedupe で二重付着は起きず、登録後の abilities は
3件ちょうど（ラウンド444で実測確認済み）。

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
from tests.test_vocab_pilot409 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dm26ex3-010"
GAP = "enters_tapped_grant"
NAME = "永遠のリュウセイ・カイザー"
ALIASES = ["dm23bd4-015", "dm26sd1-j002f", "dmbd05-003",
           "dmbd09-006", "dmd13-009", "dmd20-016",
           "dmex15-a029", "dmex17-cho19", "dmr02-s03",
           "dmx22b-094", "promoy15-051"]

# 提出形: partial の骨格＋確立形 abilities 3件（補完なし）
SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 8,
    "power": 8000,
    "races": ["レッド・コマンド・ドラゴン", "ハンター"],
    "mana": 1,
    "keywords": ["double_breaker"],
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
    assert c["cost"] == 8 and c["power"] == 8000 and c["mana"] == 1
    assert c["races"] == ["レッド・コマンド・ドラゴン", "ハンター"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は確立形3件ちょうど
    # （split の part[2] 定型所有分の重複は無い）
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 3
    assert c["keywords"] == ["double_breaker"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ALIASES  # validate の自動付与
    d = parse_card(c, TABLES)
    for a in FORM:
        assert a in d.abilities
    # parse 後の double_breaker 派生 static を除き3件
    assert len(d.abilities) == 4
    assert "double_breaker" in d.keywords
    # プロト T1177 と abilities・text・骨格が完全一致
    proto = proto_card("T1177")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power", "races", "mana"):
        assert proto[k] == SUBMIT[k]
    assert proto["keywords"] == ["double_breaker"]
