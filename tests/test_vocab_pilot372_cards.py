"""語彙パイロット第372弾の対象カード検証（登録形）。

対象は pure な set_power の全1件:
- dm32-011 超神龍イエス・ヤザリス
ラウンド407で登録済み。登録形は提出形と完全一致:
partial の骨格〔types [creature] / civs [light] /
cost 5 / power 5500 / races [アポロニア・ドラゴン] /
mana 1、keywords [blocker]、abilities・evolve_from
ともに無し〕に **補完2点**〔types への evolution
追加・evolve_from {types: [creature],
keyword: blocker}（同セットの登録先例 dm32-002・
dm32-072 と同文・同形）の追加〕と、第372弾の確立形
CIP 誘発〔trigger {event: move, to: bz,
subject: self} → modify {select: {zone: bz,
owner: opp, filter: {types: [creature],
not_types: [evolution]}, count: all},
mod: {power_set: 500}, duration: end_of_turn}〕
1件を足し、unsupported を外したもの。partial の
text は行の公式テキスト全文と一致するため text の
補完はなし。単面カードで未検証の面は無い。
alias は dm32-011hc（登録形の source.aliases）。

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
TARGET = "dm32-011"
ALIAS = "dm32-011hc"
GAP = "set_power"

CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self"},
       "effect": [
           {"op": "modify",
            "select": {"zone": "bz", "owner": "opp",
                       "filter": {"types": ["creature"],
                                  "not_types": ["evolution"]},
                       "count": "all"},
            "mod": {"power_set": 500},
            "duration": "end_of_turn"}]}
EVOLVE_FROM = {"types": ["creature"], "keyword": "blocker"}
FORM = [CIP]
FULL_TEXT = ("ブロッカー\n"
             "進化-自分の「ブロッカー」を持つクリーチャー１体の上に置く。\n"
             "このクリーチャーをバトルゾーンに出した時、そのターン、"
             "バトルゾーンにある相手の進化ではないクリーチャーすべての"
             "パワーは500になる。")


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
    assert ALIAS not in rows             # alias に独自行は元々無い
    fam = [i for i, x in rows.items() if GAP in (x.get("gaps") or [])]
    assert fam == []                     # ファミリーはこの1件だけだった
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["types"] == ["creature", "evolution"]   # 補完: evolution
    assert c["civs"] == ["light"] and c["cost"] == 5
    assert c["power"] == 5500 and c["mana"] == 1
    assert c["races"] == ["アポロニア・ドラゴン"]
    assert c["keywords"] == ["blocker"]
    assert c["evolve_from"] == EVOLVE_FROM           # 補完: 進化元
    assert c["text"] == FULL_TEXT                    # 公式テキスト全文
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1                  # CIP 1件ちょうど
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == [ALIAS]
    d = parse_card(c, TABLES)
    assert CIP in d.abilities
    assert d.evolve_from == EVOLVE_FROM
    # プロト T1116 と abilities / types / evolve_from が完全一致
    proto = proto_card("T1116")
    assert proto["abilities"] == FORM
    assert proto["types"] == c["types"]
    assert proto["evolve_from"] == EVOLVE_FROM
    assert proto["keywords"] == c["keywords"]
