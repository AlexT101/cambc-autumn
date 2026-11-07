//! `fastrunner scenario`: the combat lab's scenarios (research/combat-lab/PLAN.md, "Scenario setup" and "Scenario
//! spec") on the wasm engine backend. Per scenario: load the map, draft the spec's picks (each team's draft bot runs
//! with its picks substituted, once per (bot, map, team, picks); its draft memory is cached and written directly
//! afterwards), buy items on spawn in round 1, idle to the last champion turn of round `round - 1`, set the
//! fighters' state with the sandbox and the cooldown words, end that turn and snapshot at round `round`'s first
//! champion turn. Per rollout: restore, fresh bot instances for the fighters only, play up to H rounds.
//!
//!   fastrunner scenario SPECS.jsonl --bot-a BOT --bot-b BOT --rollouts N --rounds H --out OUT.jsonl
//!       [--jobs J] [--slot-dir DIR --slots K] [--skip S] [--limit M] [--marks 10,30] [--hash]
//!       [--stdout DIR] [--turns] [--first-fuel SCALE] [--log-limit B] [--release]
//!       [--lab [--decisions] [--alt K [--alt-fighter ID|all]] [--force-home|--force-chase ID:ROUND:VERDICT]
//!        [--warm-pre F] [--warm-radius R]]
//!
//! OUT.jsonl: a line per rollout; OUT.setup.jsonl: a line per scenario (setup time, cached draft, every field that
//! did not land exactly). The draft-memory cache is FASTRUNNER_DRAFT_CACHE (default ~/.cache/fastrunner/draftmem).
use crate::engine::{persp, Game};
use crate::host::{BotInit, TeamLog};
use crate::runtime::{Bot, Program, Runtime, TurnEnd};
use crate::wengine::{self, args, raw::*, shim, Snapshot};
use anyhow::{anyhow, bail, ensure, Context, Result};
use serde_json::{json, Value};
use std::collections::{HashMap, HashSet};
use std::io::{BufRead, Write};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Instant;

const OBS: u64 = 2 | (u32::MAX as u64) << 32;
/// The lab warm start's default fuel before its warm point (`--warm-pre`; 0: as the first turn spent it): the
/// mean of lab ocean's later turns (median 7.1k, p90 10.4k); a fresh instance's first world update takes ~50k.
const WARM_PRE: u32 = 7300;
const WARM_RADIUS: i32 = 12;
type P = *mut u8;

fn ck(r: i32, what: &str) -> Result<()> {
    if r != 0 {
        bail!("{what} failed ({r}): {}", unsafe { args::last_error() });
    }
    Ok(())
}

fn err_of(r: u32) -> String {
    format!("{r} {}", unsafe { args::last_error() })
}

fn fnv(h: u64, b: &[u8]) -> u64 {
    b.iter().fold(h, |h, &x| (h ^ x as u64).wrapping_mul(0x0100_0000_01B3))
}
const FNV0: u64 = 0xCBF2_9CE4_8422_2325;

// ---------------------------------------------------------------- spec

struct ChS {
    id: u32,
    team: u32,
    name: String,
    alive: bool,
    x: i32,
    y: i32,
    hp: f64,
    max_hp: f64,
    gold: f64,
    gems: u32,
    /// (item id, count)
    items: Vec<(u32, u32)>,
    cons: [u32; 4],
    cd: [u32; 2],
    stun: u32,
    shield: (f64, u32),
    fighter: bool,
    prio: Option<i32>,
    /// The ward's (charges, recharge rounds), as the replay recorded them.
    ward: Option<(u32, u32)>,
}

struct WardS {
    owner: u32,
    x: i32,
    y: i32,
}

struct CampS {
    id: u32,
    alive: bool,
    hp: f64,
    awake: bool,
}

struct Spec {
    map: PathBuf,
    picks: [Vec<u32>; 2],
    round: u32,
    champs: Vec<ChS>,
    camps: Vec<CampS>,
    wards: Vec<WardS>,
}

fn parse_spec(v: &Value, root: &Path) -> Result<Spec> {
    let u = |v: &Value, k: &str| -> Result<u64> { v.get(k).and_then(Value::as_u64).ok_or_else(|| anyhow!("spec: {k} missing")) };
    let f = |v: &Value, k: &str| -> f64 { v.get(k).and_then(Value::as_f64).unwrap_or(0.0) };
    let m = v.get("map").and_then(Value::as_str).ok_or_else(|| anyhow!("spec: map missing"))?;
    let map = [PathBuf::from(m), root.join(m)].into_iter().find(|p| p.is_file()).ok_or_else(|| anyhow!("map {m} not found"))?;
    let pk = v.get("picks").and_then(Value::as_array).ok_or_else(|| anyhow!("spec: picks missing"))?;
    ensure!(pk.len() == 2, "spec: picks needs two teams");
    let team_picks = |t: usize| -> Vec<u32> { pk[t].as_array().map(|a| a.iter().filter_map(|x| x.as_u64()).map(|x| x as u32).collect()).unwrap_or_default() };
    let mut champs = Vec::new();
    for c in v.get("champions").and_then(Value::as_array).ok_or_else(|| anyhow!("spec: champions missing"))? {
        let mut items: Vec<(u32, u32)> = c
            .get("items")
            .and_then(Value::as_object)
            .map(|o| o.iter().filter_map(|(k, n)| Some((k.parse().ok()?, n.as_u64()? as u32))).filter(|x: &(u32, u32)| x.1 > 0).collect())
            .unwrap_or_default();
        items.sort();
        let arr = |k: &str, i: usize| c.get(k).and_then(|a| a.get(i)).and_then(Value::as_u64).unwrap_or(0) as u32;
        let sh = c.get("shield");
        champs.push(ChS {
            id: u(c, "id")? as u32,
            team: u(c, "team")? as u32,
            name: c.get("name").and_then(Value::as_str).unwrap_or("").to_string(),
            alive: c.get("alive").and_then(Value::as_bool).unwrap_or(true),
            x: c.get("x").and_then(Value::as_i64).unwrap_or(-1) as i32,
            y: c.get("y").and_then(Value::as_i64).unwrap_or(-1) as i32,
            hp: f(c, "hp"),
            max_hp: f(c, "maxHp"),
            gold: f(c, "gold"),
            gems: c.get("gems").and_then(Value::as_u64).unwrap_or(0) as u32,
            items,
            cons: [arr("cons", 0), arr("cons", 1), arr("cons", 2), arr("cons", 3)],
            cd: [arr("cd", 0), arr("cd", 1)],
            stun: c.get("stun").and_then(Value::as_u64).unwrap_or(0) as u32,
            shield: (sh.map_or(0.0, |s| f(s, "amount")), sh.and_then(|s| s.get("turns")).and_then(Value::as_u64).unwrap_or(0) as u32),
            fighter: c.get("fighter").and_then(Value::as_bool).unwrap_or(false),
            prio: c.get("prio").and_then(Value::as_i64).map(|p| p as i32),
            ward: c.get("ward").and_then(Value::as_array).filter(|a| a.len() == 2).map(|a| (a[0].as_u64().unwrap_or(0) as u32, a[1].as_u64().unwrap_or(0) as u32)),
        });
    }
    let camps = v
        .get("camps")
        .and_then(Value::as_array)
        .map(|a| {
            a.iter()
                .filter_map(|c| {
                    Some(CampS {
                        id: c.get("id")?.as_u64()? as u32,
                        alive: c.get("alive").and_then(Value::as_bool).unwrap_or(true),
                        hp: f(c, "hp"),
                        awake: c.get("awake").and_then(Value::as_bool).unwrap_or(false),
                    })
                })
                .collect()
        })
        .unwrap_or_default();
    let wards = v
        .get("wards")
        .and_then(Value::as_array)
        .map(|a| {
            a.iter()
                .filter(|w| !w.get("disabled").and_then(Value::as_bool).unwrap_or(false))
                .filter_map(|w| Some(WardS { owner: w.get("owner")?.as_u64()? as u32, x: w.get("x")?.as_i64()? as i32, y: w.get("y")?.as_i64()? as i32 }))
                .collect()
        })
        .unwrap_or_default();
    let round = u(v, "round")? as u32;
    ensure!(round >= 2, "spec round {round}: a scenario starts in round 2 or later");
    Ok(Spec { map, picks: [team_picks(0), team_picks(1)], round, champs, camps, wards })
}

// ---------------------------------------------------------------- engine reads and edits

#[derive(Clone, Copy, Debug)]
struct Ch {
    x: i32,
    y: i32,
    hp: f32,
    max: f32,
}

struct W {
    g: Game,
}

