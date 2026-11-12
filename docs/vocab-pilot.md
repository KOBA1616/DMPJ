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
- 持続期間の裏取りと解除範囲の修正（2026-11-09）: 公式 QA 44820／48760 で「次の自分のターンのはじめまで」（相手ターンを挟んで続く）を確認。ターン開始時の解除は bz が共有ゾーンのため全カードに及んでいた（自分のターンに解放すると相手ターンのはじめに解けていた）ので、解除を「そのターンのプレイヤーがコントロールするカードだけ」に絞った。hyper_act／Zラッシュ／op hyper_release の全経路が対象。詳細は faq-check-hyper-duration-20261109.md

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

## 第118弾: summon_event_trigger（召喚した時）— 新語彙なし（2026-11-05）
「自分の他のクリーチャーを召喚した時、〜」は move イベント（reason: summon）を他者 subject で表す。
- 書き方: {kind: trigger, when: {event: move, to: bz, reason: summon,
  subject: {owner: you, other: true, filter}}, effect: [...]}。
  「呪文を唱えた時」との複合条件は cast イベントの誘発を併記する。
- tests/test_vocab_pilot118.py 2件（正常 parse／検証）
- 待機8枚（summon_event_trigger のみが gap のもの）。

## 第119弾: enters_non_summon（召喚以外の方法で出た時）— 新語彙なし（2026-11-05）
「召喚以外の方法で出た時」は move イベントの reason: put で表す
（バトルゾーンへの出現理由は summon / put の2種のみ）。
- 書き方（誘発）: {kind: trigger, when: {event: move, to: bz, reason: put,
  subject: {owner: opp, filter}}, if: {is_turn: opp}, effect: [...]}。
- 書き方（置換）: {kind: replace, when: {event: move, to: bz, reason: put, subject: {...}},
  instead: [{op: move, select: {ref: event.subject}, to: graveyard, reason: put}]}。
- tests/test_vocab_pilot119.py 2件（正常 parse／検証）
- 待機6枚（enters_non_summon のみが gap のもの）。

## 第120弾: under_card_count（含まれるカードの数）— 新語彙なし（2026-11-05）
「そのクリーチャーに含まれるカード１枚につき」は under_of セレクタの count で表す。
- 書き方: 含まれる総数 = {sum: [1, {count: {under_of: <変数名またはself>}}]}
  （under_of は下にあるカードを返し、本体1枚を加える）。回数・枚数・パワー量の式に使う。
- tests/test_vocab_pilot120.py 2件（正常 parse／検証）
- 待機6枚（under_card_count のみが gap のもの）。

## 第121弾: total_count_condition（合計数条件）— 新語彙なし（2026-11-05）
「バトルゾーンとマナゾーンにある〜カードが合計N以上」は count の sum で表す。
- 書き方: {cmp: [{sum: [{count: {zone: bz, owner: you, filter}}, {count: {zone: mana, owner: you, filter}}]}, ">=", N]}。
  G・ゼロ等の free_if や static の if、コスト軽減の条件に使う。
- tests/test_vocab_pilot121.py 2件（正常 parse／検証）
- 待機6枚（total_count_condition のみが gap のもの）。

### 第122弾 battle_opponent_filter（2026-11-05）
- 「『ブロッカー』を持つクリーチャーとバトル中、パワーを+Nする」= mod: {battle_power: {amount: N, opponent_filter: {keyword: blocker}}}。「火のクリーチャーとバトル中、破壊されない」= mod: {battle_indestructible: {opponent_filter: {civs: [fire]}}}（エンジン拡張: battle_power / battle_indestructible に opponent_filter を追加。combat._battle が相手を渡してフィルタ判定。chars には battle_indestructible_filters として集める）。
- proto T159/T160、試験カード R084/R085/R086、tests/test_vocab_pilot122.py 6件（parse 2件＋実挙動4件: 対ブロッカーで勝つ／対非ブロッカーで負ける／対火で不壊／対自然で破壊）。

### 第123弾 mana_all_civilizations（2026-11-05）
- 「自分のマナゾーンにあるカードを、すべての文明のカードとして扱う」= static {affects: {zone: mana, owner: you}, mod: {add_civs: [light, water, darkness, fire, nature]}}。「すべての文明を持つかのようにタップしてもよい」系も同じ静的で表す（支払い時の文明として扱う点が本質）。
- エンジン拡張: turn._mana_choices の文明判定をカード定義ではなく特性（chars）ベースに変更（グループキーに chars の文明タプルを含める）。これで add_civs（自分の静的・マナ側の静的を含む）が支払いに効く。
- proto T161、試験カード R087/R088、tests/test_vocab_pilot123.py 3件（parse、R087 ありで自然マナが火の文明を満たす、なしでは満たせない）。

- 第123弾の適用範囲の訂正（ラウンド130）: 「〜を召喚する時／実行する時、すべての文明を持つかのようにタップしてもよい」のように支払い範囲が限定される変種は、無条件の静的にすると原文より広くなるため対象外。gap mana_civilization_tap として rejects に残す（dm24bd6-042、dm24rp2-074、dm26rp3-012）。第123弾の静的は無条件の「すべての文明のカードとして扱う」にのみ使う。

### 第124弾 holy_field（2026-11-05）
- 「ホーリー・フィールド（自分のシールドの数が相手以上であれば、このクリーチャーは次の能力を得る）」は新語彙なし。得る能力そのものに if: {cmp: [{count: {zone: shield, owner: you}}, ">=", {count: {zone: shield, owner: opp}}]} を付ける（第73弾のゾーン枚数比較＋第97弾の条件つき能力）。静的なら static の if、誘発なら trigger の if。
- tests/test_vocab_pilot124.py 3件（static parse、trigger parse、実カード dm36-072 の原文確認）。

### 第125弾 civilization_count（2026-11-05）
- 「自分のマナゾーンにある文明ひとつにつき」「文明の数以下のコスト」は既存の式 civ_count で表す（新語彙なし）。{civ_count: {zone: mana, owner: you}} は対象群にある文明の種類数（多色は持つ文明をすべて数える）。mod の count（パワー+N×種類数）、filter の cost_le 等の式、cmp の項（相手との比較）に使える。
- tests/test_vocab_pilot125.py 3件（power の count、filter の cost_le、cmp の項、それぞれ parse）。

### 第126弾 power_less_than_self（2026-11-05）
- 「パワーがこのクリーチャーより小さい相手のクリーチャー」は第116弾の filter {power_le: {sum: [{power_of: {ref: self}}, -1]}} で表す（選択側は candidates が式を前評価する）。
- 「パワーがこのクリーチャーより小さいクリーチャーにブロックされない」= static mod {deny: [{action: be_blocked, other: {power_le: <同式>}}]}。エンジン拡張: permits の other フィルタの式を許可側カード（self）基準で前評価する（core.permits の _other_filter、candidates と同じ方式）。
- proto T162、試験カード R089、tests/test_vocab_pilot126.py 3件（parse 1件＋実挙動2件: パワー3000ブロッカーはブロック不可、5000ブロッカーはブロックして相打ち）。

### 第127弾 indestructible（2026-11-05）
- 「破壊されない」は新語彙 static mod: {indestructible: true}（エンジン拡張）。chars に集め、events._apply_one が置換を経た最終的な破壊（reason: destroy で墓地へ）を防ぐ。バトルでも battle_indestructible と同様に扱う（combat の _battle_indestructible が併せて見る）。条件つきは static の if、付与は modify の mod で同じ形。
- proto T163、試験カード R090、tests/test_vocab_pilot127.py 5件（parse 2件＋実挙動3件: バトルで負けても残る／破壊効果でも残る／対照は破壊される）。

### 第128弾 facedown_mana（2026-11-05）
- 「裏向きのままマナゾーンに置く」は新語彙 move op の face_down: true（エンジン拡張: move イベントが face_down を運び、_apply_one がマナ到着時に裏向きにする。together の move でも伝播）。move+flip_down の合成は置かれた瞬間が表向きになるため採らない（ラウンド122の判断を正式化）。既にマナにあるカードを裏向きにするのは従来どおり flip_down op。
- 裏向きマナは支払い時に無色・マナ数1として扱う（_mana_choices の既存処理）。
- proto T164、試験カード R091、tests/test_vocab_pilot128.py 3件（parse、裏向きで到着し支払いで無色扱い、対照）。

### 第129弾 null_breaker（2026-11-05）
- 「ヌル・ブレイカー（このクリーチャーはシールドを０ブレイクする）」を keywords.yaml のキーワードとして登録（静的 mod {breaks: 0}）。攻撃時のブレイク数は break_opts で決まるため 0 が唯一の選択肢になる。
- エンジン修正: combat のダイレクトアタックでブレイク数 0 の時はブレイクタスク自体を積まない（ブレイクイベントも発生しない）。
- proto T165、試験カード R092、tests/test_vocab_pilot129.py 3件（parse、break_opts=[0]、攻撃してもシールドが割れない）。

### 第130弾 crew_breaker（2026-11-05）
- 「クルー・ブレイカー：X（自分の他のX１体につき、シールドをさらにもう１枚ブレイクする）」は static mod {breaks: {count: <selector>}} で表す（エンジン拡張: breaks に {count} 形式を追加。ブレイク数 = 1 + count_of(selector)。「他の」が無い原文では other を付けない）。
- proto T166、試験カード R093/R094、tests/test_vocab_pilot130.py 3件（parse、不正形式の拒否、他のドラゴン2体で break_opts=[3]／0体で [1]）。
- **訂正・統一（2026-11-05、全体テストで検出）**: breaks の dict 形式は既存カードにも2形式あり、第130弾の検証がそれらを弾いて3テスト失敗した。統一後の仕様: dict はすべて「1 + 値」— {count: sel} は 1+数、{amount: A, count: sel} は 1+A×数（dmd10-008 型）、{civ_count: sel} は 1+文明の種類数（第79弾、dmc34-025 型）。回帰テストとして R095/R096 を追加（同テストファイル、計5件）。なお第130弾以前、dict 形式は chars で未評価（int との max で壊れる潜在バグ）だったため、この統一で初めて実働する。

## 第131弾: powered_blocker（パワード・ブロッカー）— 新語彙なし（2026-11-06）
「パワード・ブロッカー +N（ブロック中、このクリーチャーのパワーを+Nする）」は常在型のパワー修整で表す。
- 書き方: kind: static, affects: self, mod: {power_when: {amount: N, when: blocking}}（ブロッカー自体はキーワードで処理済み）。
- tests/test_vocab_pilot131.py 2件（正常 parse／検証）
- 待機8枚（powered_blocker のみが gap のもの）。

## 第132弾: blocked_trigger（ブロックされた時）— 新語彙なし（2026-11-06）
「このクリーチャーがブロックされた時」は block イベントの attacker 照合で表す。
- 書き方: {kind: trigger, when: {event: block, attacker: self}, effect: [...]}。block レコードの subject はブロッカー側なので、「自分のクリーチャーがブロックされた時」を他者の視点で書く場合は subject: {owner: opp} になる（先例 dm30-050、dm29-012）。
- 試験カード R097 を tests/rule_cards.yaml に追加。tests/test_vocab_pilot132.py 3件（parse 2件＋実挙動1件）。
- 待機4枚（blocked_trigger のみが gap のもの）。

## 第133弾: cost_lt_card_cost（参照カードよりコストが小さい）— 新語彙なし（2026-11-06）
「その捨てたカードよりコストが小さい相手のクリーチャーを破壊する」は第82・85弾の式フィルタの応用で表す。
- 書き方: 捨てるカードを as で束縛し、対象選択の filter: {cost_le: {sum: [{cost_of: {ref: <束縛名>}}, -1]}}（「より小さい」＝参照コスト−1以下）。
- tests/test_vocab_pilot133.py 2件（正常 parse／検証）
- 待機4枚（cost_lt_card_cost のみが gap のもの）。

## 第134弾: entered_this_turn_filter（このターン中に出た）— 新語彙あり（2026-11-06）
「このターン中に出たクリーチャー」を対象フィルタで絞れるようにした。
- 新フィルタ: {entered_this_turn: true}（defs.py FILTER_KEYS 追加、engine/selectors.py の filter_match に実装）。判定はカードの entered_turn（バトルゾーンに出たターン。それ以外は -1）が現在のターンと一致するか。
- proto T167。tests/test_vocab_pilot134.py 2件（parse／照合の実挙動）。
- 待機4枚（entered_this_turn_filter のみが gap のもの）。entered_this_turn_condition（9枚）の条件側にも使える可能性あり。

## 第135弾: entered_this_turn_condition（このターン中に出た数での条件）— 新語彙なし（2026-11-06）
「このターン中に自分のクリーチャーがN体以上バトルゾーンに出ていれば／なければ」は式 {entered: {owner: you}}（既存実装、そのまま数が返る。other: true で自分自身を除く）で数え、cmp で条件化する。
- 書き方: 条件付き static（第88弾）や trigger の if に {cmp: [{entered: {owner: you}}, "<", 2]} 等（count: で包まない）。
- 試験カード R098。tests/test_vocab_pilot135.py 2件（parse／entered カウンタで deny が解ける実挙動）。
- 待機11枚（entered_this_turn_condition のみが gap のもの）。

## 第136弾: choose_a_race（選んだ種族の付与・参照）— エンジン拡張あり（2026-11-06）
「種族をひとつ選ぶ」choose_race（既存）の使い分け。
- 選んだ種族のクリーチャーへの効果: filter: {races: {race: <変数名>}}（既存先例 dm09-028 等）。
- 選んだ種族そのものを追加する効果: mod: {add_races: [{race: <変数名>}]}。add_races の式エントリを許可し（defs / schema）、op_modify が継続効果の生成時に env で種族名へ展開して固定する（エンジン拡張）。
- proto T168、試験カード R099。tests/test_vocab_pilot136.py 2件（parse／起動→選択→種族追加の実挙動）。
- 待機9枚（choose_a_race のみが gap のもの）。

## 第137弾: god_filter（ゴッドのフィルタ・条件）— 新語彙なし（2026-11-06）
「ゴッド」は種族名として扱う。既存語彙の組み合わせで足りる。
- 対象・検索・数え上げ: filter: {race_has: ゴッド}。「ゴッド以外」は not_race_has: ゴッド（第81弾）。
- 存在条件: exists を条件に使う（ゾーン指定、または破壊したカードは ref 指定で op: if の cond に）。
- 「リンクしているゴッド」は filter: {linked_god: true}（第103弾）を count に使う。
- tests/test_vocab_pilot137.py 2件（正常 parse／検証）
- 待機9枚（god_filter のみが gap のもの）。

## 第138弾: filter_or_race_or_type（種族またはタイプの選択）— 新語彙なし（2026-11-06）
「ゴッドまたは呪文」「ナイト呪文または〜呪文」のような OR 条件の対象指定は filter の any_of で表す。
- 書き方: filter: {any_of: [{race_has: ゴッド}, {types: [spell]}]}（第93弾 soul の any_of と同形）。同じ区分の AND は通常キー併記。
- tests/test_vocab_pilot138.py 2件（正常 parse／検証）
- 待機5枚（filter_or_race_or_type のみが gap のもの）。

## 第139弾: mach_fighter_grant（マッハファイターの付与）— 新語彙なし（2026-11-06）
「マッハファイターを与える」は第58弾の展開形（allow attack_creature、other: {tapped: false}）を modify / static で付与する。
- 一時的付与: trigger の effect で modify（select は対象、mod: {allow: [{action: attack_creature, other: {tapped: false}}]}、duration: end_of_turn）。
- 常在付与: static の affects（対象範囲）+ 同じ allow を mod に置く。
- tests/test_vocab_pilot139.py 2件（正常 parse／検証）
- 待機6枚（mach_fighter_grant のみが gap のもの）。

## 第140弾: same_name_as_chosen_card（選んだカードと同じ名前）— エンジン拡張あり（2026-11-06）
「そのクリーチャーと同じ名前のクリーチャーをすべて〜」は新式 name_of で表す。
- 新式: {name_of: {ref: <束縛名>}}（engine/selectors.py の eval_expr に追加。参照カードのカード名を返す。複数参照なら先頭）。フィルタでは filter: {name: {name_of: {ref: X}}} と書き、candidates が選択時に名前へ解決する。
- proto T169。tests/test_vocab_pilot140.py 2件（parse／candidates の同名照合の実挙動）。
- 待機5枚（same_name_as_chosen_card のみが gap のもの）。

## 第141弾: power_doubling（パワーを2倍にする）— エンジン拡張あり（2026-11-06）
新 mod: {double_power: true} を実装した。
- op_modify が継続効果の生成時に対象ごとの現在パワーを控え（ce["double_power"]）、chars がそれを加算として適用する。範囲固定（110.2e）の効果のみ対象で、生成後に加わった対象には及ばない。
- defs MOD_KEYS / 検証、schema に追加。proto T170、試験カード R101。tests/test_vocab_pilot141.py 2件（parse／起動でパワー3000→6000の実挙動）。
- 待機5枚（power_doubling のみが gap のもの）。

## 第142弾: draw_event_trigger（引いた時の誘発と枚数条件）— エンジン拡張あり（2026-11-06）
「相手がカードを引いた時」は既存の when: {event: draw, player: opp}。
- 新式: {drew: {owner: opp}}（このターンそのプレイヤーが引いた枚数。engine/events.py の draw 適用で turn_counters を数え、eval_expr で参照）。「そのターン1枚目のドローでなければ」は trigger の if: {cmp: [{drew: {owner: opp}}, ">=", 2]}（当該ドローは適用済みのため数に含まれる）。
- 試験カード R102。tests/test_vocab_pilot142.py 2件（parse／drew カウンタで deny が解ける実挙動＋実際のドローで数える確認）。
- 待機5枚（draw_event_trigger のみが gap のもの）。

## 第143弾: leave_stay（離れるかわりにとどまる）— 新語彙なし（2026-11-06）
「バトルゾーンを離れる時、かわりにとどまる」は mod: {no_leave: true}（第49弾）。
- 条件付きは条件付き static（第88弾）の if と併記。例外は辞書形: {except_destroy: true}（破壊以外）、{except_battle: true}（バトル敗北以外）、{by_opp: true}（相手の効果では離れない）。
- tests/test_vocab_pilot143.py 2件（正常 parse／検証）
- 待機6枚（leave_stay のみが gap のもの）。

## 第144弾: total_power_selection（パワーの合計制限つき選択）— エンジン拡張あり（2026-11-08）
「相手のクリーチャーを、パワーの合計がN以下になるように好きな数選び、破壊する」に対応。第38・39弾の total_cost_le/ge の選択機構をパワー軸へ一般化した。
- 新セレクタ: `total_power_le` / `total_power_ge`（式）。変更は3か所: defs.py（SELECTOR_KEYS＋selector の式検証）、schema.py（selector の properties）、engine/selectors.py（合計制限モードを軸ごとの (特性キー, 上限, 下限) のリストに共通化し、値の取得を chars の cost／power で切り替える方式 (a) を採用）。パワーは chars(x)["power"]＝現在パワー（常在型の修整込み）で合計する。
- 枚数上限（第39弾の count 併記）は軸に依存しないためそのまま使える。上限が式の形（`{power_of: <変数>}`）や「より少なく」（`{sum: [{power_of: <変数>}, -1]}`）も既存の式で書ける。破壊数連動は destroy の as＋repeat、モード選択・条件分岐は既存 op で対応する（設計ノート §1）。
- proto T171（合計6000以下）／T172（2体まで・合計10000以下）。tests/test_vocab_pilot144.py 4件（合計以下で予算外の候補が外れる／0枚で止められる／常在型 +1000 の修整が現在パワーに反映され予算判定が変わる／count 上限）＋tests/test_vocab_pilot144_cards.py（代表2枚: 地獄万力、プラスワン・フレーム）。
- 待機29枚（total_power_selection 単独20件＋total_power_selection_limit 単独9件、2026-11-08 実測）。再変換は別ラウンドで実施する。

## 第145弾: barabaraety＋distinct_cost_count（異なるコストの種類数）— エンジン拡張あり（2026-11-08）
「コストが異なる自分のエレメントが3つ以上あれば、この能力を与える」（バラバラエティ）に対応する。
- 新式: `{distinct_cost_count: <セレクタ>}`（対象カード群にあるコストの種類数。civ_count のコスト版）。エレメントは `zone: [bz, mana]`、自分のクリーチャーは `zone: bz`＋types フィルタ、墓地は `zone: graveyard`。数えるコストは chars の cost（印刷コスト。コスト軽減などの支払うコストの増減は cost を変えない）。追加箇所: engine/selectors.py（eval_expr／count_of）、defs.py（expr()／count_spec()）、schema.py（expr の properties）。
- バラエティ・ブレイカー用に breaks dict へ `base`（既定1）を追加。`{distinct_cost_count: ..., base: 0}` でブレイク数がちょうど種類数になる（defs.py の mod 検証＋engine/core.py の評価。既存の `{count}`／`{civ_count}` 形式は base 省略で従来どおり）。
- 評価の再入ガード: 数える対象に発生源自身が含まれるのがこのファミリーの常形で、素朴に chars を呼ぶと自身の常在条件・ブレイク数の評価から無限再帰する（candidates 列挙中の filter_match 経由でも再入する）。評価中（`_distinct_costing`）のカードは定義（印刷）特性・コストで見る（filter_match の base 条件に `_distinct_costing` を追加）。civ_count の同型条件は対象が自分を含まない形（例: 相手のバトルゾーン）でのみ使われてきたため露見しなかった既存の潜在制限で、本弾では civ_count 側には触っていない。
- proto T173（常在＋誘発の if）／T174（バラエティ・ブレイカー）／T175（G・ゼロの free_if）／T176（「1体につき1枚引く」の draw count）、試験カード R103。tests/test_vocab_pilot145.py 6件（parse／エレメントの種類数で deny が切り替わる・重複を数えない・自身も数える／裏向きマナも数える／軽減が付いても印刷コストで数える／base: 0 でブレイク数がちょうど種類数／ブレイカー2体で相互再帰しない）＋tests/test_vocab_pilot145_cards.py（代表1枚: 魔誕哀樹シンバーロ）。
- 待機26枚（barabaraety 単独17＋distinct_cost_count 単独9）。複合2件のうち dm26sd1-t004 は no_leave（第143弾）と合わせて解消見込み、dm25ex3-td07 は choose_number が残る。再変換は別ラウンドで実施する。「異なるコストの選択」（dm24ex3-rp4005／dmrp19-s03）は選択時の制約が別途必要なため本弾の範囲外。

## 第146弾: shield_break_replacement（ブレイクの自己置換）— エンジン拡張あり（2026-11-08）
公式FAQどおり自己置換効果として実装した（ユーザー決定 2026-11-08）。語彙は既存の kind: replace＋when: {event: break} に統一し、エンジン側は h_break に諮問段を新設した。
- 諮問段: h_break の phase 0（chosen 確定後）から phase 1（S・トリガー宣言）の間に、シールド1つずつ置換を諮る（combat.py の h_break から events.py の `_break_consult`／`_break_candidates` を呼ぶ。進捗は BreakTask の brk_* に持たせ、instead の effect タスクを break タスクの上に push して再入する）。諮問順はターン・プレイヤー→非ターン・プレイヤー（609.9a）。1つのシールドに適用できる置換は1つだけ（適用済みは再諮問しない＝自己置換は連鎖しない。FAQ qa_old/36516）。擬似ブレイク（効果でシールドを手札に加える。113.6、fire_break: False）は諮問の対象外。効果ブレイク（op break、in_effect のものを含む）も同じ段を通る。
- 発生源の走査は _replacement と同じ規則（そのプレイヤーの bz_tops＋シールドゾーン。バトルゾーン外は zone 宣言が実ゾーンと一致するものだけ）で、シールドゾーンの発生源は表向きのものだけを候補にする。被ブレイク側で発生源がバトルゾーンと表向きシールドの両方にありうるカード（雷光の聖騎士）は、同じ replace 能力を zone 宣言違いで2つ書く形を想定（実ゾーンに合う方だけが拾われる）。
- 書き方: ブレイク側は `when: {event: break, subject: self}`、被ブレイク側は `when: {event: break, player: you}`（ブレイクしたクリーチャーの条件は subject に {owner: opp, filter} を重ねる）。条件は replace の if、獲得型は static＋mod の gain で書ける。
- 置換されたシールドは「ブレイクされた」ことにならない（QA 33466）: 諮問後に chosen から外し、S・トリガー宣言・S・バック pool・最終 move のすべてから除外する。実際にブレイクされるシールドが0枚なら break レコード自体を出さない（broke_in も立てない）。**【裁定待ち】**この扱いは「ブレイクする時、かわりに」型（FAQ の裏付けあり）でも「手札に加えるかわりに」型でも同じとする設計の仮定で実装した（設計ノート pilot146 §5-1）。裁定が逆になれば、events.py の `_break_consult` の取り消しの印（brk_cancelled）と combat.py のレコード抑制を切り替える。
- 割り込み型（ガイアール・ベイビー）は新キー `continue: true`（ability のキー。break の replace だけに書け、defs.py で検証する）: instead の後もそのシールドのブレイクが続く。ブレイク枚数は諮問前に確定済みで、割り込みで出したクリーチャーの能力で増えることはない（qa_old/36514）。**【裁定待ち】**ミラクルスター（dmr21-s06）を「ブレイクした」として数えるか（設計ノート pilot146 §5-2）は、continue の有無だけで両案に対応できる形を維持し、決着まで再変換の対象から外す。
- 諮問 env の変数 `shield`（束のトップ＋under の ref 列）と `{ref: event.shield}`（トップ）でブレイクされるシールドを参照できる（selectors.py の ref 解決に event.shield を追加）。コスト参照は `cost_of: {ref: shield}`（束なら最大コスト＝「束の中のカード1枚より小さい」の存在読み。qa_old/36515）。束はトップへの move で under ごと動く（109.2b）。
- proto T177（B型: W・ブレイカー＋行き先変更）／T178（A型: continue: true＋コスト参照つきで手札から出す）／T179（C型: 手札を捨てて取り消し）、試験カード R104（デス型: シールドを墓地へ＋ブレイクしたクリーチャーを破壊）。tests/test_vocab_pilot146.py 13件（parse／continue の検証／B型の全置換・束ごと墓地／A型の割り込み継続・束の最大コスト参照／C型の decline・accept・ライダー／部分置換で count 1／擬似ブレイクで諮問なし／連鎖しない／効果ブレイクでも諮問）＋tests/test_vocab_pilot146_cards.py（代表2枚: ボルメテウス・ホワイト・ドラゴン GS、ガイアール・ベイビー）。
- 待機12枚（shield_break_replacement を gaps に含む。単独11＋複合1）。うち dmx15-s04 は shield_go_condition が残るため対象外、dmr21-s06 は裁定待ちのため対象外。再変換は別ラウンドで実施する。P・サファイア（dmx15-v01）用の filter `s_trigger` は本弾に含めていない（再変換時に必要なら小追加する）。

## 第147弾: distinct_cost_selection（コストが異なる選択）— エンジン拡張あり（2026-11-08）
「コストが異なるクリーチャーを好きな数」の選択時制約を、セレクタの新キー2つで表す。土台は第38弾の積み上げ選択（total_cost_le/ge）と、ハイパーエナジー支払い（turn.py）の「使用済みコストを候補から外す」述語。解釈はユーザー決定（2026-11-08）で確定済み。
- `distinct_from: <セレクタ>`（型1: 参照集合と重ならない）: 候補確定（candidates＋be_chosen 絞り込み）の直後に、参照集合のコストと重なる候補を外す前置フィルタ。評価は選択開始時に1回だけ＝「出す前の場」が比較対象で、選んだカードが出た後に場のコストが増えても残りの選択には影響しない。選んだカード同士のコスト重複は可。defs.py の selector() で再帰検証する。
- `distinct_costs: true`（型2: 選んだ同士が互いに異なる）: 積み上げ分岐の発動条件に加え、`_fits` に「候補のコストが選択済み集合に無いこと」の述語を追加（total 系の limits が空でも動く）。「好きな数」（count: any／up_to）は既存の下限なし＝常に止められる。候補がすべて重複コストになったら rest が空になって自動で終わる。
- 型3（全コスト網羅）: `distinct_costs` ＋ count に `{distinct_cost_count: ...}` の式を組み合わせる（dmrp03-007。当てはまるものをすべて＝コストの種類ごとに1体ずつ、同コストが複数あれば1つを選ぶ。公式QA 31610）。can_stop は distinct の時だけ必要数（need＝count の評価値）に達するまで止められない規則を追加し、どう選んでも届かない場合は打ち切る。**既存の total 系の can_stop の意味は変えていない**。なお候補が1枚だけになった段は ask の一意自動決定で選ばれる（決定としては現れない）。
- distinct 系のキーは count の併記が必須（defs.py で検証）。count: all 単独は「選んだことにならない」ため不可、count: all＋up_to: true（any 相当）は可。distinct_costs は true のみ。schema.py の selector properties にも2キーを追加し card.schema.json を再生成した。
- 登場は op move の既存の逐次処理（409.1e）に乗り、選んだ順＝出てくる順。「出た時」は全員出終わるまで待機する（公式QA 31611）ことを実挙動テストで裏取りした（最初に出た R105 の出た時能力の選択肢に、最後に出たカードが含まれる）。
- コストの取り方は chars の cost（印刷コスト。ハイパーエナジー支払いの先例に一致）。
- **範囲外（親判断で確定）**: 進化クリーチャーの重ね出しは本弾では扱わない（設計ノート §5-1 の (a)）。型2の dm26ex1-017・型3の dmrp03-007 で進化が絡む分は、再変換フェーズで gap を細分して rejects に戻す。dm26sd1-u001 清永（distinct_cost_condition、条件側）は本弾に含めない（§5-2）。
- proto T180（型2: 出た時、墓地からコストが異なるクリーチャーを好きな数手札に戻す）／T181（型1: 攻撃時、上から3枚から自分のどのクリーチャーともコストが異なるものを好きな数出す）／T182（型3: ターン終わりに墓地の異なるコスト8種をすべて出す）、試験カード R105（出た時観測獣: 型3の待機の観測用）。tests/test_vocab_pilot147.py 7件（parse／検証／型2の選択と自動終了・0枚停止／型1の前置フィルタと同士重複可／型3の全コスト登場・逐次登場と待機・7種で不発）＋tests/test_vocab_pilot147_cards.py（代表3枚: 無龍 <デッゾ.Star>、魔誕の邪将クエイクス、ラトリエ・ロブション）。
- 待機8枚（distinct_cost_selection を gaps に含む。単独7＋複合1）。うち dm24ex3-rp2010 は dynamic_name_reference_filter が残るため、選択が解けても登録には至らない（gap が1つに減る見込み）。再変換は別ラウンドで実施する。

