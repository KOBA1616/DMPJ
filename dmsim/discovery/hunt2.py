"""コンボ発見 v2: 検証を「エンジン判定」と「変換判定」に分ける（2構造モデル、2026-11-25 作り直し）。

旧 combo_hunt の欠陥への対処:
1. 候補デッキが「コア札×4＋同文明の軽い札」で、連携が要るループを再現できなかった
   → 仕込み局面は候補の組から機械的に構築し（setup_from_cards）、開幕検証のデッキは役割補完で組む（build_deck_v2）。
2. 検証の探索予算200・4ターンでは偽陰性が支配的だった → 予算600〜1500、2段ふるい（仕込み確認→開幕検証）。
3. カバレッジが候補の 0.002% でスコア指標が近視眼的だった → 循環の種類で層化して抽出する（stratified_sample）。
4. 陽性対照が壊れたまま本番を回した → 対照（akashic / saga）を通常経路で先に通す（tools/combo_hunt2.py --controls）。

2構造モデル（ユーザーの定義）:
- エンジン (A): 最小初期盤面 M を維持・回帰しながら、一定のリソース／アドバンテージが増え続ける回帰構造。
- 変換 (B): 蓄積したアドバンテージから勝利・ロックを実行する構造。
検証は分けて判定する。エンジン判定は「骨格が M に戻る周回（ループ証明書／パターン）が実エンジンで実行され、
1周ごとの資源ベクトルが増える（致命的な減少がない）」こと、変換判定は「資源が莫大化した局面から勝ち／ロックが実行できる」こと。
"""
from __future__ import annotations

import json
import random
import time
from collections import Counter, defaultdict

from dmsim.cards.defs import load_rules
from dmsim.discovery import loop_cond as C
from dmsim.discovery import loop_screen as LS
from dmsim.engine import scenario
from dmsim.engine import zone_graph as Z

FILLER = "T013"          # 手札の身代わり（呪文ダミー）
GY_SEED = "T001"         # 墓地の種札。クリーチャーでなければならない（「墓地にクリーチャー3体以上」のような
                         # 条件は種札の種別で決まる。T013 は呪文なので数に入らない — 対照 saga で実証済み）
GAIN_ZONES = ("hand", "graveyard", "mana", "mana_untapped")

_W = None


def _weights():
    global _W
    if _W is None:
        from dmsim.discovery.advantage import load_weights
        _W = load_weights()
    return _W


def _board_value(eng, me):
    """エンジン判定用の葉評価: 資源の換算値（advantage.board_value）。
    勝ちだけを探す通常の探索は、勝ち手段のないエンジンの周回を実行する動機を持たない。
    資源の増大を評価する物差しで探させることで、「増え続ける回帰」を実行させる。"""
    from dmsim.discovery.advantage import board_value
    return board_value(eng, me, _weights())


def bundles_by_card(rules) -> dict[str, list]:
    by_card: dict[str, list] = defaultdict(list)
    for b in C.bundles(rules):
        by_card[b.card].append(b)
    return by_card


# ---------------------------------------------------------------- 仕込み局面

