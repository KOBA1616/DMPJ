"""語彙パイロット第371弾の対象カード検証（登録形）。

対象は pure な set_power_zero の全1件:
- dmex15-b025 永遠の無
ラウンド406で登録済み。登録形は提出形と完全一致:
partial の骨格〔types [spell] / civs [darkness] /
cost 5 / mana 1、abilities・spell ともに無し〕に
第371弾の確立形〔spell の choose {owner: opp,
as: victim} / modify {power_set: 0,
duration: end_of_turn} の2 op（第370弾
set_power_to_zero の確立形と同形。登録先例
dmrp11-zs01・dm24ex2-042）〕を足し、unsupported を
外したもの。**補完あり**: partial の text は第2条項の
断片（「そのクリーチャーのパワーを０にする」）だけの
ため、text には行の公式テキスト全文を入れた。
単面カードで未検証の面は無い。alias は無い。

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
TARGET = "dmex15-b025"
GAP = "set_power_zero"

SPELL = [{"op": "choose",
          "select": {"zone": "bz", "owner": "opp",
                     "filter": {"types": ["creature"]},
                     "count": 1},
          "as": "victim"},
         {"op": "modify",
          "select": {"ref": "victim"},
          "mod": {"power_set": 0},
          "duration": "end_of_turn"}]
FULL_TEXT = ("相手のクリーチャーを１体選ぶ。このターン、そのクリーチャーの"
             "パワーを０にする。（パワー０以下のクリーチャーは破壊される）")


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


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["types"] == ["spell"] and c["civs"] == ["darkness"]
    assert c["cost"] == 5 and c["mana"] == 1
    assert not c.get("abilities")        # abilities は無いまま
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    assert c["spell"] == SPELL
    assert len(c["spell"]) == 2          # choose / modify の2 op ちょうど
    assert not (c.get("source") or {}).get("unsupported")
    assert not (c.get("source") or {}).get("aliases")
    d = parse_card(c, TABLES)
    assert [op["op"] for op in d.spell] == ["choose", "modify"]
    assert d.spell[0]["as"] == "victim"
    assert d.spell[1]["mod"] == {"power_set": 0}
    # プロト T1115 と spell が完全一致
    proto = proto_card("T1115")
    assert proto["spell"] == SPELL
