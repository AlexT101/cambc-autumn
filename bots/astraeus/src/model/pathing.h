// Live routes treat the units we see as standing still: walk one step, then replan. A host
// search costs a fixed setup plus a little per layer, not per tile, so routes run in full.
#pragma once
#include <cambc.h>
#include <array>
#include <cstdint>
#include <memory>
#include <optional>
#include <span>
#include <vector>
#include "../util.h"

namespace aph {

// Extra steps a live route may take over the static walking distance.
inline constexpr int max_detour = 16;

class World;
class Safety;
struct StaticMap;

// Tiles a dash from `from` can land on: <= 2 king steps not through walls or camps, onto a free
// tile; off `also` too when given.
// A scratch board, valid until the next call.
const bitboard& dash_landings_from(const StaticMap& map, vec2 from, const bitboard* also = nullptr);

class Pathing {
public:
    explicit Pathing(const World& world);

    void begin_turn();
    // The turn's Safety, which the travel dash's clearance reads (fight_near); null between turns.
    void use_safety(Safety* safety) { safety_ = safety; }

    const Field& to_ally_spawn();
    const Field& to_altar(int altar); // goals: the altar's tribute tiles
    const Field& to_any_altar();
    int centre_to_altar(int group); // to_any_altar() at the group's centre, kept once read
    int centre_to_spawn(int group); // steps from the group's centre to our spawn's centre tile, kept once read
    const Field& to_hop(int hop);   // goals: StaticMap::hops[hop]'s source tiles
    int hop_landing_steps(int hop); // the walk from its nearest landing tile to its altar, kept once read
    const Field& from_landings(int hop); // goals: StaticMap::hops[hop]'s landing tiles
    bool hop_ready(int hop) const;       // to_hop and from_landings made
    const Field& to_group(int group);    // goals: the group's camp tiles
    // to_group() walking only (blocked_for_us), whoever asks: the same for every ally, dash or not.
    const Field& to_group_walking(int group);
    // Static steps to tiles within `range` of the group's camp tiles, around the camps believed alive:
    // the walk to its attack tiles but for sight lines near the end. Range 0: onto its camp tiles, to
    // capture. Null if no walk reaches it within the search's cap (static steps + max_detour, as the farm walk's).
    const Field* approach(int group, int range);
    // What approach()'s latest search for the group knows of our walk there, while its labels hold:
    // the steps if it labelled us, else at least the layers it ran; `unreachable` if it ran dry (no
    // way round the live camps) or a search from here would run no farther; -1 with no such search.
    int live_steps(int group, int range);
    // approach(), or null without searching if the search could take the fuel below `fuel_floor`
    // (then approach_skipped() until the next call).
    const Field* prepare_approach(int group, int range, std::uint64_t fuel_floor);
    bool approach_skipped() const { return approach_skipped_; }
    bool approach_ready(int group, int range); // usable from here without a search
    std::uint64_t approach_cost(int group, int range); // 0 when ready
    // Width + height layers: below approach_cost() once walk_cap() has grown.
    static std::uint64_t max_approach_cost() { return search_cost_estimate(cambc::map::width() + cambc::map::height()); }
    // Walking steps from the centre of a group worth farming (a reward, no Monolith): by symmetry,
    // from anywhere to it. from_centre() is null until one is made; centre_field() makes it (at most
    // a full field), null only for a group not farmed.
    const Field* from_centre(int group);
    const Field* centre_field(int group);
    // Walkable tiles from which a basic attack reaches and sees the member, camp tiles included.
    const bitboard& member_attack_tiles(int group, int member, int range);
    bool attack_tiles_ready(int group, int member, int range) { return attack_slot(group, member, range).has_value(); }
    // Over the members believed alive; off camp tiles, but for those of its dead members.
    void attack_tiles(int group, int range, bitboard& out);
    // Compute attack_tiles' missing parts while more than `fuel_floor` remains; true once cached.
    bool prepare_attack_tiles(int group, int range, std::uint64_t fuel_floor);
    // The same for the members in `members` (bit i: member i), alive or not.
    bool prepare_member_tiles(int group, int range, std::uint32_t members, std::uint64_t fuel_floor);
    bool prepare_member(int group, int member, int range, std::uint64_t fuel_floor);
    // Precompute while more than `fuel_floor` remains; true once everything is cached.
    bool warm_up(int attack_range, std::uint64_t fuel_floor);
    // A field capped at centre_cap() has a bounded cost, so it may go down to last_reserve above
    // what `fuel_floor` keeps beyond end_reserve.
    // `near`: a group whose nearest groups go first.
    bool warm_centres(std::uint64_t fuel_floor, int near = -1);
    // A group farm read our steps to without its centre field: warm_centres makes those first.
    void want_centre(int group) {
        if (group < 256) wanted_centres_[static_cast<std::size_t>(group >> 6)] |= std::uint64_t{1} << (group & 63);
    }

