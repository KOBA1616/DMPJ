"""語彙パイロット第314弾の対象カード検証（ラウンド349で登録済み）。

stack_from_deck_search は dmex18-045 ワンケングレンオー
～弧月躍動～ の1件のみだった。gaps は空で、partial の
source.unsupported にだけギャップ名が残る監査行
（第312・313弾の監査の継続）。

第314弾の結論はドリフト: 未解決条項は起動能力1節のみで、
第308弾の確立形（{kind: activate, cost: {tap: self}} ＋
may [choose {zone: deck, look: true, filter:
{name_has: 《ケンゴウグレンオー》, types: [creature]},
count: 1} as p → move {ref: p, count: all, stack_evo:
true, evo_source: {ref: self}}] ＋ shuffle、第173弾
deck_evolution の全山札検索形）と完全一致する。
partial の他の節（NEO進化 evolve_from any_of、出た時
マナ置き誘発）は完成済み。

ラウンド349で登録した。登録形は partial ＋ 起動能力、
unsupported を外したもので、abilities は [CIP誘発,
起動能力] の2件ちょうど（連結・merge_split 由来の混入
なし、keywords は無し）。正本判定は identity の実データ
照合による: canon_id は自id、aliases_for は空（alias
なし）。対象行は gaps が空のため reopen では外れず直接
submit（第323・343・347・348弾の先例）。converted
10,252→10,253 / rejects 2,066→2,065、canonical
重なり0・漏れ0。stack_from_deck_search はファミリー
単独行だったため完全に解消。

探索名は《ケンゴウグレンオー》であって進化元の
《ケングレンオー》ではない点に注意（本カードの名
《ワンケングレンオー》が、上に乗る dmc64-025
ケンゴウグレンオーの evolve_from {name_has:
ワンケングレンオー} と一致する名前の連鎖。第308弾の
024 / 025 と同じ構造）。実挙動は
test_vocab_round349_cards.py が登録カード自身で固定。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
REJECTS = ROOT / "data" / "cards" / "raw" / "rejects.jsonl"
TABLES = load_tables()

TARGET = "dmex18-045"
GAP = "stack_from_deck_search"

TEXT = ("NEO進化：自然のクリーチャーまたは名前に《ケングレンオー》とあるクリーチャー１体の上に置いてもよい。"
        "（クリーチャーが下にあれば、これをNEO進化クリーチャーとして扱う）\n"
        "このクリーチャーが出た時、自分の山札の上から１枚目をマナゾーンに置く。\n"
        "このクリーチャーで攻撃するかわりに、タップして次のｔ能力を使ってもよい。\n"
        "t 自分の山札を見る。その中から、名前に《ケンゴウグレンオー》とあるクリーチャーを１体、"
        "このクリーチャーの上に置いてもよい。その後、山札をシャッフルする。")

CIP_TRIGGER = {"kind": "trigger",
               "when": {"event": "move", "to": "bz", "subject": "self"},
               "effect": [
                   {"op": "move",
                    "select": {"zone": "deck", "owner": "you",
                               "from_top": 1},
                    "to": "mana", "reason": "put"}]}

ACTIVATE = {"kind": "activate",
            "cost": {"tap": "self"},
            "effect": [
                {"op": "may",
                 "body": [
                     {"op": "choose",
                      "select": {"zone": "deck", "owner": "you",
                                 "look": True,
                                 "filter": {"name_has": "ケンゴウグレンオー",
                                            "types": ["creature"]},
                                 "count": 1},
                      "as": "p"},
                     {"op": "move",
                      "select": {"ref": "p", "count": "all"},
                      "to": "bz", "reason": "put",
                      "stack_evo": True,
                      "evo_source": {"ref": "self"}}]},
                {"op": "shuffle"}]}

FORM = {"id": TARGET,
        "name": "ワンケングレンオー ～弧月躍動～",
        "types": ["creature"],
        "civs": ["nature"],
        "cost": 5, "power": 5000,
        "races": ["フレイム・モンスター", "エメラルド・モンスター"],
        "mana": 1,
        "neo": True,
        "evolve_from": {"any_of": [{"civs": ["nature"]},
                                   {"name_has": "ケングレンオー"}],
                        "types": ["creature"]},
        "text": TEXT,
        "abilities": [CIP_TRIGGER, ACTIVATE]}


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _unsup(r):
    return [u.get("need") if isinstance(u, dict) else u
            for u in (((r.get("partial") or {}).get("source") or {})
                      .get("unsupported") or [])]


def test_target_registered():
    rows = _rows()
    assert len(rows) == 2065
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10253
    assert not (ids & set(rows))          # canonical 重なり0
    assert TARGET in ids and TARGET not in rows   # 漏れ0
    c = next(c for c in conv if c["id"] == TARGET)
    assert not (c.get("source") or {}).get("unsupported")
    assert not (c.get("source") or {}).get("aliases")   # alias なし
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "neo", "evolve_from", "text", "abilities"):
        assert c.get(k) == FORM[k], k
    assert len(c["abilities"]) == 2       # [CIP誘発, 起動能力]
    assert not c.get("keywords")
    # stack_from_deck_search は完全に解消（ファミリー単独行）
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


def test_established_form_parses():
    d = parse_card(FORM, TABLES)
    assert d.neo
    assert d.evolve_from == FORM["evolve_from"]
    assert [a.get("kind") for a in d.abilities] == ["trigger", "activate"]
    act = d.abilities[1]
    assert act["cost"] == {"tap": "self"}
    # 第308弾の確立形そのもの（may の中身＋外側の shuffle）
    may = act["effect"][0]
    assert may["op"] == "may"
    choose, move = may["body"]
    assert choose["op"] == "choose" and choose["as"] == "p"
    assert choose["select"]["filter"] == {
        "name_has": "ケンゴウグレンオー", "types": ["creature"]}
    assert move["op"] == "move" and move["stack_evo"] is True
    assert move["evo_source"] == {"ref": "self"}
    assert act["effect"][1] == {"op": "shuffle"}
    # 登録カード自身も parse できる
    c = _conv_cache.find(CONVERTED, TARGET)
    d2 = parse_card(c, TABLES)
    assert [a.get("kind") for a in d2.abilities] == ["trigger", "activate"]
