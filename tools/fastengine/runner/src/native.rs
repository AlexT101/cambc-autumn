//! Native mode, part 2: runs bots translated by aot.rs and compiled by clang, with cambc's fuel accounting.
//!
//! A guest is an instance (aot_rt.h's `Inst`: fuel counter, memory, globals) plus a fiber: `_start` runs on its
//! own stack; yield and running out of fuel switch back to the runner, which resumes it next turn. Linear memory
//! is an 8 GiB reservation (any i32 address + offset lands inside it) with only the wasm-visible pages
//! accessible; a fault inside it, or on the fiber stack's guard page, becomes a trap.
use crate::fuel::{Meter, STORE_FUEL};
use crate::host::{BotCtx, BotInit, HostCx, TeamLog};
use crate::runtime::{TurnEnd, HOST_EXIT};
use anyhow::{anyhow, bail, Context, Result};
use std::collections::HashMap;
use std::ffi::{c_void, CStr, CString};
use std::path::{Path, PathBuf};
use std::sync::Arc;

const PAGE: u64 = 65536;
/// i32 address + u32-ish offset + a v128 access.
const RESERVE: usize = (8u64 << 30) as usize + 2 * PAGE as usize;
const STACK: usize = 8 << 20;
const GUARD: usize = 64 << 10;

/// aot_rt.h's Inst header; the globals follow.
#[repr(C)]
pub struct Inst {
    pub fuel: i64,
    pub mem: *mut u8,
    pub size: u64,
    pub exn: u64,
    pub rt: *mut Guest,
    pad: [u64; 3],
}

#[repr(C)]
struct FrImport {
    module: *const i8,
    name: *const i8,
    sig: *const i8,
}

#[repr(C)]
struct FrData {
    offset: u32,
    len: u32,
    bytes: *const u8,
}

#[repr(C)]
struct FrModule {
    version: u32,
    n_imports: u32,
    imports: *const FrImport,
    slots: *mut *const c_void,
    n_globals: u32,
    ginit: *const u64,
    mem_pages: u64,
    mem_max: u64,
    n_data: u32,
    data: *const FrData,
    start: unsafe extern "C" fn(*mut Inst),
    n_tags: u32,
}

pub struct NativeModule {
    desc: &'static FrModule,
    _lib: *mut c_void,
}
unsafe impl Send for NativeModule {}
unsafe impl Sync for NativeModule {}

// ---------------------------------------------------------------------------------------------------------
// Import trampolines

/// A host call's caller in native mode: the guest's instance and context.
pub struct NCaller<'a> {
    i: *mut Inst,
    g: &'a mut Guest,
    /// A constant in each trampoline copy (tramp / tramp_slow), so the fast copy has no slow path at all.
    slow: bool,
}

impl<'a> NCaller<'a> {
    #[inline(always)]
    pub fn data(&self) -> &BotCtx {
        &self.g.ctx
    }
    #[inline(always)]
    pub fn data_mut(&mut self) -> &mut BotCtx {
        &mut self.g.ctx
    }
}

impl HostCx for NCaller<'_> {
    #[inline(always)]
    fn ctx(&mut self) -> &mut BotCtx {
        &mut self.g.ctx
    }
    #[inline(always)]
    fn slow(&self) -> bool {
        self.slow
    }
    /// Straight from the instance (what ctx.memdef points at), saving two dependent loads.
    #[inline(always)]
    fn mem<'m>(&mut self) -> &'m mut [u8] {
        unsafe { std::slice::from_raw_parts_mut((*self.i).mem, (*self.i).size as usize) }
    }
}

#[inline(always)]
unsafe fn caller<'a>(i: *mut Inst, slow: bool) -> NCaller<'a> {
    NCaller { i, g: &mut *(*i).rt, slow }
}

pub trait NArg: Copy {
    const CH: char;
}
impl NArg for i32 {
    const CH: char = 'i';
}
impl NArg for i64 {
    const CH: char = 'j';
}
impl NArg for f32 {
    const CH: char = 'f';
}
impl NArg for f64 {
    const CH: char = 'd';
}

/// Host results as C values; an error ends the guest.
pub trait NRet {
    type C;
    const SIG: &'static str;
    fn conv(self, i: *mut Inst) -> Self::C;
}
macro_rules! nret {
    ($t:ty, $s:expr) => {
        impl NRet for $t {
            type C = $t;
            const SIG: &'static str = $s;
            #[inline(always)]
            fn conv(self, _i: *mut Inst) -> $t {
                self
            }
        }
    };
}
nret!(i32, "i");
nret!(i64, "j");
nret!(f32, "f");
nret!(f64, "d");
nret!((), "");
impl NRet for Result<i32, wasmtime::Error> {
    type C = i32;
    const SIG: &'static str = "i";
    fn conv(self, i: *mut Inst) -> i32 {
        match self {
            Ok(v) => v,
            Err(e) => unsafe { fail(i, format!("{e:?}")) },
        }
    }
}
impl NRet for Result<(), wasmtime::Error> {
    type C = ();
    const SIG: &'static str = "";
    fn conv(self, i: *mut Inst) {
        if let Err(e) = self {
            unsafe { fail(i, format!("{e:?}")) }
        }
    }
}

