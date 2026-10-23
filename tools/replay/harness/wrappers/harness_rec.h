// Recorder hooks (gen_wrappers.py --mode rec): log what a later traced run must reproduce, at zero net
// fuel. Each wrapper is
//     fuel_pause(); hk_pre(id, pre); fuel_resume(); r = real(args); fuel_pause(); hk_post(...); fuel_resume();
// The pauses are direct imports, which are not fuel checks: only wasm function entries and loop
// headers are. When an import's price exceeds the fuel left, the engine finishes the call, leaves 0
// fuel and suspends the bot at its next check; a wrapper that called a hook function right after the
// import would add a check there and suspend early. hk_pre refunds the wrapper's operators before
// the import runs, so the import sees exactly the unwrapped fuel; hk_post refunds the rest unless the
// import left 0 fuel, so the bot reaches its next own check with no fuel, as unwrapped.
//
// No static data: a static would shift the bot's data or heap and could change its behaviour. State
// lives in the bottom of the shadow stack (the bot links stack-first, so [0, 65536) is stack growing
// down from 65536; v38 never uses more than ~13 KB of it). Strings are built from immediates.
//
// Output (stdout): every record is written as '\n' + line + '\n' and flushed at once, so a record
// never shares a line with the bot's own output; skip empty lines. All numbers decimal.
//   @f <me> <seg> <idx> <value>   fuel_remaining call #idx of segment seg returned value
//   @r <me> <seg> <idx> <round>   the bot ran out of fuel before host call #idx, which is the first
//                                 call made in the new round <round>
//   @x <me> <seg> <idx>           with the @r before it: it ran out at the wrapper's own entry check
//                                 (an unwrapped bot would have made call #idx in the old round, at
//                                 zero fuel, and stopped at its next check): trust ends here
//   @y <me> <seg> <round> <calls> <hash>   yield ending segment seg (calls counted incl. the yield)
// <me> is the champion id, -1 for the draft bot. A segment is the work between two yields.
#pragma once
#include <cstdint>

extern "C" {
__attribute__((import_module("env"), import_name("fuel_pause"))) int32_t hr_pause();
__attribute__((import_module("env"), import_name("fuel_resume"))) void hr_resume();
__attribute__((import_module("env"), import_name("fuel_adjust"))) void hr_adjust(int64_t);
__attribute__((import_module("env"), import_name("bc_round_number"))) int32_t hr_round(uint32_t*);
__attribute__((import_module("env"), import_name("my_champion"))) int32_t hr_me();
__attribute__((import_module("env"), import_name("fuel_remaining"))) int64_t hr_fuel(); // frozen while paused
__attribute__((import_module("wasi_snapshot_preview1"), import_name("fd_write"))) int32_t hr_fd_write(int32_t, void*, int32_t, void*);
}

// Host-side fuel of a pause/adjust/resume sequence not covered by the wrapper's operator counts
// (calibrated with the probe in calib/).
#ifndef HK_PRE_HOST
#define HK_PRE_HOST 1
#endif
#ifndef HK_POST_HOST
#define HK_POST_HOST 0
#endif

#ifndef HR_STATE_ADDR
#define HR_STATE_ADDR 16384
#endif

