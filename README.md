# dmsim（DMPJ プロトタイプ）

デュエル・マスターズのルールエンジン骨格。設計の詳細は設計書（Claude Doc）を参照。
**開発状況とTODOは [docs/STATUS.md](docs/STATUS.md)**（数字は `python tools/gen_status.py` で更新）。

```
pip install pyyaml pytest
python -m pytest -q          # 設計判断の検証テスト
docker build -t dmsim . && docker run --rm dmsim
python -m dmsim.devserver    # 開発者モード http://127.0.0.1:8765/
python -m dmsim.solitaire --deck deck.yaml --games 1000 --turns 4 --workers 4   # 1人回しのキル率
```

- `dmsim/engine/state.py`  純データのゲーム状態（乱数状態・実行中タスク・決定待ちも含む）
- `dmsim/engine/` タスクスタック式のエンジン
  - `core.py` 進行ループと Decision、`registry.py` 拡張ポイント（task / op の登録表）
  - `selectors.py` セレクタ・式・条件、`events.py` イベント→置換→適用→状況起因→誘発→待機（解決窓）
  - `interpreter.py` 効果DSLの実行、`ops.py` DSLのコア語彙、`turn.py` ターン構造とカードの実行、`combat.py` 攻撃・バトル・ブレイク
- `dmsim/cards/defs.py`   カード定義の読み込みと効果DSLの検証（閉じた語彙＋マクロ展開、op 引数の型検査）
- `dmsim/types.py`  タスク・イベント・Decision などの形（TypedDict）。`DMSIM_CHECK=1` で実行時に検査
- `dmsim/cards/schema.py` カードDSLの JSON Schema を生成（`data/schema/card.schema.json`。LLM変換に渡す）
- `dmsim/engine/loop.py`   骨格＋カウンタによるループ／ロック検出とストック証明
- `dmsim/engine/play.py`   方策・対戦実行・シード付き記録の保存と再生（`python -m dmsim.play --seed 1 --out g.json` / `--replay g.json`）
- `dmsim/solitaire.py` 1人回しAI（自分のターン内を探索、ループはストック、ロックは試し回しで確認）と、
  シード付きの大量試行で「自分の Nターン目までのキル率」（95%信頼区間・キルの種類別）を出すハーネス
- `dmsim/engine/scenario.py` 配置を指定した局面の作成（テストと開発者モードで共用）
- `dmsim/devserver.py`＋`dmsim/web/` 開発者モード（標準ライブラリのHTTPサーバー）
- `dmsim/playback.py` 対戦記録の再生解析（ループの骨格・周回数・ストック量・勝ち筋）。開発者モードの「再生」タブが使う（読み取り専用）
- `data/rules/*.yaml` ゾーン・キーワード・DSLマクロ・許可/禁止できる行為（permissions）・ターンのステップ列（turn）の定義
- `data/cards/proto.yaml` 検証用の架空カード、`data/cards/real.yaml`・`data/cards/real_zone.yaml`・`data/cards/real_vocab.yaml` 実カード（公式テキストを変換したもの。`source.review` で確認状態を持つ。
  `real_zone.yaml` はゾーン間移動を補完し合うカード。G・ゼロは `free_if`、「マナをタップせずに」は `when.unpaid`。
  `real_vocab.yaml` は語彙拡張: 「選ばれない」は mod の `deny: [be_chosen]`、「選んだ時」は event `choose`、「かわりにバトルさせてもよい」は event `battle` の置換＋`op: battle_substitute`）
- `data/cards/raw/*.jsonl` 公式カード詳細ページから取った原文
- `tests/test_saga_loop.py` 【絶望神サガループ】の検証（下記のループデッキの動作試験）
- `tools/fetch_cards.py` 公式サイトからカードテキストを取る（手元のPCで実行。3秒以上の間隔・HTMLをキャッシュ）
- `tools/convert_cards.py` 原文を効果DSLに変換する（Claude API: `pip install anthropic` と `ANTHROPIC_API_KEY`）
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

