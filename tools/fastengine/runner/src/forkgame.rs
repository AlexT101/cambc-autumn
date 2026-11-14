//! `fastrunner forkgame`: stateful forks of real games for the combat lab (research/notes/combat-lab-forks.md,
//! research/notes/RUNNER.md "Forks of real games"), on the wasm engine backend.
//!
//! Per game, two passes of the same deterministic game:
//! - pass 1 plays it whole (normal draft, every champion's bot live from round 1) and records each round start's
//!   digest (every champion's API state, both teams' tributed gems, the timeline position), each round's alive set,
//!   deaths and the lab bots' decide branches; the fork points come from these (triggers), so a trigger may look
//!   ahead (a death N rounds later);
//! - pass 2 plays it again and, at the input boundary before each fork point's champion's turn (the decider), takes
//!   the whole state (engine memory and host state, every bot instance's memory, stack and meter, the team logs) and
//!   plays each arm's continuation from it for H rounds with every champion live, then restores it and plays on.
//!
//! An arm is the unforced continuation (`none`: ocean's own choice), a forced action of the decider (lab.h LabAct:
//! run at the start of its decide, ocean then plays the rest of the turn; `--holds N` repeats it N rounds), or a
//! forced want_home / chase verdict (lab.h LabBlock). The `none` arm's round-start digests are compared with pass 1's
//! (the continuation must be the original game's). Output: one line per game, fork and arm (`type`).
//!
//!   fastrunner forkgame --bot-a BOT --bot-b BOT (--maps M,M,... | --games FILE.jsonl) --out OUT.jsonl
//!       [--both-sides] [--jobs J --slot-dir DIR --slots K] [--debug] [--lab-flags F] [--decider a|b|both]
//!       [--trigger near:6,close:6,branch:RC,death:10,kill:10,every:50] [--gap G] [--max-forks N] [--min-round R]
//!       [--seed S] [--marks 10,30,60] [--arms none,sweep,end,home:V:N,chase:V:N] [--holds 1,3] [--ground hits|all]
//!       [--work FPGBTW] [--work-radius 8] [--full] [--max-rounds R] [--hash] [--log-limit B] [--decisions]
//!       [--jitter J,J,...] [--skip-reps K] (noise replicates: each arm again per J with every bot's turn fuel
//!       shifted by J, and per k <= K with the k-th farthest champion from the decider skipping its next turn)
//!       [--trace N] (arm rows list every champion's position, health and liveness at its first N round starts)
use crate::engine::Game;
use crate::host::{BotInit, TeamLog};
use crate::runtime::{Bot, BotSnap, Program, Runtime, TurnEnd};
use crate::scenario::{self as sc, ck, lb, W, OBS, P};
use crate::wengine::{self, shim, Snapshot};
use anyhow::{anyhow, bail, ensure, Context, Result};
use serde_json::{json, Value};
use std::collections::{HashMap, HashSet};
use std::io::{BufRead, Write};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Instant;

/// lab.h's LabAct: the forced-action block.
const ACT_MAGIC: &[u8; 16] = b"CAMBC-LAB-ACT-1\0";
const ACT_SIZE: u32 = 128;
mod la {
    pub const ROUND: usize = 24;
    pub const N: usize = 28;
    pub const OPS: usize = 32;
    pub const OP: usize = 12;
    pub const DONE_ROUND: usize = 80;
    pub const RES: usize = 84;
}

fn find_act(m: &[u8]) -> Option<usize> {
    let mut i = 0;
    while i + 16 <= m.len() {
        let j = i + m[i..].iter().position(|&b| b == b'C')?;
        if j + ACT_SIZE as usize <= m.len() && &m[j..j + 16] == ACT_MAGIC && sc::rd_u32(m, j + 20) == ACT_SIZE {
            return Some(j);
        }
        i = j + 1;
    }
    None
}

// ---------------------------------------------------------------- options

#[derive(Clone, Debug)]
enum Trig {
    /// An enemy within D of a decider at a round start where none was at the one before (first contact).
    Near(i32),
    /// An enemy within D of a decider at a round start.
    Close(i32),
    /// A decider's decide branch in this set (lab bots).
    Branch(Vec<u8>),
    /// N rounds before a decider's death.
    Death(u32),
    /// N rounds before a decider's kill.
    Kill(u32),
    /// Every K rounds, the deciders in turn.
    Every(u32),
}

#[derive(Clone, Debug)]
enum ArmSpec {
    None,
    Sweep,
    End,
    /// A forced verdict: 0 want_home / 1 chase, the verdict, the rounds it holds.
    Verdict(u8, i32, i32),
}

#[derive(Clone)]
struct Opts {
    bots: [String; 2],
    release: bool,
    lab_flags: u32,
    /// The deciders' side by bot: 0 the --bot-a bot's champions, 1 the --bot-b bot's, 2 both.
    decider: u32,
    triggers: Vec<Trig>,
    gap: u32,
    max_forks: usize,
    min_round: u32,
    seed: u64,
    marks: Vec<u32>,
    arms: Vec<ArmSpec>,
    holds: Vec<i32>,
    ground_all: bool,
    work: Vec<u8>,
    work_radius: i32,
    full: bool,
    max_rounds: u32,
    hash: bool,
    log_limit: usize,
    decisions: bool,
    /// The game line lists pass 1's round-start digests (finding where two games part).
    digests: bool,
    /// Pass 1's replay is written here as ID.repl26a (the engine's replay file, not a bundle).
    replays: Option<PathBuf>,
    /// Noise replicates: each arm is also played once per value, with every bot's per-turn fuel shifted by it from
    /// each bot's next turn on (the fork turn itself is as played). Empty: one unperturbed play per arm.
    jitter: Vec<i64>,
    /// More noise replicates: rep k ends the turn (LabAct op 7) of the k-th farthest live champion from the decider
    /// (lab bots only) in the round after the fork's.
    skip_reps: usize,
    /// Arm rows list every champion's [id, x, y, hp, alive] at each of the arm's first `trace` round starts.
    trace: u32,
}

impl Opts {
    fn horizon(&self) -> u32 {
        self.marks.iter().copied().max().unwrap_or(30)
    }
}

// ---------------------------------------------------------------- a match in progress

/// A game's whole state between turns, for putting the same match back to it (its bots must be these objects).
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

impl Snap {
    fn bytes(&self) -> (usize, usize) {
        (self.eng.bytes(), self.bots.iter().map(|b| b.1.bytes()).sum())
    }
}

struct Match {
    g: Game,
    /// (id, team, champion type) of every champion.
    champs: Vec<(u32, u32, u32)>,
    team: HashMap<u32, u32>,
    bots: HashMap<u32, Bot>,
    blk: HashMap<u32, usize>,
    act: HashMap<u32, usize>,
    logs: [Box<TeamLog>; 2],
    seen: HashSet<u32>,
    oof: [u32; 2],
    errors: [u32; 2],
    resigned: [bool; 2],
    flags: u32,
    draft_ms: f64,
    /// The map's width and height.
    size: (i32, i32),
}

/// Each team's program and where its lab blocks sit (the same in every instance of a program).
struct Progs {
    progs: [Arc<Program>; 2],
    blk: [Option<Option<usize>>; 2],
    act: [Option<Option<usize>>; 2],
}

impl Match {
    fn w(&self) -> W {
        W { g: self.g }
    }

