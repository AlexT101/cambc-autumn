// Crews on camps, gold-only camps, team sieges of Monoliths, kites of big shared groups, capture recalls
// that also go shopping, banking every bag once the race is close, and altar locks. Fights are
// taken whatever the numbers, except when hurt or carrying, or against a pack in our own half.
// Champions never stand under camps they cannot outlast, wait at most a few rounds for a camp to
// return, and stun any enemy tribute that would win the game.
#include "bot.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <limits>
#include <memory>
#include <optional>
#include <span>
#include <vector>
#include "abilities.h"
#include "comms.h"
#include "crew_work.h"
#include "params.h"
#include "pathing.h"
#include "plan.h"
#include "safety.h"
#include "self_abilities.h"
#include "turn_order.h"
#include "world.h"

namespace aph {

namespace {

constexpr int endgame_margin = 20;   // rounds to spare on the last trip to an altar
constexpr int endgame_slack = 2;     // rounds to spare on a last-chance tribute
constexpr float escape_step_value = 210; // a retreat's or a game-ender intercept's walk, in enemy health

// The turn's branch, for debug_fights: Chase, Attack, Retreat, Farm, Bank, Wait at an altar,
// Tribute kept / t cancelled, recall Kept / k cancelled, Healing on spawn, Shopping trip,
// holding (P), capture recall (Q), siege or kite of a big group (G), contest (X),
// stopping a game-ending bag (E).
char decision = '-';
bool sieged = false; // siege() ran this turn
bool stunned_turn = false; // stunned at this turn's start
bool searched = false; // the strike search chose this turn's cast, heals and shields included
bool struck = false;   // the strike search ran this turn
// The Prism-Willow support code chose this turn: the wrap-up's strike, heal, shield and recall stay out.
bool support_owned = false;
bool support_requested = false, support_offered = false, support_retreat = false;
bool end_ward = false; // the turn-end ward, seeing more than our last observe
vec2 searched_at{};      // where the search's plan ended, and whether it had attacked by then
bool searched_hit = false;

// damage, imminent: Safety::damage_bound, the second with enemies yet to act counted twice.
struct SupportExposure {
    float damage = 0, imminent = 0;
    bool enemy = false, camp = false, stun = false;
    bool safe() const { return !enemy && !camp; }
};

// Willow's tile, or one a step away, with its exposure in the beliefs of our latest observe.
struct Station {
    vec2 p;
    SupportExposure risk;
    bool open = false;
};
struct Stations {
    std::array<Station, 9> tiles; // ours first
    bitboard guard;               // where an enemy may hit
    vec2 origin{-1, -1};
    std::uint32_t observations = 0;
};
Stations& stations_cache() {
    static Stations s;
    return s;
}
const Stations& stations(const World& world, Safety& safety, vec2 here);
void guard_steps(const World& world, Pathing& pathing, Safety& safety);

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
        if (const auto b = th.at(p); b.hits)
            std::printf(" %u%c:%d:%d:%d", static_cast<std::uint32_t>(world.enemies[th.enemy].handle), th.visible ? 'v' : 'u',
                        th.visible ? dist(p, th.pos) : -1, static_cast<int>(b.damage), world.round - world.enemies[th.enemy].pos_round);
    std::printf("\n");
}

// cambc::item_family's order, which the item enum's layout follows.
enum Family { monster, power, durability, treasure, jungle, home, bruiser, tribute, capture, prospector, hunter, skirmish, greed, collectors };
enum StatKind { strength_stat, focus_stat, health_stat };
static_assert(collectors == static_cast<int>(cambc::item_family::collectors));
static_assert(health_stat == static_cast<int>(cambc::item_stat::health));

unsigned shards_needed(int family) { return family == greed ? greed_shards : shards_per_emblem; }

cambc::item_type shard_of(int family, int stat) {
    return cambc::item_type{static_cast<std::uint32_t>(family * 6 + stat * 2)};
}
cambc::item_type emblem_of(int family, int stat) {
    return cambc::item_type{static_cast<std::uint32_t>(family * 6 + stat * 2 + 1)};
}

// Our basic attacks and casts per slot over the game, counted at each turn's end (count_use).
struct Use {
    int attacks = 0;
    std::array<int, 2> casts{};
};
Use use;

// Focus when a shard's Focus, over our damaging casts so far (landings too, as raw_output counts
// them), beats its Strength over our basic attacks; until both have happened, over the damage
// spells' multipliers against the basic attacks in one cooldown (one a round, plus the reset's).
// Ren's retaliation also scales with Focus, and where big groups fall to spells from out of reach
// (kite), every spell's Focus counts.
int main_stat(const World& world) {
    const auto& f = world.me().facts();
    float spells = 0, cast = 0;
    for (int s = 0; s < 2; ++s) {
        const auto& a = f.abilities[s];
        if (a.kind == AbilityKind::damage) spells += a.multiplier;
        if (a.kind == AbilityKind::damage || a.lands()) cast += a.multiplier * static_cast<float>(use.casts[s]);
    }
    if ((world.map().shared_gems && spells > 0) || f.passive == Passive::retaliation) return focus_stat;
    float attacks = static_cast<float>(use.attacks);
    if (use.attacks == 0 || cast <= 0) cast = spells, attacks = static_cast<float>(ability_cooldown + (f.has_attack_reset() ? 1 : 0));
    return f.focus.growth * cast > attacks * f.strength.growth ? focus_stat : strength_stat;
}

bool buy(cambc::item_type shard, unsigned count) {
    auto& me = cambc::self();
    if (!count || !me.can_buy(shard, count)) return false;
    throw_if_stale();
    try {
        me.buy(shard, count);
        return true;
    } catch (const cambc::error&) {
        return false;
    }
}

// Locks on our own and middle altars keep the enemy's bags from scoring there until broken.
void buy_lock() {
    auto& me = cambc::self();
    try {
        if (me.can_buy(cambc::consumable_type::altar_lock)) throw_if_stale(), me.buy(cambc::consumable_type::altar_lock);
    } catch (const cambc::error&) {
    }
}

bool carries_crystal() { return cambc::self().consumables()[cambc::consumable_type::tp_crystal].count() > 0; }
bool can_buy_crystal() { return my_gold() >= cambc::consumable_type::tp_crystal.cost(); }

// Once a hop to an altar only a crystal reaches (StaticMap::hops) would have beaten walking to bank.
void buy_crystal(const Memory& memory) {
    if (!memory.wants_crystal) return;
    auto& me = cambc::self();
    try {
        if (me.can_buy(cambc::consumable_type::tp_crystal)) throw_if_stale(), me.buy(cambc::consumable_type::tp_crystal);
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
            if (!enemy_tribute && dist(p, map.ally_spawn_centre) > dist(p, map.enemy_spawn_centre) + 2) continue;
            // Placing one cancels every tribute at the altar, ours included: worth it only against a win.
            bool tributing = false, ours_wins = false;
            for (const auto& ally : world.allies)
                if (!ally.is_self && ally.alive && ally.channel == Channel::tribute && dist(ally.pos, p) <= cambc::constants::submit_gems_range)
                    tributing = true,
                    ours_wins |= world.score.ally + ally.gems >= static_cast<int>(cambc::constants::winning_gems);
            if (tributing && (!winning || ours_wins)) continue;
            const auto known = [&] {
                if (own_lock_round.size() < map.altars.size()) own_lock_round.resize(map.altars.size(), -1);
                own_lock_round[a] = world.round;
            };
            throw_if_stale();
            try {
                if (lock.use(p)) return known();
            } catch (const cambc::error& e) {
                if (e.code() == cambc::error_code::invalid_action_altar_lock_already_locked) known();
            }
        }
}

bool attack_enemy(const World& world) {
    if (!my_can_attack()) return false;
    const auto target = attack_target(world);
    if (!target) return false;
    try {
        attack_champion(*target);
        return true;
    } catch (const cambc::error&) {
        return false;
    }
}

struct CampAttackTarget {
    int group, member;
    float score;
};

struct CampAttackTargets {
    std::array<CampAttackTarget, 16> found;
    int n = 0;
};

// Keep the ordinary list's bound and order even when farm also collects harmless alternatives.
template <class Allowed> CampAttackTargets camp_attack_targets(const World& world, Allowed allowed, CampAttackTargets* resources = nullptr) {
    CampAttackTargets targets;
    if (!my_can_attack()) return targets;
    const int range = world.me().facts().attack_range();
    const vec2 here = my_position();
    if (!camp_in_reach(world, here, range)) return targets;
    const bool splash = world.me().facts().passive == Passive::splash_attack;
    const auto& map = world.map();
    for (auto p : positions_within(live_camp_tiles(), here, range)) {
        const int g = map.group_at(p);
        if (g < 0 || (map.groups[g].has_monolith && g != siege_group())) continue;
        const bool ordinary = allowed(g);
        const bool resource = resources && !map.groups[g].has_monolith && map.groups[g].strength <= 0;
        if (!ordinary && !resource) continue;
        const auto& members = map.groups[g].members;
        const auto& health = world.camps[g].health;
        for (int i = 0; i < static_cast<int>(members.size()); ++i) {
            if (members[i].pos != p) continue;
            const float hp = health[i] > 0 ? health[i] : members[i].max_health;
            float score = members[i].strength / std::max(1.0f, hp);
            if (splash) {
                int near = 0;
                for (int j = 0; j < static_cast<int>(members.size()); ++j)
                    near += j != i && health[j] > 0 && dist(members[i].pos, members[j].pos) <= 1;
                score += static_cast<float>(near);
            }
            if (ordinary && targets.n < static_cast<int>(targets.found.size())) targets.found[targets.n++] = {g, i, score};
            if (resource && resources->n < static_cast<int>(resources->found.size())) resources->found[resources->n++] = {g, i, score};
        }
    }
    const auto rank = [](CampAttackTargets& list) {
        std::stable_sort(list.found.begin(), list.found.begin() + list.n,
                         [](const CampAttackTarget& a, const CampAttackTarget& b) { return a.score > b.score; });
    };
    rank(targets);
    if (resources) rank(*resources);
    return targets;
}

bool attack_camp_target(const World& world, const CampAttackTarget& target) {
    throw_if_stale();
    try {
        cambc::self().attack(world.map().groups[target.group].camp(target.member));
        ++camp_hits();
        return true;
    } catch (const cambc::error&) {
    }
    return false;
}

int attack_camp_targets(const World& world, const CampAttackTargets& targets) {
    for (int k = 0; k < targets.n; ++k)
        if (attack_camp_target(world, targets.found[k])) return targets.found[k].group;
    return -1;
}

// A camp in range of a group `allowed` accepts; the group attacked, or -1. Removing the most
// damage per hit goes first; Varg's splash wants the most live members next to its target.
template <class Allowed> int attack_camp(const World& world, Allowed allowed) {
    return attack_camp_targets(world, camp_attack_targets(world, allowed));
}

// A static field counts camps as cleared, so its walk can end at a live camp holding the only way
// on. When every step down the field is onto one, hit the weakest in reach if we outlast the fire
// of its group's members that reach us for as long as our basic attacks take to kill it. Camps
// never regenerate: a retreat and return still make progress.
bool breach(const World& world, const Field& field) {
    if (!my_can_attack()) return false;
    const vec2 here = my_position();
    const int at = field.at(here);
    if (at == 0 || at == unreachable) return false;
    const auto& map = world.map();
    const auto& live = live_camp_tiles();
    int group = -1, member = -1;
    float weakest = 0;
    for (const auto d : directions) {
        const vec2 p = here + d;
        if (!in_bounds(p) || field.at(p) >= at) continue;
        if (!test(live, p)) return false; // something else holds this way on
        const int g = map.group_at(p);
        if (g < 0 || map.groups[g].has_monolith) return false;
        const auto& members = map.groups[g].members;
        for (int i = 0; i < static_cast<int>(members.size()); ++i) {
            if (members[i].pos != p) continue;
            const float hp = world.camps[g].health[i] > 0 ? world.camps[g].health[i] : members[i].max_health;
            if (group < 0 || hp < weakest) group = g, member = i, weakest = hp;
        }
    }
    if (group < 0) return false;
    // Hitting any member wakes the group.
    float fire = 0;
    const auto& members = map.groups[group].members;
    for (int i = 0; i < static_cast<int>(members.size()); ++i)
        if (world.camps[group].health[i] > 0 && dist(here, members[i].pos) <= members[i].reach) fire += members[i].strength;
    const float turns = std::ceil(weakest / std::max(1.0f, my_strength() * camp_dealt_factor()));
    if (camp_hit_factor() * fire * turns >= my_health()) return false;
    if (!attack_camp_target(world, {group, member, 0})) return false;
    reset_and_attack_camp(world, group);
    return true;
}

// Around awake camps and credible enemies when a way exists, else straight. Routes are replanned
// every turn, so only danger near us is worth the extra search.
void step_safely(const World& world, Pathing& pathing, const Field& field, Safety& safety) {
    if (!my_can_move()) return;
    bool moved;
    if (!safety.avoid_within(my_position(), vision_radius)) {
        moved = pathing.step_towards(field);
    } else {
        const auto& avoid = safety.avoid();
        moved = pathing.step_towards(field, &avoid) || pathing.step_towards(field);
    }
    if (!moved) breach(world, field);
}

// Out of the camps' reach first, along the cheapest neighbour: walking home past an awake camp
// takes a hit every step, while a recall started outside its reach goes home untouched.
bool flee_camps(const World& world, Pathing& pathing, Safety& safety, const Field& home) {
    if (!my_can_move()) return false;
    const vec2 here = my_position();
    if (safety.camp_damage(here) <= 0) return false;
    // A camp hits every tile in its reach alike, so one step's damage cannot tell the way out from
    // a walk along the edge of its reach: count the hits still to come before leaving it.
    static bitboard exits{cambc::uninitialized};
    or_into(world.map().standable, safety.camp_area(), exits);
    exits ^= safety.camp_area();
    const int longest = world.map().max_camp_reach;
    int walk_out = 1;
    while (walk_out <= longest && !any_within(exits, here, walk_out)) ++walk_out;
    // A step changes the walk out by at most one: only a step that shortens it needs telling apart.
    const auto cost = [&](vec2 p) {
        const float camp = safety.camp_damage(p);
        float damage = safety.damage_bound(p);
        if (camp > 0 && walk_out > 1) damage += camp * static_cast<float>(p != here && any_within(exits, p, walk_out - 1) ? walk_out - 2 : walk_out - 1);
        return damage;
    };
    const auto& blocked = pathing.blocked();
    std::optional<vec2> best;
    float best_damage = cost(here);
    int best_home = home.at(here);
    for (auto d : directions) {
        const vec2 p = here + d;
        if (!in_bounds(p) || test(blocked, p)) continue;
        const float damage = cost(p);
        const int steps = home.at(p);
        if (damage < best_damage || (damage == best_damage && steps < best_home)) best = p, best_damage = damage, best_home = steps;
    }
    return best && pathing.try_move(*best);
}

// Inside danger a route home is only the shortest walk, ties in compass order, which can lead
// along the enemies we flee: take the homeward step that can be hit least, then the nearest home,
// then the farthest from them. A sideways step goes first only when it can be hit less, and one
// that lengthens the walk only when it leaves every reach and no shorter one does: still in reach,
// it only delays, as the pursuer takes the step back next turn.
void retreat_step(const World& world, Pathing& pathing, Safety& safety, const Field& home) {
    if (!my_can_move()) return;
    const vec2 here = my_position();
    if (!safety.avoid_within(here, vision_radius)) {
        pathing.step_towards(home);
        return;
    }
    const auto& avoid = safety.avoid();
    if (!test(avoid, here) && pathing.step_towards(home, &avoid)) return;
    const int steps = home.at(here);
    const auto& blocked = pathing.blocked();
    struct Option {
        vec2 p;
        float damage;
        int steps, gap;
    };
    Unwritten<Option, 8> scratch;
    auto& options = scratch.a;
    int n = 0;
    bool clear = false;
    const auto add = [&](bool longer) {
        for (auto d : directions) {
            const vec2 p = here + d;
            if (!in_bounds(p) || test(blocked, p)) continue;
            const int s = home.at(p);
            if (s == unreachable || (s > steps) != longer) continue;
            const float damage = safety.damage_bound(p);
            if (longer && damage > 0) continue;
            int gap = unreachable;
            for (const auto& e : world.enemies)
                if (e.alive && e.visible) gap = std::min(gap, dist(p, e.pos));
            options[n++] = {p, damage, s, gap};
            clear |= damage <= 0;
        }
    };
    add(false);
    if (!clear) add(true);
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
    for (const auto& lock : cambc::vision::altar_locks())
        if (lock.is_enemy() && lock.position() == p) return true;
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
// Ours.
int tribute_turns(const World& world, int gems) { return tribute_turns(gems, world.me().fast_tribute); }

int recall_turns(const World& world) {
    return world.me().recall_turns();
}

int rounds_left(const World& world) { return static_cast<int>(cambc::constants::max_rounds) - world.round; }

// Tavi shops anywhere: no trip home for it.
bool may_shop(const World& world) { return world.me().facts().passive != Passive::remote_shop; }

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

// The tribute tiles a walk from our spawn reaches with live camps as walls; those only a crystal
// reaches stay in. With none, `opened` gets those live camps cut off and `blocks` the groups beside
// our walk in the same area as one: a thicker wall of camps is opened a layer at a time.
struct AltarAccess {
    bitboard live, open, opened;
    bool any_open = false;
    std::vector<int> blocks;
    int version = 0;          // bumped on each rebuild
    std::uint32_t live_flips = 0;
};

// out = b with its 8 neighbours.
void dilate_into(const bitboard& b, bitboard& out) {
    static bitboard rows{cambc::uninitialized}, shifted{cambc::uninitialized};
    copy_into(b, rows);
    for (const int d : {1, -1}) {
        b.shift_right_into(d, shifted);
        rows |= shifted;
    }
    copy_into(rows, out);
    for (const int d : {1, -1}) {
        rows.shift_up_into(d, shifted);
        out |= shifted;
    }
}

const AltarAccess& altar_access(const World& world, Pathing& pathing) {
    static AltarAccess a;
    const auto& live = pathing.live_camps();
    if (a.version > 0 && a.live_flips == pathing.live_flips()) return a;
    a.live_flips = pathing.live_flips();
    const auto& map = world.map();
    // `ours` is kept as the walk from our spawn with a.live as walls: most changes update it
    // without a flood from spawn.
    static bitboard walls{cambc::uninitialized}, ours{cambc::uninitialized}, area{cambc::uninitialized},
        seen{cambc::uninitialized}, gone{cambc::uninitialized}, grown{cambc::uninitialized};
    bool walked = false;
    if (a.version > 0 && !map.ally_spawn_tiles.empty()) {
        copy_into(live, area);
        drop(area, a.live);
        copy_into(a.live, gone);
        drop(gone, live);
        const bool back = !board_empty(area), died = !board_empty(gone);
        if (!back && !died) return a;
        if (!back) {
            // Deaths add to the walk what each dead camp beside it reaches without crossing it.
            or_into(pathing.static_walls(), live, walls);
            walls |= ours;
            dilate_into(ours, grown);
            gone &= grown;
            while (!board_empty(gone)) {
                const vec2 t = first_tile(gone);
                walls.reachable_tiles_into(t, unreachable, seen);
                ours |= seen;
                drop(gone, seen);
                set_tile(gone, t, false);
            }
            walked = true;
        } else if (!died) {
            // Respawns whose walkable ring is connected cut no walk: it goes round them.
            dilate_into(area, grown);
            grown &= ours;
            drop(grown, area);
            walked = board_empty(grown);
            if (!walked) {
                not_into(grown, walls);
                walls.reachable_tiles_into(first_tile(grown), static_cast<std::uint16_t>(board_count(grown)), seen);
                walked = seen == grown;
            }
            if (walked) drop(ours, area);
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
    if (!walked) {
        or_into(pathing.static_walls(), live, walls);
        walls.reachable_tiles_into(map.ally_spawn_tiles[0], unreachable, ours);
    }
    if (a.version == 1) { // never walked: `ours` is the flood above
        clear_board(tributes);
        for (const auto& t : map.altars) tributes |= t.tribute_tiles();
        // Off our walk, a tribute tile counts below as a crystal's: only if a hop reaches its altar.
        // Live camps only add walls, so a tile on `ours` is on that walk too: the walk, a flood as
        // costly as ours (cached, but uncached until the warm-up), is read only for the others.
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
    // The static walk is a flood as costly as ours (~28k on 100x100, uncached until the warm-up):
    // read it only when a tribute tile is off our walk or none is open.
    copy_into(a.open, area);
    drop(area, ours);
    const bool off_walk = !board_empty(area);
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
    if (!off_walk) {
        copy_into(pathing.foot(), area);
        drop(area, ours);
    }
    a.opened &= area;
    // The live camps beside our walk.
    dilate_into(ours, grown);
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

// The camp damage a phase on the best open tribute tile, from the members believed awake: an asleep
// one wakes only when damaged. Huge with no open tile.
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
    // recall out of a pocket to a spawn with a walk to one banks it.
    if (!world.map().hops().empty() && pathing.to_any_altar().at(my_position()) == unreachable && !carries_crystal()
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
        const int out = field.at(world.map().ally_spawn_centre);
        walk = out == unreachable ? 0 : recall_turns(world) + out;
    }
    return bag_rounds_left(world) <= walk + tribute_turns(world, my_gems()) + endgame_margin;
}

bool retaining_gems(const World& world, Pathing& pathing) {
    return world.me().facts().passive == Passive::gem_focus && my_gems() > 0
           && !winning_bag(world) && !closing(world, pathing);
}

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

bool place_ward(const World& world, Memory& memory, bool grow = true);
bool see_revealed(World& world, Pathing& pathing, Safety& safety);
bool willow_bank_heal_step(World& world, Pathing& pathing, Safety& safety, const Field& field);

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
            return true;
        } catch (const cambc::error&) {
        }
    }
    return false;
}

const bitboard* pack_zone(const World& world);

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
        // A lock is broken on arrival, as bank_gems does on foot: a turn per hit left.
        const auto& belief = world.altars[a];
        const int lock = !belief.enemy_lock ? 0 : belief.enemy_lock_hits > 0 ? belief.enemy_lock_hits : static_cast<int>(cambc::constants::altar_lock_hits);
        if (const int steps = walk + cambc::constants::tp_crystal_time + inner + lock + recall_turns(world); steps < best.steps)
            best = {h, steps};
    }
    return best;
}

// Towards the hop's sources; on one, the crystal to the free landing nearest `goal` (its altar's
// field by default). A farm hop (`goal` given) lands only out of the strike of every enemy in sight
// that could close in during the channel; false if it found none on a source.
bool take_hop(const World& world, Pathing& pathing, Safety& safety, int h, const Field* goal = nullptr) {
    const auto& hop = world.map().hops()[h];
    if (test(hop.sources, my_position())) {
        auto targets = pathing.teleport_targets();
        targets &= hop.landings;
        const auto& field = goal ? *goal : pathing.to_altar(hop.altar);
        const auto watched = [&](vec2 l) {
            if (!goal) return false;
            for (const auto& e : world.enemies)
                if (e.alive && e.visible && dist(l, e.pos) <= safety.strike_of(e).reach + cambc::constants::tp_crystal_time) return true;
            return false;
        };
        vec2 best{-1, -1};
        int best_steps = unreachable;
        for (const vec2 l : targets.positions())
            if (const int s = field.at(l); s < best_steps && !watched(l)) best = l, best_steps = s;
        if (best.x < 0 && goal) return false;
        if (best.x >= 0) {
            throw_if_stale();
            try {
                if (cambc::self().consumables()[cambc::consumable_type::tp_crystal].use(best)) return true;
            } catch (const cambc::error&) {
            }
        }
    }
    step_safely(world, pathing, pathing.to_hop(h), safety);
    return true;
}

[[gnu::flatten]] void bank_gems(World& world, Pathing& pathing, Safety& safety, Memory& memory, bool heal_step = true) {
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
    // Breaking a lock takes a turn per hit left, about a step each.
    int best = -1, best_steps = unreachable;
    if (any_locked) {
        for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
            // A tribute tile is within 1 of its altar: an altar this rules out needs no field.
            if (avoided(a) || dist(here, altars[a].pos) - cambc::constants::submit_gems_range >= best_steps) continue;
            const auto& belief = world.altars[a];
            int steps = pathing.to_altar(a).at(here);
            if (steps == unreachable) continue;
            if (belief.enemy_lock) steps += belief.enemy_lock_hits > 0 ? belief.enemy_lock_hits : static_cast<int>(cambc::constants::altar_lock_hits);
            if (steps < best_steps) best = a, best_steps = steps;
        }
        any_locked = best >= 0;
        // Walking reaches only the altar we gave up waiting at, and no hop leads elsewhere when we
        // left: stop avoiding it rather than stand still. submit_here judges its safety again.
        if (best < 0 && world.round < memory.avoid_until) memory.avoid_until = world.round;
    }
    // A pack we would retreat from stands in the way: around it within the usual detour, else
    // wait outside it until it leaves or a recall (recall_to_bank) takes the bag home.
    if (const auto* zone = pack_zone(world)) {
        if (any_locked && world.altars[best].enemy_lock && break_lock(world, best) && !world.me().facts().walk_and_attack_independent())
            return;
        if (pathing.step_towards(any_locked ? pathing.to_altar(best) : pathing.to_any_altar(), zone)) submit_here(world, safety, memory);
        return;
    }
    const int walk_steps = any_locked ? best_steps : pathing.to_any_altar().at(here);
    if (const auto hop = hop_route(world, pathing, memory); hop.hop >= 0 && hop.steps < walk_steps) {
        memory.wants_crystal = true;
        if (carries_crystal()) {
            take_hop(world, pathing, safety, hop.hop);
            return;
        }
    }
    const Field& field = any_locked ? pathing.to_altar(best) : pathing.to_any_altar();
    if ((dash_across(world, pathing, field) || dash_towards(world, pathing, field)) && submit_here(world, safety, memory)) return;
    if (any_locked && world.altars[best].enemy_lock && break_lock(world, best) && !world.me().facts().walk_and_attack_independent())
        return;
    if (heal_step && willow_bank_heal_step(world, pathing, safety, field)) {
        submit_here(world, safety, memory);
        return;
    }
    step_safely(world, pathing, field, safety);
    submit_here(world, safety, memory);
}

// output(), at least 1: a divisor for clear times.
float floored_output(const ChampionBelief& c) { return std::max(1.0f, output(c)); }

