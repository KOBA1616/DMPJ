"""語彙パイロット第436弾（cards 側）: mana_tap_trigger —
ラウンド470で登録済み。

対象は dmx08-010 大喰の超人（pure 1件、multi にも
現れない）。提出形は partial そのもの（骨格
〔クリーチャー / 自然 / コスト8 / パワー8000 / 種族
ジャイアント/ハンター、mana 1〕＋abilities 2件
〔static mana_boost {values: [2, 3]}（第212弾・
ラウンド248の確立形）と trigger {when: {event: tap,
subject: {owner: you, zone: mana}}, effect: [move
{select: {ref: subject}, to: graveyard, reason: put}]}〕
から unsupported を外したもの。**補完なし**（text は
partial の時点で公式全文）。第436弾で支払い・コストの
マナタップ6か所をイベント化し、_match_when に
tap/untap の subject ゾーン既定規則を追加した
（新規語彙＝エンジン変更、defs・スキーマ変更なし）。
登録形は提出形と完全一致〔source 以外の全フィールドを
照合〕、abilities は static＋trigger の2件ちょうど、
text は公式全文。

alias は無し（identity 実測で canon_id は対象自身、
aliases_for = []）。登録ブロッカーの確認（第375弾の
教訓）: rule_convert.split（対象行）は
(['double_breaker'], 残り原文, []) を返し、定型所有は
キーワード double_breaker のみで partial の keywords
と一致（欠落なし。第465弾の作法どおり提出形の
keywords をそのまま使った）、定型所有の ability は
無い。対象行は gaps=[mana_tap_trigger]・
reason == "vocab" のため、ラウンド470の reopen の
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
from tests.test_vocab_pilot436 import FORM, FULL_TEXT  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
TARGET = "dmx08-010"
GAP = "mana_tap_trigger"
NAME = "大喰の超人"

SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["nature"],
    "cost": 8,
    "power": 8000,
    "races": ["ジャイアント", "ハンター"],
    "mana": 1,
    "text": FULL_TEXT,
    "keywords": ["double_breaker"],
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
    assert len(c["abilities"]) == 2      # abilities は static＋trigger の2件ちょうど
    assert [a["kind"] for a in c["abilities"]] == ["static", "trigger"]
    assert c["abilities"][0] == {"kind": "static",
                                 "mana_boost": {"values": [2, 3]}}
    assert c["abilities"][1]["when"] == {
        "event": "tap", "subject": {"owner": "you", "zone": "mana"}}
    assert c["text"] == FULL_TEXT        # 公式全文
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
    assert d.cost == 8 and d.power == 8000
    assert find(str(PROTO), TARGET) is None
    proto = proto_card("T1226")
    for k in ("name", "types", "civs", "cost", "power",
              "races", "mana", "text", "abilities", "keywords"):
        assert proto[k] == SUBMIT[k], k


def test_official_row_consistency():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/x08.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    off = next(r for r in rows if r["id"] == TARGET)
    assert off["name"] == NAME
    assert off["text"] == FULL_TEXT
