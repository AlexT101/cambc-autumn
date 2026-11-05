//! The game API imports, reproduced from cambc 5.0.0's runner::api::{imports, primitives::imports,
//! metadata_imports} closures (specs: research/fastengine/RUNNER.md). Each import validates guest
//! pointers exactly as cambc does (order and error codes matter), charges the same host fuel, and
//! calls the same engine function, which writes straight into guest memory.
#![allow(non_snake_case, clippy::too_many_arguments)]
use crate::engine::{Eng, Game, Persp};
use crate::host::{gptr, split, BotCtx};
use anyhow::Result;
use std::sync::OnceLock;
use wasmtime::{Caller, Linker};

/// Per-bot host state: memoised game reads (valid while the stamp is unchanged: within one turn, until the bot
/// acts) and the valid-tile mask for native bitboard ops.
pub struct ApiState {
    /// Bumped by every action; with the meter's turn number it stamps the memo.
    pub actions: u64,
    pub memo: bool,
    pub native: bool,
    /// The CPU has POPCNT (kern::count).
    pub popcnt: bool,
    round: (u64, u32),
    // Inline tables (no pointer or length to load): a memo hit is a stamp compare and a copy.
    champ: [(u64, [u8; 44]); MEMO_IDS],
    gems: [(u64, [u8; 4]); MEMO_IDS],
    gold: [(u64, [u8; 4]); MEMO_IDS],
    alive: [(u64, u32); MEMO_IDS],
    chan: [(u64, [u8; 4]); MEMO_IDS],
    prio: [(u64, u32); MEMO_IDS * 2],
    cool: [(u64, u32); MEMO_IDS * 2],
    items: [(u64, [u8; 336]); MEMO_IDS],
    cons: [(u64, [u8; 16]); MEMO_IDS],
    wards: [(u64, [u8; 8]); MEMO_IDS],
    pub valid: Vec<u64>,
    /// visible_altar_locks' buffers, kept between calls.
    lock_board: Vec<u128>,
    lock_tiles: Vec<(i32, i32)>,
    locks: Vec<[u8; 24]>,
}

const MEMO_IDS: usize = 32;

impl ApiState {
    pub fn new(meta: &[u32; 5], board_bytes: u64) -> ApiState {
        static FLAGS: OnceLock<(bool, bool)> = OnceLock::new();
        let (memo, native) = *FLAGS.get_or_init(|| {
            (std::env::var("FASTRUNNER_MEMO").map_or(true, |v| v != "0"), std::env::var("FASTRUNNER_NATIVE").map_or(true, |v| v != "0"))
        });
        let mut a = ApiState {
            actions: 0,
            memo,
            native,
            popcnt: std::arch::is_x86_feature_detected!("popcnt"),
            round: (u64::MAX, 0),
            champ: [(u64::MAX, [0; 44]); MEMO_IDS],
            gems: [(u64::MAX, [0; 4]); MEMO_IDS],
            gold: [(u64::MAX, [0; 4]); MEMO_IDS],
            alive: [(u64::MAX, 0); MEMO_IDS],
            chan: [(u64::MAX, [0; 4]); MEMO_IDS],
            prio: [(u64::MAX, 0); MEMO_IDS * 2],
            cool: [(u64::MAX, 0); MEMO_IDS * 2],
            items: [(u64::MAX, [0; 336]); MEMO_IDS],
            cons: [(u64::MAX, [0; 16]); MEMO_IDS],
            wards: [(u64::MAX, [0; 8]); MEMO_IDS],
            valid: Vec::new(),
            lock_board: Vec::new(),
            lock_tiles: Vec::new(),
            locks: Vec::new(),
        };
        a.init_valid(meta, board_bytes);
        a
    }

    fn init_valid(&mut self, meta: &[u32; 5], board_bytes: u64) {
        // Valid tiles of the chunked board (padding bits and words excluded), as the engine's
        // IsZero / IsEqual / NumSetBits mask them.
        let (w, h, cw, ch, stride) = (meta[0] as i64, meta[1] as i64, meta[2] as usize, meta[3] as usize, meta[4] as usize);
        let words = (board_bytes / 8) as usize;
        let mut valid = vec![0u64; words];
        for cy in 0..ch {
            for cx in 0..cw {
                let mut m = 0u64;
                for dy in 0..8i64 {
                    for dx in 0..8i64 {
                        if (cx as i64 * 8 + dx) < w && (cy as i64 * 8 + dy) < h {
                            m |= 1u64 << (dy * 8 + dx);
                        }
                    }
                }
                if cy * stride + cx < words {
                    valid[cy * stride + cx] = m;
                }
            }
        }
        self.valid = valid;
    }
}

type P = *mut u8;
type C = *const u8;

/// Two boards the engine takes together: the same or disjoint. It refuses a partial overlap (error 5, with
/// its last error set), so native ops leave that case to it.
#[inline(always)]
fn same_or_apart(a: P, b: P, n: u64) -> bool {
    a == b || a as u64 + n <= b as u64 || b as u64 + n <= a as u64
}

/// Native bitboard kernels, 16 bytes a step (boards are 16-byte aligned whole 16-byte units), and POPCNT when
/// the CPU has it.
mod kern {
    use std::arch::x86_64::*;

