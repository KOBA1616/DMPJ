"""指定した配置から始まる局面（シナリオ）を作る。テストと開発者モードで共用する。

spec = {"p0": {ゾーン名: [カードID, ...]}, "p1": {...}, "filler": "T001", "seed": 1,
        "deck_size": 20, "deck_left": [None, None]}

- 残りの山札は filler で埋める。shield を指定しなければ filler を5枚置く。
- バトルゾーンに置いたクリーチャーは召喚酔いなし。
- 先攻（プレイヤー0）1ターン目のはじめから始まる（最初の Decision はマナチャージ）。
同じ spec からは必ず同じ局面になるので、spec＋選択ログで対戦を再現できる。
"""
from __future__ import annotations

from .engine import Engine


def build(rules, spec: dict, **kw) -> Engine:
    p_specs = (spec.get("p0") or {}, spec.get("p1") or {})
    filler = spec.get("filler", "T001")
    deck_size = spec.get("deck_size", 20)
    deck_left = spec.get("deck_left")
    decks = [[c for z in ps.values() for c in z] + [filler] * deck_size for ps in p_specs]
    e = Engine.new_game(rules, decks, spec.get("seed", 1), **kw)
    s = e.s
    # 準備で配られた手札とシールドを山札に戻し、指定どおりに置き直す
    for p, ps in enumerate(p_specs):
        for z in ("hand", "shield"):
            for c in list(s.zones[z][p]):
                e._raw_move(c, "deck")
        pool = list(s.zones["deck"][p])
        for z, ids in ps.items():
            if z not in rules.zones:
                raise KeyError(f"unknown zone {z}")
            for name in ids:
                cid = next(c for c in pool if s.cards[c].defn == name)
                pool.remove(cid)
                e._raw_move(cid, z, controller=p)
                if z == "bz":
                    s.cards[cid].entered_turn = 0   # 召喚酔いなし
        if "shield" not in ps:
            for _ in range(5):
                c = next(c for c in s.zones["deck"][p] if s.cards[c].defn == filler)
                e._raw_move(c, "shield")
        if deck_left and deck_left[p] is not None:
            for c in list(s.zones["deck"][p])[deck_left[p]:]:
                e._raw_move(c, "graveyard")
    s.deck_emptied = [p for p in (0, 1) if not s.zones["deck"][p]]   # 組み立て途中の0枚は数えない
    return e


def try_card(rules, card_id: str, filler: str = "T001") -> dict:
    """カード1枚を試すためのシナリオ: 手札にそのカード、払えるだけのマナ、相手の場にクリーチャー2体。
    進化・宣言（革命チェンジ等）を持つカードは、条件に合う自分のクリーチャーを1体バトルゾーンに置く。
    細かい局面は開発者モードでこの spec を書き換えて作る。"""
    d = rules.cards[card_id]
    mono = {}
    for cd in rules.cards.values():
        if len(cd.civs) == 1 and cd.mana == 1 and cd.source:      # 実カードの単色をマナ用に使う
            mono.setdefault(cd.civs[0], cd.id)
    civs = [c for c in d.civs if c in mono] or [next(iter(mono))]
    cost = max([d.cost] + [f.cost for f in d.faces])
    mana = [mono[civs[i % len(civs)]] for i in range(max(cost, len(civs)))]
    creatures = [cd.id for cd in rules.cards.values()
                 if cd.source and "creature" in cd.types and "evolution" not in cd.types and not cd.faces]
    spec = {"p0": {"hand": [card_id], "mana": mana}, "p1": {"bz": creatures[:2]}, "filler": filler, "seed": 1}
    wants = [f.evolve_from for f in (d.faces or [d]) if "evolution" in f.types and f.evolve_from is not None]
    wants += [ab["when"]["subject"].get("filter", {}) for f in (d.faces or [d]) for ab in f.abilities
              if ab["kind"] == "declare" and isinstance(ab.get("when", {}).get("subject"), dict)]
    if wants:
        probe = build(rules, {"p0": {"bz": [c for c in creatures if c != card_id]}, "filler": filler})
        for w in wants:
            hit = next((probe.s.cards[c].defn for c in probe.bz_tops(0) if probe.filter_match(c, w)), None)
            if hit:
                spec["p0"]["bz"] = [hit]
                break
    return spec
