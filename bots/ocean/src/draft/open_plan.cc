#include "open_plan.h"
#include <wasm_simd128.h>
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstring>
#include "../params.h"
#include "../util.h"

namespace aph::open_plan {

namespace {

constexpr float never = 1e9f;
constexpr int capture = 6, wait_most = 2;

struct GroupState {
    float back = 0;      // the round it is standing again
    float clear = never; // with its attendees so far
    int n = 0;
    std::array<std::int8_t, max_bodies> att;
    std::array<float, max_bodies> arr;
};

// The problem's numbers a run reads, laid out for it once per problem: by body, and per candidate the walk from
// spawn (row 0) or from each candidate, the capture's value by holder and the trip home.
struct Tables {
    std::array<float, max_bodies> dps, usable, bonus, health;
    std::array<bool, max_bodies> melee;
    std::array<std::array<std::array<float, max_cands>, max_cands + 1>, max_bodies> walk;
    std::array<std::array<float, max_bodies>, max_cands> worth;
    std::array<float, max_cands> home, respawn;

    void build(const Problem& p) {
        for (int b = 0; b < p.bodies; ++b) {
            const auto& B = p.body[b];
            dps[b] = B.dps, usable[b] = B.usable, bonus[b] = B.bonus, health[b] = B.health, melee[b] = B.melee;
            for (int c = 0; c < p.cands; ++c) walk[b][0][c] = static_cast<float>(std::max(0, B.from_spawn[c] - B.range));
            for (int l = 0; l < p.cands; ++l)
                for (int c = 0; c < p.cands; ++c) walk[b][l + 1][c] = static_cast<float>(std::max(0, p.steps[l][c] - B.range));
        }
        for (int c = 0; c < p.cands; ++c) {
            const auto& C = p.cand[c];
            for (int b = 0; b < p.bodies; ++b) worth[c][b] = C.gems + p.per_gold * C.gold * p.body[b].bonus;
            home[c] = static_cast<float>(std::min(2 * C.home, cambc::constants::recall_time + C.home));
            respawn[c] = static_cast<float>(C.respawn);
        }
    }
};

// Attendees are kept in arrival order (Sim::choose inserts in place).
// The clear's end with these attendees: the members' health pooled, as the order they die in does not change it.
float clear_end(const Tables& x, const Cand& c, const GroupState& g) {
    if (g.n == 1) { // the loop's one pass (dps > 0, so 0 + dps is dps)
        const float end = g.arr[0] + c.total / x.dps[g.att[0]];
        return end <= never ? end : never;
    }
    float left = c.total, rate = 0, t = g.arr[0];
    for (int i = 0; i < g.n; ++i) {
        const float until = i + 1 < g.n ? g.arr[i + 1] : never;
        rate += x.dps[g.att[i]];
        if (t + left / rate <= until) return t + left / rate;
        left -= rate * (until - t), t = until;
    }
    return never;
}

// Each attendee's camp damage taken in the clear into `taken`, monsters dying deadliest first: they hit the first
// to arrive until a melee is there, then the healthiest melee.
void clear_damage(const Tables& x, const Cand& c, const GroupState& g, float* taken) {
    for (int i = 0; i < g.n; ++i) taken[i] = 0;
    float strength = c.total_strength;
    if (strength <= 0) return;
    float rate = 0, t = g.arr[0], left = c.hp[0];
    int next = 0, m = 0, tank = -1;
    if (g.n == 1) { // the loop below with its one arrival taken at the start
        const float dps = x.dps[g.att[0]];
        while (m < c.members) {
            const float dies = t + left / dps;
            if (dies <= never) {
                taken[0] += strength * (dies - t);
                strength -= c.strength[m];
                t = dies;
                if (++m < c.members) left = c.hp[m];
            } else {
                taken[0] += strength * (never - t);
                left -= dps * (never - t);
                t = never;
            }
        }
        return;
    }
    while (m < c.members) {
        while (next < g.n && g.arr[next] <= t) {
            const int a = g.att[next];
            rate += x.dps[a];
            if (tank < 0 || (x.melee[a] && (!x.melee[g.att[tank]] || x.health[a] > x.health[g.att[tank]]))) tank = next;
            ++next;
        }
        const float until = next < g.n ? g.arr[next] : never;
        const float dies = t + left / rate;
        if (dies <= until) {
            taken[tank] += strength * (dies - t);
            strength -= c.strength[m];
            t = dies;
            if (++m < c.members) left = c.hp[m];
        } else {
            taken[tank] += strength * (until - t);
            left -= rate * (until - t);
            t = until;
        }
    }
}

// Everything a run changes. The groups come last: a snapshot copies only the problem's candidates. `free` has a
// slot past the bodies' up to 8, at +inf, for the vector minimum.
struct State {
    std::array<float, 8> free{}, damage{};
    std::array<int, max_bodies> loc{}, k{}, att{};
    float value = 0;
    int guard = 0;
    std::array<GroupState, max_cands> group;
};

// The search's record of its best plan's run (solve): before each choose event, the state and the last list index
// that event read. A plan that differs from the best only in body b from index d runs as the best's does up to the
// first of b's events that reads index d or later, since a run reads a body's list only in its choose events, in
// order: that event's state is where it resumes.
struct Mark {
    int body = -1, last = -1;
};

struct Trace {
    int n = 0;
    std::array<Mark, 64 * max_bodies> mark;
    std::array<State, 64 * max_bodies> state;
    std::array<std::array<int, max_steps>, max_bodies> first; // the first mark of each body reading each index, else n

