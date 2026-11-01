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

- summon_time_cost 系（34＋8件）: 召喚時のコスト条件・代替コスト → 第5弾で精査（下記）
- entered_this_turn_condition（8件）／total_count_condition（6件）: 小粒の条件系 → 第5弾で対応
- 鬼タイムの残り（「真上の能力を無視する」系 約8件）: mod の ignore で届くか精査

# 第5弾（2026-10-30）

検証は `tests/test_vocab_pilot5.py`（動作）と `tests/test_vocab_pilot5_cards.py`（代表カードの parse）。

## 実装したもの（新規）

| 語彙 | 旧 need | 件数 | 実装 |
|---|---|---:|---|
| 式 `entered: {owner, other?}` | entered_this_turn_condition | 8（うち約5がこの式で届く形） | このターン、そのプレイヤーがバトルゾーンに出したクリーチャーの数。move の適用時に `turn_counters` へ記録し、ターン開始でリセット。`other: true` で自分自身を除く（「すでに自分の他のクリーチャーが」）。「２体目」は cmp に `=` が無いので `>= 2` と `< 3` の `all` で挟む |

## 実は既存語彙で表せたもの

| 旧 need | 件数 | 表し方 |
|---|---:|---|
| total_count_condition | 6 | 「場とマナにあるジョーカーズが合計N以上」は `sum` に2つの `count`。G・ゼロはカード欄外の `free_if` に同じ条件を書く。シールドゾーンでキーワードを得る形は `static` の `zone: shield` ＋ `grant`（サンダイテイオーで確認） |

## summon_time_cost（8件）は見送り

全件が「召喚する時に〜してもよい。そうしたら/につき コストをN少なくする（下限あり）」で、支払い時に任意の行動（手札を見せる・捨てる、シールドを手札に加える、墓地の呪文を山札に戻す）を伴う。既存の `opt_reduce` は「減らす代わりにターン終了時に処理」という別タイミングの仕組みなので流用できず、支払いフローへの組み込みが要る（中規模）。次弾で扱う。

## 次の候補

- summon_time_cost（8件）: opt_reduce の支払い時アクション拡張 → 第6弾で対応（下記）
- 鬼タイムの残り（「真上の能力を無視する」系 約8件）: mod の ignore で届くか精査
- data_incomplete 以外で残る中規模: g_link（37件）、soul（キーワード複合）など

# 第6弾（2026-10-30）

検証は `tests/test_vocab_pilot6.py`（動作）と `tests/test_vocab_pilot6_cards.py`（代表カードの parse）。

## 実装したもの（新規）

`opt_reduce` に支払い時の行動 `do` を追加した（rejects: summon_time_cost 8件）。

```
opt_reduce: {amount: 2, floor: 0,
             do: {select: <selector>, min: 1, max: 1, move_to: graveyard?, shuffle: true?},
             per: true?}
```

- 「減らして実行する」を選ぶと、支払いの前に `select` で燃料を選ぶ。`move_to` があれば選んだカードをそこへ動かしてから支払う（手札を見せるだけなら `move_to` なし＝カードは残る。捨てる＝graveyard、シールドを手札に加える＝hand、墓地から山札へ＝deck＋shuffle）
- `per: true` なら軽減量は `amount × 燃料の件数`（「１枚につき」）。`floor` が下限（「コストは１より少なくならない」→ floor: 1）
- 燃料の候補から実行中のカード自身は常に除く（「他のカード」と明記がなくても自分は対象にできない）
- 行動できない（候補が無い）場合は軽減自体が得られない
- 従来の `then`（B・A・D / J・O・E のターン終了時処理）とは併用・単独どちらでもよい

## 次の候補

- 鬼タイムの残り（「真上の能力を無視する」系 約8件）: mod の ignore で届くか精査 → 第7弾で対応（下記）
- g_link（37件）: G・リンクの精査 → 第7弾で精査（下記）
- コスト参照系: paid_cost_reference など小粒の残り

# 第7弾（2026-10-31）

検証は `tests/test_vocab_pilot7.py`（動作）と `tests/test_vocab_pilot7_cards.py`（代表カードの parse）。

## 実装したもの（新規）

能力の `id` と mod の `ignore_ids`（rejects: oni_time の「真上の▪️能力を無視する」系 9件）。

