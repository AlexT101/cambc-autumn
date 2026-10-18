#include "micro.h"
#include <algorithm>
#include <array>
#include <cstdlib>
#include <exception>
#include "bands.h"
#include "kit.h"
#include "linefight.h"
#include "pathing.h"
#include "safety.h"
#include "world.h"

namespace aph::micro {

namespace {
using AK = cambc::ability_kind;
constexpr int kVision = 8;

int manh(vec2 a, vec2 b) { return std::abs(a.x - b.x) + std::abs(a.y - b.y); }
cambc::champion live(const ChampionBelief& b) { return cambc::detail::handle_access::make_champion(b.handle); }
vec2 my_pos() { return cambc::self().position(); }
const hyp::Kit& kit_of(const ChampionBelief& b) { return hyp::facts::kit(b.type); }

// ---- Geometry ---------------------------------------------------------------------------------------------------

// Straight-line sight within vision (walls and bushes in between block it) -- Helios's routine.
bool line_of_sight(const World& world, vec2 a, vec2 b) {
    if (dist(a, b) > kVision) return false;
    const auto& blocks = world.map().walls_and_bushes;
    int x = a.x, y = a.y;
    const int dx = std::abs(b.x - a.x), dy = -std::abs(b.y - a.y);
    const int sx = a.x < b.x ? 1 : -1, sy = a.y < b.y ? 1 : -1;
    int err = dx + dy;
    while (true) {
        if (x == b.x && y == b.y) return true;
        const int e2 = 2 * err;
        if (e2 >= dy) err += dy, x += sx;
        if (e2 <= dx) err += dx, y += sy;
        if (x == b.x && y == b.y) return true;
        if (blocks.is_set(vec2{x, y})) return false;
    }
}

// Walking distance over terrain (walls, holes, altars), from a field rooted at `to` (kept for the turn; a few roots).
struct WalkField {
    vec2 root{-1, -1};
    int round = -1;
    cambc::distance_field f;
    bitboard visited;
};
std::array<WalkField, 4> walks;
int walk_next = 0;
int walk(const World& world, vec2 from, vec2 to) {
    auto value = [&](const WalkField& w) { return w.visited.is_set(from) ? static_cast<int>(w.f.get(from)) : static_cast<int>(unreachable); };
    for (auto& w : walks)
        if (w.round == world.round && w.root == to) return value(w);
    WalkField& w = walks[static_cast<std::size_t>(walk_next++ & 3)];
    w.round = world.round;
    w.root = to;
    bitboard root;
    root.set(to);
    w.f.compute(world.map().impassable, root, w.visited, 16);
    return value(w);
}

// My legal one-step destinations; out[0] = staying.
int my_moves(Pathing& pathing, vec2* out) {
    const vec2 me = my_pos();
    int n = 0;
    out[n++] = me;
    if (!cambc::self().can_move()) return n;
    const auto& blocked = pathing.blocked();
    for (const vec2 d : directions) {
        const vec2 p{me.x + d.x, me.y + d.y};
        if (p.x < 0 || p.y < 0 || p.x >= cambc::map::width() || p.y >= cambc::map::height()) continue;
        if (blocked.is_set(p)) continue;
        out[n++] = p;
    }
    return n;
}

bool step_to(Pathing& pathing, vec2 t) { return !(t == my_pos()) && pathing.try_move(t); }

// The point a fight keeps away from: the nearest OTHER visible enemy, else their spawn.
vec2 danger_ref(const World& world, const ChampionBelief& target) {
    const vec2 me = my_pos();
    vec2 best = world.map().enemy_spawn_centre;
    int bd = 1 << 20;
    for (const auto& e : world.enemies)
        if (&e != &target && e.alive && e.visible && dist(e.pos, me) < bd) bd = dist(e.pos, me), best = e.pos;
    return best;
}

// Of my moves, the one within `rng` of `epos` farthest from `ref` (ties: staying, then move order); -1 if none.
int best_in_range(const vec2* c, int n, vec2 epos, int rng, vec2 ref) {
    int best = -1, bd = -1;
    for (int i = 0; i < n; ++i)
        if (dist(c[i], epos) <= rng && dist(c[i], ref) > bd) best = i, bd = dist(c[i], ref);
    return best;
}

// Of my moves, the one walking closest to `epos` (ties: farther from `ref`).
int closest_move(const World& world, const vec2* c, int n, vec2 epos, vec2 ref) {
    int best = 0, bw = 1 << 20, br = -1;
    for (int i = 0; i < n; ++i) {
        const int w = walk(world, c[i], epos), r = dist(c[i], ref);
        if (w < bw || (w == bw && r > br)) best = i, bw = w, br = r;
    }
    return best;
}

int enemy_range(const ChampionBelief& e) { return kit_of(e).attack_range; }

// ---- Abilities --------------------------------------------------------------------------------------------------

bool cast_free() { return cambc::self().can_cast(); }

// Our own cooldowns are exact at turn start (the belief); one cast a turn.
bool slot_ready(const World& world, int s) {
    if (s < 0 || !cast_free()) return false;
    const auto& me = world.me();
    if (!me.ability_ready(s, world.round) && kit_of(me).passive != cambc::passive_type::reset_cooldowns_on_kill) return false;
    try {
        return cambc::self().abilities()[static_cast<std::size_t>(s)].cooldown() == 0;
    } catch (const std::exception&) {
        return false;
    }
}

int dash_slot(const World& world) { return kit_of(world.me()).slot(AK::dash); }
bool dash_ready(const World& world) { return slot_ready(world, dash_slot(world)); }

enum class Role { stun, damage };

// A ready slot of this role that reaches `e` now (not walk-exclusive once we walked).
int usable_slot(const World& world, const ChampionBelief& e, Role role, bool walked) {
    const hyp::Kit& k = kit_of(world.me());
    const int d = dist(my_pos(), e.pos);
    for (int s = 0; s < 2; ++s) {
        const hyp::Ability& a = k.ab[static_cast<std::size_t>(s)];
        if (!a.present || (walked && a.excludes_walking) || !slot_ready(world, s)) continue;
        if (role == Role::stun
            && (!a.stuns() || a.kind == AK::attack_reset || kit_of(e).passive == cambc::passive_type::stun_immunity))
            continue;
        if (role == Role::damage && (!a.damages() || a.stuns())) continue;   // stuns go in their own role
        if (d > a.reach() || !a.hits_champions()) continue;
        return s;
    }
    return -1;
}

bool walk_compatible(const World& world, int s) { return s >= 0 && !kit_of(world.me()).ab[static_cast<std::size_t>(s)].excludes_walking; }
bool deals_damage(const World& world, int s) { return s >= 0 && kit_of(world.me()).ab[static_cast<std::size_t>(s)].damages(); }

bool cast_at(const World& world, int s, const ChampionBelief& e) {
    if (s < 0) return false;
    const hyp::Ability& a = kit_of(world.me()).ab[static_cast<std::size_t>(s)];
    try {
        const auto ab = cambc::self().abilities()[static_cast<std::size_t>(s)];
        if (a.is_ground()) {
            // The area's centre within cast range, covering them: on them, or the tile toward them at the range.
            const vec2 me = my_pos();
            vec2 t = e.pos;
            const int range = static_cast<int>(a.range);
            if (dist(me, t) > range) t = {me.x + std::clamp(e.pos.x - me.x, -range, range), me.y + std::clamp(e.pos.y - me.y, -range, range)};
            return ab.use(t);
        }
        return ab.use(live(e));
    } catch (const std::exception&) {
        return false;
    }
}

bool attack(const World& world, const ChampionBelief& e) {
    auto& self = cambc::self();
    if (!self.can_attack() || dist(my_pos(), e.pos) > kit_of(world.me()).attack_range) return false;
    try {
        self.attack(live(e));
        return true;
    } catch (const std::exception&) {
        return false;
    }
}

void reset_and_attack(const World& world, const ChampionBelief& e) {
    const int s = kit_of(world.me()).slot(AK::attack_reset);
    if (s < 0 || cambc::self().can_attack() || !slot_ready(world, s)) return;
    try {
        if (cambc::self().abilities()[static_cast<std::size_t>(s)].use()) attack(world, e);
    } catch (const std::exception&) {
    }
}

void shield_if_hit_next_turn(const World& world, Safety& safety) {
    const int s = kit_of(world.me()).slot(AK::shield);
    if (s < 0 || !slot_ready(world, s) || !safety.enemy_area().is_set(my_pos())) return;
    try {
        cambc::self().abilities()[static_cast<std::size_t>(s)].use();
    } catch (const std::exception&) {
    }
}

// ---- Dashes -----------------------------------------------------------------------------------------------------

int landings(const World& world, Pathing& pathing, vec2* out, int cap) {
    if (dash_slot(world) < 0) return 0;
    const bitboard land = pathing.dash_landings();
    const auto& blocked = pathing.blocked();
    int n = 0;
    for (const vec2 p : Tiles<32>(land)) {
        if (blocked.is_set(p)) continue;
        if (n < cap) out[n++] = p;
    }
    return n;
}

bool do_dash(const World& world, Pathing& pathing, vec2 land) {
    try {
        if (cambc::self().abilities()[static_cast<std::size_t>(dash_slot(world))].use(land)) {
            pathing.invalidate();
            return true;
        }
    } catch (const std::exception&) {
    }
    return false;
}

// Melee: dash, then (if needed) one step, ending within `rng` of `epos` -- the end tile farthest from `ref`.
bool dash_move_into_range(const World& world, Pathing& pathing, vec2 epos, int rng, vec2 ref) {
    vec2 land[32];
    const int nl = landings(world, pathing, land, 32);
    int li = -1, best_end = -1;
    for (int i = 0; i < nl; ++i) {
        int end = -1;
        if (dist(land[i], epos) <= rng) end = dist(land[i], ref);
        else if (dist(land[i], epos) <= rng + 1) end = dist(land[i], ref) - 1;   // a step still needed
        if (end > best_end) li = i, best_end = end;
    }
    if (li < 0 || !do_dash(world, pathing, land[li])) return false;
    if (dist(my_pos(), epos) > rng) {
        vec2 c[9];
        const int n = my_moves(pathing, c);
        const int bi = best_in_range(c, n, epos, rng, ref);
        if (bi >= 0) step_to(pathing, c[bi]);
    }
    return true;
}

// Dash to the landing they must walk to the farthest (ties: farthest from `ref`).
bool dash_away(const World& world, Pathing& pathing, vec2 from, vec2 ref) {
    vec2 land[32];
    const int nl = landings(world, pathing, land, 32);
    int li = -1, bw = walk(world, my_pos(), from), br = -1;
    for (int i = 0; i < nl; ++i) {
        const int w = walk(world, land[i], from), r = dist(land[i], ref);
        if (w > bw || (w == bw && li >= 0 && r > br)) li = i, bw = w, br = r;
    }
    return li >= 0 && do_dash(world, pathing, land[li]);
}

// ---- Cast orders (the user's) ------------------------------------------------------------------------------------

void melee_casts(const World& world, Safety& safety, const ChampionBelief& e, bool walked, bool vs_melee) {
    shield_if_hit_next_turn(world, safety);
    if (cast_free() && !vs_melee) cast_at(world, usable_slot(world, e, Role::stun, walked), e);
    if (cast_free()) cast_at(world, usable_slot(world, e, Role::damage, walked), e);
    if (attack(world, e) && cast_free()) reset_and_attack(world, e);
    if (cast_free() && vs_melee) cast_at(world, usable_slot(world, e, Role::stun, walked), e);
}

void ranged_casts(const World& world, Safety& safety, const ChampionBelief& e) {
    shield_if_hit_next_turn(world, safety);
    if (cast_free()) cast_at(world, usable_slot(world, e, Role::stun, false), e);
    if (cast_free()) cast_at(world, usable_slot(world, e, Role::damage, false), e);
    if (attack(world, e) && cast_free()) reset_and_attack(world, e);
}

void confirm_kill(const World& world, const ChampionBelief& e) {
    if (bands::saved() && double_kills(world, e)) bands::use_double();
}

// A turn to give: FIRST now and FIRST planned next -- going LAST banks a double turn.
void give_turn() {
    if (bands::now() == bands::Band::first && bands::request() >= 0) bands::forfeit();
}

// ---- Matchups ---------------------------------------------------------------------------------------------------

void melee_vs_melee(const World& world, Pathing& pathing, Safety& safety, const ChampionBelief& e) {
    vec2 c[9];
    const int n = my_moves(pathing, c);
    const vec2 epos = e.pos, ref = danger_ref(world, e);
    const int rng = kit_of(world.me()).attack_range;
    bool walked = false;
    const int bi = best_in_range(c, n, epos, rng, ref);
    if (bi >= 0) {
        walked = step_to(pathing, c[bi]);
    } else if (dash_ready(world) && dash_move_into_range(world, pathing, epos, rng, ref)) {
        walked = true;
    } else {
        // Hold where their walking distance to us is > 2 (they can't move + attack us): seeing them, then the
        // closest (chebyshev, then manhattan). None that far: the farthest.
        int best = 0;
        std::array<int, 4> bkey{-1, 0, 0, 0};
        for (int i = 0; i < n; ++i) {
            const int w = walk(world, c[i], epos);
            const std::array<int, 4> key{w > 2 ? 1 : 0, w > 2 ? (line_of_sight(world, c[i], epos) ? 1 : 0) : w, -dist(c[i], epos), -manh(c[i], epos)};
            if (key > bkey) best = i, bkey = key;
        }
        walked = step_to(pathing, c[best]);
        give_turn();
    }
    melee_casts(world, safety, e, walked, true);
    confirm_kill(world, e);
}

void melee_vs_ranged(const World& world, Pathing& pathing, Safety& safety, const ChampionBelief& e) {
    give_turn();
    vec2 c[9];
    const int n = my_moves(pathing, c);
    const vec2 epos = e.pos, ref = danger_ref(world, e);
    const int rng = kit_of(world.me()).attack_range;
    bool walked = false;
    const bool dash_ok = dash_ready(world);
    const int d = dist(my_pos(), epos);
    const int bi = best_in_range(c, n, epos, rng, ref);
    if (bi >= 0) {
        walked = step_to(pathing, c[bi]);
    } else if (dash_ok && dash_move_into_range(world, pathing, epos, rng, ref)) {
        walked = true;
    } else if (bands::saved() && (d - rng <= 2 || (dash_ok && d - rng <= 4))) {
        // A double move reaches them: this turn (the dash +) a step toward them, the next turn finishes.
        bands::use_double();
        if (dash_ok && d - rng > 2) {
            vec2 land[32];
            const int nl = landings(world, pathing, land, 32);
            int li = -1, lw = 1 << 20;
            for (int i = 0; i < nl; ++i)
                if (walk(world, land[i], epos) < lw) li = i, lw = walk(world, land[i], epos);
            if (li >= 0) do_dash(world, pathing, land[li]);
        }
        vec2 c2[9];
        const int n2 = my_moves(pathing, c2);
        walked = step_to(pathing, c2[closest_move(world, c2, n2, epos, ref)]);
    } else {
        // A stun that reaches them, always; then walk toward them (unless the stun excluded it).
        const int s = usable_slot(world, e, Role::stun, false);
        const bool stunned = s >= 0 && cast_at(world, s, e);
        if (!stunned || walk_compatible(world, s)) walked = step_to(pathing, c[closest_move(world, c, n, epos, ref)]);
    }
    melee_casts(world, safety, e, walked, false);
    confirm_kill(world, e);
}

void ranged_vs_melee(const World& world, Pathing& pathing, Safety& safety, const ChampionBelief& e) {
    const int rng = kit_of(world.me()).attack_range;
    if (dist(my_pos(), e.pos) > rng) {
        vec2 c[9];
        const int n = my_moves(pathing, c);
        step_to(pathing, c[closest_move(world, c, n, e.pos, danger_ref(world, e))]);
        shield_if_hit_next_turn(world, safety);
        if (cast_free()) cast_at(world, usable_slot(world, e, Role::stun, true), e);
        if (cast_free()) cast_at(world, usable_slot(world, e, Role::damage, true), e);
        return;
    }
    ranged_casts(world, safety, e);
    if (cast_free() && dash_ready(world) && walk(world, my_pos(), e.pos) <= enemy_range(e) + 1)
        dash_away(world, pathing, e.pos, danger_ref(world, e));
    confirm_kill(world, e);
}

void ranged_vs_ranged(const World& world, Pathing& pathing, Safety& safety, const ChampionBelief& e) {
    const int rng = kit_of(world.me()).attack_range;
    const int d = dist(my_pos(), e.pos);
    if (d <= rng) {
        ranged_casts(world, safety, e);
        confirm_kill(world, e);
        return;
    }
    const vec2 ref = danger_ref(world, e);
    if (dash_ready(world)) {   // dash into range (the landing farthest from them, then from `ref`), then attack
        vec2 land[32];
        const int nl = landings(world, pathing, land, 32);
        int li = -1, k1 = -1, k2 = -1;
        for (int i = 0; i < nl; ++i) {
            const int a = dist(land[i], e.pos);
            if (a > rng) continue;
            if (a > k1 || (a == k1 && dist(land[i], ref) > k2)) li = i, k1 = a, k2 = dist(land[i], ref);
        }
        if (li >= 0 && do_dash(world, pathing, land[li])) {
            if (attack(world, e) && cast_free()) reset_and_attack(world, e);
            confirm_kill(world, e);
            return;
        }
    }
    // Walk toward them, never into their range: the move closest to them outside it; none outside: the farthest.
    vec2 c[9];
    const int n = my_moves(pathing, c);
    const int their = enemy_range(e);
    int best = 0;
    std::array<int, 3> bkey{-1, 0, 0};
    for (int i = 0; i < n; ++i) {
        const int k = dist(c[i], e.pos);
        const std::array<int, 3> key{k > their ? 1 : 0, k > their ? -k : k, -manh(c[i], e.pos)};
        if (key > bkey) best = i, bkey = key;
    }
    step_to(pathing, c[best]);
    confirm_kill(world, e);
}
} // namespace

bool double_kills(const World& world, const ChampionBelief& e) {
    const auto& me = world.me();
    const hyp::Kit& k = kit_of(me);
    const int d = dist(my_pos(), e.pos);
    if (d > k.attack_range + (k.ranged() ? 0 : 1)) return false;   // must hit without them moving
    float dmg = me.strength;
    float best = 0;
    for (int s = 0; s < 2; ++s) {
        const hyp::Ability& a = k.ab[static_cast<std::size_t>(s)];
        if (!a.present || !me.ability_ready(s, world.round + 1)) continue;
        if (a.is(AK::attack_reset)) best = std::max(best, me.strength);
        else if (a.damages() && d <= a.reach()) best = std::max(best, a.modifier * me.focus);
    }
    dmg += best;
    float hp = e.health;   // after this turn's hits: read live
    cambc::detail::champion_info ci{};
    if (cambc::detail::sdk_champion(static_cast<std::uint32_t>(e.handle), &ci) == 0) hp = ci.health;
    return hp > 0 && dmg >= hp + line::shield_of(e);
}

namespace {
constexpr double kChannel = 95, kKill = 85, kFight = 72, kRetreat = 70;

int max_chase(const hyp::Kit& k) {
    if (k.has(AK::dash)) return 6;
    if (k.passive == cambc::passive_type::splash_attack) return 3;
    return 4;
}

// The linked pair (Cassi / Issac) fights only with a margin while it carries gems.
double min_margin(const World& world) {
    return kit_of(world.me()).linked() && cambc::self().gem_count() >= 30 ? 0.3 : 0.0;
}

bool fight_is_ours(const World& world, const line::Outcome& f) {
    return f.any_enemy && f.we_win && !f.i_die && f.margin >= min_margin(world);
}

// Our burst now: a basic attack plus the best ready ability (one cast a turn) -- against their hp + shield.
bool burst_kills(const World& world, const ChampionBelief& e) {
    const auto& me = world.me();
    const hyp::Kit& k = kit_of(me);
    float extra = 0;
    for (int s = 0; s < 2; ++s) {
        const hyp::Ability& a = k.ab[static_cast<std::size_t>(s)];
        if (!a.present || !me.ability_ready(s, world.round)) continue;
        if (a.is(AK::attack_reset)) extra = std::max(extra, me.strength);
        else if (a.damages() && a.hits_champions()) extra = std::max(extra, a.modifier * me.focus);
    }
    return e.health + line::shield_of(e) <= me.strength + extra;
}

// Ranged: standing still `rounds` rounds keeps us above 20% hp against everything that can reach us.
bool hold_survives(const World& world, Safety& safety, int rounds) {
    const auto& me = cambc::self();
    (void)world;
    return safety.damage_bound(me.position()) * static_cast<float>(rounds) < me.health() - 0.2f * me.max_health();
}

// The ladder's fight where we stand: the turn's one sim (line::at).
const line::Outcome& ladder_fight(const World& world, Safety& safety) { return line::at(world, safety, my_pos()); }
} // namespace

// Every tile within `r` of `p` lies in `zone` (Aph's covered()).
bool covered(const bitboard& zone, vec2 p, int r) {
    static bitboard outside{cambc::uninitialized};
    outside.clear();
    outside.draw_chebyshev(p, static_cast<float>(r));
    outside |= zone;
    outside ^= zone;
    return outside.is_empty();
}

Choice choose(const World& world, Safety& safety, const bitboard* zone) {
    Choice best;
    const auto& me = world.me();
    if (!me.alive) return best;
    const hyp::Kit& k = kit_of(me);
    const vec2 here = my_pos();
    const int rng = k.attack_range;
    const bool dash = k.has(AK::dash) && me.ability_ready(k.slot(AK::dash), world.round);
    const bool stun = k.has_stun();
    int spell = -1;
    for (int s = 0; s < 2; ++s)
        if (k.ab[static_cast<std::size_t>(s)].damages() && k.ab[static_cast<std::size_t>(s)].hits_champions()) spell = s;
    const bool spell_ready = spell >= 0 && me.ability_ready(spell, world.round);

    bool any = false;
    for (const auto& e : world.enemies) any |= e.alive && e.visible && dist(e.pos, here) <= 10;
    if (!any) return best;
    // The line model runs only once a target is within reach (lossless: the verdict matters only then, and for the
    // retreat below, which needs a credible enemy hitting our tile).
    const auto fight_here = [&]() -> const line::Outcome& { return ladder_fight(world, safety); };

    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible) continue;
        const int d = dist(here, e.pos);
        if (zone && covered(*zone, e.pos, rng)) continue;   // every tile in reach of it would make us retreat (Aph)
        // An enemy on (or next to) its own spawn heals there: only a kill now.
        const bool home = world.map().near_enemy_spawn.is_set(e.pos);
        const bool channel = e.channel != Channel::none;
        double sc = 0;
        if (!k.ranged()) {
            if (d > max_chase(k)) continue;
            const bool kill = burst_kills(world, e) && d <= rng + 1 + (dash ? 2 : 0);
            if (home && !kill) continue;
            const bool survive = !fight_here().i_die, ours = fight_is_ours(world, fight_here());
            if (channel && survive && d <= rng + (dash ? 3 : 1) + (stun ? 4 : 0)) sc = kChannel;
            else if (kill && survive) sc = kKill;
            else if (ours) sc = kFight;
        } else {
            const bool reach = d <= rng || (spell_ready && d <= 4);
            const bool e_ranged = kit_of(e).ranged();
            if (!reach && !(e_ranged ? ((dash && d <= rng + 2) || d <= kit_of(e).attack_range + 3) : d <= rng + 3)) continue;
            const bool kill = reach && burst_kills(world, e);
            if (home && !kill) continue;
            const bool survive = !fight_here().i_die, ours = fight_is_ours(world, fight_here());
            if (reach && channel && survive && hold_survives(world, safety, 1)) sc = kChannel;
            else if (kill && survive) sc = kKill;
            else if (ours && hold_survives(world, safety, 2)) sc = kFight;
        }
        if (sc <= 0) continue;
        const int gems = static_cast<int>(e.gems), best_gems = best.target ? static_cast<int>(best.target->gems) : -1;
        if (sc > best.score || (sc == best.score && best.target && (gems > best_gems || (gems == best_gems && e.health < best.target->health)))) {
            best.score = sc;
            best.target = &e;
            best.mode = Mode::fight;
        }
    }
    if (!best.target && safety.enemy_area().is_set(here) && !fight_is_ours(world, fight_here())) {
        best.mode = Mode::retreat;
        best.score = kRetreat;
    }
    return best;
}

