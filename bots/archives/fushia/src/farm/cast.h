#pragma once
#include "../common/common.h"
#include "../fight/kits.h"
#include "hit.h"
#include <algorithm>

// An ability on the group we farm: the ready slot worth the most this turn, from our kit. Damage
// and area count what they deal, a stun also the hit it saves (a monster within 3 of us), a reset
// the second attack it gives, a shield what it would absorb in its 5 rounds. A slot that stops
// walking only on a turn we did not walk. Only monsters with health left, as read now.
namespace farm {
    struct cast_choice {
        i8 slot = -1;
        const camp_info::monster* on = nullptr; // else the tile `at` (-1, -1: ourselves)
        vec2 at{-1, -1};
        f32 value = 0;
        bool resets = false; // a second attack follows
    };

    // m's health, read now; 0 if dead or out of our own sight
    inline f32 health_left(const camp_info::monster& m) {
        f32 hp;
        return camp_info::health(m, hp) ? std::max(hp, 0.f) : 0;
    }

    inline f32 hits_for(const camp_info::monster& m) {
        return camp_info::stats_of(m).base_strength;
    }

    inline cast_choice choose_cast(const camp_info::group& grp, bool walked, bool attacked) {
        using fight::effect;
        cast_choice best;
        const champ_info& me = champs::my_info();
        if (!channel::state().contains(cambc::champion_state::can_cast))
            return best;
        const fight::kit& K = fight::kits[u32(me.type)];
        const vec2 from = g::my_pos;
        const auto consider = [&](cast_choice c) {
            if (c.value > best.value)
                best = c;
        };
        for (i8 s = 0; s < 2; ++s) {
            const fight::ability_kit& a = K.slots[s];
            if (me.cooldowns[s] || (a.exclusive && walked))
                continue;
            const f32 spell = a.modifier * me.focus;
            switch (a.kind) {
                case effect::damage:
                case effect::stun:
                    for (const camp_info::monster& m : camp_info::members(grp)) {
                        const i32 d = util::chebyshev(from, m.pos);
                        const f32 hp = d <= a.range ? health_left(m) : 0;
                        if (hp == 0)
                            continue;
                        const f32 saved = a.kind == effect::stun && d <= 3 ? hits_for(m) : 0;
                        consider({s, &m, {}, std::min(spell, hp) + saved, false});
                    }
                    break;
                case effect::area:
                    for (const camp_info::monster& t : camp_info::members(grp)) {
                        if (util::chebyshev(from, t.pos) > a.range + a.radius)
                            continue;
                        const vec2 d = t.pos - from;
                        const vec2 at = from + vec2{std::clamp<i32>(d.x, -a.range, a.range),
                                                    std::clamp<i32>(d.y, -a.range, a.range)};
                        f32 v = 0;
                        for (const camp_info::monster& m : camp_info::members(grp)) {
                            if (util::chebyshev(at, m.pos) > a.radius)
                                continue;
                            if (const f32 hp = health_left(m))
                                v += std::min(spell, hp) + (a.stun ? hits_for(m) : 0);
                        }
                        consider({s, nullptr, at, v, false});
                    }
                    break;
                case effect::reset:
                    // the weakest in range outlives a hit (in a plan, the first hit is not made
                    // yet)
                    if (!attacked)
                        break;
                    if (const hit_candidate h = weakest_in_range(grp);
                        h.monster && h.hp > me.strength) {
                        const f32 stun = a.stun ? hits_for(*h.monster) : 0;
                        consider({s, nullptr, {-1, -1}, std::min(me.strength, h.hp) + stun, true});
                    }
                    break;
                case effect::shield: {
                    f32 incoming = 0;
                    for (const camp_info::monster& m : camp_info::members(grp))
                        if (util::chebyshev(from, m.pos) <= 3 && health_left(m) > 0)
                            incoming += hits_for(m);
                    consider({s, nullptr, {-1, -1}, std::min(spell, 5 * incoming), false});
                    break;
                }
                default: // dash, heal
                    break;
            }
        }
        return best;
    }
} // namespace farm
