# Rust 化の設計メモ（試作段階）

日付: 2026-11-09 / 状態: 試作（rust/dmcore）。ユーザー承認済み。Python 版を「正」とし、同一シードの差分テストで一致を確かめながら移す。

## 1. 方針
- 境界は「状態そのもの」。Rust 側が State を持ち、Python からは `clone / digest / to_json / from_json / advance / answer` などを呼ぶ（PyO3、abi3）。
- ルール・カード定義の読み込みと検証（defs.py）は Python に残す。Rust へは正規化した JSON（版番号つき）で渡す。
- 探索・チューナー・自動実行は Python のまま始める（プロファイルでは時間の約85〜90%がエンジンと状態の複製）。エンジンを数十倍にしても全体は約4〜5倍が上限なので、その先は候補生成・抽象化・評価の移植を計測してから決める。
- Python 版エンジンは削除しない。差分テストの基準（oracle）として残し、語彙の追加・自動修正は当面 Python 版に先に入れる。

## 1.5 疑似API（先に定義する）
Rust 版と Python 版は、同じ「エンジン疑似API」（プロセス内ライブラリ。`open / decision / apply / fork / checkpoint / rollback / expand / observe / read / digest / trace / log / run / lockstep`）を満たす形で作る。ネットワークのサーバーにはしない（速度を失うため。熱い経路は JSON 化しない）。詳細は `notes/engine-api-v0.md`、Python 参照実装は `dmsim/engine_api.py`。探索・チューナー・自動診断・カード検証は、順次この API 経由に寄せる。

## 2. 互換性の契約（これが API）
1. 状態の JSON: Python の `GameState.to_json()`（sort_keys、区切り `,` `:`、非 ASCII そのまま）とバイト列で一致。digest は blake2b(16)。
2. 選択肢: 決定は `{player, kind, options[], min, max, prompt}`。答えは「選択肢の番号」なので、**選択肢の順序・key 文字列・cid などの中身**が一致しないとログ再生が壊れる。差分テストで 1 決定ごとに比べる。
3. 乱数: splitmix64（64 ビット固定幅）。`rng_below(n) = next % n`、シャッフルは Fisher–Yates を末尾から。
4. ハッシュ順に依存しない（PYTHONHASHSEED を変えても同一 digest を確認済み）。Rust では BTreeMap / 明示的な整列を使い、HashMap の反復順を結果に出さない。
5. 状態に整数キーの dict が1箇所ある（継続的効果の `double_power`）。JSON ではキーが文字列になるので、形を文字列キーに揃えてから移す。
6. 対戦ログ・replay は `{p, kind, choice, keys}`。key で再生できるので、選択肢の key が契約に含まれる。
7. step_limit・turn_limit の意味は同一。Python 側の先読み打ち切り（TurnSearch.rollout_cap）は探索側の仕様で、エンジン契約ではない。

## 3. 段階
- 段階0（完了）: State の serde（Python と同形）、canonical JSON、digest、splitmix64、準備（new_game: シャッフル・シールド5・手札5・最初のターンタスク）。
- 段階1: ルール JSON の書き出しと Rust 側ローダ。タスクスタックと `advance`、ターン進行（start / draw / charge / end）、イベント適用（move / draw / tap / untap）、`_distinct_hand_options` 相当。疑似API（`open / decision / apply / fork / digest / observe`）を Rust 版が満たし、`lockstep(Python, Rust)` を通す。未移植の語彙は `Unsupported` で返す。
- 段階2: セレクタ・式・条件・特性（chars）、op 44種、誘発、戦闘。実カード 9002 枚のコーパスで、op ごとに差分テストを通してから次へ。
- 段階3: 探索が使う読み出し API（zlist / bz_tops / chars / cdef / 状態の読み書き口）を Rust 側に用意し、solitaire・loop・eval を Rust のエンジンで回す。境界の呼び出し回数が多い所は一括取得にする。
- 段階4: 計測して、候補生成・`loop.abstract`・評価の移植を判断。

## 4. 差分テスト（段階1で最初に作る）
`engine_api.lockstep`（実装済み。`tools/rust_diff.py` はその CLI にする予定）: 固定シードの乱択ポリシーで、Python 版と Rust 版を 1 決定ずつ並走させる。毎決定で ①決定の kind・選択肢（key と順序）②状態の digest を比べ、最初のずれた決定のログと JSON 差分を出す。デッキはコーパスから多様に取る（実デッキ5種＋ランダム抽出）。CI では Rust 未ビルドなら飛ばす。

## 5. 試作の計測（2026-11-09、tenmon デッキの初期状態、32KB の JSON）
- 初期状態: 5デッキ × 20シード × 先後 = 200 局面で、Python 版と JSON が完全一致（digest も一致）。シード 2^63 超でも一致。
- clone: Python 51.2µs → Rust 5.8µs（約8.8倍、PyO3 の呼び出し込み）。
- digest: Python 687.5µs → Rust 57.7µs（約11.9倍）。
- 乱数: 100 回の `rng_next` が一致。

## 6. リスクと対処
- 選択肢の並びの再現（最大のリスク）→ 段階1から 1 決定ごとの差分テスト。
- エンジンが毎日変わる（語彙追加・自動修正）→ Python 版を先に変更し、Rust 版は差分テストが落ちた所を追う。語彙の追加は op 単位で小さく。
- 境界の費用（Python から状態を読む回数）→ 段階3で一括取得と、探索側の移植を計測して判断。
- ビルド環境（maturin、crates.io）→ このクラウド環境では利用可（cargo 1.97、maturin 1.16）。ローカルでは `cd rust/dmcore && maturin develop --release`。

## 段階1の結果（2026-11-09）
- Rust: タスクスタック・ターン進行・draw/untap/チャージ・パス・デッキ切れ・マナ選択肢（DFS）を移植（rust/dmcore/src/engine.rs）。
- `lockstep(Python, Rust)` が plain デッキ（T001 など）で全手・全 digest 一致（パス方策でデッキ切れまで約59手）。
- 未移植の語彙（play など）は `dmcore.Unsupported` で構造化して返り、lockstep は `ok: None, unsupported: …` を返す。
- 次（段階2）: play/h_play・セレクタ・式・条件・chars・44 ops・誘発・戦闘。
