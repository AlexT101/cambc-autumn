// Banking: tribute timing and safety, which altars stay reachable, hops to them, locks, and the
// channels a turn continues.
#include "../bot_parts.h"

namespace aph {

namespace {

// One state read: each is a host call.
bool channelling() {
    using cambc::champion_state;
    const auto state = my_state();
    return state.contains(champion_state::recalling) || state.contains(champion_state::submitting_gems)
           || state.contains(champion_state::teleporting);
}

// By altar, the round we learned our team locks it (placed, or refused as already locked): update_altars
// sees only locks in sight. Its belief is trusted again once the altar is seen after that round.
std::vector<int> own_lock_round;

[[gnu::flatten]] void place_lock(const World& world) {
    auto& me = cambc::self();
    if (stunned_turn || !world.me().alive) return;
    const auto& lock = me.consumables()[cambc::consumable_type::altar_lock];
    if (lock.count() == 0 || channelling()) return;
    const auto& map = world.map();
    const vec2 here = my_position();
    // Altars with an enemy tributing first.
    for (int pass = 0; pass < 2; ++pass)
        for (int a = 0; a < static_cast<int>(map.altars.size()); ++a) {
            const vec2 p = map.altars[a].pos;
            if (dist(here, p) > altar_lock_range || world.altars[a].ally_lock) continue;
            if (a < static_cast<int>(own_lock_round.size()) && own_lock_round[a] >= 0
                && own_lock_round[a] >= world.altars[a].seen_round)
                continue;
            // Placing one also cancels an enemy's tribute there: its bag stays out of the score.
            bool enemy_tribute = false, winning = false;
            for (const auto& e : world.enemies)
                if (e.alive && e.visible && e.channel == Channel::tribute && dist(e.pos, p) <= cambc::constants::submit_gems_range)
                    enemy_tribute = true, winning |= enemy_tribute_wins(world, e);
            if (enemy_tribute != (pass == 0)) continue;
            // With no tribute to cancel, only altars on our side are worth denying.
            if (!enemy_tribute && dist(p, map.ally_spawn_centre) > dist(p, map.enemy_spawn_centre) + 2) continue;
            // Placing one cancels every tribute at the altar, ours included: worth it only against a win.
            bool tributing = false, ours_wins = false;
            for (const auto& ally : world.allies)
                if (!ally.is_self && ally.alive && ally.channel == Channel::tribute && dist(ally.pos, p) <= cambc::constants::submit_gems_range)
                    tributing = true,
                    ours_wins |= world.score.ally + ally.gems >= static_cast<int>(cambc::constants::winning_gems);
            if (tributing && (!winning || ours_wins)) continue;
            const auto note_own_lock = [&] {
                if (own_lock_round.size() < map.altars.size()) own_lock_round.resize(map.altars.size(), -1);
                own_lock_round[a] = world.round;
            };
            throw_if_stale();
            try {
                if (lock.use(p)) return note_own_lock();
            } catch (const cambc::error& e) {
                if (e.code() == cambc::error_code::invalid_action_altar_lock_already_locked) note_own_lock();
            }
        }
}

bool break_lock(const World& world, int altar) {
    auto& me = cambc::self();
    const vec2 p = world.map().altars[altar].pos;
    if (!my_can_attack() || dist(my_position(), p) > world.me().facts().attack_range()) return false;
    for (const auto& lock : cambc::vision::altar_locks())
        if (lock.is_enemy() && lock.position() == p) {
            throw_if_stale();
            try {
                me.attack(lock);
                return true;
            } catch (const cambc::error&) {
                return false;
            }
        }
    return false;
}

// A believed lock can be gone: break_lock's last hit, or an old sighting of an altar out of view at turn start.
bool enemy_lock_live(vec2 p) {
    namespace raw = cambc::detail;
    std::uint32_t count{};
    ok(raw::sdk_altar_locks(nullptr, 0, &count));
    if (count == 0) return false;
    static std::vector<raw::altar_lock_info> locks; // vision::altar_locks() allocates two vectors a call
    if (locks.size() < count) locks.resize(count);
    ok(raw::sdk_altar_locks(locks.data(), count, &count));
    const auto own = static_cast<std::uint32_t>(raw::cached_my_team);
    for (std::uint32_t i = 0; i < count && i < locks.size(); ++i)
        if (locks[i].team != own && locks[i].x == p.x && locks[i].y == p.y) return true;
    return false;
}

// A tribute channel cannot act, and a kill takes the whole bag: start or keep one only if the
// visible enemies could not kill us within the next few turns, nor damage at the rate of the last
// round (attackers in bushes stay unseen). Judged again every turn of the channel, which is
// cancelled once a threat comes that close: a long bag's whole channel would wait on any enemy in sight.
bool tribute_safe(Safety& safety, const Memory& memory, int turns) {
    const int window = std::min(turns, params::tribute_window);
    const float health = my_health();
    if (memory.damage * static_cast<float>(window) >= health) return false;
    const int kill = safety.turns_to_kill_idle(my_position(), window + 1);
    return kill == 0 || kill > window;
}

// The rules' max(1, ceil(gems / 10)) (cambc::constants::submit_gem_*), as a constant so the division folds:
// the engine's settings are read at run time, and this is called in the farm loop.
constexpr int gems_per_tribute_turn = 10;

// `fast`: a Tribute emblem's owner, whose channel loses floor(0.33 b) of its b turn ends.
int tribute_turns(int gems, bool fast) {
    const int b = std::max(1, (gems + gems_per_tribute_turn - 1) / gems_per_tribute_turn);
    return fast ? b - b * tribute_emblem_cut / 100 : b;
}
int tribute_turns(const World& world, int gems) { return tribute_turns(gems, world.me().fast_tribute); }

int recall_turns(const World& world) {
    return world.me().recall_turns();
}

// The tile a recall lands on: the first in the engine's order with no ally seen on it.
vec2 recall_landing(const World& world) {
    const auto& tiles = world.map().landing_tiles;
    if (tiles.empty()) return world.map().ally_spawn_centre;
    for (const vec2 t : tiles) {
        bool taken = false;
        for (const auto& a : world.allies) taken |= !a.is_self && a.alive && a.visible && a.pos == t;
        if (!taken) return t;
    }
    return tiles[0];
}

int rounds_left(const World& world) { return static_cast<int>(cambc::constants::max_rounds) - world.round; }

// Gems still to capture, beyond the bag and the tributes allies in sight are channelling, before
// our tributes reach the win.
int gems_short(const World& world) {
    int pending = 0;
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && a.channel == Channel::tribute) pending += a.gems;
    return static_cast<int>(cambc::constants::winning_gems) - world.score.ally - static_cast<int>(my_gems())
           - pending;
}

const ChampionBelief* partner(const World& world) { return linked_partner(world, world.me()); }

// What a death would hand over: both bags for Cassi and Issac (an unseen partner's as posted).
int bag_at_stake(const World& world) {
    const auto* p = partner(world);
    const int other = !p || !p->alive ? 0 : p->visible ? p->gems : std::max(p->gems, comms::bag_of(world, p->index));
    return static_cast<int>(my_gems()) + other;
}

AltarWalk& altar_walk() {
    static AltarWalk w;
    return w;
}

void flood_altar_walk(const World& world, Pathing& pathing, AltarWalk& w) {
    or_into(pathing.static_walls(), w.access.live, w.walls);
    w.walls.reachable_tiles_into(world.map().ally_spawn_tiles[0], unreachable, w.ours);
    w.walked = true;
    altar_walk_pending = false;
}

[[gnu::noinline]] const AltarAccess& rebuild_altar_access(const World& world, Pathing& pathing, const bitboard& live) {
    auto& w = altar_walk();
    auto& a = w.access;
    auto& ours = w.ours;
    auto& walls = w.walls;
    a.live_flips = pathing.live_flips();
    const auto& map = world.map();
    static bitboard area{cambc::uninitialized}, seen{cambc::uninitialized}, gone{cambc::uninitialized}, grown{cambc::uninitialized};
    bool updated = false; // `ours` brought up to date without a flood from spawn
    if (a.version > 0 && !map.ally_spawn_tiles.empty()) {
        copy_into(live, area);
        drop(area, a.live);
        copy_into(a.live, gone);
        drop(gone, live);
        const bool back = !board_empty(area), died = !board_empty(gone);
        if (!back && !died) return a;
        if (w.walked && !back) {
            // Deaths add to the walk what each dead camp beside it reaches without crossing it.
            or_into(pathing.static_walls(), live, walls);
            walls |= ours;
            square_dilate(ours, 1, grown);
            gone &= grown;
            while (!board_empty(gone)) {
                const vec2 t = first_tile(gone);
                walls.reachable_tiles_into(t, unreachable, seen);
                ours |= seen;
                drop(gone, seen);
                set_tile(gone, t, false);
            }
            updated = true;
        } else if (w.walked && !died) {
            // Respawns whose walkable ring is connected cut no walk: it goes round them.
            square_dilate(area, 1, grown);
            grown &= ours;
            drop(grown, area);
            updated = board_empty(grown);
            if (!updated) {
                not_into(grown, walls);
                walls.reachable_tiles_into(first_tile(grown), static_cast<std::uint16_t>(board_count(grown)), seen);
                updated = seen == grown;
            }
            if (updated) drop(ours, area);
        }
    }
    ++a.version;
    copy_into(live, a.live);
    a.blocks.clear();
    clear_board(a.open);
    clear_board(a.opened);
    a.any_open = false;
    if (map.ally_spawn_tiles.empty()) return a;
    static bitboard tributes{cambc::uninitialized};
    // Every tribute tile is on our walk and none on a camp: the first build finds them all open
    // without the walk.
    const bool on_walk = a.version == 1 && map.tributes_walked();
    if (!updated && !on_walk) flood_altar_walk(world, pathing, w);
    altar_walk_pending = !w.walked;
    if (a.version == 1) {
        clear_board(tributes);
        for (const auto& t : map.altars) tributes |= t.tribute_tiles();
    }
    if (a.version == 1 && !on_walk) { // never walked: `ours` is the flood above
        // Drop for good the tribute tiles off the static walk that no hop reaches either. A tile on
        // `ours` is on the static walk (live camps only add walls), so that walk is read only if
        // some tile is off ours.
        copy_into(tributes, area);
        drop(area, ours);
        if (!board_empty(area)) drop(area, pathing.foot());
        if (!board_empty(area)) {
            for (const auto& h : map.hops())
                if (h.altar >= 0) drop(area, map.altars[h.altar].tribute_tiles());
            drop(tributes, area);
        }
    }
    copy_into(tributes, a.opened);
    // open = tributes off live camps, but for those the static walk reaches and this one does not
    copy_into(a.opened, a.open);
    drop(a.open, live);
    // The static walk (pathing.foot()) is a flood as costly as ours (~28k on 100x100, uncached
    // until the warm-up): read it only when a tribute tile is off our walk or none is open.
    bool off_walk = false;
    if (!on_walk) {
        copy_into(a.open, area);
        drop(area, ours);
        off_walk = !board_empty(area);
    }
    if (off_walk) {
        copy_into(pathing.foot(), area);
        drop(area, ours);
        drop(a.open, area);
        // A crystal's altar is open only from a hop source this walk reaches.
        for (const auto& h : map.hops()) {
            if (h.altar < 0) continue;
            and_into(h.sources, ours, seen);
            if (board_empty(seen)) drop(a.open, map.altars[h.altar].tribute_tiles());
        }
    }
    a.any_open = !a.open.is_empty();
    if (a.any_open) {
        copy_into(a.open, a.opened);
        return a;
    }
    if (!w.walked) flood_altar_walk(world, pathing, w);
    if (!off_walk) {
        copy_into(pathing.foot(), area);
        drop(area, ours);
    }
    a.opened &= area;
    // The live camps beside our walk.
    square_dilate(ours, 1, grown);
    grown &= live;
    or_into(pathing.static_walls(), ours, walls);
    clear_board(seen);
    for (const vec2 t : a.opened.positions()) {
        if (test(seen, t)) continue;
        walls.reachable_tiles_into(t, unreachable, area);
        seen |= area;
        area &= grown;
        for (const vec2 p : area.positions())
            if (const int g = map.group_at(p); g >= 0 && std::find(a.blocks.begin(), a.blocks.end(), g) == a.blocks.end())
                a.blocks.push_back(g);
    }
    return a;
}

const AltarAccess& altar_access(const World& world, Pathing& pathing) {
    const auto& a = altar_walk().access;
    const auto& live = pathing.live_camps();
    if (a.version > 0 && a.live_flips == pathing.live_flips()) return a;
    return rebuild_altar_access(world, pathing, live);
}

// The camp damage a phase on the best open tribute tile, from the members believed awake: an asleep
// one wakes only when damaged or stunned. Huge with no open tile.
float access_fire(const World& world, const AltarAccess& a) {
    static int round = -1, version = 0;
    static float fire = 0;
    if (round == world.round && version == a.version) return fire;
    round = world.round;
    version = a.version;
    fire = std::numeric_limits<float>::max();
    const auto& map = world.map();
    const auto& groups = map.groups;
    // By group, once read: 1 if a member reaches a tile beside an altar.
    static std::vector<signed char> near;
    if (near.size() != groups.size()) near.assign(groups.size(), -1);
    static std::vector<int> stirring;
    stirring.clear();
    world.each_stirring([&](int g) {
        if (near[g] < 0) {
            near[g] = 0;
            for (const auto& m : groups[g].members)
                for (const auto& altar : map.altars)
                    if (dist(m.pos, altar.pos) <= m.reach + cambc::constants::submit_gems_range) near[g] = 1;
        }
        if (near[g]) stirring.push_back(g);
    });
    // With nothing stirring every open tile is free of fire.
    if (stirring.empty()) return fire = a.any_open ? 0.0f : fire;
    // Room for every tribute tile, which the open ones are among.
    static std::vector<vec2> open;
    if (open.empty()) {
        bitboard tributes;
        for (const auto& t : map.altars) tributes |= t.tribute_tiles();
        open.resize(std::max<std::size_t>(1, board_count(tributes)));
    }
    const auto n = std::min<std::size_t>(positions_into(a.open, open.data(), static_cast<std::uint32_t>(open.size())), open.size());
    for (const vec2 t : std::span{open.data(), n}) {
        float f = 0;
        for (const int g : stirring) {
            if (!test(groups[g].threat(), t)) continue;
            const auto& c = world.camps[g];
            for (std::size_t i = 0; i < groups[g].members.size(); ++i) {
                const auto& m = groups[g].members[i];
                if (c.health[i] > 0 && !c.maybe_asleep(i) && in_square(t, m.pos, m.reach)) f += m.strength;
            }
        }
        if ((fire = std::min(fire, f)) <= 0) break;
    }
    return fire;
}

// A tribute of `bag` on an open tribute tile ends before the camps' fire there takes `health`.
bool altar_usable(const World& world, Pathing& pathing, int bag, float health) {
    const auto& a = altar_access(world, pathing);
    return a.any_open && camp_hit_factor() * access_fire(world, a) * static_cast<float>(tribute_turns(world, bag)) < health;
}

// The bag a tribute could score: one no altar is usable for is held back, and we farm and shop as
// if empty-handed.
int bankable_bag(const World& world, Pathing& pathing) {
    const int bag = static_cast<int>(my_gems());
    if (bag == 0 || !altar_usable(world, pathing, bag, my_health())) return 0;
    // Only a crystal reaches an altar and we can neither use nor buy one: farm the gold first. A
    // recall out of a pocket to a spawn with a walk to one banks it. Altars' hops come first.
    if (!world.map().hops().empty() && world.map().hops()[0].altar >= 0 && pathing.to_any_altar().at(my_position()) == unreachable && !carries_crystal()
        && !can_buy_crystal() && pathing.to_any_altar().at(world.map().ally_spawn_centre) == unreachable)
        return 0;
    return bag;
}

// No altar is usable for the team's largest bag (an unseen ally's as posted).
bool altars_sealed(const World& world, Pathing& pathing) {
    int bag = static_cast<int>(my_gems());
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive) bag = std::max(bag, a.visible ? a.gems : comms::bag_of(world, a.index));
    return !altar_usable(world, pathing, bag, my_max_health());
}

