//! A cache in front of the engine's own `Engine::Bitboard::ShadowCast`, installed by patching its entry, so every
//! cast is memoised: the engine's vision updates (`Engine::Game::DrawVision`, under `Game_Action_Move` and others)
//! as well as the C API's (`Bitboard_ShadowCastWithScanCount`, whose calls api.rs only caches in native mode).
//!
//! `void ShadowCast(Metadata meta, ChunkPtr walls, Vec2i pos, unsigned short radius, ChunkPtr out, unsigned* scan)`
//! (cambc 4.0.0 at 0x41bdaa0, 0x3495 bytes). The 24-byte Metadata `{w, h, w8, h8, w8 rounded to even, cw}` is
//! passed in memory; walls in rdi, pos in rsi (x low, y high), the radius in dx, out in rcx, scan in r8.
//! It is pure, from its disassembly: it reads only its arguments (the low 16 bits of the radius; walls only within
//! the board's `h8 * cw * 16` bytes, since the octant scans clamp to the board), a rodata constant, and its private
//! thread-local scratch vector `s_rows`, which it empties on entry before pushing and popping rows. It writes:
//! `out` (Bitboard::Zero, then only bits it sets, then `out &= ~walls`), `*scan` (only on the single exit, if
//! non-null, before that last loop), `s_rows` (and allocates it on a thread's first call), and leaves
//! `h8 * cw * 16` in rax, which neither caller (DrawVision, the C API) reads. So a hit zeroes `out`, writes the
//! cached non-zero chunks, sets `*scan` and returns the same rax. A key is the full input contents (metadata and
//! walls bytes, interned; x, y, radius). Inputs outside what was verified (another layout, positions off the
//! board, misaligned or overlapping buffers) and re-entrant or concurrent calls go straight to the original.
//!
//! The patch: the function's first 14 bytes (push r15; mov r15,rsi; push r14; mov r14,rdi; push r13; push r12:
//! whole instructions, no RIP-relative operands, no branch into them) become `jmp [rip+0]` to a stub
//! (`mov r9,[rsp]`: the return address, to count hits per caller), which jumps to `cast`; a trampoline runs the
//! displaced bytes and jumps back to the original's 15th byte. Applied only if the whole function (and its .cold
//! part) has 4.0.0's FNV-1a.
//!
//! Env: FASTRUNNER_SHADOW=0 leaves the engine unpatched; FASTRUNNER_CHECK_SHADOW=1 also runs the original on
//! every hit and aborts on any difference; FASTRUNNER_SHADOW_STATS=1 (or FASTRUNNER_STATS) prints counts at exit.
use crate::engine::Eng;
use std::cell::UnsafeCell;
use std::collections::HashMap;
use std::hash::{BuildHasherDefault, Hasher};
use std::sync::atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering};

const OFF: usize = 0x41bdaa0;
const SIZE: usize = 0x3495;
const FNV: u64 = 0x8c25d78d933ad8fb;
const OFF_COLD: usize = 0x41bda71;
const SIZE_COLD: usize = 0x18;
const FNV_COLD: u64 = 0xb6342b589bd13bda;
const NCOPY: usize = 14;
/// Return addresses of the two callers.
const RET_DRAW_VISION: usize = 0x41a12fa;
const RET_CAPI: usize = 0x41b991e;

/// Bounds (~35 MB a process at most; a game of 100x100 takes ~10k results, ~30k chunks): past one, everything
/// (walls) or the results are dropped. Keys are contents, so entries stay valid across games.
const MAX_WALLS: usize = 2048;
const MAX_WALLS_BYTES: usize = 8 << 20;
const MAX_RESULTS: usize = 1 << 17;
const MAX_CHUNKS: usize = 1 << 20;
const PTR_SLOTS: usize = 64;
const NONE: u32 = u32::MAX;

#[repr(C)]
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct Meta([u32; 6]);

type ScFn = unsafe extern "C" fn(Meta, *const u8, u64, u32, *mut u8, *mut u32) -> u64;

static ORIG: AtomicUsize = AtomicUsize::new(0);
static BUSY: AtomicBool = AtomicBool::new(false);
static CHECK: AtomicBool = AtomicBool::new(false);
static BYPASS_BUSY: AtomicU64 = AtomicU64::new(0);

