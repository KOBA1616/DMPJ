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

## 対象外（2026-11-04 ユーザー指示）

- ジャンケン系は変換対象にしない。`op: janken` の win/lose 分岐は既存語彙にあるが、相手の出した手（グー/チョキ/パー）の参照、連勝数カウント、ジャンケン結果の置換などは語彙がなく、実装コストに見合わないため対象外とする。該当 gap: janken_opponent_hand（8件）、janken_streak_count（1件）、janken_win_hand_event（1件）、janken_loss_replace（1件）、battle_outcome_replace（1件、ジャンケン由来）

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

# 第29弾（2026-11-01）: フェーズ7（進化V / 代替コスト）

検証は `tests/test_vocab_pilot29.py`（動作4件）と `tests/test_vocab_pilot29_cards.py`（代表5枚）。対象: evolution_filter 26件、evolution_v 25件、alternative_cost 25件。

- 進化V: `evolve_from` をフィルタのリストにできるようにした。選択はフィルタごとに1体ずつ進み、重ね方は既存の複数進化元（stack_more）を再利用
- 代替コスト: 面の宣言 `alt_cost`。別額形式 `{cost, civs}` は「:alt」選択肢、行動形式 `{do: [{zone, filter, count, to, reason}...]}` は段階ごとに選んで支払い、払い切ったらコストを支払ったものとして実行する。条件式に `{alt_paid: true}` を追加（「[代替]支払って唱えたら」）
- ついでに op `opp_may`（「相手は〜してもよい」）を追加。代替コストの「そうしたら、相手は〜してもよい」で必要になった
- 進化クリーチャーの参照（「1体につき」「なければ」）: count 式とフィルタで既存表現可（申告切れ）

# 第30弾（2026-11-01）: フェーズ8（ビビッドロー / 強制攻撃 / 究極進化）

検証は `tests/test_vocab_pilot30.py`（動作3件）と `tests/test_vocab_pilot30_cards.py`（代表3枚）。対象: vividraw 27件、ultimate_evolution 23件、must_attack 23件。

- ビビッドロー: 面の宣言 `vividraw {cost, civs}`。ドローしたカードに drawn_turn を記録し、自分のターンのメインステップ（攻撃前のみ）に「reveal」選択肢で表向きにすると、そのターンは「:vivid」選択肢で代替コスト実行できる
- 強制攻撃: キーワード `must_attack`（mod の require: [attack]。強制の仕組み自体は既存）
- 究極進化: evolve_from {types: [evolution]} で既存表現可（申告切れ）

# 第31弾（2026-11-01）: フェーズ9（ロングテール3）

検証は `tests/test_vocab_pilot31.py`（動作5件）と `tests/test_vocab_pilot31_cards.py`（代表5枚）。対象: fushigibirth 23件、last_burst 21件、meteor_burn 21件、shield_plus 19件、janken 18件。out_of_game 23件はブースターパック開封という外部要素のため対象外とした。

- フシギバース: 面の宣言 `fushigi {cost, civs, min}`。墓地からの「:fushigi」選択肢で、自分のクリーチャー1体をタップしてマナに置き、差額（宣言コスト−そのクリーチャーのコスト、下限 min）を払って召喚する
- ラスト・バースト: キーワード（破壊時誘発 + op cast_face の呪文面解決。cast_face の face: -1 で呪文面を探すよう拡張）
- メテオバーン: キーワード（離脱の置換。条件は下のカードの count、代わりは under_of の move）
- ジャンケン: op `janken {win, lose, draw}`（両プレイヤーが手を選ぶ）
- シールド・プラス: op `shield_plus`（山札の上をシールドの束の下へ。束は1つと数える）

# 第32弾（2026-11-01）: フェーズ10（検証の穴＋ツールのバグ修正）

検証は `tests/test_vocab_pilot32.py`（動作1件＋ツール単体2件）と `tests/test_vocab_pilot32_cards.py`（代表1枚）。

- when の `attacker: crossed`: 照合側（_ref_match→_subject_match）は対応済みだったのに defs の検証が弾いていた。許可リストに crossed を追加し、「これをクロスしたクリーチャーがブロックされた時」の誘発（dm14-070 ネオ・スレッジハンマー等）が書けるようになった
- 変換ツール split のバグ修正: 攻撃時型メテオバーン（「メテオバーン - このクリーチャーが攻撃する時、…」）に離脱置換キーワード meteor_burn を誤って merge していた問題を修正。原文に攻撃時型の文がある場合はキーワードとして付けず、本文をモデル側に残す（離脱型は従来どおりキーワードになる）。既存データの誤混入6枚は再変換ラウンド7で除去済み
- ジャンケン関連の拡張（相手の手への誘発など）は、ユーザーの指示により開発しない
- **op cast_face の不発バグを修正**: ラスト・バーストが「破壊された時」の誘発で、発生源は墓地へ移動済み（世代+1）のため alive チェックで常時不発になっていた。移動がちょうど1世代分（誘発の原因になった移動）の場合のみ許可するよう修正（self_moved と同じ考え方）。`tests/test_named_effects.py` のラスト・バーストのテストは第31弾の全体実行時から失敗していたもので、本修正で通過。あわせて第31弾の自前テストの検証が甘く（ターンのドローと区別できていなかった）不発を見逃していたため、検証を厳密化した

## 第33弾（フェーズ11）: G-NEO進化＋既存可2件の確定＋潜在バグ2件の根治

- **G-NEO進化（g_neo_evolution 単独44件）**: 重ね出しは NEO進化と同じ（面の `neo: true`＋evolve_from）。離脱置換をキーワード `g_neo` として実装: replace（when: move from bz, subject: self、if: under が1枚以上、instead: 新 op `move_under_to_event`＝下のカードすべてを、置換されたイベントの行き先・理由で移動する）。任意ではない（「てもよい」ではない）ので optional は付けない。
  - 変換の型: `neo: true`、`evolve_from: {civs: [...]}` 等、keywords に `g_neo`。
  - 制限: 束ごと対象になる全体除去では、下のカード側のイベントと競合する場合がある（個別の離脱では正しく動く）。
- **「召喚によって出た時」（summon_only_entry 単独20件）は既存で表せる**: 誘発の when に `reason: summon` を付ける（move レコードの reason は召喚プレイで "summon" になる）。対になる「召喚以外の方法で出た時」は `reason: put`（効果で出す場合は put）で大半をカバーできる。動作テストで「召喚では誘発し、呪文で出す（put）では誘発しない」ことを確認。
- **「相手は呪文を唱えられない」（cast_restriction 単独22件）は既存で表せる**: 常在型 `affects: {owner: opp, zone: hand, filter: {types: [spell]}}`＋`mod: {deny: [cast]}`（お騒がせチューザの登録済みの型。条件は if に、対象の絞り込みは filter の not_civs 等に）。動作テストで play 選択肢が出なくなることを確認。
- **根治1: last_burst の重複定義を除去**: 第31弾で keywords.yaml に last_burst を追加した際、既存の正規定義（play_free＋self_moved）が既にあり、YAML の後勝ちで覆われていたのが、第31弾以降 test_named_effects が落ちていた真因だった。第32弾の cast_face 側の緩和（世代+1 を許可）は不要になるため元に戻し、重複定義を削除して正規実装に一本化した。
- **根治2: under リストの残留バグ**: 下のカードだけが移動した時、上のカードの under リストに残り続けていた（メテオバーンで確認。under_of の数え・選択に幽霊カードが混ざる）。_raw_move で top_of を持つカードが動く時は上の under から外すよう修正。G-NEO の「下が空になったら進化クリーチャーでなくなる」判定もこれで正しくなる。
- 検証: tests/test_vocab_pilot33.py（動作3件: G-NEOの離脱置換、召喚/put の誘発の切り分け、詠唱封じ）＋test_vocab_pilot33_cards.py（代表3枚: ラギルップ＝ラギバーン、応援者 オシヤバミ、九極 デュエンジェル）。proto に T101〜T104 を追加。

## 第34弾（フェーズ12）: 離脱置換・出現置換は既存可＋filter に neo 追加＋{ref: subject} の潜在バグ修正

- **離脱置換（leave_replacement 単独21件）は既存の replace で表せる**。型は3種:
  - とどまる型: replace（when: move from bz, subject: self）＋条件 if＋`instead: []`（イベント自体が置換で消える）。
  - 行き先変更型: instead で `{op: move, select: {ref: subject, count: 1}, to: <ゾーン>}`（置換されたイベントの対象を別の行き先へ）。
  - 身代わり型: optional: true の replace＋instead で別のクリーチャーを破壊する等。
- **出現置換（entry_replacement 単独18件）も既存で表せる**: replace（when: move to: bz, subject: {owner: opp, ...}）＋instead で {ref: subject} を墓地等へ。ターン条件は if の `is_turn` で付ける。
- **filter に `neo` を追加**（neo_creature_filter）: 面の `neo: true` を持つカードにマッチする（G-NEO も neo: true を持つため両方を指す）。
- **潜在バグ修正**: セレクタ `{ref: subject}` が vars を引いて常に空になっていた（正しくは `event.subject`）。登録済みカード39枚がこの形で instead を書いており、置換は発火しても対象を動かせていなかった（例: アクア鳥人 ロココのバウンス）。selectors で `subject` を `event.subject` の別名として受理するよう修正し、全39枚が一括で回復する。
- 検証: tests/test_vocab_pilot34.py（動作5件: とどまる／行き先変更／身代わり／出現置換／neo フィルタ）＋test_vocab_pilot34_cards.py（代表3枚: 暴投の針棺、単騎連射 マグナム、威牙忍ジンナイ）。proto に T105〜T108 を追加。

## 第35弾（フェーズ13）: 「攻撃するかわりにタップして使う」起動型能力の複合コスト