// While the altars are sealed, a live group whose clear opens a walk to one, or with a member
// believed awake in reach of one, seals them.
bool seals(const World& world, const AltarAccess& access, int g) {
    const auto& c = world.camps[g];
    if (c.state != CampState::alive) return false;
    if (std::find(access.blocks.begin(), access.blocks.end(), g) != access.blocks.end()) return true;
    const auto& members = world.map().groups[g].members;
    for (std::size_t i = 0; i < members.size(); ++i)
        if (c.health[i] > 0 && members[i].strength > 0 && !c.maybe_asleep(i)
            && any_within(access.opened, members[i].pos, members[i].reach))
            return true;
    return false;
}

// Tributing the bag wins: more gems are worth nothing, only the tribute is.
bool winning_bag(const World& world) { return gems_short(world) <= 0; }

// Rounds until the team, at its recent tribute rate, has the rest of the win beyond our score and
// the team's bags (as seen, else as posted through comms): our bag banked later than that only delays the win.
int race_left(const World& world) {
    int short_by = gems_short(world);
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && !(a.visible && a.channel == Channel::tribute))
            short_by -= a.visible ? a.gems : comms::bag_of(world, a.index);
    if (short_by <= 0) return 0;
    const float rate = world.ally_rate();
    return rate > 0 ? static_cast<int>(static_cast<float>(short_by) / rate) : rounds_left(world);
}

