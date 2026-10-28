// What bot.cc and the behaviour files it calls (economy/, combat/) share: the turn's state, the
// types it needs, and declarations. All one translation unit (unity.cpp), so the functions keep
// internal linkage and the compiler still inlines and drops them as it would within one file. Each
// definition is in the file named above its declaration.
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

// The turn's branch, for debug_fights: Chase, Attack, Retreat, Farm, Bank, Wait at an altar,
// Tribute kept / t cancelled, recall Kept / k cancelled, Healing on spawn, Shopping trip,
// holding (P), capture recall (Q), siege or kite of a big group (G), contest (X),
// stopping a game-ending bag (E).
char decision = '-';
bool sieged = false; // siege() ran this turn
bool stunned_turn = false; // stunned at this turn's start
bool struck = false;   // the strike search ran this turn
// The Prism-Willow support code chose this turn: the wrap-up's strike, heal, shield and recall stay out.
bool support_owned = false;
bool support_requested = false, support_offered = false, support_retreat = false;

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

// Our basic attacks and casts per slot over the game, counted at each turn's end (count_use).
struct Use {
    int attacks = 0;
    std::array<int, 2> casts{};
};
Use use;

// Our income so far, priced by best_emblem's passive emblems: gems collected (capture shares and
// kill bags), capture payouts taken part in, what a Prospector emblem would have added to them,
// base gold (before bonuses) from captures and kills, and the turn ends a Tribute emblem would have
// cut off our tributes. Gems and gold are read at each turn's start and end; `spent` is gold spent
// since the start.
struct Income {
    float gems = 0, holds = 0, prospected_gems = 0, prospected_gold = 0, capture_gold = 0, kill_gold = 0, tribute_cut = 0;
    int start_round = -1, end_round = -1;
    std::uint32_t gems_at = 0, gold_at = 0, spent = 0;
    vec2 end_pos{-1, -1};
};
Income income;

struct CampAttackTarget {
    int group, member;
    float score;
};

struct CampAttackTargets {
    std::array<CampAttackTarget, 16> found;
    int n = 0;
};

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

// altar_access's state. `ours` is kept as the walk from our spawn with access.live as walls:
// most changes update it without a flood from spawn. A first build the plan's tributes_walked
// answers leaves it unknown (`walked` false) until needed or warm_altar_walk.
struct AltarWalk {
    AltarAccess access;
    bitboard ours{cambc::uninitialized}, walls{cambc::uninitialized};
    bool walked = false;
};

bool altar_walk_pending = false; // !walked after a first build: warm_altar_walk's check, read every turn

// A farm cycle's worth a round, falling faster than 1 / rounds for long cycles: gems taken sooner
// turn into shards sooner, and a long clear is more often contested or cut short. On a large map
// every walk is long, so the horizon grows with it.
constexpr float cycle_horizon = 100;

struct CampLeft {
    float health, strength;
    int member;
    float fire; // damage a round from the strikers still alive that reach where we stand to kill it (clear_fire)
};

// Our share of the gems still to farm takes about rounds_per_gem each.
constexpr float rounds_per_gem = 2.3f;

// Our upkeep so far, over the turns we were alive: turns spent damaging camps, damage taken from
// camps and from champions, and steps from spawn (the walk back out after a heal).
struct Upkeep {
    int turns = 0, camp_turns = 0, spawn_turns = 0;
    float camp_taken = 0, champ_taken = 0, spawn_steps = 0;
};
Upkeep upkeep;

// The emblem to complete next and the share of a turn it saves (upkeep_cost): a Power emblem in
// the main stat (6 shards' stats for 5), a Jungle one in it (-30% camp damage) or a Durability one
// in Health (-10% damage taken), or a passive one (passive_saved), whichever saves most; one already
// begun is finished first, priced by the shards left to buy (`cost` in gold).
struct Emblem {
    int family, stat;
    float saved;
    unsigned cost;
    float passive = 0; // passive_saved's part of `saved`
};

// The next emblem (best_emblem), the rounds it saves us over our share of the gems still to farm,
// and the gems a gold is worth (its part of that saving). Kept while our share and stats hold: the
// upkeep counters under them move every turn, and every farm value would be rebuilt.
struct Prices {
    Emblem next;
    float gain, per_gold;
};

struct PurchaseQuote {
    Emblem next{};
    unsigned count = 0;
    float gain = 0;
};

// The way to an altar `walk` steps away, in rounds: walking, or a recall of `channel` turns
// (`overlap` of them spent anyway on a capture's remaining rounds), the heal turn when hurt (a
// recall lands at turn start and healing waits for the turn's end, free if the first step out ends
// on spawn) and the walk from the landing tile, less what
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

// economy/shop.cc
cambc::item_type emblem_of(int family, int stat);
void buy_lock();
bool carries_crystal();
bool can_buy_crystal();
void buy_crystal(const Memory& memory);
bool may_shop(const World& world);
void note_upkeep(const World& world, Safety& safety, float damage);
float spawn_steps(const World& world);
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
bool has_family(const cambc::enum_map<cambc::item_type>& owned, int family);
float camp_dealt_with(const cambc::enum_map<cambc::item_type>& owned, int added = -1);
float rate(const World& world, float worth, float rounds);
float min_camp_damage(CampLeft* left, int n, float strength, float* rounds, float reflect);
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
int prospected(int cluster, int sharers);
bool big_group(const CampGroup& G);
int holders(const CampGroup& G);
const ChampionBelief* prism_capture_holder(const World& world, const CampGroup& G);
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
