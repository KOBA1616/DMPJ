"""コンボ発見 v3: ユーザーの定義（2026-11-25 明確化）に沿った判定器。土台は hunt2。

ユーザーの定義:
- ループ（エンジン）とは、最小盤面 M を維持したまま、そのターン中に、効果と能力の連鎖によって
  アドバンテージが増加する構造。発見は「ループの最小パーツ（エンジン）」と
  「得たリソースから勝利するコンボ（変換）」に分ける。
- エンジンの同一性は増分ベクトルで見る。増分が違えば別エンジン
  （例: サガ単独 {山札-1, 墓地+1} と サガ+XENARCH {山札-1, 手札+1} は別エンジン）。
- 変換は、資源を恣意的に莫大化した試算ではなく、明示的なループによって実際に増加するリソース、
  効果ストック、無限回使用できる効果・能力を利用するもの。増えたリソースの種類に応じて変換を探す。

v2（hunt2）からの差分:
1. エンジン判定に最小性の検証を追加（judge_engine3）。組を一括で判定すると寄与ゼロの相方（乗客）が
   合格してしまう（v2 の合格17組中16組がサガ単独と同一増分だった）ため、各カードを
   「抜く／枚数を減らす」と回帰が壊れるか・増分（エンジンの同一性）が変わるかを確認し、
   最小コア（カードと枚数）を結果に含める。
2. 同一ターン内での増分を明示する。現行の検出（search.game.record_turn_loops）は
   1ターン分のログ区間（ターン開始→終了）ごとに回帰を測るため、記録される周回の増分は
   同一ターン内に閉じる。v3 は own_turn と within_turn を結果に含めてこれを可視化する。
3. 変換判定を開始点から作り直した（judge_conversion3）。v2 は「増えた資源」を身代わり札で
   人工的に最大化した局面から始めていた（extra 注入）。v3 は認定済みエンジンを実際に回して
   得た実局面（増分の累積・周回で溜まった状態そのまま）を引き継ぎ、そこから勝ちを探す。
   資源の人工的な注入はしない。変換札は判定開始時に手札（特殊勝利クリーチャーは場）へ
   1枚だけ置く（これは「変換札を引けている」ことの仮定で、資源の注入ではない）。
4. 変換候補の選び方をエンジンの増分ベクトルに連動させた（pair_conversions3）。
   候補カードが「どのゾーンを使うか」（束の移動元・前提ゾーン・特殊勝利の条件が参照するゾーン）を
   静的にタグ付けし、エンジンが増やすゾーンと重なる候補を優先する。手札型と墓地型は区別される。
"""
from __future__ import annotations

import json
import time
from collections import defaultdict

from dmsim.discovery import hunt2
from dmsim.discovery import loop_screen as LS
from dmsim.discovery.hunt2 import (_board_value, bundles_by_card, engine_verdict,
                                   grown_of, setup_from_cards)
from dmsim.engine import scenario

GAIN_ZONES = hunt2.GAIN_ZONES


# ---------------------------------------------------------------- エンジン判定 v3

def _loop_rows3(res) -> list[dict]:
    """hunt2._loop_rows に own_turn（その周回が使われた自分のターン番号）を足したもの。
    record_turn_loops がターンごとに before/after を取るため、周回は同一ターン内に閉じる。"""
    out, seen = [], set()
    for evidence, lps in (("executed", res.loops), ("searched", res.loop_candidates)):
        for lp in lps:
            key = (json.dumps(lp.get("delta"), sort_keys=True), lp.get("win_by"), lp.get("source"))
            if key in seen:
                continue
            seen.add(key)
            kind, ok = engine_verdict(lp.get("delta"), lp.get("win_by"))
            out.append({"kind": kind, "ok": ok, "delta": lp.get("delta"), "win_by": lp.get("win_by"),
                        "source": lp.get("source"), "limit": lp.get("limit"), "laps": lp.get("laps"),
                        "evidence": evidence, "own_turn": lp.get("own_turn")})
    return out


def _identity(loop: dict | None) -> str | None:
    """エンジンの同一性キー: 増分ベクトル＋勝ち方。"""
    if loop is None:
        return None
    return json.dumps({"delta": loop.get("delta"), "win_by": loop.get("win_by")}, sort_keys=True)


