#pragma once

#include "../../../params.h"
#include <algorithm>
#include <array>
#include <vector>
#include "../../comms.h"

namespace aph {
struct ChampionBelief;
class World;
}
namespace aph::teacher_priority {
struct Unit;
struct Enemies;
}
namespace aph {
struct Strike;
class Safety;
}
namespace aph {
namespace {
enum Band : int;
struct Wish;
struct Enemy;
struct Strikes;
}
}

namespace aph {
class World;

class Safety;

// A priority's low bits, below its rank: free for comms, readable by whoever sees the champion.
// None in a priority of 0.
inline constexpr int priority_payload_bits = 16;

// Ranks us for next round; publish_turn_order sets it, with the payload, once the turn's claim and
// intents are final.
void set_turn_order(const World& world, Safety& safety);

void publish_turn_order(const World& world, std::uint32_t payload);

}
namespace aph {
namespace {
// One scale for every ally: teacher_priority's danger (14..23), dead (13) and idle (at most 12)
// values, with two bands above them. A kill or a cancelled channel outranks saving a life; each
// needs us to act before some enemy next round. Only non-teacher champions bid for the bands.
enum Band : int { no_band, protect, kill };

constexpr int band_width = 10000;

teacher_priority::Unit priority_self(const World& world);

static_assert(static_cast<int>(cambc::champion_type::ryth) == teacher_priority::ryth);

static_assert(static_cast<int>(cambc::champion_type::vesper_vale) == teacher_priority::vesper_vale);

static_assert(static_cast<int>(cambc::champion_type::vendetta) == teacher_priority::vendetta);

static_assert(static_cast<int>(cambc::champion_type::cassi) == teacher_priority::cassi);

static_assert(static_cast<int>(cambc::champion_type::issac) == teacher_priority::issac);

static_assert(static_cast<int>(cambc::champion_type::stellar) == teacher_priority::stellar);

static_assert(static_cast<int>(cambc::champion_type::prism) == teacher_priority::prism);

static_assert(static_cast<int>(cambc::champion_type::marcella) == teacher_priority::marcella);

static_assert(static_cast<int>(cambc::champion_type::willow) == teacher_priority::willow);

static_assert(static_cast<int>(cambc::champion_type::ren) == teacher_priority::ren);

static_assert(static_cast<int>(cambc::champion_type::varg) == teacher_priority::varg);

static_assert(static_cast<int>(cambc::champion_type::tavi) == teacher_priority::tavi);

static_assert(static_cast<int>(cambc::champion_type::heart_of_ruin) == teacher_priority::heart_of_ruin);

// An enemy yet to act this round moves before our next turn anyway: acting before its turn next
// round denies it only a second one.
constexpr float unacted_share = 0.5f;

struct Wish {
    int band = no_band;
    float value = 0;

    void offer(int b, float v);