fn fold(x: u64, k: u64) -> u64 {
    let p = x as u128 * k as u128;
    p as u64 ^ (p >> 64) as u64
}

#[derive(Default)]
struct KeyHasher(u64);
impl Hasher for KeyHasher {
    fn write(&mut self, b: &[u8]) {
        for &x in b {
            self.0 = fold(self.0 ^ x as u64, 0x9e3779b97f4a7c15);
        }
    }
    fn write_u64(&mut self, k: u64) {
        self.0 = fold(k ^ 0x243f6a8885a308d3, 0x9e3779b97f4a7c15);
    }
    fn finish(&self) -> u64 {
        self.0
    }
}
type FastMap<V> = HashMap<u64, V, BuildHasherDefault<KeyHasher>>;

/// `bytes.len()` is a multiple of 16.
fn hash_bytes(b: &[u8]) -> u64 {
    let (mut a, mut c) = (0x13198a2e03707344u64, 0xa4093822299f31d0u64);
    for ch in b.chunks_exact(16) {
        a = fold(a ^ u64::from_le_bytes(ch[..8].try_into().unwrap()), 0x9e3779b97f4a7c15);
        c = fold(c ^ u64::from_le_bytes(ch[8..].try_into().unwrap()), 0xc2b2ae3d27d4eb4f);
    }
    fold(a ^ c.rotate_left(32), 0x165667b19e3779f9)
}

struct Walls {
    meta: Meta,
    next: u32,
    bytes: Box<[u8]>,
}

/// A non-zero 16-byte chunk of a result and its index, stored together so a hit reads one or two cache lines.
#[repr(C)]
struct Chunk {
    data: [u8; 16],
    idx: u32,
}

#[derive(Clone, Copy)]
struct Res {
    scan: u32,
    start: u32,
    len: u32,
}

#[derive(Default)]
struct Counts {
    hits: [u64; 3],
    misses: [u64; 3],
    bypass: u64,
    clears: u64,
    checks: u64,
}

struct Cache {
    walls: Vec<Walls>,
    walls_bytes: usize,
    /// Content hash -> newest board with it (older ones chain through `next`).
    index: FastMap<u32>,
    /// Last board seen at a pointer, re-verified by content on every use.
    ptr_slots: [(usize, u32); PTR_SLOTS],
    results: FastMap<Res>,
    chunks: Vec<Chunk>,
    n: Counts,
}

impl Cache {
    fn new() -> Cache {
        Cache {
            walls: Vec::new(),
            walls_bytes: 0,
            index: FastMap::default(),
            ptr_slots: [(0, NONE); PTR_SLOTS],
            results: FastMap::default(),
            chunks: Vec::new(),
            n: Counts::default(),
        }
    }

    fn clear_results(&mut self) {
        self.results.clear();
        self.chunks.clear();
        self.n.clears += 1;
    }

    /// The interned id of (meta, walls contents).
    fn walls_id(&mut self, meta: &Meta, p: *const u8, bytes: usize) -> u32 {
        let cur = unsafe { std::slice::from_raw_parts(p, bytes) };
        let slot = ((p as usize >> 4).wrapping_mul(0x9e3779b97f4a7c15) >> 58) as usize % PTR_SLOTS;
        let (sp, sid) = self.ptr_slots[slot];
        if sp == p as usize && sid != NONE {
            let w = &self.walls[sid as usize];
            if w.meta == *meta && *w.bytes == *cur {
                return sid;
            }
        }
        let h = hash_bytes(cur) ^ fold(meta.0[0] as u64 | (meta.0[1] as u64) << 32, 0xd6e8feb86659fd93);
        let head = self.index.get(&h).copied().unwrap_or(NONE);
        let mut id = head;
        while id != NONE {
            let w = &self.walls[id as usize];
            if w.meta == *meta && *w.bytes == *cur {
                self.ptr_slots[slot] = (p as usize, id);
                return id;
            }
            id = w.next;
        }
        let mut head = head;
        if self.walls.len() >= MAX_WALLS || self.walls_bytes + bytes > MAX_WALLS_BYTES {
            self.walls.clear();
            self.walls_bytes = 0;
            self.index.clear();
            self.ptr_slots = [(0, NONE); PTR_SLOTS];
            self.clear_results();
            head = NONE;
        }
        let id = self.walls.len() as u32;
        self.walls.push(Walls { meta: *meta, next: head, bytes: cur.into() });
        self.walls_bytes += bytes;
        self.index.insert(h, id);
        self.ptr_slots[slot] = (p as usize, id);
        id
    }

