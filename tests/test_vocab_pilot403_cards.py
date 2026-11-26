"""語彙パイロット第403弾の対象カード検証（登録形）。

対象は cast_limit_once_per_turn（pure 1件）:
- dmex03-g02 ゴールデン・ザ・ジョニー
この gap は multi 2件（一音の妖精 dm26ex2-pr006 /
dm26ex4-cho031、opponent_creature_entry_limit_
once_per_turn との複合）にも現れるが、そちらは
対象外で残置する（ラウンド438でも reopen に
巻き込まれず gaps・partial を保って残留）。
ラウンド438で登録済み。登録形は提出形と完全一致:
partial の骨格（無色 / コスト7 / パワー10000 /
種族 ジョーカーズ、mana 1、keywords
[speed_attacker, double_breaker]、構築済み
マスター・ブラスター攻撃時誘発1件）に第403弾の
確立形 static〔affects {zone: hand, owner: opp,
filter: {types: [spell]}}、mod {deny: [{action:
cast, max_per_turn: 1}]}〕1件を足し、unsupported
を外したもの。abilities はこの2件ちょうど、
keywords は [speed_attacker, double_breaker]
のまま。**補完なし**（partial の text は公式
全文と一致）。alias は dmex01-076 / promoy16-063
の2件で、いずれも rejects に独自行は無く、登録
エントリの source.aliases は validate が
identity.aliases_for から自動付与した2件
（identity 実測で canon_id は対象・全 alias とも
dmex03-g02）。cast_limit_once_per_turn は pure は
解消したが multi 2件が残るため完全解消しない。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は ([speed_attacker, double_breaker],
条項テキスト, []) を返し、定型所有は空（第403弾で
実測）。

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
from tests.test_vocab_pilot403 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmex03-g02"
GAP = "cast_limit_once_per_turn"
NAME = "ゴールデン・ザ・ジョニー"
ALIASES = ["dmex01-076", "promoy16-063"]


def _reject_rows():
    rows = {}
    with open(ROOT / "data/cards/raw/rejects.jsonl",
              encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                rows[r["id"]] = r
    return rows


def test_target_registered_and_family_state():
    rows = _reject_rows()
    assert TARGET not in rows            # 登録により対象行は解消
    pure = sorted(i for i, x in rows.items()
                  if (x.get("gaps") or []) == [GAP])
    assert pure == []                    # pure ファミリーは解消
    multi = sorted(i for i, x in rows.items()
                   if GAP in (x.get("gaps") or [])
                   and len(x.get("gaps") or []) > 1)
    # multi 2件（一音の妖精）は複合 gap のため対象外で残置
    assert multi == ["dm26ex2-pr006", "dm26ex4-cho031"]
    for a in ALIASES:
        assert a not in rows             # alias に独自行は無い
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["zero"]
    assert c["cost"] == 7 and c["power"] == 10000 and c["mana"] == 1
    assert c["races"] == ["ジョーカーズ"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    assert c["keywords"] == ["speed_attacker", "double_breaker"]
    # 登録形は提出形と完全一致: 誘発＋static の2能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert src.get("aliases") == ALIASES  # validate の自動付与
    assert not src.get("unsupported")
    d = parse_card(c, TABLES)
    # parse では keyword 2件が派生 static に展開されるため、
    # abilities は [speed_attacker 派生 static,
    # double_breaker 派生 static, 構築済み誘発, 確立形 static]
    assert len(d.abilities) == 4
    assert d.abilities[0].get("keyword") == "speed_attacker"
    assert d.abilities[1].get("keyword") == "double_breaker"
    assert d.abilities[2] == FORM[0]
    assert d.abilities[3] == FORM[1]
    # プロト T1170 と abilities・text・骨格が完全一致
    proto = proto_card("T1170")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power",
              "races", "mana", "keywords"):
        assert proto[k] == c[k]
