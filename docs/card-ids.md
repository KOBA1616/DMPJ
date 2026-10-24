# カードIDの型（台帳 全件）

`python tools/analyze_ids.py` が `data/cards/ledger_ids.txt`（商品とIDの一覧。台帳 `sets.json` の写し）から生成する。手で編集しない。

- 総数 **23671** 枚、商品 398 件。大文字小文字を無視しても重複なし: **はい**
- 形は `商品部-番号部`。ハイフンが2つ以上のもの: 76 枚（例 `dmbd08-a-001`）。最初のハイフンで商品部と番号部に分ける
- 商品部に大文字が混じるもの: 0 枚（全件小文字）。番号部は大文字・小文字が混在する
- 英数字とハイフン以外の記号: {'$': 1, '+': 9}。URL にそのまま入れると壊れるもの（`+` は空白になる）: 10 枚 → `detail_url` でパーセントエンコード
- `normalize_id`（人が打つ表記ゆれを吸収する整形）で衝突するもの: 4 組 [['dm23rp4x-OR01', 'dm23rp4x-OR1'], ['dm23rp4x-OR02', 'dm23rp4x-OR2'], ['dm23rp2x-OR01', 'dm23rp2x-OR1'], ['dm23rp2x-OR02', 'dm23rp2x-OR2']] → 台帳のIDには使わず、`canonical_id`（小文字にするだけ）を正本にする

## 商品部の型

| 型 | 件数 | 例 |
|---|---:|---|
| `aa99aa9` | 6729 | `dm26ex4-CHO005` |
| `aaaa99` | 5679 | `dmbd22-008` |
| `aaa99` | 4734 | `dmx26-s01` |
| `aa99` | 3094 | `dm39-s01` |
| `aaaaaa99` | 1731 | `promoy20-gum2-003` |
| `aaa99a` | 519 | `dmx22a-s01` |
| `aa99aa9a` | 506 | `dm23rp4x-OR01` |
| `aaaaa99` | 245 | `dmpcd03-b01` |
| `aaaaaa9` | 183 | `promoy9-001` |
| `aaaa99a` | 175 | `dmrp04m-s01` |
| `aa` | 30 | `sp-001` |
| `99` | 18 | `39-SECS003` |
| `aaaaaaaaaaa99` | 16 | `dmartkiwami03-001` |
| `aa99+9a` | 9 | `dm34+1s-001` |
| `a99` | 2 | `c48-SEC001` |
| `aa99aaa` | 1 | `dm20yrs-01` |

## 番号部の型

| 型 | 件数 | 例 |
|---|---:|---|
| `999` | 17624 | `dm26ex4-001` |
| `a99` | 1440 | `dmpcd03-b01` |
| `a999` | 447 | `dm26sd1-m001` |
| `AA99` | 419 | `dm25ex4-TR05` |
| `A99` | 379 | `dm25ex4-S01` |
| `AA9` | 378 | `dm25ex4-SP5` |
| `99A` | 318 | `dm23rp4x-01B` |
| `Aaa99` | 282 | `dm25rp4-Sec01` |
| `AAA999` | 217 | `dm26ex4-CHO005` |
| `AA999` | 202 | `dm26rp3-OR001` |
| `999A` | 183 | `dm23rp4x-001X` |
| `Aaa999` | 171 | `dm25ex2-Cho003` |
| `9A` | 128 | `dm23rp1-1B` |
| `999AA` | 122 | `dm35-009HC` |
| `aa9Aaa99` | 111 | `dm25ex3-rp1Sec02` |
| `A999` | 93 | `dm26rp3-S001` |
| `A9` | 93 | `dm23rp1-S1` |
| `aa9A99` | 86 | `dm25ex3-rp1S01` |
| `aa9999` | 86 | `dm25ex3-rp4001` |
| `aa9AA9` | 67 | `dm25ex3-rp1TR2` |
| `aa99` | 65 | `dmex19-ms01` |
| `aa9` | 65 | `dmpcd02-sp1` |
| `aa9a99` | 62 | `promoy18-sp6d04` |
| `a-999` | 56 | `dmbd08-a-001` |
| `aaaa99` | 40 | `dmrp20-coro01` |
| `aaa9999` | 33 | `promoy24-spd1201` |
| `AaaA99` | 30 | `dm25ex2-ChoG03` |
| `a999A` | 29 | `dm26sd1-m003F` |
| `AAAA999` | 28 | `dm26ex1-SECN001` |
| `a999AAAA` | 27 | `dm26sd1-m001STAR` |
| `aaaaa99` | 24 | `promoy23-kamip01` |
| `aa9AA99` | 22 | `dm24ex3-rp1TR02` |
| `aaa999` | 22 | `promoy19-spd803` |
| `AAA999AAA` | 20 | `dm26ex3-SEC001CHO` |
| `AAA99` | 20 | `dm25ex4-SPR01` |
| `aaaa999` | 20 | `dmbd17-teki002` |
| `aaa9-999` | 20 | `promoy20-gum2-003` |
| `a9` | 19 | `dmex19-s1` |
| `AAAAAA999` | 17 | `dm26rp3-STDSEC009` |
| `AaaAA9` | 16 | `dm25rp4-SecDM1` |
| その他 36 型 | 190 | |

## 取り扱い

- 取得URL: `detail_url(公式ID)`（公式のIDそのまま。大文字小文字は台帳のまま）。HTMLキャッシュ名も同じエンコード。
- カードの正本ID: `canonical_id(公式ID)`。台帳の全IDで衝突しないことを `tests/test_ledger_ids.py` が保証する。
- 人が打ったID: `resolve_id`（台帳にあればその公式ID、なければ `normalize_id` で整形）。
