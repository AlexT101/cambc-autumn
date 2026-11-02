// fprobe: float min/max (and other float ops) NaN/zero results for every operand pair, scalar and SIMD, with
// runtime and constant operands; then out-of-bounds traps: huge constant offsets, and loads whose value is dropped.
#include <cambc.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <wasm_simd128.h>
#include "draft.h"

#define NOINL __attribute__((noinline))
using u8 = std::uint8_t;
using u32 = std::uint32_t;
using u64 = std::uint64_t;

static u64 F() { return cambc::fuel_remaining(); }
static u32 fb(float f) { u32 b; std::memcpy(&b, &f, 4); return b; }
static u64 db(double f) { u64 b; std::memcpy(&b, &f, 8); return b; }
static float bf(u32 b) { float f; std::memcpy(&f, &b, 4); return f; }
static double bd(u64 b) { double f; std::memcpy(&f, &b, 8); return f; }
static volatile u32 v_zero = 0, v_big = 0xfffffff0u;
static u32 Z = 0;

static const u32 FV[] = {0x7fc00000u, 0x7fc12345u, 0xffc00001u, 0x7f800001u, 0xff812345u, 0x00000000u, 0x80000000u,
                         0x7f800000u, 0xff800000u, 0x3f800000u, 0xc0000000u, 0x00000001u, 0x80000003u, 0x7f7fffffu};
static const u64 DV[] = {0x7ff8000000000000ull, 0x7ff8000000012345ull, 0xfff8000000000001ull, 0x7ff0000000000001ull,
                         0xfff0000000012345ull, 0ull, 0x8000000000000000ull, 0x7ff0000000000000ull, 0xfff0000000000000ull,
                         0x3ff0000000000000ull, 0xc000000000000000ull, 1ull, 0x8000000000000003ull, 0x7fefffffffffffffull};
constexpr int NF = sizeof FV / sizeof FV[0];
constexpr int NP = NF * NF;  // 196 pairs, a multiple of 4

NOINL float smin(float a, float b) { return __builtin_elementwise_minimum(a, b); }
NOINL float smax(float a, float b) { return __builtin_elementwise_maximum(a, b); }
NOINL float sadd(float a, float b) { return a + b; }
NOINL float ssub(float a, float b) { return a - b; }
NOINL float smul(float a, float b) { return a * b; }
NOINL float sdiv(float a, float b) { return a / b; }
NOINL double dmin(double a, double b) { return __builtin_elementwise_minimum(a, b); }
NOINL double dmax(double a, double b) { return __builtin_elementwise_maximum(a, b); }
NOINL double dadd(double a, double b) { return a + b; }
NOINL double dsub(double a, double b) { return a - b; }
NOINL double dmul(double a, double b) { return a * b; }
NOINL double ddiv(double a, double b) { return a / b; }
NOINL v128_t vfmin(v128_t a, v128_t b) { return wasm_f32x4_min(a, b); }
NOINL v128_t vfmax(v128_t a, v128_t b) { return wasm_f32x4_max(a, b); }
NOINL v128_t vfpmin(v128_t a, v128_t b) { return wasm_f32x4_pmin(a, b); }
NOINL v128_t vfpmax(v128_t a, v128_t b) { return wasm_f32x4_pmax(a, b); }
NOINL v128_t vfadd(v128_t a, v128_t b) { return wasm_f32x4_add(a, b); }
NOINL v128_t vfsub(v128_t a, v128_t b) { return wasm_f32x4_sub(a, b); }
NOINL v128_t vfmul(v128_t a, v128_t b) { return wasm_f32x4_mul(a, b); }
NOINL v128_t vfdiv(v128_t a, v128_t b) { return wasm_f32x4_div(a, b); }
NOINL v128_t vdmin(v128_t a, v128_t b) { return wasm_f64x2_min(a, b); }
NOINL v128_t vdmax(v128_t a, v128_t b) { return wasm_f64x2_max(a, b); }
NOINL v128_t vdpmin(v128_t a, v128_t b) { return wasm_f64x2_pmin(a, b); }
NOINL v128_t vdpmax(v128_t a, v128_t b) { return wasm_f64x2_pmax(a, b); }
NOINL v128_t vdadd(v128_t a, v128_t b) { return wasm_f64x2_add(a, b); }
NOINL v128_t vdsub(v128_t a, v128_t b) { return wasm_f64x2_sub(a, b); }
NOINL v128_t vdmul(v128_t a, v128_t b) { return wasm_f64x2_mul(a, b); }
NOINL v128_t vddiv(v128_t a, v128_t b) { return wasm_f64x2_div(a, b); }

static u64 hash(const u32* r, int n) {
    u64 h = 1469598103934665603ull;
    for (int i = 0; i < n; ++i) h = (h ^ r[i]) * 1099511628211ull;
    return h;
}
static void out32(const char* name, const u32* r) { std::printf("%s %016llx\n", name, (unsigned long long)hash(r, NP)); }
static void out64(const char* name, const u64* r) {
    u32 h[2 * NP];
    std::memcpy(h, r, sizeof h);
    std::printf("%s %016llx\n", name, (unsigned long long)hash(h, 2 * NP));
}

