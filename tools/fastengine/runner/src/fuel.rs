//! cambc's per-bot FuelMeter, reproduced from wasm_runtime::{charge_fuel, FuelMeter, run_turn_scaled}
//! and the yield / fuel_* imports of cambc 4.0.0.
//!
//! Fuel is metered by wasmtime in chunks of `interval` (fuel_async_yield_interval): running a chunk
//! dry suspends the guest, the vendored out_of_gas adds 1 + overshoot / interval to `cell[0]` and
//! carries overshoot % interval into the next chunk (`cell[1]`, charged on resume). A turn has
//! `budget` chunks; the runner moves `cell[0]` into `chunks` after each suspension and ends the turn
//! out of fuel once `chunks >= budget`.

/// Fuel per chunk (cambc's fuel quantum) and chunks per turn (quanta_per_turn).
pub const DEFAULT_QUANTUM: u64 = 100_000;
pub const QUANTA_PER_TURN: u64 = 1;

static QUANTUM: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(DEFAULT_QUANTUM);

/// Fuel per chunk = per turn (`--fuel-quantum` / `--fuel`, default 100000).
pub fn quantum() -> u64 {
    QUANTUM.load(std::sync::atomic::Ordering::Relaxed)
}

pub fn set_quantum(q: u64) {
    QUANTUM.store(q.max(1), std::sync::atomic::Ordering::Relaxed);
}
/// Fuel given to a fresh store; never runs out in a game.
pub const STORE_FUEL: u64 = 100_000_000_000;

/// How fuel is metered (FASTRUNNER_MODE).
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Mode {
    /// wasmtime fuel metering with cambc's accounting: byte-identical games.
    Exact,
    /// No fuel metering in the bots' code: each host call stands for `per_call` fuel of guest work, plus
    /// the host prices. fuel_remaining reports that estimate; a turn past its budget reports 0 fuel left
    /// (the bot is not suspended mid-turn).
    NoFuel,
}

pub fn mode() -> Mode {
    static M: std::sync::OnceLock<Mode> = std::sync::OnceLock::new();
    *M.get_or_init(|| match std::env::var("FASTRUNNER_MODE").as_deref() {
        Ok("nofuel") | Ok("approx") | Ok("off") => Mode::NoFuel,
        _ => Mode::Exact,
    })
}

/// Estimated guest fuel per host call in NoFuel mode (FASTRUNNER_FUEL_PER_CALL; default from demeter
/// games: (total - host-charged fuel) / host calls).
pub fn per_call() -> u64 {
    static K: std::sync::OnceLock<u64> = std::sync::OnceLock::new();
    *K.get_or_init(|| std::env::var("FASTRUNNER_FUEL_PER_CALL").ok().and_then(|v| v.parse().ok()).unwrap_or(134))
}

pub struct Meter {
    /// [chunks consumed, overshoot pending] written by the vendored wasmtime's out_of_gas.
    pub cell: [u64; 2],
    /// The store's fuel counter: -(fuel left in the active chunk), positive when overrun.
    pub ctr: *mut i64,
    pub interval: u64,
    pub quanta: u64,
    /// Chunks this turn.
    pub budget: u64,
    pub mult: f64,
    /// Chunks consumed this turn.
    pub chunks: u64,
    /// Fuel used by the turn, set when it ends (yield or out of fuel).
    pub used: u64,
    /// Turns started (debug_now's first half).
    pub turn: u64,
    pub yielded: bool,
    /// Debug build: fuel_pause / fuel_resume / fuel_adjust are live.
    pub debug: bool,
    pub depth: u32,
    pub paused: bool,
    pub saved_active: u64,
    pub saved_now: (u64, u64),
    /// NoFuel mode: the virtual fuel counter `ctr` points at, and the estimate per host call.
    pub vctr: i64,
    pub virt: bool,
    pub per_call: u64,
    pub exhausted: bool,
}

unsafe impl Send for Meter {}