    void index(int bodies) {
        for (int b = 0; b < bodies; ++b) first[b].fill(n);
        for (int i = n - 1; i >= 0; --i)
            for (int d = 0; d <= mark[i].last; ++d) first[mark[i].body][d] = i;
    }
};

// Record: write the trace. Lazy: resumed from snapshot `from`, whose groups are copied in as the run first touches them.
// The methods read the members into locals first: a store to a group's int8 attendees may alias any of them.
template <bool Record, bool Lazy = false>
struct Sim {
    const Problem& p_;
    const Tables& x_;
    const Lists& plan_;
    Lists* attended_;
    Trace* trace_;
    State& s_;
    const State* from_ = nullptr;
    std::array<int, max_bodies> worked{};
    int last = -1; // Record: the last list index the current choose read

    // `loaded`: Lazy, the groups copied in.
    GroupState& group(int c, std::uint32_t& loaded) {
        if constexpr (Lazy)
            if (!(loaded >> c & 1u)) loaded |= 1u << c, s_.group[c] = from_->group[c];
        return s_.group[c];
    }

    void finalize(int c, std::uint32_t& loaded) {
        const Problem& p = p_;
        const Tables& x = x_;
        State& s = s_;
        Lists* const attended = Record || Lazy ? nullptr : attended_;
        auto& g = group(c, loaded);
        auto& free = s.free;
        auto& damage = s.damage;
        const auto& C = p.cand[c];
        std::array<float, max_bodies> taken;
        const float T = g.clear;
        clear_damage(x, C, g, taken.data());
        // A clear that takes anyone past its usable health fails: the real one leaves for home part way (and its
        // fire is what sends farm's bodies home), so the plan gets nothing from the group and it leaves the list.
        // The holder: the attendee with the best gold bonus, the first of equals.
        bool failed = false;
        int holder = -1;
        for (int i = 0; i < g.n; ++i) {
            const int b = g.att[i];
            failed |= damage[b] + taken[i] > x.usable[b];
            if (holder < 0 || x.bonus[b] > x.bonus[g.att[holder]]) holder = i;
        }
        if (failed) holder = -1;
        if (holder >= 0 && T + capture <= static_cast<float>(p.horizon)) s.value += x.worth[c][g.att[holder]];
        if (attended != nullptr) {
            debug_block({ std::printf("OPENSIM g%d clear %.0f attendees %d holder %d%s\n", C.group, T, g.n, holder >= 0 ? g.att[holder] : -1, failed ? " failed" : ""); });
        }
        for (int i = 0; i < g.n; ++i) {
            const int b = g.att[i];
            s.att[b] = -1, s.loc[b] = c, ++s.k[b];
            if (attended && worked[b] < max_steps) (*attended)[b][worked[b]++] = static_cast<std::int8_t>(c);
            damage[b] += taken[i];
            free[b] = i == holder ? T + capture : T;
            if (damage[b] > x.usable[b]) {
                free[b] += x.home[c];
                s.loc[b] = -1, damage[b] = 0;
            }
        }
        g.back = failed ? never : T + capture + x.respawn[c], g.n = 0, g.clear = never;
    }