    fn record(&mut self, key: u64, out: &[u8], scan: u32) {
        let nz = out.chunks_exact(16).filter(|c| c.iter().any(|&b| b != 0)).count();
        if self.results.len() >= MAX_RESULTS || self.chunks.len() + nz > MAX_CHUNKS {
            self.clear_results();
        }
        let start = self.chunks.len() as u32;
        for (i, c) in out.chunks_exact(16).enumerate() {
            if c.iter().any(|&b| b != 0) {
                self.chunks.push(Chunk { data: c.try_into().unwrap(), idx: i as u32 });
            }
        }
        self.results.insert(key, Res { scan, start, len: nz as u32 });
    }

    /// Writes a cached result exactly as the original leaves `out`: all zero but the recorded chunks.
    unsafe fn replay(&self, r: Res, out: *mut u8, bytes: usize) {
        std::ptr::write_bytes(out, 0, bytes);
        for c in &self.chunks[r.start as usize..(r.start + r.len) as usize] {
            std::ptr::copy_nonoverlapping(c.data.as_ptr(), out.add(c.idx as usize * 16), 16);
        }
    }
}

struct Global(UnsafeCell<Option<Cache>>);
unsafe impl Sync for Global {}
static CACHE: Global = Global(UnsafeCell::new(None));

#[cold]
#[inline(never)]
unsafe fn new_cache() -> &'static mut Cache {
    (*CACHE.0.get()).insert(Cache::new())
}

struct Unlock;
impl Drop for Unlock {
    fn drop(&mut self) {
        BUSY.store(false, Ordering::Release);
    }
}

fn overlaps(a: usize, an: usize, b: usize, bn: usize) -> bool {
    a < b.wrapping_add(bn) && b < a.wrapping_add(an)
}

/// The board size in bytes if `meta` is what Metadata(w, h) builds, else None.
fn board_bytes(m: &Meta) -> Option<usize> {
    let [w, h, w8, h8, w8e, cw] = m.0;
    let ok = (1..=4096).contains(&w)
        && (1..=4096).contains(&h)
        && w8 == (w + 7) >> 3
        && h8 == (h + 7) >> 3
        && w8e == (w8 + 1) & !1
        && cw == (w8 + 1) >> 1;
    ok.then(|| (h8 * cw) as usize * 16)
}

/// What the original leaves in rax: the byte count of its final loop.
fn rax_of(m: &Meta) -> u64 {
    m.0[3].wrapping_mul(m.0[5]) as u64 * 16
}