    macro_rules! bin {
        ($name:ident, $op:ident) => {
            /// Union / Intersect / Xor of `n16` 16-byte units.
            #[inline(always)]
            pub unsafe fn $name(a: *const u8, b: *const u8, r: *mut u8, n16: usize) {
                for i in 0..n16 {
                    let v = $op(_mm_load_si128(a.add(16 * i) as _), _mm_load_si128(b.add(16 * i) as _));
                    _mm_store_si128(r.add(16 * i) as _, v);
                }
            }
        };
    }
    bin!(or, _mm_or_si128);
    bin!(and, _mm_and_si128);
    bin!(xor, _mm_xor_si128);

    /// Not of `n8` words.
    #[inline(always)]
    pub unsafe fn not(a: *const u8, r: *mut u8, n8: usize) {
        let ones = _mm_set1_epi64x(-1);
        for i in 0..n8 / 2 {
            _mm_store_si128(r.add(16 * i) as _, _mm_xor_si128(_mm_load_si128(a.add(16 * i) as _), ones));
        }
        if n8 % 2 == 1 {
            let i = n8 - 1;
            *(r as *mut u64).add(i) = !*(a as *const u64).add(i);
        }
    }

    /// Whether `a & m` (IsZero; `b` null) or `(a ^ b) & m` (IsEqual) has no bit set, over m's words.
    #[inline(always)]
    pub unsafe fn none(a: *const u8, b: *const u8, m: &[u64]) -> bool {
        let n = m.len();
        let mp = m.as_ptr() as *const u8;
        let mut acc = _mm_setzero_si128();
        for i in 0..n / 2 {
            let mut v = _mm_load_si128(a.add(16 * i) as _);
            if !b.is_null() {
                v = _mm_xor_si128(v, _mm_load_si128(b.add(16 * i) as _));
            }
            acc = _mm_or_si128(acc, _mm_and_si128(v, _mm_loadu_si128(mp.add(16 * i) as _)));
        }
        let mut s = (_mm_cvtsi128_si64(acc) | _mm_cvtsi128_si64(_mm_unpackhi_epi64(acc, acc))) as u64;
        if n % 2 == 1 {
            let i = n - 1;
            s |= (*(a as *const u64).add(i) ^ if b.is_null() { 0 } else { *(b as *const u64).add(i) }) & m[i];
        }
        s == 0
    }

    /// Set bits of `a & m`.
    #[inline(always)]
    pub unsafe fn count(popcnt: bool, a: *const u8, m: &[u64]) -> u32 {
        if popcnt {
            return count_popcnt(a, m);
        }
        let mut n = 0u32;
        for (i, &w) in m.iter().enumerate() {
            n += (*(a as *const u64).add(i) & w).count_ones();
        }
        n
    }
    #[target_feature(enable = "popcnt")]
    unsafe fn count_popcnt(a: *const u8, m: &[u64]) -> u32 {
        let mut n = 0u32;
        for (i, &w) in m.iter().enumerate() {
            n += (*(a as *const u64).add(i) & w).count_ones();
        }
        n
    }
}

macro_rules! fns {
    ($($name:ident : fn($($arg:ty),*) -> i32;)*) => {
        pub struct Fns { $(pub $name: unsafe extern "C" fn($($arg),*) -> i32,)* }
        impl Fns {
            fn load(e: &Eng) -> Result<Fns> {
                Ok(Fns { $($name: unsafe {
                    let n = stringify!($name);
                    e.func(if n == "Engine_Result" { "_ZN6Engine6ResultENS_9ErrorCodeEPKc" } else { n })?
                },)* })
            }
        }
    };
}

