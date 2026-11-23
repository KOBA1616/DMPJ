# 対戦AI化 Phase 計画（ポケカABC調査に基づく）

ポケモンカードAIの調査（小型Transformer＋自己対戦RL、対局中探索なし）を受けて、
本システムに対戦・学習レイヤーを追加する計画。各 Phase ごとに PR を作る（マージはしない）。
既存の探索系（コンボ発見用）は置き換えない。

| Phase | 内容 | 状態 |
|---|---|---|
| 1 | 2p対戦ベンチ新設（サガミラー、局/秒・決定/秒・Rust適用率） | 完了（本PR） |
| 2 | Rust追随と最適化（digest不一致の解消、ルールバンドルの再パース削減） | 完了（本PR） |
| 3 | バッチ並行API（Rust内部で複数局を一括実行） | 完了（本PR） |
| 4 | 方策エンコーダ（DSL→共通特徴トークン）＋小型モデル＋価値ヘッド＋自己対戦RL。通常デッキの追加もここ | 完了（本PR） |

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

## Phase 2: Rust追随と最適化

### digest不一致の解消（Rust側が Python の第231〜352弾相当に未追随だった分）

tests/test_rust_connect.py（27件）・test_rust_engine.py（293件）・
test_rust_schema_sync.py（3件）が全て通るようになった。verified_engine.txt を
再スタンプし、Rust は有効化されている。追随した内容:

- 戦闘・呪文の記録系カウンタ: atk_decl / blk_decl（第254弾）、casts（第261弾）、
  enter_unpaid / hist:used（第348弾ほか）、cast レコードの from（第226弾）
- attack_unblocked イベント（第229弾）と break_before レコード（第239弾）
- trigger レコードの再帰収集（第270弾。ev_seq の進みを一致させた）
- stack_bases の記録（第231弾）とゾーン移動時の消去、EXライフシールドと
  進化クロスギア（第304弾）の進化時引き継ぎ
- chars の欠けキー（evo_reduce / evo_reduce_min / player_rush）と mana_number の既定 null
- move レコードの対（照合用 _record_for / 収集用）の整備: battle（第332弾）、
  position の常時付与（第290弾）、unpaid の導出（第257弾）、was_under（第294弾）、
  alt / vivid / no_trigger の伝播
- mod.gain で得た能力の収集（第240弾）: 継続的効果・常在型からの付与を
  負の添字＋inline pending で Python と同形に実装（サバイバー等）。
  affects の `other: true`（発生源自身は対象外）も照合する
- instead（置換）子タスクの状態同期: Python では instead リストとスタック上の
  子タスクが同一オブジェクトで、解決中の pc 等がリスト側にも見える。Rust は
  値コピーなので、決定を返す前にスタック上の実物でリスト側を同期する
- ゲート側の陳腐化も判明: rustcore._self_mods は「常在型の gain は Python も
  扱わない」前提で gain 常在型を plain としていたが、Python は第240弾で対応済み
  だった（上記の収集実装で前提どおりの挙動に一致させた）

### 最適化: ルールバンドルの再パース削減（JSON境界）

- dmcore.Engine.open はルール一式（11.3MB の JSON）を毎局パースしていて
  実測135ms/局。ベンチ（--engine auto）の支配的コストだった。
- rustcore._open_core: 同じバンドルではテンプレートを1つだけ開き、以降は
  with_state（状態だけ差し替え、ルールは Arc 共有）で開く。RustEngine /
  RustSession の両方が使う。
- chars の版番号キャッシュと clone の copy-on-write は、今回の実測では
  ボトルネックがバンドル再パースだったため見送り（Phase 3 のバッチAPIで
  まとめて効かせる）。

### 実測（2026-11-24、このVM: 共有1.5CPU、サガミラー20局・ランダム方策）

```
python tools/bench_2p.py --games 20 --engine python   → 5.46 games/s, 552 decisions/s
python tools/bench_2p.py --games 20 --engine auto     → 8.01 games/s, 810 decisions/s
```

- バンドル再パース削減の前は auto が 3.79 games/s で Python より遅かった
  （135ms/局のパースが支配的）。削減後は Python 比 1.47 倍。
- 決定/秒で見ると Python 552 に対し Rust 810。残りの差は決定ごとの JSON
  受け渡しで、Phase 3 のバッチAPIでまとめて解消する想定。

- 勝敗は Python / Rust で同一（P0=9 P1=11、先攻勝率0.35）。Rust適用率は
  20局全て wrapped され最後まで維持（フォールバックなし）。

## Phase 3: バッチ並行API（dmcore.run_batch）

- `dmcore.run_batch(rules_json, states_json, policy, seed)`: ルール一式は1回だけ
  パースし、複数局を Rust 内部で最後まで実行して {winner, turn, decisions} の
  配列を返す。決定ごとの Python↔Rust 往復が無く、GIL を解放して実行する
  （呼び出し側のマルチプロセス／スレッド並行と併用できる）。
