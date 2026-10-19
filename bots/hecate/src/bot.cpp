// Crews on camps, gold-only camps, team sieges of Monoliths and big shared groups, capture recalls
// that also go shopping, banking every bag once the race is close, and altar locks. Fights are
// taken whatever the numbers, except when hurt or carrying, or against a pack in our own half.
// Champions never stand under camps they cannot outlast, wait at most a few rounds for a camp to
// return, and stun any enemy tribute that would win the game.
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

constexpr int endgame_horizon = 400; // rounds left before the endgame checks start
constexpr int endgame_margin = 20;   // rounds to spare on the last trip to an altar
constexpr int endgame_shop_rounds = 100; // no shop trips this late: spent gold scores nothing
constexpr int endgame_slack = 2;     // rounds to spare on a last-chance tribute
constexpr int siege_stage_radius = camp_attack_range + 2; // just out of a camp's reach

// The turn's branch, for debug_fights: Chase, Attack, Retreat, Farm, Bank, Wait at an altar,
// Tribute kept / t cancelled, recall Kept / k cancelled, Healing on spawn, Shopping trip,
// holding (P), Delaying a stun, capture recall (Q), siege or kite of a big group (G), contest (X).
char decision = '-';
bool sieged = false; // siege() ran this turn

// Read by tools/replay/fight_calibration.py.
void log_fight(const char* tag, const World& world, Safety& safety, vec2 p, const Trade& t, int target = -1) {
    if (!debug_fights || !fuel_ok(end_reserve + 15000)) return;
    std::printf("%s %d %u %d %d %d %c %d %d %d %d %d %d %d %d %d %d", tag, world.round,
                static_cast<std::uint32_t>(world.me().handle), p.x, p.y, static_cast<int>(world.me().health), decision,
                static_cast<int>(t.lost), t.turns_to_kill_us, t.turns_to_kill_them, t.allies, t.enemies,
                static_cast<int>(t.our_health), static_cast<int>(t.their_health), target, static_cast<int>(safety.camp_damage(p)),
                static_cast<int>(safety.lethal(p)));
    for (const float d : t.dealt) std::printf(" %d", static_cast<int>(d));
    for (const auto& a : world.allies)
        if (a.alive && !a.is_self && a.visible && dist(p, a.pos) <= safety_params::fight_ally_radius)
            std::printf(" a%u", static_cast<std::uint32_t>(a.handle));
    for (const auto& th : safety.threats())
        if (th.strike.hits(th.distance(p)))
            std::printf(" %u%c:%d:%d:%d", static_cast<std::uint32_t>(world.enemies[th.enemy].handle), th.visible ? 'v' : 'u',
                        th.distance(p), static_cast<int>(th.strike.at(th.distance(p))), world.round - world.enemies[th.enemy].pos_round);
    std::printf("\n");
}

enum Family { monster, power, durability, treasure, jungle, home, bruiser };
enum StatKind { strength_stat, focus_stat, health_stat };

cambc::item_type shard_of(int family, int stat) {
    return cambc::item_type{static_cast<std::uint32_t>(family * 6 + stat * 2)};
}
cambc::item_type emblem_of(int family, int stat) {
    return cambc::item_type{static_cast<std::uint32_t>(family * 6 + stat * 2 + 1)};
}

// Focus when a shard's Focus, over the damage spells' multipliers, beats its Strength over the
// basic attacks in one cooldown (one a round, plus the reset's). Ren's retaliation also scales
// with Focus, and where big groups fall to spells from out of reach (kite), every spell's Focus counts.
int main_stat(const World& world) {
    const auto& f = world.me().facts();
    float spells = 0;
    for (const auto& a : f.abilities)
        if (a.kind == AbilityKind::damage) spells += a.multiplier;
    if ((world.map().shared_gems && spells > 0) || f.passive == Passive::retaliation) return focus_stat;
    const int attacks = ability_cooldown + (f.has_attack_reset() ? 1 : 0);
    return f.focus.growth * spells > static_cast<float>(attacks) * f.strength.growth ? focus_stat : strength_stat;
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
// it, a Durability emblem (-10% damage taken) in Health, then Power emblems.
std::array<std::array<int, 2>, 3> emblem_order(const World& world) {
    const int main = main_stat(world);
    return {{{jungle, main}, {power, main}, {durability, health_stat}}};
}

// The family and stat of the next emblem buy_shards completes.
std::array<int, 2> next_emblem(const World& world) {
    const auto owned = cambc::self().item_count();
    for (const auto [family, stat] : emblem_order(world)) {
        if (family == jungle && world.map().shared_gems) continue;
        if (owned[shard_of(family, stat)] + 5 * owned[emblem_of(family, stat)] < 5) return {family, stat};
    }
    return {power, main_stat(world)};
}

// True if any shard was bought.
bool buy_shards(const World& world) {
    unsigned gold = my_gold();
    if (gold < shard_price) return false;
    const unsigned start = gold;
    const auto owned = my_items();
    const int main = main_stat(world);
    for (const auto [family, stat] : emblem_order(world)) {
        if (family == jungle && world.map().shared_gems) continue; // kiting takes no camp hits
        const unsigned have = owned[shard_of(family, stat)] + 5 * owned[emblem_of(family, stat)];
        if (have >= 5) continue;
        const unsigned count = std::min<unsigned>(5 - have, gold / shard_price);
        if (!buy(shard_of(family, stat), count)) return gold < start;
        gold -= shard_price * count;
        if (have + count < 5) return true;
    }
    return (gold >= shard_price && buy(shard_of(power, main), gold / shard_price)) || gold < start;
}

// Locks on our own and middle altars keep the enemy's bags from scoring there until broken.
void buy_lock() {
    auto& me = cambc::self();
    try {
        if (me.can_buy(cambc::consumable_type::altar_lock)) me.buy(cambc::consumable_type::altar_lock);
    } catch (const cambc::error&) {
    }
}

// One state read: each is a host call.
bool channelling() {
    using cambc::champion_state;
    const auto state = my_state();
    return state.contains(champion_state::recalling) || state.contains(champion_state::submitting_gems)
           || state.contains(champion_state::teleporting);
}

void place_lock(const World& world) {
    auto& me = cambc::self();
    if (!world.me().alive) return;
    const auto& lock = me.consumables()[cambc::consumable_type::altar_lock];
    if (lock.count() == 0 || channelling()) return;
    const auto& map = world.map();
    const vec2 here = my_position();
    for (int a = 0; a < static_cast<int>(map.altars.size()); ++a) {
        const vec2 p = map.altars[a].pos;
        if (dist(here, p) > 2 || world.altars[a].ally_lock) continue;
        // Placing one also cancels an enemy's tribute there: its bag stays out of the score.
        bool enemy_tribute = false;
        for (const auto& e : world.enemies)
            enemy_tribute |= e.alive && e.visible && e.channel == Channel::tribute && dist(e.pos, p) <= 1;
        if (!enemy_tribute && dist(p, map.ally_spawn_centre) > dist(p, map.enemy_spawn_centre) + 2) continue;
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
    if (!my_can_attack()) return false;
    const auto target = attack_target(world, false, hold);
    if (!target) return false;
    try {
        me.attack(*target);
        return true;
    } catch (const cambc::error&) {
        return false;
    }
}

// A camp in range of a group `allowed` accepts; the group of the camp attacked, or -1. The member
// whose death removes the most damage per hit goes first; Varg's splash wants the one with the
// most live members next to it.
template <class Allowed> int attack_camp(const World& world, Allowed allowed) {
    auto& me = cambc::self();
    if (!my_can_attack()) return -1;
    const int range = world.me().facts().attack_range();
    const vec2 here = my_position();
    if (!camp_in_reach(world, here, range)) return -1;
    const bool splash = world.me().facts().passive == Passive::splash_attack;
    const auto& map = world.map();
    struct Candidate {
        int group, member;
        float score;
    };
    std::array<Candidate, 16> found;
    int n = 0;
    for (auto p : positions_within(live_camp_tiles(), here, range)) {
        const int g = map.group_at(p);
        if (g < 0 || (map.groups[g].has_monolith && g != siege_group()) || !allowed(g)) continue;
        const auto& members = map.groups[g].members;
        const auto& health = world.camps[g].health;
        for (int i = 0; i < static_cast<int>(members.size()); ++i) {
            if (members[i].pos != p) continue;
            const float hp = i < static_cast<int>(health.size()) && health[i] > 0 ? health[i] : members[i].max_health;
            float score = members[i].strength / std::max(1.0f, hp);
            if (splash) {
                int near = 0;
                for (int j = 0; j < static_cast<int>(members.size()); ++j)
                    near += j != i && (j >= static_cast<int>(health.size()) || health[j] > 0) && dist(members[i].pos, members[j].pos) <= 1;
                score += static_cast<float>(near);
            }
            if (n < static_cast<int>(found.size())) found[n++] = {g, i, score};
        }
    }
    std::stable_sort(found.begin(), found.begin() + n, [](const Candidate& a, const Candidate& b) { return a.score > b.score; });
    for (int k = 0; k < n; ++k) {
        try {
            me.attack(map.groups[found[k].group].camp(found[k].member));
            return found[k].group;
        } catch (const cambc::error&) {
        }
    }
    return -1;
}

// Around awake camps and credible enemies when a way exists, else straight. Routes are replanned
// every turn, so only danger near us is worth the extra search.
void step_safely(Pathing& pathing, const Field& field, Safety& safety) {
    if (!my_can_move()) return;
    if (!safety.avoid_within(my_position(), vision_radius)) {
        pathing.step_towards(field);
        return;
    }
    const auto avoid = safety.avoid();
    if (!pathing.step_towards(field, &avoid)) pathing.step_towards(field);
}

// Out of the camps' reach first, along the cheapest neighbour: walking home past an awake camp
// takes a hit every step, while a recall started outside its reach goes home untouched.
bool flee_camps(Pathing& pathing, Safety& safety, const Field& home) {
    if (!my_can_move()) return false;
    const vec2 here = my_position();
    if (safety.camp_damage(here) <= 0) return false;
    const auto& blocked = pathing.blocked();
    std::optional<vec2> best;
    float best_damage = safety.damage_bound(here);
    int best_home = home.at(here);
    for (auto d : directions) {
        const vec2 p = here + d;
        if (!in_bounds(p) || blocked.is_set(p)) continue;
        const float damage = safety.damage_bound(p);
        const int steps = home.at(p);
        if (damage < best_damage || (damage == best_damage && steps < best_home)) best = p, best_damage = damage, best_home = steps;
    }
    return best && pathing.try_move(*best);
}

// Inside danger a route home is only the shortest walk, ties in compass order, which can lead
// along the enemies we flee: take the homeward step that can be hit least, then the nearest home,
// then the farthest from them. A sideways step goes first only when it can be hit less.
void retreat_step(const World& world, Pathing& pathing, Safety& safety, const Field& home) {
    if (!my_can_move()) return;
    const vec2 here = my_position();
    if (!safety.avoid_within(here, vision_radius)) {
        pathing.step_towards(home);
        return;
    }
    const auto avoid = safety.avoid();
    if (!avoid.is_set(here) && pathing.step_towards(home, &avoid)) return;
    const int steps = home.at(here);
    const auto& blocked = pathing.blocked();
    struct Option {
        vec2 p;
        float damage;
        int steps, gap;
    };
    std::array<Option, 8> options;
    int n = 0;
    for (auto d : directions) {
        const vec2 p = here + d;
        if (!in_bounds(p) || blocked.is_set(p)) continue;
        const int s = home.at(p);
        if (s == unreachable || s > steps) continue;
        int gap = unreachable;
        for (const auto& e : world.enemies)
            if (e.alive && e.visible) gap = std::min(gap, dist(p, e.pos));
        options[n++] = {p, safety.damage_bound(p), s, gap};
    }
    std::stable_sort(options.begin(), options.begin() + n, [](const Option& a, const Option& b) {
        if (a.damage != b.damage) return a.damage < b.damage;
        if (a.steps != b.steps) return a.steps < b.steps;
        return a.gap > b.gap;
    });
    for (int i = 0; i < n; ++i)
        if (pathing.try_move(options[i].p)) return;
    pathing.step_towards(home);
}

bool break_lock(const World& world, int altar) {
    auto& me = cambc::self();
    const vec2 p = world.map().altars[altar].pos;
    if (!my_can_attack() || dist(my_position(), p) > world.me().facts().attack_range()) return false;
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

int tribute_turns(int gems) { return std::max(1, (gems + 9) / 10); }

int recall_turns(const World& world) {
    return world.me().fast_recall ? home_recall_time : static_cast<int>(cambc::constants::recall_time);
}

int rounds_left(const World& world) { return static_cast<int>(cambc::constants::max_rounds) - world.round; }

// Gold spent this late scores nothing; Tavi shops anywhere.
bool may_shop(const World& world) {
    return world.me().facts().passive != Passive::remote_shop && rounds_left(world) > endgame_shop_rounds;
}

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

// Tributing the bag wins: more gems are worth nothing, only the tribute is.
bool winning_bag(const World& world) { return gems_short(world) <= 0; }

// The race's end: our score and the team's bags (posted through comms) reach the win,
// or the enemy is near it. Every bag then goes straight to an altar: one still out when either
// team wins is worth nothing.
bool closing(const World& world) {
    const int win = static_cast<int>(cambc::constants::winning_gems);
    int bags = static_cast<int>(my_gems());
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive) bags += std::max(0, comms::bag_of(world, a.index));
    return world.score.ally + bags >= win - params::close_margin || world.score.enemy >= win - params::enemy_close;
}

// A tribute started or kept now is the bag's last chance to score, or wins the game while fleeing
// gives the enemy time to win first: take it at any risk.
bool any_risk(const World& world, int channel_turns) {
    return winning_bag(world) || rounds_left(world) <= channel_turns + endgame_slack;
}

bool tribute_ok(const World& world, Safety& safety, const Memory& memory, int turns) {
    return any_risk(world, turns) || tribute_safe(safety, memory, turns);
}

// The bag needs the rest of the game to reach an altar and score.
bool endgame(const World& world, Pathing& pathing) {
    const int bag = my_gems();
    if (bag == 0 || rounds_left(world) > endgame_horizon) return false;
    const int walk = pathing.to_any_altar().at(my_position());
    return walk != unreachable && rounds_left(world) <= walk + tribute_turns(bag) + endgame_margin;
}

void place_ward(const World& world, Pathing& pathing, Memory& memory);

// At an unlocked altar in reach. The caller judged the turn's start tile safe; anywhere else is
// judged again.
bool submit_here(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    auto& me = cambc::self();
    const vec2 here = my_position();
    const auto& altars = world.map().altars;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
        if (world.altars[a].enemy_lock || dist(here, altars[a].pos) > cambc::constants::submit_gems_range) continue;
        const int turns = tribute_turns(my_gems());
        if (here != world.me().pos && !tribute_ok(world, safety, memory, turns)) return false;
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
    world.throw_if_stale();
    if (submit_here(world, pathing, safety, memory)) return;
    const vec2 here = my_position();
    const auto& altars = world.map().altars;
    // A pack we would retreat from stands in the way: around it within the usual detour, else
    // wait outside it until it leaves or a recall (recall_to_bank) takes the bag home.
    if (const auto* zone = pack_zone(world)) {
        if (pathing.step_towards(pathing.to_any_altar(), zone)) submit_here(world, pathing, safety, memory);
        return;
    }
    // One we gave up waiting at (carry_bag) counts as locked until we could reach another.
    const auto avoided = [&](int a) { return a == memory.avoid_altar && world.round < memory.avoid_until; };
    bool any_locked = false;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) any_locked |= world.altars[a].enemy_lock || avoided(a);
    // One cached field covers every altar; per-altar fields are needed only to skip locked ones.
    // Breaking a lock takes a turn per hit left, about a step each.
    int best = -1;
    if (any_locked) {
        int best_steps = unreachable;
        for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
            if (avoided(a)) continue;
            const auto& belief = world.altars[a];
            int steps = pathing.to_altar(a).at(here);
            if (steps == unreachable) continue;
            if (belief.enemy_lock) steps += belief.enemy_lock_hits > 0 ? belief.enemy_lock_hits : static_cast<int>(cambc::constants::altar_lock_hits);
            if (steps < best_steps) best = a, best_steps = steps;
        }
        any_locked = best >= 0;
    }
    const Field& field = any_locked ? pathing.to_altar(best) : pathing.to_any_altar();
    if (dash_towards(world, pathing, field) && submit_here(world, pathing, safety, memory)) return;
    if (any_locked && world.altars[best].enemy_lock && break_lock(world, best) && !world.me().facts().walk_and_attack_independent())
        return;
    step_safely(pathing, field, safety);
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

// output(), at least 1: a divisor for clear times.
float floored_output(const ChampionBelief& c) { return std::max(1.0f, output(c)); }

// Camps hit a Jungle emblem's owner 30% softer, and a Durability emblem's 10%.
float camp_hit_factor() {
    const auto& owned = my_items();
    const auto has = [&](int family) {
        return owned[emblem_of(family, strength_stat)] + owned[emblem_of(family, focus_stat)]
                   + owned[emblem_of(family, health_stat)]
               > 0;
    };
    return (has(jungle) ? 0.7f : 1.0f) * (has(durability) ? 0.9f : 1.0f);
}

// Rounds from the first hold of a cleared group to its payout.
int capture_rounds() { return cambc::constants::capture_time + 1; }
constexpr float stickiness = 1.2f;

// Damage taken clearing a group alone with basic attacks, killing the deadliest first; also
// the rounds it takes. `reflect`: damage each hit on us returns to its monster (Ren).
float min_camp_damage(const CampGroup& group, const CampBelief& belief, float strength, float* rounds, float reflect = 0) {
    struct Left {
        float health, strength;
    };
    std::array<Left, 16> buffer;
    std::vector<Left> spill;
    Left* left = buffer.data();
    if (group.members.size() > buffer.size()) {
        spill.resize(group.members.size());
        left = spill.data();
    }
    int n = 0;
    const bool fresh = belief.state == CampState::respawning;
    for (std::size_t i = 0; i < group.members.size(); ++i) {
        const float hp = fresh ? group.members[i].max_health : belief.health[i];
        if (hp > 0) left[n++] = {hp, group.members[i].strength};
    }
    std::sort(left, left + n, [](const Left& a, const Left& b) { return a.strength * b.health > b.strength * a.health; });
    float damage = 0, elapsed = 0;
    if (reflect <= 0) {
        for (int i = 0; i < n; ++i) {
            elapsed += std::ceil(left[i].health / strength);
            damage += left[i].strength * (elapsed - 1);
        }
        *rounds = elapsed;
        return damage;
    }
    // Each round we hit the first living target, then every living attacker hits us and takes the
    // reflection. Stepped from one death to the next.
    for (int i = 0; i < n;) {
        const float own = left[i].strength > 0 ? reflect : 0.0f;
        float k = std::max(1.0f, std::ceil(left[i].health / (strength + own)));
        for (int j = i + 1; j < n; ++j)
            if (left[j].health > 0 && left[j].strength > 0) k = std::min(k, std::max(1.0f, std::ceil(left[j].health / reflect)));
        // Our hit in round k fells it before it strikes; otherwise it struck every round.
        const float hits = left[i].health - k * strength - (k - 1) * own <= 0 ? k - 1 : k;
        damage += left[i].strength * hits;
        left[i].health -= k * strength + hits * own;
        for (int j = i + 1; j < n; ++j)
            if (left[j].health > 0 && left[j].strength > 0) damage += left[j].strength * k, left[j].health -= k * reflect;
        elapsed += k;
        while (i < n && left[i].health <= 0) ++i;
    }
    *rounds = elapsed;
    return damage;
}

// Kept per group and strength while the group's belief is unchanged.
float min_camp_damage(const World& world, int g, float strength, float* rounds, float reflect = 0) {
    const auto& group = world.map().groups[g];
    const auto& belief = world.camps[g];
    struct Slots {
        std::uint32_t version = ~0u;
        int count = 0, next = 0;
        std::array<float, 4> strength{}, reflect{}, damage{}, rounds{};
    };
    static std::vector<Slots> cache;
    if (cache.size() <= static_cast<std::size_t>(g)) cache.resize(std::max(world.map().groups.size(), static_cast<std::size_t>(g) + 1));
    auto& c = cache[g];
    if (c.version != belief.version) {
        c.version = belief.version;
        c.count = c.next = 0;
    }
    for (int i = 0; i < c.count; ++i)
        if (c.strength[i] == strength && c.reflect[i] == reflect) {
            *rounds = c.rounds[i];
            return c.damage[i];
        }
    const int i = c.next;
    c.next = (c.next + 1) % static_cast<int>(c.strength.size());
    c.count = std::max(c.count, i + 1);
    c.strength[i] = strength;
    c.reflect[i] = reflect;
    c.damage[i] = min_camp_damage(group, belief, strength, &c.rounds[i], reflect);
    *rounds = c.rounds[i];
    return c.damage[i];
}

// A group's weight by its side of the map: 1 in our half, falling towards the enemy spawn. Kept
// per group.
float home_ground(const StaticMap& map, int g) {
    static std::vector<float> cache; // -1 until read
    if (cache.size() != map.groups.size()) cache.assign(map.groups.size(), -1.0f);
    auto& weight = cache[g];
    if (weight < 0) {
        const int from_us = map.ally_steps(g);
        const int from_them = map.enemy_steps(g);
        weight = 1.0f;
        if (from_us != unreachable && from_them != unreachable) {
            const float share = std::min(1.0f, 2.0f * static_cast<float>(from_them) / static_cast<float>(from_us + from_them));
            weight = std::pow(share, params::home_power);
        }
    }
    return weight;
}

// Damage spells a turn, spread over their cooldown: they reach 4, past the camps' 3.
float spell_output(const ChampionBelief& c) {
    float damage = 0;
    for (const auto& a : c.facts().abilities)
        if (a.kind == AbilityKind::damage) damage += a.multiplier * c.focus / static_cast<float>(ability_cooldown);
    return damage;
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
                reach.draw_chebyshev(m.pos, camp_attack_range);
                open |= reach;
                open ^= reach; // open & ~reach
            }
            for (std::size_t i = 0; i < members.size() && i < 32; ++i)
                if (members[i].strength <= 0 && any_within(open, members[i].pos, range)) bits |= std::int64_t{1} << i;
        }
    }
    return static_cast<std::uint32_t>(bits);
}

