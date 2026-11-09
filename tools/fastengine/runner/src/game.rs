//! One match, as runner::Game::run plays it.
use crate::engine::{persp, Eng, Game};
use crate::host::{BotInit, TeamLog};
use crate::runtime::{Bot, Program, Runtime, TurnEnd};
use anyhow::{bail, Result};
use std::collections::{HashMap, HashSet};
use std::sync::Arc;

pub struct MatchSpec<'a> {
    pub map: &'a [u8],
    pub programs: [Arc<Program>; 2],
    pub max_rounds: u32,
    pub log_limit: usize,
    pub statistics: bool,
}

pub struct MatchResult {
    pub replay: Vec<u8>,
    pub stdout: [Vec<u8>; 2],
    pub fuel: [Vec<u64>; 2],
    /// Play turns (not draft turns) that ran out of fuel, per team.
    pub oof: [u32; 2],
    /// Winning team (0 = A, 1 = B), if finished.
    pub winner: Option<u32>,
    pub rounds: u32,
    pub finished: bool,
    pub statistics: Option<Vec<u8>>,
}

fn ck(eng: &Eng, rc: i32, what: &str) -> Result<()> {
    if rc != 0 {
        bail!("{what} failed ({rc}): {}", eng.last_error());
    }
    Ok(())
}

#[derive(Clone, Copy, Debug)]
pub struct State {
    pub phase: u32,
    pub team: u32,
    pub round: u32,
    pub champion: u32,
}

pub fn state(eng: &Eng, g: Game) -> Result<State> {
    let mut s = [0u32; 4];
    ck(eng, unsafe { (eng.Game_Runner_GetState)(g, &mut s) }, "Game_Runner_GetState")?;
    Ok(State { phase: s[0], team: s[1], round: s[2], champion: s[3] })
}

/// runner::engine::Game_TimelinePosition.
pub fn timeline_pos(eng: &Eng, g: Game) -> Result<u32> {
    let mut tl = 0u64;
    ck(eng, unsafe { (eng.Game_Visualiser_Timeline_GetMain)(g, &mut tl) }, "Timeline_GetMain")?;
    let (mut pos, mut b, mut c) = (0u32, 0u64, 0u32);
    ck(eng, unsafe { (eng.Game_Visualiser_Timeline_Info)(g, tl, &mut pos, &mut b, &mut c) }, "Timeline_Info")?;
    Ok(pos)
}

/// (champion id, team, type) of every champion, as runner::engine::Game_Champions lists them.
fn champions(eng: &Eng, g: Game) -> Result<Vec<(u32, u32, u32)>> {
    let obs = persp(2, u32::MAX);
    let mut n = 0u32;
    ck(eng, unsafe { (eng.Game_API_Champion_GetNumAllies)(g, obs, &mut n) }, "GetNumAllies")?;
    let mut ids = vec![0u32; n as usize];
    let mut got = 0u32;
    ck(eng, unsafe { (eng.Game_API_Champion_GetAllies)(g, obs, ids.as_mut_ptr(), n, &mut got) }, "GetAllies")?;
    ids.truncate(got.min(n) as usize);
    let mut out = Vec::new();
    for id in ids {
        let mut info = [0u8; 44];
        ck(eng, unsafe { (eng.Game_API_Champion_Get)(g, obs, id, info.as_mut_ptr()) }, "Champion_Get")?;
        let team = u32::from_le_bytes(info[0..4].try_into().unwrap());
        let ty = u32::from_le_bytes(info[4..8].try_into().unwrap());
        out.push((id, team, ty));
    }
    Ok(out)
}

struct GameHandle<'a> {
    eng: &'a Eng,
    g: Game,
}
impl Drop for GameHandle<'_> {
    fn drop(&mut self) {
        unsafe { (self.eng.Game_Destroy)(self.g) };
    }
}

