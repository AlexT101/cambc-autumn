//! fastrunner: plays Cambridge Battlecode matches like `cambc run` / `cambc run-batch` (cambc 4.0.0),
//! with cambc's own native engine (loaded from the cambc binary) and wasmtime 49.0.2.
//!
//!   fastrunner run BOT_A BOT_B --map MAP [-o OUTDIR] [--rounds N] [--log-limit B] [--release]
//!   fastrunner run-batch MANIFEST [--jobs N] [--color never] [--fuel-quantum Q] [--timeout T]
//!                        [--rounds N] [--log-limit B] [--release] [--slot-dir DIR --slots N]
//!   fastrunner __fastrunner     (prints "fastrunner slots": how run_batched.py recognises it)
//!
//! Manifest lines: BOT_A BOT_B MAP OUT.repl26a [--statistics OUT.camstat]; paths relative to the
//! manifest's directory. Each bot is a project directory built by `cambc build` (its
//! .cambc/build/bot-injected.wasm, or build-release with --release).
mod aot;
mod api;
mod bundle;
mod df;
mod engine;
mod fuel;
mod game;
mod host;
mod native;
mod patch;
mod replay;
mod runtime;
mod stats;

/// cambc's __libc_start_main, with main replaced by ours when FASTRUNNER_MAIN is set.
type StartMain = unsafe extern "C" fn(
    unsafe extern "C" fn(i32, *mut *mut i8, *mut *mut i8) -> i32,
    i32,
    *mut *mut i8,
    usize,
    usize,
    usize,
    *mut libc::c_void,
) -> i32;

#[no_mangle]
pub unsafe extern "C" fn __libc_start_main(
    main: unsafe extern "C" fn(i32, *mut *mut i8, *mut *mut i8) -> i32,
    argc: i32,
    argv: *mut *mut i8,
    init: usize,
    fini: usize,
    rtld_fini: usize,
    stack_end: *mut libc::c_void,
) -> i32 {
    let real: StartMain = std::mem::transmute(libc::dlsym(libc::RTLD_NEXT, c"__libc_start_main".as_ptr()));
    let mut ours = false;
    // Wrappers (taskset, env, ...) pass through untouched; in cambc only matches are ours, and every other
    // cambc command (build, bundle, ...) runs as stock, without us in its children.
    if !libc::getenv(c"FASTRUNNER_MAIN".as_ptr()).is_null() && engine::is_cambc_process() {
        let cmd = if argc > 1 { std::ffi::CStr::from_ptr(*argv.add(1)).to_bytes() } else { b"" };
        ours = matches!(cmd, b"run" | b"run-batch" | b"__worker" | b"__fastrunner" | b"__fuzzdf");
        if !ours {
            libc::unsetenv(c"LD_PRELOAD".as_ptr());
            libc::unsetenv(c"FASTRUNNER_MAIN".as_ptr());
        }
    }
    if ours {
        real(fast_main, argc, argv, init, fini, rtld_fini, stack_end)
    } else {
        real(main, argc, argv, init, fini, rtld_fini, stack_end)
    }
}

unsafe extern "C" fn fast_main(_argc: i32, _argv: *mut *mut i8, _envp: *mut *mut i8) -> i32 {
    match real_main() {
        Ok(code) => code,
        Err(e) => {
            eprintln!("Error: {e:#}");
            2
        }
    }
}

