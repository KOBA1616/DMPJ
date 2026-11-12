# 陽性対照の張り付き（2026-11-13, PR #395）

## 原因
PR #303（2026-11-10）で `tools/combo_screen.py` の試行を通常の開幕（40枚・2ターン）に変えた際、点が「相手自身のドロー（山札40枚を30基準で数え +2）とマナチャージ（2〜3枚）」を数えていた。候補に関係なく全組が平均 7.0。#306 の陽性対照は導入時から一度も意味のある判定をしておらず、`data/eval/control_stamp.json` も一度もコミットされていない。

## 現状（#395 後）
- 同シードの基準局（ダミー40枚）との差分だけを点にする。
- `dmsim/validity.judge` が張り付き（全行同値／既知コンボ＝ランダム組）を理由付きで不合格にする。
- 2ターンの通常開幕では既知コンボもランダム組も全行 0.0 → 「張り付き」で不合格。**これが正しい状態**。印は作らない。

## 影響
#303 以降の `combo_screen --verify` の opp_deck / opp_mana は相手の自然増減が混ざった値（使わない）。日次ルーティンはこの検査を参照しない。`--pairs` は #303 から停止中。

## 次の担当へ: 実行層での対照（P2 で koba さんに確認してから）
- 6ターン化は採らない（3〜4ターンキル重視の方針）。
- `tools/exec_tier.exec_spec(rules, t, deck)` で仕込み済み開始局面を得る（`deck_fix.resolve_setup` → LoopSpec自動/部品表自動なら `spec_with_deck` で山札差し替え）。
- 既知コンボ: `data/known_combos/combos.yaml` の各 combo を t として exec_spec に渡し、その spec を `play_game(..., start=build(rules, spec))` で 3〜4ターン回す。
- ランダム組: 同じ spec の部品（core）だけをランダムなカードに差し替えて回し、分布を作る。percentile 判定と張り付き検知は `validity.judge` をそのまま使う。
- holdout（drill_lock）は判定に含めない（judge は tuning のみ）。
