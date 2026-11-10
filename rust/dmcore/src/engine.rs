//! エンジン（段階1）: タスクスタック・ターン進行（start / draw / charge / main の選択肢 / attack / end）・
//! イベント（draw / untap / move(マナチャージ) / turn_start / turn_end）・状況起因処理（デッキ切れ）。
//! Python 版 dmsim/engine/{core,turn,events}.py と同じ順序・同じ状態の書き換えを行う（digest が一致することが基準）。
//! 未移植の処理に当たったら Err(Unsupported) を返す。
use crate::rules::Rules;
use crate::state::GameState;
use serde_json::{json, Map, Value};
use std::collections::BTreeMap;
use std::sync::Arc;

#[derive(Debug)]
pub enum EngErr {
    Unsupported(String),
    Illegal(String),
}
pub type R<T> = Result<T, EngErr>;

fn uns<T>(what: impl Into<String>) -> R<T> {
    Err(EngErr::Unsupported(what.into()))
}

#[derive(Clone)]
pub struct Engine {
    pub s: GameState,
    pub rules: Arc<Rules>,
    pub log: Vec<Value>,
    pub step_limit: i64,
    pub turn_limit: i64,
}

enum Ask {
    Answer(Vec<usize>),
    Decision(Value),
}

impl Engine {
    pub fn new(s: GameState, rules: Arc<Rules>) -> R<Engine> {
        for c in &s.cards {
            match rules.cards.get(&c.defn) {
                Some(d) if d.plain => {}
                Some(_) => return uns(format!("card {} (plain でない)", c.defn)),
                None => return Err(EngErr::Illegal(format!("unknown card {}", c.defn))),
            }
        }
        Ok(Engine { s, rules, log: vec![], step_limit: 20000, turn_limit: 80 })
    }

    // ---- 基本の読み取り ----
    fn shared(&self, z: &str) -> bool {
        z != "hold" && self.rules.zone(z).shared
    }
    fn zl(&self, z: &str, p: i64) -> &Vec<i64> {
        &self.s.zones[z][if self.shared(z) { 0 } else { p as usize }]
    }
    fn def(&self, cid: i64) -> &crate::rules::CardDef {
        &self.rules.cards[&self.s.cards[cid as usize].defn]
    }
    /// 101.2: 禁止 → 許可 → 既定値。自分自身への常在型はバトルゾーンにある間だけ働く
    fn permits(&self, cid: i64, action: &str) -> bool {
        if self.s.cards[cid as usize].zone == "bz" {
            let d = self.def(cid);
            if d.deny.iter().any(|x| x == action) {
                return false;
            }
            if d.allow.iter().any(|x| x == action) {
                return true;
            }
        }
        *self.rules.actions.get(action).unwrap_or(&false)
    }
    /// バトルゾーンにある間のブレイク数の候補（509.2c）。能力が無ければ [1]
    fn break_opts(&self, cid: i64) -> Vec<i64> {
        let mut v: Vec<i64> = self.def(cid).breaks.clone();
        v.sort();
        v.dedup();
        if v.is_empty() { vec![1] } else { v }
    }
    fn bz_tops(&self, controller: Option<i64>) -> Vec<i64> {
        self.s.zones["bz"][0]
            .iter()
            .copied()
            .filter(|&c| {
                let k = &self.s.cards[c as usize];
                k.top_of < 0 && controller.map_or(true, |p| k.controller == p) && k.link == 0
            })
            .collect()
    }
    fn refv(&self, cid: i64) -> Value {
        json!([cid, self.s.cards[cid as usize].gen])
    }
    fn alive(&self, r: &Value) -> bool {
        match r.as_array() {
            Some(a) if a.len() == 2 => {
                let cid = a[0].as_i64().unwrap_or(-1);
                cid >= 0 && (cid as usize) < self.s.cards.len() && self.s.cards[cid as usize].gen == a[1].as_i64().unwrap_or(-2)
            }
            _ => false,
        }
    }

    // ---- 進行 ----
    pub fn advance(&mut self) -> R<Option<Value>> {
        while self.s.result.is_none() {
            if let Some(w) = &self.s.waiting {
                return Ok(Some(w.clone()));
            }
            if self.s.tasks.is_empty() {
                return Err(EngErr::Illegal("task stack empty".into()));
            }
            let tt = self.s.tasks.last().unwrap()["t"].as_str().unwrap_or("").to_string();
            let cp = self.s.tasks.last().unwrap().get("cp").and_then(|v| v.as_bool()).unwrap_or(false);
            if cp && self.s.pending.iter().any(|p| p["win"] == json!(0)) {
                self.s.tasks.push(json!({"t": "resolve_pending", "win": 0, "only_st": false}));
                continue;
            }
            let d = match tt.as_str() {
                "turn" => self.h_turn()?,
                "event" => self.h_event()?,
                "play" => self.h_play()?,
                "declare" => {
                    // 使用宣言できる能力（declare）は能力を持つカードだけ。plain では候補なし
                    self.s.tasks.pop();
                    None
                }
                "attack" => self.h_attack()?,
                "break" => self.h_break()?,
                "enqueue_st" => {
                    let t = self.s.tasks.pop().unwrap();
                    if !t["cids"].as_array().map_or(true, |a| a.is_empty()) {
                        return uns("enqueue_st（S・トリガー）");
                    }
                    None
                }
                "open_win" => {
                    let t = self.s.tasks.pop().unwrap();
                    self.s.windows.push(t["win"].as_i64().unwrap());
                    None
                }
                "close_win" => {
                    self.s.tasks.pop();
                    let w = self.s.windows.pop().unwrap_or(0);
                    let outer = self.s.windows.last().copied().unwrap_or(0);
                    for p in self.s.pending.iter_mut() {
                        if p["win"] == json!(w) {
                            p["win"] = json!(outer);
                        }
                    }
                    None
                }
                "resolve_pending" => self.h_resolve_pending()?,
                "effect" => self.h_effect()?,
                "slayer" => {
                    let t = self.s.tasks.pop().unwrap();
                    let evs: Vec<Value> = t["pairs"].as_array().unwrap().iter()
                        .map(|p| p[1].clone()).filter(|o| self.alive(o))
                        .map(|o| json!({"ev": "move", "subject": o, "to": "graveyard", "reason": "destroy"})).collect();
                    if !evs.is_empty() {
                        let e = self.ev_task(evs);
                        self.push(vec![e]);
                    }
                    None
                }
                "battle_run" => {
                    let t = self.s.tasks.pop().unwrap();
                    if self.alive(&t["att"]) && self.alive(&t["tgt"]) {
                        self.battle(&t["att"], &t["tgt"])?;
                    }
                    None
                }
                other => return uns(format!("task {}", other)),
            };
            if let Some(d) = d {
                self.s.waiting = Some(d.clone());
                return Ok(Some(d));
            }
            self.s.steps_this_turn += 1;
            if self.s.steps_this_turn > self.step_limit {
                self.s.result = Some(json!({"winner": null, "reason": "step_limit", "turn": self.s.turn}));
            }
        }
        Ok(None)
    }

    pub fn answer(&mut self, choice: Vec<i64>) -> R<()> {
        let d = match &self.s.waiting {
            Some(d) => d.clone(),
            None => return Err(EngErr::Illegal("no decision pending".into())),
        };
        let n = d["options"].as_array().map_or(0, |a| a.len()) as i64;
        let mn = d["min"].as_i64().unwrap_or(1);
        let mx = d["max"].as_i64().unwrap_or(1);
        let mut seen = std::collections::BTreeSet::new();
        for &i in &choice {
            seen.insert(i);
        }
        if seen.len() != choice.len() || !(mn <= choice.len() as i64 && choice.len() as i64 <= mx) || choice.iter().any(|&i| i < 0 || i >= n) {
            return Err(EngErr::Illegal(format!("bad choice {:?} for {}", choice, d["kind"])));
        }
        let keys: Vec<Value> = choice.iter().map(|&i| d["options"][i as usize]["key"].clone()).collect();
        self.s.tasks.last_mut().unwrap()["answer"] = json!(choice);
        self.s.waiting = None;
        self.log.push(json!({"p": d["player"], "kind": d["kind"], "choice": choice, "keys": keys}));
        Ok(())
    }

