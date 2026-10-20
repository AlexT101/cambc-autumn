// Ladder-style sparring bot: aphelios with one champion per camp (claims), farming at home, capture recalls, early retreat from packs, Jungle-Power-Durability builds and altar locks.
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
#include "turn_order.h"
#include "world.h"

namespace aph {

namespace {

using params::max_detour;

constexpr int endgame_horizon = 400; // rounds left before the endgame checks start
constexpr int endgame_margin = 20;   // rounds to spare on the last trip to an altar
constexpr int endgame_slack = 2;     // rounds to spare on a last-chance tribute
constexpr int endgame_shop_rounds = 100; // no shop trips this late: spent gold scores nothing

// The turn's branch, for debug_fights: Chase, Attack, Retreat, Farm, Bank, Wait at an altar,
// Tribute kept / t cancelled, recall Kept / k cancelled, Healing on spawn, rally (J), holding (P),
// Delaying a stun, capture recall (Q).
char decision = '-';

// Read by tools/replay/fight_calibration.py.
void log_fight(const char* tag, const World& world, Safety& safety, vec2 p, const Trade& t, int target = -1) {
    if (!debug_fights || !fuel_ok(params::end_reserve + 15000)) return;
    std::cout << tag << ' ' << world.round << ' ' << static_cast<std::uint32_t>(world.me().handle) << ' ' << p.x << ' ' << p.y
              << ' ' << static_cast<int>(world.me().health) << ' ' << decision << ' ' << t.lost << ' '
              << t.turns_to_kill_us << ' ' << t.turns_to_kill_them << ' ' << t.allies << ' ' << t.enemies << ' '
              << static_cast<int>(t.our_health) << ' ' << static_cast<int>(t.their_health) << ' ' << target << ' '
              << static_cast<int>(safety.camp_damage(p)) << ' ' << safety.lethal(p);
    for (const float d : t.dealt) std::cout << ' ' << static_cast<int>(d);
    for (const auto& a : world.allies)
        if (a.alive && !a.is_self && a.visible && dist(p, a.pos) <= safety_params::fight_ally_radius)
            std::cout << " a" << static_cast<std::uint32_t>(a.handle);
    for (const auto& th : safety.threats())
        if (th.credible() && th.strike.hits(th.distance(p)))
            std::cout << ' ' << static_cast<std::uint32_t>(world.enemies[th.enemy].handle) << (th.visible ? 'v' : 'u') << ':'
                      << th.distance(p) << ':' << static_cast<int>(th.strike.at(th.distance(p))) << ':'
                      << world.round - world.enemies[th.enemy].pos_round;
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

// Focus when a shard's Focus, over the damage spells' multipliers, beats five basic attacks'
// Strength: spells front-load a fight.
int main_stat(const ChampionFacts& f) {
    float spells = 0;
    for (const auto& a : f.abilities)
        if (a.kind == AbilityKind::damage) spells += a.multiplier;
    return f.focus.growth * spells > 5 * f.strength.growth ? focus_stat : strength_stat;
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

// A Jungle emblem (-30% camp damage) in the main stat, a Power emblem (6 shards' stats for 5) in
// it, a Durability emblem (-10% damage taken) in Health, then Power emblems. True if any was bought.
bool buy_shards(const ChampionFacts& f) {
    auto& me = cambc::self();
    unsigned gold = me.gold_count();
    if (gold < 30) return false;
    const unsigned start = gold;
    const auto owned = me.item_count();
    const int main = main_stat(f);
    const std::array<std::array<int, 2>, 3> emblems{{{jungle, main}, {power, main}, {durability, health_stat}}};
    for (const auto [family, stat] : emblems) {
        const unsigned have = owned[shard_of(family, stat)] + 5 * owned[emblem_of(family, stat)];
        if (have >= 5) continue;
        const unsigned count = std::min<unsigned>(5 - have, gold / 30);
        if (!buy(shard_of(family, stat), count)) return gold < start;
        gold -= 30 * count;
        if (have + count < 5) return true;
    }
    return (gold >= 30 && buy(shard_of(power, main), gold / 30)) || gold < start;
}

// Locks on our own and middle altars keep the enemy's bags from scoring there until broken.
void buy_lock() {
    auto& me = cambc::self();
    try {
        if (me.can_buy(cambc::consumable_type::altar_lock)) me.buy(cambc::consumable_type::altar_lock);
    } catch (const cambc::error&) {
    }
}

bool channelling() {
    const auto& me = cambc::self();
    return me.is_recalling() || me.is_submitting_gems() || me.is_teleporting();
}

void place_lock(const World& world) {
    auto& me = cambc::self();
    if (!world.me().alive || channelling()) return;
    const auto& lock = me.consumables()[cambc::consumable_type::altar_lock];
    if (lock.count() == 0) return;
    const auto& map = world.map();
    const vec2 here = me.position();
    for (int a = 0; a < static_cast<int>(map.altars.size()); ++a) {
        const vec2 p = map.altars[a].pos;
        if (dist(here, p) > 2 || world.altars[a].ally_lock) continue;
        if (dist(p, map.ally_spawn_centre) > dist(p, map.enemy_spawn_centre) + 2) continue;
        // Placing one cancels every tribute at the altar, ours included.
        bool tributing = false;
        for (const auto& ally : world.allies)
            tributing |= !ally.is_self && ally.alive && ally.channel == Channel::tribute && dist(ally.pos, p) <= 1;
        if (tributing) continue;
        try {
            if (lock.use(p)) return;
        } catch (const cambc::error&) {
        }
    }
}

bool attack_enemy(const World& world, const ChampionBelief* hold = nullptr) {
    auto& me = cambc::self();
    if (!me.can_attack()) return false;
    const auto target = attack_target(world, false, hold);
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
    for (auto p : positions_within(live_camp_tiles(), me.position(), range)) {
        const int g = map.group_at(p);
        if (g < 0 || !allowed(g)) continue;
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
    if (!cambc::self().can_move()) return;
    if (!safety.avoid_within(cambc::self().position(), safety_params::avoid_radius)) {
        pathing.step_towards(field);
        return;
    }
    const auto avoid = safety.avoid();
    if (!pathing.step_towards(field, &avoid)) pathing.step_towards(field);
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

// Gems still to capture, beyond the bag and the tributes allies in sight are channelling, before
// our tributes reach the win.
int gems_short(const World& world, int bag) {
    int pending = 0;
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && a.channel == Channel::tribute) pending += a.gems;
    return static_cast<int>(cambc::constants::winning_gems) - world.score.ally - bag - pending;
}
int gems_short(const World& world) { return gems_short(world, static_cast<int>(cambc::self().gem_count())); }

// Cassi or Issac: the other body, whose death is ours too.
const ChampionBelief* partner(const World& world) {
    if (world.me().facts().passive != Passive::linked_pair) return nullptr;
    for (const auto& a : world.allies)
        if (!a.is_self && a.facts().passive == Passive::linked_pair) return &a;
    return nullptr;
}

// What a death would hand over: both bags for Cassi and Issac (the partner's as last seen).
int bag_at_stake(const World& world) {
    const auto* p = partner(world);
    return static_cast<int>(cambc::self().gem_count()) + (p && p->alive ? p->gems : 0);
}

// Tributing the bag wins: more gems are worth nothing, only the tribute is.
bool winning_bag(const World& world) { return gems_short(world) <= 0; }

// Our score and every bag the team carries reach the win: farming on only puts the bags at risk.
bool team_wins(const World& world) {
    int gems = world.score.ally;
    for (const auto& a : world.allies) gems += a.is_self ? static_cast<int>(cambc::self().gem_count()) : comms::bag_of(world, a.index);
    return gems >= static_cast<int>(cambc::constants::winning_gems);
}

// A tribute started or kept now is the bag's last chance to score, or wins the game while fleeing
// gives the enemy time to win first: take it at any risk.
bool any_risk(const World& world, int channel_turns) {
    return winning_bag(world) || rounds_left(world) <= channel_turns + endgame_slack;
}

// The bag needs the rest of the game to reach an altar and score.
bool endgame(const World& world, Pathing& pathing) {
    const int bag = cambc::self().gem_count();
    if (bag == 0 || rounds_left(world) > endgame_horizon) return false;
    const int walk = pathing.to_any_altar().at(cambc::self().position());
    return walk != unreachable && rounds_left(world) <= walk + tribute_turns(bag) + endgame_margin;
}

void place_ward(const World& world, Pathing& pathing, Memory& memory);

// At an unlocked altar in reach. The caller judged the turn's start tile safe; anywhere else is
// judged again.
bool submit_here(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    auto& me = cambc::self();
    const vec2 here = me.position();
    const auto& altars = world.map().altars;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
        if (world.altars[a].enemy_lock || dist(here, altars[a].pos) > cambc::constants::submit_gems_range) continue;
        const int turns = tribute_turns(me.gem_count());
        if (here != world.me().pos && !any_risk(world, turns) && !tribute_safe(safety, memory, turns)) return false;
        place_lock(world); // first: it cancels every tribute at its altar
        place_ward(world, pathing, memory); // first: no ward goes down while channelling
        try {
            me.submit_gems(altars[a].pos);
            return true;
        } catch (const cambc::error&) {
        }
    }
    return false;
}

const bitboard* pack_zone(const World& world);

void bank_gems(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    if (submit_here(world, pathing, safety, memory)) return;
    const vec2 here = cambc::self().position();
    const auto& altars = world.map().altars;
    // A pack we would retreat from stands in the way: around it within the usual detour, else
    // wait outside it until it leaves or a recall (recall_to_bank) takes the bag home.
    if (const auto* zone = pack_zone(world)) {
        if (pathing.step_towards(pathing.to_any_altar(), zone)) submit_here(world, pathing, safety, memory);
        return;
    }
    bool any_locked = false;
    for (const auto& a : world.altars) any_locked |= a.enemy_lock;
    // One cached field covers every altar; per-altar fields are needed only to skip locked ones.
    if (!any_locked) {
        if (dash_towards(world, pathing, pathing.to_any_altar()) && submit_here(world, pathing, safety, memory)) return;
        step_safely(pathing, pathing.to_any_altar(), safety);
        submit_here(world, pathing, safety, memory);
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
    if (dash_towards(world, pathing, pathing.to_altar(best)) && submit_here(world, pathing, safety, memory)) return;
    if (world.altars[best].enemy_lock && break_lock(world, best) && !world.me().facts().walk_and_attack_independent()) return;
    step_safely(pathing, pathing.to_altar(best), safety);
    submit_here(world, pathing, safety, memory);
}

// Damage a turn, spells spread over their cooldown.
float output(const ChampionBelief& c) {
    float damage = c.strength;
    for (const auto& a : c.facts().abilities) {
        if (a.kind == AbilityKind::damage) damage += a.multiplier * c.focus / static_cast<float>(ability_cooldown);
        if (a.kind == AbilityKind::attack_reset) damage += c.strength / static_cast<float>(ability_cooldown);
    }
    return damage;
}

// Camps hit a Jungle emblem's owner 30% softer, and a Durability emblem's 10%.
float camp_hit_factor() {
    const auto owned = cambc::self().item_count();
    const auto has = [&](int family) {
        return owned[emblem_of(family, strength_stat)] + owned[emblem_of(family, focus_stat)]
                   + owned[emblem_of(family, health_stat)]
               > 0;
    };
    return (has(jungle) ? 0.7f : 1.0f) * (has(durability) ? 0.9f : 1.0f);
}

constexpr int capture_rounds = 6;
constexpr float stickiness = 1.2f;

// Deaths to champions per 1000 champion-rounds off spawn, by how far a tile lies from our spawn
// towards theirs in tenths of the walk between them (400 ladder games, 2026-10-16).
constexpr std::array<float, 10> death_hazard{0.15f, 0.42f, 0.84f, 1.49f, 2.71f, 3.08f, 5.24f, 6.10f, 9.24f, 9.24f};

// Chance of dying to enemies for each round spent at p.
float hazard(const StaticMap& map, vec2 p) {
    const int us = map.from_ally_spawn().at(p), them = map.from_enemy_spawn().at(p);
    if (us == unreachable || them == unreachable || us + them == 0) return 0;
    const int tenth = std::min(9, 10 * us / (us + them));
    return death_hazard[tenth] / 1000.0f;
}

// What farm reads of each group every turn that the walls fix, kept once read.
struct GroupFacts {
    bool known = false, hazard_known = false;
    float max_health = 0; // summed in member order
    int reach = 0;        // the farthest member from the centre
    float hazard = 0;
    int from_spawn = 0;   // from_ally_spawn() at the centre
    int heal_out = -1;    // from_centre() at our spawn centre, once warmed up
};

GroupFacts& group_facts(const StaticMap& map, int g) {
    static std::vector<GroupFacts> cache;
    if (cache.size() != map.groups.size()) cache.assign(map.groups.size(), {});
    auto& f = cache[g];
    if (!f.known) {
        f.known = true;
        const auto& group = map.groups[g];
        for (const auto& m : group.members) f.max_health += m.max_health, f.reach = std::max(f.reach, dist(group.centre, m.pos));
    }
    return f;
}

// Damage taken clearing a group alone with basic attacks, killing the deadliest first; also
// the rounds it takes.
float min_camp_damage(const CampGroup& group, const CampBelief& belief, float strength, float* rounds) {
    struct Left {
        float health, strength;
    };
    std::array<Left, 16> buffer;
    std::vector<Left> heap;
    Left* left = buffer.data();
    if (group.members.size() > buffer.size()) heap.resize(group.members.size()), left = heap.data();
    int n = 0;
    const bool fresh = belief.state == CampState::respawning;
    for (std::size_t i = 0; i < group.members.size(); ++i) {
        const float hp = fresh ? group.members[i].max_health : belief.health[i];
        if (hp > 0) left[n++] = {hp, group.members[i].strength};
    }
    std::sort(left, left + n,
              [](const Left& a, const Left& b) { return a.strength * b.health > b.strength * a.health; });
    float damage = 0, elapsed = 0;
    for (int i = 0; i < n; ++i) {
        elapsed += std::ceil(left[i].health / strength);
        damage += left[i].strength * (elapsed - 1);
    }
    *rounds = elapsed;
    return damage;
}

// Beliefs about most groups do not change between turns, so neither does this. Two strengths
// are kept per group: ours alone and ours with allies'.
float min_camp_damage(int g, const CampGroup& group, const CampBelief& belief, float strength, float* rounds) {
    struct Entry {
        bool valid = false, fresh = false;
        float strength = 0;
        std::array<float, 8> health{};
        float damage = 0, rounds = 0;
    };
    struct Slots {
        std::array<Entry, 2> entries;
        int recent = 0;
    };
    static std::vector<Slots> cache;
    const auto& health = belief.health;
    if (health.size() > Entry{}.health.size()) return min_camp_damage(group, belief, strength, rounds);
    if (cache.size() <= static_cast<std::size_t>(g)) cache.resize(g + 1);
    auto& [entries, recent] = cache[g];
    const bool fresh = belief.state == CampState::respawning;
    const auto matches = [&](const Entry& e) {
        if (!e.valid || e.fresh != fresh || e.strength != strength) return false;
        for (std::size_t i = 0; i < health.size(); ++i)
            if (e.health[i] != health[i]) return false;
        return true;
    };
    if (!matches(entries[recent])) {
        recent ^= 1;
        if (auto& e = entries[recent]; !matches(e)) {
            e.valid = true;
            e.fresh = fresh;
            e.strength = strength;
            std::copy(health.begin(), health.end(), e.health.begin());
            e.damage = min_camp_damage(group, belief, strength, &e.rounds);
        }
    }
    const auto& e = entries[recent];
    *rounds = e.rounds;
    return e.damage;
}

// Damage spells a turn, spread over their cooldown: they reach 4, past the camps' 3. A ground
// spell hits up to `cover` targets at once.
float spell_output(const ChampionBelief& c, int cover) {
    float damage = 0;
    for (const auto& a : c.facts().abilities)
        if (a.kind == AbilityKind::damage)
            damage += a.multiplier * c.focus / static_cast<float>(ability_cooldown) * static_cast<float>(a.target == Targeting::ground ? cover : 1);
    return damage;
}

// The most damaging members one ground spell's 3x3 can hit. Static, so kept per group.
int aoe_cover(const StaticMap& map, int g) {
    static std::vector<int> cache; // -1 until read
    if (cache.size() != map.groups.size()) cache.assign(map.groups.size(), -1);
    auto& cover = cache[g];
    if (cover < 0) {
        cover = 0;
        const auto& members = map.groups[g].members;
        for (const auto& m : members) {
            if (m.strength <= 0) continue;
            for (int d = -1; d < 8; ++d) {
                const vec2 c = d < 0 ? m.pos : m.pos + directions[d];
                int n = 0;
                for (const auto& o : members) n += o.strength > 0 && dist(c, o.pos) <= 1;
                cover = std::max(cover, n);
            }
        }
    }
    return cover;
}

// Basic attacks a turn, with the reset spread over its cooldown.
float basic_output(const ChampionBelief& c) {
    return c.strength * (c.facts().has_attack_reset() ? 1.0f + 1.0f / static_cast<float>(ability_cooldown) : 1.0f);
}

// Bit i: member i deals no damage and a basic attack of `range` reaches it from a tile more than 3
// from every member that does. Static, so kept per group.
std::uint32_t safe_targets(const StaticMap& map, int g, int range) {
    static std::vector<std::array<std::int64_t, 2>> cache; // -1 until read
    if (cache.size() != map.groups.size()) cache.assign(map.groups.size(), {-1, -1});
    auto& bits = cache[g][range > 1];
    if (bits < 0) {
        bits = 0;
        const auto& members = map.groups[g].members;
        bool mixed = false;
        for (const auto& m : members) mixed |= m.strength <= 0;
        if (mixed) {
            static bitboard open{cambc::uninitialized}, reach{cambc::uninitialized};
            open.clear();
            open |= map.standable;
            for (const auto& m : members) {
                if (m.strength <= 0) continue;
                reach.clear();
                reach.draw_chebyshev(m.pos, m.reach);
                open |= reach;
                open ^= reach; // open & ~reach
            }
            for (std::size_t i = 0; i < members.size() && i < 32; ++i)
                if (members[i].strength <= 0 && any_within(open, members[i].pos, range)) bits |= std::int64_t{1} << i;
        }
    }
    return static_cast<std::uint32_t>(bits);
}

constexpr int spell_range = 4;

// Rounds to clear a group alone without taking a hit: damage spells from 4 on the members that
// attack, basic attacks on the others from out of the attackers' range, or once they are dead.
// Negative if no spell can reach an attacker, or one reaches as far as our spells.
// No tile in sight of an attacker within 4 lies out of every attacker's range: walls are static.
char& spell_blocked(const StaticMap& map, int g) {
    static std::vector<char> blocked;
    if (blocked.size() != map.groups.size()) blocked.assign(map.groups.size(), 0);
    return blocked[g];
}

// `basic`: max(1, basic_output(self)), for callers that have checked spell_output(self, 1) > 0.
float spell_clear_rounds(const StaticMap& map, int g, const CampBelief& belief, const ChampionBelief& self, float basic) {
    if (spell_blocked(map, g)) return -1;
    const auto& members = map.groups[g].members;
    const auto safe = safe_targets(map, g, self.facts().attack_range());
    const bool fresh = belief.state == CampState::respawning;
    float attackers = 0, reachable = 0, rest = 0;
    int live = 0;
    for (std::size_t i = 0; i < members.size(); ++i) {
        const float hp = fresh ? members[i].max_health : belief.health[i];
        if (hp <= 0) continue;
        if (members[i].strength > 0 && members[i].reach >= spell_range) return -1;
        if (members[i].strength > 0) attackers += hp, ++live;
        else if (i < 32 && (safe >> i & 1)) reachable += hp;
        else rest += hp;
    }
    const float spells = spell_output(self, std::min(live, aoe_cover(map, g)));
    if (attackers <= 0 || spells <= 0) return -1;
    return std::max(attackers / spells, reachable / basic) + rest / (basic + spells);
}

// Gems one gold is worth to us if all our time went to clearing: a shard (30 gold) adds its stat's
// growth, which speeds the clears of the gems still to farm before either team reaches the win.
float gold_worth(const World& world, int short_by) {
    const auto& self = world.me();
    const auto& f = self.facts();
    const bool focus = main_stat(f) == focus_stat;
    const float gain = focus ? f.focus.growth / std::max(1.0f, self.focus) : f.strength.growth / std::max(1.0f, self.strength);
    int alive = 0;
    for (const auto& a : world.allies) alive += a.alive;
    const int left = std::max(0, std::min(short_by, static_cast<int>(cambc::constants::winning_gems) - world.score.enemy));
    return gain / 30.0f * static_cast<float>(left) / static_cast<float>(std::max(1, alive));
}

// Our part of the gems a capture we stand on pays: shares are floored, the lowest id gets the rest.
int capture_share(const World& world, int g) {
    const auto& tiles = world.map().groups[g].tiles();
    int sharers = 1;
    bool lowest = true;
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && tiles.is_set(a.pos)) ++sharers, lowest = lowest && a.index > world.me().index;
    const int gems = world.map().groups[g].gems;
    return gems / sharers + (lowest ? gems % sharers : 0);
}

// On a cleared group's tile that no lower-id ally also holds, with no enemy on any of its tiles:
// stepping off loses the capture's progress, and it pays within six rounds.
bool holding_capture(const World& world) {
    const vec2 here = cambc::self().position();
    const int g = world.map().group_at(here);
    if (g < 0 || world.camps[g].state != CampState::cleared || winning_bag(world)) return false;
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

// Clears `g` from out of its attackers' range (spell_clear_rounds): basic attacks on the members
// that deal no damage, damage spells from 4 on the others, waiting there between casts. False if
// it cannot get there, for farm's usual approach.
bool spell_clear(const World& world, Pathing& pathing, int g, int cap, const bitboard* zone) {
    auto& me = cambc::self();
    const auto& map = world.map();
    const auto& group = map.groups[g];
    const auto& belief = world.camps[g];
    const int range = world.me().facts().attack_range();
    std::uint32_t attackers = 0, others = 0;
    for (int i = 0; i < static_cast<int>(group.members.size()) && i < 32; ++i)
        if (belief.health[i] > 0) (group.members[i].strength > 0 ? attackers : others) |= 1u << i;
    // Sight lines from 4 are extra fields: not before the warm-up, which fills the opening turns.
    if (!pathing.centres_ready() || !pathing.prepare_member_tiles(g, range, others, params::end_reserve)
        || !pathing.prepare_member_tiles(g, spell_range, attackers, params::end_reserve))
        return false;
    bitboard danger, basic, spell;
    for (int i = 0; i < static_cast<int>(group.members.size()) && i < 32; ++i) {
        if (attackers >> i & 1) {
            danger.draw_chebyshev(group.members[i].pos, group.members[i].reach);
            spell |= pathing.member_attack_tiles(g, i, spell_range);
        } else if (others >> i & 1) {
            basic |= pathing.member_attack_tiles(g, i, range);
        }
    }
    spell &= map.standable & ~danger;
    if (spell.is_empty()) {
        spell_blocked(map, g) = true;
        return false;
    }
    if (zone) {
        danger |= *zone;
        spell &= ~*zone;
    }
    basic &= map.standable & ~danger;
    const auto both = basic & spell;
    const auto& goals = !both.is_empty() ? both : !basic.is_empty() ? basic : spell;
    if (!goals.is_set(me.position())
        && (!fuel_ok(search_cost_estimate(cap) + params::end_reserve) || !pathing.step_towards(goals, &danger, cap)))
        return false;
    cast_at_camp(world, g, true);
    attack_camp(world, [&](int h) { return h == g; });
    reset_and_attack_camp(world, g);
    return true;
}

// Every group that pays is priced the same way: our part of its gems and gold over the rounds it
// costs us: the walk, any wait for its respawn, the clear, the capture hold, the heal its hits
// will need and the time a death there would cost. The best one is ours to work. Discounting the
// reward itself for enemies that could reach a group (seen ones, or unseen ones at their camps)
// lost 3-20% of games, as did the old discount for distance from our spawn.
//
// Carrying gems, farming on chains a capture onto the bag: it saves the walk to the altar and
// back but keeps the bag at risk for longer. It goes ahead only if the next group, by the time it
// adds to the trip, beats the best cycle starting from the altar; false means bank instead.
bool farm(const World& world, Pathing& pathing, Memory& memory) {
    auto& me = cambc::self();
    const auto& map = world.map();
    const auto& groups = map.groups;
    const int range = world.me().facts().attack_range();
    const float strength = std::max(1.0f, output(world.me())), soften = camp_hit_factor();
    const float max_health = me.max_health();
    const float spare_health = me.health() - params::recall_health_fraction * max_health;
    const int bag = me.gem_count();
    const int short_by = gems_short(world, bag);
    std::uint64_t ally_claims = 0;
    for (const auto& a : world.allies)
        if (const int c = comms::claim_of(world, a.index); !a.is_self && c >= 0 && c < 64) ally_claims |= std::uint64_t{1} << c;
    // An ally's claim makes us its crew rather than its rival, unless we claimed it first.
    const auto taken = [&](int g) { return g < 64 && (ally_claims >> g & 1) && (memory.claim != g || memory.crew); };
    // Groups in passing pay too, but not one whose clear costs more health than we can spare, nor
    // a monolith we did not choose.
    const auto affordable = [&](int g) {
        if (g == memory.farm_group || groups[g].strength <= 0) return true;
        if (groups[g].has_monolith) return false;
        float rounds = 0;
        return soften * min_camp_damage(g, groups[g], world.camps[g], strength, &rounds) <= spare_health || ally_engaged(world, g);
    };
    const bool melee = world.me().facts().walk_and_attack_independent();
    // A ranged hit in passing costs the walk: only for our choice, or gems no ally will clear.
    const auto passing = [&](int g) {
        if (!affordable(g)) return false;
        if (g == memory.farm_group) return true;
        if (taken(g)) return false;
        return melee || groups[g].gems > 0;
    };
    const auto attack_in_range = [&] {
        const int hit = attack_camp(world, passing);
        if (hit >= 0 && hit != memory.claim) {
            memory.crew = taken(hit);
            memory.claim = hit;
        }
        if (hit < 0 || melee) return false; // walk on
        cast_at_camp(world, hit);
        reset_and_attack_camp(world, hit);
        return true;
    };
    if (bag == 0 && attack_in_range()) return true;

    // One holder keeps a capture going, and sharers split the reward: the lowest id stays.
    const auto ally_holding = [&](int g, bool lower_only) {
        const int reach = group_facts(map, g).reach;
        for (const auto& a : world.allies)
            if (!a.is_self && a.alive && a.visible && dist(a.pos, groups[g].centre) <= reach && groups[g].tiles().is_set(a.pos)
                && (!lower_only || a.index < world.me().index))
                return true;
        return false;
    };

    const vec2 here = me.position();
    if (holding_capture(world)) return true;
    // Carrying, whatever made us retreat stays out of bounds: we route around it or wait outside
    // it rather than step in to be sent back out. Empty-handed, a step in risks nothing (the zone
    // starts beyond any strike's reach) and keeps us at hand for when the pack moves on, while
    // waiting or farming elsewhere cost about 10 games in 240.
    const auto* zone = bag > 0 ? pack_zone(world) : nullptr;

    // Short of fuel, walk on towards the last choice rather than run out mid-turn.
    const auto walk_on = [&](int g) {
        if (g < 0) return false;
        if (const auto* field = pathing.from_centre(g)) return pathing.descend(*field, zone);
        return pathing.step_closer(groups[g].centre);
    };
    // The loop below measured 0.5-1.5k a group.
    const auto evaluation = (pathing.centres_ready() ? 0 : field_cost_estimate()) + 1000 * groups.size();
    if (!fuel_ok(evaluation + params::end_reserve)) {
        if (bag > 0) return false;
        // On large maps this can last hundreds of rounds, past the last choice's capture: once
        // that is gone, the nearest group as the crow flies.
        const auto worth = [&](int g) {
            const auto& c = world.camps[g];
            return !groups[g].has_monolith && (groups[g].gems > 0 || groups[g].gold > 0) && !taken(g)
                   && !(c.state == CampState::cleared && ally_holding(g, false))
                   && !(c.state == CampState::respawning && c.respawn_round - world.round > dist(here, groups[g].centre));
        };
        if (memory.farm_group < 0 || !worth(memory.farm_group)) {
            memory.farm_group = -1;
            int nearest = 0;
            for (int g = 0; g < static_cast<int>(groups.size()); ++g)
                if (const int d = dist(here, groups[g].centre); (memory.farm_group < 0 || d < nearest) && worth(g))
                    memory.farm_group = g, nearest = d;
        }
        memory.claim = memory.farm_group;
        memory.crew = false;
        walk_on(memory.farm_group);
        return true;
    }
    const auto off_zone = [&](const bitboard& goals) { return zone ? goals & ~*zone : goals; };
    const auto capture = [&](int g, int cap) {
        if (!zone) dash_towards(world, pathing, groups[g].tiles());
        if (fuel_ok(search_cost_estimate(cap) + params::end_reserve)) pathing.step_towards(off_zone(groups[g].tiles()), zone, cap);
        else walk_on(g);
    };
    // A cleared group in sight, ours or one the enemy left, is the nearest free ally's to capture:
    // priced by clearing time below, its gold would be worth nothing.
    int pick = -1, pick_steps = unreachable;
    for (int g = 0; g < static_cast<int>(groups.size()); ++g) {
        const auto& c = world.camps[g];
        if (c.state != CampState::cleared || (groups[g].gems == 0 && groups[g].gold == 0)) continue;
        if (c.state_round < world.round - (g == memory.farm_group ? params::pickup_memory : 0)) continue;
        if (c.holder == team::enemy || taken(g) || ally_holding(g, false)) continue;
        if (zone && (groups[g].tiles() & ~*zone).is_empty()) continue;
        const Field* field = pathing.centres_ready() ? pathing.from_centre(g) : nullptr;
        const auto steps_from = [&](vec2 p) { return field ? field->at(p) : dist(p, groups[g].centre); };
        const int steps = steps_from(here);
        if (steps > params::pickup_steps || steps >= pick_steps) continue;
        bool nearest = true;
        for (const auto& a : world.allies)
            if (!a.is_self && a.alive && a.visible && a.channel == Channel::none && comms::bag_of(world, a.index) == 0) {
                const int d = steps_from(a.pos);
                nearest &= d > steps || (d == steps && a.index > world.me().index);
            }
        if (nearest) pick = g, pick_steps = steps;
    }
    if (pick >= 0) {
        memory.claim = memory.farm_group = pick;
        memory.crew = false;
        capture(pick, pick_steps + max_detour);
        return true;
    }
    // Warmed-up centre fields give the steps a field from here would, without its cost. Walls are
    // static, so the steps are kept while we stand still, as when attacking a camp.
    static std::vector<int> centre_steps; // by group, -1 until read
    static vec2 steps_from{-1, -1};
    static bool steps_warm = false;
    if (here != steps_from || pathing.centres_ready() != steps_warm) {
        steps_from = here;
        steps_warm = pathing.centres_ready();
        centre_steps.assign(groups.size(), -1);
    }
    std::optional<Field> from_here;
    const Field* to_altar = bag > 0 ? &pathing.to_any_altar() : nullptr; // trips matter only when carrying
    const int left = rounds_left(world);
    const Field* deadline = left <= endgame_horizon ? &pathing.to_any_altar() : nullptr;
    // A bag rides a recall home when that reaches an altar sooner (recall_to_bank). Started during
    // a capture, the recall lands as it pays (capture_recall): only the recall's excess over the
    // capture adds to the trip.
    const int recall = world.me().fast_recall ? home_recall_time : static_cast<int>(cambc::constants::recall_time);
    const int spawn_to_altar = to_altar ? to_altar->at(map.ally_spawn_centre) : unreachable;
    const auto homeward = [&](int walk, bool after_capture) {
        if (spawn_to_altar == unreachable) return walk;
        return std::min(walk, spawn_to_altar + (after_capture ? std::max(0, recall - capture_rounds) : recall));
    };
    const int bank_now = to_altar && to_altar->at(here) != unreachable ? homeward(to_altar->at(here), false) : 0;
    const float per_gold = gold_worth(world, short_by);
    // Allies working a group we would join clear it with us: their output while we walk there, and
    // with ours after. The first to claim a group owns it and values it as its own, so that a crew
    // joining does not drive the owner off.
    std::array<int, 8> claims;
    std::array<float, 8> claim_strength;
    int n_claims = 0;
    for (const auto& a : world.allies)
        if (const int c = comms::claim_of(world, a.index); !a.is_self && a.alive && c >= 0 && c < 64 && n_claims < 8)
            claims[n_claims] = c, claim_strength[n_claims++] = std::max(1.0f, output(a));
    const auto crew_strength = [&](int g) {
        float total = 0;
        if (!taken(g)) return total;
        for (int i = 0; i < n_claims; ++i)
            if (claims[i] == g) total += claim_strength[i];
        return total;
    };
    // Health lost to camps comes back only on spawn: each recall line's worth of it costs a recall
    // and the walk back out. Already below what the job takes, we go home first, deficit and all.
    const float usable_health = (1.0f - params::recall_health_fraction) * max_health;
    const float deficit = max_health - me.health();
    const auto heal_rounds = [&](int g, GroupFacts& facts, float damage) {
        if (damage <= 0) return 0.0f;
        if (facts.heal_out < 0)
            if (const auto* field = pathing.from_centre(g)) facts.heal_out = field->at(map.ally_spawn_centre);
        const int out = facts.heal_out >= 0 ? facts.heal_out : dist(map.ally_spawn_centre, groups[g].centre);
        if (out == unreachable) return 0.0f;
        const float owed = damage > spare_health ? damage + deficit : damage;
        return owed / usable_health * static_cast<float>(recall + out);
    };
    const float recall_line = params::recall_health_fraction * max_health;
    const bool casts = spell_output(world.me(), 1) > 0;
    const float basic = std::max(1.0f, basic_output(world.me()));
    int stake = -1;
    int best = -1, best_steps = unreachable;
    float best_value = 0, from_altar_value = 0;
    bool best_spell = false, best_crew = false;
    // First readings of each group (clears, fields) can cost several times the estimate: stop with
    // enough left for the cheapest walk after it (the route falls back to descending a field), and
    // read last turn's choice first so that a cut-short loop still weighs it.
    const int n_groups = static_cast<int>(groups.size());
    const int first = memory.farm_group >= 0 && memory.farm_group < n_groups ? memory.farm_group : 0;
    for (int k = 0; k < n_groups && fuel_ok(small_cost_estimate + params::end_reserve); ++k) {
        const int g = (first + k) % n_groups;
        const auto& group = groups[g];
        const auto& belief = world.camps[g];
        // Staying with last turn's choice keeps near ties from turning us back and forth.
        const float weight = g == memory.farm_group ? stickiness : 1.0f;
        const float gems = weight * static_cast<float>(std::min(group.gems, short_by));
        const float gold = weight * per_gold * static_cast<float>(group.gold);
        const float others = crew_strength(g);
        // A crew leaves the hold to whoever stands on the tiles.
        const int hold = others > 0 ? 0 : capture_rounds;
        // No group pays more than its gems and a quarter of its gold over the rounds it takes besides
        // the clear: c rounds of clearing in a cycle of at least those rounds + c make
        // gold * c / cycle^2. Groups that cannot beat the best so far even so are skipped, with room
        // for rounding; empty-handed, those rounds are at least the walk and the hold.
        const bool bounded = gems >= 0 && gold >= 0;
        const auto beaten = [&](float pay, int rounds, float value) {
            return pay <= 0 || (rounds > 0 && pay / static_cast<float>(rounds) < 0.999f * value);
        };
        if (bounded && bag == 0 && beaten(gems + 0.25f * gold, dist(here, group.centre) + hold, best_value)) continue;
        if ((group.gems == 0 && group.gold == 0) || (belief.state == CampState::cleared && ally_holding(g, false))) continue;
        // A cleared group an ally owns is the ally's to hold.
        if (belief.state == CampState::cleared && taken(g)) continue;
        auto& steps_known = centre_steps[g];
        if (steps_known < 0) {
            if (!steps_warm && !from_here) from_here = make_field(map.blocked_for_us, single(here));
            steps_known = steps_warm ? pathing.from_centre(g)->at(here) : from_here->at(group.centre);
        }
        const int steps = steps_known;
        if (steps == unreachable) continue;
        const bool fresh = belief.state == CampState::respawning;
        const int respawn_in = fresh ? std::max(0, belief.respawn_round - world.round) : 0;
        const int wait = std::max(0, respawn_in - steps);
        // Priced like any other rounds, idle waits won out over helping allies and moving on, and
        // cost small maps half their games: wait at most a quarter of a group's respawn (+4.5% of
        // games over 528; a flat 10 rounds did as well but gave up on monoliths; discounting
        // rewards by their delay lost 12-15%).
        if (4 * wait > group.respawn) continue;
        // Carrying, compare whole trips: the gems score only after the walk to an altar and the
        // tribute. Counting those without a bag favours camps near altars, which lost games; but a
        // capture that wins shares that walk with no later one. Gems past the win are worth nothing.
        const bool wins = group.gems >= short_by;
        const Field* to_bank = to_altar ? to_altar : wins ? &pathing.to_any_altar() : nullptr;
        // A recall only goes home: the way out from an altar is walked.
        const int walk = to_bank ? pathing.centre_to_altar(g) : unreachable;
        const int back = to_altar ? homeward(walk, true) : walk;
        // Chained, the gems join the bag's one tribute; from the altar they need their own.
        const int chained_tribute = tribute_turns(bag + group.gems) - (bag > 0 ? tribute_turns(bag) : 0);
        const int bank = back == unreachable ? 0 : back + chained_tribute;
        const int cycle_bank = back == unreachable ? 0 : back + tribute_turns(group.gems);
        const int trip = steps + wait - bank_now + bank;
        auto& facts = group_facts(map, g);
        float health = fresh ? facts.max_health : 0.0f;
        if (belief.state == CampState::alive)
            for (std::size_t i = 0; i < group.members.size(); ++i) health += belief.health[i];
        // With nothing left to clear, the gold pays nothing.
        if (const float pay = health > 0 ? gems + 0.25f * gold : gems;
            bounded && beaten(pay, trip + hold, best_value)
            && (bag == 0 || walk == unreachable || beaten(pay, walk + cycle_bank + hold, from_altar_value)))
            continue;
        // No clear is quicker than its health over the whole crew's output: skip groups that
        // cannot beat the best so far even so.
        const float fastest = health / (strength + others);
        if (best >= 0 && (gems + gold) / (static_cast<float>(trip + hold) + fastest) <= best_value
            && (bag == 0 || (gems + gold) / (static_cast<float>(walk + cycle_bank + hold) + fastest) <= from_altar_value))
            continue;
        // Allies work while we walk; we arrive to what is left, and our part of the reward is the
        // share of its health we take off. Its hits go to whoever stands nearest: allies already in
        // its reach share them, and a melee one takes them all from a ranged champion. Counting only
        // the allies already there as working while we walk lost 10% of games.
        float clear_rounds = 0, damage = 0, part = 1;
        bool spell = false;
        if (health > 0) {
            const int working = std::max(0, steps - respawn_in);
            const float remaining = health - others * static_cast<float>(working);
            if (remaining <= 0) continue;
            float present = 0, dps = 0;
            bool shielded = false;
            for (const auto& a : world.allies)
                if (!a.is_self && a.alive && a.visible && dist(a.pos, group.centre) <= facts.reach + group.reach
                    && group.threat().is_set(a.pos)) {
                    present += std::max(1.0f, output(a));
                    shielded |= !melee && a.facts().walk_and_attack_independent();
                }
            for (std::size_t i = 0; i < group.members.size(); ++i)
                if (fresh || belief.health[i] > 0) dps += soften * group.members[i].strength;
            float best_rate = -1;
            const auto method = [&](float rate, float hits, bool kite) {
                const float rounds = remaining / (rate + others);
                const float method_part = rate * rounds / health;
                const float method_rate = method_part / (static_cast<float>(trip + hold) + rounds + heal_rounds(g, facts, hits));
                if (method_rate > best_rate) best_rate = method_rate, clear_rounds = rounds, part = method_part, damage = hits, spell = kite;
            };
            // Face to face only if leaving at the recall line leaves us alive: hit once there, then
            // each round until out of reach, twice from melee range and once from within ranged reach.
            if (shielded || dps * (melee ? 3.0f : 2.0f) < recall_line) {
                float rounds = 0;
                const float hits = shielded ? 0.0f
                                            : soften * min_camp_damage(g, group, belief, strength + present, &rounds)
                                                  * (remaining / health) * (strength / (strength + present));
                method(strength, hits, false);
            }
            // Spells from out of the camps' range are slower but cost no health.
            if (group.strength > 0 && casts)
                if (const float kite = spell_clear_rounds(map, g, belief, world.me(), basic); kite > 0) method(health / kite, 0, true);
            if (best_rate < 0) continue;
        }
        if (deadline) {
            const int last = pathing.centre_to_altar(g);
            if (last == unreachable
                || static_cast<float>(steps + wait + hold + last + tribute_turns(bag + group.gems)) + clear_rounds > static_cast<float>(left))
                continue;
        }
        const float heal = heal_rounds(g, facts, damage);
        const float share = wins ? 1.0f : part;
        // Enemies kill more the nearer their side we work: a death costs the respawn and the walk
        // back out, and hands over the bag. Out there for half the walk and the whole job.
        if (!facts.hazard_known) {
            facts.hazard_known = true;
            facts.hazard = hazard(map, group.centre);
            facts.from_spawn = map.from_ally_spawn().at(group.centre);
        }
        const int out = facts.from_spawn;
        const float death = facts.hazard * (0.5f * static_cast<float>(steps) + static_cast<float>(wait + hold) + clear_rounds);
        const float death_rounds = out == unreachable ? 0.0f : death * static_cast<float>(cambc::constants::respawn_time + out);
        // Gold buys shards, which speed up clearing: weighted by the share of this cycle spent on it.
        // A constant share (0.25-1) lost 4-8% of games to this.
        const auto worth = [&](float cycle, int at_stake) {
            return (share * (gems + gold * (cycle > 0 ? clear_rounds / cycle : 0.0f)) - death * static_cast<float>(at_stake)) / cycle;
        };
        const float cycle = static_cast<float>(trip + hold) + clear_rounds + heal + death_rounds;
        if (cycle <= 0) continue;
        if (stake < 0) stake = bag_at_stake(world);
        const float value = worth(cycle, stake);
        if (value > best_value) best = g, best_value = value, best_steps = steps, best_spell = spell, best_crew = others > 0;
        if (bag > 0 && walk != unreachable) {
            const int via_altar = fresh ? std::max(0, belief.respawn_round - world.round - bank_now - walk) : 0;
            from_altar_value = std::max(from_altar_value, worth(static_cast<float>(walk + cycle_bank + via_altar + hold) + clear_rounds + heal + death_rounds, 0));
        }
    }
    if (bag > 0 && (best < 0 || best_value <= from_altar_value)) return false;
    if (bag > 0 && attack_in_range()) return true;
    memory.claim = best;
    memory.crew = best_crew;
    if (best < 0) return true;
    memory.farm_group = best;
    const int cap = best_steps + max_detour;
    if (world.camps[best].state == CampState::cleared) {
        capture(best, cap);
        return true;
    }
    if (best_spell && spell_clear(world, pathing, best, cap, zone)) return true;
    if (!pathing.prepare_attack_tiles(best, range, params::end_reserve)) {
        walk_on(best);
        return true;
    }
    auto goals = pathing.attack_tiles(best, range);
    // In range and sight with the attack unspent: our pick may have been refused in passing. A
    // group yet to return has nothing to hit: wait where we stand.
    if (goals.is_set(here) && me.can_attack() && world.camps[best].state == CampState::alive
        && attack_camp(world, [&](int g) { return g == best; }) < 0)
        goals.set(here, false);
    if (goals.is_set(here)) { // attacked from here; stay
        cast_at_camp(world, best);
        reset_and_attack_camp(world, best);
        return true;
    }
    if (!zone && dash_towards(world, pathing, goals) && attack_camp(world, affordable) >= 0) return true;
    const bool walked = fuel_ok(search_cost_estimate(cap) + params::end_reserve)
                            ? pathing.step_towards(off_zone(goals), zone, cap)
                                  || pathing.step_towards(off_zone(groups[best].adjacent()), zone, cap)
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
    std::optional<bitboard> best;
    int best_tiles = 0;
    while (!candidates.is_empty()) {
        const auto& c = map.bush_cluster(first_tile(candidates));
        const int tiles = static_cast<int>((c.tiles & near).count());
        if (tiles > best_tiles) {
            const auto mine = c.tiles & candidates;
            const auto far = mine & deep;
            best = far.is_empty() ? mine : far, best_tiles = tiles;
        }
        candidates &= ~c.tiles;
    }
    if (!best) return false;
    // A teammate's ward unseen in the bush blocks its tile, and allies pick the same tile first.
    for (auto p : Tiles<3>{*best})
        if (try_ward(p, memory)) return true;
    return false;
}

void place_ward(const World& world, Pathing& pathing, Memory& memory) {
    if (!world.me().alive || channelling() || cambc::self().ward_cooldown() > 0) return;
    if (ward_bushes(world, memory) || world.round % params::ward_period != 0) return;
    const vec2 spawn = world.map().ally_spawn_centre;
    std::optional<vec2> best;
    for (auto p : pathing.ward_targets(true).positions())
        if (!best || dist(spawn, p) > dist(spawn, *best)) best = p;
    if (best) try_ward(*best, memory);
}

// Retreating from an awake camp takes its hits anyway, and the clear is lost.
bool finishing_camp(const World& world) {
    if (winning_bag(world)) return false;
    const vec2 here = cambc::self().position();
    const auto& groups = world.map().groups;
    for (int g = 0; g < static_cast<int>(groups.size()); ++g) {
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.awake == Awake::asleep || !groups[g].threat().is_set(here)) continue;
        float rounds = 0;
        const float damage = camp_hit_factor() * min_camp_damage(g, groups[g], c, std::max(1.0f, output(world.me())), &rounds);
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

// Our ground: no farther from our spawn than from theirs.
bool own_ground(const World& world, vec2 p) {
    const auto& map = world.map();
    const int us = map.from_ally_spawn().at(p), them = map.from_enemy_spawn().at(p);
    return us == unreachable || them == unreachable || us <= them;
}

// Ladder teams leave when a group they cannot match comes into view, not at contact: enemies
// seen within `pack_radius` (by us, or by a teammate last round) against us and the allies near
// us, health times damage a side; hurt, we leave at less.
// The tiles where that holds against us and the allies near us now: within `pack_radius` of every
// member of an enemy subset that outmatches us. Retreat starts inside it, and every advance (farm,
// bank, chase, rally) keeps out of it, so what made us retreat cannot pull us straight back in.
const bitboard* pack_zone(const World& world) {
    static int round = -1;
    static bitboard zone;
    static bool any = false;
    if (round != world.round) {
        round = world.round;
        zone.clear();
        any = false;
        const auto& map = world.map();
        const vec2 here = world.me().pos;
        struct Member {
            vec2 pos;
            float health, damage;
        };
        std::array<Member, 8> members{};
        int n = 0;
        for (const auto& e : world.enemies)
            if (n < static_cast<int>(members.size()) && e.alive && e.age(world.round) <= 1 && !map.near_enemy_spawn.is_set(e.pos))
                members[n++] = {e.pos, e.health, output(e)};
        if (n > 0) {
            float our_health = 0, our_damage = 0;
            for (const auto& a : world.allies)
                if (a.alive && (a.is_self || (a.visible && dist(here, a.pos) <= params::pack_ally_radius))) {
                    our_health += a.is_self ? cambc::self().health() : a.health;
                    our_damage += output(a);
                }
            const bool hurt = cambc::self().health() < 0.5f * cambc::self().max_health();
            const float ours = (hurt ? params::hurt_retreat_ratio : params::retreat_ratio) * our_health * our_damage;
            // Only minimal outmatching subsets: a superset's tiles lie within its subsets'.
            std::array<unsigned, 32> minimal{};
            int m = 0;
            const int r = params::pack_radius;
            for (unsigned mask = 1; mask < (1u << n); ++mask) {
                bool covered = false;
                for (int k = 0; k < m && !covered; ++k) covered = (minimal[k] & mask) == minimal[k];
                if (covered) continue;
                float health = 0, damage = 0;
                int x0 = -1 << 20, x1 = 1 << 20, y0 = -1 << 20, y1 = 1 << 20;
                for (int i = 0; i < n; ++i) {
                    if (!(mask >> i & 1)) continue;
                    const auto& e = members[i];
                    health += e.health, damage += e.damage;
                    x0 = std::max(x0, e.pos.x - r), x1 = std::min(x1, e.pos.x + r);
                    y0 = std::max(y0, e.pos.y - r), y1 = std::min(y1, e.pos.y + r);
                }
                if (health * damage <= ours) continue;
                if (m < static_cast<int>(minimal.size())) minimal[m++] = mask;
                if (x0 > x1 || y0 > y1) continue;
                std::optional<bitboard> tiles;
                for (int i = 0; i < n; ++i) {
                    if (!(mask >> i & 1)) continue;
                    if (!tiles) tiles = square(members[i].pos, r);
                    else *tiles &= square(members[i].pos, r);
                }
                zone |= *tiles;
                any = true;
            }
        }
    }
    return any ? &zone : nullptr;
}

bool outmatched(const World& world) {
    const vec2 here = world.me().pos;
    const auto* zone = pack_zone(world);
    if (!zone || !zone->is_set(here)) return false;
    // A capture about to pay is worth finishing while they are still a walk away.
    if (holding_capture(world)) {
        int nearest = unreachable;
        for (const auto& e : world.enemies)
            if (e.alive && e.age(world.round) <= 1) nearest = std::min(nearest, dist(here, e.pos));
        const auto& c = world.camps[world.map().group_at(here)];
        if (nearest > 3 && c.held_since >= 0 && c.held_since + cambc::constants::capture_time + 1 <= world.round + 2) return false;
    }
    return true;
}

// An enemy that could kill us before our next turn overrides finishing a camp or a capture.
bool want_home(const World& world, Safety& safety) {
    const auto& me = cambc::self();
    const vec2 here = me.position();
    if (world.map().ally_spawn.is_set(here)) return false;
    if ((me.health() < params::recall_health_fraction * me.max_health() && !finishing_camp(world) && !holding_capture(world))
        || outmatched(world))
        return true;
    // Short of fuel for the simulation, a lethal tile counts as a lost fight.
    const bool simulate = fuel_ok(safety.fight_cost_estimate() + params::end_reserve);
    return (safety.lethal(here) && (!simulate || safety.fight(here).self_falls))
           || (simulate && visible_threat(world, here) && safety.fight(here).lost);
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
    const auto& near_enemy_spawn = world.map().near_enemy_spawn;
    const auto* zone = pack_zone(world);
    // Cassi or Issac falling takes the other body and both bags: a won fight that costs us is lost.
    const bool linked = partner(world) != nullptr;
    // Quickest first (ties in index order), so fights are simulated only up to the first won.
    std::array<std::pair<float, const ChampionBelief*>, 8> order;
    int n = 0;
    for (const auto& e : world.enemies) {
        if (n == static_cast<int>(order.size()) || !e.alive || !e.visible || dist(here, e.pos) > params::chase_radius
            || near_enemy_spawn.is_set(e.pos))
            continue;
        // Out of reach on its own ground only when hurt: fights at central altars straddle the
        // line, and a beaten enemy otherwise escapes a step across it.
        if (dist(here, e.pos) > range && !own_ground(world, e.pos) && e.health >= 0.5f * e.max_health) continue;
        // Every tile in reach of it would make us retreat at once.
        if (zone && (square(e.pos, range) & ~*zone).is_empty()) continue;
        const float turns = static_cast<float>(std::max(0, dist(here, e.pos) - range)) + e.health / strength;
        int i = n++;
        for (; i > 0 && order[i - 1].first > turns; --i) order[i] = order[i - 1];
        order[i] = {turns, &e};
    }
    // Chasing is optional: leave enough for the walk after it and the turn's end.
    const auto reserve = search_cost_estimate(2 * params::chase_radius) + params::end_reserve;
    for (int i = 0; i < n && fuel_ok(safety.fight_cost_estimate() + reserve); ++i)
        if (const auto t = safety.fight(order[i].second->pos); !t.lost && !(linked && t.self_falls)) return order[i].second;
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
        const auto* zone = pack_zone(world);
        if (fuel_ok(search_cost_estimate(2 * params::chase_radius) + params::end_reserve))
            pathing.step_towards(square(target->pos, range) & world.map().open_for_us & (zone ? ~*zone : ~bitboard{}), zone);
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
    if (d <= params::chase_radius / 2 || d > params::rally_radius || !own_ground(world, rally->pos)
        || !fuel_ok(search_cost_estimate(2 * params::rally_radius) + params::end_reserve))
        return false;
    const auto* zone = pack_zone(world);
    if (zone && zone->is_set(rally->pos)) return false;
    return pathing.step_towards(square(rally->pos, 1) & world.map().open_for_us, zone, 2 * params::rally_radius);
}

bool can_tribute_safely(const World& world, Safety& safety, const Memory& memory) {
    if (!can_tribute_here(world)) return false;
    const int turns = tribute_turns(cambc::self().gem_count());
    return any_risk(world, turns) || tribute_safe(safety, memory, turns);
}

// Only a small bag, out of every credible enemy's reach, and never the gems that would win.
// Cassi's and Issac's bags fall together.
bool may_chain(const World& world, Safety& safety) {
    if (bag_at_stake(world) >= params::chain_bag_limit || winning_bag(world) || can_tribute_here(world)) return false;
    return !safety.any_threat(); // all credible
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

// No enemy seen this round or last could walk into reach before the recall lands: standing
// still to channel while a pack closes in only gets it cancelled.
bool recall_outruns(const World& world) {
    const vec2 here = cambc::self().position();
    const int turns = static_cast<int>(cambc::self().remaining_channel_time());
    for (const auto& e : world.enemies)
        if (e.alive && e.age(world.round) <= 1 && dist(here, e.pos) - turns <= strike(e, next_turn_round(world, e)).reach)
            return false;
    return true;
}

// Ladder teams recall from a capture they hold, timed to land home the turn it pays: the gems
// skip the walk when an altar is nearer by way of home, and the stop heals and shops.
bool capture_recall(const World& world, Pathing& pathing, Safety& safety) {
    auto& me = cambc::self();
    if (!holding_capture(world) || safety.threatened(me.position())) return false;
    const int g = world.map().group_at(me.position());
    const auto& c = world.camps[g];
    if (c.holder != team::ally || c.held_since < 0) return false;
    const int payout = c.held_since + cambc::constants::capture_time + 1;
    const int lands = world.round + me.remaining_channel_time();
    if (lands < payout) return false;
    const auto& to_altar = pathing.to_any_altar();
    const int walk = to_altar.at(me.position()), from_spawn = to_altar.at(world.map().ally_spawn_centre);
    if (walk == unreachable || from_spawn == unreachable) return false;
    const bool wins = capture_share(world, g) >= gems_short(world);
    // Healing is worth nothing once the bag wins: only the quicker way to an altar counts.
    const bool hurt = !wins && me.health() < 0.6f * me.max_health();
    return lands - payout + from_spawn < walk + (hurt ? params::recall_heal_bonus : 0);
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

bool alive_now(const ChampionBelief& b) {
    try {
        return cambc::detail::handle_access::make_champion(b.handle).is_alive();
    } catch (const cambc::error&) {
        return false;
    }
}

// A tribute stunned on its last turn wastes the whole channel: the visible tributer a ready stun
// reaches to wait for, left alone meanwhile, since a hit can make its owner cancel and act. None if
// a tribute in reach could land before our next turn, another enemy could stun or kill us before
// it, or our own bag can go in now.
const ChampionBelief* tribute_to_stun_later(const World& world, Safety& safety, const Memory& memory) {
    const auto& self = world.me();
    const auto& f = self.facts();
    int reach = -1;
    for (int s = 0; s < 2; ++s)
        if (f.abilities[s].stuns && self.ability_ready(s, world.round))
            reach = std::max(reach, f.abilities[s].kind == AbilityKind::attack_reset ? f.attack_range() : f.abilities[s].reach());
    const ChampionBelief* target = nullptr;
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible || e.channel != Channel::tribute || e.facts().passive == Passive::stun_immune
            || dist(self.pos, e.pos) > reach)
            continue;
        // It lands at its owner's next turn start, which can come before ours next round.
        if (e.channel_end_round <= world.round + 1) return nullptr;
        target = &e;
    }
    if (!target || safety.lethal(self.pos) || can_tribute_safely(world, safety, memory)) return nullptr;
    for (const auto& t : safety.threats()) {
        const int d = t.distance(self.pos);
        if (&world.enemies[t.enemy] != target && t.credible() && t.strike.hits(d) && t.strike.stuns[d]) return nullptr;
    }
    return target;
}

void decide(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    auto& me = cambc::self();
    if (me.gem_count() == 0 || !world.me().alive) memory.banking = false;
    if (!world.me().alive) {
        memory.claim = -1;
        buy_shards(world.me().facts()); // the dead can only shop
        buy_lock();
        return;
    }
    if (me.is_teleporting()) return;
    if (me.is_submitting_gems()) {
        decision = 'T';
        const int turns = me.remaining_channel_time();
        if (any_risk(world, turns) || tribute_safe(safety, memory, turns)) return;
        // Damage does not interrupt a tribute: cancelling pays only to flee or to fight back.
        if (memory.damage <= 0 && !want_home(world, safety) && !attack_target(world)
            && (winning_bag(world) || !prey(world, safety)))
            return;
        decision = 't';
        try {
            me.cancel_submit_gems();
        } catch (const std::exception&) {
            return;
        }
    }
    // Read again only after shopping changes our stats.
    std::optional<bool> home;
    if (me.is_recalling()) {
        decision = 'K';
        home = want_home(world, safety);
        if (*home && !safety.threatened(me.position()) && !can_tribute_safely(world, safety, memory)
            && recall_outruns(world))
            return;
        decision = 'k';
        const auto shop = [&] {
            return wants_shop(world, safety, memory) && me.remaining_channel_time() < pathing.to_ally_spawn().at(me.position());
        };
        if (!holding_capture(world) && (recall_to_bank(world, pathing, safety, memory) || shop())) return;
        if (capture_recall(world, pathing, safety)) {
            decision = 'Q';
            return;
        }
        try {
            me.cancel_recall();
        } catch (const std::exception&) {
            return;
        }
    }

    const bool on_spawn = world.map().ally_spawn.is_set(me.position());
    if ((on_spawn || world.me().facts().passive == Passive::remote_shop) && buy_shards(world.me().facts())) home.reset();
    if (on_spawn) buy_lock();
    if (!world.me().can_act(world.round)) return;
    heal_ally(world);
    shield_if_needed(world, memory.farm_group);
    // Healing needs a turn end on spawn; a recall arrives at turn start.
    if (on_spawn && me.health() < me.max_health()) {
        decision = 'H';
        const bool attacked = attack_enemy(world);
        if (attacked) reset_and_attack_enemy(world, true);
        cast_at_enemies(world);
        if (attacked) reset_and_attack_enemy(world);
        return;
    }
    if (home ? *home : want_home(world, safety)) {
        decision = 'R';
        memory.claim = -1;
        memory.banking = me.gem_count() > 0; // a bag in retreat goes on to an altar, by a recall if quicker
        if (world.me().facts().walk_and_attack_independent() && attack_enemy(world)) reset_and_attack_enemy(world, true);
        cast_at_enemies(world, true);
        if (!me.is_alive()) return;
        if (!me.can_attack() || !me.can_cast()) safety.refresh();
        // A tribute survives damage; a recall does not.
        if (can_tribute_safely(world, safety, memory)) {
            bank_gems(world, pathing, safety, memory);
            return;
        }
        // The escape dash shares the one cast: the reset only after it, from a melee attack or a ranged walk.
        dash_away(world, pathing, pathing.to_ally_spawn());
        reset_and_attack_enemy(world);
        step_safely(pathing, pathing.to_ally_spawn(), safety);
        reset_and_attack_enemy(world);
        return;
    }

    const bool holding = holding_capture(world);
    const auto* stun_later = tribute_to_stun_later(world, safety, memory);
    bool attacked = attack_enemy(world, stun_later);
    if (attacked) reset_and_attack_enemy(world, true, stun_later);
    cast_at_enemies(world, me.gem_count() > 0 && !holding, stun_later);
    if (!attacked && !holding && dash_to_attack(world, pathing, nullptr, stun_later)) attacked = attack_enemy(world, stun_later);
    if (attacked) reset_and_attack_enemy(world, false, stun_later);
    decision = holding ? 'P' : attacked ? 'A' : decision;
    if (!me.is_alive()) return;
    if (!me.can_attack() || !me.can_cast()) safety.refresh();
    if (holding) {
        memory.claim = world.map().group_at(me.position());
        memory.crew = false;
        return;
    }
    // A tributer cannot walk out of the stun's reach.
    if (stun_later && alive_now(*stun_later)) {
        decision = 'D';
        return;
    }
    if (me.gem_count() > 0) {
        const bool safe = can_tribute_safely(world, safety, memory);
        const bool late = endgame(world, pathing);
        const bool close = team_wins(world);
        if (!safe && !late && !close && !winning_bag(world) && chase(world, pathing, safety)) return;
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
        memory.banking = late || close || walked || !may_chain(world, safety) || !farm(world, pathing, memory);
        if (memory.banking) bank_gems(world, pathing, safety, memory); // a tribute can still start after a ranged attack
        return;
    }
    if (attacked && !world.me().facts().walk_and_attack_independent()) return;
    if (wants_shop(world, safety, memory)) {
        decision = 'S';
        memory.claim = -1;
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
    if (!world.me().alive || channelling() || world.map().ally_spawn.is_set(me.position()))
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
    decision = '-';
    const vec2 start = world.me().pos;
    decide(world, pathing, safety, memory);
    if constexpr (debug_fights)
        if (world.me().alive && !world.map().ally_spawn.is_set(start) && fuel_ok(params::end_reserve + 15000))
            if (const auto t = safety.fight(start); t.enemies > 0) log_fight("FF", world, safety, start, t);
    heal_ally(world); // allies in reach after walking
    shield_if_needed(world, memory.farm_group);
    place_ward(world, pathing, memory); // where we end the turn
    place_lock(world);
    start_recall(world);
    set_turn_order(world, safety);
    comms::claim(memory.claim);
    comms::bag(world.me().alive ? static_cast<int>(cambc::self().gem_count()) : 0);
    memory.round = world.round;
    memory.health = world.me().alive ? cambc::self().health() : 0;
}

} // namespace aph
