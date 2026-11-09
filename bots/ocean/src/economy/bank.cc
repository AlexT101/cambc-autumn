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

// A recall start_recall began and no turn has kept since (continue_recall): next turn cancels it
// unless wanted, so it binds none of our plans.
bool recall_feint = false;

// channelling() but for that feint: a channel our walk will not follow.
bool channel_held() {
    using cambc::champion_state;
    const auto state = my_state();
    return (state.contains(champion_state::recalling) && !recall_feint) || state.contains(champion_state::submitting_gems)
           || state.contains(champion_state::teleporting);
}

// By altar, the round we learned our team locks it (placed, or refused as already locked): update_altars
// sees only locks in sight. Its belief is trusted again once the altar is seen after that round.
std::vector<int> own_lock_round;

// An altar on our side: our walk from spawn to a tile within tribute range of it is at most 2 longer
// than theirs. Kept per altar.
bool our_side(const StaticMap& map, int a) {
    static std::vector<signed char> side;
    if (side.size() < map.altars.size()) side.resize(map.altars.size(), -1);
    if (side[a] < 0) {
        const vec2 p = map.altars[a].pos;
        const auto& field = map.from_ally_spawn();
        int ours = unreachable, theirs = unreachable;
        for (int dx = -1; dx <= 1; ++dx)
            for (int dy = -1; dy <= 1; ++dy)
                if (const vec2 t{p.x + dx, p.y + dy}; (dx || dy) && in_bounds(t))
                    ours = std::min(ours, field.at(t)), theirs = std::min(theirs, map.enemy_spawn_steps(t));
        side[a] = ours == unreachable && theirs == unreachable ? dist(p, map.ally_spawn_centre) <= dist(p, map.enemy_spawn_centre) + 2
                                                               : ours <= theirs + 2;
    }
    return side[a] > 0;
}

