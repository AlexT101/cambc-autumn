//! The wasm engine backend (FASTRUNNER_ENGINE=wasm): cambc's game engine from the viewer's WASM build
//! (tools/replay/engine/v3_0_0.wasm, cambc 5.0.0's engine), translated by wasm2c and compiled natively (build.rs,
//! wengine/glue.c), in place of the native engine inside the cambc binary.
//!
//! Only the game-stateful API (`Game_*`) moves here. `Bitboard_*`, `DistanceField_*`, `GetLastErrorMsg` and
//! `Engine::Result` stay on the native engine: they take no game state. Each `Game_*` name resolves (engine.rs) to a
//! shim below with the native function's C signature, which marshals into the instance's memory: by-value structs
//! (perspective, entity, position) are written to a scratch area, in/out buffers copied in before the call and back
//! after it with exactly the size the native function may touch (the import's checked size, or cap x element), at
//! the host pointer's alignment mod 16, so alignment and null checks see what the native engine saw.
//!
//! The last error: bots read it through the native slot (engine::err_slot), which native calls and the import
//! layer's memo hits also write. Before each wasm call the engine's own slot (a static at ERR_ADDR, written by
//! Engine::Result and read only by GetLastErrorMsg) is set to a sentinel; if the call stored a message, the native
//! slot is pointed at it (inside the instance's memory, whose mapping never moves). Messages are the same strings.
//!
//! State: one instance per process, created on first use. Its whole state is its linear memory and the global g0
//! (glue.c), so `snapshot`/`restore` capture a game exactly. Host-side state that refers to a game: `CUR` (the
//! board size of the last game a shim saw; a pure function of the map) and the import layer's per-bot memo tables
//! (api.rs ApiState, stamped by turn and action count): a caller restoring mid-turn must treat those as stale.
#![allow(non_snake_case, clippy::missing_safety_doc)]
use crate::engine::{Game, Persp};
use std::ptr::null_mut;

/// The wasm2c instance (`w2c_engine`), opaque.
#[repr(C)]
pub struct W2c {
    _p: [u8; 0],
}

/// Every export of the engine module as `w2c_engine_<name>(instance, args...)`: wasm i32 args are u32, pointers are
/// offsets into `memory()`, by-value structs are pointers to them (entity {kind u32, index u32}, position {x i32,
/// y i32}, perspective {team u32, champion u32}). Includes Game_Sandbox_* and Engine_Malloc / Engine_Free.
pub mod raw {
    use super::W2c;
    include!(concat!(env!("OUT_DIR"), "/wengine/exports.rs"));
}
use raw::*;

extern "C" {
    fn fr_w2c_instance() -> *mut W2c;
    fn fr_w2c_mem_base() -> *mut u8;
    fn fr_w2c_mem_size() -> u64;
    fn fr_w2c_snapshot(buf: *mut u8, g0: *mut u32);
    fn fr_w2c_restore(buf: *const u8, size: u64, g0: u32);
}

/// GetLastErrorMsg is `i32.load (i32.const 106248)`; checked at init.
const ERR_ADDR: usize = 106248;
const SCRATCH: u32 = 64 << 10;
/// Scratch layout: [0, 16) the sentinel (an empty string), [16, 64) board-size queries, then per-call buffers.
const BUFS: u32 = 64;

static mut I: *mut W2c = null_mut();
static mut BASE: *mut u8 = null_mut();
static mut SCR: u32 = 0;
type SizeFn = unsafe extern "C" fn(*const [u32; 5], *mut u64) -> i32;
static mut BOARD_SIZE: Option<SizeFn> = None;
/// (game, board bytes) of the last game a board shim saw.
static mut CUR: (Game, usize) = (u64::MAX, 0);

/// Creates the instance (once) and checks the error slot. `board_size`: the native Bitboard_GetRawBufferSize.
pub fn init(board_size: usize) -> anyhow::Result<()> {
    unsafe {
        if !I.is_null() {
            return Ok(());
        }
        let i = fr_w2c_instance();
        let base = fr_w2c_mem_base();
        let s = w2c_engine_Engine_Malloc(i, SCRATCH);
        anyhow::ensure!(s != 0, "wasm engine: scratch allocation failed");
        let p = base.add(ERR_ADDR) as *mut u32;
        let old = p.read();
        p.write(s);
        let ok = w2c_engine_GetLastErrorMsg(i) == s;
        p.write(old);
        anyhow::ensure!(ok, "wasm engine: last-error slot not at {ERR_ADDR}");
        base.add(s as usize).write_bytes(0, SCRATCH as usize);
        BOARD_SIZE = Some(std::mem::transmute::<usize, SizeFn>(board_size));
        (I, BASE, SCR) = (i, base, s);
    }
    Ok(())
}

/// The instance, for raw calls (`raw::*`). Null before `init`.
pub fn instance() -> *mut W2c {
    unsafe { I }
}

/// The instance's linear memory (valid until the next call that may grow it).
pub fn memory() -> &'static mut [u8] {
    unsafe { std::slice::from_raw_parts_mut(fr_w2c_mem_base(), fr_w2c_mem_size() as usize) }
}

/// A copy of the engine's whole state: every game in it, at the moment taken.
pub struct Snapshot {
    mem: Vec<u8>,
    g0: u32,
}

impl Snapshot {
    pub fn bytes(&self) -> usize {
        self.mem.len()
    }
}

pub fn snapshot() -> Snapshot {
    unsafe {
        let mut s = Snapshot { mem: vec![0; fr_w2c_mem_size() as usize], g0: 0 };
        fr_w2c_snapshot(s.mem.as_mut_ptr(), &mut s.g0);
        s
    }
}

/// Copies `s` into a snapshot taken earlier of the same size, without allocating (a rollout loop's restore point).
pub fn snapshot_into(s: &mut Snapshot) {
    unsafe {
        s.mem.resize(fr_w2c_mem_size() as usize, 0);
        fr_w2c_snapshot(s.mem.as_mut_ptr(), &mut s.g0);
    }
}

/// Puts the engine back to `s`. Game handles, scratch and the error slot's sentinel are as they were then.
pub fn restore(s: &Snapshot) {
    unsafe { fr_w2c_restore(s.mem.as_ptr(), s.mem.len() as u64, s.g0) }
}

