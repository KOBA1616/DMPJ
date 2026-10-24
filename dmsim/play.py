"""対戦の実行・再生と、簡単な方策（エージェント）。"""
from __future__ import annotations

import random

from .engine import Engine


def random_policy(rng: random.Random):
    def pol(eng: Engine, d: dict) -> list[int]:
        n = len(d["options"])
        k = rng.randint(d["min"], d["max"])
        return rng.sample(range(n), k)
    return pol


def passive_policy(eng: Engine, d: dict) -> list[int]:
    """1人回しの相手役: 何もしない（ブロックしない・S・トリガーを使わない・最小限の選択）。"""
    keys = [o["key"] for o in d["options"]]
    for k in ("pass", "no_block", "no", "decline"):
        if k in keys:
            return [keys.index(k)]
    return list(range(d["min"]))


def run(eng: Engine, policies, max_decisions: int = 100000) -> dict:
    """policies[p](eng, decision) -> 選択した添字のリスト。"""
    for _ in range(max_decisions):
        d = eng.advance()
        if d is None:
            return eng.s.result
        eng.answer(policies[d["player"]](eng, d))
    raise RuntimeError("decision limit")


def replay(rules, decks, seed, log, first_player=0, scenario=None) -> Engine:
    """シード＋選択ログから同じ対戦を再現する。scenario（dmsim.scenario の spec）があればその局面から始める。"""
    if scenario is not None:
        from . import scenario as sc
        eng = sc.build(rules, scenario)
    else:
        eng = Engine.new_game(rules, decks, seed, first_player)
    for entry in log:
        d = eng.advance()
        if d is None or d["kind"] != entry["kind"] or d["player"] != entry["p"]:
            raise RuntimeError(f"replay diverged at {len(eng.log)}: {d and d['kind']} vs {entry}")
        eng.answer(entry["choice"])
    eng.advance()
    return eng


# ---- シード付き対戦記録（再現性） -------------------------------------------------------------

RECORD_VERSION = 1


def cards_digest(rules, decks) -> str:
    """デッキに入っているカードの定義のハッシュ。定義を直した後の記録の再生を見分ける。"""
    import dataclasses
    import hashlib
    import json
    defs = {d: dataclasses.asdict(rules.cards[d]) for d in sorted({c for deck in decks for c in deck})}
    blob = json.dumps(defs, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.blake2b(blob.encode(), digest_size=16).hexdigest()


def make_record(eng: Engine, decks, seed: int, first_player: int = 0, note: str = "",
                scenario: dict | None = None) -> dict:
    """{version, seed, decks, first_player, scenario, log, result, digest, cards_digest}。JSON にそのまま書ける。
    decks はカード定義のハッシュ用に、scenario から始めた時も実際のデッキ（カードIDの列）を入れる。"""
    return {"version": RECORD_VERSION, "seed": seed, "decks": decks, "first_player": first_player,
            "scenario": scenario, "log": list(eng.log), "result": eng.s.result, "digest": eng.s.digest(),
            "cards_digest": cards_digest(eng.rules, decks), "note": note}


def deck_lists(eng: Engine) -> list[list[str]]:
    return [[c.defn for c in eng.s.cards if c.owner == p] for p in (0, 1)]


def replay_record(rules, rec: dict, *, strict: bool = True) -> Engine:
    """記録を再生する。strict なら最終状態のハッシュが一致しない時に例外。"""
    if rec.get("version") != RECORD_VERSION:
        raise ValueError(f"unknown record version {rec.get('version')}")
    if strict and rec.get("cards_digest") and rec["cards_digest"] != cards_digest(rules, rec["decks"]):
        raise ValueError("カード定義が記録時から変わっている（strict=False なら再生を試みる）")
    eng = replay(rules, rec["decks"], rec["seed"], rec["log"], rec.get("first_player", 0), rec.get("scenario"))
    if strict and eng.s.digest() != rec["digest"]:
        raise ValueError("replay digest mismatch")
    return eng


def default_decks(rules, prefix: str = "") -> list[list[str]]:
    """ID が prefix で始まるカードを順に繰り返して 40 枚にしたデッキを2つ。"""
    ids = sorted(i for i in rules.cards if i.startswith(prefix))
    deck = [ids[i % len(ids)] for i in range(40)]
    return [list(deck), list(deck)]


def main(argv=None):
    import argparse
    import json
    from pathlib import Path

    import yaml

    from .defs import load_rules
    ap = argparse.ArgumentParser(description="対戦を1局実行して記録を保存する／記録を再生して確かめる")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--decks", help='YAML: {decks: [[id, ...], [id, ...]]}。省略時は実カードを繰り返した40枚')
    ap.add_argument("--first", type=int, default=0)
    ap.add_argument("--opponent", choices=["random", "passive"], default="random")
    ap.add_argument("--out", help="記録（JSON）の保存先")
    ap.add_argument("--replay", help="記録（JSON）を再生して最終状態のハッシュを確かめる")
    a = ap.parse_args(argv)
    rules = load_rules()
    if a.replay:
        rec = json.loads(Path(a.replay).read_text(encoding="utf-8"))
        eng = replay_record(rules, rec)
        print(f"ok: {len(rec['log'])} decisions, result={eng.s.result}, digest={eng.s.digest()}")
        return
    decks = yaml.safe_load(Path(a.decks).read_text(encoding="utf-8"))["decks"] if a.decks \
        else default_decks(rules, "dm")
    rng = random.Random(a.seed)
    eng = Engine.new_game(rules, decks, a.seed, a.first)
    opp = random_policy(rng) if a.opponent == "random" else passive_policy
    p0 = random_policy(rng)
    result = run(eng, [p0, opp])          # プレイヤー0 = 自分（ランダム）、1 = 相手
    rec = make_record(eng, decks, a.seed, a.first)
    print(f"result={result} decisions={len(eng.log)} digest={rec['digest']}")
    if a.out:
        Path(a.out).write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
