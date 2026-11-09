//! DMSIM コア（Rust 試作）。Python 版との境界は「状態そのもの」: State は Rust 側が持ち、
//! Python からは clone / digest / to_json / from_json と、準備（new_game）だけを呼ぶ。
mod engine;
mod rules;
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
    fn fork(&self) -> PyEngine {
        self.clone()
    }
    fn digest(&self) -> String {
        self.e.s.digest()
    }
    fn to_json(&self) -> String {
        self.e.s.to_json()
    }
    fn result(&self) -> Option<String> {
        self.e.s.result.as_ref().map(|v| v.to_string())
    }
    fn log(&self) -> String {
        serde_json::Value::Array(self.e.log.clone()).to_string()
    }
}

#[pymodule]
fn dmcore(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyState>()?;
    m.add_class::<PyEngine>()?;
    m.add("Unsupported", m.py().get_type::<Unsupported>())?;
    Ok(())
}
