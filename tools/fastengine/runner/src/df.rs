//! Native distance fields: cambc 4.0.0's Engine::Bitboard::DistanceField (the engine behind
//! DistanceField_Compute[To]WithExpansionCount) reimplemented bit for bit, and its fuzzer
//! (`fastrunner __fuzzdf N [SEED]`; `__fuzzdf bench [REPS]`, `__fuzzdf replay FILE [REPS]` and
//! `__fuzzdf prof FILE [REPS] [OUT]` time it, FILE from FASTRUNNER_DF_RECORD).
//!
//! The engine's semantics (read from its disassembly, confirmed by fuzzing against it):
//! - valid = in-map tiles, open = valid & !walls. Level 0 = roots & open; level d = the 8-neighbour dilation of
//!   level d-1 within open, minus earlier levels (diagonal steps between two blockers are allowed).
//! - dist: every u16 of the field (cw*ch*64; chunk (cx, cy) at cy*cw + cx) is 0xffff except reached tiles, which get
//!   their level. visited, the whole board including padding bits and words, = !(walls | open-but-unreached). The
//!   prior contents of visited and dist are never read.
//! - Levels run d = 1, 2, ...; the search stops after level d if it reached nothing or d == maxd; ComputeTo also
//!   stops before a level once every valid destination is reached (one on a wall never is). count = the last d; 0 if
//!   maxd == 0, no root is open, or (ComputeTo) every destination is a root.
//! - On success the engine leaves its thread-local last error untouched. It rejects overlapping buffers with an
//!   error; those calls (and any geometry we do not handle) go to the engine.
//!
//! Two implementations, chosen at run time (`isa`; FASTRUNNER_DF_ISA=N caps it, 0 = engine only):
//! - maps up to 128 wide, with AVX-512 VBMI/VBMI2/BITALG: a chunk-row is one zmm per 64 columns (a row per qword), so
//!   a level is a few shifts and lane rotations per chunk-row of the frontier's span;
//! - otherwise (AVX2, maps up to 512 wide): the engine's chunk layout, four chunks per vector, visiting only blocks
//!   next to the frontier.
//! Distances are written per chunk with masked stores (AVX-512) or blends (AVX2).
use std::arch::x86_64::*;
use std::cell::UnsafeCell;
use std::sync::OnceLock;

/// FASTRUNNER_NATIVE_DF=0 sends every distance field to the engine.
pub fn enabled() -> bool {
    static E: OnceLock<bool> = OnceLock::new();
    *E.get_or_init(|| std::env::var("FASTRUNNER_NATIVE_DF").map_or(true, |v| v != "0"))
}

/// 0: engine only (no AVX2), 1: AVX2 chunk path, 2: with AVX-512 stores, 3: AVX-512 VBMI plane path where it fits.
fn isa() -> u8 {
    static I: OnceLock<u8> = OnceLock::new();
    *I.get_or_init(|| {
        let max: u8 = std::env::var("FASTRUNNER_DF_ISA").ok().and_then(|v| v.parse().ok()).unwrap_or(3);
        let avx512 = is_x86_feature_detected!("avx512f") && is_x86_feature_detected!("avx512bw") && is_x86_feature_detected!("avx512vl");
        let l = if !(is_x86_feature_detected!("avx2") && is_x86_feature_detected!("bmi1") && is_x86_feature_detected!("popcnt")) {
            0
        } else if !avx512 {
            1
        } else if !(is_x86_feature_detected!("avx512vbmi")
            && is_x86_feature_detected!("avx512vbmi2")
            && is_x86_feature_detected!("avx512bitalg"))
        {
            2
        } else {
            3
        };
        l.min(max)
    })
}

#[derive(Clone, Copy, Debug)]
struct Geo {
    w: usize,
    h: usize,
    cw: usize,
    ch: usize,
    stride: usize,
}

/// Most 4-chunk blocks per chunk-row (maps up to 512 wide).
const MAXB: usize = 16;

/// The board geometry, if the metadata is what the engine accepts and we handle.
fn geo(meta: &[u32; 5], board_bytes: u64, field_bytes: u64) -> Option<Geo> {
    let (w, h) = (meta[0] as i32, meta[1] as i32);
    if w <= 0 || h <= 0 || w > 32 * MAXB as i32 || h > 4096 {
        return None;
    }
    let (w, h) = (w as usize, h as usize);
    let (cw, ch) = ((w + 7) / 8, (h + 7) / 8);
    let stride = (cw + 1) & !1;
    if meta[2] as usize != cw || meta[3] as usize != ch || meta[4] as usize != stride {
        return None;
    }
    if board_bytes != (stride * ch * 8) as u64 || field_bytes != (cw * ch * 128) as u64 {
        return None;
    }
    Some(Geo { w, h, cw, ch, stride })
}

/// Valid tiles of board word (cx, cy).
#[inline(always)]
fn valid_word(g: &Geo, cx: usize, cy: usize) -> u64 {
    let xm = if cx + 1 < g.cw || (cx + 1 == g.cw && g.w % 8 == 0) {
        !0u64
    } else if cx + 1 == g.cw {
        ((1u64 << (g.w % 8)) - 1) * 0x0101_0101_0101_0101
    } else {
        0
    };
    let ym = if cy + 1 < g.ch || g.h % 8 == 0 { !0u64 } else { (1u64 << (8 * (g.h % 8))) - 1 };
    xm & ym
}

#[derive(Clone, Copy)]
#[repr(C, align(32))]
struct V4([u64; 4]);

/// Working state, in an internal layout: chunk-row cy is row cy + 1 of `p` words (rows 0 and ch + 1 and the words
/// around each row's data are zero), chunk (cx, cy) at word (cy + 1) * p + 4 + cx; blocks of 4 words from word 4.
struct Scratch {
    meta: [u32; 5],
    p: usize,
    nb: usize,
    valid: Vec<V4>,
    f: Vec<V4>,
    free: Vec<V4>,
    pend: Vec<V4>,
    /// Per row (bit b = block b): blocks whose horizontal dilation of the frontier is not zero (the frontier's
    /// blocks and those its edge columns spill into), and blocks with tiles still free.
    hn: Vec<u16>,
    hasfree: Vec<u16>,
}

thread_local! {
    static S: UnsafeCell<Scratch> = const {
        UnsafeCell::new(Scratch {
            meta: [0; 5], p: 0, nb: 0, valid: Vec::new(), f: Vec::new(), free: Vec::new(), pend: Vec::new(), hn: Vec::new(), hasfree: Vec::new(),
        })
    };
}

impl Scratch {
    fn layout(&mut self, g: &Geo, meta: &[u32; 5]) {
        if self.meta == *meta {
            return;
        }
        self.meta = *meta;
        self.nb = (g.cw + 3) / 4;
        self.p = 4 * self.nb + 8;
        let n = (g.ch + 2) * self.p / 4;
        for v in [&mut self.valid, &mut self.f, &mut self.free, &mut self.pend] {
            v.clear();
            v.resize(n, V4([0; 4]));
        }
        for v in [&mut self.hn, &mut self.hasfree] {
            v.clear();
            v.resize(g.ch + 2, 0);
        }
        let valid = self.valid.as_mut_ptr() as *mut u64;
        for cy in 0..g.ch {
            for cx in 0..g.cw {
                unsafe { *valid.add((cy + 1) * self.p + 4 + cx) = valid_word(g, cx, cy) };
            }
        }
    }
}

const C0: i64 = 0x0101_0101_0101_0101;
const C7: i64 = 0x8080_8080_8080_8080u64 as i64;
const ROW0: i64 = 0xff;
const ROW7: i64 = 0xff00_0000_0000_0000u64 as i64;

/// Words [4b, 4b + 4) of a board row of `stride` words, without reading past it.
#[inline(always)]
unsafe fn load_board(p: *const u64, b: usize, stride: usize) -> __m256i {
    if 4 * b + 4 <= stride {
        _mm256_loadu_si256(p.add(4 * b) as *const __m256i)
    } else {
        // stride is even: the last block holds two words
        _mm256_maskload_epi64(p.add(4 * b) as *const i64, _mm256_set_epi64x(0, 0, -1, -1))
    }
}

#[inline(always)]
unsafe fn store_board(p: *mut u64, b: usize, stride: usize, v: __m256i) {
    if 4 * b + 4 <= stride {
        _mm256_storeu_si256(p.add(4 * b) as *mut __m256i, v)
    } else {
        _mm256_maskstore_epi64(p.add(4 * b) as *mut i64, _mm256_set_epi64x(0, 0, -1, -1), v)
    }
}

