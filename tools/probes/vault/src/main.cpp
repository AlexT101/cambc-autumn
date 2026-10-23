// vault probe: teleport into a walled-in ("vault") altar, tribute there, recall out; watchers outside
// log what they can see of the vault. Both teams run it:
//   cambc run tools/probes/vault tools/probes/vault --map collision --rounds 300 --fuel 50000000
// Champion 0 farms the nearest camp groups paying gems and gold, buys a crystal on spawn, walks to the launch
// tile of the cheapest vault route, teleports in, tributes and recalls. Champion 1 stands outside
// the vault wall nearest the altar. Champion 2 idles on spawn.
#include <cambc.h>
#include <algorithm>
#include <iostream>
#include <optional>
#include <string>
#include <vector>

using cambc::bitboard;
using cambc::team;
using cambc::vec2;
namespace m = cambc::map;
namespace v = cambc::vision;

namespace {

int R() { return static_cast<int>(cambc::round_number()); }
std::string P(vec2 p) { return "(" + std::to_string(p.x) + "," + std::to_string(p.y) + ")"; }
void L(const std::string& s) {
    std::cout << "PROBE " << R() << " " << cambc::to_string(cambc::self().champion_name()) << " " << s << std::endl;
}
int cheb(vec2 a, vec2 b) { return std::max(std::abs(a.x - b.x), std::abs(a.y - b.y)); }
constexpr int unreachable = 65535;

bitboard static_blocked() {
    bitboard b = m::walls() | m::holes() | m::altars() | m::spawn_region(team::enemy);
    for (auto& g : m::camp_groups())
        for (auto& c : g) b.set(c.spawn_position());
    return b;
}

cambc::distance_field field(const bitboard& walls, const bitboard& roots) {
    cambc::distance_field f;
    bitboard visited;
    f.compute(walls, roots, visited);
    return f;
}

bool step(const bitboard& goals) {
    auto& me = cambc::self();
    if (!me.can_move() || goals.is_set(me.position())) return false;
    bitboard walls = m::walls() | m::holes() | m::altars() | m::spawn_region(team::enemy);
    for (auto& c : v::camps()) walls.set(c.position());
    for (auto& c : v::champions(team::ally)) if (c != me) walls.set(c.position());
    for (auto& c : v::champions(team::enemy)) walls.set(c.position());
    auto f = field(walls, goals);
    for (auto d : f.next_moves_from(me.position())) {
        try {
            if (me.move(d)) return true;
        } catch (const cambc::error&) {
        }
    }
    return false;
}

bitboard single(vec2 p) {
    bitboard b;
    b.set(p);
    return b;
}

std::string seen_enemies() {
    std::string s = "enemies=[";
    for (auto& e : v::champions(team::enemy)) s += P(e.position()) + ":" + std::to_string(e.gem_count()) + " ";
    s += "] tps=[";
    for (auto& t : v::teleports()) s += P(t.position()) + (t.is_ally() ? "a" : "e") + " ";
    return s + "]";
}

std::string chan() {
    try {
        return std::to_string(cambc::self().remaining_channel_time());
    } catch (const cambc::error&) {
        return "-";
    }
}

std::string state() {
    auto& me = cambc::self();
    return "pos=" + P(me.position()) + " hp=" + std::to_string(static_cast<int>(me.health())) + " gold=" + std::to_string(me.gold_count())
           + " gems=" + std::to_string(me.gem_count()) + " crystals=" + std::to_string(me.consumables()[cambc::consumable_type::tp_crystal].count())
           + " tp=" + std::to_string(me.is_teleporting()) + " trib=" + std::to_string(me.is_submitting_gems())
           + " rec=" + std::to_string(me.is_recalling()) + " chan=" + chan()
           + " score=" + std::to_string(cambc::global_submitted_gems(team::ally)) + " " + seen_enemies();
}

struct Plan {
    vec2 altar{-1, -1}, launch{-1, -1}, land{-1, -1};
    bitboard tribute;
    int cost = unreachable;
};

// Altars none of whose tribute tiles we can walk to; the launch tile minimising walk + inside steps.
Plan vault_plan() {
    auto& me = cambc::self();
    const bitboard blocked = static_blocked();
    const auto from_me = field(blocked, single(me.position()));
    Plan best;
    for (vec2 a : m::altars().positions()) {
        bitboard trib;
        for (int dy = -1; dy <= 1; ++dy)
            for (int dx = -1; dx <= 1; ++dx) {
                vec2 p{a.x + dx, a.y + dy};
                if (m::is_in_bounds(p) && !blocked.is_set(p)) trib.set(p);
            }
        if (trib.is_empty()) continue;
        bool walkable = false;
        for (vec2 p : trib.positions()) walkable |= from_me.get(p) != unreachable;
        if (walkable) continue;
        const auto inside = field(blocked, trib);
        for (int y = 0; y < m::height(); ++y)
            for (int x = 0; x < m::width(); ++x) {
                vec2 t{x, y};
                const int in = inside.get(t);
                if (in == unreachable || blocked.is_set(t)) continue;
                for (int dy = -3; dy <= 3; ++dy)
                    for (int dx = -3; dx <= 3; ++dx) {
                        vec2 l{x + dx, y + dy};
                        if (!m::is_in_bounds(l)) continue;
                        const int walk = from_me.get(l);
                        if (walk == unreachable) continue;
                        if (walk + in < best.cost) best = {a, l, t, trib, walk + in};
                    }
            }
    }
    return best;
}

int my_index() {
    int i = 0;
    for (auto& c : cambc::champions(team::ally)) {
        if (c == cambc::self()) return i;
        ++i;
    }
    return -1;
}

// Kill and capture the nearest group paying gold, or gems.
bool farm_cluster(bool gold) {
    auto& me = cambc::self();
    const bitboard blocked = static_blocked();
    const auto from_me = field(blocked, single(me.position()));
    std::optional<m::camp_group> best;
    int best_d = unreachable;
    for (auto& g : m::camp_groups()) {
        bool ok = gold ? g.gold_value() > 0 : g.gem_value() > 0;
        int d = unreachable;
        for (auto& c : g) {
            ok &= c.kind() != cambc::camp_type::monolith;
            for (int dy = -1; dy <= 1; ++dy)
                for (int dx = -1; dx <= 1; ++dx) {
                    vec2 p{c.spawn_position().x + dx, c.spawn_position().y + dy};
                    if (m::is_in_bounds(p)) d = std::min<int>(d, from_me.get(p));
                }
        }
        if (ok && d < best_d) best = g, best_d = d;
    }
    if (R() == 2) L("farm target " + std::to_string(best.has_value()) + " d=" + std::to_string(best_d));
    if (!best) return false;
    bitboard tiles, near;
    bool alive = false;
    for (auto& c : *best) {
        tiles.set(c.spawn_position());
        if (v::has_camp(c.spawn_position())) {
            alive = true;
            for (int dy = -1; dy <= 1; ++dy)
                for (int dx = -1; dx <= 1; ++dx) {
                    vec2 p{c.spawn_position().x + dx, c.spawn_position().y + dy};
                    if (m::is_in_bounds(p) && !static_blocked().is_set(p)) near.set(p);
                }
        }
    }
    if (alive) {
        for (auto& c : v::camps()) {
            if (!tiles.is_set(c.spawn_position()) || !me.can_attack() || cheb(c.position(), me.position()) > 1) continue;
            try {
                me.attack(c);
            } catch (const cambc::error&) {
            }
        }
        if (me.can_attack()) step(near);
        return true;
    }
    // Cleared: stand on a camp tile until paid.
    if (!tiles.is_set(me.position())) {
        bitboard walls = m::walls() | m::holes() | m::altars() | m::spawn_region(team::enemy);
        auto f = field(walls, tiles);
        for (auto d : f.next_moves_from(me.position())) {
            try {
                if (me.move(d)) break;
            } catch (const cambc::error&) {
            }
        }
    }
    return true;
}

int stage = 0;
Plan plan;
int tp_round = -1;

void runner() {
    auto& me = cambc::self();
    if (R() % 10 == 0) L("stage " + std::to_string(stage) + " " + state());
    if (stage == 0) {
        if (me.gem_count() > 0) {
            stage = 1;
            L("gems " + state());
        } else
            farm_cluster(false);
    }
    if (stage == 1) {
        if (me.gold_count() >= 10) {
            stage = 2;
            L("gold " + state());
        } else
            farm_cluster(true);
    }
    if (stage == 2) {
        if (!m::spawn_region(team::ally).is_set(me.position())) {
            step(m::spawn_region(team::ally));
            return;
        }
        try {
            me.buy(cambc::consumable_type::tp_crystal);
            L("bought " + state());
        } catch (const cambc::error& e) {
            L("buy failed " + cambc::to_string(e.code()));
        }
        plan = vault_plan();
        L("plan altar=" + P(plan.altar) + " launch=" + P(plan.launch) + " land=" + P(plan.land) + " cost=" + std::to_string(plan.cost));
        stage = 3;
        return;
    }
    if (stage == 3) {
        if (me.position() != plan.launch) {
            step(single(plan.launch));
            if (me.position() != plan.launch) return;
        }
        try {
            const bool ok = me.consumables()[cambc::consumable_type::tp_crystal].use(plan.land);
            L("teleport use=" + std::to_string(ok) + " " + state());
            if (ok) stage = 4, tp_round = R();
        } catch (const cambc::error& e) {
            L("teleport failed " + cambc::to_string(e.code()));
        }
        return;
    }
    if (stage == 4) {
        L("channel " + state() + " vis=" + std::to_string(me.visible_tiles().count()));
        if (me.is_teleporting()) return;
        L("arrived after " + std::to_string(R() - tp_round) + " rounds " + state());
        stage = 5;
    }
    if (stage == 5) {
        if (!plan.tribute.is_set(me.position())) step(plan.tribute);
        if (plan.tribute.is_set(me.position())) {
            try {
                me.submit_gems(plan.altar);
                L("submit " + state());
                stage = 6;
            } catch (const cambc::error& e) {
                L("submit failed " + cambc::to_string(e.code()));
            }
        }
        return;
    }
    if (stage == 6) {
        L("tributing " + state());
        if (me.is_submitting_gems()) return;
        stage = 7;
    }
    if (stage == 7) {
        try {
            me.recall();
            L("recall " + state());
            stage = 8;
        } catch (const cambc::error& e) {
            L("recall failed " + cambc::to_string(e.code()));
        }
        return;
    }
    if (stage == 8) {
        L("recalling " + state());
        if (!me.is_recalling()) stage = 9;
    }
}

void watcher() {
    auto& me = cambc::self();
    if (stage == 0) {
        // The reachable tile nearest a vault altar.
        const bitboard blocked = static_blocked();
        const auto from_me = field(blocked, single(me.position()));
        plan = vault_plan();
        int best = unreachable;
        for (int dy = -6; dy <= 6; ++dy)
            for (int dx = -6; dx <= 6; ++dx) {
                vec2 p{plan.altar.x + dx, plan.altar.y + dy};
                if (m::is_in_bounds(p) && from_me.get(p) != unreachable && cheb(p, plan.altar) < best)
                    best = cheb(p, plan.altar), plan.launch = p;
            }
        L("watch " + P(plan.launch) + " altar " + P(plan.altar));
        stage = 1;
    }
    if (me.position() != plan.launch) step(single(plan.launch));
    if (R() % 2 == 0 || !v::champions(team::enemy).empty()) L("watching " + state());
}

} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) {
                using cd = cambc::champion_draft;
                const cd prefs[] = {cd::varg, cd::ryth, cd::ren, cd::marcella, cd::vendetta};
                const auto chosen = cambc::draft::current_draft(team::ally);
                for (auto p : prefs)
                    if (std::find(chosen.begin(), chosen.end(), p) == chosen.end()) {
                        cambc::draft::pick(p);
                        break;
                    }
            } else if (cambc::self().is_alive()) {
                const int i = my_index();
                if (i == 0) runner();
                else if (i == 1) watcher();
            }
        } catch (const std::exception& e) {
            L(std::string("uncaught ") + e.what());
        }
        cambc::end_turn();
    }
}
