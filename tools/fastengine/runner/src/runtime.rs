//! Bot instances: one wasmtime store per bot, `_start` running on a fiber across turns.
use crate::engine::Eng;
use crate::fuel::{Meter, STORE_FUEL};
use crate::host::{self, BotCtx, TeamLog};
use anyhow::{anyhow, Context, Result};
use std::future::Future;
use std::path::{Path, PathBuf};
use std::pin::Pin;
use std::sync::Arc;
use std::task::{Context as TaskCx, Poll, Waker};
use wasmtime::{Config, Engine, InstancePre, Linker, Module, OptLevel, Store};

/// cambc's engine settings (tools/fastengine/floor: compiled modules are byte-identical to cambc's).
pub fn cambc_config() -> Config {
    let mut c = Config::new();
    c.consume_fuel(crate::fuel::mode() == crate::fuel::Mode::Exact);
    c.cranelift_opt_level(OptLevel::Speed);
    c.relaxed_simd_deterministic(true);
    c.wasm_component_model(false);
    // cambc's wasm stack limit (wasmtime's default is 512 KiB): recursion traps at the same depth (probe stackprobe).
    let stack = std::env::var("FASTRUNNER_WASM_STACK").ok().and_then(|v| v.parse().ok()).unwrap_or(1 << 20);
    c.max_wasm_stack(stack);
    let mut cost = wasmtime::OperatorCost::new();
    cost.MemoryGrow = 0;
    cost.variable.memory_grow_per_page = 0;
    c.operator_cost(cost);
    if let Some(d) = std::env::var_os("FASTRUNNER_EMIT_CLIF") {
        c.emit_clif(std::path::Path::new(&d));
    }
    if tuned() {
        // Machine-code choices that leave the fuel instrumentation (an IR-level property) unchanged.
        unsafe {
            c.cranelift_flag_set("enable_table_access_spectre_mitigation", "false");
            c.cranelift_flag_set("enable_heap_access_spectre_mitigation", "false");
        }
    }
    c
}

/// FASTRUNNER_TUNE=1: codegen settings that differ from cambc's but keep fuel semantics.
pub fn tuned() -> bool {
    std::env::var("FASTRUNNER_TUNE").map_or(false, |v| v == "1")
}

/// Marks a guest that resigned (cambc's wasm_runtime::HostExit): its turn ends and it is removed.
pub const HOST_EXIT: &str = "wasm_runtime::HostExit";

pub fn werr(e: wasmtime::Error) -> anyhow::Error {
    anyhow!("{e:?}")
}

pub struct Runtime {
    pub engine: Engine,
    pub linker: Linker<BotCtx>,
    pub eng: &'static Eng,
    cache_dir: PathBuf,
    modules: std::collections::HashMap<(PathBuf, bool), Arc<Program>>,
}

#[derive(Clone)]
pub struct Program {
    experiment: Option<crate::experiment::TeamConfig>,
    requires_config: bool,
    unmetered: bool,
    unlimited: bool,
    quantum: u64,
    pub pre: InstancePre<BotCtx>,
    pub debug: bool,
    /// Native mode (FASTRUNNER_MODE=native): the bot translated to C and compiled (native.rs).
    pub native: Option<Arc<crate::native::NativeModule>>,
}

/// FASTRUNNER_MODE=native: bots run as translated native code, fuel still exact.
pub fn native_mode() -> bool {
    static N: std::sync::OnceLock<bool> = std::sync::OnceLock::new();
    *N.get_or_init(|| std::env::var("FASTRUNNER_MODE").map_or(false, |v| v == "native"))
}