def setup_from_cards(rules, cards: dict[str, int], by_card: dict, *, mana_n: int | None = None,
                     opp_mana: int = 3, deck_size: int = 30, extra: dict | None = None,
                     place_hint: dict | None = None, seed: int = 1) -> dict:
    """候補の組 {ID: 枚数} から、組が揃った局面（scenario.build の spec）を機械的に作る。

    配り方（cyclesetup.setup_from_cycle の考え方を、閉路でなく札の組に広げたもの）:
    - 無償詠唱の常在能力を持つクリーチャーは場（能力は場で働く。出た直後から回せる形で置く）。
    - 墓地／マナで働く誘発（prem.zone）を持つ札は、そのゾーンに1枚。
    - 墓地から場へ動く札が2枚以上ある場合は、蘇生先として墓地に1枚（例: サガ2枚目）。
    - 墓地から他を動かす札（回収・蘇生）がある場合は、種として身代わり札を墓地に3枚。
    - 残りは手札。マナは組の文明を覆う単色札で、枚数は手札の最大コストと5の大きい方（上限10）。
    extra: {ゾーン: [ID...]} をそのまま足す（変換判定の「資源が莫大化した状態」の再現用）。
    place_hint: {ID: ゾーン} で、その札の最初の1枚の置き場所を上書きする（変換札の配置用）。"""
    from dmsim.discovery.cyclesetup import mono_mana
    zones: dict[str, list[str]] = {"hand": [], "graveyard": [], "mana": [], "bz": []}
    civs: list[str] = []
    for cid, k in cards.items():
        d = rules.cards[cid]
        for v in d.civs:
            if v not in civs:
                civs.append(v)
        bs = by_card.get(cid, [])
        n_bz = n_gy = n_mana = 0
        if LS.free_cast(d) and "creature" in d.types:
            n_bz = 1
        if any(b.prem is not None and b.prem.zone == "graveyard" for b in bs):
            n_gy = max(n_gy, 1)
        if any(b.prem is not None and b.prem.zone == "mana" for b in bs):
            n_mana = max(n_mana, 1)
        if k >= 2 and "creature" in d.types and any(m.from_any("graveyard") and m.dst == "bz"
                                                    for b in bs for m in b.moves):
            n_gy = max(n_gy, 1)
        hint = (place_hint or {}).get(cid)
        if hint:
            zones[hint].append(cid)
            k -= 1
        for z, n in (("bz", n_bz), ("graveyard", n_gy), ("mana", n_mana)):
            take = min(n, k)
            zones[z] += [cid] * take
            k -= take
        zones["hand"] += [cid] * k
    if any(m.from_any("graveyard") and not m.ref_self
           for cid in cards for b in by_card.get(cid, []) for m in b.moves):
        zones["graveyard"] += [GY_SEED] * 3
    for z, ids in (extra or {}).items():
        zones.setdefault(z, []).extend(ids)
    mono = mono_mana(rules)
    cov = [mono[c] for c in civs if c in mono] or [next(iter(mono.values()))]
    hand_costs = [rules.cards[c].cost or 0 for c in zones["hand"]]
    n_mana = mana_n if mana_n is not None else max(5, min(10, max(hand_costs, default=0)))
    mana = zones.pop("mana") + [cov[i % len(cov)] for i in range(n_mana)]
    p0 = {k: v for k, v in zones.items() if v} | {"mana": mana}
    return {"p0": p0, "p1": {"mana": ["T001"] * opp_mana}, "deck_size": deck_size, "seed": seed}


# ---------------------------------------------------------------- エンジン判定

def engine_verdict(delta: dict | None, win_by=None) -> tuple[str | None, bool]:
    """1周の資源ベクトル delta（"ゾーン:プレイヤー" → 増減）からエンジンの種別と合格を返す。
    合格: 勝ちに直結（win）／相手の山札・盾が減る（pressure）／自分の資源が増える（growth）／
    自分の山札だけが減る（burn。シャコガイル型の変換の前段）。手札・盾・マナが周ごとに減るものは失格（致命的）。"""
    if win_by:
        return "win", True
    d = delta or {}

    def g(z: str, p: int) -> int:
        return d.get(f"{z}:{p}", 0)

    growth = any(g(z, 0) > 0 for z in GAIN_ZONES)
    fatal = g("hand", 0) < 0 or g("shield", 0) < 0 or g("mana", 0) < 0 or (g("bz", 0) < 0 and not growth)
    if fatal:
        return None, False
    if g("deck", 1) < 0 or g("shield", 1) < 0:
        return "pressure", True
    if growth:
        return "growth", True
    if g("deck", 0) < 0 and all(g(z, 0) >= 0 for z in ("hand", "graveyard", "mana", "mana_untapped", "shield")):
        return "burn", True
    return None, False


def grown_of(delta: dict | None) -> list[str]:
    """エンジンが増やす資源（変換判定の莫大化の対象）。自分の山札が減る場合は "deck_thin" を足す。"""
    d = delta or {}
    out = [z for z in GAIN_ZONES if d.get(f"{z}:0", 0) > 0]
    if d.get("deck:0", 0) < 0:
        out.append("deck_thin")
    return out


