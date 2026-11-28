"""ループの起点（合成手の始まりの選択）を盤面から自動で取る。札名・キーは書かない（2026-11-28）。

最初の攻撃選択（攻撃を先に）と、最初の main 選択の play: 行動を、その時点のエンジンの複製つきで返す。
known_loops（再発見率）と discovery/pipeline（候補→証明書→登録）の両方がこれを使う。"""
from __future__ import annotations


def auto_origins(eng, steps: int = 60, me: int = 0) -> list[tuple]:
    """pass を選びながら進め、[(その時点のエンジン, 起点キー), ...] を返す（攻撃が先、次にメインの play:）。"""
    mains, atk = [], []
    for _ in range(steps):
        d = eng.advance()
        if d is None or eng.s.result:
            break
        ks = [o["key"] for o in d["options"]]
        if d["player"] == me and d["kind"] == "main" and not mains:
            mains = [(eng.clone(), k) for k in ks if k.startswith("play:")]
        if d["player"] == me and d["kind"] == "attack":
            atk = [(eng.clone(), k) for k in ks if k.startswith("attack:")][:1]
            break
        eng.answer([ks.index("pass") if "pass" in ks else 0])
    return atk + mains


def origin_key(origin: str) -> str:
    """札 ID だけ渡された時は攻撃の起点キーにする。キー（':' を含む）はそのまま。"""
    return origin if ":" in origin else f"attack:{origin}:player"