impl Runtime {
    pub fn new(eng: &'static Eng) -> Result<Runtime> {
        crate::api::init(eng)?;
        let mut config = cambc_config();
        if std::env::var("FASTRUNNER_POOL").map_or(true, |v| v != "0") {
            // Reuse instance slots, linear memories and fiber stacks across games, keeping touched pages
            // resident (zeroed on reuse) instead of faulting them in for every bot of every game. Allocation
            // only; compiled code and fuel are unaffected.
            let mut pool = wasmtime::PoolingAllocationConfig::default();
            pool.total_memories(64)
                .total_core_instances(64)
                .total_tables(64)
                .total_stacks(64)
                // cambc's limit (probe-memory: growth stops at 256 MiB)
                .max_memory_size(256 << 20)
                .linear_memory_keep_resident(64 << 20)
                .table_keep_resident(1 << 20)
                .async_stack_keep_resident(1 << 20);
            config.allocation_strategy(wasmtime::InstanceAllocationStrategy::Pooling(pool));
        }
        let engine = Engine::new(&config).map_err(werr)?;
        let mut linker = Linker::new(&engine);
        host::add_to_linker(&mut linker)?;
        let cache_dir = std::env::var_os("XDG_CACHE_HOME")
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from(std::env::var("HOME").unwrap_or_default()).join(".cache"))
            .join("fastrunner")
            .join("modules");
        std::fs::create_dir_all(&cache_dir)?;
        Ok(Runtime { engine, linker, eng, cache_dir, modules: Default::default() })
    }

    /// A bot program from its wasm, compiled once (cached on disk by content hash).
    pub fn program(&mut self, wasm_path: &Path) -> Result<Arc<Program>> {
        self.program_mode(wasm_path, false)
    }

    pub fn configured_program(&mut self, wasm_path: &Path, config: Option<crate::experiment::TeamConfig>) -> Result<Arc<Program>> {
        let p = self.program_mode(wasm_path, config.is_some_and(|c| c.unmetered))?;
        anyhow::ensure!(!p.requires_config || config.is_some(), "runtime opponent requires explicit per-game configuration");
        anyhow::ensure!(config.is_none() || p.requires_config, "runtime configuration supplied to a bot without experiment_config import");
        if config.is_none() { return Ok(p); }
        let mut configured = (*p).clone();
        configured.experiment = config;
        Ok(Arc::new(configured))
    }

    pub fn program_mode(&mut self, wasm_path: &Path, unmetered: bool) -> Result<Arc<Program>> {
        anyhow::ensure!(!unmetered || native_mode(), "unmetered opponents require native mode");
        if let Some(p) = self.modules.get(&(wasm_path.to_path_buf(), unmetered)) {
            return Ok(p.clone());
        }
        let wasm = std::fs::read(wasm_path).with_context(|| format!("reading {}", wasm_path.display()))?;
        let hash = fnv128(&wasm);
        let tag = match crate::fuel::mode() {
            crate::fuel::Mode::Exact => "",
            crate::fuel::Mode::NoFuel => "-nofuel",
        }
        .to_string()
            + if tuned() { "-tuned" } else { "" };
        let file = self.cache_dir.join(format!("{hash:032x}{tag}.cwasm"));
        let module = match unsafe { Module::deserialize_file(&self.engine, &file) } {
            Ok(m) => m,
            Err(_) => {
                let bytes = self.engine.precompile_module(&wasm).map_err(werr)?;
                let tmp = self.cache_dir.join(format!(".{hash:032x}.{}.tmp", std::process::id()));
                std::fs::write(&tmp, &bytes)?;
                std::fs::rename(&tmp, &file)?;
                unsafe { Module::deserialize_file(&self.engine, &file) }.map_err(werr)?
            }
        };
        let requires_config = module.imports().any(|i| i.module() == "env" && i.name() == "experiment_config");
        anyhow::ensure!(!unmetered || requires_config, "unmetered mode is restricted to explicit experimental opponent bodies");
        let debug = module.imports().any(|i| i.module() == "env" && i.name() == "fuel_pause");
        let pre = match self.linker.instantiate_pre(&module) {
            Ok(p) => p,
            Err(_) => {
                // Imports this runner does not provide (GC-language variants etc.) trap if called.
                let mut l = self.linker.clone();
                l.define_unknown_imports_as_traps(&module).map_err(werr)?;
                l.instantiate_pre(&module).map_err(werr)?
            }
        };
        let native = if let Some(so) = std::env::var_os("FASTRUNNER_NATIVE_SO") {
            // native::build's training game: its instrumented library.
            Some(crate::native::load(Path::new(&so))?)
        } else if native_mode() {
            let so = crate::native::build(&wasm, hash, &self.engine, self.cache_dir.parent().unwrap_or(&self.cache_dir), unmetered)
                .with_context(|| format!("native build of {}", wasm_path.display()))?;
            Some(crate::native::load(&so)?)
        } else {
            None
        };
        let unlimited = std::env::var("FASTRUNNER_UNLIMITED_BOTS").unwrap_or_default().split(',')
            .filter(|name| !name.is_empty())
            .any(|name| wasm_path.ancestors().nth(3).and_then(Path::file_name).is_some_and(|bot| bot == name));
        if unlimited && native.is_none() {
            anyhow::bail!("FASTRUNNER_UNLIMITED_BOTS requires FASTRUNNER_MODE=native");
        }
        let mut quantum = crate::fuel::quantum();
        for entry in std::env::var("FASTRUNNER_BOT_FUEL").unwrap_or_default().split(',').filter(|s| !s.is_empty()) {
            let (name, value) = entry.split_once(':').context("FASTRUNNER_BOT_FUEL expects bot:quantum")?;
            let q: u64 = value.parse().context("invalid per-bot fuel quantum")?;
            anyhow::ensure!(q > 0 && q <= i64::MAX as u64, "invalid per-bot fuel quantum");
            if wasm_path.ancestors().nth(3).and_then(Path::file_name).is_some_and(|bot| bot == name) { quantum = q; }
        }
        let p = Arc::new(Program { pre, debug, native, unlimited, quantum, unmetered, requires_config, experiment: None });
        self.modules.insert((wasm_path.to_path_buf(), unmetered), p.clone());
        Ok(p)
    }
}