#[inline(always)]
unsafe fn zero(v: __m256i) -> bool {
    _mm256_testz_si256(v, v) != 0
}

#[inline(always)]
unsafe fn or3<const W512: bool>(a: __m256i, b: __m256i, c: __m256i) -> __m256i {
    if W512 {
        _mm256_ternarylogic_epi64(a, b, c, 0xfe)
    } else {
        _mm256_or_si256(a, _mm256_or_si256(b, c))
    }
}

/// m ? a : b, bit by bit.
#[inline(always)]
unsafe fn select<const W512: bool>(m: __m256i, a: __m256i, b: __m256i) -> __m256i {
    if W512 {
        _mm256_ternarylogic_epi64(m, a, b, 0xca)
    } else {
        _mm256_or_si256(_mm256_and_si256(m, a), _mm256_andnot_si256(m, b))
    }
}

/// Horizontal dilation of the frontier block at word j (each tile and its west and east neighbours).
#[inline(always)]
unsafe fn hdil<const W512: bool>(f: *const u64, j: usize) -> __m256i {
    let c = _mm256_load_si256(f.add(j) as *const __m256i);
    let l = _mm256_loadu_si256(f.add(j - 1) as *const __m256i);
    let r = _mm256_loadu_si256(f.add(j + 1) as *const __m256i);
    // tile x - 1 -> x: within the chunk (x > 0) or from the west chunk's column 7; x + 1 -> x likewise
    let e = select::<W512>(_mm256_set1_epi64x(C0), _mm256_srli_epi64(l, 7), _mm256_slli_epi64(c, 1));
    let w = select::<W512>(_mm256_set1_epi64x(C7), _mm256_slli_epi64(r, 7), _mm256_srli_epi64(c, 1));
    or3::<W512>(c, e, w)
}

/// dist[p + i] = d for every set bit i of m (one chunk of 64 tiles).
#[inline(always)]
unsafe fn put_chunk<const W512: bool>(p: *mut u16, m: u64, d: u16) {
    if W512 {
        let dv = _mm512_set1_epi16(d as i16);
        _mm512_mask_storeu_epi16(p as *mut i16, m as u32, dv);
        _mm512_mask_storeu_epi16(p.add(32) as *mut i16, (m >> 32) as u32, dv);
    } else {
        let dv = _mm256_set1_epi16(d as i16);
        let bits = _mm256_setr_epi16(1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, -32768);
        for q in 0..4 {
            let b = (m >> (16 * q)) as u16;
            if b != 0 {
                let sel = _mm256_cmpeq_epi16(_mm256_and_si256(_mm256_set1_epi16(b as i16), bits), bits);
                let a = p.add(16 * q) as *mut __m256i;
                _mm256_storeu_si256(a, _mm256_blendv_epi8(_mm256_loadu_si256(a), dv, sel));
            }
        }
    }
}

/// Write level d for the tiles of block v (words w), whose first chunk is chunk index c of the field.
#[inline(always)]
unsafe fn put_block<const W512: bool>(dist: *mut u16, c: usize, w: &[u64; 4], d: u16) {
    for (k, &m) in w.iter().enumerate() {
        if m != 0 {
            put_chunk::<W512>(dist.add((c + k) * 64), m, d);
        }
    }
}

/// The blocks whose horizontal dilation a new frontier block b (words w) makes non-zero.
#[inline(always)]
fn hn_of(b: usize, w: &[u64; 4]) -> u16 {
    let e0 = ((w[0] & C0 as u64) != 0) as u32;
    let e7 = ((w[3] & C7 as u64) != 0) as u32;
    ((1u32 << b) | (e0 << b >> 1) | (e7 << (b + 1))) as u16
}

/// One row of horizontal dilations (blocks not in `hn` zero), with masks of the blocks holding row 0 / row 7 tiles.
#[inline(always)]
unsafe fn hrow<const W512: bool>(f: *const u64, j0: usize, hn: u16, nb: usize, out: &mut [__m256i; MAXB]) -> (u16, u16) {
    let (mut t0, mut t7) = (0u16, 0u16);
    for b in 0..nb {
        if hn >> b & 1 != 0 {
            let h = hdil::<W512>(f, j0 + 4 * b);
            out[b] = h;
            t0 |= ((_mm256_testz_si256(h, _mm256_set1_epi64x(ROW0)) == 0) as u16) << b;
            t7 |= ((_mm256_testz_si256(h, _mm256_set1_epi64x(ROW7)) == 0) as u16) << b;
        } else {
            out[b] = _mm256_setzero_si256();
        }
    }
    (t0, t7)
}

#[inline(always)]
unsafe fn run_impl<const W512: bool>(
    s: &mut Scratch, g: &Geo, walls: *const u64, roots: *const u64, dests: *const u64, visited: *mut u64, dist: *mut u16, maxd: u16,
) -> u16 {
    let (p, nb) = (s.p, s.nb);
    let nbm: u16 = ((1u32 << nb) - 1) as u16;
    let valid = s.valid.as_ptr() as *const u64;
    let f = s.f.as_mut_ptr() as *mut u64;
    let free = s.free.as_mut_ptr() as *mut u64;
    let pend = s.pend.as_mut_ptr() as *mut u64;
    let hn = s.hn.as_mut_ptr();
    let hasfree = s.hasfree.as_mut_ptr();
    let to = !dests.is_null();
    std::ptr::write_bytes(dist, 0xff, g.cw * g.ch * 64);
    // Level 0. Rows 0 and ch + 1 and the words around the data stay zero from `layout`.
    let (mut lo, mut hi) = (usize::MAX, 0usize);
    let mut npend = 0usize;
    for cy in 0..g.ch {
        let r = cy + 1;
        let (wr, rr) = (walls.add(cy * g.stride), roots.add(cy * g.stride));
        let (mut a, mut hf) = (0u16, 0u16);
        for b in 0..nb {
            let j = r * p + 4 + 4 * b;
            let open = _mm256_andnot_si256(load_board(wr, b, g.stride), _mm256_load_si256(valid.add(j) as *const __m256i));
            let rv = load_board(rr, b, g.stride);
            let f0 = _mm256_and_si256(rv, open);
            let fr = _mm256_andnot_si256(rv, open);
            _mm256_store_si256(f.add(j) as *mut __m256i, f0);
            _mm256_store_si256(free.add(j) as *mut __m256i, fr);
            hf |= (!zero(fr) as u16) << b;
            if !zero(f0) {
                let w: [u64; 4] = std::mem::transmute(f0);
                a |= hn_of(b, &w);
                put_block::<W512>(dist, cy * g.cw + 4 * b, &w, 0);
            }
            if to {
                let dv = _mm256_and_si256(load_board(dests.add(cy * g.stride), b, g.stride), _mm256_load_si256(valid.add(j) as *const __m256i));
                let pv = _mm256_andnot_si256(f0, dv);
                _mm256_store_si256(pend.add(j) as *mut __m256i, pv);
                npend += !zero(pv) as usize;
            }
        }
        *hn.add(r) = a & nbm;
        *hasfree.add(r) = hf;
        if a != 0 {
            lo = lo.min(r);
            hi = r;
        }
    }
    let mut d = 0u16;
    // Horizontal dilations of rows r - 1, r, r + 1, rotated as r advances.
    let mut h = [[_mm256_setzero_si256(); MAXB]; 3];
    if maxd != 0 && lo <= hi {
        loop {
            if to && npend == 0 {
                break;
            }
            d += 1;
            // Rows rs - 1 and re + 1 hold no frontier (or are padding).
            let rs = (lo - 1).max(1);
            let re = (hi + 1).min(g.ch);
            let [hp, hc, hx] = &mut h;
            let (mut hp, mut hc, mut hx) = (hp, hc, hx);
            let (mut t7p, mut hnc) = (0u16, *hn.add(rs));
            for b in 0..nb {
                hp[b] = _mm256_setzero_si256();
            }
            let (_, mut t7c) = hrow::<W512>(f, rs * p + 4, hnc, nb, hc);
            let (mut nlo, mut nhi) = (usize::MAX, 0usize);
            for r in rs..=re {
                let hnx = *hn.add(r + 1);
                let (t0x, t7x) = hrow::<W512>(f, (r + 1) * p + 4, hnx, nb, hx);
                let hfr = *hasfree.add(r);
                let cand = (hnc | t7p | t0x) & hfr;
                // frontier blocks with nothing left to reach: clear them
                let mut m = hnc & !cand;
                while m != 0 {
                    let b = m.trailing_zeros() as usize;
                    m &= m - 1;
                    _mm256_store_si256(f.add(r * p + 4 + 4 * b) as *mut __m256i, _mm256_setzero_si256());
                }
                let (mut a, mut hf) = (0u16, hfr);
                let mut m = cand;
                while m != 0 {
                    let b = m.trailing_zeros() as usize;
                    m &= m - 1;
                    let j = r * p + 4 + 4 * b;
                    let (hd, hcb, hu) = (hp[b], hc[b], hx[b]);
                    let v = or3::<W512>(
                        or3::<W512>(hcb, _mm256_slli_epi64(hcb, 8), _mm256_srli_epi64(hcb, 8)),
                        _mm256_srli_epi64(hd, 56),
                        _mm256_slli_epi64(hu, 56),
                    );
                    let fr = _mm256_load_si256(free.add(j) as *const __m256i);
                    let n = _mm256_and_si256(v, fr);
                    _mm256_store_si256(f.add(j) as *mut __m256i, n);
                    if !zero(n) {
                        let fr = _mm256_andnot_si256(n, fr);
                        _mm256_store_si256(free.add(j) as *mut __m256i, fr);
                        hf &= !((zero(fr) as u16) << b);
                        let w: [u64; 4] = std::mem::transmute(n);
                        a |= hn_of(b, &w);
                        put_block::<W512>(dist, (r - 1) * g.cw + 4 * b, &w, d);
                        if to {
                            let pv = _mm256_load_si256(pend.add(j) as *const __m256i);
                            if _mm256_testz_si256(pv, n) == 0 {
                                let pv = _mm256_andnot_si256(n, pv);
                                _mm256_store_si256(pend.add(j) as *mut __m256i, pv);
                                npend -= zero(pv) as usize;
                            }
                        }
                    }
                }
                *hn.add(r) = a & nbm;
                *hasfree.add(r) = hf;
                if a != 0 {
                    nlo = nlo.min(r);
                    nhi = r;
                }
                (hp, hc, hx) = (hc, hx, hp);
                (t7p, hnc) = (t7c, hnx);
                t7c = t7x;
            }
            if nlo > nhi || d >= maxd {
                break;
            }
            lo = nlo;
            hi = nhi;
        }
    }
    // visited = !(walls | open-but-unreached). (f, free, pend, hn and hasfree are all rewritten by the next call.)
    for cy in 0..g.ch {
        let (wr, vr) = (walls.add(cy * g.stride), visited.add(cy * g.stride));
        for b in 0..nb {
            let fr = _mm256_load_si256(free.add((cy + 1) * p + 4 + 4 * b) as *const __m256i);
            let v = _mm256_xor_si256(_mm256_or_si256(load_board(wr, b, g.stride), fr), _mm256_set1_epi64x(-1));
            store_board(vr, b, g.stride, v);
        }
    }
    d
}

