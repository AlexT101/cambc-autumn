#include "plan.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdio>
#include <string_view>
#include "abilities.h"
#include "params.h"
#include "pathing.h"
#include "safety.h"
#include "world.h"

namespace aph {

namespace {

constexpr int dash_steps = 2;
constexpr float cast_cost = 40; // a slot's next 8 rounds, as cast_at_enemies prices them
constexpr int max_foes = 8;
constexpr bool debug_search = true; // SRCH lines and the search's checks, all inside debug_block

// ---- The basic attack from where we stand, for strike_after and strike_enemy ----

struct Foe {
    const ChampionBelief* belief;
    vec2 pos;
    float health, retaliation, partner, bag;
    bool spawn;
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

    Healths healths() const {
        Healths h{};
        for (int i = 0; i < n; ++i) h[i] = foes[i].health;
        return h;
    }
};

int ready_slot(const World& world, AbilityKind kind) {
    const auto& self = world.me();
    const int slot = self.facts().slot_of(kind);
    // The belief is exact for ourselves at turn start.
    return slot >= 0 && self.ability_ready(slot, world.round) ? slot : -1;
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
        float health = 0;
        try {
            const auto c = e.live();
            if (!c.is_alive()) continue;
            health = c.health();
        } catch (const cambc::error&) {
            continue;
        }
        // A shield absorbs before health: to kill, the hits must go through both.
        b.foes[b.n++] = {&e, e.pos, health + e.shield, e.retaliation(), linked_partner_health(world, e),
                         params::gem_value * static_cast<float>(pair_gems(world, e)), test(enemy_spawn, e.pos)};
    }
    if (b.n == 0) return false;
    const bool cast = my_can_cast();
    b.attack = my_can_attack();
    b.health = my_health();
    b.strength = my_strength() * damage_scale(f.passive, b.health, my_max_health());
    b.reset = cast ? ready_slot(world, AbilityKind::attack_reset) : -1;
    b.shield = cast ? ready_slot(world, AbilityKind::shield) : -1;
    return true;
}

// A kill takes the bag; other damage on its spawn heals at its turn end.
float hit_worth(float damage, float health, bool spawn, float bag, float partner) {
    if (health <= 0) return 0;
    if (damage >= health - 0.01f) return health + params::life_value + bag;
    if (spawn) return 0;
    return useful_damage(damage, health, partner);
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
        float value = hit_worth(b.strength, h[i], f.spawn, f.bag, f.partner), retaliation = f.retaliation;
        if (b.splash)
            for (int j = 0; j < b.n; ++j) {
                const auto& o = b.foes[j];
                if (j != i && h[j] > 0 && dist(o.pos, f.pos) <= 1)
                    value += hit_worth(b.strength, h[j], o.spawn, o.bag, o.partner), retaliation += o.retaliation;
            }
        if (retaliation >= b.health) continue;
        value -= retaliation;
        if (value <= 0) continue;
        if (best.target < 0 || value > best.value || (value == best.value && h[i] < best_health)) best = {value, i}, best_health = h[i];
    }
    return best;
}

void apply(const Board& b, const Hit& hit, Healths& h) {
    if (hit.target < 0) return;
    const vec2 at = b.foes[hit.target].pos;
    for (int j = 0; j < b.n; ++j)
        if (j == hit.target || (b.splash && h[j] > 0 && dist(b.foes[j].pos, at) <= 1)) h[j] -= b.strength;
    // Cassi and Issac die together.
    for (int j = 0; j < b.n; ++j)
        if (h[j] <= 0.01f && b.foes[j].belief->facts().passive == Passive::linked_pair)
            for (int k = 0; k < b.n; ++k)
                if (b.foes[k].belief->facts().passive == Passive::linked_pair) h[k] = 0;
}

bool attack(const Board& b, const Hit& hit) {
    if (hit.target < 0) return false;
    try {
        cambc::self().attack(b.foes[hit.target].belief->live());
        return true;
    } catch (const cambc::error&) {
        return false;
    }
}

bool use_slot(int slot) {
    try {
        return cambc::self().abilities()[slot].use();
    } catch (const cambc::error&) {
        return false;
    }
}

// The shield cast left for the turn's end, over its duration, capped by what could hit us at p.
float shield_worth(const World& world, Safety& safety, int slot, vec2 p) {
    if (slot < 0) return 0;
    float amount = 0;
    try {
        amount = cambc::self().abilities()[slot].shield_amount();
    } catch (const cambc::error&) {
        return 0;
    }
    return std::min(amount, static_cast<float>(world.me().facts().abilities[slot].duration) * safety.damage_bound(p));
}

// Whether the search valued an enemy cast from its start tile this turn: strike_after casts there
// if the goal did not walk.
struct Valued {
    int round = -1;
    vec2 at{-1, -1};
    bool any = false;
} valued;

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
// allow in a turn, with one cast. Moves end within 3 of the start: a 7x7 grid, bit
// (y + 3) * 7 + x + 3 relative to it.

using Grid = std::uint64_t;
constexpr int grid_r = 3, grid_n = 7;
constexpr Grid grid_all = (Grid{1} << 49) - 1;
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
constexpr int max_centres = 81;
constexpr int max_unseen = 24;
constexpr int max_depth = 6;
// Reach queries per search; past it the rest keep their Strike price.
constexpr int max_exact_queries = 10;

enum class Op : std::uint8_t { walk, attack, reset, dash, spell };
struct Act {
    Op op;
    std::int8_t unit = -1; // attack, unit spell
    std::int8_t slot = -1; // spell
    vec2 tile{-1, -1};     // walk, dash, ground spell
    bool operator==(const Act&) const = default;
};
struct Seq {
    std::array<Act, max_depth> a;
    int n = 0;
};

// Where a sequence's actions are taken: the start, after the walk, after the dash, after a walk
// then the dash, after the dash then a walk.
enum Seg : std::uint8_t { at_start, walked, dashed, walked_dashed, dashed_walked };

using UnitHealths = std::array<float, max_units>;

struct Unit {
    const ChampionBelief* belief = nullptr; // foes
    vec2 pos;
    float health = 0; // a foe's with its shield
    float retaliation = 0, partner = 1e9f, bag = 0;
    bool foe = true, spawn = false, stunnable = false, recall = false;
    float stun = 0;                             // Marcella's armed attack's stun
    float land = 0, land_stun = 0;              // our landing's
    std::array<float, 2> spell{}, spell_stun{}; // per slot
    std::array<bool, 2> suicidal{};             // per slot: its retaliation would kill us
    int group = -1, member = -1, local = -1;    // camps
    std::int8_t hor = -1;                       // its index among enemy Hearts of Ruin
    std::int8_t link = -1;                      // Cassi's or Issac's partner among the foes
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
    bool moved : 1 = false; // exhaustive enumerator: walked
    // A walk or dash not yet followed by a strike from where it ended: a move with none is the
    // goal's walk or retreat's dash, which price what the leaf score cannot (later turns).
    bool owed : 1 = false;
    std::int8_t depth = 0;
    std::uint16_t stunned = 0;     // units stunned this turn
    float value = 0, pending = 0; // pending: a cast's price a Vendetta kill would refund
    std::uint32_t touched = 0;     // local camp groups hit
    Grid req_w = grid_all, req_d = grid_all, req_e = grid_all; // the tiles still allowed for each move's end
    Grid lset = 0; // a landing that hits: its tiles, alike in what they hit
    vec2 pos;          // exhaustive enumerator: where we stand
};

// A sequence as the search grows it, its walk and dash tiles left open.
struct Leaf {
    Seq seq;
    std::array<float, 2> hor; // the enemy Hearts of Ruin's health after it
};

struct Choice {
    float raw; // hits less prices and wakes, plus the shield and an unused walk
    int leaf;
    vec2 w, d; // its walk and dash tiles
};

