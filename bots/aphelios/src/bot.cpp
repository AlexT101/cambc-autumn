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

// Strength throughout; Jungle first for -30% camp damage, then Monster, then Power (6 shards' stats).
void buy_shards() {
    using I = cambc::item_type;
    struct Family {
        I shard, emblem;
        int cap;
    };
    static constexpr Family plan[] = {
        {I::jungle_shard_of_strength, I::jungle_emblem_of_strength, 5},
        {I::monster_shard_of_strength, I::monster_emblem_of_strength, 5},
        {I::power_shard_of_strength, I::power_emblem_of_strength, 1 << 20},
    };
    auto& me = cambc::self();
    const auto owned = me.item_count();
    for (const auto& f : plan) {
        const int have = static_cast<int>(owned[f.shard] + 5 * owned[f.emblem]);
        const unsigned count = std::min<unsigned>(f.cap - std::min(have, f.cap), me.gold_count() / I{f.shard}.cost());
        if (!count) continue;
        if (!me.can_buy(f.shard, count)) return;
        try {
            me.buy(f.shard, count);
        } catch (const cambc::error&) {
            return;
        }
    }
}

bool attack_enemy(const World& world) {
    auto& me = cambc::self();
    const vec2 here = me.position();
    const int range = world.me().facts().attack_range();
    const ChampionBelief* target = nullptr;
    for (const auto& e : world.enemies)
        if (e.visible && dist(here, e.pos) <= range && e.retaliation() < me.health()
            && (!target || e.health < target->health))
            target = &e;
    if (!target || !me.can_attack()) return false;
    try {
        me.attack(cambc::vision::champion_at(target->pos));
        return true;
    } catch (const cambc::error&) {
        return false;
    }
}