- 能力に任意の `id`（文字列）を付けられるようにした
- `mod: {ignore_ids: [id, ...]}` を持つ常在型（自分宛）や継続的効果が及ぶクリーチャーでは、`abilities()` の収集時点で id が一致する能力が落ちる。種類単位で落とす既存の `ignore`（608.4）とは別機構
- 変換の約束: 鬼タイムで無視したい「真上の能力」に id を付け、鬼タイム側は第4弾の条件＋ `ignore_ids` で書く。キーワード由来の能力（「攻撃できない」等）を無視したい場合は、キーワードの展開形を id つきの能力として直接書く

## g_link は見送り（規模の見積もり）

g_link の単独ギャップは **120件**と最大級だが、G・リンクは「左・中央・右の位置を持つリンク」「リンクしたゴッド同士を1体のクリーチャーとして扱う」など、バトルゾーンの表現そのものに手を入れる大型機構で、小さい語彙の試作の枠を超える。やるなら専用の弾として、リンク状態の持ち方（進化の重ね表現が流用できるか）から設計する必要がある。

## 次の候補

- 小粒の残り: paid_cost_reference、entered 系の派生など、単独ギャップの棚卸しから
- g_link（120件）: 専用弾として設計から

# 第8弾（2026-10-31）

検証は `tests/test_vocab_pilot8.py`（動作）と `tests/test_vocab_pilot8_cards.py`（代表カードの parse）。

## 実装したもの（新規）

op `mekurade`（rejects: mekurade、単独49件）。

- `{op: mekurade, filter: {...}, cost_le: N, look?: 3}`: 自分の山札の上から look 枚（既定3）を見て、filter と cost_le に合う1枚をコストを支払わずに使ってもよい（0枚も選べる）。残りは好きな順序で山札の下に置く
- 「ゴッド・メクレイド5」「マジック・メクレイド5」など、対象は種族（race_has）・タイプ・文明いずれも filter で表す。コスト上限なしの「メクレイド∞」は cost_le を付けない
- op 引数の型に `filter` を追加した（registry / defs / schema の3か所）

## 棚卸しメモ（g_link・data_incomplete を除く単独ギャップ上位）

大きいものは軒並みゾーンやカード種別に触れる機構（neo_evolution 251、star_evolution 153、gr_summon 141、aura 108、shinkaraizu 94、hyper_mode 94、hyperdimensional_zone 94、crystal_arms 76、d2_field 64、cross_gear 60、dragheart 40）。小さい語彙の枠で次に狙えるのは optional_cost_reduction 78（「各ターンに1度、〜の召喚コストを1少なくしてもよい」系。opt-in の常在型コスト軽減で、サンプルはヴェヌス等の奇跡妖精）、space_charge 42（マナに置かれた時の文明別誘発）、abyss_rush 36（墓地からの召喚＋攻撃可＋終了時に山札の下）、kirifudash 49（攻撃終了時の条件つき召喚）あたり。

## 次の候補

- optional_cost_reduction（78件）: 「してもよい」の常在型コスト軽減 → 第9弾で一部対応（下記）
- space_charge（42件）／abyss_rush（36件）／kirifudash（49件）
- g_link（120件）: 専用弾として設計から

# 第9弾（2026-10-31）

検証は `tests/test_vocab_pilot9.py`（動作）と `tests/test_vocab_pilot9_cards.py`（代表カードの parse）。

## 実装したもの（新規）

mod `cost_may {amount, once?, min?}`（rejects: optional_cost_reduction の常在型分）。

- 「自分の〜の召喚／詠唱コストをN少なくしてもよい」を、発生源の常在型の `mod: {cost_may: {...}}` で表す。対象は affects（zone: hand ＋ filter）で指定する
- プレイ時に発生源ごとに「減らす／通常」を選び、`once: true` なら発生源ごとにターン中1回まで（使用記録は turn_counters）。実行可否の判定（_opt_reduced）にも織り込み済み
- 制限: 継続的効果（modify）由来の cost_may は発生源を引けないため未対応

## optional_cost_reduction の残り

この語彙名の申告は混成で、残りは別機構: 自分の召喚時の任意軽減（第6弾の opt_reduce の do / per で表せるものを含む。例:「墓地の呪文1枚につき」は do なしの per 型で要精査）、相手のカードへの任意軽減など。

## 次の候補

- space_charge（42件）／abyss_rush（36件）／kirifudash（49件）
- g_link（120件）: 専用弾として設計から