pub fn play(rt: &Runtime, spec: &MatchSpec) -> Result<MatchResult> {
    let eng = rt.eng;
    crate::api::reset_game_caches();
    let mut g: Game = 0;
    ck(eng, unsafe { (eng.Game_FromMapFileBytes)(spec.map.as_ptr(), spec.map.len(), &mut g) }, "Game_FromMapFileBytes")?;
    let gh = GameHandle { eng, g };
    // Only for a .camstat: the winner summary comes from game state (identical either way), and the capture costs
    // ~5% of a game (vectors of every event). RunnerEvent is then a no-op returning 0, leaving the last error "".
    // The wasm engine exports no statistics capture, and cambc's .camstat encoder reads the native engine: none.
    let statistics = spec.statistics && !eng.is_wasm();
    if spec.statistics && eng.is_wasm() {
        static WARN: std::sync::Once = std::sync::Once::new();
        WARN.call_once(|| eprintln!("fastrunner: FASTRUNNER_ENGINE=wasm writes no .camstat statistics"));
    }
    if statistics {
        ck(eng, unsafe { (eng.Game_Statistics_Enable)(g) }, "Game_Statistics_Enable")?;
    }
    let mut meta = [0u32; 5];
    ck(eng, unsafe { (eng.Game_API_Map_GetBitboardMetadata)(g, &mut meta) }, "GetBitboardMetadata")?;
    let (mut bb, mut fb) = (0u64, 0u64);
    ck(eng, unsafe { (eng.Bitboard_GetRawBufferSize)(&meta, &mut bb) }, "Bitboard_GetRawBufferSize")?;
    ck(eng, unsafe { (eng.DistanceField_GetRawBufferSize)(&meta, &mut fb) }, "DistanceField_GetRawBufferSize")?;

    let mut logs: [Box<TeamLog>; 2] = [Box::new(TeamLog::new(spec.log_limit)), Box::new(TeamLog::new(spec.log_limit))];
    let mut fuel: [Vec<u64>; 2] = [Vec::new(), Vec::new()];
    let mut diagnostics = [0u32; 2];
    let spawn = |team: u32, champion: u32, ctype: u32, logs: &mut [Box<TeamLog>; 2]| -> Result<Bot> {
        let init = BotInit { game: g, team, champion, ctype, meta, board_bytes: bb, field_bytes: fb };
        Bot::spawn(rt, &spec.programs[team as usize], init, &mut *logs[team as usize])
    };

    let t_init = std::time::Instant::now();
    ck(eng, unsafe { (eng.Game_Runner_Init)(g) }, "Game_Runner_Init")?;

    // ---- draft ----
    let mut draft = [Some(spawn(0, u32::MAX, u32::MAX, &mut logs)?), Some(spawn(1, u32::MAX, u32::MAX, &mut logs)?)];
    let mut draft_dead = [false; 2];
    let mut draft_first = [true; 2];
    let mut draft_rng: u64 = spec.map.iter().fold(0xCBF2_9CE4_8422_2325u64, |h, &b| (h ^ b as u64).wrapping_mul(0x0100_0000_01B3));
    loop {
        let s = state(eng, g)?;
        if s.phase != 0 {
            break;
        }
        let t = s.team as usize;
        if t > 1 {
            bail!("draft turn for team {}", s.team);
        }
        if draft_dead[t] {
            fuel[t].push(0);
            default_draft(eng, g, &mut draft_rng)?;
            ck(eng, unsafe { (eng.Game_Runner_EndTurn)(g, 2) }, "EndTurn")?;
            continue;
        }
        let pos0 = timeline_pos(eng, g)?;
        let scale = if draft_first[t] { 100 } else { 1 };
        let bot = draft[t].as_mut().unwrap();
        let end = bot.run_turn(scale);
        fuel[t].push(bot.meter.used);
        report(&end, t as u32, u32::MAX, s.round);
        let code = end_code(&end);
        if code == 3 || code == 4 {
            diagnostics[t] += 1;
            unsafe { (eng.Game_Statistics_RunnerEvent)(g, 0xd, 16 + t as u32, 1) };
        }
        runner_events(eng, g, code, 16 + t as u32);
        draft_first[t] = false;
        if code == 2 {
            // Resigned: the game is over, so no EndTurn (as in play).
            draft_dead[t] = true;
            draft[t] = None;
            continue;
        }
        let pos1 = timeline_pos(eng, g)?;
        if pos1 != pos0 && code < 2 {
            ck(eng, unsafe { (eng.Game_Runner_EndTurn)(g, code as u32) }, "EndTurn")?;
            continue;
        }
        // The draft bot failed (did not pick, ran out of fuel without picking, exited or crashed):
        // it is not run again and its picks are made for it.
        draft_dead[t] = true;
        draft[t] = None;
        if pos1 != pos0 {
            let k = if code == 0 { 0 } else if code == 1 { 1 } else { 2 };
            ck(eng, unsafe { (eng.Game_Runner_EndTurn)(g, k) }, "EndTurn")?;
        } else {
            default_draft(eng, g, &mut draft_rng)?;
            ck(eng, unsafe { (eng.Game_Runner_EndTurn)(g, if code == 1 { 1 } else { 2 }) }, "EndTurn")?;
        }
    }
    drop(draft);

    // ---- play ----
    let mut bots: HashMap<u32, Bot> = HashMap::new();
    if state(eng, g)?.phase != 2 {
        for (id, team, ty) in champions(eng, g)? {
            bots.insert(id, spawn(team, id, ty, &mut logs)?);
        }
    }
    if std::env::var_os("FASTRUNNER_STATS").is_some() {
        eprintln!("timing: draft+spawn {:.3}s", t_init.elapsed().as_secs_f64());
    }
    let mut seen: HashSet<u32> = HashSet::new();
    let mut oof = [0u32; 2];
    let mut last_round = u32::MAX;
    loop {
        let s = state(eng, g)?;
        last_round = s.round;
        if s.phase == 2 || s.round > spec.max_rounds {
            break;
        }
        if s.team == 2 {
            ck(eng, unsafe { (eng.Game_Runner_Advance)(g) }, "Game_Runner_Advance")?;
            continue;
        }
        let t = s.team as usize;
        let Some(bot) = bots.get_mut(&s.champion) else {
            bail!("engine scheduled champion {} without a guest", s.champion);
        };
        let scale = if seen.insert(s.champion) { 2 } else { 1 };
        let end = bot.run_turn(scale);
        fuel[t].push(bot.meter.used);
        report(&end, t as u32, s.champion, s.round);
        let code = end_code(&end);
        if code == 3 || code == 4 {
            diagnostics[t] += 1;
            unsafe { (eng.Game_Statistics_RunnerEvent)(g, 0xd, s.champion, 1) };
        }
        runner_events(eng, g, code, s.champion);
        oof[t] += (code == 1) as u32;
        if code == 3 || code == 4 {
            bot.restart(rt);
        }
        if code == 2 {
            continue;
        }
        let kind = [0u32, 1, 0, 2, 2][code];
        ck(eng, unsafe { (eng.Game_Runner_EndTurn)(g, kind) }, "EndTurn")?;
    }
    let _ = last_round;
    let fin = state(eng, g)?;
    ck(eng, unsafe { (eng.Game_SaveReplay)(g) }, "Game_SaveReplay")?;
    let (mut p, mut n) = (std::ptr::null::<u8>(), 0usize);
    ck(eng, unsafe { (eng.Game_FileBuffer)(g, &mut p, &mut n) }, "Game_FileBuffer")?;
    let replay = unsafe { std::slice::from_raw_parts(p, n) }.to_vec();
    let mut summ = [0u8; 80];
    let rs = unsafe { (eng.Game_Statistics_GetSummary)(g, summ.as_mut_ptr()) };
    if std::env::var_os("FASTRUNNER_STATS").is_some() {
        let f: [u64; 2] = [fuel[0].iter().sum(), fuel[1].iter().sum()];
        eprintln!("stats: host calls (with memory) {}  fuel used A {} B {}  turns {} {}", unsafe { crate::host::CALLS }, f[0], f[1], fuel[0].len(), fuel[1].len());
    }
    if std::env::var_os("FASTRUNNER_DEBUG_SUMMARY").is_some() {
        let w: Vec<u32> = summ.chunks(4).map(|c| u32::from_le_bytes(c.try_into().unwrap())).collect();
        eprintln!("summary rc={rs} {:?}", w);
    }
    // Summary word 1: 1 = team A won, 2 = team B won.
    let winner = match u32::from_le_bytes(summ[4..8].try_into().unwrap()) {
        1 => Some(0),
        2 => Some(1),
        _ => crate::replay::winner(&replay),
    };
    let statistics = if statistics { crate::stats::export(eng, g, spec.map, diagnostics).ok() } else { None };
    drop(bots);
    let [a, b] = logs;
    drop(gh);
    Ok(MatchResult {
        replay,
        stdout: [a.buf, b.buf],
        fuel,
        oof,
        winner,
        rounds: fin.round,
        finished: fin.phase == 2,
        statistics,
    })
}