impl W {
    fn st(&self) -> [u32; 4] {
        let mut s = [0u32; 4];
        unsafe { shim::Game_Runner_GetState(self.g, s.as_mut_ptr() as P) };
        s
    }
    fn end(&self, kind: u32) -> Result<()> {
        ck(unsafe { shim::Game_Runner_EndTurn(self.g, kind) }, "EndTurn")
    }
    fn adv(&self) -> Result<()> {
        ck(unsafe { shim::Game_Runner_Advance(self.g) }, "Advance")
    }
    /// Advances through runner steps to the next champion's turn (or the game's end).
    fn boundary(&self) -> Result<[u32; 4]> {
        loop {
            let s = self.st();
            if s[0] == 2 || s[1] != 2 {
                return Ok(s);
            }
            self.adv()?;
        }
    }
    fn alive(&self, id: u32) -> bool {
        let mut o = 0u32;
        unsafe { shim::Game_API_Champion_IsAlive(self.g, id, &mut o as *mut u32 as P) == 0 && o != 0 }
    }
    fn champ(&self, id: u32) -> Option<Ch> {
        let mut c = [0u32; 11];
        if unsafe { shim::Game_API_Champion_Get(self.g, OBS, id, c.as_mut_ptr() as P) } != 0 {
            return None;
        }
        Some(Ch { x: c[2] as i32, y: c[3] as i32, hp: f32::from_bits(c[4]), max: f32::from_bits(c[5]) })
    }
    /// (team, champion type), readable whether alive or not.
    fn identity(&self, id: u32) -> (u32, u32) {
        let mut c = [0u32; 2];
        unsafe { shim::Game_API_Champion_GetIdentity(self.g, OBS, id, c.as_mut_ptr() as P) };
        (c[0], c[1])
    }
    fn cd(&self, id: u32, s: u32) -> Option<u32> {
        let mut o = 0u32;
        (unsafe { shim::Game_API_Champion_GetCooldown(self.g, OBS, id, s, &mut o as *mut u32 as P) } == 0).then_some(o)
    }
    /// (type, turns, amount): 0 shield, 1 stun, 2 enhanced attack.
    fn buffs(&self, id: u32) -> Vec<(u32, u32, f32)> {
        let mut b = [0u32; 3 * 8];
        let mut n = 0u32;
        if unsafe { shim::Game_API_Champion_GetBuffData(self.g, OBS, id, b.as_mut_ptr() as P, 8, &mut n as *mut u32 as P) } != 0 {
            return Vec::new();
        }
        (0..n.min(8) as usize).map(|i| (b[3 * i], b[3 * i + 1], f32::from_bits(b[3 * i + 2]))).collect()
    }
    fn shield(&self, id: u32) -> f32 {
        self.buffs(id).iter().filter(|b| b.0 == 0).map(|b| b.2).sum()
    }
    fn gold(&self, id: u32, team: u32) -> u32 {
        let mut o = 0u32;
        unsafe { shim::Game_API_Champion_GetGold(self.g, persp(team, id), id, &mut o as *mut u32 as P) };
        o
    }
    fn gems(&self, id: u32) -> u32 {
        let mut o = 0u32;
        unsafe { shim::Game_API_Champion_GetGems(self.g, OBS, id, &mut o as *mut u32 as P) };
        o
    }
    fn items(&self, id: u32) -> Vec<(u32, u32)> {
        let mut b = [0u32; 84];
        unsafe { shim::Game_API_Champion_GetItems(self.g, OBS, id, b.as_mut_ptr() as P, 84) };
        (0..84).filter(|&i| b[i] > 0).map(|i| (i as u32, b[i])).collect()
    }
    fn cons(&self, id: u32) -> [u32; 4] {
        let mut b = [0u32; 4];
        unsafe { shim::Game_API_Champion_GetConsumables(self.g, OBS, id, b.as_mut_ptr() as P, 4) };
        b
    }
    /// (state: 0 dead, 1 awake, 2 asleep; health)
    fn camp(&self, id: u32) -> Option<(u32, f32)> {
        let mut s = 0u32;
        let mut c = [0u32; 8];
        unsafe {
            if shim::Game_API_Camp_GetState(self.g, OBS, id, &mut s as *mut u32 as P) != 0 {
                return None;
            }
            if s == 0 {
                return Some((0, 0.0));
            }
            if shim::Game_API_Camp_Get(self.g, OBS, id, c.as_mut_ptr() as P) != 0 {
                return None;
            }
        }
        Some((s, f32::from_bits(c[2])))
    }
    fn champion_ids(&self) -> Result<Vec<u32>> {
        let mut n = 0u32;
        ck(unsafe { shim::Game_API_Champion_GetNumAllies(self.g, OBS, &mut n as *mut u32 as P) }, "GetNumAllies")?;
        let mut ids = vec![0u32; n as usize];
        let mut got = 0u32;
        ck(unsafe { shim::Game_API_Champion_GetAllies(self.g, OBS, ids.as_mut_ptr() as P, n, &mut got as *mut u32 as P) }, "GetAllies")?;
        ids.truncate(got.min(n) as usize);
        Ok(ids)
    }
    /// A champion's ward (charges, recharge rounds).
    fn ward_res(&self, id: u32) -> Option<(u32, i32)> {
        let mut o = [0u32; 2];
        (unsafe { shim::Game_API_Champion_GetWards(self.g, OBS, id, o.as_mut_ptr() as P) } == 0).then_some((o[0], o[1] as i32))
    }
    /// Every ward on the map: (owner, team, x, y).
    fn wards(&self) -> Vec<(u32, u32, i32, i32)> {
        let mut b = [0u32; 6 * 64];
        let mut n = 0u32;
        if unsafe { shim::Game_API_GetWards(self.g, OBS, b.as_mut_ptr() as P, 64, &mut n as *mut u32 as P) } != 0 {
            return Vec::new();
        }
        (0..n.min(64) as usize).map(|k| (b[6 * k + 5], b[6 * k], b[6 * k + 1] as i32, b[6 * k + 2] as i32)).collect()
    }
    /// The champion at the input boundary places its ward.
    fn place_ward(&self, x: i32, y: i32) -> u32 {
        let mut o = 0u32;
        (unsafe { shim::Game_Action_PlaceWard(self.g, x as u32 as u64 | (y as u32 as u64) << 32, &mut o as *mut u32 as P) }) as u32
    }
    fn teleport(&self, id: u32, x: i32, y: i32) -> u32 {
        unsafe { w2c_engine_Game_Sandbox_Teleport(wengine::instance(), self.g, args::entity(0, 1, id), args::pos(1, x, y)) }
    }
    /// Damage from no source (kind 0) to a champion (kind 1) or camp (kind 2).
    fn damage(&self, kind: u32, id: u32, amount: f32) -> u32 {
        unsafe { w2c_engine_Game_Sandbox_Damage(wengine::instance(), self.g, args::entity(0, 0, 0), args::entity(1, kind, id), amount) }
    }
    fn buff(&self, kind: u32, id: u32, ty: u32, turns: u32, amount: f32) -> u32 {
        unsafe { w2c_engine_Game_Sandbox_Buff(wengine::instance(), self.g, args::entity(0, kind, id), ty, turns, amount) }
    }
    fn give_gold(&self, id: u32, n: u32) -> u32 {
        unsafe { w2c_engine_Game_Sandbox_GiveGold(wengine::instance(), self.g, id, n) }
    }
    fn give_gems(&self, id: u32, n: u32) -> u32 {
        unsafe { w2c_engine_Game_Sandbox_GiveGems(wengine::instance(), self.g, id, n) }
    }
}

// ---------------------------------------------------------------- draft memory cache

struct DraftCache {
    dir: Option<PathBuf>,
    mem: HashMap<u64, Vec<u8>>,
}

impl DraftCache {
    fn new() -> DraftCache {
        let dir = std::env::var_os("FASTRUNNER_DRAFT_CACHE")
            .map(PathBuf::from)
            .or_else(|| std::env::var_os("HOME").map(|h| PathBuf::from(h).join(".cache/fastrunner/draftmem")));
        let dir = dir.filter(|d| std::fs::create_dir_all(d).is_ok());
        DraftCache { dir, mem: HashMap::new() }
    }
    fn path(&self, k: u64) -> Option<PathBuf> {
        self.dir.as_ref().map(|d| d.join(format!("{k:016x}.bin")))
    }
    fn get(&mut self, k: u64) -> Option<Vec<u8>> {
        if let Some(m) = self.mem.get(&k) {
            return Some(m.clone());
        }
        let b = std::fs::read(self.path(k)?).ok()?;
        self.mem.insert(k, b.clone());
        Some(b)
    }
    fn put(&mut self, k: u64, b: &[u8]) {
        self.mem.insert(k, b.to_vec());
        if let Some(p) = self.path(k) {
            let tmp = p.with_extension(format!("tmp{}", std::process::id()));
            if std::fs::write(&tmp, b).is_ok() {
                let _ = std::fs::rename(&tmp, &p);
            }
        }
    }
    fn remove(&mut self, k: u64) {
        self.mem.remove(&k);
        if let Some(p) = self.path(k) {
            let _ = std::fs::remove_file(p);
        }
    }
}

// ---------------------------------------------------------------- the lab bot's control block

/// tools/combatlab/lab.h's LabBlock: found by its magic in a lab bot's linear memory, read and written between turns.
const LAB_MAGIC: &[u8; 16] = b"CAMBC-LAB-BLK-1\0";
const LAB_SIZE: u32 = 512;
mod lb {
    pub const FLAGS: usize = 24;
    pub const WARM_PRE_IN: usize = 28;
    pub const BAN_ROUND: usize = 32;
    pub const BAN_CALL: usize = 36;
    pub const N_BANS: usize = 40;
    pub const BANS: usize = 44;
    pub const HOME_ROUND: usize = 172;
    pub const HOME_FORCE: usize = 176;
    pub const CHASE_ROUND: usize = 180;
    pub const CHASE_FORCE: usize = 184;
    pub const WARM_ROUND: usize = 188;
    pub const PRE_FUEL: usize = 192;
    pub const WARM_FUEL: usize = 200;
    pub const WARM_PRE: usize = 208;
    pub const WARM_OFFSET: usize = 216;
    pub const ROUND: usize = 224;
    pub const DECISION: usize = 228;
    pub const STAND: usize = 236;
    pub const N_PLANS: usize = 248;
    pub const WARM_RADIUS: usize = 252;
    pub const PLANS: usize = 256;
    pub const PLAN: usize = 64;
}

fn find_block(m: &[u8]) -> Option<usize> {
    let mut i = 0;
    while i + 16 <= m.len() {
        let j = i + m[i..].iter().position(|&b| b == b'C')?;
        if j + LAB_SIZE as usize <= m.len() && &m[j..j + 16] == LAB_MAGIC && rd_u32(m, j + 20) == LAB_SIZE {
            return Some(j);
        }
        i = j + 1;
    }
    None
}

fn rd_i8(m: &[u8], o: usize) -> i32 {
    m[o] as i8 as i32
}
fn rd_i16(m: &[u8], o: usize) -> i32 {
    i16::from_le_bytes([m[o], m[o + 1]]) as i32
}
fn rd_u16(m: &[u8], o: usize) -> u32 {
    u16::from_le_bytes([m[o], m[o + 1]]) as u32
}
fn rd_i32(m: &[u8], o: usize) -> i32 {
    i32::from_le_bytes(m[o..o + 4].try_into().unwrap())
}
fn rd_u32(m: &[u8], o: usize) -> u32 {
    u32::from_le_bytes(m[o..o + 4].try_into().unwrap())
}
fn rd_u64(m: &[u8], o: usize) -> u64 {
    u64::from_le_bytes(m[o..o + 8].try_into().unwrap())
}
fn rd_f32(m: &[u8], o: usize) -> f64 {
    (f32::from_le_bytes(m[o..o + 4].try_into().unwrap()) as f64 * 100.0).round() / 100.0
}
fn wr_i32(m: &mut [u8], o: usize, v: i32) {
    m[o..o + 4].copy_from_slice(&v.to_le_bytes());
}

/// A strike-search candidate's identity: end tile, cast kept for the shield, enemies removed.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
struct Cand {
    x: i32,
    y: i32,
    keep: bool,
    removed: u32,
}

impl Cand {
    fn of(v: &Value) -> Option<Cand> {
        Some(Cand { x: v["x"].as_i64()? as i32, y: v["y"].as_i64()? as i32, keep: v["keep"].as_bool()?, removed: v["removed"].as_u64()? as u32 })
    }
    fn json(&self) -> Value {
        json!({"x": self.x, "y": self.y, "keep": self.keep, "removed": self.removed})
    }
}

/// A rollout's inputs to the lab bots, by fighter id.
#[derive(Clone, Default)]
struct Inputs {
    /// (fighter, round, plan_strikes call, banned candidates)
    bans: Option<(u32, i32, i32, Vec<Cand>)>,
    /// (fighter, round, 0 want_home / 1 chase, verdict)
    forces: Vec<(u32, i32, u8, i32)>,
}

fn write_inputs(m: &mut [u8], o: usize, flags: u32, warm: (u32, i32), id: u32, inp: &Inputs) {
    let (warm_pre, warm_radius) = warm;
    wr_i32(m, o + lb::WARM_RADIUS, warm_radius);
    m[o + lb::FLAGS..o + lb::FLAGS + 4].copy_from_slice(&flags.to_le_bytes());
    m[o + lb::WARM_PRE_IN..o + lb::WARM_PRE_IN + 4].copy_from_slice(&warm_pre.to_le_bytes());
    if let Some((f, r, call, bans)) = &inp.bans {
        if *f == id {
            wr_i32(m, o + lb::BAN_ROUND, *r);
            wr_i32(m, o + lb::BAN_CALL, *call);
            let n = bans.len().min(16);
            wr_i32(m, o + lb::N_BANS, n as i32);
            for (k, c) in bans.iter().take(16).enumerate() {
                let b = o + lb::BANS + 8 * k;
                m[b..b + 2].copy_from_slice(&(c.x as i16).to_le_bytes());
                m[b + 2..b + 4].copy_from_slice(&(c.y as i16).to_le_bytes());
                m[b + 4..b + 6].copy_from_slice(&(c.removed as u16).to_le_bytes());
                m[b + 6] = c.keep as u8;
                m[b + 7] = 0;
            }
        }
    }
    for &(f, r, what, v) in &inp.forces {
        if f == id {
            let (ro, fo) = if what == 0 { (lb::HOME_ROUND, lb::HOME_FORCE) } else { (lb::CHASE_ROUND, lb::CHASE_FORCE) };
            wr_i32(m, o + ro, r);
            wr_i32(m, o + fo, v);
        }
    }
}