- 前提の確認: 「攻撃するかわりにタップして使う」起動型能力そのものは既存の kind: activate で表現できていた（攻撃ステップで、攻撃できるクリーチャーにだけ activate 選択肢が出る。602.3a）。tap_activated_ability_instead_of_attacking（単独22件）の大半は DM24 系の複合コスト「このクリーチャーと自分のマナゾーンのタップされていないカードを8枚タップして」が未対応だったのが本体。
- 拡張: activate の cost に `tap_mana: N` を追加（任意キー）。_activate_options はタップされていないマナが N 枚以上ある時だけ選択肢を出し、選択時は新タスク `activate` がマナの選択とタップ（コスト支払い）を済ませてから効果を解決する。本体のタップは従来どおり st_attack が即時に行う。
- 検証: tests/test_vocab_pilot35.py（動作3件: 複合コストで使用／マナ不足では選択肢が出ない／単独コストの従来型）＋test_vocab_pilot35_cards.py（代表1枚: 巡霊者ソルディアス）。proto に T109・T110 を追加。
- 残り: カチュア（dm22ex1-035）のように効果側に山札探索が残るものは、この弾では解けない。

## 第36弾（フェーズ14）: 素の墓地召喚と墓地進化

- 素の墓地召喚（summon_from_graveyard 単独17件）: キーワード `summon_from_graveyard` を新設（アビスラッシュと同じ許可の自己付与）。あわせて h_play のラッシュ付随処理（召喚酔いでもプレイヤー攻撃可・ターン終わりに山札の下）はキーワード `abyss_rush` を持つカードにだけ付くよう絞った（従来は墓地から召喚した全カードに付いていた。他者の常在型で墓地召喚を許可されるカードも正しい挙動になる）。
- 墓地進化（graveyard_evolution 単独17件）: 進化クリーチャー型は `evolve_zone: graveyard`＋evolve_from で既存可（進化元の墓地→バトルゾーン移動は stack_on 処理が既に対応済みだった）。通常クリーチャー型は面の宣言 `grave_evo: true` で「:gevo」選択肢を追加（NEO と同じ evo_mode 経路。通常召喚も可能で、重なっている間は進化クリーチャーとして扱う）。
- 検証: tests/test_vocab_pilot36.py（動作2件: 付随処理なしの墓地召喚／墓地進化の重ね出し）＋test_vocab_pilot36_cards.py（代表2枚: タブ＝タラウプ、ワーム・ゴワルスキー）。アビスラッシュの既存テストも回帰確認済み。

## 第37弾（フェーズ15）: 回数制限つき許可（ターン1回）

- 「自分のターンに一度（／自分のターン中、クリーチャーを1体）、自分の墓地から召喚してもよい」という他者への回数制限つき許可（summon_others_from_graveyard_once_per_turn 4件）に対応。mod の allow 項目に `{action: summon_from_graveyard, once: true}` と書けるようにした。
- 実装: chars が once つき allow を発生源（src）つきで記録し（cost_may の once と同じ方式）、墓地召喚の選択肢生成が「無制限の許可があれば常時／once の許可は発生源ごとに未使用の時だけ」を判定する。使用すると turn_counters に `summon_once:<src>` を記録し、そのターンは選択肢が出なくなる（次のターンに回復）。
- 検証: tests/test_vocab_pilot37.py（動作2件: 1体だけ召喚できる／次のターンに回復）＋test_vocab_pilot37_cards.py（代表1枚: 堕魔 ヴォーミラ）。proto に T113 を追加。

## 第38弾（フェーズ16）: コストの合計制限つき選択

- 「コストの合計が N 以下／以上になるように好きな数選ぶ」（total_cost_selection_limit 21件＋total_cost_selection 18件）に対応。セレクタに `total_cost_le` / `total_cost_ge`（式）を追加した。
- 実装: select が合計制限モードでは1枚ずつ積み上げる選択を行う。上限では予算を超える候補が自動で外れ、下限では合計が届くまで止められない（どう選んでも届かない場合は打ち切る）。答えは os に記録して再入時に再生する（ask の再入対策）。
- 検証: tests/test_vocab_pilot38.py（動作2件: 合計以下で選ぶと予算外の候補が外れる／0枚で止められる）＋test_vocab_pilot38_cards.py（代表1枚: めった切り・スクラッパー）。proto に T114 を追加。

## 第39弾（フェーズ16追補）: 合計コスト選択の枚数上限（「N体まで」併記）

- きっかけ: 再変換ラウンド14の対象に「コストの合計がN以下になるようにクリーチャーを2体まで選ぶ」型（邪入梵ほか）が複数あり、第38弾の合計制限モードが count を見ていないため厳密に表せなかった（reject原因の追加分析）。
- 実装: dmsim/engine/selectors.py の合計制限モードで、select に count がある場合だけその枚数で積み上げを打ち切る（再生パス・対話パス両方）。count 無しの「好きな数」は従来どおり無制限、count: any / all も上限なし扱い。
- 検証: tests/test_vocab_pilot39.py（動作1件: 合計10以下・2体までで、予算内の3体目が残り、選択提示自体が2回で終わる）。proto に T115 を追加。第38弾の回帰テストも通過。

## 第40弾（フェーズ17-1）: 手札破棄の置換（「相手の効果によって捨てられる時」）

- 対象: discard_replacement 単独17件。置換自体（replace＋instead で出す）は既存だが、「相手のクリーチャーの能力または呪文によって」を表す手段が無く、ターン条件（if: is_turn）での代用は厳密でないため reject されていた。
- 実装: 移動イベントに、その移動を起こした効果の解決者 `by` を記録する。ops 経由の移動には ev_task が env["you"]（効果の解決者）を by として付け、_record_for が照合用レコードへ写し、when に `by: you / opp` と書けるようにした（schema・defs の検証にも追加）。状況起因処理・コスト支払い・S・バックの捨て札など、効果解決者を伴わない移動には by が付かないため「相手の効果」扱いにならない。
- 書き方: `- {kind: replace, zone: hand, optional: true, when: {event: move, from: hand, to: graveyard, reason: discard, subject: self, by: opp}, instead: [{op: move, select: {ref: self, count: 1}, to: bz, reason: put}]}`。「相手のターンに」型は従来どおり if: {is_turn: opp}（提督シリーズの登録済み型）。
- 検証: tests/test_vocab_pilot40.py（動作2件: 相手の呪文で捨てられる時は出せる／自分の呪文で捨てる時は発火せず墓地に行く）。proto に T116（捨て置換獣）・T117（相手に捨てさせる呪文）・T118（自分が捨てる呪文）を追加。

## 第41弾（フェーズ17-2）: 「能力が書かれていない」フィルタ（vanilla）

- 対象: ラウンド15で残った no_ability_filter 2件（《アクア提督 ザ・ミスター》DMR16極/真）。reject 原因は「カードに能力が書かれていないクリーチャー」を指すフィルタの不在。
- 実装: filter に `vanilla` を追加（defs.py の FILTER_KEYS、schema は自動で追随）。判定は印刷された特性で行う: その面の定義に能力・キーワードが無く、進化・NEO・スター進化・墓地進化・ハイパーモード等の書かれた仕組みも持たないこと（dmsim/engine/selectors.py の filter_match）。付与された能力は見ない。
- 検証: tests/test_vocab_pilot41.py（動作1件: 上3枚がバニラ/キーワード持ち/能力持ちの時、バニラだけが手札に加わり残りは山札の下へ）＋ tests/test_vocab_pilot41_cards.py（ザ・ミスターの parse）。proto に T119 を追加。再変換ラウンド16で2枚を登録。
- あわせて第40弾に回帰テストを追加: 置換効果は連鎖しない（総合ルール101.5 / 609.3）。置換で生じたイベントは replaced 印でそれ以上置換されず、自分のターンの《単騎連射 マグナム》がいても相手のバイケン型置換で出すことは妨げられない（test_vocab_pilot40.py の test_replacement_does_not_chain_against_magnum）。

## 第42弾（フェーズ17-3）: 革命０トリガー（宣言型能力としての表現）

- 対象: revolution_zero_trigger 単独18件。新しいエンジン機構は不要で、既存の宣言型能力（kind: declare、ニンジャ・ストライクと同系）で表せることを確認した。
- クリーチャー版の型: declare {zone: hand, when: {event: attack, target: player}, if: {all: [{is_turn: opp}, {cmp: [{count: {zone: shield, owner: you}}, "==", 0]}]}, effect: [山札の上1枚を choose (look) → 条件（文明・進化ではない）に合えば move で出し as: base → op: invade でその上に重ねる]}。invade は侵略と同じ重ね処理で、進化として重なった扱いになる。move の as で新しい参照を取り直すのが要点（移動で世代が変わり、古い ref では重ね先が見つからない）。
- 呪文版の型: declare の effect を [{op: play_free, select: {ref: self}}] にする（コストを支払わずに唱える）。
- 検証: proto T120（ブロッカー持ちで、受けた攻撃をブロックできる形にしてある）、tests/test_vocab_pilot42.py 2件: ①シールド0で宣言→重なって出てブロックし攻撃側を破壊、②シールドが残っている間は宣言が提示されない。
- 再変換ラウンド17で18件中14件を登録（converted 5,782枚）。残4件は革命０以外の部分が原因で差し戻し: 叛逆の絆（opponent_chooses_branch）、革命の鉄拳（power_relative）、龍帝の紋章（power_lt_card）、賢者の紋章（cancel_attack）。
- 紋章系呪文に共通する「唱えた後、墓地に置くかわりに山札に加えてシャッフルする」は、resolve_to: deck ではシャッフルが伴わず近似になるため使わず、kind: replace {zone: hold, when: {event: move, to: graveyard, reason: resolve, subject: self}, instead: [move self to deck, shuffle]} で統一した（dmc64-011 先例）。
- 注意（別途点検候補）: 「次の自分のターンのはじめに〜」型の delayed_trigger は duration: permanent（when は turn_start + player: you）を付けないと、デフォルトの end_of_turn 失効で発火前に消える。converted 内の duration 無し turn_start 先例は影響を受けている可能性がある。

## 第43弾（フェーズ17-4）: S-MAX進化

