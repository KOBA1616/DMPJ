"""盤面を指定して登録簿へ検証を依頼する窓口（2026-11-27）。

発見の経路（自動探索・人の指定・別の発見系統）によらず、同じ形で「中核の札＋入口の盤面」を渡せば、
デッキ・入口局面・候補を作って verify.register に通し、Evidence を返す。手の登録はしない（探索だけで段1に届くかを測る）。
登録簿へ書けるのは verify.register だけ（docs/registry-design.md）。落ちた候補は rejected に理由つきで残る。

  from dmsim.discovery.submit import submit_board
  ev, row = submit_board(rules, id="x", name="…", core=[{"id": "dm…", "role": "…", "part": "loop"}],
                         bz=["dm…"], graveyard=["dm…"], win="effect")
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from ..base import registry
from . import triples as X

REPO = Path(__file__).resolve().parents[2]


def build_entry(rules, *, id: str, name: str, core: list[dict], bz=(), graveyard=(), hand=(), mana: int = 5,
                budget: int = 1500, note: str = "", deck: list[str] | None = None, root: Path = REPO) -> tuple[str, str]:
    """入口局面の JSON とデッキ YAML を data/loops/entry/auto・data/decks/auto に書き、(入口のパス, デッキのパス) を相対で返す。
    盤面に置いた札以外は、デッキ（既定は中核の札 4 枚ずつ＋基盤の穴埋め）から配る。minimal は置いた札だけ（勝ち手段は含めない）。"""
    ids = [c["id"] for c in core]
    deck = list(deck) if deck is not None else X.deck_of(rules, ids)
    spec = X.entry_spec(rules, deck, [], mana, 1, {})
    p0 = spec["p0"]

    def take(cid):
        for z in ("deck", "hand", "shield", "mana"):
            if cid in p0[z]:
                p0[z].remove(cid)
                return
        raise ValueError(f"{id}: {cid} がデッキの枚数を超える")
    for z, cards in (("bz", bz), ("graveyard", graveyard), ("hand", hand)):
        for c in cards:
            take(c)
    p0["bz"], p0["graveyard"] = list(bz), list(graveyard)
    p0["hand"] = list(hand) + p0["hand"]
    for z, n in (("hand", 5), ("shield", 5), ("mana", mana)):
        while len(p0[z]) < n:
            p0[z].append(p0["deck"].pop())
        del p0[z][n:]
    placed = {"bz": list(bz), "graveyard": list(graveyard), "hand": list(hand)}
    minimal = [{"match": {"name": i}, "n": ids_n, "op": ">=", "owner": 0, "zone": z, "zones": []}
               for z, cs in placed.items() for i, ids_n in sorted({c: cs.count(c) for c in cs}.items())]
    entry = {"name": f"{name}（入口）", "kind": "deterministic", "deck_floor": 1, "delta": {}, "goal": [], "limit": None,
             "hazards": ["field_removal", "counter"], "routes": [], "minimal": minimal,
             "source": {"board": {"opp_deck": spec["deck_left"][1], "opp_deck_total": spec["deck_size"],
                                  "p0": {z: p0[z] for z in ("bz", "graveyard", "hand", "mana", "shield")}, "p1": spec["p1"]},
                        "budget": budget, "deck": f"data/decks/auto/{id}.yaml",
                        "core": [{"any": [{c["id"]: int(c.get("copies", 1))}], "role": c.get("role", "部品"), "part": c.get("part", "loop")} for c in core],
                        "note": note}}
    ep, dp = root / "data" / "loops" / "entry" / "auto" / f"{id}.json", root / "data" / "decks" / "auto" / f"{id}.yaml"
    ep.parent.mkdir(parents=True, exist_ok=True)
    dp.parent.mkdir(parents=True, exist_ok=True)
    ep.write_text(json.dumps(entry, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    dp.write_text(yaml.safe_dump({"deck": deck}, allow_unicode=True), encoding="utf-8")
    return str(ep.relative_to(root)), str(dp.relative_to(root))


def submit_board(rules, *, id: str, name: str, core: list[dict], bz=(), graveyard=(), hand=(), mana: int = 5, win: str = "effect",
                 split: str = "discovered", types=("loop",), procedure=(), note: str = "", seeds=range(1, 9), max_turn: int = 2,
                 budget: int = 1500, deck: list[str] | None = None, certificate: dict | None = None, purpose: str = "eval", path=registry.PATH, root: Path = REPO):
    """中核（[{id, role, part, copies}]）と入口の盤面から候補を作って検証に流す。(Evidence, 登録簿の行) を返す。"""
    from ..eval.verify import register
    entry, _ = build_entry(rules, id=id, name=name, core=core, bz=bz, graveyard=graveyard, hand=hand, mana=mana,
                           budget=budget, note=note, deck=deck, root=root)
    cand = registry.Candidate(
        id=id, name=name, split=split, types=list(types), win=win, entry=entry, procedure=list(procedure), seeds=list(seeds),
        max_turn=max_turn, budget=budget, note=note, certificate=certificate,
        core=[{"id": c["id"], "name": rules.cards[c["id"]].name, "role": c.get("role", "部品"), "part": c.get("part", "loop")} for c in core])
    return register(rules, cand, purpose=purpose, path=path)