    fn ask(&mut self, player: i64, kind: &str, options: Vec<Value>, mn: usize, mx: usize) -> Ask {
        let t = self.s.tasks.last_mut().unwrap();
        if let Some(a) = t.as_object_mut().unwrap().remove("answer") {
            return Ask::Answer(a.as_array().unwrap().iter().map(|v| v.as_u64().unwrap() as usize).collect());
        }
        if mn == mx && mx == options.len() && kind != "order_cards" {
            return Ask::Answer((0..options.len()).collect());
        }
        Ask::Decision(json!({"player": player, "kind": kind, "options": options, "min": mn, "max": mx, "prompt": ""}))
    }

    fn push(&mut self, tasks: Vec<Value>) {
        for t in tasks.into_iter().rev() {
            self.s.tasks.push(t);
        }
    }

    fn ev_task(&self, evs: Vec<Value>) -> Value {
        json!({"t": "event", "evs": evs, "i": 0, "rp": 0, "skip": [], "instead": [], "captured": [], "applying": false})
    }

    /// 効果の解決者が起こす移動に、起こしたプレイヤーと発生源（効果帰属）を記録する（Python 版 ev_task(evs, env)）
    fn ev_task_env(&self, evs: Vec<Value>, env: &Value) -> Value {
        let you = env["you"].as_i64();
        let evs: Vec<Value> = evs
            .into_iter()
            .map(|mut e| {
                if e["ev"] == json!("move") {
                    if let Some(y) = you {
                        if e.get("by").is_none() {
                            e["by"] = json!(y);
                        }
                        if let Some(sr) = env.get("self").and_then(|v| v.as_array()) {
                            let src = sr[0].as_i64().unwrap();
                            if e.get("cause_defn").is_none() {
                                let cause = self.s.cards[src as usize].defn.clone();
                                e["cause"] = json!(cause);
                                e["cause_defn"] = json!(cause);
                                e["cause_kind"] = json!("ability");
                            }
                        }
                    }
                }
                e
            })
            .collect();
        self.ev_task(evs)
    }

    /// セレクタの解決（Python 版 select の、ゾーン指定・枚数・選ぶ人・types 絞り込みだけの版）。
    /// Ok(Ok(cids)) か Ok(Err(decision))。
    fn select(&mut self, sel: &Value, env: &Value) -> R<Result<Vec<i64>, Value>> {
        if let Some(c) = self.s.tasks.last().unwrap()["os"].get("chosen") {
            return Ok(Ok(c.as_array().unwrap().iter().map(|v| v.as_i64().unwrap()).collect()));
        }
        let obj = sel.as_object().unwrap();
        let you = env["you"].as_i64().unwrap();
        if obj.len() == 1 && sel.get("ref") == Some(&json!("self")) {
            let me = env["self"].clone();
            return Ok(Ok(if self.alive(&me) { vec![me[0].as_i64().unwrap()] } else { vec![] }));
        }
        for k in obj.keys() {
            if !["zone", "owner", "count", "from_top", "filter", "chooser"].contains(&k.as_str()) {
                return uns(format!("selector key {}", k));
            }
        }
        let p = match sel.get("owner").and_then(|v| v.as_str()).unwrap_or("you") {
            "you" => you,
            "opp" => 1 - you,
            _ => return uns("selector owner"),
        };
        let zone = sel["zone"].as_str().unwrap_or("");
        if !["hand", "deck", "graveyard", "mana", "bz"].contains(&zone) {
            return uns(format!("selector zone {}", zone));
        }
        let mut lst: Vec<i64> = if zone == "bz" { self.bz_tops(Some(p)) } else { self.zl(zone, p).clone() };
        if let Some(n) = sel.get("from_top") {
            let n = match n.as_i64() {
                Some(n) => n.max(0) as usize,
                None => return uns("from_top expr"),
            };
            lst.truncate(n);
        }
        if let Some(f) = sel.get("filter") {
            let fo = f.as_object().unwrap();
            for k in fo.keys() {
                if k != "types" {
                    return uns(format!("filter key {}", k));
                }
            }
            if let Some(ts) = fo.get("types") {
                let ts: Vec<String> = ts.as_array().unwrap().iter().map(|v| v.as_str().unwrap().to_string()).collect();
                lst.retain(|&c| self.def(c).types.iter().any(|t| ts.contains(t)));
            }
        }
        let cnt = sel.get("count");
        if (sel.get("from_top").is_some() && cnt.is_none()) || cnt == Some(&json!("all")) {
            return Ok(Ok(lst));
        }
        let n = match cnt {
            None => 1usize,
            Some(v) => match v.as_i64() {
                Some(n) => n.max(0) as usize,
                None => return uns("count expr"),
            },
        };
        if n.min(lst.len()) == 0 {
            return Ok(Ok(vec![]));
        }
        let chooser = match sel.get("chooser").and_then(|v| v.as_str()).unwrap_or("you") {
            "you" => you,
            "opp" => 1 - you,
            _ => return uns("chooser"),
        };
        let cands: Vec<i64> = lst
            .into_iter()
            .filter(|&c| {
                let k = &self.s.cards[c as usize];
                k.zone != "bz" || k.controller == chooser || self.permits(c, "be_chosen")
            })
            .collect();
        let n = n.min(cands.len());
        if n == 0 {
            return Ok(Ok(vec![]));
        }
        let opts: Vec<Value> = cands.iter().map(|&c| self.card_option(c, None)).collect();
        let a = match self.ask(chooser, "choose_cards", opts, n, n) {
            Ask::Decision(d) => return Ok(Err(d)),
            Ask::Answer(a) => a,
        };
        let chosen: Vec<i64> = a.iter().map(|&i| cands[i]).collect();
        self.s.tasks.last_mut().unwrap()["os"]["chosen"] = json!(chosen);
        for &c in &chosen {
            let k = &self.s.cards[c as usize];
            if k.zone == "bz" && k.controller != chooser {
                self.s.ev_seq += 1;   // 「相手がこのクリーチャーを選んだ時」の収集（plain には該当する誘発が無いので通し番号だけ進む）
            }
        }
        Ok(Ok(chosen))
    }

    fn build_steps(&self, _p: i64) -> R<Vec<Value>> {
        if !self.s.step_mods.is_empty() {
            return uns("step_mods");
        }
        Ok(self.rules.steps.iter().map(|x| json!(x)).collect())
    }

    // ---- ターン ----
    fn h_turn(&mut self) -> R<Option<Value>> {
        if self.s.skip_rest {
            return uns("skip_rest");
        }
        let (i, n) = {
            let t = self.s.tasks.last().unwrap();
            (t["i"].as_i64().unwrap(), t["steps"].as_array().unwrap().len() as i64)
        };
        if i < n {
            let name = self.s.tasks.last().unwrap()["steps"][i as usize].as_str().unwrap().to_string();
            self.s.step = name.clone();
            return match name.as_str() {
                "start" => self.st_start(),
                "draw" => self.st_draw(),
                "charge" => self.st_charge(),
                "main" => self.st_main(),
                "attack" => self.st_attack(),
                "end" => self.st_end(),
                other => uns(format!("step {}", other)),
            };
        }
        // 512 次のターンへ
        if !self.s.hold.is_empty() {
            return uns("hold");
        }
        self.s.active = if !self.s.extra_turns.is_empty() { self.s.extra_turns.remove(0) } else { 1 - self.s.active };
        self.s.turn += 1;
        if self.s.turn > self.turn_limit {
            self.s.result = Some(json!({"winner": null, "reason": "turn_limit", "turn": self.s.turn}));
        }
        let steps = self.build_steps(self.s.active)?;
        let t = self.s.tasks.last_mut().unwrap();
        t["steps"] = json!(steps);
        t["i"] = json!(0);
        t["sub"] = json!(0);
        Ok(None)
    }

    fn step_done(&mut self) {
        let t = self.s.tasks.last_mut().unwrap();
        t["i"] = json!(t["i"].as_i64().unwrap() + 1);
        t["sub"] = json!(0);
    }