fns! {
    Engine_Result: fn(i32, C) -> i32;
    Game_API_GetSettings: fn(P) -> i32;
    Game_API_GetItemInfo: fn(u32, P) -> i32;
    Game_API_GetConsumableInfo: fn(u32, P) -> i32;
    Game_API_GetCampOccupancy: fn(Game, Persp, P) -> i32;
    Game_API_GetAwakeCampOccupancy: fn(Game, Persp, P) -> i32;
    Game_API_GetAsleepCampOccupancy: fn(Game, Persp, P) -> i32;
    Game_API_GetAllyOccupancy: fn(Game, Persp, P) -> i32;
    Game_API_GetEnemyOccupancy: fn(Game, Persp, P) -> i32;
    Game_API_GetAllyWardOccupancy: fn(Game, Persp, P) -> i32;
    Game_API_GetEnemyWardOccupancy: fn(Game, Persp, P) -> i32;
    Game_API_GetAllyAltarLockOccupancy: fn(Game, Persp, P) -> i32;
    Game_API_GetEnemyAltarLockOccupancy: fn(Game, Persp, P) -> i32;
    Game_API_GetTeleportOccupancy: fn(Game, Persp, P) -> i32;
    Game_API_GetVision: fn(Game, Persp, P) -> i32;
    Game_API_GetVisionMask: fn(Game, Persp, i32, i32, i32, P) -> i32;
    Game_API_GetWardVisionMask: fn(Game, Persp, i32, i32, P) -> i32;
    Game_API_Champion_GetBuffData: fn(Game, Persp, u32, P, u32, *mut u32) -> i32;
    Game_Action_Resign: fn(Game) -> i32;
    Game_Runner_GetState: fn(Game, *mut [u32; 4]) -> i32;
    Game_API_GetRoundNumber: fn(Game, *mut u32) -> i32;
    Game_API_GetSubmittedGemCount: fn(Game, u32, *mut u32) -> i32;
    Game_API_Champion_GetPriority: fn(Game, Persp, u32, i32, P) -> i32;
    Game_API_Map_GetSymmetry: fn(Game, P) -> i32;
    Game_API_Champion_Get: fn(Game, Persp, u32, P) -> i32;
    Bitboard_Zero: fn(C, P) -> i32;
    Bitboard_One: fn(C, P) -> i32;
    Game_API_Map_GetWallBitboard: fn(Game, Persp, P) -> i32;
    Game_API_Map_GetBushBitboard: fn(Game, Persp, P) -> i32;
    Game_API_Map_GetHoleBitboard: fn(Game, Persp, P) -> i32;
    Game_API_Map_GetAltarBitboard: fn(Game, Persp, P) -> i32;
    Game_API_Draft_GetCurrentTeam: fn(Game, *mut u32) -> i32;
    Game_API_GetDraftMemorySize: fn(Game, *mut u32) -> i32;
    Game_API_WriteDraftMemory: fn(Game, u32, u32, C, usize) -> i32;
    Bitboard_ImportRawBuffer: fn(C, P, C, usize) -> i32;
    Bitboard_ImportLinearBuffer: fn(C, P, C, usize) -> i32;
    Bitboard_ExportRawBuffer: fn(C, C, P, usize) -> i32;
    Bitboard_ExportLinearBuffer: fn(C, C, P, usize) -> i32;
    Bitboard_Print: fn(C, C) -> i32;
    Bitboard_Test: fn(C, C, i32, i32, P) -> i32;
    Bitboard_Set: fn(C, P, i32, i32, i32) -> i32;
    Bitboard_Toggle: fn(C, P, i32, i32) -> i32;
    Bitboard_IsZero: fn(C, C, P) -> i32;
    Bitboard_NumSetBits: fn(C, C, P) -> i32;
    Bitboard_GetSetBits: fn(C, C, P, usize, P) -> i32;
    Bitboard_Not: fn(C, C, P) -> i32;
    Bitboard_Union: fn(C, C, C, P) -> i32;
    Bitboard_Intersect: fn(C, C, C, P) -> i32;
    Bitboard_Xor: fn(C, C, C, P) -> i32;
    Bitboard_IsEqual: fn(C, C, C, P) -> i32;
    Bitboard_ShiftRight: fn(C, C, P, i32) -> i32;
    Bitboard_ShiftUp: fn(C, C, P, i32) -> i32;
    Bitboard_Reflect: fn(C, C, P, i32) -> i32;
    Bitboard_DrawCircle: fn(C, P, i32, i32, f32) -> i32;
    Bitboard_DrawChebyshev: fn(C, P, i32, i32, f32) -> i32;
    Bitboard_ReflectHorizontalPosition: fn(C, i32, i32, P, P) -> i32;
    Bitboard_ReflectVerticalPosition: fn(C, i32, i32, P, P) -> i32;
    Bitboard_Rotate180Position: fn(C, i32, i32, P, P) -> i32;
    Bitboard_ReachableMaskWithExpansionCount: fn(C, C, i32, i32, P, u16, *mut u16) -> i32;
    Bitboard_ShadowCastWithScanCount: fn(C, C, i32, i32, P, u32, *mut u32) -> i32;
    Bitboard_ReachableMaskWithScratchAndExpansionCount: fn(C, C, i32, i32, P, u16, P, P, *mut u16) -> i32;
    DistanceField_ImportRawBuffer: fn(C, P, C, usize) -> i32;
    DistanceField_ImportLinearBuffer: fn(C, P, C, usize) -> i32;
    DistanceField_ExportRawBuffer: fn(C, C, P, usize) -> i32;
    DistanceField_ExportLinearBuffer: fn(C, C, P, usize) -> i32;
    DistanceField_Print: fn(C, C) -> i32;
    DistanceField_Copy: fn(C, C, P) -> i32;
    DistanceField_CopyWithMask: fn(C, C, C, P) -> i32;
    DistanceField_Get: fn(C, C, i32, i32, P) -> i32;
    DistanceField_Set: fn(C, P, i32, i32, u16) -> i32;
    DistanceField_ComputeWithExpansionCount: fn(C, C, C, P, P, u16, P) -> i32;
    DistanceField_ComputeToWithExpansionCount: fn(C, C, C, C, P, P, u16, P) -> i32;
    Game_API_InVision: fn(Game, Persp, i32, i32, P) -> i32;
    Game_API_HasCamp: fn(Game, Persp, i32, i32, P) -> i32;
    Game_API_HasChampion: fn(Game, Persp, i32, i32, P) -> i32;
    Game_API_Champion_IsAlive: fn(Game, u32, P) -> i32;
    Game_API_Champion_GetCooldown: fn(Game, Persp, u32, u32, P) -> i32;
    Game_API_GetSpawnRegion: fn(Game, u32, P) -> i32;
    Game_API_Draft_GetNumRounds: fn(Game, P) -> i32;
    Game_Action_Draft: fn(Game, i32) -> i32;
    Game_API_Draft_Get: fn(Game, u32, u8, P) -> i32;
    Game_API_Camp_GetState: fn(Game, Persp, u32, P) -> i32;
    Game_API_CampGroup_GetState: fn(Game, Persp, u32, P) -> i32;
    Game_API_CampGroup_GetCaptureState: fn(Game, Persp, u32, P) -> i32;
    Game_API_CampGroup_GetCooldown: fn(Game, Persp, u32, P) -> i32;
    Game_API_Map_GetNumCampGroups: fn(Game, *mut u32) -> i32;
    Game_API_Map_GetCampGroups: fn(Game, *mut u32, u32, *mut u32) -> i32;
    Game_API_Map_CampGroup_GetNumCamps: fn(Game, u32, *mut u32) -> i32;
    Game_API_Map_CampGroup_GetCampInfo: fn(Game, u32, *mut u32, u32, *mut u32) -> i32;
    Game_API_Map_CampGroup_Get: fn(Game, u32, *mut u32) -> i32;
    Game_API_Map_CampGroup_GetRespawnTime: fn(Game, u32, *mut u32) -> i32;
    Game_API_Map_CampInfo_Get: fn(Game, u32, *mut u32) -> i32;
    Game_API_Map_CampInfo_GetGroup: fn(Game, u32, P) -> i32;
    Game_API_Map_GetCampAt: fn(Game, i32, i32, P) -> i32;
    Game_API_Champion_GetNumAllies: fn(Game, Persp, P) -> i32;
    Game_API_Champion_GetNumEnemies: fn(Game, Persp, P) -> i32;
    Game_API_GetCamp: fn(Game, Persp, i32, i32, P) -> i32;
    Game_API_Camp_Get: fn(Game, Persp, u32, P) -> i32;
    Game_API_GetChampion: fn(Game, Persp, i32, i32, P) -> i32;
    Game_API_Champion_GetIdentity: fn(Game, Persp, u32, P) -> i32;
    Game_API_GetAllyWard: fn(Game, Persp, i32, i32, *mut u32) -> i32;
    Game_API_GetEnemyWard: fn(Game, Persp, i32, i32, *mut u32) -> i32;
    Game_API_Ward_Get: fn(Game, Persp, u32, P) -> i32;
    Game_API_Champion_GetGold: fn(Game, Persp, u32, P) -> i32;
    Game_API_Champion_GetGems: fn(Game, Persp, u32, P) -> i32;
    Game_API_Champion_GetItems: fn(Game, Persp, u32, P, u32) -> i32;
    Game_API_Champion_GetConsumables: fn(Game, Persp, u32, P, u32) -> i32;
    Game_API_Champion_CanSell: fn(Game, Persp, u32, P) -> i32;
    Game_API_Champion_GetChannelTime: fn(Game, Persp, u32, P) -> i32;
    Game_API_Champion_GetWardPositions: fn(Game, Persp, u32, P, u32, P) -> i32;
    Game_API_Camp_GetBuffs: fn(Game, Persp, u32, P, u32, P) -> i32;
    Game_API_Champion_GetAllies: fn(Game, Persp, P, u32, P) -> i32;
    Game_API_Champion_GetEnemies: fn(Game, Persp, P, u32, P) -> i32;
    Game_API_GetWards: fn(Game, Persp, P, u32, P) -> i32;
    Game_API_IsOccupiedByTeleport: fn(Game, Persp, i32, i32, P) -> i32;
    Game_API_GetAltarLock: fn(Game, Persp, i32, i32, u32, P) -> i32;
    Game_API_Map_GetBitboardMetadata: fn(Game, *mut [u32; 5]) -> i32;
    Game_API_GetTeleports: fn(Game, Persp, P, u32, P) -> i32;
    Game_API_GetTeleport: fn(Game, Persp, i32, i32, P) -> i32;
    Game_API_GetSharedMemorySize: fn(Game, P) -> i32;
    Game_API_Champion_Design: fn(Game, u32, P) -> i32;
    Game_API_Camp_Design: fn(Game, u32, P) -> i32;
    Game_API_Champion_GetRestrictions: fn(Game, Persp, u32, P) -> i32;
    Game_API_Champion_CanShop: fn(Game, Persp, u32, u32, P) -> i32;
    Game_API_Champion_GetWards: fn(Game, Persp, u32, P) -> i32;
    Game_API_Champion_GetAbilityDamage: fn(Game, Persp, u32, u32, P) -> i32;
    Game_API_Champion_GetAbilityDamageAgainst: fn(Game, Persp, u32, u32, u32, P) -> i32;
    Game_API_Champion_GetAbilityHeal: fn(Game, Persp, u32, u32, P) -> i32;
    Game_API_Champion_GetAbilityHealAgainst: fn(Game, Persp, u32, u32, u32, P) -> i32;
    Game_API_Champion_GetAbilityShield: fn(Game, Persp, u32, u32, P) -> i32;
    Game_API_Champion_GetAbilityShieldAgainst: fn(Game, Persp, u32, u32, u32, P) -> i32;
    Game_API_Champion_GetAbilityProps: fn(Game, Persp, u32, u32, P) -> i32;
    Game_API_ReadSharedMemory: fn(Game, u32, u32, P, u32) -> i32;
    Game_API_WriteSharedMemory: fn(Game, u32, u32, C, u32) -> i32;
    Game_API_ReadDraftMemory: fn(Game, u32, u32, P, u32) -> i32;
    Game_Action_Move: fn(Game, i32, i32, P) -> i32;
    Game_Action_Cast: fn(Game, u32, u64, u64, P) -> i32;
    Game_Action_UseConsumable: fn(Game, u32, u64, P) -> i32;
    Game_Action_PlaceWard: fn(Game, u64, P) -> i32;
    Game_Action_Attack: fn(Game, u64) -> i32;
    Game_Action_Recall: fn(Game) -> i32;
    Game_Action_SubmitGems: fn(Game, u64) -> i32;
    Game_Action_CancelChannel: fn(Game) -> i32;
    Game_Action_Sell: fn(Game, u32) -> i32;
    Game_Action_BuyItem: fn(Game, u32, u32) -> i32;
    Game_Action_BuyConsumable: fn(Game, u32) -> i32;
    Game_Action_SetPriority: fn(Game, i32) -> i32;
}

