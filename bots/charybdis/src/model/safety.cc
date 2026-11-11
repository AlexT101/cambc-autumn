#include "safety.h"
#include <algorithm>
#include <bit>
#include <cmath>
#include <cstring>
#include <limits>
#include <memory>
#include <vector>
#include "../emblems.h"
#include "../params.h"
#include "comms.h"
#include "enemy_reach.h"
#include "world.h"
#if defined(__wasm_simd128__)
#include <wasm_simd128.h>
#endif

namespace aph {

using namespace safety_params;

namespace {

// walls.shadow_cast_into(origin, r, out) without check()'s call.
[[gnu::always_inline]] inline void shadow_into(const bitboard& walls, vec2 origin, std::uint16_t r, bitboard& out) {
    ok(cambc::detail::sdk_Bitboard_ShadowCast(walls.ptr(), origin.x, origin.y, out.ptr(), r));
}

constexpr int max_fighters = 6; // one team's bodies
// For loops over a side's members, mostly one to three: unrolling costs more than it saves.
#define NO_UNROLL _Pragma("clang loop unroll(disable)")
constexpr int never = std::numeric_limits<int>::max();

// Strength and Focus as they deal damage to champions: Heart of Ruin's passive at its last-read
// health, and Skirmish and Collectors emblems.
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

// Cassi or Issac at fighters[count]: linked with the other body if it is in already.
inline void link_bodies(std::array<Fighter, max_fighters>& fighters, int count) {
    auto& g = fighters[count];
    if (g.linked)
        for (int i = 0; i < count; ++i)
            if (fighters[i].linked) g.link = i, fighters[i].link = count;
}

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
    // Own turns before `quiet_until` are only the basic attacks, `quiet_damage` in all, while
    // nobody is stunned and `alive` stays `quiet_alive`.
    int quiet_until = 0, quiet_alive = -1;
    float quiet_damage = 0;
    int weak = -2; // weakest(), or -2 when it must be found again
    int arrival = never; // plain: the next turn a living member comes into reach
    bool plain = true; // every kit plain

    constexpr Side() {}

