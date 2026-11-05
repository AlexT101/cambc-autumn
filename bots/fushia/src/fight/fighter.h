#pragma once
#include "../farm/hit.h"
#include "../game/actions.h"
#include "threat.h"

// fighter<T>: a fight turn as champion type T. Every move (stay, a walk, a dash) is scored in
// gold with the best actions it allows (score_plan), and the best plan is made. T's kit is
// read at compile time, so only the kinds T has are looked for.
namespace fight {
    constexpr f32 next_weight = 0.539f; // of what we could hit next turn: the enemy moves too
    constexpr f32 protect_gold = 0.938f; // a point of an ally's health an enemy's stun or death saves
    constexpr f32 home_pull = 7.062f;    // gold a step nearer our spawn, at no health left
    constexpr f32 gem_pull = 0.00009f;   // of the carried gems' worth, a step nearer an altar
    constexpr f32 economy_gold = 5;     // the economy's turn, over a plan that only moves there
    constexpr i64 budget = 75000; // fuel used this turn past which no more moves are listed

    inline cambc::distance_field to_altar; // steps over fixed ground

    inline f32 base_threat[(2 * window + 1) * (2 * window + 1)];
    inline f32 protect[champs::max_champs / 2]; // gold an enemy's stun or death saves our allies

    inline void init_value() {
        static cambc::bitboard visited;
        to_altar.compute(map_info::fixed, map_info::altar_adj, visited);
    }

    // Where we end the turn: nearer our spawn when hurt, nearer an altar with gems.
    inline f32 score_tile(vec2 t) {
        const champ_info& c = champs::my_info();
        const i32 cell = map_info::cell(t);
        const f32 hurt = 1 - c.health / c.max_health;
        const f32 gems = f32(c.gems) * economy::gem_worth_in_gold();
        return -home_pull * hurt * f32(map_info::to_spawn.ptr()[cell]) -
               gem_pull * gems * f32(to_altar.ptr()[cell]);
    }

    // What a plan does, in the order it is made: a cast and the attacks (the second after an
    // attack reset) before the move when `first`, the move, then the rest.
    struct plan {
        vec2 to;
        i8 dash = -1;           // the slot, when the move is a dash
        i8 hit = -1, hit2 = -1; // foes attacked; hit2 after the reset
        bool hit_first = false;
        i8 slot = -1;           // the ability cast, a reset included (not the dash)
        i8 cast_on = -1;        // its target foe; -1: the tile cast_at, or ourselves
        vec2 cast_at{-1, -1};
        bool cast_first = false;
    };

    // ---- for real

    // Still a target: in range and in sight. An earlier hit may have killed it (its twin too),
    // or the move taken it out of sight.
    inline bool is_target(i8 f, i32 range) {
        cambc::detail::champion_info raw;
        return util::chebyshev(g::my_pos, foes[f].pos) <= range &&
               cambc::detail::sdk_champion(foes[f].id, &raw) == 0 && raw.health > 0;
    }

    inline bool sdk_cast(i8 slot, i8 on, vec2 at) {
        using namespace cambc::detail;
        channel::drop();
        i32 ok;
        if (on >= 0)
            check(cambc::detail::sdk_cast(u32(slot), u32(entity_kind::champion), foes[on].id, -1,
                                          -1, &ok));
        else
            check(cambc::detail::sdk_cast(u32(slot), 0, 0, at.x, at.y, &ok));
        return ok != 0;
    }

    // false: Ren hit back and killed us
    inline bool sdk_attack(i8 f) {
        using namespace cambc::detail;
        channel::drop();
        check(cambc::detail::sdk_attack(u32(entity_kind::champion), foes[f].id));
        return foes[f].k->retaliate == 0 ||
               g::me().state().contains(cambc::champion_state::alive);
    }

    template <ct T>
    struct fighter {
        static constexpr kit K = kits[u32(T)];

        static inline f32 next_dmg[3][max_d]; // ours next turn: no slot used, slot 0, slot 1
        static inline plan best;
        static inline f32 best_v;
        static inline bool can_attack, can_cast;
        static inline bool must_attack; // melee, with an enemy champion in reach from here

        // ---- scoring