- 対象: s_max_evolution 単独17件。3つの仕組みを実装した。
- (1) 進化元を必要としない召喚: カード属性 `s_max: true` を新設（defs.py / schema.py）。s_max の進化クリーチャーは evolve_from が無くてよく、プレイ判定・プレイ処理では通常のクリーチャーとして扱う（turn.py の _can_play_face / h_play で進化分岐をスキップ）。
- (2) 敗北の置換: イベント `lose` を新設し、when: {event: lose} の kind: replace で表す。敗北の確定箇所（ダイレクトアタック = combat.py、デッキ切れ・状況起因の勝敗 = events.py の _sba_tasks、効果による敗北 = ops.py の op lose）はすべて Engine.game_lose を通るよう統一し、置換候補があれば lose_replace タスクで敗北するプレイヤーに諮問する。標準形の支払い（本体を破壊するか手札の同名を捨てる）は if + modal で表す（proto T121）。鬼/CRY 型は「離れる時」の通常の移動置換と対で同じ instead を使う。なお op win（相手を勝たせる効果）は従来どおり即確定で、敗北置換の対象にしていない。
- (3) 2体制限: 状況起因処理（_sba_tasks）に S-MAX チェックを追加。自分の S-MAX が2体以上あれば smax_reduce タスクで残す1体を選ばせ、残りをすべて手札に戻す。
- 検証: proto T121 / T122、tests/test_vocab_pilot43.py 5件（進化元なし召喚、2体制限、ダイレクトアタック敗北の置換＝破壊／同名破棄、辞退すると敗北）。
- 再変換ラウンド18で17件中8件を登録（converted 5,790枚）。残9件はS-MAX以外の部分が原因で差し戻し（gap更新済み）: copy_abilities、shield_keep_rest_graveyard、mach_fighter ×2、master_g_breaker ×2、break_pre_trigger、battle_indestructible、cost_lt_card、player_attack_protection。

## 第44弾（フェーズ17-5）: キズナと[P]能力

- 対象: kizuna 単独18件。
- 実装: (1) 能力種別 `partner` を新設（defs.py の ABILITY_KINDS、schema の enum）。[P]能力は単独では機能せず、effect だけを持つ。(2) キーワード `kizuna` を data/rules/keywords.yaml に追加: 出た時の誘発として op: use_partner を解決する。(3) op: use_partner（ops.py）: 自分のクリーチャーの[P]を列挙して1つ選ばせ、その effect を self=[P]の持ち主として解決する。候補が無ければ何もしない。
- 検証: proto T123（キズナのみ）/ T124（[P]のみ）/ T125（両方）、tests/test_vocab_pilot44.py 4件: 他者の[P]を使う、自分の[P]を使う、複数候補から選ぶ、[P]が無ければ何も起こらない。
- 再変換ラウンド19で18件中17件を登録（converted 5,807枚）。残1件（キズナ・チャージャー）は「パートナー召喚時にこのマナを全文明として扱う」が原因で差し戻し（既存 gap mana_all_civilizations）。

## 第45弾（フェーズ17-6）: 無月の門

- 対象: mugon_gate 単独18件。
- 表現: 宣言ではなく「手札/墓地で機能する誘発型能力」で表す。zone: hand と zone: graveyard の2能力を併記し、when は「自分の魔導具が出た時」（subject: {owner: you, other: true, filter}）、if で重ねる枚数の実現可能性を門番する（cmp + count、合算形は sum）。
- 実装: op: summon_on（ops.py）。parts: [{zone, count, filter?}]（zones で複数ゾーン合算も可）どおりに選ばせ、移動イベントの stack_on / stack_more で選んだカードの上に無償召喚する。満たせないパートがあれば何もしない。
- 進化との違い: 重ねる処理 _stack は進化の流儀（召喚酔いなし・タップ継承）のため、後始末タスク summon_on_fix（interpreter.py / types.py）で通常の召喚どおりに直す（召喚酔いする、タップは op の tapped 指定どおり）。
- 追随: summon_on は解決後に mugon_used イベントを流すので、「自分の『無月の門』能力を使った時」に誘発するカード（zone: hand/graveyard、when: {event: mugon_used, player: you}）も表現できる。
- 制約（v1）: 重ねる対象は各ゾーンの「一番上」のカードだけ（他のクリーチャーの下にあるカードは選べない）。無月の門・終（呪文の代替コスト）は対象外。
- 検証: proto T126（門番）/ T127（魔導具）、tests/test_vocab_pilot45.py 4件: 手札から召喚（下4枚・召喚酔い・タップしない）、墓地から召喚、追随者がタップして出る、枚数不足では発動しない。
- 再変換ラウンド20で18件中15件を登録（converted 5,822枚）。残3件は別 gap が原因で差し戻し: mugon_gate_period（無月の門・終）、untap_limit、smash_burst。

## 第46弾（フェーズ17-7）: 封印

- 対象: seal_mechanic 単独18件。
- 状態: Card.seals（上に裏向きで重なった封印の cid 列）と Card.seal_of。封印カードは top_of を持ち、バトルゾーンの「一番上」には数えない。
- 無視される: 封印されているクリーチャーは特性（タイプ・種族・キーワード）を持たず、能力も機能しない（chars の早期分岐と abilities の門番）。パワーは印刷どおり返す（パワー0の状況起因処理で破壊されないため）。通常のフィルタでは選べず、filter: {sealed: true} でだけ指せる。
- op: attach_seal（対象の持ち主の山札の上から count 枚を重ねる）/ op: remove_seal（封印を墓地に置く。通常の移動イベントとして処理する）。
- コマンドが出た時: その持ち主は、そのコマンドと同じ文明を持つ自身のカードから封印を1つ墓地に置く（seal_release タスク、events.py の移動適用から起動）。
- 封印の移動: 封印そのものが動くと対象から外れ、記録に sealed_from（どのカードの封印だったか）が付く。封印されたカードがバトルゾーンを離れる時、封印はそれぞれ持ち主の墓地に置かれる。「封印がすべてなくなった時」は when: {event: move, reason: seal, sealed_from: self} ＋ if: {cmp: [{seals_on: self}, "==", 0]} で表す。式 {seals: {owner}} はプレイヤーの封印総数（シンパシー用）、{seals_on: self} は自カードの封印数。
- 既知の制約: 封印を付ける行為自体はイベント記録を出さない（「封印を付けた時」の誘発は未対応）。封印されたカードの離脱時誘発（LKI）は無視の完全な適用外。
- 検証: proto T129（自らに2つ＋全外れでドロー）/ T130（相手に付ける）/ T131（コマンド）/ T132（remove_seal）、tests/test_vocab_pilot46.py 5件。

### 第46弾v2: 封印を付けた状態で出す／進化フィルタ
- move に seal: N を追加: バトルゾーンに出る時、持ち主の山札の上から N 枚を封印として付けた状態で出る。封印は誘発の収集より前に付くので、出た時能力は無視される（メモッタ型）。
- 封印されているカードへの付け外し: attach_seal / remove_seal の選択の間だけ、無視による選択除外を外す（すでにある封印の数え直しや追加が公式どおりできる）。
- フィルタに evolution を追加（「進化ではないクリーチャー」等。進化はタイプで判定）。

### 第46弾v3: mugen_climb フィルタ
- フィルタに mugen_climb を追加（「『ムゲンクライム』能力を持つカード」。面の宣言の有無で判定）。ラウンド22の差し戻し原因から追加し、グリダルマ/ツェン・ミリアルデンの2枚が変換可能になった。

### 第46弾v4: face_up フィルタ
- フィルタに face_up を追加（シールドゾーンの「表向きのカード」を絞る。シールド・ゴーの条件「表向きのシールド・ゴー持ちカードがある/その枚数」の数え上げ用）。ラウンド22 wave2 の差し戻し原因から追加。

## 第47弾: 多文明O・ドライブ＋呪文側O・ドライブ（2026-11-02）
ラウンド22 wave4 の差し戻し原因（o_drive_multi_civ 11件・odrive_spell 2件）から。
- `o_drive` を拡張: 従来の {civ, count} に加え {civs: {文明: 枚数}}（まとめて形: 全部タップしたら能力を得る）と {civs: {...}, each: true}（文明別形: 文明ごとにタップするか選び、能力は `odrive: <文明>` の印で文明別に有効化。`odrive: true` は従来どおり「いずれか払えば」ではなく支払い全体の印）。
- 状態: Card.odrive_civs（実際にタップした文明の列）を追加。支払いは turn.py の play ハンドラでステップ化（まとめて形=1ステップ、文明別形=文明ごとのステップ）。複数文明の同時タップは「重ならないマナの割り当てが存在するか」を小さい探索で判定してから提示する（多色マナ1枚で2文明分はまかなえない）。
- 呪文側: 面フィールド `odrive_spell`（stp_spell と同型）。唱える時に追加タップを払っていたら解決 ops に追加される。単一文明・多文明どちらの o_drive でもよい。
- proto T133（まとめて形）/ T134（文明別形）/ T135（呪文側）。tests/test_vocab_pilot47.py 4件＋実カード（ライオン・アームズ/ビューティシャン/コアラ大佐の火能力/ソーラー・ドライブ）で検証。
- 残: ゼツ型「支払ったコストに合う能力を得る」(o_drive_multiple_costs) は別構造のため未対応。

## 第48弾: cost_may の must（強制・ターン1回の軽減）（2026-11-03）
converted の監査（opt_reduce の素の整数表記9件）から。任意形は第9弾の cost_may {amount, once, min} で足りたが、強制形（「各ターン、自分の〜１体目/１枚目のコストを少なくする」）は確認を出す cost_may では表せなかった。
- mod cost_may に `must: true` を追加: 支払い時に確認せず適用する。once の消費記録（発生源ごとターン1回）は任意形と共有。
- 適用先: 珊瑚妖精キユリ（dm24bd5-060／ツインパクト版 dm26ex4-055）、ザパンプ（dm24ex3-tf22）。ツインパクト版のテキストには床の条項が無いため min は付けない。
- proto T136。tests/test_vocab_pilot48.py 2件（確認が出ないこと・once 消費・min の床）＋実カード3枚の parse テスト。
- 同時に直したもの: 任意形5枚（ブラッドレイン dm23ex2-097 ほか）は cost_may {amount: 1, once: true, min: 1} に、突風のゴーマッハ・スワン（dmd05-015）の条件つき自己軽減は mod {cost: -3, cost_min: 1} に正規化。これで converted 全6,169枚が厳密 parse を通過するようになった。

## 第49弾: no_leave（バトルゾーンを離れない）（2026-11-03）
ラウンド24〜26で繰り返し差し戻された leave_prevention / leave_protection 系（計17件）の受け皿。
- mod に `no_leave` を追加。値は true（無条件）か辞書 {except_destroy, by_opp, except_battle}（いずれも bool、併記可）。
  - except_destroy: 「破壊される時以外、離れない」型。reason: destroy の移動だけ通す。
  - by_opp: 「相手のカードの効果で離れない」型。移動イベントの by（第40弾で導入した解決者記録）が相手の時だけ止める。by の無い移動（状況起因処理・バトル敗北・コスト）は通す。
  - except_battle: 「バトルに負けた時以外、離れない」型。combat の敗北破壊イベントに battle: true の印を追加し、その移動だけ通す（スレイヤー等の効果破壊は止める）。