// The rounds left in the game for a bag: to the round limit, and for ours to the race's end.
int bag_rounds_left(const World& world) {
    return my_gems() > 0 ? std::min(rounds_left(world), race_left(world)) : rounds_left(world);
}

// The bag needs the rest of the game, or of the race (the rest of the win comes without it), to
// reach an altar and score: it goes straight there.
bool closing(const World& world, Pathing& pathing) {
    const auto& field = pathing.to_any_altar();
    int walk = field.at(my_position());
    // No walk out of here: recall home and walk from there.
    if (walk == unreachable) {
        const int out = field.at(recall_landing(world));
        walk = out == unreachable ? 0 : recall_turns(world) + out;
    }
    return bag_rounds_left(world) <= walk + tribute_turns(world, my_gems()) + endgame_margin;
}

bool retaining_gems(const World& world, Pathing& pathing) {
    return world.me().facts().passive == Passive::gem_focus && my_gems() > 0
           && !winning_bag(world) && !closing(world, pathing);
}

// Our bag is headed for an altar: one a tribute could score that Prism is not keeping for Focus.
bool banks_bag(const World& world, Pathing& pathing) { return bankable_bag(world, pathing) > 0 && !retaining_gems(world, pathing); }

// A tribute started or kept now is the bag's last chance to score, or wins the game while fleeing
// gives the enemy time to win first: take it at any risk. Not a long winning channel: standing
// that long beside an enemy hands it the bag, so it waits for a safe window like any other.
bool any_risk(const World& world, int channel_turns) {
    return (winning_bag(world) && channel_turns <= params::tribute_window)
           || rounds_left(world) <= channel_turns + endgame_slack;
}