// Rounds to clear a group alone without taking a hit: damage spells from 4 on the members that
// attack, basic attacks on the others from out of the attackers' range, or once they are dead.
// Negative if no spell can reach an attacker. `spells` and `basic`: our spell_output and
// basic_output (at least 1), with `range` our attack range.
float spell_clear_rounds(const StaticMap& map, int g, const CampBelief& belief, int range, float spells, float basic) {
    if (spells <= 0) return -1;
    const auto& members = map.groups[g].members;
    const auto safe = safe_targets(map, g, range);
    const bool fresh = belief.state == CampState::respawning;
    float attackers = 0, reachable = 0, rest = 0;
    for (std::size_t i = 0; i < members.size(); ++i) {
        const float hp = fresh ? members[i].max_health : belief.health[i];
        if (hp <= 0) continue;
        if (members[i].strength > 0) attackers += hp;
        else if (i < 32 && (safe >> i & 1)) reachable += hp;
        else rest += hp;
    }
    if (attackers <= 0) return -1;
    return std::max(attackers / spells, reachable / basic) + rest / (basic + spells);
}

// Kept per group while its belief and our output hold.
float spell_clear_rounds(const World& world, int g, int range, float spells, float basic) {
    struct Kept {
        std::uint32_t version = ~0u;
        int range = 0;
        float spells = 0, basic = 0, rounds = 0;
    };
    static std::vector<Kept> kept;
    if (kept.size() <= static_cast<std::size_t>(g)) kept.resize(world.map().groups.size());
    auto& k = kept[g];
    const auto& belief = world.camps[g];
    if (k.version != belief.version || k.range != range || k.spells != spells || k.basic != basic)
        k = {belief.version, range, spells, basic, spell_clear_rounds(world.map(), g, belief, range, spells, basic)};
    return k.rounds;
}

// No clear is quicker than the group's health over our whole output. Kept per group while its
// belief and our output hold.
float fastest_clear(const World& world, int g, float strength) {
    struct Kept {
        std::uint32_t version = ~0u;
        float strength = 0, rounds = 0;
    };
    static std::vector<Kept> kept;
    if (kept.size() <= static_cast<std::size_t>(g)) kept.resize(world.map().groups.size());
    auto& k = kept[g];
    const auto& belief = world.camps[g];
    if (k.version == belief.version && k.strength == strength) return k.rounds;
    const auto& members = world.map().groups[g].members;
    float rounds = 0;
    if (belief.state != CampState::cleared)
        for (std::size_t i = 0; i < members.size(); ++i)
            rounds += (belief.state == CampState::respawning ? members[i].max_health : belief.health[i]) / strength;
    k = {belief.version, strength, rounds};
    return rounds;
}

// Gems one gold is worth to us: a shard (30 gold) adds its stat's growth, which speeds our share
// of the clears of the gems still to farm before either team reaches the win.
float gold_worth(const World& world, int short_by) {
    const auto& self = world.me();
    const auto& f = self.facts();
    const bool focus = main_stat(world) == focus_stat;
    const float gain = focus ? f.focus.growth / std::max(1.0f, self.focus) : f.strength.growth / std::max(1.0f, self.strength);
    int alive = 0;
    for (const auto& a : world.allies) alive += a.alive;
    const int left = std::max(0, std::min(short_by, static_cast<int>(cambc::constants::winning_gems) - world.score.enemy));
    return gain / static_cast<float>(shard_price) * static_cast<float>(left) / static_cast<float>(std::max(1, alive));
}

// Rounds the next emblem (next_emblem) saves us before the race ends: our share of the gems still
// to farm takes about rounds_per_gem each, clear_share of it clearing, which the main stat's gain
// speeds up. A cut in damage taken (Jungle's camp damage, Durability's and more health) cuts heal
// trips, counted at heal_trip_share of the cut.
constexpr float rounds_per_gem = 2.3f;
constexpr float heal_trip_share = 0.5f;
float emblem_gain_rounds(const World& world) {
    const auto& self = world.me();
    const auto& f = self.facts();
    const auto [family, stat] = next_emblem(world);
    float gain = 0;
    if (stat == health_stat) {
        const float add = 5.0f * f.health.growth;
        const float taken = (family == durability ? 0.9f : 1.0f) * self.max_health / std::max(1.0f, self.max_health + add);
        gain = heal_trip_share * (1.0f - taken);
    } else {
        const float now = stat == focus_stat ? self.focus : self.strength;
        const float add = (family == power ? 6.0f : 5.0f) * (stat == focus_stat ? f.focus.growth : f.strength.growth);
        gain = add / std::max(1.0f, now + add);
        if (family == jungle) gain += heal_trip_share * 0.3f;
    }
    int alive = 0;
    for (const auto& a : world.allies) alive += a.alive;
    const int left = std::max(0, std::min(gems_short(world), static_cast<int>(cambc::constants::winning_gems) - world.score.enemy));
    return 2.0f * gain * params::clear_share * rounds_per_gem * static_cast<float>(left) / static_cast<float>(std::max(1, alive));
}

