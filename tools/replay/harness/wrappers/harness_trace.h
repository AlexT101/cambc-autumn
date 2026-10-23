// Tracer hooks (gen_wrappers.py --mode trace): replay a recorder run's fuel view in a debug build.
//
// The traced bot is a debug build with logging, so its own fuel use differs from the release
// code's. The hooks make that irrelevant:
// - fuel_remaining() returns the value the recorder logged for the same call (@f, by segment and
//   counted call), so every fuel-gated choice sees what the recorded bot saw;
// - each counted call refunds a huge amount, so the tracer never runs out on its own: a refund past
//   the budget is real hidden fuel until the turn ends or a drain, though fuel_remaining() reads at
//   most the budget (probe-fueladjust-b);
// - each recorded out-of-fuel point (@r: the bot ran out before call #idx, the first call of the
//   new round) is reproduced as a real one right before that call: the hook drains the fuel and
//   spins until the next fuel check suspends it, so the engine records the same Turn rollover;
// - every counted call is hashed as the recorder hashes it, and each segment's count and hash are
//   checked against @y.
// bc_round_number clears the engine's last error, which the SDK reads right after a failing call:
// like the recorder, the hooks query the round only after a counted call that returned 0, and
// otherwise take round changes from the recording (a forced rollover lands by fuel, not round).
// Calls made inside debug_block (cambc_debug_depth > 0, ws SDK patch) are neither counted nor
// virtualised: fuel_remaining() there returns the last value the bot itself was given.
//
// Output lines (stdout), besides the bot's own:
//   @v <me> <seg> <round> <calls> <hash>        each segment's own @y, for the runner's offline check
//   @o <me> <seg> <idx> <round>                 an out-of-fuel point reproduced: call idx runs in round
//   @! <what> <me> <seg> <idx|round> ...        a mismatch against the recording (see TRACE_SCHEMA.md)
#pragma once
#include <cstdint>
#include <cstdio>
#include "harness_trace_data.h"

extern "C" {
__attribute__((import_module("env"), import_name("fuel_pause"))) int32_t hr_pause();
__attribute__((import_module("env"), import_name("fuel_resume"))) void hr_resume();
__attribute__((import_module("env"), import_name("fuel_adjust"))) void hr_adjust(int64_t);
__attribute__((import_module("env"), import_name("bc_round_number"))) int32_t hr_round(uint32_t*);
__attribute__((import_module("env"), import_name("my_champion"))) int32_t hr_me();
__attribute__((import_module("env"), import_name("fuel_remaining"))) int64_t hr_fuel();
extern int32_t cambc_debug_depth;
}

#define HK_PRE(id) ht::pre()

namespace ht {
constexpr int64_t refund = 1000000000;
constexpr int64_t drain = -(int64_t{1} << 62);

struct State {
    bool ready = false;
    int32_t me = -2;
    const HtInst* inst = nullptr;
    uint32_t seg = 0, calls = 0, hash = 0, round = 0;
    uint32_t fc = 0, rc = 0; // cursors into inst->f and inst->r
    uint32_t last_rc = 0;    // the last counted call's return code: nonzero, the round is not queried
    int64_t last_fuel = -1;  // the last value fuel_remaining() returned to the bot
    uint32_t mismatches = 0, forced = 0;
    bool tail = false; // past the recording's last @y: the game ended in this segment
};
State S;

uint32_t round_now() {
    uint32_t r = 0;
    hr_round(&r);
    return r;
}

void note_tail() {
    S.tail = S.inst && S.seg >= S.inst->ny;
    if (S.tail) std::printf("@! tail %d %u %u\n", S.me, S.seg, S.round), std::fflush(stdout);
}

__attribute__((noinline)) void init() {
    if (S.ready) return;
    S.ready = true;
    S.me = hr_me();
    for (uint32_t i = 0; i < ht_ninst; ++i)
        if (ht_insts[i].me == S.me) S.inst = &ht_insts[i];
    if (!S.inst) std::printf("@! inst %d %s\n", S.me, ht_game), ++S.mismatches;
    S.round = round_now();
    note_tail();
}

void miss() { ++S.mismatches; }

inline uint32_t mix(uint32_t h, uint32_t v) { return (h ^ v) * 16777619u; }

void count(uint32_t id, uint32_t r, uint32_t h0, uint32_t h1, uint32_t h2) {
    ++S.calls;
    uint32_t h = S.hash ? S.hash : 2166136261u;
    S.hash = mix(mix(mix(mix(mix(h, id), r), h0), h1), h2);
}

// Before counted call #calls: reproduce the out-of-fuel points recorded before it, and flag any
// other round change (only where the round may be queried).
__attribute__((noinline)) void pre_slow() {
    init();
    if (const HtInst* in = S.inst) {
        while (S.rc < in->nr && (in->r[S.rc].seg < S.seg || (in->r[S.rc].seg == S.seg && in->r[S.rc].idx < S.calls))) ++S.rc;
        while (S.rc < in->nr && in->r[S.rc].seg == S.seg && in->r[S.rc].idx == S.calls) {
            const uint32_t target = in->r[S.rc].round;
            std::printf("@o %d %u %u %u\n", S.me, S.seg, S.calls, target);
            std::fflush(stdout);
            // A drain empties one 100k chunk of the turn's budget (a first turn has more): drain
            // until none is left. Imports are not fuel checks, the spin's back-edge is: the bot
            // stops there and resumes with the next round's fresh fuel.
            for (uint32_t k = S.round; k < target; ++k) {
                do {
                    hr_pause();
                    hr_adjust(drain);
                    hr_resume();
                } while (hr_fuel() > 0);
                int64_t f;
                do f = hr_fuel();
                while (f <= 0);
                ++S.forced;
            }
            if (S.last_rc == 0)
                if (const uint32_t now = round_now(); now != target)
                    std::printf("@! oof %d %u %u %u %u\n", S.me, S.seg, S.calls, now, target), miss();
            S.round = target;
            ++S.rc;
        }
    }
    if (S.last_rc != 0) return;
    if (const uint32_t now = round_now(); now != S.round) {
        std::printf("@! round %d %u %u %u %u\n", S.me, S.seg, S.calls, now, S.round), miss();
        S.round = now;
    }
}

inline void pre() {
    if (cambc_debug_depth) return;
    pre_slow();
}
} // namespace ht