#[target_feature(enable = "avx2,bmi1,popcnt")]
unsafe fn run_avx2(s: &mut Scratch, g: &Geo, wl: *const u64, ro: *const u64, de: *const u64, vi: *mut u64, di: *mut u16, maxd: u16) -> u16 {
    run_impl::<false>(s, g, wl, ro, de, vi, di, maxd)
}

#[target_feature(enable = "avx2,bmi1,popcnt,avx512f,avx512bw,avx512vl")]
unsafe fn run_avx512(s: &mut Scratch, g: &Geo, wl: *const u64, ro: *const u64, de: *const u64, vi: *mut u64, di: *mut u16, maxd: u16) -> u16 {
    run_impl::<true>(s, g, wl, ro, de, vi, di, maxd)
}

// ---- AVX-512 plane path (maps up to 128 wide): chunk-row cy as `np` zmm "planes", plane k holding tiles 64k..64k+63
// of the chunk-row's 8 rows (qword dy = row 8cy + dy). A plane is the 8x8 byte transpose of the chunk-row's words
// 8k..8k+7 (one vpermb either way).

struct PScratch {
    meta: [u32; 5],
    /// Per internal chunk-row r (r = cy + 1; rows 0 and ch + 1 are zero) and plane k: index r * np + k.
    valid: Vec<__m512i>,
    a: Vec<__m512i>,
    b: Vec<__m512i>,
    free: Vec<__m512i>,
    pend: Vec<__m512i>,
    tr: __m512i,
}

thread_local! {
    static PS: UnsafeCell<Option<PScratch>> = const { UnsafeCell::new(None) };
}

impl PScratch {
    #[target_feature(enable = "avx512f")]
    unsafe fn new() -> PScratch {
        let mut t = [0u8; 64];
        for (i, x) in t.iter_mut().enumerate() {
            *x = ((i % 8) * 8 + i / 8) as u8; // byte dy * 8 + cx <- byte cx * 8 + dy
        }
        let tr = _mm512_loadu_si512(t.as_ptr() as *const _);
        PScratch { meta: [0; 5], valid: Vec::new(), a: Vec::new(), b: Vec::new(), free: Vec::new(), pend: Vec::new(), tr }
    }

    #[target_feature(enable = "avx512f")]
    unsafe fn layout(&mut self, g: &Geo, meta: &[u32; 5]) {
        if self.meta == *meta {
            return;
        }
        self.meta = *meta;
        let np = (g.w + 63) / 64;
        let n = (g.ch + 2) * np;
        for v in [&mut self.valid, &mut self.a, &mut self.b, &mut self.free, &mut self.pend] {
            v.clear();
            v.resize(n, _mm512_setzero_si512());
        }
        for cy in 0..g.ch {
            for k in 0..np {
                let bits = (g.w - 64 * k).min(64);
                let m = if bits == 64 { !0u64 } else { (1u64 << bits) - 1 };
                let mut q = [0u64; 8];
                for dy in 0..8 {
                    if 8 * cy + dy < g.h {
                        q[dy] = m;
                    }
                }
                self.valid[(cy + 1) * np + k] = _mm512_loadu_si512(q.as_ptr() as *const _);
            }
        }
    }
}

/// Horizontal dilation of a chunk-row's planes (x: tiles 0-63, y: tiles 64-127 when NP == 2).
#[inline(always)]
unsafe fn hdil_planes<const NP: usize>(x: __m512i, y: __m512i) -> (__m512i, __m512i) {
    if NP == 1 {
        return (_mm512_ternarylogic_epi64(x, _mm512_slli_epi64(x, 1), _mm512_srli_epi64(x, 1), 0xfe), y);
    }
    // tiles 63 and 64 are neighbours across the planes: funnel shifts carry them over
    let hx = _mm512_ternarylogic_epi64(x, _mm512_slli_epi64(x, 1), _mm512_shrdi_epi64(x, y, 1), 0xfe);
    let hy = _mm512_ternarylogic_epi64(y, _mm512_srli_epi64(y, 1), _mm512_shldi_epi64(y, x, 1), 0xfe);
    (hx, hy)
}

/// Write level d for the new tiles of a chunk-row given as chunk words (c0: words 0-7, c1: words 8-15), whose first
/// chunk's distances are at `base`. The words are compressed and taken from lane 0 in turn, not through memory
/// (reloading a 512-bit store's parts stalls on store-to-load forwarding).
#[inline(always)]
unsafe fn put_words(base: *mut u16, c0: __m512i, c1: __m512i, d: u16) {
    let m0 = _mm512_test_epi64_mask(c0, c0);
    let m1 = _mm512_test_epi64_mask(c1, c1);
    if (m0 | m1) == 0 {
        return;
    }
    let dv = _mm512_set1_epi16(d as i16);
    let base = base as *mut i16;
    // vpshufbitqmb takes bit 8L + j of lane L's qword for mask bit 8L + j: a broadcast word comes out as itself
    let sel = _mm512_setr_epi64(
        0x0706_0504_0302_0100,
        0x0f0e_0d0c_0b0a_0908,
        0x1716_1514_1312_1110,
        0x1f1e_1d1c_1b1a_1918,
        0x2726_2524_2322_2120,
        0x2f2e_2d2c_2b2a_2928,
        0x3736_3534_3332_3130,
        0x3f3e_3d3c_3b3a_3938,
    );
    for (m, c, off) in [(m0, c0, 0usize), (m1, c1, 8usize)] {
        let mut m = m as u32;
        let v = _mm512_maskz_compress_epi64(m as u8, c);
        let mut i = _mm512_setzero_si512();
        while m != 0 {
            let cx = m.trailing_zeros() as usize + off;
            m &= m - 1;
            let k = _mm512_bitshuffle_epi64_mask(_mm512_permutexvar_epi64(i, v), sel);
            i = _mm512_add_epi64(i, _mm512_set1_epi64(1));
            _mm512_mask_storeu_epi16(base.add(cx * 64), k as u32, dv);
            _mm512_mask_storeu_epi16(base.add(cx * 64 + 32), (k >> 32) as u32, dv);
        }
    }
}