// Allies other than us in sight on `tiles`; with `below`, only those of a lower index.
int allies_on(const World& world, const bitboard& tiles, int below = 1 << 30) {
    int n = 0;
    for (const auto& a : world.allies) n += !a.is_self && a.alive && a.visible && a.index < below && tiles.is_set(a.pos);
    return n;
}

bool enemy_on(const World& world, const bitboard& tiles) {
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && tiles.is_set(e.pos)) return true;
    return false;
}

// Our part of the gems a capture we stand on pays: shares are floored, the lowest id gets the rest.
int capture_share(const World& world, int g) {
    const auto& tiles = world.map().groups[g].tiles();
    const int sharers = 1 + allies_on(world, tiles);
    const bool lowest = allies_on(world, tiles, world.me().index) == 0;
    const int gems = world.map().groups[g].gems;
    return gems / sharers + (lowest ? gems % sharers : 0);
}

// A group other than a Monolith too big for one champion or a crew, like stampede's shared block
// of elk and gem clusters.
bool big_group(const CampGroup& G) { return !G.has_monolith && G.gems >= params::big_gems; }

int holders(const CampGroup& G) {
    if (G.has_monolith) return params::monolith_holders;
    return G.gems >= params::big_gems ? params::big_holders : 1;
}

// On a cleared group's tile that no lower-id ally also holds, with no enemy on any of its tiles:
// stepping off loses the capture's progress, and it pays within six rounds.
bool holding_capture(const World& world) {
    const vec2 here = my_position();
    const int g = world.map().group_at(here);
    if (g < 0 || world.camps[g].state != CampState::cleared || winning_bag(world)) return false;
    const auto& tiles = world.map().groups[g].tiles();
    return allies_on(world, tiles, world.me().index) < holders(world.map().groups[g]) && !enemy_on(world, tiles);
}

bool ally_engaged(const World& world, int group) { return allies_on(world, world.map().groups[group].threat()) > 0; }

// Pathing::attack_tiles once prepared, null if preparing could take the fuel below `floor()`.
// Member tiles are static once prepared, so the union is kept while the same members live.
template <class Floor>
[[gnu::noinline]] const bitboard* farm_attack_tiles(const World& world, Pathing& pathing, int group, int range, Floor floor) {
    static struct {
        int group = -1, range = -1;
        std::uint32_t alive = 0;
        bitboard tiles;
    } kept;
    const auto& health = world.camps[group].health;
    std::uint32_t alive = 0;
    for (std::size_t i = 0; i < health.size() && i < 32; ++i)
        if (health[i] > 0) alive |= 1u << i;
    if (health.size() <= 32 && kept.group == group && kept.range == range && kept.alive == alive) return &kept.tiles;
    if (!pathing.prepare_attack_tiles(group, range, floor())) return nullptr;
    pathing.attack_tiles(group, range, kept.tiles);
    kept.group = health.size() <= 32 ? group : -1, kept.range = range, kept.alive = alive;
    return &kept.tiles;
}

// After our attack killed a group's last monster, walk onto a free camp tile of it within a step,
// unless an ally in sight already stands on one (it holds, and sharing would split the gems).
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
    if (allies_on(world, G.tiles()) > 0) return false;
    const vec2 here = my_position();
    for (const auto d : directions)
        if (in_bounds(here + d) && G.tiles().is_set(here + d) && pathing.try_move(here + d)) return true;
    return false;
}

// Fuel the farm evaluation and the walk after it need: fields from here unless the steps are
// known, about 1000 a group, and the approach to last turn's choice.
std::uint64_t farm_evaluation_reserve(const World& world, Pathing& pathing, const Memory& memory, vec2 here) {
    const auto& map = world.map();
    const int group = memory.farm_group;
    const int range = group >= 0 && group < static_cast<int>(map.groups.size())
        && world.camps[group].state != CampState::cleared ? world.me().facts().attack_range() : 0;
    const bool steps_free = pathing.centres_ready() || (map.ally_spawn.is_set(here) && map.spawn_steps_drafted());
    const auto evaluation = (steps_free ? 0 : field_cost_estimate()) + 1000 * map.groups.size();
    const auto walk = group < 0 || group >= static_cast<int>(map.groups.size()) ? std::uint64_t{0}
        : pathing.approach_cost(group, range);
    return evaluation + walk + end_reserve;
}

