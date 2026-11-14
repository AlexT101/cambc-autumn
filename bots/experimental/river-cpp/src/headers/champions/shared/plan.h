#pragma once

#include "../../../params.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdio>
#include <cstring>
#include "../../comms.h"

namespace aph::dash_route {
struct Board;
}
namespace aph {
struct StaticMap;
struct ChampionBelief;
class World;
class Pathing;
struct Field;
enum class AbilityKind : std::uint8_t;
struct ChampionFacts;
struct Intent;
struct Planned;
}
namespace aph {
namespace {
struct Foe;
struct Board;
struct Hit;
enum class Op : std::uint8_t;
struct Act;
struct Seq;
enum Seg : std::uint8_t;
struct SearchUnit;
struct Centre;
struct Member;
struct Waker;
struct Node;
struct Leaf;
struct Choice;
struct Front;
struct Unseen;
struct Near;
struct SearchTables;
union TableStorage;
struct TerrainGrid;
}
}
namespace aph {
class Safety;
}

namespace aph {
class World;

class Pathing;

class Safety;

// What the turn's goal does after the strikes: stays (holding a capture, at an altar), or walks a
// step along `field` (null: a way the planner cannot read), each step worth `step_value`.
struct Intent {
    bool walks = false;
    bool anchored = false; // must not leave this tile
    // Where the walk goes, read only when a move is priced: to an altar, else to `group`.
    bool to_altar = false;
    int group = -1;
    float step_value = 0;
};

// A visible enemy near enough to strike this turn, by walk, dash and attack range.
bool strike_possible(const World& world);

struct Planned {
    bool attacked = false;
    bool moved = false;    // the goal's walk is spent
    bool searched = false; // the search chose the turn's cast, heals and shields included
};

// Before the goal acts.
Planned plan_strikes(const World& world, Pathing& pathing, Safety& safety, const Intent& intent);

// Turns the search does not plan (a retreat, a heal on spawn): a reset's second attack could kill
// an enemy, or a dash that lands on enemies is ready, so the cast is not spent on a shield first.
bool reset_may_kill(const World& world);

bool landing_ready(const World& world);

// The basic attack from here on the enemy it is worth most against, if any.
bool strike_enemy(const World& world);

// After the goal: the search again from where it left us, for the attack and cast still unspent,
// without moving.
Planned strike_after(const World& world, Pathing& pathing, Safety& safety);

// Fills the terrain-only tables a fight around p reads (Reach's and the search's), each exactly as
// a miss would; p is not a wall.
void warm_tile(const World& world, vec2 p);

}
namespace aph {
namespace {
constexpr int plan_dash_steps = 2;

constexpr float cast_cost = 40;

constexpr int max_foes = 8;

constexpr bool debug_search = true;

// Search's attack_viewers by window row, for the two ranges asked most (ability_range, our attack
// range); here so that warm_tile can fill them.
using ViewerRows = std::array<std::uint16_t, 9>;

std::array<std::array<ViewerRows, 100 * 100>, 2> viewer_rows_cache;

std::array<std::array<std::uint8_t, 100 * 100>, 2> viewer_rows_known;

void fill_viewer_rows(const World& world, vec2 p, int r, ViewerRows& out);

struct Foe {
    const ChampionBelief* belief;
    vec2 pos;
    float health, retaliation, partner, bag;
    bool spawn;
    float taken; // damage it takes per point of our Strength
};

using Healths = std::array<float, max_foes>;

struct Board {
    std::array<Foe, max_foes> foes;
    int n = 0;
    vec2 here;
    float strength = 0, health = 0;
    int range = 1;
    bool splash = false, attack = false;
    int reset = -1, shield = -1;

