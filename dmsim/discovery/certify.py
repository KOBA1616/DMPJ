"""見つけたループを証明書にして登録まで渡す（2026-11-28）。

合成手 find_loop（dmsim/search/compose.py）の回帰を、証明書（最小盤面M・周回・差分Δ）にまとめ、
submit_board（dmsim/discovery/submit.py）経由で verify.register へ渡す。登録簿へ書くのは verify.register だけ。
ループ判定にマナの増加は要らない（収支0以上で可）。回帰が1周も見つからなければ登録せず、証明書だけ返す。
"""
from __future__ import annotations

from pathlib import Path

from ..base import registry
from ..base.loopspec import LoopSpec
from ..eval import loop_entry as LE
from ..search import compose as C
from ..search.origins import origin_key
from . import submit as S

REPO = S.REPO


ZONES = ("deck", "graveyard", "hand", "mana", "shield", "bz")


def _zone_counts(e) -> dict:
    return {who: {z: len(e.zlist(z, p)) for z in ZONES} for who, p in (("you", 0), ("opp", 1))}


def zone_deltas(eng, origin_key: str, moves: list) -> list[dict]:
    """証明書の周ごとの、各ゾーンの枚数の増減（自分 you・相手 opp）。段2が「この蓄積を勝ちに変える札」を引く材料。"""
    out, cur = [], eng
    prev = _zone_counts(cur)
    for keys in moves:
        r = C.replay(cur, origin_key, [tuple(k) for k in keys])
        if r is None:
            break
        cur = r[0]
        now = _zone_counts(cur)
        out.append({w: {z: now[w][z] - prev[w][z] for z in ZONES} for w in now})
        prev = now
    return out


def make_certificate(rules, *, origin: str, bz=(), graveyard=(), hand=(), seed: int = 1, entry_json: str,
                     laps_max: int = 6, max_nodes: int = 2500, tries: int = 6, root: Path = REPO) -> dict:
    """入口局面 JSON から盤面を作り、origin（札 ID なら攻撃の起点、':' を含めば起点キーそのまま）から find_loop を回して証明書を返す。"""
    ls = LoopSpec.from_json((root / entry_json).read_text(encoding="utf-8"))
    e = LE.build(rules, ls, seed)
    while (d := e.advance())["kind"] != "attack":
        ks = [o["key"] for o in d["options"]]
        e.answer([ks.index("pass") if "pass" in ks else 0])
    r = C.find_loop(e, origin_key(origin), laps_max=laps_max, max_nodes=max_nodes, tries=tries)
    zd = zone_deltas(e, f"attack:{origin}:player", r.get("moves", []))
    return {"kind": r["kind"], "origin": origin, "seed": seed, "zone_deltas": zd,
            "M": {"bz": sorted(bz), "graveyard": sorted(graveyard), "hand": sorted(hand)},
            "moves": r.get("moves", []), "laps": r["laps"], "est_laps": r.get("est_laps"), "deltas": r["deltas"], "decks": r.get("decks", [])}


def certificate_note(cert: dict) -> str:
    return (f"合成手の証明書: {cert['kind']}、{cert['laps']}周（見積り {cert.get('est_laps')}）、山札の差分Δ {cert['deltas']}、"
            f"最小盤面M {cert['M']}、起点 {cert['origin']}、seed {cert['seed']}")


def certify_and_submit(rules, *, id: str, name: str, core: list[dict], origin: str, bz=(), graveyard=(), hand=(),
                       mana: int = 5, seed: int = 1, note: str = "", path=registry.PATH, root: Path = REPO, **kw):
    """証明書を作り、回帰があれば submit_board で登録へ渡す。戻り: (証明書, Evidence か None, 登録簿の行か None)。"""
    entry, _ = S.build_entry(rules, id=id, name=name, core=core, bz=bz, graveyard=graveyard, hand=hand, mana=mana,
                             note=note, root=root)
    cert = make_certificate(rules, origin=origin, bz=bz, graveyard=graveyard, hand=hand, seed=seed, entry_json=entry, root=root)
    if cert["kind"] == "none":
        return cert, None, None
    ev, row = S.submit_board(rules, id=id, name=name, core=core, bz=bz, graveyard=graveyard, hand=hand, mana=mana,
                             note=(note + " " + certificate_note(cert)).strip(), certificate=cert, path=path, root=root, **kw)
    return cert, ev, row
