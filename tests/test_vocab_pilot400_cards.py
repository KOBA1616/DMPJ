"""語彙パイロット第400弾の対象カード検証（登録形）。

対象は untap_restriction（pure 3件）のうち形が
確定する1件:
- dmrp21-t14 ブルース・ガー
ラウンド435で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 火 / コスト1 /
パワー1000 / 種族 ファイアー・バード、mana 1、
keywords・abilities ともに無し）に第400弾の
確立形 static {affects: self, mod: {deny:
[untap_at_start]}} の1能力を足し、unsupported を
外したもの。abilities はこの1件ちょうど、
keywords は無いまま。**補完あり: races と text
のみ**（【K・ソウル】は種族特性で、登録先例
dmex01-043 / dm36-032 と同様に races へ
'K・ソウル' を入れる。partial の races は
[ファイアー・バード] のみ。text には公式テキスト
全文を入れる。partial の text は断片
「アンタップしない」）。alias は dm38-029 /
dmrp21-tf14 の2件で、いずれも rejects に独自行は
無く、登録エントリの source.aliases は validate が
identity.aliases_for から自動付与した2件。
残り2件（dm26rp1-td004 / dmx15-011）は形が異なる
ため対象外で、ラウンド435の reopen で巻き込まれた
分を unsupported を残した partial のまま差し戻し
済み。ファミリーは解消しない。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い
（第400弾で実測）。

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
from tests.test_vocab_pilot400 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmrp21-t14"
GAP = "untap_restriction"
NAME = "ブルース・ガー"
REMAINING = ["dm26rp1-td004", "dmx15-011"]


def _reject_rows():
    rows = {}
    with open(ROOT / "data/cards/raw/rejects.jsonl",
              encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                rows[r["id"]] = r
    return rows


def test_target_registered_and_family_remains():
    rows = _reject_rows()
    assert TARGET not in rows            # 登録により対象行は解消
    fam = sorted(i for i, x in rows.items()
                 if GAP in (x.get("gaps") or []))
    assert fam == REMAINING              # 残り2件は別形で残留
    assert find(CONVERTED, TARGET) is not None


def test_bounced_rows_preserved():
    rows = _reject_rows()
    for bid in REMAINING:
        r = rows[bid]
        assert r["reason"] == "vocab"
        assert r["gaps"] == [GAP]
        uns = r["partial"]["source"]["unsupported"]
        assert [u["need"] for u in uns] == [GAP]
    # 差し戻し行の partial は元のまま保持されている
    td = rows["dm26rp1-td004"]["partial"]
    assert td["keywords"] == ["hyper_energy", "double_breaker"]
    assert len(td["abilities"]) == 1
    x15 = rows["dmx15-011"]["partial"]
    assert x15["keywords"] == ["double_breaker"]
    assert not x15.get("abilities")


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 1 and c["power"] == 1000 and c["mana"] == 1
    # 補完あり: races（K・ソウルは種族特性として races へ）
    assert c["races"] == ["ファイアー・バード", "K・ソウル"]
    assert not c.get("keywords")         # キーワードは無いまま
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり: text）
    # 登録形は提出形と完全一致: 確立形1能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert src.get("aliases") == ["dm38-029", "dmrp21-tf14"]
    assert not src.get("unsupported")
    d = parse_card(c, TABLES)
    assert FORM[0] in d.abilities
    # プロト T1167 と abilities・text・骨格が完全一致
    proto = proto_card("T1167")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power",
              "races", "mana"):
        assert proto[k] == c[k]
