"""語彙パイロット第380弾の対象カード検証（登録形）。

対象は pure な up_to_cost_reduction の残り全1件:
- dm23rp4x-tf03 西南の超人 / 断断打つべしナウ
ラウンド415で登録済み。登録形は提出形と完全一致:
partial の組立て済み部分（クリーチャー面のセイバー
置換・呪文面の3 op）に第347弾の確立形 static
〔affects {zone: hand, owner: you, filter
{races: [ジャイアント]}}, mod {cost: -2}〕を
クリーチャー面の条項順どおり先頭に足し、unsupported
を外したもの。クリーチャー面の abilities は
[確立形 static, セイバー置換] の2件ちょうど、呪文面の
spell は3 op ちょうど。top の text は rejects 行に
クリーチャー面分しか無いため、提出形では面テキストを
「 ／ 」で連結して補完した（dm23bd6-003 等の
ツインパクト登録形の作法。クリーチャー面は
「。/ セイバー」を dmbd02-014 登録形に倣い
「。セイバー」に直し、呪文面は「S・トリガー 自分…」
の平坦形）。alias は dm23rp4-t03 / dm23rp4-tf03 /
dmex04-017 / dmex13-017 / dmex15-b073 の5件
（いずれも rejects に独自行は無く、登録形の
source.aliases に入っている）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無いことを
第380弾で実測済みで、ラウンド415は通常どおり submit
できた。

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
from tests.test_vocab_pilot380 import (  # noqa: E402
    COST_STATIC, FACE0, FACE1, SABER, SPELL_OPS, TOP_TEXT)

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dm23rp4x-tf03"
GAP = "up_to_cost_reduction"
ALIASES = ["dm23rp4-t03", "dm23rp4-tf03", "dmex04-017",
           "dmex13-017", "dmex15-b073"]
NAME = "西南の超人 / 断断打つべしナウ"


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
    # alias に rejects の独自行は無い
    for a in ALIASES:
        assert a not in rows


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["mana"] == 1
    assert c["text"] == TOP_TEXT         # 連結全文（補完あり）
    # 登録形は提出形と完全一致: faces は確立形ちょうど
    assert c["faces"] == [FACE0, FACE1]
    f0, f1 = c["faces"]
    assert f0["abilities"] == [COST_STATIC, SABER]
    assert len(f0["abilities"]) == 2
    assert f1["spell"] == SPELL_OPS
    assert len(f1["spell"]) == 3
    assert f1["keywords"] == ["s_trigger"]
    assert not c.get("aliases")
    # alias 5件は source.aliases に入っている
    assert (c.get("source") or {}).get("aliases") == ALIASES
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d is not None
    # プロト T1134 と faces・mana・text が完全一致
    proto = proto_card("T1134")
    assert proto["faces"] == [FACE0, FACE1]
    assert proto["mana"] == 1
    assert proto["text"] == TOP_TEXT