    void add(const Fighter& f) {
        if (count == max_fighters) return;
        auto& g = fighters[count];
        g = f;
        plain = plain && g.kit->plain;
        link_bodies(fighters, count);
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
        NO_UNROLL
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
        NO_UNROLL
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
    // The camps' hits, on us at p (rules: camps.attack, nearest champion); once we are down or
    // absent, on the weakest, as before, so the totals the bounds sum still hold.
    void hurt_by_camps() {
        if (self < 0 || fighters[self].health <= 0) return hurt(camp);
        hurt(camp, self);
        lowered(self);
    }
    // `damage` as dealt: each member takes it through its own Durability.
    [[gnu::noinline]] void spill(float damage, int first) {
        for (int i = first; i >= 0; i = damage > 0 ? weakest() : -1) damage = take(i, damage);
    }
    // `damage` as dealt on living member i alone, which need not be the weakest.
    void hurt_one(int i, float damage) {
        if (damage <= 0 || fighters[i].health <= 0) return;
        take(i, damage);
        lowered(i);
    }
    // Member i takes `damage` as dealt, through its Durability and shield; returns what passes it.
    [[gnu::always_inline]] float take(int i, float damage) {
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
        if (f.health > 0) return damage;
        weak = -2;
        --alive;
        if (f.link >= 0) {
            alive -= fighters[f.link].health > 0;
            fighters[f.link].health = 0;
        }
        return damage;
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
        const bool resets = a.kind == AbilityKind::attack_reset, damages = a.kind == AbilityKind::damage || a.lands();
        if (resets) e.damage = strength;
        if (damages) e.damage = a.multiplier * focus;
        // Heart of Ruin's passive scales its damage, not its shield.
        if (a.kind == AbilityKind::shield || a.kind == AbilityKind::heal) e.heal = a.multiplier * c.focus;
        e.stuns = a.stuns;
        e.heals_self = a.kind == AbilityKind::shield;
        e.heals_ally = e.heal != 0 && !e.heals_self;
        e.hits = resets || damages ? 2 : 1;
        e.duration = a.duration;
        // A stun is worth the basic attack it takes from its target.
        e.value = (a.stuns ? strength : 0) + e.damage + e.heal;
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
[[gnu::always_inline]] inline int attack(Fighter& f, int turn, Side& self, Side& other, float& damage) {
    damage += f.strength;
    return turn < f.next_cast ? 1 : cast(f, turn, self, other, damage);
}

// f(i) for each member i of a side of `N` members (0: `count`), unrolled for a fixed N.
template <int N, typename F>
[[gnu::always_inline]] inline void each(int count, F&& f) {
    if constexpr (N > 0) [&]<int... I>(std::integer_sequence<int, I...>) { (f(I), ...); }(std::make_integer_sequence<int, N>{});
    else
        NO_UNROLL
        for (int i = 0; i < count; ++i) f(i);
}

// Bit i: fighters[i] is stunned, the strongest of those in reach first. `N`: self.count, or 0.
template <int N>
unsigned stun_skips(const Side& self, int turn) {
    unsigned skip = 0;
    NO_UNROLL
    for (int k = 0; k < self.stunned; ++k) {
        int best = -1;
        each<N>(self.count, [&](int i) {
            const auto& f = self.fighters[i];
            if (!(skip >> i & 1) && f.health > 0 && f.arrives_at <= turn && !f.stun_immune
                && (best < 0 || f.strength > self.fighters[best].strength))
                best = i;
        });
        if (best < 0) break;
        skip |= 1u << best;
    }
    return skip;
}

// One side's turn: stunned members (the strongest of those in reach first) skip it. `N`:
// self.count for the common sizes, for which the loops unroll, or 0.
template <int N>
[[gnu::noinline]] float act(Side& self, Side& other) {
    const int turn = self.turn++;
    // Nothing of this turn changes their weakest. A Ren there hits back each of ours by its hits.
    const int target = other.weakest();
    const float back = target >= 0 ? other.fighters[target].retaliation : 0.0f;
    // With `back`: each member's hits, the first `count` written. Static, as a stack frame costs more.
    static std::array<int, max_fighters> hits;
    const int count = N > 0 ? N : self.count;
    float damage = 0;
    if (self.stunned == 0 && turn < self.quiet_until && self.alive == self.quiet_alive) {
        damage = self.quiet_damage;
        if (target >= 0) other.hurt(damage, target);
        // With no cast each living attacker takes one reflection; no per-member hit tape is needed.
        if (back > 0)
            each<N>(count, [&](int i) {
                const auto& f = self.fighters[i];
                if (f.health > 0 && f.arrives_at <= turn) self.hurt_one(i, back);
            });
        return damage;
    } else if (self.plain) {
        // Sums of plain kits are exact in any order: the members in reach, less the stunned, plus the casts.
        const unsigned skip = self.stunned == 0 ? 0u : stun_skips<N>(self, turn);
        self.stunned = 0;
        if (self.alive != self.quiet_alive || turn >= self.arrival) {
            float quiet = 0;
            int arrival = never;
            each<N>(count, [&](int i) {
                if (const auto& f = self.fighters[i]; f.health <= 0) return;
                else if (f.arrives_at <= turn) quiet += f.strength;
                else arrival = std::min(arrival, f.arrives_at);
            });
            self.quiet_alive = self.alive;
            self.quiet_damage = quiet;
            self.arrival = arrival;
        }
        damage = self.quiet_damage;
        for (unsigned left = skip; left; left &= left - 1) damage -= self.fighters[std::countr_zero(left)].strength;
        int until = self.arrival;
        each<N>(count, [&](int i) {
            auto& f = self.fighters[i];
            if (back > 0) hits[i] = f.health > 0 && f.arrives_at <= turn && !(skip >> i & 1);
            if (f.health <= 0 || f.arrives_at > turn) return;
            if (f.next_cast <= turn && !(skip >> i & 1)) {
                const int h = cast(f, turn, self, other, damage);
                if (back > 0) hits[i] = h;
            }
            until = std::min(until, f.next_cast);
        });
        self.quiet_until = until;
    } else {
        const unsigned skip = self.stunned == 0 ? 0u : stun_skips<N>(self, turn);
        self.stunned = 0;
        int until = std::numeric_limits<int>::max();
        float quiet = 0;
        each<N>(count, [&](int i) {
            auto& f = self.fighters[i];
            if (f.shield_until <= turn) f.shield = 0, f.shield_until = never, self.lowered(i);
            if (back > 0) hits[i] = 0;
            if (f.health <= 0) return;
            if (f.arrives_at <= turn && !(skip >> i & 1)) {
                const int h = attack(f, turn, self, other, damage);
                if (back > 0) hits[i] = h;
            }
            until = std::min(until, f.shield_until);
            if (f.arrives_at > turn + 1) {
                until = std::min(until, f.arrives_at);
                return;
            }
            quiet += f.strength;
            until = std::min(until, f.next_cast);
        });
        self.quiet_until = until;
        self.quiet_alive = self.alive;
        self.quiet_damage = quiet;
    }
    if (target < 0) return damage;
    other.hurt(damage, target);
    if (back > 0)
        each<N>(count, [&](int i) {
            if (hits[i] > 0) self.hurt_one(i, static_cast<float>(hits[i]) * back);
        });
    return damage;
}

float act(Side& self, Side& other) {
    switch (self.count) {
    case 1: return act<1>(self, other);
    default: return act<0>(self, other);
    }
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
[[gnu::noinline]] int play_shielded(Side& us, Side& them, Fighter& u, Fighter& e, int t, int end, bool they_first) {
    // Camp hits on another of ours: act() plays it.
    if (us.camp > 0 && us.self >= 0 && &us.fighters[us.self] != &u && us.fighters[us.self].health > 0) return t;
    // Each as hurt() takes it, through the target's Durability.
    const float camp = us.camp * u.taken, on_us = them.quiet_damage * u.taken, on_them = us.quiet_damage * e.taken;
    for (; t < end; ++t) {
        float us_ = u.shield, uh = u.health, es = e.shield, eh = e.health;
        if ((t % 2 == 0) == they_first) {
            if (them.turn >= them.quiet_until || them.alive != them.quiet_alive || them.stunned != 0) break;
            if (!takes(on_us, us_, uh) || !takes(camp, us_, uh)) break;
            ++them.turn;
        } else {
            if (us.turn >= us.quiet_until || us.alive != us.quiet_alive || us.stunned != 0) break;
            if (!takes(on_them, es, eh)) break;
            ++us.turn;
        }
        u.shield = us_, u.health = uh, e.shield = es, e.health = eh;
    }
    return t;
}

// Quiet attacks with reflection, stopping before any shield or death needs act().
int play_reflected(Side& us, Side& them, int t, int end, bool they_first) {
    for (; t < end; ++t) {
        const bool their_turn = (t % 2 == 0) == they_first;
        Side& self = their_turn ? them : us;
        Side& other = their_turn ? us : them;
        if (self.turn >= self.quiet_until || self.alive != self.quiet_alive || self.stunned) break;
        const int weak = other.weakest();
        if (weak < 0) break;
        auto& target = other.fighters[weak];
        const float damage = self.quiet_damage * target.taken, back = target.retaliation;
        if (target.shield != 0 || !(damage < target.health)) break;
        Fighter* camp = nullptr;
        float camp_hit = 0;
        if (their_turn && us.camp > 0) {
            camp = us.self >= 0 && us.fighters[us.self].health > 0 ? &us.fighters[us.self] : &target;
            camp_hit = us.camp * camp->taken;
            if (camp->shield != 0 || !(camp_hit < camp->health - (camp == &target ? damage : 0.0f))) break;
        }
        bool safe = true;
        if (back > 0) {
            NO_UNROLL
            for (int i = 0; i < self.count; ++i) {
                const auto& f = self.fighters[i];
                if (f.health > 0 && f.arrives_at <= self.turn && (f.shield != 0 || !(back * f.taken < f.health))) {
                    safe = false;
                    break;
                }
            }
        }
        if (!safe) break;
        target.health -= damage;
        if (back > 0) {
            NO_UNROLL
            for (int i = 0; i < self.count; ++i) {
                auto& f = self.fighters[i];
                if (f.health > 0 && f.arrives_at <= self.turn) f.health -= back * f.taken;
            }
            self.weak = -2;
        }
        if (camp) {
            camp->health -= camp_hit;
            if (us.self >= 0) us.lowered(us.self);
        }
        ++self.turn;
    }
    return t;
}

// The half-turns from `t` (to `end` at most) in which both sides only make their basic attacks
// and nobody falls, each taken off the side's weakest as act() and hurt() would; returns the next.
int play_quiet(Side& us, Side& them, int t, int end, bool they_first) {
    const int wu = us.weakest(), we = them.weakest();
    if (wu < 0 || we < 0) return t;
    auto& u = us.fighters[wu];
    auto& e = them.fighters[we];
    if (u.retaliation > 0 || e.retaliation > 0) return play_reflected(us, them, t, end, they_first);
    if (u.shield != 0 || e.shield != 0) return play_shielded(us, them, u, e, t, end, they_first);
    // The camps hit us (hurt_by_camps()), who may not be the weakest.
    Fighter* s = us.camp > 0 && us.self >= 0 && us.self != wu && us.fighters[us.self].health > 0 ? &us.fighters[us.self] : nullptr;
    if (s && s->shield != 0) return t;
    const float camp = s ? 0.0f : us.camp * u.taken, on_self = s ? us.camp * s->taken : 0.0f;
    // Neither side's alive or stunned changes in here: only their turns run out.
    const int their_end = them.alive == them.quiet_alive && them.stunned == 0 ? them.quiet_until : them.turn;
    const int our_end = us.alive == us.quiet_alive && us.stunned == 0 ? us.quiet_until : us.turn;
    const float on_us = them.quiet_damage * u.taken, on_them = us.quiet_damage * e.taken;
    float uh = u.health, eh = e.health;
    int their_turn = them.turn, our_turn = us.turn;
    for (; t < end; ++t) {
        if ((t % 2 == 0) == they_first) {
            if (their_turn >= their_end) break;
            if (!(on_us < uh)) break;
            const float h = uh - on_us;
            if (camp > 0 && !(camp < h)) break;
            if (s && !(on_self < s->health)) break;
            uh = camp > 0 ? h - camp : h;
            ++their_turn;
            if (s) {
                u.health = uh;
                s->health -= on_self;
                us.lowered(us.self);
                // Now the weakest: their damage lands on us from here.
                if (us.weak != wu) {
                    ++t;
                    break;
                }
            }
        } else {
            if (our_turn >= our_end) break;
            if (!(on_them < eh)) break;
            eh -= on_them;
            ++our_turn;
        }
    }
    u.health = uh, e.health = eh;
    them.turn = their_turn, us.turn = our_turn;
    return t;
}

// Own turns a fight is played for: every slot ready at the start is cast on turns 0, 8 and 16,
// and kills land just after those casts.
constexpr int fight_horizon = 2 * ability_cooldown + 1;

// Our fighter's health, as its linked body's falls with it.
float watched_health(const Side& us, int self) {
    const auto& me = us.fighters[self];
    const float health = me.health / me.taken;
    return me.link >= 0 ? std::min(health, us.fighters[me.link].health / us.fighters[me.link].taken) : health;
}

// The least damage that fells every member of ours: each one's health, but a linked pair falls
// with the first of its bodies.
float side_health(const Side& us) {
    float total = 0, linked = std::numeric_limits<float>::max();
    NO_UNROLL
    for (int i = 0; i < us.count; ++i)
        if (const auto& f = us.fighters[i]; f.health <= 0) continue;
        else if (f.link >= 0) linked = std::min(linked, f.health / f.taken);
        else total += f.health / f.taken;
    return linked < std::numeric_limits<float>::max() ? total + linked : total;
}

// A bound's sum with room for float rounding: the bounds only skip the simulation when it is sure.
constexpr float rounded_up(float x) { return x * 1.001f + 1.0f; }

// Remaining casts and largest reflection, assuming every living enemy survives to the horizon.
float their_rest(const Side& them, int horizon, float& back) {
    float casts = 0;
    back = 0;
    NO_UNROLL
    for (int i = 0; i < them.count; ++i) {
        const auto& f = them.fighters[i];
        if (f.health <= 0) continue;
        back = std::max(back, f.retaliation);
        for (int s = 0; s < 2; ++s)
            if (const int first = std::max(them.turn, f.ready_at[s]); first < horizon)
                casts += static_cast<float>((horizon - first + ability_cooldown - 1) / ability_cooldown) * f.kit->cast[s].damage;
    }
    return casts;
}
struct Cap {
    float rate = 0, rest = -1; // a turn of theirs, and the casts (their_rest(); -1 until needed)
    float back = 0;
    float weakest = std::numeric_limits<float>::max(); // their weakest's health
    // Over their next `theirs` turns, with room for rounding, it falls short of `health`. The rest,
    // at least 0, is summed only if the basic attacks alone fall short: adding it cannot lower the sum.
    bool short_of(const Side& us, const Side& them, int horizon, int ours, int theirs, float health, bool watched = false) {
        const float basic = static_cast<float>(theirs) * rate;
        if (!(rounded_up(basic) < health)) return false;
        if (rest < 0) rest = their_rest(them, horizon, back);
        // Reflection hits only its attacker: a watched body takes at most its own two hits a turn.
        const float extra = back > 0 ? rest + static_cast<float>(2 * ours * (watched ? 1 : us.alive)) * back : rest;
        return rounded_up(basic + extra) < health;
    }
};
Cap their_cap(const Side& us, const Side& them) {
    Cap c;
    float strength = 0;
    NO_UNROLL
    for (int i = 0; i < them.count; ++i) {
        const auto& f = them.fighters[i];
        if (f.health <= 0) continue;
        strength += f.strength;
        c.weakest = std::min(c.weakest, f.health);
    }
    c.rate = us.camp + strength;
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
    NO_UNROLL
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
    NO_UNROLL
    for (int i = 0; i < them.count; ++i) {
        const auto& f = them.fighters[i];
        if (f.health <= 0) continue;
        weakest = std::min(weakest, f.health);
        if (!f.stun_immune) strongest = std::max(strongest, f.strength);
        if (f.arrives_at == never) continue;
        least += static_cast<float>(std::max(0, theirs - std::max(0, f.arrives_at - them.turn))) * f.strength;
    }
    if (!(rounded_up(most) < weakest)) return false;
    least -= static_cast<float>(stuns) * strongest;
    // Our Durability takes at most this off each hit.
    least *= taken;
    return least > rounded_up(guard);
}

// Bounds on what overwhelmed() sums: `strength`, our arriving members' Strength each of our turns, is
// at most its damage, every other term of which is at least 0; `health`, our health, at most its guard.
struct Ours {
    float strength = 0, health = 0;
};
Ours our_bounds(const Side& us) {
    Ours o;
    NO_UNROLL
    for (int i = 0; i < us.count; ++i)
        if (const auto& f = us.fighters[i]; f.health > 0) {
            o.health += f.health;
            if (f.arrives_at != never) o.strength += f.strength;
        }
    return o;
}

// simulate()'s early end, asked at the start and as either side loses a member: when the fight is
// decided, the turns it takes them (0 or the horizon), else -1.
template <bool Dealt>
[[gnu::noinline]] int decided(const Side& us, const Side& them, int horizon, int ours_left, int theirs_left, int watched, int their_start,
                              bool* self_falls, bool* falls_unknown) {
    auto cap = their_cap(us, them);
    // Our fighter outlives the fight or, once it has fallen, the rest of ours do.
    if (cap.short_of(us, them, horizon, ours_left, theirs_left, watched >= 0 ? watched_health(us, watched) : side_health(us), watched >= 0)) return 0;
    // Asked only whether we lose: the rest of ours outlive it.
    if (falls_unknown && watched >= 0 && them.alive < their_start && cap.short_of(us, them, horizon, ours_left, theirs_left, side_health(us)))
        return *falls_unknown = true, 0;
    // Past their weakest, or with their basic attacks and the camps short of our health,
    // overwhelmed() is false.
    if (const auto o = our_bounds(us); static_cast<float>(ours_left) * o.strength < cap.weakest) {
        if (static_cast<float>(theirs_left) * cap.rate > o.health && overwhelmed(us, them, theirs_left, ours_left)) {
            if (watched >= 0) *self_falls = true;
            return horizon;
        }
    } else if constexpr (!Dealt) {
        debug_block({
            if (overwhelmed(us, them, theirs_left, ours_left)) std::printf("PREFILTER-MISMATCH %d overwhelmed\n", cambc::round_number());
        });
    }
    return -1;
}

// Turns each side needs to empty the other's pool, within `horizon` turns each, playing the fight
// out on the sides given. `self_falls`: whether our own fighter dies before their side does; with
// it, our fighter falling while all of theirs stand loses the fight there: a champion lost for
// nothing. `dealt`, for debug_fights: their first turn's damage, ours, then
// their first five turns', ours.
// With `self_falls` and not Dealt, a fight our fighter (or, once it has fallen, the rest of ours)
// must outlive ends at once as {0, 0}, and one they must win as {0, horizon}. With `falls_unknown` too, a fight the rest of ours must outlive
// once one of theirs has fallen ends as {0, 0}, setting it and leaving self_falls unknown.
template <bool Dealt = false>
std::pair<int, int> simulate(Side& us, Side& them, bool they_first, bool* self_falls = nullptr, int horizon = fight_horizon,
                             std::array<float, 4>* dealt = nullptr, bool* falls_unknown = nullptr,
                             bool* lost_unknown = nullptr) {
    int ours = 0, theirs = 0;
    int watched = self_falls ? us.self : -1;
    const int their_start = them.alive;
    if (!Dealt && self_falls && 2 * horizon > 0)
        if (const int end = decided<Dealt>(us, them, horizon, horizon, horizon, watched, their_start, self_falls, falls_unknown); end >= 0) return {0, end};
    // Members fall only in act() and the camps' hits, so the checks after one wait for a change of
    // `alive`; -1: the first act is checked, for sides that start without a member standing.
    int alive = us.alive + 16 * them.alive;
    if (us.alive == 0 || them.alive == 0 || (watched >= 0 && us.fighters[watched].health <= 0)) alive = -1;
    for (int t = 0; t < 2 * horizon; ++t) {
        // play_quiet() makes no move unless the side to act is quiet.
        if (const Side& next = (t % 2 == 0) == they_first ? them : us;
            !Dealt && us.turn < us.quiet_until && them.turn < them.quiet_until && next.stunned == 0 && next.alive == next.quiet_alive) {
            const int our_turn = us.turn, their_turn = them.turn;
            t = play_quiet(us, them, t, 2 * horizon, they_first);
            ours += us.turn - our_turn, theirs += them.turn - their_turn;
            if (t == 2 * horizon) break;
        }
        if constexpr (!Dealt)
            if (t % 8 == 7) throw_if_stale();
        const bool their_turn = (t % 2 == 0) == they_first;
        if (their_turn) {
            const float d = act(them, us);
            if constexpr (Dealt)
                if (theirs < 5) (*dealt)[2] += d, (*dealt)[0] += theirs == 0 ? d : 0;
            if (us.camp > 0) us.hurt_by_camps();
            ++theirs;
        } else {
            const float d = act(us, them);
            if constexpr (Dealt)
                if (ours < 5) (*dealt)[3] += d, (*dealt)[1] += ours == 0 ? d : 0;
            ++ours;
        }
        if (const int now = us.alive + 16 * them.alive; now != alive) {
            alive = now;
            // Ren's reflection can fell the side whose turn it is.
            if (watched >= 0 && us.fighters[watched].health <= 0) {
                *self_falls = true, watched = -1;
                if (them.alive == their_start) return {0, std::max(1, theirs)};
                if (lost_unknown) return *lost_unknown = true, std::pair{0, 0};
            }
            if (us.alive == 0) return {0, std::max(1, theirs)};
            if (them.count > 0 && them.alive == 0) return {std::max(1, ours), 0};
            if (!Dealt && self_falls && t + 1 < 2 * horizon)
                if (const int end = decided<Dealt>(us, them, horizon, horizon - ours, horizon - theirs, watched, their_start, self_falls, falls_unknown); end >= 0)
                    return {0, end};
        }
    }
    return {0, 0};
}

// An idle holder's own turns only expire its shield. Reflections and the attackers'
// casts still run through act(), including deaths caused by Ren's passive.
int simulate_idle(Side& us, Side& them, int horizon) {
    auto& f = us.fighters[0];
    for (int turn = 0; turn < horizon; ++turn) {
        act(them, us);
        if (us.camp > 0) us.hurt_by_camps();
        if (us.alive == 0) return turn + 1;
        if (them.count > 0 && them.alive == 0) return 0;
        if (turn % 4 == 3) throw_if_stale();
        if (!us.plain && f.shield_until <= turn) f.shield = 0, f.shield_until = never;
        us.stunned = 0;
    }
    return 0;
}

constinit std::array<Side, 2> debug_sides{};

// Plays the fight out on the sides given, which callers discard: copying them is costly.
Trade trade(Side& us, Side& them, bool they_first = true, bool need_falls = true, bool settle = false) {
    Trade t;
    t.allies = us.count;
    t.enemies = them.count;
    if constexpr (debug_fights) t.our_health = us.health(), t.their_health = them.health();
    if (them.count == 0) return t;
    if constexpr (check_fight_exits) debug_block({ debug_sides = {us, them}; });
    bool unknown = false, lost_unknown = false;
    const auto [we_kill, they_kill] = simulate<debug_fights>(us, them, they_first, &t.self_falls, fight_horizon, debug_fights ? &t.dealt : nullptr,
                                                             need_falls ? nullptr : &unknown, settle && need_falls && !debug_fights ? &lost_unknown : nullptr);
    t.falls_known = !unknown;
    t.lost_known = !lost_unknown;
    if constexpr (check_fight_exits) debug_block({
        // An early end (outlives, overwhelmed) must agree with the fight played out.
        bool falls = false;
        std::array<float, 4> dealt{};
        const auto [a, b] = simulate<true>(debug_sides[0], debug_sides[1], they_first, &falls, fight_horizon, &dealt);
        if ((t.lost_known && (b > 0) != (they_kill > 0)) || (t.falls_known && falls != t.self_falls))
            std::printf("FIGHT-EXIT-MISMATCH %d %d %d %d %d\n", cambc::round_number(), b, they_kill, falls, t.self_falls);
    });
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
    static std::array<unsigned, 16> side;
    if (round != world.round) {
        round = world.round;
        self = seen = 0;
        for (std::size_t i = 0; i < world.allies.size() && i < x0.size(); ++i) {
            const auto& a = world.allies[i];
            if (!a.alive) continue;
            if (a.is_self) self |= 1u << i;
            // An ally posting a chase joins from farther, after its walk (walk_allies_in).
            else if (a.visible) {
                const int r = comms::ally_chasing(world, a) ? chasing_ally_radius : fight_ally_radius;
                seen |= 1u << i, x0[i] = a.pos.x - r, y0[i] = a.pos.y - r, side[i] = static_cast<unsigned>(2 * r);
            }
        }
    }
    std::uint32_t out = self;
#if defined(__wasm_simd128__)
    const v128_t x = wasm_i32x4_splat(p.x), y = wasm_i32x4_splat(p.y);
    for (unsigned left = seen; left;) {
        const int i = std::countr_zero(left) & ~3;
        left &= ~(15u << i);
        const v128_t widths = wasm_v128_load(&side[i]);
        const v128_t in = wasm_v128_and(wasm_u32x4_le(wasm_i32x4_sub(x, wasm_v128_load(&x0[i])), widths),
                                        wasm_u32x4_le(wasm_i32x4_sub(y, wasm_v128_load(&y0[i])), widths));
        out |= (static_cast<unsigned>(wasm_i32x4_bitmask(in)) << i) & seen;
    }
#else
    for (unsigned left = seen; left; left &= left - 1) {
        const auto i = static_cast<std::size_t>(std::countr_zero(left));
        const bool in = static_cast<unsigned>(p.x - x0[i]) <= side[i];
        if (in & (static_cast<unsigned>(p.y - y0[i]) <= side[i])) out |= 1u << i;
    }
#endif
    return out;
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
    if (turn_lost(c)) {
        // From the turn the stun takes, as an ally's below.
        make_fighter(c, next_turn_round(world, c) - 1, m.fighter[slot], m.kit[slot]);
        m.fighter[slot].arrives_at = 1;
        return;
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
    else if (c.stun_pending) f.arrives_at = 1;
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
        plain = plain && g.kit->plain;
        link_bodies(side.fighters, count);
        alive += g.health > 0;
        ++count;
    }
    side.count = count;
    side.alive = alive;
    side.plain = plain;
}

// Where it strikes from: a visible enemy's teleport lands before it acts.
vec2 acts_from(const ChampionBelief& e) { return e.teleport_pending() && in_bounds(e.tp_dest) ? e.tp_dest : e.pos; }

} // namespace

bool turn_lost(const ChampionBelief& c) { return c.side == team::enemy && c.visible && c.stun_pending; }

int attack_reach_in_turn(const ChampionBelief& c, int round) {
    const auto& f = c.facts();
    const int basic = f.basic_reach(), walk = f.ranged ? 0 : 1; // a ranged walk spends the attack
    // Ours read live: our belief's cooldowns are not read again after a cast this turn.
    const auto ready = [&](int s) {
        if (!c.is_self) return c.ability_ready(s, round);
        try {
            return my_cooldown(s) <= round - static_cast<int>(round_now()); // it ticks at each of our turn ends
        } catch (const cambc::error&) {
            return c.ability_ready(s, round);
        }
    };
    int r = basic + walk;
    if (const int s = f.slot_of(AbilityKind::attack_reset); s >= 0 && f.ranged && ready(s)) r = std::max(r, basic + 1);
    if (const int s = f.slot_of(AbilityKind::dash); s >= 0 && ready(s)) r = std::max(r, basic + walk + dash_range);
    return r;
}

float ally_fall_value(const World& world, const ChampionBelief& o) {
    const auto& me = world.me();
    const float ours = my_health() + (me.shield_slot >= 0 ? shield_value(me.handle) : 0.0f);
    if (o.facts().passive == Passive::linked_pair && me.facts().passive == Passive::linked_pair) return my_max_health() + ours + 1;
    // Its life against ours: each full health, life and bag (params value units).
    const float theirs = o.max_health + params::life_value + params::gem_value * static_cast<float>(o.gems);
    const float own = my_max_health() + params::life_value + params::gem_value * static_cast<float>(me.gems);
    return ours * std::min(1.0f, theirs / own);
}

float max_group_strength(const World& world) {
    static float most = -1;
    if (most < 0) {
        most = 0;
        for (const auto& g : world.map().groups) most = std::max(most, g.strength);
    }
    return most;
}

float partner_bound(const World& world, const ChampionBelief& e) {
    const auto* p = linked_partner(world, e);
    if (!p || !p->alive || !p->visible || test(world.map().enemy_spawn, p->pos)) return no_partner_bound;
    for (const auto& a : world.allies) {
        if (!a.alive || !(a.is_self || (a.visible && !a.stun_pending && a.channel != Channel::teleport))) continue;
        if (dist(a.is_self ? my_position() : a.pos, p->pos) <= attack_reach_in_turn(a, world.round + 1)) return p->health;
    }
    return no_partner_bound;
}

int next_turn_round(const World& world, const ChampionBelief& c) {
    // Read for those in sight; ranks are a guess when priorities change unseen.
    if (c.teleport_pending()) return std::max(c.acted ? world.round + 1 : world.round, c.channel_end_round);
    if (c.visible && !c.is_self) return (c.acted ? world.round + 1 : world.round) + (turn_lost(c) ? 1 : 0);
    if (c.side == team::enemy) return enemy_may_act_after_us(world, c) ? world.round : world.round + 1;
    return world.slot(c, world.round) > world.my_slot_now() ? world.round : world.round + 1;
}

namespace {

// Movement and ability ranges are static; only Strength and Focus change between strikes.
struct StrikeFormula {
    alignas(16) std::array<float, 8> basic{}, focus{}, added{};
    std::array<bool, Strike::max_reach + 1> stuns{};
    int reach = -1;
    bool valid = true;
};

constexpr StrikeFormula strike_formula(const ChampionFacts& f, unsigned slots, bool moved) {
    StrikeFormula out;
    std::array<float, 8> pure{}, combined{};
    const int range = f.attack_range(), basic = f.basic_reach();
    const int walk = f.ranged || moved ? 0 : 1;
    const auto add = [&](int reach, float strength, float focus, bool stuns) {
        reach = std::min(reach, Strike::max_reach);
        for (int d = 0; d <= reach; ++d) {
            if (focus > 0) {
                auto& term = strength > 0 ? combined[d] : pure[d];
                term = std::max(term, focus);
            } else out.basic[d] = std::max(out.basic[d], strength);
            out.stuns[d] = out.stuns[d] || stuns;
        }
        out.reach = std::max(out.reach, reach);
    };
    add(basic + walk, 1, 0, false);
    for (int slot = 0; slot < 2; ++slot) {
        if (!(slots >> slot & 1)) continue;
        const auto& a = f.abilities[slot];
        switch (a.kind) {
        case AbilityKind::attack_reset:
            add(basic + walk, 2, 0, a.stuns);
            if (f.ranged && !moved) add(basic + 1, 1, 0, a.stuns);
            break;
        case AbilityKind::dash: {
            const int travel = moved ? 0 : a.range();
            add(basic + walk + travel, 1, 0, false);
            if (a.lands()) {
                add(walk + travel + a.radius, 0, a.multiplier, a.stuns);
                add(walk + travel + std::min(range, a.radius), 1, a.multiplier, a.stuns);
            }
            break;
        }
        case AbilityKind::damage:
            add(a.reach(), 0, a.multiplier, a.stuns);
            add(range, 1, a.multiplier, a.stuns);
            break;
        case AbilityKind::stun: add(a.reach() + (a.excludes_walking || moved ? 0 : 1), 0, 0, true); break;
        default: break;
        }
    }
    for (int d = 0; d <= Strike::max_reach; ++d) {
        // For these kits, a spell with a basic attack dominates every spell without one at that distance.
        if (combined[d] > 0) {
            out.valid &= combined[d] >= pure[d];
            out.focus[d] = combined[d], out.added[d] = 1;
        } else out.focus[d] = pure[d];
    }
    return out;
}

constexpr auto strike_formulas = [] {
    std::array<std::array<StrikeFormula, 8>, champion_table.size()> out{};
    for (std::size_t i = 0; i < out.size(); ++i)
        for (unsigned k = 0; k < 8; ++k) out[i][k] = strike_formula(champion_table[i], k & 3u, k >= 4);
    return out;
}();
static_assert([] {
    for (const auto& champion : strike_formulas)
        for (const auto& f : champion)
            if (!f.valid) return false;
    return true;
}());

Strike compute_strike(const ChampionFacts& f, float s, float focus, unsigned slots, bool moved = false) {
    const auto& formula = strike_formulas[&f - champion_table.data()][slots + (moved ? 4 : 0)];
    Strike out;
#if defined(__wasm_simd128__)
    const v128_t strength = wasm_f32x4_splat(s), power = wasm_f32x4_splat(focus);
    const auto four = [&](int i) {
        return wasm_f32x4_max(wasm_f32x4_mul(wasm_v128_load(&formula.basic[i]), strength),
                             wasm_f32x4_add(wasm_f32x4_mul(wasm_v128_load(&formula.focus[i]), power),
                                            wasm_f32x4_mul(wasm_v128_load(&formula.added[i]), strength)));
    };
    wasm_v128_store(out.damage.data(), four(0));
    const v128_t high = four(4);
    out.damage[4] = wasm_f32x4_extract_lane(high, 0);
    out.damage[5] = wasm_f32x4_extract_lane(high, 1);
    out.damage[6] = wasm_f32x4_extract_lane(high, 2);
#else
    for (int d = 0; d <= Strike::max_reach; ++d)
        out.damage[d] = std::max(formula.basic[d] * s, formula.focus[d] * focus + formula.added[d] * s);
#endif
    out.stuns = formula.stuns;
    out.reach = formula.reach;
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
    // compute_strike's `moved` strike, and its widening (ahead_slots: the second turn's).
    bool standing_known, ahead_known;
    std::uint8_t ahead_slots;
    Strike standing, ahead;
};

// Static storage starts zeroed, and a zeroed memo is not valid: no constructor writes it all on
// first use.
union StrikeMemos {
    constexpr StrikeMemos() {}
    std::array<std::array<StrikeMemo, 4>, 16> by_champion;
};

StrikeMemo& strike_slots(const ChampionBelief& c, unsigned slots) {
    static StrikeMemos memo;
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
        m.widened_known = m.standing_known = m.ahead_known = false;
    }
    return m;
}

StrikeMemo& strike_memo(const ChampionBelief& c, int turn_round) {
    const bool uncertain = c.cooldowns_uncertain();
    const unsigned slots =
        (uncertain || c.ability_ready(0, turn_round) ? 1u : 0u) | (uncertain || c.ability_ready(1, turn_round) ? 2u : 0u);
    return strike_slots(c, slots);
}

} // namespace

const Strike& strike(const ChampionBelief& c, int turn_round) { return strike_memo(c, turn_round).value; }

const Strike& strike_with(const ChampionBelief& c, unsigned slots) { return strike_slots(c, slots).value; }

int turns_before_ours(const World& world, const ChampionBelief& c) {
    // An enemy's order is a window (turn_window.h): unseen, it may still act this round while an
    // enemy turn after ours is unaccounted for; next round, the likeliest few take the slots before ours.
    const bool enemy = c.side == team::enemy;
    const bool now = c.visible ? !c.acted : enemy ? enemy_may_act_after_us(world, c) : world.slot(c, world.round) > world.my_slot_now();
    // A teleport's channel turns are not its own.
    const int from = c.teleport_pending() ? c.channel_end_round : world.round;
    const bool next = enemy ? enemy_turn_before_ours_next(world, c) : world.slot(c, world.round + 1) < world.my_slot_next();
    const int turns = (now && from <= world.round ? 1 : 0) + (from <= world.round + 1 && next ? 1 : 0);
    return turn_lost(c) ? std::max(0, turns - 1) : turns;
}

namespace {

// turns_before_ours(), worked out on first need and kept by the caller (-1: not yet).
int turns_before_ours(const World& world, const ChampionBelief& c, int& known) {
    if (known < 0) known = turns_before_ours(world, c);
    return known;
}

bool enemy_blow_repeats(const World& world, const ChampionBelief& e, int& turns) {
    if (!e.visible || e.acted || turn_lost(e)) return false;
    if (e.teleport_pending() && e.channel_end_round > world.round) return false;
    return turns_before_ours(world, e, turns) < 2;
}

} // namespace

bool enemy_blow_repeats(const World& world, const ChampionBelief& e) {
    int turns = -1;
    return enemy_blow_repeats(world, e, turns);
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

bool engagement_near(const World& world, vec2 p, int reach, int margin) {
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible) continue;
        const int d = dist(p, e.pos);
        if (d <= reach + margin) return true;
        if (d > Strike::max_reach + margin) continue;
        if (const int r = threat_strike(world, e).reach + margin; d <= r && enemy_reach::within(world, e, acts_from(e), p, r)) return true;
    }
    return false;
}

// threat_strike() for an unseen enemy whose turn this round `possible` already holds: that turn's
// strike from where it ended, and with a second turn before ours (next round) either that turn's
// full strike or this one's and a second basic attack.
const Strike& moved_strike(const World& world, const ChampionBelief& c, StrikeMemo& m, int round, int& turns) {
    const auto& f = c.facts();
    const float hs = hit_strength(c), hf = hit_focus(c);
    if (!m.standing_known) m.standing_known = true, m.standing = compute_strike(f, hs, hf, m.slots, true);
    const auto& st = m.standing;
    if (turns_before_ours(world, c, turns) < 2) return st;
    const auto& m2 = strike_memo(c, round + 1);
    const auto& s2 = m2.value;
    if (m.ahead_known && m.ahead_slots == m2.slots) return m.ahead;
    m.ahead_known = true;
    m.ahead_slots = m2.slots;
    const int basic_reach = f.basic_reach() + (f.ranged ? 0 : 1);
    auto& out = m.ahead;
    for (int d = 0; d <= Strike::max_reach; ++d) {
        const float twice = st.hits(d) ? st.at(d) + (d <= basic_reach ? hs : 0.0f) : 0.0f;
        out.damage[d] = std::max(s2.at(d), twice);
        out.stuns[d] = s2.stuns[d] || st.stuns[d];
    }
    out.reach = std::max(s2.reach, st.reach);
    return out;
}

namespace {

const Strike& threat_strike(const World& world, const ChampionBelief& c, int& turns) {
    static const Strike none;
    if ((c.teleport_pending() || turn_lost(c)) && turns_before_ours(world, c, turns) == 0) return none;
    const int round = next_turn_round(world, c);
    auto& m = strike_memo(c, round);
    const auto& s = m.value;
    if (s.reach < 0) return s;
    // Out of sight, `possible` already holds its turn later this round (World::track grows it past
    // that turn): the turn adds only what it does from where it ends.
    // With windows, an unseen enemy may act after us though its read slot is before ours: `possible`
    // grew by that slot, so holds this round's turn either way.
    if (!c.visible && c.side == team::enemy
        && (world.slot(c, world.round) > world.my_slot_now() || enemy_may_act_after_us(world, c))
        && !(c.at < Moment{world.round, world.slot(c, world.round)}))
        return moved_strike(world, c, m, round, turns);
    if (turns_before_ours(world, c, turns) < 2) return s;
    // Its second turn falls in the next round: a walk first, then what is ready by then.
    const auto& m2 = strike_memo(c, round + 1);
    const auto& s2 = m2.value;
    if (m.widened_known && m.widened_slots == m2.slots) return m.widened;
    m.widened_known = true;
    m.widened_slots = m2.slots;
    const auto& f = c.facts();
    const int basic_reach = f.basic_reach() + (f.ranged ? 0 : 1);
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

} // namespace

const Strike& threat_strike(const World& world, const ChampionBelief& c) {
    int turns = -1;
    return threat_strike(world, c, turns);
}

namespace {

// Window arithmetic by tables where it can: WASM loops and variable shifts cost fuel.
using Window = Reach::Window;
constexpr int win_r = Window::radius, win_n = Window::width;
static_assert(win_n <= 9); // chunk_window: a window spans at most 2x2 of a board's 8x8 chunks
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
    std::array<std::uint8_t, bytes> uncrossable; // walls and our spawn: no enemy dash path crosses them
    // By tile, any_near(bushes) and any_near(walls): the boards dilated by win_r, once `near_ready`.
    bool near_ready = false;
    std::array<std::uint8_t, bytes> near_bushes, near_walls;

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
        const int x0 = p.x - win_r, y0 = p.y - win_r;
        const int lo = std::max(0, -x0), hi = std::min(win_n, width - x0);
        const int a = x0 >> 3, s = x0 - 8 * a, c = y0 >> 3;
        const int down = (height + 7) / 8;
        const auto word = [&](int cy, int cx) -> std::uint64_t {
            return cy >= 0 && cy < down && cx >= 0 && cx < across ? words[static_cast<std::size_t>(cy * across + cx)] : 0;
        };
        const std::uint64_t w00 = word(c, a), w01 = word(c, a + 1), w10 = word(c + 1, a), w11 = word(c + 1, a + 1);
        // Insert one gap after each byte, packing four 8-bit rows into four 9-bit rows.
        const auto spread = [](std::uint32_t v) __attribute__((always_inline)) {
            std::uint64_t x = v;
            x = (x & 0xffffULL) | ((x & 0xffff0000ULL) << 2);
            return (x & (0xffULL | (0xffULL << 18))) | ((x & ((0xffULL << 8) | (0xffULL << 26))) << 1);
        };
        const std::uint64_t low = 0x0101010101010101ULL * ((1u << (8 - s)) - 1);
        const std::uint64_t high = 0x0101010101010101ULL * ((1u << (s + 1)) - 1);
        const auto pack = [&](std::uint64_t l, std::uint64_t r) __attribute__((always_inline)) {
            l = (l >> s) & low;
            r &= high;
            const auto first = spread(static_cast<std::uint32_t>(l)) | (spread(static_cast<std::uint32_t>(r)) << (8 - s));
            const auto last = spread(static_cast<std::uint32_t>(l >> 32)) | (spread(static_cast<std::uint32_t>(r >> 32)) << (8 - s));
            return Window{first | (last << 36), last >> 28};
        };
        const int skip = win_n * (y0 - 8 * c);
        const Window m = pack(w00, w01).shr(skip) | pack(w10, w11).shl(72 - skip);
        return m & tables.columns[lo][hi - 1] & tables.rows[std::max(0, -y0)][std::min(win_n - 1, height - 1 - y0)];
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
    {
        bitboard uncrossable;
        or_into(map.walls, map.ally_spawn, uncrossable);
        uncrossable.export_linear_buffer({t.uncrossable.data(), size});
    }
    map.bushes.export_linear_buffer({t.bushes.data(), size});
    map.camp_tiles.export_linear_buffer({t.camps.data(), size});
    t.packed = true;
}

const Terrain& terrain(const StaticMap& map) {
    if (!terrain_storage.ready) make_terrain(terrain_storage, map);
    return terrain_storage;
}

// Terrain::near_* (~2k on 100x100): built on first need after the first turn, whose double budget
// is already short on big maps; until then sight() scans rows.
[[gnu::noinline]] void make_near(Terrain& t, const StaticMap& map) {
    t.near_ready = true;
    static const bitboard open;
    static cambc::distance_field field;
    static bitboard dilated{cambc::uninitialized};
    const auto near = [&](const bitboard& b, std::array<std::uint8_t, Terrain::bytes>& out) {
        field.compute(open, b, dilated, static_cast<std::uint16_t>(win_r));
        dilated.export_linear_buffer({out.data(), bitboard::linear_buffer_size()});
    };
    near(map.bushes, t.near_bushes);
    near(map.walls, t.near_walls);
}

// The box around group g's members, as x0, x1, y0, y1; each worked out on first use, as all of
// them at once cost ~6k on a many-group map.
const std::array<int, 4>& member_box(const StaticMap& map, int g) {
    static std::vector<std::array<int, 4>> boxes;
    if (boxes.empty()) boxes.assign(map.groups.size(), {1, 0, 0, 0});
    auto& b = boxes[static_cast<std::size_t>(g)];
    if (b[0] > b[1]) {
        b = {1 << 20, -(1 << 20), 1 << 20, -(1 << 20)};
        for (const auto& m : map.groups[g].members)
            b = {std::min(b[0], m.pos.x), std::max(b[1], m.pos.x), std::min(b[2], m.pos.y), std::max(b[3], m.pos.y)};
    }
    return b;
}

bool live_member(const World& world, int group, int member) {
    const auto& c = world.camps[static_cast<std::size_t>(group)];
    return c.state == CampState::alive && c.health[static_cast<std::size_t>(member)] > 0;
}

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
// attack_viewers' bushes around a tile, laid out as a window: terrain only, so kept for the game.
std::array<Window, 100 * 100> bush_windows;
std::array<std::uint8_t, 100 * 100> bush_known;

// Who sees p, laid out around p: within 1 (`far` false) or within win_r. Far masks depend only on
// terrain, so they are kept for the game.
Window sight(const World& world, vec2 p, bool far, bool store = true) {
    const auto& t = terrain(world.map());
    if (!far) {
        if (!t.bush(p)) return tables.square[1];
        // A diagonal bush joins through either shared cardinal neighbour.
        if (t.packed) {
            const int x0 = p.x - 1;
            const unsigned b = (t.row(t.bushes, x0, p.y - 1) & 7)
                | ((t.row(t.bushes, x0, p.y) & 7) << 3)
                | ((t.row(t.bushes, x0, p.y + 1) & 7) << 6);
            const unsigned card = b & 0x0aa;
            const unsigned connected = b & (0x0ba | ((card & 0x082) >> 1) | ((card & 0x082) << 1)
                | ((card & 0x028) >> 3) | ((card & 0x028) << 3));
            return Window{static_cast<std::uint64_t>(connected & 7) << 30
                | static_cast<std::uint64_t>((connected >> 3) & 7) << 39
                | static_cast<std::uint64_t>(connected >> 6) << 48, 0};
        }
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
    if (t.packed && !t.near_ready && world.round > world.first_round) make_near(terrain_storage, map);
    const bool on = t.near_ready && t.inside(p);
    const int pi = p.x + p.y * t.width;
    const bool plain = t.packed && !(on ? Terrain::bit(t.near_bushes, pi) : t.any_near(t.bushes, p));
    if (plain && !(on ? Terrain::bit(t.near_walls, pi) : t.any_near(t.walls, p))) {
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
    const auto bush_rows = [&] {
        Window w;
        for (int r = 0; r < win_n; ++r)
            if (const std::uint32_t bits = t.row(t.bushes, target.x - win_r, target.y - win_r + r)) w |= Window{bits, 0}.shl(win_n * r);
        return w;
    };
    Window bush;
    if (t.inside(target)) {
        const auto i = static_cast<std::size_t>(target.x + target.y * t.width);
        if (!bush_known[i]) {
            // Beside a kept tile in y: its window moved by a row, and one new row (as static_window).
            const auto W = static_cast<std::size_t>(t.width);
            if (target.y > 0 && bush_known[i - W])
                bush_windows[i] = bush_windows[i - W].shr(win_n)
                                  | Window{t.row(t.bushes, target.x - win_r, target.y + win_r), 0}.shl(win_n * (win_n - 1));
            else if (target.y + 1 < t.height && bush_known[i + W])
                bush_windows[i] = bush_windows[i + W].shl(win_n) | Window{t.row(t.bushes, target.x - win_r, target.y - win_r), 0};
            else
                bush_windows[i] = bush_rows();
            bush_known[i] = 1;
        }
        bush = bush_windows[i];
    } else {
        bush = bush_rows();
    }
    return (sight(world, target, true, store) & tables.square[range] & ~bush) | near;
}

Reach::Window seen_from(const World& world, vec2 p, int range) {
    range = std::clamp(range, 0, win_r);
    static bitboard seen{cambc::uninitialized};
    shadow_into(world.map().walls_and_bushes, p, static_cast<std::uint16_t>(range), seen);
    const auto& t = terrain(world.map());
    if (t.chunked) return t.chunk_window(seen.ptr(), p);
    Window m;
    for (const vec2 q : Tiles<win_n * win_n>{seen})
        m |= tables.bits[static_cast<std::size_t>((q.y - p.y + win_r) * win_n + q.x - p.x + win_r)];
    return m;
}

Reach::Window window_square(int range) { return tables.square[static_cast<std::size_t>(range)]; }

Reach::Window board_window(const World& world, const bitboard& board, vec2 centre) {
    const auto& t = terrain(world.map());
    if (t.chunked) return t.chunk_window(board.ptr(), centre);
    Window out;
    for (const vec2 p : positions_within(board, centre, win_r))
        out |= win_bit(p.x - centre.x + win_r, p.y - centre.y + win_r);
    return out;
}

namespace {

// sight() laid out around the enemy at p - (dx, dy). Out of line: inlined, the shift's constants
// were worked out on every Reach::at() call.
[[gnu::noinline]] Window sight_from(const World& world, vec2 p, bool far, int dx, int dy) { return shift(sight(world, p, far), dx, dy); }

// Static terrain around each tile, kept for the game: enemies keep to a few tiles. pass: a dash
// path may cross it (not a wall or our spawn); land: open to them; camps: camp tiles, whose
// monsters block while alive.
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
    // One row's masks: through (a dash path may cross), open (they may land), camp.
    const auto row_masks = [&](int y, std::uint32_t& open, std::uint32_t& through, std::uint32_t& camp) __attribute__((always_inline)) {
        open = 0, through = 0, camp = 0;
        if (t.packed) {
            if (columns != 0 && y >= 0 && y < t.height) {
                // Terrain::row() of each board, sharing the word offset.
                const int i = x0 + lo + y * t.width;
                const auto at = static_cast<std::size_t>(i >> 3);
                const int shift = i & 7;
                std::uint64_t uncrossable, blocked, camps;
                std::memcpy(&uncrossable, &t.uncrossable[at], sizeof uncrossable);
                std::memcpy(&blocked, &t.blocked[at], sizeof blocked);
                std::memcpy(&camps, &t.camps[at], sizeof camps);
                through = columns & ~(static_cast<std::uint32_t>((uncrossable >> shift) & width_mask) << lo);
                open = columns & ~(static_cast<std::uint32_t>((blocked >> shift) & width_mask) << lo);
                camp = static_cast<std::uint32_t>((camps >> shift) & width_mask) << lo;
            }
        } else {
            for (int k = 0; k < win_n; ++k) {
                const vec2 p{x0 + k, y};
                if (!t.inside(p) || test(world.map().walls, p)) continue;
                if (!test(world.map().ally_spawn, p)) through |= 1u << k;
                if (!test(world.map().blocked_for_them, p)) open |= 1u << k;
                if (world.map().group_at(p) >= 0) camp |= 1u << k;
            }
        }
    };
    Window pass, land, camps;
    // A tile beside one in y that is kept: its window moved by a row, and one new row.
    const int W = t.width;
    if (origin.y > 0 && scanned[oi - static_cast<std::size_t>(W)]) {
        const auto& b = statics[oi - static_cast<std::size_t>(W)];
        std::uint32_t open, through, camp;
        row_masks(origin.y + win_r, open, through, camp);
        constexpr int top = win_n * (win_n - 1);
        st = {b.pass.shr(win_n) | Window{through, 0}.shl(top), b.land.shr(win_n) | Window{open, 0}.shl(top),
              b.camps.shr(win_n) | Window{camp, 0}.shl(top)};
        return st;
    }
    if (origin.y + 1 < t.height && scanned[oi + static_cast<std::size_t>(W)]) {
        const auto& a = statics[oi + static_cast<std::size_t>(W)];
        std::uint32_t open, through, camp;
        row_masks(origin.y - win_r, open, through, camp);
        st = {a.pass.shl(win_n) | Window{through, 0}, a.land.shl(win_n) | Window{open, 0}, a.camps.shl(win_n) | Window{camp, 0}};
        return st;
    }
    // Unrolled, so that each row's place in the window is a constant shift.
    [&]<int... Row>(std::integer_sequence<int, Row...>) {
        (
            [&] {
                std::uint32_t open, through, camp;
                row_masks(origin.y - win_r + Row, open, through, camp);
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

} // namespace

int board_chunks_across(const StaticMap& map) {
    const auto& t = terrain(map);
    return t.chunked ? t.across : 0;
}

void warm_reach_tile(const World& world, vec2 p) {
    (void)static_window(world, p);
    (void)sight(world, p, true);
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
    const auto& f = e.facts();
    const bool uncertain = e.cooldowns_uncertain();
    const std::array<bool, 2> ready{uncertain || e.ability_ready(0, turn_round), uncertain || e.ability_ready(1, turn_round)};
    const std::array<bool, 2> ready2 =
        twice ? std::array<bool, 2>{ready[0] || e.ability_ready(0, turn_round + 1), ready[1] || e.ability_ready(1, turn_round + 1)} : ready;
    const int dash_slot = f.slot_of(AbilityKind::dash);
    const bool dash = dash_slot >= 0 && ready2[static_cast<std::size_t>(dash_slot)];
    enemy_ = &e;
    turn_round_ = turn_round;
    dash_ = dash;
    geometry_ready_ = false;
    build_ways(e, ready, ready2, twice);
}

void Reach::build_geometry() {
    geometry_ready_ = true;
    const auto& world = *world_;
    const auto& e = *enemy_;
    const auto& f = e.facts();
    const int turn_round = turn_round_;
    const bool twice = twice_, dash = dash_;
    splash_ = f.passive == Passive::splash_attack;
    const int sets_radius = splash_ ? win_r : (twice ? 1 : 0) + (dash ? (f.ranged ? 2 : 3) : 1);
    if (ways_->stationary && !splash_) {
        tiles_[here] = win_bit(win_r, win_r);
        extent_[here] = 0;
        set_bounds();
        return;
    }
    // Our champions around it, which block its walks and landings; they stay put through our turn.
    // Its next turn is worked out on first need: an ally's belief and the ranks change only at the
    // round's update (observe skips allies read this round).
    struct Ally {
        vec2 pos;
        int index;
        int round, slot; // its next turn, once known
        bool known;
    };
    static int allies_round = -1;
    static std::array<Ally, 8> allies;
    static int ally_count = 0;
    if (allies_round != world.round) {
        allies_round = world.round;
        ally_count = 0;
        for (int k = 0; k < static_cast<int>(world.allies.size()); ++k)
            if (const auto& a = world.allies[static_cast<std::size_t>(k)]; ally_count < static_cast<int>(allies.size()) && a.alive && a.visible && !a.is_self)
                allies[ally_count++] = {a.pos, k, 0, 0, false};
    }
    // A dash path is barred only by those of ours still standing at its last chance to dash. Without
    // a dash, pass is unread: fixed stays empty.
    const int last_round = twice ? turn_round + 1 : turn_round,
              last_slot = dash ? enemy_latest_slot(world, e, last_round) : 0;
    Window occupied, fixed, in_bushes;
    for (int i = 0; i < ally_count; ++i)
        if (const vec2 p = allies[i].pos; dist(p, origin_) <= sets_radius) {
            const Window bit = win_bit(p.x - origin_.x + win_r, p.y - origin_.y + win_r);
            occupied |= bit;
            if (!dash) continue;
            auto& ally = allies[i];
            if (!ally.known) {
                const auto& a = world.allies[static_cast<std::size_t>(ally.index)];
                ally.round = next_turn_round(world, a), ally.slot = world.slot(a, ally.round), ally.known = true;
            }
            if (ally.round > last_round || (ally.round == last_round && ally.slot > last_slot)) fixed |= bit;
            if (terrain(world.map()).bush(p)) in_bushes |= bit;
        }
    units_ = occupied;
    splash_known_ = 0;
    const auto kind = static_cast<std::uint8_t>(twice | dash << 1);
    if ((sets_reusable_ || (!splash_ && sets_built_ && sets_camps_version_ == world.camp_geometry_version))
        && sets_origin_ == origin_ && sets_kind_ == kind && sets_occupied_.lo == occupied.lo && sets_occupied_.hi == occupied.hi
        && sets_fixed_.lo == fixed.lo && sets_fixed_.hi == fixed.hi) {
        set_bounds();
        return;
    }
    sets_built_ = true;
    sets_camps_version_ = world.camp_geometry_version;
    sets_origin_ = origin_;
    sets_kind_ = kind;
    sets_occupied_ = occupied;
    sets_fixed_ = fixed;
    const auto& st = static_window(world, origin_);
    // A dash path crosses no champion of ours it sees; one in a bush is taken as unseen.
    Window pass = st.pass & ~(fixed & ~in_bushes), land = st.land & ~occupied;
    // The sets read the terrain only this far out (each walk or dash step one more), but Varg's
    // splash reads every live member.
    const Window camps = st.camps & tables.square[static_cast<std::size_t>(sets_radius)];
    sets_reusable_ = !camps;
    if (camps) {
        // A camp in a bush is unseen from outside its cluster, and a dash path may cross an unseen camp.
        const auto& t = terrain(world.map());
        Window live, solid;
        for (int word = 0; word < 2; ++word)
            for (std::uint64_t bits = word ? camps.hi : camps.lo; bits; bits &= bits - 1) {
                const int i = 64 * word + std::countr_zero(bits);
                const vec2 p{origin_.x - win_r + i % win_n, origin_.y - win_r + i / win_n};
                const int group = world.map().group_at(p), member = world.map().camp_member_at(p);
                if (group < 0 || member < 0 || !live_member(world, group, member)) continue;
                live |= tables.bits[static_cast<std::size_t>(i)];
                if (dash && !t.bush(p)) solid |= tables.bits[static_cast<std::size_t>(i)];
            }
        pass &= ~solid, land &= ~live;
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
    set_bounds();
}

void Reach::set_bounds() {
    for (int i = 0; i < ways_->count; ++i) bounds_[static_cast<std::size_t>(i)] = static_cast<std::int8_t>(bound(ways_->way[static_cast<std::size_t>(i)]));
}

void Reach::build_ways(const ChampionBelief& e, std::array<bool, 2> ready, std::array<bool, 2> ready2, bool twice) {
    const auto& f = e.facts();
    const float s = hit_strength(e), focus = hit_focus(e);
    const Recipe recipe{e.type, std::bit_cast<std::uint32_t>(s), std::bit_cast<std::uint32_t>(focus),
                        static_cast<std::uint8_t>(ready[0] | ready[1] << 1 | ready2[0] << 2 | ready2[1] << 3), twice, true};
    ways_ = &ways_by_[static_cast<std::size_t>(ready[0] + ready2[0] + 3 * (ready[1] + ready2[1]) + 9 * twice)];
    auto& ws = *ways_;
    if (recipe == ws.recipe) return;
    ws.recipe = recipe;
    // Ability geometry and equal-key merges depend only on the kit and ready slots.
    struct Term {
        Way way{};
        float basic = 0, pure = 0, combined = 0;
    };
    struct Pattern {
        std::array<Term, 14> terms{};
        int count = 0, basic = -1;
        bool stuns = false, stationary = true;
        int from_here_range = win_r;
    };
    static constexpr auto patterns = [] {
        std::array<std::array<Pattern, 18>, champion_table.size()> table{};
        for (std::size_t i = 0; i < table.size(); ++i)
            for (int k = 0; k < 18; ++k) {
                auto& out = table[i][k];
                const auto& f = champion_table[i];
                const bool twice = k >= 9;
                const int x = k % 9;
                const std::array<bool, 2> ready{x % 3 == 2, x / 3 == 2}, ready2{x % 3 != 0, x / 3 != 0};
                const auto add = [&](Tiles from, int range, bool sight, float strength, float focus, bool stuns, bool walked) {
                    const auto key = static_cast<std::uint8_t>(((from * 8 + range) * 2 + sight) * 2 + walked);
                    int j = 0;
                    while (j < out.count && out.terms[j].way.key != key) ++j;
                    if (j == static_cast<int>(out.terms.size())) return -1;
                    if (j == out.count) {
                        out.terms[j].way = {0, from, static_cast<std::int8_t>(range), key, sight, stuns, walked};
                        ++out.count;
                    }
                    out.stationary &= from == here;
                    out.from_here_range = std::min(out.from_here_range, range);
                    auto& t = out.terms[j];
                    t.way.stuns |= stuns;
                    out.stuns |= stuns;
                    if (focus > 0) {
                        auto& coefficient = strength > 0 ? t.combined : t.pure;
                        coefficient = std::max(coefficient, focus);
                    } else t.basic = std::max(t.basic, strength);
                    return j;
                };
                const Tiles basic_from = f.ranged ? here : walked1;
                const int range = f.attack_range();
                for (int turn = 0; turn < (twice ? 2 : 1); ++turn) {
                    const bool walked = turn == 1;
                    // A walk first, on the first of two turns.
                    const auto from = [&](Tiles x) { return !walked ? x : x == here ? walked1 : x == walked1 ? walked2 : dashed_walked; };
                    const int basic = add(from(basic_from), range, true, 1, 0, false, walked);
                    if (!walked) out.basic = basic;
                    for (std::size_t slot = 0; slot < 2; ++slot) {
                        if (!(walked ? ready2 : ready)[slot]) continue;
                        const auto& a = f.abilities[slot];
                        const float spell = a.multiplier;
                        switch (a.kind) {
                        case AbilityKind::attack_reset:
                            add(from(basic_from), range, true, 2, 0, a.stuns, walked);
                            if (f.ranged) add(from(walked1), range, true, 1, 0, a.stuns, walked); // walk, reset, attack
                            break;
                        case AbilityKind::dash:
                            add(from(dashed), range, true, 1, 0, false, walked);
                            // The landing hits unseen tiles too; the landings are taken as all of `dashed`.
                            if (a.lands()) {
                                add(from(dashed), a.radius, false, 0, spell, a.stuns, walked);
                                add(from(dashed), std::min(range, a.radius), true, 1, spell, a.stuns, walked);
                            }
                            break;
                        case AbilityKind::damage:
                            // Excludes walking but not the basic attack.
                            add(from(here), a.reach(), a.target == Targeting::unit, 0, spell, a.stuns, walked);
                            add(from(here), range, true, 1, spell, a.stuns, walked);
                            break;
                        case AbilityKind::stun:
                            add(from(a.excludes_walking ? here : walked1), a.reach(), a.target == Targeting::unit, 0, 0, true, walked);
                            break;
                        default: break;
                        }
                    }
                }

            }
        return table;
    }();
    static_assert([] {
        for (const auto& kit : patterns)
            for (const auto& pattern : kit)
                for (int i = 0; i < pattern.count; ++i)
                    if (pattern.terms[i].way.range < 1) return false;
        return true;
    }());
    const auto& pattern = patterns[&f - champion_table.data()][ready[0] + ready2[0] + 3 * (ready[1] + ready2[1]) + 9 * twice];
    ws.count = pattern.count;
    ws.basic = pattern.basic;
    ws.stuns = pattern.stuns;
    ws.from_here_range = pattern.from_here_range;
    ws.stationary = pattern.stationary;
    for (int i = 0; i < ws.count; ++i) {
        const auto& term = pattern.terms[i];
        auto& w = ws.way[i];
        w = term.way;
        w.damage = std::max(term.basic * s, std::max(term.pure * focus, term.combined > 0 ? term.combined * focus + s : 0.0f));
    }
    float single = -1, walked = -1;
    for (int i = 0; i < ws.count; ++i) {
        const auto& w = ws.way[i];
        if (w.walked) walked = std::max(walked, w.damage);
        else single = std::max(single, w.damage);
    }
    ws.from_here = {std::max({0.0f, walked, single < 0 ? 0.0f : single + (twice ? s : 0.0f)}), true, ws.stuns};
    // Largest damage first: a query stops at the first way that reaches it.
    for (int i = 1; i < ws.count; ++i)
        for (int j = i; j > 0 && ws.way[static_cast<std::size_t>(j)].damage > ws.way[static_cast<std::size_t>(j - 1)].damage; --j) {
            std::swap(ws.way[static_cast<std::size_t>(j)], ws.way[static_cast<std::size_t>(j - 1)]);
            if (ws.basic == j) ws.basic = j - 1;
            else if (ws.basic == j - 1) ws.basic = j;
        }
}

int Reach::reach() const {
    if (!geometry_ready_) const_cast<Reach*>(this)->build_geometry();
    int reach = -1;
    for (int i = 0; i < ways_->count; ++i) reach = std::max(reach, bound(ways_->way[static_cast<std::size_t>(i)]));
    return reach;
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
    if (const auto& t = terrain(world_->map()); t.inside(p)) {
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
        // Every movement set contains the origin. Seeing the target from there settles every way within this range.
        if (d <= ws.from_here_range
            && ((d <= 1 && !t.bush(p)) || (sight(*world_, p, d > 1) & win_bit(win_r - dx, win_r - dy)))) {
            memo = {p, ws.from_here, stamp_};
            return ws.from_here;
        }
        if (!geometry_ready_) const_cast<Reach*>(this)->build_geometry();
        int ward = -1;
        const auto seen = [&](bool far, Window& m) __attribute__((always_inline)) {
            if (ward < 0) {
                if (ward_ == unknown_ward) ward_ = ward_of(*world_, owner_);
                ward = ward_ >= 0 ? ward_sees(t, ward_, p) : t.bush(p) && !test(world_->visible, p);
            }
            m = ward ? win_full : sight_from(*world_, p, far, dx, dy);
        };
        for (int i = 0; i < ws.count; ++i) {
            if (d > bounds_[static_cast<std::size_t>(i)]) continue;
            const auto& w = ws.way[static_cast<std::size_t>(i)];
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
            // Remaining ways cannot beat this single turn; only a basic follow-up or stun is missing.
            if (single >= w.damage && (!twice_ || basic) && (!ws.stuns || out.stuns)) break;
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

// A big group's members as lanes for find_members, built on first use (members never move): tiles
// and reaches padded to whole vectors. Published map coordinates and their differences fit a
// signed byte. Bit i of `live`: member i strikes and is alive at this occupancy version.
struct MemberLanes {
    std::vector<std::int8_t> x, y, reach;
    std::vector<std::uint64_t> live;
    std::uint32_t version = 0;
    bool built = false;
};

const MemberLanes& member_lanes(const CampGroup& G, const CampBelief& c, int g) {
    static std::vector<MemberLanes> table;
    if (table.size() <= static_cast<std::size_t>(g)) table.resize(static_cast<std::size_t>(g) + 1);
    auto& t = table[static_cast<std::size_t>(g)];
    const std::size_t n = G.members.size();
    if (!t.built) {
        const std::size_t padded = (n + 15) & ~std::size_t{15};
        t.x.assign(padded, 0), t.y.assign(padded, 0), t.reach.assign(padded, 0);
        for (std::size_t i = 0; i < n; ++i) t.x[i] = static_cast<std::int8_t>(G.members[i].pos.x), t.y[i] = static_cast<std::int8_t>(G.members[i].pos.y), t.reach[i] = static_cast<std::int8_t>(G.members[i].reach);
        t.live.assign((n + 63) / 64, 0);
        t.built = true;
        t.version = c.geometry_version + 1;
    }
    if (t.version != c.geometry_version) {
        t.version = c.geometry_version;
        std::fill(t.live.begin(), t.live.end(), 0);
        for (std::size_t i = 0; i < n; ++i)
            if (c.health[i] > 0 && G.members[i].strength > 0) t.live[i >> 6] |= std::uint64_t{1} << (i & 63);
    }
    return t;
}

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

Safety::Safety(const World& world) : world_{world}, threats_{threat_pool()}, members_{member_pool()} { ++generation_, ++hold_generation_; }

std::span<const Safety::CampHit> Safety::awake_members() {
    if (!members_known_) find_members();
    return {members_.data(), static_cast<std::size_t>(member_count_)};
}

[[gnu::noinline]] void Safety::find_members() {
    members_known_ = true;
    ++members_found;
    int count = 0;
    tie_only_count_ = 0;
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
            o.first = enemy_latest_slot(world_, *o.belief, next) < self_slot ? 1 : 0;
        }
        return static_cast<int>(o.first);
    };
    const bool reread = refresh_;
    const auto& groups = world_.map().groups;
    // Allies done acting that some group could fell (into others), and whether an ally is yet to act.
    std::array<std::int8_t, 4> fallers;
    int n_fallers = 0;
    bool later = false;
    float ours = -1; // our health and shield, read where a group could fell us
    // Members whose hit falls on a faller: shields (camp_total_) once every hit on it is summed.
    struct Onto {
        vec2 pos;
        int radius;
        bool stunned;
        std::int8_t ally; // into others
        float hit;
    };
    std::array<Onto, 8> onto;
    int n_onto = 0;
    world_.each_stirring([&](int g) {
        if (groups[g].strength <= 0) return;
        const auto& c = world_.camps[g];
        if (n < 0) {
            n = 0;
            for (const auto& o : world_.allies)
                if (n < static_cast<int>(others.at.size()) && o.alive && o.visible && !o.is_self && !gone(o)) {
                    if (!o.acted) later = true;
                    else if (n_fallers < static_cast<int>(fallers.size()) && o.health + o.shield <= max_group_strength(world_) * o.taken)
                        fallers[static_cast<std::size_t>(n_fallers++)] = static_cast<std::int8_t>(n);
                    others.at[n++] = {o.pos, &o, -1, -2};
                }
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
        const auto box_out = [&](const Other& o) {
            const auto& box = member_box(world_.map(), g);
            return std::max({box[0] - o.pos.x, o.pos.x - box[1], box[2] - o.pos.y, o.pos.y - box[3], 0});
        };
        // A big group's near others have their turn order worked out by the filter: the member
        // loop reads them flat.
        const bool big = groups[g].members.size() >= 8;
        std::array<int, 2 * max_fighters> near_x, near_y, near_first;
        if (big) {
            for (int k = 0; k < n; ++k) {
                auto& o = others.at[k];
                const int out = box_out(o);
                if (out - 1 < groups[g].reach && out - first(o) < groups[g].reach)
                    near_x[k_near] = o.pos.x, near_y[k_near] = o.pos.y, near_first[k_near] = o.first, near[k_near++] = static_cast<std::uint8_t>(k);
            }
        } else {
            for (int k = 0; k < n; ++k) near[k_near++] = static_cast<std::uint8_t>(k);
        }
        const auto size = groups[g].members.size();
        // An asleep member wakes only when the group is damaged or stunned: by us, which our own
        // choices weigh, or by another champion yet to act this round within its strike's reach.
        // No member lies nearer an other than the group's box.
        bool stirred = c.asleep == 0;
        for (int k = 0; k < n && !stirred; ++k) {
            auto& o = others.at[k];
            const int out = box_out(o);
            if (out > Strike::max_reach) continue;
            if (o.wakes == -2) o.wakes = o.belief->acted ? -1 : static_cast<std::int8_t>(strike(*o.belief, world_.round).reach);
            if (o.wakes < out) continue;
            for (std::size_t i = 0; i < size && !stirred; ++i)
                stirred = c.health[i] > 0 && dist(o.pos, groups[g].members[i].pos) <= o.wakes;
        }
        if (static_cast<std::size_t>(count) + size > members_.size()) members_.resize(static_cast<std::size_t>(count) + size);
        auto* const out = members_.data();
        // The buffs read first: out of sight it fails as cheaply as the tile test, which then only
        // confirms a rare stun.
        const auto emit = [&](const CampMember& m, int reach, int tie) __attribute__((always_inline)) {
            if (reach > 0)
                out[count++] = {m.pos, m.strength * camp_factor_, w, reach, m.handle, camp_stunned(m.handle) && test(world_.visible, m.pos), tie};
            else if (tie > 0) {
                // Full: only tie_hit reads them, so the weakest goes.
                const CampHit hit{m.pos, m.strength * camp_factor_, w, 0, m.handle, camp_stunned(m.handle) && test(world_.visible, m.pos), tie};
                if (tie_only_count_ < static_cast<int>(tie_only_.size())) {
                    tie_only_[static_cast<std::size_t>(tie_only_count_++)] = hit;
                } else {
                    const auto weakest = std::min_element(tie_only_.begin(), tie_only_.end(), [](const CampHit& a, const CampHit& b) { return a.strength < b.strength; });
                    if (weakest->strength < hit.strength) *weakest = hit;
                }
            }
        };
        if (big) {
            // Member by member in order as below, the minima sixteen members at a time over the near
            // others, whose turn order the filter has read. Only live strikers, awake or stirred, count.
            const auto& lanes = member_lanes(groups[g], c, g);
            const std::uint64_t awake_mask = stirred ? ~std::uint64_t{0} : c.awake == Awake::asleep ? 0 : ~c.asleep;
            for (std::size_t word = 0; word < lanes.live.size(); ++word) {
                std::uint64_t left = lanes.live[word] & (word == 0 ? awake_mask : stirred || c.awake != Awake::asleep ? ~std::uint64_t{0} : 0);
                while (left) {
                    const int base = std::countr_zero(left) & ~15;
                    const std::size_t at = 64 * word + static_cast<std::size_t>(base);
                    std::uint32_t chunk = static_cast<std::uint32_t>(left >> base) & 65535u;
                    left &= ~(std::uint64_t{65535} << base);
                    alignas(16) std::int8_t reach16[16], tie16[16];
#if defined(__wasm_simd128__)
                    v128_t r = wasm_v128_load(&lanes.reach[at]), t = r;
                    if (k_near > 0) {
                        const v128_t x = wasm_v128_load(&lanes.x[at]), y = wasm_v128_load(&lanes.y[at]);
                        for (int k = 0; k < k_near; ++k) {
                            const v128_t d = wasm_i8x16_max(wasm_i8x16_abs(wasm_i8x16_sub(x, wasm_i8x16_splat(static_cast<std::int8_t>(near_x[k])))),
                                                            wasm_i8x16_abs(wasm_i8x16_sub(y, wasm_i8x16_splat(static_cast<std::int8_t>(near_y[k])))));
                            r = wasm_i8x16_min(r, wasm_i8x16_sub(d, wasm_i8x16_splat(static_cast<std::int8_t>(near_first[k]))));
                            t = wasm_i8x16_min(t, d);
                        }
                    }
                    wasm_v128_store(reach16, r), wasm_v128_store(tie16, t);
#else
                    for (int j = 0; j < 16; ++j) {
                        int reach = lanes.reach[at + j], tie = reach;
                        for (int k = 0; k < k_near; ++k) {
                            const int d = std::max(std::abs(near_x[k] - lanes.x[at + j]), std::abs(near_y[k] - lanes.y[at + j]));
                            reach = std::min(reach, d - near_first[k]), tie = std::min(tie, d);
                        }
                        reach16[j] = static_cast<std::int8_t>(reach), tie16[j] = static_cast<std::int8_t>(tie);
                    }
#endif
                    for (; chunk; chunk &= chunk - 1) {
                        const int j = std::countr_zero(chunk);
                        const auto& m = groups[g].members[at + static_cast<std::size_t>(j)];
                        if (reread && seen_empty(m.pos)) continue;
                        emit(m, reach16[j], tie16[j]);
                    }
                }
            }
            return;
        }
        bool track = false, doubt = false;
        for (int i = 0; i < n_fallers && !track && c.awake == Awake::awake; ++i) {
            const auto& o = others.at[fallers[static_cast<std::size_t>(i)]];
            track = box_out(o) <= groups[g].reach && o.belief->health + o.belief->shield <= groups[g].strength * o.belief->taken;
        }
        if (shield_doubt_later && later) {
            if (ours < 0) ours = my_health() + (world_.me().shield_slot >= 0 ? shield_value(world_.me().handle) : 0.0f);
            doubt = groups[g].strength * camp_factor_ >= ours;
        }
        if (track || doubt) {
        for (std::size_t i = 0; i < size; ++i) {
            const auto& m = groups[g].members[i];
            if (c.health[i] <= 0 || m.strength <= 0 || (reread && seen_empty(m.pos))) continue;
            if (!stirred && c.member_asleep(i)) continue;
            {
                int reach = m.reach, tie = m.reach;
                // The other that takes the hit: the strictly nearest within range, or -1 if tied.
                int target = -1, target_d = m.reach + 1;
                const bool doubts = doubt && m.strength * camp_factor_ >= ours;
                for (int k = 0; k < k_near; ++k) {
                    auto& o = others.at[near[k]];
                    const int d = dist(o.pos, m.pos);
                    if (d < target_d) target = near[k], target_d = d;
                    else if (d == target_d) target = -1;
                    if (d - 1 >= reach || (doubts && o.belief->side == team::ally && !o.belief->acted)) continue;
                    reach = std::min(reach, d - first(o)), tie = std::min(tie, d);
                }
                if (track && target >= 0 && n_onto < static_cast<int>(onto.size()))
                    if (const auto& o = *others.at[target].belief; o.side == team::ally && o.acted)
                        onto[static_cast<std::size_t>(n_onto++)] = {m.pos, target_d - first(others.at[target]), camp_stunned(m.handle) && test(world_.visible, m.pos),
                                                                    static_cast<std::int8_t>(target), m.strength * o.taken};
                emit(m, reach, tie);
            }
        }
        return;
        }
        for (std::size_t i = 0; i < size; ++i) {
            const auto& m = groups[g].members[i];
            if (c.health[i] <= 0 || m.strength <= 0 || (reread && seen_empty(m.pos))) continue;
            if (!stirred && c.member_asleep(i)) continue;
            // tie: the reach had we acted first, so reach <= tie <= reach + 1 and no other lies
            // between them. Both are plain minima: an other with d - 1 >= reach lowers neither.
            int reach = m.reach, tie = m.reach;
            for (int k = 0; k < k_near; ++k) {
                auto& o = others.at[near[k]];
                if (const int d = dist(o.pos, m.pos); d - 1 < reach) reach = std::min(reach, d - first(o)), tie = std::min(tie, d);
            }
            emit(m, reach, tie);
        }
    });
    member_count_ = count;
    camp_total_ = count;
    // An ally felled by the hits on it, which our taking one of them would spare.
    for (int i = 0; i < n_onto; ++i) {
        const auto& x = onto[static_cast<std::size_t>(i)];
        const auto& o = *others.at[x.ally].belief;
        float sum = 0;
        for (int j = 0; j < n_onto; ++j)
            if (onto[static_cast<std::size_t>(j)].ally == x.ally) sum += onto[static_cast<std::size_t>(j)].hit;
        if (const float health = o.health + o.shield; sum < health || sum - x.hit >= health) continue;
        if (static_cast<std::size_t>(camp_total_) + 2 > members_.size()) members_.resize(static_cast<std::size_t>(camp_total_) + 2);
        const float value = ally_fall_value(world_, o);
        members_[static_cast<std::size_t>(camp_total_++)] = {x.pos, value, 1, 1 << 12, 0, x.stunned, 0};
        members_[static_cast<std::size_t>(camp_total_++)] = {x.pos, -value, 1, x.radius, 0, x.stunned, 0};
    }
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
    ++generation_;
    ++hold_generation_;
    built_ = false;
    refresh_ = true;
    reached_ = 0;
    build_cost_ = 0;
    threat_count_ = 0;
    threat_mask_ = lost_mask_ = 0;
    members_known_ = false;
    camp_area_known_ = false;
    enemy_area_known_ = false;
    threatened_known_ = false;
    recall_line_known = false;
    fight_count_ = 0;
    unknown_falls_ = 0;
    unknown_lost_ = 0;
    gone_.fill(0);
    reachable_known_ = false;
}

void Safety::refresh() {
    ++generation_;
    refresh_ = true;
    recall_line_known = false;
    own_health_ = -1;
    gone_.fill(0);
    build_cost_ = 0;
    reachable_known_ = false;
    if (!built_ && !members_known_) { ++hold_generation_; return; }
    bool changed = false;
    for (auto left = seen_enemies(); left; left &= left - 1) changed |= gone(world_.enemies[static_cast<std::size_t>(std::countr_zero(left))]);
    if (!changed && members_known_)
        for (int i = 0; i < member_count_ && !changed; ++i) changed = seen_empty(members_[static_cast<std::size_t>(i)].pos);
    if (!changed && members_known_)
        for (int i = 0; i < tie_only_count_ && !changed; ++i) changed = seen_empty(tie_only_[static_cast<std::size_t>(i)].pos);
    if (changed) {
        invalidate();
        return;
    }
    // Our stuns this turn: a stunned member skips the next camp phase.
    bool stunned = false;
    for (int i = 0; i < member_count_ && members_known_; ++i)
        if (auto& m = members_[static_cast<std::size_t>(i)]; !m.stunned && camp_stunned(m.handle) && test(world_.visible, m.pos))
            m.stunned = stunned = true;
    for (int i = 0; i < tie_only_count_ && members_known_; ++i)
        if (auto& m = tie_only_[static_cast<std::size_t>(i)]; !m.stunned && camp_stunned(m.handle) && test(world_.visible, m.pos))
            m.stunned = true, ++hold_generation_;
    // Idle fights read fixed champion beliefs and the retained camp model. A refresh that
    // found no death or new camp stun changes neither, even after our own nonlethal attack.
    if (stunned) ++hold_generation_, camp_memo_[2].valid = false, threatened_known_ = false;
}

[[gnu::noinline]] void Safety::strike_foe(const ChampionBelief& e, Foe& x) {
    known_ |= static_cast<std::uint16_t>(1u << e.index);
    int turns = -1;
    x.strike = threat_strike(world_, e, turns);
    x.repeats = enemy_blow_repeats(world_, e, turns);
    x.turns = turns;
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
        if (reach < 0) {
            if (turn_lost(e) && fight_reach(e) >= 0) {
                threat_mask_ |= static_cast<std::uint16_t>(1u << e.index);
                lost_mask_ |= static_cast<std::uint16_t>(1u << e.index);
            }
            continue;
        }
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
        // No walls: ranged attacks and ground casts ignore them, as Strike does, and king steps on
        // an open board are Chebyshev distance.
        static const bitboard open;
        clear_board(t.area);
        field.compute(open, e.possible, t.area, static_cast<std::uint16_t>(radius));
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
        if (e.visible ? !in_square(p, acts_from(e), Strike::max_reach) : !e.possible_box.meets(p, Strike::max_reach)) continue;
        if (gone(e)) continue;
        auto& x = foe(e);
        const auto& s = x.strike;
        if (s.reach < 0) continue;
        if (e.visible) f(e, blow(e, p));
        else if (x.weight > 0) {
            if (x.asked != p) x.asked = p, x.near = possible_within(e, p, s.reach);
            f(e, x.near ? s.blow(0) : Blow{});
        }
    }
}

template <class F> bool Safety::any_threat_at(vec2 p, F&& f) {
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (e.visible ? !in_square(p, acts_from(e), Strike::max_reach) : !e.possible_box.meets(p, Strike::max_reach)) continue;
        if (gone(e)) continue;
        auto& x = foe(e);
        const auto& s = x.strike;
        if (s.reach < 0) continue;
        if (e.visible) {
            if (f(blow(e, p))) return true;
        } else if (x.weight > 0) {
            if (x.asked != p) x.asked = p, x.near = possible_within(e, p, s.reach);
            if (f(x.near ? s.blow(0) : Blow{})) return true;
        }
    }
    return false;
}

[[gnu::noinline]] void Safety::build_reach(const ChampionBelief& e, Reach& r) {
    reached_ |= static_cast<std::uint16_t>(1u << e.index);
    auto& x = struck(e);
    r.build(world_, e, next_turn_round(world_, e), turns_before_ours(world_, e, x.turns) >= 2);
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
        // Do not build deferred geometry under the debug fuel refund. Strike must bound any geometry already built.
        static int last = -1;
        const int d = dist(p, e.pos);
        if (last != world_.round && ((r.geometry_ready() && r.reach() > s.reach) || b.damage > s.at(d) + 0.01f || (b.stuns && !s.stuns[d]))) {
            last = world_.round;
            std::printf("REACH-BOUND %d e%d reach %d/%d d %d damage %.1f/%.1f\n", world_.round, e.index, r.reach(), s.reach, d, b.damage, s.at(d));
        }
    });
    return b;
}

int Safety::fight_reach(const ChampionBelief& e) {
    const int reach = struck(e).strike.reach;
    return reach >= 0 || !turn_lost(e) ? reach : strike(e, next_turn_round(world_, e)).reach;
}

int Safety::approach(const ChampionBelief& e, vec2 p, int horizon) {
    const int reach = struck(e).strike.reach;
    if (reach < 0 && turn_lost(e)) {
        if (reach_of(e).at(p).hits) return 1;
        const int r = fight_reach(e);
        return 1 + std::max(1, enemy_reach::distance(world_, e, e.pos, p, r + horizon - 1) - r);
    }
    if (blow(e, p).hits) return 0;
    return walk_in(e, p, horizon);
}

// approach() past its blow test, which found no hit.
int Safety::walk_in(const ChampionBelief& e, vec2 p, int horizon) {
    const int reach = struck(e).strike.reach;
    return std::max(1, enemy_reach::distance(world_, e, acts_from(e), p, reach + horizon) - reach);
}

int Safety::threats_at(vec2 p, std::array<ThreatAt, 16>& out, bool unseen_only) {
    int n = 0;
    if (built_) {
        for (const auto& t : threats())
            if (n < static_cast<int>(out.size()) && !(unseen_only && t.visible)) out[n++] = {t.enemy, t.at(p)};
        return n;
    }
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e) || n == static_cast<int>(out.size())) continue;
        const auto& x = foe(e);
        if (x.strike.reach < 0) continue;
        if (e.visible) {
            if (!unseen_only) out[n++] = {e.index, blow(e, p)};
        } else if (x.weight > 0) {
            out[n++] = {e.index, unseen_blow(e, x, p)};
        }
    }
    return n;
}

// An unseen enemy's blow at p from the nearest possible tile within the radius (never past the
// reach), found by bisection.
Blow Safety::unseen_blow(const ChampionBelief& e, const Foe& x, vec2 p) {
    const int radius = unseen_radius(x.strike.reach, x.tiles);
    int d = radius + 1;
    if (possible_within(e, p, radius)) {
        int lo = 0;
        d = radius;
        while (lo < d) {
            const int mid = (lo + d) / 2;
            if (possible_within(e, p, mid)) d = mid;
            else lo = mid + 1;
        }
    }
    return x.strike.blow(d <= radius ? d : static_cast<int>(unreachable));
}

// threats_at(p)'s entries in its order, the 16 it keeps, stopping at the first hit by another
// than `enemy`; `enemy`'s own blow is never worked out.
bool Safety::other_hits(vec2 p, int enemy) {
    constexpr int kept = 16;
    int n = 0;
    if (built_) {
        for (const auto& t : threats()) {
            if (n++ == kept) break;
            if (t.enemy != enemy && t.at(p).hits) return true;
        }
        return false;
    }
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e) || n == kept) continue;
        const auto& x = foe(e);
        if (x.strike.reach < 0 || (!e.visible && !(x.weight > 0))) continue;
        ++n;
        if (e.index != enemy && (e.visible ? blow(e, p) : unseen_blow(e, x, p)).hits) return true;
    }
    return false;
}

bool Safety::may_reach_within(vec2 p, int turns) {
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        // Out of the widest reach (a strike's is at most max_reach): no need to build its foe (~1.5k).
        if (e.visible ? dist(p, acts_from(e)) > Strike::max_reach + turns : !e.possible_box.meets(p, Strike::max_reach + turns)) continue;
        if (gone(e)) continue;
        const auto& x = foe(e);
        int reach = x.strike.reach, walk = turns;
        // A stun takes its next turn, not the ones after it (as approach() counts it).
        if (reach < 0 && turn_lost(e)) reach = fight_reach(e), --walk;
        if (reach < 0 || walk < 0 || (!e.visible && !(x.weight > 0))) continue;
        if (e.visible ? enemy_reach::within(world_, e, acts_from(e), p, reach + walk) : possible_within(e, p, reach + walk)) return true;
    }
    return false;
}