    Healths healths() const;




};

// Read live: Vendetta's kill readies both slots mid-turn, after the belief was read.
bool slot_ready(const World& world, int slot);

int ready_slot(const World& world, AbilityKind kind);

// Health read from the engine, after our own hits this turn.
bool read_board(const World& world, Board& b, int reach);

// A kill takes the bag; other damage on its spawn heals at its turn end.
float plan_hit_worth(float damage, float health, bool spawn, float bag, float partner);

struct Hit {
    float value = 0;
    int target = -1;
};

// The basic attack from here worth most, never one whose retaliation would kill us.
Hit best_hit(const Board& b, const Healths& h);

bool plan_attack(const Board& b, const Hit& hit);

bool use_slot(int slot);

const Field* goal_field(const World& world, Pathing& pathing, const Intent& intent);

using Grid = std::uint64_t;

constexpr int grid_r = 3, grid_n = 7;

constexpr Grid grid_all = (Grid{1} << 49) - 1;

constexpr Grid grid_column(int x);

constexpr Grid grid_column(int x)
{
    Grid g = 0;
    for (int y = 0; y < grid_n; ++y) g |= Grid{1} << (y * grid_n + x);
    return g;
}

constexpr Grid not_west = grid_all & ~grid_column(0), not_east = grid_all & ~grid_column(grid_n - 1);

constexpr Grid gbit(int c);

constexpr Grid gbit(int c)
{ return Grid{1} << c; }

Grid grid_dilate(Grid g);

template <class F> [[gnu::always_inline]] inline void each_bit(Grid g, F&& f);

constexpr int max_units = 14;

constexpr int max_groups = 16;

constexpr int max_members = 48;

constexpr int max_centres = 81;

constexpr int max_unseen = 24;

constexpr int max_depth = 6;

constexpr int max_mates = 6;

// Reach queries per search; past it the rest keep their Strike price.
constexpr int max_exact_queries = 10;

// Nodes a search grows. At 100M on the wide set 24 binds on 0.46% of searches, where nodes cost
// ~1.1k each; past it the leaves offered so far stand.
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
enum Seg : std::uint8_t { at_start, seg_walked, dashed, walked_dashed, dashed_walked };

using UnitHealths = std::array<float, max_units>;

struct SearchUnit {
    const ChampionBelief* belief = nullptr; // foes
    vec2 pos;
    float health = 0, shield = 0; // a foe's health with its shield, and the shield
    float retaliation = 0, partner = 1e9f, bag = 0;
    float taken = 1; // damage it takes per point dealt (a Durability emblem)
    bool foe = true, spawn = false, stunnable = false, recall = false;
    float stun = 0;                             // Marcella's armed attack's stun
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
    int admit(float raw, std::uint16_t r);













    float top() const;




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

// Tiles within 4 of the start: a 9x9 window, index (y + 4) * 9 + x + 4 relative to it.
constexpr int win9_r = 4, win9_n = 9;

// Kept in static storage: zeroing it each turn would cost more than the search. In a union, so
// its members' default initialisers never run: they cost ~50k of the first turn's fuel.
struct SearchTables {
    std::array<SearchUnit, max_units> u;
    std::array<Centre, max_centres> centres;
    std::array<Unseen, max_unseen> unseen;
    std::array<Member, max_members> members;
    std::array<Waker, max_members> wakers;
    std::array<Front, 49> best, kept; // kept: the cast left for the shield; valid by has bits
    std::array<Leaf, 512> leaves;
    std::array<Grid, 49> land_from;
    std::array<float, 49> heal_at; // the best heal cast from each tile
    std::array<std::int8_t, 49> heal_who;
    std::array<std::uint32_t, win9_n * win9_n> touch1;
    std::array<Near, win9_n * win9_n> near;
    std::array<std::uint8_t, max_centres> distinct; // centres, less those equal to an earlier one
    std::array<std::uint32_t, 49> land_foes;
};

union TableStorage {
    SearchTables t;
    TableStorage();
    ~TableStorage();
} table_storage;

SearchTables& search_tables = table_storage.t;

struct Search { struct Spell; struct WakeMemo;
    const World& world;
    Safety& safety;
    Pathing& pathing;
    const Intent& intent;
    const ChampionFacts& f;
    std::array<SearchUnit, max_units>& u = search_tables.u;
    std::array<Front, 49>& best = search_tables.best;

