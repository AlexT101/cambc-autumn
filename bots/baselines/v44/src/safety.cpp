#include "safety.h"
#include <algorithm>
#include <bit>
#include <cmath>
#include <cstring>
#include <limits>
#include <memory>
#include <vector>
#include "world.h"

namespace aph {

using namespace safety_params;

namespace {

// walls.shadow_cast_into(origin, r, out) without check()'s call.
[[gnu::always_inline]] inline void shadow_into(const bitboard& walls, vec2 origin, std::uint16_t r, bitboard& out) {
    ok(cambc::detail::sdk_Bitboard_ShadowCast(walls.ptr(), origin.x, origin.y, out.ptr(), r));
}

constexpr int max_fighters = 6; // one team's bodies
constexpr int never = std::numeric_limits<int>::max();

// Strength and Focus as they deal damage: Heart of Ruin's passive at its last-read health.
float hit_strength(const ChampionBelief& c) { return c.strength * c.scale; }
float hit_focus(const ChampionBelief& c) { return c.focus * c.scale; }

// What casting a slot adds to a turn's basic attack.
struct CastEffect {
    float value = 0; // the choice between ready slots: the most valuable, if any above 0
    float damage = 0, heal = 0;
    bool heals_self = false; // a shield; a heal goes to the weakest hurt ally
    bool stuns = false;
    bool heals_ally = false;
    int hits = 1;
    int duration = 0; // a shield's own turns
};

// A champion's casts, fixed for a turn.
struct Kit {
    std::array<CastEffect, 2> cast;
    std::array<int, 2> preference; // slots by value, ties to slot 0
    // No shield, and its Strength and cast damage are sixteenths small enough that any sum of a
    // side's is exact in any order.
    bool plain;
};

bool exact(float v) { return v >= 0 && v < 4096 && v * 16 == std::trunc(v * 16); }

// Turns are counted per side from 0, so cooldowns and arrivals are turn indices rather than
// counters to tick down.
struct Fighter {
    const Kit* kit;
    float strength;
    std::array<int, 2> ready_at; // own turn from which the slot can be cast; never: not worth it
    int next_cast;               // own turn from which a slot worth casting is ready
    int arrives_at;              // own turns spent walking into reach first; never: idle
    bool stun_immune, linked;
    float health, max_health;
    float shield;
    int shield_until;  // own turn at whose start the shield is lost; never: no shield
    float retaliation; // Ren: damage back per hit taken
    float taken;       // damage it takes per point dealt (a Durability emblem)
    int link;          // Cassi or Issac: the other body, which dies with this one
};

// Fixed storage, as WASM heap work is costly; only the first `count` fighters are written, as the
// engine charges for every byte.
struct Side {
    union {
        std::array<Fighter, max_fighters> fighters;
    };
    int count = 0;
    int alive = 0; // members with health above 0; the fallen stay down
    int turn = 0; // own turns taken
    int self = -1; // our own fighter
    int stunned = 0; // members that lose their next turn
    float camp = 0;  // camp damage taken with each of the other side's turns
    // Own turns before `quiet_until` are only the basic attacks, `quiet_damage` from `quiet_hits`
    // hits, while nobody is stunned and `alive` stays `quiet_alive`.
    int quiet_until = 0, quiet_alive = -1, quiet_hits = 0;
    float quiet_damage = 0;
    int weak = -2; // weakest(), or -2 when it must be found again
    bool plain = true; // every kit plain and no arrivals

    constexpr Side() {}

