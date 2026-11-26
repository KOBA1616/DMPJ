"""語彙パイロット第386弾の対象カード検証（登録形）。

対象は pure な graveyard_replacement のうち単一条項の1件:
- dm26ex4-cho046 夜露死苦 キャロル
ラウンド421で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 水・火 / コスト3 /
パワー2000 / 種族 アウトレイジ、mana 1、keywords・
abilities ともに無し）に第386弾の確立形〔replace
{when: {event: move, to: graveyard, subject: self},
if: {all: [exists マナ水, exists マナ火]}, instead:
[move {ref: subject} → hand]}〕1能力を足し、
unsupported を外したもの。abilities はこの1件
ちょうど、keywords は無いまま。補完あり: partial の
text は条項の断片（「どこからでも墓地に置かれる時、
かわりに手札に戻す」）だけのため、登録形では text に
行の公式テキスト全文が入っている。

正本判定（ラウンド421）: 新規登録として扱った。
identity 実測で canon_id(dm26ex4-cho046) =
dm26ex4-cho046（対象 id 自身が最新版の正本）で、
同名カードの別刷り dm23ex1-062 は converted の
独立エントリとして登録済みだが、その source.aliases
は [dmex03-029, dmex13-056, dmx14-031,
promoy12-031] の4件で対象 id を含まない（対象は
どの converted エントリからもカバーされていない）。
dm02-046 型の stale（正本が登録済みでその aliases に
当該 id が含まれ行が重複）は本件と異なる。登録形の
source.aliases は validate が identity.aliases_for
から自動付与した5件（dm23ex1-062 を含む）で、
dm23ex1-062 の独立エントリとの id∩aliases 重なりが
生じるが、同種の重なりは既存データに多数ある
（ラウンド415で確認）ほか、AliasDict は ID として
存在する alias を別名解決から除外するため無害。

ファミリーのもう1件 dm25ex2-cho021（悠久を統べる者
フォーエバー・プリンセス）は instead の形が異なり
第1条項も未構築のため対象外。reopen で一緒に外れた
が、submit で unsupported を残したまま差し戻され、
gaps = [graveyard_replacement] を保って rejects に
残っている（本 gap は完全解消しない）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無いことを
第386弾で実測済みで、ラウンド421は通常どおり
submit できた。

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
from tests.test_vocab_pilot386 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dm26ex4-cho046"
OTHER = "dm25ex2-cho021"
GAP = "graveyard_replacement"
NAME = "夜露死苦 キャロル"
ALIASES = ["dm23ex1-062", "dmex03-029", "dmex13-056",
           "dmx14-031", "promoy12-031"]


def _reject_rows():
    rows = {}
    with open(ROOT / "data/cards/raw/rejects.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                rows[r["id"]] = r
    return rows


def test_target_registered_and_family_remains():
    rows = _reject_rows()
    assert TARGET not in rows            # 登録により対象行は解消
    fam = sorted(i for i, x in rows.items() if GAP in (x.get("gaps") or []))
    assert fam == [OTHER]                # もう1件は対象外で残る
    assert find(CONVERTED, TARGET) is not None


def test_other_row_remains_with_gap():
    """対象外の dm25ex2-cho021 は reopen で一緒に外れたが
    差し戻され、gaps と partial（unsupported 含む）を
    保って rejects に残っている。"""
    rows = _reject_rows()
    assert OTHER in rows
    assert rows[OTHER]["gaps"] == [GAP]
    assert rows[OTHER]["reason"] == "vocab"
    p = rows[OTHER]["partial"]
    assert p["keywords"] == ["speed_attacker", "double_breaker"]
    uns = (p.get("source") or {}).get("unsupported") or []
    assert [u["need"] for u in uns] == [GAP]


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"]
    assert c["civs"] == ["water", "fire"]
    assert c["cost"] == 3 and c["power"] == 2000 and c["mana"] == 1
    assert c["races"] == ["アウトレイジ"]
    assert not c.get("keywords")         # keywords は無いまま
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    # 登録形は提出形と完全一致: 確立形 replace 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    # source.aliases は validate が identity から自動付与した5件
    assert (c.get("source") or {}).get("aliases") == ALIASES
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d.abilities == FORM
    # プロト T1149 と abilities・text が完全一致
    proto = proto_card("T1149")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    # 登録先例 dm23ex1-062（同名カードの別刷り・独立
    # エントリ）の abilities とも完全一致する
    prec = find(CONVERTED, "dm23ex1-062")
    assert prec is not None
    assert prec["abilities"] == FORM
