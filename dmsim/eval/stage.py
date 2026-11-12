"""段階指標の共通部品。探索葉の部品スコア（search/leaf_parts）と評価の段階指標（eval/progress）が同じ数え方を使う。

- zone_counts      : 自分側ゾーンの {定義ID: 枚数}
- count_matching   : ゾーン内で ids のどれか（空ならクリーチャー全般）に当たる枚数
- board_met        : 最小盤面 {zone: {id: n}} を全部満たすか
- cards_met        : 必要カード {id: n} が見えるゾーン（山札・盾以外）にそろったか
- parts_to_cards   : 部品表（zone/ids/need を持つ列）→ 必要カード {id: n}（評価側の cards に使える）
山札・盾の中身は公開情報ではないので VISIBLE_ZONES に含めない。
"""
from __future__ import annotations

from ..engine_view import (VISIBLE_ZONES, board_met, cards_met, count_matching,  # noqa: F401  旧名の再公開（実体は engine_view）
                           defn_of, zone_counts)


def parts_to_cards(parts) -> dict:
    """部品（zone, ids, need）の列 → {id: 必要枚数}。ids が空の部品（クリーチャー全般）は除く。同じ id は最大の need をとる。"""
    out: dict = {}
    for p in parts:
        for i in p.ids:
            out[i] = max(out.get(i, 0), p.need)
    return out