#[inline(always)]
unsafe fn run_planes_impl<const NP: usize>(
    s: &mut PScratch, g: &Geo, walls: *const u64, roots: *const u64, dests: *const u64, visited: *mut u64, dist: *mut u16, maxd: u16,
) -> u16 {
    let ch = g.ch;
    let (valid, free, pend) = (s.valid.as_ptr(), s.free.as_mut_ptr(), s.pend.as_mut_ptr());
    let (mut a, mut b) = (s.a.as_mut_ptr(), s.b.as_mut_ptr());
    let tr = s.tr;
    let to = !dests.is_null();
    let z = _mm512_setzero_si512();
    // board words 0-7 and 8-15 of a chunk-row (masked loads read nothing past the board)
    let k0: u8 = if g.stride >= 8 { 0xff } else { ((1u32 << g.stride) - 1) as u8 };
    let k1: u8 = if g.stride > 8 { ((1u32 << (g.stride - 8)) - 1) as u8 } else { 0 };
    let planes = |p: *const u64| -> (__m512i, __m512i) {
        let x = _mm512_permutexvar_epi8(tr, _mm512_maskz_loadu_epi64(k0, p as *const _));
        let y = if NP == 2 { _mm512_permutexvar_epi8(tr, _mm512_maskz_loadu_epi64(k1, p.add(8) as *const _)) } else { z };
        (x, y)
    };
    let words = |x: __m512i, y: __m512i| -> (__m512i, __m512i) {
        (_mm512_permutexvar_epi8(tr, x), if NP == 2 { _mm512_permutexvar_epi8(tr, y) } else { z })
    };
    // every distance 0xffff: two 64-byte stores per chunk, inline (a call costs more for small fields)
    let ones = _mm512_set1_epi64(-1);
    for c in 0..g.cw * ch {
        _mm512_storeu_si512(dist.add(64 * c) as *mut _, ones);
        _mm512_storeu_si512(dist.add(64 * c + 32) as *mut _, ones);
    }
    let (mut lo, mut hi) = (usize::MAX, 0usize);
    let mut npend = 0u64;
    for cy in 0..ch {
        let r = cy + 1;
        let o = cy * g.stride;
        let w = planes(walls.add(o));
        let rt = planes(roots.add(o));
        let ds = if to { planes(dests.add(o)) } else { (z, z) };
        let mut f0 = [z; 2];
        let mut any = 0u8;
        for k in 0..NP {
            let (wk, rk, dk) = if k == 0 { (w.0, rt.0, ds.0) } else { (w.1, rt.1, ds.1) };
            let v = *valid.add(r * NP + k);
            let open = _mm512_andnot_si512(wk, v);
            let f = _mm512_and_si512(rk, open);
            *a.add(r * NP + k) = f;
            *free.add(r * NP + k) = _mm512_andnot_si512(rk, open);
            any |= _mm512_test_epi64_mask(f, f);
            if to {
                let p = _mm512_andnot_si512(f, _mm512_and_si512(dk, v));
                *pend.add(r * NP + k) = p;
                if _mm512_test_epi64_mask(p, p) != 0 {
                    let q: [u64; 8] = std::mem::transmute(p);
                    npend += q.iter().map(|x| x.count_ones() as u64).sum::<u64>();
                }
            }
            f0[k] = f;
        }
        if any != 0 {
            lo = lo.min(r);
            hi = r;
        }
        let (c0, c1) = words(f0[0], f0[1]);
        put_words(dist.add(cy * g.cw * 64), c0, c1, 0);
    }
    let mut d = 0u16;
    if maxd != 0 && lo <= hi {
        loop {
            if to && npend == 0 {
                break;
            }
            d += 1;
            let rs = (lo - 1).max(1);
            let re = (hi + 1).min(ch);
            let (mut nlo, mut nhi) = (usize::MAX, 0usize);
            let ld = |r: usize, k: usize| if k < NP { *a.add(r * NP + k) } else { z };
            let (mut hp0, mut hp1) = hdil_planes::<NP>(ld(rs - 1, 0), ld(rs - 1, 1));
            let (mut hc0, mut hc1) = hdil_planes::<NP>(ld(rs, 0), ld(rs, 1));
            for r in rs..=re {
                let (hx0, hx1) = hdil_planes::<NP>(ld(r + 1, 0), ld(r + 1, 1));
                let mut nn = [z; 2];
                let mut any = 0u8;
                for k in 0..NP {
                    let (hp, hc, hx) = if k == 0 { (hp0, hc0, hx0) } else { (hp1, hc1, hx1) };
                    // rows y - 1 and y + 1, from the neighbouring chunk-rows at the edges
                    let v = _mm512_ternarylogic_epi64(_mm512_alignr_epi64(hc, hp, 7), hc, _mm512_alignr_epi64(hx, hc, 1), 0xfe);
                    let i = r * NP + k;
                    let fr = *free.add(i);
                    let n = _mm512_and_si512(v, fr);
                    *b.add(i) = n;
                    *free.add(i) = _mm512_andnot_si512(n, fr);
                    let nz = _mm512_test_epi64_mask(n, n);
                    any |= nz;
                    if to && nz != 0 {
                        let p = *pend.add(i);
                        let hit = _mm512_and_si512(p, n);
                        if _mm512_test_epi64_mask(hit, hit) != 0 {
                            *pend.add(i) = _mm512_andnot_si512(n, p);
                            let q: [u64; 8] = std::mem::transmute(hit);
                            npend -= q.iter().map(|x| x.count_ones() as u64).sum::<u64>();
                        }
                    }
                    nn[k] = n;
                }
                if any != 0 {
                    nlo = nlo.min(r);
                    nhi = r;
                    let (c0, c1) = words(nn[0], nn[1]);
                    put_words(dist.add((r - 1) * g.cw * 64), c0, c1, d);
                }
                (hp0, hp1, hc0, hc1) = (hc0, hc1, hx0, hx1);
            }
            for r in lo..=hi {
                for k in 0..NP {
                    *a.add(r * NP + k) = z;
                }
            }
            std::mem::swap(&mut a, &mut b);
            if nlo > nhi || d >= maxd {
                break;
            }
            lo = nlo;
            hi = nhi;
        }
    }
    // `b` is all zero; keep it as the next call's s.b (`a` is rewritten by the next call's level 0).
    if b != s.b.as_mut_ptr() {
        std::mem::swap(&mut s.a, &mut s.b);
    }
    // visited = !(walls | open-but-unreached)
    for cy in 0..ch {
        let r = cy + 1;
        let (c0, c1) = words(*free.add(r * NP), if NP == 2 { *free.add(r * NP + 1) } else { z });
        let (wp, vp) = (walls.add(cy * g.stride), visited.add(cy * g.stride));
        let w0 = _mm512_maskz_loadu_epi64(k0, wp as *const _);
        _mm512_mask_storeu_epi64(vp as *mut _, k0, _mm512_ternarylogic_epi64(w0, c0, c0, 0x03));
        if k1 != 0 {
            let w1 = _mm512_maskz_loadu_epi64(k1, wp.add(8) as *const _);
            _mm512_mask_storeu_epi64(vp.add(8) as *mut _, k1, _mm512_ternarylogic_epi64(w1, c1, c1, 0x03));
        }
    }
    d
}

#[target_feature(enable = "avx2,bmi1,popcnt,avx512f,avx512bw,avx512vl,avx512vbmi,avx512vbmi2,avx512bitalg")]
unsafe fn run_planes(
    s: &mut PScratch, g: &Geo, wl: *const u64, ro: *const u64, de: *const u64, vi: *mut u64, di: *mut u16, maxd: u16,
) -> u16 {
    if g.w <= 64 {
        run_planes_impl::<1>(s, g, wl, ro, de, vi, di, maxd)
    } else {
        run_planes_impl::<2>(s, g, wl, ro, de, vi, di, maxd)
    }
}