    /// A fresh game on `map`: clean engine, the draft (as game.rs plays it), every champion's bot spawned.
    fn new(rt: &Runtime, pr: &mut Progs, clean: &Snapshot, map: &[u8], flags: u32, log_limit: usize) -> Result<Match> {
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
        let t0 = Instant::now();
        // ---- draft, as game.rs plays it ----
        {
            let spawn = |t: usize, logs: &mut [Box<TeamLog>; 2]| -> Result<Bot> {
                let init = BotInit { game: g, team: t as u32, champion: u32::MAX, ctype: u32::MAX, meta, board_bytes: bb, field_bytes: fb };
                Bot::spawn(rt, &pr.progs[t], init, &mut *logs[t])
            };
            let mut draft = [Some(spawn(0, &mut logs)?), Some(spawn(1, &mut logs)?)];
            let mut dead = [false; 2];
            let mut first = [true; 2];
            let mut rng: u64 = map.iter().fold(0xCBF2_9CE4_8422_2325u64, |h, &b| (h ^ b as u64).wrapping_mul(0x0100_0000_01B3));
            loop {
                let s = w.st();
                if s[0] != 0 {
                    break;
                }
                let t = s[1] as usize;
                ensure!(t < 2, "draft turn for team {t}");
                if dead[t] {
                    crate::game::default_draft(eng, g, &mut rng)?;
                    w.end(2)?;
                    continue;
                }
                let pos0 = crate::game::timeline_pos(eng, g)?;
                let bot = draft[t].as_mut().unwrap();
                let end = bot.run_turn(if first[t] { 100 } else { 1 });
                first[t] = false;
                let code = code_of(&end);
                if code == 2 {
                    dead[t] = true;
                    draft[t] = None;
                    continue;
                }
                let pos1 = crate::game::timeline_pos(eng, g)?;
                if pos1 != pos0 && code < 2 {
                    w.end(code as u32)?;
                    continue;
                }
                dead[t] = true;
                draft[t] = None;
                if pos1 != pos0 {
                    w.end(if code == 0 { 0 } else if code == 1 { 1 } else { 2 })?;
                } else {
                    crate::game::default_draft(eng, g, &mut rng)?;
                    w.end(if code == 1 { 1 } else { 2 })?;
                }
            }
        }
        let draft_ms = t0.elapsed().as_secs_f64() * 1e3;
        let mut champs = Vec::new();
        let mut team = HashMap::new();
        let mut bots = HashMap::new();
        if w.st()[0] != 2 {
            for id in w.champion_ids()? {
                let (t, ty) = w.identity(id);
                champs.push((id, t, ty));
                team.insert(id, t);
                let init = BotInit { game: g, team: t, champion: id, ctype: ty, meta, board_bytes: bb, field_bytes: fb };
                bots.insert(id, Bot::spawn(rt, &pr.progs[t as usize], init, &mut *logs[t as usize])?);
            }
        }
        let mut m = Match {
            g, champs, team, bots, blk: HashMap::new(), act: HashMap::new(), logs, seen: HashSet::new(), oof: [0; 2], errors: [0; 2],
            resigned: [false; 2], flags, draft_ms, size: (meta[0] as i32, meta[1] as i32),
        };
        let ids: Vec<u32> = m.champs.iter().map(|c| c.0).collect();
        for id in ids {
            m.init_blocks(pr, id);
        }
        Ok(m)
    }

    /// Finds a (fresh) instance's lab blocks and writes its flags.
    fn init_blocks(&mut self, pr: &mut Progs, id: u32) {
        let t = self.team[&id] as usize;
        let Some(b) = self.bots.get_mut(&id) else { return };
        let Some(mem) = b.memory() else { return };
        let o = *pr.blk[t].get_or_insert_with(|| sc::find_block(mem));
        let a = *pr.act[t].get_or_insert_with(|| find_act(mem));
        if let Some(o) = o.filter(|&o| o + 512 <= mem.len() && &mem[o..o + 16] == sc::LAB_MAGIC) {
            mem[o + lb::FLAGS..o + lb::FLAGS + 4].copy_from_slice(&self.flags.to_le_bytes());
            self.blk.insert(id, o);
        }
        if let Some(a) = a.filter(|&a| a + ACT_SIZE as usize <= mem.len() && &mem[a..a + 16] == ACT_MAGIC) {
            self.act.insert(id, a);
        }
    }

    /// Runner steps up to the next champion's input boundary (or the game's end).
    fn boundary(&self) -> Result<[u32; 4]> {
        self.w().boundary()
    }

