//! Host side of a bot: its context, WASI subset, and the fuel/turn imports. The game API imports are
//! in api.rs.
use crate::engine::{Eng, Game};
use crate::fuel::Meter;
use anyhow::Result;
use std::future::Future;
use std::pin::Pin;
use std::task::{Context, Poll};
use wasmtime::{Caller, Linker, Memory};

/// A team's stdout (team-x.stdout): every bot of the team appends, capped at the log limit
/// (runner::TeamLog::flush). Before each write it pads with one NUL per replay-timeline step since the
/// last write, which lets the viewer align output with the replay; padding does not count to the limit.
pub struct TeamLog {
    pub buf: Vec<u8>,
    pub limit: usize,
    pub written: usize,
    pub last_pos: u32,
}

impl TeamLog {
    pub fn new(limit: usize) -> TeamLog {
        TeamLog { buf: Vec::new(), limit, written: 0, last_pos: 0 }
    }
    pub fn write(&mut self, b: &[u8], pos: u32) {
        let room = self.limit.saturating_sub(self.written);
        if room == 0 {
            return;
        }
        let gap = pos.wrapping_sub(self.last_pos) as usize;
        self.buf.resize(self.buf.len() + gap, 0);
        self.last_pos = pos;
        let n = room.min(b.len());
        self.buf.extend_from_slice(&b[..n]);
        self.written += n;
    }
}

/// What a bot needs to know about itself and the map (set at spawn).
#[derive(Clone, Copy)]
pub struct BotInit {
    pub game: Game,
    pub team: u32,
    pub champion: u32,
    pub ctype: u32,
    pub meta: [u32; 5],
    pub board_bytes: u64,
    pub field_bytes: u64,
}

pub struct BotCtx {
    pub eng: &'static Eng,
    pub game: Game,
    pub persp: u64,
    pub team: u32,
    pub champion: u32,
    pub ctype: u32,
    pub meta: [u32; 5],
    pub board_bytes: u64,
    pub field_bytes: u64,
    pub mem: Option<Memory>,
    /// The memory's VMMemoryDefinition {base, current_length} (null until instantiated).
    pub memdef: *const u8,
    pub meter: *mut Meter,
    pub log: *mut TeamLog,
    /// Bytes this bot has produced on stdout (GuestOutput caps each stream at 64 MiB).
    pub out_total: usize,
    pub err_total: usize,
    pub closed: [bool; 3],
    /// split's slow path: FASTRUNNER_STATS, a fuel trace or NoFuel metering.
    pub slow: bool,
    pub api: crate::api::ApiState,
}

unsafe impl Send for BotCtx {}

impl BotCtx {
    pub fn new(eng: &'static Eng, i: BotInit, meter: *mut Meter, log: *mut TeamLog) -> BotCtx {
        BotCtx {
            eng,
            game: i.game,
            persp: crate::engine::persp(i.team, i.champion),
            team: i.team,
            champion: i.champion,
            ctype: i.ctype,
            meta: i.meta,
            board_bytes: i.board_bytes,
            field_bytes: i.field_bytes,
            mem: None,
            memdef: std::ptr::null(),
            meter,
            log,
            out_total: 0,
            err_total: 0,
            closed: [false; 3],
            slow: slow_calls(),
            api: crate::api::ApiState::new(&i.meta, i.board_bytes),
        }
    }
    pub fn set_memory(&mut self, m: Option<Memory>) {
        self.mem = m;
    }
    #[inline(always)]
    pub fn meter(&mut self) -> &mut Meter {
        unsafe { &mut *self.meter }
    }
    /// The guest's stdout (WASI fd_write). cambc flushes it to the team log on a tokio worker thread
    /// (GuestOutput::poll_flush, from wasmtime-wasi's AsyncWriteStream task), so the timeline reads there set that
    /// thread's last error and never the bot's: keep the bot's.
    pub fn stdout(&mut self, b: &[u8]) {
        let slot = crate::engine::err_slot();
        let saved = unsafe { *slot };
        let n = (64usize << 20).saturating_sub(self.out_total).min(b.len());
        self.out_total += n;
        let pos = crate::game::timeline_pos(self.eng, self.game).unwrap_or(0);
        unsafe { (*self.log).write(&b[..n], pos) };
        unsafe { *slot = saved };
    }
}

