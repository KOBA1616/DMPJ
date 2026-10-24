# DMPJ 作業メモ（全スレッド共通）

- 日本語で報告する。リポジトリは非公開。
- Claude の上限節約: 機械的・大量の作業は無料モデルかルールベースへ回す。方針と使い方は `docs/offload.md`。
  - 長いログは読む前に `... 2>&1 | python tools/offload.py digest` で縮める。
  - テストは `python tools/offload.py affected-tests` の出力だけ先に回す。全体は最後に1回。
  - 差分の一次レビュー: `git diff origin/main | python tools/offload.py review-diff`（終了コード3は Claude で処理してよい合図）。
- 課金が発生する経路を作らない（無料モデルは `tools/llm_offload/providers.py` の許可リストのみ）。キーはコード・ログに出さない。
- 取得・変換の定期ワークフロー（auto-sync / auto-convert / convert-cards）を壊さない。`tools/convert_cards.py` の公開名は維持する。