/// The scenario layer's draft: each team's picks in order, and how many each has made.
pub static mut DRAFT_PICKS: Option<([Vec<u32>; 2], [usize; 2])> = None;

/// Host state a `restore` can leave stale: the board-size cache (a restore to before a game was created can reuse
/// its handle for another map) and the native last-error slot (it may point at a message in the restored memory).
pub fn reset_host() {
    static EMPTY: [u8; 1] = [0];
    unsafe {
        CUR = (u64::MAX, 0);
        *crate::engine::err_slot() = EMPTY.as_ptr();
    }
}

/// Raw-call helpers: by-value structs written to a scratch slot for one call.
pub mod args {
    use super::*;
    /// Writes `v` at scratch slot `k` (0..8, 8 bytes each, after the shims' area) and returns its wasm address.
    pub unsafe fn put(k: usize, v: u64) -> u32 {
        assert!(k < 8);
        let o = SCR + SCRATCH - 64 + 8 * k as u32;
        (BASE.add(o as usize) as *mut u64).write_unaligned(v);
        o
    }
    pub unsafe fn entity(k: usize, kind: u32, index: u32) -> u32 {
        put(k, kind as u64 | (index as u64) << 32)
    }
    pub unsafe fn pos(k: usize, x: i32, y: i32) -> u32 {
        put(k, x as u32 as u64 | (y as u32 as u64) << 32)
    }
    pub unsafe fn persp(k: usize, team: u32, champion: u32) -> u32 {
        put(k, team as u64 | (champion as u64) << 32)
    }
    /// A 4-byte out slot (slot `k`), and reading it back.
    pub unsafe fn out(k: usize) -> u32 {
        put(k, 0)
    }
    pub unsafe fn read32(o: u32) -> u32 {
        (BASE.add(o as usize) as *const u32).read_unaligned()
    }
    /// The engine's last error message.
    pub unsafe fn last_error() -> String {
        let p = w2c_engine_GetLastErrorMsg(I) as usize;
        std::ffi::CStr::from_ptr(BASE.add(p) as *const std::ffi::c_char).to_string_lossy().into_owned()
    }
}

#[inline(always)]
unsafe fn pre() {
    (BASE.add(ERR_ADDR) as *mut u32).write(SCR);
}

#[inline(always)]
unsafe fn post() {
    let v = (BASE.add(ERR_ADDR) as *const u32).read();
    if v != SCR {
        *crate::engine::err_slot() = BASE.add(v as usize);
    }
}

/// One call's marshalling: a bump allocator over the scratch and the buffers to copy back.
struct M {
    cur: u32,
    outs: [(*mut u8, u32, usize); 4],
    n: usize,
    tmp: [u32; 2],
    nt: usize,
}

impl M {
    #[inline(always)]
    unsafe fn new() -> M {
        M { cur: SCR + BUFS, outs: [(null_mut(), 0, 0); 4], n: 0, tmp: [0; 2], nt: 0 }
    }
    #[inline(always)]
    unsafe fn alloc(&mut self, n: usize, h: usize) -> u32 {
        let a = ((self.cur + 15) & !15) + (h & 15) as u32;
        if a as u64 + n as u64 <= (SCR + SCRATCH - 64) as u64 {
            self.cur = a + n as u32;
            return a;
        }
        self.big(n, h)
    }
    /// Beyond the scratch (a long shared-memory read, a map file): a block of its own, freed after the call.
    #[cold]
    unsafe fn big(&mut self, n: usize, h: usize) -> u32 {
        assert!(self.nt < 2 && n < (1 << 31), "wasm engine: buffer of {n} bytes");
        let p = w2c_engine_Engine_Malloc(I, n as u32 + 32);
        assert!(p != 0, "wasm engine: out of memory for a {n}-byte buffer");
        self.tmp[self.nt] = p;
        self.nt += 1;
        ((p + 15) & !15) + (h & 15) as u32
    }
    #[inline(always)]
    unsafe fn val(&mut self, v: u64) -> u32 {
        let o = self.alloc(8, 0);
        (BASE.add(o as usize) as *mut u64).write_unaligned(v);
        o
    }
    /// An input buffer (null stays null).
    #[inline(always)]
    unsafe fn inp(&mut self, h: *const u8, n: usize) -> u32 {
        if h.is_null() {
            return 0;
        }
        let o = self.alloc(n, h as usize);
        std::ptr::copy_nonoverlapping(h, BASE.add(o as usize), n);
        o
    }
    /// An in/out buffer: copied in, and back after the call, so bytes the engine leaves alone come back unchanged.
    #[inline(always)]
    unsafe fn io<T>(&mut self, h: *mut T, n: usize) -> u32 {
        let h = h as *mut u8;
        if h.is_null() {
            return 0;
        }
        let o = self.inp(h, n);
        self.outs[self.n] = (h, o, n);
        self.n += 1;
        o
    }
    #[inline(always)]
    unsafe fn run(self, f: impl FnOnce(*mut W2c) -> u32) -> i32 {
        pre();
        let r = f(I);
        post();
        for &(h, o, n) in &self.outs[..self.n] {
            std::ptr::copy_nonoverlapping(BASE.add(o as usize), h, n);
        }
        for &t in &self.tmp[..self.nt] {
            w2c_engine_Engine_Free(I, t);
        }
        r as i32
    }
}

/// Board bytes of game `g` (Bitboard_GetRawBufferSize of its metadata), cached for the last game seen.
#[inline(always)]
unsafe fn bb(g: Game) -> usize {
    if CUR.0 != g {
        board_size_of(g);
    }
    CUR.1
}

#[cold]
unsafe fn board_size_of(g: Game) {
    let o = SCR + 16;
    let r = w2c_engine_Game_API_Map_GetBitboardMetadata(I, g, o);
    let mut meta = [0u32; 5];
    std::ptr::copy_nonoverlapping(BASE.add(o as usize), meta.as_mut_ptr() as *mut u8, 20);
    let mut n = 0u64;
    if r != 0 || (BOARD_SIZE.unwrap())(&meta, &mut n) != 0 {
        // Not a live game: its board calls fail in the engine before writing; copy nothing.
        n = 0;
    }
    CUR = (g, n as usize);
}