// Farm's spell clear (spell_clear_rounds): from a tile within ability range of a live attacker of
// the group but out of every attacker's reach, casting at the attackers, with basic attacks on
// what cannot hit back. False with no such tile or way to one, for the usual approach.
bool spell_clear(const World& world, Pathing& pathing, int g, const bitboard* zone, int cap) {
    const auto& G = world.map().groups[g];
    const auto& c = world.camps[g];
    static bitboard reach{cambc::uninitialized}, goals{cambc::uninitialized};
    reach.clear();
    std::uint32_t attackers = 0;
    for (std::size_t i = 0; i < G.members.size() && i < 32; ++i)
        if (c.health[i] > 0 && G.members[i].strength > 0) {
            attackers |= 1u << i;
            reach.draw_chebyshev(G.members[i].pos, static_cast<float>(camp_attack_range));
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
    const auto hit = [&] {
        cast_at_camp(world, g, true);
        attack_camp(world, [&](int h) { return h == g || world.map().groups[h].strength <= 0; });
        reset_and_attack_camp(world, g);
    };
    if (goals.is_set(my_position())) {
        hit();
        return true;
    }
    if (zone) reach |= *zone;
    if (!pathing.step_towards(goals, &reach, cap)) return false;
    if (!reach.is_set(my_position())) hit();
    return true;
}

// Chebyshev steps from p to the group's nearest camp tile.
int steps_to(const CampGroup& G, vec2 p) {
    int steps = unreachable;
    for (auto t : G.tiles().positions()) steps = std::min(steps, dist(p, t));
    return steps;
}

// Our farm choice or claim, cleared and seen empty this turn, goes to the nearest of the allies in
// sight claiming it (ties to the lower index): one taker, so the others move on rather than split
// the share. Before anything else farm does, since a ranged hit in passing would cost the step.
bool pick_up(const World& world, Pathing& pathing, Memory& memory) {
    auto& me = cambc::self();
    if (!my_can_move() || memory.banking) return false;
    const auto& map = world.map();
    const vec2 here = my_position();
    for (const int g : {memory.farm_group, memory.claim}) {
        if (g < 0 || g >= static_cast<int>(map.groups.size())) continue;
        const auto& G = map.groups[g];
        const auto& c = world.camps[g];
        if (c.state != CampState::cleared || c.state_round != world.round || G.has_monolith || G.gems + G.gold == 0
            || G.tiles().is_set(here) || allies_on(world, G.tiles()) > 0 || enemy_on(world, G.tiles()))
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
        memory.crew = memory.farm_spell = false;
        return pathing.step_towards(G.tiles(), nullptr, steps + max_detour);
    }
    return false;
}

// Carrying gems, farming on chains a capture onto the bag: it saves the walk to the altar and
// back but keeps the bag at risk for longer. It goes ahead only if the next group, by the time it
// adds to the trip, beats the best cycle starting from the altar; false means bank instead.
bool farm(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    world.throw_if_stale();
    if (pick_up(world, pathing, memory)) return true;
    auto& me = cambc::self();
    const auto& map = world.map();
    const auto& groups = map.groups;
    const int range = world.me().facts().attack_range();
    const float strength = floored_output(world.me()), soften = camp_hit_factor(), reflect = world.me().retaliation();
    const float max_health = my_max_health();
    const float spare_health = (my_health() - params::recall_health_fraction * max_health) / params::camp_risk;
    const int bag = my_gems();
    const int short_by = gems_short(world);
    if (world.is_stale()) return true;
    // Groups in passing pay too (gold clusters are never chosen below), but not one whose clear
    // costs more health than we can spare.
    const auto affordable = [&](int g) {
        if (g == memory.farm_group || groups[g].strength <= 0) return true;
        float rounds = 0;
        return soften * min_camp_damage(world, g, strength, &rounds, reflect) <= spare_health || ally_engaged(world, g);
    };
    std::array<std::uint64_t, 4> ally_claims{}; // bit g: comms carries groups below 255
    for (const auto& a : world.allies)
        if (const int c = comms::claim_of(world, a.index); !a.is_self && c >= 0 && c < 256) ally_claims[c >> 6] |= std::uint64_t{1} << (c & 63);
    // An ally's claim makes us its crew rather than its rival, unless we claimed it first.
    const auto taken = [&](int g) {
        return g < 256 && (ally_claims[g >> 6] >> (g & 63) & 1) && (memory.claim != g || memory.crew);
    };
    const bool melee = world.me().facts().walk_and_attack_independent();
    // Cassi farms gold: the team's weakest body takes the harmless gold-only groups.
    const bool gold_farmer = world.me().facts().passive == Passive::linked_pair && !melee;
    // A ranged hit in passing costs the walk: only for our choice, or gems no ally will clear.
    const auto passing = [&](int g) {
        if (!affordable(g)) return false;
        if (g == memory.farm_group) return true;
        if (taken(g)) return false;
        return melee || groups[g].gems > 0 || (gold_farmer && groups[g].strength <= 0);
    };
    const auto attack_in_range = [&] {
        const int hit = attack_camp(world, passing);
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
    if (bag == 0 && attack_in_range()) return true;
    if (world.is_stale()) return true;

    // One holder keeps a capture going, and sharers split the reward.
    const auto ally_holding = [&](int g) { return allies_on(world, groups[g].tiles()) > 0; };

    const vec2 here = my_position();
    if (holding_capture(world)) return true;
    // Carrying, whatever made us retreat stays out of bounds: we route around it or wait outside
    // it rather than step in to be sent back out. Empty-handed, a step in risks nothing (the zone
    // starts beyond any strike's reach) and keeps us at hand for when the pack moves on.
    const auto* zone = bag_at_stake(world) > 0 ? pack_zone(world) : nullptr;

    // Short of fuel, walk on towards the last choice rather than run out mid-turn. Static fields
    // are kept, so after the first walk to a group this costs a descent.
    const auto walk_range = [&](int g) { return world.camps[g].state == CampState::cleared ? 0 : range; };
    const int previous = memory.farm_group;
    const auto walk_on = [&](int g) {
        if (g < 0) return false;
        // Descending it walks around walls and live camps; a live route only helps past allies.
        const auto walk = [&](const Field& field) { return pathing.descend(field, zone) || pathing.step_towards(field, zone); };
        if (const auto* field = pathing.approach(g, walk_range(g), end_reserve)) return walk(*field);
        // Too short of fuel to search the way to a new choice: last turn's, whose way is known.
        if (previous >= 0 && previous != g && pathing.approach_ready(previous, walk_range(previous))) {
            note_shortcut("farm-kept-target");
            memory.farm_group = memory.claim = previous;
            memory.crew = false;
            return walk(*pathing.approach(previous, walk_range(previous), end_reserve));
        }
        if (const auto* centre = pathing.from_centre(g)) return pathing.descend(*centre, zone);
        note_shortcut("crow-flies-farm");
        return pathing.step_closer(groups[g].centre);
    };
    const bool on_spawn = map.ally_spawn.is_set(here);
    // The walk comes before choosing better: fuel for its search is kept back from the evaluation.
    const auto walk_reserve = [&](int g) { return g < 0 ? std::uint64_t{0} : pathing.approach_cost(g, walk_range(g)); };
    if (!fuel_ok(farm_evaluation_reserve(world, pathing, memory, here))) {
        note_shortcut("farm-no-evaluation");
        debug_block({
            if (!pathing.centres_ready() && !(on_spawn && map.spawn_steps_drafted()))
                std::printf("SHORTCUT %d %u farm-no-evaluation-cold\n", world.round, static_cast<unsigned>(world.me().handle));
        });
        if (bag > 0) return false;
        // On large maps this can last hundreds of rounds, past the last choice's capture: once
        // that is gone, the nearest group, as the crow flies until fields are ready.
        const auto steps_to = [&](int g) {
            if (const auto* field = pathing.from_centre(g)) return field->at(here);
            return on_spawn ? map.ally_steps(g) : dist(here, groups[g].centre);
        };
        const auto worth = [&](int g) {
            const auto& c = world.camps[g];
            return !groups[g].has_monolith && groups[g].gems + groups[g].gold > 0 && !taken(g) && !(c.state == CampState::cleared && ally_holding(g))
                   && !(c.state == CampState::respawning && c.respawn_round - world.round > dist(here, groups[g].centre));
        };
        if (memory.farm_group < 0 || !worth(memory.farm_group)) {
            memory.farm_group = -1;
            int nearest = 0;
            for (int g = 0; g < static_cast<int>(groups.size()); ++g)
                if (const int d = steps_to(g); (memory.farm_group < 0 || d < nearest) && worth(g))
                    memory.farm_group = g, nearest = d;
        }
        memory.claim = memory.farm_group;
        memory.crew = false;
        walk_on(memory.farm_group);
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
    const int recall = recall_turns(world);
    const int spawn_to_altar = to_altar ? to_altar->at(map.ally_spawn_centre) : unreachable;
    const auto homeward = [&](int walk, bool after_capture) {
        if (spawn_to_altar == unreachable) return walk;
        return std::min(walk, spawn_to_altar + (after_capture ? std::max(0, recall - capture_rounds()) : recall));
    };
    const int bank_now = to_altar && to_altar->at(here) != unreachable ? homeward(to_altar->at(here), false) : 0;
    float from_altar_value = 0;
    // Unaffordable groups, then allies' claims, only when nothing else is left: idling is worse.
    int best = -1, best_steps = unreachable, risky = -1, risky_steps = unreachable, shared = -1, shared_steps = unreachable;
    bool best_spell = false;
    float best_value = 0, risky_value = 0, shared_value = 0;
    const float per_gold = gold_worth(world, short_by) * (gold_farmer ? params::gold_farmer_weight : 1.0f);
    // An ally in sight clearing its claimed damaging group gets help only if finishing it alone
    // would take it below the recall line: one champion per camp otherwise.
    const auto struggling = [&](int g) {
        for (const auto& a : world.allies) {
            if (a.is_self || !a.alive || !a.visible || comms::claim_of(world, a.index) != g || !groups[g].threat().is_set(a.pos))
                continue;
            float rounds = 0;
            const float damage = min_camp_damage(groups[g], world.camps[g], floored_output(a), &rounds, a.retaliation());
            if (a.health - damage < params::recall_health_fraction * a.max_health) return true;
        }
        return false;
    };
    // Joining allies on a group, our part of its gems is our share of the damage still to deal
    // when we arrive, and of the camps' hits.
    const auto crew_strength = [&](int g) {
        float total = 0;
        for (const auto& a : world.allies)
            if (!a.is_self && a.alive && comms::claim_of(world, a.index) == g) total += floored_output(a);
        return total;
    };
    // A group too costly for us alone is still ours to call if an ally in reach with no claim of
    // its own can join: valued, like a crew's, by our share of the work.
    float partner_output = 0;
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && dist(here, a.pos) <= params::rally_radius && comms::claim_of(world, a.index) < 0)
            partner_output = std::max(partner_output, floored_output(a));
    const int n_groups = static_cast<int>(groups.size());
    // Static per group once read: its centre field (once warm) and that field's steps to our
    // spawn, its home_ground weight and its centre_to_altar steps.
    struct GroupFacts {
        const Field* centre = nullptr;
        int to_spawn = -1;
        float home = -1;
        int to_altar = -1;
    };
    static std::vector<GroupFacts> group_facts;
    if (static_cast<int>(group_facts.size()) != n_groups) group_facts.assign(n_groups, {});
    const auto centre_field = [&](int g) {
        auto& known = group_facts[g];
        if (!known.centre) known.centre = pathing.from_centre(g);
        return known.centre;
    };
    // Health lost to camps comes back only on spawn: a recall and the walk back out.
    const auto heal_rounds = [&](int g, float damage) {
        int out = group_facts[g].to_spawn;
        if (out < 0) {
            const auto* field = centre_field(g);
            out = field ? field->at(map.ally_spawn_centre) : dist(map.ally_spawn_centre, groups[g].centre);
            if (field) group_facts[g].to_spawn = out;
        }
        return out == unreachable ? 0.0f : damage / max_health * static_cast<float>(recall + out);
    };
    const float spells = world.me().facts().ranged ? spell_output(world.me()) : 0.0f, basic = std::max(1.0f, basic_output(world.me()));
    int help_group = -1, help_steps = unreachable;
    // First readings of each group (clears, fields) can cost several times the estimate: stop with
    // enough left for the walk after it, and read last turn's choice first so that a cut-short loop
    // still weighs it.
    const int first = memory.farm_group >= 0 && memory.farm_group < n_groups ? memory.farm_group : 0;
    // Nothing in the loop moves us or changes the fields walk_reserve reads.
    int reserved_for = -2;
    std::uint64_t reserved = 0;
    const auto loop_reserve = [&] {
        const int g = best >= 0 ? best : memory.farm_group;
        if (g != reserved_for) reserved_for = g, reserved = walk_reserve(g);
        return reserved;
    };
    int k = 0;
    for (; k < n_groups && fuel_ok(small_cost_estimate + end_reserve + loop_reserve()); ++k) {
        const int g = (first + k) % n_groups;
        world.throw_if_stale();
        const auto& group = groups[g];
        const auto& belief = world.camps[g];
        if (group.has_monolith || group.gems + group.gold == 0 || (belief.state == CampState::cleared && ally_holding(g)))
            continue;
        auto& steps_known = centre_steps[g];
        if (steps_known < 0) {
            if (steps_warm) {
                steps_known = centre_field(g)->at(here);
            } else if (const auto drafted = map.drafted_spawn_steps(here, g)) {
                steps_known = *drafted;
            } else {
                if (!from_here) from_here = make_field(map.blocked_for_us, single(here));
                steps_known = from_here->at(group.centre);
            }
        }
        const int steps = steps_known;
        if (steps == unreachable) continue;
        // A group still respawning when we would arrive costs the wait there.
        const int wait = belief.state == CampState::respawning ? std::max(0, belief.respawn_round - world.round - steps) : 0;
        if (wait > params::max_wait) continue;
        if (bag == 0 && group.strength > 0 && belief.state == CampState::alive && steps <= params::help_radius
            && steps < help_steps && struggling(g))
            help_group = g, help_steps = steps;
        const bool claimed = taken(g);
        // Carrying, compare whole trips: the gems score only after the walk to an altar and the
        // tribute. Empty-handed, only a capture that wins counts that walk, as no later one shares
        // it. Gems past the win are worth nothing.
        const bool wins = group.gems >= short_by;
        const Field* to_bank = to_altar ? to_altar : wins ? &pathing.to_any_altar() : nullptr;
        // A recall only goes home: the way out from an altar is walked.
        auto& known = group_facts[g];
        if (to_bank && known.to_altar < 0) known.to_altar = pathing.centre_to_altar(g);
        const int walk = to_bank ? known.to_altar : unreachable;
        const int back = to_altar ? homeward(walk, true) : walk;
        // Chained, the gems join the bag's one tribute; from the altar they need their own.
        const int chained_tribute = tribute_turns(bag + group.gems) - (bag > 0 ? tribute_turns(bag) : 0);
        const int bank = back == unreachable ? 0 : back + chained_tribute;
        const int cycle_bank = back == unreachable ? 0 : back + tribute_turns(group.gems);
        const int trip = steps + wait - bank_now + bank;
        // The spawn fields home_ground reads are warm once the centres are.
        if (known.home < 0 && pathing.centres_ready()) known.home = home_ground(map, g);
        float weight = pathing.centres_ready() ? known.home : 1.0f;
        // Staying with last turn's choice keeps near ties from turning us back and forth.
        if (g == memory.farm_group) weight *= stickiness;
        const float gems = weight * static_cast<float>(std::min(group.gems, short_by));
        const float gold = weight * per_gold * static_cast<float>(group.gold);
        // Risky groups matter only while no affordable one is found; skip the costly clearing
        // estimate for groups that cannot beat it even with no clearing. A crew's share can.
        const float fastest = fastest_clear(world, g, strength);
        if (!claimed && best >= 0 && (gems + gold) / (static_cast<float>(trip + capture_rounds()) + fastest) <= best_value
            && (bag == 0 || (gems + gold) / (static_cast<float>(walk + cycle_bank + capture_rounds()) + fastest) <= from_altar_value))
            continue;
        const auto too_late = [&](float clear_rounds) {
            if (!deadline) return false;
            if (known.to_altar < 0) known.to_altar = pathing.centre_to_altar(g);
            const int last = known.to_altar;
            return last == unreachable
                   || static_cast<float>(steps + wait + capture_rounds() + last + tribute_turns(bag + group.gems)) + clear_rounds > static_cast<float>(left);
        };
        // Shards speed up the clears of every later cycle, not this one's: gold is worth its
        // speed-up over the share of the game spent clearing.
        const float worth = gems + gold * params::clear_share;
        if (claimed) {
            if (belief.state == CampState::cleared) continue;
            const bool fresh = belief.state == CampState::respawning;
            float health = 0;
            for (std::size_t i = 0; i < group.members.size(); ++i) health += fresh ? group.members[i].max_health : belief.health[i];
            const float others = crew_strength(g);
            const int working = std::max(0, steps - (fresh ? std::max(0, belief.respawn_round - world.round) : 0));
            const float health_left = health - others * static_cast<float>(working);
            if (health <= 0 || health_left <= 0) continue;
            // A capture that wins the game is the team's, not a share: what counts is how soon.
            const float rounds = health_left / (strength + others), part = wins ? 1.0f : strength * rounds / health;
            if (too_late(rounds)) continue;
            float joint_rounds = 0;
            const float hits = soften * min_camp_damage(world, g, strength + others, &joint_rounds) * (strength * rounds / health);
            if (hits > spare_health) continue;
            // No capture rounds: the claimer holds it, and the crew moves on once it is cleared.
            const float value = worth * part / (static_cast<float>(trip) + rounds);
            if (value > shared_value) shared = g, shared_value = value, shared_steps = steps;
            continue;
        }
        float clear_rounds = 0, damage = 0;
        bool spell = false;
        if (belief.state != CampState::cleared) {
            damage = soften * min_camp_damage(world, g, strength, &clear_rounds, reflect);
            // Clearing with spells from out of the camps' range is slower but costs no health.
            if (group.strength > 0) {
                const float kite = spell_clear_rounds(world, g, range, spells, basic);
                if (kite >= 0 && (damage > spare_health || kite < clear_rounds + heal_rounds(g, damage))) {
                    spell = true;
                    damage = 0;
                    clear_rounds = kite;
                }
            }
        }
        if (too_late(clear_rounds)) continue;
        const float cycle = static_cast<float>(trip) + clear_rounds + capture_rounds();
        float value = worth / cycle;
        if (damage > spare_health && partner_output > 0 && belief.state == CampState::alive) {
            float joint_rounds = 0;
            const float part = strength / (strength + partner_output);
            if (soften * min_camp_damage(world, g, strength + partner_output, &joint_rounds) * part <= spare_health) {
                damage = 0;
                const float joint_cycle = static_cast<float>(trip) + joint_rounds + capture_rounds();
                value = worth * part / joint_cycle;
            }
        }
        if (damage > spare_health && !ally_engaged(world, g)) {
            if (value > risky_value) risky = g, risky_value = value, risky_steps = steps;
        } else {
            if (value > best_value) best = g, best_value = value, best_steps = steps, best_spell = spell;
            if (bag > 0 && walk != unreachable) {
                const int via_altar = belief.state == CampState::respawning ? std::max(0, belief.respawn_round - world.round - bank_now - walk) : 0;
                const float from_altar = static_cast<float>(walk + cycle_bank + via_altar) + clear_rounds + capture_rounds();
                from_altar_value = std::max(from_altar_value, worth / from_altar);
            }
        }
    }
    if (k < n_groups) note_shortcut("farm-partial-evaluation");
    if (bag > 0 && (best < 0 || best_value <= from_altar_value)) return false;
    if (bag > 0 && attack_in_range()) return true;
    if (world.is_stale()) return true;
    if (best < 0) best = risky, best_steps = risky_steps, best_value = risky_value;
    memory.claim = best;
    memory.crew = false;
    memory.farm_spell = best >= 0 && best_spell;
    if (shared >= 0 && (best < 0 || shared_value > best_value))
        best = shared, best_steps = shared_steps, memory.claim = shared, memory.crew = true, memory.farm_spell = false;
    if (help_group >= 0) best = help_group, best_steps = help_steps, memory.claim = help_group, memory.crew = true, memory.farm_spell = false;
    if (best < 0) return true;
    memory.farm_group = best;
    const int cap = best_steps + max_detour;
    const bool search = fuel_ok(search_cost_estimate(cap) + end_reserve);
    // In a scratch board, valid until the next call.
    const auto off_zone = [&](const bitboard& goals) -> const bitboard& {
        if (!zone) return goals;
        static bitboard outside{cambc::uninitialized};
        outside.clear();
        outside |= goals;
        outside |= *zone;
        outside ^= *zone;
        return outside;
    };
    if (world.camps[best].state == CampState::cleared) {
        if (!zone) dash_towards(world, pathing, groups[best].tiles());
        if (search) pathing.step_towards(off_zone(groups[best].tiles()), zone, cap);
        else {
            note_shortcut("farm-no-route");
            walk_on(best);
        }
        return true;
    }
    if (memory.farm_spell && dist(here, groups[best].centre) <= vision_radius + ability_range
        && spell_clear(world, pathing, best, zone, cap))
        return true;
    const auto* tiles = farm_attack_tiles(world, pathing, best, range, [&] { return end_reserve + walk_reserve(best); });
    if (!tiles) {
        note_shortcut("farm-no-attack-tiles");
        walk_on(best);
        return true;
    }
    // In range and sight with the attack unspent: our pick may have been refused in passing.
    std::optional<bitboard> refused;
    if (tiles->is_set(here) && my_can_attack() && attack_camp(world, [&](int g) { return g == best; }) < 0) {
        refused.emplace(*tiles);
        refused->set(here, false);
    }
    const auto& goals = refused ? *refused : *tiles;
    if (goals.is_set(here)) { // attacked from here; stay
        cast_at_camp(world, best);
        reset_and_attack_camp(world, best);
        if (melee) step_onto_cleared(world, pathing, best);
        return true;
    }
    if (!zone && dash_towards(world, pathing, goals) && attack_camp(world, affordable) >= 0) return true;
    const bool walked = fuel_ok(search_cost_estimate(cap) + end_reserve)
                            ? pathing.step_towards(off_zone(goals), zone, cap)
                                  || pathing.step_towards(off_zone(groups[best].adjacent()), zone, cap)
                            : (note_shortcut("farm-no-route"), walk_on(best));
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
    const vec2 here = my_position();
    const auto floor = small_cost_estimate + end_reserve;
    if (here == memory.bushes_watched) return false;
    if (!fuel_ok(floor)) {
        note_shortcut("ward-no-bushes-fuel");
        return false;
    }
    if (!map.near_bushes().is_set(here)) return false;
    if (!map.find_bush_clusters(here, 2, floor)) {
        note_shortcut("ward-no-bushes-clusters");
        return false;
    }
    // Scratch boards: allocating one costs more than the host operations on it.
    static bitboard candidates{cambc::uninitialized}, near{cambc::uninitialized}, inner{cambc::uninitialized},
        scratch{cambc::uninitialized}, best{cambc::uninitialized};
    candidates.clear();
    candidates.draw_chebyshev(here, 2.0f);
    candidates &= map.bushes;
    if (map.bushes.is_set(here)) drop(candidates, map.bush_cluster(here).tiles);
    if (in_bounds(memory.ward) && map.bushes.is_set(memory.ward)) drop(candidates, map.bush_cluster(memory.ward).tiles);
    if (candidates.is_empty()) {
        memory.bushes_watched = here;
        return false;
    }
    drop(candidates, map.enemy_spawn);
    cambc::vision::ward_tiles_into(team::ally, scratch);
    drop(candidates, scratch);
    near.clear();
    near.draw_chebyshev(here, static_cast<float>(ability_range)); // an ability reaches farther than any basic attack
    inner.clear();
    inner.draw_chebyshev(here, 1.0f);
    bool found = false;
    int best_tiles = 0;
    while (!candidates.is_empty()) {
        const auto& c = map.bush_cluster(first_tile(candidates));
        scratch.clear();
        scratch |= c.tiles;
        scratch &= near;
        const int tiles = static_cast<int>(scratch.count());
        if (tiles > best_tiles) {
            best.clear();
            best |= c.tiles;
            best &= candidates; // ours in the cluster
            scratch.clear();
            scratch |= best;
            drop(scratch, inner); // beyond 1
            if (!scratch.is_empty()) best.swap(scratch);
            found = true, best_tiles = tiles;
        }
        drop(candidates, c.tiles);
    }
    if (!found) return false;
    // A teammate's ward unseen in the bush blocks its tile, and allies pick the same tile first.
    for (auto p : Tiles<3>{best})
        if (try_ward(p, memory)) return true;
    return false;
}

void place_ward(const World& world, Pathing& pathing, Memory& memory) {
    world.throw_if_stale();
    if (!world.me().alive || channelling() || cambc::self().ward_cooldown() > 0) return;
    if (ward_bushes(world, memory) || world.round % params::ward_period != 0) return;
    const vec2 spawn = world.map().ally_spawn_centre;
    std::optional<vec2> best;
    for (auto p : pathing.ward_targets().positions())
        if (!best || dist(spawn, p) > dist(spawn, *best)) best = p;
    if (best) try_ward(*best, memory);
}

// A live group, awake or maybe, whose monsters reach p.
bool awake_over(const World& world, int g, vec2 p) {
    const auto& c = world.camps[g];
    return c.state == CampState::alive && c.awake != Awake::asleep && world.map().groups[g].threat().is_set(p);
}

// Retreating from an awake camp takes its hits anyway, and the clear is lost. Every awake group in
// reach counts: a nearly cleared harmless one next to an elk that is hitting us is no reason to stay.
bool finishing_camp(const World& world) {
    if (winning_bag(world)) return false;
    const vec2 here = my_position();
    bool any = false;
    float damage = 0;
    world.each_stirring([&](int g) {
        if (!awake_over(world, g, here)) return;
        float rounds = 0;
        damage += camp_hit_factor() * min_camp_damage(world, g, floored_output(world.me()), &rounds, world.me().retaliation());
        any = true;
    });
    return any && damage < params::finish_camp_health_fraction * my_health();
}

// On a cleared group's tile worth contesting while the enemy holds it or stands on another:
// leaving lets their hold pay.
bool contesting(const World& world) {
    if (winning_bag(world)) return false;
    const vec2 here = my_position();
    const int g = world.map().group_at(here);
    if (g < 0 || world.map().groups[g].gems < params::contest_gems || world.camps[g].state != CampState::cleared) return false;
    return world.camps[g].holder == team::enemy || enemy_on(world, world.map().groups[g].tiles());
}

// The threats' visible part, without building the unseen ones' fields.
bool visible_threat(const World& world, Safety& safety, vec2 p) {
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && dist(p, e.pos) <= Strike::max_reach && safety.strike_of(e).hits(dist(p, e.pos)))
            return true;
    return false;
}

// Our ground: no farther from our spawn than from theirs.
bool own_ground(const World& world, vec2 p) {
    const auto& map = world.map();
    const int us = map.from_ally_spawn().at(p), them = map.from_enemy_spawn().at(p);
    return us == unreachable || them == unreachable || us <= them;
}

constexpr int pack_radius = Strike::max_reach + 1;

// The tiles within pack_radius of every member of an enemy subset (seen this round or
// last) that outmatches us and the allies near us, by health times damage a side; hurt or carrying, at less.
// Retreat starts inside it, and every advance (farm, bank, chase) keeps out of it, so what made us
// retreat cannot pull us straight back in.
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
                    our_health += a.is_self ? my_health() : a.health;
                    our_damage += output(a);
                }
            const bool hurt = my_health() < params::hurt_health_fraction * my_max_health()
                          || bag_at_stake(world) >= params::brake_bag;
            // A pack in our half has come to fight there.
            const bool home = own_ground(world, here);
            const float healthy = home ? params::home_retreat_ratio : params::retreat_ratio;
            const float ours = (hurt ? std::min(healthy, params::hurt_retreat_ratio) : healthy) * our_health * our_damage;
            // Only minimal outmatching subsets: a superset's tiles lie within its subsets'.
            std::array<unsigned, 32> minimal{};
            int m = 0;
            const int r = pack_radius;
            // By mask, each built from the mask without its highest member, so that sums add the
            // members in index order, as a loop over them would.
            struct Subset {
                float health, damage;
                int x0, x1, y0, y1; // the box within r of every member
            };
            static std::array<Subset, (1u << std::tuple_size_v<decltype(members)>)> subsets;
            subsets[0] = {0, 0, -1 << 20, 1 << 20, -1 << 20, 1 << 20};
            static bitboard tiles{cambc::uninitialized}, other{cambc::uninitialized};
            for (unsigned mask = 1; mask < (1u << n); ++mask) {
                const int top = 31 - __builtin_clz(mask);
                const auto& e = members[top];
                const auto& rest = subsets[mask ^ (1u << top)];
                auto& sub = subsets[mask];
                sub = {rest.health + e.health, rest.damage + e.damage, std::max(rest.x0, e.pos.x - r), std::min(rest.x1, e.pos.x + r),
                       std::max(rest.y0, e.pos.y - r), std::min(rest.y1, e.pos.y + r)};
                bool covered = false;
                for (int k = 0; k < m && !covered; ++k) covered = (minimal[k] & mask) == minimal[k];
                if (covered) continue;
                if (sub.health * sub.damage <= ours) continue;
                if (m < static_cast<int>(minimal.size())) minimal[m++] = mask;
                if (sub.x0 > sub.x1 || sub.y0 > sub.y1) continue;
                // The members' squares meet in the box, as do the two squares around the largest and
                // the smallest member coordinates: (x0 + r, y0 + r) and (x1 - r, y1 - r).
                tiles.clear();
                tiles.draw_chebyshev({sub.x0 + r, sub.y0 + r}, static_cast<float>(r));
                other.clear();
                other.draw_chebyshev({sub.x1 - r, sub.y1 - r}, static_cast<float>(r));
                tiles &= other;
                zone |= tiles;
                any = true;
            }
        }
    }
    return any ? &zone : nullptr;
}