    fn st_start(&mut self) -> R<Option<Value>> {
        let a = self.s.active;
        for c in self.zl("bz", a).clone() {
            if self.s.cards[c as usize].controller == a {
                self.s.cards[c as usize].hyper = false;
            }
        }
        self.s.steps_this_turn = 0;
        self.s.prev_counters = self.s.turn_counters.clone();
        self.s.turn_counters = Map::new();
        // 継続的効果・遅延効果の期限切れ（plain の対戦では空）
        if !self.s.continuous.is_empty() || !self.s.delayed.is_empty() {
            return uns("continuous/delayed");
        }
        // サイレントスキルは能力を持つカードだけ。plain では候補なし
        let mut zs = self.bz_tops(Some(a));
        zs.extend(self.zl("mana", a).iter().copied());
        let frozen: Vec<i64> = zs.iter().copied().filter(|&c| self.s.cards[c as usize].no_untap_next).collect();
        for &c in &frozen {
            self.s.cards[c as usize].no_untap_next = false;
        }
        let untap: Vec<Value> = zs
            .iter()
            .copied()
            .filter(|&c| self.s.cards[c as usize].tapped && self.permits(c, "untap_at_start") && !frozen.contains(&c))
            .map(|c| json!({"ev": "untap", "subject": self.refv(c)}))
            .collect();
        self.step_done();
        let mut ts = vec![];
        if !untap.is_empty() {
            ts.push(self.ev_task(untap));
        }
        ts.push(self.ev_task(vec![json!({"ev": "turn_start", "player": a})]));
        self.push(ts);
        Ok(None)
    }

    fn st_draw(&mut self) -> R<Option<Value>> {
        self.step_done();
        if !(self.s.turn == 1 && self.s.active == self.s.first_player) {
            let t = self.ev_task(vec![json!({"ev": "draw", "player": self.s.active})]);
            self.push(vec![t]);
        }
        Ok(None)
    }

    fn distinct_hand_options(&self, p: i64, verb: &str) -> Vec<Value> {
        let mut seen = std::collections::BTreeSet::new();
        let mut out = vec![];
        for &cid in self.zl("hand", p) {
            let dfn = self.s.cards[cid as usize].defn.clone();
            if seen.insert(dfn.clone()) {
                out.push(json!({"key": format!("{}:{}", verb, dfn), "cid": cid, "name": self.def(cid).name}));
            }
        }
        out
    }

    fn st_charge(&mut self) -> R<Option<Value>> {
        let a = self.s.active;
        let mut opts = self.distinct_hand_options(a, "charge");
        opts.push(json!({"key": "pass"}));
        let ans = match self.ask(a, "charge", opts.clone(), 1, 1) {
            Ask::Decision(d) => return Ok(Some(d)),
            Ask::Answer(a) => a,
        };
        self.step_done();
        let o = &opts[ans[0]];
        if o["key"] != json!("pass") {
            let cid = o["cid"].as_i64().unwrap();
            let t = self.ev_task(vec![json!({"ev": "move", "subject": self.refv(cid), "to": "mana", "reason": "charge"})]);
            self.push(vec![t]);
        }
        Ok(None)
    }

    fn st_main(&mut self) -> R<Option<Value>> {
        let a = self.s.active;
        let mut opts = self.play_options(a);
        // 十字ギア・ハイパー・ビビッドローの選択肢は plain では出ない
        opts.push(json!({"key": "pass"}));
        let ans = match self.ask(a, "main", opts.clone(), 1, 1) {
            Ask::Decision(d) => return Ok(Some(d)),
            Ask::Answer(x) => x,
        };
        if opts[ans[0]]["key"] == json!("pass") {
            self.step_done();
            return Ok(None);
        }
        let o = &opts[ans[0]];
        let cid = o["cid"].as_i64().unwrap();
        let gen = self.s.cards[cid as usize].gen;
        let a = self.s.active;
        self.push(vec![json!({"t": "play", "cid": cid, "player": a, "free": false, "phase": "start", "gen": gen})]);
        Ok(None)
    }

    /// カードの実行（601）。段階2-a: 通常のクリーチャー召喚（コスト軽減・進化・代替コストなどは無い札だけ）
    fn h_play(&mut self) -> R<Option<Value>> {
        let (cid, p, gen) = {
            let t = self.s.tasks.last().unwrap();
            (t["cid"].as_i64().unwrap(), t["player"].as_i64().unwrap(), t["gen"].as_i64().unwrap())
        };
        let (g, z) = {
            let c = &self.s.cards[cid as usize];
            (c.gen, c.zone.clone())
        };
        if g != gen || z == "bz" || z == "hold" {
            self.s.tasks.pop();
            return Ok(None);
        }
        if !self.permits(cid, "summon") || !self.permits(cid, "enter_bz") {
            self.s.tasks.pop();
            return Ok(None);
        }
        let has = |t: &Value, k: &str| t.get(k).is_some();
        // ササゲール（破壊してコスト軽減）: 候補なし → 空の sac と sac_done を残す
        if !has(self.s.tasks.last().unwrap(), "sac_done") {
            let t = self.s.tasks.last_mut().unwrap();
            if !has(t, "sac") {
                t["sac"] = json!([]);
            }
            t["sac_done"] = json!(true);
        }
        self.s.turn_counters.insert(format!("last_play_creature:{}", p), json!(1));
        if !has(self.s.tasks.last().unwrap(), "cost_may_done") {
            self.s.tasks.last_mut().unwrap()["cost_may_done"] = json!(true);
        }
        if !has(self.s.tasks.last().unwrap(), "paid_done") {
            let choices = self.mana_choices(cid, p, None, 32);
            if choices.is_empty() {
                self.s.tasks.pop();
                return Ok(None);
            }
            let opts: Vec<Value> = choices
                .iter()
                .map(|ch| {
                    let mut names: Vec<String> = ch.iter().map(|&c| self.s.cards[c as usize].defn.clone()).collect();
                    names.sort();
                    json!({"key": format!("mana:{}", names.join(",")), "cids": ch})
                })
                .collect();
            let ans = match self.ask(p, "pay_mana", opts.clone(), 1, 1) {
                Ask::Decision(d) => return Ok(Some(d)),
                Ask::Answer(x) => x,
            };
            for c in opts[ans[0]]["cids"].as_array().unwrap() {
                self.s.cards[c.as_i64().unwrap() as usize].tapped = true;
            }
            self.s.tasks.last_mut().unwrap()["paid_done"] = json!(true);
        }
        self.s.tasks.pop();
        // 保留状態へ（409, 601.1b）。gen は変えない
        let from_zone = self.s.cards[cid as usize].zone.clone();
        let owner = self.s.cards[cid as usize].owner as usize;
        let sh = self.shared(&from_zone);
        {
            let lst = self.s.zones.get_mut(&from_zone).unwrap();
            let idx = if sh { 0 } else { owner };
            if let Some(pos) = lst[idx].iter().position(|&x| x == cid) {
                lst[idx].remove(pos);
            }
        }
        self.note_deck(cid);
        self.s.cards[cid as usize].zone = "hold".to_string();
        self.s.hold.push(cid);
        let r = self.refv(cid);
        let ev = json!({"ev": "move", "subject": r, "from": from_zone, "to": "bz", "reason": "summon", "controller": p, "unpaid": false});
        let t = self.ev_task(vec![ev]);
        self.push(vec![t]);
        Ok(None)
    }

    fn play_options(&self, p: i64) -> Vec<Value> {
        let mut out = vec![];
        for o in self.distinct_hand_options(p, "play") {
            let cid = o["cid"].as_i64().unwrap();
            if self.can_play(cid, p) {
                out.push(json!({"key": o["key"], "cid": cid, "name": self.def(cid).name}));
            }
        }
        // マナ・墓地からの召喚は、許可を与える能力が無いので plain では出ない
        out
    }

    fn can_play(&self, cid: i64, p: i64) -> bool {
        if !self.permits(cid, "summon") || !self.permits(cid, "enter_bz") {
            return false;
        }
        !self.mana_choices(cid, p, None, 1).is_empty()
    }