    int priority() const;
};

// Only the order within the team matters, so a raw priority is renumbered by a code that keeps the
// order of every value it can take: idle, dead and danger in [-73, 23]; in a band, int(a life,
// tribute or recall value + 15 x gems), or of half a kill's, which is 0, 7 or 10 mod 15 (0 or 10
// when protecting), with the clamped 9999 above all.
constexpr int rank_code(int raw);

// Only the order within the team matters, so a raw priority is renumbered by a code that keeps the
// order of every value it can take: idle, dead and danger in [-73, 23]; in a band, int(a life,
// tribute or recall value + 15 x gems), or of half a kill's, which is 0, 7 or 10 mod 15 (0 or 10
// when protecting), with the clamped 9999 above all.
constexpr int rank_code(int raw)
{
    if (raw < band_width) return std::clamp(raw, -73, 23) + 73;
    const bool protecting = raw < 2 * band_width;
    const int v = raw - (protecting ? band_width : 2 * band_width), q = v / 15, r = v - 15 * q;
    if (protecting) return 97 + (v == band_width - 1 ? 1333 : 2 * q + (r >= 10));
    return 97 + 1334 + (v == band_width - 1 ? 2000 : 3 * q + (r >= 7) + (r >= 10));
}

static_assert(params::gem_value == 15 && static_cast<int>(params::life_value) % 15 == 0
              && static_cast<int>(params::tribute_value) % 15 == 10 && static_cast<int>(params::recall_value) % 15 == 0
              && unacted_share == 0.5f && static_cast<int>(params::life_value * unacted_share) % 15 == 0);

static_assert(rank_code(band_width - 1) < rank_code(band_width));

// The latest rank set_turn_order chose: kept when it skips a turn short of fuel.
int turn_rank = 0;

// The lowest rank: every ally acts before us.
constexpr int dodge_rank = -73;

// A camp monster hits the nearest champion in its reach, a tie going to the one acting first that
// round. The monsters we tie for with an ally who acts after us go to that ally if we act last: we do
// when every such ally has a larger share of its health left than we have.
bool dodge_camp_hits(const World& world, Safety& safety);

// Above the payload, the code relative to raw 0's, then 7 - our index so that equal codes still tie
// by id. Bots read a champion they have not seen as priority 0, so raw 0 stays 0 (no payload) and
// every other priority keeps its sign.
std::int32_t packed_priority(int raw, int index, std::uint32_t payload);

static_assert(((rank_code(3 * band_width - 1) - rank_code(0)) * 8 + 7) < 1 << (31 - priority_payload_bits));

struct Enemy {
    const ChampionBelief* belief;
    float health; // shield included
};

// Visible enemies still alive after our turn, with their health and shield now. One raw read
// each: every SDK accessor reads the whole record again.
const std::vector<Enemy>& live_enemies(const World& world);

// The enemies in sight at turn start that our turn has not killed.
const teacher_priority::Enemies& live_start_enemies(const World& world);

// Ourselves as we end the turn, moved. The fields read here only:
// copying a belief copies its bitboards.
ChampionBelief& live_self(const World& world, cambc::champion_state& state);

// What our strikes next round read, cooldowns restarted by casts included: only needed with an
// enemy in sight.
void read_strike(const World& world, ChampionBelief& b);

bool we_start(const World& world, int round);

// We can act before `e` next round unless its team starts and it is their first champion. Its
// priority for next round is final once it has acted, or if its team never changes priority;
// while either rank can change, `e` may go first.
bool can_act_before(const World& world, const ChampionBelief& e);

// Strikes for next round, by index, each worked out on first use. Slots not used are left
// unwritten: the engine charges for every byte.
struct Strikes {
    unsigned known = 0;
    union {
        std::array<Strike, 8> by_index;
    };
    Strikes();
};

const Strike& next_strike(const World& world, const ChampionBelief& c, Strikes& cache);

// Damage our next turn and those of the allies we see could deal to a tile, each walking first.
float side_damage(const World& world, const ChampionBelief& self, const Strike& ours, vec2 p, Strikes& allies);

// Killing or cancelling a channel needs us to act before its owner.
void offer_kills(const World& world, const ChampionBelief& self, const Strike& ours, const std::vector<Enemy>& enemies,
                 Wish& wish);

bool channel_ending(cambc::champion_state state);

// Our ending channel completes at our next turn's start, unless an enemy acting first cancels it:
// any damage cancels a recall, only a stun (Marcella is immune) a tribute or a teleport.
void offer_channel(const ChampionBelief& self, cambc::champion_state state, Safety& safety, Wish& wish);

// At least offer_escape's damage, from the strikes alone: no placement, and unseen enemies at
// their most. Before a refresh it still bounds the damage after one unless a visible enemy may have
// died: otherwise our turn only removed camp members.
bool may_escape(const World& world, const ChampionBelief& self, Safety& safety, bool seen);

// Enemies yet to act this round strike before our next turn whatever the order; acting first
// next round denies the second strike of those, and the only one of the others.
void offer_escape(const World& world, const ChampionBelief& self, Safety& safety, Wish& wish);

// A heal before the enemies' turns keeps an ally alive whom they would otherwise kill.
void offer_heal(const World& world, const ChampionBelief& self, const std::vector<Enemy>& enemies, Wish& wish);

}
}
namespace aph {
void set_turn_order(const World& world, Safety& safety);

void publish_turn_order(const World& world, std::uint32_t payload);

}