/// Guest memory and the context, borrowed together.
/// Host calls that touched guest memory (FASTRUNNER_STATS); one game at a time per process, so not atomic.
pub static mut CALLS: u64 = 0;

/// A host call's view of its bot: wasmtime's Caller or native mode's NCaller.
pub trait HostCx {
    fn ctx(&mut self) -> &mut BotCtx;
    /// Whether split must take its slow path (BotCtx::slow; native trampolines decide before the call).
    fn slow(&self) -> bool;
    /// The guest's linear memory (empty without one); valid for the host call.
    fn mem<'m>(&mut self) -> &'m mut [u8];
}

impl HostCx for Caller<'_, BotCtx> {
    #[inline(always)]
    fn ctx(&mut self) -> &mut BotCtx {
        self.data_mut()
    }
    #[inline(always)]
    fn slow(&self) -> bool {
        self.data().slow
    }
    #[inline(always)]
    fn mem<'m>(&mut self) -> &'m mut [u8] {
        let d = self.data().memdef;
        if d.is_null() {
            return &mut [];
        }
        // The memory's VMMemoryDefinition {base, current_length}, live as long as the instance.
        unsafe { std::slice::from_raw_parts_mut(*(d as *const *mut u8), *(d.add(8) as *const usize)) }
    }
}

/// FASTRUNNER_TRACE_FUEL=FILE: the fuel counter at every host call (and, in native mode built with
/// FASTRUNNER_TRACE_SITES=1, the calling site), written at the end of the game; for finding where two modes diverge.
pub static mut TRACE: Option<Vec<(i64, u64)>> = None;
#[no_mangle]
pub static mut fr_site: u64 = 0;

#[allow(static_mut_refs)]
pub fn trace_start() {
    if std::env::var_os("FASTRUNNER_TRACE_FUEL").is_some() {
        unsafe { TRACE = Some(Vec::with_capacity(1 << 20)) };
    }
}

#[allow(static_mut_refs)]
pub fn trace_dump() {
    let Some(path) = std::env::var_os("FASTRUNNER_TRACE_FUEL") else { return };
    let Some(v) = (unsafe { TRACE.take() }) else { return };
    let mut s = String::with_capacity(v.len() * 24);
    for (f, site) in v {
        s.push_str(&format!("{f} {:x}:{:x}\n", site >> 32, site as u32));
    }
    let _ = std::fs::write(path, s);
}

/// Whether host calls must count themselves (FASTRUNNER_STATS), trace fuel (armed by trace_start before a game's
/// bots exist) or tick NoFuel's virtual counter; fixed per bot, so the common case is one predictable branch.
#[allow(static_mut_refs)]
fn slow_calls() -> bool {
    static STATS: std::sync::OnceLock<bool> = std::sync::OnceLock::new();
    *STATS.get_or_init(|| std::env::var_os("FASTRUNNER_STATS").is_some())
        || unsafe { TRACE.is_some() }
        || crate::fuel::mode() == crate::fuel::Mode::NoFuel
}

#[inline(always)]
pub fn split<'a, C: HostCx>(c: &'a mut C) -> (&'a mut [u8], &'a mut BotCtx) {
    let mem = c.mem();
    let slow = c.slow();
    let x = c.ctx();
    if slow {
        split_slow(x);
    }
    (mem, x)
}

#[cold]
#[inline(never)]
fn split_slow(x: &mut BotCtx) {
    unsafe { CALLS += 1 };
    #[allow(static_mut_refs)]
    unsafe {
        if let Some(t) = TRACE.as_mut() {
            let m = &*x.meter;
            if !m.ctr.is_null() {
                t.push((*m.ctr, fr_site));
            }
        }
    }
    let m = unsafe { &mut *x.meter };
    if m.virt {
        m.tick();
    }
}

