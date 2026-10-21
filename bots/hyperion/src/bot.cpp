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
#include <vector>
#include "abilities.h"
#include "comms.h"
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
// PREY-FLIP and PURSUIT-SKIP-MISMATCH re-run the rule they replaced. The re-runs fill Safety's memos
// and Reach and spend fuel, so games change while this is on.
constexpr bool debug_verdicts = false;

// The turn's branch, for debug_fights: Chase, Attack, Retreat, Farm, Bank, Wait at an altar,
// Tribute kept / t cancelled, recall Kept / k cancelled, Healing on spawn, Shopping trip,
// holding (P), capture recall (Q), siege or kite of a big group (G), contest (X),
// stopping a game-ending bag (E).
char decision = '-';
bool sieged = false; // siege() ran this turn
bool stunned_turn = false; // stunned at this turn's start
bool searched = false; // the strike search chose this turn's cast, heals and shields included
vec2 searched_at{};      // where the search's plan ended, and whether it had attacked by then
bool searched_hit = false;
// Debug only (WANTHOME): want_home's runs this decide, less the answers a ward or shards discarded.
int home_asks = 0;

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

enum Family { monster, power, durability, treasure, jungle, home, bruiser };
enum StatKind { strength_stat, focus_stat, health_stat };

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
        if (me.can_buy(cambc::consumable_type::altar_lock)) me.buy(cambc::consumable_type::altar_lock);
    } catch (const cambc::error&) {
    }
}

bool carries_crystal() { return cambc::self().consumables()[cambc::consumable_type::tp_crystal].count() > 0; }

// Once a hop to an altar only a crystal reaches (StaticMap::hops) would have beaten walking to bank.
void buy_crystal(const Memory& memory) {
    if (!memory.wants_crystal) return;
    auto& me = cambc::self();
    try {
        if (me.can_buy(cambc::consumable_type::tp_crystal)) me.buy(cambc::consumable_type::tp_crystal);
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

[[gnu::flatten]] void place_lock(const World& world) {
    Phase phase{"place_lock"};
    auto& me = cambc::self();
    if (stunned_turn || !world.me().alive) return;
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

bool attack_enemy(const World& world) {
    auto& me = cambc::self();
    if (!my_can_attack()) return false;
    const auto target = attack_target(world);
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
    Phase phase{"attack_camp"};
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
            const float hp = health[i] > 0 ? health[i] : members[i].max_health;
            float score = members[i].strength / std::max(1.0f, hp);
            if (splash) {
                int near = 0;
                for (int j = 0; j < static_cast<int>(members.size()); ++j)
                    near += j != i && health[j] > 0 && dist(members[i].pos, members[j].pos) <= 1;
                score += static_cast<float>(near);
            }
            if (n < static_cast<int>(found.size())) found[n++] = {g, i, score};
        }
    }
    std::stable_sort(found.begin(), found.begin() + n, [](const Candidate& a, const Candidate& b) { return a.score > b.score; });
    for (int k = 0; k < n; ++k) {
        try {
            me.attack(map.groups[found[k].group].camp(found[k].member));
            ++camp_hits();
            return found[k].group;
        } catch (const cambc::error&) {
        }
    }
    return -1;
}

// Storage left unwritten until used: vec2 and std::pair initialise their members.
template <typename T, std::size_t N> union Unwritten {
    Unwritten() {}
    std::array<T, N> a;
};

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

float escape_cost(Safety& safety, vec2 q) { return safety.escape_cost(q); }

// Out of the camps' reach first, along the cheapest neighbour: walking home past an awake camp
// takes a hit every step, while a recall started outside its reach goes home untouched.
bool flee_camps(const World&, Pathing& pathing, Safety& safety, const Field& home) {
    if (!my_can_move()) return false;
    const vec2 here = my_position();
    if (safety.camp_damage(here) <= 0) return false;
    const auto& blocked = pathing.blocked(); // walls included
    std::optional<vec2> best;
    float best_damage = escape_cost(safety, here);
    int best_home = home.at(here);
    for (auto d : directions) {
        const vec2 p = here + d;
        if (!in_bounds(p) || test(blocked, p)) continue;
        const float damage = escape_cost(safety, p);
        const int steps = home.at(p);
        if (damage < best_damage || (damage == best_damage && steps < best_home)) best = p, best_damage = damage, best_home = steps;
    }
    return best && pathing.try_move(*best);
}

// Inside danger a route home is only the shortest walk, ties in compass order, which can lead
// along the enemies we flee: take the homeward step that costs least (escape_cost), then the
// nearest home, then the farthest from them. A sideways step goes first only when it costs less.
void retreat_step(const World& world, Pathing& pathing, Safety& safety, const Field& home) {
    if (!my_can_move()) return;
    const vec2 here = my_position();
    if (!safety.avoid_within(here, vision_radius)) {
        pathing.step_towards(home);
        return;
    }
    const auto avoid = safety.avoid();
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
    for (auto d : directions) {
        const vec2 p = here + d;
        if (!in_bounds(p) || test(blocked, p)) continue;
        const int s = home.at(p);
        if (s == unreachable || s > steps) continue;
        int gap = unreachable;
        for (const auto& e : world.enemies)
            if (e.alive && e.visible) gap = std::min(gap, dist(p, e.pos));
        options[n++] = {p, escape_cost(safety, p), s, gap};
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
    std::uint32_t camps_version = 0;
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
    Phase phase{"altar_access"};
    static AltarAccess a;
    if (a.version > 0 && a.camps_version == world.camps_version) return a;
    a.camps_version = world.camps_version;
    const auto& live = pathing.live_camps();
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
    if (a.version == 1) {
        clear_board(tributes);
        for (const auto& t : map.altars) tributes |= t.tribute_tiles();
    }
    copy_into(tributes, a.opened);
    if (!walked) {
        or_into(pathing.static_walls(), live, walls);
        walls.reachable_tiles_into(map.ally_spawn_tiles[0], unreachable, ours);
    }
    // open = tributes off live camps, but for those the static walk reaches and this one does not
    copy_into(a.opened, a.open);
    drop(a.open, live);
    copy_into(pathing.foot(), area);
    drop(area, ours);
    drop(a.open, area);
    a.any_open = !a.open.is_empty();
    if (a.any_open) {
        copy_into(a.open, a.opened);
        return a;
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
                    if (dist(m.pos, altar.pos) <= m.reach + 1) near[g] = 1;
        }
        if (near[g]) stirring.push_back(g);
    });
    for (const vec2 t : a.open.positions()) {
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
    return a.any_open && camp_hit_factor() * access_fire(world, a) * static_cast<float>(tribute_turns(bag)) < health;
}

// The bag a tribute could score: one no altar is usable for is held back, and we farm and shop as
// if empty-handed.
int bankable_bag(const World& world, Pathing& pathing) {
    Phase phase{"bankable_bag"};
    const int bag = static_cast<int>(my_gems());
    return bag > 0 && altar_usable(world, pathing, bag, my_health()) ? bag : 0;
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
// the team's bags (posted through comms): our bag banked later than that only delays the win.
int race_left(const World& world) {
    int short_by = gems_short(world);
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && !(a.visible && a.channel == Channel::tribute))
            short_by -= comms::bag_of(world, a.index);
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
    const int walk = pathing.to_any_altar().at(my_position());
    return bag_rounds_left(world) <= (walk == unreachable ? 0 : walk) + tribute_turns(my_gems()) + endgame_margin;
}

// A tribute started or kept now is the bag's last chance to score, or wins the game while fleeing
// gives the enemy time to win first: take it at any risk.
bool any_risk(const World& world, int channel_turns) {
    return winning_bag(world) || rounds_left(world) <= channel_turns + endgame_slack;
}

bool tribute_ok(const World& world, Safety& safety, const Memory& memory, int turns) {
    return any_risk(world, turns) || tribute_safe(safety, memory, turns);
}

bool place_ward(const World& world, Memory& memory, bool grow = true);

// At an unlocked altar in reach. The caller judged the turn's start tile safe; anywhere else, or at
// an altar carry_bag gave up waiting at, is judged again.
bool submit_here(const World& world, Safety& safety, Memory& memory) {
    auto& me = cambc::self();
    const vec2 here = my_position();
    const auto& altars = world.map().altars;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
        if (world.altars[a].enemy_lock || dist(here, altars[a].pos) > cambc::constants::submit_gems_range) continue;
        const bool avoided = a == memory.avoid_altar && world.round < memory.avoid_until;
        if ((avoided || here != world.me().pos) && !tribute_ok(world, safety, memory, tribute_turns(my_gems()))) return false;
        place_lock(world); // first: it cancels every tribute at its altar
        place_ward(world, memory); // first: no ward goes down while channelling
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
// the nearest landing and the recall out, as no walk leaves the pocket.
struct HopRoute {
    int hop = -1;
    int steps = unreachable;
};
HopRoute hop_route(const World& world, Pathing& pathing, const Memory& memory) {
    HopRoute best;
    const auto& map = world.map();
    const vec2 here = my_position();
    if (map.hops().empty() || !test(pathing.foot(), here)) return best;
    for (int h = 0; h < static_cast<int>(map.hops().size()); ++h) {
        const int a = map.hops()[h].altar;
        if (world.altars[a].enemy_lock || (a == memory.avoid_altar && world.round < memory.avoid_until)) continue;
        const int walk = pathing.to_hop(h).at(here), inner = pathing.hop_landing_steps(h);
        if (walk == unreachable || inner == unreachable) continue;
        if (const int steps = walk + cambc::constants::tp_crystal_time + inner + recall_turns(world); steps < best.steps)
            best = {h, steps};
    }
    return best;
}

// Towards the hop's sources; on one, the crystal to the free landing nearest its altar, the least
// dangerous on ties. The channel is judged as a tribute's (death cancels it, a camp kill takes the
// bag), and a stun cancels it after the crystal is spent.
void take_hop(const World& world, Pathing& pathing, Safety& safety, const Memory& memory, int h) {
    const auto& hop = world.map().hops()[h];
    const vec2 here = my_position();
    if (test(hop.sources, here)) {
        const bool stun = world.me().facts().passive != Passive::stun_immune && safety.tile(here).stun_mask != 0;
        const bool safe = !stun && tribute_ok(world, safety, memory, cambc::constants::tp_crystal_time);
        vec2 best{-1, -1};
        float best_worst = 0;
        if (safe) {
            auto targets = pathing.teleport_targets();
            targets &= hop.landings;
            const auto& field = pathing.to_altar(hop.altar);
            int best_steps = unreachable;
            for (const vec2 l : targets.positions()) {
                const int s = field.at(l);
                if (s == unreachable || s > best_steps) continue;
                const float worst = safety.tile(l).worst();
                if (s < best_steps || worst < best_worst) best = l, best_steps = s, best_worst = worst;
            }
        }
        debug_block({ std::printf("HOP %d %d %d %d %d %.0f\n", world.round, safe ? 1 : 0, stun ? 1 : 0, best.x, best.y, best_worst); });
        if (best.x >= 0) {
            try {
                if (cambc::self().consumables()[cambc::consumable_type::tp_crystal].use(best)) return;
            } catch (const cambc::error&) {
            }
        }
    }
    step_safely(pathing, pathing.to_hop(h), safety);
}

[[gnu::flatten]] void bank_gems(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    Phase phase{"bank_gems"};
    world.throw_if_stale();
    if (submit_here(world, safety, memory)) return;
    const vec2 here = my_position();
    const auto& altars = world.map().altars;
    // A pack we would retreat from stands in the way: around it within the usual detour, else
    // wait outside it until it leaves or a recall (recall_to_bank) takes the bag home.
    if (const auto* zone = pack_zone(world)) {
        if (pathing.step_towards(pathing.to_any_altar(), zone)) submit_here(world, safety, memory);
        return;
    }
    // One we gave up waiting at (carry_bag) counts as locked until we could reach another.
    const auto avoided = [&](int a) { return a == memory.avoid_altar && world.round < memory.avoid_until; };
    bool any_locked = false;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) any_locked |= world.altars[a].enemy_lock || avoided(a);
    // One cached field covers every altar; per-altar fields are needed only to skip locked ones.
    // Breaking a lock takes a turn per hit left, about a step each.
    int best = -1, best_steps = unreachable;
    const bool skipping = any_locked;
    if (any_locked) {
        for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
            // A tribute tile is within 1 of its altar: an altar this rules out needs no field.
            if (avoided(a) || dist(here, altars[a].pos) - 1 >= best_steps) continue;
            const auto& belief = world.altars[a];
            int steps = pathing.to_altar(a).at(here);
            if (steps == unreachable) continue;
            if (belief.enemy_lock) steps += belief.enemy_lock_hits > 0 ? belief.enemy_lock_hits : static_cast<int>(cambc::constants::altar_lock_hits);
            if (steps < best_steps) best = a, best_steps = steps;
        }
        any_locked = best >= 0;
    }
    // Every altar a walk reaches avoided: only a hop is left.
    const int walk_steps = any_locked ? best_steps : skipping ? unreachable : pathing.to_any_altar().at(here);
    if (const auto hop = hop_route(world, pathing, memory); hop.hop >= 0 && hop.steps < walk_steps) {
        memory.wants_crystal = true;
        if (carries_crystal()) {
            take_hop(world, pathing, safety, memory, hop.hop);
            return;
        }
    }
    const Field& field = any_locked ? pathing.to_altar(best) : pathing.to_any_altar();
    if ((dash_across(world, pathing, field) || dash_towards(world, pathing, field)) && submit_here(world, safety, memory)) return;
    if (any_locked && world.altars[best].enemy_lock && break_lock(world, best) && !world.me().facts().walk_and_attack_independent())
        return;
    step_safely(pathing, field, safety);
    submit_here(world, safety, memory);
}

