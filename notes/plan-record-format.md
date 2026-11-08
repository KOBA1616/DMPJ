# 計画の記録形式 v1（計画仕様 §4.7 の確定）

実装: `dmsim/plan/`。エンジン・カードデータには依存しない。未承認の §9-12（相手の見込み・判断・探索補正・経験ログ接続）は枠のまま。

## 確定した点
- **スキーマ版**: `SCHEMA_VERSION = 1`。v0（スケルトン）は `MIGRATIONS[0]` で読める。版を上げるときは対応表の追加が必須。未知の版・対応表のない版は `ValueError`。
- **シリアライズ**: 正規形 JSON（キー順固定・空白なし・NaN 不可・UTF-8）。1計画1行の JSONL（`dump_jsonl` / `load_jsonl`）。
- **plan_id**: 正規形の SHA-256 先頭16桁。出典（`source`）は含めない。集合として扱う項目（roles, hazards, minimal, goal, routes, Pred.zones, Route.civs）は並べ替えてから計算するので順序に依存しない。`params` と `extra` は内容に含む。
- **検証**: 種類・役割は登録式（未登録は拒否）。Pred の `op` は `>= <= == > <`、`n >= 0`。
- **未知の項目**: トップレベルの未知キーは `extra` に保持し往復で捨てない。
- **LoopSpec**: `kind="loop"` として `from_loopspec` / `to_loopspec` で無損失に往復（テストあり）。

## 版を上げる手順
1. `SCHEMA_VERSION` を上げ、`MIGRATIONS[旧版]` に変換関数を足す。
2. 旧形式のサンプルを読み込むテストを足す。
3. 版が変わると plan_id の入力（schema_version）が変わるため、移行後に ID を再計算する（登録簿側で旧IDとの対応を持つ）。