## 第148弾: shield_stack / flip_up / shield_flip（シールドの重ね置きと向き変更）— エンジン拡張あり（2026-11-08）
「シールド１つの上に表向きにして置く」と「シールドゾーンにあるカードの表向き／裏向き」を、move の拡張・新セレクタ・新 op で表す。設計は判断1（束の中の表向きも数える。ユーザー決定 2026-11-08）を反映し、判断2〜4は範囲を絞った（下記「範囲外」）。
- move の新キー `stack_on: <セレクタ>`（to: shield の時だけ。対象セレクタの count は1だけ。defs で検証）: 移動したカードが対象の束の新しいトップになる。put_under（下に入れる・イベントなし）でも shield_plus（下に差すだけ）でも表せない「上に・表向きで・誘発が発火する形」のための拡張で、move レコード経由なので「シールドゾーンに置かれた時」「表向きで置かれた時」が正しく発火する。対象の束は効果の使用者が選ぶ（セレクタの owner は候補の絞り込み。相手のシールドに重ねる時は owner: opp）。重ねる先のシールドが無い場合は置けないので移動自体を行わない。イベント適用（events.py の _apply_one）で束を合体する: 順序は [新しいトップ, その下のカード, 旧トップ, 旧トップの下]、旧トップの face_up はそのまま残る。対象の束が消えていたら通常の新しいシールドとして置く。イベント側のキーは shield_stack（進化の stack_on とは分ける。あちらは _record_for が stacked として照合するため）。
- セレクタ新キー `bundle_of`: 値 `"self"` | 変数名 | セレクタ。解決した束（トップ）ごとに [トップ]＋その下すべてを候補にする。**束の中の（覆われている）表向きカードも「シールドゾーンにある表向きのカード」の数え・選択に含める**（ユーザー決定）ため、表向きカードの数え・選択は `{bundle_of: {zone: shield, ...}, filter: {face_up: true}}` の形を変換の標準とする。素の zone: shield はトップだけを見る（シールドの枚数を数える用途ではこちらが正しい）。defs は再帰検証し、schema にも追加した（card.schema.json 再生成済み）。
- op `flip_up`（新設）＋ `flip_down` のシールド拡張: シールドゾーンでは face_up の付け外し、マナゾーンでは face_down の付け外し（flip_up のマナ側はエターナル・Κ 等の「裏向きのマナを表向きにする」用）。どちらもイベントを作らない直操作で、「置かれた時」は誘発しない（ギャラクシールドのターン開始時召喚は状態条件 if: {face_up: true} で拾う）。表向き化は note_public で公開を記録する。両方向の選択（「表向きまたは裏向きにしてもよい」）は既存の modal で書く。
- 裁キ型の変換型: 「唱えた後、墓地に置くかわりにシールドの上に置く」は kind: replace（zone: hold、when: {event: move, subject: self, to: graveyard, reason: resolve}）の instead に stack_on つき move を書く（先例 dmc64-011 系）。自分のシールドが無い場合は重ねられないのでカードは保留ゾーンに残り、ターン終了時に通常どおり墓地に置かれる（512.1）。
- ブレイク処理は無変更: 束はトップへの move で under ごと動き、束のカード全員が S・トリガー宣言できる（既存実装。本弾のテストで重ね置きで作った束でも確認した）。
- proto T183（裁キ型呪文）／T184（B型: 山札上を裏向き新シールド＋別の山札上を表向きでその上に。D型: 相手のクリーチャーを表向きで持ち主のシールドへ）／T185（束のカードすべてを表向き／表向きのカードを裏向き）、試験カード R106（「シールドゾーンに置かれた時」の観測獣。反転で誘発しないことの確認用）／R107（modal で束の中のカードを両方向に返す呪文。シンクロ・ルピア呪文面の型）。tests/test_vocab_pilot148.py 11件（parse／stack_on の検証／B型の束形成と置かれた時×2／束のブレイクで両カードが S・トリガー宣言可・ブレイクは1回として数える／D型の相手シールド重ねと置かれたカード自身の誘発／覆われた表向きが bundle_of で数えられる／反転で誘発せず次の自分のターン開始に召喚／modal の両方向反転／裁キ型の置換とシールド無しでの墓地行き／進化クリーチャーの下の保持）＋tests/test_vocab_pilot148_cards.py 2件（代表4枚: 天門ノ裁キ、煌龍 サッヴァーク、カイザー・ルピア、シンクロ・ルピア）。
- 待機36枚（shield_stack 28／flip_up 7／shield_flip 3。dmex19-m18・promoy17-044 は stack と flip の両方を含む）。再変換しても残るもの: dmex07-m02 は gr_summon、dm24sp2-001 は deny_cast_below_facedown_mana_count、dmx12b-035 は unblocked_trigger が残る。再変換は別ラウンドで実施する（reopen shield_stack flip_up shield_flip）。
- **範囲外（ユーザー承認済みの切り分け）**: dmex19-m18 のブレイカー部分（「各ブレイクの前に」の割り込みは h_break への新フックが要る。本弾はその shield_flip 部分のみ対象）、dm25ex3-rp4001 の「シールド1つにつき」の繰り返し、dmbd07-b-001 の「重ねた表向きのカードを使う」は扱わない（gap の細分は再変換ラウンドで行う）。
- 既存の変換済みカードへの影響: 「表向きのシールド」を素のセレクタ（zone: shield＋filter: face_up）で数える／選ぶ既存カード（ℵHEAVEN dm24ex2-025 の勝利条件、シールド・ゴー条件の dmr10 系、dm26ex2-013/024、dmrp16-s01、dmex08-093、dmex14-021 等）はトップだけを見ている。束の中に表向きカードがある局面ではユーザー決定と食い違うため、関係するカードは今後のラウンドで bundle_of 形への書き換えを検討する（本弾では converted.yaml は変更しない）。

## 第149弾: d_d_d_rider（「D・D・D」によって出た時／唱えた時の照合）— エンジン拡張あり（2026-11-09）
「D・D・D」（自分のクリーチャーが攻撃する時、このカードを固有コストで手札／マナから実行する代替プレイ）の経由で出たこと・唱えたことを、play 本体の印 `via` で照合する。設計ノート pilot149-d-d-d-rider-design どおり。
- op `play_self` に任意キー `via` を追加（タスクに `via` が写り、play フローがイベントに `via` として伝播し、誘発収集レコードまで届く）。defs の `VIAS` に `d_d_d` を追加し、`play_self.via` の値域を VIAS で検証する。印は既存の `vivid` 印と同格の横並びの値で、precedent は g_link の挿入タスクで使う `via`（リンク由来の入場の区別。タスク・イベントの素の文字列キー）がある。エンジンは D・D・D の効果文を一切解釈せず、印の生成（play_self の宣言）・伝播（play フロー）・照合（when／cond）の3点だけを担う。
- クリーチャー型ライダー: 誘発の `when` に `via: d_d_d` を追加で書く（既存の alt／vivid と同じく when の文字列キーとして照合する。当該カードに限る追加条件で、形状は `unpaid` と平行）。**通常召喚・キリフダッシュ等では発火しない**（via は play_self 実行時のイベントにだけ付く）。
- 呪文型ライダー: 条件式に `ddd_paid`（bool）を追加し、効果リストの先頭に `{op: if, cond: {ddd_paid: true}, then: [追加処理]}` を書く（常設の alt_paid／vivid_paid と同じ作り。env には play タスクの via が入る場合だけ立ち、イベント経由でも拾える）。登録済みカードに先例がある形で、S・トリガーで唱えた場合は play_self を経由しないため `ddd_paid` は立たない。「そうしたら」型の接続は、唱えた本体が成功した時に続けて解決する一続きの効果として then の中に書く。根拠は公式QA Q31668（選択肢は置換効果のため、無効化されたカードはブレイクされたことにならない——本弾の論点は「D・D・Dで唱えたか」の状態照合であり、反例となる裁定は確認できなかった。第146弾の裁定待ち2件とは別件）。
- モーダルの個数差（通常2つ／D・D・Dなら3つ等）は、modal を if の then／else に複製して count（と repeat の有無）だけ変えて書く。エンジン側に特例は作らない。
- マナゾーンからの declare は `zone: mana` の declare をもう1つ書く（既存の多ゾーン宣言の型。対象カードは攻撃誘発の提示が2回になる構造で、変換時の手書き確認事項とする）。
- **変換ルール（親判断 2026-11-09）: `via: d_d_d` を付けるのはライダー（「D・D・Dによって出た時／唱えたなら」の効果）を持つ11枚の declare だけ**。ライダーを持たない D・D・D カードには付けない（不発火の保証は T186 のキリフダッシュ対照テストで担保し、誤爆の心配は無いが、変換の手間と「via を見たらライダーがある」という可読性の規約を優先する）。タマシード／フィールドの play は `t['via']` があればそちらを優先し、無ければ従来どおり `generate` とする。
- **潜在バグの根治（同梱）**: 誘発収集レコード（events.py の `_apply_one` が作る out）には via だけが写り、**alt／vivid の印が写っていなかった**。そのため `when: {vivid: true}` の move 誘発（登録済みカードの実在の形）と、誘発の `if: {alt_paid: true}` は実際には発火しない状態だった。本弾で alt／vivid も同じ経路で収集レコードに伝播させた。第54弾の既存テスト `test_trigger_fires_on_vivid_summon` は「入場後に手札が1枚になるまで進める」非判別な形でこのバグを素通ししていたため、「入場直後の Decision 提示時点の手札」で見る判別形に補強した（修正を外すと落ちることを確認済み）。
- proto T186（declare＋ライダー誘発。キリフダッシュ execute 併記で不発火も固定）／T187（呪文の ddd_paid 分岐）／T188（declare 2枚＋モーダル3/2の書き分け）、試験カード R108（vivid の move 誘発と alt_paid の if をタップで観測する獣。ドローのような代替説明が利かない効果で観測する）。tests/test_vocab_pilot149.py 16件（parse／検証エラー3件／ライダー発火・不発火（通常召喚・キリフダッシュ）／呪文の追加処理あり・なし・S・トリガー不発／モーダル2⇔3と全モード1回ずつ／マナゾーンからの declare／vivid 伝播の判別2件／alt 伝播の判別2件）＋tests/test_vocab_pilot149_cards.py 11件（対象11枚の手書き変換。単独7枚は変換形まで、複合4枚は parse と残 unsupported の内訳まで）。
- schema は再生成済み（when.via の列挙に d_d_d、play_self に via、条件式に ddd_paid）。
- 待機11枚（単独7: dm25ex3-021, dm25ex3-026, dm25ex3-038, dm25ex3-rp3011, dm25ex3-rp3s08, dm25ex3-rp4007, dm25rp4-019／複合4: dm25ex3-010, dm25ex3-rp4005, dm25ex3-rp4s05, dm25rp4-012）。再変換は別ラウンドで実施する（reopen d_d_d_rider）。
- **範囲外（親判断 2026-11-09）**: dm25ex3-010 の cip_trigger_double（出た時誘発の2度トリガー）は実装しない。dm25ex3-rp4s05 の「出ることによって起こる効果やルールはすべて無視する」は実装しない（ライダー本体の「マナから12体まで出す」だけを書く。無視条項は手書き変換テストでは仮の need 名 `enter_effects_ignored` で残し、命名は再変換時に確定する）。dm25rp4-012 のライダーは declare に via だけ付けて unsupported に d_d_d_rider を残す（シャッフル→公開→無料実行／手札かマナの複合の精査は再変換ラウンドで行う）。

## 第150弾: become_evolution_base_trigger（進化元になる時）— エンジン拡張あり（2026-11-09）
「このクリーチャーが進化元になる時」（NEOクリーチャーの併記誘発）と「シンカパワー：このタマシードが進化する時」を、進化の重ね適用時に出す合成レコードで照合する。設計ノート pilot150-evo-base-design どおり。
- 進化の重ね適用時（events.py の `_apply_one` の stack_on 分岐）、h_play が立てた進化印（`ev["evolution"]`、t["evo"] がある時だけ）がある場合に限り、進化元を subject・出たクリーチャーの適用後 ref を top とする合成レコード `{"ev": "evolve_base", "subject", "top", "controller"}` を元ごとに1つ出す（進化V等の複数元は元ごとに発火する）。defs の EVENTS に `evolve_base` を追加（schema は再生成のみ）。
- 誘発収集（`_collect_triggers`）では、evolve_base レコードの subject を発生源に加える（重ねられた側は bz_tops から外れるため、レコードを出すだけでは進化元の能力を走査できない。離れたカードの lki 追加と同じ形）。他者の進化元化を見る文面は対象に無いので、汎用の走査には広げない。
- 変換の型: `- kind: trigger / when: {event: evolve_base, subject: self} / effect: [...]`。型N（NEO併記）は2能力に分ける: 出た時側は既存の `{event: move, subject: self, to: bz, stacked: true}`、元になる時側は evolve_base。効果が同じでも2つ並べる。
- 効果の宛先の注意: 型N-b／S-a（「この進化したクリーチャー／それに与える」）は、元になる時側では宛先を `{ref: event.top}`（selectors の event.* 参照に第146弾の event.shield と並べて追加）に書き換える（出た時側は `{ref: self}` のまま）。**同じ文面でも2能力で宛先が違う**。
- **前提修正: when の `stacked` 照合を有効化**（第28弾で「照合可能」とされたが `_match_when` に分岐が無く、未知キーとして素通りしていた。あわせて収集レコードへの stacked 伝播も無かった）。これで「進化して出た時」は重ねて出た時だけ発火する。converted の stacked 使用52箇所のうち、変わるのは重ねずに出られるカード（NEO等）が通常召喚で誘発しなくなる＝文面どおりになる方向のみ。第28弾の T087 テストは重ねて出す形なので従来どおり発火する。
- **発火しない経路（親判断 2026-11-09）**: 無月の門（summon_on）は進化ではないので発火しない（ev に進化印を付けないことで切り分ける）。侵略はイベントを経ず `_stack` を直接呼ぶため自動的に対象外（進化ではないので正しい）。スター進化の離脱・G-NEO の離脱置換など重ね以外の処理には触らない。進化元が既に重なっていた側では、その時点のトップだけが subject になる（下のカードは新たに元になるわけではない）。
- proto T189（シンカパワー試験タマシード: evolve_base で event.top にマッハファイター相当の許可を与える）／T190（併記型NEO試験獣: stacked 側と evolve_base 側の両方でドロー）／T191（進化試験獣: クリーチャー／タマシード両対応の受け手）。設計ノートは T188〜T190 の予定だったが、第149弾が T188（決断試験呪文）まで使ったため +1 ずらした。tests/test_vocab_pilot150.py 8件（parse／シンカパワーの付与先がトップであること／NEO通常召喚で両側とも不発火（判別）／NEO重ね出しで stacked 発火／NEOが元になって evolve_base 発火／進化Vで元ごとに発火／無月の門で不発火／侵略で不発火）＋tests/test_vocab_pilot150_cards.py 4件（dmrp22-025 レヴィヤの地版、dm25rp2-058 ～淡き舵取りの唄～、dm25rp4-077 スマッシュ・ホーンの地版、dm25rp3-044 轟速 ジャ・ターボ3 の手変換）。
- schema は再生成済み（イベント列挙に evolve_base）。
- 待機31枚（型N 16／型S 15。うち dmrp22-021 は must_attack_next_turn が残る）。再変換は別ラウンドで実施する（reopen become_evolution_base_trigger、登録見込み30枚）。

## 第151弾: d2_field（D2フィールドの型印・一意性・Dスイッチ）— エンジン拡張あり（2026-11-09）
D2フィールドの本体は既存の型 `field` で実行・常在型・誘発が既に書ける（第25弾）。本弾の新規は3点だけ: 型印 `d2_field` の併記と一意性フックのプール分離、Dスイッチ（旗＋op＋出し分け）、禁止の受け皿（deny: [d_switch] の照合点。deny: [generate] は既存）。設計ノート pilot151-d2-field-design と公式裏取り faq-check-d2-20261109 どおり。
- D2フィールドは types に `["field", "d2_field"]` と書く（defs の CARD_TYPES に型印 `d2_field` を追加。is_permanent は "field" で従来どおり）。D2だけを指すフィルタは `{types: [d2_field]}`、存在条件は exists＋同フィルタ（いずれも既存語彙。selectors の変更なし）。`{types: [field]}` では D2 も数えられる（併記の帰結）。変換指示（tools/convert_cards.py）にも併記を明記した。
- 一意性: バトルゾーンの D2フィールドは両プレイヤー合わせて1つだけ。新しい D2フィールドが出たら、他の D2フィールドはすべて破壊される（events の適用後フック）。**プール分離（公式裏取りで確定）**: 総合ルール 703.4l は出現側・対象側とも「D2フィールド」に限定され、通常フィールドには一意性の規定が無い（308）。行き先は destroy（701.6「バトルゾーンから墓地に置くことは破壊」＋109.1 最新表記＋公式 QA 47896 で破壊置換が適用できた事例）。フックは出現イベントごとに1回だけ適用される形（move の適用時にだけ走る）で、置換で生き残った D2 は次の新しい D2 が出るまで残る（QA 47896）。通常フィールド同士は第25弾の挙動（T069／T070）を温存する（通常フィールド同士の一意性も総合ルールに規定は無く、温存は設計側の選択）。
- Dスイッチの型: kind: trigger に `dswitch: true` を付け、効果の先頭に may＋`{op: dswitch}` を置く。使うと may の body が走って旗が立ち、断れば反転せず使用済みにもならない（次の同じタイミングで再提示される）。使用済みは Card の `dswitched` 旗で管理し、_raw_move（ゾーン移動）でリセットされる＝新しいオブジェクトとして出直したら再び使える（「ゲーム中で一度」はオブジェクト単位。親判断）。出し分けは abilities() の印照合に追加: `dswitch: true` の能力は「dswitched でなく、かつ permits(発生源, "d_switch")」の時だけ有効（kind 照合の後ろで permits を見るので chars 計算とは再帰しない）。op `dswitch` は self 専用の直操作でイベントは作らない（flip_up／flip_down と同じ性格）。defs は ABILITY_KEYS に `dswitch` を追加し、trigger に true でだけ書けるよう検証する。permissions.yaml に行為 `d_switch`（default: true）を追加。
- 禁止の受け皿: 「Dスイッチを使えず」は affects／modify＋`deny: [d_switch]`（対象フィルタは types: [d2_field]）、「D2フィールドを展開できない」は affects／modify＋`deny: [generate]`（第33弾の deny cast と同型）。**「展開できない」の範囲はメインの generate まで**（親判断。S・トリガー等の play_free 経路は止めない）。文面が「バトルゾーンに出せない」とより広い dmex08-204 ワチャゴナは本弾の範囲外（再変換では条項だけ unsupported に細分する）。
- proto T192（Dスイッチ試験フィールド: 常在型＋ターンのはじめの Dスイッチでドロー）／T193（D2試験フィールド: 出た時ドロー）／T194（D2言及試験クリーチャー: exists 条件）／T195（D2 S・トリガー試験フィールド。設計ノートの T192〜T194 に S・トリガー確認用を1枚追加）、試験カード R109（自分のターンの終わり型の Dスイッチ観測フィールド）。tests/test_vocab_pilot151.py 13件（parse／dswitch キーの検証2件／一意性（両プレイヤー・プール分離の共存・出す順序2通り）／filter の併記帰結／Dスイッチの断る→再提示→使う→提示されない／使用ターンのドロー数／ターン終わり型／墓地→手札→出直しで再使用可／deny 2種と期限切れ後の復帰／S・トリガーで無料展開／言及カードの条件3場面／クリーチャー選択と攻撃の対象外）＋tests/test_vocab_pilot151_cards.py 7件（dmr21-036、dmr21-047、dm23ex3-042、dmd35-011、dmr21-035、dmr23-040、dmex08-204 の手変換）。
- schema は再生成済み（型の列挙に d2_field、能力キーに dswitch、行為に d_switch、op に dswitch）。
- 待機68枚（本体46／言及22。うち dm23ex2-034 は対象外の複合、dm25ex2-057 は超次元、dmex17-cho38 は文明喪失、dm26ex3-053 は二度トリガーが残る）。再変換は別ラウンドで実施する（reopen d2_field d_switch、登録見込み約49〜56枚）。
- **範囲外・残件（親判断／精査の結果）**: dm23ex3-014 の継続的アンタップ禁止と dmex08-140（ジャンケン）は扱わない。dm23ex3-042 の Dスイッチ効果「このターン破壊された自分のクリーチャーをすべて墓地から手札に戻す」は、「このターン破壊された」カードを墓地から選ぶセレクタが現行語彙に無いため、本弾では unsupported（need: destroyed_this_turn_select）に細分して残す（カードテストでは常在型と型印だけを固定）。dmex08-204 の禁止条項も同様に unsupported（need: d2_field_enter_ban_all_paths）。dmd35-011 の侵略ZERO は再変換ラウンドで精査する（相手がコストを支払わずに出していたかの追跡が要る可能性）。

## 第153弾: kizuna_plus（キズナプラス）— エンジン拡張あり（小）（2026-11-09）
キズナプラスはキーワード `kizuna_plus` と書く。[P]能力の受け皿（kind: partner）と「下のカード」の選択・移動・数えは既存（第44弾）。本弾の新規は op `use_partner` の引数拡張とキーワード追加だけ。設計ノート pilot153-kizuna-plus-design と公式裏取り faq-check-kizuna-20261109 どおり。
- 変換の型: カード側は `keywords: [kizuna_plus]` と、自身の[P]を `kind: partner` の能力として書くだけ（変換指示 tools/convert_cards.py にも明記）。展開形は攻撃時誘発（when: {event: attack, subject: self}、if: 下のカード1枚以上）で、may の body が「下のカード1枚を墓地に置く（under_of＋move、reason: put）→自分の[P]を使う→他のクリーチャー1体の[P]を使う」。
- op `use_partner` に引数を追加: `of: self`（候補を自身の[P]だけに絞る）、`exclude_self: true`（自身を候補から除く）、`pending: true`（選んだ[P]をその場で解決せず待機中の効果として登録する）。引数なしは従来どおり（素のキズナ。第44弾の挙動・テストは不変）。
- **2つの[P]の順序（公式裏取りで確定）**: 文面の列挙順で固定ではない。支払いの時点で2つの[P]はそれぞれ独立した待機効果として確定し（総合ルール 603.3a。本文がキズナプラス自体を例示）、解決順は使う側が好きな順番で選べる（605.1／101.4a）。そのためキーワード展開は use_partner を2回直列に解決せず、両方とも `pending: true` で待機に登録する形にした（order_pending の判断で順序を選ぶ。途中で誘発した他の効果も割り込める）。発生源が解決前に離れても不発にならない（110.5a。待機中の効果は発生源から独立）。選択自体（自分の[P]と、どの他のクリーチャーの[P]か）は支払い時点で確定する。
- **他の[P]持ちがいない場合（公式裏取りで確定）**: 支払いだけ行って自分の[P]だけ使うことができる（101.3／605.2b／606.2）。誘発の if は「下のカード1枚以上」のみで、他の[P]の存在条件は付けない（exclude_self 側は候補なしで何もしない）。逆に、他の[P]持ちがいる場合はその[P]を使うことは必須（文面は「使う」）。
- 誘発の `if` は収集時と解決時の両方で評価される（h_resolve_pending が解決時に再評価する）ことを実施時に確認したので、may の body 側へのガードの重ねは不要だった。
- proto T196（キズナプラス試験獣: NEO進化＋[P]「1ドロー」）／T197（絆試獣・乙: [P]のみ「2ドロー」）。進化元と他の[P]持ちの一部は既存の T001／T124 を流用。tests/test_vocab_pilot153.py 9件（parse と展開形／素のキズナの不変／両[P]が使われて攻撃が続行する／may を断る／下が無いと提示されない／他の[P]なしで自分の[P]だけ／複数候補からの選択と自身の除外／順序選択の判別2件: 相手の[P]の破壊を先に解決して発生源が離れても自分の[P]が解決する・逆順）＋tests/test_vocab_pilot153_cards.py 4件（dmrp03-002、dmrp03-015、dmrp04s-029、dmex06-020 の手変換）。
- schema は再生成済み（キーワード列挙に kizuna_plus、op use_partner に of／exclude_self／pending）。
- 待機19枚（全件単独 gap。同名の別印刷7件がキューにあり通常変換で登録可能になる）。再変換は別ラウンドで実施する（reopen kizuna_plus、登録見込み19枚）。
- **範囲外**: キズナコンプ（kizuna_comp 5件）は本弾に含めない（「好きな数」を繰り返し選ぶ意味論が別途要る。第154弾候補）。dmrp03-008（キズナプラス持ちだが rejects の gaps が空）は reopen の対象にならないので再変換時に個別確認が要る。

## 第154弾: crystal_soul（水晶ソウル）— エンジン拡張あり（小）（2026-11-09）
水晶ソウルN は面の宣言 `crystal_soul: N` と書く（キーワード欄には書かない）。「このカードを召喚／唱える時、自分のマナゾーンにある裏向きのカードのマナの数字はNになる」。設計ノート pilot154-crystal-soul-design どおり。
- 実装は chars の `crystal_soul`（面の宣言を種に、mod {crystal_soul: N} と max で集約。G・リンクの特性統合でも max）を _mana_choices が読み、支払うカードに水晶ソウルがある時だけ裏向きグループの数値（と早期判定の合計）をその値に差し替える。支払いの総和計算は _mana_choices に一元化されているため組み込み先はこの1関数で足りる（実支払い・可否判定・墓地召喚・フシギバース等の支払いを伴う実行はすべて経由する）。**裏向きマナは無色のまま（文明は得ない）**。**上書きは置換であり最大値ではない**（文面「数字はNになる」。proto T202＝マナ数3で判別）。
- 付与は affects {zone: hand, owner: you, filter: {...}} の常在型＋mod {crystal_soul: N}（dm24bd6-001 偽神殺しのツラトゥストラの型: 手札のアンノウンに2、ゼニスに3）。付与は手札にある間だけ効く。
- **代替コスト・バズレンダの追加支払いにも一律に及ぶ**（親判断 2026-11-09: _mana_choices 経由の支払いはすべて対象。水晶ソウルと代替コスト宣言・バズレンダを併せ持つ実カードは存在しないため実務差は無い。併せ持ちが現れた時点で公式裏取りを行う）。**自前と付与で値が競合した場合は max**（親判断。実カードでは付与値が種族ごとに自前値と一致し競合しない）。
- proto T198（水晶ソウル試験獣2: 水・コスト7・ソウル2）／T199（水晶ソウル試験呪文3: コスト6・ソウル3・1ドロー）／T200（水晶付与試験獣: 手札のゼニスに mod でソウル3）／T201（ゼニス試験獣: コスト9・宣言なし）／T202（多マナ試験カード: mana: 3 のバニラ）。tests/test_vocab_pilot154.py 10件（parse／宣言と mod の検証／ソウル2の支払いと対照（判別: 表向きまで上書きされると合計が偶数だけになり払えない）／裏向きだけでは払えない／裏向きは文明を得ない（判別: 数値が届いても文明で弾く）／置換 vs 最大値（判別）／呪文のソウル3／付与の有無と手札限定／宣言なしカードの支払いの不変／実支払いの召喚 e2e）＋tests/test_vocab_pilot154_cards.py 2件（dm23ex3-036 偽りの名 システイス、dm24sp2-008 偽りの名 プラットの手変換）。
- schema は再生成済み（面の項目と mod に crystal_soul）。
- 待機: 単独6枚（再変換で登録見込み）。eternal_kappa の弾と合わせると11枚（kappa のみ複合4枚＋付与の dm24bd6-001）。キューの別印刷15件も通常変換で登録可能になる。再変換は別ラウンドで実施する（reopen crystal_soul）。
- **範囲外**: dmex06-034 の mana_value_boost_multicolor（「マナゾーンで多色カードをタップする時、そのうちの好きな枚数のカードのマナを2にしてもよい」）は形が違う別需要で本弾に含めない。

## 第155弾: link_establish_event（リンクした時）— エンジン拡張あり（小）（2026-11-09）
G・リンクの手順（h_g_link、第16弾）は Card.link の状態変更のみで誘発収集用レコードを出さなかったため、「リンクした時」を受ける先が無かった（ラウンド182の実測: 代替型「出た時の誘発＋能力側 if: link_count>=2」は、誘発条件の評価がリンク手順より前に行われるため発火しない。効果側 if に寄せれば出る側だけは表せるが、リンクされる側の誘発を拾えず近似になる）。本弾の新規は合成イベント `link_established` の追加だけ（第150弾 evolve_base と同型）。
- 変換の型: `kind: trigger, when: {event: link_established, subject: self}`。「カードN枚でリンクした時」は能力の `if: {cmp: [{link_count: self}, ">=", N]}`（link_count 式は既存。収集時点ではリンク成立済みなので正しく判定できる）。変換指示（tools/convert_cards.py）にも明記した。
- 発行点: h_g_link でリンク先を選んで gid を付けた直後（手順の完了時点）に、成立したグループの全員（link_members）を subject とするレコードを ev_task の束で出す。_apply_one は attack_end 等と同じ素通しでレコード化し、置換諮問の対象にはならない（_record_for は move／draw のみ）。リンクを外しただけ・リンク先をパスした場合は成立ではないので出さない。外して付け直した場合は、成立した新しいグループの全員だけが対象（外れたメンバーは含まれない）。
- 誘発収集は既存の仕組みのまま: 発生源は bz_tops＋リンクグループ全員の展開で全メンバーが候補になり、各メンバーの能力は発生源が代表（link_rep）に正規化されるため、subject が代表のレコードに一致して1回だけ拾われる。これにより「リンクされる側（既に場にいたゴッド）」の「リンクした時」も誘発する（判別テストあり）。_collect_triggers への発生源の追加は不要だった（evolve_base では重ねられた側が bz_tops から外れるため必要だったが、リンクのメンバーは全員場に残る）。
- リンク成立のタイミング裏取り（公式FAQ）: 「リンクした時」の能力は出た時にトリガーする能力ではない（公式FAQ 2026-06-11変更）。《「黒幕」》自身を3枚リンクした状態で出した場合も、その「カード3枚でリンクした時」はトリガーする。すでに場にいる《「黒幕」》が他のゴッドの登場で3枚リンクした場合もトリガーする。本弾の発行形（出る側・リンクされる側の全員）はこの運用と一致する。
- **パターンA「出た時、またはリンクした時」（6件: dmd12-003／dmd12-004／dmr09-011／dmr09-012／dmr09-041／dmr09-042）は本弾の対象外**。出た時とリンクした時が別の誘発イベントであることは上記FAQで裏取りできたが、一体の能力として書かれた「出た時、またはリンクした時」が、リンクした状態で出た時に1回だけ誘発するのか、出た時とリンクした時で2回誘発するのかは、公式の裏取りが取れなかった。推測で回数を固めないため、変換形（move 誘発と link_established 誘発の2能力に分ける形）は本弾では固定せず、再変換でも能力ごと unsupported（need: link_establish_event）に残す。裏取りが取れれば2能力形で登録できる見込み。
- 4方向リンク（g_link_four_way 8件）と5体チェーン（g_link_five_god_chain 1件）は本弾の範囲外（リンク手順そのものの拡張が主ブロッカー。再変換では link 側の need だけ link_establish_event に差し替えてある）。
- proto T203（リンク時試験左ゴッド: link_established でドロー）／T204（リンク時試験中央ゴッド: カード3枚でリンクした時、link_count の if でドロー。黒幕型）／T205（リンク時試験右ゴッド: link_established でドロー）。tests/test_vocab_pilot155.py 6件（parse／リンクなし・パスで不発／出た側とリンクされる側の両方が各1回（trace で解決回数を実測する判別テスト）／link_count 条件（2枚で不発・3枚で発火）／外したメンバーは成立で誘発しない／外すだけでは成立しない）＋tests/test_vocab_pilot155_cards.py 2件（dm22ex2-s02「黒幕」、dmr11-004 悪魔右神メタモルフォーゼの手変換）。
- schema は再生成済み（イベント列挙に link_established）。
- 待機4枚（単独のうちパターンAを除く分: dm22ex2-s02、dm25-008、dmr11-003、dmr11-004）。再変換は別ラウンドで実施する（reopen link_establish_event。パターンA 6件と複合9件は戻しになる）。

## 第2段・小パイロットその1: unpaid 修正／unblocked 小拡張／bundles 式 — エンジン拡張あり（小）（2026-11-09）
網羅計画の第2段のうち、エンジン変更3件をまとめて実施したもの（カードデータは変更していない。是正・再変換は次ラウンド）。

### 1. unpaid 潜在バグ修正
- 症状: イベント（ev）の unpaid は実行側で立てられていた（turn.py の h_play が「free かつ as_paid でない」時に付け、ops.py の summon_on 等も付ける）が、_apply_one が作る move の収集レコードと置換照合用の _record_for のレコードに複写されていなかった。そのため when {event: move, unpaid: true} の誘発（登録済み dm26rp1-038、dm26ex2-041 極限龍神ヘヴィ等。第149弾の変換群にも同形がある）がすべて不発だった（ラウンド187の精査で実証）。summon レコードには従来から unpaid が載っていたため、「召喚した時」形だけが動き move 形が死んでいた。
- 修正: events.py の _record_for / _apply_one で、via・alt・vivid と同じ並びで ev の unpaid をレコードへ複写する（立っている時だけ True を載せる従来形式。照合は _match_when の既存の unpaid 分岐）。置換側（kind: replace の when）でも unpaid が読めるようになる。

### 2. unblocked 小拡張（gap unblocked_trigger、単独11件）
- attack タスクは phase 2 でブロック成立時に t["blocked"] を立てていたが、攻撃の終わりに作る attack_end レコードへ伝播しておらず「ブロックされなかった時」を when で書けなかった（設計 design-full-bandA.md の unblocked-trigger 単位どおりの小拡張）。
- 変更: combat.py の attack_end レコードに "blocked": bool(t.get("blocked")) を追加し、events.py の _match_when に broke と同じ形の blocked 照合を追加。defs.when は blocked が bool でなければ DefError とする検証を追加し、schema にも blocked を追加した。変換の型は when: {event: attack_end, subject: self, target: player, blocked: false} 等（対象指定なし・blocked: true の形も可）。遅延誘発（delayed_trigger の when）でも同じ照合が効く。
- ガードマンで攻撃先が変更された場合はブロックではない（507.2b）ので t["blocked"] は立たず blocked: false のまま（正しい）。
- **attack_end の発火条件自体は変えていない**。攻撃が途中で取り除かれた場合に attack_end が発火するかは設計側でも未確定（公式確認待ち。ura／j-tornado と共通の前提）で、本弾では現行の発火範囲のまま記録だけを足した。