// By enemy: Chebyshev distance from `possible` out to its reach + pursuit_steps (approach_field_).
static cambc::distance_field& approach_field(int i) {
    static std::vector<std::unique_ptr<cambc::distance_field>> fields;
    if (fields.size() <= static_cast<std::size_t>(i)) fields.resize(static_cast<std::size_t>(i) + 1);
    auto& field = fields[static_cast<std::size_t>(i)];
    if (!field) field = std::make_unique<cambc::distance_field>();
    return *field;
}

bool Safety::credible_unseen(const ChampionBelief& e) {
    const auto bit = static_cast<std::uint16_t>(1u << e.index);
    if (credible_known_ & bit) return credible_ & bit;
    credible_known_ |= bit;
    if (!(live_enemies() >> e.index & 1) || (seen_ >> e.index & 1)) return false;
    // Too many tiles for any strike's reach to hold half: no strike needs working out.
    if (!(counted_ >> e.index & 1) && unseen_weight(Strike::max_reach, static_cast<int>(board_count(e.possible))) == 0) return false;
    const auto& x = foe(e);
    if (x.strike.reach >= 0 && x.weight > 0) credible_ |= bit;
    return credible_ & bit;
}

// The tests below ask `possible` within the widest strike first: a square kept by within() and two
// board operations, where a strike and a weight cost more.
bool Safety::unseen_may_hit_within(vec2 p, int radius) {
    for (auto left = live_enemies() & ~seen_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (radius <= params::pursuit_steps && (approach_field_ >> e.index & 1)) {
            if (steps_at(approach_field(e.index), p) <= struck(e).strike.reach + radius) return true;
            continue;
        }
        if (!possible_within(e, p, Strike::max_reach + radius) || !credible_unseen(e)) continue;
        if (const int reach = struck(e).strike.reach; reach == Strike::max_reach || possible_within(e, p, reach + radius)) return true;
    }
    return false;
}

