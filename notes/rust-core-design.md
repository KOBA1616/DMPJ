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

## 段階2-a の結果（2026-11-09）
- 通常のカード実行（h_play: 保留→コスト支払い→召喚 move→bz）、攻撃できる者がいなければ attack は pass のみ、を移植。plain の lockstep が攻撃できるクリーチャーが出るまで全手・全 digest 一致。
- 速度（plain の約59手の対戦をパス方策で）: Python 約16 ms / Rust 約0.9 ms（fork 込み、約18倍）。Python 経由で1手ずつ JSON を往復する RustSession は 28 ms と遅い → 探索の内側は `Engine.run`（組み込み方策）や expand のように境界を跨がない形にする。
- 次: 2-b 攻撃・戦闘・シールドブレイク・勝敗。

## 段階2-b の結果（2026-11-09）
- 攻撃・バトル・シールドブレイク・ダイレクトアタック・窓（open/close/resolve_pending）・attack_end・break 後処理を plain 範囲で移植。ランダム方策4種×20シードの完全な1局（最大約110手）が決定・digest まで一致して終局。
- 「plain」の条件に、種族コマンド（出た時の seal_release が走る）を除外する条件を追加。lockstep が見つけた差で、段階を進めるたびに plain の定義を広げる運用が機能している。
- 速度（plain の1局・約37手）: Python 約15 ms / Rust 約0.6 ms（約25倍、fork 込み）。
- 次: 2-c セレクタ・式・条件・特性計算（能力を持つ札へ）。

## 段階2-c（第1弾）の結果（2026-11-09）
- 範囲: 自分自身にだけ及ぶ単純な常在型（allow: block / attack_summoning_sick / slayer / guardman、deny: attack_player / attack_creature / be_blocked / be_attacked、breaks）だけのクリーチャー。ブロッカー・スピードアタッカー・スレイヤー・W/T/Qブレイカー・攻撃不可などの札で約560枚。ブロック・ガードマン・スレイヤー・複数ブレイカーの選択が lockstep の対象になった。
- 実カードのランダムなデッキ×360シードで、全局が決定と digest まで一致。速度は1局で Python 約40 ms / Rust 約1.5 ms（約27倍）。
- Python 側が先へ進んでいた分に追従: 状態の新項目（dswitched / strigger_* / prev_counters / game_counters / declares）、履歴カウンタ（_record_history）、battle_end、attack_end.blocked、ハイパーの解除条件。
- ドリフト対策: ①tests/test_rust_schema_sync.py（Rust の状態項目が Python の dataclass と一致するかをビルド無しで検査）②.github/workflows/rust-lockstep.yml（Rust をビルドして lockstep を回す。情報提供で必須ではない）。Python 側のエンジン変更に Rust が遅れると、PR に失敗の抜粋が出る。
- 次: 誘発（trigger）と置換、選択肢をつくる式・条件・セレクタ（2-d）。札の約7割は誘発を持つので、ここが山場。

## 段階2-d 第1弾の結果（2026-11-10）
- 誘発の仕組みを移植: 履歴の ord 付与、誘発の収集（出た時・攻撃する時／自身）、待機（pending）、resolve_pending（ターン側から先、複数なら order_pending の決定）、効果インタプリタ（effect タスク）、lki（離れる前の姿。chars を含む）。
- 動く op: draw（枚数固定）・may（yes/no）・tap/untap（自身）。これらだけで書ける誘発を持つ札を追加して、動かせる札は約710枚。
- 実カードのランダムデッキ（誘発札を半分混ぜる）で 80 局が、yes_no を含む全決定・digest まで一致。
- 次: セレクタ（ゾーン・フィルタ・count・chooser）・式・条件、そして move / modify / tap（相手）などを頻度順に追加。

## 段階2-d 第2弾の結果（2026-11-10）: セレクタ＋移動／タップ

- Rust に `select`（ゾーン hand/deck/graveyard/mana/bz・持ち主 you/opp・枚数 int/all・from_top・chooser・types 絞り込み・`be_chosen` 禁止）と、
  op `move`（to: hand/graveyard/mana/deck、position）・`tap`/`untap`（任意セレクタ）・`shuffle`・`draw` の player を追加。
  効果が起こす移動には Python と同じく `by` と効果帰属（cause/cause_defn/cause_kind）を載せる（`ev_task_env`）。
- 通る札: 931 枚（うち誘発に move/tap/untap/shuffle を持つ 174 枚）。選択肢つき決定（choose_cards）を含む 150 ゲームで全手一致。
- 見つかった差: lki の chars.keywords は Python が sort＋重複除去（Rust は定義順だった）→ 修正。
- 未対応（Unsupported のまま）: 絞り込みの types 以外、count の式、up_to／any、`as`、シールド起点の移動（ブレイク経路）、バトルゾーンへ出す移動、choose/if/modify 等。

## 段階2-d 第3弾の結果（2026-11-10）: choose と変数参照

- `choose`（最上段のみ。as で変数に束縛）、セレクタの変数参照 `{ref: 名前}`（count／chooser／types 絞り込み）、`look` を追加。通る札は 957 枚。
- 変数の束縛を最上段に限る理由: Python は子タスク（may の本体など）と env を同じ辞書で共有するが、Rust は状態が JSON のため複製になり、子での束縛が親の env に出ない（ダイジェストが食い違う）。入れ子の束縛を通すには共有の再現が要る。
- 120 ゲームで全手一致。
- 次の壁（Rust 化できない札の、唯一の障害になっている語彙の数）: 複雑な常在型 約1640 枚、`when` が move/attack/turn_end/cast の他形 約530 枚、セレクタの他形 約270 枚、置換 約140 枚、if 約100 枚、modify 約70 枚。常在型（特性計算 chars）の移植が最大の山。