/// DistanceField_ComputeWithExpansionCount (dests null) or ComputeToWithExpansionCount, natively. Returns false,
/// having written nothing, for calls left to the engine; true when done (the engine would have returned 0, and its
/// last error is left as it is).
pub unsafe fn compute(
    meta: &[u32; 5], board_bytes: u64, field_bytes: u64, walls: *const u8, roots: *const u8, dests: *const u8, visited: *mut u8,
    dist: *mut u8, maxd: u16, count: *mut u8,
) -> bool {
    if let Some(r) = recorder() {
        record(r, meta, board_bytes, walls, roots, dests, maxd);
    }
    let isa = isa();
    if isa == 0 {
        return false;
    }
    let Some(g) = geo(meta, board_bytes, field_bytes) else { return false };
    let (bb, fb) = (board_bytes as usize, field_bytes as usize);
    let r = [(walls as usize, bb), (roots as usize, bb), (visited as usize, bb), (dist as usize, fb), (count as usize, 2), (dests as usize, bb)];
    let k = if dests.is_null() { 5 } else { 6 };
    for i in 0..k {
        let (a, n) = r[i];
        if a == 0 || (i != 3 && i != 4 && a % 16 != 0) || (i == 3 && a % 2 != 0) || a.checked_add(n).is_none() {
            return false;
        }
        for &(b, m) in &r[i + 1..k] {
            if a < b + m && b < a + n {
                return false;
            }
        }
    }
    let (w, ro, de, vi, di) = (walls as *const u64, roots as *const u64, dests as *const u64, visited as *mut u64, dist as *mut u16);
    let c = if isa == 3 && g.cw <= 16 {
        PS.with(|s| {
            let s = (*s.get()).get_or_insert_with(|| PScratch::new());
            s.layout(&g, meta);
            run_planes(s, &g, w, ro, de, vi, di, maxd)
        })
    } else {
        S.with(|s| {
            let s = &mut *s.get();
            s.layout(&g, meta);
            if isa >= 2 {
                run_avx512(s, &g, w, ro, de, vi, di, maxd)
            } else {
                run_avx2(s, &g, w, ro, de, vi, di, maxd)
            }
        })
    };
    (count as *mut u16).write_unaligned(c);
    true
}

/// FASTRUNNER_DF_RECORD=FILE: append every call's inputs to FILE (diagnostics: `__fuzzdf replay FILE`).
fn recorder() -> Option<&'static std::sync::Mutex<std::fs::File>> {
    static R: OnceLock<Option<std::sync::Mutex<std::fs::File>>> = OnceLock::new();
    R.get_or_init(|| {
        let p = std::env::var_os("FASTRUNNER_DF_RECORD")?;
        Some(std::sync::Mutex::new(std::fs::OpenOptions::new().create(true).append(true).open(p).ok()?))
    })
    .as_ref()
}

unsafe fn record(
    r: &std::sync::Mutex<std::fs::File>, meta: &[u32; 5], board_bytes: u64, walls: *const u8, roots: *const u8, dests: *const u8,
    maxd: u16,
) {
    use std::io::Write;
    let bb = board_bytes as usize;
    let mut v = Vec::with_capacity(28 + 3 * bb);
    v.extend_from_slice(b"DFR1");
    for m in meta {
        v.extend_from_slice(&m.to_le_bytes());
    }
    v.extend_from_slice(&maxd.to_le_bytes());
    v.extend_from_slice(&[!dests.is_null() as u8, 0]);
    for p in [walls, roots, dests] {
        if !p.is_null() {
            v.extend_from_slice(std::slice::from_raw_parts(p, bb));
        }
    }
    let _ = r.lock().unwrap().write_all(&v);
}

// ---------------------------------------------------------------------------------------------------------------
// Fuzzer and benchmark: `fastrunner __fuzzdf N [SEED]` compares N random calls with the engine's own function,
// `fastrunner __fuzzdf bench [REPS]` times both on every map's walls.

type CompFn = unsafe extern "C" fn(*const u32, *const u8, *const u8, *mut u8, *mut u8, u16, *mut u16) -> i32;
type CompToFn = unsafe extern "C" fn(*const u32, *const u8, *const u8, *const u8, *mut u8, *mut u8, u16, *mut u16) -> i32;
type BoardFn = unsafe extern "C" fn(u64, u64, *mut u8) -> i32;

struct Rng(u64);
impl Rng {
    fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9e3779b97f4a7c15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94d049bb133111eb);
        z ^ (z >> 31)
    }
    fn below(&mut self, n: u64) -> u64 {
        if n == 0 { 0 } else { self.next() % n }
    }
    fn chance(&mut self, p: f64) -> bool {
        ((self.next() >> 11) as f64 / (1u64 << 53) as f64) < p
    }
}

struct MapBoards {
    meta: [u32; 5],
    walls: Vec<u64>,
    blocked: Vec<u64>,
}

fn meta_of(w: u32, h: u32) -> [u32; 5] {
    let cw = (w + 7) / 8;
    let ch = (h + 7) / 8;
    [w, h, cw, ch, (cw + 1) & !1]
}

fn sizes(meta: &[u32; 5]) -> (usize, usize) {
    ((meta[4] * meta[3] * 8) as usize, (meta[2] * meta[3] * 128) as usize)
}

fn load_maps(eng: &crate::engine::Eng) -> anyhow::Result<Vec<MapBoards>> {
    let wallf: BoardFn = unsafe { eng.func("Game_API_Map_GetWallBitboard")? };
    let holef: BoardFn = unsafe { eng.func("Game_API_Map_GetHoleBitboard")? };
    let altarf: BoardFn = unsafe { eng.func("Game_API_Map_GetAltarBitboard")? };
    let mut files = Vec::new();
    for dir in ["maps", "maps/gen"] {
        for e in std::fs::read_dir(dir)? {
            let p = e?.path();
            if p.extension().map_or(false, |x| x == "map26a") {
                files.push(p);
            }
        }
    }
    files.sort();
    let mut out = Vec::new();
    for p in files {
        let bytes = std::fs::read(&p)?;
        let mut g = 0u64;
        if unsafe { (eng.Game_FromMapFileBytes)(bytes.as_ptr(), bytes.len(), &mut g) } != 0 {
            eprintln!("skipping {}: {}", p.display(), eng.last_error());
            continue;
        }
        let mut meta = [0u32; 5];
        unsafe { (eng.Game_API_Map_GetBitboardMetadata)(g, &mut meta) };
        let (bb, _) = sizes(&meta);
        let persp = crate::engine::persp(0, u32::MAX);
        let get = |f: BoardFn| -> Vec<u64> {
            let mut v = vec![0u64; bb / 8 + 2];
            let a = v.as_mut_ptr() as usize;
            let off = ((16 - a % 16) % 16) / 8;
            let rc = unsafe { f(g, persp, (a + off * 8) as *mut u8) };
            assert_eq!(rc, 0, "board read failed for {}", p.display());
            v[off..off + bb / 8].to_vec()
        };
        let walls = get(wallf);
        let holes = get(holef);
        let altars = get(altarf);
        let blocked = walls.iter().zip(&holes).zip(&altars).map(|((a, b), c)| a | b | c).collect();
        unsafe { (eng.Game_Destroy)(g) };
        out.push(MapBoards { meta, walls, blocked });
    }
    Ok(out)
}

/// A 16-byte-aligned buffer of `n` bytes.
struct Buf {
    v: Vec<u128>,
    n: usize,
}
impl Buf {
    fn new(n: usize) -> Buf {
        Buf { v: vec![0u128; n / 16 + 1], n }
    }
    fn p(&mut self) -> *mut u8 {
        self.v.as_mut_ptr() as *mut u8
    }
    fn bytes(&self) -> &[u8] {
        unsafe { std::slice::from_raw_parts(self.v.as_ptr() as *const u8, self.n) }
    }
    fn bytes_mut(&mut self) -> &mut [u8] {
        unsafe { std::slice::from_raw_parts_mut(self.v.as_mut_ptr() as *mut u8, self.n) }
    }
    fn words_mut(&mut self) -> &mut [u64] {
        unsafe { std::slice::from_raw_parts_mut(self.v.as_mut_ptr() as *mut u64, self.n / 8) }
    }
}