    fn st_attack(&mut self) -> R<Option<Value>> {
        let a = self.s.active;
        let turn = self.s.turn;
        let mut opts: Vec<Value> = vec![];
        for c in self.bz_tops(Some(a)) {
            let k = &self.s.cards[c as usize];
            if k.tapped || (k.entered_turn == turn && !self.permits(c, "attack_summoning_sick")) {
                continue;
            }
            let dfn = k.defn.clone();
            if self.permits(c, "attack_player") {
                opts.push(json!({"key": format!("attack:{}:player", dfn), "cid": c, "target": "player"}));
            }
            for tc in self.bz_tops(Some(1 - a)) {
                if self.s.cards[tc as usize].tapped && self.permits(c, "attack_creature") && self.permits(tc, "be_attacked") {
                    opts.push(json!({"key": format!("attack:{}:{}", dfn, self.s.cards[tc as usize].defn), "cid": c, "target": self.refv(tc)}));
                }
            }
        }
        opts.push(json!({"key": "pass"}));
        let ans = match self.ask(a, "attack", opts.clone(), 1, 1) {
            Ask::Decision(d) => return Ok(Some(d)),
            Ask::Answer(x) => x,
        };
        let o = opts[ans[0]].clone();
        if o["key"] == json!("pass") {
            self.step_done();
            return Ok(None);
        }
        self.s.turn_counters.insert("attacked".into(), json!(true));
        let att = self.refv(o["cid"].as_i64().unwrap());
        self.push(vec![json!({"t": "attack", "attacker": att, "target": o["target"], "phase": 0, "cp": true})]);
        Ok(None)
    }

    fn window(&mut self, inner: Vec<Value>) -> Vec<Value> {
        self.s.seq += 1;
        let w = self.s.seq;
        let mut v = vec![json!({"t": "open_win", "win": w})];
        v.extend(inner);
        v.push(json!({"t": "resolve_pending", "win": w, "only_st": false}));
        v.push(json!({"t": "close_win"}));
        v
    }

    fn decl(player: i64, window: &str, rec: &Value) -> Value {
        json!({"t": "declare", "player": player, "window": window, "ctx": rec})
    }

    fn tset(&mut self, k: &str, v: Value) {
        self.s.tasks.last_mut().unwrap()[k] = v;
    }

    /// 攻撃ステップのサブステップ（506〜510）。ブロッカー・バトル置換・使用宣言は能力を持つカードだけなので plain では空振り
    fn h_attack(&mut self) -> R<Option<Value>> {
        let a = self.s.active;
        let (att, target, ph) = {
            let t = self.s.tasks.last().unwrap();
            (t["attacker"].clone(), t["target"].clone(), t["phase"].as_i64().unwrap())
        };
        if self.s.skip_rest {
            return uns("skip_rest");
        }
        if ph == 0 {
            self.tset("phase", json!(1));
            let n = self.s.turn_counters.get("attack_no").and_then(|v| v.as_i64()).unwrap_or(0) + 1;
            self.s.turn_counters.insert("attack_no".into(), json!(n));
            self.tset("ano", json!(n));
            self.s.turn_counters.insert("current_attack".into(), json!(n));
            self.s.cards[att[0].as_i64().unwrap() as usize].tapped = true;
            let rec = json!({"ev": "attack", "subject": att, "target": target, "controller": a});
            let e = self.ev_task(vec![rec.clone()]);
            self.push(vec![e, Self::decl(a, "attack", &rec)]);
            return Ok(None);
        }
        if ph == 1 {
            self.tset("phase", json!(2));
            if self.alive(&att) {
                let rec = json!({"ev": "attack", "subject": att, "target": target, "controller": a});
                self.push(vec![Self::decl(1 - a, "attack", &rec)]);
            }
            return Ok(None);
        }
        if ph < 5 && (!self.alive(&att) || (target != json!("player") && !self.alive(&target))) {
            self.tset("phase", json!(5));
            return Ok(None);
        }
        if ph == 2 {
            // 507 ブロッククリーチャー指定
            let attc = att[0].as_i64().unwrap();
            let blockers: Vec<i64> = self.bz_tops(Some(1 - a)).into_iter().filter(|&c| {
                !self.s.cards[c as usize].tapped && self.permits(c, "block") && self.permits(attc, "be_blocked")
                    && json!([c, self.s.cards[c as usize].gen]) != target
            }).collect();
            let guards: Vec<i64> = if target == json!("player") { vec![] } else {
                self.bz_tops(Some(1 - a)).into_iter().filter(|&c| {
                    !self.s.cards[c as usize].tapped && json!([c, self.s.cards[c as usize].gen]) != target && self.permits(c, "guardman")
                }).collect()
            };
            let mut opts: Vec<Value> = blockers.iter().map(|&c| self.card_option(c, None)).collect();
            for &c in &guards {
                opts.push(self.card_option(c, Some(format!("guard:{}", self.s.cards[c as usize].defn))));
            }
            opts.push(json!({"key": "no_block"}));
            let ans = match self.ask(1 - a, "block", opts.clone(), 1, 1) {
                Ask::Decision(d) => return Ok(Some(d)),
                Ask::Answer(x) => x,
            };
            self.tset("phase", json!(3));
            let o = opts[ans[0]].clone();
            if o["key"] != json!("no_block") {
                let c = o["cid"].as_i64().unwrap();
                self.s.cards[c as usize].tapped = true;
                let r = self.refv(c);
                self.tset("target", r.clone());
                if o["key"].as_str().unwrap().starts_with("guard:") {
                    return Ok(None);
                }
                self.tset("blocked", json!(true));
                let rec = json!({"ev": "block", "subject": r, "attacker": att, "controller": 1 - a});
                let e = self.ev_task(vec![rec.clone()]);
                self.push(vec![e, Self::decl(a, "block", &rec), Self::decl(1 - a, "block", &rec)]);
            }
            return Ok(None);
        }
        if ph == 3 {
            self.tset("phase", json!(4));
            if target != json!("player") {
                if self.s.tasks.last().unwrap().get("subbed").is_none() {
                    self.tset("subbed", json!([]));
                }
                let bs = json!({"ev": "battle_start", "subject": att, "opponent": target, "controller": a});
                let e = self.ev_task(vec![bs]);
                let mut ts = self.window(vec![e]);
                ts.push(json!({"t": "battle_run", "att": att, "tgt": target}));
                self.push(ts);
            }
            return Ok(None);
        }
        if ph == 4 {
            // 509 ダイレクトアタック: 複数のブレイカー能力ならどれを使うか選ぶ
            let mut n = 1;
            if target == json!("player") && !self.zl("shield", 1 - a).is_empty() {
                let counts = self.break_opts(att[0].as_i64().unwrap());
                let opts: Vec<Value> = counts.iter().map(|n| json!({"key": format!("breaks:{}", n)})).collect();
                let ans = match self.ask(a, "choose_breaker", opts, 1, 1) {
                    Ask::Decision(d) => return Ok(Some(d)),
                    Ask::Answer(x) => x,
                };
                n = counts[ans[0]];
            }
            self.tset("phase", json!(5));
            if target == json!("player") {
                if !self.zl("shield", 1 - a).is_empty() {
                    if n > 0 {
                        self.push(vec![json!({"t": "break", "victim": 1 - a, "by": a, "count": n, "phase": 0, "in_effect": false, "breaker": att})]);
                    }
                } else {
                    self.game_lose(1 - a, "direct_attack");
                }
            }
            return Ok(None);
        }
        let end_fired = self.s.tasks.last().unwrap().get("end_fired").is_some();
        if !end_fired && self.s.result.is_none() {
            self.tset("end_fired", json!(true));
            let ano = self.s.tasks.last().unwrap().get("ano").cloned().unwrap_or(Value::Null);
            let broke = self.s.turn_counters.get(&format!("broke_in:{}", att[0].as_i64().unwrap())).cloned() == Some(ano);
            let e = self.ev_task(vec![json!({"ev": "attack_end", "subject": att, "target": target, "controller": a, "broke": broke, "blocked": self.s.tasks.last().unwrap().get("blocked").and_then(|v| v.as_bool()).unwrap_or(false)})]);
            self.push(vec![e]);
            return Ok(None);
        }
        self.s.tasks.pop();
        if !self.s.continuous.is_empty() || !self.s.delayed.is_empty() {
            return uns("expire during_attack");
        }
        Ok(None)
    }

