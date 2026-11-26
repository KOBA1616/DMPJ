"""閉路（zone_graph.Cycle）から、そのループを回せる仕込み局面（dmsim.scenario の spec）を作る。
候補の組に部品表（手書きの仕込み）が無くても、実行層（仕込み済み開始からの測定）にかけるための生成器。

配り方（各カードが起動前提を満たせる場所に置く）:
  自分から起動する（prem なし）・呪文・召喚 → 手札
  場に出た時などの誘発（prem.zone が bz）  → 手札（出す操作が最初の一手になる）
  墓地・マナなど、そのゾーンで働く誘発      → そのゾーン
  動かし元が墓地・マナの効果（回収・蘇生）は、そのゾーンに身代わりのカードを1枚足す
マナは必要な文明を覆う単色カードを mana_n 枚（コストの最大に合わせる）。"""
from __future__ import annotations

FILLER = "T013"


def mono_mana(rules) -> dict[str, str]:
    mono: dict[str, str] = {}
    for cd in rules.cards.values():
        if len(cd.civs) == 1 and cd.mana == 1 and cd.source:
            mono.setdefault(cd.civs[0], cd.id)
    return mono


def setup_from_cycle(rules, cycle, mana_n: int | None = None, opp_mana: int = 6, opp_deck: int = 30) -> dict:
    zones: dict[str, list[str]] = {"hand": [], "graveyard": [], "mana": [], "bz": []}
    civs: list[str] = []
    cost = 0
    placed: set = set()
    for b in cycle.bundles:
        if b.card in placed:            # 1枚の札が複数の束を持つ（誘発が2つ等）。仕込みは1枚だけ
            continue
        placed.add(b.card)
        cd = rules.cards[b.card]
        for v in cd.civs:
            if v not in civs:
                civs.append(v)
        cost = max(cost, cd.cost)
        z = "hand"
        if b.prem is not None and b.origin == "trigger" and b.prem.zone not in ("bz", "hand"):
            z = b.prem.zone
        zones.setdefault(z, []).append(b.card)
        for m in b.moves:                       # 回収・蘇生・マナからの移動は、元のゾーンに種札が要る
            if m.owner != "opp" and m.from_any("graveyard", "mana") and not m.ref_self and not m.blind:
                # src がリストなら候補のうち種札が要るゾーン（先頭の該当）に置く
                zones.setdefault(next(z for z in m.src_zones()
                                      if z in ("graveyard", "mana")), []).append(FILLER)
    mono = mono_mana(rules)
    n = mana_n if mana_n is not None else max(cost, len(civs), 4)
    cov = [mono[c] for c in civs if c in mono] or [next(iter(mono.values()))]
    mana = zones.pop("mana", []) + [cov[i % len(cov)] for i in range(n)]
    spec = {"p0": {k: v for k, v in zones.items() if v} | {"mana": mana}, "p1": {"mana": ["T001"] * opp_mana},
            "deck_size": opp_deck, "shuffle_deck": True}
    return spec