inline uint32_t hk_f32(float f) { return __builtin_bit_cast(uint32_t, f); }

__attribute__((noinline)) void hk(uint32_t id, int32_t, uint32_t r, uint32_t h0, uint32_t h1, uint32_t h2) {
    if (cambc_debug_depth) return;
    hr_pause();
    ht::count(id, r, h0, h1, h2);
    ht::S.last_rc = r;
    hr_adjust(ht::refund);
    hr_resume();
}

__attribute__((noinline)) int64_t hk_fuel(uint32_t id, int32_t, int64_t real) {
    using ht::S;
    if (cambc_debug_depth) return S.last_fuel >= 0 ? S.last_fuel : real;
    ht::pre_slow();
    hr_pause();
    const uint32_t idx = S.calls;
    ht::count(id, 0, 0, 0, 0);
    int64_t v = S.last_fuel >= 0 ? S.last_fuel : 100000;
    if (const HtInst* in = S.inst) {
        while (S.fc < in->nf && (in->f[S.fc].seg < S.seg || (in->f[S.fc].seg == S.seg && in->f[S.fc].idx < idx))) ++S.fc;
        if (S.fc < in->nf && in->f[S.fc].seg == S.seg && in->f[S.fc].idx == idx) v = in->f[S.fc++].v;
        else std::printf("@! fuel %d %u %u %u\n", S.me, S.seg, idx, S.round), ht::miss();
    }
    S.last_fuel = v;
    S.last_rc = 0;
    hr_adjust(ht::refund);
    hr_resume();
    return v;
}

__attribute__((noinline)) void hk_yield(uint32_t id, int32_t) {
    using ht::S;
    ht::pre_slow();
    hr_pause();
    ht::count(id, 0, 0, 0, 0);
    std::printf("@v %d %u %u %u %u\n", S.me, S.seg, S.round, S.calls, S.hash);
    if (const HtInst* in = S.inst) {
        if (S.seg < in->ny)
            if (const HtY& y = in->y[S.seg]; y.round != S.round || y.calls != S.calls || y.hash != S.hash)
                std::printf("@! yield %d %u %u %u %u %u %u %u\n", S.me, S.seg, S.round, S.calls, S.hash, y.round, y.calls, y.hash), ht::miss();
    }
    std::fflush(stdout);
    ++S.seg;
    S.calls = S.hash = 0;
    S.last_fuel = -1;
    hr_resume();
}

__attribute__((noinline)) void hk_resumed(uint32_t) {
    ht::S.round = ht::round_now();
    ht::S.last_rc = 0;
    ht::note_tail();
}

// For the traced bot's logging (declared weak there): the fuel the bot last read, the segment and
// the mismatches so far.
extern "C" {
__attribute__((noinline)) int64_t ht_last_fuel() { return ht::S.last_fuel; }
__attribute__((noinline)) uint32_t ht_segment() { return ht::S.seg; }
__attribute__((noinline)) uint32_t ht_mismatches() { return ht::S.mismatches; }
__attribute__((noinline)) const char* ht_game_key() { return ht_game; }
// The traced bot's current decision site (its trace.cpp defines it).
__attribute__((weak)) const char* trace_site = "-";
}

// A counted action call: TA r=<round> c=<me> a=<import> x=<int args> rc=<return code> ok=<result
// written through the out-parameter, -1 if none> s=<site>.
__attribute__((noinline)) void ht_act(const char* name, int32_t r, int32_t res, int n, int32_t a0, int32_t a1, int32_t a2, int32_t a3, int32_t a4) {
    if (cambc_debug_depth) return;
    hr_pause();
    const int32_t a[5] = {a0, a1, a2, a3, a4};
    std::printf("TA r=%u c=%d a=%s x=", ht::S.round, ht::S.me, name);
    for (int i = 0; i < n; ++i) std::printf(i ? ",%d" : "%d", a[i]);
    if (!n) std::printf("-");
    std::printf(" rc=%d ok=%d s=%s\n", r, res, trace_site ? trace_site : "-");
    hr_resume();
}