def _best_loop(rows: list[dict]) -> dict | None:
    ok = [l for r in rows for l in r["loops"] if l["ok"]]
    ok.sort(key=lambda l: l["evidence"] != "executed")
    return ok[0] if ok else None


def judge_engine_once(rules, cards: dict[str, int], by_card=None, *, budget: int = 1000,
                      max_turn: int = 3, seeds=(1,)) -> dict:
    """最小性なしの素のエンジン判定（hunt2.judge_engine と同じ条件で、own_turn を含む）。"""
    by_card = by_card if by_card is not None else bundles_by_card(rules)
    rows = []
    for sd in seeds:
        spec = setup_from_cards(rules, cards, by_card, seed=sd)
        res, _ = hunt2._play(rules, spec, budget=budget, max_turn=max_turn, seed=sd,
                             value_fn=_board_value)
        rows.append({"seed": sd, "kill_turn": res.kill_turn, "kind": res.kind, "origin": res.origin,
                     "lost": res.lost, "error": res.error, "loops": _loop_rows3(res),
                     "seconds": round(res.seconds, 1)})
    best = _best_loop(rows)
    return {"pass": best is not None,
            "kinds": sorted({l["kind"] for r in rows for l in r["loops"] if l["ok"] and l["kind"]}),
            "delta": best["delta"] if best else None, "win_by": best["win_by"] if best else None,
            "grown": grown_of(best["delta"]) if best else [],
            "evidence": best["evidence"] if best else None,
            "within_turn": True if best else None,
            "own_turns": sorted({l["own_turn"] for r in rows for l in r["loops"]
                                 if l["ok"] and l.get("own_turn") is not None}),
            "rows": rows}


def _reductions(cards: dict[str, int]):
    """{cid: n} の1段の縮小候補（カードを抜く／枚数を1減らす）を列挙する。"""
    for cid in sorted(cards):
        if cards[cid] > 1:
            yield {**cards, cid: cards[cid] - 1}
        yield {k: v for k, v in cards.items() if k != cid}


def judge_engine3(rules, cards: dict[str, int], by_card=None, *, budget: int = 1000,
                  max_turn: int = 3, seeds=(1,)) -> dict:
    """エンジン判定 v3: 回帰＋増分（hunt2 と同条件）に最小性の検証を足す。

    手順: まず組全体を判定し、合格したら増分ベクトルを「エンジンの同一性」として固定する。
    次に縮小候補（抜く／減らす）を繰り返し試し、同一性が保たれる縮小は採用する（貪欲な最小化）。
    最後に残った組の各カードについて、縮小すると同一性が保てないことを確認し、必要性を記録する。
    乗客カード（抜いても同一性が変わらないカード）は最小コアから外れる。
    """
    by_card = by_card if by_card is not None else bundles_by_card(rules)
    base = judge_engine_once(rules, cards, by_card, budget=budget, max_turn=max_turn, seeds=seeds)
    out: dict = {"pass": base["pass"], "kinds": base["kinds"], "delta": base["delta"],
                 "win_by": base["win_by"], "grown": base["grown"], "evidence": base["evidence"],
                 "within_turn": base["within_turn"], "own_turns": base["own_turns"],
                 "input": dict(cards), "core": None, "ablations": [], "rows": base["rows"]}
    if not base["pass"]:
        return out
    ident = _identity({"delta": base["delta"], "win_by": base["win_by"]})
    cache: dict[str, dict] = {}

    def same_identity(sub: dict[str, int]) -> dict:
        key = json.dumps(sub, sort_keys=True)
        if key not in cache:
            cache[key] = judge_engine_once(rules, sub, by_card, budget=budget,
                                           max_turn=max_turn, seeds=seeds)
        v = cache[key]
        return {"pass": v["pass"], "delta": v["delta"],
                "same": v["pass"] and _identity({"delta": v["delta"], "win_by": v["win_by"]}) == ident}

    core = dict(cards)
    changed = True
    while changed:
        changed = False
        for sub in _reductions(core):
            if not sub:
                continue
            r = same_identity(sub)
            out["ablations"].append({"cards": sub, "pass": r["pass"], "delta": r["delta"],
                                     "same_identity": r["same"], "accepted": r["same"]})
            if r["same"]:
                core = sub
                changed = True
                break
    necessity = {}
    for cid in sorted(core):
        variants = []
        if core[cid] > 1:
            variants.append({**core, cid: core[cid] - 1})
        variants.append({k: v for k, v in core.items() if k != cid})
        tests = []
        for full in variants:
            r = same_identity(full) if full else {"pass": False, "delta": None, "same": False}
            tests.append({"cards": full, "pass": r["pass"], "delta": r["delta"],
                          "same_identity": r["same"]})
        necessity[cid] = {"necessary": all(not t["same_identity"] for t in tests), "tests": tests}
    out["core"] = core
    out["necessity"] = necessity
    out["core_verdict"] = cache.get(json.dumps(core, sort_keys=True)) or same_identity(core)
    return out


