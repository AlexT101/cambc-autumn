// The farm loop: which group to work next, and the walk and hits towards it.
#include "../bot_parts.h"

namespace aph {

namespace {

constexpr float stickiness = 1.2f;

// Pathing::attack_tiles once prepared, null if preparing could take the fuel below `floor()`.
// Member tiles are static once prepared, so the union is kept while the same members live.
template <class Floor>
[[gnu::noinline]] const bitboard* farm_attack_tiles(const World& world, Pathing& pathing, int group, int range, Floor floor) {
    static struct {
        int group = -1, range = -1;
        std::array<std::uint64_t, 4> alive{};
        bitboard tiles;
    } kept;
    const auto& health = world.camps[group].health;
    const bool keeps = health.size() <= 64 * kept.alive.size();
    std::array<std::uint64_t, 4> alive{};
    for (std::size_t i = 0; i < health.size() && keeps; ++i)
        if (health[i] > 0) alive[i >> 6] |= std::uint64_t{1} << (i & 63);
    if (keeps && kept.group == group && kept.range == range && kept.alive == alive) return &kept.tiles;
    if (!pathing.prepare_attack_tiles(group, range, floor())) return nullptr;
    pathing.attack_tiles(group, range, kept.tiles);
    kept.group = keeps ? group : -1, kept.range = range, kept.alive = alive;
    return &kept.tiles;
}

// After our attack killed a group's last monster, walk onto a free camp tile of it within a step,
// unless allies in sight already hold it (holders: more would only split the gems).
bool step_onto_cleared(const World& world, Pathing& pathing, int g) {
    if (!my_can_move()) return false;
    const auto& G = world.map().groups[g];
    for (std::size_t i = 0; i < G.members.size(); ++i) {
        try {
            if (G.camp(static_cast<int>(i)).is_alive()) return false;
        } catch (const cambc::error&) {
            return false;
        }
    }
    if (prism_capture_holder(world, G) || allies_on(world, G.tiles()) >= holders(G)) return false;
    const vec2 here = my_position();
    for (const auto d : directions)
        if (in_bounds(here + d) && test(G.tiles(), here + d) && pathing.try_move(here + d)) return true;
    return false;
}

// The approach to a farm choice: onto its tiles once cleared, else into attack range.
int walk_range(const World& world, int g) {
    return g >= 0 && g < static_cast<int>(world.camps.size()) && world.camps[g].state != CampState::cleared
               ? world.me().facts().attack_range()
               : 0;
}

// No walk of ours from here reaches the group: only a recall out of our pocket or the crystal's hop
// into its region (StaticMap::group_hop) do.
bool beyond_walk(const World& world, Pathing& pathing, int g) {
    const auto& map = world.map();
    const vec2 here = my_position();
    const int h = map.group_hop(g);
    if (h >= 0 && test(map.hops()[h].pocket, here)) return false;
    if (!test(pathing.foot(), here)) return true;
    if (!map.any_group_hop()) return false;
    static std::vector<signed char> on_foot; // by group, -1 until read: our static walls never change
    if (on_foot.size() != map.groups.size()) on_foot.assign(map.groups.size(), -1);
    if (on_foot[g] < 0) {
        static bitboard both{cambc::uninitialized};
        and_into(map.groups[g].tiles(), pathing.foot(), both);
        on_foot[g] = !board_empty(both);
    }
    return !on_foot[g];
}

// Farm's spell clear (spell_clear_rounds): from a tile within ability range of a live attacker of
// the group but out of every attacker's reach, casting at the attackers, with basic attacks on
// what cannot hit back. False with no such tile or way to one, for the usual approach.
bool spell_clear(const World& world, Pathing& pathing, int g, const bitboard* zone, int cap) {
    const auto& G = world.map().groups[g];
    const auto& c = world.camps[g];
    static bitboard reach{cambc::uninitialized}, goals{cambc::uninitialized};
    reach.clear();
    // Targets only among the first 32 members (the mask's width), but every member's reach is avoided.
    std::uint32_t attackers = 0;
    for (std::size_t i = 0; i < G.members.size(); ++i)
        if (c.health[i] > 0 && G.members[i].strength > 0) {
            if (i < 32) attackers |= 1u << i;
            reach.draw_chebyshev(G.members[i].pos, static_cast<float>(G.members[i].reach));
        }
    if (!attackers) return false;
    if (!pathing.prepare_member_tiles(g, ability_range, attackers, end_reserve)) {
        note_shortcut("spell-clear-no-tiles");
        return false;
    }
    goals.clear();
    for (std::size_t i = 0; i < G.members.size() && i < 32; ++i)
        if (attackers >> i & 1) goals |= pathing.member_attack_tiles(g, static_cast<int>(i), ability_range);
    drop(goals, reach);
    if (zone) drop(goals, *zone);
    if (goals.is_empty()) return false;
    const auto hit = [&]() __attribute__((always_inline)) {
        cast_at_camp(world, g, true);
        attack_camp(world, [&](int h) { return h == g || world.map().groups[h].strength <= 0; });
        reset_and_attack_camp(world, g);
    };
    if (test(goals, my_position())) {
        hit();
        return true;
    }
    if (zone) reach |= *zone;
    if (!pathing.step_towards(goals, &reach, cap, G.centre)) return false;
    if (!test(reach, my_position())) hit();
    return true;
}

// Our spawn tiles' bounding box, read once.
std::pair<vec2, vec2> ally_spawn_box(const StaticMap& map) {
    static std::optional<std::pair<vec2, vec2>> box;
    if (!box) {
        vec2 lo{map.width, map.height}, hi{-1, -1};
        for (const auto p : map.ally_spawn_tiles) {
            lo.x = std::min(lo.x, p.x), lo.y = std::min(lo.y, p.y);
            hi.x = std::max(hi.x, p.x), hi.y = std::max(hi.y, p.y);
        }
        box.emplace(lo, hi);
    }
    return *box;
}

// Chebyshev steps from p to the group's nearest camp tile.
int steps_to(const CampGroup& G, vec2 p) {
    int steps = unreachable;
    for (const auto& m : G.members) steps = std::min(steps, dist(p, m.pos));
    return steps;
}

// Our farm choice or claim, cleared this turn and short of holders, goes to the nearest of the
// allies in sight claiming it (ties to the lower index), so the others move on rather than split
// the share. Before anything else farm does, since a ranged hit in passing would cost the step.
bool pick_up(const World& world, Pathing& pathing, Memory& memory) {
    if (!my_can_move() || memory.banking) return false;
    const auto& map = world.map();
    const vec2 here = my_position();
    for (const int g : {memory.farm_group, memory.claim}) {
        if (g < 0 || g >= static_cast<int>(map.groups.size())) continue;
        const auto& G = map.groups[g];
        const auto& c = world.camps[g];
        if (c.state != CampState::cleared || c.state_round != world.round || G.has_monolith || G.gems + G.gold == 0
            || test(G.tiles(), here) || prism_capture_holder(world, G) || allies_on(world, G.tiles()) >= holders(G) || enemy_on(world, G.tiles()))
            continue;
        const int steps = steps_to(G, here);
        if (steps > 4) continue;
        bool ours = true;
        for (const auto& a : world.allies) {
            if (a.is_self || !a.alive || !a.visible || comms::claim_of(world, a.index) != g) continue;
            const int d = steps_to(G, a.pos);
            ours &= d > steps || (d == steps && a.index > world.me().index);
        }
        if (!ours) continue;
        memory.farm_group = memory.claim = g;
        memory.crew = false;
        return pathing.step_towards(G.tiles(), nullptr, steps + max_detour);
    }
    return false;
}

// For farm's prunes: a group that cannot beat `best` (nor, with `from_altar` at least 0, the best
// cycle from the altar after `walk`) at `trip` rounds. The value is rated, falling with the
// rounds, and no clear is quicker than the `fastest` (for Ren, reflected_clear). A clear shared
// with an unclaimed `partner` is quicker but pays only our part.
bool rated_beaten(const World& world, float worth, float trip, float fastest, float strength, float partner, float best, float from_altar,
                  int walk, float cycle_bank) {
    const float cap = static_cast<float>(capture_rounds(world));
    float bound = rate(world, worth, trip + cap + fastest);
    if (partner > 0) {
        const float part = strength / (strength + partner);
        bound = std::max(bound, rate(world, worth * part, trip + cap + fastest * part));
    }
    // The slack covers float rounding where a clear takes exactly the fastest.
    return bound * 1.0001f < best
           && (from_altar < 0 || rate(world, worth, static_cast<float>(walk) + cap + cycle_bank + fastest) * 1.0001f < from_altar);
}

// A live group farm would only call risky (it costs more health than we spare): no spell clear
// kites it (an attacker reaches as far as our spells, or we have none), and each attacker strikes
// at least until its own kill, alone or with the unclaimed partner. Ren's attackers take its
// `reflect` too, so each lives at least its health over our hit and that, shaved as in
// reflected_clear. An ally on its threat tiles makes it ours to help, which is left to farm (the
// caller asks ally_engaged).
bool beyond_spare(const World& world, int g, float strength, float reflect, float soften, float spare, float partner, float spells,
                  float shield) {
    const auto& members = world.map().groups[g].members;
    const auto& belief = world.camps[g];
    if (belief.state != CampState::alive) return false;
    bool kites = spells > 0, attacker = false;
    float alone = 0, shared = 0, rounds = 0;
    for (std::size_t i = 0; i < members.size(); ++i) {
        const float hp = belief.health[i];
        // A shield's income needs the clear's rounds, which min_camp_damage sums exactly so (Ren has no shield).
        if (shield > 0 && hp > 0) rounds += std::ceil(hp / strength);
        if (hp <= 0 || members[i].strength <= 0) continue;
        attacker = true;
        kites = kites && members[i].reach < ability_range;
        alone += members[i].strength * (reflect > 0 ? std::ceil(0.999f * hp / (strength + reflect)) - 1 : std::ceil(hp / strength) - 1);
        if (partner > 0) shared += members[i].strength * (std::ceil(hp / (strength + partner)) - 1);
    }
    // The slack covers the sums' float rounding.
    const float limit = spare * 1.0001f;
    return attacker && !kites && shielded_clear(soften * alone, rounds, shield) > limit && (partner <= 0 || soften * shared * (strength / (strength + partner)) > limit);
}

// Static per group once read: its centre field (once warm) and that field's steps to our
// spawn, its home_ground weight, its centre_to_altar steps, its own tribute and each holder's
// gold (`tribute` 0 until read, read again when our Tribute or Prospector emblem changes them).
// Then its reward and the walks to bank it, kept while `context` holds (the gold's worth while
// `gold_context` also does), and its fastest clear while its belief holds.
struct GroupFacts {
    const Field* centre = nullptr;
    int to_spawn = -1;
    float home = -1;
    int to_altar = -1;
    std::uint32_t context = 0, gold_context = 0, version = ~0u;
    bool sticky = false;
    std::uint8_t emblems = 0; // `emblems` when `tribute` and `gold_in` were read
    int walk = 0, chained_tribute = 0, tribute = 0;
    std::uint32_t gold_in = 0;
    float weight = 0, gems = 0, gold = 0, fastest = 0, fastest_strength = 0, walked_bank = 0, walked_cycle = 0;
    // Clearing it alone, kept while `clearing` and its belief hold.
    std::uint32_t clearing = 0, clear_version = ~0u;
    float damage = 0, rounds = 0, kite = -1;
};
struct FarmContext {
    int bag, short_by;
    bool banking;
    std::uint8_t emblems;
    bool operator==(const FarmContext&) const = default;
};
struct FarmClearing {
    float strength, reflect, spells, basic;
    int range;
    bool operator==(const FarmClearing&) const = default;
};
// farm's kept readings, one set for both of its versions.
struct FarmMemo {
    std::vector<int> centre_steps; // by group, -1 until read
    vec2 steps_from{-1, -1};
    std::array<GroupFacts, 256> few_facts;
    std::vector<GroupFacts> many_facts;
    FarmContext last_context{};
    std::uint32_t context = 0;
    float last_per_gold = 0, last_tribute_gold = 0;
    std::uint32_t gold_context = 0;
    FarmClearing last_clearing{};
    std::uint32_t clearing = 0;
    // By group: from each position of its nearest_groups order on, the most any group there holds.
    struct Most {
        int gems, gems_prospected, gold, gold_prospected;
        int near; // the position's own distance from the group's centre
    };
    std::vector<std::vector<Most>> most_from;
    // By group, for later turns' rated bound: gems and gold with a Prospector emblem's extra if
    // `worth_prospector`.
    std::vector<int> worth_gems;
    std::vector<float> worth_gold;
    bool worth_prospector = false;
};
FarmMemo& farm_memo() {
    static FarmMemo memo;
    return memo;
}

// Carrying gems, farming on chains a capture onto the bag: it saves the walk to the altar and
// back but keeps the bag at risk for longer. It goes ahead only if the next group, by the time it
// adds to the trip, beats the best cycle starting from the altar; false means bank instead.
// The first turn has its own instance: its extra prunes would make every later call dearer.
template <bool opening> [[gnu::flatten]] bool farm_turn(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    world.throw_if_stale();
    auto& memo = farm_memo();
    if (pick_up(world, pathing, memory)) return true;
    const auto& map = world.map();
    const auto& groups = map.groups;
    const int range = world.me().facts().attack_range();
    const float strength = camp_output(world.me()), soften = camp_hit_factor(), reflect = world.me().retaliation();
    const float max_health = my_max_health();
    const float spare_health = (my_health() - params::recall_health_fraction * max_health) / params::camp_risk;
    const float shield = self_shield_amount(world.me());
    const int bag = bankable_bag(world, pathing);
    const bool banks_bag = bag > 0 && !retaining_gems(world, pathing);
    const int short_by = gems_short(world);
    if (world.is_stale()) return true;
    // Groups in passing pay too (gold clusters are never chosen below), but not one whose clear
    // costs more health than we can spare.
    const auto affordable = [&](int g) __attribute__((always_inline)) {
        if (g == memory.farm_group || groups[g].strength <= 0) return true;
        float rounds = 0;
        return shielded_clear(soften * min_camp_damage(world, g, strength, &rounds, reflect), rounds, shield) <= spare_health
               || ally_engaged(world, g);
    };
    std::array<std::uint64_t, 4> ally_claims{}; // bit g: comms carries groups below 255
    for (const auto& a : world.allies)
        if (const int c = comms::claim_of(world, a.index); !a.is_self && c >= 0 && c < 256) ally_claims[c >> 6] |= std::uint64_t{1} << (c & 63);
    const auto claimed_by_ally = [&](int g) __attribute__((always_inline)) {
        return g < 256 && (ally_claims[g >> 6] >> (g & 63) & 1);
    };
    // An ally's claim makes us its crew rather than its rival, unless we claimed it first.
    const auto taken = [&](int g) __attribute__((always_inline)) {
        return claimed_by_ally(g) && (memory.claim != g || memory.crew);
    };
    const bool melee = world.me().facts().walk_and_attack_independent();
    // Cassi farms gold: the team's weakest body takes the harmless gold-only groups. With three
    // picks, so does Tavi on maps of pure-gold groups.
    const bool gold_farmer = (world.me().facts().passive == Passive::linked_pair && !melee)
                             || (economy_three(world) && world.me().facts().passive == Passive::remote_shop && map_economy(map).tavi_map());
    // A ranged hit in passing costs the walk: only for our choice, or gems no ally will clear. A
    // group that hits back and that we will not finish is only woken by it: hit one only while an
    // ally clears it or, melee, once every striker is awake anyway.
    const auto passing = [&](int g) __attribute__((always_inline)) {
        if (!affordable(g)) return false;
        if (g == memory.farm_group) return true;
        if (taken(g)) return false;
        if (groups[g].strength > 0) return ally_engaged(world, g) || (melee && world.camps[g].fully_awake());
        return melee || groups[g].gems > 0 || gold_farmer;
    };
    // Rather than wake a sleeping striker group with a ranged hit that kills nothing, finish a
    // harmless resource group already damaged and wholly in range: its index in `resources`, or -1.
    // Called only for an ordinary farming turn's hit.
    const auto prefer_partial = [&](const CampAttackTargets& ordinary, const CampAttackTargets& resources) {
        if (ordinary.n == 0 || resources.n == 0 || holding_capture(world, pathing)) return -1;
        const auto& alternative = ordinary.found[0];
        const int g = alternative.group;
        const auto& G = groups[g];
        const auto& c = world.camps[g];
        if (G.has_monolith || G.members[alternative.member].strength <= 0 || c.state != CampState::alive) return -1;
        const vec2 here = my_position();
        bool striker = false;
        for (int i = 0; i < static_cast<int>(G.members.size()); ++i) {
            if (G.members[i].strength <= 0) continue;
            if (!test(world.visible, G.members[i].pos) || c.health_round[i] != world.round || !(c.health[i] >= 0)) return -1;
            if (c.health[i] <= 0) continue;
            striker = true;
            if (!c.member_asleep(i)) return -1;
        }
        if (!striker) return -1;
        const auto live = my_record();
        const float basic = live.strength * damage_scale(world.me().facts().passive, live.health, live.max_health)
                            * camp_dealt_factor();
        if (!(basic > 0) || !(c.health[alternative.member] > basic)) return -1;
        std::array<int, 16> checked;
        int n_checked = 0;
        for (int k = 0; k < resources.n; ++k) {
            const int h = resources.found[k].group;
            if (std::find(checked.begin(), checked.begin() + n_checked, h) != checked.begin() + n_checked) continue;
            checked[n_checked++] = h;
            const auto& H = groups[h];
            const auto& known = world.camps[h];
            // Strength is the members' sum, so none of them strikes.
            if (h == g || H.has_monolith || H.strength > 0 || H.gems + H.gold <= 0 || known.state != CampState::alive) continue;
            // An ally's claim wins even over our own.
            if (claimed_by_ally(h) || prism_capture_holder(world, H) || allies_on(world, H.tiles()) >= holders(H)) continue;
            bool partial = false, alive = false, fresh = true, in_range = true;
            for (int i = 0; i < static_cast<int>(H.members.size()); ++i) {
                const auto& m = H.members[i];
                fresh &= test(world.visible, m.pos) && known.health_round[i] == world.round && known.health[i] >= 0;
                partial |= known.health[i] < m.max_health;
                if (known.health[i] <= 0) continue;
                alive = true;
                in_range &= dist(here, m.pos) <= range;
            }
            if (fresh && alive && partial && in_range) return k;
        }
        return -1;
    };
    const auto attack_in_range = [&]() __attribute__((always_inline)) {
        CampAttackTargets resources;
        const bool ordinary = !melee && decision == 'F' && !memory.banking && !memory.siege && siege_group() < 0;
        const auto targets = camp_attack_targets(world, passing, ordinary ? &resources : nullptr);
        int hit = -1;
        if (ordinary) {
            const int preferred = prefer_partial(targets, resources);
            if (preferred >= 0 && attack_camp_target(world, resources.found[preferred])) {
                hit = memory.farm_group = memory.claim = resources.found[preferred].group;
                memory.crew = false;
            }
        }
        if (hit < 0) hit = attack_camp_targets(world, targets);
        if (hit >= 0 && hit != memory.claim) {
            memory.crew = taken(hit);
            memory.claim = hit;
        }
        // Our hit cleared the group: a melee walk onto its tile starts the capture a round sooner.
        if (hit >= 0 && melee && step_onto_cleared(world, pathing, hit)) {
            memory.farm_group = hit;
            return true;
        }
        if (hit < 0 || melee) return false; // walk on
        cast_at_camp(world, hit);
        reset_and_attack_camp(world, hit);
        return true;
    };
    if (!banks_bag && attack_in_range()) return true;
    if (world.is_stale()) return true;

    // Holders keep a capture going, and more only split the reward.
    const auto ally_holding = [&](int g) __attribute__((always_inline)) {
        return prism_capture_holder(world, groups[g]) || allies_on(world, groups[g].tiles()) >= holders(groups[g]);
    };

    const vec2 here = my_position();
    if (holding_capture(world, pathing)) return true;
    // Carrying, whatever made us retreat stays out of bounds: we route around it or wait outside
    // it rather than step in to be sent back out. Empty-handed, a step in risks nothing (the zone
    // starts beyond any strike's reach) and keeps us at hand for when the pack moves on.
    const auto* zone = bag_at_stake(world) > 0 ? pack_zone(world) : nullptr;

    // Beyond our walk: from a pocket the turn-end recall takes us home (continue_recall); from our
    // walk, the crystal's hop, by way of our spawn to buy one.
    const bool in_pocket = map.any_group_hop() && !test(pathing.foot(), here);
    const auto cross = [&](int g) {
        const int h = map.group_hop(g);
        if (in_pocket || h < 0) return false;
        memory.wants_crystal = true;
        if (!carries_crystal() && test(map.ally_spawn, here)) buy_crystal(memory);
        // No safe start or landing: the hop is set aside for a while rather than stood on.
        if (carries_crystal() && !take_hop(world, pathing, safety, memory, h, &pathing.to_group(g)))
            memory.hop_refused = h, memory.hop_refused_until = world.round + 2 * ability_cooldown;
        else if (!carries_crystal()) step_safely(world, pathing, pathing.to_ally_spawn(), safety);
        return true;
    };
    // Short of fuel, walk on towards the last choice rather than run out mid-turn. Static fields
    // are kept, so after the first walk to a group this costs a descent.
    const int previous = memory.farm_group;
    const auto walk_on = [&](int g) __attribute__((always_inline)) {
        if (g < 0) return false;
        if (map.any_group_hop() && beyond_walk(world, pathing, g)) return cross(g);
        // Descending it walks around walls and live camps; a live route only helps past allies.
        const auto walk = [&](const Field& field, int target) __attribute__((always_inline)) {
            return dash_across(world, pathing, field) || pathing.descend(field, zone, groups[target].centre)
                   || pathing.step_towards(field, zone, groups[target].centre);
        };
        if (const auto* field = pathing.prepare_approach(g, walk_range(world, g), end_reserve)) return walk(*field, g);
        const bool skipped = pathing.approach_skipped();
        // Too short of fuel to search the way to a new choice: last turn's, whose way is known.
        if (previous >= 0 && previous != g && pathing.approach_ready(previous, walk_range(world, previous))) {
            note_shortcut("farm-kept-target");
            memory.farm_group = memory.claim = previous;
            memory.crew = false;
            return walk(*pathing.approach(previous, walk_range(world, previous)), previous);
        }
        // No way round the live camps within the search's cap: down the static walls.
        if (const auto* centre = skipped ? nullptr : pathing.centre_field(g)) return pathing.descend(*centre, zone, groups[g].centre);
        note_shortcut("crow-flies-farm");
        return pathing.step_closer(groups[g].centre, zone, groups[g].centre);
    };
    // The walk comes before choosing better: fuel for its search is kept back from the evaluation.
    const auto walk_reserve = [&](int g) __attribute__((always_inline)) { return g < 0 ? std::uint64_t{0} : pathing.approach_cost(g, walk_range(world, g)); };
    // Centre fields give the steps a field from here would, without its cost. Walls are static, so
    // the steps are kept while we stand still, as when attacking a camp.
    auto& centre_steps = memo.centre_steps;
    auto& steps_from = memo.steps_from;
    if (here != steps_from) {
        steps_from = here;
        centre_steps.assign(groups.size(), -1);
    }
    std::optional<Field> from_here;
    const Field* to_altar = banks_bag ? &pathing.to_any_altar() : nullptr;
    const int left = bag_rounds_left(world);
    // A bag rides a recall home when that reaches an altar sooner (recall_to_bank). Started during
    // a capture, the recall lands as it pays (capture_recall). Once a group's gems make the bag
    // win, the stop on spawn is worth nothing.
    std::optional<HomeTrip> trip_home, winning_trip;
    if (to_altar) {
        trip_home = winning_trip = home_trip(world, pathing, recall_turns(world), winning_bag(world));
        winning_trip->heal = winning_trip->emblem = 0;
    }
    const float bank_now = to_altar && to_altar->at(here) != unreachable ? trip_home->rounds(to_altar->at(here), 0, 0) : 0.0f;
    float from_altar_value = 0;
    // Unaffordable groups, then allies' claims, only when nothing else is left: idling is worse.
    int best = -1, best_steps = unreachable, risky = -1, risky_steps = unreachable, shared = -1, shared_steps = unreachable;
    bool best_spell = false;
    float best_value = 0, risky_value = 0, shared_value = 0;
    // Per base gold of a group: we are paid it with our bonuses.
    const float paid = gold_paid(world);
    const float per_gold = prices(world).per_gold * paid * (gold_farmer ? params::gold_farmer_weight : 1.0f);
    // An ally in sight clearing its claimed damaging group gets help only if finishing it alone
    // would take it below the recall line: one champion per camp otherwise.
    const auto struggling = [&](int g) __attribute__((always_inline)) {
        if (!claimed_by_ally(g)) return false;
        for (const auto& a : world.allies) {
            if (a.is_self || !a.alive || !a.visible || comms::claim_of(world, a.index) != g || !test(groups[g].threat(), a.pos))
                continue;
            float rounds = 0;
            const float damage = min_camp_damage(world, g, camp_output(a), &rounds, a.retaliation(), a.facts().attack_range());
            if (a.health - damage < params::recall_health_fraction * a.max_health) return true;
        }
        return false;
    };
    // Joining allies on a group, our part of its gems is our share of the damage still to deal
    // when we arrive, and of the camps' hits.
    struct CrewWork {
        float output = 0, delayed_damage = 0;
    };
    const vec2 spawn_lo = ally_spawn_box(map).first, spawn_hi = ally_spawn_box(map).second;
    struct WorkArrival {
        int anchor_round = -1, member = -1, reach = 0, distance = unreachable, spawn_distance = unreachable;
        int dash_ready = 0, direct = 0, recall_delay = 0, recall_route = unreachable, earliest = 0;
        int delay(int round, int waiting = 0) const {
            return anchor_round < 0 ? 0 : std::max(0, anchor_round + earliest - round - waiting);
        }
    };
    const auto work_arrival = [&](const ChampionBelief& a, int g) __attribute__((always_inline)) {
        WorkArrival arrival;
        const bool seen_anchor = !a.visible && a.pos_source == Source::seen && a.pos_round == a.stats_round
                                 && a.stats_round > 0 && in_bounds(a.pos) && a.seen_channel != Channel::teleport;
        if ((!a.visible && !seen_anchor) || a.channel == Channel::teleport) return arrival;
        const auto& group = groups[g];
        const auto& belief = world.camps[g];
        arrival.anchor_round = a.visible ? world.round : a.stats_round;
        const auto& f = a.facts();
        arrival.reach = f.basic_reach();
        // Readiness and walking exclusions can only delay this earliest effect.
        for (const auto& ability : f.abilities)
            if (ability.kind == AbilityKind::damage) arrival.reach = std::max(arrival.reach, ability.reach());
            else if (ability.lands()) arrival.reach = std::max(arrival.reach, ability.radius);
        for (int i = 0; i < static_cast<int>(group.members.size()); ++i) {
            if (belief.state == CampState::alive && belief.health[i] <= 0) continue;
            const auto p = group.members[i].pos;
            if (const int d = dist(a.pos, p); d < arrival.distance) arrival.distance = d, arrival.member = i;
            if (!map.ally_spawn_tiles.empty()) {
                const int dx = std::max({spawn_lo.x - p.x, 0, p.x - spawn_hi.x});
                const int dy = std::max({spawn_lo.y - p.y, 0, p.y - spawn_hi.y});
                arrival.spawn_distance = std::min(arrival.spawn_distance, std::max(dx, dy));
            }
        }
        if (arrival.member < 0) return WorkArrival{};
        const int dash = f.slot_of(AbilityKind::dash);
        const int dash_steps = dash >= 0 ? f.abilities[dash].range() : 0;
        arrival.dash_ready = dash >= 0 ? a.ready_round[dash] - arrival.anchor_round : 0;
        const int first_turn = a.acted ? 1 : 0;
        const bool kill_resets = a.cooldowns_uncertain();
        arrival.direct = earliest_work_delay(arrival.distance - arrival.reach, first_turn, arrival.dash_ready, dash_steps,
                                            ability_cooldown, kill_resets);
        // Allies' Home ownership is unknown: allow the fastest new recall and a ready dash on arrival.
        arrival.recall_delay = a.seen_channel == Channel::recall ? std::max(0, a.channel_end_round - arrival.anchor_round)
                                                              : first_turn + home_recall_time;
        arrival.recall_route = arrival.spawn_distance == unreachable ? unreachable
                                   : arrival.recall_delay + earliest_work_delay(arrival.spawn_distance - arrival.reach, 0, 0, dash_steps,
                                                                               ability_cooldown, kill_resets);
        arrival.earliest = std::min(arrival.direct, arrival.recall_route);
        return arrival;
    };
    const auto crew_work = [&](int g, int working, int waiting) __attribute__((always_inline)) {
        CrewWork total;
        for (const auto& a : world.allies) {
            if (a.is_self || !a.alive || comms::claim_of(world, a.index) != g) continue;
            const float output = camp_output(a);
            total.output += output;
            const auto arrival = work_arrival(a, g);
            // Age the work round from the observation, never a guessed hidden position or turn order.
            const int delay = arrival.delay(world.round, waiting);
            total.delayed_damage += output * static_cast<float>(std::min(working, delay));
        }
        return total;
    };
    // A group too costly for us alone is still ours to call if an ally in reach with no claim of
    // its own can join: valued, like a crew's, by our share of the work.
    float unclaimed_partner_output = 0;
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && dist(here, a.pos) <= params::partner_radius && comms::claim_of(world, a.index) < 0)
            unclaimed_partner_output = std::max(unclaimed_partner_output, camp_output(a));
    // The allies ally_engaged reads, boxed on first need: a group whose threat radius cannot reach
    // the box has none on its threat tiles. Its members are edge-connected, so the radius is at
    // most their count less one plus the longest reach, which needs no pass over them.
    vec2 ally_lo{1 << 20, 1 << 20}, ally_hi{-(1 << 20), -(1 << 20)};
    bool boxed = false;
    const auto engaged = [&](int g) __attribute__((always_inline)) {
        if (!boxed) {
            boxed = true;
            for (const auto& a : world.allies)
                if (!a.is_self && a.alive && a.visible) {
                    ally_lo.x = std::min(ally_lo.x, a.pos.x), ally_lo.y = std::min(ally_lo.y, a.pos.y);
                    ally_hi.x = std::max(ally_hi.x, a.pos.x), ally_hi.y = std::max(ally_hi.y, a.pos.y);
                }
        }
        const auto& G = groups[g];
        const vec2 c = G.centre;
        const int d = std::max(std::max({ally_lo.x - c.x, c.x - ally_hi.x, 0}), std::max(ally_lo.y - c.y, c.y - ally_hi.y));
        return d < static_cast<int>(G.members.size()) + G.reach && ally_engaged(world, g);
    };
    const int n_groups = static_cast<int>(groups.size());
    auto& few_facts = memo.few_facts;
    auto& many_facts = memo.many_facts;
    if (n_groups > static_cast<int>(few_facts.size()) && static_cast<int>(many_facts.size()) != n_groups) many_facts.assign(n_groups, {});
    GroupFacts* const group_facts = n_groups > static_cast<int>(few_facts.size()) ? many_facts.data() : few_facts.data();
    const bool prospector = world.me().prospector;
    const auto emblems = static_cast<std::uint8_t>(world.me().fast_tribute | prospector << 1);
    auto& last_context = memo.last_context;
    auto& context = memo.context;
    if (const FarmContext now{bag, short_by, banks_bag, emblems}; context == 0 || !(now == last_context))
        last_context = now, ++context;
    // Marcella is paid gold for each gem she tributes, with our gold bonus (probe-marcella-gold).
    const float per_gem = world.me().facts().tribute_gold_per_gem();
    const float tribute_gold = per_gem > 0 ? prices(world).per_gold * paid * per_gem : 0.0f;
    auto& last_per_gold = memo.last_per_gold;
    auto& last_tribute_gold = memo.last_tribute_gold;
    auto& gold_context = memo.gold_context;
    if (gold_context == 0 || per_gold != last_per_gold || tribute_gold != last_tribute_gold)
        last_per_gold = per_gold, last_tribute_gold = tribute_gold, ++gold_context;
    const auto centre_field = [&](int g) __attribute__((always_inline)) {
        auto& known = group_facts[g];
        if (!known.centre) known.centre = pathing.from_centre(g);
        return known.centre;
    };
    // Health lost to camps comes back only on spawn: a recall and the walk back out.
    const auto heal = [&](int g, float damage) __attribute__((always_inline)) {
        // The first turn's walk back from a group is the Chebyshev distance, a bound: no field from spawn yet.
        int out = opening ? dist(map.ally_spawn_centre, groups[g].centre) : group_facts[g].to_spawn;
        if (out < 0) out = group_facts[g].to_spawn = pathing.centre_to_spawn(g);
        return out == unreachable ? 0.0f : heal_rounds(world, damage, static_cast<float>(out));
    };
    const float spells = world.me().facts().ranged ? spell_output(world.me()) : 0.0f, basic = std::max(1.0f, basic_output(world.me()));
    auto& last_clearing = memo.last_clearing;
    auto& clearing = memo.clearing;
    if (const FarmClearing now{strength, reflect, spells, basic, range}; clearing == 0 || !(now == last_clearing))
        last_clearing = now, ++clearing;
    int help_group = -1, help_steps = unreachable;
    // First readings of each group (clears, fields) can cost several times the estimate: stop with
    // enough left for the walk after it, and read last turn's choice first so that a cut-short loop
    // still weighs it. Without one, the nearest group worth farming as the crow flies.
    int first = memory.farm_group >= 0 && memory.farm_group < n_groups ? memory.farm_group : -1;
    if (first < 0) {
        int nearest = unreachable;
        for (int g = 0; g < n_groups; ++g) {
            if (groups[g].has_monolith || groups[g].gems + groups[g].gold == 0) continue;
            const int steps = dist(here, groups[g].centre);
            if (steps < nearest) first = g, nearest = steps;
        }
        if (first < 0) first = 0;
    }
    // After a fight's search, the turn's walk goes on to last turn's choice (a bag is banked): the
    // fight has already taken the turn's work, and the evaluation is done again once it is over.
    const int evaluated = struck && memory.farm_group >= 0 ? 0 : n_groups;
    // Nothing in the loop moves us or changes the fields walk_reserve reads.
    int reserved_for = -2;
    std::uint64_t reserved = 0;
    const auto loop_reserve = [&]() __attribute__((always_inline)) {
        const int g = best >= 0 ? best : memory.farm_group;
        if (g != reserved_for) {
            reserved_for = g;
            reserved = walk_reserve(g);
            if (g >= 0) reserved += search_cost_estimate((g == best ? best_steps : dist(here, groups[g].centre)) + max_detour);
        }
        return reserved;
    };
    // With the costliest approach and route to spare, the reserve need not be read.
    const auto loop_floor = small_cost_estimate + end_reserve, ample = loop_floor + 2 * pathing.max_approach_cost();
    // Nothing in the loop changes memory, the round or the warm-up.
    const int round = world.round, farm_group = memory.farm_group;
    const bool crew_of_choice = memory.claim == farm_group && memory.crew;
    // taken() as a mask.
    auto claimed_bits = ally_claims;
    if (memory.claim >= 0 && memory.claim < 256 && !memory.crew)
        claimed_bits[memory.claim >> 6] &= ~(std::uint64_t{1} << (memory.claim & 63));
    // Draft spawn distances use walking walls; dashers keep the live field's graph unless the plan
    // says the two agree.
    static const bool draft_spawn_graph = !world.me().facts().has_dash() || map.crossable.is_empty() || map.dash_spawn_steps_drafted();
    // The draft's dash steps (a dasher's otherwise from a field from here) take ~150 fuel a group to
    // decode: on a small map the field is cheaper.
    static const int dash_kind = 150 * static_cast<std::uint64_t>(n_groups) < full_field_cost_estimate() ? world.me().facts().dash_kind() : 0;
    const CampGroup* const group_data = groups.data();
    const CampBelief* const camp_data = world.camps.data();
    int* const steps_data = centre_steps.data();
    const int bag_tribute = bag > 0 ? tribute_turns(world, bag) : 0;
    int crystal = -1; // read on first need: 2 carried, 1 to buy, 0 neither
    // Nearest to last turn's choice first: a loop cut short has weighed the likeliest groups, and
    // an early good best prunes the rest sooner. With no choice yet, by index from `first`.
    const auto* order = memory.farm_group == first ? map.nearest_groups(first) : nullptr;
    // The prunes' bounds hold but for Ren, whose reflection clears faster than its output, and in a
    // pocket, whose recall out can beat the Chebyshev distance.
    const bool tight = reflect <= 0 && !in_pocket;
    // The first turn's extra prunes: later loops start from last turn's choice, and the plain
    // bound already skips most groups for less. Ren's take reflected_clear for the fastest; its
    // plain prunes, which its reflection can beat, still decide, so its order stays.
    const bool rated = opening && !in_pocket;
    // The draft's guesses at the first choice (DraftPlan's leads) go first: an early good best
    // prunes the rest. As the prunes skip only groups that cannot reach the best, and ties still go
    // to the earlier group in the usual order, the choice is the usual one.
    static std::vector<std::uint8_t> led;
    int n_lead = 0;
    if (opening && !order && tight && evaluated == n_groups && n_groups <= 256) {
        std::array<int, DraftPlan::leads> lead;
        n_lead = map.drafted_leads(world.me().index, lead);
        if (n_lead > 0) {
            static_assert(DraftPlan::leads == 2);
            if (static_cast<int>(led.size()) != n_groups) led.resize(n_groups);
            std::uint8_t* out = led.data();
            const int l0 = lead[0], l1 = n_lead > 1 ? lead[1] : -1;
            out[0] = static_cast<std::uint8_t>(l0);
            int w = 1;
            if (l1 >= 0) out[w++] = static_cast<std::uint8_t>(l1);
            for (int g = first; g < n_groups; ++g)
                if (g != l0 && g != l1) out[w++] = static_cast<std::uint8_t>(g);
            for (int g = 0; g < first; ++g)
                if (g != l0 && g != l1) out[w++] = static_cast<std::uint8_t>(g);
            order = &led;
        }
    }
    // rated_beaten by the best so far. Callers leave out our last choice, whose clear a partner
    // claiming it may share.
    const auto beaten = [&](float worth, float trip, float fastest, int walk, float cycle_bank) __attribute__((always_inline)) {
        return rated_beaten(world, worth, trip, fastest, strength, unclaimed_partner_output, best_value,
                            banks_bag ? from_altar_value : -1.0f, walk, cycle_bank);
    };
    // rated_beaten before farm reads the group's facts, with its turn constants hoisted: empty-handed
    // and short of the win, no walk to an altar is in the trip and the weight is at most 1. Each rate
    // is tested alone, as the larger of the two fails the test exactly when either does.
    const int capture = capture_rounds(world);
    const float cap_rounds = static_cast<float>(capture);
    const float horizon = cycle_horizon * std::max(1.0f, static_cast<float>(std::max(map.width, map.height)) / 50.0f);
    const float partner_part = unclaimed_partner_output > 0 ? strength / (strength + unclaimed_partner_output) : 0.0f;
    const auto rated_below = [&](float worth, float trip, float fastest) __attribute__((always_inline)) {
        const auto rated = [&](float w, float rounds) __attribute__((always_inline)) {
            rounds = std::max(rounds, 1.0f);
            return w / (rounds * (1.0f + rounds / horizon));
        };
        const float near_trip = trip + cap_rounds;
        // The slack covers float rounding where a clear takes exactly the fastest.
        return rated(worth, near_trip + fastest) * 1.0001f < best_value
               && (unclaimed_partner_output <= 0 || rated(worth * partner_part, near_trip + fastest * partner_part) * 1.0001f < best_value);
    };
    const auto unweighed_beaten = [&](const CampGroup& group, const CampBelief& belief, int g, float trip) __attribute__((always_inline)) {
        const int gems = std::min(group.gems + (prospector ? prospected(group.cluster_gems, 1) : 0), short_by);
        const int gold = group.gold + (prospector ? prospected(group.cluster_gold, 1) : 0);
        const float worth = static_cast<float>(gems) + per_gold * static_cast<float>(gold) + tribute_gold * static_cast<float>(gems);
        // At version 0 every member is alive at full health: the bound needs no pass over them.
        const float fastest = reflect > 0          ? reflected_clear(world, g, strength, reflect)
                              : belief.version == 0 ? group.health / strength
                                                    : fastest_clear(world, g, strength);
        return rated_below(worth, trip, fastest);
    };
    const int* worth_gems = nullptr;
    const float* worth_gold = nullptr;
    if constexpr (!opening) {
        if (static_cast<int>(memo.worth_gems.size()) != n_groups || memo.worth_prospector != prospector) {
            memo.worth_prospector = prospector;
            memo.worth_gems.resize(n_groups), memo.worth_gold.resize(n_groups);
            for (int g = 0; g < n_groups; ++g) {
                const auto& G = groups[g];
                memo.worth_gems[g] = G.gems + (prospector ? prospected(G.cluster_gems, 1) : 0);
                memo.worth_gold[g] = static_cast<float>(G.gold + (prospector ? prospected(G.cluster_gold, 1) : 0));
            }
        }
        worth_gems = memo.worth_gems.data(), worth_gold = memo.worth_gold.data();
    }
    // The wait for a group respawning when we would arrive, and whether it may be the group we
    // help (no bound covers that) for a walk of at least `near`.
    const auto near_wait = [&](const CampBelief& belief, int near) __attribute__((always_inline)) {
        return belief.state == CampState::respawning ? std::max(0, belief.respawn_round - round - near) : 0;
    };
    const auto may_help = [&](const CampGroup& group, const CampBelief& belief, int near) __attribute__((always_inline)) {
        return !banks_bag && group.strength > 0 && belief.state == CampState::alive && near <= params::help_radius
               && (near < help_steps || (n_lead > 0 && near == help_steps));
    };
    // With leads first, ties still go to the group earlier in the usual order.
    const auto earlier = [&](int g, int than) __attribute__((always_inline)) {
        return n_lead > 0 && than >= 0 && (g - first + n_groups) % n_groups < (than - first + n_groups) % n_groups;
    };
    const auto is_claimed = [&](int g) __attribute__((always_inline)) { return g < 256 && (claimed_bits[g >> 6] >> (g & 63) & 1); };
    // Nearest to `first` first, every group from position k on is at least r_k - D from here (r_k
    // from first's centre, D ours to it) and walks no fewer steps. Once the most any of them holds,
    // that close and cleared at once, cannot beat the best (only rising), none of them can change
    // the choice: weight is at most 1 off our last choice, and with no bag to bank the trip is at
    // least the steps. Past help_radius none is helped. Still weighed: a crew's share (no capture
    // in its cycle) and crystal hops (shorter than the crow flies).
    const bool hop_any = map.any_group_hop(); // group_hop(g) >= 0 only then
    const bool can_bound = !opening && order && !banks_bag && !in_pocket;
    const bool hops = can_bound && hop_any;
    const int offset = dist(here, groups[first].centre);
    const float most_tribute = std::max(0.0f, tribute_gold), most_per_gold = std::max(0.0f, per_gold);
    const FarmMemo::Most* most = nullptr;
    const auto beyond = [&](int j) __attribute__((always_inline)) {
        const auto& m = most[j];
        const int near = m.near - offset;
        if (near <= params::help_radius) return false;
        const int gems = std::max(0, std::min(prospector ? m.gems_prospected : m.gems, short_by));
        const float worth = static_cast<float>(gems) * (1.0f + most_tribute)
                            + most_per_gold * static_cast<float>(prospector ? m.gold_prospected : m.gold);
        return rate(world, worth, static_cast<float>(near + capture)) * 1.0001f < best_value;
    };
    // The first position the bound covers. It holds from there on (r_k rises, the most held falls),
    // so it is searched for, and again only when the best rises.
    int stop = n_groups;
    float tested_value = 0;
    const auto stop_from = [&](int k) {
        if (!most) {
            auto& most_from = memo.most_from;
            if (static_cast<int>(most_from.size()) != n_groups) most_from.assign(n_groups, {});
            auto& from_first = most_from[first];
            if (from_first.empty()) {
                from_first.resize(n_groups);
                const vec2 origin = groups[first].centre;
                FarmMemo::Most run{0, 0, 0, 0, 0};
                for (int j = n_groups - 1; j >= 0; --j) {
                    const auto& G = groups[(*order)[j]];
                    run.gems = std::max(run.gems, G.gems), run.gold = std::max(run.gold, G.gold);
                    run.gems_prospected = std::max(run.gems_prospected, G.gems + prospected(G.cluster_gems, 1));
                    run.gold_prospected = std::max(run.gold_prospected, G.gold + prospected(G.cluster_gold, 1));
                    run.near = dist(origin, G.centre);
                    from_first[j] = run;
                }
            }
            most = from_first.data();
        }
        int lo = k, hi = stop;
        while (lo < hi)
            if (const int mid = (lo + hi) / 2; beyond(mid)) hi = mid;
            else lo = mid + 1;
        return lo;
    };
    // Fuel rises within a turn only when the engine resumed it, a round late: a stale tail leaves
    // at once instead of weighing groups on the next round's budget.
    std::uint64_t seen = ~std::uint64_t{0};
    const auto room = [&]() __attribute__((always_inline)) {
        const std::uint64_t left = fuel();
        if (left > seen) world.throw_if_stale();
        seen = left;
        return left >= ample || left >= loop_floor + loop_reserve();
    };
    int k = 0;
    for (; k < evaluated && room(); ++k) {
        int g = order ? (*order)[k] : (first + k) % n_groups;
        // best_value moves only with best, from 0.
        if (can_bound && best_value != tested_value) tested_value = best_value, stop = stop_from(k);
        if (k >= stop) {
            while (k < evaluated && !is_claimed(g = (*order)[k]) && !(hops && map.may_hop(g))) ++k;
            if (k == evaluated) break;
        }
        const auto& group = group_data[g];
        const auto& belief = camp_data[g];
        if (group.has_monolith || group.gems + group.gold == 0 || (belief.state == CampState::cleared && ally_holding(g)))
            continue;
        const bool claimed = is_claimed(g);
        // Carrying, compare whole trips: the gems score only after the walk to an altar and the
        // tribute. Empty-handed, only a capture that wins counts that walk, as no later one shares
        // it. Gems past the win are worth nothing.
        const bool wins = group.gems >= short_by;
        // Later turns: the same bound before facts, the fastest clear and steps, for every group (the
        // facts' weighted worth while they hold). The fastest it reads is the one the facts keep.
        if constexpr (!opening) {
            if (tight && !banks_bag && !wins && !claimed && best >= 0 && g != farm_group && (!hop_any || map.group_hop(g) < 0)) {
                if (const int near = dist(here, group.centre); !may_help(group, belief, near)) {
                    auto& kf = group_facts[g];
                    float worth;
                    if (kf.context == context && !kf.sticky && kf.gold_context == gold_context) {
                        worth = kf.gems + kf.gold;
                    } else {
                        const float gems = static_cast<float>(std::min(worth_gems[g], short_by));
                        worth = gems + per_gold * worth_gold[g] + tribute_gold * gems;
                    }
                    float fastest;
                    if (kf.version == belief.version && kf.fastest_strength == strength) fastest = kf.fastest;
                    else if (belief.version == 0) fastest = group.health / strength;
                    else kf.version = belief.version, kf.fastest_strength = strength, fastest = kf.fastest = fastest_clear(world, g, strength);
                    if (rated_below(worth, static_cast<float>(near + near_wait(belief, near)), fastest)) continue;
                }
            }
        }
        // A first turn's facts cost a few hundred fuel a group. Empty-handed and short of the win
        // no walk to an altar is in the trip, and the weight is at most 1: a group the rated bound
        // rules out from as close as the Chebyshev distance needs none.
        if (rated && !banks_bag && !wins && !claimed && best >= 0 && g != farm_group && (!hop_any || map.group_hop(g) < 0)) {
            if (const int near = dist(here, group.centre); !may_help(group, belief, near)
                && (unweighed_beaten(group, belief, g, static_cast<float>(near + near_wait(belief, near)))
                    || (beyond_spare(world, g, strength, reflect, soften, spare_health, unclaimed_partner_output, spells, shield) && !engaged(g))))
                continue;
        }
        auto& known = group_facts[g];
        if (known.context != context || known.sticky != (g == farm_group)) {
            if (known.tribute == 0 || known.emblems != emblems) {
                known.emblems = emblems;
                known.tribute = tribute_turns(world, group.gems);
                const int n = holders(group);
                known.gold_in = static_cast<std::uint32_t>(group.gold / n + (prospector ? prospected(group.cluster_gold, n) : 0));
            }
            const Field* to_bank = to_altar ? to_altar : wins ? &pathing.to_any_altar() : nullptr;
            // A recall only goes home: the way out from an altar is walked.
            if (to_bank && known.to_altar < 0) known.to_altar = pathing.centre_to_altar(g);
            known.walk = to_bank ? known.to_altar : unreachable;
            // Chained, the gems join the bag's one tribute; from the altar they need their own.
            known.chained_tribute = tribute_turns(world, bag + group.gems) - (banks_bag ? bag_tribute : 0);
            // The bank terms when the way back is walked.
            const bool banks = static_cast<float>(known.walk) < static_cast<float>(unreachable);
            known.walked_bank = banks ? static_cast<float>(known.walk) + static_cast<float>(known.chained_tribute) : 0.0f;
            known.walked_cycle = banks ? static_cast<float>(known.walk) + static_cast<float>(known.tribute) : 0.0f;
            // From the draft's spawn steps; without a plan, two spawn floods once a game.
            if (known.home < 0) known.home = home_ground(map, g, opening);
            float weight = known.home;
            // Staying with last turn's choice keeps near ties from turning us back and forth.
            if (g == farm_group) weight *= stickiness;
            known.weight = weight;
            // A Prospector emblem's extra as if alone on the capture, as the reward is valued.
            known.gems = weight * static_cast<float>(std::min(group.gems + (prospector ? prospected(group.cluster_gems, 1) : 0), short_by));
            known.context = context;
            known.sticky = g == farm_group;
            known.gold_context = 0;
        }
        if (known.gold_context != gold_context) {
            const int gold = group.gold + (prospector ? prospected(group.cluster_gold, 1) : 0);
            const int gems = group.gems + (prospector ? prospected(group.cluster_gems, 1) : 0);
            known.gold = known.weight * (per_gold * static_cast<float>(gold) + tribute_gold * static_cast<float>(std::min(gems, short_by)));
            known.gold_context = gold_context;
        }
        if (known.version != belief.version || known.fastest_strength != strength)
            known.version = belief.version, known.fastest_strength = strength, known.fastest = fastest_clear(world, g, strength);
        // Ren's for the rated prunes; its plain ones keep the fastest.
        const float quickest = rated && reflect > 0 ? reflected_clear(world, g, strength, reflect) : known.fastest;
        const int walk = known.walk;
        // The trip home is health-dependent, so it stays out of the kept facts.
        float bank = known.walked_bank, cycle_bank = known.walked_cycle;
        if (to_altar) {
            const float back = (wins ? winning_trip : trip_home)->rounds(walk, capture, static_cast<std::uint32_t>(static_cast<float>(known.gold_in) * paid));
            const bool banks = back < static_cast<float>(unreachable);
            bank = banks ? back + static_cast<float>(known.chained_tribute) : 0.0f;
            cycle_bank = banks ? back + static_cast<float>(known.tribute) : 0.0f;
        }
        auto& steps_known = steps_data[g];
        if (steps_known < 0) {
            // A walk is never shorter than the Chebyshev distance, and the trip grows with the walk: a
            // group that cannot beat the best from that close needs no steps. A recall out of a pocket
            // or a crystal hop can be shorter (its nearest source and landing need not pair).
            const auto beaten_near = [&](bool by_rate) __attribute__((always_inline)) {
                const int near = dist(here, group.centre);
                if (in_pocket || may_help(group, belief, near) || (hop_any && map.group_hop(g) >= 0)) return false;
                const float worth = known.gems + known.gold;
                const float trip = std::max(0.0f, static_cast<float>(near + near_wait(belief, near)) - bank_now + bank);
                if (by_rate) return beaten(worth, trip, opening ? quickest : known.fastest, walk, cycle_bank);
                const float near_cycle = trip + cap_rounds + known.fastest;
                return near_cycle > 0 && worth / near_cycle <= best_value
                       && (!banks_bag || worth / (static_cast<float>(walk + capture) + cycle_bank + known.fastest) <= from_altar_value);
            };
            // Walking is symmetric: a group's centre field, once made, gives our steps to it. The sources
            // below give the same steps (the prunes skip only groups that cannot beat the best).
            if (const auto* centre = centre_field(g)) {
                steps_known = centre->at(here);
            } else if ((tight || rated) && !claimed && best >= 0 && g != farm_group && beaten_near(true)) {
                continue;
            } else if (const auto drafted = draft_spawn_graph ? map.drafted_spawn_steps(here, g) : std::nullopt) {
                steps_known = *drafted;
            } else if (const auto dashed = map.drafted_dash_steps(world.me().index, here, g, dash_kind)) {
                steps_known = *dashed;
            } else {
                if (!from_here) {
                    if ((!tight || g == farm_group) && !claimed && best >= 0 && beaten_near(false)) continue;
                    if (!fuel_ok(full_field_cost_estimate() + loop_floor + loop_reserve())) break;
                    from_here = make_field(pathing.static_walls(), single(here));
                    world.throw_if_stale();
                }
                steps_known = from_here->at(group.centre);
            }
        }
        int steps = steps_known;
        // Beyond our walk (beyond_walk): out of a pocket by a recall; into another region by its
        // crystal hop (StaticMap::group_hop) from our spawn, where one is bought (`toll`) unless
        // carried, and out of it again by a recall unless it holds an altar.
        float toll = 0;
        if (steps == unreachable && map.any_group_hop()) {
            int out = 0;
            vec2 from = here;
            if (in_pocket) out = recall_turns(world), from = recall_landing(world), steps = pathing.to_ally_spawn().at(group.centre);
            int h = map.group_hop(g);
            if (h == memory.hop_refused && round < memory.hop_refused_until) h = -1;
            if (steps == unreachable && h >= 0 && crystal < 0) crystal = carries_crystal() ? 2 : can_buy_crystal() ? 1 : 0;
            if (steps == unreachable && h >= 0 && crystal > 0) {
                if (crystal == 1 && !in_pocket) out = pathing.to_ally_spawn().at(here), from = map.ally_spawn_centre;
                if (!pathing.hop_ready(h) && !fuel_ok(2 * full_field_cost_estimate() + loop_floor + loop_reserve())) break;
                const int walk = pathing.to_hop(h).at(from), inner = pathing.from_landings(h).at(group.centre);
                if (walk != unreachable && inner != unreachable) {
                    steps = walk + cambc::constants::tp_crystal_time + inner
                            + (pathing.centre_to_altar(g) == unreachable ? recall_turns(world) : 0);
                    if (crystal == 1) toll = prices(world).per_gold * static_cast<float>(cambc::consumable_type::tp_crystal.cost());
                }
            }
            steps = steps == unreachable || out == unreachable ? unreachable : steps + out;
        }
        if (steps == unreachable) continue;
        // A group still respawning when we would arrive costs the wait there.
        const int wait = belief.state == CampState::respawning ? std::max(0, belief.respawn_round - round - steps) : 0;
        if (wait > params::max_wait) continue;
        if (!banks_bag && group.strength > 0 && belief.state == CampState::alive && steps <= params::help_radius
            && (steps < help_steps || (steps == help_steps && earlier(g, help_group))) && struggling(g))
            help_group = g, help_steps = steps;
        // A capture's gold that completes an emblem shortens the trip home (HomeTrip::rounds) though worth
        // counts it too: floored, so a chain never costs less than nothing and every filter below agrees.
        const float trip = std::max(0.0f, static_cast<float>(steps + wait) - bank_now + bank);
        const float gems = known.gems, gold = known.gold, fastest = known.fastest;
        // Risky groups matter only while no affordable one is found; skip the costly clearing
        // estimate for groups that cannot beat it even with no clearing. A crew's share can.
        if (!claimed && best >= 0
            && ((rated && g != farm_group && beaten(gems + gold, trip, quickest, walk, cycle_bank))
                || ((!rated || g == farm_group || reflect > 0)
                    && (gems + gold) / (trip + cap_rounds + fastest) <= best_value
                    && (!banks_bag || (gems + gold) / (static_cast<float>(walk + capture) + cycle_bank + fastest) <= from_altar_value))))
            continue;
        // No known way to an altar (sealed, or a centre walls hide) is no deadline: the gold still counts.
        const auto too_late = [&](float clear_rounds) __attribute__((always_inline)) {
            if (known.to_altar < 0) known.to_altar = pathing.centre_to_altar(g);
            const int last = known.to_altar;
            return last != unreachable
                   && static_cast<float>(steps + wait + capture + last + tribute_turns(world, bag + group.gems)) + clear_rounds > static_cast<float>(left);
        };
        const float worth = gems + gold - toll;
        if (claimed) {
            if (belief.state == CampState::cleared) continue;
            const bool fresh = belief.state == CampState::respawning;
            float health = 0;
            for (std::size_t i = 0; i < group.members.size(); ++i) health += fresh ? group.members[i].max_health : belief.health[i];
            const int waiting = fresh ? std::max(0, belief.respawn_round - round) : 0;
            const int working = std::max(0, steps - waiting);
            const auto crew = crew_work(g, working, waiting);
            const float others = crew.output;
            const float health_left = health - std::max(0.0f, others * static_cast<float>(working) - crew.delayed_damage);
            if (health <= 0 || health_left <= 0) continue;
            // A capture that wins the game is the team's, not a share: what counts is how soon.
            const float rounds = health_left / (strength + others), part = wins ? 1.0f : strength * rounds / health;
            // No capture rounds: the claimer holds it, and the crew moves on once it is cleared.
            const float value = rate(world, worth * part, trip + rounds);
            // Only a better share counts, and the final pick takes none an affordable group beats.
            if ((value < shared_value || (value == shared_value && !earlier(g, shared))) || (best >= 0 && value <= best_value) || too_late(rounds))
                continue;
            float joint_rounds = 0;
            // Unless we see the camp's health falling, our share is as if the claimer did nothing before
            // we arrive: crediting work the camp does not show would grow our share with every step
            // closer, and turn us back near the cap.
            const bool worked = belief.last_damaged_round >= round - 1;
            const float hits = soften * min_camp_damage(world, g, strength + others, &joint_rounds)
                               * (worked ? strength * rounds / health : strength / (strength + others));
            if (hits > spare_health) continue;
            shared = g, shared_value = value, shared_steps = steps;
            continue;
        }
        if (known.clearing != clearing || known.clear_version != belief.version) {
            known.clearing = clearing, known.clear_version = belief.version;
            known.damage = known.rounds = 0, known.kite = -1;
            if (belief.state != CampState::cleared) {
                known.damage = min_camp_damage(world, g, strength, &known.rounds, reflect);
                if (group.strength > 0) known.kite = spell_clear_rounds(world, g, range, spells, basic);
            }
        }
        const float alone_damage = shielded_clear(soften * known.damage, known.rounds, shield);
        const float alone_rounds = known.rounds, kite = known.kite;
        float partner_output = unclaimed_partner_output;
        if (alone_damage > spare_health && g == farm_group && memory.claim == g && !memory.crew && belief.state == CampState::alive) {
            for (const auto& a : world.allies) {
                if (a.is_self || !a.alive || !a.visible || dist(here, a.pos) > params::partner_radius
                    || comms::claim_of(world, a.index) != g) continue;
                const auto arrival = work_arrival(a, g);
                const int delay = arrival.delay(round);
                const bool together = arrival.anchor_round >= 0 && delay <= steps + wait;
                if (together) partner_output = std::max(partner_output, camp_output(a));
            }
        }
        // Unless a partner shares the clear, it takes us alone at least the quicker of the two ways.
        if (best >= 0 && (alone_damage <= spare_health || partner_output <= 0 || belief.state != CampState::alive)) {
            const float quickest = kite >= 0 ? std::min(alone_rounds, kite) : alone_rounds;
            if (worth / (trip + quickest + capture) <= best_value
                && (!banks_bag || worth / (static_cast<float>(walk) + cycle_bank + quickest + capture) <= from_altar_value))
                continue;
        }
        float clear_rounds = alone_rounds, damage = alone_damage;
        bool spell = false;
        // Clearing with spells from out of the camps' range is slower but costs no health.
        if (kite >= 0 && (damage > spare_health || kite < clear_rounds + heal(g, damage))) {
            spell = true;
            damage = 0;
            clear_rounds = kite;
        }
        if (too_late(clear_rounds)) continue;
        const float cycle = trip + clear_rounds + capture;
        float value = rate(world, worth, cycle);
        if (damage > spare_health && partner_output > 0 && belief.state == CampState::alive) {
            float joint_rounds = 0;
            const float part = strength / (strength + partner_output);
            if (soften * min_camp_damage(world, g, strength + partner_output, &joint_rounds) * part <= spare_health) {
                damage = 0;
                const float joint_cycle = trip + joint_rounds + capture;
                value = rate(world, worth * part, joint_cycle);
            }
        }
        if (damage > spare_health && !(opening ? engaged(g) : ally_engaged(world, g))) {
            if (value > risky_value || (value == risky_value && earlier(g, risky))) risky = g, risky_value = value, risky_steps = steps;
        } else {
            if (value > best_value || (value == best_value && earlier(g, best))) best = g, best_value = value, best_steps = steps, best_spell = spell;
            if (banks_bag && walk != unreachable) {
                const float via_altar = belief.state == CampState::respawning ? std::max(0.0f, static_cast<float>(belief.respawn_round - round - walk) - bank_now) : 0.0f;
                const float from_altar = static_cast<float>(walk) + cycle_bank + via_altar + clear_rounds + capture;
                from_altar_value = std::max(from_altar_value, rate(world, worth, from_altar));
            }
        }
    }
    if (k < evaluated) note_shortcut("farm-partial-evaluation");
    if (banks_bag && (best < 0 || best_value <= from_altar_value)) return false;
    if (banks_bag && attack_in_range()) return true;
    if (world.is_stale()) return true;
    if (best < 0) best = risky, best_steps = risky_steps, best_value = risky_value;
    memory.claim = best;
    memory.crew = false;
    bool spell = best >= 0 && best_spell;
    if (shared >= 0 && (best < 0 || shared_value > best_value))
        best = shared, best_steps = shared_steps, memory.claim = shared, memory.crew = true, spell = false;
    if (help_group >= 0) best = help_group, best_steps = help_steps, memory.claim = help_group, memory.crew = true, spell = false;
    if (best < 0) {
        // Cut short before weighing even last turn's choice: walk on towards it, as its crew if we were.
        if (k == 0 && memory.farm_group >= 0)
            memory.claim = memory.farm_group, memory.crew = crew_of_choice, walk_on(memory.farm_group);
        return true;
    }
    memory.farm_group = best;
    if (map.any_group_hop() && beyond_walk(world, pathing, best) && (in_pocket || cross(best))) return true;
    // Our fields price a dash over a hole line; live routes walk round it.
    const bool dasher = world.me().facts().has_dash();
    if (dasher && test(map.near_crossable, here))
        if (const auto* field = pathing.prepare_approach(best, walk_range(world, best), end_reserve); field && dash_across(world, pathing, *field))
            return true;
    const int cap = best_steps + max_detour;
    const bool search = fuel_ok(search_cost_estimate(cap) + end_reserve);
    // In a scratch board, valid until the next call.
    const auto off_zone = [&](const bitboard& goals) __attribute__((always_inline)) -> const bitboard& {
        if (!zone) return goals;
        static bitboard outside{cambc::uninitialized};
        outside.clear();
        outside |= goals;
        outside |= *zone;
        outside ^= *zone;
        return outside;
    };
    if (world.camps[best].state == CampState::cleared) {
        if (!zone) dash_towards(world, pathing, groups[best].tiles(), cap);
        if (search) {
            if (!pathing.step_towards(off_zone(groups[best].tiles()), zone, cap, groups[best].centre) && dasher) walk_on(best);
        } else {
            note_shortcut("farm-no-route");
            walk_on(best);
        }
        return true;
    }
    if (spell && dist(here, groups[best].centre) <= vision_radius + ability_range
        && spell_clear(world, pathing, best, zone, cap))
        return true;
    if (cast_at_camp_on_approach(world, best)) return true;
    const auto* tiles = farm_attack_tiles(world, pathing, best, range, [&] { return end_reserve + walk_reserve(best); });
    if (!tiles) {
        note_shortcut("farm-no-attack-tiles");
        walk_on(best);
        return true;
    }
    // In range and sight with the attack unspent: our pick may have been refused in passing.
    std::optional<bitboard> refused;
    if (test(*tiles, here) && my_can_attack() && attack_camp(world, [&](int g) { return g == best; }) < 0) {
        refused.emplace(*tiles);
        refused->set(here, false);
    }
    const auto& goals = refused ? *refused : *tiles;
    if (test(goals, here)) { // attacked from here; stay
        cast_at_camp(world, best);
        reset_and_attack_camp(world, best);
        if (melee) step_onto_cleared(world, pathing, best);
        return true;
    }
    const Field* dash_route = nullptr;
    if (!zone && dash_towards(world, pathing, goals, cap, &dash_route) && attack_camp(world, passing) >= 0) return true;
    if (dash_route) world.throw_if_stale();
    bool walked = dash_route && pathing.descend(*dash_route, zone, groups[best].centre);
    if (!walked)
        walked = fuel_ok(search_cost_estimate(cap) + end_reserve)
                     ? pathing.step_towards(off_zone(goals), zone, cap, groups[best].centre)
                           || pathing.step_towards(off_zone(groups[best].adjacent()), zone, cap, groups[best].centre)
                     : (note_shortcut("farm-no-route"), walk_on(best));
    if (!walked && dasher) walk_on(best);
    if (walked) {
        // A hit on a champion is worth its damage; on a camp, the gems it brings closer.
        see_revealed(world, pathing, safety);
        if (!strike_enemy(world)) attack_camp(world, passing);
        cast_at_camp(world, best); // only casts that allow walking remain
        reset_and_attack_camp(world, best);
    }
    return true;
}

bool farm(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    return world.round == world.first_round ? farm_turn<true>(world, pathing, safety, memory) : farm_turn<false>(world, pathing, safety, memory);
}

// A farming turn's output lands on camps: in enemy health points, the gems it earns at the map's
// gems per camp health point.
float farm_step_value(const World& world) {
    static float density = -1;
    if (density < 0) {
        float gems = 0, health = 0;
        for (const auto& g : world.map().groups) {
            if (g.gems == 0 || (g.has_monolith && !world.map().monolith_only)) continue;
            gems += static_cast<float>(g.gems);
            for (const auto& m : g.members) health += m.max_health;
        }
        density = health > 0 ? gems / health : 0.0f;
    }
    return output(world.me()) * density * params::gem_value;
}

} // namespace

} // namespace aph