bool Safety::unseen_within(vec2 p, int r) {
    for (auto left = live_enemies() & ~seen_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (possible_within(e, p, r) && credible_unseen(e)) return true;
    }
    return false;
}

bool Safety::possible_on_spawn(const ChampionBelief& e) {
    const auto bit = static_cast<std::uint16_t>(1u << e.index);
    if (on_spawn_known_ & bit) return on_spawn_ & bit;
    on_spawn_known_ |= bit;
    static bitboard off{cambc::uninitialized};
    copy_into(e.possible, off);
    drop(off, world_.map().near_enemy_spawn);
    if (board_empty(off)) on_spawn_ |= bit;
    return on_spawn_ & bit;
}

// The searches below cost a few board operations a tile: an enemy asked about near a second tile
// gets a field instead, read for ~30 a tile.
int Safety::unseen_approach(const ChampionBelief& e, vec2 p, int horizon) {
    const auto bit = static_cast<std::uint16_t>(1u << e.index);
    const bool fits = horizon <= params::pursuit_steps;
    if (fits && (approach_field_ & bit)) {
        const auto& x = foe(e);
        const int reach = x.strike.reach, d = steps_at(approach_field(e.index), p);
        if (d > reach + horizon) return horizon + 1;
        if (d <= unseen_radius(reach, x.tiles)) return 0;
        return std::max(1, d - reach);
    }
    if (!possible_within(e, p, Strike::max_reach + horizon) || !credible_unseen(e)) return horizon + 1;
    const auto& x = foe(e);
    const int reach = x.strike.reach;
    if (fits) {
        if (approached_ & bit) {
            static const bitboard open;
            static bitboard reached{cambc::uninitialized};
            approach_field(e.index).compute(open, e.possible, reached, static_cast<std::uint16_t>(reach + params::pursuit_steps));
            approach_field_ |= bit;
            return unseen_approach(e, p, horizon);
        }
        approached_ |= bit;
    }
    if (reach < Strike::max_reach && !possible_within(e, p, reach + horizon)) return horizon + 1;
    if (possible_within(e, p, unseen_radius(reach, x.tiles))) return 0;
    int lo = 1, hi = horizon;
    while (lo < hi) {
        const int mid = (lo + hi) / 2;
        if (possible_within(e, p, reach + mid)) hi = mid;
        else lo = mid + 1;
    }
    return lo;
}