# 第10弾（2026-10-31）

検証は `tests/test_vocab_pilot10.py`（動作）と `tests/test_vocab_pilot10_cards.py`（代表カードの parse）。

## 既存の語彙で表せたもの（新規実装なし）

space_charge（単独42件）: スペース・チャージは、文明ごとの行を誘発に分けて書ける。

- 型: `{kind: trigger, when: {event: move, to: mana, subject: {owner: you, filter: {civs: [<文明>]}}}, effect: [{op: may, body: [...]}]}`
- 置かれたカードがイベントの subject になるため、その文明で絞れる。多色のカードを置いた時は合う行がそれぞれ誘発する。通常のチャージでも、効果でマナゾーンに置いた時でも発火する
- 注意（第11弾で判明）: 誘発能力の `optional` はエンジンでは効かない（置換候補でのみ効く）。「使ってもよい」は効果の先頭に `may` を置いて表すのが正しい型

## 次の候補

- abyss_rush（36件）／kirifudash（49件）
- g_link（120件）: 専用弾として設計から

# 第11弾（2026-10-31）

検証は `tests/test_vocab_pilot11.py`（動作）と `tests/test_vocab_pilot11_cards.py`（代表カードの parse）。あわせて第10弾の検証に「断れる」ケースを追加し、代表カードの型を効果側 may に直した。

## 実装したもの（新規）

キリフダッシュ（rejects: kirifudash、単独49件）。

- イベント `attack_end` を追加。攻撃タスクの終了時に、攻撃クリーチャーを subject として発火する。攻撃開始時に通し番号を振り、ブレイク側が「どの攻撃でブレイクしたか」を記録することで、「その攻撃中にシールドをブレイクしていれば」を when の `broke: true` で指定できるようにした
- op `play_self {cost, civs?}`: このカード自身を代替コストで実行する。支払いは通常の play の流れ（コスト mod は上乗せ、他の軽減は代替コストが優先）
- 変換の型: `{kind: trigger, zone: hand, when: {event: attack_end, broke: true, subject: {owner: you}}, effect: [{op: may, body: [{op: play_self, cost: N, civs: [...]}]}]}`。[XYnn] の nn が総額、XY が必要な文明（[cc00] は cost: 0, civs: []）

## 次の候補

- abyss_rush（36件）
- g_link（120件）: 専用弾として設計から

# 第12弾（2026-10-31）

検証は `tests/test_vocab_pilot12.py`（動作）と `tests/test_vocab_pilot12_cards.py`（代表カードの parse）。

## 実装したもの（新規）

アビスラッシュ（rejects: abyss_rush、単独36件）。エンジンの流儀（ルール側はキーワード名を見ない）に合わせ、許可ベースで組んだ。

- 許可 `summon_from_graveyard` を permissions.yaml に追加。キーワード `abyss_rush` は墓地で機能する常在型（allow: summon_from_graveyard）に展開される
- メインステップの選択肢に、墓地のアビスラッシュ持ちが `play:<カード>:rush` として出る（通常コストを払う）
- ラッシュで召喚すると: そのターンは召喚酔いでもプレイヤーだけは攻撃できる（turn_counters に印。クリーチャーへの攻撃は不可）、ターンの終わりに山札の下に置かれる（delayed_trigger を登録）

## 次の候補

- 小粒の残ギャップの棚卸し（単独20件以下の層）
- g_link（120件）: 専用弾として設計から

# 第13弾（2026-10-31）

棚卸し（単独ギャップの残り上位）から3件をまとめた。検証は `tests/test_vocab_pilot13.py`（動作）と `tests/test_vocab_pilot13_cards.py`（代表カードの parse）。

## opt_reduce の do に tap（summon_time_alternative_cost 34件の一部）

「召喚する時、自分のクリーチャーを1体タップしてもよい。そうしたらコストをN少なくする」型に対応。`do: {select, tap: true}` と書くと、燃料をタップしてから支払う（ゾーンは動かない）。手札を捨てる・シールドを墓地に置く・エレメントをマナに置く・味方を手札に戻す（per 対応）分は第6弾の move_to で既に表せる。

## revolution_condition（36件）は既存表現可

「革命N―自分のシールドがNつ以下なら」は oni_time と同じ条件接頭辞。常在型の if に cmp（シールド数 <= N）を置けばパワー修整とブレイカー付与（breaks）が切り替わり、呪文・誘発では効果内の if/else で「すべて／1体」を分ける（Rev.スパークで確認）。

