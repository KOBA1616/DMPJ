# DMPJ 作業メモ（全スレッド共通）

- 日本語で報告する。リポジトリは非公開。
- 外部AI連携（無料モデル振り分け・ローカルワーカー・OpenCode 等）と GitHub Actions のワークフローは 2026-11-26 に削除済み（koba 指示）。復活させない。`tools/convert_cards.py` の公開名は維持する（検証・前処理の関数と Claude API 変換だけ残している）。
- Rust エンジン（既定で有効、`DMSIM_RUST=0` で無効）: `dmsim/engine` のエンジンのファイルを変えたら、dmcore を作り直して `tests/test_rust_*.py` を通し、`python tools/rust_stamp.py` で記録し直す。記録が古い間は自動で Python だけで動く（Rust の無い環境で直した変更でも結果はずれない）。