    /// 101.4 / 605.1: ターン・プレイヤーの待機中の効果から順に、1つずつ解決する（S・トリガー系・遅延は plain に無い）
    fn h_resolve_pending(&mut self) -> R<Option<Value>> {
        let (win, only_st) = {
            let t = self.s.tasks.last().unwrap();
            (t["win"].clone(), t["only_st"].as_bool().unwrap_or(false))
        };
        let here: Vec<Value> = self.s.pending.iter().filter(|p| p["win"] == win).cloned().collect();
        if here.iter().any(|p| p["kind"] != json!("normal")) {
            return uns("pending kind");
        }
        let active = self.s.active;
        let mine: Vec<Value> = here.iter().filter(|p| p["controller"] == json!(active)).cloned().collect();
        let pool: Vec<Value> = if only_st { vec![] } else if !mine.is_empty() { mine } else { here };
        if pool.is_empty() {
            self.s.tasks.pop();
            return Ok(None);
        }
        let player = pool[0]["controller"].as_i64().unwrap();
        let opts: Vec<Value> = pool
            .iter()
            .map(|p| json!({"key": format!("pending:{}:{}:{}", p["kind"].as_str().unwrap(), p["defn"].as_str().unwrap(), p["ab"]), "pid": p["pid"]}))
            .collect();
        let ans = match self.ask(player, "order_pending", opts.clone(), 1, 1) {
            Ask::Decision(d) => return Ok(Some(d)),
            Ask::Answer(x) => x,
        };
        let pid = opts[ans[0]]["pid"].clone();
        let idx = self.s.pending.iter().position(|p| p["pid"] == pid).unwrap();
        let p = self.s.pending.remove(idx);
        let defn = p["defn"].as_str().unwrap().to_string();
        let ab = self.rules.cards[&defn].abil[p["ab"].as_i64().unwrap() as usize].clone();
        let eff = ab["effect"].clone();
        self.push(vec![json!({"t": "effect", "ops": eff, "pc": 0, "env": p["env"], "os": {}})]);
        Ok(None)
    }

    /// 効果の解釈（ops の1つずつ）。段階2-d の範囲: draw / may / tap・untap（自身）
    fn h_effect(&mut self) -> R<Option<Value>> {
        let (pc, n) = {
            let t = self.s.tasks.last().unwrap();
            (t["pc"].as_i64().unwrap() as usize, t["ops"].as_array().unwrap().len())
        };
        if pc >= n || self.s.result.is_some() {
            self.s.tasks.pop();
            return Ok(None);
        }
        let (op, env) = {
            let t = self.s.tasks.last().unwrap();
            (t["ops"][pc].clone(), t["env"].clone())
        };
        let mut deferred = false;
        match op["op"].as_str().unwrap_or("") {
            "draw" => {
                let cnt = op.get("count").and_then(|v| v.as_i64()).unwrap_or(1);
                let you = env["you"].as_i64().unwrap();
                let ps: Vec<i64> = match op.get("player").and_then(|v| v.as_str()).unwrap_or("you") {
                    "you" => vec![you],
                    "opp" => vec![1 - you],
                    "each" => {
                        let a = self.s.active;
                        vec![a, 1 - a]
                    }
                    _ => return uns("draw player"),
                };
                let mut ch = vec![];
                for p in ps {
                    for _ in 0..cnt {
                        ch.push(self.ev_task(vec![json!({"ev": "draw", "player": p})]));
                    }
                }
                self.defer(ch);
                deferred = true;
            }
            "may" => {
                if op.get("label").is_some() || op.get("player").is_some() || op.get("else").is_some() {
                    return uns("may options");
                }
                let you = env["you"].as_i64().unwrap();
                let ans = match self.ask(you, "yes_no", vec![json!({"key": "yes"}), json!({"key": "no"})], 1, 1) {
                    Ask::Decision(d) => return Ok(Some(d)),
                    Ask::Answer(x) => x,
                };
                if ans[0] == 0 {
                    let child = json!({"t": "effect", "ops": op["body"], "pc": 0, "env": env, "os": {}});
                    self.defer(vec![child]);
                    deferred = true;
                }
            }
            k @ ("tap" | "untap") => {
                if op.get("no_untap_next").is_some() {
                    return uns("no_untap_next");
                }
                let cids = match self.select(&op["select"], &env)? {
                    Ok(c) => c,
                    Err(d) => return Ok(Some(d)),
                };
                if !cids.is_empty() {
                    let evs: Vec<Value> = cids.iter().map(|&c| json!({"ev": k, "subject": self.refv(c)})).collect();
                    let e = self.ev_task(evs);
                    self.defer(vec![e]);
                    deferred = true;
                }
            }
            "move" => {
                let to = op["to"].as_str().unwrap_or("");
                if !["hand", "graveyard", "mana", "deck"].contains(&to) {
                    return uns(format!("move to {}", to));
                }
                let cids = match self.select(&op["select"], &env)? {
                    Ok(c) => c,
                    Err(d) => return Ok(Some(d)),
                };
                let pos = op.get("position").and_then(|v| v.as_str()).unwrap_or("top");
                let evs: Vec<Value> = cids
                    .iter()
                    .map(|&c| json!({"ev": "move", "subject": self.refv(c), "to": to, "reason": op["reason"], "position": pos}))
                    .collect();
                if !evs.is_empty() {
                    let e = self.ev_task_env(evs, &env);
                    self.defer(vec![e]);
                    deferred = true;
                }
            }
            "shuffle" => {
                let you = env["you"].as_i64().unwrap();
                let p = match op.get("player").and_then(|v| v.as_str()).unwrap_or("you") {
                    "you" => you,
                    "opp" => 1 - you,
                    _ => return uns("shuffle player"),
                };
                let n = self.s.pub_len();
                let turn = self.s.turn;
                self.s.r#pub.push(json!({"n": n, "turn": turn, "kind": "shuffle", "viewers": [0, 1], "player": p, "zone": "deck"}));
                let len = self.s.zones["deck"][p as usize].len();
                for i in (1..len).rev() {
                    let j = self.s.rng_below((i + 1) as u64) as usize;
                    self.s.zones.get_mut("deck").unwrap()[p as usize].swap(i, j);
                }
            }
            other => return uns(format!("op {}", other)),
        }
        if !deferred {
            let t = self.s.tasks.last_mut().unwrap();
            t["pc"] = json!(pc as i64 + 1);
            t["os"] = json!({});
        }
        Ok(None)
    }

    /// t の次の op を children が終わった後に回す（書かれた順に解決する 605.2c）
    fn defer(&mut self, children: Vec<Value>) {
        let t = self.s.tasks.last_mut().unwrap();
        t["pc"] = json!(t["pc"].as_i64().unwrap() + 1);
        t["os"] = json!({});
        self.push(children);
    }

    /// 誘発チェック（Python 版 _collect_triggers の、バトルゾーンの「出た時」「攻撃する時」だけを扱う版）
    fn collect_triggers(&mut self, rec: &mut Value) {
        self.s.ev_seq += 1;
        rec["_eid"] = json!(self.s.ev_seq);
        let win = self.s.windows.last().copied().unwrap_or(0);
        for src in self.bz_tops(None) {
            let defn = self.s.cards[src as usize].defn.clone();
            let ctrl = self.s.cards[src as usize].controller;
            let n = self.rules.cards[&defn].abil.len();
            for i in 0..n {
                let ab = self.rules.cards[&defn].abil[i].clone();
                if ab["kind"] != json!("trigger") {
                    continue;
                }
                let w = &ab["when"];
                if w["event"] != rec["ev"] {
                    continue;
                }
                if let Some(to) = w.get("to") {
                    if rec.get("to") != Some(to) {
                        continue;
                    }
                }
                // subject: self
                if rec.get("subject").map_or(true, |s| s[0].as_i64() != Some(src)) {
                    continue;
                }
                self.s.seq += 1;
                let sref = self.refv(src);
                let p = json!({"pid": self.s.seq, "kind": "normal", "win": win, "controller": ctrl, "src": sref, "defn": defn, "ab": i,
                    "env": {"you": ctrl, "self": sref, "event": rec.clone(), "vars": {}}});
                self.s.pending.push(p);
            }
        }
    }

    /// chars の JSON（lki に載せる。Python 版 _chars_calc の、能力が自身への単純な常在型だけの札の結果）
    fn chars_json(&self, cid: i64) -> Value {
        let d = self.def(cid);
        let in_bz = self.s.cards[cid as usize].zone == "bz";
        let (allow, deny, bo): (Vec<String>, Vec<String>, Vec<i64>) =
            if in_bz { (d.allow.clone(), d.deny.clone(), d.breaks.clone()) } else { (vec![], vec![], vec![]) };
        let breaks = bo.iter().copied().max().unwrap_or(1).max(1);
        let mut kw = d.keywords.clone();
        kw.sort();
        kw.dedup();
        json!({"power": d.power, "cost": d.cost, "civs": d.civs, "types": d.types, "races": d.races, "keywords": kw,
            "name": d.name, "names": [d.name], "allow": allow, "deny": deny, "require": [], "breaks": breaks, "break_opts": bo,
            "breaks_add": 0, "pay_cost": d.cost, "sac_reduce": 0, "opt_reduce": null, "cost_may": [], "no_leave": [],
            "must_be_attacked": false, "battle_indestructible": false, "battle_indestructible_filters": [],
            "win_all_battles": false, "indestructible": false, "crystal_soul": 0})
    }

