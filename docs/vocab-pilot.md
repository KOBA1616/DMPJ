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

## 次の候補

- freeze キーワード本体（攻撃してブロックされなかった時の誘発）: 「ブロックされなかった」イベントが無いので中規模
- once_per_turn / first_time_per_turn（計約100件）: `mark` の応用か、誘発ゲートの仕組み化
- civil_count（52件）: 文明数を数える式の追加
