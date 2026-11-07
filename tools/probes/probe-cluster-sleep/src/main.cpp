// probe-cluster-sleep: within what distance does a champion keep an awake gem or gold cluster awake (clusters have no
// attack range)? Map clustersleep.map26a (makemap.mjs). Each champion runs one scenario in its team's own (rotated)
// coordinates: team A 0-4, team B 5-9, by pick (Vesper, Stellar, Prism, Tavi, Ryth). Everyone walks to its wake tile,
// hits its target once in round 45 (before that no camp is awake, so the walk keeps nothing awake), holds at the hold
// tile through round 60, then stands at a control tile 6+ from every camp of its scenario (they should all sleep).
//   0 gem alone, hold (+3,0)        1 gem alone, hold (+4,0)       2 gold alone, hold (+3,0)   3 gold alone, hold (+4,0)
//   4 gem alone, hold (+3,+3)       5 gold alone, hold (+3,-3)
//   6 elk-gem-gold row, hold: gold 3, gem 4, elk 5      7 elk-gold-gem row, hold: gem 3, gold 4, elk 5
//   8 gem+gold pair, hold: gem 3, gold 4                9 elk + gem below it, hold: elk 4, gem 4
//   node tools/probes/probe-cluster-sleep/makemap.mjs
//   cambc run tools/probes/probe-cluster-sleep tools/probes/probe-cluster-sleep \
//     --map tools/probes/probe-cluster-sleep/clustersleep.map26a --rounds 75 --fuel 50000000 -o <dir>
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <vector>

using cambc::vec2;
using cambc::team;
using D = cambc::champion_draft;
using CT = cambc::champion_type;
namespace M = cambc::map;

namespace {

bool team_a() { return M::spawn_region(team::ally).is_set({ 0, 0 }); }
vec2 T(vec2 p) { return team_a() ? p : vec2{ M::width() - 1 - p.x, M::height() - 1 - p.y }; }
int R() { return (int)cambc::round_number(); }

struct scenario { std::vector<vec2> camps; vec2 target, wake, hold, control; };
const scenario S[10] = {
    { { { 8, 4 } }, { 8, 4 }, { 9, 4 }, { 11, 4 }, { 14, 4 } },
    { { { 8, 10 } }, { 8, 10 }, { 9, 10 }, { 12, 10 }, { 15, 10 } },
    { { { 8, 16 } }, { 8, 16 }, { 9, 16 }, { 11, 16 }, { 14, 16 } },
    { { { 8, 22 } }, { 8, 22 }, { 9, 22 }, { 12, 22 }, { 15, 22 } },
    { { { 8, 28 } }, { 8, 28 }, { 9, 29 }, { 11, 31 }, { 14, 31 } },
    { { { 30, 4 } }, { 30, 4 }, { 31, 3 }, { 33, 1 }, { 36, 1 } },
    { { { 30, 10 }, { 31, 10 }, { 32, 10 } }, { 32, 10 }, { 33, 10 }, { 35, 10 }, { 38, 10 } },
    { { { 30, 16 }, { 31, 16 }, { 32, 16 } }, { 32, 16 }, { 33, 16 }, { 35, 16 }, { 38, 16 } },
    { { { 30, 22 }, { 31, 22 } }, { 30, 22 }, { 29, 22 }, { 27, 22 }, { 24, 22 } },
    { { { 30, 28 }, { 30, 29 } }, { 30, 29 }, { 31, 29 }, { 34, 28 }, { 37, 28 } },
};
constexpr int WAKE_ROUND = 45, HOLD_UNTIL = 60;

int scenario_index() {
    const CT order[5] = { CT::vesper_vale, CT::stellar, CT::prism, CT::tavi, CT::ryth };
    const CT me = cambc::self().champion_name();
    for (int i = 0; i < 5; ++i) if (order[i] == me) return i + (team_a() ? 0 : 5);
    return -1;
}

int woke = -1;

void log(int si) {
    auto& me = cambc::self();
    const vec2 p = me.position();
    std::printf("PROBE r%d s%d pos=(%d,%d) hp=%.0f |", R(), si, T(p).x, T(p).y, (double)me.health());
    for (vec2 lp : S[si].camps) {
        const vec2 cp = T(lp);
        const char* st = "dead";
        const char* kind = "?";
        double hp = 0;
        for (const auto& c : cambc::vision::camps())
            if (c.position() == cp) {
                st = c.is_awake() ? "awake" : c.is_asleep() ? "asleep" : "dead";
                kind = c.is_elk() ? "elk" : c.is_gem_cluster() ? "gem" : c.is_gold_cluster() ? "gold" : "other";
                hp = (double)c.health();
            }
        std::printf(" %s(%d,%d) d%d %s %.0f", kind, lp.x, lp.y, (int)p.chebyshev_distance(cp), st, hp);
    }
    std::printf("\n");
}

void go(vec2 t) {
    auto& me = cambc::self();
    if (me.position() != T(t) && me.can_move()) me.move_towards(T(t));
}

void play() {
    const int si = scenario_index();
    if (si < 0) return;
    const scenario& s = S[si];
    auto& me = cambc::self();
    if (R() >= WAKE_ROUND - 1) log(si);
    if (woke < 0) {
        go(s.wake);
        if (R() >= WAKE_ROUND && me.position() == T(s.wake) && me.can_attack())
            for (const auto& c : cambc::vision::camps())
                if (c.position() == T(s.target)) {
                    me.attack(c);
                    woke = R();
                    std::printf("PROBE r%d s%d attacked target\n", R(), si);
                    break;
                }
        if (R() >= WAKE_ROUND && woke < 0) std::printf("PROBE r%d s%d not ready to wake\n", R(), si);
        return;
    }
    go(R() <= HOLD_UNTIL ? s.hold : s.control);
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    for (auto d : { D::vesper_vale, D::stellar, D::prism, D::tavi, D::ryth })
        if (std::find(mine.begin(), mine.end(), d) == mine.end()) { cambc::draft::pick(d); return; }
}
} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else if (cambc::self().is_alive()) play();
        } catch (const cambc::error& e) {
            std::printf("PROBE r%d err %d %s\n", R(), (int)e.code(), e.message().c_str());
        }
        cambc::end_turn();
    }
}
