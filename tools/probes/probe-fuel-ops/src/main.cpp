// probe-fuel-ops: fuel per WASM arithmetic instruction, by kind (is a division dearer than an add?).
// Run: cambc run probe-fuel-ops probe-fuel-ops --map 00corners --rounds 3 -o <dir>
// Each loop runs N times on volatile operands; PROBE lines print the fuel per iteration, minus an
// empty loop's. bot.cpp / draft.cpp from the template are unused.
#include <cambc.h>
#include <cstdint>
#include <cstdio>

static std::uint64_t F() { return cambc::fuel_remaining(); }

constexpr int N = 2000;
volatile std::uint64_t v64 = 1234567891234ull, d64 = 37;

template <class Body> static double per_iteration(Body body) {
    const auto a = F();
    for (int i = 0; i < N; ++i) body(i);
    const auto b = F();
    return static_cast<double>(a - b) / N;
}

static void measure() {
    const double empty = per_iteration([](int) { v64 = v64; });
    const double add64 = per_iteration([](int i) { v64 = v64 + static_cast<std::uint64_t>(i); }) - empty;
    const double mul64 = per_iteration([](int) { v64 = v64 * d64; }) - empty;
    const double div64 = per_iteration([](int) { v64 = v64 / d64 + 1234567891234ull; }) - empty;
    const double rem64 = per_iteration([](int) { v64 = v64 % d64 + 1234567891234ull; }) - empty;
    const double shift64 = per_iteration([](int) { v64 = v64 >> (d64 & 63); }) - empty;
    std::printf("PROBE %u ops empty=%.2f add64=%.2f mul64=%.2f div64=%.2f rem64=%.2f shift64=%.2f\n",
                cambc::round_number(), empty, add64, mul64, div64, rem64, shift64);
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
    while (true) {
        try {
            if (cambc::is_draft()) draft_turn_fn();
            else if (cambc::round_number() == 2) measure();
        } catch (const std::exception& e) {
            std::printf("PROBE err %s\n", e.what());
        }
        cambc::end_turn();
    }
}