type P = *mut u8;

macro_rules! sz {
    (BB, $g:ident) => {
        bb($g)
    };
    ($n:expr, $g:ident) => {
        $n
    };
}

// (game, perspective, out)
macro_rules! gp_o {
    ($name:ident, $wf:ident, $n:tt) => {
        pub unsafe extern "C" fn $name(g: Game, p: Persp, out: P) -> i32 {
            let n = sz!($n, g);
            let mut m = M::new();
            let pp = m.val(p);
            let o = m.io(out, n);
            m.run(|i| $wf(i, g, pp, o))
        }
    };
}
// (game, perspective, a, out)
macro_rules! gp1_o {
    ($name:ident, $wf:ident, $n:tt) => {
        pub unsafe extern "C" fn $name(g: Game, p: Persp, a: u32, out: P) -> i32 {
            let n = sz!($n, g);
            let mut m = M::new();
            let pp = m.val(p);
            let o = m.io(out, n);
            m.run(|i| $wf(i, g, pp, a, o))
        }
    };
}
// (game, perspective, a, b, out)
macro_rules! gp2_o {
    ($name:ident, $wf:ident, $n:tt) => {
        pub unsafe extern "C" fn $name(g: Game, p: Persp, a: u32, b: u32, out: P) -> i32 {
            let n = sz!($n, g);
            let mut m = M::new();
            let pp = m.val(p);
            let o = m.io(out, n);
            m.run(|i| $wf(i, g, pp, a, b, o))
        }
    };
}
// (game, perspective, a, b, c, out)
macro_rules! gp3_o {
    ($name:ident, $wf:ident, $n:tt) => {
        pub unsafe extern "C" fn $name(g: Game, p: Persp, a: u32, b: u32, c: u32, out: P) -> i32 {
            let n = sz!($n, g);
            let mut m = M::new();
            let pp = m.val(p);
            let o = m.io(out, n);
            m.run(|i| $wf(i, g, pp, a, b, c, o))
        }
    };
}
// (game, out)
macro_rules! g_o {
    ($name:ident, $wf:ident, $n:tt) => {
        pub unsafe extern "C" fn $name(g: Game, out: P) -> i32 {
            let mut m = M::new();
            let o = m.io(out, $n);
            m.run(|i| $wf(i, g, o))
        }
    };
}
// (game, a, out)
macro_rules! g1_o {
    ($name:ident, $wf:ident, $n:tt) => {
        pub unsafe extern "C" fn $name(g: Game, a: u32, out: P) -> i32 {
            let mut m = M::new();
            let o = m.io(out, $n);
            m.run(|i| $wf(i, g, a, o))
        }
    };
}
// (game, a, b, out)
macro_rules! g2_o {
    ($name:ident, $wf:ident, $n:tt) => {
        pub unsafe extern "C" fn $name(g: Game, a: u32, b: u32, out: P) -> i32 {
            let mut m = M::new();
            let o = m.io(out, $n);
            m.run(|i| $wf(i, g, a, b, o))
        }
    };
}
// (game, perspective, buf, cap, count): cap elements of $e bytes
macro_rules! gp_list {
    ($name:ident, $wf:ident, $e:expr) => {
        pub unsafe extern "C" fn $name(g: Game, p: Persp, buf: P, cap: u32, count: P) -> i32 {
            let mut m = M::new();
            let pp = m.val(p);
            let b = m.io(buf, cap as usize * $e);
            let c = m.io(count, 4);
            m.run(|i| $wf(i, g, pp, b, cap, c))
        }
    };
}
// (game, perspective, id, buf, cap, count)
macro_rules! gp1_list {
    ($name:ident, $wf:ident, $e:expr) => {
        pub unsafe extern "C" fn $name(g: Game, p: Persp, id: u32, buf: P, cap: u32, count: P) -> i32 {
            let mut m = M::new();
            let pp = m.val(p);
            let b = m.io(buf, cap as usize * $e);
            let c = m.io(count, 4);
            m.run(|i| $wf(i, g, pp, id, b, cap, c))
        }
    };
}
// (game, id, buf, cap, count)
macro_rules! g1_list {
    ($name:ident, $wf:ident, $e:expr) => {
        pub unsafe extern "C" fn $name(g: Game, id: u32, buf: P, cap: u32, count: P) -> i32 {
            let mut m = M::new();
            let b = m.io(buf, cap as usize * $e);
            let c = m.io(count, 4);
            m.run(|i| $wf(i, g, id, b, cap, c))
        }
    };
}
// (game, scalars...)
macro_rules! g_n {
    ($name:ident, $wf:ident $(, $a:ident)*) => {
        pub unsafe extern "C" fn $name(g: Game $(, $a: u32)*) -> i32 {
            M::new().run(|i| $wf(i, g $(, $a)*))
        }
    };
}

/// The shims, each with its native function's C signature (api.rs `fns!`, engine.rs `engine_fns!`).
pub mod shim {
    use super::*;

    // ---- metadata (no game) ----
    pub unsafe extern "C" fn Game_API_GetSettings(out: P) -> i32 {
        let mut m = M::new();
        let o = m.io(out, 120);
        m.run(|i| w2c_engine_Game_API_GetSettings(i, o))
    }
    pub unsafe extern "C" fn Game_API_GetItemInfo(item: u32, out: P) -> i32 {
        let mut m = M::new();
        let o = m.io(out, 40);
        m.run(|i| w2c_engine_Game_API_GetItemInfo(i, item, o))
    }
    pub unsafe extern "C" fn Game_API_GetConsumableInfo(item: u32, out: P) -> i32 {
        let mut m = M::new();
        let o = m.io(out, 8);
        m.run(|i| w2c_engine_Game_API_GetConsumableInfo(i, item, o))
    }

