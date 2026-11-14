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
struct Field;
}
namespace aph {
namespace {
struct PackBox;
struct PackZone;
struct RecallThreat;
struct Exposure;
}
}
namespace aph {
struct Strike;
class Safety;
struct Aims;
}

namespace aph {
namespace {
// Around awake camps and credible enemies when a way exists, else straight. Routes are replanned
// every turn, so only danger near us is worth the extra search.
void step_safely(Pathing& pathing, const Field& field, Safety& safety);

// Out of the camps' reach first, along the cheapest neighbour: walking home past an awake camp
// takes a hit every step, while a recall started outside its reach goes home untouched.
bool flee_camps(const World& world, Pathing& pathing, Safety& safety, const Field& home);

// Inside danger a route home is only the shortest walk, ties in compass order, which can lead
// along the enemies we flee: take the homeward step that can be hit least, then the nearest home,
// then the farthest from them. A sideways step goes first only when it can be hit less, and one
// that lengthens the walk only when it leaves every reach and no shorter one does: still in reach,
// it only delays, as the pursuer takes the step back next turn.
void retreat_step(const World& world, Pathing& pathing, Safety& safety, const Field& home);

const bitboard* pack_zone(const World& world);

// Our ground: no farther from our spawn than from theirs.
bool own_ground(const World& world, vec2 p);

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

PackZone& pack_zone_state(const World& world);

// The boxes as seen from `here`: our side counts us and the allies near `here`, at its ground's ratio.
void build_pack_boxes(const World& world, vec2 here, PackZone& pz);

PackZone& pack_boxes(const World& world);

// After a re-read of vision: the next query builds the boxes from what we see now.
void forget_pack_zone(const World& world);

bool in_pack_zone(const World& world, vec2 p);

// Adds the tiles of a box inside the map as a few squares: a host square costs about what a
// single tile does, a whole-board operation far more.
void draw_box(bitboard& b, int x0, int x1, int y0, int y1);

const bitboard* pack_zone(const World& world);

// pack_zone() holds every tile within r of p, worked out from its boxes.
bool pack_covers(const World& world, vec2 p, int r);

bool outmatched(const World& world, Pathing& pathing);

// Whether p lies in the pack zone as seen from p (the allies near it, its ground): outmatched() there.
bool in_pack_zone_from(const World& world, vec2 p);

// Whether an advance must keep out of the pack zone: wherever outmatched() would send us back out of it,
// carrying or not, or the advance and the retreat trade a tile each turn.
bool keeps_out_of_pack(const World& world, Pathing& pathing);

// Rounds of walking until no awake monster can pick us, at most one more than the longest camp reach.
int camp_exit_rounds(const World& world, Safety& safety, vec2 here);

// Camps keep hitting while we walk out of their reach: leave while the health still covers that.
// A siege (Aims::siege) keeps its own health limits for its group's hits.
bool camp_trapped(const World& world, Safety& safety, vec2 here, float health, bool sieging);

// No enemy can see `here` before a recall kept now lands, nor hit it blind. Sight is symmetric: an enemy
// sees us from a tile we would see from here (our shadowcast, radius 8), or from a bush, which sees out but
// not in; standing in a bush, only from inside our own cluster. A ground spell or a landing needs no sight:
// any tile in its reach. An enemy reaches one of those tiles by walking (dashers: 2 more, over holes) for
// the recall's remaining turns, from wherever the tracker allows it to be (`possible`; where it stands if
// seen; its spawn if it may respawn). An enemy alive, unseen and untracked could be anywhere.
// Which enemies could cut a recall here short (`may`: some tile they could be on reaches; `must`: one we see
// does, or every tile the tracker allows it, by enemy bit). `horizon` < 0: every enemy, one the tracker lost
// anywhere (the recall line). Else only those seen within `horizon` rounds, over the recall's turns left;
// one the tracker lost was judged while it had it.
struct RecallThreat {
    bool may = false;
    std::uint32_t must = 0;
};

RecallThreat recall_threat(const World& world, vec2 here, int horizon);

bool recall_unreachable_within(const World& world, vec2 here, int horizon);

bool recall_unreachable_now(const World& world, vec2 here);

bool recall_unreachable(const World& world, vec2 here);

// The health fraction at which we go home: lower while no enemy can interrupt the recall.
float recall_line(const World& world);

// Turns of the recall under way gone by, the turn end it began on not counted (start_recall begins one
// every turn end: kept the first time, it is at stage 0). 0 when not recalling.
int recall_stage(const World& world);

// A recall reckons with the enemies seen within track_horizon rounds of its start: one weighed when it
// began counts until it lands, so aging out cannot turn the decision mid-recall.
int recall_horizon(const World& world);

bool reckoned(const World& world, const ChampionBelief& e, int horizon);

// What the enemies we see see (sight is symmetric; a bush sees out, not in): their shadowcasts, a cluster
// one stands in transparent to it. Once a round.
const bitboard& enemy_sight(const World& world);

// Memory: where the enemy could believe we are, as its tracker would hold us. Every tile we could have
// walked to unseen since an enemy we see could last see us; our tile alone when one can, or after a round
// not noted (unknown counts as seen). Noted once a round, by the retreat state's first score.
struct Exposure {
    bitboard tiles{cambc::uninitialized};
    int round = -1;
};

Exposure& exposure();

void note_exposure(const World& world);

// In a bush the enemy could believe us on at least min(its cluster's size, 8) bush tiles of.
bool bush_hidden(const World& world, vec2 here);

// Within walk_home_steps of our spawn and no enemy we reckon with nearer it (where last seen): walk home.
bool near_home(const World& world, Pathing& pathing);

// An enemy we reckon with in sight.
bool enemy_seen_now(const World& world);

// Enemies we see, or know could cut a recall at `p` short (every tile they could be on reaches it): the
// recall must then hide or outdistance them. Otherwise (the base case) a tile off camp reach will do.
bool pressed(const World& world, vec2 p);

// A recall kept here lands: no awake camp member reaches us (stunned or not), and, pressed, no enemy could
// cut it short or we are hidden in a bush.
// Some awake camp member's own reach covers p: Safety's reach shrinks for a nearer champion, who shields us
// only while it stays, not for a whole recall.
bool camp_reaches(const World& world, vec2 p);

bool recall_spot_with(const World& world, Safety& safety, vec2 here, const RecallThreat& r);

bool recall_spot(const World& world, Safety& safety, vec2 here);

// The way home. Near home, walk it (the router dashes where that pays). Where a recall would land, stand
// (the turn end starts one). With no enemy in sight nor able to cut a recall short, to the nearest tile
// out of every awake camp's reach. Else away from them: the step (or staying) farthest by their walk,
// then out of their sight (a bush, behind a wall), then nearer home; off camp reach while any is.
void retreat_move(const World& world, Pathing& pathing, Safety& safety);

// An enemy that could kill us before our next turn overrides finishing a camp or a capture.
bool want_home(const World& world, Pathing& pathing, Safety& safety, const Aims& aims);

// want_home as if we stood on `here`: an advance (Pathing::set_advance) never steps where it holds.
bool want_home_at(const World& world, Pathing& pathing, Safety& safety, const Aims& aims, vec2 here);

// No enemy seen this round or last could walk into reach before the recall lands: standing
// still to channel while a pack closes in only gets it cancelled.
bool recall_outruns(const World& world, Safety& safety);

// A visible enemy within `range` of `from` that one basic attack kills.
const ChampionBelief* sure_kill(const World& world, vec2 from, int range);

// Nothing but `enemy` could hit us at p before our next turn.
bool only_threat(Safety& safety, vec2 p, int enemy);

// A sure kill from a tile a step away (melee: the walk keeps the attack) or a ready dash away,
// where nothing but the victim reaches us: the victim's tile, else {-1, -1}.
vec2 step_to_kill(const World& world, Pathing& pathing, Safety& safety, int range, bool melee);

// After our hits: an enemy we killed stays a live threat around its tile in World (dash landings,
// retreat steps) and, once refresh() has read it alive, in Safety: read vision again.
void see_kills(World& world, Pathing& pathing, Safety& safety);

void retreat(World& world, Pathing& pathing, Safety& safety, Aims& aims);

}
}
