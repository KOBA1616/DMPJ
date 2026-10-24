"""拡張ポイントの登録表。

- TASKS: 処理スタック上のタスク種別 → ハンドラ (eng, task) -> Decision | None
- OPS:   効果DSLの op 名 → ハンドラ (eng, task, op, env) -> Decision | None
新しいルール手順はタスクとして、新しい効果の動詞は op として登録する。エンジン本体は変更しない。
defs.py の語彙検証は OPS のキーを正とするので、登録すればそのまま YAML で使える。
"""
from __future__ import annotations

TASKS: dict = {}
OPS: dict = {}


def task(name: str):
    def deco(fn):
        if name in TASKS:
            raise ValueError(f"task '{name}' already registered")
        TASKS[name] = fn
        return fn
    return deco


def op(name: str):
    def deco(fn):
        if name in OPS:
            raise ValueError(f"op '{name}' already registered")
        OPS[name] = fn
        return fn
    return deco