    // Body b, free at t, joins its next listed group still to clear when it arrives.
    void choose(int b, float t, std::uint32_t& loaded) {
        const Problem& p = p_;
        const Tables& x = x_;
        const Lists& plan = plan_;
        State& s = s_;
        const float H = static_cast<float>(p.horizon);
        auto& k = s.k;
        auto& free = s.free;
        while (k[b] < max_steps && plan[b][k[b]] >= 0) {
            if constexpr (Record) last = k[b];
            const int c = plan[b][k[b]];
            const float a = t + x.walk[b][s.loc[b] + 1][c];
            if (a >= H) break;
            auto& g = group(c, loaded);
            const float start = std::max(a, g.back);
            if (start - a > static_cast<float>(wait_most) || (g.n > 0 && g.clear <= start)) {
                ++k[b];
                continue;
            }
            int at = g.n++;
            for (; at > 0 && g.arr[at - 1] > start; --at) g.att[at] = g.att[at - 1], g.arr[at] = g.arr[at - 1];
            g.att[at] = static_cast<std::int8_t>(b), g.arr[at] = start;
            g.clear = clear_end(x, p.cand[c], g);
            // Attendees the sooner clear leaves arriving after it walked for nothing (the latest: the list ends with them).
            for (int i = 0; i < g.n; ++i) {
                if (g.arr[i] > g.clear) {
                    for (int j = i; j < g.n; ++j) {
                        const int o = g.att[j];
                        free[o] = g.arr[j], s.att[o] = -1, s.loc[o] = c, ++k[o];
                    }
                    g.n = i;
                    break;
                }
                free[g.att[i]] = g.clear;
            }
            s.att[b] = c;
            return;
        }
        if constexpr (Record)
            if (k[b] < max_steps) last = k[b]; // read the list's end
        free[b] = never;
    }

    void start() {
        s_.loc.fill(-1), s_.att.fill(-1);
        for (int i = p_.bodies; i < 8; ++i) s_.free[i] = __builtin_inff();
    }

    // From state s (fresh after start(), or a snapshot) to the end.
    float run() {
        const Problem& p = p_;
        State& s = s_;
        Trace* const trace = trace_;
        Lists* const attended = Record || Lazy ? nullptr : attended_;
        std::uint32_t loaded = 0;
        const float H = static_cast<float>(p.horizon);
        for (; s.guard < 64 * max_bodies; ++s.guard) {
            // The first body of least free time, if under the horizon.
            const v128_t lo = wasm_v128_load(&s.free[0]), hi = wasm_v128_load(&s.free[4]);
            v128_t m = wasm_f32x4_pmin(lo, hi);
            m = wasm_f32x4_pmin(m, wasm_i32x4_shuffle(m, m, 2, 3, 0, 1));
            m = wasm_f32x4_pmin(m, wasm_i32x4_shuffle(m, m, 1, 0, 3, 2));
            if (!(wasm_f32x4_extract_lane(m, 0) < H)) break;
            const int b = __builtin_ctz(static_cast<unsigned>(wasm_i32x4_bitmask(wasm_f32x4_eq(lo, m)) | wasm_i32x4_bitmask(wasm_f32x4_eq(hi, m)) << 4));
            if (s.att[b] >= 0) finalize(s.att[b], loaded);
            else if constexpr (Record) {
                const int i = trace->n++;
                std::memcpy(&trace->state[i], &s, snapshot_bytes(p));
                last = -1;
                choose(b, s.free[b], loaded);
                trace->mark[i] = {b, last};
            } else choose(b, s.free[b], loaded);
        }
        if (attended)
            for (int b = 0; b < p.bodies; ++b)
                if (s.att[b] >= 0 && worked[b] < max_steps) (*attended)[b][worked[b]++] = static_cast<std::int8_t>(s.att[b]);
        return s.value;
    }

