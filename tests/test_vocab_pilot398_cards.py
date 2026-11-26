"""語彙パイロット第398弾の対象カード検証（登録形）。

対象は pure な speed_attacker_rule の全1件:
- dmex11-004 ディオーネ
ラウンド433で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 水 / コスト3 /
パワー3000 / 種族 シー・ハッカー、mana 1、
keywords [blocker, cannot_attack]、abilities 無し）
に第398弾の確立形 static〔affects {zone: bz,
owner: any, filter: {types: [creature], keyword:
speed_attacker, entered_this_turn: true}}, mod:
{deny: [attack_player, attack_creature]}〕を足し、
unsupported を外したもの。abilities はこの1件
ちょうど、keywords は [blocker, cannot_attack]
のまま。text は行の公式テキスト全文と一致する
（補完なし）。alias は dm14-004 / dmx22a-002 の
2件で、いずれも rejects に独自行は無く、登録形の
source.aliases に validate が自動付与して収載。
identity 実測で canon_id は対象・全 alias とも
dmex11-004。確立形は第362弾の登録先例
dm23rp4x-014 / dm23bd6-003 の形の owner を any に
広げ、フィルタに keyword: speed_attacker を足した
もの。既知の制限: 静的効果の affects 照合は base
（印刷特性）のため、付与されたスピードアタッカーは
フィルタに掛からない（エンジン全体の規約。第398弾
本体テストで固定）。ファミリーは完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (['blocker', 'cannot_attack'],
条項テキスト, []) を返し、part[2] の定型所有は空
＝ブロッカー無し（第398弾で実測）。

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
from tests.test_vocab_pilot398 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmex11-004"
GAP = "speed_attacker_rule"
NAME = "ディオーネ"
ALIASES = ["dm14-004", "dmx22a-002"]


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
    assert fam == []                     # ファミリーは完全解消
    for a in ALIASES:                    # alias に独自行は無い
        assert a not in rows
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["water"]
    assert c["cost"] == 3 and c["power"] == 3000 and c["mana"] == 1
    assert c["races"] == ["シー・ハッカー"]
    assert c["keywords"] == ["blocker", "cannot_attack"]
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完なし）
    # 登録形は提出形と完全一致: 確立形1能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert src.get("aliases") == ALIASES  # validate が自動付与
    assert not src.get("unsupported")
    d = parse_card(c, TABLES)
    own = [a for a in d.abilities if not a.get("keyword")]
    assert own == FORM
    # プロト T1165 と abilities・text・骨格が完全一致
    proto = proto_card("T1165")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power", "races", "mana"):
        assert proto[k] == c[k]
    assert proto["keywords"] == c["keywords"]
