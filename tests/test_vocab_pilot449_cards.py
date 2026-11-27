"""語彙パイロット第449弾（cards 側）:
end_of_attack_effect — 対象は dm25ex2-094
鬼星の絆 ウコン丸＆サコン丸（pure 1件）。

提出形は partial の骨格（名称・文明・コスト3・
パワー4000・種族・マナ1、keywords [blocker]）に
公式全文の text と確立形の abilities を足し、
unsupported を外したもの:
- trigger {event: attack, subject: self,
  if: {not: {exists: {zone: bz, owner: you,
  filter: {types: [tamaseed]}}}} → delayed_trigger
  {when: {event: attack_end, subject: self},
  duration: during_attack, effect: [destroy {ref: self}]}
  （第319弾形A＋タマシード不在の if。if の形は
  登録済み dmrp21-072 と同一）
- trigger {event: block, subject: self, if: 同上}
  → delayed_trigger {when: {event: attack_end,
  target: self}, duration: during_attack,
  effect: [destroy {ref: self}]}（第319弾形B）
- static {affects: {owner: you, zone: hand,
  filter: {types: [creature], race_has: デモニオ}},
  mod: {cost: -1}}（登録済み dm24bd2-016 と同文の
  軽減。ただし下限0はエンジン既定のため cost_min
  は付けない＝第346弾の確立形）
＝ドリフト（追加語彙なし）。

**補完あり: text（公式全文。partial の text は
公式全文のため実質なし）＋abilities（3件）**。
partial の text は既に公式全文と同一のため、
text の補完は無い（abilities のみ未構築）。

alias は dmrp22-060 / promoy21-018（identity 実測で
canon_id は対象自身、aliases_for はこの2件と一致。
rejects に独自行は無い）。カード登録はしない
（それはラウンド483の仕事）。本ファイルは提出形
（未登録）で固定する。

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
from tests.test_vocab_pilot449 import FORM, NAME, TEXT  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
GAP = "end_of_attack_effect"
TARGET = "dm25ex2-094"
ALIASES = ["dmrp22-060", "promoy21-018"]

SUBMIT = {"id": TARGET, **FORM}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_still_rejected_and_family_single():
    rows = _reject_rows()
    mine = {r["id"]: r for r in rows}
    assert TARGET in mine
    row = mine[TARGET]
    assert row["gaps"] == [GAP]
    assert row.get("reason") == "vocab"
    assert row["partial"]["keywords"] == ["blocker"]
    assert "abilities" not in row["partial"]
    # ファミリーはこの1件だけ
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == [TARGET]
    # まだ未登録
    assert find(CONVERTED, TARGET) is None
    for a in ALIASES:
        assert find(CONVERTED, a) is None
        assert a not in mine


def test_alias_and_canon():
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == ALIASES
    for a in ALIASES:
        assert canon_id(a) == TARGET
    # proto には対象 id のカードは無い（T1240 は型カード）
    assert find(str(PROTO), TARGET) is None


def test_submit_form_parse_and_match_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    assert d.name == NAME and d.power == 4000
    # blocker キーワードは parse 時に static 1件へ展開される
    # ため、展開後の abilities は確立形3件＋展開1件＝4件
    assert len(d.abilities) == 4
    assert {"kind": "static", "affects": "self",
            "mod": {"allow": ["block"]},
            "keyword": "blocker"} in d.abilities
    proto = proto_card("T1240")
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "text", "keywords", "abilities"):
        assert proto[k] == SUBMIT[k], k


def test_official_row_consistency():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/25ex2.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    off = next(r for r in rows if r["id"] == TARGET)
    assert off["name"] == NAME
    assert off["card_type"] == "クリーチャー"
    assert off["civilization"] == "闇"
    assert int(off["cost"]) == 3
    assert int(off["power"]) == 4000
    assert off["race"] == "デモニオ/鬼レクスターズ"
    assert int(off["mana"]) == 1
    assert off["text"] == TEXT
    # partial の text は既に公式全文と同一
    row = next(r for r in _reject_rows() if r["id"] == TARGET)
    assert row["partial"]["text"] == TEXT