    // Our static fields' walls, and what they leave walkable from our spawn: a dasher's leave out
    // the hole and altar lines a dash crosses.
    const bitboard& static_walls() const;
    const bitboard& foot() const;
    // test(foot(), p), without making foot() near our spawn.
    bool on_foot(vec2 p) const { return foot_made_ ? test(*foot_made_, p) : on_foot_unmade(p); }
    // Cohesion: the pull of the team on tile p, lower nearer it (allies in sight off our spawn, else
    // their claims' centres). Ties between equally short steps go to the lowest, so walks bend
    // towards teammates at no cost in steps.
    int pull(vec2 p);
    const bitboard& live_camps(); // members believed alive
    // Changes whenever a tile of live_camps() does, as of its last call.
    std::uint32_t live_flips() const { return live_flips_; }
    // Static walls, visible units, camps believed alive out of sight, teleport reservations, and tiles bumped this round.
    const bitboard& blocked();
    void occupied_into(bitboard& out); // blocked() with our own tile set
    void invalidate(); // after we move or dash

    // A champion with a dash travels by the turn (dash_turns): a walk, a dash, both in either order,
    // or a wait beside a line only a dash crosses, whichever reaches the goals in the fewest turns.
    // Of equally quick ones it dashes (the dash is back soonest), keeping the walk (a ranged attack's)
    // if it can. Not with an enemy seen this round or last within vision_radius + dash_range by its
    // terrain distance (enemy_reach): then it walks, and the dash is the fight's.
    // A hidden blocker fails a move without spending the walk; the other first steps are tried,
    // then the route is replanned.
    // An optional aim breaks equal-distance ties, retaining compass order for equal aim distance.
    bool step_towards(const bitboard& goals, const bitboard* avoid = nullptr, int max_steps = unreachable, std::optional<vec2> aim = std::nullopt);
    // On a respawning group's camp tile, a step off it: waiting there would hold the group back for good
    // (rules capture.respawn). False if not on one or no step was taken.
    bool leave_respawning(const bitboard* avoid = nullptr);
    // Turns, this one first, that travel as step_towards does it takes over `steps` steps of open ground.
    int travel_turns(int steps);
    // travel_turns in two parts, for a caller that reads the dash once: the wait before it (-1 without one).
    int travel_wait();
    static int travel_turns_after(int steps, int wait);
    // The same right after a failed step_towards from this tile, for goals that may lie within the
    // failed search's: when they do, under the same walls and cap, that search's failure is this one's.
    // Its caller must not read route_exhausted_ before another search.
    bool step_towards_within(const bitboard& goals, const bitboard* avoid, int max_steps, std::optional<vec2> aim);
    // The same, without avoid, aim or make_way, searching as deep as the fuel above `fuel_floor` pays for.
    bool step_towards_funded(const bitboard& goals, std::uint64_t fuel_floor);
    // A live route within `max_detour` of the static distance, else greedy descent of the field.
    bool step_towards(const Field& field, const bitboard* avoid = nullptr, std::optional<vec2> aim = std::nullopt);
    // Cheap fallbacks without a search, when fuel is short: a step down the field (or a dash, by the
    // turn as step_towards travels, waiting for none), or one that gets closer to the target as the crow flies.
    bool descend(const Field& field, const bitboard* avoid = nullptr, std::optional<vec2> aim = std::nullopt);
    // descend, else step_towards.
    bool walk_down(const Field& field, const bitboard* avoid = nullptr, std::optional<vec2> aim = std::nullopt);
    bool step_closer(vec2 target, const bitboard* avoid = nullptr, std::optional<vec2> aim = std::nullopt);
    // False, spending nothing, if illegal, guarded or blocked by a hidden unit; `refused`: set
    // unless a hidden unit was the reason.
    bool try_move(vec2 tile, bool* refused = nullptr);
    // A hidden unit refused a move since the last call: it is in sight now.
    bool take_bump() { const bool b = bumped_new_; bumped_new_ = false; return b; }
    // Tiles no step or dash may end on until cleared: routes go around them.
    void set_guard(const bitboard* guard) { guard_ = guard, guard_fn_ = nullptr, guard_skipped_ = false, route_cover_round_ = 0; }
    // A guard worked out on first need, from inputs read now: a turn that never steps skips it.
    using GuardFn = const bitboard* (*)(const World&, Safety&, vec2 here, int radius);
    // `cover`, if given, returns a superset of the tiles `fn` could guard (null: none), for less.
    void defer_guard(GuardFn fn, Safety& safety, vec2 here, int radius, GuardFn cover = nullptr) {
        guard_ = nullptr, guard_fn_ = fn, guard_safety_ = &safety, guard_here_ = here, guard_radius_ = radius, guard_cover_ = cover;
        guard_skipped_ = false;
        route_cover_round_ = 0;
    }
    // A route that left the guard deferred (route()) worked it out from what we know now: before
    // that changes, it is worked out, so that a later need reads the same guard.
    void settle_guard() const {
        if (guard_skipped_) (void)guard();
    }
    bool cover_deferred() const { return guard_fn_ && guard_cover_; }
    // While the guard is deferred with a cover, true with `out` the cover; false otherwise.
    bool guard_cover(const bitboard*& out) const {
        if (!cover_deferred()) return false;
        out = guard_cover_(world_, *guard_safety_, guard_here_, guard_radius_);
        return true;
    }
    const bitboard* guard() const {
        if (guard_fn_) {
            const auto fn = guard_fn_;
            guard_fn_ = nullptr;
            guard_ = fn(world_, *guard_safety_, guard_here_, guard_radius_);
        }
        return guard_;
    }
    // The guard as set, deferred or not, to put back without working it out.
    struct GuardState {
        const bitboard* guard;
        GuardFn fn;
        bool skipped;
        GuardFn cover;
        vec2 here;
        int radius;
    };
    GuardState held_guard() const { return {guard_, guard_fn_, guard_skipped_, guard_cover_, guard_here_, guard_radius_}; }
    void restore_guard(const GuardState& s) {
        guard_ = s.guard, guard_fn_ = s.fn, guard_skipped_ = s.skipped, guard_cover_ = s.cover, guard_here_ = s.here, guard_radius_ = s.radius;
        route_cover_round_ = 0;
    }

