# 自動診断のサガ実行（2026-11-08）
`python tools/auto_fix.py --combo saga --deck data/decks/saga_entry.yaml --need dm22ex2-021 --board graveyard:dm22ex2-021:1 --seeds 8 --rounds 2`（約4分）
- 診断: board 段階（部品は見える 62%、墓地サガ 38%、キル 0%）→ 手作業の結論（墓地仕込み不足）と一致。
- 候補（部品倍率2倍・墓地重み2倍）は 8 局では有意差なし（inconclusive）。採否には 100 局以上が要る。
- cards 段階は deckplan の `add_parts` 候補（部品が3枚未満なら非部品札と入れ替え）へ接続。採用は人。
