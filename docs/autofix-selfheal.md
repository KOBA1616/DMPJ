# 日次の自己修復ループ

目的: 日次の自動診断・改善（`tools/auto_fix.py`）が一部失敗しても、残りを止めずに回し、原因を Issue に残し、次回までに自動で直す。

1. **握って続ける**: 診断（対象ごと）・deck_fix・auto_tune の各段階の例外を `dmsim/autofix/selfheal.py` が握り、`data/autofix/health.yaml` に記録する（連続失敗回数・最後のエラー・traceback の末尾・最後の成功日）。1つの失敗で他の段階・対象は止まらない。
2. **隔離**: 同じ段階が連続3回失敗したら、日次ではその段階を飛ばす（時間の無駄を避ける）。直したら `health.yaml` の該当段階を消せば再開する。
3. **Issue 化**: 失敗した段階があれば `logs/autofix_issue.md`（Issue 本文）を作る。日次ルーティンがこれを label `autofix-failing` の Issue に1件へ集約して残す（既にあればコメント）。失敗が無ければ、開いている同 label の Issue を閉じる。
4. **次回に直す**: 日次ルーティンは最初に開いている `autofix-failing` / `tests-failing` の Issue を読み、原因を直す PR を出す（エンジン内部・カードデータには触れない）。直ったら `health.yaml` の該当段階を消して再測定する。
5. `data/autofix/health.yaml` は日次の PR でコミットする（次回の実行が連続失敗を引き継ぐため）。