- 組み込み方策: "random"（Python の random_policy と同じ一様乱択の分布。
  乱数列は Rust 側 RNG のため駆動方式とは一致しない）と "first"
  （最小数を先頭から。決定的で、駆動方式と結果が完全一致することを
  tests/test_batch.py で検証）。
- Python 側: rustcore.run_batch(rules, states, policy, seed) と
  tools/bench_2p.py の --engine batch。
- 未対応の語彙に当たった局は {error} を返し、他の局は完走する
  （局単位で結果が欠けない）。

### 実測（2026-11-24、このVM: 共有1.5CPU、サガミラー・ランダム方策）

```
--games 100 --engine batch → 13.78 games/s, 1408 decisions/s（102 decisions/game）
--games 100 --engine auto  →  9.91 games/s, 1009 decisions/s（駆動方式・Rust）
--games 20  --engine auto  →  8.01 games/s,  810 decisions/s（Phase 2 時点）
```

- 駆動方式比で約1.4倍。残りの上限はエンジン本体の解釈実行で、Phase 4 の
  自己対戦では本APIをプロセス並行と組み合わせて使う想定。

## Phase 4: 方策エンコーダ＋小型モデル＋自己対戦RL（dmsim/ai/）

ポケカABC上位の共通形（カード1枚＝1トークン、最終勝敗のみの疎な報酬＋価値
ヘッド、対局中探索なし）を本システムの Decision インターフェース上に実装した。

- encode.py: 局面エンコーダ。公開ゾーン＋自分の手札のカードをトークン化
  （定義埋め込み＋コスト/パワー/タップ等の数値特徴）し、ゾーン別にプーリング。
  相手の手札・シールドの中身などの秘匿情報はトークン化せず枚数だけ全体特徴へ。
  選択肢は「動詞（key の接頭辞）＋参照札の定義/平均コスト・パワー」で符号化し、
  同じ特徴の同値合法手は自然に同スコアになる（重複合法手の集約に相当）。
- model.py: numpy 実装の小型モデル（約38万パラメータ。torch がこの環境に
  無いための手書き逆伝播で、勾配は数値勾配と全パラメータで照合済み）。
  方策は Plackett-Luce 型の逐次サンプリングで、単一選択・複数選択・順序付け
  （order_cards）を1つの分布で扱う。個数ヘッド（min..max の分布）と価値
  ヘッドを持つ。学習は REINFORCE＋価値ベースライン、報酬は最終勝敗のみ。
  Transformer 化（トークン間の注意）は次の拡張点で、現状はゾーン別
  プーリングがその最小形。
- selfplay.py / tools/selfplay_train.py: 自己対戦の収集→学習→評価ループ。
  評価はモデル（greedy）対ランダム方策。--deck で任意のデッキを指定でき、
  data/decks/ の通常デッキ（tenmon、akashic 等）でも収集・評価できる
  （異デッキ対戦の動作を tenmon 対 saga で確認済み）。
- tests/test_ai.py: エンコード形状、勾配の有限性、評価、保存/復元。

### 参考ラン（2026-11-24、このVM、サガミラー、15 iter × 8局＝120局・約1.2万決定、52秒）

```
[eval before] win rate vs random = 0.50（10W/10L、20局）
[eval after]  win rate vs random = 0.95（19W/1L、20局）
```

- ランダム方策は本ゲームでは非常に弱いため、これは「学習パイプラインが
  実際に方策を改善する」ことの確認であって強さの主張ではない。次の課題:
  greedy／leaf_eval 等の既存方策との対戦評価、Phase 3 バッチAPIを使った
  収集の高速化（現状の収集は駆動方式）、注意機構への置換、相手デッキ推定。

## Phase 5: 強い基準（greedy）との評価

- selfplay.evaluate に相手方策の指定（random / greedy / charge_only）を追加。
  greedy は dmsim/search/turn.py の greedy_policy（leaf_eval の手作り重みで
  最善手を選ぶ既存の貪欲方策）で、ランダムより遥かに強い基準。
- 参考ラン（2026-11-24、サガミラー、40 iter × 8局＝320局・約2.8万決定、122秒）:

```
[eval before] vs random: 0.50（10W/10L） / vs greedy: 0.20（4W/16L）
[eval after]  vs random: 1.00（20W/0L）  / vs greedy: 0.55（11W/9L）   ※各20局
```

- 学習前は greedy に大きく負けていたモデルが、320局の自己対戦だけで
  greedy をわずかに上回った。評価は各20局と小さいため誤差は大きいが、
  「手作り評価関数に自己対戦が追いつき始める」段階には達した。
- 次の課題: 評価局数を増やした再現確認、収集の高速化（駆動方式が律速）、
  注意機構への置換、相手デッキ推定、torch 導入（この環境ではダウンロード
  失敗のため未導入。導入できれば学習基盤を移す）。