    // ---- boards ----
    gp_o!(Game_API_GetCampOccupancy, w2c_engine_Game_API_GetCampOccupancy, BB);
    gp_o!(Game_API_GetAwakeCampOccupancy, w2c_engine_Game_API_GetAwakeCampOccupancy, BB);
    gp_o!(Game_API_GetAsleepCampOccupancy, w2c_engine_Game_API_GetAsleepCampOccupancy, BB);
    gp_o!(Game_API_GetAllyOccupancy, w2c_engine_Game_API_GetAllyOccupancy, BB);
    gp_o!(Game_API_GetEnemyOccupancy, w2c_engine_Game_API_GetEnemyOccupancy, BB);
    gp_o!(Game_API_GetAllyWardOccupancy, w2c_engine_Game_API_GetAllyWardOccupancy, BB);
    gp_o!(Game_API_GetEnemyWardOccupancy, w2c_engine_Game_API_GetEnemyWardOccupancy, BB);
    gp_o!(Game_API_GetAllyAltarLockOccupancy, w2c_engine_Game_API_GetAllyAltarLockOccupancy, BB);
    gp_o!(Game_API_GetEnemyAltarLockOccupancy, w2c_engine_Game_API_GetEnemyAltarLockOccupancy, BB);
    gp_o!(Game_API_GetTeleportOccupancy, w2c_engine_Game_API_GetTeleportOccupancy, BB);
    gp_o!(Game_API_GetVision, w2c_engine_Game_API_GetVision, BB);
    gp3_o!(Game_API_GetVisionMask, w2c_engine_Game_API_GetVisionMask, BB);
    gp2_o!(Game_API_GetWardVisionMask, w2c_engine_Game_API_GetWardVisionMask, BB);
    gp_o!(Game_API_Map_GetWallBitboard, w2c_engine_Game_API_Map_GetWallBitboard, BB);
    gp_o!(Game_API_Map_GetBushBitboard, w2c_engine_Game_API_Map_GetBushBitboard, BB);
    gp_o!(Game_API_Map_GetHoleBitboard, w2c_engine_Game_API_Map_GetHoleBitboard, BB);
    gp_o!(Game_API_Map_GetAltarBitboard, w2c_engine_Game_API_Map_GetAltarBitboard, BB);