struct Unseen {
    vec2 pos;
    float weight, worth; // worth < 0: hitting it is suicidal
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
struct Tables {
    std::array<Unit, max_units> u;
    std::array<Centre, max_centres> centres;
    std::array<Unseen, max_unseen> unseen;
    std::array<Member, max_members> members;
    std::array<Waker, max_members> wakers;
    std::array<Choice, 49> best;
    std::array<Leaf, 512> leaves;
    std::array<Grid, 49> land_from;
    std::array<float, 49> exh, menu;
    std::array<std::uint32_t, win9_n * win9_n> touch1;
    std::array<Near, win9_n * win9_n> near;
    std::array<std::uint8_t, max_centres> distinct; // centres, less those equal to an earlier one
    std::array<std::uint32_t, 49> land_foes;
};
union TableStorage {
    Tables t;
    TableStorage() {}
    ~TableStorage() {}
} table_storage;
Tables& tables = table_storage.t;

struct Search {
    const World& world;
    Safety& safety;
    Pathing& pathing;
    const Intent& intent;
    const ChampionFacts& f;
    std::array<Unit, max_units>& u = tables.u;
    std::array<Choice, 49>& best = tables.best;

    vec2 here;
    float strength = 0, health = 0, step = 0, shield_value = 0, dash_cost = 0;
    int range = 1, land_radius = 0;
    bool melee = true, splash = false, vendetta = false, lands = false, walks = false, moves = true;
    bool can_walk = false, can_attack = false, can_cast = false;
    int reset = -1, dash = -1, shield = -1;
    bool reset_ready = false, dash_ready = false, arms = false;
    struct Spell {
        int slot = -1;
        bool unit = false, ground = false, excl = false;
    };
    std::array<Spell, 2> spells;

    int n = 0, foes = 0;
    UnitHealths h{};
    std::array<int, max_groups> groups{};
    int n_groups = 0, n_members = 0, n_centres = 0, n_distinct = 0, n_unseen = 0;
    // By local group: its wakers in tables.wakers, found on first need.
    std::array<std::uint8_t, max_groups> waker_begin{}, waker_end{};
    std::uint32_t wakers_known = 0;
    int n_wakers = 0, self_slot = 0;
    void find_wakers(int k);
    std::array<const ChampionBelief*, 2> hors{};
    int n_hors = 0;

    Grid free_ = 0, pass_ = 0, free_n = 0, land_here = 0, land_hits = 0, plain_here = 0, dom_dw = 0;
    Grid land_known = 0;
    // Landings never taken: those striking camps but no foe, and those waking a sleeping striker
    // (as the old menu's landing_wakes; a woken pack keeps hitting while the fight stays).
    Grid land_bad = 0;

    std::array<Act, max_depth> stack;
    Grid has = 0;
    int nodes = 0, offers = 0, n_leaves = 0;

    Grid exh_has = 0, menu_has = 0;
    std::array<char, max_depth> shape{};

    Search(const World& w, Safety& s, Pathing& p, const Intent& i) : world(w), safety(s), pathing(p), intent(i), f(w.me().facts()) {}

    int cell(vec2 p) const { return (p.y - here.y + grid_r) * grid_n + (p.x - here.x + grid_r); }
    vec2 tile(int c) const { return {here.x + c % grid_n - grid_r, here.y + c / grid_n - grid_r}; }
    bool in_grid(vec2 p) const { return std::abs(p.x - here.x) <= grid_r && std::abs(p.y - here.y) <= grid_r; }
    bool inside_map(vec2 p) const { return p.x >= 0 && p.y >= 0 && p.x < world.map().width && p.y < world.map().height; }

    // A dash from cell c: at most 2 king steps not through walls or live camps, onto a free tile.
    Grid landings(int c) {
        if (land_known & gbit(c)) return tables.land_from[c];
        const Grid s = gbit(c), one = dilate(s);
        tables.land_from[c] = ((one | dilate(one & pass_)) & free_) & ~s & ~land_bad;
        land_known |= gbit(c);
        return tables.land_from[c];
    }

    // A Reach::Window around `centre`, within r of it, read into the grid a row at a time.
    Grid to_grid(Reach::Window w, vec2 centre, int r) const {
        Grid g = 0;
        const int shift = centre.x - here.x - 1; // grid column less window column
        const std::uint64_t span = ((std::uint64_t{1} << (2 * r + 1)) - 1) << (4 - r);
        for (int dy = -r; dy <= r; ++dy) {
            const int gy = centre.y + dy - here.y + grid_r;
            if (gy < 0 || gy >= grid_n) continue;
            std::uint64_t row = w.shr((dy + 4) * 9).lo & span;
            row = (shift >= 0 ? row << shift : row >> -shift) & 0x7F;
            g |= row << (gy * grid_n);
        }
        return g;
    }

    // Tiles within r of the visible unit at p that see it. attack_viewers leaves out bushes beyond
    // a step, but the start tile is exact: the unit is visible from there now.
    Grid viewers(vec2 p, int r) const {
        const auto& rows = viewer_rows(p, r);
        const int shift = p.x - here.x - 1; // grid column less window column
        const std::uint32_t span = ((1u << (2 * r + 1)) - 1) << (4 - r);
        Grid g = 0;
        for (int dy = std::max(-r, here.y - grid_r - p.y), dy1 = std::min(r, here.y + grid_r - p.y); dy <= dy1; ++dy) {
            const std::uint32_t row = rows[dy + 4] & span;
            g |= static_cast<Grid>((shift >= 0 ? row << shift : row >> -shift) & 0x7F) << ((p.y + dy - here.y + grid_r) * grid_n);
        }
        return g | (dist(here, p) <= r ? gbit(cell(here)) : 0);
    }
    // attack_viewers by window row (bit x + 4), kept for the game for the two ranges asked most:
    // it depends on terrain alone.
    using Rows = std::array<std::uint16_t, 9>;
    const Rows& viewer_rows(vec2 p, int r) const {
        static std::array<std::array<Rows, 100 * 100>, 2> rows;
        static std::array<std::array<std::uint8_t, 100 * 100>, 2> known;
        static Rows scratch;
        const auto fill = [&](Rows& out) {
            const auto w = attack_viewers(world, p, r);
            for (int y = 0; y < 9; ++y) out[y] = static_cast<std::uint16_t>(w.shr(9 * y).lo & 0x1FF);
        };
        const int slot = r == ability_range ? 0 : r == range ? 1 : -1;
        const auto i = static_cast<std::size_t>(p.x + p.y * world.map().width);
        if (slot < 0 || i >= known[0].size()) {
            fill(scratch);
            return scratch;
        }
        if (!known[slot][i]) fill(rows[slot][i]), known[slot][i] = 1;
        return rows[slot][i];
    }

    // The camp groups a landing on cell c touches, by cell.
    Grid land_touch_known = 0;
    std::uint32_t land_touch(int c) {
        if (land_radius == 1) return touch1(tile(c));
        static std::array<std::uint32_t, 49> memo; // valid by land_touch_known
        if (!(land_touch_known & gbit(c))) memo[c] = touch_near(tile(c), land_radius), land_touch_known |= gbit(c);
        return memo[c];
    }
    std::uint32_t touch_near(vec2 p, int r) const {
        std::uint32_t mask = 0;
        for (int k = 0; k < n_members; ++k)
            if (dist(p, tables.members[k].pos) <= r) mask |= 1u << tables.members[k].local;
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
        auto& t = tables.touch1;
        if (!touch1_known) {
            touch1_known = true;
            t.fill(0);
            for (int k = 0; k < n_members; ++k) {
                const std::uint32_t bit = 1u << tables.members[k].local;
                around(tables.members[k].pos, [&](int i) { t[i] |= bit; });
            }
        }
        return t[(dy + win9_r) * win9_n + dx + win9_r];
    }
    // Landings that hit, grouped alike for the last hits set and foes alive asked.
    Grid groups_hits = 0;
    std::uint32_t groups_alive = 0;
    int n_land_groups = 0;
    std::array<Grid, 49> land_groups;
    // The foes a landing on cell c hits, alive or not.
    Grid land_foes_known = 0;
    std::uint32_t land_foes(int c) {
        if (!(land_foes_known & gbit(c))) {
            std::uint32_t m = 0;
            for (int t = 0; t < foes; ++t)
                if (dist(tile(c), u[t].pos) <= land_radius) m |= 1u << t;
            tables.land_foes[c] = m, land_foes_known |= gbit(c);
        }
        return tables.land_foes[c];
    }

