//! Probes for a fast engine built on upstream wasmtime 49.0.2 (the version cambc 4.0.0 embeds).
//!
//!   floor check-cache BOT.wasm CACHE_DIR   compile BOT.wasm as cambc does and compare with every compiled module
//!                                          in cambc's wasmtime cache (CAMBC_WASMTIME_CACHE/modules/wasmtime-49.0.2)
//!   floor load-cache CACHE_FILE            load a cambc-compiled module with our engine (config compatibility)
//!   floor costs CACHE_FILE                 recover cambc's operator cost table from a compiled module's engine section
//!   floor bench-calls [N]                  ns per wasm -> host call (bench.rs), with fuel on and off
mod bench;

use anyhow::{bail, Context, Result};
use object::{Object, ObjectSection};
use std::path::Path;
use wasmtime::{Config, Engine, Module, OptLevel};

/// cambc's engine settings, as far as its cached modules show them (`floor costs`, `load-cache`).
pub fn cambc_config() -> Config {
    let mut c = Config::new();
    c.consume_fuel(true);
    c.cranelift_opt_level(OptLevel::Speed);
    c.relaxed_simd_deterministic(true);
    c.wasm_component_model(false);
    // Default operator costs except memory.grow, which cambc makes free (flat and per page).
    let mut cost = wasmtime::OperatorCost::new();
    cost.MemoryGrow = 0;
    cost.variable.memory_grow_per_page = 0;
    c.operator_cost(cost);
    c
}

pub fn werr(e: wasmtime::Error) -> anyhow::Error {
    anyhow::anyhow!("{e:?}")
}

fn text_of(elf: &[u8]) -> Result<Vec<u8>> {
    let f = object::File::parse(elf)?;
    let s = f.section_by_name(".text").context("no .text")?;
    Ok(s.data()?.to_vec())
}

fn engine_section(elf: &[u8]) -> Result<Vec<u8>> {
    let f = object::File::parse(elf)?;
    let s = f.section_by_name(".wasmtime.engine").context("no engine section")?;
    Ok(s.data()?.to_vec())
}

/// Finds the serialized OperatorCost table inside an engine section by its closeness to the default table.
pub fn recover_costs(section: &[u8]) -> Result<wasmtime::OperatorCost> {
    let def = postcard::to_allocvec(&wasmtime::OperatorCost::new())?;
    let (mut best, mut best_d) = (0, usize::MAX);
    for off in 0..section.len().saturating_sub(def.len()) {
        let d = def.iter().zip(&section[off..]).filter(|(a, b)| a != b).count();
        if d < best_d {
            best_d = d;
            best = off;
        }
    }
    eprintln!("operator table at engine-section offset {best}, {best_d} of {} bytes differ from the default", def.len());
    Ok(postcard::from_bytes(&section[best..best + def.len()])?)
}

fn read_cache_file(p: &Path) -> Result<Vec<u8>> {
    let raw = std::fs::read(p)?;
    Ok(zstd::decode_all(&raw[..])?)
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    match args.get(1).map(|s| s.as_str()) {
        Some("check-cache") => {
            let engine = Engine::new(&cambc_config()).map_err(werr)?;
            let wasm = std::fs::read(&args[2])?;
            let t0 = std::time::Instant::now();
            let ours = engine.precompile_module(&wasm).map_err(werr)?;
            eprintln!("compiled in {:?}", t0.elapsed());
            let our_text = text_of(&ours)?;
            let our_engine = engine_section(&ours)?;
            std::fs::write("floor-ours-engine.bin", &our_engine)?;
            let mut found = false;
            for e in std::fs::read_dir(&args[3])? {
                let p = e?.path();
                if p.extension().is_some() || p.file_name().unwrap().to_string_lossy().starts_with('.') {
                    continue;
                }
                let theirs = match read_cache_file(&p) {
                    Ok(t) => t,
                    Err(_) => continue,
                };
                let t = text_of(&theirs)?;
                let es = engine_section(&theirs)?;
                let same_text = t == our_text;
                println!(
                    "{}  text {} bytes (ours {}), text identical: {}, engine section identical: {}, whole artifact identical: {}",
                    p.file_name().unwrap().to_string_lossy(),
                    t.len(),
                    our_text.len(),
                    same_text,
                    es == our_engine,
                    theirs == ours
                );
                found |= same_text;
            }
            if !found {
                bail!("no cached module has our .text (our engine section written to ./floor-ours-engine.bin)");
            }
        }
        Some("load-cache") => {
            let engine = Engine::new(&cambc_config()).map_err(werr)?;
            let bytes = read_cache_file(Path::new(&args[2]))?;
            match unsafe { Module::deserialize(&engine, &bytes) } {
                Ok(m) => println!("loaded: {} imports, {} exports", m.imports().len(), m.exports().len()),
                Err(e) => println!("rejected: {e:#}"),
            }
        }
        Some("bench-calls") => {
            let n: i32 = args.get(2).map(|s| s.parse()).transpose()?.unwrap_or(20_000_000);
            println!("-- cambc config (fuel on)");
            bench::run(&Engine::new(&cambc_config()).map_err(werr)?, n)?;
            let mut c = cambc_config();
            c.consume_fuel(false);
            println!("-- same, fuel off");
            bench::run(&Engine::new(&c).map_err(werr)?, n)?;
        }
        Some("costs") => {
            let theirs = engine_section(&read_cache_file(Path::new(&args[2]))?)?;
            let cost = recover_costs(&theirs)?;
            let def = format!("{:#?}", wasmtime::OperatorCost::new());
            let got = format!("{:#?}", cost);
            for (a, b) in def.lines().zip(got.lines()) {
                if a != b {
                    println!("default {:<40} cambc {}", a.trim(), b.trim());
                }
            }
            std::fs::write("cambc-operator-cost.postcard", postcard::to_allocvec(&cost)?)?;
        }
        _ => bail!("usage: floor check-cache BOT.wasm CACHE_DIR | load-cache FILE"),
    }
    Ok(())
}