/// The block's outputs of the turn just played.
fn read_decision(m: &[u8], o: usize) -> Value {
    let b = |k: usize| rd_i8(m, o + k);
    let mut v = json!({
        "r": rd_i32(m, o + lb::ROUND), "b": (m[o + lb::DECISION] as char).to_string(),
        "home": b(lb::DECISION + 1), "home_impl": b(lb::DECISION + 2), "chase": b(lb::DECISION + 3),
    });
    if b(lb::DECISION + 3) == 1 {
        v["target"] = json!(rd_u32(m, o + lb::DECISION + 4));
    }
    let st = o + lb::STAND;
    if rd_i8(m, st) >= 0 {
        v["stand"] = json!({"lost": rd_i8(m, st), "reason": rd_i8(m, st + 1)});
        if rd_i8(m, st + 1) == 4 {
            v["stand"]["trade"] = json!({"lost": rd_i8(m, st + 2), "self_falls": rd_i8(m, st + 3), "falls": rd_i8(m, st + 4),
                "turns_to_kill_us": rd_i16(m, st + 6), "turns_to_kill_them": rd_i16(m, st + 8)});
        }
    }
    let n = rd_i32(m, o + lb::N_PLANS).clamp(0, 4) as usize;
    let mut plans = Vec::new();
    for k in 0..n {
        let p = o + lb::PLANS + lb::PLAN * k;
        let mut pv = json!({
            "call": k, "r": rd_i32(m, p), "site": (m[p + 4] as char).to_string(), "status": rd_i8(m, p + 5), "early": rd_i8(m, p + 6),
        });
        if rd_i8(m, p + 5) > 0 {
            pv["capped"] = json!(rd_i8(m, p + 7));
            pv["tiles"] = json!(rd_i16(m, p + 8));
            pv["exact_tiles"] = json!(rd_i16(m, p + 10));
            pv["exact_cands"] = json!(rd_i16(m, p + 12));
            pv["queries"] = json!(rd_i16(m, p + 14));
            pv["banned"] = json!(rd_i16(m, p + 16));
            pv["replanned"] = json!(rd_i16(m, p + 18));
        }
        if rd_i8(m, p + 5) == 1 {
            let c = p + 20;
            let ops: String = m[c + 36..c + 44].iter().take_while(|&&x| x != 0).map(|&x| x as char).collect();
            pv["c"] = json!({
                "x": rd_i16(m, c), "y": rd_i16(m, c + 2), "removed": rd_u16(m, c + 4), "keep": m[c + 6] != 0, "entry": rd_i8(m, c + 7),
                "raw": rd_f32(m, c + 8), "price": rd_f32(m, c + 12), "danger": rd_f32(m, c + 16), "shield": rd_f32(m, c + 20),
                "camp": rd_f32(m, c + 24), "gain": rd_f32(m, c + 28), "total": rd_f32(m, c + 32), "ops": ops,
            });
        }
        plans.push(pv);
    }
    if !plans.is_empty() {
        v["plans"] = json!(plans);
    }
    v
}

/// A fighter's first strike-search decision that chose a candidate: (round, call, candidate).
fn first_choice(decs: &[Value]) -> Option<(i32, i32, Cand)> {
    for d in decs {
        for p in d["plans"].as_array().into_iter().flatten() {
            if p["status"].as_i64() == Some(1) {
                return Some((p["r"].as_i64()? as i32, p["call"].as_i64()? as i32, Cand::of(&p["c"])?));
            }
        }
    }
    None
}

/// The plan of `call` in `round` among a fighter's decisions.
fn plan_at(decs: &[Value], round: i32, call: i32) -> Option<&Value> {
    decs.iter().filter(|d| d["r"].as_i64() == Some(round as i64)).flat_map(|d| d["plans"].as_array().into_iter().flatten())
        .find(|p| p["call"].as_i64() == Some(call as i64) && p["r"].as_i64() == Some(round as i64))
}

// ---------------------------------------------------------------- the lab

#[derive(Clone)]
struct LabOpts {
    rollouts: usize,
    rounds: u32,
    marks: Vec<u32>,
    hash: bool,
    /// Per-turn records (round, fuel, out of fuel, acted) for each fighter.
    turns: bool,
    /// The fresh fighters' first-turn budget, in turns (the engine's rule for a new champion is 2).
    first_fuel: u64,
    log_limit: usize,
    stdout_dir: Option<PathBuf>,
    /// Lab bots (tools/combatlab/labify.py): the warm start on and decision outputs recorded.
    lab: bool,
    /// Each fighter's decisions in its rollout line.
    decisions: bool,
    /// Alternatives mode: up to this many alternatives at a fighter's first strike-search decision.
    alt: usize,
    /// Its fighter (champion id); None: each fighter in turn.
    alt_fighter: Option<u32>,
    /// Forced verdicts: (fighter, round, 0 want_home / 1 chase, verdict).
    forces: Vec<(u32, i32, u8, i32)>,
    /// The warm start's fuel before its warm point, as a normal turn spends it (0: as the first turn did).
    warm_pre: u32,
    /// The warm start fills the turn end's tables around each fighter to this radius (0: vision, as a turn end does).
    warm_radius: i32,
}

struct Lab<'a> {
    rt: &'a Runtime,
    progs: [Arc<Program>; 2],
    hashes: [u64; 2],
    cache: DraftCache,
    clean: Snapshot,
    maps: HashMap<PathBuf, Vec<u8>>,
    o: LabOpts,
    /// The control block's offset in each team's lab bot.
    blocks: [Option<usize>; 2],
}

struct Setup {
    g: Game,
    snap: Snapshot,
    round: u32,
    meta: [u32; 5],
    bb: u64,
    fb: u64,
    /// (id, team) of every fighter, by id, and its champion type.
    fighters: Vec<(u32, u32)>,
    types: Vec<u32>,
    /// Draft memory to validate on the first rollout: (team, key, bytes, fresh).
    drafts: Vec<(u32, u64, Vec<u8>, bool)>,
    info: serde_json::Map<String, Value>,
}

/// Item purchases for a spec champion: shards per shard id (an emblem is 5 of its shards, 25 for Greed) and gold.
fn purchases(c: &ChS) -> (Vec<(u32, u32)>, u32) {
    let mut sh: Vec<(u32, u32)> = Vec::new();
    for &(it, n) in &c.items {
        let (s, k) = if it % 2 == 1 { (it - 1, n * if it / 6 == 12 { 25 } else { 5 }) } else { (it, n) };
        match sh.iter_mut().find(|x| x.0 == s) {
            Some(x) => x.1 += k,
            None => sh.push((s, k)),
        }
    }
    let gold = 30 * sh.iter().map(|x| x.1).sum::<u32>() + 10 * c.cons.iter().sum::<u32>();
    (sh, gold)
}

/// How many rounds before the scenario's an asleep camp's health is set (it wakes, then sleeps again in time).
const EARLY_CAMP: u32 = 6;

/// A ward placed in round t can be placed again from round t + WARD_RECHARGE.
const WARD_RECHARGE: i64 = 10;
/// The round that leaves recharge k at the scenario's start is round - 1 - (10 - k) + WARD_LAG (measured: 893 frames).
const WARD_LAG: i64 = 1;

/// The round its owner places a ward in: with no charge left, the one that leaves the spec's recharge; with one,
/// long enough before for the recharge to be over.
fn ward_round(round: u32, res: Option<(u32, u32)>) -> u32 {
    let last = round as i64 - 1;
    let t = match res {
        Some((0, k)) => last - (WARD_RECHARGE - k as i64) + WARD_LAG,
        _ => last - WARD_RECHARGE - 2,
    };
    t.clamp(1, last) as u32
}

/// The champion at the input boundary places its ward at (x, y), teleported within 2 of it and back.
fn place_ward_as(w: &W, o: u32, x: i32, y: i32) -> Result<(), String> {
    let ch = w.champ(o).ok_or("owner not on the map")?;
    let (x0, y0) = (ch.x, ch.y);
    let near = |a: i32, b: i32| (a - x).abs().max((b - y).abs()) <= 2;
    let mut moved = false;
    if !near(x0, y0) {
        'find: for d in 0i32..=2 {
            for dy in -d..=d {
                for dx in -d..=d {
                    if dx.abs().max(dy.abs()) == d && w.teleport(o, x + dx, y + dy) == 0 {
                        moved = true;
                        break 'find;
                    }
                }
            }
        }
        if !moved {
            return Err("no free tile within 2 to teleport to".into());
        }
    }
    let r = w.place_ward(x, y);
    if moved && w.teleport(o, x0, y0) != 0 {
        return Err(format!("could not teleport back to ({x0}, {y0})"));
    }
    if r != 0 {
        return Err(err_of(r));
    }
    Ok(())
}

/// Words of the champion table: cooldown of champion c, slot s at base + 72 c + 8 s.
const CD_STRIDE: u32 = 72;

