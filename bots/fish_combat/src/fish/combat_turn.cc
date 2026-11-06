// Intercontinental Fish's behaviour around and against enemies: see combat_turn.h. Thresholds are
// FISH_MODEL's fitted ones (tools/fish/combat_rules.py); kills, danger and acceptable tiles are
// fish_math's D-based definitions, so a "kill" is Fish's estimate, not the engine's damage.
#include "../bot_parts.h"
#include "combat_turn.h"
#include "fish_math.h"
#include "switches.h"

namespace aph {

namespace {

namespace fishc {

constexpr float progress_health = 0.5f;   // 9: the route keeps closing on an enemy iff h > 0.5
constexpr int camp_hold_distance = 4;     // 9: keeps hitting camps iff the nearest enemy is beyond 4
constexpr float chase_target_health = 0.37f, chase_ratio = 1.24f, chase_health = 0.44f; // 10.3
constexpr float gem_offset = 8;           // 10.4: unit damage target argmax (gems + 8) / EHP
constexpr float ward_rate_contact = 0.080f, ward_rate_enemy = 0.050f, ward_rate_none = 0.029f; // 12

// A candidate end tile, judged from the turn-start view (combat_tiles.py tile_features).
struct Tile {
    vec2 p{-1, -1};
    int dmin = 99;   // to the nearest visible enemy
    int dmelee = 99; // to the nearest visible melee enemy
    float danger = 0;
    bool kill = false, bush = false;
    int home = unreachable;
};

struct Tiles9 {
    std::array<Tile, 9> t;
    int n = 0;
};

bool is_melee(const ChampionBelief& e) { return !e.facts().ranged; }

// Visible enemies as the turn started (beliefs; nothing moves during our turn but what we kill).
template <class F> void each_enemy(const World& world, F f) {
    for (const auto& e : world.enemies)
        if (e.alive && e.visible) f(e);
}

int nearest(const World& world, vec2 p, bool melee_only = false) {
    int d = 99;
    each_enemy(world, [&](const ChampionBelief& e) {
        if (!melee_only || is_melee(e)) d = std::min(d, dist(p, e.pos));
    });
    return d;
}

float my_ehp(const World& world) { return std::max(1.0f, fish::ehp(world.me())); }

Tile judge(const World& world, vec2 start, vec2 p) {
    Tile t;
    t.p = p;
    t.dmin = nearest(world, p);
    t.dmelee = nearest(world, p, true);
    t.danger = fish::danger(world, p, my_ehp(world));
    t.kill = fish::kill_available(world, start, p);
    t.bush = test(world.map().bushes, p);
    t.home = world.map().from_ally_spawn().at(p);
    return t;
}

// The start tile and its free neighbours (walls, holes, altars, the enemy spawn, visible units and
// live camps block); with `only`, those on it (a capture's tiles).
Tiles9 candidates(const World& world, Pathing& pathing, vec2 start, const bitboard* only) {
    Tiles9 out;
    out.t[out.n++] = judge(world, start, start);
    if (!my_can_move()) return out;
    const auto& blocked = pathing.blocked();
    const auto& open = world.map().open_for_us;
    for (const auto d : directions) {
        const vec2 p = start + d;
        if (!in_bounds(p) || !test(open, p) || test(blocked, p) || (only && !test(*only, p))) continue;
        out.t[out.n++] = judge(world, start, p);
    }
    return out;
}

bool acceptable(const World& world, const Tile& t) {
    return t.kill || (fish::health_fraction(world.me()) > fish::accept_health && t.danger <= fish::accept_danger);
}

// Ties among equally good tiles: the bush (section 12), then homeward, then compass order.
bool tie_better(const Tile& a, const Tile& b) {
    if (a.bush != b.bush) return a.bush;
    return a.home < b.home;
}

// --- live reads of what we act on ---

struct Foe {
    cambc::handle_champion_t h{};
    const ChampionBelief* b = nullptr;
    vec2 pos{-1, -1};
    float hp = 0, ehp = 0, strength = 0;
};

// The visible enemy champions within r of `here`, read live: a hit changes health and a kill removes one.
int foes_within(const World& world, vec2 here, int r, std::array<Foe, 16>& out) {
    int n = 0;
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible || dist(here, e.pos) > r || n >= static_cast<int>(out.size())) continue;
        const auto* rec = visible_record(e.handle);
        if (!rec) continue;
        const vec2 p{rec->x, rec->y};
        if (dist(here, p) > r) continue;
        Foe f;
        f.h = e.handle, f.b = &e, f.pos = p, f.hp = rec->health, f.strength = rec->strength;
        f.ehp = rec->health + (e.facts().has(AbilityKind::shield) ? shield_value(e.handle) : 0.0f);
        out[n++] = f;
    }
    return n;
}

std::uint32_t id_of(const Foe& f) { return static_cast<std::uint32_t>(f.h); }

// The basic attack's target: argmin (EHP, id) over visible enemies in range; Ren is left when its
// retaliation would kill us.
std::optional<cambc::handle_champion_t> basic_target(const World& world) {
    const vec2 here = my_position();
    const int range = world.me().facts().attack_range();
    std::array<Foe, 16> fs;
    const int n = foes_within(world, here, range, fs);
    const float guard = my_health_and_shield(world);
    const Foe* best = nullptr;
    for (int i = 0; i < n; ++i) {
        const auto& f = fs[i];
        if (f.b->facts().passive == Passive::retaliation && retaliation_share * f.b->focus * world.me().taken >= guard) continue;
        if (!best || f.ehp < best->ehp || (f.ehp == best->ehp && id_of(f) < id_of(*best))) best = &f;
    }
    if (!best) return std::nullopt;
    return best->h;
}

bool attack(cambc::handle_champion_t t) {
    if (!my_can_attack()) return false;
    try {
        attack_champion(t);
        return true;
    } catch (const cambc::error&) {
        return false;
    }
}

bool attack_basic(const World& world, std::optional<cambc::handle_champion_t>* first = nullptr) {
    if (!my_can_attack()) return false;
    const auto t = basic_target(world);
    if (!t || !attack(*t)) return false;
    if (first) *first = t;
    return true;
}

bool slot_ready_now(int slot) { return slot >= 0 && my_can_cast() && my_cooldown(slot) == 0; }

// The reset and a second basic: on the first target for Marcella's stunning reset (10.4), else
// the basic rule's. Fails, spending nothing, while the attack is unspent or no enemy is in range.
bool reset_attack(const World& world, std::optional<cambc::handle_champion_t> first) {
    const auto& f = world.me().facts();
    const int slot = f.slot_of(AbilityKind::attack_reset);
    if (!slot_ready_now(slot) || my_can_attack()) return false;
    std::optional<cambc::handle_champion_t> t;
    if (first && f.abilities[slot].stuns) {
        if (const auto* rec = visible_record(*first); rec && dist(my_position(), {rec->x, rec->y}) <= f.attack_range()) t = first;
    }
    if (!t) t = basic_target(world);
    if (!t) return false;
    try {
        if (!cast_slot(slot)) return false;
    } catch (const cambc::error&) {
        return false;
    }
    return attack(*t);
}

// Basic, then the reset's second basic on a survivor: melee hits whenever walking allows; a ranged
// basic spends the walk, so only on a tile we keep.
bool hit_and_reset(const World& world) {
    std::optional<cambc::handle_champion_t> first;
    bool hit = attack_basic(world, &first);
    hit |= reset_attack(world, first);
    return hit;
}

// Unit damage spell target: argmax (gems + 8) / EHP within 4, lower id on ties.
std::optional<cambc::handle_champion_t> spell_target(const World& world) {
    std::array<Foe, 16> fs;
    const int n = foes_within(world, my_position(), ability_range, fs);
    const Foe* best = nullptr;
    float best_score = -1;
    for (int i = 0; i < n; ++i) {
        const float s = (static_cast<float>(fs[i].b->gems) + gem_offset) / std::max(1.0f, fs[i].ehp);
        if (s > best_score || (s == best_score && best && id_of(fs[i]) < id_of(*best))) best = &fs[i], best_score = s;
    }
    if (!best) return std::nullopt;
    return best->h;
}

// Cassi's stun: argmax (Strength, then lower id) within 4, Marcella and those already stunned for
// their next turn left out.
std::optional<cambc::handle_champion_t> stun_target(const World& world) {
    std::array<Foe, 16> fs;
    const int n = foes_within(world, my_position(), ability_range, fs);
    const Foe* best = nullptr;
    for (int i = 0; i < n; ++i) {
        const auto& f = fs[i];
        if (f.b->facts().passive == Passive::stun_immune || stun_pending(f.h)) continue;
        if (!best || f.strength > best->strength || (f.strength == best->strength && id_of(f) < id_of(*best))) best = &f;
    }
    if (!best) return std::nullopt;
    return best->h;
}

// The exclusive damage spells a standing champion casts: unit damage first (Prism's slot 0 before
// its ground spell, 10.5), -1 if none is ready.
int ready_damage_slot(const World& world, bool* ground = nullptr) {
    const auto& f = world.me().facts();
    int pick = -1;
    for (int s = 0; s < 2; ++s) {
        const auto& a = f.abilities[s];
        if (a.kind != AbilityKind::damage || !slot_ready_now(s)) continue;
        if (pick < 0 || (a.target == Targeting::unit && f.abilities[pick].target != Targeting::unit)) pick = s;
    }
    if (ground) *ground = pick >= 0 && f.abilities[pick].target == Targeting::ground;
    return pick;
}

// Prism's ground centre: the tile within 4 with the most visible enemies within 1, camps ignored.
std::optional<vec2> ground_centre(const World& world) {
    const vec2 here = my_position();
    std::array<Foe, 16> fs;
    const int n = foes_within(world, here, ability_range + ground_radius, fs);
    if (n == 0) return std::nullopt;
    int best = 0;
    vec2 at{-1, -1};
    for (int dy = -ability_range; dy <= ability_range; ++dy)
        for (int dx = -ability_range; dx <= ability_range; ++dx) {
            const vec2 c{here.x + dx, here.y + dy};
            if (!in_bounds(c)) continue;
            int k = 0;
            for (int i = 0; i < n; ++i) k += dist(c, fs[i].pos) <= ground_radius;
            if (k > best) best = k, at = c;
        }
    if (best == 0) return std::nullopt;
    return at;
}

// A standing champion's exclusive damage spell; false if none is ready or nothing is in reach.
bool cast_damage(const World& world) {
    if (turn_acts.walked) return false;
    bool ground = false;
    const int slot = ready_damage_slot(world, &ground);
    if (slot < 0) return false;
    try {
        if (ground) {
            const auto c = ground_centre(world);
            return c && cast_slot(slot, *c);
        }
        const auto t = spell_target(world);
        return t && cast_slot_on(slot, *t);
    } catch (const cambc::error&) {
        return false;
    }
}

// Cassi's stun (a pure stun, walking allowed): whenever her damage spell cools down or she walked.
bool cassi_stun(const World& world) {
    const auto& f = world.me().facts();
    const int slot = f.slot_of(AbilityKind::stun);
    if (!slot_ready_now(slot)) return false;
    const int damage = f.slot_of(AbilityKind::damage);
    if (damage >= 0 && my_cooldown(damage) == 0 && !turn_acts.walked) return false;
    const auto t = stun_target(world);
    if (!t) return false;
    try {
        return cast_slot_on(slot, *t);
    } catch (const cambc::error&) {
        return false;
    }
}

bool walk_to(Pathing& pathing, vec2 p) { return p == my_position() || pathing.try_move(p); }

// --- dashes ---

// A dash kill (10.2): the nearest enemy is beyond walk-and-hit reach but inside dash reach (melee
// at 3-4, a ranged dasher at 4-5, Heart of Ruin at 2-3), and a landing gives a kill by D (a basic's
// Strength within reach, Heart of Ruin's 1.5 x Focus plus a basic within 1 of the landing).
// Heart of Ruin lands where the most visible enemies are within 1; the rest at least danger.
bool dash_kill(const World& world, Pathing& pathing) {
    const auto& me = world.me();
    const auto& f = me.facts();
    const int slot = f.slot_of(AbilityKind::dash);
    if (!slot_ready_now(slot)) return false;
    const bool lands = f.abilities[slot].lands();
    const vec2 here = my_position();
    const int d0 = nearest(world, here);
    const int walkhit = f.ranged ? ranged_range : melee_range + 1;
    const int lo = lands ? 2 : walkhit + 1, hi = lands ? 3 : walkhit + dash_range;
    if (d0 < lo || d0 > hi) return false;
    const float scale = damage_scale(f.passive, me.health, me.max_health);
    const float blow = (me.strength + (lands ? f.abilities[slot].multiplier * me.focus : 0.0f)) * scale;
    // A melee landing may still walk a step before its attack ("dash, walk, attack").
    const int reach = lands ? f.abilities[slot].radius : f.ranged ? ranged_range : melee_range + 1;
    const auto& landings = pathing.dash_landings();
    const float own = my_ehp(world);
    vec2 best{-1, -1};
    int best_n = -1;
    float best_danger = 0;
    Tile best_t;
    for (const auto p : positions_within(landings, here, dash_range)) {
        if (lands && landing_wakes(world, p, f.abilities[slot].radius)) continue;
        bool kill = false;
        int n = 0;
        each_enemy(world, [&](const ChampionBelief& e) {
            const int d = dist(p, e.pos);
            if (d <= reach && blow >= fish::ehp(e)) kill = true;
            if (lands && d <= f.abilities[slot].radius) ++n;
        });
        if (!kill) continue;
        const float danger = fish::danger(world, p, own);
        Tile t;
        t.p = p, t.bush = test(world.map().bushes, p), t.home = world.map().from_ally_spawn().at(p);
        const bool better = best.x < 0 || (lands && n != best_n ? n > best_n
                                           : danger != best_danger ? danger < best_danger
                                                                   : tie_better(t, best_t));
        if (better) best = p, best_n = n, best_danger = danger, best_t = t;
    }
    if (best.x < 0) return false;
    try {
        if (!cast_slot(slot, best)) return false;
    } catch (const cambc::error&) {
        return false;
    }
    pathing.invalidate();
    if (lands)
        each_enemy(world, [&](const ChampionBelief& e) {
            if (dist(best, e.pos) <= f.abilities[slot].radius) note_engaged(static_cast<std::uint32_t>(e.handle));
        });
    // A melee landing two from its prey closes the last step.
    if (!f.ranged && !lands && my_can_move() && nearest(world, my_position()) > melee_range) {
        vec2 step{-1, -1};
        int sd = 99;
        for (const auto d : directions) {
            const vec2 q = my_position() + d;
            if (!in_bounds(q) || !test(world.map().open_for_us, q) || test(pathing.blocked(), q)) continue;
            if (const int k = nearest(world, q); k < sd) sd = k, step = q;
        }
        if (step.x >= 0 && sd <= melee_range) pathing.try_move(step);
    }
    hit_and_reset(world);
    return true;
}

// Heart of Ruin's landing when engaging (walk, dash, attack): onto the free landing with the most
// visible enemies within 1, of the acceptable ones, least danger and the bush then breaking ties.
bool hor_landing(const World& world, Pathing& pathing) {
    const auto& me = world.me();
    const auto& f = me.facts();
    const int slot = f.slot_of(AbilityKind::dash);
    if (slot < 0 || !f.abilities[slot].lands() || !slot_ready_now(slot)) return false;
    const int radius = f.abilities[slot].radius;
    const vec2 here = my_position();
    const float own = my_ehp(world);
    const bool healthy = fish::health_fraction(me) > fish::accept_health;
    vec2 best{-1, -1};
    int best_n = 0;
    float best_danger = 0;
    Tile best_t;
    for (const auto p : positions_within(pathing.dash_landings(), here, dash_range)) {
        int n = 0;
        each_enemy(world, [&](const ChampionBelief& e) { n += dist(p, e.pos) <= radius; });
        if (n == 0 || landing_wakes(world, p, radius)) continue;
        const float danger = fish::danger(world, p, own);
        if (!fish::kill_available(world, here, p) && !(healthy && danger <= fish::accept_danger)) continue;
        Tile t;
        t.p = p, t.bush = test(world.map().bushes, p), t.home = world.map().from_ally_spawn().at(p);
        const bool better = best.x < 0 || (n != best_n ? n > best_n : danger != best_danger ? danger < best_danger : tie_better(t, best_t));
        if (better) best = p, best_n = n, best_danger = danger, best_t = t;
    }
    if (best.x < 0) return false;
    try {
        if (!cast_slot(slot, best)) return false;
    } catch (const cambc::error&) {
        return false;
    }
    pathing.invalidate();
    each_enemy(world, [&](const ChampionBelief& e) {
        if (dist(best, e.pos) <= radius) note_engaged(static_cast<std::uint32_t>(e.handle));
    });
    return true;
}

// --- positioning ---

enum class Ctx { none, m2, m1, r };

// combat_rules.py contexts(): m2 melee two from the nearest enemy, engage tiles adjacent; m1
// melee adjacent with a tile farther, engage tiles adjacent; r ranged within 3 with a tile
// farther, the engage tile staying put.
Ctx context(const World& world, const Tiles9& c) {
    const auto& st = c.t[0];
    const bool ranged = world.me().facts().ranged;
    bool farther = false, adjacent = false;
    for (int i = 0; i < c.n; ++i) farther |= c.t[i].dmin > st.dmin, adjacent |= c.t[i].dmin == 1;
    if (!ranged && st.dmin == 2) return adjacent ? Ctx::m2 : Ctx::none;
    if (!ranged && st.dmin == 1) return farther ? Ctx::m1 : Ctx::none;
    if (ranged && st.dmin <= ranged_range) return farther ? Ctx::r : Ctx::none;
    return Ctx::none;
}

// A decline's end tile (10.8): the farther tiles; a ranged champion with a melee enemy within 2
// first those 3 or more from every melee enemy, then the farthest from them (capped at 3); then the
// least danger, the bush, home. The start tile if none is farther.
const Tile& decline_tile(const World& world, const Tiles9& c) {
    const auto& st = c.t[0];
    const bool kite = world.me().facts().ranged && st.dmelee <= 2;
    const Tile* best = &st;
    for (int i = 1; i < c.n; ++i) {
        const auto& t = c.t[i];
        if (t.dmin <= st.dmin) continue;
        if (best == &st) {
            best = &t;
            continue;
        }
        if (kite) {
            const bool a = t.dmelee >= 3, b = best->dmelee >= 3;
            if (a != b) {
                if (a) best = &t;
                continue;
            }
            const int ma = std::min(t.dmelee, 3), mb = std::min(best->dmelee, 3);
            if (ma != mb) {
                if (ma > mb) best = &t;
                continue;
            }
        }
        if (t.danger != best->danger) {
            if (t.danger < best->danger) best = &t;
            continue;
        }
        // Retreats go homeward (91%) and don't seek bushes.
        if (t.home != best->home ? t.home < best->home : tie_better(t, *best)) best = &t;
    }
    return *best;
}

// m2's engage tile: adjacent to the weakest enemy an engage tile reaches (the basic rule seen
// through the end tile), among the acceptable ones the least danger, then the bush.
const Tile* engage_tile(const World& world, const Tiles9& c) {
    const ChampionBelief* weakest = nullptr;
    each_enemy(world, [&](const ChampionBelief& e) {
        bool reach = false;
        for (int i = 0; i < c.n && !reach; ++i) reach = c.t[i].dmin == 1 && dist(c.t[i].p, e.pos) <= 1;
        if (!reach) return;
        if (!weakest || fish::ehp(e) < fish::ehp(*weakest) || (fish::ehp(e) == fish::ehp(*weakest) && static_cast<std::uint32_t>(e.handle) < static_cast<std::uint32_t>(weakest->handle))) weakest = &e;
    });
    const Tile* best = nullptr;
    for (int i = 0; i < c.n; ++i) {
        const auto& t = c.t[i];
        if (t.dmin != 1 || !acceptable(world, t)) continue;
        if (!best) {
            best = &t;
            continue;
        }
        const bool a = weakest && dist(t.p, weakest->pos) <= 1, b = weakest && dist(best->p, weakest->pos) <= 1;
        if (a != b) {
            if (a) best = &t;
            continue;
        }
        if (t.danger != best->danger) {
            if (t.danger < best->danger) best = &t;
            continue;
        }
        if (tie_better(t, *best)) best = &t;
    }
    return best;
}

// The chase rule (10.3): last turn's target, now the nearest visible enemy and out of basic range,
// is chased iff it is at or below 0.37 of its health, or our side's EHP within 8 outweighs theirs
// 1.24 times and our gem health is above 0.44.
const ChampionBelief* chase_target(const World& world, vec2 here) {
    const ChampionBelief* e0 = nullptr;
    int d0 = 99;
    each_enemy(world, [&](const ChampionBelief& e) {
        if (const int d = dist(here, e.pos); d < d0) d0 = d, e0 = &e;
    });
    if (!e0 || d0 <= world.me().facts().attack_range() || !engaged_last_turn(static_cast<std::uint32_t>(e0->handle))) return nullptr;
    const float gem_h = std::min(1.0f, fish::ehp(world.me()) / std::max(1.0f, world.me().max_health)) * (world.me().gems > 0 ? fish::gem_health_factor : 1.0f);
    const bool go = fish::health_fraction(*e0) <= chase_target_health || (fish::side_ehp_ratio(world, here) > chase_ratio && gem_h > chase_health);
    return go ? e0 : nullptr;
}

// A step closing on e: the tile nearest it, then the least danger, the bush.
bool step_at(const World& world, Pathing& pathing, const Tiles9& c, vec2 target) {
    const int d0 = dist(c.t[0].p, target);
    const Tile* best = nullptr;
    for (int i = 1; i < c.n; ++i) {
        const auto& t = c.t[i];
        const int d = dist(t.p, target);
        if (d >= d0) continue;
        if (!best || d < dist(best->p, target) || (d == dist(best->p, target) && (t.danger < best->danger || (t.danger == best->danger && tie_better(t, *best)))))
            best = &t;
    }
    return best && pathing.try_move(best->p);
}

} // namespace fishc

