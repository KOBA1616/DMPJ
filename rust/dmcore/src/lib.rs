//! DMSIM コア（Rust 試作）。Python 版との境界は「状態そのもの」: State は Rust 側が持ち、
//! Python からは clone / digest / to_json / from_json と、準備（new_game）だけを呼ぶ。
mod engine;
mod rules;
mod search;
mod setup;
mod state;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use state::GameState;

#[pyclass(name = "State")]
#[derive(Clone)]
struct PyState {
    s: GameState,
}

#[pymethods]
impl PyState {
    #[staticmethod]
    fn from_json(text: &str) -> PyResult<PyState> {
        serde_json::from_str::<GameState>(text).map(|s| PyState { s }).map_err(|e| PyValueError::new_err(e.to_string()))
    }
    #[staticmethod]
    fn new_game(spec_json: &str) -> PyResult<PyState> {
        let spec: setup::NewGameSpec = serde_json::from_str(spec_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(PyState { s: setup::new_game(&spec) })
    }
    fn clone(&self) -> PyState {
        self.clone_state()
    }
    fn digest(&self) -> String {
        self.s.digest()
    }
    /// Python の GameState.fast_key と同じ値（位置符号化）。
    fn fast_key(&self) -> String {
        self.s.fast_key()
    }
    fn to_json(&self) -> String {
        self.s.to_json()
    }
    fn rng_next(&mut self) -> u64 {
        self.s.rng_next()
    }
}

impl PyState {
    fn clone_state(&self) -> PyState {
        PyState { s: self.s.clone() }
    }
}

pyo3::create_exception!(dmcore, Unsupported, pyo3::exceptions::PyException);

fn conv(e: engine::EngErr) -> PyErr {
    match e {
        engine::EngErr::Unsupported(m) => Unsupported::new_err(m),
        engine::EngErr::Illegal(m) => PyValueError::new_err(m),
    }
}

#[pyclass(name = "Engine")]
#[derive(Clone)]
struct PyEngine {
    e: engine::Engine,
}

#[pymethods]
impl PyEngine {
    /// state_json: 初期状態、rules_json: Python 側 rules_bundle の出力
    #[staticmethod]
    fn open(state_json: &str, rules_json: &str) -> PyResult<PyEngine> {
        let s: GameState = serde_json::from_str(state_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
        let r: rules::Rules = serde_json::from_str(rules_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(PyEngine { e: engine::Engine::new(s, std::sync::Arc::new(r)).map_err(conv)? })
    }
    /// 次の判断（JSON 文字列）を返す。勝敗が付いていれば None。
    fn advance(&mut self) -> PyResult<Option<String>> {
        Ok(self.e.advance().map_err(conv)?.map(|v| v.to_string()))
    }
    fn answer(&mut self, choice: Vec<i64>) -> PyResult<()> {
        self.e.answer(choice).map_err(conv)
    }
    /// 速度測定・探索の内側向け: 組み込み方策で終局（または未移植）まで進める。mode: "first" | "pass"（最後の選択肢=パス）
    fn run(&mut self, mode: &str) -> PyResult<i64> {
        let mut n = 0;
        while let Some(d) = self.e.advance().map_err(conv)? {
            let len = d["options"].as_array().map_or(1, |a| a.len()) as i64;
            let i = if mode == "pass" { len - 1 } else { 0 };
            self.e.answer(vec![i]).map_err(conv)?;
            n += 1;
        }
        Ok(n)
    }
    /// 規則はそのまま共有して、状態だけ差し替えた新しいエンジン（決定化の注入用。規則の JSON を読み直さない）
    fn with_state(&self, state_json: &str) -> PyResult<PyEngine> {
        let s: GameState = serde_json::from_str(state_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(PyEngine { e: engine::Engine::new(s, self.e.rules.clone()).map_err(conv)? })
    }
    fn fork(&self) -> PyEngine {
        self.clone()
    }
    fn digest(&self) -> String {
        self.e.s.digest()
    }
    /// Python の GameState.fast_key と同じ値（位置符号化）。
    fn fast_key(&self) -> String {
        self.e.s.fast_key()
    }
    fn to_json(&self) -> String {
        self.e.s.to_json()
    }
    fn result(&self) -> Option<String> {
        self.e.s.result.as_ref().map(|v| v.to_string())
    }
    /// 最後の決定の記録（answer の直後に Python 側の log へ足す）
    fn last_log(&self) -> Option<String> {
        self.e.log.last().map(|v| v.to_string())
    }
    fn log_len(&self) -> usize {
        self.e.log.len()
    }
    /// よく読む小さな値（状態全体の変換を避ける）: (active, turn, first_player, step)
    fn quick(&self) -> (i64, i64, i64, String) {
        (self.e.s.active, self.e.s.turn, self.e.s.first_player, self.e.s.step.clone())
    }
    /// 探索の打ち切り（勝者なしの結果を書く）
    fn set_result(&mut self, js: &str) -> PyResult<()> {
        self.e.s.result = Some(serde_json::from_str(js).map_err(|e| PyValueError::new_err(e.to_string()))?);
        Ok(())
    }
    fn eval_feats(&self, me: i64) -> Vec<i64> {
        self.e.eval_feats(me)
    }
    fn zone_ids(&self, z: &str, owner: i64) -> Vec<i64> {
        self.e.zone_ids(z, owner)
    }
    fn card_sig(&self, cid: i64) -> (String, Vec<String>) {
        self.e.card_sig(cid)
    }
    fn zone_names(&self, z: &str, owner: i64, top: bool) -> Vec<String> {
        self.e.zone_names(z, owner, top)
    }
    fn skel_raw(&self) -> String {
        self.e.skel_raw().to_string()
    }
    fn log(&self) -> String {
        serde_json::Value::Array(self.e.log.clone()).to_string()
    }
    /// 増分E・段階1: ターン内展開ループ（search::expand_turn）。params_json は
    /// dmsim.engine.rustcore.expand_turn が組み立てる。戻り値は (メタ情報 JSON, 葉の Engine 列)。
    /// 走査は大きなスタックのスレッドで回す（Python の再帰と同じ深さの DFS を Rust の再帰で写すため）。
    fn expand_turn(&self, params_json: &str) -> PyResult<(String, Vec<PyEngine>)> {
        let e = self.e.clone();
        let pj = params_json.to_string();
        let h = std::thread::Builder::new()
            .stack_size(512 * 1024 * 1024)
            .spawn(move || search::expand_turn(&e, &pj))
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        match h.join() {
            Ok(r) => r
                .map(|(meta, engines)| {
                    (meta, engines.into_iter().map(|e| PyEngine { e }).collect())
                })
                .map_err(conv),
            Err(_) => Err(PyValueError::new_err("expand_turn panicked")),
        }
    }
    /// 増分G の照合用: trim スコア（search::trim_score）をこの Engine の状態で計算する。
    fn trim_score(&self, trim_json: &str) -> PyResult<Vec<f64>> {
        let spec = search::TrimSpec::parse(trim_json).map_err(conv)?;
        Ok(search::trim_score(&self.e, &spec))
    }
    /// 照合用: engine.loop.abstract(eng, "in_turn") の骨格ハッシュ。
    /// zones_counter_json は {ゾーン名: counter か} の JSON。
    fn abstract_hash(&self, zones_counter_json: &str) -> PyResult<String> {
        let zc: std::collections::HashMap<String, bool> =
            serde_json::from_str(zones_counter_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(search::abstract_hash_of(&self.e, &zc))
    }
}

/// 増分G: crossturn 統合のセッション。保持局面と当ターンの候補を Rust 側に
/// 持ち、ターン境界処理（葉の振り分け・保持選択）まで Rust で完結させる。
/// 駆動（総予算・メモリ・progress の確認）は Python 側に残る。
#[pyclass(name = "CrossturnSession")]
struct PyCrossturn {
    // 展開のたびにセッション全体を clone すると候補集合のぶんメモリが倍化し
    // 速度も落ちるため、take して別スレッドへ渡し、終わったら戻す形にする。
    // パニック／エラーの場合はセッションを破棄する（Python 側はケース全体を
    // 従来経路でやり直すので意味論は保たれる）。
    s: Option<search::Crossturn>,
}

fn session_gone() -> PyErr {
    PyValueError::new_err("crossturn session is closed (rust panic/error)")
}

#[pymethods]
impl PyCrossturn {
    /// 開始局面の Engine（dmcore.Engine）からセッションを開く。
    #[staticmethod]
    fn open(core: PyEngine) -> PyResult<PyCrossturn> {
        Ok(PyCrossturn {
            s: Some(search::Crossturn::new(core.e)),
        })
    }
    fn frontier_len(&self) -> PyResult<usize> {
        Ok(self.s.as_ref().ok_or_else(session_gone)?.frontier_len())
    }
    /// frontier の次の1局面を展開する。params_json は expand_turn と同じ
    /// パラメータ、trim_json は trim スコアの仕様。戻り値は
    /// (メタ情報 JSON, キル葉の Engine or None)。走査は大きなスタックの
    /// スレッドで回す（expand_turn と同じ理由）。
    fn expand_next(&mut self, params_json: &str, trim_json: &str) -> PyResult<(String, Option<PyEngine>)> {
        let mut sess = self.s.take().ok_or_else(session_gone)?;
        let pj = params_json.to_string();
        let tj = trim_json.to_string();
        let h = std::thread::Builder::new()
            .stack_size(512 * 1024 * 1024)
            .spawn(move || {
                let r = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                    sess.expand_next(&pj, &tj)
                }));
                (sess, r)
            })
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        match h.join() {
            Ok((sess2, Ok(Ok((meta, kill))))) => {
                self.s = Some(sess2);
                Ok((meta, kill.map(|e| PyEngine { e })))
            }
            Ok((_sess2, Ok(Err(e)))) => Err(conv(e)),
            Ok((_sess2, Err(_))) => Err(PyValueError::new_err("crossturn expand_next panicked")),
            Err(_) => Err(PyValueError::new_err("crossturn expand_next thread failed")),
        }
    }
    /// ターン境界の保持選択。戻り値は (trim 前の候補件数, 保持件数)。
    fn finish_turn(&mut self, keep: i64) -> PyResult<(usize, usize)> {
        let s = self.s.as_mut().ok_or_else(session_gone)?;
        Ok(s.finish_turn(keep))
    }
}

#[pymodule]
fn dmcore(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyState>()?;
    m.add_class::<PyEngine>()?;
    m.add_class::<PyCrossturn>()?;
    m.add("Unsupported", m.py().get_type::<Unsupported>())?;
    Ok(())
}