// A channel still running at the round limit scores nothing.
bool tribute_ok(const World& world, Safety& safety, const Memory& memory, int turns) {
    return turns <= rounds_left(world) && (any_risk(world, turns) || tribute_safe(safety, memory, turns));
}

// At an unlocked altar in reach. The caller judged the turn's start tile safe; anywhere else, at an
// altar carry_bag gave up waiting at, or at one believed locked (the caller skipped it), is judged again.
bool submit_here(const World& world, Safety& safety, Memory& memory) {
    if (stunned_turn) return false; // the engine refuses it, and the thrown error costs ~3.9k fuel
    auto& me = cambc::self();
    const vec2 here = my_position();
    const auto& altars = world.map().altars;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
        if (dist(here, altars[a].pos) > cambc::constants::submit_gems_range) continue;
        if (world.altars[a].enemy_lock && enemy_lock_live(altars[a].pos)) continue;
        const bool avoided = a == memory.avoid_altar && world.round < memory.avoid_until;
        if ((avoided || world.altars[a].enemy_lock || here != world.me().pos)
            && !tribute_ok(world, safety, memory, tribute_turns(world, my_gems())))
            return false;
        place_lock(world); // first: it cancels every tribute at its altar
        place_ward(world, memory); // first: no ward goes down while channelling
        throw_if_stale();
        try {
            me.submit_gems(altars[a].pos);
            const int bag = static_cast<int>(my_gems());
            income.tribute_cut += static_cast<float>(tribute_turns(bag, false) - tribute_turns(bag, true));
            return true;
        } catch (const cambc::error&) {
        }
    }
    return false;
}

