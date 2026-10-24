# dmsim（DMPJ プロトタイプ）

デュエル・マスターズのルールエンジン骨格。設計の詳細は設計書（Claude Doc）を参照。

```
pip install pyyaml pytest
python -m pytest -q          # 設計判断の検証テスト
docker build -t dmsim . && docker run --rm dmsim
python -m dmsim.devserver    # 開発者モード http://127.0.0.1:8765/
python -m dmsim.solitaire --deck deck.yaml --games 1000 --turns 4 --workers 4   # 1人回しのキル率
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
- `dmsim/play.py`   方策・対戦実行・シード付き記録の保存と再生（`python -m dmsim.play --seed 1 --out g.json` / `--replay g.json`）
- `dmsim/solitaire.py` 1人回しAI（自分のターン内を探索、ループはストック、ロックは試し回しで確認）と、
  シード付きの大量試行で「自分の Nターン目までのキル率」（95%信頼区間・キルの種類別）を出すハーネス
- `dmsim/scenario.py` 配置を指定した局面の作成（テストと開発者モードで共用）
- `dmsim/devserver.py`＋`dmsim/web/` 開発者モード（標準ライブラリのHTTPサーバー）
- `data/rules/*.yaml` ゾーン・キーワード・DSLマクロ・許可/禁止できる行為（permissions）・ターンのステップ列（turn）の定義
- `data/cards/proto.yaml` 検証用の架空カード、`data/cards/real.yaml` 実カード（公式テキストを変換したもの。`source.review` で確認状態を持つ）
- `data/cards/raw/*.jsonl` 公式カード詳細ページから取った原文
- `tools/fetch_cards.py` 公式サイトからカードテキストを取る（手元のPCで実行。3秒以上の間隔・HTMLをキャッシュ）
- `tools/convert_cards.py` 原文を効果DSLに変換する（Claude API。`pip install anthropic`、`ANTHROPIC_API_KEY` が必要）
- 参照ルール: 総合ゲームルール Ver.1.53（公式PDF。リポジトリには含めない）

## 開発者モードの起動

ブラウザで開く画面です（外部ライブラリ不要、Python 3.11 以上）。

```
git clone https://github.com/KOBA1616/DMPJ.git     # 非公開リポジトリ: GitHub にログインした状態で
cd DMPJ
pip install pyyaml
python -m dmsim.devserver                          # → http://127.0.0.1:8765/ をブラウザで開く
python -m dmsim.devserver --port 9000              # ポートを変える場合
```

Docker の場合（ポートを公開し、コンテナの外から届くよう `--host 0.0.0.0` を付ける）:

```
docker build -t dmsim .
docker run --rm -p 8765:8765 dmsim python -m dmsim.devserver --host 0.0.0.0
# → http://localhost:8765/
```

- 「カード」タブ: カードごとの公式テキストと効果データ。「試す」でそのカードの局面ができ、approve / reject は `data/cards/real.yaml` に書き込まれる（Docker では保存されないので、確認結果を残すなら `-v "$PWD/data:/app/data"` を付ける）
- 「対戦」タブ: 配置を指定した局面を作り、選択肢に答えて進める。1手戻す、記録（シード＋選択）の保存と読み込みもここ
- 認証や暗号化はないので、`--host 0.0.0.0` は手元のPCや信頼できるネットワークでだけ使う

## カードを増やす手順

1. `python tools/fetch_cards.py <カードID...> --out data/cards/raw/official_YYYYMMDD.jsonl`（手元のPCで）
2. `python tools/convert_cards.py data/cards/raw/official_YYYYMMDD.jsonl`（`data/cards/converted.yaml` に出る。
   検査を通らなかったものは `data/cards/raw/rejects.jsonl`）
3. `python -m dmsim.devserver` の「カード」タブで「試す」→ 動かして確かめ、approve / reject を付ける
4. 確かめたカードを `real.yaml` に移す。動作をテストに残すなら `tests/test_real_cards.py` に足す
