"""ルールエンジン。

core.py        Engine 本体（進行ループ・Decision の出し入れ・状態ヘルパ）
registry.py    拡張ポイント（task / op の登録表）
selectors.py   セレクタ・式・条件
events.py      イベント・パイプライン、誘発、待機と解決窓
interpreter.py 効果DSLの実行
ops.py         効果DSLのコア語彙
turn.py        ターン構造とカードの実行
combat.py      攻撃・ブロック・バトル・ブレイク
"""
from . import ops  # noqa: F401  op を登録する
from .core import Engine, IllegalAnswer
from .registry import OPS, TASKS

__all__ = ["Engine", "IllegalAnswer", "OPS", "TASKS"]