// Written once by init() before any game; read without OnceLock's state load (f()).
static mut FNS: std::mem::MaybeUninit<Fns> = std::mem::MaybeUninit::uninit();
static FNS_SET: std::sync::Once = std::sync::Once::new();

/// FASTRUNNER_CHECK_DF=1: verify distance-field / shadow-cast purity (slow; diagnostics only).
fn check_df() -> bool {
    static C: OnceLock<bool> = OnceLock::new();
    *C.get_or_init(|| std::env::var_os("FASTRUNNER_CHECK_DF").is_some())
}
static EMPTY: [u8; 1] = [0];

pub fn init(e: &Eng) -> Result<()> {
    if !FNS_SET.is_completed() {
        let f = Fns::load(e)?;
        FNS_SET.call_once(|| unsafe { (*std::ptr::addr_of_mut!(FNS)).write(f); });
    }
    // The direct write of the engine's thread-local last error must land where GetLastErrorMsg reads.
    unsafe {
        let tp: usize;
        std::arch::asm!("mov {}, fs:0", out(reg) tp, options(nostack, readonly, preserves_flags));
        let slot = (tp - 0x5f0) as *mut *const u8;
        let old = *slot;
        *slot = EMPTY.as_ptr();
        let ok = (e.GetLastErrorMsg)() as *const u8 == EMPTY.as_ptr();
        *slot = old;
        anyhow::ensure!(ok, "engine last-error slot not where expected");
    }
    Ok(())
}