/// Conjures a capture-free closure (a zero-sized type) inside its trampoline.
#[inline(always)]
unsafe fn zst<F>() -> F {
    debug_assert_eq!(std::mem::size_of::<F>(), 0);
    std::mem::MaybeUninit::<F>::uninit().assume_init()
}

pub trait NativeFn<A> {
    fn entry(self) -> (*const c_void, String);
}

macro_rules! native_fn {
    ($($a:ident $v:ident),*) => {
        impl<F, R, $($a: NArg),*> NativeFn<($($a,)*)> for (F, std::marker::PhantomData<R>)
        where
            F: for<'x> Fn(NCaller<'x>, $($a),*) -> R + 'static,
            R: NRet,
        {
            fn entry(self) -> (*const c_void, String) {
                assert_eq!(std::mem::size_of::<F>(), 0, "native imports must not capture");
                // BotCtx::slow (diagnostics, NoFuel) is fixed per bot: a slow bot's calls go to a second copy, a
                // tail call, so the fast copy keeps no registers across a call it never makes.
                unsafe extern "C" fn tramp<F, R, $($a: NArg),*>(i: *mut Inst, $($v: $a),*) -> R::C
                where
                    F: for<'x> Fn(NCaller<'x>, $($a),*) -> R + 'static,
                    R: NRet,
                {
                    if (*(*i).rt).ctx.slow {
                        return tramp_slow::<F, R, $($a),*>(i, $($v),*);
                    }
                    let f: F = zst::<F>();
                    f(caller(i, false), $($v),*).conv(i)
                }
                #[cold]
                #[inline(never)]
                unsafe extern "C" fn tramp_slow<F, R, $($a: NArg),*>(i: *mut Inst, $($v: $a),*) -> R::C
                where
                    F: for<'x> Fn(NCaller<'x>, $($a),*) -> R + 'static,
                    R: NRet,
                {
                    let f: F = zst::<F>();
                    f(caller(i, true), $($v),*).conv(i)
                }
                let mut sig = String::from(R::SIG);
                sig.push(':');
                $(sig.push($a::CH);)*
                (tramp::<F, R, $($a),*> as *const c_void, sig)
            }
        }
    };
}
native_fn!();
native_fn!(A1 a1);
native_fn!(A1 a1, A2 a2);
native_fn!(A1 a1, A2 a2, A3 a3);
native_fn!(A1 a1, A2 a2, A3 a3, A4 a4);
native_fn!(A1 a1, A2 a2, A3 a3, A4 a4, A5 a5);
native_fn!(A1 a1, A2 a2, A3 a3, A4 a4, A5 a5, A6 a6);
native_fn!(A1 a1, A2 a2, A3 a3, A4 a4, A5 a5, A6 a6, A7 a7);
native_fn!(A1 a1, A2 a2, A3 a3, A4 a4, A5 a5, A6 a6, A7 a7, A8 a8);
native_fn!(A1 a1, A2 a2, A3 a3, A4 a4, A5 a5, A6 a6, A7 a7, A8 a8, A9 a9);

/// Native imports by (module, name): entry point and signature ("results:params").
#[derive(Default)]
pub struct Registry {
    map: HashMap<(String, String), (usize, String)>,
}

impl Registry {
    pub fn add<F, R, A>(&mut self, module: &str, name: &str, f: F)
    where
        (F, std::marker::PhantomData<R>): NativeFn<A>,
        F: NFnRet<A, R>,
    {
        let (p, s) = (f, std::marker::PhantomData::<R>).entry();
        self.map.insert((module.to_string(), name.to_string()), (p as usize, s));
    }
}

/// Ties a closure to its result type so `Registry::add` can infer `R`.
pub trait NFnRet<A, R> {}
macro_rules! nfnret {
    ($($a:ident),*) => {
        impl<F, R, $($a),*> NFnRet<($($a,)*), R> for F where F: for<'x> Fn(NCaller<'x>, $($a),*) -> R {}
    };
}
nfnret!();
nfnret!(A1);
nfnret!(A1, A2);
nfnret!(A1, A2, A3);
nfnret!(A1, A2, A3, A4);
nfnret!(A1, A2, A3, A4, A5);
nfnret!(A1, A2, A3, A4, A5, A6);
nfnret!(A1, A2, A3, A4, A5, A6, A7);
nfnret!(A1, A2, A3, A4, A5, A6, A7, A8);
nfnret!(A1, A2, A3, A4, A5, A6, A7, A8, A9);

fn registry() -> &'static Registry {
    static R: std::sync::OnceLock<Registry> = std::sync::OnceLock::new();
    R.get_or_init(|| {
        let mut r = Registry::default();
        crate::host::native_imports(&mut r);
        crate::api::native_imports(&mut r);
        r.map.insert(("env".into(), "yield".into()), (native_yield as usize, ":".into()));
        r
    })
}

unsafe extern "C" fn unknown_import(i: *mut Inst) {
    fail(i, "call to an import this runner does not provide".into());
}