    void add(const Fighter& f) {
        if (count == max_fighters) return;
        auto& g = fighters[count];
        g = f;
        plain = plain && g.kit->plain && g.arrives_at == 0;
        if (g.linked)
            for (int i = 0; i < count; ++i)
                if (fighters[i].linked) g.link = i, fighters[i].link = count;
        alive += g.health > 0;
        ++count;
        weak = -2;
    }
    float health() const {
        float total = 0;
        for (int i = 0; i < count; ++i) total += std::max(0.0f, fighters[i].health);
        return total;
    }
    // The living member with the least health and shield, or -1. Damage only lands on it, so it
    // stays the weakest until it falls, or a heal or shield comes or goes.
    int weakest() {
        if (weak != -2) return weak;
        int best = -1;
        for (int i = 0; i < count; ++i)
            if (fighters[i].health > 0
                && (best < 0 || fighters[i].health + fighters[i].shield < fighters[best].health + fighters[best].shield))
                best = i;
        return weak = best;
    }
    // Member i gained health or shield: only if it was the weakest can another be weaker now.
    void lifted(int i) {
        if (weak == i) weak = -2;
    }
    // Member i lost its shield: it is the weakest now if below the weakest, or as low and first.
    void lowered(int i) {
        if (weak < 0 || i == weak || fighters[i].health <= 0) return;
        const float a = fighters[i].health + fighters[i].shield, b = fighters[weak].health + fighters[weak].shield;
        if (a < b || (a == b && i < weak)) weak = i;
    }
    // A heal's target: the living member below max health with the least, other than `caster`.
    int weakest_hurt(int caster) const {
        int best = -1;
        for (int i = 0; i < count; ++i)
            if (i != caster && fighters[i].health > 0 && fighters[i].health < fighters[i].max_health
                && (best < 0 || fighters[i].health < fighters[best].health))
                best = i;
        return best;
    }
    // Focused on the weakest, shields first, the excess spilling over to the next. `first`:
    // weakest(), when the caller has it.
    void hurt(float damage, int first = -2) {
        if (damage <= 0) return;
        const int i = first >= -1 ? first : weakest();
        if (i < 0) return;
        // The weakest takes it all and lives: the loop below in short.
        if (auto& f = fighters[i]; f.shield == 0 && damage * f.taken < f.health) {
            f.health -= damage * f.taken;
            return;
        }
        spill(damage, i);
    }
    // `damage` as dealt: each member takes it through its own Durability.
    [[gnu::noinline]] void spill(float damage, int first) {
        for (int i = first; i >= 0; i = damage > 0 ? weakest() : -1) {
            auto& f = fighters[i];
            float d = damage * f.taken;
            if (f.shield != 0) {
                const float absorbed = std::min(d, f.shield);
                f.shield -= absorbed;
                d -= absorbed;
            }
            const float lost = std::min(d, f.health);
            f.health -= lost;
            damage = (d - lost) / f.taken;
            if (f.health > 0) continue;
            weak = -2;
            --alive;
            if (f.link >= 0) {
                alive -= fighters[f.link].health > 0;
                fighters[f.link].health = 0;
            }
        }
    }
};

int next_cast(const Fighter& f) { return std::min(f.ready_at[0], f.ready_at[1]); }

// A champion's casts, from its type, Strength and Focus alone. A heal is valued even with no ally
// to take it: attack() then finds no target and moves on, as if it were worth nothing.
void make_kit(const ChampionBelief& c, Kit& kit) {
    const auto& facts = c.facts();
    const float strength = hit_strength(c), focus = hit_focus(c);
    for (int s = 0; s < 2; ++s) {
        const auto& a = facts.abilities[s];
        auto& e = kit.cast[s];
        e = {};
        const bool damages = a.kind == AbilityKind::damage || a.lands();
        e.value = a.stuns ? strength : 0;
        if (a.kind == AbilityKind::attack_reset) e.value += strength;
        if (damages) e.value += a.multiplier * focus;
        if (a.kind == AbilityKind::shield || a.kind == AbilityKind::heal) e.value += a.multiplier * c.focus;
        e.stuns = a.stuns;
        if (a.kind == AbilityKind::shield || a.kind == AbilityKind::heal) e.heal = a.multiplier * c.focus;
        e.heals_self = a.kind == AbilityKind::shield;
        e.heals_ally = e.heal != 0 && !e.heals_self;
        if (a.kind == AbilityKind::attack_reset) e.damage = strength;
        if (damages) e.damage = a.multiplier * focus;
        e.hits = a.kind == AbilityKind::attack_reset || damages ? 2 : 1;
        e.duration = a.duration;
    }
    kit.preference = kit.cast[1].value > kit.cast[0].value ? std::array<int, 2>{1, 0} : std::array<int, 2>{0, 1};
    kit.plain = exact(strength) && exact(kit.cast[0].damage) && exact(kit.cast[1].damage) && !kit.cast[0].heals_self
                && !kit.cast[1].heals_self;
}

// A champion as it enters a fight, with its kit made.
void make_fighter(const ChampionBelief& c, int turn_round, Fighter& f, Kit& kit) {
    const auto& facts = c.facts();
    f.kit = &kit;
    f.strength = hit_strength(c);
    const bool uncertain = c.cooldowns_uncertain();
    for (int s = 0; s < 2; ++s)
        f.ready_at[s] = kit.cast[s].value <= 0 ? never : uncertain ? 0 : std::max(0, c.ready_round[s] - turn_round);
    f.next_cast = next_cast(f);
    f.arrives_at = 0;
    f.stun_immune = facts.passive == Passive::stun_immune;
    f.linked = facts.passive == Passive::linked_pair;
    f.health = c.health;
    f.max_health = c.max_health;
    const bool shielded = c.shield > 0 && (c.visible || c.is_self);
    f.shield = shielded ? c.shield : 0;
    // At 0 turn ends left it is lost at turn 0's start, though it still absorbs what comes before.
    f.shield_until = shielded ? c.shield_turns : never;
    f.retaliation = c.retaliation();
    f.taken = c.taken;
    f.link = -1;
}

// Fighters made this turn, by slot: allies[i] at i, enemies[i] at 16 + i. Beliefs are fixed for
// the turn, so each is made once and copied into each fight.
struct Fighters {
    union {
        std::array<Fighter, 32> fighter;
    };
    union {
        std::array<Kit, 32> kit;
    };
    // Kits are kept across turns while what they are made from holds: bit i, kit[i] is made from
    // kit_of[i] (type, Strength and Focus).
    std::uint32_t kits = 0;
    std::array<std::array<std::uint32_t, 3>, 32> kit_of{};
    constexpr Fighters() {}
};

constinit Fighters made_fighters;

// A fighter's most valuable ready cast (one a turn); returns hits landed with the basic attack.
[[gnu::always_inline]] inline int cast(Fighter& f, int turn, Side& self, Side& other, float& damage) {
    for (const int s : f.kit->preference) {
        const auto& c = f.kit->cast[s];
        if (f.ready_at[s] > turn) continue;
        const int target = c.heals_ally ? self.weakest_hurt(static_cast<int>(&f - self.fighters.data())) : -1;
        if (c.heals_ally && target < 0) continue;
        f.ready_at[s] = turn + ability_cooldown;
        f.next_cast = next_cast(f);
        other.stunned += c.stuns;
        if (c.heals_self) {
            f.shield = c.heal, f.shield_until = turn + c.duration;
            self.lifted(static_cast<int>(&f - self.fighters.data()));
        } else if (target >= 0) {
            auto& t = self.fighters[target];
            t.health = std::min(t.max_health, t.health + c.heal);
            self.lifted(target);
        }
        damage += c.damage;
        return c.hits;
    }
    return 1;
}

// A fighter's basic attack and its most valuable ready cast; returns hits landed.
int attack(Fighter& f, int turn, Side& self, Side& other, float& damage) {
    damage += f.strength;
    return turn < f.next_cast ? 1 : cast(f, turn, self, other, damage);
}

// Bit i: fighters[i] is stunned, the strongest of those in reach first.
unsigned stun_skips(const Side& self, int turn) {
    unsigned skip = 0;
    for (int k = 0; k < self.stunned; ++k) {
        int best = -1;
        for (int i = 0; i < self.count; ++i) {
            const auto& f = self.fighters[i];
            if (!(skip >> i & 1) && f.health > 0 && f.arrives_at <= turn && !f.stun_immune
                && (best < 0 || f.strength > self.fighters[best].strength))
                best = i;
        }
        if (best < 0) break;
        skip |= 1u << best;
    }
    return skip;
}

// One side's turn: stunned members (the strongest of those in reach first) skip it.
float act(Side& self, Side& other) {
    const int turn = self.turn++;
    float damage = 0;
    int hits = 0;
    if (self.stunned == 0 && turn < self.quiet_until && self.alive == self.quiet_alive) {
        damage = self.quiet_damage;
        hits = self.quiet_hits;
    } else if (self.plain) {
        // The basic attacks are the quiet ones, and the casts add to them exactly.
        const unsigned skip = self.stunned == 0 ? 0u : stun_skips(self, turn);
        self.stunned = 0;
        const int count = self.count;
        if (self.alive != self.quiet_alive) {
            int quiet_hits = 0;
            float quiet = 0;
            for (int i = 0; i < count; ++i)
                if (const auto& f = self.fighters[i]; f.health > 0) quiet += f.strength, ++quiet_hits;
            self.quiet_alive = self.alive;
            self.quiet_damage = quiet;
            self.quiet_hits = quiet_hits;
        }
        damage = self.quiet_damage;
        hits = self.quiet_hits;
        for (unsigned left = skip; left; left &= left - 1) damage -= self.fighters[std::countr_zero(left)].strength, --hits;
        int until = never;
        for (int i = 0; i < count; ++i) {
            auto& f = self.fighters[i];
            if (f.health <= 0) continue;
            if (f.next_cast <= turn && !(skip >> i & 1)) hits += cast(f, turn, self, other, damage) - 1;
            until = std::min(until, f.next_cast);
        }
        self.quiet_until = until;
    } else {
        const unsigned skip = stun_skips(self, turn);
        self.stunned = 0;
        int until = std::numeric_limits<int>::max(), quiet_hits = 0;
        float quiet = 0;
        const int count = self.count;
        for (int i = 0; i < count; ++i) {
            auto& f = self.fighters[i];
            if (f.shield_until <= turn) f.shield = 0, f.shield_until = never, self.lowered(i);
            if (f.health <= 0) continue;
            if (f.arrives_at <= turn && !(skip >> i & 1)) hits += attack(f, turn, self, other, damage);
            until = std::min(until, f.shield_until);
            if (f.arrives_at > turn + 1) {
                until = std::min(until, f.arrives_at);
                continue;
            }
            quiet += f.strength;
            ++quiet_hits;
            until = std::min(until, f.next_cast);
        }
        self.quiet_until = until;
        self.quiet_alive = self.alive;
        self.quiet_damage = quiet;
        self.quiet_hits = quiet_hits;
    }
    const int target = other.weakest();
    if (target < 0) return damage;
    const float back = other.fighters[target].retaliation;
    other.hurt(damage, target);
    if (back > 0) self.hurt(static_cast<float>(hits) * back);
    return damage;
}

// hurt() of `d` on the weakest, with its shield and health in `shield` and `health`: false if it
// would fall.
[[gnu::always_inline]] inline bool takes(float d, float& shield, float& health) {
    if (!(d > 0)) return true;
    const float absorbed = std::min(d, shield);
    shield -= absorbed;
    d -= absorbed;
    if (!(d < health)) return false;
    health -= d;
    return true;
}

// play_quiet() with a weakest shielded.
[[gnu::noinline]] int play_shielded(Side& us, Side& them, Fighter& u, Fighter& e, int t, int end, bool they_first, int& ours, int& theirs) {
    // Each as hurt() takes it, through the target's Durability.
    const float onto_them = u.retaliation > 0 ? static_cast<float>(them.quiet_hits) * u.retaliation * e.taken : 0.0f;
    const float onto_us = e.retaliation > 0 ? static_cast<float>(us.quiet_hits) * e.retaliation * u.taken : 0.0f;
    const float camp = us.camp * u.taken, on_us = them.quiet_damage * u.taken, on_them = us.quiet_damage * e.taken;
    for (; t < end; ++t) {
        float us_ = u.shield, uh = u.health, es = e.shield, eh = e.health;
        if ((t % 2 == 0) == they_first) {
            if (them.turn >= them.quiet_until || them.alive != them.quiet_alive || them.stunned != 0) break;
            if (!takes(on_us, us_, uh) || !takes(onto_them, es, eh) || !takes(camp, us_, uh)) break;
            ++them.turn;
            ++theirs;
        } else {
            if (us.turn >= us.quiet_until || us.alive != us.quiet_alive || us.stunned != 0) break;
            if (!takes(on_them, es, eh) || !takes(onto_us, us_, uh)) break;
            ++us.turn;
            ++ours;
        }
        u.shield = us_, u.health = uh, e.shield = es, e.health = eh;
    }
    return t;
}

// The half-turns from `t` (to `end` at most) in which both sides only make their basic attacks
// and nobody falls, each taken off the side's weakest as act() and hurt() would; returns the next.
int play_quiet(Side& us, Side& them, int t, int end, bool they_first, int& ours, int& theirs) {
    const int wu = us.weakest(), we = them.weakest();
    if (wu < 0 || we < 0) return t;
    auto& u = us.fighters[wu];
    auto& e = them.fighters[we];
    if (u.shield != 0 || e.shield != 0) return play_shielded(us, them, u, e, t, end, they_first, ours, theirs);
    // Each as hurt() takes it, through the target's Durability.
    const float onto_them = u.retaliation > 0 ? static_cast<float>(them.quiet_hits) * u.retaliation * e.taken : 0.0f;
    const float onto_us = e.retaliation > 0 ? static_cast<float>(us.quiet_hits) * e.retaliation * u.taken : 0.0f;
    const float camp = us.camp * u.taken;
    for (; t < end; ++t) {
        if ((t % 2 == 0) == they_first) {
            if (them.turn >= them.quiet_until || them.alive != them.quiet_alive || them.stunned != 0) break;
            const float d = them.quiet_damage * u.taken;
            if (!(d < u.health) || !(onto_them < e.health)) break;
            const float h = u.health - d;
            if (camp > 0 && !(camp < h)) break;
            u.health = camp > 0 ? h - camp : h;
            if (onto_them > 0) e.health -= onto_them;
            ++them.turn;
            ++theirs;
        } else {
            if (us.turn >= us.quiet_until || us.alive != us.quiet_alive || us.stunned != 0) break;
            const float d = us.quiet_damage * e.taken;
            if (!(d < e.health) || !(onto_us < u.health)) break;
            e.health -= d;
            if (onto_us > 0) u.health -= onto_us;
            ++us.turn;
            ++ours;
        }
    }
    return t;
}

// Own turns a fight is played for: every slot ready at the start is cast on turns 0, 8 and 16.
// Measured at 100M on the worst maps, kills land just after those casts (peaks on turns 9 and 17),
// and the 8% of fights still undecided at 24 turns cost 20% of the simulation fuel.
constexpr int fight_horizon = 2 * ability_cooldown + 1;

// Our fighter's health, as its linked body's falls with it.
float watched_health(const Side& us, int self) {
    const auto& me = us.fighters[self];
    return me.link >= 0 ? std::min(me.health, us.fighters[me.link].health) : me.health;
}

// The least damage that fells every member of ours: each one's health, but a linked pair falls
// with the first of its bodies.
float side_health(const Side& us) {
    float total = 0, linked = std::numeric_limits<float>::max();
    for (int i = 0; i < us.count; ++i)
        if (const auto& f = us.fighters[i]; f.health <= 0) continue;
        else if (f.link >= 0) linked = std::min(linked, f.health);
        else total += f.health;
    return linked < std::numeric_limits<float>::max() ? total + linked : total;
}

// The most their side can deal ours over the rest of the fight, `horizon` turns each: every member
// alive now attacking each turn and casting each slot as soon as it is ready, Ren hitting back at
// each of our next `ours` hits, and the camps.
struct Cap {
    float rate = 0, rest = 0; // a turn of theirs, and the casts and Ren
    float weakest = std::numeric_limits<float>::max(); // their weakest's health
    // Over their next `theirs` turns, with room for rounding, it falls short of `health`.
    bool short_of(int theirs, float health) const { return (static_cast<float>(theirs) * rate + rest) * 1.001f + 1.0f < health; }
};
Cap their_cap(const Side& us, const Side& them, int horizon, int ours) {
    Cap c;
    float strength = 0, casts = 0, back = 0;
    for (int i = 0; i < them.count; ++i) {
        const auto& f = them.fighters[i];
        if (f.health <= 0) continue;
        strength += f.strength;
        c.weakest = std::min(c.weakest, f.health);
        back = std::max(back, f.retaliation);
        for (int s = 0; s < 2; ++s)
            if (const int first = std::max(them.turn, f.ready_at[s]); first < horizon)
                casts += static_cast<float>((horizon - first + ability_cooldown - 1) / ability_cooldown) * f.kit->cast[s].damage;
    }
    c.rate = us.camp + strength;
    c.rest = back > 0 ? casts + static_cast<float>(2 * ours * us.alive) * back : casts;
    return c;
}

// Whether their side must take all of ours within their next `theirs` turns. We cannot fell any of
// theirs in our next `ours`: every attack and cast of ours as soon as ready, and our Ren hitting
// back at each of their hits, fall short of their weakest. Then their basic attacks alone, less a
// turn of their strongest for each stun we could cast, and the camps, outweigh our health, shields
// and every heal or shield we could cast.
bool overwhelmed(const Side& us, const Side& them, int theirs, int ours) {
    const int our_end = us.turn + ours;
    float most = 0, guard = 0, back = 0, taken = 1;
    int stuns = them.stunned;
    for (int i = 0; i < us.count; ++i) {
        const auto& f = us.fighters[i];
        if (f.health <= 0) continue;
        back = std::max(back, f.retaliation);
        taken = std::min(taken, f.taken);
        guard += f.health + f.shield;
        if (f.arrives_at == never) continue;
        most += static_cast<float>(ours) * f.strength;
        for (int s = 0; s < 2; ++s)
            if (const int first = std::max(us.turn, f.ready_at[s]); f.ready_at[s] != never && first < our_end) {
                const int n = (our_end - first + ability_cooldown - 1) / ability_cooldown;
                const auto& c = f.kit->cast[s];
                most += static_cast<float>(n) * c.damage;
                guard += static_cast<float>(n) * c.heal;
                stuns += c.stuns ? n : 0;
            }
    }
    if (back > 0) most += static_cast<float>(2 * theirs * them.alive) * back;
    float weakest = std::numeric_limits<float>::max(), least = static_cast<float>(theirs) * us.camp, strongest = 0;
    for (int i = 0; i < them.count; ++i) {
        const auto& f = them.fighters[i];
        if (f.health <= 0) continue;
        weakest = std::min(weakest, f.health);
        if (!f.stun_immune) strongest = std::max(strongest, f.strength);
        if (f.arrives_at == never) continue;
        least += static_cast<float>(std::max(0, theirs - std::max(0, f.arrives_at - them.turn))) * f.strength;
    }
    if (!(most * 1.001f + 1.0f < weakest)) return false;
    least -= static_cast<float>(stuns) * strongest;
    // Our Durability takes at most this off each hit.
    least *= taken;
    return least > guard * 1.001f + 1.0f;
}

// A lower bound on the damage overwhelmed() sums, every other term of which is at least 0: our
// arriving members' Strength each of our turns. Past their weakest, overwhelmed() is false.
float our_strength(const Side& us) {
    float total = 0;
    for (int i = 0; i < us.count; ++i)
        if (const auto& f = us.fighters[i]; f.health > 0 && f.arrives_at != never) total += f.strength;
    return total;
}

// Turns each side needs to empty the other's pool, within `horizon` turns each, playing the fight
// out on the sides given. `self_falls`: whether our own fighter dies before their side does.
// `dealt`, for debug_fights: their first turn's damage, ours, then their first five turns', ours.
// {-1, -1} if the fuel left fell below `fuel_floor` first. With `self_falls` and not Dealt, a fight
// our fighter (or, once it has fallen, the rest of ours) must outlive ends at once as {0, 0}, and
// one they must win as {0, horizon}. With `falls_unknown` too, a fight the rest of ours must outlive
// ends as {0, 0}, setting it and leaving self_falls unknown.
template <bool Dealt = false>
std::pair<int, int> simulate(Side& us, Side& them, bool they_first, bool* self_falls = nullptr, int horizon = fight_horizon,
                             std::array<float, 4>* dealt = nullptr, std::uint64_t fuel_floor = 0, bool* falls_unknown = nullptr) {
    int ours = 0, theirs = 0;
    int watched = self_falls ? us.self : -1;
    // Asked at the start and as either side loses a member.
    for (int t = 0, alive = -1; t < 2 * horizon; ++t) {
        if (!Dealt && self_falls && us.alive + 16 * them.alive != alive) {
            alive = us.alive + 16 * them.alive;
            const int theirs_left = horizon - theirs, ours_left = horizon - ours;
            const auto cap = their_cap(us, them, horizon, ours_left);
            // Our fighter outlives the fight or, once it has fallen, the rest of ours do.
            if (cap.short_of(theirs_left, watched >= 0 ? watched_health(us, watched) : side_health(us))) return {0, 0};
            // Asked only whether we lose: the rest of ours outlive it.
            if (falls_unknown && watched >= 0 && cap.short_of(theirs_left, side_health(us))) return *falls_unknown = true, std::pair{0, 0};
            if (static_cast<float>(ours_left) * our_strength(us) < cap.weakest) {
                if (overwhelmed(us, them, theirs_left, ours_left)) {
                    if (watched >= 0) *self_falls = true;
                    return {0, horizon};
                }
            } else if constexpr (!Dealt) {
                debug_block({
                    if (overwhelmed(us, them, theirs_left, ours_left)) std::printf("PREFILTER-MISMATCH %d overwhelmed\n", cambc::round_number());
                });
            }
        }
        if (!Dealt && us.turn < us.quiet_until && them.turn < them.quiet_until) {
            t = play_quiet(us, them, t, 2 * horizon, they_first, ours, theirs);
            if (t == 2 * horizon) break;
        }
        if (t % 8 == 7) {
            if constexpr (!Dealt) throw_if_stale();
            if (fuel_floor && fuel() < fuel_floor) return {-1, -1};
        }
        const bool their_turn = (t % 2 == 0) == they_first;
        if (their_turn) {
            const float d = act(them, us);
            if constexpr (Dealt)
                if (theirs < 5) (*dealt)[2] += d, (*dealt)[0] += theirs == 0 ? d : 0;
            if (us.camp > 0) us.hurt(us.camp);
            ++theirs;
        } else {
            const float d = act(us, them);
            if constexpr (Dealt)
                if (ours < 5) (*dealt)[3] += d, (*dealt)[1] += ours == 0 ? d : 0;
            ++ours;
        }
        // Ren's reflection can fell the side whose turn it is.
        if (watched >= 0 && us.fighters[watched].health <= 0) *self_falls = true, watched = -1;
        if (us.alive == 0) return {0, std::max(1, theirs)};
        if (them.count > 0 && them.alive == 0) return {std::max(1, ours), 0};
    }
    return {0, 0};
}

constinit std::array<Side, 2> debug_sides{};

// Only the order where they strike first: `lost` is all callers need.
// Plays the fight out on the sides given, which callers discard: copying them is costly.
Trade trade(Side& us, Side& them, std::uint64_t fuel_floor = 0, bool they_first = true, bool need_falls = true) {
    Trade t;
    t.allies = us.count;
    t.enemies = them.count;
    if constexpr (debug_fights) t.our_health = us.health(), t.their_health = them.health();
    if (them.count == 0) return t;
    debug_block({ debug_sides = {us, them}; });
    bool unknown = false;
    const auto [we_kill, they_kill] = simulate<debug_fights>(us, them, they_first, &t.self_falls, fight_horizon, debug_fights ? &t.dealt : nullptr, fuel_floor,
                                                             need_falls ? nullptr : &unknown);
    t.falls_known = !unknown;
    debug_block({
        // An early end (outlives, overwhelmed) must agree with the fight played out.
        bool falls = false;
        std::array<float, 4> dealt{};
        const auto [a, b] = simulate<true>(debug_sides[0], debug_sides[1], they_first, &falls, fight_horizon, &dealt);
        if (we_kill >= 0 && ((b > 0) != (they_kill > 0) || (t.falls_known && falls != t.self_falls)))
            std::printf("FIGHT-EXIT-MISMATCH %d %d %d %d %d\n", cambc::round_number(), b, they_kill, falls, t.self_falls);
    });
    if (we_kill < 0) {
        note_shortcut("fight-cut");
        t.lost = t.self_falls = true;
        return t;
    }
    t.turns_to_kill_them = we_kill;
    t.turns_to_kill_us = they_kill;
    t.lost = they_kill > 0;
    return t;
}

// Us, and the allies we see within fight_ally_radius of p: bit i for allies[i]. Beliefs are fixed
// for the turn, so who could join is read once.
std::uint32_t fighting_allies(const World& world, vec2 p) {
    static int round = -1;
    static std::uint32_t self = 0, seen = 0;
    // The corner of each one's square within fight_ally_radius: p is in it when both offsets from
    // the corner, unsigned, are at most its side.
    static std::array<int, 16> x0, y0;
    if (round != world.round) {
        round = world.round;
        self = seen = 0;
        for (std::size_t i = 0; i < world.allies.size() && i < x0.size(); ++i) {
            const auto& a = world.allies[i];
            if (!a.alive) continue;
            if (a.is_self) self |= 1u << i;
            else if (a.visible) seen |= 1u << i, x0[i] = a.pos.x - fight_ally_radius, y0[i] = a.pos.y - fight_ally_radius;
        }
    }
    std::uint32_t out = self;
    constexpr unsigned side = 2 * fight_ally_radius;
    for (unsigned left = seen; left; left &= left - 1) {
        const int i = std::countr_zero(left);
        const bool in = static_cast<unsigned>(p.x - x0[static_cast<std::size_t>(i)]) <= side;
        if (in & (static_cast<unsigned>(p.y - y0[static_cast<std::size_t>(i)]) <= side)) out |= 1u << i;
    }
    return out;
}

// A stun that will take its next turn. One at 0 turn ends left has already taken a turn and
// expires at the next one's start.
std::optional<bool> stun_pending(cambc::handle_champion_t c) {
    static std::array<cambc::detail::buff_data, static_cast<std::size_t>(cambc::buff_types::count)> buffs;
    std::uint32_t n = 0;
    const auto code = cambc::detail::sdk_champion_buff_data(static_cast<std::uint32_t>(c), buffs.data(), static_cast<std::uint32_t>(buffs.size()), &n);
    if (code == static_cast<std::int32_t>(cambc::error_code::api_not_in_vision)) return std::nullopt;
    ok(code);
    for (std::uint32_t i = 0; i < n && i < buffs.size(); ++i)
        if (buffs[i].type == static_cast<std::uint32_t>(cambc::buff_types::stun)) return buffs[i].data.stun.duration > 0;
    return false;
}

[[gnu::noinline]] void make_slot(const World& world, const ChampionBelief& c, int slot) {
    auto& m = made_fighters;
    const std::array<std::uint32_t, 3> from{static_cast<std::uint32_t>(c.type), std::bit_cast<std::uint32_t>(hit_strength(c)),
                                            std::bit_cast<std::uint32_t>(hit_focus(c))};
    if (!(m.kits >> slot & 1) || m.kit_of[slot] != from) {
        m.kits |= 1u << slot;
        m.kit_of[slot] = from;
        make_kit(c, m.kit[slot]);
    }
    if (c.side == team::enemy || c.is_self || !c.alive || !c.visible) {
        make_fighter(c, c.is_self ? world.round : next_turn_round(world, c), m.fighter[slot], m.kit[slot]);
        return;
    }
    // An ally in sight joins from its next turn, but loses it to a stun and its turns until it lands
    // to a teleport: counted from that turn, not from the landing next_turn_round() gives.
    const int next = c.acted ? world.round + 1 : world.round;
    auto& f = m.fighter[slot];
    make_fighter(c, next, f, m.kit[slot]);
    if (c.teleport_pending()) f.arrives_at = std::max(0, c.channel_end_round - next);
    else if (c.facts().passive != Passive::stun_immune) {
        // Our move can hide a believed-visible ally: unknown stun must not promise its next turn.
        const auto pending = stun_pending(c.handle);
        if (!pending || *pending) f.arrives_at = 1;
    }
}

// `made`: bit i, Fighters::fighter[i] is this turn's.
const Fighter& fighter(const World& world, const ChampionBelief& c, std::uint32_t& made) {
    const int slot = (c.side == team::enemy ? 16 : 0) + c.index;
    if (!(made >> slot & 1)) made |= 1u << slot, make_slot(world, c, slot);
    return made_fighters.fighter[slot];
}

// An empty side's members, bit i for from[i]: Side::add() for each, kept in locals.
void fill(Side& side, const World& world, const std::vector<ChampionBelief>& from, unsigned bits, std::uint32_t& made) {
    int count = 0, alive = 0;
    bool plain = true;
    for (; bits && count < max_fighters; bits &= bits - 1) {
        const auto& c = from[static_cast<std::size_t>(std::countr_zero(bits))];
        if (c.is_self) side.self = count;
        auto& g = side.fighters[count];
        g = fighter(world, c, made);
        plain = plain && g.kit->plain && g.arrives_at == 0;
        if (g.linked)
            for (int i = 0; i < count; ++i)
                if (side.fighters[i].linked) g.link = i, side.fighters[i].link = count;
        alive += g.health > 0;
        ++count;
    }
    side.count = count;
    side.alive = alive;
    side.plain = plain;
}

void join_allies(const World& world, Side& us, vec2 p, std::uint32_t& made) { fill(us, world, world.allies, fighting_allies(world, p), made); }

} // namespace

int next_turn_round(const World& world, const ChampionBelief& c) {
    // Read for those in sight; ranks are a guess when priorities change unseen.
    if (c.teleport_pending()) return std::max(c.acted ? world.round + 1 : world.round, c.channel_end_round);
    if (c.visible && !c.is_self) return c.acted ? world.round + 1 : world.round;
    return world.slot(c, world.round) > world.slot(world.me(), world.round) ? world.round : world.round + 1;
}

namespace {

// Slot bit i: ability i counts.
Strike compute_strike(const ChampionFacts& f, float s, float focus, unsigned slots) {
    const int range = f.attack_range();
    // Varg's basic attack reaches a tile through a target beside it.
    const int basic = range + (f.passive == Passive::splash_attack ? 1 : 0);
    const int walk = f.ranged ? 0 : 1; // a ranged champion's walk spends its attack
    Strike out;
    const auto add = [&](int reach, float damage, bool stuns) {
        reach = std::min(reach, Strike::max_reach);
        for (int d = 0; d <= reach; ++d) {
            out.damage[d] = std::max(out.damage[d], damage);
            out.stuns[d] = out.stuns[d] || stuns;
        }
        out.reach = std::max(out.reach, reach);
    };
    add(basic + walk, s, false);
    for (int slot = 0; slot < 2; ++slot) {
        if (!(slots >> slot & 1)) continue;
        const auto& a = f.abilities[slot];
        switch (a.kind) {
        case AbilityKind::attack_reset:
            add(basic + walk, 2 * s, a.stuns);
            if (f.ranged) add(basic + 1, s, a.stuns); // walk, reset, attack
            break;
        case AbilityKind::dash:
            add(basic + walk + 2, s, false);
            if (a.lands()) {
                // The landing, then a basic attack from it.
                add(walk + a.reach(), a.multiplier * focus, a.stuns);
                add(walk + 2 + std::min(range, a.radius), a.multiplier * focus + s, a.stuns);
            }
            break;
        case AbilityKind::damage:
            // Excludes walking but not the basic attack.
            add(a.reach(), a.multiplier * focus, a.stuns);
            add(range, a.multiplier * focus + s, a.stuns);
            break;
        case AbilityKind::stun: add(a.reach() + (a.excludes_walking ? 0 : 1), 0, true); break;
        default: break;
        }
    }
    return out;
}

// Called many times a turn for the same few champions: the last result per champion is kept,
// keyed by everything it depends on, and its widening to two turns once threat_strike() asks.
struct StrikeMemo {
    bool valid;
    cambc::champion_type type;
    std::uint32_t strength, focus;
    Strike value;
    bool widened_known;
    std::uint8_t slots, widened_slots; // widened_slots: the second turn's
    Strike widened;
};

// Static storage starts zeroed, and a zeroed memo is not valid: no constructor writes it all on
// first use.
union StrikeMemos {
    constexpr StrikeMemos() {}
    std::array<std::array<StrikeMemo, 4>, 16> by_champion;
};

StrikeMemo& strike_memo(const ChampionBelief& c, int turn_round) {
    // By champion and slots ready: cooldowns run out and come back.
    static StrikeMemos memo;
    const bool uncertain = c.cooldowns_uncertain();
    const unsigned slots =
        (uncertain || c.ability_ready(0, turn_round) ? 1u : 0u) | (uncertain || c.ability_ready(1, turn_round) ? 2u : 0u);
    const float hs = hit_strength(c), hf = hit_focus(c);
    const auto s = std::bit_cast<std::uint32_t>(hs), focus = std::bit_cast<std::uint32_t>(hf);
    auto& m = memo.by_champion[(c.side == team::enemy ? 8u : 0u) + (static_cast<unsigned>(c.index) & 7u)][slots];
    if (!m.valid || m.type != c.type || m.strength != s || m.focus != focus) {
        m.valid = true;
        m.type = c.type;
        m.strength = s;
        m.focus = focus;
        m.value = compute_strike(c.facts(), hs, hf, slots);
        m.slots = static_cast<std::uint8_t>(slots);
        m.widened_known = false;
    }
    return m;
}

} // namespace

const Strike& strike(const ChampionBelief& c, int turn_round) { return strike_memo(c, turn_round).value; }

int turns_before_ours(const World& world, const ChampionBelief& c) {
    const auto& me = world.me();
    const bool now = c.visible ? !c.acted : world.slot(c, world.round) > world.slot(me, world.round);
    // A teleport's channel turns are not its own.
    const int from = c.teleport_pending() ? c.channel_end_round : world.round;
    return (now && from <= world.round ? 1 : 0) + (from <= world.round + 1 && world.slot(c, world.round + 1) < world.slot(me, world.round + 1) ? 1 : 0);
}

namespace {

// threat_strike()'s damage at distance 0 with both slots ready and two turns: at least what it
// can be on any turn. Kept per champion by what it depends on.
float most_damage(const ChampionBelief& c) {
    struct Memo {
        cambc::champion_type type;
        std::uint32_t strength, focus;
        bool known = false;
        float damage;
    };
    static std::array<Memo, 8> memo;
    const float hs = hit_strength(c), hf = hit_focus(c);
    const auto s = std::bit_cast<std::uint32_t>(hs), focus = std::bit_cast<std::uint32_t>(hf);
    auto& m = memo[static_cast<unsigned>(c.index) & 7u];
    if (!m.known || m.type != c.type || m.strength != s || m.focus != focus) {
        const auto k = compute_strike(c.facts(), hs, hf, 3u);
        m = {c.type, s, focus, true, k.hits(0) ? k.at(0) + hs : 0.0f};
    }
    return m.damage;
}

} // namespace

const Strike& threat_strike(const World& world, const ChampionBelief& c) {
    static const Strike none;
    if (c.teleport_pending() && turns_before_ours(world, c) == 0) return none;
    const int round = next_turn_round(world, c);
    auto& m = strike_memo(c, round);
    const auto& s = m.value;
    if (s.reach < 0 || turns_before_ours(world, c) < 2) return s;
    // Its second turn falls in the next round: a walk first, then what is ready by then.
    const auto& m2 = strike_memo(c, round + 1);
    const auto& s2 = m2.value;
    if (m.widened_known && m.widened_slots == m2.slots) return m.widened;
    m.widened_known = true;
    m.widened_slots = m2.slots;
    const auto& f = c.facts();
    const int basic_reach = f.attack_range() + (f.passive == Passive::splash_attack ? 1 : 0) + (f.ranged ? 0 : 1);
    auto& out = m.widened;
    for (int d = 0; d <= Strike::max_reach; ++d) {
        const float walked = s2.at(std::max(0, d - 1));
        const float twice = s.hits(d) ? s.at(d) + (d <= basic_reach ? hit_strength(c) : 0.0f) : 0.0f;
        out.damage[d] = std::max(walked, twice);
        out.stuns[d] = s2.stuns[std::max(0, d - 1)]; // s2.stuns holds from 0 out to some distance
    }
    out.reach = std::min(Strike::max_reach, s2.reach + 1);
    return out;
}

namespace {

// Window arithmetic by tables where it can: WASM loops and variable shifts cost fuel.
using Window = Reach::Window;
constexpr int win_r = 4, win_n = 2 * win_r + 1;
constexpr Window win_full = ~Window{};
constexpr Window win_bit(int x, int y) { return Window::bit(y * win_n + x); }

struct Tables {
    // [a][b]: columns (rows) a to b of the window; empty if a > b.
    std::array<std::array<Window, win_n>, win_n> columns{}, rows{};
    std::array<Window, win_r + 1> square{}; // [k]: within k of the centre
    std::array<Window, win_n * win_n> bits{};
    // [c + win_n][r]: the columns (rows) within r of column (row) c, which may lie outside the window.
    std::array<std::array<Window, win_n>, 3 * win_n> column_spans{}, row_spans{};
};

constexpr Tables tables = [] {
    Tables t;
    for (int y = 0; y < win_n; ++y)
        for (int x = 0; x < win_n; ++x) t.bits[static_cast<std::size_t>(y * win_n + x)] = win_bit(x, y);
    for (int a = 0; a < win_n; ++a)
        for (int b = a; b < win_n; ++b)
            for (int i = a; i <= b; ++i)
                for (int j = 0; j < win_n; ++j) {
                    t.columns[a][b] |= win_bit(i, j);
                    t.rows[a][b] |= win_bit(j, i);
                }
    for (int k = 0; k <= win_r; ++k) t.square[k] = t.columns[win_r - k][win_r + k] & t.rows[win_r - k][win_r + k];
    for (int c = -win_n; c < 2 * win_n; ++c)
        for (int r = 0; r < win_n; ++r) {
            const int a = std::max(0, c - r), b = std::min(win_n - 1, c + r);
            if (a > b) continue;
            t.column_spans[c + win_n][r] = t.columns[a][b];
            t.row_spans[c + win_n][r] = t.rows[a][b];
        }
    return t;
}();

Window dilate(Window s) {
    const Window h = s | (s.shl(1) & ~tables.columns[0][0]) | (s.shr(1) & ~tables.columns[win_n - 1][win_n - 1]);
    return h | h.shl(win_n) | h.shr(win_n);
}

// The window tiles within r of window tile (cx, cy), which may lie outside it: -win_n <= cx, cy <
// 2 * win_n and r < win_n.
Window box(int cx, int cy, int r) {
    return tables.column_spans[static_cast<std::size_t>(cx + win_n)][static_cast<std::size_t>(r)]
           & tables.row_spans[static_cast<std::size_t>(cy + win_n)][static_cast<std::size_t>(r)];
}

// A mask laid out around tile q, read in the window around q - (dx, dy).
Window shift(Window m, int dx, int dy) {
    if (dx <= -win_n || dx >= win_n || dy <= -win_n || dy >= win_n) return {};
    const int k = dx + win_n * dy;
    m = k >= 0 ? m.shl(k) : m.shr(-k);
    if (dx > 0) m &= ~tables.columns[0][dx - 1];
    if (dx < 0) m &= ~tables.columns[win_n + dx][win_n - 1];
    return m;
}

// Static terrain as packed bits, read a window row at a time without host calls (host tests if
// the layout is unclear).
struct Terrain {
    static constexpr std::size_t bytes = 100 * 100 / 8 + 8;
    bool ready = false, packed = false;
    int width = 0, height = 0;
    const StaticMap* map = nullptr;
    std::array<std::uint8_t, bytes> walls, blocked, bushes, camps;