/// Entered from the stub with the original's arguments and its caller's return address in r9.
unsafe extern "C" fn cast(meta: Meta, walls: *const u8, pos: u64, r: u32, out: *mut u8, scan: *mut u32, ret: usize) -> u64 {
    let orig: ScFn = std::mem::transmute(ORIG.load(Ordering::Relaxed));
    if BUSY.swap(true, Ordering::Acquire) {
        BYPASS_BUSY.fetch_add(1, Ordering::Relaxed);
        return orig(meta, walls, pos, r, out, scan);
    }
    let _unlock = Unlock;
    let c = match (*CACHE.0.get()).as_mut() {
        Some(c) => c,
        None => new_cache(),
    };
    let (x, y) = (pos as u32 as i32, (pos >> 32) as i32);
    let usable = board_bytes(&meta).filter(|&bytes| {
        let (wp, op, sp) = (walls as usize, out as usize, scan as usize);
        x >= 0
            && y >= 0
            && (x as u32) < meta.0[0]
            && (y as u32) < meta.0[1]
            && wp != 0
            && op != 0
            && wp % 16 == 0
            && op % 16 == 0
            && !overlaps(wp, bytes, op, bytes)
            && (sp == 0 || !overlaps(sp, 4, wp, bytes) && !overlaps(sp, 4, op, bytes))
    });
    let Some(bytes) = usable else {
        c.n.bypass += 1;
        return orig(meta, walls, pos, r, out, scan);
    };
    let who = match ret.wrapping_sub(cambc_base()) {
        RET_DRAW_VISION => 0,
        RET_CAPI => 1,
        _ => 2,
    };
    let id = c.walls_id(&meta, walls, bytes);
    let key = (id as u64) << 48 | (r as u16 as u64) << 32 | (y as u64) << 16 | x as u64;
    if let Some(&res) = c.results.get(&key) {
        c.n.hits[who] += 1;
        c.replay(res, out, bytes);
        if !scan.is_null() {
            *scan = res.scan;
        }
        let rax = rax_of(&meta);
        if CHECK.load(Ordering::Relaxed) {
            c.n.checks += 1;
            let mine = std::slice::from_raw_parts(out, bytes).to_vec();
            let mut s = 0u32;
            let rax2 = orig(meta, walls, pos, r, out, &mut s);
            let theirs = std::slice::from_raw_parts(out, bytes);
            if theirs != &mine[..] || s != res.scan || rax2 != rax {
                eprintln!(
                    "fastrunner: shadow-cast cache differs from the engine at ({x}, {y}) radius {} meta {:?}: out {}, scan {} vs {}, rax {rax} vs {rax2}",
                    r as u16,
                    meta.0,
                    if theirs == &mine[..] { "same" } else { "differs" },
                    res.scan,
                    s
                );
                std::process::abort();
            }
        }
        return rax;
    }
    c.n.misses[who] += 1;
    let mut s = 0u32;
    let rax = orig(meta, walls, pos, r, out, &mut s);
    c.record(key, std::slice::from_raw_parts(out, bytes), s);
    if !scan.is_null() {
        *scan = s;
    }
    rax
}

static BASE: AtomicUsize = AtomicUsize::new(0);
fn cambc_base() -> usize {
    BASE.load(Ordering::Relaxed)
}

fn fnv1a(p: *const u8, n: usize) -> u64 {
    let mut h = 0xcbf29ce484222325u64;
    for i in 0..n {
        h = (h ^ unsafe { *p.add(i) } as u64).wrapping_mul(0x100000001b3);
    }
    h
}

/// The main program's executable segment, page-aligned.
fn text_range() -> Option<(usize, usize)> {
    unsafe extern "C" fn cb(info: *mut libc::dl_phdr_info, _size: usize, data: *mut libc::c_void) -> i32 {
        let info = &*info;
        let pg = libc::sysconf(libc::_SC_PAGESIZE) as usize;
        for i in 0..info.dlpi_phnum as usize {
            let ph = &*info.dlpi_phdr.add(i);
            if ph.p_type == libc::PT_LOAD && ph.p_flags & libc::PF_X != 0 {
                let lo = (info.dlpi_addr as usize + ph.p_vaddr as usize) & !(pg - 1);
                let hi = (info.dlpi_addr as usize + ph.p_vaddr as usize + ph.p_memsz as usize + pg - 1) & !(pg - 1);
                *(data as *mut (usize, usize)) = (lo, hi);
                break;
            }
        }
        1 // the main program comes first
    }
    let mut r = (0usize, 0usize);
    unsafe { libc::dl_iterate_phdr(Some(cb), &mut r as *mut (usize, usize) as *mut libc::c_void) };
    (r.1 > r.0).then_some(r)
}

extern "C" fn report() {
    let busy = BYPASS_BUSY.load(Ordering::Relaxed);
    let Some(c) = (unsafe { &*CACHE.0.get() }) else { return };
    let n = &c.n;
    let rate = |h: u64, m: u64| if h + m == 0 { 0.0 } else { 100.0 * h as f64 / (h + m) as f64 };
    let (h, m) = (n.hits.iter().sum::<u64>(), n.misses.iter().sum::<u64>());
    eprintln!(
        "fastrunner shadow-cast cache: {h} hits / {} calls ({:.1}%); engine vision {:.1}% of {}, C API {:.1}% of {}, other {}; \
         {} bypassed, {busy} busy; {} boards, {} results, {} chunks, {} clears; {} checked",
        h + m,
        rate(h, m),
        rate(n.hits[0], n.misses[0]),
        n.hits[0] + n.misses[0],
        rate(n.hits[1], n.misses[1]),
        n.hits[1] + n.misses[1],
        n.hits[2] + n.misses[2],
        n.bypass,
        c.walls.len(),
        c.results.len(),
        c.chunks.len(),
        n.clears,
        n.checks
    );
}

