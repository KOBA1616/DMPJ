# ノブ自動チューニング（tools/auto_tune.py）
診断→候補（autofix）が「診断が指す1ノブを動かす」のに対し、複数ノブを同時に乱択変異して探す。LLM・課金なし。
- 採用条件: 調整用シード(1..N)で有意に良い → 別シード(1000..)でも有意に良い。再現しなければ `reject_not_reproduced`。
- 評価点: キルの早さが主、盤面・部品の到達の早さを小さく加える（滑らかにするため。Vの足切りではない）。FAIRのみ・holdout除外。
- 採用した設定は `data/autofix/knobs.yaml`（autofix と共通の開始点）。履歴は `--out` の台帳。
- 日次: `python tools/auto_fix.py --targets data/autofix/targets.yaml ... --tune-seconds 1200`（既定0=無効）。
  時間枠は deck_fix(`--deck-fix-budget`)と別枠で加算される。日次全体の枠は自動化スレッドの配分に合わせて `--tune-seconds` を決める。
- 目安: knight_dmc を seeds=10, generations=2, lam=2, workers=4 で約50秒。
