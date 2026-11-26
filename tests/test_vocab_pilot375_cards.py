"""語彙パイロット第375弾の対象カード検証（登録形）。

対象は pure な metamorph の全1件:
- dm14-018 サルベージ・クラスター
ラウンド410で登録済み。登録形は提出形と完全一致:
partial の組立て済み部分（keywords [unblockable] と
破壊置換〔replace {when: {event: move, from: bz,
to: graveyard, reason: destroy, subject: self},
instead: [move {ref: self} to hand]}〕）に第375弾の
確立形の条件 if {cmp: [{count: {zone: mana, owner:
you}}, ">=", 7]}（登録先例 dm14-024 の static if と
同形のイディオム）を足し、unsupported を外したもの。
abilities は条件つき置換1件ちょうど（無条件形の
混入なし）。partial の text は行の公式テキスト全文と
一致するため補完なし。単面カードで未検証の面は無い。
alias は無い。

第375弾で見つかった登録ブロッカー（agent_convert の
submit は rule_convert.split の結果を merge_split で
先頭に戻し、完全一致でしか dedupe しないため、split が
無条件形で所有する破壊置換と条件つき置換が二重に付く）
は、変換ツール改修ステージ（コミット 964746b、(a) split
にメタモーフ条件を伝える改修）で解消済み。ラウンド410の
submit 前には split/merge の実測で merge 結果が条件つき
置換1件ちょうどになることを目視で確認した。

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
TARGET = "dm14-018"
GAP = "metamorph"

UNCONDITIONAL = {"kind": "replace",
                 "when": {"event": "move", "from": "bz", "to": "graveyard",
                          "reason": "destroy", "subject": "self"},
                 "instead": [{"op": "move", "select": {"ref": "self"},
                              "to": "hand", "reason": "return"}]}
REPLACE = dict(UNCONDITIONAL,
               **{"if": {"cmp": [{"count": {"zone": "mana", "owner": "you"}},
                                 ">=", 7]}})
FORM = [REPLACE]
FULL_TEXT = ("このクリーチャーは、ブロックされない。\n"
             "メタモーフ(自分のマナゾーンに７枚以上カードがあれば、"
             "このクリーチャーは次の能力を得る)\n"
             "このクリーチャーが破壊される時、墓地に置くかわりに"
             "自分の手札に戻す。")


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
    assert c["keywords"] == ["unblockable"]
    assert c["types"] == ["creature"] and c["civs"] == ["water"]
    assert c["cost"] == 5 and c["power"] == 3000
    assert c["races"] == ["サイバー・クラスター"]
    assert c["mana"] == 1
    assert c["text"] == FULL_TEXT                      # 公式テキスト全文
    # 登録形は提出形と完全一致: 条件つき置換1件ちょうど、
    # 無条件形（split の定型が所有していた形）の混入なし
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert UNCONDITIONAL not in c["abilities"]
    assert not c.get("aliases")                        # alias は無い
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert REPLACE in d.abilities
    # プロト T1123 と abilities・keywords が完全一致
    proto = proto_card("T1123")
    assert proto["abilities"] == FORM
    assert proto["keywords"] == ["unblockable"]
