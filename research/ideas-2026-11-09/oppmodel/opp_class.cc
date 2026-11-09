#include "opp_class.h"

#include <cmath>

#include "opp_tables.h"
#include "opp_token.h"
#include "world.h"

namespace aph::opp {
namespace {

// Indexed by cambc::champion_type.
constexpr int base_health[13] = {1200, 1000, 900, 600, 900, 650, 700, 1200, 700, 900, 1000, 900, 1000};
// Fish's rank order among equal base health: type order, but Heart of Ruin before Varg.
constexpr float tie[13] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 9.5f};

constexpr int max_enemies = 8;
// Live trace: plain printf in release builds (debug_block is compiled out on the platform). Off
// except in the copy that checks the posterior live.
constexpr bool live_trace = false;

struct State {
    bool started = false;
    int n = 0;                           // enemy bodies
    std::int8_t rank[max_enemies]{};     // Fish's rank of each enemy
    std::int8_t res0[max_enemies]{};     // residue of its first counted nonzero value, -1 none
    bool read[max_enemies]{};
    std::int32_t last[max_enemies]{};
    float base[3]{};             // log prior + pick order, per class
    float sub[tables::subs]{};   // tempered token log-likelihood per sub-model
    int shown = -1, shown_round = -1000; // live trace: last argmax printed and when
    std::uint32_t pending = 0;   // bit j: enemy j's read this turn differs from the last counted one
    bool dirty = true;           // post is stale
    float lp[3]{};               // class log scores, from score()
    Posterior post;
    Evidence ev;
};
State st;

bool tank(cambc::champion_type t) { return t == cambc::champion_type::heart_of_ruin || t == cambc::champion_type::marcella; }

// Class log scores: each class's best sub-model (max, not log-sum-exp: no transcendental calls in
// fight turns), less the log of its kept weights, plus prior and pick order.
void score() {
    const bool gate = 100 % (st.n + 1) == 0;
    for (int c = 0; c < 3; ++c) {
        float m = -1e30f, weight = 0;
        for (int k = 0; k < tables::subs; ++k)
            if (tables::sub_class[k] == c && !(gate && tables::sub_gated[k])) {
                m = std::fmax(m, tables::sub_log_w[k] + st.sub[k]);
                weight += tables::sub_w[k];
            }
        st.lp[c] = st.base[c] + m - (weight < 0.999f ? std::log(weight) : 0.0f);
    }
}

int top_class() { return st.lp[0] >= st.lp[1] && st.lp[0] >= st.lp[2] ? 0 : st.lp[1] >= st.lp[2] ? 1 : 2; }

void normalise() {
    const float m = std::fmax(st.lp[0], std::fmax(st.lp[1], st.lp[2]));
    float e[3];
    for (int c = 0; c < 3; ++c) e[c] = st.lp[c] - m > -40 ? std::exp(st.lp[c] - m) : 0.0f;
    const float s = e[0] + e[1] + e[2];
    st.post = {e[0] / s, e[1] / s, e[2] / s};
    st.dirty = false;
}

void start(const World& world) {
    st.started = true;
    st.n = std::min(static_cast<int>(world.enemies.size()), max_enemies);
    for (int c = 0; c < 3; ++c) st.base[c] = tables::prior[c];
    // Fish's rank: 2 + place by base health, descending.
    for (int j = 0; j < st.n; ++j) {
        const auto tj = static_cast<int>(world.enemies[j].type);
        int place = 0;
        for (int k = 0; k < st.n; ++k) {
            const auto tk = static_cast<int>(world.enemies[k].type);
            if (base_health[tk] > base_health[tj] || (base_health[tk] == base_health[tj] && tie[tk] < tie[tj])) ++place;
        }
        st.rank[j] = static_cast<std::int8_t>(2 + place);
        st.res0[j] = -1;
    }
    // Pick order given the champion: handles run in pick order, Issac on Cassi's pick.
    int slots = 0;
    for (int j = 0; j < st.n; ++j) slots += world.enemies[j].type != cambc::champion_type::issac;
    float draft[3]{};
    if (slots >= 3 && slots <= 5) {
        int slot = -1;
        for (int j = 0; j < st.n; ++j) {
            const auto t = static_cast<int>(world.enemies[j].type);
            if (world.enemies[j].type == cambc::champion_type::issac) continue;
            ++slot;
            const int pick = t <= 3 ? t : t - 1;
            for (int c = 0; c < 3; ++c) draft[c] += tables::draft[pick][slots - 3][c][slot];
        }
    }
    // Pick order shifts at most draft_cap between classes: drafts change between versions.
    const float top = std::fmax(draft[0], std::fmax(draft[1], draft[2]));
    for (int c = 0; c < 3; ++c) st.base[c] += std::fmax(draft[c], top - tables::draft_cap);
    score();
}

} // namespace

