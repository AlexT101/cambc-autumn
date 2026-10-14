// Placeholder behaviour, roughly the starter bot's. Replace freely.
#include "bot.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <optional>
#include <vector>
#include "abilities.h"
#include "comms.h"
#include "params.h"
#include "pathing.h"
#include "safety.h"
#include "self_abilities.h"
#include "world.h"

namespace aph {

namespace {

using params::max_detour;

constexpr int endgame_horizon = 400; // rounds left before the endgame checks start
constexpr int endgame_margin = 20;   // rounds to spare on the last trip to an altar
constexpr int endgame_slack = 2;     // rounds to spare on a last-chance tribute
constexpr int endgame_shop_rounds = 100; // no shop trips this late: spent gold scores nothing

// The turn's branch, for debug_fights: Chase, Attack, Retreat, Farm, Bank, Wait at an altar,
// Tribute kept / t cancelled, recall Kept / k cancelled, Healing on spawn, rally (J), holding (P).
char decision = '-';

// Read by tools/replay/fight_calibration.py.
void log_fight(const char* tag, const World& world, Safety& safety, vec2 p, const Trade& t, int target = -1) {
    if (!debug_fights || !fuel_ok(params::end_reserve + 15000)) return;
    std::cout << tag << ' ' << world.round << ' ' << static_cast<std::uint32_t>(world.me().handle) << ' ' << p.x << ' ' << p.y
              << ' ' << static_cast<int>(world.me().health) << ' ' << decision << ' ' << t.lost << ' '
              << t.turns_to_kill_us << ' ' << t.turns_to_kill_them << ' ' << t.allies << ' ' << t.enemies << ' '
              << static_cast<int>(t.our_health) << ' ' << static_cast<int>(t.their_health) << ' ' << target << ' '
              << static_cast<int>(safety.camp_damage(p)) << ' ' << safety.lethal(p);
    for (const auto& th : safety.threats())
        if (th.credible() && th.strike.hits(th.distance(p)))
            std::cout << ' ' << static_cast<std::uint32_t>(world.enemies[th.enemy].handle) << (th.visible ? 'v' : 'u');
    std::cout << std::endl;
}

enum Family { monster, power, durability, treasure, jungle, home, bruiser };
enum StatKind { strength_stat, focus_stat, health_stat };

cambc::item_type shard_of(int family, int stat) {
    return cambc::item_type{static_cast<std::uint32_t>(family * 6 + stat * 2)};
}
cambc::item_type emblem_of(int family, int stat) {
    return cambc::item_type{static_cast<std::uint32_t>(family * 6 + stat * 2 + 1)};
}

// Casters whose spells out-damage their basic attacks per shard: Focus grows 10-15 a shard
// against 3.5 Strength, and spell multipliers sum to 2-3.4 per 8 rounds, front-loaded in a fight.
int main_stat(const ChampionFacts& f) {
    using C = cambc::champion_type;
    return f.type == C::stellar || f.type == C::prism || f.type == C::cassi ? focus_stat : strength_stat;
}

bool buy(cambc::item_type shard, unsigned count) {
    auto& me = cambc::self();
    if (!count || !me.can_buy(shard, count)) return false;
    try {
        me.buy(shard, count);
        return true;
    } catch (const cambc::error&) {
        return false;
    }
}

// Jungle (-30% camp damage), then Monster (+10% camp damage) in the main stat; then Bruiser
// emblems (7 shards' stats for 5), each in whichever of health and the main stat raises their
// product more, since fights go to the side with more health and damage.
void buy_shards(const ChampionFacts& f) {
    auto& me = cambc::self();
    const auto owned = me.item_count();
    const int main = main_stat(f);
    unsigned gold = me.gold_count();
    for (int family : {jungle, monster}) {
        const int have = static_cast<int>(owned[shard_of(family, main)] + 5 * owned[emblem_of(family, main)]);
        const unsigned count = std::min<unsigned>(5 - std::min(have, 5), gold / 30);
        if (!count) continue;
        if (!buy(shard_of(family, main), count)) return;
        gold -= 30 * count;
        if (have + static_cast<int>(count) < 5) return;
    }
    float health = me.max_health(), value = main == focus_stat ? me.focus() : me.strength();
    const float main_growth = main == focus_stat ? f.focus.growth : f.strength.growth;
    int partial_hp = static_cast<int>(owned[shard_of(bruiser, health_stat)]);
    int partial_main = static_cast<int>(owned[shard_of(bruiser, main)]);
    while (gold >= 30) {
        bool hp;
        if (partial_hp) hp = true;
        else if (partial_main) hp = false;
        else {
            float hp_gain = f.health.growth / health;
            if (f.passive == Passive::health_strength && main == strength_stat) hp_gain += 1 / value;
            hp = hp_gain > main_growth / value;
        }
        int& partial = hp ? partial_hp : partial_main;
        const unsigned count = std::min<unsigned>(5 - partial, gold / 30);
        if (!buy(shard_of(bruiser, hp ? health_stat : main), count)) return;
        gold -= 30 * count;
        (hp ? health : value) += (hp ? f.health.growth : main_growth) * static_cast<float>(count);
        partial = (partial + static_cast<int>(count)) % 5;
        if (partial == 0) (hp ? value : health) += hp ? main_growth : f.health.growth; // the emblem's extra shard
    }
}

bool attack_enemy(const World& world) {
    auto& me = cambc::self();
    if (!me.can_attack()) return false;
    const auto target = attack_target(world);
    if (!target) return false;
    try {
        me.attack(*target);
        return true;
    } catch (const cambc::error&) {
        return false;
    }
}

// A camp in range of a group `allowed` accepts; the group of the camp attacked, or -1.
template <class Allowed> int attack_camp(const World& world, Allowed allowed) {
    auto& me = cambc::self();
    if (!me.can_attack()) return -1;
    const int range = world.me().facts().attack_range();
    const auto& map = world.map();
    for (auto p : (cambc::vision::camp_tiles() & square(me.position(), range)).positions()) {
        const int g = map.group_at(p);
        if (g < 0 || map.groups[g].has_monolith || !allowed(g)) continue;
        const auto& members = map.groups[g].members;
        for (int i = 0; i < static_cast<int>(members.size()); ++i) {
            if (members[i].pos != p) continue;
            try {
                me.attack(map.groups[g].camp(i));
                if (map.groups[g].strength > 0 && g < 63) comms::post_help(world.round, g);
                return g;
            } catch (const cambc::error&) {
            }
        }
    }
    return -1;
}

// Around awake camps and credible enemies when a way exists, else straight. Routes are replanned
// every turn, so only danger near us is worth the extra search.
void step_safely(Pathing& pathing, const Field& field, Safety& safety) {
    const auto avoid = safety.avoid();
    const bool near = !(avoid & square(cambc::self().position(), safety_params::avoid_radius)).is_empty();
    if (!near || !pathing.step_towards(field, &avoid)) pathing.step_towards(field);
}

bool break_lock(const World& world, int altar) {
    auto& me = cambc::self();
    const vec2 p = world.map().altars[altar].pos;
    if (!me.can_attack() || dist(me.position(), p) > world.me().facts().attack_range()) return false;
    for (const auto& lock : cambc::vision::altar_locks())
        if (lock.is_enemy() && lock.position() == p) {
            try {
                me.attack(lock);
                return true;
            } catch (const cambc::error&) {
                return false;
            }
        }
    return false;
}

// A tribute channel cannot act, and a kill takes the whole bag: start or keep one only if the
// visible enemies could not kill us before it ends, nor damage at the rate of the last round
// (attackers in bushes stay unseen).
bool tribute_safe(Safety& safety, const Memory& memory, int turns) {
    const float health = cambc::self().health();
    if (memory.damage * static_cast<float>(turns) >= health) return false;
    const int kill = safety.turns_to_kill_idle(cambc::self().position(), turns + 1);
    return kill == 0 || kill > turns;
}

int tribute_turns(int gems) { return std::max(1, (gems + 9) / 10); }

// Carried gems score nothing after the round limit.
int rounds_left(const World& world) { return static_cast<int>(cambc::constants::max_rounds) - world.round; }

// A tribute started or kept now is the bag's last chance to score: take it at any risk.
bool last_chance(const World& world, int channel_turns) { return rounds_left(world) <= channel_turns + endgame_slack; }

// The bag needs the rest of the game to reach an altar and score.
bool endgame(const World& world, Pathing& pathing) {
    const int bag = cambc::self().gem_count();
    if (bag == 0 || rounds_left(world) > endgame_horizon) return false;
    const int walk = pathing.to_any_altar().at(cambc::self().position());
    return walk != unreachable && rounds_left(world) <= walk + tribute_turns(bag) + endgame_margin;
}

// At an unlocked altar in reach. The caller judged the turn's start tile safe; anywhere else is
// judged again.
bool submit_here(const World& world, Safety& safety, const Memory& memory) {
    auto& me = cambc::self();
    const vec2 here = me.position();
    const auto& altars = world.map().altars;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
        if (world.altars[a].enemy_lock || dist(here, altars[a].pos) > cambc::constants::submit_gems_range) continue;
        const int turns = tribute_turns(me.gem_count());
        if (here != world.me().pos && !last_chance(world, turns) && !tribute_safe(safety, memory, turns)) return false;
        try {
            me.submit_gems(altars[a].pos);
            return true;
        } catch (const cambc::error&) {
        }
    }
    return false;
}

void bank_gems(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    if (submit_here(world, safety, memory)) return;
    const vec2 here = cambc::self().position();
    const auto& altars = world.map().altars;
    bool any_locked = false;
    for (const auto& a : world.altars) any_locked |= a.enemy_lock;
    // One cached field covers every altar; per-altar fields are needed only to skip locked ones.
    if (!any_locked) {
        if (dash_towards(world, pathing, pathing.to_any_altar()) && submit_here(world, safety, memory)) return;
        step_safely(pathing, pathing.to_any_altar(), safety);
        submit_here(world, safety, memory);
        return;
    }
    // Breaking a lock takes a turn per hit left, about a step each. Fields not yet affordable
    // wait for a later turn.
    int best = -1, best_steps = unreachable;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
        const auto& belief = world.altars[a];
        const auto* field = pathing.to_altar(a, params::end_reserve);
        if (!field) continue;
        int steps = field->at(here);
        if (steps == unreachable) continue;
        if (belief.enemy_lock) steps += belief.enemy_lock_hits > 0 ? belief.enemy_lock_hits : static_cast<int>(cambc::constants::altar_lock_hits);
        if (steps < best_steps) best = a, best_steps = steps;
    }
    if (best < 0) return;
    if (dash_towards(world, pathing, pathing.to_altar(best)) && submit_here(world, safety, memory)) return;
    if (world.altars[best].enemy_lock && break_lock(world, best) && !world.me().facts().walk_and_attack_independent()) return;
    step_safely(pathing, pathing.to_altar(best), safety);
    submit_here(world, safety, memory);
}

