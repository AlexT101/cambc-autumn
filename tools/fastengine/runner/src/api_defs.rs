// Import definitions of api.rs, included twice: for wasmtime's linker and as native-mode trampolines
// (`Cx` is the caller type, `def!` the registration).
{
    // ---- metadata_imports ----
    def!("game_settings", |mut c: Cx<'_>, out: i32| -> i32 {
        let (mem, _) = split(&mut c);
        let o = tryp!(gptr(mem, out, 1, 120, 8));
        unsafe { (f().Game_API_GetSettings)(hp(mem, o)) }
    });
    def!("item_info", |mut c: Cx<'_>, item: i32, out: i32| -> i32 {
        let (mem, _) = split(&mut c);
        let o = tryp!(gptr(mem, out, 1, 40, 4));
        unsafe { (f().Game_API_GetItemInfo)(item as u32, hp(mem, o)) }
    });
    def!("consumable_info", |mut c: Cx<'_>, item: i32, out: i32| -> i32 {
        let (mem, _) = split(&mut c);
        let o = tryp!(gptr(mem, out, 1, 8, 4));
        unsafe { (f().Game_API_GetConsumableInfo)(item as u32, hp(mem, o)) }
    });

    // ---- boards (primitives::imports #0-#14) ----
    macro_rules! board {
        ($name:expr, $func:ident) => {
            def!($name, |mut c: Cx<'_>, board: i32| -> i32 {
                let (mem, x) = split(&mut c);
                let b = tryp!(x.bb(mem, board));
                x.charge(x.chunks());
                unsafe { (f().$func)(x.game, x.persp, b) }
            });
        };
    }
    board!("board_camp_occupancy", Game_API_GetCampOccupancy);
    board!("board_awake_camp_occupancy", Game_API_GetAwakeCampOccupancy);
    board!("board_asleep_camp_occupancy", Game_API_GetAsleepCampOccupancy);
    board!("board_ally_occupancy", Game_API_GetAllyOccupancy);
    board!("board_enemy_occupancy", Game_API_GetEnemyOccupancy);
    board!("board_ally_ward_occupancy", Game_API_GetAllyWardOccupancy);
    board!("board_enemy_ward_occupancy", Game_API_GetEnemyWardOccupancy);
    board!("board_ally_altar_lock_occupancy", Game_API_GetAllyAltarLockOccupancy);
    board!("board_enemy_altar_lock_occupancy", Game_API_GetEnemyAltarLockOccupancy);
    board!("board_teleport_occupancy", Game_API_GetTeleportOccupancy);
    board!("board_vision", Game_API_GetVision);
    def!("board_vision_mask", |mut c: Cx<'_>, ty: i32, px: i32, py: i32, board: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let b = tryp!(x.bb(mem, board));
        x.charge(2 * x.chunks());
        unsafe { (f().Game_API_GetVisionMask)(x.game, x.persp, ty, px, py, b) }
    });
    def!("board_ward_vision_mask", |mut c: Cx<'_>, px: i32, py: i32, board: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let b = tryp!(x.bb(mem, board));
        x.charge(2 * x.chunks());
        unsafe { (f().Game_API_GetWardVisionMask)(x.game, x.persp, px, py, b) }
    });
    def!("champion_buff_data", |mut c: Cx<'_>, champ: i32, buf: i32, cap: i32, count: i32| -> i32 {
        let (mem, x) = split(&mut c);
        if cap < 0 {
            return ERR;
        }
        let bo = tryp!(gptr(mem, buf, cap as u64, 12, 4));
        let co = tryp!(gptr(mem, count, 1, 4, 4));
        let mut local = [0u8; 36];
        let mut n = 0u32;
        let r = unsafe {
            (f().Game_API_Champion_GetBuffData)(x.game, x.persp, champ as u32, local.as_mut_ptr(), (cap as u32).min(3), &mut n)
        };
        if r != 0 {
            return r;
        }
        if cap != 0 {
            let len = (n as usize * 12).min(36).min(mem.len() - bo);
            mem[bo..bo + len].copy_from_slice(&local[..len]);
        }
        mem[co..co + 4].copy_from_slice(&n.to_le_bytes());
        0
    });
    def!("bc_get_last_error", |mut c: Cx<'_>, buf: i32, cap: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let s = x.eng.last_error();
        let s = s.as_bytes();
        if cap < 0 || s.len() > 0x7fff_ffff {
            return ERR;
        }
        let n = (cap as usize).min(s.len());
        x.charge((n as u64 + 7) / 8);
        if cap == 0 {
            return s.len() as i32;
        }
        let o = tryp!(gptr(mem, buf, cap as u64, 1, 1));
        mem[o..o + n].copy_from_slice(&s[..n]);
        s.len() as i32
    });
    def!("resign", |mut c: Cx<'_>| -> Result<i32, wasmtime::Error> {
        let x = c.data_mut();
        x.api.actions += 1;
        if !x.is_current_input() {
            return Ok(INVALID_ACTION);
        }
        let r = unsafe { (f().Game_Action_Resign)(x.game) };
        if r != 0 {
            return Ok(r);
        }
        Err(wasmtime::Error::msg(crate::runtime::HOST_EXIT))
    });
    def!("bc_round_number", |mut c: Cx<'_>, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let o = tryp!(gptr(mem, out, 1, 4, 4));
        if x.api.memo {
            let st = x.stamp();
            if x.api.round.0 == st {
                wr32(mem, o, x.api.round.1);
                x.ok_result();
                return 0;
            }
            let mut v = 0u32;
            let r = unsafe { (f().Game_API_GetRoundNumber)(x.game, &mut v) };
            if r == 0 {
                wr32(mem, o, v);
                x.api.round = (st, v);
            }
            return r;
        }
        let mut v = 0u32;
        let r = unsafe { (f().Game_API_GetRoundNumber)(x.game, &mut v) };
        if r == 0 {
            mem[o..o + 4].copy_from_slice(&v.to_le_bytes());
        }
        r
    });
    def!("bc_submitted_gems", |mut c: Cx<'_>, team: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let o = tryp!(gptr(mem, out, 1, 4, 4));
        let mut v = 0u32;
        let r = unsafe { (f().Game_API_GetSubmittedGemCount)(x.game, team as u32, &mut v) };
        if r == 0 {
            mem[o..o + 4].copy_from_slice(&v.to_le_bytes());
        }
        r
    });
    def!("bc_champion_priority", |mut c: Cx<'_>, champ: i32, next: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let o = tryp!(gptr(mem, out, 1, 4, 4));
        if x.api.memo && (champ as u32 as usize) < MEMO_IDS && (next as u32) < 2 {
            let k = champ as usize * 2 + next as usize;
            let st = x.stamp();
            if x.api.prio[k].0 == st {
                wr32(mem, o, x.api.prio[k].1);
                x.ok_result();
                return 0;
            }
            let r = unsafe { (f().Game_API_Champion_GetPriority)(x.game, x.persp, champ as u32, next, hp(mem, o)) };
            if r == 0 {
                x.api.prio[k] = (st, rd_u32(hp(mem, o)));
            }
            return r;
        }
        unsafe { (f().Game_API_Champion_GetPriority)(x.game, x.persp, champ as u32, next, hp(mem, o)) }
    });
    def!("bc_metadata", |mut c: Cx<'_>, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let o = tryp!(gptr(mem, out, 7, 4, 4));
        let mut v = [0u32; 7];
        v[..5].copy_from_slice(&x.meta);
        v[5] = x.board_bytes as u32;
        v[6] = x.field_bytes as u32;
        for (i, w) in v.iter().enumerate() {
            mem[o + 4 * i..o + 4 * i + 4].copy_from_slice(&w.to_le_bytes());
        }
        0
    });
    def!("bc_map_symmetry", |mut c: Cx<'_>, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let o = tryp!(gptr(mem, out, 1, 4, 4));
        unsafe { (f().Game_API_Map_GetSymmetry)(x.game, hp(mem, o)) }
    });
    def!("bc_champion_vision", |mut c: Cx<'_>, champ: i32, board: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let b = tryp!(x.bb(mem, board));
        x.charge(x.chunks());
        if champ as u32 == x.champion {
            return unsafe { (f().Game_API_GetVision)(x.game, x.persp, b) };
        }
        let mut info = [0i32; 11];
        let rc = unsafe { (f().Game_API_Champion_Get)(x.game, x.persp, champ as u32, info.as_mut_ptr() as P) };
        if rc != 0 {
            return rc;
        }
        if (info[2] | info[3]) >= 0 {
            x.charge(x.chunks());
            unsafe { (f().Game_API_GetVisionMask)(x.game, x.persp, info[1], info[2], info[3], b) }
        } else {
            unsafe { (f().Bitboard_Zero)(x.metap(), b) }
        }
    });
    def!("bc_map_mask", |mut c: Cx<'_>, kind: i32, board: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let b = tryp!(x.bb(mem, board));
        x.charge(x.chunks());
        let g = match kind as u32 {
            0 => f().Game_API_Map_GetWallBitboard,
            1 => f().Game_API_Map_GetBushBitboard,
            2 => f().Game_API_Map_GetHoleBitboard,
            3 => f().Game_API_Map_GetAltarBitboard,
            _ => return INVALID_ACTION,
        };
        unsafe { g(x.game, x.persp, b) }
    });
    def!("bc_submit_draft_memory", |mut c: Cx<'_>, data: i32, size: i32| -> i32 {
        let (mem, x) = split(&mut c);
        x.api.actions += 1;
        let mut cur = 0u32;
        if unsafe { (f().Game_API_Draft_GetCurrentTeam)(x.game, &mut cur) } != 0 || cur != x.team {
            return INVALID_ACTION;
        }
        let mut msize = 0u32;
        let rc = unsafe { (f().Game_API_GetDraftMemorySize)(x.game, &mut msize) };
        if rc != 0 {
            return rc;
        }
        if size < 0 {
            return ERR;
        }
        let n = (size as u32).min(msize);
        let o = tryp!(gptr(mem, data, n as u64, 1, 1));
        x.charge((n as u64 + 7) / 8);
        let p = if n == 0 { std::ptr::null() } else { hp(mem, o) as C };
        unsafe { (f().Game_API_WriteDraftMemory)(x.game, x.team, 0, p, n as usize) }
    });

    // ---- bitboard primitives ----
    macro_rules! bb1 {
        ($name:expr, $func:ident) => {
            def!($name, |mut c: Cx<'_>, board: i32| -> i32 {
                let (mem, x) = split(&mut c);
                let b = tryp!(x.bb(mem, board));
                x.charge(x.chunks());
                unsafe { (f().$func)(x.metap(), b) }
            });
        };
    }
    def!("bc_Bitboard_Zero", |mut c: Cx<'_>, board: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let b = tryp!(x.bb(mem, board));
        x.charge(x.chunks());
        if x.api.native {
            unsafe { std::ptr::write_bytes(b, 0, x.board_bytes as usize) };
            return 0;
        }
        unsafe { (f().Bitboard_Zero)(x.metap(), b) }
    });
    bb1!("bc_Bitboard_One", Bitboard_One);
    def!("bc_Bitboard_Print", |mut c: Cx<'_>, board: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let b = tryp!(x.bb(mem, board));
        x.charge(x.chunks());
        unsafe { (f().Bitboard_Print)(x.metap(), b) }
    });
    macro_rules! bbio {
        ($name:expr, $func:ident) => {
            def!($name, |mut c: Cx<'_>, board: i32, bytes: i32, size: i32| -> i32 {
                let (mem, x) = split(&mut c);
                if size < 0 {
                    return ERR;
                }
                let b = tryp!(x.bb(mem, board));
                let o = tryp!(gptr(mem, bytes, size as u64, 1, 1));
                x.charge(x.chunks());
                unsafe { (f().$func)(x.metap(), b as _, hp(mem, o) as _, size as usize) }
            });
        };
    }
    bbio!("bc_Bitboard_ImportRawBuffer", Bitboard_ImportRawBuffer);
    bbio!("bc_Bitboard_ImportLinearBuffer", Bitboard_ImportLinearBuffer);
    bbio!("bc_Bitboard_ExportRawBuffer", Bitboard_ExportRawBuffer);
    bbio!("bc_Bitboard_ExportLinearBuffer", Bitboard_ExportLinearBuffer);
    def!("bc_Bitboard_Test", |mut c: Cx<'_>, board: i32, px: i32, py: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let b = tryp!(x.bb(mem, board));
        let o = tryp!(gptr(mem, out, 1, 4, 4));
        if x.api.native && px >= 0 && py >= 0 && px < x.meta[0] as i32 && py < x.meta[1] as i32 {
            let wi = (py as usize >> 3) * x.meta[4] as usize + (px as usize >> 3);
            let w = unsafe { (b as *const u64).add(wi).read() };
            let v = (w >> ((py & 7) * 8 + (px & 7))) as u32 & 1;
            mem[o..o + 4].copy_from_slice(&v.to_le_bytes());
            return 0;
        }
        unsafe { (f().Bitboard_Test)(x.metap(), b, px, py, hp(mem, o)) }
    });
    def!("bc_Bitboard_Set", |mut c: Cx<'_>, board: i32, px: i32, py: i32, v: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let b = tryp!(x.bb(mem, board));
        if x.api.native && px >= 0 && py >= 0 && px < x.meta[0] as i32 && py < x.meta[1] as i32 {
            let wi = (py as usize >> 3) * x.meta[4] as usize + (px as usize >> 3);
            let bit = ((py & 7) * 8 + (px & 7)) as u32;
            unsafe {
                let p = (b as *mut u64).add(wi);
                *p = (*p & !(1u64 << bit)) | ((v != 0) as u64) << bit;
            }
            return 0;
        }
        unsafe { (f().Bitboard_Set)(x.metap(), b, px, py, v) }
    });
    def!("bc_Bitboard_Toggle", |mut c: Cx<'_>, board: i32, px: i32, py: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let b = tryp!(x.bb(mem, board));
        unsafe { (f().Bitboard_Toggle)(x.metap(), b, px, py) }
    });
    #[allow(unused_macros)]
    macro_rules! bb_out {
        ($name:expr, $func:ident) => {
            def!($name, |mut c: Cx<'_>, board: i32, out: i32| -> i32 {
                let (mem, x) = split(&mut c);
                let b = tryp!(x.bb(mem, board));
                let o = tryp!(gptr(mem, out, 1, 4, 4));
                x.charge(x.chunks());
                unsafe { (f().$func)(x.metap(), b, hp(mem, o)) }
            });
        };
    }
    def!("bc_Bitboard_IsZero", |mut c: Cx<'_>, board: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let b = tryp!(x.bb(mem, board));
        let o = tryp!(gptr(mem, out, 1, 4, 4));
        x.charge(x.chunks());
        if x.api.native {
            let z = unsafe { kern::none(b, std::ptr::null(), &x.api.valid) };
            wr32(mem, o, z as u32);
            return 0;
        }
        unsafe { (f().Bitboard_IsZero)(x.metap(), b, hp(mem, o)) }
    });
    def!("bc_Bitboard_NumSetBits", |mut c: Cx<'_>, board: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let b = tryp!(x.bb(mem, board));
        let o = tryp!(gptr(mem, out, 1, 4, 4));
        x.charge(x.chunks());
        if x.api.native {
            let n = unsafe { kern::count(x.api.popcnt, b, &x.api.valid) };
            wr32(mem, o, n);
            return 0;
        }
        unsafe { (f().Bitboard_NumSetBits)(x.metap(), b, hp(mem, o)) }
    });
    def!("bc_Bitboard_GetSetBits", |mut c: Cx<'_>, board: i32, pos: i32, cap: i32, count: i32| -> i32 {
        let (mem, x) = split(&mut c);
        if cap < 0 {
            return ERR;
        }
        let b = tryp!(x.bb(mem, board));
        let po = tryp!(gptr(mem, pos, 2 * cap as u64, 4, 4));
        let co = tryp!(gptr(mem, count, 1, 4, 4));
        let rc = unsafe { (f().Bitboard_GetSetBits)(x.metap(), b, hp(mem, po), cap as usize, hp(mem, co)) };
        let n = if rc == 0 { rd_u32(hp(mem, co)).min(cap as u32) as u64 } else { 0 };
        x.charge(x.chunks() + n);
        rc
    });
    def!("bc_Bitboard_Not", |mut c: Cx<'_>, board: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let a = tryp!(x.bb(mem, board));
        let r = tryp!(x.bb(mem, out));
        x.charge(x.chunks());
        if x.api.native && same_or_apart(a, r, x.board_bytes) {
            unsafe { kern::not(a, r, (x.board_bytes / 8) as usize) };
            return 0;
        }
        unsafe { (f().Bitboard_Not)(x.metap(), a, r) }
    });
    macro_rules! bb3 {
        ($name:expr, $func:ident, $kern:ident) => {
            def!($name, |mut c: Cx<'_>, a: i32, b: i32, out: i32| -> i32 {
                let (mem, x) = split(&mut c);
                let pa = tryp!(x.bb(mem, a));
                let pb = tryp!(x.bb(mem, b));
                let pr = tryp!(x.bb(mem, out));
                x.charge(x.chunks());
                let n = x.board_bytes;
                if x.api.native && same_or_apart(pa, pb, n) && same_or_apart(pa, pr, n) && same_or_apart(pb, pr, n) {
                    // Boards are 16-byte aligned and a whole number of 16-byte units (even chunk stride).
                    unsafe { kern::$kern(pa, pb, pr, (x.board_bytes / 16) as usize) };
                    return 0;
                }
                unsafe { (f().$func)(x.metap(), pa, pb, pr) }
            });
        };
    }
    bb3!("bc_Bitboard_Union", Bitboard_Union, or);
    bb3!("bc_Bitboard_Intersect", Bitboard_Intersect, and);
    bb3!("bc_Bitboard_Xor", Bitboard_Xor, xor);
    def!("bc_Bitboard_IsEqual", |mut c: Cx<'_>, a: i32, b: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let pa = tryp!(x.bb(mem, a));
        let pb = tryp!(x.bb(mem, b));
        let o = tryp!(gptr(mem, out, 1, 4, 4));
        x.charge(x.chunks());
        if x.api.native && same_or_apart(pa, pb, x.board_bytes) {
            let eq = unsafe { kern::none(pa, pb, &x.api.valid) };
            wr32(mem, o, eq as u32);
            return 0;
        }
        unsafe { (f().Bitboard_IsEqual)(x.metap(), pa, pb, hp(mem, o)) }
    });
    macro_rules! bbshift {
        ($name:expr, $func:ident) => {
            def!($name, |mut c: Cx<'_>, a: i32, out: i32, k: i32| -> i32 {
                let (mem, x) = split(&mut c);
                let pa = tryp!(x.bb(mem, a));
                let pr = tryp!(x.bb(mem, out));
                x.charge(x.chunks());
                unsafe { (f().$func)(x.metap(), pa, pr, k) }
            });
        };
    }
    bbshift!("bc_Bitboard_ShiftRight", Bitboard_ShiftRight);
    bbshift!("bc_Bitboard_ShiftUp", Bitboard_ShiftUp);
    bbshift!("bc_Bitboard_Reflect", Bitboard_Reflect);
    macro_rules! bbdraw {
        ($name:expr, $func:ident) => {
            def!($name, |mut c: Cx<'_>, board: i32, px: i32, py: i32, r: f32| -> i32 {
                let (mem, x) = split(&mut c);
                let b = tryp!(x.bb(mem, board));
                let (mw, mh) = (x.meta[0] as i32, x.meta[1] as i32);
                let rr = draw_radius(r, mw, mh);
                x.charge(span(px, rr, mw).wrapping_mul(span(py, rr, mh)));
                unsafe { (f().$func)(x.metap(), b, px, py, r) }
            });
        };
    }
    bbdraw!("bc_Bitboard_DrawCircle", Bitboard_DrawCircle);
    bbdraw!("bc_Bitboard_DrawChebyshev", Bitboard_DrawChebyshev);
    macro_rules! bbpos {
        ($name:expr, $func:ident) => {
            def!($name, |mut c: Cx<'_>, px: i32, py: i32, ox: i32, oy: i32| -> i32 {
                let (mem, x) = split(&mut c);
                let a = tryp!(gptr(mem, ox, 1, 4, 4));
                let b = tryp!(gptr(mem, oy, 1, 4, 4));
                unsafe { (f().$func)(x.metap(), px, py, hp(mem, a), hp(mem, b)) }
            });
        };
    }
    bbpos!("bc_Bitboard_ReflectHorizontalPosition", Bitboard_ReflectHorizontalPosition);
    bbpos!("bc_Bitboard_ReflectVerticalPosition", Bitboard_ReflectVerticalPosition);
    bbpos!("bc_Bitboard_Rotate180Position", Bitboard_Rotate180Position);
    def!("bc_Bitboard_ReachableMask", |mut c: Cx<'_>, walls: i32, px: i32, py: i32, out: i32, d: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let pw = tryp!(x.bb(mem, walls));
        let pr = tryp!(x.bb(mem, out));
        if d as u32 > 0xffff {
            return INVALID_ACTION;
        }
        let mut count = 0u16;
        let rc = unsafe { (f().Bitboard_ReachableMaskWithExpansionCount)(x.metap(), pw, px, py, pr, d as u16, &mut count) };
        let (mw, mh) = (x.meta[0] as i32, x.meta[1] as i32);
        let fuel = (count as u64 + 2).wrapping_mul(span(px, d as i64, mw)).wrapping_mul(span(py, d as i64, mh)).wrapping_add(x.chunks());
        x.charge(fuel);
        rc
    });
    def!("bc_Bitboard_ShadowCast", |mut c: Cx<'_>, walls: i32, px: i32, py: i32, out: i32, d: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let pw = tryp!(x.bb(mem, walls));
        let pr = tryp!(x.bb(mem, out));
        if d as u32 > 0xffff {
            return INVALID_ACTION;
        }
        let mut scan = 0u32;
        if check_df() {
            sc_check(x, pw, px, py, d as u32);
        }
        // Repeats are served by the engine-level cache (patch.rs), beneath this call.
        let rc = unsafe { (f().Bitboard_ShadowCastWithScanCount)(x.metap(), pw, px, py, pr, d as u32, &mut scan) };
        x.charge((scan as u64 >> 1) + 2 * x.chunks());
        rc
    });
    def!(
        "bc_Bitboard_ReachableMaskWithScratch",
        |mut c: Cx<'_>, walls: i32, px: i32, py: i32, out: i32, d: i32, fr: i32, sc: i32| -> i32 {
            let (mem, x) = split(&mut c);
            let pw = tryp!(x.bb(mem, walls));
            let pr = tryp!(x.bb(mem, out));
            if d as u32 > 0xffff {
                return INVALID_ACTION;
            }
            let pf = tryp!(x.bb(mem, fr));
            let ps = tryp!(x.bb(mem, sc));
            let mut count = 0u16;
            let rc = unsafe {
                (f().Bitboard_ReachableMaskWithScratchAndExpansionCount)(x.metap(), pw, px, py, pr, d as u16, pf, ps, &mut count)
            };
            let (mw, mh) = (x.meta[0] as i32, x.meta[1] as i32);
            let fuel =
                (count as u64 + 2).wrapping_mul(span(px, d as i64, mw)).wrapping_mul(span(py, d as i64, mh)).wrapping_add(x.chunks());
            x.charge(fuel);
            rc
        },
    );

    // ---- distance fields ----
    macro_rules! dfio {
        ($name:expr, $func:ident) => {
            def!($name, |mut c: Cx<'_>, field: i32, bytes: i32, size: i32| -> i32 {
                let (mem, x) = split(&mut c);
                if size < 0 {
                    return ERR;
                }
                let d = tryp!(x.df(mem, field));
                let o = tryp!(gptr(mem, bytes, size as u64, 1, 1));
                x.charge((size as u64 + 7) >> 3);
                unsafe { (f().$func)(x.metap(), d as _, hp(mem, o) as _, size as usize) }
            });
        };
    }
    dfio!("bc_DistanceField_ImportRawBuffer", DistanceField_ImportRawBuffer);
    dfio!("bc_DistanceField_ImportLinearBuffer", DistanceField_ImportLinearBuffer);
    dfio!("bc_DistanceField_ExportRawBuffer", DistanceField_ExportRawBuffer);
    dfio!("bc_DistanceField_ExportLinearBuffer", DistanceField_ExportLinearBuffer);
    def!("bc_DistanceField_Print", |mut c: Cx<'_>, field: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let d = tryp!(x.df(mem, field));
        x.charge((x.field_bytes + 7) / 8);
        unsafe { (f().DistanceField_Print)(x.metap(), d) }
    });
    def!("bc_DistanceField_Copy", |mut c: Cx<'_>, src: i32, dst: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let s = tryp!(x.df(mem, src));
        let d = tryp!(x.df(mem, dst));
        x.charge((x.field_bytes + 7) / 8);
        unsafe { (f().DistanceField_Copy)(x.metap(), s, d) }
    });
    def!("bc_DistanceField_CopyWithMask", |mut c: Cx<'_>, src: i32, mask: i32, dst: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let s = tryp!(x.df(mem, src));
        let m = tryp!(x.bb(mem, mask));
        let d = tryp!(x.df(mem, dst));
        x.charge((x.field_bytes + x.board_bytes + 7) / 8);
        unsafe { (f().DistanceField_CopyWithMask)(x.metap(), s, m, d) }
    });
    def!("bc_DistanceField_Get", |mut c: Cx<'_>, field: i32, px: i32, py: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let d = tryp!(x.df(mem, field));
        let o = tryp!(gptr(mem, out, 1, 2, 2));
        if x.api.native && px >= 0 && py >= 0 && px < x.meta[0] as i32 && py < x.meta[1] as i32 {
            let i = ((py as usize >> 3) * x.meta[2] as usize + (px as usize >> 3)) * 64 + (py as usize & 7) * 8 + (px as usize & 7);
            let v = unsafe { (d as *const u16).add(i).read() };
            mem[o..o + 2].copy_from_slice(&v.to_le_bytes());
            return 0;
        }
        unsafe { (f().DistanceField_Get)(x.metap(), d, px, py, hp(mem, o)) }
    });
    def!("bc_DistanceField_Set", |mut c: Cx<'_>, field: i32, px: i32, py: i32, v: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let d = tryp!(x.df(mem, field));
        if v as u32 > 0xffff {
            return INVALID_ACTION;
        }
        unsafe { (f().DistanceField_Set)(x.metap(), d, px, py, v as u16) }
    });
    def!(
        "bc_DistanceField_ComputeWithExpansionCount",
        |mut c: Cx<'_>, walls: i32, roots: i32, visited: i32, dist: i32, maxd: i32, count: i32| -> i32 {
            let (mem, x) = split(&mut c);
            let pw = tryp!(x.bb(mem, walls));
            let pr = tryp!(x.bb(mem, roots));
            let pv = tryp!(x.bb(mem, visited));
            let pd = tryp!(x.df(mem, dist));
            if maxd as u32 > 0xffff {
                return INVALID_ACTION;
            }
            let co = tryp!(gptr(mem, count, 1, 2, 2));
            if check_df() {
                df_check(x, pw, pr, std::ptr::null_mut(), pv, maxd as u16);
            }
            let rc = if crate::df::enabled()
                && unsafe { crate::df::compute(&x.meta, x.board_bytes, x.field_bytes, pw, pr, std::ptr::null(), pv, pd, maxd as u16, hp(mem, co)) }
            {
                0
            } else {
                unsafe { (f().DistanceField_ComputeWithExpansionCount)(x.metap(), pw, pr, pv, pd, maxd as u16, hp(mem, co)) }
            };
            let e = if rc == 0 { u16::from_le_bytes([mem[co], mem[co + 1]]) as u64 + 16 } else { 16 };
            x.charge(e.wrapping_mul(x.chunks()).min(40000));
            rc
        },
    );
    def!(
        "bc_DistanceField_ComputeToWithExpansionCount",
        |mut c: Cx<'_>, walls: i32, roots: i32, dests: i32, visited: i32, dist: i32, maxd: i32, count: i32| -> i32 {
            let (mem, x) = split(&mut c);
            let pw = tryp!(x.bb(mem, walls));
            let pr = tryp!(x.bb(mem, roots));
            let pt = tryp!(x.bb(mem, dests));
            let pv = tryp!(x.bb(mem, visited));
            let pd = tryp!(x.df(mem, dist));
            if maxd as u32 > 0xffff {
                return INVALID_ACTION;
            }
            let co = tryp!(gptr(mem, count, 1, 2, 2));
            if check_df() {
                df_check(x, pw, pr, pt, pv, maxd as u16);
            }
            let rc = if crate::df::enabled()
                && unsafe { crate::df::compute(&x.meta, x.board_bytes, x.field_bytes, pw, pr, pt, pv, pd, maxd as u16, hp(mem, co)) }
            {
                0
            } else {
                unsafe { (f().DistanceField_ComputeToWithExpansionCount)(x.metap(), pw, pr, pt, pv, pd, maxd as u16, hp(mem, co)) }
            };
            let e = if rc == 0 { u16::from_le_bytes([mem[co], mem[co + 1]]) as u64 + 16 } else { 16 };
            x.charge(e.wrapping_mul(x.chunks()).min(40000));
            rc
        },
    );

    // ---- runner::api::imports ----
    def!("my_team", |c: Cx<'_>| -> i32 { c.data().team as i32 });
    def!("my_champion", |c: Cx<'_>| -> i32 { c.data().champion as i32 });
    // game + perspective + (x, y) -> 4-byte out
    macro_rules! gp_xy {
        ($name:expr, $func:ident) => {
            def!($name, |mut c: Cx<'_>, px: i32, py: i32, out: i32| -> i32 {
                let (mem, x) = split(&mut c);
                let o = tryp!(optr(mem, out, 4, 4));
                unsafe { (f().$func)(x.game, x.persp, px, py, hp(mem, o)) }
            });
        };
    }
    gp_xy!("is_visible", Game_API_InVision);
    gp_xy!("has_camp", Game_API_HasCamp);
    gp_xy!("has_champion", Game_API_HasChampion);
    gp_xy!("camp_at", Game_API_GetCamp);
    gp_xy!("champion_at", Game_API_GetChampion);
    gp_xy!("is_occupied_by_teleport", Game_API_IsOccupiedByTeleport);
    def!("ally_ward_at", |mut c: Cx<'_>, px: i32, py: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let o = tryp!(optr(mem, out, 4, 4));
        unsafe { (f().Game_API_GetAllyWard)(x.game, x.persp, px, py, hp(mem, o) as *mut u32) }
    });
    def!("enemy_ward_at", |mut c: Cx<'_>, px: i32, py: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let o = tryp!(optr(mem, out, 4, 4));
        unsafe { (f().Game_API_GetEnemyWard)(x.game, x.persp, px, py, hp(mem, o) as *mut u32) }
    });
    def!("ward_at", |mut c: Cx<'_>, px: i32, py: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let o = tryp!(optr(mem, out, 4, 4));
        let (mut a, mut e) = (0u32, 0u32);
        let ra = unsafe { (f().Game_API_GetAllyWard)(x.game, x.persp, px, py, &mut a) };
        if ra != 0 && ra != 98 {
            return ra;
        }
        let re = unsafe { (f().Game_API_GetEnemyWard)(x.game, x.persp, px, py, &mut e) };
        let v = match (ra, re) {
            (0, 0) => a.min(e),
            (0, 98) => a,
            (0, r) => return r,
            (_, 0) => e,
            (_, r) => return r,
        };
        mem[o..o + 4].copy_from_slice(&v.to_le_bytes());
        0
    });
    // game + perspective + id -> fixed-size out (inline check)
    macro_rules! gp_id {
        ($name:expr, $func:ident, $size:expr, $align:expr) => {
            def!($name, |mut c: Cx<'_>, id: i32, out: i32| -> i32 {
                let (mem, x) = split(&mut c);
                let o = tryp!(optr(mem, out, $size, $align));
                unsafe { (f().$func)(x.game, x.persp, id as u32, hp(mem, o)) }
            });
        };
    }
    gp_id!("camp_state", Game_API_Camp_GetState, 4, 4);
    gp_id!("camp_group_state", Game_API_CampGroup_GetState, 4, 4);
    gp_id!("camp_group_capture_state", Game_API_CampGroup_GetCaptureState, 8, 4);
    gp_id!("camp_group_cooldown", Game_API_CampGroup_GetCooldown, 4, 4);
    gp_id!("camp", Game_API_Camp_Get, 32, 4);
    gp_id!("champion_identity", Game_API_Champion_GetIdentity, 8, 4);
    gp_id!("ward", Game_API_Ward_Get, 24, 4);
    // Memoised reads: (import, engine fn, memo table, bytes). Only successful reads are kept.
    macro_rules! memo_id {
        ($name:expr, $func:ident, $tab:ident, $n:expr) => {
            def!($name, |mut c: Cx<'_>, id: i32, out: i32| -> i32 {
                let (mem, x) = split(&mut c);
                let o = tryp!(optr(mem, out, $n, 4));
                let k = id as u32 as usize;
                if x.api.memo && k < MEMO_IDS {
                    let st = x.stamp();
                    let e = &mut x.api.$tab[k];
                    // `o..o + $n` is in bounds (optr).
                    if e.0 == st {
                        unsafe { std::ptr::copy_nonoverlapping(e.1.as_ptr(), hp(mem, o), $n) };
                        x.ok_result();
                        return 0;
                    }
                    let r = unsafe { (f().$func)(x.game, x.persp, id as u32, hp(mem, o)) };
                    if r == 0 {
                        let e = &mut x.api.$tab[k];
                        e.0 = st;
                        unsafe { std::ptr::copy_nonoverlapping(hp(mem, o) as C, e.1.as_mut_ptr(), $n) };
                    }
                    return r;
                }
                unsafe { (f().$func)(x.game, x.persp, id as u32, hp(mem, o)) }
            });
        };
    }
    memo_id!("champion_gold", Game_API_Champion_GetGold, gold, 4);
    memo_id!("champion_gems", Game_API_Champion_GetGems, gems, 4);
    memo_id!("champion", Game_API_Champion_Get, champ, 44);
    memo_id!("champion_wards", Game_API_Champion_GetWards, wards, 8);
    memo_id!("bc_champion_channel_time", Game_API_Champion_GetChannelTime, chan, 4);
    gp_id!("champion_can_sell", Game_API_Champion_CanSell, 4, 4);
    gp_id!("champion_restrictions", Game_API_Champion_GetRestrictions, 1, 1);
    macro_rules! memo_cap {
        ($name:expr, $func:ident, $tab:ident, $n:expr, $cap:expr) => {
            def!($name, |mut c: Cx<'_>, id: i32, out: i32| -> i32 {
                let (mem, x) = split(&mut c);
                let o = tryp!(optr(mem, out, $n, 4));
                let k = id as u32 as usize;
                if x.api.memo && k < MEMO_IDS {
                    let st = x.stamp();
                    let e = &mut x.api.$tab[k];
                    if e.0 == st {
                        unsafe { std::ptr::copy_nonoverlapping(e.1.as_ptr(), hp(mem, o), $n) };
                        x.ok_result();
                        return 0;
                    }
                    let r = unsafe { (f().$func)(x.game, x.persp, id as u32, hp(mem, o), $cap) };
                    if r == 0 {
                        let e = &mut x.api.$tab[k];
                        e.0 = st;
                        unsafe { std::ptr::copy_nonoverlapping(hp(mem, o) as C, e.1.as_mut_ptr(), $n) };
                    }
                    return r;
                }
                unsafe { (f().$func)(x.game, x.persp, id as u32, hp(mem, o), $cap) }
            });
        };
    }
    memo_cap!("champion_items", Game_API_Champion_GetItems, items, 336, 84);
    memo_cap!("champion_consumables", Game_API_Champion_GetConsumables, cons, 16, 4);
    def!("champion_cooldown", |mut c: Cx<'_>, id: i32, slot: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let o = tryp!(optr(mem, out, 4, 4));
        let k = (id as u32 as usize) * 2 + (slot as u32 as usize);
        if x.api.memo && (id as u32 as usize) < MEMO_IDS && (slot as u32) < 2 {
            let st = x.stamp();
            if x.api.cool[k].0 == st {
                wr32(mem, o, x.api.cool[k].1);
                x.ok_result();
                return 0;
            }
            let r = unsafe { (f().Game_API_Champion_GetCooldown)(x.game, x.persp, id as u32, slot as u32, hp(mem, o)) };
            if r == 0 {
                x.api.cool[k] = (st, rd_u32(hp(mem, o)));
            }
            return r;
        }
        unsafe { (f().Game_API_Champion_GetCooldown)(x.game, x.persp, id as u32, slot as u32, hp(mem, o)) }
    });
    def!("champion_can_shop", |mut c: Cx<'_>, id: i32, cons: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let o = tryp!(optr(mem, out, 4, 4));
        unsafe { (f().Game_API_Champion_CanShop)(x.game, x.persp, id as u32, cons as u32, hp(mem, o)) }
    });
    macro_rules! ability {
        ($name:expr, $func:ident, $size:expr) => {
            def!($name, |mut c: Cx<'_>, id: i32, slot: i32, out: i32| -> i32 {
                let (mem, x) = split(&mut c);
                let o = tryp!(optr(mem, out, $size, 4));
                unsafe { (f().$func)(x.game, x.persp, id as u32, slot as u32, hp(mem, o)) }
            });
        };
    }
    ability!("champion_ability_damage", Game_API_Champion_GetAbilityDamage, 4);
    ability!("champion_ability_heal", Game_API_Champion_GetAbilityHeal, 4);
    ability!("champion_ability_shield", Game_API_Champion_GetAbilityShield, 4);
    ability!("champion_ability_props", Game_API_Champion_GetAbilityProps, 36);
    macro_rules! ability_vs {
        ($name:expr, $func:ident) => {
            def!($name, |mut c: Cx<'_>, id: i32, slot: i32, t: i32, out: i32| -> i32 {
                let (mem, x) = split(&mut c);
                let o = tryp!(optr(mem, out, 4, 4));
                unsafe { (f().$func)(x.game, x.persp, id as u32, slot as u32, t as u32, hp(mem, o)) }
            });
        };
    }
    ability_vs!("champion_ability_damage_against", Game_API_Champion_GetAbilityDamageAgainst);
    ability_vs!("champion_ability_heal_against", Game_API_Champion_GetAbilityHealAgainst);
    ability_vs!("champion_ability_shield_against", Game_API_Champion_GetAbilityShieldAgainst);
    def!("champion_is_alive", |mut c: Cx<'_>, id: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let o = tryp!(optr(mem, out, 4, 4));
        let k = id as u32 as usize;
        if x.api.memo && k < MEMO_IDS {
            let st = x.stamp();
            if x.api.alive[k].0 == st {
                wr32(mem, o, x.api.alive[k].1);
                x.ok_result();
                return 0;
            }
            let r = unsafe { (f().Game_API_Champion_IsAlive)(x.game, id as u32, hp(mem, o)) };
            if r == 0 {
                x.api.alive[k] = (st, rd_u32(hp(mem, o)));
            }
            return r;
        }
        unsafe { (f().Game_API_Champion_IsAlive)(x.game, id as u32, hp(mem, o)) }
    });
    def!("spawn_region", |mut c: Cx<'_>, team: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let o = tryp!(optr(mem, out, 16, 4));
        unsafe { (f().Game_API_GetSpawnRegion)(x.game, team as u32, hp(mem, o)) }
    });
    def!("draft_num_rounds", |mut c: Cx<'_>, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let o = tryp!(optr(mem, out, 1, 1));
        unsafe { (f().Game_API_Draft_GetNumRounds)(x.game, hp(mem, o)) }
    });
    def!("draft_champion", |mut c: Cx<'_>, ty: i32| -> i32 {
        let x = c.data_mut();
        x.api.actions += 1;
        let mut cur = 0u32;
        if unsafe { (f().Game_API_Draft_GetCurrentTeam)(x.game, &mut cur) } != 0 || cur != x.team || !x.is_current_input() {
            return INVALID_ACTION;
        }
        unsafe { (f().Game_Action_Draft)(x.game, ty) }
    });
    def!("draft_get", |mut c: Cx<'_>, team: i32, round: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        if round as u32 > 255 || team < 0 {
            return OUT_OF_RANGE;
        }
        let o = tryp!(optr(mem, out, 4, 4));
        unsafe { (f().Game_API_Draft_Get)(x.game, team as u32, round as u8, hp(mem, o)) }
    });
    macro_rules! g_out {
        ($name:expr, $func:ident) => {
            def!($name, |mut c: Cx<'_>, out: i32| -> i32 {
                let (mem, x) = split(&mut c);
                let o = tryp!(optr(mem, out, 4, 4));
                unsafe { (f().$func)(x.game, hp(mem, o) as _) }
            });
        };
    }
    g_out!("map_num_camp_groups", Game_API_Map_GetNumCampGroups);
    g_out!("shared_memory_size", Game_API_GetSharedMemorySize);
    g_out!("draft_memory_size", Game_API_GetDraftMemorySize);
    macro_rules! gp_out {
        ($name:expr, $func:ident) => {
            def!($name, |mut c: Cx<'_>, out: i32| -> i32 {
                let (mem, x) = split(&mut c);
                let o = tryp!(optr(mem, out, 4, 4));
                unsafe { (f().$func)(x.game, x.persp, hp(mem, o)) }
            });
        };
    }
    gp_out!("num_allies", Game_API_Champion_GetNumAllies);
    gp_out!("num_enemies", Game_API_Champion_GetNumEnemies);
    macro_rules! g_id {
        ($name:expr, $func:ident, $size:expr) => {
            def!($name, |mut c: Cx<'_>, id: i32, out: i32| -> i32 {
                let (mem, x) = split(&mut c);
                let o = tryp!(optr(mem, out, $size, 4));
                unsafe { (f().$func)(x.game, id as u32, hp(mem, o) as _) }
            });
        };
    }
    g_id!("map_camp_group_num_camps", Game_API_Map_CampGroup_GetNumCamps, 4);
    g_id!("map_camp_group", Game_API_Map_CampGroup_Get, 8);
    g_id!("map_camp_info", Game_API_Map_CampInfo_Get, 12);
    g_id!("map_camp_group_of", Game_API_Map_CampInfo_GetGroup, 4);
    g_id!("bc_camp_group_max_respawn", Game_API_Map_CampGroup_GetRespawnTime, 4);
    g_id!("champion_design", Game_API_Champion_Design, 128);
    g_id!("camp_design", Game_API_Camp_Design, 124);
    def!("map_camp_at", |mut c: Cx<'_>, px: i32, py: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let o = tryp!(optr(mem, out, 4, 4));
        unsafe { (f().Game_API_Map_GetCampAt)(x.game, px, py, hp(mem, o)) }
    });
    def!("map_camp_layout", |mut c: Cx<'_>, words: i32, cap: i32, count: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let v = match camp_layout(x.game) {
            Ok(v) => v,
            Err(r) => return r,
        };
        if cap < 0 {
            return ERR;
        }
        let (start, end) = if cap == 0 {
            (0u64, 0u64)
        } else {
            if words < 0 {
                return ERR;
            }
            (words as u64, words as u64 + cap as u64 * 4)
        };
        if count < 0 {
            return ERR;
        }
        let (len, cn) = (mem.len() as u64, count as u64);
        if end > len || cn + 4 > len || (start < cn + 4 && end > cn) {
            return ERR;
        }
        let base = mem.as_ptr() as u64;
        if ((cap as u64 * 4) | (base + start) | (base + cn)) & 3 != 0 {
            return ERR;
        }
        let n = (cap as usize).min(v.len());
        for (i, wd) in v[..n].iter().enumerate() {
            let o = start as usize + 4 * i;
            mem[o..o + 4].copy_from_slice(&wd.to_le_bytes());
        }
        mem[cn as usize..cn as usize + 4].copy_from_slice(&(v.len() as u32).to_le_bytes());
        x.charge((n - n / 2) as u64);
        0
    });
    def!("bc_champion_ward_positions", |mut c: Cx<'_>, id: i32, buf: i32, cap: i32, count: i32| -> i32 {
        let (mem, x) = split(&mut c);
        // As LIST(8), except the buffer is never nulled and the size-alignment term differs (equivalent).
        let Some((bp, cp, cnt)) = list(mem, buf, cap, count, 8, false) else { return ERR };
        let r = unsafe { (f().Game_API_Champion_GetWardPositions)(x.game, x.persp, id as u32, bp, cp, cnt) };
        if r != 0 {
            return r;
        }
        let n = rd_u32(cnt);
        x.charge(if cp == 0 { 0 } else { n.min(cp) as u64 });
        0
    });
    macro_rules! glist {
        ($name:expr, $e:expr, |$x:ident, $bp:ident, $cp:ident, $cnt:ident| $call:expr) => {
            def!($name, |mut c: Cx<'_>, buf: i32, cap: i32, count: i32| -> i32 {
                let (mem, $x) = split(&mut c);
                let Some(($bp, $cp, $cnt)) = list(mem, buf, cap, count, $e, true) else { return ERR };
                let r = unsafe { $call };
                if r != 0 {
                    return r;
                }
                let n = rd_u32($cnt).min($cp) as u64;
                $x.charge((n * $e + 7) / 8);
                0
            });
        };
    }
    glist!("map_camp_groups", 4, |x, bp, cp, cnt| (f().Game_API_Map_GetCampGroups)(x.game, bp as _, cp, cnt as _));
    glist!("allies", 4, |x, bp, cp, cnt| (f().Game_API_Champion_GetAllies)(x.game, x.persp, bp, cp, cnt));
    glist!("enemies", 4, |x, bp, cp, cnt| (f().Game_API_Champion_GetEnemies)(x.game, x.persp, bp, cp, cnt));
    glist!("wards", 24, |x, bp, cp, cnt| (f().Game_API_GetWards)(x.game, x.persp, bp, cp, cnt));
    glist!("teleports", 28, |x, bp, cp, cnt| (f().Game_API_GetTeleports)(x.game, x.persp, bp, cp, cnt));
    def!("map_camp_group_camps", |mut c: Cx<'_>, g: i32, buf: i32, cap: i32, count: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let Some((bp, cp, cnt)) = list(mem, buf, cap, count, 4, true) else { return ERR };
        let r = unsafe { (f().Game_API_Map_CampGroup_GetCampInfo)(x.game, g as u32, bp as _, cp, cnt as _) };
        if r != 0 {
            return r;
        }
        let n = rd_u32(cnt).min(cp) as u64;
        x.charge((n * 4 + 7) / 8);
        0
    });
    def!("camp_buffs", |mut c: Cx<'_>, camp: i32, buf: i32, cap: i32, count: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let Some((bp, cp, cnt)) = list(mem, buf, cap, count, 12, true) else { return ERR };
        let r = unsafe { (f().Game_API_Camp_GetBuffs)(x.game, x.persp, camp as u32, bp, cp, cnt) };
        if r != 0 {
            return r;
        }
        let n = rd_u32(cnt).min(cp) as u64;
        x.charge((n * 12 + 7) / 8);
        0
    });
    def!("altar_lock", |mut c: Cx<'_>, px: i32, py: i32, team: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let o = tryp!(optr(mem, out, 24, 4));
        unsafe { (f().Game_API_GetAltarLock)(x.game, x.persp, px, py, team as u32, hp(mem, o)) }
    });
    def!("altar_locks", |mut c: Cx<'_>, buf: i32, cap: i32, count: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let Some((bp, cp, cnt)) = list(mem, buf, cap, count, 24, false) else { return ERR };
        let r = visible_altar_locks(x, bp, cp, cnt);
        if r != 0 {
            return r;
        }
        let n = rd_u32(cnt).min(cp) as u64;
        x.charge((n * 24 + 7) / 8);
        0
    });
    def!("teleport_at", |mut c: Cx<'_>, px: i32, py: i32, out: i32| -> i32 {
        let (mem, x) = split(&mut c);
        let o = tryp!(optr(mem, out, 28, 4));
        let r = unsafe { (f().Game_API_GetTeleport)(x.game, x.persp, px, py, hp(mem, o)) };
        if r != 0 {
            return r;
        }
        x.charge(4);
        0
    });
    macro_rules! memio {
        ($name:expr, $func:ident) => {
            def!($name, |mut c: Cx<'_>, off: i32, buf: i32, len: i32| -> i32 {
                let (mem, x) = split(&mut c);
                if len < 0 {
                    return ERR;
                }
                let (start, end) = if len != 0 {
                    if buf < 0 {
                        return ERR;
                    }
                    (buf as u64, buf as u64 + len as u64)
                } else {
                    (0, 0)
                };
                if end > mem.len() as u64 {
                    return ERR;
                }
                x.charge((len as u64 + 7) / 8);
                let p = if len == 0 { std::ptr::null_mut() } else { hp(mem, start as usize) };
                unsafe { (f().$func)(x.game, x.team, off as u32, p as _, len as u32) }
            });
        };
    }
    memio!("read_shared_memory", Game_API_ReadSharedMemory);
    memio!("write_shared_memory", Game_API_WriteSharedMemory);
    memio!("read_draft_memory", Game_API_ReadDraftMemory);
    // Debug draws only reach team-x.debug, which this runner leaves empty (our bots don't draw).
    def!("debug_dot", |c: Cx<'_>, px: i32, py: i32, rgb: i32| -> i32 {
        let x = c.data();
        let (w, h) = (x.meta[0] as i32, x.meta[1] as i32);
        if px < 0 || px >= w || px >= 256 || py < 0 || rgb as u32 > 0xffffff || py > 255 || py >= h {
            return OUT_OF_RANGE;
        }
        0
    });
    def!("debug_line", |c: Cx<'_>, x1: i32, y1: i32, x2: i32, y2: i32, rgb: i32| -> i32 {
        let x = c.data();
        let (w, h) = (x.meta[0] as i32, x.meta[1] as i32);
        let bad = |px: i32, py: i32| px < 0 || px >= w || px >= 256 || py < 0 || py > 255 || py >= h;
        if bad(x1, y1) || bad(x2, y2) || rgb as u32 > 0xffffff {
            return OUT_OF_RANGE;
        }
        0
    });

    // ---- actions ----
    macro_rules! with_result {
        ($name:expr, ($($a:ident),*), |$x:ident, $o:ident| $call:expr) => {
            def!($name, |mut c: Cx<'_>, $($a: i32,)* out: i32| -> i32 {
                let (mem, $x) = split(&mut c);
                let o = tryp!(optr(mem, out, 4, 4));
                mem[o..o + 4].fill(0);
                $x.api.actions += 1;
                if !$x.is_current_input() {
                    return INVALID_ACTION;
                }
                let $o = hp(mem, o);
                unsafe { $call }
            });
        };
    }
    with_result!("move_to_with_result", (px, py), |x, o| (f().Game_Action_Move)(x.game, px, py, o));
    with_result!("cast_with_result", (slot, kind, handle, px, py), |x, o| (f().Game_Action_Cast)(
        x.game,
        slot as u32,
        kind as u32 as u64 | (handle as u32 as u64) << 32,
        px as u32 as u64 | (py as u32 as u64) << 32,
        o
    ));
    with_result!("use_consumable_with_result", (item, px, py), |x, o| (f().Game_Action_UseConsumable)(
        x.game,
        item as u32,
        px as u32 as u64 | (py as u32 as u64) << 32,
        o
    ));
    with_result!("place_ward_with_result", (px, py), |x, o| (f().Game_Action_PlaceWard)(
        x.game,
        px as u32 as u64 | (py as u32 as u64) << 32,
        o
    ));
    macro_rules! action {
        ($name:expr, ($($a:ident),*), |$x:ident| $call:expr) => {
            def!($name, |mut c: Cx<'_>, $($a: i32),*| -> i32 {
                let $x = c.data_mut();
                $x.api.actions += 1;
                if !$x.is_current_input() {
                    return INVALID_ACTION;
                }
                unsafe { $call }
            });
        };
    }
    action!("attack", (kind, handle), |x| (f().Game_Action_Attack)(x.game, kind as u32 as u64 | (handle as u32 as u64) << 32));
    action!("recall", (), |x| (f().Game_Action_Recall)(x.game));
    action!("submit_gems", (px, py), |x| (f().Game_Action_SubmitGems)(x.game, px as u32 as u64 | (py as u32 as u64) << 32));
    action!("cancel_channel", (), |x| (f().Game_Action_CancelChannel)(x.game));
    action!("sell", (item), |x| (f().Game_Action_Sell)(x.game, item as u32));
    action!("buy_item", (item, n), |x| (f().Game_Action_BuyItem)(x.game, item as u32, n as u32));
    action!("buy_consumable", (item), |x| (f().Game_Action_BuyConsumable)(x.game, item as u32));
    action!("set_priority", (p), |x| (f().Game_Action_SetPriority)(x.game, p));
}