1. `python tools/fetch_cards.py <カードID...> --out data/cards/raw/official_YYYYMMDD.jsonl`（手元のPCで）。弾ごとなら `--set DMRP1 --count 93 --skip-known`。ID は公式の形式 `dmrp01-001` に正規化して管理する（`dmsim/cardid.py`）
2. （任意・API不要）`python tools/survey_text.py data/cards/raw --uncovered` 原文の文を正規化して、同じ形の文を持つカード枚数で並べる。変換前に足す語彙の見当をつける
2. `python tools/convert_cards.py data/cards/raw`（`data/cards/converted.yaml` に出る。ディレクトリ・複数ファイル・glob 可）。
   大量なら `--workers 4 --order short --limit 200` で少しずつ。検査を通らなかったものは `data/cards/raw/rejects.jsonl`、
   結果（件数・トークン・失敗理由の種類別）は `data/cards/raw/convert_report.json`。語彙を足したあとは `--retry-rejects` で落ちたものだけやり直す。
   `python tools/report_gaps.py` で足りない語彙を枚数順に集計
3. `python -m dmsim.devserver` の「カード」タブで「試す」→ 動かして確かめ、approve / reject を付ける
   （「一括検証」ボタン: 全カードの「試す」シナリオを探索方策で自動回しし、例外・ループを報告する。`dmsim/engine/verify.py`）
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

## ループ発見と勝ち筋探索の分離（2段探索）

`python -m dmsim.loop_first --setup tests/saga_loop_first_setup.yaml`（`dmsim/loop_first.py`）。
1段目で勝ちを求めずにループ（骨格が戻る行動列＋カウンタ差分）だけを集め、2段目で周回数 n を変えてストックした局面から勝ちを探す。
1段目の結果は再生で確かめられ、同じ入力から同じ結果になる。山札20枚のサガ構成では、単独の探索(約1800ノード・4秒)より遅い(約15秒)。
利点は、ループ（資源）と勝ち筋（払い）を別々に調整・キャッシュでき、周回数が探索パラメータになること。

## ゾーン変換グラフ（ループ候補の静的な列挙）

`python -m dmsim.zone_graph --max-cards 2`（`dmsim/engine/zone_graph.py`）。各カードの効果から「どのゾーンからどのゾーンへ動くか」を取り、
互いの移動が相手の誘発の前提を満たす閉路をループ候補として列挙する。閉路の差分は動的な検出と一致する（サガ: 山札-1・墓地+1）。
現在は「ゾーンに入った時」の誘発だけを扱う（唱える・ターン開始・攻撃などで回るループは未対応）。
候補は実際にループするか確かめるため、`dmsim.loop_first` や `dmsim.combo_search` の部品固定に渡す。

`python -m dmsim.combo_search --from-cycles 3 --slots 1`: ゾーン変換グラフのループ候補を固定部品にして残りを探索する。
`python -m dmsim.pool_metrics --deck deck.yaml`: カードごとの dig（1回で山札から触れる枚数）・speed と、デッキの dig_total（全部絡めば掘れる上限。山札の枚数を超えれば山を掘り切れる当たり）。

### 公式サイトからの取得（確立した方法）

クラウド開発環境は `dm.takaratomy.co.jp` に届かない（プロキシが 403）ので、GitHub Actions のランナーで取る:
`.github/workflows/fetch-cards.yml`（手動実行。弾の表記と件数を入れる）か、`tools/fetch_request.yaml` を編集して push する。
結果は Artifact `cards-raw` と `cards-raw/<弾>` ブランチの `data/cards/raw/<弾>.jsonl` に出る（2026-10-24 に DMRP1 の3枚で確認済み）。
手元のPCなら `python tools/fetch_cards.py --set DMRP1 --count 93 --skip-known`。
