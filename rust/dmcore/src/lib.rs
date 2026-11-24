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
}

/// バッチ実行用の簡易 RNG（xorshift64*）。方策の乱択専用で、対戦内部の乱数（状態の rng）とは別。
struct BatchRng(u64);

impl BatchRng {
    fn next(&mut self) -> u64 {
        let mut x = self.0;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        self.0 = x;
        x.wrapping_mul(0x2545F4914F6CDD1D)
    }
    fn below(&mut self, n: u64) -> u64 {
        if n <= 1 { 0 } else { self.next() % n }
    }
}

/// 組み込み方策で1つの決定に答える。policy: "first"（最小数を先頭から）| "random"（一様乱択、Python の random_policy と同じ分布）
fn batch_answer(d: &serde_json::Value, policy: &str, rng: &mut BatchRng) -> Vec<i64> {
    let n = d["options"].as_array().map_or(0, |a| a.len()) as i64;
    let min = d["min"].as_i64().unwrap_or(1).clamp(0, n);
    let max = d["max"].as_i64().unwrap_or(min).clamp(min, n);
    if policy == "random" {
        let k = min + rng.below((max - min + 1) as u64) as i64;
        let mut idx: Vec<i64> = (0..n).collect();
        for i in 0..k as usize {
            let j = i + rng.below((n as usize - i) as u64) as usize;
            idx.swap(i, j);
        }
        idx.truncate(k as usize);
        idx
    } else {
        (0..min).collect()
    }
}

/// 複数局を Rust 内部で一括実行する（Phase 3: バッチ並行API）。
/// rules_json は1回だけパースし、局ごとに状態だけ差し替える。決定ごとの Python 往復は無い。
/// 戻り: JSON 配列。各要素は {winner, turn, decisions} または {error}。
#[pyfunction]
fn run_batch(py: Python<'_>, rules_json: &str, states_json: &str, policy: &str, seed: u64) -> PyResult<String> {
    let rules_s = rules_json.to_string();
    let states_s = states_json.to_string();
    let policy_s = policy.to_string();
    let out = py.allow_threads(move || -> Result<String, String> {
        let r: rules::Rules = serde_json::from_str(&rules_s).map_err(|e| e.to_string())?;
        let rules = std::sync::Arc::new(r);
        let states: Vec<String> = serde_json::from_str(&states_s).map_err(|e| e.to_string())?;
        let mut results: Vec<serde_json::Value> = Vec::with_capacity(states.len());
        for (i, sj) in states.iter().enumerate() {
            let mut rng = BatchRng((seed ^ (i as u64).wrapping_mul(0x9E3779B97F4A7C15)) | 1);
            let one = (|| -> Result<serde_json::Value, engine::EngErr> {
                let s: GameState = serde_json::from_str(sj).map_err(|e| engine::EngErr::Illegal(e.to_string()))?;
                let mut e = engine::Engine::new(s, rules.clone())?;
                let mut decisions: i64 = 0;
                while let Some(d) = e.advance()? {
                    if decisions >= 100_000 {
                        return Err(engine::EngErr::Illegal("decision limit".into()));
                    }
                    let ans = batch_answer(&d, &policy_s, &mut rng);
                    e.answer(ans)?;
                    decisions += 1;
                }
                let res = e.s.result.clone().unwrap_or(serde_json::Value::Null);
                Ok(serde_json::json!({
                    "winner": res["winner"].clone(),
                    "turn": res["turn"].clone(),
                    "decisions": decisions,
                }))
            })();
            results.push(match one {
                Ok(v) => v,
                Err(e) => serde_json::json!({"error": format!("{e:?}")}),
            });
        }
        Ok(serde_json::Value::Array(results).to_string())
    });
    out.map_err(PyValueError::new_err)
}

#[pymodule]
fn dmcore(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyState>()?;
    m.add_class::<PyEngine>()?;
    m.add_function(wrap_pyfunction!(run_batch, m)?)?;
    m.add("Unsupported", m.py().get_type::<Unsupported>())?;
    Ok(())
}
