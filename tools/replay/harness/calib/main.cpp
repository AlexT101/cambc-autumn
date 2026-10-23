// Calibration probe for the recorder hooks (calibrate.py). Built twice: plain, and with the recorder
// wrappers. Champion 0 measures in round 3 how much fuel a wrapped import costs over the direct import,
// using unwrapped aliases of the imports; every champion does a fixed mixed workload each turn so the
// two builds' per-turn fuel files can be compared.
#include <cambc.h>
#include <cstdint>
#include <cstdio>

extern "C" {
__attribute__((import_module("env"), import_name("fuel_remaining"))) int64_t pf();
__attribute__((import_module("env"), import_name("my_team"))) int32_t d_my_team();
__attribute__((import_module("env"), import_name("bc_round_number"))) int32_t d_round(uint32_t*);
__attribute__((import_module("env"), import_name("bc_Bitboard_Test"))) int32_t d_test(const uint64_t*, int32_t, int32_t, int32_t*);
__attribute__((import_module("env"), import_name("champion"))) int32_t d_champion(uint32_t, void*);
__attribute__((import_module("env"), import_name("bc_Bitboard_DrawChebyshev"))) int32_t d_cheb(uint64_t*, int32_t, int32_t, float);
}
namespace d = cambc::detail;
volatile int64_t sink;
uint64_t board[256];
cambc::detail::champion_info info;

[[gnu::noinline]] void w_team(int n) { for (int i = 0; i < n; ++i) sink = sink + d::sdk_my_team(); }
[[gnu::noinline]] void d_team(int n) { for (int i = 0; i < n; ++i) sink = sink + d_my_team(); }
[[gnu::noinline]] void w_round(int n) { uint32_t r; for (int i = 0; i < n; ++i) { d::sdk_bc_round_number(&r); sink = sink + r; } }
[[gnu::noinline]] void d_round_(int n) { uint32_t r; for (int i = 0; i < n; ++i) { d_round(&r); sink = sink + r; } }
[[gnu::noinline]] void w_test(int n) { int32_t v; for (int i = 0; i < n; ++i) { d::sdk_Bitboard_Test(board, i & 7, 3, &v); sink = sink + v; } }
[[gnu::noinline]] void d_test_(int n) { int32_t v; for (int i = 0; i < n; ++i) { d_test(board, i & 7, 3, &v); sink = sink + v; } }
[[gnu::noinline]] void w_champ(int n) { for (int i = 0; i < n; ++i) sink = sink + d::sdk_champion(0, &info); }
[[gnu::noinline]] void d_champ(int n) { for (int i = 0; i < n; ++i) sink = sink + d_champion(0, &info); }
[[gnu::noinline]] void w_cheb(int n) { for (int i = 0; i < n; ++i) sink = sink + d::sdk_Bitboard_DrawChebyshev(board, 5, 5, 2.0f); }
[[gnu::noinline]] void d_cheb_(int n) { for (int i = 0; i < n; ++i) sink = sink + d_cheb(board, 5, 5, 2.0f); }
[[gnu::noinline]] void w_fuel(int n) { for (int i = 0; i < n; ++i) sink = sink + d::sdk_fuel_remaining(); }
[[gnu::noinline]] void d_fuel(int n) { for (int i = 0; i < n; ++i) sink = sink + pf(); }

template <class W, class D> void measure(const char* name, W w, D dd) {
    const int64_t a = pf(); w(100); const int64_t b = pf(); dd(100); const int64_t c = pf();
    std::printf("CAL %s wrapped %lld direct %lld\n", name, (long long)(a - b), (long long)(b - c));
}

int main() {
    int draft_turn = 0;
    while (true) {
        if (cambc::is_draft() && d::sdk_my_team() == 0 && draft_turn++ < 2) {
            std::printf("CALR draft%d left %lld\n", draft_turn, (long long)pf());
            measure("my_team", w_team, d_team);
            measure("round", w_round, d_round_);
            measure("fuel", w_fuel, d_fuel);
            cambc::draft::pick(draft_turn == 1 ? cambc::champion_draft::ryth : cambc::champion_draft::prism);
        } else if (cambc::is_draft()) {
            for (int c = 0; c < 12; ++c) if (d::sdk_draft_champion(c) == 0) break;
        }
        if (!cambc::is_draft()) {
            const uint32_t r = cambc::round_number();
            if ((r == 3 || r == 1) && d::sdk_my_champion() == 0) {
                std::printf("CALR r%u left %lld\n", r, (long long)pf());
                measure("my_team", w_team, d_team);
                measure("round", w_round, d_round_);
                measure("test", w_test, d_test_);
                measure("champion", w_champ, d_champ);
                measure("cheb", w_cheb, d_cheb_);
                measure("fuel", w_fuel, d_fuel);
                // The value a wrapped read returns against a direct read at the same point.
                const int64_t x0 = pf(); const int64_t x1 = pf();
                const int64_t y0 = pf(); const int64_t y1 = d::sdk_fuel_remaining();
                const int64_t z0 = pf(); const int64_t z1 = pf(); const int64_t z2 = pf();
                const int64_t u0 = pf(); const int64_t u1 = d::sdk_fuel_remaining(); const int64_t u2 = pf();
                std::printf("CALF direct %lld wrapped %lld after3 %lld/%lld wrapped3 %lld/%lld\n", (long long)(x0 - x1), (long long)(y0 - y1),
                            (long long)(z0 - z1), (long long)(z1 - z2), (long long)(u0 - u1), (long long)(u1 - u2));
            }
            // A fixed workload so per-turn fuel files can be compared between builds.
            w_team(10 + r % 7); w_round(5); w_test(3 + r % 5); w_champ(2); w_cheb(r % 3); w_fuel(1 + r % 4);
        }
        cambc::end_turn();
    }
}
