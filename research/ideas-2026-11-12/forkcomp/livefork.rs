//! `fastrunner livefork`: forks of replayed live games (research/ideas-2026-11-12/forkcomp/), on the wasm engine.
//!
//! A game line names the map and each team's bot (our live release build and an opponent puppet that replays the
//! live game's recorded inputs, tools/replay/harness), so the main line is the live game itself, with our bot's
//! memory exactly as it was live. At each fork round, at the round's first champion boundary, the whole state is
//! snapshotted and each arm plays to the game's end with some teams' champions replaced by fresh instances of other
//! bots (a synthetic opponent body; one of our variants), then the state is restored and the main line goes on.
//!
//! A replacement bot needs its own draft memory: it is computed per (bot, team) by a draft with the live picks forced
//! (wengine::DRAFT_PICKS, as the scenario layer does). A puppet team's draft memory is never read, so the first
//! replacement's is written into it during the main line's draft; at a fork, a team whose draft memory differs from
//! the replacement's gets it by scanning the engine's memory for the current bytes (the API refuses writes in play).
//! The replaced team's 8 shared bytes are zeroed. Replacement bots start cold (no memory of the game so far) and get
//! the 2x first-turn budget a new champion gets.
//!
//!   fastrunner livefork --games GAMES.jsonl --out OUT.jsonl [--log-limit B]
//!   game line: {"id", "map", "bots": [DIR_A, DIR_B], "puppet": [false, true], "forks": [R, ...], "max_rounds": 2000,
//!               "arms": [{"label": "puppet"}, {"label": "body", "t1": {"bot": DIR, "seed": 1, "salt": 1,
//!                         "unmetered": true}}, {"label": "x", "t0": {"bot": DIR}, "t1": {...}}]}
//!   Output lines: {"type": "game", ...} and {"type": "arm", ...}.
use crate::engine::Game;
use crate::host::{BotInit, TeamLog};
use crate::runtime::{Bot, BotSnap, Program, Runtime, TurnEnd};
use crate::scenario::{self as sc, ck, W, P};
use crate::wengine::{self, shim, Snapshot};
use anyhow::{anyhow, bail, ensure, Context, Result};
use serde_json::{json, Value};
use std::collections::{HashMap, HashSet};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Instant;

const DRAFT_BYTES: usize = 1024;

struct Live {
    g: Game,
    meta: [u32; 5],
    bb: u64,
    fb: u64,
    champs: Vec<(u32, u32, u32)>,
    team: HashMap<u32, u32>,
    bots: HashMap<u32, Bot>,
    logs: [Box<TeamLog>; 2],
    seen: HashSet<u32>,
    oof: [u32; 2],
    errors: [u32; 2],
    resigned: [bool; 2],
}

struct Snap {
    eng: Snapshot,
    host: ((Game, usize), *const u8),
    bots: Vec<(u32, BotSnap)>,
    logs: [(usize, usize, u32); 2],
    seen: HashSet<u32>,
    oof: [u32; 2],
    errors: [u32; 2],
    resigned: [bool; 2],
}

fn code_of(e: &TurnEnd) -> usize {
    match e {
        TurnEnd::Yield => 0,
        TurnEnd::OutOfFuel => 1,
        TurnEnd::Removed => 2,
        TurnEnd::Exited => 3,
        TurnEnd::Error(_) => 4,
    }
}

fn winner(eng: &crate::engine::Eng, g: Game) -> Option<u32> {
    let mut summ = [0u8; 80];
    unsafe { (eng.Game_Statistics_GetSummary)(g, summ.as_mut_ptr()) };
    match u32::from_le_bytes(summ[4..8].try_into().unwrap()) {
        1 => Some(0),
        2 => Some(1),
        _ => None,
    }
}

impl Live {
    fn w(&self) -> W {
        W { g: self.g }
    }

