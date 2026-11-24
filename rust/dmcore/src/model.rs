//! Phase 7: 方策モデルの Rust 埋め込み。dmsim/ai のエンコードと推論（プーリング版
//! Model）を Rust で再実装し、run_batch_model で「収集（自己対戦＋軌跡記録）」を
//! 一括APIの中で完結させる。特徴の定義は Python 版（dmsim/ai/encode.py）と同一で、
//! 一致は tests/test_rust_model.py のパリティテストで担保する。

use crate::engine::Engine;
use crate::rules::Rules;
use crate::state::GameState;
use crate::BatchRng;
use serde_json::{json, Value};
use std::collections::BTreeMap;

pub const D_EMB: usize = 24;
pub const H_TOK: usize = 64;
pub const H_CTX: usize = 128;
pub const H_MID: usize = 64;
pub const MAXK: usize = 16;
const ZONE_NAMES: [&str; 10] = ["my_bz", "my_mana", "my_grave", "my_hand", "my_shield",
    "op_bz", "op_mana", "op_grave", "op_hand", "op_shield"];
const VERBS: [&str; 15] = ["charge", "play", "attack", "block", "pass", "yes", "no", "mana",
    "shield", "deck", "bz", "graveyard", "hand", "no_block", "decline"];

// ---- 重み ----
pub struct Weights {
    pub emb: Vec<f32>, pub emb_rows: usize,
    pub w1: Vec<f32>, pub b1: Vec<f32>,
    pub wc: Vec<f32>, pub bc: Vec<f32>,
    pub wv1: Vec<f32>, pub bv1: Vec<f32>, pub wv2: Vec<f32>, pub bv2: Vec<f32>,
    pub wk: Vec<f32>, pub bk: Vec<f32>,
    pub wo1: Vec<f32>, pub bo1: Vec<f32>, pub wo2: Vec<f32>, pub bo2: Vec<f32>,
}

fn flat(v: &Value) -> Vec<f32> {
    match v {
        Value::Array(rows) if !rows.is_empty() && rows[0].is_array() => {
            rows.iter().flat_map(|r| r.as_array().unwrap().iter().map(|x| x.as_f64().unwrap() as f32)).collect()
        }
        Value::Array(xs) => xs.iter().map(|x| x.as_f64().unwrap() as f32).collect(),
        _ => vec![],
    }
}

impl Weights {
    pub fn from_json(v: &Value) -> Weights {
        let emb = flat(&v["emb"]);
        Weights {
            emb_rows: emb.len() / D_EMB, emb,
            w1: flat(&v["W1"]), b1: flat(&v["b1"]),
            wc: flat(&v["Wc"]), bc: flat(&v["bc"]),
            wv1: flat(&v["Wv1"]), bv1: flat(&v["bv1"]),
            wv2: flat(&v["wv2"]), bv2: flat(&v["bv2"]),
            wk: flat(&v["Wk"]), bk: flat(&v["bk"]),
            wo1: flat(&v["Wo1"]), bo1: flat(&v["bo1"]),
            wo2: flat(&v["wo2"]), bo2: flat(&v["bo2"]),
        }
    }
}

fn matvec(w: &[f32], rows: usize, cols: usize, x: &[f32], b: &[f32]) -> Vec<f32> {
    let mut out = vec![0f32; rows];
    for r in 0..rows {
        let mut s = b[r];
        let base = r * cols;
        for c in 0..cols {
            s += w[base + c] * x[c];
        }
        out[r] = s;
    }
    out
}

fn tanh(v: &mut [f32]) {
    for x in v.iter_mut() {
        *x = x.tanh();
    }
}

// ---- 語彙と静的特徴（Python の Vocab と同一） ----
pub struct Vocab {
    pub index: BTreeMap<String, usize>, // defn -> 添字（1始まり）
    pub statics: Vec<[f32; 5]>,         // 添字 -> [cost, power, is_creature, is_spell, civ数]
}

impl Vocab {
    /// defns は Python の Vocab.ids（正規IDのソート済みリスト）をそのまま受け取る。
    /// バンドルの cards には別名（alias）が混ざるため、Rust 側で keys から作ると添字がずれる。
    pub fn build(rules: &Rules, defns: &[String]) -> Vocab {
        let mut index = BTreeMap::new();
        let mut statics = vec![[0f32; 5]];
        for (i, d) in defns.iter().enumerate() {
            index.insert(d.clone(), i + 1);
            let cd = &rules.cards[d];
            statics.push([
                cd.cost as f32 / 10.0,
                cd.power as f32 / 10000.0,
                if cd.types.iter().any(|t| t == "creature") { 1.0 } else { 0.0 },
                if cd.types.iter().any(|t| t == "spell") { 1.0 } else { 0.0 },
                cd.civs.len() as f32 / 2.0,
            ]);
        }
        Vocab { index, statics }
    }
    pub fn idx(&self, defn: &str) -> usize {
        self.index.get(defn).copied().unwrap_or(0)
    }
}