// ---------------------------------------------------------------------------------------------------------
// Building and loading

fn cc() -> String {
    std::env::var("FASTRUNNER_CC").unwrap_or_else(|_| "clang".into())
}

fn cflags() -> Vec<String> {
    let opt = std::env::var("FASTRUNNER_COPT").unwrap_or_else(|_| "-O2".into());
    let mut v: Vec<String> = vec![
        opt,
        "-fPIC".into(),
        "-ffp-contract=off".into(),
        "-fno-math-errno".into(),
        "-fno-strict-aliasing".into(),
        "-fwrapv".into(),
        "-fvisibility=hidden".into(),
        "-march=x86-64-v3".into(),
        "-w".into(),
    ];
    if let Ok(extra) = std::env::var("FASTRUNNER_CFLAGS") {
        v.extend(extra.split_whitespace().map(String::from));
    }
    v
}

/// FASTRUNNER_PGO (default on; 0 = off): compile bots with clang profile-guided optimisation, trained by one
/// self-play game of an instrumented build (pgo_profile). Generated code keeps the C's semantics, so games and fuel
/// are unchanged; the bots' code runs ~30% faster.
pub fn pgo() -> bool {
    std::env::var("FASTRUNNER_PGO").map_or(true, |v| v != "0") && !crate::aot::trace_sites()
}

/// The training game's map (a ladder map, built in so the profile depends only on the bot).
pub const PGO_MAP: &[u8] = include_bytes!("../../../../maps/00ambush.map26a");

/// Compiles the translation units in parallel with `flags` and links them into `out`.
fn compile(srcs: &[PathBuf], flags: &[String], tag: &str, out: &Path) -> Result<()> {
    let jobs = std::thread::available_parallelism().map_or(4, |n| n.get()).min(16);
    let next = std::sync::atomic::AtomicUsize::new(0);
    let errors = std::sync::Mutex::new(Vec::<String>::new());
    let obj = |p: &PathBuf| p.with_extension(format!("{tag}o"));
    std::thread::scope(|s| {
        for _ in 0..jobs {
            s.spawn(|| loop {
                let k = next.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                if k >= srcs.len() {
                    break;
                }
                let r = std::process::Command::new(cc())
                    .args(flags)
                    .arg("-c")
                    .arg(&srcs[k])
                    .arg("-o")
                    .arg(obj(&srcs[k]))
                    .env_remove("LD_PRELOAD")
                    .output();
                match r {
                    Ok(o) if o.status.success() => {}
                    Ok(o) => errors.lock().unwrap().push(format!("{}: {}", srcs[k].display(), String::from_utf8_lossy(&o.stderr))),
                    Err(e) => errors.lock().unwrap().push(format!("{}: {e}", cc())),
                }
            });
        }
    });
    let errs = errors.into_inner().unwrap();
    if !errs.is_empty() {
        bail!("compiling the translated bot failed:\n{}", errs.join("\n").chars().take(4000).collect::<String>());
    }
    // The profile runtime is linked in only when the flags ask for it.
    let link_flags: Vec<&String> = flags.iter().filter(|f| f.starts_with("-fprofile-instr-generate")).collect();
    let o = std::process::Command::new(cc())
        .arg("-shared")
        .args(link_flags)
        .arg("-o")
        .arg(out)
        .args(srcs.iter().map(obj))
        .env_remove("LD_PRELOAD")
        .output()
        .context("linking the translated bot")?;
    if !o.status.success() {
        bail!("linking the translated bot failed: {}", String::from_utf8_lossy(&o.stderr));
    }
    Ok(())
}

/// An instrumented build (-O0: frontend profiles do not depend on the optimisation level) plays one self-play game
/// on PGO_MAP in a child process (`__pgotrain`), whose profile is merged for -fprofile-instr-use.
fn pgo_profile(work: &Path, srcs: &[PathBuf], wasm: &[u8]) -> Result<PathBuf> {
    let mut flags: Vec<String> = cflags().into_iter().map(|f| if f.starts_with("-O") { "-O0".into() } else { f }).collect();
    flags.push("-fprofile-instr-generate".into());
    let inst = work.join("inst.so");
    compile(srcs, &flags, "inst.", &inst)?;
    let bot = work.join("bot.wasm");
    std::fs::write(&bot, wasm)?;
    let out = std::process::Command::new(std::env::current_exe()?)
        .arg("__pgotrain")
        .arg(&bot)
        .env("FASTRUNNER_NATIVE_SO", &inst)
        .env("LLVM_PROFILE_FILE", work.join("train-%p.profraw"))
        .env_remove("FASTRUNNER_STATS")
        .env_remove("FASTRUNNER_TRACE_FUEL")
        .output()
        .context("running the training game")?;
    if !out.status.success() {
        bail!("the training game failed: {}{}", String::from_utf8_lossy(&out.stdout), String::from_utf8_lossy(&out.stderr));
    }
    let raws: Vec<PathBuf> = std::fs::read_dir(work)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|x| x == "profraw"))
        .collect();
    if raws.is_empty() {
        bail!("the training game wrote no profile");
    }
    let tool = std::process::Command::new(cc()).arg("-print-prog-name=llvm-profdata").env_remove("LD_PRELOAD").output()?;
    let tool = String::from_utf8_lossy(&tool.stdout).trim().to_string();
    let prof = work.join("bot.profdata");
    let o = std::process::Command::new(if tool.is_empty() { "llvm-profdata".into() } else { tool })
        .arg("merge")
        .arg("-o")
        .arg(&prof)
        .args(&raws)
        .env_remove("LD_PRELOAD")
        .output()
        .context("running llvm-profdata")?;
    if !o.status.success() {
        bail!("llvm-profdata merge failed: {}", String::from_utf8_lossy(&o.stderr));
    }
    Ok(prof)
}

