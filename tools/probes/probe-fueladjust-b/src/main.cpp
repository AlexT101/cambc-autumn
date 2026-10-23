// probe-fueladjust-b: fuel_adjust(+delta) beyond the budget, and drains, against the fuel actually
// available (debug builds only; engine 1.0.3). Findings:
// - fuel_remaining() never reads above the turn's budget, but a refund past it is real: the excess is
//   hidden fuel that work spends before the reading drops (k12-k14: +2e4, +1e7, +1e9 all fully usable).
// - The hidden excess does not carry into the next turn (k15/k151), and a drain (-2^62) clears it (k16).
// - A first turn is two 100k chunks: in the first, readings cap at 200000; once into the second, at
//   100000 (k10, k11, k19, k20). A drain empties only the current chunk: in the first it reads 100000,
//   and a second drain with no fuel check between reads 100000 too (k7, k17); in the second it reads 0 (k18).
// Lines: FA r<round> t<team> c<champion> first=<0|1> k<kind> per=<fuel per loop iteration> | readings
//   | end_round (a later round than r: the turn ran out). Kinds 12-14/19/20: e = fuel burnt before the
//   reading dropped below b, f = the fuel of one step (undercounts by ~2%).
// Run: cambc run rules-verification/probes/probe-fueladjust-b rules-verification/probes/probe-fueladjust-b --map 00expanse --rounds 16 --log-limit 8000000
//      (default --fuel, no --release; set V1 to 1 for the first run's schedule, kinds 1-9 and 6-9 on first turns)
#include <cambc.h>
#include <cstdint>
#include <cstdio>
extern "C" {
__attribute__((import_module("env"), import_name("fuel_remaining"))) int64_t pf();
__attribute__((import_module("env"), import_name("fuel_adjust"))) void adj(int64_t);
__attribute__((import_module("env"), import_name("fuel_pause"))) int32_t fpause();
__attribute__((import_module("env"), import_name("fuel_resume"))) void fresume();
__attribute__((import_module("env"), import_name("bc_round_number"))) int32_t d_round(uint32_t*);
}
namespace d = cambc::detail;
volatile uint64_t x;
[[gnu::noinline]] void loop(uint64_t n) { for (uint64_t i = 0; i < n; ++i) x = x + 1; }
[[gnu::noinline]] void burn_to(int64_t left) { while (pf() > left) loop(20); }
uint32_t rnd() { uint32_t r = 0; d_round(&r); return r; }
void padj(int64_t v) { fpause(); adj(v); fresume(); }
#ifndef V1
#define V1 0 // 1: the first run's schedule (kinds 1..9 on rounds 5..13; first turns 1,2,3,10,5,11,4,7,8,9,6)
#endif
constexpr int64_t HUGE_ = 1000000000;
constexpr int64_t DRAIN = -(int64_t{1} << 62);

// fuel per loop iteration, measured
int64_t per_iter() { const int64_t a = pf(); loop(1000); const int64_t b = pf(); return (a - b) / 1000; }

