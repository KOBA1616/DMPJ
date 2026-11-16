"""1人回し（ソリティア）AI とキル率の測定ハーネス（ステップ4の土台）。

相手は何もしない（マナチャージだけする。ブロック・S・トリガー・召喚・攻撃はしない）。妨害は後から足す。
自分の手番は「そのターンの中の自分の選択」を深さ優先で探索し、ターン終了時の局面を評価して一番良い線を採る。
エンジンは決定的（乱数も state に入っている）なので、探索で見つけた葉の Engine をそのまま本番の局面として採用できる。

キルとして数えるもの（own_turn は自分の何ターン目か。先攻・後攻どちらでも自分のターンを 1, 2, 3 ... と数える）:
- direct_attack  シールドを割ってダイレクトアタックが通った
- deck_out       相手の山札切れ（ループをストックして削り切ったものは loop_deck_out）
- effect         「ゲームに勝つ」効果
- lock           ターンをまたぐロック（LoopDetector period="round"）。確立したターンで数える。
                 相手のマナ・手札などが周回ごとに増えないこと（相手が何も積み上げられない）と、
                 自分の山札が相手より先に尽きないこと（analyze の limit）を条件にする
ターン内ループは探索中に LoopDetector（period="in_turn"）で見つけ、verify で確かめてから fast_forward でストックする。
相手のシールドを 0 にするループ（win_by="shield_zero"）はストックした後の局面から探索を続ける（その後の攻撃を探す）。

  python -m dmsim.solitaire --deck deck.yaml --games 1000 --turns 4 --workers 4
  python -m dmsim.solitaire --deck deck.yaml --games 1 --seed 7 --record g.json   # 1局を記録（python -m dmsim.play --replay g.json）
"""
# P0-3 で責務ごとに分割した。ここは旧名を全て再エクスポートする互換モジュール（CLI の入口も維持）。
#   探索        dmsim.search.turn      TurnSearch・Detectors・candidates・charge_only_policy・own_turn
#   局面精度    dmsim.search.leaf_eval Weights・evaluate・goal_distance・WIN
#   1局の進行   dmsim.search.game      play_game・fair_game・GameResult
#   ロック判定   dmsim.eval.lockcheck   lock_probe・round_probe・lock_ok（P2 タスク2）
#   大量試行    dmsim.eval.measure     measure・summarize・load_deck・main
# 注意: 関数を差し替える（monkeypatch）ときは、ここではなく定義元のモジュールを差し替えること。
from __future__ import annotations

from .eval.measure import W, _one, _init_worker, _W, init_worker, load_deck, main, measure, summarize, wilson  # noqa: F401
from .eval.lockcheck import _lock_ok, lock_ok, lock_probe, round_probe  # noqa: F401
from .search.game import GameResult, _origin, fair_game, origin, play_game, run_turns  # noqa: F401
from .search.leaf_eval import WIN, Weights, evaluate, goal_distance  # noqa: F401
from .search.turn import (Detectors, TurnSearch, TurnStats, _is_burn, _is_engine, _rank, candidates,  # noqa: F401
                          charge_only_policy, greedy_policy, is_burn_loop, is_engine_loop, own_turn)

if __name__ == "__main__":
    main()