use anyhow::{anyhow, bail, Context, Result};
use std::io::{BufRead, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

#[derive(Clone, Debug)]
struct Job {
    a: PathBuf,
    b: PathBuf,
    map: PathBuf,
    out: PathBuf,
    statistics: Option<PathBuf>,
}

#[derive(Clone, Debug)]
struct Opts {
    quantum: u64,
    rounds: u32,
    log_limit: usize,
    release: bool,
    jobs: usize,
    quiet: bool,
    /// tools/cpu_slots.py's pool (directory, size): run-batch holds a slot per game in play.
    slots: Option<(PathBuf, usize)>,
}

fn bot_name(p: &Path) -> String {
    p.file_name().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default()
}

fn map_name(p: &Path) -> String {
    p.file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default()
}

/// Like cambc run/run-batch, rebuilds the bot first (a no-op build costs ~nothing), once per process;
/// run-batch workers inherit FASTRUNNER_BUILT and only check the wasm exists.
fn wasm_of(bot: &Path, release: bool) -> Result<PathBuf> {
    static BUILT: std::sync::Mutex<Vec<(PathBuf, bool)>> = std::sync::Mutex::new(Vec::new());
    let w = bot.join(".cambc").join(if release { "build-release" } else { "build" }).join("bot-injected.wasm");
    let key = (bot.to_path_buf(), release);
    let skip = std::env::var_os("FASTRUNNER_BUILT").is_some() || BUILT.lock().unwrap().contains(&key);
    if !skip {
        let mut cmd = std::process::Command::new(std::env::current_exe()?);
        cmd.arg("build").arg(bot).env_remove("FASTRUNNER_MAIN").env_remove("LD_PRELOAD");
        if release {
            cmd.arg("--release");
        }
        let out = cmd.output().context("running cambc build")?;
        if !out.status.success() {
            std::io::stderr().write_all(&out.stdout).ok();
            std::io::stderr().write_all(&out.stderr).ok();
            bail!("building {} failed", bot.display());
        }
        BUILT.lock().unwrap().push(key);
    }
    if !w.exists() {
        bail!("{} is not built ({} missing)", bot.display(), w.display());
    }
    Ok(w)
}

/// cambc run works from anywhere inside a project: the nearest ancestor holding cambc.toml.
fn project_root() -> PathBuf {
    let cwd = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    cwd.ancestors().find(|d| d.join("cambc.toml").is_file()).map(Path::to_path_buf).unwrap_or(cwd)
}

fn resolve_bot(root: &Path, b: &str) -> Result<PathBuf> {
    for p in [PathBuf::from(b), root.join("bots").join(b), root.join(b)] {
        if p.is_dir() {
            return Ok(std::fs::canonicalize(p)?);
        }
    }
    bail!("bot {b} not found")
}

/// cambc run --map: maps/<M>.map26a, maps/<M> (in the project), then <M>.map26a, <M> (from the current directory);
/// an existing .map26a suffix is not repeated; without --map, the first .map26a directly in maps/, alphabetically.
fn resolve_map(root: &Path, m: Option<&str>) -> Result<PathBuf> {
    let Some(m) = m else {
        let mut maps: Vec<PathBuf> = std::fs::read_dir(root.join("maps"))
            .context("listing maps/")?
            .filter_map(|e| e.ok().map(|e| e.path()))
            .filter(|p| p.is_file() && p.extension().is_some_and(|x| x == "map26a"))
            .collect();
        maps.sort();
        return maps.into_iter().next().ok_or_else(|| anyhow!("no maps in {}", root.join("maps").display()));
    };
    let suffixed = m.ends_with(".map26a");
    let mut cands = Vec::new();
    if !suffixed {
        cands.push(root.join("maps").join(format!("{m}.map26a")));
    }
    cands.push(root.join("maps").join(m));
    if !suffixed {
        cands.push(PathBuf::from(format!("{m}.map26a")));
    }
    cands.push(PathBuf::from(m));
    for p in cands {
        if p.is_file() {
            return Ok(std::fs::canonicalize(p)?);
        }
    }
    bail!("map {m} not found")
}

fn play_job(rt: &mut runtime::Runtime, job: &Job, o: &Opts) -> Result<game::MatchResult> {
    let wa = wasm_of(&job.a, o.release)?;
    let wb = wasm_of(&job.b, o.release)?;
    let pa = rt.program(&wa)?;
    let pb = rt.program(&wb)?;
    let map = std::fs::read(&job.map).with_context(|| format!("reading {}", job.map.display()))?;
    let spec = game::MatchSpec { map: &map, programs: [pa, pb], max_rounds: o.rounds, log_limit: o.log_limit, statistics: job.statistics.is_some() };
    let t0 = Instant::now();
    host::trace_start();
    let r = game::play(rt, &spec);
    host::trace_dump();
    let r = r?;
    let t1 = Instant::now();
    bundle::write_bundle(&job.out, &r)?;
    if std::env::var_os("FASTRUNNER_STATS").is_some() {
        eprintln!("timing: play {:.3}s bundle {:.3}s", (t1 - t0).as_secs_f64(), t1.elapsed().as_secs_f64());
        let m = unsafe { native::MEM_STATS };
        eprintln!("native memory: {} guests, {} pages accessible, {} resident", m.0, m.1, m.2);
    }
    if let (Some(p), Some(s)) = (&job.statistics, &r.statistics) {
        std::fs::write(p, s)?;
    }
    Ok(r)
}

/// Status lines in cambc run-batch's format (tools/run_batched.py parses them).
fn status_line(job: &Job, r: &Result<game::MatchResult>, max_rounds: u32) -> String {
    let (a, b) = (bot_name(&job.a), bot_name(&job.b));
    let m = map_name(&job.map);
    let head = match r {
        Ok(res) => match res.winner {
            Some(w) if res.finished => {
                let (t, n) = if w == 0 { ("A", &a) } else { ("B", &b) };
                format!("[+] TEAM {t} WIN ({n})  {a} vs {b}  {m}  Round {:04}/2000", res.rounds)
            }
            _ => format!("[+] TRUNCATED  {a} vs {b}  {m}  Round {:04}/2000", res.rounds),
        },
        Err(e) => format!("[!] FAILED: {}  {a} vs {b}  {m}", format!("{e:#}").replace('\n', " ")),
    };
    format!("{head}\n    Replay: {}\n", job.out.display())
}

fn parse_manifest(path: &Path) -> Result<Vec<Job>> {
    let base = path.parent().map(Path::to_path_buf).unwrap_or_default();
    let abs = |s: &str| -> PathBuf {
        let p = PathBuf::from(s);
        if p.is_absolute() {
            p
        } else {
            base.join(p)
        }
    };
    let text = std::fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
    let mut jobs = Vec::new();
    for (n, line) in text.lines().enumerate() {
        let w: Vec<&str> = line.split_whitespace().collect();
        if w.is_empty() || w[0].starts_with('#') {
            continue;
        }
        if w.len() < 4 {
            bail!("{}:{}: expected BOT_A BOT_B MAP REPLAY", path.display(), n + 1);
        }
        let mut job = Job { a: abs(w[0]), b: abs(w[1]), map: abs(w[2]), out: abs(w[3]), statistics: None };
        let mut i = 4;
        while i < w.len() {
            match w[i] {
                "--statistics" if i + 1 < w.len() => {
                    job.statistics = Some(abs(w[i + 1]));
                    i += 2;
                }
                "--json" => i += 1,
                x => bail!("{}:{}: unknown option {x}", path.display(), n + 1),
            }
        }
        for (what, p) in [("bot A", &job.a), ("bot B", &job.b), ("map", &job.map)] {
            if !p.exists() {
                bail!("{}:{}: {what} does not exist: {}", path.display(), n + 1, p.display());
            }
        }
        jobs.push(job);
    }
    Ok(jobs)
}

fn load_runtime() -> Result<runtime::Runtime> {
    let eng = engine::load()?;
    patch::install(eng);
    runtime::Runtime::new(eng)
}

/// Worker process: reads job indices on stdin, plays them, writes "idx<TAB>status lines" records.
fn worker(manifest: &Path, o: &Opts) -> Result<()> {
    let jobs = parse_manifest(manifest)?;
    let mut rt = load_runtime()?;
    let stdin = std::io::stdin();
    let mut out = std::io::stdout().lock();
    for line in stdin.lock().lines() {
        let line = line?;
        let idx: usize = line.trim().parse()?;
        let job = &jobs[idx];
        let t = Instant::now();
        let r = play_job(&mut rt, job, o);
        let s = status_line(job, &r, o.rounds);
        let enc = s.replace('\n', "\u{1f}");
        writeln!(out, "{idx}\t{:.3}\t{enc}", t.elapsed().as_secs_f64())?;
        out.flush()?;
    }
    Ok(())
}

/// A held CPU slot: tools/cpu_slots.py's flock on DIR/slot-NN.
struct Slot(usize, std::fs::File);

struct Slots {
    dir: PathBuf,
    n: usize,
    rng: u64,
}

impl Slots {
    fn new(dir: &Path, n: usize) -> Slots {
        Slots { dir: dir.to_path_buf(), n, rng: std::process::id() as u64 * 0x9e3779b97f4a7c15 | 1 }
    }

    /// A free slot now, or None.
    fn take(&mut self) -> Option<Slot> {
        use std::os::fd::AsRawFd;
        self.rng ^= self.rng << 13;
        self.rng ^= self.rng >> 7;
        self.rng ^= self.rng << 17;
        let start = (self.rng % self.n as u64) as usize;
        for k in 0..self.n {
            let i = (start + k) % self.n;
            let Ok(f) = std::fs::OpenOptions::new().read(true).append(true).create(true).open(self.dir.join(format!("slot-{i:02}"))) else {
                continue;
            };
            if unsafe { libc::flock(f.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } == 0 {
                return Some(Slot(i, f));
            }
        }
        None
    }

    fn release(&mut self, s: Slot) {
        use std::os::fd::AsRawFd;
        unsafe { libc::flock(s.1.as_raw_fd(), libc::LOCK_UN) };
    }
}

fn run_batch(manifest: &Path, o: &Opts) -> Result<i32> {
    let jobs = parse_manifest(manifest)?;
    let started = Instant::now();
    let mut failed = 0usize;
    let mut stdout = std::io::stdout().lock();
    if jobs.is_empty() {
        return Ok(0);
    }
    let n = o.jobs.max(1).min(jobs.len());
    if n == 1 {
        let mut rt = load_runtime()?;
        let mut slots = o.slots.as_ref().map(|(d, k)| Slots::new(d, *k));
        for job in &jobs {
            write!(stdout, "[|] STARTING  {} vs {}  {}\n    Replay: {}\n", bot_name(&job.a), bot_name(&job.b), map_name(&job.map), job.out.display())?;
            stdout.flush()?;
            // Like the workers below, a game in play holds a CPU slot.
            let slot = match slots.as_mut() {
                Some(s) => loop {
                    if let Some(x) = s.take() {
                        break Some(x);
                    }
                    std::thread::sleep(std::time::Duration::from_millis(5 + s.rng % 5));
                },
                None => None,
            };
            let r = play_job(&mut rt, job, o);
            if let (Some(s), Some(sl)) = (slots.as_mut(), slot) {
                s.release(sl);
            }
            if r.is_err() {
                failed += 1;
            }
            stdout.write_all(status_line(job, &r, o.rounds).as_bytes())?;
            stdout.flush()?;
        }
    } else {
        // Compile each bot once here, so the workers load it from the cache instead of racing to compile it.
        {
            let mut rt = load_runtime()?;
            let mut seen = std::collections::HashSet::new();
            for job in &jobs {
                for b in [&job.a, &job.b] {
                    if seen.insert(b.clone()) {
                        rt.program(&wasm_of(b, o.release)?)?;
                    }
                }
            }
        }
        // n worker processes, each playing jobs handed out one at a time.
        let exe = std::env::current_exe()?;
        let mut children = Vec::new();
        for _ in 0..n {
            let mut c = std::process::Command::new(&exe);
            c.env("FASTRUNNER_BUILT", "1");
            c.arg("__worker").arg(manifest).arg("--rounds").arg(o.rounds.to_string()).arg("--log-limit").arg(o.log_limit.to_string());
            c.arg("--fuel-quantum").arg(o.quantum.to_string());
            if o.release {
                c.arg("--release");
            }
            c.stdin(std::process::Stdio::piped()).stdout(std::process::Stdio::piped());
            children.push(c.spawn()?);
        }
        let (tx, rx) = std::sync::mpsc::channel::<(usize, String)>();
        let mut inputs = Vec::new();
        for (w, ch) in children.iter_mut().enumerate() {
            inputs.push(ch.stdin.take().unwrap());
            let so = ch.stdout.take().unwrap();
            let tx = tx.clone();
            std::thread::spawn(move || {
                for line in std::io::BufReader::new(so).lines() {
                    let Ok(line) = line else { break };
                    if tx.send((w, line)).is_err() {
                        break;
                    }
                }
                let _ = tx.send((w, String::from("\u{0}eof")));
            });
        }
        drop(tx);
        let mut slots = o.slots.as_ref().map(|(d, k)| Slots::new(d, *k));
        let mut current: Vec<Option<(usize, Option<Slot>)>> = (0..n).map(|_| None).collect();
        let mut idle: Vec<usize> = (0..n).rev().collect();
        let mut next = 0usize;
        let mut busy = 0usize;
        let mut alive = n;
        // With shared CPU slots, take free ones only every few ms (jittered), never straight after freeing one, so
        // concurrent batches (ab.py's suites) share the slots evenly instead of one keeping them all.
        let mut next_poll = Instant::now();
        let mut rng = std::process::id() as u64 | 1;
        loop {
            let poll_now = slots.is_none() || Instant::now() >= next_poll;
            if slots.is_some() && poll_now {
                rng ^= rng << 13;
                rng ^= rng >> 7;
                rng ^= rng << 17;
                next_poll = Instant::now() + std::time::Duration::from_micros(3000 + rng % 5000);
            }
            while poll_now && next < jobs.len() && !idle.is_empty() {
                let slot = match slots.as_mut() {
                    Some(s) => match s.take() {
                        Some(x) => Some(x),
                        None => break,
                    },
                    None => None,
                };
                let w = idle.pop().unwrap();
                let job = &jobs[next];
                write!(stdout, "[|] STARTING  {} vs {}  {}\n    Replay: {}\n", bot_name(&job.a), bot_name(&job.b), map_name(&job.map), job.out.display())?;
                stdout.flush()?;
                if writeln!(inputs[w], "{next}").and_then(|_| inputs[w].flush()).is_err() {
                    // a dead worker: its eof record retires it
                    if let (Some(s), Some(sl)) = (slots.as_mut(), slot) {
                        s.release(sl);
                    }
                    continue;
                }
                current[w] = Some((next, slot));
                next += 1;
                busy += 1;
            }
            if busy == 0 && (next >= jobs.len() || alive == 0 || idle.is_empty()) {
                break;
            }
            // Waiting for a CPU slot: poll at next_poll; otherwise wait for a result.
            let waiting = slots.is_some() && next < jobs.len() && !idle.is_empty();
            let msg = if waiting {
                match rx.recv_timeout(next_poll.saturating_duration_since(Instant::now())) {
                    Ok(m) => m,
                    Err(std::sync::mpsc::RecvTimeoutError::Timeout) => continue,
                    Err(_) => break,
                }
            } else {
                match rx.recv() {
                    Ok(m) => m,
                    Err(_) => break,
                }
            };
            let (w, line) = msg;
            let done = current[w].take();
            let (idx, slot) = match done {
                Some((i, sl)) => (Some(i), sl),
                None => (None, None),
            };
            if let (Some(s), Some(sl)) = (slots.as_mut(), slot) {
                s.release(sl);
            }
            if line == "\u{0}eof" {
                alive -= 1;
                idle.retain(|&x| x != w);
                if let Some(i) = idx {
                    let job = &jobs[i];
                    stdout.write_all(format!("[!] FAILED: worker died  {} vs {}  {}\n    Replay: {}\n", bot_name(&job.a), bot_name(&job.b), map_name(&job.map), job.out.display()).as_bytes())?;
                    stdout.flush()?;
                    failed += 1;
                    busy -= 1;
                }
                continue;
            }
            let s = line.splitn(3, '\t').nth(2).unwrap_or("").replace('\u{1f}', "\n");
            if s.starts_with("[!]") {
                failed += 1;
            }
            stdout.write_all(s.as_bytes())?;
            stdout.flush()?;
            if idx.is_some() {
                busy -= 1;
            }
            idle.push(w);
        }
        drop(inputs);
        for mut c in children {
            let _ = c.wait();
        }
        for job in &jobs[next..] {
            stdout.write_all(format!("[!] FAILED: worker died  {} vs {}  {}\n    Replay: {}\n", bot_name(&job.a), bot_name(&job.b), map_name(&job.map), job.out.display()).as_bytes())?;
            failed += 1;
        }
    }
    writeln!(
        stdout,
        "Finished: {} replay bundles saved, {} failed ({:.1}s)",
        jobs.len() - failed,
        failed,
        started.elapsed().as_secs_f64()
    )?;
    Ok(if failed > 0 { 1 } else { 0 })
}


fn real_main() -> Result<i32> {
    let args: Vec<String> = std::env::args().collect();
    let mut o = Opts { quantum: crate::fuel::DEFAULT_QUANTUM, rounds: 2000, log_limit: 1 << 20, release: false, jobs: 1, quiet: false, slots: None };
    let mut slot_dir: Option<PathBuf> = None;
    let mut slot_count = 0usize;
    let mut pos: Vec<String> = Vec::new();
    let mut map: Option<String> = None;
    let mut outdir: Option<PathBuf> = None;
    let mut statistics: Option<PathBuf> = None;
    let mut i = 2;
    let need = |i: usize| -> Result<&String> { args.get(i + 1).ok_or_else(|| anyhow!("{} needs a value", args[i])) };
    while i < args.len() {
        let a = args[i].as_str();
        match a {
            "--jobs" => {
                o.jobs = need(i)?.parse()?;
                i += 2;
            }
            "--rounds" => {
                o.rounds = need(i)?.parse::<u64>()?.min(u32::MAX as u64) as u32;
                i += 2;
            }
            "--log-limit" => {
                o.log_limit = need(i)?.parse()?;
                i += 2;
            }
            "--fuel-quantum" | "--fuel" => {
                let q: u64 = need(i)?.parse()?;
                crate::fuel::set_quantum(q);
                o.quantum = q;
                i += 2;
            }
            "--timeout" | "--color" | "--jsonl" => i += 2,
            "--release" => {
                o.release = true;
                i += 1;
            }
            "--quiet" => {
                o.quiet = true;
                i += 1;
            }
            "--map" => {
                map = Some(need(i)?.clone());
                i += 2;
            }
            "-o" | "--out-dir" => {
                outdir = Some(PathBuf::from(need(i)?));
                i += 2;
            }
            "--statistics" => {
                statistics = Some(PathBuf::from(need(i)?));
                i += 2;
            }
            "--slot-dir" => {
                slot_dir = Some(PathBuf::from(need(i)?));
                i += 2;
            }
            "--slots" => {
                slot_count = need(i)?.parse()?;
                i += 2;
            }
            "--json" | "--view" => i += 1,
            _ if a.starts_with("--") => bail!("unknown option {a}"),
            _ => {
                pos.push(a.to_string());
                i += 1;
            }
        }
    }
    if let Some(d) = slot_dir {
        o.slots = Some((d, slot_count.max(1)));
    }
    match args.get(1).map(String::as_str) {
        Some("__fastrunner") => {
            println!("fastrunner slots");
            Ok(0)
        }
        Some("run-batch") => {
            let m = pos.first().ok_or_else(|| anyhow!("run-batch needs a manifest"))?;
            run_batch(&std::fs::canonicalize(m)?, &o)
        }
        Some("__fuzzdf") => df::fuzz_main(&pos),
        Some("__worker") => {
            worker(Path::new(&pos[0]), &o)?;
            Ok(0)
        }
        Some("run") => {
            if pos.len() < 2 {
                bail!("usage: fastrunner run BOT_A BOT_B --map MAP [-o OUTDIR]");
            }
            let root = project_root();
            let a = resolve_bot(&root, &pos[0])?;
            let b = resolve_bot(&root, &pos[1])?;
            let mp = resolve_map(&root, map.as_deref())?;
            let dir = outdir.unwrap_or_else(|| root.join("replays"));
            let ms = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_millis()).unwrap_or(0);
            let out = dir.join(format!("{}-vs-{}-{ms}.repl26a", bot_name(&a), bot_name(&b)));
            let job = Job { a, b, map: mp, out, statistics };
            let mut rt = load_runtime()?;
            let t = Instant::now();
            let r = play_job(&mut rt, &job, &o);
            print!("{}", status_line(&job, &r, o.rounds));
            if !o.quiet {
                eprintln!("{:.3}s", t.elapsed().as_secs_f64());
            }
            Ok(if r.is_ok() { 0 } else { 1 })
        }
        _ => {
            eprintln!("usage: fastrunner run|run-batch ...");
            Ok(2)
        }
    }
}