void run(int kind, int team, int me, int first) {
    const uint32_t r0 = rnd();
    const int64_t per = per_iter();
    const uint64_t big = 600000 / (per > 0 ? per : 1); // ~600k fuel of pure loop
    int64_t a = 0, b = 0, c = 0, e = 0, f = 0;
    uint32_t r1 = 0;
    const char* what = "";
    switch (kind) {
    case 1: what = "below: burn to 50000, +20000, paused +20000";
        burn_to(50000); a = pf(); adj(20000); b = pf(); padj(20000); c = pf(); break;
    case 2: what = "near: +500, paused +500";
        a = pf(); adj(500); b = pf(); padj(500); c = pf(); break;
    case 3: what = "near: +1e9 once, then 600k loop";
        a = pf(); adj(HUGE_); b = pf(); loop(big); c = pf(); r1 = rnd(); break;
    case 4: what = "near: paused +1e9 once, then 600k loop";
        a = pf(); padj(HUGE_); b = pf(); loop(big); c = pf(); r1 = rnd(); break;
    case 5: what = "below: burn to 50000, +1e9, then 600k loop";
        burn_to(50000); a = pf(); adj(HUGE_); b = pf(); loop(big); c = pf(); r1 = rnd(); break;
    case 6: what = "paused +1e9 every ~2k fuel during a 3M loop";
        a = pf(); for (uint64_t i = 0; i < 3000000 / 2000; ++i) { padj(HUGE_); loop(2000 / (per > 0 ? per : 1)); }
        c = pf(); r1 = rnd(); break;
    case 7: what = "drain: paused -2^62, read, again, read";
        a = pf(); padj(DRAIN); b = pf(); padj(DRAIN); c = pf(); break;
    case 8: what = "drain once then 600k loop (rollover expected if drain is total)";
        a = pf(); padj(DRAIN); b = pf(); loop(big); c = pf(); r1 = rnd(); break;
    case 9: what = "control: 600k loop, no refund (rollover expected)";
        a = pf(); loop(big); c = pf(); r1 = rnd(); break;
    case 10: what = "first-turn chunk: burn to 150000, +1e9, burn to 50000, +1e9";
        burn_to(150000); a = pf(); adj(HUGE_); b = pf(); burn_to(50000); e = pf(); adj(HUGE_); f = pf(); c = pf(); break;
    case 12: case 13: case 14: case 19: case 20: {
        const int64_t X = kind == 12 ? 20000 : kind == 14 ? HUGE_ : 10000000;
        what = kind == 12 ? "hidden: +20000, steps until the reading drops" : kind == 13 ? "hidden: +1e7, steps until the reading drops"
             : kind == 14 ? "hidden: +1e9, steps until the reading drops" : kind == 19 ? "hidden (first turn, chunk 1): +1e7" : "hidden (first turn, chunk 2): burn to 50000, +1e7";
        if (kind == 20) burn_to(50000);
        const int64_t s0 = pf(); loop(100); const int64_t s1 = pf();
        const int64_t C = s0 - s1; // fuel of one step: loop(100) + a read
        a = pf(); adj(X); b = pf();
        uint64_t steps = 0;
        while ((c = pf()) >= b && steps < 3000000) { loop(100); ++steps; }
        e = int64_t(steps) * C; f = C; r1 = rnd();
        break;
    }
    case 15: what = "+1e9 then end the turn"; a = pf(); adj(HUGE_); b = pf(); break;
    case 151: what = "turn after a +1e9: start reading, 600k loop, no refund"; a = pf(); loop(big); c = pf(); r1 = rnd(); break;
    case 16: what = "+1e9, paused drain, read, 600k loop"; a = pf(); adj(HUGE_); b = pf(); padj(DRAIN); c = pf(); loop(big); e = pf(); r1 = rnd(); break;
    case 17: what = "first turn: burn to 150000, drain, read; drain, read"; burn_to(150000); a = pf(); padj(DRAIN); b = pf(); padj(DRAIN); c = pf(); break;
    case 18: what = "first turn: burn to 50000, drain, read; -1000, read"; burn_to(50000); a = pf(); padj(DRAIN); b = pf(); adj(-1000); c = pf(); break;
    case 11: what = "first-turn chunk: burn to 150000, +20000; burn to 50000, +20000, +60000";
        burn_to(150000); a = pf(); adj(20000); b = pf(); burn_to(50000); e = pf(); adj(20000); f = pf(); adj(60000); c = pf(); break;
    }
    if (!r1) r1 = rnd();
    std::printf("FA r%u t%d c%d first=%d k%d per=%lld | a=%lld b=%lld c=%lld e=%lld f=%lld | end_round=%u (%s)\n",
                r0, team, me, first, kind, (long long)per, (long long)a, (long long)b, (long long)c, (long long)e,
                (long long)f, r1, what);
    std::fflush(stdout);
}

constexpr int FIRST_KINDS[12] = {1, 2, 3, 10, 5, 11, 4, 7, 17, 18, 19, 20};
constexpr int SCHED0[] = {12, 13, 14, 15, 151}, SCHED1[] = {16};
int main() {
    bool first = true;
    while (true) {
        if (cambc::is_draft()) { for (int c = 0; c < 12; ++c) if (d::sdk_draft_champion(c) == 0) break; }
        else {
            const int team = d::sdk_my_team(), me = d::sdk_my_champion();
            const uint32_t r = rnd();
            if (first) {
                std::printf("FA first turn r%u t%d c%d start=%lld\n", r, team, me, (long long)pf());
                run(FIRST_KINDS[me % 12], team, me, 1);
            } else if (V1 && team == 0 && me == 0 && r >= 5 && r <= 13) run(int(r) - 4, team, me, 0);
            else if (!V1 && me == 0 && r >= 5 && r < 5 + sizeof SCHED0 / sizeof *SCHED0) run(SCHED0[r - 5], team, me, 0);
            else if (!V1 && me == 1 && r == 5) run(SCHED1[0], team, me, 0);
            first = false;
        }
        cambc::end_turn();
    }
}