- 判定場所: events の移動適用（_apply_one）の先頭。置換を経た最終的な移動に対して判定するので、置換で行き先が変わっても正しく止まる。止めた場合は移動イベント自体が発生しない（「離れた時」誘発も起きない）。
- 特性の集約: chars の no_leave に発生源ごとの例外指定を集める（封印中は空）。付与（modify の mod に no_leave を書く期間つき付与）も同じ経路で効く。
- proto T137（無条件）/ T138（except_destroy）/ T139（by_opp 付与）/ T140（バウンス呪文）/ T141（except_battle 付与、パワー12000以上）/ T142・T143（バトル検証用）。tests/test_vocab_pilot49.py 5件＋実カード（ブルトゥーラ-D1、龍装者 ジスタジオ）の parse テスト。
- 既知の制約: 進化元など「下のカード」だけの離脱抑止、G・リンクグループ単位の判定は未対応。

## 第50弾: 回数制限つき許可のマナ召喚版（once_per_turn_mana_summon_permission）（2026-11-04）
ラウンド47（summon_from_mana 27件）で6件がこの gap で差し戻された。第37弾の墓地召喚版は実装済みだったが、マナ召喚の選択肢（turn.py の :msum）は permits の真偽しか見ておらず、once の消費経路が無かった。
- turn.py に `_mana_summon_grant` を追加（第37弾の `_grave_summon_grant` と同じ方式）: chars の allow にある {action: summon_from_mana, once: true} を発生源ごとに判定し、無制限なら {}、未使用の制限つきなら {"once_src": 発生源}、使い切りなら選択肢を出さない。使用時の消費は墓地版と共有（turn_counters の `summon_once:<src>`、from_zone が mana の場合も記録）。
- 効果で与える許可（呪文・誘発からの modify）の帰属: 継続的効果（ce）に発生源カードの cid（`src`）を記録し（ops の op_modify、types の Continuous に src を追加）、chars の src_of マップに継続的効果の mod も加えた。これで「このターン、1体だけ」という呪文型の許可も、対象全員で共有の1回になる（従来は対象カード自身に帰属してしまい、1体ずつ使えてしまうところだった）。
- 書き方: 常在型は static {affects: {owner: you, zone: mana, filter: {...}}, mod: {allow: [{action: summon_from_mana, once: true}]}}。呪文型は効果で modify {select: {zone: mana, owner: you, filter: {types: [creature]}}, mod: {allow: [{action: summon_from_mana, once: true}]}, duration: end_of_turn, dynamic: true}。
- proto T144（常在型の許可獣）/ T145（呪文型）。tests/test_vocab_pilot50.py 3件（常在型で1体だけ／翌ターン回復／呪文型は唱える前は出ず・唱えた後も共有の1回だけ）＋実カード parse テスト（蔑如と覚悟 dm24rp3-076。マッハファイター付与は「マナから召喚された時」の遅延誘発で対象に与える形）。
- 注意: 蔑如と覚悟の遅延誘発は「この呪文の許可で召喚した」こと自体は区別できない（別のマナ召喚許可と併用し、そちらを先に使った場合にだけ差が出る）。notes に明記する前提で変換する。

## 第51弾: must_be_attacked（攻撃先の強制）（2026-11-04）
ラウンド40・44・45・46・48と繰り返し差し戻された must_attack_this_creature（rejects に21件）の受け皿。
- mod に `must_be_attacked: true` を追加（defs の MOD_KEYS＋検証、chars に集約。封印中は false、ダイナモの add_of 経由でも伝わる）。
- 判定場所: combat の _attack_options。攻撃クリーチャーごとに合法な攻撃先（プレイヤー／タップ状態または許可で攻撃できるクリーチャー）を集め、その中に must_be_attacked 持ちが含まれれば、選択肢を誘引持ちへの攻撃だけに制限する。「可能なら」の範囲は既存の合法性判定（タップ状態・attack_creature の許可・be_attacked の許可）がそのまま決めるので、アンタップしていて攻撃できない誘引持ちは制限をかけない。複数いればその中から選ぶ。
- 書き方: 本体は static {affects: self, mod: {must_be_attacked: true}}（条件があれば if を付ける）。付与は modify の mod に同じ形（期間は duration で指定。「次の自分のターンのはじめまで」は until_next_own_turn_start）。
- ガードマン（攻撃先の変更）とは別機構で、こちらは宣言時の選択肢そのものを制限する。ブロックの可否には影響しない。
- proto T146（誘引獣）/ T147（付与呪文）。tests/test_vocab_pilot51.py 3件（タップした誘引持ちだけが攻撃先になる／アンタップの誘引持ちは制限しない／呪文付与が相手ターンまで効く）＋実カード parse テスト（指示虫アロー・ワーム dmrp16-016）。

## 第52弾: S・バックの対象指定を filter に一般化（2026-11-04）
ラウンド50（s_back 22件）の下書きで判明: S・バックの対象は文明指定だけでなく種族指定（アウトレイジ、サイバー等）・複合文明（水または闇）・ツインパクト指定があり、面フィールド s_back（文明名の文字列）と combat の文明照合だけでは表せなかった。
- 面フィールド s_back に filter（辞書）を書けるようにした。文字列は従来どおり文明名。辞書は捨てるカードへの filter_match で判定（combat の宣言選択肢の生成）。面への直接指定は _load_face で raw の s_back を props に取り込む形にし、文字列は文明名の検証、辞書は filter 検証を行う。
- filter に `twinpact: true/false` を追加（defs の FILTER_KEYS、selectors の filter_match で CardDef.faces の有無を見る）。「S・バック：ツインパクト」は {twinpact: true} と書く。
- ツインパクトの CardDef.s_back は None 固定だったのを、面のうち最初に s_back を持つ面の値に集約（呪文面にだけ付いているアリス型が宣言候補になる）。
- 書き方: 種族は {race_has: アウトレイジ}（種族名の一部一致。完全一致の種族は {races: [...] }）、複合文明は {civs: [water, darkness]}、ツインパクトは {twinpact: true}。文明1つは従来どおりキーワード（s_back_light 等）でもよい。
- 試験カード R071（種族形）/ R072（複合文明形）を tests/rule_cards.yaml に追加。tests/test_vocab_pilot52.py 3件（種族形で宣言が出て無料召喚／複合文明形で無料詠唱／合わない文明だけでは宣言が出ない）＋実カード parse テスト（アリス dm23ex1-034、ツインパクト集約の確認）。既存の S・バックテスト4件も継続合格。

## 第53弾: 起動型コスト {under: N} — メテオバーン「攻撃できる時」形（2026-11-04）
ラウンド52（meteor_burn 21件）の差し戻しで判明: メテオバーンには「バトルゾーンを離れる時」の置換形（keywords.yaml の `meteor_burn`）と「このクリーチャーが攻撃する時」の誘発形（R067 の先例）のほかに、「このクリーチャーが**攻撃できる時**、下のカードを墓地に置いてもよい」という起動型の形がある（超神龍アルグロス・クリューソス等4枚）。既存の kind: activate はコストがタップ必須で表せなかった。
- defs: activate の cost に `under: N`（正の整数）を許可。tap との併用可、tap_mana とは併用不可。tap が無く under のみの形も可。
- combat._activate_options: under のみの形は「タップするクリーチャー」ではなくクリーチャー自身に選択肢が付き（key は activate:<defn>:<i>）、下のカードが N 枚以上ある時だけ提示される。攻撃できる時だけ使える点は従来どおり（can = 攻撃選択肢のあるクリーチャー）。
- turn.st_attack: コストの支払いは tap（あれば）→ under（効果の先頭に move {select: {under_of: self, count: N}, to: graveyard, reason: put} を差し込む形で効果より先に処理）。タップしないので使用後も攻撃でき、攻撃を強制されているクリーチャーの免除手段にならないため強制フィルタ（forced）は tap がある選択肢にだけ効く。
- types: Option に under_cost を追加。
- 試験カードは R073（tests/rule_cards.yaml）と T148（proto、本弾の形そのもの）。tests/test_vocab_pilot53.py 1件（攻撃ステップで起動できる／下のカードが墓地へ行く／自身はタップせず攻撃もできる／下が無くなれば再使用できない）。
- 変種: 原文が「**自分の**クリーチャーが攻撃できる時」のカード（魔皇アゼルザード sp-015 等）は、能力に `any_attacker: true` を付ける。保持者自身が攻撃できなくても、自分の他のクリーチャーが攻撃できる状態なら使える（combat._activate_options のゲートが can 全体を見る）。ABILITY_KEYS に any_attacker を追加。試験カード R074。実カード parse は tests/test_vocab_pilot53_cards.py（4枚）。

## 第54弾: ビビッドロー使用の可視化（2026-11-04）
ラウンド54（vividraw 27件）の差し戻しで判明: ビビッドローで実行したことを他カードの誘発・呪文自身の分岐・対象フィルタから参照できなかった。代替コストの alt / alt_paid と同じ型で3経路を足した。
- プレイタスクに `vivid: true` を刻み（types の PlayTask に vivid を追加）、召喚/設置の移動イベント（ev["vivid"]）→ イベント記録（rec["vivid"]、events._record_for）へ伝播。誘発は when: {event: move, to: bz, reason: summon, vivid: true, subject: {...}} や when: {event: cast, vivid: true, player: you} と書く（_match_when に vivid フラグ照合を追加）。
- 呪文の解決 env に vivid_paid を入れ、条件 {vivid_paid: true} で「ビビッドロー能力を使って唱えていれば」の分岐が書ける（selectors の eval_cond、defs の cond 検証。CIP 等の誘発解決では env.event 側の vivid 印でも判定する）。
- filter に `vividraw: true/false` を追加（defs FILTER_KEYS、selectors filter_match: CardDef 本体か いずれかの面が vividraw を持つか。第52弾の twinpact と同じ型）。「見たカードがビビッドローを持つなら」は exists {ref, filter: {vividraw: true}} で判定できる。
- 試験カード T149（使用時誘発獣）/ T150（分岐呪文）/ T151（探知呪文）を proto に追加。tests/test_vocab_pilot54.py 5件（誘発する／通常召喚ではしない／呪文分岐の両方向／フィルタ）＋実カード parse（シャッセロアー、空が真っ赤に燃え尽きる！）。

