// What bot.cc and the behaviour files it calls (economy/, combat/) share: the turn's state, the
// types it needs, and declarations. All one translation unit (unity.cpp), so the functions keep
// internal linkage and the compiler still inlines and drops them as it would within one file. Each
// definition is in the file named above its declaration. The per-turn flags below are reset in play_turn.
#pragma once
#include "bot.h"
#include "model/follow.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <limits>
#include <memory>
#include <optional>
#include <span>
#include <vector>
#include "combat/abilities.h"
#include "model/comms.h"
#include "model/crew_work.h"
#include "model/enemy_reach.h"
#include "emblems.h"
#include "params.h"
#include "model/pathing.h"
#include "combat/plan.h"
#include "model/safety.h"
#include "combat/self_abilities.h"
#include "model/turn_order.h"
#include "model/world.h"
#include "draft/map_economy.h"

namespace aph {

namespace {

constexpr int endgame_margin = 20;   // rounds to spare on the last trip to an altar
constexpr int endgame_slack = 2;     // rounds to spare on a last-chance tribute

// The turn's branch: traces print its letter, and act() and farm() read it.
enum class Branch : char {
    none = '-',
    chase = 'C',
    attack = 'A',
    retreat = 'R',
    farm = 'F',
    bank = 'B',
    wait_altar = 'W',
    tribute_kept = 'T',
    tribute_cancelled = 't',
    recall_kept = 'K',
    recall_cancelled = 'k',
    mend = 'H',           // healing on spawn
    shop = 'S',           // a shopping trip
    hold = 'P',           // holding a capture
    capture_recall = 'Q',
    siege = 'G',          // siege or kite of a big group
    contest = 'X',
    stop_ender = 'E',     // stopping a game-ending bag
    willow_support = 'h', // Willow's heal or formation
    prism_recovery = 'r', // Prism's recovery beside Willow
};
Branch decision = Branch::none;
bool sieged = false;       // siege() or its heal trip ran this turn: act() keeps the siege
bool stunned_turn = false; // stunned at this turn's start
bool struck = false;       // the strike search ran this turn
bool searched = false;     // and priced every enemy we see: none its own moves revealed
// The Prism-Willow support code chose this turn: the wrap-up's strike, heal, shield and recall stay out.
bool support_owned = false;
// For the turn end's comms::support_intent: Prism waits on a heal (requested) or Willow can give
// one safely (offered). support_retreat: the support code hands the turn to retreat().
bool support_requested = false, support_offered = false, support_retreat = false;

// A tile's risk to the support pair. imminent: Safety::bound's damage with enemies yet to act
// counted twice. enemy: an enemy is likely to hit it; camp: a live or returning camp member
// reaches it; stun: an enemy may stun there.
struct SupportExposure {
    float imminent = 0;
    bool enemy = false, camp = false, stun = false;
    bool safe() const { return !enemy && !camp; }
};

// Willow's tile, or one a step away, with its exposure in the beliefs of our latest observe.
struct Station {
    vec2 p;
    SupportExposure risk;
    bool open = false; // in bounds and open_for_us
};
// Cached per origin and World::observations.
struct Stations {
    std::array<Station, 9> tiles; // ours first
    bitboard guard;               // the stations an enemy is likely to hit
    vec2 origin{-1, -1};
    std::uint32_t observations = 0;
};

// Our basic attacks and casts per slot over the game, counted at each turn's end (count_use).
struct Use {
    int attacks = 0;
    std::array<int, 2> casts{};
};
Use use;

// Our income so far, priced by best_emblem's passive emblems: gems collected (capture shares and
// kill bags), capture payouts taken part in, what a Prospector emblem would have added to them,
// base gold (before bonuses) from captures and kills, and the turn ends a Tribute emblem would have
// cut off our tributes. Gems and gold are read at each turn's start and end; `spent` is the gold
// spent since this turn's start.
struct Income {
    float gems = 0, holds = 0, prospected_gems = 0, prospected_gold = 0, capture_gold = 0, kill_gold = 0, tribute_cut = 0;
    int start_round = -1, end_round = -1;
    std::uint32_t gems_at = 0, gold_at = 0, spent = 0;
    vec2 end_pos{-1, -1};
};
Income income;

// A camp member in basic attack range; best first by `score` (camp_attack_targets).
struct CampAttackTarget {
    int group, member;
    float score;
};

struct CampAttackTargets {
    std::array<CampAttackTarget, 16> found; // the best 16
    int n = 0;
};

// `open`: the tribute tiles a walk from our spawn reaches with the `live` camps as walls, or a
// crystal hop from it. With none, `opened` holds the tribute tiles those camps cut off and `blocks`
// the groups beside our walk on the same side as them: a thicker wall of camps opens a layer at a
// time. Otherwise `opened` is `open`. `camp_hopped`: none is open but a camp hop's, whose ring
// still seals them (altars_sealed): the hop banks while a siege may yet open a walk.
struct AltarAccess {
    bitboard live, open, opened;
    bool any_open = false, camp_hopped = false;
    std::vector<int> blocks;
    int version = 0;              // bumped on each rebuild
    std::uint32_t live_flips = 0; // Pathing::live_flips() at the last build
};

// altar_access's state. `ours` is kept as the walk from our spawn with access.live as walls (`walls`
// is scratch): most camp changes update it without a flood from spawn. A first build that
// StaticMap::tributes_walked answers leaves it unknown (`walked` false) until needed or
// prepare_next_turn floods it with spare fuel.
struct AltarWalk {
    AltarAccess access;
    bitboard ours{cambc::uninitialized}, walls{cambc::uninitialized};
    bool walked = false;
};

// Built but not walked: prepare_next_turn's every-turn check, without touching altar_walk()'s static.
bool altar_walk_pending = false;

// rate()'s horizon: a farm cycle's worth a round falls faster than 1 / rounds for long cycles, as
// gems taken sooner turn into shards sooner, and a long clear is more often contested or cut short.
// Scaled up by the map's larger side over 50, since on a large map every walk is long.
float cycle_horizon(const StaticMap& map) { return 100 * std::max(1.0f, static_cast<float>(std::max(map.width, map.height)) / 50.0f); }

// Our share of the gems still to farm takes about rounds_per_gem each.
constexpr float rounds_per_gem = 2.3f;

// Our upkeep so far, over the turns we were alive: turns spent damaging camps, damage taken from
// camps and from champions, and steps from spawn (the walk back out after a heal).
struct Upkeep {
    int turns = 0, camp_turns = 0, spawn_turns = 0;
    float camp_taken = 0, champ_taken = 0, spawn_steps = 0;
};
Upkeep upkeep;

// The emblem to complete next (best_emblem) and the share of a turn it saves (upkeep_cost), its
// passive's part included. One already begun is finished first; `cost` is the gold for the shards
// left to buy.
struct Emblem {
    int family, stat;
    float saved;
    unsigned cost;
    float passive = 0; // passive_saved's part of `saved`
};

// The next emblem (best_emblem), the rounds it saves us over our share of the gems still to farm,
// and the gems a gold is worth (its part of that saving). Kept while our share and stats hold, not
// keyed on the upkeep counters under them: those move every turn, and every farm value would be
// rebuilt.
struct Prices {
    Emblem next;
    float gain, per_gold;
};

// What affordable_prefix's gold buys: the first emblem it works on, the shards, and the rounds saved.
struct PurchaseQuote {
    Emblem next{};
    unsigned count = 0;
    float gain = 0;
};

// The way to an altar `walk` steps away, in rounds: the walk, or a recall less what the stop is
// worth, whichever is shorter. The recall takes `channel` turns (`overlap` of them spent anyway on a
// capture's remaining rounds), then `hurt`, the heal turn (a recall lands at turn start and healing
// waits for a turn end on spawn, free if the first step out ends on spawn), then `from_spawn`, the
// walk from the landing tile. The stop is worth the heal, and the next emblem once `gold_in` more
// gold completes it; nothing once the bag wins or the end is close. Never a recall that reaches the
// altar after `deadline`, too late to tribute the bag.
struct HomeTrip {
    int channel, from_spawn, hurt, deadline;
    float heal = 0, emblem = 0;
    std::uint32_t short_gold = ~0u; // gold still needed for the emblem; never reached by default
    float value(std::uint32_t gold_in) const { return heal + (gold_in >= short_gold ? emblem : 0.0f); }
    float rounds(int walk, int overlap, std::uint32_t gold_in) const {
        const int arrive = std::max(0, channel - overlap) + hurt + from_spawn;
        if (from_spawn == unreachable || arrive > deadline) return static_cast<float>(walk);
        return std::min(static_cast<float>(walk), std::max(0.0f, static_cast<float>(arrive) - value(gold_in)));
    }
};

// Empty-handed, the way to a group by way of spawn, in rounds: the recall's `channel`, `hurt` (the
// heal turn), the walk `out` from spawn and any wait for its respawn `respawn` rounds away, less
// `value`, what the stop is worth as HomeTrip prices it (the heal, and the next emblem if our gold
// completes it). Never below the channel.
struct FarmRecall {
    int channel = 0, hurt = 0;
    float value = 0;
    float rounds(int out, int respawn) const {
        if (out == unreachable) return static_cast<float>(unreachable);
        const int arrive = std::max(channel + hurt + out, respawn);
        return std::max(static_cast<float>(channel), static_cast<float>(arrive) - value);
    }
    // rounds() when sooner than the walk of `walk` steps, else unreachable. Not when the walk too
    // arrives before the respawn (the recall only waits it out, and walking keeps us free to act),
    // nor for a wait farm would not take.
    float sooner(int out, int respawn, int walk) const {
        if (out == unreachable || walk == unreachable || respawn >= walk || respawn - (channel + hurt + out) > params::max_wait)
            return static_cast<float>(unreachable);
        const float via = rounds(out, respawn);
        return via < static_cast<float>(walk) ? via : static_cast<float>(unreachable);
    }
};

// economy/shop.cc
cambc::item_type emblem_of(int family, int stat);
void buy_lock();
bool carries_crystal();
bool can_buy_crystal();
void buy_crystal(const Memory& memory);
bool shops_at_home(const World& world);
void note_upkeep(const World& world, Safety& safety, float damage);
float heal_rounds(const World& world, float damage, float gap, float out);
float heal_rounds_now(const World& world);
bool buy_shards(const World& world);
float gold_rate(const ChampionFacts& f, const cambc::enum_map<cambc::item_type>& owned);
float gold_paid(const World& world);
float gold_paid(const ChampionBelief& a);
const Prices& prices(const World& world);
PurchaseQuote affordable_prefix(const World& world, unsigned gold_in = 0);
HomeTrip home_trip(const World& world, Pathing& pathing, int channel, bool wins);
FarmRecall farm_recall(const World& world, Pathing& pathing, int channel);
void note_income_start(const World& world);
void note_income_end(const World& world);
bool wants_shop(const World& world, Pathing& pathing, Safety& safety, const Memory& memory);

// economy/home.cc
float home_room(const ChampionBelief& c);
float home_survivable(const ChampionBelief& c);
float home_room(const World& world, Safety& safety);
float heal_trip(int channel, float gap, float out);
float heal_trip(const World& world, float gap, float out);
int walk_home_limit(int channel);
bool walk_home_beats(int steps, int channel);
bool walk_beats_recall(const World& world, Pathing& pathing, Safety& safety, int channel);
bool camps_reach_spawn(const World& world);
const bitboard& home_board(const World& world, Safety& safety);
float phase_fire(const World& world, Safety& safety, vec2 p, int wake);
bool home_stands(const World& world, Pathing& pathing, Safety& safety, const bitboard& tiles, int wake, bitboard& out);
void home_tiles(const World& world, Pathing& pathing, Safety& safety, bitboard& out);
bool home_stands_near(const World& world, Pathing& pathing, Safety& safety, int g, int range, bitboard& out);
void home_exits(const World& world, Safety& safety, bitboard& goals);
int home_exit_steps(const World& world, Pathing& pathing, Safety& safety, vec2 p, int longest);
bool mend_hit(const World& world, const Memory& memory);

// economy/camps.cc
template <class Allowed> CampAttackTargets camp_attack_targets(const World& world, Allowed allowed, CampAttackTargets* resources = nullptr);
bool attack_camp_target(const World& world, const CampAttackTarget& target);
int attack_camp_targets(const World& world, const CampAttackTargets& targets);
template <class Allowed> int attack_camp(const World& world, Allowed allowed);
bool breach(const World& world, const Field& field);
float camp_output(const ChampionBelief& c);
float rate(const World& world, float worth, float rounds);
float min_camp_damage(const World& world, int g, float strength, float* rounds, float reflect = 0, int range = -1, float survivable = -1);
std::uint64_t home_reach(const World& world, int g, int range);
int home_gap(const StaticMap& map, int g, int range);
float home_free(const World& world, int g, int range, float survivable);
float shielded_clear(float damage, float rounds, float shield, float ready_in = 0);
float home_ground(const StaticMap& map, int g, bool first_turn);
float home_side(const StaticMap& map, int g, bool first_turn);
float spell_output(const ChampionBelief& c);
float basic_output(const ChampionBelief& c);
float spell_clear_rounds(const StaticMap& map, int g, const CampBelief& belief, int range, float spells, float basic);
float spell_clear_rounds(const World& world, int g, int range, float spells, float basic);
float fastest_clear(const World& world, int g, float strength);
float reflected_clear(const World& world, int g, float strength, float reflect);
float gems_share(const World& world);
bool awake_over(const World& world, int g, vec2 p);
bool finishing_camp(const World& world);
bool finishing_camp(const World& world, vec2 p); // as if we stood at p

// combat/guard.cc
void step_safely(const World& world, Pathing& pathing, const Field& field, Safety& safety);
bool own_ground(const World& world, vec2 p);
void forget_pack_zone(const World& world);
bool in_pack_zone(const World& world, Safety& safety, vec2 p);
const bitboard* pack_zone(const World& world, Safety& safety);
bool pack_covers(const World& world, Safety& safety, vec2 p, int r);
void guard_steps(const World& world, Pathing& pathing, Safety& safety);
void guard_work(const World& world, Pathing& pathing, Safety& safety, float damage);
void strike_guard_known(const Pathing& pathing, vec2 here);

// combat/fight.cc
bool attack_enemy(const World& world);
float recall_line(const World& world, Safety& safety);
float recall_line(const World& world, Safety& safety, vec2 p);
int hold_rounds(const World& world, Pathing& pathing, vec2 p);
bool hold_outlasts(Safety& safety, float damage, vec2 p, int rounds);
bool paying_soon(const World& world, Safety& safety, vec2 p, int turns);
bool want_home(const World& world, Pathing& pathing, Safety& safety, const Memory& memory);
// want_home's recall line and pack zone (drawn_home) at p, as if we stood there with last round's loss `damage`.
bool drawn_home_at(const World& world, Pathing& pathing, Safety& safety, vec2 p, float damage);
const ChampionBelief* prey(const World& world, Safety& safety);
vec2 chase_aim(const World& world, Safety& safety);
bool chase(const World& world, Pathing& pathing, Safety& safety);
const ChampionBelief* stoppable_winning_tribute(const World& world, Pathing& pathing);
bool ally_stops(const World& world, const ChampionBelief& e);
const ChampionBelief* game_ender(const World& world, Pathing& pathing);
void stop_game_ender(const World& world, Pathing& pathing, Memory& memory, const ChampionBelief& e);
void retreat(World& world, Pathing& pathing, Safety& safety, Memory& memory);

// economy/bank.cc
bool channelling();
void place_lock(const World& world);
// Turns to break the altar's believed enemy lock, about a step each: one per hit left.
inline int lock_turns(const AltarBelief& belief) {
    if (!belief.enemy_lock) return 0;
    return belief.enemy_lock_hits > 0 ? belief.enemy_lock_hits : static_cast<int>(cambc::constants::altar_lock_hits);
}
int tribute_turns(int gems, bool fast);
int tribute_turns(const World& world, int gems);
int recall_turns(const World& world);
vec2 recall_landing(const World& world);
int rounds_left(const World& world);
int gems_short(const World& world, int horizon = static_cast<int>(cambc::constants::max_rounds));
const ChampionBelief* partner(const World& world);
int bag_at_stake(const World& world);
AltarWalk& altar_walk();
void flood_altar_walk(const World& world, Pathing& pathing, AltarWalk& w);
const AltarAccess& altar_access(const World& world, Pathing& pathing);
bool sealed_in(const World& world, Pathing& pathing, vec2 p);
bool wake_ring(const World& world, Pathing& pathing, Safety& safety);
int altar_steps(const World& world, Pathing& pathing, vec2 p, int altar);
int bankable_bag(const World& world, Pathing& pathing);
bool altars_sealed(const World& world, Pathing& pathing);
bool seals(const World& world, const AltarAccess& access, int g);
bool winning_bag(const World& world);
int bag_rounds_left(const World& world);
bool closing(const World& world, Pathing& pathing);
bool retaining_gems(const World& world, Pathing& pathing);
bool banks_bag(const World& world, Pathing& pathing);
bool take_hop(const World& world, Pathing& pathing, Safety& safety, const Memory& memory, int h, const Field* goal = nullptr, bool bold = false);
void bank_gems(World& world, Pathing& pathing, Safety& safety, Memory& memory, bool heal_step = true);
bool can_tribute_here(const World& world);
int carried_locks();
int tribute_altar(const World& world, vec2 p);
bool can_tribute_safely(const World& world, Pathing& pathing, Safety& safety, const Memory& memory);
bool recall_outruns(const World& world, Safety& safety, int turns = -1);
bool recall_to_farm(const World& world, Pathing& pathing, Safety& safety, const Memory& memory, int g);
bool continue_tribute(const World& world, Pathing& pathing, Safety& safety, Memory& memory, std::optional<bool>& home);
bool continue_recall(const World& world, Pathing& pathing, Safety& safety, Memory& memory, std::optional<bool>& home, int recall_farm);
void carry_bag(World& world, Pathing& pathing, Safety& safety, Memory& memory, bool attacked, const Pathing::GuardState& chase_guard);

// economy/capture.cc
int capture_rounds(bool fast);
int capture_rounds(const World& world);
int allies_on(const World& world, const bitboard& tiles, int below = 1 << 30);
bool enemy_on(const World& world, const bitboard& tiles);
int prospected(int cluster, int sharers, bool lowest = false);
bool big_group(const CampGroup& G);
int holders(const CampGroup& G);
const ChampionBelief* sole_capture_holder(const World& world, const CampGroup& G);
const ChampionBelief* value_holder(const World& world, const CampGroup& G);
bool outvalues_holders(const World& world, const CampGroup& G);
bool takes_over(const World& world);
bool may_take_over(const World& world, const CampGroup& G);
float takeover_gain(const World& world, const CampGroup& G, int& timer);
float takeover_worth(float gain, int timer, int walk, float work_rate, int& hold);
bool holding_capture_now(const World& world, Pathing& pathing, vec2 here);
bool holding_capture(const World& world, Pathing& pathing);
bool contest_manned(const World& world, int g, vec2 here);
bool yield_capture(const World& world, Pathing& pathing, Safety& safety, Memory& memory);
bool join_marcella_capture(const World& world, Pathing& pathing, Safety& safety, Memory& memory);
bool take_capture_handoff(const World& world, Pathing& pathing, Safety& safety, Memory& memory);
bool ally_engaged(const World& world, int group);
bool contesting(const World& world);
bool capture_recall(const World& world, Pathing& pathing, Safety& safety, Memory& memory);
int enemy_hold_left(const World& world, const CampBelief& c);
bool capture_taken(const World& world, Pathing& pathing, int g, vec2 here);
bool ally_claims(const World& world, int g);
const bitboard& free_tiles(const bitboard& tiles);
bool contest_capture(const World& world, Pathing& pathing, Memory& memory);
void hold_capture(const World& world, Memory& memory, bool attacked);

// economy/crew.cc
// A crew's clear of a group: its camp output (ours included), its camp damage before anyone's
// emblems and rounds at that output, its tank now (crew_tank), our part of the damage as the tank's
// turn passes from member to member (share_damage), and the extra trips home that costs the crew.
// `claimers` count the allies claiming it; `expected` the available allies counted in as well.
struct CrewPlan {
    float output = 0, damage = 0, rounds = 0, my_damage = 0;
    const ChampionBelief* tank = nullptr; // debug builds only, for the traces
    int trips = 0, claimers = 0, n_expected = 0;
    std::array<int, 8> expected{};
};
// What plan_crew, share_damage and crew_available read of each ally, read once for a farm call
// (nothing in its loop changes them), in ally order; the costlier parts on first need.
// `line` is the recall line plans are priced at.
struct CrewAllies {
    struct Ally {
        const ChampionBelief* a;
        int claim;
        bool seen; // another living ally whose claim counts (plan_crew's claimers)
        mutable bool has_output, has_avail, has_pool;
        mutable float output_;                                   // camp_output
        mutable float score, weight, taken, budget, usable;      // share_damage's pool entry
        // crew_available: 0 never, 1 unless it claims the group, 2 by the distances below.
        mutable std::uint8_t avail;
        mutable bool harmless_claim, on_cleared;
        mutable vec2 claim_centre, on_centre;
    };
    std::array<Ally, 16> at;
    int n = 0;
    float line = 0, my_hp = 0, my_max = 0;
    vec2 here{};
};
float crew_output(const CrewAllies::Ally& a);
void crew_allies(const World& world, float line, CrewAllies& out);
float crew_taken(const ChampionBelief& a);
float crew_budget(float health, float max_health, float line);
float crew_usable(float max_health, float line);
int extra_trips(float damage, float budget, float usable);
int crew_arrival(const World& world, const ChampionBelief& a, int g, vec2 p); // from p, a's position
bool crew_in_reach(const World& world, int g, vec2 p, int range);
// Of us and the allies in sight claiming `group` (with `extra`, allies counted in whether seen or
// not): the one with the most health above crew_tank_line per camp damage taken, x1.5 melee; ties
// to the lower index.
const ChampionBelief* crew_tank(const World& world, int group, std::span<const int> extra = {});
bool crew_available(const World& world, const CrewAllies& allies, const CrewAllies::Ally& a, int g);
void share_damage(const World& world, const CrewAllies& allies, int g, CrewPlan& p);
// With `expect`, available allies join nearest first while each saves the crew a trip home, up to
// `cap` bodies.
CrewPlan plan_crew(const World& world, const CrewAllies& allies, int g, float my_output, bool expect, int cap = params::crew_cap);
// A Monolith group farm works as a crew operation: off Monolith-only maps (siege's there).
bool farm_monolith(const World& world, int g);
// Our claim is farm's Monolith operation and another member in sight stands in its reach: once we
// step out of reach far enough it is nearer and takes the hits. Then whether we are trapped
// (camp_trapped's role): while the hits until then, and one more, would take us to 0. -1 otherwise.
int mono_trapped(const World& world, Pathing& pathing, Safety& safety, const Memory& memory, float health);

// economy/farm.cc
int walk_range(const World& world, int g);
bool beyond_walk(const World& world, Pathing& pathing, int g);
int steps_to(const CampGroup& G, vec2 p);
int walk_to(const World& world, Pathing& pathing, int g, vec2 p);
int team_walk_to(const World& world, Pathing& pathing, int g, vec2 p);
bool farm(World& world, Pathing& pathing, Safety& safety, Memory& memory);
float farm_step_value(const World& world);

// economy/siege.cc
bool siege(const World& world, Pathing& pathing, Safety& safety, Memory& memory);
bool kite(const World& world, Pathing& pathing, Memory& memory);
bool kites_with_spells(const ChampionBelief& c);
bool kite_owns(const World& world, int g);
bool siege_declines(const World& world, int g);

// combat/support.cc
const Stations& stations(const World& world, Safety& safety, vec2 here);
SupportExposure exposure_here(const World& world, Safety& safety);
const ChampionBelief* support_endpoint(const World& world, bool healer);
bool willow_bank_heal_step(World& world, Pathing& pathing, Safety& safety, const Field& field);
bool willow_independent_heal_step(World& world, Pathing& pathing, Safety& safety, int farm_group);
bool support_work(const World& world, Pathing& pathing, Safety& safety, const Memory& memory);
bool local_support(World& world, Pathing& pathing, Safety& safety, Memory& memory, bool leave, bool& mate_eligible);

// bot.cc
void log_fight(const char* tag, const World& world, Safety& safety, vec2 p, const Trade& t, int target = -1);
bool place_ward(const World& world, Memory& memory, bool bushes = true);
void see_again(World& world, Pathing& pathing, Safety& safety);
void see_stuns(World& world, Safety& safety);
bool see_revealed(World& world, Pathing& pathing, Safety& safety);

} // namespace

} // namespace aph
