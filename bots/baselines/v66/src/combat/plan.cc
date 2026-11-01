#include "plan.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdio>
#include <cstring>
#include "abilities.h"
#include "../emblems.h"
#include "../params.h"
#include "../model/pathing.h"
#include "../model/safety.h"
#include "self_abilities.h"
#include "../model/world.h"

namespace aph {

namespace {

constexpr int max_foes = 8;
constexpr bool debug_search = true; // SRCH and SRCH-REFUSED lines, inside debug_block
// SRCH-GUARD lines: every search works out a deferred step guard at its end and checks that no tile
// it priced was guarded (debug builds; it changes their fuel use).
constexpr bool debug_lazy_guard = false;
// SRCH-FREE lines: strike_free's answer checked against the whole search, which then always runs.
constexpr bool debug_strike_free = false;

// Search's attack_viewers by window row, for the two ranges asked most (ability_range, our attack
// range); here so that warm_tile can fill them.
constexpr int view_r = Reach::Window::radius, view_n = Reach::Window::width;
static_assert(ability_range <= view_r && view_n <= 16);
using ViewerRows = std::array<std::uint16_t, view_n>;
std::array<std::array<ViewerRows, 100 * 100>, 2> viewer_rows_cache;
std::array<std::array<std::uint8_t, 100 * 100>, 2> viewer_rows_known;

void fill_viewer_rows(const World& world, vec2 p, int r, ViewerRows& out) {
    const auto w = attack_viewers(world, p, r);
    for (int y = 0; y < view_n; ++y) out[y] = static_cast<std::uint16_t>(w.shr(view_n * y).lo & ((1u << view_n) - 1));
}

// ---- The basic attack from where we stand, for strike_enemy ----

struct Foe {
    const ChampionBelief* belief;
    vec2 pos;
    float health, retaliation, partner, bag;
    bool spawn;
    float taken; // damage it takes per point of our Strength
    float full;  // max health with the shield
    float stop;  // a kill's worth beyond hit_worth (kill_stops)
};

using Healths = std::array<float, max_foes>;

struct Board {
    std::array<Foe, max_foes> foes;
    int n = 0;
    vec2 here;
    float strength = 0, health = 0;
    int range = 1;
    bool splash = false;

    Healths healths() const {
        Healths h{};
        for (int i = 0; i < n; ++i) h[i] = foes[i].health;
        return h;
    }
};

// Read live: Vendetta's kill readies both slots mid-turn, after the belief was read.
bool slot_ready(const World& world, int slot) {
    try {
        return my_cooldown(slot) == 0;
    } catch (const cambc::error&) {
        return world.me().ability_ready(slot, world.round);
    }
}

// Health read from the engine, after our own hits this turn.
bool read_board(const World& world, Board& b, int reach) {
    const auto& f = world.me().facts();
    b.here = my_position();
    b.range = f.attack_range();
    b.splash = f.passive == Passive::splash_attack;
    const auto& enemy_spawn = world.map().enemy_spawn;
    b.n = 0;
    for (const auto& e : world.enemies) {
        if (b.n == max_foes) break;
        if (!e.alive || !e.visible || e.stats_round != world.round || dist(b.here, e.pos) > reach) continue;
        float health = 0, shield = 0;
        try {
            if (!is_alive(e.handle)) continue;
            health = record_of(e.handle).health;
            shield = e.shield > 0 ? shield_value(e.handle) : 0.0f;
        } catch (const cambc::error&) {
            continue;
        }
        // A shield absorbs before health: to kill, the hits must go through both.
        b.foes[b.n++] = {&e, e.pos, health + shield, e.retaliation() * world.me().taken, linked_partner_health(world, e),
                         params::gem_value * static_cast<float>(pair_gems(world, e)), test(enemy_spawn, e.pos), e.taken,
                         e.max_health + shield, kill_stops(world, e)};
    }
    if (b.n == 0) return false;
    b.health = my_health();
    b.strength = my_strength() * damage_scale(f.passive, b.health, my_max_health()) * champion_dealt_factor();
    return true;
}

struct Hit {
    float value = 0;
    int target = -1;
};

// The basic attack from here worth most, never one whose retaliation would kill us.
Hit best_hit(const Board& b, const Healths& h) {
    Hit best;
    float best_health = 0;
    for (int i = 0; i < b.n; ++i) {
        const auto& f = b.foes[i];
        if (h[i] <= 0 || dist(b.here, f.pos) > b.range) continue;
        const auto worth = [&](const Foe& o, float health) {
            const float d = b.strength * o.taken;
            return hit_worth(d, health, o.spawn, o.bag, o.partner, o.full) + (d >= health - 0.01f ? o.stop : 0.0f);
        };
        float value = worth(f, h[i]), retaliation = f.retaliation;
        if (b.splash)
            for (int j = 0; j < b.n; ++j) {
                const auto& o = b.foes[j];
                if (j != i && h[j] > 0 && dist(o.pos, f.pos) <= 1) value += worth(o, h[j]), retaliation += o.retaliation;
            }
        if (retaliation >= b.health) continue;
        value -= retaliation;
        if (value <= 0) continue;
        if (best.target < 0 || value > best.value || (value == best.value && h[i] < best_health)) best = {value, i}, best_health = h[i];
    }
    return best;
}

bool attack(const Board& b, const Hit& hit) {
    if (hit.target < 0) return false;
    try {
        attack_champion(b.foes[hit.target].belief->handle);
        return true;
    } catch (const cambc::error&) {
        return false;
    }
}

const Field* goal_field(const World& world, Pathing& pathing, const Intent& intent) {
    if (intent.to_altar) return &pathing.to_any_altar();
    const int g = intent.group;
    if (g < 0 || g >= static_cast<int>(world.camps.size())) return nullptr;
    const int range = world.camps[g].state == CampState::cleared ? 0 : world.me().facts().attack_range();
    return pathing.approach_ready(g, range) ? pathing.approach(g, range) : nullptr;
}

// ---- The strike search ----
//
// Every sequence of walk (W), basic attack (A), reset (R), dash (D) and enemy cast (S) the rules
// allow in a turn, with one cast. Moves end within grid_r of the start: a grid_n x grid_n grid,
// bit (y + grid_r) * grid_n + x + grid_r relative to it.

using Grid = std::uint64_t;
constexpr int grid_r = 1 + dash_range, grid_n = 2 * grid_r + 1; // a walk and a dash
constexpr int grid_cells = grid_n * grid_n;
static_assert(grid_cells < 64); // one Grid word, with grid_all's shift defined
constexpr Grid grid_all = (Grid{1} << grid_cells) - 1;
constexpr std::uint32_t grid_row = (1u << grid_n) - 1;
constexpr Grid grid_column(int x) {
    Grid g = 0;
    for (int y = 0; y < grid_n; ++y) g |= Grid{1} << (y * grid_n + x);
    return g;
}
constexpr Grid not_west = grid_all & ~grid_column(0), not_east = grid_all & ~grid_column(grid_n - 1);
constexpr Grid gbit(int c) { return Grid{1} << c; }
Grid dilate(Grid g) {
    const Grid h = g | ((g << 1) & not_west) | ((g >> 1) & not_east);
    return (h | (h << grid_n) | (h >> grid_n)) & grid_all;
}
template <class F> [[gnu::always_inline]] inline void each_bit(Grid g, F&& f) {
    for (; g; g &= g - 1) f(std::countr_zero(g));
}

constexpr int max_units = 14;  // foes, then camp members
constexpr int max_groups = 16; // camp groups the turn may touch
constexpr int max_members = 48;
// Tiles within ability_range of the start: index (y + win9_r) * win9_n + x + win9_r relative to it.
constexpr int win9_r = ability_range, win9_n = 2 * win9_r + 1;
constexpr int max_centres = win9_n * win9_n; // every window tile
constexpr int max_unseen = 24;
constexpr int max_depth = 6;
constexpr int max_mates = 6;
// Reach queries per search; past it the rest keep their Strike price.
constexpr int max_exact_queries = 10;
// Nodes a search grows, at ~1.1k fuel each; past it the leaves offered so far stand.
constexpr int max_nodes = 24;

enum class Op : std::uint8_t { walk, attack, reset, dash, spell, heal, shield };
struct Act {
    Op op;
    std::int8_t unit = -1; // attack, unit spell; heal: the mate
    std::int8_t slot = -1; // spell
    vec2 tile{-1, -1};     // walk, dash, ground spell
    bool operator==(const Act&) const = default;
};
struct Seq {
    std::array<Act, max_depth + 1> a; // + a heal or shield
    int n = 0;
};

// Where a sequence's actions are taken: the start, after the walk, after the dash, after a walk
// then the dash, after the dash then a walk.
enum Seg : std::uint8_t { at_start, walked, dashed, walked_dashed, dashed_walked };

using UnitHealths = std::array<float, max_units>;

struct Unit {
    const ChampionBelief* belief = nullptr; // foes
    vec2 pos;
    float health = 0, shield = 0; // a foe's health with its shield, and the shield
    float full = 0;               // a foe's max health with its shield
    float retaliation = 0, partner = 1e9f, bag = 0;
    float taken = 1; // damage it takes per point dealt (a Durability emblem)
    bool foe = true, spawn = false, stunnable = false, recall = false;
    float stun = 0;                             // Marcella's armed attack's stun
    float stop = 0;                             // a kill's worth beyond hit_worth (kill_stops)
    float land = 0, land_stun = 0;              // our landing's
    std::array<float, 2> spell{}, spell_stun{}; // per slot
    std::array<bool, 2> suicidal{};             // per slot: its retaliation would kill us
    int group = -1, member = -1, local = -1;    // camps
    std::int8_t hor = -1;                       // its index among enemy Hearts of Ruin
    std::int8_t link = -1;                      // Cassi's or Issac's partner among the foes
    // Enemies (bits by index) leaving our end tile's danger: when it dies, both of a pair, the
    // unseen one too; when stunned, itself if it has one turn before ours.
    std::uint16_t drop_kill = 0, drop_stun = 0;
    Grid legal = 0, cast_legal = 0; // where our attack, or a unit cast, reaches and sees it
};

struct Centre {
    vec2 tile;
    std::uint16_t foes = 0;
    std::uint32_t touched = 0;
    float unseen = 0;
    bool banned = false;
};

struct Member {
    vec2 pos;
    int local;
    bool sleeper; // a striker maybe asleep
};

// A sleeping striker a touch would wake, and the nearest champion other than us in its reach.
struct Waker {
    vec2 pos;
    float strength;
    int reach;
    bool monolith;
    int other_d, other_slot; // other_d > reach: none
    int ally;                // index into World::allies, or -1 for an enemy held in place
};

// Copied for every child: kept small, as copies cost a fuel a byte.
struct Node {
    Seg seg = at_start;
    bool walk : 1 = false, attack : 1 = false, cast : 1 = false, excl : 1 = false;
    bool reset : 1 = false, dash : 1 = false, armed : 1 = false;
    // A walk or dash not yet followed by a strike from where it ended: a move with none is the
    // goal's walk or retreat's dash, which price what the leaf score cannot (later turns).
    bool owed : 1 = false;
    std::int8_t depth = 0;
    std::uint16_t stunned = 0;     // units stunned this turn
    std::uint16_t dead = 0;        // units killed this turn
    float value = 0, pending = 0; // pending: a cast's price a Vendetta kill would refund
    float hurt = 0;               // Ren's retaliation taken this turn
    std::uint32_t touched = 0;     // local camp groups hit
    Grid req_w = grid_all, req_d = grid_all, req_e = grid_all; // the tiles still allowed for each move's end
    Grid lset = 0; // a landing that hits: its tiles, alike in what they hit
    // The tiles of units killed before the walk, and before the dash, which it could cross or end on.
    Grid open_w = 0, open_d = 0;
};

// A sequence as the search grows it, its walk and dash tiles left open.
struct Leaf {
    Seq seq;
    std::array<float, 2> hor; // the enemy Hearts of Ruin's health after it
};

struct Choice {
    float raw; // hits less prices and wakes, plus a heal and an unused walk
    std::int16_t leaf;
    std::int8_t w, d;   // its walk and dash cells
    std::int8_t mate;   // healed, or -1
    bool first;         // the heal cast from the start tile, before the moves
    std::uint16_t removed; // enemies out of the end tile's danger, by index
};

// The best leaves on one end tile, one per set of enemies removed, less those another beats with
// a superset removed. When full the lowest goes: an option lost, never one overvalued.
constexpr int max_sets = 8;
struct Front {
    std::array<Choice, max_sets> e;
    int n;
    // The entry to fill with a leaf worth `raw` removing `r`, or -1.
    int admit(float raw, std::uint16_t r) {
        for (int i = 0; i < n; ++i)
            if ((e[i].removed & r) == r && e[i].raw >= raw) return -1;
        int k = 0, low = -1;
        for (int i = 0; i < n; ++i)
            if ((e[i].removed & r) != e[i].removed || e[i].raw > raw) {
                if (k != i) e[k] = e[i];
                if (low < 0 || e[k].raw < e[low].raw) low = k;
                ++k;
            }
        n = k;
        if (n < max_sets) return n++;
        return e[low].raw < raw ? low : -1;
    }
    float top() const {
        float x = e[0].raw;
        for (int i = 1; i < n; ++i) x = std::max(x, e[i].raw);
        return x;
    }
};

struct Unseen {
    vec2 pos;
    float weight, worth;
    bool suicidal; // its retaliation would kill us
};

// What lies within 1 of a tile, for ground centres.
struct Near {
    std::uint16_t foes;
    bool banned;
    float unseen;
};

// Kept in static storage: zeroing it each turn would cost more than the search. In a union, so
// its members' default initialisers never run: they cost ~50k of the first turn's fuel.
struct PlanTables {
    std::array<Unit, max_units> u;
    std::array<Centre, max_centres> centres;
    std::array<Unseen, max_unseen> unseen;
    std::array<Member, max_members> members;
    std::array<Waker, max_members> wakers;
    std::array<Front, grid_cells> best, kept; // kept: the cast left for the shield; valid by has bits
    std::array<Leaf, 512> leaves;
    std::array<Grid, grid_cells> land_from;
    std::array<float, grid_cells> heal_at; // the best heal cast from each tile
    std::array<std::int8_t, grid_cells> heal_who;
    std::array<std::uint32_t, win9_n * win9_n> touch1;
    std::array<Near, win9_n * win9_n> near;
    std::array<std::uint8_t, max_centres> distinct; // centres, less those equal to an earlier one
    std::array<std::uint32_t, grid_cells> land_foes;
};
union TableStorage {
    PlanTables t;
    TableStorage() {}
    ~TableStorage() {}
} table_storage;
PlanTables& plan_tables = table_storage.t;

struct Search {
    const World& world;
    Safety& safety;
    Pathing& pathing;
    const Intent& intent;
    const ChampionFacts& f;
    std::array<Unit, max_units>& u = plan_tables.u;
    std::array<Front, grid_cells>& best = plan_tables.best;