impl<'a> Lab<'a> {
    fn new(rt: &'a Runtime, progs: [Arc<Program>; 2], wasm: [&Path; 2], o: LabOpts) -> Result<Lab<'a>> {
        let mut hashes = [0u64; 2];
        for t in 0..2 {
            hashes[t] = fnv(FNV0, &std::fs::read(wasm[t])?);
        }
        anyhow::ensure!(rt.eng.is_wasm(), "fastrunner scenario needs FASTRUNNER_ENGINE=wasm");
        Ok(Lab { rt, progs, hashes, cache: DraftCache::new(), clean: wengine::snapshot(), maps: HashMap::new(), o, blocks: [None; 2] })
    }

    fn spawn(&self, s: &Setup, team: u32, id: u32, log: &mut TeamLog) -> Result<Bot> {
        let i = s.fighters.iter().position(|f| f.0 == id).unwrap();
        let init = BotInit { game: s.g, team, champion: id, ctype: s.types[i], meta: s.meta, board_bytes: s.bb, field_bytes: s.fb };
        Bot::spawn(self.rt, &self.progs[team as usize], init, log)
    }

    /// Finds a fresh lab bot's control block and writes its flags and inputs.
    fn lab_init(&mut self, b: &mut Bot, team: u32, id: u32, inp: &Inputs) -> Result<usize> {
        let m = b.memory().ok_or_else(|| anyhow!("--lab needs native mode (FASTRUNNER_MODE=native)"))?;
        let o = match self.blocks[team as usize] {
            Some(o) if o + 16 <= m.len() && &m[o..o + 16] == LAB_MAGIC => o,
            _ => find_block(m).ok_or_else(|| anyhow!("team {team}'s bot has no lab control block (make it with tools/combatlab/labify.py)"))?,
        };
        self.blocks[team as usize] = Some(o);
        write_inputs(m, o, 3, (self.o.warm_pre, self.o.warm_radius), id, inp);
        Ok(o)
    }

    fn setup(&mut self, sp: &Spec) -> Result<Setup> {
        let eng = self.rt.eng;
        wengine::restore(&self.clean);
        wengine::reset_host();
        crate::api::reset_game_caches();
        if !self.maps.contains_key(&sp.map) {
            let b = std::fs::read(&sp.map).with_context(|| format!("reading {}", sp.map.display()))?;
            self.maps.insert(sp.map.clone(), b);
        }
        let map = &self.maps[&sp.map];
        let mut g: Game = 0;
        ck(unsafe { shim::Game_FromMapFileBytes(map.as_ptr(), map.len(), &mut g) }, "Game_FromMapFileBytes")?;
        let w = W { g };
        let mut meta = [0u32; 5];
        ck(unsafe { (eng.Game_API_Map_GetBitboardMetadata)(g, &mut meta) }, "GetBitboardMetadata")?;
        let (mut bb, mut fb) = (0u64, 0u64);
        ck(unsafe { (eng.Bitboard_GetRawBufferSize)(&meta, &mut bb) }, "Bitboard_GetRawBufferSize")?;
        ck(unsafe { (eng.DistanceField_GetRawBufferSize)(&meta, &mut fb) }, "DistanceField_GetRawBufferSize")?;
        ck(unsafe { shim::Game_Runner_Init(g) }, "Game_Runner_Init")?;
        let mut info = serde_json::Map::new();
        let mut miss: Vec<String> = Vec::new();

        // ---- draft ----
        let mh = fnv(FNV0, map);
        let mut key = [0u64; 2];
        let mut mem: [Option<Vec<u8>>; 2] = [None, None];
        for t in 0..2 {
            let mut h = fnv(FNV0, &self.hashes[t].to_le_bytes());
            h = fnv(h, &mh.to_le_bytes());
            h = fnv(h, &[t as u8]);
            for p in &sp.picks {
                h = fnv(h, &(p.len() as u32).to_le_bytes());
                for x in p {
                    h = fnv(h, &x.to_le_bytes());
                }
            }
            key[t] = h;
            mem[t] = self.cache.get(h);
        }
        let mut draft_log = [Box::new(TeamLog::new(self.o.log_limit)), Box::new(TeamLog::new(self.o.log_limit))];
        let t_draft = Instant::now();
        unsafe { *std::ptr::addr_of_mut!(wengine::DRAFT_PICKS) = Some((sp.picks.clone(), [0, 0])) };
        let r = (|| -> Result<()> {
            let mut bots: [Option<Bot>; 2] = [None, None];
            for t in 0..2 {
                if mem[t].is_none() {
                    let init = BotInit { game: g, team: t as u32, champion: u32::MAX, ctype: u32::MAX, meta, board_bytes: bb, field_bytes: fb };
                    bots[t] = Some(Bot::spawn(self.rt, &self.progs[t], init, &mut *draft_log[t])?);
                }
            }
            let mut first = [true; 2];
            let mut written = [false; 2];
            loop {
                let s = w.st();
                if s[0] != 0 {
                    break;
                }
                let t = s[1] as usize;
                ensure!(t < 2, "draft turn for team {t}");
                if let Some(m) = &mem[t] {
                    if !written[t] {
                        ck(unsafe { shim::Game_API_WriteDraftMemory(g, t as u32, 0, m.as_ptr(), m.len()) }, "WriteDraftMemory")?;
                        written[t] = true;
                    }
                    ck(unsafe { shim::Game_Action_Draft(g, 0) }, "Draft")?;
                    w.end(0)?;
                    continue;
                }
                let pos0 = crate::game::timeline_pos(eng, g)?;
                let mut kind = 0;
                if let Some(bot) = bots[t].as_mut() {
                    let end = bot.run_turn(if first[t] { 100 } else { 1 });
                    first[t] = false;
                    match end {
                        TurnEnd::Yield => {}
                        TurnEnd::OutOfFuel => kind = 1,
                        TurnEnd::Removed => bail!("team {t}'s draft bot resigned"),
                        TurnEnd::Exited | TurnEnd::Error(_) => {
                            let what = match &end {
                                TurnEnd::Error(m) => m.lines().next().unwrap_or("").chars().take(200).collect::<String>(),
                                _ => "exited".into(),
                            };
                            info.insert(format!("draft_bot_{t}"), json!(what));
                            bots[t] = None;
                            kind = 2;
                        }
                    }
                }
                if crate::game::timeline_pos(eng, g)? == pos0 {
                    // It did not pick (or is gone): the runner picks for it.
                    ck(unsafe { shim::Game_Action_Draft(g, 0) }, "Draft")?;
                }
                w.end(kind)?;
            }
            Ok(())
        })();
        let made = unsafe { (*std::ptr::addr_of_mut!(wengine::DRAFT_PICKS)).take() };
        r?;
        info.insert("draft_ms".into(), json!(t_draft.elapsed().as_secs_f64() * 1e3));
        info.insert("draft_cached".into(), json!([mem[0].is_some(), mem[1].is_some()]));
        let made = made.map(|m| m.1).unwrap_or([0, 0]);
        for t in 0..2 {
            for (r, &want) in sp.picks[t].iter().enumerate() {
                let mut got = u32::MAX;
                unsafe { shim::Game_API_Draft_Get(g, t as u32, r as u8, &mut got as *mut u32 as P) };
                if got != want {
                    miss.push(format!("team {t} pick {r}: {got} (spec {want})"));
                }
            }
            if made[t] != sp.picks[t].len() {
                miss.push(format!("team {t}: {} picks made, spec {}", made[t], sp.picks[t].len()));
            }
            let text = String::from_utf8_lossy(&draft_log[t].buf);
            for l in text.lines().filter(|l| l.starts_with("DRAFT-") || l.starts_with("PLAN-")) {
                info.insert(format!("draft_note_{t}"), json!(l));
            }
        }
        let mut drafts = Vec::new();
        let mut size = 0u32;
        ck(unsafe { shim::Game_API_GetDraftMemorySize(g, &mut size as *mut u32 as P) }, "GetDraftMemorySize")?;
        let mut unread = [false; 2];
        for t in 0..2 {
            match mem[t].take() {
                Some(m) => drafts.push((t as u32, key[t], m, false)),
                None => unread[t] = true,
            }
        }
        // A team's draft memory is readable only at its own champions' turns.
        let mut grab = |c: u32, drafts: &mut Vec<(u32, u64, Vec<u8>, bool)>| -> Result<()> {
            let t = w.identity(c).0 as usize;
            if t < 2 && unread[t] {
                let mut m = vec![0u8; size as usize];
                ck(unsafe { shim::Game_API_ReadDraftMemory(g, t as u32, 0, m.as_mut_ptr(), size) }, "ReadDraftMemory")?;
                drafts.push((t as u32, key[t], m, true));
                unread[t] = false;
            }
            Ok(())
        };

        // ---- bodies ----
        let ids = w.champion_ids()?;
        let mut by_id: HashMap<u32, &ChS> = HashMap::new();
        for c in &sp.champs {
            by_id.insert(c.id, c);
        }
        for &id in &ids {
            match by_id.get(&id) {
                Some(c) if c.team != w.identity(id).0 => miss.push(format!("c{id}: team {} (spec {})", w.identity(id).0, c.team)),
                None => miss.push(format!("c{id}: not in the spec")),
                _ => {}
            }
        }
        ensure!(ids.len() == sp.champs.len(), "{} champions in the game, {} in the spec", ids.len(), sp.champs.len());
        let fighters: Vec<(u32, u32)> = sp.champs.iter().filter(|c| c.fighter).map(|c| (c.id, c.team)).collect();
        ensure!(!fighters.is_empty(), "no fighters");
        let is_tavi = |c: &ChS| c.name.eq_ignore_ascii_case("tavi");
        // Tavi sells its items on its spawn: a fighting Tavi buys at its own turn of round - 1, then leaves its spawn.
        let late_buy = |c: &ChS| is_tavi(c) && c.fighter && c.alive;
        let buy = |c: &ChS, miss: &mut Vec<String>| {
            let (sh, cost) = purchases(c);
            // A fighter's spare gold too, now: given after a Treasure emblem's purchase it would get +10%.
            let gold = cost + if c.fighter { c.gold.floor() as u32 } else { 0 };
            if gold == 0 {
                return;
            }
            // Vesper's +33% applies to given gold (no emblem's bonus yet: none is owned before these purchases).
            let k = if c.name.starts_with("Vesper") { 1.33 } else { 1.0 };
            let r = w.give_gold(c.id, (gold as f64 / k).ceil() as u32);
            if r != 0 {
                miss.push(format!("c{} GiveGold({gold}): {}", c.id, err_of(r)));
            }
            for (s, n) in sh {
                let r = unsafe { shim::Game_Action_BuyItem(g, s, n) };
                if r != 0 {
                    miss.push(format!("c{} BuyItem({s}, {n}): {}", c.id, err_of(r as u32)));
                }
            }
            for (k, &n) in c.cons.iter().enumerate() {
                for _ in 0..n {
                    let r = unsafe { shim::Game_Action_BuyConsumable(g, k as u32) };
                    if r != 0 {
                        miss.push(format!("c{} BuyConsumable({k}): {}", c.id, err_of(r as u32)));
                    }
                }
            }
        };

        // ---- wards: each placed by its owner, in the round that leaves the spec's recharge ----
        let mut ward_at: HashMap<(u32, u32), (i32, i32)> = HashMap::new();
        for wd in &sp.wards {
            match by_id.get(&wd.owner) {
                Some(c) => {
                    if ward_at.insert((ward_round(sp.round, c.ward), wd.owner), (wd.x, wd.y)).is_some() {
                        miss.push(format!("c{}: a second ward", wd.owner));
                    }
                }
                None => miss.push(format!("ward of c{}: no such champion", wd.owner)),
            }
        }
        let place = |s: [u32; 4], miss: &mut Vec<String>| {
            if let Some(&(x, y)) = ward_at.get(&(s[2], s[3])) {
                if let Err(e) = place_ward_as(&w, s[3], x, y) {
                    miss.push(format!("c{} ward at ({x}, {y}) in round {}: {e}", s[3], s[2]));
                }
            }
        };

        // ---- idle to round - 1 ----
        let t_idle = Instant::now();
        let last_round = sp.round - 1;
        let mut bought: HashSet<u32> = HashSet::new();
        // Damage wakes a camp, which sleeps again after a few camp phases with no champion in range: a camp asleep
        // in the spec with lost health takes it in round - EARLY_CAMP, while every champion is still on its spawn.
        let early = sp.round.checked_sub(EARLY_CAMP).filter(|&r| r >= 1);
        let mut early_done = false;
        let s1 = loop {
            let s = w.boundary()?;
            ensure!(s[0] == 1, "game over in round {} before the scenario's round", s[2]);
            grab(s[3], &mut drafts)?;
            if Some(s[2]) == early && !early_done {
                early_done = true;
                // Dead camps too: a kill wakes the rest of the group.
                for cm in &sp.camps {
                    if let Some((st, hp)) = w.camp(cm.id) {
                        if st != 0 && !cm.alive {
                            w.damage(2, cm.id, 1e9);
                        } else if st != 0 && !cm.awake && (cm.hp as f32) < hp - 1e-3 {
                            w.damage(2, cm.id, hp - cm.hp as f32);
                        }
                    }
                }
            }
            if s[2] >= last_round {
                break s;
            }
            if s[2] == 1 && bought.insert(s[3]) && !late_buy(by_id[&s[3]]) {
                buy(by_id[&s[3]], &mut miss);
            }
            place(s, &mut miss);
            w.end(0)?;
        };
        ensure!(s1[2] == last_round, "skipped round {last_round}");
        info.insert("idle_ms".into(), json!(t_idle.elapsed().as_secs_f64() * 1e3));
        let snap1 = wengine::snapshot();
        let bought1 = bought.clone();

        // ---- pass A (thrown away): round - 1's turn order, and the cooldown words' base by one cast ----
        let t_cal = Instant::now();
        let mut order = Vec::new();
        let mut base: Option<u32> = None;
        loop {
            let s = w.boundary()?;
            if s[0] != 1 || s[2] != last_round {
                break;
            }
            order.push(s[3]);
            if s[2] == 1 && bought.insert(s[3]) && !late_buy(by_id[&s[3]]) {
                buy(by_id[&s[3]], &mut Vec::new());
            }
            place(s, &mut Vec::new());
            if base.is_none() {
                base = calibrate(&w, s[3], &ids);
            }
            w.end(0)?;
        }
        info.insert("calibrate_ms".into(), json!(t_cal.elapsed().as_secs_f64() * 1e3));
        if base.is_none() {
            miss.push("cooldowns: no castable slot in round - 1 to calibrate with; cooldowns left at 0".into());
        }
        let last = *order.last().ok_or_else(|| anyhow!("no champion turns in round {last_round}"))?;

        // ---- pass B: priorities, a fighting Tavi's purchases, and the edits at the round's last champion turn ----
        wengine::restore(&snap1);
        wengine::reset_host();
        bought = bought1;
        let mut k = 0usize;
        let t_edit = Instant::now();
        // Dead camps first: a fighter may stand on a dead camp's tile.
        for cm in sp.camps.iter().filter(|c| !c.alive) {
            if w.camp(cm.id).is_some_and(|x| x.0 != 0) {
                w.damage(2, cm.id, 1e9);
            }
        }
        loop {
            let s = w.boundary()?;
            ensure!(s[0] == 1 && s[2] == last_round, "round {last_round} ended before its last turn");
            let c = s[3];
            ensure!(order.get(k) == Some(&c), "round {last_round}'s order changed on replay");
            let cs = by_id[&c];
            grab(c, &mut drafts)?;
            if s[2] == 1 && bought.insert(c) && !late_buy(cs) {
                buy(cs, &mut miss);
            }
            if let Some(p) = cs.prio {
                let r = unsafe { shim::Game_Action_SetPriority(g, p as u32) };
                if r != 0 {
                    miss.push(format!("c{c} SetPriority({p}): {}", err_of(r as u32)));
                }
            }
            if late_buy(cs) {
                buy(cs, &mut miss);
            }
            place(s, &mut miss);
            if cs.fighter {
                self.edit_fighter(&w, cs, base, &mut miss);
            }
            if k + 1 == order.len() {
                break;
            }
            w.end(0)?;
            k += 1;
        }
        self.edit_last(&w, sp, &mut miss);
        let check = verify(&w, sp, last, true);
        w.end(0)?;
        let s = w.boundary()?;
        ensure!(s[0] == 1 && s[2] == sp.round, "not at round {} after setup (state {s:?})", sp.round);
        // After the round's start (camp respawns, captures and attacks) and the last champion's turn end.
        let after = verify(&w, sp, last, false);
        info.insert("edit_ms".into(), json!(t_edit.elapsed().as_secs_f64() * 1e3));
        info.insert("cd_base".into(), json!(base));
        info.insert("last_turn".into(), json!(last));
        info.insert("order".into(), json!(order));
        miss.extend(check);
        info.insert("wards".into(), json!(sp.wards.len()));
        info.insert("inexact".into(), json!(miss));
        info.insert("after_round_start".into(), json!(after));
        let types = fighters.iter().map(|f| w.identity(f.0).1).collect();
        let snap = wengine::snapshot();
        info.insert("snapshot_kib".into(), json!(snap.bytes() >> 10));
        Ok(Setup { g, snap, round: sp.round, meta, bb, fb, fighters, types, drafts, info })
    }

    /// A fighter's edits, at its own turn of round - 1: that turn's end ticks its cooldowns and buffs, so they are set
    /// one higher (a shield or stun with 0 turns left is then set too), and it ends off its spawn, so no heal.
    fn edit_fighter(&self, w: &W, c: &ChS, base: Option<u32>, miss: &mut Vec<String>) {
        let id = c.id;
        if !c.alive {
            w.damage(1, id, 1e9);
            miss.push(format!("c{id}: dead in the spec, killed in round - 1 (respawn timer full, not the spec's)"));
            return;
        }
        if w.champ(id).is_some_and(|ch| (ch.x, ch.y) != (c.x, c.y)) {
            // Retried at the round's last turn, when a fighter not yet moved may have left the tile.
            w.teleport(id, c.x, c.y);
        }
        let want = c.hp as f32;
        let mut r = 1.0f32;
        for _ in 0..8 {
            let Some(ch) = w.champ(id) else { break };
            let d = ch.hp - want;
            if d.abs() <= 1e-3 {
                break;
            }
            if d < 0.0 {
                miss.push(format!("c{id} hp {} below the spec's {want}: health cannot be raised", ch.hp));
                break;
            }
            // Damage taken is scaled (Durability): aim by the last ratio, from below.
            let amt = d / r;
            if w.damage(1, id, amt) != 0 {
                break;
            }
            let got = ch.hp - w.champ(id).map_or(ch.hp, |x| x.hp);
            if got > 0.0 {
                r = got / amt;
            }
        }
        if c.shield.0 > 0.0 {
            let rc = w.buff(1, id, 0, c.shield.1 + 1, c.shield.0 as f32);
            if rc != 0 {
                miss.push(format!("c{id} shield: {}", err_of(rc)));
            }
        }
        if c.stun > 0 {
            let rc = w.buff(1, id, 1, c.stun + 1, 0.0);
            if rc != 0 {
                miss.push(format!("c{id} stun: {}", err_of(rc)));
            }
        }
        let gems = w.gems(id);
        if c.gems > gems {
            w.give_gems(id, c.gems - gems);
        }
        // Gold bonuses apply to given gold: Vesper's +33%, a Treasure emblem's +10% (items 18..23).
        let k = 1.0 + if c.name.starts_with("Vesper") { 0.33 } else { 0.0 } + if c.items.iter().any(|x| (18..24).contains(&x.0) && x.0 % 2 == 1) { 0.1 } else { 0.0 };
        let want_gold = c.gold.floor() as u32;
        for _ in 0..4 {
            let gold = w.gold(id, c.team);
            if gold >= want_gold {
                break;
            }
            w.give_gold(id, (((want_gold - gold) as f64 / k).floor() as u32).max(1));
        }
        if let Some(b) = base {
            let m = wengine::memory();
            for s in 0..2u32 {
                let v = c.cd[s as usize] + (c.cd[s as usize] > 0) as u32;
                let a = (b + CD_STRIDE * id + 8 * s) as usize;
                m[a..a + 4].copy_from_slice(&v.to_le_bytes());
            }
        }
    }

    /// At the round's last champion turn: teleports that failed at the fighters' own turns (their tile was taken), and
    /// the zone's camps.
    fn edit_last(&self, w: &W, sp: &Spec, miss: &mut Vec<String>) {
        let mut todo: Vec<&ChS> = sp.champs.iter().filter(|c| c.fighter && c.alive).collect();
        // A non-fighter idles on its spawn, which may be a fighter's tile: it moves to the nearest free tile.
        for c in &todo {
            let mut h = u32::MAX;
            unsafe { shim::Game_API_GetChampion(w.g, OBS, c.x as u32, c.y as u32, &mut h as *mut u32 as P) };
            if h == c.id || !sp.champs.iter().any(|x| x.id == h && !x.fighter) {
                continue;
            }
            let moved = (1..=4i32).any(|r| {
                (-r..=r).any(|dy| (-r..=r).any(|dx| dx.abs().max(dy.abs()) == r && !todo.iter().any(|f| (f.x, f.y) == (c.x + dx, c.y + dy)) && w.teleport(h, c.x + dx, c.y + dy) == 0))
            });
            if moved {
                miss.push(format!("c{h} (not fighting) moved off c{}'s tile ({}, {})", c.id, c.x, c.y));
            }
        }
        for _ in 0..4 {
            todo.retain(|c| match w.champ(c.id) {
                Some(ch) if ch.x == c.x && ch.y == c.y => false,
                _ => w.teleport(c.id, c.x, c.y) != 0,
            });
            if todo.is_empty() {
                break;
            }
        }
        for c in &todo {
            let r = w.teleport(c.id, c.x, c.y);
            let (mut camp, mut champ) = (u32::MAX, u32::MAX);
            unsafe {
                shim::Game_API_Map_GetCampAt(w.g, c.x as u32, c.y as u32, &mut camp as *mut u32 as P);
                shim::Game_API_GetChampion(w.g, OBS, c.x as u32, c.y as u32, &mut champ as *mut u32 as P);
            }
            let what = match (camp, champ) {
                (u32::MAX, u32::MAX) => String::new(),
                (u32::MAX, h) => format!(" (champion {h} there)"),
                (k, _) => format!(" (camp {k} there, state {:?})", w.camp(k).map(|x| x.0)),
            };
            miss.push(format!("c{} teleport to ({}, {}): {}{what}", c.id, c.x, c.y, err_of(r)));
        }
        for cm in sp.camps.iter().filter(|c| c.alive) {
            let Some((st, hp)) = w.camp(cm.id) else {
                miss.push(format!("camp {}: unreadable", cm.id));
                continue;
            };
            if st == 0 {
                miss.push(format!("camp {}: dead, alive in the spec", cm.id));
                continue;
            }
            let want = cm.hp as f32;
            if want < hp - 1e-3 {
                w.damage(2, cm.id, hp - want);
            } else if cm.awake && st == 2 {
                // Only damage or a stun wakes a camp: the least damage that does.
                w.damage(2, cm.id, 1e-3);
            }
        }
    }

    /// One rollout; with `track` (or --decisions) each fighter's decisions are returned.
    fn rollout(&mut self, s: &Setup, sp_id: &str, k: usize, inp: &Inputs, track: bool) -> Result<(Value, Vec<Vec<Value>>)> {
        wengine::restore(&s.snap);
        wengine::reset_host();
        crate::api::reset_game_caches();
        let w = W { g: s.g };
        let mut logs = [Box::new(TeamLog::new(self.o.log_limit)), Box::new(TeamLog::new(self.o.log_limit))];
        let mut bots: HashMap<u32, Bot> = HashMap::new();
        let mut blk: HashMap<u32, usize> = HashMap::new();
        for &(id, t) in &s.fighters {
            let mut b = self.spawn(s, t, id, &mut logs[t as usize])?;
            if self.o.lab {
                blk.insert(id, self.lab_init(&mut b, t, id, inp)?);
            }
            bots.insert(id, b);
        }
        let track = track || self.o.decisions;
        let n = s.fighters.len();
        let idx: HashMap<u32, usize> = s.fighters.iter().enumerate().map(|(i, f)| (f.0, i)).collect();
        let team = |i: usize| s.fighters[i].1;
        #[derive(Clone, Default)]
        struct F {
            deaths: u32,
            kills: u32,
            dealt: f64,
            taken: f64,
            taken_other: f64,
            fuel: u64,
            turns: u32,
            out_of_fuel: u32,
            errors: u32,
            log: Vec<[u64; 5]>,
            fuel_view: u64,
            /// The instance's warm start: round, fuel, fuel before it, the offset its turn's fuel readings took.
            warm: Option<[i64; 4]>,
            warm_seen: bool,
            decs: Vec<Value>,
        }
        let mut f: Vec<F> = vec![F::default(); n];
        let read = |w: &W, id: u32| -> (bool, f64) {
            if !w.alive(id) {
                return (false, 0.0);
            }
            (true, w.champ(id).map_or(0.0, |c| c.hp as f64) + w.shield(id) as f64)
        };
        let mut prev: Vec<(bool, f64)> = s.fighters.iter().map(|x| read(&w, x.0)).collect();
        let mut seen: HashSet<u32> = HashSet::new();
        let mut resigned = [false; 2];
        let mut apart = 0u32;
        let mut cur_round = s.round;
        let mut marks = serde_json::Map::new();
        let mut champion_turns = 0u64;
        let account = |w: &W, actor: Option<usize>, f: &mut Vec<F>, prev: &mut Vec<(bool, f64)>| {
            for i in 0..n {
                let now = read(w, s.fighters[i].0);
                let (was, v0) = prev[i];
                let enemy = actor.filter(|&a| team(a) != team(i));
                let loss = if was && !now.0 {
                    f[i].deaths += 1;
                    if let Some(a) = enemy {
                        f[a].kills += 1;
                    }
                    v0
                } else if was {
                    (v0 - now.1).max(0.0)
                } else {
                    0.0
                };
                if loss > 0.0 {
                    match enemy {
                        Some(a) => {
                            f[a].dealt += loss;
                            f[i].taken += loss;
                        }
                        None => f[i].taken_other += loss,
                    }
                }
                prev[i] = now;
            }
        };
        let team_dead = |prev: &Vec<(bool, f64)>| (0..2).any(|t| (0..n).filter(|&i| team(i) == t).all(|i| !prev[i].0));
        let mark = |f: &Vec<F>, prev: &Vec<(bool, f64)>, w: &W| -> Value {
            let mut deaths = [0u32; 2];
            let mut kills = [0u32; 2];
            let mut dmg = [0f64; 2];
            let mut hp = serde_json::Map::new();
            for i in 0..n {
                let t = team(i) as usize;
                deaths[t] += f[i].deaths;
                kills[t] += f[i].kills;
                dmg[t] += f[i].dealt;
                let id = s.fighters[i].0;
                hp.insert(id.to_string(), if prev[i].0 { json!(w.champ(id).map(|c| c.hp)) } else { Value::Null });
            }
            json!({"deaths": deaths, "kills": kills, "dmg": [round1(dmg[0]), round1(dmg[1])], "hp": hp})
        };
        let stop = loop {
            let st = w.st();
            if st[0] == 2 {
                break if resigned.iter().any(|&r| r) { "resign" } else { "game_over" };
            }
            if st[1] == 2 {
                w.adv()?;
                account(&w, None, &mut f, &mut prev);
                if team_dead(&prev) {
                    break "team_dead";
                }
                continue;
            }
            if st[2] != cur_round {
                cur_round = st[2];
                let played = cur_round - s.round;
                if self.o.marks.contains(&played) {
                    marks.insert(played.to_string(), mark(&f, &prev, &w));
                }
                if played >= self.o.rounds {
                    break "rounds";
                }
                let mut near = false;
                for i in 0..n {
                    for j in 0..n {
                        if team(i) == 0 && team(j) == 1 && prev[i].0 && prev[j].0 {
                            if let (Some(a), Some(b)) = (w.champ(s.fighters[i].0), w.champ(s.fighters[j].0)) {
                                near |= (a.x - b.x).abs().max((a.y - b.y).abs()) <= 8;
                            }
                        }
                    }
                }
                apart = if near { 0 } else { apart + 1 };
                if apart >= 3 {
                    break "apart";
                }
            }
            let c = st[3];
            let Some(bot) = bots.get_mut(&c) else {
                w.end(0)?;
                continue;
            };
            let i = idx[&c];
            // Whether the turn acted: its actions advance the timeline.
            let pos0 = if self.o.turns { crate::game::timeline_pos(self.rt.eng, s.g).unwrap_or(0) } else { 0 };
            let end = bot.run_turn(if seen.insert(c) { self.o.first_fuel } else { 1 });
            champion_turns += 1;
            f[i].fuel += bot.meter.used;
            f[i].turns += 1;
            let code = match end {
                TurnEnd::Yield => 0,
                TurnEnd::OutOfFuel => 1,
                TurnEnd::Removed => 2,
                TurnEnd::Exited => 3,
                TurnEnd::Error(_) => 4,
            };
            f[i].out_of_fuel += (code == 1) as u32;
            // The fuel as the bot saw it: on a warm start's turn, a normal turn's before the warm point, then what it read.
            let mut view = bot.meter.used;
            let mut pre = 0u64;
            let mut warm_turn = false;
            if let (Some(&o), Some(m)) = (blk.get(&c), bot.memory()) {
                pre = rd_u32(m, o + lb::PRE_FUEL) as u64;
                if !f[i].warm_seen && rd_i32(m, o + lb::WARM_ROUND) >= 0 {
                    f[i].warm_seen = true;
                    warm_turn = true;
                    let w = [rd_i32(m, o + lb::WARM_ROUND) as i64, rd_u64(m, o + lb::WARM_FUEL) as i64, rd_u64(m, o + lb::WARM_PRE) as i64,
                             rd_u64(m, o + lb::WARM_OFFSET) as i64];
                    // As a normal turn's: its fuel before the warm point, then what this one spent after the warm start.
                    let pre_set = if self.o.warm_pre > 0 { self.o.warm_pre as u64 } else { w[2] as u64 };
                    view = (view + pre_set).saturating_sub((w[1] + w[2]) as u64);
                    f[i].warm.get_or_insert(w);
                }
                if track {
                    let d = read_decision(m, o);
                    if d["r"].as_i64().unwrap_or(-1) >= 0 {
                        f[i].decs.push(d);
                    }
                }
            }
            f[i].fuel_view += view;
            if self.o.turns {
                let acted = crate::game::timeline_pos(self.rt.eng, s.g).unwrap_or(0) != pos0;
                                // 2: a warm start's turn that read past a normal turn's budget (it cannot run out).
                let oof = if code == 1 { 1 } else if warm_turn && view >= 100_000 { 2 } else { 0 };
                f[i].log.push([st[2] as u64, view, oof, acted as u64, pre]);
            }
            if code >= 3 {
                f[i].errors += 1;
                bot.restart(self.rt);
                if self.o.lab {
                    f[i].warm_seen = false;
                    if bot.alive() {
                        let t = team(i);
                        let o = self.lab_init(bot, t, c, inp)?;
                        blk.insert(c, o);
                    }
                }
            }
            if code == 2 {
                resigned[team(i) as usize] = true;
            } else {
                w.end([0u32, 1, 0, 2, 2][code])?;
            }
            account(&w, Some(i), &mut f, &mut prev);
            if team_dead(&prev) {
                break "team_dead";
            }
        };
        let fin = w.st();
        let mut out = Vec::new();
        for i in 0..n {
            let (id, t) = s.fighters[i];
            let log = std::mem::take(&mut f[i].log);
            let alive = w.alive(id);
            let ch = if alive { w.champ(id) } else { None };
            let mut fv = json!({
                "id": id, "team": t, "alive": alive, "deaths": f[i].deaths, "kills": f[i].kills,
                "hp": ch.map(|c| c.hp), "max_hp": ch.map(|c| c.max), "gems": w.gems(id), "gold": w.gold(id, t),
                "x": ch.map(|c| c.x), "y": ch.map(|c| c.y),
                "dealt": round1(f[i].dealt), "taken": round1(f[i].taken), "taken_other": round1(f[i].taken_other),
                "fuel": f[i].fuel, "turns": f[i].turns, "out_of_fuel": f[i].out_of_fuel, "errors": f[i].errors,
            });
            if self.o.turns {
                fv["turn_log"] = json!(log);
            }
            if self.o.lab {
                fv["fuel_view"] = json!(f[i].fuel_view);
                if let Some(w) = f[i].warm {
                    fv["warm"] = json!({"round": w[0], "fuel": w[1], "pre": w[2], "offset": w[3]});
                }
            }
            if self.o.decisions {
                fv["decisions"] = json!(f[i].decs);
            }
            out.push(fv);
        }
        let mut flags = Vec::new();
        for t in 0..2 {
            let text = String::from_utf8_lossy(&logs[t].buf);
            for l in text.lines().filter(|l| l.starts_with("PLAN-CHECK") || l.starts_with("DRAFT-UNFINISHED")) {
                flags.push(format!("team {t}: {l}"));
            }
            if resigned[t] {
                flags.push(format!("team {t} resigned"));
            }
        }
        if let Some(dir) = &self.o.stdout_dir {
            if k == 0 {
                let safe: String = sp_id.chars().map(|c| if c.is_ascii_alphanumeric() || c == '-' { c } else { '_' }).collect();
                for t in 0..2 {
                    let _ = std::fs::write(dir.join(format!("{safe}.team-{}.stdout", ["a", "b"][t])), &logs[t].buf);
                }
            }
        }
        let played = if fin[0] == 2 { fin[2].saturating_sub(s.round) + 1 } else { cur_round - s.round };
        let mut v = json!({
            "id": sp_id, "rollout": k, "rounds": played, "stop": stop, "end_round": fin[2],
            "champion_turns": champion_turns, "fighters": out,
        });
        if !marks.is_empty() {
            v["at"] = Value::Object(marks);
        }
        if !flags.is_empty() {
            v["flags"] = json!(flags);
        }
        if self.o.hash {
            v["hash"] = json!(format!("{:016x}", mem_hash()));
        }
        drop(bots);
        let decs = f.into_iter().map(|x| x.decs).collect();
        Ok((v, decs))
    }

    /// One scenario: setup, then its rollouts. Lines: ("R", rollout json) and one ("S", setup json).
    fn run(&mut self, line: &str, root: &Path, emit: &mut dyn FnMut(&str, &Value)) {
        let t0 = Instant::now();
        let c0 = cpu_ms();
        let v: Value = match serde_json::from_str(line) {
            Ok(v) => v,
            Err(e) => {
                emit("S", &json!({"error": format!("bad spec line: {e}")}));
                return;
            }
        };
        let id = v.get("id").and_then(Value::as_str).unwrap_or("?").to_string();
        let res = (|| -> Result<(Setup, Spec)> {
            let sp = parse_spec(&v, root)?;
            let s = self.setup(&sp)?;
            Ok((s, sp))
        })();
        let (mut s, _sp) = match res {
            Ok(x) => x,
            Err(e) => {
                let msg = format!("{e:#}");
                emit("R", &json!({"id": id, "error": msg}));
                emit("S", &json!({"id": id, "error": msg, "setup_ms": t0.elapsed().as_secs_f64() * 1e3}));
                return;
            }
        };
        let setup_ms = t0.elapsed().as_secs_f64() * 1e3;
        let c1 = cpu_ms();
        let t1 = Instant::now();
        let mut turns = 0u64;
        let mut fuel = 0u64;
        let mut done = 0usize;
        let base = Inputs { bans: None, forces: self.o.forces.clone() };
        let tally = |r: &Value, turns: &mut u64, fuel: &mut u64| {
            *turns += r["champion_turns"].as_u64().unwrap_or(0);
            *fuel += r["fighters"].as_array().map_or(0, |a| a.iter().map(|f| f["fuel"].as_u64().unwrap_or(0)).sum());
        };
        if self.o.alt > 0 {
            // Rollout 0 plays as without --alt; then, per chosen fighter, rollout k bans the candidates rollouts
            // 0..k-1 chose at that fighter's first strike-search decision (same round, same plan_strikes call).
            match self.rollout(&s, &id, 0, &base, true) {
                Ok((mut r, decs0)) => {
                    tally(&r, &mut turns, &mut fuel);
                    self.validate_drafts(&mut s, &r);
                    let mut firsts = Vec::new();
                    let mut fj = serde_json::Map::new();
                    for (i, &(fid, _)) in s.fighters.iter().enumerate() {
                        if self.o.alt_fighter.is_some_and(|a| a != fid) {
                            continue;
                        }
                        let fc = first_choice(&decs0[i]);
                        fj.insert(fid.to_string(), fc.map_or(Value::Null, |(r, call, c)| json!({"round": r, "call": call, "choice": c.json()})));
                        if let Some(x) = fc {
                            firsts.push((i, fid, x));
                        }
                    }
                    r["alt"] = json!({"k": 0, "first": fj});
                    emit("R", &r);
                    done += 1;
                    let mut k = 1;
                    'fighters: for (i, fid, (round, call, c0)) in firsts {
                        let mut bans = vec![c0];
                        for a in 1..self.o.alt {
                            let inp = Inputs { bans: Some((fid, round, call, bans.clone())), forces: self.o.forces.clone() };
                            let (mut r, decs) = match self.rollout(&s, &id, k, &inp, true) {
                                Ok(x) => x,
                                Err(e) => {
                                    emit("R", &json!({"id": id, "rollout": k, "error": format!("{e:#}")}));
                                    break 'fighters;
                                }
                            };
                            k += 1;
                            tally(&r, &mut turns, &mut fuel);
                            let p = plan_at(&decs[i], round, call);
                            let status = p.and_then(|p| p["status"].as_i64()).unwrap_or(-1);
                            let choice = p.and_then(|p| Cand::of(&p["c"]));
                            let repeat = choice.is_some_and(|c| bans.contains(&c));
                            r["alt"] = json!({"fighter": fid, "round": round, "call": call, "k": a, "banned": bans.len(), "status": status,
                                              "choice": choice.map(|c| c.json()), "plan": p.cloned(), "repeat": repeat});
                            emit("R", &r);
                            done += 1;
                            match choice {
                                Some(c) if status == 1 && !repeat => bans.push(c),
                                _ => break,
                            }
                        }
                    }
                }
                Err(e) => emit("R", &json!({"id": id, "rollout": 0, "error": format!("{e:#}")})),
            }
        } else {
            for k in 0..self.o.rollouts {
                match self.rollout(&s, &id, k, &base, false) {
                    Ok((r, _)) => {
                        tally(&r, &mut turns, &mut fuel);
                        if k == 0 {
                            self.validate_drafts(&mut s, &r);
                        }
                        emit("R", &r);
                        done += 1;
                    }
                    Err(e) => {
                        emit("R", &json!({"id": id, "rollout": k, "error": format!("{e:#}")}));
                        break;
                    }
                }
            }
        }
        let mut info = std::mem::take(&mut s.info);
        info.insert("id".into(), json!(id));
        info.insert("setup_ms".into(), json!(setup_ms));
        info.insert("rollouts".into(), json!(done));
        info.insert("rollout_ms".into(), json!(t1.elapsed().as_secs_f64() * 1e3));
        info.insert("setup_cpu_ms".into(), json!(c1 - c0));
        info.insert("rollout_cpu_ms".into(), json!(cpu_ms() - c1));
        info.insert("champion_turns".into(), json!(turns));
        info.insert("fighter_fuel".into(), json!(fuel));
        emit("S", &Value::Object(info));
    }

