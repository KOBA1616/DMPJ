# 作業の振り分け方針（Claude の上限を節約する）

目的: Claude のプラン上限を、設計・難しい実装・最終判断に使い、大量で機械的な作業は無料モデルかルールベースで済ませる。
**絶対条件: 課金が発生する経路を作らない。** 無料モデルは `-free` で終わる許可リスト内のみ（`tools/llm_offload/providers.py`）。
費用の兆候（HTTP 402・課金系エラー・応答に費用>0）が出たら停止（終了コード2）。キーはコード・ログに出さない（`scrub`で伏せる）。

## どこに回すか

| 作業 | 回し先 | 手段 |
|---|---|---|
| カード原文→効果DSL変換 | 無料モデル（人が確認） | `convert_cards.py --provider opencode-cli`、定期は auto-convert |
| 原文サーベイの分類・語彙案出し | 無料モデル→Claudeが結果だけ判断 | `offload.py classify` / `ask` |
| テスト失敗・ログの要約 | まずルールベース、足りなければ無料モデル | `offload.py digest` → `summarize-log` |
| 差分の一次レビュー | 無料モデル（指摘の取捨はClaude） | `git diff | offload.py review-diff` |
| docstring・README下書き | 無料モデル | `offload.py docstring` |
| 探索結果の要約（長い表・ログ） | ルールベースで集計→必要なら無料モデル | 集計スクリプト＋`summarize` |
| 変更に関係するテストの選択 | ルールベース | `offload.py affected-tests` |
| ルール解釈・エンジン設計・デッキ探索の設計 | **Claude** | 無料モデルに回さない |
| 難しい実装・バグ原因の特定・レビュー指摘の最終判断 | **Claude** | 一次結果を渡して使う |
| 人の確認が要る判断（ルール裁定・カード承認） | **koba** | 決定カード |

迷ったら: 出力が間違っていても人かテストがすぐ気づける作業 → 無料モデル。間違いが静かに残る作業 → Claude。

## 使い方

```
git diff origin/main | python tools/offload.py review-diff
pytest -q 2>&1 | python tools/offload.py digest          # LLMなし。まずこれ
pytest -q 2>&1 | python tools/offload.py summarize-log
python tools/offload.py affected-tests                      # 出てきた pytest コマンドだけ回す
python tools/offload.py ask --instruction "この表を civ ごとに数えて" < table.txt
```

- 終了コード `3`（`ESCALATE:`）= 無料枠切れ・レート制限・空応答。**黙って別の有料経路へ行かない**ので、その作業は Claude が自分でやるか、後で再実行する。
- 同じ入力はキャッシュ（`.cache/llm_offload`）。1日200回まで（`--daily-limit`）。入力は6万文字で前後を残して切る。
- 既定は `opencode-cli`（キー不要の無料枠）。`--provider opencode` は `OPENCODE_API_KEY` が必要。
- 無料モデルを足す時は https://opencode.ai/docs/zen/ で$0を確認し `OPENCODE_FREE_MODELS` に追加（テストあり）。
- 外部APIに送るのは diff・ログ・公式カード文面など。リポジトリは非公開なので、ソース全体を送る運用にはしない。

## Claude 側の節約ルール

1. 出力が長いコマンド（pytest・ビルド・探索）は `| tail -40` か `digest` を通してから読む。全文は失敗の原因が分からない時だけ。
2. テストは `affected-tests` が示した分を先に回し、コミット前・PR前に1回だけ全体を回す。
3. 大きなファイルは `Read` に offset/limit を付け、`grep` で場所を絞ってから読む。
4. 調査・機械的な修正を繰り返す前に、スクリプト化できないか考える（1回書けば以後はトークン0）。
5. サブエージェントは頼まれた時だけ。仕様の再確認で同じファイルを読み直さない。
6. 長い報告はファイルにして、返信は結論と1行リンクだけにする。

## 手元のPCで高性能な無料モデルを動かす（ローカルワーカー）

クラウドのセッションから PC には届かないので、**PC が GitHub のジョブを取りに行く**方式。ポート開放も外部へのキー受け渡しも不要。

```
Claude / Actions ──jobs/pending/*.yaml──▶ llm-jobs ブランチ ◀──取得・結果push── PCのワーカー(OpenCode)
```