    static bool bit(const std::array<std::uint8_t, bytes>& b, int i) { return b[static_cast<std::size_t>(i >> 3)] >> (i & 7) & 1; }
    // Bit k: tile (x0 + k, y), for the window's width.
    std::uint32_t row(const std::array<std::uint8_t, bytes>& b, int x0, int y) const {
        if (y < 0 || y >= height) return 0;
        const int lo = std::max(0, -x0), hi = std::min(win_n, width - x0);
        if (lo >= hi) return 0;
        const int i = x0 + lo + y * width;
        std::uint64_t word;
        std::memcpy(&word, &b[static_cast<std::size_t>(i >> 3)], sizeof word);
        return static_cast<std::uint32_t>((word >> (i & 7)) & ((std::uint64_t{1} << (hi - lo)) - 1)) << lo;
    }
    bool test(const std::array<std::uint8_t, bytes>& b, const bitboard& board, vec2 p) const {
        return packed ? bit(b, p.x + p.y * width) : aph::test(board, p);
    }
    bool bush(vec2 p) const { return test(bushes, map->bushes, p); }
    bool any_near(const std::array<std::uint8_t, bytes>& b, vec2 p) const {
        for (int y = p.y - win_r; y <= p.y + win_r; ++y)
            if (row(b, p.x - win_r, y)) return true;
        return false;
    }
    bool inside(vec2 p) const { return p.x >= 0 && p.y >= 0 && p.x < width && p.y < height; }