## race_addition（35件）: mod add_races を実装

`mod: {add_races: [種族...]}` で chars の種族に足す。対象ゾーンが複数（バトルゾーン+墓地など）の文面は、ゾーンごとの常在型に分けて書く。条件つきで自身に足す形（「〜があれば、種族に〜を追加する」）も同じ mod でよい。

## 次の候補

- galaxyshield（35件）: 表向きシールド＋代替コスト＋ターン開始時の召喚が絡む中規模機構
- smash_burst（34件）: 攻撃時にバトルゾーンに置いたまま呪文面を唱える（ツインパクトの面の扱いが要る）
- g_link（120件）: 専用弾として設計から

# 第14弾（2026-10-31）

検証は `tests/test_vocab_pilot14.py`（動作）と `tests/test_vocab_pilot14_cards.py`（代表カードの parse）。

## 実装したもの（新規）

スマッシュ・バースト（rejects: smash_burst、単独34件）に対応する op `cast_face {face}` を追加した。ツインパクトの呪文面を、カードをバトルゾーンに置いたまま唱える。唱えたことにはなる（cast イベントを起こす、コストは支払わない）が、カード自体は動かず解決後に墓地へも行かない。呪文面の after_resolve も続けて解決する。変換の型は、クリーチャー面の攻撃時誘発に may + cast_face を置く形。

## 次の候補

- galaxyshield（35件）: 表向きシールド＋代替コスト＋ターン開始時の召喚が絡む中規模機構
- g_link（120件）: 専用弾として設計から

# 第15弾（2026-10-31）

検証は `tests/test_vocab_pilot15.py`（動作）と `tests/test_vocab_pilot15_cards.py`（代表カードの parse）。

## 実装したもの（新規）

ギャラクシールド（rejects: galaxyshield、単独35件）。文面は全カード共通の3点セットで、それぞれに受け皿を作った。

- 代替コスト: 面に `galaxy_shield: {cost, civs}` を宣言する。メインステップに「:gshield」の選択肢が出て、払うと召喚ではなく表向きでシールドゾーンに置かれる（move イベントに face_up を付け、シールドに入る時に表向きになる。move op の `face_up: true` も対応）
- 「表向きでシールドゾーンに置かれた時」の誘発: when に `face_up: true` を書けるようにした（move の記録に face_up を伝える）。この誘発は zone: shield で機能させる
- ターン開始時の召喚: op `summon_self` を追加。zone: shield の誘発（when turn_start、条件は新しい条件式 `face_up`）から使い、支払いはしないが「コストを支払ったものとして」召喚する（summon イベントの unpaid が立たない）

## 次の候補

- 単独ギャップは35件以下が尽きた。残りは大型ゾーン機構（neo_evolution 251、star_evolution 153、gr_summon 141、aura 108、shinkalaizu 94、hyper_mode 94、hyperdimensional_zone 94、crystal_arms 76、d2_field 64、cross_gear 60、dragheart 40）と g_link 120件
- 多重ギャップ側（2種類以上の組み合わせ）の棚卸しも選択肢になる

# 第16弾（2026-10-31）: ゴッドリンク

計画は `docs/g-link-plan.md`（実装状況もそちらに記載）。rejects: g_link、単独120件。

- グループ表現（Card.link）と特性統合（パワー・コストは合計、キーワード等は和集合、代表1体として扱う）
- 出た時のリンク手順（中央はリンク外し→リンク先、左/右はリンク先のみ）
- 離脱の置換（グループが離れる時は中から1枚だけが離れる）
- 式 link_count（「カードN枚でリンクしていれば」）

検証は `tests/test_vocab_pilot16.py`（全サイクル＋離脱置換）と `tests/test_vocab_pilot16_cards.py`（代表カードの parse）。

## 対象外（2026-10-31 ユーザー指示）

- GR召喚・オーラ・超次元はオリジナルフォーマットではないため、明示的にスキップする

## 次の候補

- 進化系: NEO進化（251件、二択の出し方＋重なっている時の性質変化）、スター進化（153件、離れる時は一番上だけ）
- シンカライズ（94件）は実装済み（キーワード shinka_rise）なので、変換側の精査で解ける見込み
- 多重ギャップ側の棚卸し

