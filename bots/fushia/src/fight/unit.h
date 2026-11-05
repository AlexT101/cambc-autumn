#pragma once
#include "kits.h"

// The champions of this turn's fight, from champs::info: us, the enemies seen this round or
// last, and the allies (for sharing an enemy's threat). Each has its damage table: the most
// it deals one champion on its next turn, by distance.
namespace fight {
    constexpr i32 max_d = 10;        // damage tables cover distances [0, max_d)
    constexpr f32 life_gold = 115.1f; // a death: the killer's 100 gold, and 60 rounds out
    constexpr i32 forget_after = 0;   // rounds an enemy that left our sight still counts

    struct unit {
        vec2 pos;
        f32 hp, shield;      // health, and shields on top
        f32 worth;           // gold its team loses when it dies: a life and the gems lost
        f32 strength, focus; // Heart of Ruin's rage already in
        const kit* k;
        i8 cooldown[2];
        bool seen;           // in our sight now: a target
        u32 id;              // in champs::info
        f32 dmg[max_d];      // the most damage it deals one champion on its next turn
        i32 reach;           // the farthest d with dmg[d] > 0, -1 none
        f32 share;           // of its threat that falls on us: 1 / (1 + allies it reaches)
    };

    inline unit me, foes[champs::max_champs / 2];
    inline u32 n_foes;
    inline vec2 friends[champs::max_champs / 2]; // allies but us, alive
    inline u32 n_friends;

    inline f32 ehp(const unit& u) {
        return u.hp + u.shield;
    }

    // gold `amount` damage on u is worth: its share of u's worth, all of it on a kill
    inline f32 score_damage(const unit& u, f32 amount) {
        return u.worth * std::min(amount / ehp(u), 1.f);
    }

    // The most damage u deals one champion d tiles away on a turn with these slots ready: a
    // walk and the basic attack (ranged: one or the other), plus one cast (an attack reset, a
    // spell, or a dash, Heart of Ruin's landing hitting around it).
    inline f32 most_damage(const unit& u, i32 d, bool ready0, bool ready1) {
        const kit& k = *u.k;
        const bool ranged = k.is_ranged();
        const i32 basic = ranged ? k.attack_range : k.attack_range + 1; // walk, then attack
        const f32 S = u.strength;
        f32 best = d <= basic ? S : 0;
        for (i32 i = 0; i < 2; ++i) {
            if (!(i ? ready1 : ready0))
                continue;
            const ability_kit& a = k.slots[i];
            const f32 spell = a.modifier * u.focus;
            switch (a.kind) {
                case effect::reset:
                    if (d <= basic)
                        best = std::max(best, 2 * S);
                    break;
                case effect::damage:
                case effect::stun:
                case effect::area: {
                    const i32 r = a.range + a.radius;
                    if (d <= r) // standing: the attack from here too
                        best = std::max(best, spell + (d <= k.attack_range ? S : 0));
                    if (!a.exclusive && d <= r + 1) // walking in
                        best = std::max(best, spell + (!ranged && d <= basic ? S : 0));
                    break;
                }
                case effect::dash:
                    if (d <= a.range + basic)
                        best = std::max(best, S);
                    if (a.radius && d <= a.range + 1 + a.radius)
                        best = std::max(best, spell + (d <= a.range + basic ? S : 0));
                    break;
                default:
                    break;
            }
        }
        return best;
    }

    inline void fill_damage(unit& u, bool ready0, bool ready1) {
        u.reach = -1;
        for (i32 d = 0; d < max_d; ++d)
            if ((u.dmg[d] = most_damage(u, d, ready0, ready1)) > 0)
                u.reach = d;
    }

    // the other body of Cassi and Issac, on c's team; null for the rest
    inline const champ_info* partner_of(u32 id) {
        const champ_info& c = champs::info[id];
        if (!kits[u32(c.type)].paired)
            return nullptr;
        const u32* ids = c.is_ally ? champs::allies : champs::enemies;
        const u32 n = c.is_ally ? champs::n_allies : champs::n_enemies;
        for (u32 i = 0; i < n; ++i)
            if (ids[i] != id && kits[u32(champs::info[ids[i]].type)].paired)
                return &champs::info[ids[i]];
        return nullptr;
    }

    inline void make_unit(u32 id, unit& u) {
        using bk = cambc::detail::buff_kind;
        const champ_info& c = champs::info[id];
        u.pos = c.pos, u.hp = c.health, u.shield = 0;
        for (u32 i = 0; i < c.n_buffs; ++i)
            if (c.buffs[i].type == u32(bk::shield))
                u.shield += c.buffs[i].data.shield.value;
        u32 gems = c.gems;
        if (const champ_info* p = partner_of(id)) // they die together
            gems += p->gems;
        u.worth = life_gold + f32(gems) * economy::gem_worth_in_gold();
        u.k = &kits[u32(c.type)];
        const f32 rage = 1 + u.k->rage * (1 - c.health / c.max_health);
        u.strength = c.strength * rage, u.focus = c.focus * rage;
        u.cooldown[0] = i8(c.cooldowns[0]), u.cooldown[1] = i8(c.cooldowns[1]);
        u.seen = c.pos_observed == g::round;
        u.id = id;
        u.share = 1;
    }

    inline bool is_alive(const champ_info& c) {
        return c.state.contains(cambc::champion_state::alive);
    }

    // An enemy alive, seen this round or last.
    inline bool is_fresh(const champ_info& e) {
        return g::round - e.pos_observed <= forget_after && is_alive(e);
    }

    inline void observe() {
        make_unit(champs::my_id, me);
        n_foes = 0;
        for (u32 i = 0; i < champs::n_enemies; ++i) {
            const u32 id = champs::enemies[i];
            if (!is_fresh(champs::info[id]) ||
                util::chebyshev(champs::info[id].pos, g::my_pos) >= max_d + 3)
                continue;
            unit& f = foes[n_foes++];
            make_unit(id, f);
            fill_damage(f, f.cooldown[0] == 0, f.cooldown[1] == 0);
        }

        // allies: as seen this round, else where they ended their last turn
        n_friends = 0;
        for (u32 i = 0; i < champs::n_allies; ++i) {
            const u32 id = champs::allies[i];
            const champ_info& a = champs::info[id];
            if (id == champs::my_id)
                continue;
            const vec2 p = a.vision_observed == g::round ? (is_alive(a) ? a.pos : vec2{-1, -1})
                                                         : comms::ally_position::pos[id];
            if (p.x >= 0)
                friends[n_friends++] = p;
        }
        for (u32 f = 0; f < n_foes; ++f) {
            u32 others = 0;
            for (u32 i = 0; i < n_friends; ++i)
                others += util::chebyshev(friends[i], foes[f].pos) <= foes[f].reach;
            foes[f].share = 1 / f32(1 + others);
        }
    }
} // namespace fight