/// The native library for a wasm module: translated, compiled in parallel and cached by content and flags.
pub fn build(wasm: &[u8], hash: u128, engine: &wasmtime::Engine, cache: &Path) -> Result<PathBuf> {
    let pgo = pgo();
    let key = {
        let mut k = format!("{hash:032x}");
        let flags = cflags().join(" ") + &cc() + include_str!("aot_rt.h") + env!("CARGO_PKG_VERSION") + if crate::aot::trace_sites() { "trace" } else { "" }
            + &std::env::var("FASTRUNNER_UNITS").unwrap_or_default()
            + if pgo { "pgo1" } else { "" };
        let fh = crate::runtime::fnv128(flags.as_bytes()) ^ crate::runtime::fnv128(include_bytes!("aot.rs"));
        k.push_str(&format!("-{:08x}", fh as u32));
        k
    };
    let dir = cache.join("native");
    std::fs::create_dir_all(&dir)?;
    let so = dir.join(format!("{key}.so"));
    if so.exists() {
        return Ok(so);
    }
    // One builder per key: others (concurrent batches, or workers of a batch that outlived a runner rebuild) wait
    // for its library instead of each compiling the bot on 16 threads.
    let lock = std::fs::OpenOptions::new().read(true).append(true).create(true).open(dir.join(format!(".{key}.lock")))?;
    unsafe { libc::flock(std::os::fd::AsRawFd::as_raw_fd(&lock), libc::LOCK_EX) };
    if so.exists() {
        return Ok(so);
    }
    let t0 = std::time::Instant::now();
    // Ask Cranelift (the vendored hook) how it placed bulk-memory fuel, by compiling the module once.
    wasmtime_internal_cranelift::cambc_hook::start();
    let compiled = engine.precompile_module(wasm);
    let log = wasmtime_internal_cranelift::cambc_hook::take();
    compiled.map_err(crate::runtime::werr)?;
    let mut bulk: crate::aot::BulkLog = HashMap::new();
    for (loc, kind, cost, units) in log {
        bulk.insert(loc, (kind, cost, units));
    }
    for off in crate::aot::bulk_offsets(wasm)? {
        if !bulk.contains_key(&off) {
            bail!("no Cranelift record for the bulk operation at {off}");
        }
    }
    let jobs = std::thread::available_parallelism().map_or(4, |n| n.get()).min(16);
    let units = std::env::var("FASTRUNNER_UNITS").ok().and_then(|v| v.parse().ok()).unwrap_or(jobs * 2);
    let m = crate::aot::translate(wasm, &bulk, units)?;
    let work = dir.join(format!(".{key}.{}", std::process::id()));
    std::fs::create_dir_all(&work)?;
    std::fs::write(work.join("mod.h"), &m.header)?;
    let mut srcs = vec![];
    for (k, u) in m.units.iter().enumerate() {
        let p = work.join(format!("u{k}.c"));
        std::fs::write(&p, u)?;
        srcs.push(p);
    }
    let t1 = std::time::Instant::now();
    let mut flags = cflags();
    if pgo {
        match pgo_profile(&work, &srcs, wasm) {
            Ok(prof) => flags.push(format!("-fprofile-instr-use={}", prof.display())),
            Err(e) => eprintln!("fastrunner: profile-guided build of {key} failed, compiling without a profile: {e:#}"),
        }
    }
    let t2 = std::time::Instant::now();
    let tmp = work.join("lib.so");
    compile(&srcs, &flags, "", &tmp)?;
    std::fs::rename(&tmp, &so)?;
    if std::env::var_os("FASTRUNNER_KEEP_C").is_none() {
        let _ = std::fs::remove_dir_all(&work);
    }
    if std::env::var_os("FASTRUNNER_STATS").is_some() {
        eprintln!(
            "native: translated in {:.1}s, profiled in {:.1}s, compiled in {:.1}s ({} units)",
            (t1 - t0).as_secs_f64(),
            (t2 - t1).as_secs_f64(),
            t2.elapsed().as_secs_f64(),
            srcs.len()
        );
    }
    Ok(so)
}

