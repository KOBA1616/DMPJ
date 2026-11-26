"""語彙パイロット第433弾（cards 側）:
opponent_mana_trigger — ラウンド468で登録済み。

対象は dm39-015 穿神兵ジェットドリル（pure 1件、
multi にも現れない）。提出形は partial の骨格
（クリーチャー / 火 / コスト3 / パワー2000 / 種族
アーマロイド、mana 1）に第433弾の確立形 ability 1件
〔trigger {when: {event: move, to: mana,
from: [deck, graveyard], subject: {owner: opp}},
effect: [move {select: {zone: mana, owner: opp,
count: 1, chooser: opp}, to: deck, reason: put,
position: bottom}]}〕（to: mana の監視誘発は
第397弾、from のリスト指定は defs の when 検証と
エンジン _match_when の両側で対応済み、chooser: opp
は selector の既存キー、山札の一番下への move は
登録済みニンジャ・ストライク形の確立形）を足した
もの。**補完あり: text（公式全文。partial の text は
断片「相手の山札または墓地から、カードがマナゾーンに
置かれた時」）＋abilities**。登録形は提出形と完全一致
〔source 以外の全フィールドを照合〕、abilities は
trigger 1件ちょうど、text は公式全文。

alias は無し（identity 実測で canon_id は対象自身、
aliases_for = []）。登録ブロッカーの確認（第375弾の
教訓）: rule_convert.split（対象行）は None を返し
定型所有は無い＝ツール側ブロッカーなし。対象行は
gaps=[opponent_mana_trigger]・reason == "vocab" の
ため、ラウンド468の reopen の出力は対象1件ちょうど
だった。

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
from tests.test_vocab_pilot433 import FORM, FULL_TEXT  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
TARGET = "dm39-015"
GAP = "opponent_mana_trigger"
NAME = "穿神兵ジェットドリル"

# 提出形: partial の骨格＋text 公式全文＋確立形 trigger 1件
SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 3,
    "power": 2000,
    "races": ["アーマロイド"],
    "mana": 1,
    "text": FULL_TEXT,
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
    assert c["abilities"][0]["when"] == {"event": "move", "to": "mana",
                                         "from": ["deck", "graveyard"],
                                         "subject": {"owner": "opp"}}
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
    assert d.cost == 3 and d.power == 2000
    assert find(str(PROTO), TARGET) is None
    proto = proto_card("T1217")
    for k in ("name", "types", "civs", "cost", "power",
              "races", "mana", "text", "abilities"):
        assert proto[k] == SUBMIT[k], k
    assert len(proto["abilities"]) == 1


def test_official_row_matches_skeleton_and_text():
    off = None
    for line in (ROOT / "data/cards/raw/by_product/39.jsonl") \
            .read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("id") == TARGET:
            off = r
    assert off is not None
    assert off["name"] == NAME
    assert off["text"] == FULL_TEXT
    assert int(off["cost"]) == 3
    assert int(off["power"]) == 2000
    assert off["race"] == "アーマロイド"
    assert off["civilization"] == "火"
    assert off["card_type"] == "クリーチャー"
    assert int(off["mana"]) == 1