    // Board storage read in place, when probes confirm it: a word per 8x8 chunk, `across` chunks
    // a row, bit 8 * (y % 8) + x % 8.
    bool chunked = false;
    int across = 0;
    // The window around p (inside the map) of board `words`: it lies within 2x2 chunks.
    Reach::Window chunk_window(const std::uint64_t* words, vec2 p) const {
        const int x0 = p.x - 4, y0 = p.y - 4;
        const int lo = std::max(0, -x0), hi = std::min(9, width - x0);
        const std::uint32_t columns = ((1u << hi) - 1) & ~((1u << lo) - 1);
        const int a = x0 >> 3, s = x0 - 8 * a, c = y0 >> 3;
        const int down = (height + 7) / 8;
        const auto word = [&](int cy, int cx) -> std::uint64_t {
            return cy >= 0 && cy < down && cx >= 0 && cx < across ? words[static_cast<std::size_t>(cy * across + cx)] : 0;
        };
        const std::uint64_t w00 = word(c, a), w01 = word(c, a + 1), w10 = word(c + 1, a), w11 = word(c + 1, a + 1);
        Reach::Window m;
        for (int r = 0; r < 9; ++r) {
            const int y = y0 + r;
            if (y < 0 || y >= height) continue;
            const bool second = (y >> 3) != c;
            const int shift = 8 * (y & 7);
            const auto seg = static_cast<std::uint32_t>(((second ? w10 : w00) >> shift) & 0xFF)
                             | static_cast<std::uint32_t>(((second ? w11 : w01) >> shift) & 0xFF) << 8;
            const std::uint64_t bits = (seg >> s) & columns;
            const int b = 9 * r;
            if (b < 64) {
                m.lo |= bits << b;
                if (b > 55) m.hi |= bits >> (64 - b);
            } else {
                m.hi |= bits << (b - 64);
            }
        }
        return m;
    }
};

void check_chunks(Terrain& t) {
    const auto words = bitboard::raw_buffer_size() / 8;
    bitboard b;
    t.across = (t.width + 7) / 8;
    if (t.height > 8) {
        b.set({0, 8});
        int found = -1;
        for (std::size_t i = 0; i < words; ++i)
            if (b.ptr()[i] != 0) found = found < 0 ? static_cast<int>(i) : -2;
        if (found <= 0) return;
        t.across = found;
    }
    if (static_cast<std::size_t>(t.across * ((t.height + 7) / 8)) > words) return;
    const std::array<vec2, 8> probes{vec2{0, 0}, {1, 0}, {0, 1}, {7, 7}, {std::min(8, t.width - 1), 0}, {std::min(9, t.width - 1), std::min(10, t.height - 1)}, {t.width - 1, t.height - 1}, {t.width / 2 + 3, t.height / 2 + 5}};
    for (const vec2 p : probes) {
        b.clear();
        b.set(p);
        const auto at = static_cast<std::size_t>((p.y >> 3) * t.across + (p.x >> 3));
        if (b.ptr()[at] != std::uint64_t{1} << (8 * (p.y & 7) + (p.x & 7))) return;
    }
    t.chunked = true;
}

Terrain terrain_storage;

[[gnu::noinline]] void make_terrain(Terrain& t, const StaticMap& map) {
    t.ready = true;
    t.map = &map;
    t.width = map.width;
    t.height = map.height;
    check_chunks(t);
    const std::size_t size = bitboard::linear_buffer_size();
    if (size + 8 > Terrain::bytes) return;
    map.walls.export_linear_buffer({t.walls.data(), size});
    // Bits run from the low end of each byte; check on a set tile.
    if (!map.walls.is_empty()) {
        const vec2 probe = first_tile(map.walls);
        if (!Terrain::bit(t.walls, probe.x + probe.y * t.width)) return;
    }
    map.blocked_for_them.export_linear_buffer({t.blocked.data(), size});
    map.bushes.export_linear_buffer({t.bushes.data(), size});
    map.camp_tiles.export_linear_buffer({t.camps.data(), size});
    t.packed = true;
}

const Terrain& terrain(const StaticMap& map) {
    if (!terrain_storage.ready) make_terrain(terrain_storage, map);
    return terrain_storage;
}

// By group: the box around its members, as x0, x1, y0, y1.
const std::vector<std::array<int, 4>>& member_boxes(const StaticMap& map) {
    static std::vector<std::array<int, 4>> boxes;
    if (boxes.empty())
        for (const auto& g : map.groups) {
            std::array<int, 4> b{1 << 20, -(1 << 20), 1 << 20, -(1 << 20)};
            for (const auto& m : g.members)
                b = {std::min(b[0], m.pos.x), std::max(b[1], m.pos.x), std::min(b[2], m.pos.y), std::max(b[3], m.pos.y)};
            boxes.push_back(b);
        }
    return boxes;
}

// By tile, once looked up: its camp group (-1 if none) and the index of the member on it.
struct CampTile {
    std::int16_t group;
    std::uint8_t member;
    bool known;
};
std::array<CampTile, 100 * 100> camp_tiles;

const CampTile& camp_tile(const World& world, vec2 p) {
    auto& t = camp_tiles[static_cast<std::size_t>(p.x + p.y * world.map().width)];
    if (!t.known) {
        t.known = true;
        t.group = static_cast<std::int16_t>(world.map().group_at(p));
        t.member = 255;
        if (t.group >= 0) {
            const auto& members = world.map().groups[t.group].members;
            for (std::size_t i = 0; i < members.size() && i < 255 && t.member == 255; ++i)
                if (members[i].pos == p) t.member = static_cast<std::uint8_t>(i);
        }
    }
    return t;
}

bool live_member(const World& world, int group, int member) {
    const auto& c = world.camps[static_cast<std::size_t>(group)];
    return c.state == CampState::alive && c.health[static_cast<std::size_t>(member)] > 0;
}

// The camp members on the camp tiles of the window around each tile, by window bit, found on its
// first build there: liveness is then read without looking each tile up. By tile, the first spot
// in the pool and the count + 1 (0: not yet found).
struct CampSpot {
    std::uint8_t bit, member;
    std::int16_t group;
};
std::vector<CampSpot> spot_pool;
std::array<std::uint32_t, 100 * 100> spots_from;
std::array<std::uint8_t, 100 * 100> spots_count;

// The enemy wards in our sight this round, by owner (its index among the enemies): what one sees
// is in its owner's sight alone (vision.personal). sdk_wards lists the wards in our own sight with
// their owners, and sdk_ward_vision is the engine's mask, bushes included (probe-ward-bush); a
// mask is cast again only when its ward moves.
struct Wards {
    static constexpr int slots = 8;
    int round = -1;
    std::uint8_t present = 0; // bit i: enemies[i]'s ward is in sight
    std::array<vec2, slots> cast_at;
    std::array<std::array<std::uint8_t, Terrain::bytes>, slots> bits; // when the terrain is packed
    std::vector<bitboard> boards;                                      // when it is not