pub fn load(so: &Path) -> Result<Arc<NativeModule>> {
    let c = CString::new(so.as_os_str().as_encoded_bytes())?;
    let lib = unsafe { libc::dlopen(c.as_ptr(), libc::RTLD_NOW | libc::RTLD_LOCAL) };
    if lib.is_null() {
        let e = unsafe { CStr::from_ptr(libc::dlerror()) };
        bail!("dlopen {}: {}", so.display(), e.to_string_lossy());
    }
    let sym = unsafe { libc::dlsym(lib, c"fr_module".as_ptr()) };
    if sym.is_null() {
        bail!("{}: no fr_module", so.display());
    }
    let desc: &'static FrModule = unsafe { &*(sym as *const FrModule) };
    if desc.version != 1 {
        bail!("{}: descriptor version {}", so.display(), desc.version);
    }
    let reg = registry();
    for k in 0..desc.n_imports as usize {
        let imp = unsafe { &*desc.imports.add(k) };
        let (m, n, s) = unsafe {
            (
                CStr::from_ptr(imp.module).to_string_lossy().into_owned(),
                CStr::from_ptr(imp.name).to_string_lossy().into_owned(),
                CStr::from_ptr(imp.sig).to_string_lossy().into_owned(),
            )
        };
        let p = match reg.map.get(&(m.clone(), n.clone())) {
            Some((p, sig)) if *sig == s => *p as *const c_void,
            Some((_, sig)) => bail!("import {m}::{n}: signature {s}, runner has {sig}"),
            None => unknown_import as *const c_void,
        };
        unsafe { *desc.slots.add(k) = p };
    }
    install_signals();
    Ok(Arc::new(NativeModule { desc, _lib: lib }))
}

// ---------------------------------------------------------------------------------------------------------
// Fibers

std::arch::global_asm!(
    ".globl fr_switch",
    ".hidden fr_switch",
    "fr_switch:",
    "push rbp",
    "push rbx",
    "push r12",
    "push r13",
    "push r14",
    "push r15",
    "mov [rdi], rsp",
    "mov rsp, rsi",
    "pop r15",
    "pop r14",
    "pop r13",
    "pop r12",
    "pop rbx",
    "pop rbp",
    "ret",
    ".globl fr_fiber_entry",
    ".hidden fr_fiber_entry",
    "fr_fiber_entry:",
    "mov rdi, r12",
    "and rsp, -16",
    "call {main}",
    "ud2",
    main = sym fiber_main,
);

extern "C" {
    /// Saves callee-saved registers and the stack pointer into `*save`, switches to `to`.
    fn fr_switch(save: *mut *mut u8, to: *mut u8);
    fn fr_fiber_entry();
}

/// Why control came back to the runner.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Back {
    Yield,
    OutOfFuel,
    Done,
}

struct Region {
    base: *mut u8,
    len: usize,
}

impl Drop for Region {
    fn drop(&mut self) {
        unsafe { libc::munmap(self.base as *mut c_void, self.len) };
    }
}

fn map(len: usize, prot: i32) -> Result<Region> {
    let p = unsafe { libc::mmap(std::ptr::null_mut(), len, prot, libc::MAP_PRIVATE | libc::MAP_ANONYMOUS | libc::MAP_NORESERVE, -1, 0) };
    if p == libc::MAP_FAILED {
        bail!("mmap {len}: {}", std::io::Error::last_os_error());
    }
    Ok(Region { base: p as *mut u8, len })
}

/// Memory reservations and fiber stacks, reused across guests and games.
struct Pool {
    mems: Vec<(Region, usize)>,
    stacks: Vec<Region>,
}

static mut POOL: Pool = Pool { mems: Vec::new(), stacks: Vec::new() };

#[allow(static_mut_refs)]
fn pool() -> &'static mut Pool {
    unsafe { &mut POOL }
}

pub struct Guest {
    inst: Box<[u64]>,
    mem: Option<(Region, usize)>,
    stack: Option<Region>,
    pub ctx: BotCtx,
    module: Arc<NativeModule>,
    fiber_sp: *mut u8,
    runner_sp: *mut u8,
    started: bool,
    back: Back,
    result: Option<Result<(), String>>,
    /// wasmtime's fuel reserve (store fuel not yet injected into the counter).
    reserve: u64,
}

/// The guest running on this thread (one process plays one game at a time, on one thread).
static mut CURRENT: *mut Guest = std::ptr::null_mut();

impl Guest {
    fn inst(&mut self) -> *mut Inst {
        self.inst.as_mut_ptr() as *mut Inst
    }