    /// A draft memory just computed is cached once its fighters' first turns took its plan; a cached one its fighters
    /// refused is dropped.
    fn validate_drafts(&mut self, s: &mut Setup, r: &Value) {
        let flags: Vec<String> = r["flags"].as_array().map(|a| a.iter().filter_map(|x| x.as_str().map(String::from)).collect()).unwrap_or_default();
        for (t, key, mem, fresh) in std::mem::take(&mut s.drafts) {
            let bad = flags.iter().any(|f| f.starts_with(&format!("team {t}: ")));
            let tested = s.fighters.iter().any(|f| f.1 == t);
            if bad {
                self.cache.remove(key);
                s.info.insert(format!("draft_rejected_{t}"), json!(true));
            } else if fresh && tested {
                self.cache.put(key, &mem);
            }
        }
    }
}

/// This thread's CPU time in ms (the box is shared: wall time measures the neighbours too).
fn cpu_ms() -> f64 {
    let mut t = libc::timespec { tv_sec: 0, tv_nsec: 0 };
    unsafe { libc::clock_gettime(libc::CLOCK_THREAD_CPUTIME_ID, &mut t) };
    t.tv_sec as f64 * 1e3 + t.tv_nsec as f64 * 1e-6
}

fn round1(x: f64) -> f64 {
    (x * 10.0).round() / 10.0
}

