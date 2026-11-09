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
    Posterior post;
    Evidence ev;
};
State st;

bool tank(cambc::champion_type t) { return t == cambc::champion_type::heart_of_ruin || t == cambc::champion_type::marcella; }

void normalise() {
    // Each class: its sub-models' weighted likelihoods summed (log-sum-exp), plus prior and draft.
    float lp[3];
    const bool gate = 100 % (st.n + 1) == 0;
    for (int c = 0; c < 3; ++c) {
        float m = -1e30f;
        for (int k = 0; k < tables::subs; ++k)
            if (tables::sub_class[k] == c && !(gate && tables::sub_gated[k])) m = std::fmax(m, tables::sub_log_w[k] + st.sub[k]);
        float sum = 0, weight = 0; // weight: the kept sub-models' total, to renormalise a gated class
        for (int k = 0; k < tables::subs; ++k)
            if (tables::sub_class[k] == c && !(gate && tables::sub_gated[k])) {
                sum += std::exp(tables::sub_log_w[k] + st.sub[k] - m);
                weight += std::exp(tables::sub_log_w[k]);
            }
        lp[c] = st.base[c] + m + std::log(sum / weight);
    }
    const float m = std::fmax(lp[0], std::fmax(lp[1], lp[2]));
    const float a = std::exp(lp[0] - m), b = std::exp(lp[1] - m), c = std::exp(lp[2] - m);
    const float s = a + b + c;
    st.post = {a / s, b / s, c / s};
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
    normalise();
}

} // namespace

void observe(const World& world) {
    if (!st.started) start(world);
    const int now = world.round;
    bool changed = false;
    for (int j = 0; j < st.n; ++j) {
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
    if (changed) normalise();
    if constexpr (live_trace) {
        // First read, argmax changes and every 100 rounds.
        const auto& p = st.post;
        const int top = p.fish >= p.mite && p.fish >= p.other ? 0 : p.mite >= p.other ? 1 : 2;
        if (top != st.shown || now - st.shown_round >= 100) {
            std::printf("OPPL %d %d %.4f %.4f %.4f %d %d %d %d\n", now, static_cast<int>(world.me().handle), p.fish, p.mite, p.other,
                        st.ev.fish_hits, st.ev.mite_hits, st.ev.other_hits, st.ev.zero_hits);
            st.shown = top;
            st.shown_round = now;
        }
    }
    if (!changed) return;
    debug_block({ std::printf("OPPC %d %d %.4f %.4f %.4f\n", now, static_cast<int>(world.me().handle), st.post.fish, st.post.mite, st.post.other); });
}

const Posterior& posterior(const World& world) {
    if (!st.started) start(world);
    return st.post;
}

const Evidence& evidence(const World&) { return st.ev; }

} // namespace aph::opp