# 第17弾（2026-10-31）: NEO進化

検証は `tests/test_vocab_pilot17.py`（動作）と `tests/test_vocab_pilot17_cards.py`（代表カードの parse）。rejects: neo_evolution、単独251件。

- 面に `neo: true` と evolve_from を宣言する（types に evolution は入れない）。通常召喚の選択肢に加えて「:neo」の重ねて出す選択肢が出る
- 重ねて出た時だけ chars の types に evolution が加わる（「NEO進化クリーチャーとして扱う」）。「それがNEO進化クリーチャーなら」は、自身を types: [evolution] で見る exists 条件で書く

## 次の候補

- スター進化（153件）: 離れる時は一番上のカードだけが離れる（スタックの分離を常時化する印が要る）
- 多重ギャップ側の棚卸し

# 第18弾（2026-10-31）: スター進化

検証は `tests/test_vocab_pilot18.py`（動作）と `tests/test_vocab_pilot18_cards.py`（代表カードの parse）。rejects: star_evolution、単独153件。

- 面に `star: true` を宣言する。離れる時は一番上のカードだけが離れ、下のカードは再構築（既存の「カードとして離れる」処理）でバトルゾーンに残る
- ついでに filter へ `any_of`（OR 条件）を追加した。スター進化の進化元「レクスターズまたは〈文明〉のクリーチャー」がこれで書ける

## 次の候補

- 大型ゾーン機構の残りは crystal_arms（76件）、d2_field（64件）、cross_gear（60件）、hyper_mode（94件）、dragheart（40件）。GR・オーラ・超次元は対象外（ユーザー指示）
- 多重ギャップ側の棚卸し

# 第19弾（2026-10-31）: ハイパーモード

検証は `tests/test_vocab_pilot19.py`（動作）と `tests/test_vocab_pilot19_cards.py`（代表カードの parse）。rejects: hyper_mode、単独94件。

- 面に `hyper: true` を宣言する。メインステップに「ハイパー化」の選択肢が出て、自分の他のクリーチャーを1体タップすると解放される（タップはイベントを通す）
- ハイパーモードでだけ働く能力は条件 `{hyper: true}` で書く。次の自分のターンのはじめに解ける

## 次の候補

- crystal_arms（76件）、d2_field（64件）、cross_gear（60件、基盤は既存）、dragheart（40件）
- 多重ギャップ側の棚卸し

# 第20弾（2026-10-31）: Zラッシュ

検証は `tests/test_vocab_pilot20.py`（動作）と `tests/test_vocab_pilot20_cards.py`（代表カードの parse）。rejects: hyper_mode の一部（Zラッシュ持ち）。

- キーワード `z_rush` を追加した。自分のカードがシールドゾーンを離れた時に誘発し、op `hyper_mode`（新規）で自身をハイパーモードにする
- 期限の解釈を修正した。「次の自分のターンのはじめまで」は、相手のターンに解放された場合は来る自分のターンを丸ごと含む（一神のI ガナストラが Zラッシュ後に攻撃できることからの確認）。解放したターン番号を持ち、ターン開始時の解除条件に使う。第19弾のハイパー化（自分のターンに解放）の挙動は変わらない

## 次の候補

- crystal_arms（76件）、d2_field（64件）、cross_gear（60件、基盤は既存）、dragheart（40件）
- 多重ギャップ側の棚卸し

# 第21弾（2026-10-31）: Zラッシュの作り替え（ユーザーの指摘による）

第20弾の Zラッシュは2点が誤っていたため作り替えた。検証は差し替えた `tests/test_vocab_pilot20.py`。

- 誘発型ではなく常在型: Zラッシュはシールドが離れた瞬間に発動する誘発効果ではない。公式Q&A（48466）によれば「Zラッシュを持つクリーチャーがバトルゾーンにいる間にシールドが離れた際」に、そのクリーチャーのハイパーモードを即座に解放する常在型能力。実装は、カードがシールドゾーンを離れたイベントの適用時に、その時点でバトルゾーンにいる Zラッシュ持ち全員（両プレイヤー）の hyper の旗を立てる形にした。S・トリガーの使用より前に解放される。キーワード z_rush は印だけになり、第20弾で足した op hyper_mode は削除した
- 後から出たクリーチャーには適用されない: 解放されるのはシールドが離れた際に場にいたクリーチャーだけ（Q&A の「バトルゾーンにいる間に」）
- 期限は文字通り: 「次の自分のターンのはじめまで」は、相手のターンにブレイクされても自分のターンのはじめで戻る。第20弾で入れた「来る自分のターンを丸ごと含む」解釈（hyper_turn）は誤りだったので撤回し、ターン開始時の解除は無条件に戻した

