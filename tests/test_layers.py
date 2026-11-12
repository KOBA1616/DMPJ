"""層の向きテスト（ロードマップ P0-1）。import は上の層から下の層への一方向だけを許す。

S0 共通基盤 ← S1 カードデータ ← S2 ゲームエンジン ← S3 探索・プレイ ← S4 評価 ← S5 発見 ← S6 学習・改善 ← APP（画面・開発用サーバ）
同じ層どうしは可。ファイル配置はまだ動かしていないので、層はモジュール名の前方一致で対応づける（長い方を優先）。
新しいモジュールを足したら LAYER_OF にも足すこと（未登録はテストが失敗する）。
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "dmsim"
ORDER = ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "APP"]

LAYER_OF = {
    # S0 共通基盤: 型・ID・記録の形
    "dmsim.base": "S0",                    # 定義元（P1: types・cardid・loopspec をここへ集めた）
    "dmsim.types": "S0",                   # 旧名の互換（dmsim.base.types と同じモジュール）
    "dmsim.cardid": "S0",                  # 旧名の互換（dmsim.base.cardid と同じモジュール）
    "dmsim.discovery.loopspec": "S0",      # 旧名の互換（dmsim.base.loopspec と同じモジュール）
    # S1 カードデータ
    "dmsim.defs": "S1",
    "dmsim.canonical": "S1",
    "dmsim.cardfiles": "S1",
    "dmsim.cardstore": "S1",
    "dmsim.approval": "S1",
    "dmsim.identity": "S1",
    "dmsim.schema": "S1",
    "dmsim.dataaudit": "S1",
    # S2 ゲームエンジン
    "dmsim": "S2",                         # パッケージ直下 __init__（load_rules と Engine の再公開）
    "dmsim.engine": "S2",
    "dmsim.state": "S2",
    "dmsim.engine_view": "S2",
    "dmsim.engine_api": "S2",
    "dmsim.scenario": "S2",
    "dmsim.verify": "S2",
    "dmsim.effectcheck": "S2",
    "dmsim.loop": "S2",
    "dmsim.rustcore": "S2",
    "dmsim.zone_graph": "S2",
    "dmsim.play": "S2",                    # 1局を回す最小の進行と既定方策（passive/random）。窓口 play/api(S3) は後の手順
    # S3 探索・プレイ（大局観を含む）
    "dmsim.play_api": "S3",                # 探索・プレイの窓口 play(局面, 設定, 情報水準)（P0-2）
    "dmsim.opponent": "S3",
    "dmsim.loop_first": "S3",
    "dmsim.search": "S3",
    "dmsim.plan": "S3",
    "dmsim.discovery.bestfirst": "S3",     # 汎用の最良優先・ビーム探索（search/ へ移す予定）
    "dmsim.discovery.reachsearch": "S3",   # 段階目標への到達探索 reach_chain（search/ へ移す予定）
    # S4 評価
    "dmsim.eval": "S4",
    "dmsim.solitaire": "S4",              # 旧名の互換モジュール（search/turn・leaf_eval・game と eval/measure を再エクスポート、P0-3）
    "dmsim.pool_metrics": "S4",
    # S5 発見（デッキ構築を含む）
    "dmsim.discovery": "S5",
    "dmsim.combo_search": "S5",
    "dmsim.deckplan": "S5",
    # S6 学習・改善
    "dmsim.autofix": "S6",
    # 画面・開発用
    "dmsim.devserver": "APP",
    "dmsim.playback": "APP",
}

# 今回解消できなかった逆流: (import する側, される側) → 理由
ALLOWED = {
    ("dmsim.defs", "dmsim.engine.registry"): "core_ops はエンジンの op 語彙を読む（遅延 import）。語彙の正本を S2 engine/vocab に分ける手順で解消",
    ("dmsim.defs", "dmsim.engine.ops"): "同上（op 登録を確実にするための import）",
    ("dmsim.deckplan.auto", "dmsim.autofix.usage"): "使われにくい札の監査 collect_usage が autofix にある（遅延 import）。usage 監査を S4 へ移す手順で解消",
    ("dmsim.plan.macro", "dmsim.eval.vfeatures"): "旧名 plan.macro.macro_prio の互換（モジュール __getattr__ の遅延 import のみ）。呼び出し側の移行後に削除",
}


def _modules():
    for p in sorted(ROOT.rglob("*.py")):
        parts = p.relative_to(ROOT.parent).with_suffix("").parts
        is_pkg = parts[-1] == "__init__"
        mod = ".".join(parts[:-1] if is_pkg else parts)
        yield p, mod, (mod if is_pkg else mod.rsplit(".", 1)[0])


def _targets(node, pkg):
    if isinstance(node, ast.Import):
        return [a.name for a in node.names]
    if isinstance(node, ast.ImportFrom):
        if node.level:
            base = pkg.split(".")[: len(pkg.split(".")) - (node.level - 1)]
            m = ".".join(base + ([node.module] if node.module else []))
        else:
            m = node.module or ""
        return [f"{m}.{a.name}" for a in node.names]
    return []


def layer(mod: str) -> str | None:
    best = None
    for k in LAYER_OF:
        if (mod == k or mod.startswith(k + ".")) and (best is None or len(k) > len(best)):
            best = k
    return LAYER_OF[best] if best else None


def _known(name: str, mods: set) -> str | None:
    """import 先の名前 → 実在するモジュール名（from X import 関数 は X に丸める）。"""
    while name:
        if name in mods:
            return name
        name = name.rpartition(".")[0]
    return None


def edges():
    mods = {m for _, m, _ in _modules()}
    out = set()
    for p, mod, pkg in _modules():
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            for t in _targets(n, pkg):
                k = _known(t, mods) if t.startswith("dmsim") else None
                if k and k != mod:
                    out.add((mod, k))
    return out


def test_every_module_has_a_layer():
    missing = [m for _, m, _ in _modules() if layer(m) is None]
    assert not missing, f"LAYER_OF に層が無い: {missing}"


def test_imports_point_downward_only():
    bad = []
    for a, b in sorted(edges()):
        la, lb = layer(a), layer(b)
        if ORDER.index(lb) > ORDER.index(la) and (a, b) not in ALLOWED:
            bad.append(f"{a}({la}) -> {b}({lb})")
    assert not bad, "上の層への import（逆流）:\n" + "\n".join(bad)


def test_allowlist_is_not_stale():
    es = edges()
    stale = [k for k in ALLOWED if k not in es or ORDER.index(layer(k[1])) <= ORDER.index(layer(k[0]))]
    assert not stale, f"もう不要な許可: {stale}"


def test_base_imports_no_other_layer():
    """S0 の定義元 dmsim.base は他の層（dmsim.base 以外の dmsim.*）を import しない。"""
    bad = sorted(f"{a} -> {b}" for a, b in edges() if (a == "dmsim.base" or a.startswith("dmsim.base."))
                 and not (b == "dmsim.base" or b.startswith("dmsim.base.")))
    assert not bad, bad


def test_old_names_are_the_same_module():
    """旧名は定義元と同一オブジェクト（旧名への monkeypatch が定義元に効く）。"""
    import importlib
    for old, new in [("dmsim.types", "dmsim.base.types"), ("dmsim.cardid", "dmsim.base.cardid"),
                     ("dmsim.discovery.loopspec", "dmsim.base.loopspec")]:
        assert importlib.import_module(old) is importlib.import_module(new)
