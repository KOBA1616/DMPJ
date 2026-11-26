"""語彙パイロット第387弾の対象カード検証（登録形）。

対象は pure な attack_count_this_turn の全1件:
- dm25ex3-rp4s04 楽蛇の虚 フミガルド
ラウンド422で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 火 / コスト5 / パワー6000 /
デーモン・コマンド、mana 1、keywords [speed_attacker,
double_breaker]、abilities [declare, replace] は
構築済み）に、第387弾の確立形〔static {zone: hand,
affects: self, mod: {cost: {amount: -2, count:
{turn_count: {kind: attack, owner: any,
distinct: true}}}, cost_min: 1}}〕を条項順の先頭に
1件足し、unsupported を外したもの。abilities は
[static, declare, replace] の3件ちょうど。補完なし:
text は公式テキスト全文のまま。alias は3件
（dm25ex3-rp4sec05 / dm25rp4-s04 / dm25rp4-sec05。
いずれも自前の reject 行は無い）で、登録形の
source.aliases に入っている。

公式セマンティクス: 第1条項の「このターン攻撃した
クリーチャー1体につき」は体数読み（公式QA 47928。
同一クリーチャーの再攻撃は1体）。turn_count
{kind: attack} の既定（攻撃宣言の回数）では
表せないため distinct: true を追加したのが本弾。
turn_count の distinct を使う初の登録カード。

よく似た別 gap の attack_count_this_turn_condition
（dm25ex3-014）は別ファミリーで、本ラウンドでも
対象外のまま rejects に残っている。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (keywords, text, []) を返し
part[2] の定型所有は空＝ブロッカー無し（第387弾で実測）。

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
from tests.test_vocab_pilot387 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dm25ex3-rp4s04"
GAP = "attack_count_this_turn"
NAME = "楽蛇の虚 フミガルド"
ALIASES = ["dm25ex3-rp4sec05", "dm25rp4-s04", "dm25rp4-sec05"]


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
    for a in ALIASES:                    # alias に自前の reject 行は無い
        assert a not in rows
    # 類似 gap の別ファミリーは混同されず残っている
    assert rows["dm25ex3-014"]["gaps"] == ["attack_count_this_turn_condition"]


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 5 and c["power"] == 6000 and c["mana"] == 1
    assert c["races"] == ["デーモン・コマンド"]
    assert c["keywords"] == ["speed_attacker", "double_breaker"]
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完なし）
    # 登録形は提出形と完全一致: 確立形3能力ちょうど（条項順）
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 3
    assert not c.get("aliases")
    # alias 3件は source.aliases に入っている
    assert (c.get("source") or {}).get("aliases") == ALIASES
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 5   # 3能力＋キーワード2件の展開
    # プロト T1150 と abilities・text が完全一致
    proto = proto_card("T1150")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