void note(int j, std::int32_t v) {
    if (j < max_enemies && (!st.read[j] || st.last[j] != v)) st.pending |= 1u << j;
}

void observe(const World& world) {
    if (!st.started) start(world);
    const int now = world.round;
    bool changed = false;
    for (std::uint32_t bits = st.pending; bits; bits &= bits - 1) {
        const int j = __builtin_ctz(bits);
        if (j >= st.n) continue;
        const auto& b = world.enemies[j];
        if (!b.visible || !b.alive || b.priority_round != now) continue;
        const std::int32_t v = b.priority;
        if (st.read[j] && st.last[j] == v) continue;
        st.read[j] = true;
        st.last[j] = v;
        const Token t = token(v, st.n, st.rank[j], st.res0[j], tank(b.type), b.health, b.max_health, b.shield, b.gems);
        if (v != 0 && st.res0[j] < 0) {
            const std::int64_t n1 = st.n + 1;
            st.res0[j] = static_cast<std::int8_t>(((-static_cast<std::int64_t>(v)) % n1 + n1) % n1);
        }
        for (int k = 0; k < tables::subs; ++k) st.sub[k] += tables::tau * tables::log_p[k][t];
        changed = true;
        debug_block({ std::printf("OPPT %d %d %d %d %d %.1f %.1f %.1f %d\n", now, static_cast<int>(world.me().handle), j, v, static_cast<int>(t), b.health, b.max_health, b.shield, b.gems); });
        auto& e = st.ev;
        if (t == zero) ++e.zero_hits;
        else if (t == fish_quiet || t == fish_contact || t == fish_mod) {
            ++e.fish_hits;
            if (e.first_round_fish < 0) e.first_round_fish = static_cast<std::int16_t>(now);
        } else if (t >= mite_quiet) {
            if (t == other) ++e.other_hits;
            else {
                ++e.mite_hits;
                if (e.first_round_mite < 0) e.first_round_mite = static_cast<std::int16_t>(now);
            }
        } else ++e.other_hits;
    }
    st.pending = 0;
    if (changed) score(), st.dirty = true;
    if constexpr (live_trace) {
        // First read, argmax changes and every 100 rounds.
        const int top = top_class();
        if (top != st.shown || now - st.shown_round >= 100) {
            if (st.dirty) normalise();
            const auto& p = st.post;
            std::printf("OPPL %d %d %.4f %.4f %.4f %d %d %d %d\n", now, static_cast<int>(world.me().handle), p.fish, p.mite, p.other,
                        st.ev.fish_hits, st.ev.mite_hits, st.ev.other_hits, st.ev.zero_hits);
            st.shown = top;
            st.shown_round = now;
        }
    }
    if (!changed) return;
    debug_block({ if (st.dirty) normalise(); std::printf("OPPC %d %d %.4f %.4f %.4f\n", now, static_cast<int>(world.me().handle), st.post.fish, st.post.mite, st.post.other); });
}

const Posterior& posterior(const World& world) {
    if (!st.started) start(world);
    if (st.dirty) normalise();
    return st.post;
}

const Evidence& evidence(const World&) { return st.ev; }

} // namespace aph::opp