## 第55弾: filter の fushigi 所持判定（2026-11-04）
ラウンド56（fushigibirth 23件）の差し戻しで判明: 「墓地に置いた中から『フシギバース』を持つクリーチャー1体につき〜」を数える/選ぶための所持フィルタが無かった。第54弾の vividraw と同じ型で、filter に `fushigi: true/false` を追加（defs FILTER_KEYS、selectors filter_match: CardDef 本体かいずれかの面が fushigi を持つか）。数え上げは count 式の filter や exists {ref, filter: {fushigi: true}} で書ける。試験カード T152（探知呪文）を proto に追加、tests/test_vocab_pilot55.py 1件（T095 だけが選ばれる）。

## 第56弾: 条件付き代替コスト（alt_cost の if）（2026-11-04）
ラウンド60（summon_time_alternative_cost 35件）の差し戻しで判明: 「〜があれば、このクリーチャーを[コスト]支払って召喚してもよい」の条件付き代替コストを表す語彙が無かった。alt_cost は {cost, civs} または {do: [...]} のみで条件を付けられなかった。
- defs: alt_cost に `if`（条件式）を許可。chk.cond で検証。
- engine/turn.py: :alt 選択肢の提示時に if 条件を eval_cond で評価し、不成立なら選択肢を出さない（continue）。env は {"you": p, "self": ref(cid), "vars": {}}（free_if と同型）。
- 書き方: alt_cost: {cost: 1, civs: [water, water], if: {exists: {zone: bz, owner: you, filter: {types: [creature], tapped: true}}}}。
- proto T153（試験用条件付き代替コスト獣）。tests/test_vocab_pilot56.py 2件（条件成立/不成立での eval_cond）＋実カード parse テスト（4枚）。

## 第57弾: タップによる代替コスト（alt_cost の do に tap: true）（2026-11-04）
ラウンド65（alternative_cost 26件）の差し戻しで判明: 「コストを支払うかわりに、自分のクリーチャーをN体タップして召喚してもよい」の代替コストを表す語彙が無かった。alt_cost の do ステップは {zone, count, to, reason} の移動のみでタップに対応していなかった。
- defs: alt_cost の do ステップに `tap: true` を許可（to/reason は不要）。
- engine/turn.py: do ステップに tap: true があれば {"ev": "tap"} を生成。:alt 提示判定ではアンタップのカードのみを数える（タップ済みは除外）。
- 書き方: alt_cost: {do: [{zone: bz, filter: {types: [creature], civs: [light]}, count: 2, tap: true}]}。
- proto T154（試験用タップ代替コスト獣）。tests/test_vocab_pilot57.py 2件（定義の valid/invalid）。
- 待機12枚: tap_alt_cost×7 / alt_cost_do_tap×4 / alt_cost_tap_payment×1（gap名を tap_alt_cost に統一）。

## 第58弾: マッハファイターの付与パターン（2026-11-04）
ラウンド59（race_addition）の差し戻しで判明: 「〜に『マッハファイター』を与える」の付与パターンが変換エージェントに知られていなかった。基盤は既存（keyword_patterns.yaml の mach_fighter パターン、combat._attack_options の allow 判定、第50弾の実カードテスト dm24rp3-076）。
- 自身が持つ場合: keyword_patterns.yaml の `mach_fighter` が自動処理（出た時に trigger → 自分に allow 付与、duration: end_of_turn）。変換側は text から「マッハファイター（…）」を除くだけ。
- 他に与える場合: `op: modify` で `mod: {allow: [{action: attack_creature, other: {tapped: false}}]}` を直接付与し、duration: end_of_turn。「出たターンの間」の条件は、付与対象が出たばかり（誘発の subject）か、常在型で全体に与える場合は各クリーチャーの出たターンにのみ有効というルール解釈でカバーする。
- 書き方（誘発型）: when: {event: move, to: bz, subject: {owner: you, filter: {...}}} → effect: [{op: modify, select: {ref: event.subject}, mod: {allow: [{action: attack_creature, other: {tapped: false}}]}, duration: end_of_turn}]。
- 書き方（常在型）: kind: static, affects: {zone: bz, owner: you, filter: {types: [creature]}}, mod: {gain: [{kind: trigger, when: {event: move, to: bz, subject: self}, effect: [{op: modify, select: {ref: self}, mod: {allow: [{action: attack_creature, other: {tapped: false}}]}, duration: end_of_turn}]}]}。既に場にいるクリーチャーには trigger が発火しない（正しいルール動作）。
- tests/test_vocab_pilot58.py 2件（誘発付与の parse／常在付与の parse）＋実カード parse テスト。
- 待機16枚（mach_fighter のみが gap のもの）。複合 gap の4枚（dmrp21-7a、dm26ex1-027、dm26ex3-033、dm26ex2-pr005）は別途対応。

## 第59弾: battle_indestructible（バトル中破壊されない）（2026-11-04）
「バトル中、このクリーチャーは破壊されない」を表す語彙が無かった。
- defs: MOD_KEYS に `battle_indestructible` を追加。値は true のみ。
- engine/core.py: chars に `battle_indestructible: False` を追加し、static の mod から集約（ダイナモの add_from 経由も伝播）。
- engine/combat.py: _battle でパワー敗者から battle_indestructible 持ちを除外（破壊イベントを出さない）。勝敗判定（battle_win の対象）はパワーどおり。
- 書き方: kind: static, affects: self, mod: {battle_indestructible: true}。「火のクリーチャーとバトル中」の条件付きは if で書く（未対応の場合は unsupported）。
- tests/test_vocab_pilot59.py 2件（正常 parse／不正値の検証エラー）。
- 待機13枚（battle_indestructible のみが gap のもの）。

## 第60弾: attack_untapped（アンタップしているクリーチャーを攻撃できる）（2026-11-04）
「このクリーチャーは、アンタップしているクリーチャーを攻撃できる」は、マッハファイターの効果部分（第58弾）と同じ語彙で表せる。違いは「出たターンの間」の制限が無い点。
- 書き方: kind: static, affects: self, mod: {allow: [{action: attack_creature, other: {tapped: false}}]}。
- 付与の場合: op: modify で同じ mod を付与（duration は原文どおり。「このターン」なら end_of_turn）。
- tests/test_vocab_pilot60.py 2件（正常 parse／付与の parse）。
- 待機17枚（attack_untapped のみが gap のもの）。

## 第61弾: win_all_battles（すべてのバトルに勝つ）（2026-11-04）
「このクリーチャーはすべてのバトルに勝つ」を表す語彙が無かった。
- defs: MOD_KEYS に `win_all_battles` を追加。値は true のみ。
- engine/core.py: chars に `win_all_battles: False` を追加し、static の mod から集約（ダイナモ経由も伝播）。
- engine/combat.py: _battle でパワー比較の前に win_all_battles を判定。片方だけ持てばその側が勝ち、両方持てば相打ちなし。
- 書き方: kind: static, affects: self, mod: {win_all_battles: true}。
- tests/test_vocab_pilot61.py 2件（正常 parse／不正値の検証エラー）。
- 待機4枚（win_all_battles のみが gap のもの）。dmrp15-031 は ability_ignore との複合のため別途対応。

## 第62弾: add_civs（文明追加）（2026-11-04）
「〜は〜のクリーチャーでもある」「文明に〜を追加する」を表す語彙が無かった。
- defs: MOD_KEYS に `add_civs` を追加。文明名の非空リスト（CIVS で検証）。
- engine/core.py: chars の集約で add_civs の文明を ch["civs"] に追加（重複なし）。
- 書き方: kind: static, affects: {...}, mod: {add_civs: ["fire"]}。「好きな文明をひとつ追加する」は選択肢が必要なため別途検討。
- tests/test_vocab_pilot62.py 2件（正常 parse／不正値の検証エラー）。
- 待機10枚（civ_addition のみが gap のもの）。

## 第63弾: force_attack（可能なら攻撃する）— 新語彙なし（2026-11-04）
「可能であれば攻撃する」は既存の `require: ["attack"]` で表せる（エンジンが強制攻撃を処理済み）。
- 書き方: kind: static（または modify）, affects: {...}, mod: {require: ["attack"]}
- duration で期間を指定（例: 次の相手のターン中 → until_next_opp_turn_end）
- tests/test_vocab_pilot63.py 2件（正常 parse／検証）
- 待機14枚（force_addition のみが gap のもの）。

## 第64弾: must_attack_this_creature（相手は可能ならこのクリーチャーを攻撃する）— 新語彙なし（2026-11-04）
「相手は可能ならこのクリーチャーを攻撃する」は既存の `mod: {must_be_attacked: true}` で表せる（第51弾で実装済み）。
- 書き方: kind: static, affects: self, mod: {must_be_attacked: true}
- enters_tapped との複合も対応可能（両方とも既存語彙）
- tests/test_vocab_pilot64.py 2件（正常 parse／検証）
- 待機7枚（enters_tapped + must_attack_this_creature のみが gap のもの）。

## 第65弾: cost_gt_count（コストがゾーンの枚数より大きい）— 新語彙なし（2026-11-05）
「相手のマナゾーンにあるカードの枚数よりコストが大きいクリーチャー」は既存の `if: {cmp: [{cost_of: ...}, ">", {count: ...}]}` で表せる。
- 書き方: trigger の if に cmp を使用。cost_of で対象のコスト、count でゾーンの枚数を取得。
- 例: `if: {cmp: [{cost_of: {ref: event.subject}}, ">", {count: {zone: mana, owner: opp}}]}`
- tests/test_vocab_pilot65.py 2件（正常 parse／検証）
- 待機14枚（cost_gt_count のみが gap のもの）。

## 第66弾: colorless（無色フィルタ）（2026-11-05）
「無色カード」を対象とするフィルタが無かった。
- defs: FILTER_KEYS に `colorless` を追加。
- engine/selectors.py: filter_match で colorless をチェック（civs が空の場合に true）。
- 書き方: filter: {colorless: true}（無色カードのみ）、filter: {colorless: false}（無色でないカード）。
- tests/test_vocab_pilot66.py 2件（正常 parse／FILTER_KEYS 確認）。
- 待機13枚（filter_colorless のみが gap のもの）。