    // ---- reads ----
    gp1_list!(Game_API_Champion_GetBuffData, w2c_engine_Game_API_Champion_GetBuffData, 12);
    g_o!(Game_Runner_GetState, w2c_engine_Game_Runner_GetState, 16);
    g_o!(Game_API_GetRoundNumber, w2c_engine_Game_API_GetRoundNumber, 4);
    g1_o!(Game_API_GetSubmittedGemCount, w2c_engine_Game_API_GetSubmittedGemCount, 4);
    gp2_o!(Game_API_Champion_GetPriority, w2c_engine_Game_API_Champion_GetPriority, 4);
    g_o!(Game_API_Map_GetSymmetry, w2c_engine_Game_API_Map_GetSymmetry, 4);
    gp1_o!(Game_API_Champion_Get, w2c_engine_Game_API_Champion_Get, 44);
    g_o!(Game_API_Draft_GetCurrentTeam, w2c_engine_Game_API_Draft_GetCurrentTeam, 4);
    g_o!(Game_API_GetDraftMemorySize, w2c_engine_Game_API_GetDraftMemorySize, 4);
    gp2_o!(Game_API_InVision, w2c_engine_Game_API_InVision, 4);
    gp2_o!(Game_API_HasCamp, w2c_engine_Game_API_HasCamp, 4);
    gp2_o!(Game_API_HasChampion, w2c_engine_Game_API_HasChampion, 4);
    g1_o!(Game_API_Champion_IsAlive, w2c_engine_Game_API_Champion_IsAlive, 4);
    gp2_o!(Game_API_Champion_GetCooldown, w2c_engine_Game_API_Champion_GetCooldown, 4);
    g1_o!(Game_API_GetSpawnRegion, w2c_engine_Game_API_GetSpawnRegion, 16);
    g_o!(Game_API_Draft_GetNumRounds, w2c_engine_Game_API_Draft_GetNumRounds, 1);
    pub unsafe extern "C" fn Game_API_Draft_Get(g: Game, team: u32, round: u8, out: P) -> i32 {
        let mut m = M::new();
        let o = m.io(out, 4);
        m.run(|i| w2c_engine_Game_API_Draft_Get(i, g, team, round as u32, o))
    }
    gp1_o!(Game_API_Camp_GetState, w2c_engine_Game_API_Camp_GetState, 4);
    gp1_o!(Game_API_CampGroup_GetState, w2c_engine_Game_API_CampGroup_GetState, 4);
    gp1_o!(Game_API_CampGroup_GetCaptureState, w2c_engine_Game_API_CampGroup_GetCaptureState, 8);
    gp1_o!(Game_API_CampGroup_GetCooldown, w2c_engine_Game_API_CampGroup_GetCooldown, 4);
    g_o!(Game_API_Map_GetNumCampGroups, w2c_engine_Game_API_Map_GetNumCampGroups, 4);
    pub unsafe extern "C" fn Game_API_Map_GetCampGroups(g: Game, buf: P, cap: u32, count: P) -> i32 {
        let mut m = M::new();
        let b = m.io(buf, cap as usize * 4);
        let c = m.io(count, 4);
        m.run(|i| w2c_engine_Game_API_Map_GetCampGroups(i, g, b, cap, c))
    }
    g1_o!(Game_API_Map_CampGroup_GetNumCamps, w2c_engine_Game_API_Map_CampGroup_GetNumCamps, 4);
    g1_list!(Game_API_Map_CampGroup_GetCampInfo, w2c_engine_Game_API_Map_CampGroup_GetCampInfo, 4);
    g1_o!(Game_API_Map_CampGroup_Get, w2c_engine_Game_API_Map_CampGroup_Get, 8);
    g1_o!(Game_API_Map_CampGroup_GetRespawnTime, w2c_engine_Game_API_Map_CampGroup_GetRespawnTime, 4);
    g1_o!(Game_API_Map_CampInfo_Get, w2c_engine_Game_API_Map_CampInfo_Get, 12);
    g1_o!(Game_API_Map_CampInfo_GetGroup, w2c_engine_Game_API_Map_CampInfo_GetGroup, 4);
    g2_o!(Game_API_Map_GetCampAt, w2c_engine_Game_API_Map_GetCampAt, 4);
    gp_o!(Game_API_Champion_GetNumAllies, w2c_engine_Game_API_Champion_GetNumAllies, 4);
    gp_o!(Game_API_Champion_GetNumEnemies, w2c_engine_Game_API_Champion_GetNumEnemies, 4);
    gp2_o!(Game_API_GetCamp, w2c_engine_Game_API_GetCamp, 4);
    gp1_o!(Game_API_Camp_Get, w2c_engine_Game_API_Camp_Get, 32);
    gp2_o!(Game_API_GetChampion, w2c_engine_Game_API_GetChampion, 4);
    gp1_o!(Game_API_Champion_GetIdentity, w2c_engine_Game_API_Champion_GetIdentity, 8);
    gp2_o!(Game_API_GetAllyWard, w2c_engine_Game_API_GetAllyWard, 4);
    gp2_o!(Game_API_GetEnemyWard, w2c_engine_Game_API_GetEnemyWard, 4);
    gp1_o!(Game_API_Ward_Get, w2c_engine_Game_API_Ward_Get, 24);
    gp1_o!(Game_API_Champion_GetGold, w2c_engine_Game_API_Champion_GetGold, 4);
    gp1_o!(Game_API_Champion_GetGems, w2c_engine_Game_API_Champion_GetGems, 4);
    // (game, perspective, id, buf, cap): cap u32 items / consumables
    pub unsafe extern "C" fn Game_API_Champion_GetItems(g: Game, p: Persp, id: u32, buf: P, cap: u32) -> i32 {
        let mut m = M::new();
        let pp = m.val(p);
        let b = m.io(buf, cap as usize * 4);
        m.run(|i| w2c_engine_Game_API_Champion_GetItems(i, g, pp, id, b, cap))
    }
    pub unsafe extern "C" fn Game_API_Champion_GetConsumables(g: Game, p: Persp, id: u32, buf: P, cap: u32) -> i32 {
        let mut m = M::new();
        let pp = m.val(p);
        let b = m.io(buf, cap as usize * 4);
        m.run(|i| w2c_engine_Game_API_Champion_GetConsumables(i, g, pp, id, b, cap))
    }
    gp1_o!(Game_API_Champion_CanSell, w2c_engine_Game_API_Champion_CanSell, 4);
    gp1_o!(Game_API_Champion_GetChannelTime, w2c_engine_Game_API_Champion_GetChannelTime, 4);
    gp1_list!(Game_API_Champion_GetWardPositions, w2c_engine_Game_API_Champion_GetWardPositions, 8);
    gp1_list!(Game_API_Camp_GetBuffs, w2c_engine_Game_API_Camp_GetBuffs, 12);
    gp_list!(Game_API_Champion_GetAllies, w2c_engine_Game_API_Champion_GetAllies, 4);
    gp_list!(Game_API_Champion_GetEnemies, w2c_engine_Game_API_Champion_GetEnemies, 4);
    gp_list!(Game_API_GetWards, w2c_engine_Game_API_GetWards, 24);
    gp2_o!(Game_API_IsOccupiedByTeleport, w2c_engine_Game_API_IsOccupiedByTeleport, 4);
    gp3_o!(Game_API_GetAltarLock, w2c_engine_Game_API_GetAltarLock, 24);
    g_o!(Game_API_Map_GetBitboardMetadata, w2c_engine_Game_API_Map_GetBitboardMetadata, 20);
    gp_list!(Game_API_GetTeleports, w2c_engine_Game_API_GetTeleports, 28);
    gp2_o!(Game_API_GetTeleport, w2c_engine_Game_API_GetTeleport, 28);
    g_o!(Game_API_GetSharedMemorySize, w2c_engine_Game_API_GetSharedMemorySize, 4);
    g1_o!(Game_API_Champion_Design, w2c_engine_Game_API_Champion_Design, 128);
    g1_o!(Game_API_Camp_Design, w2c_engine_Game_API_Camp_Design, 124);
    gp1_o!(Game_API_Champion_GetRestrictions, w2c_engine_Game_API_Champion_GetRestrictions, 1);
    gp2_o!(Game_API_Champion_CanShop, w2c_engine_Game_API_Champion_CanShop, 4);
    gp1_o!(Game_API_Champion_GetWards, w2c_engine_Game_API_Champion_GetWards, 8);
    gp2_o!(Game_API_Champion_GetAbilityDamage, w2c_engine_Game_API_Champion_GetAbilityDamage, 4);
    gp3_o!(Game_API_Champion_GetAbilityDamageAgainst, w2c_engine_Game_API_Champion_GetAbilityDamageAgainst, 4);
    gp2_o!(Game_API_Champion_GetAbilityHeal, w2c_engine_Game_API_Champion_GetAbilityHeal, 4);
    gp3_o!(Game_API_Champion_GetAbilityHealAgainst, w2c_engine_Game_API_Champion_GetAbilityHealAgainst, 4);
    gp2_o!(Game_API_Champion_GetAbilityShield, w2c_engine_Game_API_Champion_GetAbilityShield, 4);
    gp3_o!(Game_API_Champion_GetAbilityShieldAgainst, w2c_engine_Game_API_Champion_GetAbilityShieldAgainst, 4);
    gp2_o!(Game_API_Champion_GetAbilityProps, w2c_engine_Game_API_Champion_GetAbilityProps, 36);

    // ---- team memories: (game, team, offset, buf, len) ----
    pub unsafe extern "C" fn Game_API_ReadSharedMemory(g: Game, team: u32, off: u32, buf: P, len: u32) -> i32 {
        let mut m = M::new();
        let b = m.io(buf, len as usize);
        m.run(|i| w2c_engine_Game_API_ReadSharedMemory(i, g, team, off, b, len))
    }
    pub unsafe extern "C" fn Game_API_ReadDraftMemory(g: Game, team: u32, off: u32, buf: P, len: u32) -> i32 {
        let mut m = M::new();
        let b = m.io(buf, len as usize);
        m.run(|i| w2c_engine_Game_API_ReadDraftMemory(i, g, team, off, b, len))
    }
    pub unsafe extern "C" fn Game_API_WriteSharedMemory(g: Game, team: u32, off: u32, data: *const u8, len: u32) -> i32 {
        let mut m = M::new();
        let d = m.inp(data, len as usize);
        m.run(|i| w2c_engine_Game_API_WriteSharedMemory(i, g, team, off, d, len))
    }
    pub unsafe extern "C" fn Game_API_WriteDraftMemory(g: Game, team: u32, off: u32, data: *const u8, len: usize) -> i32 {
        let mut m = M::new();
        let d = m.inp(data, len);
        m.run(|i| w2c_engine_Game_API_WriteDraftMemory(i, g, team, off, d, len as u32))
    }

