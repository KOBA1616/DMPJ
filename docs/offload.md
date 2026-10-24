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
