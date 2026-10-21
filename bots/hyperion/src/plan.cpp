#include "plan.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <new>
#include <string_view>
#include "abilities.h"
#include "params.h"
#include "pathing.h"
#include "safety.h"
#include "self_abilities.h"
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
        if (retaliation_kills(b.strength, retaliation, b.health)) continue;
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

} // namespace

float shield_cap(float amount, int duration, float damage) { return std::min(amount, static_cast<float>(duration) * damage); }

float shield_cap(Safety& safety, vec2 p, float amount, int duration) { return shield_cap(amount, duration, safety.damage_bound(p)); }

namespace {

// The shield cast left for the turn's end, over its duration, capped by what could hit us at p.
float shield_worth(const World& world, Safety& safety, int slot, vec2 p) {
    if (slot < 0) return 0;
    float amount = 0;
    try {
        amount = cambc::self().abilities()[slot].shield_amount();
    } catch (const cambc::error&) {
        return 0;
    }
    return shield_cap(safety, p, amount, world.me().facts().abilities[slot].duration);
}

// The enemy cast the search values most from its start tile this round, if any is worth its price:
// strike_after casts it if the goal did not walk.
struct Valued {
    int round = -1;
    vec2 at{-1, -1};
    bool any = false;
    int slot = -1;
    int target = -1;        // a unit cast's target, enemies[target]
    vec2 ground{-1, -1};    // else the area's centre
    std::uint16_t foes = 0; // the enemies the area's value counted, bits by enemies index
    float health = 0;       // ours when valued
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
constexpr int max_mates = 6;
// Exact queries per price (cap C1: Reach blows, threats_at calls, distance-3 rows; a flee's row
// counts each visible foe whose Strike reaches it, and its unseen blows); past it the rest keep
// their Strike price (C4).
constexpr int max_exact_queries = 10;
// guarded() asks per search (cap C7); past it an unasked end tile counts as guarded.
constexpr int max_guard_asks = 6;
// Nodes of a flee's tree; past them only walks and plain dashes grow, so every move is still
// recorded and only strike leaves are lost.
constexpr int max_flee_nodes = 16;

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
    // Enemies (bits by index) leaving our end tile's danger: when it dies, both of a pair, the
    // unseen one too; when stunned, itself if it has one turn before ours.
    std::uint16_t drop_kill = 0, drop_stun = 0;
    Grid legal = 0, cast_legal = 0; // where our attack, or a unit cast, reaches and sees it
};

struct Centre {
    vec2 tile;
    std::uint16_t foes = 0;
    std::uint32_t touched = 0;
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
    // goal's walk, which prices what the leaf score cannot (later turns). A flee prices them all.
    bool owed : 1 = false;
    // A dash taken and not refunded by a Vendetta kill: it costs dash_steps steps, priced with the
    // mode's step value (Prepared leaves hold no step terms).
    bool dash_paid : 1 = false;
    std::int8_t depth = 0;
    std::uint16_t stunned = 0;     // units stunned this turn
    float value = 0, pending = 0; // pending: a cast's price a Vendetta kill would refund
    float taken = 0;              // retaliation our own hits take this turn
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

// A leaf's step terms, by class: bit 0 its walk left for the goal (one step when the mode walks),
// bit 1 a dash paid (dash_steps steps). Terms[cls] is what the class adds at one mode's step value.
using Terms = std::array<float, 4>;
std::uint8_t leaf_class(const Node& s) { return static_cast<std::uint8_t>((s.walk && !s.excl ? 1 : 0) | (s.dash_paid ? 2 : 0)); }
// Class a prices at least as high as class b at every step value, walking or not.
constexpr bool class_ge(std::uint8_t a, std::uint8_t b) { return (a & 2) < (b & 2) || ((a & 2) == (b & 2) && (a & 1) >= (b & 1)); }
Terms class_terms(bool walks, float step) {
    // The dash's cooldown would otherwise carry us dash_steps steps.
    const float w = walks ? step : 0.0f, d = static_cast<float>(dash_steps) * step;
    return {0.0f, w, -d, w - d};
}

struct Choice {
    float raw; // hits less prices and wakes, plus a heal; its class's step terms left out
    vec2 w, d; // its walk and dash tiles
    std::int16_t leaf;
    std::uint16_t removed; // enemies out of the end tile's danger, by index
    std::int8_t mate;      // healed, or -1
    bool first;            // the heal cast from the start tile, before the moves
    std::uint8_t cls;
    float taken;           // a flee's: retaliation and woken camps' first hits on us; else 0
};

// The best leaves on one end tile, one per set of enemies removed and step class, less those
// another beats at every step value with a superset removed and no more taken. When full the
// lowest at `terms` goes: an option lost, never one overvalued.
constexpr int max_sets = 8;
struct Front {
    std::array<Choice, max_sets> e;
    int n;
    // The entry to fill with a leaf worth `raw` removing `r`, or -1.
    int admit(float raw, std::uint16_t r, std::uint8_t cls, const Terms& terms, float taken) {
        for (int i = 0; i < n; ++i)
            if ((e[i].removed & r) == r && e[i].raw >= raw && class_ge(e[i].cls, cls) && e[i].taken <= taken) return -1;
        int k = 0, low = -1;
        for (int i = 0; i < n; ++i)
            if ((e[i].removed & r) != e[i].removed || e[i].raw > raw || !class_ge(cls, e[i].cls) || e[i].taken < taken) {
                e[k] = e[i];
                if (low < 0 || e[k].raw + terms[e[k].cls] < e[low].raw + terms[e[low].cls]) low = k;
                ++k;
            }
        n = k;
        if (n < max_sets) return n++;
        return e[low].raw + terms[e[low].cls] < raw + terms[cls] ? low : -1;
    }
    float top(const Terms& terms) const {
        float x = e[0].raw + terms[e[0].cls];
        for (int i = 1; i < n; ++i) x = std::max(x, e[i].raw + terms[e[i].cls]);
        return x;
    }
};

// A flee's leaf whose last move has no strike after it: one record for all its end tiles, priced
// as a candidate on each, its walk and dash tiles named only for the tile carried out (cap C3).
constexpr int max_pend = 16;
struct Pend {
    Node s;
    std::array<Act, max_depth> stack;
    std::array<float, 2> hor;
    Grid ends;
    float v; // as Choice::raw, before the end tile's wake and heal
    std::uint16_t removed;
    std::uint8_t cls;
};

// Landings that hit, classed by the foes alive they hit and the camp groups they touch, each cell
// on first need.
struct LandClasses {
    std::uint32_t alive;
    int n;
    Grid known;
    std::array<Grid, 49> cls;
    std::array<std::uint32_t, 49> hit, touch;
    std::array<std::int8_t, 49> of;
};

// What lies within 1 of a tile, for ground centres.
struct Near {
    std::uint16_t foes;
    bool banned;
};

// Tiles within 4 of the start: a 9x9 window, index (y + 4) * 9 + x + 4 relative to it.
constexpr int win9_r = 4, win9_n = 9;

// Kept in static storage: zeroing it each turn would cost more than the search. In a union, so
// its members' default initialisers never run: they cost ~50k of the first turn's fuel.
struct Tables {
    std::array<Unit, max_units> u;
    std::array<Centre, max_centres> centres;
    std::array<vec2, max_unseen> unseen;
    std::array<Member, max_members> members;
    std::array<Waker, max_members> wakers;
    std::array<Front, 49> best, kept, exh, exh_kept; // kept: the cast left for the shield; valid by has bits
    std::array<Leaf, 512> leaves;
    std::array<Pend, max_pend> pend;
    std::array<LandClasses, 2> land_classes;
    std::array<Grid, 49> land_from;
    std::array<float, 49> menu;
    std::array<float, 49> heal_at; // the best heal cast from each tile
    std::array<std::int8_t, 49> heal_who;
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
    std::array<Front, 49>& best = tables.best;

    vec2 here;
    float strength = 0, health = 0, step = 0, shield_amount = 0;
    // prep_terms: the prepare's, for which entry a full front drops; terms: the price's mode.
    Terms prep_terms{}, terms{};
    int range = 1, land_radius = 0;
    // flee_tree: grown for a flee (prepare's intent), its pure moves kept as records.
    bool melee = true, splash = false, vendetta = false, lands = false, walks = false, moves = true, flee_tree = false;
    bool can_walk = false, can_attack = false, can_cast = false;
    int reset = -1, dash = -1, shield = -1, heal = -1;
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
    std::array<const ChampionBelief*, max_mates> mates{};
    int n_mates = 0;

    Grid free_ = 0, pass_ = 0, free_n = 0, land_here = 0, land_hits = 0, plain_here = 0, dom_dw = 0;
    Grid land_known = 0;
    // Landings never taken: those striking camps but no foe, those waking a sleeping striker (as the
    // old menu's landing_wakes; a woken pack keeps hitting while the fight stays), and those that may
    // hit an unseen Ren whose retaliation kills us (as cast_at_enemies).
    Grid land_bad = 0;

    std::array<Act, max_depth> stack;
    Grid has = 0, pend_has = 0;
    int nodes = 0, offers = 0, n_leaves = 0, n_pend = 0, pend_dropped = 0;
    int flee_cut = 0; // strike children a flee's node budget skipped

    Grid exh_has = 0, exh_kept_has = 0, menu_has = 0, kept_has = 0;
    std::array<char, max_depth> shape{};

    Search(const World& w, Safety& s, Pathing& p, const Intent& i) : world(w), safety(s), pathing(p), intent(i), f(w.me().facts()) {}

    int cell(vec2 p) const { return (p.y - here.y + grid_r) * grid_n + (p.x - here.x + grid_r); }
    vec2 tile(int c) const { return {here.x + c % grid_n - grid_r, here.y + c / grid_n - grid_r}; }
    bool in_grid(vec2 p) const { return std::abs(p.x - here.x) <= grid_r && std::abs(p.y - here.y) <= grid_r; }

