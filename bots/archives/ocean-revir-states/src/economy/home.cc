// Healing on our own spawn: a turn ended there heals to full (rules rounds.turn_end) and no enemy can
// enter it (map.spawn). Camp fire taken there costs one camp phase, not health carried; near it, a
// heal is a short walk rather than a recall. Its stands, its exits from camp fire and the heal trips
// that farm, siege and the shop price come from here. The spawn stands of each group's members are
// camps.cc's StandReach (home_free, home_gap).
#include "../bot_parts.h"

namespace aph {

namespace {

// The most camp damage one phase may deal `c` on its spawn: the turn end before it healed `c` to
// full, and what the phase leaves must stay above the safe recall line. For pricing, which looks past
// the enemies of the moment.
float home_room(const ChampionBelief& c) { return c.max_health * (1.0f - params::safe_recall_health_fraction); }

// home_room in the camps' own Strength, before c's emblems: what min_camp_damage and the siege weigh.
float home_survivable(const ChampionBelief& c) {
    return home_room(c) / std::max(0.01f, c.is_self ? camp_hit_factor() : c.camp_taken);
}

// home_room for us now: enemies attack into our spawn between the heal and the phase, so with one
// near (recall_line at the spawn's centre, read once a turn) the line kept above is the recall line.
float home_room(const World& world, Safety& safety) {
    static int round = -1;
    static float room = 0;
    if (round == world.round) return room;
    // recall_line keeps one tile's answer, most often ours: kept as it was.
    const bool known = safety.recall_line_known;
    const vec2 at = safety.recall_line_at;
    const float share = safety.recall_line_share;
    round = world.round, room = my_max_health() * (1.0f - recall_line(world, safety, world.map().ally_spawn_centre));
    safety.recall_line_known = known, safety.recall_line_at = at, safety.recall_line_share = share;
    return room;
}

// A heal trip from a stand `gap` steps from our spawn, `out` steps back out from where a recall lands,
// in rounds: the walk home and back, or the recall and the walk out, whichever is sooner. The recall's
// arrival turn is left out, as the heal prices before these always did.
float heal_trip(int channel, float gap, float out) { return std::min(2.0f * gap, static_cast<float>(channel) + out); }
float heal_trip(const World& world, float gap, float out) { return heal_trip(recall_turns(world), gap, out); }

// A camp member's reach covers a tile of our spawn, read once.
bool camps_reach_spawn(const World& world) {
    static int known = -1;
    if (known >= 0) return known == 1;
    known = 0;
    // As any_within(ally_spawn, m.pos, m.reach) for every member, without its four board calls a
    // member (~300k on maps of thousands): a spawn tile within reach lies in the spawn's box too.
    const auto& tiles = world.map().ally_spawn_tiles;
    if (tiles.empty()) return false;
    vec2 lo = tiles[0], hi = tiles[0];
    for (const auto t : tiles) lo = {std::min(lo.x, t.x), std::min(lo.y, t.y)}, hi = {std::max(hi.x, t.x), std::max(hi.y, t.y)};
    for (const auto& g : world.map().groups)
        for (const auto& m : g.members) {
            const vec2 p = m.pos;
            if (std::max({lo.x - p.x, p.x - hi.x, lo.y - p.y, p.y - hi.y}) > m.reach) continue;
            for (const auto t : tiles)
                if (dist(t, p) <= m.reach) return (known = 1);
        }
    return false;
}

// Our spawn tiles whose fire in the next phase, as Safety reads it (each awake member on its nearest
// champion), fits home_room, and that fire by spawn tile (the first 64): kept until Safety finds the
// members again. Champions are left on it.
struct HomeBoard {
    bitboard board{cambc::uninitialized}, fired{cambc::uninitialized}; // fired: our spawn tiles in camp_area()
    std::array<float, 64> fire{};
    bool any_fired = false;
    int round = -1;
    std::uint32_t found = 0;
};
const HomeBoard& home_fires(const World& world, Safety& safety) {
    static HomeBoard h;
    if (h.round == world.round && h.found == safety.members_found) return h;
    const auto& map = world.map();
    copy_into(map.ally_spawn, h.board);
    // Read only below the spawn's tile count.
    std::fill_n(h.fire.begin(), std::min(h.fire.size(), map.ally_spawn_tiles.size()), 0.0f);
    and_into(safety.camp_area(), map.ally_spawn, h.fired);
    h.any_fired = !board_empty(h.fired);
    if (h.any_fired) {
        const float room = home_room(world, safety);
        for (std::size_t k = 0; k < map.ally_spawn_tiles.size(); ++k) {
            const vec2 t = map.ally_spawn_tiles[k];
            if (!test(h.fired, t)) continue;
            const float fire = safety.camp_damage(t);
            if (k < h.fire.size()) h.fire[k] = fire;
            if (fire > room) h.board.set(t, false);
        }
    }
    // camp_area() may find the members, bumping the count.
    h.round = world.round, h.found = safety.members_found;
    return h;
}
const bitboard& home_board(const World& world, Safety& safety) { return home_fires(world, safety).board; }

// The camp damage the next phase deals us on p, after our emblems (phase_fire): the stirring groups'
// as Safety reads it, and group `wake`'s live strikers read asleep in full, as our hit wakes them all
// (rules camps.wake); sleeping_fire is the sleepers' part.
float sleeping_fire(const World& world, vec2 p, int wake) {
    if (wake < 0 || world.camps[wake].state != CampState::alive || world.camps[wake].fully_awake()) return 0;
    const auto& G = world.map().groups[wake];
    const auto& c = world.camps[wake];
    float sleeping = 0;
    for (std::size_t i = 0; i < G.members.size(); ++i)
        if (c.member_asleep(i) && c.health[i] > 0 && G.members[i].strength > 0 && dist(p, G.members[i].pos) <= G.members[i].reach)
            sleeping += G.members[i].strength;
    return sleeping * camp_hit_factor();
}
float phase_fire(const World& world, Safety& safety, vec2 p, int wake) { return safety.camp_damage(p) + sleeping_fire(world, p, wake); }

// `out` gets the free tiles of home_board among `tiles` where group `wake`'s sleepers, once woken,
// still leave the fire within home_room; true if any. Without a spawn tile among them (most groups:
// no board work), false.
bool home_stands(const World& world, Pathing& pathing, Safety& safety, const bitboard& tiles, int wake, bitboard& out) {
    const auto& map = world.map();
    and_into(tiles, map.ally_spawn, out);
    if (board_empty(out)) return false;
    const auto& h = home_fires(world, safety);
    out &= h.board;
    drop(out, pathing.blocked());
    if (wake < 0 || world.camps[wake].state != CampState::alive || world.camps[wake].fully_awake()) return !board_empty(out);
    // Board calls cost the same for any tiles; only the sleepers' fire is read tile by tile.
    const float room = home_room(world, safety);
    bool any = false;
    for (std::size_t k = 0; k < map.ally_spawn_tiles.size(); ++k) {
        const vec2 t = map.ally_spawn_tiles[k];
        if (!test(out, t)) continue;
        const float known = k < h.fire.size() ? h.fire[k] : safety.camp_damage(t);
        if (known + sleeping_fire(world, t, wake) > room) out.set(t, false);
        else any = true;
    }
    return any;
}

// home_stands without attack tiles: the spawn stands of g's live members (home_reach, in range and
// sight). False at once for most groups.
bool home_stands_near(const World& world, Pathing& pathing, Safety& safety, int g, int range, bitboard& out) {
    const auto& map = world.map();
    if (g < 0 || world.camps[g].state != CampState::alive) return false;
    const std::uint64_t tiles = home_reach(world, g, range);
    if (tiles == 0) return false;
    static bitboard near{cambc::uninitialized};
    clear_board(near);
    for (std::uint64_t b = tiles; b; b &= b - 1) near.set(map.ally_spawn_tiles[static_cast<std::size_t>(std::countr_zero(b))], true);
    return home_stands(world, pathing, safety, near, g, out);
}

// `out` gets the free tiles of home_board, our own included.
void home_tiles(const World& world, Pathing& pathing, Safety& safety, bitboard& out) {
    copy_into(home_board(world, safety), out);
    drop(out, pathing.blocked());
}

// Adds home_board to `goals`: its tiles in the camps' reach are an exit from their fire as good as a
// tile out of it, as the turn end there heals us.
void home_exits(const World& world, Safety& safety, bitboard& goals) {
    if (const auto& h = home_fires(world, safety); h.any_fired) goals |= h.board; // else every spawn tile is a goal already
}

// Steps from p to a free tile of home_board (home_tiles, the walk home's target) round the camps
// believed alive, if at most `longest`, else unreachable. The static walk to our spawn crosses camps:
// it, and within it the distance as the crow flies (a spawn is open ground), is only where the
// floods start.
int home_exit_steps(const World& world, Pathing& pathing, Safety& safety, vec2 p, int longest) {
    const auto& map = world.map();
    const int walk = map.from_ally_spawn().at(p);
    if (walk == unreachable || walk > longest) return unreachable;
    static bitboard free_home{cambc::uninitialized}, walls{cambc::uninitialized}, reached{cambc::uninitialized};
    home_tiles(world, pathing, safety, free_home);
    int least = unreachable;
    for (const auto t : map.ally_spawn_tiles)
        if (const int d = std::max(walk, dist(p, t)); d < least && test(free_home, t)) least = d;
    if (least > longest) return unreachable;
    or_into(map.blocked_for_us, pathing.live_camps(), walls);
    set_tile(walls, p, false);
    for (int d = least; d <= longest; ++d) {
        walls.reachable_tiles_into(p, static_cast<std::uint16_t>(d), reached);
        reached &= free_home;
        if (!board_empty(reached)) return d;
    }
    return unreachable;
}

// The walk home (home_exit_steps) no slower than a recall with `channel` turn ends left: the recall
// heals at the end of its arrival turn, a walk at the end of the turn it arrives, and needs no channel
// that damage cancels.
int walk_home_limit(int channel) { return channel + 1; }
bool walk_home_beats(int steps, int channel) { return steps <= walk_home_limit(channel); }
bool walk_beats_recall(const World& world, Pathing& pathing, Safety& safety, int channel) {
    return walk_home_beats(home_exit_steps(world, pathing, safety, my_position(), walk_home_limit(channel)), channel);
}

// A turn on our spawn heals at its end wherever on it we stand: a mend turn still hits the group we
// work (the siege's claim, else farm's choice) from here while every striker of it is awake, which
// wakes nothing new.
bool mend_hit(const World& world, const Memory& memory) {
    const int g = memory.siege ? memory.claim : memory.farm_group;
    if (!my_can_attack() || g < 0 || g >= static_cast<int>(world.camps.size()) || world.camps[g].state != CampState::alive
        || !world.camps[g].fully_awake())
        return false;
    // camp_attack_targets takes a Monolith only as the group under siege.
    if (world.map().groups[g].has_monolith) siege_group() = g;
    if (attack_camp(world, [&](int h) { return h == g; }) < 0) return false;
    reset_and_attack_camp(world, g);
    return true;
}

} // namespace

} // namespace aph