    fn game_lose(&mut self, loser: i64, reason: &str) {
        if self.s.result.is_none() {
            self.s.result = Some(json!({"winner": 1 - loser, "reason": reason, "turn": self.s.turn}));
        }
    }

    /// バトル（701.13）: plain はパワーだけで勝敗が決まる
    fn battle(&mut self, x: &Value, y: &Value) -> R<()> {
        let (xc, yc) = (x[0].as_i64().unwrap(), y[0].as_i64().unwrap());
        let (px, py) = (self.def(xc).power, self.def(yc).power);
        let mut losers: Vec<&Value> = vec![];
        if px <= py {
            losers.push(x);
        }
        if py <= px {
            losers.push(y);
        }
        let slay: Vec<Value> = losers
            .iter()
            .filter(|r| self.permits(r[0].as_i64().unwrap(), "slayer"))
            .map(|r| json!([r, if *r == x { y } else { x }]))
            .collect();
        let mut evs: Vec<Value> = losers
            .iter()
            .map(|r| json!({"ev": "move", "subject": r, "to": "graveyard", "reason": "destroy", "battle": true}))
            .collect();
        for r in [x, y] {
            if !losers.contains(&r) {
                let c = self.s.cards[r[0].as_i64().unwrap() as usize].controller;
                evs.push(json!({"ev": "battle_win", "subject": r, "controller": c}));
            }
        }
        let e = self.ev_task(evs);
        let mut ts = self.window(vec![e]);
        if !slay.is_empty() {
            ts.extend(self.window(vec![json!({"t": "slayer", "pairs": slay})]));
        }
        let (cx, cy) = (self.s.cards[xc as usize].controller, self.s.cards[yc as usize].controller);
        ts.push(self.ev_task(vec![
            json!({"ev": "battle_end", "subject": x, "opponent": y, "controller": cx}),
            json!({"ev": "battle_end", "subject": y, "opponent": x, "controller": cy}),
        ]));
        self.push(ts);
        Ok(())
    }

    fn card_option(&self, cid: i64, key: Option<String>) -> Value {
        let c = &self.s.cards[cid as usize];
        let hidden = c.zone == "shield" || c.zone == "deck";
        let k = key.unwrap_or_else(|| if hidden { c.zone.clone() } else { format!("{}:{}:{}", c.zone, c.defn, c.tapped as i32) });
        json!({"cid": cid, "key": k, "name": if hidden { "?".to_string() } else { self.def(cid).name.clone() }})
    }

    /// ブレイク（509.3〜509.5）。置換・S・トリガー・S・バックは能力を持つカードだけなので plain では空振り
    fn h_break(&mut self) -> R<Option<Value>> {
        let (victim, by, ph) = {
            let t = self.s.tasks.last().unwrap();
            (t["victim"].as_i64().unwrap(), t["by"].as_i64().unwrap(), t["phase"].as_i64().unwrap())
        };
        if ph == 0 {
            let shields = self.zl("shield", victim).clone();
            let n = (self.s.tasks.last().unwrap()["count"].as_i64().unwrap() as usize).min(shields.len());
            let opts: Vec<Value> = shields.iter().map(|&c| json!({"cid": c, "key": "shield", "name": "?"})).collect();
            let ans = match self.ask(by, "choose_shields", opts, n, n) {
                Ask::Decision(d) => return Ok(Some(d)),
                Ask::Answer(x) => x,
            };
            let chosen: Vec<i64> = ans.iter().map(|&i| shields[i]).collect();
            self.tset("chosen", json!(chosen));
            self.tset("phase", json!(1));
            return Ok(None);
        }
        if ph == 1 {
            let t = self.s.tasks.last().unwrap();
            if t.get("brk_done").is_none() {
                // ブレイクの置換の諮問: 候補なし。印だけ残す
                let chosen = t["chosen"].clone();
                let n = chosen.as_array().unwrap().len();
                let t = self.s.tasks.last_mut().unwrap();
                t["brk_list"] = chosen;
                t["brk_i"] = json!(n);
                t["brk_p"] = json!(0);
                t["brk_cancelled"] = json!([]);
                t["brk_done"] = json!(true);
            }
            let ch: Vec<i64> = self.s.tasks.last().unwrap()["chosen"].as_array().unwrap().iter().map(|v| v.as_i64().unwrap()).collect();
            if ch.iter().any(|&c| self.permits(c, "s_trigger")) {
                return uns("s_trigger");
            }
            self.tset("declared", json!([]));
            self.tset("phase", json!(2));
            return Ok(None);
        }
        // phase 2: S・バックなし → 手札へ
        let tk = self.s.tasks.pop().unwrap();
        let chosen: Vec<i64> = tk["chosen"].as_array().unwrap().iter().map(|v| v.as_i64().unwrap()).filter(|&c| self.s.cards[c as usize].zone == "shield").collect();
        let reason = tk.get("reason").and_then(|v| v.as_str()).unwrap_or("break").to_string();
        let mut seq = vec![self.ev_task(chosen.iter().map(|&c| json!({"ev": "move", "subject": self.refv(c), "to": "hand", "reason": reason})).collect())];
        seq.push(json!({"t": "enqueue_st", "cids": tk["declared"], "player": victim}));
        if !chosen.is_empty() {
            let mut ev = json!({"ev": "break", "player": victim, "count": chosen.len()});
            let br = tk.get("breaker").cloned().unwrap_or(Value::Null);
            if !br.is_null() && self.alive(&br) {
                ev["subject"] = br.clone();
                let cur = self.s.turn_counters.get("current_attack").cloned().unwrap_or(json!(0));
                self.s.turn_counters.insert(format!("broke_in:{}", br[0].as_i64().unwrap()), cur);
            }
            seq.push(self.ev_task(vec![ev]));
        }
        self.push(seq);
        Ok(None)
    }

    fn st_end(&mut self) -> R<Option<Value>> {
        let sub = self.s.tasks.last().unwrap()["sub"].as_i64().unwrap();
        if sub == 0 {
            self.s.tasks.last_mut().unwrap()["sub"] = json!(1);
            let t = self.ev_task(vec![json!({"ev": "turn_end", "player": self.s.active})]);
            self.push(vec![t]);
            return Ok(None);
        }
        if !self.s.continuous.is_empty() || !self.s.delayed.is_empty() {
            return uns("expire");
        }
        self.step_done();
        Ok(None)
    }

