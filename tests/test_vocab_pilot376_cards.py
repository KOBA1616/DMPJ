"""語彙パイロット第376弾の対象カード検証（登録形）。

対象は pure な mana_all_civs の全1件:
- dmex14-010 暴歌の妖精
ラウンド411で登録済み。登録形は提出形と完全一致:
partial の骨格（自然 / コスト3 / パワー3000 / 種族
スノーフェアリー・暴拳王国、mana 1、keywords・
abilities ともに無し）に第376弾の確立形2能力
〔第123弾の add_civs 常在型＋第206弾イディオムの
レインボーナス CIP 誘発〕を足し、unsupported を
外したもの。abilities はこの2件ちょうど、keywords は
無いまま。**補完あり: text には行の公式テキスト
全文を入れた**（partial の text は第1条項の断片
のみ）。単面カードで未検証の面は無い。alias は無い。
第260弾の常在キー mana_all_civs は支払い計算専用で
意味が違うため使っていない。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無いことを
第376弾で実測済みで、ラウンド411は通常どおり submit
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

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmex14-010"
GAP = "mana_all_civs"
ALL_CIVS = ["light", "water", "darkness", "fire", "nature"]

STATIC = {"kind": "static", "affects": {"zone": "mana", "owner": "you"},
          "mod": {"add_civs": ALL_CIVS}}
CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self"},
       "if": {"exists": {"zone": "bz", "owner": "you",
                         "filter": {"types": ["creature"],
                                    "multicolor": True}}},
       "effect": [{"op": "move",
                   "select": {"zone": "deck", "owner": "you",
                              "from_top": 1},
                   "to": "mana", "reason": "put"}]}
FORM = [STATIC, CIP]
FULL_TEXT = ("自分のマナゾーンにあるカードを、すべての文明のカードとして扱う。\n"
             "レインボーナス：このクリーチャーがバトルゾーンに出た時、"
             "バトルゾーンに自分の多色クリーチャーがあれば、"
             "自分の山札の上から１枚目をマナゾーンに置く。")


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
    assert not c.get("keywords")                       # keywords は無いまま
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 3 and c["power"] == 3000
    assert c["races"] == ["スノーフェアリー", "暴拳王国"]
    assert c["mana"] == 1
    assert c["text"] == FULL_TEXT                      # 公式テキスト全文（補完）
    # 登録形は提出形と完全一致: 確立形2能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("aliases")                        # alias は無い
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d.abilities == FORM
    # プロト T1124 と abilities・text が完全一致
    proto = proto_card("T1124")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT.replace("\n", "")
