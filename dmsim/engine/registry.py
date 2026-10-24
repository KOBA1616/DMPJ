"""拡張ポイントの登録表。

- TASKS: 処理スタック上のタスク種別 → (ハンドラ (eng, task) -> Decision | None, 形の TypedDict)
- OPS:   効果DSLの op 名 → ハンドラ (eng, task, op, env) -> Decision | None
- OP_ARGS: op 名 → 引数の型（defs.py の検証と JSON Schema の生成に使う）
- STEPS: ターンのステップ名 → ハンドラ (eng, turn_task) -> Decision | None
新しいルール手順はタスクとして、新しい効果の動詞は op として、新しいステップは step として登録する。
エンジン本体は変更しない。defs.py の語彙検証は OPS / OP_ARGS を正とするので、登録すればそのまま YAML で使える。

op の引数の型（末尾 ? は省略可）:
  selector, zone, reason, expr, cond, ops, player, mod, duration, position, step, str, int, bool, any
"""
from __future__ import annotations

TASKS: dict = {}
TASK_SHAPES: dict = {}
OPS: dict = {}
OP_ARGS: dict[str, dict[str, str]] = {}
STEPS: dict = {}

ARG_TYPES = {"selector", "zone", "reason", "expr", "cond", "ops", "player", "mod", "duration",
             "position", "step", "str", "int", "bool", "any", "ability"}


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
        OPS[name] = fn
        OP_ARGS[name] = dict(args)
        return fn
    return deco


def step(name: str):
    def deco(fn):
        if name in STEPS:
            raise ValueError(f"step '{name}' already registered")
        STEPS[name] = fn
        return fn
    return deco
