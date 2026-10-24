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

登録前に `tools\run_worker.bat` をダブルクリックか PowerShell で1回動かし、`%USERPROFILE%\.dmpj-worker\log.txt` にエラーが無いことを確認する。そのうえで10分ごとに実行する。PowerShell で（`C:\path\DMPJ` は clone した場所。パスに空白がある場合は、PowerShell では `/TR '"C:\my path\DMPJ\tools\run_worker.bat"'` と外側を単引用符にする）:

```
schtasks /Create /SC MINUTE /MO 10 /TN "dmpj-worker" /TR C:\path\DMPJ\tools\run_worker.bat /F
```

- ログ: `%USERPROFILE%\.dmpj-worker\log.txt`。止める: `schtasks /Delete /TN "dmpj-worker" /F`。
- 二重起動はロック(`.dmpj-worker\lock`)で防ぐ。PC がスリープ中の分は、復帰後の次回にまとめて処理される。
- 定期的にカード変換を回すなら、`python tools\local_worker.py enqueue convert --limit 100` を投入する（毎回の投入もスケジュールできる）。
- ローカルで変換する間は、Actions と cards-data が衝突しないよう `tools/auto_convert.yaml` を `enabled: false` にして main に入れる。
- Mac/Linux は cron: `*/10 * * * * cd ~/DMPJ && python tools/local_worker.py run --once >> ~/.dmpj-worker/log.txt 2>&1`

投入例: `python tools\local_worker.py enqueue routine --name gaps --summarize` / `... --name review --summarize`
