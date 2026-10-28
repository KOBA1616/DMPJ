# converted.yaml を弾別ファイルに移す手順

準備は済んでいる。書き手（convert_cards / agent_convert / rule_register / auto_convert / local_worker の合流処理）は、
`data/cards/converted/` というディレクトリがあればそちらへ、無ければ従来の `converted.yaml` へ書く（`dmsim.cardstore.converted_path()`）。
承認（`auto_approve`）と読み込み（`card_files()`）は両方の形を読む。

## 移行する日の手順（cards-data ブランチ上。変換が一段落してから）
1. PCのワーカーを止める（タスクスケジューラ `dmpj-worker` を無効化）。`tools/auto_convert.yaml` の `enabled` を false にして push。実行中の Actions が終わるのを待つ。
2. 新しい tools / dmsim を PC のリポジトリと cards-data に反映する（auto-convert / auto-approve は実行時に最新を取り込む。PCは `git pull`）。
3. cards-data で `python tools/migrate_converted.py --check`、問題なければ `python tools/migrate_converted.py`。`data/cards/converted/<弾>.yaml` ができ、`converted.yaml` が消える。
4. `git add -f data/cards/converted && git rm data/cards/converted.yaml` をコミットして push。
5. `python tools/auto_approve.py --dry-run` で枚数が移行前と同じことを確認。
6. ワーカーと `auto_convert.yaml` を元に戻す。

戻すとき: `python tools/split_cards.py` の逆はなく、`converted/` を削除して移行前のコミットに戻すのが確実。
