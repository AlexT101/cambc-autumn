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
    if (slot < 0) return -1;
    if (!self.ability_ready(slot, world.round) && self.facts().passive != Passive::reset_on_kill) return -1;
    try {
        return cambc::self().abilities()[slot].cooldown() > 0 ? -1 : slot;
    } catch (const cambc::error&) {
        return -1;
    }
}

int strike_reach(const ChampionFacts& f, bool dash) {
    return f.attack_range() + 1 + (dash ? dash_steps : 0) + (f.passive == Passive::splash_attack ? 1 : 0);
}

bool read_board(const World& world, const ChampionBelief* hold, Board& b, int reach) {
    auto& me = cambc::self();
    const auto& f = world.me().facts();
    b.here = me.position();
    b.range = f.attack_range();
    b.melee = f.walk_and_attack_independent();
    b.splash = f.passive == Passive::splash_attack;
    const auto& enemy_spawn = world.map().enemy_spawn;
    b.n = 0;
    for (auto p : positions_within(live_champion_tiles(team::enemy), b.here, reach)) {
        if (b.n == max_foes) break;
        const ChampionBelief* belief = nullptr;
        for (const auto& e : world.enemies)
            if (e.alive && e.visible && e.pos == p) belief = &e;
        if (!belief) continue;
        try {
            auto c = cambc::vision::champion_at(p);
            const auto passive = belief->facts().passive;
            float partner = 1e9f;
            if (passive == Passive::linked_pair)
                for (const auto& e : world.enemies)
                    if (e.alive && e.visible && e.pos != p && e.facts().passive == Passive::linked_pair) partner = e.health;
            b.foes[b.n++] = {belief,
                             p,
                             c.health(),
                             passive == Passive::retaliation ? retaliation_share * c.focus() : 0.0f,
                             partner,
                             params::gem_value * static_cast<float>(pair_gems(world, *belief)),
                             enemy_spawn.is_set(p),
                             belief == hold};
        } catch (const cambc::error&) {
        }
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
Hit best_hit(const Board& b, vec2 p, const Healths& h) {
    Hit best;
    float best_health = 0;
    for (int i = 0; i < b.n; ++i) {
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

int progress(const Intent& intent, vec2 from, vec2 to) {
    if (intent.target.x >= 0) {
        const auto steps = [&](vec2 p) { return std::max(0, dist(p, intent.target) - intent.target_range); };
        return steps(from) - steps(to);
    }
    if (!intent.field) return 0;
    const int a = intent.field->at(from), c = intent.field->at(to);
    if (a == unreachable || c == unreachable) return 0;
    return a - c;
}

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
    if (!read_board(world, hold, b, std::max(ability_range + 1, strike_reach(f, f.has_dash())))) return out;
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
        if (cast > 0) {
            const float walk = exclusive && !intent.keep_walk ? 0.0f : walk_after;
            if (const float v = first.value + cast - cast_cost + walk; v > best.value)
                best = {Kind::stay, v, {}, {}, false, false, true};
        }
    }

    const float stay_value = best.value;
    // Moving to strike: a walk, a dash or both, scored against staying.
    std::optional<float> here_danger;
    const auto danger_change = [&](vec2 p) {
        if (!here_danger) here_danger = safety.expected_damage(b.here);
        return safety.expected_damage(p) - *here_danger;
    };
    const auto offer = [&](Plan plan, float before_danger, vec2 end) {
        if (before_danger <= best.value) return;
        plan.value = before_danger - danger_change(end);
        if (plan.value > best.value) best = plan;
    };
    if (intent.anchored) b.move = false, b.dash = -1;
    const auto& blocked = pathing.blocked();
    const bitboard* guard = pathing.guard();
    const auto walkable = [&](vec2 p) { return in_bounds(p) && !blocked.is_set(p) && !(guard && guard->is_set(p)); };
    if (b.move && b.attack) {
        for (auto d : directions) {
            const vec2 n = b.here + d;
            if (!walkable(n)) continue;
            const float gain = static_cast<float>(progress(intent, b.here, n)) * step;
            if (b.melee) {
                // Either attack here then the reset there, or the one attack there.
                const Hit there = best_hit(b, n, h0);
                if (there.target >= 0 && there.value > first.value)
                    offer({Kind::walk, 0, {}, n, false, false, false}, there.value + gain + shield_worth(world, safety, b, n), n);
                if (first.target >= 0 && b.reset >= 0)
                    if (const Hit second = best_hit(b, n, h1); second.target >= 0)
                        offer({Kind::walk, 0, {}, n, true, true, false}, first.value + second.value + gain, n);
            } else if (b.reset >= 0) {
                // A ranged walk spends the attack; the reset restores it.
                if (const Hit there = best_hit(b, n, h0); there.target >= 0)
                    offer({Kind::walk, 0, {}, n, false, true, false}, there.value + gain, n);
            }
        }
    }
    if (b.dash >= 0 && b.attack) {
        // The dash's cooldown would otherwise carry us two steps.
        const float dash_cost = dash_steps * step;
        const auto landings = pathing.dash_landings();
        for (int i = 0; i < b.n; ++i) {
            for (auto l : positions_within(landings, b.foes[i].pos, b.range)) {
                const Hit there = best_hit(b, l, h0);
                const bool before = b.melee && first.value > there.value;
                const float gain = static_cast<float>(progress(intent, b.here, l)) * step + (b.melee && walks ? step : 0.0f);
                offer({Kind::dash, 0, l, {}, before, false, false}, (before ? first : there).value + gain - dash_cost, l);
            }
            if (!b.melee || !b.move || dist(b.here, b.foes[i].pos) > b.range + 1 + dash_steps) continue;
            // Dash, then walk into range.
            for (int dy = -b.range; dy <= b.range; ++dy)
                for (int dx = -b.range; dx <= b.range; ++dx) {
                    const vec2 n{b.foes[i].pos.x + dx, b.foes[i].pos.y + dy};
                    if (n == b.here || !walkable(n) || dist(n, b.here) <= 1) continue;
                    const Hit there = best_hit(b, n, h0);
                    if (there.target < 0 || there.value - dash_cost + step <= best.value) continue;
                    const auto& near = within(landings, n, 1);
                    if (near.is_empty()) continue;
                    const float gain = static_cast<float>(progress(intent, b.here, n)) * step;
                    offer({Kind::dash_walk, 0, first_tile(near), n, false, false, false}, there.value + gain - dash_cost, n);
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
        if (best.enemy_cast) {
            bool exclusive = false;
            if (enemy_cast_value(world, intent.keep_walk, hold, exclusive) > 0) cast_chosen();
        }
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
    if (read_board(world, hold, b, f.attack_range() + (f.passive == Passive::splash_attack ? 1 : 0))) {
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
    // A cast the plan kept for a walk the goal did not take, or one a walk allows.
    if (state.contains(cambc::champion_state::can_cast)) cast_at_enemies(world, false, hold);
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
