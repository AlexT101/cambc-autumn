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
    // Only a crystal reaches an altar and we can neither use nor buy one: farm the gold first. A
    // recall out of a pocket to a spawn with a walk to one banks it. Altars' hops come first.
    if (!world.map().hops().empty() && world.map().hops()[0].altar >= 0 && pathing.to_any_altar().at(my_position()) == unreachable && !carries_crystal()
        && !can_buy_crystal() && pathing.to_any_altar().at(recall_landing(world)) == unreachable)
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
        if ((avoided || world.altars[a].enemy_lock || here != world.turn_start)
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
    if (map.hops().empty() || !pathing.on_foot(here)) return best;
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
        }
    }
    const Field& field = best >= 0 ? pathing.to_altar(best) : pathing.to_any_altar();
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
// still to channel while a pack closes in only gets it cancelled. `turns`: the channel left, by
// default ours now.
bool recall_outruns(const World& world, Safety& safety, int turns) {
    const vec2 here = my_position();
    if (turns < 0) turns = static_cast<int>(my_channel_time());
    for (const auto& e : world.enemies)
        if (e.alive && e.age(world.round) <= 1
            && (e.visible ? safety.approach(e, here) : dist(here, e.pos) - safety.strike_of(e).reach) <= turns)
            return false;
    return true;
}

// The recall farm chose to reach group g by (Memory::recall_farm) is kept while, priced as farm
// prices it (FarmRecall::sooner), it still beats the walk, empty-handed and with no enemy to cancel it.
bool recall_to_farm(const World& world, Pathing& pathing, Safety& safety, const Memory& memory, int g) {
    if (g < 0 || g != memory.farm_group || g >= static_cast<int>(world.camps.size()) || my_gems() > 0 || memory.siege) return false;
    const vec2 here = my_position();
    if (safety.threatened(here) || !recall_outruns(world, safety)) {
        debug_block({ std::printf("RFWHY %d %u threat %d\n", world.round, my_handle(), static_cast<int>(safety.threatened(here))); });
        return false;
    }
    const auto* centre = pathing.centre_field(g);
    if (!centre) return false;
    const auto& c = world.camps[g];
    const int respawn = c.state == CampState::respawning ? std::max(0, c.respawn_round - world.round) : 0;
    const auto r = farm_recall(world, pathing, static_cast<int>(my_channel_time()));
    const bool kept = r.sooner(pathing.centre_to_spawn(g), respawn, centre->at(here)) < static_cast<float>(unreachable);
    if (!kept) {
        debug_block({ std::printf("RFWHY %d %u walk %d out %d respawn %d channel %d hurt %d value %.1f\n", world.round, my_handle(),
                                  centre->at(here), pathing.centre_to_spawn(g), respawn, r.channel, r.hurt, r.value); });
    }
    return kept;
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
    decision = Branch::tribute_kept;
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
bool continue_recall(const World& world, Pathing& pathing, Safety& safety, Memory& memory, std::optional<bool>& home, int recall_farm) {
    auto& me = cambc::self();
    decision = Branch::recall_kept;
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
    // Home by the recall only while it lands sooner than the walk, which no damage cancels.
    if (*home && my_channel_time() < pathing.to_ally_spawn().at(my_position()) && !safety.threatened(my_position())
        && !can_tribute_safely(world, pathing, safety, memory) && recall_outruns(world, safety))
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
        if ((!*home || recall_outruns(world, safety)) && (recall_to_bank(world, pathing, safety, memory) || shop())) return true;
        if (siege_heal_trip(world, memory, safety)) return sieged = true; // the trip keeps the siege until home
        // No walk leaves a pocket a crystal took us into, unless to bank there or to farm there.
        if (!pathing.on_foot(my_position()) && (memory.farm_group < 0 || beyond_walk(world, pathing, memory.farm_group))
            && (my_gems() == 0 || retaining_gems(world, pathing) || !memory.banking))
            return true;
        if (recall_to_farm(world, pathing, safety, memory, recall_farm)) {
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
    if (!safe && !close && !winning_bag(world)) {
        const auto work_guard = pathing.held_guard();
        pathing.restore_guard(chase_guard);
        if (chase(world, pathing, safety)) return;
        strike_guard_known(pathing, my_position());
        pathing.restore_guard(work_guard);
    }
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
