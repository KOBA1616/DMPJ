# 自立発見ランナー

盤面を変異させながら探索し、勝てた盤面を検証・縮約して LoopSpec として保存する。LLM は使わない（課金なし）。

```
python tools/auto_discover.py --config tools/auto_discover.yaml --seconds 600 --out data/loops/auto
```

- 設定 `tools/auto_discover.yaml`: `pool`（盤面に足してよいカード）、`seeds`（種盤面。同名4枚の制限を守ること）、`width`（ビーム幅）、`rate_seeds`。
- 1周: 種盤面を変異（追加・削除・差し替え・ゾーン移動・シード変更）→ ビーム探索 → 勝てたら手順を再生して win_rate（同じ手順が通るシードの割合）を測る
  → 手順が通る盤面の下限まで縮約 → `data/loops/auto/<署名>.json`。署名は非 filler カードの多重集合で、同じものは保存しない。
- win_rate が 0.99 以上なら `deterministic`、それ未満はシャッフルなどの運しだいの `reroll`。
- 手順は `source.steps`、盤面は `source.board` に入る。`tests/test_tenmon_loopspec.py` と同様に再生すれば回帰テストになる。
- **見つかった勝ちは、必ずカード名つきで一手ずつ確認する**。自動発見は、カード変換の誤り（例: アレフティナの手札でのコスト増が効いていなかった）を最初に突く。
- GitHub Actions の `auto-discover`（手動実行）でも回せる。結果は artifact。

## デッキ版（mode: deck）
種盤面はすべて通常の開幕から始める: 40枚デッキ、シャッフル、先手後手はシードで決まる、手札5枚・盾5枚・墓地0・マナ0・1ターン目。
- `deck_counts`（残りは `filler` で40枚）か `deck`（40枚の並び）を種にする。同名4枚まで。
- 相手は `opp_card` 40枚（マナチャージのみ）。`eval_seeds` 個のシードで評価し、`max_turn`（通しターン数）までに勝てるデッキを探す。
- 勝ちは `data/loops/auto/<署名>.json` に保存（デッキの署名で重複除去）。単なる直接攻撃の勝ちも出るので、保存後にカード単位で監査すること。
