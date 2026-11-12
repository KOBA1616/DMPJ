"""拡張ポイントの登録表。

- TASKS: 処理スタック上のタスク種別 → (ハンドラ (eng, task) -> Decision | None, 形の TypedDict)
- OPS:   効果DSLの op 名 → ハンドラ (eng, task, op, env) -> Decision | None
- OP_ARGS: op 名 → 引数の型。正本は base/opvocab.py（defs.py の検証と JSON Schema の生成はそちらを読む）
- STEPS: ターンのステップ名 → ハンドラ (eng, turn_task) -> Decision | None
新しいルール手順はタスクとして、新しい効果の動詞は op として、新しいステップは step として登録する。
エンジン本体は変更しない。defs.py の語彙検証は base/opvocab.py の OP_ARGS を正とする。新しい op はそこに型を足してから登録する。

op の引数の型（末尾 ? は省略可）:
  selector, zone, reason, expr, cond, ops, player, mod, duration, position, step, str, int, bool, any
"""
from __future__ import annotations

# op の語彙（名前と引数の型）の正本は S0 の base/opvocab.py。OP_ARGS は同じ dict を指す別名。
from ..base.opvocab import ARG_TYPES, OP_ARGS  # noqa: F401
from ..base.opvocab import declare as _declare_op

TASKS: dict = {}
TASK_SHAPES: dict = {}
OPS: dict = {}
STEPS: dict = {}


def task(name: str, shape=None):
    def deco(fn):
        if name in TASKS:
            raise ValueError(f"task '{name}' already registered")
        TASKS[name] = fn
        TASK_SHAPES[name] = shape
        return fn
    return deco


def op(op_name: str, /, **args: str):
    """args は引数名=型。例: @op("draw", player="player?", count="expr?")"""
    name = op_name
    for k, v in args.items():
        if v.rstrip("?") not in ARG_TYPES:
            raise ValueError(f"op '{name}': unknown arg type '{v}' for '{k}'")

    def deco(fn):
        if name in OPS:
            raise ValueError(f"op '{name}' already registered")
        _declare_op(name, args)
        OPS[name] = fn
        return fn
    return deco


def step(name: str):
    def deco(fn):
        if name in STEPS:
            raise ValueError(f"step '{name}' already registered")
        STEPS[name] = fn
        return fn
    return deco


def read_only(fn):
    """状態を読むだけのメソッド: 呼び出しの間は chars() の結果を使い回す（chars_scope）。状態を書き換える処理を呼んではならない。"""
    import functools

    @functools.wraps(fn)
    def w(self, *a, **k):
        with self.chars_scope():
            return fn(self, *a, **k)
    return w