bool Safety::credible_enemy_may_hit_within(vec2 p, int radius) {
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (e.visible ? dist(p, acts_from(e)) > Strike::max_reach + radius : !e.possible_box.meets(p, Strike::max_reach + radius)) continue;
        if (gone(e)) continue;
        const auto& x = foe(e);
        const int reach = x.strike.reach;
        if (reach < 0 || (!e.visible && !(x.weight > 0))) continue;
        if (e.visible) {
            if (dist(p, acts_from(e)) <= reach + radius) return true;
        } else if (possible_within(e, p, reach + radius)) {
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

float Safety::damage_bound(vec2 p, bool double_unacted, float blow_scale) {
    float total = camp_damage(p, true, true);
    each_threat(p, [&](const ChampionBelief& e, const Blow& b) {
        total += b.damage * (double_unacted && struck(e).repeats ? 2.0f : 1.0f) * blow_scale;
    });
    return total;
}

Safety::Bound Safety::bound(vec2 p, float blow_scale) {
    Bound out;
    out.damage = out.doubled = camp_damage(p, true, true);
    float safe = 1;
    each_threat(p, [&](const ChampionBelief& e, const Blow& b) {
        out.damage += b.damage * blow_scale;
        out.doubled += b.damage * (struck(e).repeats ? 2.0f : 1.0f) * blow_scale;
        out.hits |= b.hits;
        out.stuns |= b.hits && b.stuns;
        if (!b.hits || out.threat) return;
        if (e.visible) {
            out.threat = true;
            return;
        }
        const auto& x = foe(e);
        const float chance = std::min(1.0f, static_cast<float>(possible_count_within(e, p, x.strike.reach)) / static_cast<float>(x.tiles));
        out.threat = 1 - (safe *= 1 - chance * hit_given_reach) >= recall_risk;
    });
    return out;
}

bool Safety::threat_at(vec2 p) {
    float safe = 1;
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (e.visible ? !in_square(p, acts_from(e), Strike::max_reach) : !e.possible_box.meets(p, Strike::max_reach)) continue;
        if (gone(e)) continue;
        auto& x = foe(e);
        const auto& s = x.strike;
        if (s.reach < 0) continue;
        if (e.visible) {
            if (blow(e, p).hits) return true;
        } else if (x.weight > 0) {
            if (x.asked != p) x.asked = p, x.near = possible_within(e, p, s.reach);
            if (!x.near || !s.blow(0).hits) continue;
            const float chance = std::min(1.0f, static_cast<float>(possible_count_within(e, p, x.strike.reach)) / static_cast<float>(x.tiles));
            if (1 - (safe *= 1 - chance * hit_given_reach) >= recall_risk) return true;
        }
    }
    return false;
}

float Safety::damage_ceiling(vec2 p, bool double_unacted, float blow_scale) {
    float total = camp_damage(p, true, true);
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (e.visible && !in_square(p, acts_from(e), Strike::max_reach)) continue;
        if (gone(e)) continue;
        if (!e.visible) {
            total += most_damage(e) * blow_scale;
            continue;
        }
        if (struck(e).strike.reach < 0) continue;
        total += blow(e, p).damage * (double_unacted && struck(e).repeats ? 2.0f : 1.0f) * blow_scale;
    }
    return total;
}

