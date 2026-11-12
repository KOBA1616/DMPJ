# base/store への移行状況（P1-S0 その2）

書き込み口は `dmsim/base/store.py`（`root()` / `write_text`（一時ファイル→os.replace）/ `append_line` / `append_json`（split 付き）/ `purpose="tuning"` への holdout 書き込み拒否）。

## 移行済み
- `dmsim/deckplan/evaluate.py` `record`（採否台帳、purpose=tuning）
- `dmsim/autofix/selfheal.py` `save`
- `dmsim/deckplan/budget.py` `save_history`
- `dmsim/discovery/auto.py` LoopSpec の保存2か所

## 未移行の直接書き込み（ファイル: 箇所数）
S1 カードデータ・定期ワークフロー（auto_sync / auto_convert / convert_cards / fetch / sync）とローカルワーカーは、ワークフローを壊さないため対象外のまま。
```
tools/local_worker.py: 8
tools/auto_tune.py: 5
tools/combo_hunt.py: 4
tools/v_gate.py: 3
tools/llm_offload/providers.py: 2
tools/llm_offload/__init__.py: 2
tools/fetch_cards.py: 2
tools/discover_sets.py: 2
tools/discover_pipeline.py: 2
tools/convert_cards.py: 2
tools/combo_screen.py: 2
tools/auto_fix.py: 2
tools/auto_convert.py: 2
dmsim/eval/measure.py: 2
dmsim/discovery/auto.py: 2
dmsim/combo_search.py: 2
dmsim/cardstore.py: 2
dmsim/autofix/valuelearn.py: 2
dmsim/approval.py: 2
tools/usage_audit.py: 1
tools/sync_cards.py: 1
tools/split_cards.py: 1
tools/pair_verify.py: 1
tools/pair_exec.py: 1
tools/measure_candidates.py: 1
tools/hypothesis_gate.py: 1
tools/gen_status.py: 1
tools/gen_stages.py: 1
tools/gen_eval_starts.py: 1
tools/explore_decks.py: 1
tools/eval_plan_chain.py: 1
tools/eval_multiturn.py: 1
tools/eval_harness.py: 1
tools/eval_convert.py: 1
tools/eval_baseline.py: 1
tools/dedupe_cards.py: 1
tools/catalog_sets.py: 1
tools/build_tenmon_loopspec.py: 1
tools/build_decks.py: 1
tools/auto_sync.py: 1
tools/audit_cards.py: 1
tools/analyze_ids.py: 1
dmsim/validity.py: 1
dmsim/engine/play.py: 1
dmsim/plan/spec.py: 1
dmsim/eval/explog.py: 1
dmsim/devserver.py: 1
dmsim/deckplan/spec.py: 1
dmsim/deckplan/budget.py: 1
dmsim/autofix/selfheal.py: 1
dmsim/autofix/batch.py: 1
```