# ---------------------------------------------------------------- 変換候補（増分連動）

def _card_zones(rules, by_card, cid: str) -> set[str]:
    """カードが「使う」ゾーンの静的タグ: 束の移動元（自分側）・前提ゾーン・
    特殊勝利や条件が参照するゾーン（defn の op の zone 指定）を集める。"""
    zones: set[str] = set()
    for b in by_card.get(cid, []):
        for m in b.moves:
            if m.owner == "you":
                src = m.src if isinstance(m.src, (list, tuple)) else [m.src]
                zones.update(z for z in src if isinstance(z, str))
        if getattr(b, "prem", None) is not None and b.prem.zone:
            zones.add(b.prem.zone)
    d = rules.cards[cid]
    for op in LS._all_ops(d):
        z = op.get("zone")
        if isinstance(z, str):
            zones.add(z)
        for v in op.values():
            if isinstance(v, dict) and isinstance(v.get("zone"), str):
                zones.add(v["zone"])
    if getattr(d, "grave_cast", False):
        zones.add("graveyard")
    return {z for z in zones if z in ("hand", "graveyard", "mana", "bz", "deck", "shield")}


def conversion_catalog3(rules, by_card) -> list[dict]:
    """変換候補カタログ（v2 と同じ母集団＝特殊勝利＋相手の山札・盾を動かす札）に、
    使うゾーンのタグを付けたもの。"""
    out = []
    for e in hunt2.conversion_catalog(rules, by_card):
        out.append({**e, "zones": sorted(_card_zones(rules, by_card, e["card"]))})
    return out


def engine_type(delta: dict | None, kinds: list[str]) -> str:
    """増分ベクトルからエンジンの型を決める（変換候補の連動キー）。"""
    d = delta or {}
    if any(d.get(f"{z}:0", 0) > 0 for z in ("graveyard",)):
        return "graveyard"
    if d.get("hand:0", 0) > 0:
        return "hand"
    if any(d.get(f"{z}:0", 0) > 0 for z in ("mana", "mana_untapped")):
        return "mana"
    if d.get("bz:0", 0) > 0:
        return "board"
    if "burn" in kinds or (d.get("deck:0", 0) < 0 and d.get("deck:1", 0) >= 0):
        return "deck_thin"
    if d.get("deck:1", 0) < 0 or d.get("shield:1", 0) < 0:
        return "pressure"
    return "other"


# 型 → その資源を使う変換を優先するためのゾーン対応
_TYPE_ZONES = {"graveyard": ("graveyard",), "hand": ("hand",), "mana": ("mana", "hand"),
               "board": ("bz",), "deck_thin": ("deck", "graveyard"), "pressure": (),
               "other": ()}


def pair_conversions3(delta: dict | None, kinds: list[str], catalog3: list[dict],
                      limit: int = 4) -> list[dict]:
    """増分ベクトルに連動した変換候補の並び。
    優先順: (1) 特殊勝利で、使うゾーンがエンジンの増やすゾーンと重なるもの
            (2) 使うゾーンが重なるもの (3) 特殊勝利 (4) その他。いずれもコストの軽い順。"""
    if "win" in kinds:
        return []
    grown = {z for z in GAIN_ZONES if (delta or {}).get(f"{z}:0", 0) > 0}
    etype = engine_type(delta, kinds)
    want = set(_TYPE_ZONES.get(etype, ())) | grown

    def rank(c: dict):
        overlap = len(set(c["zones"]) & want)
        return (0 if (c["special_win"] and overlap) else
                1 if overlap else
                2 if c["special_win"] else 3, c["cost"] or 99, c["card"])

    return [{**c, "engine_type": etype} for c in sorted(catalog3, key=rank)[:limit]]