constexpr int capture_rounds = 6;

// Damage taken clearing a group alone with basic attacks, killing the deadliest first; also
// the rounds it takes.
float min_camp_damage(const CampGroup& group, const CampBelief& belief, float strength, float* rounds) {
    struct Left {
        float health, strength;
    };
    std::vector<Left> left(group.members.size());
    int n = 0;
    const bool fresh = belief.state == CampState::respawning;
    for (std::size_t i = 0; i < group.members.size(); ++i) {
        const float hp = fresh ? group.members[i].max_health : belief.health[i];
        if (hp > 0) left[n++] = {hp, group.members[i].strength};
    }
    std::sort(left.begin(), left.begin() + n,
              [](const Left& a, const Left& b) { return a.strength * b.health > b.strength * a.health; });
    float damage = 0, elapsed = 0;
    for (int i = 0; i < n; ++i) {
        elapsed += std::ceil(left[i].health / strength);
        damage += left[i].strength * (elapsed - 1);
    }
    *rounds = elapsed;
    return damage;
}

// Beliefs about most groups do not change between turns, so neither does this.
float min_camp_damage(int g, const CampGroup& group, const CampBelief& belief, float strength, float* rounds) {
    struct Entry {
        bool valid = false, fresh = false;
        float strength = 0;
        std::array<float, 8> health{};
        float damage = 0, rounds = 0;
    };
    static std::vector<Entry> cache;
    const auto& health = belief.health;
    if (health.size() > Entry{}.health.size()) return min_camp_damage(group, belief, strength, rounds);
    if (cache.size() <= static_cast<std::size_t>(g)) cache.resize(g + 1);
    auto& e = cache[g];
    const bool fresh = belief.state == CampState::respawning;
    bool same = e.valid && e.fresh == fresh && e.strength == strength;
    for (std::size_t i = 0; same && i < health.size(); ++i) same = e.health[i] == health[i];
    if (!same) {
        e.valid = true;
        e.fresh = fresh;
        e.strength = strength;
        std::copy(health.begin(), health.end(), e.health.begin());
        e.damage = min_camp_damage(group, belief, strength, &e.rounds);
    }
    *rounds = e.rounds;
    return e.damage;
}