fn mem_hash() -> u64 {
    let m = wengine::memory();
    let mut h = FNV0;
    for c in m.chunks_exact(8) {
        h = (h ^ u64::from_le_bytes(c.try_into().unwrap())).wrapping_mul(0x0100_0000_01B3);
    }
    h
}

/// Finds the cooldown words' base: a cast by champion `c` (at its turn), then the memory word that changed to the
/// cooldown the API reads, confirmed by writing another champion's word and reading it back. The caller throws the
/// state away afterwards (the cast stays).
fn calibrate(w: &W, c: u32, ids: &[u32]) -> Option<u32> {
    let ch = w.champ(c)?;
    if (0..2).all(|s| w.cd(c, s) != Some(0)) {
        return None;
    }
    let before = wengine::memory().to_vec();
    let mut targets: Vec<u64> = vec![0, 1 | (c as u64) << 32];
    targets.extend(ids.iter().filter(|&&i| i != c).map(|&i| 1 | (i as u64) << 32));
    for s in 0..2u32 {
        if w.cd(c, s) != Some(0) {
            continue;
        }
        for &t in &targets {
            for r in 0..=2i32 {
                for dy in -r..=r {
                    for dx in -r..=r {
                        if dx.abs().max(dy.abs()) != r {
                            continue;
                        }
                        let p = (ch.x + dx) as u32 as u64 | ((ch.y + dy) as u32 as u64) << 32;
                        let mut o = 0u32;
                        if unsafe { shim::Game_Action_Cast(w.g, s, t, p, &mut o as *mut u32 as P) } != 0 {
                            continue;
                        }
                        let v = w.cd(c, s)?;
                        let m = wengine::memory();
                        let n = before.len().min(m.len()) & !3;
                        let other = *ids.iter().find(|&&i| i != c)?;
                        for a in (0..n).step_by(4) {
                            let now = u32::from_le_bytes(m[a..a + 4].try_into().unwrap());
                            let was = u32::from_le_bytes(before[a..a + 4].try_into().unwrap());
                            if now != v || was == now {
                                continue;
                            }
                            let Some(b) = (a as u32).checked_sub(CD_STRIDE * c + 8 * s) else { continue };
                            let q = (b + CD_STRIDE * other + 8 * (1 - s)) as usize;
                            if q + 4 > m.len() {
                                continue;
                            }
                            let old: [u8; 4] = m[q..q + 4].try_into().unwrap();
                            m[q..q + 4].copy_from_slice(&5u32.to_le_bytes());
                            let ok = w.cd(other, 1 - s) == Some(5);
                            wengine::memory()[q..q + 4].copy_from_slice(&old);
                            if ok {
                                return Some(b);
                            }
                        }
                        return None;
                    }
                }
            }
        }
    }
    None
}