[[gnu::flatten]] void place_lock(const World& world) {
    auto& me = cambc::self();
    if (stunned_turn || !world.me().alive) return;
    const auto& lock = me.consumables()[cambc::consumable_type::altar_lock];
    if (lock.count() == 0 || channelling()) return;
    const auto& map = world.map();
    const vec2 here = my_position();
    // The altars in reach, listed once for both passes.
    std::array<int, 8> near;
    int n = 0;
    for (int a = 0; a < static_cast<int>(map.altars.size()); ++a)
        if (dist(here, map.altars[a].pos) <= altar_lock_range) {
            if (n == static_cast<int>(near.size())) {
                n = -1;
                break;
            }
            near[n++] = a;
        }
    if (n == 0) return;
    // Altars with an enemy tributing first.
    for (int pass = 0; pass < 2; ++pass)
        for (int k = 0, end = n < 0 ? static_cast<int>(map.altars.size()) : n; k < end; ++k) {
            const int a = n < 0 ? k : near[k];
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
            // With no tribute to cancel, only altars on our side, or the one we guard, are worth denying.
            if (!enemy_tribute && !our_side(map, a) && !keep_guard_lock(world, a)) continue;
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
// enemies (the unseen from the tiles they may be on) could not kill us within the next few turns, nor
// damage at the rate of the last round (attackers in bushes stay unseen). Judged again every turn of the channel, which is
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

// Gems still to capture, beyond the bag and the tributes allies in sight are channelling (those
// ending within `horizon` turns), before our tributes reach the win.
int gems_short(const World& world, int horizon) {
    struct Key {
        BagKey bag;
        int horizon = 0;
        bool operator==(const Key&) const = default;
    };
    // One slot for the whole game's horizon, one for the other.
    static Key last[2];
    static int kept[2];
    const Key key{bag_key(world), horizon};
    const int slot = horizon == static_cast<int>(cambc::constants::max_rounds) ? 0 : 1;
    if (key == last[slot]) return kept[slot];
    last[slot] = key;
    int pending = 0;
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && a.channel == Channel::tribute && a.channel_end_round - world.round <= horizon)
            pending += a.gems;
    return kept[slot] = static_cast<int>(cambc::constants::winning_gems) - world.score.ally - static_cast<int>(key.bag.gems)
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
    w.behind = false;
    altar_walk_pending = false;
}

namespace {

// Deaths (`gone`, emptied) add to the walk what each dead camp beside it reaches without crossing it.
void walk_deaths(Pathing& pathing, AltarWalk& w, const bitboard& live, bitboard& gone) {
    static bitboard walk_seen{cambc::uninitialized}, walk_grown{cambc::uninitialized};
    or_into(pathing.static_walls(), live, w.walls);
    w.walls |= w.ours;
    square_dilate(w.ours, 1, walk_grown);
    gone &= walk_grown;
    // Most add a few tiles. A flood cut at its reach holds a tile at each step up to it, so one of at
    // most that many tiles is whole; the mask's price is its layers over the chunks within its reach.
    constexpr std::uint16_t near = 8;
    while (!board_empty(gone)) {
        const vec2 t = first_tile(gone);
        w.walls.reachable_tiles_into(t, near, walk_seen);
        if (board_count(walk_seen) > near) w.walls.reachable_tiles_into(t, unreachable, walk_seen);
        w.ours |= walk_seen;
        drop(gone, walk_seen);
        set_tile(gone, t, false);
    }
}

// The tiles beside the returned camps `back` that are walkable with the `live` camps as walls are
// connected among themselves (or there are none): a walk through them can go round instead.
bool round_returns(Pathing& pathing, AltarWalk& w, const bitboard& live, const bitboard& back) {
    static bitboard ring{cambc::uninitialized}, rest{cambc::uninitialized}, seen{cambc::uninitialized};
    or_into(pathing.static_walls(), live, w.walls);
    square_dilate(back, 1, ring);
    drop(ring, w.walls);
    if (board_empty(ring)) return true;
    not_into(ring, rest);
    rest.reachable_tiles_into(first_tile(ring), static_cast<std::uint16_t>(board_count(ring)), seen);
    return seen == ring;
}

// The tiles of `ours` beside the returned camps `back` are connected through the rest of `ours`: a
// walk through `back` goes round instead, so the walk with them as walls is `ours` without them. The
// mask's price grows with its reach, so it floods near them first; past both reaches the walk floods.
bool returns_go_round(const AltarWalk& w, const bitboard& back) {
    static bitboard beside{cambc::uninitialized}, rest{cambc::uninitialized}, seen{cambc::uninitialized};
    square_dilate(back, 1, beside);
    beside &= w.ours;
    drop(beside, back);
    if (board_empty(beside)) return true;
    not_into(w.ours, rest);
    rest |= back;
    const vec2 from = first_tile(beside);
    rest.reachable_tiles_into(from, 16, seen);
    seen &= beside;
    if (seen == beside) return true;
    // Farther, a search that stops once it holds them all: a field's price is its layers over the
    // whole board, a mask's every layer of its reach.
    static cambc::distance_field field;
    static bitboard root{cambc::uninitialized};
    clear_board(root);
    set_tile(root, from);
    clear_board(seen);
    field.compute_to(rest, root, beside, seen);
    seen &= beside;
    return seen == beside;
}

} // namespace

// `ours` lacks only what the deaths since `ours_live` add (round_returns dropped the returns), so
// the flood from spawn with the live camps as walls is `ours` with those added.
void catch_up_walk(Pathing& pathing, AltarWalk& w) {
    if (!w.behind) return;
    w.behind = false;
    static bitboard gone{cambc::uninitialized};
    copy_into(w.ours_live, gone);
    drop(gone, w.access.live);
    walk_deaths(pathing, w, w.access.live, gone);
}

[[gnu::noinline]] const AltarAccess& rebuild_altar_access(const World& world, Pathing& pathing, const bitboard& live) {
    auto& w = altar_walk();
    auto& a = w.access;
    auto& ours = w.ours;
    auto& walls = w.walls;
    a.live_flips = pathing.live_flips();
    const auto& map = world.map();
    static bitboard area{cambc::uninitialized}, seen{cambc::uninitialized}, gone{cambc::uninitialized}, grown{cambc::uninitialized};
    static bitboard tributes{cambc::uninitialized};
    bool updated = false; // `ours` brought up to date without a flood from spawn
    if (a.version > 0 && !map.ally_spawn_tiles.empty()) {
        xor_into(live, a.live, seen);
        and_into(seen, live, area);
        and_into(seen, a.live, gone);
        const bool back = !board_empty(area), died = !board_empty(gone);
        if (!back && !died) return a;
        // The last build's open tiles all lay on our walk (`plain`): with no tribute tile flipped they
        // stay open and on it, and only the walk changes. Deaths only grow it and nothing here reads
        // it, so they are added once something does (catch_up_walk).
        bool quick = false;
        if (w.plain && w.walked) {
            and_into(seen, tributes, grown);
            quick = board_empty(grown);
        }
        // Returns whose ring of tiles walkable now is connected cut no walk: it goes round them, so
        // dropping them from the walk leaves what a flood would reach but for the deaths not yet
        // added, which catch_up_walk adds as before.
        bool lazy = w.walked && (!back || round_returns(pathing, w, live, area) || returns_go_round(w, area));
        if (lazy) {
            if (!w.behind) w.ours_live.swap(a.live), w.behind = true;
            if (back) w.ours_live |= area, drop(ours, area);
            if (quick) {
                ++a.version;
                copy_into(live, a.live);
                return a;
            }
            updated = true;
        } else if (w.walked && !died) {
            // Their ring on our walk connected does as well.
            catch_up_walk(pathing, w);
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
    w.plain = false;
    ++a.version;
    copy_into(live, a.live);
    if (updated) catch_up_walk(pathing, w);
    a.blocks.clear();
    clear_board(a.open);
    clear_board(a.opened);
    a.any_open = a.camp_hopped = false;
    if (map.ally_spawn_tiles.empty()) return a;
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
    static bitboard hopped{cambc::uninitialized}; // camp hops' tribute tiles
    clear_board(hopped);
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
            if (board_empty(seen)) {
                drop(a.open, map.altars[h.altar].tribute_tiles());
            } else if (h.camps) { // its sources are on the walk with every camp standing, so on ours
                and_into(map.altars[h.altar].tribute_tiles(), h.pocket, seen);
                drop(seen, live);
                hopped |= seen;
            }
        }
    }
    a.any_open = !a.open.is_empty();
    if (a.any_open) {
        copy_into(a.open, a.opened);
        w.plain = !off_walk && w.walked;
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
    if (!board_empty(hopped)) copy_into(hopped, a.open), a.any_open = a.camp_hopped = true;
    return a;
}

const AltarAccess& altar_access(const World& world, Pathing& pathing) {
    const auto& a = altar_walk().access;
    const auto& live = pathing.live_camps();
    if (a.version > 0 && a.live_flips == pathing.live_flips()) return a;
    return rebuild_altar_access(world, pathing, live);
}

// Whether our walk with live camps as walls (altar_walk().ours) reaches an open tribute tile of
// `altar` (any altar for -1). Pathing's altar fields price static walls only: a camp hop's altar
// reads a few steps away though no walk reaches it while its ring stands.
bool altar_walked(const World& world, Pathing& pathing, int altar) {
    const auto& map = world.map();
    if (!map.any_camp_hop()) return true;
    const auto& a = altar_access(world, pathing);
    auto& w = altar_walk();
    if (!w.walked) flood_altar_walk(world, pathing, w);
    catch_up_walk(pathing, w);
    static bitboard on{cambc::uninitialized};
    and_into(a.open, w.ours, on);
    if (altar >= 0) on &= map.altars[altar].tribute_tiles();
    return !board_empty(on);
}

bool in_camp_pocket(const StaticMap& map, vec2 p) {
    if (!map.any_camp_hop()) return false;
    for (const auto& h : map.hops())
        if (h.camps && test(h.pocket, p)) return true;
    return false;
}

// The round until which take_hop's refusal of a camp hop holds the bag back (bank_gems).
int ring_refused_until = -1;

// A camp hop's pocket we stand in, off our walk: no walk leaves it while its ring stands.
bool sealed_in(const World& world, Pathing& pathing, vec2 p) {
    if (!in_camp_pocket(world.map(), p)) return false;
    altar_access(world, pathing);
    auto& w = altar_walk();
    if (!w.walked) flood_altar_walk(world, pathing, w);
    catch_up_walk(pathing, w);
    return !test(w.ours, p);
}

// The static field's steps from p to `altar` (any for -1), unless no walk reaches it
// (altar_walked); from inside a camp hop's pocket, its own.
int altar_steps(const World& world, Pathing& pathing, vec2 p, int altar) {
    const int steps = (altar < 0 ? pathing.to_any_altar() : pathing.to_altar(altar)).at(p);
    if (steps == unreachable || in_camp_pocket(world.map(), p)) return steps;
    return altar_walked(world, pathing, altar) ? steps : unreachable;
}

// access_fire's fire on the open tiles. `active`: for each stirring group with a member that lives
// and may be awake, in group order, its id, then its word count, then those members' words.
static float fire_on_open(const World& world, const AltarAccess& a, const std::vector<std::uint64_t>& active) {
    const auto& map = world.map();
    const auto& groups = map.groups;
    // Every tribute tile, which the open ones are among, in board order; and room for the open ones.
    static std::vector<vec2> tributes, open;
    if (tributes.empty()) {
        bitboard b;
        for (const auto& t : map.altars) b |= t.tribute_tiles();
        tributes.resize(std::max<std::size_t>(1, board_count(b)));
        tributes.resize(std::min<std::size_t>(positions_into(b, tributes.data(), static_cast<std::uint32_t>(tributes.size())), tributes.size()));
        open.resize(std::max<std::size_t>(1, tributes.size()));
    }
    const std::size_t T = tributes.size();
    // Per group once it has an active member: per tribute tile, the members reaching it (bit i: member
    // i), made when first read; and the members by Strength when every Strength is whole with at most
    // 4 kinds (`kinds` -1 else).
    struct Reach {
        int words = 0, kinds = -1, chunks = 0;
        float total = 0;
        std::array<float, 4> strength{};
        std::array<int, 4> box{}; // beyond it no member reaches
        std::vector<std::uint64_t> kind_bits, at; // kinds x words, T x words
        std::vector<std::uint8_t> made;           // per tribute tile
        std::vector<std::int8_t> xyr;             // members' x, y and reach, 16 a chunk, padded with reach -1
    };
    static std::vector<std::unique_ptr<Reach>> reach;
    if (reach.size() != groups.size()) reach.resize(groups.size());
    const auto make = [&](int g) -> Reach& {
        if (reach[g]) return *reach[g];
        reach[g] = std::make_unique<Reach>();
        auto& r = *reach[g];
        const auto& members = groups[g].members;
        const int n = static_cast<int>(members.size());
        r.words = (n + 63) / 64;
        r.at.assign(T * static_cast<std::size_t>(r.words), 0);
        r.made.assign(T, 0);
        r.kinds = 0;
        r.kind_bits.assign(4 * static_cast<std::size_t>(r.words), 0);
        for (int i = 0; i < n && r.kinds >= 0; ++i) {
            const float s = members[i].strength;
            if (s == 0) continue;
            r.total += s;
            int k = 0;
            while (k < r.kinds && r.strength[k] != s) ++k;
            if (k == 4 || s != std::floor(s) || !(s > 0)) {
                r.kinds = -1;
                break;
            }
            if (k == r.kinds) r.strength[r.kinds++] = s;
            r.kind_bits[static_cast<std::size_t>(k * r.words + i / 64)] |= std::uint64_t{1} << (i % 64);
        }
        // Sixteen members a vector: coordinates below 100 and their differences fit a signed byte.
        r.chunks = (n + 15) / 16;
        const int m16 = 16 * r.chunks;
        r.xyr.assign(3 * static_cast<std::size_t>(m16), 0);
        std::fill(r.xyr.begin() + 2 * m16, r.xyr.end(), std::int8_t{-1});
        vec2 lo = members[0].pos, hi = lo;
        int most = 0;
        for (int i = 0; i < n; ++i) {
            const auto& m = members[i];
            r.xyr[i] = static_cast<std::int8_t>(m.pos.x), r.xyr[m16 + i] = static_cast<std::int8_t>(m.pos.y);
            r.xyr[2 * m16 + i] = static_cast<std::int8_t>(m.reach);
            lo = {std::min(lo.x, m.pos.x), std::min(lo.y, m.pos.y)}, hi = {std::max(hi.x, m.pos.x), std::max(hi.y, m.pos.y)};
            most = std::max(most, m.reach);
        }
        r.box = {lo.x - most, hi.x + most, lo.y - most, hi.y + most};
        return r;
    };
    const auto members_at = [&](Reach& r, std::size_t k) -> const std::uint64_t* {
        auto* bits = &r.at[k * static_cast<std::size_t>(r.words)];
        if (r.made[k]) return bits;
        r.made[k] = 1;
        const vec2 t = tributes[k];
        if (t.x < r.box[0] || t.x > r.box[1] || t.y < r.box[2] || t.y > r.box[3]) return bits;
        const int m16 = 16 * r.chunks;
        const std::int8_t *mx = r.xyr.data(), *my = mx + m16, *mr = my + m16;
        for (int c = 0; c < r.chunks; ++c) {
#if defined(__wasm_simd128__)
            const v128_t d = wasm_i8x16_max(wasm_i8x16_abs(wasm_i8x16_sub(wasm_v128_load(&mx[16 * c]), wasm_i8x16_splat(static_cast<std::int8_t>(t.x)))),
                                            wasm_i8x16_abs(wasm_i8x16_sub(wasm_v128_load(&my[16 * c]), wasm_i8x16_splat(static_cast<std::int8_t>(t.y)))));
            const auto hit = static_cast<std::uint64_t>(wasm_i8x16_bitmask(wasm_i8x16_le(d, wasm_v128_load(&mr[16 * c]))));
#else
            std::uint64_t hit = 0;
            for (int j = 0; j < 16; ++j)
                if (std::max(std::abs(mx[16 * c + j] - t.x), std::abs(my[16 * c + j] - t.y)) <= mr[16 * c + j]) hit |= std::uint64_t{1} << j;
#endif
            bits[c / 4] |= hit << (16 * (c % 4));
        }
        return bits;
    };
    // Whole Strengths summing below 2^24 make every float sum of them exact, so in any order it is
    // the member-by-member one. Groups with no active member add nothing either way.
    bool exact = true;
    float total = 0;
    for (std::size_t at = 0; at < active.size(); at += 2 + active[at + 1]) {
        const auto& r = make(static_cast<int>(active[at]));
        exact &= r.kinds >= 0;
        total += r.total;
    }
    exact &= total < 16777216.0f;
    float fire = std::numeric_limits<float>::max();
    const auto n = std::min<std::size_t>(positions_into(a.open, open.data(), static_cast<std::uint32_t>(open.size())), open.size());
    std::size_t k = 0;
    for (const vec2 t : std::span{open.data(), n}) {
        while (k < T && tributes[k] != t) ++k;
        float f = 0;
        for (std::size_t at = 0; at < active.size(); at += 2 + active[at + 1]) {
            const int g = static_cast<int>(active[at]);
            const std::uint64_t* live = &active[at + 2];
            auto& r = *reach[g];
            const auto* bits = members_at(r, k);
            if (exact) {
                for (int s = 0; s < r.kinds; ++s) {
                    int count = 0;
                    for (int w = 0; w < r.words; ++w) count += std::popcount(bits[w] & live[w] & r.kind_bits[static_cast<std::size_t>(s * r.words + w)]);
                    f += r.strength[s] * static_cast<float>(count);
                }
            } else {
                const auto& members = groups[g].members;
                for (int w = 0; w < r.words; ++w)
                    for (std::uint64_t m = bits[w] & live[w]; m; m &= m - 1) f += members[static_cast<std::size_t>(64 * w + std::countr_zero(m))].strength;
            }
        }
        if ((fire = std::min(fire, f)) <= 0) break;
    }
    return fire;
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
    // The fire reads the open tiles and the members of the stirring groups near them that live and
    // may be awake (not maybe_asleep): kept while those are, as health moves every round in a fight
    // but seldom to 0, and a rebuild of the access (any camp's death or return) seldom moves the open
    // tiles. Each awake group's live words are read again only when its version (bumped by every
    // health write) moved.
    struct Live {
        std::uint32_t version = 0;
        std::int32_t at = -1; // its words in `words`, -1 until read
    };
    static std::vector<Live> lives;
    static std::vector<std::uint64_t> words, key, now;
    now.clear();
    world.each_stirring([&](int g) {
        if (near[g] < 0) {
            near[g] = 0;
            for (const auto& m : groups[g].members)
                for (const auto& altar : map.altars)
                    if (dist(m.pos, altar.pos) <= m.reach + cambc::constants::submit_gems_range) near[g] = 1;
        }
        const auto& c = world.camps[g];
        if (!near[g] || c.awake != Awake::awake) return;
        if (lives.size() != groups.size()) lives.resize(groups.size());
        const std::size_t n = groups[g].members.size(), count = (n + 63) / 64;
        auto& live = lives[g];
        if (live.at < 0 || live.version != c.version) {
            if (live.at < 0) live.at = static_cast<std::int32_t>(words.size()), words.resize(words.size() + count);
            live.version = c.version;
            auto* w = &words[static_cast<std::size_t>(live.at)];
            std::fill(w, w + count, 0);
            for (std::size_t i = 0; i < n; ++i) w[i / 64] |= static_cast<std::uint64_t>(c.health[i] > 0) << (i % 64);
        }
        const auto* w = &words[static_cast<std::size_t>(live.at)];
        std::uint64_t any = 0;
        for (std::size_t i = 0; i < count; ++i) any |= w[i] & (i == 0 ? ~c.asleep : ~std::uint64_t{0});
        if (!any) return;
        now.push_back(static_cast<std::uint64_t>(g));
        now.push_back(count);
        for (std::size_t i = 0; i < count; ++i) now.push_back(w[i] & (i == 0 ? ~c.asleep : ~std::uint64_t{0}));
    });
    // With no such member every open tile is free of fire.
    if (now.empty()) return fire = a.any_open ? 0.0f : fire;
    static float kept = 0;
    static int open_version = 0;
    static bitboard open{cambc::uninitialized};
    bool same = true;
    if (open_version != a.version) {
        same = open_version > 0 && boards_equal(open, a.open);
        if (!same) copy_into(a.open, open);
        open_version = a.version;
    }
    if (same && now == key) return fire = kept;
    key.swap(now);
    fire = kept = fire_on_open(world, a, key);
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
    if (bag < params::min_bank && !winning_bag(world) && !closing(world, pathing)) return 0;
    if (world.round < ring_refused_until && altar_steps(world, pathing, my_position(), -1) == unreachable) return 0;
    // Only a crystal reaches an altar and we can neither use nor buy one: farm the gold first. A
    // recall out of a pocket to a spawn with a walk to one banks it. Altars' hops come first.
    if (!world.map().hops().empty() && world.map().hops()[0].altar >= 0 && altar_steps(world, pathing, my_position(), -1) == unreachable && !carries_crystal()
        && !can_buy_crystal() && altar_steps(world, pathing, recall_landing(world), -1) == unreachable)
        return 0;
    return bag;
}

// No altar is usable for the team's largest bag (an unseen ally's as posted).
bool altars_sealed(const World& world, Pathing& pathing) {
    int bag = static_cast<int>(my_gems());
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive) bag = std::max(bag, a.visible ? a.gems : comms::bag_of(world, a.index));
    return !altar_usable(world, pathing, bag, my_max_health()) || altar_access(world, pathing).camp_hopped;
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
int race_left_now(const World& world) {
    int short_by = gems_short(world);
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && !(a.visible && a.channel == Channel::tribute))
            short_by -= a.visible ? a.gems : comms::bag_of(world, a.index);
    if (short_by <= 0) return 0;
    const float rate = world.ally_rate();
    return rate > 0 ? static_cast<int>(static_cast<float>(short_by) / rate) : rounds_left(world);
}
int race_left(const World& world) {
    static BagKey last;
    static int kept = 0;
    const BagKey key = bag_key(world);
    if (key == last) return kept;
    last = key;
    return kept = race_left_now(world);
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
        if ((avoided || world.altars[a].enemy_lock || here != world.turn_start)
            && !tribute_ok(world, safety, memory, tribute_turns(world, my_gems())))
            return false;
        place_lock(world); // first: it cancels every tribute at its altar
        place_ward(world, memory); // first: no ward goes down while channelling
        throw_if_stale();
        try {
            me.submit_gems(altars[a].pos);
            const int bag = static_cast<int>(my_gems());
            const auto cut = [](int g) { return tribute_turns(g, false) - tribute_turns(g, true); };
            // A restart of a cancelled channel (no tribute of its size since) counts only the gems it adds.
            static int pending = 0, score_at = 0;
            const bool restart = pending > 0 && bag >= pending && world.score.ally - score_at < pending;
            income.tribute_cut += static_cast<float>(restart ? std::max(0, cut(bag) - cut(pending)) : cut(bag));
            pending = bag, score_at = world.score.ally;
            return true;
        } catch (const cambc::error&) {
        }
    }
    return false;
}

