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
    "dmsim.cards": "S1",                   # 定義元（P1: defs・canonical・cardfiles・cardstore・approval・identity・schema・dataaudit）
    "dmsim.defs": "S1",              # 旧名の互換（dmsim.cards.defs と同じモジュール）
    "dmsim.canonical": "S1",         # 旧名の互換（dmsim.cards.canonical と同じモジュール）
    "dmsim.cardfiles": "S1",         # 旧名の互換（dmsim.cards.cardfiles と同じモジュール）
    "dmsim.cardstore": "S1",         # 旧名の互換（dmsim.cards.cardstore と同じモジュール）
    "dmsim.approval": "S1",          # 旧名の互換（dmsim.cards.approval と同じモジュール）
    "dmsim.identity": "S1",          # 旧名の互換（dmsim.cards.identity と同じモジュール）
    "dmsim.schema": "S1",            # 旧名の互換（dmsim.cards.schema と同じモジュール）
    "dmsim.dataaudit": "S1",         # 旧名の互換（dmsim.cards.dataaudit と同じモジュール）
    # S2 ゲームエンジン
    "dmsim": "S2",                         # パッケージ直下 __init__（load_rules と Engine の再公開）
    "dmsim.engine": "S2",                  # 定義元（P1: state・view・api・scenario・verify・effectcheck・loop・rustcore・zone_graph・play）
    "dmsim.state": "S2",             # 旧名の互換（dmsim.engine.state と同じモジュール）
    "dmsim.engine_view": "S2",       # 旧名の互換（dmsim.engine.view と同じモジュール）
    "dmsim.engine_api": "S2",        # 旧名の互換（dmsim.engine.api と同じモジュール）
    "dmsim.scenario": "S2",          # 旧名の互換（dmsim.engine.scenario と同じモジュール）
    "dmsim.verify": "S2",            # 旧名の互換（dmsim.engine.verify と同じモジュール）
    "dmsim.effectcheck": "S2",       # 旧名の互換（dmsim.engine.effectcheck と同じモジュール）
    "dmsim.loop": "S2",              # 旧名の互換（dmsim.engine.loop と同じモジュール）
    "dmsim.rustcore": "S2",          # 旧名の互換（dmsim.engine.rustcore と同じモジュール）
    "dmsim.zone_graph": "S2",        # 旧名の互換（dmsim.engine.zone_graph と同じモジュール）
    "dmsim.play": "S2",              # 旧名の互換（dmsim.engine.play と同じモジュール。1局の最小進行と既定方策）
    # S3 探索・プレイ（大局観を含む）
    "dmsim.play_api": "S3",                # 探索・プレイの窓口 play(局面, 設定, 情報水準)（P0-2）
    "dmsim.search": "S3",                  # 定義元（P1-S3: 1ターン・公平・複数ターン探索、相手役 opponent、loop_first、bestfirst、reachsearch）
    "dmsim.plan": "S3",                    # 大局観
    "dmsim.opponent": "S3",          # 旧名の互換（dmsim.search.opponent と同じモジュール）
    "dmsim.loop_first": "S3",        # 旧名の互換（dmsim.search.loop_first と同じモジュール）
    "dmsim.discovery.bestfirst": "S3",     # 旧名の互換（dmsim.search.bestfirst と同じモジュール）
    "dmsim.discovery.reachsearch": "S3",   # 旧名の互換（dmsim.search.reachsearch と同じモジュール）
    # S4 評価
    "dmsim.eval": "S4",                    # 定義元（P1-S4: 測定 measure・到達率 reach・構造検証 replay/shrink・再現性・妥当性 validity・開始局面 evalstarts・pool_metrics）
    "dmsim.eval.ruler": "S4",              # 物差しの本体 段1・段2（P2 タスク5）
    "dmsim.eval.lockcheck": "S4",          # ロック判定 lock_probe・round_probe・lock_ok（P2 タスク2 で search.game から移動）
    "dmsim.solitaire": "S4",              # 旧名の互換モジュール（search/turn・leaf_eval・game と eval/measure を再エクスポート、P0-3）
    "dmsim.pool_metrics": "S4",          # 旧名の互換（dmsim.eval.pool_metrics と同じモジュール）
    "dmsim.validity": "S4",              # 旧名の互換（dmsim.eval.validity と同じモジュール）
    "dmsim.discovery.replay": "S4",      # 旧名の互換（dmsim.eval.replay と同じモジュール）
    "dmsim.discovery.shrink": "S4",      # 旧名の互換（dmsim.eval.shrink と同じモジュール）
    "dmsim.discovery.reproducibility": "S4",  # 旧名の互換（dmsim.eval.reproducibility と同じモジュール）
    "dmsim.discovery.evalstarts": "S4",  # 旧名の互換（dmsim.eval.evalstarts と同じモジュール）
    "dmsim.autofix.reach": "S4",         # 旧名の互換（dmsim.eval.reach と同じモジュール）
    "dmsim.autofix.usage": "S4",         # 旧名の互換（dmsim.eval.usage と同じモジュール、P1-S5）
    "dmsim.deckplan.evaluate": "S4",     # 旧名の互換（dmsim.eval.deckeval と同じモジュール、P1-S6）
    # S5 発見（デッキ構築を含む）
    "dmsim.discovery": "S5",               # 定義元（P1-S5: ループ発見・候補・監査・combo_search。S0/S3/S4 の旧名は上の個別指定）
    "dmsim.combo_search": "S5",          # 旧名の互換（dmsim.discovery.combo_search と同じモジュール）
    "dmsim.deckplan": "S5",
    # S6 学習・改善
    "dmsim.autofix": "S6",
    # 画面・開発用
    "dmsim.devserver": "APP",
    "dmsim.playback": "APP",
}