/// Every set field against the spec; `pre`: at the last champion turn of round - 1, where that champion's cooldowns
/// and buffs are one higher than the spec's (else after its turn end and the round's start).
fn verify(w: &W, sp: &Spec, last: u32, pre: bool) -> Vec<String> {
    let mut v = Vec::new();
    for c in &sp.champs {
        let id = c.id;
        let items = w.items(id);
        if items != c.items {
            v.push(format!("c{id} items {items:?} (spec {:?})", c.items));
        }
        let cons = w.cons(id);
        if cons != c.cons {
            v.push(format!("c{id} consumables {cons:?} (spec {:?})", c.cons));
        }
        if !c.fighter {
            if let Some(ch) = w.champ(id) {
                if c.max_hp > 0.0 && (ch.max as f64 - c.max_hp).abs() > 0.05 {
                    v.push(format!("c{id} max hp {} (spec {})", ch.max, c.max_hp));
                }
            }
            continue;
        }
        let alive = w.alive(id);
        if alive != c.alive {
            v.push(format!("c{id} alive {alive} (spec {})", c.alive));
            continue;
        }
        if !alive {
            continue;
        }
        let Some(ch) = w.champ(id) else {
            v.push(format!("c{id} unreadable"));
            continue;
        };
        if (ch.x, ch.y) != (c.x, c.y) {
            v.push(format!("c{id} at ({}, {}) (spec ({}, {}))", ch.x, ch.y, c.x, c.y));
        }
        if (ch.hp as f64 - c.hp).abs() > 0.01 {
            v.push(format!("c{id} hp {} (spec {})", ch.hp, c.hp));
        }
        if c.max_hp > 0.0 && (ch.max as f64 - c.max_hp).abs() > 0.05 {
            v.push(format!("c{id} max hp {} (spec {})", ch.max, c.max_hp));
        }
        let gold = w.gold(id, c.team);
        if gold != c.gold.floor() as u32 {
            v.push(format!("c{id} gold {gold} (spec {})", c.gold));
        }
        let gems = w.gems(id);
        if gems != c.gems {
            v.push(format!("c{id} gems {gems} (spec {})", c.gems));
        }
        let up = (pre && id == last) as u32;
        for s in 0..2 {
            let want = c.cd[s] + if up == 1 && c.cd[s] > 0 { 1 } else { 0 };
            let got = w.cd(id, s as u32);
            if got != Some(want) {
                v.push(format!("c{id} cooldown {s} {got:?} (want {want}, spec {})", c.cd[s]));
            }
        }
        let b = w.buffs(id);
        let stun = b.iter().filter(|x| x.0 == 1).map(|x| x.1).max().unwrap_or(0);
        let want_stun = if c.stun > 0 { c.stun + up } else { 0 };
        if stun != want_stun {
            v.push(format!("c{id} stun {stun} (want {want_stun}, spec {})", c.stun));
        }
        let (amt, turns) = b.iter().filter(|x| x.0 == 0).fold((0f32, 0u32), |a, x| (a.0 + x.2, a.1.max(x.1)));
        let want_turns = if c.shield.0 > 0.0 { c.shield.1 + up } else { 0 };
        if (amt as f64 - c.shield.0).abs() > 0.01 || turns != want_turns {
            v.push(format!("c{id} shield {amt}/{turns} (want {}/{want_turns})", c.shield.0));
        }
        if let (Some(p), false) = (c.prio, pre) {
            // Set in round - 1, it applies from this round.
            let mut o = 0u32;
            unsafe { shim::Game_API_Champion_GetPriority(w.g, OBS, id, 0, &mut o as *mut u32 as P) };
            if o as i32 != p {
                v.push(format!("c{id} priority {} (spec {p})", o as i32));
            }
        }
        if let Some(e) = b.iter().find(|x| x.0 == 2) {
            v.push(format!("c{id} enhanced attack {e:?} (not in the spec)"));
        }
    }
    if !pre {
        let mut got = w.wards();
        got.sort();
        let mut want: Vec<(u32, i32, i32)> = sp.wards.iter().map(|x| (x.owner, x.x, x.y)).collect();
        want.sort();
        let got3: Vec<(u32, i32, i32)> = got.iter().map(|x| (x.0, x.2, x.3)).collect();
        if got3 != want {
            v.push(format!("wards {got3:?} (spec {want:?})"));
        }
        for c in &sp.champs {
            if let (Some(spec), Some(r)) = (c.ward, w.ward_res(c.id)) {
                if (r.0, r.1.max(0) as u32) != spec {
                    v.push(format!("c{} ward charges/recharge {}/{} (spec {}/{})", c.id, r.0, r.1, spec.0, spec.1));
                }
            }
        }
    }
    for cm in &sp.camps {
        match w.camp(cm.id) {
            None => v.push(format!("camp {} unreadable", cm.id)),
            Some((st, hp)) => {
                let alive = st != 0;
                if alive != cm.alive {
                    v.push(format!("camp {} alive {alive} (spec {})", cm.id, cm.alive));
                } else if alive {
                    if (hp as f64 - cm.hp).abs() > 0.01 {
                        v.push(format!("camp {} hp {hp} (spec {})", cm.id, cm.hp));
                    }
                    if (st == 1) != cm.awake {
                        v.push(format!("camp {} awake {} (spec {})", cm.id, st == 1, cm.awake));
                    }
                }
            }
        }
    }
    v
}

