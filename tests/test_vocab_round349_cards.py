"""再変換ラウンド349（第314弾 stack_from_deck_search）の記録テスト。

- 新規登録1件: dmex18-045 ワンケングレンオー ～弧月躍動～。
- alias 畳み込み0件（identity の canon_id は自id、
  aliases_for は空）。
- stale クリーンアップ0件・差し戻し0件。
- 対象行は gaps が空のため reopen では外れず直接 submit
  （第323・343・347・348弾の先例）。
- converted 10,252→10,253 / rejects 2,066→2,065、
  canonical 重なり0・漏れ0。stack_from_deck_search は
  ファミリー単独行だったため完全に解消。

登録形は第314弾の確立形と完全一致（submit の連結・
merge_split 由来の混入なし、abilities は [CIP誘発,
起動能力] の2件ちょうど、keywords は無し）:
- partial（NEO進化 evolve_from any_of、出た時「山札の
  上から1枚目をマナゾーンに置く」誘発は完成済み）に、
  第308弾の確立形の起動能力（{kind: activate, cost:
  {tap: self}} ＋ may [choose {zone: deck, look: true,
  filter: {name_has: ケンゴウグレンオー, types:
  [creature]}, count: 1} as p → move {ref: p, count: all,
  stack_evo: true, evo_source: {ref: self}}] ＋ shuffle、
  第173弾 deck_evolution の全山札検索形）を追加し、
  unsupported を除去したもの。
- 探索名は《ケンゴウグレンオー》であって進化元の
  《ケングレンオー》ではない（本カードの名
  《ワンケングレンオー》が上に乗る dmc64-025 の
  evolve_from {name_has: ワンケングレンオー} と一致する
  名前の連鎖。第308弾の 024 / 025 と同じ構造）。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない（第319弾以降の
作法）。
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


def _reject_rows():
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


def test_round349_disposition():
    rej = _reject_rows()
    assert len(rej) == 2065
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10253
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGET in ids and TARGET not in rej   # 漏れ0
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert not (c.get("source") or {}).get("aliases")   # alias なし
    # 登録形の完全一致（連結・merge_split 由来の混入なし）
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "neo", "evolve_from", "text", "abilities"):
        assert c.get(k) == FORM[k], k
    assert len(c["abilities"]) == 2      # [CIP誘発, 起動能力]
    assert not c.get("keywords")         # キーワード能力なし
    d = parse_card(c, TABLES)
    assert d.neo and d.types == ["creature"]
    assert [a.get("kind") for a in d.abilities] == ["trigger", "activate"]
    # stack_from_deck_search は完全に解消（ファミリー単独行）
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or []) or GAP in _unsup(r)}
    assert left == set(), left


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

CARD = TARGET


def _build(rules, p0, p1):
    return scenario.build(
        rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                "deck_size": 20, "deck_exact": [True, True]})


def _cids(e, zone, p=0):
    return [c for c in e.zlist(zone, p)
            if zone != "bz" or e.s.cards[c].controller == p]


def _by_defn(e, zone, defn, p=0):
    return [c for c in _cids(e, zone, p) if e.s.cards[c].defn == defn]


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
    raise AssertionError("run did not finish")


# ---------- 実挙動（登録形） ----------

def test_registered_cip_top_card_to_mana(rules):
    """dmex18-045: 出た時、自分の山札の上から1枚目をマナへ。"""
    e = _build(rules,
               {"hand": [CARD], "mana": ["T001"] * 5,
                "deck": ["T002"] * 8},
               {"deck": ["T002"] * 6})
    st = {"played": False}

    def handler(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d["player"] == 0 and not st["played"]:
            for i, k in enumerate(keys):
                if k == f"play:{CARD}":
                    st["played"] = True
                    return [i]
        if d["kind"] == "pay_mana":
            return [0]
        if d["kind"] == "yes_no":
            return [keys.index("yes")] if "yes" in keys else [0]
        return None

    _run(e, handler,
         done=lambda: len(_by_defn(e, "mana", "T002")) == 1)
    assert st["played"]
    assert len(_by_defn(e, "bz", CARD)) == 1
    assert len(_by_defn(e, "mana", "T002")) == 1   # 山札の上から1枚
    assert len(_cids(e, "mana")) == 6              # 5 + CIP 1


def _activate_driver(accept=True, seen=None):
    st = {"used": False}

    def handler(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["player"] == 0 and not st["used"]:
            for i, k in enumerate(keys):
                if k.startswith(f"activate:{CARD}:"):
                    st["used"] = True
                    return [i]
        if d["kind"] == "yes_no":
            if accept:
                return [keys.index("yes")] if "yes" in keys else [0]
            return [keys.index("no")] if "no" in keys \
                else [len(d["options"]) - 1]
        if d["kind"] == "choose_cards":
            defns = [e.s.cards[o["cid"]].defn for o in d["options"]]
            if seen is not None:
                seen.append(defns)
            for i, dfn in enumerate(defns):
                if dfn == "T949":
                    return [i]
        if d["kind"] == "pay_mana":
            return [0]
        return None

    handler.state = st
    return handler


def _activate_fixture(rules):
    # 山札 spec は末尾が上。T949（ケンゴウグレンオー）を2枚
    # （候補1枚では choose が自動決定されるため）、名前が近い
    # だけの T951 を対照に混ぜる
    return _build(rules,
                  {"bz": [CARD], "mana": ["T034"] * 3,
                   "deck": ["T949", "T949", "T951"] + ["T001"] * 7},
                  {"deck": ["T002"] * 6})


def test_registered_activate_stacks_from_deck(rules):
    """起動能力: 山札から《ケンゴウグレンオー》を1体、
    このクリーチャーの上に置く（候補は T949 のみ）。"""
    e = _activate_fixture(rules)
    host = _by_defn(e, "bz", CARD)[0]
    seen = []
    handler = _activate_driver(seen=seen)
    _run(e, handler,
         done=lambda: len(_by_defn(e, "bz", "T949")) == 1)
    assert handler.state["used"]
    # choose の候補は T949 の2枚だけで、T951 は提示されない
    assert seen and all(s == ["T949", "T949"] for s in seen)
    placed = _by_defn(e, "bz", "T949")[0]
    assert e.s.cards[host].top_of == placed
    assert host in e.s.cards[placed].under
    assert len(_by_defn(e, "deck", "T949")) == 1   # もう1枚は山札に残る
    assert e.s.cards[host].tapped                 # 起動コスト


def test_registered_activate_decline_stacks_nothing(rules):
    """起動能力を辞退すると何も重ならず、コストのタップだけ払う。"""
    e = _activate_fixture(rules)
    host = _by_defn(e, "bz", CARD)[0]
    handler = _activate_driver(accept=False)
    _run(e, handler, limit=300,
         done=lambda: e.s.cards[host].tapped
         and len(_by_defn(e, "deck", "T949")) == 2)
    assert handler.state["used"]
    assert e.s.cards[host].top_of == -1            # 重なっていない
    assert len(_by_defn(e, "deck", "T949")) == 2   # 山札不変
    assert e.s.cards[host].tapped                  # コストは支払う