# 今回解消できなかった逆流: (import する側, される側) → 理由
ALLOWED: dict = {}   # P1-S5 で最後の1件（deckplan.auto→autofix.usage）を usage の S4 移行で解消


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


def test_cards_imports_only_base():
    """S1 の定義元 dmsim.cards は dmsim.base（S0）と自分自身だけを import する。"""
    ok = lambda b: any(b == p or b.startswith(p + ".") for p in ("dmsim.cards", "dmsim.base"))  # noqa: E731
    bad = sorted(f"{a} -> {b}" for a, b in edges() if (a == "dmsim.cards" or a.startswith("dmsim.cards.")) and not ok(b))
    assert not bad, bad


def test_search_plan_import_only_lower_layers():
    """S3 の定義元 dmsim.search・dmsim.plan は base・cards・engine（と旧名の互換）と S3 自身だけを import する。"""
    bad = sorted(f"{a} -> {b}" for a, b in edges()
                 if (a.startswith("dmsim.search") or a.startswith("dmsim.plan"))
                 and ORDER.index(layer(b)) > ORDER.index("S3") and (a, b) not in ALLOWED)
    assert not bad, bad


def test_old_names_are_the_same_module():
    """旧名は定義元と同一オブジェクト（旧名への monkeypatch が定義元に効く）。"""
    import importlib
    for old, new in [("dmsim.types", "dmsim.base.types"), ("dmsim.cardid", "dmsim.base.cardid"),
                     ("dmsim.discovery.loopspec", "dmsim.base.loopspec")] + \
            [(f"dmsim.{m}", f"dmsim.cards.{m}") for m in
             ("defs", "canonical", "cardfiles", "cardstore", "approval", "identity", "schema", "dataaudit")] + \
            [("dmsim.opponent", "dmsim.search.opponent"), ("dmsim.loop_first", "dmsim.search.loop_first"),
             ("dmsim.discovery.bestfirst", "dmsim.search.bestfirst"),
             ("dmsim.discovery.reachsearch", "dmsim.search.reachsearch")]:
        assert importlib.import_module(old) is importlib.import_module(new)


def test_op_vocab_matches_engine_implementations():
    """op 語彙の正本 base/opvocab と engine の実装登録が1対1で、型の宣言も一致する。"""
    from dmsim.base import opvocab
    from dmsim.engine import ops  # noqa: F401
    from dmsim.engine.registry import OP_ARGS, OPS
    assert OP_ARGS is opvocab.OP_ARGS
    assert set(opvocab.OP_ARGS) - set(OPS) == set(), "語彙にあるのに実装が無い op"


# P1-S4: 旧名 → 定義元（同じモジュールオブジェクトであること）
S4_ALIASES = {
    "dmsim.pool_metrics": "dmsim.eval.pool_metrics",
    "dmsim.validity": "dmsim.eval.validity",
    "dmsim.discovery.replay": "dmsim.eval.replay",
    "dmsim.discovery.shrink": "dmsim.eval.shrink",
    "dmsim.discovery.reproducibility": "dmsim.eval.reproducibility",
    "dmsim.discovery.evalstarts": "dmsim.eval.evalstarts",
    "dmsim.autofix.reach": "dmsim.eval.reach",
}


