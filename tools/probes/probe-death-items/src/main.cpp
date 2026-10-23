// probe-death-items: does a champion keep its consumables (teleport crystal, altar lock), shards and gold through death?
// Self-play; only the side whose spawn sorts first acts, with one champion (its first pick). It captures cluster-only
// camp groups until it has 70 gold, buys a crystal, a lock and a shard on spawn, then wakes the nearest wolf group and
// stands in its range until it dies. Logs inventory every turn from the purchase until a few turns after respawn.
//   cambc run tools/probes/probe-death-items tools/probes/probe-death-items \
//     --map 00packs --rounds 160 --fuel 50000000 -o <dir>
// Result (2026-10-23): bought crystal=1 lock=1 shard=1 gold=50 in round 62; killed by wolves in round 96; every dead
// turn and the respawn turn (157) still read crystal=1 lock=1 shard=1 gold=50.
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <vector>

using cambc::vec2;
using cambc::team;
using CT = cambc::consumable_type;
using IT = cambc::item_type;
using D = cambc::champion_draft;

namespace {

enum Phase { FARM, HOME, DIE, DEAD, DONE };
Phase g_phase = FARM;
int g_role = -1;  // 1 = subject
int g_respawn_round = -1;
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
    int shards = 0;
    for (std::uint32_t i = 0; i < static_cast<std::uint32_t>(IT::count); ++i) shards += (int)items[IT(i)];
    std::printf("PROBE %d %s alive=%d pos=(%d,%d) hp=%.1f gold=%u crystal=%u lock=%u items=%d mhs=%u\n",
                (int)cambc::round_number(), tag, (int)me.is_alive(), me.position().x, me.position().y, me.health(),
                me.gold_count(), me.consumables()[CT::tp_crystal].count(), me.consumables()[CT::altar_lock].count(), shards,
                items[IT::monster_shard_of_health]);
}

bool on_spawn() { return cambc::map::spawn_region(team::ally).is_set(cambc::self().position()); }

vec2 nearest_spawn_tile() {
    auto& me = cambc::self();
    auto ps = cambc::map::spawn_region(team::ally).positions();
    return *std::min_element(ps.begin(), ps.end(), [&](vec2 a, vec2 b) {
        return me.position().chebyshev_distance(a) < me.position().chebyshev_distance(b);
    });
}

// Attack a visible live member of group g if in range; else walk towards the nearest one. Returns true once all are dead.
bool fight(const cambc::map::camp_group& g, bool wake_only) {
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
            if (wake_only && c.is_awake()) return false;
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
        g_role = (acting_side() && me.champion_name() == cambc::champion_type::vendetta) ? 1 : 0;
        if (g_role == 1) {
            const vec2 home = me.position();
            for (const auto& g : cambc::map::camp_groups()) {
                bool clusters = true;
                for (const auto& c : g) clusters &= c.kind() == cambc::camp_type::gold_cluster || c.kind() == cambc::camp_type::gem_cluster;
                std::printf("PROBE %d group gold=%u first=(%d,%d) n=%d clusters=%d\n", r, g.gold_value(),
                            g.camps().front().spawn_position().x, g.camps().front().spawn_position().y, (int)g.camps().size(), (int)clusters);
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
        if (me.gold_count() >= 70 || g_next >= g_targets.size()) { g_phase = HOME; log_inv("farmed"); break; }
        const auto& g = g_targets[g_next];
        if (r % 5 == 0) log_inv("farm");
        if (fight(g, false)) {
            // stand on a tile of the dead group until paid
            const vec2 t = g.camps().front().spawn_position();
            if (me.position() != t && me.can_move()) me.move_towards(t);
        }
        static unsigned last_gold = 0;
        if (me.gold_count() > last_gold) { log_inv("paid"); ++g_next; }
        last_gold = me.gold_count();
        break;
    }
    case HOME:
        if (!on_spawn()) { if (me.can_move()) me.move_towards(nearest_spawn_tile()); break; }
        if (me.can_buy(CT::tp_crystal)) me.buy(CT::tp_crystal);
        if (me.can_buy(CT::altar_lock)) me.buy(CT::altar_lock);
        if (me.can_buy(IT::monster_shard_of_health)) me.buy(IT::monster_shard_of_health);
        log_inv("bought");
        g_phase = DIE;
        break;
    case DIE: {
        if (!me.is_alive()) { g_phase = DEAD; log_inv("dead"); break; }
        log_inv("die");
        static const auto groups = cambc::map::camp_groups();
        static int best = -1;
        if (best < 0)
            for (int i = 0; i < (int)groups.size(); ++i)
                for (const auto& c : groups[i])
                    if (c.kind() == cambc::camp_type::wolf &&
                        (best < 0 || me.position().chebyshev_distance(c.spawn_position()) <
                                         me.position().chebyshev_distance(groups[best].camps().front().spawn_position())))
                        best = i;
        if (best >= 0) fight(groups[best], true);
        break;
    }
    case DEAD:
        log_inv(me.is_alive() ? "respawned" : "dead");
        if (me.is_alive() && g_respawn_round < 0) g_respawn_round = r;
        if (g_respawn_round >= 0 && r >= g_respawn_round + 2) g_phase = DONE;
        break;
    case DONE: break;
    }
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    const auto theirs = cambc::draft::current_draft(team::enemy);
    auto taken = [&](D d) { return std::find(mine.begin(), mine.end(), d) != mine.end() || std::find(theirs.begin(), theirs.end(), d) != theirs.end(); };
    const std::vector<D> a{ D::vendetta, D::vesper_vale, D::stellar, D::prism, D::marcella, D::varg };
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