## 次の候補

- crystal_arms（76件）、d2_field（64件）、cross_gear（60件、基盤は既存）、dragheart（40件）
- 多重ギャップ側の棚卸し

# 第22弾（2026-10-31）: クロスギアは既存実装で表せる

検証は `tests/test_vocab_pilot22.py`（動作）と `tests/test_vocab_pilot22_cards.py`（代表カードの parse）。rejects: cross_gear、単独60件。新規実装なし。

- クロスギアのジェネレート、メインステップでコストをもう一度払うクロス、クロス先が離れてもギアが残る処理はすべて既存にある（tests/test_vocab_cross.py もある）。rejects の申告が古い側
- 変換の型: クロスしたクリーチャーへの常在型は affects: crossed、誘発は subject: crossed。クロスギアを出す効果は通常の move

## 次の候補

- crystal_arms（76件）、d2_field（64件）、dragheart（40件）
- 多重ギャップ側の棚卸し

# 第23弾（2026-10-31）: クリスタルアームズ（水晶武装）

検証は `tests/test_vocab_pilot23.py`（動作2件）と `tests/test_vocab_pilot23_cards.py`（代表2枚）。rejects: crystal_arms、単独76件。

- 水晶武装の本体は「マナゾーンのカードを裏向きにする」効果と、「裏向きのマナがN枚以上」という条件。裏向きのマナは無色カード（マナの数字は元のまま）として扱う
- 実装: Card.face_down（マナゾーンを離れたら戻る）、op `flip_down`、filter の `face_down`、支払い計算で裏向きマナを文明なしとして扱う（グループ分けを変更）
- 変換の型: 「水晶武装N」は条件 `if: {cmp: [{count: {zone: mana, owner: you, filter: {face_down: true}}}, >=, N]}` を常在型・誘発・コスト軽減に付けて書く
- 制限: 「裏向きのままマナゾーンに置く」（シャングリラ・クリスタル等）は move 側の対応が別途必要。裏向きマナに文明を与える効果（玉座のタマシード等）も未対応

# 第24弾（2026-10-31）: フェーズ2（攻撃時すげ替え系）

検証は `tests/test_vocab_pilot24.py`（動作4件）と `tests/test_vocab_pilot24_cards.py`（代表4枚）。対象: revolution_change 63件、invasion 60件、attack_chance 54件、j_change 26件。

- 革命チェンジとアタック・チャンスは既存の declare の型で表せた（申告切れ）。革命チェンジ＝ declare + swap、アタック・チャンス＝ declare + play_free
- 侵略は op `invade` を新設（手札のクリーチャーを攻撃中のクリーチャーの上に重ね、進化と同じ _stack で攻撃を引き継ぐ）
- J・チェンジのため swap を拡張: `out_to`（既定 hand、mana で J・チェンジ）と、入る側の選択（ref でない selector は select で選ぶ）
- filter に `civs_all`（すべての文明を持つ）を追加（アタック・チャンスの条件用）
- ムゲンクライム（42件）は支払い方法の拡張が別途必要でフェーズ2には含めなかった
- 制限: 「革命チェンジによって出た時」（ファイナル革命）の via 照合、侵略カードの ETB の一部（捨てた枚数参照）は未対応

# 第25弾（2026-11-01）: フェーズ3（フィールド/ゾーン系）

検証は `tests/test_vocab_pilot25.py`（動作3件）と `tests/test_vocab_pilot25_cards.py`（代表3枚）。対象: d2_field 64件、d_d_d 62件、g_castle 20件。

- D2フィールド: 型 field の実行・常在型は既存。新規は一意性のみ（フィールドが出たら他のフィールドはすべて破壊される。events の適用後フックで実装）
- D・D・D: declare + play_self（キリフダッシュと同じ型）で表現可（申告切れ）
- G・城: galaxy_shield 宣言が土台。あわせて2つのエンジン側の穴を塞いだ: (1) シールドゾーンのカードを発生源とする常在型が集計されていなかった（chars の発生源走査にシールドを追加。zone: shield を宣言した能力だけ）、(2) 置換効果の候補がバトルゾーンのカードだけだった（動くカード自身とシールドゾーンの発生源を追加）

