# 対戦AI化 Phase 計画（ポケカABC調査に基づく）

ポケモンカードAIの調査（小型Transformer＋自己対戦RL、対局中探索なし）を受けて、
本システムに対戦・学習レイヤーを追加する計画。各 Phase ごとに PR を作る（マージはしない）。
既存の探索系（コンボ発見用）は置き換えない。

| Phase | 内容 | 状態 |
|---|---|---|
| 1 | 2p対戦ベンチ新設（サガミラー、局/秒・決定/秒・Rust適用率） | 完了（本PR） |
| 2 | Rust追随と最適化（下記「Phase 2 の初手」の不一致解消が先。その後 chars の版番号キャッシュ、PyO3 の JSON 文字列境界の削減、clone の copy-on-write） | 未着手 |
| 3 | バッチ並行API（Rust内部で複数局を一括実行） | 未着手 |
| 4 | 方策エンコーダ（DSL→共通特徴トークン）＋小型Transformer＋価値ヘッド＋自己対戦RL。通常デッキの追加もここ | 未着手 |

## Phase 1: 2p対戦ベンチ（tools/bench_2p.py）

- 既定は絶望神サガ（data/decks/saga.yaml）のミラー戦、両者ランダム方策、探索なし。
  対戦を最後まで回し、局/秒・決定/秒・平均ターン・先攻勝率・Rust適用率を出す。
- Rust適用率 = maybe_rust で RustEngine になり、終了まで Python へフォールバック
  しなかった局の割合（動的フォールバックの頻度）。
- 前提確認: サガデッキ全22種40枚は rustcore._is_plain を全て通る（静的ゲート100%）。
- load_rules の時間は対戦時間に含めず別表示（実測約22秒。初期化コストの償却は Phase 3 の課題）。

### 実測（2026-11-23、このVM: 共有1.5CPU）

Python のみ（dmcore 未ビルドのため Rust は無効）:

```
python tools/bench_2p.py --games 20 --engine python
  5.35 games/s, 541 decisions/s, 101 decisions/game, avg 20.4 turns
  wins P0=9 P1=11, first player win rate=0.35
```

- 当初このVMには Rust ツールチェーンが無く dmcore 未ビルドだった。ツールチェーンを
  入れてビルドしたところ、main の dmcore に以下の問題が見つかり、本PRで先行2件を直した。
  1. コンパイルエラー: setup.rs の GameState 初期化で action_limits / untap_caps が
     欠落（Python 側 state.py の第227弾・第254弾で追加された欄）。→ 空で初期化して修正。
  2. ゲートのクラッシュ: rustcore._simple_when が `from` がリスト形式の時に
     TypeError: unhashable type で落ちた。→ 文字列の時だけ集合判定するよう修正。
- 残る問題（Phase 2 の初手）: tests/test_rust_connect.py の test_random_games_match が
  digest 不一致で落ちる。切り分け済み: 対戦ログと勝敗は完全一致し、違うのは内部の
  記録だけ（turn_counters の atk_decl / blk_decl、prev_counters の casts 等、
  ev_seq 189 vs 171、steps_this_turn 98 vs 90、tasks の through_fired）。
  Rust 側が Python 側のカウンタ／イベント記録の追加に追随できていない。
  条件判定（turn_count 系）に効く欄を含むため、放置すると他のデッキで実挙動もずれ得る。
  このため verified_engine.txt のスタンプは更新していない（Rust は自動で無効のまま）。
  解消して test_rust_*.py が通ったらスタンプし直し、--engine auto でベンチを取り直す。
