# 実験B: copy-on-write（カード／ゾーン共有）の記録

ブランチ `claude/cow-experiment`。有効化は環境変数 `DMSIM_COW=1`（既定は無効で従来動作と同一）。

## 仕組み

- `GameState.clone()` がカード実体とゾーンのリストを複製先と共有する。共有の所有管理は
  dataclass のフィールド外（インスタンス `__dict__` の `_cow_cards` / `_cow_zones`）に置き、
  digest・fast_key には影響しない。
- 書き込みは `GameState.mut_card(cid)` / `mut_zone(name, player, shared)` 経由に統一した
  （エンジン内の書き込み箇所を全て変換）。共有中の対象への最初の書き込みでだけ実体コピーを作る。
- ゾーンは `Engine.mut_zlist(z, p)`、カードは `s.mut_card(cid)` / `eng.s.mut_card(cid)` を使う。
- 対象外: タスク・継続効果などの純データ（従来どおり clone 時にコピー）、対局ログ
  （案1で共有化済み）。

## 検証

- 差分検証ハーネス `tools/diff_play_check.py --cow`: 各決定点で複製側だけを別方策で
  25決定まで進め、親の digest が変わらないことを確認。6シード全て漏れなし、
  COW 無効時と digest 列・結果が完全一致。`--cow-diag` で漏れ箇所の差分表示も可能。
- golden（COW 有効）: 6/6 PASS、ノード数は基準と一致。
- 記録の再生検証は digest を使うため影響なし（mut 化はオブジェクト同一性の話で、
  状態の内容は不変）。

## 測定（prep frontier、段1・rank）

- 最大RSS: 1,184MB → 530MB（-55%）。判定・ノード数（26,955）は COW 有無で一致。
  時間は約-4%（測定時のマシン負荷が高く参考値）。
- 上限なし保持の再試験（prep seed1、保持上限・葉上限を撤廃、最大2ターン）:
  従来はターン2の一括展開でメモリ 6GB を使い切り OOM だったものが、
  **完走**した。91,874 ノード、最大RSS 1,104MB、capped=False、truncated=False、
  2ターンキル。これにより prep seed1 は上限に触れない形で「ターン1にキルなし＋
  ターン2にキルあり」（段1・無抵抗の前提内）を確認できた。

## 採否（決定済み）

- **保持探索でのみ既定有効**（2026-11-17 決定）。対象は探索系3ツール
  （exhaustive_proto / exhaustive_multiturn / exhaustive_crossturn）で、各ツールの
  起動時に有効化する。`DMSIM_COW=0` で無効化できる。エンジン全体の既定にはしない:
  効果は局面を大量保持する探索に限られ、検証（分岐チェック＋golden）の及ぶ範囲も
  探索系の経路までなので、有効範囲を検証範囲に揃える。Rust コア有効時の経路
  （rustcore は独自実装）では COW は効かない。
- 既定有効化の確認: 環境変数なしで golden 6/6 PASS（ツール側の有効化で
  COW 有効時と同じ結果になること、DMSIM_COW=0 で無効に戻ることを確認済み）。