    /// A fresh game: clean engine, the draft by `draft` (None: the runner picks, as DRAFT_PICKS says), `write[t]`
    /// written into team t's draft memory at its first draft turn, and (if `champ`) every champion's bot spawned.
    fn new(rt: &Runtime, clean: &Snapshot, map: &[u8], draft: [Option<&Arc<Program>>; 2], champ: Option<[&Arc<Program>; 2]>,
           write: [Option<&Vec<u8>>; 2], log_limit: usize) -> Result<Live> {
        let eng = rt.eng;
        wengine::restore(clean);
        wengine::reset_host();
        crate::api::reset_game_caches();
        let mut g: Game = 0;
        ck(unsafe { (eng.Game_FromMapFileBytes)(map.as_ptr(), map.len(), &mut g) }, "Game_FromMapFileBytes")?;
        let mut meta = [0u32; 5];
        ck(unsafe { (eng.Game_API_Map_GetBitboardMetadata)(g, &mut meta) }, "GetBitboardMetadata")?;
        let (mut bb, mut fb) = (0u64, 0u64);
        ck(unsafe { (eng.Bitboard_GetRawBufferSize)(&meta, &mut bb) }, "Bitboard_GetRawBufferSize")?;
        ck(unsafe { (eng.DistanceField_GetRawBufferSize)(&meta, &mut fb) }, "DistanceField_GetRawBufferSize")?;
        ck(unsafe { (eng.Game_Runner_Init)(g) }, "Game_Runner_Init")?;
        let mut logs: [Box<TeamLog>; 2] = [Box::new(TeamLog::new(log_limit)), Box::new(TeamLog::new(log_limit))];
        let w = W { g };
        {
            let mut bots: [Option<Bot>; 2] = [None, None];
            for t in 0..2 {
                if let Some(p) = draft[t] {
                    let init = BotInit { game: g, team: t as u32, champion: u32::MAX, ctype: u32::MAX, meta, board_bytes: bb, field_bytes: fb };
                    bots[t] = Some(Bot::spawn(rt, p, init, &mut *logs[t])?);
                }
            }
            let mut dead = [false; 2];
            let mut first = [true; 2];
            let mut written = [false; 2];
            let mut rng: u64 = map.iter().fold(0xCBF2_9CE4_8422_2325u64, |h, &b| (h ^ b as u64).wrapping_mul(0x0100_0000_01B3));
            loop {
                let s = w.st();
                if s[0] != 0 {
                    break;
                }
                let t = s[1] as usize;
                ensure!(t < 2, "draft turn for team {t}");
                if let (Some(m), false) = (write[t], written[t]) {
                    ck(unsafe { shim::Game_API_WriteDraftMemory(g, t as u32, 0, m.as_ptr(), m.len()) }, "WriteDraftMemory")?;
                    written[t] = true;
                }
                if draft[t].is_none() {
                    ck(unsafe { shim::Game_Action_Draft(g, 0) }, "Draft")?;
                    w.end(0)?;
                    continue;
                }
                if dead[t] {
                    crate::game::default_draft(eng, g, &mut rng)?;
                    w.end(2)?;
                    continue;
                }
                let pos0 = crate::game::timeline_pos(eng, g)?;
                let bot = bots[t].as_mut().unwrap();
                let end = bot.run_turn(if first[t] { 100 } else { 1 });
                first[t] = false;
                let code = code_of(&end);
                if code == 2 {
                    dead[t] = true;
                    bots[t] = None;
                    continue;
                }
                let pos1 = crate::game::timeline_pos(eng, g)?;
                if pos1 != pos0 && code < 2 {
                    w.end(code as u32)?;
                    continue;
                }
                dead[t] = true;
                bots[t] = None;
                if pos1 != pos0 {
                    w.end(if code == 0 { 0 } else if code == 1 { 1 } else { 2 })?;
                } else {
                    crate::game::default_draft(eng, g, &mut rng)?;
                    w.end(if code == 1 { 1 } else { 2 })?;
                }
            }
        }
        let mut champs = Vec::new();
        let mut team = HashMap::new();
        let mut bots = HashMap::new();
        if w.st()[0] != 2 {
            for id in w.champion_ids()? {
                let (t, ty) = w.identity(id);
                champs.push((id, t, ty));
                team.insert(id, t);
                if let Some(p) = champ {
                    let init = BotInit { game: g, team: t, champion: id, ctype: ty, meta, board_bytes: bb, field_bytes: fb };
                    bots.insert(id, Bot::spawn(rt, p[t as usize], init, &mut *logs[t as usize])?);
                }
            }
        }
        Ok(Live { g, meta, bb, fb, champs, team, bots, logs, seen: HashSet::new(), oof: [0; 2], errors: [0; 2], resigned: [false; 2] })
    }

