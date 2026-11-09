// probe-fuel-arb: fuel prices of operations that are cheap in fuel but not in CPU, and the start-up price of a
// large table compiled into the binary.
// Run: tools/probes/probe-fuel-arb/run.sh OUTDIR (makes probe-fuel-arb-big/src/data.bin first). By hand (release, as on the platform):
//   cambc run tools/probes/probe-fuel-arb tools/probes/probe-fuel-arb-big --map 00corners --rounds 3 --release --fuel 50000000 -o <dir>
// (the op lines need --fuel above ~400k; the start lines are the real budget's at the default --fuel)
// probe-fuel-arb-big is this source with BIG_TABLE 1 (an 8 MiB #embed table). PROBE start lines give each
// instance's fuel_remaining at its first statement: draft (budget 10M) and each champion (budget 200k).
// PROBE op lines (round 2) give fuel per iteration, minus an empty loop's.
#include <cambc.h>
#include <wasm_simd128.h>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>

#ifndef BIG_TABLE
#define BIG_TABLE 0
#endif
#if BIG_TABLE
alignas(16) static const unsigned char big[] = {
#embed "data.bin"
};
#endif

static std::uint64_t F() { return cambc::fuel_remaining(); }
constexpr int N = 2000;
volatile std::uint64_t v64 = 1234567891234ull, d64 = 37;
volatile double vd = 12345.678;
volatile float vf = 1.2345f;
volatile int vi = 3;
alignas(16) static unsigned char lut[256], src[65536], dst[65536];
static std::uint32_t lut32[1 << 20]; // 4 MiB, zero at start (bss)

template <class Body> static double per(Body body, int n = N) {
    const auto a = F();
    for (int i = 0; i < n; ++i) body(i);
    const auto b = F();
    return static_cast<double>(a - b) / n;
}
[[gnu::noinline]] static int empty_fn(int x) { return x + 1; }

