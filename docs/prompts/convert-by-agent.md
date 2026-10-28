# カード変換プロンプト（チャットの AI に git の参照だけで処理させる）

AI が KOBA1616/DMPJ（非公開）を読め、コマンドを実行できる場合は、下の「プロンプト」をそのまま渡す。原文も指示文も貼らない（すべて実ファイルを参照する）。
コマンドが実行できない場合は、`python tools/agent_convert.py next 5` と `system` の出力を人が貼り、返答を `submit` に渡す。

## プロンプト
```
あなたは DMPJ（デュエル・マスターズのシミュレーター）のカード効果の変換係です。リポジトリ KOBA1616/DMPJ の main を clone して作業してください。

## 参照元（読むだけ。書き換えない）
- 変換の指示・語彙・スキーマ・変換例: `python tools/agent_convert.py system` の出力（最初に1回だけ読む）
- 公式の原文: data/cards/raw/by_product/*.jsonl（`next` が必要な分だけ出す。自分で開いて探さない）

## 作業（1回につき5枚。これを繰り返す）
1. `python tools/agent_convert.py next 5 --order newest` を実行する（古い順にしたいときは `--order id`）。出力が変換するカードの原文。
2. 指示文に従って、各カードを効果データ（YAML）にする。答えは次の形で、`answer.yaml` に書く。
     ```yaml
     cards:
     - id: <入力と同じID>
       ...（指示文のスキーマどおり）
     ```
   `known_keywords` がある場合、それはルールで処理済みなので能力として書き直さない。書かれた原文の残りだけを変換する。
3. `python tools/agent_convert.py submit answer.yaml` を実行する。✓ は登録済み。✗ は検査で落ちた理由なので、その理由を直して、✗ のカードだけをもう一度 submit する（同じカードは2回まで。それでも通らなければ飛ばして報告する）。
4. 登録された分を、作業ブランチに `git add data/cards/converted.yaml` して commit・push し、PR にする（main へ直接 push しない）。飛ばしたカードのIDは PR の説明に書く。

## 書き込み先
- 登録先は data/cards/converted.yaml だけ（`submit` が書く。手で編集しない）。review は必ず pending（人の確認待ち）。
- real.yaml・data/rules・コードは変更しない。

## 守ること
- 原文に無い効果を足さない。分からない効果は無理に変換せず、そのカードを飛ばして理由を報告する。
- ルール上の判断（置換効果・同時処理など）は推測で書かない。指示文と語彙表にある書き方だけを使う。
- キー・トークン・秘密の値を出力やコミットに含めない。
- 終わったら、登録した枚数・飛ばしたID・✗ の理由の傾向（足りない語彙など）を3行で報告する。
```

## 注意
- 登録先を main の `data/cards/converted.yaml` にすると、PC のワーカーや Actions が書く `cards-data` の同名ファイルと別々に育つ。取り込みは `cards-data` 側と ID ごとの和集合で合流する（docs/offload.md の合流規則）。クラウドのエージェントがどちらに書くかは、PR の運用で決める（既定は PR で main へ）。
- 精度は `tools/eval_convert.py` と同じ基準（手作業の real.yaml との一致率）で、最初の20枚を人が確認してから量を増やす。