/// Patches ShadowCast's entry (once per process). Leaves the engine as it is if anything does not match.
pub fn install(eng: &Eng) {
    static ONCE: std::sync::Once = std::sync::Once::new();
    ONCE.call_once(|| {
        if std::env::var_os("FASTRUNNER_SHADOW").is_some_and(|v| v == "0") {
            return;
        }
        if let Err(e) = unsafe { install_at(eng.base) } {
            eprintln!("fastrunner: shadow-cast cache off: {e}");
        }
    });
}

unsafe fn install_at(base: usize) -> Result<(), String> {
    let site = (base + OFF) as *mut u8;
    if fnv1a(site, SIZE) != FNV || fnv1a((base + OFF_COLD) as *const u8, SIZE_COLD) != FNV_COLD {
        return Err("Engine::Bitboard::ShadowCast differs from cambc 4.0.0's".into());
    }
    let (lo, hi) = text_range().ok_or("no executable segment")?;
    if (site as usize) < lo || site as usize + SIZE > hi {
        return Err("ShadowCast is outside the executable segment".into());
    }
    let pg = libc::sysconf(libc::_SC_PAGESIZE) as usize;
    let code = libc::mmap(std::ptr::null_mut(), pg, libc::PROT_READ | libc::PROT_WRITE, libc::MAP_PRIVATE | libc::MAP_ANONYMOUS, -1, 0);
    if code == libc::MAP_FAILED {
        return Err("mmap failed".into());
    }
    let code = code as *mut u8;
    let jmp_abs = |at: *mut u8, to: usize| {
        let j: [u8; 6] = [0xff, 0x25, 0, 0, 0, 0]; // jmp [rip+0]
        std::ptr::copy_nonoverlapping(j.as_ptr(), at, 6);
        std::ptr::copy_nonoverlapping(to.to_le_bytes().as_ptr(), at.add(6), 8);
    };
    // Trampoline: the displaced prologue, then back to the original's next instruction.
    std::ptr::copy_nonoverlapping(site, code, NCOPY);
    jmp_abs(code.add(NCOPY), site as usize + NCOPY);
    // Stub: mov r9, [rsp] (the return address: `cast`'s 7th argument), then on to `cast`.
    let stub = code.add(32);
    std::ptr::copy_nonoverlapping([0x4c, 0x8b, 0x0c, 0x24].as_ptr(), stub, 4);
    jmp_abs(stub.add(4), cast as *const () as usize);
    if libc::mprotect(code as *mut libc::c_void, pg, libc::PROT_READ | libc::PROT_EXEC) != 0 {
        return Err("mprotect of the trampoline failed".into());
    }
    BASE.store(base, Ordering::Relaxed);
    ORIG.store(code as usize, Ordering::Relaxed);
    CHECK.store(std::env::var_os("FASTRUNNER_CHECK_SHADOW").is_some_and(|v| v != "0"), Ordering::Relaxed);
    // The whole segment at once, as turbo.c does: one mapping change, so profilers keep cambc's symbols.
    let prot = libc::PROT_READ | libc::PROT_EXEC;
    if libc::mprotect(lo as *mut libc::c_void, hi - lo, prot | libc::PROT_WRITE) != 0 {
        return Err("mprotect of the text failed".into());
    }
    jmp_abs(site, stub as usize); // exactly NCOPY bytes
    libc::mprotect(lo as *mut libc::c_void, hi - lo, prot);
    if std::env::var_os("FASTRUNNER_SHADOW_STATS").is_some() || std::env::var_os("FASTRUNNER_STATS").is_some() {
        libc::atexit(report);
    }
    Ok(())
}