static void measure() {
    for (int i = 0; i < 256; ++i) lut[i] = static_cast<unsigned char>(i * 37 + 11);
    const double empty = per([](int) { v64 = v64; });
    std::printf("PROBE op empty_loop=%.2f\n", empty);
    std::printf("PROBE op add64=%.2f mul64=%.2f div64=%.2f popcnt64=%.2f\n",
        per([](int i) { v64 = v64 + std::uint64_t(i); }) - empty, per([](int) { v64 = v64 * d64; }) - empty,
        per([](int) { v64 = v64 / d64 + 1234567891234ull; }) - empty, per([](int) { v64 = __builtin_popcountll(v64) + v64; }) - empty);
    std::printf("PROBE op f64_add=%.2f f64_div=%.2f f64_sqrt=%.2f f32_sqrt=%.2f\n",
        per([](int) { vd = vd + 1.5; }) - empty, per([](int) { vd = vd / 1.0001; }) - empty,
        per([](int) { vd = std::sqrt(vd) + 100.0; }) - empty, per([](int) { vf = std::sqrt(vf) + 1.0f; }) - empty);
    std::printf("PROBE op powf=%.2f expf=%.2f logf=%.2f sinf=%.2f atan2f=%.2f\n",
        per([](int) { vf = std::pow(vf, 1.37f) + 0.5f; }, 200) - empty, per([](int) { vf = std::exp(vf * 0.01f) ; }, 200) - empty,
        per([](int) { vf = std::log(vf + 2.0f); }, 200) - empty, per([](int) { vf = std::sin(vf) + 1.0f; }, 200) - empty,
        per([](int) { vf = std::atan2(vf, 1.3f) + 1.0f; }, 200) - empty);
    std::printf("PROBE op call_noinline=%.2f\n", per([](int) { vi = empty_fn(vi); }) - empty);
    // 16 byte-table lookups: scalar vs one i8x16.swizzle (16-entry table) vs 256-entry via 16 swizzles is not tried.
    std::printf("PROBE op lut16_scalar=%.2f lut16_swizzle=%.2f\n",
        per([](int i) { unsigned s = 0; for (int k = 0; k < 16; ++k) s += lut[(i + k) & 15]; vi = s; }) - empty,
        per([](int i) {
            const v128_t t = wasm_v128_load(lut);
            const v128_t idx = wasm_i8x16_add(wasm_i8x16_splat(static_cast<int8_t>(i)), wasm_i8x16_make(0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15));
            const v128_t r = wasm_i8x16_swizzle(t, wasm_v128_and(idx, wasm_i8x16_splat(15)));
            vi = wasm_i32x4_extract_lane(r, 0); }) - empty);
    // Bulk memory: 64 KiB copy and zero.
    std::printf("PROBE op memcpy64k=%.0f memset64k=%.0f v128copy64k=%.0f v128copy64k_x4=%.0f\n",
        per([](int i) { std::memcpy(dst, src, sizeof src); vi = dst[i & 1023]; }, 5) - empty,
        per([](int i) { std::memset(dst, i, sizeof dst); vi = dst[i & 1023]; }, 5) - empty,
        per([](int i) { for (int k = 0; k < 65536; k += 16) wasm_v128_store(dst + k, wasm_v128_load(src + k)); vi = dst[i & 1023]; }, 5) - empty,
        per([](int i) {
            _Pragma("clang loop unroll(disable)")
            for (int k = 0; k < 65536; k += 64) {
                const v128_t a = wasm_v128_load(src + k), b = wasm_v128_load(src + k + 16), c = wasm_v128_load(src + k + 32), d = wasm_v128_load(src + k + 48);
                wasm_v128_store(dst + k, a); wasm_v128_store(dst + k + 16, b); wasm_v128_store(dst + k + 32, c); wasm_v128_store(dst + k + 48, d);
            }
            vi = dst[i & 1023]; }, 5) - empty);
    const auto g0 = F();
    const auto pages = __builtin_wasm_memory_grow(0, 16); // 1 MiB of fresh zero pages
    const auto g1 = F();
    std::printf("PROBE op grow1MiB=%llu ok=%d\n", static_cast<unsigned long long>(g0 - g1), pages >= 0);
    // A random read from a 4 MiB table vs a 256-byte one: both one load.
    std::printf("PROBE op load_small=%.2f load_4MiB=%.2f\n",
        per([](int i) { vi = lut[(i * 2654435761u) & 255]; }) - empty,
        per([](int i) { vi = static_cast<int>(lut32[(i * 2654435761u) & ((1u << 20) - 1)]); }) - empty);
    {
        // A full-map distance field: host get per tile vs one export then local reads.
        const auto& walls = cambc::map::walls();
        cambc::bitboard roots;
        roots.set(cambc::self().position());
        cambc::bitboard visited;
        cambc::distance_field f;
        const auto c0 = F();
        f.compute_with_expansion_count(walls, roots, visited);
        const auto c1 = F();
        static std::uint16_t lin[100 * 100];
        const std::size_t n = cambc::distance_field::linear_buffer_size() / 2;
        const auto e0 = F();
        f.export_linear_buffer({lin, n});
        const auto e1 = F();
        const int W = cambc::map::width(), H = cambc::map::height();
        std::uint16_t v = 0;
        const double get = per([&](int i) { std::uint16_t r; (void)cambc::detail::sdk_DistanceField_Get(f.ptr(), i % W, (i / W) % H, &r); v ^= r; });
        const double local = per([&](int i) { v ^= lin[(i % W) + ((i / W) % H) * W]; });
        int mism = 0;
        for (int y = 0; y < H; ++y) for (int x = 0; x < W; ++x) { std::uint16_t r; (void)cambc::detail::sdk_DistanceField_Get(f.ptr(), x, y, &r); mism += r != lin[x + y * W]; }
        std::printf("PROBE op map=%dx%d field_compute=%llu field_export=%llu get=%.2f local=%.2f mismatches=%d v=%u\n", W, H,
            static_cast<unsigned long long>(c0 - c1), static_cast<unsigned long long>(e0 - e1), get - empty, local - empty, mism, v);
    }
#if BIG_TABLE
    std::printf("PROBE op big_read=%d size=%zu\n", big[(cambc::round_number() * 7919u) % sizeof big], sizeof big);
#endif
}

static void draft_turn_fn() {
    const auto ally = cambc::draft::current_draft(cambc::team::ally);
    for (int i = 0; i < 64; ++i) {
        auto pick = static_cast<cambc::champion_draft>(i);
        bool taken = false;
        for (auto a : ally) taken |= a == pick;
        if (!taken) { cambc::draft::pick(pick); break; }
    }
}

int main() {
    const auto f0 = F();
    std::printf("PROBE start big=%d draft=%d fuel=%llu\n", BIG_TABLE, cambc::is_draft() ? 1 : 0, static_cast<unsigned long long>(f0));
#if BIG_TABLE
    std::printf("PROBE start_read %d\n", big[f0 % sizeof big]);
#endif
    while (true) {
        try {
            if (cambc::is_draft()) draft_turn_fn();
            else if (cambc::round_number() == 2) { measure(); std::fflush(stdout); }
        } catch (const std::exception& e) {
            std::printf("PROBE err %s\n", e.what());
        }
        cambc::end_turn();
    }
}