bool Safety::touched(vec2 p, float blow_scale) {
    if (camp_damage(p, true, true) > 0) return true;
    return any_threat_at(p, [&](const Blow& b) { return b.hits || b.damage * blow_scale > 0; });
}

Safety::Tally Safety::tally(vec2 p, float blow_scale) {
    Tally t;
    t.damage = camp_damage(p, true, true);
    t.left = live_enemies();
    if (!(t.damage > 0)) tally_on(t, p, blow_scale, true);
    return t;
}

// each_threat's order and terms, from where the last call stopped.
void Safety::tally_on(Tally& t, vec2 p, float blow_scale, bool first) {
    while (t.left) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(t.left))];
        t.left &= t.left - 1;
        if (e.visible ? !in_square(p, acts_from(e), Strike::max_reach) : !e.possible_box.meets(p, Strike::max_reach)) continue;
        if (gone(e)) continue;
        auto& x = foe(e);
        const auto& s = x.strike;
        if (s.reach < 0) continue;
        Blow b{};
        if (e.visible) b = blow(e, p);
        else if (x.weight > 0) {
            if (x.asked != p) x.asked = p, x.near = possible_within(e, p, s.reach);
            if (x.near) b = s.blow(0);
        } else continue;
        t.damage += b.damage * blow_scale;
        t.hits |= b.hits;
        t.stuns |= b.hits && b.stuns;
        if (first && t.damage > 0) return;
    }
}