    bool read();
    void read_geometry();
    void read_members();
    void read_camps();
    void read_spells();
    void add_unseen(int slot);
    void find_centres(int slot);

    // Health left to t's partner, whose death is t's.
    float partner(int t) const {
        const int k = u[t].link;
        return k < 0 ? u[t].partner : std::min(h[k], u[k].belief->health);
    }
    // A kill takes the partner with it.
    void lose(int t, float d) {
        if ((h[t] -= d) > 0.01f) return;
        h[t] = 0;
        if (u[t].link >= 0) h[u[t].link] = 0;
    }
    // Whether t's partner, hit later by the same blow (not yet counted), dies to it while t would
    // not: t's hit is then worth nothing beyond the partner's kill.
    bool moot(int t, float d, bool partner_hit, float partner_d) const {
        const int k = u[t].link;
        return partner_hit && h[k] > 0 && partner_d >= h[k] - 0.01f && d < h[t] - 0.01f;
    }

    bool hit_unit(int t, Node& s);
    bool spell_unit(const Spell& sp, int t, Node& s);
    bool land_at(vec2 L, Node& s);
    float centre_value(const Centre& c, int slot, const Node& s, bool& ok) const;
    void hit_centre(const Centre& c, int slot, Node& s);
    bool wake(std::uint32_t touched, vec2 E, float& cost);
    bool wakers_known_slot = false;
    // wake() by end tile, for the last touched set asked there: leaves differing only in their
    // hits share them.
    struct WakeMemo {
        std::uint32_t touched;
        float cost;
        bool ok;
    };

    Grid wake_known = 0;
    bool wake_at(std::uint32_t touched, int c, float& cost) {
        static std::array<WakeMemo, 49> memo; // valid by wake_known
        auto& m = memo[c];
        if (!(wake_known & gbit(c)) || m.touched != touched) {
            m.touched = touched, m.ok = wake(touched, tile(c), m.cost);
            wake_known |= gbit(c);
        }
        cost = m.cost;
        return m.ok;
    }
    // wake() at the start tile, by touched set: the ground centres ask it at every node.
    std::array<WakeMemo, 8> here_wakes;
    int n_here_wakes = 0;
    bool wake_here(std::uint32_t touched, float& cost) {
        for (int i = 0; i < n_here_wakes; ++i)
            if (here_wakes[i].touched == touched) {
                cost = here_wakes[i].cost;
                return here_wakes[i].ok;
            }
        const bool ok = wake(touched, here, cost);
        if (n_here_wakes < static_cast<int>(here_wakes.size())) here_wakes[n_here_wakes++] = {touched, cost, ok};
        return ok;
    }
    float leaf_value(const Node& s) const;

    Node root() const;
    bool legal_at(Node& s, Grid legal) const;
    // Whether a strike can still follow: a move with none after it is never offered.
    bool strikes_left(const Node& s) const {
        if (s.attack) return true;
        if (!s.cast) return false;
        if (s.reset || (lands && s.dash)) return true;
        for (const auto& sp : spells)
            if (sp.slot >= 0 && sp.unit && !sp.excl) return true;
        return false;
    }

    void grow(const Node& s);
    void settle(const Node& s);
    template <class Mid> void offer(Grid ends, float v, const Node& s, int& leaf, Mid&& mid);
    Seq concrete(int c) const {
        const auto& ch = best[c];
        Seq q = tables.leaves[ch.leaf].seq;
        for (int i = 0; i < q.n; ++i) {
            if (q.a[i].op == Op::walk) q.a[i].tile = ch.w;
            if (q.a[i].op == Op::dash) q.a[i].tile = ch.d;
        }
        return q;
    }
    float hor_health(int c, int k) const { return tables.leaves[best[c].leaf].hor[k]; }

    void exhaust(const Node& s);
    void offer_exh(const Node& s);
    bool menu_shape(int depth) const;
};

void Search::read_geometry() {
    static bitboard box{cambc::uninitialized}, t{cambc::uninitialized};
    clear_board(box);
    draw_square(box, here, grid_r);
    Grid columns = 0, inside = 0;
    for (int x = 0; x < grid_n; ++x)
        if (const int tx = here.x + x - grid_r; tx >= 0 && tx < world.map().width) columns |= grid_column(x);
    for (int y = 0; y < grid_n; ++y)
        if (const int ty = here.y + y - grid_r; ty >= 0 && ty < world.map().height) inside |= columns & (Grid{0x7F} << (y * grid_n));
    std::array<vec2, 49> at;
    const auto read_into = [&](Grid& out) {
        and_into(t, box, t);
        const auto k = positions_into(t, at.data(), 49);
        out = 0;
        for (std::uint32_t i = 0; i < k; ++i) out |= gbit(cell(at[i]));
    };
    Grid blocked = 0, walls = 0;
    if (const bitboard* guard = pathing.guard()) or_into(pathing.blocked(), *guard, t);
    else copy_into(pathing.blocked(), t);
    read_into(blocked);
    // Dash paths are blocked by walls, camps and visible enemies (probe-dash-enemy).
    static bitboard foes_seen{cambc::uninitialized};
    camps_into(t);
    occupancy_into(team::enemy, foes_seen);
    or_into(t, foes_seen, t);
    or_into(t, world.map().walls, t);
    read_into(walls);
    free_ = inside & ~blocked;
    pass_ = inside & ~walls;
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
                tables.members[n_members++] = {groups_map[g].members[i].pos, local,
                                               groups_map[g].members[i].strength > 0 && c.maybe_asleep(i)},
                any = true;
        if (any) groups[n_groups++] = g;
    }
}

void Search::read_camps() {
    // Camps are struck only for what that enables: Vendetta's refresh, Varg's splash.
    if (!vendetta && !splash) return;
    const int reach = vendetta ? grid_r + range : 2;
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
            if (vendetta) useful |= hp <= strength;
            if (!useful || hp <= 0) continue;
            auto& x = u[n];
            x = Unit{};
            x.foe = false;
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
        if (!world.me().ability_ready(s, world.round)) continue;
        if ((a.kind != AbilityKind::damage && a.kind != AbilityKind::stun) || (a.target != Targeting::unit && a.target != Targeting::ground))
            continue;
        float raw = 0;
        try {
            raw = cambc::self().abilities()[s].damage_amount();
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
                lost = raw > 0 ? cambc::self().abilities()[s].damage_amount(e.live()) : 0.0f;
            } catch (const cambc::error&) {
                lost = std::min(raw, e.health);
            }
            // Health lost after the shield, which x.health counts.
            x.spell[s] = e.shield <= 0 ? lost : lost > 0 ? lost + e.shield : std::min(raw, e.shield);
            x.spell_stun[s] = a.stuns && x.stunnable ? stun_worth(world, e, raw > 0) : 0.0f;
            x.suicidal[s] = raw > 0 && x.retaliation >= health;
            if (sp.unit && x.cast_legal == 0) x.cast_legal = viewers(x.pos, ability_range);
        }
        if (sp.ground) {
            add_unseen(s);
            find_centres(s);
        }
    }
}

// Unseen tracked enemies on few tiles, which a ground cast may hit, as cast_at_enemies aims.
void Search::add_unseen(int s) {
    const auto& a = f.abilities[s];
    float raw = 0;
    try {
        raw = cambc::self().abilities()[s].damage_amount();
    } catch (const cambc::error&) {
    }
    const auto& enemy_spawn = world.map().enemy_spawn;
    n_unseen = 0;
    for (const auto& e : world.enemies) {
        if (!e.alive || e.visible || !e.tracked || board_empty(e.possible)) continue;
        const int count = static_cast<int>(board_count(e.possible));
        if (count > 9) continue;
        const float hp = e.health > 0 ? e.health : e.max_health;
        const float stun = a.stuns ? stun_worth(world, e, raw > 0) : 0.0f;
        const bool suicidal = raw > 0 && e.retaliation() >= health;
        for (auto p : positions_within(e.possible, here, a.reach())) {
            if (n_unseen == max_unseen) break;
            const float worth = suicidal ? -1.0f
                                         : hit_worth(std::min(raw, hp), hp, test(enemy_spawn, p),
                                                     params::gem_value * static_cast<float>(pair_gems(world, e)),
                                                     linked_partner_health(world, e)) + stun;
            tables.unseen[n_unseen++] = {p, 1.0f / static_cast<float>(count), worth};
        }
    }
}