### 3. 束（バンドル）数えの式 {bundles: ...}
- 数え方の単位は 113.2 で分かれる: 「シールドの数」は束単位、「シールドゾーンにあるカードの枚数」は束の中身を含むカード単位。表向きカードのカード数は既存の bundle_of＋filter: face_up で数えられるが、「表向きのカードを含むシールドが10以上」（ℵHEAVEN dm24ex2-025）と「表向きのシールド1つにつき」（ミケランジェロ dm26rp2-022）は束の数であり、数える式が無かった（faq-check-judgments-20261109.md 論点4。ラウンド175で bundle_of 形に統一した2枚は、束に表向きカードが2枚以上ある局面では文面と一致しない既知の不完全さがあった）。
- 追加する式アトム: {bundles: {owner: you/opp, face_up?: bool}}。face_up: true は「表向きのカードを1枚以上含む束」だけ（覆われている表向きカードも含む。文面の「含む」に対応）、false は含まない束だけ、省略時は全束。評価は selectors.py の eval_expr（count_of からも引ける。mod の count 等でも使える）、検証は defs.py の expr / count_spec、schema にも追加した。カード側の是正（上記2枚の書き換え）は次ラウンドで行う。

- proto T206（無償召喚の番人: unpaid の move でドロー）／T207（盾発の試験兵: S・トリガー）／T208（無封鎖の突撃手: attack_end blocked: false）／T209（封鎖感知の突撃手: blocked: true）／T210（直撃無封鎖の突撃手: target: player 併記）／T211（束数えの番人: bundles 条件でドロー）／T212（束数えの秘術: bundles 枚数ドロー）。
- tests/test_vocab_unpaid.py 4件（parse／S・トリガー無償召喚で move 誘発が発火（trace で解決回数を実測。複写を外すと落ちる判別済み）／支払い召喚では不発／既存 move 誘発の回帰）＋tests/test_vocab_unblocked.py 6件（parse と bool 検証／無封鎖で発火／ブロックで不発（判別済み）／blocked: true はブロック時のみ／target: player 併記形）＋tests/test_vocab_bundles.py 5件（式の数え分け: 束3・表向き含む束2・表向きカード3枚の区別／検証の DefError／閾値条件の発火・不発／束数ドロー）。
- schema は再生成済み（when に blocked、expr に bundles。あわせて従来から生成側にあったキーワード rensa の列挙差分も取り込まれた）。

## 第3段・共通基盤その2a: 履歴カウンタ一般化／宣言プリミティブ — エンジン拡張あり（2026-11-09）
網羅計画の第3段・共通基盤のうち、履歴系（バンドC1 U19＋バンドA/B/D の履歴系単位の受け口）と宣言系（バンドC2 基盤B4・U97、バンドB U3）をまとめて実施したもの。統一の確定事項（unification-applied-20261109.md）どおりの形で実装した。カードデータは変更していない（再変換は別ラウンド）。

### 1. 履歴カウンタ一般化（式 {turn_count:} / {used_count:} / {prev_shield_added:}、when の {ord:}）
- 記録器: events.apply_batch が適用済みレコードを並び順に走査し（_record_history）、turn_counters の hist:<kind>:{player}（クリーチャー単位は hist:<kind>:{cid}）へ集約する。あわせて対象レコードへ rec["ord"] = {kind: その出来事のこのターン通し番号} を刻み、when の {ord: {kind, 比較1つ}}（_match_when の照合）で「そのターン最初の〜」「2枚目以降の〜」が書ける。同時適用の束内の順序はレコードの並び順。
- kind: shield_put / shield_left / mana_put / cast / summon / attack / destroyed / broke_by_self（self 固定）/ draw / broken / enter / discard / leave / tap / untap / block / enter_unpaid / attack_by / attack_on（統一で追加した分を含む）。ord が刻まれるのは mana_put / enter / cast / summon / draw / attack / attack_by。
- 式 {turn_count: {kind, owner?, other?, filter?, ref?}}: attack は攻撃クリーチャーの cid リスト（hist:attackers）から数え直すため other（自分以外）/ filter（問い合わせ時点の特性で照合）が効く。attack_by / attack_on は ref（"self" か変数名）でクリーチャーを指す。owner: any は destroyed と attack だけ（検証で制限）。攻撃先（attack_on）は宣言時点で記録し、ブロック等で変わっても遡らない（バンドA の設計既定）。
- 式 {used_count: {owner?, filter?}}: cast レコード（唱えた呪文）と via: generate の実行（タマシード／フィールド／クロスギア）を、印刷特性 {cost, types, civs} のスナップショットで hist:used:{player} に積み、特性での数え直しができる。
- 式 {prev_shield_added: {owner}}: st_start がリセット直前に turn_counters を prev_counters へ退避し、前のターンの hist:shield_put を読む（バンドB U18）。ターン開始の一括アンタップも untap として数える（同設計の既定。公式確認は設計側の宿題のまま）。
- count_of の一般化: 式キー（turn_count / used_count / prev_shield_added / declared 等）を mod の count に書ける（バンドB U18 の受け口一般化）。
- 既存キー（entered: / drew: / broken: / broke_in:）は従来どおり別途維持し、既存カードの挙動は変えていない。ゲーム内履歴は mark の scope: game（下記）で担う。
- mark の scope（バンドB 基盤 mark-scope）: op mark に scope（turn＝既定 / attack＝その攻撃の中だけ / game）を追加。game は GameState.game_counters に積み、ターン開始で消えない（「ゲーム中に一度だけ」、極限ファイナル革命の使用履歴用。使用済みの実数え・カードデータ側の付け替えは別ラウンド）。cond の marked は辞書形 {name, scope} を受ける（文字列形は従来どおり）。

### 2. 宣言プリミティブ（op choose_number / choose_name / choose_civ、式 {declared:}）
- 保存先は GameState.declares。choose_number {as, min?, max?}（既定 0〜10、ask は choose_one で選択肢 num:N）、choose_name {as}（候補は対戦中の全カード名）、choose_civ {as}（5文明、ask は choose_civ で選択肢 civ:<文明名>）。選ぶのは常に効果の解決者。**choose_civ の player / exclude は統一の未確定事項のため実装していない**（相手に選ばせる形は今回の範囲外）。
- 式 {declared: 名前} は declares を読む。未宣言は 0 を返す（設計は「実行時エラーにしない」までで値未定のため、数・名前・文明のどの照合でも「一致しない」側に倒れる 0 を既定値とした。実装判断として明記）。
- filter の受け口（バンドB U3）: FILTER_EXPR_KEYS に civs / not_civs / name を追加し、式の結果が文明名の文字列なら単一文明のリストとして扱う（filter_match の正規化）。検証側は辞書値にリテラル照合を素通りさせるガードを追加。あわせて name_of の式検証分岐が無かった分を他の *_of と同じ受理に統一した（従来 filter 経由で未検証だった T169 の形が、今回の検証追加で弾かれるのを防ぐ）。
- modify 生成時のベイク（バンドC2 基盤B4）: op modify は mod 内（add_races の専用処理と gain を除く）と dynamic: true の範囲フィルタ内の {declared:} / {var:} を生成時点の値へ固定する（特性計算・範囲照合は env を持たないため、固定しないと宣言が届かない。判別テストあり）。
- mod の add_names（バンドC2 U97）: chars に名前の集合 names（主名＋追加分）を持ち、filter の name / name_has / not_name は集合に当てる。name_of は主名のまま（文面の「名前は〜も持つ」の読み）。

- proto T236（引き軽減試験獣: mod の count に turn_count draw。ティガウォック型）／T237（詠唱門番試験獣: turn_count cast の条件読み。ガリアル型）／T238（順序番人試験獣: ord ge。タクヤ型）／T239（最初番人試験獣: ord eq。グラヴィッツ型）／T240＋T241（used_count）／T242＋T243（shield_left）／T244＋T245（prev_shield_added）／T246（broke_by_self）／T247（数字宣言試験呪文）／T248（文明宣言試験呪文。プラトーン型）／T249（名前宣言試験呪文）／T250（封唱宣言試験呪文。dmart10-005 型）／T251（別名持ち試験獣）。
- tests/test_vocab_hist_counters.py 11件（parse と検証／引き軽減／詠唱門／ord ge・eq の発火境界／used_count の特性判別／shield_left の攻撃可否／prev_shield_added の前ターン読み／broke_by_self／記録器の直接確認（discard・tap・untap・destroyed・leave とリセット・退避）／game スコープ mark の持続）＋tests/test_vocab_declare.py 6件（parse と検証／数字宣言ドロー（0 の判別つき）／文明宣言タップ（選んだ文明は tap されない判別つき）／名前宣言ドロー（場に無い名前の判別つき）／封唱宣言のベイク（別の数字では封じられない判別つき）／add_names）。
- 判別確認: 記録器（_record_history）を止めると履歴テスト 11件中9件が落ちる（残りは parse と mark）、ベイク（dynamic 範囲分）を止めると T250 のテストが落ちる、{declared:} の読みを止めると宣言テスト 6件中4件が落ちることを確認済み。
- schema は再生成済み（式に turn_count / used_count / prev_shield_added / declared / name_of、cond の marked 辞書形、when に ord、mod に add_names、op に choose_number / choose_name / choose_civ と mark の scope）。
- 全体テスト初回で判明した回帰2件とその修正（同日）: (1) count_of の一般化で単一キー制限をかけたため、複合キー辞書 {distinct_cost_count: ..., base: 0}（variety breaker の mod）がセレクタ扱いになって KeyError になった。従来キー（civ_count / distinct_cost_count / sum / var / bundles）は従来どおりキー有無で式判定し、新規キーだけ単一キーで判定するよう分けた。(2) filter の name に式検証を広げたため、既存の変換データの形 name: {ref: 変数名}（参照指定形。dmr01-058 等5件）と name: {name_of: ...}（8件）が読み込みで弾かれた。{ref: 名前} は式ではないので検証対象外とし、name_of は他の *_of と同じ受理分岐を defs.expr に追加した（従来は未検証で素通りしていた形の明示化）。

## 第3段・共通基盤その2b: レコード系基盤5点（効果帰属／公開集合／S・トリガーの印／合成レコード時機／名前つき条件） — エンジン拡張あり（2026-11-09）
網羅計画の第3段・共通基盤のうち、レコード系の5点（バンドC2 基盤B1、C1 U39・U26、C2 U68、B U7・U1）をまとめて実施したもの。統一の確定事項（unification-applied-20261109.md）どおりの形で実装した。カードデータ（converted.yaml / rejects.jsonl）は変更していない（再変換は別ラウンド）。

### 1. 効果帰属レコード（バンドC2 基盤B1）＋捨て札の帰属（バンドC1 U26）
- events.ev_task: 効果の解決中に出る move イベントへ、発生源の defn 名 cause_defn と種別 cause_kind（発生源の面の types に spell を含めば "spell"、そうでなければ "ability"）を常時刻む（従来の trace 用 cause も同じ値で常時化）。状況起因処理・コスト・バトル等の効果起因でない移動には付かない。_record_for と _apply_one の収集レコードにも複写する。
- when の新キー cause: {by?: you/opp, kind?: spell/ability}（defs 検証・schema 追加）。by は解決者との関係、kind は cause_kind と照合する。発生源の無いレコードには一致しない。
- U26 の実態は2つの潜在不具合だった: (1) _apply_one が by を収集レコードへ複写しておらず、when:{by:} が move 誘発で一切効かなかった（複写を追加）。(2) _collect_triggers の lki 発生源がバトルゾーン発だけだったため、手札から捨てられた本人の誘発・置換（発生源ゾーン=hand）が拾えなかった。非bz の lki でも「移動後の現在ゾーン ≠ lki ゾーン」の場合に発生源へ加え、能力フィルタを lsrc の zone に合わせた。shield→hand の自己誘発（G・ストライク等、能力は zone: hand）は通常経路で拾われるため二重発火しない（lki の zone=shield と一致しない）。
- 置換の諮問（h_event）は従来から when の by / cause を見ており、T254 型（手札の置換）は追加変更なしで機能することをテストで確認した。

### 2. 公開集合の保持（バンドC1 U39）
- 式に {total_cost: セレクタ} / {total_power: セレクタ} を追加（selectors.eval_expr、defs 検証、schema 追加、count_of 経由で mod の count でも使用可）。choose の as で束ねた集合を {ref: 変数名} で指すのが主用途で、「公開した3枚のコストの合計」等が書ける。空集合は 0。
- op choose に reveal: true を追加し、束ねたカードを note_public("reveal", cid) で公開情報（s.pub）に残す。reveal_until（公開の持続）の本実装は対象文面が出た時点で別途。

### 3. S・トリガーの印（バンドC2 U68）
- Card に strigger_off / strigger_on（手札にいる間だけ有効な印）を追加。_raw_move で手札から離れる時に両方消去する（hold 経由も含む）。
- op move に strigger: "off"/"on" を追加: 手札に加わる移動（効果の擬似ブレイク経由を含む）と束の下のカードに印を付ける。h_break の宣言適格判定で off は宣言不可に、on は「クリーチャーか呪文の面なら宣言可」に上書きする。data/rules/keywords.yaml の escape はこの印（strigger: "off"）を使うよう変更（YAML の裸 off は真偽値になるため引用符つき）。
- op strigger {select, mode} を新設（移動させずに対象へ印を付ける。dmx18-024 型の付与誘発用）。
- 到達性の確認: バトルゾーンの常在型は affects.zone で他ゾーンの chars に届くため、mod deny: [s_trigger]（dmrp01-s03 型）は追加実装なしでシールドゾーンのカードに効くことをテストで確認した。

### 4. 合成レコードの誘発時機（バンドB U7）
- use_s_trigger レコードを新設: h_break で S・トリガーとして宣言されたカードが h_enqueue_st で待機に入る時にだけ _collect_triggers へ渡す（S・バック経由は付けない）。EVENTS と schema に追加。
- battle_end レコードを新設: combat._battle のスレイヤー窓の後に、両参加者を subject（相手を opponent）とするレコードを出す。攻撃フローのバトルと force_battle の両方が _battle を通るため両対応。既に場を離れた参加者は発生源が無く拾われない（設計の許容範囲）。
- chosen_trigger（相手がこのクリーチャーを選んだ時）は精査で既存可と確定: selectors.select が choose レコードを _collect_triggers へ渡す既存機構で発火する。ただし作られるのは「選んだプレイヤーが対象のコントローラの相手」の時だけ（picked_opp 条件）。chooser: opp で被害側が自分のクリーチャーを選ぶ形では作られない — 実在文面（相手が選ぶ）とは一致するが、変換時は形に注意。
- 式のイベント参照の基盤: selectors._expr_refs が "event.<key>"（event.opponent 等）を env["event"] から引けるようになり、{power_of: {ref: "event.opponent"}} 等が書ける。あわせて schema の cost_of / power_of を {ref:} 形も受ける anyOf に広げた。
- **battle_lose レコードは未実装（判断保留）**: 生成形が統一メモ §4-1 で未確定（バンドB の move 由来案 vs バンドD のバトル解決時点の対レコード案）。ユーザーの確定後に別途実装する。

### 5. 名前つき条件アトム（バンドB U1）— 精査で全て既存可
- G・G・G = 手札数の count 式＋zone: hand の常在型 cost mod、ラビリンス = シールド数の比較式＋相手の手札ゾーンへの affects と deny: [cast]、レインボーナス = filter multicolor の exists、龍マナ武装 = マナゾーンの race_has フィルタの count で、いずれも既存の式・フィルタで書けることをテストで裏取りした。新規アトムの追加は不要。ラビリンスの前提だった「BZ の常在型が相手の手札のカードの chars（deny cast）に届く」ことも実測で確認。convert_cards.py の対応表への追記は変換側の作業として残す（本弾はエンジンとテストのみ）。

- proto T252〜T279（T280 は chosen の形の誤りに気づき撤去）: T252 捨て検知試験獣（by: opp つき検知）／T253 捨てられ誘発試験獣（パウアー型）／T254 捨て置換試験獣（メテオキャノン型）／T255 呪文では離れない試験獣（cause 照合）／T256 除去試験呪文／T257 破壊能力試験獣／T258 公開合計試験呪文／T259 合計パワー門試験呪文／T260 マナ合計強化試験獣／T261 エメラル型試験呪文／T262 帰還試験呪文／T263 印付与試験呪文／T264 無印の盾兵／T265 付与誘発試験獣／T266 非光封じ試験獣／T267 選ばれ誘発試験獣／T268 ST使用観測試験獣／T269 バトル後自壊試験獣／T270 強制バトル試験呪文／T271 GGG軽減試験獣／T272 ラビリンス試験獣／T273 観測試験呪文／T274 レインボーナス試験獣／T275 多色試験獣／T276 龍マナ武装試験獣／T277 竜試験兵／T278 逃避試験獣／T279 闇盾試験兵。
- tests/test_vocab_cause_records.py 8件（parse と cause 検証／相手の呪文での捨て札で手札誘発が発火（by 複写と lki 拡張の判別済み）／自分の呪文では不発／検知側 by: opp の発火・不発／置換は相手ターンだけ／cause kind: spell で場に残る・ability とバトルでは残らない判別）＋tests/test_vocab_reveal_binding.py 5件（parse と検証／合計コストの境界と公開の保持・超過側の判別／合計パワーの門／mod の count での合計／空集合は0）＋tests/test_vocab_strigger_mark.py 7件（parse と検証／move off で宣言不可（判別済み）・対照で宣言可／エスケープの off／op strigger の on で宣言可・無印では不可／印は手札を離れると消える／deny: [s_trigger] がシールドに届く・光は対象外）＋tests/test_vocab_trigger_records.py 6件（parse／chosen の発火・対照／use_s_trigger の発火・辞退では不発（判別済み）／battle_end はバトルでのみ・force_battle でも（判別済み）／event 参照の式）＋tests/test_vocab_named_conditions.py 5件（parse／GGG の軽減と判別／ラビリンスの deny と対照／レインボーナス／龍マナ武装）。
- 判別確認: by の収集レコード複写を外すと cause 系2件が落ちる、cause 刻印を外すと spell 置換テストが落ちる、lki 拡張を外すと手札誘発テストが落ちる、宣言適格の上書きを外すと off の2件が落ちる、use_s_trigger／battle_end のレコード生成を外すと各テストが落ちることを確認済み。
- schema は再生成済み（when に cause、式に total_cost / total_power、cost_of / power_of の anyOf 化、EVENTS に use_s_trigger / battle_end）。
- **全体テストの既存失敗1件（本弾の変更起因・要判断）**: tests/test_tools.py::test_system_prompt_picks_similar_examples が「例つきプロンプト長 < 全体の60%」の比率ガードで落ちた（56182 < 93304×0.6=55982.4、比率 0.6021、超過は約200字=0.36%）。原因は system_prompt の共通部（schema.build() の JSON と rules テキスト）が語彙追加のたびに増える累積で、本弾の増加は約640字（cause 約150、total_cost/total_power 約240、cost_of/power_of の anyOf 化 約200、新イベント名 約35、keywords の escape 1行 +19）。本弾開始時点の余裕は約56字しか無かった（第2a等の増加で既に際どかった）。examples_for の例選択自体は無事（先頭 dmx03-035・8枚を確認）。エンジンの挙動テストは全て通過しており、直し方は閾値の見直しかプロンプト側の削減で、変換ツール側の判断として親へ残す。本弾の5点はいずれも切り離して戻すと各単位の受け口が消えるため、独断では巻き戻していない。

## 第3段・from_under 機構（下にあったカードの移動レコード） — エンジン拡張あり（2026-11-10）
網羅計画の第3段の残件。第156弾の event.under（離脱する側から下を見る）に対する、下のカード側から見る機構。gap from_under_trigger の rejects 10件（dm34 系5件、dmsd06-012、邪眼帝2件、dm25ex3-or4、dm25rp4-033）が対象。カードデータ（converted.yaml / rejects.jsonl）は変更していない（再変換は別ラウンド）。

### 設計
- レコード: バトルゾーンで他のカードの下にあったカードの move レコードには、宿主（上にいたカード）の移動直前の姿を host（移動直前の ref）と host_lki（defn/face/controller/zone/tapped/chars/ref のスナップショット）として載せる。host の有無が「下にあったか」の判別そのもの。シールドの束は対象外（バトルゾーンの重なりだけ。束は第148弾の bundles 式の領分）。封印（seal_of が付いたカード）も対象外。
- 発行経路は2つ: (1) スタック一括移動 — _apply_one が一緒に動いた下のカードにも move レコードを出す（従来は最上位のレコードしか出なかった）。移動前に under_lkis として各下カードの姿を取り、実際に行き先へ動いたものだけにレコードを出す。再構築（card_only／スター進化）で場に残る分は unders から外れており対象にならない。(2) 単独移動 — 下のカードだけが動く移動（メテオバーンのコスト、G-NEO 置換の move_under_to_event 等）は、そのレコード自体に host / host_lki を載せる（_record_for も同じ）。
- when の新キー from_under: true（下にあった）/ false（下になかった。通常の移動だけを見る否定形）/ self（発生源自身の下にあった。宿主自身の誘発用）/ {owner?, filter?, other?}（宿主への条件。subject と同じ形で host_lki に当てる）。defs 検証と schema（when プロパティに from_under）追加済み。false 形は dmsd06-012 のため: 「破壊された時」と「下から墓地に置かれた時」が同じ移動（宿主ごと破壊）で重ならないよう、破壊側の誘発を from_under: false で切り分ける（フレーバー文の「一気に4枚」が1枚につき1回の裏付け）。
- 誘発収集: 下のカードのレコードでは宿主も lki 発生源に加える（宿主は既に場を離れており、通常経路では届かないため）。ただし宿主の能力は when に from_under を書いたものだけを見る（host_only スコープ）: 宿主の通常の観測誘発が下のカードの枚数だけ重複発火するのを防ぐ。宿主自身の移動は宿主自身のレコードで通常どおり収集される。下のカード自身の誘発はスコープしない（U26 の作法どおり、本人の move レコードで本人の誘発が発火する）。
- 履歴: 下のカードのレコードは hist の leave / destroyed に数えない。下のカードは総合ルールの進化の扱いで「特性を持たないカード」として置かれ（dmwiki の破壊の項）、クリーチャーとして離れた／破壊されたのは最上位だけのため。カード単位の観測（ボーン・アミーゴ型の「自分のカードが破壊された時」）はレコード自体が出るので拾える。mana_put 等の他の種別は従来どおりカードごとに数える。
- 根拠: 下のカードにもカード単位のイベントが立つことは dmwiki の破壊の項（下のカードは「特性を持たないカードが破壊された」ものとして扱われ、カード単位の観測誘発は下のカード1枚ごとに誘発する／「クリーチャーが破壊された」のは最上位だけ）による。邪眼帝型（宿主自身の「下を離れた時」）を宿主破壊時にも発火させるのは 603.5c/d の lki 原則による（発生源の能力は移動直前に存在した）。邪眼帝固有の公式 QA は未確認。

### 実装
- dmsim/engine/events.py: _record_for と _apply_one に host / host_lki の付与と下カードのレコード発行、_match_when に from_under 照合、_collect_triggers に宿主の lki 発生源（host_only スコープ付き）、_record_history に host 付きレコードの leave / destroyed 除外。
- dmsim/defs.py: when の from_under 検証（true / false / self / {owner, filter, other}）。dmsim/schema.py と data/schema/card.schema.json: when プロパティに from_under を追加し再生成（差分はその1点のみ）。
- proto T280〜T288: T280 下敷き墓地試験兵（A型: 自身＋宿主フィルタ {types: [evolution]}）／T281 進化試験龍／T282 平宿主試験獣／T283 邪眼試験帝（C型: from_under: self）／T284 燃焼宿主試験龍（単独移動: under コストの起動型）／T285 下離れ観測試験獣（D型: 宿主 owner 照合）／T286 道具観測試験獣（B型: from_under: true）／T287 無言の下敷き試験兵／T288 道具観測・双試験獣（B実物型: 破壊側 from_under: false ＋下から側 true の2誘発）。
- tests/test_vocab_from_under.py 18件（parse と検証／レコードの形の直接確認／履歴の数え／A型の発火と対照2件／C型の宿主ごと破壊で下の枚数だけ発火・対照2件／D型の発火と相手側の対照／B型の発火と種族対照／B実物型は重なっても1回・通常破壊で1回／単独移動（under コスト）の発火と対照）。発火の観測は trace の解決回数。
- tests/test_vocab_from_under_cards.py 1件（対象10件すべての手変換 parse）: dm34 系5件は A型の誘発追加、dmsd06-012 は B実物型の2誘発、邪眼帝2件は from_under: self ＋ modal（山札上1枚をシールド化／相手クリーチャー1体を破壊）、dm25ex3-or4 は D型 ＋ 相手の自己選択捨て札と may ブレイク、dm25rp4-033 は D型（to: graveyard）＋ {ref: event.subject} を手札に戻す may。10件すべて parse 通過し、unsupported から from_under_trigger を外せる形になった。
- 判別確認: 下カードのレコード発行を止めると直接確認・A・C・D・B の5件が落ちる、宿主の lki 発生源を止めると C型の1件だけが落ちることを確認済み（復元後は全通過）。

### 残る不足
- 再構築パス（card_only／スター進化で最上位だけが離れる時）で場に残らず墓地へ落ちる非クリーチャーの下カード（タマシード等）は _rebuild の内部で raw_move され、レコードが出ないまま。対象10件には不要（dm34 系はスタックごと離脱、邪眼帝は G-NEO 置換で下が個別の move イベントになる）ため未実装のまま残す。必要になった時点で _rebuild 側にもレコード発行が要る。

## 第159弾: first_attack_of_turn（そのターンはじめての攻撃）— 新語彙なし（2026-11-10）
「そのターンはじめての攻撃であれば」は、攻撃レコードに刻まれる通し番号（第3段・履歴基盤の ord）を when で照合して表す。新語彙・エンジン変更なし。
- 煽動型（ターンの初回攻撃）: {kind: trigger, when: {event: attack, subject: {owner: you, filter: {types: [creature]}}, ord: {kind: attack, eq: 1}}, effect: [...]}。ord の attack は攻撃側プレイヤーごとの通し番号なので、subject の owner と合わせて「自分のクリーチャーによる、そのターンの最初の攻撃」になる。相手のクリーチャーが対象なら subject owner: opp（ord も相手側で数える。dmr14-003）。
- 自分型（このクリーチャーがはじめて攻撃する時）: when の subject: self ＋ ord: {kind: attack_by, eq: 1}。attack_by はクリーチャー単位の通し番号なので、ターンの最初の攻撃でなくても自身の初回なら発火する（dmr20-005、dmrp03-s06。条件は if に置く）。
- 全体型（各ターン、はじめてクリーチャーが攻撃する時）: subject owner: any ＋ ord: {kind: attack, eq: 1}。攻撃は通常ターンプレイヤーだけが行うため、プレイヤーごとの eq 1 がターンの初回と一致する（dmsp01-036。効果は modify の breaks_add を duration: during_attack でその攻撃だけに与える）。
- proto T289（煽動型）/ T290（自分型）。tests/test_vocab_pilot159.py 3件（parse、煽動型は1回目の攻撃でだけ発火、自分型は他が先に攻撃しても自身の初回で発火し同ターン2回目は発火しない）。
- tests/test_vocab_pilot159_cards.py 1件（対象19件すべての手変換 parse）: 煽動型14件、自分型2件、全体型1件、相手型1件（dmr14-003。ターン開始の「可能であれば攻撃する」は dmrp15-006 と同型の modify require、初回攻撃で出したファンキー・ナイトメアは delayed_trigger でターン終わりに破壊）。dmrp03-s06 は連結表記で split が効かなかったキーワードとパワーアタッカー+1000000（static power_when）も補った。
- 差し戻し1件: dm26sd1-m001 はマッハファイター付与（第139弾の常在形）とターン終わりの墓地／マナからの出し（modal）まで書いたが、「各ターン、相手のクリーチャーがはじめて攻撃するなら、可能ならこのクリーチャーを攻撃する」が残る。must_be_attacked は攻撃側の通し番号で条件づけられないため、新 gap first_attack_taunt として rejects に残す（combat の攻撃先制限に attack_by 次数の条件を足す小規模拡張が候補）。
- 待機19枚（first_attack_of_turn のみが gap のもの。dm15-004 は accel も付くため対象外）。再変換ラウンド195で18件を新規登録、dm26sd1-m001 は first_attack_taunt で差し戻し（converted 9,107枚、rejects 3,424件、漏れゼロ）。

## 第160弾: must_be_attacked の first_only 形（はじめて攻撃するなら）— mod 拡張（2026-11-10）
「各ターン、相手のクリーチャーがはじめて攻撃するなら、可能ならこのクリーチャーを攻撃する」は、第51弾の mod must_be_attacked の辞書形 {first_only: true} で表す（defs は true または {first_only: true} のみ許可）。
- 判定は combat の攻撃先制限: 対象の特性 must_be_attacked_first が立ち、攻撃側クリーチャーの履歴カウンタ hist:attack_by が 0 の時だけ誘引として扱う。クリーチャー単位の条件なので、別のクリーチャーが先に攻撃していても、まだ攻撃していない個体の初回攻撃は制限される（ターン単位ではない）。
- 特性は chars に must_be_attacked_first として集約する（進化の重ね merge・封印時の空特性も対応）。op modify で付与する形も同じ mod で書ける。
- proto T291（初撃誘引獣）。tests/test_vocab_pilot160.py 5件（parse、不正形の拒否、初回は制限される、一度攻撃した後は制限されない＝履歴カウンタの種付けで確認、制限はクリーチャー単位＝実戦で確認）。
- 対象は gap first_attack_taunt の dm26sd1-m001（単独1件）。dm25ex3-rp4s05「K」-9+9+9 の must_be_attacked_first_only も同じ形で解けるが、enter_effects_ignored が残るため対象外。
- 再変換ラウンド196で dm26sd1-m001 を新規登録（converted 9,108枚、rejects 3,423件、重なり0、漏れゼロ）。tests/test_vocab_pilot160_cards.py で登録形を検証し、test_vocab_pilot159_cards.py の差し戻し検証は登録検証に更新した。

## 第161弾: attacked_this_turn_condition（このターン攻撃したか）— 新語彙なし（2026-11-10）
「このターン、〜が攻撃していなければ／攻撃していれば」は、履歴カウンタ式 {turn_count: ...}（第3段・共通基盤）を条件に置いて表す。新語彙・エンジン変更なし。
- 攻撃できない形: 常在型の if に {cmp: [{turn_count: {kind: attack, owner, other?, filter?}}, "==", 0]} を置き、mod {deny: [attack_player, attack_creature]}（実カード dmbd17-009「墓地13枚より少なければ攻撃できない」と同じ条件つき常在型の型）。other: true で自分以外の攻撃を数える。原文に「自分の」とあれば owner: you、無ければ owner: any。「自分のパワー12000以上のクリーチャーが」は filter: {power_ge: 12000}（other なし＝自分も含む）。
- 条件つき誘引形: 「相手のターン中にタップしていて、そのターンまだ攻撃されていなければ、可能ならこのクリーチャーを攻撃する」は常在型の if {all: [{is_turn: opp}, {exists: {ref: self, filter: {tapped: true}}}, {cmp: [{turn_count: {kind: attack_on, ref: self}}, "==", 0]}]} ＋ mod {must_be_attacked: true}（第51弾）。
- 効果の条件形: 呪文・誘発の if / op if の cond に {cmp: [{turn_count: {kind: attack, owner: any}}, ">=", 1]}。「選んだクリーチャーがこのターン中に攻撃していたら、ターンの終わりに破壊する」は delayed_trigger の効果に {cmp: [{turn_count: {kind: attack_by, ref: <選択変数>}}, ">=", 1]} を置く。
- proto T292（様子見獣）/ T293（条件誘引獣）/ T294（終末スレイヤー呪文）。tests/test_vocab_pilot161.py 5件（parse、攻撃できない形は他の攻撃後に解ける、条件つき誘引は一度攻撃されたら解ける、遅延破壊は攻撃した場合のみ）。
- 再変換ラウンド197: 対象11件（単独 gap）のうち8件を新規登録（dmrp14-089、dmrp14-s04、dmrp21-067、dm26sd1-p008、dmr17-s09、dmrp06-079、dm25rp4-044、dm25rp4-048）。差し戻し3件: dmrp08-023 は「他のクリーチャーが2体以上」が攻撃したクリーチャーの distinct な数えを要するため attacked_this_turn_condition_distinct に、dm25ex3-020 は「自分がカードを実行した時」の統合トリガーが無いため card_executed_trigger に、dm36-038 は「このクリーチャーを攻撃できるクリーチャーは自分を攻撃できない」という攻撃先スコープの禁止が無く attack_on_scoped_player_denial に、それぞれ gap を絞り込んだ（dm36-038 は rejects 行に名前・partial が無いため再提出せず gap 名のみ差し替え）。converted 9,116枚、rejects 3,415件、重なり0、漏れゼロ。attacked_this_turn_condition の残りは shield_placement_restriction と重なる dm24ex3-tf16 のみ。

