// probe-tavi-sell: Tavi's sale on spawn. How many sales a turn (one call, several types, counts), what each item
// refunds (shard, emblem), buying after a sale, a sale off spawn, and Health bought off spawn then sold on spawn.
// Self-play; only the side whose spawn sorts first acts, with Tavi (its first pick). It captures cluster-only groups
// until it has 200 gold, buys off spawn (5 Power Focus shards, which make an emblem, and 1 Jungle Health),
// tries a sale there, walks home and runs one sale test a turn.
//   cambc run tools/probes/probe-tavi-sell tools/probes/probe-tavi-sell --map 00packs --rounds 250 --fuel 50000000 -o <dir>
// Result (2026-11-08, cambc 5.0.0): off spawn, "Selling items requires your team's spawn tiles". On spawn, round 111:
// a Jungle Health shard sold (+30 gold, health and max 975 -> 900), the Power Focus emblem sold in the same turn (+150,
// Focus 170 -> 110), then a buy. Later turns: a count of 2 sold in one call (+60), the same type sold twice in a turn.
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <vector>

using cambc::vec2;
using cambc::team;
using IT = cambc::item_type;
using D = cambc::champion_draft;

namespace {

enum Phase { FARM, BUY, HOME, SELL, DONE };
Phase g_phase = FARM;
int g_role = -1;
int g_step = 0;
std::vector<cambc::map::camp_group> g_targets;
size_t g_next = 0;

bool acting_side() {
    const auto a = cambc::map::spawn_region(team::ally).positions().front();
    const auto e = cambc::map::spawn_region(team::enemy).positions().front();
    return a.x + a.y < e.x + e.y;
}

void log_inv(const char* tag) {
    auto& me = cambc::self();
    const auto items = me.item_count();
    std::printf("PROBE %d %s pos=(%d,%d) hp=%.1f max=%.1f str=%.1f foc=%.1f gold=%u can_sell=%d pfs=%u pfe=%u pss=%u jhs=%u mss=%u\n",
                (int)cambc::round_number(), tag, me.position().x, me.position().y, me.health(), me.max_health(), me.strength(), me.focus(),
                me.gold_count(), (int)me.can_sell(), items[IT::power_shard_of_focus], items[IT::power_emblem_of_focus],
                items[IT::power_shard_of_strength], items[IT::jungle_shard_of_health], items[IT::monster_shard_of_strength]);
}

void try_sell(const char* tag, IT t, unsigned n) {
    try {
        cambc::self().sell(t, n);
        std::printf("PROBE %d sell %s n=%u ok\n", (int)cambc::round_number(), tag, n);
    } catch (const cambc::error& e) {
        std::printf("PROBE %d sell %s n=%u err %s\n", (int)cambc::round_number(), tag, n, e.message().c_str());
    }
    log_inv(tag);
}
void try_buy(const char* tag, IT t, unsigned n) {
    try {
        cambc::self().buy(t, n);
        std::printf("PROBE %d buy %s n=%u ok\n", (int)cambc::round_number(), tag, n);
    } catch (const cambc::error& e) {
        std::printf("PROBE %d buy %s n=%u err %s\n", (int)cambc::round_number(), tag, n, e.message().c_str());
    }
    log_inv(tag);
}

bool on_spawn() { return cambc::map::spawn_region(team::ally).is_set(cambc::self().position()); }

vec2 nearest_spawn_tile() {
    auto& me = cambc::self();
    auto ps = cambc::map::spawn_region(team::ally).positions();
    return *std::min_element(ps.begin(), ps.end(), [&](vec2 a, vec2 b) {
        return me.position().chebyshev_distance(a) < me.position().chebyshev_distance(b);
    });
}

bool fight(const cambc::map::camp_group& g) {
    auto& me = cambc::self();
    bool any = false;
    vec2 goal = g.camps().front().spawn_position();
    for (const auto& c : g)
        if (me.position().chebyshev_distance(c.spawn_position()) < me.position().chebyshev_distance(goal)) goal = c.spawn_position();
    int best = 1 << 30;
    for (const auto& c : cambc::vision::camps()) {
        if (static_cast<cambc::handle_camp_group_t>(c.camp_group()) != static_cast<cambc::handle_camp_group_t>(g)) continue;
        any = true;
        if (me.can_attack() && me.attack_tiles().is_set(c.position())) {
            me.attack(c);
            return false;
        }
        const int d = me.position().chebyshev_distance(c.position());
        if (d < best) best = d, goal = c.position();
    }
    if (me.can_move()) me.move_towards(goal);
    return !any && me.position().chebyshev_distance(goal) <= 3;
}

void play_turn() {
    auto& me = cambc::self();
    const int r = (int)cambc::round_number();
    if (g_role < 0) {
        g_role = (acting_side() && me.champion_name() == cambc::champion_type::tavi) ? 1 : 0;
        if (g_role == 1) {
            const vec2 home = me.position();
            for (const auto& g : cambc::map::camp_groups()) {
                bool clusters = true;
                for (const auto& c : g) clusters &= c.kind() == cambc::camp_type::gold_cluster || c.kind() == cambc::camp_type::gem_cluster;
                if (clusters && g.gold_value() > 0) g_targets.push_back(g);
            }
            std::sort(g_targets.begin(), g_targets.end(), [&](const auto& a, const auto& b) {
                return home.chebyshev_distance(a.camps().front().spawn_position()) < home.chebyshev_distance(b.camps().front().spawn_position());
            });
        }
    }
    if (g_role != 1) return;
    switch (g_phase) {
    case FARM: {
        if (me.gold_count() >= 200) { g_phase = BUY; log_inv("farmed"); break; }
        if (g_targets.empty()) break;
        const auto& g = g_targets[g_next % g_targets.size()];
        if (r % 25 == 0) log_inv("farm");
        if (fight(g)) {
            const vec2 t = g.camps().front().spawn_position();
            if (me.position() != t && me.can_move()) me.move_towards(t);
        }
        static unsigned last_gold = 0;
        if (me.gold_count() > last_gold) ++g_next;
        last_gold = me.gold_count();
        break;
    }
    case BUY:
        log_inv(on_spawn() ? "buy-on-spawn" : "buy-off-spawn");
        try_buy("pf5", IT::power_shard_of_focus, 5);
        try_buy("jh1", IT::jungle_shard_of_health, 1);
        try_sell("off-spawn-jh", IT::jungle_shard_of_health, 1);
        g_phase = HOME;
        break;
    case HOME:
        if (!on_spawn()) {
            auto ps = cambc::map::spawn_region(team::ally).positions();
            std::sort(ps.begin(), ps.end(), [&](vec2 a, vec2 b) { return me.position().chebyshev_distance(a) < me.position().chebyshev_distance(b); });
            for (const vec2 t : ps) {
                if (!me.can_move()) break;
                try { me.move_towards(t); } catch (const cambc::error&) {}
            }
            break;
        }
        log_inv("arrived");
        g_phase = SELL;
        break;
    case SELL:
        switch (g_step++) {
        case 0: // Health bought off spawn, sold on spawn; then a second sale (another type) and a buy in the same turn
            try_sell("jh1", IT::jungle_shard_of_health, 1);
            try_sell("pfe1-same-turn", IT::power_emblem_of_focus, 1);
            try_buy("ms1-after-sale", IT::monster_shard_of_strength, 1);
            break;
        case 1: // the emblem
            try_sell("pfe1", IT::power_emblem_of_focus, 1);
            break;
        case 2: // a count of 2 in one call
            try_buy("ms1", IT::monster_shard_of_strength, 1);
            try_sell("ms2", IT::monster_shard_of_strength, 2);
            break;
        case 3: // the same type twice in a turn, a buy between
            try_buy("ms1", IT::monster_shard_of_strength, 2);
            try_sell("ms1", IT::monster_shard_of_strength, 1);
            try_sell("ms1-again", IT::monster_shard_of_strength, 1);
            break;
        case 4: // a shard not owned
            try_sell("pss-not-owned", IT::power_shard_of_strength, 1);
            try_sell("ms1-last", IT::monster_shard_of_strength, 1);
            break;
        default: g_phase = DONE; log_inv("done"); break;
        }
        break;
    case DONE: break;
    }
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    const auto theirs = cambc::draft::current_draft(team::enemy);
    auto taken = [&](D d) { return std::find(mine.begin(), mine.end(), d) != mine.end() || std::find(theirs.begin(), theirs.end(), d) != theirs.end(); };
    const std::vector<D> a{ D::tavi, D::vesper_vale, D::stellar, D::prism, D::marcella, D::varg };
    const std::vector<D> b{ D::ryth, D::stellar, D::prism, D::marcella, D::vesper_vale, D::varg };
    for (auto d : acting_side() ? a : b) if (!taken(d)) { cambc::draft::pick(d); return; }
}
} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else play_turn();
        } catch (const cambc::error& e) {
            std::printf("PROBE %d err %s\n", (int)cambc::round_number(), e.message().c_str());
        } catch (const std::exception& e) { std::printf("PROBE err %s\n", e.what()); }
        cambc::end_turn();
    }
}