static void scalars() {
    float (*fs[])(float, float) = {smin, smax, sadd, ssub, smul, sdiv};
    double (*ds[])(double, double) = {dmin, dmax, dadd, dsub, dmul, ddiv};
    const char* names[] = {"min", "max", "add", "sub", "mul", "div"};
    static u32 r[NP];
    static u64 q[NP];
    char nm[32];
    for (int k = 0; k < 6; ++k) {
        for (int i = 0; i < NP; ++i) r[i] = fb(fs[k](bf(FV[i / NF] + Z), bf(FV[i % NF] + Z)));
        std::snprintf(nm, sizeof nm, "f32.%s", names[k]);
        out32(nm, r);
        for (int i = 0; i < NP; ++i) q[i] = db(ds[k](bd(DV[i / NF] + Z), bd(DV[i % NF] + Z)));
        std::snprintf(nm, sizeof nm, "f64.%s", names[k]);
        out64(nm, q);
    }
    // Direct calls with constant operands (native clang may inline and fold these).
    std::printf("K f32 %08x %08x %08x %08x %08x %08x\n", fb(smin(bf(0x7fc12345u), bf(0xffc00001u))), fb(smin(bf(0xff812345u), 1.0f)),
                fb(smax(bf(0x7f800001u), bf(0xff812345u))), fb(smax(-0.0f, 0.0f)), fb(smin(0.0f, -0.0f)), fb(sadd(bf(0x7fc12345u), bf(0xffc00001u))));
    std::printf("K f64 %016llx %016llx %016llx %016llx\n", (unsigned long long)db(dmin(bd(0x7ff8000000012345ull), bd(0xfff8000000000001ull))),
                (unsigned long long)db(dmax(bd(0x7ff0000000000001ull), -1.0)), (unsigned long long)db(dmax(0.0, -0.0)),
                (unsigned long long)db(dadd(bd(0x7ff8000000012345ull), bd(0xfff8000000000001ull))));
}

static void vectors() {
    v128_t (*fs[])(v128_t, v128_t) = {vfmin, vfmax, vfpmin, vfpmax, vfadd, vfsub, vfmul, vfdiv};
    v128_t (*ds[])(v128_t, v128_t) = {vdmin, vdmax, vdpmin, vdpmax, vdadd, vdsub, vdmul, vddiv};
    const char* names[] = {"min", "max", "pmin", "pmax", "add", "sub", "mul", "div"};
    alignas(16) static u32 a[NP], b[NP], r[NP];
    alignas(16) static u64 c[NP], d[NP], q[NP];
    for (int i = 0; i < NP; ++i) a[i] = FV[i / NF] + Z, b[i] = FV[i % NF] + Z, c[i] = DV[i / NF] + Z, d[i] = DV[i % NF] + Z;
    char nm[32];
    for (int k = 0; k < 8; ++k) {
        for (int i = 0; i < NP; i += 4) wasm_v128_store(r + i, fs[k](wasm_v128_load(a + i), wasm_v128_load(b + i)));
        std::snprintf(nm, sizeof nm, "f32x4.%s", names[k]);
        out32(nm, r);
        for (int i = 0; i < NP; i += 2) wasm_v128_store(q + i, ds[k](wasm_v128_load(c + i), wasm_v128_load(d + i)));
        std::snprintf(nm, sizeof nm, "f64x2.%s", names[k]);
        out64(nm, q);
    }
    const v128_t x = wasm_u32x4_make(0x7fc12345u, 0xffc00001u, 0x80000000u, 0x7f800001u), y = wasm_u32x4_make(0xffc00001u, 0x7fc12345u, 0u, 0xff812345u);
    u32 o[4];
    wasm_v128_store(o, vfmin(x, y));
    std::printf("K f32x4.min %08x %08x %08x %08x\n", o[0], o[1], o[2], o[3]);
    wasm_v128_store(o, vfmax(y, x));
    std::printf("K f32x4.max %08x %08x %08x %08x\n", o[0], o[1], o[2], o[3]);
    wasm_v128_store(o, vdmin(x, y));
    std::printf("K f64x2.min %08x %08x %08x %08x\n", o[0], o[1], o[2], o[3]);
    wasm_v128_store(o, vdmax(y, x));
    std::printf("K f64x2.max %08x %08x %08x %08x\n", o[0], o[1], o[2], o[3]);
}

static void trap(int which) {
    std::printf("T %d start fuel %llu\n", which, (unsigned long long)F());
    std::fflush(stdout);
    u32 r = 0;
    switch (which) {
        case 0: r = *(volatile u32*)(uintptr_t)0xfffffff0u; break;           // huge constant offset, value used
        case 1: *(volatile u64*)(uintptr_t)0xfffffff8u = 1; break;           // huge constant offset store
        case 2: (void)*(volatile u32*)(uintptr_t)v_big; break;               // dropped OOB load
        case 3: (void)*(volatile u8*)(uintptr_t)0xffffff00u; break;          // dropped, huge constant offset
        case 4: (void)*(volatile v128_t*)(uintptr_t)(v_big - 16); break;     // dropped OOB v128 load
        case 5: (void)*(volatile std::uint16_t*)(uintptr_t)(v_big + 15); break;  // dropped, wraps to 0xffffffff
        case 6: (void)*(volatile u64*)(uintptr_t)(v_zero + 8); r = 6; break;  // dropped in-bounds load: survives
        default: break;
    }
    std::printf("T %d survived r %u fuel %llu\n", which, r, (unsigned long long)F());
}

static int stage = 0;
static void play() {
    const u32 R = cambc::round_number();
    Z = R / 1000000u;
    if (R < 20) {
        if (stage++ == 0) {
            const u64 f0 = F();
            scalars();
            vectors();
            std::printf("P floats fuel %llu\n", (unsigned long long)(f0 - F()));
        }
    } else if (R < 27) {
        trap((int)R - 20);
    }
}

int main() {
    while (true) {
        if (cambc::is_draft())
            play_draft();
        else
            play();
        cambc::end_turn();
    }
}