// ---- エンコード ----
pub struct EncState {
    pub tok_defn: Vec<i64>,
    pub tok_num: Vec<[f32; 8]>,
    pub tok_zone: Vec<i64>,
    pub glob: [f32; 12],
}

fn zone_key(zone: &str, owner: i64, me: i64) -> Option<usize> {
    let my = owner == me;
    let name = match (zone, my) {
        ("bz", true) => "my_bz", ("bz", false) => "op_bz",
        ("mana", true) => "my_mana", ("mana", false) => "op_mana",
        ("graveyard", true) => "my_grave", ("graveyard", false) => "op_grave",
        ("hand", true) => "my_hand", ("hand", false) => "op_hand",
        ("shield", true) => "my_shield", ("shield", false) => "op_shield",
        _ => return None,
    };
    ZONE_NAMES.iter().position(|z| *z == name).map(|i| i as usize)
}

pub fn encode_state(s: &GameState, player: i64, vocab: &Vocab) -> EncState {
    let me = player;
    let op = 1 - player;
    let mut enc = EncState { tok_defn: vec![], tok_num: vec![], tok_zone: vec![], glob: [0.0; 12] };
    for zone in ["bz", "mana", "graveyard", "hand", "shield"] {
        for p in [me, op] {
            let zk = match zone_key(zone, p, me) { Some(z) => z, None => continue };
            let cids: &[i64] = s.zones.get(zone).and_then(|z| z.get(p as usize)).map(|v| v.as_slice()).unwrap_or(&[]);
            let hidden = zone == "shield" || (zone == "hand" && p != me);
            for (pos, &cid) in cids.iter().enumerate() {
                if zone == "hand" && p != me {
                    continue;
                }
                let c = &s.cards[cid as usize];
                let di = vocab.idx(&c.defn);
                let st = vocab.statics[di];
                enc.tok_defn.push(if hidden { 0 } else { di as i64 });
                enc.tok_num.push([
                    if hidden { 0.0 } else { st[0] },
                    if hidden { 0.0 } else { st[1] },
                    if c.tapped { 1.0 } else { 0.0 },
                    if hidden { 0.0 } else { st[2] },
                    if hidden { 0.0 } else { st[3] },
                    if hidden { 0.0 } else { st[4] },
                    c.under.len() as f32 / 4.0,
                    pos as f32 / 10.0,
                ]);
                enc.tok_zone.push(zk as i64);
            }
        }
    }
    let zlen = |zone: &str, p: i64| -> f32 {
        s.zones.get(zone).and_then(|z| z.get(p as usize)).map(|v| v.len()).unwrap_or(0) as f32
    };
    enc.glob = [
        s.turn as f32 / 20.0,
        if s.active == me { 1.0 } else { 0.0 },
        zlen("mana", me) / 10.0, zlen("mana", op) / 10.0,
        zlen("shield", me) / 5.0, zlen("shield", op) / 5.0,
        zlen("hand", me) / 10.0, zlen("hand", op) / 10.0,
        zlen("deck", me) / 40.0, zlen("deck", op) / 40.0,
        zlen("graveyard", me) / 20.0, zlen("graveyard", op) / 20.0,
    ];
    enc
}

pub struct EncOpts {
    pub opt_defn: Vec<i64>,
    pub opt_num: Vec<[f32; 6]>,
    pub min: i64,
    pub max: i64,
}

fn verb_band(key: &str) -> f32 {
    let head = key.split(':').next().unwrap_or("");
    match VERBS.iter().position(|v| *v == head) {
        Some(i) => i as f32 / VERBS.len() as f32,
        None => 1.0,
    }
}