    // A dash from cell c: at most 2 king steps not through walls or live camps, onto a free tile.
    Grid landings(int c) {
        if (land_known & gbit(c)) return tables.land_from[c];
        const Grid s = gbit(c), one = dilate(s);
        tables.land_from[c] = ((one | dilate(one & pass_)) & free_) & ~s & ~land_bad;
        land_known |= gbit(c);
        return tables.land_from[c];
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
    // The classes for the last two alive sets asked, with `hits` classed.
    int n_classes = 0, class_last = 0;
    LandClasses& land_classes(std::uint32_t alive, Grid hits) {
        int i = 0;
        while (i < n_classes && tables.land_classes[i].alive != alive) ++i;
        if (i == n_classes) {
            if (n_classes < 2) ++n_classes;
            else i = 1 - class_last;
            auto& e = tables.land_classes[i];
            e.alive = alive, e.n = 0, e.known = 0;
        }
        class_last = i;
        auto& e = tables.land_classes[i];
        each_bit(hits & ~e.known, [&](int k) {
            const std::uint32_t m = land_foes(k) & alive, t = land_touch(k);
            int j = 0;
            while (j < e.n && !(e.hit[j] == m && e.touch[j] == t)) ++j;
            if (j == e.n) e.hit[j] = m, e.touch[j] = t, e.cls[j] = 0, ++e.n;
            e.cls[j] |= gbit(k);
            e.of[k] = static_cast<std::int8_t>(j);
        });
        e.known |= hits;
        return e;
    }
    // The landings from any of the walk tiles `mids`, for the last mids asked.
    Grid reach_mids = ~Grid{0}, reach_last = 0;
    Grid walk_reach(Grid mids) {
        if (mids != reach_mids) {
            reach_mids = mids, reach_last = 0;
            each_bit(mids, [&](int m) { reach_last |= landings(m); });
        }
        return reach_last;
    }
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
    void add_unseen(int slot, float raw);
    void find_centres(int slot);
    void read_mates();
    // The heal worth most cast from cell c or, before moving, from the start; its mate in `who`.
    float heal_from(int c, std::int8_t& who, bool& first) const {
        const int h0 = cell(here);
        first = tables.heal_at[h0] >= tables.heal_at[c];
        who = tables.heal_who[first ? h0 : c];
        return tables.heal_at[first ? h0 : c];
    }
    // What the shield would absorb at p over its turns, as shield_worth prices it.
    float shield_at(vec2 p) const { return shield_cap(safety, p, shield_amount, f.abilities[shield].duration); }

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
    bool wake(std::uint32_t touched, vec2 E, float& cost, float* hit = nullptr);
    bool wakers_known_slot = false;
    // wake() by end tile, for the last touched set asked there: leaves differing only in their
    // hits share them.
    struct WakeMemo {
        std::uint32_t touched;
        float cost, hit;
        bool ok;
    };

    Grid wake_known = 0;
    bool wake_at(std::uint32_t touched, int c, float& cost, float* hit = nullptr) {
        static std::array<WakeMemo, 49> memo; // valid by wake_known
        auto& m = memo[c];
        if (!(wake_known & gbit(c)) || m.touched != touched) {
            m.touched = touched, m.ok = wake(touched, tile(c), m.cost, &m.hit);
            wake_known |= gbit(c);
        }
        cost = m.cost;
        if (hit) *hit = m.hit;
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
        if (n_here_wakes < static_cast<int>(here_wakes.size())) here_wakes[n_here_wakes++] = {touched, cost, 0, ok};
        return ok;
    }

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
    Grid ends_of(const Node& s);
    void mid_of(const Node& s, int c, vec2& w, vec2& d);
    void settle(const Node& s);
    void record(const Node& s, Grid ends);
    // Record g's candidates on cell c, as offer() would place them: put(keep, raw, mate, first, taken).
    template <class Put> void record_at(int g, int c, Put&& put) {
        const auto& p = tables.pend[g];
        float x = p.v, woken = 0;
        if (p.s.touched) {
            float cost;
            if (!wake_at(p.s.touched, c, cost, &woken)) return;
            x -= cost;
        }
        const float taken = p.s.taken + woken;
        put(p.s.cast && shield >= 0, x, std::int8_t{-1}, false, taken);
        if (p.s.cast && heal >= 0) {
            std::int8_t who;
            bool first;
            if (const float hv = heal_from(c, who, first); hv > 0) put(false, x + hv, who, first, taken);
        }
    }
    // The leaves ending on cell c (keep: those keeping the cast for the shield), one per set of
    // enemies removed; valid by has bits.
    const Front& front(int c, bool keep) const { return (keep ? tables.kept : best)[c]; }
    float top(int c, bool keep) const { return front(c, keep).top(terms); }
    template <class Mid> void offer(Grid ends, float v, const Node& s, int& leaf, Mid&& mid);
    std::uint16_t removed(const Node& s) const {
        std::uint16_t r = 0;
        for (int t = 0; t < foes; ++t) r |= h[t] <= 0 ? u[t].drop_kill : s.stunned >> t & 1 ? u[t].drop_stun : 0;
        return r;
    }
    static void finish(Seq& q, std::int8_t mate, bool first, bool shields) {
        if (mate >= 0) {
            const Act heal_act{Op::heal, mate};
            if (first) {
                for (int i = q.n; i > 0; --i) q.a[i] = q.a[i - 1];
                q.a[0] = heal_act;
            } else {
                q.a[q.n] = heal_act;
            }
            ++q.n;
        } else if (shields) {
            q.a[q.n++] = {Op::shield};
        }
    }
    Seq concrete(int c, bool keep, int entry, bool shields) const {
        const auto& ch = front(c, keep).e[entry];
        Seq q = tables.leaves[ch.leaf].seq;
        for (int i = 0; i < q.n; ++i) {
            if (q.a[i].op == Op::walk) q.a[i].tile = ch.w;
            if (q.a[i].op == Op::dash) q.a[i].tile = ch.d;
        }
        finish(q, ch.mate, ch.first, shields);
        return q;
    }
    Seq concrete_pend(int g, int c, std::int8_t mate, bool first, bool shields) {
        const auto& p = tables.pend[g];
        Seq q;
        q.n = p.s.depth;
        vec2 w{-1, -1}, d{-1, -1};
        mid_of(p.s, c, w, d);
        for (int i = 0; i < q.n; ++i) {
            q.a[i] = p.stack[i];
            if (q.a[i].op == Op::walk) q.a[i].tile = w;
            if (q.a[i].op == Op::dash) q.a[i].tile = d;
        }
        finish(q, mate, first, shields);
        return q;
    }
    // leaf <= -2: record -2 - leaf.
    float hor_health(int leaf, int k) const { return leaf >= 0 ? tables.leaves[leaf].hor[k] : tables.pend[-2 - leaf].hor[k]; }

    void exhaust(const Node& s);
    void offer_exh(const Node& s);
    bool menu_shape(int depth) const;
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
        std::array<vec2, 49> tiles;
        and_into(map.walls, box, scratch);
        const auto k = positions_into(scratch, tiles.data(), 49);
        for (std::uint32_t i = 0; i < k; ++i)
            out.walls |= gbit((tiles[i].y - centre.y + grid_r) * grid_n + tiles[i].x - centre.x + grid_r);
    }
    return out;
}

void Search::read_geometry() {
    static bitboard box{cambc::uninitialized}, t{cambc::uninitialized};
    static vec2 box_at{-1, -1};
    if (here != box_at) {
        clear_board(box);
        draw_square(box, here, grid_r);
        box_at = here;
    }
    const auto& terrain = terrain_grid(world.map(), here, box, t);
    std::array<vec2, 49> at;
    const auto read_into = [&](const bitboard& from, Grid& out) {
        and_into(from, box, t);
        const auto k = positions_into(t, at.data(), 49);
        out = 0;
        for (std::uint32_t i = 0; i < k; ++i) out |= gbit(cell(at[i]));
    };
    Grid blocked = 0, walls = 0;
    read_into(pathing.blocked(), blocked);
    // Dash paths are blocked by walls, camps and visible enemies (probe-dash-enemy).
    static bitboard foes_seen{cambc::uninitialized};
    camps_into(t);
    occupancy_into(team::enemy, foes_seen);
    or_into(t, foes_seen, t);
    read_into(t, walls);
    walls |= terrain.walls;
    free_ = terrain.inside & ~blocked;
    pass_ = terrain.inside & ~walls;
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
            add_unseen(s, raw);
            find_centres(s);
        }
    }
}

// The tiles cast_at_enemies keeps a ground cast's area off.
void Search::add_unseen(int s, float raw) {
    n_unseen = unseen_retaliators(world, here, f.abilities[s].reach(), raw, health, tables.unseen.data(), max_unseen);
}

// Allies a heal could reach from some tile, each worth what it restores, capped by what could hit
// it before the slot is ready again. Seen from the start, or from a tile that sees it.
void Search::read_mates() {
    if (heal < 0) return;
    float amount = 0;
    try {
        amount = cambc::self().abilities()[heal].heal_amount();
    } catch (const cambc::error&) {
        heal = -1;
        return;
    }
    const int r = f.abilities[heal].range();
    tables.heal_at.fill(0);
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible || n_mates == max_mates || dist(here, a.pos) > grid_r + r
            || test(world.map().ally_spawn, a.pos))
            continue;
        float hp = 0, top = 0;
        try {
            const auto c = a.live();
            // Allies start a recall at every turn end and cancel it unless wanted: one kept will
            // reach spawn and heal there.
            if (!c.is_visible() || kept_recall(c)) continue;
            hp = c.health(), top = c.max_health();
        } catch (const cambc::error&) {
            continue;
        }
        const float gain = std::min(amount, top - hp);
        if (!worth_healing(amount, gain, hp / top)) continue;
        const float value = shield_cap(safety, a.pos, gain, ability_cooldown);
        if (value <= 0) continue;
        const auto k = static_cast<std::int8_t>(n_mates);
        mates[n_mates++] = &a;
        each_bit(viewers(a.pos, r), [&](int c) {
            if (value > tables.heal_at[c]) tables.heal_at[c] = value, tables.heal_who[c] = k;
        });
    }
    if (n_mates == 0) heal = -1;
}