    [[gnu::noinline]] void refresh(const World& world, const Terrain& t) {
        if (round < 0) cast_at.fill({-1, -1});
        round = world.round;
        present = 0;
        static std::array<cambc::detail::ward_info, 16> raw;
        std::uint32_t n = 0;
        ok(cambc::detail::sdk_wards(raw.data(), static_cast<std::uint32_t>(raw.size()), &n));
        const auto own = static_cast<std::uint32_t>(world.map().team_a ? 0 : 1);
        for (std::uint32_t k = 0; k < n && k < raw.size(); ++k) {
            const auto& w = raw[k];
            if (w.team == own) continue;
            int i = 0;
            while (i < static_cast<int>(world.enemies.size()) && static_cast<std::uint32_t>(world.enemies[static_cast<std::size_t>(i)].handle) != w.owner) ++i;
            if (i >= slots || i >= static_cast<int>(world.enemies.size())) continue;
            present |= static_cast<std::uint8_t>(1u << i);
            const vec2 at{w.x, w.y};
            if (cast_at[static_cast<std::size_t>(i)] == at) continue;
            cast_at[static_cast<std::size_t>(i)] = at;
            static bitboard cast{cambc::uninitialized};
            if (!t.packed && boards.empty()) boards.resize(slots);
            auto& out = t.packed ? cast : boards[static_cast<std::size_t>(i)];
            ok(cambc::detail::sdk_ward_vision(at.x, at.y, out.ptr()));
            if (t.packed) out.export_linear_buffer({bits[static_cast<std::size_t>(i)].data(), bitboard::linear_buffer_size()});
        }
    }
};

Wards enemy_wards;

// enemies[owner]'s index in enemy_wards if we see its ward this round, else -1.
int ward_of(const World& world, int owner) {
    auto& w = enemy_wards;
    if (w.round != world.round) w.refresh(world, terrain(world.map()));
    return owner >= 0 && owner < Wards::slots && (w.present >> owner & 1) ? owner : -1;
}

[[gnu::always_inline]] inline bool ward_sees(const Terrain& t, int ward, vec2 p) {
    const auto i = static_cast<std::size_t>(ward);
    return t.packed ? Terrain::bit(enemy_wards.bits[i], p.x + p.y * t.width) : test(enemy_wards.boards[i], p);
}

std::array<Window, 100 * 100> sight_masks;
std::array<std::uint8_t, 100 * 100> sight_known;

// Who sees p, laid out around p: within 1 (`far` false) or within win_r. Far masks depend only on
// terrain, so they are kept for the game.
Window sight(const World& world, vec2 p, bool far, bool store = true) {
    const auto& t = terrain(world.map());
    if (!far) {
        if (!t.bush(p)) return tables.square[1];
        // A bush tile is seen only from its own cluster; diagonal bushes join through a bush
        // beside both.
        Window m = win_bit(win_r, win_r);
        for (const vec2 d : directions) {
            const vec2 q = p + d;
            if (!t.inside(q) || !t.bush(q)) continue;
            if (d.x == 0 || d.y == 0 || t.bush({p.x + d.x, p.y}) || t.bush({p.x, p.y + d.y}))
                m |= win_bit(win_r + d.x, win_r + d.y);
        }
        return m;
    }
    auto& masks = sight_masks;
    auto& known = sight_known;
    const auto i = static_cast<std::size_t>(p.x + p.y * t.width);
    if (i < known.size() && known[i]) return masks[i];
    const auto& map = world.map();
    // Viewers outside bushes exactly; those inside one by walls alone, as finding the clusters can
    // cost tens of thousands: a viewer in another cluster, or behind bushes, may be counted.
    static bitboard viewers{cambc::uninitialized}, outside{cambc::uninitialized};
    Window m;
    // Without bushes in the square, walls alone decide; without walls too, all of it sees p.
    const bool plain = t.packed && !t.any_near(t.bushes, p);
    if (plain && !t.any_near(t.walls, p)) {
        m = tables.columns[std::max(0, win_r - p.x)][std::min(win_n - 1, win_r + t.width - 1 - p.x)]
            & tables.rows[std::max(0, win_r - p.y)][std::min(win_n - 1, win_r + t.height - 1 - p.y)];
    } else {
        shadow_into(map.walls, p, static_cast<std::uint16_t>(win_r), viewers);
        if (!plain) {
            and_into(viewers, map.bushes, viewers);
            if (!t.bush(p)) {
                shadow_into(map.walls_and_bushes, p, static_cast<std::uint16_t>(win_r), outside);
                drop(outside, map.bushes);
                or_into(viewers, outside, viewers);
            }
        }
        // The shadowcast square keeps them within win_r.
        if (t.chunked) {
            m = t.chunk_window(viewers.ptr(), p);
        } else {
            for (const vec2 q : Tiles<win_n * win_n>{viewers})
                m |= tables.bits[static_cast<std::size_t>((q.y - p.y + win_r) * win_n + q.x - p.x + win_r)];
        }
    }
    if (i < known.size() && store) masks[i] = m, known[i] = 1;
    return m;
}

} // namespace

Reach::Window attack_viewers(const World& world, vec2 target, int range, bool store) {
    range = std::clamp(range, 0, win_r);
    const Window near = sight(world, target, false) & tables.square[std::min(range, 1)];
    if (range <= 1) return near;
    const auto& t = terrain(world.map());
    if (!t.packed) return near;
    Window bush;
    for (int r = 0; r < win_n; ++r)
        if (const std::uint32_t bits = t.row(t.bushes, target.x - win_r, target.y - win_r + r)) bush |= Window{bits, 0}.shl(win_n * r);
    return (sight(world, target, true, store) & tables.square[range] & ~bush) | near;
}

namespace {

// sight() laid out around the enemy at p - (dx, dy). Out of line: inlined, the shift's constants
// were worked out on every Reach::at() call.
[[gnu::noinline]] Window sight_from(const World& world, vec2 p, bool far, int dx, int dy) { return shift(sight(world, p, far), dx, dy); }

// Static terrain around each tile, kept for the game: enemies keep to a few tiles. pass: a dash
// path may cross it; land: open to them; camps: camp tiles, whose monsters block while alive.
struct StaticWindow {
    Window pass, land, camps;
};

std::array<StaticWindow, 100 * 100> statics;
std::array<std::uint8_t, 100 * 100> statics_scanned;

const StaticWindow& static_window(const World& world, vec2 origin) {
    auto& scanned = statics_scanned;
    const auto& t = terrain(world.map());
    const auto oi = static_cast<std::size_t>(origin.x + origin.y * t.width);
    auto& st = statics[oi];
    if (scanned[oi]) return st;
    scanned[oi] = 1;
    const int x0 = origin.x - win_r;
    const int lo = std::max(0, -x0), hi = std::min(win_n, t.width - x0);
    const std::uint32_t columns = lo >= hi ? 0u : ((1u << hi) - 1) & ~((1u << lo) - 1);
    const std::uint64_t width_mask = lo >= hi ? 0 : (std::uint64_t{1} << (hi - lo)) - 1;
    Window pass, land, camps;
    // Unrolled, so that each row's place in the window is a constant shift.
    [&]<int... Row>(std::integer_sequence<int, Row...>) {
        (
            [&] {
                const int y = origin.y - win_r + Row;
                std::uint32_t open = 0, through = 0, camp = 0;
                if (t.packed) {
                    if (columns != 0 && y >= 0 && y < t.height) {
                        // Terrain::row() of each board, sharing the word offset.
                        const int i = x0 + lo + y * t.width;
                        const auto at = static_cast<std::size_t>(i >> 3);
                        const int shift = i & 7;
                        std::uint64_t walls, blocked, camps;
                        std::memcpy(&walls, &t.walls[at], sizeof walls);
                        std::memcpy(&blocked, &t.blocked[at], sizeof blocked);
                        std::memcpy(&camps, &t.camps[at], sizeof camps);
                        through = columns & ~(static_cast<std::uint32_t>((walls >> shift) & width_mask) << lo);
                        open = columns & ~(static_cast<std::uint32_t>((blocked >> shift) & width_mask) << lo);
                        camp = static_cast<std::uint32_t>((camps >> shift) & width_mask) << lo;
                    }
                } else {
                    for (int k = 0; k < win_n; ++k) {
                        const vec2 p{x0 + k, y};
                        if (!t.inside(p) || test(world.map().walls, p)) continue;
                        through |= 1u << k;
                        if (!test(world.map().blocked_for_them, p)) open |= 1u << k;
                        if (world.map().group_at(p) >= 0) camp |= 1u << k;
                    }
                }
                // A row's 9 bits straddle the words only on row 7.
                constexpr int at = Row * win_n;
                const auto place = [](Window& w, std::uint64_t row) __attribute__((always_inline)) {
                    if constexpr (at < 64) w.lo |= row << at;
                    if constexpr (at > 64 - win_n && at < 64) w.hi |= row >> (64 - at);
                    if constexpr (at >= 64) w.hi |= row << (at - 64);
                };
                place(pass, through);
                place(land, open);
                place(camps, camp);
            }(),
            ...);
    }(std::make_integer_sequence<int, win_n>{});
    st = {pass, land, camps};
    return st;
}

// Tiles whose 8 neighbours' static windows are all known.
std::array<std::uint8_t, 100 * 100> statics_around;

} // namespace

void warm_reach(const World& world, std::uint64_t fuel_floor) {
    if (!world.me().alive || !fuel_ok(fuel_floor + 8000)) return;
    const vec2 here = my_position();
    const auto& t = terrain(world.map());
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible || dist(here, e.pos) > vision_radius) continue;
        const auto ei = static_cast<std::size_t>(e.pos.x + e.pos.y * t.width);
        if (statics_around[ei]) continue;
        for (const vec2 d : directions) {
            const vec2 q = e.pos + d;
            if (!t.inside(q) || statics_scanned[static_cast<std::size_t>(q.x + q.y * t.width)]) continue;
            if (!fuel_ok(fuel_floor + 8000)) return;
            (void)static_window(world, q);
        }
        statics_around[ei] = 1;
    }
}

int Reach::add(Tiles from, int range, bool sight, float damage, bool stuns, bool walked) {
    auto& ws = *ways_;
    const auto key = static_cast<std::uint8_t>(((from * 8 + range) * 2 + sight) * 2 + walked);
    for (int i = 0; i < ws.count; ++i) {
        auto& w = ws.way[static_cast<std::size_t>(i)];
        if (w.key == key) {
            w.damage = std::max(w.damage, damage);
            w.stuns = w.stuns || stuns;
            return i;
        }
    }
    if (ws.count == static_cast<int>(ws.way.size())) return -1;
    ws.way[static_cast<std::size_t>(ws.count)] = {damage, from, static_cast<std::int8_t>(range), key, sight, stuns, walked};
    return ws.count++;
}

void Reach::build(const World& world, const ChampionBelief& e, int turn_round, bool twice) {
    world_ = &world;
    origin_ = e.pos;
    owner_ = e.index;
    ward_ = unknown_ward;
    static std::uint32_t builds = 0;
    stamp_ = ++builds;
    twice_ = twice;
    strength_ = hit_strength(e);
    reach_ = -1;
    const auto& f = e.facts();
    const bool uncertain = e.cooldowns_uncertain();
    const std::array<bool, 2> ready{uncertain || e.ability_ready(0, turn_round), uncertain || e.ability_ready(1, turn_round)};
    const std::array<bool, 2> ready2 =
        twice ? std::array<bool, 2>{ready[0] || e.ability_ready(0, turn_round + 1), ready[1] || e.ability_ready(1, turn_round + 1)} : ready;
    const int dash_slot = f.slot_of(AbilityKind::dash);
    const bool dash = dash_slot >= 0 && ready2[static_cast<std::size_t>(dash_slot)];
    // Our champions around it, which block its walks and landings; they stay put through our turn.
    static int allies_round = -1;
    static std::array<vec2, 8> allies;
    static int ally_count = 0;
    if (allies_round != world.round) {
        allies_round = world.round;
        ally_count = 0;
        for (const auto& a : world.allies)
            if (ally_count < static_cast<int>(allies.size()) && a.alive && a.visible && !a.is_self) allies[ally_count++] = a.pos;
    }
    Window occupied;
    for (int i = 0; i < ally_count; ++i)
        if (dist(allies[i], origin_) <= win_r) occupied |= win_bit(allies[i].x - origin_.x + win_r, allies[i].y - origin_.y + win_r);
    splash_ = f.passive == Passive::splash_attack;
    units_ = occupied;
    splash_known_ = 0;
    const auto kind = static_cast<std::uint8_t>(twice | dash << 1);
    if (sets_reusable_ && sets_origin_ == origin_ && sets_kind_ == kind && sets_occupied_.lo == occupied.lo
        && sets_occupied_.hi == occupied.hi) {
        build_ways(e, ready, ready2, twice);
        return;
    }
    sets_origin_ = origin_;
    sets_kind_ = kind;
    sets_occupied_ = occupied;
    const auto& st = static_window(world, origin_);
    Window pass = st.pass, land = st.land & ~occupied;
    const Window& camps = st.camps;
    sets_reusable_ = !camps;
    if (camps) {
        const auto oi = static_cast<std::size_t>(origin_.x + origin_.y * world.map().width);
        if (!spots_count[oi]) {
            if (spot_pool.empty()) spot_pool.reserve(512);
            spots_from[oi] = static_cast<std::uint32_t>(spot_pool.size());
            for (int word = 0; word < 2; ++word)
                for (std::uint64_t bits = word ? camps.hi : camps.lo; bits; bits &= bits - 1) {
                    const int i = 64 * word + std::countr_zero(bits);
                    const auto& t = camp_tile(world, {origin_.x - win_r + i % win_n, origin_.y - win_r + i / win_n});
                    if (t.group >= 0 && t.member != 255) spot_pool.push_back({static_cast<std::uint8_t>(i), t.member, t.group});
                }
            spots_count[oi] = static_cast<std::uint8_t>(spot_pool.size() - spots_from[oi] + 1);
        }
        Window live;
        for (const CampSpot *s = spot_pool.data() + spots_from[oi], *end = s + spots_count[oi] - 1; s != end; ++s)
            if (live_member(world, s->group, s->member)) live |= tables.bits[s->bit];
        pass &= ~live, land &= ~live;
        units_ |= live;
    }
    const auto walk = [&](Window s) { return s | (dilate(s) & land); };
    const auto dash_from = [&](Window s) {
        const Window first = dilate(s) & pass;
        return s | ((first | (dilate(first) & pass)) & land);
    };
    const auto extent = [](const Window& w) {
        int k = win_r;
        while (k > 0 && !(w & ~tables.square[static_cast<std::size_t>(k - 1)])) --k;
        return static_cast<std::int8_t>(k);
    };
    tiles_[here] = win_bit(win_r, win_r);
    extent_[here] = 0;
    tiles_[walked1] = walk(tiles_[here]);
    extent_[walked1] = extent(tiles_[walked1]);
    if (twice) tiles_[walked2] = walk(tiles_[walked1]), extent_[walked2] = extent(tiles_[walked2]);
    if (dash) {
        tiles_[dashed] = f.ranged ? dash_from(tiles_[here]) : dash_from(tiles_[walked1]) | walk(dash_from(tiles_[here]));
        extent_[dashed] = extent(tiles_[dashed]);
        if (twice) tiles_[dashed_walked] = walk(tiles_[dashed]), extent_[dashed_walked] = extent(tiles_[dashed_walked]);
    }
    build_ways(e, ready, ready2, twice);
}

