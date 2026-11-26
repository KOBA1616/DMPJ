"""語彙パイロット第430弾（cards 側）:
infinity_power_attacker — ラウンド465で登録済み。

対象は dmr09-v02 武闘将軍 カツキング（pure 1件、
multi にも現れない）。提出形は partial の骨格＋
構築済み条項に第430弾の検証を反映したもの:
(1) keywords に infinite_power_attacker を追加
（唯一の unsupported。第272弾の確立キーワード）、
(2) types に exile_creature を追加（partial は
[creature] のみ。公式 card_type はエグザイル・
クリーチャー）、(3) ドロン・ゴー誘発と deny
静的効果5件の filter を partial の races
[アウトレイジMAX] 代理から登録先例 dmd11-001 /
dmd11-005 の {name_has: 武闘, types:
[exile_creature]} へ修正（代理は同値でないことを
公式コーパスで実測: アウトレイジMAX 種族 280件中
エグザイルは 84件のみ。《武闘》名でも熱血武闘
カツキング等の非エグザイルが代理に一致する）、
(4) deny 5件にチーム・エグザイル無視の if を追加
（登録先例2件とも保持。partial は欠落）。
alias は無し。登録形は提出形と完全一致〔source
以外の全フィールドを照合〕、abilities は8件
ちょうど、types [creature, exile_creature]、
keywords 3件。形の根拠は本体テストの docstring
参照。

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
from tests.test_vocab_pilot430 import ABILITIES, FORM, FULL_TEXT, NAME  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
TARGET = "dmr09-v02"
GAP = "infinity_power_attacker"

SUBMIT = {"id": TARGET, **copy.deepcopy(FORM)}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_registered_and_family_cleared():
    rows = _reject_rows()
    mine = {r["id"]: r for r in rows}
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert TARGET not in mine            # 対象行は登録で解消
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 8      # abilities 8件ちょうど
    assert c["types"] == ["creature", "exile_creature"]
    assert c["keywords"] == ["speed_attacker", "double_breaker",
                             "infinite_power_attacker"]
    assert c["text"] == FULL_TEXT        # 公式全文
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し
    # フィルタはすべて types 側（races 代理は残っていない）
    dg = c["abilities"][2]
    assert dg["effect"][0]["body"][0]["select"]["filter"] == \
        {"name_has": "武闘", "types": ["exile_creature"]}
    for ab in c["abilities"][3:]:
        assert ab["affects"]["filter"] == \
            {"name_has": "武闘", "types": ["exile_creature"]}
        assert "if" in ab
    # 正本は対象自身・alias 無し
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []
    # 判断待ちの stale 行には触っていない
    assert mine["dm02-046"]["gaps"] == [
        "destroy_self_after_attacking_player"]


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.types == ["creature", "exile_creature"]
    assert d.cost == 8 and d.power == 11000
    proto = proto_card("T1209")
    for k in ("name", "types", "civs", "cost", "power",
              "races", "mana", "text", "keywords", "abilities"):
        assert proto[k] == SUBMIT[k], k
    assert len(proto["abilities"]) == 8


def test_official_row_matches_skeleton_and_text():
    off = None
    for line in (ROOT / "data/cards/raw/by_product/r09.jsonl") \
            .read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("id") == TARGET:
            off = r
    assert off is not None
    assert off["name"] == NAME
    assert off["text"] == FULL_TEXT
    assert int(off["cost"]) == 8
    assert int(off["power"]) == 11000
    assert off["race"] == "アウトレイジMAX"
    assert off["civilization"] == "火"
    assert off["card_type"] == "エグザイル・クリーチャー"
