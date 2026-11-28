"""語彙パイロット第414弾の対象カード検証（登録形）。

対象は chosen_creature_can_be_attacked_while_untapped
（pure 1件、multi にも現れない）:
- dm01-034 カオス・ストライク
ラウンド449で登録済み。登録形は提出形と完全一致:
partial の骨格（呪文 / 火 / コスト2、mana 1）に
第414弾の確立形 spell 2 op〔choose {select:
{zone: bz, owner: opp, filter: {types: [creature]},
count: 1}, as: tgt} / modify {select: {zone: bz,
owner: you, filter: {types: [creature]}, count: all},
mod: {allow: [{action: attack_creature,
other: {tapped: false}, only: {var: tgt}}]},
duration: end_of_turn}〕を足し、unsupported を
外したもの。spell はこの2 op ちょうど。登録済み
dmr09-102 戦場のロックンロール（第275弾、同じく
火・コスト2の呪文）の登録形と同型で、差は選択
フィルタに tapped: false が無いことだけ（本件は
タップ状態を問わず選べる）。
**補完なし**（partial の text は行の公式テキスト
全文と内容が一致し、文間の改行だけが欠ける。提出形の
text は行の公式テキストをそのまま使い、登録後の
全文一致〔改行を含む〕も照合済み）。

alias は無し（公式データで カオス・ストライク の
収録は dm01-034 のみ。identity 実測で canon_id は
対象自身、aliases_for = [] のため登録エントリに
source.aliases は付かない）。
chosen_creature_can_be_attacked_while_untapped は
完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し、定型所有は無い
＝ツール側ブロッカーなし。ラウンド449の登録で、
登録後の spell は 2 op ちょうどで allow 項目の
only {var: tgt} が保持されていることを実測確認済み。

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
from tests.test_vocab_pilot414 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dm01-034"
GAP = "chosen_creature_can_be_attacked_while_untapped"
NAME = "カオス・ストライク"

# 提出形: partial の骨格＋確立形 spell（補完なし）
SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["spell"],
    "civs": ["fire"],
    "cost": 2,
    "mana": 1,
    "text": FULL_TEXT,
    "spell": FORM,
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
    assert len(rows) <= 1917  # 件数は減る一方（スナップショット固定をやめた）
    assert TARGET not in rows            # 登録により対象行は解消
    fam = sorted(i for i, x in rows.items()
                 if GAP in (x.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert identity.canon_id(TARGET) == TARGET
    assert identity.aliases_for(NAME, TARGET) == []
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["spell"] and c["civs"] == ["fire"]
    assert c["cost"] == 2 and c["mana"] == 1
    assert c["text"] == FULL_TEXT        # 公式全文（改行あり、補完なし）
    # 登録形は提出形と完全一致: spell は 2 op ちょうど
    assert c["spell"] == FORM
    assert len(c["spell"]) == 2
    assert [op["op"] for op in c["spell"]] == ["choose", "modify"]
    # allow 項目の only {var: tgt} が保持されている
    assert c["spell"][1]["mod"]["allow"][0]["only"] == {"var": "tgt"}
    # 選択フィルタに tapped: false は無い（第275弾形との差）
    assert "tapped" not in c["spell"][0]["select"]["filter"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無しのため付かない
    d = parse_card(c, TABLES)
    assert [op["op"] for op in d.spell] == ["choose", "modify"]
    assert d.spell[1]["mod"]["allow"][0]["only"] == {"var": "tgt"}
    # プロト T1182 と spell・text・骨格が完全一致
    proto = proto_card("T1182")
    assert proto["spell"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "mana"):
        assert proto[k] == SUBMIT[k]
