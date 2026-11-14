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
#include "self_abilities.h"

namespace aph {
struct ChampionBelief;
class World;
class Pathing;
struct Field;
class Reach;
class Safety;
struct HealTarget;
}
namespace aph {
namespace {
struct SupportExposure;
struct Station;
struct Stations;
struct HealView;
}
}
namespace aph {
struct Aims;
}

namespace aph {
namespace {
// damage, imminent: Safety::damage_bound, the second with enemies yet to act counted twice.
struct SupportExposure {
    float damage = 0, imminent = 0;
    bool enemy = false, camp = false, stun = false;
    bool safe() const;
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

Stations& stations_cache();

const Stations& stations(const World& world, Safety& safety, vec2 here);

bool willow_bank_heal_step(World& world, Pathing& pathing, Safety& safety, const Field& field);

// Each camp member whose strike reaches p, as f(group, member index, member), in groups_near order;
// stops at the first f that returns false.
template <class F>
bool each_camp_striker(const World& world, vec2 p, F&& f);

// Willow holds no fight: a tile an enemy is likely to hit (want_home's test) or any camp member may
// hit is unsafe. `enemies`: false when no enemy can hit p, which spares their search.
SupportExposure exposure_at(const World& world, Safety& safety, vec2 p, bool enemies = true);

// Worked out on first need after we move or see again. Its guard board stays at one address: a
// guard Pathing holds reads the latest.
const Stations& stations(const World& world, Safety& safety, vec2 here);

// stations(here).tiles[0].risk alone, for when no step or guard read follows this turn: after
// Willow's walk, or at the turn's end.
SupportExposure exposure_here(const World& world, Safety& safety);

// Ours, or a free open tile a step reaches.
bool station_legal(Pathing& pathing, const Station& tile, vec2 here);

SupportExposure support_exposure(const World& world, Safety& safety, vec2 p);

bool stationary_support_output(const World& world, int work);

bool support_view(Reach::Window viewers, vec2 target, vec2 p);

const ChampionBelief* support_endpoint(const World& world, cambc::champion_type type);

bool recovered_for_work(const World& world, Safety& safety, const Aims& aims);

int heal_range(const ChampionBelief& healer);

// A unit our own ward sees stays visible to us wherever we step (wards.vision). Read per call: a
// ward can go down mid-turn without a re-observe (submit_here); its mask is cast again only when it moves.
bool own_ward_sees(const World& world, vec2 p);

// Tiles within `range` of a visible ally from which we see it, as the search's viewers(): exact
// where attack_viewers leaves out bushes beyond a step for our own tile, which sees it now, and
// every tile when our ward sees it.
Reach::Window heal_viewers(const World& world, vec2 target, int range);

struct HealView {
    HealTarget target;
    Reach::Window viewers; // tiles that see it within heal range
};

// heal_target's allies within a step of our heal range of p.
int heal_views(const World& world, vec2 p, float amount, std::array<HealView, 8>& out);

// One is in heal range of p: heal_ally casts from there without a step.
bool heal_lands_from(const World& world, vec2 p, const std::array<HealView, 8>& views, int n);

// The neighbouring station `ok` accepts from which a heal lands best: the most restored, then on
// the lowest ally, then the least `cost`. `here` if none.
template <class Ok, class Cost>
vec2 heal_station(const World& world, Pathing& pathing, Safety& safety, vec2 here, const std::array<HealView, 8>& views,
                  int n, Ok&& ok, Cost&& cost);

bool willow_bank_heal_step(World& world, Pathing& pathing, Safety& safety, const Field& field);

bool immediate_camp_finish(const World& world, vec2 here, float basic);

bool willow_independent_heal_step(World& world, Pathing& pathing, Safety& safety);

// Work the support formation must not interrupt: a capture, a bag to bank, a trip to shop.
bool support_work(const World& world, Pathing& pathing, Safety& safety, const Aims& aims);

// A single current-plus-neighbours pass owns both formation and local recovery. Willow comes here
// neither wanting home nor at work (decide).
bool local_support(World& world, Pathing& pathing, Safety& safety, Aims& aims, bool leave, bool& mate_eligible);

}
}