// Centres within range whose 3x3 holds a visible foe or an unseen one's tile.
void Search::find_centres(int s) {
    const int r = std::min(f.abilities[s].range(), win9_r);
    // What each tile holds within 1, scattered from the foes and unseen tiles once.
    auto& near = tables.near;
    // Centres lie within 1 of a foe or an unseen tile: only those are cleared.
    for (int i = 0; i < foes; ++i) around(u[i].pos, [&](int j) { near[j] = {}; });
    for (int k = 0; k < n_unseen; ++k) around(tables.unseen[k].pos, [&](int j) { near[j] = {}; });
    for (int i = 0; i < foes; ++i)
        around(u[i].pos, [&](int j) { near[j].foes |= static_cast<std::uint16_t>(1u << i), near[j].banned |= u[i].suicidal[s]; });
    for (int k = 0; k < n_unseen; ++k) {
        const auto& un = tables.unseen[k];
        around(un.pos, [&](int j) {
            if (un.worth < 0) near[j].banned = true;
            else near[j].unseen += un.weight * un.worth;
        });
    }
    // Window columns and rows on the map and within r.
    std::uint32_t cols = 0, rows = 0;
    for (int k = -r; k <= r; ++k) {
        if (const int x = here.x + k; x >= 0 && x < world.map().width) cols |= 1u << (k + win9_r);
        if (const int y = here.y + k; y >= 0 && y < world.map().height) rows |= 1u << (k + win9_r);
    }
    std::array<std::uint8_t, win9_n * win9_n> seen{};
    // A centre equal to an earlier one in all its value reads can never be picked over it: only
    // the first of each is kept in `distinct`, found by a hash of those reads.
    std::array<std::uint8_t, 128> slots{};
    std::array<std::uint64_t, max_centres> keys;
    std::array<std::uint32_t, max_centres> unseen_bits;
    n_centres = n_distinct = 0;
    const auto add = [&](vec2 p) {
        const int x = p.x - here.x + win9_r, y = p.y - here.y + win9_r;
        for (int yy = std::max(0, y - 1), y1 = std::min(win9_n - 1, y + 1); yy <= y1; ++yy) {
            if (!(rows >> yy & 1)) continue;
            for (int xx = std::max(0, x - 1), x1 = std::min(win9_n - 1, x + 1); xx <= x1; ++xx) {
                const int j = yy * win9_n + xx;
                if (!(cols >> xx & 1) || seen[j]) continue;
                seen[j] = 1;
                const int k = n_centres++;
                auto& ce = tables.centres[k];
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
                tables.distinct[n_distinct++] = static_cast<std::uint8_t>(k);
            }
        }
    };
    for (int i = 0; i < foes; ++i)
        if (dist(here, u[i].pos) <= r + 1) add(u[i].pos);
    for (int k = 0; k < n_unseen; ++k) add(tables.unseen[k].pos);
}

bool Search::read() {
    const auto& self = world.me();
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
    strength = record.strength * damage_scale(f.passive, health, record.max_health);
    moves = !intent.anchored;
    walks = intent.walks && can_walk;
    step = intent.step_value;
    dash_cost = dash_steps * step; // the dash's cooldown would otherwise carry us two steps
    reset = f.slot_of(AbilityKind::attack_reset);
    dash = f.slot_of(AbilityKind::dash);
    shield = can_cast ? ready_slot(world, AbilityKind::shield) : -1;
    reset_ready = can_cast && reset >= 0 && self.ability_ready(reset, world.round);
    dash_ready = can_cast && moves && dash >= 0 && self.ability_ready(dash, world.round);
    arms = reset >= 0 && f.abilities[reset].stuns;
    if (dash >= 0 && f.abilities[dash].lands()) lands = true, land_radius = f.abilities[dash].radius;

    // Foes some end tile could hit, by attack or cast. Their stun buffs and recalls are read only
    // when a stun or a cast could use them.
    const int reach = std::max(grid_r + range + (splash ? 1 : 0), ability_range + 1);
    bool stuns = arms, casts = false, touches = (lands && dash_ready) || splash || vendetta;
    for (int s = 0; s < 2; ++s)
        if (can_cast && self.ability_ready(s, world.round) && f.abilities[s].hits_enemies())
            stuns |= f.abilities[s].stuns, casts |= !f.abilities[s].lands(), touches |= f.abilities[s].target == Targeting::ground;
    const auto& enemy_spawn = world.map().enemy_spawn;
    for (const auto& e : world.enemies) {
        if (foes == max_foes) break;
        if (!e.alive || !e.visible || e.stats_round != world.round || dist(here, e.pos) > reach) continue;
        bool stunned = false, recall = false;
        if (stuns || (casts && e.channel == Channel::recall)) {
            const cambc::champion c = e.live();
            try {
                if (!c.is_visible()) continue;
                stunned = stuns && c.buffs().has_stun();
                recall = casts && e.channel == Channel::recall
                         && aph::kept_recall(c, e.fast_recall ? home_recall_time : static_cast<int>(cambc::constants::recall_time));
            } catch (const cambc::error&) {
                continue;
            }
        }
        auto& x = u[foes];
        x = Unit{};
        x.belief = &e;
        x.pos = e.pos;
        x.health = e.health + e.shield;
        x.retaliation = e.retaliation();
        x.partner = linked_partner_health(world, e);
        x.bag = params::gem_value * static_cast<float>(pair_gems(world, e));
        x.spawn = test(enemy_spawn, e.pos);
        x.stunnable = !stunned && e.facts().passive != Passive::stun_immune;
        x.recall = recall;
        x.stun = arms && x.stunnable ? stun_worth(world, e, true) : 0.0f;
        if (e.facts().passive == Passive::missing_health && n_hors < 2) x.hor = static_cast<std::int8_t>(n_hors), hors[n_hors++] = &e;
        x.legal = can_attack && dist(here, e.pos) <= grid_r + range ? viewers(e.pos, range) : 0;
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
    if (lands && (dash_ready || vendetta)) {
        try {
            const auto ability = cambc::self().abilities()[dash];
            const float raw = ability.damage_amount();
            const auto& a = f.abilities[dash];
            for (int i = 0; i < foes; ++i) {
                auto& x = u[i];
                if (dist(here, x.pos) > grid_r + land_radius) continue;
                const float lost = raw > 0 ? ability.damage_amount(x.belief->live()) : 0.0f, sh = x.belief->shield;
                x.land = sh <= 0 ? lost : lost > 0 ? lost + sh : std::min(raw, sh);
                x.land_stun = a.stuns && x.stunnable ? stun_worth(world, *x.belief, raw > 0) : 0.0f;
            }
        } catch (const cambc::error&) {
        }
    }
    read_spells();
    shield_value = shield_worth(world, safety, shield, here);
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
                if (dist(here, tables.members[k].pos) <= grid_r + land_radius) mark(tables.members[k].pos, land_bad);
            land_bad &= ~land_hits;
            for (int k = 0; k < n_members; ++k)
                if (tables.members[k].sleeper && dist(here, tables.members[k].pos) <= grid_r + land_radius)
                    mark(tables.members[k].pos, land_bad);
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
    const bool kill = strength >= h[t] - 0.01f;
    const auto splashed = [&](int k) { return splash && k != t && dist(u[k].pos, x.pos) <= 1; };
    if (x.foe) {
        const bool m = x.link >= 0 && moot(t, strength, splashed(x.link), strength);
        if (!m) value += hit_worth(strength, h[t], x.spawn, x.bag, partner(t));
        if (!m && s.armed && x.stunnable && !(s.stunned >> t & 1)) value += x.stun, s.stunned |= static_cast<std::uint16_t>(1u << t);
        retaliation += x.retaliation;
    } else {
        s.touched |= 1u << x.local;
    }
    lose(t, strength);
    if (splash) {
        for (int j = 0; j < n; ++j) {
            if (j == t || h[j] <= 0 || dist(u[j].pos, x.pos) > 1) continue;
            const auto& o = u[j];
            if (o.foe) {
                const bool m = o.link >= 0 && moot(j, strength, splashed(o.link) && o.link > j, strength);
                if (!m) value += hit_worth(strength, h[j], o.spawn, o.bag, partner(j));
                retaliation += o.retaliation;
            }
            lose(j, strength);
        }
        s.touched |= touch1(x.pos);
    }
    if (retaliation >= health) return false;
    value -= retaliation;
    if (value < 0 || (!x.foe && value <= 0 && !(vendetta && kill))) return false;
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
    if (x.suicidal[sp.slot]) return false;
    float v = hit_worth(d, h[t], x.spawn, x.bag, partner(t));
    if (d > 0 && d < h[t] - 0.01f && !x.spawn && x.recall) v += params::recall_value;
    if (x.spell_stun[sp.slot] > 0 && !(s.stunned >> t & 1)) v += x.spell_stun[sp.slot], s.stunned |= static_cast<std::uint16_t>(1u << t);
    if (d <= 0 && v <= 0) return false;
    lose(t, d);
    s.value += v - cast_cost;
    s.pending = cast_cost;
    s.cast = false;
    s.owed = false;
    if (sp.excl) s.excl = true, s.walk = false;
    return true;
}

float Search::centre_value(const Centre& c, int slot, const Node& s, bool& ok) const {
    ok = !c.banned;
    float v = c.unseen;
    for (std::uint32_t m = c.foes; m && ok; m &= m - 1) {
        const int t = std::countr_zero(m);
        const auto& x = u[t];
        if (h[t] <= 0) continue;
        const float d = x.spell[slot];
        if (x.link >= 0 && moot(t, d, x.link > t && (c.foes >> x.link & 1), u[x.link].spell[slot])) continue;
        v += hit_worth(d, h[t], x.spawn, x.bag, partner(t));
        if (d > 0 && d < h[t] - 0.01f && !x.spawn && x.recall) v += params::recall_value;
        if (!(s.stunned >> t & 1)) v += x.spell_stun[slot];
    }
    return v;
}

void Search::hit_centre(const Centre& c, int slot, Node& s) {
    bool ok;
    s.value += centre_value(c, slot, s, ok) - cast_cost;
    for (std::uint32_t m = c.foes; m; m &= m - 1) {
        const int t = std::countr_zero(m);
        if (h[t] <= 0) continue;
        if (u[t].spell_stun[slot] > 0) s.stunned |= static_cast<std::uint16_t>(1u << t);
        lose(t, u[t].spell[slot]);
    }
    s.touched |= c.touched;
    s.pending = cast_cost;
    s.cast = false;
    if (spells[slot].excl) s.excl = true, s.walk = false;
}

bool Search::land_at(vec2 L, Node& s) {
    float value = 0, retaliation = 0;
    bool struck = false;
    const int c = cell(L);
    for (std::uint32_t near = land_foes(c); near; near &= near - 1) {
        const int t = std::countr_zero(near);
        const auto& x = u[t];
        if (h[t] <= 0) continue;
        struck |= x.land > 0 || x.land_stun > 0;
        const bool m = x.link >= 0 && moot(t, x.land, x.link > t && dist(L, u[x.link].pos) <= land_radius, u[x.link].land);
        if (!m) value += hit_worth(x.land, h[t], x.spawn, x.bag, partner(t));
        if (!m && x.land_stun > 0 && !(s.stunned >> t & 1)) value += x.land_stun, s.stunned |= static_cast<std::uint16_t>(1u << t);
        retaliation += x.land > 0 ? x.retaliation : 0.0f;
        lose(t, x.land);
    }
    if (retaliation >= health) return false;
    s.touched |= land_touch(c);
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
        tables.wakers[n_wakers++] = w;
    }
    waker_end[k] = static_cast<std::uint8_t>(n_wakers);
}