#[inline(always)]
fn f() -> &'static Fns {
    unsafe { (*std::ptr::addr_of!(FNS)).assume_init_ref() }
}

const ERR: i32 = -1;
const INVALID_ACTION: i32 = 18;
const OUT_OF_RANGE: i32 = 110;

/// The inline out-pointer check of the runner::api::imports closures: no null check; `align` 1 skips
/// the alignment test.
#[inline(always)]
fn optr(mem: &[u8], p: i32, size: u64, align: u64) -> Option<usize> {
    if p < 0 {
        return None;
    }
    let p = p as u64;
    if p + size > mem.len() as u64 {
        return None;
    }
    if align > 1 && (mem.as_ptr() as u64 + p) % align != 0 {
        return None;
    }
    Some(p as usize)
}

/// LIST(E): (buf, cap, count) list output checks. Returns (buffer host ptr or NULL, cap, count host ptr).
#[inline(always)]
fn list(mem: &mut [u8], buf: i32, cap: i32, count: i32, e: u64, null_when_empty: bool) -> Option<(P, u32, P)> {
    if cap < 0 {
        return None;
    }
    let (start, end) = if cap != 0 {
        if buf < 0 {
            return None;
        }
        (buf as u64, buf as u64 + cap as u64 * e)
    } else {
        (0, 0)
    };
    if count < 0 {
        return None;
    }
    let len = mem.len() as u64;
    let c = count as u64;
    if end > len || c + 4 > len {
        return None;
    }
    if start < c + 4 && end > c {
        return None;
    }
    let base = mem.as_mut_ptr();
    if (base as u64 + start) & 3 != 0 || (base as u64 + c) & 3 != 0 {
        return None;
    }
    let bp = if cap == 0 && null_when_empty { std::ptr::null_mut() } else { unsafe { base.add(start as usize) } };
    Some((bp, cap as u32, unsafe { base.add(c as usize) }))
}

#[inline(always)]
fn rd_u32(p: P) -> u32 {
    unsafe { (p as *const u32).read_unaligned() }
}

/// A u32 into guest memory at an offset already checked (gptr / optr).
#[inline(always)]
fn wr32(mem: &mut [u8], o: usize, v: u32) {
    unsafe { (mem.as_mut_ptr().add(o) as *mut u32).write_unaligned(v) }
}

#[inline(always)]
fn hp(mem: &mut [u8], o: usize) -> P {
    unsafe { mem.as_mut_ptr().add(o) }
}

