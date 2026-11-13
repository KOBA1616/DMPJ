# 検証済みコンボの登録簿（ロードマップ P2「登録簿」、2026-11-13）

## 1. 窓口の約束
- 入力: 候補（`dmsim.base.registry.Candidate`）= 中核の札・型・勝ち方・入口局面か手順・区分・測り方（シード・ターン上限・budget）。
- 出力: 照会 `registry.query(types=, split=, for_tuning=, core_id=, win=)`。大局観 S3 と発見 S5 が読む。調整に使う経路は `for_tuning=True`（holdout を出さない）。
- 書き込み: `dmsim.eval.verify.register` だけ（中で `registry.record` を呼ぶ）。`record` は S4 の検証役が出した `Evidence` で、候補と同じ指紋のものしか受け付けない。`record` を呼ぶのが verify.py だけであることを `tests/test_registry.py` が確かめる。
- tuning / holdout / discovered: `split` で区別。holdout は `purpose="tuning"` で書くと `HoldoutWriteError`（`base/store.check`）。

## 2. 置き場と項目
- 型: `dmsim/base/registry.py`（S0、他層を import しない）。
- 候補: `data/registry/candidates.yaml`（人が書く）。元は `data/known_combos/combos.yaml` と `data/discovered_combos/combos.yaml`。どちらも形を変えていない（日次の自動実行が読む）。
- 登録簿: `data/registry/combos.yaml`（`tools/registry.py` が書く。手で書き換えない）。`entries`（通過）と `rejected`（落ちた候補と落ちた検証 `failed_at`）。
- 1件の項目: id・name・split・types（loop/resource/attack/lock、重複可、設計書 §11）・core（id・name・役割）・win（opp_deck_out/effect/lock/beat）・entry（入口局面）か procedure（手順の文）・lock_mode・seeds・max_turn・budget・digest（候補の指紋）・checks（各検証の合否と説明）・measured（段1・段2の到達率、勝ち方の内訳、勝ったターン、シードごとの行）・version（測定器とカードデータの fingerprint、commit、日付）。
- fingerprint が今と違う行は古い（測り直しの対象）。今は照会で弾かず、読む側が version を見る。

## 3. 検証（`dmsim/eval/verify.py`）
順に行い、最初に落ちた所で止める: cards（中核の札がカードデータにある）→ type（今の物差しで測れる型か）→ entry（入口局面がある）→ ruler（`ruler_control.run_one` と同じ測り方で各シード1局、段2到達率 ≥ 陽性対照の KNOWN_MIN=0.8、対局の失敗なし）→ replay（先頭2シードを回し直して開始局面の指紋・段1・段2・勝ち方・勝ったターンが一致）。閾値・budget は既存の値のまま（数字を合わせる調整はしない）。

### replay・shrink を S4 に寄せる計画
- すでに S4: `eval/replay.py`（手順の再生 replay_test）、`eval/shrink.py`、`eval/reproducibility.py`、`eval/lockcheck.py`（discovery 側は旧名の互換だけ）。
- 下の層に残るもの: `engine/loop.py` の `verify`・`replay_keys`（ループ証明書の再生、S2）、`engine/play.py` の `replay`・`replay_record`（ログの再生、S2）、`search/pattern_loop.py` の `replay_counts`（S3）。これらは下の層の部品なので移さず、S4 の verify から呼ぶ形にする。
- 次の段（今回は未実装）: (1) 登録時に勝った局の手順（`replay.steps_of`）を保存し、`replay_test` で手順の再生も確かめる。(2) `shrink` で入口局面の最小化をして core の自動抽出と突き合わせる。(3) 能動ロックの自分の方針（`lockcheck.prefer_policy`・探索）を候補に持たせて `make_full_lock_judge` で測る。

## 4. 既知4件と新規1件を通した結果（2026-11-13、各8シード、上限2ターン、budget は入口の既定）
| 候補 | 区分 | 結果 | 落ちた検証と理由 |
|---|---|---|---|
| アカシック（ナウ・オア・ネバー＋ウォカンナ） | tuning | **登録** | 段2 8/8、全部 loop、replay 一致 |
| サガ | tuning | 不可 | ruler: 段2 1/8（beat 6・loop 1・勝ちなし1）。探索がループを選び切れない（§12 と同じ。TurnSearch の作業待ち） |
| 騎士＋DMC | tuning | 不可 | type: リソース型の目盛りが未実装（設計書 §6 タスク12）。入口局面も無い |
| アカシック H.D.2.（新規） | discovered | 不可 | ruler: 段2 5/8（基準0.8）。外れた seed は手札にナウ・オア・ネバーが入り探索が L2 を選び切れない局面（data/discovered_combos の記録と同じ） |
| ドリル＋ジョバンニ＋クルト | holdout | 不可 | cards: ドリルスコールがカードデータに無い。その先も能動ロック（lock_mode=active）は type で落ちる |

同じシードで2回通して `data/registry/combos.yaml` が一致することを確認した。

## 5. 新規性判定（範囲）
`registry.novelty(候補)`: 登録済みと落ちた候補の中核の札の集合を比べ、same／superset／subset／overlap と、勝ち方が同じかを返す最小版。H.D.2. 版は既知アカシックと overlap（アカシック3・訪れる魔の時刻が共通、勝ち手段が違う）。
次の段（未実装）: 仕組みの比較（入口局面の 1周の差分 delta と勝ち方が同じなら同じ仕組み）、代わりのある組（loop_entry.core_groups の any）を考えた比較。