// Turns to break the altar's believed enemy lock, about a step each: one per hit left.
int lock_turns(const AltarBelief& belief) {
    if (!belief.enemy_lock) return 0;
    return belief.enemy_lock_hits > 0 ? belief.enemy_lock_hits : static_cast<int>(cambc::constants::altar_lock_hits);
}

// The quickest bank by a crystal (StaticMap::hops): the walk to a source, the channel, the walk from
// the nearest landing and the recall out, as no walk leaves the pocket. Not to `exclude`.
struct HopRoute {
    int hop = -1;
    int steps = unreachable;
};
HopRoute hop_route(const World& world, Pathing& pathing, const Memory& memory, int exclude = -1) {
    HopRoute best;
    const auto& map = world.map();
    const vec2 here = my_position();
    if (map.hops().empty() || !test(pathing.foot(), here)) return best;
    for (int h = 0; h < static_cast<int>(map.hops().size()); ++h) {
        const int a = map.hops()[h].altar;
        if (a < 0 || a == exclude || (a == memory.avoid_altar && world.round < memory.avoid_until)) continue;
        const int walk = pathing.to_hop(h).at(here), inner = pathing.hop_landing_steps(h);
        if (walk == unreachable || inner == unreachable) continue;
        // A lock is broken on arrival, as bank_gems does on foot.
        const int steps = walk + cambc::constants::tp_crystal_time + inner + lock_turns(world.altars[a]) + recall_turns(world);
        if (steps < best.steps)
            best = {h, steps};
    }
    return best;
}

