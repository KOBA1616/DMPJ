# 高速化メモ

計測: `python tools/bench.py --games 20 [--profile]`（seed 固定。結果は高速化の前後で一致する）。

## 実施済み
- `GameState.clone()` を deepcopy から手書きコピーに置換。探索（solitaire / loop）の時間の約88%が deepcopy だった。
  1人回し 2.2 → 8.0 局/秒（約3.7倍）、全テスト 71s → 36s。state は純データ（int/str/bool/None + list/dict）だけという
  設計判断⑧に依存する。Card や GameState にフィールドを足しても `__dict__` コピーなので自動で追従する。
  ただし可変の値（list/dict）を新たに足すときは `_jcopy` が扱える型（list / dict / スカラー）に収めること。

## 次の候補（clone 後のプロファイル、上位）
1. `Engine.chars` / `abilities`（継続的効果の再計算。呼び出しごとに全カードを走査）→ ターン内キャッシュ（continuous 変更でのみ無効化）。
2. `_copy_card`（clone の残り）→ Card を `__slots__` 化、または cards をゾーン単位の copy-on-write に。
3. `loop.abstract`（転置・ループ検出キー）→ 差分更新のハッシュ。

## Rust 移植の見立て（DSL は変えない）
- 移植する核: `GameState`（純データなので構造体にそのまま落ちる）、`rng_next`（splitmix64、既に Rust 前提）、
  `Engine.advance` のタスクスタックと `events`/`combat`/`turn` の各ハンドラ、セレクタ評価。
- Python に残す: カード YAML → 効果データ変換、LoopDetector の解析・認定、探索の方策（まず PyO3 で state 単位の
  `clone`/`advance`/`answer`/`digest` だけ公開し、探索は Python から呼ぶ）。
- 先に clone と chars の最適化を終えるのが得策。Rust 化の主な利益は clone とハンドラの分岐で、ここがボトルネックの大半。
- 検証: 同一 seed のログ再生で Python 版と digest が一致することを回帰基準にする（既に `play.replay` がある）。