    vec2 here;
    float strength = 0, health = 0, step = 0, dash_cost = 0, shield_amount = 0;
    float camp_taken = -1; // camp_hit_factor(), read on first need
    float champion_dealt = 1; // champion_dealt_factor(), which strength includes
    int range = 1, land_radius = 0;
    bool melee = true, splash = false, vendetta = false, lands = false, walks = false, moves = true;
    bool can_walk = false, can_attack = false, can_cast = false, walked_first = false;
    int reset = -1, dash = -1, shield = -1, heal = -1;
    bool reset_ready = false, dash_ready = false, arms = false;
    std::array<bool, 2> ready{}; // by slot, with the cast unspent
    bool ready_known = false;    // ready as read by strike_free
    int ready_of(AbilityKind kind) const {
        const int slot = f.slot_of(kind);
        return slot >= 0 && ready[slot] ? slot : -1;
    }
    struct Spell {
        int slot = -1;
        bool unit = false, ground = false, excl = false;
    };
    std::array<Spell, 2> spells;

    int n = 0, foes = 0;
    UnitHealths h{};
    std::array<int, max_groups> groups;
    int n_groups = 0, n_members = 0, n_centres = 0, n_distinct = 0, n_unseen = 0;
    // By local group: its wakers in plan_tables.wakers, found on first need.
    std::array<std::uint8_t, max_groups> waker_begin, waker_end;
    std::uint32_t wakers_known = 0;
    int n_wakers = 0, self_slot = 0;
    void find_wakers(int k);
    std::array<const ChampionBelief*, 2> hors;
    std::array<std::int8_t, 2> hor_unit;
    int n_hors = 0;
    std::array<const ChampionBelief*, max_mates> mates;
    int n_mates = 0;

    Grid free_ = 0, pass_ = 0, free_n = 0, land_here = 0, land_hits = 0, plain_here = 0, dom_dw = 0;
    // A unit's grid bit, when its death opens its tile to us (not on the enemy spawn); 0 otherwise.
    std::array<Grid, max_units> unit_cell{};
    // The tiles the units killed so far in a sequence have opened.
    Grid opened(const Node& s) const {
        Grid g = 0;
        for (std::uint32_t m = s.dead; m; m &= m - 1) g |= unit_cell[std::countr_zero(m)];
        return g;
    }
    // free_n, landings(), land_here and plain_here with the tiles `o` open as well.
    Grid free_n_at(Grid o) const { return o ? (moves && can_walk ? (free_ | o) & dilate(gbit(cell(here))) & ~gbit(cell(here)) : 0) : free_n; }
    Grid landings_at(int c, Grid o) {
        if (!o) return landings(c);
        const Grid s = gbit(c), one = dilate(s);
        return ((one | dilate(one & (pass_ | o))) & (free_ | o)) & ~s & ~land_bad;
    }
    Grid land_here_at(Grid o) { return o ? landings_at(cell(here), o) : land_here; }
    Grid plain_here_at(Grid o) { return o ? land_here_at(o) & ~land_hits : plain_here; }
    Grid guarded = 0; // the step guard's tiles: never an end
    // Tiles a deferred step guard may cover: offered, and dropped once it is worked out (resolve_guard).
    Grid maybe_guarded = 0, cover = 0; // cover: maybe_guarded as read (debug_lazy_guard)
    Grid land_known = 0;
    // Landings never taken: those striking camps but no foe, and those waking a sleeping striker
    // (a woken pack keeps hitting while the fight stays, which wake() does not price).
    Grid land_bad = 0;

    union {
        std::array<Act, max_depth> stack;
    };
    Grid has = 0;
    int nodes = 0, offers = 0, n_leaves = 0;

    Grid kept_has = 0;

    Search(const World& w, Safety& s, Pathing& p, const Intent& i) : world(w), safety(s), pathing(p), intent(i), f(w.me().facts()) {}

    int cell(vec2 p) const { return (p.y - here.y + grid_r) * grid_n + (p.x - here.x + grid_r); }
    vec2 tile(int c) const { return {here.x + c % grid_n - grid_r, here.y + c / grid_n - grid_r}; }
    bool in_grid(vec2 p) const { return std::abs(p.x - here.x) <= grid_r && std::abs(p.y - here.y) <= grid_r; }

    // A dash from cell c: at most 2 king steps not through walls or live camps, onto a free tile.
    Grid landings(int c) {
        if (land_known & gbit(c)) return plan_tables.land_from[c];
        const Grid s = gbit(c), one = dilate(s);
        plan_tables.land_from[c] = ((one | dilate(one & pass_)) & free_) & ~s & ~land_bad;
        land_known |= gbit(c);
        return plan_tables.land_from[c];
    }

    // Tiles within r of the visible unit at p that see it. attack_viewers leaves out bushes beyond
    // a step, but the start tile is exact: the unit is visible from there now.
    Grid viewers(vec2 p, int r) const {
        if (ward_sees(p)) return square(p, r);
        const auto& rows = viewer_rows(p, r);
        const int shift = p.x - here.x + grid_r - view_r; // grid column less window column
        const std::uint32_t span = ((1u << (2 * r + 1)) - 1) << (view_r - r);
        Grid g = 0;
        for (int dy = std::max(-r, here.y - grid_r - p.y), dy1 = std::min(r, here.y + grid_r - p.y); dy <= dy1; ++dy) {
            const std::uint32_t row = rows[dy + view_r] & span;
            g |= static_cast<Grid>((shift >= 0 ? row << shift : row >> -shift) & grid_row) << ((p.y + dy - here.y + grid_r) * grid_n);
        }
        return g | (dist(here, p) <= r ? gbit(cell(here)) : 0);
    }
    // Every grid tile within r of p.
    Grid square(vec2 p, int r) const {
        const int x0 = std::max(p.x - r - here.x, -grid_r) + grid_r, x1 = std::min(p.x + r - here.x, grid_r) + grid_r;
        const int y0 = std::max(p.y - r - here.y, -grid_r) + grid_r, y1 = std::min(p.y + r - here.y, grid_r) + grid_r;
        if (x0 > x1) return 0;
        const Grid row = gbit(x1 + 1) - gbit(x0);
        Grid g = 0;
        for (int y = y0; y <= y1; ++y) g |= row << (y * grid_n);
        return g;
    }
    // A unit our own ward sees stays visible to us wherever we move (wards.vision). Our ward is
    // found on first need; its mask is cast again only when it moves.
    mutable bool ward_known = false, warded = false;
    bool ward_sees(vec2 p) const {
        static bitboard sight{cambc::uninitialized};
        static vec2 cast_at{-1, -1};
        if (!ward_known) {
            ward_known = true;
            static std::array<cambc::detail::ward_info, 16> raw;
            std::uint32_t k = 0;
            ok(cambc::detail::sdk_wards(raw.data(), static_cast<std::uint32_t>(raw.size()), &k));
            const auto own = static_cast<std::uint32_t>(world.map().team_a ? 0 : 1);
            for (std::uint32_t i = 0; i < k && i < raw.size() && !warded; ++i) {
                const auto& w = raw[i];
                if (w.team != own || w.owner != my_handle() || w.disabled) continue;
                warded = true;
                if (const vec2 at{w.x, w.y}; at != cast_at) ok(cambc::detail::sdk_ward_vision(at.x, at.y, sight.ptr())), cast_at = at;
            }
        }
        return warded && test(sight, p);
    }
    // attack_viewers by window row (bit x + view_r), kept for the game for the two ranges asked most:
    // it depends on terrain alone.
    using Rows = ViewerRows;
    const Rows& viewer_rows(vec2 p, int r) const {
        static Rows scratch;
        const int slot = r == ability_range ? 0 : r == range ? 1 : -1;
        const auto i = static_cast<std::size_t>(p.x + p.y * world.map().width);
        if (slot < 0 || i >= viewer_rows_known[0].size()) {
            fill_viewer_rows(world, p, r, scratch);
            return scratch;
        }
        if (!viewer_rows_known[slot][i]) fill_viewer_rows(world, p, r, viewer_rows_cache[slot][i]), viewer_rows_known[slot][i] = 1;
        return viewer_rows_cache[slot][i];
    }

    // The camp groups a landing on cell c touches, by cell.
    Grid land_touch_known = 0;
    std::uint32_t land_touch(int c) {
        if (land_radius == 1) return touch1(tile(c));
        static std::array<std::uint32_t, grid_cells> memo; // valid by land_touch_known
        if (!(land_touch_known & gbit(c))) memo[c] = touch_near(tile(c), land_radius), land_touch_known |= gbit(c);
        return memo[c];
    }
    std::uint32_t touch_near(vec2 p, int r) const {
        std::uint32_t mask = 0;
        for (int k = 0; k < n_members; ++k)
            if (dist(p, plan_tables.members[k].pos) <= r) mask |= 1u << plan_tables.members[k].local;
        return mask;
    }
    // Calls f(i) for each 9x9 window index within 1 of p.
    template <class F> [[gnu::always_inline]] void around(vec2 p, F&& f) const {
        const int x = p.x - here.x + win9_r, y = p.y - here.y + win9_r;
        const int x0 = std::max(0, x - 1), x1 = std::min(win9_n - 1, x + 1), y1 = std::min(win9_n - 1, y + 1);
        for (int yy = std::max(0, y - 1); yy <= y1; ++yy)
            for (int xx = x0; xx <= x1; ++xx) f(yy * win9_n + xx);
    }
    // touch_near(p, 1), from the members scattered once over the 9x9 window.
    bool touch1_known = false;
    std::uint32_t touch1(vec2 p) {
        if (n_members == 0) return 0;
        const int dx = p.x - here.x, dy = p.y - here.y;
        if (std::abs(dx) > win9_r || std::abs(dy) > win9_r) return touch_near(p, 1);
        auto& t = plan_tables.touch1;
        if (!touch1_known) {
            touch1_known = true;
            t.fill(0);
            for (int k = 0; k < n_members; ++k) {
                const std::uint32_t bit = 1u << plan_tables.members[k].local;
                around(plan_tables.members[k].pos, [&](int i) { t[i] |= bit; });
            }
        }
        return t[(dy + win9_r) * win9_n + dx + win9_r];
    }
    // Landings that hit, grouped alike for the last hits set and foes alive asked.
    Grid groups_hits = 0;
    std::uint32_t groups_alive = 0;
    int n_land_groups = 0;
    std::array<Grid, grid_cells> land_groups;
    // Landing cells by class, alike in (foes in reach, groups touched), found on first need: a
    // query merges the classes whose foes alive agree.
    Grid class_known = 0;
    int n_land_classes = 0;
    std::array<std::int8_t, grid_cells> cell_class;
    std::array<std::uint32_t, grid_cells> class_foes, class_touch;
    std::uint32_t class_foes_all = 0;
    void group_landings(Grid hits, std::uint32_t alive) {
        each_bit(hits & ~class_known, [&](int k) {
            const std::uint32_t m = land_foes(k), t = land_touch(k);
            int i = 0;
            while (i < n_land_classes && !(class_foes[i] == m && class_touch[i] == t)) ++i;
            if (i == n_land_classes) class_foes[i] = m, class_touch[i] = t, ++n_land_classes;
            cell_class[k] = static_cast<std::int8_t>(i);
            class_foes_all |= m;
        });
        class_known |= hits;
        const bool merge = (alive & class_foes_all) != class_foes_all;
        std::array<std::uint32_t, grid_cells> hit, touch;
        std::array<std::int8_t, grid_cells> group_of;
        std::uint64_t seen = 0;
        n_land_groups = 0;
        each_bit(hits, [&](int k) {
            const int j = cell_class[k];
            if (!(seen >> j & 1)) {
                seen |= std::uint64_t{1} << j;
                int i = n_land_groups;
                if (merge) {
                    const std::uint32_t m = class_foes[j] & alive, t = class_touch[j];
                    i = 0;
                    while (i < n_land_groups && !(hit[i] == m && touch[i] == t)) ++i;
                    if (i == n_land_groups) hit[i] = m, touch[i] = t;
                }
                if (i == n_land_groups) land_groups[i] = 0, ++n_land_groups;
                group_of[j] = static_cast<std::int8_t>(i);
            }
            land_groups[group_of[j]] |= gbit(k);
        });
    }
    // The foes a landing on cell c hits, alive or not.
    Grid land_foes_known = 0;
    std::uint32_t land_foes(int c) {
        if (!(land_foes_known & gbit(c))) {
            std::uint32_t m = 0;
            for (int t = 0; t < foes; ++t)
                if (dist(tile(c), u[t].pos) <= land_radius) m |= 1u << t;
            plan_tables.land_foes[c] = m, land_foes_known |= gbit(c);
        }
        return plan_tables.land_foes[c];
    }