void Reach::build_ways(const ChampionBelief& e, std::array<bool, 2> ready, std::array<bool, 2> ready2, bool twice) {
    const auto& f = e.facts();
    const float s = hit_strength(e), focus = hit_focus(e);
    const Recipe recipe{e.type, std::bit_cast<std::uint32_t>(s), std::bit_cast<std::uint32_t>(focus),
                        static_cast<std::uint8_t>(ready[0] | ready[1] << 1 | ready2[0] << 2 | ready2[1] << 3), twice, true};
    ways_ = &ways_by_[static_cast<std::size_t>(ready[0] + ready2[0] + 3 * (ready[1] + ready2[1]) + 9 * twice)];
    auto& ws = *ways_;
    if (recipe == ws.recipe) {
        set_reach();
        return;
    }
    ws.recipe = recipe;
    ws.count = 0;
    ws.basic = -1;
    const Tiles basic_from = f.ranged ? here : walked1;
    const int range = f.attack_range();
    for (int turn = 0; turn < (twice ? 2 : 1); ++turn) {
        const bool walked = turn == 1;
        // A walk first, on the first of two turns.
        const auto from = [&](Tiles x) { return !walked ? x : x == here ? walked1 : x == walked1 ? walked2 : dashed_walked; };
        const int basic = add(from(basic_from), range, true, s, false, walked);
        if (!walked) ws.basic = basic;
        for (std::size_t slot = 0; slot < 2; ++slot) {
            if (!(walked ? ready2 : ready)[slot]) continue;
            const auto& a = f.abilities[slot];
            const float spell = a.multiplier * focus;
            switch (a.kind) {
            case AbilityKind::attack_reset:
                add(from(basic_from), range, true, 2 * s, a.stuns, walked);
                if (f.ranged) add(from(walked1), range, true, s, a.stuns, walked); // walk, reset, attack
                break;
            case AbilityKind::dash:
                add(from(dashed), range, true, s, false, walked);
                // The landing hits unseen tiles too; the landings are taken as all of `dashed`.
                if (a.lands()) {
                    add(from(dashed), a.radius, false, spell, a.stuns, walked);
                    add(from(dashed), std::min(range, a.radius), true, spell + s, a.stuns, walked);
                }
                break;
            case AbilityKind::damage:
                // Excludes walking but not the basic attack.
                add(from(here), a.reach(), a.target == Targeting::unit, spell, a.stuns, walked);
                add(from(here), range, true, spell + s, a.stuns, walked);
                break;
            case AbilityKind::stun:
                add(from(a.excludes_walking ? here : walked1), a.reach(), a.target == Targeting::unit, 0, true, walked);
                break;
            default: break;
            }
        }
    }
    // Largest damage first: a query stops at the first way that reaches it.
    for (int i = 1; i < ws.count; ++i)
        for (int j = i; j > 0 && ws.way[static_cast<std::size_t>(j)].damage > ws.way[static_cast<std::size_t>(j - 1)].damage; --j) {
            std::swap(ws.way[static_cast<std::size_t>(j)], ws.way[static_cast<std::size_t>(j - 1)]);
            if (ws.basic == j) ws.basic = j - 1;
            else if (ws.basic == j - 1) ws.basic = j;
        }
    set_reach();
}

void Reach::set_reach() {
    reach_ = -1;
    auto& ws = *ways_;
    for (int i = 0; i < ws.count; ++i) {
        auto& w = ws.way[static_cast<std::size_t>(i)];
        w.bound = static_cast<std::int8_t>(extent_[w.from] + w.range + (splash_ && w.sight && units_ ? 1 : 0));
        reach_ = std::max(reach_, static_cast<int>(w.bound));
    }
}

const Reach::Window& Reach::splash_targets(Tiles from, int range) const {
    auto& m = splash_units_[from];
    if (splash_known_ >> from & 1) return m;
    splash_known_ |= static_cast<std::uint8_t>(1u << from);
    m = {};
    const auto& t = terrain(world_->map());
    const Window units = range <= 1 ? units_ & dilate(tiles_[from]) : units_;
    for (int word = 0; word < 2; ++word)
        for (std::uint64_t bits = word ? units.hi : units.lo; bits; bits &= bits - 1) {
            const int i = 64 * word + std::countr_zero(bits), ux = i % win_n, uy = i / win_n;
            const vec2 u{origin_.x - win_r + ux, origin_.y - win_r + uy};
            Window f = tiles_[from] & box(ux, uy, range);
            if (f && (range > 1 || t.bush(u))) {
                if (ward_ == unknown_ward) ward_ = ward_of(*world_, owner_);
                if (ward_ < 0 || !ward_sees(t, ward_, u)) f &= sight_from(*world_, u, range > 1, ux - win_r, uy - win_r);
            }
            if (f) m |= tables.bits[static_cast<std::size_t>(i)];
        }
    return m;
}

Blow Reach::at(vec2 p) const {
    auto& memo = memo_[static_cast<std::size_t>((p.x & 7) | (p.y & 7) << 3)];
    if (memo.stamp == stamp_ && memo.p == p) return memo.blow;
    Blow out;
    const int dx = p.x - origin_.x, dy = p.y - origin_.y;
    if (const auto& t = terrain(world_->map()); std::max(std::abs(dx), std::abs(dy)) <= reach_ && t.inside(p)) {
        // Who sees p, in this window; worked out on first need. If its own ward sees p, it sees
        // it from anywhere. So may a ward we do not see, hidden in a bush cluster we cannot see into.
        union Sight {
            Sight() {}
            Window w;
        } near_sight, far_sight;
        auto& near = near_sight.w;
        auto& far = far_sight.w;
        bool near_known = false, far_known = false;
        float single = -1, walked = -1;
        bool basic = false;
        const int d = std::max(std::abs(dx), std::abs(dy));
        const auto& ws = *ways_;
        int ward = -1;
        const auto seen = [&](bool far, Window& m) __attribute__((always_inline)) {
            if (ward < 0) {
                if (ward_ == unknown_ward) ward_ = ward_of(*world_, owner_);
                ward = ward_ >= 0 ? ward_sees(t, ward_, p) : t.bush(p) && !test(world_->visible, p);
            }
            m = ward ? win_full : sight_from(*world_, p, far, dx, dy);
        };
        for (int i = 0; i < ws.count; ++i) {
            const auto& w = ws.way[static_cast<std::size_t>(i)];
            if (d > w.bound) continue;
            if (out.hits && w.damage <= (w.walked ? walked : single) && (!w.stuns || out.stuns) && !(twice_ && i == ws.basic)) continue;
            Window from = tiles_[w.from] & box(dx + win_r, dy + win_r, w.range);
            if (from && w.sight) {
                if (w.range <= 1) {
                    if (!near_known) {
                        // Outside bushes, all within 1 of p sees it: the box alone settles it.
                        if (t.bush(p)) seen(false, near);
                        else near = win_full;
                        near_known = true;
                    }
                    from &= near;
                } else {
                    if (!far_known) seen(true, far), far_known = true;
                    from &= far;
                }
            }
            if (!from && !(splash_ && w.sight && (splash_targets(w.from, w.range) & box(dx + win_r, dy + win_r, 1)))) continue;
            if (w.walked) walked = std::max(walked, w.damage);
            else single = std::max(single, w.damage);
            basic |= i == ws.basic;
            out.stuns |= w.stuns;
            out.hits = true;
        }
        if (out.hits) out.damage = std::max({0.0f, walked, single < 0 ? 0.0f : single + (twice_ && basic ? strength_ : 0.0f)});
    }
    memo = {p, out, stamp_};
    return out;
}

Blow Threat::at(vec2 p) const {
    if (owner) return owner->blow(*belief, p);
    if (visible) return strike.blow(dist(p, pos));
    return strike.blow(steps ? steps_at(*steps, p) : unreachable);
}

// An unseen enemy's best chance to be in reach of a tile, or 0 if too slight to count.
float unseen_weight(int reach, int tiles) {
    const float weight = std::min(1.0f, static_cast<float>((2 * reach + 1) * (2 * reach + 1)) / static_cast<float>(tiles));
    return tiles == 0 || weight < credible_weight ? 0.0f : weight;
}

// Next to a compact possible set of side ~sqrt(tiles), the chance of being in reach falls by about
// 1 / sqrt(tiles) per step out; keep the tiles still near the cutoff.
int unseen_radius(int reach, int tiles) {
    return std::clamp(static_cast<int>(static_cast<float>(reach) + 1.5f - credible_weight * std::sqrt(static_cast<float>(tiles))), 0, reach);
}

namespace {

// The most an unseen enemy's threat has cost to build so far, 0 before the first.
std::uint64_t& costliest_unseen() {
    static std::uint64_t cost = 0;
    return cost;
}

std::vector<Threat>& threat_pool() {
    static std::vector<Threat> pool;
    return pool;
}

// Left zeroed rather than constructed, as constructing ~50KB costs as many fuel: a zeroed Reach
// is ready for its first build.
union ReachPool {
    constexpr ReachPool() {}
    std::array<Reach, 16> reaches;
};

std::array<Reach, 16>& reach_pool() {
    static ReachPool pool;
    return pool.reaches;
}

} // namespace

namespace {

// A tile in our vision with no camp on it: its member has died. One host call, which tells hidden
// tiles apart.
bool seen_empty(vec2 p) {
    std::int32_t camp = 0;
    return cambc::detail::sdk_has_camp(p.x, p.y, &camp) == 0 && camp == 0;
}

} // namespace

std::vector<Safety::CampHit>& Safety::member_pool() {
    static std::vector<CampHit> pool;
    return pool;
}

Safety::Safety(const World& world) : world_{world}, threats_{threat_pool()}, members_{member_pool()} {}

std::span<const Safety::CampHit> Safety::awake_members() {
    if (!members_known_) find_members();
    return {members_.data(), static_cast<std::size_t>(member_count_)};
}

