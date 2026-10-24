# dmsim（DMPJ プロトタイプ）

デュエル・マスターズのルールエンジン骨格。設計の詳細は設計書（Claude Doc）と `docs/` を参照。

```
pip install pyyaml pytest
python -m pytest -q          # 設計判断の検証テスト
docker build -t dmsim . && docker run --rm dmsim
```

- `dmsim/state.py`  純データのゲーム状態（乱数状態・実行中タスク・決定待ちも含む）
- `dmsim/engine/` タスクスタック式のエンジン
  - `core.py` 進行ループと Decision、`registry.py` 拡張ポイント（task / op の登録表）
  - `selectors.py` セレクタ・式・条件、`events.py` イベント→置換→適用→状況起因→誘発→待機（解決窓）
  - `interpreter.py` 効果DSLの実行、`ops.py` DSLのコア語彙、`turn.py` ターン構造とカードの実行、`combat.py` 攻撃・バトル・ブレイク
- `dmsim/defs.py`   カード定義の読み込みと効果DSLの検証（閉じた語彙＋マクロ展開、op 引数の型検査）
- `dmsim/types.py`  タスク・イベント・Decision などの形（TypedDict）。`DMSIM_CHECK=1` で実行時に検査
- `dmsim/schema.py` カードDSLの JSON Schema を生成（`data/schema/card.schema.json`。LLM変換に渡す）
- `dmsim/loop.py`   骨格＋カウンタによるループ／ロック検出とストック証明
- `dmsim/play.py`   方策・対戦実行・シード＋ログ再生
- `data/rules/*.yaml` ゾーン・キーワード・DSLマクロ・許可/禁止できる行為（permissions）・ターンのステップ列（turn）の定義
- `data/cards/proto.yaml` 検証用の架空カード
- 参照ルール: 総合ゲームルール Ver.1.53（公式PDF。リポジトリには含めない）