    // ---- マナの支払いの組（Python 版 _mana_choices と同じ列挙順） ----
    pub fn mana_choices(&self, cid: i64, p: i64, cost: Option<i64>, limit: usize) -> Vec<Vec<i64>> {
        let d = self.def(cid);
        let eff = cost.unwrap_or(d.cost).max(0);
        let need: Vec<String> = d.civs.clone();
        if eff == 0 && need.is_empty() {
            return vec![vec![]];
        }
        let untapped: Vec<i64> = self.zl("mana", p).iter().copied().filter(|&c| !self.s.cards[c as usize].tapped).collect();
        let total_mana: i64 = untapped.iter().map(|&c| self.def(c).mana).sum();
        if (untapped.len() as i64) < d.civs.len() as i64 || total_mana < eff {
            return vec![];
        }
        let mut groups: BTreeMap<(String, bool, Vec<String>), Vec<i64>> = BTreeMap::new();
        for &c in &untapped {
            let k = &self.s.cards[c as usize];
            let civkey: Vec<String> = if k.face_down {
                vec![]
            } else {
                let mut v = self.def(c).civs.clone();
                v.sort();
                v
            };
            groups.entry((k.defn.clone(), k.face_down, civkey)).or_default().push(c);
        }
        let names: Vec<&(String, bool, Vec<String>)> = groups.keys().collect();
        let mana: Vec<i64> = names.iter().map(|n| self.rules.cards[&n.0].mana).collect();
        let mut out: Vec<Vec<i64>> = vec![];

        fn civ_ok(names: &[&(String, bool, Vec<String>)], cnt: &[i64], need: &[String]) -> bool {
            let mut civsets: Vec<&Vec<String>> = vec![];
            for (n, &k) in names.iter().zip(cnt.iter()) {
                for _ in 0..k {
                    civsets.push(&n.2);
                }
            }
            fn rec(j: usize, need: &[String], civsets: &[&Vec<String>], used: &mut Vec<bool>) -> bool {
                if j == need.len() {
                    return true;
                }
                for i in 0..civsets.len() {
                    if !used[i] && civsets[i].contains(&need[j]) {
                        used[i] = true;
                        if rec(j + 1, need, civsets, used) {
                            return true;
                        }
                        used[i] = false;
                    }
                }
                false
            }
            let mut used = vec![false; civsets.len()];
            rec(0, need, &civsets, &mut used)
        }

        #[allow(clippy::too_many_arguments)]
        fn dfs(i: usize, cnt: &mut Vec<i64>, total: i64, zeros: i64, eff: i64, names: &[&(String, bool, Vec<String>)], mana: &[i64],
               groups: &BTreeMap<(String, bool, Vec<String>), Vec<i64>>, need: &[String], limit: usize, out: &mut Vec<Vec<i64>>) {
            if out.len() >= limit {
                return;
            }
            if i == names.len() {
                if total == eff && civ_ok(names, cnt, need) {
                    let mut v = vec![];
                    for (n, &k) in names.iter().zip(cnt.iter()) {
                        v.extend(groups[*n].iter().take(k as usize).copied());
                    }
                    out.push(v);
                }
                return;
            }
            let cap = groups[names[i]].len() as i64;
            let bound = if mana[i] != 0 { (eff - total).div_euclid(mana[i]) } else { need.len() as i64 - zeros };
            let mut k = cap.min(bound);
            while k >= 0 {
                cnt.push(k);
                dfs(i + 1, cnt, total + k * mana[i], zeros + if mana[i] == 0 { k } else { 0 }, eff, names, mana, groups, need, limit, out);
                cnt.pop();
                k -= 1;
            }
        }

        fn floor_dfs(i: usize, cnt: &mut Vec<i64>, left: i64, names: &[&(String, bool, Vec<String>)],
                     groups: &BTreeMap<(String, bool, Vec<String>), Vec<i64>>, need: &[String], limit: usize, out: &mut Vec<Vec<i64>>) {
            if out.len() >= limit {
                return;
            }
            if i == names.len() {
                if left == 0 && civ_ok(names, cnt, need) {
                    let mut v = vec![];
                    for (n, &k) in names.iter().zip(cnt.iter()) {
                        v.extend(groups[*n].iter().take(k as usize).copied());
                    }
                    out.push(v);
                }
                return;
            }
            let mut k = (groups[names[i]].len() as i64).min(left);
            while k >= 0 {
                cnt.push(k);
                floor_dfs(i + 1, cnt, left - k, names, groups, need, limit, out);
                cnt.pop();
                k -= 1;
            }
        }

        let mut cnt = vec![];
        if (eff as usize) < need.len() {
            floor_dfs(0, &mut cnt, need.len() as i64, &names, &groups, &need, limit, &mut out);
        } else {
            dfs(0, &mut cnt, 0, 0, eff, &names, &mana, &groups, &need, limit, &mut out);
        }
        out
    }

    // ---- イベント ----
    fn h_event(&mut self) -> R<Option<Value>> {
        // 置換効果・G・リンクの離脱置換は、能力を持つカードだけが起こす。plain では何も起きない。
        let t = self.s.tasks.pop().unwrap();
        let evs: Vec<Value> = t["evs"].as_array().unwrap().clone();
        self.apply_batch(evs)?;
        Ok(None)
    }

    fn apply_batch(&mut self, evs: Vec<Value>) -> R<()> {
        if !evs.is_empty() && !evs.iter().any(|e| e.get("sba").and_then(|v| v.as_bool()).unwrap_or(false)) {
            self.s.sba_held.clear();
        }
        let mut records: Vec<Value> = vec![];
        for ev in &evs {
            records.extend(self.apply_one(ev)?);
        }
        for r in &records {
            if r["ev"] == json!("break") {
                let k = format!("broken:{}", r["player"].as_i64().unwrap());
                let n = self.s.turn_counters.get(&k).and_then(|v| v.as_i64()).unwrap_or(0) + r.get("count").and_then(|v| v.as_i64()).unwrap_or(0);
                self.s.turn_counters.insert(k, json!(n));
            }
        }
        self.record_history(&mut records);
        self.sba()?;
        for r in records.iter_mut() {
            self.collect_triggers(r);
        }
        Ok(())
    }

    fn hist_bump(&mut self, kind: &str, player: i64, n: i64) -> i64 {
        let k = format!("hist:{}:{}", kind, player);
        let v = self.s.turn_counters.get(&k).and_then(|v| v.as_i64()).unwrap_or(0) + n;
        self.s.turn_counters.insert(k, json!(v));
        v
    }

    fn push_list(&mut self, k: String, v: i64) {
        let mut l = self.s.turn_counters.get(&k).and_then(|v| v.as_array().cloned()).unwrap_or_default();
        l.push(json!(v));
        self.s.turn_counters.insert(k, Value::Array(l));
    }

    /// 履歴カウンタ（Python 版 _record_history。ここで扱うのは plain の対戦で起きる種類だけ）
    fn record_history(&mut self, records: &mut [Value]) {
        for rec in records.iter_mut() {
            match rec["ev"].as_str().unwrap_or("") {
                "move" => {
                    let ctrl = if rec["lki"].is_null() { rec["controller"].as_i64().unwrap() } else { rec["lki"]["controller"].as_i64().unwrap() };
                    let rc = rec["controller"].as_i64().unwrap();
                    let (frm, to) = (rec["from"].as_str().unwrap_or("").to_string(), rec["to"].as_str().unwrap_or("").to_string());
                    let (frm, to) = (frm.as_str(), to.as_str());
                    if to == "shield" {
                        self.hist_bump("shield_put", rc, 1);
                    }
                    if frm == "shield" && to != "shield" {
                        self.hist_bump("shield_left", ctrl, 1);
                    }
                    if to == "mana" {
                        let n = self.hist_bump("mana_put", rc, 1);
                        rec["ord"] = json!({"mana_put": n});
                    }
                    if to == "bz" {
                        let n = self.hist_bump("enter", rc, 1);
                        rec["ord"] = json!({"enter": n});
                        if rec.get("unpaid").and_then(|v| v.as_bool()).unwrap_or(false) {
                            self.hist_bump("enter_unpaid", rc, 1);
                        }
                    }
                    if frm == "bz" && to != "bz" {
                        self.hist_bump("leave", ctrl, 1);
                        if to == "graveyard" && rec["reason"] == json!("destroy") {
                            self.hist_bump("destroyed", ctrl, 1);
                        }
                    }
                    if to == "graveyard" && rec["reason"] == json!("discard") {
                        self.hist_bump("discard", ctrl, 1);
                    }
                }
                "summon" => {
                    let n = self.hist_bump("summon", rec["controller"].as_i64().unwrap(), 1);
                    rec["ord"] = json!({"summon": n});
                }
                "draw" => {
                    let n = self.hist_bump("draw", rec["player"].as_i64().unwrap(), 1);
                    rec["ord"] = json!({"draw": n});
                }
                "break" => {
                    let cnt = rec.get("count").and_then(|v| v.as_i64()).unwrap_or(1);
                    self.hist_bump("broken", rec["player"].as_i64().unwrap(), cnt);
                    if let Some(s) = rec.get("subject") {
                        if !s.is_null() {
                            let k = format!("hist:broke_by:{}", s[0].as_i64().unwrap());
                            let v = self.s.turn_counters.get(&k).and_then(|v| v.as_i64()).unwrap_or(0) + cnt;
                            self.s.turn_counters.insert(k, json!(v));
                        }
                    }
                }
                "attack" => {
                    let a = rec["controller"].as_i64().unwrap();
                    let att = rec["subject"][0].as_i64().unwrap();
                    let n = self.hist_bump("attack", a, 1);
                    self.push_list(format!("hist:attackers:{}", a), att);
                    let k = format!("hist:attack_by:{}", att);
                    let v = self.s.turn_counters.get(&k).and_then(|v| v.as_i64()).unwrap_or(0) + 1;
                    self.s.turn_counters.insert(k, json!(v));
                    rec["ord"] = json!({"attack": n, "attack_by": v});
                    if let Some(tg) = rec["target"].as_array() {
                        let k2 = format!("hist:attack_on:{}", tg[0].as_i64().unwrap());
                        let v = self.s.turn_counters.get(&k2).and_then(|v| v.as_i64()).unwrap_or(0) + 1;
                        self.s.turn_counters.insert(k2, json!(v));
                    }
                }
                "block" => { self.hist_bump("block", rec["controller"].as_i64().unwrap(), 1); }
                "tap" => { self.hist_bump("tap", rec["controller"].as_i64().unwrap(), 1); }
                "untap" => { self.hist_bump("untap", rec["controller"].as_i64().unwrap(), 1); }
                _ => {}
            }
        }
    }