// Towards the hop's sources; on one, the crystal to the free landing nearest `goal` (its altar's
// field by default). The channel cannot be cancelled: it starts only where a tribute of as many
// turns could, and lands only out of the strike of every enemy in sight that could close in
// during it, unless `bold` (the bag's last chance). False on a source that is neither.
bool take_hop(const World& world, Pathing& pathing, Safety& safety, const Memory& memory, int h, const Field* goal,
              bool bold) {
    const auto& hop = world.map().hops()[h];
    if (test(hop.sources, my_position())) {
        if (!bold && !tribute_safe(safety, memory, cambc::constants::tp_crystal_time)) return false;
        auto targets = pathing.teleport_targets();
        // Its camp tiles too, which teleport_targets keeps only while their group is believed dead.
        static bitboard landings{cambc::uninitialized};
        or_into(hop.landings, hop.camp_landings, landings);
        targets &= landings;
        const auto& field = goal ? *goal : pathing.to_altar(hop.altar);
        // A teleport headed for a respawning group's tile delays its return (capture.respawn): off
        // our farm choice's tiles when another landing serves.
        const int farm = memory.farm_group;
        const bool returning = farm >= 0 && farm < static_cast<int>(world.camps.size()) && world.camps[farm].state == CampState::respawning;
        const auto watched = [&](vec2 l) {
            if (bold) return false;
            for (const auto& e : world.enemies)
                if (e.alive && e.visible && dist(l, e.pos) <= safety.strike_of(e).reach + cambc::constants::tp_crystal_time) return true;
            return false;
        };
        vec2 best{-1, -1};
        int best_steps = unreachable;
        bool best_delays = true;
        for (const vec2 l : targets.positions()) {
            const bool delays = returning && world.map().group_at(l) == farm;
            if (const int s = field.at(l); (delays != best_delays ? !delays : s < best_steps) && s < unreachable && !watched(l))
                best = l, best_steps = s, best_delays = delays;
        }
        if (best.x < 0) return false;
        throw_if_stale();
        try {
            if (cambc::self().consumables()[cambc::consumable_type::tp_crystal].use(best)) return true;
        } catch (const cambc::error&) {
        }
    }
    step_safely(world, pathing, pathing.to_hop(h), safety);
    return true;
}

[[gnu::flatten]] void bank_gems(World& world, Pathing& pathing, Safety& safety, Memory& memory, bool heal_step) {
    if (retaining_gems(world, pathing)) return;
    world.throw_if_stale();
    if (submit_here(world, safety, memory)) return;
    const vec2 here = my_position();
    const auto& altars = world.map().altars;
    // One we gave up waiting at (carry_bag) counts as locked until we could reach another.
    const auto avoided = [&](int a) { return a == memory.avoid_altar && world.round < memory.avoid_until; };
    bool any_locked = false;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) any_locked |= world.altars[a].enemy_lock || avoided(a);
    // One cached field covers every altar; per-altar fields are needed only to skip locked ones.
    // `best` is the altar aimed for when one is, else -1 and the shared field leads.
    int best = -1, best_steps = unreachable;
    if (any_locked) {
        for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
            // A tribute tile is within 1 of its altar: an altar this rules out needs no field.
            if (avoided(a) || dist(here, altars[a].pos) - cambc::constants::submit_gems_range >= best_steps) continue;
            const int steps = pathing.to_altar(a).at(here);
            if (steps == unreachable) continue;
            if (const int total = steps + lock_turns(world.altars[a]); total < best_steps) best = a, best_steps = total;
        }
        // Walking reaches only the altar we gave up waiting at, and no hop leads elsewhere when we
        // left: stop avoiding it rather than stand still. submit_here judges its safety again.
        if (best < 0 && world.round < memory.avoid_until && (!carries_crystal() || hop_route(world, pathing, memory).hop < 0))
            memory.avoid_until = world.round;
    }
    // A hit on the aimed altar's lock; it ends the turn of a champion whose attack spends the walk.
    const auto lock_hit_ends_turn = [&] {
        return best >= 0 && world.altars[best].enemy_lock && break_lock(world, best)
               && !world.me().facts().walk_and_attack_independent();
    };
    // A pack we would retreat from stands in the way: around it within the usual detour, else
    // wait outside it until it leaves or a recall (recall_to_bank) takes the bag home.
    if (const auto* zone = pack_zone(world)) {
        if (lock_hit_ends_turn()) return;
        if (pathing.step_towards(best >= 0 ? pathing.to_altar(best) : pathing.to_any_altar(), zone)) submit_here(world, safety, memory);
        return;
    }
    const int walk_steps = best >= 0 ? best_steps : pathing.to_any_altar().at(here);
    if (auto hop = hop_route(world, pathing, memory); hop.hop >= 0 && hop.steps < walk_steps) {
        memory.wants_crystal = true;
        if (carries_crystal()) {
            const int a = world.map().hops()[hop.hop].altar;
            const bool bold = any_risk(world, hop.steps - recall_turns(world) + tribute_turns(world, my_gems()));
            if (take_hop(world, pathing, safety, memory, hop.hop, nullptr, bold)) return;
            // Refused on the source: wait as carry_bag waits at a watched altar, as many rounds as
            // the next way to an altar takes, then take that way.
            const int other = std::min(walk_steps, hop_route(world, pathing, memory, a).steps);
            if (memory.wait_altar != a) memory.wait_altar = a, memory.wait_since = world.round;
            if (other == unreachable || world.round - memory.wait_since < other) {
                decision = 'W';
                return;
            }
            memory.avoid_altar = a;
            memory.avoid_until = world.round + other;
            memory.wait_altar = -1;
            if (hop = hop_route(world, pathing, memory); hop.hop >= 0 && hop.steps < walk_steps) {
                take_hop(world, pathing, safety, memory, hop.hop);
                return;
            }
        }
    }
    const Field& field = best >= 0 ? pathing.to_altar(best) : pathing.to_any_altar();
    if ((dash_across(world, pathing, field) || dash_towards(world, pathing, field)) && submit_here(world, safety, memory)) return;
    if (lock_hit_ends_turn()) return;
    if (heal_step && willow_bank_heal_step(world, pathing, safety, field)) {
        submit_here(world, safety, memory);
        return;
    }
    step_safely(world, pathing, field, safety);
    submit_here(world, safety, memory);
}