## 第67弾: tap_activated_ability（攻撃するかわりにタップして能力を使う）— 新語彙なし（2026-11-05）
「このクリーチャーで攻撃するかわりに、タップして次の能力を使ってもよい」は既存の `kind: activate, cost: {tap: self}` で表せる。
- 書き方: kind: activate, cost: {tap: self}, effect: [...]
- 「攻撃するかわりに」は activate のコストとして表現（エンジンが攻撃の代わりに発動することを処理）。
- tests/test_vocab_pilot67.py 2件（正常 parse／検証）
- 待機13枚（tap_activated_ability のみが gap のもの）。

## 第68弾: wave_striker（ウェーブストライカー）— 新語彙なし（2026-11-05）
「ウェーブストライカー」は既存のキーワード（keywords.yaml に定義済み）。条件付き能力の付与は if で表す。
- 書き方: keywords: [wave_striker]、続く能力に `if: {cmp: [{count: {zone: bz, owner: any, other: true, filter: {keyword: wave_striker}}}, ">=", 2]}` を付ける。
- tests/test_vocab_pilot68.py 2件（正常 parse／検証）
- 待機13枚（wave_striker のみが gap のもの）。

## 第69弾: kourin（光臨）— 新語彙なし（2026-11-05）
「光臨：自分のターンの終わりに、このクリーチャーがタップされていれば、〜」は既存の trigger + if で表せる。
- 書き方: kind: trigger, when: {event: turn_end, player: you}, if: {exists: {ref: self, filter: {tapped: true}}}, effect: [...]
- 「タップされていれば」は exists で self の tapped 状態を確認。
- tests/test_vocab_pilot69.py 2件（正常 parse／検証）
- 待機13枚（kourin のみが gap のもの）。

## 第70弾: ability_ignore（能力を無視する）— 新語彙なし（2026-11-05）
「〜の能力を無視する」は既存の `mod: {ignore: [all]}` で表せる（modify で付与、duration で期間を指定）。
- 書き方: op: modify, select: {...}, mod: {ignore: [all]}, duration: until_next_own_turn_start 等
- 対象が「すべてのクリーチャー」の場合は select で対象範囲を指定する。
- tests/test_vocab_pilot70.py 2件（正常 parse／検証）
- 待機13枚（ability_ignore のみが gap のもの）。

## 第71弾: l_gate（L・ゲート）— 新語彙なし（2026-11-05）
「L・ゲート：種族（このクリーチャーが破壊される時、墓地に置くかわりに、その種族を１体、自分の墓地から手札に戻してもよい。そうした場合、このクリーチャーを山札の一番下に置く）」は既存の kind: replace で表せる。
- 書き方: kind: replace, when: {event: move, from: bz, to: graveyard, reason: destroy, subject: self}, instead: [may で墓地から種族1体を手札へ、そうしたら self を山札の一番下へ]
- 種族はカードごとに異なるためキーワード化せず、パターンとして各カードに書く。
- tests/test_vocab_pilot71.py 2件（正常 parse／検証）
- 待機12枚（l_gate のみが gap のもの）。

## 第72弾: summon_from_mana_or_graveyard（マナゾーンまたは墓地から召喚）— 新語彙なし（2026-11-05）
「このクリーチャーを、自分のマナゾーンまたは墓地から召喚してもよい」は既存キーワード2つの併記で表せる。
- 書き方: keywords: [summon_from_mana, summon_from_graveyard]
- tests/test_vocab_pilot72.py 2件（正常 parse／検証）
- 待機15枚（summon_from_mana_or_graveyard のみが gap のもの）。

## 第73弾: zone_count_comparison（ゾーン枚数の相手比較）— 新語彙なし（2026-11-05）
「自分の〜が相手より少ない場合」は既存の cmp + count（owner: you / opp）で表せる。
- 書き方: if: {cmp: [{count: {zone: hand, owner: you}}, "<", {count: {zone: hand, owner: opp}}]}
- 「多い場合」は ">"、「以下／以上」は "<=" / ">="。
- tests/test_vocab_pilot73.py 2件（正常 parse／検証）
- 待機15枚（zone_count_comparison のみが gap のもの）。

## 第74弾: enters_event_trigger（他クリーチャーが出た時の誘発）— 新語彙なし（2026-11-05）
「自分の〜がバトルゾーンに出た時」は既存の when.subject セレクタで表せる。
- 書き方: kind: trigger, when: {event: move, to: bz, subject: {owner: you, other: true, filter: {race_has: ...}}}（summon イベントでも可）
- 効果の対象が self の場合は effect 内で select: {ref: self} を使う。
- tests/test_vocab_pilot74.py 2件（正常 parse／検証）
- 待機15枚（enters_event_trigger のみが gap のもの）。

## 第75弾: battle_trigger（バトルする時）— エンジン拡張あり（2026-11-05）
「このクリーチャーがバトルする時」は battle_start イベントで表す。proto T155。
- 攻撃側: when: {event: battle_start, subject: self}。バトル相手は select: {ref: event.opponent}。
- 守備側（攻撃先になった時）: when: {event: battle_start, opponent: self}（本弾で when の opponent キー照合を events.py に追加）。バトル相手（攻撃クリーチャー）は select: {ref: event.subject}。
- selectors.py に ref: event.opponent を追加。defs.py の when 検証に opponent を追加（attacker と同形）。
- tests/test_vocab_pilot75.py 3件（parse + 攻撃側・守備側の実挙動）。試験カード R075/R076 を tests/rule_cards.yaml に追加。
- 待機15枚（battle_trigger のみが gap のもの）。

## 第76弾: dynamo（ダイナモ）— 新語彙なし（2026-11-05）
「ダイナモ」は keywords.yaml に定義済み（エンジン挙動テスト tests/test_vocab_dynamo.py あり）。
- 書き方: keywords: [dynamo]
- 意味: バトルが始まる時、あるいはこのクリーチャーで攻撃できる時、タップしてもよい。そうした場合、そのターンの終わりまで、パワーと能力（ダイナモ自身を除く）を自分の他のダイナモ1体に加える。
- tests/test_vocab_pilot76.py 2件（正常 parse／キーワード定義確認）
- 待機12枚（dynamo のみが gap のもの）。

## 第77弾: attacked_trigger（攻撃された時）— 新語彙なし（2026-11-05）
「このクリーチャーが攻撃された時」は既存の attack イベント + target: self で表せる。
- 書き方: kind: trigger, when: {event: attack, target: self}
- 「相手が自分のクリーチャーを攻撃する時」は target: {owner: you, filter: {types: [creature]}}。
- 攻撃宣言時に解決する（ブロック・バトルの前）。
- tests/test_vocab_pilot77.py 3件（parse + 実挙動）。試験カード R077 を tests/rule_cards.yaml に追加。
- 待機11枚（attacked_trigger のみが gap のもの）。

## 第78弾: shield_event_trigger（シールドゾーンに置かれた時）— 新語彙なし（2026-11-05）
「自分のシールドゾーンにカードが置かれた時」は既存の move イベント + to: shield で表せる。
- 書き方: kind: trigger, when: {event: move, to: shield, subject: {owner: you}}
- 「シールドがブレイクされた時」は event: break（player: you）を使う。
- tests/test_vocab_pilot78.py 2件（正常 parse／検証）
- 待機11枚（shield_event_trigger のみが gap のもの）。

## 第79弾: civ_count（文明の種類数）— 新語彙なし（2026-11-05）
「〜にある文明ひとつにつき」は既存の式 civ_count で表せる（対象カード群にある文明の種類数、多色はそれぞれ数える）。
- 書き方: {civ_count: {zone: bz, owner: opp}} を式として使う（breaks や power の係数、cmp の辺など）。
- tests/test_vocab_pilot79.py 2件（正常 parse／検証）
- 待機11枚（civ_count のみが gap のもの）。

## 第80弾: break_increase（ブレイク数増加）— 新語彙なし（2026-11-05）
「シールドをさらにN枚ブレイクする」は静的 modify の mod: {breaks: N}（加算）で表せる。
- 書き方: kind: static, affects: {...}, mod: {breaks: 1}。条件は if で付ける。
- W・ブレイカー等のキーワード化済みのブレイク数とは別に、付与・増加分を mod で表す。
- tests/test_vocab_pilot80.py 2件（正常 parse／検証）
- 待機11枚（break_increase のみが gap のもの）。

## 第81弾: not_race_filter（〜でないクリーチャー）— 新語彙 filter: {not_race_has}（2026-11-05）
「ドラゴンでないクリーチャー」のような種族否定フィルタが無かったため、filter キー not_race_has を追加した。
- 書き方: filter: {not_race_has: ドラゴン}（race_has の否定。種族文字列に部分一致したら除外）
- 実装: defs.py の FILTER_KEYS に追加、engine/selectors.py の filter_match に対応行を追加。proto T156。
- tests/test_vocab_pilot81.py 3件（parse／filter_match の実挙動）
- 待機11枚（not_race_filter のみが gap のもの）。
- 拡張（同日）: not_race_has はリストも受け付ける（いずれかに部分一致したら除外）。dmr12-s04 の3種族否定で使用。tests/test_vocab_pilot81.py に list 形式のテストを追加（計4件）。

## 第82弾: cost_le_card_cost（そのカード以下のコスト）— 新語彙なし（2026-11-05）
「そのカード以下のコストを持つ〜」は filter の cost_le に式を書く既存パターンで表せる（cost_le / cost_ge / power_le / power_ge / races は式可）。
- 書き方: filter: {cost_le: {cost_of: {ref: 束縛変数}}}（めくった／置いたカードを as で束縛して参照）。
- tests/test_vocab_pilot82.py 2件（正常 parse／検証）
- 待機11枚（cost_le_card_cost のみが gap のもの）。

## 第83弾: evolution_existence_filter（進化クリーチャーの有無）— 新語彙なし（2026-11-05）
「自分の進化クリーチャーがあれば／なければ」は既存の filter: {evolution: true} + exists 条件で表せる。
- 書き方: if: {exists: {zone: bz, owner: you, filter: {evolution: true}}}（否定は not で包む）。
- tests/test_vocab_pilot83.py 2件（正常 parse／検証）
- 待機11枚（evolution_existence_filter のみが gap のもの）。