/// Valid-tile mask per board word.
fn valid_words(meta: &[u32; 5]) -> Vec<u64> {
    let g = Geo { w: meta[0] as usize, h: meta[1] as usize, cw: meta[2] as usize, ch: meta[3] as usize, stride: meta[4] as usize };
    let mut v = Vec::new();
    for cy in 0..g.ch {
        for cx in 0..g.stride {
            v.push(valid_word(&g, cx, cy));
        }
    }
    v
}

/// A random board: each valid tile set with probability p; padding bits random when `junk`.
fn rand_board(rng: &mut Rng, valid: &[u64], p: f64, junk: bool, out: &mut [u64]) {
    for (i, o) in out.iter_mut().enumerate() {
        let mut x = 0u64;
        if p >= 1.0 {
            x = !0;
        } else if p > 0.0 {
            for b in 0..64 {
                if valid[i] >> b & 1 != 0 && rng.chance(p) {
                    x |= 1 << b;
                }
            }
        }
        x &= valid[i];
        if junk {
            x |= rng.next() & rng.next() & !valid[i];
        }
        *o = x;
    }
}

fn rand_tiles(rng: &mut Rng, valid: &[u64], k: usize, avoid: Option<&[u64]>, out: &mut [u64]) {
    out.iter_mut().for_each(|x| *x = 0);
    let cand: Vec<(usize, u32)> = valid
        .iter()
        .enumerate()
        .flat_map(|(i, &m)| (0..64).filter(move |b| m >> b & 1 != 0).map(move |b| (i, b)))
        .filter(|&(i, b)| avoid.map_or(true, |a| a[i] >> b & 1 == 0))
        .collect();
    if cand.is_empty() {
        return;
    }
    for _ in 0..k {
        let (i, b) = cand[rng.below(cand.len() as u64) as usize];
        out[i] |= 1 << b;
    }
}

struct Case {
    meta: [u32; 5],
    walls: Buf,
    roots: Buf,
    dests: Option<Buf>,
    maxd: u16,
    fill_v: u8,
    fill_d: u8,
}

fn gen_case(rng: &mut Rng, maps: &[MapBoards]) -> Case {
    let real = !maps.is_empty() && rng.chance(0.6);
    let meta = if real {
        maps[rng.below(maps.len() as u64) as usize].meta
    } else {
        let pick = |rng: &mut Rng| -> u32 {
            match rng.below(4) {
                0 => 1 + rng.below(16) as u32,
                1 => 8 * (1 + rng.below(17) as u32) - rng.below(2) as u32,
                _ => 1 + rng.below(136) as u32,
            }
        };
        match rng.below(40) {
            // wider than the plane path (chunk path up to 512, then the engine)
            0 => meta_of(129 + rng.below(400) as u32, 1 + rng.below(64) as u32),
            // taller than we handle (the engine)
            1 if rng.chance(0.1) => meta_of(1 + rng.below(8) as u32, 4090 + rng.below(16) as u32),
            _ => meta_of(pick(rng), pick(rng)),
        }
    };
    let (bb, _) = sizes(&meta);
    let valid = valid_words(&meta);
    let mut walls = Buf::new(bb);
    let junk = rng.chance(0.5);
    if real {
        let m: Vec<&MapBoards> = maps.iter().filter(|m| m.meta == meta).collect();
        let m = m[rng.below(m.len() as u64) as usize];
        let src = if rng.chance(0.5) { &m.walls } else { &m.blocked };
        let ww = walls.words_mut();
        ww.copy_from_slice(src);
        if rng.chance(0.3) {
            let mut extra = vec![0u64; ww.len()];
            let p = [0.01, 0.05, 0.2][rng.below(3) as usize];
            rand_board(rng, &valid, p, false, &mut extra);
            for (a, b) in ww.iter_mut().zip(extra) {
                *a |= b;
            }
        }
        if junk {
            for (a, v) in ww.iter_mut().zip(&valid) {
                *a |= rng.next() & !v;
            }
        }
    } else {
        let p = [0.0, 0.02, 0.1, 0.25, 0.4, 0.55, 0.7, 1.0][rng.below(8) as usize];
        rand_board(rng, &valid, p, junk, walls.words_mut());
    }
    let wcopy: Vec<u64> = walls.words_mut().to_vec();
    let tiles = |rng: &mut Rng, out: &mut [u64], for_dests: bool| {
        let junk = rng.chance(0.2);
        match rng.below(if for_dests { 9 } else { 8 }) {
            0 => out.iter_mut().for_each(|x| *x = 0),
            1 => rand_tiles(rng, &valid, 1, Some(&wcopy), out),
            2 => rand_tiles(rng, &valid, 1, None, out),
            3 => {
                let k = 2 + rng.below(20) as usize;
                rand_tiles(rng, &valid, k, Some(&wcopy), out)
            }
            4 => {
                let p = [0.002, 0.01, 0.05, 0.2, 0.5][rng.below(5) as usize];
                rand_board(rng, &valid, p, false, out)
            }
            5 => rand_board(rng, &valid, 1.0, false, out),
            6 => {
                let k = 1 + rng.below(4) as usize;
                rand_tiles(rng, &valid, k, None, out)
            }
            7 => {
                // a filled rectangle
                out.iter_mut().for_each(|x| *x = 0);
                let (w, h) = (meta[0] as u64, meta[1] as u64);
                let (x0, y0) = (rng.below(w), rng.below(h));
                let (x1, y1) = ((x0 + rng.below(12)).min(w - 1), (y0 + rng.below(12)).min(h - 1));
                for y in y0..=y1 {
                    for x in x0..=x1 {
                        let i = (y as usize / 8) * meta[4] as usize + x as usize / 8;
                        out[i] |= 1 << ((y % 8) * 8 + x % 8);
                    }
                }
            }
            _ => {}
        }
        if junk {
            for (a, v) in out.iter_mut().zip(&valid) {
                *a |= rng.next() & rng.next() & !v;
            }
        }
    };
    let mut roots = Buf::new(bb);
    tiles(rng, roots.words_mut(), false);
    let dests = if rng.chance(0.5) {
        let mut d = Buf::new(bb);
        if rng.chance(0.08) {
            let r: Vec<u64> = roots.words_mut().to_vec();
            d.words_mut().copy_from_slice(&r);
        } else {
            tiles(rng, d.words_mut(), true);
        }
        Some(d)
    } else {
        None
    };
    let maxd = match rng.below(20) {
        0 => 0,
        1 => 1,
        2..=5 => 2 + rng.below(9) as u16,
        6..=9 => 11 + rng.below(290) as u16,
        10 => rng.next() as u16,
        11 => 65534,
        _ => 65535,
    };
    let fills = [0u8, 0xff, 0x5a, 0x00];
    Case { meta, walls, roots, dests, maxd, fill_v: fills[rng.below(4) as usize], fill_d: fills[rng.below(4) as usize] }
}

struct Out {
    rc: i32,
    native: bool,
    visited: Vec<u8>,
    dist: Vec<u8>,
    count: u16,
    err: *const u8,
}

static SENTINEL: [u8; 1] = [0];

unsafe fn run_engine(c: &mut Case, comp: CompFn, compto: CompToFn) -> Out {
    let (bb, fb) = sizes(&c.meta);
    let mut v = Buf::new(bb);
    let mut d = Buf::new(fb);
    v.bytes_mut().fill(c.fill_v);
    d.bytes_mut().fill(c.fill_d);
    let mut count = 0x7777u16;
    let slot = crate::engine::err_slot();
    *slot = SENTINEL.as_ptr();
    let m = c.meta.as_ptr();
    let rc = match &mut c.dests {
        None => comp(m, c.walls.p(), c.roots.p(), v.p(), d.p(), c.maxd, &mut count),
        Some(t) => compto(m, c.walls.p(), c.roots.p(), t.p(), v.p(), d.p(), c.maxd, &mut count),
    };
    Out { rc, native: false, visited: v.bytes().to_vec(), dist: d.bytes().to_vec(), count, err: *slot }
}

unsafe fn run_native(c: &mut Case, comp: CompFn, compto: CompToFn) -> Out {
    let (bb, fb) = sizes(&c.meta);
    let mut v = Buf::new(bb);
    let mut d = Buf::new(fb);
    v.bytes_mut().fill(c.fill_v);
    d.bytes_mut().fill(c.fill_d);
    let mut count = 0x7777u16;
    let slot = crate::engine::err_slot();
    *slot = SENTINEL.as_ptr();
    let tp = c.dests.as_mut().map_or(std::ptr::null_mut(), |t| t.p());
    let ok = compute(&c.meta, bb as u64, fb as u64, c.walls.p(), c.roots.p(), tp, v.p(), d.p(), c.maxd, &mut count as *mut u16 as *mut u8);
    if !ok {
        // the import's fallback
        return run_engine(c, comp, compto);
    }
    Out { rc: 0, native: true, visited: v.bytes().to_vec(), dist: d.bytes().to_vec(), count, err: *slot }
}

