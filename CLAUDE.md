# DMPJ 作業メモ（全スレッド共通）

- 日本語で報告する。リポジトリは非公開。
- 外部AI連携（無料モデル振り分け・ローカルワーカー・OpenCode 等）と GitHub Actions のワークフローは 2026-11-26 に削除済み（koba 指示）。復活させない。`tools/convert_cards.py` の公開名は維持する（検証・前処理の関数と Claude API 変換だけ残している）。
- Rust エンジン（既定で有効、`DMSIM_RUST=0` で無効）: `dmsim/engine` のエンジンのファイルを変えたら、dmcore を作り直して `tests/test_rust_*.py` を通し、`python tools/rust_stamp.py` で記録し直す。記録が古い間は自動で Python だけで動く（Rust の無い環境で直した変更でも結果はずれない）。
- 出力の節約（トークン対策）: pytest は `pyproject.toml` の既定で `-q --tb=short --durations=10`。長い出力が出るコマンド（全体テスト・探索・ベンチ）は `python tools/run_quiet.py -- <コマンド>` で包む。全文は `logs/quiet/*.log` に残り、画面には終了コード・行数・エラー行の前後5行・末尾15行だけ出る。ログの全文を cat しない（必要なら該当箇所だけ grep や sed -n で見る）。失敗したテストは落ちたものだけ再実行する。乱数シード・JSONL ログ（再現用）は従来どおり全文を保存し、削らない。
- よく使う実行手順（コードから読み取りにくいもの）: 1ファイルだけは `pytest tests/test_x.py`、1件は `pytest tests/test_x.py::test_name`。クラウドで全体テストをする前に `git fetch --unshallow`。全体テストは分割して `python tools/run_quiet.py -- pytest tests/<部分>` で回す。既存の失敗は 228 件（2026-11-27 時点）なので、差分で見る。Rust スタンプの確認は `python tools/rust_stamp.py --check`。
- フック（`.claude/settings.json`、警告のみで止めない。実体は `tools/claude_hooks.py`）: エンジンを編集した時に Rust スタンプが古ければ警告、`logs/` の全文 cat を警告。
