"""計画の部品札（段階目標に出てくる札）を、マナに置いてしまうことへの減点。v_priority の `terms` に渡す (eng, me) -> 加点 の関数。
天門の測定（2026-11-10）: 探索はコスト9のミルザムをマナに置いて使い切り、連鎖の続きが消えていた。
減点（300/枚）を入れると、3枚強制の開始で 12 seed 中 7 が 4 段（天門が盾の中→エメラルーダ登場で天門が墓地→ミルザム登場→盾の下5枚）を最速の通しターン9〜12 で完遂（入れない時は 1）。足切りには使わず順位づけのみ。"""
from __future__ import annotations


def stage_ids(stages) -> set:
    """段階目標（{ゾーン: {ID: 枚数}} の列）に出てくるカード定義 ID（"*" 除く）。"""
    return {i for st in stages for want in st.values() for i in want if i != "*"}


def key_in_mana_penalty(eng, me: int, ids, pen: float = 300.0) -> float:
    return -pen * sum(1 for c in eng.zlist("mana", me) if eng.s.cards[c].defn in ids)


def make_term(stages, pen: float = 300.0):
    ids = stage_ids(stages)
    return lambda eng, me: key_in_mana_penalty(eng, me, ids, pen)