    fn new(module: &Arc<NativeModule>, eng: &'static crate::engine::Eng, init: BotInit, meter: *mut Meter, log: *mut TeamLog) -> Result<Box<Guest>> {
        let d = module.desc;
        let words = std::mem::size_of::<Inst>() / 8 + d.n_globals as usize;
        let mut g = Box::new(Guest {
            inst: vec![0u64; words].into_boxed_slice(),
            mem: None,
            stack: None,
            ctx: BotCtx::new(eng, init, meter, log),
            module: module.clone(),
            fiber_sp: std::ptr::null_mut(),
            runner_sp: std::ptr::null_mut(),
            started: false,
            back: Back::Done,
            result: None,
            reserve: 0,
        });
        // memory
        let pages = d.mem_pages;
        let bytes = (pages * PAGE) as usize;
        let (region, dirty) = match pool().mems.pop() {
            Some(r) => r,
            None => (map(RESERVE, libc::PROT_NONE)?, 0),
        };
        unsafe {
            if dirty > 0 {
                std::ptr::write_bytes(region.base, 0, dirty.min(bytes));
                if dirty > bytes {
                    // pages beyond the new size: zero them and make them inaccessible again
                    libc::madvise(region.base.add(bytes) as *mut c_void, dirty - bytes, libc::MADV_DONTNEED);
                    libc::mprotect(region.base.add(bytes) as *mut c_void, dirty - bytes, libc::PROT_NONE);
                }
            }
            if bytes > dirty {
                if libc::mprotect(region.base.add(dirty) as *mut c_void, bytes - dirty, libc::PROT_READ | libc::PROT_WRITE) != 0 {
                    bail!("mprotect: {}", std::io::Error::last_os_error());
                }
            }
            for k in 0..d.n_data as usize {
                let seg = &*d.data.add(k);
                if seg.offset as usize + seg.len as usize > bytes {
                    bail!("data segment out of bounds");
                }
                std::ptr::copy_nonoverlapping(seg.bytes, region.base.add(seg.offset as usize), seg.len as usize);
            }
        }
        let base = region.base;
        g.mem = Some((region, bytes));
        let gp: *mut Guest = &mut *g;
        let ip = g.inst();
        unsafe {
            (*ip).mem = base;
            (*ip).size = bytes as u64;
            (*ip).rt = gp;
            let gl = (ip as *mut u64).add(std::mem::size_of::<Inst>() / 8);
            for k in 0..d.n_globals as usize {
                *gl.add(k) = *d.ginit.add(k);
            }
        }
        g.ctx.memdef = unsafe { &(*ip).mem as *const *mut u8 as *const u8 };
        // fuel: Store::set_fuel(STORE_FUEL), then fuel_async_yield_interval(quantum)
        let q = crate::fuel::quantum();
        let inject = q.min(STORE_FUEL).min(i64::MAX as u64);
        g.reserve = STORE_FUEL - inject;
        unsafe {
            (*ip).fuel = -(inject as i64);
            (*meter).ctr = &mut (*ip).fuel;
        }
        // fiber stack: guard page at the bottom
        let stack = match pool().stacks.pop() {
            Some(s) => s,
            None => {
                let s = map(STACK + GUARD, libc::PROT_READ | libc::PROT_WRITE)?;
                unsafe { libc::mprotect(s.base as *mut c_void, GUARD, libc::PROT_NONE) };
                s
            }
        };
        unsafe {
            let top = stack.base.add(stack.len) as *mut usize;
            // initial frame popped by fr_switch: r15 r14 r13 r12 rbx rbp, then the return address
            let sp = top.sub(8);
            *sp.add(0) = 0; // r15
            *sp.add(1) = 0; // r14
            *sp.add(2) = 0; // r13
            *sp.add(3) = gp as usize; // r12: fiber_main's argument
            *sp.add(4) = 0; // rbx
            *sp.add(5) = 0; // rbp
            *sp.add(6) = fr_fiber_entry as usize;
            *sp.add(7) = 0;
            g.fiber_sp = sp as *mut u8;
        }
        g.stack = Some(stack);
        Ok(g)
    }

    /// Runs the guest until it yields, runs out of fuel or ends.
    fn resume(&mut self) -> Back {
        if self.result.is_some() {
            return Back::Done;
        }
        self.started = true;
        unsafe {
            let prev = CURRENT;
            CURRENT = self;
            fr_switch(&mut self.runner_sp, self.fiber_sp);
            CURRENT = prev;
        }
        self.back
    }

    /// Back to the runner (on the fiber); returns when resumed.
    #[inline(never)]
    fn suspend(&mut self, why: Back) {
        self.back = why;
        unsafe { fr_switch(&mut self.fiber_sp, self.runner_sp) };
    }
}

/// FASTRUNNER_STATS: guests dropped, pages they had accessible, pages resident (touched).
pub static mut MEM_STATS: (u64, u64, u64) = (0, 0, 0);

impl Drop for Guest {
    fn drop(&mut self) {
        if std::env::var_os("FASTRUNNER_STATS").is_some() {
            if let Some((r, sz)) = &self.mem {
                let pages = sz / 4096;
                let mut v = vec![0u8; pages];
                unsafe {
                    libc::mincore(r.base as *mut c_void, *sz, v.as_mut_ptr());
                    MEM_STATS.0 += 1;
                    MEM_STATS.1 += pages as u64;
                    let _ = &v;
                    let words = std::slice::from_raw_parts(r.base as *const u64, sz / 8);
                    MEM_STATS.2 += words.chunks(512).filter(|p| p.iter().any(|&w| w != 0)).count() as u64;
                }
            }
        }
        if let Some(m) = self.mem.take() {
            pool().mems.push(m);
        }
        if let Some(s) = self.stack.take() {
            pool().stacks.push(s);
        }
    }
}

extern "C" fn fiber_main(g: *mut Guest) {
    unsafe {
        let ip = (*g).inst();
        let start = (&(*g).module).desc.start;
        start(ip);
        (*g).result = Some(if (*ip).exn != 0 { Err("wasm trap: uncaught exception".into()) } else { Ok(()) });
        (*g).suspend(Back::Done);
    }
    unreachable!("a finished guest was resumed");
}