        static f32 score_plan(const plan& p) {
            f32 dealt[champs::max_champs / 2] = {};
            bool stunned[champs::max_champs / 2] = {};
            f32 my_shield = 0;
            const auto stun = [&](i8 f) { stunned[f] = !foes[f].k->stun_immune; };

            if (p.hit >= 0)
                dealt[p.hit] += me.strength;
            if (p.hit2 >= 0) {
                dealt[p.hit2] += me.strength;
                if (K.slots[p.slot].stun) // Marcella's reset charges a stun
                    stun(p.hit2);
            }
            if (p.slot >= 0) {
                const ability_kit& a = K.slots[p.slot];
                const f32 spell = a.modifier * me.focus;
                if (a.kind == effect::damage || a.kind == effect::stun) {
                    dealt[p.cast_on] += spell;
                    if (a.stun)
                        stun(p.cast_on);
                } else if (a.kind == effect::area) {
                    for (u32 f = 0; f < n_foes; ++f)
                        if (util::chebyshev(foes[f].pos, p.cast_at) <= a.radius) {
                            dealt[f] += spell;
                            if (a.stun)
                                stun(i8(f));
                        }
                } else if (a.kind == effect::shield)
                    my_shield = spell;
            }
            if (p.dash >= 0 && K.slots[p.dash].radius) { // Heart of Ruin's landing
                const ability_kit& a = K.slots[p.dash];
                for (u32 f = 0; f < n_foes; ++f)
                    if (foes[f].seen && util::chebyshev(foes[f].pos, p.to) <= a.radius) {
                        dealt[f] += a.modifier * me.focus;
                        if (a.stun)
                            stun(i8(f));
                    }
            }

            // gold dealt; the foes it kills or stuns hit no one next turn
            f32 v = 0, threat = at.threat;
            bool killed_any = false, touched = false;
            for (u32 f = 0; f < n_foes; ++f) {
                if (dealt[f] == 0 && !stunned[f])
                    continue;
                touched = true;
                const bool killed = dealt[f] >= ehp(foes[f]);
                killed_any |= killed;
                v += score_damage(foes[f], dealt[f]);
                if (killed || stunned[f])
                    threat -= at.threat_of[f], v += protect[f];
            }

            // the best hit we could make next turn from p.to
            const i32 used = K.resets_on_kill && killed_any ? 0 : 1 + (p.dash >= 0 ? p.dash : p.slot);
            f32 next_v = at.next_v[used];
            if (touched) {
                const f32* next = next_dmg[used];
                next_v = 0;
                for (u32 f = 0; f < n_foes; ++f) {
                    const unit& u = foes[f];
                    const f32 left = ehp(u) - dealt[f];
                    if (left > 0 && at.d[f] < max_d)
                        next_v = std::max(next_v, u.worth * std::min(next[at.d[f]], left) / ehp(u));
                }
            }

            const f32 risk = me.worth * std::min(std::max(threat, 0.f) / (ehp(me) + my_shield), 1.f);
            return v + next_weight * next_v - risk + at.tile;
        }

        // the move's terms that no action changes, worked out once per move
        struct move_terms {
            i32 d[champs::max_champs / 2];        // to each foe
            f32 threat_of[champs::max_champs / 2]; // each foe's share of `threat`
            f32 threat, tile;                      // score_tile
            f32 next_v[3];                         // by next_dmg row, with no damage dealt
        };
        static inline move_terms at;

        static void set_move_terms(vec2 to) {
            at.threat = base_threat[window_index(to)], at.tile = score_tile(to);
            at.next_v[0] = at.next_v[1] = at.next_v[2] = 0;
            for (u32 f = 0; f < n_foes; ++f) {
                const i32 d = at.d[f] = util::chebyshev(to, foes[f].pos);
                at.threat_of[f] = threat_of(foes[f], d);
                if (d < max_d)
                    for (u32 r = 0; r < 3; ++r)
                        at.next_v[r] = std::max(at.next_v[r], foes[f].worth *
                                                                  std::min(next_dmg[r][d], ehp(foes[f])) /
                                                                  ehp(foes[f]));
            }
        }

        static void consider(const plan& p) {
            if (must_attack && p.hit < 0)
                return;
            if (const f32 v = score_plan(p); v > best_v)
                best = p, best_v = v;
        }

        // ---- listing