pub(crate) fn fnv128(b: &[u8]) -> u128 {
    // Two independent 64-bit FNV-1a lanes; a cache key, not security.
    let (mut a, mut c) = (0xcbf29ce484222325u64, 0x84222325cbf29ce4u64);
    for (i, &x) in b.iter().enumerate() {
        a = (a ^ x as u64).wrapping_mul(0x100000001b3);
        c = (c ^ (x as u64).wrapping_add(i as u64)).wrapping_mul(0x100000001b3);
    }
    (a as u128) << 64 | c as u128 ^ b.len() as u128
}

pub enum TurnEnd {
    /// The bot called yield (end_turn).
    Yield,
    /// The bot ran out of fuel and is suspended inside the turn.
    OutOfFuel,
    /// The guest returned from _start.
    Exited,
    /// The guest trapped or errored.
    Error(String),
    /// The guest resigned (HostExit): removed without ending the turn.
    Removed,
}

type GuestFuture = Pin<Box<dyn Future<Output = Result<(), wasmtime::Error>> + Send>>;

pub struct BotSnap {
    guest: crate::native::GuestSnap,
    meter: Meter,
}

impl BotSnap {
    pub fn bytes(&self) -> usize {
        self.guest.bytes()
    }
}

pub struct Bot {
    fut: Option<GuestFuture>,
    native: Option<crate::native::NativeBot>,
    pub meter: Box<Meter>,
    pub team: u32,
    pub champion: u32,
    prog: Arc<Program>,
    init: host::BotInit,
    log: *mut TeamLog,
}

impl Bot {
    pub fn spawn(rt: &Runtime, prog: &Arc<Program>, init: host::BotInit, log: *mut TeamLog) -> Result<Bot> {
        let mut meter = Box::new(Meter::new(prog.debug));
        let pgo = std::env::var_os("FASTRUNNER_NATIVE_SO").is_some();
        anyhow::ensure!(!prog.requires_config || prog.experiment.is_some() || pgo, "missing runtime experiment configuration");
        meter.unmetered = prog.unmetered || (pgo && std::env::var("FASTRUNNER_PGO_UNMETERED").as_deref() == Ok("1"));
        meter.unlimited = prog.unlimited || meter.unmetered;
        // PGO uses one fixed configuration so the compiled cache never depends on the experiment seed.
        meter.experiment = prog.experiment.map(|c| [c.seed, c.salt]).unwrap_or([1310001, 1]);
        meter.interval = prog.quantum;
        meter.vctr = -(prog.quantum as i64);
        if let Some(m) = &prog.native {
            let nb = crate::native::NativeBot::spawn(m, rt.eng, init, &mut *meter, log)?;
            return Ok(Bot { fut: None, native: Some(nb), meter, team: init.team, champion: init.champion, prog: prog.clone(), init, log });
        }
        let fut = Self::guest(rt, prog, init, &mut *meter, log);
        Ok(Bot { fut: Some(fut), native: None, meter, team: init.team, champion: init.champion, prog: prog.clone(), init, log })
    }