def _play(rules, spec, *, budget: int, max_turn: int, seed: int, value_fn=None):
    from dmsim.eval.lockcheck import lock_probe
    from ..play_api import play_cheat as play_game
    start = scenario.build(rules, spec, first_player=0)
    return play_game(rules, [], [], seed, first_player=0, max_turn=max_turn, budget=budget,
                     start=start, lock_judge=lock_probe, value_fn=value_fn)


def _loop_rows(res) -> list[dict]:
    """実行された周回（res.loops、証拠: executed）と、探索が試して証明書の出た周回
    （res.loop_candidates、証拠: searched）を、重複を除いて並べる。
    証明書は検出器が再生検証したものなので、searched でも「回せる」ことの証拠になる。"""
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
                        "evidence": evidence})
    return out


def judge_engine(rules, cards: dict[str, int], by_card: dict | None = None, *, budget: int = 1500,
                 max_turn: int = 3, seeds=(1,)) -> dict:
    """エンジン判定: 組が揃った局面から、資源評価（advantage.board_value）を物差しにした探索で回し、
    周回の資源ベクトルで判定する。実行された周回を優先し、探索で証明書が出た周回も証拠に数える。"""
    by_card = by_card if by_card is not None else bundles_by_card(rules)
    rows = []
    for sd in seeds:
        spec = setup_from_cards(rules, cards, by_card, seed=sd)
        res, _ = _play(rules, spec, budget=budget, max_turn=max_turn, seed=sd, value_fn=_board_value)
        rows.append({"seed": sd, "kill_turn": res.kill_turn, "kind": res.kind, "origin": res.origin,
                     "lost": res.lost, "error": res.error, "loops": _loop_rows(res),
                     "seconds": round(res.seconds, 1)})
    ok_loops = [l for r in rows for l in r["loops"] if l["ok"]]
    ok_loops.sort(key=lambda l: l["evidence"] != "executed")
    best = ok_loops[0] if ok_loops else None
    return {"pass": bool(ok_loops), "kinds": sorted({l["kind"] for l in ok_loops if l["kind"]}),
            "delta": best["delta"] if best else None, "grown": grown_of(best["delta"]) if best else [],
            "evidence": best["evidence"] if best else None, "rows": rows}


# ---------------------------------------------------------------- 変換判定

def conversion_catalog(rules, by_card: dict) -> list[dict]:
    """変換候補のカタログ: 特殊勝利の札と、相手の山札・盾を動かす札（静的判定 loop_screen.win_card の strict）。"""
    out = []
    for cid, d in sorted(rules.cards.items()):
        if cid.startswith(("T", "R", "L")) or d.cost is None:
            continue
        sw = LS.special_win(d)
        if not sw and not LS.win_card(rules, by_card, cid, strict=True):
            continue
        out.append({"card": cid, "name": d.name, "special_win": bool(sw), "cost": d.cost})
    return out


def pair_conversions(grown: list[str], kinds: list[str], catalog: list[dict], limit: int = 2) -> list[dict]:
    """エンジンの増やす資源に合う変換候補を並べる。特殊勝利を先に、次にコストの軽い順。
    山札を薄くするエンジン（burn / deck_thin）と墓地を増やすエンジンは特殊勝利と相性がよい、という既知の型を優先する。"""
    if "win" in kinds:
        return []
    ordered = sorted(catalog, key=lambda c: (not c["special_win"], c["cost"] or 99, c["card"]))
    return ordered[:limit]