impl Meter {
    pub fn new(debug: bool) -> Meter {
        Meter {
            cell: [0, 0],
            ctr: std::ptr::null_mut(),
            interval: quantum(),
            quanta: QUANTA_PER_TURN,
            budget: 0,
            mult: 1.0,
            chunks: 0,
            used: 0,
            turn: 0,
            yielded: false,
            debug,
            depth: 0,
            paused: false,
            saved_active: 0,
            saved_now: (0, 0),
            vctr: -(quantum() as i64),
            virt: false,
            per_call: per_call(),
            exhausted: false,
        }
    }

    #[inline(always)]
    pub fn active(&self) -> u64 {
        let v = unsafe { *self.ctr };
        if v < 0 {
            v.unsigned_abs()
        } else {
            0
        }
    }

    #[inline(always)]
    pub fn set_active(&mut self, fuel: u64) {
        unsafe { *self.ctr = -(fuel.min(i64::MAX as u64) as i64) };
    }

    /// wasm_runtime::charge_fuel: a host price, in the store's active chunk and then whole chunks.
    #[inline(always)]
    pub fn charge(&mut self, amount: u64) {
        // With the multiplier 1.0 the f64 round trip is exact below 2^53 (out of line, or LLVM computes both arms).
        let price = if self.mult == 1.0 && amount < 1 << 53 { amount } else { self.scaled(amount) };
        let fuel = self.active();
        if price < fuel {
            self.set_active(fuel - price);
            return;
        }
        self.charge_chunks(price, fuel);
    }

    #[cold]
    #[inline(never)]
    fn scaled(&self, amount: u64) -> u64 {
        (amount as f64 * self.mult) as u64
    }

    #[cold]
    #[inline(never)]
    fn charge_chunks(&mut self, price: u64, fuel: u64) {
        let excess = price - fuel;
        let i = self.interval;
        let count = self.chunks.saturating_add(excess / i + 1);
        if count < self.budget {
            self.chunks = count;
            self.set_active(i - excess % i);
        } else {
            self.chunks = self.budget.saturating_sub(1);
            self.set_active(0);
        }
    }

    /// FuelMeter::capture: fuel used so far this turn.
    pub fn capture(&mut self, active: u64) {
        let i = self.interval;
        let whole = self.chunks.saturating_mul(i);
        let part = i.saturating_sub(active);
        let cap = i.saturating_mul(self.budget);
        self.used = whole.saturating_add(part).min(cap);
    }

    /// FuelMeter::debug_now.
    pub fn debug_now(&self) -> (u64, u64) {
        (self.turn, self.chunks.saturating_add(self.cell[0]))
    }

    /// FuelMeter::reported_active: inside a debug_block, the fuel saved at its start.
    pub fn reported_active(&self, active: u64) -> u64 {
        if self.paused && self.debug_now() == self.saved_now {
            self.saved_active
        } else {
            active
        }
    }

    /// The fuel_remaining import.
    #[inline]
    pub fn remaining(&self) -> u64 {
        if self.exhausted {
            return 0;
        }
        let i = self.interval;
        let r = self.reported_active(self.active());
        let total = i.saturating_mul(self.budget);
        let spent = self.chunks.checked_add(1).unwrap_or(u64::MAX).saturating_mul(i);
        let rest = total.saturating_sub(spent);
        r.min(i).saturating_add(rest)
    }

    /// NoFuel: guest work since the last host call, estimated; crossing chunk boundaries like out_of_gas.
    #[inline(always)]
    pub fn tick(&mut self) {
        self.vctr += self.per_call as i64;
        if self.vctr >= 0 {
            self.tick_slow();
        }
    }

    #[cold]
    fn tick_slow(&mut self) {
        let over = self.vctr as u64;
        let i = self.interval;
        self.chunks = self.chunks.saturating_add(over / i + 1);
        self.vctr = -((i - over % i) as i64);
        if self.chunks >= self.budget {
            self.exhausted = true;
            self.chunks = self.budget;
            self.vctr = 0;
        }
    }

    /// Start of a turn (run_turn_scaled).
    pub fn begin_turn(&mut self, scale: u64) {
        let scale = scale.max(1);
        self.budget = scale.saturating_mul(self.quanta);
        self.chunks = 0;
        self.cell = [0, 0];
        self.used = 0;
        self.turn += 1;
        self.yielded = false;
        self.exhausted = false;
    }
}