## 第162弾: extremal（パワーが一番小さい／大きいクリーチャー）— セレクタ拡張（2026-11-10）
「パワーが一番小さい／大きいクリーチャーを選ぶ」は、セレクタの新キー extremal: min_power / max_power で表す。候補（zone / owner / filter で絞った後）の中で現在パワー（常在型の修整込み）が最小／最大のものだけが残る。同点はすべて候補に残り、どちらを選ぶかは chooser の選択に委ねられる（dm31-046「2体以上ある場合、自分がどちらを破壊するか選ぶ」、相手に選ばせる形は chooser: opp）。count: all なら同点のすべてが対象（「一番大きいクリーチャーをすべて破壊する」）。
- 実装: defs の SELECTOR_KEYS と検証（値は min_power / max_power のみ。ref / under_of / bundle_of / exlife_of とは併用不可）、schema.py と card.schema.json、selectors.candidates のゾーン経路（exclude の後）に extremal の絞り込みを追加。count 式の評価にも同じ候補が使われる。
- proto T295（最小・1体）/ T296（最大・すべて）/ T297（タップしている中で最小＋次の相手ターンにアンタップしない。dm32-014 と同型で、tap の no_untap_next はタップ済み対象にも印を付ける）。tests/test_vocab_pilot162.py 6件（parse、不正形の拒否、最小が1体だけなら自動で決まる、同点なら選択肢は同点の2体だけ、最大すべて、同点でない凍結形の実挙動）。
- 併せて使った既存の型: dm25ex3-sp5 の条件つき S・トリガー付与は zone: shield の self 常在型（dmx23-031 と同型。条件は cost_ge に sum 式で「相手のマナ枚数より大きい」）、「2回選ぶ（同じものを選んでもよい）」は modal の repeat、見たカードの振り分けは choose count: all で束ねて move {ref, count: 1} → move {ref, count: all} の残り型。dm32-064 の2体目は extremal の choose を exclude: {ref: 先の変数} でつないだ。
- 再変換ラウンド198: 対象10件（単独 gap。dm23sp1-007 は同一 gap が2条項分）すべて新規登録、差し戻し0（dm24bd4-010、dm24ex3-024、dm25ex3-rp4011、dm25ex3-sp5、dm25ex3-td14、dm31-046、dm32-014、dm32-064、dm23sp1-007、dm26sd1-w002f）。converted 9,126枚、rejects 3,405件、重なり0、漏れゼロ。extremal_power_selection の残り5件は他の gap と重なるもの（lose_prevention、god_slayer、invasion_zero、up_to_cost_reduction）。

## 第163弾: reveal_until（「〜が出るまで表向きにする」）— 新 op（2026-11-10）
「自分の山札の上から、＜条件＞が出るまで表向きにする」を新 op reveal_until で表す。対象プレイヤー（player。既定 you。player_from = 変数名なら、その最初のカードの持ち主 = 「その持ち主は自身の山札の上から」）の山札を上から1枚ずつ公開し、filter に合うカードが count 枚（既定1）出た時点で止める。合ったカード群を as に、出なかった公開カード群を rest_as（既定 as + "_rest"）に束縛する。公開したカードは山札に残るので、行き先は後続の op が決める（move で出す／手札に加える／墓地に置く／山札の下に置く、shuffle で山札に戻す）。count は式で、{var: 先に破壊・移動した変数} を渡すと「破壊した数と同じ数」になる。相対条件は filter の式値に cost_of / power_of を置く（「破壊されたクリーチャーよりコストが小さい」= cost_le: {sum: [{cost_of: {ref: d}}, -1]}）。count が 0 以下のときは何も公開しない。
- 併せた小拡張: shuffle に player_from（「その持ち主は山札をシャッフルする」）、move の order に shuffle（「残りのカードをすべてシャッフルし、山札の下に置く」。動かす集合だけを Fisher-Yates で混ぜる。ヨビニオンの残り処理と同方式）。
- proto T298（基本形: 出す＋残りは墓地）/ T299（2体＋シャッフルで戻す）/ T300（持ち主＋相対コスト、dmex17-053 と同型）/ T301（破壊した数と同じ数、dm26ex3-061 と同型）。tests/test_vocab_pilot163.py 7件（parse、不正形の拒否、基本形、複数ヒット＋シャッフル、持ち主の相対コスト、動的な数、ヒット無しで山札が尽きて敗北する（総合ルール104.2b）まで実挙動で確認）。
- ヨビニオン（op yobinion）は従来どおり専用 op のまま（発生源のコスト基準＋残りをシャッフルして下に置くまでが一体の宣言効果のため）。今回の reveal_until は宣言効果ではなく通常の効果文のための汎用形。
- 再変換ラウンド199: reopen できた18件のうち16件を新規登録、2件を差し戻し（dmx22b-043 ヒラメキ・プログラム → psychic_filter: 破壊対象の「サイキックではない」の区別が要る。GR・超次元・サイキック関連は実装しない方針のため見送り。dm24ex2-040 運命の境界線 → first_cast_spell_trigger: 「各ターン、自分がはじめて呪文を唱えた時」の誘発＋その呪文基準の相対条件＋無料詠唱の複合）。dm24ex2-chog03 は rejects 行に id / gaps / text しか無く reopen の対象にならないため手を付けていない。converted 9,142枚、rejects 3,389件、重なり0、漏れゼロ。reveal_until の残りはこの2件のみ（dm24bd6-011 は他の gap と重なるもの）。

## 第164弾: chosen_protection_scoped（範囲つきの「選ばれない」）— select の発生源照合（2026-11-10）
「呪文の効果によって相手に選ばれない」「コスト4以下の呪文によって選ばれない」「多色ではない、クリーチャーの能力または呪文で選べない」「このクリーチャー以下のコストのカードによって選ばれない」など、発生源で範囲を限った「選ばれない」。表現は従来の deny の辞書形 {action: be_chosen, other: <発生源フィルタ>}（other フィルタの式値は保護される側を self として評価される。第126弾の基盤がそのまま使える）:
- 呪文からだけ: other: {types: [spell]}。コスト4以下の呪文から: {types: [spell], cost_le: 4}。多色でない発生源から: {any_of: [{types: [creature]}, {types: [spell]}], multicolor: false}。自分以下のコストから: {cost_le: {cost_of: {ref: self}}}。
- エンジン変更は1点だけ: selectors の選択候補の除外（be_chosen 判定）が、発生源なしで permits を見ていたのを、解決中のカード（env の self）を other として渡すようにした。発生源フィルタのない deny（文字列形）は従来どおり無範囲に効く。
- 発生源は「その選択を行っている効果のカード」。呪文の解決中は呪文自身、クリーチャーの能力の解決中はそのクリーチャー。タマシードやフィールドの能力は types で区別される（呪文範囲には入らない）。
- 攻撃中だけの保護（dm24bd3-007）は、攻撃誘発で modify により during_attack の間だけ付与する形で表した。超魂X のホストへの付与は choukon: true の常在型（第126弾の先例は誘発型）。
- proto T302（呪文範囲）/ T303（コスト範囲）/ T304（多色範囲）/ T305（相対コスト範囲）/ T306（集団への常在型）/ T307（多色・高コストの破壊呪文＝検証用の発生源）。tests/test_vocab_pilot164.py 8件（各範囲で「選べない／選べる」を呪文・クリーチャー・多色呪文の発生源ごとに実挙動で確認。集団形は相手ターンで検証）。
- 再変換ラウンド200: 16件のうち14件を新規登録、1件を差し戻し（dm15-022 聖騎士ウラヌス → crossed_gear_chosen_protection: 保護対象がこのクリーチャーにクロスされたギアで、常在型の affects では指せない。affects: crossed はギア側からホストを指す逆向き）。残る1件 dm24ex3-rp3tr6 フィオナ・フォレストは real_akashic.yaml に手書き変換（同じ2能力）が既にあり、rejects の行は古い残りだったため、converted へは登録せず行の掃除のみ（登録すると duplicate card id で全体が読めなくなる。教訓: 対象が real_akashic.yaml 等の他ファイルに無いかも提出前に見る）。converted 9,156枚、rejects 3,374件、重なり0、漏れゼロ。chosen_protection_scoped の残りは他の gap と重なる2件のみ。

## 第165弾: ura_ninja_strike（ウラ・ニンジャ・ストライク）— 新語彙なし（2026-11-10）
ウラ・ニンジャ・ストライク N（文明）は、通常のニンジャ・ストライクの declare 2本（相手の攻撃時／ブロック時。マナが N 枚以上で無償召喚し、ターンの終わりに山札の下へ）の条件に「自分のマナゾーンに指定文明がある」を足したもの。指定が2文明（光/水）のものは exists を2つ並べる。エンジン変更は無し。変換ツール側の keyword_patterns.yaml に ura_ninja_strike_<文明> の6パターン（闇・水・火・光・自然・光/水）を追加し、今後の自動変換でも展開できるようにした。
- proto T308（水3）/ T309（光/水6）。tests/test_vocab_pilot165.py 6件（宣言→召喚→ブロック→山札の下まで、文明が無い／枚数が足りないと宣言できないこと、2文明の片欠けを実挙動で確認）。
- 「その攻撃中にニンジャ・ストライクを使っていなければ」は、通常のニンジャ・ストライクと同じく宣言ウィンドウ自体が攻撃ごとに1回という既存の扱いに揃えた。
- 再変換ラウンド201: 16件のうち14件を新規登録、2件を差し戻し（dm26ex4-010 / sec007 切札混成 光隼 蒼斬丸 → attack_cancel: 「攻撃を中止する」が未実装。ウラ declare と出た時のドローは partial に入れたので、残りは中止条項のみ）。converted 9,170枚、rejects 3,360件、重なり0、漏れゼロ。ura_ninja_strike は全解消。提出前に対象を real.yaml / real_akashic.yaml / proto.yaml とも照合し、重複は無いことを確認した（ラウンド200の教訓）。
- 対象の残りの能力で使った形: 相手が自分のシールドをブレイクした時の誘発は when {event: break, player: you}＋相手自身に選ばせる破壊（chooser: opp）。捨てたカードと同じコストは cost_le と cost_ge の重ねがけ（cost_eq は無い）。相手のマナ枚数より大きいコストは cost_ge に {sum: [count, 1]}。「2枚まで引く」は repeat times 2＋may draw（変換済みの先例どおり）。手札を2枚、山札の上か下に置く形（dm26ex3-049）は「上に入れる分を選ぶ（up_to）→残りを下へ」の2段で表した。

## 第166弾: shield_force（シールド・フォース）（2026-11-11）
シールド・フォースは「出す時、自分のシールドを1枚選んでもよい。そのシールドがシールドゾーンにある間、このクリーチャーは次の能力を得る」。EXライフ（第何弾かは keywords.yaml 参照）と同じくシールド側に紐付け参照を持たせる形で実装した。
- 実装: Card に sforce_of（このシールドが力を与えているクリーチャーの参照 [cid, gen]）を追加。ゾーン移動で外れる（core の移動時クリア、EXライフと同位置）。新 op {op: sforce_link} は自分のシールドから0〜1枚を選ばせ（選ばなければ何も起きない）、選んだシールドに sforce_of = 自分を刻む。再選択時は古い紐付けを消す。得る能力は能力フラグ sforce: true（defs ABILITY_KEYS に追加）で示し、core.abilities() のゲートで「紐付いたシールドが今もシールドゾーンにある（core._sforce_active）」時だけ機能させる。常在型・誘発型・置換など kind を問わない。カード側は出す時の誘発 {kind: trigger, when: {event: move, subject: self, to: bz}, effect: [{op: sforce_link}]} を明示で持つ。
- シールドの束（シールド・プラスで下に重ねたカード）については、選んだシールド本体のインスタンスがシールドゾーンにあるかどうかで判定する。山札の下に置かれた側のカードが動いても紐付けは切れない。
- proto T310（ブロッカー付与）/ T311（パワー+3000とW・ブレイカー）/ T312（ブロックした時に引く誘発の付与。印刷ブロッカー持ち）/ T313（ブロッカー付与＋離れない）。tests/test_vocab_pilot166.py 7件（紐付けで付与→シールドが離れると消える、選ばないと何も得ない、シールド0枚では選択自が出ない、付与された誘発がブロックで実際に引く＝対照実験つき、no_leave の付与と解除を実挙動で確認）。
- 再変換ラウンド202: reopen 16件 → **新規登録13件**（dm28-026 / 031 / 032 / 037 / 046 / 075 / 091 / 096、dm29-036、dmex03-004、dmc68-010、dmbd18-se06、28-sec001）＋差し戻し3件。28-sec001 は同一カード（不滅の精霊パーフェクト・ギャラクシー）の別刷りで、dmbd18-se06 の登録に alias として取り込まれた（submit の原文チェックは同一刷りを canonical 行に畳むため、28-sec001 単体では提出できない）。差し戻し: dm26rp1-s001 → shield_hand_shieldize_trigger（SF の全体 no_leave は partial に残した）、dm28-049 → draw_replacement_double（SF の選択だけ partial に残した）、dm31-s01 → g_castle（進化と SF の全体コスト増は partial に残した）。converted 9,182枚、rejects 3,347件、重なり0、漏れゼロ（alias 込みで確認）。dmex16-080 は行に reason が無く reopen 対象外のため残置（shield_force の残りは実質この1件と、複合 gap の dm24ex3-tf16 等のみ）。
- 変換で使った形: パワーアタッカーは mod {power_when: {amount, when: attacking}} と grant の併記。全体付与は affects {zone: bz, owner: you, filter}＋sforce。全体コスト増（dm31-s01）は affects {zone: hand, owner: any, filter: {types: [creature], not_civs: [light]}}＋mod {cost: 4}。相手クリーチャー全てを山札へは move count: all の後に {op: shuffle, player: opp}。

## 第167弾: G・G・G（手札1枚以下を条件とする能力群）— エンジン修正2点（2026-11-11）
G・G・G の条件は手札数の count 式 {cmp: [{count: {zone: hand, owner: you}}, "<=", 1]}（第3段で既存可と裏取り済み。T271 が自分自身の軽減形の先例）。常在型・誘発型の if、op if の cond、free_if に置いて表す。新語彙なし。エンジン修正は2点。
- 修正1（combat._battle_bonus）: 条件つき常在型の battle_power の if を見ていなかった。chars の集約と同じく _static_cond で見るようにした。従来は「相手のターン、バトル中+4000」（dmr09-031）が自分のターンでも効く、「相手のシールドが2つ以下なら自分の自然のクリーチャーすべてのパワーをバトル中+5000」（dmr17-054）は affects が self でないためそもそも _battle_bonus の対象外、という潜在不具合があった。後者（他者への battle_power）は本弾の対象外で、dmr17-054 の不具合として残る（affects 側の集約が別途要る）。
- 修正2（turn._play_options の free_if）: G・ゼロ呪文の「コストを支払わずに唱えてもよい」は free_if で登録されている（dm23rp1-t10 等15枚）のに、:free 選択肢はクリーチャーにしか出ず、呪文は無料で唱えられなかった。呪文も同じ条件で :free を出すようにした（下の cast_free 許可の分岐が重複を弾く）。マスターG・G・G（dmex07-m08）はこの free_if 形で表す。alt_cost {cost: 0, civs: [fire]} は _mana_choices が文明分のマナ1枚を要求するため「支払わず」にならない（civs: [] なら無料になるが、G・ゼロ呪文の確立した idiom は free_if）。
- 形の整理: 自分自身の軽減は zone: hand＋affects: self（T271）。種族など群れへの軽減は発生源がバトルゾーンにいて affects: {zone: hand, owner, filter} で届く形（zone: hand＋affects 辞書はどの集約経路にも載らないため使えない。T317 で確認）。「クリーチャーを攻撃中」のパワーは battle_power {amount, only: attacking}、「バトル中」は battle_power {amount}（only 無しは攻撃・防御の両バトル）。「攻撃できない」は if {手札数 > 1}＋mod {deny: [attack_player, attack_creature]}（第161弾の型）。呪文の1体／すべて分岐は op if（then: count: all／else: count: 1）。
- proto T314（付与スピードアタッカー）/ T315（攻撃誘発ブロッカー破壊）/ T316（攻撃禁止）/ T317（種族軽減）/ T318（バトル不壊）/ T319（バトルパワー+3000）/ T320（攻撃時バトルパワー+10000 only: attacking）/ T321（マスターGGG呪文 free_if）/ T322（分岐呪文）/ T323（パワーアタッカー+5000とW・ブレイカー付与）。tests/test_vocab_pilot167.py 11件（各形態の実挙動＋対照実験。修正1の判別は T319 の手札2枚側、修正2の判別は T321 の手札2枚側で確認済み。攻撃不能だと攻撃決定自体が自動パスされるため、T314/T316 は T005 を別に置いてターン1の攻撃決定を出させる。軽減の有無は _play_options の直接照会で見る（出せないとメイン決定自体が現れない）。T320 の防御側はブロッカーではないため、タップ状態で攻撃される形で見る。ターン開始のアンタップを避けるため最初の決定でタップし直す）。
- 再変換ラウンド203: reopen 17件 → **新規登録14件**（dmex02-050 / 054、dmex03-s07、dmex07-m08、dmrp06-050 / 083 / 084、dmrp07-022 / 047 / 084 / s08、dmrp08-025 / 085 / 087）＋差し戻し3件。dmrp06-s08 → attack_target_unchangeable（「攻撃先は変更できない」に語彙なし。GGG の battle_power と相手呪文／能力による捨て置換2本は partial に残した）、dmrp08-008 → top_card_play_permission（山札の上から1枚目を見て召喚／唱える持続的許可。CIP の全捨ては partial に残した）、dmrp08-047 → per_creature_battle（「1体につきバトルさせる」の繰り返し。基本の+2000と1対1バトルは partial に残した）。converted 9,196枚、rejects 3,333件、重なり0（plain id。alias 込みで5件の既存 stale 重なりあり：dm05-014 / dm01-008 / 31-sec001 / 32-sec001 / 28-sec002 は HEAD~1 時点から存在し本ラウンド起因ではない）、漏れゼロ。g_g_g は全解消。dmex02-054 の alias dmrp06-085、dmrp06-050 の alias promoy17-034 も登録に含まれる。

## 第168弾: フォートE（召喚時にマナの指定種族をタップしていたら能力を得る）— 召喚時タップ記録（2026-11-11）
フォートEは「このクリーチャーをバトルゾーンに出した時、＜種族＞を自分のマナゾーンでタップしてこのクリーチャーを召喚していた場合、このクリーチャーは次の能力を得る」。得る能力は、出た時誘発（得たその出た時に誘発する）・常在型のどちらもあり、1枚に2条項あるものもある。実装は O・ドライブ（第47弾）と同じ作法。
- 記録: 召喚時の支払いでタップしたマナを `Card.summon_tapped` に種族のスナップショットつき（`{ref: [cid, gen], races: [...]}`）で刻む。記録する支払いは通常支払い＋バズレンダ追加＋O・ドライブ追加タップ。ハイパーエナジーでタップしたバトルゾーンのクリーチャー（`t["tap"]`）はマナではないので含めない。無料召喚では記録は空（条件は不成立）。ゾーン移動で消え、移動イベントに載せて出し直す（odrive と同じ。`turn.h_play` の刻印＋イベント引き渡し＋`events._apply_one` の再刻印＋`core._raw_move` のクリア）。
- ゲート: 能力フラグ `fort_e: {races: [...], as?: 変数名}`（defs ABILITY_KEYS に追加し、辞書形・races 非空・as は文字列のみ許可。schema は再生成で追随）。`core.abilities()` で、召喚時に指定種族のマナをタップしていた時だけその能力を機能させる。種族は召喚時のスナップショットで照合する（タップしたマナが後から動いても、召喚という出来事の条件は変わらないため）。得た出た時誘発は、移動イベントの収集時に既にゲートが開いているので、その出た時に誘発する。
- 参照: `as` を書くと、誘発の収集時に条件に合ったタップ済みマナの参照を変数に束ねる（`events._collect_triggers`）。「タップした〜のいずれかよりパワーが小さい」は `power_of`（複数参照で最大値）を当て、`power_le: {sum: [{power_of: {ref: 変数}}, -1]}` で書く（`power_lt` はフィルタに無い）。
- proto T324（出た時ドロー）/ T325（常在型スピードアタッカー付与）/ T326（参照・破壊）/ T327（二条項・ドラゴン＋ヒューマノイド）/ T328（進化召喚）/ T329〜T332（マナ要員: ドラゴン3000・ドラゴン5000・非ドラゴン・ヒューマノイド）。tests/test_vocab_pilot168.py 8件（parse、不正形の拒否、誘発はドラゴンをタップした時だけ、常在型はドラゴンをタップした時だけ、参照は最大値で見る判別（相手3000は破壊・相手5000は残る）、二条項の独立、進化召喚、記録はゾーン移動で消える）。
- 判別確認: ゲートを外すと対照4件が落ちる、刻印を外すと肯定6件が落ちることを確認済み（復元後は全通過）。判別確認中の `git checkout dmsim/engine/turn.py` で turn.py の未コミット変更を一度消してしまった（再適用しテストで復旧を確認）。教訓: 未コミット変更のあるファイルを checkout で戻さない。
- 再変換ラウンド204: reopen 15件 → **新規登録15件**（dm20-015 / 021 / 024 / 048 / 052 / s03、dm21-010 / 017、dm22-040、dm24ex1-039、dmx12b-059、promoy5-034、sp-017、dm20-006 / 009）、差し戻し0。converted 9,211枚、rejects 3,318件、重なり0（plain id。alias 込みの既存 stale 重なり5件はラウンド203から存在し本ラウンド起因ではない）、漏れゼロ。fort_e は全解消。dm24ex1-039 の alias dm20-003、dmx12b-059 の alias dm20-005 も登録に含まれる。使った形: dm20-s03 の FE1（ブレイクしたシールドの S・トリガー封じ）は fort_e 誘発→modify gain（置換 break subject: self、continue: true、instead で strigger off）duration: end_of_turn、FE2 は fort_e 誘発→op break（wiki の「cipでのシールドブレイク効果」）。dm21-010/017 は as 束ね＋power_of 最大値。dm20-024 は各プレイヤー repeat＋may（player 指定）。dm20-009 の「プレイヤーをひとり選ぶ」は modal の自分/相手モード（手札枚数は choose で束ねて {var: h} で引く）。promoy5-034 のシールド交換は dm03-042 型＋戻す移動に strigger: "off"（dm03-042 では未対応だった制限を今回の語彙で表した）。sp-017 の攻撃誘発 +4000 は power_when の常在型に正した。

## 第169弾: サバキZ（裁きの紋章）— 紋章判定＋手札誘発＋呪文のシールド置換（2026-11-11）
サバキZは「裁きの紋章が自分のシールドゾーンから手札に加えられた時、そのカードを捨ててもよい。そうしたら、このカードをコストを支払わずに出す」。裁きの紋章＝シールドの上に表向きに置かれたカード（束のトップで下にカードがあるもの、または束の下にいる表向きのカード。単独の表向きシールド＝ギャラクシールドは紋章ではない）。
- 判定: 移動レコードに `emblem: true` を刻む（`events._apply_one`。トップは移動前の face_up＋下のカードありで判定、下のカードは自身の face_up で判定）。`when` に `emblem: bool` を追加（defs 検証＋schema 再生成）。シールドの束は一緒に動く（第148弾の stack_on に加え、シールド→シールド以外への移動で下のカードにも host 付き move レコードを出す。バトルゾーンへ出る時とシールド内の置き直しは除く）。シールドの数は束で1つなので、下のカードの分は `shield_left` 履歴に数えない。
- 誘発: `kind: trigger, zone: hand, when: {event: move, from: shield, to: hand, emblem: true, subject: {owner: you, other: true}}`。`other: true` は紋章がこのカード自身の場合を除く（自身を捨てて自身を出すことはできないため、誘発自体を起こさない。実プレイと等価）。効果は `op: if`（`exists: {ref: event.subject, zone: hand}` で解決時にまだ手札にあることを確認）→ `op: may` → `discard {ref: event.subject, zone: hand}` → `play_free {ref: self}`。discard はマクロ（move→墓地 reason: discard）。ref＋zone の併記は従来 zone が無視されていたが、本弾で素の読みどおりに絞るようにした（`selectors.candidates` の ref 経路）。
- 面未定ツインパクトの誘発: 手札のツインパクトは面が未定（face -1）のため、従来の `abilities()` 経由では誘発が拾えなかった。`events._trigger_abs` を新設し、面未定の時は各面の能力を面つきで列挙する（pending 解決時に `face` を付ける。once_per_turn／first_time のキーにも面を含める）。面が決まっている時は従来どおり。
- 欠陥と修正（2026-11-11・回帰で発覚）: 面を持たないカードはバトルゾーンでも face が -1 のままなので、初版の `_trigger_abs` は src 経路でゲートなしの素の能力に落ち、fort_e のゲートが素通りした（第168弾の対照3件が落ちた）。面なしカードの src 経路はゲートつき `abilities()` を使うように修正（ab_face は None のまま）。判別: 修正前は pilot168 の対照3件が失敗、修正後は pilot164〜169（51件）＋mechanics（16件）が全通過。
- 呪文の置き換え: 「この呪文を自分の手札から唱えた後、墓地に置くかわりに自分のシールド1つの上に表向きにして置く」は `kind: replace, zone: hold, when: {event: move, from: hand, to: graveyard, reason: resolve, subject: self}`＋`instead: [move {ref: self} to: shield, face_up: true, stack_on: {zone: shield, owner: you, count: 1}, reason: put]`。zone: hold は確立した idiom（dmsd07-011 憤怒スル破面ノ裁キ、革命０各カードの「唱えた後、墓地に置くかわりに〜」が同じ形。唱えている間カードは hold にいる）。from: hand は先行例には無い厳密化（墓地等から唱えた時は置換しない。テキストの「自分の手札から唱えた後」どおり）。シールドが無い時のガードは付けない（先行例と同じ。置換できず hold に残ったカードはターン終了時（512.1）に墓地へ行く）。
- 付随する形（既存語彙）: 山札の上から1枚目をシールドの上に表向きに置く＝同じ move（stack_on＋face_up）。「シールドゾーンにカードが置かれた時」は `when: {event: move, to: shield, subject: {owner: you}}`＋次に使うカードのコスト軽減は `modify {cost_may: {amount, min: 0, once: true}}`（duration: end_of_turn、dynamic: true、dm23rp1-021 型）。「次の自分のターンのはじめまで、〜した時」は `delayed_trigger`（duration: until_next_own_turn_start、繰り返すものは once: false）。ブレイク置換は第146弾の形（`when: {event: break, player: you}`、諮問 env の変数 `shield`＝束の ref 列、`{ref: shield, filter: {face_up: true}}` で束の中の表向きカードを指す）。表向きカードの数えは `count: {bundle_of: {zone: shield, owner: you}, filter: {face_up: true}}`（束の下も含む。zone: shield だけだとトップしか数えない）。
- proto T333（サバキZ呪文・ドロー＋置換）/ T334（サバキZ獣・ブロッカー）/ T335（紋章・無能力）/ T336（シールド回収呪文・strigger: off）/ T337（CIP 山札上→シールド表向き）/ T338（ブレイク置換で裏返し＋表向き3枚以上で不壊）/ T339（メタリカ兵）/ T340（ブレイク呪文）。tests/test_vocab_pilot169.py（parse、不正形の拒否、呪文は唱えた後に表向きでシールドの上へ、シールドが無ければ墓地へ、紋章が手札に入るとサバキZ獣を無料召喚、断れば手札に残る、紋章が自身なら誘発しない、CIP の山札上→シールド表向き、ブレイク置換で表向きカードを裏返し・シールドは残る、表向き3枚で不壊・2枚では不壊でない）。

## 第170弾: crossed_state（クロスギアがクロスされている状態）— フィルタ・セレクタ・式・op（2026-11-11）
クロスギア本体の仕組み（crossed 参照・affects: crossed・303.3）は第22弾で既にある。本弾は「クロスされている状態」を条件・数え・選択で扱う語彙で、dm16〜dm17・dm30・dm31 のクロスギア関連 17 件（単独 gap 15 件＋同一 gap の重複 2 件）を解く。
- フィルタ（defs FILTER_KEYS＋selectors.filter_match）: `crossed: bool`（クリーチャー＝ギアがクロスされているか。ギア自身＝クロスされているか）、`crossed_ge` / `crossed_le`（枚数。式値も可）、`crossed_name: <名前>`（その名前のギアがクロスされているか）。lki（離れた後の姿）がある時は離れる前の参照で数える。
- セレクタ（SELECTOR_KEYS＋candidates）: `crossed_to: <ref>`（そのクリーチャーにクロスされているギア）、`host_of: <ref>`（そのギアをクロスしているクリーチャー）。ref は "self"／変数名／セレクタ。
- 式 `{crossed_count: <refspec>}`（そのカードにクロスされているギアの数。破壊された時の LKI 参照＝古い gen にも当たる。ギアの crossed は宿主が離れてもクリアされないため）。`_expr_refs` に参照名 `crossed` を追加（このギアをクロスしているクリーチャー。cost_of / power_of / name_of / races_of 用）。
- mod `breaks_add` の辞書形 `{amount, count}`（「〜1枚につき、さらに1枚ブレイクする」。count は count_spec 経由）。
- 新 op `uncross`（選んだギアの crossed を外す。ギアはバトルゾーンに残る。303.5）。
- 起動コスト `{tap: {ref: crossed}}`（このギアをクロスしているクリーチャーをタップする。combat._activate_options で host を who にする。host が攻撃できない（タップ済み・召喚酔い）時は選択肢が出ない）。
- 再帰防止: `core._chars_busy`（chars() の評価中に特性を計算しているカード。`_chars_calc` が本体を `_chars_calc_body` に分けて try/finally で管理）。`filter_match` は評価中のカードを印刷特性で見る（従来の `_in_static_cond > 1` だけでは、自身の常在型の if が `exists: {ref: self, filter: ...}` で自身を見る時に再帰した。T352 で発覚）。`eval_expr` の cost_of / power_of / name_of / races_of も `_chars_val` 経由で評価中のカードは印刷特性で見る（第145弾の distinct_cost_count と同じ作法。affects フィルタの `races: {races_of: crossed}` が評価中の宿主を指す時に要る）。
- 形の整理: 「クロスされていなければ攻撃できない」は常在型 if `exists: {ref: self, filter: {crossed: false}}`＋deny [attack_player / attack_creature]。「タップされている時」は同じく `exists: {ref: self, filter: {tapped: true}}`。「〜もクロスされていれば」は `exists: {ref: crossed, filter: {crossed_name: <名前>}}`（+4000 の代わりに +12000 は +4000 と条件つき +8000 の2本に分ける）。「同じ種族のクリーチャー」は filter `{races: {races_of: crossed}}`（攻撃誘発は when の subject: {filter: ...}。attack イベントの攻撃者は subject）。「そのクリーチャーとそれにクロスされているギアをすべて〜に置く」は choose で先に束縛してからギア→クリーチャーの順に move する（move の as は移動後の新しい参照を束縛するため、クリーチャーを先に動かすとギアの crossed（古い参照）と合わなくなる）。「破壊された時、クロスされていたギアの数だけ引く」は draw count `{crossed_count: {ref: self}}`。
- proto T341（攻撃禁止）/ T342（タップ時全体追加ブレイク）/ T343（枚数パワー）/ T344・T345（名前ペアの追加ボーナス）/ T346（クロス破壊呪文。filter には types: [creature] が要る。crossed: true だけだとクロスされているギア自身も当たる）/ T347（クリーチャー＋ギアをマナへ）/ T348（G・ゼロ free_if＋全体+1000）/ T349（同種族＋1000と攻撃時ドロー）/ T350（タップ無しクロスを攻撃可）/ T351（CIP で uncross）/ T352（4枚以上で離れない）/ T353（破壊時クロス枚数ドロー）/ T354（起動・クロス先タップ）/ T355（ギアを墓地へ＋ホスト破壊）/ T356（枚数追加ブレイク）。tests/test_vocab_pilot170.py 17件（parse、不正形の拒否、各形態の実挙動＋対照実験）。
- 判別確認: dmsim/ の変更を退避すると 17件中16件が失敗（parse 時の DefError 等）。回帰は pilot22・32・161〜169＋cross（94件）が全通過。

## 第171弾: attack_redirect（攻撃先の変更）— 起動型リダイレクト＋「可能ならクリーチャーを攻撃する」（2026-11-11）
攻撃先の変更は2つの型がある。起動型（青守銀モルゲン型）と「可能なら」型（誘引・強制型）。

