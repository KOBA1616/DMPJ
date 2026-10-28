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
- 原文に無い効果を足さない。語彙で原文どおりに表せない効果は、近い語彙で代用せず、`source.unsupported` に残す（need: 足せばよい語彙の案、text: 該当する原文）。unsupported があるカードは `submit` が登録せず、`data/cards/raw/rejects.jsonl` に `reason: vocab` で残す（語彙が足りてから変換し直す。足りない語彙は `python tools/report_gaps.py` に出る）。
- サイキック・GR・超次元・ドラグハート・城はオリジナルフォーマットでは使わないので変換しない。クロスギアは対象（語彙が足りなければ unsupported で rejects へ）。`next` は出さず、`submit` に来ても飛ばす。
- ルール上の判断（置換効果・同時処理など）は推測で書かない。指示文と語彙表にある書き方だけを使う。
- 近似・代用の禁止（具体例）: 「ブロック中」「攻撃中」の効果を、ターン終了まで残る modify や battle_power（only なし）で置き換えない。結果が厳密に同じと言い切れないなら unsupported にする。「同時」の処理を逐次で代用しない。
- 語彙の照合: 使う op・mod キー・event・permission は data/rules と dmsim/defs.py の定数で確認してから書く。「無い」と書く前に、op と mod のキーを取り違えていないか確かめる（step_mod は op として存在する）。
- main に追従する: 作業開始時と各 Unit の前に git fetch して main の最新に載せ替える（ZIP での再構築はしない）。
- PR は1 Unit（100枚）ごとに分け、前のをマージしてから次へ進む。1つの PR に積み増さない。
- 各カードの source.notes に、原文と厳密に一致するか近似かを書く。近似になるなら登録せず rejects へ。
- rejects の gaps 名は data/cards/raw/rejects.jsonl にある既存の名前に揃える（表記ゆれを避ける）。
- 同文コピーは aliases で表し、同名カードは最新版を正とする（docs/card-ids.md）。
- キー・トークン・秘密の値を出力やコミットに含めない。
- 終わったら、登録した枚数・飛ばしたID・✗ の理由の傾向（足りない語彙など）を3行で報告する。
```

## 注意
- 登録先を main の `data/cards/converted.yaml` にすると、PC のワーカーや Actions が書く `cards-data` の同名ファイルと別々に育つ。取り込みは `cards-data` 側と ID ごとの和集合で合流する（docs/offload.md の合流規則）。クラウドのエージェントがどちらに書くかは、PR の運用で決める（既定は PR で main へ）。
- 精度は `tools/eval_convert.py` と同じ基準（手作業の real.yaml との一致率）で、最初の20枚を人が確認してから量を増やす。
