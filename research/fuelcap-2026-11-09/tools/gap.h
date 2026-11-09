#pragma once
// Segment census (debug builds only, measurement). A reset is a point after which the fuel left is
// known to be at least B: the turn start (B = the turn's budget), a passed fuel_ok (B = what it
// needed) and a checkpoint (stale check or deadline check: B = 0 here, the floor is the proof's).
// Between consecutive resets the fuel spent is a segment, aggregated by (from-site, to-site):
// "SEG id round from to kind count max maxexcess sum maxround", excess = cost - B (signed).
// Every 100 rounds (and from 1995) each instance prints its table so far, then "SEGEND id round
// turns oof". Everything runs inside debug_block.
#include <cambc.h>
#include <cstdint>
#include <cstdio>
#include <cstring>

namespace aph::gap {

inline constexpr std::uint64_t keep_cost = 2000;
inline constexpr int slots = 4096;

struct Pair {
    const char* f0;
    int l0;
    const char* f1;
    int l1;
    char kind; // the from-reset's kind: t turn start, g gate, c checkpoint
    std::uint64_t n, max, sum;
    std::int64_t excess;
    std::uint32_t max_round;
};
struct State {
    bool on = false;
    std::uint32_t round = 0, last_dump = 0;
    std::uint64_t at = 0, budget = 0; // fuel at the last reset
    std::int64_t B = 0;
    char kind = 't';
    const char* pf = "turn_start";
    int pl = 0;
    Pair pairs[slots]{};
    int n = 0;
    std::uint64_t turns = 0, oof = 0;
    // every mark (probes included): consecutive pairs
    std::uint64_t mat = 0;
    const char* mf = "turn_start";
    int ml = 0;
    Pair any[slots]{};
    Pair oofs[512]{}; // the turns that ran out: last reset -> last mark
    // the open segment's profile: self cost by mark site (the gap after each mark)
    struct Site { const char* f; int l; std::uint32_t n; std::uint64_t cost; };
    Site prof[256]{};
    int prof_n = 0;
    std::uint64_t trc_printed = 0;
};
inline State& st() {
    static State s;
    return s;
}
inline std::uint64_t now() { return static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining()); }
inline const char* base(const char* f) {
    const char* b = std::strstr(f, "/src/");
    return b ? b + 5 : f;
}
inline void add(const char* f0, int l0, char kind, const char* f1, int l1, std::uint64_t g, std::int64_t excess, bool all = false) {
    auto& s = st();
    Pair* pairs = all ? s.any : s.pairs;
    const std::uint32_t h = (static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(f0)) * 31u + static_cast<std::uint32_t>(l0) * 131u
                             + static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(f1)) * 17u + static_cast<std::uint32_t>(l1) * 7u)
                            % slots;
    for (std::uint32_t k = 0; k < slots; ++k) {
        auto& p = pairs[(h + k) % slots];
        if (!p.f0) p = {f0, l0, f1, l1, kind, 0, 0, 0, INT64_MIN, 0};
        if (p.f0 == f0 && p.l0 == l0 && p.f1 == f1 && p.l1 == l1) {
            ++p.n, p.sum += g;
            if (g > p.max) p.max = g, p.max_round = s.round;
            if (excess > p.excess) p.excess = excess;
            return;
        }
    }
}
// kind: 'g' passed gate needing B, 'c' checkpoint, 'n' not a reset (failed gate, raw read).
inline void mark(const char* f, int l, char kind, std::uint64_t B) {
    auto& s = st();
    if (!s.on) return;
    if (cambc::round_number() != s.round) return; // resumed after running out: the segment is lost
    const auto n = now();
    const auto ga = s.mat > n ? s.mat - n : 0;
    if (ga >= 3000) add(s.mf, s.ml, kind, f, l, ga, 0, true);
    if (ga > 0) {
        int i = 0;
        for (; i < s.prof_n; ++i)
            if (s.prof[i].f == s.mf && s.prof[i].l == s.ml) break;
        if (i == s.prof_n && s.prof_n < 256) s.prof[s.prof_n++] = {s.mf, s.ml, 0, 0};
        if (i < 256) ++s.prof[i].n, s.prof[i].cost += ga;
    }
    s.mat = n, s.mf = f, s.ml = l;
    if (kind == 'n' || kind == 'p') return;
    const auto g = s.at > n ? s.at - n : 0;
    if (g >= 200) add(s.pf, s.pl, s.kind, f, l, g, static_cast<std::int64_t>(g) - s.B);
    if ((g >= 25000 || static_cast<std::int64_t>(g) - s.B >= 7000) && s.trc_printed < 300000) {
        s.trc_printed += static_cast<std::uint64_t>(std::printf("TRC %u %s:%d %s:%d %c %llu\n", s.round, base(s.pf), s.pl, base(f), l, s.kind, static_cast<unsigned long long>(g)));
        for (int k = 0; k < 14; ++k) {
            int best = -1;
            for (int i = 0; i < s.prof_n; ++i)
                if (s.prof[i].n && (best < 0 || s.prof[i].cost > s.prof[best].cost)) best = i;
            if (best < 0 || s.prof[best].cost < 500) break;
            s.trc_printed += static_cast<std::uint64_t>(std::printf("TRS %s:%d %u %llu\n", base(s.prof[best].f), s.prof[best].l, s.prof[best].n, static_cast<unsigned long long>(s.prof[best].cost)));
            s.prof[best].n = 0;
        }
    }
    s.prof_n = 0;
    s.at = n, s.pf = f, s.pl = l, s.kind = kind, s.B = static_cast<std::int64_t>(B);
}
inline void dump(unsigned id) {
    auto& s = st();
    for (const auto& p : s.pairs)
        if (p.f0 && (p.max >= 5000 || p.excess > -3000))
            std::printf("SEG %u %u %s:%d %s:%d %c %llu %llu %lld %llu %u\n", id, s.round, base(p.f0), p.l0, base(p.f1), p.l1, p.kind,
                        static_cast<unsigned long long>(p.n), static_cast<unsigned long long>(p.max), static_cast<long long>(p.excess),
                        static_cast<unsigned long long>(p.sum), p.max_round);
    for (const auto& p : s.any)
        if (p.f0 && p.max >= 8000)
            std::printf("ANY %u %u %s:%d %s:%d %c %llu %llu %lld %llu %u\n", id, s.round, base(p.f0), p.l0, base(p.f1), p.l1, p.kind,
                        static_cast<unsigned long long>(p.n), static_cast<unsigned long long>(p.max), 0LL,
                        static_cast<unsigned long long>(p.sum), p.max_round);
    for (const auto& p : s.oofs)
        if (p.f0)
            std::printf("OOF %u %u %s:%d %s:%d %c %llu %llu 0 0 %u\n", id, s.round, base(p.f0), p.l0, base(p.f1), p.l1, p.kind,
                        static_cast<unsigned long long>(p.n), static_cast<unsigned long long>(p.max), p.max_round);
    std::printf("SEGEND %u %u %llu %llu\n", id, s.round, static_cast<unsigned long long>(s.turns), static_cast<unsigned long long>(s.oof));
}
inline void begin() {
    auto& s = st();
    static bool first = true;
    const std::uint64_t budget = first ? 200000 : 100000;
    first = false;
    s.on = true;
    s.round = cambc::round_number();
    s.at = now();
    s.B = static_cast<std::int64_t>(budget < s.at ? budget : s.at);
    s.kind = 't';
    s.pf = "turn_start", s.pl = 0;
    s.mat = s.at, s.mf = "turn_start", s.ml = 0;
    s.prof_n = 0;
    ++s.turns;
}
inline void end(unsigned id) {
    auto& s = st();
    if (cambc::round_number() != s.round) {
        ++s.oof;
        if (s.trc_printed < 600000) {
            s.trc_printed += static_cast<std::uint64_t>(std::printf("OOFT %u %s:%d %s:%d %c %llu\n", s.round, base(s.pf), s.pl, base(s.mf), s.ml, s.kind, static_cast<unsigned long long>(s.at)));
            for (int k = 0; k < 10; ++k) {
                int best = -1;
                for (int i = 0; i < s.prof_n; ++i)
                    if (s.prof[i].n && (best < 0 || s.prof[i].cost > s.prof[best].cost)) best = i;
                if (best < 0) break;
                s.trc_printed += static_cast<std::uint64_t>(std::printf("OOFS %s:%d %u %llu\n", base(s.prof[best].f), s.prof[best].l, s.prof[best].n, static_cast<unsigned long long>(s.prof[best].cost)));
                s.prof[best].n = 0;
            }
        }
        const std::uint32_t h = (static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(s.pf)) * 31u + static_cast<std::uint32_t>(s.pl) * 131u
                                 + static_cast<std::uint32_t>(reinterpret_cast<std::uintptr_t>(s.mf)) * 17u + static_cast<std::uint32_t>(s.ml) * 7u) % 512;
        for (std::uint32_t k = 0; k < 512; ++k) {
            auto& o = s.oofs[(h + k) % 512];
            if (!o.f0) o = {s.pf, s.pl, s.mf, s.ml, s.kind, 0, 0, 0, 0, 0};
            if (o.f0 == s.pf && o.l0 == s.pl && o.f1 == s.mf && o.l1 == s.ml) {
                ++o.n, o.max_round = s.round;
                if (s.at > o.max) o.max = s.at; // fuel left at the last reset
                break;
            }
        }
    } else mark("turn_end", 0, 'c', 0);
    s.on = false;
    if (s.round >= s.last_dump + 250 || (s.round >= 1995 && s.round >= s.last_dump + 3)) {
        s.last_dump = s.round;
        dump(id);
    }
}

} // namespace aph::gap
#define PROBE() debug_block({ ::aph::gap::mark(__FILE__, __LINE__, 'p', 0); })
