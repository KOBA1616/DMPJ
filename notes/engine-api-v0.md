# エンジン疑似API v0.1（プロセス内ライブラリ）

状態: 設計＋Python 参照実装（`dmsim/engine_api.py`、`tests/test_engine_api.py`）。Rust 版（`rust/dmcore`）は同じ操作を満たす。

## 1. 採用の判断
- **採用する。ただしネットワークのサーバーではなく、プロセス内のライブラリ API とする。** 外部サービス化はしない。
- 理由: 探索の内側は 1 秒に数千〜数万回エンジンを呼ぶ。ネットワークや JSON の往復を挟むと、Rust 化で得る速度を失う（状態の JSON 化だけで約600µs、Rust の clone は約6µs）。
- 2層にする:
  - **熱い経路**（探索の内側）: ハンドルを持ち回る関数呼び出し。`fork / apply(番号) / decision / read` は JSON 化しない。参照実装の呼び出し層の費用は、計測で素の Engine と同等（1決定あたり約530〜580µs、差は誤差内）。
  - **冷たい経路**（ログ・差分検証・ツール・開発者モード・将来の外部連携）: 入出力は JSON で表せる辞書。必要になった時に、同じ操作を薄い JSON-RPC（標準入出力）で包める。熱い経路には影響しない。
- 今あるものを置き換えるのではなく、既存の使い方（`devserver.Session`、`scenario.build`、`play.replay`、`eval/steplog`、`verify`、`infoset.determinize`）を、同じ小さな操作の集合に寄せていく。

## 2. 操作（言語非依存の定義。Python 名で記す）
| 操作 | 内容 | 使う側 |
|---|---|---|
| `open(spec)` | `new_game{decks,seed,first_player}` / `scenario{...}`（配置指定）/ 将来 `state{json}`（局面の注入） | 全部 |
| `decision()` | 次の決定 `{id, player, kind, options[{key,...}], min, max, prompt}`、終局なら None。`id` は選択数で、差分検証の位置合わせに使う | 探索・検証 |
| `apply(answer, digest=False)` | 番号 or `{keys:[...]}` で答えて次の決定まで進める。`{applied, decision, result[, digest, trace]}` | 全部 |
| `fork()` / `checkpoint()` / `rollback(id)` | 枝分かれ・巻き戻し（clone ベース。再生に頼らない） | 探索・開発者モード |
| `expand(answers?)` | 現在の決定の各答えごとに fork して適用（呼び出し回数を減らす一括 API） | 探索 |
| `observe(view)` | 状態の JSON。`full` / `player:N`（見えない札を伏せる＝公平探索・AIの入力） | 評価・学習・UI |
| `read(what, ...)` | 読み取り専用の問い合わせ: zone / bz_tops / chars / card（状態は変えない） | 探索・診断 |
| `digest()` | 状態全体のハッシュ（重いので要る時だけ） | 差分検証・ログ |
| `trace(on)` | 誘発の因果の記録（apply の戻りに付く） | カード検証・診断 |
| `log()` | `{p, kind, choice, keys}` の選択ログ（key で再生できる） | 記録・再現 |
| `run(policy)` | 方策 id（`first / passive / random:<seed> / greedy`）で最後まで | 検証・計測 |
| `diff_states(a, b)` / `lockstep(a, b, policy)` | 状態の差（JSON ポインタ）／2実装を1決定ずつ並走させ、決定（選択肢の key・順序・中身）と digest の最初のずれを返す | Rust 移行・回帰 |

## 3. 契約
- 決定の `options` の順序・key・中身が API の一部（答えは番号で返すため）。`lockstep` が毎決定で比べる。
- 状態は純データ（JSON で表せる）。canonical JSON（sort_keys・区切り `,` `:`）のバイト列が一致することを契約にする。
- エラーは種類を分ける: `IllegalAnswer`（答えが範囲外）/ `NoDecision`（決定待ちでない）/ `Unsupported{op|kind}`（未対応の語彙。Rust 版が未移植の op に当たった時に、落ちずに構造化して返す＝移行の進捗表になる）/ `LimitExceeded`（step_limit / turn_limit）。
- 版: `API_VERSION`、ルール語彙の版、エンジン版を `capabilities()` で返し、ログ（explog）に残す。

## 4. 拡張性・汎用性
- ルールの語彙はデータ表（op 名 → ハンドラ）で登録する（現状の registry と同じ）。Rust 版も同じ表の形にし、語彙の追加は「表に1行＋ハンドラ」で済ませる。
- 未移植の語彙は `Unsupported` で返し、自動診断（autofix）が「Rust 版で動かないカード」を数えられるようにする。
- 局面の注入（`scenario`・将来の `state`）は、カード検証・ループ探索の仕込み局面・デッキ診断が共用する。
- 隠れた情報（`observe("player:N")`）と determinize を API に含め、公平探索を実装の外から使えるようにする。
- 方策・評価・相手モデルはエンジンの外（呼び出し側）。エンジンは「状態と決定」だけを持つ。

## 5. 検証・自動化
- 適合性テスト（conformance）: 同じ `lockstep` を、Python 版どうし（決定性の自己検証）、Python 版と Rust 版（移行の回帰）、コーパスの実カード・多様なデッキ・乱択方策で回す。差が出たら最初のずれの決定と JSON 差分を出す。
- 記録の正本: Python 版が作った選択ログ＋決定ごとの digest を、保存して Rust 版の回帰に使う（explog と同じ形式に寄せる）。
- 計測: 決定/秒・ノード/秒を API から取れるようにし、日次実行の予算配分（`deckplan/budget`）と速度の回帰検出に使う。
- すべての道具（探索・チューナー・autofix・カード検証・devserver）が `open / decision / apply / fork` で書けるようにし、バックエンドの差し替え（Python / Rust）を引数1つにする。

## 6. 段階
1. （今回）API の定義と Python 参照実装、`lockstep` と適合性テスト。
2. Rust 版が `open / decision / apply / fork / digest / observe` を満たす（段階1の移植と同時）。`lockstep(Python, Rust)` を通す。
3. 探索・チューナー・自動診断を、エンジン本体の直接参照から API 経由へ順に移す（挙動は変えない。各移行で結果一致を確認）。
4. 必要になったら JSON-RPC の薄いラッパ（devserver・外部ツール向け）。
