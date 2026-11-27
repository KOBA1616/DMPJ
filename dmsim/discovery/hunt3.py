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
   蓄積段には停止条件がある（2026-11-25 追加）: 増分ベクトルから決まる周回上限（lap_cap）で
   蓄積を止め、決着（特に消費ゾーンの枯渇による自滅）がつく前に変換段へ引き継ぐ。
   初版は停止条件がなく、手札型エンジン（サガ+XENARCH）が蓄積段で山札を移し切って
   山札切れ自滅し、変換段に到達できなかった。あわせて仕込みの山札は身代わり札でなく
   実カード（役割補完＋埋め札）で構成する（default_deck_cards）。初版は山札が T001 のため、
   増えた手札の中身が大半身代わり札になっていた。
4. 変換候補の選び方をエンジンの増分ベクトルに連動させた（pair_conversions3）。
   候補カードが「どのゾーンを使うか」（束の移動元・前提ゾーン・特殊勝利の条件が参照するゾーン）を
   静的にタグ付けし、エンジンが増やすゾーンと重なる候補を優先する。手札型と墓地型は区別される。
"""
from __future__ import annotations

import json
import time
from collections import Counter, defaultdict

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


# --- 蓄積段の停止条件（増分ベクトルから決まる汎用形） -------------------------

_DELTA_ZONES = ("hand", "graveyard", "mana", "bz", "shield", "deck")


def _delta_zones(delta: dict | None) -> tuple[dict[str, int], dict[str, int]]:
    """増分ベクトルを (増えるゾーン {zone: +n}, 減るゾーン {zone: n}) に分ける（自分側のみ）。
    mana_untapped は mana に合算する（局面の枚数としては mana ゾーンで数える）。"""
    gained: dict[str, int] = {}
    consumed: dict[str, int] = {}
    for z in _DELTA_ZONES + ("mana_untapped",):
        d = (delta or {}).get(f"{z}:0", 0)
        key = "mana" if z == "mana_untapped" else z
        if d > 0:
            gained[key] = gained.get(key, 0) + d
        elif d < 0:
            consumed[key] = consumed.get(key, 0) - d
    return gained, consumed


def _accum_caps(delta: dict | None, snap0: dict, lap_cap: int) -> dict[str, int]:
    """蓄積の上限: 増えるゾーンは「開始枚数＋増分×lap_cap」までで頭打ちにする。"""
    gained, _ = _delta_zones(delta)
    return {z: snap0.get(z, 0) + d * lap_cap for z, d in gained.items()}


def _laps_estimate(delta: dict | None, snap0: dict, snap: dict) -> float:
    """開始局面と現在局面の差分から、実行された周回数を推定する（増分のあるゾーンの最大値）。
    ターン開始ドロー等でも枚数は動くため推定値だが、停止判定と記録にはこれで足りる。"""
    gained, consumed = _delta_zones(delta)
    ests = [(snap.get(z, 0) - snap0.get(z, 0)) / d for z, d in gained.items()]
    ests += [(snap0.get(z, 0) - snap.get(z, 0)) / c for z, c in consumed.items()]
    return max(ests) if ests else 0.0


def _accum_stop_reason(delta: dict | None, snap0: dict, snap: dict, lap_cap: int) -> str | None:
    """蓄積を止める理由（止めないなら None）。
    - lap_cap: 推定周回数が上限に達した
    - consumed_floor:<zone>: 減るゾーンが「あと2周分」まで減った（枯渇による決着を避ける）"""
    if _laps_estimate(delta, snap0, snap) >= lap_cap:
        return "lap_cap"
    _, consumed = _delta_zones(delta)
    for z, c in consumed.items():
        if snap.get(z, 0) <= 2 * c:
            return f"consumed_floor:{z}"
    return None


def _accum_value_fn(delta: dict | None, snap0: dict, lap_cap: int):
    """蓄積段専用の葉評価: board_value に「決着回避」と「増分連動の上限」を入れたもの。

    資源評価（_board_value）は勝敗を見ない（探索の _eval は value_fn があれば終局判定も
    差し替える）うえ、山札の重みが 0 で増えるゾーンは無制限に数えるため、探索は周回を
    連続適用して消費ゾーン（山札）を尽きさせ、自滅する線を平気で選んでしまう。
    ここでは (1) 終局した局面は勝敗そのもので評価し（負け＝最低値。蓄積段で決着をつけない）、
    (2) 増えるゾーンを開始局面＋増分×lap_cap で頭打ちにし、上限を超えた周回には
    1周分の資源ゲインより大きい減点を付ける。これで「目標まで回したら、決着前に止める」が
    探索自身の選択になる。delta が無い／増減ゾーンが無い場合は通常の _board_value を返す。"""
    gained, consumed = _delta_zones(delta)
    if not gained and not consumed:
        return _board_value
    from dmsim.discovery.advantage import resource_vector, value
    w = hunt2._weights()
    caps = _accum_caps(delta, snap0, lap_cap)
    vec_key = {"bz": "board"}     # resource_vector では bz を board と呼ぶ

    def fn(eng, me):
        r = eng.s.result
        if r is not None:                      # 蓄積段で決着した線は資源量でなく勝敗で評価する
            if r.get("winner") == me:
                return 1e9
            return -1e9 if r.get("winner") is not None else -1e6
        vec = resource_vector(eng, me)
        capped = dict(vec)
        for z, cap in caps.items():
            k = vec_key.get(z, z)
            capped[k] = min(capped[k], cap)
        v = value(capped, resource_vector(eng, 1 - me), w)
        snap = {"hand": vec["hand"], "shield": vec["shield"], "mana": vec["mana"],
                "bz": vec["board"], "graveyard": vec["graveyard"], "deck": vec["deck"]}
        v -= 10.0 * max(0.0, _laps_estimate(delta, snap0, snap) - lap_cap)
        return v

    return fn


def _replay_until(rules, start, entries: list[dict], stop_fn) -> tuple[object, int, bool]:
    """探索が選んだラインの記録（eng.log の断片）を start から再生し、stop_fn(eng) が
    真になった時点（または決着・記録の終わり）で止める。(Engine, 再生した決定数, 完走したか)。
    エンジンは決定的なので、同じ開始局面＋同じ選択からは必ず同じ局面になる。"""
    eng = start.clone()
    used = 0
    for e in entries:
        d = eng.advance()
        if d is None or d["player"] != e["p"] or d["kind"] != e["kind"]:
            return eng, used, False          # 記録とずれた（想定外）→ ここまでの局面を返す
        eng.answer(e["choice"])
        used += 1
        if eng.s.result is not None or stop_fn(eng):
            return eng, used, False
    return eng, used, True


def _play_accum(rules, start, *, delta: dict | None, snap0: dict, lap_cap: int,
                max_turns: int, budget: int = 1000, seed: int = 1) -> tuple[object, dict]:
    """蓄積段: ターンは探索（play_game＋蓄積価値）に任せ、行き過ぎたターンは再生で切り取る。

    play_game にターンを丸ごと任せると、探索予算を使い切った残りは貪欲ロールアウトが
    受け持ち、そちらは価値関数を見ないためループを回し続けて山札切れ自滅する
    （実測: 予算1000では証明書で8周ストックした後、ロールアウトが約17周を手で回して自滅。
    予算を20000に上げてもターン探索が終わらない。逆に決定を1つずつ貪欲に選ぶ方式では、
    探索が実行できる XENARCH 型のループに入れずサガ単独のループに流れた）。
    そこで、各ターンはまず play_game で最後まで回し、結果が「負けで決着」または
    「周回上限の超過」なら、そのターンの決定記録（eng.log）を開始局面から再生し、
    停止条件が発火した決定の直後で切り取った局面を引き継ぎに使う。再生した局面は
    実際に選ばれたラインの途中経過そのものなので、到達可能性は保たれる。
    停止条件に届かなかったターンはそのまま採用し、次のターンへ進む。"""
    from dmsim.eval.lockcheck import lock_probe
    from dmsim.search.game import GameResult, finish_result, play_game, record_turn_loops
    from dmsim.search.turn import own_turn
    me = 0
    eng = start.clone()
    value_fn = _accum_value_fn(delta, snap0, lap_cap) if delta else _board_value
    info: dict = {"loops": [], "decisions": 0, "turns": 0, "stop_reason": None,
                  "kill_turn": None, "kind": None, "origin": None, "lost": None,
                  "error": None, "truncated": False}
    seen_loops: set = set()

    def add_loops(rows: list[dict]):
        for lp in rows:
            key = (json.dumps(lp["delta"], sort_keys=True), lp["win_by"], lp["source"], lp["own_turn"])
            if key not in seen_loops:
                seen_loops.add(key)
                info["loops"].append(lp)

    try:
        for _ in range(max_turns):
            if eng.s.result is not None:
                break
            pre = eng
            at = len(pre.log)
            ot = own_turn(pre, me)
            res, leaf = play_game(rules, [], [], seed, first_player=0, max_turn=ot,
                                  budget=budget, start=pre, lock_judge=lock_probe,
                                  value_fn=value_fn)
            info["turns"] += 1
            info["error"] = info["error"] or res.error
            snap_leaf = _snapshot(leaf)
            lost_game = leaf.s.result is not None and leaf.s.result.get("winner") not in (None, me)
            won_game = leaf.s.result is not None and leaf.s.result.get("winner") == me
            overshot = bool(delta) and _laps_estimate(delta, snap0, snap_leaf) > lap_cap
            if (lost_game or overshot) and not won_game and res.kill_turn is None:
                # 行き過ぎたターン: 決定記録を再生し、停止条件の発火点で切り取る
                entries = leaf.log[at:]
                stop_fn = (lambda e: bool(delta) and
                           _accum_stop_reason(delta, snap0, _snapshot(e), lap_cap) is not None)
                rep, used, _full = _replay_until(rules, pre, entries, stop_fn)
                if used > 0:
                    tmp = GameResult(seed=seed, first_player=0)
                    record_turn_loops(tmp, pre, rep, at, [], [], ot, me)
                    add_loops(_loop_rows3(tmp))
                    add_loops(_loop_rows3(res))     # 探索が使った証明書ループも記録に残す
                    info["decisions"] += used
                    info["truncated"] = True
                    info["stop_reason"] = (_accum_stop_reason(delta, snap0, _snapshot(rep), lap_cap)
                                           if delta else None) or "truncated"
                    eng = rep
                    if eng.s.result is not None:
                        fin = GameResult(seed=seed, first_player=0)
                        finish_result(fin, eng, me)
                        info.update({"kill_turn": fin.kill_turn, "kind": fin.kind,
                                     "origin": fin.origin, "lost": fin.lost})
                    break
                # 再生できなかった場合は葉をそのまま採用する（記録に残す）
                info["error"] = info["error"] or "replay_failed"
            add_loops(_loop_rows3(res))
            info["decisions"] += len(leaf.log) - at
            info["kill_turn"] = res.kill_turn if res.kill_turn is not None else info["kill_turn"]
            info["kind"] = res.kind or info["kind"]
            info["origin"] = res.origin or info["origin"]
            info["lost"] = res.lost or info["lost"]
            eng = leaf
            if eng.s.result is not None or res.kill_turn is not None:
                break
            if delta:
                reason = _accum_stop_reason(delta, snap0, _snapshot(eng), lap_cap)
                if reason:
                    info["stop_reason"] = reason
                    break
    except Exception as ex:          # play_game と同様、1件の失敗で全体を止めない
        info["error"] = info["error"] or f"{type(ex).__name__}: {ex}"
    return eng, info


# --- 仕込みの山札（実カード構成） ---------------------------------------------

def default_deck_cards(rules, core_cards: dict[str, int], conv_cards=(), *,
                       deck_n: int = 30, shield_n: int = 5, raw=None) -> tuple[list[str], list[str]]:
    """仕込み局面の山札とシールドを、エンジンと無関係な実カードで構成する。

    中核デッキ構築（basebuild）の考え方を流用する: 中核の文明に収まる役割補完札
    （search/draw/prep/accel/recover、コストの軽い順）を各種4枚まで並べ、埋め札で足りない
    分を埋める。中核カードと変換札は含めない（エンジンと無関係な山札にするため）。
    戻り値は (山札 deck_n 枚, シールド shield_n 枚)。"""
    from collections import Counter

    from dmsim.discovery import basebuild as BB
    exclude = set(core_cards) | set(conv_cards)
    cand = BB.candidates(rules, dict(core_cards), raw)
    species: list[str] = []
    for role in BB.ROLES:
        species += [c for c in cand.get(role, []) if c not in exclude]
    species += [c for c in BB.fillers(rules, dict(core_cards), raw) if c not in exclude]
    total = deck_n + shield_n
    cards: list[str] = []
    cnt: Counter = Counter()
    for cid in species:
        while cnt[cid] < 4 and len(cards) < total:
            cards.append(cid)
            cnt[cid] += 1
        if len(cards) >= total:
            break
    if len(cards) < total and species:      # 種が尽きた場合のみ、埋め札の先頭種で4枚制限を超えて埋める
        pad = species[-1]
        cards += [pad] * (total - len(cards))
    return cards[shield_n:], cards[:shield_n]


def judge_conversion3(rules, core_cards: dict[str, int], conv_cards: list[str], by_card=None, *,
                      engine_budget: int = 1000, conv_budget: int = 1000,
                      engine_turns: int = 2, conv_turns: int = 6, seeds=(1,),
                      delta: dict | None = None, lap_cap: int = 12,
                      deck_cards: list[str] | None = None,
                      shield_cards: list[str] | None = None,
                      controls: bool = True, conv_deck_floor: int | None = 3,
                      conv_time_limit: float | None = None, conv_lock_rounds: int = 2) -> dict:
    """変換判定 v3: 認定済みエンジンを実際に回して得た実局面から勝ちを探す。

    段1（蓄積）: 仕込み局面（最小コア＋変換札1枚）を _play_accum で進める（ターンは探索に
    任せ、行き過ぎたターンは決定記録の再生で停止条件の発火点まで切り取る）。
    停止条件（delta を渡した場合）: 増分ベクトルから決まる周回上限 lap_cap に達するか、
    減るゾーンが枯渇寸前（あと2周分）になったら蓄積を止めて引き継ぐ。
    探索の葉評価にも同じ上限と決着回避を入れる（_accum_value_fn）。
    段2（変換）: 到達局面をそのまま引き継ぎ、勝ち狙いの探索を conv_turns ターン回して
    勝ち／ロックが実行できるかを見る。資源の注入は一切しない。
    仕込みの山札は実カードで構成する（default_deck_cards。deck_cards/shield_cards で差し替え可）。
    ゲームが段1で決着していた場合は、その結果をそのまま記録する（勝ちなら変換不要で合格）。"""
    from dmsim.eval.lockcheck import lock_probe
    from dmsim.search.game import play_game
    from dmsim.search.turn import own_turn
    by_card = by_card if by_card is not None else bundles_by_card(rules)
    if deck_cards is None or shield_cards is None:
        d2, s2 = default_deck_cards(rules, core_cards, conv_cards)
        deck_cards = d2 if deck_cards is None else deck_cards
        shield_cards = s2 if shield_cards is None else shield_cards
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
        spec["p0"]["deck"] = list(deck_cards)
        spec["p0"]["shield"] = list(shield_cards or [])
        spec["p1"]["deck"] = ["T001"] * 30     # 相手は従来どおり身代わり札の山札
        spec["deck_size"] = 0                  # filler で水増ししない（山札は上記の指定そのまま）
        start = scenario.build(rules, spec, first_player=0)
        snap0 = _snapshot(start)
        eng_cur, acc = _play_accum(rules, start, delta=delta, snap0=snap0, lap_cap=lap_cap,
                                   max_turns=engine_turns, budget=engine_budget, seed=sd)
        snap1 = _snapshot(eng_cur)
        row: dict = {"seed": sd, "engine_loops": acc["loops"],
                     "engine_kill_turn": acc["kill_turn"], "engine_lost": acc["lost"],
                     "engine_error": acc["error"], "handoff": snap1,
                     "accum": {"initial": {k: v for k, v in snap0.items() if k != "hand_cards"},
                               "laps_est": round(_laps_estimate(delta, snap0, snap1), 1) if delta else None,
                               "lap_cap": lap_cap if delta else None,
                               "turns": acc["turns"], "decisions": acc["decisions"],
                               "stop_reason": acc["stop_reason"], "truncated": acc["truncated"]},
                     "setup_deck": dict(Counter(deck_cards + list(shield_cards or [])))}
        decided = eng_cur.s.result is not None
        row["decided_in_engine_phase"] = decided
        if decided:
            row.update({"kill_turn": acc["kill_turn"], "kind": acc["kind"],
                        "origin": acc["origin"],
                        "pass": eng_cur.s.result.get("winner") == 0})
        else:
            ot = own_turn(eng_cur, 0)
            res2, _eng2 = play_game(rules, [], [], sd, first_player=0,
                                    max_turn=ot + conv_turns, budget=conv_budget,
                                    start=eng_cur, lock_judge=lock_probe,
                                    deck_floor=conv_deck_floor if delta else None,
                                    time_limit=conv_time_limit, lock_rounds=conv_lock_rounds)
            row.update({"kill_turn": res2.kill_turn, "kind": res2.kind, "origin": res2.origin,
                        "lost": res2.lost, "error": res2.error,
                        "pass": res2.kill_turn is not None})
        row["seconds"] = round(time.time() - t0, 1)
        row["raw_pass"] = row["pass"]
        if controls and row["pass"]:
            # 対照: 核からカードを1種ずつ外した局面（と核なし）でも勝てるなら、勝ちは
            # エンジン由来ではない（ただ殴って勝った等）。不合格にはせず値つきで残す。
            variants = [(c, {k: v for k, v in core_cards.items() if k != c})
                        for c in core_cards]
            ctl = []
            for removed, sub in variants:
                try:
                    cv = judge_conversion3(rules, sub, conv_cards, by_card, engine_budget=engine_budget,
                                           conv_budget=conv_budget, engine_turns=engine_turns,
                                           conv_turns=conv_turns, seeds=(sd,), delta=delta,
                                           lap_cap=lap_cap, controls=False)
                    r0 = cv["rows"][0]
                    ctl.append({"removed": removed, "pass": cv["pass"], "kill_turn": r0.get("kill_turn")})
                except Exception as ex:      # 核が空など、局面を作れない対照は「勝てない」扱いで理由を残す
                    ctl.append({"removed": removed, "pass": False, "kill_turn": None,
                                "error": f"{type(ex).__name__}: {ex}"})
            row["controls"] = ctl
            row["attributed"] = not any(c["pass"] for c in ctl)
            row["pass"] = row["attributed"]
        rows.append(row)
    return {"pass": any(r["pass"] for r in rows),
            "raw_pass": any(r.get("raw_pass") for r in rows), "rows": rows}
