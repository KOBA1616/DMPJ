# 実験コマンド集（全探索・横断探索まわり）

2026-11-16〜17 の探索改善で作った tools のコマンド一覧。
いずれもリポジトリルートで `python3` で実行する（このVMに pytest は無い）。

前提:

- ログは構造化 JSONL（ヘッダ＋case_start/stage_result/case_result）で
  `logs/` 配下に出る（.gitignore 済み）。勝ち手順の記録は
  `logs/exhaustive_records/` に分離される。
- 記録ファイル名には設定のハッシュ（sha256 先頭8文字）が付く
  （例: `crossturn_saga_hidden_setup_seed1_beam-9655cecb.json`）。
  設定が違う走行は別ファイルになり、上書き事故は起きない。
- 順序（--order / --trim-order）の意味: rank＝本体の候補順位、
  canonical＝正規順、value＝評価関数V、ruler＝ターン境界専用の順序関数 v2、
  plan＝大局観の段の充足率（--stages-file の鎖を使う）。

## 1. 探索の実行

### 小ケースの全探索（exhaustive_proto）

固定局面 A〜D で「勝ちがあるか／無いか」を段制（段1→段3）で調べ切る。

```bash
python3 tools/exhaustive_proto.py                      # 既定の小ケース一式
python3 tools/exhaustive_proto.py --cases D --order rank
```

- ケース: A＝シャコガイル場・山札8（勝ち）、B＝払い無し・山札8（勝ちなし証明）、
  C＝saga_setup・ドラゲリオン無し（勝ちなし証明）、D＝C＋ドラゲリオン（段1でキル）
- no-kill の証明は段3の完走時のみ。ケースD は --order value では段1が
  終わらないので rank を使う（報告書 §5.5）。

### デッキ×シードの複数ターン走行（exhaustive_multiturn）

```bash
# 段2を標準としたスキャン（段1では本家 saga のキルが隠れる。報告書 §5.8）
python3 tools/exhaustive_multiturn.py --deck data/decks/saga.yaml \
    --seeds 1,2,3,4,5,6 --stages 2 --order rank --budget 1000000 \
    --out logs/scan_saga_stage2.jsonl
```

- 判定は scope（デッキ／シード／ターン数）の中だけ。verdict は
  kill_3_4 のようにキルターンを埋め込んだ形で記録される。

### ターン横断探索（exhaustive_crossturn）

ターン終了局面を複数保持し、ターン毎の貪欲確定の見逃しを測る。

```bash
# frontier: 到達局面を全保持（打ち切られなければ no-kill が証明になる）
python3 tools/exhaustive_crossturn.py --setup tests/saga_setup.yaml \
    --seeds 1 --mode frontier --max-turn 2

# beam: 順序の上位 k 件だけ保持（k=1 が貪欲相当）
python3 tools/exhaustive_crossturn.py --setup tests/saga_hidden_setup.yaml \
    --seeds 1,2,3,4 --mode beam --beam 4 --trim-order ruler

# beam + 大局観の鎖で保持を決める
python3 tools/exhaustive_crossturn.py --setup tests/saga_hidden_setup.yaml \
    --seeds 1,2,3,4 --mode beam --beam 4 --trim-order plan \
    --stages-file tools/saga_loop_stages.yaml
```

### 比較用ベースライン（greedy_scenario_baseline）

従来方式（ターン毎に最良の終了局面を1つ確定）を同じシナリオで回す。

```bash
python3 tools/greedy_scenario_baseline.py --setup tests/saga_prep_setup.yaml \
    --seeds 1,2,3 --max-turn 4
```

## 2. 診断

```bash
# ターン1の終了局面ごとに、その先の最速キルターンを測る（順序の損失の定量化）
python3 tools/turn1_leaf_outcomes.py --setup tests/saga_hidden_setup.yaml \
    --seed 1 --max-turn 3

# 終了局面に大局観の充足率（stage_fraction）と実績キルターンを併記する
python3 tools/plan_leaf_diag.py --setup tests/saga_hidden_setup.yaml --seed 1 \
    --stages-file data/eval/stages/saga.generated.yaml
```

## 3. 段階目標の鎖: 生成と採否

```bash
# 検証済み記録の軌跡から実行フェーズの鎖を抽出する
python3 tools/chain_extract.py \
    --records 'logs/exhaustive_records/crossturn_*_frontier*.json' \
    --out tools/saga_extracted_stages.yaml

# 鎖の採否を判定する（診断＋beam4保持テスト＋ノード基準）
python3 tools/chain_gate.py --stages-file tools/saga_extracted_stages.yaml
python3 tools/chain_gate.py --stages-file data/eval/stages/saga.generated.yaml \
    --skip-diag   # 対照（生成チェーンは hidden で FAIL するのが既知の判定）
```

鎖ファイル: tools/saga_loop_stages.yaml（実行フェーズ、手書き）、
tools/saga_extracted_stages.yaml（記録から自動抽出）、
data/eval/stages/saga.generated.yaml（部品集め、stagegen の生成物）。

## 4. 検証・集計・実験管理

```bash
# 記録の再生検証（全件 strict 再生、FAIL があれば終了コード1）
python3 tools/verify_records.py --records 'logs/exhaustive_records/*.json'

# ログの集計（ファイル×ケースごとの件数・キル率・Wilson 95% 信頼区間）
python3 tools/scan_report.py logs/scan2_*.jsonl logs/scan3_*.jsonl

# ゴールデンケースの回帰（探索ツールを直したら回す。全6ケース約2分）
python3 tools/run_golden.py
python3 tools/run_golden.py crossturn-hidden-beam4-ruler-kill2   # ケースIDで絞る

# 比較実験のグリッド実行（定義は tools/grid_example.yaml がサンプル）
python3 tools/exp_grid.py tools/grid_example.yaml
python3 tools/exp_grid.py tools/grid_example.yaml --dry-run     # コマンドだけ表示

# ログヘッダの点検（設定の完全記録。不備があれば終了コード1）
python3 tools/check_log_headers.py 'logs/*.jsonl'
```

## 5. 典型的な流れ

スキャン → 集計 → 検証:

```bash
python3 tools/exhaustive_multiturn.py --deck data/decks/saga.yaml \
    --seeds 1,2,3,4,5,6 --stages 2 --order rank --budget 1000000 \
    --out logs/scan_saga_stage2.jsonl
python3 tools/scan_report.py logs/scan_saga_stage2.jsonl
python3 tools/verify_records.py --records 'logs/exhaustive_records/saga_*.json'
python3 tools/check_log_headers.py logs/scan_saga_stage2.jsonl
```

探索ツールを改修したら:

```bash
python3 tools/run_golden.py    # 既知の判定が変わっていないか
```

保持の方式を比べたら（順序×beam幅など）:

```bash
# grid 定義に「1変数だけ違う run」を並べて書く（感度スイープもこの形）
python3 tools/exp_grid.py <定義.yaml>
```

補助: tools/order_fn.py は単体コマンドではなく、順序関数 v2 と
ruler_score を提供するライブラリ（crossturn 等が import する）。
