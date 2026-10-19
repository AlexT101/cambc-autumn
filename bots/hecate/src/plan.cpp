#include "plan.h"
#include <algorithm>
#include <cstdio>
#include <array>
#include <optional>
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
constexpr bool debug_plan = false; // a PLAN line per planned turn

struct Foe {
    const ChampionBelief* belief;
    vec2 pos;
    float health, retaliation, partner, bag;
    bool spawn, hold;
};

using Healths = std::array<float, max_foes>;

// The turn's state, read once.
struct Board {
    std::array<Foe, max_foes> foes;
    int n = 0;
    vec2 here;
    float strength = 0, health = 0;
    int range = 1;
    bool melee = true, splash = false;
    bool move = false, attack = false, cast = false;
    int reset = -1, dash = -1, shield = -1; // ready slots

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

int strike_reach(const ChampionFacts& f, bool dash) {
    return f.attack_range() + 1 + (dash ? dash_steps : 0) + (f.passive == Passive::splash_attack ? 1 : 0);
}

// `live`: health read from the engine, after our own hits this turn; else this turn's beliefs.
bool read_board(const World& world, const ChampionBelief* hold, Board& b, int reach, bool live) {
    auto& me = cambc::self();
    const auto& f = world.me().facts();
    b.here = me.position();
    b.range = f.attack_range();
    b.melee = f.walk_and_attack_independent();
    b.splash = f.passive == Passive::splash_attack;
    const auto& enemy_spawn = world.map().enemy_spawn;
    b.n = 0;
    for (const auto& e : world.enemies) {
        if (b.n == max_foes) break;
        if (!e.alive || !e.visible || e.stats_round != world.round || dist(b.here, e.pos) > reach) continue;
        float health = e.health;
        if (live) {
            try {
                const auto c = e.live();
                if (!c.is_alive()) continue;
                health = c.health();
            } catch (const cambc::error&) {
                continue;
            }
        }
        float partner = 1e9f;
        if (e.facts().passive == Passive::linked_pair)
            for (const auto& o : world.enemies)
                if (&o != &e && o.alive && o.visible && o.facts().passive == Passive::linked_pair) partner = o.health;
        b.foes[b.n++] = {&e, e.pos, health, e.retaliation(), partner,
                         params::gem_value * static_cast<float>(pair_gems(world, e)), enemy_spawn.is_set(e.pos), &e == hold};
    }
    if (b.n == 0) return false;
    const auto state = me.state();
    b.move = state.contains(cambc::champion_state::can_move);
    b.attack = state.contains(cambc::champion_state::can_attack);
    b.cast = state.contains(cambc::champion_state::can_cast);
    b.strength = me.strength();
    b.health = me.health();
    b.reset = b.cast ? ready_slot(world, AbilityKind::attack_reset) : -1;
    b.dash = b.cast ? ready_slot(world, AbilityKind::dash) : -1;
    b.shield = b.cast ? ready_slot(world, AbilityKind::shield) : -1;
    return true;
}

// A kill takes the bag; other damage on its spawn heals at its turn end.
float hit_worth(const Foe& f, float damage, float health) {
    if (health <= 0) return 0;
    if (damage >= health - 0.01f) return health + params::life_value + f.bag;
    if (f.spawn) return 0;
    return useful_damage(damage, health, f.partner);
}

struct Hit {
    float value = 0;
    int target = -1;
};

// The basic attack from p worth most, never one whose retaliation would kill us.
// `only`: that enemy alone.
Hit best_hit(const Board& b, vec2 p, const Healths& h, int only = -1) {
    Hit best;
    float best_health = 0;
    for (int i = 0; i < b.n; ++i) {
        if (only >= 0 && i != only) continue;
        const auto& f = b.foes[i];
        if (h[i] <= 0 || dist(p, f.pos) > b.range) continue;
        if (f.hold && b.strength < h[i] - 0.01f) continue;
        float value = hit_worth(f, b.strength, h[i]), retaliation = f.retaliation;
        if (b.splash)
            for (int j = 0; j < b.n; ++j)
                if (j != i && h[j] > 0 && dist(b.foes[j].pos, f.pos) <= 1)
                    value += hit_worth(b.foes[j], b.strength, h[j]), retaliation += b.foes[j].retaliation;
        if (retaliation >= b.health) continue;
        value -= retaliation;
        if (value <= 0) continue;
        if (best.target < 0 || value > best.value || (value == best.value && h[i] < best_health))
            best = {value, i}, best_health = h[i];
    }
    return best;
}

void apply(const Board& b, const Hit& hit, Healths& h) {
    if (hit.target < 0) return;
    const vec2 at = b.foes[hit.target].pos;
    for (int j = 0; j < b.n; ++j)
        if (j == hit.target || (b.splash && h[j] > 0 && dist(b.foes[j].pos, at) <= 1)) h[j] -= b.strength;
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

bool dash_to(int slot, Pathing& pathing, vec2 p) {
    try {
        if (!cambc::self().abilities()[slot].use(p)) return false;
    } catch (const cambc::error&) {
        return false;
    }
    pathing.invalidate();
    return true;
}

// The shield cast left for the turn's end, over its duration, capped by what could hit us at p.
float shield_worth(const World& world, Safety& safety, const Board& b, vec2 p) {
    if (b.shield < 0) return 0;
    const auto& a = world.me().facts().abilities[b.shield];
    float amount = 0;
    try {
        amount = cambc::self().abilities()[b.shield].shield_amount();
    } catch (const cambc::error&) {
        return 0;
    }
    return std::min(amount, static_cast<float>(a.duration) * safety.damage_bound(p));
}

// The enemy cast valued this turn and where from: cast_chosen() still holds it unless cast.
struct Valued {
    int round = -1;
    vec2 at{-1, -1};
    bool any = false;
} valued;

enum class Kind { stay, walk, dash, dash_walk };

struct Plan {
    Kind kind = Kind::stay;
    float value = 0;
    vec2 dash{-1, -1}, walk{-1, -1};
    bool attack_first = false; // melee: attack from where we stand before moving
    bool reset = false;
    bool enemy_cast = false;
};

} // namespace

bool strike_possible(const World& world) {
    const auto& self = world.me();
    if (!self.alive) return false;
    const vec2 here = cambc::self().position();
    return enemy_within(world, here, std::max(ability_range + 1, strike_reach(self.facts(), self.facts().has_dash())));
}

Planned plan_strikes(const World& world, Pathing& pathing, Safety& safety, const Intent& intent, const ChampionBelief* hold) {
    Planned out;
    Board b;
    const auto& f = world.me().facts();
    if (!read_board(world, hold, b, std::max(ability_range + 1, strike_reach(f, f.has_dash())), false)) return out;
    const bool walks = intent.walks && b.move;
    const float step = intent.step_value;
    const Healths h0 = b.healths();

    // Staying: an attack from here, then the cast; the goal walks after unless the attack (ranged)
    // or an excludes-walking cast spent the walk.
    const Hit first = b.attack ? best_hit(b, b.here, h0) : Hit{};
    Healths h1 = h0;
    apply(b, first, h1);
    const bool ranged_attack = !b.melee && first.target >= 0;
    const float walk_after = walks && !ranged_attack ? step : 0.0f;
    const float shield = shield_worth(world, safety, b, b.here);
    Plan best{Kind::stay, first.value + walk_after + shield};
    if (first.target >= 0 && b.reset >= 0)
        if (const Hit second = best_hit(b, b.here, h1); second.target >= 0 && first.value + second.value + walk_after > best.value)
            best = {Kind::stay, first.value + second.value + walk_after, {}, {}, false, true};
    if (b.cast) {
        bool exclusive = false;
        const float cast = enemy_cast_value(world, intent.keep_walk, hold, exclusive);
        valued = {world.round, b.here, cast > 0};
        if (cast > 0) {
            const float walk = exclusive && !intent.keep_walk ? 0.0f : walk_after;
            if (const float v = first.value + cast - cast_cost + walk; v > best.value)
                best = {Kind::stay, v, {}, {}, false, false, true};
        }
    }

    const float stay_value = best.value;
    // Moving to strike: a walk, a dash or both, scored against staying. Candidates are listed by
    // their hits and the most progress their move could make, then priced best first (walkable,
    // the steps saved, the danger there) while one could still win: the danger can fall by at
    // most ours here.
    if (intent.anchored) b.move = false, b.dash = -1;
    struct Candidate {
        Plan plan;
        vec2 end;
        float bound;
    };
    // The few with the highest bounds, highest first.
    std::array<Candidate, 3> candidates;
    int count = 0;
    // `value`: all but the steps saved and the danger; `steps`: the most the move could save.
    const auto offer = [&](Plan plan, float value, int steps, vec2 end) {
        const float bound = value + static_cast<float>(steps) * step;
        constexpr int keep = static_cast<int>(candidates.size());
        if (bound <= best.value || (count == keep && bound <= candidates[keep - 1].bound)) return;
        int i = count < keep ? count++ : keep - 1;
        for (; i > 0 && candidates[i - 1].bound < bound; --i) candidates[i] = candidates[i - 1];
        plan.value = value;
        candidates[i] = {plan, end, bound};
    };
    int nearest = 1 << 20;
    for (int i = 0; i < b.n; ++i) nearest = std::min(nearest, dist(b.here, b.foes[i].pos));
    // Without splash a hit's worth does not depend on where it is struck from: priced once per
    // enemy and spread over the tiles within 3 of us that reach it.
    std::array<float, max_foes> worth{};
    // A move earns at most the best hit it brings into range, its steps and, for Varg, the
    // shield; each kind is listed only if that can beat staying.
    float walk_most = 0, dash_most = 0;
    const int dash_reach = b.range + dash_steps + (b.melee && b.move ? 1 : 0);
    for (int i = 0; i < b.n; ++i) {
        const int d = dist(b.here, b.foes[i].pos);
        if (d > dash_reach && d > b.range + 1) continue;
        worth[i] = best_hit(b, b.foes[i].pos, h0, i).value;
        const float w = std::max(0.0f, worth[i]);
        if (d <= b.range + 1) walk_most = b.splash ? walk_most + w : std::max(walk_most, w);
        if (d <= dash_reach) dash_most = std::max(dash_most, w);
    }
    const float shield_most = b.shield >= 0 ? 1e6f : 0.0f; // not bounded cheaply
    const bool try_walk = b.move && b.attack && nearest <= b.range + 1
                          && std::max(walk_most + shield_most, first.value + walk_most) + step > best.value;
    const float dash_cost = dash_steps * step;
    const bool try_dash = b.dash >= 0 && b.attack && nearest <= dash_reach
                          && std::max(dash_most, first.value) + (dash_steps + 2) * step - dash_cost > best.value;
    const auto local = [&](vec2 p) { return (p.y - b.here.y + 3) * 7 + (p.x - b.here.x + 3); };
    std::array<Hit, 49> tile_hit{};
    std::array<vec2, 49> struck; // the tiles tile_hit reaches, in marking order
    int n_struck = 0;
    if (!b.splash && (try_walk || try_dash))
        for (int i = 0; i < b.n; ++i) {
            const float w = worth[i];
            if (w <= 0) continue;
            for (int y = std::max(b.foes[i].pos.y - b.range, b.here.y - 3); y <= std::min(b.foes[i].pos.y + b.range, b.here.y + 3); ++y)
                for (int x = std::max(b.foes[i].pos.x - b.range, b.here.x - 3); x <= std::min(b.foes[i].pos.x + b.range, b.here.x + 3); ++x) {
                    auto& t = tile_hit[local({x, y})];
                    if (t.target < 0) struck[n_struck++] = {x, y};
                    if (t.target < 0 || w > t.value || (w == t.value && h0[i] < h0[t.target])) t = {w, i};
                }
        }
    const auto hit_at = [&](vec2 p) { return b.splash ? best_hit(b, p, h0) : tile_hit[local(p)]; };
    if (try_walk) {
        // The reset's second hit after a walk, from each neighbour, marked enemy first as above.
        std::array<Hit, 9> again{};
        const bool resets = b.melee && first.target >= 0 && b.reset >= 0;
        if (resets && !b.splash)
            for (int i = 0; i < b.n; ++i) {
                if (dist(b.here, b.foes[i].pos) > b.range + 1) continue;
                const float w = best_hit(b, b.foes[i].pos, h1, i).value;
                if (w <= 0) continue;
                for (int k = 0; k < 9; ++k) {
                    const vec2 n{b.here.x + k % 3 - 1, b.here.y + k / 3 - 1};
                    auto& t = again[k];
                    if (dist(n, b.foes[i].pos) <= b.range && (t.target < 0 || w > t.value || (w == t.value && h1[i] < h1[t.target])))
                        t = {w, i};
                }
            }
        for (auto d : directions) {
            const vec2 n = b.here + d;
            const Hit there = hit_at(n);
            if (b.melee) {
                // Either attack here then the reset there, or the one attack there.
                if (there.target >= 0 && there.value > first.value)
                    offer({Kind::walk, 0, {}, n, false, false, false}, there.value + shield, 1, n);
                if (resets)
                    if (const Hit second = b.splash ? best_hit(b, n, h1) : again[(d.y + 1) * 3 + d.x + 1]; second.target >= 0)
                        offer({Kind::walk, 0, {}, n, true, true, false}, first.value + second.value, 1, n);
            } else if (b.reset >= 0 && there.target >= 0) {
                // A ranged walk spends the attack; the reset restores it.
                offer({Kind::walk, 0, {}, n, false, true, false}, there.value, 1, n);
            }
        }
    }
    // The dash's cooldown would otherwise carry us two steps.
    std::optional<Tiles<5 * 5>> landings;
    if (try_dash) {
        const float walk_on = b.melee && walks ? step : 0.0f;
        // Splash (Varg) has no dash: every tile here is one tile_hit reaches.
        for (int k = 0; k < n_struck; ++k) {
            const vec2 p = struck[k];
            const int d = dist(p, b.here);
            if (d < 1) continue;
            const Hit there = hit_at(p);
            if (d <= dash_steps) {
                if (there.target < 0) continue;
                const bool before = b.melee && first.value > there.value;
                offer({Kind::dash, 0, p, {}, before, false, false}, (before ? first : there).value + walk_on - dash_cost, d, p);
            } else if (b.melee && b.move && there.target >= 0) {
                // Dash, then walk into range: the landing is found when priced.
                offer({Kind::dash_walk, 0, {}, p, false, false, false}, there.value - dash_cost, d, p);
            }
        }
    }

    if (count > 0) {
        const auto& blocked = pathing.blocked();
        const bitboard* guard = pathing.guard();
        const auto walkable = [&](vec2 p) { return in_bounds(p) && !blocked.is_set(p) && !(guard && guard->is_set(p)); };
        const int here_steps = intent.field ? intent.field->at(b.here) : static_cast<int>(unreachable);
        const auto gain_to = [&](vec2 p) {
            if (here_steps == unreachable) return 0.0f;
            const int c = intent.field->at(p);
            return c == unreachable ? 0.0f : static_cast<float>(here_steps - c) * step;
        };
        // Expected damage as Safety prices it, from the camps and the enemies we see near us: the
        // unseen differ little over three tiles.
        struct Striker {
            vec2 pos;
            const Strike* strike;
        };
        std::array<Striker, 16> strikers;
        int ns = 0;
        for (const auto& e : world.enemies)
            if (ns < 16 && e.alive && e.visible && dist(b.here, e.pos) <= Strike::max_reach + 3)
                if (const auto& st = safety.strike_of(e); st.reach >= 0) strikers[ns++] = {e.pos, &st};
        std::array<Safety::CampHit, 24> camps;
        int nc = 0;
        for (const auto& m : safety.awake_members())
            if (nc < 24 && dist(b.here, m.pos) <= m.reach + 3) camps[nc++] = m;
        const auto expected = [&](vec2 p) {
            float total = 0;
            for (int k = 0; k < nc; ++k)
                if (dist(p, camps[k].pos) <= camps[k].reach) total += camps[k].strength * camps[k].weight;
            for (int k = 0; k < ns; ++k) total += safety_params::hit_given_reach * strikers[k].strike->at(dist(p, strikers[k].pos));
            return total;
        };
        const float here_danger = expected(b.here);
        for (int i = 0; i < count && candidates[i].bound + here_danger > best.value; ++i) {
            auto plan = candidates[i].plan;
            const vec2 p = candidates[i].end;
            if (plan.kind == Kind::dash) {
                if (!landings) landings.emplace(pathing.dash_landings());
                if (std::find(landings->begin(), landings->end(), p) == landings->end()) continue;
            } else {
                if (!walkable(p)) continue;
                if (plan.kind == Kind::dash_walk) {
                    if (!landings) landings.emplace(pathing.dash_landings());
                    const vec2* from = std::find_if(landings->begin(), landings->end(), [&](vec2 l) { return dist(l, p) <= 1; });
                    if (from == landings->end()) continue;
                    plan.dash = *from;
                }
            }
            if (const float v = plan.value + gain_to(p) - (expected(p) - here_danger); v > best.value) {
                best = plan;
                best.value = v;
            }
        }
    }

    if constexpr (debug_plan) {
        debug_block({
            std::printf("PLAN %d %u k%d v%.0f s%.0f w%d,%d d%d,%d f%d r%d c%d n%d step%.0f walks%d field%d\n", world.round,
                        static_cast<std::uint32_t>(world.me().handle), static_cast<int>(best.kind), best.value, stay_value,
                        best.walk.x, best.walk.y, best.dash.x, best.dash.y, best.attack_first, best.reset, best.enemy_cast, b.n,
                        step, walks, intent.field != nullptr);
        });
    }
    // Carry it out; a move refused (a hidden unit) falls back to striking from here.
    Healths h = h0;
    const auto strike_here = [&](bool reset) {
        const Hit a = b.attack ? best_hit(b, cambc::self().position(), h) : Hit{};
        if (attack(b, a)) {
            out.attacked = true;
            apply(b, a, h);
            if (reset && b.reset >= 0) {
                const Hit again = best_hit(b, cambc::self().position(), h);
                if (again.target >= 0 && use_slot(b.reset) && attack(b, again)) apply(b, again, h);
            }
        }
    };
    switch (best.kind) {
    case Kind::stay:
        strike_here(best.reset);
        // Our attack may have killed its target.
        if (best.enemy_cast && !cast_chosen()) cast_at_enemies(world, intent.keep_walk, hold);
        break;
    case Kind::walk:
        if (best.attack_first) strike_here(false);
        if (pathing.try_move(best.walk)) {
            out.moved = true;
            if (out.attacked) {
                const Hit again = best_hit(b, best.walk, h);
                if (again.target >= 0 && use_slot(b.reset) && attack(b, again)) apply(b, again, h);
            } else if (b.melee) {
                strike_here(false);
            } else if (use_slot(b.reset)) {
                strike_here(false);
            }
        } else if (!best.attack_first) {
            strike_here(false);
        }
        break;
    case Kind::dash:
        if (best.attack_first) strike_here(false);
        dash_to(b.dash, pathing, best.dash);
        if (!out.attacked) strike_here(false);
        break;
    case Kind::dash_walk:
        if (dash_to(b.dash, pathing, best.dash) && pathing.try_move(best.walk)) out.moved = true;
        strike_here(false);
        break;
    }
    if (!b.melee && out.attacked) out.moved = true;
    return out;
}

void strike_after(const World& world, Safety& safety, const ChampionBelief* hold) {
    if (!world.me().alive || world.is_stale()) return;
    auto& me = cambc::self();
    const auto state = me.state();
    if (state.contains(cambc::champion_state::submitting_gems) || state.contains(cambc::champion_state::recalling)
        || state.contains(cambc::champion_state::teleporting))
        return;
    if (!state.contains(cambc::champion_state::can_attack) && !state.contains(cambc::champion_state::can_cast)) return;
    Board b;
    const auto& f = world.me().facts();
    if (read_board(world, hold, b, f.attack_range() + (f.passive == Passive::splash_attack ? 1 : 0), true)) {
        Healths h = b.healths();
        bool attacked = !b.attack;
        if (b.attack) {
            const Hit a = best_hit(b, b.here, h);
            attacked = attack(b, a);
            apply(b, a, h);
        }
        if (attacked && b.reset >= 0) {
            const Hit again = best_hit(b, b.here, h);
            if (again.target >= 0 && again.value > shield_worth(world, safety, b, b.here) && use_slot(b.reset)) attack(b, again);
        }
    }
    if (!state.contains(cambc::champion_state::can_cast)) return;
    // A cast the plan kept for a walk the goal did not take, or one a walk allows.
    const vec2 here = cambc::self().position();
    if (valued.round == world.round && valued.at == here) {
        if (valued.any) cast_chosen();
        return;
    }
    if (here == world.me().pos) return;
    bool walk_allows = false;
    for (int s = 0; s < 2; ++s)
        walk_allows |= f.abilities[s].hits_enemies() && !f.abilities[s].excludes_walking && world.me().ability_ready(s, world.round);
    if (walk_allows) cast_at_enemies(world, false, hold);
}

bool strike_enemy(const World& world, const ChampionBelief* hold) {
    if (!world.me().alive || !cambc::self().can_attack()) return false;
    Board b;
    const auto& f = world.me().facts();
    if (!read_board(world, hold, b, f.attack_range() + (f.passive == Passive::splash_attack ? 1 : 0), true)) return false;
    return attack(b, best_hit(b, b.here, b.healths()));
}

bool reset_may_kill(const World& world) {
    const auto& self = world.me();
    const auto& f = self.facts();
    const int slot = f.slot_of(AbilityKind::attack_reset);
    if (slot < 0 || !self.ability_ready(slot, world.round)) return false;
    const int reach = f.attack_range() + (f.walk_and_attack_independent() ? 1 : 0);
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && dist(self.pos, e.pos) <= reach && e.health <= 2 * self.strength) return true;
    return false;
}

} // namespace aph