/// Ends the guest with an error (on its fiber); never returns.
unsafe fn fail(i: *mut Inst, msg: String) -> ! {
    let g = &mut *(*i).rt;
    g.result = Some(Err(msg));
    g.suspend(Back::Done);
    unreachable!("a failed guest was resumed");
}

const TRAPS: [&str; 11] = [
    "wasm trap: wasm `unreachable` instruction executed",
    "wasm trap: integer divide by zero",
    "wasm trap: integer overflow",
    "wasm trap: invalid conversion to integer",
    "wasm trap: out of bounds memory access",
    "wasm trap: uninitialized element",
    "wasm trap: indirect call type mismatch",
    "wasm trap: undefined element: out of bounds table access",
    "wasm trap: null reference",
    "wasm trap: uncaught exception",
    "wasm trap: call stack exhausted",
];

#[no_mangle]
pub unsafe extern "C" fn fr_trap(i: *mut Inst, code: u32) -> ! {
    fail(i, TRAPS.get(code as usize).copied().unwrap_or("wasm trap").to_string())
}

/// wasmtime's out_of_gas with cambc's accounting (vendor patch), and the runner's reaction to the suspension
/// (Bot::run_turn): count the chunk(s); at the turn's budget the turn ends here and resumes next turn.
#[no_mangle]
pub unsafe extern "C" fn fr_out_of_gas(i: *mut Inst) {
    let g = &mut *(*i).rt;
    let m = &mut *g.ctx.meter;
    let ctr = &mut (*i).fuel;
    let overshoot = if *ctr > 0 { *ctr as u64 } else { 0 };
    // refuel(): all store fuel left, injected up to the yield interval
    let total = g.reserve.saturating_add_signed(-*ctr);
    if total == 0 {
        fail(i, "wasm trap: all fuel consumed by WebAssembly".into());
    }
    let interval = m.interval;
    let inject = interval.min(total).min(i64::MAX as u64);
    g.reserve = total - inject;
    *ctr = -(inject as i64);
    m.cell[0] = m.cell[0].saturating_add(overshoot / interval + 1);
    m.cell[1] = overshoot % interval;
    let a = std::mem::take(&mut m.cell[0]);
    m.chunks = m.chunks.saturating_add(a);
    if m.chunks >= m.budget {
        m.cell[1] = 0;
        m.used = m.interval.saturating_mul(m.budget);
        g.suspend(Back::OutOfFuel);
    }
    // resume accounting: the overshoot is charged to the new chunk
    let m = &mut *g.ctx.meter;
    let b = std::mem::take(&mut m.cell[1]);
    if b != 0 {
        let b = b.min(i64::MAX as u64) as i64;
        (*i).fuel = (*i).fuel.saturating_add(b);
    }
}

#[no_mangle]
pub unsafe extern "C" fn fr_memory_grow(i: *mut Inst, delta: u32) -> u32 {
    let g = &mut *(*i).rt;
    let old = (*i).size / PAGE;
    let max = g.module.desc.mem_max.min(65536).min(crate::native::max_pages());
    let new = old + delta as u64;
    if new > max {
        return u32::MAX;
    }
    if delta > 0 {
        let (r, sz) = g.mem.as_mut().unwrap();
        let start = *sz;
        let end = (new * PAGE) as usize;
        if libc::mprotect(r.base.add(start) as *mut c_void, end - start, libc::PROT_READ | libc::PROT_WRITE) != 0 {
            return u32::MAX;
        }
        *sz = end;
        (*i).size = end as u64;
    }
    old as u32
}

/// cambc's memory limit, 256 MiB (probe-memory), as the wasmtime backend's pooling allocator applies it.
pub fn max_pages() -> u64 {
    (256u64 << 20) / PAGE
}

/// The yield import: the turn's fuel is captured and the next turn gets a fresh chunk (host.rs's yield).
unsafe extern "C" fn native_yield(i: *mut Inst) {
    let g = &mut *(*i).rt;
    let ctx = &mut g.ctx;
    let m = ctx.meter();
    if m.paused {
        if m.debug_now() == m.saved_now {
            let s = m.saved_active;
            m.set_active(s);
        } else {
            crate::host::debug_overrun(ctx);
        }
        ctx.meter().paused = false;
    }
    let m = &mut *g.ctx.meter;
    let a = m.active();
    m.capture(a);
    m.yielded = true;
    // fuel_async_yield_interval(Some(i)): set_fuel(get_fuel())
    let total = g.reserve.saturating_add_signed(-(*i).fuel);
    let inject = m.interval.min(total).min(i64::MAX as u64);
    g.reserve = total - inject;
    (*i).fuel = -(inject as i64);
    g.suspend(Back::Yield);
}

// ---------------------------------------------------------------------------------------------------------
// Faults: memory accesses outside the wasm memory and fiber stack overflow become traps.

static mut OLD_SEGV: libc::sigaction = unsafe { std::mem::zeroed() };
static mut OLD_BUS: libc::sigaction = unsafe { std::mem::zeroed() };