// A capture about to pay is worth finishing while they are still a walk away.
bool paying_soon(const World& world) {
    if (!holding_capture(world)) return false;
    const vec2 here = world.me().pos;
    int nearest = unreachable;
    for (const auto& e : world.enemies)
        if (e.alive && e.age(world.round) <= 1) nearest = std::min(nearest, dist(here, e.pos));
    const auto& c = world.camps[world.map().group_at(here)];
    return nearest > 3 && c.held_since >= 0 && c.payout_round() <= world.round + 2;
}

bool outmatched(const World& world) {
    const auto* zone = pack_zone(world);
    return zone && zone->is_set(world.me().pos) && !paying_soon(world);
}

// Rounds of walking until no awake monster can pick us, at most 4.
int camp_exit_rounds(const World& world, Safety& safety, vec2 here) {
    const auto& open = world.map().standable;
    for (int r = 1; r <= 3; ++r)
        for (int dy = -r; dy <= r; ++dy)
            for (int dx = -r; dx <= r; ++dx) {
                if (std::max(std::abs(dx), std::abs(dy)) != r) continue;
                const vec2 p{here.x + dx, here.y + dy};
                if (in_bounds(p) && open.is_set(p) && safety.camp_damage(p) <= 0) return r;
            }
    return 4;
}

// Camps keep hitting while we walk out of their reach: leave while the health still covers that.
// A siege (Memory::siege) keeps its own health limits for the big group's hits.
bool camp_trapped(const World& world, Safety& safety, vec2 here, float health, bool sieging) {
    if (sieging) return false;
    const float dps = safety.camp_damage(here);
    if (dps <= 0) return false;
    const auto exit_cost = [&](int rounds) { return dps * (1.5f * static_cast<float>(rounds) + 1.0f); };
    // The exit takes 1 to 4 rounds: the bounds settle most cases without the search.
    if (health > exit_cost(4)) return false;
    if (health <= exit_cost(1)) return true;
    return health <= exit_cost(camp_exit_rounds(world, safety, here));
}

// A visible enemy that our basic attack and best ready cast kill this turn, after which the rest (and
// the camps) could not kill us before our next turn; -1 if none. Cassi and Issac fall together.
int killable_now(const World& world, Safety& safety) {
    const auto& self = world.me();
    const auto& f = self.facts();
    const vec2 here = my_position();
    const float health = my_health();
    const int range = f.attack_range();
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible || world.map().enemy_spawn.is_set(e.pos)) continue;
        const int d = dist(here, e.pos);
        float cast = 0;
        for (int s = 0; s < 2; ++s) {
            const auto& a = f.abilities[s];
            if (!self.ability_ready(s, world.round)) continue;
            if (a.kind == AbilityKind::attack_reset && d <= range) cast = std::max(cast, self.strength);
            if (a.kind == AbilityKind::damage && d <= a.range()) cast = std::max(cast, a.multiplier * self.focus);
        }
        if ((d <= range ? self.strength : 0.0f) + cast < e.health) continue;
        const bool linked = e.facts().passive == Passive::linked_pair;
        float rest = safety.camp_damage(here);
        for (const auto& t : safety.threats())
            if (t.enemy != e.index && !(linked && world.enemies[t.enemy].facts().passive == Passive::linked_pair))
                rest += t.strike.at(t.distance(here));
        if (rest < health) return e.index;
    }
    return -1;
}

// An enemy that could kill us before our next turn overrides finishing a camp or a capture.
bool want_home(const World& world, Safety& safety, bool sieging) {
    world.throw_if_stale();
    const vec2 here = my_position();
    if (world.map().ally_spawn.is_set(here)) return false;
    const float health = my_health();
    const int kill = killable_now(world, safety);
    const bool low = health < params::recall_health_fraction * my_max_health() && !finishing_camp(world) && !holding_capture(world);
    if ((low && kill < 0)
        || outmatched(world) || camp_trapped(world, safety, here, health, sieging))
        return true;
    // Short of fuel for the simulation, a lethal tile counts as a lost fight.
    const bool simulate = fuel_ok(safety.fight_cost_estimate() + end_reserve);
    if (!simulate && safety.lethal(here)) note_shortcut("home-no-fight-sim");
    if ((kill < 0 && safety.lethal(here) && (!simulate || safety.fight(here).self_falls))
        || (simulate && visible_threat(world, safety, here) && safety.fight(here, kill).lost))
        return true;
    if (kill >= 0) return false;
    if (!simulate || !fuel_ok(2 * safety.fight_cost_estimate() + end_reserve)) {
        note_shortcut("home-no-pursuit");
        return false;
    }
    // Healthy on our own ground, they have no reason to come for us.
    if (paying_soon(world) || (own_ground(world, here) && health >= params::hurt_health_fraction * my_max_health())) return false;
    const auto t = safety.pursuit(here, params::pursuit_steps);
    return t.lost || (partner(world) && t.self_falls);
}