- 起動型: 「このクリーチャーをアンタップして、相手クリーチャーの攻撃先をこのクリーチャーまたは自分のタップしているクリーチャーに変更してもよい。」activate 能力の cost に `{untap: self | <filter>}` を追加し、能力に `redirect: true | {include_cost?: bool}` を持たせる（defs 検証: untap は tap/under/tap_mana と併用不可、untap には redirect が要る、redirect と effect の併用は不可、redirect は activate だけ）。
  - 標準形（dmrp01-061 型）: `{kind: activate, cost: {untap: self}, redirect: true}`。新しい攻撃先はコストのクリーチャー＋自分のタップしているクリーチャー。
  - タップのみ形（dmr23-s01 型）: `redirect: {include_cost: false}`。新しい攻撃先は自分のタップしているクリーチャーだけ（コストでアンタップした自身は対象にならない）。
  - フィルタコスト形（dmrp10-s02 型）: `cost: {untap: {types: [creature], tapped: true}}`。自分のタップしているクリーチャー1体をコストにし、新しい攻撃先はそのクリーチャー＋自分のタップしているクリーチャー。
  - 条件つき形（dmrp07-061 型）: 能力の `if` に `{cmp: [{count: {zone: bz, owner: you, filter: {types: [creature]}}}, ">", {count: {zone: bz, owner: opp, filter: {types: [creature]}}}]}（「自分のクリーチャーの数が相手より多ければ」）。
  - 解決: 攻撃タスクのブロック前（ph 2 開始時）に防御側へ諮問する（`combat._redirect_options`、決定種別 `redirect`、選択肢キー `redirect:<能力持ち>:<能力添字>:<コスト>:<新攻撃先>`＋`decline`）。選ばれればコスト（アンタップ。タップのコストと同じくイベントは出さない）を払って `t["target"]` を書き換え、もう一度諮問する（別のクリーチャーの変更も同じ攻撃で使える）。断ればブロックへ進む。attack_on の履歴は宣言時のまま書き換えない（ブロック／ガードマンと同じバンドAの既定）。タスクの形は `AttackTask.redirect_done`、選択肢の追加フィールドは `Option.payer`。
- 「可能なら」型: 「相手のクリーチャーが攻撃する時、そのクリーチャーは可能ならこのクリーチャーを攻撃する」は第51弾の mod `must_be_attacked: true` で表す（dmx17-s03）。「このクリーチャーがタップされていて」は常在型の `if: {exists: {ref: self, filter: {tapped: true}}}` を足す（dmx22a-005。第170弾の「タップされている時」の形）。
- 「可能ならクリーチャーを攻撃する」（対象は任意のクリーチャー）: 新 mod `must_attack_creature: true | {first_only: true}`（defs は must_be_attacked と同じ検証）。攻撃側の特性として集約し（`chars` に `must_attack_creature` / `must_attack_creature_first`、ダイナモの伝播も対応）、`combat._attack_options` で攻撃できるクリーチャーがいればプレイヤーへの攻撃選択肢を落とす。特定の誘引（must_be_attacked）があればそちらが優先する。`first_only` は第160弾と同じく攻撃側クリーチャー単位の初回攻撃だけ（dm26sd1-m001 の「各ターン、相手のクリーチャーがはじめて攻撃するなら」と同じ読み。dm25ex4-s05 型は発生源の常在型 `{kind: static, affects: {zone: bz, owner: opp, filter: {types: [creature]}}, mod: {must_attack_creature: {first_only: true}}}` で相手クリーチャーに付与する）。検討した別案（自分のクリーチャー全員への must_be_attacked {first_only} の集団付与）は挙動は等価だが、読みが「このクリーチャーを攻撃しなければならない」に寄るため、攻撃側の制限として素直に読める新 mod を採用した。
- proto T357（標準・モルゲン型）/ T358（タップのみ・s01型）/ T359（フィルタコスト・s02型）/ T360（条件つき・dmrp07-061型）/ T361（誘引・dmx17-s03型）/ T362（タップ誘引・dmx22a-005型）/ T363（初回強制・dm25ex4-s05型）/ T364（常時強制・対照用）。tests/test_vocab_pilot171.py 18件（parse、不正形の拒否、自己・他タップ・2回連続のリダイレクトとバトル結果、アンタップされていない時の不出現、include_cost の有無、フィルタコスト、条件の真偽、誘引・タップ誘引、初回強制の初回限定・攻撃後解除・クリーチャー単位、常時形との対照、「可能なら」不成立時のプレイヤー攻撃）。
- 判別: 各テストは肯定・否定の対照実験で組んである（リダイレクトは untap 時の不出現、T358 は対象の有無、T360 は条件の真偽、T363 は初回後・他クリーチャー先行・常時形との対照で判別）。回帰は pilot51・159〜161・164〜170＋cards（88件）、mechanics（16件）、attacked／cross／unblocked／file_schemas（13件＋1 skip）が全通過。
- schema.py の cost に `untap` を追加し `python -m dmsim.schema > data/schema/card.schema.json` を再生成（差分は must_attack_creature・untap・redirect の3点のみ）。

## 第172弾: recycle（リサイクル）— 墓地からの代替コスト唱え＋解決後は山札の一番下（2026-11-11）
リサイクルは「この呪文を墓地からコストNを支払って唱えてもよい。そうして唱えた後、墓地に置くかわりに自分の山札の一番下に置く」。新形は「リサイクル [ll04]」のように文明2文字＋数字2桁で書く（[ll04]＝光マナ2枚を含むコスト6。以下 [ww04]＝水2枚、[dd04]＝闇2枚、[ff04]＝火2枚、[nn04]＝自然2枚）。
- 面フィールド `recycle: {cost: int, civs?: [civ...]}`（defs 検証: 辞書形・cost は int・civs は既知の文明のみ。schema は再生成で追随、差分は recycle のみ）。civs 省略時はカード自身の文明（alt_cost と同じ支払い規約。`_mana_choices` の civs 省略時は面の civs が要る）。新形は `recycle: {cost: 6, civs: [light, light]}` のように書く（`_mana_choices` は civs の各要素を別々のマナ1枚で満たすので、同じ文明の重複＝その文明のマナ2枚）。
- 唱え: `turn._play_options` に墓地ブロックを追加（ムゲンクライム／フシギバースと同じ作法。面ごと・呪文だけ・`permits(cid, "cast")`・`_mana_choices(cost=recycle.cost, civs=recycle.civs, limit=1)` で払える時だけ）。選択肢キー `play:<defn>:recycle`（面つきは `play:<defn>:<face>:recycle`）、Option に `recycle: true` を追加（types.py の Option・PlayTask にも同名フィールドを追加。DMSIM_CHECK=1 では未知キーが TypeError になるため）。`st_main` で `task["recycle"]=True`＋`cost_override`／`cost_civs` を立てる（alt と同じ）。`h_play` の呪文分岐で、recycle の時だけ `t["resolve_to"]="deck"`＋`t["resolve_position"]="bottom"` にし、解決 env に `recycle_paid`、cast イベントに `recycle` を載せる（alt_paid／vivid と同じく、将来の「リサイクルで唱えたなら」用）。
- 行き先の区別: 手札からの通常唱えとアタック・チャンスの無料唱え（`play_free` は recycle の印を付けない）は従来どおり解決後に墓地へ行く。リサイクルで唱えた時にだけ山札の一番下へ行く。
- 置換 idiom（第169弾の zone: hold の replace）を使わなかった理由: 置換は「墓地から唱えて墓地へ行く」移動すべてに反応するため、リサイクル以外の経路（play_free 等）で墓地から唱えた時にも山札の下へ行ってしまい、テキストの「そうして唱えた後」（リサイクルで唱えた時に限る）と合わない。タスクの印で行き先を変える方式なら、リサイクル選択肢で唱えた時にだけ行き先が変わる。なお resolve_to を持つカード（チャージャー等）に recycle が付いた場合、リサイクル唱えでは deck/bottom が resolve_to に優先する（対象14枚に該当なし。ラウンド側で注意）。
- 副次修正（既存バグ）: `combat._activate_options` の「tap が無い＝under のみ」分岐が `cost["under"]` を無条件に参照し、untap コスト（第171弾のリダイレクト能力）が攻撃側にあると KeyError になった。under が無い時はその分岐を出さない（untap コストはブロック時の redirect 決定で使うもので、攻撃ステップの起動ではない）。T357 を攻撃側に置く T367 のアタック・チャンステストで発覚・回帰テスト化。
- proto T365（古典③・水・ドロー・dmd24-033型）/ T366（古典⑧・自然・マナブースト2・dmex03-068型）/ T367（新形[ll04]・光・シールド化＋アタック・チャンス・dm26rp2-031型）/ T368（古典②・火・ブロッカー破壊・dmr16g-049型）。tests/test_vocab_pilot172.py 11件（parse、不正形の拒否、墓地から唱えて山札の下へ・払えなければ選択肢に出ない・手札からは選択肢に出ない・手札から唱えると墓地へ・⑧とマナブースト・[ll04]の文明不足と充足・ブロッカー破壊・アタック・チャンスの無料唱えは墓地へ）。
- 判別確認: 選択肢の列挙を止めると肯定4件が落ちる、行き先の刻印を外すと肯定4件が落ちる（いずれも復元後11件全通過）。回帰は pilot29・53・56・57・149・165・167・169〜171＋cards、cost、mechanics、file_schemas、engine（137件＋1 skip）が全通過。
- テスト作成の注意: setup 直後のマナはタップ状態なので、`_play_options` を直接呼んで選択肢の有無を見てはいけない（ターン開始のアンタップ前で払えない判定になる）。実決定まで進めてメイン決定のキーを見るか、唱えまで駆動すること（`_main_keys`／`_drive` の作法）。

## 第173弾: deck_evolution（デッキ進化）— 山札の上からめくって重ねる進化＋固定の進化元（2026-11-11）
デッキ進化は「自分の山札の上から1枚目を見る。それがクリーチャーなら、このクリーチャーをその上に重ねて出す」進化（801 進化の下位形。総合ゲームルール Ver.1.53 に単独の条文はなく、進化の手続きとして扱う）。Mデッキ進化は3枚見て1体を選び、残りは墓地へ。OMGデッキ進化は山札をシャッフルしてから一番上を裏向きのまま重ねる（種類を問わない）。
- 面フィールド `deck_evolution: {count?, rest_to?, blind?, shuffle_first?}`（defs 検証: 辞書形・count は 1 以上の int・rest_to は既知ゾーン・blind／shuffle_first は bool。`True` は `{count: 1}` に正規化。schema は再生成で追随、差分は deck_evolution ×2 と move の `evo_source`）。`{count: 1}`＝デッキ進化、`{count: 3, rest_to: graveyard}`＝Mデッキ進化、`{count: 1, blind: true, shuffle_first: true}`＝OMGデッキ進化。
- 召喚: `turn.h_play` の進化分岐にデッキ進化サブ分岐を追加。めくりは**支払いの前に**行う（通常の進化元選択も支払いの前に行う作法に合わせる）。失敗（候補なし）ならカードは手札に残り、マナは払わない。shuffle_first なら先に `eng._shuffle(p)`、blind でなければ公開（`note_public("reveal")`）。候補が1体だけなら選択は出ない（1候補＝自動）。2体以上なら `choose_cards` で選ぶ。残りは `rest_to` へ（M のみ）。通常の bz 進化元選択ブロックは `else:` 化し、デッキ分岐からフォールスルーしない。
- 進化元選択の可否: `_can_play_face` は山札が空でなければ、めくりの結果にかかわらず召喚を試みられる（コストは `cost_reduce_per_evo` を n=1 で適用）。なおこのエンジンは 703.4b で山札0枚を SBA 敗北とするため、空山札で main に到達することはなく、チェックは防御。
- 固定の進化元 `evo_source`: move op に `evo_source="selector?"` を追加（`Checker.ops` の組合せ検査: `move.evo_source` は `stack_evo: true` を要求）。`op_move` の stack_evo 分岐が `task["evo_source"]` を `put_stacked` へ転送し、interpreter の `h_put_stacked` が `t["evo_source"]` を優先する（bz にあり `filter_match` で evolve_from に合う時のみ有効。無効ならそのカードは出さない＝従来の無元と同じ）。`PutStackedTask` にも `evo_source` を追加（DMSIM_CHECK=1）。用途: 「このクリーチャーの上に置く」検索型の重ね出し（dmc64-036/042 型）。進化V のリスト形 evolve_from との併用は未対応（制限として記録）。
- 既存の誤変換の指摘（ラウンド209の範囲外。直さず記録のみ）: すでに converted の dmc64-020 ワンケングレンオー～全速前進～ と dmc64-031 ケングレンオー～水遊び～ は、テキスト「このクリーチャーの上に置く」を `put_under` で書いているが、`put_under` は選んだカードを onto の**下**に置くため逆向き。同じ「上に置く」は move＋`stack_evo`＋`evo_source` が正しい（第173弾で追加）。他の `put_under` 使用箇所はすべて正しい「下に置く」。
- proto T369（dm32-029型・デッキ進化＋条件付きパワー）/ T370（dm35-048型・デッキ進化）/ T371（dmc58-003型・Mデッキ進化）/ T372（dmex17-037型・OMGデッキ進化）/ T373（dmc64-042型・起動で山札から固定進化元へ重ねる）＋T374（その進化先）/ T375（dmc64-026型・デッキ進化＋下のカードの破壊時誘発。from_under は第156弾の仕組み）/ T376（dmrp17-023型・CIP で上4枚を見て進化を重ねる。残りは山札の下へ）＋T377（その進化先）。tests/test_vocab_pilot173.py 14件（parse、不正形の拒否、デッキ進化成功＋条件付きパワー、失敗して手札に残る、めくり失敗で山札が空になるとドロー負け、M成功／M失敗、OMG盲目、固定の重ね出し×3（2体いる時の起動元の判別・対象なし）、下のカードの破壊時誘発、CIP の重ね出し／候補なし）。
- テスト作成の注意: setup の deck 指定は所属だけで順序は保証しない（`_raw_move` の top 挿入で逆順になる）。山札の上から順に並べたい時は `_arrange_deck`（第163弾の流儀）で並べ替えること。山札の枚数は filler 20枚が全ゾーンで共有されるため、spec の枚数から計算する（手札＋マナ＋シールド5枚を引く）。進化で出たクリーチャーは `_stack` が `entered_turn=-1` にする（801.3 召喚酔いなし）ので、出たばかりの判別には `under` の有無を使う。破壊タスクを積む時は待機中 Decision の回答が先に消費される点に注意: 破壊で選択肢が変わる Decision（attack 等）では回答 index が陳腐化する。破壊は手札に影響しない相手の charge Decision で待っている状態で呼ぶこと（`_to_opponent_charge`＋`_destroy_and_answer_may` の作法）。choose の filter で「進化クリーチャー」は `types: [evolution]` と書く（`types: [creature, evolution]` はどちらか一方を持つカードに当たる）。
- 判別確認: deck-evo 分岐を外すと肯定6件が落ちる、evo_source の転送を外すと肯定3件が落ちる（いずれも復元後14件全通過）。回帰は pilot169〜172＋mechanics（87件）が全通過。

## 第174弾: dream_creature（ドリーム・クリーチャーの型印）— エンジン変更なし（2026-11-11）
ドリーム・クリーチャーはカードの「種類」（タイプ）であって、タイプ自体に固有のゲームルールは無い（総合ルールにドリーム・クリーチャーだけの条文はなく、効果がタイプを参照するための印。D2フィールドの型印と同型の追加。第151弾の流儀）。
- defs の CARD_TYPES に `dream_creature` を追加。types は通常 `["creature", "dream_creature"]`、進化 `["creature", "evolution", "dream_creature"]`、G-NEO進化 `["creature", "dream_creature"]` に `neo: true` と書く。ドリームだけを指すフィルタは既存語彙の `{types: [dream_creature]}`（selectors は汎用の集合照合のため変更なし）。schema は再生成で追随（差分は型の列挙×2）。Rust 側の変更なし（types は文字列リストで Card フィールドの追加なし）。
- **注意（今回の発見）**: types に `evolution` がある NEO カードは `_can_play_face` が進化元を要求するため通常召喚の選択肢が出ない。進化元なしでは main の選択肢が pass だけになり、`ask` が一意選択肢を自動回答するため main 決定自体が出ず、ターンが charge だけ回る。NEO は types に `evolution` を含めない（実例 dm25ex3-011 エリー＝エリザベス: types `[creature]`＋`neo: true`）。T381 は最初 `[creature, evolution, dream_creature]` で書いて test_neo_dream_normal_summon が落ち、修正して通過。ラウンド210の G-NEO 2件（dm25ex3-rp1dm1/rp4dm1）も partial の types `[creature]` のまま `neo`＋`evolve_from` を足す。
- proto T378（ドリーム・クリーチャー。CIPドロー）/ T379（進化ドリーム。火のクリーチャーの上に置く。CIPドロー）/ T380（ドリーム言及。自分のドリーム・クリーチャー全てに+1000、ドリームがあればCIPドロー）/ T381（G-NEOドリーム。neo: true。火のアーマード・ドラゴンの上に置く）。tests/test_vocab_pilot174.py 8件（parse、不正形の拒否、スキーマ、ドリーム CIPドロー、進化ドリーム、ドリーム言及の静的＋exists、NEO通常召喚、NEO進化）＋tests/test_vocab_pilot174_cards.py 1件（rejects の13件の partial に型印を足すだけで parse が通る。G-NEO 2件は neo＋evolve_from を補う）。
- 判別確認: CARD_TYPES から dream_creature を外すと T378 の parse が DefError（unknown type）。回帰は pilot169〜173＋174＋mechanics（96件）が全通過。
- 待機13件（dream_creature 単独ギャップ）。再変換はラウンド210で実施。うち dm24ex2-dm02 / dm25ex2-dm4 / dmartkiwami01-001 は超次元ゾーンに触れるため範囲外で差し戻し見込み。

## 第175弾: accel（アクセル）— クロスギアがクロスされている間だけ得る能力（2026-11-11）
アクセルは「このクリーチャーにクロスギアがクロスされている時、このクリーチャーは次の能力を得る」。能力そのものが条件つきで存在するため、常在型の `if` では誘発・置換を表せない。sforce / fort_e / odrive と同型の能力フラグ方式を採用した。
- 能力フラグ `accel: true`（defs ABILITY_KEYS。`true` 以外は DefError。schema は再生成で追随、差分は accel ×1）。`core.abilities()` が `(not ab.get("accel") or self._accel_active(cid))` で絞る。`_accel_active` は `crossed_gears(self.s.ref(cid))` が空でないかだけを見る（状態だけを見るので chars() の評価中でも再帰しない）。static / trigger / replace のいずれの種別にも付けられる（誘発・置換の列挙は abilities() 経由のためゲートが効く）。
- 静的形は既存の mod で書く（power / grant: [speed_attacker / double_breaker / unblockable] / add_races。sforce の T311 と同じく static に affects は要らない）。誘発形は既存の when で書く（攻撃時 `{event: attack, subject: self}`、ブロックされなかった時 `{event: attack_end, subject: self, target: player, blocked: false}`、破壊置換 `{event: move, from: bz, to: graveyard, reason: destroy, subject: self}`＋instead で `{crossed_to: self}` のギア1枚を墓地へ、ブレイク置換 `{event: break, subject: self}`＋instead で `{ref: event.shield}` を `to: mana` へ）。「よりパワーの小さい」は `power_le: {sum: [{power_of: self}, -1]}`。
- proto T382（静的パワー＋スピードアタッカー・dm28-097型）/ T383（静的パワー＋種族追加・dm15-037型）/ T384（攻撃時ドロー・dmpcd02-a10型）/ T385（ブロックされなかった時バウンス・dm28-083型）/ T386（ブロックされない＋破壊身代わり・dm15-009型）/ T387（ブレイク置換でマナへ・dm15-018型）。tests/test_vocab_pilot175.py 8件（parse、不正形の拒否、各形態の実挙動＋対照実験）。
- 判別確認: ゲートを無効化すると 8件中6件が失敗（parse・不正形の2件以外すべて。復元後8件全通過）。回帰は pilot166〜175＋mechanics＋cross＋file_schemas（133件＋1 skip）が全通過。
- テスト作成の注意: scenario.build は bz 配置のクリーチャーを entered_turn=0（召喚酔いなし）で置くため、スピードアタッカーの判別には entered_turn = e.s.turn で「このターンに出たことにする」必要がある。手札が空だと charge / main が一意選択肢で自動回答されるため、attack 決定まで種別を見て進めること（_attack_player の流儀）。_drive_combat は相手ターンの開始まで進むので、相手の手札は開始ドロー+1を織り込んで相対値で見ること。試験ギアは T100（ホストのパワー・キーワードに影響しない。T343 はホストに+1000するためパワー判定が汚れる）。
- 待機19件（accel 単独ギャップ）。再変換はラウンド211で実施。注意: dm15-009 の partial は keywords に unblockable を素のキーワードとして含んでいるが、これはアクセルの内側の能力なので、ラウンド側で accel 静的に移すこと。dm28-065 は partial が無く（侍流ジェネレート＋アクセル）、dm15-004 は first_attack_of_turn との複合ギャップ。

## 第176弾: g_castle（G城）— 実行したら表向きでシールド化されるカード（2026-11-11）
G城は「（G城は実行したら、表向きでシールド化される。このカードが表向きで自分のシールドゾーンを離れる時、かわりに墓地に置く）」という型ルールを持つカードの種類。能力はシールドゾーンで働く。土台の多くは既存だった（zone: shield の常在型は第15弾のギャラクシールドで、face_up 付きの置く時誘発・シールド束・put_under の onto シールド対応も済み）。
- 型印 `g_castle`（defs CARD_TYPES。第174弾の dream_creature と同型）。「自分のシールドゾーンにある城」は filter `{types: [g_castle]}` で指す。schema は再生成で追随（差分は型の列挙×2）。Rust 側の変更なし（types は文字列リスト）。
- 実行: 面が g_castle なら通常の実行が表向きシールド化になる。`turn.h_play` の to_shield 分岐（ギャラクシールドと同型）へ `d.is_castle()` で振り分ける（FaceDef・CardDef 両方に `is_castle()` を追加。面なしカードは `face()` が自身を返すため両方要る）。play_task を作る全経路（メイン・S・トリガー・無償実行）で同じ振る舞いになる。実行アクションは "generate"（タマシード等と同じ「実行」。`_can_play_face`・`_climb_ready`・`h_play` の3か所の判定式に `or is_castle()` を足す）。G城は PERMANENT_TYPES には入れない（バトルゾーンには出ないため。`h_play` の `is_permanent()` 分岐に落ちると呪文解決になってしまうのを避ける）。
- 型ルール「表向きで離れる時、かわりに墓地に置く」は、シールド・ゴー（keywords.yaml）の2つ目の置換と同型の replace 能力として、types に g_castle を含む面すべてに `_load_face` で自動で付く（データ側に書かない。`keyword="g_castle"` の印つき）。`{kind: replace, zone: shield, when: {event: move, from: shield, subject: self}, if: {face_up: true}, instead: [{op: move, select: {ref: self}, to: graveyard, reason: put}]}`。置換の諮問は既存の `_replacement` がシールドゾーンのカードと動くカード自身を走査するため、そのまま働く（ブレイク時の shield→hand 移動もここで拾う。単一・非任意の置換は諮問が一意選択肢で自動回答される）。
- 離れる時のレコード: `events._apply_one` が、シールドを表向きで離れた時もレコードに `face_up: true` を載せる（従来は表向きで置く時だけ。`ev.get("face_up") or (from_zone == "shield" and was_face_up)`）。これで「表向きで置かれた時または離れた時」誘発を when の face_up で書ける。既存の when face_up はすべて to: shield の置く時誘発なので挙動は変わらない（converted・proto を全検索して確認）。
- シールドゾーンの能力の書き方（シールド・ゴーの流儀）: 静的・非移動誘発は `zone: shield` + `if: {face_up: true}`、置く時／離れる時誘発は `zone: shield` + when の face_up: true。裏向きでシールド化された G城に能力は働かない（コスト軽減は `pay_cost` で見る。`cost` は「コスト5以下」等の参照用で変わらない）。
- proto T388（静的コスト軽減・dm26ex4-085型）/ T389（置かれた時ドロー・dm26rp1-023型）/ T390（置かれた時または離れた時バウンス・dm26rp1-002型。原文は「好きな数」だが proto は１体に簡略化）/ T391（置かれた時シールド下置き・dm26rp1-001型。`put_under` の onto は `{ref: self}`、下のカードは裏向きになる）/ T392（攻撃時自己墓地＋手札出し・dm26ex1-n022型。ブロッカー／スレイヤー付与とメカ指定は省略）/ T393（初回破壊時ドロー・dm26rp1-067型。`first_time: true`）。tests/test_vocab_pilot176.py 11件（parse、不正形の拒否、実行→表向きシールド化、静的軽減の表向き／裏向き対照、置かれた時ドロー、ブレイクで墓地へ＋裏向き対照、出入り誘発、下置き、攻撃時誘発、初回破壊ドロー）＋tests/test_vocab_pilot176_cards.py 1件（rejects の21件の partial に型印を足すだけで parse が通る）。
- 判別確認: 型ルールの自動展開を外すとブレイク試験が失敗、シールド化振り分けを外すと実行試験が失敗、離れる時の face_up レコードを外すと出入り誘発試験が失敗（いずれも復元後12件全通過）。
- テスト作成の注意: 単一選択肢の決定（pay_mana の組合せが1通り、pass だけの main / attack、非任意の単一置換）は自動回答されるため、1回の advance() が複数ターン分進むことがある。_settle は done() を advance の直後にも見る（満たされた直後の決定は答えずに止める。答えてしまうとメインを pass してターンが進み、手札枚数などの前提が崩れる）。ターン開始ドローが入るため手札枚数の厳密な assert は避け、ゾーンで assert すること。T005 はダブル・ブレイカー（2ブレイク）なのでブレイク試験では choose_shields を min 枚ちょうど選ぶ（選択肢のキーはすべて 'shield' なので cid から defn で選ぶ）。setup 直後のタップ指定は相手ターンの開始アンタップで解けるので、離れた時誘発の対象はプレイ段階の後に改めてタップすること。
- 待機21件（g_castle 単独ギャップ）。再変換はラウンド212で実施。注意: dm26rp1-057 のブレイク置換節（「シールドを２つ以上ブレイクする時、かわりにこのシールドをブレイクさせる」）は shield_break_replacement 語彙が要るため差し戻し見込み。dm31-s01 はシールド・フォース持ちのクリーチャーで「自分のシールドゾーンにある城」を数える（filter types: [g_castle]）。古典の城（要塞化）は別メカニズムのため本弾の対象外（castle 10＋castle_fortify 12は別パイロットで扱う）。out_of_game 23件（未開封パックを開ける等）は物理パックを使うため実装不能で対象外。duelist_link 20件は超次元ゾーンに触れるため範囲外。

## 第177弾: choukon_raid（超魂レイド）— 山札の上3枚から進化元を1枚下に置く（2026-11-11）
超魂レイドは「このクリーチャーが出た時、山札の上から3枚を表向きにする。その中からこのクリーチャーの進化元になれるカードを1枚、この下に置いてもよい。残りを好きな順序で山札の下に置く」。土台は既存語彙で足りた（reveal_until＋put_under＋move の order: choose）が、「進化元になれる」の照合だけが無かった。
- 新フィルタキー `evo_source_of`（defs FILTER_KEYS。値は `"self"` / 変数名の文字列。schema は再生成で追随、差分は evo_source_of ×3）。`filter_match` に任意引数 `env` を追加し（既定 None。既存の呼び出しはそのまま動く）、`evo_source_of` は env がある文脈でのみ解決する。判定は `_evo_sources` と同型: 候補がクリーチャーであること（非クリーチャーで evolve_base の許可があるものも可。ただし常在型の条件・base 判定中は permits を呼ばずクリーチャー必須）＋対象の `evolve_from`（zone を除く）のいずれかに合うこと。進化V のリスト形も any で扱う。env が無い文脈（常在型の条件・when の照合）では一致しない（安全側の既定）。
- env の受け渡し: `candidates()` 内の全 filter_match 呼び出し（under_of / bundle_of / exlife_of / crossed_to / host_of / ref / zone）と `_turn_count`、および ops.py の3か所（メクレイド・reveal_until・多パート選択）に `env=env` を通す。core / combat / turn / interpreter / events の呼び出しは env を持たないので従来どおり（evo_source_of を含むフィルタはそこで一致しない）。
- 超魂レイドの書き方（CIP 誘発）: `reveal_until {as: pile, filter: {}, count: 3}`（filter {}＝全てに合うので上3枚が hit になり rest は空）→ `if {exists: {ref: pile, filter: {evo_source_of: self}}}` で適格カードがある時だけ `may` → `put_under {select: {count: 1, up_to: true, ref: pile, filter: {evo_source_of: self}}, onto: {ref: self}}` → `move {select: {count: all, ref: pile}, to: deck, position: bottom, order: choose, reason: put}`。下に置いたカードは gen が進むので、残りの move の ref 束縛から自動で外れる（`s.alive` の照合）。order: choose は2枚以上の異なる defn の時だけ並びを聞く。
- proto T394（dm25ex3-046型・civs形 evolve_from）/ T395（dm25bd1-005型・races形 evolve_from。種族は proto の慣例で [テスト]）/ T396（リスト形 evolve_from。dm25ex3-rp2s04型の CIP 破壊も併せ持つ）/ T397（dm26ex4-sec025型・攻撃時2ドロー2捨て付き。墓地からの出し節は省略）。tests/test_vocab_pilot177.py 9件（parse、不正形の拒否、適格カードを下に置く＋残りを選んだ順で山札の下へ、適格なしでは may が出ない、may 拒否、種族形、リスト形、CIP 破壊との共存、攻撃時誘発）＋tests/test_vocab_pilot177_cards.py 1件（rejects の14件の partial に超魂レイドの誘発能力を足すだけで parse が通る）。
- 判別確認: evo_source_of の分岐を無効化すると 9件中5件が失敗（適格ありの4件＋may 拒否。復元後10件全通過）。回帰は pilot160〜177＋mechanics＋cross＋file_schemas（241件＋1 skip）が全通過。
- テスト作成の注意: setup の deck 指定は所属だけで順序は保証しないので `_arrange_deck`（第163弾の流儀）で上から並べ替えること。may は yes/no を聞くので、適格なしの試験では if ガードにより may が出ないことを決定の種類で確認する。order: choose の答えの先頭が、置いたカードの中で一番上になる（山札の末尾2枚＝答えた順）。
- 待機14件（choukon_raid 単独11件＋複合3件）。再変換はラウンド213で実施。注意: dm26ex4-sec025 の partial は `count: {upto: 2}` という未定義形を含んでいる（正しくは `count: 2, up_to: true`）。dm25rp2-050 は summon_from_mana_alt_cost_no_element との複合、dm25ex3-rp2003 は under_creatures_total_cost_put との複合、dm25ex3-rp2dm1 は alt_cost_mana_race_condition との複合で、いずれも本弾では差し戻し見込み。dm25ex3-rp2s01 の破壊時節（下にあったカードを墓地から NEO/進化の下に置くか表向きシールド化）は modal＋put_under/move で書けるかラウンド時に精査する。

## 第178弾: castle_fortify（城・要塞化）（2026-11-11）
城は「バトルゾーンに出る時、自分のシールドを1枚選び、このカードを付けて要塞化する。その要塞化されたシールドがシールドゾーンから離れた時、このカードを自分の墓地に置く。（「S・トリガー」能力を使う場合は、このカードを墓地に置く前に使う）」。シールド・フォース（第166弾）と同型だが、紐付けは城側の単一参照で持つ（1枚のシールドを複数の城が要塞化できるため、シールド側の単一参照では足りない）。
- 状態: Card に `fortifies`（この城が要塞化しているシールドの参照 [cid, gen]。城がゾーンを離れたら外れる。state.py／Rust state.rs・engine.rs・setup.rs を同期）。城の能力はバトルゾーンにある間は要塞化の有無を問わず機能する（城の常在・誘発は通常の bz 能力。シールドが無くて要塞化できなかった城もバトルゾーンに残る）。要塞化は墓地行きルールと「この城を付けて要塞化されたシールド」の参照のためだけに使う。
- 新 op `{op: castle_link}`（ops.py。sforce_link と同型だが選択は必須）: 自分のシールドを1枚選ばせる（0枚なら何も起きない。1枚以上あれば必ず1枚選ぶ）。選んだシールドへの参照を自分の `fortifies` に刻む。カード側は出す時の誘発 `{kind: trigger, when: {event: move, subject: self, to: bz}, effect: [{op: castle_link}]}` を明示で持つ。
- 墓地行きルールは状況起因処理（events.py `_sba_tasks`）: バトルゾーンの城で `fortifies` があり、その参照が今シールドゾーンに無いもの（gen が進んだものも含む）を reason: put で墓地へ。ブレイクの最終 move と同じ apply_batch の `_sba()` で走るため、S・トリガー宣言（h_break phase 1。最終 move の前）より後になり、注記の順序（S・トリガーを使ってから城を墓地へ）を満たす。置換ではないのでブレイク自体は妨げない。
- 「この城を付けて要塞化されたシールド」の参照3種: (1) セレクタキー `castle_of: "self"`（selectors.py。exlife_of と同型。値は "self" / 変数名。要塞化先が今もシールドゾーンにあるものだけを返す）。(2) when の subject 辞書キー `castle_of: "self"`／`castle_only: "self"`（events.py `_subject_match`。後者は「他の城によって要塞化されていなければ」＝要塞化している城が自分だけ）。(3) when の新キー `shield`（events.py `_match_when`。ブレイクの rec["shield"]＝束のトップに `_ref_match` で当てる。`when: {event: break, player: you, shield: {castle_of: self, castle_only: self}}` の形で城のブレイク置換を書く。schema.py の when にも "shield" を追加し schema 再生成）。
- フィルタキー `fortifying`（この城が今シールドを要塞化している）／`fortified`（このシールドがどの城かに要塞化されている。dmex18-017 の「自分の要塞化されたシールド」用。affects の owner: you と組で使う）。
- ブレイク置換の書き方（「この城を付けて要塞化したシールドが…ブレイクされる時、かわりに自分のシールドを１枚手札に加えてもよい」）: `kind: replace, when: {event: break, player: you, shield: {castle_of: self, castle_only: self}}, optional: true, instead: [{op: move, select: {count: 1, zone: shield, owner: you, exclude: {ref: event.shield}}, to: hand, reason: put}]`。instead の選択はブレイクされるシールド自身を exclude する（同じシールドを手札に加える読みは空虚な置換になるため。別シールドを犠牲にするのが趣旨）。
- 要塞化時誘発の書き方（dm34-029「シールドを１枚要塞化した時、相手の手札を１枚見ないで選び、捨てさせる」）: CIP 誘発の effect を `[{op: castle_link}, {op: if, cond: {exists: {castle_of: self}}, then: [<捨てさせる効果>]}]` と書く（要塞化できなかった時は捨てさせない）。dm34-029 の原文「この城を自分のシールドゾーンに置いて」は転記ミス疑い（実カードは「バトルゾーンに出した時」）。ラウンド時に原文を確認する。
- proto T398（dm30-023型・全体+1000とブロッカー付与）/ T399（dmex01-033型・ブレイク置換）/ T400（dm34-029型・要塞化時相手1捨て）/ T401（dmex08-223型・「シールドを要塞化している城」を選んで手札に戻す CIP 選択）/ T402（dm31-011型・要塞化されたシールドに常在で S・トリガー許可を与える。誘発で手札に加わる時に印を付ける形ではブレイクの宣言（最終 move の前）に間に合わないため、常在型＋mod allow: [s_trigger] が正しい形。宣言後の解決はゾーンだけを見るので、城が墓地へ行っても宣言済みの S・トリガーは解決する）。tests/test_vocab_pilot178.py（実挙動テスト。bz は共有ゾーンなので controller も照合）。
- 対象外・見込み: dmex18-017 の「自分の要塞化されたシールドはブレイクされない」はブレイク不能の仕組みが無く、本弾では差し戻し見込み（新ギャップ fortified_shield_unbreakable）。dmr02-009 のサイキック節は範囲外（psychic_filter）で差し戻し見込み。dm35-029 の「ゴッドでなければ山札の下、ゴッドなら出してもよい」節と攻撃時節は既存語彙で書ける見込み。dmex08-223 の第2モード（マナの M・ソウル数以下のコストのカードをバトルゾーンから手札へ）は既存語彙で書ける見込み。
- 判別確認: SBA の城分岐を無効化すると墓地行きの2件（効果でシールドを手札へ／ブレイク）が失敗し、復元後12件全通過。回帰は pilot160〜178＋mechanics＋cross＋file_schemas が全通過。
- 待機22件（castle_fortify 単独12件＋castle 単独10件。同じ要塞化メカニズムで gap 名が2つに分かれている）。再変換はラウンド214で実施。

## 第179弾: ace_tamaseed_conditional_creature（ACEタマシード）（2026-11-11）
ACEタマシードは「自分の、その文明のクリーチャーまたはタマシードが合計4つ以上なければ、バトルゾーンにあるこのタマシードはクリーチャーとして扱わない」。条件を満たす間だけクリーチャーとして扱い、満たさなければタマシードのまま（攻撃・ブロック不可、クリーチャー指定の対象にならない、攻撃時誘発は起きない）。タマシードとしての能力（出た時誘発など）は条件に関わらず働く。
- 面フラグ `ace: true`（defs Face・CardDef。第174弾の dream_creature と同型の型印ではなく、NEO進化と同型の面フラグ）。`ace` は `tamaseed` を含む面にだけ付き、それ以外は DefError（`ace: true` 以外の値も DefError）。schema は再生成で追随（差分は ace ×2）。Rust 側の変更なし（CardDef の Rust 側は面フラグを持たず、未知フィールドは無視される。test_card_fields_match は Card 状態フィールドだけを見るため影響なし）。
- 判定 `core._ace_active(cid)`（accel / sforce と同型の状態だけを見る述語）: バトルゾーンにあり、コントローラーのバトルゾーンにある、そのカードと同じ文明のクリーチャーまたはタマシードが合計4つ以上。自分自身も数える（ACE自身がその文明のタマシード）。数えは定義の特性（fdef）だけで行うため chars() の評価中でも再帰しない。bz は共有ゾーンなので controller で絞る（第160弾の教訓）。
- 特性の上書き `_chars_calc_body`（NEO進化の型追加と同型）: `d.ace and c.zone == "bz"` かつ条件を満たせば `ch["types"]` に "creature" を追加する。攻撃可否（combat._can_attack）、ブロック、フィルタ照合、パワー0の SBA はすべて chars の types を見るため、この1か所で全体が連動する。出たターンは entered_turn が当ターンのため攻撃できない（タマシードとして出た場合も summoning sickness と同じ扱い。第179弾の確認: _raw_move が bz への移動時に entered_turn を刻むため、条件を満たしてクリーチャーになったのが出たターンなら攻撃できず、前のターンに出ていれば攻撃できる）。
- ブロックの型要求（combat.py）: 507.1 によりブロックできるのはクリーチャーだけ。blockers の列挙に `"creature" in eng.chars_ro(c)["types"]` を追加した（従来は permits の allow: [block] だけを見ていたため、ブロッカー印のあるタマシードがブロックできてしまっていた。既存の該当は dm25rp4-024 のみで、テストはこれに依存していない。ガードマン側は今回触らない）。
- 登録形: types は `[tamaseed]` のみとし、クリーチャー性は chars フックで付ける（converted のタマシード110枚すべてが `[tamaseed]` の慣例に合わせる。`[tamaseed, creature]` にすると is_creature() が真になり、手札からの出し方が summon になってしまうため）。dm25sd1-001/003 の partial の `[tamaseed, creature]` はラウンド側で `[tamaseed]` に正規化する。既知の制限: バトルゾーン外ではクリーチャーとして扱われない（公式には印刷タイプがタマシード/クリーチャーのため墓地などではクリーチャーでもあるが、本弾では「バトルゾーンにある」節だけを表す。影響は稀な墓地・手札からのクリーチャー指定のみ）。
- 「〜してもよい」は `{op: may, body: [...]}` で書く（2,514件の慣例）。trigger 能力の `optional: true` は置換（choose_replacement の decline）にしか効かず、誘発の任意性にはならない（T406/T407 は最初 optional で書いて CIP が無条件に発火し、may に直して通過）。
- proto T403（dm22rp1-10b型・自然。CIP マナ4アンタップ＋T・ブレイカー＋攻撃時マナ加速）/ T404（dm22rp1-2b型・光。CIP 相手2体タップ＋ブロッカー＋W・ブレイカー）/ T405（dm22rp1-6a型・火。CIP パワー4000以下破壊＋スピードアタッカー＋攻撃時他のクリーチャーに+6000）/ T406（dm23sp1-006型・闇。CIP 任意で山札の上4枚を墓地へ＋ブロッカー＋T・ブレイカー＋攻撃時破壊＋自ターン中の no_leave {except_destroy}）/ T407（dm22rp1-3a型・水。CIP 任意で3ドロー2捨て＋ブロッカー＋W・ブレイカー）。tests/test_vocab_pilot179.py 11件（parse、不正形の拒否、非クリーチャー判定、条件を満たした攻撃＋3ブレイク＋攻撃時マナ加速、タマシード同士の数え、他文明・相手の場は数えない、数が減るとクリーチャーでなくなる、CIP は非クリーチャー時も働く、ブロッカーは条件を満たす時だけ、攻撃時+6000付与、自ターンだけの no_leave、任意 CIP の承諾／辞退）＋tests/test_vocab_pilot179_cards.py 1件（rejects の11件の partial に ace: true を足し、types を [tamaseed] に正規化するだけで parse が通る）。
- 判別確認: chars フックを外すと 11件中6件が失敗（条件つきクリーチャー性の肯定系。復元後12件全通過）。combat の型要求を外すとブロッカー試験が失敗（復元後通過）。
- テスト作成の注意: 単一選択肢の決定（charge / main / attack の pass だけ）は自動回答されるため、手札が空の側のターンは決定が出ずに飛ぶ。攻撃ステップに選択肢がない（攻撃できない）場合も決定は出ないので、「攻撃できない」ことの確認は `_attack_options(0)` / `_can_attack` で直接行うこと。ブロック決定はブロッカーが1体もいなければ選択肢が no_block だけで自動回答されるため、ブロック可否の試験には対照用のブロッカー（T004）を別に入れておくこと。攻撃中の継続的効果（modify）はブロック決定の時点で観察する（攻撃が終わると end_of_turn で消える）。
- 待機11件（ace_tamaseed_conditional_creature 単独）。再変換はラウンド215で実施。注意: dm22rp2x-4a の2節は本弾の対象外で差し戻し見込み（「タマシードが攻撃する時、そのタマシードが持つ『このタマシードが出た時』で始まる能力を使ってもよい」は他カードの誘発の再利用語彙が無く、新ギャップ tamaseed_attack_reuse_cip。「クリーチャーではないタマシードはすべて、カードタイプに『クリーチャー』を追加し、『W・ブレイカー』を得、パワーが8000になる」は add_types mod とパワー固定 mod が無く、付与節は partial に残す）。dm26sd1-p005 は複合ギャップ（choose_player_effect＋once_per_turn_mana_summon_permission＋ace）で本弾では対象外。

## 第180弾: j_tornado（Jトルネード）（2026-11-11）
Jトルネードは定義語（「自分の他のジョーカーズ（・クリーチャー）を１体、手札に戻す」）で、新エンジン語彙は要らない。核は既存語彙だけのイディオム（第165弾のウラ・ニンジャ・ストライクと同型のコンバータ側パイロット）。
- 基本形（攻撃時・任意）: `kind: trigger, when: {event: attack, subject: self}` の effect を `op: if, cond: {exists: {zone: bz, owner: you, filter: {races: [ジョーカーズ]}, exclude: {ref: self}}}` で守り、then を `op: may, body: [{op: move, select: {zone: bz, owner: you, filter: {races: [ジョーカーズ]}, exclude: {ref: self}, count: 1}, to: hand, as: jtornado}, <後続>]` と書く。if ガードが無いと他のジョーカーズが無い時に may だけが出る（第177弾の流儀）。move は候補0枚なら何もせず `as` に空束縛するので、後続の `cost_of` は未束縛でも 0 を返す（selectors.py `_expr_refs` は未束縛の変数を `[]` とし、`cost_of` は max の既定 0）。`as: jtornado` の束縛は後続の「そのJトルネードされたクリーチャー」参照に使う。
- 「Jトルネードを２回までする」「最大２回」: `op: repeat, times: 2, body: [if ガード → may [move as: jtornado, <１回分の後続>]]`。repeat に up_to は無く、各反復の may 辞退で 0〜2 回になる（dmrp11-004型）。１回分の後続（「そのJトルネード１回につき、…唱えてもよい」）は may の body 内に置く。唱える呪文の選択も任意なら内側にも may を置き、候補0枚で may だけ出ないよう `if {exists: {zone: hand, owner: you, filter: {types: [spell], cost_le: 6}}}` で守る。「選んで相手に見せ」は唱えること自体が公開情報のため別 op は置かない。
- 合計コスト形（dm26ex4-020型）: `cost_of` は参照先が複数ある時に最大値を返すため、合計は `repeat` では書けない。2回の may 移動を展開し、別名 `jt1` / `jt2` に束縛して `cost_le: {sum: [{cost_of: {ref: jt1}}, {cost_of: {ref: jt2}}]}` と書く（辞退した側は 0）。唱えるのは `if {any: [{exists: {ref: jt1}}, {exists: {ref: jt2}}]}` の内側の may とし、ゾーン選択（手札または墓地）は modal の2モードで書く（dm26ex3-089 の先例）。「唱えた後、墓地のかわりに山札の下に置く」は `play_free` の `resolve_to: deck, resolve_position: bottom`。
- ブロック時形（dmrp12-042型）: `when: {event: block, subject: self}` で同じイディオム。ブロッカー＋攻撃不可は keywords `[blocker, cannot_attack]`。
- proto T408（dmsd13-013型・攻撃時 Jトルネード＋2ドロー）/ T409（dmrp12-042型・ブロック時 Jトルネード＋自アンタップ）/ T410（dmrp11-004型・最大2回＋1回につき手札からコスト6以下の呪文を無料唱え）/ T411（dm26rp3-033型・攻撃時 Jトルネード＋3ドロー1捨て。CIP節は省略）/ T412（dm26ex4-020型・2回まで＋合計コスト以下の呪文を手札/墓地から無料唱え、解決後山札の下へ。G・ストライク印付き）。tests/test_vocab_pilot180.py（実挙動テスト。bz は共有ゾーンなので controller も照合）＋tests/test_vocab_pilot180_cards.py 1件（rejects の10件の partial に Jトルネードの攻撃時誘発を足すだけで parse が通る）。
- 対象外・見込み: dm26ex4-021 の「そのJトルネードされたクリーチャーの『このクリーチャーが出た時』で始まる能力を１つ使う」は他カードの誘発の再利用語彙が無く、新ギャップ cip_reuse で差し戻し見込み。dmrp12-078 の「そうしなかったら、この攻撃を中止する」は攻撃中止の語彙が無く、新ギャップ attack_cancel で差し戻し見込み。dmsd13-007 の GR召喚は範囲外（gr_summon）で差し戻し。dmrp11-040 の「次のターン、相手は１度しかクリーチャーで攻撃できない」は攻撃回数制限の語彙が無く、新ギャップ attack_count_limit_next_turn で差し戻し見込み。dm26ex4-020 の合計コスト形は本弾の T412 で検証済みのため挑戦する。
- 判別確認: T408 の move から `exclude: {ref: self}` を外すと攻撃テストが失敗（自分自身が候補に入り、攻撃者が手札に戻る）。復元後13件全通過。
- テスト作成の注意: 先攻1ターン目はドローが無い（攻撃決定時点の手札は0枚）ため、手札枚数の assert は攻撃決定時の手札を on_attack で測ってからの差分で書く（戻ったジョーカーズ自身も手札に数える）。ブロックのタップ状態は、ターン開始アンタップより前に観測する必要があるため、相手に攻撃者を2体置き、2回目の攻撃決定の時点でタップ状態を記録する（1回目の攻撃決定ではまだブロック前）。自分の攻撃手順に攻撃できるクリーチャーが無いと攻撃決定自体が出ない（選択肢 pass だけは自動回答）。捨て札の choose_cards は候補の先頭が戻ったジョーカーズになることがあるため、捨てるカードは defn で選ぶ（pick_filler）。
- 待機10件（j_tornado 単独）。再変換はラウンド216で実施。

## 第181弾: lost_prism（ロスト・プリズム）（2026-11-11）
ロスト・プリズムは「このクリーチャーをバトルゾーンに出した時、自分の山札の上から１枚目を表向きにしてもよい。それが多色カードであれば、手札に加える」。第163弾の reveal_until に limit（公開する合計枚数の上限。式）を追加し、`limit: 1, count: 1, filter: {multicolor: true}` で表す。合わなかった公開分は山札に残るので移動しない。limit が無ければ従来どおり「合うカードが count 枚出るまで」公開し続ける。任意性は `{op: may, body: [...]}`（誘発の optional は置換の辞退にしか効かない。第179弾の教訓）。schema は再生成で追随（差分は limit の1点のみ）。Rust 側の変更なし（op の追加パラメータで Card 状態フィールドに影響なし）。
- proto T413（dm24-063型・ロスト・プリズムのみ）/ T414（dm24-033型・ロスト・プリズム＋スピードアタッカー＋ターン終了時自アンタップ）/ T415（dm24-065型・ロスト・プリズム＋破壊時手札戻し置換）/ T416（dm24-069型・S・トリガー＋ロスト・プリズム）/ T417（dm24-s09型・ロスト・プリズム＋破壊時山札探索）。tests/test_vocab_pilot181.py 10件（parse、不正な limit の拒否、ヒットで多色が手札へ、ミスで1枚だけ公開して止まる、may 辞退、山札1枚の境界、スピードアタッカー＋ターン終了時アンタップ、破壊時手札戻し、破壊時探索、S・トリガー付きのヒット）＋tests/test_vocab_pilot181_cards.py 1件（rejects の9件の partial にロスト・プリズム誘発を足すだけで parse が通る）。
- 判別確認: limit を無効化すると miss 試験が失敗（2枚目の多色まで公開して手札に行く）。復元後11件全通過。
- テスト作成の注意: 多色カードは各文明のマナを1枚ずつ要るため、マナは文明混ぜにすること（全自然マナでは T413/T414/T307 が出せず、メインが pass だけになって自動でターンが進み、後のドローで山札の並びが崩れる）。山札0枚は SBA で即敗北するため、空の山札での CIP は試験できない（山札1枚のミスで境界を試験）。choose_shields はブレイク枚数分だけ選ぶ（全シールド指定は IllegalAnswer）。
- 待機9件（lost_prism 単独）。再変換はラウンド217で実施。注意: dm24-036 の文明数比較の常在型（「バトルゾーンに自分のほうが多くの文明のカードを持っている時、パワーを+3000し、W・ブレイカーを得る」）と dm24-s09 の破壊時探索は partial に無く、ラウンド217で既存語彙で書けるか判断する（dm24-s09 の探索は choose＋move＋shuffle の既存形で書ける見込み。dm24-036 は civ_count 式の比較で書ける見込み）。dm24-s06 のドロー時分岐（引いたカードを表向きにし、光ならそのターン破壊時とどまる、闇なら相手1体を-2000）は新ギャップ draw_reveal_branch で差し戻し見込み。

## 第182弾: play_restriction（実行制限）（2026-11-11）
「〜を実行できない」「〜を出せない」は常在型の範囲付与（affects）＋mod deny のイディオムで表す。核は既存語彙で、回数制限だけ新しい deny 辞書形を追加した。
- 基本形（常在型）: `{kind: static, affects: {zone: hand, owner: opp/any, filter: {...}}, mod: {deny: [summon, cast]}}`。`_can_play_face` が permits(summon/cast) を見るため、手札からの実行が選択肢に出ない。filter の式値は `_subject_match` が解決時に計算する（既存の前評価）。「自分の手札の枚数以下のコスト」は `cost_le: {count: {zone: hand, owner: opp}}`（owner: opp は発生源コントローラーから見た相手＝制限を受ける側の手札）。「自分のターン中、〜」は static の `if: {is_turn: you}`（`_static_cond` 既存）。S・トリガー使用禁止は affects {zone: shield}＋`deny: [s_trigger]`（宣言時の `_permits_face` が見る）。
- 期間つき（「次の相手のターン中」）: CIP 誘発から `{op: modify, dynamic: true, duration: until_next_own_turn_start, select: {zone: hand, owner: opp, filter: {...}}, mod: {deny: [...]}}`。自分のターンに解決すれば自分の次のターン開始まで残り、間の相手ターン全体を覆う（既存の duration）。
- 回数制限（新語彙）: deny 辞書形 `{action: summon, max_per_turn: 1, count: enter}`。`permits()` の hit() が、そのターンに `hist:<count>:<controller>` が `max_per_turn` 以上なら禁止する。`count` 省略時は action 名を履歴 kind とする（summon→hist:summon、cast→hist:cast）。「クリーチャーを１体までしか出せない」は「出す」＝バトルゾーンへの出現全般なので `count: enter` を明記する（hist:enter は召喚・効果を問わず bz 入りを数える）。select zone: any と組にすれば手札以外からの出現も同じカウンタで数える。defs 検証: max_per_turn は 1 以上の int、count は TURN_COUNT_KINDS。schema.py の perm 辞書形にも max_per_turn / count を追加し schema 再生成（`python3 -m dmsim.schema > data/schema/card.schema.json`）。defs の allow/deny 辞書形に未知キー拒否も追加（既存キーは action/other/once のみだったため安全）。
- proto T418（dm25ex3-rp2tr3/dmpcd01-t01型・光以外は誰も実行できない）/ T419（dm25bd2-006型・相手は自分の手札の枚数以下のコストを実行できない＋相手の実行時に2ドロー）/ T420（dm26ex2-001型・CIPで相手パワー5000以下を全バウンス＋次の相手のターン中そのパワーを出せない）/ T421（dm26rp1-std004型・CIPで次の相手のターン中クリーチャーを1体までしか出せない）/ T422（dm26ex4-035型・自分のターン中、相手は多色ではないクリーチャーを出せない）/ T423（dmex08-128のS・トリガー禁止節だけ）。tests/test_vocab_pilot182.py 9件（parse、不正な max_per_turn の拒否、光以外不可、手札枚数 cap の境界＋実行時2ドロー、バウンス＋次ターン制限の期限切れ、1体制限＋期限切れ、自ターン限定、S・トリガー禁止と対照）＋tests/test_vocab_pilot182_cards.py 1件（rejects の7件の partial に実行制限節を足すだけで parse が通る）。
- 判別確認: permits() の max_per_turn 分岐を無効化すると T421 試験が失敗（復元後10件全通過）。回帰は file_schemas＋mechanics＋rules＋engine 68件＋pilot160/161/164/166/178/179/180/181 70件が全通過。
- 対象外・見込み: dmex12-s05 の超次元/超GRからの出現禁止は範囲外（hyperdimensional_zone/gr_summon）で差し戻し見込み。dm26ex2-036 の「手札または山札以外から実行できない／出ない」は発生源ゾーン条件の語彙が無く、新ギャップ play_restriction_origin_zone で差し戻し見込み。dmrp18-a12 の「召喚以外の方法で出せない」は enter_bz の deny が召喚経路も塞ぐため、新ギャップ play_restriction_non_summon_entry で差し戻し見込み。dmex08-128 は「シールドをブレイクできない」（breaks は max 合成で 0 にできない）と「4枚より多くデッキに入れられる」（デッキ構築ルールはエンジン外）の2節が書けず、新ギャップ play_restriction_break_and_deck で差し戻し見込み（S・トリガー禁止節は解けているので partial に残す）。
- テスト作成の注意: T419 の手札枚数 cap はターン開始ドローで手札が1枚増えるため、ライブ試験ではドロー後の枚数で境界を計算すること（手札2枚で開始→ドロー後3枚。コスト3は不可、コスト6は可）。T420 の CIP バウンスは出た相手クリーチャーも手札に戻るため、許可側の試験札はバウンス対象外のパワー6000以上（T040）を手札に用意すること。T421 の回数制限は summon だけでなく enter_bz も deny する（効果での出現も同じ hist:enter で数える）。相手ターンの駆動は pilot164 の型（player==1 の main で play: を選ぶ）を使う。
- 待機11件（play_restriction 単独）。再変換はラウンド218で実施。

## 第183弾: s_class_invasion（S級侵略）（2026-11-11）
S級侵略は第24弾の侵略イディオム（declare＋op invade）の拡張で、発生源ゾーンが手札以外にも広がるだけ。新しいキーワード印は要らない。ゾーンごとに declare を1つずつ書く（アタック・チャンスの手札＋墓地の前例と同じ型）。「自分の指定のクリーチャーが攻撃する時」は declare の when {event: attack, subject: {owner: you, filter}} で、条件は civs＋race_has: コマンド（部分一致なのでソニック／マジック／ゲリラ・コマンドを拾う）か、コスト3指定なら cost_le＋cost_ge の積み重ね。
- 新語彙は3点だけ（いずれも combat/events/ops の小変更）。(1) `_declarable` が bz も走査する。bz は共有ゾーンなので controller で絞り、下のカード（top_of >= 0）は宣言できない。攻撃中のクリーチャー自身は自分の上には重ねられない（「自分以外のクリーチャーが攻撃する時」）ので、イベントの subject は除外する。(2) `op_invade` は onto が自分自身なら何もしない（自己重ねの受け皿）。(3) `_match_when` は from: bz・to: bz の移動を「離れた時」には照合しない（bz→bz は離れたことにならない。公式Q&A・DARK MATERIAL COMPLEX の裁定）。「出た時」側は「置くは出すと同義」で to: bz の照合を通す——bz から重ねても CIP は発火する扱い（要公式確認の解釈。覆れば invade 側で enter イベントを抑える）。
- 「このクリーチャーをその上に重ねてもよい」型（[轟速][不死][原始]）はクリーチャーごと移動し、既存の `_stack` と同じ挙動（公式Q&A 2023年2月17日更新版・総合ルール 409.1f）。「このカードをその上に重ねてもよい」型（[宇宙] アダムスキー）は進化元を置いていく剥がし重ねのため対象外。新ギャップ s_class_invasion_peel で差し戻し見込み。
- proto T424（試験用闇コマンド・攻撃者）/ T425（墓地経路・dmr19-017型）/ T426（手札＋墓地・dmr19-018型）/ T427（マナ・コスト3・dmr19-s09型）/ T428（試験用自然コスト3獣・攻撃者）/ T429（バトルゾーン経路・dmex16-027型。CIP ドロー＋離れた時ドローの両方を持ち、bz 重ねで前者だけ発火することを検証）。tests/test_vocab_pilot183.py 8件（墓地・手札・墓地2つ目・マナ・コスト3・条件外の攻撃者では出ない・バトルゾーン・自己攻撃では出ない・相手のバトルゾーンでは出ない）＋tests/test_vocab_pilot183_cards.py 1件（対象10件の partial に declare を足すだけで parse が通る）。
- 判別確認: bz 走査を無効化すると T429 試験が失敗、離れた時ガードを無効化すると T429 試験が失敗（手札+2）、自己攻撃除外を無効化すると自己攻撃試験が失敗（復元後9件全通過）。回帰は file_schemas＋mechanics＋rules＋engine と pilot24/165/182 を回す。
- 対象外・見込み: dm26ex1-n015 の超次元ゾーン経路は範囲外（hyperdimensional_zone）。発生源ゾーンに hyper を含む declare は parse こそ通るが、hyper ゾーンにカードが入る手段がエンジンに無く、_declarable も走査しないため、解けた節（手札・墓地）を partial に残して新ギャップ s_class_invasion_hyperdimensional で差し戻し見込み。dm26rp2-tr003 アダムスキーのバトルゾーン経路は剥がし重ねのため新ギャップ s_class_invasion_peel で差し戻し見込み（手札経路は解けているので partial に残す）。リマインダー省略の再録の発生源ゾーンは初出文面で確認済み（dm26ex2-mc006＝手札・墓地・バトルゾーン、dm26rp2-tr003＝手札・バトルゾーン、dm26rp2-tr004＝手札・墓地、dm26rp2-tr006＝手札・マナ）。
- テスト作成の注意: `_drive` の want_defn には `declare:T4xx` の形で渡すこと（`attack:T429:player` のような攻撃選択肢にもカードIDが含まれ、T429 を攻撃者に選んでしまう）。

## 第184弾: cast_spell_side_from_battle_zone（呪文側をバトルゾーンに置いたまま唱える）（2026-11-12）
第14弾の op `cast_face`（スマッシュ・バースト／ラスト・バースト。自分自身の呪文面を置いたまま唱える）の拡張。対象は rejects 単独11件。
- 新語彙は2点だけ。(1) `cast_face` に任意引数 `select: selector` を追加（face は既定 -1＝呪文面を探す）。select がある時は選んだツインパクト・クリーチャーの呪文面を唱え、カードはバトルゾーンに残る。cast イベントの subject は選んだカード、self は選んだカードになる。候補1体なら選択は出ない（ask の mn==mx==len 自動確定）。`{ref: event.subject}` 形も使え、「そのクリーチャー」（攻撃したツインパクト自身、dm26sd1-u005型）を唱えられる。(2) フィルタに `spell_cost_le` / `spell_cost_ge` を追加（FILTER_KEYS＋FILTER_EXPR_KEYS。値は式を書ける）。ツインパクトの呪文側（types に spell を含む面）の印刷コストで絞る。dm25ex4-063型「呪文側のコストが自分のマナの枚数以下なら」は `spell_cost_le: {count: {zone: mana, owner: you}}` と書く。なお filter_match の ref 分岐は式の値を評価しないため、spell_cost_* に式を書くのは zone セレクタで使うこと（従来の cost_le と同じ制約）。
- 既存の型の再利用: 「各ターンに１度」の誘発は `once_per_turn: true`（dm26ex4-057型・dm26sd1-u005型）。相手の呪文を唱えた時は `when: {event: cast, subject: {owner: opp, filter: {types: [spell]}}}`。相手のクリーチャーが手札以外から出た時は `when: {event: move, to: bz, from: [deck, graveyard, mana, shield, bz, hyper, gr, abyss], subject: {owner: opp, filter: {types: [creature]}}}`（from のリスト指定は _match_when が「いずれか」で照合する。旧 dmex12-034 の「照合できない」注記とは異なり、現行の _match_when と defs の when 検証はリスト形を通す）。呪文面の「次の中からN回選ぶ」は既存の op `modal`（repeat ありで同じものを選んでよい）。
- proto T430（呪文面コスト2・1ドロー）/ T431（呪文面コスト4・バウンス）/ T432（攻撃時・dm23bd6-018型）/ T433（自分のツインパクトが攻撃した時・event.subject・dm26sd1-u005型）/ T434（呪文面コスト制限つき・dm25ex4-063型）/ T435（相手の呪文時・once_per_turn・dm26ex4-057型）。tests/test_vocab_pilot184.py 6件（他者の呪文面を選択して唱える・候補1体は選択なし・event.subject で攻撃者自身・呪文面コスト制限の両側・相手の呪文で1度だけ・対象無しは何もしない）＋tests/test_vocab_pilot184_cards.py 1件（変換形が定まる10件の raw 両面に対する parse。呪文面は modal／destroy／move／modify の既存 ops で書く）。
- 判別確認: T432 はツインパクトではない（自分の呪文面を持たない）ため、select が無ければ試験1はドローせず失敗する。T433 の event.subject 形は攻撃者自身の呪文面を唱えることを検証する。回帰は file_schemas＋mechanics＋rules＋engine と pilot14/31 を回す。
- 対象外・見込み: dm26ex1-008（山札の上3枚を表向きにし、ツインパクトの呪文側を唱え、墓地に置くかわりに出す）はめくり唱え＋解決後置き換えの別形のため、新ギャップ cast_spell_side_from_reveal で差し戻し見込み。dm23bd5-014 の CIP「山札の上から４枚まで、タップしてマナゾーンに置く」は「まで」の枚数選択の idiom をラウンド220で確認すること（from_top＋count＋up_to の形）。dm25ex4-063 の呪文面「コスト３以下のエレメントを１つ選び、持ち主のマナゾーンに置く」は move to: mana の行き先が持ち主のマナになるかの確認がラウンド220で要る。dm25ex1-011 は G-NEO進化（neo＋evolve_from）の併記がラウンド220で要る。待機11件（cast_spell_side_from_battle_zone 単独）。再変換はラウンド220で実施。
- テスト作成の注意: 支払いのマナは文明が要る（水の呪文を唱えるには水マナが必要）。相手に呪文を唱えさせる試験では相手のマナをその呪文の文明で置くこと。_drive は終局まで回すとターンのドローで手札が増えるため stop 述語で止めること。
- 待機10件（s_class_invasion 単独）。再変換はラウンド219で実施。

## 第185弾: break_bonus（ブレイク・ボーナス）（2026-11-12）
「ブレイク・ボーナス（このクリーチャーの攻撃が終わった時、このクリーチャーがまだバトルゾーンにあれば、その攻撃中にブレイクしたシールド１枚につき、次の能力を１回使ってもよい）」。対象は rejects 単独10件のうち真のブレイク・ボーナス7件（dm33-004/010/010hc/025/034/s03、dmc64-037）。残り3件は別ギャップ（dmrp08-051＝S・トリガー＋スマッシュ・バースト、dm24ex3-rp3s07＝ハイパーエナジー＋ブレイク数追加、dmr12-048＝ブレイク数追加の付与＋ドロン・ゴー）。
- 新語彙は2点＋ついでの1点。(1) h_break が攻撃番号で区切ったカウンタ `broke_count:<cid>:atk<ano>` を刻む（その攻撃中にそのクリーチャーがブレイクした枚数。`broke_in` の隣）。ターン通しの `hist:broke_by` では、同じターンに効果でブレイクした分まで数えてしまうため使えない。(2) 式 `{turn_count: {kind: broke_by_self_attack}}` がその枚数を読む（defs の TURN_COUNT_KINDS に追加。broke_by_self と同じく owner/other/filter 不可）。(3) ついでに `chooser: random`（「見ないで選ぶ」）を select() に実装した：従来は parse だけ通り実行時に `_rel` が KeyError になり、先行カード12件の能力も実行時に壊れていた（dm33-s03 のランダム捨てに要る）。ついでに `chooser: opponent`（dm06-005 の既存形、opp の同義語）も select() で処理し、defs の chooser 検証を you/opp/opponent/random にした（検証を厳しくしすぎて load_rules が壊れる事故があったので、既存値の網羅を確認してから入れること）。
- カードの型: `when: {event: attack_end, subject: self, broke: true}` の誘発＋ `{op: repeat, times: {turn_count: {kind: broke_by_self_attack}}, body: [{op: may, body: [<ボーナス>]}]}`。「まだバトルゾーンにあれば」は _collect_triggers の発生源＝バトルゾーンのカードで自動的に保証される。1回ごとの may が「１回使ってもよい」に対応する。
- 既存の型の再利用: dm33-010 の「破壊する。そうした場合、クリーチャーが出るまで表向きにする」は destroy `as: d`＋reveal_until `count: {var: d}`（第199弾の型）。dmc64-037 の「1枚目を見せる。ファイアー・バードなら出してもよい。でなければ墓地」は reveal_until `limit: 1, count: 1`＋hit/rest 分岐。ミルは `op: mill` マクロ、ランダム捨ては choose `chooser: random`＋move reason: discard。進化は types に evolution を足し、dm33-010 は evolve_from `{any_of: [{race_has: サイバー}, {races: [オリジン]}]}`。
- Rust 側: rust/dmcore/src/engine.rs のブレイク処理に broke_count の書き込みをミラーした（broke_in の隣）。turn_count 式の評価は Rust に無い（broke_by_self と同じ扱い）ため読み側の変更なし。**この環境には cargo が無いため Rust のコンパイル未検証**。次に Rust をビルドできる環境で `cargo check -p dmcore` を行うこと。
- proto T436（dm33-025型・ミル4）/ T437（dm33-004型・進化＋パワー7000以下破壊）/ T438（dm33-s03型・T・ブレイカー＋ランダム捨て）/ T439（dm33-034型・マナ2枚）/ T440（判別用・CIP 効果ブレイク＋W・ブレイカー＋1ドロー）。tests/test_vocab_pilot185.py 10件（parse、W・ブレイカーでミル2回、1枚ブレイクでミル1回、破壊2回、捨て3回、マナ2回、ブロックで不発、S・トリガーで破壊されて不発、効果ブレイクは数えない、may 辞退）＋tests/test_vocab_pilot185_cards.py 1件（7件の partial に誘発を足すだけで parse が通る）。
- 判別確認: broke_count の刻みを無効化すると T440 試験が失敗（ドロー0回）。chooser: random の実装前は T438 試験が KeyError で失敗していた（既存の先行カードも同じ箇所で壊れていた）。回帰は file_schemas＋mechanics＋rules＋engine＋pilot14/31＋rust_schema_sync＋data_audit と pilot185（11件）で 95 passed / 1 skipped。
- テスト作成の注意: 先攻1ターン目はドローが無い（ターン開始ドローは setup 時には起きない）。手札枚数の assert は「出した-1、ボーナス+2」など差分で書くこと。ターン2のドローは charge 決定より前に済むが、stop 述語の評価タイミングによっては手札が増える前／後が変わるため、手札枚数は二次的な確認に留め、墓地・シールド・ゾーンなどの決定的な量で主に assert すること。ブロック試験では墓地の1枚はバトルで死んだブロッカー、S・トリガー試験では墓地の1枚は使い終わった T006 であることに注意（ミルと区別する）。op move には reason が必須（mill/mana_put マクロを使うか reason: put を書く）。`op: destroy/mill/discard/bounce` は op_macros.yaml のマクロで、move 等に展開される（OPS には無い）。
- 待機7件（break_bonus 単独）。再変換はラウンド221で実施。次候補：super_guardman 10、friend_burst 9、ggg_condition 9、cast_resolution_destination 9、ex_life 9、cip_reuse 9、mana_number_change 9、chosen_trigger 9（out_of_game 23・duelist_link 20・outside_game 12 は範囲外／ジョーク系、lose_replacement 11・summon_time_cost 11 は未検討）。

## 第186弾: super_guardman（スーパーガードマン）（2026-11-12）
「スーパーガードマン（自分の他のクリーチャーがバトルする時、かわりにこのクリーチャーをタップしてバトルさせてもよい）」。対象は rejects 単独10件。
- 土台は既存のバトル相手の置換（combat の `_battle_substitute`。攻撃フロー ph 3 で `when: {event: battle}` の置換効果を諮り、選ばれれば攻撃側／防御側のどちらかを入れ替える。データ側での使用実績はまだ無かった）。新語彙は1点だけ：`battle_substitute` op に任意引数 `tap: true` を追加（ops.py の @op 登録＋schema 再生成で追随）。
- カードの型: `{kind: replace, when: {event: battle, subject: {owner: you, filter: {types: [creature]}, other: true}}, instead: [{op: battle_substitute, tap: true}]}`。subject の `other: true` が「他のクリーチャー」（自身を除く）、`owner: you` が「自分の」を表す（`_subject_match` の既存形。converted には同じキー組合せが152件ある）。`_battle_substitute` は置き換えられる側のコントローラーのバトルゾーンだけを走査するため、相手のガードマンが自分のクリーチャーを守ることはない。
- `_battle_substitute` の変更2点：(1) 選ばれた置換の instead に `tap: true` があれば、代わりにバトルするクリーチャーをタップする（タップにイベントは出さない。第171弾のリダイレクトのアンタップ・コストと同じ扱い）。(2) tap が要る置換は、タップ済みのクリーチャーを選択肢に出さない。tap が無い置換（従来の印だけの形）は従来どおりタップしない。
- 制限：効果によるバトル（op `force_battle`）は `_battle_substitute` を通らないため、スーパーガードマンは働かない（vocab-pilot.md 冒頭の既知の注記どおり）。dm26rp2-046 の「相手のクリーチャーが手札以外から出た時、このクリーチャーとそのクリーチャーをバトルさせてもよい」は force_battle の別能力なので本弾の置換とは無関係。
- proto T441（dm26rp2-069型・8000）/ T442（判別用・2000）/ T443（W・ブレイカー・6000・dm26rp2-069型）/ T444（攻撃できない・8000・dm26rp2-046型）/ T445（T・ブレイカー・12000・dm26rp2-073型）。tests/test_vocab_pilot186.py 10件（parse、不正形の拒否、攻撃された時にタップしてかわりにバトル、辞退、ブロックされた攻撃でも置換、タップ済みは選択肢に出ない、相手のクリーチャーは守らない、2体から1体を選ぶ、自身では置換できない、1回目のバトルでタップされると同じターンの2回目では置換に出ない）＋tests/test_vocab_pilot186_cards.py 1件（対象10件の partial に置換能力を足すだけで parse が通る）。
- 判別確認：エンジン変更（combat.py＋ops.py）を退避すると 1 failed・8 errors（proto の tap 引数が DefError になる等。復元後11件全通過）。回帰は file_schemas＋mechanics＋rules＋engine＋pilot14/31＋rust_schema_sync＋data_audit＋pilot185/186 で 107 passed / 1 skipped。Rust 側に battle_substitute の実装は無く、ミラー不要。
- テスト作成の注意：直接攻撃できるのはタップ状態のクリーチャーだけ（505.2）なので、攻撃先のクリーチャーは setup 後にタップすること。攻撃が終わると次の決定は翌ターンの charge になり、ターン開始アンタップで置換のタップが見えなくなるため、タップを assert する試験では T007 のような2体目の攻撃者を置いて同じターンの攻撃決定で止めること。ゾーン移動でタップ印は消えるため、バトルで破壊されたガードマンのタップは墓地では見えない（機能的には2回目のバトル試験で検証する）。
- 待機10件（super_guardman 単独）。再変換はラウンド222で実施。差し戻し見込み：dm26rp3-010（CIP の「選んだクリーチャーの、出た時にトリガーする能力を、自分が１つ使ってもよい」は他カードの誘発の再利用語彙が無く、新ギャップ見込み。残りの節は既存語彙で書ける見込み）、dm26rp2-s008（ファイナル革命＋攻撃終了時めくり節はラウンド時に精査）、dm26rp2-027（「攻撃できない能力を無視する」は mod `ignore` の意味をラウンド時に確認）。なお今回の schema 再生成には第185弾の `broke_by_self_attack` の列挙追加（第185弾コミット時の再生成漏れ）も含まれる。

## 第187弾: friend_burst（フレンド・バースト）（2026-11-12）
「X・フレンド・バースト（このクリーチャーが出た時、自分の他のX・クリーチャーを１体タップしてもよい。そうしたら、このクリーチャーの呪文側を、バトルゾーンに置いたままコストを支払わずに唱える。）」。対象は rejects 単独9件（すべてツインパクト）。新エンジン語彙は要らない。第14弾・第184弾の `cast_face`（自分の呪文面を置いたまま無料で唱える）と既存 op の組合せだけのイディオム・パイロット（第180弾の Jトルネードと同型）。
- カードの型（クリーチャー面の CIP 誘発）: `{kind: trigger, when: {event: move, to: bz, subject: self}, effect: [{op: if, cond: {exists: {zone: bz, owner: you, filter: {types: [creature], race_has: <X>, tapped: false}, exclude: {ref: self}}}, then: [{op: may, body: [{op: tap, select: {zone: bz, owner: you, filter: {types: [creature], race_has: <X>, tapped: false}, exclude: {ref: self}, count: 1}}, {op: cast_face}]}]}]}`
- `race_has: <X>` は「X・フレンド・バースト」の X（スノーフェアリー／メカ／アビス／アーマード／ジャイアント／マジック）。部分一致のため「コマンド」類と同型（第183弾）。「・」で結ばれた複合種族は両方の種族を持つ扱いのため、例えば race_has: スノーフェアリー はジャイアント・スノーフェアリーにも当たる。`races:` は完全一致のため使わない（アーマード・ファイアー・バードに races: [ファイアー・バード] は当たらない。converted の定番は race_has: ファイアー・バード）。
- `tapped: false` はガードと選択の両方に入れる。タップ済みのクリーチャーはタップし直せないため「そうしたら」の条件を満たさず、候補に入れない。ガードが無いと他の X クリーチャーが全員タップ済みの時に may だけが出る（第180弾の教訓）。
- `types: [creature]` はタマシード等の同種族クリーチャー以外を除くため。`exclude: {ref: self}` は「他の」を表す（第180弾と同型）。
- `cast_face` は選択無しで自分自身の呪文面を唱える（第14弾・第184弾）。唱えたことになり、カードはバトルゾーンに残り、解決後に墓地へは行かない。
- 既存の型の再利用: 呪文面の「墓地から出す」は `play_free`（as: 束縛可。dm22ex2-008型）、「そのクリーチャーにスピードアタッカーを与える」は modify grant [speed_attacker] duration end_of_turn、「自分のクリーチャー１体につき、いずれか１つを選ぶ」は repeat times: {count: ...}＋modal、「自分の他のファイアー・バードのパワーを+2000」は affects {other: true}＋mod {power: 2000}、「自分のスノーフェアリーの召喚コストを２少なくする」は affects {zone: hand}＋mod {cost: -2}（０以下にはならないのは _pay_cost の max(0, ...) で自動。dm24ex1-087型）、「バトルに勝った時」は when {event: battle_win, subject: self}＋{op: break}（相手のシールドをブレイクする）、「自分のクリーチャー１体のパワーを+4000する。その後…その２体をバトルさせる」は op `choose`（as: 束縛）＋modify {ref: a}＋may force_battle a: {ref: a}（modify に as は無いので choose を使う）。呪文面の S・トリガーは面の keywords: [s_trigger] に書く（第184弾の dm23bd6-024・dm25ex4-063 で確認済み）。
- proto T446（dm23rp2x-057型・マジック・3ドロー）/ T447（dm23rp2x-020型・アーマード・他ファイアー・バード+2000・呪文は1捨て2ドロー）/ T448（dm23rp2x-009型・メカ・ブロッカー＋W・ブレイカー・呪文は自分のクリーチャー１体につきタップかドロー）/ T449（dm23ex2-040型・スノーフェアリー・ブロッカー・召喚コスト-2・呪文は墓地からスノーフェアリーを出しスピードアタッカー付与）/ T450（dm23rp2x-023型・ジャイアント・ガードマン＋W・ブレイカー・バトル勝利時1ドロー＋1ブレイク・呪文は+4000＋任意でバトル）。tests/test_vocab_pilot187.py 11件（parse、タップして唱える、辞退、他の X が無い時は出ない、他の X がタップ済みの時は出ない、2体から1体を選ぶ、相手の X はタップできない、アーマードの静的＋呪文、メカの modal 呪文、スノーフェアリーの墓地出し＋スピードアタッカー、ジャイアントの呪文＋バトル辞退）＋tests/test_vocab_pilot187_cards.py 1件（対象9件の partial にフレンド・バースト誘発を足すだけで parse が通る。X は写像で与える。アビスロイヤルだけ「・」区切りではなく接頭辞のため）。
- 判別確認: T446 のガードから `exclude: {ref: self}` を外すと test_no_other_friend_no_prompt が失敗（出た本人自身が「他の」候補に入り may が出る）。復元後12件全通過。回帰は file_schemas＋mechanics＋rules＋engine＋pilot14/31＋rust_schema_sync＋data_audit＋pilot185/186/187 で 116 passed / 1 skipped。
- テスト作成の注意: ツインパクトの play キーは `play:T446:0` の形（面番号つき）になるため、ドライバは前方一致で拾うこと。ターン開始アンタップがあるため、タップ状態の試験は setup 直後ではなく最初の決定（charge）の後にタップすること。CIP 解決後に手札が空だとメインが自動終了し、攻撃も出られないとそのまま相手ターンへ進むため、ターン終了時効果（+4000）や相手のタップ状態を assert する試験は、手札に T001 を残し余分なマナで出せる状態にして、プレイ後の最初のメイン決定で止めること（pay_mana の組合せ選択は [0] で有効な組合せが選ばれる）。ブロッカーの keywords は暗黙の static 能力（allow: [block]）を生むため、parse 試験で static の件数を数える時は mod で絞ること。
- 待機9件（friend_burst 単独）。再変換はラウンド223で実施。差し戻し見込み：dm25ex4-036（呪文面が跳次元召喚４＝範囲外 hyperdimensional_summon）、dm26sd1-i009（「相手がそのターン２枚目以降のカードを引いた時」の誘発条件は要精査）、dm24ex4-095（呪文面の S・トリガー＋マナ送り節は要精査だが、面の keywords 形は確認済み）。

## 第188弾: lose_prevention（敗北の防止）（2026-11-12）
- 「自分がゲームに負ける時、かわりに〜」の置換は第43弾からあるが、「負けない」そのものの語彙が無かった。本弾で追加するもの。
- 新 op `no_lose`: `{op: no_lose, player: you|opp|each, duration: end_of_turn|until_next_own_turn_start|permanent, once?: bool, deck_out_only?: bool}`。player は duration の間ゲームに負けない（＝相手はゲームに勝てない）。once は一度だけ（防いだら消費。「このターン中に一度、自分がゲームに負ける時、かわりに負けない」）。deck_out_only は山札切れだけを防ぐ。継続的効果として `s.continuous` に載せ（mod は空・affected は空集合で特性に影響しない）、期限切れは既存の duration 仕組みに任せる。each は両プレイヤー分のエントリを2つ作る。
- 常在型能力 `no_lose`: static だけ。true か `{deck_out_only: true}`（if と併用可。マナ武装・自分のターン中などの条件付き防止、山札切れ限定の防止）。`_lose_immune` は `eval_cond` ではなく `_static_cond` で if を評価する（常在条件の再入防止）。
- `Engine.game_lose` は防止を先に見て、防がれていれば何もしない（置換の諮問も出ない）。常在勝利（kind: state の win）・勝利効果（op win）も、負ける側に防止があれば働かない（state-win 側は該当能力を飛ばして次の常在勝利を探す）。
- 置換の `when.reason`: 敗北の reason（direct_attack / deck_out / state / effect）と照合できる（defs の when 検証は event: lose の時だけ LOSE_REASONS を許す）。「相手クリーチャーの攻撃によって、相手がゲームに勝つ時」用。
- 既存の置換フックで「山札が無い時の引く置換」も表せる（draw イベントの置換。ビッグバン型: 空の山札から引く時、かわりに墓地からクリーチャーを出す。`if: {cmp: [{count: {zone: deck, owner: you}}, ==, 0]}`＋`instead: [may [play_free ...]]`）。
- 「自分の次のターンの終わりに自分はゲームに負ける」（ガブリエラ型）は delayed_trigger の二重掛けで表す：外側 when {event: turn_start, player: you} duration permanent → 内側 when {event: turn_end, player: you} duration end_of_turn → effect [op: lose]。外側を turn_start にすることで、自分のターン中に置換を使っても「次のターン」の終わりになる。
- proto T451（ビッグバン型・山札切れ防止＋引く置換）/ T452（ダイハード型・破壊置換＋破壊時そのターン防止）/ T453（バドフレア型・呪文で一度だけ防止）/ T454（ドギラゴン・ファイアー型・次の自分のターンのはじめまで防止）/ T455（ヴァルハラ型・マナ武装の静的防止。実カードは武装９、proto は２で試験）/ T456（ミノガミ型・マナを山札に戻す置換。実カードは８枚、proto は２枚）/ T457（常在勝利・防止との干渉確認用）。tests/test_vocab_pilot188.py 13件（parse、不正形の拒否、山札切れ防止と対照、引く置換の採用／辞退、破壊置換＋そのターン防止と2回目の攻撃、置換の辞退で敗北、呪文の一度だけ防止、次ターンのはじめまでの防止と期限切れ、マナ武装の静的防止と対照、マナ山札送り置換、常在勝利の防止によるブロックと期限切れ後の勝利）＋tests/test_vocab_pilot188_cards.py 3件（対象16件の partial に敗北の節を足すだけで parse が通る。dmex08-003 は偶奇判定の語彙が無いため対象外）。
- 判別確認: エンジン変更（defs.py＋ops.py＋events.py）を退避すると pilot188 は collection エラーで全滅する（test ファイルが `op_no_lose` を import できない。復元後13件全通過）。対照テスト（防止なしの山札切れ敗北、置換の辞退で敗北、マナ武装の枚数不足）も各節の有無を直接確かめる。回帰は file_schemas＋mechanics＋rules＋engine＋pilot14/31＋rust_schema_sync＋data_audit＋pilot185/186/187/188 で 131 passed / 1 skipped。Rust 側に no_lose の実装は無く、ミラー不要（継続的効果は辞書のため）。
- テスト作成の注意: マナは支払うカードの文明を満たす必要がある（水の呪文には水マナ）。呪文の防止（duration: end_of_turn）は唱えた advance の中でターンが終わると切れて観測できないため、唱えた後も出せるカードを手札に残してメイン決定を再び出させること。draw の置換は毎回のドローで諮問が出るため、辞退テストでは2回目以降も辞退し続けること。山札切れテストは長時間回すと相手の山札も切れるため、ターン数で区切るか山札を多めにすること。`destroy` はマクロで move（to: graveyard, reason: destroy）に展開されるため、parse 後の spell は move 形で assert すること。単面カードの parse 結果は CardDef 自体が面（faces は空）なので `_face0` で吸収すること。
- 待機17件（lose_replacement 単独11件＋lose_prevention 単独6件）。再変換はラウンド224で実施。差し戻し見込み：dmex08-003（山札の上から１枚目を表向きにし、そのコストが奇数なら〜／偶数なら負ける。偶奇判定の語彙が無いため refined gap `reveal_top_cost_parity` へ）、dmex08-226（「このターン中クリーチャーは攻撃できず」の表現を要確認）、dmrp20-s04（置換の破壊が2体ちょうど要る形・シールド0枚条件の扱いを要確認）。

## 第189弾: summon_time_cost 拡張（複数選択・S・トリガー不可・召喚時燃料）（2026-11-12）
第6弾の `opt_reduce`（支払い時の行動を伴うコスト軽減）では表せなかった summon_time_cost の残り11件のための拡張。
- 新語彙は3点。(1) `opt_reduce.do.selects`: 複数の選択肢（`{select, min?, max?}` の配列）。燃料は全項目の合算で、`per` の軽減はその合計枚数 × amount。テラ・スザーク型「手札・クリーチャー・タマシード・シールドを最大1つずつ選び墓地に置く。選んだ数だけコストを1少なくする」用。(2) `opt_reduce.do.strigger_off: true`: 燃料を手札へ動かす時、そのカードの S・トリガーが使えない印（移動イベントに `strigger: "off"` を載せる。第169弾の move op の印と同じ仕組み）を付ける。レッコパブロウ型「シールドを1つ手札に加える。ただし、その『S・トリガー』は使えない」用。(3) Card に `summon_fuel`（召喚時の支払い行動で選んだカードの `[cid, gen]`。ゾーン移動で消える。フォートEの `summon_tapped` と同じ作法で、召喚の移動イベントに載せて出し直す）とセレクタ `{ref: fuel}`（そのカードの summon_fuel のうち生きているもの）。グレイテスト・ジャオウガ型「シールドを2つまで選ぶ。選んだ数だけ軽減。このクリーチャーが出た時、選んだシールドを手札に加える。その『S・トリガー』は使えない」は出た時の誘発 `{op: move, select: {ref: fuel}, to: hand, reason: return, strigger: "off"}` で書ける。
- `do` は `select` と `selects` のどちらかちょうど1つ（defs で検証。schema の required は外し、defs に任せる）。`strigger_off` は bool。
- 再入の注意（今回の教訓）: `ask` は再入ごとに先頭の1回だけ保存された回答を消費するため、複数項目の選択は `t["fuel_idx"]` / `t["fuel"]` / `t["fuel_asked"]` に進捗を刻んで再入時にそこから再開すること。素の for ループでは2項目目以降が再提示されて進まない。`fuel_idx` / `fuel_asked` は PlayTask（types.py）の NotRequired キーにも追加すること（check_shape が未知のキーを拒否する）。単一選択の従来挙動（候補が無ければ軽減なし）は変えない。
- Rust 側: `summon_fuel: Vec<Value>` を state.rs の Card に追加（alphabetical のため summon_tapped の前）＋ `Card::new` の初期化＋ engine.rs / setup.rs のゾーン移動時の clear。**この環境には cargo が無いため Rust のコンパイル未検証**（第185弾と同じ）。test_card_fields_match でフィールド名の一致は検証する。
- proto T458（テラ・スザーク型・4項目選択）/ T459（レッコパブロウ型・シールド→手札＋strigger_off）/ T460（ジャオウガ型・シールド最大2枚＋出た時燃料手札）。tests/test_vocab_pilot189.py 11件（parse、不正形の拒否、4項目燃料で 7→3、一部だけ選ぶ、燃料辞退で 7 のまま、マナ6枚では出せない見積もり確認、シールド→手札＋S・トリガー不可、燃料2枚の出た時手札、1枚だけ、0枚で空振り、summon_fuel の記録）＋tests/test_vocab_pilot189_cards.py 2件（対象11件の partial に節を足すだけで parse が通る）。既存イディオムの再利用: 進化見せ（T038型）、手札捨て（T039型）、墓地呪文→山札（T040型）。コスト9の一致は `cost_le: 9`＋`cost_ge: 9` の重ね（第165弾の idiom）。dmr15-002 の水呪文時バウンスは `when: {event: cast, subject: {owner: you, filter: {types: [spell], civs: [water]}}}`＋may［bz のカード1枚を手札へ］。dmr18-027 のターン終了時アンタップは `when: {event: turn_end, player: you}`＋op untap。
- 判別確認: エンジン変更（defs.py＋schema.py＋state.py＋types.py＋engine 4ファイル＋Rust 3ファイル＋schema.json）を退避すると pilot189 は 2 failed・9 errors（DefError 等）。復元後13件全通過。
- テスト作成の注意: 燃料選択の ask は `mn == mx == len(options)` だと決定を出さず自動確定する（候補1枚で min=max=1 の T459 型）。ドライブの計画にその分のエントリを入れると計画が空にならずドレインが始まらない（ターンが進んでマナがアンタップされる）。シールドの選択肢キーは伏せ札のため両方 `shield` で区別できない。1枚だけ選ぶ試験は同名シールド2枚で組むこと。pay_mana の組み合わせは先頭が異文明マナ混じりになることがあるため、残した手札カードを出せる状態に保つには pay_mana のキーで全闇マナの組み合わせを明示すること（`mana:T460,T460,T460` 形）。召喚後に手札が空だとメイン決定が自動パスしてターンが進む（第187弾の教訓）。
- 待機11件（summon_time_cost 単独）。再変換はラウンド225で実施。次候補：ggg_condition 9、cast_resolution_destination 9、ex_life 9、cip_reuse 9、mana_number_change 9、chosen_trigger 9、henrei 9、battle_replacement 9、marshal_touch 9。

## 第190弾: EXライフの残り節（「EXライフ」シールドが離れた時の誘発＋攻撃/ブロック宣言のタップ・イベント）（2026-11-12）
EXライフ本体（出す時のシールド化・離脱置換）は実装済みだったが、「このクリーチャーの『EXライフ』シールドが離れた時」の誘発と「タップした時」の誘発が書けず、ex_life 単独9件が残っていた。
- 新語彙は2点。(1) `when.subject` の `{exlife_of: self}`（第164弾の `castle_of` と同型の subject パターン）。移動レコードの lki に `exlife_of` を載せ（`_apply_one` の lki 構築時。離れた後では紐付けは消えているため lki が要る）、`_match_when` は subject パターンに `exlife_of` がある時だけ lki を渡し、`_subject_match` が移動前の紐付けで照合する。`when()` の subject は従来どおり検証しない（castle_of と同じ）。(2) 攻撃宣言・ブロック宣言のタップが tap イベントを出す（combat.py の ph 0 / ph 2）。従来は直接代入でタップしていたため「タップした時」誘発が攻撃・ブロックで発火せず、converted の dm24ex3-005 型も実質死んでいた。tap イベントの適用が tapped=True にする（既にタップ済みなら記録は出ない）。コストのタップ（マナ支払い・起動コスト）や battle_substitute の tap は従来どおりイベントを出さない。
- 既存語彙の組合せ: 「自分のシールド１つにつきパワー+1000」は `mod: {power: {amount: 1000, count: {zone: shield, owner: you}}}`。「多色ではない呪文の効果によって、相手がクリーチャーを選ぶ時、このクリーチャーは選ばれない」は第164弾の `deny: [{action: be_chosen, other: {types: [spell], multicolor: false}}]`。「相手のクリーチャーの能力をすべて無視する」は `modify`＋`mod: {ignore: [all]}`＋`dynamic: true`＋`duration: until_next_own_turn_start`（後から出たクリーチャーにも及ぶ）。「自分のカードを使うコストを、そのカードが持つ文明１つにつき１少なくする」は `mod: {cost: {amount: -1, count: {civ_count: {ref: self}}}}`（civ_count は対象カード群の文明の種類数。ref: self ならそのカード自身の文明数）。
- proto T461（dm26ex1-n014型・タップ時/EXライフシールド離脱時: マナ・墓地から1枚手札へ＋相手は1枚捨てる）/ T462（dmsd18-001型・単色呪文で選ばれない＋出た時/シールド離脱時: 相手クリーチャー破壊）/ T463（dmex19-021型・シールド数パワー＋CIPで山札の下へ＋攻撃時: 山札上2枚を見て1枚シールド化・1枚手札へ）/ T464（dmex19-m13型・CIPで相手能力を無視＋相手ターン中の相手召喚/唱え時: 1ドロー＋手札の呪文を無料で唱える）。tests/test_vocab_pilot190.py 9件（parse、タップ誘発、EXライフシールド離脱誘発、通常シールド離脱では不発＝判別、T462 の破壊、単色呪文での選ばれなさ＋クリーチャー由来では選べる判別、シールド数パワー＋CIP、攻撃時シールド化、能力無視＋相手召喚誘発）＋tests/test_vocab_pilot190_cards.py 2件（対象7件の partial に能力を足すだけで parse が通る。dmex18-014 第1節の文明数コスト軽減も parse 可）。
- 判別確認: エンジン変更（events.py＋combat.py）を退避すると pilot190 は 2 failed（タップ誘発、通常シールド不発の判別。EXライフ離脱の肯定試験は退避時も通るが、それは subject パターンが空フィルタ扱いになり「どのシールドでも」発火する偽陽性のためで、通常シールド試験がそれを捕捉する）。復元後11件全通過。回帰は file_schemas＋mechanics＋rules＋engine＋pilot14/31＋rust_schema_sync＋data_audit＋dogiradante＋pilot185/186/187/188/189/190 で 159 passed / 1 skipped。Rust 側の変更なし（lki は実行時レコードのみ。Card フィールドの追加なし）。
- テスト作成の注意: 攻撃宣言のタップは直接代入だったため、タップ誘発は攻撃では発火しなかった（第190弾で修正）。`_play` は手札が空だとメイン・攻撃が自動パスして相手チャージまで進んでから止まる（T003 は水マナが無くて出せないため同じ）。ターン開始ドローはチャージ決定の前に起きるため、手札枚数の assert はドロー分を数えること。無視の duration は次の自分のターンのはじめまでなので、相手の召喚誘発を試す時は相手ターン1に召喚すること（相手ターン2では期限切れ）。`_drive` の停止条件は plan が空の時の charge/main/attack で、待機中の決定があると ev_task が走る前に止まるため、ev_task 注入試験では charge を1回消費する計画を入れること。
- 待機9件（ex_life 単独）。再変換はラウンド226で実施。差し戻し見込み：dmex18-014（攻撃終了時の「手札か墓地からコストを支払って唱える/召喚する」は支払い付き実行の語彙が無く、新ギャップ見込み。第1節は書けるので partial に残す）、dmsd19-001（「プレイヤーを１人選ぶ」はプレイヤー選択の語彙が無く、既存ギャップ choose_player_effect へ）。次候補：ggg_condition 9、cast_resolution_destination 9、cip_reuse 9、mana_number_change 9、chosen_trigger 9、henrei 9、battle_replacement 9、marshal_touch 9。

## 第191弾: マナ爆誕（mana_bakutan）（2026-11-12）
「マナ爆誕N（このクリーチャーを自分のマナゾーンから、コストNを支払って召喚してもよい）」。カード自身の能力による代替コスト召喚で、第50弾の許可（summon_from_mana・通常コスト）とは別系統。
- 新語彙は面フィールド `mana_bakutan: int >= 0` の1点。メインステップの選択肢 `play:<id>:bakutan`（rush 印でマナゾーンからの召喚として処理し、支払いは recycle（第172弾）と同じ cost_override 方式＝固定コストで軽減は乗らない）。permits(cid, "summon") が必要で、進化クリーチャーは対象外。コスト0はマナをタップしないため、支払いの文明要求も無い（cost_civs = []）。
- 副次修正（既存バグ）: `_mana_choices` が支払いプールに実行するカード自身を含んでいた。マナゾーンから出すカードが「自分をタップして自分のコストを払う」組み合わせが列挙され、第50弾の msum 経路でも選択肢の見積もりが甘かった。プールから cid を除外した（手札・墓地から出す場合は元々プールに無いので無影響）。
- 「自分のマナゾーンから召喚していたら」の出た時誘発は既存語彙で書ける：召喚の移動イベントへの trigger `when: {event: move, from: mana, to: bz, reason: summon, subject: self}`（陰陽の舞 dmex08-072 型）。「自然のカードを置けない場合、このクリーチャーを破壊する」は op if（cond exists＋else destroy）で表す。
- dm37-s05（大地竜機シロガシラ・ジュカイ）の「マナゾーンに置く時タップして置く」は多色カードのルール（405.1、core の移動処理で自動）のため語彙不要。残る障害は召喚誘発の「マーシャル・タッチ能力を持つクリーチャーがあればバトルゾーンに出してもよい」節のみで、能力所持フィルタ＋marshal_touch が必要 → ラウンド227で差し戻し（refined gap `marshal_touch`、partial に mana_bakutan: 9 を残す）。
- proto T465（爆誕3・印字6）/ T466（爆誕0）/ T467（爆誕2＋マナから召喚時のドロー誘発）/ T468（火・爆誕2、文明要求の判別用）。tests/test_vocab_pilot191.py 9件（parse、不正形の拒否、固定コスト召喚と支払い3枚タップ、マナ不足で不出、コスト0はマナ無しで可、文明不足で不出＋火マナで可、マナから召喚でドロー、手札からは誘発せず爆誕も出ない、墓地では不出）＋tests/test_vocab_pilot191_cards.py 3件（登録8件の変換形が partial＋mana_bakutan で parse 可、dm37-s05 は対象外の確認）。
- 判別確認: エンジン変更（defs.py＋schema.py＋types.py＋turn.py）を退避すると pilot191 は 6 failed / 3 passed。復元後9件全通過。回帰は pilot50＋pilot172 系27件、mechanics＋cost＋engine＋file_schemas＋pilot37/149/173/189/190 で 88 passed / 1 skipped。schema 再生成済み（差分は mana_bakutan のみ）。Rust 側の変更なし（面フィールドは defs のみ。Card の状態フィールドは追加していない）。
- 待機9件（mana_bakutan 単独）。再変換はラウンド227で実施（登録見込み8件＋差し戻し1件）。

## 第192弾: choose_player（プレイヤーを1人選ぶ）（2026-11-12）
「プレイヤーを1人選ぶ。そのプレイヤーは〜」を表す語彙。対象は choose_player_effect 単独9件＋複合1件（dm26sd1-p005）。
- 新 op `choose_player {as: 名前}`: 効果の使用者がプレイヤーを1人選び、変数に相対指定 "you"/"opp" を入れる（決定 kind は choose_player、選択肢キー you/opp＋絶対 player 番号。Option に player フィールドを追加）。「選んでもよい」は may の body に choose_player を入れて表す（T471 で検証）。
- プレイヤー指定の変数参照 `{var: 名前}`: op の player / players、セレクタの owner / chooser で使える。解決は `Engine._rel` が変数を引く1か所に集約（selector の owner は元々 _rel 経由、chooser も _rel に落ちる）。defs Checker は {var: 文字列} のみ許可し、それ以外（数値・別キー）は DefError。schema.py も VAR_REF で追随（player / players / owner / chooser）。
- 既存語彙で書けた周辺節: 「コストを支払わずに出た時」は `when: {unpaid: true}`＋効果側は `select: {ref: event.subject}`（dm24bd2-007 第2節）。「マナゾーンのカードを裏向きにする」は op `flip_down`（dm24ex4-025 第2節）。「山札の上からマナへ」は op `mana_put`。dm26sd1-p005 は ace: true（第179弾、types は [tamaseed] に正規化）＋第50弾の once マナ召喚静的（affects mana＋if is_turn＋allow summon_from_mana once）も併せて解消し、複合3ギャップごと登録見込み。※同カードの partial の unsupported 記述（「手札をすべて捨てる」）は原文と食い違っていたため、reject 行の原文（墓地をシャッフルし山札の下へ）を正とした。
- 差し戻し見込み1件: dm24ex1-sp7。「その持ち主は選ばれたカードを好きな順序で山札の下に置く」は並び順を決めるのが持ち主だが、move の order: choose は効果の使用者に聞くため表せない → refined gap `owner_ordered_deck_put`（choose_player 形は partial に残す）。なお dm25ex3-017（同型文面の既登録カード）は owner: any＋位置指定なしの粗い形で登録されていたが、本弾では真似ない。
- proto T469（CIP・プレイヤー選択→そのプレイヤーの墓地を山札に戻しシャッフル）/ T470（呪文・選択→そのプレイヤーが2ドロー1捨て。捨てる札は chooser {var} で本人が選ぶ）/ T471（CIP・may 内で選択→墓地をシャッフルして山札の下）/ T472（CIP・選択したプレイヤーの墓地から1枚選んで持ち主の山札の下→1ドロー）。tests/test_vocab_pilot192.py 9件（parse、不正形の拒否、自分を選ぶ／相手を選ぶの判別、呪文のドロー＆本人が捨てる、may 承諾／辞退、選んだプレイヤーの墓地から選ぶ、選ばなければ引かない）＋tests/test_vocab_pilot192_cards.py 2件（登録9件＋差し戻し1件の変換形が parse 可）。
- 判別確認: エンジン変更（defs.py＋schema.py＋types.py＋core.py＋ops.py）を退避すると pilot192 は 1 failed / 7 errors（choose_player が未知 op）。復元後9件全通過。回帰は pilot191/163/164/190＋file_schemas＋engine＋mechanics＋cost で 78 passed / 1 skipped。schema 再生成済み（差分は choose_player op と VAR_REF の伝播のみ）。Rust 側の変更なし。
- テスト作成の注意: 駆動（_drive）は攻撃決定が出ない盤面では相手ターンのチャージ決定まで進むため、相手の手札・山札の assert はターン開始ドロー分を数えること（第190弾の教訓どおり）。唱えた呪文自身も解決後に墓地へ行く。
- 待機10件（choose_player_effect 単独9件＋dm26sd1-p005 の複合）。再変換はラウンド228で実施（登録見込み9件＋差し戻し1件 dm24ex1-sp7）。

## 第193弾: marshal_touch（マーシャル・タッチ）のイディオム（2026-11-12）
「マーシャル・タッチ（このクリーチャーをバトルゾーンに出した時、自分の他のクリーチャーを1体、バトルゾーンから手札に戻してもよい。そうした場合、このクリーチャーの能力を使う）＋後続効果」は、ニンジャ・ストライク（第165弾）と同じくエンジンのキーワード能力にはせず、カード定義への展開形で表せる（新規エンジン語彙なし）。対象は marshal_touch 単独9件。
- イディオム: 出た時誘発 → `may` の body に [ `move`（自分の他のクリーチャー1体。selector の `other: true` で自身を除く → 手札、reason: return、`as: bounced`）, `if {exists: {ref: bounced}}` → 後続効果 ]。may を断る／戻せるクリーチャーがいない場合は後続効果を使えない、がそのまま出る。
- 後続効果のバリエーションは既存語彙で全部書けた: ブロッカー破壊（filter `keyword: blocker`）、戻したクリーチャー以下のコストを破壊（filter `cost_le: {cost_of: bounced}`。「戻すために選んだクリーチャー」は手札へ移動後も変数で参照できる）、自身へスピードアタッカー付与（modify grant＋duration end_of_turn）、パワー以下をすべて破壊、光または水のパワー以下破壊（filter civs）、他の自分のクリーチャー1体に「タップされていないクリーチャーを攻撃できる」（modify の allow attack_creature＋other {tapped: false}。第39弾 dm01-031 の静的形と同じ mod）、山札の上からマナへ（mana_put）、自分のクリーチャーすべてにスピードアタッカー付与。
- 併せて解消: dm37-031 のマナ爆誕7、dmex08-060 のマナ爆誕5 は第191弾のフィールドで付ける。dmex12-098 の【K・ソウル】は種族として扱う（dm36-029 の登録形と同じ。partial に欠けていたので足した）。
- proto T473（→ブロッカー破壊）/ T474（→戻したコスト以下を破壊）/ T475（→自身がスピードアタッカーを得る）。tests/test_vocab_pilot193.py 6件（parse、戻して破壊、may を断ると何も起きない、他のクリーチャーがいないと承諾しても後続なし、コスト相対の判別＝コスト3が残り候補が自動確定する、SA を得て出たターンに攻撃できる）＋tests/test_vocab_pilot193_cards.py 1件（登録9件の変換形が parse 可）。
- テスト作成の注意: (1) 召喚の支払いには出したカードの文明を持つマナが要る（T030 は光/水の双色。火の T473 には火のマナを置く）。(2) バトルゾーンは共有ゾーンで `zlist("bz", p)` は全件を返すため、所有の判定は Card.controller で絞る。(3) セレクタの候補が1件だけの時は選択の決定が出ず自動確定する（コスト相対フィルタの判別はこの性質と最終状態で確認した）。
- dm37-s05（第227弾で marshal_touch に差し戻し）は本弾の対象外: その誘発に残るのは「『マナ爆誕』能力を持つ／『マーシャル・タッチ』能力を持つクリーチャー」という能力持ちフィルタで、ラウンド229で refined gap `has_ability_filter` に差し戻す（mana_bakutan: 9 は partial に保存済み）。
- 待機9件。再変換はラウンド229で実施（登録見込み9件＋差し戻し1件 dm37-s05）。

## 第194弾: must_attack_creature_if_able のイディオム確認（2026-11-12）
「相手のクリーチャーが攻撃する時、可能ならクリーチャーを攻撃する」系のギャップ名は第171弾より前の命名で、構成要素は既に揃っていた（新規エンジン語彙なし）。対象は単独5件＋attack_untapped との複合1件。
- 対応表: 「可能ならクリーチャーを攻撃する」= mod `must_attack_creature`（第171弾。攻撃できるクリーチャーがいればプレイヤーへの攻撃選択肢が落ちる）。「可能であれば攻撃し」= キーワード `must_attack`（第30弾。require [attack] で攻撃ステップの pass が消える）。「可能であればそのクリーチャーを攻撃する」= mod `must_be_attacked`（第51弾）。期間「次の自分のターンのはじめまで」= modify の duration `until_next_own_turn_start`。
- カード形: dmrp18-087 は choose した相手1体に grant [must_attack]＋must_attack_creature。dmr14-054 は partial の modify（パワー+4000）に must_be_attacked を足すだけ。dmr23-022 は partial の第1モード（山札の上→シールド）を modal に包み直し、第2モードに相手全員への must_attack_creature 付与。dmrp04s-093 は相手全員付与のみ。dmex14-017（attack_untapped との複合）は CIP で全クリーチャーに allow attack_creature（other {tapped: false}、第39弾 dm01-031 の形）＋must_attack_creature を期間付き付与。
- 差し戻し1件: dmr10-016。「このカードが自分のシールドゾーンに表向きであれば」の常在型はシールドゾーンから効く静的で、静的の収集がバトルゾーン起点のエンジンでは表せない → refined gap `shield_zone_static`（キーワード類は partial に保存済み）。
- proto T476（1体に強制＋対象制限）/ T477（相手全員に対象制限、期間切れで解除）/ T478（タップ＋パワー+4000＋誘引）。tests/test_vocab_pilot194.py 4件＋tests/test_vocab_pilot194_cards.py 2件。
- テスト作成の注意: (1) 攻撃先の制限は「攻撃できるタップ状態のクリーチャー」がいる時だけ効く（いなければプレイヤー攻撃が残る）。検証では自分のクリーチャーに先に攻撃させてタップしておく。(2) 選択肢が1つだけの決定はエンジンが自動確定する（強制攻撃で対象がプレイヤーのみになると攻撃決定自体が出ない）。(3) シナリオは相手のターンから始まる周回があり、捕捉は「唱えた後」に限る。(4) 唱えた呪文自身も自分の墓地に入る。
- 待機6件（単独5＋複合1）。再変換はラウンド230で実施（登録見込み5件＋差し戻し1件 dmr10-016）。

## 第195弾: cross_free（コストを支払わずにクロスする）（2026-11-12）
対象は cross_free_permission 単独9件＋cross_free_op 単独5件。
- 許可（permission）: 新アクション `cross_free`（data/rules/permissions.yaml、default false）。`_cross_options` は支払い可否に加えて、ギア側 permits(gear, cross_free, creature) またはクリーチャー側 permits(creature, cross_free, gear) が通れば無料の選択肢 `cross:<ギア>:<クリーチャー>:free` を併記する（h_cross は free の時、支払いを飛ばして crossed を付ける。CrossTask に free を追加）。カード形は static の mod allow [cross_free] で、発生源は4形: クリーチャー自身（affects: self)、ギア自身（affects: self＋other フィルタ。other は進化なら {evolution: true}、リンクしているゴッドと併記なら any_of、名前は name_has、種族は race_has)、ギアから宿主へ（affects: crossed。宿主の特性に allow が載る）、全体付与（affects で自分のギア全体へ。dmex17-051)。
- 効果（op）: 新 op `cross_free {gear, to}`。gear セレクタのギアすべてを to セレクタのクリーチャー1体に支払いなしでクロスする。2つの選択が衝突しないよう、参照系セレクタ（ref / crossed_to / host_of / under_of / bundle_of）は op_swap と同じく candidates で引き、残りを select で引く（select を2回呼ぶと os の chosen が衝突する）。
- ついでに直した不具合: selectors の `_refs_of` が LKI 参照を alive で落としていたため、「破壊されたクリーチャーにクロスしてあったギア」を crossed_to: self で拾えなかった（crossed_gears 自体は LKI 照合が用途）。alive フィルタを外した（照合は crossed_gears の gen 完全一致が担う）。第170弾・第177弾の回帰は通過。
- dmex16-042 の「山札の上から3枚を見る」は choose {from_top: 3, look: true, count: all} as: pile の既存イディオム（束から選んで出し、残りを下へ）。dmc42-010 は partial の move（as: gear）の後ろに cross_free {ref: gear} を足す。
- proto T479（クリーチャー側許可）/ T480（ギア側許可・進化フィルタ。※フィルタの types は「いずれかを含む」照合なので、進化指定は {evolution: true} を使う）/ T481（タップ起動。choose でギアを束縛してから cross_free)/ T482（CIP で自分に）/ T483（破壊時に crossed_to で付け替え）。tests/test_vocab_pilot195.py 9件（parse、不正形、許可あり/なし、ギア側フィルタ、支払うクロスの回帰、起動、CIP、破壊時付け替え）＋tests/test_vocab_pilot195_cards.py 1件（登録14件の変換形が parse 可）。
- テスト作成の注意: (1) メインステップの決定は意味のある選択肢がある時だけ提示される（何もできない時は自動で進む）。(2) マナのタップ確認はクロス直後（次のターン開始でアンタップされる）。(3) bz は共有ゾーン: cid 引きは controller でも絞る。(4) 選択肢が1つだけの決定は自動確定する。
- 待機14件。再変換はラウンド231で実施（登録見込み14件）。

## 第196弾: eternal_kappa（エターナル・Κ）のイディオム確認＋置換の once_per_turn 対応（2026-11-12）
対象は eternal_kappa 単独5件。「このクリーチャーが離れる時、かわりに自分のマナゾーンにある裏向きのカードをN枚、表向きにしてもよい」は既存の置換 machinery で表せる（新規カード語彙なし）。
- カード形: {kind: replace, when: {event: move, from: bz, subject: self}（行き先を書かない＝どこへ離れる時でも）, optional: true（断れば元の移動が進む）, if: {cmp: [{count: {zone: mana, owner: you, filter: {face_down: true}}}, ">=", N]}（第23弾の水晶武装と同じ数え方）, instead: [{op: flip_up, select: {zone: mana, owner: you, filter: {face_down: true}, count: N}}]}。「各ターンに一度」版（dm24bd6-001、N=2）は once_per_turn: true を足す。
- ついでに直した不具合: once_per_turn は誘発の収集でしか見ておらず、置換側（_replacement）では無視されていた。登録済みの移動置換4件（dm26ex1-n008、dm25ex1-019、dm26rp1-016、dm24ex3-rp3s07）も「各ターンに一度」が効いていなかった。_replacement で候補収集時に印（turn_counters の once:replace:<cid>:<gen>:<添字>）を見て、選ばれた時に印を付けるよう修正した（断った場合は消費しない）。
- 注意: セレクタの「〜まで」は {count: N, up_to: true} と書く。{count: {upto: N}} は parse を通っても実行時に bad expr で壊れる（dm24ex2-041 の partial に保存されていた形を登録時に修正）。flip_down の候補には裏向きのカードも含まれるので、表向きだけを対象にする時は filter {face_down: false} を付ける。
- proto T484（Κ・3枚）/ T485（裏向き化の仕込み呪文）/ T486（各ターンに一度・2枚）。tests/test_vocab_pilot196.py 5件（parse、置換で残る、断ると離れる、裏向き不足では諮問自体が出ない、各ターンに一度）＋test_vocab_pilot196_cards.py 2件。回帰は第187・190・40弾＋mechanics＋engine で通過。
- 待機5件（全単独）。再変換はラウンド232で実施（登録見込み5件）。

## 第197弾: g_link_four_way（名前指定・4方向 G・リンク）（2026-11-12）
起源神・神帝・神王グループのリンクは位置キーワード（左/中央/右）では決まらず、「《A》の右横、《B》の上側」のように相手の名前と方向で決まる。面フィールドとリンク手順の分岐を足した。
- 面フィールド `link_to: [{name, pos}]`（pos は相手から見た自分の位置: right / left / up / down）。defs の Face/CardDef＋検証＋schema に追加（第191弾 mana_bakutan と同じ4点同期。定義フィールドは Rust state の対象外）。
- リンク手順（h_g_link）に名前指定の分岐を追加: 位置キーワードを持たず link_to を持つゴッドは、指定名のゴッドがいるグループ（選択肢は代表で提示される）にリンクする。同じ名前のカードは1グループに1枚まで（星座が一意に決まる）。リンク成立時は既存の link_established レコード（第155弾）を出すので、「リンクした時」誘発もそのまま受ける。特性統合・離脱置換（choose_link_leave）・link_count は既存のグループ機構を共用する。
- proto T487–T490（相互指定の2体＋3体目＋リンク誘発持ち）。tests/test_vocab_pilot197.py 9件（parse、不正な link_to、名前リンクと特性統合、相手なし、名前違いの判別、3体グループ、同名いるグループへの判別、離脱置換、link_established 誘発）。判別は events/core を stash すると5件失敗。回帰は第16・155弾＋engine＋mechanics＋schemas＋rust 同期で通過。
- 注意: rejects の行ギャップ名には付替え漏れがある（link_establish_event とだけ付いた行の実不足が gachinko_judge 等、別物の例を確認）。reopen のプール計算は行ギャップで行うため、複合ギャップの行は安易に reopen できない。ラウンド233は単独4件のみ reopen し、複合6件は submit の挙動を確認してから扱う。

## 第198弾: ggg_condition（G・G・G の条件違い）のイディオム確認（2026-11-12）
第167弾で G・G・G 本体（手札1枚以下）を実装した後に残った9件。unsupported は全件「G・G・G」の文言のみで、不足は GGG の当て方とカードごとの他条項だった。新規エンジン語彙なし。
- 当て方: 自己軽減は static {zone: hand, affects: self, if: 手札<=1, mod: {cost: -N}}。付与は static {affects, if: 手札<=1, mod: {grant}}（「マッハファイター」の付与はキーワードではなく allow attack_creature {other: {tapped: false}} で表す）。マスターG・G・G と複合条件は face の free_if（{all: [手札<=1, {not: {exists: 指定名}}]} の形も可）。
- 「各ターン、相手のクリーチャーがはじめて攻撃する時、可能ならこのクリーチャーを攻撃する」は static {affects: self, if: {cmp: [{turn_count: {kind: attack, owner: opp}}, "==", 0]}, mod: {must_be_attacked: true}}。第160弾の first_only（攻撃側ごとの初回）とは別物で、こちらはターン単位の初回を履歴カウンタで見る。
- 攻撃時の「上から1枚を表向きにし、種族とコストの条件を満たせば出す」は、choose で event.subject を変数に束ね（cost_of の引数にする）、look の pile から filter（any_of の種族＋cost_le {cost_of: 変数}）で hit を分ける（dm21-013 の骨格）。
- 「自分のターンの終わりに、アンタップしていれば手札に戻す」の条件は {exists: {ref: self, filter: {tapped: false}}}（T497 で判別確認）。
- proto T491（自己軽減）/ T492（自己付与）/ T493（複合 free_if）/ T494（初回攻撃タウント）/ T496（攻撃時公開）/ T497（ターン終わり帰還）。tests/test_vocab_pilot198.py 8件＋test_vocab_pilot198_cards.py 2件。
- 再変換はラウンド234で実施（登録見込み9件）。

## 第199弾: chosen_trigger（相手に選ばれた時）＋ must_be_chosen（2026-11-12）
「相手がこのクリーチャーを選んだ時」の誘発は既存だった（セレクタの決定経路が {ev: choose, subject, player: chooser} を誘発収集へ流す）。本弾は挙動の固定と、対になる選択強制の追加。
- choose 誘発の範囲: 対象が1体だけだと選択決定は自動解決されるが誘発はする。「すべて破壊」のような数え上げ経路は選んだことにならない。自分の効果で選んだ時は誘発しない。選ばれて破壊されても誘発は解決する（発生源から独立）。filter の power_le に {power_of: self} を渡すと「自分のパワー以下」の全体破壊になる。
- 新規 mod `must_be_chosen: true`（「相手が自分のクリーチャーを選ぶ時、相手は可能ならこのクリーチャーを選ぶ」）: defs の MOD_KEYS＋検証、chars へ集約し、セレクタの be_chosen フィルタ直後で、must_be_chosen を持つ候補がいるコントローラーの他のクリーチャーを候補から外す。このクリーチャー自身が候補にいない効果（フィルタ不一致）や、be_chosen 保護で先に外れた場合は制限しない。スキーマは MOD_KEYS から生成されるため再生成のみ。
- 併せて使う形: 選ばれた側の「相手はマナを3枚残して他を墓地へ」は choose {chooser: opp, count: 3, up_to: true} as keep ＋ move {count: all, exclude: {ref: keep}}（exclude は変数名ではなくセレクタ {ref: 名前} で書く）。EXライフシールド離脱の誘発は第190弾の subject {exlife_of: self}。
- proto T498（must_be_chosen）/ T499（choose 誘発ドロー）/ T500（全体破壊・対照）/ T501（自壊呪文・対照）/ T502（自パワー以下の全体破壊）。tests/test_vocab_pilot199.py 8件＋test_vocab_pilot199_cards.py 2件。判別は defs/core/selectors を stash すると崩れることを確認。回帰は第164・185弾＋engine＋mechanics＋schemas で通過。
- 再変換はラウンド235で実施（登録見込み9件）。

## 第200弾: cast_resolution_destination（唱えた後の置き場所）のイディオム確認（2026-11-12）
「唱えた後、墓地に置くかわりに〜に置く」は既存の2形で書ける。新規エンジン語彙なし。
- 他のカードの効果で唱える場合: op play_free の resolve_to / resolve_position（docstring に用例そのものがある）。行き先は hand / mana / deck（+ position: bottom）。
- 呪文自身の恒常的な行き先は面の resolve_to（チャージャー等）。条件つきの自己帰還（解決中の結果に依存するもの）は、置換の if が解決中の変数を読めないため未対応（ギャップ cast_destination_conditional として分離）。
- 誤ラベル発見: dm25ex1-021「水のクリーチャーが11体以上あればゲームに勝つ」は cast と無関係の常在勝利で、{kind: state, if: 条件, effect: [{op: win}]}（SBA で評価）で書ける（T505 で挙動確認）。
- 範囲外・未対応の分離: 超次元ゾーンへの配置（hyperdimensional_zone、範囲外）、シールドの束の上への配置（shield_pile_attach）、ブレイク前に唱える（before_break_cast）、跳次元召喚（choujigen_shoukan）は、それぞれ精緻化ギャップとして差し戻し、解けた節は partial に残した。
- proto T503（resolve_to: hand）/ T504（resolve_to: deck, bottom）/ T505（常在勝利）。tests/test_vocab_pilot200.py 4件＋test_vocab_pilot200_cards.py 2件。
- 再変換はラウンド236で実施（登録4件＋差し戻し5件の見込み）。

## 第201弾: sasageeru（ササゲール）のイディオム確認（2026-11-12）
ササゲール本体は既存だった（mod sac_reduce を持つ場のカードが、ディスペクター召喚時の軽減プールになる）。新規エンジン語彙なし。
- 純粋なササゲール・タマシードは static {affects: self, mod: {sac_reduce: N}} のみでよい（T506 で「マナ5＋ササゲール2でコスト7を召喚でき、生贄は破壊される」ことを確認）。
- 「ディスタス/ディスペクター・カードを自分のマナゾーンに置いた時、そのカードをアンタップする」は move（to: mana）誘発＋ {ref: event.subject} の untap で書ける。両カテゴリは種族名なので filter は any_of の races。多色カードはマナにタップで置かれる（405.1）ため挙動を観測できる（T507）。
- 「ササゲールを使った時、軽減したディスペクターに付与する」節は、生贄の破壊と召喚先を結ぶ印が無く未対応（ギャップ sac_reduce_followup）。
- proto T506（ササゲール玉）/ T507（マナ置き反応）。tests/test_vocab_pilot201.py 3件＋test_vocab_pilot201_cards.py 2件。
- 再変換はラウンド237で実施（登録6件＋差し戻し1件の見込み）。

## 第202弾: trigger_when_opponent_uses_s_trigger（相手がS・トリガーを使った時）のイディオム確認（2026-11-12）
「相手がS・トリガーを使った時」の誘発は既存だった（宣言時に合成レコード {ev: use_s_trigger, player: 使用者} が誘発収集へ流れる）。新規エンジン語彙なし。
- 受け方は {when: {event: use_s_trigger, player: opp}}。「2枚まで引く」は repeat 2 の may ドロー。「山札からS・トリガー呪文を探し、シャッフルしてから唱える」は choose（look, filter keyword: s_trigger）→ shuffle → play_free {ref}（シャッフルは参照を無効化しない）。
- 混同注意: 「相手がS・トリガーを持つカードを使った時」（唱える/召喚する）は use_s_trigger ではなく、cast レコードと召喚 move への subject フィルタ {keyword: s_trigger} で受ける（dmbd22-017）。
- テスト上の注意: declare_strigger 決定に空答えを返すと宣言しなかったことになる（min 0 のため）。宣言させるには選択肢を明示的に選ぶ。
- proto T508（盾反応獣）。tests/test_vocab_pilot202.py 3件＋test_vocab_pilot202_cards.py 2件。
- 再変換はラウンド238で実施（登録見込み8件）。

## 第203弾: unblocked_trigger（ブロックされなかった時）のイディオム確認（2026-11-12）
「攻撃してブロックされなかった時」は、攻撃宣言の誘発から {op: delayed_trigger, when: {event: break, player: 守る側}, duration: during_attack} を仕掛ける形で表す（dm23-045 の登録先例を一般化）。新規エンジン語彙なし。
- ブロックされればブレイクは起きず発火しない。ブレイク・レコードの subject はブレイクしたクリーチャーなので、遅延効果内では {ref: event.subject} で攻撃側を指せる。「攻撃の後、そのターンを終了する」は {op: end_turn}。「ブロック中パワー+N」は mod power_when {amount: N, when: blocking}。
- 「離れるかわりにとどまる」（条件つき）は kind: replace ＋ if（体数条件と {power_ge: 1}）＋ instead: [] で書ける。
- 範囲外: クリーチャーへの攻撃がブロックされなかった場合（ブレイクが無い）はこの形では拾えない → ギャップ unblocked_creature_attack に分離（dmex10-041。プレイヤー攻撃の形は partial に保存）。
- proto T509（未ブロック反応・ドロー、ブロック対照つき）/ T510（攻撃後ターン終了）。tests/test_vocab_pilot203.py 4件＋test_vocab_pilot203_cards.py 2件。テスト注意: ブロック決定の選択肢キーは guard: ではなく対象の bz:… キー。
- 再変換はラウンド239で実施（登録7件＋差し戻し1件の見込み）。

## 第204弾: henrei（返霊）のイディオム確認（2026-11-12）
返霊N は「攻撃誘発 → may［墓地からN枚を好きな順序で山札の一番下へ（move、order: choose、reason: put、as: paid）→ {cmp: [{var: paid}, "==", N]} の場合のみ本体効果］」のイディオムで書ける。新規エンジン語彙なし。墓地がN枚未満なら支払えず本体は発動しない。
- dm36-006 の「シールドを1枚選び、残りをすべてブレイク」は break の count を {sum: [{count: シールド数}, -1]} とし、ブレイク側が割る盾を選ぶことで等価に表す。ランダム手札捨ては {op: discard}（chooser 無し。dm12-025 先例）。
- 地獄返霊（「またはその能力を使った時」。dm36-005）は分岐の意味が別途必要なため新ギャップ jigoku_henrei に分離（攻撃時の形は partial に保存）。
- proto T511（返霊2→ドロー、支払い/辞退の対照つき）。tests/test_vocab_pilot204.py 3件＋test_vocab_pilot204_cards.py 2件。
- 再変換はラウンド240で実施（登録8件＋差し戻し1件の見込み）。

## 第205弾: labyrinth（ラビリンス）のイディオム確認（2026-11-12）
ラビリンスは条件名で、本体は {cmp: [{count: {zone: shield, owner: you}}, ">", {count: {zone: shield, owner: opp}}]} を static / trigger の if に置くイディオム。新規エンジン語彙なし。条件は評価のたびに読まれるためシールド数の変化に追随する。
- ファミリーの他条項の既存形: 攻撃先変更は起動型 {kind: activate, cost: {untap: self}, redirect: true}（第171弾）、モード選択は {op: modal, modes: [...]}、バトル勝利は {event: battle_win, subject: self}、「そのターン攻撃が無かった」は {turn_count: {kind: attack}} の条件、「次の自分のターンまで離れない」は modify の no_leave ＋ duration: until_next_own_turn_start。
- 範囲外（分離）: 効果で手札に加えたシールドの S・トリガー宣言（宣言の機会はブレイク処理にしか無い）→ shield_hand_strigger_use。誘発型の攻撃先変更（起動型 redirect と別）→ labyrinth_trigger_redirect。
- proto T512（静的パワー）/ T513（CIP ドロー）。tests/test_vocab_pilot205.py 4件＋test_vocab_pilot205_cards.py 2件。テスト注意: パワーは e.chars(cid)["power"] で読む。召喚の成否は「召喚直後の最初の決定」時点の手札で測る（攻撃ステップは自動で飛ぶことがある）。
- 再変換はラウンド241で実施（登録6件＋差し戻し2件の見込み）。

## 第206弾: rainbonus（レインボーナス）のイディオム確認（2026-11-12）
レインボーナスは条件付き能力の接頭辞で、本体は {exists: {zone: bz, owner: you, filter: {types: [creature], multicolor: true}}} を if に置くイディオム。新規エンジン語彙なし。
- 「攻撃できない能力を無視する」は鬼タイムの先例（dmrp14-079）と同型に書く: キーワードの展開形を id: above つき静的として直接書き、条件つき静的が mod {ignore_ids: [above]} で無視する。注意: submit はカードテキストからキーワードを補完するため、cannot_attack_player を keywords に残すと展開形の deny が二重になり ignore_ids が効かない（deny は id を持たない方も残る）。dmex14-042 は登録後にこの形へ修正し、多色あり/なしでの permits まで確認した。「次の相手のターンのはじめにアンタップしない」は tap op の no_untap_next（条件分岐は choose で束ねてから if/else で tap し分ける）。「はじめて攻撃する時」は when の ord {kind: attack_by, eq: 1}（第159弾）。
- proto T514（破壊誘発ドロー、多色あり/なし対照つき）/ T515（多色の試験獣）。tests/test_vocab_pilot206.py 3件＋test_vocab_pilot206_cards.py 2件。テスト注意: 攻撃対象にできるのはタップ状態のクリーチャーだけなので、相手の大型を先に攻撃させてタップさせる。
- 再変換はラウンド242で実施（登録7件の見込み）。

## 第207弾: deck_limit_exception（デッキ枚数制限の例外）の扱いの確認（2026-11-12）
「4枚以上デッキに入れることができる」はデッキ構築のルールで対戦中の能力ではないため、コーパスの先例（dmex13-057 等）どおり defs には表さず、残りの条項だけで変換する。新規エンジン語彙なし。
- ファミリーの形: 名前カウント条件の自己強化（{count: {filter: {name_has: …}}} の if ＋ mod {power, breaks}）、パワー閾値のブレイカー獲得（if {power_ge: N}。自己参照は _threshold_power が再帰を回避）、体数比例のパワーアタッカー（power_when {amount, count: <selector>, when: attacking}。selector の other: true で「自分の他の」）、2ゾーンにまたがるカウントの召喚コスト軽減（selector の zone はリスト可）。
- proto T516（遊撃師団 テスト兵）/ T517（閾値獣）。tests/test_vocab_pilot207.py 3件＋test_vocab_pilot207_cards.py 1件。
- 再変換はラウンド243で実施（登録8件の見込み）。

## 第208弾: j_crime（Jクライム）のイディオム確認（2026-11-12）
JクライムN は「攻撃誘発 → may［swap {out: {ref: self}, in: {zone: graveyard, filter: {races: [ジョーカーズ], cost_le: N}, count: 1}, out_to: graveyard}］」のイディオムで書ける。op swap（701.26）は入ったクリーチャーにタップ状態と攻撃中の状態を引き継がせる。新規エンジン語彙なし。
- proto T518（Jクライム獣、入れ替え/辞退の対照つき）/ T519（墓地ジョーカーズ）。tests/test_vocab_pilot208.py 3件＋test_vocab_pilot208_cards.py 2件。
- 再変換はラウンド244で実施（登録8件の見込み）。
