# 語彙パイロット（2026-10-30）: 費用対効果の高い小さい語彙から

rejects 6,965件（gap 1,191種類）のうち、小さな実装で解けるものを試作した記録。
検証は `tests/test_vocab_pilot.py`（動作）と `tests/test_vocab_pilot_cards.py`（代表カードの parse）。

## 実装した語彙（新規）

| 語彙 | 旧 need | 件数 | 実装 |
|---|---|---:|---|
| `tap` の `no_untap_next: true` | does_not_untap_next_turn（freeze 系の一部も） | 20 | `Card.no_untap_next` の印。持ち主の次のターン開始時のアンタップ判定（501）で1回だけ消費し、`_raw_move` で離れたら外れる |
| キーワード `enters_tapped` | enters_tapped | 23 | `keywords.yaml` に追加。適用は EXライフと同じく move 適用時にキーワード名を見てタップ状態で出す |
| `op force_battle` | force_battle | 78 | `a`（攻撃側）／`b` の2体を共通の `_battle` でバトルさせる。`b` 省略時は `a` の先頭2体。対象は `choose` で変数に入れてから `ref` で指す |

合計 121件が対象。スキーマ（`data/schema/card.schema.json`）は
`python -m dmsim.schema > data/schema/card.schema.json` の再生成で自動追随する（変換時の語彙表にもそのまま載る）。

注意（force_battle）: バトル相手の置換（`battle_substitute`）は攻撃時のフローでのみ判定しており、
効果によるバトルでは未判定。実カードの置換持ちが絡むケースは今後の課題。

## main に既にあったもの

- `move` の `tapped: true`（旧 need: tapped_mana_placement、47件）: 当初パイロット側でも実装したが、
  現行 main に同名・同意味で実装済みだったため、パイロット版は破棄し main のものを使う（動作テストは残してある）。

## 実は既存語彙で表せたもの（エンジン変更不要）

変換側が「無い」と申告していたが、既存の組み合わせで表せた。次回の変換では rejects にしないこと。

| 旧 need | 件数 | 表し方 |
|---|---:|---|
| grant_until_next_turn_start | 126 | `modify` の `duration: until_next_own_turn_start`（既存。付与先は `play_free` の `as` → `modify {select: {ref: 変数}, mod: {grant: [...]}}`） |
| won_battle | 76 | 誘発 `when: {event: battle_win, subject: ...}`（既存イベント） |
| not_evolution_filter | 54 | `filter: {not_types: [evolution]}` |
| g_strike | 43 | キーワード `g_strike`（既存）。「見せた時」の追加能力も同じ shield→hand の move 誘発で表せる |
| evolution_filter | 26 | `filter: {types: [evolution]}`（types は OR 照合なので進化クリーチャーに当たる） |

合計 325件。代表カード9枚の手変換が `defs.parse_card` を通ることをテストで固定した。

## アンタップしない、の2文型（区別すること）

| 文型 | 意味 | 表し方 |
|---|---|---|
| A型「次の相手のターンのはじめにアンタップしない」（対象は相手のカード） | 対象の次のアンタップ機会を必ず1回飛ばす | `tap` の `no_untap_next: true` |
| B型「次の自分のターンのはじめまでアンタップしない」（対象は相手のカード） | 自分の次のターン開始で切れる期限型。相手対象では間の相手のアンタップを1回飛ばすが、相手のターン中に適用すると相手の次のアンタップより先に期限が切れることがある。自分対象では次の自分のターン開始で切れているのでアンタップする | `tap` ＋ `modify {select, mod: {deny: [untap_at_start]}, duration: until_next_own_turn_start}` |

「次の自分のターンのはじめにアンタップしない」（自分対象。こたつむり等）は A型と同じ1回スキップで、`no_untap_next` でよい。
B型は rejects では grant_until_next_turn_start と申告されていたものが多い（Disエビンビー等）。動作の違いは `tests/test_vocab_pilot2.py` で固定した。

# 第2弾（2026-10-30）

検証は `tests/test_vocab_pilot2.py`（動作）と `tests/test_vocab_pilot2_cards.py`（代表カードの parse）。

## 実装した語彙（新規）

| 語彙 | 旧 need | 件数 | 実装 |
|---|---|---:|---|
| 誘発の `once_per_turn: true` | once_per_turn_trigger | 47 | 収集時に `turn_counters` へ印（カードのオブジェクト＋能力番号）。「各ターンに一度」はその能力がそのターンに誘発済みかをゲートする。使用を断っても誘発自体は消費される |
| 誘発の `first_time: true` | first_time_per_turn_trigger | 53 | ゲートはコントローラー＋カード定義＋能力番号で共有し、印にはイベントの通し番号（`ev_seq`）を入れる。最初の出来事では場の全コピーが誘発し、次の出来事からは誘発しない。制限: そのカードが場に出る前に起きた出来事は数えない |
| 式 `civ_count: <selector>` | civ_count（11）＋ civilization_count（5） | 16 | 対象カード群にある文明の種類数（多色は持つ文明をすべて数える）。あわせて mod の `power` に `{amount, count}` 形式（「〜ひとつにつき+N」）を対応し、`power_when`／`battle_power`／`cost` の count でも式が使えるようにした |

