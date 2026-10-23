// probe-pathcost: fuel cost of bounded host-side searches, and whether bitboard::shadow_cast
// reproduces engine vision (shape, bushes, symmetry).
// Run: cambc run tools/probes/probe-pathcost tools/probes/probe-pathcost
//        --map <map> --rounds 40 --fuel 50000000
// The first-picked champion of each team measures costs on its 2nd turn; every champion walks
// towards the map centre (later picks into the nearest bush) and compares shadow_cast with visible_tiles() each turn.
#include <cambc.h>
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

using cambc::bitboard;
using cambc::distance_field;
using cambc::vec2;

namespace {

std::uint64_t F() { return cambc::fuel_remaining(); }
std::string P(vec2 p) { return "(" + std::to_string(p.x) + "," + std::to_string(p.y) + ")"; }
std::string tag() {
    return "PROBE r" + std::to_string(cambc::round_number()) + ' ' + cambc::to_string(cambc::self().champion_name()) + ' ';
}

bitboard single(vec2 p) {
    bitboard b;
    b.set(p);
    return b;
}

bitboard static_walls() {
    return cambc::map::walls() | cambc::map::holes() | cambc::map::altars() | cambc::map::spawn_region(cambc::team::enemy);
}

bitboard live_walls(vec2 me) {
    auto w = static_walls() | cambc::vision::champion_tiles() | cambc::vision::camp_tiles() | cambc::vision::teleport_tiles();
    w.set(me, false);
    return w;
}

// Tiles at exactly distance d from me on the live board (empty if none).
bitboard ring(const bitboard& walls, vec2 me, int d) {
    distance_field f;
    bitboard inner, outer;
    f.compute(walls, single(me), outer, static_cast<std::uint16_t>(d));
    if (d > 0) f.compute(walls, single(me), inner, static_cast<std::uint16_t>(d - 1));
    return outer & ~inner;
}

void measure_costs() {
    auto& me = cambc::self();
    const vec2 here = me.position();
    std::cout << tag() << "map " << cambc::map::width() << 'x' << cambc::map::height() << " at " << P(here) << '\n';
    const auto walls = live_walls(here);
    const auto roots = single(here);
    distance_field f;
    bitboard visited;
    std::uint64_t a, b;

    // Bounded search from our tile.
    for (int r : {2, 4, 6, 8, 10, 12, 16, 24, 32, 65535}) {
        a = F();
        f.compute(walls, roots, visited, static_cast<std::uint16_t>(r));
        b = F();
        std::cout << tag() << "cost compute_from_me R=" << r << " fuel=" << (a - b) << " reached=" << visited.count() << '\n';
    }
    // The same through compute_to with no destination hit (empty destinations).
    for (int r : {6, 8, 12}) {
        bitboard none;
        a = F();
        f.compute_to(walls, roots, none, visited, static_cast<std::uint16_t>(r));
        b = F();
        std::cout << tag() << "cost compute_to_empty R=" << r << " fuel=" << (a - b) << " reached=" << visited.count() << '\n';
    }
    // compute_to a single tile d steps away, both directions.
    for (int d : {3, 6, 10, 20, 40}) {
        const auto targets = ring(walls, here, d).positions();
        if (targets.empty()) continue;
        const auto dest = single(targets.front());
        a = F();
        f.compute_to(walls, roots, dest, visited);
        b = F();
        const auto forward = a - b;
        a = F();
        f.compute_to(walls, dest, roots, visited);
        b = F();
        std::cout << tag() << "cost compute_to d=" << d << " forward=" << forward << " reverse=" << (a - b)
                  << " reached=" << visited.count() << '\n';
    }
    // Reading the boundary of an R=8 search: positions() plus one get per tile.
    {
        const auto edge = ring(walls, here, 8);
        f.compute(walls, roots, visited, 8);
        a = F();
        const auto tiles = edge.positions();
        int sum = 0;
        for (auto p : tiles) sum += f.get(p);
        b = F();
        std::cout << tag() << "cost read_ring8 tiles=" << tiles.size() << " fuel=" << (a - b) << " (sum " << sum << ")\n";
    }
    // next_moves_from on a computed field.
    {
        const auto targets = ring(walls, here, 8).positions();
        if (!targets.empty()) {
            f.compute_to(walls, single(targets.front()), roots, visited);
            a = F();
            const auto moves = f.next_moves_from(here);
            b = F();
            std::cout << tag() << "cost next_moves_from fuel=" << (a - b) << " moves=" << moves.size() << '\n';
        }
    }
    // reachable_tiles.
    for (int r : {1, 8}) {
        a = F();
        const auto reach = walls.reachable_tiles(here, static_cast<std::uint16_t>(r));
        b = F();
        std::cout << tag() << "cost reachable_tiles R=" << r << " fuel=" << (a - b) << " reached=" << reach.count() << '\n';
    }
    // Growing a set by one king step: a capped search vs shifts.
    {
        bitboard blob;
        blob.draw_chebyshev(here, 3);
        const auto sw = static_walls();
        a = F();
        f.compute(sw, blob & ~sw, visited, 1);
        b = F();
        std::cout << tag() << "cost dilate_by_compute fuel=" << (a - b) << " out=" << visited.count() << '\n';
        a = F();
        auto h = blob | blob.shift_right(1) | blob.shift_right(-1);
        auto grown = h | h.shift_up(1) | h.shift_up(-1);
        grown &= ~sw;
        b = F();
        std::cout << tag() << "cost dilate_by_shifts fuel=" << (a - b) << " out=" << grown.count() << '\n';
        a = F();
        const auto big = sw.reachable_tiles(here, 30);
        b = F();
        a = F();
        f.compute(sw, big & ~sw, visited, 1);
        b = F();
        std::cout << tag() << "cost dilate_large_by_compute in=" << big.count() << " fuel=" << (a - b) << '\n';
    }
    // shadow_cast and a few bitboard ops.
    {
        const auto opaque = cambc::map::walls() | cambc::map::bushes();
        a = F();
        const auto c = opaque.shadow_cast(here, 8);
        b = F();
        std::cout << tag() << "cost shadow_cast R=8 fuel=" << (a - b) << '\n';
        a = F();
        const auto c3 = opaque.shadow_cast(here, 3);
        b = F();
        std::cout << tag() << "cost shadow_cast R=3 fuel=" << (a - b) << '\n';
        bitboard sq;
        a = F();
        sq.draw_chebyshev(here, 3);
        sq &= ~opaque;
        b = F();
        std::cout << tag() << "cost draw_chebyshev_and_mask fuel=" << (a - b) << " (" << c.count() << ',' << c3.count() << ")\n";
        a = F();
        const auto v = cambc::vision::visible_tiles();
        b = F();
        std::cout << tag() << "cost visible_tiles fuel=" << (a - b) << '\n';
        a = F();
        const auto ct = cambc::vision::champion_tiles();
        const auto cp = cambc::vision::camp_tiles();
        b = F();
        std::cout << tag() << "cost champion_and_camp_tiles fuel=" << (a - b) << (v.is_empty() || ct.is_empty() || cp.is_empty() ? "" : " ") << '\n';
    }
}

// Compare shadow_cast from our tile with the engine's vision; once, check symmetry over the cast.
void compare_vision(bool check_symmetry) {
    const vec2 here = cambc::self().position();
    const auto walls = cambc::map::walls();
    const auto bushes = cambc::map::bushes();
    const bool in_bush = bushes.is_set(here);
    // In a bush, our own cluster is see-through: cast with only the other clusters opaque.
    // cluster8 joins diagonal neighbours too; cluster (used) is edge-connected only.
    bitboard cluster, cluster8;
    if (in_bush) {
        cluster8 = (~bushes).reachable_tiles(here, static_cast<std::uint16_t>(cambc::map::width() * cambc::map::height()));
        cluster.set(here);
        for (;;) {
            auto grown = (cluster | cluster.shift_right(1) | cluster.shift_right(-1) | cluster.shift_up(1) | cluster.shift_up(-1)) & bushes;
            if (grown == cluster) break;
            cluster = std::move(grown);
        }
        bitboard square8;
        square8.draw_chebyshev(here, 8);
        std::cout << tag() << "cluster4=" << cluster.count() << " cluster8=" << cluster8.count()
                  << " cluster4_in_square8=" << (cluster & square8).count() << '\n';
    }
    const auto opaque = walls | (bushes & ~cluster);
    if (in_bush) {
        try {
            (void)(walls | bushes).shadow_cast(here, 8);
            std::cout << tag() << "raw cast from bush ok\n";
        } catch (const cambc::error& e) {
            std::cout << tag() << "raw cast from bush error: " << e.what() << '\n';
        }
    }
    const auto cast = opaque.shadow_cast(here, 8);
    const auto seen = cambc::vision::visible_tiles();
    if (in_bush)
        std::cout << tag() << "cluster size=" << cluster.count() << " cluster_seen=" << (cluster & seen).count()
                  << " cluster_in_cast=" << (cluster & cast).count() << " cluster_beyond_8_seen="
                  << (cluster & seen & ~cast).count() << '\n';
    std::cout << tag() << "vision at " << P(here) << (in_bush ? " IN_BUSH" : "") << " cast=" << cast.count()
              << " seen=" << seen.count() << " cast_only=" << (cast & ~seen).count() << " seen_only=" << (seen & ~cast).count()
              << " cast_walls=" << (cast & walls).count() << " seen_walls=" << (seen & walls).count()
              << " cast_bushes=" << (cast & bushes).count() << " seen_bushes=" << (seen & bushes).count() << '\n';
    // Print a few disagreeing tiles.
    int shown = 0;
    for (auto p : (cast ^ seen).positions()) {
        if (shown++ == 6) break;
        std::cout << tag() << "  diff " << P(p) << (cast.is_set(p) ? " cast_only" : " seen_only")
                  << (walls.is_set(p) ? " wall" : "") << (bushes.is_set(p) ? " bush" : "") << '\n';
    }
    if (!check_symmetry) return;
    int asym = 0, checked = 0;
    for (auto p : cast.positions()) {
        if (opaque.is_set(p) || cluster.is_set(p)) continue;
        ++checked;
        if (!opaque.shadow_cast(p, 8).is_set(here)) {
            if (asym < 6) std::cout << tag() << "  asym " << P(here) << " sees " << P(p) << " but not back\n";
            ++asym;
        }
    }
    std::cout << tag() << "symmetry checked=" << checked << " asymmetric=" << asym << '\n';
}

// Walk one step towards the map centre, or for later picks into the nearest bush.
void walk(bool to_bush) {
    auto& me = cambc::self();
    if (!me.can_move()) return;
    const vec2 here = me.position();
    bitboard goal;
    if (to_bush) goal = cambc::map::bushes();
    if (goal.is_empty()) goal.draw_chebyshev({cambc::map::width() / 2, cambc::map::height() / 2}, 2);
    const auto walls = live_walls(here);
    goal &= ~walls;
    if (goal.is_empty() || goal.is_set(here)) return;
    distance_field f;
    bitboard visited;
    f.compute_to(walls, goal, single(here), visited);
    for (auto d : f.next_moves_from(here)) {
        try {
            if (me.move_absolute(here + d)) return;
        } catch (const cambc::error&) {
        }
    }
}

int turn = 0;

void play() {
    ++turn;
    const auto picks = cambc::draft::current_draft(cambc::team::ally);
    const bool first = !picks.empty() && cambc::to_string(picks[0]) == cambc::to_string(cambc::self().champion_name());
    if (first && turn == 2) measure_costs();
    if (turn >= 2) compare_vision(turn == 2 || turn == 20 || cambc::map::bushes().is_set(cambc::self().position()));
    walk(!first);
}

void draft() {
    const auto ours = cambc::draft::current_draft(cambc::team::ally);
    for (int i = 0; i < 11; ++i) {
        const auto pick = static_cast<cambc::champion_draft>(i);
        if (pick == cambc::champion_draft::cassi_and_issac) continue;
        if (std::find(ours.begin(), ours.end(), pick) != ours.end()) continue;
        try {
            cambc::draft::pick(pick);
            return;
        } catch (const cambc::error&) {
        }
    }
}

} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) draft();
            else play();
        } catch (const std::exception& e) {
            std::cout << "PROBE error " << e.what() << '\n';
        }
        cambc::end_turn();
    }
}