def judge_conversion(rules, engine_cards: dict[str, int], conv_cards: list[str], grown: list[str],
                     by_card: dict | None = None, *, budget: int = 1000, max_turn: int = 6,
                     seeds=(1,)) -> dict:
    """変換判定: エンジンで増えた状態（grown の資源を莫大化した局面）＋変換札から、勝ち／ロックが実行できるか。
    莫大化の再現: 墓地 + 身代わり10枚 / 手札 + 身代わり4枚 / マナは10枚 / 山札は薄く（deck_size を小さく）。
    変換札は、特殊勝利のクリーチャーは場、その他は手札に置く。"""
    by_card = by_card if by_card is not None else bundles_by_card(rules)
    cards = dict(engine_cards)
    hint: dict[str, str] = {}
    for cid in conv_cards:
        cards[cid] = cards.get(cid, 0) + 1
        d = rules.cards[cid]
        hint[cid] = "bz" if ("creature" in d.types and LS.special_win(d)) else "hand"
    extra: dict[str, list[str]] = {}
    if "graveyard" in grown:
        extra["graveyard"] = [GY_SEED] * 10
    if "hand" in grown:
        extra["hand"] = [FILLER] * 4
    mana_n = 10 if ("mana" in grown or "mana_untapped" in grown) else None
    deck_size = 8 if "deck_thin" in grown else 30
    rows = []
    for sd in seeds:
        spec = setup_from_cards(rules, cards, by_card, seed=sd, extra=extra, place_hint=hint,
                                mana_n=mana_n, deck_size=deck_size)
        res, _ = _play(rules, spec, budget=budget, max_turn=max_turn, seed=sd)
        rows.append({"seed": sd, "kill_turn": res.kill_turn, "kind": res.kind, "origin": res.origin,
                     "lost": res.lost, "error": res.error, "loops": _loop_rows(res),
                     "seconds": round(res.seconds, 1)})
    return {"pass": any(r["kill_turn"] is not None for r in rows), "rows": rows}


# ---------------------------------------------------------------- 候補デッキ v2

def build_deck_v2(rules, core: dict[str, int], conv: list[str] = (), raw: dict | None = None) -> list[str]:
    """開幕検証用の40枚。中核は各種4枚、変換札は2枚、残りは役割補完（basebuild.candidates:
    search/draw/prep/accel/recover を文明・コストで絞ったもの）各種4枚、最後に能力なしの埋め札（basebuild.fillers）。
    旧版の「同文明の軽い札を無作為に」という作り方はしない。"""
    from dmsim.discovery import basebuild as BB
    deck: list[str] = []
    for cid in core:
        deck += [cid] * 4
    for cid in conv:
        deck += [cid] * 2
    cand = BB.candidates(rules, dict(core), raw)
    for role in BB.ROLES:
        for cid in cand.get(role, []):
            if len(deck) + 4 <= 40:
                deck += [cid] * 4
    fill = BB.fillers(rules, dict(core), raw)
    i = 0
    while len(deck) < 40 and fill:
        deck += [fill[i % len(fill)]] * min(4, 40 - len(deck))
        i += 1
    while len(deck) < 40 and core:      # 埋め札が無い文明構成の保険（中核を足して40にする）
        deck.append(next(iter(core)))
    return deck[:40]


def judge_opening(rules, deck: list[str], *, budget: int = 600, max_turn: int = 6,
                  seeds=(1, 2)) -> dict:
    """開幕検証（2段ふるいの段2）: 通常の開幕から回し、勝ちか、エンジンの周回が実行されるかを見る。"""
    from dmsim.eval.lockcheck import lock_probe
    from ..play_api import play_cheat as play_game
    rows = []
    for sd in seeds:
        res, _ = play_game(rules, deck, ["T001"] * 40, sd, first_player=sd % 2,
                           max_turn=max_turn, budget=budget, lock_judge=lock_probe)
        rows.append({"seed": sd, "kill_turn": res.kill_turn, "kind": res.kind, "origin": res.origin,
                     "lost": res.lost, "error": res.error, "loops": _loop_rows(res),
                     "seconds": round(res.seconds, 1)})
    passed = any(r["kill_turn"] is not None or any(l["ok"] for l in r["loops"]) for r in rows)
    return {"pass": passed, "rows": rows}


# ---------------------------------------------------------------- 静的な候補列挙と層化

def stratum_of(desc: dict) -> str:
    """循環の種類（どのゾーンが動くか）の層キー。層化抽出の単位。"""
    own = ",".join(sorted((desc.get("delta") or {}).keys()))
    opp = ",".join(sorted((desc.get("opp") or {}).keys()))
    origins = ",".join(sorted({s.split(":")[1] for s in desc.get("steps", []) if s.count(":") >= 2}))
    return f"own[{own}] opp[{opp}] via[{origins}]"


