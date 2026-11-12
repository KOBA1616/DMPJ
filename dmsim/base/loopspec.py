"""LoopSpec: 発見したループを、再利用できるデータとして持つ。

- 最小盤面 M: ゾーン × 所有者 × カードの区分 × 個数の下限、の述語の集合（Pred）。
- 1周の差分 delta: 骨格が戻るループでの、カウンタ（枚数）の1周あたりの変化（loop.LoopCertificate と同じ表現）。
- 種別 kind:
    deterministic  毎周の結果が決まっていて、delta × N で効果が見積もれる。
    reroll         毎周の結果が運任せ（ドローなど）。M は維持されるが自由な部分（手札・山札）が変わる。
                   停止条件 G に達するか、山札の下限に達するまで繰り返す（競技ルール 4.4: 望む結果まで省略できる）。
- 弱点 hazards: そのループが妨害に弱い種類（attack / counter / hand_disrupt など）。相手モデルの下での頑健性は
  別に保存し、ここには「事実」だけを置く（相手モデルを変えてもループ発見をやり直さない）。
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from math import comb

KINDS = ("deterministic", "reroll")
OPS = (">=", "<=", "==")


@dataclass(frozen=True)
class Pred:
    """zone にいる owner（0=自分, 1=相手）のカードのうち match に合うものの枚数が、op n を満たす。
    match は {"name": カードID} または {"types": [...]} / {"civs": [...]} / {"races": [...]}（どれか1つ以上）。
    zones は「どのゾーンでもよい」場合の候補（手札か墓地にもう1枚、など）。zone と排他。"""
    owner: int
    match: dict
    n: int = 1
    op: str = ">="
    zone: str | None = None
    zones: tuple[str, ...] = ()

    def __post_init__(self):
        if self.op not in OPS:
            raise ValueError(f"unknown op {self.op}")
        if (self.zone is None) == (not self.zones):
            raise ValueError("zone か zones のどちらか一方を指定する")
        if not self.match:
            raise ValueError("match が空")


@dataclass(frozen=True)
class Route:
    """入口 M に至る経路（到達条件）。M そのものではなく「どうやって M を作るか」。
    例: 手札のサガをコスト3の水・闇で出す → Route("cast", {"name": サガ}, from_zone="hand", cost=3, civs=("water", "darkness"))。
    場に最初からある場合は経路が要らない（routes を空にする）。"""
    name: str
    card: dict                             # 出すカードの match（Pred.match と同じ形）
    from_zone: str = "hand"
    cost: int = 0                          # 必要な合計マナ（アンタップ）
    civs: tuple[str, ...] = ()             # マナゾーンに揃っているべき文明（各1枚以上）


@dataclass
class LoopSpec:
    name: str
    kind: str
    minimal: list[Pred]
    delta: dict[str, int] = field(default_factory=dict)
    limit: float | None = None            # 周回上限（None は無限）
    goal: list[Pred] = field(default_factory=list)   # reroll の停止条件 G（満たすまで繰り返す）
    deck_floor: int = 1                    # reroll: 自分の山札がこの枚数以下になったら打ち切る（山札切れ負けの回避）
    hazards: list[str] = field(default_factory=list)
    routes: list[Route] = field(default_factory=list)   # M への到達経路（どれか1つでよい）。空なら最初から M にある
    source: dict = field(default_factory=dict)       # 発見の出典: seed、エンジン版、カード定義のハッシュなど

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"unknown kind {self.kind}")
        if self.kind == "reroll" and not self.goal:
            raise ValueError("reroll には停止条件 goal が要る")

    def to_json(self) -> str:
        d = asdict(self)
        for key in ("minimal", "goal"):
            d[key] = [{**p, "zones": list(p["zones"])} for p in d[key]]
        if d["limit"] is not None and d["limit"] == float("inf"):
            d["limit"] = None
        d["routes"] = [{**r, "civs": list(r["civs"])} for r in d["routes"]]
        return json.dumps(d, ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_json(cls, s: str) -> "LoopSpec":
        d = json.loads(s)
        for key in ("minimal", "goal"):
            d[key] = [Pred(**{**p, "zones": tuple(p.get("zones") or ())}) for p in d[key]]
        d["routes"] = [Route(**{**r, "civs": tuple(r.get("civs") or ())}) for r in d.get("routes", [])]
        return cls(**d)


def hit_prob_within(deck_n: int, hits: int, draws: int) -> float:
    """山札 deck_n 枚のうち欲しいカードが hits 枚あるとき、上から draws 枚を引いて少なくとも1枚が当たる確率（超幾何）。"""
    if draws <= 0 or hits <= 0 or deck_n <= 0:
        return 0.0
    draws = min(draws, deck_n)
    if deck_n - hits < draws:
        return 1.0
    return 1.0 - comb(deck_n - hits, draws) / comb(deck_n, draws)


def reroll_success_prob(spec: LoopSpec, deck_n: int, hits: int) -> float:
    """再抽選型ループが、山札の下限に達する前に欲しいカード（hits 枚）を1枚以上引ける確率。
    1周で1枚引くなら、使える周回数は deck_n - deck_floor。複数の目標が要る場合は呼び出し側で組み合わせる。"""
    return hit_prob_within(deck_n, hits, deck_n - spec.deck_floor)


def none_of(deck_n: int, hits: int, draws: int) -> float:
    """山札 deck_n 枚のうち hits 枚が「当たり」のとき、上から draws 枚に当たりが1枚も無い確率。"""
    draws = min(draws, deck_n)
    return comb(deck_n - hits, draws) / comb(deck_n, draws) if deck_n - hits >= draws else 0.0


def all_civs_prob(deck_civs: list[frozenset], need: tuple[str, ...], draws: int) -> float:
    """山札（各カードの文明の集合の並び）の上から draws 枚に、need の文明がそれぞれ1枚以上含まれる確率（厳密。包含と排除）。
    多色カードは複数の文明に数える。"""
    n = len(deck_civs)
    total = 0.0
    k = len(need)
    for mask in range(1 << k):
        sub = {need[i] for i in range(k) if mask >> i & 1}
        hits = sum(1 for c in deck_civs if c & sub)
        total += (-1) ** len(sub) * (1.0 if not sub else none_of(n, hits, draws))
    return total


def route_prob(route: Route, deck_civs: list[frozenset], copies: int, draws: int, mana_cards: int | None = None) -> float:
    """経路が使える確率の近似: P(出すカードが引ける) × P(必要な文明が揃う) × P(マナが cost 枚以上引ける)。
    三者を独立とみなす近似（互いに同じ山札から引くので、厳密な同時確率とは少しずれる）。
    mana_cards は山札のうちマナに置けるカードの枚数（既定は山札の全て）。"""
    n = len(deck_civs)
    p_card = hit_prob_within(n, copies, draws)
    p_civ = all_civs_prob(deck_civs, route.civs, draws) if route.civs else 1.0
    m = n if mana_cards is None else mana_cards
    p_mana = 1.0 - sum(comb(m, j) * comb(n - m, draws - j) for j in range(min(route.cost, draws + 1))
                       if draws - j >= 0 and n - m >= draws - j) / comb(n, min(draws, n)) if route.cost else 1.0
    return p_card * p_civ * p_mana