    vec2 here;
    float strength = 0, health = 0, step = 0, dash_cost = 0, shield_amount = 0;
    int range = 1, land_radius = 0;
    bool melee = true, splash = false, vendetta = false, lands = false, walks = false, moves = true;
    bool can_walk = false, can_attack = false, can_cast = false, walked_first = false;
    int reset = -1, dash = -1, shield = -1, heal = -1;
    bool reset_ready = false, dash_ready = false, arms = false;
    struct Spell {
        int slot = -1;
        bool unit = false, ground = false, excl = false;
    };
    std::array<Spell, 2> spells;

    int n = 0, foes = 0;
    UnitHealths h{};
    std::array<int, max_groups> groups;
    int n_groups = 0, n_members = 0, n_centres = 0, n_distinct = 0, n_unseen = 0;
    // By local group: its wakers in tables.wakers, found on first need.
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
    Grid opened(const Node& s) const;




    // free_n, landings(), land_here and plain_here with the tiles `o` open as well.
    Grid free_n_at(Grid o) const;
    Grid landings_at(int c, Grid o);




    Grid land_here_at(Grid o);
    Grid plain_here_at(Grid o);
    Grid guarded = 0; // the step guard's tiles: never an end
    Grid land_known = 0;
    // Landings never taken: those striking camps but no foe, and those waking a sleeping striker
    // (as the old menu's landing_wakes; a woken pack keeps hitting while the fight stays).
    Grid land_bad = 0;

    union {
        std::array<Act, max_depth> stack;
    };
    Grid has = 0;
    int nodes = 0, offers = 0, n_leaves = 0;

    Grid kept_has = 0;

    Search(const World& w, Safety& s, Pathing& p, const Intent& i);

    int cell(vec2 p) const;
    vec2 tile(int c) const;
    bool in_grid(vec2 p) const;

    // A dash from cell c: at most 2 king steps not through walls or live camps, onto a free tile.
    Grid landings(int c);







    // Tiles within r of the visible unit at p that see it. attack_viewers leaves out bushes beyond
    // a step, but the start tile is exact: the unit is visible from there now.
    Grid viewers(vec2 p, int r) const;











    // Every grid tile within r of p.
    Grid square(vec2 p, int r) const;








    // A unit our own ward sees stays visible to us wherever we move (wards.vision). Our ward is
    // found on first need; its mask is cast again only when it moves.
    mutable bool ward_known = false, warded = false;
    bool ward_sees(vec2 p) const;

















    // attack_viewers by window row (bit x + 4), kept for the game for the two ranges asked most:
    // it depends on terrain alone.
    using Rows = ViewerRows;
    const Rows& viewer_rows(vec2 p, int r) const;











    // The camp groups a landing on cell c touches, by cell.
    Grid land_touch_known = 0;
    std::uint32_t land_touch(int c);





    std::uint32_t touch_near(vec2 p, int r) const;





    // Calls f(i) for each 9x9 window index within 1 of p.
    template <class F> [[gnu::always_inline]] void around(vec2 p, F&& f) const {
        const int x = p.x - here.x + win9_r, y = p.y - here.y + win9_r;
        const int x0 = std::max(0, x - 1), x1 = std::min(win9_n - 1, x + 1), y1 = std::min(win9_n - 1, y + 1);
        for (int yy = std::max(0, y - 1); yy <= y1; ++yy)
            for (int xx = x0; xx <= x1; ++xx) f(yy * win9_n + xx);
    }
    // touch_near(p, 1), from the members scattered once over the 9x9 window.
    bool touch1_known = false;
    std::uint32_t touch1(vec2 p);