    bool read();
    void read_geometry();
    Grid read_grid(const bitboard& from); // its tiles in the grid
    // Works out a deferred guard: its tiles join `guarded`.
    void resolve_guard() {
        maybe_guarded = 0;
        if (const bitboard* guard = pathing.guard()) guarded |= read_grid(*guard) & ~gbit(cell(here));
    }
    void read_members();
    void read_camps();
    void read_spells();
    void add_unseen(int slot, float raw);
    void find_centres(int slot);
    void read_mates();
    // The heal worth most cast from cell c or, before moving, from the start; its mate in `who`.
    float heal_from(int c, std::int8_t& who, bool& first) const {
        const int h0 = cell(here);
        first = plan_tables.heal_at[h0] >= plan_tables.heal_at[c];
        who = plan_tables.heal_who[first ? h0 : c];
        return plan_tables.heal_at[first ? h0 : c];
    }
    // What the shield would absorb at p over its turns.
    float shield_at(vec2 p) const {
        return std::min(shield_amount, static_cast<float>(f.abilities[shield].duration) * safety.damage_bound(p, false, world.me().taken));
    }

    // Health left to t's partner, whose death is t's.
    float partner(int t) const {
        const int k = u[t].link;
        return k < 0 ? u[t].partner : std::min(h[k], u[k].belief->health);
    }
    // A kill takes the partner with it.
    void lose(int t, float d, Node& s) {
        if ((h[t] -= d) > 0.01f) return;
        h[t] = 0;
        die(t, s);
        if (const int k = u[t].link; k >= 0) h[k] = 0, die(k, s);
    }
    // A kill cancels a tribute, and a stun credited this turn on the dead takes no turn from it. Each
    // of our champions stuns by one means, so the stun credited is the one nonzero stun value.
    void die(int t, Node& s) const {
        const auto bit = static_cast<std::uint16_t>(1u << t);
        if (s.dead & bit) return;
        s.dead |= bit;
        const auto& x = u[t];
        s.value += x.stop - (s.stunned & bit ? std::max({x.stun, x.land_stun, x.spell_stun[0], x.spell_stun[1]}) : 0.0f);
    }
    // Whether t's partner, hit later by the same blow (not yet counted), dies to it while t would
    // not: t's hit is then worth nothing beyond the partner's kill.
    bool moot(int t, float d, bool partner_hit, float partner_d) const {
        const int k = u[t].link;
        return partner_hit && h[k] > 0 && partner_d >= h[k] - 0.01f && d < h[t] - 0.01f;
    }

    [[gnu::always_inline]] bool hit_unit(int t, Node& s);
    [[gnu::always_inline]] bool spell_unit(const Spell& sp, int t, Node& s);
    // A landing on cell c, of a class already found.
    [[gnu::always_inline]] bool land_at(int c, Node& s);
    [[gnu::always_inline]] float centre_value(const Centre& c, int slot, const Node& s, bool& ok, float& back) const;
    void hit_centre(const Centre& c, int slot, Node& s);
    bool wake(std::uint32_t touched, vec2 E, float& cost, float& on_us);
    bool wakers_known_slot = false;
    // wake() by end tile, for the last touched set asked there: leaves differing only in their
    // hits share them.
    struct WakeMemo {
        std::uint32_t touched;
        float cost, on_us;
        bool ok;
    };

    Grid wake_known = 0;
    bool wake_at(std::uint32_t touched, int c, float& cost, float& on_us) {
        static std::array<WakeMemo, grid_cells> memo; // valid by wake_known
        auto& m = memo[c];
        if (!(wake_known & gbit(c)) || m.touched != touched) {
            m.touched = touched, m.ok = wake(touched, tile(c), m.cost, m.on_us);
            wake_known |= gbit(c);
        }
        cost = m.cost, on_us = m.on_us;
        return m.ok;
    }
    // wake() at the start tile, by touched set: the ground centres ask it at every node.
    std::array<WakeMemo, 8> here_wakes;
    int n_here_wakes = 0;
    bool wake_here(std::uint32_t touched, float& cost, float& on_us) {
        for (int i = 0; i < n_here_wakes; ++i)
            if (here_wakes[i].touched == touched) {
                cost = here_wakes[i].cost, on_us = here_wakes[i].on_us;
                return here_wakes[i].ok;
            }
        const bool ok = wake(touched, here, cost, on_us);
        if (n_here_wakes < static_cast<int>(here_wakes.size())) here_wakes[n_here_wakes++] = {touched, cost, on_us, ok};
        return ok;
    }
    float leaf_value(const Node& s) const;

    Node root() const;
    bool legal_at(Node& s, Grid legal);
    // Whether a strike can still follow: a move with none after it is never offered.
    bool strikes_left(const Node& s) const {
        if (s.attack) return true;
        if (!s.cast) return false;
        if (s.reset || (lands && s.dash)) return true;
        for (const auto& sp : spells)
            if (sp.slot >= 0 && sp.unit && !sp.excl) return true;
        return false;
    }
    // Foes the start tile's attack hits without a kill, off their spawn and with no partner to
    // cap the damage: on them hit_worth sums the same in either order. Set as the root expands,
    // its attacks first.
    std::uint16_t soft_first = 0;
    // An attack after moves and casts alone, the last move followed by a strike, is offered
    // earlier from the start tile, at the same value and with more end tiles. A spell's cancelled
    // recall needs the foe to outlive it, so a recalling foe keeps its order.
    bool hoisted(const Node& s, int t) const {
        if (s.owed || s.depth == 0 || splash || vendetta || !(soft_first >> t & 1)) return false;
        for (int k = 0; k < s.depth; ++k) {
            const Op op = stack[k].op;
            if (op != Op::walk && op != Op::dash && (op != Op::spell || u[t].recall)) return false;
        }
        return true;
    }
    // A walk then an attack the start tile allows leaves the state the attack then the walk does,
    // which is grown first and keeps every walk tile: only the leaf itself is its own.
    bool walked_attack(const Node& s) const {
        return s.depth == 2 && melee && stack[0].op == Op::walk && stack[1].op == Op::attack &&
               (u[stack[1].unit].legal & gbit(cell(here)));
    }

