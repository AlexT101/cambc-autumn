#include "open_plan.h"
#include <algorithm>
#include <cmath>
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

// Attendees are kept in arrival order (Sim::choose inserts in place).
// The clear's end with these attendees: the members' health pooled, as the order they die in does not change it.
float clear_end(const Problem& p, const Cand& c, const GroupState& g) {
    float left = c.total, rate = 0, t = g.arr[0];
    for (int i = 0; i < g.n; ++i) {
        const float until = i + 1 < g.n ? g.arr[i + 1] : never;
        rate += p.body[g.att[i]].dps;
        if (t + left / rate <= until) return t + left / rate;
        left -= rate * (until - t), t = until;
    }
    return never;
}

// Each attendee's camp damage taken in the clear into `taken`, monsters dying deadliest first: they hit the first
// to arrive until a melee is there, then the healthiest melee.
void clear_damage(const Problem& p, const Cand& c, const GroupState& g, float* taken) {
    for (int i = 0; i < g.n; ++i) taken[i] = 0;
    float strength = c.total_strength;
    if (strength <= 0) return;
    float rate = 0, t = g.arr[0], left = c.hp[0];
    int next = 0, m = 0, tank = -1;
    while (m < c.members) {
        while (next < g.n && g.arr[next] <= t) {
            rate += p.body[g.att[next]].dps;
            const auto& a = p.body[g.att[next]];
            if (tank < 0 || (a.melee && (!p.body[g.att[tank]].melee || a.health > p.body[g.att[tank]].health))) tank = next;
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

struct Sim {
    const Problem& p;
    const Lists& plan;
    Lists* attended;
    std::array<float, max_bodies> free{}, damage{};
    std::array<int, max_bodies> loc{}, k{}, att{}, worked{};
    std::array<GroupState, max_cands> group;
    float value = 0;

    void finalize(int c) {
        auto& g = group[c];
        const auto& C = p.cand[c];
        std::array<float, max_bodies> taken;
        const float T = g.clear;
        clear_damage(p, C, g, taken.data());
        // A clear that takes anyone past its usable health fails: the real one leaves for home part way (and its
        // fire is what sends farm's bodies home), so the plan gets nothing from the group and it leaves the list.
        bool failed = false;
        for (int i = 0; i < g.n; ++i) failed |= damage[g.att[i]] + taken[i] > p.body[g.att[i]].usable;
        int holder = -1;
        for (int i = 0; i < g.n && !failed; ++i)
            if (holder < 0 || p.body[g.att[i]].bonus > p.body[g.att[holder]].bonus) holder = i;
        if (holder >= 0 && T + capture <= static_cast<float>(p.horizon))
            value += C.gems + p.per_gold * C.gold * p.body[g.att[holder]].bonus;
        if (attended) {
            debug_block({ std::printf("OPENSIM g%d clear %.0f attendees %d holder %d%s\n", C.group, T, g.n, holder >= 0 ? g.att[holder] : -1, failed ? " failed" : ""); });
        }
        for (int i = 0; i < g.n; ++i) {
            const int b = g.att[i];
            att[b] = -1, loc[b] = c, ++k[b];
            if (attended && worked[b] < max_steps) (*attended)[b][worked[b]++] = static_cast<std::int8_t>(c);
            damage[b] += taken[i];
            free[b] = i == holder ? T + capture : T;
            if (damage[b] > p.body[b].usable) {
                free[b] += static_cast<float>(std::min(2 * C.home, cambc::constants::recall_time + C.home));
                loc[b] = -1, damage[b] = 0;
            }
        }
        g.back = failed ? never : T + capture + static_cast<float>(C.respawn), g.n = 0, g.clear = never;
    }

    // Body b, free at t, joins its next listed group still to clear when it arrives.
    void choose(int b, float t) {
        const float H = static_cast<float>(p.horizon);
        while (k[b] < max_steps && plan[b][k[b]] >= 0) {
            const int c = plan[b][k[b]];
            const int d = loc[b] < 0 ? p.body[b].from_spawn[c] : p.steps[loc[b]][c];
            const float a = t + static_cast<float>(std::max(0, d - p.body[b].range));
            if (a >= H) break;
            auto& g = group[c];
            const float start = std::max(a, g.back);
            if (start - a > static_cast<float>(wait_most) || (g.n > 0 && g.clear <= start)) {
                ++k[b];
                continue;
            }
            int at = g.n++;
            for (; at > 0 && g.arr[at - 1] > start; --at) g.att[at] = g.att[at - 1], g.arr[at] = g.arr[at - 1];
            g.att[at] = static_cast<std::int8_t>(b), g.arr[at] = start;
            g.clear = clear_end(p, p.cand[c], g);
            // Attendees the sooner clear leaves arriving after it walked for nothing (the latest: the list ends with them).
            for (int i = 0; i < g.n; ++i) {
                if (g.arr[i] > g.clear) {
                    for (int j = i; j < g.n; ++j) {
                        const int o = g.att[j];
                        free[o] = g.arr[j], att[o] = -1, loc[o] = c, ++k[o];
                    }
                    g.n = i;
                    break;
                }
                free[g.att[i]] = g.clear;
            }
            att[b] = c;
            return;
        }
        free[b] = never;
    }

    float run() {
        loc.fill(-1), att.fill(-1);
        const float H = static_cast<float>(p.horizon);
        for (int guard = 0; guard < 64 * max_bodies; ++guard) {
            int b = -1;
            for (int i = 0; i < p.bodies; ++i)
                if (free[i] < H && (b < 0 || free[i] < free[b])) b = i;
            if (b < 0) break;
            if (att[b] >= 0) finalize(att[b]);
            else choose(b, free[b]);
        }
        if (attended)
            for (int b = 0; b < p.bodies; ++b)
                if (att[b] >= 0 && worked[b] < max_steps) (*attended)[b][worked[b]++] = static_cast<std::int8_t>(att[b]);
        return value;
    }
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

float simulate(const Problem& p, const Lists& plan, Lists* attended) {
    if (attended)
        for (auto& l : *attended) l.fill(-1);
    Sim s{p, plan, attended};
    return s.run();
}

Lists solve(const Problem& p, std::uint64_t fuel_floor, float& value, int& iterations) {
    Lists best;
    for (auto& l : best) l.fill(-1);
    value = 0, iterations = 0;
    if (p.bodies == 0 || p.cands == 0) return best;
    const auto unit_of = [&](int b) { return Unit{p.body[b].dps, p.body[b].bonus, p.body[b].range, b}; };
    const auto join = [&](Unit u, int b) {
        u.dps += p.body[b].dps, u.bonus = std::max(u.bonus, p.body[b].bonus), u.range = std::min(u.range, p.body[b].range);
        return u;
    };
    // Seeds: every body alone; the whole team as one; pairs in id order (Cassi and Issac together).
    std::array<Unit, max_bodies> units;
    Lists seed, by_unit;
    const auto take = [&](const Lists& plan) {
        const float v = simulate(p, plan);
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
        const float v = simulate(p, cand);
        int t = 0;
        for (int i = 0; i < p.bodies; ++i) t += length(cand[i]);
        if (v > value || (v == value && t < total)) value = v, best = cand, total = t;
    }
    return best;
}

} // namespace aph::open_plan
