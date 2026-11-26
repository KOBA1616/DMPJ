"""語彙パイロット第370弾の対象カード検証（登録形）。

対象は pure な set_power_to_zero の全1件:
- dm24ex2-042 騎士のコード オルタナティブ
ラウンド405で登録済み。登録形は提出形と完全一致:
partial（水晶ソウル2（crystal_soul: 2、第154弾で
宣言化）、keywords [double_breaker]、破壊時誘発1件が
組立て済み）に第370弾の確立形 CIP 誘発〔trigger
{event: move, to: bz, subject: self} → choose
{owner: opp, as: victim} / modify {power_set: 0,
duration: end_of_turn}（dmrp11-zs01 の登録先例と
同形）〕を abilities の先頭に足し、unsupported を
外したもの。abilities は公式テキストの条項順に
[CIP, 破壊時] の2件ちょうど。partial の text は行の
公式テキスト全文と一致するため補完なし。civs は
partial の骨格どおり [] のまま（proto T1113 の
civs [zero] はフィクスチャ側の表記）。単面カードで
未検証の面は無い。alias は無い。

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
TARGET = "dm24ex2-042"
GAP = "set_power_to_zero"

CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self"},
       "effect": [
           {"op": "choose",
            "select": {"zone": "bz", "owner": "opp",
                       "filter": {"types": ["creature"]}, "count": 1},
            "as": "victim"},
           {"op": "modify",
            "select": {"ref": "victim"},
            "mod": {"power_set": 0},
            "duration": "end_of_turn"}]}
DESTROYED = {"kind": "trigger",
             "when": {"event": "move", "from": "bz",
                      "to": "graveyard", "reason": "destroy",
                      "subject": "self"},
             "effect": [
                 {"op": "may",
                  "body": [
                      {"op": "play_free",
                       "select": {"zone": "hand", "owner": "you",
                                  "filter": {"types": ["creature"],
                                             "colorless": True,
                                             "race_has": "ゼニス"},
                                  "count": 1}}]}]}
FORM = [CIP, DESTROYED]
FULL_TEXT = ("水晶ソウル２（このクリーチャーを召喚する時、自分のマナゾーンにある"
             "裏向きのカードのマナの数字は２になる）\n"
             "W・ブレイカー\n"
             "このクリーチャーが出た時、相手のクリーチャーを１体選ぶ。このターン、"
             "そのクリーチャーのパワーを０にする。（パワー０以下のクリーチャーは破壊される）\n"
             "このクリーチャーが破壊された時、無色ゼニス・クリーチャーを１体、"
             "自分の手札からコストを支払わずに召喚してもよい。")


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
    assert c["types"] == ["creature"] and c["civs"] == []
    assert c["cost"] == 7 and c["power"] == 6543
    assert c["races"] == ["アンノウン・セレス"] and c["mana"] == 1
    assert c["crystal_soul"] == 2
    assert c["keywords"] == ["double_breaker"]
    assert c["text"] == FULL_TEXT       # 公式テキスト全文（補完なし）
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2      # [CIP, 破壊時] の2件ちょうど
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert CIP in d.abilities and DESTROYED in d.abilities
    # プロト T1113 と abilities が完全一致
    proto = proto_card("T1113")
    assert proto["abilities"] == FORM
