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

## 対象外（2026-11-06 ユーザー指示）

- outside_game 系は変換対象にしない。音読など実世界の行為に依存する内容のため。該当 gap: outside_game（12件、全て dmex08）

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
- 修正（2026-11-17、c1ebc1c）：第66弾の定義「civs が空＝無色」は誤りで、実際の無色カードは civs: [zero] で登録されていた（116件以上。civs == [] は29件のみ）。そのため filter {colorless: true} は本物の [zero] カードに一切一致せず、効果が黙って不発になっていた。修正：colorless := civs == [] または civs == ["zero"]（dmsim/engine/selectors.py:368 と engine.rs:773。Rust は cargo 無しのため未検証、スタンプは stale のまま）。tests/test_colorless_filter_fix.py 3件。影響：converted 22枚／29箇所（colorless: false は dmd10-007 天界の神罰の1箇所のみで、修正後は [zero] を正しく除外）。修正後の全体テスト：2,200 passed / 335 skipped / 0 failed。

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

### ラウンド297（第171弾/第194弾＋第251弾/第259弾/第164弾）

must_attack_creature_if_able の残り6件を再変換。新規4件（dm22rp1-023、dm24ex3-rp1010、dm24ex3-rp3s09、dmex12-046）、差し戻し2件。converted 10,075 / rejects 2,262、重複0・漏れ0。
- dm24ex3-rp1010 のハイパー面の破壊時誘発は if: {hyper: true}＋first_time（各ターンに一度）で、墓地から出すのは move to bz reason: put（「出す」は召喚ではない。play_free は召喚扱いのため使わない）。「それよりコストが小さい」は cost_le に {sum: [{cost_of: event.subject}, -1]}（第149弾の cost_of: event.subject の先例＋dmrp16-014 の -1 式）。
- dm24ex3-rp3s09 の「相手プレイヤーを攻撃する時」は when: {event: attack, target: player}。dmex12-046 の攻撃中止は may の mana_put（as: placed）後に if {exists: {ref: placed, filter: {races: [ドリームメイト]}}} then [cancel_attack]（dmd03-005 の形）。Dスイッチ2件は turn_start（player: opp）＋may の先頭に dswitch op。
- 差し戻し: dmrp16-s07 → 新ギャップ must_attack_creature_first_attack_of_turn。「各ターン、相手がはじめてクリーチャーで攻撃する時」は主語が相手プレイヤーでターンの最初の攻撃だけを指すため、攻撃側クリーチャー単位の初回だけを制限する must_attack_creature: {first_only: true} では正確に表せない（出た時能力とアバレチェーン＝first_time 誘発＋indestructible 付与は partial に保存）。dmr22-025 → 新ギャップ mana_tap_placement（「マナゾーンに置く時、タップして置く」。abilities() はマナゾーンのカードを拾わないため誘発型では書けない。パワー常在型＋呪文からの選ばれ防止＋Dスイッチは partial に保存）。
- tests/test_vocab_pilot194_cards.py にラウンド297分を追加（登録形＋差し戻し2件＋dm24ex3-rp3s09 の攻撃誘発の挙動テスト）。6 passed。

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

## 第209弾: alternative_summon_cost（代替コスト）のイディオム確認（2026-11-12）
代替コストは面の alt_cost フィールド（既存）で書く。新規エンジン語彙なし。
- マナ形式: {cost, civs, if?}（[ff02] = {cost: 2, civs: [fire, fire]}。if は提示条件）。行動形式: {do: [{zone, filter?, count, to, reason}]}（自分のクリーチャーを4体破壊する等）。
- 「そうしたら」の後続は条件 {alt_paid: true} で受ける（dm26ex2-075 の先例）。「ターンの終わりに破壊し1枚引く」は CIP 誘発（if alt_paid）から delayed_trigger {when: turn_end} に載せる。
- 未対応: 条件つきの追加軽減＋「その攻撃の後で破壊する」後続（after_attack_destroy として差し戻し）。
- proto T520（代替獣。代替提示/代替時の後続/通常支払いの判別/条件未成立で不提示）。tests/test_vocab_pilot209.py 4件＋test_vocab_pilot209_cards.py 2件。
- 再変換はラウンド245で実施（登録5件＋差し戻し3件の見込み）。

## 第210弾: number_choice（数字を1つ選ぶ）のイディオム確認（2026-11-12）
数字選択の op choose_number は既存（宣言プリミティブ。選んだ整数は GameState.declares に入り {declared: 名前} で読む）。新規エンジン語彙なし。
- コスト一致は filter の cost_le と cost_ge に同じ {declared: n} を置く。効果は modify ＋ duration until_next_own_turn_start で: 能力を無視する = {ignore: [all]}（バトルゾーンの相手エレメント全体）、唱えられない = 手札の相手呪文への {deny: [cast]}、攻撃もブロックもできない = {deny: [attack_player, attack_creature, block]}（action に単独の attack はない）。
- 宣言の決定は kind choose_one、キーは "num:<n>"。範囲の既定は 0〜10、上限つきの原文は max で指定する。
- proto T521（数字呪文。3効果すべてを行動で検証）/ T522（強化獣）/ T523（3コスト呪文）。tests/test_vocab_pilot210.py 3件＋test_vocab_pilot210_cards.py 2件。
- 再変換はラウンド246で実施（登録7件＋差し戻し1件の見込み。dm26ex1-n006 は数字選択ではなく登場反応のラベルずれ、dmrp21-002 は攻撃の終わりの処理が残る）。

## 第211弾: battle_end_trigger（バトルの後）のイディオム確認（2026-11-12）
バトルの終了時に両参加者を subject とする battle_end レコードが出る（combat.py。バトルで場を離れた参加者の誘発は拾われないが、「バトルの後に破壊する」は勝てば場に残っており負ければ既に破壊されているため意味が一致する）。新規エンジン語彙なし。
- 形: trigger {when: {event: battle_end, subject: self}}。「ブロックした時」は相手のターン = 防御側として if {is_turn: opp} を添える。
- proto T524（バトルの後に自壊。勝ちバトル/バトルなしの対照つき）/ T525（ブロック後にアンタップ）。tests/test_vocab_pilot211.py 4件＋test_vocab_pilot211_cards.py 1件。
- 再変換はラウンド247で実施（登録6件の見込み。dmd02-004 の partial には「クリーチャーを攻撃できない」が落ちていたため deny [attack_creature] の static を足して登録する）。

## 第212弾: mana_number_change（マナの数字の変更）（2026-11-16）
支払い（_mana_choices）でのマナの数字を変える入口を3つ新設した。基本値は定義の mana（裏向きは水晶ソウルで置換）のまま変えていない。
- 面フィールド mana_boost {filter?, value, optional?}: 出すカード自身の宣言で、この支払いでのみ効く。必須形は「このクリーチャーを召喚する時、〜のマナの数字は1のかわりに2になる」（dmx19-s42 型）、任意形は「好きな数を選び〜2にしてもよい」（dmx19-v01 型）。
- 常在型の mana_boost {value | values, filter?, scope?, if?}: バトルゾーンの発生源から支払う側のすべての支払いに任意形で効く（dmx06-002 型）。scope: spell は呪文の支払いだけ（dmrp18-008 型）。if は発生源の条件（「各ターン、はじめて呪文を唱える時」は if {cmp: [{turn_count: {kind: cast, owner: you}}, "==", 0]} で受ける）。
- mod mana_number（int >= 2）: affects {zone: mana, owner: you} の常在型が「自分のマナゾーンにあるカードのマナの数字をNにする」を置換する。chars の mana_number（重なったら大きい方）で読み、条件は通常の if（dm24bd5-014 のシビルカウント、dm26rp1-006 のタイプ数条件）。
- あわせて式 distinct_type_count {selector} を追加（対象群のカードタイプの種類数。多重タイプはすべて数える。distinct_cost_count と同じ再入回避の作法）。
- _mana_choices は値の選択肢ごとにマナカードを分けて数える（任意形がある時だけ分岐が増える。通常の支払いは従来どおり）。文明の判定は山（プール）単位のまま。
- proto T526（必須形）/ T527（任意形）/ T528（常在型ブースト）/ T529（scope: spell）/ T530（mana_number＋タイプ数条件）/ T531（ゴッド見本）/ T532（ドラゴン見本）/ T533（高額呪文）/ T534（対照獣）/ T535（values [2, 3]）。tests/test_vocab_pilot212.py 8件。水晶ソウル（第154弾）・エンジン・スキーマ同期の回帰確認済み。Rust はこの環境では stamp 旧版のため Python のみで動作（CLAUDE.md の作法どおり結果は一致する）。
- ついでに when の subject 指定へ zone を追加した（_subject_match: 「自分のマナゾーンのカードをタップした時」のように、イベントの主体のいるゾーンで絞れる。離れた時は lki のゾーンで見る）。proto T536（マナタップ墓地獣）で照合を確認。
- ただし支払いのマナタップは現状イベント化されておらず（h_play 等が直接 tapped を書き換える）、「タップした時」は支払いでは誘発しない。イベントとして流れるタップ（起動コスト・効果）でのみ誘発する。支払いタップのイベント化は mana_tap_trigger として別途残る（dmx08-010 はこの不足で差し戻し。ブースト側は partial に保存済み）。
- 再変換はラウンド248で実施（対象9件）。

## 第213弾 suppress_entry_triggers（出た時能力の誘発抑制）

「出て、その能力がトリガーする時、かわりにその能力はトリガーしない」を2つの入口で実装した。

- move op の引数 `no_trigger: true`（opvocab と ops の宣言に同期追加）: その移動でバトルゾーンに出たカード自身の出た時能力は誘発しない。op_move が各イベントに印を載せ、適用レコード（_apply_one）と照合レコード（_record_for）の両方へ伝播させ、誘発収集で「発生源＝移動対象」の時だけ落とす。他のカードの観測誘発は通常どおり誘発する。重ね出し（stack_evo）の経路には載せていない（対象カードが無いため）。
- 常在型の能力キー `suppress_triggers` {whose: opp, events: [enter / attack, ...], if?}: 相手のクリーチャーが出た（enter）／攻撃した（attack）出来事で誘発する相手側の能力すべてを誘発させない（出た本人の能力に限らない。カードの例示「例えば、相手は『このクリーチャーが出た時』で始まる能力を使えない」の読みどおり、同じ出来事で誘発する観測能力も対象）。誘発収集で、出来事の主体のコントローラと誘発のコントローラが一致する時だけ、相手のバトルゾーンの発生源を引く（定義集合はキャッシュ）。キー名は YAML の真値語 `on` を避けて `events` にした。
- proto T537–T543、tests/test_vocab_pilot213.py 9件（no_trigger の本人抑制・対照・観測は誘発する、常在型の enter 抑制・対照・観測まで届く範囲・自分の側は抑えない、attack 抑制と enter 専用では止まらない対照）。
- 教訓: 移動レコードは _record_for（置換照合用）と _apply_one（収集用）の2箇所で別々に組まれる。新フラグは両方へ伝播させないと収集側に届かない（初回は _record_for だけに入れて不発だった）。

### ラウンド249（第213弾の再変換）

reopen suppress_entry_triggers で4枚（残り2枚は理由なし行で直接 submit）。**新規登録5件**: dm23rp2x-018 冥逝邪夢（山札上3枚を墓地＋マナ枚数以下のコストのクリーチャーをすべて墓地からタップして出す。cost_le に count 式、no_trigger）、dm25ex3-rp3s09 「GG」-001（NEO進化 neo: true + evolve_from 文明3色。suppress は if {count: {under_of: self} >= 1} ＝進化している時だけ）、dm26ex1-026 ブラキオ龍樹（fushigi {cost: 13, civs: [nature], min: 1} + suppress enter）、dm26ex4-cho019 / dmart26-006 終末縫合王 ザ=キラー・キーナリー（EXライフ。出た時: choose → if exists → may バウンス + その cost_of 以下のクリーチャーを墓地から出す。suppress enter）。**差し戻し1件**: dm26ex4-013 鮫鰐竜 ACE-Agony / 覚醒の杯（ツインパクト）→新ギャップ **enter_rules_ignore**: マナからの自己召喚許可（static zone: mana, affects: self, allow summon_from_mana）・両者の墓地から好きな数出し（count: any + chooser: opp、no_trigger で誘発抑制は表現済み）・呪文面（3ドロー3捨て＋チャージャー）は partial に保存済み。残るは「出ることによって起こるルールもすべて無視する」範囲（フィールド一意性・リンク手順等）のみ。suppress_entry_triggers の行は消滅。converted 9,887 / rejects 2,455、重なり0・漏れ0。tests/test_vocab_pilot213_cards.py 3件通過（冥逝邪夢の実挙動＋ブラキオ龍樹の抑制を含む）。

## 第214弾: revenge_chance（リベンジ・チャンス）のイディオム確認＋履歴の from 修飾（2026-11-17）

リベンジ・チャンス（各ターンの終わりに条件を満たせば、手札からコストを支払わずに召喚してもよい）は既存語彙のイディオムで表せる。新規の能力語彙は無し。

- 形: {kind: trigger, zone: hand, when: {event: turn_end}, if: 条件, effect: [may [play_free {select: {ref: self}}]]}。自己無料召喚はアタック・チャンス／ニンジャ・ストライク（第165弾）と同じ play_free {ref: self}。turn_end は両者のターンの終わりに発火し、条件は「相手のそのターン」で判定する。
- 条件の書き分け: 相手の大物がいる = exists {zone: bz, owner: opp, filter: {any_of: [{cost_ge: N}, {power_ge: M}]}}。相手がそのターン出した数 = turn_count {kind: enter, owner: opp}。引いた数 = turn_count {kind: draw, owner: opp}（開始ドローも draw レコードで数える）。
- 追加した語彙は履歴式の from 修飾だけ: {turn_count: {kind, owner?, from: <zone>}}。移動で数える kind（shield_put / mana_put / enter / discard）は通常カウンタと並べて hist:<kind>_from_<zone> にも集約し（events._hist_bump_from）、式は修飾つきキーを読む。「山札からシールドゾーンに新しいシールドを加えた」を、手札から加えた場合（シールド・プラス系）と区別するために必要だった。defs の turn_count 検証にも from を追加。
- proto T544（exists 条件）/ T545（enter 数）/ T546（shield_put from: deck）/ T547（draw 数）/ T548（手札→シールド呪文。from 対照用）/ T549（山札→シールド呪文）/ T550（2ドロー呪文）/ T551（1コスト獣）。tests/test_vocab_pilot214.py 10件（条件成立・拒否・未成立、from の有無で shield 条件が分かれること、を含む）。
- 再変換はラウンド250で実施（対象6件: 登録5件＋差し戻し1件の見込み。dm25ex4-t13 は条件が超次元ゾーンからの登場＝範囲外のため、revenge_chance_hyperdimensional へ精緻化して差し戻す）。

### ラウンド250（第214弾の再変換）

reopen revenge_chance で6枚。**新規登録5件**: dm24ex4-022 地雷冥土The World Is Mine（exists any_of 条件＋タップ時誘発: choose → destroy → if exists → may で cost_le {cost_of: tgt} の非進化を墓地から出す）、dm38-014 風来の用心棒クマっ太（turn_count enter 条件。CIP は chooser: opp で相手が自身のクリーチャーをマナゾーンへ。partial の text が切り詰められていたため reject 行の公式テキストを採用）、dmx12b-092 反射の大地カプリコン（turn_count shield_put from: deck 条件）、dmx18-020 ベニジシ・スパイダー（turn_count draw 条件。CIP は partial の既存能力を維持）、dmx19-s44 剛撃無双カンクロウ（exists any_of 条件。W・ソウルを種族に追加＝K・ソウルの前例どおり partial に欠けていた）。**差し戻し1件**: dm25ex4-t13 熱血龍 バトリベンジ → 新ギャップ **revenge_chance_hyperdimensional**（条件が超次元ゾーンからの登場＝範囲外。CIP の force_battle と battle_power +2000 は解けた条項として partial に保存）。revenge_chance の行は消滅。converted 9,892 / rejects 2,450、重なり0・漏れ0。tests/test_vocab_pilot214_cards.py 4件通過。

## 第215弾: mana_count_doubled（マナの数字の倍加）のイディオム確認（2026-11-17）

「このクリーチャーを召喚する時／この呪文を唱える時、自分のマナゾーンにあるオリジンのマナの数字は、1のかわりに2になる」（DM34 のオリジン一族）は、第212弾の面フィールド mana_boost の必須形でそのまま表せる。新規語彙は無し。

- 形: 面フィールド mana_boost: {filter: {races: [オリジン]}, value: 2}。必須形はこの支払いでのみフィルタに合うマナの数字を置換する（第212弾の values_of）。出すカード自身の宣言なので、他のカードの支払いには漏れない。呪文形（「この呪文を唱える時」）も同じ面フィールドで効く（支払いは _mana_choices で共通）。
- proto T552（オリジン見本）/ T553（倍数獣・クリーチャー形）/ T554（倍数呪文・呪文形）。tests/test_vocab_pilot215.py 6件（支払い組み合わせ: 2+2、混在 2+1+1、非オリジンでは不足、通常マナ4枚でも可／他カードへの非漏洩／呪文形の組み合わせ／実プレイでの召喚・唱える＋ドロー）。
- 再変換はラウンド251で実施（対象5件: dm34-034 / 037 / 043 / 044 / 048。うち dm34-043 は partial に呪文本体が無く、dm34-048 は CIP が欠けているため、公式テキストから補って登録する）。

### ラウンド251（第215弾の再変換）

reopen mana_count_doubled で5枚。**新規登録5件**: dm34-034 オリジナルネイチャー / dm34-037 ピュアオリジナル / dm34-044 ヤミノオリジナル（いずれも partial に面 mana_boost {filter: {races: [オリジン]}, value: 2} を足すだけ）、dm34-043 オリジナル・ブレイン（呪文形。partial に呪文本体が無かったため公式テキストから構築: choose {from_top: 4, look: true} で pile に束ね、count: 2 + up_to で2枚まで手札へ、残りを山札の下へ＝dm22-043 のイディオム）、dm34-048 オリジナルグレンオー（partial に欠けていた CIP「相手の『ブロッカー』を持つクリーチャーを1体破壊」を filter {keyword: blocker} の destroy で追加）。dm34-043 / 048 は partial の text が切り詰められていたため reject 行の公式テキストを採用。mana_count_doubled の行は消滅。converted **9,897** / rejects **2,445**、正規 id の重なり0・漏れ0（エイリアス水準の既存重なり7件は従前どおりで本ラウンドとは無関係）。tests/test_vocab_pilot215_cards.py 4件通過。

## 第216弾: final_declaration（終極宣言）のゲート＋game 印のプレイヤー別化（2026-11-17）

公式Q&A（dm.takaratomy.co.jp/rule/qa/44220）: 「終極宣言」はプレイヤーごとにゲーム中一度だけ。どのカードの宣言を使っても、その後は同じプレイヤーの他の終極宣言も使えない。効果を何も使わなかった（使わないを選んだ）場合は消費されず、次の自分のターンのはじめに再びトリガーする。相手は独立に一度ずつ使える。

- ゲートの形: trigger {when: {event: turn_start, player: you}, if: {not: {marked: {name: final_declaration, scope: game}}}, effect: [if {not marked} then [may [<効果>, {op: mark, name: final_declaration, scope: game}]]]}。内側の if は、複数の終極宣言が同じターン開始に同時トリガーした時の再確認（先に使った方で印が立ち、後の方は静かに解決する）。
- 基盤変更: mark の scope: game はプレイヤーごとに印を分ける（_mark_key が game スコープの時だけ名前＋プレイヤー番号をキーにする）。使用履歴は各プレイヤーのもので、従来の「名前そのまま」のキーでは相手の使用で自分の分まで消費されてしまう。scope: game の印を使う登録カードはまだ無く、影響は tests/test_vocab_hist_counters.py の期待キー更新のみ。
- 注意（発見した潜在問題・本弾では未修正）: when の subject: self は、subject を持たない tick レコード（turn_start / turn_end のレコードは {ev, player} のみ）とは決して一致しない（_match_when は subject 不在で不一致を返す）。{event: turn_start, subject: self} と書かれた登録済みカードが turn_start / turn_end 合わせて数十枚あり（dm21-s04 で実測: 誘発しない）、「自分のターンのはじめに」の正しい形は player: you。影響範囲が大きいので、専用の弾で全体テストとセットで直す。
- proto T555 / T556（宣言: カードを2枚引く）。tests/test_vocab_pilot216.py 4件（使用で消費・使わないと再トリガー、2体での共有ゲート、プレイヤー独立性）。
- 再変換はラウンド252で実施（対象7件: 各カードの宣言効果は個別に構築し、正確に表せないものは残余を精緻化して差し戻す）。

### ラウンド252（第216弾の再変換）

reopen final_declaration で7枚。**新規登録6件**:
- dm23rp4x-08a シス＝魔＝シャル: CIP は「自分の墓地枚数以下のコストの他のクリーチャーをすべて、タップして持ち主のマナゾーンに置く」（select の owner: any が必要。既定は you で相手のクリーチャーが選ばれない）。宣言はマナ/墓地からアビスを3体まで。印は「実際に出した時」だけ立てる（exists {ref: put} で確認してから mark）。
- dm26rp1-tr003 審判の精霊ラストジャッジ: CIP は tap + no_untap_next（次の相手のターンのはじめにアンタップしない）。宣言はブロッカーを好きな数出し、自分のブロッカーが12体以上なら追加ターン。印は「出した or 追加ターンが発生した時」だけ立てる。
- dm23rp4x-01b 富轟皇 ゴルギーニ・エン・ゲルス: 「このターンにシールドが離れていなければ離れない」は turn_count {kind: shield_left, owner: you} == 0 の間の常在型 no_leave。宣言は modal {count: 4, repeat: true}（相手を破壊＋1ドロー／山札上をシールド化＋墓地から1枚回収）。
- dm26sd1-q001 超重竜 ゴルファンタジスタ: 自分のジャイアントへの unblockable 付与常在型、CIP はマナからコスト6以下のジャイアントを出す。宣言は draw {count: 手札枚数の式} の後、mana_put {from_top: マナ枚数の式}（from_top は式で書ける）。
- dm23rp4x-06a 芸魔龍馬 バルバトチェス: CIP はパワー10000以下を破壊して2枚引く。宣言は modify {dynamic: true} でこのターン手札のマジックを -4（cost_min: 0）＋ delayed_trigger {duration: end_of_turn} で「マジックを唱えた時、1枚引いてもよい」。
- dm26sd1-g003 ボルシャック・ヴォルジャアク: 出た時（各ターン1度、誰のクリーチャーでも）山札上をシールド化、破壊された時に名前に《ボルシャック》とあるコスト7以下を手札から出す。宣言は自シールドをすべてブレイク（move reason: break）＋ no_lose {duration: until_next_own_turn_start}。

**差し戻し1件**: dm23ex3-or2 アビスベル=覇統=ジャシン帝 → 新ギャップ **final_declaration_no_trigger_summon**（宣言の「出た時にトリガーする能力はトリガーしない無料召喚＋このターン、それらは相手プレイヤーを攻撃できる」が未表現）。解けた条項（相手のコスト10以上がいる間の「離れない」常在型、自分のシールドがブレイクされた時の破壊誘発）は partial に保存した。

submit 時の注意: dm26rp1-tr003 に「play_free は召喚・唱えるの意味。原文に召喚・唱えるが無い」という警告が出たが登録は成立。コーパスでは「手札から出してもよい」に play_free 55件 / move（reason: put）45件と両形式があり、本ラウンドは play_free に統一した。

converted **9,903** / rejects **2,439**、正規 id の重なり0・漏れ0、final_declaration の行は消滅。tests/test_vocab_pilot216_cards.py 9件通過。

## 第217弾: reversal_strike（逆転撃）＋ op pay_or_lose（2026-11-17）

逆転撃 {支払い}: クリーチャーが自分を攻撃する時、その攻撃中にまだ「逆転撃」を使っていなければ、この呪文を自分の手札からコストを支払わずに唱えてもよい。そうしたら、次の自分のターンのはじめに {支払い} を支払う。支払えなければ、自分はゲームに負ける。対象は singles 8件（うち3件は呪文本体に超次元条項があり範囲外 — ラウンド253で精緻化して差し戻す）。

- 支払いの記法: {ll03} は「合計3・そのうち光2枚」。{ww02} は合計2・水2枚（印刷コスト3とは別物）。写像は pay_or_lose {cost: 合計, civs: [必要文明を1枚分ずつ]}。
- ゲートの形: declare {zone: hand, when: {event: attack, subject: {owner: opp}, target: player}, if: {not: {marked: {name: reversal_strike, scope: attack}}}, effect: [if {not marked} then [mark scope: attack, play_free {ref: self}, delayed_trigger {…}]]}。when の target: player が「自分を攻撃する時」（自分のクリーチャーへの攻撃は対象外）。使用宣言は窓の中でまとめて選ばれる（h_declare）ため、解決時の再確認（内側の if）が要る — 第216弾の同時トリガー再確認と同じ理由。
- 後払いの形: delayed_trigger {when: {event: turn_start, player: you}, duration: permanent, effect: [pay_or_lose]}。duration: until_next_own_turn_start は不可 — ターン開始ステップ（st_start）の失効処理が turn_start の記録より先に走り、誘発前に消える。permanent＋once（既定）で「次の自分のターンのはじめに一度だけ」になる（登録カードにも先例あり）。
- 新規 op pay_or_lose {cost, civs}（opvocab＋ops.py）: 払える場合は支払いは任意ではない（組の選択だけがプレイヤーの決定、ask "pay_mana"）。払えなければ game_lose（op lose と同じ口で置換を諮る）。
- 同期点の注意: 新規 op は data/schema/card.schema.json の再生成（python -m dmsim.cards.schema）も必要。生成し忘れると submit が「スキーマ不一致」で全件止まる（エラー表示は if ブロック先頭で切り取られ、原因が op 本体だと分かりにくい）。第214弾の castle_of の教訓と同じ「登録漏れ」型。
- 基盤変更: _mana_choices に raw_cost を追加。カードを出すための支払いではないので、コスト増減（pay_cost）・水晶ソウル・出すカードの面 mana_boost・場の常在型 mana_boost を適用せず、金額と文明をそのまま数える（マナの数字そのものを変える mod mana_number は効く）。発生源は支払いプールから外れるため、アンカーはマナゾーンの外にある前提。ついでに事前チェックの必要枚数を d.civs から「実際に使う need（civs 指定時）」に合わせた（従来は civs 指定時にだけ過剰に厳しい食い違いがあった）。
- Rust: この環境には cargo が無いため dmcore の再構築は未検証。verified_engine.txt は据え置き（stamp が古い間は自動で Python のみで動く。CLAUDE.md の手順どおり、ビルドできる環境で再構築＋test_rust_*＋再記録を行うこと）。
- proto T557 / T558（逆転撃つき呪文、本文はドロー1）。tests/test_vocab_pilot217.py 6件（無料詠唱＋次ターン支払い、支払えず敗北、同一攻撃での共有ゲート、攻撃ごとの再使用、クリーチャー攻撃では不発、parse）。
- 再変換はラウンド253で実施（対象8件）。

### ラウンド253（第217弾の再変換）

reopen reversal_strike で8枚。**新規登録5件**:
- dm24ex3-rp3001 正義の逆転撃: 後払い {ll03} = 合計3・光2枚。本文は draw 1 → may で光のコスト3以下を手札から出し、次の自分のターンのはじめまでブロッカーを与える（play_free as: put ＋ exists 確認後に modify grant）。
- dm24ex3-rp3003 自由の逆転撃: 後払い {ww02} = 合計2・水2枚（印刷コスト3とは別）。本文は相手2体まで deny [attack_player, attack_creature, block] を次の自分のターンのはじめまで。
- dm24ex3-rp3007 伝説の逆転撃: 後払い {ff02} = 合計2・火2枚。本文は choose 2体 → force_battle（b 省略で先頭2体同士）。
- dm24ex3-rp3009 情熱の逆転撃: 後払い {nn04} = 合計4・自然2枚。本文は自然のコスト5以下をマナからタップして出す（move reason: put, tapped: true, as: put）＋ must_be_attacked を次の自分のターンのはじめまで。
- dm26ex3-032 深淵の逆転撃: 後払い [dd03] = 合計3・闇2枚。本文は相手1体のパワーを -999999（-∞ の登録済みイディオム、end_of_turn）。

**差し戻し3件** → 新ギャップ **reversal_strike_hyperdimensional**（逆転撃側は全件解決し、宣言能力＋解けた本文を partial に保存）:
- dm25ex4-s02 流星の逆転撃: 「相手を手札に戻す」まで保存。残余は超次元ゾーンからの召喚。
- dm26ex4-015 DREAMの逆転撃: 「自他1体ずつのバトル」まで保存。残余は超次元召喚（ウエポン装備含む）＋ **ignore_deny_cast**（唱えられなくする効果を無視する）も併記。
- dm26ex4-018 NIGHTMAREの逆転撃: 本文が超次元ゾーンへの移動＋GR召喚で、保存は宣言能力のみ。

converted **9,908** / rejects **2,434**、正規 id の重なり0・漏れ0（エイリアス水準の既存重なり7件は baseline と同一で無関係）。tests/test_vocab_pilot217_cards.py 4件通過（登録形 parse 5件＋rp3001/rp3007/032 の実挙動）。

## 第218弾 chou_mugen_evolution（超無限進化）

対象: 単独ギャップ9件。既存の evolve_any（1体以上の進化元。超無限墓地進化・超無限G-NEO進化で使用）が土台にあり、不足は3点だった。

- **文明条件 evolve_civs**（面の新フィールド）: 選んだ進化元の集合が指定文明を全て含むこと。h_play の選択は1体ずつの逐次選択にし、揃うまでは min=1（止まれない）、揃った後は min=0 で追加も可。_can_play_face は候補全体の文明の和集合で実現可能性を判定。defs は evolve_any 必須を検証。タスク側の選択途中状態は PlayTask に evo_civs_sel を登録（types.py の型形状チェックに引っかかるため必須）。
- **超無限進化Ω evolve_zones**（面の新フィールド）: 進化元を複数ゾーンから探す（_evo_pool が和集合化）。併せて2つの一般化: (1) events.py の stack_more 適用は墓地の進化元しか場へ移していなかった → stack_on 本体と同じく「bz でなければ _raw_move で場へ」に一般化（マナの進化元が下に重ならなかった）。(2) h_play の支払いは進化元に確定したカードを _mana_choices の exclude で支払いプールから外す（マナゾーンの進化元を支払いに使えてしまい、二重使用になっていた）。実現可能性判定（_can_play_face）は従来どおり寛容（全候補を重ねる前提）で、選んだ進化元のせいで払えなければ play は手札に戻る（既存の choices 空→pop と同じ扱い）。
- **ソウルシフト∞ soul_shift {floor}**（面の新フィールド）: 実際に重ねた進化元の合計コストぶん軽減し、floor 未満にはならない（ゴウケンオー floor 0 / Guy-R floor 1）。支払い側は t["evo"] の実コスト合計、実現可能性側は全候補の合計で判定。cost_reduce_per_evo（体数×固定値）とは排他に近いが、両方あれば soul_shift を優先。
- 同期点: defs（Face/CardDef/parse/検証）・schema.py（型付きで追加）・dataaudit _STRUCT_FIELDS・card.schema.json 再生成・types.py（PlayTask）。Rust 側（rules.rs の Face 相当・rustcore の受け渡し）は cargo の無い本環境では未対応で、stamp は古いまま（Python フォールバック。第217弾と同じ扱い。再構築できる環境で evolve_civs/evolve_zones/soul_shift の3フィールドを追加すること）。
- proto T559（素の超無限進化）/ T560（文明条件: 光水火）/ T561（Ω: 墓地・マナ・場）/ T562（ソウルシフト∞ floor 0、無色）。tests/test_vocab_pilot218.py 8件: parse、2体積み、1体積み、文明不足では出せない、逐次選択（揃うまで min=1）、Ωの3ゾーン積み、軽減 10-7=3 の支払い、floor 0 で無支払い召喚。
- ついでに発見した既存データ不具合を修正: dm23ex2-048 イプシロン・トゥレイト（main 側変換分、baseline 時点で既在）は本文が「進化：サバイバー1体の上に置く」なのに types に evolution が無く evolve_from も欠けていた（同系統のゼータ/シータ・トゥレイトと同じ形に修正）。これは converted を読み込む状態で test_data_audit が踏む潜在違反で、cards テスト群が DMSIM_SKIP_CONVERTED を外すためフルスイートでも表面化しうるものだった。

### ラウンド254（第218弾の再変換）

reopen chou_mugen_evolution で9枚。**新規登録7件**:
- dmex17-012 ファイナル・ストームXX NEX: evolve_from {race_has: ドラゴン}＋evolve_any。召喚コスト軽減は static {affects: self, zone: hand, mod: {cost: {amount: -2, count: {zone: mana, owner: you, filter: {race_has: ドラゴン}}}}}（ダブル・シンパシーの登録形）。CIP/自ターン開始の「上から1枚を表向きにし、ドラゴンなら下に重ねる」は choose {from_top: 1, look: true} → exists {ref, filter} → put_under。メテオバーンは move {under_of: self, count: all, up_to: true} as: paid → cmp [{total_cost: {ref: paid}}, >=, 20] → extra_turn。
- dmr04-015 ディス・オルトロス: evolve_civs [light, darkness, fire]。各ターン開始は trigger を player: you / player: opp の2本に分け、相手分は select に chooser: opp を付けて「そのプレイヤーが自分のを選ぶ」を厳密に表現。多色カードのマナタップはルール405.1（core の _raw_move）で内蔵済みのため本文1行目は注記扱い。
- dmr08-001 イギー・スペシャルズ: evolve_zones [graveyard, mana, bz]＋evolve_any。無色の指定は filter {civs: [zero]}（後述の注意）。攻撃時は repeat {times: {count: {under_of: self}}} の中に modal {count: 1}（モード決定の kind は choose_mode）。相手手札の無作為移動は select {chooser: random}。
- dmr08-007 タテブエ・ヤッホー: 素の超無限進化。メテオバーンは may [move {under_of: self, count: 1} to: shield reason: charge as: paid] → exists 確認後に delayed_trigger {when: turn_end} で untap（duration 省略 = end_of_turn が既定で正しい）。
- dmrp21-tr3 愛の無限オーケストラ: evolve_civs 5文明。メテオバーンは choose {from_top: 3, look: true} as: rev → play_free（多色クリーチャー → 多色呪文の順、count: all, up_to: true）→ 残りを move {ref: rev, count: all} to: deck position: bottom order: choose（dm34-043 の残り処理と同じく、ref は移動済みを除いた残りを指す）。
- dmx15-v02 Guy-R: evolve_from {race_has: アウトレイジ}＋soul_shift {floor: 1}。攻撃時は filter {power_le: {sum: [{power_of: {ref: self}}, -1]}}（第116・126弾の登録形）で全破壊。
- dmx19-s14 ファタル・スパイラル: evolve_from {any_of: [{races: [オリジン]}, {race_has: ドラゴン}]}。CIP は repeat {times: {count: {under_of: self}}}＋may バウンス。

**差し戻し2件**:
- dmr04-003 ハカイ・デストロイヤー → 新ギャップ **shield_break_intercept_cast**（ブレイク横取り: シールドを見せ、中の呪文を唱えて墓地に置いてからブレイクする手順）。文明条件つき進化定義は partial に保存。
- dmex18-023 ゴウケンオー → 新ギャップ **stack_creature_from_deck**（山札を見て非進化クリーチャーを一番上に重ねる操作が無い。move の stack_evo は進化専用、stack_on はシールド専用）。進化＋ソウルシフト∞の定義は partial に保存。

converted **9,915** / rejects **2,427**、正規 id の重なり0・漏れ0（エイリアス水準の既存重なり7件は baseline と同一）。tests/test_vocab_pilot218_cards.py 8件通過。

**注意（今回の発見）**: filter {colorless: true} は chars の civs が空リストの定義にしか一致しないが、実データの無色カードは civs: [zero] で登録されているため一致しない（dm23ex2-090 で実測）。converted には colorless: true を使う既存カード（奇石 オリオン等）があり、対象が [zero] のカードなら効いていない可能性がある。要別途調査。テスト作成時の注意も2つ: バトルゾーンは共有ゾーンで zlist("bz", p) は相手のカードも返す（所有者で絞ること）。山札は zlist の先頭が一番上で、build の deck 指定は逆順に入る。

## 第219弾 draw_replacement_extra_card（引く時に余分に引く）

対象: rejects の単独ギャップ draw_replacement_extra_card 6件。「ターンのはじめにカードを引く時／自分のターンに1枚目のカードを引く時、もう1枚（2枚まで）余分に引く」系。

2つの形を分けて表現する:

- **ターン頭ドロー形**（dm07-s02、dm12-029、dm14-017）: ドローステップのドローそのものにだけ反応する必要がある。効果ドローと区別するため、基盤に **turn_draw フラグ**を追加した: `st_draw` が立てる `turn_draw: True` を draw イベント→レコード（置換照合用 _record_for と、誘発収集に使われる _apply_one の draw レコードの両方）に伝搬し、`when: {turn_draw: true}` で照合する（blocked/emblem 等の真偽フラグと同型。defs は bool 検証、schema.py の when プロパティにも追加。Rust も st_draw/record_for/apply_one の3箇所に同フラグを伝搬）。形は trigger {when: {event: draw, player: you, turn_draw: true}, effect: [may [draw 1]]}。
- **1枚目ドロー形**（dm16-s02、dm19-018）: 既存の合成で足りた: trigger {when: {event: draw, player: you, ord: {kind: draw, eq: 1}}, if: {is_turn: you}, effect: [may [draw 1]]}。追加ドローは ord 2 になるので再発しない。相手のターンに引いても is_turn の門で反応しない。

あわせて式 **{max_power: selector}**（対象群の最大パワー、対象が無ければ0）を追加（selectors の _EXPR_KEYS/eval、defs の expr/count_spec、schema.py）。dm12-029 の条件「自分の一番パワーの大きいクリーチャーが相手のどのクリーチャーよりも大きければ」= {cmp: [{max_power: 自分の場のクリーチャー}, ">", {max_power: 相手の場のクリーチャー}]}。

dm14-017 の「2枚まで余分に引く」は {op: choose_number, min: 0, max: 2, as: n} + {op: draw, count: {declared: n}}。ターン終わりの「自分のクリーチャーを2体タップする」は turn_end 誘発の tap select {count: 2}（候補が1体なら自動でその1体をタップする）。

proto T563（ターン頭形）/ T564（1枚目形）/ T565（条件形）/ T566（2枚まで＋ターン終わりタップ）/ T567（ドロー呪文・対照）/ T568（各プレイヤーが引く呪文・対照）。tests/test_vocab_pilot219.py 9件通過（ターン頭形の受理/拒否・効果ドローで不発・1枚目形が呪文ドローで発火/2枚目で不発・相手ターンで不発・条件形の真偽・2枚選択とタップ支払い・候補1体の縮退）。回帰: pilot212–218・engine・履歴カウンタ・誘発レコード・Rust スキーマ同期・データ監査など 110件通過。

教訓: 新しいイベントフラグは _record_for（置換照合）と _apply_one（誘発収集）の両方に伝搬しないと誘発に届かない（第213弾 no_trigger と同じ落とし穴。今回は draw レコードが _apply_one 側で組み立てられるため、最初 _record_for だけ直して不発だった）。

### ラウンド255（draw_replacement_extra_card 再変換）

reopen 6件 → **新規登録5件** + 差し戻し1件。stale クリーンアップなし。

- dm07-s02 アストラル・メデューサ（進化）: ターン頭形そのまま。
- dm12-029 ウイングアイ・モス: ターン頭形 + max_power 比較の if。
- dm14-017 アクア・オフィサー: choose_number 0〜2 + declared ドロー、ターン終わりに自軍2体タップ。
- dm16-s02 ルナ・コスモビュー: G・ゼロは free_if {any: [手札9枚以上（自分）, 手札9枚以上（相手）]}、1枚目形（ord + is_turn）。
- dm19-018 封魔バーガンティス: 1枚目形 + 「ブロックされなかった時」は attack_end レコードの blocked: false 照合（subject は相手クリーチャー、target: player）で全手札を捨てる。
- dm26rp1-034 源神のH エレクトロン → 差し戻し: 残る未対応はハイパー面の「自分がカードを引く時、かわりにカードを2枚引いてもよい」（常時置換）で、本弾の追加ドローとは別機構。既存ギャップ **draw_replacement_double** に改名して partial（攻撃時ドロー＋ハイパー静的は解決済み）を保存。

converted **9,920** / rejects **2,422**、正規 id の重なり0・漏れ0、draw_replacement_extra_card は消滅。tests/test_vocab_pilot219_cards.py 6件通過（全5枚 parse + dm07 ターン頭 + dm12 条件真偽 + dm14 の2枚選択とタップ + dm16 1枚目 + dm19 の全捨て〈割れたシールドが手札に加わった後に捨てるので、ターン3ドロー提示時点の手札は1枚〉）。

## 第220弾 hyper_subject_filter（ハイパーモード状態の主体フィルタ）

対象: rejects の単独ギャップ hyper_subject_filter 6件。アタック・チャンス自体は既存の declare イディオム（zone: hand、when {event: attack, subject: {owner: you, filter: ...}}、effect は may [play_free self]。dmr06-042 の Ωアタック・チャンスが前例）で表現でき、足りなかったのは subject を「ハイパーモード状態のクリーチャー」に絞る手段だけだった。

追加したのはフィルタキー **hyper**（真偽）1つ: 候補カードがハイパーモード状態（Card.hyper。is_hyper が Zラッシュの窓も含めて読む）かどうかで照合する。同期箇所は colorless と同型: defs の FILTER_KEYS、selectors の filter_match、Rust の filter 照合、card.schema.json 再生成。

dm24ex3-062 型（自分のハイパークリーチャーが攻撃する時、墓地から出してもよい）は trigger {zone: graveyard, when: {event: attack, subject: {owner: you, filter: {hyper: true}}}, effect: [may [play_free self]]} で同フィルタを使う。

proto T569（ハイパー化できる攻撃役）/ T570（アタック・チャンス呪文）/ T571（墓地救援獣）。tests/test_vocab_pilot220.py 6件通過（解放したターンに攻撃→宣言が提示され無料で唱えられる、解放なし→提示されない、別クリーチャーの攻撃→提示されない、相手のハイパー攻撃→提示されない、墓地救援の発火/不発）。回帰 85件通過（pilot157 のハイパー基礎、219、217、213、engine、Rust スキーマ同期、データ監査、誘発レコード）。

注意: ハイパーモードは「次の自分のターンのはじめまで」（st_start で自分のカードだけ戻る）なので、解放と攻撃は同じターンに行う。宣言の判断は yes_no ではなく declare 系の選択（declare:<id> を選ぶ）で、その後に効果内の may が yes_no で来る。

### ラウンド256（hyper_subject_filter 再変換）

reopen 6件 → **新規登録6件**（全件登録、差し戻しなし、stale クリーンアップなし）。

- アタック・チャンス呪文5枚（dm24ex3-065 超化秘伝アビスアサルト、dm24rp1-036 タノシキチシキ、dm24rp1-045 フンヌノフンカ、dm24rp1-050 モリノカナシミ、dm24rp1-057 ヨロコビノウタ）: partial の呪文本体に declare {zone: hand, when: {event: attack, subject: {owner: you, filter: {types: [creature], hyper: true}}}, effect: [may [play_free self]]} を足すだけ。
- dm24ex3-062 シザー＝ゾー: partial の CIP（相手1体に -4000）に、墓地トリガー {zone: graveyard, when: {event: attack, subject: hyper}} + may [move {ref: self} → bz] を追加。「出してもよい」のため reason は submit の lint 助言に従い **put**（当初 summon で登録し、登録後に該当行だけ put へ修正。notes も同期）。

converted **9,926** / rejects **2,416**、正規 id の重なり0・漏れ0、hyper_subject_filter は消滅。tests/test_vocab_pilot220_cards.py 4件通過（全6枚 parse + 036 のバウンス + 065 のミル＆墓地出し + 062 の墓地出し→CIP -4000 で相手を破壊）。

## 第221弾 bio_t（バイオ・T）（2026-11-18）

対象: rejects の単独ギャップ bio_t 6件（dm23-011 / 039 / 040 / 046 / 049 / 054）。

「バイオ・T―自分の<種族>が攻撃して、バトルが始まった時、このカードを自分の手札から捨ててもよい。そうした場合、（攻撃しているクリーチャーに関する効果）」は、既存語彙だけのイディオムで表せる。**新規エンジン語彙は無し**（第215弾と同型のイディオム弾）。

- 形: trigger {zone: hand, when: {event: battle_start, subject: {owner: you, filter: {races: [<種族>]}}}, effect: [may [discard self, <条項>]]}。zone_trigger_defs が手札の誘発を拾う。battle_start レコードは subject=攻撃側・opponent=防御側を持つ。may の body 先頭で {op: discard, select: {ref: self}}（discard マクロ＝墓地へ reason: discard）。
- 条項の形: 手札比例パワー＝modify {power: {amount: 1000, count: {zone: hand, owner: you}}}（count は特性計算時に評価されるため手札枚数を追う。捨てた後で数えるので自身は含まれない）、固定パワー＝modify {power: N}（duration 既定 end_of_turn）、スレイヤー付与＝modify {grant: [slayer]}、パワーアタッカー付与＝modify {power_when: {amount: 4000, when: attacking}}、両バウンス＝bounce {ref: event.subject} + bounce {ref: event.opponent}（バトルは battle_run の alive 検査で止まる）、終了時アンタップ＝choose {as: t, select: {ref: event.subject}}（ref だけの select は決定を出さない）+ delayed_trigger {when: {event: turn_end}, effect: [untap {ref: t}]}（忍者チェンジの turn_end 遅延誘発と同じ既存形）。
- 注意（仕様の罠・2件）: クリーチャーへの攻撃は 505.2 で既定ではタップ状態の相手だけが対象。試験の攻撃役にはマッハファイター相当の allow（{action: attack_creature, other: {tapped: false}}）を付けた。先攻は1ターン目に引かない（500.6）ので、手札枚数の実測は may 時で [T572]=2枚・[T572,T003,T006]=4枚。
- 注意（付与形の選択）: パワーアタッカー付与は gain で static を与える形でも battle_power でも表せない。**gain-static はエンジンが展開しない**（後述）うえ、**battle_power は _battle_bonus が自身の static しか見ない**ため modify では死ぬ。power_when は chars 集約で継続的効果からも効く。dm20-051 の modify＋battle_power 付与も同じ理由で死んでいるはず（コード上の読みで未検証。別途確認）。
- 潜在問題（本弾では未修正）: mod.gain で static 能力を与える形はエンジンが展開しない。abilities() は gain 由来の能力を kind != "static" の時だけ返し（core.py:296）、_chars_calc は集めた mod の gain を展開しない。実証: dmr12-048 猛友情 五郎丸・G の「パワーアタッカー+2000」付与は、対象（dm25sp2-017 友情地龍 ルピア・ターン）の abilities(cid, "static") に現れない。T576 の gain-static 型も同じ理由でバトルに負けることをテストで確認した。gain-static の対応は専用の弾＋全体テストで行う（第216弾の when subject: self 問題と同型の扱い）。
- Rust: battle_start の誘発・zone: hand は _simple_trigger の範囲外（_OK_EVENTS に無く、zone は bz/graveyard のみ）なので、この札を含む局は supports() が False を返し Python へフォールバックする（既存の battle_start 持ちカードと同じ扱い）。dmcore の再構築は不要。stamp は据え置き。

- proto T572（手札比例）/ T573（パワー＋終了時アンタップ）/ T574（両バウンス）/ T575（スレイヤー付与）/ T576（パワーアタッカー付与）/ T577（パワー固定）/ T578（別種族の攻撃役・マッハ付き）/ T579（テストの攻撃役・マッハ付き）。tests/test_vocab_pilot221.py 13件通過（全8枚 parse＋手札比例の 1000/枚証明＋断り・他種族・相手攻撃の不発＋終了時アンタップの履歴確認＋両バウンス＋スレイヤー道連れ＋パワーアタッカー＋固定パワー）。

- 再変換はラウンド257で実施（対象6件: 各カードの条項は上記の形でそのまま書ける）。下記参照。

### ラウンド257（bio_t 再変換）

reopen 6件 → **新規登録6件**（全件登録、差し戻しなし、stale クリーンアップなし）。

- dm23-011 アクア・スイッチ: 手札比例パワー modify {power: {amount: 1000, count: {zone: hand, owner: you}}}（T572型）。
- dm23-039 風雲闘機マスターフィンガー: パワー+1500＋終了時アンタップ（choose {as: t} + delayed_trigger turn_end。T573型）。
- dm23-040 封魔グレミー: 両バウンス bounce {ref: event.subject} + {ref: event.opponent}（T574型）。
- dm23-046 デスハンター・ドラグーン: スレイヤー付与 modify {grant: [slayer]}（T575型）。
- dm23-049 お祭番長ゴリヤンキー: パワーアタッカー+4000付与 modify {power_when: {amount: 4000, when: attacking}}（T576型。gain-static は使わない）。
- dm23-054 霊騎ゼブルス・アームズ: パワー+2000固定（T577型）。

converted **9,932** / rejects **2,410**、正規 id の重なり0・漏れ0、bio_t は消滅。tests/test_vocab_pilot221_cards.py 7件通過（全6枚 parse＋手札比例の実測＋終了時アンタップ履歴＋両バウンス＋スレイヤー道連れ＋パワーアタッカー＋固定パワー）。カードテストの注意: 攻撃役は各レースのバニラ実カード（dm01-084 アクア・ガードは cannot_attack のため不可。dm32-090 も同様）。防御側はターン2にプレイヤーへ攻撃させてタップするが、T005 は W・ブレイカーのためシールドが2枚割れて may 時の手札が+2される（dm23-011 の実測は4枚）。

## 第222弾 mana_placement_reveal（2026-11-18）

対象: rejects の単独ギャップ mana_placement_reveal 6件（dm26ex2-030 / 031 / 032 / 033 / 035 / 046）。

「このカードを自分の手札からマナゾーンに置いた時、自分の手札にある〈種族〉・カードを１枚、表向きにしてもよい。そうしたら、このカードをアンタップする。」（決闘5枚の共通条項）は、既存語彙だけのイディオムで表せる。**新規エンジン語彙は無し**（第215弾・第221弾と同型のイディオム弾）。

- 形: trigger {zone: hand, when: {event: move, from: hand, to: mana, subject: self}, effect: [may [choose {select: {zone: hand, owner: you, filter: {races: [<種族>]}}, reveal: true, as: r}, if {exists: {ref: r}} then [untap {ref: self_moved}]]]}。
- チャージはイベントになる: st_charge は ev_task {ev: move, to: mana, reason: charge} を発行し、_apply_one が lki（移動前の手札の姿）付きの move レコードを作る。_collect_triggers の lki 経路（手札等から離れたカード自身の誘発）が zone == "hand" の能力を拾う。支払い時のマナタップがイベント化されない第212弾の教訓（mana_tap_trigger）は配置には当てはまらない。移動後のゾーンが mana のため zone_trigger_defs 経路との二重発火も無い（手札の束からは既に離れている）。
- 公開: choose の reveal: true が note_public("reveal") で全員への公開を記録する。公開は情報開示のみで、ゲーム状態への副作用はアンタップだけ。
- アンタップは公開した場合だけ: choose は候補0件で空リストを返す（selectors.select の mx == 0 分岐）ため、ガード無しでは後続の untap が実行されてしまう。op: if {cond: {exists: {ref: r}}} でガードする（{exists: {ref: <変数>}} は変換済み先例あり）。may を断った場合は body 自体が実行されない。
- アンタップの対象は {ref: self_moved}: _raw_move は gen を+1する（400.5 で新しいオブジェクトになる）ため、誘発の env に残る self は移動前の世代で alive にならず、{ref: self} の untap は常時不発になる。最初の実装がまさにこの罠を踏んだ（テストで検出）。移動がちょうど1回（手札→マナ）の場合だけ今の姿を指す self_moved を使う（ラスト・バーストと同じ形。第31弾）。
- マナの既定はアンタップで置かれる（opp_mana_tapped 持ちがいる時だけタップで置かれる。_apply_one の mana 分岐）。そのため既定ではアンタップは状態変化なしの空振りだが、相手のタップ置き効果がある時にこそ意味を持つ。テストは T582（opp_mana_tapped 持ち。dmex10-008型）でタップ置きを再現してアンタップの有無を判定する。
- Rust: move イベントの誘発・zone: hand は _simple_trigger の範囲外（_OK_EVENTS に無く、zone は bz/graveyard のみ）なので、この札を含む局は supports() が False を返し Python へフォールバックする（既存の手札誘発持ちカードと同じ扱い）。dmcore の再構築は不要。stamp は据え置き（cargo 無し）。

- proto T580（テスト公開・dm26ex2-030型）/ T581（別種公開・dm26ex2-031型。種族フィルタ違い）/ T582（マナタップ置き役・dmex10-008型）。tests/test_vocab_pilot222.py 10件通過（全3枚 parse＋タップ置きでの公開→アンタップ＋既定アンタップ置きでの公開記録＋断り・種族不一致・手札空・他札チャージの不発＋唱えた時の不発（呪文本体1ドローも確認）＋2枚目の決闘の独立発火（2回公開））。

- dm26ex2-046 断罪のロスト・サインは本 family の対象外: 公式テキスト（data/cards/raw/by_product/26ex2.jsonl。alias promoy25-123 も同一文面）にはマナ配置条項が無く、rejects 行の gaps: [mana_placement_reveal] は誤タグである。本体（山札シャッフル→上4枚を見てロスト・クルセイダーをコストを支払わずに召喚、残りを山札の下へ、ブロッカー付与、次の自分のターンのはじめに手札へ戻す）のどこが阻んでいるかは未判定で、ラウンド258での再判定材料とする。rejects 行には手を付けていない。

- 再変換はラウンド258で実施（対象5件: dm26ex2-030 / 031 / 032 / 033 / 035。各カードの条項は上記の形でそのまま書ける。dm26ex2-046 は対象外）。

### ラウンド258 mana_placement_reveal 再変換（2026-11-18）

- reopen は使わず direct submit（reopen すると誤タグの dm26ex2-046 の行まで消えるため。同行は未判定のまま rejects に残置）。対象5件すべて**新規登録**、差し戻し・クリーンアップなし。
- partial には呪文本体が一切無く（マナ配置条項だけが unsupported 扱いだった）、本体は全件公式テキストから構築した: 030 = draw 2 → 手札枚数以下のコストの相手クリーチャーをすべて bounce（cost_le に count 式）。031 = 上3枚を見るイディオム（choose pile → 1枚を move で shield へ face_up: true、1枚を手札、残り1枚を as: g で墓地 → cost_of: "g" 以下を破壊）。032 = 選んだ相手を破壊 → choose（up_to）で小コストのゴッドを墓地から move-put、出さなければ（exists {ref: g} の else）may で 2 ドロー。033 = 山札上1枚を mana_put → マナからソニック・コマンドを select {total_cost_le: 8, count: 2, up_to: true} で move-put（as: put）→ modify でブロッカー付与（duration: until_next_own_turn_start）。035 = choose→discard → cost_of 以下を破壊 → タマシードとデモニオを最大1つずつ zone: [mana, graveyard] から move-put。
- 公開フィルタは races（完全一致）でなく **race_has**（部分一致）: 「ロスト・クルセイダー・カード」は種族名にそれを含む複合種族（ロスト・クルセイダー・ワード等）も指す、という DM の種族参照に合わせた（パイロットの proto は単一種族のため races で足りていた）。
- 検証: converted **9,937** / rejects **2,405**、canonical 重なり 0・漏れ 0。mana_placement_reveal の残りは dm26ex2-046（誤タグ）のみ。tests/test_vocab_pilot222_cards.py 8件通過（全5枚の登録形 parse＋各呪文本体＋030 の配置誘発で公開→アンタップ）。

## 第223弾 power_gachinko_judge（2026-11-18）

対象: rejects の単独ギャップ power_gachinko_judge 6件（dm26rp2-004 / 009 / 016 / 020 / 030 / 042）。パワー・ガチンコ・ジャッジ（自分と相手は自身の山札の上から1枚を表向きにし、それを下に置く。そのカードのパワーが相手以上なら自分の勝ち。パワーがないカードは0として扱う）は、既存 op gachinko（コスト比較、第26弾）への arg 追加2つで表せる。

- **by: "power"**: 比較軸を chars の power に切り替える。パワーがないカード（呪文・タマシード等）は chars の power が無いため `or 0` で 0 扱い（公式説明文どおり）。同点は「相手以上」で勝ち（コスト版と同じ >=）。
- **mine_as: <変数名>**: 自分の見せたカードを山札の下に置かず、その参照を変数へ残す。dm26rp2-004 の「下に置くかわりにコストを支払わずに召喚してもよい」という代替先を後続 op が決めるための保留。繰り返しの場合は最後の1枚だけが残り、前の分は通常どおり下へ置く。保留状態は task の os（gj.held）に持つため、stoppable の ask で中断・再入しても失われない。相手の見せたカードは常どおり即座に下へ置く。
- 注意: times / until_lose / stoppable のいずれも無い素の gachinko は終了しない（下に置く行為は山札を減らさないため、デッキが尽きるまで終わらない）。既存の利用箇所はすべて回数か終了条件を指定している。単発ジャッジは times: 1 と書く（本弾の proto で実際に無限ループを踏んで検出）。
- 後続処理の形: 勝敗は従来どおり {var: wins}。004 型の尾部は [if {cmp: [{var: wins}, ">=", 1]} then [may [move {ref: mine} → bz（reason: summon、as: put）]], if {not: {exists: {ref: put}}} then [if {exists: {ref: mine}} then [move {ref: mine} → deck（reason: put、**position: bottom**）]]]。move の deck 行きは position を書かないと上に戻るため、bottom を明示する。
- proto T583（基本形: CIP ジャッジ→勝てば1ドロー）/ T584（mine_as 形: 勝てば見せたカードをかわりに召喚、断るか負ければ下へ）/ T585（攻撃終了時 until_lose＋stoppable→勝った回数だけ repeat ドロー）。tests/test_vocab_pilot223.py 8件通過（全3枚 parse＋勝ち/負け＋呪文=0 の負けと 0>=0 の勝ち＋mine_as の召喚/辞退/負け＋until_lose＋stoppable の repeat）。回帰: 第26弾（コスト版）＋公開イベント系と合わせて21件通過。
- テスト上の注意: conftest の setup() で deck を指定すると**逆順に積まれる**（指定リストの最後が山札の上）。advance() が次のターンへ跨ぐと、そのターンのドローまで処理してから最初の決定を返す（相手の山札トップ検証がドローに汚染される）。
- Rust: gachinko を含むカードは単純ミラーの範囲外で Python フォールバック（コスト版の既存カードと同じ）。dmcore 再構築は不要、stamp は据え置き。
- 再変換はラウンド259で実施（対象6件すべて: 004 は mine_as 形、009 は until_lose＋stoppable＋repeat、016 は破壊時誘発＋墓地からの自己復帰、020 は add_civs 常在＋ターン開始ジャッジ、030 はターン開始ジャッジ→シールド化、042 は CIP ジャッジ＋shield_go キーワード）。

### ラウンド259 power_gachinko_judge 再変換（2026-11-18）

- reopen で6件すべて外し、**新規登録6件**（dm26rp2-004 / 009 / 016 / 020 / 030 / 042）。差し戻し・クリーンアップなし。converted **9,943** / rejects **2,399**、重なり0・漏れ0、power_gachinko_judge 単独は消滅。
- 各カードの形: 004 = ターン開始 may ジャッジ（mine_as）→ 勝てば見せたカードを reason: summon で出し、自身を bounce。009 = static battle_power +5000（バトル中）＋ attack_end で until_lose＋stoppable ジャッジ → repeat {var: wins} で相手が選んだ相手のクリーチャー/シールドを相手のマナへ。016 = CIP で相手が手札3枚を選んで捨てる＋破壊時 may ジャッジ → 勝てば {ref: self_moved} を tapped: true で自己復帰。020 = static {affects: {zone: mana, owner: you}, mod: {add_civs: 全5文明}} ＋ターン開始 may ジャッジ → 勝てば mana_put。030 = ターン開始 may ジャッジ → 勝てば山札上を move でシールド化。042 = CIP ジャッジ → 負けたら destroy self ＋ keywords [shield_go]（SG はキーワードとして実装済みだった）。
- **登録後の修正1件**: dm26rp2-009 は partial にキーワードが無く、submit でもテキスト由来のキーワードは補われなかったため、マッハファイター（CIP modify allow のイディオム、dm22rp1-071 型）と double_breaker を登録形へ追記した（converted.yaml の差分は末尾の1ハンクのみ、他カード無変更を確認）。**教訓: submit はキーワードを union しない。partial に keywords が無いカードはテキストと突き合わせて自前で補う。**
- tests/test_vocab_pilot223_cards.py 8件通過（全6枚の登録確認＋030 シールド化＋020 マナ置き＆全文明＋004 召喚＆自己バウンス＋042 の勝敗と SG＋016 の CIP 捨てと破壊時復帰）。テスト上の注意: 破壊時復帰の tapped は、復帰が相手ターンに起きると次の自ターンのアンタップで観測不能になるため、自ターンにブロッカーで破壊される形にして stop_when で復帰直後に止めた。

## 第224弾 cross_gear_effect（2026-11-18）

「これをクロスしたクリーチャー」への付与・誘発は**既存イディオムで足りる**ことを確認する回（新規語彙なし）。第22弾（クロスギア本体・affects: crossed）と第170弾（crossed 状態のフィルタ/セレクタ/式）で部品は揃っていた:

- ホストへの常在付与 = ギア側の `{kind: static, affects: crossed, mod: {...}}`（dm14-046 型。power / grant / breaks_add がそのまま使える）
- ホストの攻撃誘発 = ギア側の `{kind: trigger, when: {event: attack, subject: crossed}, effect: [...]}`（_subject_match の "crossed" パターン、303.3a。離脱後の誘発は LKI で見る）
- 「それよりパワーが小さい」 = セレクタ filter `{power_le: {sum: [{power_of: "crossed"}, -1]}}`（式の参照名 crossed は第170弾）
- 「相手のシールドを1つブレイクする」（攻撃とは別の効果ブレイク） = `{op: break, player: opp, count: 1}`
- 相手のマナを墓地に置く = move {select: {zone: mana, owner: opp, count: 2, up_to: true}, to: graveyard, reason: put}。見ないで1枚捨てさせる = discard {select: {zone: hand, owner: opp, chooser: random, count: 1}}（第185弾）

proto T586（超銀河槍型: +9000＆パワード・ブレイカー付与＋攻撃時 破壊→ブレイク）/ T587（クルト・アーム型: G・ゼロ＋ホスト+500）/ T588（バジュラズ・ソウル型: +2000＆ブレイク+1＋攻撃時 相手マナ2枚を墓地へ）/ T589（オール・イエス型: +4000＆ブロッカー付与＋攻撃時 ランダムハンデス）/ T590（メモリー・アクセラー型: 攻撃時 may ドロー）/ T591（フェアリー・アクセラー型: 攻撃時 may マナ置き）。

- **エンジン修正1件**: G・ゼロ（free_if）の無料選択肢はクリーチャー（summon）と呪文（cast）にしか出ず、クロスギアのジェネレートには出なかった（クルト・アームが無料で出せない）。turn.py `_play_options` の分岐に `(f.is_permanent() and permits(cid, "generate"))` を追加。play_task の free 経路は汎用なので支払いスキップはそのまま効く。zone_graph の free バンドルはクリーチャー専用のまま（探索ツール側の話として残す）。
- テスト: tests/test_vocab_pilot224.py 8件（parse、T586 ホスト+9000＆パワード・ブレイカー、攻撃誘発の破壊＋効果ブレイク1＋攻撃ブレイク2でシールド5→2、T588 ブレイク数2＆マナ2枚墓地、T589 ブロッカー付与＆ランダムハンデス、T590/T591 の may、T587 の G・ゼロ無料ジェネレート）＋回帰（第170/195/167弾）45件通過。

### ラウンド260 cross_gear_effect 再変換（2026-11-18）

- reopen で6件すべて外し、**新規登録6件**（dmex16-041 / dmex17-107 / dmex17-cho07 / dmex17-w15 / dmpcd02-a11 / dmpcd02-a13）。差し戻し・クリーンアップなし。converted **9,949** / rejects **2,393**、重なり0・漏れ0、cross_gear_effect 単独は消滅。
- 形は第224弾の proto と同一（affects: crossed の常在付与＋ subject: crossed の攻撃誘発）。dmex17-107 は free_if 付きで、第224弾のエンジン修正（ジェネレートの G・ゼロ）により実際に無料で出せることを登録形テストで確認した（play キーが :free）。
- tests/test_vocab_pilot224_cards.py 6件通過（全6枚の登録確認＋041 の破壊＆ブレイク＋cho07 のブレイク数とマナ焼き＋w15 のブロッカー付与とハンデス＋a11/a13 の may＋107 の G・ゼロ）。

## 第225弾 cross_gear_mechanic 切り分け（2026-11-18）

cross_gear_mechanic の単独6件は単一機構ではなく混在だったため、条項ごとに切り分けた。4件は既存語彙で足りる（本弾でイディオムを実証）:

- **クロスされていない時の軽減**（センゴク・トッパアーマー型）: ギア側の常在 `{affects: {zone: hand, owner: you, filter: {races: [ドラゴン]}}, mod: {cost_may: {amount: 1, min: 1}}, if: {not: {exists: {ref: self, filter: {crossed: true}}}}}`。ギア自身の crossed 状態は第170弾のフィルタで読める。
- **名前制限付きフリー・クロス**: `{affects: self, mod: {allow: [{action: cross_free, other: {any_of: [{name_has: 武者}, {name_has: 大和}, {name_has: 紫電}]}}]}}`。permits は allow の other フィルタを宿主候補に当てる（第195弾の仕組みのまま）。
- **ホストのブレイク誘発**（オンセン・サバキ型）: `{when: {event: break, subject: crossed}}`。break レコードは t["breaker"] があれば subject を載せる（events.py の break タスク適用）ので、宿主の攻撃ブレイクに一致する。CIP のギア破壊は通常の destroy。
- **マナから出す**（偉大なる大地型・呪文）: may で自分のクリーチャーをマナへ → `{op: if, cond: {exists: {ref: put}}}` で名前に《ボルベルグ》を含むクリーチャーと進化ではないクロスギアを move（reason: put）でマナから出す。
- ビクトリーソウル型（ホスト+3000＋攻撃時にマナ置き2→マナから1枚手札へ）も第224弾イディオムの組み合わせで足りる。

残る2件は新しい詰まりとして切り離す: dmx21-045 → **strigger_x**（S・トリガーX: シールドから手札に加わる時に即ジェネレート＋クロス）、promoy4-002 → **cross_cost_reduction**（宿主側の常在がクロスコストを軽減する形は未実装。現行の軽減はギア側許可 cross_free と支払いのみ）。

proto T592（センゴク型）/ T593（オンセン型）/ T594（大地型呪文）/ T595（ビクトリー型）/ T596（武者クリーチャー）/ T597（ボルベルグ名クリーチャー）/ T598（高コストドラゴン）。

### ラウンド261 cross_gear_mechanic 再変換（2026-11-18）

- reopen で6件すべて外し、**新規登録4件＋差し戻し2件**。converted **9,953** / rejects **2,389**、重なり0・漏れ0、cross_gear_mechanic 単独は消滅。
- 新規: dmx21-047（ホスト+3000＋攻撃時マナ循環）、dmx21-046（マナから出す呪文）、dmx21-013（未クロス軽減＋名前制限フリー・クロス）、dmx12b-025（フリー・クロス＋CIP ギア破壊＋ブレイク誘発）。いずれも第225弾の proto と同形。
- 差し戻し: dmx21-045 → **strigger_x**（ホスト付与のパワーアタッカー+9000＆T・ブレイカーは partial に保存）、promoy4-002 → **cross_cost_reduction**（W・ブレイカーは partial に保存）。
- tests/test_vocab_pilot225_cards.py 5件通過（登録確認＋差し戻しのギャップ名確認＋4枚の挙動）。テスト上の注意: パイロット（proto）テストと登録形テストを同一 pytest 実行に混ぜると conftest の DMSIM_SKIP_CONVERTED 捕捉で converted が読めなくなるため、別々に実行する。

## 第226弾 cast_from_graveyard（2026-11-18）

墓地から呪文を通常コストで唱える形を、第172弾リサイクル（代替コスト＋解決後は山札の下）の姉妹として実装した:

- 面の項目 **grave_cast: true**（その呪文自身が墓地から唱えられる。回数制限なし）
- 許可型は常在 `{affects: {zone: graveyard, owner: you, filter: {types: [spell]}}, mod: {allow: [{action: cast_from_graveyard, once: true}]}}`（permissions.yaml に action を追加。回数制限は第37弾 summon_from_graveyard と同じ方式で、chars の allow を読み cast_once:<src> カウンタで管理。src 省略時は None キー＝ターン1回）
- _play_options の墓地スキャンに :grave 選択肢を追加（通常コストの _mana_choices で判定、コスト上書きなし）。解決後はリサイクルと同じく山札の一番下（resolve_to: deck / resolve_position: bottom）
- Rust: リサイクル同様、墓地スキャンは Python 側のみ（対象カードはフォールバック）

proto T599（自己 grave_cast 呪文）/ T600（許可型クリーチャー＋唱えた時ドロー）/ T601（手札から唱えた呪文を墓地から無料で唱え直す再演型・dmex18-s06 型）。
- ついでに cast レコードへ **from**（唱えた元のゾーン）を追加（h_play の cev と play_self の両方）。「手札から唱えた時」の照合が可能になり、dmex18-s06 型の再演（手札から唱えた呪文を墓地から無料で唱え直す）は `{when: {event: cast, from: hand, subject: {owner: you, filter: {types: [spell]}}}, effect: [may [play_free {select: {ref: subject}}]]}` のイディオムで足りる。再演自体は墓地から唱えるので from: hand に一致せずループしない。
- テスト: tests/test_vocab_pilot226.py 5件（parse、自己 grave_cast の支払いと山札下、許可型のターン1回と次ターン回復＋唱えた時ドロー、再演で2回解決、墓地から唱えた場合は再演しない）＋回帰（第172/50/51弾）21件通過。

### ラウンド262 cast_from_graveyard 再変換（2026-11-18）

- reopen で5件すべて外し、**新規登録4件**（dm26ex2-mc004 / dmex18-s06 / dmrp03-004 / dm26ex4-011）。converted **9,957** / rejects **2,384**、重なり0・漏れ0、cast_from_graveyard 単独は消滅。
- dm26ex4-sec022 は dm26ex4-011 の別刷りで、submit が自動で 011 の aliases に折り畳み、reject 行も除去した（原文コーパスに無い ID のため単独 submit は不可。自分の手作業での alias 追加は不要だった）。
- dm26ex2-mc004: grave_cast＋modal 2回選択。オーラはこのデータではクリーチャー型なのでモード2は闇クリーチャーで兼ねる。dmex18-s06: 再演イディオム＋ deny be_chosen {other: {types: [spell]}}（owner キーは other フィルタに無い。第164弾型どおり相手性は評価側で担保され、登録形テストで相手呪文から選べないことを確認）。dm26ex4-011: partial の墓地コスト軽減に cost_min: 1 を補った。
- tests/test_vocab_pilot226_cards.py 6件通過。

## 第227弾 untap_limit（アンタップ制限）

相手のターン開始時にアンタップできる枚数を制限する家族（単独5件）。「アンタップ」は通常すべて同時に行われるため、上限が候補数より小さい時だけ「どれをアンタップするか」の選択が発生する。

- 常在型は static の専用キー `untap_limit: {zone: bz | mana, count: N}`（第213弾 suppress_triggers と同じく chars を経由しない直接読み）。能力の `if` は発生源のコントローラ側で評価する（革命2＝自分のシールド2つ以下、など）。st_start が相手の bz トップから集め、ゾーンごとに最小値を取る。
- 呪文などの一回性は新 op `untap_limit {player, zone, count}` → `s.untap_caps` に保留し、対象の次の st_start で消費する（常在分と最小値を取る）。
- st_start の統合: サイレントスキルの諮問を過ぎてから上限を確定し（諮問の再入で保留を二重消費しない）、上限が効く場合はアンタップのイベント束の代わりに専用タスク `untap_limit` を積む。タスクはゾーンごとに1回ずつ選択を諮問し（os で段階管理）、選ばれたカードだけのアンタップ束を積む。上限が効かない場合は従来どおり。
- プロト T602–T606、tests/test_vocab_pilot227.py。

### ラウンド263 untap_limit 再変換（2026-11-18）

- reopen 5件 → **新規登録5件**（dm24ex4-053 / dmex19-m32 / dmr12-007 / dmrp16-s08 / dmx20-001）、差し戻しなし。converted **9,962** / rejects **2,379**、重なり0・漏れ0、untap_limit 単独は消滅。
- dmex19-m32 はツインパクトで、無月の門・絶と呪文面は partial に既存表現があり、クリーチャー面への static 追加だけで完結した。dmrp16-s08 は partial の重複スレイヤー付与を1つに統合。dm24ex4-053 の「見ないで選び」は chooser: random。
- **教訓**: 新規タスクハンドラは終了時に `eng._pop(t)` が必須（無いとハンドラが再実行され続け step_limit になる）。パイロットテストは偶然通ってしまった（最初のアンタップ束が処理された後の状態だけを見ていた）が、登録形テストの「ゲームが終わらない」検証で検出できた。
- tests/test_vocab_pilot227_cards.py 5件通過。

## 第228弾 crystal_charger（水晶チャージャー）

通常チャージャーは既存（キーワード `charger` → card props {resolve_to: mana} で表向きにマナへ）。水晶チャージャーは裏向きで置く点だけが違う。

- キーワード `crystal_charger` を keywords.yaml に追加（card props {resolve_to: mana, resolve_face_down: true}）。
- 面項目 `resolve_face_down`（bool）を新設: defs の Face/CardDef＋props 伝播、schema.py、dataaudit の BASIC_FIELDS に同期。
- h_play の呪文解決移動に、面が resolve_face_down の時だけ `face_down: true` を載せる（events 側は第128弾の「裏向きのままマナゾーンに置く」処理が既にある）。無料で唱えた場合も play タスク経由で同じ解決経路を通る。
- プロト T607–T608、tests/test_vocab_pilot228.py。

### ラウンド264 crystal_charger 再変換（2026-11-18）

- reopen 4件＋ direct submit 1件（dm26rp2-t001 は partial も reason も無い行で reopen が外さないため）→ **新規登録5件**、差し戻しなし。converted **9,967** / rejects **2,374**、重なり0・漏れ0、crystal_charger 単独は消滅。
- 4件はツインパクトの partial に呪文面キーワード crystal_charger を足すだけ。dm26rp2-t001 は partial が無く、by_product の公式 faces から構築（クリーチャー面＝出たターン攻撃不可の deny 付与、呪文面＝相手のマナ枚数より大きいコストの相手エレメントを山札の下へ）。
- 副次修正: 第226弾で dataaudit の _STRUCT_FIELDS に grave_cast を足し忘れていた同期漏れを検出・修正（test_data_audit が落ちていた）。
- tests/test_vocab_pilot228_cards.py 4件通過。

## 第229弾 bio_k（バイオ・K）

バイオ・K は第221弾 bio_t の攻撃終了版: 自分の指定種族がプレイヤーを攻撃してブロックされなかった時、手札からこのカードを捨てて効果を使う。

- 誘発点は新規イベント **attack_unblocked**: 「ブロックされなかった時」はブレイクの前に解決するのが公式の順序で、W・ブレイカーの付与（dm23-028）がその攻撃のブレイクに間に合う必要がある。attack_end（第219弾）はブレイク後なので使えない。combat の攻撃タスク phase 4（ブロック不成立・プレイヤー対象の時だけ、ブレイク数選択の前）に1回だけ発火させる。イディオムは trigger {zone: hand, when: {event: attack_unblocked, subject: {owner: you, filter: {races: [X]}}, target: player}, effect: [may [discard self, 条項]]}。
- 条項の部品: 攻撃クリーチャーへの付与 = modify {select: {ref: event.subject}, mod: {grant: [...]}, duration: end_of_turn}。同名サーチ = 山札を全部見る（choose look count: all → pile）→ filter {name: {name_of: event.subject}} で選ぶ → 残りを戻して shuffle {player: you}。パワー合計制限の破壊 = select の total_power_le（既存）。「N枚まで引く」= choose_number + draw {declared: n}（第219弾）。
- エンジン修正2件: (1) 新イベント attack_unblocked の同期（defs EVENTS、events のレコード素通しリスト、AttackTask に through_fired）。(2) selectors.candidates の ref 分岐だけフィルタ式の事前評価が無く、{name: {name_of: ...}} のような式フィルタが素通りで不一致になっていた（under_of / bundle_of 分岐にはあった）。同名サーチが動かなかった原因で、近傍分岐と同じ事前評価を追加。
- プロト T610–T615、tests/test_vocab_pilot229.py 4件。

### ラウンド265 bio_k 再変換（2026-11-18）

- reopen 5件 → **新規登録5件**（dm23-005 / 028 / 037 / dm23-s01 / dmx11-076）、差し戻しなし。converted **9,972** / rejects **2,369**、重なり0・漏れ0、bio_k 単独は消滅。
- partial は基礎欄のみで、条項は第229弾イディオムで構築（同名サーチ／W・ブレイカー付与／光の呪文2枚回収／パワー合計3000以下の破壊／2枚まで引く）。
- tests/test_vocab_pilot229_cards.py 3件通過（028 の付与→2枚ブレイク、005 の同名サーチを実カードで検証）。

## 第230弾 leave_protection_vs_opponent_spells（相手の呪文では離れない）

「相手の呪文の効果でバトルゾーンを離れる時、かわりにとどまる」は mod `no_leave` の適用範囲の問題。移動イベントには効果帰属（発生源の解決者 `by` と種別 `cause_kind`: spell/ability）が既に記録されている（基盤B1）。

- no_leave の辞書に新キー **by_opp_spell** を追加: _apply_one の判定で「by が相手プレイヤー、かつ cause_kind が spell」の移動だけを止める。自分の呪文・相手の能力・バトルや状況起因（帰属なし）は通す。defs の検証キーにも追加。
- 形: 自分だけ = static {affects: self, mod: {no_leave: {by_opp_spell: true}}}。味方全体・他だけ = affects {zone: bz, owner: you, filter / other: true} の通常形。
- プロト T617–T619、tests/test_vocab_pilot230.py。

### ラウンド266 leave_protection_vs_opponent_spells 再変換（2026-11-18）

- reopen 5件 → **新規登録5件**（promoy6-003 / dm22rp1-004 / dmr03-010 / dmx22a-029 / dm33-012）、差し戻しなし。converted **9,977** / rejects **2,364**、重なり0・漏れ0、同単独は消滅。
- 形は4通り: 自分だけ（dmx22a-029）、他の闇（promoy6-003、ブロッカー付与は partial 既存）、他のクリーチャー全般（dmr03-010）、アビス全般（dm22rp1-004、攻撃時ランダム3枚捨ては partial 既存）、名前に《死神》（dm33-012）。
- tests/test_vocab_pilot230_cards.py 3件通過。

## 第231弾 evolution_v_two_bases（進化V: 進化元2体）

進化V 自体は既存（evolve_from をリストで書くとフィルタごとに1体ずつ選ぶ。選択済みの進化元は候補から外れる）。残っていたのは2点。

- 同一プールから2体（「いずれか2体」）: 同じフィルタを2回書く形で表現できることをプロトで検証した（新規語彙なし）。
- 太陽王ソウル・フェニックス型の離脱ルール（「一番上のカードだけが離れ、下の2枚は別々のクリーチャーとなる」）: star: true の再構築は従来、下のカードを1体のクリーチャーに連結していた。直接の進化元を Card.stack_bases に記録し（_stack で追加、ゾーン移動で消去）、再構築時に進化元が2つ以上あればセグメントごとに独立したクリーチャーとして残すよう _rebuild を拡張した。
- プロト T622–T625、tests/test_vocab_pilot231.py。

### ラウンド267 evolution_v_two_bases 再変換（2026-11-18）

- reopen 4件 → **新規登録4件**（dm22-024 / dm22-027 / dm12-005 / dm12-s03）、差し戻しなし。converted **9,981** / rejects **2,360**、重なり0・漏れ0、同単独は消滅。
- dm22-024 / 027 は同一プールフィルタ×2（024 の破壊→手札置換、027 の出た時破壊は partial 既存）。dm12-005 は異種フィルタ×2＋star: true。dm12-s03 は異種フィルタ×2＋離脱時に全クリーチャー破壊のトリガー。
- tests/test_vocab_pilot231_cards.py 2件通過（フェニックスの2進化元での進化を実カードで検証。分離再構築の挙動は第231弾プロトで検証済み）。

## 第232弾 evolution_base_any_race（どんな種族の進化も置ける進化元）

「どんな種族の進化クリーチャーを、このクリーチャーの上に置いてもよい」は進化元側の許可。新アクション **evolve_base_any**（permissions.yaml、default: false）を追加し、進化元候補の照合を集約した `_evo_match` で「フィルタに種族指定があり、進化元がこの許可を持つ」場合も一致とする。文明など種族以外の指定は許可で肩代わりしない。

- 照合の差し替え箇所: _evo_sources（単独・リスト両形）、_evo_v_ready、h_play の進化V選択。NEO・墓地進化・超無限の候補も _evo_sources 経由で効く。山札進化（めくったカードが進化元）には場の常在型は及ばないので対象外。
- 形: 本人 = static {affects: self, mod: {allow: [evolve_base_any]}}。クロスギア形 = {affects: crossed, mod: {allow: [evolve_base_any]}}。メタモーフ形 = 同じ static に if（マナ枚数）を付ける。
- プロト T626–T629、tests/test_vocab_pilot232.py。

### ラウンド268 evolution_base_any_race 再変換（2026-11-18）

- reopen 4件 → **新規登録4件**（dm22-019 / dm23-034 / dm14-037 / dm32-110）、差し戻しなし。converted **9,985** / rejects **2,356**、重なり0・漏れ0、同単独は消滅。
- 形は3通り: 自己許可（イノス/ビャッコ）、メタモーフ＝マナ7枚以上の if つき自己許可（式神イノセント）、クロス先への許可（メガ・イノセントソード。パワー+3000 は partial 既存）。
- tests/test_vocab_pilot232_cards.py 3件通過。

## 第233弾 launcher_e（ランチャーE）

「この呪文を唱える時、自分の（種族）のタップされていないクリーチャーを好きな数タップする。その数／合計パワーで効果が変わる」を面項目で表す。

- 面項目 **launcher: {filter}**（defs Face/CardDef＋検証＋schema）。h_play にムゲンクライムと同じ段階ステップを追加: 支払いの前に候補（自分のタップされていない場のトップで filter 一致）を提示し、選んだ数をタップして参照リストを PlayTask.launcher に記録。コスト軽減ではないので無料詠唱（S・トリガー）でも使える。
- 呪文の効果 env の vars に **launcher** として渡す。条項の形: 枚数 = repeat {times: {var: launcher}} や choose の count: {var: launcher}。合計パワー = {total_power: {ref: launcher}}。
- プロト T630–T632、tests/test_vocab_pilot233.py 4件。
- 追加の小拡張: op **repeat** に `over: <変数名>, as: <名前>` を追加（変数のカード1枚ずつに body を適用し、要素を as の変数へ束ねる）。ドラグハリケーン・エナジーの「タップしたドラゴン1体につき、それと同じ名前のクリーチャーを出す」に必要。opvocab と @op の同期＋スキーマ再生成。

### ラウンド269 launcher_e 再変換（2026-11-18）

- reopen 5件 → **新規登録5件**（dm20-014 / 023 / 032 / 055、dm24ex3-rp2tr07）、差し戻しなし。converted **9,990** / rejects **2,351**、重なり0・漏れ0、同単独は消滅。
- 条項の形: タップ数×ブレイク（repeat times）、タップ数までの呪文サーチ、合計パワー以下の破壊、タップ数×マナ加速（mana_put の repeat）、タップしたドラゴンと同名を出す（repeat over/as）。
- tests/test_vocab_pilot233_cards.py 3件通過。

## 第234弾 tamaseed_evolution_cost_reduction（進化元で変わる召喚コスト）

「タマシードから進化するならコストを2少なくする」は、支払い額が選んだ進化元に依存する形。2つの置き場所で表す。

- 出す側の宣言 = 面項目 **evo_base_reduce: {filter, amount, min?}**。進化元が filter に合えば軽減。
- 進化元側の付与 = mod **evo_reduce: {amount, min}**（chars に evo_reduce / evo_reduce_min として集約）。「このタマシードから進化するクリーチャーのコストを少なくする」。
- 適用は turn.py の `_evo_base_reduced` に集約: _can_play_face の進化分岐（見積り: 候補全体から必要数ぶん）と h_play の支払い段階（実際に選んだ進化元で確定）の両方から使う。
- プロト T633–T636、tests/test_vocab_pilot234.py。

### ラウンド270 tamaseed_evolution_cost_reduction 再変換（2026-11-18）

- reopen 5件 → **新規登録4件＋別刷り畳み込み1件**（dmrp21-10b / dmrp22-001 / dmsd20-006 / dmrp22-069、promoy21-005 は原文コーパスに無いIDで dmsd20-006 の aliases へ自動で畳まれた）。converted **9,994** / rejects **2,346**、重なり0・漏れ0（aliases 込みで確認）、同単独は消滅。
- dmsd20-006 の攻撃モーダルは partial に無く原文から構築（相手のコスト4以下のクリーチャー/タマシードをシールド化／自分の山札上1枚をシールド化してもよい）。dmrp22-069 は付与形（mod evo_reduce）。
- 監査の教訓: dataaudit は converted に現れたフィールドしか検出しない。第233弾 launcher の同期漏れはラウンド269 の登録で初めて表面化した（あわせて修正済み）。
- tests/test_vocab_pilot234_cards.py 3件通過（付与の chars 値、モーダルのシールド化を含む）。

## 第235弾 kizuna_comp（キズナコンプ）

「このクリーチャーが攻撃する時、好きな数の自分のクリーチャーの[P]能力を使う」を、攻撃トリガー＋専用 op で表す。

- [P]能力は既存の能力種 **partner**（{kind: partner, effect: [...]}）に置く。単独では解決しない。
- 既存 op **use_partner**（第153弾キズナ用、1件だけ使う形）に引数 **any_number: true** を追加: 1件使うたびに次を聞き（0件で終えてよい）、使った能力（cid, gen, 能力index）はこの解決中は候補から外れる。効果は「そのクリーチャー自身の効果」として子で解決される。
- キズナコンプ自体は攻撃トリガー {when: {event: attack, subject: self}, effect: [{op: use_partner, any_number: true}]} と書く。
- プロト T637–T638、tests/test_vocab_pilot235.py。

### ラウンド271 kizuna_comp 再変換（2026-11-18）

- reopen 5件 → **新規登録5件**（dmrp04s-s05 / 007 / 001 / s03 / s09）、差し戻しなし。converted **9,999** / rejects **2,341**、重なり0・漏れ0、同単独は消滅。
- [P] の形: 自分自身の破壊、味方1体への「最初の攻撃の終わりにアンタップ」（delayed_trigger の subject: {ref}＋turn_count attack_by）、次の自分のターン開始まで破壊されない（modify indestructible）、いずれかの墓地からコスト7以下の呪文を無料で（解決後は持ち主の山札の下）、山札上2枚から自然のパワー12000以上の非進化を出す（残りは手札）。
- dmrp04s-s05 の W・ブレイカーは partial の keywords に無く、原文から補った。
- tests/test_vocab_pilot235_cards.py 2件通過（自分の[P]と味方の[P]を続けて使う確認を含む）。

## 第236弾 infinite_evolution / super_infinite_evolution（超無限進化）

「1体以上の上に置く」は既存の evolve_any（通常進化の分岐で1〜全数を一度に選ぶ）で足りていた。残りは dm26ex4 系の「コストの合計が20以上になるように」だけ。

- 面項目 **evolve_total_cost_ge: N**。h_play に文明条件（第218弾）と同型の段階分岐を追加: 合計が届くまで1体ずつ必須で選び、届いた後は追加も可（0件で確定）。_can_play_face は候補全体の合計コストで可否を判定。
- 出た時の「◯枚以上のカードの上に進化していれば」は {count: {under_of: self}} で数える。
- あわせて前提修正: mod **mana_number は 0 への置換**も表せるようにした（ワルドバロムの「マナの数字を0にする」）。未設定の番兵を 0 から None に変更（core の chars 既定値と集約、turn の values_of、defs の検証は >= 0 に緩和）。Rust 側は mana_number の集約自体を持たないため対象外（該当する試合は従来どおり Python に落ちる）。
- プロト T640–T642、tests/test_vocab_pilot236.py 4件。

### ラウンド272 超無限進化 再変換（2026-11-18）

- 直接 submit（reopen せず、空テキストの dm26ex1-011 を残す）→ **新規登録4件**（dm24ex3-or5 ワルドバロム、dm34-001、dm34-006、dm34-030）＋**差し戻し3件**（dm25ex2-030 → dragheart へ再分類、dm26ex4-012 → extra_ex_life、dmc58-004 → g_link_positional。解決済みの節は partial に保存）。converted **10,003** / rejects **2,337**、重なり0・漏れ0。
- dmartkiwami01-002 は dm24ex3-or5 の aliases に畳み込み（rejects 行は別刷り stale として残存。既存7件と同種）。dm26ex4-sec009 は原文コーパス外IDのため単独処理できず、旧ラベルのまま残存（012 が将来登録される時に畳まれる）。
- ワルドバロムの出た時: 下の枚数条件（under_of の count）で全捨て／相手マナ数字0（第236弾の mana_number 0 置換）。攻撃時は choose_civ → その文明の相手エレメント全破壊。
- dm34 系のメテオバーンは「下を1枚墓地へ置く→そうした場合」の may＋exists 形。006 は shield_plus の repeat（コスト回数）、030 は3モード（相手が自分のマナから選んで墓地／クロスギア／要塞化の城）。
- tests/test_vocab_pilot236_cards.py 2件通過（3体重ね→全捨てを含む）。

## 第237弾 extra_ex_life（エクストラEXライフ）

EXライフとの差は「紐付けるシールドが2枚」だけ。置換能力の形（紐付いたシールドの中から1枚を墓地に置く）はそのまま使える。

- キーワード **extra_ex_life** を keywords.yaml に追加（置換能力は ex_life と同一）。
- events の入場フック: extra_ex_life を持つクリーチャーが出たら _exlife_shield を2回行う（山札が尽きたら尽きた分だけ）。
- あわせて新フィルタ **exlife**（EXライフで紐付いたシールドか）を追加（defs FILTER_KEYS＋selectors＋Rust＋スキーマ再生成）。「自分のEXライフシールドすべてにS・トリガーを与える」= static {affects: {zone: shield, owner: you, filter: {exlife: true}}, mod: {grant: [s_trigger]}}。
- プロト T643–T644、tests/test_vocab_pilot237.py 2件。

### ラウンド273 エクストラEXライフ再変換（2026-11-18）

- reopen 5件 → **新規登録3件**（dm26ex4-012、dm26ex4-019、dm26rp3-s007）。別刷り3件（dm26ex4-sec009／sec020、dm26rp3-sec008）は原文コーパス外IDのため、正規カードの aliases に畳み込み（sec020/sec008 は登録後に converted.yaml へ直接追記）。converted **10,006** / rejects **2,332**、重なり0・漏れ0、extra_ex_life 解消。
- dm26ex4-012 は第272で保存した節（手札誘発・合計20の超無限進化・呪文禁止・破壊誘発）にキーワードを足すだけ。dm26rp3-s007 は節を新規構築: EXライフシールドへの S・トリガー付与（フィルタ exlife）、タップ誘発でブレイク、ターン終了時にアンタップ＋任意ドロー。
- tests/test_vocab_pilot237_cards.py 2件通過（s007 の2枚紐付け＋S・トリガー付与を含む）。
- 注意: reopen 済みの rejects は第237弾のコミットに混入して確定済み（行データは e19d4ac 時点の rejects から復元して構築）。

## 第238弾 static no_lose（常在型の敗北防止イディオム）

第188弾で入った常在型 no_lose（{kind: static, no_lose: true | {deck_out_only: true}, if: 条件}）の適用範囲を確認するイディオムパイロット。エンジン変更なし。

- 「相手のターン中、自分は負けない」= {kind: static, if: {is_turn: opp}, no_lose: true}（既存の dmex08-256 は is_turn: you 形）。
- 「タップしていれば負けない」= if に {exists: {ref: self, filter: {tapped: true}}}（ref セレクタは filter を適用する）。
- 「山札切れで負けない（残りのゲーム中）」の呪文形は op no_lose {deck_out_only: true, duration: permanent}。
- プロト T645–T647、tests/test_vocab_pilot238.py。

### ラウンド274 lose_protection 再変換（2026-11-18）

- reopen 5件 → **新規登録3件**（dm25bd1-001、dm25bd2-003、dm24ex3-rp3tr1）＋**差し戻し2件**（dm24ex3-tf01 勝敗の無効化、dm25-003 勝利の置換 — 静的形の対象外として lose_protection のまま残す）。converted **10,009** / rejects **2,329**、重なり0・漏れ0。
- dm25bd1-001: 墓地の火カード数でパワー+3000、全捨て→3ドロー＋捨てたボルシャック1枚ごとの任意破壊（repeat over/as）、相手ターン中 no_lose、破壊置換は optional replace（マナのボルシャック3枚を墓地へ）。
- dm24ex3-rp3tr1 はツインパクト: 呪文面 = op no_lose {deck_out_only, duration: permanent}＋5ドロー＋山札が空なら追加ターン。行の text がクリーチャー面だけだったため by_product の faces から構築。
- tests/test_vocab_pilot238_cards.py 3件通過。

## 第239弾 break_before（各ブレイクの前に）

新イベント **break_before**: ブレイクタスクが選ばれたシールドを割る直前に、シールド1枚につき1回、subject = ブレイクするクリーチャーで発火する（defs EVENTS、events のレコード通過リスト、combat のブレイクタスク末尾で移動より前に積む。置換でブレイクが無くなった場合は発火しない）。

- 形は trigger {when: {event: break_before, subject: self}, effect: [...]}。複数ブレイクでは枚数分だけ誘発する。
- 進化時の付与（シンカパワー）は delayed_trigger {when: {event: break_before, subject: {ref: self}}, duration: end_of_turn} の形を取る。
- プロト T648–T649、tests/test_vocab_pilot239.py。

## 第240弾 static_gain（常在型 mod gain の展開）

潜在バグの修正: mod **gain** は継続的効果（modify op 由来の s.continuous）からしか展開されず、**常在型能力の mod.gain は丸ごと無効**だった（converted 37枚が使用。誘発・置換の付与が死んでいた。ラウンド275の登録形テストでセイバーが発火しないことから発見）。

- core.abilities(): バトルゾーン／シールドの発生源の常在型で、このカードに適用される（chars 計算と同じ _subject_match＋if 判定）ものの mod.gain を、負の添字で能力列に加える。自分自身への affects: self 付与も対象。
- events の誘発収集の省略判定（gainable）にも常在型 gain の存在を含めた。
- 得た常在型能力（gain の中身が static のもの）自体の mod 適用は chars 計算側の別課題として残す。
- プロト T650–T651、tests/test_vocab_pilot240.py。

### ラウンド275 break_pre_trigger 再変換（2026-11-18）

- reopen 5件 → **新規登録5件**、差し戻し0件。converted **10,014** / rejects **2,324**、重なり0・漏れ0、break_pre_trigger 解消。
- dm26sd1-o003 は常在型に affects: self が欠けていた partial を直して再提出。dmrp22-019 のシンカパワーは delayed_trigger {when: break_before, subject: {ref: self}, once: false, duration: end_of_turn} で実装（重複した変換由来スタティックは除去）。
- 第240弾の検証で dm23rp1-1b のセイバー付与（静的 gain）が実際に働くことを登録形で確認（テストにはセイバーの持ち主としてファイアー・バード T624 が必要）。
- tests/test_vocab_pilot239_cards.py 3件通過。第240弾の全体テストで test_rust_schema_sync の同期漏れ2件（stack_bases／untap_caps の Rust 側欠落、第227・231弾由来）を発見し state.rs に追加して解消。全チャンク通過（失敗はその2件のみで修正済み）。

## 第241弾 cross_reduce（クロスのコスト軽減）

新 mod **cross_reduce** {amount, min?, host?: filter, gear?: filter, may?: bool}。chars にリストで集約し、クロスの支払い時に turn の _cross_costs が「ギア側の項目（host で対象を判定）＋ホスト側の項目（gear でギアを判定）」を集める。may の項目は「最大N少なくしてもよい」= 0..amount の任意軽減として、達成可能な実コストの候補すべてを _mana_choices に渡して組を統合する。下限は min の最大値。

- ギア側の自己軽減（「このカードをサムライにクロスする時、最大2少なく」）= ギア自身の static {affects: self, mod: {cross_reduce: {amount: 2, min: 1, host: {races: [サムライ]}}}}。
- ホスト側（「このクリーチャーにクロスする時1少なく」）= ホストの static {affects: self, mod: {cross_reduce: {amount: 1, min: 1}}}。
- 全体（「自分のクロスギアをクロスする時1少なく」）= {affects: {zone: bz, owner: you, filter: {types: [cross_gear]}}, mod: {cross_reduce: ...}}。ジェネレート（手札から出す）側の軽減は既存の mod cost（hand ゾーンへの affects）で表す。
- プロト T652–T656、tests/test_vocab_pilot241.py。

### ラウンド276 cross_cost_reduction 再変換（2026-11-18）

- reopen 3件＋直接提出2件 → **新規登録4件**（dm15-016、dm17-021、promoy4-002、dmc45-009）＋**差し戻し1件**（dmc45-008: クロス軽減は partial に残し、残ギャップは trigger_when_destroyed_by_named_card_effect のみ）。converted **10,018** / rejects **2,320**、重なり0・漏れ0。
- dm15-016 は2面で表現: ジェネレート側 = {affects: {zone: hand, filter: {types: [cross_gear]}}, mod: {cost: -1, cost_min: 1}}、クロス側 = {affects: {zone: bz, filter: {types: [cross_gear]}}, mod: {cross_reduce}}。
- dmc45-009 の「そのクリーチャーよりパワーが小さい」は power_le {sum: [{power_of: crossed}, -1]} で表現でき、dynamic_power_comparison_filter も同時に解消。ホスト破壊の対象は crossed_to（ギア側）ではなく **host_of: self**（第170弾の selector は crossed_to = そのクリーチャーにクロスされているギア、host_of = そのギアのホスト）。
- tests/test_vocab_pilot241_cards.py 3件＋データ監査通過。

## 第242弾 draw_replacement_double（ドロー置換の倍化）

イディオム: ドロー置換は既存の {kind: replace, optional: true, when: {event: draw, player: you}, instead: [...]} で表せる（コーパスに7件、うち draw 2 形は dmx17-013 等）。ドローは1枚ごとのイベントなので、「その2倍引く」は各イベントの instead で draw 2 にすれば多枚ドローでも自然に倍化する。

- 単純形: instead: [{op: draw, count: 2}]。
- シールド・フォース形（dm28-049）: replace に sforce: true を付け、instead: [draw 2, 手札1枚を山札の一番下へ]（引いた2枚につき1枚）。
- プロト T657–T658、tests/test_vocab_pilot242.py。

### ラウンド277 draw_replacement_double 再変換（2026-11-18）

- reopen 2件 → **新規登録2件**、差し戻し0件。converted **10,020** / rejects **2,318**、重なり0・漏れ0、draw_replacement_double 解消。
- dm26rp1-034 は replace {optional: true, when: {event: draw, player: you}, instead: [draw 2]} を追加。dm28-049 は sforce: true 付きで instead に「手札1枚を山札の一番下へ」を加えた形。
- tests/test_vocab_pilot242_cards.py 2件＋データ監査通過。

## 第243弾 rush op（そのターン限りプレイヤーを攻撃できる）

新 op **rush** {select}: 対象に turn_counters の rush:<cid> フラグを立てる。combat の _attack_options はこの印がある出たターンのクリーチャーにプレイヤーへの攻撃だけを許可する（アビスラッシュの付随処理と同じ印。ただし山札送り等の付随処理は付けない）。

終極宣言の無トリガー召喚（dm23ex3-or2）は既存語彙の組み合わせで表せる: 終極宣言ゲート（第216弾イディオム）＋ choose {zone: [graveyard, mana], count: any} ＋ move {to: bz, reason: summon, no_trigger: true}（第213弾）＋ rush。

注意: rush は move より先に書く。move の後に {ref: summoned} を引くと世代が進んだ参照になり候補が空になる（rush フラグは cid 単位なので移動前に立ててよい）。

- プロト T659–T660、tests/test_vocab_pilot243.py。

### ラウンド278 final_declaration_no_trigger_summon 再変換（2026-11-18）

- reopen 1件 → **新規登録1件**（dm23ex3-or2）。converted **10,021** / rejects **2,317**、重なり0・漏れ0、final_declaration_no_trigger_summon 解消。
- 宣言は第216弾ゲート＋ choose {zone: [graveyard, mana], filter: {race_has: アビス}, count: any} ＋ rush（move より先）＋ move {reason: summon, no_trigger: true} ＋ mark の並び。
- tests/test_vocab_pilot243_cards.py 1件＋データ監査通過。

## 第244弾 gained statics の mod 適用（第240弾の残件）

第240弾で abilities() は常在型 mod.gain を展開するようになったが、得た常在型能力自身の mod は chars に反映されなかった（バトルパワー付与などが死んでいた。コーパスで9枚）。_chars_calc_body に、付与元（自身の self 常在型／バトルゾーンの発生源／シールドの発生源／継続的効果）ごとに、第240弾と同じ適用判定で gain を集める処理を追加。対象は持ち主自身に働く形（affects 無し／"self"／{ref: self}）に限る（コーパスの得る常在型はすべてこの形）。

- プロト T661–T662、tests/test_vocab_pilot244.py。

## 第245弾 dm26ex2-046 再評価（誤タグ行）

rejects で mana_placement_reveal と誤タグされていた dm26ex2-046（断罪のロスト・サイン）の実テキストは、マナ配置条項を持たない S・トリガー呪文だった。実ブロッカーは「見た4枚から召喚した個体への、次の自ターン開始時の遅延バウンス」だが、delayed_trigger は登録時に env の vars を保存し（ops.py）、play_free の as: が召喚後の個体を束縛する（bind タスク）ため、登録済み前例 dm23rp4x-026 と同じく {ref: 変数} で正確に表せる。残りは既存イディオムの組合せ: shuffle → choose {from_top: 4, look} → may [play_free] → modify grant blocker（end_of_turn）→ move {position: bottom, order: choose}。

- プロト T663–T664、tests/test_vocab_pilot245.py。

### ラウンド279（第245弾）

dm26ex2-046（断罪のロスト・サイン）を直接 submit で登録（reopen は使わず、誤タグ行をそのまま解消）。新規1件、バウンスなし。converted 10,022 / rejects 2,316、重複0・漏れ0。mana_placement_reveal の残存行は消滅（ファミリー完全解消）。

## 第246弾 when の cause に defn（発生源カード）

「《特定カード》の能力で破壊される時」を表すため、when の cause 仕様に defn（文字列またはリスト）を追加した。レコードは基盤B1で cause_defn を既に持ち、照合は events._match_when の cause ブロックで行う。defs の検証とスキーマも同期。dmc45-008 の置換は、ギアの常在型（affects: crossed）が mod.gain で置換能力をホストへ与える形: 置換の when は subject: self + cause: {defn: dmc45-009}、追加条件（もう一方のギアもクロスされている）は if {exists: {ref: self, filter: {crossed_name: 雷刃 ブシドー・スピリット}}}、instead: [] でとどまる（登録済み前例と同じ形）。同じ cause 仕様に name_has（発生源の名前の一部）も追加: dm23ex1-020 の「名前に《武者》とあるカードの効果によって相手のクリーチャーが破壊された時」は cause: {by: you, name_has: 武者} で表せる（照合は本体名＋各面の名前）。

- プロト T665–T666（T655 サムライがホスト）、tests/test_vocab_pilot246.py。

### ラウンド280（第246弾）

reopen trigger_when_destroyed_by_named_card_effect で外れた2枚を登録: dmc45-008（風刃 カミカゼ・スピリット、cause.defn の置換を追加）と dm23ex1-020（ボルシャック・大和・ドラゴン「開眼」、cause.name_has の誘発＋攻撃中パワー静的を構築）。新規2件、バウンスなし。converted 10,024 / rejects 2,314、重複0・漏れ0。trigger_when_destroyed_by_named_card_effect ファミリー解消。

## 第247弾 S・トリガーX（イディオム）

S・トリガーX は「シールドゾーンから手札に加える時」の誘発として表せる: {kind: trigger, zone: hand, when: {event: move, from: shield, to: hand, subject: self}, effect: [may [play_free {ref: self, as: gen}, cross_free {gear: {ref: gen}, to: 自分のクリーチャー1体}]]}。play_free がジェネレート（第224弾で permanents 対応）、cross_free op（第195弾）が効果によるクロス。生成後の個体は play_free の as: で束縛してから参照する（移動前の世代は gen-strict で引けない）。

- プロト T670、tests/test_vocab_pilot247.py。

### ラウンド281（第247弾）

dmx21-045（アクテリオン・フォース）を登録。新規1件、バウンスなし。別刷り dm15-s05 は aliases に畳まれ、その reject 行もツールが除去（残存なし）。converted 10,025 / rejects 2,313、重複0・漏れ0。strigger_x ファミリー解消。

## 第248弾 shield_break_intercept_cast（ブレイク置換の割り込み型、第146弾の形）

「ブレイクする時、そのシールドの中の呪文をすべて無料で唱え、その後ブレイクする」は、第146弾のブレイク置換の割り込み型で表せる: {kind: replace, when: {event: break, subject: self}, continue: true, instead: [play_free {select: {ref: event.shield, filter: {types: [spell]}, count: "all"}}]}。諮問はシールドが動く前に行われるため event.shield は生きており、唱えた呪文は通常解決で持ち主の墓地へ行く。continue: true なのでシールドは chosen に残り、ブレイクが続く（ゾーンに残っていないカードは最終 move で自然に外れる）。

ついでに第239弾の break_before レコードへ shield: 割られるシールドの参照を追加した（break レコードと揃える。_record_for は dict(ev) で通す）。なお break_before の誘発から event.shield を引く形は、解決時点ですでにシールドが手札へ移っており世代が合わないため使えない — 差し替え型は置換で表すのが正道。

- プロト T671–T672、tests/test_vocab_pilot248.py。

### ラウンド282（第248弾）

dmr04-003（無限王ハカイ・デストロイヤー）を登録。新規1件、バウンスなし。converted 10,026 / rejects 2,312、重複0・漏れ0。shield_break_intercept_cast ファミリー解消。

## 第249弾 stack_creature_from_deck（move の stack_evo + evo_source、第173弾の形）

「山札から見たクリーチャーをこのクリーチャーの上に置く」は、move op の stack_evo: true + evo_source: {ref: self}（第173弾「このクリーチャーの上に置く」）が受け皿になるが、h_put_stacked は進化クリーチャーしか重ねなかった（partial のノートどおり）。第249弾で、固定の evo_source がある非進化カードも stack_on で重ねる分岐を追加（進化印は付けないので、進化元レコードやシンカパワーの対象にはならない）。見る7枚は choose {from_top: 7, look} のイディオム、残りは山札へ戻してから shuffle。

- プロト T673–T674、tests/test_vocab_pilot249.py。

### ラウンド283（第249弾）

dmex18-023（ゴウケンオー ～秘剣轟誕～）を登録。新規1件、バウンスなし。converted 10,027 / rejects 2,311、重複0・漏れ0。stack_creature_from_deck ファミリー解消。

## 第250弾 g_link_positional / g_link（名前指定と位置キーワードの併記、トライ・G・リンク）

第197弾の名前指定リンクは位置キーワードを持たないゴッド専用だった（side is None の分岐）。邪神M・ロマノフは左 G・リンク（位置キーワード）を持ちながら「《R》または《C》の左横」と名前も指定する。第250弾で h_g_link のキーワード分岐にも link_to の名前制限を効かせた（位置条件を満たすグループのうち、指定名のゴッドがいるグループだけがリンク先になる）。邪神R・ロマノフのトライ・G・リンクは位置キーワードを持たないので、第197弾の名前指定分岐のまま link_to [{M, right}, {C, left}] で表せる（「その間」は M と C がリンク済みのグループへ加わる形で自然に実現する）。

同じ再変換で外れた極限邪神M・ロマノフ（左G・リンクOMG）は指定が「《R》《C》、または『中央/右 G・リンク』を持つゴッド」と混成なので、link_to に {side: left|center|right} エントリを追加した（検証も拡張）。キーワード分岐の名前制限は「名前または side が合うゴッドのいるグループ」に一般化し、位置キーワードを持たない名前指定ゴッド単体へのリンクも、自分の位置が空いていれば候補に加える。

- プロト T675–T678、tests/test_vocab_pilot250.py。

### ラウンド284（第250弾）

dmc58-003（邪神M・ロマノフ）・dmc58-004（邪神R・ロマノフ）・dmex17-037（極限邪神M・ロマノフ）を登録。新規3件、バウンスなし。converted 10,030 / rejects 2,308、重複0・漏れ0。g_link / g_link_positional ファミリー解消。なお reopen は g_link の部分集合だった dmex17-037 も外したため、同ラウンドで一緒に登録して漏れを防いだ。

## 第251弾 attack_cancel（攻撃の中止 op）

「攻撃を中止する」は新しい op **cancel_attack** で表す: タスクスタック上の attack タスクに cancelled 印を付け、h_attack は再開時にバトルもブレイクも行わず attack_end を出して攻撃を終わらせる（AttackTask に cancelled を追加）。攻撃宣言時の誘発（相手の攻撃時・自分の攻撃時）の解決窓で使う。捨てる/破壊する等のコストは may + as: paid + if {exists: {ref: paid}} の既存イディオム、しなかった場合の分岐は if {not: {exists: {ref: var}}} で書ける。

- プロト T680–T682、tests/test_vocab_pilot251.py。

### ラウンド285（第251弾）

dmd03-005（特攻の菊）・dmsd01-010（バッテン親父）・dm26ex4-010（切札混成 光隼 蒼斬丸）・dmrp12-078（パイパーパイプー）を登録。dm26ex4-sec007 は dm26ex4-010 の aliases に自動で畳まれた。新規4件＋alias畳み込み1件、バウンスなし。converted 10,034 / rejects 2,303、重複0・漏れ0。attack_cancel ファミリー解消。

## 第252弾 g_breaker（G・ブレイカー）

キーワード **g_breaker** を新設（keywords.yaml に登録。能力の実体は combat が持つ）。攻撃フェイズ4のブレイカー選択（509.2c）に "all" の選択肢を加え、選ばれたら相手のシールドをすべてブレイクし、その後（相手側のブレイク処理が終わってから）自分のシールドもすべてブレイクする break タスクを積む。付与形は mod grant [g_breaker] + duration: during_attack で表せる。なお dm23rp1-t4（孫条項）と dm26sd1-n008（発声条項）は現実世界の行為を条件にするジョーク条項が残るため、G・ブレイカー自体は解消しても別ギャップで差し戻す。

- プロト T683–T684、tests/test_vocab_pilot252.py。

### ラウンド286（第252弾）

dmx17-014（THE FINALカイザー）・dmc64-008（超銀河剣 THE FINAL）を登録。新規2件。dm23rp1-t4（じーさん）は G・ブレイカー＋シールド化20枚を保存して win_replacement_grandchild で、dm26sd1-n008 は G・ブレイカーを保存して declare_speech で、それぞれ差し戻し（どちらも現実世界の行為・関係を条件にする条項）。converted 10,036 / rejects 2,301、重複0・漏れ0。g_breaker ファミリー解消。

## 第253弾 protect_hand（相手の効果では手札を捨てられない）

常在型キー **protect_hand: true** を新設。そのクリーチャーがバトルゾーンにある間、そのプレイヤーの手札は、相手の呪文またはクリーチャーの能力による破棄（手札→墓地、reason: discard、起因印 by が相手で cause_kind が spell、または起因カードがクリーチャー）を受けない。events の移動適用ガードで判定する（no_leave や破壊耐性と同じ層）。自分の効果による破棄、ギア／タマシード等の能力による破棄は対象外。

- プロト T685–T688、tests/test_vocab_pilot253.py。

### ラウンド287（第253弾）

hand_discard_protection の4件すべてを登録。新規4件（dm24ex3-051、dm23rp2x-029、dmbd04-003、dmrp08-003）。dmbd04-003 のコスト比較条項は count 式（相手のマナ枚数）で表現。converted 10,040 / rejects 2,297、重複0・漏れ0。ファミリー解消。

## 第254弾 action_limit（攻撃/ブロック回数の制限）

新規 op **action_limit** {player, attack?, block?, until}。保留は GameState.action_limits（Rust state.rs にも同名フィールドを追加）。until は caster_next_turn_start（唱えた側の次のターンのはじめまで。st_start で失効）と opp_next_turn（次の相手のターン中だけ）。判定は Engine._action_limit。攻撃は combat の _attack_options で、そのターンに宣言した攻撃回数（turn_counters atk_decl:<p>、攻撃フェイズ0で加算）が上限に達したら選択肢を出さない。ブロックはブロック指定の諮問で、上限到達時はブロッカー候補を空にする（blk_decl:<p> は実際にブロックした時に加算。ガードマンは数えない）。

- プロト T689–T690、tests/test_vocab_pilot254.py。

### ラウンド288（第254弾）

attack_limit の3件を登録。新規3件（dm24rp3-061、dmrp16-015、dmrp22-014）。dm24ex4-066 は誤タグではなく、呪文側が attack_limit・クリーチャー側が別条項のツインパクトだった。呪文側を解決して保存し、non_summon_entry_trigger（召喚以外の方法で出た時）で差し戻し。converted 10,043 / rejects 2,294、重複0・漏れ0。

## 第255弾 breaks_scaling（数で変わるブレイク数）はイディオム

3形とも既存の breaks_add {amount, count} で足りる。(1) 常在の数え上げ: breaks_add {amount: 1, count: {zone: bz, owner: you, other: true, filter: …}}（クロトラ／アウトランダー。後者は shield ゾーンの {keyword: shield_go, face_up: true} 数え上げ）。(2) 束縛した集合の大きさ: 攻撃誘発で破壊した集合を as で束縛し、modify で power {amount: 3000, count: {ref: killed}} と breaks_add {amount: 1, count: {ref: killed}} を end_of_turn 付与（サードニクス）。残る dm24ex3-tf02 は「表向きにした束のうち無色だけを数える count」と「上か下かの配置選択」が要るため、ギャップを精密化して差し戻す。

- プロト T691、tests/test_vocab_pilot255.py。

### ラウンド289（第255弾）

breaks_scaling の3件を登録。新規3件（promoy10-007、dmr12-013、dm25-s03）。dm24ex3-tf02 は revealed_pile_breaks_and_placement に精密化して差し戻し（アタック・チャンス宣言は保存）。converted 10,046 / rejects 2,291、重複0・漏れ0。

## 第256弾 not_reason（when の理由否定）

when に **not_reason**（文字列またはリスト）を追加。「召喚以外の方法で出た時」= {event: move, to: bz, not_reason: summon, subject: …} と書ける。defs の検証、events の _match_when、スキーマの when プロパティに反映。

- プロト T692–T693、tests/test_vocab_pilot256.py。

### ラウンド290（第256弾）

dm24ex4-066（伝達妖精セージ / コンタクト・メッセージ）を登録。新規1件。converted 10,047 / rejects 2,290、重複0・漏れ0。non_summon_entry_trigger 解消。

## 第257弾 unpaid の拡張（マナをタップせずに出た時）

move レコードの unpaid 印を拡張する: バトルゾーン以外から召喚以外の理由でバトルゾーンへ移る移動（効果で「出された」カード）は、マナをタップせずに出ているので unpaid とする。events の両レコード構築（_record_for と _apply_one）に同じ規則を入れた。これで既存イディオム {event: move, to: bz, unpaid: true, subject: …} が、無料召喚と効果出場の両方に効くようになる。既存の「コストを支払わずに出た時」系カード（move 照合のもの）も、公式どおり効果出場で誘発するようになる。

- プロト T694–T695、tests/test_vocab_pilot257.py。

### ラウンド291（第257弾）

entry_without_mana_tap の4件を登録。新規4件（dm26ex4-083、dm26ex4-070、dm26rp1-std001、dm26sd1-s011）。converted 10,051 / rejects 2,286、重複0・漏れ0。

## 第258弾 alt_cost の混合形（cost + do）

alt_cost は {cost, civs} 形と {do: [...]} 形を併記できるが、従来は do の完了時点で free 扱いになり、併記した cost が課金されなかった。h_play の代替コスト処理で、cost を併記した場合は free にせず、行動ステップの後に cost_override で通常どおり支払うよう修正した。「{df04}を支払い、自分のシールドを1つ墓地に置いて唱えてもよい」（鬼火と魍魎の決断）がこの形。

- プロト T696、tests/test_vocab_pilot258.py。

### ラウンド292（第258弾）

cast_time_alternative_cost の3件を登録。新規3件（dm24ex3-rp3s11、dm24ex3-tf20、dm24ex4-060）。dm25ex2-080 は支払い先が超次元ゾーン（範囲外）のため hyperdimensional_alt_cost に精密化して差し戻し。converted 10,054 / rejects 2,283、重複0・漏れ0。

## 第259弾 tap_entry（タップして出してもよい）

面の項目 **tap_entry: true** を追加。h_play の支払いフェーズ（再開可能な地点）で「タップして出すか」を尋ね、選べば召喚の move イベントに tapped を載せてタップ状態で出す。通常召喚・無料召喚・S・トリガーなど、h_play を通る全ての召喚で効く。

- プロト T697、tests/test_vocab_pilot259.py。

### ラウンド293（第259弾）

tap_entry_option の4件を登録。新規4件（dm26rp1-005、dm26rp2-044、dm26rp2-075、dmrp22-043）。dmrp22-043 の partial にあった deny be_attacked は誤読として、dm24rp2-047 の前例どおりプレイヤーへの攻撃 deny に修正した。converted 10,058 / rejects 2,279、重複0・漏れ0。

## 第260弾 mana_all_civs（すべての文明を持つかのようにタップする）

常在キー **mana_all_civs: {for?: 出すカードへのフィルター}** を追加。発生源がバトルゾーンにあれば自分のマナすべてに、マナゾーンのカード自身にあればそのカードだけに効く。_mana_choices の文明キー計算でのみ有効化するので、マナ武装の数え上げなど支払い以外の文明判定には漏れない。「してもよい」は選択肢が増える形で自然に表れる。

- プロト T698–T700、tests/test_vocab_pilot260.py。

### ラウンド294（第260弾）

mana_civilization_tap の4件を登録。新規4件（dm26ex4-081、dm24bd6-042、dm24rp2-074、dm26rp3-012）。パートナー指定のためにフィルターキー partner: true（[P]能力を持つカード）を追加した。「攻撃できない」はキーワード cannot_attack で表す。converted 10,062 / rejects 2,275、重複0・漏れ0。

## 第261弾 CIP能力の使用・呪文回数制限・出場ラッシュ

3つの小さい語彙をまとめて追加する。(1) op **use_entry_abilities** {select, count?}: 対象カードの「出た時」誘発（move→bz、subject self）の効果を、使う側の能力として解決する。self は使う側のまま、event.subject も使う側に差し替える。count があればその数だけ（多い時は使う側が選ぶ）。(2) 常在キー **cast_limit: {count}**: 相手のバトルゾーンにある間、その相手は各ターン count 回までしか呪文を唱えられない。唱えた数は turn_counters の casts:<player> で数え、_play_options の末尾で呪文の選択肢を落とす。(3) mod **player_rush: true**: 出たターンでもプレイヤーだけは攻撃できる（combat の rush 判定に chars 側の条件を追加）。

- プロト T701–T705、tests/test_vocab_pilot261.py。

### ラウンド295（第261弾）

CIP能力の使用系を再変換。新規4件（dmrp08-010、dm25ex3-rp3007、promoy17-sp4d01、dm26ex4-cho005＝ジョギラゴン＆ジョニー。dm26sd1-n001 は原文コーパス外の ID のため、同一カードの cho005 を正規形として登録し、n001 は alias に収めた。n001 の rejects 行は alias 側の残行として残る）。dm25ex2-004 は攻撃先を自分が選ぶ条項が未対応のため、新ギャップ attack_target_choice で差し戻し（残りは保存）。converted 10,066 / rejects 2,271、正規重複0・漏れ0。

## 第262弾 declare group（この攻撃中に1回まで）

宣言型能力に任意キー **group: <名前>** を追加。同じ group の宣言は、1回の攻撃につきプレイヤーごとに1回までしか宣言できない（ニンジャ・チェンジの「この攻撃中に自分が『ニンジャ』能力を使っていなければ」）。_declarable が現在の攻撃番号（turn_counters の current_attack）と使用済み印を照合し、h_declare が宣言時に印を立てる。ニンジャ・チェンジ自体は既存の declare 窓（攻撃宣言時は防御側にも、ブロック時は両者に開く）と op swap の組み合わせで表す。

- プロト T706–T707、tests/test_vocab_pilot262.py。

### ラウンド296（第262弾）

ninja_change の5件を登録。新規5件（dm23sd2-001、dm25ex1-014、dm25ex1-034、dm25ex1-mc009、dm26sd1-s001）、差し戻しなし。converted 10,071 / rejects 2,266、重複0・漏れ0。

## 第263弾 dragon_mana_buso（龍マナ武装）

「龍マナ武装 N」は、自分のマナゾーンにあるドラゴン・クリーチャーが N 体以上ある時に能力が働く条件。既存の式 `{cmp: [{count: {zone: mana, owner: you, filter: {types: [creature], race_has: ドラゴン}}}, ">=", N]}` で表す（忍者のマナ7枚条件と同型）。`if` にも `op: if` の cond にも静的の `if` にも書ける。シールドゾーンの常在型（`zone: shield` + `grant: [s_trigger]`）も同じ `if` で動き、ブレイク時の宣言は移動前（まだシールドゾーン）の特性で判定されるため付与が効く。

本弾で足した小さい語彙は3つ。(1) cond **extra_turn**（bool）: このターンが追加ターンか。「これが追加ターンでなければ」は `{extra_turn: false}`。GameState に `extra_turn` を追加し、h_turn が extra_turns からの開始時に立てる。Rust 側も state.rs＋setup.rs＋engine.rs の遷移＋eval_cond を同期（dmcore のビルドはこの環境に無いため stamp は更新しない。前弾と同じ扱い）。(2) セレクタ **distinct_names: true**: 「名前が異なる」選択。distinct_costs と同じ積み上げ分岐に乗り、既に選んだ名前を候補から外す（異なる名前の Jack-Pot を好きな数出す用）。検証は distinct_costs と同型（count 併記必須、count: all 単独は不可）。(3) 生成時ベイクの拡張: `_bake_refs` が `{cost_of / power_of / name_of / races_of}` も生成時の値に焼く。dynamic な modify の範囲フィルタに「表向きにしたカード以下のコスト」を書けるようになる（`{cost_le: {cost_of: shown}}` はベイク前だと特性計算時に dict 比較で落ちる）。

- プロト T708–T716、tests/test_vocab_pilot263.py（12件）。

### ラウンド298（第263弾）

dragon_mana_buso の6件をすべて新規登録、差し戻しなし。新規6件（dm26ex3-016、dm26ex3-021、dm26ex3-034、dm26ex3-037、dm26ex3-046、dm26ex3-073）。converted 10,081 / rejects 2,256、重複0・漏れ0。tests/test_vocab_pilot263_cards.py（4件）＋tests/test_vocab_pilot263.py（12件）が通る。dm26ex3-037 の partial の text は「龍マナ武装７」しかなかったため全文を raw 行から補完。「マッハファイター」は keywords.yaml に無いため dm26ex3-037 のドラゴン付与は展開形の allow（attack_creature・tapped: false）を speed_attacker 付与と併記。dm26ex3-034 の「合計5枚置いてもよい。そうしたら追加」は effect 内 if（Jack-Pot 合計5枚以上の存在確認。select の count は不足時に切り詰められるためガード必須）＋may［move 5枚＋extra_turn］。proto テストと cards テストは同一 pytest 呼び出しで混ぜないこと（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが汚染される。第261弾の教訓どおり別プロセスで実行）。

## 第264弾 trigger_doubling（誘発の2度トリガー）

常在 mod **trigger_double** を追加。誘発の収集時（`_collect_triggers`）に、条件に合う誘発型能力へ適用する。

```yaml
mod:
  trigger_double:
    when: <when-spec>            # 必須: 誘発の原因イベントへの照合（when と同じ言語）
    source: <subject-pattern>    # 任意: 能力の発生源カードへの条件（"self" か {owner?, filter?, other?}）
    source_subject: true         # 任意: 能力の発生源が原因イベントの subject と同一であること
    may: true                    # 任意: 任意（決定を尋ねる）。省略時は強制
    once_per_turn: true          # 任意: 各ターン1回まで
    first_per_turn: true         # 任意: 各ターンはじめての一致だけ
    cost: [<ops>]                # 任意: 適用時に解決するコスト ops（may が必須）
```

- 強制は収集時に pending をその場で複製する（2度目の解決は vars を分ける。bazurenda の複数解決と同型）。
- 任意（may）は同じ窓に `double_ask` の pending を積み、専用タスク `h_double_ask`（`DoubleAskTask`）で決定を尋ねる。「はい」なら対象を複製し、コストがあれば解決する（複製した誘発の解決より先に走る）。対象が先に解決されていたら尋ねない。`once_per_turn` は「はい」で消費し（断っても回数は残る）、`first_per_turn` は最初の一致で枠を使い切る（断ってもそのターンはもう来ない）。
- 常在型（バトルゾーンのカード自身の static。`if` は収集時に eval_cond で見る）と継続的効果（modify で付与されたもの。`affected` の各カードが発生源）の両方を見る。`affects` が self でない常在型と dynamic の継続的効果はこの弾では扱わない。
- 対象は通常の誘発（kind normal）のみ。遅延誘発（delayed）と declare 経由の pending は対象外。
- **再入の教訓**: 任意の決定を `h_resolve_pending` の中で直接尋ねてはいけない。再入時に先頭の `order_pending` の ask が回答を誤消費し、double_ask が消えて複製も印も失われる（本弾で実測）。決定は専用タスクへ分離すること。タスクは `base/types.py` に TypedDict を足し、`@task` で登録する（check_shape が厳密なため）。
- 複数の2度トリガーが同じ誘発に合う時は、それぞれが1回ずつ追加する（N+1回）。重ね掛けの乗算（2^N）は裁定待ちのためこの弾では扱わない。
- Rust: 新しい GameState フィールドは無い（state.rs の変更なし）。Rust 側の `collect_triggers` は部分実装で、2度トリガーのミラーは未実装。dmcore のビルドはこの環境に無いため stamp は更新しない（第263弾と同じ扱い。stamp は HEAD 時点ですでに stale）。Rust は `double_ask` pending を uns("pending kind") で弾くため、2度トリガーがある対局では Python にフォールバックする。
- 関連ギャップ `cip_trigger_double`（dm25ex3-010、dm26ex3-053）は別ギャップとして残す。dm25ex3-010 の「出た時誘発の2度トリガー」はこの語彙で表せる見込み（ラウンド側で判断）。dm26ex3-053 の Dスイッチ（ゲーム中で1度上下逆さまにする）は別語彙が要る。

- プロト T717–T728、tests/test_vocab_pilot264.py（15件）。

### ラウンド299（第264弾）

trigger_doubling の6件のうち5件を新規登録、1件を差し戻し。新規5件（dmrp04s-004、dmrp21-013、dmrp22-040、dmex03-s02、dm24ex3-rp2s07）。差し戻し dmrp12-008 → opt_reduce_then_entry_destroy（離脱型の2度トリガー＋W・ブレイカーは解決して partial に保存。残余は「コストを２少なくしてもよい。そうしたら、このターン、出た時、自分のクリーチャーを１体破壊する」条項：opt_reduce.then はターン終了時の destroy / deck_bottom_draw のみで、出た時の破壊は表せず、軽減したかどうかの条件も無い）。converted 10,086 / rejects 2,251、重複0・漏れ0。tests/test_vocab_pilot264_cards.py（3件）が通る。見守り実行がタイムアウトで中断したため、カードテスト・本節・コミットは後続の実行で仕上げた。

## 第265弾 ultimate_evolution_max（究極進化MAX）

共通文言: 「究極進化MAX：自分の究極進化クリーチャー１体の上に置く。」対象は dm26ex1-020 / dm26ex1-039 / dm26sd1-y004 / dm35-002（単独ギャップ）＋ 35-sec001（selector_filter_or も併せ持つ）。

- 公式裁定の確認: 「究極進化クリーチャー」とは究極進化の能力を持つクリーチャー、すなわち自身の進化条件（`evolve_from`）が進化クリーチャーを要求するカードである。バトルゾーンへの出方は問わない（効果で直接出た究極進化クリーチャーも究極進化クリーチャーであり、MAX の進化元になれる）。よって **def レベルの判定 (a)** を採用し、進化で出た履歴を見る (b) は採らない。第30弾で究極進化自体は `evolve_from: {types: [evolution]}` で既存表現可とされているので、その述語形としてフィルタキーを足すのが最小の語彙である。
- 新語彙: フィルタキー **`ultimate_evolution: true|false`**。対象カードの `fdef(cid).evolve_from`（単一フィルタまたは進化Vのリスト）のいずれかが「進化クリーチャーを要求する」場合に真。要求するとは `types` に `evolution` を含むこと。`any_of` は全分岐が要求する場合に要求とみなす。進化Vで片方の分岐だけが究極進化を要求する札は実在しないので、分岐の扱いは `any`（いずれかの分岐が要求すれば究極進化クリーチャー）とした。
- 用法: `evolve_from: {ultimate_evolution: true}`（NEX 4枚の進化条件）。`_evo_sources` → `_evo_match` → `filter_match` の経路でそのまま働くので、進化まわりの本体変更は不要。一般の select フィルタとしても使える（「自分の究極進化クリーチャーを1体破壊する」等）。`false` 形は「究極進化クリーチャーではない」。
- 注意: 従来の partial にあった `evolve_from: {types: [evolution]}` は近似である（進化クリーチャー全般に広げすぎ。35-sec001 の partial の notes に明記あり）。ラウンド300で `{ultimate_evolution: true}` に正す。dm26ex1-020 / dm26ex1-039 の partial の `evolve_from: {types: [creature]}` も同様に正す。
- dm26sd1-y004 の「このクリーチャーを自分のマナゾーンから召喚してもよい」はキーワード `summon_from_mana`（第28弾）で既存表現可。攻撃時能力（山札の上から3枚までマナへ＋マナからクリーチャーを好きな数出す＋出た時の効果・ルール無視）はラウンド300で既存語彙（`no_trigger` 等）で組む。
- Rust: 新しい GameState フィールドは無い（state.rs の変更なし）。Rust 側の `filter_ok` は未知のフィルタキーを `Unsupported` で返すため、究極進化MAXのカードがある対局では Python にフォールバックする（第264弾と同じ扱い）。dmcore のビルドはこの環境に無いため stamp は更新しない（第263/264弾と同じ扱い）。Rust 側の `Def` は `evolve_from` を `Value` で持っているので、将来のミラーは可能。

- プロト T729–T733、tests/test_vocab_pilot265.py（9件）。

### ラウンド300（第265弾）

ultimate_evolution_max の4件を新規登録、差し戻しなし。新規4件（dm26ex1-020 ロマノフカイザー・NEX：出た時・相手2体破壊＋マナ2枚墓地／離れた時・山札サーチ any_of、dm26ex1-039 ギャラクシー・デスティニー：攻撃時・山札からクリーチャー2体まで出す、dm26sd1-y004 ギュンター・ペガサス：マナ召喚＋攻撃時・山札上3枚までマナ＋マナから好きな数出す no_trigger、dm35-002 ギャラクシー・オペレーションθ：攻撃時・山札から呪文1枚を無料唱え／離れた時・墓地の呪文すべて手札）。partial の evolve_from 近似は {ultimate_evolution: true} に正した。35-sec001 は dm26ex1-020 の同名別版として aliases に折り畳まれ、rejects には alias-level stale 行として残る。converted 10,090 / rejects 2,247、重複0・漏れ0。tests/test_vocab_pilot265_cards.py（9件）が通る。

## 第266弾 exile_doron_go（ウルトラ・ドロン・ゴー）

共通文言: 「ウルトラ・ドロン・ゴー：このクリーチャーが離れた時、名前に《X》とあるエグザイル・クリーチャーを１体、自分の手札から出してもよい。自分の他の、名前に《X》とあるエグザイル・クリーチャーは出せない。」対象は dm22ex1-021 / dm22ex1-080 / dm22ex1-090 / dm22ex1-cho22（単独ギャップ）。

- 新語彙: 型印 **`exile_creature`**（defs の CARD_TYPES。第174弾の dream_creature と同型）。types には通常 `["creature", "exile_creature"]` と書く。フィルタ `{types: [exile_creature]}` は selectors の汎用の集合照合でそのまま働くため、エンジン変更なし。schema は再生成で追随（差分は型の列挙×2）。Rust 側の変更なし（types は文字列リストで、filter_ok は汎用の文字列照合）。
- **発見（今回の本質）**: 従来、converted.yaml には `types: [exile_creature]` をフィルタに書いたカードが10箇所あったが、どのカードの types にもその印が無く、照合は常に偽だった（死んだフィルタ）。エグザイルは種族では識別できない（エグザイルの種族はアウトレイジMAX / アウトレイジOMG / オラクリオン / オラクルの4種だが、非エグザイルのアウトレイジMAXは169枚ある）。今回、変換済みのエグザイル・クリーチャー28枚の types に印を付け、その10箇所が初めて生きる。
- ウルトラ・ドロン・ゴーの型（ドロン・ゴーとの差は誘発条件だけ）:
  - 誘発 `{event: move, from: bz, subject: self}`（行き先を問わない「離れた時」。dm22ex1-055 の「離れた時」と同型）。効果は may [move {select: {zone: hand, owner: you, filter: {types: [exile_creature], name_has?: X}}, count: 1, to: bz, reason: put}]。名前に制限が無い札（dm22ex1-090 / cho22）は name_has を省く。
  - 出場制限は常在型5つ（hand / graveyard / mana / deck / shield の各ゾーン。dmd11-005 のドロン・ゴーと同型）で、filter は `{types: [exile_creature], name_has: X}`、mod は `{deny: [enter_bz]}`。
- **移行（同じコミットで実施）**: 既存の27枚の制限の常在型135箇所と、ドロン・ゴー誘発の select 25箇所（+ any_of 形2箇所）のフィルタを、従来の近似 `{name_has, races: [アウトレイジMAX]}` から精密な `{name_has, types: [exile_creature]}`（any_of 形は各分岐を同様に）に正した。近似は両方向に誤っていた：非エグザイルの「熱血武闘 カツキング」「極大左神 マックス」「武闘親父 カツドン」等（種族アウトレイジMAXで名前に武闘／神を含む）を誤って制限・対象にし、種族がアウトレイジMAXでないエグザイル（dmr12-v02 はアウトレイジOMGのみ）を見逃していた。real.yaml / real_akashic.yaml にはエグザイル・クリーチャーは無い（アウトレイジMAXの2件は非エグザイル）ので、そちらの移行は不要。
- **チーム・エグザイルの無視能力**（dm22ex1-cho22「このクリーチャーが自分の手札またはバトルゾーンにある時、自分のエグザイル・クリーチャーの持つ、エグザイル・クリーチャーを出せないようにする能力を無視する」）は、制限側の常在型の `if` で表す: `{not: {exists: {zone: [hand, bz], owner: you, filter: {name_has: チーム・エグザイル}}}}`。常在型はバトルゾーンの発生源からしか働かず、手札にある時の無視を cho22 自身の能力では表せないため。mod.ignore は対象カードの常在型をすべて無視してしまうので使えない（deny 以外の常在型まで消える）。「チーム・エグザイル」を名前に含むカードは原文コーパスに cho22 だけ。既存の135箇所すべてにこの `if` を付けた（cho22 の無視はすべてのエグザイルの制限能力に及ぶため）。cho22 自身の def には無視の能力は書かない（名前が鍵）。将来、同能力を持つ別名のカードが増えたら、すべての制限の `if` の filter を見直す必要がある。
- **教訓**: 同一の dict オブジェクトを複数箇所の `if` に使い回すと、cardstore.write（safe_dump）が共有オブジェクトにアンカーを打ち、以降のアンカー番号がずれて差分が膨らむ。移行スクリプトでは箇所ごとに deepcopy する（初回はこの罠で差分が 1083行になり、やり直した）。types リストも共有オブジェクトの場合があるので、新しいリストに置き換えること。cardstore の load→write ラウンドトリップは無変更時にバイト同一であることを事前に確認した。
- **テスト上の注意**: 選択肢が1枚だけの決定は ask が自動回答するため、誘発の出し先の選択は決定として現れない（破壊テストでは choose_cards が出ない）。候補が複数ある時だけ決定が出る。制限が働いている時の誘発の move は、選択自体が出ずに permits で止まる（T735 は手札に残る）。dmr11-008（天空美麗 ミケラ・ジェンヌ）は制限を持たないエグザイル（誘発のみ）。

- プロト T734–T739、tests/test_vocab_pilot266.py（10件）。

### ラウンド301（第266弾）

exile_doron_go の4件すべてを新規登録、差し戻しなし。新規4件（dm22ex1-021、dm22ex1-080、dm22ex1-090、dm22ex1-cho22）。dm22ex1-021 の CIP は destroy count:any + as:k で破壊数を保持し、draw count:{count:{ref:k}} で同数ドロー、その後手札からエグザイルを1体出す（dm25ex2-cho030 / dm22rp2x-tf6 型）。dm22ex1-080 はツインパクト（呪文面は相手が選んで破壊 chooser: opp、dm21-028 型）。dm22ex1-cho22 のコスト∞は partial の慣例どおり 999。dmx22b-014 は dm22ex1-cho22 の aliases に折り畳まれた。converted 10,094 / rejects 2,243、重複0・漏れ0。tests/test_vocab_pilot266_cards.py（14件）が通る。

- **CIP の罠**: dm22ex1-021 の CIP で手札の《神》エグザイル（T735）は出せない。自身の出場制限が場に出た瞬間から働くため、破壊→ドローまでは進むが、put は permits で止まる。テスト test_021_cip_cannot_put_restricted で確認。
- **テストの罠**: dm22ex1-021 は無色コスト11のため、火マナでは play 選択肢が出ない（文明「zero」をマナの文明集合に要求する）。無色の T423 を11枚マナに置く。ウルトラ誘発の出し先は 021 では名前に《神》とあるものだけなので、T739 では不発になる（T735 を使う）。

## 第267弾 rinne（輪廻∞）

共通文言: 「輪廻∞：このカードの呪文側を、バトルゾーンに置いたまま唱えてもよい（コストは支払う）。そうした時、自分の《天地命動 バラギアラ》１体につき、自分の山札の上から１枚をマナゾーンに置く。」対象は dm26rp3-s011 / dmex08-258 / dmrp08-mh05 / dmrp21-tr2（＋sec012 は s011 の別印刷）。

- 新語彙: 面項目 **`rinne: true`**（ツインパクトのクリーチャー側に付ける。第226弾の grave_cast と同型）。defs の Face / CardDef、schema.py の面項目、dataaudit の _STRUCT_FIELDS、base/types.py の Option / PlayTask に追加。schema 再生成の差分は `rinne: {}` 2箇所＋via 列挙への `rinne` 1行。Rust 側の変更なし（第226弾と同じく定義項目のみ）。
- `via` に **`rinne`** を追加（defs.VIAS）。cast イベントには `from: bz` と `via: rinne` が載る。
- エンジン（turn.py のみ）: _play_options にバトルゾーン分岐を追加し、rinne 持ちの呪文側を通常コストで唱える選択肢 `play:<defn>:1:rinne` を出す（墓地からの grave_cast 分岐と同型）。h_play は rinne の時だけ (a) bz のガードを素通りし、(b) 保留へ移さず、(c) 面を変えず、(d) 呪文解決後の墓地への移動を省く。コスト支払い・casts カウンタ・S・トリガー等の処理は通常の呪文分岐をそのまま使う。
- マナ・チャージは誘発のイディオムで表す: `{kind: trigger, when: {event: cast, via: rinne, subject: self}, effect: [repeat {times: {count: {zone: bz, owner: you, filter: {name_has: <名>}}}} [move {select: {zone: deck, owner: you, from_top: 1}, to: mana, reason: put}]]}`。手札からの通常詠唱や cast_face（スマッシュ・バースト。via 無し）では誘発しない。誘発は cast イベントの待機窓で解決するため、呪文の解決の後にチャージされる（第226弾の再唱イディオムと同じ順序）。
- **チャージの罠**: move の select は `{zone: deck, count: 1}` では山札の任意の1枚を選ぶ決定が出てしまう。「上から1枚」は `{zone: deck, owner: you, from_top: 1}`（count 無し。dm18-136 型）。
- 呪文側の型（すべて既存語彙の組み合わせ）:
  - 輪廻虹災: choose {from_top: 5, look: true, count: all, reveal: true} で表向きにし、文明ごとに if {exists: {ref: pile, zone: deck, filter: {civs: [X], cost_le: 9}}} → may [play_free]（dm24bd1-007 の「各文明１枚ずつは文明ごとに分解」と同型）。残りは move {ref: pile, zone: deck, count: all, to: deck, position: bottom, order: choose}。
  - 輪廻暴炎: destroy {total_power_le: 3000}（第144弾）＋このターンの grant。
  - 天上天下輪廻独尊: modify {power: 8000, grant: [world_breaker], dynamic: true, duration: end_of_turn} ＋ modify {must_attack_creature: true, dynamic: true, duration: until_next_own_turn_start}（第194弾。must_attack は付けない＝攻撃自体は強制しない）。
  - 輪廻暴冥: 既存語彙のみ（-4000 は modify、墓地からは move）。
- CIP「召喚によって出た時、自分のマナゾーンにあるカードをすべてアンタップする」は trigger {event: move, to: bz, subject: self, reason: summon} → untap {zone: mana, owner: you, count: all}（dm26ex3-dcr012 型に reason: summon を追加）。

- プロト T740–T742、tests/test_vocab_pilot267.py（8件）。

### ラウンド302（第267弾）

rinne の3件すべてを新規登録、差し戻しなし。新規3件（dm26rp3-s011、dmex08-258、dmrp08-mh05）。dm26rp3-sec012 は dm26rp3-s011 の同名別印刷として aliases に折り畳まれた（canonical dedup のため submit の対象外。dm26ex4-sec022 と同型）。dmrp08-mh04 は dmex08-258 の同名別印刷として aliases に折り畳まれた。呪文面はすべて第267弾の設計どおり：輪廻虹災は T740 型、輪廻暴炎は modify grant [speed_attacker]（dm20-030 型）＋destroy total_power_le: 3000、天上天下輪廻独尊は modify {power: 8000, grant: [world_breaker], dynamic: true, duration: end_of_turn}＋modify {must_attack_creature: true, dynamic: true, duration: until_next_own_turn_start}。converted 10,097 / rejects 2,239、重複0・漏れ0。tests/test_vocab_pilot267_cards.py（6件）＋tests/test_vocab_pilot267.py（8件）が通る。data audit 8件、file schemas＋Rust schema sync も通過。

- **schema 取りこぼし**: 第267弾の schema 再生成で via 列挙への `rinne` 追加が漏れており、ラウンド302の最初の submit が「スキーマ不一致: 'rinne' is not one of [...]」で失敗した。`python -m dmsim.cards.schema` は標準出力に吐くだけでファイルを書かないため、再生成時はリダイレクトで data/schema/card.schema.json を上書きすること。差分は via enum への `"rinne"` 1行のみ。新しい via を足す時は schema 再生成の差分に enum 側も含まれるか確認する。
- **テストの罠**: ツインパクトのクリーチャー面の play キーは `play:<defn>:0`。`play:<defn>` だけでは選択肢に一致せず、カードが出ないままゲームが終わる。
- dmrp21-tr2（輪廻暴冥）はギャップ名が `rinne_infinity` のため今回の対象外。次回以降の対象。

## 第268弾 dogiragon_gacha（ドギラゴン・ガチャ）

共通文言: 「ドギラゴン・ガチャをN度回す。回すたびに、その能力を使う。」対象は dmd34-001 / dmd34-003 / dmd34-004 / dmd34-008（単独ギャップ）。

- **ガチャは実物フィギュア依存だが実装可能**: ドギラゴン・ガチャは DMD-34 のガチャフィギュアの出目で決まるが、出目→能力の対応表は公式に定まっており（Duel Masters Wiki「Gacha Figure」）、フィギュアは乱数発生器にすぎない。out_of_game（実世界依存で棚上げ）とは違い、シミュレータの決定的乱数で正確に置き換えられる。公式が「公式大会ではガチャ能力を使えない」としているのはフィギュアの使用可否の話で、対応表そのものは定義済み。
- 出目表（1d6）: 1 ブースト＝山札の上から1枚をマナへ / 2 リプレニッシュ＝1枚引く / 3 ブレイク＝自分のクリーチャー1体がこのターンさらに1枚ブレイク / 4 デストロイ＝相手のコスト7以下のクリーチャー1体を破壊 / 5 ファイト＝自分のクリーチャー1体と相手のクリーチャー1体をバトル / 6 ストライク＝自分のマナから進化ではないクリーチャー1体を出す。
- 新語彙: op **`gacha`** `{op: gacha, kind: dogiragon, times: N}`（既定1回）。宣言は `dmsim/base/opvocab.py` の OP_ARGS に追加し、engine 側の `@op` と型が食い違うと登録時にエラーになる。kind の値検証は defs.py の Checker.ops に追加（play_self.via と同型。未知の kind は submit 前に DefError）。
- エンジン（ops.py）: op_gacha は専用タスク `gacha` を `_defer` で積む（`_push` だと h_effect が pc を進めず同じ op を繰り返す罠）。タスク handler h_gacha が1回分ずつ `rng_below(s, 6) + 1` を振り、出目を s.pub に kind: "gacha"（result・name・player・viewers [0, 1]）で公開記録してから、その出目の効果を子タスク（effect）で解決する。子タスクが終わると handler が再び頂点に来るので `spin` を消して次を振る。後の出目は前の効果の解決後に振るため、公開記録が未来の出目を漏らさない。
- 6つの効果はすべて既存語彙: Boost は move `{zone: deck, owner: you, from_top: 1}` → mana（dm18-136 型。count 無しで決定が出ない）/ Replenish は draw / Break は modify `{breaks_add: 1, duration: end_of_turn}`（dmr22-s03 型。`chars_ro(cid)["breaks_add"]` で観測できる）/ Destroy は move `{filter: {types: [creature], cost_le: 7}}` → graveyard, reason: destroy / Fight は choose ×2（変数 gacha_a/gacha_b）→ force_battle `{ref: ...}` / Strike は move `{zone: mana, filter: {types: [creature], not_types: [evolution]}}` → bz（dm23bd7-043 型）。選ぶものが無い出目は決定を出さず何も起きない。
- Rust: 新しい GameState フィールドは無い（state.rs の変更なし）。gacha op は Rust 未移植のため、ガチャを含む対局は Python にフォールバックする（第264弾と同じ扱い）。dmcore のビルドはこの環境に無いため stamp は更新しない。s.pub は Rust 側で `Vec<Value>` のため result/name の追加キーは素通りし、infoset は cid の無い記録を無視する。
- **テストの罠**: 単面クリーチャーの play キーは `play:<defn>`（面番号なし）。`play:<defn>:0` はツインパクト専用で、単面では選択肢に一致せず出ないままゲームが終わる（デッキ切れで敗北）。`zlist("bz", p)` は共有ゾーンで両軍分を含むため、バトルゾーンの枚数比較は `bz_tops(controller)` で絞ること（第261弾の教訓と同じ）。

- プロト T743–T745、tests/test_vocab_pilot268.py（4件）。seed 1..48 のスイープで6出目すべてが出て、各出目の局面変化が署名どおりになることを確認（Boost/Replenish は山札−1、Break は breaks_add 1、Destroy/Fight は墓地行き、Strike はマナ−1・場＋1）。

### ラウンド303（第268弾）

dogiragon_gacha の4件すべてを新規登録、差し戻しなし。新規4件（dmd34-001、dmd34-003、dmd34-004、dmd34-008）。dmd34-001 は革命チェンジ（ルール側で declare＋swap に分解。火/自然のドラゴン＝filter {civs: [fire, nature], race_has: "ドラゴン"}、dm23rp3-042 型）＋W・ブレイカー（double_breaker）＋CIP ガチャ3度。dmd34-003 はスピードアタッカー＋CIP ガチャ1度、dmd34-004 は S・トリガー呪文（spell キーでガチャ2度）、dmd34-008 は CIP ガチャ1度。タップイン（マナゾーンに置く時タップして置く）は多色カードの一般則（core.py: 多色カードはマナにタップして置かれる）で処理されるため面項目なし。converted 10,101 / rejects 2,235、重複0・漏れ0。dogiragon_gacha ギャップは残り0件でファミリー解消。tests/test_vocab_pilot268_cards.py（7件）＋tests/test_vocab_pilot268.py（4件）が通る。data audit 8件も通過。

- **テストの罠**: declare / attack の決定キーは `declare:<defn>:1` / `attack:<defn>:player` のように接尾辞が付く。完全一致で探すと見つからず、宣言を逃してデッキ切れで敗北する。`startswith("declare:<defn>")` / `startswith("attack:<defn>")` で探すこと（第262弾の `declare:T706` 検索と同型）。

## 第269弾 s_trigger_x（S・トリガーX）

共通文言: 「S・トリガーX（このクロスギアをシールドゾーンから手札に加える時、コストを支払わずにすぐジェネレートし、自分のクリーチャー１体にクロスしてもよい）」対象は dm23ex1-066 / dm29-034 / dm15-023 / dm15-026 / dm15-029 / dm15-032（6枚）。うち4枚は単独ギャップ、残り2枚の cross_free_op は第195弾の op cross_free で表せる（cross_free op 自体は既存語彙で、9枚の cross_free_op ギャップはすべて他ギャップとの複合）。

- 新語彙: キーワード **`s_trigger_x`**（data/rules/keywords.yaml）。通常の S・トリガーと同じくシールドゾーンからの常在型 `{allow: [s_trigger]}` を与えるので、ブレイク時の declare_strigger の選択肢に出る。宣言して解決すると、通常の S・トリガーと同じく play_task（free）でジェネレートされる。
- エンジン（events.py の h_resolve_pending の strigger 分岐のみ）: 解決する S・トリガーの発生源が s_trigger_x を持つ時、play_task の後に効果の子タスクを1つ積む。子タスクは `if`（`self_entered` が存在し、自分のバトルゾーンにクリーチャーがいる）→ `may` → `cross_free {gear: {ref: self_entered}, to: {zone: [bz], owner: you, filter: {types: [creature]}}}`。生成後の姿は self_entered で指す（生成で gen が1増えるため、宣言時の古い ref では candidates が空になる）。生成されなかった時や自分のクリーチャーがいない時は尋ねない。
- Rust: 新しい GameState フィールドは無い。s_trigger_x は _OK_KW に無いため、S・トリガーX を持つカードを含む対局は Python にフォールバックする（第268弾のガチャと同じ扱い）。
- **schema 取りこぼし**: キーワード追加時は `python -m dmsim.cards.schema` の再生成が要る（第267弾の via 漏れと同型）。初回は漏れてラウンド304の validate が「's_trigger_x' is not one of [...]」で失敗した。再生成の差分は `"s_trigger_x"` 3行のみ。
- **テストの罠**: S・トリガーXで出たギアの「出た時」誘発は、クロスの子タスクの後に checkpoint の resolve_pending（win 0）で解決される。単一の待機誘発は order_pending が自動回答されるため決定としては現れず、次に現れるのは誘発の効果の選択（T747 のタップ先）である。クロス先の選択は候補1枚なら自動回答されるため、ドライバの choose_cards で現れるのはタップ先だけ。タップ先は T002（アンタップ）を選ぶこと。タップ済みの攻撃者 T001 を選ぶと無意味なタップになり、テストがデッキ切れで終わる。

- プロト T746–T747、tests/test_vocab_pilot269.py（5件）。

### ラウンド304（第269弾）

s_trigger_x の6件すべてを新規登録、差し戻しなし。新規6件（dm23ex1-066、dm29-034、dm15-023、dm15-026、dm15-029、dm15-032）。dm23ex1-066 は出た時／クロス先の攻撃時の2誘発（tap no_untap_next）。dm29-034 は出た時の無償クロス（may＋cross_free）＋攻撃時のシールド・プラス。dm15-023 はブロッカー付与＋クロス先の破壊時に付け替え（when move from bz to graveyard reason destroy subject crossed。lki 照合で発火）。dm15-026 は常在型 affects crossed（power 5000＋blocker＋cannot_attack）。dm15-029 は動的パワー（power {amount: 1000, count: {zone: bz, owner: any, filter: {tapped: true}}}）。dm15-032 は攻撃時誘発 destroy total_power_le 3000 count any。promoy4-014 は dm15-032 の同名別印刷として aliases に折り畳まれた。converted 10,107 / rejects 2,229、重複0・漏れ0。s_trigger_x ギャップは残り0件でファミリー解消。cross_free_op は残り7件（他ギャップとの複合）。tests/test_vocab_pilot269_cards.py（8件）＋tests/test_vocab_pilot269.py（5件）が通る。data audit 8件、file schemas＋Rust schema sync、test_rules.py（40件）も通過。

- **テストの罠**: クリーチャーはタップ状態のものしか攻撃できない。dm15-023 の付け替えテストでは、ホストを攻撃する前に p1 のターンでホスト自身に攻撃させてタップさせる必要がある。choose_cards は所有者で区別する: 自分のクリーチャー＝クロス先（T001 がいればそれ、なければ付け替え先の T002）、相手のクリーチャー＝タップ先／破壊先（T002 がいればそれ）。T002 優先の一律ルールにすると、S・トリガーXのクロス先選択で T002 を選んでしまい、ホストが T001 にならない。

## 第270弾 ability_copy（他者の誘発能力の使用）

共通文言: 「相手のターンに相手のクリーチャーが出て、その能力がトリガーした時、自分もその能力を使ってもよい」（魔誕の斬将オルゲイト dm26sd1-a005）。ジョギラゴン＆ジョニー dm26sd1-n001 の「捨てたカードの出た時能力を１つ使う」は第261弾の use_entry_abilities で既に表せており、n001 は dm26ex4-cho005 として登録済み（rejects 行は alias 側の残行）。

- 新語彙は2つ。(1) イベント **`trigger`**（defs.EVENTS に追加）: 自身の出た時能力が誘発したこと。events.py の _collect_triggers が、通常の待機誘発を積んだ直後に発表する。発表の条件は厳密に「自身の」出た時能力: ability の when が {event: move, to: bz, subject: self または無し} かつ発生源 src が移動レコードの subject と同じカード（lki 経路・host_only は除外）。観測型（subject が他カード）の誘発や、trigger イベント自体を見る能力は発表しないので再帰しない。2度トリガーの複製分は発表しない（1能力1回）。レコードは {ev: trigger, subject: 発生源の ref, controller/player, defn, ab: 能力添字, ability: 能力そのもの, face?, from/to/reason: 元の移動}。発表は同じ _collect_triggers の再帰呼び出しで行うため、遅延誘発の when 照合や once_per_turn / first_time の扱いも通常の誘発と同じ。待機順序は元の誘発（＋2度トリガー複製）の後になる。
- (2) op **`use_triggered_ability`**（引数なし。base/opvocab.py に `{}` で宣言）: env.event の trigger レコードが指す能力の effect を、使う側の能力として解決する。効果の self は使う側のまま、event.subject も使う側に差し替える（第261弾の use_entry_abilities と同型）。コピーされる能力の `if` は使う側の env で再判定する。trigger イベントの外で呼ばれた時や ability が無ければ何もしない。
- オルゲイトの形: `{kind: trigger, when: {event: trigger, subject: {owner: opp, filter: {types: [creature]}}}, if: {is_turn: opp}, effect: [may [use_triggered_ability]]}`。「相手のクリーチャーが出て」は発表条件（自身の出た時能力）が、「相手のターンに」は `if: {is_turn: opp}` が担う。複数ある出た時能力は能力ごとに trigger イベントが発表され、それぞれ別にコピーできる。
- Rust: _simple_when の _OK_EVENTS に "trigger" は無いため、この能力を持つカードを含む対局は Python にフォールバックする（第268弾のガチャと同じ扱い）。新しい GameState フィールドは無い（state.rs の変更なし）。
- **schema 取りこぼし（再発注意）**: 新しいイベント名・op は `python -m dmsim.cards.schema` の再生成が要る（第267弾の via 漏れ・第269弾のキーワード漏れと同型）。再生成は標準出力を `data/schema/card.schema.json` へリダイレクトで上書きすること。今回の差分は op `use_triggered_ability` 1件＋イベント enum への `"trigger"` 1行。
- **テストの罠**: コピーしたドローの直後に p1 のターン開始ドローが入るため、停止条件の手札枚数は「コピー1＋ターンドロー1」で数えること（p1 手札は 2 になる）。断った場合はターンドローのみの 1。攻撃ステップは攻撃可能なクリーチャーがいないと決定自体が出ない（第254弾の教訓）ため、「攻撃ステップに到達した」判定は seen_kinds に "attack" が出たことで見る。s.step は1決定遅れるので使わない。

- プロト T748–T752、tests/test_vocab_pilot270.py（8件）。

### ラウンド305（第270弾）

ability_copy の2件を処理: 新規1件（dm26sd1-a005 魔誕の斬将オルゲイト）＋ stale 除去1件（dm26sd1-n001）。a005 はハイパーエナジー（キーワードのみ）＋ブロッカー＋ジャストダイバー（dm22rp1-056 型の deny be_chosen/be_attacked until_next_own_turn_start）＋出た時の may バウンス＋相手ターンの相手 CIP のコピー（trigger イベント＋may＋use_triggered_ability。T749 型）。dm26sd1-n001 は原文コーパス外の ID のため raw 行が無く、ラウンド295で dm26ex4-cho005 として登録済み（aliases に n001 を含む）。reopen ability_copy で外れた2行のうち n001 は submit 対象外とし、cho005 の aliases に収まっていることを build_round305.py で照合して stale 除去とした（漏れではない）。converted 10,108 / rejects 2,227、重複0・漏れ0。ability_copy ギャップは残り0件でファミリー解消。tests/test_vocab_pilot270_cards.py（4件）＋tests/test_vocab_pilot270.py（8件）が通る。data audit 8件も通過。

- **テストの罠**: カード適用テストは conftest を import しないこと（DMSIM_SKIP_CONVERTED=1 が復活して登録形カードが読めなくなる）。第267–269弾の型どおり `os.environ.pop("DMSIM_SKIP_CONVERTED", None)` を dmsim import より前に置き、`_conv_cache`＋`dmsim.scenario.build` で直接組む。プロトテストとは別プロセスで実行する。

### ラウンド306（第271弾）

janken_opponent_hand の9件を処理: 新規登録7件＋stale 除去2件、差し戻し0件。対象の特定は rejects 行の text が空のため by_product の原文から行った（data/cards/raw/by_product/28・29・ex08・x22b.jsonl）。

- 新規7件: dm28-056 JK人形ボッコグー（activate tap: self＋勝ちで相手クリーチャーのパワー-3000＋パーで相手ハンデス）、dm28-060 JK野朗チョッキー（battle_start の trigger 2つ＋勝ちでパワー+5000＋グーで相手マナ→墓地）、dm29-035 JK兜 パッパラ・ベンケイ（partial の勝ち分岐にチョキ誘発を追加して完成）、dmex08-041 ＪＫパーネイチャー（dm28-103 の再録と同一能力）、dmex08-171 ＪＫヤミノグーデリアン（出た時ジャンケン＋勝ちで墓地からコスト5以下を出す＋パーで墓地からコスト4以下を手札へ）、dmex08-172 ＪＫ軍曹チョキパン（dm29-031 の再録と同一能力）、dmx22b-106 S・マネーキ（T755 と同一の battle_start 置換2つ＋グーで1ドロー）。
- stale 除去2件: dm28-103 と dm29-031 は同名の古い版で、canonical_rows の同名規則により原文行から外れている（submit は「原文に無いID」で弾く）。dmex08-041／dmex08-172 の aliases に既に収まっていることを照合して rejects から除去した（漏れではない）。dm28-103hc も dmex08-041 の aliases に収まる。
- reopen janken_opponent_hand は reason: vocab の dm29-035 の1行だけを外した（残り8行は reason が無く reopen 対象外。submit が登録時に rejects から外す）。
- converted 10,108 → 10,115 / rejects 2,227 → 2,218、重複0・漏れ0。janken_opponent_hand ギャップは残り0件でファミリー解消。tests/test_vocab_pilot271_cards.py（12件）＋tests/test_vocab_pilot271.py・test_data_audit・test_rules.py（計60件）が通る。

- **テストの罠（2件）**: (1) マナにはカードと同文明が最低1枚要る。火のカードに自然マナだけでは play 選択肢が出ない（T001×2 で dmex08-172 が出せなかった）。火は T011、闇は T008 を使うこと。(2) ターン終了まで残る modify（パワー+5000、-3000）は、バトル／起動型の効果解決直後にターンが終わると観測窓が無い。勝敗や破壊などの永続する結果で証明し、数値自体は登録形テストで検証すること（dm28-060 は相打ちにならないこと、dm28-056 は対象がパワー0以下で破壊されることで証明）。(3) 手の誘発は相手がその手を出した時にしか起きない。グー誘発のテストでは相手にグーを出させること（あいこになる組み合わせに注意）。

## 第271弾 janken_opponent_hand（相手とジャンケン＋相手の出した手への誘発）

共通文言: 「相手とジャンケンで勝敗を決める」＋「相手がジャンケンで「グー／チョキ／パー」を出した時」。対象は janken_opponent_hand ギャップの9件（ただし rejects 行の text が空のため、対象カードの特定はラウンド306で行う）。

- DM のジャンケンは「勝敗が決まるまでやって一回」で、あいこは勝敗が決まるまでやり直す（デュエル・マスターズ Wiki「ジャンケン」）。あいこの投で相手がその手を出しても誘発し、勝敗が決まってから溜まった分をまとめて解決する。そのため手の条項は分岐ではなく、ジャンケン1投ごとに発表される janken イベントを見る誘発型能力（when: {event: janken, opp_hand: rock|scissors|paper}）で表す。勝った側の効果が先に解決され、その後で溜まった手の誘発が解決される（603.3）。
- 新語彙: op **`janken`** の専用タスク化（第31弾の op 内二段 ask は不発だった: 1人目の答えが返った時点で h_effect が pc を進めて os を消し、相手の手を尋ねる前に終わって分岐が一度も走らない。第31弾のテストはターンのドローと区別できず見逃していた。既存の4枚のジャンケン能力はこの修正で初めて動くようになる）。op_janken は `_defer` で `janken` タスクを積む（`_push` だと h_effect が pc を進めず同じ op を繰り返す罠。第268弾のガチャと同型）。h_janken が両者の手を choose_one で尋ね、1投ごとに s.pub に kind: "janken"（hands: プレイヤー順の手、winner: 勝者・あいこは None、turn 付き）で公開記録してから ev_task でイベントを発表する。勝敗が決まれば勝敗分岐の子タスクを積み、あいこならその投のイベントだけ発表して、もう一度手を尋ねる。
- イベント **`janken`**（defs.EVENTS に追加。_apply_one の単純イベント allowlist にも追加）。when の **`opp_hand`**（rock/scissors/paper。相手＝この能力のコントローラーの対戦相手が出した手。events.py の _match_when で rec.hands[1 - env["you"]] と照合。defs.py の Checker と schema.py の when プロパティで enum 検証）。
- `draw` 分岐の削除: あいこに「あいこという判定」は無いので draw 分岐は死に語彙。opvocab.py の janken から `draw` を外し、書くと検証で弾かれる（DefError）。既存の4枚は draw を使っていない。
- **エンジンバグ修正（第271弾で発見）**: `_record_for`（events.py）は move/draw のレコードしか作らず、それ以外は None を返していたため、`_replacement` は battle_start の replace を一度も諮問していなかった（バトルが普通に起きて両方破壊され、ジャンケンが発火しない）。修正: `_record_for` が battle_start には `dict(ev)` を返す（_apply_one の単純イベントと同じ扱い）。break は `_break_candidates` の別経路があるため含めない（入れると二重諮問になる）。lose/battle の replace も別経路の inline 参照があるため含めない。converted には battle_start の replace は無く（trigger のみ32件）、既存カードへの影響は無い。
- Rust: 新しい GameState フィールドは無い（state.rs の変更なし）。Rust は event "janken"・when の opp_hand・op janken を知らないため、この能力を持つカードを含む対局は Python にフォールバックする（_simple_when が janken/opp_hand を False とする。第268弾のガチャと同型）。
- **schema 取りこぼし（再発注意）**: 新しいイベント名・op は `python -m dmsim.cards.schema` の再生成が要る（第267弾の via 漏れ・第269弾のキーワード漏れと同型）。再生成は標準出力を `data/schema/card.schema.json` へリダイレクトで上書きすること。今回の差分は op janken からの `draw` 削除＋イベント enum への `"janken"` 1行＋when の `opp_hand` enum。
- **テストの罠**: (1) バトルの後始末は決定を挟まず進むため、停止はターン2のチャージで初めて観測される。e.s.turn でのターン1証明はできない — ジャンケンの公開記録の `turn` フィールドで見ること（test_janken_battle_replace_attacker_wins）。(2) クリーチャーはタップ状態のものしか攻撃できない。守備側のクリーチャーをフィクスチャでタップしても、攻撃側のターン開始時のアンタップ（st_start はアクティブ・プレイヤーの bz をアンタップする）で戻される。攻撃する側のターンのチャージ決定時にタップし直すこと（第230弾の遅延タップ。今回はチャージ決定時にタップするので、攻撃ステップの選択肢は最初からタップ済みで作られる）。(3) 攻撃決定の罠（第230弾の仕組みの解明）: `eng.ask` は答えをターンタスクに蓄え、次の `advance()` で st_attack が再実行されて選択肢を再計算してから答えのインデックスを消費する。決定の提示と消費の間に状態が変わると、古い選択肢のインデックスが新しい選択肢の別項目を指す（第230弾は「pass」のインデックス1が、タップ後に挿入された攻撃先選択肢を指すことで成立していた）。インデックス依存のテストは避け、キーで選ぶこと。(4) ギアは `play:<defn>` でジェネレートし、その後のメインで `cross:<gear>:<host>` の選択肢が出る。`generate:<defn>` というキーは出ない。
- プロト T753–T757、tests/test_vocab_pilot271.py（12件）。回帰: クロスギア第224/225/241/252弾、バトル／攻撃第229/230/238/251/254/259/262/264弾、test_data_audit、test_rules.py — 149件通過。

## 第272弾 infinite_power / infinite_breaker（無限のパワー／ブレイク）

共通文言: 「∞ パワーアタッカー（攻撃中、このクリーチャーのパワーは無限大になる）」「∞ブレイカー（相手のシールドを好きな数ブレイクする）」「このターン、そのクリーチャーのパワーを－∞する」。対象は infinite_power 5件・infinite_breaker 5件（重なり dmex08-216）の9枚。無限大は 1<<30 の整数で表す（G・ブレイカーの break count 1<<30 と同型）。

- 新語彙は3つ。(1) キーワード **`infinite_breaker`**（abilities: [] の印だけ。g_breaker と同型）: combat の攻撃フェイズ4で、キーワードを持つ攻撃クリーチャーのブレイク数選択肢を 0..残シールド数にする。G・ブレイカー（"all"＋自壊）とは別物。ワールド・ブレイカー（breaks: 99＝全ブレイク強制）とも別物で、こちらは好きな数を選べる。(2) キーワード **`infinite_power_attacker`**: 常在型 mod `power_when: {amount: 1073741824, when: attacking}`（パワーアタッカー+N の power_when と同型。攻撃中の特性パワーが∞になり、バトル比較だけでなく攻撃中のパワー参照にも効く）。(3) mod **`power_set`**: 「パワーをXにする」置換。chars 計算の最後に置換値の最小を適用し、加算・ダイナモ・リンク統合のすべてを上書きする。defs.MOD_KEYS＋schema.py の mod プロパティ＋Checker.mod の整数検証を追加し、`python3 -m dmsim.cards.schema` で card.schema.json を再生成した。
- 「バトル中、パワーを∞にする」（dm26rp2-s011 の条項）は新語彙なしで mod `battle_power: {amount: 1073741824}`（only 無し＝攻守両方）で表せる。ただし同カードは trigger_when_opponent_plays_without_paying ギャップも持つ複合のため、ラウンド307ではそちらに差し戻し、バトル条項は partial に残す。
- **エンジンバグ修正（第272弾で発見）**: `_mod_nonneg`（events.py）が power_set を知らず「パワーを下げない」と判定していたため、パワー－∞の継続的効果がある盤面で SBA の高速経路が「パワー>0」と誤って断定し、破壊を省いてしまっていた（DMSIM_CHECK=1 の assert で発覚。本番でも同じ誤りになる）。修正: power_set を含む mod は False を返す。
- Rust: 新しい GameState フィールドは無い（state.rs の変更なし）。Rust は infinite_breaker / infinite_power_attacker を _OK_KW に持たず、power_set の modify も _simple_effect が弾くため、この能力を持つカードを含む対局は Python にフォールバックする（ガチャ・trigger と同型）。
- **テストの罠**: (1) ブレイク解決と次のターンのドローは同じ advance で観測される。ブレイク後の手札枚数は「ブレイク数＋ターンドロー1」で数えること（第270弾のコピー＋ターンドローと同型）。(2) T760 のようにキーワード（ブロッカー）と誘発を併せ持つプロトでは abilities[0] がキーワード展開の常在型になる。能力の特定は kind で絞ること。(3) choose_breaker の既定回答（最大値）は第271弾ドライバの流用では max を選ぶ。特定の数を選ぶテストは breaker 台本を渡すこと。
- プロト T758–T763、tests/test_vocab_pilot272.py（9件）。回帰: G・ブレイカー第252弾、バトル／攻撃第229/230/238/251/254/259/262/264弾、ジャンケン第271弾、test_data_audit、test_rules.py、test_file_schemas.py、test_rust_schema_sync、test_rustcore — 116件通過（13 skipped）。登録形カードテスト（第252/271弾）15件も別プロセスで通過。

### ラウンド307（第272弾）

infinite_power ギャップ5件・infinite_breaker ギャップ5件（重なり dmex08-216）の9件を処理: 新規登録5件＋差し戻し3件＋手つかず1件。reopen infinite_power infinite_breaker は純粋な5行（dm26ex3-079、dmr10-015、dm26ex3-054、dmex08-216、dmsp02-009）だけを外した。

- 新規5件: dm26ex3-079 帝王坂∞（CIP の「相手は自身の手札を5枚選び捨てる」は chooser: opp の discard、攻撃時のパワー－∞は power_set: -1073741824。partial には両能力とも欠落していたため原文から構築）、dmr10-015 無限の銃刃 ダン・クローリー（キーワード infinite_breaker のみ）、dm26ex3-054 帝王坂∞＜…………！＞（CIP パワー－∞は T760 と同型。印刷パワーも∞のため power: 1073741824 を補った — 登録直後は power 欠落で 0 として SBA に破壊される状態だった）、dmex08-216 アルティメット無法伝説（grant [infinite_power_attacker, infinite_breaker] を既存の gain と同一 modify に統合。T761 と同型）、dmsp02-009 武闘将軍 カツキング GS（キーワード infinite_power_attacker を追加）。
- 差し戻し3件（解けた条項は partial に bank）: dm26rp2-s011 V頂神話 カツムゲン → 「バトル中パワー∞」を battle_power {amount: 1073741824} で bank し、残りは trigger_when_opponent_plays_without_paying と、バトル中分から分離した新ギャップ **deck_faceup_power**（山札で表向きの間のパワー∞。デッキ内カードの特性パワーを読む仕組みが無い）。dm26rp3-td001 ∞龍 ゲンムエンペラー・dmart26-002 → ∞ブレイカーをキーワードで bank し、残りは ignore_abilities のみ。
- 手つかず1件: dm25bd2-007 極限の精霊インフィニティ・シリウス — partial が無く、コスト・パワーとも印刷∞（infinite_cost_power そのもの）で placeholder 値を置けないため、ギャップ [infinite_cost_power, infinite_breaker] のまま残した。
- **submit のテキスト由来マージに注意**: dm26ex3-079 は submit が原文由来の CIP discard を自前 partial の能力と重複登録した（同一誘発が2件）。登録後に同一 dict の重複を1件除去した。partial に能力が既にあるカードは submit 後の abilities 件数を必ず数えること。
- **付随するデータ修復（別コミット）**: dm26ex4-054（精霊龍 ライトマスターズ／龍素解析）の旧登録に dm26ex3-054 の text・keywords・aliases が混入していた。公式データに基づき text を自身のものに差し替え、keywords と aliases を除去し、aliases は dm26ex3-054 側に登録した。
- converted 10,115 → 10,120 / rejects 2,218 → 2,213、重複0・漏れ0。tests/test_vocab_pilot272_cards.py（7件）＋test_data_audit（8件）が通る。

## 第273弾 evolution_base_any（進化元を問わない扱い: 許可の肩代わりを race_has / any_of へ拡張）

ギャップ名 evolution_base_any の純粋4件（dmex08-137 無頼剣兵ドラグイノセント / dmex16-014 未来王龍 モモキング / dmx21-062 無垢の宝剣 / dmx22a-041 コマンダー・イノセント）。第232弾で実装した許可アクション **evolve_base_any** とギャップ名がずれていたため、ラウンド268の対象にならず残っていた。

- 本人の形は既存語彙: {kind: static, affects: self, mod: {allow: [evolve_base_any]}}。ただし第232弾の `_evo_match` の肩代わりは evolve_from が {races} 形の時だけで、進化側の要求として多い {civs, race_has} 形（converted の evolve_from に race_has は約195箇所）や any_of の種族枝には許可が及ばず、文面どおり「どの種族の進化クリーチャーでも置ける」になっていなかった。
- **拡張（turn.py `_evo_match`）**: 肩代わりを `_evo_race_waived` として一般化した。種族指定（races / race_has）を取り除いた残りを filter_match で照合する。any_of は枝ごとに再帰し、枝の外にあるキーも各枝へ合わせて見る。文明・タイプなど種族以外の指定は従来どおり肩代わりしない（第232弾の設計を維持）。なお {races, civs} の複合フィルタは converted に存在しないため、この厳密化で既存カードの挙動は変わらない。
- 残りの条項も既存語彙で足りる: dmex16-014 の「このクリーチャーから進化する進化クリーチャーの召喚コストを1少なくする」は第234弾の mod **evo_reduce** {amount: 1}（下限は既定の0）。dmex08-137 の破壊時「ドラゴンを1体、自分の手札からバトルゾーンに出してもよい」は trigger {event: move, from: bz, to: graveyard, reason: destroy, subject: self} ＋ may [play_free] の既存形。partial の text は4枚とも切り詰められているので、ラウンド308では reject 行の原文で置き換えること。
- Rust: 新規フィールド・op・enum は無し（スキーマ再生成不要、state.rs 変更なし）。許可を持つ進化元が絡む照合は Python 側で従来どおり。
- **テストの罠**: 支払ったマナのタップ観測は、進化クリーチャーが場に出た瞬間に止めて行うこと。汎用ドライバを回し続けるとターンを跨いでアンタップされ、支払済みのマナが起きた状態で観測される（本弾の evo_reduce テストで踏んだ）。
- プロト T764–T769、tests/test_vocab_pilot273.py（9件）＋ tests/test_vocab_pilot273_cards.py（3件: 対象4枚の提出形が unsupported 無しで parse できることと未登録チェック）。回帰: 第232/234弾（本体＋登録形）、第218/231/235/265/266弾、test_data_audit、test_rules.py — 合計107件通過。

### ラウンド308（第273弾）

evolution_base_any の純粋4件を処理: 新規登録4件、差し戻し0件。reopen evolution_base_any は対象4行（dmex08-137、dmex16-014、dmx21-062、dmx22a-041）だけを外した。

- 新規4件: dmex08-137 無頼剣兵ドラグイノセント（allow [evolve_base_any] ＋破壊時にドラゴンを手札から出す誘発）、dmex16-014 未来王龍 モモキング（allow ＋ evo_reduce {amount: 1}、キーワード speed_attacker / double_breaker は partial 由来のまま）、dmx21-062 無垢の宝剣（allow のみ）、dmx22a-041 コマンダー・イノセント（allow のみ、キーワード blocker / cannot_attack は partial 由来のまま）。
- 4枚とも partial の text が切り詰められていたため、登録形の text は reject 行の公式全文に差し替えた（登録形テストで全文一致を検証）。
- dmex08-137 の破壊時誘発は第273弾の提出形どおり play_free で登録。submit の lint（「出す」なら move put 形を推奨）は助言のみで、converted には play_free 形の「手札から出してもよい」が多数あるため提出形を維持した。
- converted 10,120 → 10,124 / rejects 2,213 → 2,209、重複0・漏れ0。tests/test_vocab_pilot273_cards.py を登録形に書き換え（4件: 登録形の検証＋登録カードでの evo_reduce / any_of 肩代わり / 破壊時誘発の挙動）＋test_data_audit（8件）＋第273弾本体（9件）が通る。

## 第274弾 soulshift（クラシック・ソウルシフト: 既存 soul_shift {floor} の単体進化への適用＋実現可能性見積もりの修正）

ギャップ名 soulshift の純粋4件（dmx10-035 白騎士の聖霊王ウルファス / dmx11-050 真実の大神秘 星飯 / dmx12b-056 宇宙巨匠ゼノン・ダヴィンチ / dmx22a-013 超電磁マクスウェル Z）。いずれも通常の単体進化クリーチャーで、ソウルシフト（召喚する時、進化元クリーチャーを選ぶ。その選んだクリーチャーのコストだけコストが少なくなる）が唯一の未対応条項。

- 第218弾の面フィールド **soul_shift {floor}** はソウルシフト∞（超無限進化: 重ねた進化元全員の合計ぶん軽減）として実装されたが、支払い側（h_play）は「実際に重ねた進化元の合計」で計算するため、単体進化では合計＝選んだ1体のコストとなり、クラシック形の意味と一致する。新規語彙は不要で、floor の対応は「1より少なくならない」→ {floor: 1}（035/050/056）、「0以下にならない」→ {floor: 0}（013）。
- **エンジン修正（turn.py `_can_play_face`）**: 実現可能性の見積もりが候補全体の合計で軽減を見積もっており、単体進化では払えない額を提示して出せる扱いにしてしまう（例: 本体コスト7・候補コスト5と3・マナ1 → 旧見積もりは 7−8→床1 で提示、実際は最良の元でも 7−5=2 で払えない）。evolve_any（∞）の時は候補全体の合計のまま、そうでない時は「重ねる数（通常1体）ぶんを大きい順」の合計で見積もるよう修正。converted で soul_shift を持つ2面はいずれも evolve_any: true のため、既存カードの挙動は変わらない。
- 支払いの観測上の注意: 有色カードは軽減でコスト0になっても 112.2b（コストが文明数を下回れば文明の支払いを優先）により文明数ぶんのマナをタップする（第218弾の無支払い証明が無色プロトだったのはこのため）。本弾は T771（水・floor 0）でこの相互作用も固定した。
- Rust: 新規フィールド・op・enum は無し（スキーマ再生成不要、state.rs 変更なし）。soul_shift は従来どおり Python 側で処理される。
- プロト T770–T775、tests/test_vocab_pilot274.py（8件: parse＋進化元なし soul_shift の検証エラー、選んだ進化元のコストぶん軽減、小さい元を選ぶと高くなる、floor 1 のクランプ、floor 0 の無色無支払い／有色の文明数支払い、実現可能性の提示／不提示）＋ tests/test_vocab_pilot274_cards.py（1件: 対象4枚の partial＋soul_shift が unsupported 無しで parse できることと未登録チェック）。回帰: 第218/232/234/236/265/273弾本体＋test_data_audit — 合計46件通過。
- ラウンド309側の注意: dmx11-050 の partial には「自分よりパワーの小さいクリーチャーにブロックされない」能力が、dmx22a-013 の partial には W・ブレイカーと「各プレイヤーは自身の墓地にある呪文と同じ文明を持つ呪文を唱えられない」が欠けている（text も切り詰め）。dmx12b-056 の partial の evolve_from は {types: [creature]} で、原文の「ジャイアント、ドリームメイト、オリジンいずれか」とずれている。登録形は reject 行の原文から補うこと。

### ラウンド309（第274弾）

soulshift の純粋4件を処理: 新規登録4件、差し戻し0件。reopen soulshift は対象4行（dmx10-035、dmx11-050、dmx12b-056、dmx22a-013）だけを外した。

- 新規4件: dmx10-035 白騎士の聖霊王ウルファス（soul_shift {floor: 1}、partial は完全で追加のみ。aliases dm32-071 / dm32-071hc）、dmx11-050 真実の大神秘 星飯（{floor: 1}）、dmx12b-056 宇宙巨匠ゼノン・ダヴィンチ（{floor: 1}、alias dm32-009）、dmx22a-013 超電磁マクスウェル Z（{floor: 0}、aliases dm32-017 / dmx10-020）。alias はいずれも canonical 側の source.aliases に畳まれ、alias id の reject 行は元々無かったため stale 整理は無し。
- partial の欠落・ずれは reject 行の公式全文から補った（第274弾の注意どおり）: dmx11-050 には「このクリーチャーよりパワーの小さいクリーチャーにブロックされない」を deny be_blocked の other フィルタ {power_le: {sum: [{power_of: self}, -1]}} で追加（permits の _other_filter が self 基準で式を先評価する）。dmx12b-056 は evolve_from を {any_of: [ジャイアント, ドリームメイト, オリジン]}（種族枝）に修正し、partial に丸ごと欠けていた破壊時誘発「自分の進化クリーチャーが破壊された時、進化ではないジャイアント/ドリームメイト/オリジンのいずれか1体をマナゾーンからバトルゾーンに出してもよい」を trigger {event: move, from: bz, to: graveyard, reason: destroy, subject: {owner: you, filter: {types: [evolution]}}} ＋ play_free {zone: mana, filter: {types: [creature], evolution: false, any_of: 種族枝}, up_to: true} で追加（自身が破壊された時も誘発することをバトル破壊で検証）。dmx22a-013 は text を公式全文に差し替え、W・ブレイカー（keywords 欠落）と呪文ロックを追加。呪文ロック「各プレイヤーは自身の墓地にある呪文と同じ文明を持つ呪文を唱えられない」は、文明×（自分/相手）の計10枚の常在型 {affects: {owner, zone: hand, filter: {types: [spell], civs: [C]}}, if: {exists: {zone: [graveyard], owner, filter: {types: [spell], civs: [C]}}}, mod: {deny: [cast]}} で表した（多色呪文は各文明で判定、無色呪文は文明を持たないため対象外）。
- converted 10,124 → 10,128 / rejects 2,209 → 2,205、重複0・漏れ0。tests/test_vocab_pilot274_cards.py を登録形に書き換え（10件: 登録形の検証＋035/050 のソウルシフト実支払い、050 のブロック可否（パワー3000 不可・同11000 可）、056 の破壊時誘発（他者破壊・自身のバトル破壊）、013 の呪文ロック（自分側・相手側・対照2件））＋test_data_audit（8件）が通る。
- テストの罠: build() のメイン決定は「出せるカードが無い」と現れない（pass のみのメインはスキップされる）。相手側ロックの検証は、相手の手札に唱えられる別カードを入れてメイン決定自体を出現させてから対象呪文の不在を見ること。T407（ACEタマシード）は素ではクリーチャーとして扱われずブロッカーにならない。同パワーのブロッカー役には登録済みカードを使うのが確実。

## 第275弾 attack_specific_target（選んだ特定のクリーチャーへの攻撃許可: allow 項目の only）

ギャップ名 attack_specific_target の純粋4件のうち3件は同一形: 「相手のタップされていない（アンタップしている）クリーチャーを1体選ぶ。このターン、自分のクリーチャーはすべて、そのクリーチャーを攻撃できる」（dmr09-102 戦場のロックンロール＝呪文形 / dmr14-050 爆旗持ち ラガブーリン＝CIP形）。dmrp06-080 ポリスワン は CIP形の変種で、付与先が「自分の他のクリーチャー」（発生源を除く）。残る dmrp08-058 ホンヤクツーヤク は「このクリーチャーが攻撃する時、可能ならパワー2222以下のクリーチャーを攻撃する」という攻撃強制のフィルタ形で、本弾の対象外（must_attack_creature に other フィルタを持たせる別ギャップとして残す）。

- 新語彙: allow / deny 項目の新キー **only: {var: 名前}**。choose で対象を束縛し、modify で {allow: [{action: attack_creature, other: {tapped: false}, only: {var: tgt}}]} を自分のクリーチャー全員（count: all）に duration: end_of_turn で与える。only は「その項目が当たる対象」を選んだカードだけに絞る修飾で、マッハファイター形（other: {tapped: false} のみ、無条件）は従来どおり。
- 実装: defs.py の allow/deny 項目検証に only を追加（値は {var: 文字列} のみ）。op_modify に **_bake_only** を追加し、only を生成時点の束縛参照列へベイクする（_bake_refs の {var:} は束縛した枚数を返す数式のため、参照そのものは別経路で焼く。焼く前の _bake_refs より先に処理する）。照合は core._only_ok に集約し、combat._attack_options のアンタップ攻撃可否と core.permits の hit の両方で使う。未ベイク（常在型に書かれた場合など）・対象なしでは当たらない。
- dmrp06-080 の「他の」は modify の select に exclude: {ref: self} を付けて表す（既存セレクタ機能）。
- Rust: modify の mod {allow: [...]} は _simple_effect の単純形に含まれないため、この形を持つカードを含む対局は Python にフォールバックする。新規フィールド・op・enum は無し（スキーマ再生成で差分なし、state.rs 変更なし）。
- プロト T776–T779、tests/test_vocab_pilot275.py（8件: parse、only の検証エラー形、非 rust-simple、対照＝付与なしでは攻撃不可、呪文形の付与＋実際にバトル、次ターン失効、CIP全員形、CIP他者形の exclude＋ベイク確認）＋ tests/test_vocab_pilot275_cards.py（対象3枚の登録形が unsupported 無しで parse できること）。回帰: 第251/254/264/271/272/274弾＋test_rules＋test_data_audit＋test_rust_schema_sync＋攻撃系 — 合計121件通過。
- ラウンド310側の注意: 対象3枚の partial は abilities を一切含まない（効果全体が unsupported 側にある）ため、登録形は reject 行の公式全文から組み立てること。dmr09-102 は呪文面（spell: キー）、dmr14-050 / dmrp06-080 は {event: move, to: bz, subject: self} の CIP 誘発。dmrp08-058 は本弾では登録しない（差し戻し時はギャップ名を精緻化すること）。

### ラウンド310（第275弾）

attack_specific_target の4件を処理: 新規登録3件、差し戻し1件。reopen attack_specific_target は対象4行（dmr09-102、dmr14-050、dmrp06-080、dmrp08-058）だけを外した。3枚の partial は abilities を一切含まないため、登録形は reject 行の公式全文から組み立て、text も公式全文に差し替えた。

- 新規3件: dmr09-102 戦場のロックンロール（呪文面 spell: に choose＋modify）、dmr14-050 爆旗持ち ラガブーリン（CIP {event: move, to: bz, subject: self}）、dmrp06-080 ポリスワン（CIP変種、modify の select に exclude {ref: self}）。いずれも choose {zone: bz, owner: opp, filter: {types: [creature], tapped: false}, count: 1} as: tgt → modify {select: 自分のクリーチャー全員, mod: {allow: [{action: attack_creature, other: {tapped: false}, only: {var: tgt}}]}, duration: end_of_turn} の形。alias の畳み込み・stale 整理は無し。
- 差し戻し1件: dmrp08-058 ホンヤクツーヤク は攻撃強制のフィルタ形で本弾の対象外。ギャップ名を **must_attack_filtered_target**（must_attack_creature に other フィルタ＝パワー2222以下を持たせる形）に精緻化し、partial（公式全文＋unsupported）に残した。
- converted 10,128 → 10,131 / rejects 2,205 → 2,202、重複0・漏れ0。attack_specific_target ギャップは残り0件でファミリー解消。tests/test_vocab_pilot275_cards.py を登録形に書き換え（5件: 登録形の検証、dmrp08-058 の差し戻し確認、呪文形・CIP全員形の実バトル、CIP他者形の exclude＋ベイク確認）＋test_data_audit（8件）が通る。

## 第276弾 grant_duration（ターン境界を越える付与期間: duration 2値＋相手ターン中のみのイディオム）

ギャップ名 grant_duration の純粋4件（dmex18-s11 地龍神バラフィオル / dmr05-078 ビックリ・ガード / dmr22-006 ジャッジメント・タイム / dmrp19-032 †正義†と「正義」）。4件とも不足は期間の指定だけで、付与そのものの形（modify の grant / deny / no_leave）は既存だった。

- **新 duration 2値**（defs.py DURATIONS_FIXED＋スキーマ再生成）: **until_next_own_turn_end**（次の自分のターンの終わりまで。dmex18-s11）と **until_next_opp_turn_end**（次の相手のターンの終わりまで。dmr22-006）。生成時に core._duration が **until_turn_end:{player}:{生成ターン}** へ解決し、turn.py の新設 **_expire_turn_end** が st_end（511.2、end_of_turn の直後）とターンの残りをとばす経路で、そのプレイヤーの生成より後のターンの終了時に落とす。生成がそのプレイヤーのターン中なら次のそのプレイヤーのターン、相手のターン中なら直後のそのプレイヤーのターンが期限（追加ターンもそのプレイヤーのターンとして数える）。プレイヤー基準の解決なので追加ターンでもずれない。
- dmr05-078 の「次の自分のターンのはじめまで」は既存の **until_next_own_turn_start** で足りることを本弾で検証した（modify の付与でも until_turn_start:{you} に解決され、次の自分のターンの開始時に切れる）。
- dmrp19-032 の「次の相手のターン中のみ」は固定 duration では表せない（自分のターン中に唱えた場合、そのターン中は効かないのが原文）。**イディオム**: 呪文の解決時に delayed_trigger {when: {event: turn_start, player: opp}, duration: permanent} を登録し、相手のターン開始時に modify {mod: {no_leave: true}, duration: end_of_turn} を発火させる。自分のターン中は継続的効果自体が存在しないため、S・トリガー等で除去されうるという原文の挙動と一致する。
- dmr22-006 の「アンタップしない」は deny の **untap_at_start**（既存。常在型での使用例が converted にある）、「攻撃もブロックもできない」は deny [attack_player, attack_creature, block] の既存形。ロックは唱えた時点から効く（そのターンの相手のブロックも禁止される）。
- Rust: modify の duration が end_of_turn でない形は _simple_effect の単純形に含まれないため Python フォールバック。新規 GameState フィールドは無し（state.rs 変更なし）。解決済み duration は continuous / delayed のエントリ内文字列のみ。
- **テストの罠**: バトルや破壊の後始末は決定を挟まず次のターンへ進むため、観測は次のターンの最初の決定で行い、生成ターンの証明は e.s.turn ではなく解決済み duration の生成ターン欄で読むこと（第271弾の教訓の再確認）。相手ターンに攻撃決定が現れないこと自体が deny の証明になる場合は、失効後のターンに攻撃決定が戻ることも併せて見る。
- プロト T780–T784、tests/test_vocab_pilot276.py（8件: parse、duration 検証、非 rust-simple、次の自分のターンの終わりまでの窓（呪文形・相手ターンに破壊される誘発形）、次の相手のターンの終わりまでのロック（アンタップ・攻撃・失効後の回復）、until_next_own_turn_start の失効、次の相手のターン中のみの窓（バトル生存と失効後の破壊））＋ tests/test_vocab_pilot276_cards.py（5件: 対象4件の未登録確認と各条項の提出形 parse）。回帰: 第188/245/254/264/271/272/275弾（本体＋cards）＋test_data_audit＋test_rules＋test_rust_schema_sync＋test_file_schemas — 合計145件通過・1件スキップ（test_file_schemas は jsonschema 未導入のため丸ごとスキップ、既存条件）。
- ラウンド311側の注意: dmex18-s11 の partial は abilities が壊れており（無関係な誘発が1つだけ残る）、text も公式全文だが登録形は全文から組むこと（マッハファイター＋Q・ブレイカー、ドラゴンが相手プレイヤーを攻撃する時の誘発＝上から3枚を見てドラゴンを出して残りを底へ、破壊時誘発＝本弾の形）。dmr22-006 の partial は abilities 空・text 切り詰め。残りの条項（光のコスト4以下の呪文を手札から無料で唱えてもよい／唱えた後、墓地のかわりに山札の一番下に置く）は reject 行の公式全文から組むこと。dmr05-078 の partial は spell 空（呪文面を本弾の形で組む）。dmrp19-032 の partial はシンパシーの常在型まで完全で、呪文面にイディオムを載せるだけ。

### ラウンド311（第276弾）

grant_duration の純粋4件をすべて新規登録、差し戻しなし。reopen grant_duration は対象4行（dmex18-s11、dmr05-078、dmr22-006、dmrp19-032）だけを外した。alias の畳み込み・stale 整理は無し。

- 新規4件: dmex18-s11 地龍神バラフィオル（partial の abilities はマッハファイター展開形のみ＝キーワードパターンの展開と同形だったためそのまま残し、攻撃誘発と破壊時誘発を公式全文から組んだ。攻撃誘発は {event: attack, target: player, subject: {owner: you, filter: {types: [creature], race_has: ドラゴン}}} → choose {from_top: 3, look: true, count: all, reveal: true} as: pile → may [play_free {ref: pile, ドラゴン, count: 1}] → move {ref: pile, to: deck, position: bottom, order: choose}。play_free の lint 警告（出す＝move/put の示唆）が出たが、「見た中から出す」は dm26ex2-046（ラウンド279）の登録形が play_free で先例化しているためそれに合わせた。破壊時誘発は本弾の形＝modify grant [world_breaker] を until_next_own_turn_end）。dmr05-078 ビックリ・ガード（呪文面が空だったため本弾検証形＝grant [blocker] を until_next_own_turn_start で組んだ）。dmr22-006 ジャッジメント・タイム（partial は abilities 空・text 切り詰め。ロック＝deny [attack_player, attack_creature, block, untap_at_start] を until_next_opp_turn_end、光のコスト4以下の呪文の無償詠唱＝may [play_free {zone: hand, filter: {types: [spell], civs: [light], cost_le: 4}}]、唱えた後の山札下行き＝{kind: replace, zone: hold, when: {event: move, to: graveyard, reason: resolve, subject: self}, instead: [move {ref: self, to: deck, position: bottom, reason: return}]}。マナゾーンに置く時タップして置くは多色カードの一般則のため面項目なし）。dmrp19-032 †正義†と「正義」（partial のシンパシー常在型はそのまま、呪文面に本弾の delayed_trigger イディオムを載せた）。
- converted 10,131 → 10,135 / rejects 2,202 → 2,198、重複0・漏れ0。grant_duration ギャップは残り0件でファミリー解消。tests/test_vocab_pilot276_cards.py を登録形に書き換え（6件: 登録形の検証、s11 の攻撃誘発でドラゴンを出す・破壊時付与の窓、078 の付与失効、006 のロック＋無償詠唱＋山札下行き、p19 イディオムの窓）＋test_data_audit（8件）が通る。テストの罠: T006（パワー4000以下破壊）ではパワー22000 の s11 を破壊できない — 破壊役は T056（無制限破壊）を使うこと。build の deck_size は両プレイヤー共通で、相手の山札も初期配布（シールド5＋手札5）に足りる大きさが要る。

## 第277弾 true_escape（真・エスケープ）

ギャップ名 true_escape の純粋3件（dm23rp2x-010 アウルーリー-T8 / dm24bd5-004 聖霊妖精オーデマリー / dm24rp1-011 獲銀月 ミール）。3件とも不足はキーワード「真・エスケープ」だけで、置換の機構は既存の escape（破壊時のみ・シールド1枚）と eternal_omega（離れる時全般・強制）の先例で実証済みだった。

- **新キーワード true_escape**（data/rules/keywords.yaml、エンジンのコードは変更なし）: {kind: replace, optional: true, when: {event: move, from: bz, subject: self}, if: {cmp: [{count: {zone: shield, owner: you}}, ">=", 2]}, instead: [move {select: {zone: shield, owner: you, count: 2}, to: hand, reason: return, strigger: "off"}]}。when は eternal_omega と同じ「離れる時」全般（行き先・理由を問わない）。if は escape の exists（1枚以上）では「2枚払える」ことを表せないため cmp/count で2枚以上にゲートする（1枚しか無い時に諮問して選ばせると支払えない置換になる）。instead は escape と同形で、加えたシールドは strigger: "off" の印により「S・トリガー」を使えない。
- dm23rp2x-010 の追加条項「自分のシールドがなければ、このクリーチャーは離れない」はキーワードの外で、既存の mod **no_leave** を常在型の if でゲートする形 {kind: static, affects: self, if: {not: {exists: {zone: shield, owner: you}}}, mod: {no_leave: true}} で表せる（プロト T786 で検証）。境界は原文どおり: シールド1枚では no_leave が切れるが真・エスケープも払えず通常どおり離れる。
- dm24rp1-011 の真・エスケープはハイパー時のみ。**mod grant は置換能力を届けない**（abilities() が展開するのは印刷キーワードと mod.gain のみ）ため、キーワード本体を mod.gain で {hyper: true} ゲートした常在型で載せる（第240弾の静的 gain 展開が経路。提出形は cards テストで parse 検証済み）。
- **同時離脱の観測（エンジン構造）**: 複数枚が同時に離れる効果（全体破壊など）では、置換の諮問は全件ぶんが instead の支払いより先に済む（capture 相。escape 等の既存置換と共通）。したがって if の枚数判定は諮問時点の枚数で読まれる。逐次処理と結果が一致する範囲（2体・シールド5枚→1枚）でテストし、それを超える同時離脱の重なりはキーワード側ではなく置換機構全体の性質として記録に留める。
- **テストの罠**: 呪文解決から次の決定までの間にターン境界を越えるため、手札枚数の内訳には次の自分のターンのドローが混ざる（第271弾の教訓どおり、内訳を明記して数える）。攻撃側にクリーチャーがいないと攻撃ステップの決定自体が現れず、停止点は次のターンのチャージ決定になる。
- Rust: true_escape は _OK_KW になく置換も _simple_replace が弾く（escape と同じ）ため Python フォールバック。新規 GameState フィールドは無し（state.rs 変更なし）。スキーマはキーワード enum の追加で再生成した。
- プロト T785–T786、tests/test_vocab_pilot277.py（13件: parse・未知キーワード拒否、非 rust-simple、破壊置換、支払いシールドの S・トリガー不可、辞退、バウンス置換、バトル敗北置換、シールド1枚・0枚では諮問なし、全体破壊2体、no_leave の0枚ブロック・1枚境界・シールドありでの諮問）＋ tests/test_vocab_pilot277_cards.py（4件: 対象3件の未登録確認と各提出形 parse）。回帰: 第230/240/244/266/272/276弾（本体）＋named_effects＋strigger_mark＋test_data_audit＋test_rules＋test_rust_schema_sync＋test_file_schemas で 126 passed / 1 skipped（file_schemas は jsonschema 未導入のため丸ごとスキップ、既存条件）、cards 側（第230/266/272/276弾 cards＋本弾 cards）で 34 passed。
- ラウンド312側の注意: dm23rp2x-010 の partial はキーワードのみで abilities 空 — T786 と同形（キーワード追加＋no_leave 常在型）で組む。alias は dm23rp2-010 / promoy22-019。dm24bd5-004 の partial は abilities 空 — 出た時・攻撃する時の「上から2枚を見て1枚をシールド化・残りを手札」は choose {from_top: 2, look: true, count: all} as: pile → move {ref: pile, count: 1, to: shield, reason: put} → move {ref: pile, count: all, to: hand, reason: draw} を2つの誘発に載せ、シールドゾーンのスノーフェアリーへの S・トリガー付与は常在型 {affects: {zone: shield, owner: you, filter: {race_has: スノーフェアリー}}, mod: {grant: [s_trigger]}}（dm24ex1-001 の先例形）。alias は promoy24-037。dm24rp1-011 は partial のハイパー静的が完全なため、mod.gain の常在型を1つ足すだけ。alias は dm24rp1-sec13。

### ラウンド312（第277弾）

true_escape の純粋3件をすべて新規登録、差し戻しなし。reopen true_escape は対象3行（dm23rp2x-010、dm24bd5-004、dm24rp1-011）だけを外した。3件とも partial の text は公式全文と同一だったため差し替えなし。

- 新規3件: dm23rp2x-010 アウルーリー-T8（partial はキーワードのみ。true_escape をキーワードに追加し、「自分のシールドがなければ、このクリーチャーは離れない」を no_leave 常在型 {affects: self, if: {not: {exists: {zone: shield, owner: you}}}, mod: {no_leave: true}} で組んだ。プロト T786 と同形。alias: dm23rp2-010 / promoy22-019 は canonical の source.aliases に畳み込み）。dm24bd5-004 聖霊妖精オーデマリー（partial は abilities 空。出た時・攻撃する時の誘発＝choose {from_top: 2, look: true, count: all} as: pile → move {ref: pile, count: 1, to: shield, reason: put} → move {ref: pile, count: all, to: hand, reason: draw} を2誘発に載せ、シールドゾーンのスノーフェアリーすべてへの S・トリガー付与＝常在型 {affects: {zone: shield, owner: you, filter: {race_has: スノーフェアリー}}, mod: {grant: [s_trigger]}} を公式全文から組んだ。alias: promoy24-037）。dm24rp1-011 獲銀月 ミール（partial のハイパー静的は完全なためそのまま。真・エスケープはハイパー時のみで mod grant では置換が届かないため、キーワード本体を mod.gain で {hyper: true} ゲートした常在型を1つ追加した。alias: dm24rp1-sec13）。
- converted 10,135 → 10,138 / rejects 2,198 → 2,195、重複0・漏れ0（alias 側の stale 行10件は従来分で本ラウンド無関係）。true_escape ギャップは残り0件でファミリー解消。tests/test_vocab_pilot277_cards.py を登録形に書き換え（6件: 登録形の検証、010 の破壊置換・シールド0枚での no_leave、004 の出た時誘発＋シールドゾーン付与、011 のハイパー時置換・非ハイパー時不発）＋test_data_audit（8件）が通る。テストの罠: build の山札はシャッフルされるため 004 の上から2枚は defn でなく実体（cid）で追うこと（filler と同名だと zone 内カウントが崩れる）。置換の支払い choose（シールド2枚）にも T001 が並ぶため、対象選択フックは選択肢がすべて bz の時だけ応じること。ハイパー解放のコストでタップした味方は、停止点が次の自分のターン開始を越えるとアンタップ済みで検証できない。

## 第278弾 filter_race_and（種族の AND フィルタ races_all）

ギャップ名 filter_race_and の純粋3件（dm23ex3-t13 黒神龍オンバシ・ラオーン / dm23ex3-t01 極頂秘伝ゼニス・シンフォニー / dm24bd6-023 「武」の頂 マキシマム・ザ・マックス）。3件とも不足は「アンノウンとゼニス両方を種族に持つ」という種族の AND 条件だけで、既存の races（OR）・race_has（部分一致の OR）では表せなかった。文明には同じ非対称があり civs（OR）に対して civs_all（第24弾）があるため、その種族版を足すのが最小の語彙になる。

- **新フィルタキー races_all**（defs.py の FILTER_KEYS に追加、selectors.py の filter_match に `set(races_all) <= set(ch["races"])` を civs_all と同形で追加。文字列が来た場合は civs の _civ_list と同じく単一種族として正規化）。値の式化は civs_all と同じく不可（FILTER_EXPR_KEYS に入れない）。種族は split_races で「/」分割された正確な種族名のリストとして保持されるため、部分一致ではなく完全一致の集合包含で判定する（race_has の部分一致とは別物）。他のフィルタキーとの積み重ねは通常の AND として働く。
- スキーマは filter キー enum の差分（3箇所に races_all）だけで再生成した。新規 GameState フィールドなし（state.rs 変更なし）。when の subject フィルタは parse_card のキー検証対象外（既存の性質）で、submit 時は再生成済みスキーマが受ける。
- **テストの罠**: (1) ゼロ文明のカードはゼロ文明のマナでしか支払えない（_mana_choices の need は civs そのもので、T001 の自然マナでは play 選択肢自体が出ない）。試験では T788/T789 をマナ役にした。(2) 相手ターン内の誘発観測にドローを使うと自分の次のターンのドローと数え分けられない（召喚の解決とターン境界が同じ回答の中で進む）。T790 の効果はマナブーストにしてマナ枚数で観測した。(3) 呪文の解決中は自分の決定が現れないことがある（候補1体の select は自動決定、残りステップに決定なし）ため、T791 の召喚観測は攻撃決定が現れるよう初期配置に T001 を置き、advance のたびに答える前に場を見て記録した。
- プロト T787–T791、tests/test_vocab_pilot278.py（8件: parse・未知キー拒否（検証位置では弾く）、filter_match の意味論（両種族のみ一致・片方指定・文字列正規化・OR との対照・他キーとの AND）、監視獣の誘発（両種族で発火・片方で不発・相手のでは不発）、召喚呪文（両種族だけが出る・終了時に手札へ戻る・両種族なしでは何も出ない））＋ tests/test_vocab_pilot278_cards.py（4件: 対象3件の未登録確認と各提出形 parse）。
- ラウンド313側の注意: dm23ex3-t13 の partial の常在型は壊れている（race_has に文章が入った軽減 -2 が1件だけ）。実際は「アンノウンの召喚コスト -1」「ゼニスの召喚コスト -2」の2件で、フィルタは races の OR 形で足りる（アンノウンとゼニス両方を持つクリーチャーは両方の軽減を受ける。原文どおり）。誘発は subject {owner: you, filter: {types: [creature], races_all: [アンノウン, ゼニス]}} → destroy {ref: self}。自身の種族はドラゴン・ゾンビ／アンノイズで対象外のため自己誘発しない。alias: dmr05-055 / dmr05-055m / dmx13-023。dm23ex3-t01 は呪文面に play_free {select: {zone: hand, owner: you, filter: {types: [creature], races_all}, count: 1}, as: summoned} ＋ delayed_trigger {when: {event: turn_end}, effect: [move {ref: summoned, to: hand, reason: return}]} を載せるだけ（T791 で実挙動検証済み。play_free の「てもよい」の辞退可否はラウンド側で select の min を確認すること）。alias: dmbd06-012。dm24bd6-023 はツインパクトでクリーチャー面は partial のまま、呪文面に t01 と同じ形を載せる。alias: dm22ex1-043。

### ラウンド313（第278弾）

filter_race_and の純粋3件をすべて新規登録、差し戻しなし。reopen filter_race_and は対象3行（dm23ex3-t13、dm23ex3-t01、dm24bd6-023）だけを外した（alias 行は rejects に無く巻き込みなし）。3件とも partial の text が公式全文（t13/t01 は行テキストと内容同一、bd6 は両面を結合した全文）のため差し替えなし。

- 新規3件: dm23ex3-t13 黒神龍オンバシ・ラオーン（partial の常在型は壊れていたため、コスト軽減2件＝{affects: {owner: you, zone: hand, filter: {types: [creature], races: [アンノウン]}}, mod: {cost: -1}} と {races: [ゼニス], cost: -2}、誘発＝{when: {event: move, to: bz, subject: {owner: you, filter: {types: [creature], races_all: [アンノウン, ゼニス]}}}, effect: [destroy {ref: self}]} を公式全文から組み直した。下限0はエンジン既定（core の pay_cost は cost_min 既定0で max を取る）ため cost_min は付けない。alias: dmr05-055 / dmr05-055m / dmx13-023）。dm23ex3-t01 極頂秘伝ゼニス・シンフォニー（declare は partial のまま。呪文面＝play_free {select: {zone: hand, owner: you, filter: {types: [creature], races_all}, count: 1, up_to: true}, as: summoned} ＋ delayed_trigger {when: {event: turn_end}, effect: [move {ref: summoned, to: hand, reason: return}]}。**辞退可否の確認結果: select の count: 1 は mn=mx=1 で候補があると強制になるため、「てもよい」には up_to: true が必要**（selectors.select の mn 決定。dmrp18-034 の先例形。辞退時は summoned が空束縛になり終了時の戻しは空振りする）。alias: dmbd06-012）。dm24bd6-023 「武」の頂 マキシマム・ザ・マックス（ツインパクト。クリーチャー面は partial のまま、呪文面に t01 と同じ形。alias: dm22ex1-043）。
- **submit の abilities 連結（重要）**: submit は partial の abilities と回答の abilities を連結する（同一 dict は重複排除される。t01 の declare は同一だったため重複しなかった）。t13 は壊れた partial の常在型が回答の3件に加えて残ったため、ラウンド307（dm26ex3-079）の先例どおり converted.yaml から直接除去して修正した（除去後の登録形・実効コストを再検証済み）。partial に abilities が残るカードを「組み直し」で提出する時は、登録後に abilities の件数と内容を必ず照合すること。
- converted 10,138 → 10,141 / rejects 2,195 → 2,192、重複0・漏れ0。filter_race_and ギャップは残り0件でファミリー解消。tests/test_vocab_pilot278_cards.py を登録形に書き換え（7件: 登録形の検証（連結で残った壊れ常在型が無いことの断言を含む）、t13 の実効コスト（両種族0 / アンノウン2 / ゼニス1）、t13 の自己破壊誘発と片種族での不発、t01 の召喚→終了時戻しと辞退、bd6 呪文面の召喚→戻し）＋test_data_audit（8件）が通る。テストの罠: build の決定種別は charge → main → attack と分かれており、相手ターンの開始検出は main でなく player で見ること（相手に main 決定が出ないと停止条件が永遠に来ず山札切れで game ended になる）。

## 第279弾 alt_cost_mana_civilization_condition（マナゾーンの各文明を条件とする代替コスト）

ギャップ名 alt_cost_mana_civilization_condition の純粋4件（dm25ex3-054 ～破壊と殺戮の連鎖～（光・水・闇）/ dm25ex3-057 大集合！アカネ&アサギ&コハク（光・水・自然）/ dm25ex3-062 哀蛇の虚 シンロッチ（闇・火・自然）/ dm25ex3-060 トレース＝トレーシー（水・闇・火））。4件とも同形で「自分のマナゾーンに（3文明）の各文明があれば、このクリーチャーを[cc02]支払って召喚してもよい」＋NEO進化。partial は他の条項まで完成しており、不足は代替コストの条件だけだった。

- **新語彙なしのイディオム確立弾**（第247/255/276弾と同型）。条件は既存の alt_cost.if に cond の `all` ＋ `exists {zone: mana, owner: you, filter: {civs: [文明]}}` の3連を載せる: `alt_cost: {cost: 2, civs: [], if: {all: [...]}}`。alt_cost.if は defs 検証（chk.cond）と turn.py の選択肢生成（eval_cond で条件成立時のみ :alt を提示）の両方に配線済みで、converted に13件の先例がある（dm24rp2-059 の exists 形、dm22rp1-018 等の cmp 形）。eval_cond は all/any と exists（candidates）を実装済み。多色マナ1枚はその各文明について exists を満たす（多色カードは各文明を持つという公式ルールどおりで、3文明マナ1枚だけでも条件が成立することをテストで確認した）。エンジン変更なし・スキーマ再生成なし（cond の all/exists と alt_cost.if はスキーマ登録済み）。新規 GameState フィールドなし。
- **[cc02] の支払い文明は civs: [] が正表現**。bazurenda [cc02] の登録先例（dm23bd6-015 / dm24bd5-046 / dmrp14-045 等）がすべて `civs: []`。partial の `civs: [zero, zero]` は変換側の誤記で、そのまま提出すると _mana_choices の need が「ゼロ文明のマナ2枚でしか払えない」意味になる。実測の裏付け: civs [zero] の登録済みカード dm24bd2-016（コスト2）は自然マナ2枚では play 選択肢自体が出ず、無色マナを置いた時のみ出た（civs [] の dmd10-008 は色マナで出る）。ラウンド314は civs: [] に直して提出すること。
- **既知の制限（本弾の対象外）**: NEO進化と代替コストの併用選択肢（:neo:alt）は生成されない。free_if と NEO の併用（dm25rp2-068 魔誕獣ヤミノストライク等の登録済みカード）でも同じで、エンジン全体の既存性質。:neo は通常コストで重ね、:alt は重ねない通常召喚として働く（T792 で両方を実挙動確認済み）。
- プロト T792、tests/test_vocab_pilot279.py（10件: parse・提出形検証と未知 cond キー拒否、選択肢生成＝3文明そろえば :alt・闇不足で不発・多色1枚で2文明を兼ねる・3文明マナ1枚で成立し通常召喚は不可・相手のマナは数えない、実挙動＝:alt は2枚タップ・通常は3枚タップ・:neo は通常コストで重なる）＋ tests/test_vocab_pilot279_cards.py（3件: 対象4件の未登録確認、partial の [zero, zero] 誤記の固定、各提出形 parse）。
- ラウンド314側の注意: 対象4行すべてが解放される。提出形は partial の alt_cost を本弾の形（cost: 2, civs: [], if は自カードの civs 3つぶんの exists）に差し替えるだけ。alias: dm25ex3-054 → dm25rp4-049、dm25ex3-057 → dm25rp4-050 / promoy25-120、dm25ex3-062 → dm25rp4-053、dm25ex3-060 → dm25rp4-052。dm25ex3-062 の攻撃時誘発は原文「上から2枚を表向きにする」だが partial の choose は look: true のみ（reveal: true の要否をラウンド側で確認）。submit は partial の abilities と回答の abilities を連結する（第313弾の教訓）ため、登録後に abilities の件数・内容とキーワードをテキストと照合すること。4件とも text は partial が公式全文のため差し替え不要。

### ラウンド314（第279弾）

alt_cost_mana_civilization_condition の純粋4件をすべて新規登録、差し戻しなし。reopen alt_cost_mana_civilization_condition は対象4行（dm25ex3-054、dm25ex3-057、dm25ex3-062、dm25ex3-060）だけを外した（alias 行の巻き込みなし）。4件とも text は partial が公式全文のため差し替えなし。

- 新規4件: dm25ex3-054 ～破壊と殺戮の連鎖～（光・水・闇、alias: dm25rp4-049）/ dm25ex3-057 大集合！アカネ&アサギ&コハク（光・水・自然、alias: dm25rp4-050 / promoy25-120）/ dm25ex3-062 哀蛇の虚 シンロッチ（闇・火・自然、alias: dm25rp4-053）/ dm25ex3-060 トレース＝トレーシー（水・闇・火、alias: dm25rp4-052）。いずれも partial の alt_cost を本弾の形（cost: 2, civs: [], if: {all: [exists {zone: mana, owner: you, filter: {civs: [自カードの文明]}} ×3]}）に差し替えただけ。他の条項は partial のまま。
- **dm25ex3-062 の reveal 判定: 必要**。原文は「自分の山札の上から2枚を表向きにする」で、choose の reveal: true がまさに「表向きにする」の公開形（ops の docstring 明記。束縛カードを全プレイヤーに公開し s.pub に reveal 記録が残る）。partial の look: true（自分だけが見る）は「見る」と書く dm25ex3-057 の形であり、062 では不正確なため、最初の choose から look を外し op に reveal: true を付けた（dm23rp1-071 の登録先例形）。登録形テストで reveal の公開記録（viewers [0, 1]）が上2枚ぶん残ることまで実挙動で確認した。なお dm21-013 等の旧登録には「表向きにする」でも look のみの形が残っているが、本ラウンドでは触らない。
- submit 後の照合（第313弾の教訓）: 4件とも登録形の abilities・キーワード・alt_cost・text が回答と完全一致（partial 残存なし）。4件ともキーワード能力は無し（NEO進化は neo/evolve_from 項目）。
- converted 10,141 → 10,145 / rejects 2,192 → 2,188、重複0・漏れ0。alt_cost_mana_civilization_condition ギャップは残り0件でファミリー解消。tests/test_vocab_pilot279_cards.py を登録形に書き換え（7件: 登録形の完全一致検証、054 の :alt 提示/不提示と2枚タップ＋CIP シールド化、057 の CIP（見て1枚手札・残りを底）、062 の攻撃時誘発（表向き＋1体手札・残り墓地）、060 の CIP（1枚墓地＋墓地から回収））＋test_data_audit（8件）が通る。テストの罠: 攻撃宣言は main と別の attack 決定で提示されるため、ドライバの play フックは attack 決定にも掛けること（main だけ見ると攻撃できず山札切れで game ended になる）。

## 第280弾 battle_does_not_occur_when_blocked（ブロックされた場合、バトルは行われない）

ギャップ名 battle_does_not_occur_when_blocked の純粋3件（dm06-032 ピーカプ・リザード / dm06-101 無謀鉄人チョイヤ / dm19-s02 護法の精霊アムシオン）。dm06 の2件は同文（パワーアタッカー＋「このクリーチャーの攻撃がブロックされた場合、バトルは行われない。ただし、両クリーチャーはタップしたままである」）で、partial はパワーアタッカー誘発まで完成し不足はこの条項だけ。dm19-s02 は partial に abilities が無く、第2条項（任意形）に加えて第1条項「バトルゾーンにある自分の、タップされているクリーチャーのパワーは、攻撃していない時、+7000される」の「攻撃していない時」条件も未表現だった。

- **イディオム（強制形）**: 誘発 {when: {event: block, attacker: self}, effect: [{op: cancel_attack}]}。when の attacker 照合は既存（dm08-033 シェル・コロシアムが「このクリーチャーがブロックされたとき」に attacker: self を使用）、cancel_attack は第251弾の op（攻撃宣言時誘発の窓で使う想定だったが、ブロック誘発の窓でも攻撃タスクはスタック上にあり、h_attack は再開時に cancelled を phase 分岐より先に見るため同じく効く）。ブロック宣言時点で両クリーチャーはタップ済みで、cancel 後は attack_end（blocked: true）だけが出てバトルもブレイクも起きないため、原文「両クリーチャーはタップしたままである」まで一致する。ガードマンはブロックではない（507.2b）ので block イベント自体が出ず、このイディオムは発火しない（バトルは通常どおり）。
- **イディオム（任意・第三者形、dm19-s02）**: 誘発 {when: {event: block, attacker: {owner: you}}, effect: [may [cancel_attack]]}。「自分のクリーチャーがブロックされた時、その攻撃を中止してもよい」。attacker の {owner: you} は _ref_match → _subject_match の既存形で、相手のクリーチャーがブロックされても発火しないことをテストで確認した。
- **拡張: mod power_when に when: not_attacking を追加**（「攻撃していない時」）。変更は defs.py の検証、dmsim/cards/schema.py の enum、core._power_when の3箇所＋スキーマ再生成（enum の差分のみ）。意味論は attacking の否定: 進行中の攻撃の攻撃クリーチャーでない間ずっと付く（ブロック中・攻撃されている間・どの攻撃も無い間を含む）。攻撃クリーチャー自身はタップしていても付かない。dm19-s02 の第1条項は常在型 {affects: {zone: bz, owner: you, filter: {tapped: true}}, mod: {power_when: {amount: 7000, when: not_attacking}}} で表す。新規 GameState フィールドなし（state.rs 変更なし）。
- プロト T793–T795（T793 = dm06-101 の形、T794 = dm06-032 の形、T795 = dm19-s02 の形そのもの）、tests/test_vocab_pilot280.py（12件: parse・検証（not_attacking 受理と defending 等の拒否、両イディオム形の parse）、強制形＝弱い攻撃側がブロックされても両者タップのまま残る／強い攻撃側でもブロッカーが破壊されない、ブロックされなければ通常ブレイク、クリーチャーへの直接攻撃は通常バトル、任意形＝中止を選べば両者残る・断ればバトルが行われ攻撃側は +7000 無しで負ける・相手の攻撃側では誘発しない、not_attacking＝タップした味方だけ +7000・攻撃中は付かない・防御バトルで 9000 になって勝つ（対照あり））＋ tests/test_vocab_pilot280_cards.py（2件: 対象3件の未登録・ギャップ純粋確認、partial＋本弾条項の提出形 parse）。回帰: 第251弾本体＋test_muse_quality＋test_rules＋test_rust_schema_sync 70件、test_data_audit 8件が通る。
- ラウンド315側の注意: 対象3行すべてが解放される。dm06-032 / dm06-101 は partial に本弾の誘発を1つ足すだけ（text は partial が公式全文）。dm19-s02 は partial に abilities が無いため、本弾の常在型＋誘発を公式全文から構築して足す（text は partial のものが公式全文）。3件とも alias は rejects 行に無い見込みだが、提出前に id・カード名とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること。submit は partial の abilities と回答を連結する（第313弾の教訓）ため、登録後に abilities の件数・内容とキーワードをテキストと照合すること。

### ラウンド315（第280弾）battle_does_not_occur_when_blocked

純粋3件をすべて新規登録、差し戻し0件。converted 10,145 → **10,148** / rejects 2,188 → **2,185**、canonical overlap 0・漏れ 0（reopen は対象3行のみを外し、巻き込みなし）。3件とも alias は無く stale 整理なし。ファミリー残り0件で解消。

- **dm06-032 ピーカプ・リザード / dm06-101 無謀鉄人チョイヤ**: partial に block 誘発 {when: {event: block, attacker: self}, effect: [{op: cancel_attack}]}（強制形イディオム）を追加して提出。**post-submit 修正あり**: submit がテキスト由来のパワーアタッカー常在型 {kind: static, affects: self, mod: {power_when: {amount, when: attacking}}} を加え、partial のパワーアタッカー誘発（攻撃時 modify +3000/+1000）と二重適用になる形で登録された。登録済み256件のパワーアタッカーで「常在型＋同一額の誘発 modify」の重複はこの2件だけで、他は常在型のみ（165件）か誘発は別効果。converted.yaml を直接編集して誘発側を除去し常在型に一本化（第307弾 dm26ex3-079・第313弾の先例どおり）、source.notes も追随させた。登録形テストでブロック決定時点の攻撃側パワー 2000（+1000 一回だけ）まで実挙動確認済み。**教訓: submit は partial と回答の連結に加えて、テキスト由来のキーワード能力（パワーアタッカー等）を常在型として加えることがある — 登録後の abilities 照合は回答との一致ではなくテキストとの一致で見ること。**
- **dm19-s02 護法の精霊アムシオン**: partial は abilities を持たないため、常在型 {affects: {zone: bz, owner: you, filter: {tapped: true}}, mod: {power_when: {amount: 7000, when: not_attacking}}}＋ block 誘発 {when: {event: block, attacker: {owner: you}}, effect: [may [cancel_attack]]}（任意・第三者形）を公式全文から構築。登録形は回答と完全一致（partial 残存なし）。
- テスト: tests/test_vocab_pilot280_cards.py を登録形に書き換え **5 passed**（登録形の完全一致、101 のブロック中止＋パワー一本化、032 の非ブロック時ブレイク、s02 の not_attacking 常在型と任意中止の受諾）。test_data_audit **8 passed**。旧テストに対象 id の bounce 断言は無し。回答下書き: ~/workspace/DMPJ-work/answers/round315.yaml。

## 第281弾 leave_replacement_shield_to_hand（自分のクリーチャーが離れる時、かわりにシールドを手札に戻す）

ギャップ名 leave_replacement_shield_to_hand の純粋3件（dm23ex3-tf03 「終焉」の頂 オーエン・ザ・ロード / dm24ex4-042 星姫械 エルナドンナ / dmx23-025 若き日の族長 ヘンザ）。3件とも不足は「自分のクリーチャーが離れる時、かわりに自分のシールドをNつ手札に戻してもよい。ただし、その『S・トリガー』は使えない」という置換条項だけで、発生源が自分自身ではなくバトルゾーンの他のクリーチャーにも及ぶ点が escape（破壊時のみ・自分・1枚）や第277弾 true_escape（離れる時全般・自分・2枚）と異なる。置換の機構そのものは両先例で実証済みで、events._replacement の候補走査は発生源プレイヤーの bz_tops 全体を見るため、発生源と動くカードが別でも諮問される。本弾は新語彙・エンジン変更なしのイディオム弾。

- **基本形（tf03 / ヘンザ）**: {kind: replace, optional: true, when: {event: move, from: bz, subject: {owner: you, filter: {types: [creature]}}}, if: {cmp: [{count: {zone: shield, owner: you}}, ">=", 2]}, instead: [{op: move, select: {zone: shield, owner: you, count: 2}, to: hand, reason: return, strigger: "off"}]}。subject の dict 形は _subject_match の既存形で、自分を含む「自分のクリーチャー」全般を指す（filter の types: [creature] でクリーチャー以外が離れる時は発火しない）。行き先・理由は問わない（true_escape と同じ「離れる時」全般）。if は true_escape と同じ cmp/count ゲートで、2枚払える時だけ諮問する。instead は escape / true_escape と同形（reason: return、strigger: "off" で「その『S・トリガー』は使えない」）。
- **他者・各ターン一度形（dm24ex4-042）**: subject に other: true（_subject_match の「自分以外」）を足し、once_per_turn: true（置換側の対応は第196弾。印は選ばれた時に付き、辞退では消費しない）、枚数は1枚で if は >= 1。「自分の他のクリーチャーが離れる時」に発生源自身は守れない。
- 同時離脱（全体破壊）では置換の諮問が全件ぶん instead の支払いより先に済む（capture 相。第277弾の観察と同じエンジン構造）ため、if の枚数判定は諮問時点の枚数で読まれる。プロトの範囲（発生源＋味方1体・シールド5枚）では逐次処理と結果は一致する。
- Rust: どちらの形も optional（エルナドンナ形は once_per_turn も）を含むため _simple_replace の対象外（escape / true_escape と同じ）で、この能力を持つカードを含む対局は Python にフォールバックする。新規 GameState フィールドなし（state.rs 変更なし）。スキーマ再生成なし（when の subject は parse_card のキー検証対象外＝第278弾の確認どおり）。
- プロト T796–T797（T796 = 基本形そのもの、T797 = 他者・各ターン一度形そのもの）、tests/test_vocab_pilot281.py（13件: parse・両形の dict 一致、非 rust-simple、基本形＝味方の破壊置換／自身の破壊置換／辞退／バウンス置換／相手のクリーチャーは守らない／シールド1枚では諮問なし／支払ったシールドの S・トリガー不可／全体破壊で両方残る、他者形＝味方を1枚で置換／自身は守らない／各ターン一度で2体目は諮問なし）＋ tests/test_vocab_pilot281_cards.py（2件: 対象3件の未登録・ギャップ純粋確認、partial＋本弾条項の提出形 parse）。回帰: 第277弾本体＋第196弾本体＋test_rules＋test_rust_schema_sync 61件、test_data_audit 8件が通る。
- ラウンド316側の注意: 対象3行すべてが解放される。**dm23ex3-tf03 の partial には出た時の能力（自分の墓地のカードをすべて山札に加えてシャッフルする。その後、自分の山札の上から3枚をシールド化してもよい）が丸ごと欠けている**（unsupported にも無い）ため、置換条項の追加に加えてこの出た時能力を公式全文から構築すること。dm24ex4-042 は abilities 空で、ブロッカー＋他者形の置換だけを足す。dmx23-025 は partial の革命チェンジ（declare＋swap）に基本形の置換を足すだけ。alias は tf03 → dmbd06-001、dm24ex4-042 → dm23rp4-012 / dm23rp4x-012 / dm24ex4-pr002（提出前に id・alias・カード名とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること）。submit は partial の abilities と回答を連結する（第313弾の教訓）ため、登録後に abilities の件数・内容とキーワードをテキストと照合すること。
- 関連する単独行 dm26rp3-001 ヒトリダチ ケントナーク（ギャップ名 once_per_turn_leave_replacement_shield_to_hand）も同じ形で表せる（subject の filter に race_has: ジョーカーズ、once_per_turn: true、1枚）。ただし partial に出た時のモード能力（▶シールド化／▶Jビッグ1）が丸ごと欠けているため、本弾の対象には含めなかった。ラウンド316で併せて取る場合は、出た時能力を公式全文から構築し、reopen に両ギャップ名を指定すること。

### ラウンド316（第281弾）

leave_replacement_shield_to_hand の純粋3件＋関連単独行 dm26rp3-001 をすべて新規登録、差し戻し0件。converted 10,148 → 10,152 / rejects 2,185 → 2,181、canonical overlap 0・漏れ 0。両ギャップ名とも残り0件で解消。reopen は両ギャップ名を指定し、対象4行だけが外れた（巻き込みなし）。提出前の照合（real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml、id・alias・カード名とも）は proto.yaml の T796/T797 の text 内参照のみで重複なし。

- **dm23ex3-tf03 「終焉」の頂 オーエン・ザ・ロード**: 基本形の置換に加え、partial に丸ごと欠けていた出た時能力を公式全文から構築: 誘発 {when: {event: move, to: bz, subject: self, reason: summon}（第92弾の「召喚によって出た時」）→ move {zone: graveyard, owner: you, count: all} to: deck, reason: return ＋ shuffle {player: you}（dmex12-056 先例形）＋ may [move {zone: deck, from_top: 3} to: shield, reason: charge]（シールド化は「その後…してもよい」だけが任意なので may はシールド化のみに掛ける。シールド化の move 形は dm23ex3-tr06 先例）}。alias dmbd06-001 は canonical の source.aliases に畳み込み（rejects に alias 行なし）。
- **dm24ex4-042 星姫械 エルナドンナ**: abilities 空の partial にブロッカー（キーワードは partial のまま）＋他者・各ターン一度形の置換を追加。alias 3件（dm23rp4-012 / dm23rp4x-012 / dm24ex4-pr002）はすべて畳み込み。
- **dmx23-025 若き日の族長 ヘンザ**: partial の革命チェンジ（declare＋swap）に基本形の置換を追加しただけ。alias なし。
- **dm26rp3-001 ヒトリダチ ケントナーク（併せて取得）**: partial に丸ごと欠けていた出た時のモード能力を公式全文から構築: modal のモード1 = シールド化（move {zone: deck, from_top: 1} to: shield, reason: charge）、モード2 = Jビッグ1（op use_cip {select: {zone: bz, owner: you, other: true, count: 1, filter: {race_has: ジョーカーズ}}}、dm26rp3-077 の登録先例形そのまま）。置換は各ターンに1度形で、subject の filter は原文「自分のジョーカーズ」にクリーチャー限定が無いため race_has: ジョーカーズ のみとし、types: [creature] は付けなかった（基本形・他者形の「クリーチャー」明記との対比）。公式の別印刷は無く alias なし。
- submit 後の照合（第313/315弾の教訓）: 4件とも登録形の abilities・キーワードをテキストと照合し、partial の連結残り・テキスト由来のキーワード常在型の追加は無いことを確認（cards テストの test_registered_forms が abilities の完全一致を固定）。
- テスト: tests/test_vocab_pilot281_cards.py を登録形に書き換え **10 passed in 49.84s**（登録形の完全一致、tf03 の召喚時 CIP＝墓地全回収＋シールド+3 と置換、042 の味方保護／自身は守らない、ヘンザの置換、rp3 の CIP シールド化モード／Jビッグモード＝dm26rp3-077 の能力でドロー、ジョーカーズのみ保護、各ターンに1度）。tests/test_data_audit.py **8 passed in 65.82s**。第281弾本体 13件も通過。旧テストに対象 id の bounce 断言は無し。回答下書き: ~/workspace/DMPJ-work/answers/round316.yaml。

## 第282弾 filter_same_name_as_event_card（イベントのカードと同じ名前のフィルタ）

ギャップ名 filter_same_name_as_event_card の純粋3件（c48-sec001 邪眼皇アレクサンドルIII世 / dm24ex3-rp1s10 巨進の超人 / dmrp02-006 サイバー・GG・ハルク）。3件とも不足は「イベントの対象カード（唱えた呪文／召喚によって出たクリーチャー／破壊されたクリーチャー）と同じ名前のカードを選ぶ」というフィルタ条件だけ。フィルタ値の式 {name_of: <参照>} は第140弾で導入済みで、dm23-005（ラウンド265）が {name: {name_of: event.subject}} の実戦先例（attack_unblocked の攻撃クリーチャー参照）。cast レコードは from（唱えた元のゾーン。第226弾）を保持し、when の from はリスト指定で「いずれか」に照合される（events._match_when）。本弾は新語彙・エンジン変更なしのイディオム弾で、残る3つのイベント文脈でも event.subject 参照がそのまま効くことを実挙動で固定した。

- **詠唱形（c48-sec001）**: 誘発 {when: {event: cast, player: you, from: [hand, graveyard], subject: {filter: {types: [spell], civs: [light, water, darkness]}}}, if: {exists: {zone: bz, owner: you, other: true, filter: {race_has: ナイト}}}, effect: [choose {zone: deck, look: true, count: all} as: pile → choose {ref: pile, filter: {name: {name_of: event.subject}, types: [spell]}, count: 1} as: found → if {exists: {ref: found}} then may [play_free {ref: found}] → move {ref: pile, count: all} to: deck → shuffle]}。「自分のナイトが他に1枚でもあれば」は exists の other: true（発生源自身を除く。candidates の既存形）で表す。見つけた呪文は pile（hold）から play_free で唱えるため、その cast の from は deck/hold になり、この誘発自体は再発火しない。手札から唱えた時・墓地から唱えた時（grave_cast）の両方で発火し、他のナイトがいない時は if で落ちて諮問自体が出ない。
- **召喚形（dm24ex3-rp1s10）**: 誘発 {once_per_turn: true, when: {event: move, to: bz, reason: summon, subject: {owner: you, other: true, filter: {types: [creature]}}}, effect: [may [play_free {select: {zone: mana, owner: you, filter: {name: {name_of: event.subject}, types: [creature]}, count: 1}}]]}。「召喚によって出た」は reason: summon の照合（第316弾 dm23ex3-tf03 の先例）。play_free は「出してもよい」の定形（第313弾の山札からの先例と同じく、置かれたゾーンを問わない）。
- **破壊形（dmrp02-006）**: 誘発 {when: {event: move, from: bz, to: graveyard, reason: destroy, subject: {owner: you, filter: {civs: [water], types: [creature]}}}, effect: [may [play_free {select: {zone: hand, owner: you, filter: {name: {name_of: event.subject}, types: [creature]}, count: 1}}]]}。破壊されたカードは墓地にあっても event.subject の参照先として名前を読める（発生源自身が破壊された場合も、待機した誘発から手札の同名を出せる）。同カードの第1誘発（自分の他の水のクリーチャーが出た時、1枚引く）は通常形 {event: move, to: bz, subject: {owner: you, other: true, filter: {civs: [water], types: [creature]}}} → draw。
- 観察: 山札検索の choose は候補が1枚だけだと決定が提示されず自動選択される（mn == mx の既存仕様）。詠唱形のテストでは「発火したか」を墓地の同名呪文の枚数と may 諮問の有無で判定した。
- Rust: 3形とも _simple_trigger の対象外（when の subject が dict 形／from リスト／once_per_turn／name_of 式フィルタ／play_free を含むため）で、この能力を持つカードを含む対局は Python にフォールバックする。新規 GameState フィールドなし（state.rs 変更なし）。スキーマ再生成なし（name_of は第140弾で式の語彙に登録済み。when の subject フィルタは parse_card のキー検証対象外＝第278弾の確認どおり）。
- プロト T798–T803（T798 = 詠唱形そのもの、T799 = 他のナイト役、T800 = 同名呪文（grave_cast つき・ドロー）、T801 = 召喚形そのもの、T802 = 同名の双子獣、T803 = 破壊形＋出た時ドローの dmrp02-006 そのもの）、tests/test_vocab_pilot282.py（13件: parse・EXPECTED 一致、未知フィルタキーの拒否、非 rust-simple、詠唱形＝手札から唱えて同名を無償詠唱／墓地から唱えても発火／他のナイトなしで不発／辞退で山札に戻る、召喚形＝同名をマナから出す／各ターン一度／相手の召喚で不発、破壊形＝自身が破壊されて手札の同名を出す／味方が出てドロー／水でない味方の破壊で不発）＋ tests/test_vocab_pilot282_cards.py（2件: 対象3件の未登録・ギャップ純粋確認、提出形 parse）。回帰: 第140弾＋第229弾（本体・cards）＋第281弾本体＋test_rules＋test_rust_schema_sync＋test_data_audit 73件が通る。
- ラウンド317側の注意: 対象3行すべてが解放される。**c48-sec001** は partial が abilities を持たないため詠唱形の誘発を足すだけ（キーワード double_breaker は partial のまま）。partial の notes に「29-sec001 と同一カードの別収録」とあるため、提出前に 29-sec001 の id・カード名も照合先に含めること。**dm24ex3-rp1s10** は partial の出た時能力（G・ストライク含む）はそのまま、召喚形の誘発を足すだけ。alias: dm24ex3-rp1tr08 / dm24rp1-s10 / dm24rp1-tr08。**dmrp02-006** は partial が空のため、公式データから全形を構築すること（サイバー・GG・ハルク、水、コスト7、パワー8000、種族サイバー・コマンド、キーワード blocker / double_breaker、誘発2つ＝T803 と同形、text は reject 行のもの）。submit は partial の abilities と回答を連結する（第313弾の教訓）ため、登録後に abilities の件数・内容とキーワードをテキストと照合すること。

### ラウンド317（第282弾）

filter_same_name_as_event_card の純粋3件のうち2件を新規登録、1件を差し戻し。converted 10,152 → 10,154 / rejects 2,181 → 2,179、canonical overlap 0・漏れ 0。filter_same_name_as_event_card は残り0件で解消。提出前の照合（real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml、id・alias・カード名とも）は proto.yaml の T798–T803 の text 内参照のみで重複なし。

- **dm24ex3-rp1s10 巨進の超人**: partial の出た時能力（G・ストライク含む）はそのまま、召喚形の誘発（T801 と同形）を追加して登録。alias 3件（dm24ex3-rp1tr08 / dm24rp1-s10 / dm24rp1-tr08）は canonical の source.aliases に畳み込み（rejects に alias 行なし）。
- **dmrp02-006 サイバー・GG・ハルク**: reject 行に partial が無いため、公式データ（水・コスト7・パワー8000・サイバー・コマンド）から全形を構築して登録: 出た時ドロー誘発＋破壊形の誘発（T803 と同形）、キーワード blocker / double_breaker。submit の play_free lint 警告（「出す」用途への示唆）は、第282弾で確立した「出してもよい」の定形として維持した。
- **c48-sec001 邪眼皇アレクサンドルIII世は差し戻し（ギャップ名を same_name_cast に精緻化）**: 本印刷の本文形は本弾の詠唱形イディオムで解決済みで、解けた形（T798 と同形）は partial の abilities に格納した。しかし submit が「取得済みの原文に無いID」で拒否した。原因は変換対象の絞り込み: convert_cards.load_rows は identity.canonical_rows で同一カードの古い印刷を落とすため、最新版でない印刷は submit の原文コーパスに存在しない。同一カードの最新版は **dm26ex4-cho010**（canon_id の向き先。29-sec001 / dm29-s03 / dmc48-001 も同じ最新版の alias）で、その本文は本印刷と異なる形（「選んだ呪文を１枚表向きにし、山札をシャッフルしてからその呪文をコストを支払わずに唱えてもよい」＝公開＋シャッフルが詠唱より前）であり、rejects に gaps [same_name_cast] で残存している。よって登録は same_name_cast 側（最新版）の変換で行い、その際に本行は alias として畳み込むのが正路。本行は reopen で外れていたため、行を復元したうえで gaps を [same_name_cast] に付け替え、partial の notes に経緯を記録した（submit 経由の差し戻しは ID 拒否のため不可能で、行の直接復元で対応）。**教訓: 対象行が同一カードの古い印刷でないか（canon_id が自 ID と異なるか）を submit 前に確認すること。異なる場合は、その行は登録対象ではなく、最新版の行が変換対象になる。**
- 既存の欠落（本ラウンドでは触らない）: 別印刷 29-sec001 / dm29-s03 / dmc48-001 は converted に本誘発を欠いた形（キーワードのみ）で登録済み。いずれも「原文が同じ他印刷の変換結果を写した」初期の登録で、最新版 dm26ex4-cho010 の変換時に併せて是正するのが望ましい。
- submit 後の照合（第313/315弾の教訓）: 登録2件とも登録形の abilities・キーワードをテキストと照合し、partial の連結残り・テキスト由来のキーワード常在型の追加は無いことを確認（cards テストの test_registered_forms が abilities の完全一致を固定）。
- テスト: tests/test_vocab_pilot282_cards.py を登録形に書き換え **5 passed in 36.63s**（登録形の完全一致、c48 の差し戻し確認＝gaps [same_name_cast]・解けた形の格納・最新版行の残存、rp1s10 の召喚形＝マナの同名 T802 が出る、rp02-006 の出た時ドローと破壊形＝手札の同名が出て破壊分は墓地に残る）。tests/test_data_audit.py **8 passed in 62.71s**。旧テストに対象 id の bounce 断言は無し。テスト中の発見: 多色カード（T030＝光/水）の支払いには各文明のマナがすべて要るため、支払い fixture には光と水の両方を用意すること。回答下書き: ~/workspace/DMPJ-work/answers/round317.yaml。

## 第283弾 eternal_kappa（エターナル・Κ）

ギャップ名 eternal_kappa の8件（dm23ex3-or1 クリス=タブラ=ラーサ / dm23ex3-s06 「使命」の頂天 グレイテスト・グレート / dm23ex3-027 「怪異」の頂天 クリス=ベルゼ / dm24bd6-002 「祝福」の頂天 ウェディング / dm24bd6-011 「無上」の頂天 シャングリラ・ファンタジア / dm24bd6-024 「異形」の頂天 クリス=ゼ=ブブ / dm24rp3-td01 「呪怨」の頂天 サスペンス / dm24sp2-003 「戦鬼」の頂天 ベートーベン）。共通条項は「エターナル・Κ（このクリーチャーが離れる時、かわりに自分のマナゾーンにある裏向きのカードを３枚、表向きにしてもよい）」で、dm23ex3-or1 だけが「または自分がゲームに負ける時」も含む変形（クリスターナル・Κ）。8件とも他のギャップを併せ持つため、本弾は eternal_kappa 条項の語彙・イディオム確立が目的で、ラウンド318で対象行が解放される見込みは低い（下記の注意を参照）。

- **新キーワード eternal_kappa**（data/rules/keywords.yaml、エンジンのコードは変更なし）: {kind: replace, optional: true, when: {event: move, from: bz, subject: self}, if: {cmp: [{count: {zone: mana, owner: you, filter: {face_down: true}}}, ">=", 3]}, instead: [flip_up {select: {zone: mana, owner: you, filter: {face_down: true}, count: 3}}]}。when は true_escape（第277弾）と同じ「離れる時」全般（行き先・理由を問わない）。if は true_escape と同じ cmp/count ゲートで、裏向きマナが3枚ある時だけ諮問する（count＋filter の形は第23弾の FD2 が先例）。instead の支払いは「マナゾーンの裏向きカードを表向きにする」既存 op **flip_up** の流用（第148弾。docstring に「エターナル・Κ 等」とあるとおりマナゾーンの裏向きカードを表向きに戻す。イベントを作らないため「表向きで置かれた時」は誘発しない）。マナゾーンの裏向きカード関連の先例は第228/229弾 crystal_charger（face resolve_face_down）で、裏向きマナの状態（Card.face_down）と filter の face_down 照合は既存。
- **負ける時形（dm23ex3-or1 のみ）**: キーワードとは別に置換能力を1つ足す。{kind: replace, optional: true, when: {event: lose}, if / instead は基本形と同じ}。敗北の置換は第188弾の lose_replace 経路（_lose_candidates が敗北する側の bz を走査し、敗北する側に諮問する。辞退の選択肢は常にある）。「クリスターナル・Κ」は水晶ソウル持ちゼニスの変形名だが、機構はエターナル・Κと同一のため同じキーワードで表す。
- Rust: 両形とも optional を含むため _simple_replace の対象外（escape / true_escape と同じ）で、この能力を持つカードを含む対局は Python にフォールバックする。新規 GameState フィールドなし（state.rs 変更なし）。スキーマはキーワード enum の追加で再生成した（data/schema/card.schema.json、3行差分）。
- プロト T804–T805（T804 = 基本形そのもの、T805 = 負ける時形つきの dm23ex3-or1 の形）、tests/test_vocab_pilot283.py（11件: parse・EXPECTED 一致、未知キーワード拒否、非 rust-simple、基本形＝破壊置換／辞退／バウンス置換／裏向き2枚では諮問なし／裏向き5枚から3枚だけ選ぶ、負ける時形＝破壊置換の共存／山札切れの置換／辞退で敗北／裏向き2枚では諮問なし）＋ tests/test_vocab_pilot283_cards.py（2件: 対象8件の未登録・ギャップ純粋確認、partial＋本弾条項の提出形 parse）。回帰: 第277弾本体＋第281弾本体＋第228弾本体＋第188弾本体＋第238弾本体＋test_rules＋test_rust_schema_sync＋test_data_audit 95件が通る。
- **テストの罠**: parse 後の abilities には partial 自身のキーワード（double_breaker / blocker 等）の展開分も含まれるため、cards テストで partial の abilities の残存を数える時は keyword 付きの展開分を除外すること。裏向きマナの fixture は setup 後に `e.s.cards[c].face_down = True` で直接立てる（第145・154弾の先例）。
- ラウンド318側の注意: **対象8行すべてが他のギャップを併せ持つため、本弾だけでは解放されない可能性が高い**。残りギャップは dm23ex3-or1 → use_opponent_etb_abilities、dm23ex3-s06 → look_put_any_number_rest_to_hand、dm23ex3-027 → even_shield_or_cost_attack_permission、dm24bd6-002 → each_opponent_shieldize、dm24bd6-011 → reveal_until＋entered_turn_attack_player、dm24bd6-024 → battle_by_cost、dm24rp3-td01 → cast_opponent_graveyard_spells_then_bottom、dm24sp2-003 → tapped_self_cannot_be_attacked。提出形は partial のキーワードに eternal_kappa を足すだけ（or1 は負ける時形の置換能力も1つ足す）。各行の他の条項は partial のまま（dm23ex3-s06 の partial は grant の常在型が3件あるが、うち2件は同一 dict の重複。submit 時の重複排除に任せる。dm24sp2-003 の partial の abilities は要検証のまま残す）。alias は or1 → dm23ex3-orsec1、s06 → dm23ex3-sp4、bd6-011 → dm23ex3-s01、bd6-024 → dm23ex3-009、rp3-td01 → dm23ex3-s05 / dm23ex3-sp3、sp2-003 → dm23ex3-s08 / dm23ex3-sp5（提出前に id・alias・カード名とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること）。submit は partial の abilities と回答を連結する（第313弾の教訓）ため、登録後に abilities の件数・内容とキーワードをテキストと照合すること。

### ラウンド318（第283弾）

eternal_kappa 8件のうち3件を新規登録、5件を差し戻し（Κ節をキーワードとして partial に保存）。converted 10,154 → 10,157 / rejects 2,179 → 2,176、canonical overlap は不変（既存の alias 級 stale 10件のまま）・漏れ 0。eternal_kappa は残り0件で解消。reopen eternal_kappa は **0件**だった（8行すべてが他のギャップを併せ持ち、gaps ⊆ {eternal_kappa} の条件に合わない）ため、対象行は rejects に残したまま submit で直接処理した（登録分は rejects から除去され、差し戻し分は partial と gaps が更新される）。提出前の照合（real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml、id・alias・カード名とも）は重複なし（alias はいずれも rejects に行が無く、登録側の source.aliases に畳み込んだ）。

- **ギャップ名のドリフト（本ラウンドの主発見）**: 3件の「他のギャップ」は実際には既存語彙で表現可能だった。ギャップ名だけで未実装と判断せず、条項ごとにエンジンと converted の先例と照合すること。
  - **dm23ex3-s06 「使命」の頂天 グレイテスト・グレート**（look_put_any_number_rest_to_hand）: 既存イディオムで登録。choose {zone: deck, from_top: 3, look: true, count: all} as: pile → play_free {ref: pile, filter: {types: [creature], cost_le: 7}, count: any} → move {ref: pile, count: all} to: hand（reason: draw）。partial のスピードアタッカー付与の常在型3件は同一 dict の重複で、submit の重複排除により1件に畳まれた。alias: dm23ex3-sp4。
  - **dm24bd6-002 「祝福」の頂天 ウェディング**（each_opponent_shieldize）: 「相手は自身の〜を選び、シールド化する」は chooser: opp の move 2連で登録（バトルゾーンのクリーチャー2体 → shield（reason: charge）、その後、手札2枚 → shield）。partial の攻撃時誘発（相手が自身のシールド1枚を選び墓地へ）はそのまま。alias なし。
  - **dm24sp2-003 「戦鬼」の頂天 ベートーベン**（tapped_self_cannot_be_attacked）: ギャップ名は本文の誤読。本文は「このクリーチャーがタップしていれば、相手のクリーチャーは自分を攻撃できない」＝プレイヤー保護で、dmrp22-043 の同一文先例 {kind: static, affects: {owner: opp, zone: bz, filter: {types: [creature]}}, if: {exists: {ref: self, filter: {tapped: true}}}, mod: {deny: [attack_player]}} で登録。ついでに partial を再構築した: マッハファイター誘発の重複3件 → 1件、出た時の「残り」は count: "rest"（スキーマ enum にあるがエンジン未実装）を使わず、ref に束縛された残存分を count: all で move する既存の「残り」イディオム（dmex18-s11 先例）に置換。alias: dm23ex3-s08 / dm23ex3-sp5。
- **差し戻し5件**（Κ節は解決済みとして partial に保存し、eternal_kappa を gaps から除いた）: dm23ex3-or1 → [use_opponent_etb_abilities]（負ける時形の置換能力も partial に追加）、dm23ex3-027 → [even_shield_or_cost_attack_permission]、dm24bd6-011 → [reveal_until, entered_turn_attack_player]、dm24bd6-024 → [battle_by_cost]（プローブ提出で partial が回答と一致することを確認してから本提出）、dm24rp3-td01 → [cast_opponent_graveyard_spells_then_bottom]。
- submit 後の照合（第313/315弾の教訓）: 登録3件とも登録形の keywords・abilities を公式テキストと完全照合（cards テストの test_registered_forms が完全一致を固定）。crystal_soul: 3 は保持。テキスト由来のキーワード常在型の追加は無し。
- テスト: tests/test_vocab_pilot283_cards.py を登録形に書き換え（登録形の完全一致、差し戻し5行の gaps と Κ節保存の確認、振る舞い6件＝ s06 の出た時／bd6-002 のシールド化と Κ 置換／sp2-003 の出た時・タップ時保護・対照）＋ tests/test_data_audit.py で **16 passed in 87.90s**。旧テストの stale 台帳を修正: tests/test_vocab_pilot196_cards.py の test_family_leftovers_are_multi_gap_only（残件が多重ギャップのみ、という前提）はファミリー解消に伴い test_family_cleared（残件0件の確認）に更新し、同ファイル＋第283弾本体で **13 passed**。テスト中の発見: (1) build の deck_exact は filler と同じ defn の spec カードも山札から除去する。(2) 山札0枚は SBA で即敗北（703.4b のエンジン解釈。効果の途中で一瞬でも0枚になれば敗北）なので、look 系テストの山札は処理後に1枚以上残る構成にすること。(3) build で hand を指定しないプレイヤーの手札は空（配られた手札は山札に戻され、指定ゾーンだけが置き直される）。(4) タップ fixture はターン開始時のアンタップで消えるため相手ターンの決定前に立てること。ただし攻撃決定の提示後に状態を変えると回答消費時の選択肢再計算でインデックスがずれる（第271弾の教訓）ため、自ターンの攻撃決定には触らない。回答下書き: ~/workspace/DMPJ-work/answers/round318.yaml（プローブ: round318-probe.yaml、本提出: round318-rest.yaml）。

## 第284弾 once_per_turn_replacement（各ターン1度しか使えない置換）

ギャップ名 once_per_turn_replacement の純粋3件（dm22rp2x-001 真実の精霊ヴァルペキュラ / dm22rp2x-050 霊魂と怨念のドライバー / dm23sd1-002 ボルシャック・モルナルク）。3件とも不足は「置換効果に各ターン1度の回数制限を付ける語彙が無い」という点だけで、partial の notes は「置換の相談経路は once_per_turn 印を見ない」と書いている。しかし置換側の once_per_turn 対応は第196弾で入っており（events._replacement が ab["once_per_turn"] を見て、選ばれた時にだけ turn_counters へ印を付け、辞退では消費しない）、第281弾＋ラウンド316で dm26rp3-001 / dm24ex4-042 が once_per_turn つき置換の登録形として実証済み。つまり本ファミリーはギャップ名のドリフトであり、本弾は新語彙・エンジン変更なしのイディオム弾として、3件それぞれの instead の形を実挙動で固定する。

- **形A（dm22rp2x-001）**: {kind: replace, optional: true, once_per_turn: true, when: {event: move, from: bz, to: graveyard, reason: destroy, subject: {owner: you, filter: {types: [creature, tamaseed]}}}, instead: [move {select: {ref: event.subject}, to: shield, reason: charge}]}。対象を {ref: event.subject} で指してシールド化する形は dm25ex3-rp1001 が登録先例（reason: charge はシールド化の標準、dmr06-020 等）。subject は self を含む（発生源自身の破壊でも諮問される）し、タマシードも対象になる（T811 で実挙動確認）。
- **形B（dm22rp2x-050）**: {kind: replace, optional: true, once_per_turn: true, when: {event: move, from: bz, subject: {owner: you, filter: {types: [creature]}}}, instead: [move {select: {ref: event.subject}, to: mana, reason: put, tapped: true}]}。when は第281弾の基本形と同じ「離れる時」全般（破壊でもバウンスでも発火）。原文が「タップしてマナゾーンに置く」ため move の tapped: true でタップしたまま置く。dm03-005 の mana_put 形（タップ指定なし＝アンタップで置く）とは区別される。
- **形C（dm23sd1-002）**: {kind: replace, optional: true, once_per_turn: true, when: {event: move, from: bz, to: graveyard, reason: destroy, subject: {owner: you, filter: {race_has: アーマード・ドラゴン}}}, if: {exists: {zone: hand, owner: you, filter: {race_has: ファイアー・バード}}}, instead: [play_free {select: {zone: hand, owner: you, filter: {race_has: ファイアー・バード}, count: 1}}]}。**if のゲートが必須**: 手札にファイアー・バードが無い時に諮問して選んでしまうと instead が空振りし、ドラゴンが無条件で残ってしまう（公式では使えない置換は選べない）。escape の if: exists と同じ役割で、本弾で「鳥が無ければ諮問自体が起きない」ことを実挙動で固定した。
- **付随形（dm22rp2x-001 の第2能力）**: {kind: trigger, when: {event: turn_start, player: opp}, if: {cmp: [{count: {zone: shield, owner: you}}, ">", {count: {zone: shield, owner: opp}}]}, effect: [tap {select: {zone: bz, owner: opp, filter: {types: [creature]}, count: 2}}]}。turn_start の player: opp（登録先例7件）と cmp の両辺 count の組み合わせを実挙動で固定（シールドが多い時だけ相手の獣2体がタップする。対照も確認）。
- Rust: 3形とも optional + once_per_turn を含むため _simple_replace の対象外（dm26rp3-001 等と同じ Python フォールバック）。新規 GameState フィールドなし（印は既存の turn_counters。state.rs 変更なし）。スキーマ再生成なし（once_per_turn は置換のキーとして登録済み）。
- プロト T806–T812（T806 = 形Aそのもの、T807 = 形Bそのもの、T808 = 形Cそのもの、T809 = 付随形そのもの、T810 = ファイアー・バード役＋味方役のバニラ、T811 = 保護対象役のバニラタマシード、T812 = タマシード破壊呪文）、tests/test_vocab_pilot284.py（16件: parse・EXPECTED 一致、未知キーワード拒否、非 rust-simple、形A＝味方を守る／同ターン2体目は諮問なし／次ターンで再諮問／辞退で消費しない／タマシードも守る／自身も守る／相手は守らない、形B＝バウンスでタップしたままマナへ／破壊でもマナへ＋各ターン1度／辞退で手札へ、形C＝鳥が出てドラゴンは残る／鳥が無ければ諮問なし／辞退で消費しない／ドラゴン以外は守らない、付随形＝シールドが多ければ2体タップ／対照）＋ tests/test_vocab_pilot284_cards.py（2件: 対象3件の未登録・ギャップ純粋確認、提出形 parse）。回帰: 第196弾＋第281弾＋第283弾本体＋test_rules＋test_rust_schema_sync 72件、test_data_audit 8件が通る。
- **テストの罠**: (1) setup のシールドは T001 filler で埋まるため、シールドゾーンの枚数を defn で数えるテストの味方役には filler と重ならない defn（T810）を使うこと。(2) 形B の「タップしたままマナ」は相手ターンに解決すると次の自ターン開始のアンタップで消えてから次の決定が提示されるため、観測は相手ターン内の決定（相手の攻撃決定）で行うこと。(3) 1ターンに複数枚の呪文を唱えられる（マナが足りる限り）ため、「同ターン2回目」の検証はマナ枚数で唱えられる回数を絞ること。
- ラウンド319側の注意: 対象3行すべてが本弾で解放される。提出形は partial を土台に条項を足すだけ（3件とも partial の text は公式全文で差し替え不要）: dm22rp2x-001 は abilities を持たない partial に形A＋付随形を足す（alias: dm22rp2-001 / dm22rp2x-001x）。dm22rp2x-050 は abilities を持たない partial に出た時 {event: move, to: bz, subject: self} → 上から2枚を墓地に置く（move {zone: deck, from_top: 2, count: all} to: graveyard, reason: put）＋形Bを足す（alias: dm22rp2-050）。dm23sd1-002 は partial の出た時（墓地のファイアー・バードをすべて手札に加える）が完全なため形Cを足すだけ（alias なし）。submit は partial の abilities と回答を連結する（第313弾の教訓）ため、登録後に abilities の件数・内容とキーワードをテキストと照合すること。提出前照合は id・alias・カード名とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml に対して行うこと。

### ラウンド319（第284弾）

once_per_turn_replacement 純粋3件をすべて新規登録、差し戻し0件。converted 10,157 → 10,160 / rejects 2,176 → 2,173、canonical overlap 0・漏れ 0。once_per_turn_replacement は残り0件で解消。reopen は対象3行のみを外し（alias 行の巻き込みなし）、提出前の照合（real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml、id・alias・カード名とも）は重複なし（proto の4ヒットは第284弾プロト T806–T809 の text 内参照のみ）。canon_id は3件とも自 ID（第317弾の教訓で確認済み。aliases_for も partial の aliases と一致）。

- **dm22rp2x-001 真実の精霊ヴァルペキュラ**: abilities を持たない partial に形A＋付随形（第2能力）を追加。alias: dm22rp2-001 / dm22rp2x-001x（登録側の source.aliases に畳み込み。rejects に alias 行は無し）。
- **dm22rp2x-050 霊魂と怨念のドライバー**: abilities を持たない partial に出た時（上から2枚を墓地に置く）＋形Bを追加。alias: dm22rp2-050（同上）。
- **dm23sd1-002 ボルシャック・モルナルク**: partial の出た時はそのまま、形C（if ゲート付き）を追加。alias なし。submit の play_free lint 警告（reason: summon の示唆）は助言のみで、第284弾で実挙動検証した定形のため維持。
- submit 後の照合（第313/315弾の教訓）: 登録3件とも登録形の abilities・キーワード・aliases・text が回答と完全一致（cards テストの test_registered_forms が固定）。partial 連結残り・テキスト由来のキーワード常在型の追加は無し。
- テスト: tests/test_vocab_pilot284_cards.py を登録形に書き換え（登録形の完全一致、振る舞い7件＝ 001 の形A保護／第2能力の2体タップ、050 の出た時ミル2／形Bのバウンス→タップしたままマナ、002 の出た時回収／形Cの身代わり召喚／鳥なし対照）で **8 passed in 33.24s**、tests/test_data_audit.py で **8 passed in 62.72s**、第284弾本体は **16 passed in 1.55s**。旧テストに対象 id の bounce 断言は無し。テスト中の発見: cards テストで tests.conftest を import すると別モジュールとして再実行され DMSIM_SKIP_CONVERTED=1 が復活して converted の defn が unknown card になる。setup が要る cards テストは conftest を import せず scenario.build を直接包むこと（第283弾 cards の方式）。回答下書き: ~/workspace/DMPJ-work/answers/round319.yaml。

## 第285弾 free_play_event（コストを支払わずに出したクリーチャーを破壊する）

ギャップ名 free_play_event の純粋3件（dmex10-006 ウソと盗みのエンターテイナー / dmex12-064 キャタピラ親方 / dmsp01-033 早撃人形マグナム）。3件とも不足は「コストを支払わずにバトルゾーンに出した時」という出来事を照合する語彙が無いという点だけで、partial の notes も「無料で出したことを照合する語彙が無い」と書いている。しかしその照合は第257弾で入っている: when の unpaid は両方のレコード構築経路（events._record_for と _apply_one）に伝播し、(1) プレイ自体が無料の時（play タスクの free 印。G・ゼロ／S・トリガー召喚／play_free の「使う」）と (2) 効果でバトルゾーンに出た時（reason が summon でなく、bz の中での移動でない move）に立つ。ラウンド291では同じ unpaid 誘発を持つ別ギャップ名の行が再変換済みで、destroy {ref: event.subject} の形も登録先例がある。つまり本ファミリーはギャップ名のドリフトであり、本弾は新語彙・エンジン変更なしのイディオム弾として、2つの subject 形と境界を実挙動で固定する。

- **相手形（dmex10-006）**: {kind: trigger, when: {event: move, to: bz, subject: {owner: opp, filter: {types: [creature]}}, unpaid: true}, effect: [destroy {select: {ref: event.subject}}]}。
- **全員形（dmsp01-033 / dmex12-064）**: subject から owner を省く（_subject_match は owner が無い／"any" の時どちらのプレイヤーにも一致する）。自分が効果で出した自分のクリーチャーも壊れるし、**発生源自身が効果で出た時も自身を破壊する**（原文「いずれかのプレイヤーが…出した時、そのクリーチャーを破壊する」の素直な読み。誘発の収集は移動後の bz を見るため自身も対象になる。本弾で実挙動を固定）。
- **境界**: 通常召喚（支払った）には発火しない。**コスト0のクリーチャーを通常プレイしても「支払った」扱いで発火しない**（unpaid はコストの額ではなくプレイの free 印）。タマシードは filter の types: [creature] で対象外（3件とも原文はクリーチャーのみ。エレメント全般が対象の行は trigger_when_opponent_plays_free 側に残る）。
- Rust: when に unpaid を含むため _simple_when の対象外（_OK な when キーは event/from/to/reason/player/subject のみ）で Python フォールバック。新規 GameState フィールドなし（state.rs 変更なし）。スキーマ再生成なし（unpaid は when のキーとして登録済み）。
- プロト T813–T819（T813 = 相手形そのもの、T814 = 全員形そのもの、T815 = 効果で出す役の無料召喚呪文、T816 = 出される役のバニラ、T817 = コスト0獣、T818 = G・ゼロ獣、T819 = タマシード召喚呪文。対照役に第284弾の T811 タマシードを流用）、tests/test_vocab_pilot285.py（12件: parse・EXPECTED 一致（destroy はマクロ展開形で比較）、未知キーワード拒否、非 rust-simple、相手形＝効果出しを破壊／通常召喚は無事／G・ゼロ無料プレイを破壊／自分の効果出しは無事／タマシードは無事／コスト0通常プレイは無事、全員形＝自分の効果出しを破壊／相手の効果出しを破壊／通常召喚は無事／自身が出た時は自身を破壊）＋ tests/test_vocab_pilot285_cards.py（2件: 対象3件の未登録・ギャップ純粋確認、提出形 parse）。回帰: 第257弾＋第281弾＋第284弾本体＋test_rules＋test_rust_schema_sync 75件、test_data_audit 8件が通る。
- **テストの罠**: s.turn はプレイヤー交代ごとに進む（P0 のターン = 1、P1 のターン = 2）。停止条件に turn を使うと相手ターンの最初の決定で止まってしまうため、効果解決の観測はゾーン内容＋ _quiet で行うこと。
- ラウンド320側の注意: 対象3行すべてが本弾で解放される。dmex10-006 は partial の text が切れているため reject 行の公式全文を text に戻し、abilities を持たない partial に2条項を足す: 第1条項（自分の他のクリーチャーがあれば攻撃されない）は cannot_be_attacked キーワードの展開そのもの {kind: static, affects: self, mod: {deny: [be_attacked]}} に if {exists: {zone: bz, owner: you, other: true, filter: {types: [creature]}}} の条件を付けた形（cards テストで parse 検証済み。登録形の振る舞い＝他のクリーチャーがいる時だけ攻撃対象にならない、もラウンド側で確認すること）、第2条項は相手形（alias: dmx22b-135 / promoy11-070 / promoy17-065 / promoy17-068）。dmex12-064 は partial が完全（J・O・E の opt_reduce 常在型＋speed_attacker）のため全員形を足すだけ（alias: dmbd03-008）。dmsp01-033 は speed_attacker のみの partial に全員形を足すだけ（alias: dmr07-030 / dmx22b-036 / promoy12-060）。submit は partial の abilities と回答を連結する（第313弾の教訓）ため、登録後に abilities の件数・内容とキーワードをテキストと照合すること。提出前照合は id・alias・カード名とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml に対して行い、canon_id が自 ID と異なる行が無いかも確認すること（第317弾の教訓）。
- 関連ファミリーへの言及: trigger_when_opponent_plays_free（純粋3件）と trigger_when_opponent_plays_without_paying（純粋2件＋dm26rp2-s011）の行も unpaid 誘発そのものは本弾の形で表せるが、各行には別の障害（エレメント全般の subject、対象のコスト参照、メクレイド、相手選択の破壊、自身破壊コスト等）が残るため、本弾では解放されない。dm26rp2-s011 は deck_faceup_power も併せ持つ。

### ラウンド320（第285弾）

free_play_event 純粋3件をすべて新規登録、差し戻し0件。converted 10,160 → 10,163 / rejects 2,173 → 2,170、canonical overlap 0・漏れ 0。free_play_event は残り0件で解消。reopen は対象3行のみを外し（alias 行の巻き込みなし）、提出前の照合（real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml、id・alias・カード名とも）は重複なし（proto の2ヒットは第285弾プロト T813/T814 の text 内参照のみ）。canon_id は3件とも自 ID（第317弾の教訓で確認済み）。

- **dmex10-006 ウソと盗みのエンターテイナー**: text を reject 行の公式全文に戻し、第1条項（cannot_be_attacked 展開形＋ if 条件）と第2条項（相手形）を追加。alias: dmx22b-135 / promoy11-070 / promoy17-065 / promoy17-068（登録側の source.aliases に畳み込み。rejects に alias 行は無し）。
- **dmex12-064 キャタピラ親方**: partial の J・O・E 常在型はそのまま、全員形を追加。alias: dmbd03-008（同上）。
- **dmsp01-033 早撃人形マグナム**: 全員形を追加（原文の「マナゾーンのカードをタップせずに」は unpaid 照合で判定）。alias: dmr07-030 / dmx22b-036 / promoy12-060（同上）。
- submit 後の照合（第313/315弾の教訓）: 登録3件とも登録形の abilities・キーワード・aliases・text が回答と完全一致（cards テストの test_registered_forms が固定）。partial 連結残り・テキスト由来のキーワード常在型の追加は無し。alias 級 stale 行は従来の10件のままで本ラウンド無関係。
- テスト: tests/test_vocab_pilot285_cards.py を登録形に書き換え（登録形の完全一致、振る舞い7件＝ 006 の相手形破壊／自分の効果出しは無事／第1条項で他の獣がいれば攻撃対象にならない／単独では対象になる対照、064 の全員形で自分の効果出しを破壊、033 の全員形で相手の効果出しを破壊／自身が出た時は自身を破壊）で **8 passed in 31.84s**、tests/test_data_audit.py で **8 passed in 61.50s**。旧テストに対象 id の参照は無し。第1条項の検証法: P0 の2体でプレイヤーを攻撃して両方タップさせ、P1 の最初の攻撃決定の選択肢キーを捕捉する（タップした味方は対象に出るが dmex10-006 は出ない／単独の対照では出る）。回答下書き: ~/workspace/DMPJ-work/answers/round320.yaml。

## 第286弾 choose_restriction（相手は可能ならこのクリーチャーを選ぶ）

ギャップ名 choose_restriction の純粋4件（dmr18-054 アクア特攻兵 デコイ / dmrp06-029 ギギギのギタロー / dm26rp2-033 救済のラクシャ ミルク / dm26ex3-088 雨森まもり）。4件の partial はいずれも「選択を強制する語彙が無い」として unsupported に残しているが、その語彙は第199弾で入っている: mod `must_be_chosen: true`（セレクタの候補計算で、選ぶ側と別のコントローラーの候補の中に must_be_chosen を持つクリーチャーがいれば、そのコントローラーの他のクリーチャーを候補から外す。ラウンド235で dmrp20-067 が登録済み）。つまり本ファミリーはギャップ名のドリフトであり、本弾は新語彙・エンジン変更なしのイディオム弾として、残る3形と境界を実挙動で固定する。

- **形A（条件つき常在型、dmr18-054）**: {kind: static, affects: self, if: {cmp: [{count: {zone: mana, owner: you, filter: {civs: [water]}}}, ">=", 3]}, mod: {must_be_chosen: true}}。マナ武装の if 形は dm26rp2-028 の登録先例。水マナ2枚では制限しない（対照で確認）。括弧書き「自分の他のクリーチャーを攻撃またはブロックしてもよい」は、攻撃対象の決定（combat）とブロック決定がセレクタの候補計算を通らないため自動的に満たされる（武装中でも、タップした他の味方への攻撃選択肢と、他の味方でのブロック選択肢が残ることを実挙動で確認）。
- **形B（出た時・そのターン付与、dmrp06-029）**: {kind: trigger, when: {event: move, to: bz, subject: self}, effect: [{op: modify, select: {ref: self}, mod: {must_be_chosen: true}, duration: end_of_turn}]}。modify の継続的効果は chars の mods ループに集約され must_be_chosen が立つ（ジャストダイバーの modify 付与と同じ受け渡し）。ターンが回ると切れる。実挙動は、出たターンに自分の攻撃で割った相手の S・トリガー（T006）の対象選択が T821 に自動で決まる形で確認（対照: 置いただけ／不在では自由選択）。
- **形C（無条件常在型、dm26rp2-033 / dm26ex3-088）**: T498（第199弾）の形そのまま {kind: static, affects: self, mod: {must_be_chosen: true}}。dm26rp2-033 は shield_go キーワードが partial に既存（parse で置換2件に展開され、その後ろに形Cが付く）。dm26ex3-088 は第186弾で置換2件（スーパーガードマン＝ battle_substitute、破壊時シールド化）が解けており、残るは形Cだけ。
- **境界（第199弾の意味論を踏襲）**: このクリーチャー自身が候補にいない効果（フィルタ不一致、be_chosen 保護で先に除外）では制限しない。自分の選択は制限されない。複数対象の効果では候補がこのクリーチャーのみに絞られる（第199弾で固定した意味論。dmr18-054 の原文「以外選べない」とも一致する）。
- **観測上の注意**: 制限は candidates() の素の候補計算ではなく select の決定経路（be_chosen フィルタの直後）で効くため、candidates() の直接呼び出しでは観測できない。形B の検証は chars の印＋ S・トリガーの実挙動で行うこと。また召喚後のメインステップは単発で次のメイン決定は来ないため、「出たターン」の観測点は支払い以外の最初の決定（攻撃ステップ）。
- Rust: must_be_chosen の判定は selectors（Python）側。形B は継続的効果を生むため対象は Python フォールバック。新規 GameState フィールドなし（state.rs 変更なし）、スキーマ再生成なし（must_be_chosen は MOD_KEYS 登録済み、modify / duration は既存）。
- プロト T820（形A）/ T821（形B）。tests/test_vocab_pilot286.py（9件: parse・形A＝武装時に自動決定／水2枚では自由選択／攻撃対象は対象外／ブロックは対象外、形B＝出たターンの印／ターン経過で消滅／直接置き対照／S・トリガー強制＋対照）＋ tests/test_vocab_pilot286_cards.py（2件: 対象4件の未登録・ギャップ純粋確認、提出形 parse）。回帰: 第199弾＋第284弾＋第285弾本体＋test_rules＋test_rust_schema_sync 79件、test_data_audit 8件が通る。
- ラウンド321側の注意: 対象4行すべてが本弾で解放される。dmr18-054 / dmrp06-029 は partial の text が節だけに切れているため、reject 行の公式全文を text に戻すこと。dm26ex3-088 は partial に abilities（置換2件）が既にあるため、回答には形Cだけを足すか、置換2件をバイト同一で含めること（submit は partial と連結し、同一 dict のみ重複除去される）。提出前照合は id・alias・カード名とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml に対して行い、canon_id が自 ID と異なる行が無いかも確認すること（第317弾の教訓）。

### ラウンド321（第286弾）

choose_restriction 純粋4件をすべて新規登録、差し戻し0件。converted 10,163 → 10,167 / rejects 2,170 → 2,166、canonical overlap 0・漏れ 0。choose_restriction は残り0件で解消。reopen は対象4行のみを外し（巻き込みなし。choose_restriction を含む行はこの4件だけ）、提出前の照合（real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml、id・カード名とも）は重複なし（ヒット0件）。canon_id は4件とも自 ID（load_rows の canonical corpus に自 ID で載ることを確認）。4件とも identity.aliases_for は空で alias 畳み込み・stale 整理は無し（alias 級 stale 行は従来の10件のまま、本ラウンド無関係）。

- **dmr18-054 アクア特攻兵 デコイ**: partial は abilities を持たず text も節だけ（「以外選べない」）に切れていた。text を reject 行の公式全文に戻し、形A（マナ武装3の条件つき常在型 must_be_chosen）を追加。submit 時 split は None のため merge_split は働かず、回答の text・abilities がそのまま登録される。
- **dmrp06-029 ギギギのギタロー**: 同じく text を全文に戻し、形B（出た時、そのターン modify で must_be_chosen を付与）を追加。split は None。
- **dm26rp2-033 救済のラクシャ ミルク**: shield_go キーワードはそのまま、形Cを追加。split が shield_go をキーワードとして拾い、text は corpus の全文で上書きされる。登録形の parse で置換2件＋形Cの3能力になる。
- **dm26ex3-088 雨森まもり**: 第186弾で解けた置換2件（スーパーガードマン、破壊時シールド化）は partial の abilities のまま引き継ぎ、末尾に形Cを追加。split の extra は空のため、回答に置換2件を含めないと登録形から落ちる（本ラウンドは partial を土台に形Cだけを足す方式で回避）。
- submit 後の照合（第313/315弾の教訓）: 登録4件とも abilities・キーワード・text が公式全文と完全一致（cards テストの test_registered_forms が固定）。partial 連結残り・テキスト由来の追加は無し。
- stale 台帳の修正（第276/277弾の教訓）: tests/test_vocab_pilot186_cards.py の BOUNCED から dm26ex3-088 を外し（choose_restriction で差し戻し中という前提が崩れたため）、088 の partial 断言も削除。docstring にラウンド321で登録済みの旨を明記。
- テスト: tests/test_vocab_pilot286_cards.py を登録形に書き換え（登録形の完全一致、振る舞い6件＝ 054 の武装時自動決定／水2枚では自由選択の対照、029 の出たターンの印＋ターン経過で消滅／S・トリガー強制、033 の自動決定＋ shield_go で表向きシールド化、088 の自動決定＋置換 decline で墓地）で **7 passed in 32.81s**、tests/test_vocab_pilot186_cards.py で **3 passed in 69.80s**、tests/test_data_audit.py で **8 passed in 63.59s**。
- テスト中の発見: ゼロ文明のカード（dmrp06-029）の支払いは、エンジンの civ_ok が need の各文明を別々のマナで満たすため、zero 文明のマナが1枚要る。T001（自然）4枚では play 選択肢自体が出ない。cards テストではマナに同カードを1枚置き、残り3枚を T001 で揃えた（合計値4＝コスト4）。また shield_go の破壊置換は必須形（optional でない）ため、033 は破壊されると墓地でなく表向きシールドゾーンに行く。
- 回答下書き: ~/workspace/DMPJ-work/answers/round321.yaml。

## 第287弾 山札の一番下へのアクセス（deck_bottom_card / deck_bottom_reveal）

ギャップ名 deck_bottom_card の純粋4件（dm26rp3-tr007 / dm26sd1-c001 一王二命三眼槍、dmr06-002 合身巨兵エクスキュベーターMS、dmrp05-007 カツラデランス）と deck_bottom_reveal の純粋3件（dm26rp3-018 キング・ザ・ベスト、dm32-019 / dm32-019hc サイバーX・ザナドゥ）の計7件。2つのギャップ名は同じ欠落を指している: 山札の「一番下」を選ぶ手段が無い（セレクタは from_top のみ）。本弾の新語彙は3点、いずれも最小の拡張:

- **セレクタキー `from_bottom`**（defs の SELECTOR_KEYS + selectors.candidates の両分岐 + select の自動決定条件）。山札リストは上が先頭（from_top は lst[:n]）なので、一番下は末尾の N 枚を取る。複数ゾーン指定では山札にだけ効く（from_top と同じ）。フィルタは「下から N 枚」の中で効く。count を書かなければ from_top と同じく候補をそのまま返し、決定を出さない。JSON スキーマはセレクタキーを列挙しないため、この追加でのスキーマ差分は無い（下記 player 引数の分だけ再生成した）。
- **`play_free` の `player` 引数**（任意、既定は効果の使用者。opvocab + @op デコレータ + ops 本体で eng._rel 解決）。「相手はそれをバトルゾーンに出してもよい」（dm32-019）は出す主体が相手でなければならず、従来の play_free は env["you"] で固定だった。選択は select の chooser: opp、実行は player: opp と分けて書く。スキーマ再生成済み（差分は play_free の player のみ）。
- **敗北置換の発生源走査に手札を追加**（events._lose_candidates）。従来はバトルゾーンのカードだけを走査していたため、「手札にあるこのカードを〜置いてもよい」形の lose 置換が永遠に候補に入らなかった。手札のカードは zone: hand を宣言した置換だけが候補になる（_replacement / _break_candidates の「バトルゾーン外の発生源は、そのゾーンを宣言した置換だけ」と同じ規則）。h_lose_replace は候補をそのまま使うため変更なし。

形は5つ:

- **形A（一番下を手札に、T822。dmr06-002 の末尾節）**: {op: move, select: {zone: deck, owner: you, from_bottom: 1}, to: hand, reason: draw}。
- **形B（一番下を墓地に置き、出してもよい、T823。一王二命三眼槍の鬼エンド）**: 誘発の if ゲート {any: [自分のシールド数 == 0, 相手のシールド数 == 0]} + move {from_bottom: 1, to: graveyard, reason: put, as: bot} + {op: if, cond: {exists: {ref: bot, filter: {types: [creature], cost_le: 5}}}, then: [may [play_free {ref: bot}]]}。dmrp05-007 はゲートなし・ジョーカーズ・コスト6以下の変種。
- **形C（下から公開して出す、T824。dm26rp3-018）**: 攻撃時誘発で choose {zone: deck, owner: you, from_bottom: 3, look: true, count: all} as pile（reveal: true）→ play_free {ref: pile, filter: {types: [creature], races: [ジョーカーズ], cost_le: 8}, count: 1, up_to: true} → 残りを move {ref: pile, count: all, to: deck, position: top, order: choose, reason: put}。束の扱いは第318弾 dm23ex3-s06（from_top 版）と同じで、残りは gen 切れの参照が落ちることで決まる。山札内移動（deck→deck）の順序付けは mekurade の残り処理と同じ move の order: choose。
- **形D（相手が自身の一番下を出す、T825。dm32-019）**: 離れた時誘発 {event: move, from: bz, subject: self} で choose {zone: deck, owner: opp, from_bottom: 1, look: true, count: all} as pile（reveal: true）→ play_free {select: {ref: pile, filter: {types: [creature], evolution: false}, count: 1, up_to: true, chooser: opp}, player: opp}。相手のカードは相手のコントロールで出る（play タスクの player が召喚 move の controller になる）。019 の出た時節（相手の進化ではないクリーチャーを山札の一番下に戻す）は move の position: bottom で既存。
- **形E（手札からの敗北置換、T826。一王二命三眼槍）**: {kind: replace, zone: hand, optional: true, when: {event: lose}, if: {all: [{is_turn: opp}, {exists: マナに闇}, {exists: マナに火}]}, instead: [move {ref: self, to: deck, position: bottom, face_up: true, reason: put}]}。闇と火は別々の exists で見る（多色1枚でも両方を満たす）。

- **境界**: 「表向きにし」の状態保持は本弾の範囲外。move の face_up は移動レコードには載るが、_raw_move が face_up をゾーンの public 性で決めるため、山札（非公開ゾーン）に入ったカードの face_up は残らない。山札内の表向き状態を数える・参照する仕組みは deck_faceup 系（dm26rp2-s011 の deck_faceup_power）の領域。一王二命三眼槍については「表向きにし」は置換の公開そのもので、置かれた後の状態を参照する条項は無いため、この形で正確。
- **Rust**: from_bottom は Rust 側セレクタの許可キー一覧（count 専用・通常の両方）に無いため、その選択を含む効果は Python フォールバックになる。player: opp の play_free は Rust が player を無視するが、形Dは直前の choose が from_bottom を含むため必ず Python パスに入る。敗北置換はもともと Rust の game_lose が諮問を持たず対象外。新規 GameState フィールドなし（state.rs 変更なし）。
- プロト T822（形A）/ T823（形B）/ T824（形C）/ T825（形D）/ T826（形E）/ T827・T828（役カード: コスト2のバニラ、コスト6のジョーカーズ）。tests/test_vocab_pilot287.py（16件: parse・from_bottom の候補計算（from_top 対照・過大指定・フィルタ）、形A＝一番下が手札に来て残りの並び不変、形B＝出す／辞退で墓地／コスト6は諮問なし／ゲート不成立では不発、形C＝ジョーカーズを出して残りを回答順に上へ／対象なしでは全部を上へ、形D＝相手が自分の獣として出す／辞退／一番下が呪文では諮問なし、形E＝置換で敗北回避し一番下へ／火マナなしでは諮問なし／decline で敗北／自分のターンでは is_turn で諮問なし）＋ tests/test_vocab_pilot287_cards.py（3件: 対象7件の未登録・ギャップ純粋確認、提出形 parse、未知セレクタキーの拒否）。回帰: 第283・284・285・286・188弾本体＋test_rules＋test_rust_schema_sync＋test_defer_empty 105件、test_data_audit＋第196・199・271弾 33件、第259弾＋第283・285弾 cards 18件が通る。
- テスト中の発見: (1) ターン開始ドローは最初の決定より前に上から1枚を取るため、山札の並びの断言は「実行を答えた時点」のスナップショットを基準にすること。(2) 召喚したターンの攻撃ステップは決定を出さない（召喚酔いのみ）ため、解決後の観測点は次の相手ターンのチャージ決定が安全。(3) deck_exact で 0〜1枚の山札は SBA の山札切れで即敗北する（deck_emptied。第318弾の教訓の再確認）。両プレイヤーとも3枚以上を保つこと。
- ラウンド322側の注意: 対象7行すべてが本弾で解放される。dm26rp3-018 は partial 完全で形Cを足すだけ。dm32-019 / dm32-019hc は partial に abilities が無く、出た時（CIP_BOTTOM_RETURN）と形Dを構築する。dmr06-002 は partial のガチンコ勝利分岐の then の末尾に「その後、一番下を手札に加えてもよい」（may の move、形A）を追加する。dmrp05-007 は partial の faces が仮置き（名前 x/y、コストも誤り）のため公式 faces から再構築すること（クリーチャー面=形Bのジョーカーズ変種、呪文面=手札1枚捨て→2枚引く）。dm26rp3-tr007 / dm26sd1-c001 は partial が null で、公式データから全構築する（形E + 形B + speed_attacker / double_breaker）。両者は同一カード《一王二命三眼槍》の2刷り（tr007 の公式名にはセット表記が付くが登録名は同じ）で、どちらが canon で片方が alias になるかは提出前に identity で確認すること。提出前照合は id・alias・カード名とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml に対して行い、canon_id が自 ID と異なる行が無いかも確認すること（第317弾の教訓）。submit 後の照合（第313/315弾の教訓）で abilities・キーワードをテキストと照合すること。

### ラウンド322（第287弾）

対象7行（deck_bottom_card 純粋4件 + deck_bottom_reveal 純粋3件）を処理し、新規登録5件 + alias 畳み込み3行で両ファミリーと deck_bottom_mill を解消。converted 10,167 → 10,172 / rejects 2,166 → 2,158、canonical overlap 0・漏れ0。

- **canon の確定（提出前に identity で確認。第317弾の教訓）**: 対象7行のうち canon でない刷りが3行あった。dm32-019hc は dm32-019 の alias、dm26sd1-c001 は dm26rp3-tr007 の alias、そして当初の対象指定だった **dmrp05-007 は canon ではなく、正規刷りは dm26sd1-n006**（rejects では別ギャップ名 deck_bottom_mill の純粋1件として残っていた。同じ欠落の別名）。submit のコーパスは canonical_rows で正規刷りだけに絞られるため、非 canon の ID は提出できない。ラウンドは canon 5件（dm26rp3-018 / dm32-019 / dmr06-002 / dm26sd1-n006 / dm26rp3-tr007）を提出し、alias 3行は畳み込んだ。
- **reopen と alias 行の処理**: reopen deck_bottom_card deck_bottom_reveal deck_bottom_mill で6行を除去（dm26rp3-018 / dm26sd1-n006 / dm32-019 / dm32-019hc / dmr06-002 / dmrp05-007。巻き込みなし）。このうち 019hc と rp05-007 は提出しないため、そのまま rejects から消えて alias として取り込まれた形になる。tr007 / c001 は reason が無く reopen 対象外で、tr007 は submit が reject 行を pop し、**c001 は登録後に stale な alias 行として rejects.jsonl から直接除去**した（ラウンド306/307 の先例）。
- **dm26rp3-018**: partial に形Cを追加しただけ。キーワード3つ（g_strike / speed_attacker / double_breaker）は submit の split 連結で partial と一致し、重複・追加なし。
- **dm32-019**: 出た時（相手の進化ではないクリーチャーを1体選び、持ち主の山札の一番下に戻す。move position: bottom）と形Dを構築。submit の play_free lint 警告は助言のみで、第287弾で実挙動検証した定形のため維持。
- **dmr06-002**: partial のガチンコ勝利分岐の then 末尾に形A（may の move、from_bottom: 1 → hand、reason: draw）を追加。partial の text に文字化け（�）があったため reject 行の公式全文に戻した（submit の merge_split が text を原文行で置き換えるため登録形も正常）。
- **dm26sd1-n006**: partial の faces は仮置きのため公式 faces から再構築。**クリーチャー面は第287弾の提出形メモの may 形から修正した**: 原文は両刷りとも「コスト６以下のジョーカーズ・クリーチャーなら（バトルゾーンに）出す」で強制形であり、「出してもよい」の鬼エンド（形B）とは異なる。if ゲート（exists でコスト6以下のジョーカーズ・クリーチャーか確認）の内側に may を付けず play_free を直接置いた。登録形テストで yes_no の諮問が無いことと、ジョーカーズでない底は墓地に残ることを実挙動で確認。呪文面は手札を1枚捨て、カードを2枚引く。
- **dm26rp3-tr007**: partial が null のため公式データから全構築（形E + 形B + speed_attacker / double_breaker、闇/火・コスト5・パワー6000・デモニオ/鬼札王国）。登録名はセット表記を除いた《一王二命三眼槍》（canon 判定は ID で行われ、aliases は validate が原文行の名前から自動設定する）。submit の play_free lint 警告は助言のみで維持。
- **submit 後の照合（第313/315弾の教訓）**: 5件とも登録形の abilities・キーワード・aliases・text を公式全文と照合し、partial 連結の残り・テキスト由来の追加が無いことを確認。旧テストに対象 ID の bounce 断言は無し。
- テスト: tests/test_vocab_pilot287_cards.py を登録形に書き換え（登録形の完全一致 + 実挙動8件: 018 の形C、019 の出た時と形D、n006 のクリーチャー面の強制形と対照・呪文面、tr007 の鬼エンドと形E、002 のガチンコ勝利分岐でバウンスを辞退し一番下を手札に加える）— `10 passed in 32.35s`。tests/test_data_audit.py — `8 passed in 62.43s`。tests/test_vocab_pilot287.py — `16 passed in 2.12s`。
- テスト中の発見: 呪文面テストの手札枚数は「唱える前の最初の決定時点」を基準に数えると、唱えた1枚と捨てた1枚が減って2枚引くため増減ゼロになる（ターン開始ドローは build の spec 配置後に数え直されるため、基準時点の手札は spec のまま）。

## 第288弾 文明の一致（civilization_match）

ギャップ名 civilization_match の純粋3件（dm27-026 暗黒螺旋 / dm27-047 デビル・スモーク / dmr21-002 ワルスラ・プリンスS）。3件とも不足は「そのカードの文明と同じ文明のカードが自分のマナゾーンにあれば」の判定だけで、参照カードの特性を読む式に文明版が無かった。本弾の新語彙は1点、既存の参照特性式の対になる最小拡張:

- **式 `civs_of`**（selectors.eval_expr。races_of と同形で、参照カードの文明の和集合をソートして返す）。併せて selectors の _EXPR_KEYS と _chars_val の再入時辞書（civs を印刷文明で返す。races と同じ作法）、ops._bake_refs のベイク対象（継続的効果のフィルタ用。races_of と同じ）、defs の式検証の受理キー、schema.py の expr 定義へ追加し、スキーマを再生成した（差分は civs_of のみ）。フィルタの civs は辞書値を式として解決時に評価する既存経路（candidates の各分岐。第282弾の name_of と同じ）を通るため、{civs: {civs_of: 変数名}} と書ける。多色カードは和集合で返るため、「同じ文明」は多色のどれか1つでも一致すればよい（公式の読みどおり）。対象カードは move の as で移動後の参照を束縛するので、捨てた・破壊した後の墓地のカードでも文明を読める。

形は3つ:

- **形A（捨てたカード形、T829。dm27-026）**: 呪文効果 = move {select: {zone: hand, owner: opp, chooser: opp, count: 1}, to: graveyard, reason: discard, as: dropped} → {op: if, cond: {exists: {zone: mana, owner: you, filter: {civs: {civs_of: dropped}}}}, then: [move {select: {zone: mana, owner: opp, chooser: opp, count: 1}, to: graveyard, reason: put}]}。捨て札の選択も第2文のマナの選択も相手自身が行う（chooser: opp）。destroy / discard マクロは as を転送しないため明示 move 形で書く。
- **形B（破壊したカード形、T830。dm27-047）**: move {select: {zone: bz, owner: opp, filter: {types: [creature], tapped: false}, count: 1}, to: graveyard, reason: destroy, as: victim} → {op: if, cond: {exists: {zone: mana, owner: you, filter: {civs: {civs_of: victim}}}}, then: [may [draw 1]]}。一致しなければ引く諮問自体が起きない。
- **形C（公開したカード形、T831。dmr21-002）**: 誘発 {when: {event: move, to: bz, reason: summon, subject: {owner: you, other: true, filter: {types: [creature]}}}} の effect = [may [move {select: {ref: event.subject}, to: graveyard, reason: destroy, as: sac}, {op: if, cond: {exists: {ref: sac, zone: graveyard}}, then: [choose {select: {zone: deck, owner: you, from_top: 1}, reveal: true, as: top}, {op: if, cond: {exists: {ref: top, filter: {types: [creature], civs: {civs_of: sac}}}}, then: [move {ref: top, to: bz, reason: put}], else: [move {ref: top, to: hand, reason: draw}]}]}]]。「召喚した時」は when の reason: summon で受ける（play_free は 112.3g で召喚に当たるため reason: summon を持ち、reason: put の「出す」は当たらない）。「そうしたら」は、破壊が置換等で実際に起きなかった場合に後続を止めるため exists {ref: sac, zone: graveyard} のゲートで受ける。may は破壊全体を包む（辞退したら公開もしない）。

- **Rust**: civs_of を含むフィルタは解決時の式評価が要るため Python パス（name_of / races_of と同じ）。新規 GameState フィールドなし（state.rs 変更なし）。
- プロト T829（形A）/ T830（形B）/ T831（形C）。tests/test_vocab_pilot288.py（17件: parse・未知式キーの拒否、civs_of の式とフィルタ評価（単文明・多色の和集合・マナ照合）、形A＝一致で相手マナが墓地へ／不一致では不発／多色の捨て札は1文明でも一致、形B＝一致でドローの諮問（受諾・辞退）／不一致では諮問なし／タップしたクリーチャーは対象外（候補計算）、形C＝一致で上が場に出る／異文明・呪文は手札へ／辞退で何も起きない／自身の召喚・相手の召喚では誘発しない／reason ゲートの照合）＋ tests/test_vocab_pilot288_cards.py（2件: 対象3件の未登録・ギャップ純粋確認、提出形 parse）。回帰: 第284・285・286・287・282・263・170弾本体＋test_rules＋test_rust_schema_sync 138件、test_data_audit＋第288・287弾 cards 20件が通る。
- テスト中の発見: バトルゾーンは zones["bz"] が共有リスト（zlist も両プレイヤー分を返す）ため、ゾーン内訳の断言は controller で絞ること（第286弾の教訓の再確認）。_match_when は subject 照合まで含むため、reason ゲートの単体検証では subject の実参照をレコードに含めること。
- ラウンド323側の注意: 対象3行すべてが本弾で解放される。dm27-026 は partial に abilities / spell が無く形Aを構築する（text は公式全文のまま使える。s_trigger は partial の keywords に既にある）。dm27-047 は partial に abilities / spell が無く **text も節の途中まで切れている**ため、reject 行の公式全文を text に戻して形Bを構築する。dmr21-002 は **partial が null で reason も無い**ため reopen では外れない（submit の直接経路を使うこと）。公式データ（by_product/r21）から全構築する: 水・コスト6・パワー6000・種族 マジック・コマンド/イニシャルズ・mana 1・keywords [double_breaker]・形C・text は reject 行の公式全文。3件とも canon は自 ID（canon_id の指定なし）だが、提出前に identity で再確認すること。提出前照合は id・alias・カード名とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml に対して行うこと。submit 後の照合（第313/315弾の教訓）で abilities・キーワード・spell をテキストと照合すること。

## ラウンド323 civilization_match 再変換

第288弾（文明の一致）の再変換。対象は civilization_match 純粋3件で、**新規登録3件・差し戻し0件**。converted 10,172 → **10,175** / rejects 2,158 → **2,155**、canonical overlap 0・漏れ0。civilization_match は残り0件でファミリー解消。

- **dm27-026 暗黒螺旋**: reopen で外し、partial（text は公式全文、keywords に s_trigger）に形Aの呪文効果を追加して登録。捨て札とマナの選択はどちらも相手自身（chooser: opp）。
- **dm27-047 デビル・スモーク**: reopen で外し、partial の text（節の途中まで切れていた）を reject 行の公式全文に戻し、形Bの呪文効果を追加して登録。
- **dmr21-002 ワルスラ・プリンスS**: reject 行は partial が null で reason も無いため reopen では外れず、submit の直接経路で登録（submit が id で reject 行を除去）。公式データ（by_product/r21: 水・コスト6・パワー6000・種族 マジック・コマンド/イニシャルズ・mana 1）から全構築し、形Cを追加。
- 提出前照合: 3件とも canon は自 ID・alias 無しを identity で再確認。id・カード名とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml に重複なし。
- submit 後の照合（第313/315弾の教訓）: 3件とも登録形の abilities・キーワード・spell・text が回答＝公式全文と完全一致し、partial 連結残り・テキスト由来の追加は無し。alias 級 stale は従来の10件のまま（本ラウンド無関係）。
- テスト: tests/test_vocab_pilot288_cards.py を登録形に書き換え（登録形の完全一致＋実挙動9件: 026＝一致で相手マナが墓地へ／不一致では不発、047＝一致でドローの諮問（受諾・辞退）／不一致では諮問なし、002＝一致で上が場に出る／異文明・呪文は手札へ／辞退で何も起きない）— `10 passed in 32.85s`。tests/test_data_audit.py — `8 passed in 65.73s`。第288弾本体 — `17 passed in 2.13s`。旧テストに対象 ID の bounce 断言は無し。
- テスト中の発見: build の deck_exact は filler と同じ defn の spec カードを取り除く（第318弾の教訓の再確認）。形Cテストで相手の山札に filler の T002 を使うと山札が0枚になりゲームが即終了したため、相手の山札は T827 に変更した。

## 第289弾 墓地シャッフル（graveyard_shuffle）

ギャップ名 graveyard_shuffle の純粋3件（dmrp10-s03 緑知銀 グィムショウ / dmx13-015 天頂のゼロ・エッグ / dmx22a-009 偽りの名 スネーク）。3件とも不足は「墓地をシャッフルして戻す」だけで、必要な部品はすべて既存だった（ギャップ名のドリフト）: move の order: shuffle は「動かす集合だけをシャッフルしてから置く」意味論で第163弾に登録先例があり、position: bottom と組で「シャッフルして山札の一番下に置く」になる。山札全体のシャッフルは {op: shuffle}。本弾は新語彙・エンジン変更なしのイディオム弾で、5形を実挙動で固定した:

- **形A（自分の墓地→一番下、T832。dmx22a-009 の攻撃時節）**: move {select: {zone: graveyard, owner: you, count: all}, to: deck, reason: put, position: bottom, order: shuffle}。既存の山札の順序は不変で、墓地の集合だけがシャッフルされて末尾に付く。墓地が空なら何も起きない。
- **形B（相手の墓地→相手の一番下、T833。dmrp10-s03 の出た時節）**: select の owner: opp 版。原文は「相手は自身の墓地をシャッフルし」だが count: all では選択が無く chooser は機械的に無関係。相手の山札の既存順序は不変、自分の山札・墓地は不変。
- **形C（自分の墓地→山札に加えてシャッフル、T834。dmx13-015 の出た時節）**: move {select: {zone: graveyard, owner: you, count: all}, to: deck, reason: put} ＋ {op: shuffle}。位置指定は全体シャッフルで無意味になるため付けない。
- **形D（どこからでも墓地に置かれた時、T835。dmrp10-s03 の第3節）**: 誘発 {when: {event: move, to: graveyard, subject: self}} の effect に形A。破壊で墓地に着いた自分自身も含め、その時点の墓地すべてが戻る（誘発は着いた後に解決する）。
- **形E（一番下の公開形、T836。dmx13-015 の第2節）**: 誘発 {when: {event: turn_start, player: you}} の effect = [move {select: {zone: deck, owner: you, from_bottom: 1}（第287弾）, to: graveyard, reason: put, as: bottom}, {op: if, cond: {exists: {ref: bottom, zone: graveyard, filter: {types: [creature], colorless: true, evolution: false}}}, then: [may [move {select: {ref: self}, to: graveyard, reason: destroy, as: fallen}, {op: if, cond: {exists: {ref: fallen, zone: graveyard}}, then: [play_free {select: {ref: bottom}}]}]]}]。「進化ではない無色クリーチャー」は filter の colorless: true（civs == [] または [zero]。色の無いことの判定は selectors 側に既存）と evolution: false で受ける。「そうした場合」のゲートは、破壊 move の as で束縛した**移動後の** ref を exists で見る（第288弾形Cと同じ）。移動前の self ref は世代が変わって一致しないため、{ref: self} のままではゲートが永遠に偽になる（実測で確認した落とし穴）。

併せて dmrp10-s03 の第2節「自分のターンの終わりに、このクリーチャーがタップしていたら、カードを1枚引いてもよい」の形も T833 の第2能力で固定した: 誘発 {when: {event: turn_end, player: you}} の effect 先頭に {op: if, cond: {exists: {ref: self, zone: bz, filter: {tapped: true}}}, then: [may [draw 1]]}。タップしていなければ諮問自体が起きない。

- **Rust**: 対象形はすべて Python パス（order: shuffle の move、turn_start/turn_end 誘発はいずれも Rust の単純形の対象外）。新規 GameState フィールドなし（state.rs 変更なし）。スキーマ再生成なし。
- プロト T832（形A）/ T833（形B＋第2節）/ T834（形C）/ T835（形D）/ T836（形E）。tests/test_vocab_pilot289.py（13件: parse（キーワード展開の static を除いた trigger 一致）、形A＝攻撃で墓地が一番下へ・既存順序不変／墓地なしでは不変、形B＝相手の墓地が相手の一番下へ・自分の山札不変、形C＝墓地が山札に混ざる（多重集合一致）、形D＝破壊されると自分を含む墓地全部が一番下へ、第2節＝タップ時はドローの諮問／アンタップ時は諮問なし、形E＝無色クリーチャーで召喚（受諾）／辞退で両方残る／有色・呪文・無色進化では諮問なし）＋ tests/test_vocab_pilot289_cards.py（2件: 対象3件の未登録・ギャップ純粋確認、提出形 parse（mana_put マクロは parse で move に展開される））。回帰: 第287・288弾本体＋test_rules＋test_rust_schema_sync 76件、test_data_audit＋第283・285・286弾本体 40件が通る。
- テスト中の発見: (1) conftest の setup は攻撃ステップから始まるため、攻撃宣言の観測は「宣言に答えた直後の最初の決定」で行うこと（ブロック決定はブロッカーがいなければ現れない）。(2) 召喚したターンは攻撃決定が現れないことがあるため、出た時節の観測は自軍の別クリーチャーの攻撃決定で行うこと（相手ターンのドローを跨ぐと山札枚数の断言がずれる）。(3) 形E の観測は相手の最初の charge までで止めること（自分の2ターン目の開始にもう一度誘発して底がもう1枚墓地に落ちる）。
- ラウンド324側の注意: 対象3行すべてが本弾で解放される。**dmrp10-s03** は partial が abilities を持たず **text も節だけに切れている**ため、reject 行の公式全文を text に戻し、形B＋第2節＋形D を構築する。**dmx13-015** は partial が abilities を持たないため形C＋形E を構築する（text と keywords [cannot_attack] は partial のまま使える）。**dmx22a-009** は partial の出た時誘発が完全なため形Aを足すだけ（alias: dmr04-004）。3件とも提出前に canon を identity で確認し、id・alias・カード名を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること。submit 後の照合（第313/315弾の教訓）で登録形の abilities・キーワード・text を公式全文と照合すること（特に submit の partial 連結とテキスト由来キーワードの追加）。

## ラウンド324 graveyard_shuffle 再変換

第289弾（墓地シャッフル）の再変換。対象は graveyard_shuffle 純粋3件で、**新規登録3件・差し戻し0件**。converted 10,175 → **10,178** / rejects 2,155 → **2,152**、canonical overlap 0・漏れ0。graveyard_shuffle は残り0件でファミリー解消。

- **dmrp10-s03 緑知銀 グィムショウ**: reopen で外し、partial の text（節だけに切れていた）を reject 行の公式全文に戻し、形B（出た時、相手の墓地をシャッフルして相手の山札の一番下）＋第2節（自分のターンの終わりにタップしていたら1枚引いてもよい）＋形D（どこからでも墓地に置かれた時、墓地をシャッフルして自分の山札の一番下）を構築して登録。
- **dmx13-015 天頂のゼロ・エッグ**: reopen で外し、abilities を持たない partial に形C（出た時、墓地をすべて山札に加えてシャッフル）＋形E（ターンのはじめ、一番下が進化ではない無色クリーチャーなら自分を破壊してもよく、そうしたらそれを召喚する）を構築して登録。text と keywords [cannot_attack] は partial のまま。
- **dmx22a-009 偽りの名 スネーク**: reopen で外し、partial の出た時誘発（1枚引いて上1枚をマナへ）は完全なため形A（攻撃時、墓地をシャッフルして一番下）を追加して登録。alias dmr04-004 は validate が identity から自動設定（canon は dmx22a-009 自身）。
- 提出前照合: 3件とも canon は自 ID を identity で確認（dmr04-004 の canon は dmx22a-009）。id・alias・カード名とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml に重複なし。reopen は対象3行のみ（巻き込みなし）。
- submit 後の照合（第313/315弾の教訓）: 3件とも登録形の abilities・キーワードが回答＝実挙動で固定した形と完全一致し、partial 連結残り・テキスト由来の追加は無し。text は s03・015 は公式全文と一致。**009 の text は rule_convert.split が None を返すため merge_split が走らず、partial の「 / 」区切り形がそのまま登録された**（内容は公式全文と区切り以外一致。変換済みカードには同形式が多数あるためそのまま）。alias 級 stale は従来の10件のまま（本ラウンド無関係）。
- テスト: tests/test_vocab_pilot289_cards.py を登録形に書き換え（登録形の完全一致＋実挙動10件: s03＝形Bで相手の墓地が相手の一番下へ／第2節はタップ時だけドローの諮問／形Dで破壊されると自分を含む墓地全部が一番下へ、015＝形Cで墓地が山札に混ざる／形Eは無色クリーチャーで召喚（受諾）・辞退で両方残る・有色では諮問なし、009＝形Aで攻撃時に墓地が一番下へ／出た時誘発で1枚引いて上1枚がマナへ）— `11 passed in 33.16s`。tests/test_data_audit.py — `8 passed in 65.73s`。第289弾本体 — `13 passed in 2.19s`。旧テストに対象 ID の bounce 断言は無し。
- 回答下書き: ~/workspace/DMPJ-work/answers/round324.yaml（reject 行の partial から決定的に構築）。

## 第290弾 敗北防止と勝利の置換（win_prevention）

ギャップ名 win_prevention の純粋3件（dmrp06-001 帰還の精霊シュマヌマージ / dmx11-001 十弐制覇 鬼「王者」 / dmr20-038 完全防御革命）。不足は3形に分解でき、うち2形は既存イディオム（第188/238弾の no_lose と第287弾の手札敗北置換）で、残りは小さなエンジン拡張2点で解けた:

- **形A（数の条件つき no_lose、T837。dmrp06-001 の敗北防止節）**: 常在型 {kind: static, if: {cmp: [{count: {zone: bz, owner: you, filter: {types: [creature]}}}, ">", {count: {zone: bz, owner: opp, filter: {types: [creature]}}}]}, no_lose: true}。dmex08-221（単一 count と定数の cmp）に登録先例があり、cmp は両辺とも式を評価する（selectors.eval_cond）ため2つの count の比較はそのまま通る。新語彙なし。「相手はゲームに勝てない」は _lose_immune の1判定で両側を兼ねる（第188弾の docstring 通り）。
- **形B（タップ中だけ no_lose、T838。dmx11-001 の敗北防止節）**: 常在型 {kind: static, if: {exists: {ref: self, filter: {tapped: true}}}, no_lose: true}。dm25bd2-003 に同一形の登録先例あり。新語彙なし。
- **形C（手札からの勝利置換、T839。dmr20-038 の第2節）**: {kind: replace, zone: hand, optional: true, when: {event: lose, reason: [deck_out, state, effect]}, instead: [{op: move, select: {ref: self}, to: graveyard, reason: discard}]}。lose の reason は direct_attack / deck_out / state / effect の4値（第188弾、LOSE_REASONS）で、「クリーチャーによる攻撃以外の方法で相手が勝つ時」は自分の敗北 reason が direct_attack でない3値のリストで正確に表せる（_lose_candidates は when.reason のリストと照合する）。手札の発生源走査は第287弾で入っており、ダイレクトアタックの敗北では諮問自体が起きないことを実挙動で固定した。
- **形D（相手の効果で山札の一番下に置かれた時、T840。dmrp06-001 の第2節）**: 誘発 {when: {event: move, to: deck, position: bottom, subject: {owner: you}, cause: {by: opp, kind: [spell, ability]}}, effect: [may [draw 1]]}。不足は2点で、本弾のエンジン拡張: (1) **move レコードに position を伝播**（events._record_for と events._apply_one の両方。片方だけでは置換照合か誘発照合のどちらかが欠ける。move op の ev は position を常に持つ）。あわせて defs.when の検証（POSITIONS）と _match_when の照合、schema.py の when プロパティに position を追加してスキーマ再生成（差分は position と cause.kind のリスト形のみ）。(2) **cause.kind のリスト形**（「呪文の効果またはクリーチャーの能力によって」。defs.when の検証・_match_when の照合・スキーマの3か所を defn のリスト形に揃えた）。position / cause を含む when は rustcore._simple_when のキー集合条件で対象外になり Python パス（実測で確認）。相手の呪文・相手のクリーチャーの能力の両方で発火し、一番上に戻す形と自分の呪文による一番下置きでは発火しないことを対照で固定した。
- **形E（選んだ獣がバトルに勝った時アンタップ、T846。dmr20-038 の第1節）**: 呪文の効果 [{op: choose, select: {zone: bz, owner: you, filter: {types: [creature]}, count: 1}, as: pick}, {op: delayed_trigger, when: {event: battle_win, subject: {ref: pick}}, duration: end_of_turn, effect: [{op: untap, select: {ref: pick}}]}]。delayed_trigger は subject: {ref: 変数} を登録時に refs へ解決し、env の vars を保持する（第279/280弾の教訓）ため、選んだ1体だけに遅延誘発が付く。新語彙なし。バトルせずプレイヤーを攻撃した場合はアンタップしないことを対照で固定した。

- **Rust**: 新規 GameState フィールドなし（state.rs 変更なし）。形D の when は Python フォールバック（_simple_when 対象外）。形A/B の static と形C の置換は従来経路。
- プロト T837（形A）/ T838（形B）/ T839（形C）/ T840（形D）/ T841（相手の呪文で一番下へ戻す駆動役）/ T842（一番上へ戻す対照役）/ T843（相手の獣の能力で一番下へ戻す駆動役）/ T844（自分の呪文で自分の獣を一番下へ戻す対照役）/ T845（効果による敗北の駆動役 {op: lose, player: you}）/ T846（形E）。tests/test_vocab_pilot290.py（18件: parse・position の検証（不正値の拒否）・cause.kind リストの検証（リスト可・単独可・不正値と空リストの拒否）・_simple_when 対象外の確認、形A＝多い時は全 reason で免疫／同数・少数では非免疫／実ゲームで効果敗北が防がれる・防がれない、形B＝タップ時だけ免疫、形C＝reason 別の候補判定／受諾で捨てて生存／辞退で敗北／ダイレクトアタックでは諮問なし、形D＝相手の呪文で発火／相手の能力で発火／一番上では不発／自分の呪文では不発、形E＝バトル勝利でアンタップ／プレイヤー攻撃ではアンタップしない）＋ tests/test_vocab_pilot290_cards.py（2件: 対象3件の未登録・ギャップ純粋確認、提出形 parse）。回帰: test_data_audit＋第188・238・287・288・285弾本体＋test_rules＋test_rust_schema_sync **112 passed**、第246・246b・256・283弾本体＋第238・188弾 cards **23 passed**。
- テスト中の発見: (1) 駆動ヘルパの on_dec が決定に答えたのに「未処理」を返すと _drive が二重に答えて IllegalAnswer になる（答えたら True、止める時は "stop" を返す規約に統一）。(2) _cast 型ヘルパの停止条件は「プレイした後」に限定しないと、ターン最初の charge 決定で即停止して何も唱えていないのに成功扱いになる。(3) 相手ターン中の観測は、相手に攻撃決定が現れる局面で止めないと自分の次のターンのドローを跨いで手札枚数の断言がずれる（攻撃できる相手クリーチャーを置いておく）。(4) setup/build は手札を指定しなければ空で始まる（opening draw で埋まらない）。
- ラウンド325側の注意: 対象3行すべてが本弾で解放される。**dmrp06-001** は partial が abilities を持たないため形A＋形D を構築するだけ（text は公式全文のまま、keywords [blocker, double_breaker] は partial のまま）。**dmx11-001** は形Bを足すだけだが、**partial の evolve_from は {types: [creature]} だけで公式全文の「ハンターとエイリアンを種族に持つクリーチャー」の条件が欠けている**ため、evolve_from: {races_all: [ハンター, エイリアン]} に補うこと（第278弾 races_all の進化元形に登録先例あり。cards テストの提出形はこの補正形で parse 済み）。**dmr20-038** は partial の **text が unsupported 節だけに切れている**ため reject 行の公式全文を text に戻し、spell に形E、abilities に形C を構築する。3件とも提出前に canon を identity で確認し、id・alias・カード名を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること。submit 後の照合（第313/315弾の教訓）で登録形の abilities・キーワード・spell・text を公式全文と照合すること。

## ラウンド325 win_prevention 再変換

第290弾（敗北防止と勝利の置換）の再変換。対象は win_prevention 純粋3件で、**新規登録3件・差し戻し0件**。converted 10,178 → **10,181** / rejects 2,152 → **2,149**、canonical overlap 0・漏れ0。win_prevention は残り0件でファミリー解消。

- **dmrp06-001 帰還の精霊シュマヌマージ**: reopen で外し、abilities を持たない partial に形A（自分のクリーチャーの数が相手より多ければ負けない常在型 no_lose）＋形D（相手の呪文の効果またはクリーチャーの能力で自分のカードが山札の一番下に置かれた時、1枚引いてもよい）を構築して登録。text・keywords [blocker, double_breaker] は partial のまま（text は公式全文）。
- **dmx11-001 十弐制覇 鬼「王者」**: reopen で外し、形B（タップされている間、負けない常在型 no_lose）を追加して登録。partial の evolve_from は {types: [creature]} だけで公式全文の「ハンターとエイリアンを種族に持つクリーチャー」の条件が欠けていたため {races_all: [ハンター, エイリアン]} に補正。
- **dmr20-038 完全防御革命**: reopen で外し、partial の text（unsupported 節だけに切れていた）を reject 行の公式全文に戻し、spell に形E（選んだクリーチャーがバトルに勝った時アンタップする遅延誘発）、abilities に形C（クリーチャーによる攻撃以外の方法で相手が勝つ時、手札から捨てて置き換える敗北置換）を構築して登録。
- 提出前照合: 3件とも canon は自 ID・aliases は空を identity で確認。id・カード名とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / converted.yaml に重複なし（proto.yaml のヒットは第290弾プロトの text 内参照のみ）。reopen は対象3行のみ（巻き込みなし）。
- submit 後の照合（第313/315弾の教訓）: 3件とも登録形の abilities・キーワード・spell・text・evolve_from が回答と完全一致し、partial 連結残り・テキスト由来の追加は無し。alias 級 stale は従来の10件のまま（本ラウンド無関係）。
- テスト: tests/test_vocab_pilot290_cards.py を登録形に書き換え（登録形の完全一致＋実挙動10件: 001＝形Aで数が多い時は全 reason 免疫・同数/少数では非免疫／形Dで相手の呪文・能力の一番下置きに発火してドロー、x11＝形Bでタップ時だけ免疫、038＝形Cの reason 別候補判定・受諾で捨てて生存・辞退で敗北／形Eでバトル勝利時にアンタップ・プレイヤー攻撃ではアンタップしない）＋第290弾本体 — `29 passed in 33.80s`。tests/test_data_audit.py — `8 passed in 63.20s`。旧テストに対象 ID の bounce 断言は無し。
- 回答下書き: ~/workspace/DMPJ-work/answers/round325.yaml（reject 行の partial から決定的に構築）。

## 第291弾 EXライフシールドの追跡（ex_life_shield_tracking）

ギャップ名 ex_life_shield_tracking の純粋3件（dm23bd1-005 頂竜連結 バジュエン・ザ・ローラ / dm23ex2-024 頂上連結 サックーヴ・ヴァッサークァ7th / dmrp17-s06 紫天連結 ネバーシデンド）。3件の partial はいずれも「『EXライフ』シールドを特定して追跡する語彙が無い」と書いているが、その照合は第190弾で実装済み（when.subject {exlife_of: self}、移動レコードの lki で移動前の紐付けと照合）で、登録先例も dmrp17-s08（離れた時、相手クリーチャーすべてをタップ＋凍結）・dm26rp1-tr009（select {exlife_of: self}）等がある。**ギャップ名のドリフト**。本弾は新語彙・エンジン変更なしのイディオム弾で、第190弾が合成 move イベントの push でしか検証していなかった離脱経路を、実際のゲーム経路で固定した。

- **共通誘発**: {kind: trigger, when: {event: move, from: shield, subject: {exlife_of: self}}}。紐付けはシールドが離れた時点で消えるため、照合はレコードの lki（第190弾）による。EXライフでない普通のシールドが割れても発火しない（第190弾の合成 push に加え、本弾でもブレイク経路で判別）。
- **形A（dm23bd1-005 の追跡節、T847）**: 共通誘発＋ ability の if {is_turn: opp}（「相手のターン中」。move レコードには player が無いため when.player ではゲートできず、eval_cond の is_turn を使う）＋ effect [tap {select: {zone: mana, owner: opp, count: all}, no_untap_next: true}]。凍結は turn.py のターン開始処理が bz と mana の両方を見るため、マナゾーンのカードにも効く。実挙動: 相手の攻撃で割れる→全マナがタップ＋凍結、次の相手のターンのはじめにアンタップしない（印は消費）、さらに次の相手のターンのはじめに通常通りアンタップ。自分のターンにバトル敗北→EXライフ置換でシールドが離れる経路ではゲートで不発（置換自体は起き、獣は場に残る）。
- **形B（dm23ex2-024 の追跡節、T848）**: 共通誘発＋ effect [tap {select: {zone: bz, owner: opp, filter: {types: [creature]}, count: 1}, no_untap_next: true}]（dmrp17-s08 の count: all を 1 にした形）。破壊呪文→置換経路と、ブレイク呪文（T850、op break）経路の両方で発火し、選んだ獣は次の相手のターンのはじめもタップしたまま。割れたシールドは持ち主の手札に加わる。
- **形C（dmrp17-s06 の追跡節、T849）**: 共通誘発＋ effect [{op: modify, select: {ref: self}, mod: {no_leave: true}, duration: end_of_turn}]。破壊→EXライフ置換でシールドが墓地に置かれた場合も誘発し、付与された no_leave が同じターンの2度目の破壊を止める（2度目はシールドが無いため置換では止められない。chars の no_leave で判別）。ブレイク経路でも同ターン中の破壊を止め、次の相手のターンには失効して破壊が通る。
- **駆動役 T850**: 呪文 {op: break, player: opp, count: 1}。攻撃ステップの後にはメインステップが無いため、「シールドが離れた同じターン中に呪文を唱える」検証には攻撃を介さないブレイクが要る。

- **Rust**: 新規 GameState フィールドなし（state.rs 変更なし）。新語彙なし、スキーマ再生成なし。誘発・凍結・no_leave はすべて従来経路。
- プロト T847（形A）/ T848（形B）/ T849（形C）/ T850（駆動役: ブレイク呪文）。tests/test_vocab_pilot291.py（8件: parse＋形の一致、形A＝ブレイクで全マナ凍結／凍結の持続と失効／普通のシールドでは不発／自分のターンでは置換経路でもゲートで不発、形B＝破壊置換経路でタップ＋凍結／凍結の持続／ブレイク経路でも発火、形C＝置換経路で no_leave 付与＋2度目の破壊を阻止／ブレイク経路で付与・次のターンに失効）＋ tests/test_vocab_pilot291_cards.py（2件: 対象3件の未登録・ギャップ純粋確認、提出形 parse）。回帰: 第190・237・287・288・289・290弾本体＋test_rules＋test_rust_schema_sync **126 passed**、test_data_audit＋第291弾 cards＋第190弾 cards **13 passed**。
- テスト中の発見: (1) 対象が1体しかいない選択（破壊呪文の対象等）は候補＝確定数で自動解決され choose_cards 決定が現れない。誘発側の選択だけを待つフックにすること。(2) 攻撃対象にできるのはタップ状態のクリーチャーだけだが、相手の獣のタップ指定は自分のターン開始処理では戻らない（アンタップはアクティブプレイヤーだけ）ため、setup 直後の直接指定で足りる。(3) parse では destroy マクロが move {to: graveyard, reason: destroy} に展開される（提出形の照合は展開形で見る）。
- ラウンド326側の注意: 対象3行すべてが本弾で解放される。**dm23bd1-005** は partial が abilities を持たないため、出た時（相手のパワー3000以下のクリーチャーをすべて破壊）＋形A を構築するだけ（text は公式全文のまま、keywords [ex_life, speed_attacker, triple_breaker] は partial のまま）。alias は dm23bd1-be003（reject 行ではない。登録時に畳まれる）。**dm23ex2-024** は partial が abilities を持たないため、シンパシー＋攻撃時＋形B を構築する: シンパシーは static {affects: self, zone: hand, mod: {cost: {amount: -1, count: {zone: shield, owner: you, filter: {face_up: true}}}, cost_min: 0}}（dm21-020 の登録先例。下限は原文「０以下にならない」どおり 0）、攻撃時は [{op: may, body: [draw 1]}, {op: play_free, select: {zone: hand, owner: you, filter: {types: [spell], race_has: 裁きの紋章}, count: 1, up_to: true}}]（「その後」はドローの成否に依らない）。**dmrp17-s06** は partial の「はじめてタップした時、アンタップする」誘発が完全なため形Cを足すだけ（submit の連結意味論、第313弾の教訓: 回答は形Cだけを足すか、タップ誘発をバイト同一で含めること）。3件とも canon は自 ID（identity で確認済み）。提出前に id・alias・カード名を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合し、submit 後に登録形の abilities・キーワード・text を公式全文と照合すること。

## ラウンド326 ex_life_shield_tracking 再変換

第291弾（EXライフシールドの追跡）の再変換。対象は ex_life_shield_tracking 純粋3件で、**新規登録3件・差し戻し0件**。converted 10,181 → **10,184** / rejects 2,149 → **2,146**、canonical overlap 0・漏れ0。ex_life_shield_tracking は残り0件でファミリー解消。

- **dm23bd1-005 頂竜連結 バジュエン・ザ・ローラ**: reopen で外し、abilities を持たない partial に出た時（相手のパワー3000以下のクリーチャーをすべて破壊）＋形A（相手のターン中、EXライフシールドが離れた時、相手のマナゾーンのカードをすべてタップし、次の相手のターンのはじめにアンタップしない）を構築して登録。text・keywords [ex_life, speed_attacker, triple_breaker] は partial のまま（text は公式全文）。alias dm23bd1-be003 は reject 行ではなく、登録時に identity から自動で畳まれた。
- **dm23ex2-024 頂上連結 サックーヴ・ヴァッサークァ7th**: reopen で外し、abilities を持たない partial にシンパシー（static {affects: self, zone: hand} の cost 形、表向きシールドの枚数だけ軽減・下限0）＋攻撃時（1枚引いてもよい。その後、裁きの紋章を手札からコストを支払わずに唱えてもよい）＋形B（離れた時、相手の獣1体をタップ＋凍結）を構築して登録。text・keywords [ex_life, double_breaker] は partial のまま。
- **dmrp17-s06 紫天連結 ネバーシデンド**: reopen で外し、partial の「はじめてタップした時、アンタップする」誘発（完全）に形C（離れた時、そのターン離れない modify 付与）を足して登録。回答はタップ誘発をバイト同一で含めた形にし、submit の連結（重複排除）後も登録形は [タップ誘発, 形C] の2件で重複なし。
- 提出前照合: 3件とも canon は自 ID（第291弾で identity 確認済み）。対象 id・alias（dm23bd1-be003）とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml に重複なし。reopen は対象3行のみ（巻き込みなし）。
- submit 後の照合（第313/315弾の教訓）: 3件とも登録形の abilities・キーワード・text が公式全文と完全一致し、partial 連結残り・テキスト由来の追加は無し。alias 級 stale は従来の10件のまま（本ラウンド無関係）。
- テスト: tests/test_vocab_pilot291_cards.py を登録形に書き換え — `5 passed in 33.91s`（登録形の完全一致＋実挙動4件: 005＝出た時でパワー3000以下だけ破壊・4000は残る／形Aでブレイク時に相手の全マナがタップ＋凍結し持続・失効、024＝形Bで破壊置換経路のタップ＋凍結、s06＝形Cで置換後に no_leave が立ち2度目の破壊を阻止）。tests/test_data_audit.py＋第291弾本体 — `16 passed in 69.22s`。旧テストに対象 ID の bounce 断言は無し。
- 回答下書き: ~/workspace/DMPJ-work/answers/round326.yaml（reject 行の partial から決定的に構築）。

## 第292弾 破壊して払う代替コスト（alternative_cost_destroy / optional_cost_reduction_with_sacrifice）

「自分のカードを破壊して払う」支払いクラスタ。alternative_cost_destroy 純粋3件（dm24ex1-003 ジェニー&ガ:ナテハ / dm26rp3-011 黎悪銃と邪煉哀の決断 / dm26rp3-sec015 同シークレット印刷）＋ optional_cost_reduction_with_sacrifice 純粋3件（dm22rp2x-038 ソー＝ゾー / dm23rp2x-004 ラーテ:ガ:フヨーキ / dm22rp2x-015 セリヴィエット＝エリー）、計6件。支払いの形そのものは既存だった（alt_cost {do} は第29弾、混合形 {cost, civs, do} は第258弾、mod sac_reduce は第201弾）が、実挙動を測ると3点の欠落があり、本弾で直した。在範の純粋ファミリーはどれも3〜4件まで痩せており、本クラスタが単独パイロットで正確に表せる最大の塊だった。

- **欠落1（alt_cost do ステップの owner）**: do ステップは selector 形だが、提示判定・候補計算・実行のいずれも step の owner を読んでいなかった。bz は共有ゾーンのため、相手のカードまで候補に入り、自分の生贄が無くても相手の獣を壊して代替コストを払えてしまった（プローブで確認: 自分の場が空でも :alt が提示され、相手の獣が支払い候補に出た）。候補計算を `_alt_step_cands` に統一し、owner（省略時 you）を honor する。あわせて defs 検証に「do ステップの owner は you/opp のみ」を追加（従来は未検証で、意味を持つようになったため）。
- **欠落2（混合形の提示判定）**: {cost, do} 混合形の提示判定は cost 側だけを見ており、do 側が払えない時も :alt が提示され、選ぶと実行時に潰れていた。提示判定で cost 側と do 側の両方を要求するよう修正。
- **形A（dm22rp2x-038、T851）**: alt_cost {cost: 1, do: [{zone: bz, owner: you, filter: {types: [creature, tamaseed]}, count: 1, to: graveyard, reason: destroy}]}（印刷5から-4）。獣でもタマシードでもよい。
- **形B（dm23rp2x-004、T852）**: alt_cost {cost: 6, do: [{zone: bz, owner: you, filter: {types: [creature]}, count: 2, to: graveyard, reason: destroy}]}（印刷9から-3）。
- **形C（dm24ex1-003、T853）**: alt_cost {cost: 2, civs: [darkness, darkness], do: [{zone: bz, owner: you, filter: {race_has: デスパペット}, count: 3, to: graveyard, reason: destroy}]}（[dd02] にする形。プロトでは種族をドールで代用）。
- **形D（dm26rp3-011 / sec015、T854）**: alt_cost {cost: 5, civs: [light, darkness, nature], do: [{zone: bz, owner: you, count: 2, to: graveyard, reason: destroy}]}（フィルタなし＝自分のエレメントなら何でもよい。[ldn05]）。
- **欠落3（sac_reduce の対象ゲート）→ dict 形 {amount, for}**: sac_reduce はディスペクター専用だった（_sac_pool の種族ゲート）。dm22rp2x-015「自分のアビスを召喚する時、コストを2少なくしてもよい。そうしたら、このクリーチャーを破壊する。ただし、そのアビスのコストは0以下にはならない」はササゲールと同文型で対象だけが違う。dict 形 {amount: 2, for: {race_has: アビス}} を追加: chars に内訳リスト **sac_gated**（[amount, for]）を持ち、適用判定では召喚先の**印刷特性**（printed chars: power/cost/civs/types/races/keywords/name）に for を照合する。int 形の意味は不変（ディスペクター専用）。見積もり（_can_play_face）・諮問（h_play）・最終計算の3経路すべてが同じ _sac_applicable を通る。
- **支払い0の修正（_mana_choices）**: 実効コスト0で [[]]（支払いなし）を返す早期分岐が「文明なし」の時だけだったため、文明を持つカードを0まで軽減すると、文明を満たすマナの組が存在せず払えなかった。コスト0なら支払い自体が無い（文明条件はタップするマナへの条件）として一律 [[]] を返すよう統一した。ササゲール／セリヴィエットの「0以下にはならない」は0での召喚を許す読みで、形Eの床テスト（コスト3を2体で軽減しマナ0枚で召喚）がこれに依存する。
- **既存 dict 形の発見（検証・スキーマの2系統化）**: 登録済みの dmex01-042 逆襲の支配者 ニュー・ディアボロス が sac_reduce {amount: 5, cost_min: 4}（自己受益・下限つき）を使っており、本弾の検証追加で一瞬 parse 不能になった（test_data_audit が検出）。dict 形は {amount, for} と {amount, cost_min} の2系統として defs 検証とスキーマ（anyOf）の両方で受理し、集計は amount を合計に入れ、sac_gated には {amount, for} だけを入れる。なお {amount, cost_min} の実行時挙動（自分の獣を好きな数破壊する諮問・下限4）は従来から sac 経路に接続されておらず、本弾では触らない（別件の潜在ギャップとして記録のみ）。
- **Rust**: 新規 GameState フィールドなし（state.rs 変更なし）。chars に sac_gated を追加したため rust/dmcore/src/engine.rs の chars 既定 JSON に "sac_gated": [] を同期。スキーマ再生成済み（差分は sac_reduce の anyOf のみ）。
- プロト T851（形A）/ T852（形B）/ T853（形C）/ T854（形D、本体は2ドローの代用）/ T855・T856（役カード: タマシード生贄・ドール生贄）/ T857（形E: dict 形の生贄）/ T858（形Eの召喚先アビス）/ T859（対象外の召喚先）/ T860（床を見る召喚先）。tests/test_vocab_pilot292.py（16件: parse＋形の一致、検証拒否3形、形A＝自分の獣/タマシードで支払い・候補は自分だけ・生贄なしでは提示されない・通常召喚では生贄が残る、形B＝2体破壊で6払い・1体では提示されない、形C＝自分のドール3つ＋[dd02]・2つでは提示されない、形D＝エレメント2つ＋[ldn05]で本体解決・1つでは提示されない、形E＝一致時のみ提示され-2・辞退で全額・対象外は見積もりにも入らない・2体で床0）＋ tests/test_vocab_pilot292_cards.py（2件: 対象6件の未登録・ギャップ純粋確認、提出形 parse）。回帰: 第29・56・57・167・172・177・201・209・258弾＋test_cost＋test_data_audit＋test_rust_schema_sync **71 passed / 2 failed**（失敗は test_data_audit の2件で、上記 {amount, cost_min} 既存形との検証衝突。2系統化の修正後に test_data_audit＋第292弾一式で **26 passed**、test_rules＋test_cost＋第29・201・209・258弾＋test_rust_schema_sync で **65 passed**）。
- ラウンド327側の注意: 対象6行すべてが本弾で解放される。**dm22rp2x-038 / dm23rp2x-004** は partial に alt_cost（形A/形B）を足すだけ（004 の abilities は完全、keywords は partial のまま）。**dm24ex1-003** は partial の CIP 誘発（相手の手札を2枚見ないで選び捨てさせる）が同一内容で2重に入っているため、畳んでから形Cを足すこと。**dm22rp2x-015** は abilities を持たない partial に CIP（{op: may, body: [自分の手札を1枚捨てる, 相手が自身の手札を1枚選んで捨てる（select の chooser: opp）]}）＋形Eの静的を構築する。**dm26rp3-011 / sec015** は partial の text が「自分のエレメントを２つ破壊し、支払って唱えてもよい」で切れており本体も無いため、公式全文（[ldn05] を含む。cards テストの OFFICIAL_011 と同一で両印刷で同文）に差し替え、形D＋モーダル本体（次の中から2回選ぶ・同じものを選んでもよい = {op: modal, count: 2, repeat: true}）を構築すること。モーダルのモード2（コスト9以下の進化でない獣を手札から出し、ターンの終わりに破壊する）は play_free {as: entered} ＋ delayed_trigger {when: {event: turn_end}, effect: [destroy {ref: entered}]} の先例形（ニンジャ・ストライク）で parse は通るが、辞退時（up_to で0体選んだ時）の entered 空束縛の挙動はラウンドで実挙動を確認すること。sec015 は 011 のシークレット印刷 — canon は identity で確認し、011 が canonical なら sec015 は alias に畳まれる想定。提出前の id・alias 照合（real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted）と、submit 後の登録形（abilities・キーワード・text）の公式全文照合はいつもどおり行うこと。

## ラウンド327 破壊して払う代替コスト 再変換

第292弾（alternative_cost_destroy / optional_cost_reduction_with_sacrifice）の再変換。対象は純粋6件で、**新規登録5件・alias 畳み込み1件・差し戻し0件**。converted 10,184 → **10,189** / rejects 2,146 → **2,140**、canonical overlap 0・漏れ0。両ギャップとも残り0件でファミリー解消。

- **dm22rp2x-038 ソー＝ゾー**: reopen で外し、partial に形Aの alt_cost（自分の獣/タマシード1つを破壊して cost 1）を足して登録。keywords・text は partial のまま。
- **dm23rp2x-004 ラーテ:ガ:フヨーキ**: partial に形Bの alt_cost（自分の獣2体を破壊して cost 6）を足して登録。abilities（W・メクレイド8＋スレイヤー付与）は partial のまま完全。
- **dm22rp2x-015 セリヴィエット＝エリー**: abilities を持たない partial に CIP（自分の手札を1枚捨ててもよい。そうしたら、相手は自身の手札を1枚選んで捨てる。相手の選択は chooser: opp）＋形Eの静的（sac_reduce {amount: 2, for: アビス}）を構築して登録。text は partial のまま（文の連結形。第324弾の先例どおり）。
- **dm24ex1-003 ジェニー&ガ:ナテハ**: partial の重複 CIP を畳み、形Cの alt_cost（自分のデスパペット3つを破壊して [dd02]）を足して登録。**submit 後の照合で merge_split 由来の二重登録を検出**: split が本文から起こした CIP（「見ないで選び」= chooser: random 付き）が partial 由来（chooser 無し）と非同一 dict のため重複排除されず、登録形は CIP が2件になっていた。本文に合う chooser: random 形（変換済み128件の先例どおり）だけを残し、もう一方を converted.yaml から外科的に除去した（cardstore.write で再書出しし、差分は新規5件のみに収まることを git diff で確認）。
- **dm26rp3-011 黎悪銃と邪煉哀の決断**: partial の text が切れ本体も無かったため、公式全文（[ldn05] を含む）に差し替え、形Dの alt_cost（自分のエレメント2つを破壊して [ldn05]）＋モーダル本体（2回選択・同選択可）を構築して登録。**モード3の修正**: 「エレメントを２つまで選び、破壊する」は無資格のため両プレイヤーのエレメントが対象（dm23-031 等の先例で owner: any）。第292弾の提出形は owner 省略（= you のみ）で、提出前の実挙動プローブで相手のエレメントが候補に出ないことを検出し、owner: any に修正した。**モード2の辞退時検証（ラウンド必須）**: up_to で0体選んだ場合、entered 空束縛の delayed_trigger がターン終わりに発火しても潰れず、何も破壊されないことを実挙動で確認（2回とも辞退・1体出してターン終わりに破壊・モード1・モード3・代替コスト経路の5シナリオ）。
- **dm26rp3-sec015**: 011 のシークレット印刷（同一本文）。canon は identity で dm26rp3-011 と確認したため提出せず、011 の登録時に validate の aliases_for で alias として畳まれた（reopen で外した reject 行は戻らず、漏れなし）。
- 提出前照合: 対象 id・alias とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml に重複なし。reopen は対象6行のみ（巻き込みなし）。submit は一括1回で全5件 ✓（lint 警告なし）。
- テスト: tests/test_vocab_pilot292_cards.py を登録形に書き換え — `11 passed in 44.02s`（登録形の完全一致＋実挙動10件: 038＝形Aで自軍だけ破壊し1マナ支払い、004＝形Bで2体破壊し6マナ、015＝CIP（相手自身が選ぶ捨て札）＋形Eでアビス召喚-2、003＝CIP は1回だけ（相手の墓地2枚）＋形Cでデスパペット3つ破壊し [dd02]、011＝モード2辞退×2の安全性／出した獣のターン終わり破壊／モード3で相手＋自分のエレメント破壊／代替コストで2つ破壊し5マナ）。tests/test_vocab_round327_cards.py — `1 passed in 14.73s`。tests/test_data_audit.py — `8 passed in 86.02s`。旧テストに対象 ID の bounce 断言は無し（第292弾 cards 以外に対象 ID の参照なし）。
- 回答: ~/workspace/DMPJ-work/answers/round327.yaml（reject 行の partial＋第292弾 cards テストの定数から決定的に構築。モード3 の owner: any 修正を含む）。

## 第293弾 進化元のゾーン拡張（graveyard/mana/hand/shield evolution V・GV、進化GV・Ω、デッキ進化GV、超無限の各形）

進化元をバトルゾーン以外から取る進化のクラスタ、純粋26件。内訳: 墓地進化V 3件（dm22ex2-003 / dm26ex2-027 / dm38-027）、マナ進化V 3件（dm28-s01 / dm28-s05 / dmc55-021）、手札進化V 1件（dm34-002）、墓地進化GV 3件（dm25ex1-044 / dm26ex2-mc005 / dmc66-008）、マナ進化GV 3件（dm23bd4-017 / dm28-s09 / dmc63-009）、手札進化GV 1件（dm25ex1-023）、シールド進化GV 1件（dm25ex1-016）、デッキ進化GV 3件（dm22ex2-4a / dm25ex1-010 / dmartkiwami03-005）、進化GV・Ω 2件（dm23ex3-tr07 / dm26ex2-mc009）、超無限進化・Ω 2件（dm24bd5-012 / dm23ex3-tr02）、超無限墓地進化 2件（dm26ex2-pr003 / dmr20-s04）、超無限進化 2件（dm26ex4-sec009 / dm26ex1-011）。土台の機構（evolve_zone / evolve_count / evolve_any / evolve_zones、非bz進化元の _raw_move→_stack、支払い時の進化元除外）は第95・173・218・231弾で入っており、墓地進化GV・マナ進化（単体）には登録済み先例もある。本弾の実質は (1) 未検証だった形の実挙動固定、(2) フィルタ別ゾーン（形C）とデッキ進化GV（形D）の新規実装、(3) 「N体まで」形の evolve_max（形B'）とシールド進化の進化元範囲の是正。なお第292弾が記録した sac_reduce {amount, cost_min} の未接続は本弾では扱わない（ブロックされている reject 行が無く、登録済み dmex01-042 の挙動修正だけの単独ステージ向き）。

- **形A（進化V＋ゾーン）**: evolve_from リスト形＋evolve_zone: graveyard/mana/hand。h_play の V 分岐・_evo_v_ready・_can_play_face はすべて _evo_pool 経由でゾーン対応済みだったことを T861（墓地）/ T862（マナ）/ T863（手札）で実挙動固定した。マナ進化V は進化元に選んだマナが支払いから除外される（第218弾Ωの除外機構）こともあわせて確認。
- **形B（進化GV＋ゾーン）**: evolve_count: 3＋evolve_zone: mana（T864）/ hand（T865）/ shield（T866）。graveyard は登録済み先例（dmpcd03-b02 / dmx11-043）があるため再検証のみ。**シールドのプール是正**: _evo_pool をゾーン単位の `_evo_pool_zone` に分解し、シールドは (a) 束の下のカードを選べないよう top_of < 0 のトップだけ、(b) 進化元が「カード」全般（dm25ex1-016 の原文）なので 801.1a のクリーチャー絞り込みをせず evolve_from フィルタに委ねる（呪文シールドも重ねられる。T881 で固定）。クリーチャー指定のシールド進化はフィルタ {types: [creature]} で従来どおり絞れる（T866）。
- **形B'（「N体まで」形）→ 新フィールド evolve_max**: dm28-s09 は「自然のクリーチャーを３体まで」で、evolve_any（1体以上無制限）とも evolve_count（ちょうどN）とも違う。面フィールド **evolve_max: int**（evolve_any 必須。defs 検証・Face/Card 両 dataclass・parse 配線・schema.py の面項目・dataaudit _STRUCT_FIELDS に登録し、スキーマ再生成＝差分は evolve_max ×2）を追加。選択の上限は h_play 通常分岐の mx、見積もりは _can_play_face と _evo_base_reduced の n を min(len, evolve_max) で頭打ちにする。T880 で「候補9体でも max 3・2体だけ重ねてもよい」を固定。GameState フィールドではないため Rust state.rs の変更なし（test_rust_schema_sync は通過）。
- **形C（進化GV・Ω）→ フィルタ別ゾーン**: 「墓地、マナゾーン、バトルゾーンから1体ずつ」は evolve_zones（どのゾーンからでも1体以上）では表せない。evolve_from の各フィルタに書ける `zone` キーは、従来 defs 検証とスキーマ（FILTER_KEYS | {"zone"}）で受容されながら実行側では剥がして捨てていた（＝書いても無意味だった）。本弾で honor する: `_evo_filter_pool`（フィルタに zone があればそのゾーンだけのプール、無ければ面のプール全体）を新設し、_evo_sources のリスト形・_evo_v_ready・h_play の V 分岐が使う。defs 検証に zone 値の検査も追加（従来は無検査で剥がしていた）。T867 で各ゾーンから1体ずつの重ねと、「墓地に元が無ければ bz に3体いても出せない」ゾーン強制を固定。
- **形D（デッキ進化GV）→ deck_evolution {stack_all: true}**: 「山札の上から3枚の上に重ねる（裏向きのまま見ないで）」は第173弾の deck_evolution（めくって1体選ぶ形）では表せない。キー **stack_all** を追加（defs 検証に bool 検査）。h_play のデッキ分岐で、公開も選択もせず上から count 枚すべてを t["evo"] にする（上の1枚が直下）。_can_play_face は山札が count 枚未満では出せないようゲート（通常のデッキ進化は「空でなければ試みられる」とは別扱い）。T868 で「トップ3が順序どおり下に入る・choose 系の decision が出ない・山札2枚では出せない」を固定。
- **形E（超無限の各形はドリフト）**: 超無限進化・Ω＝evolve_zones＋evolve_any（T869: マナだけの元でも、墓地の元でも出せる）、超無限墓地進化＝evolve_zone: graveyard＋evolve_any（T870: 2体選択）、超無限進化（コスト合計）＝evolve_total_cost_ge＋{any_of: [race_has コマンド, race_has ドラゴン], not_types: [evolution]}（T871: 進化クリーチャーは元になれない）はいずれも既存語彙で足りることを実挙動で固定した。新規語彙なし。
- **発見した既存の競合（本弾の範囲外・未修正）**: tests/test_vocab_pilot274.py::test_floor_zero_colored_pays_civ_count が HEAD（da2c22b）時点で落ちる。第292弾の _mana_choices 変更（実効コスト0なら文明持ちでも支払いなし [[]]）が、第274弾の固定した 112.2b 解釈（有色カードは0まで軽減しても文明数ぶんタップする）と正面から競合しており、第292弾の回帰バッチに第274弾が含まれていなかったため顕在化しなかった。本弾の変更とは無関係（stash で HEAD に戻して再現確認済み）。どちらの読みを採るかは単独ステージで判断すること。
- プロト T861（形A 墓地V）/ T862（形A マナV）/ T863（形A 手札V）/ T864（形B マナGV）/ T865（形B 手札GV）/ T866（形B シールドGV・クリーチャー指定）/ T867（形C GV・Ω）/ T868（形D デッキGV）/ T869（形E ∞Ω）/ T870（形E ∞墓地）/ T871（形E コスト合計）/ T880（形B' マナGV まで形）/ T881（形B シールド・カード全般）＋役カード T872–T879（闇/光/水/ドラゴン/火の進化元、コスト5ドラゴン/コマンド、進化ドラゴン）。tests/test_vocab_pilot293.py（19件: parse＋形の一致、検証拒否（未知ゾーン・stack_all 非bool・未知キー・evolve_max 単独/evolve_max 0）、形A×3、形B×3＋シールド不足の否定、形B'（上限3・2体可）、シールド全般（呪文シールドを重ねる）、形C（各ゾーン1体・ゾーン強制の否定＋対照）、形D（トップ3・選択なし・枚数不足の否定＋対照）、形E×4）＋ tests/test_vocab_pilot293_cards.py（2件: 対象26件の未登録・ギャップ純粋確認、partial＋本弾の面フィールドの提出形 parse）。回帰: 第95・173・218・231・232・234・236・249・274・293弾＋test_rules＋test_rust_schema_sync = **109 passed / 1 failed**（失敗は上記の既存競合 test_vocab_pilot274 の1件のみで、本弾の変更前から落ちることを確認済み）。
- **監査修正（コミット後に判明・追随修正）**: T881 の `evolve_from: {}`（シールド進化・カード全般）が dataaudit の evo_no_source に新規違反として検出された（test_no_new_data_violations が落ちる）。`{}` は「進化元フィルタなし＝カード全般」の明示宣言なので、dataaudit の同規則を「辞書形の evolve_from は空でも進化元ありと数える（リスト形は非空のみ）」に修正。修正後 test_data_audit **8 passed**。ラウンド328 で dm25ex1-016 を同形で登録する際もこの修正が前提になる。
- ラウンド328側の注意: 対象26行すべてが本弾で解放される見込みだが、**多くの partial は骨格のみ**（types に evolution が無い、abilities が無い、text が切れている等）で、ラウンドは公式全文から不足分を構築すること。行ごとの注意: **dm25ex1-010 / 016 / 023 / 044** の第1行「自分のマナゾーンにあるカードとエレメントが合計5つ以上、種族にXまたはフェニックスを持っていれば [文明コスト] 支払って召喚してもよい」は代替召喚コスト節で、partial に無いため公式文から構築する（表現できない場合はその節を新ギャップに差し戻す）。**dm28-s09** は partial の text が「マナ進化GV」だけに切れ power も 0 の仮置き: 公式全文（下に重ねたカードの合計パワーを持つ＋パワー帯でブレイカーが増える常在型つき）から全構築する。**dm26ex4-sec009** は partial に「自分のコマンドまたはドラゴンが出た時、手札から出してもよい」誘発とエクストラEXライフのキーワードが欠けている。**dm26ex1-011** は partial の無い note 行: 公式データ（26ex1）から全構築し、メガメテオバーン10「そうしたら、自分はゲームに勝つ」が別ギャップになるかラウンドで判定する。**dmartkiwami03-005** は dm25ex1-010 の再刷り: canon は identity で確認し、canon でない側は alias に畳む。alias は partial の source.aliases（dm26ex2-mc005 → dm23rp3-tr06 / dmpcd03-b01、dmc66-008 → dm34-s03、dm23bd4-017 → dm34-005 ほか5件）を提出前に id・alias とも照合すること。提出形の進化面は cards テストの FORMS が正本。

## ラウンド328 進化元のゾーン拡張 再変換

第293弾（graveyard/mana/hand/shield evolution V・GV、進化GV・Ω、デッキ進化GV、超無限の各形）の再変換。対象は純粋26件で、**新規登録18件・alias 畳み込み1件・stale 解消2件・差し戻し5件**。converted 10,189 → **10,207** / rejects 2,140 → **2,119**、canonical overlap 0・漏れ0。第293弾の12ギャップは rejects に残り0件でファミリー解消。

- **愛銀河の代替コスト（dm25ex1-044 / 023 / 016 / 010）**: partial に無い第1行の代替召喚コスト節は、dm25ex1-050 の登録先例形（alt_cost {cost, civs: [同文明×2], if: マナゾーンのカード＋バトルゾーンのエレメントで対象種族またはフェニックスが合計5以上}）で4件とも表現でき、全件登録。[dd02] 闇（シノビ）/ [ww03] 水（サイバー）/ [ll04] 光（エンジェル・コマンド）/ [ff03] 火（ファイアー・バード）。
- **dm26ex1-011 無限銀河ジ・エンド・オブ・ユニバース**: partial の無い note 行を公式データ（26ex1）から全構築。メガメテオバーン10の「そうしたら、自分はゲームに勝つ」は dmr13-s01 の登録先例形（may＋move 10枚＋count==10 で win）で表現でき、別ギャップにせず登録。実挙動で勝利まで確認。identity alias 3件（dm23rp1-tr3 / dmex01-022 / dmex08-283）を併記。
- **dmartkiwami03-005**: dm25ex1-010 の再刷り（canon は identity で dm25ex1-010）。提出せず、010 の登録時に alias として畳まれた。
- **stale 解消2件**: **dmc66-008** は canon dmpcd03-b02（大邪眼B・ロマノフ）が変換済みで本文・コスト・パワー一致のため、dmc66-008 と dm34-s03 を dmpcd03-b02 の source.aliases に外科的に追加し reject 行だけ除去。**dm26ex4-sec009** は canon dm26ex4-012 の alias に既存だったため reject 行の除去のみ（012 の登録形が手札誘発＋唱えられない常在を持つことも併せて確認）。
- **submit で差し戻し2件**: **dm28-s01 → super_shield_plus**（既存ギャップ）: マナ進化Vの面は形Aで解けたが、スーパー・シールド・プラス（全シールドの下に1枚ずつ）は shield_plus op が1つのシールド対象でしかなく表現できない。面＋W・ブレイカーを partial に銀行。**dm26ex2-pr003 → per_evolution_base_cost_reduction**（新規ギャップ）: 「進化元クリーチャー1体につき1少なくする」は evo_base_reduce が一律形（マッチしたら amount を1回だけ引く）のみで、体数比例が無い。超無限墓地進化の面＋メテオバーンを銀行。
- **提出後に登録を取り消して差し戻し3件**（いずれも実挙動・コード照合で検出。解けた節は partial に銀行し、reject 行は submit の差し戻し行と同じ形で再構成した）:
  - **dm24bd5-012 → was_under_cards_return**（既存ギャップ、dm25rp2-033 と同じ欠落機構）: 離脱誘発 {when: move from bz, subject: self} の effect で under_of: self を引く形は、離脱時点で対象カードの under が解体され（_raw_move が c.under を消す）gen も進む（_under_base の alive 判定で落ちる）ため、解決時に必ず空になる。「下にあったカード」を指す selector が無い。
  - **dm26ex2-mc009 → exlife_shield_left_any**（新規ギャップ）: 「自分の『EXライフ』シールドが離れた時」は所有者＋exlife の subject フィルタで書いたが、_match_when は from: shield のレコードに LKI を渡さず（from: bz か subject に exlife_of キーがある時だけ）、filter の exlife は離脱後の実カード（exlife_of は移動で消える）しか見ないため一致しない。exlife_of は特定クリーチャーへの紐付け照合のみで「自分のEXライフシールド全般」は書けない。進化GV・Ω面＋エクストラEXライフ＋G・ストライク付与は銀行。
  - **dm28-s09 → static_if_own_current_power**（新規ギャップ）: ブレイカー帯（6000/12000/18000）の常在条件に power_of: self を使ったが、常在条件の評価は再帰防止のため印刷特性で行われ（_static_cond／_chars_busy）、印刷パワー0しか読めないため永遠に付与されない。「パワーは下のカードの合計」常在自体は動作する（実挙動で 6000 を確認）。合計への読み替えは外部のパワー修正で乖離するため採らない。進化面（evolve_max: 3）＋合計パワー常在は銀行。
- **登録形の修正2件**（実挙動テストで検出）: **dm28-s05** のターン開始誘発は subject: self では turn_start レコード（subject を持たない）に一致しないため、登録先例74件の player: you 形に修正（自分のターン開始でのみ相手が自軍の場/マナから1枚選んで墓地に置くことを実挙動で確認）。**dm22ex2-003** の攻撃者コスト参照は attack レコードに attacker キーが無いため cost_of: event.subject に修正（自分のドラゴンの攻撃で、攻撃者よりコストが1小さい闇クリーチャーを墓地から出すことを実挙動で確認。ドラゴンでない自軍の攻撃では誘発しない対照つき）。
- **マージ由来混入の除去1件**: dm34-002 の keywords に merge_split が meteor_burn（離脱置換キーワード）を足していた。本文のメテオバーンは攻撃中止形で別能力のため除去し [double_breaker] のみにした。
- **発見した既存の問題（本ラウンドの範囲外・未修正）**: dm21-s04 のターン開始誘発も {event: turn_start, subject: self} 形で、turn_start レコードに subject が無いため一致せず死んでいる（本ラウンドで dm28-s05 を直す際に判明）。同形の登録済みカードが他にもある可能性があり、棚卸しは単独ステージ向き。
- 提出前照合: 対象 id・alias とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml に重複なし（stale 2件と dm22ex2-007＝pr003 の alias が real.yaml の ID である件は無害と確認）。reopen は対象25行のみ（dm26ex1-011 は reason 無しのため残り、直接 submit で除去）。submit は一括1回で21件 ✓・差し戻し2件（lint 警告3件は play_free の助言で、「出す」は召喚意味論のため登録形が正）。
- テスト: tests/test_vocab_round328_cards.py＋tests/test_data_audit.py — **14 passed in 83.96s**（内訳: round328 = 帰属・登録形＋実挙動5件［011 メガメテオバーン10で勝利、s05 ターン開始の自分ターン限定、003 ドラゴン攻撃で墓地から召喚／非ドラゴンの対照］、data_audit = 8件）。差し戻し5件は銀行 partial の形を帰属テストで固定。
- 回答: ~/workspace/DMPJ-work/answers/round328.yaml（reject 行の partial＋第293弾 FORMS＋公式全文から決定的に構築。提出後の取消3件・修正2件・混入除去1件を含む最終状態は converted.yaml / rejects.jsonl と本節が正）。
- 次の番号: パイロット294 / ラウンド329 / プロト T882。

## 第294弾 「下にあったカード」（was_under_cards_return）

ギャップ名 was_under_cards_return の純粋4件（dm25rp2-033 ～時空の工兵～ / dmex12-004 デュエにゃん皇帝 / dmex12-037 超轟速 レッド・エンド / dm24bd5-012 氷結龍 ダイヤモンド・クレバス）。共通条項は「破壊された時／離れた時、下にあったカードを墓地から手札に戻す・出す／手札に加える」で、不足は1点だけ: クリーチャーが下のカードを連れて離れた後、その「下にあったカード」を指す語彙が無い。離脱時点で束は解体され生成も進むため under_of: self は解決時に必ず空になる（ラウンド328で dm24bd5-012 がこの理由で差し戻された）。本弾はレコード側に LKI として下のカードの列を持たせる。

- **新レコード項目 was_under**（dmsim/engine/events.py）: 一緒に離れる下のカードすべての参照列。収集レコード（_apply_one）は移動後の参照で、under_lkis のうち実際に行き先へ動いた分だけを載せる。照合用レコード（_record_for）は移動直前の参照で対にする（両ビルダに載せるのが基盤の作法）。載せる条件は under_lkis の収集条件と同一: （bz から bz 以外へ）または（シールドから bz・シールド以外へ）。card_only／スター進化の再構築で下が場に残る場合は載せない（_record_for 側も card_only と star を見て除外する）。シールドの束が一緒に動く場合も同じ項目で指せる。
- **新 ref 参照 event.was_under**（dmsim/engine/selectors.py の ref 経路）: レコードの was_under（参照の列）そのものを対象にする。既存の event.under（leave_under_untap の単体形）と対の複数形。ref 経路の既存作法で filter と zone の併記が効くため、「墓地から」「種族で絞る」がそのまま書ける。alive（生成一致）で落とすため、解決前に別の移動をした下カードは自動で外れる。Rust の _simple_selector は event. 参照を一律に対象外にしているため、この形を使う対局は自動で Python にフォールバックする（eternal_kappa 等と同じ）。新規の GameState フィールド・op・面フィールドは無し（state.rs・スキーマ再生成は不要。ref は自由文字列で defs/schema とも無変更）。
- 形A（dm25rp2-033）: 破壊トリガー＋ move {select: {ref: event.was_under, zone: graveyard}, to: hand, reason: return}。「すべて」は ref セレクタの count 省略（全件・選択なし）で表す。墓地にあっただけのカードは was_under に含まれないため戻らない。
- 形B（dmex12-004）: 破壊トリガー＋ play_free {select: {ref: event.was_under, zone: graveyard, filter: {race_has: ファンキー・ナイトメア}}}。下にあったが種族が合わないカード、下に無かった同種族の墓地カードはどちらも出ない。
- 形C（dmex12-037）: 破壊トリガー＋ may {play_free {select: {ref: event.was_under, zone: graveyard, count: 1}}}。辞退すれば何も出ない。
- 形D（dm24bd5-012）: 離脱トリガー {event: move, from: bz, subject: self}（行き先・理由を問わない）＋ move {select: {ref: event.was_under, zone: [graveyard, mana, deck, shield]}, to: hand, reason: return}。一緒に手札へ離れた分は元々手札にいるため select の zone から hand を外して二重移動しない（バウンスで本体と下が全て手札に残ることを実挙動で固定）。本体がマナへ置かれた場合は下だけが手札に加わる。
- プロト T882（形A。dm25rp2-033 のターン終了の下置きも partial の形のまま併せ持つ）/ T883（形B。攻撃の終わりの下置きも併せ持つ）/ T884（形C）/ T885（形D）＋役カード T886（ファンキー・ナイトメアの下カード）/ T887（形D の対照: 下を持たない通常クリーチャーでは何も起きない）/ T888・T889（形D のバウンス／マナ送りドライバ呪文）。tests/test_vocab_pilot294.py（12件: parse＋形の一致、event 無し文脈では空、_record_for の was_under 搭載／card_only・bz 行きでは不搭載、形A×2［破壊で回収・下置き実経由で2枚とも回収］、形B［攻撃→下置き→破壊で下のファンキーだけ出撃］、形C×2［1枚選んで出す／辞退］、形D×3［破壊／バウンス／マナ送り］、対照）＋ tests/test_vocab_pilot294_cards.py（2件: 対象4件の未登録・純粋確認、partial＋本弾条項の提出形 parse）。
- ラウンド329側の注意: 対象4行すべてが本弾で解放される見込み。提出形は cards テストの ADDITIONS が正本（partial にトリガーを1つ足し、unsupported から was_under_cards_return を外すだけ。他の節は partial のまま）。alias は提出前に id・alias とも照合すること（033 → dm25rp2-sec19、004 → dmex08-121 / dmr19-005、037 → dmex08-217 / promoy14-045、012 → dm23rp1-tr7 / dm24ex1-006 / dmex12-s15）。dm24bd5-012 はラウンド328で一度登録→取消された行で、partial の notes に経緯がある（進化面とパワー常在は銀行済み）。submit は partial の abilities と回答を連結するため、登録後に abilities の件数・内容を本文と照合すること。

## ラウンド329 「下にあったカード」再変換

第294弾（was_under）の再変換。対象は was_under_cards_return 純粋4件で、全件登録（差し戻し0件）。

- **新規登録4件**: dm25rp2-033 ～時空の工兵～（形A: 破壊された時、下にあったカードをすべて墓地から手札に戻す）/ dmex12-004 デュエにゃん皇帝（形B: 破壊された時、下にあったファンキー・ナイトメアをすべて墓地から出す）/ dmex12-037 超轟速 レッド・エンド（形C: 破壊された時、下にあったカードのうち1枚を墓地から出してもよい）/ dm24bd5-012 氷結龍 ダイヤモンド・クレバス（形D: 離れた時、下にあったカードをすべて手札に加える。ラウンド328で同ギャップに差し戻された行で、銀行済みの進化面＋パワー常在に形Dトリガーを足して登録）。
- 提出形は第294弾 cards テストの ADDITIONS が正本どおり（partial にトリガーを1つ足し、unsupported から was_under_cards_return を外すだけ。他の節は partial のまま、公式全文からの追加構築なし）。partial の text は4件とも公式全文と一致していた。
- alias 畳み込みは無し（alias は各カードの source.aliases として登録時に併記: 033 → dm25rp2-sec19、004 → dmex08-121 / dmr19-005、037 → dmex08-217 / promoy14-045、012 → dm23rp1-tr7 / dm24ex1-006 / dmex12-s15。alias id 自体の reject 行は無かった）。
- 提出前照合: 対象 id・alias とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml に重複なし。reopen は対象4行のみ除去。submit は一括1回で4件 ✓（lint 警告2件は dmex12-004 / dmex12-037 の play_free への助言で、「出す」は召喚意味論のため登録形が正。第328弾の submit でも同じ助言が出て登録形を正とした先例あり）。
- 登録後の照合: 4件とも abilities の件数・内容とキーワードを本文と照合し、マージ由来の混入・重複は無し（033 = ターン終了の下置き＋形A、004 = 侵略 declare＋攻撃終了の下置き＋形B、037 = 侵略 declare＋形C、012 = パワー常在＋形D）。
- テストブックキーピング: tests/test_vocab_pilot294_cards.py を登録形に書き換え。tests/test_vocab_round328_cards.py の dm24bd5-012 の差し戻し断言（BOUNCED と銀行 partial の検証）を登録済みに合わせて更新。**既存の stale（本ラウンド起因ではない）: tests/test_vocab_pilot293_cards.py はラウンド328時点で既に落ちていた**（対象26件の未登録を断言するパイロット段階テストで、ラウンド328の登録後に書き換えられていない。HEAD 2ac920c でも再現）。
- テスト: tests/test_vocab_round329_cards.py＋tests/test_data_audit.py — **13 passed in 81.88s**（round329 = 帰属＋実挙動4件［形A 回収と墓地のみカードの対照、形B 下のファンキーだけ出撃、形C 1枚選んで出す、形D 破壊で下が全て手札］、data_audit = 8件）。tests/test_vocab_pilot294_cards.py（登録形）— **2 passed in 11.93s**。tests/test_vocab_round328_cards.py（更新後）— **6 passed in 31.52s**。
- ラウンド直後: converted 10,207 → **10,211** / rejects 2,119 → **2,115**、canonical overlap 0・漏れ0。was_under_cards_return は rejects に残り0件でファミリー解消。
- 回答: ~/workspace/DMPJ-work/answers/round329.yaml（reject 行の partial＋第294弾 ADDITIONS から決定的に構築）。
- 次の番号: パイロット295 / ラウンド330 / プロト T890。

## 第295弾 スーパー／ウルトラ・シールド・プラス（super_shield_plus）

ギャップ名 super_shield_plus の純粋3件（dmex06-010 奇跡の精霊ネオ・ミルザム / dmx19-s06 奇跡の精霊ミルザム / dm28-s01 超神龍ラディオ・ヤエサル。dm28-s01 は第293弾のマナ進化Vがラウンド328で解けた後にこの節だけで差し戻された行）。共通条項は「バトルゾーンに出た時、自分の山札の上から裏向きのまま、自分のシールドの下に置いてもよい」で、既存 op **shield_plus**（第31弾）は「1枚を、選んだシールド1つの下に」固定のため、(A) 各シールドの下に1枚ずつ（スーパー・シールド・プラス）と (B) 1つのシールドの下に最大5枚まで（ウルトラシールド・プラス）が表せなかった。本弾は op の引数拡張だけで、新規 op・面フィールド・GameState フィールドはなし（state.rs 変更なし。op 引数のためスキーマ再生成＝差分は shield_plus の each/count のみ）。

- **shield_plus 引数 each: true（形A）**: 自分の各シールドの下に1枚ずつ置く。1枚ずつ、置く先のシールドを選びながら進める（束ごとに差すカードが違うため、置く順序＝シールドの選択は実手続きどおり諮問する）。山札がシールドの数より少なければ、置ける分だけ置いて終わる。dmex06-010 の原文は「上から1枚目を各シールドの下に」の旧表記だが、スーパー・シールド・プラスの定義（dm28-s01 の「1枚ずつ」表記が明示）として形Aで統一する。
- **shield_plus 引数 count: N（形B）**: 選んだ1つのシールドの下に最大 N 枚まで。2枚目以降は1枚ずつ「もう1枚置くか」を諮問し、断られたら止める。置くカードは裏向きのままで途中に得られる情報は無いため、「N枚まで」の一括枚数選択と等価。山札が尽きたら諮問なしで止まる。
- **再入可能性**: op は回答のたびに頭から再実行されるため、複数回の諮問にまたがる進行（形Aの済みシールド列 sp_done、形Bの対象と枚数 sp）はタスクの os に持つ（gachinko と同じ作法）。差し込み処理は既存コードから切り出した **_shield_plus_tuck** に共通化し、素形（引数なし）の挙動は従来と同一（対象シールドを1つ選び1枚差す。対象は os 経由になったが再開時の決定性は同じ）。
- プロト T890（形A: CIP may shield_plus {each: true}）/ T891（形B: CIP may shield_plus {count: 3}。実カードは5）。tests/test_vocab_pilot295.py（8件: parse＋形一致（T890/T891/T099 素形）、引数検証拒否（未知引数・each 非bool・count 非int）、形A 全シールド／山札不足（山札2枚で2束だけ）／辞退、形B 上限まで／1枚で停止／山札不足）＋ tests/test_vocab_pilot295_cards.py（2件: 対象3件の未登録・ギャップ純粋確認、partial＋本弾条項の提出形 parse。dm28-s01 は銀行済みの進化面が効くことも確認）。
- **ブックキーピング修正（本弾に同梱）**: tests/test_vocab_pilot293_cards.py を登録形に書き換え（ラウンド328/329の結果: 登録19件の進化面照合、alias 3件［dmc66-008 → dmpcd03-b02、dmartkiwami03-005 → dm25ex1-010、dm26ex4-sec009 → dm26ex4-012］、差し戻し4件の精緻化ギャップ照合）。書き換え後 **3 passed**。
- テスト結果: 第295弾本体 **8 passed**、cards **2 passed**、第293弾 cards（登録形）**3 passed**、test_data_audit **8 passed**。回帰バッチ（第295・31・293・294弾本体＋test_rules＋test_rust_schema_sync）= **86 passed / 1 failed**、cards バッチ（第295・293・31弾 cards）= **10 passed**。唯一の失敗 tests/test_vocab_pilot31.py::test_janken_win_draws は HEAD 1fe4a4e でも再現する既存失敗（stash で切り分け確認済み。本弾無関係。既知の pilot274 競合 test_floor_zero_colored_pays_civ_count には触れていない）。
- ラウンド330側の注意: 対象3行すべてが本弾で解放される見込み。提出形は cards テストの ADDITIONS が正本で、各行とも partial に CIP 誘発を1つ足し、unsupported から super_shield_plus を外すだけ（dmex06-010 / dmx19-s06 の partial には能力が無く条項は丸ごと追加、dm28-s01 は進化面＋W・ブレイカー銀行済み）。alias は提出前に照合: dmx19-s06 → dm29-s01 / dmc50-008 / dmc66-004 / promoy14-011（partial の source.aliases）。submit は partial の abilities と回答を連結するため、登録後に abilities の件数・内容とキーワードをテキストと照合すること。

## ラウンド330 スーパー／ウルトラ・シールド・プラス再変換

第295弾（shield_plus の each / count 引数）の再変換。対象は super_shield_plus 純粋3件。

- **新規登録2件**: dmex06-010（形A: CIP may shield_plus {each: true}）/ dm28-s01（形A。同形の CIP を追加し、銀行済みだったマナ進化Vの面＋W・ブレイカーと合わせて登録。ラウンド328で本節だけで差し戻された行）。
- **stale 解消1件**: dmx19-s06（形B）は提出前照合で **real.yaml に手変換済み**と判明（ウルトラシールド・プラスを modal＋put_under で表現、koba 確認 2026-10-28 の注記つき）。converted へ二重登録せず（ラウンド200の Fiona 教訓）、reject 行の除去のみ。alias（dm29-s01 / dmc50-008 / dmc66-004 / promoy14-011 → canon dmx19-s06）は real.yaml 側の扱いに残る。
- **差し戻し0件**。reopen は対象3行のみ除去（巻き込みなし）。登録後の本文照合: 2件とも abilities は CIP 誘発1件のみで、キーワード・マージ由来の混入・重複なし（dmex06-010 = blocker / double_breaker、dm28-s01 = double_breaker＋進化面 mana / [{civs: [light]}×2]）。
- converted **10,211 → 10,213** / rejects **2,115 → 2,112**、canonical overlap 0・漏れ 0（対象3件は converted ∪ real.yaml で全て所在確認）。super_shield_plus は rejects に残り0件でファミリー解消。
- ブックキーピング: tests/test_vocab_pilot293_cards.py の dm28-s01 を STILL_REJECTED から登録形（FORMS 形A）へ移動（登録 19→20件、差し戻し 4→3件）。tests/test_vocab_pilot295_cards.py は登録形に書き換え（登録2件の形照合＋dmx19-s06 の real 所在＋ファミリー解消）。新規に tests/test_vocab_round330_cards.py（帰属＋実挙動2件: dmex06-010 の各シールド1枚ずつ、dm28-s01 のマナ進化V＋各シールド1枚ずつ）。
- 次の番号: パイロット296 / ラウンド331 / プロト T892。

## 第296弾 「S・トリガーは使えない」（shield_trigger_restriction / s_trigger_disable）

ギャップ名 shield_trigger_restriction の純粋3件（dmx18-003 極武者カイザー「斬鬼」 / dmx21-064 / dmx22b-023 エメラル）と s_trigger_disable の純粋3件（dmr13-003 理英雄 デカルトQ / dmrp01-s03 赤攻銀 アサラーム / dm26rp2-066 禁術のラクシャ カレイル）、計6件。共通条項は「手札に加えた（加わる）シールドカードの S・トリガーは使えない」。不足は2形に分かれ、どちらも既存語彙で足りることを実挙動で固定した（ギャップ名と語彙名のドリフト）。新規 op・面フィールド・GameState フィールドはなし（state.rs 変更なし、スキーマ再生成なし）。

- **形A（そのカード形、5件）**: move の引数 **strigger: "off"**（バンドC2 U68 で導入された「S・トリガーの印」。escape キーワードの instead 形が keywords.yaml にあり、実挙動は第281弾 test_796 で固定済み）。効果の shield→hand 移動は op_move が break タスク（phase 1・fire_break: False）へ回し、宣言諮問で t["strigger"] == "off" がその束の宣言肢を消す。本弾は対象行の形（CIP 誘発・攻撃誘発の素の move）で再検証した。dm26rp2-066 は partial の CIP move に strigger: "off" を足すだけ。dmx18-003 は may で加え、加えた場合（move の as: 束縛＋ if {exists: {ref}} ゲート）だけ相手のパワー6000以下を破壊する形。dmx22b-023 / dmr13-003 は「手札1枚を新しいシールドとして置いてもよい。そうしたら、自分のシールドをひとつ手札に戻す」ゲート形（シールド化 move の as: 束縛でゲートし、戻す move に strigger: "off"）。dmx21-064 は同じゲート形のターン終わり誘発。
- **形B（常在形、1件・dmrp01-s03）**: {kind: static, affects: {zone: shield, owner: you, filter: {not_civs: [light]}}, mod: {deny: [s_trigger]}}。変換済み dm24ex1-001（affects の zone: shield で S・トリガーを与える）の鏡像。permits は deny → allow → 既定の順（101.2「できない」は「できる」に勝つ）でキーワード s_trigger の allow を打ち消し、宣言諮問（combat phase 1 の _permits_face）はブレイク経路・効果経路の両方が見るため、両経路で効くことを固定した。
- プロト T892（形A: CIP move＋strigger: "off"）/ T893（形Aの対照: 指定なし）/ T894（形B）。シールド役は既存 T279（闇・S・トリガー持ち）/ T207（光・同）。tests/test_vocab_pilot296.py（10件: parse＋形一致、検証拒否2形［未知 action・未知 filter キー］、形A CIP で宣言なし＋印の確認／対照で宣言あり、形B ブレイクで闇は不可／発生源なし対照で可／光は可／相手のシールドは不干渉／効果経路でも不可）＋ tests/test_vocab_pilot296_cards.py（2件: 対象6件の未登録・ギャップ純粋確認［converted・real とも無し］、partial＋本弾条項の提出形 parse。dmx18-003 の destroy はマクロ展開形で照合）。回帰: 第296・281・189・269弾＋test_rules＋test_rust_schema_sync = **82 passed**、test_data_audit = **8 passed**。既知の既存失敗2件（pilot274 競合、pilot31 janken）には触れていない。
- **範囲外の注意**: 印 strigger_on（付与）と形B の deny が重なった場合、combat phase 1 の elif 分岐は印側を優先して宣言肢を復活させうる（permits の deny と印の優劣が未分離）。対象6件にこの重なりは無く、本弾では触らない。
- ラウンド331側の注意: 対象6行すべてが本弾で解放される見込み。提出形は cards テストの ADDITIONS が正本（dm26rp2-066 は move への strigger: "off" 追加のみ）。他の5件は partial が骨格のみなので公式全文から不足分を構築すること: dmx18-003 のパワーアタッカー節は partial で攻撃誘発＋modify の形になっているが、公式の「攻撃中 +2000」と一致するか全文で照合すること。dmx21-064 は partial の name が "No Data"・text が断片のみ（ターンのはじめのドロー節を含む全文が要る）。dmr13-003 はブロッカーとマナ武装7のドロー節が別に要る。dmrp01-s03 の CIP（自分のシールドを数える。それと同じ枚数を山札の上からシールド化）は selector の count が式を受けるため count: {count: {zone: shield, owner: you}} で表せる見込みだが、数えるのは置く前のシールド数であることを実挙動で確認すること。alias は提出前に照合: dmx18-003 → dmx11-002、dmx22b-023 → dm03-042 / dmc37-025 / dmc56-033 / dmc66-036 / dmx21-069（partial の source.aliases）。submit は partial の abilities と回答を連結するため、登録後に abilities の件数・内容とキーワードをテキストと照合すること。
- 次の番号: パイロット297 / ラウンド331 / プロト T895。

## ラウンド331 「S・トリガーは使えない」再変換

第296弾（strigger: "off" / 形B deny）の再変換。対象は shield_trigger_restriction 純粋3件＋s_trigger_disable 純粋3件の計6件で、新規登録4件・差し戻し1件・stale 解消1件（差し戻し・stale はいずれも対象行側の事情で、語彙の不足ではない）。

- **新規登録4件**: dm26rp2-066 禁術のラクシャ カレイル（partial の CIP move に strigger: "off" を追加しただけ）/ dmx18-003 極武者カイザー「斬鬼」（パワーアタッカー+2000 は rule_convert.split 由来の power_when 常在形が正本で、partial の攻撃誘発＋modify 形は採用しなかった。回答の abilities は第296弾 ADDITION の攻撃誘発のみで、split が静的を前置する）/ dmr13-003 理英雄 デカルトQ（マナ武装7 CIP は dmr13-083 先例の if 形＋dm21-040 先例の repeat×may-draw で「5枚まで引いてもよい」。ブロッカーは split が拾わないため回答の keywords で明示。もう1つの CIP はゲート形）/ dmrp01-s03 赤攻銀 アサラーム（CIP シールド化＋形B 常在）。
- **dmrp01-s03 の count 実挙動確認（必須項目）**: CIP の select count = {count: {zone: shield, owner: you}} は置く前のシールド数で評価されることを登録形テストで固定した（開始 n0 枚 → CIP 後に 2×n0 枚、山札は n0 枚減）。
- **差し戻し1件: dmx21-064 → data_incomplete（新規の不足ではない）**: 公式データ自体がカード名・種族を欠く行（name: No Data / race: ???、原文データの取得欠落）。S・トリガー節は第296弾で表現可能になったため、ターン開始ドロー節＋ターン終わりゲート形まで全構築した提出形を partial に銀行し、残る不足を data_incomplete として差し戻した。データが直れば銀行済みの形で即登録できる。
- **stale 解消1件: dmx22b-023（エメラル）**: 提出前照合で正本が **dm26ex4-cho049**（identity の canon）で変換済みと判明し、dmx22b-023 自体は submit の原文コーパスに無いため登録せず reject 行の除去のみ。あわせて登録済みエメラルの同条項の欠落を外科的に修繕した: 正本 cho049 の戻す move には strigger: "off" が無く、旧 notes の「エンジン側の扱いに委ねる」は誤りで、**修繕前は手札に加えたシールドの S・トリガー宣言諮問が実際に出ていた**（実挙動プローブで確認。印を付けると消える）。cho049 に印を付与し、dmx22b-023 を source.aliases に追加、notes を訂正。同じ欠落があった別変換エントリ **dm03-042**（同じカードの旧変換。notes 自身が「制限は扱っていない」と明記）にも同じ印付与＋notes 訂正をした（プローブで同様に確認）。なお converted にエメラルの変換エントリが dm03-042 と dm26ex4-cho049 の2つある重複自体は既存のデータ債務で、本ラウンドでは触っていない（relocation/監査ステージの課題）。
- 提出前照合: 対象 id・alias とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml に重複なし（dmx18-003 の alias dmx11-002 は登録時に自動付与）。canon 照合は5件が自 id、dmx22b-023 のみ上記のとおり。reopen は対象6行のみ除去（巻き込みなし）。submit は一括1回で4件 ✓＋dmx21-064 が data_incomplete で銀行差し戻し。
- 登録後の照合: 4件とも abilities の件数・内容とキーワードを本文と照合し、マージ由来の混入・重複は無し（dmx18-003 に partial の旧 modify 形は残っていない）。
- テストブックキーピング: tests/test_vocab_pilot296_cards.py を登録形に書き換え。登録4件の source.unsupported は空リスト（converted 既存の209件と同じ形）として残るため、帰属テストの断言は「unsupported が空」に合わせた。
- テスト: tests/test_vocab_round331_cards.py＋tests/test_vocab_pilot296_cards.py — **10 passed in 47.23s**（round331 = 帰属＋実挙動6件［066 CIP で宣言なし＋印、s03 count CIP（置く前評価）、s03 形B deny、18-003 攻撃形、13-003 ゲート形、修繕した cho049／dm03-042 で宣言なし］、pilot296 cards 登録形 = 3件）。tests/test_data_audit.py — **8 passed in 63.44s**。
- ラウンド直後: converted 10,213 → **10,217** / rejects 2,112 → **2,107**、canonical overlap 0・漏れ0。shield_trigger_restriction / s_trigger_disable は rejects に残り0件でファミリー解消。
- 回答: ~/workspace/DMPJ-work/answers/round331.yaml（reject 行の partial＋第296弾 ADDITIONS から決定的に構築。dmx21-064 のみ全文構築）。
- 次の番号: パイロット297 / ラウンド332 / プロト T895。

## 第297弾 「ブレイクしたシールドは墓地に置く」（break_replacement_graveyard / break_to_graveyard / shield_break_to_graveyard）

3つのギャップ名に分かれた同一条項「このクリーチャーがシールドをブレイクする時、相手はそのシールドを手札に加えるかわりに墓地に置く」の純粋6件（break_replacement_graveyard: dm25ex2-018 / dmr04-018 / dm26ex4-002、break_to_graveyard: dm26sd1-g005 / dmex17-w06、shield_break_to_graveyard: dm24bd6-037）。不足は無く、ギャップ名と語彙名のドリフトだった（新規 op・面フィールド・GameState フィールドなし＝ state.rs 変更なし、スキーマ再生成なし）。

- **機構は既存**: ブレイクの置換諮問 `_break_consult`（第146弾）が、割るシールド1枚ずつ chosen 確定後・S・トリガー宣言の前に置換を諮り、レコード {ev: break, subject: ブレイクしたクリーチャー, shield: そのシールド, player: victim} で照合する。登録済み先例が6件以上ある形: {kind: replace, when: {event: break, subject: self}, instead: [{op: move, select: {ref: event.shield, count: 1}, to: graveyard, reason: put}]}（dm24ex2-chog06 / dm24ex2-014 / dm25ex2-014 / dmrp18-s07 / dm24ex2-dm04 / dmex15-a027。条件つき変形は promoy8-002 の if 形）。置換されたシールドは「ブレイクされた」ことにならない（QA 33466 の設計判断、第146弾）: chosen から外れ、break_before も S・トリガー宣言も S・バックも起こらず、ブレイク枚数にも数えない。任意でない置換は諮問の決定自体が出ない（候補1件・辞退肢なし）。束の下のカードは instead の move が上のカードだけを指すが、エンジンの束移動の作法で上のカードと一緒に墓地へ動くことを実挙動で確認した（先例6件と同一挙動。T895 の束テストで固定）。
- **形A（無条件、4件: dm25ex2-018 / dm26ex4-002 / dm26sd1-g005 / dmex17-w06）**: 先例形そのまま。T895 で W・ブレイカーの2枚割り（S・トリガー持ち T279＋T207）が2枚とも墓地に置かれ、宣言も諮問決定も出ないことを固定。対照 T896（置換なし）は手札＋宣言あり。
- **形B（相手の手札0枚、dmr04-018）**: 形A ＋ if {cmp: [{count: {zone: hand, owner: opp}}, "==", 0]}。if は _break_candidates が諮問時点（割る前）で評価する。T897 で手札0枚→墓地／手札1枚→手札＋宣言ありを固定。
- **形C（水晶武装4、dm24bd6-037）**: 形A ＋ if {cmp: [{count: {zone: mana, owner: you, filter: {face_down: true}}}, ">=", 4]}。count＋face_down フィルタの形は第283弾 eternal_kappa の if ゲートと同形。T898 で裏向き4枚→墓地／3枚→手札＋宣言ありを固定。
- プロト T895（形A）/ T896（形Aの対照）/ T897（形B）/ T898（形C）。tests/test_vocab_pilot297.py（10件: parse＋形一致、検証拒否2形［instead の未知 op・if の count セレクタ未知キー］、形A 2枚割り／対照／束の下のカードの追随、形B 両方向、形C 両方向）＋ tests/test_vocab_pilot297_cards.py（2件: 対象6件の未登録・ギャップ純粋確認、partial＋本弾条項の提出形 parse）。回帰: 第297・146・238・248・281・283・290・296弾＋test_rule_break_replace＋test_rules＋test_rust_schema_sync = **126 passed**、test_data_audit = **8 passed**。既知の既存失敗2件（pilot274 競合、pilot31 janken）には触れていない。
- ラウンド332側の注意: 対象6行すべてが本弾で解放される見込み。提出形は cards テストの FORM_A / FORM_B / FORM_C が正本で、各行とも partial に置換能力を1つ足し、unsupported から当該ギャップを外すだけ（dm26ex4-002 を除く）。行ごとの注意: **dm26ex4-002 は partial の無い行** — 公式全文から全構築すること（コスト軽減［相手のエレメントの文明1つにつき2］、T・ブレイカー、CIP の無色でないクリーチャー全シールド化＋自分の無色クリーチャー1体につき相手の手札1枚をシールド化、エターナル・Ω。Ω のキーワード有無は提出前に keywords.yaml と変換済み先例で確認を）。**dm26sd1-g005** の partial のパワーアタッカーは攻撃誘発＋modify 形だが、ラウンド331の先例では split 由来の power_when 常在形が正本 — 全文照合してから提出を。alias は提出前に id・alias とも照合: g005 → 20件（dm22ex1-cho09 / dm24ex2-033 / dmex15-a042 ほか）、w06 → dmd24-009 / dmex04-003、018 → dm25ex2-chog10、037 → dm23ex3-022。submit は partial の abilities と回答を連結するため、登録後に abilities の件数・内容とキーワードをテキストと照合すること。なお **dm26ex4-sec005 / dm26ex4-025** は同じ条項を break_replacement_by_breaker の名で持ち、残りギャップ enter_bz_summon_only が別にあるため本弾では解放されないが、条項の形は同じなので、ラウンドで reopen 対象に含める場合は解けた条項として partial に銀行できる（任意）。
- 次の番号: パイロット298 / ラウンド332 / プロト T899。

## ラウンド332 「ブレイクしたシールドは墓地に置く」再変換

第297弾（ブレイク置換の先例形）の再変換。対象は break_replacement_graveyard 純粋3件＋break_to_graveyard 純粋2件＋shield_break_to_graveyard 純粋1件の計6件で、全件が新規登録（差し戻し0件）。

- **新規登録6件**: dm25ex2-018 ネオ・ボルメテウス・ホワイト・ドラゴン（形A。alias dm25ex2-chog10 は登録時に自動付与）/ dmr04-018 混沌の覇者ディス・ガジラ（形B。スペース・チャージと power_when 常在は partial のまま）/ dm26sd1-g005 ボルメテウス・サファイア・ドラゴン（形A。パワーアタッカー+3000 は split 由来の power_when 常在形が正本で、partial の攻撃誘発＋modify 形は回答に含めなかった。alias 20件は登録時に自動付与）/ dmex17-w06 ボルメテウス・レッド・ドラグーン（形A。alias dmd24-009 / dmex04-003）/ dm24bd6-037 偽りの名 ルカニド（形C。alias dm23ex3-022）/ dm26ex4-002 「誣」の頂 ウェディング・イノセンス（形A。partial の無い行のため公式全文から全構築）。
- **dm26ex4-002 の全構築**: エターナル・Ω はキーワード **eternal_omega** が keywords.yaml に既存（split も導出）。召喚コスト軽減「相手のエレメントの文明1つにつき2」は **civ_count 式** {cost: {amount: -2, count: {civ_count: {zone: bz, owner: opp}}}}。下限のただし書きは原文に無く、最大軽減10＜コスト13のため cost_min 不要。CIP は「召喚によって出た時」= when {event: move, to: bz, reason: summon, subject: self}。全体シールド化は filter {types: [creature], colorless: false}＋count: "all"＋move to shield / reason: charge（dmd10-007 の同形フィルタ先例）。手札シールド化は自分の無色クリーチャー数ぶんの repeat {times: {count: {zone: bz, owner: you, filter: {types: [creature], colorless: true}}}}、本体は相手が選ぶ move {select: {zone: hand, owner: opp, chooser: opp, count: 1}, to: shield, reason: charge}。文明はゼロ＝無色として civs: []（他の「頂」ゼニス変換と同表記）。
- **登録後の実挙動確認で3件の外科的修正（dm26ex4-002）**: (1) コスト軽減の常在型は **zone: hand が必須** — 自常在型は ability の zone（既定 bz）とカードの現在ゾーンが一致する時だけ効くため、zone 無しでは手札で不発だった（pay_cost 13 のまま）。dm24ex3-rp2s08 の登録形（zone 無し）も同じ理由で手札では不発のままであることを実測で確認した（既存データの潜在的な不発として記録。修繕は別ステージの課題）。実働先例は dm21-020 / dm22rp2x-008 の zone: hand 形で、本カードも同形に差し替えた（pay_cost 13→9 を実測）。(2) 全体シールド化のフィルタは当初 not_civs: [zero] としたが、civs: [] 表記のこのカード自身が「無色ではない」に一致してしまい、自分自身がシールド化されかけてエターナル・Ω で手札に戻る実挙動を確認した。両表記（[] / [zero]）に効く **colorless: false** に差し替えた。(3) 全体シールド化の select には **owner: any** が必要だった（select の owner 既定は you で、当初は自分のクリーチャーしか対象にならなかった。dm22-006 / dm23rp4x-045 等の全体形先例）。
- **dm26ex4-002 の実挙動確認（登録形テストで固定）**: 相手のエレメントが火・水の2文明なら軽減後コスト9（9マナで召喚でき、8マナでは main の選択肢に play が出ない）。CIP で自他の無色でないクリーチャー（自分の T001・相手の T034 / T010）がすべてシールド化され、自分の無色クリーチャー（このカード自身）1体につき相手の手札1枚がシールド化される。
- **reopen の範囲外の巻き込み回避**: shield_break_to_graveyard で reopen すると promoy11-011（独走状態！鬼無双・カイザー「真剣」）も巻き込まれるため、このギャップは reopen せず dm24bd6-037 は直接 submit で登録した（submit が reject 行を除去）。reopen（break_replacement_graveyard / break_to_graveyard）は対象4行のみ除去。dm26ex4-002 は reason の無い行のため reopen 対象外で、こちらも submit が除去。
- **promoy11-011 は未処理（記録のみ）**: その shield_break_to_graveyard は「攻撃時にガチンコ・ジャッジに勝ったら、このターンだけ」という条件つき付与形で、本弾の常在置換とは別機構。ギャップ名は誤ラベルのまま残る（残り1件）。将来のガチンコ条件つき付与の弾で精緻化すること。
- **任意の銀行行は見送り**: dm26ex4-sec005 は submit の原文コーパス（load_rows の canon）に無い印刷で提出自体ができない。dm26ex4-025 は canon だが「相手がこのクリーチャーを選んだ時」の節の表現検証が別途必要なため、本ラウンドでは銀行しなかった（両行とも従来どおり rejects に残る）。
- 提出前照合: 対象 id・alias とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml に重複なし。canon 照合は6件とも自 id（load_rows に在ることを確認）。提出前に merge_split＋validate を模擬実行し6件とも検査通過・vocab_reject なしを確認してから submit 1回。
- 登録後の照合: 6件とも abilities の件数・内容とキーワードを本文と照合し、マージ由来の混入・重複は無し（dm26sd1-g005 に partial の旧 modify 形は残っていない）。
- テストブックキーピング: tests/test_vocab_pilot297_cards.py を登録形に書き換え。
- テスト: tests/test_vocab_round332_cards.py＋tests/test_vocab_pilot297_cards.py（登録形）— **7 passed in 32.45s**（round332 = 帰属＋実挙動4件［w06 形A、dmr04-018 形B の両方向、dm26ex4-002 の CIP＋コスト、8マナでは出せない］、pilot297 cards 登録形 = 2件）。tests/test_data_audit.py — **8 passed in 64.66s**。
- ラウンド直後: converted 10,217 → **10,223** / rejects 2,107 → **2,101**、canonical overlap 0・漏れ0。break_replacement_graveyard / break_to_graveyard は rejects に残り0件で解消。shield_break_to_graveyard は promoy11-011 のみ残存（上記）。
- 回答: ~/workspace/DMPJ-work/answers/round332.yaml（reject 行の partial＋第297弾 FORM_A / FORM_B / FORM_C から決定的に構築。dm26ex4-002 のみ全文構築）。
- 次の番号: パイロット298 / ラウンド333 / プロト T899。

## 第298弾 same_name_cast（同名呪文を表向きにし、シャッフルしてから唱える）

ギャップ名 same_name_cast の純粋2件は同一カード 邪眼皇アレクサンドルIII世の2印刷（dm26ex4-cho010 最新版・canon / c48-sec001 旧印刷）。在範の純粋ファミリーは最大でも3件規模まで痩せ、その多くは評価済み DEEP／延期のため、本弾は「rejects 2件＋converted の是正3件」が動く本ファミリーを選んだ。旧印刷の本文形（選んで唱え、その後シャッフル）は第282弾の詠唱形イディオムで解決済み・partial に銀行済みで、本弾の対象は最新版形の手順差だけ: 「唱えた呪文と同じ名前の呪文を1枚表向きにし、山札をシャッフルしてからその呪文をコストを支払わずに唱えてもよい」。不足は無く、ギャップ名と語彙名のドリフトだった（新規 op・面フィールド・GameState フィールドなし＝ state.rs 変更なし、スキーマ再生成なし）。

- **最新版形イディオム**: 誘発 {when: {event: cast, player: you, from: [hand, graveyard], subject: {filter: {types: [spell], civs: [light, water, darkness]}}}, if: {exists: {zone: bz, owner: you, other: true, filter: {race_has: ナイト}}}, effect: [choose {zone: deck, owner: you, look: true, count: all} as: pile → choose {ref: pile, filter: {name: {name_of: event.subject}, types: [spell]}, count: 1} as: found（choose の **reveal: true** つき）→ if {exists: {ref: found}} then [shuffle {player: you} → may [play_free {ref: found}]]]}。第282弾形との差は3点: (1) 「表向きにする」は choose の reveal: true（バンドC1 U39。束縛したカードを全プレイヤーに公開し、s.pub に reveal 記録が残る）。(2) シャッフルは詠唱より前で、見つけた場合の if の中にある（旧印刷形は末尾の無条件シャッフル。最新版は「表向きにし、シャッフルしてから…唱えてもよい」の連鎖のため、見つからなければシャッフルも起きない形に置いた）。(3) pile の戻し move は不要（choose はカードを動かさず ref を束縛するだけ。旧印刷形の move {ref: pile → deck} は見た束を戻す手続きで、最新版形では公開→シャッフルの連鎖に吸収される）。
- **シャッフルを挟んでも ref は生きる**: shuffle は山札リストの並べ替えのみでカードの生成を進めないため、found の ref (cid, gen) は不変で、後続の play_free {ref: found} がそのまま効く。T899 で公開記録の順序（山札の同名呪文の reveal < shuffle）と、シャッフル後に無償詠唱が解決すること（墓地の同名呪文2枚）を実挙動で固定。辞退した場合でも公開とシャッフルは諮問より前に済んでいること、同名呪文が山札に無い場合は公開・シャッフル・諮問のいずれも起きないこと、他のナイトが無い場合は誘発自体が起きないことも併せて固定した。
- Rust: when の subject が dict 形／from リスト／name_of 式フィルタ／play_free を含むため _simple_trigger の対象外（第282弾と同形）で、この能力を持つカードを含む対局は Python にフォールバックする。
- プロト T899（他のナイト役 T799・同名呪文 T800 は第282弾のものを流用）。tests/test_vocab_pilot298.py（8件: parse＋形一致、select への reveal 誤置の検証拒否、非 rust-simple、手札から詠唱［公開＜シャッフル＜詠唱］／墓地から詠唱／辞退［公開・シャッフル済みで山札に残る］／同名なし［公開・シャッフルなし］／他のナイトなし［不発］）＋ tests/test_vocab_pilot298_cards.py（4件: 対象2件の未登録・ギャップ純粋確認、cho010 提出形 parse、c48 の銀行形の不変確認、別印刷3件の誘発欠落の固定）。回帰: 第282・297弾本体＋test_rules = 63 passed、第282・297弾 cards＋test_data_audit＋test_rust_schema_sync = 18 passed。既知の既存失敗2件（pilot274 のコスト0競合、pilot31 の janken）には触れていない。
- ラウンド333側の注意: **dm26ex4-cho010** は partial に abilities が無いため、本弾の誘発を1つ足し、unsupported から same_name_cast を外すだけ（提出形は cards テストの CHO010_FORM が正本）。登録時に **c48-sec001** が alias として畳み込まれるか（aliases_for に含まれるか）を提出前後に確認すること。併せて既存の欠落の是正: 別印刷 **29-sec001 / dm29-s03 / dmc48-001** は converted の独立エントリとして本誘発を欠いた形（キーワード double_breaker のみ）で登録済み — 各エントリの本文が旧印刷形（選んで唱え、その後シャッフル）か最新版形かを確認し、対応する形（旧印刷形 = 第282弾の CAST_FORM / 最新版形 = 本弾の CHO010_FORM）を足すこと。submit は partial の abilities と回答を連結するため、登録後に abilities の件数・内容とキーワードをテキストと照合すること。
- 次の番号: パイロット299 / ラウンド333 / プロト T900。

## ラウンド333 same_name_cast 再変換

第298弾（最新版形イディオム）の再変換。対象は same_name_cast 純粋2件＋converted の是正3件。

- **新規登録1件**: dm26ex4-cho010 邪眼皇アレクサンドルIII世（最新版・canon）。partial に abilities が無いため第298弾の誘発（cards テストの CHO010_FORM）を1つ足し、unsupported から same_name_cast を外して登録。登録形は abilities == [CHO010_FORM]・keywords == [double_breaker] で、submit の連結（merge_split）由来の混入・重複は無し（提出後に本文と照合済み）。
- **alias 畳み込み1件**: c48-sec001（旧印刷）は submit の原文コーパス（canonical_rows）に無い印刷で直接は提出できない。reopen same_name_cast で対象2行のみ除去し、cho010 の登録時に validate の aliases_for が source.aliases = [29-sec001, c48-sec001, dm29-s03, dmc48-001] を自動付与した。c48-sec001 は converted の独立エントリではなく alias として引け、reject 行も残らないことを提出後に確認した。
- **converted 是正3件（件数不変）**: 29-sec001 / dm29-s03 / dmc48-001 は独立エントリとして本誘発を欠いた形（キーワード double_breaker のみ）で登録されていた既存の欠落。3件とも登録本文は旧印刷形（「唱えた呪文と同じ名前の呪文を1枚選び、コストを支払わずに唱えてもよい。その後、山札をシャッフルする」）だったため、各エントリに第282弾の詠唱形 CAST_FORM を abilities として追加し、source.notes に是正の記録を追記した。なお3件は cho010 の aliases にも名を連ねるが、独立エントリとして引く場合はエントリ側が優先される（AliasDict の仕様）ため実害は無く、data_audit も通過した。
- **差し戻し0件**。提出前照合: 対象 id・alias とも real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml（プロト本文中の参照のみ）/ converted に重複なし。canon は identity で cho010 本人と確認。
- **実挙動（登録形テストで固定）**: cho010（最新版形）は手札から水の呪文 T800 を唱えると山札の同名呪文が表向きにされ（reveal 記録）、シャッフルされてから無償で唱えられる（公開記録の順序 reveal < shuffle、墓地の T800 が2枚）。是正した dm29-s03（旧印刷形）は同名呪文を選んで無償で唱えた後にシャッフルが起き、表向きにする手順が無いため reveal 記録は出ない。
- テストブックキーピング: tests/test_vocab_pilot298_cards.py を登録形に書き換え。tests/test_vocab_pilot282_cards.py の c48 テストは差し戻し固定から alias 畳み込み固定（test_c48_folded_into_cho010_round333）に更新し、docstring にラウンド333の後日談を追記した。
- テスト: tests/test_vocab_round333_cards.py（帰属＋実挙動2件）＋tests/test_vocab_pilot298_cards.py（登録形4件）＋tests/test_vocab_pilot282_cards.py（5件）＋tests/test_data_audit.py（8件）— **20 passed in 88.08s**。
- ラウンド直後: converted 10,223 → **10,224** / rejects 2,107 → **2,099**、canonical overlap 0・漏れ0。same_name_cast は rejects に残り0件で解消。
- 回答: ~/workspace/DMPJ-work/answers/round333.yaml（reject 行の partial＋第298弾 CHO010_FORM から決定的に構築）。
- 次の番号: パイロット299 / ラウンド334 / プロト T900。

## 第299弾 under_card_removed（自分の進化クリーチャーの下にあるカードが墓地に置かれた時）

ギャップ名 under_card_removed の純粋3件は、いずれも DM-34 の同一能力「自分の他のクリーチャーが破壊された時、または自分の進化クリーチャーの下にあるカードが墓地に置かれた時、＜効果＞」を持つ監視者クリーチャー（dm34-014 呪言人形ワヤ / dm34-022 神星の守護者アルト・コロニス / dm34-032 惑星の勇者ドリッピー）。在範の純粋ファミリーは最大でも3件規模まで痩せ、その多くは評価済み DEEP／延期のため本ファミリーを選んだ。不足は from_under 機構（第3段）の監視者形が未検証だったことだけで、新規 op・面フィールド・GameState フィールドは無い（ドリフト）。ただし検証の過程で既存エンジンの二重収集を1件見つけて修正した（下記）。converted 10,224 / rejects 2,099 は不変（パイロットのみ、ラウンド334は未実施）。

- **誘発対の形（3件共通）**: 破壊側 = {kind: trigger, when: {event: move, from: bz, to: graveyard, reason: destroy, subject: {owner: you, other: true, filter: {types: [creature]}}, from_under: false}, effect: ＜効果＞}。from_under: false は、進化クリーチャーごと破壊された時に下のカードのレコード（host つき・reason も destroy）まで「自分のクリーチャーが破壊された」に数えて重ねて発火させないための切り分け（dmsd06-012 の第3段先例と同型。下のカードは特性を持たないカードとして墓地に置かれるのであって、クリーチャーが破壊されるのではない）。下カード側 = {kind: trigger, when: {event: move, from: bz, to: graveyard, from_under: {owner: you, filter: {types: [evolution]}}}, effect: ＜効果＞}。こちらは理由を問わない（破壊でも効果の put でも「墓地に置かれた時」）。
- **監視者形の実挙動固定**: from_under の変換済み先例は subject: self（下にあったカード自身、第3段・ラウンド194）と from_under: self（宿主自身）だけで、第三のクリーチャーが場から {owner, filter} で監視する形は未検証だった。T900（誘発対＋数え用ミル効果）で固定: 自分の他のクリーチャーの破壊で1回／スタックごと破壊で破壊側1回＋下カード側は下1枚につき1回（下2枚なら計3回。レコード単位の発火は第3段の作法どおり）／下カードの単独移動（reason: put）では下カード側だけ1回／相手のスタック・監視者自身の破壊では発火しない。
- **エンジン修正（宿主の二重収集）**: 宿主がまだバトルゾーンにトップとして残っている時に下のカードが単独で動くと、宿主の from_under 誘発が通常の発生源（bz_tops）と host_only の lki 発生源の両方から収集され、二重に発火していた（T903 の from_under: self で実測: 効果が2回解決）。events._collect_triggers で、宿主が既に通常の発生源に含まれる場合は host 発生源を加えないよう修正した。宿主ごと離れた場合は従来どおり host_only から1回だけ発火する（両形をテストで固定）。収集ロジックのみの変更で state.rs・スキーマには触れていない（from_under を含む照合は元々 Python 経路）。
- **効果形（3件とも既存イディオム）**: dm34-014 = modify {select: {zone: bz, owner: opp, count: 1}, mod: {power: -1000}, duration: end_of_turn}。dm34-032 = may [choose_number {as: n} → choose {zone: deck, count: 1, reveal: true} as: top → if {cmp: [{cost_of: {ref: top}}, "==", {declared: n}]} then move {select: {zone: bz, owner: opp, filter: {power_le: 5000}, count: 1}, to: graveyard, reason: destroy}]（第210弾の宣言プリミティブ。数字の範囲は先例どおり既定の 0〜10）。dm34-022 = choose {zone: deck, owner: you, from_top: 1, count: 1} as: top（上を見る）→ if {exists: {ref: top, filter: {types: [spell]}}} → may [choose {ref: top, count: 1, reveal: true} as: hit → move {select: {ref: hit}, to: hand, reason: draw}]（dmx16-030 の「見て、呪文なら唱えてもよい」形の手札版）。
- **既存問題の発見（本弾では直さない）**: dm34-022 の形の先例として引いた dmr08-008 の登録形 choose {count: 0, up_to: true} は不発形だった。selectors.select は count で mx（選択上限）を決めるため count: 0 では候補があっても常に空に束縛される（candidates が2件ある状態で select が決定なしに [] を返すことを実測）。同形の select は converted に **334箇所**あり、文脈はいずれも「1体／1枚選んでもよい」（正しい形は count: 1, up_to: true 相当。docs 内の既存注記にも「正しくは count: 2, up_to: true」とある）。エンジン側で count: 0 + up_to: true を解釈するかデータ側を移行するかは、全334箇所の文面照合が要るため、本弾では扱わず専用の棚卸し＋修繕ステージとして切り出す（dm24ex3-rp2s08 の zone: hand 欠落と同じ「変換済みデータの不発」類型）。
- プロト T900–T906（T900 監視者・ミル形 / T901 素の進化獣 / T902 下カード単独送りの駆動つき進化獣 / T903 宿主自身の監視者 / T904・T905・T906 は対象3件の実形）。tests/test_vocab_pilot299.py 17件（parse＋検証3件、誘発対の実挙動6件、宿主 self の実挙動2件、実形3カードの実挙動6件）＋ tests/test_vocab_pilot299_cards.py 2件（対象3件の未登録・ギャップ純粋確認、partial＋提出形の parse）。回帰: from_under 本体＋第173・294・297弾＋test_rules＋rust 系 = 113 passed / 293 skipped（rust は未構築環境のため skip で Python フォールバック）、from_under cards＋pilot299 cards＋test_data_audit = 11 passed。既知の既存失敗2件（pilot274 のコスト0競合、pilot31 の janken）には触れていない。dm24ex3-rp2s08 の修繕は本ファミリー外のため未実施（従来どおり別ステージ課題）。
- ラウンド334側の注意: 対象3件とも単独 gap の純粋行で、reopen under_card_removed で3行だけが外れる見込み（reopen の出力行数を必ず数えること）。3件とも partial に abilities が無いため、本弾の誘発対を足し、unsupported から under_card_removed を外すだけ（提出形は cards テストの FORMS が正本）。登録後に abilities・keywords が本文と一致するか照合すること（submit の連結／merge_split の混入確認）。
- 次の番号: パイロット300 / ラウンド334 / プロト T907。

## ラウンド334 under_card_removed 再変換

第299弾（from_under 監視者形の誘発対）の再変換。対象は under_card_removed 純粋3件。

- **新規登録3件**: dm34-014 呪言人形ワヤ / dm34-022 神星の守護者アルト・コロニス / dm34-032 惑星の勇者ドリッピー。3件とも partial に abilities が無いため第299弾の誘発対＋効果（cards テストの FORMS が正本）を足し、unsupported から under_card_removed を外して登録。partial の text は断片（対象条項のみ）だったため、回答の text は reject 行の公式全文に戻した。登録形は3件とも abilities == FORMS・keywords なしで、submit の連結（merge_split）由来の混入・重複は無し（提出後に本文と照合済み）。
- **dm34-022 の形**: 効果は choose {from_top: 1, count: 1}（第299弾で実挙動固定した正本）。dmr08-008 の登録形 choose {count: 0, up_to: true} は select の mx=0 で常に空になる不発形のため使っていない（converted に同形が334箇所ある棚卸し＋修繕は別ステージ課題のまま）。
- **alias 畳み込み・stale 解消・差し戻しは0件**。3件とも identity で自 canon・alias なしを確認。提出前照合: 対象 id は real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted のいずれにも無し。reopen under_card_removed は対象3行のみ除去（巻き込みなし）。
- **実挙動（登録形テストで固定）**: dm34-014 は自分の他のクリーチャーの破壊を監視して相手クリーチャー1体のパワーを 3000→2000 にした。dm34-032 は数字宣言と山札の上のコストが一致して相手のパワー5000以下を破壊し、上のカードが表向きにされた（reveal 記録）。dm34-022 は山札の上の呪文 T003 を相手に見せて（reveal 記録）手札に加えた。
- テストブックキーピング: tests/test_vocab_pilot299_cards.py を登録形に書き換え。
- テスト: tests/test_vocab_round334_cards.py（帰属＋実挙動3件）＋tests/test_vocab_pilot299_cards.py（登録形1件）＋tests/test_data_audit.py（8件）— **13 passed in 85.01s**。
- ラウンド直後: converted 10,224 → **10,227** / rejects 2,099 → **2,096**、canonical overlap 0・漏れ0。under_card_removed は rejects に残り0件で解消。
- 回答: ~/workspace/DMPJ-work/answers/round334.yaml（reject 行の partial＋第299弾 FORMS から決定的に構築）。
- 次の番号: パイロット300 / ラウンド335 / プロト T907。

## 修繕ステージ: choose {count: 0, up_to: true} の棚卸しと修繕

第299弾の発見（converted dmr08-008 の登録形 choose {count: 0, up_to: true} が不発 — selectors.select は count を選択上限として扱うため、up_to: true でも常に対象0件で束縛し、決定自体が発生しない）を受け、パイロット番号を消費しない独立の修繕ステージとして棚卸しと一括修繕を実施した。

### 棚卸し（パースベースで厳密に数えた）

- data/cards/converted.yaml: 論理出現 **335件 / 314カード**、物理 dict は **334件**（dmr03-012 の2つの誘発が YAML アンカーで同一 dict を共有し、論理2件が物理1行に載る — 第299弾の「334箇所」は物理数と一致）。
- data/cards/proto.yaml / real.yaml / real_vocab.yaml / real_zone.yaml: **各0件**（編集対象外、計数のみ）。
- 隣接パターン（本節では対象外）: up_to を伴わない op 引数レベルの count: 0 が13件。**【訂正】本節の初出では「mill 系12件／break 系1件、select ではないので不発問題とは無関係」としたが、これは誤り。** op 定義を直接確認したところ内訳は mill 系11件／break 系2件（dmx11-023 は mill ではなく break）で、どちらも同じ不発形だった（mill はマクロ展開で from_top: $count になるため 0 では何も動かず、break は op_break が count を評価してブレイクタスクに渡すため 0 では何もブレイクしない）。追補の修繕ステージで対応した（次節）。

### 分類（全335件を所有カードのテキスト＋能力形と照合）

- **移行 326件**: 条文に選択肢性（「選んでもよい」）または「最大1件まで選ぶ」読みがあるもの。正形 count: 1, up_to: true へ移行（up_to は保持し辞退可能性を保存）。
- **除外 9件**（count: 0, up_to: true のまま据え置き。将来の修繕候補として正形を記録）:
  1. dmex02-066 卍月の流星群 — テキストは強制の1体破壊。正形は count: 1 **without** up_to（up_to を残すと誤って辞退可能になる）。
  2. dmex10-016 シバカゲ斎 — 山札上5枚をまとめて墓地へ（束縛集合そのものを移動する全か無か形）。
  3. dmex10-018 白骨の守護者ホネンビー — 山札上3枚、同上。
  4. dmex11-037 トツゲキ戦車 バクゲットー — 手札すべてを捨てる、全か無か形。
  5. dmr12-045 戦慄の取引 ビッグ・パルサー — 束縛は count >= 0 の常に真のゲートにのみ使われる不活性形。本当の選択は may + count: "all" 側にあり、現状でも動作する。移行すると無意味な決定が増えるだけなので据え置き。
  6. dmr13-017 龍素記号Bs ボラパール（2ヒット中の第1ヒット） — 強制の条件付き束縛（見せることも、呪文なら手札に加えることも強制で選択肢性なし）。正形は count: 1 without up_to。第2ヒット（バウンス側「選んでもよい」）は移行した。
  7. dmr15-022 龍秘陣 ヘブン・アンセム — repeat 本体内の強制の上1枚束縛。条文に選択肢性なし。正形は count: 1 without up_to。
  8. dmr17-093 侵略者 タネタロウ — 山札上2枚をマナへ、全か無か形。
  9. dmr18-005 破線の悪魔龍 キルビリー — 墓地すべてを山札へ＋シャッフル、全か無か形。
- 検証中の再分類: dmex03-012 は純粋なゲート形（束縛集合は count>=1 判定にのみ使用、破壊本体は count: "all"、条文は「てもよい」）のため移行側に確定。

### 移行の実施

- yaml.compose のマーク（行番号）に基づく行精密編集で、対象 select の count スカラ行だけを 0 → 1 に書き換え。**326論理件 / 325物理行**（dmr03-012 の共有アンカーが1行で2論理件）。git diff は 325 insertions / 325 deletions で、全変更行が count: 0 → count: 1 のみ。ヘッダーコメント保持、未対象カードはバイト不変。per-card の source.notes には記録しない（本節が記録）。
- 移行後のパース棚卸し: 残存 {count: 0, up_to: true} は除外9件のみ（カード・パスとも一致、dmr13-017 は abilities[0] 側のみ残存）。converted 総数 10,227 は不変。

### 挙動証明（tests/test_repair_count0_upto.py、5件）

- 移行前（git stash で移行を退避して実測）: 棚卸しテスト失敗（335件残存）、代表3件の挙動テストすべて失敗 — dmex09-002 シンカイサーチャー（探索の選択がターン1内に解決しない）、dmr05-s06（墓地からの回収が提示されない）、dmr08-008 ラプソディ（攻撃時束縛が空で shieldize しない）。辞退テストは移行前は空転合格。
- 移行後: **5 passed** — 探索の選択が提示され選んだ T001 が手札へ（ターン1内）、辞退（0件選択）も可能、墓地回収が提示される、ラプソディの束縛が効いてシールドが5→6。
- テスト作成時の落とし穴（記録）: (1) deck_exact は filler と同名の spec カードを剥がす — 山札 spec を filler 異名で埋めないと1枚山札になり探索後に deck_out で負ける。(2) choose_cards の option key はゾーン名で重複する — 対象は key ではなく options の位置で指す。(3) 「いつかドローで来る」ケースと区別するため探索テストは解決ターンを1に区切った。

### 回帰

- tests/test_data_audit.py ＋ pilot299/round334/round333/pilot298/round332/pilot297 の cards テスト群: **26 passed / 1 failed**。失敗は tests/test_vocab_round333_cards.py::test_round333_disposition で、ラウンド333時点のスナップショット（rejects 2,099 / converted 10,224）を主張する陳腐化したブックキーピング — **クリーンな HEAD 3404ab1 でも再現する既存失敗**で本修繕とは無関係（ラウンド334で未更新）。別途ブックキーピング是正が必要。
- tests/test_rules.py ＋ tests/test_vocab_pilot299.py: **57 passed**。

### 収支

- converted **10,227（不変）** / rejects **2,096（無編集）**。新規登録・差し戻し・alias 畳み込みはなし（データ修繕のみ）。
- 次の番号は不変: パイロット300 / ラウンド335 / プロト T907。

## 修繕ステージ（追補）: op 引数レベルの count: 0 の修繕

前節の棚卸しで「対象外」とした op 引数レベルの count: 0（13件）について、op 定義を直接確認した結果、select 形と同じ不発形であることが判明したため、追補の修繕ステージとして対応した。前節の「mill 系12件／break 系1件・無関係」という記述は誤りであり、前節側に訂正を入れた（正しくは mill 11件／break 2件）。

### 棚卸しと不発の仕組み

- mill {count: 0} ×11: dmr16g-008 / dmr16g-008d / dmr17-075（then 内）/ dmr19-066 / dmr21-089 / dmr23-003 / dmrp04m-s05（能力2件）/ dmrp21-035 / dmx10-009 / dmx10-030。mill マクロ（data/rules/op_macros.yaml）は `{op: move, select: {zone: deck, owner: $owner, from_top: $count}, to: graveyard, reason: put}` に展開されるため、count: 0 では山札の上から0枚しか動かない。
- break {count: 0, player: you} ×2: dmx05-s03 / dmx11-023。op_break（dmsim/engine/ops.py）は count を評価してブレイクタスクに渡すため、0 では何もブレイクしない。

### mill 11件の修繕（本文の N へ、周囲の構造は不変）

各カードの本文「自分の山札の上からN枚を墓地に置いてもよい」の N を適用した（yaml.compose の行マークに基づく行精密編集、変更は count 行のみ11行、ヘッダーコメント保持）:

- dmr16g-008 アクア呪文師 スペルビー: 3（mill で3枚 → ゲートが開き呪文を墓地から手札へ）
- dmr16g-008d アクア呪文師 スペルビー: 3（同上）
- dmr17-075 暗黒鎧 ゴルドバット: 1（マナ武装3の then 内。「上から1枚目」）
- dmr19-066 不死 デッド: 4
- dmr21-089 【問１】 テック: 1（「上から1枚目」。後続のドロー may は不変）
- dmr23-003 魔天斬 ドゥームズ: 6
- dmrp04m-s05 ハインリヒ・ダーマルク: 1（出た時・攻撃する時の両能力。「上から1枚目」→ ゲートが開き闇コスト4以下を墓地から出す）
- dmrp21-035 ジョルジュくん: 2
- dmx10-009 絶叫の影ガナル・スクリーム: 4（→ ゲートが開きクリーチャーを墓地から手札へ）
- dmx10-030 死神明王ガブリエル・XENOM: 3（→ ゲートが開き破壊＋コマンド回収）

「置いてもよい」の任意性の表現は周囲の既存構造（as 束縛＋if ゲート等）をそのまま保存した。素の mill（may で包まない形）は本文が「置いてもよい」のカードでも変換済み先例に多数ある（count>0 の mill 242件中 may 外は186件）ため、本ステージでは値のみを是正した。

### break 2件は除外（op 自体が誤り。正形を記録して別ステージへ）

dmx05-s03 ザビメテウス・武者・BLACK / dmx11-023 偽りの星夜 コングラチュレーションは count の値の問題ではないため、本ステージでは count: 0 のまま残置した:

- 本文は「自分のシールドをひとつ、（自分の）墓地に置いてもよい。そうした場合、〜」。しかしブレイクタスク（combat.h_break）は割ったシールドを**手札**へ送り、S・トリガー宣言とブレイクイベントを伴う。count を 1 にしても墓地には行かず、本文と一致しない。
- 現行形はさらに壊れている: 支払い（シールドの移動）が起きないのに後続の破壊が無条件で発火する。修繕前の実測（dmx11-023）: 出した時に choose_shields が提示されるが選べるのは0枚で、シールドは5→5のまま、相手のクリーチャー2体（T001 / T004）が両方とも自動で選ばれて破壊された。
- 正形は実績のあるイディオム（dmex01-026 / dmd08-019 / dmx11-022 / dmbd22-021 等と同形）: `{op: choose, as: sh, select: {zone: shield, owner: you, count: 1, up_to: true}}` → `{op: if, cond: {cmp: [{count: {ref: sh}}, ">=", 1]}, then: [{op: move, select: {ref: sh}, to: graveyard, reason: put}, <後続効果>]}`。値の修繕ではなく構造の再変換になるため、本ステージからは切り出して記録のみとする。

### 挙動証明（tests/test_repair_opcount0.py、5件）

- 修繕前（使い捨てプローブで実測）: dmr19-066 は出しても山札15→15・墓地0枚（mill 0枚）。dmx11-023 は上記のとおり無償破壊が発火。
- 修繕後: **5 passed** — 棚卸し（mill 全件が本文の N、残存 count: 0 は除外した break 2件のみ、件数不変）＋実挙動4件（dmr19-066: 上から4枚が墓地へ／dmr16g-008: 3枚 mill でゲートが開き呪文 T003 が手札へ／dmr17-075: then 内 mill 1枚でクリーチャー回収／dmrp04m-s05: mill 1枚でゲートが開き T008 を墓地から出す）。

### ついでに直したブックキーピング

- tests/test_vocab_round333_cards.py::test_round333_disposition がラウンド333時点のスナップショット（rejects 2,099 / converted 10,224）を主張してラウンド334以降クリーンな HEAD でも失敗していたため、現行件数（rejects 2,096 / converted 10,227）に更新した（ラウンド334の disposition テストと同形式）。

### 回帰

- tests/test_repair_opcount0.py: **5 passed**。
- tests/test_repair_count0_upto.py ＋ tests/test_data_audit.py ＋ tests/test_vocab_round333_cards.py ＋ tests/test_rules.py: **56 passed**（round333 disposition の既存失敗は解消）。

### 収支

- converted **10,227（不変）** / rejects **2,096（無編集）**。変更は converted.yaml の count 行11行＋テスト＋docs のみ。プロトは不使用。
- 次の番号は不変: パイロット300 / ラウンド335 / プロト T907。
- 残件: break 2件（dmx05-s03 / dmx11-023）のイディオムへの再変換（上記に正形を記録済み）。→ 追補2で解消（次節）。

## 修繕ステージ（追補2）: 「自分のシールドを墓地に置く」条項の再変換

前節の残件（break 2件のイディオム再変換）を、パイロット番号を消費しない独立の修繕ステージとして実施した。あわせてセンサスで同種の誤用を洗い出し、対象は4件になった。

### センサス（op break {player: you} 全件照合）

op break は converted 全体で115件、うち player: you は32件。各カードの本文を照合した結果:

- **本物のブレイク28件は無変更**: 本文はいずれも「自分のシールドを（〜つ／好きな数／すべて）ブレイクする（してもよい）」で、ブレイク＝手札＋S・トリガー宣言が正しい（dm22ex2-1a、dm23ex2-chog004、dm24ex1-002 / 037、dmrp22-016（「そのS・トリガーを使ってもよい」明記）等）。dmr12-010 は text フィールドが「G・リンク」のみで条項を照合できないため無変更とした。
- **誤用は4件**: いずれも本文は「シールドを墓地に置く」であり、break（割ったシールドを手札へ送る）では一致しない。当初対象の任意コスト2件に加え、必須形2件が同じ誤用だった。

### 是正した4件

- **dmx05-s03 ザビメテウス・武者・BLACK**（任意コスト）: 攻撃誘発の effect を choose＋if＋move のイディオム（dmex01-026 と同形）へ組み替え。when（自分のエイリアンの攻撃）は不変。後続はパワー6000以下1体破壊。
- **dmx11-023 偽りの星夜 コングラチュレーション**（任意コスト）: CIP を同イディオム（dmd08-019 と同形）へ。後続は相手が自身のクリーチャー2体を選んで破壊（chooser: opp、count: 2）。
- **dmsd07-008 セツナノ裁徒**（必須）: 離脱誘発の break {count: 1} を move {select: {zone: shield, owner: you, count: 1}, to: graveyard, reason: put} へ。
- **dmx11-007 ボルカニック・アロー**（必須）: 呪文の第2ステップの break {count: 1} を同じ move 形へ（第1ステップの破壊は不変）。

各カードの source.notes に是正記録を追記。変更は converted.yaml の4カードの能力ブロック＋notes のみ（73 insertions / 31 deletions）、ヘッダーコメント保持。

### 挙動証明（tests/test_repair_break_selfshield.py、7件）

修繕前（使い捨てプローブで実測）: dmx11-023 / dmx05-s03 はシールド5→5のまま後続の破壊が無条件で発火。dmx11-007 / dmsd07-008 はシールドが墓地ではなく**手札**へ行った。

修繕後: **7 passed** — 棚卸し（4件に break op が残らない、イディオム形の固定、player: you の break 残存は本物の28件のみ、件数不変）＋実挙動6件:
- dmx11-023: 払ったシールドの cid が墓地にあること、手札に行かないこと、相手2体が破壊されること、S・トリガー宣言もブレイクイベントも発生しないこと。辞退（0枚選択）では破壊が発火しないこと。
- dmx05-s03: 攻撃時に払えば墓地へ行き T004 が破壊されること。辞退では破壊が発火せず自分のシールドも不変なこと。
- dmx11-007 / dmsd07-008: 選んだシールドが墓地へ行き、手札へ行かないこと。

### ブックキーピング

- tests/test_repair_opcount0.py の「break 2件は count: 0 のまま残置」という固定を、本ステージの是正済み状態（break op は残らず、mill / break の count: 0 は converted に1件も残らない）に更新した。

### 回帰

- tests/test_repair_break_selfshield.py: **7 passed**。
- tests/test_repair_opcount0.py ＋ tests/test_repair_count0_upto.py ＋ tests/test_data_audit.py ＋ tests/test_rules.py: **58 passed**。

### 収支

- converted **10,227（不変）** / rejects **2,096（無編集）**。変更は converted.yaml の4カード＋テスト2ファイル＋docs のみ。プロトは不使用。
- 次の番号は不変: パイロット300 / ラウンド335 / プロト T907。
- 残件: なし（count: 0 系の不発形は converted から一掃された）。

## 第300弾 skip_turn_remainder（ターンの残りをとばす）

センサス（2026-11-20、rejects 2,096件を再集計）: 純粋ファミリーは最大でも4件止まりで、その4件組（victory_icon_filter 等）はすべて評価済み（延期・異種混合）。単一ギャップ行のうち未評価の候補を走査し、**skip_turn_remainder** を選定した。純粋3件、rejects 全体でもこのギャップを含む行は3件のみ（多重ギャップ行に現れない）。

### 対象（3件）

- **dm26ex4-031 / dm26ex4-sec012 切札混成 ゴッド・タイム**（同名・同コスト7・パワー12000・水/火・キーワード [ex_life, speed_attacker, triple_breaker] の2印刷。partial に能力なし。本文の差は EXライフ注釈文の有無のみ）: CIP「出た時、相手のパワー5000以下のクリーチャーをすべて破壊する」＋「このクリーチャーの「EXライフ」シールドが離れた時、ターンの残りをとばしてもよい」。
- **dmr21-021 時の宮殿 ベルファーレ**（コスト6・パワー6000・光/水。partial に革命チェンジの declare 能力あり）: 「このクリーチャーが破壊された時、または、自分のシールドがブレイクされた時にこのクリーチャーがタップしていれば、そのターンの残りをとばす」。

### 結論: ギャップ名ドリフト（新規語彙・エンジン変更なし）

「ターンの残りをとばす」は既存の **op end_turn** そのもの（第203弾・プロト T510 で実証済み。converted に14件の使用例）。エンジン側は `s.skip_rest = True` を立て、残りのステップをすべて飛ばして次のプレイヤーのターンへ移る。**「ターンの終わりに」誘発は発火しない**（公式FAQ qa/39060: ターンをとばした場合、「ターンの終わりに」能力は誘発しない。解決中の効果以外の待機中効果も無効化される）— エンジンの挙動と一致する。戦闘中（combat.py）でも skip_rest が検査される。

### 3つの形

- **形A（ゴッド・タイム、任意）**: `{kind: trigger, when: {event: move, from: shield, subject: {exlife_of: self}}, effect: [{op: may, body: [{op: end_turn}]}]}`。EXライフシールド離脱の誘発は第291弾の共通形。**任意化は効果先頭の {op: may, body: [...]} で書く**（プロト T010/T026 の先例）。誘発能力への `may: true` キーは無効（defs の ABILITY_KEYS に無い。`optional` は replace 種専用）— 初稿で踏んで修正した。
- **形B（ベルファーレ第1節、必須・条件なし）**: `{kind: trigger, when: {event: move, from: bz, to: graveyard, reason: destroy, subject: self}, effect: [{op: end_turn}]}`。
- **形C（ベルファーレ第2節、必須）**: `{kind: trigger, when: {event: break, player: you}, if: {exists: {ref: self, filter: {tapped: true}}}, effect: [{op: end_turn}]}`。タップ条件の if イディオムは第290弾 dm25bd2-003 の形。

### 解釈判断（ラウンド335で再確認すること）

ベルファーレの「タップしていれば」の条件は**第2節（シールドブレイク時）にのみ付く**と解した。根拠: 条件は第2のタイミング句に読点なしで直結しており（「ブレイクされた時にこのクリーチャーがタップしていれば」）、両節共通の条件なら通常は選択肢全体の後に置かれる。公式FAQでの裏取りは未了（DM wiki の汎用ページでは確認できず）— ラウンドで再確認する。実務上も、革命チェンジでタップ状態で出る本カードの防御的用法は第2節側が本命。

### ラウンド335への申し送り

- ゴッド・タイム: canon 側（dm26ex4-031）を登録し、sec012 は alias に畳む想定。partial に能力が無いため提出形は [CIP（dm23bd1-005 の destroy マクロ形、power_le 5000）, 形A] ＋ partial のキーワード3件で構成する。
- ベルファーレ: 提出形は partial（革命チェンジ declare）＋形B＋形C。本文1行目「マナゾーンに置く時、このカードはタップして置く」は dm10-037 の先例では追加フィールドなし（スプリット側の扱い）— ラウンドで確認。

### プロト（T907–T909）

- T907 試験用EXライフ時跳獣（水・コスト5・パワー5000・ex_life・形A）
- T908 試験用破壊時跳獣（水・コスト4・パワー3000・形B）
- T909 試験用盾破時跳獣（光・コスト4・パワー3000・形C）

### テスト

- tests/test_vocab_pilot300.py: **9 passed** — parse、形A（ブレイク yes で跳ぶ / no で継続＝相手2体目も攻撃する判別 / 普通のシールドでは不発 / 破壊呪文→EXライフ置換経由でも yes で唱えた側のターンが終わる）、形B（破壊で跳ぶ / 他のクリーチャーの破壊では不発）、形C（タップ中ブレイクで跳ぶ / アンタップ中ブレイクでは跳ばず次ターンに進む判別）。
  - テスト作成中の教訓: (1) ブレイク対象の選択フックは**毎回**選ぶこと（2回目のブレイクが無制御だと EXライフシールドを割り直して誤判定する）。(2) 破壊対象が1件だけの select は決定を出さず自動確定する（eng.ask の mn==mx==候補数）。(3) 攻撃決定は min 1 で、「攻撃しない」は空回答でなく `pass` キー。
- tests/test_vocab_pilot300_cards.py: **3 passed** — 対象3件が純粋行・未登録・ファミリーがこの3行のみ、2印刷の同一性（注釈差のみ）、提出形の parse（CIP は parse 後に destroy マクロが move へ展開される形で照合）。

### 回帰

- 実挙動バッチ: test_vocab_pilot300 ＋ 第291弾 ＋ 第297弾 ＋ 第203弾: **31 passed**。
- カード側バッチ: test_vocab_pilot300_cards ＋ test_data_audit ＋ test_rules: **51 passed**。
- 既知の事前失敗2件（第274弾 test_floor_zero_colored_pays_civ_count、第31弾 test_janken_win_draws）は本弾の範囲外として未追跡。

### 収支

- converted **10,227（不変）** / rejects **2,096（不変）**。変更は proto.yaml（T907–T909）＋テスト2ファイル＋docs のみ。エンジン・スキーマ・データ監査への変更なし。
- 次: ラウンド335（skip_turn_remainder の再変換）/ パイロット301 / プロト T910。

### ラウンド335（skip_turn_remainder の再変換）

- **新規登録2件**: dm26ex4-031 切札混成 ゴッド・タイム（canon。partial のキーワード3件＋CIP（dm23bd1-005 の destroy マクロ形）＋形A で登録。提出後の登録形は abilities == [CIP, 形A]・keywords == [ex_life, speed_attacker, triple_breaker] で、submit の連結／merge_split 由来の混入なしを本文と照合済み）、dmr21-021 時の宮殿 ベルファーレ（partial の革命チェンジ declare ＋形B＋形C。登録形は [declare, 形B, 形C]・keywords == [double_breaker] で混入なし）。
- **alias 畳み込み1件**: dm26ex4-sec012 は reopen で行を外し、dm26ex4-031 の登録時に validate の aliases_for が source.aliases に自動付与。提出後に「独立エントリではない／031 の aliases に在る／rejects に残らない」の3点を実測確認。
- **差し戻し・stale 解消は0件**。converted **10,227 → 10,229** / rejects **2,096 → 2,093**、canonical overlap 0・漏れ 0。skip_turn_remainder は rejects に残り0件で解消。
- **再確認 (a) タップ条件の範囲**: 公式FAQ（dm.takaratomy.co.jp/rule/qa/）と DM wiki を検索したが、本カード個別の裁定は見つからなかった（汎用「ターンの残りをとばす」ページが引く公式Q&A qa/39060・qa/31817 はいずれも本件に触れない）。したがって第300弾の文法判断（条件「このクリーチャーがタップしていれば」は読点なしで第2のタイミング句に直結するため第2節にのみ付く）を**解釈として採用**し、ベルファーレの source.notes にも明記した。
- **再確認 (b) 1行目「マナゾーンに置く時、このカードはタップして置く」**: dm10-037 アクア・リバイバーの converted 登録形は同一文を持ち、フィールド・能力のいずれでも表していない（本文のみ）ことを実測で確認。先例は正確に一致するため、ベルファーレも追加フィールドなしで扱った。
- テスト: tests/test_vocab_round335_cards.py（disposition＋登録形の実挙動4件: 形A 破壊置換経路で yes→跳ぶ、形B アンタップで破壊されても必須で跳ぶ、形C タップ中ブレイクで跳ぶ／アンタップでは跳ばない判別）＋ tests/test_vocab_pilot300_cards.py を登録形に書換（3件）＋ tests/test_data_audit.py 8件 = **16 passed**。プロト側の回帰として tests/test_vocab_pilot300.py **9 passed**（別プロセス）。
- 回答は answers/round335.yaml に保存。次: パイロット301 / ラウンド336 / プロト T910。

## 第301弾 reveal_stay（山札の上を見て／置いて、合えばとどまる）

センサス（2026-11-20、rejects 2,093件を再集計）: 純粋3件以上の未評価ファミリーは残っておらず、純粋3件は reveal_stay / wd_field 系（場ゾーン新設級）/ cost_may_per_count＋up_to_cost_reduction（任意コスト軽減クラスタ）/ gachinko_break_count（ドリフト濃厚）等が並ぶ。3件の partial がそろって「置換の instead 内で条件を見て元の移動を再適用する手段が無い」と同一の不足を書いている **reveal_stay** を選定した（純粋3件、多重ギャップ行には現れない。第4の出現 dmrp22-005 は誤ラベル — 後述）。

### 対象（3件）

- **dmr05-v03 黄金世代 鬼丸「爆」**（火・コスト13・パワー13000・進化・[triple_breaker]。partial は能力なしのスケルトン）: 第1節「破壊される時、山札の上から1枚目をすべてのプレイヤーに見せる。それがヒューマノイドであれば、墓地に置かれるかわりにバトルゾーンにとどまる」＋第2節「破壊された時、このクリーチャーの下にあったクリーチャーをすべて、墓地からバトルゾーンに出してもよい」。
- **dmx15-006 夢幻界廊 ヴァリアント**（火・コスト7・パワー7000・アウトレイジ・[double_breaker]。partial は能力なし）: 「バトルゾーンを離れる時、自分の山札の上から1枚目を墓地に置いてもよい。そのカードがアウトレイジであれば、離れるかわりにとどまる」。
- **dmx16-006 インフィニティ・ドラゴン**（火・コスト7・パワー7000・アーマード・ドラゴン・[double_breaker]。partial は能力なし、source.aliases に4印刷）: 「自分のドラゴンがバトルゾーンを離れる時、自分の山札の1枚目を墓地に置く。そのカードがドラゴンまたはファイアー・バードであれば、そのドラゴンは離れずにとどまる」。

### 結論: 新規 op **move_to_event** を追加（エンジン変更あり）

不足は partial の注記のとおり1点だけ: 置換された元の移動を、条件を見て instead 内から再適用する手段。先例は G・NEO の離脱置換用 op **move_under_to_event**（第184弾: イベントレコードの to / reason / position を引き継いで下のカードを移す）。本弾はその一般化として、select で選んだカードをイベントの行き先へ移す **move_to_event** {select} を追加した（ops.py + opvocab.py + スキーマ再生成、差分は新 op の16行のみ）。再適用した移動は ev_task の no_replace 環境で起こすため再置換されず、行き先・理由・位置に加えて効果帰属（by / cause / cause_defn / cause_kind）もレコードから引き継ぐ。イベントが無い文脈・行き先が bz の場合は何もしない。

### 設計上の要点: instead 内では「choose 束縛 → 判定 → 移動発行」の順

初稿の形B/C は「move で墓地に置いて as 束縛し、if で見る」形だったが、実測で条件が常に不成立になった。理由: instead 内の移動は capture され（609.9 の同時適用）、束の適用は instead 全体の解決後。move の as 束縛は h_bind が移動先ゾーンで照合するため適用前に走ると空になり、移動したカードの ref も gen が増えて失効する。したがって確立形は **choose で先に束縛し（choose は選択時点で束縛する）、ref が生きている間に判定し、最後に移動を発行する**。なお converted の MAX 系敗北置換（dm23-008 / dm23-017）が使う「山札→山札の move で見る」形は、移動元と移動先が同じゾーンのため束縛が成立する同問題の回避形で、本弾の調査で壊れていないことを確認した（本弾の形とは別系統）。

### 3つの形

- **形A（dmr05-v03、破壊のみ・公開形）**: `{kind: replace, when: {event: move, from: bz, to: graveyard, reason: destroy, subject: self}, instead: [{op: choose, select: {zone: deck, owner: you, from_top: 1, count: 1}, reveal: true, as: top}, {op: if, cond: {not: {exists: {ref: top, filter: {race_has: ヒューマノイド}}}}, then: [{op: move_to_event, select: {ref: event.subject}}]}]}`。合えば元の破壊は置換されたまま＝とどまり、外れれば破壊を再適用する（公開はどちらの場合も行われる）。第2節は第294弾の既存形 `{kind: trigger, when: {…destroy, subject: self}, effect: [{op: may, body: [{op: play_free, select: {ref: event.was_under, zone: graveyard}}]}]}` で、再適用された破壊レコードから通常どおり誘発する（とどまった場合は誘発しない）。
- **形B（dmx15-006、離脱全般・任意）**: 置換 when は行き先・理由を絞らない `{event: move, from: bz, subject: self}`。instead は `[{op: may, body: [{op: choose, select: {zone: deck, owner: you, from_top: 1, count: 1}, as: picked}]}, {op: if, cond: {exists: {ref: picked}}, then: [{op: move, select: {ref: picked}, to: graveyard, reason: put}]}, {op: if, cond: {not: {exists: {ref: picked, filter: {race_has: アウトレイジ}}}}, then: [{op: move_to_event, select: {ref: event.subject}}]}]`。may は中身を見ない盲目の任意選択（「置いてもよい」の忠実な形）で、置かない選択でも離れる。再適用先はイベント依存（バウンスなら手札、破壊なら墓地）。
- **形C（dmx16-006、監視者形）**: 置換 when は `{event: move, from: bz, subject: {owner: you, filter: {types: [creature], race_has: ドラゴン}}}`（other: true は付けない — 監視者自身もドラゴンなので対象に含む）。instead は `[{op: choose, select: {zone: deck, owner: you, from_top: 1, count: 1}, as: seen}, {op: move, select: {ref: seen}, to: graveyard, reason: put}, {op: if, cond: {not: {any: [{exists: {ref: seen, filter: {race_has: ドラゴン}}}, {exists: {ref: seen, filter: {race_has: ファイアー・バード}}}]}}, then: [{op: move_to_event, select: {ref: event.subject}}]}]`。ミルは必須。相手のドラゴン・ドラゴンでない味方の離脱は監視しない。

### プロト（T910–T916）

- T910 試験用公開滞留進化獣（火・コスト6・パワー7000・進化・形A＋第2節）
- T911 試験用任意滞留獣（火・コスト7・パワー7000・形B）
- T912 試験用竜見守獣（火・コスト7・パワー7000・形C）
- T913–T916 ダミー（アーマード・ドラゴン／ヒューマノイド／アウトレイジ／ファイアー・バード）

### テスト

- tests/test_vocab_pilot301.py: **13 passed** — parse＋形の一致、move_to_event の登録（OP_ARGS＋スキーマ）、形A（合致で残留＋スタック無事＋公開記録＋第2節不発／不一致で破壊＋公開記録＋第2節で下のカードが復帰）、形B（合致でバウンス回避／不一致で手札へ／置かない選択でも手札へ・山札不変）、形C（ドラゴン落としで残留／ファイアー・バードで残留／不一致で破壊・ミル必須／監視者自身も残留／相手のドラゴンは無監視・ミルなし／非ドラゴンは無監視・ミルなし）。
- tests/test_vocab_pilot301_cards.py: **2 passed** — 対象3件が純粋行・未登録、reveal_stay の出現は対象3件＋誤ラベル dmrp22-005 のみ、提出形（partial＋確立形、unsupported 除去）の parse。

### 回帰

- 実挙動バッチ: 第299弾＋第297弾＋第283弾（eternal_kappa）＋第300弾＋第33弾（G・NEO）＋ test_rules ＋ test_data_audit ＋ test_rust_schema_sync: **101 passed**。
- カード側バッチ: 第299弾 cards ＋ 第283弾 cards: **9 passed**。
- 既知の事前失敗2件（第274弾 test_floor_zero_colored_pays_civ_count、第31弾 test_janken_win_draws）は本弾の範囲外として未追跡。
- Rust: ops.py の変更でスタンプは stale になるが、この VM では Rust コア未ビルドのため認可済みの Python フォールバック（結果不変）。

### 収支

- converted **10,229（不変）** / rejects **2,093（不変）**。変更は dmsim/engine/ops.py（move_to_event 追加）＋ dmsim/base/opvocab.py ＋ data/schema/card.schema.json（再生成、新 op のみ）＋ proto.yaml（T910–T916）＋テスト2ファイル＋docs。

### ラウンド336側の注意

- 対象3件は tests/test_vocab_pilot301_cards.py の FORMS の形で提出する。dmr05-v03 の partial は能力なしのスケルトンなので、第1節（形A）と第2節（event.was_under 形）の両方を足すこと。
- dmx16-006 の partial の source.aliases に4印刷（dm22-015 / dmc36-017 / dmc49-019 / dmx09-018）がある — 畳み込みの扱いはラウンド側で実測確認すること。
- **dmrp22-005 の reveal_stay は誤ラベルとして行を残す**（unsupported の実体は「山札の上をこのターンの終わりまで表向きにする」条項＋ play_from_deck_top。ラベル訂正は記録のみ、promoy11-011 の先例どおり行自体には触らない）。本セクションと MEMORY 側の記録で足りる。
- promoy11-011（gachinko 勝ち条件付き・ターン限定の付与形）は本弾の対象外のまま。

### ラウンド336 reveal_stay 再変換（第301弾）

- **新規登録3件**: dmr05-v03 黄金世代 鬼丸「爆」（形A＋第2節。partial は能力なしのスケルトンだったため両節を追加。登録形は abilities == [形A, 第2節]、keywords == [triple_breaker] で、submit の連結／merge_split 由来の混入なしを本文と照合済み。submit の助言 lint「play_free/reason: summon」は第294弾の確立形（event.was_under＋play_free）を踏襲して不採用）/ dmx15-006 夢幻界廊 ヴァリアント（形B、abilities == [形B]、keywords == [double_breaker]）/ dmx16-006 インフィニティ・ドラゴン（形C、abilities == [形C]、keywords == [double_breaker]）。
- **alias 畳み込み1件（4印刷）**: dm22-015 / dmc36-017 / dmc49-019 / dmx09-018 は全て canon = dmx16-006（identity で実測）で、dmx16-006 の source.aliases に畳み込まれた。4件とも独立エントリではなく、reject 行も元々無し（提出前照合で real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted のいずれにも無いことを確認）。
- **差し戻し・stale 解消 0件**。dmrp22-005 は誤ラベルのまま行を残置（reveal_stay の残存はこの1行のみ。実体は別条項＋play_from_deck_top）。
- **収支: converted 10,229 → 10,232 / rejects 2,093 → 2,090、canonical overlap 0・漏れ 0**。reveal_stay は対象3件で解消。
- テスト: tests/test_vocab_round336_cards.py（disposition＋登録形の実挙動6件: 形A 合致で滞留／不一致で破壊＋第2節で下のカードが復帰、形B 合致でバウンス回避／不一致で手札へ再適用、形C ドラゴン落としで滞留／不一致で破壊・ミル必須）＋ tests/test_vocab_pilot301_cards.py を登録形に書換（2件）＋ tests/test_data_audit.py（8件）= **17 passed**。
- 回答は ~/workspace/DMPJ-work/answers/round336.yaml に保存。次の番号: パイロット302 / ラウンド337 / プロト T917。

## 第302弾 gachinko_break_count（勝ち数でブレイク）はイディオム（ドリフト）

センサス（rejects 2,090件を再集計）: 純粋ファミリーの最大は範囲外（gr_summon 147、aura 108 = 未承認、hyperdimensional_zone 105、dragheart 45、psychic_filter 45、hyperdimensional_summon 41、out_of_game 23、duelist_link 20、outside_game 12、pandora_shift 4）が占め、在範の純粋3件組も大半が評価済み DEEP／延期（victory_icon_filter、dokindam_gacha、cost_sum_of_revealed、copy_abilities、ignore_abilities、all_civs_treatment 等）。未評価で均一な **gachinko_break_count 純粋3件**（多重ギャップ行への出現なし）を選定: dm26rp2-tr009 / dmex12-009（同名カード R.S.F.K. の2印刷）と dmr05-v02（鬼無双 カイザー「勝」）。3件の partial がそろって「ブレイク数を勝ち数（変数）で増やす表現が無い」という同一の不足を明記していた（ラウンド169の判断）。

結論はギャップ名ドリフト — 新規 op・フィールド・スキーマ変更なし。不足は読みの取り違えと既存イディオムの未適用で、対象は次の2形に分かれる:

- **形A（カイザー「勝」型 = その攻撃自体のブレイク数への加算）**: 本文は「勝つたび…シールドを**さらに**1枚ブレイクし」。partial が既に持つ gachinko {until_lose: true, stoppable: true, as: wins} + repeat {times: {var: wins}} の body に、**modify {breaks_add: 1}（duration: end_of_turn）を1ステップ足すだけ**（本文の順序どおりパワー+6000 の後、ブロッカー破壊の前）。breaks_add の modify 形はドギラゴン・ガチャの出目3（ops.py の _gacha_spin_ops: 「このターンの終わりまでシールドをさらに1枚ブレイクする」）で確立済みで、第255弾の breaks_add {amount, count} 集約（break_opts の各値へ加算）に乗る。
- **形B（R.S.F.K.型 = 誘発の効果としてブレイク）**: 本文は「その後、こうして自分が勝った回数、このクリーチャーは相手のシールドを1つブレイクする」で「さらに」が無い。形は attack 誘発 **[gachinko {until_lose: true, stoppable: true, as: wins}, break {player: opp, count: {var: wins}}]**。op break の count は expr で、{var: wins} の後続参照は dmr05-v02 の partial 自身（repeat）と tr009 の呪文面（if {var: wins}）が使っている確立形。読みの裏取りは公式QA: qa/42524（「効果で相手のシールドを5つブレイクする際、それらは同時にブレイクしますか？」— 効果ブレイクとして同時処理が前提）、2023.5.17 の一連のQA（終納 カボード＝ロウで R.S.F.K. が破壊された後／革命チェンジで入れ替わった後でも、能力のブレイク数が問われる = 攻撃自身のブレイクではなく能力の効果として成立する前提。qa/42846 ほか）。ラウンド169の「ブレイク数を変数で増やす」読みは形Aへの誤読だった。

実挙動で固定した判別: 形Bはブロックより前に割れる（ブロッカーで受けても効果の勝ち数ぶんは割れたまま）。形Aは誘発中1枚も割らず、攻撃のブレイク（choose_shields は1件だけ）に勝ち数が加算される。

- プロト T917（形B）・T918（形A。speed_attacker は検証用の便宜で実カードには無い旨を text に明記）。次の空きは T919。
- tests/test_vocab_pilot302.py: **7 passed** — parse、形B（2勝→誘発中に2枚＋攻撃で1枚／ブロックされても効果1枚は割れる判別／即負けで count 0 の決定のみ・割れない／1勝1敗で1枚）、形A（2勝→パワー19000・ブロッカー2体破壊・攻撃ブレイク4枚／即負けで通常 W・ブレイカー2枚・パワー不変）。
- tests/test_vocab_pilot302_cards.py: **2 passed** — 対象3件の純粋行・未登録、gachinko_break_count の出現は対象3件のみ、提出形（dmex12-009 = partial＋形B、tr009 = クリーチャー面に形B、dmr05-v02 = partial の repeat body へ BREAKS_STEP 挿入で FORM_A_TRIGGER と完全一致）の parse。

### 回帰

- 実挙動バッチ: 第223弾（ガチンコ基盤）＋第255弾（breaks_scaling）＋第301弾＋第297弾（ブレイク諮問）＋ test_rules: **72 passed**。
- カード側バッチ: 第302弾（7＋2）＋第301弾 cards＋第223弾 cards＋ test_data_audit: **27 passed**。
- 既知の事前失敗2件（第274弾 test_floor_zero_colored_pays_civ_count、第31弾 test_janken_win_draws）は本弾の範囲外として未追跡。エンジン変更なしのため Rust スタンプ・スキーマは不変。

### 収支

- converted **10,232（不変）** / rejects **2,090（不変）**。変更は proto.yaml（T917–T918）＋テスト2ファイル＋ docs のみ。

### ラウンド337側の注意

- 対象3件は tests/test_vocab_pilot302_cards.py の FORMS（FORM_B / FORM_A_TRIGGER）の形で提出する。dmr05-v02 は partial の repeat body に BREAKS_STEP を1つ挿入するだけ（提出形は FORM_A_TRIGGER と完全一致が正本）。dm26rp2-tr009 はツインパクトで、形Bはクリーチャー面に足す（呪文面は partial のまま）。dmex12-009 は abilities に形Bを足す。
- alias は partial の source.aliases に既存（dmex12-009: dmr08-004 / dmx22b-079、dm26rp2-tr009: dm22bd3-008 / dm22ex1-030 / dmart19-004）— 畳み込みの扱いはラウンド側で実測確認すること。
- 形Bの効果ブレイクで割れたシールドの S・トリガーは op break の確立挙動（効果の処理が終わってから解決、101.4d）に従う。ブレイクの帰属（breaker）は break タスクの env self = このクリーチャー。
- dm24ex3-rp2s08 の zone: hand 欠落の修繕債務は、本弾のファミリーがコスト軽減形でないため手つかず（従来どおり別ステージ扱い）。

### ラウンド337 gachinko_break_count 再変換（第302弾）

- **新規登録3件**: dm26rp2-tr009 R.S.F.K. / オールイン・チャージャー（ツインパクト。クリーチャー面に形Bを追加、呪文面は partial のまま。登録形は faces[0].abilities == [形B]、keywords == [speed_attacker] で、submit の連結／merge_split 由来の混入なしを本文と照合済み）/ dmex12-009 R.S.F.K.（形B、abilities == [形B]、keywords == [speed_attacker]）/ dmr05-v02 鬼無双 カイザー「勝」（形A。partial の repeat body に BREAKS_STEP を挿入し、登録形は FORM_A_TRIGGER と完全一致、keywords == [double_breaker]）。
- **identity の確認**: tr009 と dmex12-009 は同名カードの2印刷だが、identity の canon_id は各自自身（ツインパクトと通常版は別々の正本エントリ）だったため、畳み込みではなく**両方を独立に登録**した。
- **alias 畳み込み0件・stale 解消0件・converted 是正0件・差し戻し0件**。alias は partial の source.aliases のまま登録（tr009: dm22bd3-008 / dm22ex1-030 / dmart19-004、dmex12-009: dmr08-004 / dmx22b-079）。5件とも独立エントリではなく reject 行も元々無い（提出前照合で real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted のいずれにも無いことを確認。proto.yaml 内の言及は第302弾プロト T917/T918 の本文のみ）。
- **converted 側センサス（ラウンド169の誤読の有無）**: 登録前の converted で gachinko と breaks_add を併せ持つカードは **0件**（gachinko を含む56件は全て breaks_add なし、breaks_add を含む18件は全て gachinko なし）。ラウンド169の「効果ブレイクを攻撃のブレイク数への加算と読む」誤読は converted に登録されていなかったため、是正対象なし。登録後に併せ持ちになるのは形Aの本物 dmr05-v02（本文に「さらに」あり）だけであることを round337 cards テストで固定。
- **収支: converted 10,232 → 10,235 / rejects 2,090 → 2,087、canonical overlap 0・漏れ 0**。gachinko_break_count は rejects に残り0件で解消。
- テスト: tests/test_vocab_round337_cards.py（disposition＋登録形の実挙動5件: 形B 2勝で効果2枚→攻撃1枚／ブロックされても効果1枚は割れる判別／ツインパクト面で1勝、形A 2勝で攻撃ブレイク4枚・パワー+12000・ブロッカー2体破壊／即負けで通常 W・ブレイカー）＋ tests/test_vocab_pilot302_cards.py を登録形に書換（2件）＋ tests/test_data_audit.py（8件）= **16 passed**。
- 回答は ~/workspace/DMPJ-work/answers/round337.yaml に保存。次の番号: パイロット303 / ラウンド338 / プロト T919。

## 第303弾 dragonic_field（ドラゴニック・フィールド）— 型印の追加、能力は既存語彙

センサス（rejects 2,087件を再集計）: 純粋ファミリーの最大は範囲外（gr_summon 147、aura 108 = 未承認、hyperdimensional_zone 105、dragheart 45、psychic_filter 45、hyperdimensional_summon 41、out_of_game 23、duelist_link 20、outside_game 12、pandora_shift 4）が占め、在範の純粋ファミリーは全て4件以下で大半が評価済み DEEP／延期（victory_icon_filter、dokindam_gacha、cost_sum_of_revealed、climax_dorongo、shield_manipulation、spell_replay、summon_lock、opponent_chooses_deck_position、dynamic_name_reference_filter、must_attack_next_turn、doron_go、cancel_attack、per_card_tap_or_untap、evolution_base_from_graveyard、untap_restriction、joe、break_limit、next_spell_cost_reduction、negate_cannot_attack、copy_abilities、ignore_abilities、all_civs_treatment、trigger_when_opponent_plays_free 等）。wd_field 系は第301弾センサスで「場ゾーン新設級」と評価済み。任意コスト軽減クラスタは _mana_choices のルール対立（第274弾 vs 第292弾）が未解決のため支払いフロー手術を避けた。未評価で均一な **dragonic_field 純粋3件**を選定: dm26ex3-067 / dmex12-011（同名カード 龍世界 〜龍の降臨する地〜 の2印刷）と dmex15-b027（切札の里）。3件とも partial は骨格のみで、unsupported は型名「ドラゴニック・フィールド」そのものだけ、本文は reject 行の text にのみある。historic_field 系（初手手札誘発が本体の別機構）は本弾に含めない。

鍵となる発見: フィールドというカードタイプ自体は既存である（D2フィールドが第25／151弾から動作し、converted の dm23ex2-056 ヒストリック・フィールドは types [field] で登録済み）。不足はサブタイプ名に対応する語彙だけだった。先例は型印 d2_field（第151弾）、dream_creature（第174弾）、exile_creature（第266弾）で、いずれも types に基本タイプと併記する形。converted 内に「ドラゴニック」を参照するフィルタは現状0件で、型印はタイプ行の忠実度と将来のフィルタのためのものである。

追加した語彙（最小）:

- **型印 `dragonic_field`** を defs の CARD_TYPES に追加。types は [field, dragonic_field] と併記する。
- 変換指示（tools/convert_cards.py）に併記を明記（「ドラゴニック・フィールドは ["field", "dragonic_field"] と併記する。ドラゴニック・フィールドだけを指すフィルタは {types: [dragonic_field]}」）。
- スキーマ再生成: 差分は型 enum の2箇所への "dragonic_field" 追加のみ。
- 新規 op・新規フィールド・エンジン変更はなし。能力は次の2形とも既存語彙で足りる:
  - **形A（龍世界）**: フィールドの turn_start 誘発（player: you。tick レコードに subject は無い＝第328弾の作法）。[move {zone: deck, owner: you, from_top: 1} → graveyard + as: milled（mill マクロは as を転送しないため明示形）、if {exists: {ref: milled, filter: {race_has: ドラゴン, not_types: [evolution]}}} → [may [move {ref: self} → graveyard, reason: destroy, as: gone]、if {exists: {ref: gone}} → [play_free {ref: milled}]]]。払えた場合だけ出すゲートは dmx18-003 の確立形。dmex12-011 の本文は「このドラゴニック・フィールドを墓地に置いてもよい」だが、バトルゾーンのカードを墓地に置くことは破壊である（701.6）ため 067 の「破壊してもよい」と同一形。
  - **形B（切札の里）**: 常在型2つ。(1) affects {owner: you, zone: hand, filter: {types: [creature], name_has: ボルシャック}} + mod cost_may {amount: 2, min: 1}（dm23ex2-097 等の先例形。ただし b027 の本文にターン制限は無いため once は付けない。「コストは0以下にはならない」= min: 1）。(2) affects {owner: you, zone: bz, 同フィルタ} + mod grant [speed_attacker]。

実挙動で固定した点: 形Aは 承諾（フィールド破壊＋ドラゴン着地＋墓地に残らない）／辞退（両方そのまま）／非ドラゴン（選択自体が出ない）／進化ドラゴン（not_types で除外、選択なし）／相手ターン不発火。形Bは 文明が一様なマナでは支払いが自動タップになり pay_mana 決定が出ない作法のため、軽減の提示（choose_cards の reduce / normal）と着地後のタップ数で観測した（reduce 3 / normal 5 / コスト2子竜の床 1 / フィールド無し 5・提示なし / 名前がボルシャックでない獣は素払い2・提示なし）。スピードアタッカー付与は、setup で bz に置いたクリーチャーは召喚酔いの対象にならない作法のため、手札から実行したそのターンに攻撃できるかで判別した。

- プロト T919（形A）・T920（形B）・T921（アーマード・ドラゴン）・T922（進化ドラゴン）・T923（ボルシャック獣、コスト5）・T924（ボルシャック子竜、コスト2 = 床の確認用）。次の空きは T925。
- tests/test_vocab_pilot303.py: **15 passed** — parse＋未知タイプの拒否、型印フィルタの帰結（T919 は dragonic_field／field 両方に一致、通常フィールド T069 は field のみ）、形A 5件、形B（chars の cost_may、支払い4件、スピードアタッカー2件）。
- tests/test_vocab_pilot303_cards.py: **2 passed** — 対象3件の純粋行・未登録、提出形（partial ＋ types 併記 ＋ text を reject 行から復元 ＋ 形A／形B）の parse。

### 回帰

- バッチ1: 第303弾（15＋2）＋ test_data_audit ＋ 第302弾（7＋2）＋ 第301弾 ＋ test_rules: **87 passed**。
- バッチ2: test_rust_schema_sync ＋ 第151弾（型印の先例）: **16 passed**。test_file_schemas ＋ 第151弾 cards: **7 passed, 1 skipped**（jsonschema 未導入によるスキップ）。
- 既知の事前失敗2件（第274弾 test_floor_zero_colored_pays_civ_count、第31弾 test_janken_win_draws）は本弾の範囲外として未追跡。_mana_choices には触れていない。

### 収支

- converted **10,235（不変）** / rejects **2,087（不変）**。変更は defs.py（型印）＋ tools/convert_cards.py（変換指示）＋ data/schema/card.schema.json（再生成）＋ proto.yaml（T919–T924）＋テスト2ファイル＋ docs のみ。

### ラウンド338側の注意

- 対象3件は tests/test_vocab_pilot303_cards.py の FORM_A / FORM_B の形で提出する。types は [field, dragonic_field] に差し替え、partial の text（型名のみ）を reject 行の text で置き換えること。
- 正本判定: dm26ex3-067 の partial は aliases 5件（dm23bd4-034 / dm24rp1-td2 / dm25sp2-010 / dmex16-002 / dmrp22-tr10）を持ち、dmex12-011 はその中に含まれず aliases も無い別行。第337弾の R.S.F.K. と同様に独立正本か、067 への畳み込みかはラウンド側で identity を実データ照合すること。
- dmex15-b027 の cost_may には once を付けない（先例 dm23ex2-097 等は本文にターン制限がある形で、b027 には無い）。
- dm24ex3-rp2s08 の zone: hand 欠落の修繕債務は手つかず。形Bの cost_may はフィールドが手札の獣へ与える軽減（affects の zone: hand）であり、rp2s08 の「自身の軽減常在型が手札で発火しない」問題とは別機構のため、本弾のファミリーには含めなかった。

### ラウンド338 dragonic_field 再変換（第303弾）

- **新規登録2件**: dm26ex3-067（龍世界 〜龍の降臨する地〜、形A）/ dmex15-b027（切札の里、形B）。**alias 畳み込み1件**: dmex12-011。差し戻し・stale 解消・converted 是正は0件。
- 正本判定（identity 実データ照合）: canon_id(dmex12-011) = dm26ex3-067 で、aliases_for（067 の名前）= [dm23bd4-034, dm24rp1-td2, dm25sp2-010, **dmex12-011**, dmex16-002, dmrp22-tr10] にも含まれるため、dmex12-011 は独立登録せず 067 の alias に畳み込んだ（第337弾の R.S.F.K. とは逆の結論で、根拠は canon_id の実測）。dmex15-b027 は canon_id が自身・aliases 無しで独立正本。
- reopen dragonic_field で対象3件だけが外れた（rejects 2,087→2,084）。submit 前照合: 対象 id と alias 8件すべて converted / real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml の実エントリに無し（proto のヒットは第303弾プロト T919/T920 の text 内参照のみ）。alias 5件には元々 reject 行が無く、行があったのは dmex12-011 だけ。
- 提出形は partial（骨格）＋ types [field, dragonic_field] ＋ text を reject 行の正式本文で復元 ＋ FORM_A / FORM_B。submit 後の登録形は abilities が提出形と完全一致し keywords の追加も無し（連結・merge_split 混入なし）。submit の助言 lint（067 の play_free/reason: summon に対し本文は「出す」）は第303弾の確立形（play_free の着地は 112.3g で召喚として数える）のため形を変えていない。
- converted **10,235→10,237** / rejects **2,087→2,084**、canonical 重なり0・漏れ0（対象3件は converted id 2件＋alias 1件に解決）。dragonic_field 解消。なお converted の alias 全体では alias∩rejects の stale が9件残るが、いずれも本ラウンド対象外の既存分。
- テスト: tests/test_vocab_round338_cards.py（disposition＋登録形の実挙動4件: 形A 承諾／辞退、形B 軽減支払い3／床1）＋ tests/test_vocab_pilot303_cards.py を登録形に書換（2件）＋ test_data_audit（8件）: **15 passed**。
- 回答は ~/workspace/DMPJ-work/answers/round338.yaml に保存。次の番号: パイロット304 / ラウンド339 / プロト T925。

## 第304弾 evolution_cross_gear（進化クロスギア）— 進化元プールのギア対応＋新許可 evolve_civ_any

センサス（rejects 2,084件を再集計）: evolution_cross_gear は純粋3件（dmc42-017 ツナミ・カタストロフィー / dmc45-017 龍刃 ヤマト・スピリット / dm17-s05 グランドクロス・カタストロフィー）＋第2ギャップ付き3件（dmc42-001 = evolution_base_any_race〔第232弾で実装済み〕、dmc66-034 = dynamic_name_reference_filter、dm17-004 = same_name_sweep、dm17-s04 = reveal_and_cast_free）。共通条項は「進化-自分のXクロスギア１枚の上に置く」で、3件の partial は能力側がほぼ完成形、unsupported は進化クロスギアそのものだけ。本弾は見守り側の設計メモ（pilot297-evolution-cross-gear-design.md、2026-11-20 02:45 の見守り実行で作成）の実装であり、対象は純粋3件＋dmc42-001（両ギャップとも本弾で揃う）。

詰まりは4点で、いずれも最小変更で解消した:

1. **進化元プールがクリーチャー限定**（turn.py `_evo_pool_zone` の bz 分岐は creature か evolve_base 許可のみ）。進化する面が cross_gear の時（`_evo_for_gear`）はプールをクロスギアのトップだけに替える `for_gear` を `_evo_pool` / `_evo_filter_pool` からスレッドした。クリーチャーは文明・種族が合ってもギアの進化元にならない。ベースはクロス済みでなくてよい（本文に条件なし）。ギア進化は既定ゾーン（自分のバトルゾーン）しか使わないが、shield 分岐にも同じ絞り込みを入れた。
2. **h_play の permanent 分岐が進化重ねを扱っていなかった**。クリーチャー形と同じく `stack_on` / `evolution` / `stack_more` を move イベントに載せる（`_apply_one` の重ね処理と `_stack` は元々タイプ不問）。進化元の選択（`_evo_sources` 経由）と `_can_play_face` の evolution 分岐も元々タイプ不問で、そのまま動く。
3. **_stack の crossed 引き継ぎ**（events.py）: crossed（クロス先）は束のトップだけが持つ。top・base ともに cross_gear の時、進化元がクロスしていたら進化後のギアへ引き継ぎ、元のギアからは外す。そうしないと進化後のギアが未クロス扱いになり、affects: crossed の常在型が壊れる（実挙動: クロス済み水ギア +1000 → 進化ギア +2000 に切り替わることを固定）。
4. **_rebuild のギア対応**（events.py）: トップだけが card_only で離れる時、下のカードはクリーチャーしか残らなかった（ギアは墓地に落ちていた）。クロスギアも単独で存在できるので残し、新トップがクロスギアなら crossed を引き継ぐ（下のギアがクロスしたまま場に残る）。

新許可 **`evolve_civ_any`**（data/rules/permissions.yaml、dmc42-001 条項b「このクロスギアに、好きな文明の進化クロスギアを置いてもよい」）: `_evo_match` に `_evo_race_waived` と対の `_evo_civ_waived`（civs / civs_all を除いて照合、any_of の枝ごと）を追加。種族など文明以外の指定は肩代わりしない（実挙動: レオパルド〔自然〕に civs 形は重なるが races 形は重ならないことを固定）。allow 検証は permissions.yaml の actions に無いと弾かれるため登録必須。スキーマ再生成の差分は allow/deny enum への "evolve_civ_any" 追加4箇所のみ（設計メモの「差分0」見込みは外れた: allow の enum は permissions 由来だった）。

既存イディオムで足りる条項（新規コードなし）:

- dmc42-001 条項(a): static {affects: crossed, mod: {allow: [evolve_base_any]}}（先例 dm32-110、ラウンド268。第232弾の許可）。
- dmc42-001 条項(b): static {affects: self, mod: {allow: [evolve_civ_any]}}（先例 dm22-019 の自己許可形）。
- dmc45-017 クルー・ブレイカー: static {affects: crossed, mod: {breaks: {count: {zone: bz, owner: you, other: true, filter: {race_has: サムライ, types: [creature]}}}}}（第130弾の breaks {count} = base 1 + 数。converted のジョーカーズ形と同型。other: true で宿主自身を除く）。
- 3件とも多色で「マナゾーンに置く時、タップして置く」は 405.1 の一般則（core の _raw_move で処理済み）。

- プロト T925（civs形、dmc42-017型）・T926（races形＋クルー・ブレイカー、dmc45-017型）・T927（許可形、dmc42-001型）・T928（水ギア＝進化元）・T929（サムライ・ギア＝進化元）・T930（サムライ獣）・T931（card_only 回収呪文＝再構築の検証用）。次の空きは T932。
- tests/test_vocab_pilot304.py: **10 passed** — parse＋許可登録＋未知許可の拒否、プールのゲート（civs形4件: クリーチャー不可／文明不一致／相手のギア不可／水ギア可、races形3件）、重ねてからクロス（束の形＋パワー4000）、crossed 引き継ぎ（+1000→+2000、元のギアは crossed=None）、_rebuild（トップだけ手札へ、下のギアがクロスしたまま残り +1000 が再び及ぶ）、クルー・ブレイカー（他のサムライ獣2体で breaks 3、0体で 1）、レオパルド許可（evolve_civ_any の既定 false と付与、クロス先への evolve_base_any 付与、civ_any の実挙動＋種族は肩代わりしない）。
- tests/test_vocab_pilot304_cards.py: **2 passed** — 対象4件の rejects 行（純粋3件＋dmc42-001 の2ギャップ）・未登録、確立形（partial ＋ types/evolve_from 差し替え ＋ クルー常在型の追加 ＋ dmc42-001 の常在型2つ）の parse。

### 回帰

- 第293弾＋第232弾＋第273弾＋第22弾＋第224弾: **41 passed**（進化元プール・種族肩代わり・クロスギアの近傍）。
- 第303弾（15＋2）＋ test_data_audit ＋ test_rust_schema_sync: **28 passed**。
- test_rules: **40 passed**。
- 既知の事前失敗2件（第274弾 test_floor_zero_colored_pays_civ_count、第31弾 test_janken_win_draws）は本弾の範囲外として未追跡。_mana_choices には触れていない。エンジン変更は turn.py / events.py のみで新規 op・面フィールド・GameState フィールドは無い（Rust は本環境で未ビルド＝ Python フォールバック。test_rust_schema_sync は通過）。

### 収支

- converted **10,237（不変）** / rejects **2,084（不変）**。変更は turn.py・events.py・permissions.yaml・card.schema.json（再生成）・proto.yaml（T925–T931）・テスト2ファイル・docs のみ。

### ラウンド339側の注意

- 対象は純粋3件＋dmc42-001 の計4件。提出形は tests/test_vocab_pilot304_cards.py の確立形（partial ＋ types [cross_gear, evolution] ＋ evolve_from。dmc45-017 はクルー・ブレイカー常在型を追加、dmc42-001 は types 据え置きで常在型2つ）。
- text は reject 行の正式本文へ復元すること（partial の text は「マナゾーンに置く時」行が欠けている。ラウンド325の先例）。
- alias: dmc42-017 は dm17-003、dmc42-001 は promoy4-024（partial の source.aliases）。submit 前に正本判定と real 系照合を行うこと。
- dmc42-001 の条項(a)は「クロスしたクリーチャーに」進化クリーチャーを置く許可で、置く側の進化クリーチャーのフィルタ照合（_evo_match の種族肩代わり）で効く。条項(b)の evolve_civ_any はギア自身に付く。

### ラウンド339 evolution_cross_gear 再変換（第304弾）

- 新規登録 **4件**: dmc42-017 ツナミ・カタストロフィー（civs形）/ dmc45-017 龍刃 ヤマト・スピリット（races形＋クルー・ブレイカー常在型を追加）/ dm17-s05 グランドクロス・カタストロフィー（civs形）/ dmc42-001 レオパルド・グローリーソード（types 据え置き、常在型2つ。第2ギャップ evolution_base_any_race は第232弾で実装済みのため本ラウンドで両ギャップ解消）。
- alias 畳み込み・stale 解消・converted 是正・差し戻しは **0件**。alias は登録カードの source.aliases に記録されただけ（dm17-003 → dmc42-017、promoy4-024 → dmc42-001。どちらも reject 行は元々無かった）。
- 正本判定（identity 実データ照合）: 対象4件はいずれも canon_id が自身＝独立正本。canon_id(dm17-003) = dmc42-017、canon_id(promoy4-024) = dmc42-001 で partial の source.aliases と一致。submit 前照合: 対象 id と alias 計6件すべて converted / real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml に無し。reopen（evolution_cross_gear + evolution_base_any_race）は対象4件だけを除外（他ギャップ併記の dmc66-034 / dm17-004 / dm17-s04 は残留）。
- 登録形は確立形と完全一致（types / evolve_from / abilities / keywords / text を提出形と突き合わせ、連結・merge_split 由来の混入なし）。text は reject 行の正式本文へ復元（partial は「マナゾーンに置く時」行が欠落していた）。
- converted **10,237 → 10,241** / rejects **2,084 → 2,080**、canonical 重なり0・漏れ0。evolution_cross_gear の純粋行は解消（ギャップ名自体は他ギャップ併記の3行に残る）。alias∩rejects の既存 stale 9件は本ラウンド対象外で不変。
- テスト: 登録形バッチ（test_vocab_round339_cards 5件＝disposition＋登録形の実挙動4件〔civs形の進化＋クロスでパワー4000、クルー・ブレイカー breaks 3、レオパルド許可2つ、条項(b) civ_any で自然ギアに水/闇ギアが重なる〕＋ test_vocab_pilot304_cards 登録形書換 2件 ＋ test_data_audit 8件）**15 passed**。第304弾本体（プロト）は別 invocation で **10 passed**（プロト系と登録形 cards テストは同一 invocation に混ぜない作法どおり）。
- 回答は ~/workspace/DMPJ-work/answers/round339.yaml に保存。次の番号: パイロット305 / ラウンド340 / プロト T932。

## 第305弾 soul_shift（ギャップ名ドリフト: 第274弾 soulshift と同一機構の別表記）

ギャップ名 soul_shift の純粋2件（dm26rp2-001 極まる九極 Q.9 / dmex18-005 ケンゲキオージャ ～究極火焔～）。機構は第218弾の面フィールド **soul_shift {floor}**（ソウルシフト∞）＋第274弾のクラシック単体進化への適用で実装済みだが、第274弾の対象はギャップ名 **soulshift**（アンダースコア無し）の4件で、本2件は表記の違う soul_shift で残っていた。同型のドリフト（第283–302弾の各弾と同系）。**新規語彙・エンジン変更なし**。両件とも floor は「０以下にならない」→ {floor: 0}。

- **dm26rp2-001 形（プロト T932）**: partial は骨格のみ（types に evolution が無く、evolve_from・abilities も無い）。提出形は公式全文から構築: types [creature, evolution] ＋ evolve_from {civs: [light], types: [creature]} ＋ soul_shift {floor: 0} ＋ 離脱誘発。離脱誘発「その下にコスト９のクリーチャーがあれば」は第294弾の **event.was_under** を exists ゲート（filter {types: [creature], cost_le: 9, cost_ge: 9}。コスト一致の専用キーは無いため le/ge の併用）で読み、「上から９枚を見て、光のコスト９を１体出してもよい。残りをシャッフルして山札の下に置く」は dmex18-s11 の登録先例（choose {from_top, look: true, count: all} as: pile → may [play_free {ref: pile}] → move {ref: pile, to: deck, position: bottom}）の order を **shuffle** に替えた形（order: shuffle 自体は第289弾で move の集合シャッフルとして実証済み。ref: pile との組み合わせは本弾で実挙動固定）。実挙動で固定: コスト9の下では見て出る（残りは下へ）、コスト5の下では門が閉じて何も起きない。
- **dmex18-005 形（プロト T935）**: partial に evolve_from {name_has: ゴウケンオー} はあるが abilities が無い。勝利誘発「相手の呪文またはバトルゾーンにある相手のクリーチャーの能力によって、このクリーチャーが離れる時、自分はゲームに勝つ」は第290弾で固定した **cause {by: opp, kind: [spell, ability]}** の形（defs の cause 検証コメントが同フレーズをこの形と明記）＋ {op: win}。実挙動で固定: 相手の呪文（T056）・相手のクリーチャーの能力（T937 の CIP 破壊）で離れると勝利、自分の呪文（T938）では勝利しない。
- **ソウルシフト本体の固定**: 文明フィルタ進化（T932: 元コスト9で実効0＝場に出る／元コスト5で4を支払う）、名前フィルタ進化（T935: 元コスト5で7を支払う）、名前不一致では提示されない。**コスト0まで軽減された有色カードの支払い枚数は断言していない**（112.2b を巡る第274弾 vs 第292弾の未解決競合に触れないため。実効0のケースは「場に出ること＋束」だけを見る）。
- プロト T932（dm26rp2-001 形）/ T933（光・コスト9獣。進化元・下・山札からの出し先を兼ねる）/ T934（光・コスト5獣）/ T935（dmex18-005 形）/ T936（ゴウケン名のコスト5獣）/ T937（CIP 破壊獣＝能力除去の駆動）/ T938（自軍破壊呪文＝対照）。次の空きは **T939**。
- tests/test_vocab_pilot305.py（**10 passed**: parse＋形の一致、ソウルシフト実支払い×3、名前不一致の不提示、離脱誘発の発火／門の対照、勝利誘発の呪文／能力／自分の呪文の対照）＋ tests/test_vocab_pilot305_cards.py（**3 passed**: 対象2件の純粋・未登録確認、提出形 parse、dmc64-024/025 の残留確認）。回帰: 第218・274・294・290弾＋test_rust_schema_sync **48 passed / 1 failed**（失敗は既知の既存競合 tests/test_vocab_pilot274.py::test_floor_zero_colored_pays_civ_count のみ。本弾はエンジン無変更で無関係）＋ test_data_audit＋test_rules **48 passed**。
- テスト中の発見: build の deck spec は逆順に置かれる（spec の末尾が山札の一番上。第259–263弾の教訓の再確認）。離脱誘発の検証では、進化元と山札の同名カードを cid で区別しないと done 述語が即成立してしまう。
- **ラウンド340側の注意**: 対象は純粋2件。提出形は cards テストの _form_001 / _form_005 が正本（partial からの差分は上記のみ。text は reject 行の正式本文へ差し替え）。dm26rp2-001 の partial には abilities が一切無いため、登録後に abilities の連結混入が無いか本文と照合すること。dmex18-005 の aliases は dm35-004 / dmc64-013（partial の source.aliases）。提出前に canon を identity で確認し、id・alias を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること。dmc64-024 / dmc64-025（soul_shift + evolve_from_deck_onto_self）は本弾の対象外で残る。converted / rejects は本弾で不変（10,241 / 2,080）。

### ラウンド340 soul_shift 再変換（第305弾）

- 新規登録 **2件**: dm26rp2-001 極まる九極 Q.9（partial は骨格のため公式全文から構築: types [creature, evolution] ＋ evolve_from {civs: [light], types: [creature]} ＋ soul_shift {floor: 0} ＋ 離脱誘発）/ dmex18-005 ケンゲキオージャ ～究極火焔～（partial ＋ soul_shift {floor: 0} ＋ 勝利誘発）。
- alias 畳み込み **1件**: dm35-004 / dmc64-013 → dmex18-005（登録カードの source.aliases に記録。どちらも reject 行は元々無かった）。stale 解消・converted 是正・差し戻しは **0件**。
- 正本判定（identity 実データ照合）: 対象2件はいずれも canon_id が自身＝独立正本。canon_id(dm35-004) = canon_id(dmc64-013) = dmex18-005 で、aliases_for（ケンゲキオージャ）= [dm35-004, dmc64-013] とも一致。submit 前照合: 対象 id と alias 計4件すべて converted / real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml に無し（proto.yaml のヒットは第305弾プロト T932/T935 の text 内参照のみ）。reopen（soul_shift）は対象2件だけを除外（多ギャップの dmc64-024 / dmc64-025 は残留）。
- 登録形は確立形と完全一致（types / evolve_from / soul_shift / abilities / keywords / text を提出形と突き合わせ、連結・merge_split 由来の混入なし。dm26rp2-001 の abilities は離脱誘発1件のみで、骨格 partial からの混入なし）。text は reject 行の正式本文。
- converted **10,241 → 10,243** / rejects **2,080 → 2,078**、canonical 重なり0・漏れ0。soul_shift の純粋行は解消（ギャップ名自体は evolve_from_deck_onto_self 併記の dmc64-024 / dmc64-025 に残る）。
- テスト: 登録形バッチ（test_vocab_round340_cards 5件＝disposition＋登録形の実挙動4件〔ソウルシフト部分軽減で4枚支払い、離脱誘発で上9枚から光のコスト9を出す、勝利誘発が相手の呪文で発火・自分の呪文では不発〕＋ test_vocab_pilot305_cards 登録形書換 2件 ＋ test_data_audit 8件）**15 passed**。第305弾本体（プロト）は別 invocation で **10 passed**。テスト中の注意: build の deck_exact は filler と同じ defn の deck spec を取り除くため、round340 cards の filler は deck spec と重ならない T001 にした（T002 を filler にすると山札が空になり deck_out で敗北する）。
- 回答は ~/workspace/DMPJ-work/answers/round340.yaml に保存。次の番号: パイロット306 / ラウンド341 / プロト T939。

## 第306弾 same_name_sweep（同名一掃）— ギャップ名ドリフト（battle_win ＋ name_of: event.opponent ＋ 複数ゾーン一括移動）

対象は dm17-004 エクスプロード・カタストロフィー 1件のみ（第2ギャップ evolution_cross_gear は第304弾で実装済み）。残る条項は「これをクロスしたクリーチャーがバトルに勝った時、相手の手札を見る。相手は自分自身の手札、マナゾーン、墓地、バトルゾーンから、このバトルで負けたクリーチャーと同じ名前の自分自身のカードをすべて山札の一番下に置く」。結論: **新規語彙・エンジン変更なしのドリフト**。部品はすべて既存で足りる:

- **誘発点**: battle_win 記録は {subject: 勝者, opponent: 敗者, controller} を持つ（combat.py `_battle`）。ギア側の誘発は subject: crossed の照合（events.py `_subject_match`、第223弾〜の cross_gear_effect イディオム）で宿主の勝利に紐付く。
- **敗者の名前**: フィルタ {name: {name_of: event.opponent}}。name_of の `event.<キー>` 解決は基盤 expr-event-ref（selectors.py `_expr_refs` が event.opponent を明示対応）で、第140弾・第282弾は event.subject 版の確立形。
- **手札を見る**: choose {select: {zone: hand, owner: opp, count: all}, as: seen} の束縛だけする look 形（converted dm36-083 ミルルンの先例。一掃は名前で自動なので look 自体に機械的帰結はない）。
- **一掃**: move {select: {zone: [hand, mana, graveyard, bz], owner: opp, filter: {name: {name_of: event.opponent}}, count: all}, to: deck, position: bottom, reason: put}。複数ゾーン選択・count: all・position: bottom はいずれも確立形。敗者自身も（墓地経由で）一緒に山札の下へ行く — 本文が墓地を対象に含むため正しい。相手が置く形だが全数移動で選択の余地はなく、効果側の move で等価。

- 提出形（プロト T939 で固定）: partial ＋ types [cross_gear, evolution] ＋ evolve_from {civs: [darkness, fire]} ＋ 一掃誘発。partial の静的型（crossed への attack_creature allow {tapped: false}）はそのまま。text は partial の形（欠落行なし）。
- プロト T939（dm17-004 型）/ T940（闇ギア＝進化元）/ T941（火獣＝宿主）/ T942（同名獣＝敗者役とコピー）/ T943（別名獣＝対照）/ T944（強獣＝負けケース用）。次の空きは **T945**。
- tests/test_vocab_pilot306.py（**5 passed**: parse＋形の一致、進化元プールのゲート〔クリーチャー不可／文明不一致／相手のギア不可／闇ギア可〕、勝利時の一掃〔4ゾーンから同名4枚＝手札1・マナ1・墓地1・敗者自身が相手の山札の末尾4枚へ、別名は残留、タップされていないクリーチャーへの攻撃はギアの常在型で可能〕、敗北時は一掃なし、プレイヤー攻撃時は一掃なし）＋ tests/test_vocab_pilot306_cards.py（**2 passed**: 対象行の残留・未登録確認、確立形の parse）。回帰: 第304・282・290弾＋test_rules **81 passed**、test_data_audit **8 passed**。エンジン無変更のため既知の事前失敗2件（第274弾・第31弾）は無関係。converted / rejects は本弾で不変（10,243 / 2,078）。

### ラウンド341側の注意

- 対象は dm17-004 の1件。提出形は tests/test_vocab_pilot306_cards.py の確立形が正本（partial ＋ types/evolve_from 差し替え ＋ 一掃誘発の追加）。text は reject 行の正式本文へ差し替えること（partial の text は「 / 」区切り形）。
- dm17-004 に alias は記録されていないが、submit 前に identity の正本判定と id の real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml 照合を行うこと（作法どおり）。
- reopen（evolution_cross_gear + same_name_sweep）は dm17-004 だけを除外するはず（evolution_cross_gear 併記の dm17-s04 は reveal_and_cast_free、dmc66-034 は dynamic_name_reference_filter が残るため外れない）。混ざっていたら submit せず報告すること。
- 登録後は abilities が [静的型, 一掃誘発] の2件ちょうどであることを本文と照合すること（連結・merge_split 混入の確認）。

### ラウンド341（第306弾の再変換）

- 新規登録 **1件**: dm17-004 エクスプロード・カタストロフィー。alias 畳み込み0件・stale クリーンアップ0件・差し戻し0件。
- 正本判定は identity 実測: canon_id(dm17-004) = dm17-004 自身＝独立正本、aliases_for は空。submit 前照合で id は converted / real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml に無し（proto.yaml のヒットは第306弾プロト T939 の text 内参照のみ）。reopen（evolution_cross_gear + same_name_sweep）は dm17-004 だけを除外した。
- 提出形は第306弾の確立形そのもの（partial ＋ types [cross_gear, evolution] ＋ evolve_from {civs: [darkness, fire]} ＋ 一掃誘発、text は reject 行の正式本文へ復元）。登録形は types / evolve_from / abilities / text すべて提出形と完全一致で、abilities は [静的型, 一掃誘発] の2件ちょうど（連結・merge_split 混入なし）。
- 実挙動を登録カード自身で固定: 闇ギア（T940）の上に進化→火獣（T941）にクロス→タップされていない T942 を攻撃して勝利し、相手の同名カード4枚（手札1・マナ1・墓地1＋敗者自身）が山札の末尾4枚へ。敗北時は一掃なし。
- converted **10,243 → 10,244** / rejects **2,078 → 2,077**、canonical 重なり0・漏れ0。same_name_sweep 解消。evolution_cross_gear のギャップ名自体は併記2行（dmc66-034 / dm17-s04）に残留。pilot306 cards を登録形に書換。
- テスト **13 passed**（round341 cards 3＋pilot306 cards 登録形 2＋data_audit 8）＋第306弾本体 **5 passed**（別 invocation。プロト系と登録形 cards は同一 invocation に混ぜない）。

## 第307弾 exlife_shield_left_any（EXライフシールド全般の離脱）— when.subject の exlife_of に "any" を追加

対象は dm26ex2-mc009 不敬合成王 ロマティックダム・アルキング 1件のみ（純粋）。ラウンド328で一旦提出・登録されたが、「自分の『EXライフ』シールドが離れた時、このクリーチャーの下にあるカードを1枚、墓地に置く。それが進化ではないクリーチャーなら、自分の墓地から出す」の subject 形が無く、登録を取り消して差し戻された経緯がある（partial の notes に記録）。詰まりの内訳:

- 第190弾の when.subject {exlife_of: self} は「移動したシールドが特定クリーチャー（self か変数）に紐付いていたか」の照合のみで、「どのクリーチャーのものでもよい」は書けない。
- filter の {exlife: true} は selectors.filter_match が実カードの exlife_of を読むが、紐付けはゾーン移動で外れる（core._raw_move）ため、離脱後の subject 照合では常に false になる（第237弾の filter は場にあるシールドの選択用）。
- 一方で移動記録の LKI スナップショットは移動前の exlife_of を保持しており（events.py のレコード構築）、subject 照合は from: shield の記録でも LKI を読む（「exlife_of」が subject にある時）。不足は「紐付け先を問わない」値だけだった。

追加した語彙（最小）:

- **when.subject の exlife_of に値 "any"**（owner: "any" と同じ流儀）: 移動したカードが移動前にいずれかのクリーチャーに紐付いていたこと（LKI の exlife_of が None でないこと）だけを照合する。実装は events.py `_subject_match` の分岐追加のみ。when.subject はスキーマ無制約・defs 検証も subject 内部を見ないため、スキーマ再生成・defs 変更は不要（test_rust_schema_sync 通過で確認）。subject の owner: you と併記して「自分のEXライフシールド全般」になる。

確立形（残りの条項はすべて partial に完成済み）:

- 誘発: {kind: trigger, when: {event: move, from: shield, subject: {owner: you, exlife_of: any}}, effect: [move {select: {under_of: self, count: 1}, to: graveyard, reason: put, as: buried}, if {exists: {ref: buried, filter: {types: [creature], not_types: [evolution]}}} then [play_free {select: {ref: buried}}]]}。下のカードを墓地に置く形はメテオバーンの先例（move {under_of: self} ＋ as ＋ exists ゲート）。
- 進化GV・Ω = evolve_from の3ゾーン指定（graveyard / mana / bz、第293弾で per-filter zone が効く形）。エクストラEXライフ = キーワード extra_ex_life、ワールド・ブレイカー = キーワード world_breaker。シールドゾーンのディスペクターすべてに G・ストライク = static {affects: {zone: shield, owner: you, filter: {race_has: ディスペクター}}, mod: {grant: [g_strike]}}（いずれも partial のまま）。

- プロト T945（dm26ex2-mc009 型: 進化＋EXライフ＋監視誘発）/ T946（進化元＝進化でない下のカード役）/ T947（進化クリーチャーの下敷き役）。次の空きは **T948**。
- tests/test_vocab_pilot307.py（**7 passed**: parse＋形の一致、他の自軍獣のEXライフシールドが割れる→下のカードが墓地経由で場に戻る、監視者自身のシールドでも発火、普通のシールドでは不発、相手のシールドでは不発〔owner: you〕、下が進化クリーチャーなら墓地に留まる、下にカードが無ければ空振りで安全）＋ tests/test_vocab_pilot307_cards.py（**3 passed**: 対象行の残留・未登録確認、確立形＝partial＋誘発の parse）。回帰: 第291・237・290・294弾＋test_data_audit＋test_rust_schema_sync **51 passed**、test_rules＋第291・237弾 cards **47 passed**。_mana_choices 不触、範囲外不触。converted / rejects は本弾で不変（10,244 / 2,077）。

### ラウンド342側の注意

- 対象は dm26ex2-mc009 の1件。提出形は partial そのものに上記の誘発を abilities へ追加し、source.unsupported から exlife_shield_left_any を外した形（cards テストの TRIGGER が正本）。text は reject 行の正式本文と partial の text を照合すること。
- alias は dm22ex2-8a / dm22ex2-8b / dm22ex2-s15（partial の source.aliases）。submit 前に identity で正本判定し、id・alias を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること。
- reopen（exlife_shield_left_any）は dm26ex2-mc009 だけを除外するはず。登録後は abilities が [G・ストライク常在型, 誘発] の2件ちょうど（parse 時は world_breaker キーワード展開の常在型も加わる）であることを本文と照合すること。

### ラウンド342（第307弾の再変換）

- 新規登録 **1件**: dm26ex2-mc009 不敬合成王 ロマティックダム・アルキング。alias 畳み込み0件（alias 3件は登録カードの source.aliases への記録のみで、いずれも reject 行は元々無し）・stale クリーンアップ0件・差し戻し0件。
- 正本判定は identity 実測: canon_id(dm26ex2-mc009) = dm26ex2-mc009 自身＝独立正本、canon_id は alias 3件（dm22ex2-8a / dm22ex2-8b / dm22ex2-s15）とも dm26ex2-mc009 で aliases_for と一致。submit 前照合で対象 id と alias 計4件すべて converted / real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml に無し（proto.yaml のヒットは第307弾プロト T945 の text 内参照のみ）。reopen（exlife_shield_left_any）は dm26ex2-mc009 だけを除外した。
- 提出形は第307弾の確立形そのもの（partial ＋ 誘発 {event: move, from: shield, subject: {owner: you, exlife_of: any}}、unsupported から exlife_shield_left_any を除去、text は reject 行の正式本文＝partial の text と同一を確認）。登録形は abilities / keywords / evolve_from / text すべて提出形と完全一致で、abilities は [G・ストライク常在型, 誘発] の2件ちょうど（連結・merge_split 混入なし）。ラウンド328で提出後に登録を取り消した条項がこれで解けた。
- 実挙動を登録カード自身で固定: 進化GV・Ωで墓地・マナ・バトルゾーンの T946 を1体ずつ重ねて出し、相手の T850 で自身のEXライフシールドを割ると誘発が発火し、下のカード1枚が墓地経由で場に戻る（残りの下は2枚）。EXライフでない普通のシールドでは発火しない。
- converted **10,244 → 10,245** / rejects **2,077 → 2,076**、canonical 重なり0・漏れ0。exlife_shield_left_any 解消（alias∩rejects の既存 stale 9件は本ラウンド対象外で残留）。pilot307 cards を登録形に書換。
- テスト **13 passed**（round342 cards 3＋pilot307 cards 登録形 2＋data_audit 8）＋第307弾本体 **7 passed**（別 invocation。プロト系と登録形 cards は同一 invocation に混ぜない）。
- 回答は ~/workspace/DMPJ-work/answers/round342.yaml に保存。次の番号: パイロット308 / ラウンド343 / プロト T948。

## 第308弾 evolve_from_deck_onto_self（山札から自分の上に置く）— ギャップ名ドリフト（第173弾 deck_evolution の全山札検索形）

センサス（rejects 2,076件を再集計）: 候補を評価し、相方 soul_shift が第305弾でドリフト確認済みの2件（dmc64-024 ゴウケンオー～剣々轟々～ / dmc64-025 ケンゴウグレンオー～天地鳴動～、いずれも gaps = [soul_shift, evolve_from_deck_onto_self]、partial は空）を選定。win_replacement_grandchild / declare_speech は現実依存のジョーク条項で対象外（第307弾で確認）。trigger_when_opponent_plays_free は第285弾で各行に別ブロッカーありと評価済み。per_evolution_base_cost_reduction は evo_base_reduce の一律形のみが詰まりだが、対象が単独行で支払い近傍のため本弾では見送り。

残りの条項はすべて既存語彙で書けた（新規語彙・エンジン変更なし）:

- 「自分の山札を見る。その中から名前に《X》とあるクリーチャーを1体選び、このクリーチャーの上に置いてもよい。その後、山札をシャッフルする」= {op: may, body: [choose {zone: deck, owner: you, look: true, filter: {name_has: X, types: [creature]}, count: 1} as p, move {select: {ref: p, count: all}, to: bz, reason: put, stack_evo: true, evo_source: {ref: self}}]} ＋ {op: shuffle}。第173弾 deck_evolution の形で、同製品 DMC64 の登録済み dmc64-036 / dmc64-042 が全山札検索形の先例（そちらは本文が「カードを1枚」のため types フィルタなし。本2件は「クリーチャーを1体」なので types: [creature] を付ける）。重ね先の適格性は解決時に照合される（ops の stack_evo 分岐）。なお第173弾の記録どおり、converted の dmc64-020 / dmc64-031 は同じ「上に置く」を put_under で書いた既存の誤変換（本弾の対象外、直さず記録のみ）。
- 「このクリーチャーで攻撃するかわりに、タップして次の能力を使ってもよい」= {kind: activate, cost: {tap: self}}（多数の先例。起動は attack 決定で activate:<defn>:* として提示される）。
- 全体破壊は destroy {count: all}: 024 は filter {types: [creature], keyword: blocker}、025 は filter {types: [creature], power_le: 2000}。効果の順序は本文どおり破壊が先。
- 進化元は evolve_from {name_has: ...}（dmc64-036 の先例。024 = ケンゴウグレンオー、025 = ワンケングレンオー）。重ねられる側も名前の連鎖が整合する（024 の上に乗るケンゲキオージャ dmex18-005 の evolve_from は name_has ゴウケンオー で 024 の名前に一致、025 の上に乗るゴウケンオー勢の evolve_from は name_has ケンゴウグレンオー で 025 の名前に一致）。
- ソウルシフトは soul_shift {floor: 1}: 024 は裸のキーワードで、標準定義は「1より少なくならない」（同セット 025 のリマインダが明記）。025 はリマインダ明記で floor: 1（第274弾・ラウンド309の先例どおり。第305弾の2件は「0以下にならない」明記だったため floor: 0 であり、本2件とは異なる）。

プロト T948（024形）・T949（025形）・T950（ケンゴウグレンオー進化元）・T951（ワンケングレンオー進化元）・T952（ケンゲキオージャ役）・T953（ゴウケンオー進化役）・T954（ブロッカー役）・T955（パワー2000役）。次の空きは T956。

- tests/test_vocab_pilot308.py: **8 passed** — parse（soul_shift floor 1・キーワード・activate 形）、ソウルシフト実支払い（024形: 17−5＝12枚、025形: 10−5＝5枚）、名前不一致では提示されない、起動能力024形（ブロッカーだけ破壊＋山札から重ね＋タップ確認）/ 辞退（破壊のみ・重ねなし）/ 山札に該当なし（破壊のみ・空振り安全）、起動能力025形（パワー2000以下だけ破壊＋重ね）。
- tests/test_vocab_pilot308_cards.py: **2 passed** — 対象2件の rejects 行（2ギャップ・partial 空）・未登録・ファミリーがこの2件だけ、確立形 FORM_024 / FORM_025 の parse（destroy マクロは parse 時に move（reason: destroy）へ展開される点も固定）。
- 回帰: data_audit＋第305・173・249弾＋test_rules＋test_rust_schema_sync **76 passed**。既知の事前失敗2件（第274弾 test_floor_zero_colored_pays_civ_count、第31弾 test_janken_win_draws）は本弾の範囲外として未追跡。_mana_choices には触れていない。エンジン変更なし。

収支: converted **10,245（不変）** / rejects **2,076（不変）**。変更は proto.yaml（T948–T955 純追加）・テスト2件・docs のみ。

### ラウンド343側の注意

- 対象は dmc64-024 / dmc64-025 の2件。提出形は tests/test_vocab_pilot308_cards.py の FORM_024 / FORM_025 が正本（partial は空なので公式データから構築済み。text は reject 行の正式本文と同一であることを cards テストで固定済み）。
- reopen は soul_shift + evolve_from_deck_onto_self で、この2件だけが外れるはず。
- submit 前に identity で正本判定を行い、id・alias を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること（dmc64-013 は dmex18-005 の alias であって本2件とは無関係）。
- 登録後は abilities が [起動能力] の1件ちょうど（024 は keywords [triple_breaker]、025 は [double_breaker]）であることを本文と照合すること。
### ラウンド343（第308弾の再変換）

- 新規登録 **2件**: dmc64-024 ゴウケンオー～剣々轟々～ / dmc64-025 ケンゴウグレンオー～天地鳴動～。alias 畳み込み0件（alias は登録カードの source.aliases への記録のみで、いずれも reject 行は元々無し）・stale クリーンアップ0件・差し戻し0件。
- 正本判定は identity 実測: canon_id は対象2件とも自身＝独立正本。alias は dmc64-024 ← dm34-015、dmc64-025 ← dm33-016（いずれも canon_id が対象に一致し aliases_for とも一致）。submit 前照合で対象 id と alias 計4件すべて converted / real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml に無し（proto.yaml のヒットは第308弾プロト T948 / T949 の text 内参照のみ）。対象行は reason を持たないため reopen（soul_shift + evolve_from_deck_onto_self）は0件を外し（第323弾 dmr21-002 の先例どおり）、submit が登録時に reject 行を直接外した。
- 提出形は第308弾の確立形 FORM_024 / FORM_025 そのもの（partial は空のため公式データから構築、text は reject 行の正式本文と同一を提出前に照合）。登録形は name / types / civs / cost / power / mana / races / text / evolve_from / soul_shift / keywords / abilities すべて提出形と完全一致で、abilities は [起動能力] の1件ちょうど（連結・merge_split 混入なし）。ソウルシフトは両件とも soul_shift {floor: 1}（024 は裸のキーワード＝標準定義、025 はリマインダ明記。第305弾の floor: 0 の2件とは本文が異なる）。
- 実挙動を登録カード自身で固定: 024 はソウルシフトで 17−5＝12 枚を支払って T950 の上に進化（支払いマナ12枚タップを確認）、起動で相手のブロッカー T954 だけを破壊し山札の T952 を上に重ねる（小型 T955 は残留、起動コストでタップ）。025 の起動はパワー2000以下の T955 だけを破壊し山札の T953 を上に重ねる（パワー3000の T954 は残留）。
- converted **10,245 → 10,247** / rejects **2,076 → 2,074**、canonical 重なり0・漏れ0。evolve_from_deck_onto_self 解消、soul_shift も解消（残留は本2件だけだった）。pilot308 cards を登録形に書換。
- テスト **14 passed**（round343 cards 4＋pilot308 cards 登録形 2＋data_audit 8）＋第308弾本体 **8 passed**（別 invocation。プロト系と登録形 cards は同一 invocation に混ぜない）。
- 回答は ~/workspace/DMPJ-work/answers/round343.yaml に保存。次の番号: パイロット309 / ラウンド344 / プロト T956。

## 第309弾 rinne_infinity（輪廻暴冥）— ギャップ名ドリフト

センサス（rejects 2,074件を再集計）: 候補を順に評価した。reveal_and_cast_free（dm17-s04）は evolution_cross_gear が第304弾で解けた最後の併記行だが、残る条項は第267弾の輪廻虹災形（choose look pile → 文明ごと if/may/play_free → 残りを下へ）がほぼ同型で、本弾の対象はその前に立つ純粋1件の **rinne_infinity（dmrp21-tr2 天地命動 バラギアラ / 輪廻暴冥）** とした。rinne_infinity は第267弾で「ギャップ名が違うため対象外。次回以降の対象」と明記されていた行で、共通文言は第267弾の3件と同一（「輪廻∞：このカードの呪文側を、バトルゾーンに置いたまま唱えてもよい。そうした時、自分の《天地命動 バラギアラ》１体につき、自分の山札の上から１枚をマナゾーンに置く」）。機構は面項目 `rinne: true`＋ cast `via: rinne` 誘発イディオムで実装済みのため、本弾は **ドリフト（新規語彙・エンジン変更なし）**。

tr2 の全条項は第267弾の確立形で書ける:

- クリーチャー面（自然コスト9・パワー17000・マスター・ハザード/グランセクト）: rinne: true ＋ CIP {event: move, to: bz, subject: self, reason: summon} → untap {zone: mana, owner: you, count: all} ＋ {event: cast, via: rinne, subject: self} → repeat {times: {count: {zone: bz, owner: you, filter: {name_has: 天地命動 バラギアラ}}}} [move {select: {zone: deck, owner: you, from_top: 1}, to: mana, reason: put}] ＋ triple_breaker（登録済み dm26rp3-s011 と同型）。
- 呪文面（輪廻暴冥、闇コスト6、S・トリガー）: choose {zone: bz, owner: opp, filter: {types: [creature]}, count: 1} as x → modify {ref: x, power: -4000, duration: end_of_turn} ＋ move {select: {zone: graveyard, owner: you, filter: {types: [creature], cost_le: 5}, count: 1}, to: bz, reason: put}（第267弾の設計どおり「-4000 は modify、墓地からは move」。墓地→bz の reason: put は converted 先例どおり）。

プロト T956（tr2 型。クリーチャー面は T742 と同型、呪文面が暴冥形）。次の空きは **T957**。

- tests/test_vocab_pilot309.py: **5 passed** — parse（rinne・誘発2件・暴冥 spell の [choose, modify, move] 形と cost_le 5 フィルタ）、rinne 詠唱（-4000 で相手 T004 が破壊され相手墓地へ、墓地の T001 が出て コスト9の T741 は残留、カードは場に面0のまま残り墓地へ行かない、支払い6枚タップ＋チャージ1枚、casts カウンタ1）、バラギアラ2体でチャージ2枚、手札から普通に唱えた場合はチャージなし・唱えた後は墓地へ、CIP でマナ全アンタップ。
- tests/test_vocab_pilot309_cards.py: **2 passed** — 対象行の残留（gaps [rinne_infinity] 純粋1件・partial の faces がプレースホルダであること）・未登録（id・alias とも converted に無い）、確立形 FORM の parse（faces の rinne / キーワード / spell 形）。
- 回帰: 第267弾本体 **8 passed** ＋ test_data_audit **8 passed**（309 cards と同一 invocation で計18 passed）、第267弾 cards（登録済み rinne 3件）**6 passed**。既知の事前失敗2件（第274弾・第31弾）は範囲外として未追跡。_mana_choices には触れていない。エンジン変更なし。

収支: converted **10,247（不変）** / rejects **2,074（不変）**。変更は proto.yaml（T956 純追加）・テスト2件・docs のみ。

### ラウンド344側の注意

- 対象は dmrp21-tr2 の1件。提出形は tests/test_vocab_pilot309_cards.py の FORM が正本。
- **partial の faces はプレースホルダ（名前 x / y・火コスト1）で実データではない**。提出形は公式データ（data/cards/raw/by_product/rp21.jsonl）から構築すること。reject 行の text はクリーチャー面分しか無いので、両面テキストは公式から復元する（dm26rp3-s011 の登録形が体裁の先例: 面ごとに text、トップレベルは「 ／ 」連結）。
- alias は dmrp08-mh03（partial の source.aliases、reject 行は無い）。submit 前に identity で正本判定し、id・alias を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること。mh03 の公式テキストはチャージ条件が「バトルゾーンにある自分の《天地命動 バラギアラ》１体につき」と明記する版だが、数え方は bz カウント {name_has} で同一。
- 登録後は faces[0].abilities が [CIP, チャージ誘発] の2件ちょうど、faces[1].spell が [choose, modify, move] の3件ちょうどであることを本文と照合すること。

### ラウンド344（第309弾の再変換）

- 新規登録 **1件**: dmrp21-tr2 天地命動 バラギアラ / 輪廻暴冥。alias 畳み込み0件（alias dmrp08-mh03 は登録カードの source.aliases への記録のみ、reject 行は元々無し）・stale クリーンアップ0件・差し戻し0件。
- 正本判定は identity 実測: canon_id(dmrp21-tr2) は自身＝独立正本、canon_id(dmrp08-mh03) も dmrp21-tr2。submit 前照合で対象 id と alias 計2件すべて converted / real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml に無し（proto.yaml のヒットは第309弾プロト T956 の text 内参照のみ）。reopen（rinne_infinity）は対象1件だけを外した。
- 提出形は第309弾の確立形 FORM そのもの。partial の faces はプレースホルダ（名前 x / y・火コスト1）だったため、faces と両面 text は公式データ（by_product/rp21）から構築し、トップレベル text は dm26rp3-s011 の体裁（面ごとに text、「 ／ 」連結）。登録形は name / mana / faces / text すべて提出形と完全一致で、faces[0].abilities は [CIP, チャージ誘発] の2件ちょうど、faces[1].spell は [choose, modify, move] の3件ちょうど（連結・merge_split 混入なし）。
- 実挙動を登録カード自身で固定: 輪廻∞で暴冥を唱えると -4000 で相手 T004 が破壊され、墓地のコスト5以下の T001 が出て（コスト9の T741 は残留）、カードは場に面0のまま残り、支払い6枚タップ＋チャージ1枚（マナ7枚）。召喚時は CIP で支払った9枚がすべてアンタップする。
- converted **10,247 → 10,248** / rejects **2,074 → 2,073**、canonical 重なり0・漏れ0。rinne_infinity 解消。pilot309 cards を登録形に書換。
- テスト **13 passed**（round344 cards 3＋pilot309 cards 登録形 2＋data_audit 8）。第309弾本体はプロト系のため別 invocation（パイロット時に 5 passed 済み）。
- 回答は ~/workspace/DMPJ-work/answers/round344.yaml に保存。次の番号: パイロット310 / ラウンド345 / プロト T957。

## 第310弾 opt_reduce_then_entry_destroy — opt_reduce.then の第3形 entry_destroy

センサス（rejects 2,073件を再集計）: 候補を順に評価した。reveal_and_cast_free（dm17-s04）は第267弾の輪廻虹災形とほぼ同型で別途ドリフト候補として残る。attack_target_choice（dm25ex2-004）は攻撃宣言の対象選択を相手側へ移すエンジン手術で重い。per_evolution_base_cost_reduction（dm26ex2-pr003）は支払いフローの軽減計算に触れるため _mana_choices 対立（第274弾 vs 第292弾）回避の観点から見送り。static_if_own_current_power（dm28-s09）は常在条件の印刷特性評価そのものが詰まりで重い。revealed_pile_breaks_and_placement（dm24ex3-tf02）は「上か下のどちらかへの配置選択」が別途必要。本弾の対象は純粋1件の **opt_reduce_then_entry_destroy（dmrp12-008 帝神龍装 ティーゾリス）**。第264弾で離脱型 trigger_double と W・ブレイカーは解けて partial に保存済みで、残余は「コストを2少なくしてもよい。そうしたら、このターン、このクリーチャーがバトルゾーンに出た時、自分のクリーチャーを1体破壊する」のみ。

詰まりは opt_reduce.then がターン終了時の2形（destroy / deck_bottom_draw）しか無く、「軽減した」ことを条件に出た時の処理を書けないこと。追加した語彙は最小の1点:

- **opt_reduce.then の第3形 `entry_destroy`**（defs 検証・schema.py の enum・スキーマ再生成。差分は enum への追加のみ）。h_play の then 処理で、ターン終了時ではなく {event: move, to: bz, subject: self} の遅延誘発を積む。遅延誘発の登録（子タスク）は後に積んだタスクが先に動くため召喚の移動イベントより先に処理され、出た時の照合に間に合う（実挙動で固定）。持続は delayed_trigger の既定 end_of_turn、once も既定どおり（同一ターン内の再入場は新しいオブジェクトとして扱い再誘発しない）。効果は「自分のクリーチャーを1体破壊する」= {op: move, select: {zone: bz, owner: you, filter: {types: [creature]}, count: 1}, to: graveyard, reason: destroy}。出た本人も対象に含む（本文に除外指定なし）。軽減を選ばなければ（t["reduced"] が立たなければ）登録自体されない。
- tools/convert_cards.py の変換指示に entry_destroy の形を追記。
- エンジン変更は turn.py の then 分岐のみ。新規 op・面フィールド・GameState フィールドは無い（Rust は本環境で未ビルド＝Python フォールバック。test_rust_schema_sync は通過）。

プロト T957（ティーゾリス型: 闇コスト6・パワー7000・W・ブレイカー・opt_reduce {amount: 2, then: entry_destroy}）。次の空きは **T958**。

- tests/test_vocab_pilot310.py: **4 passed** — parse＋then の未知値が DefError で弾かれること、軽減して出して他の自軍獣（T001）を破壊（支払い4枚タップ確認・ターン終了時に再破壊しないこと）、軽減して本人だけなら本人を破壊（候補1件は自動決定）、軽減しなければ破壊なし（全額6枚支払い）。
- tests/test_vocab_pilot310_cards.py: **2 passed** — 対象行の残留（gaps [opt_reduce_then_entry_destroy] 純粋1件・converted 10,248 / rejects 2,073・未登録・重なり0）、確立形 FORM（partial ＋ opt_reduce 常在型）の parse。
- 回帰: test_data_audit＋test_rust_schema_sync（310 cards と同一 invocation で計13 passed）、第6弾＋第189弾＋第13弾＋test_cost **25 passed**、第264弾＋第6弾 cards＋第189弾 cards **20 passed**。既知の事前失敗2件（第274弾・第31弾）は範囲外として未追跡。_mana_choices には触れていない。

収支: converted **10,248（不変）** / rejects **2,073（不変）**。変更は defs.py・schema.py・card.schema.json（再生成）・turn.py・convert_cards.py・proto.yaml（T957 純追加）・テスト2件・docs。

### ラウンド345側の注意

- 対象は dmrp12-008 の1件。提出形は tests/test_vocab_pilot310_cards.py の FORM が正本（partial ＋ {kind: static, affects: self, zone: hand, mod: {opt_reduce: {amount: 2, then: entry_destroy}}}、unsupported から opt_reduce_then_entry_destroy を外す）。text は reject 行の正式本文と同一であることを提出前に照合済み（cards テストで固定）。
- partial に aliases の記録は無いが、submit 前に identity で正本判定し、id・alias を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること。
- 登録後は abilities が [trigger_double 常在型, opt_reduce 常在型] の2件ちょうどであることを本文と照合すること（連結・merge_split 混入の確認）。
- reopen は opt_reduce_then_entry_destroy で対象1件だけが外れるはず。違う行が混ざったら submit せず報告すること。

### ラウンド345（opt_reduce_then_entry_destroy 再変換）

- 新規登録 **1件**: dmrp12-008 帝神龍装 ティーゾリス。alias 畳み込み0件・stale クリーンアップ0件・差し戻し0件。
- 正本判定は identity 実測: canon_id(dmrp12-008) = dmrp12-008 自身＝独立正本、aliases_for は空（alias なし）。submit 前照合: 対象 id は converted / real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml に無し（proto.yaml のヒットは第310弾プロト T957 の text 内参照のみ）。reopen（opt_reduce_then_entry_destroy）は対象1件だけを除外。
- 登録形は確立形 FORM と完全一致（partial〔第264弾で trigger_double と W・ブレイカーを解決済み〕＋ opt_reduce 常在型、unsupported 除去、text は reject 行の正式本文）。abilities は [trigger_double 常在型, opt_reduce 常在型] の2件ちょうどで連結・merge_split 混入なし。
- converted **10,248 → 10,249** / rejects **2,073 → 2,072**、canonical 重なり0・漏れ0、opt_reduce_then_entry_destroy 解消。
- テスト **13 passed**（round345 cards 3件＝disposition＋登録形の実挙動2件〔軽減→他獣破壊＋支払い4枚／通常召喚→破壊なし＋全額6枚〕、pilot310 cards 登録形書換 2件、data_audit 8件）＋第310弾本体 **4 passed**（別 invocation）。
- 回答は answers/round345.yaml に保存。次の番号: パイロット311 / ラウンド346 / プロト T958。

## 第311弾 reveal_and_cast_free（表向きにして好きなだけ唱える）— ドリフト

センサス（rejects 2,072件を再集計）: reveal_and_cast_free は dm17-s04 ネオウェーブ・カタストロフィー 1件のみ（gaps = [evolution_cross_gear, reveal_and_cast_free]）。evolution_cross_gear は第304弾で実装済みで、本件が同ギャップの最後の併記行（残る dmc66-034 は相方 dynamic_name_reference_filter が評価済みで重い）。第310弾で「第267弾の輪廻虹災形とほぼ同型のドリフト候補」と評価されていた。dm24ex3-tf02（revealed_pile_breaks_and_placement）は「無色カード1枚につきブレイク付与」の数え上げと「上か下どちらかへの配置選択」が別機構で、本弾では選ばなかった。

結論: **ドリフト**（新規語彙・エンジン変更なし）。partial に完成済みのブロッカー常在型 {affects: crossed, mod: {grant: [blocker]}} と、第304弾の civs 形（types [cross_gear, evolution] ＋ evolve_from {civs: [light, water]}）に、攻撃誘発を既存部品で繋ぐ:

- 誘発点 = {kind: trigger, when: {event: attack, subject: crossed}}（cross_gear_effect イディオムのギア側攻撃誘発）
- 表向き = {op: choose, select: {zone: deck, owner: you, from_top: 3, look: true, count: all}, reveal: true, as: pile}（第267弾 輪廻虹災 T740 形）
- 「S・トリガー付き呪文を好きなだけ選び」 = {op: choose, select: {ref: pile, filter: {types: [spell], keyword: s_trigger}, count: all, up_to: true}, as: casts}。count: all ＋ up_to: true は selectors の any_n 形（0〜全部の任意選択）。keyword フィルタは定義の keywords を見るため、S・トリガー呪文だけが候補になる（束の中の通常呪文・クリーチャーは提示されないことを実挙動で固定）
- 「コストを支払わずに唱えてもよい」 = {op: repeat, over: casts, as: it, body: [{op: play_free, select: {ref: it}}]}（第233弾の repeat over。選んだ順に1枚ずつ唱える）
- 「唱えなかったカードを一番下に好きな順番で戻す」 = {op: move, select: {ref: pile, zone: deck, count: all}, to: deck, position: bottom, order: choose, reason: put}（T740 形。唱えたカードは山札を離れているので、zone: deck の照合で残りだけが戻る）

- プロト T958（dm17-s04 型）・T959（光ギア＝進化元）・T960（S・トリガー光呪文）・T961（S・トリガー水呪文。両方とも効果はマナ全アンタップ＝決定なし・山札に触れない形にして束の検証を純化）・T962（S・トリガーを持たない対照呪文）。次の空きは **T963**。
- tests/test_vocab_pilot311.py: **8 passed** — parse（types / evolve_from / 誘発の when）、進化元プール（クリーチャー不可・文明不一致ギア不可・光ギア可）、両方唱える（墓地に2枚・残り1枚が山札の一番下・reveal 記録3件・効果でマナ全アンタップ・宿主に blocker 付与）、1枚だけ唱えて残りを指定順（order の最後が一番下）、0枚（3枚とも指定順で下へ）、束に ST 呪文なし（choose_cards 自体が出ない）、クロスしていない攻撃では不発、クロス先でないクリーチャーの攻撃では不発。
- tests/test_vocab_pilot311_cards.py: **2 passed** — 対象行の残留（gaps 2件・converted 10,249 / rejects 2,072・未登録・重なり0、evolution_cross_gear は併記2行のみ）、確立形 FORM の parse。
- 回帰: 第304弾＋第267弾＋第306弾＋第233弾 **27 passed**、test_data_audit＋test_rust_schema_sync **11 passed**。既知の事前失敗2件（第274弾・第31弾）は範囲外。_mana_choices には触れていない。エンジン変更なし（Rust 手順不要）。

テスト中の発見: (1) クロスはギアのコストをもう一度支払うため、進化（5マナ）＋クロス（5マナ）には10マナ必要で、1回目の支払いコンボの選び方で同ターンのクロス可否が決まる（ドライバは1回目を水寄りに払い光を残す）。(2) 呪文効果がドローだと、唱えた呪文が束の残りを引いてしまい「唱えなかったカード」の検証が濁る（実挙動としては正しい: 引かれたカードは山札に残っていないので下へは戻らない）。

収支: converted **10,249（不変）** / rejects **2,072（不変）**。変更は proto.yaml（T958–T962 純追加）・テスト2件・docs のみ。

### ラウンド346側の注意

- 対象は dm17-s04 の1件。提出形は tests/test_vocab_pilot311_cards.py の FORM が正本（partial ＋ types [cross_gear, evolution] ＋ evolve_from {civs: [light, water]} ＋ 攻撃誘発、unsupported から両ギャップを外す）。text は reject 行の正式本文（\n 区切り）。
- partial に aliases の記録は無いが、submit 前に identity で正本判定し、id・alias を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること。
- 登録後は abilities が [ブロッカー常在型, 攻撃誘発] の2件ちょうどであることを本文と照合すること（連結・merge_split 混入の確認）。
- reopen は evolution_cross_gear + reveal_and_cast_free で対象1件だけが外れるはず（dmc66-034 は相方 dynamic_name_reference_filter が残るため外れない）。違う行が混ざったら submit せず報告すること。
- 本件の登録で evolution_cross_gear の併記は dmc66-034 の1行だけが残る。

### ラウンド346（reveal_and_cast_free 再変換）

- 新規登録 **1件**: dm17-s04 ネオウェーブ・カタストロフィー。alias 畳み込み0件・stale クリーンアップ0件・差し戻し0件。
- 正本判定は identity 実測: canon_id(dm17-s04) = dm17-s04 自身＝独立正本、aliases_for は空（alias なし）。submit 前照合: 対象 id は converted / real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml に無し（proto.yaml のヒットは第311弾プロト T958 の text 内参照のみ）。reopen（evolution_cross_gear + reveal_and_cast_free）は対象1件だけを除外（dmc66-034 は残留）。
- 登録形は確立形 FORM と完全一致（partial のブロッカー常在型 ＋ types [cross_gear, evolution] ＋ evolve_from {civs: [light, water]} ＋ 攻撃誘発、unsupported 除去、text は reject 行の正式本文）。abilities は [ブロッカー常在型, 攻撃誘発] の2件ちょうどで連結・merge_split 混入なし。
- converted **10,249 → 10,250** / rejects **2,072 → 2,071**、canonical 重なり0・漏れ0、reveal_and_cast_free 解消。evolution_cross_gear の併記は dmc66-034 の1行だけが残る。
- テスト **14 passed**（round346 cards 4件＝disposition＋登録形の実挙動3件〔両方唱える／1枚＋順序指定／未クロスで不発〕、pilot311 cards 登録形書換 2件、data_audit 8件）＋第311弾本体 **8 passed**（別 invocation）。
- 回答は answers/round346.yaml に保存。次の番号: パイロット312 / ラウンド347 / プロト T963。

## 第312弾 ex_life_shield_leave_trigger（「EXライフ」シールドが離れた時にも選ぶモーダル）— ドリフト

センサス（rejects 2,071件を再集計）: 純粋ファミリーの大半は範囲外（gr_summon 147、aura 108、hyperdimensional_zone 105、dragheart 45、psychic_filter 45、hyperdimensional_summon 41、out_of_game 23、duelist_link 20、outside_game 12、pandora_shift 4）か評価済み DEEP/重い。在範の単独・小グループはほぼ評価済みのため、行の `gaps` が空で `partial.source.unsupported` にだけギャップ名が残る NEO 期の行（25件）を精査し、本件を選定した。dm24ex3-tf02（revealed_pile_breaks_and_placement）は第311弾の評価どおり別機構、dm26rp2-s011（deck_faceup_power）は山札内表向き状態が保持されない点が依然ブロッカー。

対象は dm26ex4-003 / dm26ex4-sec004 切札接続 ドールバロム 2件（同一カードの2刷）。partial は NEO進化・EXライフ・T・ブレイカーと CIP 誘発＋モーダル3択まで完成済みで、欠けているのは「このクリーチャーが出た時**または**このクリーチャーの『EXライフ』シールドが離れた時」の後半だけだった。

結論: **ドリフト**（新規語彙・エンジン変更なし）。離脱誘発は第190弾で実装され第291弾で登録先例のある {event: move, from: shield, subject: {exlife_of: self}}。確立形は partial の CIP 誘発に、その effect（モーダル）を共有する離脱誘発を1件追加するだけ:

- mode 0「相手は自身の手札を表向きにし、その中から闇ではないカードをすべて捨てる」 = {op: discard, select: {chooser: opp, count: all, filter: {not_civs: [darkness]}, owner: opp, zone: hand}}（partial の形のまま。全対象が捨てられるため公開情報は墓地で確定し、闇カードは伏せたまま残ることを実挙動で固定）
- mode 1「闇ではないクリーチャーをすべて破壊する」 = {op: destroy, select: {count: all, filter: {not_civs: [darkness], types: [creature]}, owner: any, zone: bz}}（自軍の闇でない獣も巻き込む。本文どおり）
- mode 2「相手のマナゾーンにある闇ではないカードはすべて、次の自分のターンのはじめまでアンタップしない」 = {op: modify, select: {count: all, filter: {not_civs: [darkness]}, owner: opp, zone: mana}, mod: {deny: [untap_at_start]}, duration: until_next_own_turn_start}。duration は core._duration が until_turn_start:{you} に解決する既存意味論: 自分のターンに発火すれば相手の次のターン開始のアンタップを止める。相手のターンに発火した場合は相手の次のアンタップが自分の次のターン開始より後になるため、文面どおり制限はそこで切れる（実挙動の固定は CIP 経路で行った）

- プロト T963（dm26ex4-003 型: EXライフ＋CIPモーダル＋離脱モーダル。進化側は partial の parse で担保）。次の空きは **T964**。
- tests/test_vocab_pilot312.py: **6 passed** — parse（2誘発の when・効果の同一性・モーダル3択のマクロ展開と modify の mod/duration）、CIP mode 1（自他とも闇でない獣が全滅・闇は残る）、CIP mode 2（相手の自然マナだけ次のターン開始で起きない・闇マナは起きる）、ブレイク経路 mode 0（相手の自然手札だけ捨てられ闇は残る）、普通のシールドのブレイクでは不発、破壊置換経路 mode 1（置換でシールドが墓地へ・本体は残り・相手の自然獣が破壊）。
- tests/test_vocab_pilot312_cards.py: **2 passed** — 対象2行の残留（gaps 空・unsupported は当該ギャップのみ・未登録・converted 10,250 / rejects 2,071・重なり0、2刷の partial は id/name 以外同一）、確立形 FORM（partial ＋ 離脱誘発追加）の parse。
- 回帰: 第291弾＋第190弾＋第307弾＋test_data_audit＋test_rust_schema_sync＋test_rules **75 passed**、第291・307弾 cards **7 passed**。既知の事前失敗2件（第274弾・第31弾）は範囲外。_mana_choices には触れていない。エンジン変更なし（Rust 手順不要）。

テスト中の発見: T056（相手の獣を1体破壊する呪文）は、相手のクリーチャーが1体だけの局面では対象選択の決定自体が出ず自動で定まる（ask の一意自動決定）。ドライバで対象選択を待つと永久に来ないため、局面側で候補を1体に絞るか、決定が出ない前提で書くこと。

収支: converted **10,250（不変）** / rejects **2,071（不変）**。変更は proto.yaml（T963 純追加）・テスト2件・docs のみ。

### ラウンド347側の注意

- 対象は dm26ex4-003 / dm26ex4-sec004 の2件。提出形は tests/test_vocab_pilot312_cards.py の確立形（partial ＋ 離脱誘発の追加、unsupported 除去）。text は reject 行の正式本文と同一（partial の text は正式本文そのもの）。
- 対象行は `gaps` が空のため reopen では外れない（第323弾・第343弾の先例どおり直接 submit で登録する）。
- 2件は同一カードの2刷: submit 前に identity で正本判定し（sec004 は secret 刷りで canon が dm26ex4-003 の見込み）、id・alias を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること。
- 登録後は abilities が [CIP誘発, 離脱誘発] の2件ちょうどで、両誘発の effect が同一モーダルであることを本文と照合すること（連結・merge_split 混入の確認）。

### ラウンド347（ex_life_shield_leave_trigger 再変換）

- 新規登録 **1件**: dm26ex4-003 切札接続 ドールバロム。alias 畳み込み **1件**: dm26ex4-sec004 → dm26ex4-003。stale クリーンアップ **1件**（sec004 の reject 行、後述）。差し戻し0件。
- 正本判定は identity 実測: canon_id(dm26ex4-sec004) = dm26ex4-003、aliases_for（切札接続 ドールバロム, dm26ex4-003） = [dm26ex4-sec004]。submit 前照合: 対象 id と alias 計2件すべて converted / real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml に無し（proto.yaml のヒットは第312弾プロト T963 の text 内参照のみ）。対象行は gaps が空のため reopen では外れず直接 submit（第323・343弾の先例）。
- 登録形は確立形と完全一致（partial の CIP 誘発＋モーダル3択に第2誘発 {event: move, from: shield, subject: {exlife_of: self}} を追加し unsupported 除去、source.aliases に sec004 を記録、text は reject 行の正式本文）。abilities は [CIP誘発, 離脱誘発] の2件ちょうどで両 effect は同一モーダル、連結・merge_split 混入なし。
- **sec004 の reject 行の扱い**: submit は 003 の行だけを外し、sec004 の行は残った（alias 宣言だけでは行が外れないケース）。登録により sec004 は 003 の alias として完全にカバーされるため、第328・330・331弾の stale クリーンアップと同型に行だけを除去した。alias 側の残留は無し。
- converted **10,250 → 10,251** / rejects **2,071 → 2,069**、canonical 重なり0・漏れ0、ex_life_shield_leave_trigger 解消。
- テスト **14 passed**（round347 cards 4件＝disposition＋登録形の実挙動3件〔CIP mode 1 全体破壊／ブレイク経路 mode 0 捨て札／普通のシールドでは不発〕、pilot312 cards 登録形書換 2件、data_audit 8件）＋第312弾本体 **6 passed**（別 invocation）。
- 回答は answers/round347.yaml に保存。次の番号: パイロット313 / ラウンド348 / プロト T964。

## 第313弾 cost_le_count（「マナの枚数よりコストが小さい」）— ドリフト

センサス（rejects 2,069件を再集計）: 純粋ファミリーの大半は範囲外（gr_summon 147、aura 108、hyperdimensional_zone 105、dragheart 45、psychic_filter 45、hyperdimensional_summon 41、out_of_game 23、duelist_link 20、outside_game 12、pandora_shift 4）か評価済み DEEP/重い/延期。第312弾の監査（`gaps` 空・unsupported にだけギャップ名が残る NEO 期の行）を継続し、残り21行を1件ずつ公式本文＋partial で評価した。内訳: 範囲外1件（dmex17-032 超次元ドラグハート装備）、現実依存の主観条項1件（dmex08-153 subjective_kawaii_mechanic「一番可愛い」は正確に表せない）、残りは各行に別のブロッカー（must_attack_creature 条件付き攻撃対象制限、become_evolution_base_trigger「上に進化された時」イベント未確認、attack_trigger_alt_summon 攻撃ウィンドウの召喚許可、j_big＋neo_summon_cost_reduction 支払いフロー隣接、gachinko_judge の追加ターン付与、choukon_raid 自身の evolve_from を参照する動的フィルタ、break_bonus 攻撃中ブレイク枚数参照、battle_destroy_replacement_to_mana バトル起因の置換、free_summon_condition_bounce 条件付き無料召喚＋全体バウンス、cast_opponent_graveyard_spell_resolve_bottom＋attack_end_restack_self の複合、kizuna_plus の能力コピー隣接 等）。正確に表せる行として本件 cost_le_count（3行）を選定。併せて同監査から stack_from_deck_search（dmex18-045、第308弾の activate 形と完全一致）と under_dragons_return_on_destroy（dmex12-s19、第294弾 form B＋event.was_under）がドリフト候補として残る（次弾以降の候補、本弾では扱わない）。

対象は dm26rp3-std010 BARUGA-雷座87 の3刷（dm26rp3-std010 / dm26rp3-stdchosec010 / dm26rp3-stdsec010、partial は id/name 以外完全同一）。partial は NEO進化・W・ブレイカー・CIP「山札の上から2枚をタップしてマナゾーンに置く」まで完成済みで、欠けているのはメテオバーンの後半「自分のマナゾーンにあるカードの枚数よりコストが小さいクリーチャーを1体、自分のマナゾーンから出す」だけだった。

結論: **ドリフト**（新規語彙・エンジン変更なし）。ギャップ名 cost_le_count は第117弾 cost_lt_count の別名ドリフト:

- 「Xの枚数よりコストが小さい」= filter の cost_le に {sum: [{count: ...}, -1]}（第117弾の確立形。「より小さい」は枚数−1 以下）。マナ枚数で数える形も登録済み先例あり（dm26ex3-082 蒼龍の大地：cost_le: {sum: [{count: {zone: mana, owner: you}}, -1]}。選択時点＝出す前のマナ枚数で数える読みも同先例で固定済み。本件も選択時点で数えるため、燃やした下カードはマナ枚数に影響しない）。
- 攻撃時メテオバーン「このクリーチャーの下にあるカードを1枚墓地に置いてもよい。そうしたら～」= dm19-007 の確立イディオム {kind: trigger, when: {event: attack, subject: self}, effect: [may [move {under_of: self, count: 1} → graveyard, reason: put, as: paid, if {exists: {ref: paid}} → 続き]]}。下が無い場合は move が何も束縛せず if で止まる（実挙動で固定）。
- マナから出す = move {select: {zone: mana, owner: you, filter: {types: [creature], cost_le: ...}, count: 1}, to: bz, reason: put}（dm26ex3-082 と同形。play_free はマナ源の登録先例なし。本文に進化除外の指定はないため not_types は付けない）。

- プロト T964（std010 型: NEO進化＋CIP＋メテオバーン）。次の空きは **T965**。
- tests/test_vocab_pilot313.py: **6 passed** — parse（neo・evolve_from・2誘発）、CIP（山札上2枚がタップしてマナへ、マナ5→7）、メテオバーン本筋（マナ7枚時にコスト7の T142・コスト9の T095 は候補に出ず、コスト2だけが候補。燃やした進化元は墓地へ、選んだ1体が場へ、マナ7→6）、辞退（下が残り何も出ない）、下なし素出し（出す選択自体が出ない）、対象なし（マナの獣が全てコスト7以上＋CIP分は呪文 → 燃やすだけ）。
- tests/test_vocab_pilot313_cards.py: **3 passed** — 対象3行の残留（gaps 空・unsupported は当該ギャップのみ・未登録・3刷の partial は id/name 以外同一）、確立形 FORM（partial ＋ メテオバーン誘発）の parse と cost_le 式の形。
- 回帰: 第307・312弾＋data_audit＋rust_schema_sync＋test_rules **64 passed**、第117・305・311弾 **20 passed**。既知の事前失敗2件（第274弾・第31弾）は範囲外。_mana_choices には触れていない。エンジン変更なし（Rust 手順不要）。

テスト中の発見: setup() の山札 spec は内部順序が spec の並びと一致しない（CIP で取る2枚は spec 内の位置から予測できない）。山札上カードの素性を固定したい場合は spec を単一 defn で揃えること。NEO進化のプレイキーは play:<defn>:neo（接尾辞なしは素出しになる）。

収支: converted **10,251（不変）** / rejects **2,069（不変）**。変更は proto.yaml（T964 純追加）・テスト2件・docs のみ。

### ラウンド348側の注意

- 対象は dm26rp3-std010 / dm26rp3-stdchosec010 / dm26rp3-stdsec010 の3件。提出形は tests/test_vocab_pilot313_cards.py の FORM（partial ＋ メテオバーン誘発、unsupported 除去）。
- 対象行は `gaps` が空のため reopen では外れない（第323・343・347弾の先例どおり直接 submit）。
- 3件は同一カードの3刷（うち2件は secret 系）: submit 前に identity で正本判定し、id・alias を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること。partial の name は「BARUGA-雷座87(DM26RP3 STD10/)」の表記ゆれを含むため、登録名は公式データ側で確認すること。
- 登録後は abilities が [CIP誘発, メテオバーン誘発] の2件ちょうどであることを本文と照合すること（連結・merge_split 混入の確認）。

### ラウンド348（cost_le_count 再変換）

- 新規登録 **1件**: dm26rp3-std010 BARUGA-雷座87(DM26RP3 STD10/)。alias 畳み込み **4件**: dm26rp3-stdchosec010 / dm26rp3-stdsec010 / dm25ex3-023 / dm25rp2-021 → dm26rp3-std010。stale クリーンアップ **2件**（stdchosec010 / stdsec010 の reject 行、後述）。差し戻し0件。
- 正本判定は identity 実測: canon_id は3刷とも dm26rp3-std010、aliases_for（BARUGA-雷座87, dm26rp3-std010） = [dm25ex3-023, dm25rp2-021, dm26rp3-stdchosec010, dm26rp3-stdsec010]。submit 前照合: 対象 id と alias 計5件すべて converted / real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml に無し（proto.yaml のヒットは第313弾プロト T964 の text 内参照のみ）。登録名は公式データ（by_product/26rp3.jsonl）の表記「BARUGA-雷座87(DM26RP3 STD10/)」で partial の表記と一致。対象行は gaps が空のため reopen では外れず直接 submit（第323・343・347弾の先例）。
- 登録形は確立形と完全一致（partial ＋ メテオバーン誘発、unsupported 除去、source.aliases に4件を記録）。abilities は [CIP誘発, メテオバーン誘発] の2件ちょうど、keywords は [double_breaker]、連結・merge_split 混入なし（回答との全項目一致を実測）。
- **stdchosec010 / stdsec010 の reject 行の扱い**: submit は std010 の行だけを外し、2刷の行は残った（第347弾 sec004 と同型）。登録により両者は std010 の alias として完全にカバーされるため、stale クリーンアップとして行だけを除去した。dm25ex3-023 / dm25rp2-021 は reject 行自体が無く alias 記録のみ。
- converted **10,251 → 10,252** / rejects **2,069 → 2,066**、canonical 重なり0・漏れ0。cost_le_count は対象3行から解消（ギャップ名は多重ギャップ行 dm25ex3-rp1s02 にのみ残る: neo_summon_cost_reduction を併せ持ち、その cost_le_count は「手札の枚数以下のコストを持つカードなら実行してもよい」という別用法で、本ラウンドの対象外）。
- テスト **14 passed**（round348 cards 4件＝disposition＋登録形の実挙動3件〔CIP で山札上2枚がタップしてマナへ／メテオバーン本筋＝マナ7枚時にコスト7・9は候補に出ず燃やした進化元は墓地・選んだ1体が場へ・マナ7→6／辞退で下が残る〕、pilot313 cards 登録形書換 2件、data_audit 8件）＋第313弾本体 **6 passed**（別 invocation）。
- 回答は answers/round348.yaml に保存。次の番号: パイロット314 / ラウンド349 / プロト T965。

## 第314弾 stack_from_deck_search（山札を見て自分の上に置く）— ドリフト（第308弾の activate 形）

センサス（rejects 2,066件）: 第313弾の監査で記録されたドリフト候補2件を公式本文＋partial で検証した。under_dragons_return_on_destroy（dmex12-s19 燃える侵略 レッドギラゴン）も第294弾 form B ＋ filter {race_has: ドラゴン, not_types: [evolution]}（not_types は既存フィルタキー）で書ける見込みだが、本弾は第308弾の形と完全一致する **stack_from_deck_search（dmex18-045 ワンケングレンオー ～弧月躍動～、純粋1件）** を選定した（s19 は次弾以降の候補として残る）。対象行は gaps 空・unsupported にだけギャップ名が残る監査行（第312・313弾の監査の継続）。

未解決条項は起動能力1節のみで、残り（NEO進化 evolve_from {any_of: [{civs: [nature]}, {name_has: ケングレンオー}], types: [creature]}、出た時「山札の上から1枚目をマナゾーンに置く」誘発）は partial で完成済み:

- 「このクリーチャーで攻撃するかわりに、タップして次の能力を使ってもよい」= {kind: activate, cost: {tap: self}}（第308弾ほか多数の先例。起動は attack 決定で activate:<defn>:* として提示される）。
- 「自分の山札を見る。その中から、名前に《ケンゴウグレンオー》とあるクリーチャーを1体、このクリーチャーの上に置いてもよい。その後、山札をシャッフルする」= may [choose {zone: deck, owner: you, look: true, filter: {name_has: ケンゴウグレンオー, types: [creature]}, count: 1} as p → move {select: {ref: p, count: all}, to: bz, reason: put, stack_evo: true, evo_source: {ref: self}}] ＋ {op: shuffle}（第173弾 deck_evolution の全山札検索形、第308弾で実挙動固定済み。本件は第308弾の2件にあった全体破壊の節が無いだけで、may＋shuffle の構造は同一）。
- 探索名は《ケンゴウグレンオー》であって進化元の《ケングレンオー》ではない。本カードの名《ワンケングレンオー》は、上に乗る dmc64-025 ケンゴウグレンオーの evolve_from {name_has: ワンケングレンオー} と一致する（第308弾 024/025 と同じ名前の連鎖）。重ね先の適格性は解決時に照合される（ops の stack_evo 分岐）。

新規語彙・エンジン変更なし（_mana_choices 未接触、Rust 手順不要）。

- プロト T965（dmex18-045 型: NEO進化＋CIP＋起動能力。探索対象には既存の T949 試験用ケンゴウグレンオー・鳴動を再利用し、名前に《ケングレンオー》を含むが《ケンゴウグレンオー》を含まない T951 を対照として混ぜた）。次の空きは **T966**。
- tests/test_vocab_pilot314.py: **5 passed** — parse（neo・evolve_from any_of・[誘発, 起動] の並び・起動の形が確立形と完全一致）、CIP（手札から出して山札上1枚がマナへ。山札 spec は単一 defn で揃え、枚数は相対で固定）、起動本筋（候補は T949 の2枚だけで T951 は提示されない／選んだ1枚が上に重なり、もう1枚は山札に残る／起動コストでタップ）、辞退（重ならず山札不変・コストは支払う）、対象なし（山札に該当なしで空振り安全）。
- tests/test_vocab_pilot314_cards.py: **3 passed** — 対象行の残留（gaps 空・unsupported は当該ギャップのみ・未登録・ファミリーはこの1件だけ）、提出形 FORM（partial ＋ 起動能力）が partial の完成済み節と一致し text は公式全文と一致、FORM の parse と起動の形。
- 回帰: 第308・173・249・305弾＋data_audit＋test_rules＋rust_schema_sync **84 passed**。既知の事前失敗2件（第274弾・第31弾）は範囲外。

テスト中の発見: choose の候補が1枚だけだと選択は自動決定され choose_cards 決定として現れない（候補の内訳を固定したい場合は同 defn を2枚入れる）。choose_cards の選択肢は defn キーを持たず cid を持つ（defn は e.s.cards[cid].defn で引く）。公式 text は行頭の「t」だけ半角で「次のｔ能力」は全角（転記時に混同しやすい）。

収支: converted **10,252（不変）** / rejects **2,066（不変）**。変更は proto.yaml（T965 純追加）・テスト2件・docs のみ。

### ラウンド349側の注意

- 対象は dmex18-045 の1件。提出形は tests/test_vocab_pilot314_cards.py の FORM（partial ＋ 起動能力、unsupported 除去）。partial の他の節は完成済みで、公式全文からの追加構築は不要。
- 対象行は `gaps` が空のため reopen では外れない（第323・343・347・348弾の先例どおり直接 submit）。
- submit 前に identity で正本判定を行い、id・alias を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること。
- 登録後は abilities が [CIP誘発, 起動能力] の2件ちょうどであることを本文と照合すること（連結・merge_split 混入の確認）。keywords は無し（本文にキーワード能力なし）。

### ラウンド349（第314弾の再変換）

**新規登録1件**（dmex18-045 ワンケングレンオー ～弧月躍動～＝partial の CIP 誘発＋第314弾の起動能力〔第308弾の activate 確立形＋第173弾 deck_evolution の全山札検索形〕、unsupported 除去。登録形は確立形と完全一致で abilities は [CIP誘発, 起動能力] の2件ちょうど、keywords 無し、連結・merge_split 混入なし）・**alias 畳み込み0件**（identity 実測で canon_id は自id、aliases_for は空）・**stale クリーンアップ0件**・**差し戻し0件**。対象行は gaps が空のため直接 submit。提出前照合: 対象 id は real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / converted.yaml のいずれにも無し（proto.yaml のヒットはプロトカードの text 内参照のみ）。converted 10,252→**10,253** / rejects 2,066→**2,065**、重なり0・漏れ0。stack_from_deck_search はファミリー単独行のため完全解消。pilot314 cards を登録形に書換、round349 cards を新設（登録カード自身の実挙動: CIP で山札上1枚がマナへ／起動本筋＝候補は T949 の2枚だけで T951 は提示されず、選んだ1枚が上に重なる・もう1枚は山札に残る・起動コストでタップ／辞退で重ならずコストだけ払う）。テスト14 passed（round349 cards 4＋pilot314 cards 登録形 2＋data_audit 8）＋第314弾本体5 passed（別 invocation）。

## 第315弾 under_dragons_return_on_destroy（「下にあった進化ではないドラゴンをすべて出す」）— ドリフト（第294弾 form B）

対象は dmex12-s19 燃える侵略 レッドギラゴン の純粋1件。gaps 空・unsupported にだけギャップ名が残る監査行（第312〜314弾の監査の継続、第314弾で表現可能と評価された候補）。partial の他節（NEO進化、侵略＝面フィールド declare〔登録済み dm26ex1-019 等と同形〕、W・ブレイカー、攻撃の終わりに山札の上から1枚目を表向きにして下に重ねる）は完成済みで、不足は最終節「このクリーチャーが破壊された時、その下に重ねてあった進化ではないドラゴンをすべてバトルゾーンに出す」のみ。

- **確立形（追加語彙なし）**: 第294弾 form B（登録済み dmex12-004 デュエにゃん皇帝と同形）の filter を替えるだけ: 破壊トリガー {when: {event: move, from: bz, to: graveyard, reason: destroy, subject: self}, effect: [{op: play_free, select: {ref: event.was_under, zone: graveyard, filter: {race_has: ドラゴン, not_types: [evolution]}}}]}。「進化ではないドラゴン」= race_has: ドラゴン（種族文字列への部分一致。第294弾の put_under filter でも使われた既存キー not_types: [evolution] で進化を除外）。エンジン変更なし（_mana_choices 未接触、スキーマ再生成なし）。
- プロト T966（dmex12-s19 型: NEO進化＋攻撃の終わりの下置き＋本弾の破壊誘発）＋役カード T967（非進化ドラゴン）/ T968（進化ドラゴン）/ T969（非ドラゴン）。tests/test_vocab_pilot315.py（4件: parse＋形の一致、本筋＝下の3種のうち非進化ドラゴンだけが出て進化ドラゴン・非ドラゴンは墓地に残り、下に無かった同種ドラゴンは出ない、実条項連鎖＝NEO進化元の上に乗り攻撃の終わりに山札の上（ドラゴン）を重ねて破壊されると下のドラゴン2枚とも出る、対照＝下が非ドラゴンだけなら何も出ない）＋ tests/test_vocab_pilot315_cards.py（2件: 対象行の残留・ファミリー単独・提出形 parse［parse 展開後はキーワード由来 static が先頭に付く］）。
- **テスト中の注意**: 下カードは束の一部として bz ゾーンに居るため zone 属性では出入りを判定できない（zone は最初から bz）。done 条件は本体の墓地行きで取り、出たことは top_of < 0（独立したクリーチャー化）で確認する。
- テスト結果: 第315弾本体 **4 passed**、cards **2 passed**、回帰（第294・308・313・314弾本体＋test_data_audit＋test_rules＋test_rust_schema_sync）**82 passed**、cards 回帰（第294・314弾 cards＋round349 cards）**8 passed**。既知の事前失敗2件（第274弾の _mana_choices 競合、第31弾 janken）には触れていない。converted 10,253 / rejects 2,065 は不変。
- ラウンド350側の注意: 対象行は gaps が空のため reopen では外れない → 直接 submit（第323・343・347・348・349弾の先例）。提出形は tests/test_vocab_pilot315_cards.py の FORM（partial ＋ 破壊誘発、unsupported 除去）で、登録後は raw の abilities が [攻撃の終わり誘発, 破壊誘発] の2件ちょうどであることを本文と照合すること（keywords は double_breaker のまま）。submit 前に identity で正本判定し、id・alias を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること。
- 次の番号: パイロット316 / ラウンド350 / プロト T970。

### ラウンド350（第315弾の再変換）

**新規登録1件**（dmex12-s19 燃える侵略 レッドギラゴン＝partial の完成済み節〔NEO進化・侵略 declare・攻撃の終わり誘発〕＋第315弾の破壊誘発〔第294弾 form B の filter を {race_has: ドラゴン, not_types: [evolution]} に替えたもの〕、unsupported 除去。登録形は確立形と完全一致で raw の abilities は [攻撃の終わり誘発, 破壊誘発] の2件ちょうど、keywords は double_breaker のまま、連結・merge_split 混入なし）・**alias 畳み込み0件**（identity 実測で canon_id は自id、aliases_for は空）・**stale クリーンアップ0件**・**差し戻し0件**。対象行は gaps が空のため直接 submit。提出前照合: 対象 id は real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / converted.yaml のいずれにも無し（proto.yaml のヒットは第315弾プロト T966 の text 内参照のみ）。submit の lint は助言のみ（play_free の reason: summon への注意喚起。第294弾 form B＝登録済み dmex12-004 と同形のため確立形どおり）。converted 10,253→**10,254** / rejects 2,065→**2,064**、重なり0・漏れ0。under_dragons_return_on_destroy はファミリー単独行のため完全解消。pilot315 cards を登録形に書換、round350 cards を新設（登録カード自身の実挙動: 破壊で下の非進化ドラゴンだけが出る／攻撃の終わりに山札の上を重ねて破壊されると下のドラゴン2枚とも出る／下が非ドラゴンだけなら何も出ない）。テスト14 passed（round350 cards 4＋pilot315 cards 登録形 2＋data_audit 8）＋第315弾本体4 passed（別 invocation）。テスト中の発見: scenario.build の山札は spec の末尾が上（リスト index 0 が上）で、圧縮山札は破壊解決後のターン進行で deck_out しうるため、条項連鎖テストでは下に余分なカードを敷いて防いだ。回答は answers/round350.yaml に保存。次の番号: パイロット316 / ラウンド351 / プロト T970。

## 第316弾 filter_not_keyword（「『ブロッカー』以外のクリーチャー」）— 最小語彙追加（フィルタキー not_keyword）

センサス先行（rejects 2,064件を取り直し）: 第312〜315弾の空 gaps 監査ラインは表現可能なファミリーを使い切った（空 gaps 行は残り18件、全て監査で別ブロッカー確認済み）。pure ファミリーの上位は範囲外が占める（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone 105 / dragheart 45 / psychic_filter 45 / hyperdimensional_summon 41 / out_of_game 23 / duelist_link 20 / outside_game 12 / pandora_shift 4）。範囲内・未評価で最小だった **filter_not_keyword（純粋2件: dm06-016 / dm18-022、ともにジャスティス・バインドの同名2刷。multi-gap 行には現れない）** を選定した。両行の partial の notes 自身が「フィルタにキーワードの否定が無いため絞れない（not_keyword 相当が無い）」と明記しており、ギャップの実体はフィルタキーの欠落そのもの。

検討して見送った候補: フィールド系（wd_field 3 / historic_field 3 / dg_field 2 / dm_field 2 / forbidden_field 2）は型マーカーではなく各カード固有の機構（WD＝裏面側への反転、ヒストリック＝最初のターンに手札公開で無償で出す等）で均一な小語彙にならない。does_not_untap（2件）は自他2形が混在し他節も重い。all_civilizations_condition（3件: dm26sd1-b005 / b013 / dm27-050）はマナ全文明条件のイディオム検証が未了（b005 はエレメント全域＋モーダル全使用で別格）— 次弾以降の候補として残す。

- **追加語彙（最小）**: フィルタキー **not_keyword**。defs FILTER_KEYS に追加し、selectors.filter_match に既存 keyword の鏡像（not_keyword が特性値 keywords に含まれれば不一致）を1分岐追加。schema は FILTER_KEYS から生成されるため再生成し、差分は not_keyword の3行のみ（filter 本体・evolve_from・もう1箇所の filter 参照）。dataaudit は defs の FILTER_KEYS を参照するため追加作業なし。Rust 手順: フィルタキーはデータ側の語彙で、第278弾 races_all と同型（エンジンの状態フィールド追加なし。test_rust_schema_sync passed）。
- **判定の意味論**: 特性値の keywords は静的付与分を含む（core の grant 反映）ため、「ブロッカー」を付与されたクリーチャーも「ブロッカー以外」から外れる。既存 keyword フィルタと同じ見方で、ルール上も付与されたブロッカーはブロッカーとして扱うのが正しい。本体テストで実挙動固定（付与獣 T971 の下のバニラはタップせず、付与対象外の T971 本体はタップする）。
- **確立形**: 呪文面 [{op: tap, select: {zone: bz, owner: any, filter: {types: [creature], not_keyword: blocker}, count: all}}]。dm18-022 の partial には tap 形が完成済みで filter に not_keyword: blocker を足すだけ。dm06-016 の partial は spell 本体を持たない骨組みのため、提出形は dm18-022 と同じ spell を補って構築する（本文は各行の公式テキストのまま。表記差: dm06-016 は旧表記「S(シールド)・トリガー」、dm18-022 は「S・トリガー」）。
- プロト T970（ジャスティス・バインド型: 光4コスト呪文・S・トリガー）＋ T971（役カード: 自分の他のクリーチャーにブロッカーを付与する静的。other: true で自身を含まない）。対照には既存 T001（バニラ）/ T004（印刷ブロッカー）を使用。次の空きは **T972**。
- tests/test_vocab_pilot316.py: **4 passed** — parse（T970 の spell が確立形と一致・keywords [s_trigger]、T971 の grant 形）、未知フィルタキーが今も DefError で弾かれること、本筋（自他両方のバニラをタップし印刷ブロッカーは自他ともタップしない）、付与ブロッカー（付与されたバニラはタップせず、付与対象外の本体と相手バニラはタップする）。
- tests/test_vocab_pilot316_cards.py: **2 passed** — 対象2行の残留（gaps・unsupported ともに当該ギャップのみ・未登録・ファミリーはこの2件だけ）、提出形2種（dm18-022＝partial の tap 形＋not_keyword が確立形と一致、dm06-016＝spell を補った形）の parse と spell の形。
- 回帰: 本体群（第278・287・288・311・315弾＋test_rules）**93 passed**、cards/audit 群（test_data_audit＋test_rust_schema_sync＋第315・278弾 cards）**20 passed**。既知の事前失敗2件（第274弾・第31弾）は範囲外で未接触。selectors.py に触れたが _mana_choices は未接触。
- 収支: converted **10,254（不変）** / rejects **2,064（不変）**。変更は defs.py・selectors.py・card.schema.json・proto.yaml（T970/T971 純追加）・テスト2件・docs のみ。

### ラウンド351側の注意

- 対象は dm06-016 / dm18-022 の2件。提出形は tests/test_vocab_pilot316_cards.py の FORM 相当（_form(tid)）: dm18-022 は partial の spell の filter に not_keyword: blocker を追加、dm06-016 は dm18-022 と同じ spell を補う。どちらも unsupported を外す。
- 対象2行は gaps = [filter_not_keyword] を持つため reopen で外れる見込みだが、reopen は gaps ⊆ の全行を外すため、出力行を数えて対象2件だけであることを確認すること（混入時は直接 submit へ切り替える）。
- 正本判定は identity の実データで submit 前に行うこと。dm18-022 の partial の source.aliases には既に dm06-016 が記録されているが、それだけで正本を決めない。id・alias を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること。
- 登録後は spell が [tap 1件] ちょうどで filter が {types: [creature], not_keyword: blocker} であることを本文と照合すること（連結・merge_split 混入の確認）。keywords は [s_trigger] のまま。
- 次の番号: パイロット317 / ラウンド352 / プロト T972。

### ラウンド351（第316弾の再変換）

**新規登録1件**（dm18-022 ジャスティス・バインド＝partial の完成済み tap 形の filter に第316弾の not_keyword: blocker を追加、unsupported 除去。登録形は確立形と完全一致で spell は [tap 1件] ちょうど、filter は {types: [creature], not_keyword: blocker}、keywords は [s_trigger] のまま、連結・merge_split 混入なし）・**alias 畳み込み1件**（dm06-016 → dm18-022、identity 実測で canon_id は dm18-022 が正本。dm18-022 の partial の aliases 記録だけで決めたのではない。dm06-016 の提出形は同じ spell を補って構築したが、正本側の登録に畳み込まれた）・**stale クリーンアップ0件**・**差し戻し0件**。対象2行は gaps = [filter_not_keyword] のため reopen で外してから submit（rejects の差分は対象2行のみ）。提出前照合: 対象 id・alias は real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / converted.yaml のいずれにも無し（proto.yaml のヒットは第316弾プロト T970 の text 内参照のみ）。converted 10,254→**10,255** / rejects 2,064→**2,062**、重なり0・漏れ0。filter_not_keyword はファミリーがこの2行だけだったため完全解消。pilot316 cards を登録形に書換、round351 cards を新設（登録カード自身の実挙動: 自他両方のバニラをタップし印刷ブロッカーは自他ともタップしない／T971 の静的で付与されたブロッカーはタップせず、付与対象外の T971 本体と相手バニラはタップする）。テスト13 passed（round351 cards 3＋pilot316 cards 登録形 2＋data_audit 8）＋第316弾本体4 passed（別 invocation）。回答は answers/round351.yaml に保存。次の番号: パイロット317 / ラウンド352 / プロト T972。

## 第317弾 all_civilizations_condition（「すべての文明が揃っていれば」）— ドリフト（追加語彙なし）

対象は純粋3件: dm26sd1-b013 フェアリー・ミラクル / dm27-050 ゴレン・キャノン / dm26sd1-b005 魔誕と光喜と楽識と炎怒と哀樹の決断。第316弾で「マナ全文明条件のイディオム検証が未了」として残された候補。3行とも partial は骨格（unsupported のみ）で spell 本体が無い。

- **条件の確立イディオム（マナ版）**: 登録済み **dmx16-064 奇跡の面 ボアロジー**（フェアリー・ミラクルと同文の CIP「置く。その後、揃っていれば、さらに1枚」）が既にこの形で登録されていた: `{op: if, cond: {all: [cmp: [{count: {zone: mana, owner: you, filter: {civs: [文明]}}}, ">=", 1] ×5文明]}, then: [...]}`。「すべての文明」は5文明（光・水・闇・火・自然）で、多色カードは各文明を満たす（filter civs の通常の意味論）。もう1件の登録先例 dmex15-b030（G・ゼロの同条件）もある。本弾はこの条件を新規に作らず、既存イディオムの適用範囲として固定した。
- **形A（dm26sd1-b013 フェアリー・ミラクル）**: spell = [mana_put {from_top: 1}, if（マナ全文明）→ mana_put {from_top: 1}]。条件は1枚目を置いた**後**に判定する（本文の順序どおり。本体テストで「1枚目で揃って2枚目が置ける／揃わなければ置けない」を両方向で固定）。山札の上から置く形は from_top: 1（converted 内120件の多数形。dmx16-064 の count: 1 形は隠れ選択になる旧形で、指す先は同じ）。
- **形B（dm27-050 ゴレン・キャノン）**: spell = [destroy {zone: bz, owner: opp, filter: {types: [creature], power_le: 3000}, count: 1}, if（マナ全文明）→ 同じ destroy]。
- **形C（dm26sd1-b005）**: 条件は「自分の**エレメント**にすべての文明」であってマナゾーンではない。**総合ルール403.1**（エレメントに影響を及ぼす・参照する効果は、テキストに他のゾーンの記載がない限りバトルゾーンのエレメントのみを参照する）により zone: **bz** で数える。裏付け: (1) 本カードは5文明コスト [光水闇火自然] のため、通常の唱え方では支払いに5文明すべてのマナをタップしなければならず、マナ読みでは置換条項が常時成立して無意味になる（設計上ありえない）。(2) dmwiki のカードページの条件達成例は魔法陣サイクル（タマシード）・《天災 デドダム》＋《龍風混成 ザーディクリカ》・《虹速 ザ・ヴェルデ》・《超越男》・《愛の無限オーケストラ》自身などバトルゾーンのカードのみで、同ページは「このカードがマナゾーンにある」話をフェアリー・ミラクル側の条件として別に書いている。(3) 第145弾のバラバラエティ [bz, mana] はコストという特性値の参照（カードタイプ特性の参照はバトルゾーン以外でも有効という同ルールの另一面）で、本弾の存在条件とは別件として触らない。本体テストに判別テストを置いた: マナに全文明が揃い場が揃わない局面では置換の may は提示されず通常の2回選択になる。
- **形Cの本体**: `{op: if, cond: 全文明（bz）, then: [{op: may, body: [modal {count: 5, modes}], else: [modal {count: 2, repeat: true, modes}]}], else: [modal {count: 2, repeat: true, modes}]}`。modal {count: 5}（モード5種・repeat なし）は全選択が自動決定され書かれた順に解決する（公式どおり「上から順に解決」）。モードは既存先例の合成: シールド化＝move {select: {zone: deck, owner: you, from_top: 1}, to: shield, reason: charge}（dm22ex2-068）、2ドロー、見ないで捨てさせる＝discard {chooser: random}（dm24ex1-003）、相手のエレメント破壊＝destroy {select: {zone: bz, owner: opp, filter: {cost_le: 6}, count: 1}}（dm26rp3-011 モード3の destroy エレメント形。破壊はバトルゾーンのみ＝403.1）、マナ置き＋may でマナから手札回収（move {zone: mana → to: hand, reason: return} の先例形）。
- プロト T972（形A）/ T973（形B）/ T974（形C）。次の空きは **T975**。
- tests/test_vocab_pilot317.py: **8 passed** — parse（3形ともプロトと確立形の完全一致。期待形は parse のマクロ展開形で記述）、形A（1枚目で揃う→2枚目／揃わない→1枚のみ）、形B（全文明→2体破壊・パワー4000は対象外／不揃い→1体）、形C（場全文明＋全使用を選択→5モードが順に解決: シールド5→6・2ドロー＋回収で手札3・相手手札−1・相手の獣破壊・マナ5→+1→−1。yes_no は全使用と回収の2回／**判別**: マナ全文明でも場不揃いなら may は出ず通常2回選択／場全文明でも全使用を断れば通常2回選択）。
- tests/test_vocab_pilot317_cards.py: **2 passed** — 対象3行の残留（gaps・unsupported ともに当該ギャップのみ・未登録・ファミリーはこの3件だけ）、提出形3種（partial の骨格＋構築 spell）の parse とプロト形との一致。
- 回帰: 本体群（第145・279・316弾＋test_rules＋test_rust_schema_sync）**63 passed**、cards/audit 群（第316弾 cards＋第292弾 cards＋round327 cards＋test_data_audit）**22 passed**。エンジン・defs・スキーマ変更なし（_mana_choices 未接触）。既知の事前失敗2件（第274弾・第31弾）は範囲外で未接触。
- 収支: converted **10,255（不変）** / rejects **2,062（不変）**。変更は proto.yaml（T972〜T974 純追加）・テスト2件・docs のみ。

### ラウンド352側の注意

- 対象は dm26sd1-b013 / dm27-050 / dm26sd1-b005 の3件。提出形は tests/test_vocab_pilot317_cards.py の FORM 相当（_form(tid)）: partial の骨格に構築した spell を足し、unsupported を外し、text は各行の公式全文に差し替える（partial の text は切れている）。形A/B の spell は2ステップ、形C は if 1件ちょうどであることを登録後に本文と照合すること（連結・merge_split 混入の確認）。
- 対象3行は gaps = [all_civilizations_condition] を持つため reopen で外れる見込みだが、reopen は gaps ⊆ の全行を外すため、出力行を数えて対象3件だけであることを確認すること（混入時は直接 submit へ切り替える）。
- 正本判定は identity の実データで submit 前に行うこと。b005 の partial の source.aliases には dm24ex3-rp4011 / dm24ex3-rp4sec15 / dm24rp4-011 / dm24rp4-sec15 の記録があるが、それだけで正本を決めない。b013 の alias は17件（dm24bd4-015 / dm27-053 / dm27-053cc / dmart03-003 / dmbd01-015 / dmex06-095 / dmex08-099 / dmrp18-a13 / dmrp18-b13 / dmx01-039 / dmx14-080 / dmx16-070 / dmx22b-078 / dmx26-026 / promoy17-056 / promoy23-070 / promoy23-073）。id・alias を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること。なお b005 の公式全文は dm24rp4-011 と同一（「（同じものを選んでもよい）」の括弧の有無など印刷差は各行の原文どおりにする）。
- 次の番号: パイロット318 / ラウンド353 / プロト T975。

### ラウンド352（第317弾の再変換）

**新規登録3件**（dm26sd1-b013 フェアリー・ミラクル＝形A〔mana_put の後に if。条件は1枚目を置いた後に判定〕 / dm27-050 ゴレン・キャノン＝形B〔destroy の後に if＋destroy〕 / dm26sd1-b005 魔誕と光喜と楽識と炎怒と哀樹の決断＝形C〔条件は zone: bz（403.1）、if → may [modal 全5モード] else [modal 2回・同選択可]〕。いずれも partial の骨格＋構築 spell、unsupported 除去、text は公式全文。登録形は確立形と全項目一致で、形A/B の spell は2ステップ・形C は if 1件ちょうど、keywords なし、連結・merge_split 混入なし）・**alias 畳み込み0件**（b013 の17件・b005 の4件は登録エントリの source.aliases への記録のみで、alias 側の reject 行は元々無し。dm27-050 は alias 無し）・**stale クリーンアップ0件**・**差し戻し0件**。対象3行は gaps = [all_civilizations_condition] のため reopen で外してから submit（reopen の出力は対象3件ちょうど）。正本判定: identity の canon_id 実測で3件とも自 ID（b005 の partial の aliases 記録だけで決めたのではない）。提出前照合: 対象 id と全 alias（計24件）は real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml のいずれにも無し、同名カードの converted 登録も無し。converted 10,255→**10,258** / rejects 2,062→**2,059**、重なり0・漏れ0。all_civilizations_condition はファミリーがこの3件だけだったため完全解消。pilot317 cards を登録形に書換、round352 cards を新設（登録カード自身の実挙動: 形A 両方向／形B 両方向＋パワー4000対象外／形C 全モード順次解決・マナ全文明でも場不揃いなら置換なしの判別・辞退時の fallback）。テスト18 passed（round352 cards 8＋pilot317 cards 登録形 2＋data_audit 8）＋第317弾本体8 passed（別 invocation）。回答は answers/round352.yaml に保存。次の番号: パイロット318 / ラウンド353 / プロト T975。

## 第318弾 「ただし、その『S・トリガー』は使えない」（shield_to_hand_strigger_deny）— ドリフト（第296弾 形A の印）

センサス（rejects 2,059件を再集計）: 空 gaps 行18件は全て第312〜315弾の監査で別ブロッカー確認済み。純粋ファミリーの大半は範囲外（gr_summon 147、aura 108＝未承認、hyperdimensional_zone 105、dragheart 45、psychic_filter 45、hyperdimensional_summon 41、out_of_game 23、duelist_link 20、outside_game 12、pandora_shift 4）か評価済み DEEP/重い/延期（ignore_abilities、copy_abilities、attack_target_choice、mana_tap_trigger、enter_rules_ignore、all_civs_treatment、dynamic_name_reference_filter、deck_faceup_power、static_if_own_current_power、per_evolution_base_cost_reduction、revealed_pile_breaks_and_placement、break_limit、per_card_tap_or_untap、next_spell_cost_reduction、opponent_chooses_deck_position、dokindam_gacha、victory_icon_filter、cost_sum_of_revealed、climax_dorongo、shield_manipulation、spell_replay、summon_lock、cancel_attack、must_attack_next_turn、untap_restriction、power_comparison、conditional_resummon、negate_cannot_attack、doron_go、joe、majibomber、evolution_base_from_graveyard、exclude_ref 等）。フィールド系（wd_field 3 / historic_field 3 / dg_field 2 / dm_field 2 / forbidden_field 2 / t2_field 1 / fairy_field 1 / mugon_field 1）は第316弾の評価どおり各カード固有の機構で均一な小語彙にならず、does_not_untap（2件）も自他2形混在＋他節が重いため、再検討しても見込みが立たない。範囲内・未評価で最小の **shield_to_hand_strigger_deny（純粋2件）** を選定した。

対象は dm24ex3-or1 超天使 ゴルドラン・ゴルギーニ / dmrp22-031 エメラルの海幻。両行とも partial は完成済みで、未解決は「効果で自分のシールドを手札に加える時、その『S・トリガー』は使えない」の1節のみ。第296弾（shield_trigger_restriction / s_trigger_disable）とはギャップ名が違うため対象外だった同条項で、機構は第296弾 形A の move 引数 **strigger: "off"**（S・トリガーの印）そのもの — 追加語彙なしのドリフト。本弾は対象2行の形で再検証した:

- **形A1（dmrp22-031）**: シールド化（hand→shield、reason: charge）の直後に、改めて選んだシールドを手札へ戻す（reason: put）連続形。戻す move は as 束縛のゲート形（第296弾 dmx22b-023 / 変換済み dm03-042・dm26ex4-cho049）ではなく素の zone 選択で、may/if のゲートも無い。この戻す move に印を足すだけ。
- **形A2（dm24ex3-or1）**: 攻撃誘発の後段: 自分のシールドが10以上あれば、選んだシールド束を flip_up し、bundle_of＋filter で分割する（クリーチャーはすべて場へ、残りは手札へ）。印は ref＋bundle_of＋filter 経由の分割 move でも効くことを固定した。印は手札へ加える move のみに付け、クリーチャーを場に出す move には付けない。

- プロト T975（形A1）/ T976（形A1の対照: 印なし）/ T977（形A2）/ T978（形A2の対照: 印なし）。シールド役は既存 T960（光・S・トリガー呪文）と T001。次の空きは **T979**。
- tests/test_vocab_pilot318.py: **6 passed** — parse＋確立形一致、形A1（進化で重ねてシールド化→T960 を戻すと宣言なし＋印が付きシールド枚数は不変／対照では宣言あり）、形A2（攻撃誘発で束を分割し T001 は場・T960 は手札で宣言なし＋印／対照では宣言あり）。
- tests/test_vocab_pilot318_cards.py: **2 passed** — 対象2行の残留（gaps・unsupported ともに当該ギャップのみ・未登録・ファミリーはこの2件だけ）、提出形（partial の手札 move への印追加のみ）の parse と対応プロトとの abilities 完全一致。
- 回帰: 第296・281弾本体＋test_rules＋test_rust_schema_sync **66 passed**、test_data_audit＋第296弾 cards **11 passed**。エンジン・defs・スキーマ変更なし（_mana_choices 未接触）。既知の事前失敗2件（第274弾・第31弾）は範囲外で未接触。
- 収支: converted **10,258（不変）** / rejects **2,059（不変）**。変更は proto.yaml（T975〜T978 純追加）・テスト2件・docs のみ。

### ラウンド353側の注意

- 対象は dm24ex3-or1 / dmrp22-031 の2件。提出形は tests/test_vocab_pilot318_cards.py の _form 相当: partial の手札へ加える move に strigger: "off" を足し、unsupported を外したもの（他の条項は partial の完成形のまま）。登録後は abilities の件数・内容を本文と照合すること（両件とも abilities は2件ちょうどのはず）。
- 対象2行とも gaps = [shield_to_hand_strigger_deny] のため reopen で外れる見込み（ファミリーはこの2件だけなので出力は2件のはずだが、必ず数えること）。
- dmrp22-031 の partial の text は「シンカライズ」だけに切れているため、提出時は公式全文（シンカライズ説明＋CIP ドロー＋シンカパワー全文）に差し替えること。dm24ex3-or1 の partial の text は全文。
- 正本判定は identity の実データで submit 前に行うこと。dm24ex3-or1 の partial の source.aliases には dm24ex3-rp3or1 / dm24ex3-rp3sec01 / dm24rp3-or01 / dm24rp3-sec001 の4件の記録があるが、それだけで正本を決めない。id・alias を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること。
- 次の番号: パイロット319 / ラウンド354 / プロト T979。

### ラウンド353（第318弾の再変換）

**新規登録2件**（dm24ex3-or1 超天使 ゴルドラン・ゴルギーニ＝形A2〔攻撃誘発の束分割で残りを手札に加える move にのみ strigger: "off" の印。クリーチャーを場に出す move には付けない〕 / dmrp22-031 エメラルの海幻＝形A1〔シンカパワーの戻し move {zone: shield, count: 1} → hand に印〕。いずれも partial の完成形＋印追加、unsupported 除去。dmrp22-031 の text は partial が「シンカライズ」だけに切れていたため公式全文に差し替え。登録形は確立形と全項目一致で abilities は両件とも2件ちょうど、連結・merge_split 混入なし）・**alias 畳み込み1件分**（dm24ex3-or1 の alias 4件＝dm24ex3-rp3or1 / dm24ex3-rp3sec01 / dm24rp3-or01 / dm24rp3-sec001 を登録エントリの source.aliases に畳み込み。独立エントリにも reject 行にも無い。dmrp22-031 は alias 無し）・**stale クリーンアップ0件**・**差し戻し0件**。対象2行は gaps = [shield_to_hand_strigger_deny] のため reopen で外してから submit（reopen の出力は対象2件ちょうど）。正本判定: identity の canon_id 実測で2件とも自 ID、dm24ex3-or1 の aliases_for は4件で partial の記録と一致（記録だけで決めたのではない）。提出前照合: 対象 id・alias は real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / converted.yaml のいずれにも無し（proto.yaml のヒットは第318弾プロト T975 / T977 の text 内参照のみ）。converted 10,258→**10,260** / rejects 2,059→**2,057**、重なり0・漏れ0。shield_to_hand_strigger_deny はファミリーがこの2件だけだったため完全解消。pilot318 cards を登録形に書換、round353 cards を新設（登録カード自身の実挙動: 形A1＝シンカパワーで手札に加えた T960 は宣言されず印が付きシールド枚数は不変／形A2＝攻撃誘発の束分割で T001 は場へ・T960 は手札へ、宣言なし＋印）。テスト13 passed（round353 cards 3＋pilot318 cards 登録形 2＋data_audit 8）＋第318弾本体6 passed（別 invocation）。回答は answers/round353.yaml に保存。次の番号: パイロット319 / ラウンド354 / プロト T979。

## 第319弾 「攻撃の後、このクリーチャーを破壊する」（destroy_self_after_attacking）— ドリフト（第315弾の delayed 形）

センサス（rejects 2,057件を取り直し）: pure 1,908件 / multi 131件 / 空 gaps 18件（全て第312〜315弾の監査で別ブロッカー確認済み）。pure の大半は範囲外（gr_summon 147、aura 108＝未承認、hyperdimensional_zone 105、dragheart 45、psychic_filter 45、hyperdimensional_summon 41、out_of_game 23、duelist_link 20、outside_game 12、pandora_shift 4）か評価済み DEEP/重い/延期（第318弾の記録参照）。フィールド系と does_not_untap（2件）は第316・318弾の評価どおり再検討しても均一な小語彙の見込みが立たず却下。範囲内・未評価で最小の **destroy_self_after_attacking（純粋2件）** を選定した。

対象は dm22rp1-038 レター＝ジェンゲガー / dm22rp2x-061 ディッシュ＝ウィッシュ。両行とも partial は骨格（キーワードのみ、abilities 無し）で、未解決は自壊条項のみ。機構は第315弾 dmex12-s19 の登録形そのもの — 追加語彙なしのドリフト:

- **形A（dm22rp1-038）**: 攻撃誘発 {event: attack, subject: self} → delayed_trigger {when: {event: attack_end, subject: self}, duration: during_attack, effect: [destroy {ref: self}]}。
- **形B（dm22rp2x-061）**: 形A ＋ ブロック誘発 {event: block, subject: self} → delayed_trigger {when: {event: attack_end, **target: self**}, duration: during_attack, effect: [destroy {ref: self}]}。attack_end レコードの target は攻撃対象（ブロックしたクリーチャー）で、target: self の照合は dm13-040（バイバイ・アメーバ）の登録先例がある。遅延誘発は _collect_triggers の delayed 走査で通常誘発と同じ _match_when を使うため target 照合もそのまま効く。

- **発見（変換済み側の死に形）**: 同じ条項の変換済み9件（dm26-055 / dmex12-094 / dmrp05-074 / dmex14-075 / dmpcd01-r14 / dmpcd03-b11 / dmr06-043 / dmrp08-077 / dmsd06-015）が使う旧近似形 delayed_trigger {when: {event: turn_end}, duration: during_attack} は**発火しない**。during_attack の遅延誘発・継続的効果は攻撃タスク完了時（combat の 510.2 の _expire("during_attack")）に除去され、turn_end まで残らない。dmex12-094 の notes 自身が「専用イベントが無いためターンの終わりで近似した」と認める形で、attack_end イベント追加後に置き換わっていない。dmex12-094 で実挙動プローブ済み（攻撃→2ターン進めても場に残る）。本弾の対照プロト T981 でも固定した。**変換済み9件の修繕は本弾の範囲外**（第299弾の count: 0 発見と同じく別修繕ステージ送り。修繕形は本弾の形A/B への when 差し替え）。
- プロト T979（形A）/ T980（形B）/ T981（旧近似形の対照）。次の空きは **T982**。
- tests/test_vocab_pilot319.py: **7 passed** — parse＋確立形一致（parse 時に destroy マクロが move に展開されるため展開形で比較）、形A（攻撃→攻撃終了時に破壊され次のターン冒頭で既に墓地／攻撃しなければ残る）、形B（攻撃し相手ブロッカーとのバトルに勝っても自壊／ブロックしバトルに勝っても自壊）、対照（旧近似形は攻撃しても発火せず残り続ける）。
- tests/test_vocab_pilot319_cards.py: **2 passed** — 対象2行の残留（gaps・unsupported ともに当該ギャップのみ・未登録・ファミリーはこの2件だけ）、提出形（partial の骨格＋確立形の誘発）の parse と対応プロトとの abilities 完全一致。
- 回帰: 第315・310・290・318弾本体＋test_rules＋test_rust_schema_sync＋test_data_audit **83 passed**。エンジン・defs・スキーマ変更なし（_mana_choices 未接触）。既知の事前失敗2件（第274弾・第31弾）は範囲外で未接触。
- 収支: converted **10,260（不変）** / rejects **2,057（不変）**。変更は proto.yaml（T979〜T981 純追加）・テスト2件・docs のみ。

### ラウンド354側の注意

- 対象は dm22rp1-038 / dm22rp2x-061 の2件。提出形は tests/test_vocab_pilot319_cards.py の FORMS 相当: partial の骨格に形A（061 は形B のブロック誘発も）を足し、unsupported を外したもの。**旧近似形（when: turn_end）は絶対に使わないこと**（発火しない）。
- dm22rp1-038 の残りの条項「自分のターンの終わりに、自分の山札の上から１枚目を墓地に置く。それがアビスなら、カードを１枚引く」は本弾の対象外で、ラウンドで構築・検証すること。見込み: turn_end 誘発 {player: you} ＋ mill を as で束縛し、置いたカードの race を判定する形は変換済みに先例がある（「2枚ともアビスなら」を ref: milled の race 枚数で判定した登録例）。正確に表せなければ 038 だけ精緻化したギャップ名で差し戻し、061 のみ登録してよい。dm22rp2x-061 の他の条項はキーワード（s_trigger / blocker）のみ。
- 対象2行とも gaps = [destroy_self_after_attacking] のため reopen で外れる見込み（ファミリーはこの2件だけなので出力は2件のはずだが、必ず数えること）。
- 正本判定は identity の実データで submit 前に行うこと。partial の aliases 記録（038: promoy21-052、061: dm22rp2-061 / dm22rp2-20a / dm22rp2x-20a / promoy21-069）だけで決めず、id・alias を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること。登録後は abilities・キーワードをテキストと照合すること（submit は partial の abilities と回答を連結する。第313弾の教訓）。
- 次の番号: パイロット320 / ラウンド354 / プロト T982。

### ラウンド354（第319弾の再変換）

**新規登録2件**（dm22rp1-038 レター＝ジェンゲガー＝形A〔攻撃誘発→delayed_trigger {attack_end, subject: self}〕＋本ラウンドで構築したターン終了条項 / dm22rp2x-061 ディッシュ＝ウィッシュ＝形B〔形A＋ブロック誘発→delayed_trigger {attack_end, target: self}〕。いずれも partial の骨格＋確立形、unsupported 除去。登録形は確立形と完全一致で abilities は2件ちょうど、keywords は 038 が [blocker]・061 が [s_trigger, blocker] のまま、連結混入なし）・**alias 畳み込み0件**（038 の promoy21-052、061 の4件は登録エントリの source.aliases への記録のみで、alias 側の reject 行は元々無し）・**stale クリーンアップ0件**・**差し戻し0件**。038 の残りの条項「自分のターンの終わりに、自分の山札の上から1枚目を墓地に置く。それがアビスなら、カードを1枚引く」はラウンドで構築: turn_end 誘発 {player: you} ＋ move {from_top: 1, count: all, as: milled} で墓地に置き、if {cmp: [{count: {ref: milled, filter: {race_has: アビス}}}, ==, 1]} で draw 1（判定は dm23rp2x-037 の「2枚ともアビスなら」の登録先例と同形）。提出前に提出形を一時 defn として注入し、全アビス山札（手札+1・山札-2・墓地1枚）／全非アビス山札（山札-1のみ）の両方向で実挙動を検証済み。対象2行は gaps = [destroy_self_after_attacking] のため reopen で外してから submit（reopen の出力は対象2件ちょうど）。正本判定: identity の canon_id 実測で2件とも自 ID、aliases_for も partial の記録と一致。提出前照合: 対象 id と全 alias は real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / converted.yaml のいずれにも無し（proto.yaml のヒットは T979/T980 の本文内参照のみ）。converted 10,260→**10,262** / rejects 2,057→**2,055**、重なり0・漏れ0。destroy_self_after_attacking はファミリーがこの2件だけだったため完全解消。pilot319 cards を登録形に書換、round354 cards を新設（登録カード自身の実挙動: 038 攻撃で自壊／061 攻撃で自壊／061 ブロックでバトル勝利後も自壊／038 ターン終了条項の両方向）。テスト16 passed（round354 cards 6＋pilot319 cards 登録形 2＋data_audit 8）＋第319弾本体7 passed（別 invocation）。なお登録形バッチの初回実行で test_data_audit の top-level-field 検査が1件失敗したが、同バッチ再実行と単独実行の両方で合格し再現しない（変換データ側の変更なし）。回答は answers/round354.yaml に保存。次の番号: パイロット320 / ラウンド355 / プロト T982。変換済み9件の旧近似形（when: turn_end ＋ during_attack）の修繕ステージが別途残る。

## 修繕ステージ: delayed_trigger {when: turn_end, duration: during_attack} 死に形の是正

第319弾の発見（変換済み9件の旧近似形は発火しない）を受け、パイロット番号を消費しない独立の修繕ステージとして棚卸しと是正を実施した。**実測センサス（yaml.compose で converted 全件走査）: 当該パターンは17箇所・16カード**あり、第319弾の「9件」は内訳が不正確だった（訂正する）。9件のうち dm26-055 は duration が end_of_turn の別形（後述）で、残り8件に未報告の8カード（dmr05-073 / dmr16s-003 / dmr17-004 / dmrp01-009 / dmrp01-075 / dmrp03-043 / dmrp04s-055 / dmsd05-005）が加わる。during_attack の遅延誘発は攻撃タスク完了時（combat の 510.2 の _expire）で除去され turn_end まで残らないため、17箇所すべて発火しない。

- **形A（攻撃誘発 → delayed {attack_end, subject: self}、第319弾）に是正した12件**: dmex12-094 / dmrp05-074 / dmex14-075 / dmpcd01-r14 / dmr16s-003 / dmr17-004 / dmrp01-009 / dmrp01-075 / dmrp04s-055 / dmsd05-005 / dmsd06-015 / dm26-055。効果側（破壊・マナ置き・アンタップ・任意タップ＋アンタップ・任意捨て＋ドロー）は現行のまま。dmr16s-003 の「そうした場合」の連動、dmr17-004 のコスト判定の近似は従来どおり残る（各カードの notes に明記）。
- **形B（ブロック誘発 → delayed {attack_end, target: self}）に是正した2件**: dmr05-073（バトルの後にアンタップ）/ dmr06-043（バトルの後に破壊）。
- **両形の1件**: dmrp08-077（攻撃側＝形A、ブロック側＝形B。delayed 2箇所とも是正）。
- **監視形の1件**: dmrp03-043（自分の他のクリーチャーの攻撃で誘発し、その攻撃の終わりに自身を破壊）。delayed の when は素の {attack_end}（対象の攻撃は外側の誘発が束縛する。dmrp03-015・dmrp02-073 の登録先例と同形）。
- **dmpcd01-r14 は追加是正**: 本文が「相手プレイヤーを攻撃する時」のため、攻撃誘発の when に target: player を追加した（{attack, subject: self, target: player} は登録先例あり）。従来形はクリーチャーへの攻撃でも（発火すれば）破壊する過剰形だった。
- **dmpcd03-b11 は形が違う**: 本文は「バトルする時、バトルの後」で、このクリーチャーは攻撃できない。旧形は攻撃誘発で代表させていたため二重に発火不能だった。第211弾の battle_end 誘発 {when: {event: battle_end, subject: self}} → destroy self に置き換えた（delayed_trigger 自体を除去）。
- **dm26-055 は同系の別形**: delayed {when: turn_end, duration: end_of_turn} は発火はするがターンの終わりで、「その攻撃の後」とタイミングがずれていた。形A（when attack_end / subject self、duration during_attack）に是正した。
- **類似パターンの棚卸し（是正対象外）**: dm25sp1-004 も attack 誘発 → delayed {turn_end, end_of_turn} で「攻撃の終わりに」をターンの終わりで近似する同系の別形だが、本ステージの対象範囲（第319弾の報告分＋実測の during_attack 群）には含めず、別ステージ送りとして記録する。他の {turn_end, end_of_turn} 群10件は本文がいずれも「このターンの終わりに」で正しい形のため無変更。delayed {when: break / battle_win, duration: during_attack} 群（34箇所）は攻撃中に起きるイベントを待つ正しい形のため無変更。delayed {when: turn_end} 全体は214箇所あり、大半は duration 無し（＝通常のターン終了時遅延）で正常。
- **編集方法**: yaml.compose の行マークで対象ノードを特定し、該当 ability ブロックと各カードの notes だけを差し替える外科的編集（diff は対象17カード分のみ、ヘッダーコメント保持）。notes は旧形の説明を修繕内容に書き換えた（dmr16s-003 / dmr17-004 は残る近似の注記を併記）。
- **実挙動証明**: tests/test_repair_delayed_attack_end.py（11件）を新設。修繕前は11件すべて失敗（形A破壊・マナ置き・アンタップ／形B破壊・アンタップ／両形／監視形／battle_end／dm26-055 のタイミング／dmpcd01-r14 の限定、の各代表サンプルで不発・遅延を実測）。タイミング判別には同一攻撃ステップ内の2体目の攻撃決定で止めるチェックポイントを使った（このエンジンのターン構造は攻撃後に同一ターンへ戻るメイン決定が無いため）。修繕後は **11 passed**。
- **回帰**: 第319・315・211弾本体＋test_rules＋test_rust_schema_sync **58 passed**（別 invocation）。data_audit＋第319弾 cards＋ラウンド354 cards＋第211弾 cards＋旧修繕テスト群は 33 passed / 3 failed。3 failed はいずれも旧修繕テスト（test_repair_count0_upto / test_repair_opcount0 / test_repair_break_selfshield）の disposition が当時の件数（rejects 2,096）を固定している stale な簿記で、本ステージ前（HEAD 5fc6f30）でも同一に失敗することを stash で確認済みの既存問題（本ステージは件数を動かしていない）。
- **収支: converted 10,262 / rejects 2,055（不変）**。変更は converted.yaml（対象17カードの ability ブロック＋notes）・テスト1件・docs のみ。次の番号: パイロット320 / ラウンド355 / プロト T982。

## 第320弾 「ブロックした時／ブロックされた時」（trigger_when_blocked）— ドリフト（block レコードの subject / attacker 照合）

センサス（rejects 2,055件を取り直し）: pure 1,906件 / multi 131件 / 空 gaps 18件（全て第312〜315弾の監査で別ブロッカー確認済み）。pure の大半は範囲外（gr_summon 147、aura 108＝未承認、hyperdimensional_zone 105、dragheart 45、psychic_filter 45、hyperdimensional_summon 41、out_of_game 23、duelist_link 20、outside_game 12、pandora_shift 4）か評価済み DEEP・重い・延期。範囲内・未評価の候補を精査して却下した: negate_effects / effect_negation（各3件。「攻撃できない効果・能力はすべて無効」は negate_cannot_attack 系の無効化機構が要り均一な小語彙にならない）、opponent_choice_branch（3件とも相手の選択の構造が相異なる）、shield_grant（3件とも付与の発生源・持続が相異なる）、cost_matching_selection（3件。コスト参照フィルタに加え件数連動・相手側一括処理が混ざり均一でない）、per_civilization_selection（3件。文明別 distinct 選択の機構が要る）、flying（2件。攻撃／ブロック制限のエンジン作業＋他節が重い）、delayed_return（2件とも他節が重い）、draw_up_to（2件。ヨミの G・リンク、H・アルカディアスのハイパー化が併記）、look_reorder（dmrp06-071 の partial の実ブロッカーは self_return でギャップ名とずれる。dmc55-071 単独では均一なファミリーにならない）。フィールド系と does_not_untap（2件）は第316・318弾の評価どおり再検討しても均一な小語彙の見込みが立たず却下。範囲内・未評価で最小の **trigger_when_blocked（純粋2件、multi-gap 行にも現れない）** を選定した。

**結論: ドリフト（追加語彙なし）。** block レコードは combat が {ev: block, subject: ブロッカーの ref, attacker: 攻撃クリーチャーの ref, controller: 防御側} で発行し、events._match_when は subject / attacker の両キーを既に扱う（attacker 節のコメントに「self なら『このクリーチャーがブロックされた時』」と明記）。selector の event.attacker 参照も既存（selectors の event.<キー> 群）。

- **形A（dm26rp1-074 ノーガルディ・ネギオ＆ガルダンディ・ナスオ、「ブロックされた時」）**: trigger {when: {event: block, attacker: self}, effect: [{op: break, player: opp, count: 2}]}。when の形は第280弾（dm06-101 / dm06-032 の cancel_attack 形、プロト T793 / T794）の登録先例そのもの。ブレイクはブロック宣言時（バトルの前）に解決し、バトル自体は通常どおり行われることを実挙動で固定した（3000 同士の相打ち＋シールド5→3）。
- **形B（dm26ex2-068 ワダウザノミコト、「ブロックした時」）**: trigger {when: {event: block, subject: self}, effect: [move {select: {ref: self}, to: hand, reason: return}, move {select: {ref: event.attacker}, to: hand, reason: return}]}。subject＝ブロッカーは dm20-045 の登録先例（その source.notes に「block イベントの subject はブロッカー自身」と明記）。両者とも持ち主の手札に戻る。
- **形Bの併記条項（離脱時）も既存部品で構成できた**: 「離れた時、自分の山札の上から4枚を見る。その中から1枚を手札に加え、残りを好きな順序で山札の上か下に置く」= trigger {when: {event: move, from: bz, subject: self}, effect: [choose {select: {zone: deck, owner: you, from_top: 4, look: true, count: all}, as: pile}（第311弾形）→ choose {select: {ref: pile, count: 1}, as: pick} → move {select: {ref: pick, count: all}, to: hand, reason: draw} → repeat {times: {count: {ref: pile, zone: deck}}, body: [choose {select: {ref: pile, zone: deck, count: 1}, as: c}, modal [move {ref: c} to deck position: top / position: bottom]]]}。1枚ごとの上／下配置は dm24ex1-054 の登録形（repeat ＋ choose ＋ modal）の山札内版。置いたカードは gen 切れで以降の choose {ref: pile} から落ちる（第287弾の残り処理と同じ原理）。ブロックで自ら手札に戻った場合も離脱条項が連鎖すること、攻撃してブロックされバトルで破壊された場合は第1誘発が発火せず離脱条項だけが発火することを実挙動で固定した。

両行とも partial は骨格（abilities 無し）。dm26rp1-074 の partial の text は「このクリーチャーがブロックされた時」だけに切れている（reject 行の text が公式全文）。

- プロト: T982（形B、dm26ex2-068 型）/ T983（形A、dm26rp1-074 型）。次の空きは T984。
- テスト: 本体 **7 passed**（parse＋FORM とプロトの abilities 完全一致／形A: ブロックされるとバトルの前に2ブレイクし相打ちになる・別のクリーチャーがブロックされても誘発しない／形B: ブロックで両方手札へ＋離脱の連鎖（束[1]を手札、束[0]を下、束[2]・束[3]を上。解決後の最初の決定は自ターン開始ドローを済ませた後になるため一番上の束[3] はドローで手札へ）・破壊されても離脱だけ発火し残り全て下へ・別のクリーチャーがブロックしても誘発しない）＋ cards **2 passed**（対象2行の残留・ファミリー単独・提出形が partial の素性を保ち parse とプロト一致）。回帰 **101 passed**（第320・319・280・311・287弾本体＋test_rules＋rust_schema_sync＋data_audit）。既知の事前失敗2件（第274弾・第31弾）は未接触。
- テスト中の発見: (1) ブレイクするシールドの選択は攻撃側の choose_shields 決定として現れる。(2) 残り1枚の choose は自動決定され決定として現れないため、modal の対応づけは「未消費の最後の1件」で行う必要がある（第287・314弾の教訓の再確認）。(3) ブロックで戻った側の離脱解決後、相手ターン内の pass のみの決定は自動で読み飛ばされ、次の観測点は自ターン開始ドローの後になる。
- 収支: converted **10,262（不変）** / rejects **2,055（不変）**。変更は proto.yaml（T982・T983 純追加）・テスト2件・docs のみ。

### ラウンド355側の注意

- 対象は dm26ex2-068 / dm26rp1-074 の2件。提出形は tests/test_vocab_pilot320_cards.py の _form 相当: partial ＋ abilities（068 は [ブロック誘発, 離脱誘発] の2件、074 は [ブロックされ誘発] の1件）、unsupported 除去。**dm26rp1-074 は text を reject 行の公式全文に差し替えること**（partial の text は切れている）。dm26ex2-068 の text は partial のままで全文。
- 対象2行とも gaps = [trigger_when_blocked] のため reopen で外れる見込み（ファミリーはこの2件だけなので出力は2件のはずだが、必ず数えること）。
- 正本判定は identity の実データで submit 前に行い、id・alias を real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml と照合すること（両行とも partial に aliases 記録は無い）。
- 登録後は abilities が 068 は2件・074 は1件ちょうどで FORM と完全一致することを本文と照合すること（submit の連結・merge_split 混入の確認。068 の keywords は [s_trigger, blocker] のまま）。
- 次の番号: パイロット321 / ラウンド355 / プロト T984。

### ラウンド355（第320弾の再変換）

**新規登録2件**（dm26ex2-068 ワダウザノミコト＝形B〔trigger {event: block, subject: self} → move {ref: self} ＋ move {ref: event.attacker} を持ち主の手札へ〕＋離脱条項〔choose {from_top: 4, look: true, count: all} as pile → 1枚を手札 → repeat＋choose＋modal で残りを山札の上か下へ〕 / dm26rp1-074 ノーガルディ・ネギオ＆ガルダンディ・ナスオ＝形A〔trigger {event: block, attacker: self} → break {player: opp, count: 2}〕。いずれも partial ＋第320弾の確立形、unsupported 除去。登録形は確立形と完全一致で abilities は 068 が2件・074 が1件ちょうど、068 の keywords は [s_trigger, blocker] のまま、連結混入なし）・**alias 畳み込み0件**（identity の canon_id 実測で2件とも自 ID、aliases_for は空）・**stale クリーンアップ0件**・**差し戻し0件**。dm26rp1-074 の text は partial が「このクリーチャーがブロックされた時」だけに切れていたため reject 行の公式全文に差し替えた（dm26ex2-068 の text は partial のまま全文）。対象2行は gaps = [trigger_when_blocked] のため reopen で外してから submit（reopen の出力は対象2件ちょうど）。提出前照合: 対象 id は real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / converted.yaml のいずれにも無し（proto.yaml のヒットは T982/T983 の本文内参照のみ）。converted 10,262→**10,264** / rejects 2,055→**2,053**、重なり0・漏れ0。trigger_when_blocked はファミリーがこの2件だけだったため完全解消。pilot320 cards を登録形に書換、round355 cards を新設（登録カード自身の実挙動: 074 ブロックされるとバトルの前に2ブレイクし相打ち・別のクリーチャーがブロックされても誘発しない／068 ブロックで両方手札へ＋離脱の連鎖・破壊されても離脱だけ発火）。テスト15 passed（round355 cards 5＋pilot320 cards 登録形 2＋data_audit 8）＋第320弾本体7 passed（別 invocation）。回答は answers/round355.yaml に保存。次の番号: パイロット321 / ラウンド356 / プロト T984。

## 第321弾 「相手プレイヤーを攻撃してブロックされなかった時」（trigger_when_unblocked）— ドリフト（attack_end の blocked: false 照合）

センサス（rejects 2,053件を取り直し）: pure 1,904件 / multi 131件 / 空 gaps 18件（全て第312〜315弾の監査で別ブロッカー確認済み）。pure の大半は範囲外（gr_summon 147、aura 108＝未承認、hyperdimensional_zone 105、dragheart 45、psychic_filter 45、hyperdimensional_summon 41、out_of_game 23、duelist_link 20、outside_game 12＝2026-11-06 ユーザー指示で対象外化済み、pandora_shift 4）か評価済み DEEP/重い/延期（第318〜320弾の記録参照）。（訂正 2026-11-20: 当初「pure 1,906件 / hyperdimensional_zone 112 / psychic_filter 46 / hyperdimensional_summon 42」と書いたのは第320弾時点の数え方の写し間違いで、合計が 2,055件になり 2,053件と合わなかった。正しくは pure 1,904件。数え方は全行を pure/multi/空に分け、out_of_scope 行も gaps に従って数える。）フィールド系と does_not_untap（2件）は第316・318弾の評価どおり却下、flying / delayed_return / draw_up_to / look_reorder は第319・320弾で却下済み。範囲内・未評価で最小の **trigger_when_unblocked（純粋2件、multi-gap 行にも現れない）** を選定した。

対象は dm19-050 大鉄漢シルバスターズ / dm19-069 食いしん坊チャロック。両行とも partial は骨格（abilities 無し）で、未解決は「このクリーチャーが相手プレイヤーを攻撃してブロックされなかった時」の1節のみ。partial の notes は「ダイナモ能力の仕組みを表す語彙が無い」としているが、ダイナモは第76弾で keywords.yaml 定義済み（keywords: [dynamo]）。

**結論: ドリフト（追加語彙なし）。** 「ブロックされなかった時」は attack_end レコードの blocked: false 照合で書ける（第175弾 T385 / 第219弾で確立）。登録先例は同じダイナモの dm20-016 風使いのシャイアンで、when は {event: attack_end, subject: self, target: player, blocked: false} そのもの:

- **形A（dm19-050）**: trigger {when 上記} → may [draw {count: 1}]。
- **形B（dm19-069）**: trigger {when 上記} → may [move {select: {zone: deck, owner: you, from_top: 1}, to: mana, reason: put}]。

- プロト T984（形A）/ T985（形B）。次の空きは **T986**。
- tests/test_vocab_pilot321.py: **6 passed** — parse＋確立形一致（keywords [dynamo] を含む）、形A（ブロックされずに攻撃→攻撃の終わりに1枚引く／辞退できる／ブロックされると引かない判別）、形B（ブロックされずに攻撃→山札の上1枚がマナへ・山札-1／ブロックされると置かない判別）。
- tests/test_vocab_pilot321_cards.py: **2 passed** — 対象2行の残留（gaps・unsupported ともに当該ギャップのみ・未登録・ファミリーはこの2件だけ）、提出形（partial の素性＋keywords [dynamo]＋確立形）の parse と対応プロトとの abilities 完全一致。
- 収支: converted **10,264（不変）** / rejects **2,053（不変）**。変更は proto.yaml（T984〜T985 純追加）・テスト2件・docs のみ。エンジン・defs・スキーマ変更なし。

### ラウンド356側の注意

- 対象は dm19-050 / dm19-069 の2件。提出形は tests/test_vocab_pilot321_cards.py の FORMS 相当: partial ＋ keywords [dynamo] ＋ abilities（各1件）、unsupported 除去。text は partial の全文を使うが、ダイナモ説明と本条項の区切りが空白になっている箇所は reject 行の公式全文どおり改行に直すこと。
- 対象2行とも gaps = [trigger_when_unblocked] のため reopen で外れる見込み（ファミリーはこの2件だけなので出力は2件のはずだが、必ず数えること）。
- 正本判定は提出前に行うこと。両行とも partial に aliases 記録は無く、id は real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml のいずれにも無いことを確認済み（2026-11-20）。
- 登録後は abilities が各1件ちょうどで FORM と完全一致すること、keywords が [dynamo] であることを本文と照合すること。
- 次の番号: パイロット322 / ラウンド357 / プロト T986。

### ラウンド356（第321弾の再変換）

**新規登録2件**（dm19-050 大鉄漢シルバスターズ＝形A〔trigger {event: attack_end, subject: self, target: player, blocked: false} → may [draw 1]〕 / dm19-069 食いしん坊チャロック＝形B〔同じ when → may [move {zone: deck, from_top: 1} to mana, reason: put]〕。いずれも partial ＋ keywords [dynamo] ＋第321弾の確立形、unsupported 除去。登録形は確立形と完全一致で abilities は各1件ちょうど、keywords は両件とも [dynamo]、連結混入なし）・**alias 畳み込み0件**（両行とも partial に aliases 記録は無く、提出前に id が real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml のいずれにも無いことを確認済み）・**stale クリーンアップ0件**・**差し戻し0件**。text は partial の全文で、ダイナモ説明と本条項の区切りが空白だった箇所は reject 行の公式全文どおり改行に直した。対象2行は gaps = [trigger_when_unblocked] のため reopen で外してから submit（reopen の出力は対象2件ちょうど）。converted 10,264→**10,266** / rejects 2,053→**2,051**、重なり0・漏れ0。trigger_when_unblocked はファミリーがこの2件だけだったため完全解消。pilot321 cards を登録形に書換、round356 cards を新設（登録カード自身の実挙動: 050 ブロックされずに攻撃すると1枚引く・ブロックされると引かない／069 ブロックされずに攻撃すると山札の上1枚がマナへ・ブロックされると置かない）。テスト21 passed（round356 cards 5＋pilot321 cards 登録形 2＋pilot321 本体 6＋data_audit 8）。回答は answers/round356.yaml に保存。次の番号: パイロット322 / ラウンド357 / プロト T986。

## 第322弾 「攻撃してブロックされなかった時、このターンにダイナモを使うためにタップした自分のダイナモ１体につき１枚、シールドを余分にブレイクする」（trigger_when_unblocked_and_extra_breaks_per_dynamo_tap）— エンジン拡張（新 turn_count kind dynamo_tap）

センサス（rejects 2,051件を取り直し）: pure 1,902件 / multi 131件 / 空 gaps 18件（全て第312〜315弾の監査で別ブロッカー確認済み。数え方は全行を pure/multi/空に分け、out_of_scope 行も gaps に従って数える。第321弾の記録は当初 pure 1,906件と写し間違えていたため訂正済み）。pure の大半は範囲外（gr_summon 147、aura 108＝未承認、hyperdimensional_zone 105、dragheart 45、psychic_filter 45、hyperdimensional_summon 41、out_of_game 23、duelist_link 20、outside_game 12＝2026-11-06 ユーザー指示で対象外化済み、pandora_shift 4）か評価済み DEEP/重い/延期（第318〜321弾の記録参照）。delayed_return / draw_up_to / look_reorder / flying / does_not_untap は新しい証拠がない限り再提案しない（第320・321弾で却下済み）。範囲内・未評価で最小の **trigger_when_unblocked_and_extra_breaks_per_dynamo_tap（純粋2件、multi-gap 行にも現れない）** を選定した。

対象2枚:
- dm19-003 電脳鉄人センジュオー（水・5・3000・グレートメカオー/ダイナモ）: partial あり（骨格。abilities 無し）。未解決は「攻撃してブロックされなかった時、このターンに「ダイナモ」能力を使うためにタップした自分のダイナモ１体につき１枚、シールドを余分にブレイクする」の1節のみ。partial の注記「ダイナモの語彙が無い」は stale（dynamo は第76弾で定義済み）。
- dm23ex2-045: rejects 行は partial 空・name None・text はクリーチャー面のみ。by_product（23ex2.jsonl）で原文照合済み: ツインパクトで、クリーチャー面は dm19-003 と同名・同能力（「１つ、シールドを追加でブレイクする」と読む）、呪文面 センジュ・チューンは S・トリガーで「自分の手札の数と同じ枚数のカードを引き、その後、こうして引いた枚数と同じ数、手札を捨てる」。submit は by_product 行（faces 付き）を正本として読むため、faces 形式で提出する。なお rule_convert.split は faces 付き行には None を返すため、merge_split による text の上書きは起きない（rejects 行だけで split するとクリーチャー面だけが返るが、submit の正本は by_product 行）。

第321弾の when {event: attack_end, subject: self, target: player, blocked: false} の直接拡張。追加ブレイクの数は「このターンにダイナモを使うためにタップした自分のダイナモの体数」で、既存の履歴カウンタでは表せない（hist:tap は攻撃・ブロック等のあらゆるタップを数える）。エンジン拡張: 新しい turn_count kind `dynamo_tap`（defs.py の TURN_COUNT_KINDS に追加）。op_modify が add_of（ダイナモだけが使う mod。keywords.yaml の activate 経路と battle_start トリガー経路の両方とも op_modify 経由）を適用した時、発生源の cid を turn_counters["dynamo_tap:<player>"] に記録する（重複は数えない。タップはコスト／トリガー効果として先に済み、付与が使用の完了点）。_turn_count でリストの体数を返す。形: trigger {event: attack_end, subject: self, target: player, blocked: false} → [{op: break, player: opp, count: {turn_count: {kind: dynamo_tap, owner: you}}}]（通常の1ブレイクは攻撃中に済んでおり、ここで余分に N 枚割る。N=0 でも余分のブレイク決定（choose_shields min 0）が出るが何も割らない）。注意: プレイヤーへの攻撃ではバトルが発生しないため、ダイナモの battle_start トリガーはセンジュオー自身の攻撃では誘発しない。ダイナモの使用は「攻撃できる時」の activate か、他のクリーチャーのバトル開始時に起きる。

副次的なエンジン修正（呪文面のため）: op_set_var は値が式（{count: ...} 等）の時は評価して束縛する。従来は辞書のまま束縛され {var:} の読みが len(辞書)＝1 になっていた（プローブで確認: 手札3枚で set_var した {count: {zone: hand}} が draw 1枚になっていた。dmx12b-044 / dmrp09-020 / dmx07-020 等の既存6件も同じ誤りで、この修正で正しい枚数になる）。リスト・数値・真偽値は従来どおり。呪文面の形: [set_var hand_n {count: {zone: hand, owner: you}}, draw {var: hand_n}, discard {zone: hand, owner: you, count: {var: hand_n}}]（discard は parse 時に move（to: graveyard, reason: discard）へ展開。「引いた枚数」＝唱えた時点の手札枚数と同数）。

既知の不具合（第322弾の変更とは無関係。変更前のエンジンでも再現する。判断は後回し）: 同じバトル開始時にダイナモ2体がダイナモを使うと、chars キャッシュの stale 表明（`chars cache stale: cid=0`）で落ちる。T984/T985/R069 のみの再現（T004 を攻撃し、2つの yes_no に両方 yes）で確認済み。ダイナモデッキでは起きうる組み合わせのため、別途のエンジン課題として記録する。試験ではドナー1体だけの形で固定した。

proto T986（dm19-003 型。keywords [dynamo, unblockable]）/ T987（センジュ・チューン型。keywords [s_trigger]）。テスト9件通過（pilot322 本体 7＋pilot322 cards 提出前 2）。次の番号: パイロット323 / ラウンド358 / プロト T988。

### ラウンド357（第322弾の再変換）

**新規登録2件**（dm19-003 電脳鉄人センジュオー＝trigger {event: attack_end, subject: self, target: player, blocked: false} → [{op: break, player: opp, count: {turn_count: {kind: dynamo_tap, owner: you}}}] / dm23ex2-045 ツインパクト＝クリーチャー面は dm19-003 と同形、呪文面 センジュ・チューンは [set_var hand_n {count: {zone: hand, owner: you}}, draw {var: hand_n}, discard {var: hand_n}]。dm19-003 は partial ＋ keywords [dynamo, unblockable] ＋確立形、unsupported 除去。dm23ex2-045 は faces 形式（top text は convert_twin の形「面名: 面文 ／ 面名: 面文」、top レベルに keywords/abilities は無し）。登録形は確立形と完全一致で連結混入なし）・**alias 畳み込み0件**（両 id とも提出前に real.yaml / real_akashic.yaml / real_vocab.yaml / real_zone.yaml / proto.yaml / converted.yaml のいずれにも無く、aliases 記録も無し）・**stale クリーンアップ0件**・**差し戻し0件**。対象2行は gaps = [trigger_when_unblocked_and_extra_breaks_per_dynamo_tap] のため reopen で外してから submit（reopen は dm19-003 の1件だけが外れた。dm23ex2-045 の rejects 行には reason が無く reopen の条件に合わなかったためで、submit で rejects から外れた）。converted 10,266→**10,268** / rejects 2,051→**2,049**、重なり0・漏れ0。trigger_when_unblocked_and_extra_breaks_per_dynamo_tap はファミリーがこの2件だけだったため完全解消。pilot322 cards を登録形に書換、round357 cards を新設（登録カード自身の実挙動: 003 ダイナモ未使用なら1枚・dm19-050 の activate で1体使うと2枚／045 クリーチャー面も同じく2枚／045 呪文面は手札2枚の時に2枚引いて2枚捨てる。ツインパクトの呪文面は main 決定で play:dm23ex2-045:1（face 1）で唱える）。テスト22 passed（round357 cards 5＋pilot322 cards 登録形 2＋pilot322 本体 7＋data_audit 8）。回答は answers/round357.yaml に保存。次の番号: パイロット323 / ラウンド358 / プロト T988。

### 語彙パイロット第323弾（unblocked_condition、ドリフト）

センサス（rejects 2,049件を取り直し）: pure 1,900件 / multi 131件 / 空 gaps 18件（全て第312〜315弾の監査で別ブロッカー確認済み。数え方は全行を pure/multi/空に分け、out_of_scope 行も gaps に従って数える）。pure の大半は範囲外（gr_summon 147、aura 108＝未承認、hyperdimensional_zone 105、dragheart 45、psychic_filter 45、hyperdimensional_summon 41、out_of_game 23、duelist_link 20、outside_game 12＝2026-11-06 ユーザー指示で対象外化済み、pandora_shift 4）か評価済み DEEP/重い/延期（第318〜322弾の記録参照）。4件組はすべて評価済み（victory_icon_filter、dokindam_gacha、cost_sum_of_revealed、climax_dorongo、shield_manipulation、spell_replay、summon_lock、opponent_chooses_deck_position、dynamic_name_reference_filter）。3件組も大半が評価済み DEEP／延期。delayed_return / draw_up_to / look_reorder / flying / does_not_untap は新しい証拠がない限り再提案しない（第320・321弾で却下済み）。範囲内・未評価で最小の純粋2件組を走査し、after_battle_trigger（2件の構造が不均一・partial 空）、attack_limit_once_per_turn（静的制限と時限呪文面で不均一）、cip_trigger_double（トリガー二重化はエンジン作業が重い）、s_trigger_suppression（抑制の条件が2件で異なる）、enters_tapped_optional（partial 空・他節が重い）、from_hand_trigger（2件の構造が不均一）を却下し、**unblocked_condition（純粋2件、multi-gap 行にも現れない）**を選定した。別途ドリフト候補として記録: breaks_equal_creature_count（dm24ex2-024 / dm26ex4-cho021、同名呪文の2印刷。「自分のクリーチャー１体はその数のシールドを追加でブレイクする」は breaks 付与の count 式で書ける見込み。「そのクリーチャーの攻撃中、相手は呪文を唱えられない」は partial に unsupported が無く既存語彙で表せる扱い）。

対象は dmx04-011 ケロディ二郎（水・コスト4・パワー2000・ゲル・フィッシュ/ハンター・マナ1）/ dmx09-049 誕生の祈（自然・コスト3・パワー2000・ビーストフォーク・マナ1）。両行とも partial は空で、by_product（x04.jsonl / x09.jsonl）で原文照合済み。両カードとも単一能力のクリーチャーで、全文が「このクリーチャーが相手プレイヤーを攻撃してブロックされなかった時」の1節だけ。

結論: ドリフト（追加語彙なし）。「ブロックされなかった時」は第321弾で確立した attack_end {subject: self, target: player, blocked: false} そのもので、ギャップ名の違いだけが残っていた。効果側も既存の形。形A（dmx04-011）: trigger {event: attack_end, subject: self, target: player, blocked: false} → may [move {zone: bz, owner: any, filter: {types: [creature]}, count: 1} to hand, reason: return]（手札に戻すは既存の return 形）。形B（dmx09-049）: 同じ when → may [choose {zone: deck, owner: you, look: true, filter: {types: [creature]}, count: 1} as t; move {ref: t, count: all} to hand, reason: draw; shuffle]（山札を見てクリーチャーを手札に加えるはアポロニア・ドラゴンの先例と同形。look: true が相手に見せる部分を担う）。

proto T988（dmx04-011 型）/ T989（dmx09-049 型）。テスト9件通過（pilot323 本体 7: 形A＝ブロックされなければ相手クリーチャーを手札に戻す・辞退可・ブロック時は発火しない、形B＝ブロックされなければ山札からクリーチャーを手札に加える・辞退可・ブロック時は発火しない、＋pilot323 cards 提出前 2）。次の番号: パイロット324 / ラウンド359 / プロト T990。

### ラウンド358（第323弾の再変換）

**新規登録2件**（dmx04-011 ケロディ二郎＝trigger {event: attack_end, subject: self, target: player, blocked: false} → may [move {zone: bz, owner: any, filter: {types: [creature]}, count: 1} to hand, reason: return] / dmx09-049 誕生の祈＝同じ when → may [choose {zone: deck, owner: you, look: true, filter: {types: [creature]}, count: 1} as t; move {ref: t, count: all} to hand, reason: draw; shuffle]。dmx04-011 は水・コスト4・パワー2000・ゲル・フィッシュ/ハンター・マナ1、dmx09-049 は自然・コスト3・パワー2000・ビーストフォーク・マナ1。両行とも partial は空で、by_product で原文照合済み。登録形は確立形と完全一致で連結混入なし）・**alias 畳み込み0件**・**stale クリーンアップ0件**・**差し戻し0件**。対象2行は gaps = [unblocked_condition] のため reopen で外してから submit（reopen は2件とも外れた）。converted 10,268→**10,270** / rejects 2,049→**2,047**、重なり0・漏れ0。unblocked_condition はファミリーがこの2件だけだったため完全解消。pilot323 cards を登録形に書換、round358 cards を新設（登録カード自身の実挙動: 011 ブロックされなければ相手クリーチャーを手札に戻す・ブロック時は発火しない／049 ブロックされなければ山札からクリーチャーを手札に加える・ブロック時は発火しない）。テスト22 passed（round358 cards 5＋pilot323 cards 登録形 2＋pilot323 本体 7＋data_audit 8）。回答は answers/round358.yaml に保存。次の番号: パイロット324 / ラウンド359 / プロト T990。

**提出形の修正（owner: any）**: 形Aの当初形は select に owner が無く、実挙動プローブで相手のクリーチャーが候補に出ず自分のクリーチャー（攻撃者自身）だけが手札に戻ることを検出した。select の owner 既定は you のため、両プレイヤーが対象の時は owner: any が要る（第292弾と同じ罠。T081 のバウンス先例と同形）。proto・テスト・docs を owner: any に修正してから提出した。**訂正**: 第323弾の記録で「両 id とも aliases 記録も無いことを提出前に確認済み」と書いたのは、対象 id 自体に aliases が無いことの確認で、同名再録の存在までは見ていなかった。dmx09-049 は submit 時に同名再録3件（dm09-054 / dmc34-053 / dmc39-031、いずれも「誕生の祈」）が source.aliases に記録された。この3件は converted.yaml にも rejects.jsonl にも無く、rejects 行の畳み込みではない。

## 第324弾 「自分のクリーチャー１体はその数（自分のクリーチャーの数）のシールドを追加でブレイクする」（breaks_equal_creature_count）— エンジン拡張（スキーマのみ）

センサス（rejects 2,047件を取り直し）: pure 1,898件 / multi 131件 / 空 gaps 18件（全て第312〜315弾の監査で別ブロッカー確認済み。数え方は全行を pure/multi/空に分け、out_of_scope 行も gaps に従って数える）。pure の大半は範囲外（gr_summon 147、aura 108＝未承認、hyperdimensional_zone 105、dragheart 45、psychic_filter 45、hyperdimensional_summon 41、out_of_game 23、duelist_link 20、outside_game 12＝2026-11-06 ユーザー指示で対象外化済み、pandora_shift 4）か評価済み DEEP/重い/延期（第318〜323弾の記録参照）。delayed_return / draw_up_to / look_reorder / flying / does_not_untap は新しい証拠がない限り再提案しない（第320・321弾で却下済み）。第323弾の記録でドリフト候補として残した **breaks_equal_creature_count（純粋2件、multi-gap 行にも現れない）** を選定した。

対象は dm24ex2-024 / dm26ex4-cho021（同名カード ジョジョジョ・マキシマムの2印刷）。dm24ex2-024 の partial は骨格あり（unsupported は breaks_equal_creature_count だけ）。dm26ex4-cho021 は partial 空。by_product で原文照合済み。両カードとも無色・コスト9・マナ1の呪文。
- dm24ex2-024: 「G・ゼロ：バトルゾーンまたはマナゾーンに自分のジョーカーズが合計11枚以上あれば、この呪文をコストを支払わずに唱えてもよい。自分のクリーチャーを数える。このターン、自分のクリーチャー１体はその数のシールドを追加でブレイクし、そのクリーチャーの攻撃中、相手は呪文を唱えられない。」
- dm26ex4-cho021: G・ゼロの文言が「自分の、ジョーカーズとマナゾーンにあるジョーカーズ・カードが合計11以上なら」と異なる（by_product の原文のまま。効果は同一）。

結論: エンジン拡張（スキーマのみ）。3つの既存の形の組み合わせだが、1点だけスキーマの拡張が必要だった。
- G・ゼロ: free_if {cmp: [{count: {zone: [bz, mana], owner: you, filter: {race_has: ジョーカーズ}}}, '>=', 11]}（free_if の cmp＋count 形は既存。zone の配列は zones_of が受ける）。
- 数えて付与: [set_var n {count: {zone: bz, owner: you, filter: {types: [creature]}}}; choose {zone: bz, owner: you, filter: {types: [creature]}, count: 1} as chosen; modify {ref: chosen} {breaks_add: {var: n}} end_of_turn]。breaks_add の辞書形に {var: 名前} を許可するスキーマ拡張（dmsim/cards/defs.py Checker.mod と dmsim/cards/schema.py の breaks_add 項目。card.schema.json は `python -m dmsim.cards.schema` で再生成。提出時の _schema_check は card.schema.json を読むため、defs.py だけでは足りず提出で弾かれた。実行時は op_modify の _bake_refs が生成時に数値へ焼くため core.py の変更は不要。{amount, count} 形（第170弾）は攻撃時に数え直すためここでは使えない（解決時の数を固定するため）。なお {var:} の読みが1になる latent bug は第322弾で修正済み。
- 攻撃中の呪文封じ: delayed_trigger {event: attack, subject: {ref: chosen}} → [modify {zone: hand, owner: opp, filter: {types: [spell]}} {deny: [cast]} during_attack] duration end_of_turn, once: false（遅延誘発は subject: {ref: 変数名} で「その〜」を指せる。deny cast の during_attack 形は dmex13-064 の先例。once: false は「そのクリーチャーの攻撃中」が攻撃のたびに適用されるため）。

proto T990（dm24ex2-024 型）/ T991（dm26ex4-cho021 型。呪文部分は同一で G・ゼロの文言だけが違う）。テスト8件通過（pilot324 本体 6: 形の一致、G・ゼロ＝11枚で無料・10枚で非無料、呪文＝自分のクリーチャー3体で選んだ1体が4枚割る、選んだ攻撃中は相手の呪文唱え不可・攻撃後は可、選ばれなかった攻撃では封じなし、＋pilot324 cards 提出前 2）。次の番号: パイロット325 / ラウンド360 / プロト T992。

### ラウンド359（第324弾の再変換）

**新規登録1件**（dm26ex4-cho021 ジョジョジョ・マキシマム＝free_if {cmp: [{count: {zone: [bz, mana], owner: you, filter: {race_has: ジョーカーズ}}}, '>=', 11]} ＋ [set_var n {count: {zone: bz, owner: you, filter: {types: [creature]}}}; choose {zone: bz, owner: you, filter: {types: [creature]}, count: 1} as chosen; modify {ref: chosen} {breaks_add: {var: n}} end_of_turn; delayed_trigger {event: attack, subject: {ref: chosen}} → [modify {zone: hand, owner: opp, filter: {types: [spell]}} {deny: [cast]} during_attack] end_of_turn, once: false]。無色・コスト9・マナ1の呪文。by_product で原文照合済み（G・ゼロの文言は「自分の、ジョーカーズとマナゾーンにあるジョーカーズ・カードが合計11以上なら」。登録形は確立形と完全一致で連結混入なし）・**alias 畳み込み1件**（dm24ex2-024＝旧印刷。identity 実測で canon_id は dm26ex4-cho021。reopen で行を外し、cho021 の登録時に validate の aliases_for が source.aliases = [dm24ex2-024, dmex19-002, dmrp04m-001] を自動付与した。dm24ex2-024 は converted の独立エントリではなく alias として引け、reject 行も残らないことを提出後に確認済み）・**stale クリーンアップ0件**・**差し戻し0件**。対象2行は gaps = [breaks_equal_creature_count] のため reopen で外してから submit（reopen は dm24ex2-024 の1件だけが外れた。dm26ex4-cho021 の rejects 行には reason が無く reopen の条件に合わなかったためで、submit で rejects から外れた）。converted 10,270→**10,271** / rejects 2,047→**2,045**、重なり0・漏れ0。breaks_equal_creature_count はファミリーがこの2行だけだったため完全解消。pilot324 cards を登録形に書換、round359 cards を新設（登録カード自身の実挙動: ジョーカーズ11枚で無料・自分のクリーチャー3体で選んだ1体が4枚割る・選んだ攻撃中は相手の呪文唱え不可で攻撃後は可）。テスト20 passed（round359 cards 4＋pilot324 cards 登録形 2＋pilot324 本体 6＋data_audit 8）。回答は answers/round359.yaml に保存。次の番号: パイロット325 / ラウンド360 / プロト T992。

**提出時のスキーマ不一致（第324弾の追記）**: breaks_add {var: n} は defs.py の Checker を通ったが、submit の _schema_check は data/schema/card.schema.json を読むため「スキーマ不一致」で弾かれた。dmsim/cards/schema.py の breaks_add 項目に {var: string} の第3選択肢を追加し、`python -m dmsim.cards.schema > data/schema/card.schema.json` で再生成してから再提出した（両ファイルとも第324弾のコミットに含めた）。**教訓**: スキーマ拡張は defs.py と schema.py の両方＋card.schema.json の再生成までが1セット（defs.py だけでは提出で弾かれる）。**pytest の再発**: VM 再起動で pytest が消えたため `pip install --break-system-packages 'pytest>=8'` で復旧（2026-11-21 再発・復旧済み）。