// A melee champion hits on arrival; one already at the altar hits this turn.
int lock_turns(const AltarBelief& belief, const ChampionFacts& facts, int walk) {
    if (!belief.enemy_lock) return 0;
    const int hits = belief.enemy_lock_hits > 0 ? belief.enemy_lock_hits : static_cast<int>(cambc::constants::altar_lock_hits);
    return std::max(0, hits - (walk == 0 || facts.walk_and_attack_independent() ? 1 : 0));
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
    if (map.hops().empty() || !pathing.on_foot(here)) return best;
    for (int h = 0; h < static_cast<int>(map.hops().size()); ++h) {
        const int a = map.hops()[h].altar;
        if (a < 0 || a == exclude || (a == memory.avoid_altar && world.round < memory.avoid_until)) continue;
        const int walk = pathing.to_hop(h).at(here), inner = pathing.hop_landing_steps(h);
        if (walk == unreachable || inner == unreachable) continue;
        // A lock is broken on arrival, as bank_gems does on foot.
        const int steps = walk + cambc::constants::tp_crystal_time + inner
                          + lock_turns(world.altars[a], world.me().facts(), inner)
                          + recall_turns(world);
        if (steps < best.steps)
            best = {h, steps};
    }
    return best;
}

// No enemy in sight, nor any out of sight from the tiles it may be on (Safety::credible_unseen), could
// wake a camp hop's ring (a hit on any live member: its basic attack's or a spell's reach) within
// `turns`: once awake it kills whoever is inside, bag and all, and nothing leaves it (sealed-altars.md).
bool ring_quiet(const World& world, Safety& safety, const StaticMap::Hop& hop, int turns) {
    const auto& map = world.map();
    for (const auto& e : world.enemies) {
        if (!e.alive || !(e.visible || safety.credible_unseen(e))) continue;
        const int wake = std::max(e.facts().basic_reach(), e.facts().cast_reach()) + turns;
        for (const int g : hop.ring) {
            const auto& c = world.camps[g];
            if (c.state != CampState::alive) continue;
            const auto& members = map.groups[g].members;
            for (std::size_t i = 0; i < members.size(); ++i)
                if (c.health[i] > 0 && (e.visible ? dist(members[i].pos, e.pos) <= wake : possible_within(e, members[i].pos, wake)))
                    return false;
        }
    }
    return true;
}