bool has_family(const cambc::enum_map<cambc::item_type>& owned, int family) {
    return owned[emblem_of(family, strength_stat)] + owned[emblem_of(family, focus_stat)] + owned[emblem_of(family, health_stat)] > 0;
}

// Camp damage dealt per point owning `owned` and an emblem of `added` (-1: none): Monster's, and
// Collectors' per family owned.
float camp_dealt_with(const cambc::enum_map<cambc::item_type>& owned, int added = -1) {
    float dealt = added == monster || has_family(owned, monster) ? monster_camp_dealt : 1.0f;
    if (added == collectors || has_family(owned, collectors)) {
        int families = added >= 0 && !has_family(owned, added);
        for (int f = monster; f <= collectors; ++f) families += has_family(owned, f);
        dealt *= 1.0f + collectors_dealt * static_cast<float>(families);
    }
    return dealt;
}

} // namespace

float camp_hit_factor() {
    const auto& owned = my_items();
    return (has_family(owned, jungle) ? jungle_camp_taken : 1.0f) * (has_family(owned, durability) ? durability_taken : 1.0f);
}

float camp_dealt_factor() { return camp_dealt_with(my_items()); }

namespace {

// A farm cycle's worth a round, falling faster than 1 / rounds for long cycles: gems taken sooner
// turn into shards sooner, and a long clear is more often contested or cut short. On a large map
// every walk is long, so the horizon grows with it.
constexpr float cycle_horizon = 100;
float rate(const World& world, float worth, float rounds) {
    static float horizon = 0;
    if (horizon <= 0) {
        const auto& map = world.map();
        horizon = cycle_horizon * std::max(1.0f, static_cast<float>(std::max(map.width, map.height)) / 50.0f);
    }
    // A guard: farm floors its trip, so a cycle is at least the capture.
    rounds = std::max(rounds, 1.0f);
    return worth / (rounds * (1.0f + rounds / horizon));
}

// Rounds from the first hold of a cleared group to its payout: `fast` when a Capture emblem's owner holds.
int capture_rounds(bool fast) { return (fast ? capture_emblem_time : cambc::constants::capture_time) + 1; }
// Ours: an ally's Capture emblem on the hold is not counted.
int capture_rounds(const World& world) { return capture_rounds(world.me().fast_capture); }
constexpr float stickiness = 1.2f;

struct CampLeft {
    float health, strength;
};

// Damage taken clearing a group alone at `strength` a turn (callers pass floored_output, spells
// included), killing the deadliest first; also the rounds it takes. `reflect`: damage each hit on us
// returns to its monster (Ren). `left`: the living members, deadliest first; the reflect path wears it down.
float min_camp_damage(CampLeft* left, int n, float strength, float* rounds, float reflect) {
    float damage = 0, elapsed = 0;
    if (reflect <= 0) {
        for (int i = 0; i < n; ++i) {
            elapsed += std::ceil(left[i].health / strength);
            damage += left[i].strength * (elapsed - 1);
        }
        *rounds = elapsed;
        return damage;
    }
    // Only members that strike take the reflection.
    int attackers = n;
    while (attackers > 0 && left[attackers - 1].strength <= 0) --attackers;
    // Each round we hit the first living target, then every living attacker hits us and takes the
    // reflection. Stepped from one death to the next.
    for (int i = 0; i < n;) {
        const float own = left[i].strength > 0 ? reflect : 0.0f;
        float k = std::max(1.0f, std::ceil(left[i].health / (strength + own)));
        for (int j = i + 1; j < attackers; ++j)
            if (left[j].health > 0 && left[j].strength > 0) k = std::min(k, std::max(1.0f, std::ceil(left[j].health / reflect)));
        // Our hit in round k fells it before it strikes; otherwise it struck every round.
        const float hits = left[i].health - k * strength - (k - 1) * own <= 0 ? k - 1 : k;
        damage += left[i].strength * hits;
        left[i].health -= k * strength + hits * own;
        for (int j = i + 1; j < attackers; ++j)
            if (left[j].health > 0 && left[j].strength > 0) damage += left[j].strength * k, left[j].health -= k * reflect;
        elapsed += k;
        while (i < n && left[i].health <= 0) ++i;
    }
    *rounds = elapsed;
    return damage;
}

// Kept per group and strength while the group's belief is unchanged; the sorted members, for the
// last group asked, while its belief is.
float min_camp_damage(const World& world, int g, float strength, float* rounds, float reflect = 0) {
    const auto& group = world.map().groups[g];
    const auto& belief = world.camps[g];
    struct Slots {
        std::uint32_t version = ~0u;
        int count = 0, next = 0;
        std::array<float, 4> strength{}, reflect{}, damage{}, rounds{};
    };
    // Static storage starts filled for free, where a vector pays to fill its slots.
    static std::array<Slots, 256> cache;
    static Slots uncached;
    const bool kept = static_cast<std::size_t>(g) < cache.size();
    auto& c = kept ? cache[g] : uncached;
    if (c.version != belief.version || !kept) {
        c.version = belief.version;
        c.count = c.next = 0;
    }
    for (int i = 0; i < c.count; ++i)
        if (c.strength[i] == strength && c.reflect[i] == reflect) {
            *rounds = c.rounds[i];
            return c.damage[i];
        }
    static std::vector<CampLeft> sorted, worn;
    static int sorted_group = -1, n = 0;
    static std::uint32_t sorted_version = 0;
    if (sorted_group != g || sorted_version != belief.version) {
        sorted_group = g, sorted_version = belief.version;
        if (sorted.size() < group.members.size()) sorted.resize(group.members.size()), worn.resize(group.members.size());
        int living = 0;
        CampLeft* out = sorted.data();
        const bool fresh = belief.state == CampState::respawning;
        for (std::size_t i = 0; i < group.members.size(); ++i) {
            const float hp = fresh ? group.members[i].max_health : belief.health[i];
            if (hp > 0) out[living++] = {hp, group.members[i].strength};
        }
        n = living;
        if (n > 1) std::sort(sorted.data(), sorted.data() + n, [](const CampLeft& a, const CampLeft& b) { return a.strength * b.health > b.strength * a.health; });
    }
    CampLeft* left = sorted.data();
    if (reflect > 0) left = std::copy_n(sorted.data(), n, worn.data()) - n;
    const int i = c.next;
    c.next = (c.next + 1) % static_cast<int>(c.strength.size());
    c.count = std::max(c.count, i + 1);
    c.strength[i] = strength;
    c.reflect[i] = reflect;
    c.damage[i] = min_camp_damage(left, n, strength, &c.rounds[i], reflect);
    *rounds = c.rounds[i];
    return c.damage[i];
}

// A group's weight by its side of the map: 1 in our half, falling towards the enemy spawn. Kept
// per group.
float home_ground(const StaticMap& map, int g) {
    struct Kept {
        float weight = -1; // until read
    };
    static std::array<Kept, 256> cache;
    float uncached = -1;
    auto& weight = static_cast<std::size_t>(g) < cache.size() ? cache[g].weight : uncached;
    if (weight < 0) {
        int from_us = map.ally_steps(g);
        int from_them = map.enemy_steps(g);
        // Beyond our walk (a crystal's region), both as the crow flies: else the enemy's doorstep counts in full.
        if (from_us == unreachable) {
            from_us = dist(map.ally_spawn_centre, map.groups[g].centre);
            from_them = dist(map.enemy_spawn_centre, map.groups[g].centre);
        }
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
    return damage * c.damage_scale();
}

// Basic attacks a turn, with the reset spread over its cooldown.
float basic_output(const ChampionBelief& c) {
    return c.strength * c.damage_scale() * (c.facts().has_attack_reset() ? 1.0f + 1.0f / static_cast<float>(ability_cooldown) : 1.0f);
}

// Bit i: member i deals no damage and a basic attack of `range` reaches it from a tile out of the
// reach of every member that does. Static, so kept per group.
std::uint32_t safe_targets(const StaticMap& map, int g, int range) {
    struct Kept {
        std::array<std::int64_t, 2> bits{-1, -1}; // until read
    };
    static std::array<Kept, 256> cache;
    std::int64_t uncached = -1;
    auto& bits = static_cast<std::size_t>(g) < cache.size() ? cache[g].bits[range > 1] : uncached;
    if (bits < 0) {
        bits = 0;
        const auto& members = map.groups[g].members;
        bool mixed = false;
        for (const auto& m : members) mixed |= m.strength <= 0;
        if (mixed) {
            static bitboard open{cambc::uninitialized}, reach{cambc::uninitialized};
            reach.clear();
            for (const auto& m : members)
                if (m.strength > 0) reach.draw_chebyshev(m.pos, m.reach);
            or_into(map.standable, reach, open);
            open ^= reach; // standable & ~reach
            for (std::size_t i = 0; i < members.size() && i < 32; ++i)
                if (members[i].strength <= 0 && any_within(open, members[i].pos, range)) bits |= std::int64_t{1} << i;
        }
    }
    return static_cast<std::uint32_t>(bits);
}

// Rounds to clear a group alone without taking a hit: damage spells from 4 on the members that
// attack, basic attacks on the others from out of the attackers' range, or once they are dead.
// Negative if no spell can reach an attacker, or one reaches as far as our spells. `spells` and `basic`: our spell_output and
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
        if (members[i].strength > 0 && members[i].reach >= ability_range) return -1;
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
    static std::array<Kept, 256> kept;
    Kept uncached;
    auto& k = static_cast<std::size_t>(g) < kept.size() ? kept[g] : uncached;
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
    static std::array<Kept, 256> kept;
    Kept uncached;
    auto& k = static_cast<std::size_t>(g) < kept.size() ? kept[g] : uncached;
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

// Our share of the gems still to farm takes about rounds_per_gem each.
constexpr float rounds_per_gem = 2.3f;

// Our share of the gems still to farm before either team reaches the win or the game ends, at the
// team's tribute rate and at our own pace.
float gems_share(const World& world) {
    int alive = 0;
    for (const auto& a : world.allies) alive += a.alive;
    const int rounds = bag_rounds_left(world);
    int left = std::min(gems_short(world), static_cast<int>(cambc::constants::winning_gems) - world.score.enemy);
    if (const float rate = world.ally_rate(); rate > 0) left = std::min(left, static_cast<int>(rate * static_cast<float>(rounds)));
    return std::min(static_cast<float>(std::max(0, left)) / static_cast<float>(std::max(1, alive)),
                    static_cast<float>(rounds) / rounds_per_gem);
}

// Our upkeep so far, over the turns we were alive: turns spent damaging camps, damage taken from
// camps and from champions, and steps from spawn (the walk back out after a heal).
struct Upkeep {
    int turns = 0, camp_turns = 0, spawn_turns = 0;
    float camp_taken = 0, champ_taken = 0, spawn_steps = 0;
};
Upkeep upkeep;

// At the turn's start: camps hit in the camp phase, from where we ended last turn.
void note_upkeep(const World& world, Safety& safety, float damage) {
    const auto& map = world.map();
    const vec2 here = world.me().pos;
    ++upkeep.turns;
    if (damage > 0) {
        const float camp = std::min(damage, safety.camp_damage(here));
        upkeep.camp_taken += camp;
        upkeep.champ_taken += damage - camp;
    }
    if (map.from_ally_spawn_ready())
        if (const int s = map.from_ally_spawn().at(here); s != unreachable) upkeep.spawn_steps += static_cast<float>(s), ++upkeep.spawn_turns;
}

// A Treasure, Jungle, Power, Durability, Bruiser or 2.0.0-family shard short of its emblem (Vendetta's Monster too).
bool emblem_begun(const World& world) {
    const auto& owned = my_items();
    for (const int family : {treasure, jungle, power, durability, bruiser, tribute, capture, prospector, hunter, skirmish, greed, collectors})
        for (int stat = strength_stat; stat <= health_stat; ++stat)
            if (owned[shard_of(family, stat)] > 0) return true;
    if (world.me().facts().passive == Passive::reset_on_kill && owned[shard_of(monster, strength_stat)] > 0) return true;
    return world.me().facts().passive == Passive::gem_focus
        && (owned[shard_of(home, health_stat)] > 0 || owned[shard_of(monster, health_stat)] > 0
            || owned[shard_of(monster, focus_stat)] > 0);
}

// Our stats, damage taken (Jungle and Durability), and camp damage dealt (Monster, Collectors).
struct Build {
    float strength = 0, focus = 0, max_health = 0, camp_taken = 1, taken = 1, camp_dealt = 1;
    int recall = static_cast<int>(cambc::constants::recall_time);
};

// Our build with `bought` added to our stats, owning `owned`.
Build build_of(const World& world, const cambc::enum_map<cambc::item_type>& owned, const Build& bought) {
    const auto& self = world.me();
    return Build{self.strength + bought.strength, self.focus + bought.focus, self.max_health + bought.max_health,
                 has_family(owned, jungle) ? jungle_camp_taken : 1.0f, has_family(owned, durability) ? durability_taken : 1.0f,
                 camp_dealt_with(owned), has_family(owned, home) ? home_recall_time : recall_turns(world)};
}

void add_shards(Build& b, const ChampionFacts& f, int stat, float shards) {
    if (stat == strength_stat) b.strength += shards * f.strength.growth;
    if (stat == focus_stat) b.focus += shards * f.focus.growth;
    if (stat == health_stat) {
        b.max_health += shards * f.health.growth;
        if (f.passive == Passive::health_strength)
            b.strength += cambc::constants::passive_abilities::ryth_health_strength_ratio * shards * f.health.growth;
    }
}

// What completing an emblem adds beyond its shards: Power a sixth shard, Bruiser one of each other
// stat, Greed ten more.
void add_completion(Build& b, const ChampionFacts& f, int family, int stat) {
    if (family == power) add_shards(b, f, stat, 1);
    if (family == greed) add_shards(b, f, stat, static_cast<float>(greed_stats - greed_shards));
    if (family == bruiser)
        for (int s = strength_stat; s <= health_stat; ++s)
            if (s != stat) add_shards(b, f, s, 1);
}

// Where every gem is behind a siege, our upkeep before a camp has hit us: every turn on the nearest
// Monolith, alongside the others' output (`others`), its hits on the nearest of us (the melee while
// any lives) split by max health, the walk out its distance from spawn.
Upkeep siege_upkeep(const World& world, float& others) {
    const auto& map = world.map();
    Upkeep u;
    others = 0;
    int g = -1, steps = unreachable;
    for (int h = 0; h < static_cast<int>(map.groups.size()); ++h)
        if (map.groups[h].has_monolith && map.ally_steps(h) < steps) g = h, steps = map.ally_steps(h);
    if (g < 0) return upkeep;
    bool melee = false;
    for (const auto& a : world.allies) melee |= (a.alive || a.is_self) && !a.facts().ranged;
    float pool = 0;
    for (const auto& a : world.allies) {
        if (!a.alive && !a.is_self) continue;
        if (!a.is_self) others += floored_output(a);
        if (!melee || !a.facts().ranged) pool += a.max_health;
    }
    const auto& self = world.me();
    u.turns = u.camp_turns = u.spawn_turns = std::max(1, upkeep.turns);
    u.spawn_steps = static_cast<float>(steps * u.turns);
    u.champ_taken = upkeep.champ_taken;
    if (!melee || !self.facts().ranged)
        u.camp_taken = map.groups[g].strength * params::siege_hit_share * camp_hit_factor() * self.max_health / pool * static_cast<float>(u.turns);
    return u;
}

// Rounds a turn of ours costs in clearing and heal trips at upkeep u, with build b: the clearing
// share shrinks with our output (beside the others' on the same camps), as do the camps' hits taken
// meanwhile; health lost comes back by a recall and the walk out, a trip per usable health (above
// the recall line).
float upkeep_cost(const World& world, const Upkeep& upkeep, float others, const Build& now, const Build& b) {
    const auto out = [&](const Build& x) { return std::max(1.0f, raw_output(world.me().facts(), x.strength, x.focus)); };
    const float turns = static_cast<float>(std::max(1, upkeep.turns));
    const float steps = upkeep.spawn_turns > 0 ? upkeep.spawn_steps / static_cast<float>(upkeep.spawn_turns) : 0.0f;
    const float clear = (others + out(now) * now.camp_dealt) / (others + out(b) * b.camp_dealt);
    const float camp = upkeep.camp_taken / turns * clear * b.camp_taken / now.camp_taken;
    const float taken = (camp + upkeep.champ_taken / turns) * b.taken / now.taken;
    const float usable = b.max_health * (1.0f - params::recall_health_fraction);
    // Counted from one clearing turn in one: before our first camp hit, gold (priced by this
    // saving) is still worth farming.
    const float clearing = static_cast<float>(upkeep.camp_turns + 1) / static_cast<float>(upkeep.turns + 1);
    return clearing * clear + taken * (static_cast<float>(b.recall) + steps) / usable;
}

// Our mean steps from spawn while alive: the walk back out after a heal.
float spawn_steps() { return upkeep.spawn_turns > 0 ? upkeep.spawn_steps / static_cast<float>(upkeep.spawn_turns) : 0.0f; }

// Rounds `damage` costs, priced as upkeep_cost prices it: a heal trip (a recall and the walk `out`
// back out) per usable health.
float heal_rounds(const World& world, float damage, float out) {
    const float usable = my_max_health() * (1.0f - params::recall_health_fraction);
    return damage / usable * (static_cast<float>(recall_turns(world)) + out);
}

// The emblem to complete next and the share of a turn it saves (upkeep_cost): a Power emblem in
// the main stat (6 shards' stats for 5), a Jungle one in it (-30% camp damage) or a Durability one
// in Health (-10% damage taken), whichever saves most; one already begun is finished first, priced
// by the shards left to buy (`cost` in gold).
struct Emblem {
    int family, stat;
    float saved;
    unsigned cost;
};
// `bought`: the stats of shards bought since the turn's start; `items`: what we would then own.
Emblem best_emblem(const World& world, const Build& bought = {}, const cambc::enum_map<cambc::item_type>* items = nullptr) {
    const auto& f = world.me().facts();
    const auto& owned = items ? *items : my_items();
    const auto& self = world.me();
    const Build now = build_of(world, owned, bought);
    float others = 0;
    const Upkeep u = world.map().monolith_only && upkeep.camp_taken <= 0 ? siege_upkeep(world, others) : upkeep;
    const float base = upkeep_cost(world, u, others, now, now);
    const bool collecting = has_family(owned, collectors); // every new family adds to its camp damage
    const auto value = [&](int family, int stat) __attribute__((always_inline)) -> Emblem {
        const unsigned left = shards_needed(family) - owned[shard_of(family, stat)];
        Build b = now;
        add_shards(b, f, stat, static_cast<float>(left));
        add_completion(b, f, family, stat);
        if (family == jungle) b.camp_taken = jungle_camp_taken;
        if (family == durability) b.taken = durability_taken;
        if (family == monster || family == collectors || collecting) b.camp_dealt = camp_dealt_with(owned, family);
        if (family == home) b.recall = home_recall_time;
        return {family, stat, base - upkeep_cost(world, u, others, now, b), left * shard_price};
    };
    if (f.passive == Passive::gem_focus && owned[shard_of(monster, health_stat)] > 0) return value(monster, health_stat);
    if (f.passive == Passive::gem_focus && owned[shard_of(monster, focus_stat)] > 0) return value(monster, focus_stat);
    if (f.passive == Passive::reset_on_kill && owned[shard_of(monster, strength_stat)] > 0) return value(monster, strength_stat);
    // In the stat it was begun in: the main stat follows our use and can change.
    const int begun[8][2] = {{jungle, strength_stat}, {jungle, focus_stat}, {power, strength_stat}, {power, focus_stat}, {durability, health_stat},
                             {bruiser, strength_stat}, {bruiser, focus_stat}, {bruiser, health_stat}};
    for (const auto& [family, stat] : begun)
        if (owned[shard_of(family, stat)] > 0) return value(family, stat);
    for (int family = tribute; family <= collectors; ++family)
        for (int stat = strength_stat; stat <= health_stat; ++stat)
            if (owned[shard_of(family, stat)] > 0) return value(family, stat);
    if (f.heals() && owned[shard_of(jungle, health_stat)] > 0)
        return value(jungle, health_stat);
    if (f.passive == Passive::gem_focus) {
        for (const int family : {power, jungle, home})
            if (owned[shard_of(family, health_stat)] > 0) return value(family, health_stat);
        Emblem best = value(power, health_stat);
        if (const auto e = value(bruiser, health_stat); e.saved > best.saved) best = e;
        if (const auto e = value(bruiser, focus_stat); e.saved > best.saved) best = e;
        if (const auto e = value(jungle, health_stat); e.saved > best.saved) best = e;
        if (const auto e = value(durability, health_stat); e.saved > best.saved) best = e;
        if (!has_family(owned, monster))
            if (const auto e = value(monster, health_stat); e.saved > best.saved) best = e;
        if (!has_family(owned, home))
            if (const auto e = value(home, health_stat); e.saved > best.saved) best = e;
        if (const auto e = value(power, focus_stat); e.saved > best.saved) best = e;
        if (!has_family(owned, monster))
            if (const auto e = value(monster, focus_stat); e.saved > best.saved) best = e;
        return best;
    }
    const int main = main_stat(world);
    Emblem best = value(power, main);
    if (const auto e = value(jungle, main); e.saved > best.saved) best = e;
    if (const auto e = value(durability, health_stat); e.saved > best.saved) best = e;
    if (const auto e = value(bruiser, main); e.saved > best.saved) best = e;
    if (const auto e = value(bruiser, health_stat); e.saved > best.saved) best = e;
    if (f.heals() && !has_family(owned, jungle))
        if (const auto e = value(jungle, health_stat); e.saved > best.saved) best = e;
    // Vendetta's high base Strength makes +15% on camps worth more than a sixth shard.
    if (f.passive == Passive::reset_on_kill && !has_family(owned, monster))
        if (const auto e = value(monster, strength_stat); e.saved > best.saved) best = e;
    // Treasure first, in the stat the model picks and priced as the emblem it delays: at 1.x's +20%
    // gold, from round ~200 it bought 5-8 more shards a champion (ladder), more than any first
    // passive saved; 2.0.0's +10% about halves that, not yet re-tested. Vendetta's in Health, as 74% of ladder Vendettas: the model prices Health only by heal trips.
    if (!has_family(owned, treasure)) {
        int stat = f.passive == Passive::reset_on_kill ? health_stat : best.stat;
        for (int s = strength_stat; s <= health_stat; ++s)
            if (owned[shard_of(treasure, s)] > 0) stat = s;
        return {treasure, stat, best.saved, (shards_per_emblem - owned[shard_of(treasure, stat)]) * shard_price};
    }
    return best;
}

// True if any shard was bought.
bool buy_shards(const World& world) {
    unsigned gold = my_gold();
    if (gold < shard_price) return false;
    const unsigned start = gold;
    Build bought;
    while (gold >= shard_price) {
        const auto [family, stat, saved, cost] = best_emblem(world, bought);
        const unsigned have = my_items()[shard_of(family, stat)];
        const unsigned count = std::min<unsigned>(shards_needed(family) - have, gold / shard_price);
        if (!buy(shard_of(family, stat), count)) break;
        gold -= shard_price * count;
        add_shards(bought, world.me().facts(), stat, static_cast<float>(count));
        if (have + count == shards_needed(family)) add_completion(bought, world.me().facts(), family, stat);
    }
    return gold < start;
}

// Gold paid per base gold of a capture to a champion owning `owned`: the Treasure and Vesper Vale bonuses add.
float gold_rate(const ChampionFacts& f, const cambc::enum_map<cambc::item_type>& owned) {
    float rate = has_family(owned, treasure) ? 1.0f + treasure_gold : 1.0f;
    if (f.passive == Passive::bonus_gold)
        rate += static_cast<float>(cambc::constants::passive_abilities::vesper_vale_bonus_gold_percent) / 100.0f;
    return rate;
}

float gold_paid(const World& world) { return gold_rate(world.me().facts(), my_items()); }

// A visible ally's, read from its items.
float gold_paid(const ChampionBelief& a) {
    static cambc::enum_map<cambc::item_type> owned; // overwritten whole
    ok(cambc::detail::sdk_champion_items(static_cast<std::uint32_t>(a.handle), owned.ptr()));
    return gold_rate(a.facts(), owned);
}

// The next emblem (best_emblem), the rounds it saves us over our share of the gems still to farm,
// and the gems a gold is worth (its part of that saving). Kept while our share and stats hold: the
// upkeep counters under them move every turn, and every farm value would be rebuilt.
struct Prices {
    Emblem next;
    float gain, per_gold;
};
const Prices& prices(const World& world) {
    struct Key {
        float share, strength, focus, max_health;
        int main;
        bool home, monster;
        bool operator==(const Key&) const = default;
    };
    static Key last{-1};
    static Prices kept;
    const auto& self = world.me();
    if (const Key now{gems_share(world), self.strength, self.focus, self.max_health, main_stat(world),
                      self.facts().passive == Passive::gem_focus && has_family(my_items(), home),
                      self.facts().passive == Passive::gem_focus && has_family(my_items(), monster)}; !(now == last)) {
        last = now;
        kept.next = best_emblem(world);
        kept.gain = now.share * kept.next.saved * rounds_per_gem;
        kept.per_gold = now.share * kept.next.saved / static_cast<float>(std::max(1u, kept.next.cost));
    }
    return kept;
}

struct PurchaseQuote {
    Emblem next{};
    unsigned count = 0;
    float gain = 0;
};

// Everything `gold_in` more gold buys, as buy_shards buys it, and the rounds it saves us over our
// share of the gems still to farm. The saving is kept while our gold and stats hold.
PurchaseQuote affordable_prefix(const World& world, unsigned gold_in = 0) {
    const unsigned budget = my_gold() + gold_in;
    if (budget < shard_price) return {};
    const auto& self = world.me();
    struct Key {
        unsigned shards;
        float strength, focus, max_health;
        bool operator==(const Key&) const = default;
    };
    static Key last{~0u};
    static PurchaseQuote kept;
    const Key key{budget / shard_price, self.strength, self.focus, self.max_health};
    const float rounds = gems_share(world) * rounds_per_gem;
    if (key == last) return {kept.next, kept.count, kept.gain * rounds};
    last = key;
    const auto& f = self.facts();
    auto owned = my_items();
    const auto build = [&](const Build& bought) { return build_of(world, owned, bought); };
    const Build now = build({});
    PurchaseQuote quote{best_emblem(world)};
    Build bought;
    for (unsigned gold = budget; gold >= shard_price;) {
        const auto e = quote.count == 0 ? quote.next : best_emblem(world, bought, &owned);
        const unsigned have = owned[shard_of(e.family, e.stat)];
        const unsigned count = std::min<unsigned>(shards_needed(e.family) - have, gold / shard_price);
        gold -= shard_price * count;
        quote.count += count;
        add_shards(bought, f, e.stat, static_cast<float>(count));
        owned[shard_of(e.family, e.stat)] += count;
        if (have + count == shards_needed(e.family)) {
            add_completion(bought, f, e.family, e.stat);
            owned[shard_of(e.family, e.stat)] = 0;
            owned[emblem_of(e.family, e.stat)] += 1;
        }
    }
    float others = 0;
    const Upkeep u = world.map().monolith_only && upkeep.camp_taken <= 0 ? siege_upkeep(world, others) : upkeep;
    quote.gain = upkeep_cost(world, u, others, now, now) - upkeep_cost(world, u, others, now, build(bought));
    kept = quote;
    return {quote.next, quote.count, quote.gain * rounds};
}

// The way to an altar `walk` steps away, in rounds: walking, or a recall of `channel` turns
// (`overlap` of them spent anyway on a capture's remaining rounds), the heal turn when hurt (a
// recall lands at turn start, healing waits for the turn's end) and the walk from spawn, less what
// the stop is worth: the heal, and the next emblem once `gold_in` more gold completes it; nothing
// once the bag wins or the end is close. Below `walk` when the recall wins; never a recall that
// reaches the altar too late to tribute the bag by `deadline` rounds from now.
struct HomeTrip {
    int channel, from_spawn, hurt, deadline;
    float heal = 0, emblem = 0;
    std::uint32_t short_gold = ~0u;
    float value(std::uint32_t gold_in) const { return heal + (gold_in >= short_gold ? emblem : 0.0f); }
    float rounds(int walk, int overlap, std::uint32_t gold_in) const {
        const int arrive = std::max(0, channel - overlap) + hurt + from_spawn;
        if (from_spawn == unreachable || arrive > deadline) return static_cast<float>(walk);
        return std::min(static_cast<float>(walk), std::max(0.0f, static_cast<float>(arrive) - value(gold_in)));
    }
};
HomeTrip home_trip(const World& world, Pathing& pathing, int channel, bool wins) {
    HomeTrip t{channel, pathing.to_any_altar().at(world.map().ally_spawn_centre), my_health() < my_max_health() ? 1 : 0,
               bag_rounds_left(world) - tribute_turns(world, my_gems())};
    if (wins || closing(world, pathing)) return t;
    t.heal = heal_rounds(world, my_max_health() - my_health(), spawn_steps());
    if (!may_shop(world)) return t;
    const auto& p = prices(world);
    const std::uint32_t gold = my_gold();
    t.short_gold = gold >= p.next.cost ? 0 : p.next.cost - gold;
    t.emblem = p.gain;
    return t;
}

// Allies other than us in sight on `tiles`; with `below`, only those of a lower index.
int allies_on(const World& world, const bitboard& tiles, int below = 1 << 30) {
    int n = 0;
    for (const auto& a : world.allies) n += !a.is_self && a.alive && a.visible && a.index < below && test(tiles, a.pos);
    return n;
}

bool enemy_on(const World& world, const bitboard& tiles) {
    if (!enemy_seen(world)) return false;
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && test(tiles, e.pos)) return true;
    return false;
}

// Our part of the gems a capture we stand on pays: shares are floored, the lowest id gets the rest.
// Our part of `amount` split over the allies on `tiles` and us: the floor share, and the remainder
// to the lowest id.
int split_share(const World& world, const bitboard& tiles, int amount) {
    const int sharers = 1 + allies_on(world, tiles);
    const bool lowest = allies_on(world, tiles, world.me().index) == 0;
    return amount / sharers + (lowest ? amount % sharers : 0);
}

// A Prospector emblem's owner's extra on `cluster` split `sharers` ways: a part of its share, rounded down.
int prospected(int cluster, int sharers) { return cluster / sharers / prospector_part; }

int capture_share(const World& world, int g) {
    const auto& G = world.map().groups[g];
    int share = split_share(world, G.tiles(), G.gems);
    if (world.me().prospector) share += prospected(G.cluster_gems, 1 + allies_on(world, G.tiles()));
    return share;
}

// Our base gold from a capture of G, as capture_share.
int gold_share(const World& world, const CampGroup& G) {
    int share = split_share(world, G.tiles(), G.gold);
    if (world.me().prospector) share += prospected(G.cluster_gold, 1 + allies_on(world, G.tiles()));
    return share;
}

// A group other than a Monolith too big for one champion or a crew, like stampede's shared block
// of elk and gem clusters.
bool big_group(const CampGroup& G) { return !G.has_monolith && G.gems >= params::big_gems; }

// Split until each share's tribute fits the window its safety is judged over (tribute_safe).
int holders(const CampGroup& G) {
    int n = 1;
    while (n < params::big_holders && tribute_turns((G.gems + n - 1) / n, false) > params::tribute_window) ++n;
    return n;
}

const ChampionBelief* prism_capture_holder(const World& world, const CampGroup& G) {
    if (G.gems <= 0 || enemy_seen(world) || enemy_on(world, G.tiles())) return nullptr;
    for (const auto& a : world.allies) {
        if (!a.alive || !a.visible || a.facts().passive != Passive::gem_focus) continue;
        const vec2 p = a.is_self ? my_position() : a.pos;
        if (!test(G.tiles(), p) || a.health < params::hurt_health_fraction * a.max_health
            || a.channel == Channel::tribute || a.channel == Channel::teleport
            || (a.channel == Channel::recall && a.channel_end_round <= world.round + 1)
            || world.score.ally + a.gems + G.gems >= static_cast<int>(cambc::constants::winning_gems)
            || rounds_left(world) <= tribute_turns(a.gems + G.gems, a.fast_tribute) + world.map().width + world.map().height + endgame_margin)
            continue;
        bool pressure = false;
        for (const auto& e : world.enemies)
            pressure |= e.alive && e.age(world.round) <= params::track_horizon
                        && dist(e.pos, p) <= vision_radius + e.age(world.round);
        if (pressure) continue;
        return &a;
    }
    return nullptr;
}

// A hold whose payout falls after the last round never pays.
bool pays_too_late(const CampBelief& c) {
    return c.held_since >= 0 && c.payout_round() > static_cast<int>(cambc::constants::max_rounds);
}

// On a cleared group's tile that no lower-id ally also holds, with no enemy on any of its tiles:
// stepping off loses the capture's progress, and it pays within six rounds.
bool holding_capture(const World& world, Pathing& pathing) {
    const vec2 here = my_position();
    const int g = world.map().group_at(here);
    if (g < 0 || world.camps[g].state != CampState::cleared || winning_bag(world)) return false;
    const auto& c = world.camps[g];
    if (pays_too_late(c)) return false;
    // Waiting for the payout must still leave the walk and the whole bag's tribute before the limit.
    // A bag too late to bank even now gains nothing by leaving: the hold still pays gold (a tiebreak).
    if (my_gems() > 0 && c.held_since >= 0) {
        const int walk = pathing.to_any_altar().at(here);
        if (walk != unreachable && walk + tribute_turns(world, my_gems()) + endgame_slack <= rounds_left(world)
            && std::max(0, c.payout_round() - world.round) + walk + tribute_turns(world, my_gems() + capture_share(world, g))
                       + endgame_slack > rounds_left(world))
            return false;
    }
    const auto& tiles = world.map().groups[g].tiles();
    // Prism stays while a lower-id holder leaves; the last holder never yields to a remote ally.
    if (const auto* prism = prism_capture_holder(world, world.map().groups[g]); prism && prism->is_self) return true;
    return allies_on(world, tiles, world.me().index) < holders(world.map().groups[g]) && !enemy_on(world, tiles);
}

// Allies on cleared group g's tiles make a hold's holders already: those of lower id, if we stand on one.
bool contest_manned(const World& world, int g, vec2 here) {
    const auto& G = world.map().groups[g];
    return allies_on(world, G.tiles(), test(G.tiles(), here) ? world.me().index : 1 << 30) >= holders(G);
}

bool yield_capture(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    if (!my_can_move() || memory.damage > 0 || winning_bag(world)) return false;
    const vec2 here = my_position();
    const auto& map = world.map();
    const int g = map.group_at(here);
    if (g < 0 || world.camps[g].state != CampState::cleared) return false;
    const auto* prism = prism_capture_holder(world, map.groups[g]);
    if (!prism || prism->is_self || safety.any_threat() || safety.camp_damage(prism->pos) > 0) return false;
    const auto& blocked = pathing.blocked();
    for (const auto d : directions) {
        const vec2 p = here + d;
        if (!in_bounds(p) || test(map.groups[g].tiles(), p) || !test(map.standable, p)
            || test(blocked, p) || safety.camp_damage(p) > 0) continue;
        world.throw_if_stale();
        const bool moved = pathing.try_move(p);
        // Before the stale check: a turn resumed late has still made the move.
        if (moved) {
            memory.claim = memory.farm_group = -1;
            memory.crew = false;
            decision = 'F';
        }
        world.throw_if_stale();
        if (moved) return true;
    }
    return false;
}

// A dasher paid more gold takes a one-holder gold capture from a higher-id ally paid less. Arrive
// before it leaves: only its actual observation of our lower-id body releases the hold.
bool take_capture_handoff(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    if (!world.me().facts().has_dash() || memory.banking || memory.damage > 0
        || memory.round != world.round - 1 || memory.claim < 0 || memory.live_claim != memory.claim
        || !my_can_move() || !my_can_cast() || channelling() || winning_bag(world))
        return false;
    const int g = memory.claim;
    const auto& map = world.map();
    if (g >= static_cast<int>(map.groups.size())) return false;
    const auto& G = map.groups[g];
    const auto& c = world.camps[g];
    const vec2 here = my_position();
    if (c.state != CampState::cleared || c.state_round != world.round || c.holder != team::ally
        || G.has_monolith || G.gold <= 0 || holders(G) != 1 || test(G.tiles(), here)
        || holding_capture(world, pathing) || enemy_seen(world))
        return false;
    for (const auto& m : G.members)
        if (!test(world.visible, m.pos)) return false;
    const ChampionBelief* incumbent = nullptr;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible || !test(G.tiles(), a.pos)) continue;
        if (incumbent || a.index <= world.me().index || gold_paid(a) >= gold_paid(world)
            || a.channel == Channel::tribute || a.channel == Channel::teleport
            || (a.channel == Channel::recall && a.channel_end_round <= world.round + 1))
            return false;
        incumbent = &a;
    }
    if (!incumbent || world.score.ally + static_cast<int>(my_gems()) + incumbent->gems + G.gems
                          >= static_cast<int>(cambc::constants::winning_gems)
        || rounds_left(world) <= tribute_turns(world, my_gems() + G.gems) + map.width + map.height + endgame_margin
        || safety.any_threat() || safety.camp_damage(here) > 0 || safety.camp_damage(incumbent->pos) > 0)
        return false;
    const int dash = world.me().facts().slot_of(AbilityKind::dash);
    if (dash < 0 || !world.me().ability_ready(dash, world.round) || my_cooldown(dash) > 0) return false;
    std::optional<vec2> landing;
    int steps = unreachable;
    for (const auto p : Tiles<5 * 5>{pathing.dash_landings()}) {
        if (!test(G.tiles(), p) || !test(world.visible, p) || safety.camp_damage(p) > 0) continue;
        const int d = dist(here, p);
        if (!landing || d < steps || (d == steps && tile_index(p) < tile_index(*landing))) landing = p, steps = d;
    }
    if (!landing) return false;
    world.throw_if_stale();
    bool cast = false;
    try {
        cast = cast_slot(dash, *landing);
    } catch (const cambc::error&) {
    }
    // Memory before the stale check: a turn resumed late has still made the move.
    bool arrived = false;
    if (cast) {
        pathing.invalidate();
        arrived = my_position() == *landing;
        if (arrived) {
            memory.farm_group = g;
            memory.crew = false;
            decision = 'P';
        }
    }
    world.throw_if_stale();
    if (!arrived) return false;
    debug_block({ std::printf("HANDOFF %d %d incumbent %d acted %d landing %d %d\n", world.round, g,
                             incumbent->index, static_cast<int>(incumbent->acted), landing->x, landing->y); });
    return true;
}

