"""実行層の測定: 仕込み済み開始局面からの測定に使う開始局面を決める（auto_fix / auto_tune / hypothesis_gate 共通）。

測定を2層に分ける（docs/measurement-tiers.md）:
  到達層  デッキを引いて必要カードがそろう確率。厳密計算の理論上限 dmsim.autofix.reach と、通常の開幕の実測を突き合わせる。デッキの問題。
  実行層  必要カードがそろった局面から、探索・評価がキルまで運べるか。ノブ・評価式・探索の改善はここで測る。AIの問題。
通常の開幕だけで測ると、多部品のコンボは到達層（tenmon 0.03 / akashic 0.05 ＝ 理論上限どおり）で止まり、実行層の差が見えない。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deck_fix  # noqa: E402
from dmsim.eval.deckeval import spec_with_deck  # noqa: E402


def exec_spec(rules, t: dict, deck: list[str], cold: bool = False):
    """(開始局面spec|None, 由来)。cold=True なら通常の開幕（targets の setup があればそれ）。"""
    if cold:
        import yaml
        return (yaml.safe_load(Path(t["setup"]).read_text(encoding="utf-8")) if t.get("setup") else None), "冷たい開幕"
    setup, origin = deck_fix.resolve_setup(rules, t, None, deck)
    if setup and origin in ("LoopSpec自動", "部品表自動"):
        setup = spec_with_deck(setup, deck)         # 山札を候補デッキの残り札に差し替える
    return setup, origin