// The tiles a step (or a ready dash) could end on that want_home would leave at once: stopping
// there hands the enemy the first strike. Cassi and Issac also keep off tiles where one would fall.
const bitboard* step_guard(const World& world, Safety& safety) {
    world.throw_if_stale();
    static bitboard guard{cambc::uninitialized};
    const auto& self = world.me();
    const vec2 here = my_position();
    struct Foe {
        vec2 pos;
        Strike strike;
    };
    std::array<Foe, 8> foes;
    int n = 0;
    for (const auto& e : world.enemies)
        if (n < static_cast<int>(foes.size()) && e.alive && e.visible && dist(here, e.pos) <= Strike::max_reach + 2)
            if (const auto& s = safety.strike_of(e); s.reach >= 0) foes[n++] = {e.pos, s};
    if (n == 0) return nullptr;
    int radius = 1;
    for (int s = 0; s < 2; ++s)
        if (self.facts().abilities[s].kind == AbilityKind::dash && self.ability_ready(s, world.round)) radius = 2;
    // Who can hit a tile, and how hard: a tile no worse than ours is as safe as ours.
    const auto exposure = [&](vec2 p, float& damage) {
        unsigned mask = 0;
        damage = 0;
        for (int k = 0; k < n; ++k)
            if (const int d = dist(p, foes[k].pos); foes[k].strike.hits(d)) mask |= 1u << k, damage += foes[k].strike.at(d);
        return mask;
    };
    float here_damage = 0;
    const unsigned here_mask = exposure(here, here_damage);
    const bool linked = partner(world) != nullptr;
    const auto& open = world.map().open_for_us;
    bool any = false;
    for (int dy = -radius; dy <= radius; ++dy)
        for (int dx = -radius; dx <= radius; ++dx) {
            if (dx == 0 && dy == 0) continue;
            const vec2 q{here.x + dx, here.y + dy};
            float damage = 0;
            const unsigned mask = exposure(q, damage);
            if (mask == 0 || ((mask & ~here_mask) == 0 && damage <= here_damage) || !in_bounds(q) || !open.is_set(q)) continue;
            const Trade* known = safety.known_fight(q);
            if (!known && !fuel_ok(safety.fight_cost_estimate() + end_reserve)) {
                note_shortcut("step-guard");
                return any ? &guard : nullptr;
            }
            const auto t = known ? *known : safety.fight(q);
            if (t.lost || (t.self_falls && (linked || safety.lethal(q)))) {
                if (!any) guard.clear();
                guard.set(q);
                any = true;
            }
        }
    return any ? &guard : nullptr;
}

bool can_tribute_here(const World& world) {
    if (my_gems() == 0) return false;
    const vec2 here = my_position();
    const auto& altars = world.map().altars;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a)
        if (!world.altars[a].enemy_lock && dist(here, altars[a].pos) <= cambc::constants::submit_gems_range) return true;
    return false;
}

// Every tile within r of p lies in `zone`.
bool covered(const bitboard& zone, vec2 p, int r) {
    static bitboard outside{cambc::uninitialized};
    outside.clear();
    outside.draw_chebyshev(p, static_cast<float>(r));
    outside |= zone;
    outside ^= zone;
    return outside.is_empty();
}

// The visible enemy quickest to reach and kill among those whose local fight we win even when
// they strike first; never one on or next to its spawn, where it heals.
const ChampionBelief* prey(const World& world, Safety& safety) {
    world.throw_if_stale();
    const auto& me = cambc::self();
    const vec2 here = my_position();
    const int range = world.me().facts().attack_range();
    std::optional<float> strength; // read once a candidate needs it
    const auto& near_enemy_spawn = world.map().near_enemy_spawn;
    const auto* zone = pack_zone(world);
    // Cassi or Issac falling takes the other body and both bags: a won fight that costs us is lost.
    const bool linked = partner(world) != nullptr;
    // Quickest first (ties in index order), so fights are simulated only up to the first won.
    std::array<std::pair<float, const ChampionBelief*>, 8> order;
    int n = 0;
    for (const auto& e : world.enemies) {
        if (n == static_cast<int>(order.size()) || !e.alive || !e.visible || dist(here, e.pos) > vision_radius
            || near_enemy_spawn.is_set(e.pos))
            continue;
        // Out of reach on its own ground only when hurt: fights at central altars straddle the
        // line, and a beaten enemy otherwise escapes a step across it.
        if (dist(here, e.pos) > range && !own_ground(world, e.pos) && e.health >= 0.5f * e.max_health) continue;
        // Every tile in reach of it would make us retreat at once.
        if (zone && covered(*zone, e.pos, range)) continue;
        if (!strength) strength = std::max(1.0f, my_strength());
        const float turns = static_cast<float>(std::max(0, dist(here, e.pos) - range)) + e.health / *strength;
        int i = n++;
        for (; i > 0 && order[i - 1].first > turns; --i) order[i] = order[i - 1];
        order[i] = {turns, &e};
    }
    // Chasing is optional: leave enough for the walk after it and the turn's end.
    const auto reserve = search_cost_estimate(2 * vision_radius) + end_reserve;
    for (int i = 0; i < n; ++i) {
        if (!fuel_ok(safety.fight_cost_estimate() + reserve)) {
            note_shortcut("prey-cut-short");
            break;
        }
        if (const auto t = safety.fight(order[i].second->pos); !t.lost && !(linked && t.self_falls)) return order[i].second;
    }
    return nullptr;
}

bool chase(const World& world, Pathing& pathing, Safety& safety) {
    const auto* target = prey(world, safety);
    if (!target) return false;
    decision = 'C';
    comms::post_rally(target->index);
    if constexpr (debug_fights) log_fight("FC", world, safety, target->pos, safety.fight(target->pos), static_cast<int>(target->handle));
    auto& me = cambc::self();
    const int range = world.me().facts().attack_range();
    // A walk alone cannot reach range this turn.
    if (dist(my_position(), target->pos) > range + 1 && my_can_move()) dash_to_attack(world, pathing, target);
    if (dist(my_position(), target->pos) > range && my_can_move()) {
        const auto* zone = pack_zone(world);
        static bitboard goals{cambc::uninitialized};
        goals.clear();
        goals.draw_chebyshev(target->pos, static_cast<float>(range));
        goals &= world.map().open_for_us;
        if (zone) drop(goals, *zone);
        pathing.step_towards(goals, zone, 2 * vision_radius);
    }
    attack_enemy(world);
    reset_and_attack_enemy(world); // after an attack, or a ranged walk
    cast_at_enemies(world);
    return true;
}

bool can_tribute_safely(const World& world, Safety& safety, const Memory& memory) {
    if (!can_tribute_here(world)) return false;
    return tribute_ok(world, safety, memory, tribute_turns(my_gems()));
}

// Only a small bag, out of every credible enemy's reach, and never the gems that would win.
// Cassi's and Issac's bags fall together.
bool may_chain(const World& world, Safety& safety) {
    if (bag_at_stake(world) >= params::chain_bag_limit || winning_bag(world)) return false;
    return !safety.any_threat(); // all credible
}

// A bag bound for an altar rides the recall home when that reaches an altar sooner than walking;
// the stop also heals and shops.
bool recall_to_bank(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    if (!memory.banking) return false;
    const vec2 here = my_position();
    if (safety.threatened(here)) return false;
    const auto& to_altar = pathing.to_any_altar();
    const int walk = to_altar.at(here), from_spawn = to_altar.at(world.map().ally_spawn_centre);
    if (walk == unreachable || from_spawn == unreachable) return false;
    const int heal = my_health() < my_max_health() ? 1 : 0;
    return my_channel_time() + heal + from_spawn < walk;
}

// No enemy seen this round or last could walk into reach before the recall lands: standing
// still to channel while a pack closes in only gets it cancelled.
bool recall_outruns(const World& world, Safety& safety) {
    const vec2 here = my_position();
    const int turns = static_cast<int>(my_channel_time());
    for (const auto& e : world.enemies)
        if (e.alive && e.age(world.round) <= 1 && dist(here, e.pos) - turns <= safety.strike_of(e).reach) return false;
    return true;
}

// Recall from a capture we hold (holding_capture), timed to land home the turn it pays: the gems
// skip the walk when an altar is nearer by way of home, and the stop heals and shops.
bool capture_recall(const World& world, Pathing& pathing, Safety& safety) {
    const vec2 here = my_position();
    if (safety.threatened(here)) return false;
    const int g = world.map().group_at(here);
    const auto& c = world.camps[g];
    if (c.holder != team::ally || c.held_since < 0) return false;
    const int payout = c.payout_round();
    const int lands = world.round + my_channel_time();
    if (lands < payout) return false;
    const auto& to_altar = pathing.to_any_altar();
    const int walk = to_altar.at(here), from_spawn = to_altar.at(world.map().ally_spawn_centre);
    if (walk == unreachable || from_spawn == unreachable) return false;
    const bool wins = capture_share(world, g) >= gems_short(world);
    // Whenever the capture's gold then buys an emblem, bag and all: we come back out stronger and
    // at full health, and bank the bag on a later trip.
    if (!wins && lands - payout <= 1 && may_shop(world) && !closing(world)) {
        const int sharers = 1 + allies_on(world, world.map().groups[g].tiles());
        if (my_gold() + world.map().groups[g].gold / sharers >= emblem_price
            && emblem_gain_rounds(world) >= static_cast<float>(lands - payout + from_spawn - walk))
            return true;
    }
    // Healing is worth nothing once the bag wins: only the quicker way to an altar counts.
    const bool hurt = !wins && my_health() < params::heal_trip_fraction * my_max_health();
    return lands - payout + from_spawn < walk + (hurt ? params::recall_heal_bonus : 0);
}

// With an empty bag, a full emblem's gold goes home to shop, riding a recall unless walking is
// quicker.
bool wants_shop(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    if (my_gems() > 0 || my_gold() < emblem_price || memory.damage > 0 || !may_shop(world)) return false;
    const vec2 here = my_position();
    if (world.map().ally_spawn.is_set(here) || safety.threatened(here)) return false;
    // The trip costs the recall and the walk back out; hurt, it also heals.
    const int back = pathing.to_ally_spawn().at(here);
    if (my_health() >= params::heal_trip_fraction * my_max_health() && back != unreachable
        && emblem_gain_rounds(world) < static_cast<float>(std::min(back, recall_turns(world)) + back))
        return false;
    bool awake = false;
    world.each_stirring([&](int g) { awake = awake || awake_over(world, g, here); });
    return !awake;
}

bool alive_now(const ChampionBelief& b) {
    try {
        return b.live().is_alive();
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
    const int reach = self.ready_stun_reach(world.round);
    const ChampionBelief* target = nullptr;
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible || e.channel != Channel::tribute || e.facts().passive == Passive::stun_immune
            || dist(self.pos, e.pos) > reach)
            continue;
        // It lands at its owner's next turn start, which can come before ours next round. One that
        // wins them the game is stunned at once.
        if (e.channel_end_round <= world.round + 1 || enemy_tribute_wins(world, e)) return nullptr;
        target = &e;
    }
    if (!target || safety.lethal(self.pos) || can_tribute_safely(world, safety, memory)) return nullptr;
    for (const auto& t : safety.threats()) {
        const int d = t.distance(self.pos);
        if (&world.enemies[t.enemy] != target && t.strike.hits(d) && t.strike.stuns[d]) return nullptr;
    }
    return target;
}

// A ready stun of ours reaches a visible enemy whose tribute wins them the game.
bool can_stop_winning_tribute(const World& world) {
    const auto& self = world.me();
    for (const auto& e : world.enemies)
        if (enemy_tribute_wins(world, e) && e.facts().passive != Passive::stun_immune
            && dist(self.pos, e.pos) <= self.ready_stun_reach(world.round))
            return true;
    return false;
}

// Rounds before an enemy hold pays: a body of ours on a camp tile by then stops it.
int enemy_hold_left(const World& world, const CampBelief& c) {
    return c.holder == team::enemy && c.held_since >= 0 ? c.payout_round() - world.round : capture_rounds();
}

// Allies in sight on G, or nearer its centre than `here` (ties to the lower index), already make
// enough holders.
bool capture_taken(const World& world, const CampGroup& G, vec2 here) {
    int ahead = 0;
    for (const auto& a : world.allies)
        ahead += !a.is_self && a.alive && a.visible
                 && (G.tiles().is_set(a.pos) || dist(a.pos, G.centre) < dist(here, G.centre)
                     || (dist(a.pos, G.centre) == dist(here, G.centre) && a.index < world.me().index));
    return ahead >= holders(G);
}

bool ally_claims(const World& world, int g) {
    for (const auto& a : world.allies)
        if (!a.is_self && comms::claim_of(world, a.index) == g) return true;
    return false;
}

// Of `tiles`, those with no champion we see on them, in a scratch board valid until the next call.
const bitboard& free_tiles(const bitboard& tiles) {
    static bitboard free{cambc::uninitialized}, units{cambc::uninitialized};
    copy_into(tiles, free);
    cambc::vision::champion_tiles_into(team::ally, units);
    drop(free, units);
    cambc::vision::champion_tiles_into(team::enemy, units);
    drop(free, units);
    return free;
}

float team_power(const World& world) {
    float total = 0;
    for (const auto& a : world.allies)
        if (a.alive) total += floored_output(a);
    return total;
}

struct SiegeLoad {
    float health = 0, hit = 0;
    float strongest = 0; // the strongest member's Strength, dead or alive
    vec2 pos{-1, -1};    // the strongest member alive
};