    // Landings that hit, grouped alike for the last hits set and foes alive asked.
    Grid groups_hits = 0;
    std::uint32_t groups_alive = 0;
    int n_land_groups = 0;
    std::array<Grid, 49> land_groups;
    // Landing cells by class, alike in (foes in reach, groups touched), found on first need: a
    // query merges the classes whose foes alive agree.
    Grid class_known = 0;
    int n_land_classes = 0;
    std::array<std::int8_t, 49> cell_class;
    std::array<std::uint32_t, 49> class_foes, class_touch;
    std::uint32_t class_foes_all = 0;
    void group_landings(Grid hits, std::uint32_t alive);































    // The foes a landing on cell c hits, alive or not.
    Grid land_foes_known = 0;
    std::uint32_t land_foes(int c);









    bool read();
    void read_geometry();
    void read_members();
    void read_camps();
    void read_spells();
    void add_unseen(int slot);
    void find_centres(int slot);
    void read_mates();
    // The heal worth most cast from cell c or, before moving, from the start; its mate in `who`.
    float heal_from(int c, std::int8_t& who, bool& first) const;





    // What the shield would absorb at p over its turns.
    float shield_at(vec2 p) const;



    // Health left to t's partner, whose death is t's.
    float partner(int t) const;



    // A kill takes the partner with it.
    void lose(int t, float d, Node& s);





    // Whether t's partner, hit later by the same blow (not yet counted), dies to it while t would
    // not: t's hit is then worth nothing beyond the partner's kill.
    bool moot(int t, float d, bool partner_hit, float partner_d) const;




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
    bool wake_at(std::uint32_t touched, int c, float& cost, float& on_us);









    // wake() at the start tile, by touched set: the ground centres ask it at every node.
    std::array<WakeMemo, 8> here_wakes;
    int n_here_wakes = 0;
    bool wake_here(std::uint32_t touched, float& cost, float& on_us);









    float leaf_value(const Node& s) const;

    Node root() const;
    bool legal_at(Node& s, Grid legal);
    // Whether a strike can still follow: a move with none after it is never offered.
    bool strikes_left(const Node& s) const;







    // Foes the start tile's attack hits without a kill, off their spawn and with no partner to
    // cap the damage: on them hit_worth sums the same in either order. Set as the root expands,
    // its attacks first.
    std::uint16_t soft_first = 0;
    // An attack after moves and casts alone, the last move followed by a strike, is offered
    // earlier from the start tile, at the same value and with more end tiles. A spell's cancelled
    // recall needs the foe to outlive it, so a recalling foe keeps its order.
    bool hoisted(const Node& s, int t) const;







    // A walk then an attack the start tile allows leaves the state the attack then the walk does,
    // which is grown first and keeps every walk tile: only the leaf itself is its own.
    bool walked_attack(const Node& s) const;




    void grow(const Node& s);
    void settle(const Node& s);
    template <class Mid> void offer(Grid ends, float v, const Node& s, std::int16_t& leaf, Mid&& mid);
    // For the last kills and stuns asked: siblings mostly share them.
    std::uint32_t removed_key = ~0u;
    std::uint16_t removed_last = 0;
    std::uint16_t removed(const Node& s);









    Seq concrete(int c, bool keep, int entry, bool shields) const;




















    float hor_health(int leaf, int k) const;

};

// The map's bounds and walls by grid cell around each centre tile: terrain alone, kept for the game.
struct TerrainGrid {
    Grid inside = 0, walls = 0; // inside is never 0 once read
};

// `box`: the grid's square around `centre`, drawn.
const TerrainGrid& terrain_grid(const StaticMap& map, vec2 centre, const bitboard& box, bitboard& scratch);

}
}
namespace aph {
void warm_tile(const World& world, vec2 p);

bool strike_possible(const World& world);

[[gnu::flatten]] Planned plan_strikes(const World& world, Pathing& pathing, Safety& safety, const Intent& intent);

Planned strike_after(const World& world, Pathing& pathing, Safety& safety);

[[gnu::flatten]] bool strike_enemy(const World& world);

bool landing_ready(const World& world);

bool reset_may_kill(const World& world);

}