    /// A fresh instance of the bot's program, run as a future that ends when `_start` returns or traps.
    fn guest(rt: &Runtime, prog: &Arc<Program>, init: host::BotInit, mp: *mut Meter, log: *mut TeamLog) -> GuestFuture {
        let ctx = BotCtx::new(rt.eng, init, mp, log);
        let mut store = Store::new(&rt.engine, ctx);
        let pre = prog.pre.clone();
        Box::pin(async move {
            let inst = pre.instantiate_async(&mut store).await?;
            let mem = inst.get_memory(&mut store, "memory");
            let def = mem.map(|m| m.cambc_definition(&mut store)).unwrap_or(std::ptr::null());
            store.data_mut().set_memory(mem);
            store.data_mut().memdef = def;
            let m = store.data().meter;
            if crate::fuel::mode() == crate::fuel::Mode::Exact {
                store.set_fuel(STORE_FUEL)?;
                store.fuel_async_yield_interval(Some(unsafe { (*m).interval }))?;
                unsafe {
                    (*m).ctr = store.cambc_fuel_counter();
                    store.cambc_set_fuel_cell(&mut (*m).cell);
                }
            } else {
                unsafe {
                    (*m).virt = true;
                    (*m).ctr = &mut (*m).vctr;
                }
            }
            let start = inst.get_typed_func::<(), ()>(&mut store, "_start")?;
            start.call_async(&mut store, ()).await
        })
    }

    /// cambc's default restart policy: a guest that exits or traps gets a fresh instance, keeping its
    /// fuel meter (wasm_runtime::Runtime::crash).
    pub fn restart(&mut self, rt: &Runtime) {
        let mp: *mut Meter = &mut *self.meter;
        self.meter.yielded = false;
        if let Some(m) = &self.prog.native {
            // a failed instantiation leaves the bot without a guest (its turns are empty)
            self.native = crate::native::NativeBot::spawn(m, rt.eng, self.init, mp, self.log).ok();
            return;
        }
        self.fut = Some(Self::guest(rt, &self.prog, self.init, mp, self.log));
    }

    pub fn alive(&self) -> bool {
        self.fut.is_some() || self.native.as_ref().map_or(false, |n| n.alive())
    }

    /// The bot's whole state between turns (native mode only), for `restore` on this same bot.
    pub fn snapshot(&mut self) -> Option<BotSnap> {
        Some(BotSnap { guest: self.native.as_mut()?.snapshot()?, meter: (*self.meter).clone() })
    }

    /// Whether `restore(s)` would succeed (nothing is changed).
    pub fn can_restore(&self, s: &BotSnap) -> bool {
        self.native.as_ref().is_some_and(|n| n.can_restore(&s.guest))
    }

    /// Back to `s`, taken from this bot (false if it is not this bot's, or the bot was restarted since).
    pub fn restore(&mut self, s: &BotSnap) -> bool {
        if !self.native.as_mut().is_some_and(|n| n.restore(&s.guest)) {
            return false;
        }
        *self.meter = s.meter.clone();
        true
    }

    /// The bot's linear memory between turns (native mode only).
    pub fn memory(&mut self) -> Option<&mut [u8]> {
        self.native.as_mut()?.memory()
    }

    /// One turn (run_turn_scaled): returns how it ended; fuel used is in `self.meter.used`.
    pub fn run_turn(&mut self, scale: u64) -> TurnEnd {
        self.meter.begin_turn(scale);
        if let Some(n) = self.native.as_mut() {
            return n.run_turn(&mut self.meter);
        }
        let Some(fut) = self.fut.as_mut() else {
            self.meter.used = 0;
            return TurnEnd::Yield;
        };
        let waker = Waker::noop();
        let mut cx = TaskCx::from_waker(waker);
        loop {
            match fut.as_mut().poll(&mut cx) {
                Poll::Pending => {
                    let m = &mut *self.meter;
                    if m.yielded {
                        return TurnEnd::Yield;
                    }
                    let a = std::mem::take(&mut m.cell[0]);
                    if a == 0 {
                        continue;
                    }
                    m.chunks = m.chunks.saturating_add(a);
                    if m.chunks >= m.budget {
                        m.cell[1] = 0;
                        m.used = m.interval.saturating_mul(m.budget);
                        return TurnEnd::OutOfFuel;
                    }
                }
                Poll::Ready(r) => {
                    // An exit or trap mid-turn records the fuel used up to that point (the fuel
                    // counter lives in the store, so read it before dropping the instance).
                    if !self.meter.ctr.is_null() {
                        let a = self.meter.active();
                        self.meter.capture(a);
                        self.meter.ctr = std::ptr::null_mut();
                    }
                    self.fut = None;
                    // Fuel used by a crashed turn is what the meter last recorded.
                    return match r {
                        Ok(()) => TurnEnd::Exited,
                        Err(e) => {
                            let msg = format!("{e:?}");
                            if msg.contains(HOST_EXIT) {
                                TurnEnd::Removed
                            } else {
                                TurnEnd::Error(msg)
                            }
                        }
                    };
                }
            }
        }
    }
}
