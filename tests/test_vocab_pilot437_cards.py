"""語彙パイロット第437弾（cards 側）: shield_faceup_trigger —
ラウンド471で登録済み。

対象は dmd11-006 大焔団 フォルクス（pure 1件、multi にも
現れない）。提出形は partial（骨格〔クリーチャー / 火 /
コスト7 / パワー7000 / 種族 アウトレイジMAX、mana 1〕＋
keywords [speed_attacker, double_breaker]、text は公式
全文）に第437弾の確立形 ability 1件〔trigger
{when: {event: move, from: shield, reason: break,
subject: {owner: you}, face_up: true}, effect:
[destroy {select: {zone: bz, owner: opp, filter:
{types: [creature], power_le: 6000}, count: 1}}]}〕を
足し、unsupported を外したもの。**補完あり: abilities**
（partial に未構築）。シールド離脱の監視は登録済み
dm23rp3-017 等の確立形、表向きの照合は第176弾で
move レコードに載る face_up を when で見る形、
ブレイクの区別は h_break が付ける reason: break。
登録形は提出形と完全一致〔source 以外の全フィールドを
照合〕、abilities は trigger 1件ちょうど、text は公式全文。

alias は無し（identity 実測で canon_id は対象自身、
aliases_for = []）。登録ブロッカーの確認（第375弾の
教訓）: rule_convert.split（対象行）は
(['speed_attacker', 'double_breaker'], 残り原文, []) を
返し、定型所有はキーワード2件のみで partial の
keywords と完全一致（欠落なし）、定型所有の ability は
無い。対象行は gaps=[shield_faceup_trigger]・
reason == "vocab" のため、ラウンド471の reopen の
出力は対象1件ちょうどだった。

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
from tests.test_vocab_pilot437 import FORM, FULL_TEXT  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
TARGET = "dmd11-006"
GAP = "shield_faceup_trigger"
NAME = "大焔団 フォルクス"

SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 7,
    "power": 7000,
    "races": ["アウトレイジMAX"],
    "mana": 1,
    "text": FULL_TEXT,
    "keywords": ["speed_attacker", "double_breaker"],
    "abilities": FORM,
}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_registered_and_family_cleared():
    rows = _reject_rows()
    mine = {r["id"]: r for r in rows}
    assert TARGET not in mine            # 対象行は登録で解消
    # ファミリーは pure 1件のみで完全解消
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == []
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 1      # abilities は trigger 1件ちょうど
    assert c["abilities"][0]["kind"] == "trigger"
    assert c["abilities"][0]["when"] == {
        "event": "move", "from": "shield", "reason": "break",
        "subject": {"owner": "you"}, "face_up": True}
    assert c["text"] == FULL_TEXT        # 公式全文
    assert c["keywords"] == ["speed_attacker", "double_breaker"]
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し
    # 正本は対象自身・alias 無し
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []
    # 判断待ちの stale 行には触っていない
    assert mine["dm02-046"]["gaps"] == [
        "destroy_self_after_attacking_player"]


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.types == ["creature"]
    assert d.cost == 7 and d.power == 7000
    assert find(str(PROTO), TARGET) is None
    proto = proto_card("T1227")
    for k in ("name", "types", "civs", "cost", "power",
              "races", "mana", "text", "abilities", "keywords"):
        assert proto[k] == SUBMIT[k], k


def test_official_row_consistency():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/d11.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    off = next(r for r in rows if r["id"] == TARGET)
    assert off["name"] == NAME
    assert off["text"] == FULL_TEXT
    assert int(off["cost"]) == 7 and int(off["power"]) == 7000
    assert off["race"] == "アウトレイジMAX"