// Towards the hop's sources; on one, the crystal to the free landing nearest `goal` (its altar's
// field by default), of those the one a camp hop's ring fires on least should it wake. The channel cannot be cancelled: it starts only where a tribute of as many
// turns could, and lands only out of the strike of every enemy in sight that could close in
// during it, unless `bold` (the bag's last chance). False on a source that is neither.
bool take_hop(const World& world, Pathing& pathing, Safety& safety, const Memory& memory, int h, const Field* goal,
              bool bold) {
    const auto& hop = world.map().hops()[h];
    if (test(hop.sources, my_position())) {
        if (!bold && !tribute_safe(safety, memory, cambc::constants::tp_crystal_time)) return false;
        // The bag is at stake from the channel's start to the tribute's end.
        if (!bold && hop.camps && !ring_quiet(world, safety, hop, cambc::constants::tp_crystal_time + tribute_turns(world, my_gems())))
            return false;
        auto targets = pathing.teleport_targets();
        // Its camp tiles too, which teleport_targets keeps only while their camp is believed dead.
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
                if (e.alive && e.visible && enemy_reach::within(world, e, enemy_reach::origin(e), l, safety.strike_of(e).reach + cambc::constants::tp_crystal_time))
                    return true;
            return false;
        };
        const auto ring_fire = [&](vec2 l) {
            float fire = 0;
            for (const int g : hop.ring) {
                const auto& members = world.map().groups[g].members;
                for (std::size_t i = 0; i < members.size(); ++i)
                    if (world.camps[g].health[i] > 0 && dist(members[i].pos, l) <= members[i].reach) fire += members[i].strength;
            }
            return fire;
        };
        vec2 best{-1, -1};
        int best_steps = unreachable;
        bool best_delays = true;
        float best_fire = 0;
        for (const vec2 l : targets.positions()) {
            const bool delays = returning && world.map().group_at(l) == farm;
            const int s = field.at(l);
            if (s == unreachable || (delays != best_delays ? delays : s > best_steps) || watched(l)) continue;
            const float fire = ring_fire(l);
            if (delays == best_delays && s == best_steps && fire >= best_fire) continue;
            best = l, best_steps = s, best_delays = delays, best_fire = fire;
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

// An enemy carrying gems in a camp hop's pocket: a hit on a member of its sleeping ring wakes the
// whole group (camps.wake), and each member fires at the nearest champion in its reach
// (camps.attack), so the enemy inside takes the ring's fire and dies with its bag, which a camp
// kill hands nobody (combat.camp_kill). We hit only where the members that could pick us (as near
// us as the enemy: ties go by turn order) fire less than our health in a phase; the next turn
// steps out of their reach. Not while an ally is inside, nor at a tribute that ends first.
// The enemy is believed inside while no walk could have taken it out: seen there, or unseen there
// for less than a recall takes; one seen teleporting there is walked towards, and hit once landed.
bool wake_ring(const World& world, Pathing& pathing, Safety& safety) {
    const auto& map = world.map();
    if (!map.any_camp_hop() || !world.me().alive) return false;
    const auto& f = world.me().facts();
    const vec2 here = my_position();
    struct Live {
        int g, i;
        vec2 pos;
        int reach;
        float strength;
        int picks; // min(reach, its distance to the prey): it fires on a tile this near it before the prey
    };
    static std::vector<Live> live;
    for (const auto& h : map.hops()) {
        if (!h.camps) continue;
        const ChampionBelief* prey = nullptr;
        vec2 at{-1, -1};
        for (const auto& e : world.enemies) {
            if (!e.alive || e.gems <= 0 || (prey && e.gems <= prey->gems)) continue;
            if (e.channel == Channel::tribute && e.channel_end_round <= world.round) continue; // banked
            const vec2 p = e.teleport_pending() ? e.tp_dest : e.pos;
            if (!in_bounds(p) || !test(h.pocket, p)) continue;
            if (!e.visible
                && (test(world.visible, p)
                    || world.round >= (e.seen_channel == Channel::recall ? e.channel_end_round : e.pos_round + e.recall_turns())))
                continue;
            prey = &e, at = p;
        }
        if (!prey) continue;
        live.clear();
        float on_prey = 0;
        for (const int g : h.ring) {
            const auto& c = world.camps[g];
            if (c.state != CampState::alive) continue;
            if (c.awake == Awake::awake) return false; // already firing
            const auto& members = map.groups[g].members;
            for (std::size_t i = 0; i < members.size(); ++i) {
                const auto& m = members[i];
                if (c.health[i] <= 0 || m.strength <= 0) continue;
                const int d = dist(m.pos, at);
                live.push_back({g, static_cast<int>(i), m.pos, m.reach, m.strength, std::min(m.reach, d)});
                if (d <= m.reach) on_prey += m.strength;
            }
        }
        if (on_prey <= 0) continue;
        // Once it dies the ring fires on whoever is nearest: no ally may be in its reach.
        for (const auto& a : world.allies) {
            if (a.is_self || !a.alive || a.pos.x < 0) continue;
            for (const auto& m : live)
                if (dist(m.pos, a.pos) <= m.reach) return false;
        }
        // A shield in sight absorbs the phases it lasts for; one out of sight is not trusted.
        const float per_phase = on_prey * prey->camp_taken;
        const float shield = prey->visible ? std::min(prey->shield, per_phase * static_cast<float>(prey->shield_turns)) : 0.0f;
        const int phases = static_cast<int>(std::ceil((prey->health + shield) / per_phase));
        const int channel = prey->channel == Channel::tribute ? prey->channel_end_round - world.round : -1;
        if (channel >= 0 && channel < phases) continue;
        const float health = my_health() / camp_hit_factor();
        // Fire only grows as members add (positive floats, rounding monotone): no tile's sum exceeds
        // the whole ring's, and a sum that reaches health stays there.
        float ring = 0;
        for (const auto& m : live) ring += m.strength;
        const auto safe = [&](vec2 q) {
            if (ring < health) return true;
            float fire = 0;
            for (const auto& m : live)
                if (dist(m.pos, q) <= m.picks && (fire += m.strength) >= health) return false;
            return fire < health;
        };
        int spell = -1;
        if (my_can_cast())
            for (int s = 0; s < 2 && spell < 0; ++s)
                if (f.abilities[s].target == Targeting::ground && castable(world, s)) spell = s;
        if (!prey->teleport_pending() && safe(here)) {
            // One try each: a refused hit throws (~3.9k fuel).
            bool tried_attack = !my_can_attack(), tried_spell = spell < 0;
            for (const auto& m : live) {
                if (!tried_attack && dist(m.pos, here) <= f.attack_range()) {
                    tried_attack = true;
                    throw_if_stale();
                    try {
                        cambc::self().attack(map.groups[m.g].camp(m.i));
                        ++camp_hits();
                        return true;
                    } catch (const cambc::error&) {
                    }
                }
                if (!tried_spell && dist(m.pos, here) <= ability_range + ground_radius) {
                    tried_spell = true;
                    // A tile within range whose 3x3 covers the member.
                    const vec2 t{std::clamp(m.pos.x, here.x - ability_range, here.x + ability_range),
                                 std::clamp(m.pos.y, here.y - ability_range, here.y + ability_range)};
                    throw_if_stale();
                    try {
                        if (cast_slot(spell, t)) {
                            ++camp_hits();
                            return true;
                        }
                    } catch (const cambc::error&) {
                    }
                }
            }
        }
        if (!my_can_move()) return false;
        // Tiles to hit from: a basic attack's reach of a member, or a ground spell's. Kept while the
        // prey, the live members, our reach and the health that bounds the fire stay: a tributing
        // prey stands still.
        static vec2 key_prey{-1, -1};
        static std::size_t key_live = 0;
        static int key_reach = -1, key_health = -1, key_round = -1;
        static std::optional<Field> field;
        const int reach = spell >= 0 ? ability_range + ground_radius : f.attack_range();
        if (key_prey != at || key_live != live.size() || key_reach != reach || key_health != static_cast<int>(health)
            || key_round < world.round - 1) {
            key_prey = at, key_live = live.size(), key_reach = reach, key_health = static_cast<int>(health);
            field.reset();
            static bitboard members{cambc::uninitialized}, goals{cambc::uninitialized};
            clear_board(members);
            for (const auto& m : live) set_tile(members, m.pos);
            square_dilate(members, reach, goals);
            goals &= map.standable;
            drop(goals, h.pocket);
            if (ring >= health)
                for (const vec2 q : goals.positions())
                    if (!safe(q)) set_tile(goals, q, false);
            if (!board_empty(goals)) field.emplace(make_field(pathing.static_walls(), goals));
        }
        key_round = world.round;
        if (!field) continue;
        // In time for the ring to kill it before its channel ends.
        if (const int steps = field->at(here); steps == unreachable || (channel >= 0 && steps + phases >= channel)) continue;
        decision = Branch::attack;
        step_safely(world, pathing, *field, safety);
        return true;
    }
    return false;
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
            const int steps = altar_steps(world, pathing, here, a);
            if (steps == unreachable) continue;
            if (const int total = steps + lock_turns(world.altars[a], world.me().facts(), steps); total < best_steps) best = a, best_steps = total;
        }
        // Walking reaches only the altar we gave up waiting at, and no hop leads elsewhere when we
        // left: stop avoiding it rather than stand still. submit_here judges its safety again.
        if (best < 0 && world.round < memory.avoid_until && (!carries_crystal() || hop_route(world, pathing, memory).hop < 0))
            memory.avoid_until = world.round;
    }
    // A hit on the aimed altar's lock; it ends the turn of a champion whose attack spends the walk,
    // with a tribute if that hit broke it within reach.
    const auto lock_hit_ends_turn = [&] {
        if (best < 0 || !world.altars[best].enemy_lock || !break_lock(world, best) || world.me().facts().walk_and_attack_independent())
            return false;
        submit_here(world, safety, memory);
        return true;
    };
    // A melee champion's hit on the lock it stepped beside, then the tribute if that broke it.
    const auto hit_and_submit = [&] {
        if (best >= 0 && world.altars[best].enemy_lock && world.me().facts().walk_and_attack_independent()) break_lock(world, best);
        submit_here(world, safety, memory);
    };
    // A pack we would retreat from stands in the way: around it within the usual detour, else
    // wait outside it until it leaves or a recall (recall_to_bank) takes the bag home.
    if (const auto* zone = pack_zone(world, safety)) {
        if (lock_hit_ends_turn()) return;
        if (pathing.step_towards(best >= 0 ? pathing.to_altar(best) : pathing.to_any_altar(), zone)) hit_and_submit();
        return;
    }
    const int walk_steps = best >= 0 ? best_steps : altar_steps(world, pathing, here, -1);
    if (auto hop = hop_route(world, pathing, memory); hop.hop >= 0 && hop.steps < walk_steps) {
        memory.wants_crystal = true;
        if (carries_crystal()) {
            const int a = world.map().hops()[hop.hop].altar;
            const bool bold = any_risk(world, hop.steps - recall_turns(world) + tribute_turns(world, my_gems()));
            if (take_hop(world, pathing, safety, memory, hop.hop, nullptr, bold)) return;
            // A camp hop's source is in its ring's reach: the bag farms elsewhere for as long as the
            // hop's channel and tribute would have taken, then comes back (bankable_bag).
            if (world.map().hops()[hop.hop].camps) {
                ring_refused_until = world.round + cambc::constants::tp_crystal_time + tribute_turns(world, my_gems());
                return;
            }
            // Refused on the source: wait as carry_bag waits at a watched altar, as many rounds as
            // the next way to an altar takes, then take that way.
            const int other = std::min(walk_steps, hop_route(world, pathing, memory, a).steps);
            if (memory.wait_altar != a) memory.wait_altar = a, memory.wait_since = world.round;
            if (other == unreachable || world.round - memory.wait_since < other) {
                decision = Branch::wait_altar;
                return;
            }
            memory.avoid_altar = a;
            memory.avoid_until = world.round + other;
            memory.wait_altar = -1;
            if (hop = hop_route(world, pathing, memory); hop.hop >= 0 && hop.steps < walk_steps) {
                take_hop(world, pathing, safety, memory, hop.hop);
                return;
            }
        } else if (walk_steps == unreachable) {
            // Home for one: a walk there, or the turn-end recall (recall_to_bank) when that is sooner.
            if (pathing.to_ally_spawn().at(here) <= recall_turns(world)) step_safely(world, pathing, pathing.to_ally_spawn(), safety);
            return;
        }
    }
    const Field& field = best >= 0 ? pathing.to_altar(best) : pathing.to_any_altar();
    if (lock_hit_ends_turn()) return;
    if (heal_step && willow_bank_heal_step(world, pathing, safety, field)) {
        submit_here(world, safety, memory);
        return;
    }
    step_safely(world, pathing, field, safety);
    hit_and_submit();
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

// A turn-end tribute wherever one can start (Mite's habit), else the caller's recall feint: the turn has acted,
// so standing in a channel costs nothing, and next turn continue_tribute keeps or cancels it.
bool mite_tribute_habit(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    if (stunned_turn || !world.me().alive || channelling() || my_gems() <= 0) return false;
    const vec2 here = my_position();
    if (here.x < 0) return false;
    const int a = altar_here(world, here);
    if (a < 0 || enemy_lock_live(world.map().altars[a].pos) || retaining_gems(world, pathing)) return false;
    if (tribute_turns(world, my_gems()) > rounds_left(world)) return false;
    if (want_home(world, pathing, safety, memory)) return false;
    throw_if_stale();
    try {
        cambc::self().submit_gems(world.map().altars[a].pos);
        return true;
    } catch (const cambc::error&) {
    }
    return false;
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
    return !safety.may_reach_within(my_position(), params::pursuit_steps);
}

// A bag bound for an altar rides the recall home when that reaches an altar sooner than walking;
// the stop also heals and shops. A bag new this turn counts once carry_bag is sure to bank it: else
// the feint is cancelled and the recall restarted a round later.
bool recall_to_bank(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    if (!memory.banking && !(banks_bag(world, pathing) && (closing(world, pathing) || !may_chain(world, safety)))) return false;
    const vec2 here = my_position();
    if (safety.threatened(here)) return false;
    // With no walk out (a crystal's pocket), the trip by way of spawn is the only one.
    const int walk = altar_steps(world, pathing, here, -1);
    // On our walk with a crystal for a camp hop, the hop is the trip (hop_route).
    if (walk == unreachable && carries_crystal() && world.map().any_camp_hop() && !sealed_in(world, pathing, my_position())) return false;
    if (home_trip(world, pathing, my_channel_time(), winning_bag(world)).rounds(walk, 0, 0) < static_cast<float>(walk)) return true;
    // Nor from home on foot: the stop buys the crystal a hop needs.
    return walk == unreachable && memory.wants_crystal && !carries_crystal() && can_buy_crystal();
}

// No credible enemy (an unseen one from the tiles it may be on) could walk into reach before the
// recall lands: standing still to channel while a pack closes in only gets it cancelled. `turns`:
// the channel left, by default ours now.
bool recall_outruns(Safety& safety, int turns) {
    if (turns < 0) turns = static_cast<int>(my_channel_time());
    return !safety.may_reach_within(my_position(), turns);
}

// The recall farm chose to reach group g by (Memory::recall_farm) is kept while, priced as farm
// prices it (FarmRecall::sooner), it still beats the walk (carrying, with the bag's trip on to an altar
// too) and no enemy can cancel it.
bool recall_to_farm(const World& world, Pathing& pathing, Safety& safety, const Memory& memory, int g) {
    if (g < 0 || g != memory.farm_group || g >= static_cast<int>(world.camps.size()) || memory.siege) return false;
    const vec2 here = my_position();
    if (safety.threatened(here) || !recall_outruns(safety)) {
        debug_block({ std::printf("RFWHY %d %u threat %d\n", world.round, my_handle(), static_cast<int>(safety.threatened(here))); });
        return false;
    }
    const auto* centre = pathing.centre_field(g);
    if (!centre) return false;
    const auto& c = world.camps[g];
    const int respawn = c.state == CampState::respawning ? std::max(0, c.respawn_round - world.round) : 0;
    const auto r = farm_recall(world, pathing, static_cast<int>(my_channel_time()));
    const int walk = centre->at(here);
    const float via = r.sooner(pathing.centre_to_spawn(g), respawn, walk);
    bool kept = via < static_cast<float>(unreachable);
    // A bag to bank after the group, as farm's loop prices it: the walk on to an altar then needs no second stop.
    if (kept && my_gems() > 0 && banks_bag(world, pathing)) {
        const bool wins = static_cast<int>(world.map().groups[g].gems) >= gems_short(world, params::tribute_window);
        HomeTrip t = home_trip(world, pathing, recall_turns(world), winning_bag(world) || wins);
        if (wins) t.heal = t.emblem = 0;
        HomeTrip healed = t;
        healed.heal = healed.emblem = 0, healed.hurt = 0;
        const int to = pathing.centre_to_altar(g), capture = capture_rounds(world);
        const float back = t.rounds(to, capture, 0), back_healed = healed.rounds(to, capture, 0);
        kept = via + back_healed < static_cast<float>(walk + std::max(0, respawn - walk)) + back;
    }
    if (!kept) {
        debug_block({ std::printf("RFWHY %d %u walk %d out %d respawn %d channel %d hurt %d value %.1f\n", world.round, my_handle(),
                                  walk, pathing.centre_to_spawn(g), respawn, r.channel, r.hurt, r.value); });
    }
    return kept;
}

// A sieger stepped out of the besieged group's reach goes home to heal before it is needed again,
// by the recall while the walk is longer (siege() walks a shorter one); once the group is cleared
// nothing hits us there, and the capture needs us on its tiles.
bool siege_heal_trip(const World& world, Pathing& pathing, const Memory& memory, Safety& safety) {
    return memory.siege && my_health() < params::heal_trip_fraction * my_max_health() && !safety.threatened(my_position())
           && !walk_beats_recall(world, pathing, safety, my_channel_time())
           && !(memory.claim >= 0 && memory.claim < static_cast<int>(world.camps.size())
                && world.camps[memory.claim].state == CampState::cleared);
}

// Our tribute channel goes on unless it is unsafe and fleeing or fighting back pays. True if the
// turn ends with it; `home` gets want_home's answer if asked.
bool continue_tribute(const World& world, Pathing& pathing, Safety& safety, Memory& memory, std::optional<bool>& home) {
    auto& me = cambc::self();
    decision = Branch::tribute_kept;
    // The enemy's winning tribute, while we hold a hard stop for it (holds_hard_stop) or a ready stun
    // in reach, is the game: ours waits, unless ours wins first or, winning later, an ally stops theirs in time.
    const auto* ender = game_ender(world);
    const auto* stop = ender && holds_hard_stop(world, *ender) ? ender : stoppable_winning_tribute(world);
    if (stop && !(winning_bag(world) && ally_stops(world, *stop))) {
        throw_if_stale();
        try {
            me.cancel_submit_gems();
        } catch (const std::exception&) {
        }
        if (!me.is_submitting_gems()) return false;
    }
    if (tribute_ok(world, safety, memory, my_channel_time())) return true;
    // Damage does not interrupt a tribute: cancelling pays only to flee or to fight back. Sealed in
    // a ring, neither saves the bag from the camps: only the channel's end can.
    if (memory.damage > 0 && sealed_in(world, pathing, my_position())) return true;
    if (memory.damage <= 0 && !*(home = want_home(world, pathing, safety, memory)) && !attack_target(world)
        && (winning_bag(world) || !prey(world, pathing, safety)))
        return true;
    decision = Branch::tribute_cancelled;
    throw_if_stale();
    try {
        me.cancel_submit_gems();
    } catch (const std::exception&) {
        return true;
    }
    return false;
}

// Our recall (start_recall begins one every turn end) is kept to retreat, to bank a bag, to shop,
// to land as a held capture pays, to heal from a siege or to reach farm's choice sooner
// (`recall_farm`, last turn's Memory::recall_farm), else cancelled. True if the turn ends with it;
// `home` gets want_home's answer.
bool continue_recall(World& world, Pathing& pathing, Safety& safety, Memory& memory, std::optional<bool>& home, int recall_farm) {
    auto& me = cambc::self();
    decision = Branch::recall_kept;
    if (const auto* ender = game_ender(world); ender && holds_hard_stop(world, *ender)) {
        throw_if_stale();
        try {
            me.cancel_recall();
        } catch (const std::exception&) {
            return true;
        }
        return false;
    }
    home = want_home(world, pathing, safety, memory);
    // Home by the recall only while it lands sooner than the walk, which no damage cancels.
    if (*home && !walk_beats_recall(world, pathing, safety, my_channel_time()) && !safety.threatened(my_position())
        && !can_tribute_safely(world, pathing, safety, memory) && recall_outruns(safety))
        return true;
    // With no walk home, retreat has nowhere to go: the recall is the way out, and an enemy who
    // reaches us in time cancels it no sooner than it would catch us standing.
    if (*home && !safety.threatened(my_position()) && (!pathing.on_foot(my_position()) || sealed_in(world, pathing, my_position()))
        && !can_tribute_safely(world, pathing, safety, memory))
        return true;
    decision = Branch::recall_cancelled;
    if (holding_capture(world, pathing)) {
        if (capture_recall(world, pathing, safety, memory)) {
            decision = Branch::capture_recall;
            return true;
        }
    } else {
        const auto shop = [&] {
            return wants_shop(world, pathing, safety, memory) && my_channel_time() < pathing.to_ally_spawn().at(my_position());
        };
        // Wanting home, the home keep's reach test binds these too: else we alternate a retreat
        // step with a standing turn on a recall the pursuer cancels.
        if ((!*home || recall_outruns(safety)) && (recall_to_bank(world, pathing, safety, memory) || shop())) return true;
        if (siege_heal_trip(world, pathing, memory, safety)) return sieged = true; // the trip keeps the siege until home
        // No walk leaves a pocket a crystal took us into, unless to bank there or to farm there.
        const bool pocket = !pathing.on_foot(my_position()) ? memory.farm_group < 0 || beyond_walk(world, pathing, memory.farm_group)
                                                            : sealed_in(world, pathing, my_position());
        if (pocket && (my_gems() == 0 || retaining_gems(world, pathing) || !memory.banking)) return true;
        // The pick weighed again, kept while it still goes by way of spawn.
        if (recall_farm >= 0 && my_gems() == 0 && !memory.siege) {
            memory.recall_farm = -1;
            farm_reprice(world, pathing, safety, memory);
            if (memory.recall_farm >= 0) {
                debug_block({ std::printf("RFKEEP %d %u %d %d%s\n", world.round, my_handle(), memory.recall_farm, static_cast<int>(my_channel_time()),
                                          memory.recall_farm != recall_farm ? " switched" : ""); });
                decision = Branch::recall_kept;
                return true;
            }
        } else if (recall_to_farm(world, pathing, safety, memory, recall_farm)) {
            debug_block({ std::printf("RFKEEP %d %u %d %d\n", world.round, my_handle(), recall_farm, static_cast<int>(my_channel_time())); });
            decision = Branch::recall_kept;
            memory.recall_farm = recall_farm;
            return true;
        }
        if (recall_farm >= 0) {
            debug_block({ std::printf("RFDROP %d %u %d %d\n", world.round, my_handle(), recall_farm, static_cast<int>(my_channel_time())); });
        }
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
// capture on the way. A chase keeps `chase_guard`, the step guard (decide).
void carry_bag(World& world, Pathing& pathing, Safety& safety, Memory& memory, bool attacked, const Pathing::GuardState& chase_guard) {
    const bool safe = can_tribute_safely(world, pathing, safety, memory);
    const bool close = closing(world, pathing);
    if (!safe && !close && !winning_bag(world) && chase_with_guard(world, pathing, safety, chase_guard)) return;
    if (safe) {
        decision = Branch::bank;
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
                decision = Branch::wait_altar;
                return;
            }
            memory.avoid_altar = at;
            memory.avoid_until = world.round + other_steps;
            memory.wait_altar = -1;
        }
    }
    decision = Branch::bank;
    const bool walked = attacked && !world.me().facts().walk_and_attack_independent();
    memory.banking = close || walked || !may_chain(world, safety) || !farm(world, pathing, safety, memory);
    if (memory.banking) bank_gems(world, pathing, safety, memory); // a tribute can still start after a ranged attack
}

} // namespace

} // namespace aph