// On a cleared group's tile that no lower-id ally also holds, with no enemy on any of its tiles:
// stepping off loses the capture's progress, and it pays within six rounds.
bool holding_capture(const World& world) {
    const vec2 here = cambc::self().position();
    const int g = world.map().group_at(here);
    if (g < 0 || world.camps[g].state != CampState::cleared) return false;
    const auto& tiles = world.map().groups[g].tiles();
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && a.index < world.me().index && tiles.is_set(a.pos)) return false;
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && tiles.is_set(e.pos)) return false;
    return true;
}

bool ally_engaged(const World& world, int group) {
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && world.map().groups[group].threat().is_set(a.pos)) return true;
    return false;
}

// Carrying gems, farming on chains a capture onto the bag: it saves the walk to the altar and
// back but keeps the bag at risk for longer. It goes ahead only if the next group, by the time it
// adds to the trip, beats the best cycle starting from the altar; false means bank instead.
bool farm(const World& world, Pathing& pathing, Memory& memory) {
    auto& me = cambc::self();
    const auto& map = world.map();
    const auto& groups = map.groups;
    const int range = world.me().facts().attack_range();
    const float strength = std::max(1.0f, world.me().strength);
    const float spare_health = me.health() - params::recall_health_fraction * me.max_health();
    const int bag = me.gem_count();
    // Groups in passing pay too (gold clusters are never chosen below), but not one whose clear
    // costs more health than we can spare.
    const auto affordable = [&](int g) {
        if (g == memory.farm_group || groups[g].strength <= 0) return true;
        float rounds = 0;
        return min_camp_damage(g, groups[g], world.camps[g], strength, &rounds) <= spare_health || ally_engaged(world, g);
    };
    const auto attack_in_range = [&] {
        const int hit = attack_camp(world, affordable);
        if (hit < 0 || world.me().facts().walk_and_attack_independent()) return false; // walk on
        cast_at_camp(world, hit);
        reset_and_attack_camp(world, hit);
        return true;
    };
    if (bag == 0 && attack_in_range()) return true;

    // One holder keeps a capture going, and sharers split the reward: the lowest id stays.
    const auto ally_holding = [&](int g, bool lower_only) {
        for (const auto& a : world.allies)
            if (!a.is_self && a.alive && a.visible && groups[g].tiles().is_set(a.pos)
                && (!lower_only || a.index < world.me().index))
                return true;
        return false;
    };

    const vec2 here = me.position();
    if (holding_capture(world)) return true;

    // Short of fuel, walk on towards the last choice rather than run out mid-turn.
    const auto walk_on = [&](int g) {
        if (g < 0) return false;
        if (const auto* field = pathing.from_centre(g)) return pathing.descend(*field);
        return pathing.step_closer(groups[g].centre);
    };
    const auto evaluation = (pathing.centres_ready() ? 0 : field_cost_estimate()) + 300 * groups.size();
    if (!fuel_ok(evaluation + params::end_reserve)) {
        if (bag > 0) return false;
        // On large maps this can last hundreds of rounds, past the last choice's capture: once
        // that is gone, the nearest group as the crow flies.
        const auto worth = [&](int g) {
            const auto& c = world.camps[g];
            return !groups[g].has_monolith && groups[g].gems > 0 && !(c.state == CampState::cleared && ally_holding(g, false))
                   && !(c.state == CampState::respawning && c.respawn_round - world.round > dist(here, groups[g].centre));
        };
        if (memory.farm_group < 0 || !worth(memory.farm_group)) {
            memory.farm_group = -1;
            int nearest = 0;
            for (int g = 0; g < static_cast<int>(groups.size()); ++g)
                if (const int d = dist(here, groups[g].centre); (memory.farm_group < 0 || d < nearest) && worth(g))
                    memory.farm_group = g, nearest = d;
        }
        walk_on(memory.farm_group);
        return true;
    }
    // Warmed-up centre fields give the steps a field from here would, without its cost.
    std::optional<Field> from_here;
    if (!pathing.centres_ready()) from_here = make_field(map.blocked_for_us, single(here));
    const Field* to_altar = bag > 0 ? &pathing.to_any_altar() : nullptr; // trips matter only when carrying
    const int left = rounds_left(world);
    const Field* deadline = left <= endgame_horizon ? &pathing.to_any_altar() : nullptr;
    const int bank_now = to_altar && to_altar->at(here) != unreachable ? to_altar->at(here) : 0;
    float from_altar_value = 0;
    // Unaffordable groups only when nothing else is left: idling is worse.
    int best = -1, best_steps = unreachable, risky = -1, risky_steps = unreachable;
    float best_value = 0, risky_value = 0;
    const auto help = comms::help();
    const int help_group = bag == 0 && help && help->round >= world.round - 1 ? help->group : -1;
    int help_steps = unreachable;
    for (int g = 0; g < static_cast<int>(groups.size()); ++g) {
        const auto& group = groups[g];
        const auto& belief = world.camps[g];
        if (group.has_monolith || group.gems == 0 || (belief.state == CampState::cleared && ally_holding(g, false)))
            continue;
        const int steps = from_here ? from_here->at(group.centre) : pathing.from_centre(g)->at(here);
        if (steps == unreachable) continue;
        // Skip groups still respawning when we would arrive.
        if (belief.state == CampState::respawning && belief.respawn_round - world.round > steps) continue;
        if (g == help_group && belief.state == CampState::alive && steps <= params::help_radius) help_steps = steps;
        // Carrying, compare whole trips: the gems score only after the walk to an altar and the
        // tribute. Counting those without a bag favours camps near altars, which lost games.
        const int back = to_altar ? to_altar->at(group.centre) : unreachable;
        const int bank = bag == 0 || back == unreachable ? 0 : back + (group.gems + 9) / 10;
        const int trip = steps - bank_now + bank;
        const float gems = static_cast<float>(group.gems);
        // Risky groups matter only while no affordable one is found; skip the costly clearing
        // estimate for groups that cannot beat it even with no clearing.
        if (best >= 0 && gems / static_cast<float>(trip + capture_rounds) <= best_value
            && (bag == 0 || gems / static_cast<float>(back + bank + capture_rounds) <= from_altar_value))
            continue;
        float clear_rounds = 0, damage = 0;
        if (belief.state != CampState::cleared) {
            damage = min_camp_damage(g, group, belief, strength, &clear_rounds);
        }
        if (deadline) {
            const int last = deadline->at(group.centre);
            if (last == unreachable
                || static_cast<float>(steps + capture_rounds + last + tribute_turns(bag + group.gems)) + clear_rounds > static_cast<float>(left))
                continue;
        }
        const float value = gems / (static_cast<float>(trip) + clear_rounds + capture_rounds);
        if (damage > spare_health && !ally_engaged(world, g)) {
            if (value > risky_value) risky = g, risky_value = value, risky_steps = steps;
        } else {
            if (value > best_value) best = g, best_value = value, best_steps = steps;
            if (bag > 0 && back != unreachable)
                from_altar_value = std::max(from_altar_value, gems / (static_cast<float>(back + bank) + clear_rounds + capture_rounds));
        }
    }
    if (bag > 0 && (best < 0 || best_value <= from_altar_value)) return false;
    if (bag > 0 && attack_in_range()) return true;
    if (best < 0) best = risky, best_steps = risky_steps;
    // Monsters hit the nearest champion, so a second attacker shortens the clear and the damage taken.
    if (help_steps != unreachable) best = help_group, best_steps = help_steps;
    if (best < 0) return true;
    memory.farm_group = best;
    const int cap = best_steps + max_detour;
    const bool search = fuel_ok(search_cost_estimate(cap) + params::end_reserve);
    if (world.camps[best].state == CampState::cleared) {
        dash_towards(world, pathing, groups[best].tiles());
        if (search) pathing.step_towards(groups[best].tiles(), nullptr, cap);
        else walk_on(best);
        return true;
    }
    if (!pathing.prepare_attack_tiles(best, range, params::end_reserve)) {
        walk_on(best);
        return true;
    }
    auto goals = pathing.attack_tiles(best, range);
    // In range and sight with the attack unspent, so the attack failed here: try another tile.
    if (goals.is_set(here) && me.can_attack()) goals.set(here, false);
    if (goals.is_set(here)) { // attacked from here; stay
        cast_at_camp(world, best);
        reset_and_attack_camp(world, best);
        return true;
    }
    if (dash_towards(world, pathing, goals) && attack_camp(world, affordable) >= 0) return true;
    const bool walked = fuel_ok(search_cost_estimate(cap) + params::end_reserve)
                            ? pathing.step_towards(goals, nullptr, cap) || pathing.step_towards(groups[best].adjacent(), nullptr, cap)
                            : walk_on(best);
    if (walked) {
        attack_camp(world, affordable);
        cast_at_camp(world, best); // only casts that allow walking remain
        reset_and_attack_camp(world, best);
    }
    return true;
}