impl BotCtx {
    #[inline(always)]
    fn chunks(&self) -> u64 {
        self.meta[2] as u64 * self.meta[3] as u64
    }
    #[inline(always)]
    fn charge(&mut self, n: u64) {
        self.meter().charge(n);
    }
    #[inline(always)]
    fn metap(&self) -> C {
        self.meta.as_ptr() as C
    }
    /// A bitboard: board_bytes at 16-byte alignment.
    #[inline(always)]
    fn bb(&self, mem: &mut [u8], p: i32) -> Option<P> {
        gptr(mem, p, self.board_bytes >> 3, 8, 16).map(|o| hp(mem, o))
    }
    /// A distance field: field_bytes at 2-byte alignment.
    #[inline(always)]
    fn df(&self, mem: &mut [u8], p: i32) -> Option<P> {
        gptr(mem, p, self.field_bytes >> 1, 2, 2).map(|o| hp(mem, o))
    }
    /// The memo stamp: changes every turn and after every action.
    #[inline(always)]
    fn stamp(&mut self) -> u64 {
        let t = self.meter().turn;
        t << 32 | (self.api.actions & 0xffff_ffff)
    }
    /// A memo hit stands in for a successful engine read, which sets the engine's last error to "".
    #[inline(always)]
    fn ok_result(&self) {
        // Engine::Result(0, "") stores the message in the engine's thread-local last error, at fs:0 - 0x5f0
        // in cambc 5.0.0 (Engine::GetLastErrorMsg); write it directly.
        unsafe {
            let tp: usize;
            std::arch::asm!("mov {}, fs:0", out(reg) tp, options(nostack, readonly, preserves_flags));
            *((tp - 0x5f0) as *mut *const u8) = EMPTY.as_ptr();
        }
    }
    /// GuestIdentity::is_current_input: is it this bot's turn?
    fn is_current_input(&self) -> bool {
        let mut st = [0u32; 4];
        if unsafe { (f().Game_Runner_GetState)(self.game, &mut st) } != 0 {
            return false;
        }
        match st[0] {
            2 => false,
            _ if st[1] != self.team => false,
            0 => self.champion == u32::MAX,
            _ => self.champion == st[3],
        }
    }
}

macro_rules! tryp {
    ($e:expr) => {
        match $e {
            Some(v) => v,
            None => return ERR,
        }
    };
}

/// span(c, r, n): chunk columns covered by [c-r, c+r] clamped to the map (DrawCircle/ReachableMask fuel).
fn span(c: i32, r: i64, n: i32) -> u64 {
    let n1 = (if n >= 2 { n } else { 1 }) as i64 - 1;
    let c = c as i64;
    let hi = c.saturating_add(r);
    let lo = c.saturating_sub(r);
    let hc = if hi < 0 { 0 } else { hi.min(n1) >> 3 };
    let lc = if lo < 0 { 0 } else { lo.min(n1) >> 3 };
    (hc - lc + 1) as u64
}

fn draw_radius(radius: f32, w: i32, h: i32) -> i64 {
    let wh = w as i64 + h as i64;
    if !radius.is_finite() {
        return wh;
    }
    let c = radius.max(0.0).ceil();
    let k = if c > 9.2233715e18f32 { i64::MAX } else { c as i64 };
    k.min(wh)
}

pub fn add_to_linker(l: &mut Linker<BotCtx>) -> Result<()> {
    let w = crate::runtime::werr;
    macro_rules! def {
        ($name:expr, $f:expr $(,)?) => {
            l.func_wrap("env", $name, $f).map_err(w)?;
        };
    }

    type Cx<'a> = Caller<'a, BotCtx>;
    include!("api_defs.rs");
    Ok(())
}

/// The same imports as native-mode trampolines (native.rs).
pub fn native_imports(r: &mut crate::native::Registry) {
    macro_rules! def {
        ($name:expr, $f:expr $(,)?) => {
            r.add("env", $name, $f);
        };
    }
    type Cx<'a> = crate::native::NCaller<'a>;
    include!("api_defs.rs");
}

/// runner::api::camp_layout: per group [g, gold, gems, respawn, k], then per camp [c, type, x, y].
fn camp_layout(g: Game) -> Result<Vec<u32>, i32> {
    let f = f();
    let mut v = Vec::new();
    let mut n = 0u32;
    let r = unsafe { (f.Game_API_Map_GetNumCampGroups)(g, &mut n) };
    if r != 0 {
        return Err(r);
    }
    let mut groups = vec![0u32; n as usize];
    let cap = n;
    let p = if n == 0 { std::ptr::null_mut() } else { groups.as_mut_ptr() };
    let r = unsafe { (f.Game_API_Map_GetCampGroups)(g, p, cap, &mut n) };
    if r != 0 {
        return Err(r);
    }
    for &grp in &groups[..n.min(cap) as usize] {
        let mut info = [0u32; 2];
        let (mut resp, mut nc) = (0u32, 0u32);
        let r1 = unsafe { (f.Game_API_Map_CampGroup_Get)(g, grp, info.as_mut_ptr()) };
        let r2 = unsafe { (f.Game_API_Map_CampGroup_GetRespawnTime)(g, grp, &mut resp) };
        let r3 = unsafe { (f.Game_API_Map_CampGroup_GetNumCamps)(g, grp, &mut nc) };
        for r in [r1, r2, r3] {
            if r != 0 {
                return Err(r);
            }
        }
        let m = nc;
        let mut camps = vec![0u32; m as usize];
        let p = if m == 0 { std::ptr::null_mut() } else { camps.as_mut_ptr() };
        let r = unsafe { (f.Game_API_Map_CampGroup_GetCampInfo)(g, grp, p, m, &mut nc) };
        if r != 0 {
            return Err(r);
        }
        let k = nc.min(m);
        v.extend_from_slice(&[grp, info[1], info[0], resp, k]);
        for &camp in &camps[..k as usize] {
            let mut ci = [0u32; 3];
            let r = unsafe { (f.Game_API_Map_CampInfo_Get)(g, camp, ci.as_mut_ptr()) };
            if r != 0 {
                return Err(r);
            }
            v.extend_from_slice(&[camp, ci[2], ci[0], ci[1]]);
        }
    }
    Ok(v)
}

