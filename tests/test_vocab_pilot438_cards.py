"""語彙パイロット第438弾（cards 側）: revolution_2 —
ラウンド472で登録済み（対象1件のみ）。

対象は dmex06-033 革命目 ギョギョウ（pure 2件の
うち1件）。提出形は partial（骨格〔クリーチャー/進化 /
自然 / コスト6 / パワー8000 / 種族 ジュラシック・
コマンド・ドラゴン/革命軍、mana 1、evolve_from
{types: [creature], civs: [nature]}〕＋
keywords [double_breaker]、text は公式全文）に
第438弾の確立形 abilities 2件〔partial 構築済みの
監視誘発 trigger＋革命２の static {affects: self,
zone: hand, if: {cmp: [{count: {zone: shield,
owner: you}}, "<=", 2]}, mod: {cost: -5}}〕を
足し、unsupported を外したもの。**補完あり:
abilities**（革命２の static 1件のみ未構築）。
革命２の形は登録済み dmex03-s08（同条件・同
軽減幅）/ dmd27-008（同条件）と self 形の
dmex10-s03 / dmex15-a015 の組み合わせ＝ドリフト。
登録形は提出形と完全一致〔source 以外の全フィールドを
照合〕、abilities は2件ちょうど、keywords は
[double_breaker] のまま、evolve_from も保持。

alias は dmr19-009 の1件（rejects に独自行なし。
identity 実測で canon は両方向とも dmex06-033、
登録エントリの source.aliases に validate が
[dmr19-009] を自動付与）。もう1件のファミリー行
dm26sd1-o004 理想と平和の決断は呪文で形が異なる
ため残置: ラウンド472の reopen は両行を取り出し、
dm26sd1-o004 は差し戻して rejects に残る
（ファミリーは完全解消しない）。差し戻しの経緯:
submit の原文照合（load_rows の canonical_rows）が
同名カードの正本行だけを通すため、非正本行の
dm26sd1-o004 は submit 経由で戻せず、元の行を
そのまま rejects に復元した（行全体が HEAD と
完全一致することをラウンド472で照合済み）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import copy
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.cards.identity import aliases_for, canon_id  # noqa: E402
from tests._conv_cache import PROTO, find, proto_card  # noqa: E402
from tests.test_vocab_pilot438 import FORM, FULL_TEXT, TRIG  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
TARGET = "dmex06-033"
ALIAS = "dmr19-009"
OTHER = "dm26sd1-o004"
GAP = "revolution_2"
NAME = "革命目 ギョギョウ"

SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature", "evolution"],
    "civs": ["nature"],
    "cost": 6,
    "power": 8000,
    "races": ["ジュラシック・コマンド・ドラゴン", "革命軍"],
    "mana": 1,
    "text": FULL_TEXT,
    "keywords": ["double_breaker"],
    "evolve_from": {"types": ["creature"], "civs": ["nature"]},
    "abilities": FORM,
}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_registered_and_family_not_cleared():
    rows = _reject_rows()
    mine = {r["id"]: r for r in rows}
    assert TARGET not in mine            # 対象行は登録で解消
    # ファミリーは pure 2件のうち呪文の1件が残る（完全解消しない）
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == [OTHER]
    # 差し戻された行は gaps / partial を保ったまま残る
    other = mine[OTHER]
    assert other["gaps"] == [GAP]
    assert other["reason"] == "vocab"
    needs = [u["need"] for u in
             (other["partial"].get("source") or {}).get("unsupported")
             or []]
    assert needs == [GAP]
    assert other["partial"]["types"] == ["spell"]
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 2      # abilities は2件ちょうど
    assert c["abilities"][0] == TRIG     # partial 構築済みの監視誘発
    assert c["abilities"][1] == FORM[1]  # 革命２の static
    assert c["text"] == FULL_TEXT        # 公式全文
    assert c["keywords"] == ["double_breaker"]
    assert c["evolve_from"] == {"types": ["creature"],
                                "civs": ["nature"]}
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == [ALIAS]
    # alias 自身は独立エントリにならない（source.aliases のみ）
    assert find(CONVERTED, ALIAS) is None
    # 正本は対象自身・alias は dmr19-009 の1件
    assert canon_id(TARGET) == TARGET
    assert canon_id(ALIAS) == TARGET
    assert aliases_for(NAME, TARGET) == [ALIAS]
    # 判断待ちの stale 行には触っていない
    assert mine["dm02-046"]["gaps"] == [
        "destroy_self_after_attacking_player"]


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.types == ["creature", "evolution"]
    assert d.cost == 6 and d.power == 8000
    assert find(str(PROTO), TARGET) is None
    proto = proto_card("T1228")
    for k in ("name", "types", "civs", "cost", "power",
              "races", "mana", "text", "abilities", "keywords",
              "evolve_from"):
        assert proto[k] == SUBMIT[k], k


def test_official_row_consistency():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/ex06.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    off = next(r for r in rows if r["id"] == TARGET)
    assert off["name"] == NAME
    assert off["text"] == FULL_TEXT
    assert int(off["cost"]) == 6 and int(off["power"]) == 8000
    assert off["race"] == "ジュラシック・コマンド・ドラゴン/革命軍"