    // Unseen units can still block these.
    const bitboard& dash_landings(); // <= 2 king steps not through walls or camps, onto a free tile, off the guard
    // Free open or bush tiles within 3, off the enemy spawn and live camps: a camp tile only of a group
    // believed cleared or respawning (not yet due, unless seen empty) with no camp in sight on it.
    bitboard teleport_targets();

private:
    vec2 my_pos(); // our tile, read again after invalidate() or in a new round
    // Tiles and first steps are read only below count: left unwritten (vec2's initialisers would
    // zero them, a fuel a byte).
    struct Neighbours {
        Neighbours() {}
        union {
            std::array<vec2, 8> tiles;
        };
        int count = 0;
        const vec2* begin() const { return tiles.data(); }
        const vec2* end() const { return tiles.data() + count; }
    };
    // p is on the board, off `walls`, `avoid` and the guard.
    bool steppable(vec2 p, const bitboard& walls, const bitboard* avoid) const;
    // Free neighbours that get strictly closer on a static field, nearest first.
    Neighbours closer_neighbours(const Field& field, const bitboard* avoid = nullptr, std::optional<vec2> aim = std::nullopt);
    struct Route {
        Route() {}
        int steps = unreachable; // 0: already on a goal; unreachable: none within the cap
        int count = 0;
        // The first `count`: all equally short, compass order unless aimed; never onto a crossing.
        union {
            std::array<vec2, 8> first_steps;
        };
        bool unguarded = false; // the first steps are off the guard, which is left deferred
    };
    Route route(const bitboard& goals, const bitboard* avoid = nullptr, int max_steps = unreachable, std::optional<vec2> aim = std::nullopt);
    // route() with `guard` walled.
    Route route_around(const bitboard& goals, const bitboard* avoid, int max_steps, std::optional<vec2> aim, const bitboard* guard);
    // try_move past the guard test.
    bool move_to(vec2 tile, bool* refused);
    // The dash for travel: its slot (-1: none, or a visible enemy within travel_dash_clearance (.cc)),
    // whether it can be cast now, and its cooldown at the next turn's start if it is not.
    struct TravelDash {
        int slot = -1;
        bool now = false;
        int cool = 0;
        // fight_near alone left it out: the slot, now and cool it would have had.
        int withheld = -1;
        bool withheld_now = false;
        int withheld_cool = 0;
        bool forced = false; // released(): an enemy near is known, so the live checks pass it
    };
    TravelDash travel_dash();
    // A withheld dash given back.
    static TravelDash released(const TravelDash& w) {
        return TravelDash{.slot = w.withheld, .now = w.withheld_now, .cool = w.withheld_cool, .forced = true};
    }
    // An enemy within travel_dash_clearance (.cc): one in sight by its terrain distance (enemy_reach),
    // one out of sight from the tiles it may be on (Safety::unseen_within), kept for the round and
    // tile; or `live`, by the engine's tiles now, which a refused move or a landing can add to.
    bool fight_near(bool live);
    Safety* safety_ = nullptr;
    bool near_known_ = false, near_ = false;
    int near_round_ = -1;
    std::uint32_t near_obs_ = 0;
    vec2 near_at_{-1, -1};
    // Holes and altars our dash crosses (StaticMap::crossable; Heart of Ruin's off its landing walls).
    const bitboard& crossings();
    bool has_crossings();
    std::optional<bitboard> crossings_;
    int has_crossings_ = -1;
    // While set, live routes open crossings(): they count a crossing as the two steps its dash is.
    bool crossing_ = false;
    struct Crossing {
        bool& flag;
        bool was;
        Crossing(bool& f, bool on) : flag{f}, was{f} { flag = on; }
        ~Crossing() { flag = was; }
    };
    // The first crossing on the route down `d` (to `goals`) from us, within `horizon` steps: the steps
    // to its launch tile, and from its landing tile to the goals; launch -1: none.
    struct Ahead {
        int launch = -1, rest = 0;
        vec2 crossing{-1, -1};
    };
    Ahead ahead(const cambc::distance_field& d, const bitboard& goals, int here, int horizon);
    // How far ahead a crossing can change this turn's choice. With the dash ready, one farther than
    // max_horizon leaves room for a dash first that is ready again on arrival (dash_turns::across).
    // Cooling, only one reached before the dash is ready again can: a wait or a walk round.
    static constexpr int max_horizon = ability_cooldown + 1 + dash_range;
    static int horizon(const TravelDash& td) { return td.now ? max_horizon : td.cool + 2; }
    const bitboard& near_crossings(); // within max_horizon + 1 of a crossing
    std::optional<bitboard> static_no_dash_; // walls and the enemy spawn: no dash path crosses them
    std::optional<bitboard> near_crossings_;
    struct Trace {
        const cambc::distance_field* field = nullptr; // null: none kept
        int count = 0, top = 0, last = 0;             // tiles[i] is labelled top - i
        bool found = false, ended = false;            // found: beside the last tile
        int rest = 0;
        vec2 crossing{-1, -1};
        std::uint32_t used = 0; // trace_clock_ when last read: the least recent is replaced
        bitboard goals{cambc::uninitialized};
        union {
            std::array<vec2, 24> tiles; // the first `count` are set: left unzeroed (~770 fuel at start-up)
        };
        Trace() {}
    };
    std::array<Trace, 4> traces_;
    std::uint32_t trace_clock_ = 0;
    Trace* ahead_read_ = nullptr; // set by ahead() when it reads a trace
    // Set during travel()'s walk round, whose failure leaves nothing read but itself.
    bool walking_round_ = false;
    // The latest walk round whose search failed: its labels, goals, walls and cap, and whether it ran dry.
    struct RoundLabels {
        cambc::distance_field field;
        bitboard goals{cambc::uninitialized}, walls{cambc::uninitialized}, labelled{cambc::uninitialized};
        int cap = -1;
        bool dry = false;
        std::uint32_t id = 3;
    } round_labels_;
    bool round_fails(const bitboard& goals, const bitboard& walls, vec2 me, int cap);
    void keep_round();
    // No walk joins us to the goals, by map().foot() (crossings shut).
    bool walk_parted(const bitboard& goals, vec2 me);
    // The latest walk round `crossing` that found no way within `cap`, from `at` (travel()).
    struct RoundFailed {
        vec2 at{-1, -1}, crossing{-1, -1};
        int round = -1, cap = 0;
        bool avoided = false;
    } round_failed_;
    // A turn's travel: what plan() chose and travel() then did.
    enum class Travel : std::uint8_t { moved, bumped, walk };
    struct Plan {
        enum class Kind : std::uint8_t { walk, around, wait, dash } kind = Kind::walk;
        int turns = 1 << 20, end = unreachable; // our turns after this one; the end tile's steps on the field
        vec2 walk{-1, -1}, land{-1, -1};
        bool walk_first = false;
    };
    // What the plan reads: the field routed on (crossings open), the walking one if searched, and
    // the crossing ahead on the first.
    struct Labels {
        const cambc::distance_field* d = nullptr;
        const cambc::distance_field* w = nullptr;
        const bitboard* reached = nullptr; // the tiles d's search reached, if known: off them d reads unreachable
        Ahead ahead;
    };
    int turns_from(const Labels& l, vec2 q, int c) const;
    int turns_at(const Labels& l, vec2 q, int d, int c) const; // d: q's steps on l.d
    // `walks`: walking first steps, best first; `around`: those of the walking route; `may_wait`: a
    // wait beside the crossing ahead may be chosen (walking round it was weighed, or cannot be sooner).
    Plan plan(const TravelDash& td, const Labels& l, int here, std::span<const vec2> walks, std::span<const vec2> around,
              const bitboard* avoid, std::optional<vec2> aim, bool may_wait);
    // plan() after route() `r` found a way: a dash or a wait done; else the steps to walk in r (the
    // walking route's, if it plans to walk round a crossing).
    Travel travel(const TravelDash& td, Route& r, const bitboard& goals, const bitboard* avoid, int max_steps,
                  std::optional<vec2> aim);
    Travel take(const TravelDash& td, const Plan& p);
    bool dash_to(int slot, vec2 land); // false if a hidden unit holds it (now bumped), or refused
    bool step_route(const TravelDash& td, const bitboard& goals, const bitboard* avoid, int max_steps, std::optional<vec2> aim);
    bool descend_with(const TravelDash& td, const Field& field, const bitboard* avoid, std::optional<vec2> aim);
    // A failed descend_with is failed again until we act, bump or the guard changes.
    struct Descended {
        std::uint32_t acts;
        const bitboard* guard;
        GuardFn fn;
        Trace* trace; // the one its ahead() read: a repeat would read it again, as the latest
    };
    Descended descended() const { return {acts_, guard_, guard_fn_, ahead_read_}; }
    bool step_field(const Field& field, const bitboard* avoid, std::optional<vec2> aim, const Descended* failed);
    std::uint32_t acts_ = 0; // bumped by invalidate()
    // False after a failed route() that left the guard deferred: the guarded search fails too, but
    // its labels and route_exhausted_ are worked out only when read (know_failure()).
    bool failure_known_ = true;
    void know_failure(const bitboard& goals, const bitboard* avoid, int max_steps);
    bool labelled_ally_beside(const bitboard& allies, const bitboard& goals, const bitboard* avoid);
    // The label freeing ally tile a would give it from the failed search, or unreachable: one more than
    // its nearest labelled neighbour, else, through a line of allies behind it (a queue in a
    // corridor), one more per ally on the way.
    int label_through(vec2 a, const bitboard& allies, const bitboard* avoid, vec2 me);
    // Its line walk; `used`: the label the result was read from.
    int walk_through(vec2 a, const bitboard& allies, const bitboard* avoid, vec2 me, int& used);
    // The search route_field_ holds: each search computed gets a new number, which moves with its
    // field, so a failed search a standoff takes back from the spares keeps its walks.
    std::uint32_t route_gen_ = 0, field_ids_ = 3;
    struct ThroughMemo {
        std::uint32_t gen = 0;
        int cap = 0, result = 0, used = 0;
        vec2 a, me;
        bool avoided = false, guarded = false;
        bitboard allies{cambc::uninitialized}, avoid{cambc::uninitialized}, guard{cambc::uninitialized};
    };
    // A standoff asks the same few allies under two or three searches' caps every turn (make_way after
    // each failed route): 4 entries kept by turns thrash.
    std::array<std::optional<ThroughMemo>, 16> through_memo_;
    std::size_t through_next_ = 0;
    // The latest route's search: its distances from the goals, and whether it found no way
    // although it stopped short of its cap, so that no wider search finds one either.
    cambc::distance_field route_field_;
    // The tiles route_field_ labels (a field never written labels every tile 0): label_through reads
    // only those near the line of allies.
    bitboard route_labelled_{cambc::uninitialized};
    bool route_exhausted_ = false;
    // The failed search whose labels route_field_ holds (layers < 0: none).
    struct FailedRoute {
        bitboard goals{cambc::uninitialized}, walls{cambc::uninitialized};
        vec2 me{-1, -1};
        int cap = 0, layers = -1;
    } failed_;
    // Earlier failed searches, kept for a turn that repeats them (a standoff fails the same
    // searches every turn); one that matches takes failed_'s place as a fresh search would.
    struct SpareRoute {
        cambc::distance_field field;
        bitboard goals{cambc::uninitialized}, walls{cambc::uninitialized}, labelled{cambc::uninitialized};
        vec2 me{-1, -1};
        int cap = 0, layers = -1;
        std::uint32_t used = 0, id = 0;
    };
    // Made on first use, not on the first turn.
    std::array<std::optional<SpareRoute>, 3> spare_routes_;
    std::uint32_t spare_clock_ = 0;
    std::array<vec2, 3> spare_me_{{{-1, -1}, {-1, -1}, {-1, -1}}}; // each spare's origin, {-1, -1} if none
    void swap_spare(std::size_t i);
    bool take_spare(const bitboard& goals, const bitboard& walls, vec2 me, int cap);
    void spare_failed();
    void drop_dominated_spares();
    // Labels past the latest failed search's cap are another's, reused (route_around).
    int route_label_cap_ = unreachable;
    int route_label(vec2 p) const {
        const int steps = steps_at(route_field_, p);
        return steps > route_label_cap_ ? unreachable : steps;
    }
    // Where a failed search last found us enclosed (enclosed()).
    vec2 pocket_at_{-1, -1};
    static constexpr int pocket_radius = 16;
    // No goal within the walkable region around us, which ends within pocket_radius, and no ally beside us.
    bool enclosed(const bitboard& walls, const bitboard& goals, vec2 me);
    // The latest search that found a way, with its goals and walls: complete below `layer`, the
    // layer that reached us.
    struct KeptRoute {
        cambc::distance_field field;
        bitboard goals{cambc::uninitialized}, walls{cambc::uninitialized}, labelled{cambc::uninitialized};
        int layer = -1;
        std::uint32_t id = 0;
    };
    std::array<KeptRoute, 2> kept_routes_; // walking, and with crossings open (crossing_)
    // Our steps in k if a search over `walls` would label every tile below them as k's did.
    static int kept_steps(const KeptRoute& k, const bitboard& goals, const bitboard& walls, vec2 me, int cap);
    // Two allies head-on with no way past: the one with fewer gems (ties: lower champion) backs off.
    // Right after a route that found no way, with the same arguments: read from its field.
    // Leaves route_exhausted_ set only if no ally's tile, freed, opens a way at any cap.
    bool make_way(const bitboard& goals, const bitboard* avoid, int max_steps);
    // route_around may answer for goals within failed_'s (step_towards_within).
    bool within_ok_ = false;
    bool within_failed(const bitboard& goals, const bitboard* avoid);
    // `make`: the centre field or our spawn's field is made if missing, so the steps do not depend
    // on what the warm-up made; estimates read only what is there.
    int approach_steps(int group, int range, bool make);
    bool approach_skipped_ = false;
    // Layers an approach search may run when no field bounds the walk: width + height, doubled each
    // time a search is cut off at it (winding maps walk farther).
    int walk_cap() const;
    int walk_cap_ = 0;
    // An approach search's cap, from approach_steps().
    int approach_layers(int steps) const { return steps >= 0 ? steps + max_detour : walk_cap(); }
    const Field* search_approach(int group, int range, int steps); // approach() once known not ready
    using Slot = std::optional<Field>;
    const Field& cached(Slot& slot, const bitboard& goals);
    void make_centre(Slot& slot, int group); // capped at centre_cap(), doubled until whole
    // One capped try, at the cap doubled as often as fuel above `fuel_floor` pays for: the field, or the cap past it.
    void grow_centre(Slot& slot, int group, std::uint64_t fuel_floor);
    Slot& altar_slot(int altar);
    // A search that did not reach us is kept too: it bounds our walk from anywhere it left unlabelled.
    struct Approach {
        Field field;
        bitboard camps; // the live camp tiles it walks around
        std::uint32_t flips = 0; // live_flips() when made
        int layers = 0; // every tile nearer the goals than this is labelled
        bool dry = false; // it labelled all the goals reach
        std::uint32_t stale = ~0u; // live_flips() when its labels last failed to hold
    };
    std::unique_ptr<Approach>& approach_slot(int group, int range);
    // The field around the slot's camps has the labels a search around `live` would; then the
    // slot takes `live`.
    bool same_labels(Approach& slot, int group, int range, const bitboard& live);
    bool labels_hold(Approach& slot, int group, int range);
    // The slot answers for our tile without a new search: it labels us, or no search to `layers` would.
    bool approach_known(int group, int range, int layers);
    // approach_ready's latest answer, reused for the same slot, round and tile.
    struct ReadyCheck {
        const Approach* slot = nullptr;
        int round = -1;
        vec2 at{-1, -1};
        bool ready = false;
    } ready_check_;
    std::unique_ptr<Approach> spare_approach_; // a replaced one, refilled by the next search
    std::optional<bitboard>& attack_slot(int group, int member, int range);
    const StaticMap& map() const;
    bool farmed(int group) const; // farm reads only groups with a reward, Monoliths only off Monolith-only maps
    // Layers to cap its centre field at, doubled after a field cut short; 0: uncapped (no draft plan).
    int& centre_cap(int group);