- ジョブ: `type: ask`（`task`, `instruction`, `input`）、`type: routine`（決まった定型作業だけ: `gaps` 語彙ギャップ集計 / `tests` テスト結果の圧縮 / `review` 差分の一次レビュー / `status` STATUS の鮮度確認。`--summarize` で無料モデルが要約。任意のコマンドは実行しない）と `type: convert`（`limit`, `workers`, `interval`, `model`）。
- 結果: `jobs/done/<id>.yaml`（`status: ok / escalate / error`、`text`）。`escalate` は無料枠切れ等で、Claude が代わりに処理してよい合図。
- `convert` は cards-data ブランチの作業ツリーに現在の tools/dmsim/語彙を重ねて `auto_convert.py` を実行し、結果を cards-data へ push する（Actions の auto-convert と同じ処理）。
- 無料モデルの許可リスト検査・課金検知はクラウドと同じ。課金の兆候が出たらワーカー全体が止まる。

### Windows のセットアップ（初回のみ）

1. Git・Python 3.11 以上・Node.js を入れる（`git --version` / `python --version` / `node --version` で確認）。
2. PowerShell で:
   ```
   git clone https://github.com/KOBA1616/DMPJ.git
   cd DMPJ
   pip install pyyaml
   npm i -g opencode-ai
   ```
   `git push` できるよう GitHub にログイン済みであること（Git for Windows の資格情報マネージャーで可）。
3. OpenCode CLI の動作確認（動作確認済みの流れ）。デスクトップアプリも入れている場合、CLI は専用の保存先で動かす
   （そうしないと `Database is not empty and has no session table` で失敗する）:
   ```
   $env:XDG_DATA_HOME = "$env:USERPROFILE\.dmpj-worker\xdg"
   $env:XDG_CONFIG_HOME = "$env:USERPROFILE\.dmpj-worker\xdg-config"
   opencode run -m opencode/glm-5.3-flash-free "hello"
   ```
   返事が返れば成功（ログイン不要）。`local_worker.py` と `tools\run_worker.bat` は同じ保存先を自動で使うので、以後は設定不要。
   `opencode` が認識されない場合は PowerShell を開き直す。
   一覧にさらに高性能な `-free` モデルがあれば、公式 https://opencode.ai/docs/zen/ で $0 と確認し、`tools/llm_offload/providers.py` の `OPENCODE_FREE_MODELS` に足してから `--model` で指定する。
   `python` が認識されない場合（pip は動くのに python だけ出ない時など）は、`python` を `py -3` に読み替える（例: `py -3 tools\local_worker.py run --once`）。
4. 最初の1件で通し確認（定型作業 routine の `status`。無料モデルを使わず、ワーカーの経路だけ確かめる）:
   ```
   python tools\local_worker.py enqueue routine --name status
   python tools\local_worker.py run --once
   python tools\local_worker.py status
   ```
   `done: 1` になり、GitHub の `llm-jobs` ブランチ `jobs/done/` に結果が出れば経路は成功。続けて無料モデルも通す:
   ```
   python tools\local_worker.py enqueue ask --task summarize --instruction "要点3行で" --file README.md
   python tools\local_worker.py run --once
   ```
   結果が `status: ok` なら完了。`escalate` は枠切れ等、`error` は `jobs/done/<id>.yaml` の `error` を見る。

### 自動化（タスクスケジューラ）

登録前に `tools\run_worker.bat` をダブルクリックか PowerShell で1回動かし、`%USERPROFILE%\.dmpj-worker\log.txt` にエラーが無いことを確認する。そのうえで5分ごとに実行する。PowerShell で（`C:\path\DMPJ` は clone した場所。パスに空白がある場合は、PowerShell では `/TR '"C:\my path\DMPJ\tools\run_worker.bat"'` と外側を単引用符にする）:

```
schtasks /Create /SC MINUTE /MO 5 /TN "dmpj-worker" /TR C:\path\DMPJ\tools\run_worker.bat /F
```

- ログ: `%USERPROFILE%\.dmpj-worker\log.txt`。一時停止/再開: `schtasks /Change /TN "dmpj-worker" /DISABLE`（/ENABLE）、実行中を止める: `schtasks /End /TN "dmpj-worker"`、削除: `schtasks /Delete /TN "dmpj-worker" /F`、状態: `schtasks /Query /TN "dmpj-worker"`。
- 二重起動はロック(`.dmpj-worker\lock`)で防ぐ。PC がスリープ中の分は、復帰後の次回にまとめて処理される。
- 定期的にカード変換を回すなら、`python tools\local_worker.py enqueue convert --limit 100` を投入する（毎回の投入もスケジュールできる）。
- ローカルで変換する間は、Actions と cards-data が衝突しないよう `tools/auto_convert.yaml` を `enabled: false` にして main に入れる。
- Mac/Linux は cron: `*/10 * * * * cd ~/DMPJ && python tools/local_worker.py run --once >> ~/.dmpj-worker/log.txt 2>&1`