def test_eval_imports_only_s4_or_below():
    bad = [f"{a} -> {b}({layer(b)})" for a, b in sorted(edges())
           if a.startswith("dmsim.eval") and ORDER.index(layer(b)) > ORDER.index("S4")]
    assert not bad, "eval が S5 以上を import している:\n" + "\n".join(bad)


def test_s4_old_names_are_same_module():
    import importlib
    for old, new in S4_ALIASES.items():
        assert importlib.import_module(old) is importlib.import_module(new), old


def test_solitaire_reexports_definitions():
    import importlib
    import dmsim.solitaire as sol
    homes = ["dmsim.eval.measure", "dmsim.eval.lockcheck", "dmsim.search.game", "dmsim.search.leaf_eval", "dmsim.search.turn"]
    for name in [n for n in vars(sol) if not n.startswith("__") and n != "annotations"]:
        obj = getattr(sol, name)
        if callable(obj) or isinstance(obj, type):
            assert any(getattr(importlib.import_module(h), name, None) is obj for h in homes), name


# P1-S5: 旧名 → 定義元
S5_ALIASES = {
    "dmsim.combo_search": "dmsim.discovery.combo_search",
    "dmsim.autofix.usage": "dmsim.eval.usage",
}


def test_s5_old_names_are_same_module():
    import importlib
    for old, new in S5_ALIASES.items():
        assert importlib.import_module(old) is importlib.import_module(new), old


def test_s5_does_not_import_s6():
    bad = [f"{a} -> {b}" for a, b in sorted(edges()) if layer(a) == "S5" and layer(b) == "S6"]
    assert not bad, "S5 が S6 を import している:\n" + "\n".join(bad)


def test_s4_and_below_do_not_import_s5():
    bad = [f"{a}({layer(a)}) -> {b}" for a, b in sorted(edges())
           if layer(b) == "S5" and ORDER.index(layer(a)) <= ORDER.index("S4")]
    assert not bad, "S4 以下が S5 を import している:\n" + "\n".join(bad)


def test_play_api_has_single_turn_entry():
    """tools の1ターン探索は play_api.search_turn を通す（P1-S5）。"""
    from dmsim import play_api
    assert callable(play_api.search_turn)


# P1-S6: 旧名 → 定義元
S6_ALIASES = {
    "dmsim.deckplan.evaluate": "dmsim.eval.deckeval",
}


def test_s6_old_names_are_same_module():
    import importlib
    for old, new in S6_ALIASES.items():
        assert importlib.import_module(old) is importlib.import_module(new), old


def test_s6_does_not_import_s5():
    bad = [f"{a} -> {b}" for a, b in sorted(edges()) if layer(a) == "S6" and layer(b) == "S5"]
    assert not bad, "S6 が S5 を import している:\n" + "\n".join(bad)


def test_s5_and_below_do_not_import_s6():
    bad = [f"{a}({layer(a)}) -> {b}" for a, b in sorted(edges())
           if layer(b) == "S6" and ORDER.index(layer(a)) <= ORDER.index("S5")]
    assert not bad, "S5 以下が S6 を import している:\n" + "\n".join(bad)


def test_s6_search_goes_through_api():
    """S6 は探索器を直接呼ばず play_api / run_eval を通す（P1-S6）。"""
    bad = [f"{a} -> {b}" for a, b in sorted(edges())
           if layer(a) == "S6" and (b.startswith("dmsim.search.turn") or b.startswith("dmsim.search.fair")
                                   or b == "dmsim.solitaire" or b.startswith("dmsim.eval.measure"))]
    assert not bad, "S6 が探索器を直接 import している:\n" + "\n".join(bad)


def test_lock_judge_moved_to_s4():
    """ロック判定は S4 の eval.lockcheck が定義元。旧名 solitaire.* は同一オブジェクト、play_game の既定の判定役は lock_probe。"""
    from dmsim import solitaire
    from dmsim.eval import lockcheck
    from dmsim.search import game
    for n in ("lock_probe", "round_probe", "lock_ok", "_lock_ok"):
        assert getattr(solitaire, n) is getattr(lockcheck, n)
    assert lockcheck.lock_probe.__module__ == "dmsim.eval.lockcheck"
    assert game._default_lock_judge is lockcheck.lock_probe
    assert not hasattr(game, "lock_probe")