    /// 適用して、生まれたレコードを返す
    fn apply_one(&mut self, ev: &Value) -> R<Vec<Value>> {
        let kind = ev["ev"].as_str().unwrap_or("");
        match kind {
            "draw" => {
                let p = ev["player"].as_i64().unwrap();
                let deck = &self.s.zones["deck"][p as usize];
                if deck.is_empty() {
                    return Ok(vec![]);
                }
                let cid = deck[0];
                self.raw_move(cid, "hand", "top", None);
                self.s.cards[cid as usize].drawn_turn = self.s.turn;
                let k = format!("drew:{}", p);
                let n = self.s.turn_counters.get(&k).and_then(|v| v.as_i64()).unwrap_or(0) + 1;
                self.s.turn_counters.insert(k, json!(n));
                let r = self.refv(cid);
                Ok(vec![
                    json!({"ev": "draw", "player": p, "subject": r}),
                    json!({"ev": "move", "subject": r, "lki": null, "from": "deck", "to": "hand", "reason": "draw", "controller": p}),
                ])
            }
            "tap" | "untap" => {
                if !self.alive(&ev["subject"]) {
                    return Ok(vec![]);
                }
                let cid = ev["subject"][0].as_i64().unwrap();
                let c = &mut self.s.cards[cid as usize];
                if c.tapped == (kind == "tap") {
                    return Ok(vec![]);
                }
                c.tapped = kind == "tap";
                Ok(vec![json!({"ev": kind, "subject": ev["subject"], "controller": c.controller})])
            }
            "move" => {
                if !self.alive(&ev["subject"]) {
                    return Ok(vec![]);
                }
                let cid = ev["subject"][0].as_i64().unwrap();
                let to = ev["to"].as_str().unwrap_or("");
                let czone = self.s.cards[cid as usize].zone.clone();
                let from = if czone == "hold" { ev["from"].as_str().unwrap_or("").to_string() } else { czone.clone() };
                let reason = ev.get("reason").and_then(|v| v.as_str()).unwrap_or("");
                let ctl_before = self.s.cards[cid as usize].controller;
                let (tapped_before, gen_before, face_before) = {
                    let c = &self.s.cards[cid as usize];
                    (c.tapped, c.gen, c.face)
                };
                let chars_before = self.chars_json(cid);
                let defn_before = self.s.cards[cid as usize].defn.clone();
                let summon_hold = to == "bz" && czone == "hold" && reason == "summon";
                if (to == "bz" && !summon_hold) || (czone == "hold" && !summon_hold) {
                    return uns(format!("move {}→{}", from, to));
                }
                let ctl = if summon_hold { Some(ev["controller"].as_i64().unwrap()) } else { None };
                let pos = ev.get("position").and_then(|v| v.as_str()).unwrap_or("top").to_string();
                self.raw_move(cid, to, &pos, ctl);
                let after = self.s.cards[cid as usize].controller;
                let mut out = vec![json!({"ev": "move", "subject": self.refv(cid), "lki": {"defn": defn_before, "face": face_before, "controller": ctl_before, "zone": from, "tapped": tapped_before,
                        "chars": chars_before, "ref": [cid, gen_before]}, "from": from, "to": to,
                    "reason": reason, "controller": after})];
                if ev.get("unpaid").and_then(|v| v.as_bool()).unwrap_or(false) {
                    out[0]["unpaid"] = json!(true);
                }
                for k in ["cause", "cause_defn", "cause_kind"] {
                    if let Some(v) = ev.get(k) {
                        if v.as_str().map_or(false, |x| !x.is_empty()) {
                            out[0][k] = v.clone();
                        }
                    }
                }
                if let Some(b) = ev.get("by") {
                    if !b.is_null() {
                        out[0]["by"] = b.clone();
                    }
                }
                if summon_hold {
                    self.push_list(format!("entered:{}", after), cid);
                    out.push(json!({"ev": "summon", "subject": self.refv(cid), "controller": after, "player": after,
                        "unpaid": ev.get("unpaid").and_then(|v| v.as_bool()).unwrap_or(false)}));
                }
                Ok(out)
            }
            "turn_start" | "turn_end" | "attack" | "block" | "battle_start" | "battle_win" | "battle_end" | "attack_end" | "break" => {
                Ok(vec![ev.clone()])
            }
            other => uns(format!("event {}", other)),
        }
    }

    /// 山札の最後の1枚が離れた瞬間を記録する（104.2b）
    fn note_deck(&mut self, cid: i64) {
        let c = &self.s.cards[cid as usize];
        if c.zone == "deck" && self.s.zones["deck"][c.owner as usize].is_empty() && !self.s.deck_emptied.contains(&c.owner) {
            let o = c.owner;
            self.s.deck_emptied.push(o);
        }
    }

    /// イベントを通さない移動（Python 版 _raw_move の、plain の対戦で通る部分）
    fn raw_move(&mut self, cid: i64, to: &str, position: &str, controller: Option<i64>) {
        let (owner, from) = {
            let c = &self.s.cards[cid as usize];
            (c.owner as usize, c.zone.clone())
        };
        let idx = if self.shared(&from) { 0 } else { owner };
        if from == "hold" {
            self.s.hold.retain(|&x| x != cid);
        } else {
            let lst = self.s.zones.get_mut(&from).unwrap();
            if let Some(pos) = lst[idx].iter().position(|&x| x == cid) {
                lst[idx].remove(pos);
            }
        }
        if from != "hold" && !(to == "deck" && from == "deck") {
            self.note_deck(cid);
        }
        let multi = self.def(cid).civs.len() > 1;
        let public = self.rules.zone(to).public;
        {
            let turn = self.s.turn;
            if to == "bz" {
                self.s.seq += 1;
            }
            let seq = self.s.seq;
            let c = &mut self.s.cards[cid as usize];
            c.gen += 1;
            if to != "mana" {
                c.face_down = false;
            }
            c.zone = to.to_string();
            c.tapped = to == "mana" && multi;
            c.face_up = public;
            c.controller = controller.unwrap_or(c.owner);
            c.entered_turn = if to == "bz" { turn } else { -1 };
            if to == "bz" {
                c.entered_seq = seq;
            }
            c.face = -1;
            c.under.clear();
            c.top_of = -1;
            c.exlife_of = None;
            c.no_untap_next = false;
            c.hyper = false;
            c.sst = false;
            c.stp = false;
            c.odrive = false;
            c.odrive_civs.clear();
            c.bazurenda = 0;
            c.vivid = false;
        }
        let ordered = self.rules.zone(to).ordered;
        let didx = if self.shared(to) { 0 } else { owner };
        let dest = &mut self.s.zones.get_mut(to).unwrap()[didx];
        if ordered && position == "top" {
            dest.insert(0, cid);
        } else {
            dest.push(cid);
        }
    }

    /// 状況起因処理（plain では デッキ切れだけ）
    fn sba(&mut self) -> R<()> {
        if self.s.result.is_some() {
            return Ok(());
        }
        let mut out: Vec<i64> = self.s.deck_emptied.clone();
        for p in 0..2i64 {
            if self.s.zones["deck"][p as usize].is_empty() {
                out.push(p);
            }
        }
        out.sort();
        out.dedup();
        if !out.is_empty() {
            let loser = if out.len() == 2 { self.s.active } else { out[0] };
            self.s.result = Some(json!({"winner": 1 - loser, "reason": "deck_out", "turn": self.s.turn}));
            return Ok(());
        }
        // パワー0以下の破壊: plain のパワーは定義どおり（0 以下の定義は plain にしない）
        Ok(())
    }
}