def _mk_candidate(rules, cards: list[str], counts: dict[str, int], score: float, static: str, cyc) -> dict:
    desc = LS.describe(cyc[0], rules) if cyc else {}
    return {"cards": list(cards), "counts": counts, "names": [rules.cards[x].name for x in cards],
            "score": round(float(score), 2), "static": static, "stratum": stratum_of(desc), "cycle": desc}


def enumerate_candidates(rules, by_card: dict | None = None, *, max_turn: int = 6,
                         pair_limit: int | None = None, singles: bool = False,
                         log=print) -> dict:
    """静的ふるい（段0）: 候補ペアに速さの上限と loop_screen.judge_pair を当て、
    勝ち手段まで静的に見える組（full）と、閉路はあるが勝ち手段が静的には見えない組（engine）に分ける。
    singles=True では自己循環する単独札も足す。pair_limit は調べるペア数の上限（速い組から）。"""
    from dmsim.discovery.candidates import candidate_pairs
    from dmsim.eval import speed_bound as S
    by_card = by_card if by_card is not None else bundles_by_card(rules)
    ids, _ = LS.usable_ids(rules)
    pairs = LS.unordered(candidate_pairs(rules, ids))
    sb_cache: dict = {}

    def bound(x: str, y: str):
        k = (x, y)
        if k not in sb_cache:
            sb_cache[k] = S.static_bound(rules, [x, y])["turn"]
        return sb_cache[k]

    pairs.sort(key=lambda p: (-p["score"], p["a"], p["b"]))
    fast = []
    for p in pairs:      # 点の高い順に速さを当て、上限に達したら止める（列挙自体の時間も上限で切れる）
        t = bound(p["a"], p["b"])
        if t is not None and t <= max_turn:
            fast.append(p)
            if pair_limit and len(fast) >= pair_limit:
                break
    log(f"静的ふるい: 速い組 {len(fast)}（母集団 {len(pairs)}）")
    out: dict = {"full": [], "engine": [], "drop": Counter()}
    for p in fast:
        r, cyc = LS.judge_pair([p["a"], p["b"]], by_card, rules)
        counts = {p["a"]: 2, p["b"]: 2}
        if r is None:
            out["full"].append(_mk_candidate(rules, [p["a"], p["b"]], counts, p["score"], "full", cyc))
        elif r == "no_win" and cyc:
            out["engine"].append(_mk_candidate(rules, [p["a"], p["b"]], counts, p["score"], "engine", cyc))
        else:
            out["drop"][r] += 1
    if singles:
        n0 = len(out["full"]) + len(out["engine"])
        for cid in ids:
            bs = by_card.get(cid, [])
            if not any(Z.feeds(b1, b2, rules) for b1 in bs for b2 in bs):
                continue
            r, cyc = LS.judge_set([cid], by_card, rules)
            if r is None:
                out["full"].append(_mk_candidate(rules, [cid], {cid: 2}, 0.0, "full", cyc))
            elif r == "no_win" and cyc:
                out["engine"].append(_mk_candidate(rules, [cid], {cid: 2}, 0.0, "engine", cyc))
        log(f"単独札: {len(out['full']) + len(out['engine']) - n0} 件追加")
    out["drop"] = dict(out["drop"])
    return out


def stratified_sample(items: list[dict], n: int, rng: random.Random) -> list[dict]:
    """層（循環の種類）ごとに点の高い順に、層を巡回しながら n 件取る。スコア上位だけに偏らせない。"""
    strata: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        strata[it["stratum"]].append(it)
    for v in strata.values():
        v.sort(key=lambda x: -x["score"])
    keys = list(strata)
    rng.shuffle(keys)
    out: list[dict] = []
    while len(out) < n and any(strata[k] for k in keys):
        for k in keys:
            if strata[k] and len(out) < n:
                out.append(strata[k].pop(0))
    return out