namespace fishc {

// m2 declined from an acceptable tile this round: the goal's steps keep off the engage tiles.
int stay_out_round = -1;

Contact contact_turn(World& world, Pathing& pathing, Safety& safety, Memory&, bool holding) {
    Contact out;
    const auto& me = world.me();
    const auto& f = me.facts();
    const vec2 start = my_position();
    if (!me.alive || start.x < 0 || !enemy_seen(world)) return out;
    const int d0 = nearest(world, start);
    if (d0 > vision_radius) return out;
    // Beyond every rule's reach (a dash's 5, a ground spell's 4 + 1) only the chase applies: it
    // needs the nearest enemy hit last turn. The tile judging below is the turn's biggest cost.
    if (d0 > 5) {
        bool chased = false;
        each_enemy(world, [&](const ChampionBelief& e) { chased |= dist(start, e.pos) == d0 && engaged_last_turn(static_cast<std::uint32_t>(e.handle)); });
        if (!chased || holding) return out;
    }
    // The fight's own steps: the goal's guard is put back after it.
    const auto held = pathing.held_guard();
    pathing.set_guard(nullptr);
    struct Restore {
        Pathing& p;
        Pathing::GuardState s;
        ~Restore() { p.restore_guard(s); }
    } restore{pathing, held};
    // Willow heals first: the rule fires on 95% of free rows with an injured ally in reach.
    if (f.heals()) heal_ally(world, safety);
    const bitboard* only = nullptr;
    if (holding) {
        if (const int g = world.map().group_at(start); g >= 0) only = &world.map().groups[g].tiles();
    }
    const auto c = candidates(world, pathing, start, only);
    const auto& st = c.t[0];
    int stage = 0;
    const auto finish = [&](bool hit) {
        out.attacked |= hit;
        if (f.has(AbilityKind::stun)) out.attacked |= cassi_stun(world);
        out.done = true;
        decision = Branch::attack;
        debug_block({
            float dm = 9;
            for (int i = 0; i < c.n; ++i) dm = std::min(dm, c.t[i].danger);
            std::printf("FC %d %u st%d d%d h%.2f n%d hit%d at%d,%d dz%.2f dmin%.2f k%d\n", world.round, my_handle(), stage, d0, fish::health_fraction(me), c.n, static_cast<int>(out.attacked), my_position().x, my_position().y, st.danger, dm, static_cast<int>(st.kill));
        });
        return out;
    };
    // A spell kill from where we stand: an exclusive damage spell's target dies to it by D.
    if (const int s = ready_damage_slot(world); s >= 0 && f.abilities[s].target == Targeting::unit) {
        bool kill = false;
        const float blow = f.abilities[s].multiplier * me.focus * damage_scale(f.passive, me.health, me.max_health);
        if (const auto t = spell_target(world))
            each_enemy(world, [&](const ChampionBelief& e) { kill |= e.handle == *t && blow >= fish::ehp(e); });
        if (kill) {
            bool hit = attack_basic(world);
            hit |= cast_damage(world);
            return finish(hit);
        }
    }
    // The kill override extended by the dash (10.2).
    if (!holding && dash_kill(world, pathing)) return finish(true);
    // Stand and cast (10.5): an exclusive damage spell ready with an enemy in reach is cast iff the
    // start tile is acceptable (a running capture stands anyway).
    {
        bool ground = false;
        const int s = ready_damage_slot(world, &ground);
        if (s >= 0 && d0 <= ability_range + (ground ? ground_radius : 0) && (acceptable(world, st) || holding)) {
            bool hit = attack_basic(world);
            hit |= cast_damage(world);
            if (!hit) hit |= reset_attack(world, std::nullopt);
            if (hit) return finish(hit);
        }
    }
    const auto ctx = context(world, c);
    stage = 10 + static_cast<int>(ctx);
    if (ctx != Ctx::none) {
        bool engage = false;
        if (ctx == Ctx::r) engage = acceptable(world, st);
        else
            for (int i = 0; i < c.n; ++i) engage |= c.t[i].dmin == 1 && acceptable(world, c.t[i]);
        stage += engage ? 100 : 0;
        bool hit = false, stay_out = false;
        switch (ctx) {
        case Ctx::m1:
            if (engage) {
                // Walk, dash, attack: Heart of Ruin's landing is its damage spell.
                if (!holding && hor_landing(world, pathing)) hit = true;
                else if (const auto* t = engage_tile(world, c)) walk_to(pathing, t->p);
                hit |= hit_and_reset(world);
            } else {
                hit |= hit_and_reset(world);
                walk_to(pathing, decline_tile(world, c).p);
            }
            break;
        case Ctx::m2:
            if (engage) {
                if (!holding && hor_landing(world, pathing)) hit = true;
                else if (const auto* t = engage_tile(world, c)) walk_to(pathing, t->p);
                hit |= hit_and_reset(world);
            } else {
                // Staying out: from an acceptable tile the goal walks, off the engage tiles.
                if (acceptable(world, st)) {
                    stay_out = true;
                    break;
                }
                walk_to(pathing, decline_tile(world, c).p);
                hit |= hit_and_reset(world);
            }
            break;
        case Ctx::r:
            if (engage) {
                hit |= hit_and_reset(world);
            } else {
                // Walk, reset, attack; standing, the plain hits.
                if (walk_to(pathing, decline_tile(world, c).p) && my_position() != start) hit |= reset_attack(world, std::nullopt);
                else hit |= hit_and_reset(world);
            }
            break;
        case Ctx::none: break;
        }
        if (!stay_out && (hit || my_position() != start)) return finish(hit);
        if (stay_out) {
            out.stay_out = true, stay_out_round = world.round;
            return out;
        }
    }
    // In basic range with nowhere farther to go: the fight is here.
    if (st.dmin <= f.attack_range())
        if (hit_and_reset(world)) return finish(true);
    // The chase (out of the contexts' reach): a step closing on last turn's target, then the hits.
    if (const auto* e = chase_target(world, start); e && !holding) {
        bool hit = false;
        if (my_can_move()) step_at(world, pathing, c, e->pos);
        hit |= f.ranged ? reset_attack(world, std::nullopt) : hit_and_reset(world);
        if (f.ranged && my_can_attack()) hit |= hit_and_reset(world);
        if (hit || my_position() != start) return finish(hit);
    }
    (void)safety;
    debug_block({ std::printf("FC %d %u free d%d h%.2f n%d\n", world.round, my_handle(), d0, fish::health_fraction(me), c.n); });
    return out;
}

bool in_contact(const World& world) {
    return world.me().alive && enemy_seen(world) && world.turn_start.x >= 0 && nearest(world, world.turn_start) <= ranged_range;
}

// Momentum (9): where we started last turn, so the step it took.
vec2 last_start{-1, -1};
int last_round = -1;

void after_goal(World& world) {
    last_start = world.turn_start, last_round = world.round;
    if (!world.me().alive || world.is_stale() || channelling() || !enemy_seen(world)) return;
    const auto& f = world.me().facts();
    if (f.heals()) heal(world);
    // A champion over a camp: a basic left unspent, or a ranged walk's reset.
    if (my_can_attack()) hit_and_reset(world);
    else if (f.ranged && turn_acts.walked) reset_attack(world, std::nullopt);
    if (f.has(AbilityKind::stun)) cassi_stun(world);
    // Standing still, a ready exclusive damage spell goes out (95%).
    if (!turn_acts.walked && my_position() == world.turn_start) cast_damage(world);
}

bool near_turn(World& world, Pathing& pathing, Safety&) {
    const auto& me = world.me();
    if (!me.alive || !my_can_move() || !enemy_seen(world)) return false;
    const vec2 start = my_position();
    const int d0 = nearest(world, start);
    if (d0 > camp_hold_distance) return false;
    const auto held = pathing.held_guard();
    pathing.set_guard(nullptr);
    struct Restore {
        Pathing& p;
        Pathing::GuardState s;
        ~Restore() { p.restore_guard(s); }
    } restore{pathing, held};
    const auto c = candidates(world, pathing, start, nullptr);
    const Tile* best = nullptr;
    if (fish::health_fraction(me) > progress_health) {
        // Momentum: close iff last turn's step, continued, would; else hold the distance.
        bool close = false;
        if (last_round == world.round - 1 && last_start.x >= 0 && last_start != start) {
            const vec2 d = start - last_start;
            const vec2 on{start.x + (d.x > 0) - (d.x < 0), start.y + (d.y > 0) - (d.y < 0)};
            close = nearest(world, on) < d0;
        }
        for (int i = close ? 1 : 0; i < c.n; ++i) {
            const auto& t = c.t[i];
            if ((close ? t.dmin >= d0 : t.dmin != d0) || !acceptable(world, t)) continue;
            if (!best || t.danger < best->danger || (t.danger == best->danger && tie_better(t, *best))) best = &t;
        }
        if (best && best->p == start) {
            decision = Branch::attack;
            after_goal(world);
            return true;
        }
    } else {
        const auto& t = decline_tile(world, c);
        if (t.p != start) best = &t;
    }
    if (!best || !pathing.try_move(best->p)) return false;
    decision = Branch::attack;
    after_goal(world);
    return true;
}

const bitboard* step_guard(const World& world, Safety&, vec2 here, int radius) {
    const auto& me = world.me();
    const bool out_of_reach = stay_out_round == world.round;
    if (!me.alive || (fish::health_fraction(me) > progress_health && !out_of_reach) || !enemy_seen(world)) return nullptr;
    const int d0 = nearest(world, here);
    if (d0 > vision_radius) return nullptr;
    static bitboard out{cambc::uninitialized};
    clear_board(out);
    bool any = false;
    for (int dy = -radius; dy <= radius; ++dy)
        for (int dx = -radius; dx <= radius; ++dx) {
            const vec2 q{here.x + dx, here.y + dy};
            if (!(dx || dy) || !in_bounds(q)) continue;
            const int d = nearest(world, q);
            if (out_of_reach ? d <= 1 : d < d0) set_tile(out, q), any = true;
        }
    return any ? &out : nullptr;
}

bool heal(const World& world) {
    const auto& f = world.me().facts();
    const int slot = f.slot_of(AbilityKind::heal);
    if (!slot_ready_now(slot)) return false;
    const vec2 here = my_position();
    const float amount = my_heal(slot);
    const ChampionBelief* best = nullptr;
    float best_score = 0;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible || dist(here, a.pos) > ability_range || a.health >= a.max_health || a.max_health <= 0) continue;
        const float s = std::min(a.max_health - a.health, amount) / a.max_health;
        if (!best || s > best_score) best = &a, best_score = s;
    }
    if (!best) return false;
    try {
        return cast_slot_on(slot, best->handle);
    } catch (const cambc::error&) {
        return false;
    }
}