SiegeLoad siege_load(const World& world, int g) {
    const auto& G = world.map().groups[g];
    const auto& c = world.camps[g];
    SiegeLoad load;
    float top = -1;
    for (std::size_t i = 0; i < G.members.size(); ++i) {
        load.strongest = std::max(load.strongest, G.members[i].strength);
        const float hp = c.state == CampState::respawning ? G.members[i].max_health : c.health[i];
        if (hp <= 0) continue;
        load.health += hp;
        load.hit += G.members[i].strength;
        if (G.members[i].strength > top) top = G.members[i].strength, load.pos = G.members[i].pos;
    }
    return load;
}

// The Monolith or big group to siege; one the enemy holds or that returns too late is skipped.
int siege_candidate(const World& world, const Memory& memory) {
    const auto& map = world.map();
    static std::vector<int> sieged; // the Monoliths and big groups, in group order
    static bool listed = false;
    if (!listed) {
        listed = true;
        for (int g = 0; g < static_cast<int>(map.groups.size()); ++g)
            if (map.groups[g].has_monolith || big_group(map.groups[g])) sieged.push_back(g);
    }
    int best = -1;
    float best_cost = 0;
    for (const int g : sieged) {
        const bool big = big_group(map.groups[g]);
        const auto& c = world.camps[g];
        // siege_ready never passes a live Monolith off Monolith-only maps: only a cleared one counts.
        if (!big && !map.monolith_only && c.state != CampState::cleared) continue;
        const int wait = c.state == CampState::respawning ? c.respawn_round - world.round : 0;
        if (wait > (big ? params::big_respawn_wait : params::siege_respawn_wait)) continue;
        if (c.state == CampState::cleared && c.holder == team::enemy) continue;
        const int steps = map.ally_steps(g);
        if (steps == unreachable) continue;
        // The walk there and the wait for its return, with the team's current target kept until
        // another is clearly sooner: switching turns everyone around.
        float cost = static_cast<float>(std::max(steps, wait));
        if (memory.siege && memory.claim == g) cost -= static_cast<float>(params::siege_stickiness);
        if (best < 0 || cost < best_cost) best = g, best_cost = cost;
    }
    return best;
}

// The team's clear, at its current output, costs no more health than it can take in turns.
bool siege_ready(const World& world, int g, const SiegeLoad& load, bool committed) {
    if (load.health <= 0) return true;
    float pool = 0;
    for (const auto& a : world.allies)
        if (a.alive) pool += a.max_health;
    const float rounds = load.health / team_power(world);
    const float taken = rounds * load.hit * camp_hit_factor() * params::siege_hit_share;
    const float slack = committed ? params::siege_commit_slack : 1.0f;
    const float limit = big_group(world.map().groups[g]) ? params::big_rounds
                        : world.map().monolith_only      ? params::siege_rounds
                                                         : 0;
    return rounds <= limit * slack && taken <= params::siege_pool_share * pool * slack;
}

// Once the team is strong enough it goes together: melee adjacent, ranged at their range, the hurt
// stepping out to 4, where casters still cast.
bool siege(const World& world, Pathing& pathing, Memory& memory) {
    world.throw_if_stale();
    sieged = true;
    auto& me = cambc::self();
    const auto& map = world.map();
    const int g = siege_candidate(world, memory);
    const bool ally_in = g >= 0 && ally_claims(world, g);
    const auto load = g >= 0 ? siege_load(world, g) : SiegeLoad{};
    if (g < 0 || !siege_ready(world, g, load, (memory.siege && memory.claim == g) || ally_in)) {
        memory.siege = false;
        memory.staged_since = -1;
        return false;
    }
    const auto& G = map.groups[g];
    const auto& c = world.camps[g];
    const vec2 here = my_position();
    if (c.state == CampState::cleared) {
        // The nearest of us take the capture, a big group's split to shorten the tributes; the
        // rest go back to farming.
        if (capture_taken(world, G, here)) {
            memory.siege = false;
            return false;
        }
        memory.siege = true;
        memory.staged_since = -1;
        memory.claim = g;
        memory.crew = false;
        pathing.step_towards_funded(G.tiles(), end_reserve);
        return true;
    }
    memory.siege = true;
    memory.claim = g;
    memory.crew = ally_in;
    siege_group() = g;
    const vec2 m = load.pos;
    const int d = dist(here, m);
    const auto& f = world.me().facts();
    const int range = f.attack_range();
    const bool fresh = c.state == CampState::respawning;

    bool engaged = false;
    float staged = floored_output(world.me());
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible) continue;
        if (G.threat().is_set(a.pos) && c.awake != Awake::asleep) engaged = true;
        if (dist(a.pos, m) <= siege_stage_radius + 1) staged += floored_output(a);
    }
    if (!fresh && G.threat().is_set(here) && c.awake != Awake::asleep) engaged = true;
    if (!engaged && !fresh) {
        if (memory.staged_since < 0 && d <= siege_stage_radius + 1) memory.staged_since = world.round;
        engaged = staged >= params::siege_gather_share * team_power(world)
                  || (memory.staged_since >= 0 && world.round - memory.staged_since >= params::siege_max_wait);
    }

    const bool caster = spell_output(world.me()) > 0;
    bool tanked = false;
    for (const auto& a : world.allies)
        tanked |= !a.is_self && a.alive && a.visible && !a.facts().ranged && dist(a.pos, m) <= 1;
    // The members that could hit us here; out of reach, the strongest.
    float hit = 0;
    // Scratch boards: allocating one costs more than the host operations on it.
    static bitboard inner{cambc::uninitialized}, goals{cambc::uninitialized}, all{cambc::uninitialized};
    inner.clear();
    for (std::size_t i = 0; i < G.members.size(); ++i) {
        if (c.health[i] <= 0 && !fresh) continue;
        if (G.members[i].strength > 0 && dist(here, G.members[i].pos) <= camp_attack_range) hit += G.members[i].strength;
        if (range > 1) inner.draw_chebyshev(G.members[i].pos, static_cast<float>(range - 1));
    }
    hit = std::max(hit, load.strongest) * camp_hit_factor();
    // Leave while we can still walk out of reach: a hit a step until 4 away.
    const int role = f.ranged ? range : 1;
    const bool low = my_health() < hit * static_cast<float>(camp_attack_range + 2 - role);

    const bool many = G.members.size() > 1;
    const auto tiles = [&](int r, bitboard& out) {
        if (many) {
            if (pathing.prepare_attack_tiles(g, r, end_reserve)) pathing.attack_tiles(g, r, out);
            else note_shortcut("siege-no-tiles"), out.clear();
        } else if (pathing.prepare_member_tiles(g, r, 1u, end_reserve)) {
            and_into(pathing.member_attack_tiles(g, 0, r), map.standable, out);
        } else {
            note_shortcut("siege-no-tiles");
            out.clear();
        }
    };
    if (!engaged || fresh) {
        tiles(siege_stage_radius, goals);
        drop(goals, G.threat());
    } else if (low) {
        // Out of reach, the turn's recall is kept for a heal trip (siege_heal_trip); a caster
        // healthy enough stays at 4 to cast.
        tiles(caster && my_health() >= params::heal_trip_fraction * my_max_health() ? ability_range : siege_stage_radius,
              goals);
        drop(goals, G.threat());
    } else if (f.ranged && caster && !tanked && G.has_monolith) {
        // With no ally nearer the Monolith to take its hits, cast from out of its reach.
        tiles(ability_range, goals);
        drop(goals, G.threat());
        if (goals.is_empty()) {
            tiles(range, goals);
            drop(goals, inner);
        }
    } else if (f.ranged) {
        tiles(range, all);
        copy_into(all, goals);
        drop(goals, inner);
        if (goals.is_empty()) goals.swap(all);
    } else {
        tiles(1, goals);
    }
    if (goals.is_empty()) {
        goals.draw_chebyshev(m, static_cast<float>(siege_stage_radius));
        goals &= map.standable;
        drop(goals, G.threat());
    }
    if (!goals.is_set(here)) {
        pathing.step_towards_funded(goals, end_reserve);
        if (engaged && !low) attack_camp(world, [&](int h) { return h == g; });
        if (engaged) cast_at_camp(world, g);
        if (engaged && !low) reset_and_attack_camp(world, g);
        return true;
    }
    if (!engaged) return true;
    cast_at_camp(world, g);
    if (!low) {
        attack_camp(world, [&](int h) { return h == g; });
        reset_and_attack_camp(world, g);
    }
    return true;
}

// A big group cleared by spells from 4, out of its monsters' reach, so that nobody takes a hit;
// harmless members fall to basic attacks from there, the rest once the monsters are dead.
bool kite(const World& world, Pathing& pathing, Memory& memory) {
    world.throw_if_stale();
    auto& me = cambc::self();
    const auto& map = world.map();
    const vec2 here = my_position();
    int g = -1, best_cost = 0;
    // contest_capture's rule: a body of ours on a camp tile before their hold pays.
    const auto too_late = [&](int h) { return steps_to(map.groups[h], here) > enemy_hold_left(world, world.camps[h]); };
    for (int h = 0; h < static_cast<int>(map.groups.size()); ++h) {
        if (!big_group(map.groups[h])) continue;
        const auto& c = world.camps[h];
        const int steps = dist(here, map.groups[h].centre);
        if (c.state == CampState::cleared && c.holder == team::enemy && too_late(h)) continue;
        const int wait = c.state == CampState::respawning ? c.respawn_round - world.round : 0;
        if (wait > steps + params::kite_early) continue;
        const int cost = std::max(steps, wait);
        if (g < 0 || cost < best_cost) g = h, best_cost = cost;
    }
    if (g < 0) return false;
    const auto& G = map.groups[g];
    const auto& c = world.camps[g];
    if (c.state == CampState::cleared) {
        const auto& tiles = G.tiles();
        if (enemy_on(world, tiles) || c.holder == team::enemy) {
            if (!tiles.is_set(here) && too_late(g)) return false;
            memory.claim = g;
            memory.crew = false;
            if (tiles.is_set(here)) return true; // our tile keeps their hold from counting
            const auto& free = free_tiles(tiles);
            if (!free.is_empty()) pathing.step_towards_funded(free, end_reserve);
            return true;
        }
        if (capture_taken(world, G, here) || dist(here, G.centre) > 2 * vision_radius) return false;
        memory.claim = g;
        memory.crew = false;
        pathing.step_towards_funded(G.tiles(), end_reserve);
        return true;
    }
    const bool fresh = c.state == CampState::respawning;
    static bitboard threat{cambc::uninitialized}, near{cambc::uninitialized}, goals{cambc::uninitialized},
        basic{cambc::uninitialized};
    threat.clear();
    near.clear();
    basic.clear();
    const int range = world.me().facts().attack_range();
    bool attackers = false;
    for (std::size_t i = 0; i < G.members.size(); ++i) {
        if (!fresh && c.health[i] <= 0) continue;
        const vec2 p = G.members[i].pos;
        if (G.members[i].strength > 0) {
            attackers = true;
            threat.draw_chebyshev(p, static_cast<float>(camp_attack_range));
            near.draw_chebyshev(p, static_cast<float>(ability_range));
        } else {
            basic.draw_chebyshev(p, static_cast<float>(range));
        }
    }
    // Only harmless members: farm clears them. Champions without spells stand guard with the
    // casters, for the fights and the capture.
    if (!attackers) return false;
    const bool ally_in = ally_claims(world, g);
    memory.claim = g;
    memory.crew = ally_in;
    goals.clear();
    goals |= near;
    goals &= map.standable;
    drop(goals, threat);
    if (goals.is_empty()) return false;
    // Ranged: where a basic attack also reaches a harmless member, if that is a safe walk away.
    basic &= goals;
    const bool basic_first = world.me().facts().ranged && !basic.is_empty();
    const bool safe_here = !threat.is_set(here);
    const auto hit = [&] {
        if (fresh) return false;
        const bool cast = cast_at_camp(world, g, false, true);
        const bool attacked = attack_camp(world, [&](int h) { return h == g; }) >= 0;
        if (attacked) reset_and_attack_camp(world, g);
        return cast || attacked;
    };
    const auto& first = basic_first ? basic : goals;
    if (safe_here && (first.is_set(here) || hit())) {
        if (first.is_set(here)) hit();
        return true;
    }
    // Far off, the static walk to within reach; the live route around the monsters once near.
    if (dist(here, G.centre) > vision_radius + ability_range) {
        if (const auto* field = pathing.approach(g, ability_range, end_reserve)) pathing.step_towards(*field);
        else {
            note_shortcut("crow-flies-kite");
            pathing.step_closer(G.centre);
        }
        return true;
    }
    // A short way to a basic attack's tile, else any safe one: the long way round to the far side
    // of the monsters costs more than the attacks pay.
    const int cap = 2 * (vision_radius + ability_range);
    if (!fuel_ok(3 * search_cost_estimate(cap) + end_reserve)) {
        note_shortcut("crow-flies-kite");
        if (safe_here && goals.is_set(here)) return true;
        // Towards the centre while out of the monsters' reach; inside it, the way out.
        std::optional<vec2> best;
        int best_score = 0;
        const auto& blocked = pathing.blocked();
        for (const auto d : directions) {
            const vec2 p = here + d;
            if (!in_bounds(p) || blocked.is_set(p)) continue;
            const int score = threat.is_set(p) ? 1000 - dist(p, G.centre) : dist(p, G.centre);
            if (!best || score < best_score) best = p, best_score = score;
        }
        if (best && (!safe_here || !threat.is_set(*best))) pathing.try_move(*best);
        return true;
    }
    bool moved = basic_first && pathing.step_towards(basic, &threat, vision_radius);
    if (!moved && !goals.is_set(here)) moved = pathing.step_towards(goals, &threat, cap);
    // A sleeping group hits nobody passing through its reach.
    if (!moved && !goals.is_set(here) && c.awake == Awake::asleep) moved = pathing.step_towards(goals, nullptr, cap);
    // No way within the cap (round a lake): the static walk.
    if (!moved && !goals.is_set(here))
        if (const auto* field = pathing.approach(g, ability_range, end_reserve))
            moved = pathing.step_towards(*field, c.awake == Awake::asleep ? nullptr : &threat);
    if (!moved && !safe_here) {
        static bitboard out{cambc::uninitialized};
        out.clear();
        out |= map.standable;
        drop(out, threat);
        pathing.step_towards(out, nullptr, 2 * camp_attack_range);
    }
    if (!threat.is_set(my_position())) hit();
    return true;
}