投入例: `python tools\local_worker.py enqueue routine --name gaps --summarize` / `... --name review --summarize`

### コードの自動更新（git pull の自動化）

ワーカーは実行のたびに、先に `main` を更新する（`git fetch` + `git merge --ff-only origin/main`）。fast-forward できる時だけ更新し、次の場合は何もせずログ（`self-update: …`）に理由を残して続行する: main 以外のブランチにいる／未コミットの変更がある／fast-forward できない／ネットワーク不通。更新に失敗してもワーカー本体は止まらない。
- ワーカー自身（`local_worker.py` / `llm_offload` / `run_worker.bat`）が更新された時は、ロックを放して新版で自動的に起動し直す（旧版のまま長いジョブを走らせない）。
- 止めたい時は `local_worker.py run --once --no-update`。PC のこの clone で別ブランチを触る作業をする時は、自動更新が飛ばされるだけで害はない。
- **最後に手動で `git pull` を1回だけ**する（この機能を取り込むため）。以後は不要。

### 結果を Claude に渡す

- **基本**: 結果は `llm-jobs` ブランチの `jobs/done/<id>.yaml` に残る。投入したスレッドが `send_later` で数分後に読む。先頭の `summary:`（1行要約）を先に見て、必要な時だけ `text` を読む。PC 側の追加設定は要らない。
- **任意**: ジョブに `--pr <番号>` を付けると、結果を PR コメントにも投稿する（PC に GitHub CLI と `gh auth login` が要る）。使わなくてよい。投稿に失敗しても結果は `jobs/done` に残る（`pr_comment:` 欄に理由）。
  例: `py -3 tools\local_worker.py enqueue routine --name review --summarize --pr 33`

## 別サービスへの自動切り替え（OpenRouter の無料モデル）
- OpenCode の無料モデルが（タイムアウト・Model is unavailable 等で）全部だめなとき、環境変数 `OPENROUTER_API_KEY` があれば OpenRouter の無料モデルで同じ依頼を再試行する。キーがなければ何もしない。
- 使うのは、公式の一覧（`/api/v1/models`、認証不要）で `:free` かつ入力・出力の単価がどちらも 0 のモデルだけ。毎回その場で確かめるので、固定の許可リストは持たない。
- 応答に費用が載っている、または無料でないモデルが返ったら停止（Fatal）。キーはログに出さない（`scrub` が伏せる）。
- PC では、ワーカーを起動するウィンドウ（またはユーザー環境変数）に `OPENROUTER_API_KEY` を置く。ワーカーは `OPENCODE_API_KEY` だけを外す。
- OpenCode の無料モデルの許可リストは公式 zen の料金表で Free を確認したものだけ（2026-10-26: longcat を外し、beam / flint-40b / nemotron-3.5-lightning / nemotron-3.5-super-vl を追加）。

## LLM7（匿名の最後の切り替え先）
- OpenCode の無料モデルが全滅したとき、OpenRouter（キーがあれば）の次に LLM7（`api.llm7.io`、登録・キー不要。公式の匿名キー `unused`）を試す。`DMPJ_NO_LLM7=1` で無効。
- 匿名は毎分30回まで、IP が記録される。使うモデルは公式 `/v1/models` で `usage_based_only: false` のものに固定（gpt-oss:20b / nemotron-3-nano:30b / mistral-Nemo-Instruct-2407 / minimax-m2.7）。匿名キーには課金先がない。
- OpenCode が全滅したあと15分は別サービスを先に使い、毎回 OpenCode の全モデルを待たない。

