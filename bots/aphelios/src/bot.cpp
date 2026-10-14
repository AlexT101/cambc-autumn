// Placeholder behaviour, roughly the starter bot's. Replace freely.
#include "bot.h"
#include <algorithm>
#include <array>
#include <cmath>
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

bool ally_engaged(const World& world, int group) {
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && world.map().groups[group].threat().is_set(a.pos)) return true;
    return false;
}

// Carrying gems, farming on chains a capture onto the bag: it saves the walk to the altar and
// back but keeps the bag at risk for longer. It goes ahead only if the next group, by the time it
// adds to the trip, beats the best cycle starting from the altar; false means bank instead.
bool farm(const World& world, Pathing& pathing) {
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

    if (!fuel_ok(field_cost_estimate())) return bag == 0;
    bitboard origin;
    origin.set(here, true);
    const Field from_here = make_field(map.blocked_for_us, origin);
    const Field& to_altar = pathing.to_any_altar();
    const int bank_now = bag > 0 && to_altar.at(here) != unreachable ? to_altar.at(here) : 0;
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
        const int steps = from_here.at(group.centre);
        if (steps == unreachable) continue;
        // Skip groups still respawning when we would arrive.
        if (belief.state == CampState::respawning && belief.respawn_round - world.round > steps) continue;
        if (g == help_group && belief.state == CampState::alive && steps <= params::help_radius) help_steps = steps;
        // Carrying, compare whole trips: the gems score only after the walk to an altar and the
        // tribute. Counting those without a bag favours camps near altars, which lost games.
        const int back = to_altar.at(group.centre);
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
            damage = min_camp_damage(group, belief, strength, &clear_rounds);
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
    const int cap = best_steps + max_detour;
    if (world.camps[best].state == CampState::cleared) {
        dash_towards(world, pathing, groups[best].tiles());
        pathing.step_towards(groups[best].tiles(), nullptr, cap);
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
    if (!fuel_ok(search_cost_estimate(cap))) return true;
    if (pathing.step_towards(goals, nullptr, cap) || pathing.step_towards(groups[best].adjacent(), nullptr, cap)) {
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
        const float damage = min_camp_damage(groups[g], c, std::max(1.0f, world.me().strength), &rounds);
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
    const ChampionBelief* best = nullptr;
    float best_turns = 0;
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible || dist(here, e.pos) > params::chase_radius
            || !(enemy_spawn & square(e.pos, 1)).is_empty())
            continue;
        const float turns = static_cast<float>(std::max(0, dist(here, e.pos) - range)) + e.health / strength;
        if (best && turns >= best_turns) continue;
        if (safety.fight(e.pos).lost) continue;
        best = &e, best_turns = turns;
    }
    return best;
}

bool chase(const World& world, Pathing& pathing, Safety& safety) {
    const auto* target = prey(world, safety);
    if (!target) return false;
    auto& me = cambc::self();
    comms::post_rally(world.round, target->pos);
    const int range = world.me().facts().attack_range();
    // A walk alone cannot reach range this turn.
    if (dist(me.position(), target->pos) > range + 1 && me.can_move()) dash_to_attack(world, pathing, target);
    if (dist(me.position(), target->pos) > range && me.can_move())
        pathing.step_towards(square(target->pos, range) & ~world.map().blocked_for_us);
    if (attack_enemy(world)) reset_and_attack_enemy(world);
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
    if (d <= params::chase_radius / 2 || d > params::rally_radius) return false;
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

// With an empty bag, a full emblem's gold rides a recall home: the bot otherwise carries 150+
// gold for long stretches between forced visits, and the stop also heals.
bool shop_trip(const World& world, Safety& safety, const Memory& memory) {
    auto& me = cambc::self();
    if (me.gem_count() > 0 || me.gold_count() < params::shop_trip_gold || memory.damage > 0
        || world.me().facts().passive == Passive::remote_shop || safety.threatened(me.position()))
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
        if (tribute_safe(safety, memory, me.remaining_channel_time())) return;
        try {
            me.cancel_submit_gems();
        } catch (const cambc::error&) {
            return;
        }
    }
    if (me.is_recalling()) {
        if (want_home(world, safety) && !safety.threatened(me.position()) && !can_tribute_safely(world, safety, memory)) return;
        if (recall_to_bank(world, pathing, safety, memory) || shop_trip(world, safety, memory)) return;
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
        memory.banking = walked || !may_chain(world, safety) || !farm(world, pathing);
        if (memory.banking) bank_gems(world, pathing, safety); // a tribute can still start after a ranged attack
        return;
    }
    if (attacked && !world.me().facts().walk_and_attack_independent()) return;
    if (chase(world, pathing, safety)) return;
    if (join_rally(world, pathing)) return;
    farm(world, pathing);
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
    decide(world, pathing, safety, memory);
    shield_if_needed(world);
    start_recall(world);
    set_turn_order(world);
    memory.round = world.round;
    memory.health = world.me().alive ? cambc::self().health() : 0;
}

} // namespace aph