bool Safety::may_be_hit(vec2 p) {
    bool hit = false;
    each_threat(p, [&](const ChampionBelief&, const Blow& b) { hit |= b.hits; });
    return hit;
}

float Safety::camp_damage(vec2 p, bool worst, bool next) {
    if (!members_known_) find_members();
    const std::span<const CampHit> members{members_.data(), static_cast<std::size_t>(camp_total_)};
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

float Safety::tie_hit(vec2 p) {
    float hit = 0;
    for (const auto& m : awake_members())
        if (!m.stunned && in_square(p, m.pos, m.tie_reach)) hit += m.strength;
    for (int i = 0; i < tie_only_count_; ++i)
        if (const auto& m = tie_only_[static_cast<std::size_t>(i)]; !m.stunned && in_square(p, m.pos, m.tie_reach)) hit += m.strength;
    return hit;
}

float Safety::worst_damage(vec2 p, float blow_scale) {
    float total = camp_damage(p, true, true);
    for (const auto& t : threats())
        total += t.at(p).damage * blow_scale;
    return total;
}

// Any camp member or visible threat in reach is enough on its own. An unseen threat's chance is
// uniform over its possible tiles; it hits p only within its field, capped inside its reach.
bool Safety::threatened(vec2 p) {
    // A dead champion reads its position as (-1, -1): off the map, nothing reaches it.
    if (p.x < 0) return false;
    if (!threatened_known_ || p != threatened_at_) threatened_ = threatened_now(p), threatened_at_ = p, threatened_known_ = true;
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
        const auto near = possible_count_within(world_.enemies[t.enemy], p, t.strike.reach);
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
            else if (const vec2 from = acts_from(*t.belief); from != t.pos) draw_square(any, from, static_cast<float>(t.strike.reach)); // as blow()
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
        if (e.visible ? !in_square(p, acts_from(e), Strike::max_reach + r) : !e.possible_box.meets(p, Strike::max_reach + r)) continue;
        if (gone(e)) continue;
        const auto& x = foe(e);
        const int reach = x.strike.reach;
        if (reach < 0) continue;
        if (e.visible) {
            if (dist(p, acts_from(e)) <= reach + r) return true;
            continue;
        }
        if (x.weight > 0 && possible_within(e, p, unseen_radius(reach, x.tiles) + r)) return true;
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
    if (const auto lost = lost_in_reach(p)) hit = true, key |= lost;
    if (!hit) return no_fight;
    return key | fighting_allies(world_, p);
}

std::uint32_t Safety::fight_key_with(vec2 p, std::uint32_t visible) {
    std::uint32_t key = visible;
    for (const auto& t : threats())
        if (!t.visible && t.at(p).hits) key |= 1u << (16 + t.enemy);
    return key | lost_in_reach(p) | fighting_allies(world_, p);
}

std::uint32_t Safety::fight_allies(vec2 p) { return fighting_allies(world_, p); }

std::uint32_t Safety::fight_enemies_any(const vec2* ps, int n, std::array<std::uint8_t, 16>* first) {
    std::uint32_t key = 0;
    for (const auto& t : threats())
        if (!t.visible)
            for (int i = 0; i < n; ++i)
                if (t.at(ps[i]).hits) {
                    key |= 1u << (16 + t.enemy);
                    if (first) (*first)[static_cast<std::size_t>(t.enemy)] = static_cast<std::uint8_t>(i);
                    break;
                }
    for (unsigned left = lost_mask_; left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e)) continue;
        for (int i = 0; i < n; ++i)
            if (in_square(ps[i], e.pos, fight_reach(e)) && reach_of(e).at(ps[i]).hits) {
                key |= 1u << (16 + e.index);
                if (first) (*first)[static_cast<std::size_t>(e.index)] = static_cast<std::uint8_t>(i);
                break;
            }
    }
    return key;
}