## 第84弾: evolution_gv（進化GV）— 新語彙なし（2026-11-05）
「進化GV-自分の〜N体を重ねた上に置く」は既存の evolve_from + evolve_count で表せる。
- 書き方: evolve_from: {<filter>}, evolve_count: N（重ねる進化元の体数）。
- tests/test_vocab_pilot84.py 2件（正常 parse／検証）
- 待機12枚（evolution_gv のみが gap のもの）。

## 第85弾: cost_lt_card（そのカードよりコストが小さい）— 新語彙なし（2026-11-05）
「そのカードよりコストが小さい〜」は cost_le に sum 式を書く確立済みイディオムで表せる。
- 書き方: filter: {cost_le: {sum: [{cost_of: {ref: 束縛変数}}, -1]}}（第65弾 cost_gt_count の項と対）。
- tests/test_vocab_pilot85.py 2件（正常 parse／検証）
- 待機12枚（cost_lt_card のみが gap のもの）。

## 第86弾: thrilling_three（スリリング・スリー）— 新語彙なし（2026-11-05）
「山札の上から3枚を表向きにし、〜1体につき次の能力を1回行う。その後、すべて山札の一番下に戻す」は既存の choose（look）+ repeat（回数=式）+ move で表せる。
- 書き方: choose {from_top: 3, look: true} as: pile → repeat {times: {count: {ref: pile, filter: {...}}}} で本体 → move {ref: pile} to: deck, position: bottom, order: choose。
- tests/test_vocab_pilot86.py 2件（正常 parse／検証）
- 待機15枚（thrilling_three のみが gap のもの）。

## 第87弾: ultra_saber（ウルトラ・セイバー）— 新語彙なし（2026-11-05）
「自分の〜が離れる時、かわりにこのクリーチャーを破壊してもよい」は既存の replace で表せる（shield_saver の汎用版）。
- 書き方: kind: replace, when: {event: move, from: bz, subject: {owner: you, other: true, filter: {該当条件}}}, optional: true, instead: [destroy {ref: self}]。
- tests/test_vocab_pilot87.py 2件（正常 parse／検証）
- 待機14枚（ultra_saber のみが gap のもの）。

## 第88弾: grant_based_on_own_power_threshold（自分のパワー条件で得る）— 新語彙なし（2026-11-05）
「パワーがN以上のとき、〜を得る」は条件付き static で表せる（自分の現在パワーを exists で参照）。
- 書き方: kind: static, affects: self, if: {exists: {ref: self, filter: {power_ge: N}}}, mod: {grant: [...]}。
- power は修正込みの現在値で判定される。
- tests/test_vocab_pilot88.py 2件（正常 parse／検証）
- 待機13枚（grant_based_on_own_power_threshold のみが gap のもの）。

## 第89弾: does_not_untap_next_turn（次のターンのはじめにアンタップしない）— 新語彙なし（2026-11-05）
「タップする。次の相手のターンのはじめに、そのクリーチャーはアンタップしない」は tap 演算の no_untap_next で表せる（フリーズ条項）。
- 書き方: {op: tap, select: {...}, no_untap_next: true}。
- tests/test_vocab_pilot89.py 2件（正常 parse／検証）
- 待機21枚（does_not_untap_next_turn のみが gap のもの）。

## 第90弾: enters_battle_zone_tapped（タップして出る）— 新語彙なし（2026-11-05）
「〜（のクリーチャー）は、タップして出る」は既存の grant enters_tapped で表せる。
- 書き方: kind: static, affects: {zone: bz, owner: <対象>, filter: {...}}, mod: {grant: [enters_tapped]}。
- 自分自身がタップして出る場合は affects: self。
- tests/test_vocab_pilot90.py 2件（正常 parse／検証）
- 待機16枚（enters_battle_zone_tapped のみが gap のもの）。

## 第91弾: next_summon_cost_reduction（次に召喚するコスト軽減）— 新語彙なし（2026-11-05）
「このターン、次に召喚する自分の〜のコストをN少なくする」は cost_may（once）の modify で表せる（dmex14-060 の先例）。
- 書き方: {op: may, body: [{op: modify, select: {zone: hand, owner: you, filter: {...}}, mod: {cost_may: {amount: N, min: 0, once: true}}, duration: end_of_turn, dynamic: true}]}。
- tests/test_vocab_pilot91.py 2件（正常 parse／検証）
- 待機16枚（next_summon_cost_reduction のみが gap のもの）。

## 第92弾: summon_only_entry（召喚によって出た時）— 新語彙なし（2026-11-05）
「このクリーチャーが召喚によって出た時」は move イベントの理由限定で表せる（delayed_trigger の reason: summon の先例）。
- 書き方: kind: trigger, when: {event: move, to: bz, reason: summon, subject: self}。
- 通常の「出た時」（summon イベント）は召喚以外で出た場合も誘発するため、原文が「召喚によって」を明記する場合のみこの形を使う。
- tests/test_vocab_pilot92.py 2件（正常 parse／検証）
- 待機20枚（summon_only_entry のみが gap のもの）。

## 第93弾: soul（ソウル種族フィルタ）— 新語彙なし（2026-11-05）
(H・ソウル) 等のソウルは種族として扱い、any_of の race_has で表せる。
- 書き方: filter: {any_of: [{race_has: H・ソウル}, {race_has: M・ソウル}, {race_has: E・ソウル}, {race_has: K・ソウル}, {race_has: W・ソウル}, {race_has: B・ソウル}]}。
- 「他の」は other: true。
- tests/test_vocab_pilot93.py 2件（正常 parse／検証）
- 待機18枚（soul のみが gap のもの）。

## 第94弾: entry_replacement（出る時の置換）— 新語彙なし（2026-11-05）
「相手のクリーチャーが出る時、かわりに〜に置く」は出場置換で表せる。
- 書き方: kind: replace, when: {event: move, to: bz, subject: {owner: opp, filter: {...}}}, instead: [move {ref: event.subject} to: <置換先>]。「置かせてもよい」は optional: true。
- tests/test_vocab_pilot94.py 2件（正常 parse／検証）
- 待機18枚（entry_replacement のみが gap のもの）。

## 第95弾: mana_evolution（マナ進化）— 新語彙なし（2026-11-05）
「マナ進化：〜を自分のマナゾーンから選び、このクリーチャーをその上に重ねつつ出す」は evolve_zone で表せる（墓地進化の先例）。
- 書き方: types に evolution を含め、evolve_from: {<進化元の条件>}、evolve_zone: mana。
- tests/test_vocab_pilot95.py 2件（正常 parse／検証）
- 待機16枚（mana_evolution のみが gap のもの）。

## 第96弾: opponent_chooses_branch（相手が選ぶ分岐）— エンジン拡張（2026-11-05）
「相手は〜してもよい。そうしたら…、そうしなければ…」は may の決定者を相手にする＋ else 分岐で表す。
- エンジン変更: dmsim/engine/ops.py の op_may に player 引数を追加（従来はコントローラー固定）。{op: may, player: opp, body: [...], else: [...]} と書く。else は「そうしなければ」。
- 試験カード R078 を tests/rule_cards.yaml に追加。tests/test_vocab_pilot96.py 3件（parse 2件＋相手が決定者になる実挙動1件）。
- 待機20枚（opponent_chooses_branch のみが gap のもの）。

## 第97弾: night_magic（ナイト・マジック）— 新語彙なし（2026-11-05）
「バトルゾーンに自分のナイトがあれば、この呪文の能力をもう一度使ってもよい」は、呪文の効果の後ろに条件付き再実行を置く。
- 書き方: spell: [<効果>, {op: if, cond: {exists: {zone: bz, owner: you, filter: {race_has: ナイト}}}, then: [{op: may, body: [<効果>]}]}]（先例 dm28-016 魔弾プラス・ワン）。
- tests/test_vocab_pilot97.py 2件（正常 parse／検証）
- 待機16枚（night_magic のみが gap のもの）。

## 第98弾: enters_from_non_hand_replacement（手札以外から出る時の置換）— エンジン拡張（2026-11-05）
「相手のクリーチャーが、相手の手札以外から出る時、かわりに手札に加える」等の出現元で条件づける置換。
- エンジン変更: when の from / to / reason / via にリスト指定を許可（いずれかに一致）。dmsim/engine/events.py の _match_when と dmsim/defs.py の検証を対応させた。
- 書き方: {kind: replace, when: {event: move, to: bz, from: [graveyard, mana, deck, shield], subject: {owner: opp, filter}}, instead: [...]}。「召喚以外の方法で出る」は reason: put（バトルゾーンへの出現理由は summon / put の2種のみ）。
- tests/test_vocab_pilot98.py 3件（parse 2件＋照合の実挙動1件）。
- 待機10枚（enters_from_non_hand_replacement のみが gap のもの）。

## 第99弾: attack_target_filter（攻撃できる対象のフィルタ）— 新語彙なし（2026-11-05）
「タップされていない○○のクリーチャーを攻撃できる」は第60弾の allow に other フィルタを付けて表す。
- 書き方: kind: static, affects: self, mod: {allow: [{action: attack_creature, other: {tapped: false, civs: [light]}}]}。other はそのまま filter_match に渡るため、civs / races / cost_le 等の通常フィルタが使える。
- tests/test_vocab_pilot99.py 2件（正常 parse／検証）
- 待機10枚（attack_target_filter のみが gap のもの）。

## 第100弾: oni_end（鬼エンド）— 新語彙なし（2026-11-05）
「クリーチャーが攻撃する時、シールドが１つもないプレイヤーがいて、自分のマナゾーンに闇文明と火文明があれば、手札からコストを支払わずに召喚/唱えてもよい」はニンジャ・ストライクと同じ declare で表す。
- 書き方: {kind: declare, zone: hand, when: {event: attack, subject: {owner: any}}, if: {all: [{any: [{cmp: [{count: {zone: shield, owner: you}}, "==", 0]}, {cmp: [{count: {zone: shield, owner: opp}}, "==", 0]}]}, {exists: {zone: mana, owner: you, filter: {civs: [darkness]}}}, {exists: {zone: mana, owner: you, filter: {civs: [fire]}}}]}, effect: [{op: play_free, select: {ref: self}}]}。条件（対象プレイヤー・文明）は原文どおりに調整する。
- tests/test_vocab_pilot100.py 2件（正常 parse／検証）
- 待機10枚（oni_end のみが gap のもの）。

