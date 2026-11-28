"""段2の自動化: ループの1周ごとの蓄積から、勝ちに変えられる札をカードプールから選び、候補に足して測る（2026-11-28）。

流れ: 証明書の周ごとのゾーン増減（certify.zone_deltas）→ 蓄積 {(owner, zone): 増減}（loop_gains）→ 索引（gain_index）で
勝ち手段を引く（pick_wins。物差しの段2に数えられる札 triples.win_cards だけ、中核の文明に収まる札を先に、コストの軽い順）→
中核に part: win として足して certify.certify_and_submit で登録（run_stage2）。札名は決め打ちしない。
勝ち方は山札切れ・シールド・ターンをまたぐロックなど、索引が引く効果の形による。自分の山札切れで負けた局は段2に数えない（ruler 側）。
"""
from __future__ import annotations

from ..base import registry
from . import basebuild as B
from . import certify as Z
from . import gain_index as G
from . import triples as X


def loop_gains(cert: dict) -> dict:
    """証明書の、回帰が続く周（最後の周）の各ゾーンの増減。{(owner, zone): 増減}。0 は含めない。"""
    zd = cert.get("zone_deltas") or []
    if not zd:
        return {}
    last = zd[-1]
    return {(who, z): v for who, zs in last.items() for z, v in zs.items() if v}


def pick_wins(rules, gains: dict, core_ids, *, top: int = 3, idx=None, wins=None, raw=None) -> list[dict]:
    """蓄積を勝ちに変えられる札を、索引の当たりの多い順（同じなら軽い順）に top 枚。中核の文明に収まる札を先に（収まらない札は文明を足して試す）。"""
    raw = raw if raw is not None else B._raw_cards(rules)
    idx = idx if idx is not None else G.build(rules)
    wins = wins if wins is not None else X.win_cards(rules, raw)
    core = {i: B.COPIES for i in core_ids}
    civs = B.core_civs(rules, core)
    out = []
    for h in G.lookup(idx, gains, rules, top=0):
        c = rules.cards[h["id"]]
        if h["id"] in core_ids or h["id"] not in wins or h["id"].startswith(("T", "R", "L")):
            continue
        out.append(dict(h, extra_civs=len(set(c.civs) - {"zero"} - civs)))
    out.sort(key=lambda h: h["extra_civs"])    # 中核の文明に収まる札を先に（収まらない札も、文明を足したデッキで試す）
    return out[:top]


def run_stage2(rules, *, id: str, name: str, core: list[dict], origin: str, bz=(), graveyard=(), hand=(), top: int = 3,
               max_turn: int = 4, path=registry.PATH, root=Z.REPO, log=print, **kw) -> list[dict]:
    """証明書を作り、その蓄積で引いた勝ち手段ごとに候補を作って登録する。戻り: 各候補 {win, name, cert, ev, row}。"""
    entry, _ = Z.S.build_entry(rules, id=id, name=name, core=core, bz=bz, graveyard=graveyard, hand=hand, root=root)
    cert = Z.make_certificate(rules, origin=origin, bz=bz, graveyard=graveyard, hand=hand, entry_json=entry, root=root)
    gains = loop_gains(cert)
    log(f"証明書 {cert['kind']} {cert['laps']}周 蓄積 {gains}")
    out = []
    for n, h in enumerate(pick_wins(rules, gains, [c["id"] for c in core], top=top), 1):
        c2 = core + [{"id": h["id"], "role": "勝ち手段（段2の自動選択）: " + "、".join(h["why"]), "part": "win"}]
        _, ev, row = Z.certify_and_submit(rules, id=f"{id}_w{n}", name=f"{name} + {h['name']}", core=c2, origin=origin, bz=bz,
                                          graveyard=graveyard, hand=hand, max_turn=max_turn, path=path, root=root, **kw)
        log(f"  {h['id']} {h['name']}: {ev.passed if ev else None} {[c['detail'] for c in (ev.checks if ev else [])][-1:]}")
        out.append({"win": h["id"], "name": h["name"], "ev": ev, "row": row})
    return out