// Damage a turn, spells (and dash landings) spread over their cooldown.
float raw_output(const ChampionFacts& f, float strength, float focus) {
    float damage = strength;
    for (const auto& a : f.abilities) {
        if (a.kind == AbilityKind::damage || a.lands()) damage += a.multiplier * focus / static_cast<float>(ability_cooldown);
        if (a.kind == AbilityKind::attack_reset) damage += strength / static_cast<float>(ability_cooldown);
    }
    return damage;
}

float output(const ChampionBelief& c) { return raw_output(c.facts(), c.strength, c.focus) * c.damage_scale(); }

// output(), at least 1: a divisor for clear times.
float floored_output(const ChampionBelief& c) { return std::max(1.0f, output(c)); }

bool has_family(const cambc::enum_map<cambc::item_type>& owned, int family) {
    return owned[emblem_of(family, strength_stat)] + owned[emblem_of(family, focus_stat)] + owned[emblem_of(family, health_stat)] > 0;
}

} // namespace

float camp_hit_factor() {
    const auto& owned = my_items();
    return (has_family(owned, jungle) ? 0.7f : 1.0f) * (has_family(owned, durability) ? 0.9f : 1.0f);
}

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
    return worth / (rounds * (1.0f + rounds / horizon));
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
    if (n > 1) std::sort(left, left + n, [](const Left& a, const Left& b) { return a.strength * b.health > b.strength * a.health; });
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
    // Static storage starts filled for free, where a vector pays to fill its slots.
    static std::array<Slots, 256> cache;
    if (static_cast<std::size_t>(g) >= cache.size()) return min_camp_damage(group, belief, strength, rounds, reflect);
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
    struct Kept {
        float weight = -1; // until read
    };
    static std::array<Kept, 256> cache;
    float uncached = -1;
    auto& weight = static_cast<std::size_t>(g) < cache.size() ? cache[g].weight : uncached;
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
    Phase phase{"fastest_clear"};
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
// What hit us since our last turn, for Safety (W4-C: the part no visible enemy or camp explains).
void note_hits(const World&, Safety& safety, const Memory& memory) { safety.note_taken(memory.damage); }

