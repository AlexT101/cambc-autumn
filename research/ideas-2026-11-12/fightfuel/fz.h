// fightfuel profile (research/ideas-2026-11-12/fightfuel): debug-only inclusive fuel scopes and one FZ line a turn.
// Never in a real bot: instr.py adds it to a copy.
#pragma once
#include <cambc.h>
#include <cstdint>
#include <cstdio>

namespace aph::fz {

inline constexpr int N = 96, D = 24;
struct St {
    std::uint64_t in[N];
    std::uint32_t cnt[N];
    int stack[D];
    std::uint64_t t0[D];
    int depth;
    std::uint32_t round;
    std::uint64_t start, left_decide, left_queue;
    int oof[D];
    int oof_depth;
    bool spilled, open, ctx;
    int type, handle, seen, near, allies, hp, gems, hit;
    char decision;
};
inline St& st() {
    static St s{};
    return s;
}
inline std::uint64_t now() { return static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining()); }
// The first event after the round changed: the scopes open then are those the fuel ran out in.
inline void check() {
    auto& s = st();
    if (s.open && !s.spilled && cambc::round_number() != s.round) {
        s.spilled = true;
        s.oof_depth = s.depth < D ? s.depth : D;
        for (int i = 0; i < s.oof_depth; ++i) s.oof[i] = s.stack[i];
    }
}
inline void enter(int id) {
    auto& s = st();
    check();
    if (s.depth >= 0 && s.depth < D) s.stack[s.depth] = id, s.t0[s.depth] = now();
    ++s.depth;
}
inline void exit() {
    auto& s = st();
    check();
    --s.depth;
    if (s.depth >= 0 && s.depth < D && !s.spilled) {
        const int id = s.stack[s.depth];
        const auto t = now();
        if (s.t0[s.depth] >= t) s.in[id] += s.t0[s.depth] - t, ++s.cnt[id];
    }
}
inline void begin() {
    auto& s = st();
    for (auto& x : s.in) x = 0;
    for (auto& x : s.cnt) x = 0;
    s.depth = 0, s.round = cambc::round_number(), s.start = now(), s.left_decide = s.left_queue = 0;
    s.oof_depth = 0, s.spilled = false, s.open = true, s.ctx = false, s.decision = '?';
}
inline void at(int id) { // the fuel left now, the first time in the turn; 79 keeps the last mark passed
    auto& s = st();
    check();
    if (!s.spilled && !s.cnt[id]) s.in[id] = now(), s.cnt[id] = 1;
    if (!s.spilled) s.in[79] = static_cast<std::uint64_t>(id), s.cnt[79] = 1;
}
inline void set(int id) { // the fuel left now, the last time in the turn
    auto& s = st();
    if (!s.spilled) s.in[id] = now(), s.cnt[id] = 1;
}
inline void mark(int id) { // a count without fuel
    auto& s = st();
    if (!s.spilled) ++s.cnt[id];
}
inline void end() {
    auto& s = st();
    check();
    if (!s.open) return;
    s.open = false;
    if (!s.ctx) return;
    // Prism: type 6 in the engine's enum is not assumed; `type` is our Passive::gem_focus flag in bit 8.
    const bool prism = s.type & 256;
    if (!prism && s.seen == 0 && !s.spilled) return;
    std::printf("FZ %u %d %d %c %d %d %d %d %d %d %llu %llu %llu ", s.round, s.handle, s.type, s.decision, s.seen, s.near, s.allies, s.hp, s.gems, s.hit,
                static_cast<unsigned long long>(s.start), static_cast<unsigned long long>(s.left_decide), static_cast<unsigned long long>(s.left_queue));
    if (s.spilled) {
        for (int i = 0; i < s.oof_depth; ++i) std::printf(i ? ".%d" : "%d", s.oof[i]);
        if (s.oof_depth == 0) std::printf("x");
    } else
        std::printf("-");
    for (int i = 0; i < N; ++i)
        if (s.cnt[i]) std::printf(" %d:%llu:%u", i, static_cast<unsigned long long>(s.in[i]), s.cnt[i]);
    std::printf("\n");
}
struct Scope {
    explicit Scope(int id) { debug_block({ enter(id); }); }
    ~Scope() { debug_block({ exit(); }); }
    Scope(const Scope&) = delete;
    Scope& operator=(const Scope&) = delete;
};

} // namespace aph::fz

#define FZ_CAT2(a, b) a##b
#define FZ_CAT(a, b) FZ_CAT2(a, b)
#define FZ(id) ::aph::fz::Scope FZ_CAT(fz_scope_, __LINE__){id}