    fn picks(&self) -> [Vec<u32>; 2] {
        let mut out = [Vec::new(), Vec::new()];
        for t in 0..2u32 {
            for r in 0..8u8 {
                let mut got = u32::MAX;
                if unsafe { shim::Game_API_Draft_Get(self.g, t, r, &mut got as *mut u32 as P) } != 0 || got == u32::MAX {
                    break;
                }
                out[t as usize].push(got);
            }
        }
        out
    }

    fn play_turn(&mut self, rt: &Runtime, st: [u32; 4]) -> Result<usize> {
        let c = st[3];
        let t = self.team.get(&c).copied().ok_or_else(|| anyhow!("engine scheduled champion {c}, not in the game"))? as usize;
        let bot = self.bots.get_mut(&c).ok_or_else(|| anyhow!("no bot for champion {c}"))?;
        let scale = if self.seen.insert(c) { 2 } else { 1 };
        let end = bot.run_turn(scale);
        let code = code_of(&end);
        self.oof[t] += (code == 1) as u32;
        if code == 3 || code == 4 {
            self.errors[t] += 1;
            bot.restart(rt);
        }
        if code == 2 {
            self.resigned[t] = true;
            return Ok(code);
        }
        self.w().end([0u32, 1, 0, 2, 2][code])?;
        Ok(code)
    }

    fn snap(&mut self) -> Option<Snap> {
        let mut bots = Vec::with_capacity(self.bots.len());
        for (&id, b) in self.bots.iter_mut() {
            bots.push((id, b.snapshot()?));
        }
        Some(Snap {
            eng: wengine::snapshot(),
            host: wengine::host_state(),
            bots,
            logs: [0, 1].map(|t| (self.logs[t].buf.len(), self.logs[t].written, self.logs[t].last_pos)),
            seen: self.seen.clone(),
            oof: self.oof,
            errors: self.errors,
            resigned: self.resigned,
        })
    }

    fn restore(&mut self, s: &Snap) -> bool {
        if s.bots.len() != self.bots.len() || !s.bots.iter().all(|(id, b)| self.bots.get(id).is_some_and(|x| x.can_restore(b))) {
            return false;
        }
        wengine::restore(&s.eng);
        wengine::set_host_state(s.host);
        for (id, b) in &s.bots {
            if !self.bots.get_mut(id).is_some_and(|x| x.restore(b)) {
                return false;
            }
        }
        for t in 0..2 {
            let (len, written, last) = s.logs[t];
            self.logs[t].buf.truncate(len);
            self.logs[t].written = written;
            self.logs[t].last_pos = last;
        }
        self.seen.clone_from(&s.seen);
        self.oof = s.oof;
        self.errors = s.errors;
        self.resigned = s.resigned;
        true
    }

    /// Plays from here to the game's end (or past `max_rounds`): (finished, last round).
    fn play_out(&mut self, rt: &Runtime, max_rounds: u32, zero_shared: &mut [bool; 2], shared_rc: &mut [i32; 2]) -> Result<(bool, u32)> {
        loop {
            let st = self.w().boundary()?;
            if st[0] != 2 {
                // A team's shared bytes are writable at its own input boundary only (error 18 otherwise).
                let t = self.team.get(&st[3]).copied().unwrap_or(2) as usize;
                if t < 2 && zero_shared[t] {
                    let zero = [0u8; 8];
                    shared_rc[t] = unsafe { shim::Game_API_WriteSharedMemory(self.g, t as u32, 0, zero.as_ptr(), 8) };
                    zero_shared[t] = false;
                }
            }
            if st[0] == 2 {
                return Ok((true, st[2]));
            }
            if st[2] > max_rounds {
                return Ok((false, st[2]));
            }
            self.play_turn(rt, st)?;
        }
    }
}

