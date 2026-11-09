//! DMSIM コア（Rust 試作）。Python 版との境界は「状態そのもの」: State は Rust 側が持ち、
//! Python からは clone / digest / to_json / from_json と、準備（new_game）だけを呼ぶ。
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

#[pymodule]
fn dmcore(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyState>()?;
    Ok(())
}