    static std::size_t snapshot_bytes(const Problem& p) { return offsetof(State, group) + static_cast<std::size_t>(p.cands) * sizeof(GroupState); }
};

struct Unit {
    float dps = 0, bonus = 1;
    int range = 1, lead = 0; // the body whose start tile it walks from
};

// Each unit in turn takes the unclaimed group of best value per round (walk, clear, capture) from where its
// last one left it, until the horizon.
void greedy(const Problem& p, const std::array<Unit, max_bodies>& units, int n, std::array<std::array<std::int8_t, max_steps>, max_bodies>& out) {
    std::array<bool, max_cands> claimed{};
    std::array<float, max_bodies> t{};
    std::array<int, max_bodies> loc, len{};
    loc.fill(-1);
    for (auto& l : out) l.fill(-1);
    for (int round = 0; round < max_steps; ++round)
        for (int u = 0; u < n; ++u) {
            int best = -1;
            float best_rate = 0, best_rounds = 0;
            for (int c = 0; c < p.cands; ++c) {
                if (claimed[c]) continue;
                const auto& C = p.cand[c];
                const int d = loc[u] < 0 ? p.body[units[u].lead].from_spawn[c] : p.steps[loc[u]][c];
                const float rounds = static_cast<float>(std::max(0, d - units[u].range)) + C.total / units[u].dps + capture;
                const float rate = (C.gems + p.per_gold * C.gold * units[u].bonus) / rounds;
                if (t[u] + rounds <= static_cast<float>(p.horizon) + capture && rate > best_rate) best = c, best_rate = rate, best_rounds = rounds;
            }
            if (best < 0) continue;
            claimed[best] = true, out[u][len[u]++] = static_cast<std::int8_t>(best), loc[u] = best, t[u] += best_rounds;
        }
}

struct Rng {
    std::uint32_t s = 0x9e3779b9u;
    std::uint32_t next() { return s ^= s << 13, s ^= s >> 17, s ^= s << 5; }
    int below(int n) { return static_cast<int>(next() % static_cast<std::uint32_t>(n)); }
};

int length(const std::array<std::int8_t, max_steps>& l) {
    int n = 0;
    while (n < max_steps && l[n] >= 0) ++n;
    return n;
}

} // namespace

namespace {
Tables tables;

float run_plan(const Problem& p, const Lists& plan, Lists* attended) {
    if (attended)
        for (auto& l : *attended) l.fill(-1);
    State st;
    Sim<false> s{p, tables, plan, attended, nullptr, st};
    s.start();
    return s.run();
}
} // namespace

float simulate(const Problem& p, const Lists& plan, Lists* attended) {
    tables.build(p);
    return run_plan(p, plan, attended);
}

Lists solve(const Problem& p, std::uint64_t fuel_floor, float& value, int& iterations) {
    Lists best;
    for (auto& l : best) l.fill(-1);
    value = 0, iterations = 0;
    if (p.bodies == 0 || p.cands == 0) return best;
    tables.build(p);
    const auto unit_of = [&](int b) { return Unit{p.body[b].dps, p.body[b].bonus, p.body[b].range, b}; };
    const auto join = [&](Unit u, int b) {
        u.dps += p.body[b].dps, u.bonus = std::max(u.bonus, p.body[b].bonus), u.range = std::min(u.range, p.body[b].range);
        return u;
    };
    // Seeds: every body alone; the whole team as one; pairs in id order (Cassi and Issac together).
    std::array<Unit, max_bodies> units;
    Lists seed, by_unit;
    const auto take = [&](const Lists& plan) {
        const float v = run_plan(p, plan, nullptr);
        if (v > value) value = v, best = plan;
    };
    for (int b = 0; b < p.bodies; ++b) units[b] = unit_of(b);
    greedy(p, units, p.bodies, seed);
    take(seed);
    units[0] = unit_of(0);
    for (int b = 1; b < p.bodies; ++b) units[0] = join(units[0], b);
    greedy(p, units, 1, by_unit);
    for (int b = 0; b < p.bodies; ++b) seed[b] = by_unit[0];
    take(seed);
    const int pairs = (p.bodies + 1) / 2;
    for (int u = 0; u < pairs; ++u) units[u] = 2 * u + 1 < p.bodies ? join(unit_of(2 * u), 2 * u + 1) : unit_of(2 * u);
    greedy(p, units, pairs, by_unit);
    for (int b = 0; b < p.bodies; ++b) seed[b] = by_unit[b / 2];
    take(seed);
    // Local search over the lists: insert, drop, swap, copy another body's step (a joint clear) or replace.
    Rng rng;
    int total = 0;
    for (int b = 0; b < p.bodies; ++b) total += length(best[b]);
    static Trace trace;
    static State scratch;
    const std::size_t bytes = Sim<false>::snapshot_bytes(p);
    // The best's run recorded from its mark `from` on (all of it when from < 0).
    const auto record = [&](int from) {
        Sim<true> r{p, tables, best, nullptr, &trace, scratch};
        if (from < 0) trace.n = 0, scratch = State{}, r.start();
        else trace.n = from, std::memcpy(&scratch, &trace.state[from], bytes);
        r.run();
        trace.index(p.bodies);
    };
    record(-1);
    while (iterations < params::open_plan::iterations && fuel_ok(fuel_floor)) {
        ++iterations;
        Lists cand = best;
        const int b = rng.below(p.bodies);
        auto& l = cand[b];
        const int n = length(l);
        const int op = rng.below(5);
        const auto insert = [&](int c) {
            if (n >= max_steps) return false;
            const int at = rng.below(n + 1);
            for (int i = n; i > at; --i) l[i] = l[i - 1];
            l[at] = static_cast<std::int8_t>(c);
            return true;
        };
        bool made = false;
        if (op == 0) made = insert(rng.below(p.cands));
        else if (op == 1 && n > 0) {
            const int at = rng.below(n);
            for (int i = at; i + 1 < max_steps; ++i) l[i] = l[i + 1];
            l[max_steps - 1] = -1, made = true;
        } else if (op == 2 && n > 1) {
            const int i = rng.below(n), j = rng.below(n);
            std::swap(l[i], l[j]), made = i != j;
        } else if (op == 3) {
            const int o = rng.below(p.bodies), m = length(cand[o]);
            if (o != b && m > 0) made = insert(cand[o][rng.below(m)]);
        } else if (op == 4 && n > 0) {
            l[rng.below(n)] = static_cast<std::int8_t>(rng.below(p.cands)), made = true;
        }
        if (!made) continue;
        // simulate(p, cand), resumed from the best's run where they part (Trace).
        int d = 0;
        while (d < max_steps && l[d] == best[b][d]) ++d;
        const int m = d < max_steps ? trace.first[b][d] : trace.n;
        float v = value;
        if (m < trace.n) {
            std::memcpy(&scratch, &trace.state[m], offsetof(State, group));
            v = Sim<false, true>{p, tables, cand, nullptr, nullptr, scratch, &trace.state[m]}.run();
        }
        const int t = total + length(l) - length(best[b]);
        if (v > value || (v == value && t < total)) {
            value = v, best = cand, total = t;
            if (m < trace.n) record(m);
        }
    }
    return best;
}

} // namespace aph::open_plan