// What the touched groups' sleeping strikers would hit: each the nearest champion in its reach,
// ties to the first to act next round, among us at E, the allies we see and the enemies held in
// place (acted this round, or channelling). A hit on an enemy earns nothing for now. False for the
// bans: a sleeping Monolith; a woken hit on an ally recalling, tributing or holding a capture; a
// woken hit that could kill us or an ally.
bool Search::wake(std::uint32_t touched, vec2 E, float& cost) {
    cost = 0;
    std::array<float, 8> ally_hit{};
    float on_us = 0;
    for (std::uint32_t m = touched; m; m &= m - 1) {
        const int k = std::countr_zero(m);
        if (!(wakers_known >> k & 1)) find_wakers(k);
        for (int i = waker_begin[k]; i < waker_end[k]; ++i) {
            const auto& w = tables.wakers[i];
            if (w.monolith) return false;
            const int d = dist(E, w.pos);
            if (d <= w.reach && (d < w.other_d || (d == w.other_d && self_slot < w.other_slot))) {
                // Awake, it hits us every camp phase we are in its reach: the next one, and the
                // one after unless our next step can leave its reach.
                const float hits = d < w.reach ? 2.0f : 1.0f;
                cost += w.strength * hits;
                on_us += w.strength * hits;
            } else if (w.other_d <= w.reach && w.ally >= 0) {
                const auto& o = world.allies[static_cast<std::size_t>(w.ally)];
                if (o.channel == Channel::recall || o.channel == Channel::tribute) return false;
                if (const int at = world.map().group_at(o.pos); at >= 0 && world.camps[at].state == CampState::cleared) return false;
                if ((ally_hit[static_cast<std::size_t>(w.ally)] += w.strength) >= o.health) return false;
                cost += w.strength * (o.acted ? 1.0f : 0.5f);
            }
        }
    }
    return on_us < health;
}

float Search::leaf_value(const Node& s) const {
    return s.value + (s.cast && shield >= 0 ? shield_value : 0.0f) + (s.walk && !s.excl && walks ? step : 0.0f);
}

Node Search::root() const {
    Node s;
    s.walk = can_walk && moves;
    s.attack = can_attack;
    s.cast = can_cast;
    s.reset = reset_ready;
    s.dash = dash_ready;
    s.pos = here;
    return s;
}

// Offers the leaf at each end tile in `ends`; mid(c, w, d) names the walk and dash tiles for one
// it improves.
template <class Mid> void Search::offer(Grid ends, float v, const Node& s, int& leaf, Mid&& mid) {
    each_bit(ends, [&](int c) {
        ++offers;
        const vec2 E = tile(c);
        float x = v;
        if (s.touched) {
            float cost;
            if (!wake_at(s.touched, c, cost)) return;
            x -= cost;
        }
        if ((has & gbit(c)) && x <= best[c].raw) return;
        if (leaf < 0) {
            if (n_leaves == static_cast<int>(tables.leaves.size())) return;
            leaf = n_leaves++;
            auto& l = tables.leaves[leaf];
            l.seq.n = s.depth;
            for (int i = 0; i < s.depth; ++i) l.seq.a[i] = stack[i];
            for (int t = 0; t < foes; ++t)
                if (u[t].hor >= 0) l.hor[u[t].hor] = h[t];
        }
        vec2 w{-1, -1}, d{-1, -1};
        mid(c, w, d);
        has |= gbit(c);
        best[c] = {x, leaf, w, d};
    });
}