// A cleared group in sight that the enemy holds or stands on, and that we can reach before the
// hold pays: a body of ours on one of its tiles stops the count.
bool contest_capture(const World& world, Pathing& pathing, Memory& memory) {
    const auto& map = world.map();
    const vec2 here = my_position();
    int best = -1, best_steps = unreachable;
    for (int g = 0; g < static_cast<int>(map.groups.size()); ++g) {
        const auto& G = map.groups[g];
        const auto& c = world.camps[g];
        if (G.gems < params::contest_gems || c.state != CampState::cleared || dist(here, G.centre) > vision_radius + 2) continue;
        if (!enemy_on(world, G.tiles()) && c.holder != team::enemy) continue;
        const int steps = steps_to(G, here);
        if (steps > enemy_hold_left(world, c) || steps >= best_steps) continue;
        best = g, best_steps = steps;
    }
    if (best < 0) return false;
    const auto& free = free_tiles(map.groups[best].tiles());
    if (free.is_empty() || !pathing.step_towards(free, nullptr, best_steps + max_detour)) return false;
    memory.claim = best;
    memory.crew = false;
    return true;
}

// A sieger stepped out of the big group's reach goes home to heal before it is needed again.
bool siege_heal_trip(const Memory& memory, Safety& safety) {
    return memory.siege && my_health() < params::heal_trip_fraction * my_max_health() && !safety.threatened(my_position());
}

// Our tribute channel goes on unless it is unsafe and fleeing or fighting back pays. True if the
// turn ends with it.
bool continue_tribute(const World& world, Safety& safety, Memory& memory) {
    auto& me = cambc::self();
    decision = 'T';
    // The enemy's winning tribute in reach of a ready stun is the game: ours waits.
    if (!winning_bag(world) && can_stop_winning_tribute(world)) {
        try {
            me.cancel_submit_gems();
        } catch (const std::exception&) {
        }
        if (!me.is_submitting_gems()) return false;
    }
    if (tribute_ok(world, safety, memory, my_channel_time())) return true;
    // Damage does not interrupt a tribute: cancelling pays only to flee or to fight back.
    if (memory.damage <= 0 && !want_home(world, safety, memory.siege) && !attack_target(world)
        && (winning_bag(world) || !prey(world, safety)))
        return true;
    decision = 't';
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
    home = want_home(world, safety, memory.siege);
    if (*home && !safety.threatened(my_position()) && !can_tribute_safely(world, safety, memory) && recall_outruns(world, safety))
        return true;
    decision = 'k';
    if (holding_capture(world)) {
        if (capture_recall(world, pathing, safety)) {
            decision = 'Q';
            return true;
        }
    } else {
        const auto shop = [&] {
            return wants_shop(world, pathing, safety, memory) && my_channel_time() < pathing.to_ally_spawn().at(my_position());
        };
        if (recall_to_bank(world, pathing, safety, memory) || shop()) return true;
        // The sieger's role lasts the trip: dropping it here would cancel the recall next turn.
        if (siege_heal_trip(memory, safety)) return sieged = true;
    }
    try {
        me.cancel_recall();
    } catch (const std::exception&) {
        return true;
    }
    return false;
}

void retreat(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    world.throw_if_stale();
    auto& me = cambc::self();
    decision = 'R';
    memory.claim = -1;
    memory.banking = my_gems() > 0; // a bag in retreat goes on to an altar, by a recall if quicker
    if (world.me().facts().walk_and_attack_independent() && attack_enemy(world)) reset_and_attack_enemy(world, true);
    cast_at_enemies(world, true);
    if (!me.is_alive()) return;
    if (!my_can_attack() || !my_can_cast()) safety.refresh();
    // A tribute survives damage; a recall does not.
    if (can_tribute_safely(world, safety, memory)) {
        bank_gems(world, pathing, safety, memory);
        return;
    }
    // The escape dash shares the one cast: the reset only after it, from a melee attack or a ranged walk.
    dash_away(world, pathing, pathing.to_ally_spawn());
    reset_and_attack_enemy(world);
    if (!flee_camps(pathing, safety, pathing.to_ally_spawn())) retreat_step(world, pathing, safety, pathing.to_ally_spawn());
    reset_and_attack_enemy(world);
}

// On a capture we hold or contest: the hold needs no turn, so hit another group in reach that
// cannot hit back or already does.
void hold_capture(const World& world, Memory& memory, bool attacked) {
    const int held = world.map().group_at(my_position());
    memory.claim = held;
    memory.crew = false;
    if (attacked) return;
    const auto& groups = world.map().groups;
    const auto free_hit = [&](int g) { return g != held && (groups[g].strength <= 0 || world.camps[g].awake != Awake::asleep); };
    if (const int hit = attack_camp(world, free_hit); hit >= 0) {
        cast_at_camp(world, hit);
        reset_and_attack_camp(world, hit);
    }
}

// Carrying: chase a kill worth the risk, bank, wait at an altar until it is safe, or chain another
// capture on the way.
void carry_bag(const World& world, Pathing& pathing, Safety& safety, Memory& memory, bool attacked) {
    const bool safe = can_tribute_safely(world, safety, memory);
    const bool late = endgame(world, pathing);
    const bool close = closing(world);
    if (!safe && !late && !close && !winning_bag(world) && chase(world, pathing, safety)) return;
    if (safe) {
        decision = 'B';
        memory.banking = true;
        bank_gems(world, pathing, safety, memory);
        return;
    }
    if (can_tribute_here(world)) {
        // Hit with nothing to hit back: waiting here only takes more.
        if (memory.damage > 0 && !attack_target(world)) {
            decision = 'R';
            pathing.set_guard(nullptr);
            dash_away(world, pathing, pathing.to_ally_spawn());
            retreat_step(world, pathing, safety, pathing.to_ally_spawn());
            return;
        }
        const vec2 here = cambc::self().position();
        const auto& altars = world.map().altars;
        int at = -1;
        for (int a = 0; a < static_cast<int>(altars.size()) && at < 0; ++a)
            if (!world.altars[a].enemy_lock && dist(here, altars[a].pos) <= cambc::constants::submit_gems_range) at = a;
        if (at != memory.avoid_altar || world.round >= memory.avoid_until) {
            if (memory.wait_altar != at) memory.wait_altar = at, memory.wait_since = world.round;
            // How long they stay is unknown: wait as many rounds as the walk to the nearest other
            // unlocked altar takes, then walk there.
            int other_steps = unreachable;
            for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
                if (a == at || world.altars[a].enemy_lock || dist(here, altars[a].pos) - 1 >= other_steps) continue;
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
    memory.banking = late || close || walked || !may_chain(world, safety) || !farm(world, pathing, safety, memory);
    if (memory.banking) bank_gems(world, pathing, safety, memory); // a tribute can still start after a ranged attack
}

void decide(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    auto& me = cambc::self();
    if (my_gems() == 0 || !world.me().alive) memory.banking = false;
    if (!world.me().alive) {
        memory.claim = -1;
        buy_shards(world); // the dead can only shop
        buy_lock();
        return;
    }
    // One state read covers the channels until one is cancelled; a channel excludes the others.
    const auto state = my_state();
    if (state.contains(cambc::champion_state::teleporting)) return;
    if (state.contains(cambc::champion_state::submitting_gems) && continue_tribute(world, safety, memory)) return;
    // Read again only after shopping changes our stats.
    std::optional<bool> home;
    if (state.contains(cambc::champion_state::recalling) && continue_recall(world, pathing, safety, memory, home)) return;

    // Shopping, heals and shields do not move us.
    const bool on_spawn = world.map().ally_spawn.is_set(my_position());
    if ((on_spawn || world.me().facts().passive == Passive::remote_shop) && buy_shards(world)) home.reset();
    if (on_spawn) buy_lock();
    if (!world.me().can_act(world.round)) return;
    heal_ally(world);
    shield_if_needed(world, memory.claim);
    // Healing needs a turn end on spawn; a recall arrives at turn start.
    if (on_spawn && my_health() < my_max_health()) {
        decision = 'H';
        const bool attacked = attack_enemy(world);
        if (attacked) reset_and_attack_enemy(world, true);
        cast_at_enemies(world);
        if (attacked) reset_and_attack_enemy(world);
        return;
    }
    if (home ? *home : want_home(world, safety, memory.siege)) {
        retreat(world, pathing, safety, memory);
        return;
    }

    pathing.set_guard(step_guard(world, safety));
    const bool holding = holding_capture(world) || contesting(world);
    const auto* stun_later = tribute_to_stun_later(world, safety, memory);
    bool attacked = attack_enemy(world, stun_later);
    if (attacked) reset_and_attack_enemy(world, true, stun_later);
    cast_at_enemies(world, my_gems() > 0 && !holding, stun_later);
    if (!attacked && !holding && dash_to_attack(world, pathing, nullptr, stun_later)) attacked = attack_enemy(world, stun_later);
    if (attacked) reset_and_attack_enemy(world, false, stun_later);
    decision = holding ? 'P' : attacked ? 'A' : decision;
    if (!me.is_alive()) return;
    if (!my_can_attack() || !my_can_cast()) safety.refresh();
    if (holding) {
        hold_capture(world, memory, attacked);
        return;
    }
    // A tributer cannot walk out of the stun's reach.
    if (stun_later && alive_now(*stun_later)) {
        decision = 'D';
        return;
    }
    if (my_gems() > 0) {
        carry_bag(world, pathing, safety, memory, attacked);
        return;
    }
    if (attacked && !world.me().facts().walk_and_attack_independent()) return;
    if (wants_shop(world, pathing, safety, memory)) {
        decision = 'S';
        memory.claim = -1;
        step_safely(pathing, pathing.to_ally_spawn(), safety);
        return;
    }
    if (chase(world, pathing, safety)) return;
    if (contest_capture(world, pathing, memory)) {
        decision = 'X';
        return;
    }
    decision = 'F';
    if (world.map().shared_gems ? kite(world, pathing, memory) : siege(world, pathing, memory)) {
        decision = 'G';
        return;
    }
    farm(world, pathing, safety, memory);
}

// Recalling every turn end and cancelling next turn when not wanted makes a wanted recall a
// turn shorter. Damage before then cancels it at no cost.
void start_recall(const World& world) {
    auto& me = cambc::self();
    if (!world.me().alive || channelling() || world.map().ally_spawn.is_set(my_position()))
        return;
    try {
        me.recall();
    } catch (const cambc::error&) {
    }
}

} // namespace

// The walk to our farm choice, from where we stand. Before the turn's optional work: what is left
// after it then pays for that work rather than the walk.
void prepare_walk(const World& world, Pathing& pathing, const Memory& memory, std::uint64_t fuel_floor) {
    const int g = memory.farm_group;
    if (!world.me().alive || channelling() || g < 0 || g >= static_cast<int>(world.camps.size())) return;
    const int range = world.camps[g].state == CampState::cleared ? 0 : world.me().facts().attack_range();
    pathing.approach(g, range, fuel_floor);
}

void prepare_next_turn(const World& world, Pathing& pathing, const Memory& memory) {
    prepare_walk(world, pathing, memory, end_reserve);
}

void play_turn(const World& world, Pathing& pathing, Memory& memory) {
    Safety safety{world};
    const float health = world.me().alive ? my_health() : 0;
    memory.damage = memory.round == world.round - 1 ? std::max(0.0f, memory.health - health) : 0;
    decision = '-';
    sieged = false;
    siege_group() = -1;
    const vec2 start = world.me().pos;
    prepare_walk(world, pathing, memory, walk_first_floor);
    decide(world, pathing, safety, memory);
    if (decision != 'W') memory.wait_altar = -1;
    if (!sieged) {
        memory.siege = false;
        memory.staged_since = -1;
    }
    pathing.set_guard(nullptr);
    if constexpr (debug_fights)
        if (world.me().alive && !world.map().ally_spawn.is_set(start) && fuel_ok(end_reserve + 15000))
            if (const auto t = safety.fight(start); t.enemies > 0) log_fight("FF", world, safety, start, t);
    heal_ally(world); // allies in reach after walking
    shield_if_needed(world, memory.claim);
    place_ward(world, pathing, memory); // where we end the turn
    place_lock(world);
    start_recall(world);
    set_turn_order(world, safety);
    comms::claim(memory.claim);
    comms::bag(world.me().alive ? static_cast<int>(my_gems()) : 0);
    memory.round = world.round;
    memory.health = world.me().alive ? my_health() : 0;
    debug_block({ std::printf("D %d %u %c %d %d\n", world.round, static_cast<std::uint32_t>(world.me().handle), decision, memory.farm_group, memory.claim); });
}

} // namespace aph