// The group of the camp attacked, or -1.
int attack_camp(const World& world) {
    auto& me = cambc::self();
    if (!me.can_attack()) return -1;
    const int range = world.me().facts().attack_range();
    const auto& map = world.map();
    for (auto p : (cambc::vision::camp_tiles() & square(me.position(), range)).positions()) {
        const int g = map.group_at(p);
        if (g < 0 || map.groups[g].has_monolith) continue;
        const auto& members = map.groups[g].members;
        for (int i = 0; i < static_cast<int>(members.size()); ++i) {
            if (members[i].pos != p) continue;
            try {
                me.attack(map.groups[g].camp(i));
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

void bank_gems(const World& world, Pathing& pathing, Safety& safety) {
    auto& me = cambc::self();
    dash_towards(world, pathing, pathing.to_any_altar());
    const vec2 here = me.position();
    const auto& altars = world.map().altars;
    bool any_locked = false;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
        any_locked |= world.altars[a].enemy_lock;
        if (world.altars[a].enemy_lock || dist(here, altars[a].pos) > cambc::constants::submit_gems_range) continue;
        try {
            me.submit_gems(altars[a].pos);
            return;
        } catch (const cambc::error&) {
        }
    }
    // One cached field covers every altar; per-altar fields are needed only to skip locked ones.
    if (!any_locked) {
        step_safely(pathing, pathing.to_any_altar(), safety);
        return;
    }
    int best = -1, best_steps = unreachable;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
        if (world.altars[a].enemy_lock) continue;
        const int steps = pathing.to_altar(a).at(here);
        if (steps < best_steps) best = a, best_steps = steps;
    }
    if (best >= 0) step_safely(pathing, pathing.to_altar(best), safety);
}

constexpr int capture_rounds = 6;

// Damage taken clearing a group alone with basic attacks, killing the deadliest first; also
// the rounds it takes.
float min_camp_damage(const CampGroup& group, const CampBelief& belief, float strength, float* rounds) {
    struct Left {
        float health, strength;
    };
    std::array<Left, 8> left{};
    int n = 0;
    const bool fresh = belief.state == CampState::respawning;
    for (std::size_t i = 0; i < group.members.size() && n < static_cast<int>(left.size()); ++i) {
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
    const auto attack_in_range = [&] {
        const int hit = attack_camp(world);
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
    const int on_group = map.group_at(here);
    if (on_group >= 0 && world.camps[on_group].state == CampState::cleared && !ally_holding(on_group, true)) return true;

    // Short of fuel, walk on towards the last choice rather than run out mid-turn.
    const auto walk_on = [&](int g) {
        if (g < 0) return false;
        if (const auto* field = pathing.from_centre(g)) return pathing.descend(*field);
        return pathing.step_closer(groups[g].centre);
    };
    const auto evaluation = (pathing.centres_ready() ? 0 : field_cost_estimate()) + 300 * groups.size();
    if (!fuel_ok(evaluation + params::end_reserve)) {
        if (bag > 0) return false;
        walk_on(memory.farm_group);
        return true;
    }
    // Warmed-up centre fields give the steps a field from here would, without its cost.
    std::optional<Field> from_here;
    if (!pathing.centres_ready()) from_here = make_field(map.blocked_for_us, single(here));
    const Field* to_altar = bag > 0 ? &pathing.to_any_altar() : nullptr; // trips matter only when carrying
    const int bank_now = to_altar && to_altar->at(here) != unreachable ? to_altar->at(here) : 0;
    float from_altar_value = 0;
    // Unaffordable groups only when nothing else is left: idling is worse.
    int best = -1, best_steps = unreachable, risky = -1, risky_steps = unreachable;
    float best_value = 0, risky_value = 0;
    for (int g = 0; g < static_cast<int>(groups.size()); ++g) {
        const auto& group = groups[g];
        const auto& belief = world.camps[g];
        if (group.has_monolith || group.gems == 0 || (belief.state == CampState::cleared && ally_holding(g, false)))
            continue;
        const int steps = from_here ? from_here->at(group.centre) : pathing.from_centre(g)->at(here);
        if (steps == unreachable) continue;
        // Skip groups still respawning when we would arrive.
        if (belief.state == CampState::respawning && belief.respawn_round - world.round > steps) continue;
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
    if (!fuel_ok(pathing.attack_tiles_cost(best, range) + params::end_reserve)) {
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
    if (dash_towards(world, pathing, goals) && attack_camp(world) >= 0) return true;
    const bool walked = fuel_ok(search_cost_estimate(cap) + params::end_reserve)
                            ? pathing.step_towards(goals, nullptr, cap) || pathing.step_towards(groups[best].adjacent(), nullptr, cap)
                            : walk_on(best);
    if (walked) {
        attack_camp(world);
        cast_at_camp(world, best); // only casts that allow walking remain
        reset_and_attack_camp(world, best);
    }
    return true;
}

void place_ward(const World& world, Pathing& pathing) {
    if (world.round % params::ward_period != 0 || cambc::self().ward_cooldown() > 0) return;
    const auto& spawn_field = world.map().from_ally_spawn();
    std::optional<vec2> best;
    int best_steps = -1;
    for (auto p : pathing.ward_targets().positions()) {
        const int steps = spawn_field.at(p);
        if (steps != unreachable && steps > best_steps) best = p, best_steps = steps;
    }
    if (!best) return;
    try {
        cambc::self().place_ward(*best);
    } catch (const cambc::error&) {
    }
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

bool visible_threat(Safety& safety, vec2 p) {
    for (const auto& t : safety.threats())
        if (t.visible && t.strike.hits(t.distance(p))) return true;
    return false;
}

// An enemy that could kill us before our next turn overrides finishing a camp.
bool want_home(const World& world, Safety& safety) {
    const auto& me = cambc::self();
    if (world.map().ally_spawn.is_set(me.position())) return false;
    return (me.health() < params::recall_health_fraction * me.max_health() && !finishing_camp(world))
           || ((safety.lethal(me.position()) || visible_threat(safety, me.position())) && safety.fight(me.position()).lost);
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
    if (attack_enemy(world)) reset_and_attack_enemy(world);
    cast_at_enemies(world);
    return true;
}

// Towards a fight an ally posted this round or last. Within half our vision of it, chase decides
// whether to join.
bool join_rally(const World& world, Pathing& pathing) {
    const auto rally = comms::read().rally;
    if (!rally || rally->round < world.round - 1) return false;
    const vec2 here = cambc::self().position();
    const int d = dist(here, rally->pos);
    if (d <= params::chase_radius / 2 || d > params::rally_radius
        || !fuel_ok(search_cost_estimate(2 * params::rally_radius) + params::end_reserve))
        return false;
    return pathing.step_towards(square(rally->pos, 1) & ~world.map().blocked_for_us, nullptr, 2 * params::rally_radius);
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

bool can_tribute_safely(const World& world, Safety& safety, const Memory& memory) {
    return can_tribute_here(world) && tribute_safe(safety, memory, tribute_turns(cambc::self().gem_count()));
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

void decide(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    auto& me = cambc::self();
    if (me.gem_count() == 0 || !world.me().alive) memory.banking = false;
    if (!world.me().alive) {
        buy_shards(); // the dead can only shop
        return;
    }
    if (me.is_teleporting()) return;
    if (me.is_submitting_gems()) {
        if (tribute_safe(safety, memory, me.remaining_channel_time())) return;
        try {
            me.cancel_submit_gems();
        } catch (const cambc::error&) {
            return;
        }
    }
    if (me.is_recalling()) {
        if (want_home(world, safety) && !safety.threatened(me.position()) && !can_tribute_safely(world, safety, memory)) return;
        if (recall_to_bank(world, pathing, safety, memory)) return;
        try {
            me.cancel_recall();
        } catch (const cambc::error&) {
            return;
        }
    }

    if (world.map().ally_spawn.is_set(me.position()) || world.me().facts().passive == Passive::remote_shop)
        buy_shards();
    heal_ally(world);
    shield_if_needed(world);
    // Healing needs a turn end on spawn; a recall arrives at turn start.
    if (world.map().ally_spawn.is_set(me.position()) && me.health() < me.max_health()) {
        attack_enemy(world);
        return;
    }
    if (want_home(world, safety)) {
        if (world.me().facts().walk_and_attack_independent()) attack_enemy(world);
        cast_at_enemies(world, true);
        // A tribute survives damage; a recall does not.
        if (can_tribute_safely(world, safety, memory)) {
            bank_gems(world, pathing, safety);
            return;
        }
        dash_away(world, pathing, pathing.to_ally_spawn());
        step_safely(pathing, pathing.to_ally_spawn(), safety);
        return;
    }

    bool attacked = attack_enemy(world);
    if (attacked) reset_and_attack_enemy(world, true);
    cast_at_enemies(world, me.gem_count() > 0);
    if (!attacked && dash_to_attack(world, pathing)) attacked = attack_enemy(world);
    if (attacked) reset_and_attack_enemy(world);
    place_ward(world, pathing);
    if (me.gem_count() > 0) {
        const bool safe = can_tribute_safely(world, safety, memory);
        if (!safe && chase(world, pathing, safety)) return;
        if (!safe && can_tribute_here(world)) return; // until they leave or come
        const bool walked = attacked && !world.me().facts().walk_and_attack_independent();
        memory.banking = walked || !may_chain(world, safety) || !farm(world, pathing, memory);
        if (memory.banking) bank_gems(world, pathing, safety); // a tribute can still start after a ranged attack
        return;
    }
    if (attacked && !world.me().facts().walk_and_attack_independent()) return;
    if (chase(world, pathing, safety)) return;
    if (join_rally(world, pathing)) return;
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

} // namespace

void play_turn(const World& world, Pathing& pathing, Memory& memory) {
    Safety safety{world};
    const float health = world.me().alive ? cambc::self().health() : 0;
    memory.damage = memory.round == world.round - 1 ? std::max(0.0f, memory.health - health) : 0;
    decide(world, pathing, safety, memory);
    shield_if_needed(world);
    start_recall(world);
    memory.round = world.round;
    memory.health = world.me().alive ? cambc::self().health() : 0;
}

} // namespace aph