// Each end tile a leaf's moves can reach, offered once.
void Search::settle(const Node& s) {
    if (s.owed) return;
    const float v = leaf_value(s);
    int leaf = -1;
    switch (s.seg) {
    case at_start: offer(gbit(cell(here)), v, s, leaf, [](int, vec2&, vec2&) {}); break;
    case walked: offer(free_n & s.req_w, v, s, leaf, [&](int c, vec2& w, vec2&) { w = tile(c); }); break;
    case dashed: {
        const Grid ends = (s.lset ? s.lset : plain_here) & s.req_d;
        offer(ends, v, s, leaf, [&](int c, vec2&, vec2& d) { d = tile(c); });
        break;
    }
    case walked_dashed: {
        const Grid allowed = (s.lset ? s.lset : ~land_hits) & s.req_d, mids = free_n & s.req_w;
        Grid ends = 0;
        each_bit(mids, [&](int m) { ends |= landings(m); });
        // Each end's walk tile: the first mid it lands from, found for all ends on first need.
        std::array<std::int8_t, 49> first;
        bool firsts = false;
        offer(ends & allowed, v, s, leaf, [&](int c, vec2& w, vec2& d) {
            if (!firsts) {
                firsts = true;
                Grid left = ends & allowed;
                each_bit(mids, [&](int m) {
                    const Grid now = landings(m) & left;
                    left &= ~now;
                    each_bit(now, [&](int e) { first[e] = static_cast<std::int8_t>(m); });
                });
            }
            w = tile(first[c]);
            d = tile(c);
        });
        break;
    }
    case dashed_walked: {
        const Grid from = (s.lset ? s.lset : plain_here) & s.req_d;
        Grid ends = dilate(from) & free_ & s.req_e;
        // A landing itself is an end only when walked to from another.
        each_bit(ends & from, [&](int c) {
            if (!(dilate(gbit(c)) & from & ~gbit(c))) ends &= ~gbit(c);
        });
        offer(ends, v, s, leaf, [&](int c, vec2& w, vec2& d) {
            w = tile(c);
            d = tile(std::countr_zero(dilate(gbit(c)) & from & ~gbit(c)));
        });
        break;
    }
    }
}

// Narrows the current move's end tiles to `legal`; false if none is left.
bool Search::legal_at(Node& s, Grid legal) const {
    switch (s.seg) {
    case at_start: return legal & gbit(cell(here));
    case walked: return (free_n & (s.req_w &= legal)) != 0;
    case dashed: return ((s.lset ? s.lset : plain_here) & (s.req_d &= legal)) != 0;
    case walked_dashed: return ((s.lset ? s.lset : ~land_hits) & (s.req_d &= legal)) != 0;
    case dashed_walked: {
        const Grid dom = s.lset ? dilate(s.lset & s.req_d) & free_ : dom_dw;
        return (dom & (s.req_e &= legal)) != 0;
    }
    }
    return false;
}

void Search::grow(const Node& s) {
    ++nodes;
    settle(s);
    if (s.depth == max_depth) return;
    const UnitHealths saved = h;
    const auto push = [&](Node& c, Act a) {
        stack[s.depth] = a;
        c.depth = static_cast<std::int8_t>(s.depth + 1);
        grow(c);
        h = saved;
    };
    // Legality is settled before a child is copied.
    const Grid here_bit = gbit(cell(here));
    const auto open = [&](Grid legal) {
        switch (s.seg) {
        case at_start: return (legal & here_bit) != 0;
        case walked: return (free_n & s.req_w & legal) != 0;
        case dashed: return ((s.lset ? s.lset : plain_here) & s.req_d & legal) != 0;
        case walked_dashed: return ((s.lset ? s.lset : ~land_hits) & s.req_d & legal) != 0;
        case dashed_walked: return true;
        }
        return false;
    };
    if (s.attack)
        for (int t = 0; t < n; ++t) {
            if (h[t] <= 0 || !open(u[t].legal)) continue;
            Node c = s;
            if (legal_at(c, u[t].legal) && hit_unit(t, c)) push(c, {Op::attack, static_cast<std::int8_t>(t)});
            else h = saved;
        }
    if (s.cast && s.reset && !s.attack) {
        Node c = s;
        c.attack = true, c.cast = false, c.reset = false, c.armed = arms, c.pending = 0;
        push(c, {Op::reset});
    }
    if (s.walk && !s.excl && (melee || s.attack) && (s.seg == at_start || s.seg == dashed)) {
        Node c = s;
        c.walk = false, c.owed = true;
        if (!melee) c.attack = false;
        c.seg = s.seg == at_start ? walked : dashed_walked;
        const Grid dom = c.seg == walked                ? free_n
                         : s.lset                        ? dilate(s.lset & s.req_d) & free_
                                                         : dom_dw & dilate(plain_here & s.req_d);
        if (dom && strikes_left(c)) push(c, {Op::walk});
    }
    if (s.cast && s.dash && (s.seg == at_start || s.seg == walked)) {
        const bool first = s.seg == at_start;
        // Landings from the walk tiles the actions so far still allow.
        Grid reach = land_here;
        if (!first) {
            reach = 0;
            each_bit(free_n & s.req_w, [&](int m) { reach |= landings(m); });
        }
        Node c = s;
        c.cast = false, c.dash = false, c.value -= dash_cost, c.pending = dash_cost, c.req_d = reach, c.owed = true;
        c.seg = first ? dashed : walked_dashed;
        if ((reach & ~land_hits) != 0 && strikes_left(c)) push(c, {Op::dash});
        // Landings wake no sleeper, so those hitting the same foes and camp groups are alike.
        if (const Grid hits = lands ? reach & land_hits : 0) {
            std::uint32_t alive = 0;
            for (int t = 0; t < foes; ++t)
                if (h[t] > 0) alive |= 1u << t;
            // Nodes before any kill share their landings' groups.
            if (hits != groups_hits || alive != groups_alive) {
                groups_hits = hits, groups_alive = alive, n_land_groups = 0;
                std::array<std::uint32_t, 49> hit, touch;
                each_bit(hits, [&](int k) {
                    const std::uint32_t m = land_foes(k) & alive, t = land_touch(k);
                    int i = 0;
                    while (i < n_land_groups && !(hit[i] == m && touch[i] == t)) ++i;
                    if (i == n_land_groups) hit[i] = m, touch[i] = t, land_groups[i] = 0, ++n_land_groups;
                    land_groups[i] |= gbit(k);
                });
            }
            const int kinds = n_land_groups;
            std::array<Grid, 49> alike;
            std::copy_n(land_groups.begin(), kinds, alike.begin());
            for (int i = 0; i < kinds; ++i) {
                Node d = c;
                if (land_at(tile(std::countr_zero(alike[i])), d)) {
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
                    const int k = tables.distinct[q];
                    const auto& ce = tables.centres[k];
                    bool ok;
                    float v = centre_value(ce, sp.slot, s, ok);
                    if (!ok) continue;
                    float cost = 0;
                    if ((ce.touched | s.touched) && !wake_here(ce.touched | s.touched, cost)) continue;
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
                    hit_centre(tables.centres[which[i]], sp.slot, c);
                    push(c, {Op::spell, -1, static_cast<std::int8_t>(sp.slot), tables.centres[which[i]].tile});
                }
            }
        }
}

// ---- Debug: every sequence on concrete tiles, without the search's grouping ----

bool Search::menu_shape(int depth) const {
    // The old planner's menu: stay A, A R A, A + cast; walk W A, melee A W R A, ranged W R A;
    // dash D A, melee A D, D W A; a landing before or after an attack.
    static constexpr std::string_view shapes[] = {"", "A", "ARA", "AS", "S", "WA", "AWRA", "WRA", "DA", "AD", "DWA", "D"};
    const std::string_view v{shape.data(), static_cast<std::size_t>(depth)};
    for (const auto sh : shapes) {
        if (sh != v) continue;
        if ((v == "WA" || v == "AWRA" || v == "AD" || v == "DWA") && !melee) return false;
        if (v == "WRA" && melee) return false;
        if (v == "D" && !lands) return false;
        return true;
    }
    return false;
}

void Search::offer_exh(const Node& s) {
    if (s.owed) return;
    float v = leaf_value(s);
    if (s.touched) {
        float cost;
        if (!wake(s.touched, s.pos, cost)) return;
        v -= cost;
    }
    const int c = cell(s.pos);
    if (!(exh_has & gbit(c)) || v > tables.exh[c]) tables.exh[c] = v, exh_has |= gbit(c);
    if (menu_shape(s.depth) && (!(menu_has & gbit(c)) || v > tables.menu[c])) tables.menu[c] = v, menu_has |= gbit(c);
}

void Search::exhaust(const Node& s) {
    offer_exh(s);
    if (s.depth == max_depth) return;
    const UnitHealths saved = h;
    const int at = cell(s.pos);
    const auto push = [&](Node& c, char op) {
        shape[s.depth] = op;
        c.depth = static_cast<std::int8_t>(s.depth + 1);
        exhaust(c);
        h = saved;
    };
    if (s.attack)
        for (int t = 0; t < n; ++t) {
            if (h[t] <= 0 || !(u[t].legal & gbit(at))) continue;
            Node c = s;
            if (hit_unit(t, c)) push(c, 'A');
            else h = saved;
        }
    if (s.cast && s.reset && !s.attack) {
        Node c = s;
        c.attack = true, c.cast = false, c.reset = false, c.armed = arms, c.pending = 0;
        push(c, 'R');
    }
    if (s.walk && !s.excl && (melee || s.attack))
        each_bit(dilate(gbit(at)) & free_ & ~gbit(at), [&](int e) {
            Node c = s;
            c.walk = false, c.moved = true, c.owed = true, c.pos = tile(e);
            if (!melee) c.attack = false;
            push(c, 'W');
        });
    if (s.cast && s.dash && dist(s.pos, here) <= 1)
        each_bit(landings(at), [&](int l) {
            Node c = s;
            c.cast = false, c.dash = false, c.value -= dash_cost, c.pending = dash_cost, c.owed = true, c.pos = tile(l);
            if (lands && (land_hits & gbit(l)) && !land_at(tile(l), c)) {
                h = saved;
                return;
            }
            push(c, 'D');
        });
    if (s.cast)
        for (const auto& sp : spells) {
            if (sp.slot < 0 || (sp.excl && (s.moved || s.pos != here))) continue;
            if (sp.unit) {
                for (int t = 0; t < foes; ++t) {
                    if (h[t] <= 0 || !(u[t].cast_legal & gbit(at))) continue;
                    Node c = s;
                    if (spell_unit(sp, t, c)) push(c, 'S');
                    else h = saved;
                }
            } else if (sp.ground && sp.excl) {
                for (int k = 0; k < n_centres; ++k) {
                    bool ok;
                    centre_value(tables.centres[k], sp.slot, s, ok);
                    if (!ok) continue;
                    Node c = s;
                    hit_centre(tables.centres[k], sp.slot, c);
                    push(c, 'S');
                }
            }
        }
}

} // namespace