    /// The turn at boundary `st`, as game.rs plays it (a crashed bot gets a fresh instance, its blocks re-found).
    fn play_turn(&mut self, rt: &Runtime, pr: &mut Progs, st: [u32; 4]) -> Result<usize> {
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
            self.blk.remove(&c);
            self.act.remove(&c);
            self.init_blocks(pr, c);
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

    /// Back to `s`: false if a bot cannot be (restarted since).
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

    fn mem(&mut self, id: u32) -> Option<&mut [u8]> {
        self.bots.get_mut(&id)?.memory()
    }

    /// The lab block's decide branch of `id`'s turn in `round` (0 if it did not record one).
    fn branch(&mut self, id: u32, round: u32) -> u8 {
        let Some(&o) = self.blk.get(&id) else { return 0 };
        let Some(m) = self.mem(id) else { return 0 };
        if sc::rd_i32(m, o + lb::ROUND) == round as i32 {
            m[o + lb::DECISION]
        } else {
            0
        }
    }

    fn decision(&mut self, id: u32, round: u32) -> Value {
        let Some(&o) = self.blk.get(&id) else { return Value::Null };
        let Some(m) = self.mem(id) else { return Value::Null };
        if sc::rd_i32(m, o + lb::ROUND) == round as i32 {
            sc::read_decision(m, o)
        } else {
            Value::Null
        }
    }

    /// Positions at this moment: (id, team, alive, x, y).
    fn positions(&self) -> Vec<(u32, u32, bool, i32, i32)> {
        let w = self.w();
        self.champs
            .iter()
            .map(|&(id, t, _)| {
                let a = w.alive(id);
                let c = if a { w.champ(id) } else { None };
                (id, t, a && c.is_some(), c.map_or(-1, |c| c.x), c.map_or(-1, |c| c.y))
            })
            .collect()
    }

    /// The round start's digest: every champion's API record, gems, cooldowns and liveness, both teams' tributed
    /// gems, the timeline position.
    fn digest(&self, eng: &crate::engine::Eng) -> u64 {
        let w = self.w();
        let mut h = sc::FNV0;
        for &(id, _, _) in &self.champs {
            let mut c = [0u32; 11];
            let r = unsafe { shim::Game_API_Champion_Get(self.g, OBS, id, c.as_mut_ptr() as P) };
            h = sc::fnv(h, &[w.alive(id) as u8, (r == 0) as u8]);
            for x in c {
                h = sc::fnv(h, &x.to_le_bytes());
            }
            h = sc::fnv(h, &w.gems(id).to_le_bytes());
            for s in 0..2 {
                h = sc::fnv(h, &w.cd(id, s).unwrap_or(u32::MAX).to_le_bytes());
            }
        }
        for t in 0..2 {
            h = sc::fnv(h, &w.tributed(t).to_le_bytes());
        }
        sc::fnv(h, &crate::game::timeline_pos(eng, self.g).unwrap_or(0).to_le_bytes())
    }

    /// Items and consumables at shop prices (a proxy for gold spent: gold earned is not readable).
    fn item_value(&self, id: u32) -> u32 {
        let w = self.w();
        let items: u32 = w.items(id).iter().map(|&(it, n)| n * if it % 2 == 1 { if it / 6 == 12 { 750 } else { 150 } } else { 30 }).sum();
        items + 10 * w.cons(id).iter().sum::<u32>()
    }
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

fn cheb(a: (i32, i32), b: (i32, i32)) -> i32 {
    (a.0 - b.0).abs().max((a.1 - b.1).abs())
}

fn splitmix(s: &mut u64) -> u64 {
    *s = s.wrapping_add(0x9E37_79B9_7F4A_7C15);
    let mut z = *s;
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    z ^ (z >> 31)
}

// ---------------------------------------------------------------- pass 1

struct Pass1 {
    /// Round start digests and alive sets (bit k: champs[k] alive), by round.
    digest: HashMap<u32, u64>,
    alive: HashMap<u32, u64>,
    /// Fork candidates: (round, champion, trigger).
    cands: Vec<(u32, u32, String)>,
    /// (round, victim, killer if a champion's turn killed it)
    deaths: Vec<(u32, u32, Option<u32>)>,
    rounds: u32,
    finished: bool,
    winner: Option<u32>,
    replay: Vec<u8>,
    oof: [u32; 2],
    errors: [u32; 2],
    turns: u64,
    ms: f64,
    draft_ms: f64,
    branches: HashMap<char, u64>,
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

fn save_replay(eng: &crate::engine::Eng, g: Game) -> Result<Vec<u8>> {
    ck(unsafe { (eng.Game_SaveReplay)(g) }, "Game_SaveReplay")?;
    let (mut p, mut n) = (std::ptr::null::<u8>(), 0usize);
    ck(unsafe { (eng.Game_FileBuffer)(g, &mut p, &mut n) }, "Game_FileBuffer")?;
    Ok(unsafe { std::slice::from_raw_parts(p, n) }.to_vec())
}

struct Lab<'a> {
    rt: &'a Runtime,
    pr: Progs,
    clean: Snapshot,
    o: Opts,
    /// CPU ms restoring forks for arms (this game).
    restore_ms: f64,
}

impl<'a> Lab<'a> {
    /// Whether team `t` is a decider team in a game whose sides are `swap`ped.
    fn decides(&self, t: u32, swap: bool) -> bool {
        let bot = t ^ swap as u32;
        self.o.decider == 2 || self.o.decider == bot
    }

    fn pass1(&mut self, map: &[u8], swap: bool) -> Result<Pass1> {
        let t0 = Instant::now();
        let eng = self.rt.eng;
        let mut m = Match::new(self.rt, &mut self.pr, &self.clean, map, self.o.lab_flags, self.o.log_limit)?;
        let mut p = Pass1 {
            digest: HashMap::new(), alive: HashMap::new(), cands: Vec::new(), deaths: Vec::new(), rounds: 0, finished: false, winner: None,
            replay: Vec::new(), oof: [0; 2], errors: [0; 2], turns: 0, ms: 0.0, draft_ms: m.draft_ms, branches: HashMap::new(),
        };
        let kills = self.o.triggers.iter().any(|t| matches!(t, Trig::Kill(_)));
        let branch: Vec<u8> = self.o.triggers.iter().filter_map(|t| if let Trig::Branch(b) = t { Some(b.clone()) } else { None }).flatten().collect();
        let n = m.champs.len();
        let mut cur = 0u32;
        let mut alive_prev: Vec<bool> = vec![true; n];
        let mut near_prev: HashMap<u32, bool> = HashMap::new();
        let mut every_k = 0usize;
        loop {
            let st = m.boundary()?;
            if st[0] == 2 || st[2] > self.o.max_rounds {
                break;
            }
            if st[2] != cur {
                cur = st[2];
                p.digest.insert(cur, m.digest(eng));
                let pos = m.positions();
                let mut mask = 0u64;
                for (k, q) in pos.iter().enumerate() {
                    if q.2 {
                        mask |= 1 << k;
                    }
                    if alive_prev[k] && !q.2 && !kills {
                        p.deaths.push((cur - 1, q.0, None));
                    }
                    alive_prev[k] = q.2;
                }
                p.alive.insert(cur, mask);
                let deciders: Vec<&(u32, u32, bool, i32, i32)> = pos.iter().filter(|q| q.2 && self.decides(q.1, swap)).collect();
                for q in &deciders {
                    let d = pos.iter().filter(|e| e.2 && e.1 != q.1).map(|e| cheb((q.3, q.4), (e.3, e.4))).min().unwrap_or(i32::MAX);
                    for tr in &self.o.triggers {
                        match *tr {
                            Trig::Near(r) => {
                                let now = d <= r;
                                if now && !near_prev.get(&q.0).copied().unwrap_or(false) {
                                    p.cands.push((cur, q.0, format!("near:{r}")));
                                }
                            }
                            Trig::Close(r) if d <= r => p.cands.push((cur, q.0, format!("close:{r}"))),
                            _ => {}
                        }
                    }
                    let r = self.o.triggers.iter().find_map(|t| if let Trig::Near(r) = t { Some(*r) } else { None });
                    if let Some(r) = r {
                        near_prev.insert(q.0, d <= r);
                    }
                }
                for tr in &self.o.triggers {
                    if let Trig::Every(k) = *tr {
                        if k > 0 && cur % k == 0 && !deciders.is_empty() {
                            let q = deciders[every_k % deciders.len()];
                            every_k += 1;
                            p.cands.push((cur, q.0, format!("every:{k}")));
                        }
                    }
                }
            }
            let c = st[3];
            let before = if kills { m.positions() } else { Vec::new() };
            m.play_turn(self.rt, &mut self.pr, st)?;
            p.turns += 1;
            let b = m.branch(c, cur);
            if b != 0 {
                *p.branches.entry(b as char).or_default() += 1;
            }
            if !branch.is_empty() && b != 0 && branch.contains(&b) && self.decides(m.team[&c], swap) {
                p.cands.push((cur, c, format!("branch:{}", b as char)));
            }
            if kills {
                let w = m.w();
                for q in &before {
                    if q.2 && !w.alive(q.0) {
                        let killer = (m.team[&c] != q.1).then_some(c);
                        p.deaths.push((cur, q.0, killer));
                    }
                }
            }
        }
        if kills {
            // Deaths outside a champion's turn (camps), seen at round starts.
            let mut seen: HashSet<(u32, u32)> = p.deaths.iter().map(|d| (d.0, d.1)).collect();
            let ids: Vec<u32> = m.champs.iter().map(|c| c.0).collect();
            let mut rs: Vec<u32> = p.alive.keys().copied().collect();
            rs.sort();
            for w in rs.windows(2) {
                let (a, b) = (p.alive[&w[0]], p.alive[&w[1]]);
                for (k, &id) in ids.iter().enumerate() {
                    if a >> k & 1 == 1 && b >> k & 1 == 0 && !(w[0]..=w[1]).any(|r| seen.contains(&(r, id))) {
                        seen.insert((w[0], id));
                        p.deaths.push((w[0], id, None));
                    }
                }
            }
        }
        for &(r, v, k) in &p.deaths {
            for tr in &self.o.triggers {
                match *tr {
                    Trig::Death(nr) if self.decides(m.team[&v], swap) => p.cands.push((r.saturating_sub(nr), v, format!("death:{nr}"))),
                    Trig::Kill(nr) => {
                        if let Some(k) = k.filter(|k| self.decides(m.team[k], swap)) {
                            p.cands.push((r.saturating_sub(nr), k, format!("kill:{nr}")));
                        }
                    }
                    _ => {}
                }
            }
        }
        let fin = m.w().st();
        p.rounds = fin[2];
        p.finished = fin[0] == 2;
        p.winner = winner(eng, m.g);
        p.replay = save_replay(eng, m.g)?;
        p.oof = m.oof;
        p.errors = m.errors;
        p.ms = t0.elapsed().as_secs_f64() * 1e3;
        Ok(p)
    }

    /// The fork points: candidates with the decider alive at the round start, merged per (round, champion), at least
    /// `gap` rounds apart per champion, at most `max_forks` (a seeded choice), in game order.
    fn choose(&self, p: &Pass1, champs: &[(u32, u32, u32)], seed: u64) -> Vec<(u32, u32, Vec<String>)> {
        let k_of: HashMap<u32, usize> = champs.iter().enumerate().map(|(k, c)| (c.0, k)).collect();
        let mut c: Vec<(u32, u32, String)> = p
            .cands
            .iter()
            .filter(|x| x.0 >= self.o.min_round && x.0 <= p.rounds && p.alive.get(&x.0).is_some_and(|m| m >> k_of[&x.1] & 1 == 1))
            .cloned()
            .collect();
        c.sort_by(|a, b| (a.0, a.1).cmp(&(b.0, b.1)));
        let mut merged: Vec<(u32, u32, Vec<String>)> = Vec::new();
        for (r, id, t) in c {
            match merged.last_mut() {
                Some(l) if l.0 == r && l.1 == id => {
                    if !l.2.contains(&t) {
                        l.2.push(t)
                    }
                }
                _ => merged.push((r, id, vec![t])),
            }
        }
        let mut last: HashMap<u32, u32> = HashMap::new();
        merged.retain(|x| {
            if last.get(&x.1).is_some_and(|&l| x.0 < l + self.o.gap.max(1)) {
                return false;
            }
            last.insert(x.1, x.0);
            true
        });
        if merged.len() > self.o.max_forks {
            let mut s = seed;
            let mut keyed: Vec<(u64, (u32, u32, Vec<String>))> = merged.into_iter().map(|x| (splitmix(&mut s), x)).collect();
            keyed.sort_by_key(|x| x.0);
            keyed.truncate(self.o.max_forks);
            merged = keyed.into_iter().map(|x| x.1).collect();
            merged.sort_by(|a, b| (a.0, a.1).cmp(&(b.0, b.1)));
        }
        merged
    }

    /// One game: pass 1, the fork points, pass 2 with every fork's arms. Lines: ("G"|"F"|"A", json).
    fn run(&mut self, line: &str, root: &Path, emit: &mut dyn FnMut(&str)) {
        let t0 = Instant::now();
        let c0 = sc::cpu_ms();
        let v: Value = match serde_json::from_str(line) {
            Ok(v) => v,
            Err(e) => {
                emit(&json!({"type": "game", "error": format!("bad game line: {e}")}).to_string());
                return;
            }
        };
        let id = v["id"].as_str().unwrap_or("?").to_string();
        let swap = v["swap"].as_bool().unwrap_or(false);
        let res = (|| -> Result<Value> {
            let mp = v["map"].as_str().ok_or_else(|| anyhow!("game line: map missing"))?;
            let path = [PathBuf::from(mp), root.join(mp)].into_iter().find(|p| p.is_file()).ok_or_else(|| anyhow!("map {mp} not found"))?;
            let map = std::fs::read(&path)?;
            if swap {
                self.pr.progs.swap(0, 1);
                self.pr.blk.swap(0, 1);
                self.pr.act.swap(0, 1);
            }
            let r = self.game(&id, &path, &map, swap, emit);
            if swap {
                self.pr.progs.swap(0, 1);
                self.pr.blk.swap(0, 1);
                self.pr.act.swap(0, 1);
            }
            r
        })();
        let mut g = match res {
            Ok(g) => g,
            Err(e) => json!({"error": format!("{e:#}")}),
        };
        g["type"] = json!("game");
        g["id"] = json!(id);
        g["swap"] = json!(swap);
        g["wall_ms"] = json!(t0.elapsed().as_secs_f64() * 1e3);
        g["cpu_ms"] = json!(sc::cpu_ms() - c0);
        emit(&g.to_string());
    }

    fn game(&mut self, id: &str, path: &Path, map: &[u8], swap: bool, emit: &mut dyn FnMut(&str)) -> Result<Value> {
        let eng = self.rt.eng;
        let c1 = sc::cpu_ms();
        let p1 = self.pass1(map, swap)?;
        let pass1_cpu = sc::cpu_ms() - c1;
        let mut m = Match::new(self.rt, &mut self.pr, &self.clean, map, self.o.lab_flags, self.o.log_limit)?;
        let seed = sc::fnv(sc::fnv(sc::FNV0, map), &self.o.seed.to_le_bytes()) ^ swap as u64;
        let forks = self.choose(&p1, &m.champs, seed);
        let mut g = json!({
            "map": path.to_string_lossy(), "bots": if swap { [&self.o.bots[1], &self.o.bots[0]] } else { [&self.o.bots[0], &self.o.bots[1]] },
            "rounds": p1.rounds, "finished": p1.finished, "winner": p1.winner, "out_of_fuel": p1.oof, "errors": p1.errors,
            "pass1_ms": p1.ms, "pass1_cpu_ms": pass1_cpu, "draft_ms": p1.draft_ms, "turns": p1.turns, "candidates": p1.cands.len(),
            "forks": forks.len(), "deaths": p1.deaths.len(),
            "champions": m.champs.iter().map(|c| json!({"id": c.0, "team": c.1, "type": c.2})).collect::<Vec<_>>(),
        });
        if !p1.branches.is_empty() {
            let mut b: Vec<(char, u64)> = p1.branches.iter().map(|(k, v)| (*k, *v)).collect();
            b.sort();
            g["branches"] = Value::Object(b.iter().map(|(k, v)| (k.to_string(), json!(v))).collect());
        }
        if let Some(d) = &self.o.replays {
            let safe: String = id.chars().map(|c| if c.is_ascii_alphanumeric() || c == '-' || c == '#' { c } else { '_' }).collect();
            std::fs::create_dir_all(d)?;
            std::fs::write(d.join(format!("{safe}.repl26a")), &p1.replay)?;
        }
        if self.o.digests {
            let mut d: Vec<(u32, u64)> = p1.digest.iter().map(|(r, h)| (*r, *h)).collect();
            d.sort();
            g["digests"] = json!(d.iter().map(|x| format!("{:016x}", x.1)).collect::<Vec<_>>());
            g["digest_first_round"] = json!(d.first().map(|x| x.0));
        }
        // ---- pass 2 ----
        let c2 = sc::cpu_ms();
        let mut cur = 0u32;
        let mut next = 0usize;
        let mut main_ok = true;
        let mut first_diff: Option<u32> = None;
        let mut checked = 0u32;
        let mut arms_n = 0usize;
        let mut arm_cpu = 0.0;
        let mut none_bad = 0usize;
        let mut snap_cpu = 0.0;
        let mut legal_cpu = 0.0;
        let mut fork_errors = Vec::new();
        loop {
            if next >= forks.len() && !self.o.full {
                break;
            }
            let st = m.boundary()?;
            if st[0] == 2 || st[2] > self.o.max_rounds {
                break;
            }
            if st[2] != cur {
                cur = st[2];
                // The main line after its forks is the original game.
                if let Some(&d) = p1.digest.get(&cur) {
                    checked += 1;
                    if m.digest(eng) != d && first_diff.is_none() {
                        first_diff = Some(cur);
                        main_ok = false;
                    }
                }
            }
            while next < forks.len() && (forks[next].0 < cur || (forks[next].0 == cur && !m.bots.contains_key(&forks[next].1))) {
                fork_errors.push(format!("fork {next} at ({}, c{}) missed", forks[next].0, forks[next].1));
                next += 1;
            }
            if next < forks.len() && forks[next].0 == cur && forks[next].1 == st[3] {
                let fk = forks[next].clone();
                let k = next;
                next += 1;
                let t = sc::cpu_ms();
                let Some(snap) = m.snap() else {
                    fork_errors.push(format!("fork {k}: a bot could not be snapshotted"));
                    continue;
                };
                snap_cpu += sc::cpu_ms() - t;
                match self.fork(&mut m, &snap, &p1, id, k, &fk, swap, emit) {
                    Ok(x) => {
                        arms_n += x.0;
                        arm_cpu += x.1;
                        legal_cpu += x.2;
                        none_bad += x.3;
                    }
                    Err(e) => fork_errors.push(format!("fork {k}: {e:#}")),
                }
                if !m.restore(&snap) {
                    fork_errors.push(format!("fork {k}: the main line could not be restored; game stopped"));
                    break;
                }
                continue;
            }
            m.play_turn(self.rt, &mut self.pr, st)?;
        }
        g["pass2_cpu_ms"] = json!(sc::cpu_ms() - c2);
        g["arms"] = json!(arms_n);
        g["arm_cpu_ms"] = json!(arm_cpu);
        g["snap_cpu_ms"] = json!(snap_cpu);
        g["restore_cpu_ms"] = json!(std::mem::take(&mut self.restore_ms));
        g["legal_cpu_ms"] = json!(legal_cpu);
        g["check"] = json!({"main_rounds": checked, "main_ok": main_ok, "main_first_diff": first_diff, "none_arms_differing": none_bad});
        if self.o.full {
            let fin = m.w().st();
            let rep = save_replay(eng, m.g)?;
            g["check"]["replay_identical"] = json!(rep == p1.replay);
            g["check"]["pass2_rounds"] = json!(fin[2]);
        }
        if !fork_errors.is_empty() {
            g["fork_errors"] = json!(fork_errors);
        }
        Ok(g)
    }

    /// The arms at one fork (the match is at the decider's boundary, `snap` its state). Returns (arms played, their
    /// CPU ms, the legal-action enumeration's CPU ms, `none` arms whose digests differed from pass 1's).
    #[allow(clippy::too_many_arguments)]
    fn fork(&mut self, m: &mut Match, snap: &Snap, p1: &Pass1, gid: &str, k: usize, fk: &(u32, u32, Vec<String>), swap: bool,
            emit: &mut dyn FnMut(&str)) -> Result<(usize, f64, f64, usize)> {
        let (round, dec, ref trig) = *fk;
        let w = m.w();
        let dteam = m.team[&dec];
        let mut champs = Vec::new();
        for &(id, t, ty) in &m.champs {
            let alive = w.alive(id);
            let c = if alive { w.champ(id) } else { None };
            champs.push(json!({"id": id, "team": t, "type": ty, "alive": alive, "x": c.map(|c| c.x), "y": c.map(|c| c.y),
                "hp": c.map(|c| sc::round1(c.hp as f64)), "max_hp": c.map(|c| sc::round1(c.max as f64)), "gems": w.gems(id), "gold": w.gold(id, t),
                "items": m.item_value(id), "cd": [w.cd(id, 0), w.cd(id, 1)]}));
        }
        let t = sc::cpu_ms();
        let sweep = self.o.arms.iter().any(|a| matches!(a, ArmSpec::Sweep));
        let (legal, chan) = if sweep { legal_actions(m, snap, dec, self.o.ground_all) } else { (Vec::new(), false) };
        let legal_ms = sc::cpu_ms() - t;
        let (eng_b, bot_b) = snap.bytes();
        emit(&json!({"type": "fork", "game": gid, "fork": k, "round": round, "decider": dec, "team": dteam, "swap": swap,
            "trigger": trig, "trib": [w.tributed(0), w.tributed(1)], "champions": champs,
            "legal": legal.iter().map(|a| a.json(1)).collect::<Vec<_>>(), "channel_cancelled": chan, "snapshot_kib": [eng_b >> 10, bot_b >> 10], "legal_cpu_ms": legal_ms}).to_string());
        // The arms, in order.
        let mut arms: Vec<Arm> = Vec::new();
        for a in &self.o.arms {
            match a {
                ArmSpec::None => arms.push(Arm { label: json!({"kind": "none"}), ops: Vec::new(), later: None, span: 1, verdict: None }),
                ArmSpec::End => {
                    for &h in &self.o.holds {
                        let label = if h == 1 { json!({"kind": "end"}) } else { json!({"kind": "end", "span": h}) };
                        arms.push(Arm { label, ops: vec![Op { op: 7, slot: 0, x: 0, y: 0, target: 0 }], later: None, span: h, verdict: None });
                    }
                }
                ArmSpec::Verdict(what, v, span) => arms.push(Arm {
                    label: json!({"kind": if *what == 0 { "home" } else { "chase" }, "verdict": v, "span": span}),
                    ops: Vec::new(),
                    later: None,
                    span: *span,
                    verdict: Some((*what, *v)),
                }),
                ArmSpec::Sweep => {
                    for &h in &self.o.holds {
                        for a in &legal {
                            if a.kind == "end" && self.o.arms.iter().any(|x| matches!(x, ArmSpec::End)) {
                                continue;
                            }
                            let later = (a.kind == "walk" && h > 1).then(|| vec![a.op_for(h, m.size)]);
                            let mut label = a.json(h);
                            if let Some(l) = &later {
                                label["toward"] = json!([l[0].x, l[0].y]);
                            }
                            arms.push(Arm { label, ops: vec![a.op_for(1, m.size)], later, span: h, verdict: None });
                        }
                    }
                }
            }
        }
        let t = sc::cpu_ms();
        let mut bad = 0usize;
        let mut done = 0usize;
        let mut far: Vec<(i32, u32)> = {
            let pos = m.positions();
            let me = pos.iter().find(|p| p.0 == dec).map_or((0, 0), |p| (p.3, p.4));
            pos.iter().filter(|p| p.0 != dec && p.2 && m.act.contains_key(&p.0)).map(|p| (-cheb(me, (p.3, p.4)), p.0)).collect()
        };
        far.sort();
        let mut reps: Vec<(i64, Option<u32>)> = std::iter::once((0, None)).chain(self.o.jitter.iter().map(|&j| (j, None))).collect();
        reps.extend(far.iter().take(self.o.skip_reps).map(|f| (0, Some(f.1))));
        for (j, arm) in arms.iter().enumerate() {
            for (rep, &(jit, skip)) in reps.iter().enumerate() {
                let t = sc::cpu_ms();
                if !m.restore(snap) {
                    bail!("could not restore the fork for arm {j}");
                }
                self.restore_ms += sc::cpu_ms() - t;
                if let Some(t) = skip {
                    if let (Some(&a), Some(mem)) = (m.act.get(&t), m.bots.get_mut(&t).and_then(|b| b.memory())) {
                        sc::wr_i32(mem, a + la::ROUND, round as i32 + 1);
                        sc::wr_i32(mem, a + la::N, 1);
                        mem[a + la::OPS] = 7;
                    }
                }
                if jit != 0 {
                    // The restored meters' next refuel (each bot's next turn) gets the shifted interval.
                    for b in m.bots.values_mut() {
                        b.meter.interval = (b.meter.interval as i64 + jit).max(1000) as u64;
                    }
                }
                let mut r = self.arm(m, p1, round, dec, arm, rep > 0)?;
                if rep == 0 && arm.ops.is_empty() && arm.verdict.is_none() && r["check"]["match"] == json!(false) {
                    bad += 1;
                }
                r["type"] = json!("arm");
                r["game"] = json!(gid);
                r["fork"] = json!(k);
                r["arm"] = json!(j);
                r["round"] = json!(round);
                r["decider"] = json!(dec);
                r["team"] = json!(dteam);
                r["label"] = arm.label.clone();
                if rep > 0 {
                    r["rep"] = json!(rep);
                    r["jitter"] = json!(jit);
                    if let Some(t) = skip {
                        r["skip"] = json!(t);
                    }
                }
                emit(&r.to_string());
                done += 1;
            }
        }
        Ok((done, sc::cpu_ms() - t, legal_ms, bad))
    }

    /// One continuation from the fork (the match restored to it) for H rounds.
    fn arm(&mut self, m: &mut Match, p1: &Pass1, start: u32, dec: u32, arm: &Arm, perturbed: bool) -> Result<Value> {
        let eng = self.rt.eng;
        let h = self.o.horizon();
        let n = m.champs.len();
        let ids: Vec<u32> = m.champs.iter().map(|c| c.0).collect();
        let k_of: HashMap<u32, usize> = ids.iter().enumerate().map(|(k, &id)| (id, k)).collect();
        // Inputs: the decider's forced ops or verdict for this round.
        let write_inputs = |m: &mut Match, round: u32| {
            let ops = if round > start { arm.later.as_ref().unwrap_or(&arm.ops) } else { &arm.ops };
            if let (Some(&a), false) = (m.act.get(&dec), ops.is_empty()) {
                if let Some(mem) = m.mem(dec) {
                    sc::wr_i32(mem, a + la::ROUND, round as i32);
                    sc::wr_i32(mem, a + la::N, ops.len().min(4) as i32);
                    for (i, o) in ops.iter().take(4).enumerate() {
                        let b = a + la::OPS + la::OP * i;
                        mem[b] = o.op as u8;
                        mem[b + 1] = o.slot as u8;
                        mem[b + 2..b + 4].copy_from_slice(&(o.x as i16).to_le_bytes());
                        mem[b + 4..b + 6].copy_from_slice(&(o.y as i16).to_le_bytes());
                        mem[b + 6..b + 8].fill(0);
                        mem[b + 8..b + 12].copy_from_slice(&o.target.to_le_bytes());
                    }
                }
            }
            if let (Some(&o), Some((what, v))) = (m.blk.get(&dec), arm.verdict) {
                if let Some(mem) = m.mem(dec) {
                    let (ro, fo) = if what == 0 { (lb::HOME_ROUND, lb::HOME_FORCE) } else { (lb::CHASE_ROUND, lb::CHASE_FORCE) };
                    sc::wr_i32(mem, o + ro, round as i32);
                    sc::wr_i32(mem, o + fo, v);
                }
            }
        };
        if !arm.ops.is_empty() && !m.act.contains_key(&dec) {
            bail!("the decider's bot has no forced-action block (make it with tools/combatlab/labify.py)");
        }
        if arm.verdict.is_some() && !m.blk.contains_key(&dec) {
            bail!("the decider's bot has no lab control block");
        }
        write_inputs(m, start);
        let w = m.w();
        let mut deaths = vec![0u32; n];
        let mut kills = vec![0u32; n];
        let mut work = vec![0u32; n];
        let mut turns = vec![0u32; n];
        let mut alive: Vec<bool> = ids.iter().map(|&id| w.alive(id)).collect();
        let mut pos = m.positions();
        let mut marks = serde_json::Map::new();
        let mut cur = start;
        let mut decs = Vec::new();
        let mut first: Option<Value> = None;
        let mut check_n = 0u32;
        let mut diff: Option<u32> = None;
        let mut stop = "rounds";
        let account = |w: &W, actor: Option<u32>, alive: &mut Vec<bool>, deaths: &mut Vec<u32>, kills: &mut Vec<u32>, team: &HashMap<u32, u32>| {
            for (k, &id) in ids.iter().enumerate() {
                if alive[k] && !w.alive(id) {
                    deaths[k] += 1;
                    if let Some(a) = actor.filter(|a| team[a] != team[&id]) {
                        kills[k_of[&a]] += 1;
                    }
                    alive[k] = false;
                } else if !alive[k] && w.alive(id) {
                    alive[k] = true;
                }
            }
        };
        let mark = |m: &Match, deaths: &[u32], kills: &[u32], work: &[u32], turns: &[u32]| -> Value {
            let w = m.w();
            let mut cs = serde_json::Map::new();
            let mut teams = [[0u32; 7]; 2];
            for (k, &(id, t, _)) in m.champs.iter().enumerate() {
                let a = w.alive(id);
                let c = if a { w.champ(id) } else { None };
                let (gems, gold, items) = (if a { w.gems(id) } else { 0 }, w.gold(id, t), m.item_value(id));
                cs.insert(id.to_string(), json!({"alive": a, "deaths": deaths[k], "kills": kills[k], "hp": c.map(|c| sc::round1(c.hp as f64)),
                    "max_hp": c.map(|c| sc::round1(c.max as f64)), "gems": gems, "gold": gold, "items": items, "work": work[k], "turns": turns[k]}));
                let tt = &mut teams[t as usize];
                tt[0] += deaths[k];
                tt[1] += kills[k];
                tt[2] += gems;
                tt[3] += gold;
                tt[4] += items;
                tt[5] += work[k];
            }
            let tv: Vec<Value> = (0..2u32)
                .map(|t| {
                    let x = teams[t as usize];
                    json!({"trib": w.tributed(t), "deaths": x[0], "kills": x[1], "gems": x[2], "gold": x[3], "items": x[4], "work": x[5]})
                })
                .collect();
            json!({"champions": cs, "teams": tv})
        };
        let check = arm.ops.is_empty() && arm.verdict.is_none() && !perturbed;
        let mut trace: Vec<Value> = Vec::new();
        let snap_pos = |m: &Match, round: u32| -> Value {
            let w = m.w();
            let cs: Vec<Value> = m.champs.iter().map(|&(id, _, _)| {
                let a = w.alive(id);
                let c = if a { w.champ(id) } else { None };
                json!([id, c.map_or(-1, |c| c.x), c.map_or(-1, |c| c.y), c.map_or(0.0, |c| sc::round1(c.hp as f64)), a])
            }).collect();
            json!([round, cs])
        };
        if self.o.trace > 0 {
            trace.push(snap_pos(m, start));
        }
        loop {
            let st = m.boundary()?;
            let w = m.w();
            account(&w, None, &mut alive, &mut deaths, &mut kills, &m.team);
            if st[0] == 2 {
                stop = "game_over";
                break;
            }
            if st[2] != cur {
                cur = st[2];
                let played = cur - start;
                if self.o.marks.contains(&played) {
                    marks.insert(played.to_string(), mark(m, &deaths, &kills, &work, &turns));
                }
                if check {
                    if let Some(&d) = p1.digest.get(&cur) {
                        check_n += 1;
                        if diff.is_none() && m.digest(eng) != d {
                            diff = Some(cur);
                        }
                    }
                }
                if played < self.o.trace {
                    trace.push(snap_pos(m, cur));
                }
                if played >= h || cur > self.o.max_rounds {
                    break;
                }
                pos = m.positions();
                // A hold: the decider's inputs move to this round.
                if arm.span > 1 && cur < start + arm.span as u32 {
                    write_inputs(m, cur);
                }
            }
            let c = st[3];
            let kc = k_of[&c];
            let me = pos[kc];
            let free = me.2 && !pos.iter().any(|e| e.2 && e.1 != me.1 && cheb((me.3, me.4), (e.3, e.4)) <= self.o.work_radius);
            // The decider's fork turn: every champion's health and shield before it, for what it hit.
            let before: Vec<(u32, f64)> = if c == dec && first.is_none() {
                let w = m.w();
                ids.iter().filter(|&&id| w.alive(id)).map(|&id| (id, w.champ(id).map_or(0.0, |x| x.hp as f64) + w.shield(id) as f64)).collect()
            } else {
                Vec::new()
            };
            m.play_turn(self.rt, &mut self.pr, st)?;
            turns[kc] += 1;
            let b = m.branch(c, cur);
            if free && b != 0 && self.o.work.contains(&b) {
                work[kc] += 1;
            }
            if c == dec {
                if first.is_none() {
                    let mut f = json!({"branch": if b != 0 { (b as char).to_string() } else { String::new() }});
                    if let (Some(&a), false) = (m.act.get(&dec), arm.ops.is_empty()) {
                        if let Some(mem) = m.mem(dec) {
                            f["done_round"] = json!(sc::rd_i32(mem, a + la::DONE_ROUND));
                            f["res"] = json!((0..arm.ops.len().min(4)).map(|i| sc::rd_i32(mem, a + la::RES + 4 * i)).collect::<Vec<_>>());
                        }
                    }
                    let w = m.w();
                    if let Some(ch) = w.champ(dec).filter(|_| w.alive(dec)) {
                        f["to"] = json!([ch.x, ch.y]);
                    }
                    f["cd"] = json!([w.cd(dec, 0), w.cd(dec, 1)]);
                    // Health and shield lost in it (a death: all it had).
                    let hits: Vec<Value> = before
                        .iter()
                        .filter_map(|&(id, v0)| {
                            let v1 = if w.alive(id) { w.champ(id).map_or(0.0, |x| x.hp as f64) + w.shield(id) as f64 } else { 0.0 };
                            (v0 - v1 > 1e-3).then(|| json!([id, sc::round1(v0 - v1), !w.alive(id)]))
                        })
                        .collect();
                    f["hits"] = json!(hits);
                    if self.o.decisions {
                        f["decision"] = m.decision(dec, cur);
                    }
                    first = Some(f);
                }
                if decs.len() < 16 {
                    decs.push(if b != 0 { b as char } else { '.' });
                }
            }
            let w = m.w();
            account(&w, Some(c), &mut alive, &mut deaths, &mut kills, &m.team);
        }
        // A game that ended early: its remaining marks are its end.
        if stop == "game_over" {
            let end = mark(m, &deaths, &kills, &work, &turns);
            for &mk in &self.o.marks {
                marks.entry(mk.to_string()).or_insert_with(|| end.clone());
            }
        }
        let mut r = json!({"stop": stop, "end_round": cur, "at": marks, "first": first, "branches": decs.iter().collect::<String>()});
        if check {
            r["check"] = json!({"rounds": check_n, "match": diff.is_none(), "first_diff": diff});
        }
        if self.o.trace > 0 {
            r["trace"] = json!(trace);
        }
        if self.o.hash {
            r["hash"] = json!(format!("{:016x}", sc::mem_hash()));
        }
        Ok(r)
    }
}

// ---------------------------------------------------------------- arms and legal actions

#[derive(Clone, Copy, Debug)]
struct Op {
    op: i8,
    slot: i8,
    x: i32,
    y: i32,
    target: u32,
}

struct Arm {
    label: Value,
    ops: Vec<Op>,
    /// A hold's ops on its later turns (a held walk goes on toward the tile `span` steps out); None: `ops`.
    later: Option<Vec<Op>>,
    span: i32,
    verdict: Option<(u8, i32)>,
}

/// One legal one-turn action of the decider at a fork.
#[derive(Clone, Debug)]
struct Act {
    kind: &'static str,
    slot: i8,
    x: i32,
    y: i32,
    target: u32,
    /// A ground cast's enemy champions within 1 of its tile.
    hits: Vec<u32>,
    /// Walk direction (a hold walks on toward the tile `span` steps out).
    dir: (i32, i32),
}

impl Act {
    fn json(&self, span: i32) -> Value {
        let mut v = json!({"kind": self.kind});
        match self.kind {
            "walk" | "dash" | "ground" => {
                v["x"] = json!(self.x);
                v["y"] = json!(self.y);
            }
            "attack" | "cast_enemy" | "cast_ally" => v["target"] = json!(self.target),
            _ => {}
        }
        if self.kind.starts_with("cast") || self.kind == "dash" || self.kind == "ground" {
            v["slot"] = json!(self.slot);
        }
        if !self.hits.is_empty() {
            v["hits"] = json!(self.hits);
        }
        if span != 1 {
            v["span"] = json!(span);
        }
        v
    }

    fn op_for(&self, span: i32, size: (i32, i32)) -> Op {
        let (op, mut x, mut y) = match self.kind {
            "walk" => (1, self.x, self.y),
            "dash" => (2, self.x, self.y),
            "attack" => (3, 0, 0),
            "cast_enemy" | "cast_ally" => (4, 0, 0),
            "ground" => (5, self.x, self.y),
            "cast_self" => (6, 0, 0),
            _ => (7, 0, 0),
        };
        if op == 1 && span > 1 {
            x = (self.x + self.dir.0 * (span - 1)).clamp(0, size.0 - 1);
            y = (self.y + self.dir.1 * (span - 1)).clamp(0, size.1 - 1);
        }
        Op { op, slot: self.slot, x, y, target: self.target }
    }
}

/// Every legal one-turn action of champion `c` at its input boundary, by trying each through the engine (restored
/// from `f` after every trial that changed it, and at the end): walks to the 8 neighbours, basic attacks on enemy
/// champions, and per ready slot a cast with no target, on each champion, and at each tile within 4 (a dash when it
/// moved us). Ground casts keep one tile per distinct set of enemy champions within 1 of it (none: dropped) unless
/// `ground_all`. "end" (the turn ends now) is always last.
fn legal_actions(m: &Match, f: &Snap, c: u32, ground_all: bool) -> (Vec<Act>, bool) {
    let w = m.w();
    let g = m.g;
    // A recall or tribute channel refuses every action (the forced ops cancel it first): the trials start from the
    // state with it cancelled.
    let chan = unsafe { shim::Game_Action_CancelChannel(g) } == 0;
    let base = if chan { Some(wengine::snapshot()) } else { None };
    let back = || {
        wengine::restore(base.as_ref().unwrap_or(&f.eng));
        wengine::set_host_state(f.host);
    };
    let mut out = Vec::new();
    let end = Act { kind: "end", slot: 0, x: 0, y: 0, target: 0, hits: Vec::new(), dir: (0, 0) };
    let Some(me) = w.champ(c).filter(|_| w.alive(c)) else {
        wengine::restore(&f.eng);
        wengine::set_host_state(f.host);
        return (vec![end], chan);
    };
    let my_team = m.team[&c];
    let pos = m.positions();
    let enemies: Vec<&(u32, u32, bool, i32, i32)> = pos.iter().filter(|e| e.2 && e.1 != my_team).collect();
    let xy = |x: i32, y: i32| x as u32 as u64 | (y as u32 as u64) << 32;
    for dy in -1..=1 {
        for dx in -1..=1 {
            if dx == 0 && dy == 0 {
                continue;
            }
            let (x, y) = (me.x + dx, me.y + dy);
            let mut o = 0u32;
            let r = unsafe { shim::Game_Action_Move(g, x as u32, y as u32, &mut o as *mut u32 as P) };
            if r == 0 {
                if o != 0 {
                    out.push(Act { kind: "walk", slot: 0, x, y, target: 0, hits: Vec::new(), dir: (dx, dy) });
                }
                back();
            }
        }
    }
    for e in &enemies {
        if unsafe { shim::Game_Action_Attack(g, 1 | (e.0 as u64) << 32) } == 0 {
            out.push(Act { kind: "attack", slot: 0, x: e.3, y: e.4, target: e.0, hits: Vec::new(), dir: (0, 0) });
            back();
        }
    }
    let mut ground_seen: HashSet<(i8, Vec<u32>)> = HashSet::new();
    let hits_at = |x: i32, y: i32| -> Vec<u32> {
        let mut h: Vec<u32> = enemies.iter().filter(|e| cheb((e.3, e.4), (x, y)) <= 1).map(|e| e.0).collect();
        h.sort();
        h
    };
    for s in 0..2u32 {
        if w.cd(c, s) != Some(0) {
            continue;
        }
        // The slot's kind (1 reset, 2 damage, 3 area, 4 stun, 5 heal, 6 dash, 7 shield) and targets (bits: camps,
        // enemies, allies, self, ground): the engine ignores a target the ability does not take.
        let mut props = [0u32; 9];
        unsafe { shim::Game_API_Champion_GetAbilityProps(g, OBS, c, s, props.as_mut_ptr() as P) };
        let (kind, targets) = (props[0], props[3]);
        let mut cast = |target: u64, x: i32, y: i32| -> bool {
            let mut o = 0u32;
            if unsafe { shim::Game_Action_Cast(g, s, target, xy(x, y), &mut o as *mut u32 as P) } != 0 {
                return false;
            }
            let moved = w.champ(c).is_some_and(|n| (n.x, n.y) != (me.x, me.y));
            back();
            o != 0 && (kind != 6 || moved)
        };
        if targets & 8 != 0 && cast(0, -1, -1) {
            out.push(Act { kind: "cast_self", slot: s as i8, x: 0, y: 0, target: 0, hits: Vec::new(), dir: (0, 0) });
        }
        if targets & 6 != 0 {
            for q in pos.iter().filter(|q| q.2 && q.0 != c) {
                let ally = q.1 == my_team;
                if (if ally { targets & 4 } else { targets & 2 }) != 0 && cast(1 | (q.0 as u64) << 32, -1, -1) {
                    out.push(Act { kind: if ally { "cast_ally" } else { "cast_enemy" }, slot: s as i8, x: q.3, y: q.4, target: q.0, hits: Vec::new(), dir: (0, 0) });
                }
            }
        }
        if targets & 16 != 0 || kind == 6 {
            let r = if kind == 6 { 2 } else { 4 };
            for dy in -r..=r {
                for dx in -r..=r {
                    let (x, y) = (me.x + dx, me.y + dy);
                    if x < 0 || y < 0 || x >= m.size.0 || y >= m.size.1 || !cast(0, x, y) {
                        continue;
                    }
                    let hits = hits_at(x, y);
                    if kind == 6 {
                        out.push(Act { kind: "dash", slot: s as i8, x, y, target: 0, hits, dir: (0, 0) });
                    } else if ground_all || (!hits.is_empty() && ground_seen.insert((s as i8, hits.clone()))) {
                        out.push(Act { kind: "ground", slot: s as i8, x, y, target: 0, hits, dir: (0, 0) });
                    }
                }
            }
        }
    }
    wengine::restore(&f.eng);
    wengine::set_host_state(f.host);
    out.push(end);
    (out, chan)
}

// ---------------------------------------------------------------- command line and workers

struct Cli {
    games: Vec<String>,
    out: Option<PathBuf>,
    jobs: usize,
    slots: Option<(PathBuf, usize)>,
    o: Opts,
}

fn parse_cli(args: &[String]) -> Result<Cli> {
    let mut c = Cli {
        games: Vec::new(),
        out: None,
        jobs: 1,
        slots: None,
        o: Opts {
            bots: [String::new(), String::new()], release: true, lab_flags: 2, decider: 0, triggers: Vec::new(), gap: 20, max_forks: 8,
            min_round: 2, seed: 0, marks: vec![10, 30, 60], arms: vec![ArmSpec::None, ArmSpec::Sweep], holds: vec![1], ground_all: false,
            work: b"FPGBTW".to_vec(), work_radius: 8, full: false, max_rounds: 2000, hash: false, log_limit: 1 << 20, decisions: false, digests: false, replays: None,
            jitter: Vec::new(),
            skip_reps: 0,
            trace: 0,
        },
    };
    let mut maps: Vec<String> = Vec::new();
    let mut games_file: Option<PathBuf> = None;
    let mut both = false;
    let mut slot_dir = None;
    let mut slot_n = 0usize;
    let mut trig_set = false;
    let mut i = 0;
    while i < args.len() {
        let a = args[i].as_str();
        let val = || -> Result<&String> { args.get(i + 1).ok_or_else(|| anyhow!("{a} needs a value")) };
        let mut step = 2;
        match a {
            "--bot-a" => c.o.bots[0] = val()?.clone(),
            "--bot-b" => c.o.bots[1] = val()?.clone(),
            "--maps" => maps.extend(val()?.split(',').filter(|s| !s.is_empty()).map(String::from)),
            "--games" => games_file = Some(PathBuf::from(val()?)),
            "--out" | "-o" => c.out = Some(PathBuf::from(val()?)),
            "--jobs" => c.jobs = val()?.parse()?,
            "--slot-dir" => slot_dir = Some(PathBuf::from(val()?)),
            "--slots" => slot_n = val()?.parse()?,
            "--fuel-quantum" | "--fuel" => crate::fuel::set_quantum(val()?.parse()?),
            "--lab-flags" => c.o.lab_flags = val()?.parse()?,
            "--decider" => {
                c.o.decider = match val()?.as_str() {
                    "a" => 0,
                    "b" => 1,
                    "both" => 2,
                    x => bail!("--decider a|b|both, not {x}"),
                }
            }
            "--trigger" | "--triggers" => {
                trig_set = true;
                for t in val()?.split(',').filter(|s| !s.is_empty()) {
                    let (k, v) = t.split_once(':').unwrap_or((t, ""));
                    c.o.triggers.push(match k {
                        "near" => Trig::Near(v.parse().unwrap_or(6)),
                        "close" => Trig::Close(v.parse().unwrap_or(6)),
                        "branch" => Trig::Branch(if v.is_empty() { b"RC".to_vec() } else { v.as_bytes().to_vec() }),
                        "death" => Trig::Death(v.parse().unwrap_or(10)),
                        "kill" => Trig::Kill(v.parse().unwrap_or(10)),
                        "every" => Trig::Every(v.parse().unwrap_or(50)),
                        _ => bail!("unknown trigger {t} (near:D, close:D, branch:CHARS, death:N, kill:N, every:K)"),
                    });
                }
            }
            "--gap" => c.o.gap = val()?.parse()?,
            "--max-forks" => c.o.max_forks = val()?.parse()?,
            "--min-round" => c.o.min_round = val()?.parse()?,
            "--seed" => c.o.seed = val()?.parse()?,
            "--marks" => c.o.marks = val()?.split(',').filter(|s| !s.is_empty()).map(|s| s.parse()).collect::<Result<_, _>>()?,
            "--arms" => {
                c.o.arms.clear();
                for t in val()?.split(',').filter(|s| !s.is_empty()) {
                    let p: Vec<&str> = t.split(':').collect();
                    c.o.arms.push(match p[0] {
                        "none" => ArmSpec::None,
                        "sweep" => ArmSpec::Sweep,
                        "end" => ArmSpec::End,
                        "home" | "chase" => {
                            ensure!(p.len() >= 2, "{t}: home:VERDICT[:ROUNDS]");
                            ArmSpec::Verdict((p[0] == "chase") as u8, p[1].parse()?, p.get(2).map_or(Ok(1), |s| s.parse())?)
                        }
                        _ => bail!("unknown arm {t} (none, sweep, end, home:V[:N], chase:V[:N])"),
                    });
                }
            }
            "--holds" => c.o.holds = val()?.split(',').filter(|s| !s.is_empty()).map(|s| s.parse()).collect::<Result<_, _>>()?,
            "--ground" => c.o.ground_all = val()? == "all",
            "--work" => c.o.work = val()?.as_bytes().to_vec(),
            "--work-radius" => c.o.work_radius = val()?.parse()?,
            "--max-rounds" => c.o.max_rounds = val()?.parse()?,
            "--log-limit" => c.o.log_limit = val()?.parse()?,
            "--both-sides" => {
                both = true;
                step = 1;
            }
            "--full" => {
                c.o.full = true;
                step = 1;
            }
            "--hash" => {
                c.o.hash = true;
                step = 1;
            }
            "--decisions" => {
                c.o.decisions = true;
                step = 1;
            }
            "--save-replays" => c.o.replays = Some(PathBuf::from(val()?)),
            "--skip-reps" => c.o.skip_reps = val()?.parse()?,
            "--trace" => c.o.trace = val()?.parse()?,
            "--jitter" => c.o.jitter = val()?.split(',').filter(|s| !s.is_empty()).map(|s| s.parse()).collect::<Result<_, _>>()?,
            "--digests" => {
                c.o.digests = true;
                step = 1;
            }
            "--debug" => {
                c.o.release = false;
                step = 1;
            }
            "--release" => {
                c.o.release = true;
                step = 1;
            }
            _ if a.starts_with("--") => bail!("unknown option {a}"),
            _ => bail!("unexpected argument {a}"),
        }
        i += step;
    }
    if !trig_set {
        c.o.triggers = vec![Trig::Near(6)];
    }
    ensure!(!c.o.bots[0].is_empty() && !c.o.bots[1].is_empty(), "--bot-a and --bot-b are required");
    ensure!(c.o.holds.iter().all(|&h| h >= 1), "--holds: each at least 1");
    for m in &maps {
        c.games.push(json!({"id": format!("{}#a", Path::new(m).file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default()), "map": m, "swap": false}).to_string());
        if both {
            c.games.push(json!({"id": format!("{}#b", Path::new(m).file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default()), "map": m, "swap": true}).to_string());
        }
    }
    if let Some(f) = games_file {
        let text = std::fs::read_to_string(&f).with_context(|| format!("reading {}", f.display()))?;
        c.games.extend(text.lines().filter(|l| !l.trim().is_empty()).map(String::from));
    }
    if let Some(d) = slot_dir {
        c.slots = Some((d, slot_n.max(1)));
    }
    Ok(c)
}

fn lab<'a>(rt: &'a Runtime, progs: [Arc<Program>; 2], o: Opts) -> Result<Lab<'a>> {
    ensure!(rt.eng.is_wasm(), "fastrunner forkgame needs FASTRUNNER_ENGINE=wasm");
    Ok(Lab { rt, pr: Progs { progs, blk: [None, None], act: [None, None] }, clean: wengine::snapshot(), o, restore_ms: 0.0 })
}