bool try_ward(vec2 p, Memory& memory) {
    try {
        if (!cambc::self().place_ward(p)) return false;
    } catch (const cambc::error&) {
        return false;
    }
    memory.ward = p;
    memory.bushes_watched = {-1, -1};
    return true;
}

// Attackers in a bush stay unseen from outside it, and a ward inside sees across its cluster.
// Ward the cluster in reach with the most tiles near us, unless our own ward already watches it.
bool ward_bushes(const World& world, Memory& memory) {
    const auto& map = world.map();
    const vec2 here = cambc::self().position();
    const auto floor = small_cost_estimate + params::end_reserve;
    if (here == memory.bushes_watched || !fuel_ok(floor) || !map.near_bushes().is_set(here)
        || !map.find_bush_clusters(here, 2, floor))
        return false;
    auto candidates = map.bushes & square(here, 2);
    if (map.bushes.is_set(here)) candidates &= ~map.bush_cluster(here).tiles;
    if (in_bounds(memory.ward) && map.bushes.is_set(memory.ward)) candidates &= ~map.bush_cluster(memory.ward).tiles;
    if (candidates.is_empty()) {
        memory.bushes_watched = here;
        return false;
    }
    candidates &= ~(map.enemy_spawn | cambc::vision::ward_tiles(team::ally));
    const auto near = square(here, params::bush_watch_radius);
    const auto deep = ~square(here, 1);
    std::optional<vec2> best;
    int best_tiles = 0;
    while (!candidates.is_empty()) {
        const auto& c = map.bush_cluster(candidates.positions().front());
        const int tiles = static_cast<int>((c.tiles & near).count());
        if (tiles > best_tiles) {
            const auto mine = c.tiles & candidates;
            const auto far = mine & deep;
            best = (far.is_empty() ? mine : far).positions().front(), best_tiles = tiles;
        }
        candidates &= ~c.tiles;
    }
    return best && try_ward(*best, memory);
}

