"""候補 → 最小盤面 → 証明書 → submit → 検証 → 登録 を一本で流す共通の入口（2026-11-28）。

札の ID・起点・墓地条件は書かない。すべて候補（データ）か引数で渡す。起点を省くと盤面から自動で取る
（search/origins.py）。縮約（minboard）で最小盤面 M を求め、M で証明書（certify）を作り、回帰があれば
submit_board 経由で verify.register へ渡す。登録簿へ書くのは verify.register だけ。

  cand = {"id": "x", "name": "…", "core": [{"id": "dm…"}], "bz": [...], "graveyard": [...], "hand": [...],
          "mana": 5, "origin": None}          # origin: 札 ID / 起点キー / None(自動)
  rep = run_candidate(rules, cand)            # 4枚組・5枚組・自動探索の出力のどれも同じ形
  rep["stage"]  # none(回帰なし) / certified(証明書のみ) / registered
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from ..base import registry
from ..base.loopspec import LoopSpec
from ..eval import loop_entry as LE
from ..search import compose as C
from ..search.origins import auto_origins, origin_key
from . import certify as Z
from . import minboard as MB
from . import submit as S

REPO = S.REPO
FIND = dict(laps_max=6, max_nodes=2500, tries=6)


def _zones(spec: dict) -> dict:
    p0 = spec["p0"]
    return {z: list(p0.get(z) or []) for z in ("bz", "graveyard", "hand")}


def run_candidate(rules, cand: dict, *, shrink: bool = True, submit: bool = True, seed: int = 1, path=registry.PATH,
                  root: Path = REPO, find: dict | None = None, **submit_kw) -> dict:
    """候補 dict を最初から最後まで流す。戻り: {stage, origin, certificate, minimal, evidence, row, tests}。"""
    find = {**FIND, **(find or {})}
    cid, name, core = cand["id"], cand.get("name", cand["id"]), cand["core"]
    board = {z: list(cand.get(z) or []) for z in ("bz", "graveyard", "hand")}
    mana = cand.get("mana", 5)
    entry, _ = S.build_entry(rules, id=cid, name=name, core=core, mana=mana, note=cand.get("note", ""), root=root, **board)
    ls = LoopSpec.from_json((root / entry).read_text(encoding="utf-8"))
    given = cand.get("origin")
    eng = LE.build(rules, ls, seed)
    if given:
        k = origin_key(given)
        e0 = eng.clone()
        while (d := e0.advance()) is not None and not (d["player"] == 0 and k in [o["key"] for o in d["options"]]):
            ks = [o["key"] for o in d["options"]]
            e0.answer([ks.index("pass") if "pass" in ks else 0])
        origins = [(e0, k)]
    else:
        origins = auto_origins(eng)
    rep = {"id": cid, "stage": "none", "origin": None, "certificate": None, "minimal": None, "evidence": None, "row": None, "tests": 0}
    hit = None
    for e0, k in origins[: cand.get("max_origins", 8)]:
        r = C.find_loop(e0, k, **find)
        if r["kind"] in MB.LOOP_KINDS:
            hit = (k, r)
            break
    if hit is None:
        return rep
    k, r = hit
    rep["origin"] = k
    if shrink:   # 縮約して最小盤面 M にする（墓地は必要部品＋任意の n 枚）
        mb = MB.minimal_board(rules, MB.board_spec(ls, seed), k, name=name, **{x: find[x] for x in ("laps_max", "max_nodes", "tries")})
        board = _zones(mb.spec)
        rep["minimal"] = {"removed": len(mb.removed), "gy_required": dict(mb.gy_required), "gy_any": mb.gy_any, "board": board}
        rep["tests"] = mb.tests
        entry, _ = S.build_entry(rules, id=cid, name=name, core=core, mana=mana, note=cand.get("note", ""), root=root, **board)
        ls = LoopSpec.from_json((root / entry).read_text(encoding="utf-8"))
        e1 = LE.build(rules, ls, seed)
        for e0, k1 in auto_origins(e1) if not given else [(e1, k)]:
            if k1 == k:
                r = C.find_loop(e0, k, **find)
                break
    cert = {"kind": r["kind"], "origin": k, "seed": seed, "M": {z: sorted(v) for z, v in board.items()}, "laps": r["laps"],
            "est_laps": r.get("est_laps"), "deltas": r["deltas"], "decks": r.get("decks", []),
            "moves": r.get("moves", []), "inner": bool(r.get("inner"))}
    rep["certificate"], rep["stage"] = cert, "certified"
    if submit and cert["kind"] in MB.LOOP_KINDS:
        ev, row = S.submit_board(rules, id=cid, name=name, core=core, mana=mana,
                                 note=(cand.get("note", "") + " " + Z.certificate_note(cert)).strip(), path=path, root=root,
                                 certificate=cert, **board, **submit_kw)
        rep.update(evidence=ev, row=row, stage="registered")
    return rep