// Centres within range whose 3x3 holds a visible foe.
void Search::find_centres(int s) {
    const int r = std::min(f.abilities[s].range(), win9_r);
    // What each tile holds within 1, scattered from the foes and unseen tiles once.
    auto& near = tables.near;
    // Centres lie within 1 of a foe or an unseen tile: only those are read. Clearing all costs
    // less than clearing around many.
    if (foes + n_unseen > 8) std::memset(near.data(), 0, sizeof(near));
    else {
        for (int i = 0; i < foes; ++i) around(u[i].pos, [&](int j) { near[j] = {}; });
        for (int k = 0; k < n_unseen; ++k) around(tables.unseen[k], [&](int j) { near[j] = {}; });
    }
    for (int i = 0; i < foes; ++i)
        around(u[i].pos, [&](int j) { near[j].foes |= static_cast<std::uint16_t>(1u << i), near[j].banned |= u[i].suicidal[s]; });
    for (int k = 0; k < n_unseen; ++k) around(tables.unseen[k], [&](int j) { near[j].banned = true; });
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
                auto& ce = tables.centres[k];
                ce.tile = {here.x + xx - win9_r, here.y + yy - win9_r};
                ce.foes = near[j].foes, ce.banned = near[j].banned;
                ce.touched = touch1(ce.tile);
                const std::uint64_t key = ce.foes | std::uint64_t{ce.banned} << 16 | std::uint64_t{ce.touched} << 17;
                std::uint32_t h = static_cast<std::uint32_t>((key * 0x9E3779B97F4A7C15ull) >> 57);
                bool twin = false;
                for (; slots[h] && !twin; h = (h + 1) & 127) twin = keys[slots[h] - 1] == key;
                if (twin) continue;
                slots[h] = static_cast<std::uint8_t>(n_distinct + 1);
                keys[n_distinct] = key;
                tables.distinct[n_distinct++] = static_cast<std::uint8_t>(k);
            }
        }
    };
    for (int i = 0; i < foes; ++i)
        if (dist(here, u[i].pos) <= r + 1) add(u[i].pos);
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
    flee_tree = intent.flee;
    // A flee's moves are all the search's: no goal walks after it.
    walks = intent.walks && can_walk && !flee_tree;
    step = intent.step_value;
    prep_terms = terms = class_terms(walks, step);
    reset = f.slot_of(AbilityKind::attack_reset);
    dash = f.slot_of(AbilityKind::dash);
    shield = can_cast ? ready_slot(world, AbilityKind::shield) : -1;
    heal = can_cast ? ready_slot(world, AbilityKind::heal) : -1;
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
        x.drop_kill = static_cast<std::uint16_t>(1u << e.index);
        if (const auto* p = linked_partner(world, e); p && p->alive) x.drop_kill |= static_cast<std::uint16_t>(1u << p->index);
        // A stun takes only the next turn: with two before ours, the blow still lands.
        if (stuns && x.stunnable && turns_before_ours(world, e) == 1) x.drop_stun = static_cast<std::uint16_t>(1u << e.index);
        if (e.facts().passive == Passive::missing_health && n_hors < 2) x.hor = static_cast<std::int8_t>(n_hors), hors[n_hors++] = &e;
        x.legal = can_attack && dist(here, e.pos) <= grid_r + range ? viewers(e.pos, range) : 0;
        h[foes++] = x.health;
    }
    n = foes;
    if (foes == 0 && !flee_tree) return false;
    for (int i = 0; i < foes; ++i)
        for (int j = 0; j < foes && u[i].belief->facts().passive == Passive::linked_pair; ++j)
            if (j != i && u[j].belief->facts().passive == Passive::linked_pair) u[i].link = static_cast<std::int8_t>(j);
    read_geometry();
    // Camps matter only to what can touch them.
    if (touches) read_members();
    read_camps();
    float land_raw = 0;
    if (lands && (dash_ready || vendetta)) {
        try {
            const auto ability = cambc::self().abilities()[dash];
            const float raw = land_raw = ability.damage_amount();
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
    read_mates();
    if (shield >= 0) {
        try {
            shield_amount = cambc::self().abilities()[shield].shield_amount();
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
                if (dist(here, tables.members[k].pos) <= grid_r + land_radius) mark(tables.members[k].pos, land_bad);
            land_bad &= ~land_hits;
            for (int k = 0; k < n_members; ++k)
                if (tables.members[k].sleeper && dist(here, tables.members[k].pos) <= grid_r + land_radius)
                    mark(tables.members[k].pos, land_bad);
            std::array<vec2, max_unseen_tiles> ren;
            const int n_ren = unseen_retaliators(world, here, grid_r + land_radius, land_raw, health, ren.data(), max_unseen_tiles);
            for (int i = 0; i < n_ren; ++i) mark(ren[i], land_bad);
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
    s.taken += retaliation;
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
        s.dash_paid = false;
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
    if (d > 0) s.taken += x.retaliation;
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
    float v = 0;
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
        if (u[t].spell[slot] > 0) s.taken += u[t].retaliation;
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
    s.taken += retaliation;
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
// woken hit that could kill us or an ally. `hit`: what they take from us in the next camp phase.
bool Search::wake(std::uint32_t touched, vec2 E, float& cost, float* hit) {
    cost = 0;
    if (hit) *hit = 0;
    std::array<float, 8> ally_hit{};
    float on_us = 0, first = 0;
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
                first += w.strength;
            } else if (w.other_d <= w.reach && w.ally >= 0) {
                const auto& o = world.allies[static_cast<std::size_t>(w.ally)];
                if (o.channel == Channel::recall || o.channel == Channel::tribute) return false;
                if (const int at = world.map().group_at(o.pos); at >= 0 && world.camps[at].state == CampState::cleared) return false;
                if ((ally_hit[static_cast<std::size_t>(w.ally)] += w.strength) >= o.health) return false;
                cost += w.strength * (o.acted ? 1.0f : 0.5f);
            }
        }
    }
    if (hit) *hit = first;
    return on_us < health;
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
    const std::uint16_t r = ends ? removed(s) : 0;
    const std::uint8_t cls = leaf_class(s);
    each_bit(ends, [&](int c) {
        ++offers;
        float x = v, woken = 0;
        if (s.touched) {
            float cost;
            if (!wake_at(s.touched, c, cost, &woken)) return;
            x -= cost;
        }
        // Only a flee prices what we take: elsewhere it would only split the fronts.
        const float taken = flee_tree ? s.taken + woken : 0.0f;
        const auto place = [&](bool keep, float val, std::int8_t mate, bool first) {
            auto& fr = (keep ? tables.kept : best)[c];
            Grid& got = keep ? kept_has : has;
            if (!(got & gbit(c))) fr.n = 0;
            const int i = fr.admit(val, r, cls, prep_terms, taken);
            got |= gbit(c);
            if (i < 0) return;
            if (leaf < 0) {
                leaf = n_leaves++;
                auto& l = tables.leaves[leaf];
                l.seq.n = s.depth;
                for (int k = 0; k < s.depth; ++k) l.seq.a[k] = stack[k];
                for (int t = 0; t < foes; ++t)
                    if (u[t].hor >= 0) l.hor[u[t].hor] = h[t];
            }
            vec2 w{-1, -1}, d{-1, -1};
            mid(c, w, d);
            fr.e[i] = {val, w, d, static_cast<std::int16_t>(leaf), r, mate, first, cls, taken};
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

// The end tiles a leaf's moves can reach.
Grid Search::ends_of(const Node& s) {
    switch (s.seg) {
    case at_start: return gbit(cell(here));
    case walked: return free_n & s.req_w;
    case dashed: return (s.lset ? s.lset : plain_here) & s.req_d;
    case walked_dashed: return walk_reach(free_n & s.req_w) & (s.lset ? s.lset : ~land_hits) & s.req_d;
    case dashed_walked: {
        const Grid from = (s.lset ? s.lset : plain_here) & s.req_d;
        Grid ends = dilate(from) & free_ & s.req_e;
        // A landing itself is an end only when walked to from another.
        each_bit(ends & from, [&](int c) {
            if (!(dilate(gbit(c)) & from & ~gbit(c))) ends &= ~gbit(c);
        });
        return ends;
    }
    }
    return 0;
}

// The walk and dash tiles of a leaf ending on c, as settle() names them.
void Search::mid_of(const Node& s, int c, vec2& w, vec2& d) {
    switch (s.seg) {
    case at_start: break;
    case walked: w = tile(c); break;
    case dashed: d = tile(c); break;
    case walked_dashed: {
        Grid m = free_n & s.req_w;
        while (m && !(landings(std::countr_zero(m)) >> c & 1)) m &= m - 1;
        if (m) w = tile(std::countr_zero(m));
        d = tile(c);
        break;
    }
    case dashed_walked: {
        const Grid from = (s.lset ? s.lset : plain_here) & s.req_d;
        w = tile(c);
        d = tile(std::countr_zero(dilate(gbit(c)) & from & ~gbit(c)));
        break;
    }
    }
}

// A flee's pure move: past max_pend records the lowest at the prepare's step value goes.
void Search::record(const Node& s, Grid ends) {
    const std::uint8_t cls = leaf_class(s);
    int g = n_pend;
    const bool replaced = n_pend == max_pend;
    if (replaced) {
        ++pend_dropped;
        g = 0;
        const auto at = [&](int k) { return tables.pend[k].v + prep_terms[tables.pend[k].cls]; };
        for (int k = 1; k < max_pend; ++k)
            if (at(k) < at(g)) g = k;
        if (at(g) >= s.value + prep_terms[cls]) return;
    } else {
        ++n_pend;
    }
    auto& p = tables.pend[g];
    p.s = s;
    for (int k = 0; k < s.depth; ++k) p.stack[k] = stack[k];
    for (int t = 0; t < foes; ++t)
        if (u[t].hor >= 0) p.hor[u[t].hor] = h[t];
    p.ends = ends;
    p.v = s.value;
    p.removed = removed(s);
    p.cls = cls;
    if (!replaced) {
        pend_has |= ends;
        return;
    }
    pend_has = 0;
    for (int k = 0; k < n_pend; ++k) pend_has |= tables.pend[k].ends;
}

// Each end tile a leaf's moves can reach, offered once; a flee's pure moves are recorded.
void Search::settle(const Node& s) {
    if (s.owed) {
        if (flee_tree)
            if (const Grid ends = ends_of(s)) record(s, ends);
        return;
    }
    // Past the leaf table's size a new leaf is dropped.
    if (n_leaves == static_cast<int>(tables.leaves.size())) return;
    const float v = s.value;
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
        offer(walk_reach(mids) & allowed, v, s, leaf, [&](int c, vec2& w, vec2& d) {
            // The first mid it lands from.
            Grid m = mids;
            while (!(landings(std::countr_zero(m)) >> c & 1)) m &= m - 1;
            w = tile(std::countr_zero(m)), d = tile(c);
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
    const auto room = [&] {
        if (!flee_tree || nodes < max_flee_nodes) return true;
        ++flee_cut;
        return false;
    };
    if (s.attack)
        for (int t = 0; t < n; ++t) {
            if (h[t] <= 0 || !open(u[t].legal) || !room()) continue;
            Node c = s;
            if (legal_at(c, u[t].legal) && hit_unit(t, c)) push(c, {Op::attack, static_cast<std::int8_t>(t)});
            else h = saved;
        }
    if (s.cast && s.reset && !s.attack && room()) {
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
        if (dom && (flee_tree || strikes_left(c))) push(c, {Op::walk});
    }
    if (s.cast && s.dash && (s.seg == at_start || s.seg == walked)) {
        const bool first = s.seg == at_start;
        // Landings from the walk tiles the actions so far still allow.
        const Grid reach = first ? land_here : walk_reach(free_n & s.req_w);
        Node c = s;
        c.cast = false, c.dash = false, c.dash_paid = true, c.req_d = reach, c.owed = true;
        c.seg = first ? dashed : walked_dashed;
        if ((reach & ~land_hits) != 0 && (flee_tree || strikes_left(c))) push(c, {Op::dash});
        // Landings wake no sleeper, so those hitting the same foes and camp groups are alike.
        if (const Grid hits = lands ? reach & land_hits : 0; hits && room()) {
            std::uint32_t alive = 0;
            for (int t = 0; t < foes; ++t)
                if (h[t] > 0) alive |= 1u << t;
            // Each class's landings in reach, by its first: a child may reclass for another alive set.
            const auto& lc = land_classes(alive, hits);
            int kinds = 0;
            std::array<Grid, 49> alike;
            for (Grid left = hits; left;) {
                const Grid g = lc.cls[lc.of[std::countr_zero(left)]] & left;
                alike[kinds++] = g;
                left &= ~g;
            }
            for (int i = 0; i < kinds && room(); ++i) {
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
                    if (h[t] <= 0 || !open(u[t].cast_legal) || !room()) continue;
                    Node c = s;
                    if (legal_at(c, u[t].cast_legal) && spell_unit(sp, t, c))
                        push(c, {Op::spell, static_cast<std::int8_t>(t), static_cast<std::int8_t>(sp.slot)});
                    else h = saved;
                }
            } else if (sp.ground && sp.excl && s.seg == at_start && room()) {
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
                for (int i = 0; i < kinds && room(); ++i) {
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
    if (s.owed && !flee_tree) return;
    float v = s.value, woken = 0;
    if (s.touched) {
        float cost;
        if (!wake(s.touched, s.pos, cost, &woken)) return;
        v -= cost;
    }
    const int c = cell(s.pos);
    const std::uint16_t r = removed(s);
    const std::uint8_t cls = leaf_class(s);
    const float taken = flee_tree ? s.taken + woken : 0.0f;
    const auto put = [&](std::array<Front, 49>& tab, Grid& got, float x) {
        if (!(got & gbit(c))) tab[c].n = 0, got |= gbit(c);
        if (const int i = tab[c].admit(x, r, cls, prep_terms, taken); i >= 0)
            tab[c].e[i].raw = x, tab[c].e[i].removed = r, tab[c].e[i].cls = cls, tab[c].e[i].taken = taken;
    };
    // The menu is scored at the price's step value.
    const auto put_menu = [&](float x) {
        x += terms[cls];
        if (!(menu_has & gbit(c)) || x > tables.menu[c]) tables.menu[c] = x, menu_has |= gbit(c);
    };
    if (s.cast && shield >= 0) put(tables.exh_kept, exh_kept_has, v);
    else put(tables.exh, exh_has, v);
    float top = v; // the menu's, its shield left out
    if (s.cast && heal >= 0) {
        const float hv = std::max(tables.heal_at[cell(here)], tables.heal_at[c]);
        if (hv > 0) put(tables.exh, exh_has, top = v + hv);
    }
    if (menu_shape(s.depth)) put_menu(top);
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
            c.cast = false, c.dash = false, c.dash_paid = true, c.owed = true, c.pos = tile(l);
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

// The cast worth most from the start tile, priced as the search prices it there: a unit spell as an
// area holding its target alone, a centre less the camps it wakes.
void value_casts(const World& world, Search& S, vec2 here) {
    valued = {world.round, here};
    valued.health = S.health;
    float top = cast_cost;
    const Node root = S.root();
    const Grid at = gbit(S.cell(here));
    for (const auto& sp : S.spells) {
        if (sp.slot < 0) continue;
        for (int t = 0; t < S.foes && sp.unit; ++t) {
            const auto& x = S.u[t];
            if (!(x.cast_legal & at)) continue;
            bool ok;
            const float v = S.centre_value({x.pos, static_cast<std::uint16_t>(1u << t), 0, x.suicidal[sp.slot]}, sp.slot, root, ok);
            if (ok && v > top)
                top = v, valued.any = true, valued.slot = sp.slot, valued.target = x.belief->index, valued.ground = {-1, -1}, valued.foes = 0;
        }
        if (!sp.ground) continue;
        for (int q = 0; q < S.n_distinct; ++q) {
            const auto& ce = tables.centres[tables.distinct[q]];
            bool ok;
            float v = S.centre_value(ce, sp.slot, root, ok), cost = 0;
            if (!ok || (ce.touched && !S.wake_here(ce.touched, cost))) continue;
            if ((v -= cost) <= top) continue;
            top = v, valued.any = true, valued.slot = sp.slot, valued.target = -1, valued.ground = ce.tile, valued.foes = 0;
            for (std::uint32_t m = ce.foes; m; m &= m - 1)
                if (const int t = std::countr_zero(m); S.h[t] > 0) valued.foes |= static_cast<std::uint16_t>(1u << S.u[t].belief->index);
        }
    }
}

} // namespace

bool strike_possible(const World& world) {
    Phase phase{"strike_possible"};
    const auto& self = world.me();
    if (!self.alive || !enemy_seen(world)) return false;
    const auto& f = self.facts();
    const int reach = f.attack_range() + 1 + (f.has_dash() ? dash_steps : 0) + (f.passive == Passive::splash_attack ? 1 : 0);
    return enemy_within(world, my_position(), std::max(ability_range + 1, reach));
}

// One read and grow, kept for the turn's prices: one live Prepared at a time, in static storage.
struct Prepared {
    alignas(Search) unsigned char storage[sizeof(Search)];
    Search& search() { return *std::launder(reinterpret_cast<Search*>(storage)); }
    Intent intent; // the prepare's: the Search reads it
    bool live = false, ok = false, valued = false;
    std::uint32_t generation = 0, state = 0;
    vec2 pos{-1, -1};
    float health = 0;
    int prices = 0;
    // guarded() answers by end cell, shared by the search's prices (cap C7).
    Grid guard_asked = 0, guard_true = 0;
    int guard_asks = 0;
    std::uint64_t fuel_start = 0, read_fuel = 0, grow_fuel = 0; // debug_search
};

namespace {

Prepared prepared_slot;

[[gnu::flatten]] Planned price(Prepared& P, const Intent& intent) {
    Search& S = P.search();
    const World& world = S.world;
    Safety& safety = S.safety;
    Pathing& pathing = S.pathing;
    Planned out;
    std::uint64_t fuel_start = 0;
    if constexpr (debug_search) {
        debug_block({ fuel_start = fuel(); });
    }
    std::array<std::uint64_t, 4> marks{};
    const auto mark = [&](int i) {
        if constexpr (debug_search) {
            debug_block({ marks[i] = fuel(); });
        }
    };
    Phase step{"price"};
    // Normal, flee (danger and death priced, no guarded() ban) or chase (the walk's goal is the
    // prey's route); the leaves' step terms come from this intent.
    const char mode = intent.flee ? 'f' : intent.field ? 'c' : 'n';
    const bool flee = mode == 'f';
    S.walks = intent.walks && S.can_walk && !flee;
    S.step = intent.step_value;
    S.terms = class_terms(S.walks, S.step);
    const vec2 here = S.here;
    const Grid pend_ends = flee ? S.pend_has : 0;
    const Grid ends = S.has | S.kept_has | pend_ends;
    out.goal_free = (ends & ~gbit(S.cell(here))) == 0;

    // Price the end tiles best bound first, the bound being hits and progress less the camps;
    // then each foe's Reach blow, largest Strike share first, while the tile can still win.
    const cambc::distance_field* field = nullptr;
    if (flee) field = intent.field;
    else if (S.walks) {
        if (intent.field) field = intent.field;
        else if (const Field* g = goal_field(world, pathing, intent)) field = &g->steps;
    }
    int ref = field ? steps_at(*field, here) : static_cast<int>(unreachable);
    struct Striker {
        const ChampionBelief* e;
        const Strike* strike;
        int hor;
    };
    std::array<Striker, 16> strikers;
    std::array<std::int8_t, 16> hor_of;
    hor_of.fill(-1);
    std::uint16_t hor_bits = 0;
    int ns = 0;
    for (const auto& e : world.enemies) {
        if (ns == 16 || !e.alive || !e.visible || dist(here, e.pos) > Strike::max_reach + grid_r) continue;
        const auto& strike = safety.strike_of(e);
        if (strike.reach < 0 || dist(here, e.pos) > strike.reach + grid_r) continue;
        int hor = -1;
        for (int k = 0; k < S.n_hors; ++k)
            if (S.hors[k] == &e) hor = k;
        if (hor >= 0) hor_of[static_cast<std::size_t>(e.index)] = static_cast<std::int8_t>(hor), hor_bits |= static_cast<std::uint16_t>(1u << e.index);
        strikers[ns++] = {&e, &strike, hor};
    }
    // An enemy Heart of Ruin hurt but not killed hits harder.
    const auto factor = [&](int leaf, int hor) {
        if (hor < 0 || leaf == -1) return 1.0f;
        const auto& e = *S.hors[hor];
        const float hp = std::min(e.health, S.hor_health(leaf, hor));
        if (hp <= 0 || e.damage_scale() <= 0) return 1.0f;
        return damage_scale(Passive::missing_health, hp, e.max_health) / e.damage_scale();
    };
    // A flee: every visible blow in reach lands, the unseen ones at their chance, and where all of
    // it with the camps' round could kill us, our death hands them life_value and the bag. Inside a
    // camp's reach a step earns progress only on a tile out of every reach; other tiles pay the
    // camps' rounds to walk out (flee_camps' order). With no visible foe the escape (Safety::
    // escape_cost) decides first.
    const float death = flee ? params::life_value + params::gem_value * static_cast<float>(pair_gems(world, world.me())) : 0.0f;
    const bool inside = flee && safety.camp_damage(here) > 0;
    const int here_exit = inside ? safety.exit_rounds(here) : 0;
    const bool escape = inside && ns == 0;

    // Picked by their bound before the camps, which can only lower it. Each tile's candidates are
    // its best leaves per set of enemies removed, with the cast spent (or on a heal) or kept for
    // the shield, bounded by the shield's whole amount until the tile is priced.
    struct Tile {
        float top, bound, total, danger, shield, gain, camp, worst, lb, esc;
        int c;
        std::int8_t entry, mate, exit;
        bool exact, c4, done, keep, pend, first, tight, empty;
    };
    struct Cand {
        float raw, d, worst, taken;
        int leaf;
        std::uint16_t removed;
        bool keep, pend, first;
        std::int8_t entry, mate;
    };
    std::array<Tile, 49> tiles;
    std::array<int, 49> steps_of;
    std::array<Cand, 2 * max_sets + 2 * max_pend> cand;
    int nt = 0;
    const float shield_top = S.shield >= 0 ? S.shield_amount : 0.0f;
    const auto gather = [&](int c) {
        int k = 0;
        for (int keep = 0; keep < 2; ++keep) {
            if (!((keep ? S.kept_has : S.has) >> c & 1)) continue;
            const auto& fr = S.front(c, keep == 1);
            for (int i = 0; i < fr.n; ++i)
                cand[k++] = {fr.e[i].raw + S.terms[fr.e[i].cls], 0, 0, fr.e[i].taken, fr.e[i].leaf, fr.e[i].removed, keep == 1, false, false,
                             static_cast<std::int8_t>(i), -1};
        }
        if (pend_ends >> c & 1)
            for (int g = 0; g < S.n_pend; ++g) {
                const auto& pd = tables.pend[g];
                if (!(pd.ends >> c & 1)) continue;
                const float term = S.terms[pd.cls];
                S.record_at(g, c, [&](bool keep, float x, std::int8_t mate, bool first, float taken) {
                    cand[k++] = {x + term, 0, 0, taken, -2 - g, pd.removed, keep, true, first, static_cast<std::int8_t>(g), mate};
                });
            }
        return k;
    };
    // The records' best on any tile they reach: a heal or the shield at its most, before the wakes.
    std::array<float, 49> rec_top;
    if (pend_ends) {
        float heal_top = 0;
        if (S.heal >= 0)
            for (int c = 0; c < 49; ++c) heal_top = std::max(heal_top, tables.heal_at[c]);
        std::array<std::pair<float, int>, max_pend> by;
        for (int g = 0; g < S.n_pend; ++g) {
            const auto& pd = tables.pend[g];
            const bool cast = pd.s.cast;
            const float v = pd.v + S.terms[pd.cls] + std::max(cast && S.shield >= 0 ? shield_top : 0.0f, cast && S.heal >= 0 ? heal_top : 0.0f);
            int m = g;
            for (; m > 0 && by[m - 1].first < v; --m) by[m] = by[m - 1];
            by[m] = {v, g};
        }
        Grid covered = 0;
        for (int k = 0; k < S.n_pend; ++k) {
            const Grid now = tables.pend[by[k].second].ends & ~covered;
            each_bit(now, [&](int c) { rec_top[c] = by[k].first; });
            covered |= now;
        }
    }
    each_bit(ends, [&](int c) {
        float top = -1e30f;
        if (S.has >> c & 1) top = S.top(c, false);
        if (S.kept_has >> c & 1) top = std::max(top, S.top(c, true) + shield_top);
        if (pend_ends >> c & 1) top = std::max(top, rec_top[c]);
        steps_of[nt] = field ? steps_at(*field, S.tile(c)) : static_cast<int>(unreachable);
        auto& t = tiles[nt++];
        t.c = c, t.top = top, t.lb = t.esc = 0;
        t.keep = !(S.has >> c & 1);
        t.exact = t.c4 = t.done = t.pend = t.tight = t.empty = false;
    });
    // Off a flee's field (inside the walls it routes around), progress counts from the farthest end it labels.
    if (flee && ref == unreachable)
        for (int i = 0; i < nt; ++i)
            if (steps_of[i] != unreachable) ref = ref == unreachable ? steps_of[i] : std::max(ref, steps_of[i]);
    for (int i = 0; i < nt; ++i) {
        auto& t = tiles[i];
        t.gain = ref == unreachable || steps_of[i] == unreachable ? 0.0f : static_cast<float>(ref - steps_of[i]) * S.step;
        // Inside, the gain needs the tile's exit: until then it is at least 0.
        t.bound = t.total = t.top + (inside ? std::max(0.0f, t.gain) : t.gain);
    }
    float best_total = -1e30f, best_esc = 1e30f;
    int chosen = -1, queries = 0, priced = 0, share_stops = 0, bound_stops = 0;
    bool capped = false;
    // Only the end tile is stood on between turns: guarded() is asked only of a tile about to be
    // chosen, on the turn-start state whatever the plan kills or stuns. A flee is not banned.
    const bool guarding = !flee && pathing.guarding();
    Grid guard_seen = 0, guard_banned = 0; // this price's, by cell
    int guard_asks = 0, guard_skips = 0;
    const auto banned = [&](int i) {
        const int c = tiles[i].c;
        if (!guarding || c == S.cell(here)) return false;
        const Grid bit = gbit(c);
        if (!(guard_seen & bit)) {
            guard_seen |= bit;
            bool out = true;
            if (P.guard_asked & bit) out = (P.guard_true & bit) != 0;
            else if (P.guard_asks < max_guard_asks) {
                ++P.guard_asks, ++guard_asks;
                P.guard_asked |= bit;
                if ((out = safety.guarded(S.tile(c)))) P.guard_true |= bit;
            }
            if (out) guard_banned |= bit, ++guard_skips;
        }
        return (guard_banned & bit) != 0;
    };
    // The camps at a tile: their expected hit, and in a flee the rounds to walk out of their reach.
    const auto tighten = [&](Tile& t) {
        t.tight = true;
        const vec2 p = S.tile(t.c);
        t.camp = safety.camp_damage(p, false);
        t.worst = t.lb = 0, t.exit = 0;
        if (flee && (t.worst = safety.camp_damage(p)) > 0) {
            t.exit = static_cast<std::int8_t>(safety.exit_rounds(p));
            t.camp += t.worst * static_cast<float>(std::max(0, t.exit - 1));
            t.lb = t.worst * static_cast<float>(t.exit);
            if (inside) t.gain = 0;
        }
        t.bound = t.total = t.top + t.gain - t.camp;
        t.danger = t.camp;
    };
    // Sorted once (C2). A flee's ties go to the nearer tile, which keeps a dash.
    const auto before = [&](int a, int b) {
        const Tile &x = tiles[a], &y = tiles[b];
        if (escape && x.lb != y.lb) return x.lb < y.lb;
        if (x.bound != y.bound) return x.bound > y.bound;
        if (flee)
            if (const int dx = dist(S.tile(x.c), here), dy = dist(S.tile(y.c), here); dx != dy) return dx < dy;
        return x.c < y.c;
    };
    const auto heap_less = [&](int a, int b) { return before(b, a); };
    const auto lost = [&](const Tile& t) {
        if (escape) return t.lb > best_esc || (t.lb == best_esc && t.bound <= best_total);
        return t.bound <= best_total;
    };
    std::array<int, 49> heap;
    int nh = nt;
    for (int i = 0; i < nt; ++i) heap[i] = i;
    std::make_heap(heap.begin(), heap.begin() + nh, heap_less);
    const auto requeue = [&](int i) {
        heap[nh++] = i;
        std::push_heap(heap.begin(), heap.begin() + nh, heap_less);
    };
    // An escape tightens at most C1 tiles (cap C8): an untightened tile's camps count 0, so with
    // every end tile in a camp's reach it would tighten them all. The rest are then cut.
    int tightened = 0;
    Grid cut = 0;
    const auto cut_rest = [&](int i) {
        cut |= gbit(tiles[i].c);
        int k = 0;
        for (int j = 0; j < nh; ++j)
            if (tiles[heap[j]].tight) heap[k++] = heap[j];
            else cut |= gbit(tiles[heap[j]].c);
        nh = k;
        std::make_heap(heap.begin(), heap.begin() + nh, heap_less);
    };
    while (nh > 0 && !lost(tiles[heap[0]])) {
        const int i = heap[0];
        std::pop_heap(heap.begin(), heap.begin() + nh, heap_less);
        --nh;
        auto& t = tiles[i];
        if (!flee && queries >= max_exact_queries) {
            capped = true;
            requeue(i);
            break;
        }
        if (!t.tight) {
            if (escape && ++tightened > max_exact_queries) {
                cut_rest(i);
                continue;
            }
            tighten(t);
            if (lost(t)) {
                t.done = true;
                ++bound_stops;
                continue;
            }
            // A flee's camps can sink a tile far: it waits for its turn by its tight bound.
            if (flee && nh > 0 && before(heap[0], i)) {
                requeue(i);
                continue;
            }
        }
        const vec2 p = S.tile(t.c);
        int row_cost = 1;
        if (flee) {
            row_cost = 0;
            for (int k = 0; k < ns; ++k) row_cost += strikers[k].strike->hits(dist(p, strikers[k].e->pos)) ? 1 : 0;
            row_cost = std::max(1, row_cost);
        }
        if (queries + row_cost > max_exact_queries) {
            capped = true;
            requeue(i);
            break;
        }
        t.done = true;
        const float base = t.gain - t.camp;
        const int nk = gather(t.c);
        if (nk == 0) {
            t.empty = true;
            continue;
        }
        bool kept = false;
        for (int j = 0; j < nk; ++j) kept |= cand[j].keep;
        float sh = shield_top;
        int arg = 0;
        const auto top = [&] {
            float x = -1e30f;
            for (int j = 0; j < nk; ++j)
                if (const float y = cand[j].raw + (cand[j].keep ? sh : 0.0f) - cand[j].d; y > x) x = y, arg = j;
            return x + base;
        };
        const auto most_danger = [&] {
            float x = 0;
            for (int j = 0; j < nk; ++j) x = std::max(x, cand[j].d);
            return x;
        };
        float total;
        if (flee) {
            // The whole row: the death rule needs every blow at once. Its unseen blows are counted
            // once read.
            const TileDanger row = safety.tile(p);
            queries += row_cost + (row.unseen_mask ? 1 : 0);
            std::uint16_t rm_any = 0;
            for (int j = 0; j < nk; ++j) rm_any |= cand[j].removed;
            std::array<float, 16> b{}, ub{};
            for (std::uint32_t m = row.vis_mask & (rm_any | hor_bits); m; m &= m - 1) {
                const int e = std::countr_zero(m);
                b[static_cast<std::size_t>(e)] = safety.blow(world.enemies[static_cast<std::size_t>(e)], p).damage;
            }
            if (rm_any & row.unseen_mask) {
                std::array<Safety::ThreatAt, 16> at;
                ++queries;
                const int k = safety.threats_at(p, at);
                for (int m = 0; m < k; ++m)
                    if (!world.enemies[static_cast<std::size_t>(at[m].enemy)].visible) ub[static_cast<std::size_t>(at[m].enemy)] = at[m].blow.damage;
            }
            for (int j = 0; j < nk; ++j) {
                auto& x = cand[j];
                float vis = row.vis, uns = row.unseen;
                for (std::uint32_t m = x.removed & row.vis_mask; m; m &= m - 1) vis -= b[static_cast<std::size_t>(std::countr_zero(m))];
                for (std::uint32_t m = hor_bits & row.vis_mask & ~x.removed; m; m &= m - 1) {
                    const auto e = static_cast<std::size_t>(std::countr_zero(m));
                    vis += b[e] * (factor(x.leaf, hor_of[e]) - 1.0f);
                }
                for (std::uint32_t m = x.removed & row.unseen_mask; m; m &= m - 1) uns -= ub[static_cast<std::size_t>(std::countr_zero(m))];
                x.worst = vis + uns + row.camp_worst;
                x.d = vis + safety_params::hit_given_reach * uns;
            }
            // A kept shield absorbs the blows, not what our own hits take before it is cast: whole
            // for death, capped for its worth.
            const auto dies = [&](const Cand& x, float absorb) { return x.worst + x.taken >= S.health + (x.keep ? absorb : 0.0f); };
            for (int j = 0; j < nk; ++j)
                if (dies(cand[j], shield_top)) cand[j].d += death;
            total = top();
            if (escape) {
                t.esc = safety.escape_cost(p);
            } else {
                debug_block({ t.esc = row.worst() + row.camp_worst * static_cast<float>(std::max(0, t.exit - 1)); });
            }
            // The shield's worth only where it could decide the choice. Elsewhere the tile keeps
            // its total without the shield, as another plan's fallback never casts one unpriced.
            const bool open = escape ? t.esc < best_esc || (t.esc == best_esc && total > best_total) : total > best_total;
            if (kept && shield_top > 0) {
                if (open) {
                    sh = S.shield_at(p);
                } else {
                    sh = 0;
                    for (int j = 0; j < nk; ++j)
                        if (cand[j].keep && dies(cand[j], 0) && !dies(cand[j], shield_top)) cand[j].d += death;
                }
                total = top();
            }
            ++priced;
            t.exact = true;
        } else {
            const bool far = dist(p, here) == 3;
            std::uint16_t hit_by = 0xffff, unseen_by = 0;
            if (far) {
                // End tiles are open, so the row never asks Reach about a wall.
                const auto& row = safety.tile(p);
                ++queries;
                hit_by = row.vis_mask, unseen_by = row.unseen_mask;
            }
            const auto add = [&](int enemy, float b, int hor) {
                for (int j = 0; j < nk; ++j)
                    if (!(cand[j].removed >> enemy & 1)) cand[j].d += b * factor(cand[j].leaf, hor);
            };
            std::array<std::pair<float, int>, 16> order;
            int no = 0;
            for (int k = 0; k < ns; ++k) {
                if (!(hit_by >> strikers[k].e->index & 1)) continue;
                float most = 0;
                for (int j = 0; j < nk; ++j)
                    if (!(cand[j].removed >> strikers[k].e->index & 1)) most = std::max(most, factor(cand[j].leaf, strikers[k].hor));
                const float share = safety_params::hit_given_reach * strikers[k].strike->at(dist(p, strikers[k].e->pos)) * most;
                if (share <= 0) continue;
                int m = no++;
                for (; m > 0 && order[m - 1].first < share; --m) order[m] = order[m - 1];
                order[m] = {share, k};
            }
            total = top();
            bool cut = false;
            for (int m = 0; m < no && !cut; ++m) {
                const auto& sk = strikers[order[m].second];
                add(sk.e->index, safety_params::hit_given_reach * safety.blow(*sk.e, p).damage, sk.hor);
                ++queries;
                total = top();
                cut = total <= best_total;
            }
            if (!cut && kept && sh > 0) {
                sh = S.shield_at(p);
                total = top();
                cut = total <= best_total;
            }
            ++priced;
            t.total = total;
            t.danger = t.camp + most_danger();
            if (cut) {
                ++share_stops;
                continue;
            }
            // threats_at's unseen hits are a subset of the row's; at distance 2 the row's blows were asked above.
            if (dist(p, here) == 2) unseen_by = safety.tile(p).unseen_mask;
            if (unseen_by) {
                std::array<Safety::ThreatAt, 16> at;
                ++queries;
                const int k = safety.threats_at(p, at);
                for (int m = 0; m < k; ++m)
                    if (!world.enemies[static_cast<std::size_t>(at[m].enemy)].visible)
                        add(at[m].enemy, safety_params::hit_given_reach * at[m].blow.damage, -1);
                total = top();
            }
            t.exact = true;
        }
        t.total = total;
        t.danger = t.camp + most_danger();
        t.keep = cand[arg].keep;
        t.pend = cand[arg].pend;
        t.entry = cand[arg].entry;
        t.mate = cand[arg].mate;
        t.first = cand[arg].first;
        t.shield = t.keep ? sh : 0.0f;
        const bool better = escape ? t.esc < best_esc || (t.esc == best_esc && total > best_total) : total > best_total;
        if (better && !banned(i)) best_total = total, best_esc = t.esc, chosen = i;
    }
    // Unpriced tiles keep their Strike price and the camps, and no shield (C4), priced on in bound
    // order while one can still win: no C4 total exceeds its tile's bound. A flee leaves out
    // distance 3, which no blow was asked about. In an escape an unpriced tile's escape cost is known
    // only down to its camps (lb), so it beats a priced tile only on a lower lb.
    if (capped) {
        bool exact_best = chosen >= 0;
        float best_lb = exact_best ? tiles[chosen].lb : 1e30f;
        const auto c4_lost = [&](const Tile& t) {
            if (escape) return t.lb > best_lb || (t.lb == best_lb && (exact_best || t.bound <= best_total));
            return t.bound <= best_total;
        };
        while (nh > 0 && !c4_lost(tiles[heap[0]])) {
            const int i = heap[0];
            std::pop_heap(heap.begin(), heap.begin() + nh, heap_less);
            --nh;
            auto& t = tiles[i];
            if (!t.tight) {
                if (escape && ++tightened > max_exact_queries) {
                    cut_rest(i);
                    continue;
                }
                tighten(t);
                if (c4_lost(t)) {
                    t.done = true;
                    continue;
                }
                if (nh > 0 && before(heap[0], i)) {
                    requeue(i);
                    continue;
                }
            }
            t.done = true;
            const vec2 p = S.tile(t.c);
            if (flee && dist(p, here) == 3) continue;
            const int nk = gather(t.c);
            if (nk == 0) {
                t.empty = true;
                continue;
            }
            const float chance = flee ? 1.0f : safety_params::hit_given_reach;
            for (int k = 0; k < ns; ++k) {
                const float b = strikers[k].strike->at(dist(p, strikers[k].e->pos));
                if (b <= 0) continue;
                for (int j = 0; j < nk; ++j)
                    if (!(cand[j].removed >> strikers[k].e->index & 1)) {
                        const float x = b * factor(cand[j].leaf, strikers[k].hor);
                        cand[j].d += chance * x, cand[j].worst += x;
                    }
            }
            const auto net = [&](const Cand& x) { return x.raw - x.d - (flee && x.worst + x.taken + t.worst >= S.health ? death : 0.0f); };
            int arg = 0;
            for (int j = 1; j < nk; ++j)
                if (net(cand[j]) > net(cand[arg])) arg = j;
            t.keep = cand[arg].keep;
            t.pend = cand[arg].pend;
            t.entry = cand[arg].entry;
            t.mate = cand[arg].mate;
            t.first = cand[arg].first;
            t.shield = 0;
            t.total = net(cand[arg]) + t.gain - t.camp;
            t.esc = t.lb;
            t.c4 = true;
            const bool better = escape ? t.lb < best_lb || (t.lb == best_lb && !exact_best && t.total > best_total) : t.total > best_total;
            if (better && !banned(i)) best_total = t.total, best_esc = t.esc, best_lb = t.lb, exact_best = false, chosen = i;
        }
    }

    debug_block({
        // A cut tile could have won on cost if its camps alone undercut the choice's escape cost, or
        // on the tie if they match it and its bound as tighten() would set it is higher.
        if (cut) {
            int cost = 0, tie = 0;
            for (int i = 0; i < nt; ++i) {
                const auto& t = tiles[i];
                if (!(cut >> t.c & 1)) continue;
                const vec2 p = S.tile(t.c);
                float worst = 0, exp = 0;
                for (const auto& m : safety.awake_members())
                    if (in_square(p, m.pos, m.reach)) worst += m.strength, exp += m.strength * m.weight;
                const float lb = safety.exit_damage_unfilled(p);
                const float bound = worst > 0 ? t.top - exp - (lb - worst) : t.top + t.gain - exp;
                if (chosen < 0 || lb < best_esc - 0.01f) ++cost;
                else if (lb <= best_esc + 0.01f && bound > best_total + 0.01f) ++tie;
            }
            std::printf("ESC-CUT %d tiles %d cut %d cost_beat %d tie_beat %d\n", world.round, nt, std::popcount(cut), cost, tie);
        }
    });
    mark(2);
    // The start tile's casts for strike_after, once for the turn's search: a flee's moves are all its own.
    if (!flee && !P.valued) value_casts(world, S, here), P.valued = true;

    if constexpr (debug_search) {
        debug_block({
            // The exhaustive enumerator must agree with the search on every end tile; the old
            // menu, scored the same way, must never beat the search's choice.
            S.exh_has = S.exh_kept_has = S.menu_has = 0;
            S.exhaust(S.root());
            // A flee's records go into copies of the fronts, as offer() would have placed them.
            static std::array<Front, 49> sb, sk;
            sb = S.best, sk = tables.kept;
            Grid hb = S.has, hk = S.kept_has;
            for (int g = 0; g < S.n_pend; ++g) {
                const auto& pd = tables.pend[g];
                each_bit(pd.ends, [&](int c) {
                    S.record_at(g, c, [&](bool keep, float x, std::int8_t, bool, float taken) {
                        auto& fr = (keep ? sk : sb)[c];
                        Grid& got = keep ? hk : hb;
                        if (!(got >> c & 1)) fr.n = 0, got |= gbit(c);
                        if (const int i = fr.admit(x, pd.removed, pd.cls, S.prep_terms, taken); i >= 0)
                            fr.e[i].raw = x, fr.e[i].removed = pd.removed, fr.e[i].cls = pd.cls, fr.e[i].taken = taken;
                    });
                });
            }
            // Per end tile, each front's entries are matched by the other's: as many enemies removed
            // or more, for as much at every step value and no more taken. A flee tree cut by its
            // node budget lacks strike leaves.
            const auto covers = [](const Front& a, const Front& b) {
                for (int i = 0; i < b.n; ++i) {
                    bool ok = false;
                    for (int j = 0; j < a.n && !ok; ++j)
                        ok = (a.e[j].removed & b.e[i].removed) == b.e[i].removed && a.e[j].raw >= b.e[i].raw - 0.5f
                             && class_ge(a.e[j].cls, b.e[i].cls) && a.e[j].taken <= b.e[i].taken + 0.5f;
                    if (!ok) return false;
                }
                return true;
            };
            for (int c = 0; c < 49 && S.pend_dropped == 0 && S.flee_cut == 0; ++c)
                for (int keep = 0; keep < 2; ++keep) {
                    const bool a = (keep ? hk : hb) >> c & 1, b = (keep ? S.exh_kept_has : S.exh_has) >> c & 1;
                    const Front &x = (keep ? sk : sb)[c], &y = (keep ? tables.exh_kept : tables.exh)[c];
                    if (a && b && (x.n == max_sets || y.n == max_sets)) continue;
                    if (a != b || (a && (!covers(x, y) || !covers(y, x))))
                        std::printf("SRCH-EXH %d %u tile %d,%d keep %d search %.1f/%d exh %.1f/%d mode %c\n", world.round,
                                    static_cast<unsigned>(world.me().handle), S.tile(c).x, S.tile(c).y, keep, a ? x.top(S.terms) : -1.0f,
                                    a ? x.n : 0, b ? y.top(S.terms) : -1.0f, b ? y.n : 0, mode);
                }
            // An escape is chosen by its escape cost, not by this score.
            if (chosen >= 0 && !capped && !escape && S.flee_cut == 0)
                for (int i = 0; i < nt; ++i) {
                    const int c = tiles[i].c;
                    const vec2 p = S.tile(c);
                    if (!(S.menu_has >> c & 1) || dist(p, here) == 3 || (guard_banned >> c & 1)) continue;
                    // Priced (or cut short): the larger candidate's danger found there; unpriced: the camps
                    // only, summed here: asking the table would change fuel outside debug_block. An
                    // unpriced flee tile is left at its bound, which the choice already beat.
                    float danger = tiles[i].danger, gain = tiles[i].gain;
                    if (!tiles[i].tight) {
                        danger = 0;
                        if (!flee)
                            for (const auto& m : safety.awake_members())
                                if (in_square(p, m.pos, m.reach)) danger += m.strength * m.weight;
                        if (inside) gain = std::max(0.0f, gain);
                    }
                    const float old = tables.menu[c] + gain - danger;
                    if (old > best_total + 0.5f)
                        std::printf("SRCH-DOM %d %u tile %d,%d menu %.1f search %.1f mode %c\n", world.round,
                                    static_cast<unsigned>(world.me().handle), p.x, p.y, old, best_total, mode);
                }
        });
    }

    // Carry it out. A move a hidden unit refuses takes the next-ranked plan from where we stand.
    step.next("act");
    // The end tile passed guarded(); the moves before it may cross guarded tiles.
    class Unguarded {
    public:
        explicit Unguarded(Pathing& p) : p_(p), was_(p.guarding()) { p.set_guarding(false); }
        ~Unguarded() { p_.set_guarding(was_); }

    private:
        Pathing& p_;
        bool was_;
    } unguarded{pathing};
    Seq seq;
    std::array<bool, 49> dropped{};
    const auto concrete = [&](const Tile& t) {
        const bool shields = t.keep && t.shield > 0;
        return t.pend ? S.concrete_pend(t.entry, t.c, t.mate, t.first, shields) : S.concrete(t.c, t.keep, t.entry, shields);
    };
    if (chosen >= 0) seq = concrete(tiles[chosen]), dropped[tiles[chosen].c] = true;
    int done = 0;
    bool failed = false;
    vec2 cur = here;
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
        case Op::heal:
            try {
                ok = cambc::self().abilities()[S.heal].use(S.mates[a.unit]->live());
            } catch (const cambc::error&) {
            }
            break;
        case Op::shield: ok = use_slot(S.shield); break;
        }
        if (ok) {
            if (a.op == Op::walk || a.op == Op::dash) cur = a.tile;
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
        // The next-ranked plan that took the same actions so far, avoiding the revealed tile. If every
        // other ends on a guarded tile, one ending where we stand is taken: we stay there either way.
        const int cur_c = S.cell(cur);
        int alt = -1, stay = -1;
        for (;;) {
            alt = -1;
            float alt_total = -1e30f;
            for (int i = 0; i < nt; ++i) {
                if (dropped[tiles[i].c] || ((guard_banned >> tiles[i].c & 1) && tiles[i].c != cur_c) || !(tiles[i].exact || tiles[i].c4)
                    || tiles[i].total <= alt_total)
                    continue;
                const auto& t = tiles[i];
                const Seq q = concrete(t);
                bool same = q.n > done;
                for (int k = 0; k < done && same; ++k) same = q.a[k] == seq.a[k];
                for (int k = done; k < q.n && same; ++k) same = !((q.a[k].op == Op::walk || q.a[k].op == Op::dash) && q.a[k].tile == a.tile);
                if (same) alt = i, alt_total = t.total;
            }
            if (alt < 0 || !banned(alt)) break;
            dropped[tiles[alt].c] = true;
            if (tiles[alt].c == cur_c) stay = alt;
        }
        if (alt < 0) alt = stay;
        if (alt < 0) {
            failed = true;
            break;
        }
        chosen = alt;
        dropped[tiles[alt].c] = true;
        seq = concrete(tiles[alt]);
    }
    mark(3);
    debug_block({
        if (guard_asks) std::printf("SRCH-GUARD %d %d %d\n", world.round, guard_asks, guard_skips);
    });
    if (failed) out.attacked |= strike_enemy(world);
    out.acted = done > 0 || out.attacked;
    out.carried = chosen >= 0 && !failed;
    // A tile left unpriced by the query cap had no shield priced: the turn's end decides it.
    out.searched = chosen >= 0 && !failed && tiles[chosen].exact;

    if (flee) {
        debug_block({
            const Tile* ct = chosen >= 0 ? &tiles[chosen] : nullptr;
            const int st = ct ? steps_of[chosen] : -1;
            std::printf("FLEE %d %d %d %.1f %d %d tile %d,%d escape %d capped %d\n", world.round, here_exit, ct && ct->tight ? ct->exit : -1,
                        ct && (ct->exact || escape) ? ct->esc : -1.0f, st == unreachable ? -1 : st, out.carried ? 1 : 0,
                        ct ? S.tile(ct->c).x : -1, ct ? S.tile(ct->c).y : -1, escape ? 1 : 0, capped ? 1 : 0);
            // flee_camps' argmin over here and its neighbours: none may escape for less. An unpriced
            // tile is bounded by its camps (0 before they were counted), which the search beat unless
            // capped or cut (ESC-CUT judges those).
            if (escape && ct)
                for (int i = 0; i < nt; ++i) {
                    const auto& t = tiles[i];
                    const vec2 p = S.tile(t.c);
                    if (dist(p, here) > 1 || t.empty || (!t.exact && capped) || (cut >> t.c & 1)) continue;
                    const float e = t.exact ? t.esc : t.tight ? t.lb : 0.0f;
                    if (e < ct->esc - 0.01f)
                        std::printf("FLEE-CAMP-MISMATCH %d tile %d,%d esc %.1f exact %d chosen %d,%d esc %.1f\n", world.round, p.x, p.y, e,
                                    t.exact ? 1 : 0, S.tile(ct->c).x, S.tile(ct->c).y, ct->esc);
                }
        });
    }

    if constexpr (debug_search) {
        debug_block({
            const bool first = P.prices == 1;
            const std::uint64_t start = first ? P.fuel_start : fuel_start, now = fuel(), used = start > now ? start - now : 0;
            char cast = '-';
            for (int k = 0; k < seq.n; ++k)
                if (seq.a[k].op == Op::heal || seq.a[k].op == Op::shield) cast = seq.a[k].op == Op::heal ? 'h' : 's';
            unsigned rm = 0;
            int sets = 0;
            if (chosen >= 0) {
                const auto& t = tiles[chosen];
                rm = t.pend ? tables.pend[t.entry].removed : S.front(t.c, t.keep).e[t.entry].removed;
            }
            for (int i = 0; i < nt; ++i) {
                const int c = tiles[i].c;
                if (S.has >> c & 1) sets = std::max(sets, S.front(c, false).n);
                if (S.kept_has >> c & 1) sets = std::max(sets, S.front(c, true).n);
            }
            std::printf("SRCH %d %u fuel %llu nodes %d offers %d tiles %d priced %d queries %d boundstop %d sharestop %d capped %d len %d cast %c mates %d read %llu grow %llu price %llu act %llu foes %d units %d rm %x sets %d leaves %d left %llu mode %c rows %d pend %d dropped %d reprice %d flee %d cut %d\n",
                        world.round, static_cast<unsigned>(world.me().handle), static_cast<unsigned long long>(used), S.nodes, S.offers, nt,
                        priced, queries, bound_stops, share_stops, capped ? 1 : 0, seq.n, cast, S.n_mates,
                        static_cast<unsigned long long>(first ? P.read_fuel : 0), static_cast<unsigned long long>(first ? P.grow_fuel : 0),
                        static_cast<unsigned long long>(fuel_start - marks[2]), static_cast<unsigned long long>(marks[2] - marks[3]), S.foes, S.n,
                        rm, sets, S.n_leaves, static_cast<unsigned long long>(start), mode, queries, S.n_pend, S.pend_dropped, first ? 0 : 1,
                        flee ? 1 : 0, S.flee_cut);
        });
    }
    return out;
}

} // namespace

[[gnu::flatten]] Prepared* prepare_strikes(const World& world, Pathing& pathing, Safety& safety, const Intent& intent) {
    Phase phase{"prepare_strikes"};
    auto& P = prepared_slot;
    if constexpr (debug_search) {
        debug_block({ P.fuel_start = fuel(); });
    }
    P.intent = intent;
    P.generation = safety.generation();
    const auto& record = my_record();
    P.state = record.state;
    P.pos = {record.x, record.y};
    P.health = record.health;
    P.prices = 0;
    P.valued = false;
    P.guard_asked = P.guard_true = 0;
    P.guard_asks = 0;
    auto* S = new (P.storage) Search(world, safety, pathing, P.intent);
    P.live = true;
    Phase step{"read"};
    P.ok = S->read();
    std::uint64_t read_end = 0;
    if constexpr (debug_search) {
        debug_block({ read_end = fuel(), P.read_fuel = P.fuel_start - read_end, P.grow_fuel = 0; });
    }
    if (P.ok) {
        step.next("grow");
        S->grow(S->root());
        if constexpr (debug_search) {
            debug_block({ P.grow_fuel = read_end - fuel(); });
        }
    }
    return &P;
}

bool prepared_current(const Prepared& prepared, const Safety& safety) {
    if (!prepared.live || prepared.generation != safety.generation()) return false;
    const auto& record = my_record();
    return record.state == prepared.state && record.x == prepared.pos.x && record.y == prepared.pos.y && record.health == prepared.health;
}

Planned price_strikes(Prepared& prepared, const Intent& intent) {
    Phase phase{"price_strikes"};
    if (!prepared.live) return {};
    auto& S = prepared.search();
    // Resumed after running out of fuel: the round's own turn plays next (World::throw_if_stale).
    S.world.throw_if_stale();
    if (!prepared_current(prepared, S.safety)) {
        debug_block({
            std::printf("SRCH-STALE %d %s %u\n", S.world.round, prepared.generation != S.safety.generation() ? "generation" : "state",
                        static_cast<unsigned>(S.world.me().handle));
        });
        return {};
    }
    ++prepared.prices;
    if (!prepared.ok) {
        // Nothing to strike: another walk goal would find nothing either.
        Planned out;
        out.goal_free = true;
        return out;
    }
    return price(prepared, intent);
}

Planned plan_strikes(const World& world, Pathing& pathing, Safety& safety, const Intent& intent) {
    return price_strikes(*prepare_strikes(world, pathing, safety, intent), intent);
}

bool casts_searched(const World& world) { return valued.round == world.round && valued.at == my_position(); }

namespace {

// The valued cast; false, to value the turn afresh, if a Ren's retaliation has cost us health since
// (the search's Ren bans assumed the health it read), or its target or any enemy its area counted
// died since (the turn's attacks run after the valuing).
bool cast_valued(const World& world) {
    bool cast = false;
    const bool unhurt = my_health() >= valued.health;
    try {
        const auto ability = cambc::self().abilities()[valued.slot];
        if (unhurt && valued.target >= 0) {
            const auto c = world.enemies[static_cast<std::size_t>(valued.target)].live();
            cast = c.is_alive() && c.is_visible() && ability.use(c);
        } else if (unhurt) {
            bool live = valued.foes != 0;
            for (std::uint32_t m = valued.foes; m && live; m &= m - 1)
                live = world.enemies[static_cast<std::size_t>(std::countr_zero(m))].live().is_alive();
            cast = live && ability.use(valued.ground);
        }
    } catch (const cambc::error&) {
    }
    debug_block({
        std::printf("CAST-VALUED %d %u slot %d target %d tile %d,%d ok %d\n", world.round, static_cast<unsigned>(world.me().handle),
                    valued.slot, valued.target, valued.ground.x, valued.ground.y, cast ? 1 : 0);
    });
    return cast;
}

} // namespace

[[gnu::flatten]] void strike_after(const World& world, Pathing& pathing, Safety& safety) {
    Phase phase{"strike_after"};
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
    // Live: the reset above may have spent the cast.
    if (!my_can_cast()) return;
    // The search's cast for a walk the goal did not take, or one a walk allows.
    const vec2 here = my_position();
    if (valued.round == world.round && valued.at == here) {
        if (valued.any && !cast_valued(world)) {
            valued.round = -1; // spent: cast_at_enemies values the turn as it now stands
            cast_at_enemies(world, pathing);
        }
        return;
    }
    if (here == world.me().pos) return;
    bool walk_allows = false;
    for (int s = 0; s < 2; ++s)
        walk_allows |= f.abilities[s].hits_enemies() && !f.abilities[s].excludes_walking && world.me().ability_ready(s, world.round);
    if (walk_allows) cast_at_enemies(world, pathing);
}

[[gnu::flatten]] bool strike_enemy(const World& world) {
    Phase phase{"strike_enemy"};
    if (!world.me().alive || !my_can_attack()) return false;
    Board b;
    const auto& f = world.me().facts();
    if (!read_board(world, b, f.attack_range() + (f.passive == Passive::splash_attack ? 1 : 0))) return false;
    return attack(b, best_hit(b, b.healths()));
}

} // namespace aph
