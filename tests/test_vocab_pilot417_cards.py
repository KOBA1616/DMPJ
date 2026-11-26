"""語彙パイロット第417弾の対象カード検証（登録形）。

対象は battle_win_destroy（pure 1件、multi にも
現れない）:
- dmr11-051 護神のインガ イヌハッカ
ラウンド452で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 光/闇 / コスト3 /
パワー5500 / 種族 オラクル、mana 1）に第417弾の
確立形を足したもの: free_if {exists: {zone: bz,
owner: you, filter: {race_has: ゴッド}}}（G・ゼロ。
登録済み dm22rp2x-tf14 の条件形と同一）＋
keywords [blocker, cannot_attack_player]
（ブロッカー／相手プレイヤーを攻撃できない。
cannot_attack_player は同一文面の自己制限の標準形で
converted に328件）＋ abilities は trigger
{when: {event: battle_win, subject: self},
effect: [destroy {select: {ref: self}}]} の1件
ちょうど（第413弾の確立形、登録済み dm01-026 と
完全一致）。第1条項「マナゾーンに置く時タップして
置く」は多色ルール（405.1）でエンジン core が
適用済み（第399弾）のため text のみ。
**補完あり: text のみ**（partial の text は断片
「バトルに勝っても破壊される」のため、行の公式
テキスト全文を使った）。

alias は dmr11-051m の1件で rejects に独自行は
無く、identity 実測で canon_id は対象自身
（alias 側の canon も dmr11-051）、aliases_for =
[dmr11-051m]。登録エントリの source.aliases には
validate が自動付与した1件が入る。
battle_win_destroy は完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い
（convert も None）＝ツール側ブロッカーなし。
対象行は gaps=[battle_win_destroy]・reason ==
"vocab" のため reopen の出力は対象1件ちょうど
（ラウンド452で実測確認済み）。

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
from tests.test_vocab_pilot417 import (  # noqa: E402
    FORM, FREE_IF, FULL_TEXT, KEYWORDS, PARSED_TRIG)

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmr11-051"
ALIASES = ["dmr11-051m"]
GAP = "battle_win_destroy"
NAME = "護神のインガ イヌハッカ"

# 提出形: partial の骨格＋確立形（補完は text のみ）
SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["light", "darkness"],
    "cost": 3,
    "power": 5500,
    "races": ["オラクル"],
    "mana": 1,
    "text": FULL_TEXT,
    "keywords": KEYWORDS,
    "free_if": FREE_IF,
    "abilities": FORM,
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
    assert len(rows) == 1914
    assert TARGET not in rows            # 登録により対象行は解消
    fam = sorted(i for i, x in rows.items()
                 if GAP in (x.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    for a in ALIASES:
        assert a not in rows             # alias に独自行なし
        assert identity.canon_id(a) == TARGET
    assert identity.canon_id(TARGET) == TARGET
    assert identity.aliases_for(NAME, TARGET) == ALIASES
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["light", "darkness"]
    assert c["cost"] == 3 and c["power"] == 5500 and c["mana"] == 1
    assert c["races"] == ["オラクル"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完は text のみ）
    # 登録形は提出形と完全一致: abilities は誘発1件ちょうど、
    # keywords はそのまま、free_if は保持される
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert c["keywords"] == KEYWORDS
    assert c["free_if"] == FREE_IF
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ALIASES  # validate の自動付与
    d = parse_card(c, TABLES)
    assert d.free_if == FREE_IF
    assert PARSED_TRIG in d.abilities
    # キーワード由来 static 2件＋誘発1件
    assert len(d.abilities) == 3
    assert d.keywords == KEYWORDS
    # プロト T1186 と abilities・text・keywords・free_if・骨格が完全一致
    proto = proto_card("T1186")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    assert proto["keywords"] == KEYWORDS
    assert proto["free_if"] == FREE_IF
    for k in ("name", "types", "civs", "cost", "power", "races", "mana"):
        assert proto[k] == SUBMIT[k]


def test_official_row_matches_skeleton():
    """骨格と text は公式データ行（by_product/r11.jsonl）と
    一致することを固定する。"""
    with open(ROOT / "data/cards/raw/by_product/r11.jsonl",
              encoding="utf-8") as f:
        official = None
        for line in f:
            if line.strip():
                r = json.loads(line)
                if r["id"] == TARGET:
                    official = r
                    break
    assert official is not None
    assert official["name"] == NAME
    assert official["card_type"] == "クリーチャー"
    assert official["civilization"] == "光/闇"
    assert official["cost"] == "3" and official["power"] == "5500"
    assert official["race"] == "オラクル"
    assert official["mana"] == "1"
    assert official["text"] == FULL_TEXT