void place_ward(const World& world, Pathing& pathing, Memory& memory) {
    if (!world.me().alive || cambc::self().ward_cooldown() > 0) return;
    if (ward_bushes(world, memory) || world.round % params::ward_period != 0) return;
    const vec2 spawn = world.map().ally_spawn_centre;
    std::optional<vec2> best;
    for (auto p : (pathing.ward_targets() & ~world.map().bushes).positions())
        if (!best || dist(spawn, p) > dist(spawn, *best)) best = p;
    if (best) try_ward(*best, memory);
}

// Retreating from an awake camp takes its hits anyway, and the clear is lost.
bool finishing_camp(const World& world) {
    const vec2 here = cambc::self().position();
    const auto& groups = world.map().groups;
    for (int g = 0; g < static_cast<int>(groups.size()); ++g) {
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.awake == Awake::asleep || !groups[g].threat().is_set(here)) continue;
        float rounds = 0;
        const float damage = min_camp_damage(g, groups[g], c, std::max(1.0f, world.me().strength), &rounds);
        return damage < params::finish_camp_health_fraction * cambc::self().health();
    }
    return false;
}

// The threats' visible part, without building the unseen ones' fields.
bool visible_threat(const World& world, vec2 p) {
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && strike(e, next_turn_round(world, e)).hits(dist(p, e.pos))) return true;
    return false;
}