    void grow(const Node& s);
    void settle(const Node& s);
    template <class Mid> void offer(Grid ends, float v, const Node& s, std::int16_t& leaf, Mid&& mid);
    // For the last kills and stuns asked: siblings mostly share them.
    std::uint32_t removed_key = ~0u;
    std::uint16_t removed_last = 0;
    std::uint16_t removed(const Node& s) {
        const std::uint32_t key = s.dead | std::uint32_t{s.stunned} << 16;
        if (key == removed_key) return removed_last;
        std::uint16_t r = 0;
        const std::uint32_t all = (1u << foes) - 1;
        for (std::uint32_t m = s.dead & all; m; m &= m - 1) r |= u[std::countr_zero(m)].drop_kill;
        for (std::uint32_t m = s.stunned & ~s.dead & all; m; m &= m - 1) r |= u[std::countr_zero(m)].drop_stun;
        removed_key = key;
        return removed_last = r;
    }
    Seq concrete(int c, bool keep, int entry, bool shields) const {
        const auto& ch = (keep ? plan_tables.kept[c] : best[c]).e[entry];
        Seq q = plan_tables.leaves[ch.leaf].seq;
        for (int i = 0; i < q.n; ++i) {
            if (q.a[i].op == Op::walk) q.a[i].tile = tile(ch.w);
            if (q.a[i].op == Op::dash) q.a[i].tile = tile(ch.d);
        }
        if (ch.mate >= 0) {
            const Act heal_act{Op::heal, ch.mate};
            if (ch.first) {
                for (int i = q.n; i > 0; --i) q.a[i] = q.a[i - 1];
                q.a[0] = heal_act;
            } else {
                q.a[q.n] = heal_act;
            }
            ++q.n;
        } else if (shields) {
            q.a[q.n++] = {Op::shield};
        }
        return q;
    }
    float hor_health(int leaf, int k) const { return plan_tables.leaves[leaf].hor[k]; }

};

// The map's bounds and walls by grid cell around each centre tile: terrain alone, kept for the game.
struct TerrainGrid {
    Grid inside = 0, walls = 0; // inside is never 0 once read
};

// `box`: the grid's square around `centre`, drawn.
const TerrainGrid& terrain_grid(const StaticMap& map, vec2 centre, const bitboard& box, bitboard& scratch) {
    static std::array<TerrainGrid, 100 * 100> grids;
    static std::array<std::uint8_t, 100 * 100 / 8 + 8> wall_bits; // walls as packed row-major bits
    static int packed = 0;                                       // 1 yes, 2 no
    if (packed == 0) {
        packed = 2;
        const std::size_t size = bitboard::linear_buffer_size();
        if (size + 8 <= wall_bits.size()) {
            map.walls.export_linear_buffer({wall_bits.data(), size});
            packed = 1;
            // Bits run from the low end of each byte; check on a set tile.
            if (!map.walls.is_empty()) {
                const vec2 probe = first_tile(map.walls);
                const int i = probe.x + probe.y * map.width;
                if (!(wall_bits[static_cast<std::size_t>(i >> 3)] >> (i & 7) & 1)) packed = 2;
            }
        }
    }
    static TerrainGrid wide; // past 100x100: read every time
    const auto at = static_cast<std::size_t>(centre.x + centre.y * map.width);
    if (at < grids.size() && grids[at].inside) return grids[at];
    auto& out = at < grids.size() ? grids[at] : wide;
    out = {};
    const int x0 = centre.x - grid_r, lo = std::max(0, -x0), hi = std::min(grid_n, map.width - x0);
    const Grid span = ((Grid{1} << (hi - lo)) - 1) << lo;
    for (int r = 0; r < grid_n; ++r) {
        const int y = centre.y - grid_r + r;
        if (y < 0 || y >= map.height) continue;
        out.inside |= span << (r * grid_n);
        if (packed != 1) continue;
        const int i = x0 + lo + y * map.width;
        std::uint64_t word;
        std::memcpy(&word, &wall_bits[static_cast<std::size_t>(i >> 3)], sizeof word);
        out.walls |= ((word >> (i & 7)) & ((Grid{1} << (hi - lo)) - 1)) << lo << (r * grid_n);
    }
    if (packed != 1) {
        Unwritten<vec2, grid_cells> tiles;
        and_into(map.walls, box, scratch);
        const auto k = positions_into(scratch, tiles.a.data(), grid_cells);
        for (std::uint32_t i = 0; i < k; ++i)
            out.walls |= gbit((tiles.a[i].y - centre.y + grid_r) * grid_n + tiles.a[i].x - centre.x + grid_r);
    }
    return out;
}

namespace {
bitboard search_box{cambc::uninitialized}, search_scratch{cambc::uninitialized};
vec2 search_box_at{-1, -1};
} // namespace

Grid Search::read_grid(const bitboard& from) {
    Unwritten<vec2, grid_cells> at;
    and_into(from, search_box, search_scratch);
    const auto k = positions_into(search_scratch, at.a.data(), grid_cells);
    Grid out = 0;
    for (std::uint32_t i = 0; i < k; ++i) out |= gbit(cell(at.a[i]));
    return out;
}

void Search::read_geometry() {
    auto& box = search_box;
    auto& t = search_scratch;
    if (here != search_box_at) {
        clear_board(box);
        draw_square(box, here, grid_r);
        search_box_at = here;
    }
    const auto& terrain = terrain_grid(world.map(), here, box, t);
    const Grid blocked = read_grid(pathing.blocked());
    // A move may pass a guarded tile: only where the moves end is exposed. Where we stand is never
    // an end to drop: after the goal, or unmoved, it is the only one, so the guard is not worked
    // out. A deferred guard with a cover is worked out only once a tile it may cover would count.
    if (const bitboard* cover = nullptr; moves && pathing.guard_cover(cover)) {
        if (cover) this->cover = maybe_guarded = read_grid(*cover) & ~gbit(cell(here));
    } else if (const bitboard* guard = moves ? pathing.guard() : nullptr) {
        guarded = read_grid(*guard) & ~gbit(cell(here));
    }
    if (intent.anchored && intent.hold) guarded |= ~read_grid(*intent.hold) & ~gbit(cell(here));
    free_ = terrain.inside & ~blocked;
    // Dash paths are blocked by walls, camps, visible enemies (probe-dash-enemy) and the enemy spawn.
    // Read only for a turn that can dash (grow's dash nodes; a plan without one never asks).
    if (moves && (dash_ready || (vendetta && can_cast && dash >= 0))) {
        static bitboard foes_seen{cambc::uninitialized};
        camps_into(t);
        occupancy_into(team::enemy, foes_seen);
        or_into(t, foes_seen, t);
        or_into(t, world.map().enemy_spawn, t);
        pass_ = terrain.inside & ~(read_grid(t) | terrain.walls);
    }
    free_n = moves && can_walk ? free_ & dilate(gbit(cell(here))) & ~gbit(cell(here)) : 0;
}

// Live members of the groups near enough for the turn to hit: our attacks reach 3 + 1 + Varg's
// splash, a landing 3 + 1, a ground cast 5.
void Search::read_members() {
    const auto& groups_map = world.map().groups;
    for (int g : world.map().groups_near(here, grid_r + range + 1)) {
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || n_groups == max_groups) continue;
        const int local = n_groups;
        bool any = false;
        for (std::size_t i = 0; i < groups_map[g].members.size() && n_members < max_members; ++i)
            if (c.health[i] > 0 && dist(here, groups_map[g].members[i].pos) <= ability_range + 1)
                plan_tables.members[n_members++] = {groups_map[g].members[i].pos, local,
                                               groups_map[g].members[i].strength > 0 && c.maybe_asleep(i)},
                any = true;
        if (any) groups[n_groups++] = g;
    }
}

void Search::read_camps() {
    // Camps are struck only for what that enables: Vendetta's refresh, Varg's splash.
    if (!vendetta && !splash) return;
    const int reach = (vendetta ? grid_r : 1) + range;
    // strength carries the champion-only factor; a camp takes its own in its place.
    const float dealt = camp_dealt_factor() / champion_dealt;
    const auto& groups_map = world.map().groups;
    for (int k = 0; k < n_groups; ++k) {
        const int g = groups[k];
        for (int i = 0; i < static_cast<int>(groups_map[g].members.size()) && n < max_units; ++i) {
            const auto& m = groups_map[g].members[i];
            if (world.camps[g].health[i] <= 0 || dist(here, m.pos) > reach || !cambc::vision::has_camp(m.pos)) continue;
            bool useful = false;
            for (int j = 0; j < foes && splash && !useful; ++j) useful = dist(u[j].pos, m.pos) <= 1;
            float hp = 0;
            try {
                const auto live = groups_map[g].camp(i);
                if (!live.is_visible()) continue;
                hp = live.health();
            } catch (const cambc::error&) {
                continue;
            }
            if (vendetta) useful |= hp <= strength * dealt;
            if (!useful || hp <= 0) continue;
            auto& x = u[n];
            x = Unit{};
            x.foe = false;
            x.taken = dealt;
            x.pos = m.pos;
            x.health = hp;
            x.group = g, x.member = i, x.local = k;
            x.legal = viewers(m.pos, range);
            h[n++] = hp;
        }
    }
}

void Search::read_spells() {
    if (!can_cast) return;
    for (int s = 0; s < 2; ++s) {
        const auto& a = f.abilities[s];
        if (!ready[s]) continue;
        if ((a.kind != AbilityKind::damage && a.kind != AbilityKind::stun) || (a.target != Targeting::unit && a.target != Targeting::ground))
            continue;
        // After the goal's walk, the walk has taken an excludes-walking cast.
        if (a.excludes_walking && walked_first) continue;
        float raw = 0;
        try {
            raw = my_damage(s);
        } catch (const cambc::error&) {
        }
        auto& sp = spells[s];
        sp.slot = s;
        sp.unit = a.target == Targeting::unit;
        sp.ground = a.target == Targeting::ground;
        sp.excl = a.excludes_walking;
        for (int i = 0; i < foes; ++i) {
            auto& x = u[i];
            if (dist(here, x.pos) > a.reach() + (sp.excl ? 0 : 1)) continue;
            const auto& e = *x.belief;
            float lost = 0;
            try {
                lost = raw > 0 ? my_damage_to(s, e.handle) : 0.0f;
            } catch (const cambc::error&) {
                lost = std::clamp(raw * x.taken - x.shield, 0.0f, x.health - x.shield);
            }
            // Health lost after the shield, which x.health counts; the shield drains by the reduced damage.
            x.spell[s] = x.shield <= 0 ? lost : lost > 0 ? lost + x.shield : std::min(raw * x.taken, x.shield);
            x.spell_stun[s] = a.stuns && x.stunnable ? stun_worth(world, e, raw > 0) : 0.0f;
            x.suicidal[s] = raw > 0 && x.retaliation >= health;
            if (sp.unit && x.cast_legal == 0) x.cast_legal = viewers(x.pos, ability_range);
        }
        if (sp.ground) {
            add_unseen(s, raw);
            find_centres(s);
        }
    }
}

// Unseen tracked enemies on few tiles, which a ground cast may hit, as cast_at_enemies aims.
void Search::add_unseen(int s, float raw) {
    const auto& a = f.abilities[s];
    const auto& enemy_spawn = world.map().enemy_spawn;
    n_unseen = 0;
    for (const auto& e : world.enemies) {
        if (!e.alive || e.visible || !e.tracked || board_empty(e.possible)) continue;
        const int count = static_cast<int>(board_count(e.possible));
        if (count > max_unseen_tiles) continue;
        const float hp = e.health > 0 ? e.health : e.max_health;
        const float stun = a.stuns ? stun_worth(world, e, raw > 0) : 0.0f;
        const float back = raw > 0 ? e.retaliation() * world.me().taken : 0.0f;
        const bool suicidal = back >= health && back > 0;
        for (auto p : positions_within(e.possible, here, a.reach())) {
            if (n_unseen == max_unseen) break;
            const float worth = hit_worth(std::min(raw * e.taken, hp), hp, test(enemy_spawn, p),
                                          params::gem_value * static_cast<float>(pair_gems(world, e)),
                                          linked_partner_health(world, e), e.max_health) + stun - back;
            plan_tables.unseen[n_unseen++] = {p, 1.0f / static_cast<float>(count), worth, suicidal};
        }
    }
}

// Allies a heal could reach from some tile, each worth what it restores, capped by what could hit
// it before the slot is ready again.
void Search::read_mates() {
    if (heal < 0) return;
    float amount = 0;
    try {
        amount = my_heal(heal);
    } catch (const cambc::error&) {
        heal = -1;
        return;
    }
    const int r = f.abilities[heal].range();
    plan_tables.heal_at.fill(0);
    for (const auto& a : world.allies) {
        if (n_mates == max_mates || dist(here, a.pos) > grid_r + r) continue;
        std::optional<HealTarget> t;
        try {
            t = heal_target(world, a, amount);
        } catch (const cambc::error&) {
            continue;
        }
        if (!t) continue;
        const float value = std::min(t->gain, static_cast<float>(ability_cooldown) * safety.damage_bound(a.pos));
        if (value <= 0) continue;
        const auto k = static_cast<std::int8_t>(n_mates);
        mates[n_mates++] = &a;
        each_bit(viewers(a.pos, r), [&](int c) {
            if (value > plan_tables.heal_at[c]) plan_tables.heal_at[c] = value, plan_tables.heal_who[c] = k;
        });
    }
    if (n_mates == 0) heal = -1;
}

// Centres within range whose 3x3 holds a visible foe or an unseen one's tile.
void Search::find_centres(int s) {
    const int r = std::min(f.abilities[s].range(), win9_r);
    // What each tile holds within 1, scattered from the foes and unseen tiles once.
    auto& near = plan_tables.near;
    // Centres lie within 1 of a foe or an unseen tile: only those are read. Clearing all costs
    // less than clearing around many.
    if (foes + n_unseen > 8) std::memset(near.data(), 0, sizeof(near));
    else {
        for (int i = 0; i < foes; ++i) around(u[i].pos, [&](int j) { near[j] = {}; });
        for (int k = 0; k < n_unseen; ++k) around(plan_tables.unseen[k].pos, [&](int j) { near[j] = {}; });
    }
    for (int i = 0; i < foes; ++i)
        around(u[i].pos, [&](int j) { near[j].foes |= static_cast<std::uint16_t>(1u << i), near[j].banned |= u[i].suicidal[s]; });
    for (int k = 0; k < n_unseen; ++k) {
        const auto& un = plan_tables.unseen[k];
        around(un.pos, [&](int j) {
            if (un.suicidal) near[j].banned = true;
            else near[j].unseen += un.weight * un.worth;
        });
    }
    // By window row: the columns on the map and within r, less the centres already added.
    std::uint32_t cols = 0;
    std::array<std::uint32_t, win9_n> open{};
    for (int k = -r; k <= r; ++k)
        if (const int x = here.x + k; x >= 0 && x < world.map().width) cols |= 1u << (k + win9_r);
    for (int k = -r; k <= r; ++k)
        if (const int y = here.y + k; y >= 0 && y < world.map().height) open[k + win9_r] = cols;
    // A centre equal to an earlier one in all its value reads can never be picked over it: only
    // the first of each is kept in `distinct`, found by a hash of those reads.
    std::array<std::uint8_t, 128> slots{};
    std::array<std::uint64_t, max_centres> keys;
    std::array<std::uint32_t, max_centres> unseen_bits;
    n_centres = n_distinct = 0;
    const auto add = [&](vec2 p) {
        const int x = p.x - here.x + win9_r, y = p.y - here.y + win9_r;
        const std::uint32_t three = x > 0 ? 7u << (x - 1) : 7u >> (1 - x);
        for (int yy = std::max(0, y - 1), y1 = std::min(win9_n - 1, y + 1); yy <= y1; ++yy) {
            std::uint32_t row = open[yy] & three;
            open[yy] &= ~row;
            for (; row; row &= row - 1) {
                const int xx = std::countr_zero(row), j = yy * win9_n + xx;
                const int k = n_centres++;
                auto& ce = plan_tables.centres[k];
                ce.tile = {here.x + xx - win9_r, here.y + yy - win9_r};
                ce.foes = near[j].foes, ce.banned = near[j].banned, ce.unseen = near[j].unseen;
                ce.touched = touch1(ce.tile);
                const std::uint64_t key = ce.foes | std::uint64_t{ce.banned} << 16 | std::uint64_t{ce.touched} << 17;
                const auto bits = std::bit_cast<std::uint32_t>(ce.unseen);
                std::uint32_t h = static_cast<std::uint32_t>((key * 0x9E3779B97F4A7C15ull + bits * 0xC2B2AE3Dull) >> 57);
                bool twin = false;
                for (; slots[h] && !twin; h = (h + 1) & 127) {
                    const int q = slots[h] - 1;
                    twin = keys[q] == key && unseen_bits[q] == bits;
                }
                if (twin) continue;
                slots[h] = static_cast<std::uint8_t>(n_distinct + 1);
                keys[n_distinct] = key, unseen_bits[n_distinct] = bits;
                plan_tables.distinct[n_distinct++] = static_cast<std::uint8_t>(k);
            }
        }
    };
    for (int i = 0; i < foes; ++i)
        if (dist(here, u[i].pos) <= r + 1) add(u[i].pos);
    for (int k = 0; k < n_unseen; ++k) add(plan_tables.unseen[k].pos);
}

bool Search::read() {
    const auto& record = my_record();
    here = {record.x, record.y};
    range = f.attack_range();
    melee = f.walk_and_attack_independent();
    splash = f.passive == Passive::splash_attack;
    vendetta = f.passive == Passive::reset_on_kill;
    const auto state = cambc::champion_state::from_bits_retain(record.state);
    can_walk = state.contains(cambc::champion_state::can_move);
    can_attack = state.contains(cambc::champion_state::can_attack);
    can_cast = state.contains(cambc::champion_state::can_cast);
    health = record.health;
    // Off our start tile with the cast unspent, the goal walked: this is the search after it.
    walked_first = here != world.turn_start;
    champion_dealt = champion_dealt_factor();
    strength = record.strength * damage_scale(f.passive, health, record.max_health) * champion_dealt;
    moves = !intent.anchored || intent.hold;
    walks = intent.walks && can_walk;
    step = intent.step_value;
    dash_cost = dash_range * step; // the dash's cooldown would otherwise carry us two steps
    reset = f.slot_of(AbilityKind::attack_reset);
    dash = f.slot_of(AbilityKind::dash);
    if (!ready_known) ready = {can_cast && slot_ready(world, 0), can_cast && slot_ready(world, 1)};
    shield = ready_of(AbilityKind::shield);
    heal = ready_of(AbilityKind::heal);
    reset_ready = reset >= 0 && ready[reset];
    dash_ready = moves && dash >= 0 && ready[dash];
    arms = reset >= 0 && f.abilities[reset].stuns;
    if (dash >= 0 && f.abilities[dash].lands()) lands = true, land_radius = f.abilities[dash].radius;

    // Foes some end tile could hit, by attack or cast. Their stun buffs and recalls are read only
    // when a stun or a cast could use them.
    const int reach = std::max(grid_r + range + (splash ? splash_radius : 0), ability_range + 1);
    bool stuns = arms, casts = false, touches = (lands && dash_ready) || splash || vendetta;
    for (int s = 0; s < 2; ++s)
        if (ready[s] && f.abilities[s].hits_enemies())
            stuns |= f.abilities[s].stuns, casts |= !f.abilities[s].lands(), touches |= f.abilities[s].target == Targeting::ground;
    const auto& enemy_spawn = world.map().enemy_spawn;
    for (const auto& e : world.enemies) {
        if (foes == max_foes) break;
        if (!e.alive || !e.visible || e.stats_round != world.round || dist(here, e.pos) > reach) continue;
        bool stunned = false, recall = false;
        float hp = 0, absorbs = 0;
        // Read live: after the goal, our hits this turn have landed.
        try {
            const auto* record = visible_record(e.handle);
            if (!record) continue;
            hp = record->health;
            if (e.shield > 0 || stuns) {
                const auto buffs = buff_state(e.handle);
                absorbs = e.shield > 0 ? buffs.shield : 0.0f;
                stunned = stuns && buffs.stun_pending;
            }
            recall = casts && e.channel == Channel::recall
                     && aph::kept_recall(e.handle, e.recall_turns());
        } catch (const cambc::error&) {
            continue;
        }
        auto& x = u[foes];
        x = Unit{};
        x.belief = &e;
        x.pos = e.pos;
        x.health = hp + absorbs;
        x.shield = absorbs;
        x.full = e.max_health + absorbs;
        x.retaliation = e.retaliation() * world.me().taken;
        x.taken = e.taken;
        x.partner = linked_partner_health(world, e);
        x.bag = params::gem_value * static_cast<float>(pair_gems(world, e));
        x.spawn = test(enemy_spawn, e.pos);
        x.stunnable = !stunned && e.facts().passive != Passive::stun_immune;
        x.recall = recall;
        x.stun = arms && x.stunnable ? stun_worth(world, e, true) : 0.0f;
        x.stop = kill_stops(world, e);
        x.drop_kill = static_cast<std::uint16_t>(1u << e.index);
        if (const auto* p = linked_partner(world, e); p && p->alive) x.drop_kill |= static_cast<std::uint16_t>(1u << p->index);
        // A stun takes only the next turn: with two before ours, the blow still lands.
        if (stuns && x.stunnable && turns_before_ours(world, e) == 1) x.drop_stun = static_cast<std::uint16_t>(1u << e.index);
        if (e.facts().passive == Passive::missing_health && n_hors < 2) x.hor = static_cast<std::int8_t>(n_hors), hor_unit[n_hors] = static_cast<std::int8_t>(foes), hors[n_hors++] = &e;
        x.legal = (can_attack || reset_ready) && dist(here, e.pos) <= grid_r + range ? viewers(e.pos, range) : 0;
        h[foes++] = x.health;
    }
    n = foes;
    if (foes == 0) return false;
    for (int i = 0; i < foes; ++i)
        for (int j = 0; j < foes && u[i].belief->facts().passive == Passive::linked_pair; ++j)
            if (j != i && u[j].belief->facts().passive == Passive::linked_pair) u[i].link = static_cast<std::int8_t>(j);
    read_geometry();
    // Camps matter only to what can touch them.
    if (touches) read_members();
    read_camps();
    for (int t = 0; t < n; ++t)
        unit_cell[t] = in_grid(u[t].pos) && !test(world.map().enemy_spawn, u[t].pos) ? gbit(cell(u[t].pos)) : 0;
    if (lands && (dash_ready || vendetta)) {
        try {
            const float raw = my_damage(dash);
            const auto& a = f.abilities[dash];
            for (int i = 0; i < foes; ++i) {
                auto& x = u[i];
                if (dist(here, x.pos) > grid_r + land_radius) continue;
                const float lost = raw > 0 ? my_damage_to(dash, x.belief->handle) : 0.0f, sh = x.shield;
                x.land = sh <= 0 ? lost : lost > 0 ? lost + sh : std::min(raw * x.taken, sh);
                x.land_stun = a.stuns && x.stunnable ? stun_worth(world, *x.belief, raw > 0) : 0.0f;
            }
        } catch (const cambc::error&) {
        }
    }
    read_spells();
    read_mates();
    if (shield >= 0) {
        try {
            shield_amount = my_shield(shield);
        } catch (const cambc::error&) {
            shield = -1;
        }
    }
    if (moves && (dash_ready || (vendetta && can_cast && dash >= 0))) {
        if (lands) {
            const auto mark = [&](vec2 at, Grid& g) {
                for (int dy = -land_radius; dy <= land_radius; ++dy)
                    for (int dx = -land_radius; dx <= land_radius; ++dx)
                        if (const vec2 p{at.x + dx, at.y + dy}; in_grid(p)) g |= gbit(cell(p));
            };
            for (int i = 0; i < foes; ++i)
                if (u[i].land > 0 || u[i].land_stun > 0) mark(u[i].pos, land_hits);
            for (int k = 0; k < n_members; ++k)
                if (dist(here, plan_tables.members[k].pos) <= grid_r + land_radius) mark(plan_tables.members[k].pos, land_bad);
            land_bad &= ~land_hits;
            for (int k = 0; k < n_members; ++k)
                if (plan_tables.members[k].sleeper && dist(here, plan_tables.members[k].pos) <= grid_r + land_radius)
                    mark(plan_tables.members[k].pos, land_bad);
            // The landing hits unseen enemies too, which land_at cannot price: keep it off a
            // tracked Ren whose retaliation kills us, as cast_at_enemies does.
            for (const auto& e : world.enemies)
                if (unseen_suicidal(e, health, world.me().taken))
                    for (auto p : positions_within(e.possible, here, grid_r + land_radius)) mark(p, land_bad);
        }
        land_here = landings(cell(here));
        plain_here = land_here & ~land_hits;
        dom_dw = dilate(land_here) & free_;
    }
    return true;
}

// A basic attack on unit t with its splash and kill; false if not allowed: retaliation that kills
// us, or a camp hit for nothing.
bool Search::hit_unit(int t, Node& s) {
    const auto& x = u[t];
    float value = 0, retaliation = 0;
    const auto dealt = [&](int k) { return strength * u[k].taken; };
    const float d = dealt(t);
    const bool kill = d >= h[t] - 0.01f;
    const auto splashed = [&](int k) { return splash && k != t && dist(u[k].pos, x.pos) <= 1; };
    if (x.foe) {
        const bool m = x.link >= 0 && moot(t, d, splashed(x.link), dealt(x.link));
        if (!m) value += hit_worth(d, h[t], x.spawn, x.bag, partner(t), x.full);
        if (!m && s.armed && x.stunnable && !(s.stunned >> t & 1)) value += x.stun, s.stunned |= static_cast<std::uint16_t>(1u << t);
        retaliation += x.retaliation;
    } else {
        s.touched |= 1u << x.local;
    }
    lose(t, d, s);
    if (splash) {
        for (int j = 0; j < n; ++j) {
            if (j == t || h[j] <= 0 || dist(u[j].pos, x.pos) > 1) continue;
            const auto& o = u[j];
            if (o.foe) {
                const bool m = o.link >= 0 && moot(j, dealt(j), splashed(o.link) && o.link > j, dealt(o.link));
                if (!m) value += hit_worth(dealt(j), h[j], o.spawn, o.bag, partner(j), o.full);
                retaliation += o.retaliation;
            }
            lose(j, dealt(j), s);
        }
        s.touched |= touch1(x.pos);
    }
    if (s.hurt + retaliation >= health) return false;
    value -= retaliation;
    if (value < 0 || (!x.foe && value <= 0 && !(vendetta && kill))) return false;
    s.hurt += retaliation;
    s.value += value;
    s.armed = false;
    s.attack = false;
    s.owed = false;
    if (!melee) s.walk = false;
    if (vendetta && kill) {
        // Both cooldowns end; the turn's one cast still stands, and the cast spent comes back.
        s.reset = reset >= 0;
        s.dash = moves && dash >= 0;
        s.value += s.pending;
        s.pending = 0;
    }
    return true;
}

bool Search::spell_unit(const Spell& sp, int t, Node& s) {
    const auto& x = u[t];
    const float d = x.spell[sp.slot];
    const float back = d > 0 ? x.retaliation : 0.0f;
    if (x.suicidal[sp.slot] || (back > 0 && s.hurt + back >= health)) return false;
    float v = hit_worth(d, h[t], x.spawn, x.bag, partner(t), x.full) - back;
    if (d > 0 && d < h[t] - 0.01f && !x.spawn && x.recall) v += params::recall_value;
    if (x.spell_stun[sp.slot] > 0 && !(s.stunned >> t & 1)) v += x.spell_stun[sp.slot], s.stunned |= static_cast<std::uint16_t>(1u << t);
    if (d <= 0 && v <= 0) return false;
    lose(t, d, s);
    s.hurt += back;
    s.value += v - cast_cost;
    s.pending = cast_cost;
    s.cast = false;
    s.owed = false;
    if (sp.excl) s.excl = true, s.walk = false;
    return true;
}

float Search::centre_value(const Centre& c, int slot, const Node& s, bool& ok, float& back) const {
    ok = !c.banned;
    back = 0;
    float v = c.unseen;
    for (std::uint32_t m = c.foes; m && ok; m &= m - 1) {
        const int t = std::countr_zero(m);
        const auto& x = u[t];
        if (h[t] <= 0) continue;
        const float d = x.spell[slot];
        if (d > 0) v -= x.retaliation, back += x.retaliation;
        if (x.link >= 0 && moot(t, d, x.link > t && (c.foes >> x.link & 1), u[x.link].spell[slot])) continue;
        v += hit_worth(d, h[t], x.spawn, x.bag, partner(t), x.full);
        if (d > 0 && d < h[t] - 0.01f && !x.spawn && x.recall) v += params::recall_value;
        if (!(s.stunned >> t & 1)) v += x.spell_stun[slot];
    }
    ok = ok && (back == 0 || s.hurt + back < health);
    return v;
}

void Search::hit_centre(const Centre& c, int slot, Node& s) {
    bool ok;
    float back;
    s.value += centre_value(c, slot, s, ok, back) - cast_cost;
    s.hurt += back;
    // The stuns centre_value credited, all before a death can take one back.
    for (std::uint32_t m = c.foes; m; m &= m - 1) {
        const int t = std::countr_zero(m);
        const auto& x = u[t];
        if (h[t] > 0 && x.spell_stun[slot] > 0
            && !(x.link >= 0 && moot(t, x.spell[slot], x.link > t && (c.foes >> x.link & 1), u[x.link].spell[slot])))
            s.stunned |= static_cast<std::uint16_t>(1u << t);
    }
    for (std::uint32_t m = c.foes; m; m &= m - 1) {
        const int t = std::countr_zero(m);
        if (h[t] > 0) lose(t, u[t].spell[slot], s);
    }
    s.touched |= c.touched;
    s.pending = cast_cost;
    s.cast = false;
    if (spells[slot].excl) s.excl = true, s.walk = false;
}

bool Search::land_at(int c, Node& s) {
    float value = 0, retaliation = 0;
    bool struck = false;
    const vec2 L = tile(c);
    const int k = cell_class[c];
    for (std::uint32_t near = class_foes[k]; near; near &= near - 1) {
        const int t = std::countr_zero(near);
        const auto& x = u[t];
        if (h[t] <= 0) continue;
        struck |= x.land > 0 || x.land_stun > 0;
        const bool m = x.link >= 0 && moot(t, x.land, x.link > t && dist(L, u[x.link].pos) <= land_radius, u[x.link].land);
        if (!m) value += hit_worth(x.land, h[t], x.spawn, x.bag, partner(t), x.full);
        if (!m && x.land_stun > 0 && !(s.stunned >> t & 1)) value += x.land_stun, s.stunned |= static_cast<std::uint16_t>(1u << t);
        retaliation += x.land > 0 ? x.retaliation : 0.0f;
        lose(t, x.land, s);
    }
    if (s.hurt + retaliation >= health) return false;
    s.hurt += retaliation;
    s.touched |= class_touch[k];
    s.value += value - retaliation;
    s.owed = !struck;
    return true;
}

void Search::find_wakers(int k) {
    wakers_known |= 1u << k;
    waker_begin[k] = static_cast<std::uint8_t>(n_wakers);
    const int g = groups[k];
    const auto& c = world.camps[g];
    const auto& members = world.map().groups[g].members;
    const int next = world.round + 1;
    if (!wakers_known_slot) self_slot = world.slot(world.me(), next), wakers_known_slot = true;
    for (std::size_t i = 0; i < members.size() && n_wakers < max_members; ++i) {
        const auto& mb = members[i];
        if (c.health[i] <= 0 || mb.strength <= 0 || !c.maybe_asleep(i)) continue;
        Waker w{mb.pos, mb.strength, mb.reach, mb.type == cambc::camp_type::monolith, mb.reach + 1, 0, -1};
        const auto consider = [&](const ChampionBelief& o, int ally) {
            const int d = dist(o.pos, mb.pos);
            if (d > mb.reach || d > w.other_d) return;
            const int sl = world.slot(o, next);
            if (d == w.other_d && sl > w.other_slot) return;
            w.other_d = d, w.other_slot = sl, w.ally = ally;
        };
        for (std::size_t a = 0; a < world.allies.size() && a < 8; ++a) {
            const auto& o = world.allies[a];
            if (!o.is_self && o.alive && o.visible) consider(o, static_cast<int>(a));
        }
        for (const auto& o : world.enemies)
            if (o.alive && o.visible && (o.acted || o.channel != Channel::none)) consider(o, -1);
        plan_tables.wakers[n_wakers++] = w;
    }
    waker_end[k] = static_cast<std::uint8_t>(n_wakers);
}

// What the touched groups' sleeping strikers would hit: each the nearest champion in its reach,
// ties to the first to act next round, among us at E, the allies we see and the enemies held in
// place (acted this round, or channelling). A hit on an enemy earns nothing for now. False for the
// bans: a sleeping Monolith; a woken hit on an ally recalling, tributing or holding a capture; a
// woken hit that could kill an ally. `on_us`: the woken hits on us, which callers weigh against
// our health after this turn's retaliation.
bool Search::wake(std::uint32_t touched, vec2 E, float& cost, float& on_us) {
    cost = 0;
    on_us = 0;
    std::array<float, 8> ally_hit{};
    for (std::uint32_t m = touched; m; m &= m - 1) {
        const int k = std::countr_zero(m);
        if (!(wakers_known >> k & 1)) find_wakers(k);
        for (int i = waker_begin[k]; i < waker_end[k]; ++i) {
            const auto& w = plan_tables.wakers[i];
            if (w.monolith) return false;
            const int d = dist(E, w.pos);
            if (d <= w.reach && (d < w.other_d || (d == w.other_d && self_slot < w.other_slot))) {
                // Awake, it hits us every camp phase we are in its reach: the next one, and one
                // more for each step still inside it on the walk out.
                if (camp_taken < 0) camp_taken = camp_hit_factor();
                const float hits = static_cast<float>(w.reach - d + 1) * camp_taken;
                cost += w.strength * hits;
                on_us += w.strength * hits;
            } else if (w.other_d <= w.reach && w.ally >= 0) {
                const auto& o = world.allies[static_cast<std::size_t>(w.ally)];
                if (real_recall(o) || o.channel == Channel::tribute) return false;
                if (const int at = world.map().group_at(o.pos); at >= 0 && world.camps[at].state == CampState::cleared) return false;
                if ((ally_hit[static_cast<std::size_t>(w.ally)] += w.strength) >= o.health) return false;
                cost += w.strength * (o.acted ? 1.0f : 0.5f);
            }
        }
    }
    return true;
}

float Search::leaf_value(const Node& s) const {
    return s.value + (s.walk && !s.excl && walks ? step : 0.0f);
}

Node Search::root() const {
    Node s;
    s.walk = can_walk && moves;
    s.attack = can_attack;
    s.cast = can_cast;
    s.reset = reset_ready;
    s.dash = dash_ready;
    for (int t = 0; t < n; ++t)
        if (h[t] <= 0) s.dead |= static_cast<std::uint16_t>(1u << t);
    return s;
}

// Offers the leaf at each end tile in `ends`; mid(c, w, d) names the walk and dash cells for one
// it improves.
template <class Mid> void Search::offer(Grid ends, float v, const Node& s, std::int16_t& leaf, Mid&& mid) {
    ends &= ~guarded;
    const std::uint16_t r = ends ? removed(s) : 0;
    each_bit(ends, [&](int c) {
        ++offers;
        float x = v;
        if (s.touched) {
            float cost, on_us;
            if (!wake_at(s.touched, c, cost, on_us) || s.hurt + on_us >= health) return;
            x -= cost;
        }
        const auto place = [&](bool keep, float val, std::int8_t mate, bool first) __attribute__((always_inline)) {
            auto& fr = (keep ? plan_tables.kept : best)[c];
            Grid& got = keep ? kept_has : has;
            if (!(got & gbit(c))) fr.n = 0;
            if (leaf < 0 && n_leaves == static_cast<int>(plan_tables.leaves.size())) {
                // Offers to tiles a deferred guard may cover take leaves too: none may be lost.
                debug_block({ std::printf("SRCH-LEAVES-FULL %d %u\n", world.round, static_cast<unsigned>(world.me().handle)); });
                return;
            }
            const int i = fr.admit(val, r);
            got |= gbit(c);
            if (i < 0) return;
            if (leaf < 0) {
                leaf = static_cast<std::int16_t>(n_leaves++);
                auto& l = plan_tables.leaves[leaf];
                l.seq.n = s.depth;
                for (int k = 0; k < s.depth; ++k) l.seq.a[k] = stack[k];
                for (int k = 0; k < n_hors; ++k) l.hor[k] = h[hor_unit[k]];
            }
            std::int8_t w = -1, d = -1;
            mid(c, w, d);
            fr.e[i] = {val, leaf, w, d, mate, first, r};
        };
        // A cast left over goes to a heal now, or to the shield, priced with the tile's danger.
        place(s.cast && shield >= 0, x, -1, false);
        if (s.cast && heal >= 0) {
            std::int8_t who;
            bool first;
            if (const float hv = heal_from(c, who, first); hv > 0) place(false, x + hv, who, first);
        }
    });
}

// Each end tile a leaf's moves can reach, offered once.
void Search::settle(const Node& s) {
    if (s.owed) return;
    const float v = leaf_value(s);
    std::int16_t leaf = -1;
    switch (s.seg) {
    case at_start: offer(gbit(cell(here)), v, s, leaf, [](int, std::int8_t&, std::int8_t&) {}); break;
    case walked: offer(free_n_at(s.open_w) & s.req_w, v, s, leaf, [](int c, std::int8_t& w, std::int8_t&) { w = static_cast<std::int8_t>(c); }); break;
    case dashed: {
        const Grid ends = (s.lset ? s.lset : plain_here_at(s.open_d)) & s.req_d;
        offer(ends, v, s, leaf, [](int c, std::int8_t&, std::int8_t& d) { d = static_cast<std::int8_t>(c); });
        break;
    }
    case walked_dashed: {
        const Grid allowed = (s.lset ? s.lset : ~land_hits) & s.req_d, mids = free_n_at(s.open_w) & s.req_w;
        Grid ends = 0;
        each_bit(mids, [&](int m) { ends |= landings_at(m, s.open_d); });
        // Each end's walk tile: the first mid it lands from, found for all ends on first need.
        std::array<std::int8_t, grid_cells> first;
        bool firsts = false;
        offer(ends & allowed, v, s, leaf, [&](int c, std::int8_t& w, std::int8_t& d) {
            if (!firsts) {
                firsts = true;
                Grid left = ends & allowed;
                each_bit(mids, [&](int m) {
                    const Grid now = landings_at(m, s.open_d) & left;
                    left &= ~now;
                    each_bit(now, [&](int e) { first[e] = static_cast<std::int8_t>(m); });
                });
            }
            w = first[c];
            d = static_cast<std::int8_t>(c);
        });
        break;
    }
    case dashed_walked: {
        const Grid from = (s.lset ? s.lset : plain_here_at(s.open_d)) & s.req_d;
        offer(dilate(from) & (free_ | s.open_w) & s.req_e, v, s, leaf, [&](int c, std::int8_t& w, std::int8_t& d) {
            w = static_cast<std::int8_t>(c);
            d = static_cast<std::int8_t>(std::countr_zero(dilate(gbit(c)) & from));
        });
        break;
    }
    }
}

// Narrows the current move's end tiles to `legal`; false if none is left.
bool Search::legal_at(Node& s, Grid legal) {
    switch (s.seg) {
    case at_start: return legal & gbit(cell(here));
    case walked: return (free_n_at(s.open_w) & (s.req_w &= legal)) != 0;
    case dashed: return ((s.lset ? s.lset : plain_here_at(s.open_d)) & (s.req_d &= legal)) != 0;
    case walked_dashed: return ((s.lset ? s.lset : ~land_hits) & (s.req_d &= legal)) != 0;
    case dashed_walked: {
        const Grid dom = dilate((s.lset ? s.lset : plain_here_at(s.open_d)) & s.req_d) & (free_ | s.open_w);
        return (dom & (s.req_e &= legal)) != 0;
    }
    }
    return false;
}

void Search::grow(const Node& s) {
    throw_if_stale();
    if (nodes >= max_nodes) return;
    ++nodes;
    settle(s);
    if (s.depth == max_depth || walked_attack(s)) return;
    const UnitHealths saved = h;
    const auto push = [&](Node& c, Act a) {
        stack[s.depth] = a;
        c.depth = static_cast<std::int8_t>(s.depth + 1);
        grow(c);
        h = saved;
    };
    // Legality is settled before a child is copied.
    const Grid here_bit = gbit(cell(here));
    const auto open = [&](Grid legal) __attribute__((always_inline)) {
        switch (s.seg) {
        case at_start: return (legal & here_bit) != 0;
        case walked: return (free_n_at(s.open_w) & s.req_w & legal) != 0;
        case dashed: return ((s.lset ? s.lset : plain_here_at(s.open_d)) & s.req_d & legal) != 0;
        case walked_dashed: return ((s.lset ? s.lset : ~land_hits) & s.req_d & legal) != 0;
        case dashed_walked: return true;
        }
        return false;
    };
    // A kill so far frees its tile for the moves after it.
    const Grid opened_now = opened(s);
    if (s.attack)
        for (int t = 0; t < n; ++t) {
            if (h[t] <= 0 || !open(u[t].legal) || hoisted(s, t)) continue;
            Node c = s;
            if (legal_at(c, u[t].legal) && hit_unit(t, c)) {
                if (s.depth == 0 && h[t] > 0 && u[t].link < 0 && !u[t].spawn && partner(t) >= saved[t])
                    soft_first |= static_cast<std::uint16_t>(1u << t);
                push(c, {Op::attack, static_cast<std::int8_t>(t)});
            } else {
                h = saved;
            }
        }
    if (s.cast && s.reset && !s.attack) {
        Node c = s;
        c.attack = true, c.cast = false, c.reset = false, c.armed = arms, c.pending = 0;
        push(c, {Op::reset});
    }
    if (s.walk && !s.excl && (melee || s.attack) && (s.seg == at_start || s.seg == dashed)) {
        Node c = s;
        c.walk = false, c.owed = true, c.open_w = opened_now;
        if (!melee) c.attack = false;
        c.seg = s.seg == at_start ? walked : dashed_walked;
        // A walk back onto a landing is the dash alone, with the walk to spare.
        if (c.seg == dashed_walked) c.req_e = ~((s.lset ? s.lset : plain_here_at(s.open_d)) & s.req_d);
        const Grid dom = (c.seg == walked ? free_n_at(opened_now)
                          : s.lset        ? dilate(s.lset & s.req_d) & (free_ | opened_now)
                          : opened_now    ? dilate(plain_here_at(s.open_d) & s.req_d) & (free_ | opened_now)
                                          : dom_dw & dilate(plain_here_at(s.open_d) & s.req_d)) &
                         c.req_e;
        if (dom && strikes_left(c)) push(c, {Op::walk});
    }
    if (s.cast && s.dash && (s.seg == at_start || s.seg == walked)) {
        const bool first = s.seg == at_start;
        // Landings from the walk tiles the actions so far still allow.
        Grid reach = land_here_at(opened_now);
        if (!first) {
            reach = 0;
            each_bit(free_n_at(s.open_w) & s.req_w, [&](int m) { reach |= landings_at(m, opened_now); });
            // Straight after the walk, a landing the start tile reaches is the dash alone, with
            // the walk to spare.
            if (stack[s.depth - 1].op == Op::walk) reach &= ~land_here_at(opened_now);
        }
        Node c = s;
        c.cast = false, c.dash = false, c.value -= dash_cost, c.pending = dash_cost, c.req_d = reach, c.owed = true;
        c.open_d = opened_now;
        c.seg = first ? dashed : walked_dashed;
        if ((reach & ~land_hits) != 0 && strikes_left(c)) push(c, {Op::dash});
        // Landings wake no sleeper, so those hitting the same foes and camp groups are alike.
        if (const Grid hits = lands ? reach & land_hits : 0) {
            std::uint32_t alive = 0;
            for (int t = 0; t < foes; ++t)
                if (h[t] > 0) alive |= 1u << t;
            // Nodes before any kill share their landings' groups.
            if (hits != groups_hits || alive != groups_alive) groups_hits = hits, groups_alive = alive, group_landings(hits, alive);
            const int kinds = n_land_groups;
            std::array<Grid, grid_cells> alike;
            std::copy_n(land_groups.begin(), kinds, alike.begin());
            for (int i = 0; i < kinds; ++i) {
                Node d = c;
                if (land_at(std::countr_zero(alike[i]), d)) {
                    d.lset = alike[i];
                    push(d, {Op::dash});
                } else {
                    h = saved;
                }
            }
        }
    }
    if (s.cast)
        for (const auto& sp : spells) {
            if (sp.slot < 0 || (sp.excl && s.seg != at_start)) continue;
            if (sp.unit) {
                for (int t = 0; t < foes; ++t) {
                    if (h[t] <= 0 || !open(u[t].cast_legal)) continue;
                    Node c = s;
                    if (legal_at(c, u[t].cast_legal) && spell_unit(sp, t, c))
                        push(c, {Op::spell, static_cast<std::int8_t>(t), static_cast<std::int8_t>(sp.slot)});
                    else h = saved;
                }
            } else if (sp.ground && sp.excl && s.seg == at_start) {
                // The cast ends the moves here: of the centres that damage the same foes, only the
                // best can lead to the best leaf.
                std::array<float, 16> top;
                std::array<int, 16> which;
                std::array<std::uint16_t, 16> masks;
                int kinds = 0;
                for (int q = 0; q < n_distinct; ++q) {
                    const int k = plan_tables.distinct[q];
                    const auto& ce = plan_tables.centres[k];
                    bool ok;
                    float back;
                    float v = centre_value(ce, sp.slot, s, ok, back);
                    if (!ok) continue;
                    float cost = 0, on_us = 0;
                    if ((ce.touched | s.touched) && (!wake_here(ce.touched | s.touched, cost, on_us) || s.hurt + back + on_us >= health))
                        continue;
                    v -= cost;
                    std::uint16_t mask = 0;
                    for (std::uint32_t m = ce.foes; m; m &= m - 1)
                        if (h[std::countr_zero(m)] > 0) mask |= static_cast<std::uint16_t>(m & (~m + 1));
                    int i = 0;
                    while (i < kinds && masks[i] != mask) ++i;
                    if (i == kinds) {
                        if (kinds == 16) continue;
                        masks[kinds] = mask, top[kinds] = v, which[kinds] = k, ++kinds;
                    } else if (v > top[i]) {
                        top[i] = v, which[i] = k;
                    }
                }
                for (int i = 0; i < kinds; ++i) {
                    Node c = s;
                    hit_centre(plan_tables.centres[which[i]], sp.slot, c);
                    push(c, {Op::spell, -1, static_cast<std::int8_t>(sp.slot), plan_tables.centres[which[i]].tile});
                }
            }
        }
}

// What the search would find, shown without it: 0 if read() takes no foe; 1 if it takes one but no
// strike reaches any foe from any end tile, so the start tile's leaf, nothing done, is the only one
// offered and is chosen; 3 the same with the shield cast; 2 if none is shown. Read's tests, by
// distance alone.
int strike_free(const World& world, Pathing& pathing, Safety& safety, const Intent& intent, std::array<bool, 2>& ready, bool& known) {
    const auto& f = world.me().facts();
    const auto& record = my_record();
    const vec2 here{record.x, record.y};
    const auto state = cambc::champion_state::from_bits_retain(record.state);
    const bool can_walk = state.contains(cambc::champion_state::can_move), can_attack = state.contains(cambc::champion_state::can_attack);
    const bool can_cast = state.contains(cambc::champion_state::can_cast);
    const bool moves = !intent.anchored || intent.hold, walked_first = here != world.turn_start;
    const bool splash = f.passive == Passive::splash_attack;
    // A ranged walk alone is offered as a leaf on every tile it reaches.
    if (!f.walk_and_attack_independent() && can_walk && moves && !walked_first) return 2;
    ready = {can_cast && slot_ready(world, 0), can_cast && slot_ready(world, 1)};
    known = true;
    const int reset = f.slot_of(AbilityKind::attack_reset), dash = f.slot_of(AbilityKind::dash);
    const bool reset_ready = reset >= 0 && ready[reset], dash_ready = moves && dash >= 0 && ready[dash];
    const int walk = moves && can_walk ? 1 : 0;
    int bound = can_attack || reset_ready ? f.attack_range() + walk + (dash_ready ? dash_range : 0) + (splash ? splash_radius : 0) : -1;
    bool stuns = reset >= 0 && f.abilities[reset].stuns, casts = false;
    int shield = -1;
    for (int s = 0; s < 2; ++s) {
        const auto& a = f.abilities[s];
        if (!ready[s]) continue;
        if (a.kind == AbilityKind::heal) return 2;
        if (a.kind == AbilityKind::shield) shield = s;
        if (a.hits_enemies()) stuns |= a.stuns, casts |= !a.lands();
        if ((a.kind == AbilityKind::damage || a.kind == AbilityKind::stun) && (a.target == Targeting::unit || a.target == Targeting::ground)
            && !(a.excludes_walking && walked_first)) {
            // Its centres include unseen enemies' tiles.
            if (a.target == Targeting::ground)
                for (const auto& e : world.enemies)
                    if (e.alive && !e.visible && e.tracked) return 2;
            bound = std::max(bound, a.reach() + (a.excludes_walking ? 0 : 1));
        }
        if (a.lands() && dash_ready) bound = std::max(bound, walk + dash_range + a.radius);
    }
    // With the shield kept, a reset alone (the attack spent) is a leaf of its own.
    if (shield >= 0 && reset_ready && !can_attack) return 2;
    const int reach = std::max(grid_r + f.attack_range() + (splash ? splash_radius : 0), ability_range + 1);
    bool any = false;
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible || e.stats_round != world.round || dist(here, e.pos) > reach) continue;
        if (dist(here, e.pos) <= bound) return 2;
        if (any) continue;
        try {
            if (!visible_record(e.handle)) continue;
            if (e.shield > 0 || stuns) (void)buff_state(e.handle);
            if (casts && e.channel == Channel::recall) (void)aph::kept_recall(e.handle, e.recall_turns());
            any = true;
        } catch (const cambc::error&) {
        }
    }
    if (!any) return 0;
    // Vendetta's camp kill is a leaf, and readies the dash.
    if (f.passive == Passive::reset_on_kill)
        for (int g : world.map().groups_near(here, grid_r + f.attack_range() + 1)) {
            if (world.camps[g].state != CampState::alive) continue;
            const auto& members = world.map().groups[g].members;
            for (std::size_t i = 0; i < members.size(); ++i)
                if (world.camps[g].health[i] > 0 && dist(here, members[i].pos) <= grid_r + f.attack_range()) return 2;
        }
    // read_geometry works out a guard deferred without a cover.
    if (moves && !pathing.cover_deferred()) (void)pathing.guard();
    // The kept cast goes to the shield if it would absorb anything here.
    if (shield >= 0) {
        float amount = 0;
        try {
            amount = my_shield(shield);
        } catch (const cambc::error&) {
        }
        if (amount > 0 && static_cast<float>(f.abilities[shield].duration) * safety.damage_bound(here, false, world.me().taken) > 0) return 3;
    }
    return 1;
}

} // namespace