/// Team `team`'s draft memory as `prog`'s draft bot writes it when the draft makes `picks` (both teams'), read at the
/// team's first champion turn; with the draft's DRAFT-/PLAN- lines.
fn draft_mem(rt: &Runtime, clean: &Snapshot, map: &[u8], prog: &Arc<Program>, team: usize, picks: &[Vec<u32>; 2], log_limit: usize)
             -> Result<(Vec<u8>, Vec<String>)> {
    unsafe { *std::ptr::addr_of_mut!(wengine::DRAFT_PICKS) = Some((picks.clone(), [0, 0])) };
    let mut d: [Option<&Arc<Program>>; 2] = [None, None];
    d[team] = Some(prog);
    let r = Live::new(rt, clean, map, d, None, [None, None], log_limit);
    let made = unsafe { (*std::ptr::addr_of_mut!(wengine::DRAFT_PICKS)).take() };
    let lv = r?;
    let got = lv.picks();
    ensure!(&got == picks, "forced draft made {got:?}, wanted {picks:?} (made {:?})", made.map(|m| m.1));
    let notes: Vec<String> = String::from_utf8_lossy(&lv.logs[team].buf).lines().filter(|l| l.starts_with("DRAFT-") || l.starts_with("PLAN-")).map(String::from).collect();
    let w = lv.w();
    loop {
        let st = w.boundary()?;
        ensure!(st[0] != 2, "game ended before team {team}'s first champion turn");
        let t = w.identity(st[3]).0 as usize;
        if t == team {
            let mut m = vec![0u8; DRAFT_BYTES];
            ck(unsafe { shim::Game_API_ReadDraftMemory(lv.g, team as u32, 0, m.as_mut_ptr(), DRAFT_BYTES as u32) }, "ReadDraftMemory")?;
            return Ok((m, notes));
        }
        w.end(0)?;
    }
}

/// Replaces every occurrence of `old` in the engine's memory by `new` (same length): how many were replaced.
fn replace_in_engine(old: &[u8], new: &[u8]) -> usize {
    let mem = wengine::memory();
    let mut n = 0;
    let mut i = 0;
    let first = old[0];
    while i + old.len() <= mem.len() {
        match mem[i..mem.len() - old.len() + 1].iter().position(|&b| b == first) {
            None => break,
            Some(k) => {
                let j = i + k;
                if &mem[j..j + old.len()] == old {
                    mem[j..j + old.len()].copy_from_slice(new);
                    n += 1;
                    i = j + old.len();
                } else {
                    i = j + 1;
                }
            }
        }
    }
    n
}

#[derive(Clone)]
struct Repl {
    bot: String,
    config: Option<crate::experiment::TeamConfig>,
}

struct Arm {
    label: String,
    repl: [Option<Repl>; 2],
}

struct Ctx<'a> {
    rt: &'a mut Runtime,
    clean: Snapshot,
    root: PathBuf,
    release: bool,
    log_limit: usize,
}

impl<'a> Ctx<'a> {
    fn prog(&mut self, bot: &str, config: Option<crate::experiment::TeamConfig>) -> Result<Arc<Program>> {
        let w = crate::wasm_of(&crate::resolve_bot(&self.root, bot)?, self.release)?;
        self.rt.configured_program(&w, config)
    }