pub fn encode_options(s: &GameState, d: &Value, vocab: &Vocab) -> EncOpts {
    let opts = d["options"].as_array().cloned().unwrap_or_default();
    let mut out = EncOpts {
        opt_defn: vec![], opt_num: vec![],
        min: d["min"].as_i64().unwrap_or(1), max: d["max"].as_i64().unwrap_or(1),
    };
    for (i, o) in opts.iter().enumerate() {
        let mut cids: Vec<i64> = vec![];
        if let Some(c) = o.get("cid").and_then(|v| v.as_i64()) {
            cids.push(c);
        } else if let Some(cs) = o.get("cids").and_then(|v| v.as_array()) {
            cids = cs.iter().filter_map(|v| v.as_i64()).collect();
        }
        let defs: Vec<&str> = cids.iter()
            .filter(|&&c| c >= 0 && (c as usize) < s.cards.len())
            .map(|&c| s.cards[c as usize].defn.as_str()).collect();
        let (mut di, mut ac, mut ap) = (0i64, 0f32, 0f32);
        if !defs.is_empty() {
            di = vocab.idx(defs[0]) as i64;
            for dfn in &defs {
                let st = vocab.statics[vocab.idx(dfn)];
                ac += st[0];
                ap += st[1];
            }
            ac /= defs.len() as f32;
            ap /= defs.len() as f32;
        }
        out.opt_defn.push(di);
        out.opt_num.push([
            verb_band(o["key"].as_str().unwrap_or("")),
            if cids.is_empty() { 0.0 } else { 1.0 },
            cids.len() as f32 / 4.0,
            i as f32 / 10.0, ac, ap,
        ]);
    }
    out
}

// ---- 推論 ----
pub fn forward(w: &Weights, st: &EncState, op: &EncOpts) -> (Vec<f32>, f32, Vec<f32>) {
    // トークン: emb + 数値 → tanh(W1) → ゾーン平均
    let mut zone_sum = [[0f32; H_TOK]; 10];
    let mut zone_cnt = [0usize; 10];
    for (i, &di) in st.tok_defn.iter().enumerate() {
        let mut x = vec![0f32; D_EMB + 8];
        if di > 0 {
            x[..D_EMB].copy_from_slice(&w.emb[di as usize * D_EMB..(di as usize + 1) * D_EMB]);
        }
        x[D_EMB..].copy_from_slice(&st.tok_num[i]);
        let mut h = matvec(&w.w1, H_TOK, D_EMB + 8, &x, &w.b1);
        tanh(&mut h);
        let z = st.tok_zone[i] as usize;
        for j in 0..H_TOK {
            zone_sum[z][j] += h[j];
        }
        zone_cnt[z] += 1;
    }
    let mut ctx_in = vec![0f32; 10 * H_TOK + 12];
    for z in 0..10 {
        if zone_cnt[z] > 0 {
            for j in 0..H_TOK {
                ctx_in[z * H_TOK + j] = zone_sum[z][j] / zone_cnt[z] as f32;
            }
        }
    }
    ctx_in[10 * H_TOK..].copy_from_slice(&st.glob);
    let mut ctx = matvec(&w.wc, H_CTX, 10 * H_TOK + 12, &ctx_in, &w.bc);
    tanh(&mut ctx);
    // 価値
    let mut hv = matvec(&w.wv1, H_MID, H_CTX, &ctx, &w.bv1);
    tanh(&mut hv);
    let value: f32 = hv.iter().zip(w.wv2.iter()).map(|(a, b)| a * b).sum::<f32>() + w.bv2[0];
    // 個数
    let count_logits = matvec(&w.wk, MAXK + 1, H_CTX, &ctx, &w.bk);
    // 選択肢スコア
    let mut scores = Vec::with_capacity(op.opt_defn.len());
    for (i, &di) in op.opt_defn.iter().enumerate() {
        let mut ox = vec![0f32; H_CTX + D_EMB + 6];
        ox[..H_CTX].copy_from_slice(&ctx);
        if di > 0 {
            ox[H_CTX..H_CTX + D_EMB].copy_from_slice(&w.emb[di as usize * D_EMB..(di as usize + 1) * D_EMB]);
        }
        ox[H_CTX + D_EMB..].copy_from_slice(&op.opt_num[i]);
        let mut ho = matvec(&w.wo1, H_MID, H_CTX + D_EMB + 6, &ox, &w.bo1);
        tanh(&mut ho);
        scores.push(ho.iter().zip(w.wo2.iter()).map(|(a, b)| a * b).sum::<f32>() + w.bo2[0]);
    }
    (scores, value, count_logits)
}

fn softmax_pick(scores: &[f32], rest: &[usize], rng: &mut BatchRng) -> usize {
    let max = rest.iter().map(|&i| scores[i]).fold(f32::MIN, f32::max);
    let mut tot = 0f64;
    let mut ws: Vec<f64> = rest.iter().map(|&i| {
        let e = ((scores[i] - max) as f64).exp();
        tot += e;
        e
    }).collect();
    let mut r = (rng.next() % 1_000_000) as f64 / 1_000_000.0 * tot;
    for (j, wgt) in ws.iter_mut().enumerate() {
        r -= *wgt;
        if r <= 0.0 {
            return j;
        }
    }
    rest.len() - 1
}