void note_upkeep(const World& world, Safety& safety, float damage) {
    Phase phase{"note_upkeep"};
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

// A Jungle, Power or Durability shard short of its emblem.
bool emblem_begun() {
    const auto& owned = my_items();
    for (const int family : {jungle, power, durability})
        for (int stat = strength_stat; stat <= health_stat; ++stat)
            if (owned[shard_of(family, stat)] > 0) return true;
    return false;
}

// Our stats and the share of camp damage (Jungle) and of all damage (Durability) we take.
struct Build {
    float strength = 0, focus = 0, max_health = 0, camp_taken = 1, taken = 1;
};

void add_shards(Build& b, const ChampionFacts& f, int stat, float shards) {
    if (stat == strength_stat) b.strength += shards * f.strength.growth;
    if (stat == focus_stat) b.focus += shards * f.focus.growth;
    if (stat == health_stat) {
        b.max_health += shards * f.health.growth;
        if (f.passive == Passive::health_strength) b.strength += 0.01f * shards * f.health.growth;
    }
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
    const float clear = (others + out(now)) / (others + out(b));
    const float camp = upkeep.camp_taken / turns * clear * b.camp_taken / now.camp_taken;
    const float taken = (camp + upkeep.champ_taken / turns) * b.taken / now.taken;
    const float usable = b.max_health * (1.0f - params::recall_health_fraction);
    // Counted from one clearing turn in one: before our first camp hit, gold (priced by this
    // saving) is still worth farming.
    const float clearing = static_cast<float>(upkeep.camp_turns + 1) / static_cast<float>(upkeep.turns + 1);
    return clearing * clear + taken * static_cast<float>(recall_turns(world) + steps) / usable;
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
// `bought`: the stats of shards bought since the turn's start.
Emblem best_emblem(const World& world, const Build& bought = {}) {
    const auto& f = world.me().facts();
    const auto& owned = my_items();
    const auto& self = world.me();
    const Build now{self.strength + bought.strength, self.focus + bought.focus, self.max_health + bought.max_health,
                    has_family(owned, jungle) ? 0.7f : 1.0f, has_family(owned, durability) ? 0.9f : 1.0f};
    float others = 0;
    const Upkeep u = world.map().monolith_only && upkeep.camp_taken <= 0 ? siege_upkeep(world, others) : upkeep;
    const float base = upkeep_cost(world, u, others, now, now);
    const auto value = [&](int family, int stat) __attribute__((always_inline)) -> Emblem {
        const unsigned left = 5 - owned[shard_of(family, stat)];
        Build b = now;
        add_shards(b, f, stat, static_cast<float>(left + (family == power)));
        if (family == jungle) b.camp_taken = 0.7f;
        if (family == durability) b.taken = 0.9f;
        return {family, stat, base - upkeep_cost(world, u, others, now, b), left * shard_price};
    };
    // In the stat it was begun in: the main stat follows our use and can change.
    const int begun[5][2] = {{jungle, strength_stat}, {jungle, focus_stat}, {power, strength_stat}, {power, focus_stat}, {durability, health_stat}};
    for (const auto& [family, stat] : begun)
        if (owned[shard_of(family, stat)] > 0) return value(family, stat);
    const int main = main_stat(world);
    Emblem best = value(power, main);
    if (const auto e = value(jungle, main); e.saved > best.saved) best = e;
    if (const auto e = value(durability, health_stat); e.saved > best.saved) best = e;
    return best;
}

// True if any shard was bought.
bool buy_shards(const World& world) {
    Phase phase{"buy_shards"};
    unsigned gold = my_gold();
    if (gold < shard_price) return false;
    const unsigned start = gold;
    Build bought;
    while (gold >= shard_price) {
        const auto [family, stat, saved, cost] = best_emblem(world, bought);
        const unsigned have = my_items()[shard_of(family, stat)];
        const unsigned count = std::min<unsigned>(5 - have, gold / shard_price);
        if (!buy(shard_of(family, stat), count)) break;
        gold -= shard_price * count;
        add_shards(bought, world.me().facts(), stat, static_cast<float>(count + (family == power && have + count == 5)));
    }
    return gold < start;
}

// The next emblem (best_emblem), the rounds it saves us over our share of the gems still to farm,
// and the gems a gold is worth (its part of that saving). Kept while our share and stats hold: the
// upkeep counters under them move every turn, and every farm value would be rebuilt.
struct Prices {
    Emblem next;
    float gain, per_gold;
};
const Prices& prices(const World& world) {
    Phase phase{"prices"};
    struct Key {
        float share, strength, focus, max_health;
        int main;
        bool operator==(const Key&) const = default;
    };
    static Key last{-1};
    static Prices kept;
    const auto& self = world.me();
    if (const Key now{gems_share(world), self.strength, self.focus, self.max_health, main_stat(world)}; !(now == last)) {
        last = now;
        kept.next = best_emblem(world);
        kept.gain = now.share * kept.next.saved * rounds_per_gem;
        kept.per_gold = now.share * kept.next.saved / static_cast<float>(std::max(1u, kept.next.cost));
    }
    return kept;
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
    Phase phase{"home_trip"};
    HomeTrip t{channel, pathing.to_any_altar().at(world.map().ally_spawn_centre), my_health() < my_max_health() ? 1 : 0,
               bag_rounds_left(world) - tribute_turns(my_gems())};
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

// Split until each share's tribute fits the window its safety is judged over (tribute_safe).
int holders(const CampGroup& G) {
    if (G.has_monolith) return params::monolith_holders;
    int n = 1;
    while (n < params::big_holders && tribute_turns((G.gems + n - 1) / n) > params::tribute_window) ++n;
    return n;
}

// On a cleared group's tile that no lower-id ally also holds, with no enemy on any of its tiles:
// stepping off loses the capture's progress, and it pays within six rounds.
bool holding_capture(const World& world) {
    Phase phase{"holding_capture"};
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
    Phase phase{"attack_tiles"};
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
    if (allies_on(world, G.tiles()) >= holders(G)) return false;
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

// Farm's spell clear (spell_clear_rounds): from a tile within ability range of a live attacker of
// the group but out of every attacker's reach, casting at the attackers, with basic attacks on
// what cannot hit back. False with no such tile or way to one, for the usual approach.
bool spell_clear(const World& world, Pathing& pathing, int g, const bitboard* zone, int cap) {
    Phase phase{"spell_clear"};
    const auto& G = world.map().groups[g];
    const auto& c = world.camps[g];
    static bitboard reach{cambc::uninitialized}, goals{cambc::uninitialized};
    reach.clear();
    std::uint32_t attackers = 0;
    for (std::size_t i = 0; i < G.members.size() && i < 32; ++i)
        if (c.health[i] > 0 && G.members[i].strength > 0) {
            attackers |= 1u << i;
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
        cast_at_camp(world, pathing, g, true);
        attack_camp(world, [&](int h) { return h == g || world.map().groups[h].strength <= 0; });
        reset_and_attack_camp(world, pathing.safety(), g);
    };
    if (test(goals, my_position())) {
        hit();
        return true;
    }
    if (zone) reach |= *zone;
    if (!pathing.step_towards(goals, &reach, cap)) return false;
    if (!test(reach, my_position())) hit();
    return true;
}

// Chebyshev steps from p to the group's nearest camp tile.
int steps_to(const CampGroup& G, vec2 p) {
    int steps = unreachable;
    for (const auto& m : G.members) steps = std::min(steps, dist(p, m.pos));
    return steps;
}

// Safety's fights leave out the claimed group's camp hits, which the farm budgets: a claim made
// mid-turn reaches it before the walk asks guarded().
int set_claim(Memory& memory, const Pathing& pathing, int g) {
    memory.claim = g;
    if (auto* safety = pathing.safety()) safety->set_claimed(g);
    return g;
}

// A claim outside farm and siege.
void write_claim(Memory& memory, const Pathing& pathing, int g) { set_claim(memory, pathing, g); }

// Our farm choice or claim, cleared this turn and short of holders, goes to the nearest of the
// allies in sight claiming it (ties to the lower index), so the others move on rather than split
// the share. Before anything else farm does, since a ranged hit in passing would cost the step.
bool pick_up(const World& world, Pathing& pathing, Memory& memory) {
    Phase phase{"pick_up"};
    if (!my_can_move() || memory.banking) return false;
    const auto& map = world.map();
    const vec2 here = my_position();
    for (const int g : {memory.farm_group, memory.claim}) {
        if (g < 0 || g >= static_cast<int>(map.groups.size())) continue;
        const auto& G = map.groups[g];
        const auto& c = world.camps[g];
        if (c.state != CampState::cleared || c.state_round != world.round || G.has_monolith || G.gems + G.gold == 0
            || test(G.tiles(), here) || allies_on(world, G.tiles()) >= holders(G) || enemy_on(world, G.tiles()))
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
        memory.farm_group = set_claim(memory, pathing, g);
        memory.crew = false;
        return pathing.step_towards(G.tiles(), nullptr, steps + max_detour);
    }
    return false;
}

// Carrying gems, farming on chains a capture onto the bag: it saves the walk to the altar and
// back but keeps the bag at risk for longer. It goes ahead only if the next group, by the time it
// adds to the trip, beats the best cycle starting from the altar; false means bank instead.
[[gnu::flatten]] bool farm(const World& world, Pathing& pathing, Memory& memory) {
    Phase phase{"farm"};
    world.throw_if_stale();
    if (pick_up(world, pathing, memory)) return true;
    const auto& map = world.map();
    const auto& groups = map.groups;
    const int range = world.me().facts().attack_range();
    const float strength = floored_output(world.me()), soften = camp_hit_factor(), reflect = world.me().retaliation();
    const float max_health = my_max_health();
    const float spare_health = (my_health() - params::recall_health_fraction * max_health) / params::camp_risk;
    const int bag = bankable_bag(world, pathing);
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
    const auto attack_in_range = [&]() __attribute__((always_inline)) {
        Phase step{"hit"};
        const int hit = attack_camp(world, passing);
        if (hit >= 0 && hit != memory.claim) {
            memory.crew = taken(hit);
            set_claim(memory, pathing, hit);
        }
        // Our hit cleared the group: a melee walk onto its tile starts the capture a round sooner.
        if (hit >= 0 && melee && step_onto_cleared(world, pathing, hit)) {
            memory.farm_group = hit;
            return true;
        }
        if (hit < 0 || melee) return false; // walk on
        cast_at_camp(world, pathing, hit);
        reset_and_attack_camp(world, pathing.safety(), hit);
        return true;
    };
    if (bag == 0 && attack_in_range()) return true;
    if (world.is_stale()) return true;

    // Holders keep a capture going, and more only split the reward.
    const auto ally_holding = [&](int g) __attribute__((always_inline)) { return allies_on(world, groups[g].tiles()) >= holders(groups[g]); };

    const vec2 here = my_position();
    if (holding_capture(world)) return true;
    // Carrying, whatever made us retreat stays out of bounds: we route around it or wait outside
    // it rather than step in to be sent back out. Empty-handed, a step in risks nothing (the zone
    // starts beyond any strike's reach) and keeps us at hand for when the pack moves on.
    const auto* zone = bag_at_stake(world) > 0 ? pack_zone(world) : nullptr;

    // Short of fuel, walk on towards the last choice rather than run out mid-turn. Static fields
    // are kept, so after the first walk to a group this costs a descent.
    const int previous = memory.farm_group;
    const auto walk_on = [&](int g) __attribute__((always_inline)) {
        Phase step{"walk_on"};
        if (g < 0) return false;
        // Descending it walks around walls and live camps; a live route only helps past allies.
        const auto walk = [&](const Field& field) __attribute__((always_inline)) {
            return dash_across(world, pathing, field) || pathing.descend(field, zone) || pathing.step_towards(field, zone);
        };
        if (const auto* field = pathing.prepare_approach(g, walk_range(world, g), end_reserve)) return walk(*field);
        // Too short of fuel to search the way to a new choice: last turn's, whose way is known.
        if (previous >= 0 && previous != g && pathing.approach_ready(previous, walk_range(world, previous))) {
            note_shortcut("farm-kept-target");
            memory.farm_group = set_claim(memory, pathing, previous);
            memory.crew = false;
            return walk(*pathing.approach(previous, walk_range(world, previous)));
        }
        if (const auto* centre = pathing.from_centre(g)) return pathing.descend(*centre, zone);
        note_shortcut("crow-flies-farm");
        return pathing.step_closer(groups[g].centre, zone);
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
    const Field* to_altar = bag > 0 ? &pathing.to_any_altar() : nullptr; // trips matter only when carrying
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
    const float per_gold = prices(world).per_gold * (gold_farmer ? params::gold_farmer_weight : 1.0f);
    // An ally in sight clearing its claimed damaging group gets help only if finishing it alone
    // would take it below the recall line: one champion per camp otherwise.
    const auto struggling = [&](int g) __attribute__((always_inline)) {
        Phase step{"struggling"};
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
    const auto crew_strength = [&](int g) __attribute__((always_inline)) {
        float total = 0;
        for (const auto& a : world.allies)
            if (!a.is_self && a.alive && comms::claim_of(world, a.index) == g) total += floored_output(a);
        return total;
    };
    // A group too costly for us alone is still ours to call if an ally in reach with no claim of
    // its own can join: valued, like a crew's, by our share of the work.
    float partner_output = 0;
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && dist(here, a.pos) <= params::partner_radius && comms::claim_of(world, a.index) < 0)
            partner_output = std::max(partner_output, floored_output(a));
    const int n_groups = static_cast<int>(groups.size());
    // Static per group once read: its centre field (once warm) and that field's steps to our
    // spawn, its home_ground weight and its centre_to_altar steps. Then its reward and the walks
    // to bank it, kept while `context` holds, and its fastest clear while its belief also does.
    struct GroupFacts {
        const Field* centre = nullptr;
        int to_spawn = -1;
        float home = -1;
        int to_altar = -1;
        std::uint32_t context = 0, version = ~0u;
        bool sticky = false;
        int walk = 0, chained_tribute = 0, tribute = 0;
        std::uint32_t gold_in = 0;
        float gems = 0, gold = 0, fastest = 0, fastest_strength = 0;
        // Clearing it alone, kept while `clearing` and its belief hold.
        std::uint32_t clearing = 0, clear_version = ~0u;
        float damage = 0, rounds = 0, kite = -1;
    };
    static std::array<GroupFacts, 256> few_facts;
    static std::vector<GroupFacts> many_facts;
    if (n_groups > static_cast<int>(few_facts.size()) && static_cast<int>(many_facts.size()) != n_groups) many_facts.assign(n_groups, {});
    GroupFacts* const group_facts = n_groups > static_cast<int>(few_facts.size()) ? many_facts.data() : few_facts.data();
    struct Context {
        int bag, short_by;
        float per_gold;
        bool warm;
        bool operator==(const Context&) const = default;
    };
    static Context last_context{};
    static std::uint32_t context = 0;
    if (const Context now{bag, short_by, per_gold, pathing.centres_ready()};
        context == 0 || !(now == last_context))
        last_context = now, ++context;
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
    const int first = memory.farm_group >= 0 && memory.farm_group < n_groups ? memory.farm_group : 0;
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
    const bool centres_ready = pathing.centres_ready();
    const CampGroup* const group_data = groups.data();
    const CampBelief* const camp_data = world.camps.data();
    int* const steps_data = centre_steps.data();
    int k = 0;
    for (; k < n_groups && (fuel_ok(ample) || fuel_ok(loop_floor + loop_reserve())); ++k) {
        const int g = (first + k) % n_groups;
        const auto& group = group_data[g];
        const auto& belief = camp_data[g];
        if (group.has_monolith || group.gems + group.gold == 0 || (belief.state == CampState::cleared && ally_holding(g)))
            continue;
        const bool claimed = taken(g);
        // Carrying, compare whole trips: the gems score only after the walk to an altar and the
        // tribute. Empty-handed, only a capture that wins counts that walk, as no later one shares
        // it. Gems past the win are worth nothing.
        const bool wins = group.gems >= short_by;
        auto& known = group_facts[g];
        if (known.context != context || known.sticky != (g == farm_group)) {
            Phase step{"group_facts"};
            const Field* to_bank = to_altar ? to_altar : wins ? &pathing.to_any_altar() : nullptr;
            // A recall only goes home: the way out from an altar is walked.
            if (to_bank && known.to_altar < 0) known.to_altar = pathing.centre_to_altar(g);
            known.walk = to_bank ? known.to_altar : unreachable;
            // Chained, the gems join the bag's one tribute; from the altar they need their own.
            known.chained_tribute = tribute_turns(bag + group.gems) - (bag > 0 ? tribute_turns(bag) : 0);
            known.tribute = tribute_turns(group.gems);
            known.gold_in = static_cast<std::uint32_t>(group.gold / holders(group));
            // The spawn fields home_ground reads are warm once the centres are.
            if (known.home < 0 && centres_ready) known.home = home_ground(map, g);
            float weight = centres_ready ? known.home : 1.0f;
            // Staying with last turn's choice keeps near ties from turning us back and forth.
            if (g == farm_group) weight *= stickiness;
            known.gems = weight * static_cast<float>(std::min(group.gems, short_by));
            known.gold = weight * per_gold * static_cast<float>(group.gold);
            known.context = context;
            known.sticky = g == farm_group;
            known.version = ~0u;
        }
        if (known.version != belief.version || known.fastest_strength != strength)
            known.version = belief.version, known.fastest_strength = strength, known.fastest = fastest_clear(world, g, strength);
        const int walk = known.walk;
        // The trip home is health-dependent, so it stays out of the kept facts.
        const float back = to_altar ? (wins ? winning_trip : trip_home)->rounds(walk, capture_rounds(), known.gold_in) : static_cast<float>(walk);
        const bool banks = back < static_cast<float>(unreachable);
        const float bank = banks ? back + static_cast<float>(known.chained_tribute) : 0.0f;
        const float cycle_bank = banks ? back + static_cast<float>(known.tribute) : 0.0f;
        auto& steps_known = steps_data[g];
        if (steps_known < 0) {
            // Walking is symmetric: a group's warm centre field gives our steps to it before all are.
            if (const auto* centre = centre_field(g)) {
                steps_known = centre->at(here);
            } else if (const auto drafted = map.drafted_spawn_steps(here, g)) {
                steps_known = *drafted;
            } else {
                if (!from_here) {
                    // A walk is never shorter than the Chebyshev distance, and the trip grows with the
                    // walk: a group that cannot beat the best from that close needs no field from here.
                    if (!claimed && best >= 0) {
                        const int near = dist(here, group.centre);
                        const int near_wait = belief.state == CampState::respawning ? std::max(0, belief.respawn_round - round - near) : 0;
                        const bool may_help = bag == 0 && group.strength > 0 && belief.state == CampState::alive && near <= params::help_radius
                                              && near < help_steps;
                        const float near_cycle = static_cast<float>(near + near_wait + capture_rounds()) - bank_now + bank + known.fastest;
                        if (!may_help && near_cycle > 0 && (known.gems + known.gold) / near_cycle <= best_value
                            && (bag == 0 || (known.gems + known.gold) / (static_cast<float>(walk + capture_rounds()) + cycle_bank + known.fastest) <= from_altar_value))
                            continue;
                    }
                    if (!fuel_ok(full_field_cost_estimate() + loop_floor + loop_reserve())) break;
                    Phase step{"steps_field"};
                    from_here = make_field(pathing.static_walls(), single(here));
                    world.throw_if_stale();
                }
                steps_known = from_here->at(group.centre);
            }
        }
        const int steps = steps_known;
        if (steps == unreachable) continue;
        // A group still respawning when we would arrive costs the wait there.
        const int wait = belief.state == CampState::respawning ? std::max(0, belief.respawn_round - round - steps) : 0;
        if (wait > params::max_wait) continue;
        if (bag == 0 && group.strength > 0 && belief.state == CampState::alive && steps <= params::help_radius
            && steps < help_steps && struggling(g))
            help_group = g, help_steps = steps;
        const float trip = static_cast<float>(steps + wait) - bank_now + bank;
        const float gems = known.gems, gold = known.gold, fastest = known.fastest;
        // Risky groups matter only while no affordable one is found; skip the costly clearing
        // estimate for groups that cannot beat it even with no clearing. A crew's share can.
        if (!claimed && best >= 0 && (gems + gold) / (trip + static_cast<float>(capture_rounds()) + fastest) <= best_value
            && (bag == 0 || (gems + gold) / (static_cast<float>(walk + capture_rounds()) + cycle_bank + fastest) <= from_altar_value))
            continue;
        // No known way to an altar (sealed, or a centre walls hide) is no deadline: the gold still counts.
        const auto too_late = [&](float clear_rounds) __attribute__((always_inline)) {
            if (known.to_altar < 0) known.to_altar = pathing.centre_to_altar(g);
            const int last = known.to_altar;
            return last != unreachable
                   && static_cast<float>(steps + wait + capture_rounds() + last + tribute_turns(bag + group.gems)) + clear_rounds > static_cast<float>(left);
        };
        const float worth = gems + gold;
        if (claimed) {
            Phase step{"crew_share"};
            if (belief.state == CampState::cleared) continue;
            const bool fresh = belief.state == CampState::respawning;
            float health = 0;
            for (std::size_t i = 0; i < group.members.size(); ++i) health += fresh ? group.members[i].max_health : belief.health[i];
            const float others = crew_strength(g);
            const int working = std::max(0, steps - (fresh ? std::max(0, belief.respawn_round - round) : 0));
            const float health_left = health - others * static_cast<float>(working);
            if (health <= 0 || health_left <= 0) continue;
            // A capture that wins the game is the team's, not a share: what counts is how soon.
            const float rounds = health_left / (strength + others), part = wins ? 1.0f : strength * rounds / health;
            // No capture rounds: the claimer holds it, and the crew moves on once it is cleared.
            const float value = rate(world, worth * part, trip + rounds);
            // Only a better share counts, and the final pick takes none an affordable group beats.
            if (value <= shared_value || (best >= 0 && value <= best_value) || too_late(rounds)) continue;
            float joint_rounds = 0;
            const float hits = soften * min_camp_damage(world, g, strength + others, &joint_rounds) * (strength * rounds / health);
            if (hits > spare_health) continue;
            shared = g, shared_value = value, shared_steps = steps;
            continue;
        }
        if (known.clearing != clearing || known.clear_version != belief.version) {
            Phase step{"clear_cost"};
            known.clearing = clearing, known.clear_version = belief.version;
            known.damage = known.rounds = 0, known.kite = -1;
            if (belief.state != CampState::cleared) {
                known.damage = min_camp_damage(world, g, strength, &known.rounds, reflect);
                if (group.strength > 0) known.kite = spell_clear_rounds(world, g, range, spells, basic);
            }
        }
        const float alone_damage = soften * known.damage, alone_rounds = known.rounds, kite = known.kite;
        // Unless a partner shares the clear, it takes us alone at least the quicker of the two ways.
        if (best >= 0 && (alone_damage <= spare_health || partner_output <= 0 || belief.state != CampState::alive)) {
            const float quickest = kite >= 0 ? std::min(alone_rounds, kite) : alone_rounds;
            if (worth / (trip + quickest + capture_rounds()) <= best_value
                && (bag == 0 || worth / (static_cast<float>(walk) + cycle_bank + quickest + capture_rounds()) <= from_altar_value))
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
        const float cycle = trip + clear_rounds + capture_rounds();
        float value = rate(world, worth, cycle);
        if (damage > spare_health && partner_output > 0 && belief.state == CampState::alive) {
            float joint_rounds = 0;
            const float part = strength / (strength + partner_output);
            if (soften * min_camp_damage(world, g, strength + partner_output, &joint_rounds) * part <= spare_health) {
                damage = 0;
                const float joint_cycle = trip + joint_rounds + capture_rounds();
                value = rate(world, worth * part, joint_cycle);
            }
        }
        if (damage > spare_health && !ally_engaged(world, g)) {
            if (value > risky_value) risky = g, risky_value = value, risky_steps = steps;
        } else {
            if (value > best_value) best = g, best_value = value, best_steps = steps, best_spell = spell;
            if (bag > 0 && walk != unreachable) {
                const float via_altar = belief.state == CampState::respawning ? std::max(0.0f, static_cast<float>(belief.respawn_round - round - walk) - bank_now) : 0.0f;
                const float from_altar = static_cast<float>(walk) + cycle_bank + via_altar + clear_rounds + capture_rounds();
                from_altar_value = std::max(from_altar_value, rate(world, worth, from_altar));
            }
        }
    }
    if (k < n_groups) note_shortcut("farm-partial-evaluation");
    if (bag > 0 && (best < 0 || best_value <= from_altar_value)) return false;
    if (bag > 0 && attack_in_range()) return true;
    if (world.is_stale()) return true;
    if (best < 0) best = risky, best_steps = risky_steps, best_value = risky_value;
    memory.crew = false;
    bool spell = best >= 0 && best_spell;
    if (shared >= 0 && (best < 0 || shared_value > best_value))
        best = shared, best_steps = shared_steps, memory.crew = true, spell = false;
    if (help_group >= 0) best = help_group, best_steps = help_steps, memory.crew = true, spell = false;
    set_claim(memory, pathing, best);
    if (best < 0) {
        // Cut short before weighing even last turn's choice: walk on towards it.
        if (k == 0 && memory.farm_group >= 0) set_claim(memory, pathing, memory.farm_group), walk_on(memory.farm_group);
        return true;
    }
    memory.farm_group = best;
    // Our fields price a dash over a hole line; live routes walk round it.
    const bool dasher = world.me().facts().has_dash();
    if (dasher && any_within(map.crossable, here, 1))
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
            if (!pathing.step_towards(off_zone(groups[best].tiles()), zone, cap) && dasher) walk_on(best);
        } else {
            note_shortcut("farm-no-route");
            walk_on(best);
        }
        return true;
    }
    if (spell && dist(here, groups[best].centre) <= vision_radius + ability_range
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
    if (test(*tiles, here) && my_can_attack() && attack_camp(world, [&](int g) { return g == best; }) < 0) {
        refused.emplace(*tiles);
        refused->set(here, false);
    }
    const auto& goals = refused ? *refused : *tiles;
    if (test(goals, here)) { // attacked from here; stay
        cast_at_camp(world, pathing, best);
        reset_and_attack_camp(world, pathing.safety(), best);
        if (melee) step_onto_cleared(world, pathing, best);
        return true;
    }
    if (!zone && dash_towards(world, pathing, goals, cap) && attack_camp(world, passing) >= 0) return true;
    const bool walked = fuel_ok(search_cost_estimate(cap) + end_reserve)
                            ? pathing.step_towards(off_zone(goals), zone, cap)
                                  || pathing.step_towards(off_zone(groups[best].adjacent()), zone, cap)
                            : (note_shortcut("farm-no-route"), walk_on(best));
    if (!walked && dasher) walk_on(best);
    if (walked) {
        // A hit on a champion is worth its damage; on a camp, the gems it brings closer.
        if (!strike_enemy(world)) attack_camp(world, passing);
        cast_at_camp(world, pathing, best); // only casts that allow walking remain
        reset_and_attack_camp(world, pathing.safety(), best);
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
// Our one ward never expires, so replace it only by a cluster with more tiles in ability range of
// here and of our work (claimed group or waited-at altar), where we will be again.
// Without `grow`, only if every cluster that needs is found already.
bool ward_bushes(const World& world, Memory& memory, bool grow) {
    const auto& map = world.map();
    const vec2 here = my_position();
    const auto floor = small_cost_estimate + end_reserve;
    if (here == memory.bushes_watched) return false;
    if (!fuel_ok(floor)) {
        note_shortcut("ward-no-bushes-fuel");
        return false;
    }
    if (!test(map.near_bushes(), here)) return false;
    if (!grow) {
        if (!map.bush_clusters_found(here, 2)) return false;
    } else if (!map.find_bush_clusters(here, 2, floor)) {
        note_shortcut("ward-no-bushes-clusters");
        return false;
    }
    // Scratch boards: allocating one costs more than the host operations on it.
    static bitboard candidates{cambc::uninitialized}, inner{cambc::uninitialized}, scratch{cambc::uninitialized},
        best{cambc::uninitialized};
    candidates.clear();
    candidates.draw_chebyshev(here, 2.0f);
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
    Phase phase{"place_ward"};
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
    if (c.asleep == 0) return true;
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
// leaving lets their hold pay.
bool contesting(const World& world) {
    const vec2 here = my_position();
    const int g = world.map().group_at(here);
    if (g < 0 || world.map().groups[g].gems == 0 || world.camps[g].state != CampState::cleared || winning_bag(world)) return false;
    return world.camps[g].holder == team::enemy || enemy_on(world, world.map().groups[g].tiles());
}

// A visible enemy's blow reaches p.
bool visible_threat(const World&, Safety& safety, vec2 p) { return safety.tile(p).vis_mask != 0; }

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
        int n = 0;
        for (const auto& e : world.enemies)
            if (n < static_cast<int>(members.size()) && e.alive && e.age(world.round) <= 1 && !test(map.near_enemy_spawn, e.pos))
                members[n++] = {e.pos, e.health, output(e)};
        if (n > 0) {
            const float health = pz.health;
            float our_health = 0, our_damage = 0;
            for (const auto& a : world.allies)
                if (a.alive && (a.is_self || (a.visible && dist(here, a.pos) <= params::pack_ally_radius))) {
                    our_health += a.is_self ? health : a.health;
                    our_damage += output(a);
                }
            const bool hurt = health < params::hurt_health_fraction * pz.max_health || pz.bag >= params::brake_bag;
            // A pack in our half has come to fight there.
            const bool home = own_ground(world, here);
            const float healthy = home ? params::home_retreat_ratio : params::retreat_ratio;
            const float ours = (hurt ? std::min(healthy, params::hurt_retreat_ratio) : healthy) * our_health * our_damage;
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
    Phase phase{"pack_zone"};
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
    Phase phase{"outmatched"};
    return in_pack_zone(world, world.me().pos) && !paying_soon(world);
}

// Camps keep hitting while we walk out of their reach: leave while the health still covers that.
// A siege (Memory::siege) keeps its own health limits for its group's hits.
bool camp_trapped(const World& world, Safety& safety, vec2 here, float health, bool sieging) {
    Phase phase{"camp_trapped"};
    if (sieging) return false;
    const float dps = safety.camp_damage(here);
    if (dps <= 0) return false;
    const auto exit_cost = [&](float damage) { return 1.5f * damage + dps; };
    // The exit takes 1 to max_camp_reach + 1 rounds: the bounds settle most cases without the search.
    if (health > exit_cost(dps * static_cast<float>(world.map().max_camp_reach + 1))) return false;
    if (health <= exit_cost(dps)) return true;
    return health <= exit_cost(safety.exit_damage(here));
}

// An enemy that could kill us before our next turn overrides finishing a camp or a capture.
bool want_home(const World& world, Safety& safety, bool sieging) {
    Phase phase{"want_home"};
    debug_block({ ++home_asks; });
    world.throw_if_stale();
    const vec2 here = my_position();
    if (test(world.map().ally_spawn, here)) return false;
    const float health = my_health();
    const bool low = health < params::recall_health_fraction * my_max_health() && !finishing_camp(world) && !holding_capture(world);
    if (low || outmatched(world) || camp_trapped(world, safety, here, health, sieging)) return true;
    // Out of sight and not lethal, nobody can win a fight here or pursue us.
    const bool lethal = safety.lethal(here);
    if (!lethal && !enemy_seen(world)) return false;
    std::optional<Trade> stand;
    const auto s = [&]() -> const Trade& {
        if (!stand) stand = safety.engage(here, {});
        return *stand;
    };
    if ((lethal && s().self_falls) || (visible_threat(world, safety, here) && s().lost)) return true;
    // Healthy on our own ground, they have no reason to come for us.
    if (paying_soon(world) || (own_ground(world, here) && health >= params::hurt_health_fraction * my_max_health())) return false;
    const bool linked = partner(world) != nullptr;
    const Engage pursue{.mode = Engage::Mode::pursue, .approach = params::pursuit_steps};
    // The pursuit strikes first against some of the stand fight's enemies, arriving later: a stand
    // fight we win cleanly against all of them settles it. Its visible enemies are tile(here)'s.
    // The stand is unsimulated only when no visible threat hits us, and then holds no pursuer.
    const auto pursuers_standing = [&] {
        const auto& spawn = world.map().near_enemy_spawn;
        for (auto left = safety.seen_enemies() & ~std::uint32_t{safety.tile(here).vis_mask}; left; left &= left - 1) {
            const auto& e = world.enemies[static_cast<std::size_t>(std::countr_zero(left))];
            if (!in_square(here, e.pos, Strike::max_reach + params::pursuit_steps)) continue;
            if (const int reach = safety.strike_of(e).reach; reach >= 0 && dist(here, e.pos) - reach <= params::pursuit_steps && !test(spawn, e.pos))
                return false;
        }
        return true;
    };
    if (stand && !stand->lost && !stand->self_falls && pursuers_standing()) {
        debug_block({ std::printf("WANTHOME-PURSUIT-SKIPPED %d %u\n", world.round, static_cast<std::uint32_t>(world.me().handle)); });
        if constexpr (debug_verdicts) {
            if (const auto t = safety.engage(here, pursue); t.lost || (linked && t.self_falls)) {
                debug_block({
                    std::printf("PURSUIT-SKIP-MISMATCH %d %u %d %d %d %d\n", world.round, static_cast<std::uint32_t>(world.me().handle), here.x,
                                here.y, t.lost ? 1 : 0, t.self_falls ? 1 : 0);
                });
            }
        }
        return false;
    }
    const auto t = safety.engage(here, pursue);
    return t.lost || (linked && t.self_falls);
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
    if (e.channel == Channel::tribute) {
        if (e.facts().passive != Passive::stun_immune)
            if (const int reach = self.ready_stun_reach(e.channel_end_round - 1); reach >= 0)
                steps = std::min(steps, std::max(0, dist(here, e.pos) - reach));
        if (const int a = tribute_altar(world, e.pos); a >= 0 && carried_locks() > 0)
            steps = std::min(steps, std::max(0, dist(here, altars[a].pos) - 2));
        return steps < e.channel_end_round - world.round ? steps : unreachable;
    }
    int a = -1;
    for (int k = 0; k < static_cast<int>(altars.size()); ++k)
        if (a < 0 || dist(e.pos, altars[k].pos) < dist(e.pos, altars[a].pos)) a = k;
    if (a < 0) return unreachable;
    const int theirs = std::max(0, dist(e.pos, altars[a].pos) - 1) + tribute_turns(pair_gems(world, e));
    return std::max(0, dist(here, altars[a].pos) - 1 - range) < theirs ? steps : unreachable;
}

// The visible enemy whose kill pays most a turn to reach and kill it, among those whose fight at
// the tile we would strike it from we win even when they strike first; never one on or next to its
// spawn, where it heals.
const ChampionBelief* prey(const World& world, Safety& safety) {
    Phase phase{"prey"};
    world.throw_if_stale();
    if (!enemy_seen(world)) return nullptr;
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
        // Out of reach on its own ground only when hurt or carrying a bag we can stop: fights at
        // central altars straddle the line, and a beaten enemy otherwise escapes a step across it,
        // but a bag has to stop at an altar to score, and a kill takes it. An enemy holding a
        // cleared group is taking its gems: killing it is how a capture is contested.
        const int g = world.map().group_at(e.pos);
        const int held = g >= 0 && world.camps[g].state == CampState::cleared ? world.map().groups[g].gems : 0;
        if (dist(here, e.pos) > range && !own_ground(world, e.pos) && e.health >= 0.5f * e.max_health && held == 0
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
    // Where we would strike from: the open tile in range of e nearest us, then nearest the clamp of
    // our tile into its range.
    const auto& open = world.map().open_for_us;
    const auto attack_tile = [&](vec2 e) -> std::optional<vec2> {
        const vec2 c{std::clamp(here.x, e.x - range, e.x + range), std::clamp(here.y, e.y - range, e.y + range)};
        if (test(open, c)) return c;
        std::optional<vec2> best;
        int best_here = 0, best_c = 0;
        for (const vec2 q : Tiles<7 * 7>{within(open, e, range)}) {
            const int to_here = dist(q, here), to_c = dist(q, c);
            if (q == e || (best && (to_here > best_here || (to_here == best_here && to_c >= best_c)))) continue;
            best = q, best_here = to_here, best_c = to_c;
        }
        return best;
    };
    // The prey stays in the key: a melee one cannot reach a ranged attack tile.
    constexpr int max_fights = 3;
    for (int i = 0, fights = 0; i < n && fights < max_fights; ++i) {
        const auto& e = *order[i].second;
        const auto at = attack_tile(e.pos);
        if (!at) continue;
        ++fights;
        const auto t = safety.engage(*at, {.with_enemy = e.index});
        const bool won = !t.lost && !(linked && t.self_falls);
        if constexpr (debug_verdicts) {
            if (const auto old = safety.engage(e.pos, {}); won != (!old.lost && !(linked && old.self_falls))) {
                debug_block({
                    std::printf("PREY-FLIP %d %u e%d %d %d %d\n", world.round, static_cast<std::uint32_t>(world.me().handle), e.index, at->x,
                                at->y, won ? 1 : 0);
                });
            }
        }
        if (won) return &e;
    }
    return nullptr;
}

float farm_step_value(const World& world);

bool chase(const World& world, Pathing& pathing, Safety& safety, Prepared* prepared) {
    Phase phase{"chase"};
    const auto* target = prey(world, safety);
    if (!target) return false;
    decision = 'C';
    if constexpr (debug_fights) log_fight("FC", world, safety, target->pos, safety.fight(target->pos), static_cast<int>(target->handle));
    const int range = world.me().facts().attack_range();
    // A walk alone cannot reach range this turn; a melee walk can follow the dash.
    if (dist(my_position(), target->pos) > range + 1 && my_can_move()) dash_to_attack(world, pathing, *target);
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
    hit |= reset_and_attack_enemy(world, false, &safety); // after an attack, or a ranged walk
    hit |= cast_at_enemies(world, pathing);
    // No step and no hit: the target is out of our walk's reach (across live camps), so the turn goes on.
    return hit || !stuck;
}

bool can_tribute_safely(const World& world, Safety& safety, const Memory& memory) {
    Phase phase{"can_tribute_safely"};
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
    const int walk = pathing.to_any_altar().at(here);
    return walk != unreachable && home_trip(world, pathing, my_channel_time(), winning_bag(world)).rounds(walk, 0, 0) < static_cast<float>(walk);
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
bool capture_recall(const World& world, Pathing& pathing, Safety& safety) {
    const vec2 here = my_position();
    if (safety.threatened(here)) return false;
    const int g = world.map().group_at(here);
    const auto& c = world.camps[g];
    if (c.holder != team::ally || c.held_since < 0) return false;
    const int payout = c.payout_round();
    const int channel = my_channel_time();
    if (world.round + channel < payout) return false;
    const int walk = pathing.to_any_altar().at(here);
    if (walk == unreachable) return false;
    const auto& G = world.map().groups[g];
    const bool wins = capture_share(world, g) >= gems_short(world);
    const int sharers = 1 + allies_on(world, G.tiles());
    return home_trip(world, pathing, channel, wins).rounds(walk, payout - world.round, G.gold / sharers) < static_cast<float>(walk);
}

// With an empty bag, the gold to complete the next emblem goes home to shop, riding a recall unless walking is
// quicker.
[[gnu::flatten]] bool wants_shop(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    Phase phase{"wants_shop"};
    if (bankable_bag(world, pathing) > 0 || memory.damage > 0 || !may_shop(world)) return false;
    const auto gold = my_gold();
    if (gold < shard_price || (gold < emblem_price && !emblem_begun())) return false;
    const vec2 here = my_position();
    if (test(world.map().ally_spawn, here) || safety.threatened(here)) return false;
    // The trip costs the recall and the walk back out; arriving by recall, the heal takes the turn.
    const auto stop = home_trip(world, pathing, recall_turns(world), winning_bag(world));
    if (stop.short_gold > 0) return false;
    const int back = pathing.to_ally_spawn().at(here);
    if (back != unreachable && stop.value(0) < static_cast<float>(std::min(back, stop.channel + stop.hurt) + back)) return false;
    bool awake = false;
    world.each_stirring([&](int g) { awake = awake || awake_over(world, g, here); });
    return !awake;
}

// A ready stun of ours reaches a visible enemy whose tribute wins them the game.
bool can_stop_winning_tribute(const World& world) {
    if (!enemy_seen(world)) return false;
    const auto& self = world.me();
    for (const auto& e : world.enemies)
        if (enemy_tribute_wins(world, e) && e.facts().passive != Passive::stun_immune
            && dist(self.pos, e.pos) <= self.ready_stun_reach(world.round))
            return true;
    return false;
}

// A visible enemy whose bag (both, for Cassi and Issac) ends the game once tributed and that we
// can stop: nothing we gain meanwhile counts unless our own bag wins first. The nearest; null if none.
const ChampionBelief* game_ender(const World& world) {
    Phase phase{"game_ender"};
    const int need = static_cast<int>(cambc::constants::winning_gems) - world.score.enemy;
    if (!enemy_seen(world)) return nullptr;
    // No pair carries more than every living enemy's bag together.
    int carried = 0;
    for (const auto& e : world.enemies) carried += e.alive ? e.gems : 0;
    if (carried < need) return nullptr;
    std::optional<vec2> here; // and our bag not winning, once one qualifies
    const ChampionBelief* best = nullptr;
    int best_steps = unreachable;
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible || pair_gems(world, e) < need || test(world.map().near_enemy_spawn, e.pos)) continue;
        if (!here) {
            if (winning_bag(world)) return nullptr;
            here = my_position();
        }
        if (const int steps = intercept_steps(world, e, *here); steps < best_steps) best = &e, best_steps = steps;
    }
    return best;
}

// Into reach of the enemy whose bag ends the game, whatever the risk: a stun or a lock if it is
// tributing, else attacks, followed until it stops at an altar.
void stop_game_ender(const World& world, Pathing& pathing, Memory& memory, const ChampionBelief& e) {
    Phase phase{"stop_game_ender"};
    auto& me = cambc::self();
    decision = 'E';
    write_claim(memory, pathing, -1);
    pathing.set_guarding(false);
    const bool tributing = e.channel == Channel::tribute;
    const auto act = [&] {
        place_lock(world);
        cast_at_enemies(world, pathing, !tributing && dist(me.position(), e.pos) > world.me().facts().attack_range() ? escape_step_value : 0.0f);
        if (attack_enemy(world)) reset_and_attack_enemy(world, false, pathing.safety());
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
    if (dist(me.position(), e.pos) > range + 1) dash_to_attack(world, pathing, e);
    if (!test(goals, me.position())) pathing.step_towards_funded(goals, end_reserve);
    act();
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
                 && (test(G.tiles(), a.pos) || dist(a.pos, G.centre) < dist(here, G.centre)
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

// The Monolith or sealing group (seals()) to siege; one the enemy holds or that returns too late is
// skipped. `sealing` tells which.
int siege_candidate(const World& world, Pathing& pathing, const Memory& memory, bool& sealing) {
    Phase phase{"siege_candidate"};
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
        // siege_ready never passes a live Monolith off Monolith-only maps unless it seals: only a
        // cleared one counts.
        if (!map.monolith_only && !seal && c.state != CampState::cleared) return;
        const int wait = c.state == CampState::respawning ? c.respawn_round - world.round : 0;
        if (wait > params::siege_respawn_wait) return;
        if (c.state == CampState::cleared && c.holder == team::enemy) return;
        const int steps = map.ally_steps(g);
        if (steps == unreachable) return;
        // The walk there and the wait for its return, with the team's current target kept until
        // another is clearly sooner: switching turns everyone around.
        float cost = static_cast<float>(std::max(steps, wait));
        if (memory.siege && memory.claim == g) cost -= static_cast<float>(params::siege_stickiness);
        if (best < 0 || cost < best_cost) best = g, best_cost = cost, sealing = seal;
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
bool siege_ready(const World& world, const SiegeLoad& load, bool committed, bool sealing) {
    if (load.health <= 0) return true;
    const float rounds = load.health / team_power(world);
    const float slack = committed ? params::siege_commit_slack : 1.0f;
    const float limit = world.map().monolith_only || sealing ? params::siege_rounds : 0;
    if (rounds > limit * slack) return false;
    float pool = 0;
    for (const auto& a : world.allies)
        if (a.alive) pool += a.max_health;
    return rounds * load.hit * camp_hit_factor() * params::siege_hit_share <= params::siege_pool_share * pool * slack;
}

// Once the team is strong enough it goes together: melee adjacent, ranged at their range, the hurt
// stepping out to 4, where casters still cast.
bool siege(const World& world, Pathing& pathing, Memory& memory) {
    Phase phase{"siege"};
    world.throw_if_stale();
    sieged = true;
    const auto& map = world.map();
    bool sealing = false;
    const int g = siege_candidate(world, pathing, memory, sealing);
    const bool ally_in = g >= 0 && ally_claims(world, g);
    const auto load = g >= 0 ? siege_load(world, g) : SiegeLoad{};
    if (g < 0 || !siege_ready(world, load, (memory.siege && memory.claim == g) || ally_in, sealing)) {
        memory.siege = false;
        memory.staged_since = -1;
        return false;
    }
    const auto& G = map.groups[g];
    const auto& c = world.camps[g];
    const vec2 here = my_position();
    if (c.state == CampState::cleared) {
        // The nearest take the capture, split to shorten the tributes; the rest farm.
        if (capture_taken(world, G, here)) {
            memory.siege = false;
            return false;
        }
        memory.siege = true;
        memory.staged_since = -1;
        set_claim(memory, pathing, g);
        memory.crew = false;
        pathing.step_towards_funded(G.tiles(), end_reserve);
        return true;
    }
    memory.siege = true;
    set_claim(memory, pathing, g);
    memory.crew = ally_in;
    siege_group() = g;
    const vec2 m = load.pos;
    const int d = dist(here, m);
    const auto& f = world.me().facts();
    const int range = f.attack_range();
    const bool fresh = c.state == CampState::respawning;
    const int stage = G.reach + 2; // just out of the group's reach

    bool engaged = false;
    float staged = floored_output(world.me());
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible) continue;
        if (test(G.threat(), a.pos) && c.awake != Awake::asleep) engaged = true;
        if (dist(a.pos, m) <= stage + 1) staged += floored_output(a);
    }
    if (!fresh && test(G.threat(), here) && c.awake != Awake::asleep) engaged = true;
    if (!engaged && !fresh) {
        if (memory.staged_since < 0 && d <= stage + 1) memory.staged_since = world.round;
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
        Phase step{"siege_tiles"};
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
        if (engaged) cast_at_camp(world, pathing, g);
        if (engaged && !low) reset_and_attack_camp(world, pathing.safety(), g);
        return true;
    }
    if (!engaged) return true;
    cast_at_camp(world, pathing, g);
    if (!low) {
        attack_camp(world, [&](int h) { return h == g; });
        reset_and_attack_camp(world, pathing.safety(), g);
    }
    return true;
}

// A big group cleared by spells from 4, out of its monsters' reach, so that nobody takes a hit;
// harmless members fall to basic attacks from there, the rest once the monsters are dead.
bool kite(const World& world, Pathing& pathing, Memory& memory) {
    Phase phase{"kite"};
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
            if (!test(tiles, here) && too_late(g)) return false;
            set_claim(memory, pathing, g);
            memory.crew = false;
            if (test(tiles, here)) return true; // our tile keeps their hold from counting
            const auto& free = free_tiles(tiles);
            if (!board_empty(free)) pathing.step_towards_funded(free, end_reserve);
            return true;
        }
        if (capture_taken(world, G, here) || dist(here, G.centre) > 2 * vision_radius) return false;
        set_claim(memory, pathing, g);
        memory.crew = false;
        pathing.step_towards_funded(G.tiles(), end_reserve);
        return true;
    }
    const bool fresh = c.state == CampState::respawning;
    static bitboard threat{cambc::uninitialized}, near{cambc::uninitialized}, goals{cambc::uninitialized},
        basic{cambc::uninitialized};
    clear_board(threat);
    clear_board(near);
    clear_board(basic);
    const int range = world.me().facts().attack_range();
    bool attackers = false;
    for (std::size_t i = 0; i < G.members.size(); ++i) {
        if (!fresh && c.health[i] <= 0) continue;
        const vec2 p = G.members[i].pos;
        if (G.members[i].strength > 0) {
            attackers = true;
            draw_square(threat, p, static_cast<float>(G.members[i].reach));
            draw_square(near, p, static_cast<float>(ability_range));
        } else {
            draw_square(basic, p, static_cast<float>(range));
        }
    }
    // Only harmless members: farm clears them. Champions without spells stand guard with the
    // casters, for the fights and the capture.
    if (!attackers) return false;
    const bool ally_in = ally_claims(world, g);
    set_claim(memory, pathing, g);
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
        const bool cast = cast_at_camp(world, pathing, g, false, true);
        const bool attacked = attack_camp(world, [&](int h) { return h == g; }) >= 0;
        if (attacked) reset_and_attack_camp(world, pathing.safety(), g);
        return cast || attacked;
    };
    const auto& first = basic_first ? basic : goals;
    if (safe_here) {
        const bool placed = test(first, here);
        if (hit() || placed) return true;
    }
    // Far off, the static walk to within reach; the live route around the monsters once near.
    if (dist(here, G.centre) > vision_radius + ability_range) {
        if (const auto* field = pathing.approach(g, ability_range)) pathing.step_towards(*field);
        else pathing.step_closer(G.centre);
        return true;
    }
    // A short way to a basic attack's tile, else any safe one: the long way round to the far side
    // of the monsters costs more than the attacks pay.
    const int cap = 2 * (vision_radius + ability_range);
    bool moved = basic_first && pathing.step_towards(basic, &threat, vision_radius);
    if (!moved && !test(goals, here)) moved = pathing.step_towards(goals, &threat, cap);
    // A sleeping group hits nobody passing through its reach.
    if (!moved && !test(goals, here) && c.awake == Awake::asleep) moved = pathing.step_towards(goals, nullptr, cap);
    // No way within the cap (round a lake): the static walk.
    if (!moved && !test(goals, here))
        if (const auto* field = pathing.approach(g, ability_range))
            moved = pathing.step_towards(*field, c.awake == Awake::asleep ? nullptr : &threat);
    if (!moved && !safe_here) {
        static bitboard out{cambc::uninitialized};
        clear_board(out);
        out |= map.standable;
        drop(out, threat);
        pathing.step_towards(out, nullptr, 2 * G.reach);
    }
    if (!test(threat, my_position())) hit();
    return true;
}

// A cleared gem group in sight that the enemy holds or stands on, and that we can reach before the
// hold pays: a body of ours on one of its tiles stops the count. Its gems, denied within a few
// steps, beat any farm cycle's rate, however small the group.
bool contest_capture(const World& world, Pathing& pathing, Memory& memory) {
    Phase phase{"contest_capture"};
    const auto& map = world.map();
    const vec2 here = my_position();
    int best = -1, best_steps = unreachable;
    world.each_cleared([&](int g) {
        const auto& G = map.groups[g];
        const auto& c = world.camps[g];
        if (G.gems == 0 || dist(here, G.centre) > vision_radius + 2) return;
        if (!enemy_on(world, G.tiles()) && c.holder != team::enemy) return;
        const int steps = steps_to(G, here);
        if (steps > enemy_hold_left(world, c) || steps >= best_steps) return;
        best = g, best_steps = steps;
    });
    if (best < 0) return false;
    const auto& free = free_tiles(map.groups[best].tiles());
    if (free.is_empty() || !pathing.step_towards(free, nullptr, best_steps + max_detour)) return false;
    write_claim(memory, pathing, best);
    memory.crew = false;
    return true;
}

// A sieger stepped out of the besieged group's reach goes home to heal before it is needed again.
bool siege_heal_trip(const Memory& memory, Safety& safety) {
    return memory.siege && my_health() < params::heal_trip_fraction * my_max_health() && !safety.threatened(my_position());
}

// Our tribute channel goes on unless it is unsafe and fleeing or fighting back pays. True if the
// turn ends with it; `home` gets want_home's answer when it is asked.
bool continue_tribute(const World& world, Safety& safety, Memory& memory, std::optional<bool>& home) {
    Phase phase{"continue_tribute"};
    auto& me = cambc::self();
    decision = 'T';
    // The enemy's winning tribute in reach of a ready stun or a lock is the game: ours waits.
    const auto* ender = game_ender(world);
    if (!winning_bag(world) && (can_stop_winning_tribute(world) || (ender && ender->channel == Channel::tribute))) {
        try {
            me.cancel_submit_gems();
        } catch (const std::exception&) {
        }
        if (!me.is_submitting_gems()) return false;
    }
    if (tribute_ok(world, safety, memory, my_channel_time())) return true;
    // Damage does not interrupt a tribute: cancelling pays only to flee or to fight back.
    if (safety.taken() <= 0) {
        home = want_home(world, safety, memory.siege);
        if (!*home && !attack_target(world) && (winning_bag(world) || !prey(world, safety))) return true;
    }
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
    Phase phase{"continue_recall"};
    auto& me = cambc::self();
    decision = 'K';
    if (game_ender(world)) {
        try {
            me.cancel_recall();
        } catch (const std::exception&) {
            return true;
        }
        return false;
    }
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
        if (siege_heal_trip(memory, safety)) return sieged = true; // the trip keeps the siege until home
        // No walk leaves a pocket a crystal took us into.
        if (!test(pathing.foot(), my_position()) && my_gems() == 0) return true;
    }
    try {
        me.cancel_recall();
    } catch (const std::exception&) {
        return true;
    }
    return false;
}

void mend_retreat(const World& world, Safety& safety, const Memory& memory);

void retreat(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    Phase phase{"retreat"};
    world.throw_if_stale();
    auto& me = cambc::self();
    decision = 'R';
    write_claim(memory, pathing, -1);
    memory.banking = bankable_bag(world, pathing) > 0; // a bag in retreat goes on to an altar, by a recall if quicker
    if (world.me().facts().walk_and_attack_independent() && attack_enemy(world)) reset_and_attack_enemy(world, true, &safety);
    cast_at_enemies(world, pathing, escape_step_value);
    if (!me.is_alive()) return;
    if (!my_can_attack() || !my_can_cast()) safety.refresh();
    // A tribute survives damage; a recall does not.
    if (can_tribute_safely(world, safety, memory)) {
        bank_gems(world, pathing, safety, memory);
        return;
    }
    // The escape dash shares the one cast: the reset only after it, from a melee attack or a ranged walk.
    dash_away(world, pathing, pathing.to_ally_spawn());
    reset_and_attack_enemy(world, false, &safety);
    if (!flee_camps(world, pathing, safety, pathing.to_ally_spawn())) retreat_step(world, pathing, safety, pathing.to_ally_spawn());
    reset_and_attack_enemy(world, false, &safety);
}

// On a capture we hold or contest: the hold needs no turn, so hit another group in reach that
// cannot hit back or already does.
void hold_capture(const World& world, Pathing& pathing, Memory& memory, bool attacked) {
    Phase phase{"hold_capture"};
    const int held = world.map().group_at(my_position());
    write_claim(memory, pathing, held);
    memory.crew = false;
    if (attacked) return;
    const auto& groups = world.map().groups;
    const auto free_hit = [&](int g) {
        const auto& c = world.camps[g];
        return g != held && (groups[g].strength <= 0 || (c.awake != Awake::asleep && c.asleep == 0));
    };
    if (const int hit = attack_camp(world, free_hit); hit >= 0) {
        cast_at_camp(world, pathing, hit);
        reset_and_attack_camp(world, pathing.safety(), hit);
    }
}

// Carrying: chase a kill worth the risk, bank, wait at an altar until it is safe, or chain another
// capture on the way.
void carry_bag(const World& world, Pathing& pathing, Safety& safety, Memory& memory, bool attacked, Prepared* prepared) {
    Phase phase{"carry_bag"};
    const bool safe = can_tribute_safely(world, safety, memory);
    const bool close = closing(world, pathing);
    if (!safe && !close && !winning_bag(world) && chase(world, pathing, safety, prepared)) return;
    if (safe) {
        decision = 'B';
        memory.banking = true;
        bank_gems(world, pathing, safety, memory);
        return;
    }
    if (can_tribute_here(world)) {
        // Hit with nothing to hit back: waiting here only takes more.
        if (safety.taken() > 0 && !attack_target(world)) {
            decision = 'R';
            pathing.set_guarding(false);
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
            int other_steps = carries_crystal() ? hop_route(world, pathing, memory).steps : unreachable;
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
    memory.banking = close || walked || !may_chain(world, safety) || !farm(world, pathing, memory);
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


// The turn's heals and shields where decide judges them (W4-A: one valuer, mend()). Before the
// search or the goal, on the turns the search does not plan.
void mend_early(const World& world, Safety& safety, const Memory& memory, bool strikes) {
    heal_ally(world);
    if (!strikes || !(reset_may_kill(world) || landing_ready(world))) shield_if_needed(world, safety, memory.claim);
}

// After the search, before the goal.
void mend_searched(const World& world, Safety& safety, const Memory& memory, bool strikes) {
    if (!strikes) return;
    if (!searched) heal_ally(world);
    // A cast the search left priced the shield at nothing, blind to the goal's coming camp hit:
    // judged here, before farm's camp reset or dash takes it.
    shield_if_needed(world, safety, memory.claim);
}

// On spawn healing, after the hits.
void mend_spawn(const World&, Safety&, const Memory&) {}

// In a retreat the search did not plan (W3-B calls it).
void mend_retreat(const World& world, Safety& safety, const Memory& memory) {
    heal_ally(world);
    shield_if_needed(world, safety, memory.claim);
}

void decide(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    auto& me = cambc::self();
    if (!world.me().alive || bankable_bag(world, pathing) == 0) memory.banking = false;
    if (!world.me().alive) {
        write_claim(memory, pathing, -1);
        buy_shards(world); // the dead can only shop
        buy_lock();
        buy_crystal(memory);
        return;
    }
    // One state read covers the channels until one is cancelled; a channel excludes the others.
    const auto state = my_state();
    if (state.contains(cambc::champion_state::teleporting)) return;
    // Read again only after shopping or a ward changes what it rests on.
    std::optional<bool> home;
    if (state.contains(cambc::champion_state::submitting_gems) && continue_tribute(world, safety, memory, home)) return;
    if (state.contains(cambc::champion_state::recalling) && continue_recall(world, pathing, safety, memory, home)) return;
    // A ward shares the recall's channel, so this is its first chance; its sight counts this turn
    // (probe-ward-sight). Growing clusters here would starve the search: the turn end grows them.
    if (place_ward(world, memory, false)) {
        world.observe();
        pathing.invalidate();
        // Safety's beliefs are fixed for its life: it keeps what the new sight left alone, else starts again.
        if (!safety.reobserve()) {
            std::destroy_at(&safety);
            std::construct_at(&safety, world);
            safety.set_claimed(memory.claim);
            note_hits(world, safety, memory);
        }
        // Even a kept Safety answers anew wherever the unseen enemies count.
        debug_block({ home_asks -= home.has_value(); });
        home.reset();
    }

    // Shopping, heals and shields do not move us.
    const bool on_spawn = test(world.map().ally_spawn, my_position());
    if ((on_spawn || world.me().facts().passive == Passive::remote_shop) && buy_shards(world)) {
        debug_block({ home_asks -= home.has_value(); });
        home.reset();
    }
    if (on_spawn) buy_lock(), buy_crystal(memory);
    if (!world.me().can_act(world.round)) return;
    if (const auto* ender = game_ender(world)) {
        stop_game_ender(world, pathing, memory, *ender);
        return;
    }
    const bool strikes = strike_possible(world);
    // Healing needs a turn end on spawn; a recall arrives at turn start.
    const bool mend = on_spawn && my_health() < my_max_health();
    const bool leave = !mend && (home ? *home : want_home(world, safety, memory.siege));
    // On the turns the search plans, it weighs heals and shields against its other casts.
    if (!strikes || mend || leave) mend_early(world, safety, memory, strikes);
    if (mend) {
        decision = 'H';
        const bool attacked = attack_enemy(world);
        if (attacked) reset_and_attack_enemy(world, true, &safety);
        cast_at_enemies(world, pathing);
        if (attacked) reset_and_attack_enemy(world, false, &safety);
        mend_spawn(world, safety, memory);
        return;
    }
    if (leave) {
        retreat(world, pathing, safety, memory);
        return;
    }

    pathing.set_guarding(true);
    const bool holding = holding_capture(world) || contesting(world);
    bool attacked = false;
    Prepared* prepared = nullptr;
    if (strikes) {
        Intent intent;
        intent.anchored = holding;
        intent.walks = !holding && !can_tribute_here(world);
        // A carrier's step banks a turn sooner, freeing a turn of output for the farm.
        intent.step_value = farm_step_value(world);
        // An enemy already in attack range was not worth leaving (want_home): the fight is here.
        if (enemy_within(world, my_position(), world.me().facts().attack_range())) intent.walks = false;
        // The goal most likely walks to an altar when carrying, else to the farm choice.
        intent.to_altar = bankable_bag(world, pathing) > 0;
        intent.group = memory.farm_group;
        prepared = prepare_strikes(world, pathing, safety, intent);
        const auto planned = price_strikes(*prepared, intent);
        attacked = planned.attacked;
        searched = planned.searched;
        searched_at = my_position();
        searched_hit = !my_can_attack();
    }
    mend_searched(world, safety, memory, strikes);
    decision = holding ? 'P' : attacked ? 'A' : decision;
    if (!me.is_alive()) return;
    if (!my_can_attack() || !my_can_cast()) safety.refresh();
    if (holding) {
        hold_capture(world, pathing, memory, attacked);
        return;
    }
    if (bankable_bag(world, pathing) > 0) {
        carry_bag(world, pathing, safety, memory, attacked, prepared);
        return;
    }
    if (attacked && !world.me().facts().walk_and_attack_independent()) return;
    if (wants_shop(world, pathing, safety, memory)) {
        decision = 'S';
        set_claim(memory, pathing, -1);
        step_safely(pathing, pathing.to_ally_spawn(), safety);
        return;
    }
    if (chase(world, pathing, safety, prepared)) return;
    if (contest_capture(world, pathing, memory)) {
        decision = 'X';
        return;
    }
    decision = 'F';
    if (world.map().shared_gems ? kite(world, pathing, memory) : siege(world, pathing, memory)) {
        decision = 'G';
        return;
    }
    farm(world, pathing, memory);
}

// Recalling every turn end and cancelling next turn when not wanted makes a wanted recall a
// turn shorter. Damage before then cancels it at no cost. A stunned champion cannot start one:
// the engine refuses it, and the thrown error costs ~3.9k fuel.
void start_recall(const World& world) {
    Phase phase{"start_recall"};
    auto& me = cambc::self();
    if (stunned_turn || !world.me().alive || channelling() || test(world.map().ally_spawn, my_position()))
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
    Phase phase{"prepare_walk"};
    const int g = memory.farm_group;
    if (!world.me().alive || channelling() || g < 0 || g >= static_cast<int>(world.camps.size())) return;
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
    debug_block({ home_asks = 0; });
    decide(world, pathing, safety, memory);
    debug_block({
        if (home_asks > 1) std::printf("WANTHOME %d %d\n", world.round, home_asks);
    });
    if (decision != 'W') memory.wait_altar = -1;
    // A turn without siege() (a fight, a heal) keeps the siege while our claim stays on it; a chase
    // or a bag takes us away from it.
    if (!sieged && (memory.claim != claim || decision == 'C' || bankable_bag(world, pathing) > 0)) {
        memory.siege = false;
        memory.staged_since = -1;
    }
    strike_after(world, pathing, safety);
    pathing.set_guarding(false);
    if constexpr (debug_fights)
        if (world.me().alive && !test(world.map().ally_spawn, start) && fuel_ok(end_reserve + 15000))
            if (const auto t = safety.fight(start); t.enemies > 0) log_fight("FF", world, safety, start, t);
    // The search priced heal and shield where its plan ended, not a later walk or hit by the goal.
    if (!searched || my_position() != searched_at || !my_can_attack() != searched_hit) {
        heal_ally(world); // allies in reach after walking
        shield_if_needed(world, safety, memory.claim);
    }
    place_ward(world, memory); // where we end the turn
    place_lock(world);
    start_recall(world);
    count_use(world, start, could_attack);
}

void play_turn(World& world, Pathing& pathing, Memory& memory) {
    Safety safety{world};
    pathing.set_safety(&safety);
    safety.set_claimed(memory.claim);
    const auto* record = world.me().alive ? &my_record() : nullptr;
    const float health = record ? record->health : 0;
    memory.damage = memory.round == world.round - 1 ? std::max(0.0f, memory.health - health) : 0;
    decision = '-';
    sieged = false;
    searched = false;
    siege_group() = -1;
    const int camp_hits_before = camp_hits();
    if (world.me().alive) note_upkeep(world, safety, memory.damage);
    note_hits(world, safety, memory);
    stunned_turn = record && my_stunned(cambc::champion_state::from_bits_retain(record->state));
    // A failed act still posts the claim, the bag and the health that next turn's damage reads.
    try {
        act(world, pathing, safety, memory);
    } catch (const std::exception& e) {
        std::printf("r%u act error: %s\n", cambc::round_number(), e.what());
    }
    pathing.set_safety(nullptr);
    set_turn_order(world, safety);
    comms::claim(memory.claim);
    comms::bag(world.me().alive ? static_cast<int>(my_gems()) : 0);
    memory.round = world.round;
    memory.health = world.me().alive ? my_health() : 0;
    upkeep.camp_turns += camp_hits() != camp_hits_before;
    debug_block({ std::printf("D %d %u %c %d %d\n", world.round, static_cast<std::uint32_t>(world.me().handle), decision, memory.farm_group, memory.claim); });
}

} // namespace aph