// The first altar without an enemy lock that a tribute from p reaches, or -1.
int altar_here(const World& world, vec2 p) {
    const auto& altars = world.map().altars;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a)
        if (!world.altars[a].enemy_lock && dist(p, altars[a].pos) <= cambc::constants::submit_gems_range) return a;
    return -1;
}

bool can_tribute_here(const World& world) { return my_gems() > 0 && altar_here(world, my_position()) >= 0; }

int carried_locks() { return static_cast<int>(cambc::self().consumables()[cambc::consumable_type::altar_lock].count()); }

// The altar a tributer at p channels at.
int tribute_altar(const World& world, vec2 p) {
    const auto& altars = world.map().altars;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a)
        if (dist(p, altars[a].pos) <= static_cast<int>(cambc::constants::submit_gems_range)) return a;
    return -1;
}

bool can_tribute_safely(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    if (retaining_gems(world, pathing)) return false;
    if (!can_tribute_here(world)) return false;
    return tribute_ok(world, safety, memory, tribute_turns(world, my_gems()));
}

// Only a small bag, out of every credible enemy's reach, and never the gems that would win.
// Cassi's and Issac's bags fall together. A credible enemy elsewhere on the map is no reason to
// walk a small bag home.
bool may_chain(const World& world, Safety& safety) {
    if (bag_at_stake(world) >= params::chain_bag_limit || winning_bag(world)) return false;
    return !safety.credible_enemy_may_hit_within(my_position(), params::pursuit_steps);
}

// A bag bound for an altar rides the recall home when that reaches an altar sooner than walking;
// the stop also heals and shops.
bool recall_to_bank(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    if (!memory.banking) return false;
    const vec2 here = my_position();
    if (safety.threatened(here)) return false;
    // With no walk out (a crystal's pocket), the trip by way of spawn is the only one.
    const int walk = pathing.to_any_altar().at(here);
    if (home_trip(world, pathing, my_channel_time(), winning_bag(world)).rounds(walk, 0, 0) < static_cast<float>(walk)) return true;
    // Nor from home on foot: the stop buys the crystal a hop needs.
    return walk == unreachable && memory.wants_crystal && !carries_crystal() && can_buy_crystal();
}

// No enemy seen this round or last could walk into reach before the recall lands: standing
// still to channel while a pack closes in only gets it cancelled.
bool recall_outruns(const World& world, Safety& safety) {
    const vec2 here = my_position();
    const int turns = static_cast<int>(my_channel_time());
    for (const auto& e : world.enemies)
        if (e.alive && e.age(world.round) <= 1
            && (e.visible ? safety.approach(e, here) : dist(here, e.pos) - safety.strike_of(e).reach) <= turns)
            return false;
    return true;
}

// A sieger stepped out of the besieged group's reach goes home to heal before it is needed again;
// once the group is cleared nothing hits us there, and the capture needs us on its tiles.
bool siege_heal_trip(const World& world, const Memory& memory, Safety& safety) {
    return memory.siege && my_health() < params::heal_trip_fraction * my_max_health() && !safety.threatened(my_position())
           && !(memory.claim >= 0 && memory.claim < static_cast<int>(world.camps.size())
                && world.camps[memory.claim].state == CampState::cleared);
}

// Our tribute channel goes on unless it is unsafe and fleeing or fighting back pays. True if the
// turn ends with it; `home` gets want_home's answer if asked.
bool continue_tribute(const World& world, Pathing& pathing, Safety& safety, Memory& memory, std::optional<bool>& home) {
    auto& me = cambc::self();
    decision = 'T';
    // The enemy's winning tribute in reach of a ready stun or a lock is the game: ours waits, unless
    // ours wins first or, winning later, an ally stops theirs in time.
    const auto* ender = game_ender(world);
    const auto* stop = ender && ender->channel == Channel::tribute ? ender : stoppable_winning_tribute(world);
    if (stop && !(winning_bag(world) && ally_stops(world, *stop))) {
        throw_if_stale();
        try {
            me.cancel_submit_gems();
        } catch (const std::exception&) {
        }
        if (!me.is_submitting_gems()) return false;
    }
    if (tribute_ok(world, safety, memory, my_channel_time())) return true;
    // Damage does not interrupt a tribute: cancelling pays only to flee or to fight back.
    if (memory.damage <= 0 && !*(home = want_home(world, pathing, safety, memory)) && !attack_target(world)
        && (winning_bag(world) || !prey(world, safety)))
        return true;
    decision = 't';
    throw_if_stale();
    try {
        me.cancel_submit_gems();
    } catch (const std::exception&) {
        return true;
    }
    return false;
}

