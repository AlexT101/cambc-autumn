// What bot.cc and the behaviour files it calls (economy/, combat/) share: the turn's state, the
// types it needs, and declarations. All one translation unit (unity.cpp), so the functions keep
// internal linkage and the compiler still inlines and drops them as it would within one file. Each
// definition is in the file named above its declaration. The per-turn flags below are reset in play_turn.
#pragma once
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
#include "combat/abilities.h"
#include "model/comms.h"
#include "model/crew_work.h"
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

// The turn's branch, for traces; act() also reads it. Chase, Attack, Retreat, Farm, Bank, Wait at
// an altar, Tribute kept / t cancelled, recall Kept / k cancelled, Healing on spawn, Shopping trip,
// holding (P), capture recall (Q), siege or kite of a big group (G), contest (X), stopping a
// game-ending bag (E), Willow's heal or formation (h), Prism's recovery beside Willow (r).
char decision = '-';
bool sieged = false;       // siege() or its heal trip ran this turn: act() keeps the siege
bool stunned_turn = false; // stunned at this turn's start
bool struck = false;       // the strike search ran this turn
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
    std::array<CampAttackTarget, 16> found; // past 16, later tiles in scan order are dropped unranked
    int n = 0;
};

// `open`: the tribute tiles a walk from our spawn reaches with the `live` camps as walls, or a
// crystal hop from it. With none, `opened` holds the tribute tiles those camps cut off and `blocks`
// the groups beside our walk on the same side as them: a thicker wall of camps opens a layer at a
// time. Otherwise `opened` is `open`.
struct AltarAccess {
    bitboard live, open, opened;
    bool any_open = false;
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

// economy/shop.cc
cambc::item_type emblem_of(int family, int stat);
void buy_lock();
bool carries_crystal();
bool can_buy_crystal();
void buy_crystal(const Memory& memory);
bool shops_at_home(const World& world);
void note_upkeep(const World& world, Safety& safety, float damage);
float heal_rounds(const World& world, float damage, float out);
float heal_rounds_now(const World& world);
bool buy_shards(const World& world);
float gold_rate(const ChampionFacts& f, const cambc::enum_map<cambc::item_type>& owned);
float gold_paid(const World& world);
float gold_paid(const ChampionBelief& a);
const Prices& prices(const World& world);
PurchaseQuote affordable_prefix(const World& world, unsigned gold_in = 0);
HomeTrip home_trip(const World& world, Pathing& pathing, int channel, bool wins);
void note_income_start(const World& world);
void note_income_end(const World& world);
bool wants_shop(const World& world, Pathing& pathing, Safety& safety, const Memory& memory);

// economy/camps.cc
template <class Allowed> CampAttackTargets camp_attack_targets(const World& world, Allowed allowed, CampAttackTargets* resources = nullptr);
bool attack_camp_target(const World& world, const CampAttackTarget& target);
int attack_camp_targets(const World& world, const CampAttackTargets& targets);
template <class Allowed> int attack_camp(const World& world, Allowed allowed);
bool breach(const World& world, const Field& field);
float camp_output(const ChampionBelief& c);
float camp_dealt_with(const cambc::enum_map<cambc::item_type>& owned, int added = -1);
float rate(const World& world, float worth, float rounds);
float min_camp_damage(const World& world, int g, float strength, float* rounds, float reflect = 0, int range = -1);
float shielded_clear(float damage, float rounds, float shield);
float home_ground(const StaticMap& map, int g, bool first_turn);
float spell_output(const ChampionBelief& c);
float basic_output(const ChampionBelief& c);
float spell_clear_rounds(const StaticMap& map, int g, const CampBelief& belief, int range, float spells, float basic);
float spell_clear_rounds(const World& world, int g, int range, float spells, float basic);
float fastest_clear(const World& world, int g, float strength);
float reflected_clear(const World& world, int g, float strength, float reflect);
float gems_share(const World& world);
bool awake_over(const World& world, int g, vec2 p);
bool finishing_camp(const World& world);

// combat/guard.cc
void step_safely(const World& world, Pathing& pathing, const Field& field, Safety& safety);
bool own_ground(const World& world, vec2 p);
void forget_pack_zone(const World& world);
bool in_pack_zone(const World& world, vec2 p);
const bitboard* pack_zone(const World& world);
bool pack_covers(const World& world, vec2 p, int r);
void guard_steps(const World& world, Pathing& pathing, Safety& safety);

// combat/fight.cc
bool attack_enemy(const World& world);
bool want_home(const World& world, Pathing& pathing, Safety& safety, const Memory& memory);
const ChampionBelief* prey(const World& world, Safety& safety);
bool chase(const World& world, Pathing& pathing, Safety& safety);
const ChampionBelief* stoppable_winning_tribute(const World& world);
bool ally_stops(const World& world, const ChampionBelief& e);
const ChampionBelief* game_ender(const World& world);
void stop_game_ender(const World& world, Pathing& pathing, Memory& memory, const ChampionBelief& e);
void retreat(World& world, Pathing& pathing, Safety& safety, Memory& memory);

// economy/bank.cc
bool channelling();
void place_lock(const World& world);
int tribute_turns(int gems, bool fast);
int tribute_turns(const World& world, int gems);
int recall_turns(const World& world);
vec2 recall_landing(const World& world);
int rounds_left(const World& world);
int gems_short(const World& world);
const ChampionBelief* partner(const World& world);
int bag_at_stake(const World& world);
AltarWalk& altar_walk();
void flood_altar_walk(const World& world, Pathing& pathing, AltarWalk& w);
const AltarAccess& altar_access(const World& world, Pathing& pathing);
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
bool recall_outruns(const World& world, Safety& safety);
bool continue_tribute(const World& world, Pathing& pathing, Safety& safety, Memory& memory, std::optional<bool>& home);
bool continue_recall(const World& world, Pathing& pathing, Safety& safety, Memory& memory, std::optional<bool>& home);
void carry_bag(World& world, Pathing& pathing, Safety& safety, Memory& memory, bool attacked);

// economy/capture.cc
int capture_rounds(bool fast);
int capture_rounds(const World& world);
int allies_on(const World& world, const bitboard& tiles, int below = 1 << 30);
bool enemy_on(const World& world, const bitboard& tiles);
int prospected(int cluster, int sharers, bool lowest = false);
bool big_group(const CampGroup& G);
int holders(const CampGroup& G);
const ChampionBelief* sole_capture_holder(const World& world, const CampGroup& G);
bool holding_capture(const World& world, Pathing& pathing);
bool contest_manned(const World& world, int g, vec2 here);
bool yield_capture(const World& world, Pathing& pathing, Safety& safety, Memory& memory);
bool join_marcella_capture(const World& world, Pathing& pathing, Safety& safety, Memory& memory);
bool take_capture_handoff(const World& world, Pathing& pathing, Safety& safety, Memory& memory);
bool ally_engaged(const World& world, int group);
bool contesting(const World& world);
bool capture_recall(const World& world, Pathing& pathing, Safety& safety, Memory& memory);
int enemy_hold_left(const World& world, const CampBelief& c);
bool capture_taken(const World& world, int g, vec2 here);
bool ally_claims(const World& world, int g);
const bitboard& free_tiles(const bitboard& tiles);
bool contest_capture(const World& world, Pathing& pathing, Memory& memory);
void hold_capture(const World& world, Memory& memory, bool attacked);

// economy/farm.cc
int walk_range(const World& world, int g);
bool beyond_walk(const World& world, Pathing& pathing, int g);
int steps_to(const CampGroup& G, vec2 p);
bool farm(World& world, Pathing& pathing, Safety& safety, Memory& memory);
float farm_step_value(const World& world);

// economy/siege.cc
bool siege(const World& world, Pathing& pathing, Memory& memory);
bool kite(const World& world, Pathing& pathing, Memory& memory);
bool kites_with_spells(const ChampionBelief& c);

// combat/support.cc
const Stations& stations(const World& world, Safety& safety, vec2 here);
SupportExposure exposure_here(const World& world, Safety& safety);
const ChampionBelief* support_endpoint(const World& world, bool healer);
bool willow_bank_heal_step(World& world, Pathing& pathing, Safety& safety, const Field& field);
bool willow_independent_heal_step(World& world, Pathing& pathing, Safety& safety);
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