        // p, which has its move and its attack, with each spell slot i allows
        template <i32 i>
        static void add_cast(plan p, bool walked) {
            constexpr ability_kit A = K.slots[i];
            if (me.cooldown[i] || (A.exclusive && walked))
                return;
            p.slot = i;
            if constexpr (A.kind == effect::reset) {
                if (p.hit < 0)
                    return;
                // the same foe again, unless the first attack kills it
                const vec2 from = p.hit_first ? me.pos : p.to;
                if (me.strength < ehp(foes[p.hit])) {
                    p.hit2 = p.hit, consider(p);
                    return;
                }
                for (u32 f = 0; f < n_foes; ++f)
                    if (i8(f) != p.hit && foes[f].seen &&
                        util::chebyshev(from, foes[f].pos) <= K.attack_range)
                        p.hit2 = i8(f), consider(p);
            } else if constexpr (A.kind == effect::damage || A.kind == effect::stun) {
                for (u32 f = 0; f < n_foes; ++f) {
                    if (!foes[f].seen)
                        continue;
                    p.cast_on = i8(f);
                    if (util::chebyshev(me.pos, foes[f].pos) <= A.range)
                        p.cast_first = true, consider(p);
                    else if (walked && util::chebyshev(p.to, foes[f].pos) <= A.range)
                        p.cast_first = false, consider(p);
                }
            } else if constexpr (A.kind == effect::area) {
                for (u32 f = 0; f < n_foes; ++f)
                    if (foes[f].seen &&
                        util::chebyshev(me.pos, foes[f].pos) <= A.range + A.radius) {
                        const vec2 d = foes[f].pos - me.pos;
                        p.cast_at = me.pos + vec2{std::clamp<i32>(d.x, -A.range, A.range),
                                                  std::clamp<i32>(d.y, -A.range, A.range)};
                        p.cast_first = true, consider(p);
                    }
            } else if constexpr (A.kind == effect::shield) {
                p.cast_first = true, consider(p);
            }
        }

        // the plans ending on `to`: each attack it allows, alone and with each cast
        static void add_plans_at(vec2 to, i8 dash, bool walked) {
            if (g::fuel_start - i64(cambc::fuel_remaining()) > budget)
                return; // the plain moves come first, so the dashes drop
            set_move_terms(to);
            plan p{.to = to, .dash = dash};
            const bool casts = can_cast && dash < 0;
            const auto with_casts = [&](const plan& q) {
                consider(q);
                if (casts)
                    add_cast<0>(q, walked), add_cast<1>(q, walked);
            };
            with_casts(p);
            // melee from either end of the move; ranged only if it did not walk
            if (!can_attack || (K.is_ranged() && walked))
                return;
            for (u32 f = 0; f < n_foes; ++f) {
                if (!foes[f].seen)
                    continue;
                p.hit = i8(f);
                if (util::chebyshev(me.pos, foes[f].pos) <= K.attack_range)
                    p.hit_first = true, with_casts(p);
                else if (to != me.pos && util::chebyshev(to, foes[f].pos) <= K.attack_range)
                    p.hit_first = false, with_casts(p);
            }
        }

        static void add_dash_plans(const cambc::bitboard& free, const cambc::bitboard& over) {
            constexpr i32 slot = K.slot_of(effect::dash);
            if constexpr (slot >= 0) {
                if (me.cooldown[slot] || !can_cast)
                    return;
                for (i32 dy = -2; dy <= 2; ++dy)
                    for (i32 dx = -2; dx <= 2; ++dx) {
                        const vec2 land = me.pos + vec2{dx, dy};
                        if (std::max(std::abs(dx), std::abs(dy)) != 2 ||
                            !polyfill::is_in_bounds(land) || !polyfill::is_set(free, land))
                            continue;
                        // a middle tile next to both ends it may pass over
                        bool path = false;
                        for (i32 y = std::max(-1, dy - 1); y <= std::min(1, dy + 1); ++y)
                            for (i32 x = std::max(-1, dx - 1); x <= std::min(1, dx + 1); ++x)
                                if (const vec2 m = me.pos + vec2{x, y};
                                    (x || y) && polyfill::is_in_bounds(m) && polyfill::is_set(over, m))
                                    path = true;
                        if (path)
                            add_plans_at(land, i8(slot), false);
                    }
            }
        }

        // ---- the turn