unsafe extern "C" fn trap_from_signal(i: *mut Inst, code: u32) -> ! {
    fr_trap(i, code)
}

unsafe extern "C" fn on_fault(sig: i32, info: *mut libc::siginfo_t, uc: *mut c_void) {
    let g = CURRENT;
    let addr = (*info).si_addr() as usize;
    if !g.is_null() {
        let g = &mut *g;
        let code = match (&g.mem, &g.stack) {
            (Some((m, _)), _) if addr >= m.base as usize && addr < m.base as usize + m.len => Some(4u32),
            (_, Some(s)) if addr >= s.base as usize && addr < s.base as usize + GUARD + 4096 => Some(10u32),
            _ => None,
        };
        if let (Some(code), Some(s)) = (code, &g.stack) {
            // Continue in trap_from_signal on the guest's stack (abandoned afterwards).
            let ctx = &mut *(uc as *mut libc::ucontext_t);
            let top = (s.base as usize + s.len - 4096) & !15;
            ctx.uc_mcontext.gregs[libc::REG_RSP as usize] = (top - 8) as i64;
            ctx.uc_mcontext.gregs[libc::REG_RIP as usize] = trap_from_signal as usize as i64;
            ctx.uc_mcontext.gregs[libc::REG_RDI as usize] = g.inst() as i64;
            ctx.uc_mcontext.gregs[libc::REG_RSI as usize] = code as i64;
            return;
        }
    }
    // Not ours: the previous handler (wasmtime's, or the default).
    let old = if sig == libc::SIGSEGV { &raw const OLD_SEGV } else { &raw const OLD_BUS };
    let old = &*old;
    if old.sa_flags & libc::SA_SIGINFO != 0 && old.sa_sigaction > 1 {
        let f: unsafe extern "C" fn(i32, *mut libc::siginfo_t, *mut c_void) = std::mem::transmute(old.sa_sigaction);
        f(sig, info, uc);
    } else if old.sa_sigaction > 1 {
        let f: unsafe extern "C" fn(i32) = std::mem::transmute(old.sa_sigaction);
        f(sig);
    } else {
        libc::signal(sig, libc::SIG_DFL);
        libc::raise(sig);
    }
}

fn install_signals() {
    static ONCE: std::sync::Once = std::sync::Once::new();
    ONCE.call_once(|| unsafe {
        // An alternate signal stack, for faults on an exhausted fiber stack.
        let mut cur: libc::stack_t = std::mem::zeroed();
        libc::sigaltstack(std::ptr::null(), &mut cur);
        if cur.ss_flags & libc::SS_DISABLE != 0 || cur.ss_size < 64 << 10 {
            let size = 256 << 10;
            let p = libc::mmap(std::ptr::null_mut(), size, libc::PROT_READ | libc::PROT_WRITE, libc::MAP_PRIVATE | libc::MAP_ANONYMOUS, -1, 0);
            let st = libc::stack_t { ss_sp: p, ss_flags: 0, ss_size: size };
            libc::sigaltstack(&st, std::ptr::null_mut());
        }
        let mut sa: libc::sigaction = std::mem::zeroed();
        sa.sa_sigaction = on_fault as usize;
        sa.sa_flags = libc::SA_SIGINFO | libc::SA_ONSTACK | libc::SA_NODEFER;
        libc::sigemptyset(&mut sa.sa_mask);
        libc::sigaction(libc::SIGSEGV, &sa, &raw mut OLD_SEGV);
        libc::sigaction(libc::SIGBUS, &sa, &raw mut OLD_BUS);
    });
}

// ---------------------------------------------------------------------------------------------------------
// The bot interface (runtime::Bot's native backend)

pub struct NativeBot {
    guest: Option<Box<Guest>>,
}

impl NativeBot {
    pub fn spawn(module: &Arc<NativeModule>, eng: &'static crate::engine::Eng, init: BotInit, meter: *mut Meter, log: *mut TeamLog) -> Result<NativeBot> {
        Ok(NativeBot { guest: Some(Guest::new(module, eng, init, meter, log).map_err(|e| anyhow!("{e:#}"))?) })
    }

    pub fn alive(&self) -> bool {
        self.guest.is_some()
    }

    pub fn run_turn(&mut self, meter: &mut Meter) -> TurnEnd {
        let Some(g) = self.guest.as_mut() else {
            meter.used = 0;
            return TurnEnd::Yield;
        };
        match g.resume() {
            Back::Yield => TurnEnd::Yield,
            Back::OutOfFuel => TurnEnd::OutOfFuel,
            Back::Done => {
                if !meter.ctr.is_null() {
                    let a = meter.active();
                    meter.capture(a);
                    meter.ctr = std::ptr::null_mut();
                }
                let r = g.result.take().unwrap_or(Ok(()));
                self.guest = None;
                match r {
                    Ok(()) => TurnEnd::Exited,
                    Err(msg) if msg.contains(HOST_EXIT) => TurnEnd::Removed,
                    Err(msg) => TurnEnd::Error(msg),
                }
            }
        }
    }
}