[[gnu::noinline]] void Safety::find_members() {
    members_known_ = true;
    int count = 0;
    camp_memo_[0].valid = camp_memo_[1].valid = camp_memo_[2].valid = false;
    // Each monster attacks the nearest champion within range, ties to the one acting first in
    // the round of the next camp phase.
    struct Other {
        vec2 pos;
        const ChampionBelief* belief;
        std::int8_t first; // acts before us next round; -1 until needed
        std::int8_t wakes; // strike reach on its turn this round, -1 if done; -2 until needed
    };
    union Others { // the first n only: the engine charges for every byte written
        std::array<Other, 2 * max_fighters> at;
        Others() {}
    } others;
    int n = -1;
    const int next = world_.round + 1;
    int self_slot = -1;
    // Turn order matters only to an other a step nearer than a member's reach so far.
    const auto first = [&](Other& o) {
        if (o.first < 0) {
            if (self_slot < 0) self_slot = world_.slot(world_.me(), next);
            o.first = world_.slot(*o.belief, next) < self_slot ? 1 : 0;
        }
        return static_cast<int>(o.first);
    };
    const bool reread = refresh_;
    const auto& groups = world_.map().groups;
    world_.each_stirring([&](int g) {
        if (groups[g].strength <= 0) return;
        const auto& c = world_.camps[g];
        if (n < 0) {
            n = 0;
            for (const auto& o : world_.allies)
                if (n < static_cast<int>(others.at.size()) && o.alive && o.visible && !o.is_self && !gone(o))
                    others.at[n++] = {o.pos, &o, -1, -2};
            for (auto left = seen_enemies(); left; left &= left - 1)
                if (const auto& o = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
                    n < static_cast<int>(others.at.size()) && !gone(o))
                    others.at[n++] = {o.pos, &o, -1, -2};
            if (camp_factor_ <= 0) camp_factor_ = camp_hit_factor();
        }
        const float w = c.awake == Awake::awake ? 1.0f : unknown_camp_weight;
        // Only others this near a group's box can bring a member's reach below the group's:
        // a big group leaves out the rest.
        std::array<std::uint8_t, 2 * max_fighters> near;
        int k_near = 0;
        if (groups[g].members.size() >= 8) {
            const auto& box = member_boxes(world_.map())[static_cast<std::size_t>(g)];
            for (int k = 0; k < n; ++k) {
                auto& o = others.at[k];
                const int out = std::max({box[0] - o.pos.x, o.pos.x - box[1], box[2] - o.pos.y, o.pos.y - box[3], 0});
                if (out - 1 < groups[g].reach && out - first(o) < groups[g].reach) near[k_near++] = static_cast<std::uint8_t>(k);
            }
        } else {
            for (int k = 0; k < n; ++k) near[k_near++] = static_cast<std::uint8_t>(k);
        }
        const auto size = groups[g].members.size();
        // An asleep member wakes only when the group is damaged or stunned: by us, which our own
        // choices weigh, or by another champion yet to act this round within its strike's reach.
        bool stirred = c.asleep == 0;
        for (int k = 0; k < n && !stirred; ++k) {
            auto& o = others.at[k];
            if (o.wakes == -2) o.wakes = o.belief->acted ? -1 : static_cast<std::int8_t>(strike(*o.belief, world_.round).reach);
            if (o.wakes < 0) continue;
            for (std::size_t i = 0; i < size && !stirred; ++i)
                stirred = c.health[i] > 0 && dist(o.pos, groups[g].members[i].pos) <= o.wakes;
        }
        if (static_cast<std::size_t>(count) + size > members_.size()) members_.resize(static_cast<std::size_t>(count) + size);
        auto* const out = members_.data();
        for (std::size_t i = 0; i < size; ++i) {
            const auto& m = groups[g].members[i];
            if (c.health[i] <= 0 || m.strength <= 0 || (reread && seen_empty(m.pos))) continue;
            if (!stirred && c.member_asleep(i)) continue;
            int reach = m.reach;
            for (int k = 0; k < k_near; ++k) {
                auto& o = others.at[near[k]];
                if (const int d = dist(o.pos, m.pos); d - 1 < reach) reach = std::min(reach, d - first(o));
            }
            if (reach > 0) out[count++] = {m.pos, m.strength * camp_factor_, w, reach, m.handle, test(world_.visible, m.pos) && camp_stunned(m.handle)};
        }
    });
    member_count_ = count;
}

bool Safety::gone(const ChampionBelief& c) {
    if (!refresh_ || c.side != team::enemy || !c.visible || c.index >= static_cast<int>(gone_.size())) return false;
    auto& known = gone_[static_cast<std::size_t>(c.index)];
    if (known == 0) known = still_alive(c) ? 1 : 2;
    return known == 2;
}

[[gnu::noinline]] void Safety::list_enemies() {
    listed_ = true;
    const auto& enemies = world_.enemies;
    const int n = std::min(static_cast<int>(enemies.size()), 32);
    std::uint32_t seen = 0, unseen = 0;
    for (int i = 0; i < n; ++i) {
        const auto& e = enemies[static_cast<std::size_t>(i)];
        if (!e.alive) continue;
        if (e.visible) seen |= 1u << i;
        else if (e.tracked) unseen |= 1u << i;
    }
    seen_ = seen;
    unseen_ = unseen;
}

[[gnu::noinline]] bool Safety::still_alive(const ChampionBelief& c) {
    std::int32_t alive{};
    ok(cambc::detail::sdk_champion_is_alive(static_cast<std::uint32_t>(c.handle), &alive));
    return alive != 0;
}

void Safety::invalidate() {
    built_ = false;
    refresh_ = true;
    reached_ = 0;
    build_cost_ = 0;
    threat_count_ = 0;
    threat_mask_ = 0;
    members_known_ = false;
    camp_area_known_ = false;
    enemy_area_known_ = false;
    threatened_at_ = {-1, -1};
    fight_count_ = 0;
    unknown_falls_ = 0;
    gone_.fill(0);
    reachable_known_ = false;
}

void Safety::refresh() {
    refresh_ = true;
    own_health_ = -1;
    gone_.fill(0);
    build_cost_ = 0;
    reachable_known_ = false;
    if (!built_ && !members_known_) return;
    bool changed = false;
    for (auto left = seen_enemies(); left; left &= left - 1) changed |= gone(world_.enemies[static_cast<std::size_t>(std::countr_zero(left))]);
    if (!changed && members_known_)
        for (int i = 0; i < member_count_ && !changed; ++i) changed = seen_empty(members_[static_cast<std::size_t>(i)].pos);
    if (changed) {
        invalidate();
        return;
    }
    // Our stuns this turn: a stunned member skips the next camp phase.
    bool stunned = false;
    for (int i = 0; i < member_count_ && members_known_; ++i)
        if (auto& m = members_[static_cast<std::size_t>(i)]; !m.stunned && test(world_.visible, m.pos) && camp_stunned(m.handle))
            m.stunned = stunned = true;
    if (stunned) camp_memo_[2].valid = false, threatened_at_ = {-1, -1};
}

[[gnu::noinline]] void Safety::strike_foe(const ChampionBelief& e, Foe& x) {
    known_ |= static_cast<std::uint16_t>(1u << e.index);
    x.strike = threat_strike(world_, e);
    x.asked = {-1, -1};
}

Safety::Foe& Safety::struck(const ChampionBelief& e) {
    auto& x = foes_[static_cast<std::size_t>(e.index)];
    if (!(known_ >> e.index & 1)) strike_foe(e, x);
    return x;
}

Safety::Foe& Safety::foe(const ChampionBelief& e) {
    auto& x = struck(e);
    if (!(counted_ >> e.index & 1)) count_foe(e, x);
    return x;
}

[[gnu::noinline]] void Safety::count_foe(const ChampionBelief& e, Foe& x) {
    counted_ |= static_cast<std::uint16_t>(1u << e.index);
    x.tiles = 0;
    x.weight = 0;
    if (!e.visible && x.strike.reach >= 0) {
        x.tiles = static_cast<int>(board_count(e.possible));
        x.weight = unseen_weight(x.strike.reach, x.tiles);
    }
}

namespace {

Threat& next_threat(std::vector<Threat>& pool, int& count) {
    if (count == static_cast<int>(pool.size())) pool.emplace_back();
    return pool[static_cast<std::size_t>(count++)];
}

} // namespace

void Safety::build() {
    world_.throw_if_stale();
    if (!built_) build_threats();
}

[[gnu::noinline]] void Safety::build_threats() {
    built_ = true;
    FuelMeter meter{"safety"};
    // One per enemy, reused between builds: a new field allocates and clears ~13k bytes.
    static std::vector<std::unique_ptr<cambc::distance_field>> fields;
    const auto field_of = [&](int i) -> cambc::distance_field& {
        if (fields.size() <= static_cast<std::size_t>(i)) fields.resize(static_cast<std::size_t>(i) + 1);
        auto& field = fields[static_cast<std::size_t>(i)];
        if (!field) field = std::make_unique<cambc::distance_field>();
        return *field;
    };
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e)) continue;
        const auto& x = foe(e);
        const auto& s = x.strike;
        const int reach = s.reach;
        if (reach < 0) continue;
        if (e.visible) {
            auto& t = next_threat(threats_, threat_count_);
            threat_mask_ |= static_cast<std::uint16_t>(1u << e.index);
            t.enemy = e.index;
            t.strike = s;
            t.visible = true;
            t.pos = e.pos;
            t.tiles = 1;
            t.steps = nullptr;
            t.owner = this;
            t.belief = &e;
            continue;
        }
        const int tiles = x.tiles;
        const float weight = x.weight;
        if (weight == 0) continue;
        const auto before = fuel();
        auto& t = next_threat(threats_, threat_count_);
        threat_mask_ |= static_cast<std::uint16_t>(1u << e.index);
        t.enemy = e.index;
        t.strike = s;
        t.visible = false;
        t.pos = {-1, -1};
        t.tiles = tiles;
        t.owner = nullptr;
        const int radius = unseen_radius(reach, tiles);
        auto& field = field_of(e.index);
        clear_board(t.area);
        field.compute(world_.map().walls, e.possible, t.area, static_cast<std::uint16_t>(radius));
        t.steps = &field;
        if (const auto after = fuel(); after < before) costliest_unseen() = std::max(costliest_unseen(), before - after);
    }
}

std::span<const Threat> Safety::threats() {
    build();
    return {threats_.data(), static_cast<std::size_t>(threat_count_)};
}

// f(enemy, blow) for each enemy build() makes a threat of, the blow at least its threat's at p:
// exact if visible; if unseen, its strike at 0 when a tile it could be on is within its reach of
// p, else none, as its field is capped within the reach. Strikes only weaken with distance, so
// this bounds the threats' damage and hits at p without building them.
template <class F> void Safety::each_threat(vec2 p, F&& f) {
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e)) continue;
        auto& x = foe(e);
        const auto& s = x.strike;
        if (s.reach < 0) continue;
        if (e.visible) f(e, blow(e, p));
        else if (x.weight > 0) {
            if (x.asked != p) x.asked = p, x.near = any_within(e.possible, p, s.reach);
            f(e, x.near ? s.blow(0) : Blow{});
        }
    }
}

[[gnu::noinline]] void Safety::build_reach(const ChampionBelief& e, Reach& r) {
    reached_ |= static_cast<std::uint16_t>(1u << e.index);
    r.build(world_, e, next_turn_round(world_, e), turns_before_ours(world_, e) >= 2);
}

const Reach& Safety::reach_of(const ChampionBelief& e) {
    auto& r = reach_pool()[static_cast<std::size_t>(e.index)];
    if (!(reached_ >> e.index & 1)) build_reach(e, r);
    return r;
}

Blow Safety::blow(const ChampionBelief& e, vec2 p) {
    const auto& s = struck(e).strike;
    if (e.teleport_pending() && in_bounds(e.tp_dest)) return s.blow(dist(p, e.tp_dest)); // it acts from there
    if (s.reach < 0 || !in_square(p, e.pos, s.reach)) return {};
    const auto& r = reach_of(e);
    const Blow b = r.at(p);
    debug_block({
        // Strike must bound Reach: blow() cuts at Strike's reach.
        static int last = -1;
        const int d = dist(p, e.pos);
        if (last != world_.round && (r.reach() > s.reach || b.damage > s.at(d) + 0.01f || (b.stuns && !s.stuns[d]))) {
            last = world_.round;
            std::printf("REACH-BOUND %d e%d reach %d/%d d %d damage %.1f/%.1f\n", world_.round, e.index, r.reach(), s.reach, d, b.damage, s.at(d));
        }
    });
    return b;
}

int Safety::approach(const ChampionBelief& e, vec2 p) {
    const int reach = struck(e).strike.reach;
    const vec2 from = e.teleport_pending() && in_bounds(e.tp_dest) ? e.tp_dest : e.pos;
    return blow(e, p).hits ? 0 : std::max(1, dist(p, from) - reach);
}

int Safety::threats_at(vec2 p, std::array<ThreatAt, 16>& out) {
    int n = 0;
    if (built_) {
        for (const auto& t : threats())
            if (n < static_cast<int>(out.size())) out[n++] = {t.enemy, t.at(p)};
        return n;
    }
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e) || n == static_cast<int>(out.size())) continue;
        const auto& x = foe(e);
        if (x.strike.reach < 0) continue;
        if (e.visible) {
            out[n++] = {e.index, blow(e, p)};
        } else if (x.weight > 0) {
            // The nearest possible tile within the radius, by bisection; past the reach every
            // distance misses alike.
            const int radius = unseen_radius(x.strike.reach, x.tiles), top = std::min(radius, x.strike.reach);
            int d = radius + 1;
            if (any_within(e.possible, p, top)) {
                int lo = 0;
                d = top;
                while (lo < d) {
                    const int mid = (lo + d) / 2;
                    if (any_within(e.possible, p, mid)) d = mid;
                    else lo = mid + 1;
                }
            }
            out[n++] = {e.index, x.strike.blow(d <= radius ? d : static_cast<int>(unreachable))};
        }
    }
    return n;
}

bool Safety::enemy_may_hit_within(vec2 p, int radius) {
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e)) continue;
        const int reach = foe(e).strike.reach;
        if (reach < 0) continue;
        if (e.visible) {
            const vec2 from = e.teleport_pending() && in_bounds(e.tp_dest) ? e.tp_dest : e.pos;
            if (dist(p, from) <= reach + radius) return true;
        } else if (any_within(e.possible, p, reach + radius)) {
            return true;
        }
    }
    return false;
}

bool Safety::credible_enemy_may_hit_within(vec2 p, int radius) {
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e)) continue;
        const auto& x = foe(e);
        const int reach = x.strike.reach;
        if (reach < 0 || (!e.visible && !(x.weight > 0))) continue;
        if (e.visible) {
            const vec2 from = e.teleport_pending() && in_bounds(e.tp_dest) ? e.tp_dest : e.pos;
            if (dist(p, from) <= reach + radius) return true;
        } else if (any_within(e.possible, p, reach + radius)) {
            return true;
        }
    }
    return false;
}

