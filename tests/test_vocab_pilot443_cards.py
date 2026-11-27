"""語彙パイロット第443弾（cards 側）:
no_untap_until_next_own_turn_start — 対象は
dm26rp1-s002 世界のY チャクラ・デル・フィン
（pure 1件、multi にも現れない）。

提出形は partial の骨格〔クリーチャー / 光 /
コスト3 / パワー4000 / 種族 アポロニア・ドラゴン/
超化獣、mana 1、keywords [z_rush]、text 公式全文
（通常面）、abilities 4件構築済み〕に **hyper: true
フィールド**と第2条項の trigger 1件〔when:
{event: move, to: shield, subject: {owner: you}}、
effect: [choose {select: {zone: bz, owner: opp,
filter: {types: [creature]}, count: 1}, as: t},
tap {select: {ref: t, count: all}},
modify {select: {ref: t, count: all},
mod: {deny: [untap_at_start]},
duration: until_next_own_turn_start}]〕を足し、
unsupported を外したもの。**補完あり: abilities
（第2条項）＋hyper: true**（partial に欠落。
登録済み超化獣はすべてカードフィールド hyper: true
を持ち、無いと {hyper: true} 条件が満たされない）。

when は登録済み48件の確立形、choose の束縛は
登録済み dmd23-006、modify＋duration は
ジャストダイバーの登録形（dm22rp1-056）、
deny [untap_at_start] は第439弾の確立形。
フリーズ形 tap {no_untap_next: true} は「次の
相手のターンのはじめ」型で、相手ターン中に解決
すると文面（次の自分のターンのはじめまで）と
食い違うため使わない。
登録ブロッカーの確認（第375弾の教訓）:
rule_convert.split（対象行）は None（定型所有の
対象外）。

alias は dm26rp1-sec003（identity 実測で
canon_id は対象自身、aliases_for =
[dm26rp1-sec003]、rejects に独自行なし）。
ラウンド477で登録済み（reopen の出力は対象1件
ちょうど、登録形は提出形と完全一致、alias は
登録エントリの source.aliases に自動付与）。
本ファイルは登録形に書き換え済み。

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
from tests.test_vocab_pilot443 import ABILITIES, FULL_TEXT, NAME  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
TARGET = "dm26rp1-s002"
ALIAS = "dm26rp1-sec003"
GAP = "no_untap_until_next_own_turn_start"

SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["light"],
    "cost": 3,
    "power": 4000,
    "races": ["アポロニア・ドラゴン", "超化獣"],
    "mana": 1,
    "keywords": ["z_rush"],
    "hyper": True,
    "text": FULL_TEXT,
    "abilities": ABILITIES,
}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_registered_and_family_cleared():
    rows = _reject_rows()
    mine = {r["id"]: r for r in rows}
    # ラウンド477で登録済み: 対象行は rejects から解消
    assert TARGET not in mine
    # ファミリー完全解消（pure 1件のみだった）
    fam = sorted(x["id"] for x in rows if GAP in (x.get("gaps") or []))
    assert fam == []
    # 登録形 == 提出形（source 以外の全フィールド）
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT
    assert len(c["abilities"]) == 5
    assert c["keywords"] == ["z_rush"]
    assert c.get("hyper") is True
    assert c["text"] == FULL_TEXT
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == [ALIAS]


def test_alias_and_canon():
    assert canon_id(TARGET) == TARGET
    assert canon_id(ALIAS) == TARGET
    assert aliases_for(NAME, TARGET) == [ALIAS]
    rows = _reject_rows()
    # alias の独自行は rejects に無い
    assert ALIAS not in {r["id"] for r in rows}
    # proto には対象 id のカードは無い（T1233 は型カード）
    assert find(str(PROTO), TARGET) is None


def test_submit_form_parses_and_matches_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    assert d.name == NAME and d.power == 4000
    assert len(d.abilities) == 5
    proto = proto_card("T1233")
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "keywords", "hyper", "text", "abilities"):
        assert proto[k] == SUBMIT[k], k


def test_official_row_consistency():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/26rp1.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    off = next(r for r in rows if r["id"] == TARGET)
    assert off["name"] == NAME
    assert off["card_type"] == "クリーチャー"
    assert off["civilization"] == "光"
    assert int(off["cost"]) == 3
    assert int(off["power"]) == 4000
    assert off["race"] == "アポロニア・ドラゴン/超化獣"
    assert int(off["mana"]) == 1
    assert off["text"] == FULL_TEXT
    # ハイパー面: パワー7500（4000＋3500 の修整と一致）、
    # 追加条項は partial の {hyper: true} 条件群
    # （grant [blocker, double_breaker] / deny cast
    # cost_le 5）と対応する
    f1 = off["faces"][1]
    assert int(f1["power"]) == 7500
    assert "ブロッカー" in f1["text"]
    assert "W・ブレイカー" in f1["text"]
    assert "相手はコスト５以下の呪文を唱えられない" in f1["text"]