pub fn act(w: &Weights, st: &EncState, op: &EncOpts, rng: &mut BatchRng) -> Vec<i64> {
    let (scores, _value, count_logits) = forward(w, st, op);
    let mn = op.min.max(0) as usize;
    let mx = (op.max as usize).min(MAXK).max(mn);
    let k = if mn == mx {
        mn
    } else {
        // 個数分布からサンプル
        let seg = &count_logits[mn..=mx];
        let max = seg.iter().fold(f32::MIN, |a: f32, b: &f32| a.max(*b));
        let exps: Vec<f64> = seg.iter().map(|x| ((x - max) as f64).exp()).collect();
        let tot: f64 = exps.iter().sum();
        let mut r = (rng.next() % 1_000_000) as f64 / 1_000_000.0 * tot;
        let mut kk = mx;
        for (j, e) in exps.iter().enumerate() {
            r -= e;
            if r <= 0.0 {
                kk = mn + j;
                break;
            }
        }
        kk
    };
    let mut rest: Vec<usize> = (0..scores.len()).collect();
    let mut choice = vec![];
    for _ in 0..k.min(rest.len()) {
        let j = softmax_pick(&scores, &rest, rng);
        choice.push(rest.remove(j) as i64);
    }
    choice.sort();
    choice
}

// ---- JSON 化（軌跡の返却用。Python の encode 出力と同形） ----
pub fn state_json(st: &EncState) -> Value {
    json!({
        "tok_defn": st.tok_defn,
        "tok_num": st.tok_num.iter().map(|r| r.to_vec()).collect::<Vec<_>>(),
        "tok_zone": st.tok_zone,
        "glob": st.glob.to_vec(),
    })
}

pub fn opts_json(op: &EncOpts) -> Value {
    json!({
        "opt_defn": op.opt_defn,
        "opt_num": op.opt_num.iter().map(|r| r.to_vec()).collect::<Vec<_>>(),
        "min": op.min, "max": op.max,
    })
}

fn push_i32(buf: &mut Vec<u8>, xs: &[i64]) {
    for x in xs {
        buf.extend_from_slice(&(*x as i32).to_le_bytes());
    }
}

fn push_f32(buf: &mut Vec<u8>, xs: &[f32]) {
    for x in xs {
        buf.extend_from_slice(&x.to_le_bytes());
    }
}

/// モデル方策で1局を回し、軌跡をバイナリバッファ（buf）へ追記する。
/// 戻りはメタ情報（winner/turn と決定ごとの要素数）。特徴の並びは決定ごとに
/// tok_defn(i32×T), tok_num(f32×T×8), tok_zone(i32×T), glob(f32×12),
/// opt_defn(i32×O), opt_num(f32×O×6), choice(i32×K)。
/// JSON で軌跡を返すと文字列化が律速になるため、この形にした。
pub fn run_game_model(e: &mut Engine, w: &Weights, vocab: &Vocab, seed: u64, buf: &mut Vec<u8>) -> Value {
    let mut rng = BatchRng(seed | 1);
    let mut meta: Vec<Value> = vec![];
    let mut decisions = 0i64;
    loop {
        match e.advance() {
            Ok(Some(d)) => {
                if decisions >= 100_000 {
                    return json!({"error": "decision limit", "traj": meta});
                }
                let player = d["player"].as_i64().unwrap_or(0);
                let st = encode_state(&e.s, player, vocab);
                let op = encode_options(&e.s, &d, vocab);
                let choice = act(w, &st, &op, &mut rng);
                push_i32(buf, &st.tok_defn);
                for row in &st.tok_num {
                    push_f32(buf, row);
                }
                push_i32(buf, &st.tok_zone);
                push_f32(buf, &st.glob);
                push_i32(buf, &op.opt_defn);
                for row in &op.opt_num {
                    push_f32(buf, row);
                }
                push_i32(buf, &choice);
                meta.push(json!({
                    "t": st.tok_defn.len(), "o": op.opt_defn.len(), "k": choice.len(),
                    "player": player, "min": op.min, "max": op.max,
                }));
                if let Err(err) = e.answer(choice) {
                    return json!({"error": format!("{err:?}"), "traj": meta});
                }
                decisions += 1;
            }
            Ok(None) => break,
            Err(err) => return json!({"error": format!("{err:?}"), "traj": meta}),
        }
    }
    let res = e.s.result.clone().unwrap_or(Value::Null);
    json!({
        "winner": res["winner"].clone(), "turn": res["turn"].clone(),
        "decisions": decisions, "traj": meta,
    })
}
