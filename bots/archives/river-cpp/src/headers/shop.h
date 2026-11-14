#pragma once

#include "../params.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <limits>
#include <memory>
#include <optional>
#include <span>
#include <vector>

namespace aph {
class World;
class Pathing;
}
namespace aph {
namespace {
struct Upkeep;
struct Build;
struct Emblem;
struct Prices;
struct PurchaseQuote;
}
}
namespace aph {
struct ChampionFacts;
class Safety;
struct Aims;
}

namespace aph {
namespace {
enum Family { monster, power, durability, treasure, jungle, home, bruiser };

enum StatKind { strength_stat, focus_stat, health_stat };

cambc::item_type shard_of(int family, int stat);

cambc::item_type emblem_of(int family, int stat);

// Focus when a shard's Focus, over our damaging casts so far (landings too, as raw_output counts
// them), beats its Strength over our basic attacks; until both have happened, over the damage
// spells' multipliers against the basic attacks in one cooldown (one a round, plus the reset's).
// Ren's retaliation also scales with Focus, and where big groups fall to spells from out of reach
// (kite), every spell's Focus counts.
int main_stat(const World& world);

bool buy(cambc::item_type shard, unsigned count);

// Locks on our own and middle altars keep the enemy's bags from scoring there until broken.
void buy_lock();

bool carries_crystal();

bool can_buy_crystal();

// When a hop to an altar only a crystal reaches (StaticMap::hops) beats walking from our spawn to
// the nearest altar: a fact of the map, worked out once.
void buy_crystal(const World& world, Pathing& pathing);

bool has_family(const cambc::enum_map<cambc::item_type>& owned, int family);

// Our share of the gems still to farm takes about rounds_per_gem each.
constexpr float rounds_per_gem = 2.3f;

// Our share of the gems still to farm before either team reaches the win or the game ends, at the
// team's tribute rate and at our own pace.
float gems_share(const World& world);

// Our upkeep so far, over the turns we were alive: turns spent damaging camps, damage taken from
// camps and from champions, and steps from spawn (the walk back out after a heal).
struct Upkeep {
    int turns = 0, camp_turns = 0, spawn_turns = 0;
    float camp_taken = 0, champ_taken = 0, spawn_steps = 0;
};

Upkeep upkeep;

// At the turn's start: camps hit in the camp phase, from where we ended last turn.
void note_upkeep(const World& world, Safety& safety, float damage);

// A Treasure, Jungle, Power, Durability or Bruiser shard short of its emblem (Vendetta's Monster too).
bool emblem_begun(const World& world);

// Our stats, damage taken (Jungle and Durability), and camp damage dealt (Monster).
struct Build {
    float strength = 0, focus = 0, max_health = 0, camp_taken = 1, taken = 1, camp_dealt = 1;
    int recall = static_cast<int>(cambc::constants::recall_time);
};

void add_shards(Build& b, const ChampionFacts& f, int stat, float shards);

// What completing an emblem adds beyond its shards: Power a sixth shard, Bruiser one of each other stat.
void add_completion(Build& b, const ChampionFacts& f, int family, int stat);

// Where every gem is behind a siege, our upkeep before a camp has hit us: every turn on the nearest
// Monolith, alongside the others' output (`others`), its hits on the nearest of us (the melee while
// any lives) split by max health, the walk out its distance from spawn.
Upkeep siege_upkeep(const World& world, float& others);

// Rounds a turn of ours costs in clearing and heal trips at upkeep u, with build b: the clearing
// share shrinks with our output (beside the others' on the same camps), as do the camps' hits taken
// meanwhile; health lost comes back by a recall and the walk out, a trip per usable health (above
// the recall line).
float upkeep_cost(const World& world, const Upkeep& upkeep, float others, const Build& now, const Build& b);

// Our mean steps from spawn while alive: the walk back out after a heal.
float spawn_steps();

// Rounds `damage` costs, priced as upkeep_cost prices it: a heal trip (a recall and the walk `out`
// back out) per usable health.
float heal_rounds(const World& world, float damage, float out);

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
Emblem best_emblem(const World& world, const Build& bought = {}, const cambc::enum_map<cambc::item_type>* items = nullptr);

// True if any shard was bought.
bool buy_shards(const World& world);

// Gold paid to us per base gold of a capture: the Treasure and Vesper Vale bonuses add.
float gold_paid(const World& world);

// The next emblem (best_emblem), the rounds it saves us over our share of the gems still to farm,
// and the gems a gold is worth (its part of that saving). Kept while our share and stats hold: the
// upkeep counters under them move every turn, and every farm value would be rebuilt.
struct Prices {
    Emblem next;
    float gain, per_gold;
};

const Prices& prices(const World& world);

struct PurchaseQuote {
    Emblem next{};
    unsigned count = 0;
    float gain = 0;
};

// Everything `gold_in` more gold buys, as buy_shards buys it, and the rounds it saves us over our
// share of the gems still to farm. The saving is kept while our gold and stats hold.
PurchaseQuote affordable_prefix(const World& world, unsigned gold_in = 0);

// With an empty bag, the gold to complete the next emblem goes home to shop, riding a recall unless walking is
// quicker.
[[gnu::flatten]] bool wants_shop(const World& world, Pathing& pathing, Safety& safety, const Aims& aims);

}
}
namespace aph {
float camp_hit_factor();

float camp_dealt_factor();

}