## 実は既存語彙で表せたもの

| 旧 need | 件数 | 表し方 |
|---|---:|---|
| civil_count の大半（シビルカウント） | 51 | シビルカウントは「自分の（文明）のクリーチャーまたはタマシードの合計Nつ以上」で、文明の種類数ではない。`cmp` ＋ `count {zone: bz, filter: {types: [creature, tamaseed], civs: [...]}}` で表せる（ヴニースで確認）。真に種類数が要るのは civ_count 系の16件だけ |
| B型フリーズ（上記） | 15 | `modify` の deny ＋ duration（新規実装なし） |

## 次の候補

- freeze キーワード本体（攻撃してブロックされなかった時の誘発）: 「ブロックされなかった」イベントが無いので中規模 → 第3弾で対応（下記）
- first_attack_of_turn（18件）: first_time の攻撃版パターンで表せる可能性（要精査） → 第3弾で確認
- zone_count_comparison（15件）／cost_gt_count（14件）: 式の拡張で届くか精査 → 第3弾で確認

# 第3弾（2026-10-30）

検証は `tests/test_vocab_pilot3.py`（動作）と `tests/test_vocab_pilot3_cards.py`（代表カードの parse）。

## 実装したもの（新規）

| 語彙 | 旧 need | 件数 | 実装 |
|---|---|---:|---|
| キーワード `freeze` | freeze | 39 | `keywords.yaml` に定義。「ブロックされなかった」は break イベントの発生源が自分であることで判定する（ターボラッシュと同じ仕組み）。効果は may で選び、`tap` の `no_untap_next` で凍結する。制限: シールドが0枚の相手への攻撃はゲームが終わるので対象外。ブレイクを置換・軽減された場合は誘発しない |
| subject フィルタの式評価 | cost_gt_count（14）＋ cost_lt_count（9）の対象条件側 | 23 | 誘発・置換の subject 照合でも filter の式値を計算するようにした（従来は choose 等の selector 側だけ）。「マナの枚数よりコストが大きい」は `cost_ge: {sum: [{count: ...}, 1]}`、「墓地の枚数より小さい」は `cost_le: {sum: [{count: ...}, -1]}` |

## 実は既存語彙で表せたもの

| 旧 need | 件数 | 表し方 |
|---|---:|---|
| first_attack_of_turn | 18 | 「そのターンはじめての攻撃」は第2弾の `first_time` を攻撃誘発に付けるだけ（ピッケスで確認） |
| zone_count_comparison | 15 | 「自分のXが相手より多い/少ない」は `cmp` の両辺に `count` 式を置く（プロテクション・サークルで確認） |
| cost_gt_count の効果内 choose 側 | （上記と重複） | choose のフィルタは元々式が使えた（ペナルティフリートで確認） |

## 次の候補

- oni_time（43件）: 鬼タイム条件（自分のシールドが相手より少ない等＋専用処理）の精査 → 第4弾で確認（下記）
- summon_time_cost 系（34＋8件）: 召喚時のコスト条件・代替コスト
- entered_this_turn_condition（8件）／total_count_condition（6件）: 小粒の条件系

# 第4弾（2026-10-30）

検証は `tests/test_vocab_pilot4.py`（動作）と `tests/test_vocab_pilot4_cards.py`（代表カードの parse）。**新規実装は無し**。

## 鬼タイムは既存語彙で表せた

鬼タイムの条件は全カード共通で「自分と相手のシールドの数が合計6つ以下」:

```
oni = {cmp: [{sum: [{count: {zone: shield, owner: you}}, {count: {zone: shield, owner: opp}}]}, "<=", 6]}
```

| 形（43件中の内訳） | 件数 | 表し方 |
|---|---:|---|
| 常在型の付与（パワー+N、ブレイカー/ブロッカー/SA/スレイヤー付与、全体付与、破壊されない deny、召喚コスト-N） | 約21 | `static` ＋ `if: oni` ＋ `mod`（自分への付与は `affects: self`、コスト軽減は手札で効く常在型＝シンパシーと同じ） |
| 誘発に埋め込まれた形（「出た時／攻撃する時…、合計6つ以下なら追加効果」） | 7 | 誘発の effect 内に `if: oni` の分岐 |
| 残り（「真上の能力を無視する」系、勝敗の置換、選択の置換、無償召喚など） | 約15 | 個別対応が必要 |

ついでに確認した点:

- 「自分のシールドを手札に加える。ただし、そのS・トリガーは使えない」は、通常の move（shield→hand、reason: return）で足りる。S・トリガーの宣言はブレイクの流れでしか起きないため、「使えない」は自動的に満たされる（逆に「使ってもよい」形は現エンジンでは未対応）
- 自分への常在型は `affects: {self: true}` ではなく `affects: self` と書く

## 次の候補

- summon_time_cost 系（34＋8件）: 召喚時のコスト条件・代替コスト
- entered_this_turn_condition（8件）／total_count_condition（6件）: 小粒の条件系
- 鬼タイムの残り（「真上の能力を無視する」系 約8件）: mod の ignore で届くか精査