namespace hr {
constexpr uint32_t MAGIC = 0x48524543u;
constexpr uint32_t CAP = 640;
// Hooks keep every temporary here too: writing below the bot's stack pointer would change the
// garbage an uninitialised read of the bot sees (measured: it changed v38's fuel on first turns).
struct State {
    uint32_t magic, seg, calls, hash, round, scratch_round;
    int32_t me;
    // The last call's return value, and the frozen fuel plus refund after it (rollover detection).
    uint32_t last_rc;
    int64_t fuel_after;
    uint32_t len;
    uint32_t iov[2], nwritten;
    char digits[24];
    char buf[CAP];
};
static_assert(sizeof(State) < 760 && sizeof(State) % 8 == 0);
inline State* st() { return reinterpret_cast<State*>(static_cast<uintptr_t>(HR_STATE_ADDR)); }

__attribute__((noinline)) void flush() {
    State* s = st();
    if (!s->len) return;
    s->iov[0] = static_cast<uint32_t>(reinterpret_cast<uintptr_t>(s->buf));
    s->iov[1] = s->len;
    hr_fd_write(1, s->iov, 1, &s->nwritten);
    s->len = 0;
}
inline void put(char c) {
    State* s = st();
    s->buf[s->len++] = c;
}
__attribute__((noinline)) void num(int64_t v) {
    char* t = st()->digits;
    int k = 0;
    const bool neg = v < 0;
    uint64_t u = neg ? static_cast<uint64_t>(-v) : static_cast<uint64_t>(v);
    do { t[k++] = static_cast<char>('0' + u % 10); u /= 10; } while (u);
    put(' ');
    if (neg) put('-');
    while (k) put(t[--k]);
}
__attribute__((noinline)) void begin(char kind) {
    if (st()->len > CAP - 100) flush();
    put('\n');
    put('@');
    put(kind);
    num(st()->me);
    num(st()->seg);
}
inline void end() {
    put('\n');
    flush();
}
uint32_t round_now() {
    State* s = st();
    s->scratch_round = 0;
    hr_round(&s->scratch_round);
    return s->scratch_round;
}
__attribute__((noinline)) void init() {
    State* s = st();
    if (s->magic == MAGIC) return;
    s->magic = MAGIC;
    s->seg = s->calls = s->hash = s->len = 0;
    s->me = hr_me();
    s->round = round_now();
    s->last_rc = 0;
    s->fuel_after = hr_fuel();
}
inline uint32_t mix(uint32_t h, uint32_t v) { return (h ^ v) * 16777619u; }
// Counts the call and folds it into the segment hash.
__attribute__((noinline)) uint32_t count(uint32_t id, uint32_t r, uint32_t h0, uint32_t h1, uint32_t h2) {
    State* s = st();
    const uint32_t idx = s->calls++;
    uint32_t h = s->hash ? s->hash : 2166136261u;
    s->hash = mix(mix(mix(mix(mix(h, id), r), h0), h1), h2);
    return idx;
}
// Before a call: note a round change since the last call (the bot ran out of fuel in between).
// bc_round_number clears the engine's last error, which the SDK reads right after a failing call
// (bc_get_last_error), so the round is queried only after a call that returned 0; otherwise a new
// turn shows as fuel above what the last call left, and is the next round.
__attribute__((noinline)) void pre(int32_t refund) {
    init();
    State* s = st();
    uint32_t round = s->round;
    if (s->last_rc == 0) round = round_now();
    else if (hr_fuel() > s->fuel_after) round = s->round + 1;
    if (round != s->round) {
        s->round = round;
        begin('r'); num(s->calls); num(round); end();
        // Only the pause call has run since the resume: the wrapper's entry check stopped the bot.
        if (hr_fuel() >= 99999) { begin('x'); num(s->calls); end(); }
    }
    hr_adjust(refund);
}
// After a call: refund the rest of the wrapper, unless the import left no fuel (see the top).
inline void post(int32_t refund, uint32_t rc) {
    State* s = st();
    const int64_t f = hr_fuel();
    if (f <= 0) refund = 0;
    hr_adjust(refund);
    s->fuel_after = f + refund;
    s->last_rc = rc;
}
} // namespace hr

inline uint32_t hk_f32(float f) { return __builtin_bit_cast(uint32_t, f); }

__attribute__((noinline)) void hk_pre(uint32_t, int32_t pre) { hr::pre(pre + HK_PRE_HOST); }

__attribute__((noinline)) void hk_post(uint32_t id, int32_t post, uint32_t r, uint32_t h0, uint32_t h1, uint32_t h2) {
    hr::count(id, r, h0, h1, h2);
    hr::post(post + HK_POST_HOST, r);
}

__attribute__((noinline)) void hk_post_fuel(uint32_t id, int32_t post, int64_t v) {
    const uint32_t idx = hr::count(id, 0, 0, 0, 0);
    hr::begin('f'); hr::num(idx); hr::num(v); hr::end();
    hr::post(post + HK_POST_HOST, 0);
}

// The yield: its segment ends before the real yield and the next starts after it.
__attribute__((noinline)) void hk_pre_yield(uint32_t id, int32_t pre) {
    hr::pre(pre + HK_PRE_HOST);
    hr::count(id, 0, 0, 0, 0);
    hr::State* s = hr::st();
    hr::begin('y'); hr::num(s->round); hr::num(s->calls); hr::num(s->hash); hr::end();
    s->seg++;
    s->calls = 0;
    s->hash = 0;
}

// After the yield returns: a new turn, whose round is the segment's start.
__attribute__((noinline)) void hk_post_yield(uint32_t, int32_t post) {
    hr::st()->round = hr::round_now();
    hr::post(post + HK_POST_HOST, 0);
}
