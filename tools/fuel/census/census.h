#pragma once
// Fuel census (debug builds only): per-component fuel of each turn, and the scopes open when a turn ran out.
// Everything runs inside debug_block, so it costs ~10 fuel a scope. One "CEN" stdout line per turn that ran
// out, started late or spent at least print_floor; tools/fuel/census/census.py reads them.
#include <cambc.h>
#include <cstdint>
#include <cstdio>
#include <cstring>

namespace aph::census {

inline constexpr std::uint64_t print_floor = 70000;
inline constexpr int max_labels = 96, max_depth = 48;

struct Frame {
    const char* label;
    std::uint64_t start, child;
    bool dup;    // the label is already open below: not added to inclusive again
    bool closed; // credited at exhaustion
};

struct State {
    bool on = false;
    std::uint32_t round = 0;
    std::uint64_t start = 0;
    bool late = false, ran_out = false;
    char stack[400]{};
    Frame frames[max_depth];
    int depth = 0;
    const char* labels[max_labels]{};
    std::uint64_t incl[max_labels]{}, self[max_labels]{};
    int calls[max_labels]{};
    int n = 0;
    int type = -1, enemies = 0, allies = 0, awake = 0, near_enemies = 0;
    std::uint64_t post = 0; // fuel spent after resuming, until the turn's end
    std::uint64_t resume_fuel = 0;
};

inline State& st() {
    static State s;
    return s;
}

inline std::uint64_t now_fuel() { return static_cast<std::uint64_t>(cambc::detail::sdk_fuel_remaining()); }

inline int slot(const char* label) {
    auto& s = st();
    for (int i = 0; i < s.n; ++i)
        if (s.labels[i] == label || std::strcmp(s.labels[i], label) == 0) return i;
    if (s.n >= max_labels) return max_labels - 1;
    s.labels[s.n] = label;
    return s.n++;
}

inline void credit(Frame& f, std::uint64_t end) {
    auto& s = st();
    const std::uint64_t used = f.start > end ? f.start - end : 0;
    const int i = slot(f.label);
    if (!f.dup) s.incl[i] += used;
    s.self[i] += used > f.child ? used - f.child : 0;
    ++s.calls[i];
    f.closed = true;
    return;
}

// Credits every open frame as ending at 0 fuel, the first time we see the round has moved on.
inline void check_resume() {
    auto& s = st();
    if (!s.on || s.ran_out || cambc::round_number() == s.round) return;
    s.ran_out = true;
    s.resume_fuel = now_fuel();
    std::size_t len = 0;
    for (int d = 0; d < s.depth && len + 40 < sizeof s.stack; ++d)
        len += std::snprintf(s.stack + len, sizeof s.stack - len, "%s%s", d ? "/" : "", s.frames[d].label);
    for (int d = s.depth - 1; d >= 0; --d) {
        auto& f = s.frames[d];
        credit(f, 0);
        if (d > 0) s.frames[d - 1].child += f.start;
    }
}

inline void enter(const char* label) {
    auto& s = st();
    if (!s.on) return;
    check_resume();
    if (s.depth >= max_depth) {
        ++s.depth;
        return;
    }
    bool dup = false;
    for (int d = 0; d < s.depth; ++d) dup |= s.frames[d].label == label || std::strcmp(s.frames[d].label, label) == 0;
    s.frames[s.depth++] = {label, now_fuel(), 0, dup, s.ran_out};
}

inline void exit() {
    auto& s = st();
    if (!s.on || s.depth == 0) return;
    check_resume();
    if (s.depth > max_depth) {
        --s.depth;
        return;
    }
    auto& f = s.frames[--s.depth];
    if (f.closed) return; // credited at exhaustion, or opened after resuming
    const auto end = now_fuel();
    credit(f, end);
    if (s.depth > 0) s.frames[s.depth - 1].child += f.start > end ? f.start - end : 0;
}

inline void begin(bool late) {
    auto& s = st();
    s = State{};
    s.on = true;
    s.round = cambc::round_number();
    s.start = now_fuel();
    s.late = late;
}

inline void end() {
    auto& s = st();
    if (!s.on) return;
    check_resume();
    const std::uint64_t spent = s.ran_out ? s.start : s.start - now_fuel();
    if (s.ran_out) s.post = s.resume_fuel > now_fuel() ? s.resume_fuel - now_fuel() : 0;
    s.on = false;
    if (!s.ran_out && !s.late && spent < print_floor) return;
    std::printf("CEN %u %u t%d late%d oof%d start %llu spent %llu post %llu ne %d nn %d na %d aw %d stack %s |",
                s.round, static_cast<unsigned>(static_cast<cambc::handle_champion_t>(cambc::self())), s.type, s.late,
                s.ran_out, static_cast<unsigned long long>(s.start), static_cast<unsigned long long>(spent),
                static_cast<unsigned long long>(s.post), s.enemies, s.near_enemies, s.allies, s.awake,
                s.ran_out ? s.stack : "-");
    for (int i = 0; i < s.n; ++i)
        if (s.incl[i] >= 1000)
            std::printf(" %s=%llu:%llu:%d", s.labels[i], static_cast<unsigned long long>(s.incl[i]),
                        static_cast<unsigned long long>(s.self[i]), s.calls[i]);
    std::printf("\n");
}

struct Scope {
    explicit Scope(const char* label) {
        debug_block({ enter(label); });
    }
    ~Scope() {
        debug_block({ exit(); });
    }
    Scope(const Scope&) = delete;
    Scope& operator=(const Scope&) = delete;
};

} // namespace aph::census

#define CEN_CAT2(a, b) a##b
#define CEN_CAT(a, b) CEN_CAT2(a, b)
#define CENSUS(label) ::aph::census::Scope CEN_CAT(census_scope_, __LINE__){label}