bool basic_hit(const World& world) { return attack_basic(world); }

bool hor_threatened(const World& world) {
    const vec2 here = my_position();
    bool threat = false;
    each_enemy(world, [&](const ChampionBelief& e) { threat |= !e.stun_pending && fish::reach_damage(e, dist(here, e.pos), world.round) > 0; });
    return threat;
}

// A deterministic draw in [0, 1) for the ward's rate: games are deterministic anyway.
float draw(int round, std::uint32_t handle) {
    std::uint32_t x = static_cast<std::uint32_t>(round) * 0x9E3779B1u ^ (handle + 0x7F4A7C15u) * 0x85EBCA77u;
    x ^= x >> 15, x *= 0x2C1B3C6Du, x ^= x >> 12, x *= 0x297A2D39u, x ^= x >> 15;
    return static_cast<float>(x >> 8) / 16777216.0f;
}

bool place_ward(const World& world, Memory& memory) {
    if (stunned_turn || !world.me().alive || channelling() || cambc::self().ward_cooldown() > 0) return false;
    const vec2 here = my_position();
    if (here.x < 0) return false;
    const int d0 = enemy_seen(world) ? nearest(world, world.turn_start) : 99;
    const float rate = d0 <= 5 ? ward_rate_contact : d0 <= vision_radius ? ward_rate_enemy : ward_rate_none;
    if (draw(world.round, my_handle()) >= rate) return false;
    const auto& map = world.map();
    // A ward on a bush sees its own cluster, one off bushes no bush tile: only bush tiles score.
    static bitboard not_bush{cambc::uninitialized}, seen{cambc::uninitialized}, allied{cambc::uninitialized};
    static bool made = false;
    if (!made) not_into(map.bushes, not_bush), made = true;
    cambc::vision::ward_tiles_into(team::ally, allied);
    vec2 best{-1, -1};
    int best_score = 0;
    for (int dy = -2; dy <= 2; ++dy)
        for (int dx = -2; dx <= 2; ++dx) {
            const vec2 q{here.x + dx, here.y + dy};
            if (!in_bounds(q) || !test(map.bushes, q) || test(map.enemy_spawn, q)) continue;
            // A visible allied ward is an error; an unseen one fails silently, as Fish's do.
            if (test(allied, q) && test(world.visible, q)) continue;
            not_bush.reachable_tiles_into(q, 6, seen);
            drop(seen, world.visible);
            const int s = static_cast<int>(board_count(seen));
            if (s == 0) continue;
            // Ties: distance 2 first (89% of Fish's), then farther from the nearest enemy.
            const auto key = [&](vec2 p) { return dist(p, here) * 100 + (enemy_seen(world) ? std::min(nearest(world, p), 99) : 0); };
            if (s > best_score || (s == best_score && key(q) > key(best))) best = q, best_score = s;
        }
    if (best.x < 0) return false;
    throw_if_stale();
    try {
        if (!cambc::self().place_ward(best)) return false;
    } catch (const cambc::error&) {
        return false;
    }
    memory.ward = best;
    memory.bushes_watched = {-1, -1};
    return true;
}

} // namespace fishc

} // namespace

} // namespace aph