// Our recall (start_recall begins one every turn end) is kept to retreat, to bank a bag, to shop,
// to land as a held capture pays or to heal from a siege, else cancelled. True if the turn ends
// with it; `home` gets want_home's answer.
bool continue_recall(const World& world, Pathing& pathing, Safety& safety, Memory& memory, std::optional<bool>& home) {
    auto& me = cambc::self();
    decision = 'K';
    if (game_ender(world)) {
        throw_if_stale();
        try {
            me.cancel_recall();
        } catch (const std::exception&) {
            return true;
        }
        return false;
    }
    home = want_home(world, pathing, safety, memory);
    if (*home && !safety.threatened(my_position()) && !can_tribute_safely(world, pathing, safety, memory) && recall_outruns(world, safety))
        return true;
    decision = 'k';
    if (holding_capture(world, pathing)) {
        if (capture_recall(world, pathing, safety, memory)) {
            decision = 'Q';
            return true;
        }
    } else {
        const auto shop = [&] {
            return wants_shop(world, pathing, safety, memory) && my_channel_time() < pathing.to_ally_spawn().at(my_position());
        };
        // Wanting home, the home keep's reach test binds these too: else we alternate a retreat
        // step with a standing turn on a recall the pursuer cancels.
        if ((!*home || recall_outruns(world, safety)) && (recall_to_bank(world, pathing, safety, memory) || shop())) return true;
        if (siege_heal_trip(world, memory, safety)) return sieged = true; // the trip keeps the siege until home
        // No walk leaves a pocket a crystal took us into, unless to bank there or to farm there.
        if (!test(pathing.foot(), my_position()) && (memory.farm_group < 0 || beyond_walk(world, pathing, memory.farm_group))
            && (my_gems() == 0 || retaining_gems(world, pathing) || !memory.banking))
            return true;
    }
    throw_if_stale();
    try {
        me.cancel_recall();
    } catch (const std::exception&) {
        return true;
    }
    return false;
}

// Carrying: chase a kill worth the risk, bank, wait at an altar until it is safe, or chain another
// capture on the way.
void carry_bag(World& world, Pathing& pathing, Safety& safety, Memory& memory, bool attacked) {
    const bool safe = can_tribute_safely(world, pathing, safety, memory);
    const bool close = closing(world, pathing);
    if (!safe && !close && !winning_bag(world) && chase(world, pathing, safety)) return;
    if (safe) {
        decision = 'B';
        memory.banking = true;
        bank_gems(world, pathing, safety, memory);
        return;
    }
    if (can_tribute_here(world)) {
        // Hit with nothing to hit back: waiting here only takes more.
        if (memory.damage > 0 && !attack_target(world)) {
            pathing.set_guard(nullptr);
            retreat(world, pathing, safety, memory);
            return;
        }
        const vec2 here = my_position();
        const auto& altars = world.map().altars;
        const int at = altar_here(world, here);
        if (at != memory.avoid_altar || world.round >= memory.avoid_until) {
            if (memory.wait_altar != at) memory.wait_altar = at, memory.wait_since = world.round;
            // How long they stay is unknown: wait as many rounds as the walk to the nearest other
            // unlocked altar takes, then walk there.
            int other_steps = carries_crystal() ? hop_route(world, pathing, memory, at).steps : unreachable;
            for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
                if (a == at || world.altars[a].enemy_lock || dist(here, altars[a].pos) - cambc::constants::submit_gems_range >= other_steps) continue;
                other_steps = std::min<int>(other_steps, pathing.to_altar(a).at(here));
            }
            if (other_steps == unreachable || world.round - memory.wait_since < other_steps) {
                decision = 'W';
                return;
            }
            memory.avoid_altar = at;
            memory.avoid_until = world.round + other_steps;
            memory.wait_altar = -1;
        }
    }
    decision = 'B';
    const bool walked = attacked && !world.me().facts().walk_and_attack_independent();
    memory.banking = close || walked || !may_chain(world, safety) || !farm(world, pathing, safety, memory);
    if (memory.banking) bank_gems(world, pathing, safety, memory); // a tribute can still start after a ranged attack
}

} // namespace

} // namespace aph
