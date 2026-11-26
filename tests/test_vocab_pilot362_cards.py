"""語彙パイロット第362弾の対象カード（登録形の検証）。

対象は pure な entry_turn_attack_restriction の全1件で、
ラウンド397で登録:
- dm23bd6-003 アカシック・B / 「バブルの泡に溺れるのヨ！」
（ツインパクト。partial はクリーチャー面の骨格
〔能力なし〕で、未解決は unsupported の本 gap 1件だけ
だった。提出形は partial の骨格に第362弾の確立形
1能力を足したクリーチャー面＋ラウンド397で検証した
呪文面。登録形は提出形と完全一致）

呪文面（コスト7・水・S・トリガー「相手1人につき、
その相手のクリーチャーを1体選んで手札に戻し、
カードを1枚引いてもよい」）は partial に無く、
ラウンド397で既存語彙で正確に表せることを確認した:
面キーワード s_trigger（先例 dm23rp3-048 の呪文面）、
bounce {zone: bz, owner: opp, filter: {types:
[creature]}, count: 1}（dm23rp4x-058 の効果と同形）、
may {body: [draw 1]}（「引いてもよい」はドローのみ
に係り、戻しは may の外の必須選択）、「相手1人
につき」は2人戦前提で1回分とする登録慣行
（dm23bd5-007 / dm23bd7-005 の notes）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import find, proto_card  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
TARGET = "dm23bd6-003"

FORM = [{"kind": "static",
         "affects": {"zone": "bz", "owner": "opp",
                     "filter": {"types": ["creature"],
                                "entered_this_turn": True}},
         "mod": {"deny": ["attack_player", "attack_creature"]}}]

SPELL_FORM = [{"op": "bounce",
               "select": {"zone": "bz", "owner": "opp",
                          "filter": {"types": ["creature"]},
                          "count": 1}},
              {"op": "may", "body": [{"op": "draw", "count": 1}]}]


def test_target_registered():
    c = find(CONVERTED, TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert not c.get("aliases")          # alias 畳み込み0件
    f0, f1 = c["faces"]
    # クリーチャー面: 第362弾の確立形1能力ちょうど
    assert f0["name"] == "アカシック・B"
    assert f0["abilities"] == FORM
    assert len(f0["abilities"]) == 1
    assert not f0.get("keywords")
    assert f0["types"] == ["creature"] and f0["civs"] == ["water"]
    assert f0["cost"] == 3 and f0["power"] == 3000
    assert f0["races"] == ["マジック・コマンド", "マーメイド"]
    # 呪文面: ラウンド397の検証形
    assert f1["name"] == "「バブルの泡に溺れるのヨ！」"
    assert f1["types"] == ["spell"] and f1["civs"] == ["water"]
    assert f1["cost"] == 7
    assert f1["keywords"] == ["s_trigger"]
    assert f1["spell"] == SPELL_FORM
    d = parse_card(c, TABLES)
    assert [f.name for f in d.faces] == ["アカシック・B",
                                         "「バブルの泡に溺れるのヨ！」"]
    assert FORM[0] in d.faces[0].abilities


def test_proto_form_matches():
    assert proto_card("T1089")["abilities"] == FORM
