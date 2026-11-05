#include "enemy_reach.h"
#include <algorithm>
#include <array>
#include <optional>
#include "world.h"

namespace aph::enemy_reach {

int act_range(const ChampionFacts& f) {
    int a = f.basic_reach();
    for (const auto& ab : f.abilities) {
        if (ab.kind == AbilityKind::damage || ab.kind == AbilityKind::stun) a = std::max(a, ab.reach());
        else if (ab.lands()) a = std::max(a, ab.radius);
    }
    return a;
}

Profile profile(const ChampionFacts& f) { return {act_range(f), f.has_dash()}; }

Profile ally_profile(const ChampionFacts& f) { return {act_range(f), f.has_dash(), true, f.dash_kind()}; }

Profile widest(const World& world) {
    Profile w;
    for (const auto& e : world.enemies)
        if (e.alive) {
            const auto p = profile(e.facts());
            w.act = std::max(w.act, p.act), w.dasher |= p.dasher;
        }
    return w;
}

namespace {

// steps[s]: the tiles within s steps of `from` (S <= s), for s below max_steps.
constexpr int max_steps = 16;
struct Walk {
    vec2 from{-1, -1};
    int kind = 0; // walls_kind()
    std::uint32_t made = 0;    // bit s: steps[s] is this walk's
    std::uint32_t counted = 0; // bit s: count[s] is steps[s]'s
    std::uint32_t used = 0;
    std::array<std::uint16_t, max_steps> count{};
    std::array<std::optional<bitboard>, max_steps> steps;
};
// Kept across turns, as the terrain is static: an enemy standing still costs nothing more. More
// slots than enemies, so that a teleport's landing or a live tile seldom evicts a standing one's.
std::array<Walk, 32> walks;
std::uint32_t uses = 0;
// Slot + 1 of the walk last found for a key hashing here: scanning the slots cost ~470 fuel a
// call. A slot matches only once made, and two never match the same key, so checking one first
// finds what the scan would.
std::array<std::uint8_t, 64> last_slot{};

// 0, 1: the enemy's walk and dash; 2 + dash kind: ours.
int walls_kind(const Profile& who) { return who.ours ? 2 + who.dash_kind : who.dasher ? 1 : 0; }

const bitboard& walls_of(const StaticMap& map, int kind) {
    return kind == 0 ? map.blocked_for_them : kind == 1 ? map.their_dash_walls() : map.our_walls(kind - 2);
}

Walk& walk_from(vec2 from, int kind) {
    auto& hint = last_slot[static_cast<std::size_t>((from.x * 7 + from.y * 13 + kind * 29) & 63)];
    if (hint) {
        auto& w = walks[hint - 1u];
        if (w.from == from && w.kind == kind && w.made) {
            w.used = ++uses;
            return w;
        }
    }
    Walk* oldest = &walks[0];
    for (auto& w : walks) {
        if (w.from == from && w.kind == kind && w.made) {
            w.used = ++uses;
            hint = static_cast<std::uint8_t>(&w - walks.data() + 1);
            return w;
        }
        if (w.used < oldest->used) oldest = &w;
    }
    oldest->from = from, oldest->kind = kind, oldest->made = oldest->counted = 0, oldest->used = ++uses;
    hint = static_cast<std::uint8_t>(oldest - walks.data() + 1);
    return *oldest;
}

const bitboard& steps(const StaticMap& map, Walk& w, int s) {
    auto& b = w.steps[static_cast<std::size_t>(s)];
    if (!(w.made >> s & 1)) {
        if (!b) b.emplace(cambc::uninitialized);
        walls_of(map, w.kind).reachable_tiles_into(w.from, static_cast<std::uint16_t>(s), *b);
        w.made |= 1u << s;
    }
    return *b;
}

int count(const StaticMap& map, Walk& w, int s) {
    if (!(w.counted >> s & 1)) w.count[static_cast<std::size_t>(s)] = static_cast<std::uint16_t>(board_count(steps(map, w, s))), w.counted |= 1u << s;
    return w.count[static_cast<std::size_t>(s)];
}

// Some tile within s steps of `from` lies within act of p, dist(from, p) <= s + act. The tile s
// steps straight towards p is within act of it: on open ground always within s steps, so one
// tile test settles it there; only terrain needs the square.
bool reaches(const StaticMap& map, Walk& w, int s, vec2 p, int act) {
    const auto& b = steps(map, w, s);
    const vec2 q{w.from.x + std::clamp(p.x - w.from.x, -s, s), w.from.y + std::clamp(p.y - w.from.y, -s, s)};
    return test(b, q) || any_within(b, p, act);
}

} // namespace

int distance(const World& world, const Profile& who, vec2 from, vec2 p, int limit) {
    const int d = dist(from, p);
    if (d <= who.act || d > limit) return d;
    auto& w = walk_from(from, walls_kind(who));
    const auto& map = world.map();
    for (int x = d; x <= limit; ++x) {
        const int s = x - who.act;
        if (s >= max_steps) return x; // past what is kept: no more than this
        if (reaches(map, w, s, p, who.act)) return x;
        // A walk that grew no further never will.
        if (w.made >> (s - 1) & 1 && count(map, w, s) == count(map, w, s - 1)) return far;
    }
    return limit + 1;
}

int steps_within(const World& world, const Profile& who, vec2 from, vec2 p) {
    const int d = dist(from, p);
    if (d <= who.act) return 0;
    // distance() returns act + max_steps, a lower bound, past what the walk keeps.
    const int x = distance(world, who, from, p, who.act + max_steps);
    if (x >= far) return unreachable;
    if (x - who.act < max_steps) return x - who.act;
    struct Kept {
        vec2 p{-1, -1};
        int act = -1, kind = -1;
        std::uint32_t used = 0;
        std::optional<Field> field;
    };
    static std::array<Kept, 4> kept;
    static std::uint32_t uses = 0;
    const int kind = walls_kind(who);
    Kept* slot = &kept[0];
    for (auto& k : kept) {
        if (k.p == p && k.act == who.act && k.kind == kind) {
            k.used = ++uses;
            return k.field->at(from);
        }
        if (k.used < slot->used) slot = &k;
    }
    bitboard goals;
    draw_square(goals, p, static_cast<float>(who.act));
    *slot = {p, who.act, kind, ++uses, make_field(walls_of(world.map(), kind), goals)};
    return slot->field->at(from);
}

int distance(const World& world, const ChampionBelief& e, vec2 from, vec2 p, int limit) {
    return distance(world, profile(e.facts()), from, p, limit);
}

bool within(const World& world, const Profile& who, vec2 from, vec2 p, int x) {
    const int d = dist(from, p);
    if (d > x) return false;
    if (d <= who.act) return true;
    const int s = x - who.act;
    if (s >= max_steps) return true;
    return reaches(world.map(), walk_from(from, walls_kind(who)), s, p, who.act);
}

bool within(const World& world, const ChampionBelief& e, vec2 from, vec2 p, int x) { return within(world, profile(e.facts()), from, p, x); }

int steps_to(const World& world, const Profile& who, vec2 from, const bitboard& targets, int cap) {
    static bitboard near{cambc::uninitialized}, meet{cambc::uninitialized};
    square_dilate(targets, who.act, near);
    if (test(near, from)) return 0;
    auto& w = walk_from(from, walls_kind(who));
    const auto& map = world.map();
    for (int s = 1; s < cap && s < max_steps; ++s) {
        and_into(steps(map, w, s), near, meet);
        if (!board_empty(meet)) return s;
        // A walk that grew no further never will.
        if (count(map, w, s) == count(map, w, s - 1)) return cap;
    }
    return cap;
}

vec2 origin(const ChampionBelief& e) { return e.teleport_pending() && in_bounds(e.tp_dest) ? e.tp_dest : e.pos; }

bool warm_up(const World& world, std::uint64_t fuel_floor) {
    const auto& map = world.map();
    if (map.their_dash_walls_ready()) return true;
    bool dasher = false;
    for (const auto& e : world.enemies) dasher |= e.facts().has_dash();
    if (!dasher) return true;
    // About 45 whole-board operations.
    if (!fuel_ok(fuel_floor + 45 * (13 + search_chunks()) + 2000)) return false;
    (void)map.their_dash_walls();
    return true;
}

} // namespace aph::enemy_reach