# 第26弾（2026-11-01）: フェーズ4（判定/特殊系）

検証は `tests/test_vocab_pilot26.py`（動作6件）と `tests/test_vocab_pilot26_cards.py`（代表4枚）。対象: gachinko_judge 64件、super_s_trigger 58件、choukon_x 58件、bazurenda 48件。すべて新規実装。

- ガチンコ・ジャッジ: op `gachinko {times?, until_lose?, stoppable?, as?}`。各プレイヤーが山札の上を見せて一番下に置き、コスト以上で勝ち。勝ち数は env 変数へ（数値変数を {var} で参照できるよう eval_expr を拡張）
- スーパー・S・トリガー: キーワード `super_s_trigger`（許可は通常の S・トリガーと同じ）。シールド0枚で使った時だけ Card.sst が立ち、`sst: true` 印の能力と呪文の `sst_spell` が有効になる。印は移動で消えるため、移動イベントに載せて付け直す
- 超魂X: 下に重なっているカードの `choukon: true` 印の能力を、一番上のクリーチャーが得る（abilities() に負の添字で追加。誘発は inline として解決される）
- バズレンダ: 面の宣言 `bazurenda: {cost, civs}`。支払い後に追加支払いを好きな回数でき（h_play にループ。本体の支払いは paid_done で再入ガード）、[OL] 能力（`bazurenda: true` 印の誘発、呪文は全体）を 1+追加回数使う

# 第27弾（2026-11-01）: フェーズ5（ロングテール1）

検証は `tests/test_vocab_pilot27.py`（動作5件）と `tests/test_vocab_pilot27_cards.py`（代表6枚）。対象: mugen_climb 42件、tapped_mana_placement 47件、s_trigger_plus 33件、shield_go 32件、o_drive 32件、dorongo 30件。

- ムゲンクライム: 面の宣言 `mugen_climb {tap, cost, civs}`。メインに「:climb」選択肢（手札・墓地の両方）が出て、自分のクリーチャーを tap 体タップ+代替コストで実行する
- S・トリガー・プラス: キーワード + Card.stp + `stp` 印/`stp_spell`（SST と同じ型）。条件は「相手のターンで、そのターンに自分のシールドが2つ以上ブレイク」。ブレイク数は break イベントの記録から数える
- O・ドライブ: 面の宣言 `o_drive {civ, count}`。支払い後に追加タップを選べて、召喚したカードに `odrive` 印の能力が付く
- シールド・ゴー: キーワードとして実装（破壊→表向きシールド化の置換 + 表向きで離れる時は墓地への置換）
- タップしてマナに置く: move の `tapped: true` で既存表現可（申告切れ）
- ドロン・ゴー: 破壊時誘発 + name_has フィルタの move で本体は表現可。ただし「他の同名エグザイルを出せない」の常在型は、入る側のゾーンと affects のゾーンが合わず未対応（制限）
- ついでに修正: バトルゾーンの発生源から別ゾーン宣言（zone: shield 等）の常在型が漏れて働いていた問題（chars の bz 走査に発生源ゾーンの確認を追加）

# 第28弾（2026-11-01）: フェーズ6（ロングテール2）

検証は `tests/test_vocab_pilot28.py`（動作5件）と `tests/test_vocab_pilot28_cards.py`（代表6枚）。対象: not_evolution_filter 54件、shinka_power 32件、abare_chain 28件、summon_from_mana 27件、yobinion 26件、oshioki_moon 25件。

- アバレチェーン: first_time 誘発 + op `may` に `else`（「そうしなければ」）を追加して表現
- ヨビニオン: キーワード + op `yobinion`（山札の上から条件のクリーチャーが出るまで公開し、それを出す。残りはシャッフルして山札の下へ）
- マナゾーンから召喚: 許可 `summon_from_mana` + キーワード（マナゾーンの常在型）。メインに「:msum」選択肢
- シンカパワー: 移動レコードに `stacked` を追加し、when で照合可能に（「進化元になる時」側は未対応）
- 進化ではない: フィルタの `not_types: [evolution]` で既存表現可（申告切れ）
- オシオキムーン: when の from: shield + subject {owner: you} で既存表現可（申告切れ）