    fn game(&mut self, v: &Value, emit: &mut dyn FnMut(Value)) -> Result<Value> {
        let t0 = Instant::now();
        let c0 = sc::cpu_ms();
        let id = v["id"].as_str().unwrap_or("?").to_string();
        let mp = v["map"].as_str().ok_or_else(|| anyhow!("map missing"))?;
        let path = [PathBuf::from(mp), self.root.join(mp)].into_iter().find(|p| p.is_file()).ok_or_else(|| anyhow!("map {mp} not found"))?;
        let map = std::fs::read(&path)?;
        let parse_repl = |r: &Value| -> Option<Repl> {
            if let Some(b) = r.as_str() {
                return Some(Repl { bot: b.to_string(), config: None });
            }
            let bot = r["bot"].as_str()?.to_string();
            let config = r.get("seed").and_then(Value::as_u64).map(|seed| crate::experiment::TeamConfig {
                seed,
                salt: r["salt"].as_u64().unwrap_or(1),
                unmetered: r["unmetered"].as_bool().unwrap_or(false),
            });
            Some(Repl { bot, config })
        };
        let base_r: Vec<Repl> = v["bots"].as_array().ok_or_else(|| anyhow!("bots missing"))?.iter().filter_map(|b| parse_repl(b)).collect();
        ensure!(base_r.len() == 2, "bots: two");
        let bots: Vec<String> = base_r.iter().map(|r| r.bot.clone()).collect();
        let puppet: Vec<bool> = v["puppet"].as_array().map(|a| a.iter().map(|x| x.as_bool().unwrap_or(false)).collect()).unwrap_or(vec![false, false]);
        let max_rounds = v["max_rounds"].as_u64().unwrap_or(2000) as u32;
        let mut forks: Vec<u32> = v["forks"].as_array().map(|a| a.iter().filter_map(|x| x.as_u64()).map(|x| x as u32).collect()).unwrap_or_default();
        forks.sort();
        forks.dedup();
        let mut arms = Vec::new();
        for a in v["arms"].as_array().ok_or_else(|| anyhow!("arms missing"))? {
            let mut repl: [Option<Repl>; 2] = [None, None];
            for t in 0..2 {
                if let Some(r) = a.get(format!("t{t}")).filter(|r| !r.is_null()) {
                    let bot = r["bot"].as_str().ok_or_else(|| anyhow!("arm t{t}: bot"))?.to_string();
                    let config = r.get("seed").and_then(Value::as_u64).map(|seed| crate::experiment::TeamConfig {
                        seed,
                        salt: r["salt"].as_u64().unwrap_or(1),
                        unmetered: r["unmetered"].as_bool().unwrap_or(false),
                    });
                    repl[t] = Some(Repl { bot, config });
                }
            }
            arms.push(Arm { label: a["label"].as_str().unwrap_or("?").to_string(), repl });
        }
        let base = [self.prog(&base_r[0].bot, base_r[0].config)?, self.prog(&base_r[1].bot, base_r[1].config)?];
        // ---- pass 0: the live draft, for its picks ----
        let lv0 = Live::new(self.rt, &self.clean, &map, [Some(&base[0]), Some(&base[1])], None, [None, None], self.log_limit)?;
        let picks = lv0.picks();
        drop(lv0);
        // ---- each replacement's program and draft memory ----
        let mut progs: Vec<[Option<Arc<Program>>; 2]> = Vec::new();
        let mut dmem: HashMap<(usize, String, u64), Vec<u8>> = HashMap::new();
        let mut notes = serde_json::Map::new();
        for a in &arms {
            let mut ps: [Option<Arc<Program>>; 2] = [None, None];
            for t in 0..2 {
                if let Some(r) = &a.repl[t] {
                    let p = self.prog(&r.bot, r.config)?;
                    let key = (t, r.bot.clone(), r.config.map_or(0, |c| c.salt));
                    if !dmem.contains_key(&key) {
                        let (m, n) = draft_mem(self.rt, &self.clean, &map, &p, t, &picks, self.log_limit)?;
                        if !n.is_empty() {
                            notes.insert(format!("{}:t{t}", r.bot), json!(n));
                        }
                        dmem.insert(key, m);
                    }
                    ps[t] = Some(p);
                }
            }
            progs.push(ps);
        }
        let key_of = |t: usize, r: &Repl| (t, r.bot.clone(), r.config.map_or(0, |c| c.salt));
        // A puppet team's draft memory: the first replacement's, written in the main line's draft.
        let mut pwrite: [Option<Vec<u8>>; 2] = [None, None];
        for t in 0..2 {
            if puppet.get(t).copied().unwrap_or(false) {
                if let Some(r) = arms.iter().find_map(|a| a.repl[t].as_ref()) {
                    pwrite[t] = dmem.get(&key_of(t, r)).cloned();
                }
            }
        }
        // ---- the main line ----
        let mut lv = Live::new(self.rt, &self.clean, &map, [Some(&base[0]), Some(&base[1])], Some([&base[0], &base[1]]),
                               [pwrite[0].as_ref(), pwrite[1].as_ref()], self.log_limit)?;
        let eng = self.rt.eng;
        let mut cur_draft: [Option<Vec<u8>>; 2] = pwrite.clone();
        let mut cur = 0u32;
        let mut next = 0usize;
        let mut fork_errors: Vec<String> = Vec::new();
        let mut arm_cpu = 0.0;
        loop {
            let st = lv.w().boundary()?;
            if st[0] == 2 || st[2] > max_rounds {
                break;
            }
            let c = st[3];
            let t = lv.team[&c] as usize;
            if cur_draft[t].is_none() {
                let mut m = vec![0u8; DRAFT_BYTES];
                if unsafe { shim::Game_API_ReadDraftMemory(lv.g, t as u32, 0, m.as_mut_ptr(), DRAFT_BYTES as u32) } == 0 {
                    cur_draft[t] = Some(m);
                }
            }
            if st[2] != cur {
                cur = st[2];
            }
            if next < forks.len() && forks[next] <= cur {
                let r = forks[next];
                next += 1;
                if r < cur {
                    fork_errors.push(format!("fork {r} missed"));
                    continue;
                }
                let Some(snap) = lv.snap() else {
                    fork_errors.push(format!("fork {r}: snapshot failed"));
                    continue;
                };
                let w = lv.w();
                let trib0 = [w.tributed(0), w.tributed(1)];
                let alive0: Vec<bool> = lv.champs.iter().map(|ch| w.alive(ch.0)).collect();
                for (k, a) in arms.iter().enumerate() {
                    let ca = sc::cpu_ms();
                    if !lv.restore(&snap) {
                        bail!("fork {r}: restore failed (arm {k})");
                    }
                    let mut swapped: Vec<(u32, Bot)> = Vec::new();
                    let mut zero_shared = [false; 2];
                    let mut shared_rc = [-1i32; 2];
                    let mut info = serde_json::Map::new();
                    for t in 0..2 {
                        let (Some(rp), Some(p)) = (&a.repl[t], &progs[k][t]) else { continue };
                        let want = &dmem[&key_of(t, rp)];
                        match &cur_draft[t] {
                            Some(old) if old != want => {
                                let n = if old.iter().all(|&b| b == 0) { 0 } else { replace_in_engine(old, want) };
                                info.insert(format!("draft_replaced_t{t}"), json!(n));
                            }
                            Some(_) => {}
                            None => {
                                info.insert(format!("draft_unknown_t{t}"), json!(true));
                            }
                        }
                        zero_shared[t] = true;
                        for &(id, tt, ty) in &lv.champs {
                            if tt as usize != t {
                                continue;
                            }
                            let init = BotInit { game: lv.g, team: tt, champion: id, ctype: ty, meta: lv.meta, board_bytes: lv.bb, field_bytes: lv.fb };
                            let fresh = Bot::spawn(self.rt, p, init, &mut *lv.logs[t])?;
                            let old = lv.bots.insert(id, fresh).unwrap();
                            swapped.push((id, old));
                            lv.seen.remove(&id);
                        }
                    }
                    let log0 = [lv.logs[0].buf.len(), lv.logs[1].buf.len()];
                    let res = lv.play_out(self.rt, max_rounds, &mut zero_shared, &mut shared_rc);
                    for t in 0..2 {
                        if shared_rc[t] > 0 {
                            info.insert(format!("shared_rc_t{t}"), json!(shared_rc[t]));
                        }
                    }
                    let w = lv.w();
                    let mut row = json!({"type": "arm", "game": id, "fork": r, "arm": k, "label": a.label,
                        "trib_fork": trib0, "alive_fork": alive0});
                    match res {
                        Ok((fin, last)) => {
                            row["finished"] = json!(fin);
                            row["rounds"] = json!(last);
                            row["winner"] = json!(if fin { winner(eng, lv.g) } else { None });
                            row["trib"] = json!([w.tributed(0), w.tributed(1)]);
                        }
                        Err(e) => {
                            row["error"] = json!(format!("{e:#}"));
                        }
                    }
                    row["oof"] = json!(lv.oof);
                    row["errors"] = json!(lv.errors);
                    row["resigned"] = json!(lv.resigned);
                    let mut lines = Vec::new();
                    for t in 0..2 {
                        let text = String::from_utf8_lossy(&lv.logs[t].buf[log0[t].min(lv.logs[t].buf.len())..]).into_owned();
                        for l in text.lines().filter(|l| l.starts_with("DRAFT-") || l.starts_with("PLAN-") || l.contains("PUPPET-ERR")).take(4) {
                            lines.push(format!("t{t}: {l}"));
                        }
                    }
                    if !lines.is_empty() {
                        row["notes"] = json!(lines);
                    }
                    for (kk, vv) in info {
                        row[kk] = vv;
                    }
                    // Put the original bots back, then the fork's state.
                    for (bid, old) in swapped {
                        lv.bots.insert(bid, old);
                    }
                    let dt = sc::cpu_ms() - ca;
                    arm_cpu += dt;
                    row["cpu_ms"] = json!(dt);
                    emit(row);
                }
                if !lv.restore(&snap) {
                    fork_errors.push(format!("fork {r}: main line not restored"));
                    break;
                }
                continue;
            }
            lv.play_turn(self.rt, st)?;
        }
        let fin = lv.w().st();
        let w = lv.w();
        let mut g = json!({"type": "game", "id": id, "map": path.to_string_lossy(), "bots": bots, "picks": picks,
            "rounds": fin[2], "finished": fin[0] == 2, "winner": winner(eng, lv.g), "trib": [w.tributed(0), w.tributed(1)],
            "oof": lv.oof, "errors": lv.errors, "forks": forks, "arms": arms.len(), "arm_cpu_ms": arm_cpu,
            "cpu_ms": sc::cpu_ms() - c0, "wall_ms": t0.elapsed().as_secs_f64() * 1e3});
        if !notes.is_empty() {
            g["draft_notes"] = Value::Object(notes);
        }
        if !fork_errors.is_empty() {
            g["fork_errors"] = json!(fork_errors);
        }
        if let Some(d) = v["save_replay"].as_str() {
            ck(unsafe { (eng.Game_SaveReplay)(lv.g) }, "Game_SaveReplay")?;
            let (mut p, mut n) = (std::ptr::null::<u8>(), 0usize);
            ck(unsafe { (eng.Game_FileBuffer)(lv.g, &mut p, &mut n) }, "Game_FileBuffer")?;
            std::fs::write(d, unsafe { std::slice::from_raw_parts(p, n) })?;
        }
        Ok(g)
    }
}