    // ---- actions ----
    g_n!(Game_Action_Resign, w2c_engine_Game_Action_Resign);
    /// With `DRAFT_PICKS` set (the scenario layer), the pick is the team's next one from there, whatever the caller
    /// asked for: a draft bot then plans for the picks it is told it made.
    pub unsafe extern "C" fn Game_Action_Draft(g: Game, ty: u32) -> i32 {
        let picks = &mut *std::ptr::addr_of_mut!(DRAFT_PICKS);
        let mut team = usize::MAX;
        let mut ty = ty;
        if let Some((p, k)) = picks.as_ref() {
            let o = SCR + 16;
            if w2c_engine_Game_API_Draft_GetCurrentTeam(I, g, o) == 0 {
                team = args::read32(o) as usize;
            }
            if team < 2 && k[team] < p[team].len() {
                ty = p[team][k[team]];
            }
        }
        let r = M::new().run(|i| w2c_engine_Game_Action_Draft(i, g, ty));
        if let (0, Some((_, k))) = (r, picks.as_mut()) {
            if team < 2 {
                k[team] += 1;
            }
        }
        r
    }
    g_n!(Game_Action_Recall, w2c_engine_Game_Action_Recall);
    g_n!(Game_Action_CancelChannel, w2c_engine_Game_Action_CancelChannel);
    g_n!(Game_Action_Sell, w2c_engine_Game_Action_Sell, item);
    g_n!(Game_Action_BuyItem, w2c_engine_Game_Action_BuyItem, item, n);
    g_n!(Game_Action_BuyConsumable, w2c_engine_Game_Action_BuyConsumable, item);
    g_n!(Game_Action_SetPriority, w2c_engine_Game_Action_SetPriority, p);
    g2_o!(Game_Action_Move, w2c_engine_Game_Action_Move, 4);
    pub unsafe extern "C" fn Game_Action_Cast(g: Game, slot: u32, target: u64, pos: u64, out: P) -> i32 {
        let mut m = M::new();
        let t = m.val(target);
        let q = m.val(pos);
        let o = m.io(out, 4);
        m.run(|i| w2c_engine_Game_Action_Cast(i, g, slot, t, q, o))
    }
    pub unsafe extern "C" fn Game_Action_UseConsumable(g: Game, item: u32, pos: u64, out: P) -> i32 {
        let mut m = M::new();
        let q = m.val(pos);
        let o = m.io(out, 4);
        m.run(|i| w2c_engine_Game_Action_UseConsumable(i, g, item, q, o))
    }
    pub unsafe extern "C" fn Game_Action_PlaceWard(g: Game, pos: u64, out: P) -> i32 {
        let mut m = M::new();
        let q = m.val(pos);
        let o = m.io(out, 4);
        m.run(|i| w2c_engine_Game_Action_PlaceWard(i, g, q, o))
    }
    pub unsafe extern "C" fn Game_Action_Attack(g: Game, target: u64) -> i32 {
        let mut m = M::new();
        let t = m.val(target);
        m.run(|i| w2c_engine_Game_Action_Attack(i, g, t))
    }
    pub unsafe extern "C" fn Game_Action_SubmitGems(g: Game, pos: u64) -> i32 {
        let mut m = M::new();
        let q = m.val(pos);
        m.run(|i| w2c_engine_Game_Action_SubmitGems(i, g, q))
    }

    // ---- the runner's ----
    /// The third argument cambc's runner passes as 0 (Engine::Map::FromFileBytes's flag), as does the viewer.
    pub unsafe extern "C" fn Game_FromMapFileBytes(bytes: *const u8, len: usize, out: *mut Game) -> i32 {
        let mut m = M::new();
        let b = m.inp(bytes, len);
        let o = m.io(out, 8);
        m.run(|i| w2c_engine_Game_FromMapFileBytes(i, b, len as u32, o, 0))
    }
    g_n!(Game_Destroy, w2c_engine_Game_Destroy);
    g_n!(Game_Runner_Init, w2c_engine_Game_Runner_Init);
    g_n!(Game_Runner_EndTurn, w2c_engine_Game_Runner_EndTurn, kind);
    g_n!(Game_Runner_Advance, w2c_engine_Game_Runner_Advance);
    g_n!(Game_SaveReplay, w2c_engine_Game_SaveReplay);
    g_o!(Game_Visualiser_Timeline_GetMain, w2c_engine_Game_Visualiser_Timeline_GetMain, 8);
    pub unsafe extern "C" fn Game_Visualiser_Timeline_Info(g: Game, tl: u64, pos: *mut u32, b: *mut u64, c: *mut u32) -> i32 {
        let mut m = M::new();
        let (op, ob, oc) = (m.io(pos, 4), m.io(b, 8), m.io(c, 4));
        m.run(|i| w2c_engine_Game_Visualiser_Timeline_Info(i, g, tl, op, ob, oc))
    }
    /// The buffer stays in the instance's memory until the game's next SaveReplay or Destroy.
    pub unsafe extern "C" fn Game_FileBuffer(g: Game, p: *mut *const u8, n: *mut usize) -> i32 {
        let mut m = M::new();
        let (op, on) = (m.val(0), m.val(0));
        let r = m.run(|i| w2c_engine_Game_FileBuffer(i, g, op, on));
        if r == 0 {
            *p = BASE.add(args::read32(op) as usize);
            *n = args::read32(on) as usize;
        }
        r
    }
    g_o!(Game_Statistics_GetSummary, w2c_engine_Game_Statistics_GetSummary, 80);
    /// Not exported: statistics are off in this backend (game.rs), where the native function only sets the last
    /// error to "" and returns 18.
    pub unsafe extern "C" fn Game_Statistics_RunnerEvent(_g: Game, _a: u32, _b: u32, _c: u32) -> i32 {
        static EMPTY: [u8; 1] = [0];
        *crate::engine::err_slot() = EMPTY.as_ptr();
        18
    }
    pub unsafe extern "C" fn Game_Statistics_Enable(_g: Game) -> i32 {
        panic!("Game_Statistics_Enable: no statistics with FASTRUNNER_ENGINE=wasm");
    }
}

