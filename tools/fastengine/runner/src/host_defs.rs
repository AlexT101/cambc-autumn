// WASI and fuel imports of host.rs, included twice (wasmtime linker, native trampolines).
{
    defm!("env", "fuel_remaining", |mut c: Cx<'_>| -> i64 {
        let m = c.data_mut().meter();
        if m.virt {
            m.tick();
        }
        m.remaining() as i64
    });
    defm!("env", "fuel_pause", |mut c: Cx<'_>| -> i32 {
        let m = c.data_mut().meter();
        if !m.debug {
            return 0;
        }
        let d = m.depth;
        m.depth = d.wrapping_add(1);
        if d == 0 {
            m.saved_active = m.active();
            let free = m.interval.saturating_mul(m.quanta).saturating_mul(1000);
            m.set_active(free);
            m.saved_now = m.debug_now();
            m.paused = true;
        }
        1
    });
    defm!("env", "fuel_resume", |mut c: Cx<'_>| {
        let ctx = c.data_mut();
        let m = ctx.meter();
        if !m.debug || m.depth == 0 {
            return;
        }
        m.depth -= 1;
        if m.depth == 0 && m.paused {
            if m.debug_now() == m.saved_now {
                let s = m.saved_active;
                m.set_active(s);
            } else {
                debug_overrun(ctx);
            }
            ctx.meter().paused = false;
        }
    });
    defm!("env", "fuel_adjust", |mut c: Cx<'_>, delta: i64| {
        let m = c.data_mut().meter();
        if !m.debug {
            return;
        }
        if m.depth > 0 {
            m.saved_active = m.saved_active.saturating_add_signed(delta);
        } else {
            let a = m.active().saturating_add_signed(delta);
            m.set_active(a);
        }
    });

    // ---- WASI preview1 subset (wasmtime-wasi 49 p1 semantics for stdio) ----
    let wasi = "wasi_snapshot_preview1";
    defm!(wasi, "environ_sizes_get", |mut c: Cx<'_>, count: i32, size: i32| -> i32 {
        let (mem, _) = split(&mut c);
        if !put_u32(mem, count, 0) || !put_u32(mem, size, 0) {
            return ERRNO_FAULT;
        }
        0
    });
    defm!(wasi, "environ_get", |_c: Cx<'_>, _a: i32, _b: i32| -> i32 { 0 });
    defm!(wasi, "args_sizes_get", |mut c: Cx<'_>, count: i32, size: i32| -> i32 {
        let (mem, _) = split(&mut c);
        // argv = ["bot.wasm"]
        if !put_u32(mem, count, 1) || !put_u32(mem, size, 9) {
            return ERRNO_FAULT;
        }
        0
    });
    defm!(wasi, "args_get", |mut c: Cx<'_>, argv: i32, buf: i32| -> i32 {
        let (mem, _) = split(&mut c);
        let Some(o) = gptr(mem, buf, 9, 1, 1) else { return ERRNO_FAULT };
        mem[o..o + 9].copy_from_slice(b"bot.wasm\0");
        if !put_u32(mem, argv, buf as u32) {
            return ERRNO_FAULT;
        }
        0
    });
    defm!(wasi, "fd_close", |mut c: Cx<'_>, fd: i32| -> i32 {
        let ctx = c.data_mut();
        match fd {
            0..=2 if !ctx.closed[fd as usize] => {
                ctx.closed[fd as usize] = true;
                0
            }
            _ => ERRNO_BADF,
        }
    });
    defm!(wasi, "fd_fdstat_get", |mut c: Cx<'_>, fd: i32, out: i32| -> i32 {
        let (mem, ctx) = split(&mut c);
        let rights: u64 = match fd {
            0 if !ctx.closed[0] => 1 << 1,          // FD_READ
            1 | 2 if !ctx.closed[fd as usize] => 1 << 6, // FD_WRITE
            _ => return ERRNO_BADF,
        };
        let Some(o) = gptr(mem, out, 1, 24, 8) else { return ERRNO_FAULT };
        let r = &mut mem[o..o + 24];
        r.fill(0); // filetype unknown (not a tty), no flags
        r[8..16].copy_from_slice(&rights.to_le_bytes());
        r[16..24].copy_from_slice(&rights.to_le_bytes());
        0
    });
    defm!(wasi, "fd_seek", |mut c: Cx<'_>, fd: i32, _off: i64, _wh: i32, _out: i32| -> i32 {
        let ctx = c.data_mut();
        match fd {
            0..=2 if !ctx.closed[fd as usize] => ERRNO_SPIPE,
            _ => ERRNO_BADF,
        }
    });
    defm!(wasi, "fd_write", |mut c: Cx<'_>, fd: i32, iovs: i32, n: i32, nw: i32| -> i32 {
        let (mem, ctx) = split(&mut c);
        // wasmtime-wasi p1 writes only the first non-empty iovec.
        let Some(io) = gptr(mem, iovs, n.max(0) as u64, 8, 4) else { return ERRNO_FAULT };
        let mut chosen: Option<(usize, usize)> = None;
        for k in 0..n.max(0) as usize {
            let b = u32::from_le_bytes(mem[io + 8 * k..io + 8 * k + 4].try_into().unwrap()) as usize;
            let len = u32::from_le_bytes(mem[io + 8 * k + 4..io + 8 * k + 8].try_into().unwrap()) as usize;
            if len == 0 {
                continue;
            }
            if b.checked_add(len).map_or(true, |e| e > mem.len()) {
                return ERRNO_FAULT;
            }
            chosen = Some((b, len));
            break;
        }
        let (b, len) = chosen.unwrap_or((0, 0));
        if trace_write() {
            let mut v = Vec::new();
            for k in 0..n.max(0) as usize {
                let bb = u32::from_le_bytes(mem[io + 8 * k..io + 8 * k + 4].try_into().unwrap());
                let ll = u32::from_le_bytes(mem[io + 8 * k + 4..io + 8 * k + 8].try_into().unwrap());
                v.push((bb, ll));
            }
            eprintln!("fd_write fd={fd} iovs={v:?} -> {:?}", String::from_utf8_lossy(&mem[b..b + len.min(60)]));
        }
        match fd {
            1 if !ctx.closed[1] => ctx.stdout(&mem[b..b + len]),
            2 if !ctx.closed[2] => {
                // stderr goes to the cli log in cambc, which bundles do not keep.
                ctx.err_total += len;
            }
            _ => return ERRNO_BADF,
        }
        if !put_u32(mem, nw, len as u32) {
            return ERRNO_FAULT;
        }
        0
    });
    defm!(wasi, "proc_exit", |_c: Cx<'_>, code: i32| -> Result<(), wasmtime::Error> {
        Err(wasmtime::Error::msg(format!("guest exited with {code}")))
    });
    // Probed against cambc 4.0.0 (scratchpad probe-wasi2/probe-wfuel): clocks read 0 (resolution 1),
    // random_get fills zeros at 1 fuel per byte, stdin is empty, there are no preopens.
    defm!(wasi, "random_get", |mut c: Cx<'_>, buf: i32, len: i32| -> i32 {
        let (mem, ctx) = split(&mut c);
        let n = len as u32 as usize;
        let Some(o) = gptr(mem, buf, n as u64, 1, 1) else { return ERRNO_FAULT };
        mem[o..o + n].fill(0);
        ctx.meter().charge(n as u64);
        0
    });
    defm!(wasi, "clock_res_get", |mut c: Cx<'_>, _id: i32, out: i32| -> i32 {
        let (mem, _) = split(&mut c);
        if !put_u64(mem, out, 1) { return ERRNO_FAULT }
        0
    });
    defm!(wasi, "clock_time_get", |mut c: Cx<'_>, _id: i32, _prec: i64, out: i32| -> i32 {
        let (mem, _) = split(&mut c);
        if !put_u64(mem, out, 0) { return ERRNO_FAULT }
        0
    });
    defm!(wasi, "fd_read", |mut c: Cx<'_>, fd: i32, _iovs: i32, _n: i32, nread: i32| -> i32 {
        let (mem, ctx) = split(&mut c);
        if fd != 0 || ctx.closed[0] {
            return ERRNO_BADF;
        }
        if !put_u32(mem, nread, 0) { return ERRNO_FAULT }
        0
    });
    defm!(wasi, "fd_filestat_get", |mut c: Cx<'_>, fd: i32, out: i32| -> i32 {
        let (mem, ctx) = split(&mut c);
        if !(0..=2).contains(&fd) || ctx.closed[fd as usize] {
            return ERRNO_BADF;
        }
        let Some(o) = gptr(mem, out, 1, 64, 8) else { return ERRNO_FAULT };
        mem[o..o + 64].fill(0);
        0
    });
    defm!(wasi, "fd_tell", |mut c: Cx<'_>, fd: i32, _out: i32| -> i32 {
        let ctx = c.data_mut();
        match fd {
            0..=2 if !ctx.closed[fd as usize] => ERRNO_SPIPE,
            _ => ERRNO_BADF,
        }
    });
    defm!(wasi, "fd_prestat_get", |_c: Cx<'_>, _fd: i32, _out: i32| -> i32 { ERRNO_BADF });
    defm!(wasi, "fd_fdstat_set_flags", |_c: Cx<'_>, _fd: i32, _flags: i32| -> i32 { ERRNO_BADF });
    defm!(wasi, "sched_yield", |_c: Cx<'_>| -> i32 { 0 });
    defm!(wasi, "path_open", |_c: Cx<'_>, _fd: i32, _df: i32, _p: i32, _pl: i32, _of: i32, _rb: i64, _ri: i64, _ff: i32, _out: i32| -> i32 {
        ERRNO_BADF
    });

}
