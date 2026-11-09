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
    /// plain なカードの permits は既定値（許可・禁止の修整は無い）
    fn permits(&self, action: &str) -> bool {
        *self.rules.actions.get(action).unwrap_or(&false)
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
                return uns("resolve_pending");
            }
            let d = match tt.as_str() {
                "turn" => self.h_turn()?,
                "event" => self.h_event()?,
                "play" => self.h_play()?,
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
            self.s.cards[c as usize].hyper = false;
        }
        self.s.steps_this_turn = 0;
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
            .filter(|&c| self.s.cards[c as usize].tapped && self.permits("untap_at_start") && !frozen.contains(&c))
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
        if !self.permits("summon") || !self.permits("enter_bz") {
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
        if !self.permits("summon") || !self.permits("enter_bz") {
            return false;
        }
        !self.mana_choices(cid, p, None, 1).is_empty()
    }

    fn st_attack(&mut self) -> R<Option<Value>> {
        let a = self.s.active;
        let turn = self.s.turn;
        if self.bz_tops(Some(a)).iter().any(|&c| {
            let k = &self.s.cards[c as usize];
            !k.tapped && k.entered_turn != turn
        }) {
            return uns("attack（攻撃できるクリーチャーがいる）");
        }
        // 攻撃できるものが無ければ選択肢は pass だけ（1択は決定を出さない）
        let ans = match self.ask(a, "attack", vec![json!({"key": "pass"})], 1, 1) {
            Ask::Decision(d) => return Ok(Some(d)),
            Ask::Answer(x) => x,
        };
        let _ = ans;
        self.step_done();
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
        let mut records = 0usize;
        for ev in &evs {
            records += self.apply_one(ev)?;
        }
        self.sba()?;
        // 誘発の収集: plain では誘発しないが、イベントごとに通し番号が進む
        for _ in 0..records {
            self.s.ev_seq += 1;
        }
        Ok(())
    }

    /// 適用して、生まれたレコードの数を返す
    fn apply_one(&mut self, ev: &Value) -> R<usize> {
        let kind = ev["ev"].as_str().unwrap_or("");
        match kind {
            "draw" => {
                let p = ev["player"].as_i64().unwrap();
                let deck = &self.s.zones["deck"][p as usize];
                if deck.is_empty() {
                    return Ok(0);
                }
                let cid = deck[0];
                self.raw_move(cid, "hand", None);
                self.s.cards[cid as usize].drawn_turn = self.s.turn;
                let k = format!("drew:{}", p);
                let n = self.s.turn_counters.get(&k).and_then(|v| v.as_i64()).unwrap_or(0) + 1;
                self.s.turn_counters.insert(k, json!(n));
                Ok(2)
            }
            "tap" | "untap" => {
                if !self.alive(&ev["subject"]) {
                    return Ok(0);
                }
                let cid = ev["subject"][0].as_i64().unwrap();
                let c = &mut self.s.cards[cid as usize];
                if c.tapped == (kind == "tap") {
                    return Ok(0);
                }
                c.tapped = kind == "tap";
                Ok(1)
            }
            "move" => {
                if !self.alive(&ev["subject"]) {
                    return Ok(0);
                }
                let cid = ev["subject"][0].as_i64().unwrap();
                let to = ev["to"].as_str().unwrap_or("");
                let from = self.s.cards[cid as usize].zone.clone();
                let reason = ev.get("reason").and_then(|v| v.as_str()).unwrap_or("");
                if to == "mana" && from == "hand" && reason == "charge" {
                    self.raw_move(cid, to, None);
                    return Ok(1);
                }
                if to == "bz" && from == "hold" && reason == "summon" {
                    let ctl = ev["controller"].as_i64().unwrap();
                    self.raw_move(cid, to, Some(ctl));
                    let k = format!("entered:{}", ctl);
                    let mut l = self.s.turn_counters.get(&k).and_then(|v| v.as_array().cloned()).unwrap_or_default();
                    l.push(json!(cid));
                    self.s.turn_counters.insert(k, Value::Array(l));
                    return Ok(2); // move と summon
                }
                uns(format!("move {}→{}", from, to))
            }
            "turn_start" | "turn_end" => Ok(1),
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
    fn raw_move(&mut self, cid: i64, to: &str, controller: Option<i64>) {
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
        if ordered {
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