bool strike_possible(const World& world) {
    const auto& self = world.me();
    if (!self.alive || !enemy_seen(world)) return false;
    const auto& f = self.facts();
    const int reach = f.attack_range() + 1 + (f.has_dash() ? dash_steps : 0) + (f.passive == Passive::splash_attack ? 1 : 0);
    return enemy_within(world, my_position(), std::max(ability_range + 1, reach));
}

[[gnu::flatten]] Planned plan_strikes(const World& world, Pathing& pathing, Safety& safety, const Intent& intent) {
    Planned out;
    std::uint64_t fuel_start = 0;
    if constexpr (debug_search) {
        debug_block({ fuel_start = fuel(); });
    }
    Search S(world, safety, pathing, intent);
    std::array<std::uint64_t, 4> marks{};
    const auto mark = [&](int i) {
        if constexpr (debug_search) {
            debug_block({ marks[i] = fuel(); });
        }
    };
    if (!S.read()) return out;
    mark(0);
    S.grow(S.root());
    mark(1);
    const vec2 here = S.here;

    // Price the end tiles best bound first, the bound being hits and progress less the camps;
    // then each foe's Reach blow, largest Strike share first, while the tile can still win.
    const Field* field = S.walks ? goal_field(world, pathing, intent) : nullptr;
    const int here_steps = field ? field->at(here) : static_cast<int>(unreachable);
    const auto gain_to = [&](vec2 p) {
        if (here_steps == unreachable) return 0.0f;
        const int c = field->at(p);
        return c == unreachable ? 0.0f : static_cast<float>(here_steps - c) * S.step;
    };
    struct Striker {
        const ChampionBelief* e;
        const Strike* strike;
        int hor;
    };
    std::array<Striker, 16> strikers;
    int ns = 0;
    for (const auto& e : world.enemies)
        if (ns < 16 && e.alive && e.visible && dist(here, e.pos) <= Strike::max_reach + grid_r && safety.strike_of(e).reach >= 0) {
            int hor = -1;
            for (int k = 0; k < S.n_hors; ++k)
                if (S.hors[k] == &e) hor = k;
            strikers[ns++] = {&e, &safety.strike_of(e), hor};
        }
    std::array<Safety::CampHit, 24> camps;
    int nc = 0;
    for (const auto& m : safety.awake_members())
        if (nc < 24 && dist(here, m.pos) <= m.reach + grid_r) camps[nc++] = m;
    // An enemy Heart of Ruin hurt but not killed hits harder.
    const auto factor = [&](int c, int hor) {
        if (hor < 0) return 1.0f;
        const auto& e = *S.hors[hor];
        const float hp = std::min(e.health, S.hor_health(c, hor));
        if (hp <= 0 || e.damage_scale() <= 0) return 1.0f;
        return damage_scale(Passive::missing_health, hp, e.max_health) / e.damage_scale();
    };
    const auto camp_at = [&](vec2 p) {
        float camp = 0;
        for (int k = 0; k < nc; ++k)
            if (dist(p, camps[k].pos) <= camps[k].reach) camp += camps[k].strength * camps[k].weight;
        return camp;
    };
    // Picked by their bound before the camps, which can only lower it.
    struct Tile {
        int c;
        float bound, total;
        bool exact, done;
    };
    std::array<Tile, 49> tiles;
    int nt = 0;
    each_bit(S.has, [&](int c) {
        const float bound = S.best[c].raw + gain_to(S.tile(c));
        tiles[nt++] = {c, bound, bound, false, false};
    });
    float best_total = -1e30f;
    int chosen = -1, queries = 0, priced = 0, share_stops = 0, bound_stops = 0;
    bool capped = false;
    for (;;) {
        int i = -1;
        for (int k = 0; k < nt; ++k)
            if (!tiles[k].done && (i < 0 || tiles[k].bound > tiles[i].bound)) i = k;
        if (i < 0 || tiles[i].bound <= best_total) break;
        if (queries >= max_exact_queries) {
            capped = true;
            break;
        }
        auto& t = tiles[i];
        t.done = true;
        const vec2 p = S.tile(t.c);
        t.bound -= camp_at(p);
        t.total = t.bound;
        if (t.bound <= best_total) {
            ++bound_stops;
            continue;
        }
        std::array<std::pair<float, int>, 16> order;
        int no = 0;
        for (int k = 0; k < ns; ++k) {
            const float share = safety_params::hit_given_reach * strikers[k].strike->at(dist(p, strikers[k].e->pos)) * factor(t.c, strikers[k].hor);
            if (share <= 0) continue;
            int m = no++;
            for (; m > 0 && order[m - 1].first < share; --m) order[m] = order[m - 1];
            order[m] = {share, k};
        }
        float total = t.bound;
        bool cut = false;
        for (int m = 0; m < no && !cut; ++m) {
            const auto& sk = strikers[order[m].second];
            total -= safety_params::hit_given_reach * safety.blow(*sk.e, p).damage * factor(t.c, sk.hor);
            ++queries;
            cut = total <= best_total;
        }
        ++priced;
        t.total = total;
        if (cut) {
            ++share_stops;
            continue;
        }
        if (dist(p, here) >= 2) {
            std::array<Safety::ThreatAt, 16> at;
            const int k = safety.threats_at(p, at);
            for (int m = 0; m < k; ++m)
                if (!world.enemies[static_cast<std::size_t>(at[m].enemy)].visible) total -= safety_params::hit_given_reach * at[m].blow.damage;
            t.total = total;
        }
        t.exact = true;
        // The step guard covers radius 1-2 only.
        if (dist(p, here) == 3 && safety.lethal(p)) continue;
        if (total > best_total) best_total = total, chosen = i;
    }
    if (capped)
        for (int i = 0; i < nt; ++i) {
            auto& t = tiles[i];
            const vec2 p = S.tile(t.c);
            if (t.done || dist(p, here) == 3) continue;
            float total = t.bound - camp_at(p);
            for (int k = 0; k < ns; ++k)
                total -= safety_params::hit_given_reach * strikers[k].strike->at(dist(p, strikers[k].e->pos)) * factor(t.c, strikers[k].hor);
            t.total = total;
            if (total > best_total) best_total = total, chosen = i;
        }

    mark(2);
    // A cast worth its price from the start tile.
    valued = {world.round, here, false};
    for (const auto& sp : S.spells) {
        if (sp.slot < 0) continue;
        for (int t = 0; t < S.foes && sp.unit; ++t)
            valued.any |= (S.u[t].cast_legal & gbit(S.cell(here))) && !S.u[t].suicidal[sp.slot]
                          && S.u[t].spell[sp.slot] + S.u[t].spell_stun[sp.slot] > cast_cost;
        if (!sp.ground) continue;
        const Node root = S.root();
        for (int q = 0; q < S.n_distinct && !valued.any; ++q) {
            bool ok;
            valued.any |= S.centre_value(tables.centres[tables.distinct[q]], sp.slot, root, ok) > cast_cost && ok;
        }
    }

    if constexpr (debug_search) {
        debug_block({
            // The exhaustive enumerator must agree with the search on every end tile; the old
            // menu, scored the same way, must never beat the search's choice.
            S.exhaust(S.root());
            for (int c = 0; c < 49; ++c) {
                const bool a = S.has >> c & 1, b = S.exh_has >> c & 1;
                if (a != b || (a && std::abs(S.best[c].raw - tables.exh[c]) > 0.5f))
                    std::printf("SRCH-EXH %d %u tile %d,%d search %.1f exh %.1f\n", world.round, static_cast<unsigned>(world.me().handle),
                                S.tile(c).x, S.tile(c).y, a ? S.best[c].raw : -1.0f, b ? tables.exh[c] : -1.0f);
            }
            if (chosen >= 0 && !capped)
                for (int i = 0; i < nt; ++i) {
                    const int c = tiles[i].c;
                    const vec2 p = S.tile(c);
                    if (!(S.menu_has >> c & 1) || dist(p, here) == 3) continue;
                    // Priced (or cut short): the danger found there; unpriced: the camps only.
                    const float danger = tiles[i].done ? S.best[c].raw + gain_to(p) - tiles[i].total : camp_at(p);
                    const float old = tables.menu[c] + gain_to(p) - danger;
                    if (old > best_total + 0.5f)
                        std::printf("SRCH-DOM %d %u tile %d,%d menu %.1f search %.1f\n", world.round, static_cast<unsigned>(world.me().handle),
                                    p.x, p.y, old, best_total);
                }
        });
    }

    // Carry it out. A move a hidden unit refuses takes the next-ranked plan from where we stand.
    Seq seq;
    std::array<bool, 49> dropped{};
    if (chosen >= 0) seq = S.concrete(tiles[chosen].c), dropped[tiles[chosen].c] = true;
    int done = 0;
    bool failed = false;
    while (done < seq.n) {
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
                if (x.foe) cambc::self().attack(x.belief->live());
                else cambc::self().attack(world.map().groups[x.group].camp(x.member));
                ok = true;
                out.attacked = true;
                out.moved |= !S.melee;
            } catch (const cambc::error&) {
            }
            break;
        case Op::reset:
            try {
                ok = cambc::self().abilities()[S.reset].use();
            } catch (const cambc::error&) {
            }
            break;
        case Op::dash:
            try {
                ok = cambc::self().abilities()[S.dash].use(a.tile);
                blocked = !ok;
                pathing.invalidate();
            } catch (const cambc::error&) {
            }
            break;
        case Op::spell:
            try {
                const auto ability = cambc::self().abilities()[a.slot];
                ok = a.unit >= 0 ? ability.use(S.u[a.unit].belief->live()) : ability.use(a.tile);
                out.moved |= ok && S.spells[a.slot].excl;
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
        // The next-ranked plan that took the same actions so far, avoiding the revealed tile.
        int alt = -1;
        float alt_total = -1e30f;
        for (int i = 0; i < nt; ++i) {
            const auto& t = tiles[i];
            if (dropped[t.c] || !(t.exact || (capped && !t.done)) || t.total <= alt_total) continue;
            const Seq q = S.concrete(t.c);
            bool same = q.n > done;
            for (int k = 0; k < done && same; ++k) same = q.a[k] == seq.a[k];
            for (int k = done; k < q.n && same; ++k) same = !((q.a[k].op == Op::walk || q.a[k].op == Op::dash) && q.a[k].tile == a.tile);
            if (same) alt = i, alt_total = t.total;
        }
        if (alt < 0) {
            failed = true;
            break;
        }
        dropped[tiles[alt].c] = true;
        seq = S.concrete(tiles[alt].c);
    }
    mark(3);
    if (failed) out.attacked |= strike_enemy(world);

    if constexpr (debug_search) {
        debug_block({
            const std::uint64_t now = fuel(), used = fuel_start > now ? fuel_start - now : 0;
            std::printf("SRCH %d %u fuel %llu nodes %d offers %d tiles %d priced %d queries %d boundstop %d sharestop %d capped %d len %d read %llu grow %llu price %llu act %llu foes %d units %d left %llu\n",
                        world.round, static_cast<unsigned>(world.me().handle), static_cast<unsigned long long>(used), S.nodes, S.offers, nt,
                        priced, queries, bound_stops, share_stops, capped ? 1 : 0, seq.n,
                        static_cast<unsigned long long>(fuel_start - marks[0]), static_cast<unsigned long long>(marks[0] - marks[1]),
                        static_cast<unsigned long long>(marks[1] - marks[2]), static_cast<unsigned long long>(marks[2] - marks[3]), S.foes, S.n, static_cast<unsigned long long>(fuel_start));
        });
    }
    return out;
}

