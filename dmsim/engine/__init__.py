"""ルールエンジン。

core.py        Engine 本体（進行ループ・Decision の出し入れ・状態ヘルパ）
registry.py    拡張ポイント（task / op の登録表）
selectors.py   セレクタ・式・条件
events.py      イベント・パイプライン、誘発、待機と解決窓
interpreter.py 効果DSLの実行
ops.py         効果DSLのコア語彙
turn.py        ターン構造とカードの実行
combat.py      攻撃・ブロック・バトル・ブレイク
state.py       ゲーム状態（純データ）と決定的な乱数
view.py        読み取り専用アクセサ / api.py エンジン窓口 engine/api
scenario.py    局面の組み立て / verify.py・effectcheck.py 効果の検証
loop.py        ループ・ロック検出 / zone_graph.py ゾーン移動グラフ / rustcore.py Rust コアとの橋渡し
play.py        1局の最小進行・既定方策・記録と再生

import してよいのは dmsim.base（S0）と dmsim.cards（S1）だけ。旧名 dmsim.state などは同じモジュールを指す別名として残してある。
"""
from . import ops  # noqa: F401  op を登録する
from .core import Engine, IllegalAnswer
from .registry import OPS, TASKS

__all__ = ["Engine", "IllegalAnswer", "OPS", "TASKS"]