    void make_pull();
    int pull_round_ = -1, pull_n_ = 0;
    std::array<vec2, 8> pull_at_{};
    std::array<int, 8> pull_weight_{};

    const World& world_;
    Slot any_altar_;
    mutable const bitboard* foot_made_ = nullptr; // foot(), once made
    bool on_foot_unmade(vec2 p) const;
    Slot ally_spawn_;
    std::vector<std::optional<int>> centre_to_altar_, centre_to_spawn_;
    Slot spawn_centre_; // from our spawn's centre tile
    std::vector<Slot> altar_fields_, centre_fields_, hop_fields_, landing_fields_, group_fields_, walking_group_fields_;
    std::vector<std::optional<int>> hop_landing_steps_;
    std::vector<int> centre_caps_;
    std::vector<std::vector<std::unique_ptr<Approach>>> approach_fields_; // by range, then group
    bitboard live_camps_;
    std::uint32_t live_camps_version_ = ~0u; // the World::camps_version it was built for
    std::vector<std::uint32_t> live_versions_; // per group: the CampBelief::version written
    std::vector<std::uint64_t> live_members_;  // per group: bit i, member i written alive
    std::uint32_t live_flips_ = 0;
    void draw_all_camps();
    bool centres_ready_ = false;
    std::array<std::uint64_t, 4> wanted_centres_{};
    int warm_centre_near_ = -2, warm_centre_k_ = 0; // warm_centres' order and where it stopped
    int warm_group_ = 0, warm_member_ = 0; // warm_up's progress through the attack tiles
    // By attack range, then group, then member.
    std::vector<std::vector<std::vector<std::optional<bitboard>>>> attack_tiles_;
    // Kept between rebuilds: allocating a board costs more than filling it.
    bitboard blocked_{cambc::uninitialized};
    bool blocked_fresh_ = false;
    bitboard bumped_;
    bool bumped_any_ = false, bumped_new_ = false;
    mutable const bitboard* guard_ = nullptr;
    mutable GuardFn guard_fn_ = nullptr;
    GuardFn guard_cover_ = nullptr;
    bool guard_skipped_ = false; // a route relied on the deferred guard's cover
    // route()'s cover, kept until the guard is set again or the round ends: each route that reads it
    // leaves the guard skipped (or works it out), so settle_guard() works the guard out before what
    // the cover reads changes, and route() asks no more.
    const bitboard* route_cover_ = nullptr;
    std::uint32_t route_cover_round_ = 0; // 0: none kept
    Safety* guard_safety_ = nullptr;
    vec2 guard_here_{-1, -1};
    int guard_radius_ = 1;
    int bumped_round_ = -1;
    vec2 pos_;
    std::uint32_t pos_round_ = 0;
    bool pos_fresh_ = false;
    unsigned dashes_seen_ = 0; // outside_dashes() when our tile was last read
};

} // namespace aph