/// runner::engine::ffi::visible_altar_locks.
fn visible_altar_locks(x: &mut BotCtx, out: P, cap: u32, count: P) -> i32 {
    let mut board = std::mem::take(&mut x.api.lock_board);
    let mut tiles = std::mem::take(&mut x.api.lock_tiles);
    let mut locks = std::mem::take(&mut x.api.locks);
    let r = altar_locks_into(x, out, cap, count, &mut board, &mut tiles, &mut locks);
    (x.api.lock_board, x.api.lock_tiles, x.api.locks) = (board, tiles, locks);
    r
}

fn altar_locks_into(x: &mut BotCtx, out: P, cap: u32, count: P, board: &mut Vec<u128>, tiles: &mut Vec<(i32, i32)>, locks: &mut Vec<[u8; 24]>) -> i32 {
    let f = f();
    let mut meta = [0u32; 5];
    let r = unsafe { (f.Game_API_Map_GetBitboardMetadata)(x.game, &mut meta) };
    if r != 0 {
        return r;
    }
    let words = (meta[3] as usize * meta[4] as usize + 1) & !1;
    // A zeroed board, as a fresh allocation was.
    board.clear();
    board.resize(words / 2 + 1, 0);
    locks.clear();
    let bp = board.as_mut_ptr() as P;
    let (w, h) = (meta[0] as i32, meta[1] as i32);
    let stride = meta[4] as usize;
    for pass in 0..2 {
        let r = unsafe {
            if pass == 0 {
                (f.Game_API_GetAllyAltarLockOccupancy)(x.game, x.persp, bp)
            } else {
                (f.Game_API_GetEnemyAltarLockOccupancy)(x.game, x.persp, bp)
            }
        };
        if r != 0 {
            return r;
        }
        let team = if pass == 0 {
            if x.team == 2 { 0 } else { x.team }
        } else if x.team == 2 {
            1
        } else {
            1u32.wrapping_sub(x.team)
        };
        let b = unsafe { std::slice::from_raw_parts(bp as *const u64, words) };
        // Set tiles in row-major order (y outer, x inner), as the original's full scan visits them. Locks are
        // rare: skip empty runs of words.
        tiles.clear();
        for (ci, run) in b.chunks(8).enumerate() {
            if run.iter().fold(0, |a, &v| a | v) == 0 {
                continue;
            }
            for (k, &word) in run.iter().enumerate() {
                let wi = ci * 8 + k;
                let mut m = word;
                while m != 0 {
                    let bit = m.trailing_zeros() as i32;
                    m &= m - 1;
                    let (cy, cx) = ((wi / stride) as i32, (wi % stride) as i32);
                    let (yy, xx) = (cy * 8 + bit / 8, cx * 8 + bit % 8);
                    if yy < h && xx < w {
                        tiles.push((yy, xx));
                    }
                }
            }
        }
        tiles.sort_unstable();
        for &(yy, xx) in tiles.iter() {
            let mut lock = [0u8; 24];
            let r = unsafe { (f.Game_API_GetAltarLock)(x.game, x.persp, xx, yy, team, lock.as_mut_ptr()) };
            if x.team == 2 && r == 98 {
                continue;
            }
            if r != 0 {
                return r;
            }
            locks.push(lock);
        }
    }
    locks.sort_by_key(|l| u32::from_le_bytes(l[4..8].try_into().unwrap()));
    let n = locks.len();
    if cap != 0 {
        if (cap as usize) < n {
            return 111;
        }
        for (i, l) in locks.iter().enumerate() {
            unsafe { std::ptr::copy_nonoverlapping(l.as_ptr(), out.add(24 * i), 24) };
        }
    }
    unsafe { (count as *mut u32).write_unaligned(n as u32) };
    0
}