bool Safety::any_threat() {
    if (built_) return threat_count_ > 0;
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e)) continue;
        const auto& x = foe(e);
        if (x.strike.reach >= 0 && (e.visible || x.weight > 0)) return true;
    }
    return false;
}

float Safety::damage_bound(vec2 p, bool double_unacted) {
    float total = camp_damage(p, true, true);
    each_threat(p, [&](const ChampionBelief& e, const Blow& b) {
        total += b.damage * (double_unacted && e.visible && !e.acted ? 2.0f : 1.0f);
    });
    return total;
}

float Safety::damage_ceiling(vec2 p, bool double_unacted) {
    float total = camp_damage(p, true, true);
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e)) continue;
        if (!e.visible) {
            total += most_damage(e);
            continue;
        }
        if (struck(e).strike.reach < 0) continue;
        total += blow(e, p).damage * (double_unacted && !e.acted ? 2.0f : 1.0f);
    }
    return total;
}

bool Safety::may_be_hit(vec2 p) {
    bool hit = false;
    each_threat(p, [&](const ChampionBelief&, const Blow& b) { hit |= b.hits; });
    return hit;
}

float Safety::camp_damage(vec2 p, bool worst, bool next) {
    const auto& members = awake_members();
    if (members.empty()) return 0;
    next = next && worst;
    auto& memo = camp_memo_[next ? 2 : worst ? 1 : 0];
    if (memo.valid && memo.p == p) return memo.damage;
    float total = 0;
    for (const auto& m : members)
        if (in_square(p, m.pos, m.reach) && !(next && m.stunned)) total += worst ? m.strength : m.strength * m.weight;
    memo = {p, total, true};
    return total;
}

float Safety::worst_damage(vec2 p) {
    float total = camp_damage(p, true, true);
    for (const auto& t : threats())
        total += t.at(p).damage;
    return total;
}

// Any camp member or visible threat in reach is enough on its own. An unseen threat's chance is
// uniform over its possible tiles; it hits p only within its field, capped inside its reach.
bool Safety::threatened(vec2 p) {
    if (p != threatened_at_) threatened_ = threatened_now(p), threatened_at_ = p;
    return threatened_;
}

bool Safety::threatened_now(vec2 p) {
    static_assert(unknown_camp_weight >= recall_risk && hit_given_reach >= recall_risk);
    if (camp_damage(p, true, true) > 0) return true;
    if (!built_ && !may_be_hit(p)) return false;
    float safe = 1;
    for (const auto& t : threats()) {
        if (!t.at(p).hits) continue;
        if (t.visible) return true;
        const auto near = count_within(world_.enemies[t.enemy].possible, p, t.strike.reach);
        const float chance = std::min(1.0f, static_cast<float>(near) / static_cast<float>(t.tiles));
        if (1 - (safe *= 1 - chance * hit_given_reach) >= recall_risk) return true;
    }
    return false;
}

const bitboard& Safety::camp_area() {
    static bitboard area{cambc::uninitialized};
    if (!camp_area_known_) {
        clear_board(area);
        for (const auto& m : awake_members())
            draw_square(area, m.pos, static_cast<float>(m.reach));
        camp_area_known_ = true;
    }
    return area;
}

const bitboard& Safety::enemy_area() {
    static bitboard any{cambc::uninitialized};
    if (!enemy_area_known_) {
        clear_board(any);
        // A visible threat's: a superset, as a walls field per enemy each turn would cost ~3k.
        for (const auto& t : threats())
            if (!t.visible) or_into(any, t.area, any);
            else if (const int r = reach_of(*t.belief).reach(); r >= 0) draw_square(any, t.pos, static_cast<float>(r));
        enemy_area_known_ = true;
    }
    return any;
}

const bitboard& Safety::avoid() {
    static bitboard out{cambc::uninitialized};
    or_into(camp_area(), enemy_area(), out);
    return out;
}

// Every unseen threat is credible: unseen_weight() drops the rest. Its area is `possible` grown by
// its radius, so it comes within r of p exactly when `possible` comes within radius + r.
bool Safety::avoid_within(vec2 p, int r) {
    for (const auto& m : awake_members())
        if (dist(p, m.pos) <= m.reach + r) return true;
    if (built_) return any_within(enemy_area(), p, r);
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e)) continue;
        const auto& x = foe(e);
        const int reach = x.strike.reach;
        if (reach < 0) continue;
        if (e.visible) {
            if (dist(p, e.pos) <= reach + r) return true;
            continue;
        }
        if (x.weight > 0 && any_within(e.possible, p, unseen_radius(reach, x.tiles) + r)) return true;
    }
    return false;
}

std::uint32_t Safety::fight_key(vec2 p) {
    std::uint32_t key = 0;
    bool hit = false;
    for (const auto& t : threats()) {
        if (!t.at(p).hits) continue;
        hit = true;
        key |= 1u << (16 + t.enemy);
    }
    if (!hit) return no_fight;
    return key | fighting_allies(world_, p);
}

std::uint32_t Safety::fight_key_with(vec2 p, std::uint32_t visible) {
    std::uint32_t key = visible;
    for (const auto& t : threats())
        if (!t.visible && t.at(p).hits) key |= 1u << (16 + t.enemy);
    return key | fighting_allies(world_, p);
}

const Trade* Safety::memo(std::uint32_t key, bool falls) const {
    for (int i = 0; i < std::min(fight_count_, max_fights); ++i)
        if (fights_[i].key == key && !(falls && unknown_falls_ >> i & 1)) return &fights_[i].trade;
    return nullptr;
}

Trade Safety::fight(vec2 p, bool falls) {
    world_.throw_if_stale();
    const auto key = fight_key(p);
    return key == no_fight ? Trade{} : fight_of(key, falls);
}

Trade Safety::fight_of(std::uint32_t key, bool falls) {
    if (const auto* t = memo(key, falls)) return *t;
    return new_fight(key, falls);
}

Trade Safety::new_fight(std::uint32_t key, bool falls) {
    Side us, them;
    fill(us, world_, world_.allies, key & 0xFFFFu, made_);
    build();
    fill(them, world_, world_.enemies, key >> 16 & threat_mask_, made_);
    const auto before = fuel();
    // Asked again with self_falls, a fight replaces the one without.
    int i = -1;
    for (auto left = unknown_falls_; left; left &= left - 1)
        if (fights_[std::countr_zero(left)].key == key) i = std::countr_zero(left);
    if (i < 0) i = fight_count_++ % max_fights;
    auto& slot = fights_[i];
    slot = {key, trade(us, them, end_reserve, true, falls)};
    unknown_falls_ = slot.trade.falls_known ? unknown_falls_ & ~(1u << i) : unknown_falls_ | 1u << i;
    if (const auto after = fuel(); after < before) costliest_fight_ = std::max(costliest_fight_, before - after);
    return slot.trade;
}

Trade Safety::chase_trade(std::uint32_t key, std::uint32_t delayed, const std::array<int, 2>& self_cooldowns, bool can_cast, bool falls) {
    world_.throw_if_stale();
    if (key == no_fight) return {};
    Side us, them;
    fill(us, world_, world_.allies, key & 0xFFFFu, made_);
    bool changed = false;
    int at = 0;
    for (auto left = key & 0xFFFFu; left && at < us.count; left &= left - 1, ++at) {
        const int i = std::countr_zero(left);
        auto& f = us.fighters[at];
        if ((delayed >> i & 1) && f.arrives_at < 1) f.arrives_at = 1, changed = true;
        if (!world_.allies[static_cast<std::size_t>(i)].is_self) continue;
        for (int s = 0; s < 2; ++s) {
            const int ready = f.kit->cast[s].value <= 0 ? never : std::max(can_cast ? 0 : 1, self_cooldowns[s]);
            changed |= f.ready_at[s] != ready;
            f.ready_at[s] = ready;
        }
        f.next_cast = next_cast(f);
    }
    if (!changed) return fight_of(key, falls);
    us.plain = false;
    build();
    fill(them, world_, world_.enemies, key >> 16 & threat_mask_, made_);
    world_.throw_if_stale();
    // No cross-target memo: roster alone omits the delayed mask and our live action state.
    const auto before = fuel();
    const auto t = trade(us, them, end_reserve, true, falls);
    if (const auto after = fuel(); after < before) costliest_fight_ = std::max(costliest_fight_, before - after);
    world_.throw_if_stale();
    return t;
}

[[gnu::noinline]] void Safety::count_champions() {
    champions_ = 0;
    for (const auto& a : world_.allies) champions_ += a.alive && (a.is_self || a.visible);
    champions_ += std::popcount(seen_enemies());
}

std::uint64_t Safety::fight_cost_estimate() {
    if (champions_ < 0) count_champions();
    const auto champions = static_cast<std::uint64_t>(champions_);
    const auto simulation = std::max(std::max(std::uint64_t{10000}, 2000 + 2000 * champions), costliest_fight_ + costliest_fight_ / 4);
    return simulation + query_cost_estimate();
}

[[gnu::noinline]] void Safety::list_reachable() {
    reachable_known_ = true;
    reachable_ = 0;
    for (auto left = seen_enemies(); left; left &= left - 1)
        if (const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
            !(reached_ >> e.index & 1) && !gone(e) && struck(e).strike.reach >= 0)
            reachable_ |= static_cast<std::uint16_t>(1u << e.index);
}

std::uint64_t Safety::query_cost_estimate() {
    // Once listed, a visible threat's Reach is still built on its first query.
    if (built_ && !reachable_known_) list_reachable();
    return (built_ ? 2000 * static_cast<std::uint64_t>(std::popcount(static_cast<unsigned>(reachable_ & ~reached_))) : 0) + build_cost_estimate();
}

std::uint64_t Safety::build_cost_estimate() {
    if (built_) return 0;
    if (build_cost_) return build_cost_;
    return estimate_build();
}

[[gnu::noinline]] std::uint64_t Safety::estimate_build() {
    std::uint64_t cost = 2000;
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e)) continue;
        if (e.visible) cost += 4000; // with its Reach
        else cost += foe(e).weight > 0 ? (costliest_unseen() ? costliest_unseen() + costliest_unseen() / 4 : 3000 + 25 * search_chunks()) : 500;
    }
    build_cost_ = cost;
    return cost;
}

Trade Safety::stand(vec2 p, int approach, bool falls, bool unseen) {
    world_.throw_if_stale();
    std::uint32_t hit = 0, walking = 0;
    std::array<int, 16> walks;
    const auto& spawn = world_.map().near_enemy_spawn;
    for (auto left = seen_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e)) continue;
        const auto& s = struck(e).strike;
        if (s.reach < 0 || dist(p, e.pos) - s.reach > approach) continue;
        const int walk = this->approach(e, p);
        if (walk == 0) hit |= 1u << e.index;
        else if (walk <= approach && !test(spawn, e.pos)) walking |= 1u << e.index, walks[static_cast<std::size_t>(e.index)] = walk;
    }
    if (!hit && !walking && !unseen) return {};
    const auto key = hit || unseen ? fight_key_with(p, hit << 16) : fighting_allies(world_, p);
    const std::uint32_t enemies = (key >> 16 & threat_mask_) | walking;
    if (!enemies) return {};
    const float camp = camp_damage(p, false);
    if (!walking && camp <= 0) return fight_of(key, falls);
    Side us, them;
    fill(us, world_, world_.allies, key & 0xFFFFu, made_);
    fill(them, world_, world_.enemies, enemies, made_);
    int k = 0;
    for (auto left = enemies; left && k < them.count; left &= left - 1, ++k)
        if (const int i = std::countr_zero(left); walking >> i & 1) them.fighters[k].arrives_at = walks[static_cast<std::size_t>(i)], them.plain = false;
    // camp_damage() counts our Durability, which hurt() applies.
    us.camp = camp / world_.me().taken;
    // With nobody in reach yet, we strike first: they must still win.
    return trade(us, them, end_reserve, (key >> 16) != 0, falls);
}

int Safety::turns_to_kill_idle(vec2 p, int horizon) {
    Side us, them;
    us.add(fighter(world_, world_.me(), made_));
    us.fighters[0].arrives_at = never;
    us.plain = false;
    us.camp = camp_damage(p, false) / world_.me().taken; // hurt() applies our Durability
    for (auto left = seen_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e)) continue;
        const auto& s = struck(e).strike;
        if (s.reach < 0 || dist(p, e.pos) - s.reach >= horizon) continue;
        const int walk = approach(e, p);
        if (walk >= horizon) continue;
        const int k = them.count;
        them.add(fighter(world_, e, made_));
        if (them.count > k && walk != 0) them.fighters[k].arrives_at = walk, them.plain = false;
    }
    if (them.count == 0 && us.camp <= 0) return 0;
    return simulate(us, them, true, nullptr, horizon).second;
}

bool Safety::lethal(vec2 p) {
    if (own_health_ < 0) own_health_ = my_health() + (world_.me().shield_slot >= 0 ? shield_value(world_.me().handle) : 0.0f);
    const float health = own_health_;
    // Most turns no enemy is near enough; skip the threat build then.
    if (!built_ && (damage_ceiling(p) < health || damage_bound(p) < health)) return false;
    return worst_damage(p) >= health;
}

} // namespace aph