const ChampionBelief* chaser(const World& world) {
    const ChampionBelief* best = nullptr;
    int cd = 1 << 20;
    const vec2 me = my_pos();
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible) continue;
        const int d = dist(me, e.pos);
        if (d <= enemy_range(e) + 1 && d < cd) best = &e, cd = d;
    }
    return best;
}

void engage(const World& world, Pathing& pathing, Safety& safety, const ChampionBelief& e) {
    const bool me_melee = !kit_of(world.me()).ranged(), them_melee = !kit_of(e).ranged();
    if (me_melee && them_melee) melee_vs_melee(world, pathing, safety, e);
    else if (me_melee) melee_vs_ranged(world, pathing, safety, e);
    else if (them_melee) ranged_vs_melee(world, pathing, safety, e);
    else ranged_vs_ranged(world, pathing, safety, e);
}

void retreat(const World& world, Pathing& pathing, Safety& safety) {
    const ChampionBelief* c = chaser(world);   // the nearest enemy that can hit us next turn
    bool exclusive_stun = false;
    if (c) {
        if (dash_ready(world)) dash_away(world, pathing, c->pos, danger_ref(world, *c));
        if (cast_free()) {   // a stun only when we can still walk, or it does damage too (user)
            const int s = usable_slot(world, *c, Role::stun, false);
            if (s >= 0 && (walk_compatible(world, s) || deals_damage(world, s)) && cast_at(world, s, *c))
                exclusive_stun = !walk_compatible(world, s);
        }
    }
    shield_if_hit_next_turn(world, safety);
    if (!exclusive_stun && cambc::self().can_move()) {
        // Flee: the neighbour out of enemy reach (then the least camp damage), nearest home.
        vec2 m[9];
        const int n = my_moves(pathing, m);
        const auto& home = pathing.to_ally_spawn();
        const auto& reach = safety.enemy_area();
        int best = 0;
        std::array<int, 3> bkey{-1, 0, 0};
        for (int i = 0; i < n; ++i) {
            const std::array<int, 3> key{reach.is_set(m[i]) ? 0 : 1, -static_cast<int>(safety.camp_damage(m[i])), -home.at(m[i])};
            if (key > bkey) best = i, bkey = key;
        }
        step_to(pathing, m[best]);
    }
    if (bands::saved() && safety.enemy_area().is_set(my_pos())) bands::use_double();
}

} // namespace aph::micro