fn parts(c: &Cli) -> Result<(Runtime, [Arc<Program>; 2])> {
    let root = crate::project_root();
    let mut rt = crate::load_runtime()?;
    ensure!(crate::runtime::native_mode(), "fastrunner forkgame needs FASTRUNNER_MODE=native (bot snapshots)");
    let mut progs = Vec::new();
    for t in 0..2 {
        let w = crate::wasm_of(&crate::resolve_bot(&root, &c.o.bots[t])?, c.o.release)?;
        progs.push(rt.program(&w)?);
    }
    Ok((rt, [progs[0].clone(), progs[1].clone()]))
}

/// `__forkgame_worker ARGS`: reads "idx<TAB>game line" on stdin; writes "idx<TAB>L<TAB>json" lines, then "idx<TAB>D".
pub fn worker_main(args: &[String]) -> Result<i32> {
    let c = parse_cli(args)?;
    let (rt, progs) = parts(&c)?;
    let mut lab = lab(&rt, progs, c.o.clone())?;
    let root = crate::project_root();
    let stdin = std::io::stdin();
    let mut out = std::io::stdout().lock();
    for line in stdin.lock().lines() {
        let line = line?;
        let Some((idx, game)) = line.split_once('\t') else { continue };
        let mut emit = |v: &str| {
            let _ = writeln!(out, "{idx}\tL\t{v}");
        };
        lab.run(game, &root, &mut emit);
        writeln!(out, "{idx}\tD")?;
        out.flush()?;
    }
    Ok(0)
}