[[gnu::flatten]] void strike_after(const World& world, Safety& safety) {
    if (!world.me().alive || world.is_stale()) return;
    const auto state = my_state();
    if (state.contains(cambc::champion_state::submitting_gems) || state.contains(cambc::champion_state::recalling)
        || state.contains(cambc::champion_state::teleporting))
        return;
    if (!state.contains(cambc::champion_state::can_attack) && !state.contains(cambc::champion_state::can_cast)) return;
    Board b;
    const auto& f = world.me().facts();
    if (enemy_seen(world) && read_board(world, b, f.attack_range() + (f.passive == Passive::splash_attack ? 1 : 0))) {
        Healths h = b.healths();
        bool attacked = !b.attack;
        if (b.attack) {
            const Hit a = best_hit(b, h);
            attacked = attack(b, a);
            apply(b, a, h);
        }
        if (attacked && b.reset >= 0) {
            const Hit again = best_hit(b, h);
            if (again.target >= 0 && again.value > shield_worth(world, safety, b.shield, b.here) && use_slot(b.reset)) attack(b, again);
        }
    }
    if (!state.contains(cambc::champion_state::can_cast)) return;
    // A cast the search valued for a walk the goal did not take, or one a walk allows.
    const vec2 here = my_position();
    if (valued.round == world.round && valued.at == here) {
        if (valued.any) cast_at_enemies(world);
        return;
    }
    if (here == world.me().pos) return;
    bool walk_allows = false;
    for (int s = 0; s < 2; ++s)
        walk_allows |= f.abilities[s].hits_enemies() && !f.abilities[s].excludes_walking && world.me().ability_ready(s, world.round);
    if (walk_allows) cast_at_enemies(world);
}

[[gnu::flatten]] bool strike_enemy(const World& world) {
    if (!world.me().alive || !my_can_attack()) return false;
    Board b;
    const auto& f = world.me().facts();
    if (!read_board(world, b, f.attack_range() + (f.passive == Passive::splash_attack ? 1 : 0))) return false;
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
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && dist(self.pos, e.pos) <= reach && e.health <= 2 * self.strength) return true;
    return false;
}

} // namespace aph