// An enemy hitting none of the tiles hits none of them, and one first hitting a later tile misses
// this one: the tiles before its first were read and missed. Each enemy has one threat at most, and
// a lost enemy none.
std::uint32_t Safety::fight_enemies_at(vec2 p, int i, std::uint32_t any, const std::array<std::uint8_t, 16>& first) {
    std::uint32_t key = 0;
    for (const auto& t : threats()) {
        const std::uint32_t bit = 1u << (16 + t.enemy);
        if (t.visible || !(any & bit) || i < first[static_cast<std::size_t>(t.enemy)]) continue;
        if (i == first[static_cast<std::size_t>(t.enemy)] || t.at(p).hits) key |= bit;
    }
    for (unsigned left = lost_mask_ & any >> 16; left; left &= left - 1) {
        const int j = std::countr_zero(left);
        const auto& e = world_.enemies[static_cast<std::size_t>(j)];
        if (i < first[static_cast<std::size_t>(j)]) continue;
        if (i == first[static_cast<std::size_t>(j)] || (in_square(p, e.pos, fight_reach(e)) && reach_of(e).at(p).hits)) key |= 1u << (16 + j);
    }
    return key;
}

std::uint32_t Safety::lost_in_reach(vec2 p) {
    std::uint32_t out = 0;
    for (unsigned left = lost_mask_; left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        // Its Reach is its first turn's: next_turn_round() skips the lost one.
        if (!gone(e) && in_square(p, e.pos, fight_reach(e)) && reach_of(e).at(p).hits) out |= 1u << (16 + e.index);
    }
    return out;
}

const Trade* Safety::memo(std::uint32_t key, std::uint32_t late, bool falls, bool settle) const {
    for (int i = 0; i < std::min(fight_count_, max_fights); ++i)
        if (fights_[i].key == key && fights_[i].late == late && !(falls && unknown_falls_ >> i & 1) && !(!settle && unknown_lost_ >> i & 1))
            return &fights_[i].trade;
    return nullptr;
}

static_assert(params::pursuit_steps <= 3); // late(): 2 bits an enemy

std::uint32_t Safety::late(vec2 p, std::uint32_t key) {
    std::uint32_t out = 0;
    const auto& spawn = world_.map().near_enemy_spawn;
    for (auto left = seen_enemies() & ~(key == no_fight ? 0u : key >> 16); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e) || test(spawn, e.pos)) continue;
        const int reach = fight_reach(e);
        if (reach < 0 || dist(p, acts_from(e)) - reach > params::pursuit_steps) continue;
        if (const int walk = approach(e, p, params::pursuit_steps); walk > 0 && walk <= params::pursuit_steps) out |= static_cast<std::uint32_t>(walk) << 2 * e.index;
    }
    for (auto left = live_enemies() & ~seen_enemies() & ~(key == no_fight ? 0u : key >> 16); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (const int walk = unseen_approach(e, p, params::pursuit_steps); walk > 0 && walk <= params::pursuit_steps && !possible_on_spawn(e))
            out |= static_cast<std::uint32_t>(walk) << 2 * e.index;
    }
    return out;
}

namespace {

// Our allies (not us) among `allies`, which `us` was filled with, join once a walk brings an enemy
// of the fight within their strike, as approach() delays enemies. An unseen enemy may be anywhere:
// none waits then.
void walk_allies_in(const World& world, Side& us, std::uint32_t allies, std::uint32_t enemies) {
    int k = 0;
    for (auto left = allies; left && k < us.count; left &= left - 1, ++k) {
        const auto& a = world.allies[static_cast<std::size_t>(std::countr_zero(left))];
        auto& f = us.fighters[k];
        if (a.is_self || f.health <= 0) continue;
        const int reach = strike(a, next_turn_round(world, a)).reach;
        int walk = never;
        for (auto e = enemies; e && walk > 0; e &= e - 1) {
            const auto& x = world.enemies[static_cast<std::size_t>(std::countr_zero(e))];
            walk = x.visible ? std::min(walk, std::max(0, dist(a.pos, acts_from(x)) - reach)) : 0;
        }
        if (walk != never && walk > f.arrives_at) f.arrives_at = walk;
    }
}

// Bits of `late` (Safety::late) among `enemies`, which `them` was filled with: they join after walking.
void join_late(Side& them, std::uint32_t enemies, std::uint32_t late) {
    int k = 0;
    for (auto left = enemies; left && k < them.count; left &= left - 1, ++k)
        if (const int walk = late >> 2 * std::countr_zero(left) & 3) them.fighters[k].arrives_at = walk;
}

std::uint32_t late_mask(std::uint32_t late) {
    std::uint32_t out = 0;
    for (int i = 0; late; ++i, late >>= 2)
        if (late & 3) out |= 1u << i;
    return out;
}

} // namespace

Trade Safety::fight(vec2 p, bool falls) {
    world_.throw_if_stale();
    const auto key = fight_key(p);
    return key == no_fight ? Trade{} : fight_of(key, falls);
}

Trade Safety::fight_of(std::uint32_t key, bool falls, std::uint32_t late, bool settle) {
    if (const auto* t = memo(key, late, falls, settle)) return *t;
    return new_fight(key, falls, late, settle);
}

Trade Safety::new_fight(std::uint32_t key, bool falls, std::uint32_t late, bool settle) {
    Side us, them;
    fill(us, world_, world_.allies, key & 0xFFFFu, made_);
    build();
    const auto enemies = (key >> 16 | late_mask(late)) & threat_mask_;
    fill(them, world_, world_.enemies, enemies, made_);
    if (late) join_late(them, enemies, late);
    walk_allies_in(world_, us, key & 0xFFFFu, enemies);
    const auto before = fuel();
    // Asked again with self_falls (or lost), a fight replaces the one without.
    int i = -1;
    for (auto left = unknown_falls_ | unknown_lost_; left; left &= left - 1)
        if (fights_[std::countr_zero(left)].key == key && fights_[std::countr_zero(left)].late == late) i = std::countr_zero(left);
    if (i < 0) i = fight_count_++ % max_fights;
    auto& slot = fights_[i];
    slot = {key, late, trade(us, them, true, falls, settle)};
    unknown_falls_ = slot.trade.falls_known ? unknown_falls_ & ~(1u << i) : unknown_falls_ | 1u << i;
    unknown_lost_ = slot.trade.lost_known ? unknown_lost_ & ~(1u << i) : unknown_lost_ | 1u << i;
    if (const auto after = fuel(); after < before) costliest_fight_ = std::max(costliest_fight_, before - after);
    return slot.trade;
}

Trade Safety::chase_trade(std::uint32_t key, std::uint32_t delayed, const std::array<int, 2>& self_cooldowns, bool can_cast, bool falls,
                          std::uint32_t late) {
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
    if (!changed) return fight_of(key, falls, late, falls);
    build();
    const auto enemies = (key >> 16 | late_mask(late)) & threat_mask_;
    fill(them, world_, world_.enemies, enemies, made_);
    if (late) join_late(them, enemies, late);
    walk_allies_in(world_, us, key & 0xFFFFu, enemies);
    world_.throw_if_stale();
    // No cross-target memo: roster alone omits the delayed mask and our live action state.
    const auto before = fuel();
    const auto t = trade(us, them, true, falls, falls);
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

Safety::StandReach Safety::stand_reach(vec2 p, int farthest) {
    world_.throw_if_stale();
    StandReach r;
    std::uint32_t hit = 0, walking = 0;
    auto& walks = r.walks;
    const auto& spawn = world_.map().near_enemy_spawn;
    for (auto left = seen_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e)) continue;
        const int reach = fight_reach(e);
        if (reach < 0 || dist(p, acts_from(e)) - reach > farthest) continue;
        // approach()'s 0, its first test.
        if (!(struck(e).strike.reach < 0 && turn_lost(e)) && blow(e, p).hits) hit |= 1u << e.index;
        else if (!test(spawn, e.pos)) r.pending |= 1u << e.index;
    }
    for (auto left = live_enemies() & ~seen_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        const int walk = unseen_approach(e, p, farthest);
        if (walk == 0) hit |= 1u << e.index;
        else if (walk <= farthest && !possible_on_spawn(e)) walking |= 1u << e.index, walks[static_cast<std::size_t>(e.index)] = static_cast<std::int8_t>(walk);
    }
    r.hit = hit, r.walking = walking;
    return r;
}

void Safety::stand_walks(vec2 p, int farthest, StandReach& r) {
    for (auto left = std::exchange(r.pending, 0u); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        const bool lost = struck(e).strike.reach < 0 && turn_lost(e);
        if (const int walk = lost ? this->approach(e, p, farthest) : walk_in(e, p, farthest); walk <= farthest)
            r.walking |= 1u << e.index, r.walks[static_cast<std::size_t>(e.index)] = static_cast<std::int8_t>(walk);
    }
}

Safety::StandRoster Safety::stand_roster(vec2 p, const StandReach& reach, int approach, bool unseen) {
    StandRoster r;
    const std::uint32_t hit = reach.hit;
    std::uint32_t walking = reach.walking;
    r.walks = reach.walks;
    const auto& walks = r.walks;
    // Pursuit aside, an enemy who walks into a fight already on is part of it.
    if (!hit)
        for (auto left = walking; left; left &= left - 1)
            if (const int i = std::countr_zero(left); walks[static_cast<std::size_t>(i)] > approach) walking &= ~(1u << i);
    if (!hit && !walking && !unseen) return r;
    const auto key = hit || unseen ? fight_key_with(p, hit << 16) : fighting_allies(world_, p);
    // Those the key holds already fight from the start.
    walking &= ~(key >> 16);
    if (!((key >> 16 & threat_mask_) | walking)) return r;
    r.key = key, r.walking = walking;
    r.camp = camp_damage(p, false);
    return r;
}

Trade Safety::stand_trade(const StandRoster& r, bool falls) {
    if (r.key == no_fight) return {};
    const auto key = r.key;
    const auto walking = r.walking;
    if (!walking && r.camp <= 0) return fight_of(key, falls, 0, falls);
    // A fight on with walkers is fight_of's with them late, and memoised with it: the stands of the
    // tiles around ours share their fights.
    if ((key >> 16) != 0 && r.camp <= 0 && (walking & ~threat_mask_) == 0) {
        std::uint32_t late = 0;
        for (auto left = walking; left; left &= left - 1)
            if (const int i = std::countr_zero(left); i < 16) late |= static_cast<std::uint32_t>(r.walks[static_cast<std::size_t>(i)]) << 2 * i;
        return fight_of(key, falls, late, falls);
    }
    const std::uint32_t enemies = (key >> 16 & threat_mask_) | walking;
    Side us, them;
    fill(us, world_, world_.allies, key & 0xFFFFu, made_);
    fill(them, world_, world_.enemies, enemies, made_);
    int k = 0;
    for (auto left = enemies; left && k < them.count; left &= left - 1, ++k)
        if (const int i = std::countr_zero(left); walking >> i & 1) them.fighters[k].arrives_at = r.walks[static_cast<std::size_t>(i)];
    walk_allies_in(world_, us, key & 0xFFFFu, enemies);
    // camp_damage() counts our Durability, which hurt() applies.
    us.camp = r.camp / world_.me().taken;
    // With nobody in reach yet, we strike first: they must still win.
    return trade(us, them, (key >> 16) != 0, falls, falls);
}

int Safety::turns_to_kill_idle(vec2 p, int horizon) { return turns_to_harm_idle(world_.me(), p, horizon, 0, true); }

int Safety::turns_to_harm_idle(const ChampionBelief& c, vec2 p, int horizon, float keep, bool unseen) {
    Side us, them;
    Fighter f = fighter(world_, c, made_);
    f.arrives_at = never;
    f.health -= keep;
    if (f.health <= 0) return 1;
    us.add(f);
    us.camp = camp_damage(p, false) / world_.me().taken; // hurt() applies c's Durability, camp_damage() ours
    for (auto left = seen_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e)) continue;
        const int reach = fight_reach(e);
        if (reach < 0 || dist(p, acts_from(e)) - reach >= horizon) continue;
        const int walk = approach(e, p, horizon - 1);
        if (walk >= horizon) continue;
        const int k = them.count;
        them.add(fighter(world_, e, made_));
        if (them.count > k && walk != 0) them.fighters[k].arrives_at = walk;
    }
    for (auto left = unseen ? live_enemies() & ~seen_enemies() : 0u; left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        const int walk = unseen_approach(e, p, horizon - 1);
        if (walk >= horizon) continue;
        const int k = them.count;
        them.add(fighter(world_, e, made_));
        if (them.count > k && walk != 0) them.fighters[k].arrives_at = walk;
    }
    if (them.count == 0 && us.camp <= 0) return 0;
    // The idle holder never attacks, so it takes no reflected damage. Ignore its shield and
    // every attacker's arrival delay: surviving this ceiling settles the whole horizon.
    auto cap = their_cap(us, them);
    if (cap.short_of(us, them, horizon, 0, horizon, f.health / f.taken)) return 0;
    return simulate_idle(us, them, horizon);
}

// Every live enemy unseen, and none's possible tiles within Strike::max_reach of p: each_threat's
// blows at p are all none.
bool Safety::unseen_beyond(vec2 p) {
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (e.visible || possible_within(e, p, Strike::max_reach)) return false;
    }
    return true;
}

bool Safety::lethal(vec2 p) {
    if (own_health_ < 0) own_health_ = my_health() + (world_.me().shield_slot >= 0 ? shield_value(world_.me().handle) : 0.0f);
    // A turn ended on our spawn heals to full before any enemy acts (rules rounds.turn_end).
    const float health = test(world_.map().ally_spawn, p) ? own_health_ - my_health() + my_max_health() : own_health_;
    // Most turns no enemy is near enough; skip the threat build then.
    // Blows by our Durability; camp_damage has it already.
    const float taken = world_.me().taken;
    // With no enemy in sight and every one past any strike's reach of p, damage_bound adds nothing to
    // the camps' damage, and it bounds the ceiling's test: the same answer without the enemies'
    // strikes (once they are all known, the bound below costs little more). With one in sight, the
    // strikes are mostly read anyway.
    if (!built_ && live_enemies() && !seen_ && (known_ & unseen_) != unseen_ && camp_damage(p, true, true) < health && unseen_beyond(p))
        return false;
    if (!built_ && (damage_ceiling(p, false, taken) < health || damage_bound(p, false, taken) < health)) return false;
    return worst_damage(p, taken) >= health;
}

} // namespace aph