// An enemy that could kill us before our next turn overrides finishing a camp or a capture.
bool want_home(const World& world, Safety& safety) {
    const auto& me = cambc::self();
    if (world.map().ally_spawn.is_set(me.position())) return false;
    return (me.health() < params::recall_health_fraction * me.max_health() && !finishing_camp(world) && !holding_capture(world))
           || (safety.lethal(me.position()) && safety.fight(me.position()).self_falls)
           || (visible_threat(world, me.position()) && safety.fight(me.position()).lost);
}

bool can_tribute_here(const World& world) {
    const auto& me = cambc::self();
    if (me.gem_count() == 0) return false;
    const auto& altars = world.map().altars;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a)
        if (!world.altars[a].enemy_lock && dist(me.position(), altars[a].pos) <= cambc::constants::submit_gems_range) return true;
    return false;
}

// The visible enemy quickest to reach and kill among those whose local fight we win even when
// they strike first; never one on or next to its spawn, where it heals.
const ChampionBelief* prey(const World& world, Safety& safety) {
    const auto& me = cambc::self();
    const vec2 here = me.position();
    const int range = world.me().facts().attack_range();
    const float strength = std::max(1.0f, me.strength());
    const auto& enemy_spawn = world.map().enemy_spawn;
    // Quickest first (ties in index order), so fights are simulated only up to the first won.
    std::array<std::pair<float, const ChampionBelief*>, 8> order;
    int n = 0;
    for (const auto& e : world.enemies) {
        if (n == static_cast<int>(order.size()) || !e.alive || !e.visible || dist(here, e.pos) > params::chase_radius
            || !(enemy_spawn & square(e.pos, 1)).is_empty())
            continue;
        const float turns = static_cast<float>(std::max(0, dist(here, e.pos) - range)) + e.health / strength;
        int i = n++;
        for (; i > 0 && order[i - 1].first > turns; --i) order[i] = order[i - 1];
        order[i] = {turns, &e};
    }
    // Chasing is optional: leave enough for the walk after it and the turn's end.
    const auto reserve = search_cost_estimate(2 * params::chase_radius) + params::end_reserve;
    for (int i = 0; i < n && fuel_ok(safety.fight_cost_estimate() + reserve); ++i)
        if (!safety.fight(order[i].second->pos).lost) return order[i].second;
    return nullptr;
}

bool chase(const World& world, Pathing& pathing, Safety& safety) {
    const auto* target = prey(world, safety);
    if (!target) return false;
    decision = 'C';
    if constexpr (debug_fights) log_fight("FC", world, safety, target->pos, safety.fight(target->pos), static_cast<int>(target->handle));
    auto& me = cambc::self();
    comms::post_rally(world.round, target->pos);
    const int range = world.me().facts().attack_range();
    // A walk alone cannot reach range this turn.
    if (dist(me.position(), target->pos) > range + 1 && me.can_move()) dash_to_attack(world, pathing, target);
    if (dist(me.position(), target->pos) > range && me.can_move()) {
        if (fuel_ok(search_cost_estimate(2 * params::chase_radius) + params::end_reserve))
            pathing.step_towards(square(target->pos, range) & ~world.map().blocked_for_us);
        else
            pathing.step_closer(target->pos);
    }
    attack_enemy(world);
    reset_and_attack_enemy(world); // after an attack, or a ranged walk
    cast_at_enemies(world);
    return true;
}

