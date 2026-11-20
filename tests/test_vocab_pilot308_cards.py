"""語彙パイロット第308弾の対象カード検証（ラウンド343で登録済み）。

evolve_from_deck_onto_self は dmc64-024 ゴウケンオー
～剣々轟々～ / dmc64-025 ケンゴウグレンオー～天地鳴動～ の
2件で、いずれも gaps = [soul_shift, evolve_from_deck_onto_self]、
partial は空だった。soul_shift は第305弾でドリフト確認済み、
残りの条項も第308弾ですべて既存語彙で書けることを固定し、
ラウンド343で登録された:

- 山札を見る→名前に《X》とあるクリーチャーを上に置く→
  シャッフル = choose {zone: deck, look: true, filter:
  {name_has: X, types: [creature]}, count: 1} as p ＋
  move {ref: p, count: all, stack_evo: true, evo_source:
  {ref: self}}（第173弾 deck_evolution の形。同製品の
  登録済み dmc64-036 / dmc64-042 が全山札検索形の先例）
- 攻撃するかわりにタップ = {kind: activate, cost: {tap: self}}
- 全体破壊 = destroy {count: all}（024 は filter
  {keyword: blocker}、025 は {power_le: 2000}）
- 進化元 = evolve_from {name_has: ...}（dmc64-036 の先例）
- ソウルシフト = soul_shift {floor: 1}（024 は裸の
  キーワード＝標準定義「1より少なくならない」。025 は
  リマインダ明記。第305弾の floor: 0 の2件とは本文が異なる）

実挙動は第308弾本体（プロト T948 / T949）とラウンド343 cards
（登録カード自身）で固定済み。ここでは登録形が第308弾の
確立形（FORM_024 / FORM_025）と完全一致し、対象行が rejects
から解消したことを固定する。

正本判定（ラウンド343で identity を実データ照合）:
- 対象2件とも canon_id が自身＝独立正本。alias は
  dmc64-024 ← dm34-015、dmc64-025 ← dm33-016（いずれも
  canon_id が対象に一致）。alias は登録カードの
  source.aliases への記録のみで、独立エントリ・reject 行は
  いずれも無い（dmc64-013 は dmex18-005 の alias であって
  本2件とは無関係）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活
するので _conv_cache を直接使う（第319弾以降の作法）。
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

TARGETS = ["dmc64-024", "dmc64-025"]
ALIASES = {"dmc64-024": ["dm34-015"], "dmc64-025": ["dm33-016"]}

TEXT_024 = ("進化-名前に《ケンゴウグレンオー》とあるクリーチャー１体の上に置く。\n"
            "ソウルシフト\n"
            "このクリーチャーで攻撃するかわりに、タップして次の能力を使ってもよい。 "
            "相手の「ブロッカー」を持つクリーチャーをすべて破壊する。"
            "自分の山札を見る。その中から名前に《ケンゲキオージャ》とあるクリーチャーを１体選び、"
            "このクリーチャーの上に置いてもよい。その後、山札をシャッフルする。\n"
            "T・ブレイカー(このクリーチャ―はシールドを３枚ブレイクする)")

TEXT_025 = ("進化-自分の、名前に《ワンケングレンオー》とあるクリーチャー１体の上に置く。\n"
            "ソウルシフト(このクリーチャーを召喚する時、このクリーチャーの進化元クリーチャーを選ぶ。"
            "このクリーチャーのコストは、その選んだクリーチャーのコストだけ少なくなる。"
            "ただし、このクリーチャーのコストは１より少なくならない)\n"
            "W・ブレイカー\n"
            "このクリーチャーで攻撃するかわりに、タップして次の 能力を使ってもよい。\n"
            "相手のパワー2000以下のクリーチャーをすべて破壊する。"
            "自分の山札を見る。その中から名前に《ゴウケンオー》とあるクリーチャーを１体選び、"
            "このクリーチャーの上に置いてもよい。その後、山札をシャッフルする。")


def _activate(destroy_filter, name_has):
    return {"kind": "activate",
            "cost": {"tap": "self"},
            "effect": [
                {"op": "destroy",
                 "select": {"zone": "bz", "owner": "opp",
                            "filter": destroy_filter, "count": "all"}},
                {"op": "may",
                 "body": [
                     {"op": "choose",
                      "select": {"zone": "deck", "owner": "you",
                                 "look": True,
                                 "filter": {"name_has": name_has,
                                            "types": ["creature"]},
                                 "count": 1},
                      "as": "p"},
                     {"op": "move",
                      "select": {"ref": "p", "count": "all"},
                      "to": "bz", "reason": "put",
                      "stack_evo": True,
                      "evo_source": {"ref": "self"}}]},
                {"op": "shuffle"}]}


FORM_024 = {"id": "dmc64-024",
            "name": "ゴウケンオー～剣々轟々～",
            "types": ["creature", "evolution"],
            "civs": ["fire"],
            "cost": 17, "power": 16000, "mana": 1,
            "races": ["フレイム・モンスター"],
            "text": TEXT_024,
            "evolve_from": {"name_has": "ケンゴウグレンオー"},
            "soul_shift": {"floor": 1},
            "keywords": ["triple_breaker"],
            "abilities": [_activate(
                {"types": ["creature"], "keyword": "blocker"},
                "ケンゲキオージャ")]}

FORM_025 = {"id": "dmc64-025",
            "name": "ケンゴウグレンオー～天地鳴動～",
            "types": ["creature", "evolution"],
            "civs": ["fire"],
            "cost": 10, "power": 11000, "mana": 1,
            "races": ["フレイム・モンスター"],
            "text": TEXT_025,
            "evolve_from": {"name_has": "ワンケングレンオー"},
            "soul_shift": {"floor": 1},
            "keywords": ["double_breaker"],
            "abilities": [_activate(
                {"types": ["creature"], "power_le": 2000},
                "ゴウケンオー")]}


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_registered_in_pilot308_forms():
    rows = _rows()
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    for t, form in (("dmc64-024", FORM_024), ("dmc64-025", FORM_025)):
        assert t not in rows                     # rejects から外れた
        c = _conv_cache.find(CONVERTED, t)
        assert c is not None                     # converted に登録済み
        assert not (c.get("source") or {}).get("unsupported")
        assert (c.get("source") or {}).get("aliases") == ALIASES[t]
        # 登録形の完全一致（連結・merge_split 由来の混入なし）
        for k in ("name", "types", "civs", "cost", "power", "mana",
                  "races", "text", "evolve_from", "soul_shift",
                  "keywords", "abilities"):
            assert c.get(k) == form.get(k), (t, k)
        assert len(c["abilities"]) == 1
        assert c["abilities"][0]["kind"] == "activate"
        # alias は独立エントリにも reject 行にも無い
        for a in ALIASES[t]:
            assert a not in ids and a not in rows
    # evolve_from_deck_onto_self と soul_shift は解消
    for gap in ("evolve_from_deck_onto_self", "soul_shift"):
        holders = {rid for rid, r in rows.items()
                   if gap in (r.get("gaps") or [])}
        assert holders == set(), (gap, holders)


def test_registered_forms_parse():
    for t, form, kw in (("dmc64-024", FORM_024, "triple_breaker"),
                        ("dmc64-025", FORM_025, "double_breaker")):
        c = _conv_cache.find(CONVERTED, t)
        d = parse_card(c, TABLES)
        assert d.types == ["creature", "evolution"]
        assert d.soul_shift == {"floor": 1}
        assert kw in d.keywords
        acts = [a for a in d.abilities if a.get("kind") == "activate"]
        assert len(acts) == 1
        assert acts[0]["cost"] == {"tap": "self"}
        # destroy マクロは parse 時に move（reason: destroy）へ展開される
        eff = acts[0]["effect"]
        assert [op["op"] for op in eff] == ["move", "may", "shuffle"]
        assert eff[0]["reason"] == "destroy"
        assert eff[0]["select"]["filter"] == \
            form["abilities"][0]["effect"][0]["select"]["filter"]
        assert eff[1] == form["abilities"][0]["effect"][1]