pub fn main(args: &[String]) -> Result<i32> {
    let mut games: Option<PathBuf> = None;
    let mut out: Option<PathBuf> = None;
    let mut log_limit = 1usize << 20;
    let mut release = true;
    let mut i = 0;
    while i < args.len() {
        let a = args[i].as_str();
        let val = || -> Result<&String> { args.get(i + 1).ok_or_else(|| anyhow!("{a} needs a value")) };
        match a {
            "--games" => games = Some(PathBuf::from(val()?)),
            "--out" | "-o" => out = Some(PathBuf::from(val()?)),
            "--log-limit" => log_limit = val()?.parse()?,
            "--debug" => {
                release = false;
                i += 1;
                continue;
            }
            _ => bail!("unknown argument {a}"),
        }
        i += 2;
    }
    let games = games.ok_or_else(|| anyhow!("--games is required"))?;
    let out_path = out.ok_or_else(|| anyhow!("--out is required"))?;
    let text = std::fs::read_to_string(&games).with_context(|| format!("reading {}", games.display()))?;
    let mut rt = crate::load_runtime()?;
    ensure!(rt.eng.is_wasm(), "fastrunner livefork needs FASTRUNNER_ENGINE=wasm");
    ensure!(crate::runtime::native_mode(), "fastrunner livefork needs FASTRUNNER_MODE=native (bot snapshots)");
    let clean = wengine::snapshot();
    let mut ctx = Ctx { rt: &mut rt, clean, root: crate::project_root(), release, log_limit };
    let mut out = std::io::BufWriter::new(std::fs::File::create(&out_path)?);
    let t0 = Instant::now();
    for (k, line) in text.lines().filter(|l| !l.trim().is_empty()).enumerate() {
        let v: Value = serde_json::from_str(line).with_context(|| format!("game line {k}"))?;
        let mut rows: Vec<Value> = Vec::new();
        let g = ctx.game(&v, &mut |r| rows.push(r));
        for r in rows {
            writeln!(out, "{r}")?;
        }
        let g = g.unwrap_or_else(|e| json!({"type": "game", "id": v["id"], "error": format!("{e:#}")}));
        writeln!(out, "{g}")?;
        out.flush()?;
        eprintln!("[{}] {} {:.1}s", k + 1, v["id"].as_str().unwrap_or("?"), t0.elapsed().as_secs_f64());
    }
    let _ = Path::new("");
    Ok(0)
}
