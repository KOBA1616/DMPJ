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
- `tests/test_saga_loop.py` 【絶望神サガループ】の検証（下記のループデッキの動作試験）
- `tools/fetch_cards.py` 公式サイトからカードテキストを取る（手元のPCで実行。3秒以上の間隔・HTMLをキャッシュ）
- `tools/convert_cards.py` 原文を効果DSLに変換する（Claude API。`pip install anthropic`、`ANTHROPIC_API_KEY` が必要）
- 参照ルール: 総合ゲームルール Ver.1.53（公式PDF。リポジトリには含めない）

## カードを増やす手順

1. `python tools/fetch_cards.py <カードID...> --out data/cards/raw/official_YYYYMMDD.jsonl`（手元のPCで）
2. `python tools/convert_cards.py data/cards/raw/official_YYYYMMDD.jsonl`（`data/cards/converted.yaml` に出る。
   検査を通らなかったものは `data/cards/raw/rejects.jsonl`）
3. `python -m dmsim.devserver` の「カード」タブで「試す」→ 動かして確かめ、approve / reject を付ける
   （「一括検証」ボタン: 全カードの「試す」シナリオを探索方策で自動回しし、例外・ループを報告する。`dmsim/verify.py`）
4. 確かめたカードを `real.yaml` に移す。動作をテストに残すなら `tests/test_real_cards.py` に足す

## 【絶望神サガループ】の検証

TCG 実カード4枚（`real.yaml` / `data/cards/raw/official_20261024c.jsonl`）で、デッキアウトを「かわりに勝つ」
に置換するデッキが動く。テストは `py -m pytest tests/test_saga_loop.py`:

1. シャコガイルなしでループを続ける → 山札1枚のドローで**デッキアウト敗北**（無限ループにならない）
2. シャコガイルが場にいる → 山札1枚のドローが**置換されて勝利**
3. 実戦3killルート: サガA/Bの CIPループ（1ドロー1捨て＋出す→壊すで山札を減らす）→
   《超神星DOOM・ドラゲリオン》を超無限墓地進化（墓地から1体以上選べる。進化元1体につき召喚コスト1軽減）→
   攻撃時メテオバーンで下の《一なる部隊 イワシン》を墓地へ＋《シャコガイル》を踏み倒し →
   イワシンの誘発（メテオバーンの解決完了後に解決。公式裁定どおり）で最後の1枚を引く → 置換勝利

対応したエンジン機能: 置換効果の `if` 条件（《シャコガイル》の山札1枚判定）、墓地からの進化・進化元の複数選択・
進化元1体につき1のコスト軽減、クリーチャーの下のカードを指すセレクタ（メテオバーン）。
DMP（デュエルマスターズプレイス）の調整・テキストは使用せず、すべて takaratomy 公式カード詳細ページの
TCGテキストから変換している。

## サガループを1人回しAIが見つけられるか／部品を固定した探索

`tests/test_saga_discovery.py`（`py -m pytest tests/test_saga_discovery.py`）:
- 検出器（`LoopDetector(report_all=True)`）はサガの周回を「山札-1・墓地+1」の骨格回帰として見つけ、再生で確かめる。
- 1人回しAIは、山札を削るだけのループ（`is_burn`）を山札1枚までストックして続きを探索する。
  シャコガイルが場にいれば自力で置換勝利、手札に《ドラゲリオン》があれば3killルート全体を探索量 `--budget 2500` 程度で見つける。
- `python -m dmsim.combo_search`: 部品を固定して残りを探す。
  - 山札モード: `--fix ID:枚数` を固定し、`--slots` 種類を候補から足してキル率で並べる（1段目→上位を再測定）。
  - 配置モード: `--setup tests/saga_setup.yaml --fill-zone hand --slots 1 --turns 1`（配置を固定して足りない1枚を探す）。

「好きな順序で」は move の `order: choose`（`order_cards` の決定。答えの先頭が、置いたカードの中で一番上）。
山札の中での並べ替え（見たカードを山札の下に置く）は山札から離れないので、104.2b の「一瞬の山札0枚」に数えない。

探索量の目安（1人回しAI、山札7枚・墓地はタイフーンで貯める想定）: 手札に サガ×2・ドラゲリオン・イザナギテラス・コダマダンス・
エマージェンシー・タイフーン、墓地にイワシン・シャコガイルがある局面は、約37,000ノード（87秒）で勝ちを見つける。
時間の大半は、サガのループ中の「何を捨てるか」「蘇生するか」の分岐（捨てる札の選び方の枝刈りが次の課題）。
