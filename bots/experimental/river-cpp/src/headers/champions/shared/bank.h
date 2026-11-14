#pragma once

#include "../../../params.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <limits>
#include <memory>
#include <optional>
#include <span>
#include <vector>
#include "../../comms.h"

namespace aph {
struct ChampionBelief;
class World;
class Pathing;
}
namespace aph {
namespace {
struct AltarAccess;
struct HopRoute;
struct HomeTrip;
}
}
namespace aph {
class Safety;
struct Aims;
}

namespace aph {
namespace {
// By altar, the round we learned our team locks it (placed, or refused as already locked): update_altars
// sees only locks in sight. Its belief is trusted again once the altar is seen after that round.
std::vector<int> own_lock_round;

[[gnu::flatten]] void place_lock(const World& world);

bool break_lock(const World& world, int altar);

// A believed lock can be gone: break_lock's last hit, or an old sighting of an altar out of view at turn start.
bool enemy_lock_live(vec2 p);

// A tribute channel cannot act, and a kill takes the whole bag: start or keep one only if the
// visible enemies could not kill us within the next few turns, nor damage at the rate of the last
// round (attackers in bushes stay unseen). Judged again every turn of the channel, which is
// cancelled once a threat comes that close: a long bag's whole channel would wait on any enemy in sight.
bool tribute_safe(Safety& safety, const Aims& aims, int turns);

int tribute_turns(int gems);

int recall_turns(const World& world);

int rounds_left(const World& world);

// Tavi shops anywhere: no trip home for it.
bool may_shop(const World& world);

// Gems still to capture, beyond the bag and the tributes allies in sight are channelling, before
// our tributes reach the win.
int gems_short(const World& world);

const ChampionBelief* partner(const World& world);

// What a death would hand over: both bags for Cassi and Issac (an unseen partner's as posted).
int bag_at_stake(const World& world);

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
void dilate_into(const bitboard& b, bitboard& out);

const AltarAccess& altar_access(const World& world, Pathing& pathing);

// The camp damage a phase on the best open tribute tile, from the members believed awake: an asleep
// one wakes only when damaged. Huge with no open tile.
float access_fire(const World& world, const AltarAccess& a);

// A tribute of `bag` on an open tribute tile ends before the camps' fire there takes `health`.
bool altar_usable(const World& world, Pathing& pathing, int bag, float health);

// The bag a tribute could score: one no altar is usable for is held back, and we farm and shop as
// if empty-handed.
int bankable_bag(const World& world, Pathing& pathing);

// No altar is usable for the team's largest bag (an unseen ally's as posted).
bool altars_sealed(const World& world, Pathing& pathing);

// While the altars are sealed, a live group whose clear opens a walk to one, or with a member
// believed awake in reach of one, seals them.
bool seals(const World& world, const AltarAccess& access, int g);

// Tributing the bag wins: more gems are worth nothing, only the tribute is.
bool winning_bag(const World& world);

// Rounds until the team, at its recent tribute rate, has the rest of the win beyond our score and
// the team's bags (as seen, else as posted through comms): our bag banked later than that only delays the win.
int race_left(const World& world);

// The rounds left in the game for a bag: to the round limit, and for ours to the race's end.
int bag_rounds_left(const World& world);

// The bag needs the rest of the game, or of the race (the rest of the win comes without it), to
// reach an altar and score: it goes straight there.
bool closing(const World& world, Pathing& pathing);

bool retaining_gems(const World& world, Pathing& pathing);

// A tribute started or kept now is the bag's last chance to score, or wins the game while fleeing
// gives the enemy time to win first: take it at any risk. Not a long winning channel: standing
// that long beside an enemy hands it the bag, so it waits for a safe window like any other.
bool any_risk(const World& world, int channel_turns);

// A channel still running at the round limit scores nothing.
bool tribute_ok(const World& world, Safety& safety, const Aims& aims, int turns);

// An enemy in sight could strike the altar's tribute tiles: tribute there is judged again, and banking
// counts it as altar_switch_steps farther. (Unseen enemies may stand near any altar.)
bool covered(const World& world, vec2 altar);

// At an unlocked altar in reach. The caller judged the turn's start tile safe; anywhere else, at a
// covered altar, or at one believed locked (the caller skipped it), is judged again.
bool submit_here(const World& world, Safety& safety, Aims& aims);

// The quickest bank by a crystal (StaticMap::hops): the walk to a source, the channel, the walk from
// the nearest landing and the recall out, as no walk leaves the pocket. Not to `exclude`.
struct HopRoute {
    int hop = -1;
    int steps = unreachable;
};

HopRoute hop_route(const World& world, Pathing& pathing, Safety& safety, int exclude = -1);

// Towards the hop's sources; on one, the crystal to the free landing nearest its altar.
void take_hop(const World& world, Pathing& pathing, Safety& safety, int h);

[[gnu::flatten]] void bank_gems(World& world, Pathing& pathing, Safety& safety, Aims& aims, bool heal_step = true);

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
    float value(std::uint32_t gold_in) const;
    float rounds(int walk, int overlap, std::uint32_t gold_in) const;




};

HomeTrip home_trip(const World& world, Pathing& pathing, int channel, bool wins);

// The first altar without an enemy lock that a tribute from p reaches, or -1.
int altar_here(const World& world, vec2 p);

bool can_tribute_here(const World& world);

int carried_locks();

// The altar a tributer at p channels at.
int tribute_altar(const World& world, vec2 p);

bool can_tribute_safely(const World& world, Pathing& pathing, Safety& safety, const Aims& aims);

// Only a small bag, out of every credible enemy's reach, and never the gems that would win.
// Our bag heads for an altar rather than another capture: carry_bag's choice short of asking farm.
bool bag_bound_for_altar(const World& world, Pathing& pathing, Safety& safety);

// Cassi's and Issac's bags fall together. A credible enemy elsewhere on the map is no reason to
// walk a small bag home: on the ladder that started 44% of our bank trips.
bool may_chain(const World& world, Safety& safety);

// A bag bound for an altar rides the recall home when that reaches an altar sooner than walking;
// the stop also heals and shops.
bool recall_to_bank(const World& world, Pathing& pathing, Safety& safety, const Aims& aims);

// Carrying: chase a kill worth the risk, bank, wait at an altar until it is safe, or chain another
// capture on the way.
void carry_bag(World& world, Pathing& pathing, Safety& safety, Aims& aims, bool attacked);

}
}