## 第101弾: summon_restriction（召喚制限）— 新語彙なし（2026-11-05）
「すべてのプレイヤーは、コスト４以下のクリーチャーを召喚できない」は手札ゾーンへの常在型 deny で表す。
- 書き方: {kind: static, affects: {zone: hand, owner: any, filter: {types: [creature], cost_le: 4}}, mod: {deny: [summon]}}（先例 34-sec001）。owner は原文どおり（自分だけ／相手だけ／全員）。効果で出すことは禁止しない点も原文どおり。
- tests/test_vocab_pilot101.py 2件（正常 parse／検証）
- 待機10枚（summon_restriction のみが gap のもの）。

## 第102弾: samurai_generate（侍流ジェネレート）— 新語彙なし（2026-11-05）
「このクリーチャーをバトルゾーンに出した時、クロスギアを１枚、自分の手札からコストを支払わずにジェネレートしてもよい」は play_free で表す（クロスギアをプレイする行為がジェネレート。move イベントにも via: generate が付く）。
- 書き方: {kind: trigger, when: {event: move, to: bz, subject: self}, effect: [{op: may, body: [{op: play_free, select: {zone: hand, owner: you, filter: {types: [cross_gear]}, count: 1}}]}]}。
- tests/test_vocab_pilot102.py 2件（正常 parse／検証）
- 待機10枚（samurai_generate のみが gap のもの）。

## 第103弾: linked_god_filter（リンクしているゴッド）— 新語彙あり（2026-11-05）
「進化クリーチャーまたはリンクしているゴッド」は any_of の片方として新フィルタで表す。
- 新フィルタ: {linked_god: true}（defs.py FILTER_KEYS 追加、engine/selectors.py の filter_match に実装）。判定はリンク位置キーワードを持ち、link_members が2体以上（実際にリンク中）。
- 書き方: filter: {any_of: [{evolution: true}, {linked_god: true}]}。proto T157。
- 試験カード R079・R080 を tests/rule_cards.yaml に追加。tests/test_vocab_pilot103.py 2件（parse／照合の実挙動）。
- 待機7枚（linked_god_filter のみが gap のもの）。

## 第104弾: attack_end_trigger（攻撃の終わりに）— 新語彙なし（2026-11-05）
「このクリーチャーの攻撃の終わりに、〜」は既存の attack_end イベントで表す（キリフダッシュ用に追加済みのイベント。攻撃クリーチャーが subject）。
- 書き方: {kind: trigger, when: {event: attack_end, subject: self}, effect: [...]}。
- tests/test_vocab_pilot104.py 2件（正常 parse／検証）
- 待機7枚（attack_end_trigger のみが gap のもの）。

## 第105弾: first_tap_trigger（はじめてタップした時）— 新語彙なし（2026-11-05）
「各ターン、このクリーチャーがはじめてタップした時、〜」は tap イベント＋ first_time で表す。
- 書き方: {kind: trigger, first_time: true, when: {event: tap, subject: self}, effect: [...]}。first_time はラウンド110（dmrp14-007 の attack_end）でも使用した既存フラグ。
- tests/test_vocab_pilot105.py 2件（正常 parse／検証）
- 待機7枚（first_tap_trigger のみが gap のもの）。

## 第106弾: trigger_when_wins_battle（バトルに勝った時）— 新語彙なし（2026-11-05）
「このクリーチャーがバトルに勝った時、〜」は既存の battle_win イベントで表す（勝者のみが subject）。
- 書き方: {kind: trigger, when: {event: battle_win, subject: self}, effect: [...]}。
- tests/test_vocab_pilot106.py 2件（正常 parse／検証）
- 待機9枚（trigger_when_wins_battle のみが gap のもの）。

## 第107弾: tap_event_trigger（タップした時）— 新語彙なし（2026-11-05）
「このクリーチャーがタップした時、〜」は第105弾の first_time を付けない形で表す（毎回発動）。
- 書き方: {kind: trigger, when: {event: tap, subject: self}, effect: [...]}。
- tests/test_vocab_pilot107.py 2件（正常 parse／検証）
- 待機7枚（tap_event_trigger のみが gap のもの）。

## 第108弾: cost_le_card（カードのコスト以下）— 新語彙なし（2026-11-05）
選択フィルタ側でも第82弾のイディオムが使える: filter: {cost_le: {cost_of: {ref: t}}} で
「as で束縛したカードのコスト以下」を表す（自身以下は {cost_of: {ref: self}}）。
- 書き方: select ... as: t → select/filter で cost_le: {cost_of: {ref: t}}。
- tests/test_vocab_pilot108.py 2件（正常 parse／検証）
- 待機7枚（cost_le_card のみが gap のもの）。

## 第109弾: shield_trigger_grant（S・トリガー付与）— 新語彙なし（2026-11-05）
「（ゾーンにある）自分のカードは『S・トリガー』を得る」は static の grant で表す。
- 書き方: {kind: static, affects: {zone: shield/hand, owner: you, filter}, mod: {grant: [s_trigger]}}。
  先例: dm24ex4-015（手札の光カード）、dmr20-s01（シールドのメタリカ/裁きの紋章）。
- tests/test_vocab_pilot109.py 2件（正常 parse／検証）
- 待機7枚（shield_trigger_grant のみが gap のもの）。

## 第110弾: battle_win_all（すべてのバトルに勝つ）— 新語彙なし（2026-11-05）
「このクリーチャーはすべてのバトルに勝つ」は第61弾の mod で表す（条件付きは if を併記）。
- 書き方: {kind: static, mod: {win_all_battles: true}}（combat._battle でパワー比較より優先）。
- tests/test_vocab_pilot110.py 2件（正常 parse／検証）
- 待機7枚（battle_win_all のみが gap のもの）。

## 第111弾: optional_enters_tapped（タップして出てもよい）— 新語彙なし（2026-11-05）
「タップして出てもよい。そうした場合、〜」は出現置換の may で表す。
- 書き方: {kind: replace, when: {event: move, subject: self, to: bz}, optional: true,
  effect: [tap {select: {ref: self}}, <効果>]}（出る前に置換として解決し、タップ状態で出る）。
- tests/test_vocab_pilot111.py 2件（正常 parse／検証）
- 待機7枚（optional_enters_tapped のみが gap のもの）。

## 第112弾: recast_from_graveyard（墓地から唱える）— 新語彙なし（2026-11-05）
「コスト○以下の呪文を1枚、自分の墓地からコストを支払わずに唱える」は play_free で表す。
- 書き方: {op: play_free, select: {zone: graveyard, owner: you, filter: {types: [spell], cost_le: N}, count: 1}}。
  唱えた後の置き場変更は replace（move の to: graveyard を deck bottom へ）で併記する。
- tests/test_vocab_pilot112.py 2件（正常 parse／検証）
- 待機7枚（recast_from_graveyard のみが gap のもの）。

## 第113弾: draw_replacement（引くかわりに）— 新語彙なし（2026-11-05）
「自分がカードを引く時、1枚のかわりに2枚引いてもよい。そうした場合、手札を1枚捨てる」は
draw イベントへの置換で表す（draw は個別イベントとして発行される）。
- 書き方: {kind: replace, when: {event: draw, player: you}, optional: true,
  instead: [{op: draw, count: 2}, {op: discard, select: {zone: hand, owner: you, count: 1}}]}。
- tests/test_vocab_pilot113.py 2件（正常 parse／検証）
- 待機7枚（draw_replacement のみが gap のもの）。

## 第114弾: random_discard（見ないで選び捨てさせる）— 新語彙なし（2026-11-05）
「相手の手札を1枚見ないで選び、捨てさせる」は既存の discard で表す
（手札は秘匿ゾーンのため、選ぶ側からは見えない選択になる。変換済み110件が同型）。
- 書き方: {op: discard, select: {zone: hand, owner: opp, count: 1}}（chooser は既定でコントローラー）。
  「見て選ぶ」場合は先に look で公開してから選ぶ点が異なる。
- tests/test_vocab_pilot114.py 2件（正常 parse／検証）
- 待機7枚（random_discard のみが gap のもの）。

## 第115弾: filter_not_race（〜でないクリーチャー）— 新語彙なし（2026-11-05）
選択フィルタの「種族〜でない」は第81弾の not_race_has で表す（文字列／リスト両形式）。
- 書き方: filter: {not_race_has: ドラゴン}（複数種族のいずれでもない場合はリスト）。
- tests/test_vocab_pilot115.py 2件（正常 parse／検証）
- 待機8枚（filter_not_race のみが gap のもの）。

## 第116弾: power_lt_card（そのカードよりパワーが小さい）— エンジン拡張（2026-11-05）
新式 power_of（参照カードの現在パワー。cost_of の対）を追加した。
- defs: 式キーに power_of を追加。selectors.eval_expr: power_of を評価（chars の現在パワー、複数なら最大）。
  schema にも power_of を追加。proto T158。
- ついでに cost_of / power_of の参照解決を共通化（_expr_refs）: 従来 {cost_of: {ref: t}} は
  実行時 TypeError、{cost_of: "self"} は 0 扱いになる潜在バグがあり、{ref:} 形式と "self" が
  正しく解決されるよう修正した（変換済みカードの dict 形式 cost_of が実際に効くようになる）。
- 書き方: filter: {power_le: {sum: [{power_of: {ref: t}}, -1]}}（「より小さい」イディオム）。
- tests/test_vocab_pilot116.py 4件（parse 2件＋実挙動2件: R082 power_of で T001 のみ破壊、
  R081 cost_of dict 形式で T001 のみ破壊。試験カード R081〜R083）
- 待機9枚（power_lt_card のみが gap のもの）。

## 第117弾: cost_lt_count（コストが数より小さい）— 新語彙なし（2026-11-05）
選択フィルタの cost_le に {sum: [{count: <ゾーン集計>}, -1]} を渡すことで
「（数）よりコストが小さい」を表す（第65・73弾の集計式＋「より小さい」イディオム）。
- 書き方: filter: {cost_le: {sum: [{count: {zone: mana, owner: you}}, -1]}}。
- tests/test_vocab_pilot117.py 2件（正常 parse／検証）
- 待機9枚（cost_lt_count のみが gap のもの）。
