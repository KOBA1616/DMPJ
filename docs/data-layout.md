# カードデータの置き場と型

| ファイル | 内容 | 型 |
|---|---|---|
| `data/cards/real.yaml` ほか `data/cards/*.yaml` | 承認済み・手書きのカード定義 | `data/schema/card_file.schema.json`（カード1枚は `card.schema.json`） |
| `data/cards/<converted\|real>/<弾>.yaml` | 弾ごとに分けたカード定義（`tools/split_cards.py`）。`dmsim.cardfiles.card_files()` が `*.yaml` と一緒に読む | 同上 |
| `data/cards/approvals/<弾>.json` | 承認台帳（弾ごと。単一の .json も可）。承認の状態・根拠・定義/語彙のハッシュ（`dmsim/approval.py`） | `approvals.schema.json` |
| `cards-data` ブランチの `catalog/sets.json` | 取得台帳（弾ごとのID・枚数・取得済み数） | `catalog_sets.schema.json` |
| `cards-data` ブランチの `raw/rejects.jsonl` | 変換できなかったカードの原文とエラー（1行1枚） | `rejects_row.schema.json` |

- カード定義は不変に近く扱い、承認は台帳に持つ（`source.review` は互換のため残す）。
- 承認は `def_hash`（定義）と `vocab_ver`（使う語彙の定義）で無効化される。`python tools/auto_approve.py` が無効化と自動承認をまとめて行う。
- `card.schema.json` は `python -m dmsim.schema` で生成する。他の型は手書き。`tests/test_file_schemas.py` が実データを検査する。

## converted.yaml から承認済みだけを使う
ワーカーは `converted.yaml` に書き続ける（変更なし）。`auto-approve`（または `tools/auto_approve.py`）が承認台帳に承認を記録し、
`load_rules(only_approved=True)`（または環境変数 `DMSIM_ONLY_APPROVED=1`）で、承認済み（台帳で有効、またはファイル上で review: approved）のカードだけを読む。
real.yaml へ移す作業は不要。定義や語彙が変わった承認は読み込みの時点で除かれる。

## カード同一性（同名は同じカード）
`dmsim/canonical.py` が同名カードの最新版（ID と本文）を決め、`dmsim/identity.py` がデータ変換・承認につなぐ。
- 変換対象は最新版の ID だけ（`convert_cards.load_rows`）。変換したカードの `source.aliases` に古い ID を残す。
- 旧 ID で `rules.cards[...]` を引いても最新版が返る（`load_rules` が `AliasDict` を使う）。
- `tools/canonicalize.py`（auto-approve workflow が毎回先に実行）: 変換済みの旧 ID カードを最新 ID へ寄せる。本文（正規化後）が同じなら付け替えて承認を引き継ぎ（by=inherit）、違えば消して承認を取り消し再変換・再検証。弾別ディレクトリなら置き場所も移る。