macro_rules! table {
    ($($name:ident),* $(,)?) => {
        /// Every shimmed name and its address.
        pub fn table() -> Vec<(&'static str, usize)> {
            vec![$((stringify!($name), shim::$name as *const () as usize)),*]
        }
    };
}

table![
    Game_API_GetSettings, Game_API_GetItemInfo, Game_API_GetConsumableInfo,
    Game_API_GetCampOccupancy, Game_API_GetAwakeCampOccupancy, Game_API_GetAsleepCampOccupancy, Game_API_GetAllyOccupancy,
    Game_API_GetEnemyOccupancy, Game_API_GetAllyWardOccupancy, Game_API_GetEnemyWardOccupancy,
    Game_API_GetAllyAltarLockOccupancy, Game_API_GetEnemyAltarLockOccupancy, Game_API_GetTeleportOccupancy,
    Game_API_GetVision, Game_API_GetVisionMask, Game_API_GetWardVisionMask, Game_API_Map_GetWallBitboard,
    Game_API_Map_GetBushBitboard, Game_API_Map_GetHoleBitboard, Game_API_Map_GetAltarBitboard,
    Game_API_Champion_GetBuffData, Game_Runner_GetState, Game_API_GetRoundNumber, Game_API_GetSubmittedGemCount,
    Game_API_Champion_GetPriority, Game_API_Map_GetSymmetry, Game_API_Champion_Get, Game_API_Draft_GetCurrentTeam,
    Game_API_GetDraftMemorySize, Game_API_InVision, Game_API_HasCamp, Game_API_HasChampion, Game_API_Champion_IsAlive,
    Game_API_Champion_GetCooldown, Game_API_GetSpawnRegion, Game_API_Draft_GetNumRounds, Game_API_Draft_Get,
    Game_API_Camp_GetState, Game_API_CampGroup_GetState, Game_API_CampGroup_GetCaptureState,
    Game_API_CampGroup_GetCooldown, Game_API_Map_GetNumCampGroups, Game_API_Map_GetCampGroups,
    Game_API_Map_CampGroup_GetNumCamps, Game_API_Map_CampGroup_GetCampInfo, Game_API_Map_CampGroup_Get,
    Game_API_Map_CampGroup_GetRespawnTime, Game_API_Map_CampInfo_Get, Game_API_Map_CampInfo_GetGroup,
    Game_API_Map_GetCampAt, Game_API_Champion_GetNumAllies, Game_API_Champion_GetNumEnemies, Game_API_GetCamp,
    Game_API_Camp_Get, Game_API_GetChampion, Game_API_Champion_GetIdentity, Game_API_GetAllyWard, Game_API_GetEnemyWard,
    Game_API_Ward_Get, Game_API_Champion_GetGold, Game_API_Champion_GetGems, Game_API_Champion_GetItems,
    Game_API_Champion_GetConsumables, Game_API_Champion_CanSell, Game_API_Champion_GetChannelTime,
    Game_API_Champion_GetWardPositions, Game_API_Camp_GetBuffs, Game_API_Champion_GetAllies, Game_API_Champion_GetEnemies,
    Game_API_GetWards, Game_API_IsOccupiedByTeleport, Game_API_GetAltarLock, Game_API_Map_GetBitboardMetadata,
    Game_API_GetTeleports, Game_API_GetTeleport, Game_API_GetSharedMemorySize, Game_API_Champion_Design,
    Game_API_Camp_Design, Game_API_Champion_GetRestrictions, Game_API_Champion_CanShop, Game_API_Champion_GetWards,
    Game_API_Champion_GetAbilityDamage, Game_API_Champion_GetAbilityDamageAgainst, Game_API_Champion_GetAbilityHeal,
    Game_API_Champion_GetAbilityHealAgainst, Game_API_Champion_GetAbilityShield, Game_API_Champion_GetAbilityShieldAgainst,
    Game_API_Champion_GetAbilityProps, Game_API_ReadSharedMemory, Game_API_ReadDraftMemory, Game_API_WriteSharedMemory,
    Game_API_WriteDraftMemory, Game_Action_Resign, Game_Action_Draft, Game_Action_Recall, Game_Action_CancelChannel,
    Game_Action_Sell, Game_Action_BuyItem, Game_Action_BuyConsumable, Game_Action_SetPriority, Game_Action_Move,
    Game_Action_Cast, Game_Action_UseConsumable, Game_Action_PlaceWard, Game_Action_Attack, Game_Action_SubmitGems,
    Game_FromMapFileBytes, Game_Destroy, Game_Runner_Init, Game_Runner_EndTurn, Game_Runner_Advance, Game_SaveReplay,
    Game_Visualiser_Timeline_GetMain, Game_Visualiser_Timeline_Info, Game_FileBuffer, Game_Statistics_GetSummary,
    Game_Statistics_RunnerEvent, Game_Statistics_Enable,
];

