# クラウドのエージェントにカード変換を回させる手順

PC のワーカーとは別に、git を使えるクラウドのエージェント（チャットから動かすもの）に変換ジョブを処理させるための指示。
被り防止の仕組み（claim・`target`・`order`）は docs/offload.md の「複数のワーカーを同時に動かす」。

## 前提（これが満たせないエージェントには任せない）
- リポジトリを clone でき、`llm-jobs` と `cards-data` ブランチへ push できる（GitHub の権限）。
- Python 3.11 以上と `pip install pyyaml` が使え、コマンドを実行できる。
- 変換に使うモデルが**無料**であること。有料になりうる設定・キーは使わない（CLAUDE.md の方針）。`tools/llm_offload/providers.py` の許可リスト外のモデルは拒否される。
- キーはコード・ログ・コミットに出さない。環境変数で渡す。

## 指示（エージェントにそのまま渡す文）
```
リポジトリ KOBA1616/DMPJ（非公開）を clone し、次を1回だけ実行して、出力の最後の20行を報告して。
  pip install pyyaml
  python tools/local_worker.py --work ./.worker run --once --target cloud --worker-name cloud-agent
- jobs/pending のうち target が cloud または省略のジョブだけ処理される（先に取った1台だけが処理する）。
- 途中で止めない。エラーが出たらそのまま報告して、再実行や設定変更はしない。
- API キーや秘密の値は出力に含めない。
```
定期的に回すなら、エージェント側のスケジュール機能で上のコマンドを繰り返す（5〜10分おき）。

## 使うモデルについて
`run --once` は OpenCode CLI の無料モデルを使うので、クラウド側にも OpenCode CLI（`npm i -g opencode-ai`）が要る。入れられない環境では次のどちらか。
- エージェント自身が原文を読んで変換する場合は、結果を `data/cards/converted.yaml` に追記し、`python tools/convert_cards.py` の検査（`parse_card`）を通ったものだけを `cards-data` に push する。自分のモデルが有料枠なら使わない。
- 外部の無料 API（OpenAI 互換）を使う場合は provider を足す（無料枠が公式に確認できたモデルだけ許可リストに入れる）。

## ジョブの積み方
- クラウド専用: `python tools/local_worker.py enqueue convert --limit 100 --target cloud --order newest`
- PC は古い順（`--order id`）、クラウドは新しい順にすると被らない。
- 1回の呼び出しでまとめて変換する: ジョブに `pack: 5`（`auto_convert.py --pack 5`）。指示文を共有してトークンを減らす。検査に落ちた分は単独で直す。

## 診断（コンボの失敗局の分類）を外のエージェントに回させる
llm-jobs は使わない。既存の外のエージェントに、次の指示文をそのまま渡す（モデルは呼ばない。スクリプトを回すだけ）。
```
リポジトリ KOBA1616/DMPJ（非公開）を clone し、次を実行して、diag.md の中身をそのまま報告して。
  pip install pyyaml
  python tools/diagnose_run.py saga --deck data/decks/saga_user_v1.yaml --games 40 --jobs 4 --parts parts --out diag.md
- 実行時間の上限で途中で切れたら、同じコマンドをもう一度実行する（parts に終わった局が残り、続きから回る）。
- コードや設定は変えない。エラーが出たらそのまま報告する。
```