# ---------------------------------------------------------------- 変換判定 v3

def _snapshot(eng) -> dict:
    """引き継ぎ時点の実局面の要約（自分の各ゾーンの枚数と手札の中身）。
    bz は共有ゾーン（zones["bz"][0] に両者分が入る）ため、所有者で絞る。"""
    out: dict = {}
    for z in ("hand", "graveyard", "mana", "deck", "shield"):
        cids = eng.s.zones[z][0]
        out[z] = len(cids)
        if z == "hand":
            out["hand_cards"] = [eng.s.cards[c].defn for c in cids]
    bz = [c for c in eng.s.zones["bz"][0] if getattr(eng.s.cards[c], "owner", 0) == 0]
    out["bz"] = len(bz)
    return out


def judge_conversion3(rules, core_cards: dict[str, int], conv_cards: list[str], by_card=None, *,
                      engine_budget: int = 1000, conv_budget: int = 1000,
                      engine_turns: int = 2, conv_turns: int = 6, seeds=(1,)) -> dict:
    """変換判定 v3: 認定済みエンジンを実際に回して得た実局面から勝ちを探す。

    段1（蓄積）: 仕込み局面（最小コア＋変換札1枚）に資源評価の探索を engine_turns ターン回し、
    エンジンが実際に実行した周回と、その到達局面（増分の累積・効果ストックを含む実状態）を得る。
    段2（変換）: その局面をそのまま引き継ぎ、勝ち狙いの探索を conv_turns ターン回して
    勝ち／ロックが実行できるかを見る。資源の注入は一切しない。
    ゲームが段1で決着していた場合は、その結果をそのまま記録する（勝ちなら変換不要で合格）。"""
    from dmsim.eval.lockcheck import lock_probe
    from dmsim.search.game import play_game
    from dmsim.search.turn import own_turn
    by_card = by_card if by_card is not None else bundles_by_card(rules)
    rows = []
    for sd in seeds:
        t0 = time.time()
        cards = dict(core_cards)
        hint: dict[str, str] = {}
        for cid in conv_cards:
            cards[cid] = cards.get(cid, 0) + 1
            d = rules.cards[cid]
            hint[cid] = "bz" if ("creature" in d.types and LS.special_win(d)) else "hand"
        spec = setup_from_cards(rules, cards, by_card, seed=sd, place_hint=hint)
        start = scenario.build(rules, spec, first_player=0)
        res1, eng1 = play_game(rules, [], [], sd, first_player=0, max_turn=engine_turns,
                               budget=engine_budget, start=start, lock_judge=lock_probe,
                               value_fn=_board_value)
        row: dict = {"seed": sd, "engine_loops": _loop_rows3(res1),
                     "engine_kill_turn": res1.kill_turn, "engine_lost": res1.lost,
                     "engine_error": res1.error, "handoff": _snapshot(eng1)}
        decided = eng1.s.result is not None
        row["decided_in_engine_phase"] = decided
        if decided:
            row["kill_turn"] = res1.kill_turn
            row["kind"] = res1.kind
            row["origin"] = res1.origin
            row["pass"] = eng1.s.result.get("winner") == 0
        else:
            ot = own_turn(eng1, 0)
            res2, _eng2 = play_game(rules, [], [], sd, first_player=0,
                                    max_turn=ot + conv_turns, budget=conv_budget,
                                    start=eng1, lock_judge=lock_probe)
            row.update({"kill_turn": res2.kill_turn, "kind": res2.kind, "origin": res2.origin,
                        "lost": res2.lost, "error": res2.error,
                        "pass": res2.kill_turn is not None})
        row["seconds"] = round(time.time() - t0, 1)
        rows.append(row)
    return {"pass": any(r["pass"] for r in rows), "rows": rows}