// Towards a fight an ally posted this round or last. Within half our vision of it, chase decides
// whether to join.
bool join_rally(const World& world, Pathing& pathing) {
    const auto rally = comms::rally();
    if (!rally || rally->round < world.round - 1) return false;
    const vec2 here = cambc::self().position();
    const int d = dist(here, rally->pos);
    if (d <= params::chase_radius / 2 || d > params::rally_radius
        || !fuel_ok(search_cost_estimate(2 * params::rally_radius) + params::end_reserve))
        return false;
    return pathing.step_towards(square(rally->pos, 1) & ~world.map().blocked_for_us, nullptr, 2 * params::rally_radius);
}

bool can_tribute_safely(const World& world, Safety& safety, const Memory& memory) {
    if (!can_tribute_here(world)) return false;
    const int turns = tribute_turns(cambc::self().gem_count());
    return last_chance(world, turns) || tribute_safe(safety, memory, turns);
}

// Only a small bag, out of every credible enemy's reach, and never the gems that would win.
bool may_chain(const World& world, Safety& safety) {
    const int bag = cambc::self().gem_count();
    if (bag >= params::chain_bag_limit || world.score.ally + bag >= static_cast<int>(cambc::constants::winning_gems)
        || can_tribute_here(world))
        return false;
    for (const auto& t : safety.threats())
        if (t.credible()) return false;
    return true;
}

// A bag bound for an altar rides the recall home when that reaches an altar sooner than walking;
// the stop also heals and shops.
bool recall_to_bank(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    auto& me = cambc::self();
    if (!memory.banking || me.gem_count() == 0 || safety.threatened(me.position())) return false;
    const auto& to_altar = pathing.to_any_altar();
    const int walk = to_altar.at(me.position()), from_spawn = to_altar.at(world.map().ally_spawn_centre);
    if (walk == unreachable || from_spawn == unreachable) return false;
    const int heal = me.health() < me.max_health() ? 1 : 0;
    return me.remaining_channel_time() + heal + from_spawn < walk;
}

// With an empty bag, a full emblem's gold goes home, riding a recall unless walking is quicker:
// the bot otherwise carries 150+ gold for long stretches between forced visits, and the stop
// also heals.
bool wants_shop(const World& world, Safety& safety, const Memory& memory) {
    auto& me = cambc::self();
    if (me.gem_count() > 0 || me.gold_count() < params::shop_trip_gold || memory.damage > 0
        || world.me().facts().passive == Passive::remote_shop || rounds_left(world) <= endgame_shop_rounds
        || world.map().ally_spawn.is_set(me.position()) || safety.threatened(me.position()))
        return false;
    const auto& groups = world.map().groups;
    for (int g = 0; g < static_cast<int>(groups.size()); ++g)
        if (world.camps[g].state == CampState::alive && world.camps[g].awake != Awake::asleep
            && groups[g].threat().is_set(me.position()))
            return false;
    return true;
}