fn report(e: &TurnEnd, team: u32, champion: u32, round: u32) {
    if let TurnEnd::Error(msg) = e {
        let first = msg.lines().take(3).collect::<Vec<_>>().join(" | ");
        eprintln!("fastrunner: team {team} champion {} trapped in round {round}: {first}", champion as i32);
    }
}

fn end_code(e: &TurnEnd) -> usize {
    match e {
        TurnEnd::Yield => 0,
        TurnEnd::OutOfFuel => 1,
        TurnEnd::Exited => 3,
        TurnEnd::Error(_) => 4,
        TurnEnd::Removed => 2,
    }
}

fn runner_events(eng: &Eng, g: Game, code: usize, subject: u32) {
    match code {
        1 => unsafe {
            (eng.Game_Statistics_RunnerEvent)(g, 0xe, subject, 1);
        },
        2 => unsafe {
            (eng.Game_Statistics_RunnerEvent)(g, 0xf, subject, 1);
        },
        _ => {}
    }
}

/// runner::Game::default_draft (cambc 5.0.1 at 0x41acd50, unchanged from 4.0.0): a splitmix64 Fisher-Yates shuffle of 0..11 seeded with
/// FNV-1a-64 of the map file bytes, the state shared by both teams for the whole game; the first accepted pick wins.
pub(crate) fn default_draft(eng: &Eng, g: Game, state: &mut u64) -> Result<()> {
    let mut a: [u32; 12] = core::array::from_fn(|i| i as u32);
    for i in (1..12usize).rev() {
        *state = state.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = *state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^= z >> 31;
        a.swap(i, (z % (i as u64 + 1)) as usize);
    }
    for c in a {
        if unsafe { (eng.Game_Action_Draft)(g, c) } == 0 {
            return Ok(());
        }
    }
    bail!("no draft pick accepted")
}
