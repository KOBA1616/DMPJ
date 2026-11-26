"""語彙パイロット第379弾の対象カード検証（登録形）。

対象は pure な deck_rule の全1件:
- dmx22b-110 素晴らしい犬 ワンワンワン
ラウンド414で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 自然 / コスト2 /
パワー1111 / 種族 アウトレイジ犬、mana 1、keywords・
abilities ともに無し）に第379弾の確立形 static
〔power {amount: 1111, count: {zone: bz, owner: you,
filter: {races: [アウトレイジ犬]}, other: true}}〕
1能力を足し、unsupported を外したもの。abilities は
この1件ちょうど、keywords は無いまま。**補完あり:
partial の text はデッキ条項の断片のみのため、提出形
では text に行の公式テキスト全文を入れた**（ラウンド
411・403・406の作法）。デッキ条項自体は登録先例
dmex13-057 と同じく text のみで保持し能力化しない。
alias は dmx22b-111（rejects に独自行は無く、登録形の
source.aliases に入っている）。単面カードで未検証の
面は無い。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無いことを
第379弾で実測済みで、ラウンド414は通常どおり submit
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
TARGET = "dmx22b-110"
GAP = "deck_rule"
ALIASES = ["dmx22b-111"]

STATIC = {"kind": "static", "affects": "self",
          "mod": {"power": {"amount": 1111,
                            "count": {"zone": "bz", "owner": "you",
                                      "filter": {"races": ["アウトレイジ犬"]},
                                      "other": True}}}}
FORM = [STATIC]
FULL_TEXT = ("{Dog Souls}《素晴らしい犬 ワンワンワン》は、"
             "４枚より多くデッキに入れることができる。"
             "バトルゾーンにある自分の他のアウトレイジ犬１匹につき、"
             "このクリーチャーのパワーを+1111する。")


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
    # alias に rejects の独自行は無い
    for a in ALIASES:
        assert a not in rows


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["types"] == ["creature"]
    assert c["civs"] == ["nature"]
    assert c["cost"] == 2 and c["power"] == 1111
    assert c["races"] == ["アウトレイジ犬"]
    assert c["mana"] == 1
    assert not c.get("keywords")         # キーワードは無いまま
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    # 登録形は提出形と完全一致: 確立形1能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    # alias は source.aliases に入っている
    assert (c.get("source") or {}).get("aliases") == ALIASES
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities
    assert d.types == ["creature"] and d.civs == ["nature"]
    assert d.cost == 2 and d.power == 1111
    assert d.races == ["アウトレイジ犬"]
    # プロト T1131 と abilities・text が完全一致
    proto = proto_card("T1131")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
