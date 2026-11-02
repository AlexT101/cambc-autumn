//! Cost of one wasm -> host call in wasmtime 49.0.2 with cambc's engine config (fuel on), for three host styles:
//!   plain:     Func::wrap(|a, b| ..) with no Caller;
//!   lean:      Caller + guest memory through a Memory handle kept in the store (one read, one write);
//!   by-name:   Caller + caller.get_export("memory") on every call, as cambc's runner does.
//! Each import is called N times from a wasm loop; a loop with no call gives the loop's own cost.
use anyhow::Result;
use std::time::Instant;
use wasmtime::{Caller, Engine, Extern, Instance, Linker, Memory, Module, Store};

const WAT: &str = r#"
(module
  (import "env" "plain" (func $plain (param i32 i32) (result i32)))
  (import "env" "lean" (func $lean (param i32 i32) (result i32)))
  (import "env" "byname" (func $byname (param i32 i32) (result i32)))
  (memory (export "memory") 1)
  (func (export "loop_plain") (param $n i32) (result i32) (local $acc i32)
    (loop $l
      (local.set $acc (call $plain (local.get $acc) (local.get $n)))
      (local.set $n (i32.sub (local.get $n) (i32.const 1)))
      (br_if $l (local.get $n)))
    (local.get $acc))
  (func (export "loop_lean") (param $n i32) (result i32) (local $acc i32)
    (loop $l
      (local.set $acc (call $lean (local.get $acc) (local.get $n)))
      (local.set $n (i32.sub (local.get $n) (i32.const 1)))
      (br_if $l (local.get $n)))
    (local.get $acc))
  (func (export "loop_byname") (param $n i32) (result i32) (local $acc i32)
    (loop $l
      (local.set $acc (call $byname (local.get $acc) (local.get $n)))
      (local.set $n (i32.sub (local.get $n) (i32.const 1)))
      (br_if $l (local.get $n)))
    (local.get $acc))
  (func (export "loop_none") (param $n i32) (result i32) (local $acc i32)
    (loop $l
      (local.set $acc (i32.add (local.get $acc) (local.get $n)))
      (local.set $n (i32.sub (local.get $n) (i32.const 1)))
      (br_if $l (local.get $n)))
    (local.get $acc)))
"#;

struct Data {
    mem: Option<Memory>,
}

pub fn run(engine: &Engine, n: i32) -> Result<()> {
    let module = Module::new(engine, WAT).map_err(crate::werr)?;
    let mut linker: Linker<Data> = Linker::new(engine);
    linker
        .func_wrap("env", "plain", |a: i32, b: i32| a.wrapping_add(b))
        .map_err(crate::werr)?;
    linker
        .func_wrap("env", "lean", |mut caller: Caller<'_, Data>, a: i32, b: i32| {
            let mem = caller.data().mem.unwrap();
            let d = mem.data_mut(&mut caller);
            let i = (b as usize & 0xfff) * 4;
            let v = i32::from_le_bytes(d[i..i + 4].try_into().unwrap());
            d[i..i + 4].copy_from_slice(&(v ^ a).to_le_bytes());
            a.wrapping_add(v)
        })
        .map_err(crate::werr)?;
    linker
        .func_wrap("env", "byname", |mut caller: Caller<'_, Data>, a: i32, b: i32| {
            let mem = match caller.get_export("memory") {
                Some(Extern::Memory(m)) => m,
                _ => panic!("no memory"),
            };
            let d = mem.data_mut(&mut caller);
            let i = (b as usize & 0xfff) * 4;
            let v = i32::from_le_bytes(d[i..i + 4].try_into().unwrap());
            d[i..i + 4].copy_from_slice(&(v ^ a).to_le_bytes());
            a.wrapping_add(v)
        })
        .map_err(crate::werr)?;
    let mut store = Store::new(engine, Data { mem: None });
    if engine.get_consume_fuel() {
        store.set_fuel(u64::MAX / 4).map_err(crate::werr)?;
    }
    let inst: Instance = linker.instantiate(&mut store, &module).map_err(crate::werr)?;
    store.data_mut().mem = inst.get_memory(&mut store, "memory");
    for name in ["loop_none", "loop_plain", "loop_lean", "loop_byname"] {
        let f = inst.get_typed_func::<i32, i32>(&mut store, name).map_err(crate::werr)?;
        f.call(&mut store, 1000).map_err(crate::werr)?; // warm
        let mut best = f64::MAX;
        for _ in 0..3 {
            let fuel0 = store.get_fuel().unwrap_or(0);
            let t = Instant::now();
            let r = f.call(&mut store, n).map_err(crate::werr)?;
            let dt = t.elapsed().as_secs_f64();
            let used = fuel0.saturating_sub(store.get_fuel().unwrap_or(0));
            best = best.min(dt);
            std::hint::black_box(r);
            if name == "loop_none" && used > 0 {
                eprintln!("  (loop_none: {} fuel per iteration)", used / n as u64);
            }
        }
        println!("{name:12} {:7.2} ns per iteration", best * 1e9 / n as f64);
    }
    Ok(())
}