bool ally_engaged(const World& world, int group) { return allies_on(world, world.map().groups[group].threat()) > 0; }

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

// Carrying gems, farming on chains a capture onto the bag: it saves the walk to the altar and
// back but keeps the bag at risk for longer. It goes ahead only if the next group, by the time it
// adds to the trip, beats the best cycle starting from the altar; false means bank instead.
[[gnu::flatten]] bool farm(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    world.throw_if_stale();
    if (pick_up(world, pathing, memory)) return true;
    const auto& map = world.map();
    const auto& groups = map.groups;
    const int range = world.me().facts().attack_range();
    const float strength = floored_output(world.me()), soften = camp_hit_factor(), reflect = world.me().retaliation();
    const float max_health = my_max_health();
    const float spare_health = (my_health() - params::recall_health_fraction * max_health) / params::camp_risk;
    const int bag = bankable_bag(world, pathing);
    const bool banks_bag = bag > 0 && !retaining_gems(world, pathing);
    const int short_by = gems_short(world);
    if (world.is_stale()) return true;
    // Groups in passing pay too (gold clusters are never chosen below), but not one whose clear
    // costs more health than we can spare.
    const auto affordable = [&](int g) __attribute__((always_inline)) {
        if (g == memory.farm_group || groups[g].strength <= 0) return true;
        float rounds = 0;
        return soften * min_camp_damage(world, g, strength, &rounds, reflect) <= spare_health || ally_engaged(world, g);
    };
    std::array<std::uint64_t, 4> ally_claims{}; // bit g: comms carries groups below 255
    for (const auto& a : world.allies)
        if (const int c = comms::claim_of(world, a.index); !a.is_self && c >= 0 && c < 256) ally_claims[c >> 6] |= std::uint64_t{1} << (c & 63);
    // An ally's claim makes us its crew rather than its rival, unless we claimed it first.
    const auto taken = [&](int g) __attribute__((always_inline)) {
        return g < 256 && (ally_claims[g >> 6] >> (g & 63) & 1) && (memory.claim != g || memory.crew);
    };
    const bool melee = world.me().facts().walk_and_attack_independent();
    // Cassi farms gold: the team's weakest body takes the harmless gold-only groups.
    const bool gold_farmer = world.me().facts().passive == Passive::linked_pair && !melee;
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
    const auto partial_trace = [&](const char* reason, int alternative, int resource, float hp = 0, float damage = 0, bool accepted = false) {
        debug_block({
            static unsigned accepted_rows = 0, other_rows = 0;
            auto& rows = accepted ? accepted_rows : other_rows;
            if (rows < 256) {
                ++rows;
                std::printf("FPARTIAL %d %u alternative %d resource %d hp %.9g basic %.9g farm %d claim %d crew %d reason %s\n",
                            world.round, my_handle(), alternative, resource, hp, damage,
                            memory.farm_group, memory.claim, static_cast<int>(memory.crew), reason);
            }
        });
    };
    const auto prefer_partial = [&](const CampAttackTargets& ordinary, const CampAttackTargets& resources) {
        if (ordinary.n == 0 || resources.n == 0) return -1;
        const auto& alternative = ordinary.found[0];
        const int g = alternative.group;
        const auto refuse = [&](const char* reason) { partial_trace(reason, g, -1); return -1; };
        if (decision != 'F' || memory.banking || memory.siege || siege_group() >= 0) return refuse("nonordinary");
        if (holding_capture(world, pathing)) return refuse("holding-capture");
        const auto& G = groups[g];
        const auto& c = world.camps[g];
        if (G.has_monolith || G.members[alternative.member].strength <= 0 || c.state != CampState::alive)
            return refuse("alternative-harmless");
        const vec2 here = my_position();
        bool striker = false;
        for (int i = 0; i < static_cast<int>(G.members.size()); ++i) {
            if (G.members[i].strength <= 0) continue;
            if (!test(world.visible, G.members[i].pos) || c.health_round[i] != world.round || !(c.health[i] >= 0))
                return refuse("alternative-unobserved");
            if (c.health[i] <= 0) continue;
            striker = true;
            if (!c.member_asleep(i)) return refuse("alternative-awake");
        }
        if (!striker) return refuse("alternative-no-striker");
        const auto live = my_record();
        const float basic = live.strength * damage_scale(world.me().facts().passive, live.health, live.max_health)
                            * camp_dealt_factor();
        const float hp = c.health[alternative.member];
        if (!(basic > 0) || !(hp > basic)) {
            partial_trace("alternative-lethal", g, -1, hp, basic);
            return -1;
        }
        std::array<int, 16> checked;
        int n_checked = 0;
        for (int k = 0; k < resources.n; ++k) {
            const int h = resources.found[k].group;
            if (std::find(checked.begin(), checked.begin() + n_checked, h) != checked.begin() + n_checked) continue;
            checked[n_checked++] = h;
            const auto reject = [&](const char* reason) { partial_trace(reason, g, h, hp, basic); };
            const auto& H = groups[h];
            const auto& known = world.camps[h];
            // This admission tier must share any future farm-wide cleanup-delegation exclusion.
            if (h == g || H.has_monolith || H.strength > 0 || H.gems + H.gold <= 0 || known.state != CampState::alive) {
                reject("resource-not-live-harmless");
                continue;
            }
            // A different ally's actual claim wins even over our stale incumbent/claim.
            if ((h < 256 && (ally_claims[h >> 6] >> (h & 63) & 1))
                || prism_capture_holder(world, H) || allies_on(world, H.tiles()) >= holders(H)) {
                reject("resource-owned");
                continue;
            }
            bool partial = false, alive = false, fresh = true, in_range = true, harmless = true;
            for (int i = 0; i < static_cast<int>(H.members.size()); ++i) {
                const auto& m = H.members[i];
                harmless &= m.strength <= 0;
                fresh &= test(world.visible, m.pos) && known.health_round[i] == world.round && known.health[i] >= 0;
                partial |= known.health[i] < m.max_health;
                if (known.health[i] <= 0) continue;
                alive = true;
                in_range &= dist(here, m.pos) <= range;
            }
            if (!harmless || !fresh || !alive || !partial || !in_range) {
                reject(!harmless ? "resource-harmful" : !fresh ? "resource-unobserved" : !alive ? "resource-cleared"
                       : !partial ? "resource-untouched" : "resource-out-of-range");
                continue;
            }
            partial_trace("candidate", g, h, hp, basic);
            return k;
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
            if (preferred >= 0) {
                const auto& target = resources.found[preferred];
                if (attack_camp_target(world, target)) {
                    hit = memory.farm_group = memory.claim = target.group;
                    memory.crew = false;
                    partial_trace("accepted", targets.found[0].group, hit, 0, 0, true);
                } else {
                    partial_trace("native-refused", targets.found[0].group, target.group);
                }
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

    // Short of fuel, walk on towards the last choice rather than run out mid-turn. Static fields
    // are kept, so after the first walk to a group this costs a descent.
    const int previous = memory.farm_group;
    // Beyond our walk: from a pocket the turn-end recall takes us home (continue_recall); from our
    // walk, the crystal's hop, by way of our spawn to buy one.
    const bool in_pocket = map.any_group_hop() && !test(pathing.foot(), here);
    const auto cross = [&](int g) {
        const int h = map.group_hop(g);
        if (in_pocket || h < 0) return false;
        memory.wants_crystal = true;
        if (!carries_crystal() && test(map.ally_spawn, here)) buy_crystal(memory);
        // Enemies watch every landing: the hop is set aside for a while rather than stood on.
        if (carries_crystal() && !take_hop(world, pathing, safety, h, &pathing.to_group(g)))
            memory.hop_refused = h, memory.hop_refused_until = world.round + 2 * ability_cooldown;
        else if (!carries_crystal()) step_safely(world, pathing, pathing.to_ally_spawn(), safety);
        return true;
    };
    const auto walk_on = [&](int g) __attribute__((always_inline)) {
        if (g < 0) return false;
        if (map.any_group_hop() && beyond_walk(world, pathing, g)) return cross(g);
        // Descending it walks around walls and live camps; a live route only helps past allies.
        const auto walk = [&](const Field& field, int target) __attribute__((always_inline)) {
            return dash_across(world, pathing, field) || pathing.descend(field, zone, groups[target].centre)
                   || pathing.step_towards(field, zone, groups[target].centre);
        };
        if (const auto* field = pathing.prepare_approach(g, walk_range(world, g), end_reserve)) return walk(*field, g);
        // Too short of fuel to search the way to a new choice: last turn's, whose way is known.
        if (previous >= 0 && previous != g && pathing.approach_ready(previous, walk_range(world, previous))) {
            note_shortcut("farm-kept-target");
            memory.farm_group = memory.claim = previous;
            memory.crew = false;
            return walk(*pathing.approach(previous, walk_range(world, previous)), previous);
        }
        if (const auto* centre = pathing.from_centre(g)) return pathing.descend(*centre, zone, groups[g].centre);
        note_shortcut("crow-flies-farm");
        return pathing.step_closer(groups[g].centre, zone, groups[g].centre);
    };
    // The walk comes before choosing better: fuel for its search is kept back from the evaluation.
    const auto walk_reserve = [&](int g) __attribute__((always_inline)) { return g < 0 ? std::uint64_t{0} : pathing.approach_cost(g, walk_range(world, g)); };
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
        if (g >= 256 || !(ally_claims[g >> 6] >> (g & 63) & 1)) return false;
        for (const auto& a : world.allies) {
            if (a.is_self || !a.alive || !a.visible || comms::claim_of(world, a.index) != g || !test(groups[g].threat(), a.pos))
                continue;
            float rounds = 0;
            const float damage = min_camp_damage(world, g, floored_output(a), &rounds, a.retaliation());
            if (a.health - damage < params::recall_health_fraction * a.max_health) return true;
        }
        return false;
    };
    // Joining allies on a group, our part of its gems is our share of the damage still to deal
    // when we arrive, and of the camps' hits.
    struct CrewWork {
        float output = 0, delayed_damage = 0;
    };
    vec2 spawn_lo{map.width, map.height}, spawn_hi{-1, -1};
    for (const auto p : map.ally_spawn_tiles) {
        spawn_lo.x = std::min(spawn_lo.x, p.x), spawn_lo.y = std::min(spawn_lo.y, p.y);
        spawn_hi.x = std::max(spawn_hi.x, p.x), spawn_hi.y = std::max(spawn_hi.y, p.y);
    }
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
        const auto& group = groups[g];
        for (const auto& a : world.allies) {
            if (a.is_self || !a.alive || comms::claim_of(world, a.index) != g) continue;
            const float output = floored_output(a);
            total.output += output;
            const auto arrival = work_arrival(a, g);
            // Age the work round from the observation, never a guessed hidden position or turn order.
            const int delay = arrival.delay(world.round, waiting);
            debug_block({
                if (world.round <= 5 && delay > 0) {
                    const auto p = group.members[arrival.member].pos;
                    std::printf("FCDELAY %d %u group %d handle %u member %d camp %u at %d %d ally %u pos %d %d reach %d distance %d acted %d dash_ready %d direct %d recall_delay %d spawn_distance %d recall_route %d earliest %d waiting %d delay %d work %d old %.3f new %.3f anchor %d visible %d seen_channel %d\n",
                                world.round, my_handle(), g, group.handle, arrival.member, group.members[arrival.member].handle, p.x, p.y,
                                static_cast<unsigned>(a.handle), a.pos.x, a.pos.y, arrival.reach, arrival.distance,
                                static_cast<int>(a.acted), arrival.dash_ready, arrival.direct, arrival.recall_delay, arrival.spawn_distance, arrival.recall_route,
                                arrival.earliest, waiting, delay, working,
                                static_cast<double>(output * static_cast<float>(working)),
                                static_cast<double>(output * static_cast<float>(std::max(0, working - delay))),
                                arrival.anchor_round, static_cast<int>(a.visible), static_cast<int>(a.seen_channel));
                }
            });
            total.delayed_damage += output * static_cast<float>(std::min(working, delay));
        }
        return total;
    };
    // A group too costly for us alone is still ours to call if an ally in reach with no claim of
    // its own can join: valued, like a crew's, by our share of the work.
    float unclaimed_partner_output = 0;
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && dist(here, a.pos) <= params::partner_radius && comms::claim_of(world, a.index) < 0)
            unclaimed_partner_output = std::max(unclaimed_partner_output, floored_output(a));
    const int n_groups = static_cast<int>(groups.size());
    // Static per group once read: its centre field (once warm) and that field's steps to our
    // spawn, its home_ground weight, its centre_to_altar steps, its own tribute and each holder's
    // gold (`tribute` 0 until read, read again when our Tribute or Prospector emblem changes them).
    // Then its reward and the walks
    // to bank it, kept while `context` holds (the gold's worth while `gold_context` also does),
    // and its fastest clear while its belief holds.
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
    static std::array<GroupFacts, 256> few_facts;
    static std::vector<GroupFacts> many_facts;
    if (n_groups > static_cast<int>(few_facts.size()) && static_cast<int>(many_facts.size()) != n_groups) many_facts.assign(n_groups, {});
    GroupFacts* const group_facts = n_groups > static_cast<int>(few_facts.size()) ? many_facts.data() : few_facts.data();
    const bool prospector = world.me().prospector;
    const auto emblems = static_cast<std::uint8_t>(world.me().fast_tribute | prospector << 1);
    struct Context {
        int bag, short_by;
        bool warm, banking;
        std::uint8_t emblems;
        bool operator==(const Context&) const = default;
    };
    static Context last_context{};
    static std::uint32_t context = 0;
    if (const Context now{bag, short_by, pathing.centres_ready(), banks_bag, emblems}; context == 0 || !(now == last_context))
        last_context = now, ++context;
    // Marcella is paid gold for each gem she tributes, with our gold bonus (probe-marcella-gold).
    const float per_gem = world.me().facts().tribute_gold_per_gem();
    const float tribute_gold = per_gem > 0 ? prices(world).per_gold * paid * per_gem : 0.0f;
    static float last_per_gold = 0, last_tribute_gold = 0;
    static std::uint32_t gold_context = 0;
    if (gold_context == 0 || per_gold != last_per_gold || tribute_gold != last_tribute_gold)
        last_per_gold = per_gold, last_tribute_gold = tribute_gold, ++gold_context;
    const auto centre_field = [&](int g) __attribute__((always_inline)) {
        auto& known = group_facts[g];
        if (!known.centre) known.centre = pathing.from_centre(g);
        return known.centre;
    };
    // Health lost to camps comes back only on spawn: a recall and the walk back out.
    const auto heal = [&](int g, float damage) __attribute__((always_inline)) {
        int out = group_facts[g].to_spawn;
        if (out < 0) {
            const auto* field = centre_field(g);
            out = field ? field->at(map.ally_spawn_centre) : dist(map.ally_spawn_centre, groups[g].centre);
            if (field) group_facts[g].to_spawn = out;
        }
        return out == unreachable ? 0.0f : heal_rounds(world, damage, static_cast<float>(out));
    };
    const float spells = world.me().facts().ranged ? spell_output(world.me()) : 0.0f, basic = std::max(1.0f, basic_output(world.me()));
    struct Clearing {
        float strength, reflect, spells, basic;
        int range;
        bool operator==(const Clearing&) const = default;
    };
    static Clearing last_clearing{};
    static std::uint32_t clearing = 0;
    if (const Clearing now{strength, reflect, spells, basic, range}; clearing == 0 || !(now == last_clearing))
        last_clearing = now, ++clearing;
    int help_group = -1, help_steps = unreachable;
    // First readings of each group (clears, fields) can cost several times the estimate: stop with
    // enough left for the walk after it, and read last turn's choice first so that a cut-short loop
    // still weighs it.
    int first = memory.farm_group >= 0 && memory.farm_group < n_groups ? memory.farm_group : -1;
    if (first < 0) {
        int nearest = unreachable;
        for (int g = 0; g < n_groups; ++g) {
            if (groups[g].has_monolith || groups[g].gems + groups[g].gold == 0) continue;
            const int steps = dist(here, groups[g].centre);
            if (steps < nearest) first = g, nearest = steps;
        }
        if (first < 0) first = 0;
        debug_block({ if (world.round <= 100) std::printf("FSEED %d %u group %d near %d groups %d\n",
                         world.round, my_handle(), first, nearest, n_groups); });
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
    // taken() as a mask.
    auto claimed_bits = ally_claims;
    if (memory.claim >= 0 && memory.claim < 256 && !memory.crew)
        claimed_bits[memory.claim >> 6] &= ~(std::uint64_t{1} << (memory.claim & 63));
    const bool centres_ready = pathing.centres_ready();
    // Draft spawn distances use walking walls; dashers must keep the live field's graph.
    static const bool draft_spawn_graph = !world.me().facts().has_dash() || map.crossable.is_empty();
    const CampGroup* const group_data = groups.data();
    const CampBelief* const camp_data = world.camps.data();
    int* const steps_data = centre_steps.data();
    const int bag_tribute = bag > 0 ? tribute_turns(world, bag) : 0;
    int crystal = -1; // read on first need: 2 carried, 1 to buy, 0 neither
    int k = 0;
    for (; k < evaluated && (fuel_ok(ample) || fuel_ok(loop_floor + loop_reserve())); ++k) {
        const int g = (first + k) % n_groups;
        const auto& group = group_data[g];
        const auto& belief = camp_data[g];
        if (group.has_monolith || group.gems + group.gold == 0 || (belief.state == CampState::cleared && ally_holding(g)))
            continue;
        const bool claimed = g < 256 && (claimed_bits[g >> 6] >> (g & 63) & 1);
        // Carrying, compare whole trips: the gems score only after the walk to an altar and the
        // tribute. Empty-handed, only a capture that wins counts that walk, as no later one shares
        // it. Gems past the win are worth nothing.
        const bool wins = group.gems >= short_by;
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
            // The spawn fields home_ground reads are warm once the centres are.
            if (known.home < 0 && centres_ready) known.home = home_ground(map, g);
            float weight = centres_ready ? known.home : 1.0f;
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
        const int walk = known.walk;
        // The trip home is health-dependent, so it stays out of the kept facts.
        float bank = known.walked_bank, cycle_bank = known.walked_cycle;
        if (to_altar) {
            const float back = (wins ? winning_trip : trip_home)->rounds(walk, capture_rounds(world), static_cast<std::uint32_t>(static_cast<float>(known.gold_in) * paid));
            const bool banks = back < static_cast<float>(unreachable);
            bank = banks ? back + static_cast<float>(known.chained_tribute) : 0.0f;
            cycle_bank = banks ? back + static_cast<float>(known.tribute) : 0.0f;
        }
        auto& steps_known = steps_data[g];
        if (steps_known < 0) {
            // Walking is symmetric: a group's warm centre field gives our steps to it before all are.
            if (const auto* centre = centre_field(g)) {
                steps_known = centre->at(here);
            } else if (const auto drafted = draft_spawn_graph ? map.drafted_spawn_steps(here, g) : std::nullopt) {
                steps_known = *drafted;
            } else {
                if (!from_here) {
                    // A walk is never shorter than the Chebyshev distance, and the trip grows with the
                    // walk: a group that cannot beat the best from that close needs no field from here.
                    if (!claimed && best >= 0) {
                        const int near = dist(here, group.centre);
                        const int near_wait = belief.state == CampState::respawning ? std::max(0, belief.respawn_round - round - near) : 0;
                        const bool may_help = !banks_bag && group.strength > 0 && belief.state == CampState::alive && near <= params::help_radius
                                              && near < help_steps;
                        const float near_cycle = std::max(0.0f, static_cast<float>(near + near_wait) - bank_now + bank)
                                                 + static_cast<float>(capture_rounds(world)) + known.fastest;
                        if (!may_help && near_cycle > 0 && (known.gems + known.gold) / near_cycle <= best_value
                            && (!banks_bag || (known.gems + known.gold) / (static_cast<float>(walk + capture_rounds(world)) + cycle_bank + known.fastest) <= from_altar_value))
                            continue;
                    }
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
            if (in_pocket) out = recall_turns(world), from = map.ally_spawn_centre, steps = pathing.to_ally_spawn().at(group.centre);
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
            && steps < help_steps && struggling(g))
            help_group = g, help_steps = steps;
        // A capture's gold that completes an emblem shortens the trip home (HomeTrip::rounds) though worth
        // counts it too: floored, so a chain never costs less than nothing and every filter below agrees.
        const float trip = std::max(0.0f, static_cast<float>(steps + wait) - bank_now + bank);
        const float gems = known.gems, gold = known.gold, fastest = known.fastest;
        // Risky groups matter only while no affordable one is found; skip the costly clearing
        // estimate for groups that cannot beat it even with no clearing. A crew's share can.
        if (!claimed && best >= 0 && (gems + gold) / (trip + static_cast<float>(capture_rounds(world)) + fastest) <= best_value
            && (!banks_bag || (gems + gold) / (static_cast<float>(walk + capture_rounds(world)) + cycle_bank + fastest) <= from_altar_value))
            continue;
        // No known way to an altar (sealed, or a centre walls hide) is no deadline: the gold still counts.
        const auto too_late = [&](float clear_rounds) __attribute__((always_inline)) {
            if (known.to_altar < 0) known.to_altar = pathing.centre_to_altar(g);
            const int last = known.to_altar;
            return last != unreachable
                   && static_cast<float>(steps + wait + capture_rounds(world) + last + tribute_turns(world, bag + group.gems)) + clear_rounds > static_cast<float>(left);
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
            debug_block({
                const float old_left = health - others * static_cast<float>(working);
                if (world.round <= 5 && health_left != old_left)
                    std::printf("FCWINDOW %d %u group %d handle %u centre %d %d steps %d working %d hp %.3f old_left %.3f new_left %.3f\n",
                                world.round, my_handle(), g, group.handle, group.centre.x, group.centre.y, steps, working,
                                static_cast<double>(health), static_cast<double>(old_left), static_cast<double>(health_left));
            });
            if (health <= 0 || health_left <= 0) continue;
            // A capture that wins the game is the team's, not a share: what counts is how soon.
            const float rounds = health_left / (strength + others), part = wins ? 1.0f : strength * rounds / health;
            // No capture rounds: the claimer holds it, and the crew moves on once it is cleared.
            const float value = rate(world, worth * part, trip + rounds);
            // Only a better share counts, and the final pick takes none an affordable group beats.
            if (value <= shared_value || (best >= 0 && value <= best_value) || too_late(rounds)) continue;
            float joint_rounds = 0;
            // Unless we see the camp's health falling, our share is as if the claimer did nothing before
            // we arrive: crediting work the camp does not show grows our share with every step closer,
            // so near the cap each step turned us back.
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
        const float alone_damage = soften * known.damage, alone_rounds = known.rounds, kite = known.kite;
        float partner_output = unclaimed_partner_output;
        if (alone_damage > spare_health && g == farm_group && memory.claim == g && !memory.crew && belief.state == CampState::alive) {
            for (const auto& a : world.allies) {
                if (a.is_self || !a.alive || !a.visible || dist(here, a.pos) > params::partner_radius
                    || comms::claim_of(world, a.index) != g) continue;
                const auto arrival = work_arrival(a, g);
                const int delay = arrival.delay(round);
                const bool together = arrival.anchor_round >= 0 && delay <= steps + wait;
                const float output = floored_output(a);
                if (together) partner_output = std::max(partner_output, output);
                debug_block({
                    if (round <= 5)
                        std::printf("FCPARTNER %d %u group %d ally %u delay %d steps %d wait %d known %d together %d output %.6f unclaimed %.6f partner %.6f\n",
                                    round, my_handle(), g, static_cast<unsigned>(a.handle), delay, steps, wait,
                                    static_cast<int>(arrival.anchor_round >= 0), static_cast<int>(together),
                                    static_cast<double>(output), static_cast<double>(unclaimed_partner_output), static_cast<double>(partner_output));
                });
            }
        }
        // Unless a partner shares the clear, it takes us alone at least the quicker of the two ways.
        if (best >= 0 && (alone_damage <= spare_health || partner_output <= 0 || belief.state != CampState::alive)) {
            const float quickest = kite >= 0 ? std::min(alone_rounds, kite) : alone_rounds;
            if (worth / (trip + quickest + capture_rounds(world)) <= best_value
                && (!banks_bag || worth / (static_cast<float>(walk) + cycle_bank + quickest + capture_rounds(world)) <= from_altar_value))
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
        const float cycle = trip + clear_rounds + capture_rounds(world);
        float value = rate(world, worth, cycle);
        if (damage > spare_health && partner_output > 0 && belief.state == CampState::alive) {
            float joint_rounds = 0;
            const float part = strength / (strength + partner_output);
            if (soften * min_camp_damage(world, g, strength + partner_output, &joint_rounds) * part <= spare_health) {
                damage = 0;
                const float joint_cycle = trip + joint_rounds + capture_rounds(world);
                value = rate(world, worth * part, joint_cycle);
            }
        }
        if (damage > spare_health && !ally_engaged(world, g)) {
            if (value > risky_value) risky = g, risky_value = value, risky_steps = steps;
        } else {
            if (value > best_value) best = g, best_value = value, best_steps = steps, best_spell = spell;
            if (banks_bag && walk != unreachable) {
                const float via_altar = belief.state == CampState::respawning ? std::max(0.0f, static_cast<float>(belief.respawn_round - round - walk) - bank_now) : 0.0f;
                const float from_altar = static_cast<float>(walk) + cycle_bank + via_altar + clear_rounds + capture_rounds(world);
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
        // Cut short before weighing even last turn's choice: walk on towards it.
        if (k == 0 && memory.farm_group >= 0) memory.claim = memory.farm_group, walk_on(memory.farm_group);
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
    debug_block({ if (walked) std::printf("DASH-FOLLOW %d %u group %d\n", world.round, my_handle(), best); });
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

bool try_ward(vec2 p, Memory& memory) {
    throw_if_stale();
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
// Our one ward never expires, so replace it only by a cluster with more tiles in ability range of
// here and of our work (claimed group or waited-at altar), where we will be again.
// Without `grow`, only if every cluster that needs is found already.
bool ward_bushes(const World& world, Memory& memory, bool grow) {
    const auto& map = world.map();
    const vec2 here = my_position();
    const auto floor = small_cost_estimate + end_reserve;
    // Off the map: killed this turn (Ren's retaliation), after world.me() was read alive.
    if (here.x < 0 || here == memory.bushes_watched) return false;
    if (!fuel_ok(floor)) {
        note_shortcut("ward-no-bushes-fuel");
        return false;
    }
    if (!test(map.near_bushes(), here)) return false;
    if (!grow) {
        if (!map.bush_clusters_found(here, ward_range())) return false;
    } else if (!map.find_bush_clusters(here, ward_range(), floor)) {
        note_shortcut("ward-no-bushes-clusters");
        return false;
    }
    // Scratch boards: allocating one costs more than the host operations on it.
    static bitboard candidates{cambc::uninitialized}, inner{cambc::uninitialized}, scratch{cambc::uninitialized},
        best{cambc::uninitialized};
    candidates.clear();
    candidates.draw_chebyshev(here, cambc::constants::ward_placement_radius);
    candidates &= map.bushes;
    if (test(map.bushes, here)) drop(candidates, map.bush_cluster(here).tiles);
    // Found when it was placed; as a candidate it could only tie with itself.
    const BushCluster* warded =
        in_bounds(memory.ward) && test(map.bushes, memory.ward) ? map.found_bush_cluster(memory.ward) : nullptr;
    if (warded) drop(candidates, warded->tiles);
    if (candidates.is_empty()) {
        memory.bushes_watched = here;
        return false;
    }
    drop(candidates, map.enemy_spawn);
    cambc::vision::ward_tiles_into(team::ally, scratch);
    drop(candidates, scratch);
    const vec2 work = memory.claim >= 0        ? map.groups[memory.claim].centre
                      : memory.wait_altar >= 0 ? map.altars[memory.wait_altar].pos
                                               : vec2{-1, -1};
    // An ability reaches farther than any basic attack.
    const auto score = [&](const bitboard& tiles) {
        const int n = static_cast<int>(count_within(tiles, here, ability_range));
        return in_bounds(work) ? n + static_cast<int>(count_within(tiles, work, ability_range)) : n;
    };
    inner.clear();
    inner.draw_chebyshev(here, 1.0f);
    bool found = false;
    int best_tiles = warded ? score(warded->tiles) : 0;
    while (!candidates.is_empty()) {
        const auto& c = map.bush_cluster(first_tile(candidates));
        const int tiles = score(c.tiles);
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

bool place_ward(const World& world, Memory& memory, bool grow) {
    world.throw_if_stale();
    // A stun refuses every ward, and the thrown error costs ~3.9k fuel.
    if (stunned_turn || !world.me().alive || channelling() || cambc::self().ward_cooldown() > 0) return false;
    return ward_bushes(world, memory, grow);
}

// A live group, awake or maybe, whose monsters not read asleep reach p.
bool awake_over(const World& world, int g, vec2 p) {
    const auto& c = world.camps[g];
    const auto& G = world.map().groups[g];
    if (c.state != CampState::alive || c.awake == Awake::asleep || !test(G.threat(), p)) return false;
    // G.threat() also covers dead and harmless members.
    for (std::size_t i = 0; i < G.members.size(); ++i)
        if (c.health[i] > 0 && G.members[i].strength > 0 && !c.member_asleep(i) && dist(p, G.members[i].pos) <= G.members[i].reach) return true;
    return false;
}

// Retreating from an awake camp takes its hits anyway, and the clear is lost. Every awake group in
// reach counts: a nearly cleared harmless one next to an elk that is hitting us is no reason to stay.
bool finishing_camp(const World& world) {
    if (winning_bag(world)) return false;
    const vec2 here = my_position();
    bool any = false;
    float damage = 0, soften = 0, strength = 0, reflect = 0;
    world.each_stirring([&](int g) {
        if (!awake_over(world, g, here)) return;
        if (!any) soften = camp_hit_factor(), strength = floored_output(world.me()), reflect = world.me().retaliation();
        float rounds = 0;
        damage += soften * min_camp_damage(world, g, strength, &rounds, reflect);
        any = true;
    });
    return any && damage < params::finish_camp_health_fraction * my_health();
}

// On a cleared group's tile worth contesting while the enemy holds it or stands on another:
// leaving lets their hold pay. One body stops their count, so a hold's holders are enough: when
// both sides stand on it, nothing pays until a fight, and the rest of us would stand idle forever.
bool contesting(const World& world) {
    const vec2 here = my_position();
    const int g = world.map().group_at(here);
    if (g < 0 || world.map().groups[g].gems == 0 || world.camps[g].state != CampState::cleared || winning_bag(world)) return false;
    const auto& c = world.camps[g];
    if (c.holder == team::enemy && pays_too_late(c)) return false;
    if (contest_manned(world, g, here)) return false;
    return c.holder == team::enemy || enemy_on(world, world.map().groups[g].tiles());
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
// The zone is the union of boxes, one per minimal outmatching subset: the board is drawn only
// when asked for.
struct PackBox {
    int x0, x1, y0, y1;
};
struct PackZone {
    int round = -1;
    int boxes = 0;
    std::array<PackBox, 255> box; // at most one per subset
    bool drawn = false;
    // Our health and bag as this round's first query read them: they can change during the turn
    // (a kill takes a bag).
    int frozen = -1;
    float health = 0, max_health = 0;
    int bag = 0;
};

PackZone& pack_zone_state(const World& world) {
    static PackZone pz;
    if (pz.frozen != world.round) {
        pz.frozen = world.round;
        pz.health = my_health();
        pz.max_health = my_max_health();
        pz.bag = bag_at_stake(world);
    }
    return pz;
}

PackZone& pack_boxes(const World& world) {
    auto& pz = pack_zone_state(world);
    if (pz.round != world.round) {
        pz.round = world.round;
        pz.boxes = 0;
        pz.drawn = false;
        const auto& map = world.map();
        const vec2 here = world.me().pos;
        struct Member {
            vec2 pos;
            float health, damage;
        };
        Unwritten<Member, 8> scratch;
        auto& members = scratch.a;
        const float health = pz.health;
        const bool hurt = health < params::hurt_health_fraction * pz.max_health || pz.bag >= params::brake_bag;
        // A pack in our half has come to fight there; healthy elsewhere, we came to fight.
        const bool home = own_ground(world, here);
        int n = 0;
        for (const auto& e : world.enemies)
            if ((hurt || home) && n < static_cast<int>(members.size()) && e.alive && e.age(world.round) <= 1 && !test(map.near_enemy_spawn, e.pos))
                members[n++] = {e.pos, e.health, output(e)};
        if (n > 0) {
            float our_health = 0, our_damage = 0;
            for (const auto& a : world.allies)
                if (a.alive && (a.is_self || (a.visible && dist(here, a.pos) <= params::pack_ally_radius))) {
                    our_health += a.is_self ? health : a.health;
                    our_damage += output(a);
                }
            const float ours = (home ? params::home_retreat_ratio : params::hurt_retreat_ratio) * our_health * our_damage;
            // Only minimal outmatching subsets: a superset's tiles lie within its subsets'.
            std::array<unsigned, 32> minimal;
            int m = 0;
            const int r = pack_radius;
            // By mask, each built from the mask without its highest member, so that sums add the
            // members in index order, as a loop over them would.
            struct Subset {
                float health, damage;
            };
            static std::array<Subset, (1u << std::tuple_size_v<std::remove_reference_t<decltype(members)>>)> subsets;
            subsets[0] = {0, 0};
            for (unsigned mask = 1; mask < (1u << n); ++mask) {
                // A covered mask's supersets are covered too, so its sums are never read.
                bool covered = false;
                for (int k = 0; k < m && !covered; ++k) covered = (minimal[k] & mask) == minimal[k];
                if (covered) continue;
                const int top = 31 - __builtin_clz(mask);
                const auto& e = members[top];
                const auto& rest = subsets[mask ^ (1u << top)];
                auto& sub = subsets[mask];
                sub = {rest.health + e.health, rest.damage + e.damage};
                if (sub.health * sub.damage <= ours) continue;
                if (m < static_cast<int>(minimal.size())) minimal[m++] = mask;
                // The box within r of every member.
                int x0 = -1 << 20, x1 = 1 << 20, y0 = -1 << 20, y1 = 1 << 20;
                for (unsigned left = mask; left; left &= left - 1) {
                    const vec2 p = members[static_cast<std::size_t>(__builtin_ctz(left))].pos;
                    x0 = std::max(x0, p.x - r), x1 = std::min(x1, p.x + r), y0 = std::max(y0, p.y - r), y1 = std::min(y1, p.y + r);
                }
                if (x0 > x1 || y0 > y1) continue;
                pz.box[pz.boxes++] = {x0, x1, y0, y1};
            }
        }
    }
    return pz;
}

// After a re-read of vision: the next query builds the boxes from what we see now.
void forget_pack_zone(const World& world) { pack_zone_state(world).round = -1; }

// What we see changed mid-turn. Safety's beliefs are fixed for its life, so it starts again.
[[gnu::noinline]] void see_again(World& world, Pathing& pathing, Safety& safety) {
    world.observe();
    pathing.invalidate();
    std::destroy_at(&safety);
    std::construct_at(&safety, world);
    forget_pack_zone(world);
    // Willow's guard follows what we see; hyperion's keeps the tile it was worked out from.
    if (const auto held = pathing.held_guard(); world.me().facts().heals() && (held.guard || held.fn))
        guard_steps(world, pathing, safety);
}

// A stun we cast takes its target's next turn, which Safety's threats and fights count: it starts again.
void see_stuns(World& world, Safety& safety) {
    if (!world.read_stuns()) return;
    std::destroy_at(&safety);
    std::construct_at(&safety, world);
    safety.refresh(); // as after the hits that cast it: a kill is read as gone
}

// Our walk or dash brought an enemy into sight that could strike us, or that we could strike,
// before our next turn.
bool see_revealed(World& world, Pathing& pathing, Safety& safety) {
    // Off the map, Ren's reflection killed us this turn.
    const vec2 here = my_position();
    if (here.x < 0 || !world.revealed(here, Strike::max_reach, pathing.take_bump()) || world.is_stale()) return false;
    debug_block({ std::printf("REVEAL %d %u %c\n", world.round, my_handle(), decision); });
    see_again(world, pathing, safety);
    return true;
}

bool in_pack_zone(const World& world, vec2 p) {
    // Each box lies within pack_radius of every member of its subset.
    bool near = false, recent = false;
    for (const auto& e : world.enemies)
        if (e.alive && e.age(world.round) <= 1)
            recent = true, near |= (static_cast<unsigned>(p.x - e.pos.x + pack_radius) <= 2u * pack_radius)
                                   & (static_cast<unsigned>(p.y - e.pos.y + pack_radius) <= 2u * pack_radius);
    if (!near) {
        if (recent) pack_zone_state(world); // a later query this round reads what we have now
        return false;
    }
    const auto& pz = pack_boxes(world);
    for (int i = 0; i < pz.boxes; ++i)
        if (p.x >= pz.box[i].x0 && p.x <= pz.box[i].x1 && p.y >= pz.box[i].y0 && p.y <= pz.box[i].y1) return true;
    return false;
}

// Adds the tiles of a box inside the map as a few squares: a host square costs about what a
// single tile does, a whole-board operation far more.
void draw_box(bitboard& b, int x0, int x1, int y0, int y1) {
    const int side = std::min(x1 - x0, y1 - y0) / 2 * 2 + 1;
    if (side == 1) {
        for (int y = y0; y <= y1; ++y)
            for (int x = x0; x <= x1; ++x) set_tile(b, {x, y});
        return;
    }
    const int r = side / 2;
    for (int cy = y0 + r;; cy = std::min(cy + side, y1 - r)) {
        for (int cx = x0 + r;; cx = std::min(cx + side, x1 - r)) {
            draw_square(b, {cx, cy}, static_cast<float>(r));
            if (cx == x1 - r) break;
        }
        if (cy == y1 - r) break;
    }
}

const bitboard* pack_zone(const World& world) {
    static bitboard zone;
    auto& pz = pack_boxes(world);
    if (pz.boxes == 0) return nullptr;
    if (!pz.drawn) {
        pz.drawn = true;
        clear_board(zone);
        const int width = world.map().width, height = world.map().height;
        for (int i = 0; i < pz.boxes; ++i) {
            const auto& b = pz.box[i];
            const int x0 = std::max(b.x0, 0), x1 = std::min(b.x1, width - 1), y0 = std::max(b.y0, 0), y1 = std::min(b.y1, height - 1);
            if (x0 <= x1 && y0 <= y1) draw_box(zone, x0, x1, y0, y1);
        }
    }
    return &zone;
}

// pack_zone() holds every tile within r of p, worked out from its boxes.
bool pack_covers(const World& world, vec2 p, int r) {
    const auto& pz = pack_boxes(world);
    if (pz.boxes == 0) return false;
    const int x0 = std::max(0, p.x - r), x1 = std::min(world.map().width - 1, p.x + r);
    const int y0 = std::max(0, p.y - r), y1 = std::min(world.map().height - 1, p.y + r);
    for (int i = 0; i < pz.boxes; ++i)
        if (const auto& b = pz.box[i]; b.x0 <= x0 && x1 <= b.x1 && b.y0 <= y0 && y1 <= b.y1) return true;
    // Row by row, the boxes that hold the row's first tile not yet held.
    for (int y = y0; y <= y1; ++y) {
        int x = x0;
        for (bool grew = true; grew && x <= x1;) {
            grew = false;
            for (int i = 0; i < pz.boxes; ++i)
                if (const auto& b = pz.box[i]; b.y0 <= y && y <= b.y1 && b.x0 <= x && x <= b.x1) x = b.x1 + 1, grew = true;
        }
        if (x <= x1) return false;
    }
    return true;
}

// A capture is worth finishing when it pays before any enemy seen this round or last could walk
// into reach of us.
bool paying_soon(const World& world, Pathing& pathing, Safety& safety) {
    if (!holding_capture(world, pathing)) return false;
    const vec2 here = world.me().pos;
    const auto& c = world.camps[world.map().group_at(here)];
    if (c.held_since < 0) return false;
    const int turns = c.payout_round() - world.round;
    for (const auto& e : world.enemies)
        if (e.alive && e.age(world.round) <= 1
            && (e.visible ? safety.approach(e, here) : dist(here, e.pos) - safety.strike_of(e).reach) < turns)
            return false;
    return true;
}

bool outmatched(const World& world, Pathing& pathing, Safety& safety) {
    return in_pack_zone(world, world.me().pos) && !paying_soon(world, pathing, safety);
}

// Steps of walking, around walls and units, until no awake monster can pick us; at most one more
// than the longest camp reach.
int camp_exit_rounds(const World& world, Pathing& pathing, Safety& safety, vec2 here) {
    static bitboard inner{cambc::uninitialized}, reach{cambc::uninitialized}, fresh{cambc::uninitialized},
        outside{cambc::uninitialized}, scratch{cambc::uninitialized};
    const auto& walls = pathing.blocked();
    const auto& area = safety.camp_area(); // only its tiles need the exact test
    const int longest = world.map().max_camp_reach;
    not_into(area, outside);
    clear_board(inner);
    set_tile(inner, here);
    for (int r = 1; r <= longest; ++r) {
        walls.reachable_tiles_into(here, static_cast<std::uint16_t>(r), reach);
        xor_into(reach, inner, fresh); // first reached in r steps
        if (board_empty(fresh)) break;  // a closed pocket
        and_into(fresh, outside, scratch);
        if (!board_empty(scratch)) return r;
        and_into(fresh, area, scratch);
        for (const vec2 p : Tiles<11 * 11>{scratch}) // within r <= 5, the Monolith's reach
            if (safety.camp_damage(p) <= 0) return r;
        copy_into(reach, inner);
    }
    return longest + 1;
}

// Camps keep hitting while we walk out of their reach: leave while the health still covers that.
// A siege (Memory::siege) keeps its own health limits for its group's hits.
bool camp_trapped(const World& world, Pathing& pathing, Safety& safety, vec2 here, float health, bool sieging) {
    if (sieging) return false;
    const float dps = safety.camp_damage(here);
    if (dps <= 0) return false;
    const auto exit_cost = [&](int rounds) { return dps * (1.5f * static_cast<float>(rounds) + 1.0f); };
    // The exit takes 1 to max_camp_reach + 1 rounds: the bounds settle most cases without the search.
    if (health > exit_cost(world.map().max_camp_reach + 1)) return false;
    if (health <= exit_cost(1)) return true;
    return health <= exit_cost(camp_exit_rounds(world, pathing, safety, here));
}

// An enemy that could kill us before our next turn overrides finishing a camp or a capture.
bool want_home(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    world.throw_if_stale();
    const vec2 here = my_position();
    if (test(world.map().ally_spawn, here)) return false;
    const float health = my_health();
    // A hold keeps us only while last round's loss, repeated to the payout, leaves us alive: camps
    // hit from out of sight and bush attackers stay unseen.
    const auto hold_lasts = [&] {
        if (!holding_capture(world, pathing)) return false;
        const auto& c = world.camps[world.map().group_at(here)];
        const int rounds = c.held_since >= 0 ? std::max(0, c.payout_round() - world.round) : capture_rounds(world);
        return memory.damage * static_cast<float>(rounds + 1) < health;
    };
    const bool low = health < params::recall_health_fraction * my_max_health() && !finishing_camp(world) && !hold_lasts();
    if (low || outmatched(world, pathing, safety) || camp_trapped(world, pathing, safety, here, health, memory.siege)) return true;
    // Willow holds no fight: an enemy likely to hit it, as threatened() weighs them, sends it home,
    // bar on a capture, which pays without one.
    if (world.me().facts().heals() && !holding_capture(world, pathing) && !contesting(world)
        && safety.credible_enemy_may_hit_within(here, 0) && safety.bound(here).threat)
        return true;
    // Out of sight and not lethal, nobody can win a fight here or pursue us.
    const bool lethal = safety.lethal(here);
    if (!lethal && !enemy_seen(world)) return false;
    // Healthy on our own ground, they have no reason to come for us, unless we carry a bag: a kill takes it.
    const bool pursued = !paying_soon(world, pathing, safety)
                         && !(own_ground(world, here) && health >= params::hurt_health_fraction * my_max_health()
                              && bag_at_stake(world) < params::brake_bag);
    const bool linked = partner(world) != nullptr;
    const auto t = safety.stand(here, pursued ? params::pursuit_steps : 0, lethal || linked, lethal, params::pursuit_steps);
    return t.lost || ((lethal || linked) && t.self_falls);
}

// open_for_us as packed row-major bits, read without host calls; null if the export's layout is
// not the one expected.
const std::uint8_t* open_bits(const World& world) {
    static std::array<std::uint8_t, 100 * 100 / 8 + 8> bits;
    static int state = 0; // 1 packed, 2 not
    if (state == 0) {
        state = 2;
        const auto& map = world.map();
        const std::size_t size = bitboard::linear_buffer_size();
        if (size + 8 > bits.size() || map.open_for_us.is_empty()) return nullptr;
        map.open_for_us.export_linear_buffer({bits.data(), size});
        const vec2 probe = first_tile(map.open_for_us);
        const int i = probe.x + probe.y * map.width;
        if (bits[static_cast<std::size_t>(i >> 3)] >> (i & 7) & 1) state = 1;
    }
    return state == 1 ? bits.data() : nullptr;
}

// The tiles a step (or a ready dash) could end on that want_home would leave at once: stopping
// there hands the enemy the first strike. Cassi and Issac also keep off tiles where one would fall.
const bitboard* step_guard(const World& world, Safety& safety, vec2 here, int radius) {
    world.throw_if_stale();
    if (!enemy_seen(world)) return nullptr;
    static bitboard guard{cambc::uninitialized};
    std::array<const ChampionBelief*, 8> foes;
    std::array<const Strike*, 8> strikes;
    Unwritten<vec2, 8> positions;
    auto& at = positions.a;
    int n = 0;
    for (auto left = safety.seen_enemies(); left; left &= left - 1)
        if (const auto& e = world.enemies[static_cast<std::size_t>(std::countr_zero(left))];
            n < static_cast<int>(foes.size()) && in_square(here, e.pos, Strike::max_reach + 2) && safety.strike_of(e).reach >= 0)
            strikes[n] = &safety.strike_of(e), at[n] = e.pos, foes[n++] = &e;
    if (n == 0) return nullptr;
    // Who can hit a tile, and how hard: a tile no worse than ours is as safe as ours. `bound`
    // by distance alone, never below the exact exposure, which only the foes in it can add to;
    // only those `reaching` a step or dash can be in it.
    unsigned reaching = 0;
    for (int k = 0; k < n; ++k)
        if (in_square(here, at[k], strikes[k]->reach + radius)) reaching |= 1u << k;
    // Placing the tiles costs up to tens of thousands: give up as the fights would, counting the
    // costliest placing lately.
    static std::uint64_t costliest = 0;
    if (reaching == 0) {
        costliest -= costliest / 8;
        return nullptr;
    }
    const auto bound = [&](vec2 p, float& damage) {
        unsigned mask = 0;
        damage = 0;
        for (unsigned left = reaching; left; left &= left - 1)
            if (const int k = std::countr_zero(left), d = dist(p, at[k]); d <= strikes[k]->reach) mask |= 1u << k, damage += strikes[k]->damage[d];
        return mask;
    };
    // blow() for the foes whose strike reaches p.
    std::array<const Reach*, 8> reaches{};
    const auto exposure = [&](vec2 p, float& damage, unsigned near) {
        unsigned mask = 0;
        damage = 0;
        for (; near; near &= near - 1) {
            const int k = std::countr_zero(near);
            if (!reaches[k]) reaches[k] = &safety.reach_of(*foes[k]);
            if (const auto b = reaches[k]->at(p); b.hits) mask |= 1u << k, damage += b.damage;
        }
        return mask;
    };
    const auto floor = safety.fight_cost_estimate() + act_reserve;
    if (!fuel_ok(floor + costliest)) {
        note_shortcut("step-guard");
        return nullptr;
    }
    const auto placing = fuel();
    float here_damage = 0;
    const unsigned here_mask = exposure(here, here_damage, bound(here, here_damage));
    const bool linked = partner(world) != nullptr;
    const auto& open = world.map().open_for_us;
    const auto* open_packed = open_bits(world);
    const int width = world.map().width;
    const auto no_worse = [&](unsigned mask, float damage) { return mask == 0 || ((mask & ~here_mask) == 0 && damage <= here_damage); };
    // Every visible threat that could hit q is a foe, as q is within 2 of us.
    const auto visible_of = [&](unsigned mask) {
        std::uint32_t visible = 0;
        for (; mask; mask &= mask - 1) visible |= 1u << (16 + foes[std::countr_zero(mask)]->index);
        return visible;
    };
    const auto note_placing = [&] {
        if (const auto now = fuel(); now <= placing) costliest = std::max(placing - now, costliest - costliest / 8);
    };
    // The tiles more exposed than ours by `bound`, and who would fight on each by it.
    Unwritten<std::pair<vec2, std::uint32_t>, 24> tiles;
    auto& exposed = tiles.a;
    std::array<unsigned, 24> nears;
    int m = 0;
    std::uint32_t enemies = 0, allies = ~0u;
    for (int dy = -radius; dy <= radius; ++dy)
        for (int dx = -radius; dx <= radius; ++dx) {
            const vec2 q{here.x + dx, here.y + dy};
            if ((dx == 0 && dy == 0) || !in_bounds(q)) continue;
            if (const int i = q.x + q.y * width; open_packed ? !(open_packed[i >> 3] >> (i & 7) & 1) : !test(open, q)) continue;
            float damage = 0;
            const unsigned near = bound(q, damage);
            if (no_worse(near, damage)) continue;
            const auto key = n < static_cast<int>(foes.size()) ? safety.fight_key_with(q, visible_of(near)) : safety.fight_key(q);
            if (key == Safety::no_fight) continue;
            nears[m] = near;
            exposed[m++] = {q, key};
            enemies |= key & 0xFFFF0000u;
            allies &= key & 0xFFFFu;
        }
    if (m == 0) {
        note_placing();
        return nullptr;
    }
    // A fight only gets worse with more enemies or fewer allies: one we win settles those it
    // covers, one we lose those that cover it, and one not lost the `lost` of those it covers.
    const auto covers = [](std::uint32_t worse, std::uint32_t key) {
        return (key & ~worse & 0xFFFF0000u) == 0 && (worse & ~key & 0xFFFFu) == 0;
    };
    struct Settled {
        std::uint32_t key;
        bool won, lost; // won: neither lost nor do we fall
    };
    std::array<Settled, 26> settled;
    int s = 0;
    // 0 won, 1 lost, 2 not lost (self_falls unknown), -1 unsettled.
    const auto settle = [&](std::uint32_t key) {
        int not_lost = -1;
        for (int i = 0; i < s; ++i) {
            if (settled[i].won && covers(settled[i].key, key)) return 0;
            if (settled[i].lost && covers(key, settled[i].key)) return 1;
            if (!settled[i].lost && covers(settled[i].key, key)) not_lost = 2;
        }
        return not_lost;
    };
    // False if fuel ran short.
    const auto fight = [&](std::uint32_t key, bool& lost, bool& falls) {
        const auto* known = safety.known_fight_of(key);
        if (!known && !fuel_ok(safety.fight_cost_estimate() + act_reserve)) {
            note_shortcut("step-guard");
            return false;
        }
        if (known) {
            lost = known->lost;
            falls = known->self_falls;
        } else {
            const auto t = safety.new_fight(key);
            lost = t.lost;
            falls = t.self_falls;
        }
        if (s < static_cast<int>(settled.size())) settled[s++] = {key, !lost && !falls, lost};
        return true;
    };
    const auto outcome = [&](std::uint32_t key, bool& lost, bool& falls) {
        if (const int k = settle(key); k == 0 || k == 1) return lost = falls = k == 1, true;
        return fight(key, lost, falls);
    };
    bool lost = false, falls = false;
    // Every enemy that could hit any of them against the allies at all of them first: if we win
    // even that, no tile needs guarding. Each bound holds its tile's exact exposure, so a win
    // settles the exact tiles before Reach is asked.
    if (m > 1) {
        if (!outcome(enemies | allies, lost, falls)) return nullptr;
        if (!lost && !falls) {
            note_placing();
            return nullptr;
        }
    }
    const int bounded = m;
    m = 0;
    enemies = 0, allies = ~0u;
    for (int i = 0; i < bounded; ++i) {
        // An exact look can query Reach on a new tile, ~1000 a foe.
        if (!fuel_ok(floor + 1000 * static_cast<std::uint64_t>(n))) {
            note_shortcut("step-guard");
            return nullptr;
        }
        const auto [q, bound_key] = exposed[i];
        float damage = 0;
        const unsigned mask = exposure(q, damage, nears[i]);
        if (no_worse(mask, damage)) continue;
        const auto key = n < static_cast<int>(foes.size()) ? (bound_key & ~visible_of(nears[i])) | visible_of(mask) : bound_key;
        exposed[m++] = {q, key};
        enemies |= key & 0xFFFF0000u;
        allies &= key & 0xFFFFu;
    }
    note_placing();
    if (m == 0) return nullptr;
    if (m > 1 && (!outcome(enemies | allies, lost, falls) || (!lost && !falls))) return nullptr;
    // Then the fewest enemies first, so that lost fights settle the larger ones.
    std::sort(exposed.begin(), exposed.begin() + m, [](const auto& a, const auto& b) {
        return std::popcount(a.second >> 16) < std::popcount(b.second >> 16);
    });
    bool any = false;
    for (int i = 0; i < m; ++i) {
        const auto [q, key] = exposed[i];
        const int k = settle(key);
        // Not lost settles q unless a fall there counts.
        if (k == 2 && !linked && !safety.lethal(q)) continue;
        if (k == 0 || k == 1) lost = falls = k == 1;
        else if (!fight(key, lost, falls)) return any ? &guard : nullptr;
        if (lost || (falls && (linked || safety.lethal(q)))) {
            if (!any) clear_board(guard);
            set_tile(guard, q);
            any = true;
        }
    }
    return any ? &guard : nullptr;
}

// step_guard from where we stand, worked out when a step or dash first needs it.
void guard_steps(const World& world, Pathing& pathing, Safety& safety) {
    // Willow holds no fight: every tile want_home would leave is guarded. With no enemy in reach of
    // a step, an empty board, not null: see_again works out a held guard again.
    if (world.me().facts().heals()) {
        pathing.defer_guard(
            [](const World& w, Safety& s, vec2 here, int) {
                static const bitboard none;
                return s.credible_enemy_may_hit_within(here, 1) ? &stations(w, s, here).guard : &none;
            },
            safety, my_position(), 1);
        return;
    }
    const auto& self = world.me();
    int radius = 1;
    for (int s = 0; s < 2; ++s)
        if (self.facts().abilities[s].kind == AbilityKind::dash && self.ability_ready(s, world.round) && my_can_cast()) radius = dash_range;
    pathing.defer_guard(step_guard, safety, my_position(), radius);
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

// Our steps from `here` to stop a carrier's bag from scoring, unreachable if it scores first. A
// tribute under way: a stun or a lock on its altar cancels it (a lock even Marcella's), a kill
// takes the bag. Walking, it outpaces nobody but stops at an altar, the nearest as the crow
// flies: we must reach that altar before its tribute there lands.
int intercept_steps(const World& world, const ChampionBelief& e, vec2 here) {
    const auto& self = world.me();
    const auto& altars = world.map().altars;
    const int range = self.facts().attack_range();
    int steps = std::max(0, dist(here, e.pos) - range);
    vec2 from = e.pos;
    int delay = 0;
    if (e.channel == Channel::tribute || e.teleport_pending()) {
        // It completes at its turn start in its end round: the last round we act before that.
        const int end = e.channel_end_round;
        const bool first = end == world.round ? !e.acted : world.slot(self, end) < world.slot(e, end);
        const int last = first ? end : end - 1;
        int stop = steps;
        if (e.facts().passive != Passive::stun_immune)
            if (const int reach = self.ready_stun_reach(last); reach >= 0)
                stop = std::min(stop, std::max(0, dist(here, e.pos) - reach));
        if (e.channel == Channel::tribute) {
            if (const int a = tribute_altar(world, e.pos); a >= 0 && carried_locks() > 0)
                stop = std::min(stop, std::max(0, dist(here, altars[a].pos) - altar_lock_range));
            return stop <= last - world.round ? stop : unreachable;
        }
        // A teleport not stopped in time lands, and it walks on from there.
        if (stop <= last - world.round) return stop;
        if (in_bounds(e.tp_dest)) from = e.tp_dest, steps = std::max(0, dist(here, from) - range);
        delay = std::max(0, end - world.round);
    }
    int a = -1;
    for (int k = 0; k < static_cast<int>(altars.size()); ++k)
        if (a < 0 || dist(from, altars[k].pos) < dist(from, altars[a].pos)) a = k;
    if (a < 0) return unreachable;
    const int theirs = delay + std::max(0, dist(from, altars[a].pos) - cambc::constants::submit_gems_range) + tribute_turns(pair_gems(world, e), e.fast_tribute);
    return std::max(0, dist(here, altars[a].pos) - cambc::constants::submit_gems_range - range) < theirs ? steps : unreachable;
}

// The visible enemy whose kill pays most a turn to reach and kill it, among those whose local
// fight we win even when they strike first; never one on or next to its spawn, where it heals.
const ChampionBelief* prey(const World& world, Safety& safety) {
    world.throw_if_stale();
    // Willow holds no fight (want_home): a chase walks it into reach only to leave next turn.
    if (!enemy_seen(world) || world.me().facts().heals()) return nullptr;
    const vec2 here = my_position();
    const int range = world.me().facts().attack_range();
    std::optional<float> strength; // read once a candidate needs it
    const auto& near_enemy_spawn = world.map().near_enemy_spawn;
    // Cassi or Issac falling takes the other body and both bags: a won fight that costs us is lost.
    const bool linked = partner(world) != nullptr;
    // Best first (ties in index order), so fights are simulated only up to the first won.
    Unwritten<std::pair<float, const ChampionBelief*>, 8> candidates;
    auto& order = candidates.a;
    int n = 0;
    for (auto left = safety.seen_enemies(); left; left &= left - 1) {
        const auto& e = world.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (n == static_cast<int>(order.size()) || dist(here, e.pos) > vision_radius || test(near_enemy_spawn, e.pos)) continue;
        // A teleport under way cannot fight back, but leaves unless we reach it before it lands.
        if (e.teleport_pending()) {
            const int end = e.channel_end_round;
            const bool first = end == world.round ? !e.acted : world.slot(world.me(), end) < world.slot(e, end);
            if (std::max(0, dist(here, e.pos) - range) > (first ? end : end - 1) - world.round) continue;
        }
        // Out of reach on its own ground only when hurt or carrying a bag we can stop: fights at
        // central altars straddle the line, and a beaten enemy otherwise escapes a step across it,
        // but a bag has to stop at an altar to score, and a kill takes it. An enemy holding a
        // cleared group is taking its gems: killing it is how a capture is contested.
        const int g = world.map().group_at(e.pos);
        const int held = g >= 0 && world.camps[g].state == CampState::cleared ? world.map().groups[g].gems : 0;
        if (dist(here, e.pos) > range && !own_ground(world, e.pos) && e.health >= params::hurt_health_fraction * e.max_health && held == 0
            && (pair_gems(world, e) == 0 || intercept_steps(world, e, here) == unreachable))
            continue;
        // Every tile in reach of it would make us retreat at once.
        if (pack_covers(world, e.pos, range)) continue;
        if (!strength) strength = std::max(1.0f, my_strength() * world.me().damage_scale());
        const float turns = static_cast<float>(std::max(0, dist(here, e.pos) - range)) + e.health / *strength;
        // Turns per gem a kill is worth: the life (abilities' life_value, in gems) and the bag.
        const float cost = turns / (params::life_value / params::gem_value + static_cast<float>(pair_gems(world, e) + held));
        int i = n++;
        for (; i > 0 && order[i - 1].first > cost; --i) order[i] = order[i - 1];
        order[i] = {cost, &e};
    }
    if (n == 0) return nullptr;
    const auto live = my_record();
    const auto state = cambc::champion_state::from_bits_retain(live.state);
    const bool can_move = state.contains(cambc::champion_state::can_move);
    const bool can_cast = state.contains(cambc::champion_state::can_cast);
    // prey also tests whether to cancel a recall/tribute; that restriction is not a spent cast.
    const bool cancelable = state.contains(cambc::champion_state::recalling) || state.contains(cambc::champion_state::submitting_gems);
    const bool channel = cancelable || state.contains(cambc::champion_state::teleporting);
    const bool cast_available = can_cast || cancelable;
    std::array<int, 2> cooldowns;
    for (int s = 0; s < 2; ++s) {
        std::int32_t remaining{};
        ok(cambc::detail::sdk_champion_cooldown(my_handle(), static_cast<std::uint32_t>(s), &remaining));
        cooldowns[s] = std::max(0, static_cast<int>(remaining));
    }
    world.throw_if_stale();
    bool walk_cast = false;
    const auto& self = world.me();
    for (int s = 0; s < 2; ++s) {
        const auto& a = self.facts().abilities[s];
        if (!can_cast || cooldowns[s] > 0) continue;
        walk_cast |= a.kind == AbilityKind::attack_reset || a.kind == AbilityKind::dash
            || (!a.excludes_walking && (a.stuns || ((a.hits_enemies() || a.kind == AbilityKind::heal || a.kind == AbilityKind::shield)
                && a.multiplier > 0 && live.focus > 0)));
    }
    // Chasing is optional: leave enough for the walk after it and the turn's end.
    const auto reserve = search_cost_estimate(2 * vision_radius) + end_reserve;
    // The fights already lost: chase_trade reads only these and the turn's state, not the target.
    Unwritten<std::pair<std::uint64_t, std::uint32_t>, 8> lost_fights;
    auto& lost = lost_fights.a;
    int n_lost = 0;
    for (int i = 0; i < n; ++i) {
        if (!fuel_ok(safety.fight_cost_estimate() + reserve)) {
            note_shortcut("prey-cut-short");
            break;
        }
        const auto& target = *order[i].second;
        const auto key = safety.fight_key(target.pos);
        std::uint32_t delayed = 0;
        if (key != Safety::no_fight)
            for (auto left = key & 0xFFFFu; left; left &= left - 1) {
                const int j = std::countr_zero(left);
                const auto& a = world.allies[static_cast<std::size_t>(j)];
                if (a.is_self) {
                    // Intent only: blocked routes are pessimistic; post-cancel walking stays baseline.
                    if (!channel && self.facts().ranged && can_move && dist(here, target.pos) > range && !walk_cast) delayed |= 1u << j;
                    continue;
                }
                if (!a.alive || !a.visible) continue;
                const int next = next_turn_round(world, a);
                if (strike(a, next).hits(dist(a.pos, target.pos))) continue;
                bool support = false;
                for (int s = 0; s < 2; ++s) {
                    const auto& ability = a.facts().abilities[s];
                    support |= a.ability_ready(s, next) && a.focus > 0 && ability.multiplier > 0
                        && (ability.kind == AbilityKind::heal || ability.kind == AbilityKind::shield);
                }
                if (!support) delayed |= 1u << j;
            }
        // Enemies who walk to the target in time join the fight.
        const auto late = key == Safety::no_fight ? 0u : safety.late(target.pos, key);
        const std::pair<std::uint64_t, std::uint32_t> fight{std::uint64_t{key} << 32 | delayed, late};
        if (std::find(lost.begin(), lost.begin() + n_lost, fight) != lost.begin() + n_lost) continue;
        const auto t = safety.chase_trade(key, delayed, cooldowns, cast_available, linked, late);
        debug_block({
            static int traced = 0;
            if (delayed && traced < 64) {
                ++traced;
                std::printf("CHASE-AVAIL %d %u %u %u %u %d %d %d\n", world.round, my_handle(),
                            static_cast<std::uint32_t>(target.handle), key, delayed, static_cast<int>(t.lost), t.turns_to_kill_us, t.turns_to_kill_them);
            }
        });
        if (!t.lost && !(linked && t.self_falls)) return &target;
        lost[n_lost++] = fight;
    }
    return nullptr;
}

bool chase(const World& world, Pathing& pathing, Safety& safety) {
    const auto* target = prey(world, safety);
    if (!target) return false;
    decision = 'C';
    if constexpr (debug_fights) log_fight("FC", world, safety, target->pos, safety.fight(target->pos), static_cast<int>(target->handle));
    const int range = world.me().facts().attack_range();
    // A walk alone cannot reach range this turn; a melee walk can follow the dash.
    if (dist(my_position(), target->pos) > range + 1 && my_can_move()) dash_to_attack(world, pathing, target);
    bool stuck = false;
    if (dist(my_position(), target->pos) > range && my_can_move()) {
        const auto* zone = pack_zone(world);
        static bitboard goals{cambc::uninitialized};
        clear_board(goals);
        draw_square(goals, target->pos, static_cast<float>(range));
        and_into(goals, world.map().open_for_us, goals);
        if (zone) drop(goals, *zone);
        stuck = !pathing.step_towards(goals, zone, 2 * vision_radius) && dist(my_position(), target->pos) > range;
    }
    bool hit = attack_enemy(world);
    hit |= reset_and_attack_enemy(world); // after an attack, or a ranged walk
    hit |= cast_at_enemies(world);
    // No step and no hit: the target is out of our walk's reach (across live camps), so the turn goes on.
    return hit || !stuck;
}

bool can_tribute_safely(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    if (retaining_gems(world, pathing)) return false;
    if (!can_tribute_here(world)) return false;
    return tribute_ok(world, safety, memory, tribute_turns(world, my_gems()));
}

// Only a small bag, out of every credible enemy's reach, and never the gems that would win.
// Cassi's and Issac's bags fall together. A credible enemy elsewhere on the map is no reason to
// walk a small bag home: on the ladder that started 44% of our bank trips.
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

// Recall from a capture we hold (holding_capture), timed to land home the turn it pays: the gems
// skip the walk when an altar is nearer by way of home, and the stop heals and shops.
bool capture_recall(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    const vec2 here = my_position();
    if (safety.threatened(here)) return false;
    const int g = world.map().group_at(here);
    const auto& c = world.camps[g];
    if (c.holder != team::ally || c.held_since < 0) return false;
    const int payout = c.payout_round();
    const int channel = my_channel_time();
    if (world.round + channel < payout) return false;
    const auto& G = world.map().groups[g];
    const bool wins = capture_share(world, g) >= gems_short(world);
    const auto* prism = prism_capture_holder(world, G);
    if (!wins && (retaining_gems(world, pathing) || (prism && prism->is_self))) {
        if (world.me().facts().passive != Passive::gem_focus || !may_shop(world) || winning_bag(world)
            || closing(world, pathing) || !recall_outruns(world, safety) || enemy_on(world, G.tiles()))
            return false;
        const int back = pathing.to_ally_spawn().at(here);
        if (back == unreachable || c.state != CampState::cleared || payout < world.round) return false;
        bool seen = true;
        for (const auto& m : G.members) seen &= test(world.visible, m.pos);
        unsigned gold_in = 0;
        if (seen) gold_in = static_cast<unsigned>(static_cast<float>(gold_share(world, G)) * gold_paid(world));
        const float value = affordable_prefix(world, gold_in).gain
                            + heal_rounds(world, my_max_health() - my_health(), spawn_steps());
        const int hurt = my_health() < my_max_health() ? 1 : 0;
        return std::isfinite(value) && value > static_cast<float>(std::max(0, channel - (payout - world.round)) + hurt + back);
    }
    const int walk = pathing.to_any_altar().at(here);
    if (walk == unreachable) return false;
    const auto gold_in = static_cast<std::uint32_t>(static_cast<float>(gold_share(world, G)) * gold_paid(world));
    if (!(home_trip(world, pathing, channel, wins).rounds(walk, payout - world.round, gold_in) < static_cast<float>(walk)))
        return false;
    // The ride banks the share: a payout earlier than we guessed (hold_start) finds us off the hold,
    // where recall_to_bank keeps it only for a bag already banking.
    memory.banking = true;
    return true;
}

// With an empty bag, the gold to complete the next emblem goes home to shop, riding a recall unless walking is
// quicker.
[[gnu::flatten]] bool wants_shop(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    if ((bankable_bag(world, pathing) > 0 && !retaining_gems(world, pathing)) || memory.damage > 0 || !may_shop(world)) return false;
    const auto gold = my_gold();
    const bool prism = world.me().facts().passive == Passive::gem_focus;
    if (gold < shard_price || (!prism && gold < emblem_price && !emblem_begun(world))) return false;
    const vec2 here = my_position();
    if (test(world.map().ally_spawn, here) || safety.threatened(here)) return false;
    // The trip costs the recall and the walk back out; arriving by recall, the heal takes the turn.
    if (prism) {
        if (winning_bag(world) || closing(world, pathing)) return false;
        const int back = pathing.to_ally_spawn().at(here);
        if (back == unreachable) return false;
        const int hurt = my_health() < my_max_health() ? 1 : 0;
        const float value = affordable_prefix(world).gain + heal_rounds(world, my_max_health() - my_health(), spawn_steps());
        if (!std::isfinite(value) || !(value > static_cast<float>(std::min(back, recall_turns(world) + hurt) + back))) return false;
    } else {
        const auto stop = home_trip(world, pathing, recall_turns(world), winning_bag(world));
        if (stop.short_gold > 0) return false;
        const int back = pathing.to_ally_spawn().at(here);
        if (back != unreachable && stop.heal + affordable_prefix(world).gain < static_cast<float>(std::min(back, stop.channel + stop.hurt) + back)) return false;
    }
    bool awake = false;
    world.each_stirring([&](int g) { awake = awake || awake_over(world, g, here); });
    return !awake;
}

// A champion's turn start in `round`, where its channel completes.
Moment turn_start(const World& world, const ChampionBelief& c, int round) { return {round, world.slot(c, round) - 1}; }

// The earliest our winning bag's win lands: our tribute's end, or, none under way, a walk to the
// nearest altar as the crow flies and a whole channel; and no sooner than the allies' tributes in
// sight that gems_short counts.
Moment win_lands(const World& world) {
    Moment m{world.round, -1};
    if (const int bag = static_cast<int>(my_gems()); bag > 0) {
        const vec2 here = my_position();
        int r = world.round;
        if (my_state().contains(cambc::champion_state::submitting_gems)) {
            r += my_channel_time();
        } else {
            int walk = unreachable;
            for (const auto& a : world.map().altars) walk = std::min(walk, std::max(0, dist(here, a.pos) - cambc::constants::submit_gems_range));
            r += walk + tribute_turns(world, bag);
        }
        m = turn_start(world, world.me(), r);
    }
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && a.channel == Channel::tribute)
            m = std::max(m, turn_start(world, a, a.channel_end_round));
    return m;
}

// A visible enemy whose tribute wins them the game, in reach of a ready stun of ours, and lands
// before our bag's win if ours wins; null if none.
const ChampionBelief* stoppable_winning_tribute(const World& world) {
    if (!enemy_seen(world)) return nullptr;
    const auto& self = world.me();
    std::optional<Moment> win;
    for (const auto& e : world.enemies)
        if (enemy_tribute_wins(world, e) && e.facts().passive != Passive::stun_immune
            && dist(self.pos, e.pos) <= self.ready_stun_reach(world.round)) {
            if (!winning_bag(world)) return &e;
            if (!win) win = win_lands(world);
            if (turn_start(world, e, e.channel_end_round) < *win) return &e;
        }
    return nullptr;
}

// A visible ally out of channels, acting before an enemy's tribute lands, can stop it alone (its
// game_ender sees the race as we do): a ready stun in reach, or a carried lock within 2 of the
// altar, unless that altar is ours too (its place_lock spares our winning tribute). An enemy in a
// bush is seen only from its cluster: not counted.
bool ally_stops(const World& world, const ChampionBelief& e) {
    if (test(world.map().bushes, e.pos)) return false;
    const Moment lands = turn_start(world, e, e.channel_end_round);
    const int altar = tribute_altar(world, e.pos);
    const bool lockable = altar >= 0 && tribute_altar(world, my_position()) != altar;
    const bool stunnable = e.facts().passive != Passive::stun_immune;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible || a.channel != Channel::none) continue;
        const int r = a.acted ? world.round + 1 : world.round;
        if (!a.can_act(r) || !(turn_start(world, a, r) < lands) || stun_pending(a.handle)) continue;
        if (stunnable && dist(a.pos, e.pos) <= a.ready_stun_reach(r)) return true;
        if (lockable && dist(a.pos, world.map().altars[altar].pos) <= altar_lock_range) {
            std::array<std::uint32_t, 4> counts{};
            const auto lock = cambc::detail::raw_consumable_ids[static_cast<std::size_t>(cambc::consumable_type::altar_lock)];
            if (cambc::detail::sdk_champion_consumables(static_cast<std::uint32_t>(a.handle), counts.data()) == 0 && counts[lock] > 0)
                return true;
        }
    }
    return false;
}

// A visible enemy whose bag (both, for a walking Cassi and Issac) ends the game once tributed and that we
// can stop: nothing we gain meanwhile counts unless our own bag wins first. The nearest; null if none.
const ChampionBelief* game_ender(const World& world) {
    const int need = static_cast<int>(cambc::constants::winning_gems) - world.score.enemy;
    if (!enemy_seen(world)) return nullptr;
    // No pair carries more than every living enemy's bag together.
    int carried = 0;
    for (const auto& e : world.enemies) carried += e.alive ? e.gems : 0;
    if (carried < need) return nullptr;
    std::optional<vec2> here; // and when our bag's win lands if it wins, once one qualifies
    std::optional<Moment> win;
    const ChampionBelief* best = nullptr;
    int best_steps = unreachable;
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible) continue;
        const bool tributing = e.channel == Channel::tribute;
        // A tribute scores only the tributing body's bag; one by its spawn can still be stunned or locked.
        if ((tributing ? e.gems : pair_gems(world, e)) < need || (!tributing && test(world.map().near_enemy_spawn, e.pos))) continue;
        if (!here) {
            here = my_position();
            if (winning_bag(world)) win = win_lands(world);
        }
        // Our winning bag outruns a walking carrier; a tribute under way only if it lands first.
        if (win && !(tributing && turn_start(world, e, e.channel_end_round) < *win)) continue;
        if (const int steps = intercept_steps(world, e, *here); steps < best_steps) best = &e, best_steps = steps;
    }
    return best;
}

// Into reach of the enemy whose bag ends the game, whatever the risk: a stun or a lock if it is
// tributing, else attacks, followed until it stops at an altar.
void stop_game_ender(const World& world, Pathing& pathing, Memory& memory, const ChampionBelief& e) {
    auto& me = cambc::self();
    decision = 'E';
    memory.claim = -1;
    pathing.set_guard(nullptr);
    const bool tributing = e.channel == Channel::tribute;
    const auto act = [&] {
        place_lock(world);
        cast_at_enemies(world, !tributing && dist(me.position(), e.pos) > world.me().facts().attack_range() ? escape_step_value : 0.0f);
        if (attack_enemy(world)) reset_and_attack_enemy(world);
    };
    act();
    if (!me.can_move()) return;
    const int range = world.me().facts().attack_range();
    static bitboard goals{cambc::uninitialized};
    goals.clear();
    int reach = range;
    if (tributing && e.facts().passive != Passive::stun_immune) reach = std::max(reach, world.me().ready_stun_reach(world.round + 1));
    goals.draw_chebyshev(e.pos, static_cast<float>(reach));
    if (const int a = tributing ? tribute_altar(world, e.pos) : -1; a >= 0 && carried_locks() > 0) goals |= world.map().altars[a].lock_tiles();
    goals &= world.map().open_for_us;
    if (test(goals, me.position())) return;
    if (dist(me.position(), e.pos) > range + 1) dash_to_attack(world, pathing, &e);
    if (!test(goals, me.position())) pathing.step_towards_funded(goals, end_reserve);
    act();
}
// Rounds before an enemy hold pays: a body of ours on a camp tile by then stops it.
int enemy_hold_left(const World& world, const CampBelief& c) {
    return c.holder == team::enemy && c.held_since >= 0 ? c.payout_round() - world.round : capture_rounds(false);
}

// An ally that will not come to group g: tributing, on a recall kept through a turn, or working
// towards another group.
bool bound_elsewhere(const World& world, const ChampionBelief& a, int g) {
    if (a.channel == Channel::tribute) return true;
    if (a.channel == Channel::recall && visible_record(a.handle)
        && kept_recall(a.handle, a.recall_turns()))
        return true;
    const int claim = comms::claim_of(world, a.index);
    return claim >= 0 && claim != g;
}

// Allies in sight on group g's tiles, or free for it and nearer its centre than `here` (ties to
// the lower index), already make enough holders.
bool capture_taken(const World& world, int g, vec2 here) {
    const auto& G = world.map().groups[g];
    if (const auto* prism = prism_capture_holder(world, G)) return !prism->is_self;
    int ahead = 0;
    for (const auto& a : world.allies)
        ahead += !a.is_self && a.alive && a.visible
                 && (test(G.tiles(), a.pos)
                     || ((dist(a.pos, G.centre) < dist(here, G.centre)
                          || (dist(a.pos, G.centre) == dist(here, G.centre) && a.index < world.me().index))
                         && !bound_elsewhere(world, a, g)));
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
    occupancy_into(team::ally, units);
    drop(free, units);
    occupancy_into(team::enemy, units);
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
        // A cleared group's health out of sight is as last seen.
        const float hp = c.state == CampState::cleared ? 0 : c.state == CampState::respawning ? G.members[i].max_health : c.health[i];
        if (hp <= 0) continue;
        load.health += hp;
        load.hit += G.members[i].strength;
        if (G.members[i].strength > top) top = G.members[i].strength, load.pos = G.members[i].pos;
    }
    return load;
}

// A visible enemy stands in the group's reach: it, not we, takes the nearest-champion hits.
bool enemy_in_reach(const World& world, int g) {
    const auto& threat = world.map().groups[g].threat();
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && test(threat, e.pos)) return true;
    return false;
}

// The Monolith or sealing group (seals()) to siege; one the enemy holds or that returns too late is
// skipped. `sealing` tells which; `joining`, a live Monolith off Monolith-only maps that the enemy
// is sieging (in its reach, or our team already on it while it is awake); `bursting`, one there
// whose known health the team clears in a burst (params::burst_rounds).
int siege_candidate(const World& world, Pathing& pathing, const Memory& memory, bool& sealing, bool& joining, bool& bursting) {
    const auto& map = world.map();
    static std::vector<int> monoliths; // in group order
    static bool listed = false;
    if (!listed) {
        listed = true;
        for (int g = 0; g < static_cast<int>(map.groups.size()); ++g)
            if (map.groups[g].has_monolith) monoliths.push_back(g);
    }
    int best = -1;
    float best_cost = 0;
    const auto consider = [&](int g, bool seal) {
        const auto& c = world.camps[g];
        // Off Monolith-only maps a live Monolith counts only if it seals or the enemy is sieging it.
        const bool join = !map.monolith_only && !seal && c.state == CampState::alive && c.awake != Awake::asleep
                          && (enemy_in_reach(world, g) || (memory.siege && memory.claim == g) || ally_claims(world, g));
        const bool burst = !map.monolith_only && !seal && !join && c.state == CampState::alive
                           && siege_load(world, g).health <= team_power(world) * static_cast<float>(params::burst_rounds);
        if (!map.monolith_only && !seal && !join && !burst && c.state != CampState::cleared) return;
        const int wait = c.state == CampState::respawning ? c.respawn_round - world.round : 0;
        if (wait > params::siege_respawn_wait) return;
        if (c.state == CampState::cleared && c.holder == team::enemy) return;
        const int steps = map.ally_steps(g);
        if (steps == unreachable) return;
        // The walk there and the wait for its return, with the team's current target kept until
        // another is clearly sooner: switching turns everyone around.
        float cost = static_cast<float>(std::max(steps, wait));
        if (memory.siege && memory.claim == g) cost -= static_cast<float>(params::siege_stickiness);
        if (best < 0 || cost < best_cost) best = g, best_cost = cost, sealing = seal, joining = join, bursting = burst;
    };
    const bool sealed = altars_sealed(world, pathing);
    const auto& access = altar_access(world, pathing);
    for (const int g : monoliths) consider(g, sealed && seals(world, access, g));
    if (sealed) {
        // Other sealing groups: those blocking, and those awake.
        for (const int g : access.blocks)
            if (!map.groups[g].has_monolith) consider(g, true);
        world.each_stirring([&](int g) {
            if (!map.groups[g].has_monolith && seals(world, access, g)
                && std::find(access.blocks.begin(), access.blocks.end(), g) == access.blocks.end())
                consider(g, true);
        });
    }
    return best;
}

// The team's clear, at its current output, costs no more health than it can take in turns.
bool siege_ready(const World& world, const SiegeLoad& load, bool committed, bool sealing, int joined, bool bursting) {
    if (load.health <= 0) return true;
    const float rounds = load.health / team_power(world);
    const float slack = committed ? params::siege_commit_slack : 1.0f;
    const float limit = world.map().monolith_only || sealing || joined >= 0 ? params::siege_rounds
                        : bursting ? params::burst_rounds : 0;
    if (rounds > limit * slack) return false;
    // While the enemy is in its reach, their bodies take the hits.
    if (joined >= 0 && enemy_in_reach(world, joined)) return true;
    float pool = 0;
    for (const auto& a : world.allies)
        if (a.alive) pool += a.max_health;
    return rounds * load.hit * camp_hit_factor() * params::siege_hit_share <= params::siege_pool_share * pool * slack;
}

// Once the team is strong enough it goes together: melee adjacent, ranged at their range, the hurt
// stepping out to 4, where casters still cast.
bool siege(const World& world, Pathing& pathing, Memory& memory) {
    world.throw_if_stale();
    sieged = true;
    const auto& map = world.map();
    bool sealing = false, joining = false, bursting = false;
    const int g = siege_candidate(world, pathing, memory, sealing, joining, bursting);
    const bool ally_in = g >= 0 && ally_claims(world, g);
    const auto load = g >= 0 ? siege_load(world, g) : SiegeLoad{};
    if (g < 0 || !siege_ready(world, load, (memory.siege && memory.claim == g) || ally_in, sealing, joining ? g : -1, bursting)) {
        memory.siege = false;
        memory.staged_since = -1;
        return false;
    }
    const auto& G = map.groups[g];
    const auto& c = world.camps[g];
    const vec2 here = my_position();
    if (c.state == CampState::cleared) {
        // The nearest take the capture, split to shorten the tributes; the rest farm.
        if (capture_taken(world, g, here)) {
            memory.siege = false;
            memory.staged_since = -1;
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
    const auto& f = world.me().facts();
    const int range = f.attack_range();
    const bool fresh = c.state == CampState::respawning;
    const int stage = G.reach + 2; // just out of the group's reach

    // As the staging tiles: within reach of any live member, not only the strongest.
    const auto at_stage = [&](vec2 p) {
        for (std::size_t i = 0; i < G.members.size(); ++i)
            if ((c.health[i] > 0 || fresh) && dist(p, G.members[i].pos) <= stage + 1) return true;
        return false;
    };
    bool engaged = false;
    float staged = floored_output(world.me());
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible) continue;
        if (test(G.threat(), a.pos) && c.awake != Awake::asleep) engaged = true;
        if (at_stage(a.pos)) staged += floored_output(a);
    }
    if (!fresh && test(G.threat(), here) && c.awake != Awake::asleep) engaged = true;
    if (!engaged && !fresh) {
        if (memory.staged_since < 0 && at_stage(here)) memory.staged_since = world.round;
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
        if (G.members[i].strength > 0 && dist(here, G.members[i].pos) <= G.members[i].reach) hit += G.members[i].strength;
        if (range > 1) inner.draw_chebyshev(G.members[i].pos, static_cast<float>(range - 1));
    }
    hit = std::max(hit, load.strongest) * camp_hit_factor();
    // Leave while we can still walk out of reach: a hit a step until out of the group's reach.
    const int role = f.ranged ? range : 1;
    const bool low = my_health() < hit * static_cast<float>(G.reach + 2 - role);

    const bool many = G.members.size() > 1;
    const auto tiles = [&](int r, bitboard& out) __attribute__((always_inline)) {
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
        tiles(stage, goals);
        drop(goals, G.threat());
    } else if (low) {
        // Out of reach, the turn's recall is kept for a heal trip (siege_heal_trip); a caster
        // healthy enough stays at spell range to cast.
        tiles(caster && my_health() >= params::heal_trip_fraction * my_max_health() ? ability_range : stage,
              goals);
        drop(goals, G.threat());
    } else if (f.ranged && caster && !tanked) {
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
        goals.draw_chebyshev(m, static_cast<float>(stage));
        goals &= map.standable;
        drop(goals, G.threat());
    }
    if (!test(goals, here)) {
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

// Enter over two activations; an interior firing turn revalidates only its current activation.
bool kite_productive_action(const World& world, Pathing& pathing, int g, bool interior = false) {
    if (!interior && !my_can_move()) return false;
    const auto& map = world.map();
    const auto& self = world.me();
    const auto& f = self.facts();
    const auto& G = map.groups[g];
    const auto& c = world.camps[g];
    if (c.state != CampState::alive || !map.from_ally_spawn_ready()) return false;
    const int horizon = interior ? 1 : 2;
    int slot = -1;
    for (int s = 0; s < 2; ++s) {
        const auto& a = f.abilities[s];
        // This local ablation does not price ground centres or trade away an AoE in its horizon.
        if (a.kind == AbilityKind::damage && a.target == Targeting::ground && a.multiplier > 0
            && self.ability_ready(s, world.round + horizon - 1)) return false;
        if (a.kind == AbilityKind::attack_reset || (a.kind == AbilityKind::damage && a.target == Targeting::unit && a.multiplier > 0)) {
            if (slot >= 0) return false;
            slot = s;
        }
    }
    const vec2 here = my_position();
    if (interior && pathing.guard() && test(*pathing.guard(), here)) return false;
    int reach = f.attack_range();
    if (slot >= 0 && f.abilities[slot].kind == AbilityKind::damage && self.ability_ready(slot, world.round + horizon - 1))
        reach = std::max(reach, f.abilities[slot].range());
    bool reachable = false;
    for (std::size_t i = 0; i < G.members.size(); ++i)
        reachable |= c.health[i] > 0 && dist(here, G.members[i].pos) <= reach + (interior ? 0 : 1);
    if (!reachable) return false;
    const int home_steps = map.from_ally_spawn().at(here);
    if (home_steps == unreachable) return false;
    std::array<vec2, 9> endpoints;
    endpoints[0] = here;
    int count = 1;
    if (!interior) {
        const auto& blocked = pathing.blocked();
        for (int dy = -1; dy <= 1; ++dy)
            for (int dx = -1; dx <= 1; ++dx) {
                if (dx == 0 && dy == 0) continue;
                const vec2 p{here.x + dx, here.y + dy};
                if (in_bounds(p) && test(map.standable, p) && !test(blocked, p)
                    && (!pathing.guard() || !test(*pathing.guard(), p))) endpoints[count++] = p;
            }
    }
    struct Target { vec2 pos; float health, strength; std::uint16_t visible; };
    static std::vector<Target> targets;
    targets.clear();
    for (std::size_t i = 0; i < G.members.size(); ++i) {
        if (c.health[i] <= 0) continue;
        const auto& m = G.members[i];
        // Only harmful members have a prepared range-5 viewer here. Do not cold-build another.
        if (m.strength <= 0) {
            if (dist(here, m.pos) <= ability_range + 1) return false;
            continue;
        }
        const auto& viewers = pathing.member_attack_tiles(g, static_cast<int>(i), ability_range + 1);
        std::uint16_t visible = 0;
        for (int k = 0; k < count; ++k)
            if (test(viewers, endpoints[k])) visible |= std::uint16_t{1} << k;
        targets.push_back({m.pos, c.health[i], m.strength, visible});
    }
    if (targets.empty()) return false;
    const bool can_attack = my_can_attack(), can_cast = my_can_cast();
    const float dealt = self.damage_scale() * camp_dealt_factor();
    const float strength = my_strength(), basic_damage = strength * dealt;
    const float spell_damage = slot < 0 ? 0 : f.abilities[slot].multiplier * my_record().focus * dealt;
    const float soften = camp_hit_factor();
    const float spare = my_health() - params::recall_health_fraction * my_max_health();
    const float lost_output = floored_output(self);
    world.throw_if_stale();
    static std::vector<float> remaining;
    remaining.resize(targets.size());
    const auto damage = [&](int k) {
        const vec2 p = endpoints[k];
        const bool moved = k != 0;
        const bool held = engagement_near(world, p, f.cast_reach());
        const bool reset_held = engagement_near(world, p, f.basic_reach() + (f.ranged ? 0 : 1));
        float best = 0;
        // No cast, cast now, or cast next activation: a slot cannot recur within this horizon.
        for (int use = 0; use <= horizon; ++use) {
            for (std::size_t i = 0; i < targets.size(); ++i) remaining[i] = targets[i].health;
            float total = 0;
            const auto basic = [&] {
                int at = -1;
                float score = -1;
                for (std::size_t i = 0; i < targets.size(); ++i)
                    if (remaining[i] > 0 && (targets[i].visible & (std::uint16_t{1} << k)) && dist(p, targets[i].pos) <= f.attack_range()) {
                        const float value = targets[i].strength / remaining[i];
                        if (value > score) at = static_cast<int>(i), score = value;
                    }
                if (at < 0) return false;
                const float hit = std::min(basic_damage, remaining[at]);
                remaining[at] -= hit;
                total += hit;
                return true;
            };
            for (int turn = 0; turn < horizon; ++turn) {
                const bool walk = turn == 0 && (moved || here != self.pos);
                const bool attack = turn > 0 || (can_attack && (!walk || !f.ranged));
                const bool cast = slot >= 0 && use == turn + 1 && (turn > 0 || can_cast)
                    && self.ability_ready(slot, world.round + turn) && !(walk && f.abilities[slot].excludes_walking);
                if (cast && f.abilities[slot].kind == AbilityKind::damage && !held) {
                    int at = -1;
                    float value = 0;
                    for (std::size_t i = 0; i < targets.size(); ++i)
                        if ((targets[i].visible & (std::uint16_t{1} << k)) && dist(p, targets[i].pos) <= f.abilities[slot].range())
                            if (const float hit = std::min(spell_damage, remaining[i]); hit > value) at = static_cast<int>(i), value = hit;
                    if (at >= 0) remaining[at] -= value, total += value;
                }
                const bool attacked = attack && basic();
                // A ranged walk spends its attack; resetting that spent attack is legal too.
                if (cast && f.abilities[slot].kind == AbilityKind::attack_reset && (attacked || (walk && f.ranged))) {
                    int at = -1;
                    for (std::size_t i = 0; i < targets.size(); ++i)
                        if (remaining[i] > 0 && (targets[i].visible & (std::uint16_t{1} << k)) && dist(p, targets[i].pos) <= f.attack_range()
                            && (at < 0 || remaining[i] < remaining[at])) at = static_cast<int>(i);
                    const bool refunded = at >= 0 && f.passive == Passive::reset_on_kill && remaining[at] <= basic_damage;
                    if (at >= 0 && (!reset_held || refunded)) {
                        const float hit = std::min(basic_damage, remaining[at]);
                        remaining[at] -= hit;
                        total += hit;
                    }
                }
            }
            best = std::max(best, total);
        }
        return best;
    };
    const auto exposure = [&](vec2 p, bool supported) {
        float hit = 0;
        for (const int h : map.groups_near(p, map.max_camp_reach)) {
            const auto& belief = world.camps[h];
            if (belief.state == CampState::cleared) continue;
            const auto& members = map.groups[h].members;
            for (std::size_t i = 0; i < members.size(); ++i) {
                const auto& m = members[i];
                if ((belief.state == CampState::alive && belief.health[i] <= 0) || m.strength <= 0 || dist(p, m.pos) > m.reach) continue;
                bool tanked = false;
                if (supported)
                    for (const auto& a : world.allies)
                        tanked |= !a.is_self && a.alive && a.visible && a.channel != Channel::teleport
                            && !(a.channel == Channel::recall && a.channel_end_round <= world.round + horizon)
                            && dist(a.pos, m.pos) < dist(p, m.pos);
                if (!tanked) hit += m.strength;
            }
        }
        return static_cast<float>(horizon) * hit * soften;
    };
    const float stay = damage(0) - heal_rounds(world, exposure(here, true), static_cast<float>(home_steps)) * lost_output;
    if (interior) {
        const bool fire = exposure(here, false) <= spare && stay > 0;
        world.throw_if_stale();
        return fire;
    }
    int best = 0;
    float value = stay;
    for (int k = 1; k < count; ++k) {
        // Two camp phases, even if our damage would kill or stun a monster. Support prices only
        // recovery: the full raw hit reserve still applies if every other body walks away.
        if (exposure(endpoints[k], false) > spare) continue;
        const float gain = damage(k) - heal_rounds(world, exposure(endpoints[k], true), static_cast<float>(home_steps + 1)) * lost_output;
        if (gain > value) best = k, value = gain;
    }
    if (best == 0) return false;
    world.throw_if_stale();
    const bool moved = pathing.try_move(endpoints[best]);
    world.throw_if_stale();
    return moved;
}

// A big group cleared by stationary spells out of its monsters' reach, so that nobody takes a hit;
// harmless members fall to basic attacks from there, the rest once the monsters are dead.
bool kite(const World& world, Pathing& pathing, Memory& memory) {
    world.throw_if_stale();
    const auto& map = world.map();
    const vec2 here = my_position();
    int g = -1, best_cost = 0;
    // contest_capture's rule: a body of ours on a camp tile before their hold pays.
    const auto too_late = [&](int h) { return steps_to(map.groups[h], here) > enemy_hold_left(world, world.camps[h]); };
    for (int h = 0; h < static_cast<int>(map.groups.size()); ++h) {
        if (!big_group(map.groups[h])) continue;
        const auto& c = world.camps[h];
        const int steps = dist(here, map.groups[h].centre);
        if (c.state == CampState::cleared && ((c.holder == team::enemy && too_late(h)) || contest_manned(world, h, here))) continue;
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
            if (!test(tiles, here) && too_late(g)) return false;
            memory.claim = g;
            memory.crew = false;
            if (test(tiles, here)) return true; // our tile keeps their hold from counting
            const auto& free = free_tiles(tiles);
            if (!board_empty(free)) pathing.step_towards_funded(free, end_reserve);
            return true;
        }
        if (capture_taken(world, g, here) || dist(here, G.centre) > 2 * vision_radius) return false;
        memory.claim = g;
        memory.crew = false;
        pathing.step_towards_funded(G.tiles(), end_reserve);
        return true;
    }
    const bool fresh = c.state == CampState::respawning;
    static bitboard threat{cambc::uninitialized}, near{cambc::uninitialized}, goals{cambc::uninitialized},
        basic{cambc::uninitialized}, stations{cambc::uninitialized}, forbidden{cambc::uninitialized},
        seen_stations{cambc::uninitialized};
    clear_board(threat);
    clear_board(near);
    clear_board(basic);
    const auto& f = world.me().facts();
    const int range = f.attack_range();
    int ground_range = 0, unit_range = 0;
    for (const auto& a : f.abilities) {
        if (a.kind != AbilityKind::damage || a.multiplier <= 0) continue;
        if (a.target == Targeting::ground) ground_range = std::max(ground_range, a.range());
        if (a.target == Targeting::unit) unit_range = std::max(unit_range, a.range());
    }
    const int spell_reach = std::max(unit_range, ground_range > 0 ? ground_range + 1 : 0);
    // A unit spell needs sight of its target: its stations see the member, as ground stations do.
    bool ground_stations = ground_range > 0, unit_stations = !ground_stations && unit_range > 0;
    const int sight_range = ground_stations ? ground_range + 1 : unit_range;
    if (ground_stations || unit_stations)
        for (std::size_t i = 0; i < G.members.size(); ++i) {
            if ((!fresh && c.health[i] <= 0) || G.members[i].strength <= 0) continue;
            const bool ready = pathing.prepare_member(g, static_cast<int>(i), sight_range, end_reserve);
            world.throw_if_stale();
            if (!ready) {
                ground_stations = unit_stations = false;
                break;
            }
        }
    const int station_range = ground_stations ? spell_reach : ability_range;
    bool attackers = false;
    for (std::size_t i = 0; i < G.members.size(); ++i) {
        if (!fresh && c.health[i] <= 0) continue;
        const vec2 p = G.members[i].pos;
        if (G.members[i].strength > 0) {
            attackers = true;
            draw_square(threat, p, static_cast<float>(G.members[i].reach));
            if (unit_stations) near |= pathing.member_attack_tiles(g, static_cast<int>(i), unit_range);
            else if (!ground_stations) draw_square(near, p, static_cast<float>(station_range));
            if (ground_stations) {
                const auto& viewers = pathing.member_attack_tiles(g, static_cast<int>(i), ground_range + 1);
                if (unit_range > 0) {
                    clear_board(stations);
                    draw_square(stations, p, static_cast<float>(unit_range));
                    and_into(viewers, stations, seen_stations);
                    near |= seen_stations;
                }
                clear_board(forbidden);
                for (const int other : map.groups_near(p, 2)) {
                    if (other == g || world.camps[other].state != CampState::alive) continue;
                    const auto& members = map.groups[other].members;
                    for (std::size_t j = 0; j < members.size(); ++j)
                        if (world.camps[other].health[j] > 0) draw_square(forbidden, members[j].pos, 1);
                }
                clear_board(stations);
                for (int dy = -1; dy <= 1; ++dy)
                    for (int dx = -1; dx <= 1; ++dx) {
                        const vec2 centre{p.x + dx, p.y + dy};
                        if (in_bounds(centre) && !test(forbidden, centre)) draw_square(stations, centre, static_cast<float>(ground_range));
                    }
                and_into(viewers, stations, seen_stations);
                near |= seen_stations;
            }
        } else {
            draw_square(basic, p, static_cast<float>(range));
        }
    }
    // Only harmless members: farm clears them. Champions without spells stand guard with the
    // casters, for the fights and the capture.
    world.throw_if_stale();
    if (!attackers) return false;
    const bool ally_in = ally_claims(world, g);
    memory.claim = g;
    memory.crew = ally_in;
    clear_board(goals);
    goals |= near;
    goals &= map.standable;
    drop(goals, threat);
    if (board_empty(goals)) return false;
    // Ranged: where a basic attack also reaches a harmless member, if that is a safe walk away.
    basic &= goals;
    const bool basic_first = world.me().facts().ranged && !board_empty(basic);
    const bool safe_here = !test(threat, here);
    const auto hit = [&] {
        if (fresh) return false;
        const bool cast = cast_at_camp(world, g, false, true);
        const bool attacked = attack_camp(world, [&](int h) { return h == g; }) >= 0;
        if (attacked) reset_and_attack_camp(world, g);
        return cast || attacked;
    };
    if (!safe_here && ground_stations && kite_productive_action(world, pathing, g, true)) {
        const bool hit_now = hit();
        const bool reset = reset_and_attack_camp(world, g);
        if (hit_now || reset) return true;
    }
    const auto& first = basic_first ? basic : goals;
    if (safe_here) {
        const bool placed = test(first, here);
        if (hit()) return true;
        if (placed) {
            if (ground_stations && kite_productive_action(world, pathing, g)) {
                hit();
                reset_and_attack_camp(world, g);
            }
            return true;
        }
    }
    // Far off, the static walk to within reach; the live route around the monsters once near.
    if (dist(here, G.centre) > vision_radius + station_range) {
        if (const auto* field = pathing.approach(g, station_range)) {
            if (pathing.step_towards(*field)) return true;
        } else if (pathing.step_closer(G.centre)) return true;
        if (!ground_stations) return true;
    }
    // A short way to a basic attack's tile, else any safe one: the long way round to the far side
    // of the monsters costs more than the attacks pay.
    const int cap = 2 * (vision_radius + station_range);
    bool moved = basic_first && pathing.step_towards(basic, &threat, vision_radius);
    if (!moved && !test(goals, here)) moved = pathing.step_towards(goals, &threat, cap);
    // A sleeping group hits nobody passing through its reach.
    if (!moved && !test(goals, here) && c.awake == Awake::asleep) moved = pathing.step_towards(goals, nullptr, cap);
    // No way within the cap (round a lake): the static walk.
    if (!moved && !test(goals, here))
        if (const auto* field = pathing.approach(g, station_range))
            moved = pathing.step_towards(*field, c.awake == Awake::asleep ? nullptr : &threat);
    if (!moved && !safe_here) {
        static bitboard out{cambc::uninitialized};
        clear_board(out);
        out |= map.standable;
        drop(out, threat);
        pathing.step_towards(out, nullptr, 2 * G.reach);
    }
    const bool hit_safe = !test(threat, my_position()) && hit();
    if (ground_stations && !moved && !hit_safe && safe_here && !test(goals, my_position())) return false;
    return true;
}

// A cleared gem group in sight that the enemy holds or stands on, and that we can reach before the
// hold pays: a body of ours on one of its tiles stops the count. Its gems, denied within a few
// steps, beat any farm cycle's rate, however small the group.
bool contest_capture(const World& world, Pathing& pathing, Memory& memory) {
    const auto& map = world.map();
    const vec2 here = my_position();
    int best = -1, best_steps = unreachable;
    world.each_cleared([&](int g) {
        const auto& G = map.groups[g];
        const auto& c = world.camps[g];
        if (G.gems == 0 || dist(here, G.centre) > vision_radius + 2) return;
        if (!enemy_on(world, G.tiles()) && c.holder != team::enemy) return;
        if (contest_manned(world, g, here)) return;
        const int steps = steps_to(G, here);
        if (steps > enemy_hold_left(world, c) || steps >= best_steps) return;
        best = g, best_steps = steps;
    });
    if (best < 0) return false;
    const auto& free = free_tiles(map.groups[best].tiles());
    if (free.is_empty() || !pathing.step_towards(free, nullptr, best_steps + max_detour)) return false;
    memory.claim = best;
    memory.crew = false;
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

// A visible enemy within `range` of `from` that one basic attack kills.
const ChampionBelief* sure_kill(const World& world, vec2 from, int range) {
    const float health = my_health();
    const float strength = my_strength() * damage_scale(world.me().facts().passive, health, my_max_health());
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible || dist(from, e.pos) > range || e.retaliation() >= health) continue;
        const float shield = e.shield > 0 ? shield_value(e.handle) : 0.0f;
        if (e.health + shield <= strength * e.taken) return &e;
    }
    return nullptr;
}

// Nothing but `enemy` could hit us at p before our next turn.
bool only_threat(Safety& safety, vec2 p, int enemy) {
    if (safety.camp_damage(p, true, true) > 0) return false;
    std::array<Safety::ThreatAt, 16> at;
    const int n = safety.threats_at(p, at);
    for (int i = 0; i < n; ++i)
        if (at[i].enemy != enemy && at[i].blow.hits) return false;
    return true;
}

// A sure kill from a tile a step away (melee: the walk keeps the attack) or a ready dash away,
// where nothing but the victim reaches us: the victim's tile, else {-1, -1}.
vec2 step_to_kill(const World& world, Pathing& pathing, Safety& safety, int range, bool melee) {
    const vec2 here = my_position();
    const bool walk = melee && my_can_move();
    const bool dash = world.me().facts().has_dash() && my_can_cast();
    if ((!walk && !dash) || !sure_kill(world, here, range + (dash ? dash_range : 1))) return {-1, -1};
    const auto strike = [&](const ChampionBelief& kill) {
        try {
            attack_champion(kill.handle);
            return true;
        } catch (const cambc::error&) {
            return false;
        }
    };
    if (walk) {
        const auto& blocked = pathing.blocked();
        for (const auto d : directions) {
            const vec2 p = here + d;
            if (!in_bounds(p) || test(blocked, p)) continue;
            if (const auto* kill = sure_kill(world, p, range); kill && only_threat(safety, p, kill->index) && pathing.try_move(p))
                return strike(*kill) ? kill->pos : vec2{-1, -1};
        }
    }
    if (dash) {
        static bitboard tiles{cambc::uninitialized};
        clear_board(tiles);
        const ChampionBelief* victim = nullptr;
        for (auto p : Tiles<5 * 5>{pathing.dash_landings()})
            if (const auto* kill = sure_kill(world, p, range); kill && (!victim || kill == victim) && only_threat(safety, p, kill->index))
                victim = kill, tiles.set(p);
        if (victim && dash_onto(world, pathing, tiles) && strike(*victim)) return victim->pos;
    }
    return {-1, -1};
}

// After our hits: an enemy we killed stays a live threat around its tile in World (dash landings,
// retreat steps) and, once refresh() has read it alive, in Safety: read vision again.
void see_kills(World& world, Pathing& pathing, Safety& safety) {
    const bool stunned = world.read_stuns();
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && !is_alive(e.handle)) {
            see_again(world, pathing, safety);
            return;
        }
    if (stunned) {
        std::destroy_at(&safety);
        std::construct_at(&safety, world);
    }
    safety.refresh();
}

void retreat(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    world.throw_if_stale();
    auto& me = cambc::self();
    decision = 'R';
    memory.claim = -1;
    memory.banking = bankable_bag(world, pathing) > 0 && !retaining_gems(world, pathing);
    const bool melee = world.me().facts().walk_and_attack_independent();
    const int range = world.me().facts().attack_range();
    const vec2 here = my_position();
    vec2 dead{-1, -1};
    // A sure kill first. A ranged attack spends the walk, so only where standing is no worse:
    // nothing else reaches us here, or the dash still lands out of every reach.
    if (const auto* kill = my_can_attack() ? sure_kill(world, here, range) : nullptr;
        kill && (melee || only_threat(safety, here, kill->index) || dash_clears(world, pathing, kill->pos))) {
        try {
            attack_champion(kill->handle);
            dead = kill->pos;
        } catch (const cambc::error&) {
        }
    }
    // A kill a step or a dash off, where only the victim reaches us; else the homeward step may still land beside it.
    if (dead.x < 0 && my_can_attack()) dead = step_to_kill(world, pathing, safety, range, melee);
    // A melee kill one step off waits for the step, which may land beside it.
    const bool held = melee && my_can_attack() && sure_kill(world, here, range + 1);
    if (melee && !held) attack_enemy(world);
    if (!my_can_attack()) reset_and_attack_enemy(world, true);
    cast_at_enemies(world, escape_step_value);
    if (!me.is_alive()) return;
    if (!my_can_attack() || !my_can_cast()) see_kills(world, pathing, safety);
    // A tribute survives damage; a recall does not.
    if (can_tribute_safely(world, pathing, safety, memory)) {
        bank_gems(world, pathing, safety, memory, false);
        return;
    }
    // The escape dash shares the one cast: the reset only after it, from a melee attack or a ranged walk.
    dash_away(world, pathing, pathing.to_ally_spawn(), dead);
    if (reset_and_attack_enemy(world)) see_kills(world, pathing, safety);
    else see_stuns(world, safety); // Heart of Ruin's landing
    if (!flee_camps(world, pathing, safety, pathing.to_ally_spawn())) retreat_step(world, pathing, safety, pathing.to_ally_spawn());
    if (melee && attack_enemy(world)) reset_and_attack_enemy(world, true);
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
    const auto free_hit = [&](int g) {
        const auto& c = world.camps[g];
        return g != held && (groups[g].strength <= 0 || (c.awake != Awake::asleep && c.asleep == 0));
    };
    if (const int hit = attack_camp(world, free_hit); hit >= 0) {
        cast_at_camp(world, hit);
        reset_and_attack_camp(world, hit);
    }
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
            decision = 'R';
            pathing.set_guard(nullptr);
            dash_away(world, pathing, pathing.to_ally_spawn());
            retreat_step(world, pathing, safety, pathing.to_ally_spawn());
            return;
        }
        const vec2 here = cambc::self().position();
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


// Each camp member whose strike reaches p, as f(group, member index, member), in groups_near order;
// stops at the first f that returns false.
template <class F>
bool each_camp_striker(const World& world, vec2 p, F&& f) {
    for (const int g : world.map().groups_near(p, world.map().max_camp_reach)) {
        const auto& members = world.map().groups[g].members;
        for (std::size_t i = 0; i < members.size(); ++i)
            if (members[i].strength > 0 && dist(p, members[i].pos) <= members[i].reach && !f(g, i, members[i])) return false;
    }
    return true;
}

// Willow holds no fight: a tile an enemy is likely to hit (want_home's test) or any camp member may
// hit is unsafe. `enemies`: false when no enemy can hit p, which spares their search.
SupportExposure exposure_at(const World& world, Safety& safety, vec2 p, bool enemies = true) {
    SupportExposure risk;
    if (enemies) {
        const auto b = safety.bound(p);
        risk.damage = b.damage, risk.imminent = b.doubled, risk.enemy = b.threat, risk.stun = b.stuns;
    } else {
        risk.damage = risk.imminent = safety.camp_damage(p, true, true);
    }
    each_camp_striker(world, p, [&](int g, std::size_t i, const CampMember&) {
        const auto& c = world.camps[g];
        const bool returning = c.state == CampState::respawning && c.respawn_round <= world.round + 1;
        // Asleep too: a tank may leave before the next camp phase, and no ally's protection is borrowed.
        risk.camp = returning || (c.state == CampState::alive && c.health[i] > 0);
        return !risk.camp;
    });
    return risk;
}

// Worked out on first need after we move or see again. Its guard board stays at one address: a
// guard Pathing holds reads the latest.
const Stations& stations(const World& world, Safety& safety, vec2 here) {
    auto& s = stations_cache();
    if (s.observations == world.observations && s.origin == here) return s;
    world.throw_if_stale();
    // Keyed only once complete: a read that throws part-way leaves nothing to reuse.
    s.origin = {-1, -1};
    clear_board(s.guard);
    const bool enemies = safety.credible_enemy_may_hit_within(here, 1);
    for (int k = 0; k < 9; ++k) {
        auto& tile = s.tiles[k];
        tile.p = k == 0 ? here : here + directions[k - 1];
        tile.open = in_bounds(tile.p) && test(world.map().open_for_us, tile.p);
        // Ranged threats shadowcast from the candidate; an opaque origin is invalid.
        tile.risk = tile.open ? exposure_at(world, safety, tile.p, enemies) : SupportExposure{};
        if (tile.risk.enemy) set_tile(s.guard, tile.p);
    }
    world.throw_if_stale();
    s.observations = world.observations;
    s.origin = here;
    return s;
}

// stations(here).tiles[0].risk alone, for when no step or guard read follows this turn: after
// Willow's walk, or at the turn's end.
SupportExposure exposure_here(const World& world, Safety& safety) {
    const vec2 here = my_position();
    if (const auto& s = stations_cache(); s.observations == world.observations && s.origin == here) return s.tiles[0].risk;
    static struct {
        std::uint32_t observations = 0;
        vec2 p{-1, -1};
        SupportExposure risk;
    } memo;
    if (memo.observations != world.observations || memo.p != here) {
        const bool open = in_bounds(here) && test(world.map().open_for_us, here);
        memo.risk = open ? exposure_at(world, safety, here, safety.credible_enemy_may_hit_within(here, 1)) : SupportExposure{};
        memo.observations = world.observations, memo.p = here;
    }
    return memo.risk;
}

// Ours, or a free open tile a step reaches.
bool station_legal(Pathing& pathing, const Station& tile, vec2 here) {
    return tile.open && (tile.p == here || (my_can_move() && !test(pathing.blocked(), tile.p)));
}

SupportExposure support_exposure(const World& world, Safety& safety, vec2 p) {
    if (const vec2 here = my_position(); world.me().facts().heals() && dist(p, here) <= 1)
        for (const auto& tile : stations(world, safety, here).tiles)
            if (tile.p == p) return tile.risk;
    return exposure_at(world, safety, p);
}

bool stationary_support_output(const World& world, int work) {
    world.throw_if_stale();
    bool hit = attack_enemy(world);
    int camp = -1;
    if (!hit && my_can_attack())
        camp = attack_camp(world, [&](int g) {
            return world.map().groups[g].strength <= 0 || (g == work && world.camps[g].awake != Awake::asleep);
        });
    hit |= camp >= 0;
    if (hit && my_cooldown(0) > 0) {
        if (camp >= 0) reset_and_attack_camp(world, camp);
        else reset_and_attack_enemy(world);
    }
    return hit;
}

bool support_view(Reach::Window viewers, vec2 target, vec2 p) {
    const int x = p.x - target.x, y = p.y - target.y;
    return std::abs(x) <= Reach::Window::radius && std::abs(y) <= Reach::Window::radius
           && static_cast<bool>(viewers & Reach::Window::bit(Reach::Window::at(x, y)));
}

const ChampionBelief* support_endpoint(const World& world, cambc::champion_type type) {
    for (const auto& a : world.allies)
        if (a.type == type) return &a;
    return nullptr;
}

void close_recovery(Memory& memory, float health) {
    if (memory.recovery_start >= 0) {
        memory.recovery_closed_group = memory.recovery_group;
        memory.recovery_reentry = health >= 0;
    }
    if (health < 0) memory.recovery_reentry = false, memory.recovery_closed_group = -1;
    memory.recovery_start = -1;
    memory.recovery_turns = 0;
    memory.recovery_closed_health = health;
}

bool recovered_for_work(const World& world, Safety& safety, const Memory& memory) {
    const float health = my_health();
    if (health <= safety.damage_bound(my_position(), true)) return false;
    const int g = memory.farm_group;
    if (g < 0 || g >= static_cast<int>(world.camps.size()) || world.camps[g].state != CampState::alive) return true;
    float rounds = 0;
    const float damage = camp_hit_factor() * min_camp_damage(world, g, floored_output(world.me()), &rounds);
    return params::camp_risk * damage <= health - params::recall_health_fraction * my_max_health();
}

int heal_range(const ChampionBelief& healer) {
    const auto& f = healer.facts();
    return f.abilities[f.slot_of(AbilityKind::heal)].range();
}

// A unit our own ward sees stays visible to us wherever we step (wards.vision). Read per call: a
// ward can go down mid-turn without a re-observe (submit_here); its mask is cast again only when it moves.
bool own_ward_sees(const World& world, vec2 p) {
    static bitboard sight{cambc::uninitialized};
    static vec2 cast_at{-1, -1};
    static std::array<cambc::detail::ward_info, 16> raw;
    std::uint32_t k = 0;
    ok(cambc::detail::sdk_wards(raw.data(), static_cast<std::uint32_t>(raw.size()), &k));
    const auto own = static_cast<std::uint32_t>(world.map().team_a ? 0 : 1);
    for (std::uint32_t i = 0; i < k && i < raw.size(); ++i) {
        const auto& w = raw[i];
        if (w.team != own || w.owner != my_handle() || w.disabled) continue;
        if (const vec2 at{w.x, w.y}; at != cast_at) ok(cambc::detail::sdk_ward_vision(at.x, at.y, sight.ptr())), cast_at = at;
        return test(sight, p);
    }
    return false;
}

// Tiles within `range` of a visible ally from which we see it, as the search's viewers(): exact
// where attack_viewers leaves out bushes beyond a step for our own tile, which sees it now, and
// every tile when our ward sees it.
Reach::Window heal_viewers(const World& world, vec2 target, int range) {
    range = std::clamp(range, 0, Reach::Window::radius);
    Reach::Window w;
    if (own_ward_sees(world, target)) {
        for (int y = -range; y <= range; ++y)
            for (int x = -range; x <= range; ++x) w |= Reach::Window::bit(Reach::Window::at(x, y));
        return w;
    }
    w = attack_viewers(world, target, range);
    if (const vec2 here = my_position(); dist(here, target) <= range)
        w |= Reach::Window::bit(Reach::Window::at(here.x - target.x, here.y - target.y));
    return w;
}

struct HealView {
    HealTarget target;
    Reach::Window viewers; // tiles that see it within heal range
};

// heal_target's allies within a step of our heal range of p.
int heal_views(const World& world, vec2 p, float amount, std::array<HealView, 8>& out) {
    const int range = heal_range(world.me());
    int n = 0;
    for (const auto& a : world.allies)
        if (dist(p, a.pos) <= range + 1)
            if (const auto t = heal_target(world, a, amount)) out[n++] = {*t, heal_viewers(world, t->pos, range)};
    return n;
}

// One is in heal range of p: heal_ally casts from there without a step.
bool heal_lands_from(const World& world, vec2 p, const std::array<HealView, 8>& views, int n) {
    for (int t = 0; t < n; ++t)
        if (dist(p, views[t].target.pos) <= heal_range(world.me())) return true;
    return false;
}

// The neighbouring station `ok` accepts from which a heal lands best: the most restored, then on
// the lowest ally, then the least `cost`. `here` if none.
template <class Ok, class Cost>
vec2 heal_station(const World& world, Pathing& pathing, Safety& safety, vec2 here, const std::array<HealView, 8>& views,
                  int n, Ok&& ok, Cost&& cost) {
    vec2 best = here;
    float best_gain = 0, best_fraction = 0;
    int best_cost = unreachable;
    for (int k = 1; k < 9; ++k) {
        const auto& tile = stations(world, safety, here).tiles[k];
        if (!station_legal(pathing, tile, here) || !ok(tile)) continue;
        const int g = world.map().group_at(tile.p);
        if (g >= 0 && world.camps[g].state == CampState::cleared) continue;
        const int c = cost(tile);
        for (int t = 0; t < n; ++t) {
            const auto& target = views[t].target;
            if (!support_view(views[t].viewers, target.pos, tile.p)) continue;
            if (target.gain > best_gain || (target.gain == best_gain && target.fraction < best_fraction)
                || (target.gain == best_gain && target.fraction == best_fraction && c < best_cost))
                best = tile.p, best_gain = target.gain, best_fraction = target.fraction, best_cost = c;
        }
    }
    return best;
}

bool willow_bank_heal_step(World& world, Pathing& pathing, Safety& safety, const Field& field) {
    if (!world.me().facts().heals() || !my_can_move() || winning_bag(world)
        || closing(world, pathing) || holding_capture(world, pathing) || contesting(world)) return false;
    float amount = 0;
    if (!heal_ready(world, world.me(), amount)) return false;
    const vec2 here = my_position();
    const int here_steps = field.at(here);
    if (here_steps == unreachable) return false;
    std::array<HealView, 8> views;
    const int n = heal_views(world, here, amount, views);
    if (n == 0 || heal_lands_from(world, here, views, n)) return false;
    world.throw_if_stale();
    guard_steps(world, pathing, safety);
    if (!stations(world, safety, here).tiles[0].risk.safe()) return false;
    const vec2 best = heal_station(world, pathing, safety, here, views, n, [&](const Station& tile) {
        const int steps = field.at(tile.p);
        return tile.risk.safe() && steps != unreachable && steps <= here_steps;
    }, [&](const Station& tile) { return field.at(tile.p); });
    world.throw_if_stale();
    if (best == here) return false;
    // Equal-distance banking may spend one progress turn for a heal available after this step.
    if (!pathing.try_move(best)) {
        see_again(world, pathing, safety); // a hidden unit refused it, unseen by see_revealed
        world.throw_if_stale();
        return false;
    }
    see_revealed(world, pathing, safety);
    heal_ally(world);
    return true;
}

bool immediate_camp_finish(const World& world, vec2 here, float basic) {
    const int range = world.me().facts().attack_range();
    for (const int g : world.map().groups_near(here, range)) {
        const auto& c = world.camps[g];
        const auto& members = world.map().groups[g].members;
        for (std::size_t i = 0; i < members.size(); ++i) {
            if (dist(here, members[i].pos) > range || !test(world.visible, members[i].pos)) continue;
            if (c.state_round != world.round) return true;
            if (c.state != CampState::alive) continue;
            // Preserve even an individual member finish, with a ready-reset upper bound.
            if (c.health_round[i] != world.round) return true;
            if (!(c.health[i] > 0)) continue; // dead: nothing left to finish
            if (c.health[i] <= 2 * basic) return true;
        }
    }
    return false;
}

bool willow_independent_heal_step(World& world, Pathing& pathing, Safety& safety) {
    if (stunned_turn || !my_can_move()) return false;
    const vec2 here = my_position();
    if (test(world.map().ally_spawn, here)) return false;
    float amount = 0;
    if (!heal_ready(world, world.me(), amount)) return false;
    guard_steps(world, pathing, safety);
    const auto quiet = [](const SupportExposure& risk) {
        return risk.safe() && !risk.stun && risk.imminent == 0;
    };
    std::array<HealView, 8> views;
    int n = heal_views(world, here, amount, views);
    if (n == 0 || heal_lands_from(world, here, views, n)) return false;
    // The basics the step gives up: a ranged walk spends the attack and the heal takes the turn's
    // cast, so with a camp in reach the attack and the ready reset's; and a possible return step's.
    const auto& f = world.me().facts();
    const int reset = f.slot_of(AbilityKind::attack_reset);
    const bool reset_ready = reset >= 0 && world.me().ability_ready(reset, world.round) && my_cooldown(reset) == 0;
    const int forgone = 1 + (any_within(live_camp_tiles(), here, f.attack_range()) ? 1 + reset_ready : 0);
    const float basic = my_strength() * camp_dealt_factor();
    n = static_cast<int>(std::remove_if(views.begin(), views.begin() + n,
                                        [&](const HealView& v) { return !(v.target.gain > forgone * basic); }) - views.begin());
    if (n == 0 || immediate_camp_finish(world, here, basic)) return false;
    if (!quiet(stations(world, safety, here).tiles[0].risk)) return false;
    const vec2 best = heal_station(world, pathing, safety, here, views, n, [&](const Station& tile) { return quiet(tile.risk); },
                                   [](const Station&) { return 0; });
    world.throw_if_stale();
    if (best == here) return false;
    debug_block({
        std::printf("WIH %d %u from %d,%d to %d,%d basic %.1f\n", world.round,
            static_cast<std::uint32_t>(world.me().handle), here.x, here.y, best.x, best.y, basic);
    });
    if (!pathing.try_move(best)) {
        see_again(world, pathing, safety); // a hidden unit refused it, unseen by see_revealed
        world.throw_if_stale();
        support_retreat = !support_exposure(world, safety, my_position()).safe();
        return false;
    }
    support_owned = true;
    see_revealed(world, pathing, safety);
    const bool healed = heal_ally(world);
    debug_block({ std::printf("WIH-DONE %d %u moved 1 healed %d\n", world.round,
        static_cast<std::uint32_t>(world.me().handle), healed); });
    decision = 'h';
    return true;
}

// Work the support formation must not interrupt: a capture, a bag to bank, a trip to shop.
bool support_work(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    return holding_capture(world, pathing) || contesting(world)
           || (bankable_bag(world, pathing) > 0 && !retaining_gems(world, pathing)) || wants_shop(world, pathing, safety, memory);
}

// A single current-plus-neighbours pass owns both formation and local recovery. Willow comes here
// neither wanting home nor at work (decide).
bool local_support(World& world, Pathing& pathing, Safety& safety, Memory& memory, bool leave, bool& mate_eligible) {
    mate_eligible = false;
    const bool willow = world.me().type == cambc::champion_type::willow;
    const bool prism = world.me().type == cambc::champion_type::prism;
    if ((!willow && !prism) || stunned_turn) return false;
    std::optional<bool> protects;
    const auto protected_work = [&] {
        if (!protects) protects = prism && support_work(world, pathing, safety, memory);
        return *protects;
    };
    const auto* mate = support_endpoint(world, willow ? cambc::champion_type::prism : cambc::champion_type::willow);
    const vec2 here = my_position();
    const float health = my_health();
    const auto abandon_recovery = [&] {
        if (prism && memory.recovery_start >= 0) {
            close_recovery(memory, health);
            support_retreat = !recovered_for_work(world, safety, memory);
        }
        return false;
    };
    if (!world.me().alive || world.me().respawned_round == world.round || memory.round < 0) {
        close_recovery(memory, -1);
        memory.formation_start = -1;
        memory.formation_turns = 0;
    } else if (memory.round != world.round - 1) {
        close_recovery(memory, health);
        memory.formation_start = world.round - 4;
        memory.formation_turns = 4;
    }
    if (prism && memory.recovery_reentry) {
        if (memory.recovery_closed_group < 0 || memory.farm_group != memory.recovery_closed_group
            || test(world.map().ally_spawn, here) || recovered_for_work(world, safety, memory))
            memory.recovery_reentry = false;
        else {
            if (!leave && protected_work() && holding_capture(world, pathing)) return false;
            support_retreat = true;
            return false;
        }
    }
    if (prism && memory.farm_group != memory.recovery_closed_group) memory.recovery_closed_health = -1;
    if (!mate || !mate->alive || !mate->visible || !mate->can_act(world.round) || !visible_record(mate->handle)) {
        abandon_recovery();
        memory.formation_start = -1;
        return false;
    }
    const bool observed_channel = mate->channel == Channel::tribute || mate->channel == Channel::teleport
                                  || (mate->channel == Channel::recall
                                      && kept_recall(mate->handle, mate->recall_turns()));
    mate_eligible = !observed_channel;
    if (observed_channel || protected_work() || test(world.map().ally_spawn, here)) {
        if (memory.recovery_start >= 0) close_recovery(memory, health);
        if (prism && observed_channel && !protected_work()) support_retreat = !recovered_for_work(world, safety, memory);
        return false;
    }

    std::array<HealView, 8> views;
    int view_count = 0;
    float amount = 0;
    const auto& healer = willow ? world.me() : *mate;
    const bool ready = heal_ready(world, healer, amount);
    if (willow && ready) view_count = heal_views(world, here, amount, views);
    Reach::Window formation_view;
    if (prism) {
        if (memory.recovery_start >= 0 && (health > memory.recovery_health || !ready)) {
            close_recovery(memory, health);
            support_retreat = !recovered_for_work(world, safety, memory);
            return false;
        }
        const float gain = std::min(amount, my_max_health() - health);
        if (!ready || !worth_healing(amount, gain, health / my_max_health()) || !support_exposure(world, safety, mate->pos).safe())
            return abandon_recovery();
        if (memory.recovery_start < 0 && memory.recovery_closed_health >= 0 && health >= memory.recovery_closed_health) return false;
        formation_view = attack_viewers(world, mate->pos, heal_range(healer));
        const float usable = my_max_health() * (1 - params::recall_health_fraction);
        const float out = static_cast<float>(world.map().from_ally_spawn().at(here));
        const float saved = gain / usable * (static_cast<float>(recall_turns(world)) + out);
        const int detour = support_view(formation_view, mate->pos, here) ? 0 : 1;
        const int wait = mate->acted ? 1 : 0;
        if (!leave && saved <= static_cast<float>(detour + wait + 1)) return false;
        if (memory.recovery_start >= 0 && (memory.recovery_turns >= 4 || world.round - memory.recovery_start >= 4)) {
            close_recovery(memory, health);
            support_retreat = !recovered_for_work(world, safety, memory);
            return false;
        }
    } else {
        formation_view = heal_viewers(world, mate->pos, heal_range(healer));
    }
    const auto here_risk = support_exposure(world, safety, here);
    const int work = willow ? comms::claim_of(world, mate->index) : memory.farm_group;
    if (willow && !ready && here_risk.safe() && stationary_support_output(world, work)) {
        support_owned = true;
        memory.claim = -1;
        memory.crew = false;
        memory.siege = false;
        memory.formation_start = -1;
        memory.formation_turns = 0;
        decision = 'h';
        return true;
    }
    const Field* work_route = nullptr;
    if (willow && !ready && work >= 0 && work < static_cast<int>(world.map().groups.size())
        && memory.farm_group == work && pathing.approach_ready(work, walk_range(world, work)))
        work_route = pathing.approach(work, walk_range(world, work));
    const bool formation_expired = memory.formation_turns >= 4
                                   || (memory.formation_start >= 0 && world.round - memory.formation_start >= 4);
    const bool active_clear = willow && memory.claim >= 0 && memory.claim == memory.farm_group
                              && memory.claim < static_cast<int>(world.camps.size())
                              && world.camps[memory.claim].state == CampState::alive
                              && world.camps[memory.claim].awake != Awake::asleep;
    const auto& blocked = pathing.blocked();
    vec2 best = here;
    int best_gap = unreachable, best_home = unreachable;
    float best_gain = -1;
    bool found = false;
    for (int k = -1; k < 8; ++k) {
        const vec2 p = k < 0 ? here : here + directions[k];
        if (!in_bounds(p) || (p != here && (!my_can_move() || !test(world.map().standable, p) || test(blocked, p)))) continue;
        const int camp = world.map().group_at(p);
        if (willow && p != here && camp >= 0 && world.camps[camp].state == CampState::cleared) continue;
        const bool in_range = support_view(formation_view, mate->pos, p);
        const int gap = in_range ? 0 : dist(p, mate->pos);
        if (prism) {
            if (!in_range || (p == here && memory.recovery_turns > 0 && !comms::support_available(world))) continue;
        }
        int target = -1;
        for (int t = 0; t < view_count; ++t) {
            const auto& v = views[t].target;
            if (!support_view(views[t].viewers, v.pos, p)) continue;
            const auto* best = target >= 0 ? &views[target].target : nullptr;
            if (!best || v.gain > best->gain || (v.gain == best->gain && v.fraction < best->fraction)
                || (v.gain == best->gain && v.fraction == best->fraction && v.ally == mate && comms::support_request(world)))
                target = t;
        }
        const float gain = target >= 0 ? views[target].target.gain : 0;
        if (willow && !ready) {
            if (p == here || !work_route || work_route->at(p) >= work_route->at(here)
                || (!in_range && dist(p, mate->pos) >= dist(here, mate->pos))) continue;
        } else if (willow && gain <= 0 && (active_clear || formation_expired
                                          || (!in_range && dist(p, mate->pos) >= dist(here, mate->pos)))) continue;
        if (!(p == here ? here_risk : support_exposure(world, safety, p)).safe()) continue;
        const int home = dist(p, world.map().ally_spawn_centre);
        if (!found || gain > best_gain || (gain == best_gain && gap < best_gap)
            || (gain == best_gain && gap == best_gap && (p == here || (best != here && home < best_home))))
            found = true, best = p, best_gain = gain, best_gap = gap, best_home = home;
    }
    if (!found) return abandon_recovery();
    const auto commit_support = [&] {
        support_owned = true;
        if (prism) {
            if (memory.recovery_start < 0) memory.recovery_start = world.round, memory.recovery_group = memory.farm_group;
            ++memory.recovery_turns;
            memory.recovery_health = health;
        } else {
            memory.claim = -1;
            memory.crew = false;
            memory.siege = false;
            if (memory.formation_start < 0) memory.formation_start = world.round;
            ++memory.formation_turns;
        }
    };
    bool healed_before = false;
    if (best != here) {
        if (willow && !here_risk.safe()) healed_before = heal_ally(world);
        world.throw_if_stale();
        if (!pathing.try_move(best)) {
            see_again(world, pathing, safety);
            abandon_recovery();
            support_retreat = support_retreat || !support_exposure(world, safety, my_position()).safe();
            return false;
        }
        commit_support();
        see_revealed(world, pathing, safety);
        if (!(willow ? exposure_here(world, safety) : support_exposure(world, safety, my_position())).safe()) {
            // The heal we stepped for costs no walk; healed_before means the cast is spent.
            if (willow && !healed_before) heal_ally(world);
            support_owned = true;
            memory.claim = -1;
            memory.crew = false;
            if (prism) close_recovery(memory, health);
            return true;
        }
    } else commit_support();
    world.throw_if_stale();
    support_owned = true;
    if (prism) {
        support_requested = true;
        decision = 'r';
        // Waiting in place spends no walk, and the tile is out of every reach: a basic attack is free.
        // Casts keep their cooldowns for the search. Only camps whose whole group cannot strike back.
        if (best == here && !attack_enemy(world) && my_can_attack())
            attack_camp(world, [&](int g) { return world.map().groups[g].strength <= 0; });
        return true;
    }
    memory.claim = -1;
    memory.crew = false;
    memory.siege = false;
    bool productive = heal_ally(world) || healed_before;
    if (best == here && support_exposure(world, safety, my_position()).safe()) {
        productive |= attack_enemy(world);
        if (my_can_attack())
            productive |= attack_camp(world, [&](int g) {
                return world.map().groups[g].strength <= 0
                       || (g == work && world.camps[g].awake != Awake::asleep);
            }) >= 0;
    }
    const bool route_progress = best != here && (work_route ? work_route->at(best) < work_route->at(here)
                                : work >= 0 && work < static_cast<int>(world.map().groups.size())
                                  && memory.farm_group == work
                                  && dist(best, world.map().groups[work].centre) < dist(here, world.map().groups[work].centre));
    if (productive || route_progress) memory.formation_start = -1, memory.formation_turns = 0;
    float offered = 0;
    support_offered = heal_ready(world, world.me(), offered) && exposure_here(world, safety).safe();
    decision = 'h';
    return true;
}

// A camp member's reach covers a tile of our spawn (a rectangle), read once.
bool camps_reach_spawn(const World& world) {
    static int known = -1;
    if (known >= 0) return known == 1;
    known = 0;
    const auto& map = world.map();
    if (map.ally_spawn_tiles.empty()) return false;
    vec2 lo = map.ally_spawn_tiles[0], hi = lo;
    for (const vec2 t : map.ally_spawn_tiles)
        lo = {std::min(lo.x, t.x), std::min(lo.y, t.y)}, hi = {std::max(hi.x, t.x), std::max(hi.y, t.y)};
    for (const auto& g : map.groups)
        for (const auto& m : g.members)
            if (std::max({lo.x - m.pos.x, m.pos.x - hi.x, lo.y - m.pos.y, m.pos.y - hi.y, 0}) <= m.reach) known = 1;
    return known == 1;
}

void decide(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    auto& me = cambc::self();
    if (!world.me().alive || bankable_bag(world, pathing) == 0 || retaining_gems(world, pathing)) memory.banking = false;
    if (!world.me().alive) {
        memory.claim = -1;
        // The crystal first: an altar only it reaches holds our bags, and shards could spend its gold.
        buy_crystal(memory);
        buy_shards(world); // the dead can only shop
        buy_lock();
        return;
    }
    // One state read covers the channels until one is cancelled; a channel excludes the others.
    const auto state = my_state();
    if (state.contains(cambc::champion_state::teleporting)) return;
    // Read again only after shopping changes our stats.
    std::optional<bool> home;
    if (state.contains(cambc::champion_state::submitting_gems) && continue_tribute(world, pathing, safety, memory, home)) return;
    if (state.contains(cambc::champion_state::recalling) && continue_recall(world, pathing, safety, memory, home)) return;
    // A ward shares the recall's channel, so this is its first chance; its sight counts this turn
    // (probe-ward-sight). Growing clusters here would starve the search: the turn end grows them.
    if (place_ward(world, memory, false)) {
        see_again(world, pathing, safety);
        home.reset();
    }

    // Shopping, heals and shields do not move us.
    const bool on_spawn = test(world.map().ally_spawn, my_position());
    if (on_spawn) buy_crystal(memory);
    if ((on_spawn || world.me().facts().passive == Passive::remote_shop) && buy_shards(world)) home.reset();
    if (on_spawn) buy_lock();
    if (!world.me().can_act(world.round)) return;
    if (const auto* ender = game_ender(world)) {
        stop_game_ender(world, pathing, memory, *ender);
        return;
    }
    const bool willow = world.me().type == cambc::champion_type::willow;
    const bool prism = world.me().type == cambc::champion_type::prism;
    // Healing needs a turn end on spawn; a recall arrives at turn start.
    // Not under an awake camp: it hits us every round, so we would mend forever while it stays awake.
    const bool mend = on_spawn && my_health() < my_max_health() && !(camps_reach_spawn(world) && safety.camp_damage(my_position()) > 0);
    const bool leave = !mend && (home ? *home : want_home(world, pathing, safety, memory));
    // Willow at work heals first, and the work goes on without the strike search.
    const bool working = willow && !mend && !leave && support_work(world, pathing, safety, memory);
    const bool strikes = !working && strike_possible(world);
    bool mate_eligible = false;
    if (!mend && (prism || (willow && !leave && !working))
        && support_endpoint(world, willow ? cambc::champion_type::prism : cambc::champion_type::willow)
        && local_support(world, pathing, safety, memory, leave, mate_eligible))
        return;
    if (willow && !mend && !leave && !strikes && !stunned_turn && !working && !mate_eligible && !support_retreat
        && willow_independent_heal_step(world, pathing, safety))
        return;
    if (support_retreat) {
        heal_ally(world);
        retreat(world, pathing, safety, memory);
        return;
    }
    // On the turns the search plans, it weighs heals and shields against its other casts.
    if (!strikes || mend || leave) {
        heal_ally(world);
        if (!strikes || !(reset_may_kill(world) || landing_ready(world))) shield_if_needed(world, safety, memory.claim);
    }
    if (mend) {
        decision = 'H';
        const bool attacked = attack_enemy(world);
        if (attacked) reset_and_attack_enemy(world, true);
        cast_at_enemies(world);
        if (attacked) reset_and_attack_enemy(world);
        return;
    }
    if (leave) {
        retreat(world, pathing, safety, memory);
        return;
    }

    guard_steps(world, pathing, safety);
    if (yield_capture(world, pathing, safety, memory)) return;
    if (take_capture_handoff(world, pathing, safety, memory)) return;
    const bool contested = contesting(world);
    const bool holding = holding_capture(world, pathing) || contested;
    bool attacked = false;
    if (strikes) {
        Intent intent;
        intent.anchored = holding;
        // Both sides on its tiles, only a fight ends a contest: we may close in without stepping off.
        if (contested) intent.hold = &world.map().groups[world.map().group_at(my_position())].tiles();
        intent.walks = !holding && (retaining_gems(world, pathing) || !can_tribute_here(world));
        // A carrier's step banks a turn sooner, freeing a turn of output for the farm.
        intent.step_value = farm_step_value(world);
        // An enemy already in attack range was not worth leaving (want_home): the fight is here.
        if (enemy_within(world, my_position(), world.me().facts().attack_range())) intent.walks = false;
        // The goal most likely walks to an altar when carrying, else to the farm choice.
        intent.to_altar = bankable_bag(world, pathing) > 0 && !retaining_gems(world, pathing);
        intent.group = memory.farm_group;
        struck = true;
        const auto planned = plan_strikes(world, pathing, safety, intent);
        attacked = planned.attacked;
        searched = planned.searched;
        searched_at = my_position();
        searched_hit = !my_can_attack();
        if (!searched) heal_ally(world);
        // The search priced nothing against an enemy its own moves revealed.
        if (see_revealed(world, pathing, safety)) searched = false;
        // A cast the search left priced the shield at nothing, blind to the goal's coming camp hit:
        // judged here, before farm's camp reset or dash takes it.
        shield_if_needed(world, safety, memory.claim);
    }
    decision = holding ? 'P' : attacked ? 'A' : decision;
    if (!me.is_alive()) return;
    if (!my_can_attack() || !my_can_cast()) see_stuns(world, safety), safety.refresh();
    // The guard was placed around the tile we started on: the goal steps from where the search left us.
    if (my_position() != world.me().pos && (my_can_move() || my_can_cast())) guard_steps(world, pathing, safety);
    if (holding) {
        hold_capture(world, memory, attacked);
        return;
    }
    if (bankable_bag(world, pathing) > 0 && !retaining_gems(world, pathing)) {
        carry_bag(world, pathing, safety, memory, attacked);
        return;
    }
    if (attacked && !world.me().facts().walk_and_attack_independent()) return;
    if (wants_shop(world, pathing, safety, memory)) {
        decision = 'S';
        memory.claim = -1;
        step_safely(world, pathing, pathing.to_ally_spawn(), safety);
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
// turn shorter. Damage before then cancels it at no cost. A stunned champion cannot start one:
// the engine refuses it, and the thrown error costs ~3.9k fuel.
void start_recall(const World& world) {
    auto& me = cambc::self();
    if (stunned_turn || !world.me().alive || channelling()) return;
    // Ren's reflected damage can kill us in our own turn: dead, we read as off the map.
    const vec2 here = my_position();
    if (here.x < 0 || test(world.map().ally_spawn, here)) return;
    throw_if_stale();
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
    if (!world.me().alive || channelling() || g < 0 || g >= static_cast<int>(world.camps.size())
        || (world.map().any_group_hop() && beyond_walk(world, pathing, g)))
        return;
    pathing.prepare_approach(g, walk_range(world, g), fuel_floor);
}

void prepare_next_turn(const World& world, Pathing& pathing, const Memory& memory) {
    prepare_walk(world, pathing, memory, end_reserve);
}

// From our state at the turn's end: a cast restarted its slot's cooldown, and the basic attack was
// spent unless a ranged walk spent it, a reset adding one (it restores only a spent attack).
void count_use(const World& world, vec2 start, bool could_attack) {
    if (!world.me().alive) return;
    const auto& f = world.me().facts();
    bool dashed = false;
    int resets = 0;
    for (int s = 0; s < 2; ++s) {
        std::int32_t cooldown = 0;
        ok(cambc::detail::sdk_champion_cooldown(my_handle(), static_cast<std::uint32_t>(s), &cooldown));
        if (cooldown < ability_cooldown) continue;
        ++use.casts[s];
        dashed |= f.abilities[s].kind == AbilityKind::dash;
        resets += f.abilities[s].kind == AbilityKind::attack_reset;
    }
    const bool walked = !f.walk_and_attack_independent() && my_position() != start && !dashed;
    use.attacks += std::max(0, (could_attack && !my_can_attack()) + resets - walked);
}

// The turn's walk, hits and casts, and the free actions that end it.
void act(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    const vec2 start = world.me().pos;
    const bool could_attack = my_can_attack();
    prepare_walk(world, pathing, memory, walk_first_floor);
    const int claim = memory.claim;
    decide(world, pathing, safety, memory);
    if (decision != 'W') memory.wait_altar = -1;
    // A turn without siege() (a fight, a heal) keeps the siege while our claim stays on it; a chase
    // or a bag takes us away from it.
    if (!sieged && (memory.claim != claim || decision == 'C' || (bankable_bag(world, pathing) > 0 && !retaining_gems(world, pathing)))) {
        memory.siege = false;
        memory.staged_since = -1;
    }
    if (world.me().alive && see_revealed(world, pathing, safety)) searched = false;
    if (!support_owned && strike_after(world, pathing, safety).searched)
        searched = true, searched_at = my_position(), searched_hit = !my_can_attack();
    pathing.set_guard(nullptr);
    if constexpr (debug_fights)
        if (world.me().alive && !test(world.map().ally_spawn, start) && fuel_ok(end_reserve + 15000))
            if (const auto t = safety.fight(start); t.enemies > 0) log_fight("FF", world, safety, start, t);
    // The search priced heal and shield where its plan ended, not a later walk or hit by the goal.
    if (!support_owned && (!searched || my_position() != searched_at || !my_can_attack() != searched_hit)) {
        heal_ally(world); // allies in reach after walking
        shield_if_needed(world, safety, memory.claim);
    }
    end_ward = place_ward(world, memory); // where we end the turn
    place_lock(world);
    if (!support_owned) start_recall(world);
    count_use(world, start, could_attack);
}

void play_turn(World& world, Pathing& pathing, Memory& memory) {
    Safety safety{world};
    const int live_claim = world.me().facts().has_dash() && memory.claim >= 0
                               && memory.claim < static_cast<int>(world.camps.size())
                               && world.camps[memory.claim].state == CampState::alive
                               && world.camps[memory.claim].state_round == world.round
                               ? memory.claim : -1;
    const auto* record = world.me().alive ? &my_record() : nullptr;
    const float health = record ? record->health : 0;
    memory.damage = memory.round == world.round - 1 ? std::max(0.0f, memory.health - health) : 0;
    decision = '-';
    sieged = false;
    searched = false;
    struck = false;
    support_owned = support_requested = support_offered = support_retreat = end_ward = false;
    comms::support_intent(world.round, false);
    siege_group() = -1;
    const int camp_hits_before = camp_hits();
    if (world.me().alive) note_upkeep(world, safety, memory.damage);
    stunned_turn = record && my_stunned(cambc::champion_state::from_bits_retain(record->state));
    // A failed act still posts the claim, the bag and the health that next turn's damage reads.
    try {
        act(world, pathing, safety, memory);
    } catch (const std::exception& e) {
        std::printf("r%u act error: %s\n", cambc::round_number(), e.what());
    }
    // Not StaleTurn: a stale turn abandons the rest.
    try {
        if (!world.is_stale()) see_stuns(world, safety);
        set_turn_order(world, safety);
    } catch (const std::exception& e) {
        std::printf("r%u turn order error: %s\n", cambc::round_number(), e.what());
    }
    if (!world.is_stale() && world.me().alive) {
        bool intent = support_requested;
        // support_offered was judged in the vision we had: a ward since may show a threat.
        if (world.me().facts().heals() && support_offered) {
            intent = true;
            if (end_ward) {
                see_again(world, pathing, safety);
                float amount = 0;
                intent = heal_ready(world, world.me(), amount) && exposure_here(world, safety).safe();
            }
        }
        world.throw_if_stale();
        comms::support_intent(world.round, intent);
    }
    if (world.me().alive && world.me().facts().heals()
        && ((!support_owned && camp_hits() != camp_hits_before) || my_cooldown(world.me().facts().slot_of(AbilityKind::heal)) >= ability_cooldown))
        memory.formation_start = -1, memory.formation_turns = 0;
    comms::claim(memory.claim);
    comms::bag(world.me().alive ? static_cast<int>(my_gems()) : 0);
    if (!world.is_stale()) publish_turn_order(world, comms::priority_payload(world));
    memory.live_claim = live_claim;
    memory.round = world.round;
    memory.health = world.me().alive ? my_health() : 0;
    upkeep.camp_turns += camp_hits() != camp_hits_before;
    debug_block({ std::printf("D %d %u %c %d %d\n", world.round, static_cast<std::uint32_t>(world.me().handle), decision, memory.farm_group, memory.claim); });
}

} // namespace aph