        static void make(const plan& p) {
            const auto attacks = [&] {
                if (!is_target(p.hit, K.attack_range))
                    return true;
                if (!sdk_attack(p.hit))
                    return false;
                if (p.hit2 >= 0 && is_target(p.hit2, K.attack_range)) {
                    sdk_cast(p.slot, -1, {-1, -1});
                    return sdk_attack(p.hit2);
                }
                return true;
            };
            const bool resets = p.slot >= 0 && K.slots[p.slot].kind == effect::reset;
            const auto cast = [&] {
                const i32 range = K.slots[p.slot].range + K.slots[p.slot].radius;
                if (p.cast_on < 0 || is_target(p.cast_on, range))
                    sdk_cast(p.slot, p.cast_on, p.cast_at);
            };
            if (p.slot >= 0 && !resets && p.cast_first)
                cast();
            if (p.hit >= 0 && p.hit_first && !attacks())
                return;
            if (p.to != g::my_pos) {
                if (p.dash >= 0 ? sdk_cast(p.dash, -1, p.to) : move_manager::move_absolute(p.to))
                    g::my_pos = p.to;
            }
            if (p.hit >= 0 && !p.hit_first && !attacks())
                return;
            if (p.slot >= 0 && !resets && !p.cast_first)
                cast();
        }

        // the attack the plan left: on the weakest awake monster in reach (a hit wakes a
        // sleeping group, and it hits whoever stands nearest)
        static void hit_monster() {
            if (!channel::state().contains(cambc::champion_state::can_attack))
                return;
            static cambc::bitboard awake;
            cambc::vision::awake_camp_tiles_into(awake);
            farm::hit_candidate best{nullptr, 0};
            for (const camp_info::group* grp : camp_info::groups_in_view)
                if (const farm::hit_candidate h = farm::weakest_in_range(*grp);
                    h.monster && polyfill::is_set(awake, h.monster->pos) &&
                    (!best.monster || h.is_better_than(best)))
                    best = h;
            if (best.monster)
                camp_info::attack(*best.monster);
        }

        static void play_turn(const actions::plan& economy) {
            using cs = cambc::champion_state;
            const cambc::champion_state flags = champs::my_info().state;
            can_attack = flags.contains(cs::can_attack);
            can_cast = flags.contains(cs::can_cast);

            threat_into(base_threat);
            for (u32 f = 0; f < n_foes; ++f) {
                f32 most = 0;
                for (u32 i = 0; i < n_friends; ++i)
                    if (const i32 d = util::chebyshev(friends[i], foes[f].pos); d < max_d)
                        most = std::max(most, foes[f].dmg[d]);
                protect[f] = protect_gold * foes[f].share * most;
            }
            const bool ready0 = me.cooldown[0] <= 1, ready1 = me.cooldown[1] <= 1;
            fill_damage(me, ready0, ready1), std::copy_n(me.dmg, max_d, next_dmg[0]);
            fill_damage(me, false, ready1), std::copy_n(me.dmg, max_d, next_dmg[1]);
            fill_damage(me, ready0, false), std::copy_n(me.dmg, max_d, next_dmg[2]);

            // free: where we may stand; over: what a dash may pass over
            static cambc::bitboard free, over, units, enemies;
            polyfill::champion_tiles_into(units);
            bb::or_into(units, map_info::fixed, free), free |= camp_info::maybe_alive;
            bb::not_into(free, free);
            cambc::vision::champion_tiles_into(cambc::team::enemy, enemies);
            bb::or_into(map_info::walls, map_info::enemy_spawn, over),
                over |= camp_info::maybe_alive, over |= enemies;
            bb::not_into(over, over);

            // the seen foe our attack from here is worth most on; -1 none
            i8 strike = -1;
            if (can_attack)
                for (u32 f = 0; f < n_foes; ++f)
                    if (foes[f].seen && util::chebyshev(me.pos, foes[f].pos) <= K.attack_range &&
                        (strike < 0 || score_damage(foes[f], me.strength) >
                                           score_damage(foes[strike], me.strength)))
                        strike = i8(f);
            must_attack = strike >= 0 && !K.is_ranged(); // only a free hit: melee keeps its walk

            best_v = -1e30f;
            add_plans_at(me.pos, -1, false);
            if (flags.contains(cs::can_move))
                for (const vec2 dir : path::DIRS)
                    if (const vec2 t = me.pos + dir; polyfill::is_in_bounds(t) && polyfill::is_set(free, t))
                        add_plans_at(t, -1, true);
            add_dash_plans(free, over);
            set_move_terms(economy.to);
            if (score_plan({.to = economy.to}) + economy_gold > best_v) {
                if (must_attack && is_target(strike, K.attack_range) && !sdk_attack(strike))
                    return; // Ren hit back and killed us
                economy.make();
                return;
            }
            make(best);
            hit_monster();
        }
    };
} // namespace fight