/// Overlapping buffers (one board or field sharing bytes with another) must be left to the engine, untouched.
fn overlap_declined(rng: &mut Rng, meta: &[u32; 5]) -> bool {
    let (bb, fb) = sizes(meta);
    let len = [bb, bb, bb, bb, fb, 2];
    let mut off = [0usize; 6];
    let mut at = 0;
    for k in 0..6 {
        off[k] = at;
        at += (len[k] + 15) & !15;
    }
    // move one buffer onto another one's bytes (keeping the engine's alignments)
    let (i, j) = (rng.below(6) as usize, rng.below(6) as usize);
    if i == j {
        return true;
    }
    let align = if i == 4 || i == 5 { 2 } else { 16 };
    off[i] = (off[j] + rng.below(len[j] as u64) as usize) & !(align - 1);
    let mut mem = Buf::new(at + 64);
    mem.bytes_mut().iter_mut().enumerate().for_each(|(k, x)| *x = k as u8);
    let before = mem.bytes().to_vec();
    let p = mem.p();
    let ok = unsafe {
        compute(meta, bb as u64, fb as u64, p.add(off[0]), p.add(off[1]), p.add(off[2]), p.add(off[3]), p.add(off[4]), 65535, p.add(off[5]))
    };
    !ok && mem.bytes() == &before[..]
}

fn first_diff(a: &[u8], b: &[u8]) -> Option<usize> {
    a.iter().zip(b).position(|(x, y)| x != y)
}

pub fn fuzz_main(pos: &[String]) -> anyhow::Result<i32> {
    let eng = crate::engine::load()?;
    let comp: CompFn = unsafe { eng.func("DistanceField_ComputeWithExpansionCount")? };
    let compto: CompToFn = unsafe { eng.func("DistanceField_ComputeToWithExpansionCount")? };
    let maps = load_maps(eng)?;
    eprintln!("{} maps loaded", maps.len());
    if pos.first().map(String::as_str) == Some("replay") {
        let reps: usize = pos.get(2).map_or(Ok(5), |s| s.parse())?;
        return replay(pos.get(1).ok_or_else(|| anyhow::anyhow!("replay FILE [REPS]"))?, comp, compto, reps);
    }
    if pos.first().map(String::as_str) == Some("prof") {
        let reps: usize = pos.get(2).map_or(Ok(20), |s| s.parse())?;
        return prof_replay(pos.get(1).ok_or_else(|| anyhow::anyhow!("prof FILE [REPS] [OUT]"))?, reps, pos.get(3).map_or("df-prof.txt", |s| s.as_str()));
    }
    if pos.first().map(String::as_str) == Some("bench") {
        let reps: usize = pos.get(1).map_or(Ok(20), |s| s.parse())?;
        return bench(&maps, comp, compto, reps);
    }
    let n: u64 = pos.first().map_or(Ok(100_000), |s| s.parse())?;
    let seed: u64 = pos.get(1).map_or(Ok(1), |s| s.parse())?;
    let mut rng = Rng(seed);
    let (mut native, mut fallback, mut bad) = (0u64, 0u64, 0u64);
    let mut by_count = std::collections::BTreeMap::<&str, u64>::new();
    let mut sizes_seen = std::collections::BTreeSet::new();
    let selftest = std::env::var_os("FUZZDF_SELFTEST").is_some();
    let (mut sum_count, mut max_count, mut reached) = (0u64, 0u16, 0u64);
    for i in 0..n {
        let mut c = gen_case(&mut rng, &maps);
        let a = unsafe { run_engine(&mut c, comp, compto) };
        let mut b = unsafe { run_native(&mut c, comp, compto) };
        if i % 50 == 0 && !overlap_declined(&mut rng, &c.meta) {
            bad += 1;
            eprintln!("MISMATCH case {i}: compute accepted overlapping buffers");
        }
        if selftest && b.native && b.count > 3 {
            // FUZZDF_SELFTEST: a planted difference the comparison must catch
            let k = rng.below(b.dist.len() as u64) as usize;
            b.dist[k] ^= 1;
        }
        sizes_seen.insert((c.meta[0], c.meta[1]));
        sum_count += a.count as u64;
        max_count = max_count.max(a.count);
        reached += a.dist.chunks_exact(2).filter(|x| x[0] != 0xff || x[1] != 0xff).count() as u64;
        if b.native {
            native += 1;
        } else {
            fallback += 1;
        }
        *by_count.entry(if a.count == 0 { "count0" } else if a.count == c.maxd { "count=maxd" } else { "count<maxd" }).or_default() += 1;
        let same = a.rc == b.rc && a.visited == b.visited && a.dist == b.dist && a.count == b.count && a.err == b.err;
        if !same {
            bad += 1;
            if bad <= 10 {
                eprintln!(
                    "MISMATCH case {i}: meta {:?} maxd {} to {} rc {}/{} count {}/{} err-same {} visited-diff {:?} dist-diff {:?}",
                    c.meta,
                    c.maxd,
                    c.dests.is_some(),
                    a.rc,
                    b.rc,
                    a.count,
                    b.count,
                    a.err == b.err,
                    first_diff(&a.visited, &b.visited),
                    first_diff(&a.dist, &b.dist)
                );
            }
        }
        if (i + 1) % 50_000 == 0 {
            eprintln!("{} cases, {} native, {} fallback, {} mismatches", i + 1, native, fallback, bad);
        }
    }
    eprintln!(
        "done: {n} cases (seed {seed}), {native} native, {fallback} fallback (engine), {} distinct sizes, {:?}, mean count {:.1}, max count {}, mean reached tiles {:.0}, {bad} mismatches",
        sizes_seen.len(),
        by_count,
        sum_count as f64 / n as f64,
        max_count,
        reached as f64 / n as f64
    );
    Ok(if bad == 0 { 0 } else { 1 })
}

/// Synthetic calls on every map's walls, holes and altars: one root over the whole map; 10 roots; one root to one
/// destination; one root, 6 steps.
fn bench(maps: &[MapBoards], comp: CompFn, compto: CompToFn, reps: usize) -> anyhow::Result<i32> {
    let mut rng = Rng(7);
    let mut by = std::collections::BTreeMap::<String, (u64, f64, f64)>::new();
    let names = ["1 root", "10 roots", "1 root to 1 dest", "1 root, maxd 6"];
    for m in maps {
        let meta = m.meta;
        let (bb, _) = sizes(&meta);
        let valid = valid_words(&meta);
        let area = match meta[0] * meta[1] {
            0..=1600 => "<=1600 tiles",
            1601..=4096 => "<=4096 tiles",
            _ => ">4096 tiles",
        };
        for mode in 0..4 {
            let mut walls = Buf::new(bb);
            walls.words_mut().copy_from_slice(&m.blocked);
            let mut roots = Buf::new(bb);
            rand_tiles(&mut rng, &valid, if mode == 1 { 10 } else { 1 }, Some(&m.blocked), roots.words_mut());
            let dests = (mode == 2).then(|| {
                let mut d = Buf::new(bb);
                rand_tiles(&mut rng, &valid, 1, Some(&m.blocked), d.words_mut());
                d
            });
            let mut c = Case { meta, walls, roots, dests, maxd: if mode == 3 { 6 } else { 65535 }, fill_v: 0, fill_d: 0 };
            let (e, n) = time_pair(&mut c, comp, compto, reps);
            for k in [format!("{:16} {area}", names[mode]), "all".to_string()] {
                let s = by.entry(k).or_default();
                s.0 += 1;
                s.1 += e;
                s.2 += n;
            }
        }
    }
    for (k, (n, e, nn)) in &by {
        eprintln!("{k:32} {n:5} calls  engine {:7.3} us  native {:7.3} us  {:5.2}x", e * 1e6 / *n as f64, nn * 1e6 / *n as f64, e / nn);
    }
    Ok(0)
}

#[inline(always)]
fn tsc() -> u64 {
    unsafe {
        _mm_lfence();
        let t = _rdtsc();
        _mm_lfence();
        t
    }
}