pub fn main(args: &[String]) -> Result<i32> {
    let c = parse_cli(args)?;
    let out_path = c.out.clone().ok_or_else(|| anyhow!("--out is required"))?;
    ensure!(!c.games.is_empty(), "no games (--maps or --games)");
    let lines = c.games.clone();
    let mut out = std::io::BufWriter::new(std::fs::File::create(&out_path)?);
    let t0 = Instant::now();
    let mut n_lines = 0usize;
    let jobs = c.jobs.max(1).min(lines.len());
    let root = crate::project_root();
    let mut slots = c.slots.as_ref().map(|(d, k)| crate::Slots::new(d, *k));
    if jobs == 1 {
        let (rt, progs) = parts(&c)?;
        let mut lab = lab(&rt, progs, c.o.clone())?;
        for (i, l) in lines.iter().enumerate() {
            let slot = slots.as_mut().map(|s| loop {
                if let Some(x) = s.take() {
                    s.set_waiting(false);
                    break x;
                }
                s.set_waiting(true);
                std::thread::sleep(std::time::Duration::from_millis(10));
            });
            let mut buf: Vec<String> = Vec::new();
            lab.run(l, &root, &mut |v| buf.push(v.to_string()));
            if let (Some(s), Some(x)) = (slots.as_mut(), slot) {
                s.release(x);
            }
            for j in buf {
                n_lines += 1;
                writeln!(out, "{j}")?;
            }
            out.flush()?;
            eprintln!("[{}/{}] {:.1}s", i + 1, lines.len(), t0.elapsed().as_secs_f64());
        }
    } else {
        drop(parts(&c)?);
        let exe = std::env::current_exe()?;
        let (tx, rx) = std::sync::mpsc::channel::<(usize, String)>();
        let mut inputs: Vec<Option<std::process::ChildStdin>> = Vec::new();
        let mut children = Vec::new();
        let mut current: Vec<Option<Option<crate::Slot>>> = Vec::new();
        let mut idle: Vec<usize> = Vec::new();
        let (mut next, mut busy, mut done) = (0usize, 0usize, 0usize);
        while done < lines.len() {
            while next < lines.len() && (!idle.is_empty() || children.len() < jobs) {
                let slot = match slots.as_mut() {
                    Some(s) => match s.take() {
                        Some(x) => Some(x),
                        None => break,
                    },
                    None => None,
                };
                let w = match idle.pop() {
                    Some(w) => w,
                    None => {
                        let mut cmd = std::process::Command::new(&exe);
                        cmd.env("FASTRUNNER_BUILT", "1").arg("__forkgame_worker").args(args);
                        cmd.stdin(std::process::Stdio::piped()).stdout(std::process::Stdio::piped());
                        let mut ch = cmd.spawn()?;
                        let so = ch.stdout.take().unwrap();
                        let w = children.len();
                        let tx = tx.clone();
                        std::thread::spawn(move || {
                            for line in std::io::BufReader::new(so).lines() {
                                let Ok(line) = line else { break };
                                if tx.send((w, line)).is_err() {
                                    break;
                                }
                            }
                            let _ = tx.send((w, "\u{0}eof".into()));
                        });
                        inputs.push(ch.stdin.take());
                        children.push(ch);
                        current.push(None);
                        w
                    }
                };
                let input = inputs[w].as_mut().unwrap();
                writeln!(input, "{next}\t{}", lines[next])?;
                input.flush()?;
                current[w] = Some(slot);
                next += 1;
                busy += 1;
            }
            if next >= lines.len() {
                for w in idle.drain(..) {
                    inputs[w] = None;
                }
            }
            let waiting = next < lines.len();
            if let Some(s) = slots.as_mut() {
                s.set_waiting(waiting);
            }
            let msg = if waiting && slots.is_some() {
                match rx.recv_timeout(std::time::Duration::from_millis(10)) {
                    Ok(m) => m,
                    Err(std::sync::mpsc::RecvTimeoutError::Timeout) => continue,
                    Err(_) => break,
                }
            } else {
                if busy == 0 {
                    break;
                }
                match rx.recv() {
                    Ok(m) => m,
                    Err(_) => break,
                }
            };
            let (w, line) = msg;
            if line == "\u{0}eof" {
                inputs[w] = None;
                idle.retain(|&x| x != w);
                if let Some(sl) = current[w].take() {
                    if let (Some(s), Some(sl)) = (slots.as_mut(), sl) {
                        s.release(sl);
                    }
                    writeln!(out, "{}", json!({"type": "game", "error": "worker died"}))?;
                    busy -= 1;
                    done += 1;
                }
                continue;
            }
            let mut p = line.splitn(3, '\t');
            let (_idx, k, j) = (p.next().unwrap_or(""), p.next().unwrap_or(""), p.next().unwrap_or(""));
            if k == "D" {
                if let Some(Some(sl)) = current[w].take() {
                    if let Some(s) = slots.as_mut() {
                        s.release(sl);
                    }
                }
                busy -= 1;
                done += 1;
                idle.push(w);
                eprintln!("[{done}/{}] {:.1}s", lines.len(), t0.elapsed().as_secs_f64());
                out.flush()?;
                continue;
            }
            n_lines += 1;
            writeln!(out, "{j}")?;
        }
        drop(inputs);
        for mut ch in children {
            let _ = ch.wait();
        }
    }
    out.flush()?;
    eprintln!("fastrunner forkgame: {} games, {n_lines} lines in {:.1}s -> {}", lines.len(), t0.elapsed().as_secs_f64(), out_path.display());
    Ok(0)
}
