# カードデータの置き場と型

| ファイル | 内容 | 型 |
|---|---|---|
| `data/cards/real.yaml` ほか `data/cards/*.yaml` | 承認済み・手書きのカード定義 | `data/schema/card_file.schema.json`（カード1枚は `card.schema.json`） |
| `data/cards/<converted\|real>/<弾>.yaml` | 弾ごとに分けたカード定義（`tools/split_cards.py`）。`dmsim.cardfiles.card_files()` が `*.yaml` と一緒に読む | 同上 |
| `data/cards/approvals.json` | 承認台帳。承認の状態・根拠・定義/語彙のハッシュ（`dmsim/approval.py`） | `approvals.schema.json` |
| `cards-data` ブランチの `catalog/sets.json` | 取得台帳（弾ごとのID・枚数・取得済み数） | `catalog_sets.schema.json` |
| `cards-data` ブランチの `raw/rejects.jsonl` | 変換できなかったカードの原文とエラー（1行1枚） | `rejects_row.schema.json` |

- カード定義は不変に近く扱い、承認は台帳に持つ（`source.review` は互換のため残す）。
- 承認は `def_hash`（定義）と `vocab_ver`（使う語彙の定義）で無効化される。`python tools/auto_approve.py` が無効化と自動承認をまとめて行う。
- `card.schema.json` は `python -m dmsim.schema` で生成する。他の型は手書き。`tests/test_file_schemas.py` が実データを検査する。