// ---------------------------------------------------------------- command line and workers

struct Cli {
    specs: Option<PathBuf>,
    out: Option<PathBuf>,
    bots: [Option<String>; 2],
    jobs: usize,
    skip: usize,
    limit: usize,
    slots: Option<(PathBuf, usize)>,
    release: bool,
    o: LabOpts,
}

fn parse_cli(args: &[String]) -> Result<Cli> {
    let mut c = Cli {
        specs: None,
        out: None,
        bots: [None, None],
        jobs: 1,
        skip: 0,
        limit: usize::MAX,
        slots: None,
        release: false,
        o: LabOpts {
            rollouts: 1, rounds: 30, marks: Vec::new(), hash: false, turns: false, first_fuel: 0, log_limit: 1 << 20, stdout_dir: None,
            lab: false, decisions: false, alt: 0, alt_fighter: None, forces: Vec::new(), warm_pre: WARM_PRE, warm_radius: WARM_RADIUS,
        },
    };
    let mut slot_dir = None;
    let mut slot_n = 0usize;
    let mut i = 0;
    while i < args.len() {
        let a = args[i].as_str();
        let val = || -> Result<&String> { args.get(i + 1).ok_or_else(|| anyhow!("{a} needs a value")) };
        let mut step = 2;
        match a {
            "--bot-a" => c.bots[0] = Some(val()?.clone()),
            "--bot-b" => c.bots[1] = Some(val()?.clone()),
            "--rollouts" => c.o.rollouts = val()?.parse()?,
            "--rounds" => c.o.rounds = val()?.parse()?,
            "--out" | "-o" => c.out = Some(PathBuf::from(val()?)),
            "--jobs" => c.jobs = val()?.parse()?,
            "--skip" => c.skip = val()?.parse()?,
            "--limit" => c.limit = val()?.parse()?,
            "--marks" => c.o.marks = val()?.split(',').filter(|s| !s.is_empty()).map(|s| s.parse()).collect::<Result<_, _>>()?,
            "--log-limit" => c.o.log_limit = val()?.parse()?,
            "--stdout" => c.o.stdout_dir = Some(PathBuf::from(val()?)),
            "--slot-dir" => slot_dir = Some(PathBuf::from(val()?)),
            "--slots" => slot_n = val()?.parse()?,
            "--fuel-quantum" | "--fuel" => crate::fuel::set_quantum(val()?.parse()?),
            "--hash" => {
                c.o.hash = true;
                step = 1;
            }
            "--turns" => {
                c.o.turns = true;
                step = 1;
            }
            "--first-fuel" => c.o.first_fuel = val()?.parse()?,
            "--lab" => {
                c.o.lab = true;
                step = 1;
            }
            "--decisions" => {
                c.o.decisions = true;
                step = 1;
            }
            "--alt" => c.o.alt = val()?.parse()?,
            "--warm-pre" => c.o.warm_pre = val()?.parse()?,
            "--warm-radius" => c.o.warm_radius = val()?.parse()?,
            "--alt-fighter" => c.o.alt_fighter = if val()? == "all" { None } else { Some(val()?.parse()?) },
            "--force-home" | "--force-chase" => {
                let p: Vec<&str> = val()?.split(':').collect();
                ensure!(p.len() == 3, "{a} ID:ROUND:VERDICT");
                c.o.forces.push((p[0].parse()?, p[1].parse()?, (a == "--force-chase") as u8, p[2].parse()?));
            }
            "--release" => {
                c.release = true;
                step = 1;
            }
            _ if a.starts_with("--") => bail!("unknown option {a}"),
            _ => {
                ensure!(c.specs.is_none(), "one SPECS.jsonl");
                c.specs = Some(PathBuf::from(a));
                step = 1;
            }
        }
        i += step;
    }
    if let Some(d) = slot_dir {
        c.slots = Some((d, slot_n.max(1)));
    }
    ensure!(c.o.lab || (c.o.alt == 0 && !c.o.decisions && c.o.forces.is_empty()), "--alt, --decisions and --force-* need --lab");
    // A lab bot's warm start runs unbounded in its first turn, whose fuel readings then show a normal turn's.
    if c.o.first_fuel == 0 {
        c.o.first_fuel = if c.o.lab { 100 } else { 2 };
    }
    Ok(c)
}

fn lab_parts(c: &Cli) -> Result<(Runtime, [Arc<Program>; 2], [PathBuf; 2])> {
    let root = crate::project_root();
    let mut rt = crate::load_runtime()?;
    let mut wasm: Vec<PathBuf> = Vec::new();
    let mut progs = Vec::new();
    for t in 0..2 {
        let b = c.bots[t].as_deref().ok_or_else(|| anyhow!("--bot-{} is required", ["a", "b"][t]))?;
        let w = crate::wasm_of(&crate::resolve_bot(&root, b)?, c.release)?;
        progs.push(rt.program(&w)?);
        wasm.push(w);
    }
    let progs: [Arc<Program>; 2] = [progs[0].clone(), progs[1].clone()];
    Ok((rt, progs, [wasm[0].clone(), wasm[1].clone()]))
}

/// `__scenario_worker ARGS`: reads "idx<TAB>spec line" on stdin; writes "idx<TAB>R|S<TAB>json" lines, then "idx<TAB>D".
pub fn worker_main(args: &[String]) -> Result<i32> {
    let c = parse_cli(args)?;
    let (rt, progs, wasm) = lab_parts(&c)?;
    let mut lab = Lab::new(&rt, progs, [&wasm[0], &wasm[1]], c.o.clone())?;
    let root = crate::project_root();
    let stdin = std::io::stdin();
    let mut out = std::io::stdout().lock();
    for line in stdin.lock().lines() {
        let line = line?;
        let Some((idx, spec)) = line.split_once('\t') else { continue };
        let mut emit = |k: &str, v: &Value| {
            let _ = writeln!(out, "{idx}\t{k}\t{v}");
        };
        lab.run(spec, &root, &mut emit);
        writeln!(out, "{idx}\tD")?;
        out.flush()?;
    }
    Ok(0)
}

pub fn main(args: &[String]) -> Result<i32> {
    let c = parse_cli(args)?;
    let specs = c.specs.clone().ok_or_else(|| anyhow!("usage: fastrunner scenario SPECS.jsonl --bot-a BOT --bot-b BOT --rollouts N --rounds H --out OUT.jsonl [--jobs J]"))?;
    let out_path = c.out.clone().ok_or_else(|| anyhow!("--out is required"))?;
    if let Some(d) = &c.o.stdout_dir {
        std::fs::create_dir_all(d)?;
    }
    let text = std::fs::read_to_string(&specs).with_context(|| format!("reading {}", specs.display()))?;
    let lines: Vec<&str> = text.lines().filter(|l| !l.trim().is_empty()).skip(c.skip).take(c.limit).collect();
    let setup_path = {
        let s = out_path.to_string_lossy();
        PathBuf::from(format!("{}.setup.jsonl", s.strip_suffix(".jsonl").unwrap_or(&s)))
    };
    let mut out = std::io::BufWriter::new(std::fs::File::create(&out_path)?);
    let mut sout = std::io::BufWriter::new(std::fs::File::create(&setup_path)?);
    let t0 = Instant::now();
    let (mut n_roll, mut n_err) = (0usize, 0usize);
    let mut write = |k: &str, j: &str, out: &mut dyn Write, sout: &mut dyn Write| {
        if k == "R" {
            n_roll += 1;
            n_err += j.contains("\"error\"") as usize;
            let _ = writeln!(out, "{j}");
        } else {
            let _ = writeln!(sout, "{j}");
        }
    };
    let jobs = c.jobs.max(1).min(lines.len().max(1));
    let root = crate::project_root();
    let mut slots = c.slots.as_ref().map(|(d, k)| crate::Slots::new(d, *k));
    let take = |slots: &mut Option<crate::Slots>| -> Option<crate::Slot> {
        let s = slots.as_mut()?;
        loop {
            if let Some(x) = s.take() {
                s.set_waiting(false);
                return Some(x);
            }
            s.set_waiting(true);
            std::thread::sleep(std::time::Duration::from_millis(if s.denied { 20 + s.rng % 30 } else { 5 + s.rng % 5 }));
        }
    };
    if jobs == 1 {
        let (rt, progs, wasm) = lab_parts(&c)?;
        let mut lab = Lab::new(&rt, progs, [&wasm[0], &wasm[1]], c.o.clone())?;
        for (i, l) in lines.iter().enumerate() {
            let slot = take(&mut slots);
            let mut buf: Vec<(String, String)> = Vec::new();
            lab.run(l, &root, &mut |k, v| buf.push((k.to_string(), v.to_string())));
            if let (Some(s), Some(x)) = (slots.as_mut(), slot) {
                s.release(x);
            }
            for (k, j) in buf {
                write(&k, &j, &mut out, &mut sout);
            }
            out.flush()?;
            sout.flush()?;
            eprintln!("[{}/{}] {:.1}s", i + 1, lines.len(), t0.elapsed().as_secs_f64());
        }
    } else {
        // Build the bots once here, so workers find them built and compiled.
        drop(lab_parts(&c)?);
        let exe = std::env::current_exe()?;
        let (tx, rx) = std::sync::mpsc::channel::<(usize, String)>();
        let mut inputs: Vec<Option<std::process::ChildStdin>> = Vec::new();
        let mut children = Vec::new();
        let mut current: Vec<Option<Option<crate::Slot>>> = Vec::new();
        let mut idle: Vec<usize> = Vec::new();
        let mut next = 0usize;
        let mut busy = 0usize;
        let mut done = 0usize;
        while done < lines.len() {
            // Never wait for a slot here: finished scenarios' slots are released only by the receive below.
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
                        cmd.env("FASTRUNNER_BUILT", "1").arg("__scenario_worker").args(args);
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
                let poll = std::time::Duration::from_millis(5 + slots.as_ref().map_or(0, |s| s.rng % 20));
                match rx.recv_timeout(poll) {
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
                    // It died mid-scenario: that scenario is lost (a line says so) and the worker is not replaced.
                    if let (Some(s), Some(sl)) = (slots.as_mut(), sl) {
                        s.release(sl);
                    }
                    write("R", &json!({"error": "worker died"}).to_string(), &mut out, &mut sout);
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
                if done % 10 == 0 || done == lines.len() {
                    eprintln!("[{done}/{}] {:.1}s", lines.len(), t0.elapsed().as_secs_f64());
                }
                out.flush()?;
                sout.flush()?;
                continue;
            }
            write(k, j, &mut out, &mut sout);
        }
        drop(inputs);
        for mut ch in children {
            let _ = ch.wait();
        }
        if done < lines.len() {
            eprintln!("fastrunner scenario: {} scenarios lost to dead workers", lines.len() - done);
        }
    }
    out.flush()?;
    sout.flush()?;
    eprintln!(
        "fastrunner scenario: {} scenarios, {n_roll} rollout lines ({n_err} errors) in {:.1}s -> {}",
        lines.len(),
        t0.elapsed().as_secs_f64(),
        out_path.display()
    );
    Ok(0)
}