/// FASTRUNNER_CHECK_DF: are a distance-field computation's outputs a function of walls, roots,
/// destinations and max distance alone (not of the visited/distances buffers' prior contents)? Also counts
/// distinct inputs, for a cache's hit rate.
fn df_check(x: &BotCtx, pw: P, pr: P, pt: P, pv: P, maxd: u16) {
    use std::collections::HashSet;
    static mut SEEN: Option<HashSet<u64>> = None;
    static mut CALLS: u64 = 0;
    static mut BAD: u64 = 0;
    let bb = x.board_bytes as usize;
    let fb = x.field_bytes as usize;
    let cp = |p: P, n: usize| -> Vec<u8> { if p.is_null() { vec![] } else { unsafe { std::slice::from_raw_parts(p, n) }.to_vec() } };
    let (mut w, mut r, mut t, v0) = (cp(pw, bb), cp(pr, bb), cp(pt, bb), cp(pv, bb));
    let mut key = 0xcbf29ce484222325u64;
    for b in w.iter().chain(r.iter()).chain(t.iter()).chain(maxd.to_le_bytes().iter()).chain(v0.iter()) {
        key = (key ^ *b as u64).wrapping_mul(0x100000001b3);
    }
    let run = |fill: u8, w: &mut Vec<u8>, r: &mut Vec<u8>, t: &mut Vec<u8>| -> (i32, Vec<u8>, Vec<u8>, u16) {
        let mut vis = vec![fill; bb + 16];
        let mut dist = vec![fill; fb + 16];
        let va = (vis.as_mut_ptr() as usize + 15) & !15;
        let da = (dist.as_mut_ptr() as usize + 15) & !15;
        unsafe { std::ptr::copy_nonoverlapping(v0.as_ptr(), va as *mut u8, bb) };
        if fill == 0x5a {
            unsafe { std::ptr::write_bytes(va as *mut u8, 0xa5, bb) };
        }
        let mut cnt = 0u16;
        let rc = unsafe {
            if t.is_empty() {
                (f().DistanceField_ComputeWithExpansionCount)(x.metap(), w.as_ptr(), r.as_ptr(), va as P, da as P, maxd, &mut cnt as *mut u16 as P)
            } else {
                (f().DistanceField_ComputeToWithExpansionCount)(x.metap(), w.as_ptr(), r.as_ptr(), t.as_ptr(), va as P, da as P, maxd, &mut cnt as *mut u16 as P)
            }
        };
        (rc, unsafe { std::slice::from_raw_parts(va as *const u8, bb) }.to_vec(), unsafe { std::slice::from_raw_parts(da as *const u8, fb) }.to_vec(), cnt)
    };
    let a = run(0, &mut w, &mut r, &mut t);
    let b = run(0x5a, &mut w, &mut r, &mut t);
    unsafe {
        CALLS += 1;
        let seen = (*std::ptr::addr_of_mut!(SEEN)).get_or_insert_with(HashSet::new);
        seen.insert(key);
        if a != b {
            BAD += 1;
            eprintln!("df_check: outputs depend on prior buffer contents (rc {} vs {}, visited same {}, dist same {}, count {} vs {})", a.0, b.0, a.1 == b.1, a.2 == b.2, a.3, b.3);
        }
        if CALLS % 2000 == 0 {
            eprintln!("df_check: {} calls, {} distinct inputs (incl. visited), {} input-dependent", CALLS, seen.len(), BAD);
        }
    }
}

fn sc_check(x: &BotCtx, pw: P, px: i32, py: i32, d: u32) {
    use std::collections::HashSet;
    static mut SEEN: Option<HashSet<u64>> = None;
    static mut CALLS: u64 = 0;
    static mut BAD: u64 = 0;
    let bb = x.board_bytes as usize;
    let w = unsafe { std::slice::from_raw_parts(pw, bb) }.to_vec();
    let mut key = 0xcbf29ce484222325u64;
    for b in w.iter().chain(px.to_le_bytes().iter()).chain(py.to_le_bytes().iter()).chain(d.to_le_bytes().iter()) {
        key = (key ^ *b as u64).wrapping_mul(0x100000001b3);
    }
    let run = |fill: u8| {
        let mut out = vec![fill; bb + 16];
        let oa = (out.as_mut_ptr() as usize + 15) & !15;
        let mut scan = 0u32;
        let rc = unsafe { (f().Bitboard_ShadowCastWithScanCount)(x.metap(), w.as_ptr(), px, py, oa as P, d, &mut scan) };
        (rc, unsafe { std::slice::from_raw_parts(oa as *const u8, bb) }.to_vec(), scan)
    };
    let a = run(0);
    let b = run(0xff);
    unsafe {
        CALLS += 1;
        let seen = (*std::ptr::addr_of_mut!(SEEN)).get_or_insert_with(HashSet::new);
        seen.insert(key);
        if a != b {
            BAD += 1;
        }
        if CALLS % 10000 == 0 {
            eprintln!("sc_check: {} calls, {} distinct inputs, {} output depends on prior contents", CALLS, seen.len(), BAD);
        }
    }
}

pub struct ShadowEntry {
    walls: Vec<u8>,
    at: (i32, i32, u32),
    out: Vec<u8>,
    scan: u32,
}

static mut SHADOW: Option<std::collections::HashMap<u64, ShadowEntry>> = None;

/// The per-process shadow-cast memo (one game at a time per process; cleared by `reset_game_caches`).
fn shadow_cache() -> &'static mut std::collections::HashMap<u64, ShadowEntry> {
    unsafe { (*std::ptr::addr_of_mut!(SHADOW)).get_or_insert_with(Default::default) }
}

pub fn reset_game_caches() {
    shadow_cache().clear();
}

fn shadow_key(walls: &[u8], x: i32, y: i32, d: u32) -> u64 {
    let mut h = (x as u32 as u64) << 40 ^ (y as u32 as u64) << 20 ^ d as u64;
    for c in walls.chunks_exact(8) {
        h = (h.rotate_left(5) ^ u64::from_le_bytes(c.try_into().unwrap())).wrapping_mul(0x517cc1b727220a95);
    }
    h
}
