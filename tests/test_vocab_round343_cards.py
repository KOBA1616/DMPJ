"""再変換ラウンド343（第308弾 evolve_from_deck_onto_self）の記録テスト。

- 新規登録2件: dmc64-024 ゴウケンオー～剣々轟々～ /
  dmc64-025 ケンゴウグレンオー～天地鳴動～。
  alias 畳み込み・stale クリーンアップ・差し戻しは0件
  （alias は source.aliases への記録のみ）。
- 正本判定は identity の実データ照合による: 対象2件とも
  canon_id が自身＝独立正本。alias は dmc64-024 ← dm34-015、
  dmc64-025 ← dm33-016（いずれも canon_id が対象に一致し、
  独立エントリ・reject 行は無い）。
- converted 10,245→10,247 / rejects 2,076→2,074、
  canonical 重なり0・漏れ0。evolve_from_deck_onto_self と
  soul_shift はともに解消（soul_shift の残留は本2件だけだった）。
- reopen は対象行に reason が無いため0件（第323弾の先例）。
  submit が登録時に reject 行を直接外した。

登録形は第308弾の確立形 FORM_024 / FORM_025 と完全一致
（submit の連結・merge_split 由来の混入なし、abilities は
[起動能力] の1件ちょうど）:
- partial は空のため公式データから構築。text は reject 行の
  正式本文。ソウルシフトは soul_shift {floor: 1}（024 は裸の
  キーワード＝標準定義、025 はリマインダ明記。第305弾の
  floor: 0 の2件とは本文が異なる）。
- 山札から上に置く = choose {zone: deck, look: true, filter:
  {name_has: X, types: [creature]}} as p ＋ move {ref: p,
  stack_evo: true, evo_source: {ref: self}} ＋ shuffle
  （第173弾 deck_evolution の形）。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない（第319弾以降の
作法）。相手側・進化元・重ね役は第308弾プロト（T950–T955）を
使う。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

C024 = "dmc64-024"
C025 = "dmc64-025"

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


FORM_024 = {"id": C024,
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

FORM_025 = {"id": C025,
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

ALIASES = {C024: ["dm34-015"], C025: ["dm33-016"]}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round343_disposition():
    rej = _reject_rows()
    assert len(rej) == 2074
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10247
    assert not (ids & set(rej))          # canonical 重なり0
    for t, form in ((C024, FORM_024), (C025, FORM_025)):
        c = _conv(t)
        assert c is not None
        assert not (c.get("source") or {}).get("unsupported")
        assert t not in rej              # 漏れ0
        assert (c.get("source") or {}).get("aliases") == ALIASES[t]
        # 登録形の完全一致（連結・merge_split 由来の混入なし）
        for k in ("name", "types", "civs", "cost", "power", "mana",
                  "races", "text", "evolve_from", "soul_shift",
                  "keywords", "abilities"):
            assert c.get(k) == form.get(k), (t, k)
        assert len(c["abilities"]) == 1
        assert c["abilities"][0]["kind"] == "activate"
        d = parse_card(c, TABLES)
        assert d.soul_shift == {"floor": 1}
        # alias は独立エントリにも reject 行にも無い
        for a in ALIASES[t]:
            assert a not in ids and a not in rej
    # evolve_from_deck_onto_self と soul_shift は解消
    for gap in ("evolve_from_deck_onto_self", "soul_shift"):
        holders = {rid for rid, r in rej.items()
                   if gap in (r.get("gaps") or [])}
        assert holders == set(), (gap, holders)


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(
        rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                "deck_size": 20, "deck_exact": [True, True]})


def _by_defn(e, zone, defn, player=0):
    return [c for c in e.zlist(zone, player)
            if e.s.cards[c].defn == defn
            and (zone != "bz" or e.s.cards[c].controller == player)]


def _run(e, handler, limit=900, done=None):
    for _ in range(limit):
        if e.s.result is not None or (done and done()):
            return
        d = e.advance()
        if d is None:
            return
        r = handler(e, d)
        if r is not None:
            e.answer(r)
            continue
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["min"] == 0:
            e.answer([])
        else:
            e.answer(list(range(d["min"])))


def _handler(play_id=None, base_defn=None, activate_id=None,
             stack_defn=None):
    st = {"played": False, "used": False}

    def handler(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["player"] == 0 and activate_id and not st["used"]:
            for i, k in enumerate(keys):
                if k.startswith(f"activate:{activate_id}:"):
                    st["used"] = True
                    return [i]
        if d["kind"] == "main" and d["player"] == 0 \
                and play_id and not st["played"]:
            if f"play:{play_id}" in keys:
                st["played"] = True
                return [keys.index(f"play:{play_id}")]
        if d["kind"] == "choose_evo_source" and base_defn is not None:
            for i, o in enumerate(d["options"]):
                if o.get("defn") == base_defn:
                    return [i]
        if d["kind"] == "pay_mana":
            return [0]
        if d["kind"] == "yes_no":
            return [0]
        if d["kind"] == "choose_cards" and stack_defn is not None:
            for i, o in enumerate(d["options"]):
                if o.get("defn") == stack_defn:
                    return [i]
        if d["kind"] in ("block", "declare_block") \
                and "no_block" in keys:
            return [keys.index("no_block")]
        return None

    handler.state = st
    return handler


# ---------- 実挙動（登録形） ----------

def test_registered_024_soulshift_play(rules):
    """dmc64-024: ソウルシフトで 17−5＝12 を支払って進化する。"""
    e = _build(rules, {"hand": [C024], "bz": ["T950"],
                       "mana": ["T034"] * 12, "deck": ["T002"] * 6},
               {"deck": ["T002"] * 6})
    top = _by_defn(e, "hand", C024)[0]
    base = _by_defn(e, "bz", "T950")[0]
    _run(e, _handler(play_id=C024, base_defn="T950"),
         done=lambda: e.s.cards[top].zone == "bz")
    assert e.s.cards[top].zone == "bz"
    assert e.s.cards[top].under == [base]
    tapped = [c for c in e.zlist("mana", 0) if e.s.cards[c].tapped]
    assert len(tapped) == 12


def test_registered_024_activate(rules):
    """dmc64-024: 起動でブロッカーを全て破壊し、山札から重ねる。"""
    e = _build(rules, {"bz": [C024], "deck": ["T952"] + ["T002"] * 9,
                       "mana": ["T034"] * 3},
               {"bz": ["T954", "T955"], "deck": ["T002"] * 6})
    host = _by_defn(e, "bz", C024)[0]
    placed = _by_defn(e, "deck", "T952")[0]
    blocker = _by_defn(e, "bz", "T954", player=1)[0]
    small = _by_defn(e, "bz", "T955", player=1)[0]
    _run(e, _handler(activate_id=C024, stack_defn="T952"),
         done=lambda: e.s.cards[placed].zone == "bz")
    assert e.s.cards[blocker].zone == "graveyard"
    assert e.s.cards[small].zone == "bz"      # ブロッカーでない小型は残る
    assert e.s.cards[placed].zone == "bz"
    assert e.s.cards[host].top_of == placed
    assert host in e.s.cards[placed].under
    assert e.s.cards[host].tapped             # 起動コストでタップ


def test_registered_025_activate(rules):
    """dmc64-025: 起動でパワー2000以下を全て破壊し、山札から重ねる。"""
    e = _build(rules, {"bz": [C025], "deck": ["T953"] + ["T002"] * 9,
                       "mana": ["T034"] * 3},
               {"bz": ["T955", "T954"], "deck": ["T002"] * 6})
    host = _by_defn(e, "bz", C025)[0]
    placed = _by_defn(e, "deck", "T953")[0]
    small = _by_defn(e, "bz", "T955", player=1)[0]
    blocker = _by_defn(e, "bz", "T954", player=1)[0]
    _run(e, _handler(activate_id=C025, stack_defn="T953"),
         done=lambda: e.s.cards[placed].zone == "bz")
    assert e.s.cards[small].zone == "graveyard"
    assert e.s.cards[blocker].zone == "bz"    # パワー3000は残る
    assert e.s.cards[placed].zone == "bz"
    assert e.s.cards[host].top_of == placed
    assert host in e.s.cards[placed].under