/// runner::api::primitives::guest_ptr: offset of `count` elements of `size` bytes at `ptr`, or None.
#[inline(always)]
pub fn gptr(mem: &[u8], ptr: i32, count: u64, size: u64, align: u64) -> Option<usize> {
    if ptr < 0 {
        return None;
    }
    let bytes = count.checked_mul(size)?;
    let p = ptr as u64;
    let end = p.checked_add(bytes)?;
    if p == 0 && bytes != 0 {
        return None;
    }
    if end > mem.len() as u64 || align == 0 {
        return None;
    }
    let addr = mem.as_ptr() as u64 + p;
    if addr % align != 0 {
        return None;
    }
    Some(p as usize)
}

struct YieldOnce(bool);
impl Future for YieldOnce {
    type Output = ();
    fn poll(mut self: Pin<&mut Self>, _cx: &mut Context<'_>) -> Poll<()> {
        if self.0 {
            Poll::Ready(())
        } else {
            self.0 = true;
            Poll::Pending
        }
    }
}

const ERRNO_BADF: i32 = 8;
const ERRNO_SPIPE: i32 = 70;
const ERRNO_FAULT: i32 = 21;

fn put_u64(mem: &mut [u8], p: i32, v: u64) -> bool {
    match gptr(mem, p, 1, 8, 8) {
        Some(o) => {
            mem[o..o + 8].copy_from_slice(&v.to_le_bytes());
            true
        }
        None => false,
    }
}

fn put_u32(mem: &mut [u8], p: i32, v: u32) -> bool {
    match gptr(mem, p, 1, 4, 4) {
        Some(o) => {
            mem[o..o + 4].copy_from_slice(&v.to_le_bytes());
            true
        }
        None => false,
    }
}

pub fn add_to_linker(l: &mut Linker<BotCtx>) -> Result<()> {
    let w = crate::runtime::werr;
    // ---- turn and fuel (wasm_runtime::Runtime::linker) ----
    l.func_wrap_async("env", "yield", |mut c: Caller<'_, BotCtx>, (): ()| {
        let ctx = c.data_mut();
        let m = ctx.meter();
        if m.paused {
            if m.debug_now() == m.saved_now {
                let s = m.saved_active;
                m.set_active(s);
            } else {
                debug_overrun(ctx);
            }
            ctx.meter().paused = false;
        }
        let m = ctx.meter();
        let a = m.active();
        m.capture(a);
        m.yielded = true;
        let i = m.interval;
        if m.virt {
            m.vctr = -(i as i64);
        } else {
            c.fuel_async_yield_interval(Some(i)).expect("fuel");
        }
        Box::new(YieldOnce(false))
    })
    .map_err(w)?;
    macro_rules! defm {
        ($m:expr, $name:expr, $f:expr) => {
            l.func_wrap($m, $name, $f).map_err(w)?;
        };
    }
    type Cx<'a> = Caller<'a, BotCtx>;
    include!("host_defs.rs");

    crate::api::add_to_linker(l)?;
    Ok(())
}

/// The same imports as native-mode trampolines (native.rs); `yield` is native.rs's own.
pub fn native_imports(r: &mut crate::native::Registry) {
    macro_rules! defm {
        ($m:expr, $name:expr, $f:expr) => {
            r.add($m, $name, $f);
        };
    }
    type Cx<'a> = crate::native::NCaller<'a>;
    include!("host_defs.rs");
}

/// wasm_runtime::debug_overrun: a debug block outlived its turn or its free budget. cambc writes its notice
/// ("debug_block exceeded its free fuel budget; the rest of it was charged") to the bot's stderr output, which goes
/// to the cli log and not the bundle, and makes no engine call, so the last error is untouched.
pub fn debug_overrun(_ctx: &mut BotCtx) {}

fn trace_write() -> bool {
    static C: std::sync::OnceLock<bool> = std::sync::OnceLock::new();
    *C.get_or_init(|| std::env::var_os("FASTRUNNER_TRACE_WRITE").is_some())
}