void warm_tile(const World& world, vec2 p) {
    warm_reach_tile(world, p);
    const auto i = static_cast<std::size_t>(p.x + p.y * world.map().width);
    if (i >= viewer_rows_known[0].size()) return;
    const int ranges[2] = {ability_range, world.me().facts().attack_range()};
    for (int s = 0; s < 2; ++s)
        if (!viewer_rows_known[s][i]) fill_viewer_rows(world, p, ranges[s], viewer_rows_cache[s][i]), viewer_rows_known[s][i] = 1;
}

bool strike_possible(const World& world) {
    const auto& self = world.me();
    if (!self.alive || !enemy_seen(world)) return false;
    const auto& f = self.facts();
    const int reach = f.basic_reach() + 1 + (f.has_dash() ? dash_range : 0);
    return enemy_within(world, my_position(), std::max(ability_range + 1, reach));
}

[[gnu::flatten]] Planned plan_strikes(const World& world, Pathing& pathing, Safety& safety, const Intent& intent) {
    Planned out;
    std::uint64_t fuel_start = 0;
    if constexpr (debug_search) {
        debug_block({ fuel_start = fuel(); });
    }
    std::array<bool, 2> ready;
    bool ready_known = false;
    const int empty = strike_free(world, pathing, safety, intent, ready, ready_known);
    if (!debug_strike_free && empty == 0) return out;
    if (!debug_strike_free && (empty == 1 || empty == 3)) {
        throw_if_stale();
        world.throw_if_stale();
        bool ok = true;
        if (empty == 3) try {
                ok = cast_slot(world.me().facts().slot_of(AbilityKind::shield));
            } catch (const cambc::error&) {
                ok = false;
            }
        pathing.restore_guard(pathing.held_guard()); // as the search's moves leave it
        world.throw_if_stale();
        if (!ok) out.attacked |= strike_enemy(world);
        out.searched = ok;
        return out;
    }
    Search S(world, safety, pathing, intent);
    if (ready_known) S.ready = ready, S.ready_known = true;
    std::array<std::uint64_t, 4> marks{};
    const auto mark = [&](int i) {
        if constexpr (debug_search) {
            debug_block({ marks[i] = fuel(); });
        }
    };
    if (!S.read()) {
        if constexpr (debug_strike_free) {
            debug_block({
                if (empty == 1 || empty == 3) std::printf("SRCH-FREE %d %u no-foe\n", world.round, static_cast<unsigned>(world.me().handle));
            });
        }
        return out;
    }
    if constexpr (debug_strike_free) {
        debug_block({
            if (empty == 0) std::printf("SRCH-FREE %d %u foe\n", world.round, static_cast<unsigned>(world.me().handle));
        });
    }
    throw_if_stale();
    mark(0);
    // A ranged walk spends the attack, and grow() keeps such a walk only once a strike follows it:
    // offer the walk alone as a terminal leaf, priced at its end tile, against striking from here.
    if (!S.melee && S.can_walk && S.moves && !S.walked_first) {
        Node walk = S.root();
        walk.seg = walked;
        walk.walk = walk.attack = walk.owed = false;
        walk.depth = 1;
        S.stack[0] = {Op::walk};
        S.settle(walk);
    }
    S.grow(S.root());
    mark(1);
    const vec2 here = S.here;

    // Price the end tiles best bound first, the bound being hits and progress less the camps;
    // then each foe's Reach blow, largest Strike share first, while the tile can still win.
    struct Striker {
        const ChampionBelief* e;
        const Strike* strike;
        int hor;
    };
    std::array<Striker, 16> strikers;
    int ns = 0;
    for (const auto& e : world.enemies) {
        if (ns == 16 || !e.alive || !e.visible || dist(here, e.pos) > Strike::max_reach + grid_r) continue;
        const Strike& strike = safety.strike_of(e);
        if (strike.reach < 0) continue;
        int hor = -1;
        for (int k = 0; k < S.n_hors; ++k)
            if (S.hors[k] == &e) hor = k;
        strikers[ns++] = {&e, &strike, hor};
    }
    Unwritten<Safety::CampHit, 24> camp_hits;
    auto& camps = camp_hits.a;
    int nc = 0;
    for (const auto& m : safety.awake_members())
        if (nc < 24 && dist(here, m.pos) <= m.reach + grid_r) camps[nc++] = m;
    // An enemy Heart of Ruin hurt but not killed hits harder.
    const auto factor = [&](int leaf, int hor) {
        if (hor < 0 || leaf < 0) return 1.0f;
        const auto& e = *S.hors[hor];
        const float hp = std::min(e.health, S.hor_health(leaf, hor));
        if (hp <= 0 || e.damage_scale() <= 0) return 1.0f;
        return damage_scale(Passive::missing_health, hp, e.max_health) * e.dealt / e.damage_scale();
    };
    const auto camp_at = [&](vec2 p) {
        float camp = 0;
        for (int k = 0; k < nc; ++k)
            if (dist(p, camps[k].pos) <= camps[k].reach && !camps[k].stunned) camp += camps[k].strength * camps[k].weight;
        return camp;
    };
    // Picked by their bound before the camps, which can only lower it. Each tile's candidates are
    // its best leaves per set of enemies removed, with the cast spent (or on a heal) or kept for
    // the shield, bounded by the shield's whole amount until the tile is priced.
    struct Tile {
        int c;
        float bound, total, shield, gain;
        bool exact, done, keep;
        std::int8_t entry;
    };
    struct Cand {
        float raw, d;
        int leaf;
        std::uint16_t removed;
        bool keep;
        std::int8_t entry;
    };
    std::array<Tile, grid_cells> tiles;
    std::array<Cand, 2 * max_sets> cand;
    int nt = 0;
    const float shield_top = S.shield >= 0 ? S.shield_amount : 0.0f;
    const auto gather = [&](int c) {
        int k = 0;
        for (int keep = 0; keep < 2; ++keep) {
            if (!((keep ? S.kept_has : S.has) >> c & 1)) continue;
            const auto& fr = (keep ? plan_tables.kept : S.best)[c];
            for (int i = 0; i < fr.n; ++i)
                cand[k++] = {fr.e[i].raw, 0, fr.e[i].leaf, fr.e[i].removed, keep == 1, static_cast<std::int8_t>(i)};
        }
        return k;
    };
    each_bit(S.has | S.kept_has, [&](int c) {
        float top = -1e30f;
        if (S.has >> c & 1) top = S.best[c].top();
        if (S.kept_has >> c & 1) top = std::max(top, plan_tables.kept[c].top() + shield_top);
        tiles[nt++] = {c, top, top, 0, 0, false, false, !(S.has >> c & 1), 0};
    });
    // Tiles the deferred guard may cover count once it is worked out.
    int sure = 0;
    for (int i = 0; i < nt; ++i) sure += !(S.maybe_guarded >> tiles[i].c & 1);
    if (sure < 2 && sure < nt && S.walks) S.resolve_guard();
    int unguarded = 0;
    for (int i = 0; i < nt; ++i) unguarded += !(S.guarded >> tiles[i].c & 1);
    // Progress along the goal walk only ranks tiles against each other: a lone tile is chosen
    // whatever it adds.
    if (const Field* field = unguarded >= 2 && S.walks ? goal_field(world, pathing, intent) : nullptr)
        if (const int here_steps = field->at(here); here_steps != unreachable)
            for (int i = 0; i < nt; ++i) {
                auto& t = tiles[i];
                if (const int c = field->at(S.tile(t.c)); c != unreachable) t.gain = static_cast<float>(here_steps - c) * S.step;
                t.total = t.bound = t.bound + t.gain;
            }
    float best_total = -1e30f;
    int chosen = -1, queries = 0, priced = 0, share_stops = 0, bound_stops = 0;
    bool capped = false;
    for (;;) {
        int i = -1;
        for (int k = 0; k < nt; ++k)
            if (!tiles[k].done && (i < 0 || tiles[k].bound > tiles[i].bound)) i = k;
        if (i < 0 || tiles[i].bound <= best_total) break;
        if (S.maybe_guarded >> tiles[i].c & 1) S.resolve_guard();
        if (S.guarded >> tiles[i].c & 1) {
            tiles[i].done = true;
            continue;
        }
        if (queries >= max_exact_queries) {
            capped = true;
            break;
        }
        throw_if_stale();
        auto& t = tiles[i];
        t.done = true;
        const vec2 p = S.tile(t.c);
        const float camp = camp_at(p);
        t.bound -= camp;
        t.total = t.bound;
        if (t.bound <= best_total) {
            ++bound_stops;
            continue;
        }
        const float base = t.gain - camp;
        const int nk = gather(t.c);
        bool kept = false;
        std::uint16_t all_removed = 0xffff;
        for (int j = 0; j < nk; ++j) kept |= cand[j].keep, all_removed &= cand[j].removed;
        float sh = shield_top;
        int arg = 0;
        const auto top = [&] {
            float x = -1e30f;
            for (int j = 0; j < nk; ++j)
                if (const float y = cand[j].raw + (cand[j].keep ? sh : 0.0f) - cand[j].d; y > x) x = y, arg = j;
            return x + base;
        };
        const auto add = [&](int enemy, float b, int hor) {
            if (hor < 0) {
                for (int j = 0; j < nk; ++j)
                    if (!(cand[j].removed >> enemy & 1)) cand[j].d += b;
                return;
            }
            for (int j = 0; j < nk; ++j)
                if (!(cand[j].removed >> enemy & 1)) cand[j].d += b * factor(cand[j].leaf, hor);
        };
        // add() then top() in one pass.
        const auto add_top = [&](int enemy, float b, int hor) {
            float x = -1e30f;
            for (int j = 0; j < nk; ++j) {
                auto& q = cand[j];
                if (!(q.removed >> enemy & 1)) q.d += hor < 0 ? b : b * factor(q.leaf, hor);
                if (const float y = q.raw + (q.keep ? sh : 0.0f) - q.d; y > x) x = y, arg = j;
            }
            return x + base;
        };
        Unwritten<std::pair<float, int>, 16> ranked;
        auto& order = ranked.a;
        int no = 0;
        for (int k = 0; k < ns; ++k) {
            const auto& sk = strikers[k];
            const int index = sk.e->index;
            if (all_removed >> index & 1) continue;
            const float at = sk.strike->at(dist(p, sk.e->pos));
            if (at <= 0) continue;
            float most = 1;
            if (sk.hor >= 0) {
                most = 0;
                for (int j = 0; j < nk; ++j)
                    if (!(cand[j].removed >> index & 1)) most = std::max(most, factor(cand[j].leaf, sk.hor));
            }
            const float share = safety_params::hit_given_reach * at * most;
            if (share <= 0) continue;
            int m = no++;
            for (; m > 0 && order[m - 1].first < share; --m) order[m] = order[m - 1];
            order[m] = {share, k};
        }
        float total = top();
        bool cut = false;
        for (int m = 0; m < no && !cut; ++m) {
            const auto& sk = strikers[order[m].second];
            const float b = safety_params::hit_given_reach * safety.blow(*sk.e, p).damage;
            ++queries;
            // A miss leaves every candidate, and so the total, as it was.
            if (b == 0) continue;
            total = add_top(sk.e->index, b, sk.hor);
            cut = total <= best_total;
        }
        if (!cut && kept && sh > 0) {
            sh = S.shield_at(p);
            total = top();
            cut = total <= best_total;
        }
        ++priced;
        t.total = total;
        if (cut) {
            ++share_stops;
            continue;
        }
        if (dist(p, here) >= 2) {
            Unwritten<Safety::ThreatAt, 16> threats;
            auto& at = threats.a;
            const int k = safety.threats_at(p, at, true);
            bool added = false;
            for (int m = 0; m < k; ++m)
                if (!world.enemies[static_cast<std::size_t>(at[m].enemy)].visible && at[m].blow.damage != 0)
                    add(at[m].enemy, safety_params::hit_given_reach * at[m].blow.damage, -1), added = true;
            if (added) total = top(), t.total = total;
        }
        // The step guard covers radius 1-2 only. Left inexact, a hidden blocker's re-plan skips it too.
        if (dist(p, here) == grid_r && safety.lethal(p)) continue;
        t.exact = true;
        t.keep = cand[arg].keep;
        t.entry = cand[arg].entry;
        t.shield = t.keep ? sh : 0.0f;
        if (total > best_total) best_total = total, chosen = i;
    }
    // Unpriced tiles keep their Strike price, and no shield.
    if (capped && S.maybe_guarded) {
        for (int i = 0; i < nt; ++i)
            if (!tiles[i].done && (S.maybe_guarded >> tiles[i].c & 1) && dist(S.tile(tiles[i].c), here) != grid_r) S.resolve_guard();
        for (int i = 0; i < nt; ++i)
            if (S.guarded >> tiles[i].c & 1) tiles[i].done = true;
    }
    if (capped)
        for (int i = 0; i < nt; ++i) {
            auto& t = tiles[i];
            const vec2 p = S.tile(t.c);
            if (t.done || dist(p, here) == grid_r) continue;
            const int nk = gather(t.c);
            for (int k = 0; k < ns; ++k) {
                const float b = safety_params::hit_given_reach * strikers[k].strike->at(dist(p, strikers[k].e->pos));
                for (int j = 0; j < nk; ++j)
                    if (!(cand[j].removed >> strikers[k].e->index & 1)) cand[j].d += b * factor(cand[j].leaf, strikers[k].hor);
            }
            int arg = 0;
            for (int j = 1; j < nk; ++j)
                if (cand[j].raw - cand[j].d > cand[arg].raw - cand[arg].d) arg = j;
            t.keep = cand[arg].keep;
            t.entry = cand[arg].entry;
            t.shield = 0;
            t.total = cand[arg].raw - cand[arg].d + t.gain - camp_at(p);
            if (t.total > best_total) best_total = t.total, chosen = i;
        }

    if constexpr (debug_lazy_guard) {
        debug_block({
            if (S.maybe_guarded) S.resolve_guard();
            for (int i = 0; i < nt; ++i)
                if ((S.guarded >> tiles[i].c & 1) && (tiles[i].exact || i == chosen))
                    std::printf("SRCH-GUARD-MISS %d %u cell %d\n", world.round, static_cast<unsigned>(world.me().handle), tiles[i].c);
            if (const bitboard* guard = S.cover ? pathing.guard() : nullptr; guard && (S.read_grid(*guard) & ~gbit(S.cell(here)) & ~S.cover))
                std::printf("SRCH-GUARD-COVER %d %u\n", world.round, static_cast<unsigned>(world.me().handle));
        });
    }
    mark(2);
    // A search that ran out of fuel resumes in the next round: its plan is last round's.
    world.throw_if_stale();
    // Carry it out. A move a hidden unit refuses takes the next-ranked plan from where we stand.
    Seq seq;
    std::array<bool, grid_cells> dropped{};
    const auto concrete = [&](const Tile& t) { return S.concrete(t.c, t.keep, t.entry, t.keep && t.shield > 0); };
    if (chosen >= 0) seq = concrete(tiles[chosen]), dropped[tiles[chosen].c] = true;
    int done = 0;
    bool failed = false;
    // Its walk may end on a guarded tile it passes on the way to a landing.
    const auto guard = pathing.held_guard();
    pathing.set_guard(nullptr);
    while (done < seq.n) {
        // Out of fuel mid-plan, the rest would play in the next round on last round's positions.
        if (done > 0 && world.is_stale()) break;
        const Act a = seq.a[done];
        bool ok = false, blocked = false;
        switch (a.op) {
        case Op::walk: {
            bool refused = true;
            ok = pathing.try_move(a.tile, &refused);
            blocked = !ok && !refused;
            out.moved |= ok;
            break;
        }
        case Op::attack:
            try {
                const auto& x = S.u[a.unit];
                if (x.foe) attack_champion(x.belief->handle);
                else throw_if_stale(), cambc::self().attack(world.map().groups[x.group].camp(x.member));
                ok = true;
                out.attacked = true;
                out.moved |= !S.melee;
            } catch (const cambc::error&) {
            }
            break;
        case Op::reset:
            try {
                ok = cast_slot(S.reset);
            } catch (const cambc::error&) {
            }
            break;
        case Op::dash:
            try {
                ok = cast_slot(S.dash, a.tile);
                blocked = !ok;
                pathing.invalidate();
            } catch (const cambc::error&) {
            }
            break;
        case Op::spell:
            try {
                ok = a.unit >= 0 ? cast_slot_on(a.slot, S.u[a.unit].belief->handle) : cast_slot(a.slot, a.tile);
                out.moved |= ok && S.spells[a.slot].excl;
            } catch (const cambc::error&) {
            }
            break;
        case Op::heal:
            try {
                ok = cast_slot_on(S.heal, S.mates[a.unit]->handle);
            } catch (const cambc::error&) {
            }
            break;
        case Op::shield:
            try {
                ok = cast_slot(S.shield);
            } catch (const cambc::error&) {
            }
            break;
        }
        if (ok) {
            ++done;
            continue;
        }
        if (!blocked) {
            if constexpr (debug_search) {
                debug_block({
                    std::printf("SRCH-REFUSED %d %u op %d unit %d slot %d tile %d,%d step %d\n", world.round,
                                static_cast<unsigned>(world.me().handle), static_cast<int>(a.op), a.unit, a.slot, a.tile.x, a.tile.y, done);
                });
            }
            failed = true;
            break;
        }
        // The next-ranked plan that took the same actions so far, avoiding the revealed tile, also
        // as a dash's only way through. Unpriced tiles 3 away were never checked for lethal danger.
        int alt = -1;
        float alt_total = -1e30f;
        const Grid revealed = gbit(S.cell(a.tile));
        for (int i = 0; i < nt; ++i) {
            const auto& t = tiles[i];
            if (dropped[t.c] || !(t.exact || (capped && !t.done && dist(S.tile(t.c), here) < grid_r)) || t.total <= alt_total) continue;
            const Seq q = concrete(t);
            bool same = q.n > done;
            for (int k = 0; k < done && same; ++k) same = q.a[k] == seq.a[k];
            vec2 at = here;
            for (int k = 0; k < q.n && same; ++k) {
                if (q.a[k].op != Op::walk && q.a[k].op != Op::dash) continue;
                if (k >= done && q.a[k].tile == a.tile) same = false;
                else if (k >= done && q.a[k].op == Op::dash && dist(at, q.a[k].tile) == dash_range)
                    same = (dilate(gbit(S.cell(at))) & dilate(gbit(S.cell(q.a[k].tile))) & S.pass_ & ~revealed) != 0;
                at = q.a[k].tile;
            }
            if (same) alt = i, alt_total = t.total;
        }
        if (alt < 0) {
            failed = true;
            break;
        }
        chosen = alt;
        dropped[tiles[alt].c] = true;
        seq = concrete(tiles[alt]);
    }
    pathing.restore_guard(guard);
    world.throw_if_stale();
    if constexpr (debug_search) {
        debug_block({
            // A first move onto a guarded tile on the way elsewhere, and a plan whose moves stopped
            // short of its end tile.
            if (chosen >= 0) {
                const vec2 end = S.tile(tiles[chosen].c), at = my_position();
                int moves = 0, made = 0;
                vec2 first{-1, -1};
                for (int k = 0; k < seq.n; ++k)
                    if (seq.a[k].op == Op::walk || seq.a[k].op == Op::dash) {
                        if (moves++ == 0) first = seq.a[k].tile;
                        made += k < done;
                    }
                if (moves == 2 && first != end && (S.guarded >> S.cell(first) & 1))
                    std::printf("SRCH-PASS %d %u mid %d,%d end %d,%d made %d\n", world.round, static_cast<unsigned>(world.me().handle), first.x,
                                first.y, end.x, end.y, made);
                if (made > 0 && at != end)
                    std::printf("SRCH-STRANDED %d %u at %d,%d end %d,%d guarded %d failed %d\n", world.round,
                                static_cast<unsigned>(world.me().handle), at.x, at.y, end.x, end.y,
                                static_cast<int>(S.guarded >> S.cell(at) & 1), failed ? 1 : 0);
            }
        });
    }
    mark(3);
    if (failed) out.attacked |= strike_enemy(world);
    // A tile left unpriced by the query cap had no shield priced: the turn's end decides it.
    out.searched = chosen >= 0 && !failed && tiles[chosen].exact;
    if constexpr (debug_strike_free) {
        debug_block({
            const bool shields = seq.n == 1 && seq.a[0].op == Op::shield;
            if ((empty == 1 || empty == 3) && ((empty == 1 ? seq.n > 0 : !shields) || (!out.searched && !(empty == 3 && failed)) || out.moved
                                                || nt != 1 || S.tile(tiles[chosen].c) != here))
                std::printf("SRCH-FREE %d %u acts %d searched %d tiles %d empty %d\n", world.round, static_cast<unsigned>(world.me().handle),
                            seq.n, out.searched ? 1 : 0, nt, empty);
            else if (empty == 1 || empty == 3)
                std::printf("SRCH-FREE-OK %d %u %d\n", world.round, static_cast<unsigned>(world.me().handle), empty);
        });
    }

    if constexpr (debug_search) {
        debug_block({
            const std::uint64_t now = fuel(), used = fuel_start > now ? fuel_start - now : 0;
            char cast = '-';
            for (int k = 0; k < seq.n; ++k)
                if (seq.a[k].op == Op::heal || seq.a[k].op == Op::shield) cast = seq.a[k].op == Op::heal ? 'h' : 's';
            unsigned rm = 0;
            int sets = 0;
            if (chosen >= 0) rm = (tiles[chosen].keep ? plan_tables.kept : S.best)[tiles[chosen].c].e[tiles[chosen].entry].removed;
            for (int i = 0; i < nt; ++i) {
                const int c = tiles[i].c;
                if (S.has >> c & 1) sets = std::max(sets, S.best[c].n);
                if (S.kept_has >> c & 1) sets = std::max(sets, plan_tables.kept[c].n);
            }
            std::printf("SRCH %d %u fuel %llu nodes %d offers %d tiles %d priced %d queries %d boundstop %d sharestop %d capped %d len %d cast %c mates %d read %llu grow %llu price %llu act %llu foes %d units %d rm %x sets %d leaves %d left %llu\n",
                        world.round, static_cast<unsigned>(world.me().handle), static_cast<unsigned long long>(used), S.nodes, S.offers, nt,
                        priced, queries, bound_stops, share_stops, capped ? 1 : 0, seq.n, cast, S.n_mates,
                        static_cast<unsigned long long>(fuel_start - marks[0]), static_cast<unsigned long long>(marks[0] - marks[1]),
                        static_cast<unsigned long long>(marks[1] - marks[2]), static_cast<unsigned long long>(marks[2] - marks[3]), S.foes, S.n,
                        rm, sets, S.n_leaves, static_cast<unsigned long long>(fuel_start));
        });
    }
    return out;
}