void decide(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    auto& me = cambc::self();
    if (me.gem_count() == 0 || !world.me().alive) memory.banking = false;
    if (!world.me().alive) {
        buy_shards(world.me().facts()); // the dead can only shop
        return;
    }
    if (me.is_teleporting()) return;
    if (me.is_submitting_gems()) {
        decision = 'T';
        const int turns = me.remaining_channel_time();
        if (last_chance(world, turns) || tribute_safe(safety, memory, turns)) return;
        // Damage does not interrupt a tribute: cancelling pays only to flee or to fight back.
        if (memory.damage <= 0 && !want_home(world, safety) && !attack_target(world) && !prey(world, safety)) return;
        decision = 't';
        try {
            me.cancel_submit_gems();
        } catch (const cambc::error&) {
            return;
        }
    }
    if (me.is_recalling()) {
        decision = 'K';
        if (want_home(world, safety) && !safety.threatened(me.position()) && !can_tribute_safely(world, safety, memory)) return;
        decision = 'k';
        const auto shop = [&] {
            return wants_shop(world, safety, memory) && me.remaining_channel_time() < pathing.to_ally_spawn().at(me.position());
        };
        if (!holding_capture(world) && (recall_to_bank(world, pathing, safety, memory) || shop())) return;
        try {
            me.cancel_recall();
        } catch (const cambc::error&) {
            return;
        }
    }

    if (world.map().ally_spawn.is_set(me.position()) || world.me().facts().passive == Passive::remote_shop)
        buy_shards(world.me().facts());
    heal_ally(world);
    shield_if_needed(world);
    // Healing needs a turn end on spawn; a recall arrives at turn start.
    if (world.map().ally_spawn.is_set(me.position()) && me.health() < me.max_health()) {
        decision = 'H';
        const bool attacked = attack_enemy(world);
        if (attacked) reset_and_attack_enemy(world, true);
        cast_at_enemies(world);
        if (attacked) reset_and_attack_enemy(world);
        return;
    }
    if (want_home(world, safety)) {
        decision = 'R';
        if (world.me().facts().walk_and_attack_independent()) attack_enemy(world);
        cast_at_enemies(world, true);
        // A tribute survives damage; a recall does not.
        if (can_tribute_safely(world, safety, memory)) {
            bank_gems(world, pathing, safety, memory);
            return;
        }
        dash_away(world, pathing, pathing.to_ally_spawn());
        step_safely(pathing, pathing.to_ally_spawn(), safety);
        return;
    }

    const bool holding = holding_capture(world);
    bool attacked = attack_enemy(world);
    if (attacked) reset_and_attack_enemy(world, true);
    cast_at_enemies(world, me.gem_count() > 0 && !holding);
    if (!attacked && !holding && dash_to_attack(world, pathing)) attacked = attack_enemy(world);
    if (attacked) reset_and_attack_enemy(world);
    decision = holding ? 'P' : attacked ? 'A' : decision;
    if (holding) return;
    if (me.gem_count() > 0) {
        const bool safe = can_tribute_safely(world, safety, memory);
        const bool late = endgame(world, pathing);
        if (!safe && !late && chase(world, pathing, safety)) return;
        if (!safe && can_tribute_here(world)) {
            // Hit with nothing to hit back: waiting here only takes more.
            if (memory.damage > 0 && !attack_target(world)) {
                decision = 'R';
                dash_away(world, pathing, pathing.to_ally_spawn());
                step_safely(pathing, pathing.to_ally_spawn(), safety);
                return;
            }
            decision = 'W';
            return; // until they leave or come
        }
        decision = 'B';
        const bool walked = attacked && !world.me().facts().walk_and_attack_independent();
        memory.banking = late || walked || !may_chain(world, safety) || !farm(world, pathing, memory);
        if (memory.banking) bank_gems(world, pathing, safety, memory); // a tribute can still start after a ranged attack
        return;
    }
    if (attacked && !world.me().facts().walk_and_attack_independent()) return;
    if (wants_shop(world, safety, memory)) {
        decision = 'S';
        step_safely(pathing, pathing.to_ally_spawn(), safety);
        return;
    }
    if (chase(world, pathing, safety)) return;
    decision = 'J';
    if (join_rally(world, pathing)) return;
    decision = 'F';
    farm(world, pathing, memory);
}

// Recalling every turn end and cancelling next turn when not wanted makes a wanted recall a
// turn shorter. Damage before then cancels it at no cost.
void start_recall(const World& world) {
    auto& me = cambc::self();
    if (!world.me().alive || me.is_recalling() || me.is_submitting_gems() || me.is_teleporting()
        || world.map().ally_spawn.is_set(me.position()))
        return;
    try {
        me.recall();
    } catch (const cambc::error&) {
    }
}

// From next round, the ally nearest a visible enemy acts first: fights go to the first hit, and a
// stun before the enemy's turn removes it.
void set_turn_order(const World& world) {
    auto& me = cambc::self();
    int priority = 0;
    if (world.me().alive) {
        int nearest = params::chase_radius + 1;
        for (const auto& e : world.enemies)
            if (e.alive && e.visible) nearest = std::min(nearest, dist(me.position(), e.pos));
        priority = params::chase_radius + 1 - nearest;
    }
    try {
        if (priority != me.priority()) me.set_priority(priority);
    } catch (const cambc::error&) {
    }
}

} // namespace

void play_turn(const World& world, Pathing& pathing, Memory& memory) {
    Safety safety{world};
    const float health = world.me().alive ? cambc::self().health() : 0;
    memory.damage = memory.round == world.round - 1 ? std::max(0.0f, memory.health - health) : 0;
    decision = '-';
    const vec2 start = world.me().pos;
    decide(world, pathing, safety, memory);
    if constexpr (debug_fights)
        if (world.me().alive && !world.map().ally_spawn.is_set(start) && fuel_ok(params::end_reserve + 15000))
            if (const auto t = safety.fight(start); t.enemies > 0) log_fight("FF", world, safety, start, t);
    heal_ally(world); // allies in reach after walking
    shield_if_needed(world);
    place_ward(world, pathing, memory); // where we end the turn
    start_recall(world);
    set_turn_order(world);
    memory.round = world.round;
    memory.health = world.me().alive ? cambc::self().health() : 0;
}

} // namespace aph