## Gemini（Google AI Studio、キーがあるときだけ）
- 環境変数 `GEMINI_API_KEY` があれば、OpenCode 全滅時の切り替え先として最初に試す（OpenAI 互換: `generativelanguage.googleapis.com/v1beta/openai`）。順番は Gemini → OpenRouter → LLM7。
- 使うのは公式の料金ページで無料枠と出ている Flash 系（3.8 / 3.6 / 3 Flash Preview / 3.5・3.1 Flash-Lite）に固定。Pro 系は使わない。
- 注意: キーのプロジェクトに請求先を設定すると有料になりうるが、応答から費用は検知できない。**請求先のないプロジェクトで作ったキーだけ**を使う。無料枠は入力が製品改善に使われる。

## 実行をまたぐ記憶と cards-data の競合
- ワーカーは `work/model_state.json`（環境変数 `DMPJ_MODEL_STATE`）に、使えたモデル・使えなかったモデル（24時間は飛ばす）・別サービスを使う期限・最後に応答が返った時刻を残す。5枚ごとに変換プロセスを起動し直しても、前回使えたモデルから始め、直近10分に応答があれば開始前チェックも省く。
- cards-data への push: 取得系（auto-sync / sync-cards）は `data/cards/raw/by_product/` と台帳、変換は `converted.yaml` / `rejects.jsonl` / `convert_*.json` を書くので、通常は別ファイルで衝突しない。push が拒否されたら fetch → rebase で再試行し、変換結果ファイルが衝突したら ID ごとの和集合で合流（変換済みが優先、不合格は和集合から変換済みを除く）して push し直す。

## まとめて処理する枚数・スリープ
- ジョブの `chunk:`（既定10）で、何枚ごとに変換プロセスを起動し直して cards-data へ push するかを決める。大きいほど起動のむだが減るが、止まったときに失う枚数が増える（最大 chunk 枚）。
- Windows ではワーカーの実行中、スリープに入らない（SetThreadExecutionState）。ただし、実行していない間のスリープ中はタスクスケジューラが動かない。スリープ解除で動かすには、PowerShell で:
  `$t = Get-ScheduledTask dmpj-worker; $t.Settings.WakeToRun = $true; Set-ScheduledTask -InputObject $t`
  （電源オプションの『スリープ解除タイマーを許可』が有効で、ふたを閉じてスリープしない設定が前提。電源に接続していないと動かない設定もある。）

## ルールだけで変換（モデルを呼ばない）
- `tools/rule_convert.py`: クリーチャーのうち、原文が (a) 能力文なし（取得時に text だけ空と印が付いたバニラ）、(b) `data/rules/keywords.yaml` のキーワードだけ、のものは、辞書のルールで効果データにする（トークン0）。注釈（カッコ内）は無視し、改行・スラッシュ・空白でキーワードを区切る。`convert_cards.run` が最初に試し、検査（parse_card）を通らなければモデルへ回す。以前 `no_text` で rejects に入ったカードも、ルールで変換できれば対象に戻る。
- 語彙を増やすには keywords.yaml にキーワードを足す（コードは変えない）。2026-10-26 追加: Q・ブレイカー / ワールド・ブレイカー / このクリーチャーはブロックできない・アンタップしない・攻撃されない。
- cards-data（23,671枚）での該当数は585枚（バニラ251・キーワードのみ334）。バニラは「原文の取りこぼしでないか」を人が確認する（source.notes に記載）。
- 部分変換: 効果文のあるカードでも、原文からキーワード能力（ブロッカー、S・トリガー、チャージャー等。行の先頭・末尾に並んだもの）をルールで取り除き、モデルには残りの原文と `known_keywords` だけを渡す。結果の keywords はルール分が先。取り除いた分だけプロンプトが短くなり、キーワードの書き間違いも減る。
- ワーカーの `chunk` の既定は20枚（20枚ごとに保存して push）。

## 注釈・数値つきキーワード（keyword_patterns.yaml）
`パワーアタッカー+2000` や `マッハファイター` のように数値・注釈が付くキーワードは `data/rules/keyword_patterns.yaml` に正規表現と能力の雛形で書く（`{1}` が括弧の整数に置き換わる）。
`rule_convert.convert`（全体変換）と `split`（部分変換）の両方で使われ、結果は card の `abilities` に入る。注釈のカッコは照合前に除く。
追加するときは雛形を既存の演算（modify / allow / deny 等）だけで書き、`parse_card` を通ることをテストで確かめる。
対応済み: パワーアタッカー+N、マッハファイター、ジャストダイバー。
未対応（エンジンに演算が要る）: ガードマン、パワード・ブレイカー、セイバー、シールド・セイバー、ハンティング、エスケープ、G・ストライク など。
