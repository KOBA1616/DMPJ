# 仮説ルーティン（Claude が仮説を出し、機械が採否を決める）
自動マージはしない。Claude は下書きPRまで、マージは人。

## 流れ
1. 材料: `python tools/auto_fix.py ...` の台帳と `dmsim.autofix.failures.summarize/propose_from_failures`（失敗局の分類: cards_miss / board_miss / prep_unused / finish_miss / late_kill）。
2. Claude が最大の失敗クラスについて1つだけ仮説を立て、小さな変更（評価部品・探索の改造）を `claude/hyp-<日付>-<要点>` ブランチに実装して**下書きPR**を作る。ノブだけで済む仮説は `tools/auto_tune.py` に任せる（コードを書かない）。
3. ゲート: main の木で `python tools/hypothesis_gate.py baseline --out logs/gate_base.json`、下書きPRの木で
   `python tools/hypothesis_gate.py check --base-ref origin/main --baseline logs/gate_base.json`。
   - 禁止パス（`.github`、課金経路、`dmsim/eval`、holdout を含む `data/known_combos` 等）・テスト削除・テスト失敗 → 終了3（人が見る）。
   - 同一シード対比較で有意に改善かつ悪化した局が2割以下 → 終了0（accept_candidate）。有意に悪化 → 1。差なし → 2。
4. 0 の時だけPRを「レビュー可」にして koba に知らせる。1・2 は理由を台帳に残して閉じる。

## 守ること
FAIRのみ・holdout不使用・Vは足切りに使わない・課金が発生する経路を作らない・1ルーティンの仮説は1つ・結果は必ず記録。
ゲートの物差し（gate.py の FORBIDDEN、eval/ の指標）は仮説で変えられない。変える時は人が別PRで行う。