/// `fastrunner __wsnap MAP [ROUNDS]` (FASTRUNNER_ENGINE=wasm): drafts a game, teleports two enemies together with
/// the sandbox, snapshots, plays random rollouts of ROUNDS rounds from the snapshot and checks that equal seeds give
/// equal engine states; prints snapshot, restore and rollout costs.
pub fn selftest(map: &std::path::Path, rounds: u32) -> anyhow::Result<()> {
    use anyhow::{bail, ensure};
    use std::time::Instant;
    let ck = |r: i32, what: &str| -> anyhow::Result<()> {
        if r != 0 {
            bail!("{what} failed ({r}): {}", unsafe { args::last_error() });
        }
        Ok(())
    };
    let bytes = std::fs::read(map)?;
    unsafe {
        let mut g: Game = 0;
        ck(shim::Game_FromMapFileBytes(bytes.as_ptr(), bytes.len(), &mut g), "FromMapFileBytes")?;
        ck(shim::Game_Runner_Init(g), "Runner_Init")?;
        let st = |g: Game| -> [u32; 4] {
            let mut s = [0u32; 4];
            shim::Game_Runner_GetState(g, s.as_mut_ptr() as P);
            s
        };
        let picks = [[0u32, 5, 4, 7, 8], [2, 10, 9, 11, 1]];
        let mut k = [0usize; 2];
        while st(g)[0] == 0 {
            let t = st(g)[1] as usize;
            while shim::Game_Action_Draft(g, picks[t][k[t] % 5]) != 0 {
                k[t] += 1;
            }
            k[t] += 1;
            ck(shim::Game_Runner_EndTurn(g, 0), "EndTurn")?;
        }
        // Sandbox edits need an input boundary (error 18 otherwise): a champion's turn, not the runner's.
        while st(g)[1] == 2 && st(g)[0] != 2 {
            ck(shim::Game_Runner_Advance(g), "Advance")?;
        }
        let obs = crate::engine::persp(2, u32::MAX);
        let mut n = 0u32;
        shim::Game_API_Champion_GetNumAllies(g, obs, &mut n as *mut u32 as P);
        let xy = |g: Game, id: u32| -> Option<(i32, i32, u32)> {
            let mut c = [0i32; 11];
            (shim::Game_API_Champion_Get(g, obs, id, c.as_mut_ptr() as P) == 0).then(|| (c[2], c[3], c[0] as u32))
        };
        // Sandbox: champion 0 to the first free tile near the map's centre, then its first enemy beside it.
        let mut meta = [0u32; 5];
        shim::Game_API_Map_GetBitboardMetadata(g, meta.as_mut_ptr() as P);
        let (cx, cy) = (meta[0] as i32 / 2, meta[1] as i32 / 2);
        let near = |g: Game, id: u32, x0: i32, y0: i32| -> Option<(i32, i32)> {
            for r in 1..8i32 {
                for dy in -r..=r {
                    for dx in -r..=r {
                        if dx.abs().max(dy.abs()) == r
                            && w2c_engine_Game_Sandbox_Teleport(I, g, args::entity(0, 1, id), args::pos(1, x0 + dx, y0 + dy)) == 0
                        {
                            return Some((x0 + dx, y0 + dy));
                        }
                    }
                }
            }
            None
        };
        let Some(a) = near(g, 0, cx, cy) else {
            let rc = w2c_engine_Game_Sandbox_Teleport(I, g, args::entity(0, 1, 0), args::pos(1, cx, cy));
            bail!("sandbox teleport found no tile near ({cx},{cy}): {rc} {}", args::last_error());
        };
        let t0 = xy(g, 0).map_or(0, |c| c.2);
        let e = (1..n).find(|&id| xy(g, id).is_some_and(|c| c.2 != t0)).ok_or_else(|| anyhow::anyhow!("no enemy"))?;
        let b = near(g, e, a.0, a.1);
        println!("{n} champions; sandbox: champion 0 to {a:?}, enemy champion {e} to {b:?} (now {:?})", xy(g, e));
        let mut rng = 0u64;
        let rnd = |rng: &mut u64| {
            *rng ^= *rng << 13;
            *rng ^= *rng >> 7;
            *rng ^= *rng << 17;
            *rng as u32
        };
        let mut play = |g: Game, seed: u64| -> u32 {
            rng = seed;
            let r0 = st(g)[2];
            let mut acts = 0;
            loop {
                let s = st(g);
                if s[0] == 2 || s[2] >= r0 + rounds {
                    break;
                }
                if s[1] == 2 {
                    shim::Game_Runner_Advance(g);
                    continue;
                }
                if let Some((x, y, _)) = xy(g, s[3]) {
                    let mut o = 0u32;
                    for _ in 0..3 {
                        let (dx, dy) = ((rnd(&mut rng) % 3) as i32 - 1, (rnd(&mut rng) % 3) as i32 - 1);
                        if shim::Game_Action_Move(g, (x + dx) as u32, (y + dy) as u32, &mut o as *mut u32 as P) == 0 {
                            acts += 1;
                            break;
                        }
                    }
                    for e in 0..n {
                        if shim::Game_Action_Attack(g, 1 | (e as u64) << 32) == 0 {
                            acts += 1;
                            break;
                        }
                    }
                }
                shim::Game_Runner_EndTurn(g, 0);
            }
            acts
        };
        let hash = || {
            use std::hash::{Hash, Hasher};
            let mut h = std::collections::hash_map::DefaultHasher::new();
            memory().hash(&mut h);
            h.finish()
        };
        let t = Instant::now();
        let snap = snapshot();
        let t_snap = t.elapsed();
        let mut scratch = snapshot();
        let t = Instant::now();
        for _ in 0..100 {
            snapshot_into(&mut scratch);
        }
        let t_into = t.elapsed() / 100;
        let mut hs = Vec::new();
        let mut t_play = std::time::Duration::ZERO;
        let mut t_rest = std::time::Duration::ZERO;
        for (k, seed) in [12345u64, 12345, 999, 12345].into_iter().enumerate() {
            let t = Instant::now();
            restore(&snap);
            t_rest += t.elapsed();
            let t = Instant::now();
            let acts = play(g, seed);
            t_play += t.elapsed();
            let h = hash();
            println!("rollout {k} (seed {seed}): {acts} actions, round {}, memory {} KiB, state hash {h:016x}", st(g)[2], memory().len() >> 10);
            hs.push(h);
        }
        ensure!(hs[0] == hs[1] && hs[0] == hs[3], "equal seeds from one snapshot gave different states");
        ensure!(hs[2] != hs[0], "different seeds gave the same state");
        println!(
            "ok: snapshot {} KiB, first {:.1} us, into an existing one {:.1} us; restore {:.1} us; rollout of {rounds} rounds {:.2} ms",
            snap.bytes() >> 10,
            t_snap.as_secs_f64() * 1e6,
            t_into.as_secs_f64() * 1e6,
            t_rest.as_secs_f64() / 4.0 * 1e6,
            t_play.as_secs_f64() / 4.0 * 1e3
        );
        restore(&snap);
        shim::Game_Destroy(g);
    }
    Ok(())
}