/// TSC ticks per second (measured once).
fn tsc_hz() -> f64 {
    static H: OnceLock<f64> = OnceLock::new();
    *H.get_or_init(|| {
        let (t0, c0) = (std::time::Instant::now(), tsc());
        std::thread::sleep(std::time::Duration::from_millis(50));
        (tsc() - c0) as f64 / t0.elapsed().as_secs_f64()
    })
}

/// Seconds per call of the engine and of `compute` on case c: calls alternate, and each side's time is its fastest
/// of `reps` (interference only ever adds time).
fn time_pair(c: &mut Case, comp: CompFn, compto: CompToFn, reps: usize) -> (f64, f64) {
    let (bb, fb) = sizes(&c.meta);
    let mut v = Buf::new(bb);
    let mut d = Buf::new(fb);
    let mut count = 0u16;
    let tp = c.dests.as_mut().map_or(std::ptr::null_mut(), |t| t.p());
    let (mut e, mut n) = (u64::MAX, u64::MAX);
    for _ in 0..reps {
        unsafe {
            let t0 = tsc();
            if tp.is_null() {
                comp(c.meta.as_ptr(), c.walls.p(), c.roots.p(), v.p(), d.p(), c.maxd, &mut count);
            } else {
                compto(c.meta.as_ptr(), c.walls.p(), c.roots.p(), tp, v.p(), d.p(), c.maxd, &mut count);
            }
            let t1 = tsc();
            compute(&c.meta, bb as u64, fb as u64, c.walls.p(), c.roots.p(), tp, v.p(), d.p(), c.maxd, &mut count as *mut u16 as *mut u8);
            let t2 = tsc();
            e = e.min(t1 - t0);
            n = n.min(t2 - t1);
        }
    }
    (e as f64 / tsc_hz(), n as f64 / tsc_hz())
}

fn read_records(path: &str) -> anyhow::Result<Vec<Case>> {
    let b = std::fs::read(path)?;
    let mut out = Vec::new();
    let mut i = 0;
    while i + 28 <= b.len() {
        anyhow::ensure!(&b[i..i + 4] == b"DFR1", "bad record at {i}");
        let mut meta = [0u32; 5];
        for k in 0..5 {
            meta[k] = u32::from_le_bytes(b[i + 4 + 4 * k..i + 8 + 4 * k].try_into().unwrap());
        }
        let maxd = u16::from_le_bytes([b[i + 24], b[i + 25]]);
        let has = b[i + 26] != 0;
        i += 28;
        let (bb, _) = sizes(&meta);
        let take = |i: &mut usize| {
            let mut x = Buf::new(bb);
            x.bytes_mut().copy_from_slice(&b[*i..*i + bb]);
            *i += bb;
            x
        };
        let walls = take(&mut i);
        let roots = take(&mut i);
        let dests = if has { Some(take(&mut i)) } else { None };
        out.push(Case { meta, walls, roots, dests, maxd, fill_v: 0x5a, fill_d: 0xa5 });
    }
    Ok(out)
}

/// Verify and time recorded calls: engine vs native, each repeated `reps` times.
fn replay(path: &str, comp: CompFn, compto: CompToFn, reps: usize) -> anyhow::Result<i32> {
    let mut cases = read_records(path)?;
    if std::env::var_os("FUZZDF_MAXD0").is_some() {
        cases.iter_mut().for_each(|c| c.maxd = 0);
    }
    let mut bad = 0;
    let mut stats = std::collections::BTreeMap::<String, (u64, f64, f64)>::new();
    let (mut te, mut tn) = (0f64, 0f64);
    let mut counts = Vec::new();
    for c in cases.iter_mut() {
        let a = unsafe { run_engine(c, comp, compto) };
        let b = unsafe { run_native(c, comp, compto) };
        if !(a.rc == b.rc && a.visited == b.visited && a.dist == b.dist && a.count == b.count && a.err == b.err) {
            bad += 1;
        }
        counts.push(a.count);
        let (e, nn) = time_pair(c, comp, compto, reps);
        let tp = c.dests.as_ref().map_or(std::ptr::null(), |t| t.v.as_ptr());
        te += e;
        tn += nn;
        let key = format!(
            "{} {}x{} maxd {}",
            if tp.is_null() { "compute  " } else { "compute_to" },
            c.meta[0],
            c.meta[1],
            match c.maxd {
                0..=3 => "0-3",
                4..=10 => "4-10",
                11..=40 => "11-40",
                41..=65534 => "41+",
                _ => "max",
            }
        );
        let s = stats.entry(key).or_default();
        s.0 += 1;
        s.1 += e;
        s.2 += nn;
    }
    for (k, (n, e, nn)) in &stats {
        eprintln!("{k:36} {n:6} calls  engine {:7.3} us  native {:7.3} us  {:5.2}x  ({:4.1}% of engine time)", e * 1e6 / *n as f64, nn * 1e6 / *n as f64, e / nn, 100.0 * e / te);
    }
    counts.sort();
    let q = |f: f64| counts[((counts.len() - 1) as f64 * f) as usize];
    eprintln!("count quantiles: 10% {} 50% {} 90% {} 99% {} max {}", q(0.1), q(0.5), q(0.9), q(0.99), q(1.0));
    let n = cases.len() as f64;
    eprintln!("{} calls, best of {reps}: engine {:.3} us/call, native {:.3} us/call, {:.2}x; {bad} mismatches", cases.len(), te * 1e6 / n, tn * 1e6 / n, te / tn);
    Ok(if bad == 0 { 0 } else { 1 })
}

static mut SAMPLES: Vec<u64> = Vec::new();

extern "C" fn on_sigprof(_sig: i32, _info: *mut libc::siginfo_t, uc: *mut libc::c_void) {
    unsafe {
        let uc = uc as *mut libc::ucontext_t;
        let rip = (*uc).uc_mcontext.gregs[libc::REG_RIP as usize] as u64;
        let v = &mut *std::ptr::addr_of_mut!(SAMPLES);
        if v.len() < v.capacity() {
            v.push(rip);
        }
    }
}

/// A sampling profile of the native path over recorded calls (ITIMER_PROF; offsets into libfastrunner.so).
fn prof_replay(path: &str, reps: usize, out: &str) -> anyhow::Result<i32> {
    let mut cases = read_records(path)?;
    unsafe {
        (*std::ptr::addr_of_mut!(SAMPLES)).reserve(1 << 22);
        let mut sa: libc::sigaction = std::mem::zeroed();
        sa.sa_sigaction = on_sigprof as *const () as usize;
        sa.sa_flags = libc::SA_SIGINFO | libc::SA_RESTART;
        libc::sigaction(libc::SIGPROF, &sa, std::ptr::null_mut());
        let it = libc::itimerval { it_interval: libc::timeval { tv_sec: 0, tv_usec: 50 }, it_value: libc::timeval { tv_sec: 0, tv_usec: 50 } };
        libc::setitimer(libc::ITIMER_PROF, &it, std::ptr::null_mut());
    }
    let t0 = std::time::Instant::now();
    for c in cases.iter_mut() {
        let (bb, fb) = sizes(&c.meta);
        let mut v = Buf::new(bb);
        let mut d = Buf::new(fb);
        let mut count = 0u16;
        let tp = c.dests.as_mut().map_or(std::ptr::null_mut(), |t| t.p());
        for _ in 0..reps {
            unsafe {
                compute(&c.meta, bb as u64, fb as u64, c.walls.p(), c.roots.p(), tp, v.p(), d.p(), c.maxd, &mut count as *mut u16 as *mut u8);
            }
        }
    }
    let el = t0.elapsed().as_secs_f64();
    unsafe {
        let it = libc::itimerval { it_interval: libc::timeval { tv_sec: 0, tv_usec: 0 }, it_value: libc::timeval { tv_sec: 0, tv_usec: 0 } };
        libc::setitimer(libc::ITIMER_PROF, &it, std::ptr::null_mut());
        let mut info: libc::Dl_info = std::mem::zeroed();
        libc::dladdr(compute as *const libc::c_void, &mut info);
        let base = info.dli_fbase as u64;
        let v = &*std::ptr::addr_of!(SAMPLES);
        let mut s = String::new();
        for &r in v {
            s += &format!("{:x}\n", r.wrapping_sub(base));
        }
        std::fs::write(out, s)?;
        eprintln!("{} samples over {:.3}s ({:.3} us/call)", v.len(), el, el * 1e6 / (cases.len() * reps) as f64);
    }
    Ok(0)
}