Planned strike_after(const World& world, Pathing& pathing, Safety& safety) {
    if (!world.me().alive || world.is_stale()) return {};
    const auto state = my_state();
    if (state.contains(cambc::champion_state::submitting_gems) || state.contains(cambc::champion_state::recalling)
        || state.contains(cambc::champion_state::teleporting))
        return {};
    const auto& self = world.me();
    const auto& f = self.facts();
    const vec2 here = my_position();
    // Only a hit to make: a heal or shield alone is left to the turn's end.
    const bool cast = state.contains(cambc::champion_state::can_cast);
    const int basic = f.basic_reach();
    int reach = state.contains(cambc::champion_state::can_attack) ? basic : -1;
    for (int s = 0; s < 2 && cast; ++s) {
        const auto& a = f.abilities[s];
        if (!slot_ready(world, s)) continue;
        // A reset gives back a spent attack.
        if (a.kind == AbilityKind::attack_reset) reach = std::max(reach, basic);
        else if (a.hits_enemies() && !a.lands() && !(a.excludes_walking && here != world.turn_start)) reach = std::max(reach, a.reach());
    }
    if (reach < 0 || !enemy_seen(world) || !enemy_within(world, here, reach)) return {};
    Intent stay;
    stay.anchored = true;
    return plan_strikes(world, pathing, safety, stay);
}

[[gnu::flatten]] bool strike_enemy(const World& world) {
    if (!world.me().alive || !my_can_attack()) return false;
    Board b;
    const auto& f = world.me().facts();
    if (!read_board(world, b, f.basic_reach())) return false;
    return attack(b, best_hit(b, b.healths()));
}

bool landing_ready(const World& world) {
    const auto& self = world.me();
    const int slot = self.facts().slot_of(AbilityKind::dash);
    return slot >= 0 && self.facts().abilities[slot].lands() && self.ability_ready(slot, world.round);
}

bool reset_may_kill(const World& world) {
    const auto& self = world.me();
    const auto& f = self.facts();
    const int slot = f.slot_of(AbilityKind::attack_reset);
    if (slot < 0 || !self.ability_ready(slot, world.round) || !enemy_seen(world)) return false;
    const int reach = f.attack_range() + (f.walk_and_attack_independent() ? 1 : 0);
    const float strength = my_strength() * damage_scale(f.passive, my_health(), my_max_health()) * champion_dealt_factor();
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && dist(self.pos, e.pos) <= reach && e.health + e.shield <= 2 * strength * e.taken) return true;
    return false;
}

} // namespace aph
