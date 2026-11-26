"""語彙パイロット第399弾の対象カード検証（登録形）。

対象は pure な summon_turn_attack_restriction の全1件:
- dmr22-s04 聖者の精霊龍 セレナーデ
ラウンド434で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 光・水 / コスト7 /
パワー7500 / 種族 エンジェル・コマンド・ドラゴン /
革命軍、mana 1）に keywords [blocker,
double_breaker] と第399弾の確立形 static〔affects
{zone: bz, owner: any, filter: {types: [creature],
keyword: speed_attacker, entered_this_turn: true}},
mod: {deny: [attack_player, attack_creature]}〕を
足し、unsupported を外したもの。abilities はこの
1件ちょうど、keywords は [blocker, double_breaker]。
**補完あり: text のみ**（partial の text は条項の
断片のため、text には行の公式テキスト全文を条項
ごとに改行したもの）。「マナゾーンに置く時、この
カードはタップして置く」は多色カードのルール
（405.1、エンジンが civs 2つ以上をマナに置く時に
タップさせる）で text のみ。alias は無い（identity
実測で canon_id は対象自身、aliases_for = []）。
確立形は第398弾と同一（第362弾の登録先例の owner を
any に広げ keyword フィルタを足した形）。既知の
制限: 静的効果の affects 照合は base（印刷特性）の
ため、付与されたスピードアタッカーはフィルタに
掛からない（エンジン全体の規約。第399弾本体テスト
で固定）。ファミリーは完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い
（第399弾で実測）。

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
from tests.test_vocab_pilot399 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmr22-s04"
GAP = "summon_turn_attack_restriction"
NAME = "聖者の精霊龍 セレナーデ"


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
    assert fam == []                     # ファミリーは完全解消
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["light", "water"]
    assert c["cost"] == 7 and c["power"] == 7500 and c["mana"] == 1
    assert c["races"] == ["エンジェル・コマンド・ドラゴン", "革命軍"]
    assert c["keywords"] == ["blocker", "double_breaker"]
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり: text のみ）
    # 登録形は提出形と完全一致: 確立形1能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("aliases")        # alias は無い
    assert not src.get("unsupported")
    d = parse_card(c, TABLES)
    own = [a for a in d.abilities if not a.get("keyword")]
    assert own == FORM                   # キーワード展開分を除き確立形1件ちょうど
    # プロト T1166 と abilities・text・骨格が完全一致
    proto = proto_card("T1166")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power", "races", "mana"):
        assert proto[k] == c[k]
    assert proto["keywords"] == c["keywords"]
