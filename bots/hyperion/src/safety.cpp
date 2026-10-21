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

// Debug only, for the MEMO line: one Safety's simulations, memo hits and act() branches.
struct MemoStats {
    int sims = 0, hits = 0, kept = 0, idle_hits = 0, pursuit_hits = 0;
    std::array<int, 3> act{}; // act() calls by branch: quiet, plain, general
    // The VERDICT line: verdicts asked, and those answered by a simulation, the memo or dominance.
    int verdicts = 0, verdict_sims = 0, verdict_memo = 0, verdict_dom = 0;
};
constinit MemoStats memo_stats{};
// Debug only: the generation each Safety::fights_ slot was simulated in.
constinit std::array<std::uint32_t, 64> fight_generation{};

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
    int camp_until = never; // the other side's turn index from which `camp` stops
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
        if (auto& f = fighters[i]; f.shield == 0 && damage < f.health) {
            f.health -= damage;
            return;
        }
        spill(damage, i);
    }
    [[gnu::noinline]] void spill(float damage, int first) {
        for (int i = first; i >= 0; i = damage > 0 ? weakest() : -1) {
            auto& f = fighters[i];
            if (f.shield != 0) {
                const float absorbed = std::min(damage, f.shield);
                f.shield -= absorbed;
                damage -= absorbed;
            }
            const float taken = std::min(damage, f.health);
            f.health -= taken;
            damage -= taken;
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

// Of their next `theirs` turns, those that still charge us the camps.
int camp_turns(const Side& us, const Side& them, int theirs) { return std::max(0, std::min(theirs, us.camp_until - them.turn)); }

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
    f.shield_until = shielded ? std::max(1, c.shield_turns) : never;
    f.retaliation = c.retaliation();
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

// The half-turns from `t` (to `end` at most) in which both sides only make their basic attacks
// and nobody falls, each taken off the side's weakest as act() and hurt() would; returns the next.
int play_quiet(Side& us, Side& them, int t, int end, bool they_first, int& ours, int& theirs) {
    const int wu = us.weakest(), we = them.weakest();
    if (wu < 0 || we < 0) return t;
    auto& u = us.fighters[wu];
    auto& e = them.fighters[we];
    if (u.shield != 0 || e.shield != 0) return t;
    const float onto_them = u.retaliation > 0 ? static_cast<float>(them.quiet_hits) * u.retaliation : 0.0f;
    const float onto_us = e.retaliation > 0 ? static_cast<float>(us.quiet_hits) * e.retaliation : 0.0f;
    for (; t < end; ++t) {
        if ((t % 2 == 0) == they_first) {
            if (them.turn >= them.quiet_until || them.alive != them.quiet_alive || them.stunned != 0) break;
            const float camp = them.turn < us.camp_until ? us.camp : 0.0f;
            const float d = them.quiet_damage;
            if (!(d < u.health) || !(onto_them < e.health)) break;
            const float h = u.health - d;
            if (camp > 0 && !(camp < h)) break;
            u.health = camp > 0 ? h - camp : h;
            if (onto_them > 0) e.health -= onto_them;
            ++them.turn;
            ++theirs;
        } else {
            if (us.turn >= us.quiet_until || us.alive != us.quiet_alive || us.stunned != 0) break;
            const float d = us.quiet_damage;
            if (!(d < e.health) || !(onto_us < u.health)) break;
            e.health -= d;
            if (onto_us > 0) u.health -= onto_us;
            ++us.turn;
            ++ours;
        }
    }
    return t;
}

static_assert(fight_horizon == 2 * ability_cooldown + 1);

// Whether our fighter `self` (and its linked body) must outlive their next `theirs` turns and our
// next `ours`: every member of theirs alive now attacking each turn and casting each slot as soon
// as it is ready, Ren hitting back at each of our hits, and the camps, still fall short of it.
bool outlives(const Side& us, const Side& them, int self, int theirs, int ours) {
    const auto& me = us.fighters[self];
    const float health = me.link >= 0 ? std::min(me.health, us.fighters[me.link].health) : me.health;
    const int end = them.turn + theirs;
    float most = static_cast<float>(camp_turns(us, them, theirs)) * us.camp, back = 0;
    for (int i = 0; i < them.count; ++i) {
        const auto& f = them.fighters[i];
        if (f.health <= 0) continue;
        most += static_cast<float>(theirs) * f.strength;
        back = std::max(back, f.retaliation);
        for (int s = 0; s < 2; ++s)
            if (const int first = std::max(them.turn, f.ready_at[s]); f.ready_at[s] != never && first < end)
                most += static_cast<float>((end - first + ability_cooldown - 1) / ability_cooldown) * f.kit->cast[s].damage;
    }
    if (back > 0) most += static_cast<float>(2 * ours * us.alive) * back;
    return most * 1.001f + 1.0f < health;
}

// Whether their side must take all of ours within their next `theirs` turns. We cannot fell any of
// theirs in our next `ours`: every attack and cast of ours as soon as ready, and our Ren hitting
// back at each of their hits, fall short of their weakest. Then their basic attacks alone, less a
// turn of their strongest for each stun we could cast, and the camps, outweigh our health, shields
// and every heal or shield we could cast.
bool overwhelmed(const Side& us, const Side& them, int theirs, int ours) {
    const int our_end = us.turn + ours;
    float most = 0, guard = 0, back = 0;
    int stuns = them.stunned;
    for (int i = 0; i < us.count; ++i) {
        const auto& f = us.fighters[i];
        if (f.health <= 0) continue;
        back = std::max(back, f.retaliation);
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
    float weakest = std::numeric_limits<float>::max(), least = static_cast<float>(camp_turns(us, them, theirs)) * us.camp, strongest = 0;
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
    return least > guard * 1.001f + 1.0f;
}

// Turns each side needs to empty the other's pool, within `horizon` turns each, playing the fight
// out on the sides given. `self_falls`: whether our own fighter dies before their side does.
// `dealt`, for debug_fights: their first turn's damage, ours, then their first five turns', ours.
// {-1, -1} if the fuel left fell below `fuel_floor` first. With `self_falls` and not Dealt, a fight
// our fighter must outlive ends at once as {0, 0}, and one they must win as {0, horizon}.
template <bool Dealt = false>
std::pair<int, int> simulate(Side& us, Side& them, bool they_first, bool* self_falls = nullptr, int horizon = fight_horizon,
                             std::array<float, 4>* dealt = nullptr, std::uint64_t fuel_floor = 0) {
    int ours = 0, theirs = 0;
    int watched = self_falls ? us.self : -1;
    // Asked at the start and as either side loses a member.
    for (int t = 0, alive = -1; t < 2 * horizon; ++t) {
        if (!Dealt && self_falls && us.alive + 16 * them.alive != alive) {
            alive = us.alive + 16 * them.alive;
            if (watched >= 0 && outlives(us, them, watched, horizon - theirs, horizon - ours)) return {0, 0};
            if (overwhelmed(us, them, horizon - theirs, horizon - ours)) {
                if (watched >= 0) *self_falls = true;
                return {0, horizon};
            }
        }
        if (!Dealt && us.turn < us.quiet_until && them.turn < them.quiet_until) {
            t = play_quiet(us, them, t, 2 * horizon, they_first, ours, theirs);
            if (t == 2 * horizon) break;
        }
        if (fuel_floor && t % 8 == 7 && fuel() < fuel_floor) return {-1, -1};
        const bool their_turn = (t % 2 == 0) == they_first;
        // act()'s branch, counted here: trade()'s debug_block runs act() too, and debug blocks
        // must not nest.
        if constexpr (!Dealt) {
            debug_block({
                const Side& s = their_turn ? them : us;
                ++memo_stats.act[s.stunned == 0 && s.turn < s.quiet_until && s.alive == s.quiet_alive ? 0 : s.plain ? 1 : 2];
            });
        }
        if (their_turn) {
            const float d = act(them, us);
            if constexpr (Dealt)
                if (theirs < 5) (*dealt)[2] += d, (*dealt)[0] += theirs == 0 ? d : 0;
            if (us.camp > 0 && them.turn <= us.camp_until) us.hurt(us.camp);
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
Trade trade(Side& us, Side& them, std::uint64_t fuel_floor = 0, bool they_first = true, int horizon = fight_horizon) {
    Trade t;
    t.allies = us.count;
    t.enemies = them.count;
    if constexpr (debug_fights) t.our_health = us.health(), t.their_health = them.health();
    if (them.count == 0) return t;
    debug_block({ debug_sides = {us, them}; });
    const auto [we_kill, they_kill] = simulate<debug_fights>(us, them, they_first, &t.self_falls, horizon, debug_fights ? &t.dealt : nullptr, fuel_floor);
    debug_block({
        // An early end (outlives, overwhelmed) must agree with the fight played out.
        bool falls = false;
        std::array<float, 4> dealt{};
        const auto [a, b] = simulate<true>(debug_sides[0], debug_sides[1], they_first, &falls, horizon, &dealt);
        if (we_kill >= 0 && ((b > 0) != (they_kill > 0) || falls != t.self_falls))
            std::printf("FIGHT-EXIT-MISMATCH %d %d %d %d %d\n", cambc::round_number(), b, they_kill, falls, t.self_falls);
    });
    if (we_kill < 0) {
        note_shortcut("fight-cut");
        t.lost = t.self_falls = t.cut = true;
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

[[gnu::noinline]] void make_slot(const World& world, const ChampionBelief& c, int slot) {
    auto& m = made_fighters;
    const std::array<std::uint32_t, 3> from{static_cast<std::uint32_t>(c.type), std::bit_cast<std::uint32_t>(hit_strength(c)),
                                            std::bit_cast<std::uint32_t>(hit_focus(c))};
    if (!(m.kits >> slot & 1) || m.kit_of[slot] != from) {
        m.kits |= 1u << slot;
        m.kit_of[slot] = from;
        make_kit(c, m.kit[slot]);
    }
    make_fighter(c, c.is_self ? world.round : next_turn_round(world, c), m.fighter[slot], m.kit[slot]);
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

// A Safety::FightKey's sides (a template, as the key is private): its fighters, each enemy's
// arrival, the camp charge and, idle, our fighter never acting.
constexpr float camp_step = 8; // FightKey::camp_q's unit
template <class Key>
void key_sides(const World& world, const Key& k, std::uint32_t enemies, Side& us, Side& them, std::uint32_t& made) {
    fill(us, world, world.allies, k.who & 0xFFFFu, made);
    fill(them, world, world.enemies, enemies, made);
    if (k.arrive) {
        int i = 0;
        for (unsigned left = enemies; left && i < them.count; left &= left - 1, ++i)
            if (const auto walk = static_cast<int>(k.arrive >> (3 * std::countr_zero(left)) & 7u); walk != 0)
                them.fighters[i].arrives_at = walk, them.plain = false;
    }
    us.camp = static_cast<float>(k.camp_q) * camp_step;
    us.camp_until = k.camp_turns;
    if (k.mode == static_cast<std::uint8_t>(Engage::Mode::idle) && us.count > 0) us.fighters[0].arrives_at = never, us.plain = false;
}

// Debug only: made_fighters as it was before a check made fighters of its own.
constinit Fighters debug_fighters;

} // namespace

int next_turn_round(const World& world, const ChampionBelief& c) {
    // Read for those in sight; ranks are a guess when priorities change unseen.
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
        m.widened_known = false;
    }
    return m;
}

} // namespace

const Strike& strike(const ChampionBelief& c, int turn_round) { return strike_memo(c, turn_round).value; }

int turns_before_ours(const World& world, const ChampionBelief& c) {
    const auto& me = world.me();
    const bool now = c.visible ? !c.acted : world.slot(c, world.round) > world.slot(me, world.round);
    return (now ? 1 : 0) + (world.slot(c, world.round + 1) < world.slot(me, world.round + 1) ? 1 : 0);
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
    auto& m = strike_memo(c, next_turn_round(world, c));
    const auto& s = m.value;
    if (s.reach < 0 || turns_before_ours(world, c) < 2) return s;
    if (m.widened_known) return m.widened;
    m.widened_known = true;
    const auto& f = c.facts();
    const int basic_reach = f.attack_range() + (f.passive == Passive::splash_attack ? 1 : 0) + (f.ranged ? 0 : 1);
    auto& out = m.widened;
    for (int d = 0; d <= Strike::max_reach; ++d) {
        const float walked = s.at(std::max(0, d - 1));
        const float twice = s.hits(d) ? s.at(d) + (d <= basic_reach ? hit_strength(c) : 0.0f) : 0.0f;
        out.damage[d] = std::max(walked, twice);
        out.stuns[d] = s.stuns[std::max(0, d - 1)]; // s.stuns holds from 0 out to some distance
    }
    out.reach = std::min(Strike::max_reach, s.reach + 1);
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

bool live_camp(const World& world, vec2 p) {
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
    if (t.group < 0 || t.member == 255) return false;
    const auto& c = world.camps[t.group];
    return c.state == CampState::alive && c.health[t.member] > 0;
}

// Whether a visible enemy ward sees p this round: a target there is in sight of whoever owns it.
// What the wards see is cast again only when they change, and read as packed bits when the
// terrain's are.
struct Wards {
    int round = -1;
    bool any = false;
    std::array<vec2, 64> cast_from; // the wards `seen` holds
    std::uint32_t cast_count = 0;
    std::array<std::uint8_t, Terrain::bytes> bits;
    bitboard seen{cambc::uninitialized}, wards{cambc::uninitialized}, cast{cambc::uninitialized};

    [[gnu::noinline]] void refresh(const World& world, const Terrain& t) {
        round = world.round;
        ok(cambc::detail::sdk_enemy_ward_occupancy(wards.ptr()));
        const Tiles<64> tiles{wards};
        const auto count = static_cast<std::uint32_t>(tiles.end() - tiles.begin());
        any = count > 0;
        if (!any) return;
        bool same = count == cast_count;
        for (std::uint32_t i = 0; i < count && same; ++i) same = tiles.begin()[i] == cast_from[i];
        if (same) return;
        cast_count = count;
        std::copy(tiles.begin(), tiles.end(), cast_from.begin());
        const auto r = static_cast<std::uint16_t>(cambc::constants::ward_vision_radius);
        shadow_into(world.map().walls, *tiles.begin(), r, seen);
        for (const vec2* w = tiles.begin() + 1; w != tiles.end(); ++w) {
            shadow_into(world.map().walls, *w, r, cast);
            or_into(seen, cast, seen);
        }
        if (t.packed) seen.export_linear_buffer({bits.data(), bitboard::linear_buffer_size()});
    }
};

[[gnu::always_inline]] inline bool warded(const World& world, const Terrain& t, vec2 p) {
    static Wards w;
    if (w.round != world.round) w.refresh(world, t);
    return w.any && (t.packed ? Terrain::bit(w.bits, p.x + p.y * t.width) : test(w.seen, p));
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
    Phase phase{"Reach::build"};
    world_ = &world;
    origin_ = e.pos;
    static std::uint32_t builds = 0;
    stamp_ = ++builds;
    twice_ = twice;
    strength_ = hit_strength(e);
    reach_ = -1;
    const auto& f = e.facts();
    const bool uncertain = e.cooldowns_uncertain();
    const std::array<bool, 2> ready{uncertain || e.ability_ready(0, turn_round), uncertain || e.ability_ready(1, turn_round)};
    const int dash_slot = f.slot_of(AbilityKind::dash);
    const bool dash = dash_slot >= 0 && ready[static_cast<std::size_t>(dash_slot)];
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
        build_ways(e, ready, twice);
        return;
    }
    sets_origin_ = origin_;
    sets_kind_ = kind;
    sets_occupied_ = occupied;
    const auto& st = static_window(world, origin_);
    Window pass = st.pass, land = st.land & ~occupied;
    const Window& camps = st.camps;
    sets_reusable_ = !camps;
    for (int word = 0; word < 2; ++word)
        for (std::uint64_t bits = word ? camps.hi : camps.lo; bits; bits &= bits - 1) {
            const int i = 64 * word + std::countr_zero(bits);
            if (live_camp(world, {origin_.x - win_r + i % win_n, origin_.y - win_r + i / win_n})) {
                pass &= ~tables.bits[static_cast<std::size_t>(i)], land &= ~tables.bits[static_cast<std::size_t>(i)];
                units_ |= tables.bits[static_cast<std::size_t>(i)];
            }
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
    build_ways(e, ready, twice);
}

void Reach::build_ways(const ChampionBelief& e, std::array<bool, 2> ready, bool twice) {
    const auto& f = e.facts();
    const float s = hit_strength(e), focus = hit_focus(e);
    const Recipe recipe{e.type, std::bit_cast<std::uint32_t>(s), std::bit_cast<std::uint32_t>(focus),
                        static_cast<std::uint8_t>(ready[0] | ready[1] << 1), twice, true};
    ways_ = &ways_by_[static_cast<std::size_t>(recipe.slots | recipe.twice << 2)];
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
            if (!ready[slot]) continue;
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
            if (f && (range > 1 || t.bush(u)) && !warded(*world_, t, u)) f &= sight_from(*world_, u, range > 1, ux - win_r, uy - win_r);
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
        // Who sees p, in this window; worked out on first need. Whoever owns a ward that sees p
        // sees it from anywhere.
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
            if (ward < 0) ward = warded(*world_, t, p);
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

std::uint32_t next_generation() {
    static std::uint32_t last = 0;
    return ++last;
}

} // namespace

std::vector<Safety::CampHit>& Safety::member_pool() {
    static std::vector<CampHit> pool;
    return pool;
}

Safety::Safety(const World& world) : world_{world}, threats_{threat_pool()}, members_{member_pool()} {
    centre_ = world.me().pos;
    generation_ = next_generation();
    note_view();
}

Safety::~Safety() {
    debug_block({
        auto& m = memo_stats;
        if (m.sims | m.hits | m.idle_hits | m.pursuit_hits | m.act[0] | m.act[1] | m.act[2])
            std::printf("MEMO %d %d %d %d %d %d %d %d %d\n", world_.round, m.sims, m.hits, m.kept, m.idle_hits, m.pursuit_hits,
                        m.act[0], m.act[1], m.act[2]);
        if (m.verdicts)
            std::printf("VERDICT %d %d %d %d %d\n", world_.round, m.verdicts, m.verdict_sims, m.verdict_memo, m.verdict_dom);
        m = {};
    });
}

std::span<const Safety::CampHit> Safety::awake_members() {
    if (!members_known_) find_members();
    return {members_.data(), static_cast<std::size_t>(member_count_)};
}

[[gnu::noinline]] void Safety::find_members() {
    Phase phase{"find_members"};
    members_known_ = true;
    int count = 0;
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
    static bitboard seen{cambc::uninitialized}, camps{cambc::uninitialized};
    bool reread = false;
    const auto& groups = world_.map().groups;
    world_.each_stirring([&](int g) {
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
            if (refresh_) {
                reread = true;
                vision_into(seen);
                camps_into(camps);
            }
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
            if (c.health[i] <= 0 || m.strength <= 0 || (reread && test(seen, m.pos) && !test(camps, m.pos))) continue;
            if (!stirred && c.member_asleep(i)) continue;
            int reach = m.reach;
            for (int k = 0; k < k_near; ++k) {
                auto& o = others.at[near[k]];
                if (const int d = dist(o.pos, m.pos); d - 1 < reach) reach = std::min(reach, d - first(o));
            }
            if (reach > 0) out[count++] = {m.pos, m.strength * camp_factor_, w, reach, static_cast<std::int16_t>(g)};
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
    // refresh() has just asked gone() of every seen enemy. new_fight leaves the dead out, so only
    // keys naming them would now play out differently.
    std::uint32_t dead = 0;
    for (std::size_t i = 0; i < gone_.size(); ++i) dead |= (gone_[i] == 2 ? 1u : 0u) << i;
    drop_fights(dead);
    generation_ = next_generation();
    built_ = false;
    refresh_ = true;
    reached_ = 0;
    build_cost_ = 0;
    threat_count_ = 0;
    threat_mask_ = 0;
    members_known_ = false;
    camp_area_.reset();
    enemy_area_.reset();
    gone_.fill(0);
    reachable_known_ = false;
}

void Safety::refresh() {
    Phase phase{"safety_refresh"};
    refresh_ = true;
    gone_.fill(0);
    build_cost_ = 0;
    reachable_known_ = false;
    // Fights outlive invalidate() and reobserve(), so a kill must still drop those naming the dead.
    if (!built_ && !members_known_ && fight_count_ == 0) return;
    bool changed = false;
    for (auto left = seen_enemies(); left; left &= left - 1) changed |= gone(world_.enemies[static_cast<std::size_t>(std::countr_zero(left))]);
    if (!changed && members_known_ && member_count_ > 0) {
        static bitboard seen{cambc::uninitialized}, camps{cambc::uninitialized};
        vision_into(seen);
        camps_into(camps);
        for (int i = 0; i < member_count_ && !changed; ++i) changed = test(seen, members_[static_cast<std::size_t>(i)].pos) && !test(camps, members_[static_cast<std::size_t>(i)].pos);
    }
    if (changed) invalidate();
}

[[gnu::noinline]] void Safety::note_view() {
    std::uint16_t enemies = 0, allies = 0;
    const int n = std::min(static_cast<int>(world_.enemies.size()), 16);
    for (int i = 0; i < n; ++i)
        if (const auto& e = world_.enemies[static_cast<std::size_t>(i)]; e.alive && e.visible)
            enemies |= static_cast<std::uint16_t>(1u << i), viewed_[static_cast<std::size_t>(i)] = {e.pos, e.health};
    const int m = std::min(static_cast<int>(world_.allies.size()), 16);
    for (int i = 0; i < m; ++i)
        if (const auto& a = world_.allies[static_cast<std::size_t>(i)]; a.alive && a.visible) allies |= static_cast<std::uint16_t>(1u << i);
    viewed_enemies_ = enemies;
    viewed_allies_ = allies;
    viewed_camps_ = world_.camps_version;
}

// observe() moves nobody and reads no camps: with the same champions in view, their Reach, the
// fighters, the camp members and the fights among visible enemies still hold; only the unseen
// enemies' possible tiles changed. Their strikes are redone too, to drop what Foe kept per tile.
bool Safety::reobserve() {
    if (world_.camps_version != viewed_camps_) return false;
    std::uint16_t enemies = 0, allies = 0;
    const int n = std::min(static_cast<int>(world_.enemies.size()), 16);
    for (int i = 0; i < n; ++i)
        if (const auto& e = world_.enemies[static_cast<std::size_t>(i)]; e.alive && e.visible) {
            enemies |= static_cast<std::uint16_t>(1u << i);
            const auto& v = viewed_[static_cast<std::size_t>(i)];
            if (!(viewed_enemies_ >> i & 1) || v.pos != e.pos || v.health != e.health) return false;
        }
    const int m = std::min(static_cast<int>(world_.allies.size()), 16);
    for (int i = 0; i < m; ++i)
        if (const auto& a = world_.allies[static_cast<std::size_t>(i)]; a.alive && a.visible) allies |= static_cast<std::uint16_t>(1u << i);
    if (enemies != viewed_enemies_ || allies != viewed_allies_) return false;
    const auto unseen = static_cast<std::uint16_t>(~enemies);
    built_ = false;
    threat_count_ = 0;
    threat_mask_ = 0;
    enemy_area_.reset();
    known_ &= enemies;
    counted_ &= enemies;
    listed_ = false;
    build_cost_ = 0;
    reachable_known_ = false;
    // Every mode's key: pursue and idle keys name only visible enemies, so they all stay.
    drop_fights(unseen);
    generation_ = next_generation();
    return true;
}

[[gnu::noinline]] void Safety::strike_foe(const ChampionBelief& e, Foe& x) {
    known_ |= static_cast<std::uint16_t>(1u << e.index);
    x.strike = threat_strike(world_, e);
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
    if (!built_) built_ = true, build_threats(~0u);
}

[[gnu::noinline]] void Safety::build_threats(std::uint32_t which) {
    Phase phase{"build_threats"};
    FuelMeter meter{"safety"};
    // One per enemy, reused between builds: a new field allocates and clears ~13k bytes.
    static std::vector<std::unique_ptr<cambc::distance_field>> fields;
    const auto field_of = [&](int i) -> cambc::distance_field& {
        if (fields.size() <= static_cast<std::size_t>(i)) fields.resize(static_cast<std::size_t>(i) + 1);
        auto& field = fields[static_cast<std::size_t>(i)];
        if (!field) field = std::make_unique<cambc::distance_field>();
        return *field;
    };
    for (auto left = live_enemies() & which & ~std::uint32_t{threat_mask_}; left; left &= left - 1) {
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

// f(enemy, blow) for each enemy build() makes a threat of, with its threat's blow at p: exact if
// visible, by the one unseen rule (tile()) if not.
template <class F> void Safety::each_threat(vec2 p, F&& f) {
    const bool window = window_slot(p) >= 0;
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e)) continue;
        const auto& x = foe(e);
        if (x.strike.reach < 0) continue;
        if (e.visible) f(e, blow(e, p));
        else if (x.weight > 0) f(e, unseen_blow(e, x, p, window));
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
    return blow(e, p).hits ? 0 : std::max(1, dist(p, e.pos) - reach);
}

namespace {

// Inside debug_block only: any_within() on a board of its own, leaving within()'s kept square alone.
bool debug_any_within(const bitboard& tiles, vec2 p, int r) {
    static bitboard box{cambc::uninitialized};
    clear_board(box);
    draw_square(box, p, static_cast<float>(r));
    and_into(box, tiles, box);
    return !board_empty(box);
}

} // namespace

int Safety::threats_at(vec2 p, std::array<ThreatAt, 16>& out) {
    const bool was_built = built_;
    const auto& row = tile(p);
    const unsigned hit = row.vis_mask | row.unseen_mask;
    const bool window = window_slot(p) >= 0;
    int n = 0;
    for (auto left = live_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e) || n == static_cast<int>(out.size())) continue;
        const auto& x = foe(e);
        if (x.strike.reach < 0 || (!e.visible && x.weight <= 0)) continue;
        out[n++] = {e.index, !(hit >> e.index & 1) ? Blow{} : e.visible ? blow(e, p) : unseen_blow(e, x, p, window)};
    }
    debug_block({
        // The old rule before a build: an unseen threat's Chebyshev distance to `possible`, out to
        // its radius.
        static int last = -1;
        for (int i = 0; i < n && !was_built && last != world_.round; ++i) {
            const auto& e = world_.enemies[static_cast<std::size_t>(out[i].enemy)];
            if (e.visible) continue;
            const auto& x = foes_[static_cast<std::size_t>(e.index)];
            const int radius = unseen_radius(x.strike.reach, x.tiles);
            int d = 0;
            while (d <= radius && !debug_any_within(e.possible, p, d)) ++d;
            const Blow old = x.strike.blow(d <= radius ? d : static_cast<int>(unreachable));
            if (old.hits != out[i].blow.hits || std::abs(old.damage - out[i].blow.damage) > 0.01f) {
                last = world_.round;
                std::printf("TABLE-MISMATCH %d threats_at %d %d %.1f %.1f e%d\n", world_.round, p.x, p.y, old.damage, out[i].blow.damage, e.index);
            }
        }
    });
    return n;
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

// The credible field is capped at the radius, inside the reach, so a credible hit is in reach.
float Safety::damage_bound(vec2 p, bool double_unacted) {
    const int s = threat_slot(p);
    const auto& row = rows_[static_cast<std::size_t>(s)];
    auto& lazy = lazy_[static_cast<std::size_t>(s)];
    if (const auto bit = std::uint64_t{1} << s; !(bounds_known_ & bit)) {
        float unseen = 0;
        for (auto left = live_enemies(); left; left &= left - 1) {
            const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
            if (e.visible) continue;
            const auto& x = foe(e);
            if (x.strike.reach < 0 || x.weight <= 0) continue;
            bool near = row.unseen_mask >> e.index & 1;
            if (!near) {
                const int r = unseen_in_reach(e, x, p, s < window_slots);
                near = r > 0 || (r < 0 && reach_field_hit(e, x, p));
            }
            if (near) unseen += x.strike.at(0);
        }
        lazy.bound = unseen;
        bounds_known_ |= bit;
    }
    const float bound = row.vis + lazy.bound + row.camp_worst + (double_unacted ? row.vis_unacted : 0.0f);
    debug_block({
        // The old function: camps at full strength, each credible unseen threat by the distance-0 rule.
        float old = row.vis + (double_unacted ? row.vis_unacted : 0.0f) + debug_old_unseen(p, nullptr);
        for (int i = 0; members_known_ && i < member_count_; ++i)
            if (const auto& m = members_[static_cast<std::size_t>(i)]; in_square(p, m.pos, m.reach)) old += m.strength;
        static int last = -1;
        if (last != world_.round && std::abs(old - bound) > 0.01f) {
            last = world_.round;
            std::printf("TABLE-MISMATCH %d bound %d %d %.1f %.1f\n", world_.round, p.x, p.y, old, bound);
        }
    });
    return bound;
}

float Safety::damage_ceiling(vec2 p, bool double_unacted) {
    float total = camp_damage(p);
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
    const auto& row = tile(p);
    return (row.vis_mask | row.unseen_mask) != 0;
}

float Safety::camp_damage(vec2 p, bool worst) {
    if (awake_members().empty()) return 0;
    sync_table();
    const int s = slot_of(p);
    if (s < 0) {
        TileDanger row;
        fill_camps(p, row);
        return worst ? row.camp_worst : row.camp_exp;
    }
    auto& row = rows_[static_cast<std::size_t>(s)];
    if (const auto bit = std::uint64_t{1} << s; !(camps_known_ & bit)) fill_camps(p, row), camps_known_ |= bit;
    return worst ? row.camp_worst : row.camp_exp;
}

float Safety::worst_damage(vec2 p) { return tile(p).worst(); }

// Any camp member or visible threat in reach is enough on its own. An unseen threat's chance is
// uniform over its possible tiles; it hits p only within its field, capped inside its reach.
bool Safety::threatened(vec2 p) {
    static_assert(unknown_camp_weight >= recall_risk && hit_given_reach >= recall_risk);
    if (camp_damage(p) > 0) return true;
    const bool was_built = built_;
    const auto& row = tile(p);
    const bool threat = row.vis_mask || (row.unseen_mask && unseen_chance(p) >= recall_risk);
    debug_block({
        // The old rule skipped the build only when nothing could hit p by the distance-0 rule.
        bool near = false;
        (void)debug_old_unseen(p, &near);
        const bool old = (was_built || row.vis_mask || near) && threat;
        static int last = -1;
        if (old != threat && last != world_.round) {
            last = world_.round;
            std::printf("TABLE-MISMATCH %d threatened %d %d %d %d\n", world_.round, p.x, p.y, old ? 1 : 0, threat ? 1 : 0);
        }
    });
    return threat;
}

const bitboard& Safety::camp_area() {
    if (!camp_area_) {
        bitboard b;
        for (const auto& m : awake_members())
            draw_square(b, m.pos, static_cast<float>(m.reach));
        camp_area_ = std::move(b);
    }
    return *camp_area_;
}

const bitboard& Safety::enemy_area() {
    if (!enemy_area_) {
        bitboard any;
        // A visible threat's: a superset, as a walls field per enemy each turn would cost ~3k.
        for (const auto& t : threats())
            if (!t.visible) or_into(any, t.area, any);
            else if (const int r = reach_of(*t.belief).reach(); r >= 0) draw_square(any, t.pos, static_cast<float>(r));
        enemy_area_ = std::move(any);
    }
    return *enemy_area_;
}

bitboard Safety::avoid() { return camp_area() | enemy_area(); }

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

const Trade* Safety::memo(const FightKey& key) const {
    static_assert(max_fights <= static_cast<int>(fight_generation.size()));
    for (int i = 0; i < std::min(fight_count_, max_fights); ++i)
        if (const auto& f = fights_[static_cast<std::size_t>(i)]; f.key.who == key.who && f.key == key) {
            debug_block({
                ++memo_stats.hits;
                memo_stats.kept += fight_generation[static_cast<std::size_t>(i)] != generation_;
            });
            return &f.trade;
        }
    return nullptr;
}

void Safety::drop_fights(std::uint32_t enemies) {
    const std::uint32_t named = enemies << 16;
    // Once wrapped, slot order is not age order: blank the keys in place (every key has our bit, so
    // 0 never matches nor settles another) to keep replacing the oldest first.
    if (fight_count_ > max_fights) {
        for (auto& f : fights_)
            if (f.key.who & named) f.key.who = 0;
        return;
    }
    const int count = std::min(fight_count_, max_fights);
    int i = 0;
    while (i < count && !(fights_[static_cast<std::size_t>(i)].key.who & named)) ++i;
    if (i == count) return;
    int kept = i;
    for (; i < count; ++i)
        if (!(fights_[static_cast<std::size_t>(i)].key.who & named)) {
            debug_block({ fight_generation[static_cast<std::size_t>(kept)] = fight_generation[static_cast<std::size_t>(i)]; });
            fights_[static_cast<std::size_t>(kept++)] = fights_[static_cast<std::size_t>(i)];
        }
    fight_count_ = kept;
}

Trade Safety::fight(vec2 p) { return engage(p, {}); }

Trade Safety::fight_of(std::uint32_t key) {
    if (const auto* t = memo(uint_key(key))) return *t;
    return new_fight(key);
}

Trade Safety::new_fight(std::uint32_t key) {
    build();
    return run(uint_key(key), key >> 16 & threat_mask_);
}

Trade Safety::engage(vec2 p, Engage e) {
    Phase phase{"engage"};
    world_.throw_if_stale();
    FightKey k;
    return shape(p, e, k) ? play(k) : Trade{};
}

// Per COMBAT-MERGE.md's rule table.
bool Safety::shape(vec2 p, const Engage& e, FightKey& k) {
    using Mode = Engage::Mode;
    k.arrive = 0;
    k.mode = static_cast<std::uint8_t>(e.mode);
    k.horizon = static_cast<std::uint8_t>(std::clamp(e.horizon, 1, 255));
    std::uint32_t enemies = 0;
    if (e.mode == Mode::stand) {
        const auto& row = tile(p);
        enemies = row.vis_mask | row.unseen_mask;
        if (e.with_enemy >= 0) enemies |= 1u << e.with_enemy;
        if (enemies == 0) return false;
    } else {
        // Pursue: within `approach` walks and off their spawn; idle: arriving within the horizon.
        const bool pursue = e.mode == Mode::pursue;
        enemies = arriving(p, pursue ? e.approach : e.horizon - 1, pursue, &k.arrive);
        if (enemies == 0 && pursue) return false;
    }
    const bool idle = e.mode == Mode::idle;
    const float camp = idle ? camp_damage(p, false) + unseen_hit(p) : stand_camp(p);
    k.camp_q = static_cast<std::uint16_t>(std::clamp(static_cast<int>(camp / camp_step + 0.5f), 0, 0xFFFF));
    if (enemies == 0 && k.camp_q == 0) return false;
    k.camp_turns = k.camp_q == 0 ? 0 : idle ? k.horizon : static_cast<std::uint8_t>(std::clamp(exit_rounds(p), 0, 255));
    k.who = (idle ? 1u << world_.me().index : fighting_allies(world_, p)) | enemies << 16;
    return true;
}

std::uint16_t Safety::arriving(vec2 p, int turns, bool off_spawn, std::uint64_t* arrive) {
    std::uint16_t enemies = 0;
    const auto& spawn = world_.map().near_enemy_spawn;
    for (auto left = seen_enemies(); left; left &= left - 1) {
        const auto& c = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(c) || (off_spawn && test(spawn, c.pos))) continue;
        const int reach = struck(c).strike.reach;
        if (reach < 0 || dist(p, c.pos) - reach > turns) continue;
        const int walk = approach(c, p);
        if (walk > turns) continue;
        enemies |= static_cast<std::uint16_t>(1u << c.index);
        // Arrivals past 7 (horizons above 8) count as 7.
        if (arrive) *arrive |= static_cast<std::uint64_t>(std::min(walk, 7)) << (3 * c.index);
    }
    return enemies;
}

Trade Safety::play(const FightKey& k) {
    Trade t;
    // fight_calibration.py reads every field of a debug_fights trade: none is settled then.
    if (const int how = recall(k, t); how == 0 || (debug_fights && how == 2)) t = run(k, k.who >> 16);
    return t;
}

namespace {

// `worse` has every enemy of `key` and no ally it lacks: a fight only gets worse with more enemies
// or fewer allies.
bool covers(std::uint32_t worse, std::uint32_t key) { return (key & ~worse & 0xFFFF0000u) == 0 && (worse & ~key & 0xFFFFu) == 0; }

} // namespace

int Safety::recall(const FightKey& k, Trade& out) {
    const bool stand = k.mode == static_cast<std::uint8_t>(Engage::Mode::stand);
    if (stand && !linked_known_) note_linked();
    int by = -1;
    for (int i = 0; i < std::min(fight_count_, max_fights); ++i) {
        const auto& f = fights_[static_cast<std::size_t>(i)];
        if (f.key.who == k.who && f.key == k) {
            debug_block({
                auto& m = memo_stats;
                ++(k.mode == static_cast<std::uint8_t>(Engage::Mode::idle)     ? m.idle_hits
                   : k.mode == static_cast<std::uint8_t>(Engage::Mode::pursue) ? m.pursuit_hits
                                                                                : m.hits);
                m.kept += fight_generation[static_cast<std::size_t>(i)] != generation_;
            });
            out = f.trade;
            return 1;
        }
        // Cassi and Issac fall together: one more of them can turn a fight either way.
        if (by >= 0 || !stand || f.key.mode != k.mode || f.key.horizon != k.horizon || ((f.key.who ^ k.who) & linked_who_)) continue;
        // The camps hit our weakest on each of their first camp_turns turns: more for longer only
        // makes a fight worse, like more enemies.
        const bool camp_worse = f.key.camp_q >= k.camp_q && f.key.camp_turns >= k.camp_turns;
        const bool camp_milder = f.key.camp_q <= k.camp_q && f.key.camp_turns <= k.camp_turns;
        if (const auto& t = f.trade; !t.lost && !t.self_falls ? camp_worse && covers(f.key.who, k.who)
                                                              : t.lost && camp_milder && covers(k.who, f.key.who))
            by = i;
    }
    if (by < 0) return 0;
    const auto& settler = fights_[static_cast<std::size_t>(by)];
    const bool lost = settler.trade.lost;
    out = {};
    out.settled = true;
    out.lost = out.self_falls = lost;
    // Not lost: 0 as played. Lost: k's is at most this.
    out.turns_to_kill_us = settler.trade.turns_to_kill_us;
    out.allies = std::popcount(k.who & 0xFFFFu);
    out.enemies = std::popcount(k.who >> 16);
    debug_block({
        // The fight played out must agree.
        debug_fighters = made_fighters;
        std::uint32_t made = made_;
        Side us, them;
        key_sides(world_, k, k.who >> 16, us, them, made);
        bool falls = false;
        std::array<float, 4> dealt{};
        const auto [a, b] = simulate<true>(us, them, true, &falls, k.horizon, &dealt);
        if ((b > 0) != lost || falls != lost)
            std::printf("DOMINANCE-MISMATCH %d %x %x %d %d %d %d %d %d %d\n", world_.round, k.who, settler.key.who, k.camp_q,
                        settler.key.camp_q, k.camp_turns, settler.key.camp_turns, lost ? 1 : 0, b > 0 ? 1 : 0, falls ? 1 : 0);
        made_fighters = debug_fighters;
    });
    return 2;
}

Trade Safety::run(const FightKey& k, std::uint32_t enemies) {
    Phase phase{"new_fight"};
    Side us, them;
    key_sides(world_, k, enemies, us, them, made_);
    const bool stand = k.mode == static_cast<std::uint8_t>(Engage::Mode::stand);
    Trade t;
    const auto before = stand ? fuel() : 0;
    if (k.mode == static_cast<std::uint8_t>(Engage::Mode::idle)) {
        t.allies = us.count;
        t.enemies = them.count;
        t.turns_to_kill_us = simulate(us, them, true, nullptr, k.horizon).second;
        t.lost = t.self_falls = t.turns_to_kill_us != 0;
    } else {
        t = trade(us, them, end_reserve, stand, k.horizon);
    }
    debug_block({ ++memo_stats.sims; });
    // A cut fight is a guess forced by the fuel left: asked again, it may be played out.
    if (!t.cut) {
        const int i = fight_count_++ % max_fights;
        fights_[static_cast<std::size_t>(i)] = {k, t};
        debug_block({ fight_generation[static_cast<std::size_t>(i)] = generation_; });
    }
    if (stand)
        if (const auto after = fuel(); after < before) costliest_fight_ = std::max(costliest_fight_, before - after);
    return t;
}

[[gnu::noinline]] void Safety::note_linked() {
    linked_known_ = true;
    std::uint32_t bits = 0;
    for (std::size_t i = 0; i < world_.allies.size() && i < 16; ++i)
        if (world_.allies[i].facts().passive == Passive::linked_pair) bits |= 1u << i;
    for (std::size_t i = 0; i < world_.enemies.size() && i < 16; ++i)
        if (world_.enemies[i].facts().passive == Passive::linked_pair) bits |= 1u << (16 + i);
    linked_who_ = bits;
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
    // A visible threat's Reach is built on its first query, built_ or not: engage() never builds.
    if (!reachable_known_) list_reachable();
    return 2000 * static_cast<std::uint64_t>(std::popcount(static_cast<unsigned>(reachable_ & ~reached_))) + build_cost_estimate();
}

std::uint64_t Safety::build_cost_estimate() {
    if (built_) return 0;
    if (build_cost_) return build_cost_;
    return estimate_build();
}

[[gnu::noinline]] std::uint64_t Safety::estimate_build() {
    // A visible threat costs its Reach alone, which query_cost_estimate() counts.
    std::uint64_t cost = 0;
    for (auto left = live_enemies() & ~std::uint32_t{threat_mask_}; left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (e.visible || gone(e) || foe(e).weight == 0) continue;
        cost += costliest_unseen() ? costliest_unseen() + costliest_unseen() / 4 : 3000 + 25 * search_chunks();
    }
    build_cost_ = cost;
    return cost;
}

Trade Safety::pursuit(vec2 p, int approach) {
    Phase phase{"pursuit"};
    return engage(p, {.mode = Engage::Mode::pursue, .approach = approach});
}

int Safety::turns_to_kill_idle(vec2 p, int horizon) {
    Phase phase{"turns_to_kill_idle"};
    return engage(p, {.mode = Engage::Mode::idle, .horizon = horizon}).turns_to_kill_us;
}

bool Safety::lethal(vec2 p) {
    Phase phase{"lethal"};
    const float health = world_.me().health;
    // Most turns no enemy is near enough; skip the threat build then.
    const bool was_built = built_;
    if (!built_ && damage_ceiling(p) < health) return false;
    const auto& row = tile(p);
    const bool dies = row.worst() >= health;
    debug_block({
        const bool old = (was_built || row.vis + row.camp_worst + debug_old_unseen(p, nullptr) >= health) && dies;
        static int last = -1;
        if (old != dies && last != world_.round) {
            last = world_.round;
            std::printf("TABLE-MISMATCH %d lethal %d %d %d %d\n", world_.round, p.x, p.y, old ? 1 : 0, dies ? 1 : 0);
        }
    });
    return dies;
}

void Safety::sync_table() {
    if (table_generation_ == generation_) return;
    table_generation_ = generation_;
    threats_known_ = camps_known_ = chances_known_ = bounds_known_ = 0;
    gate_asked_ = gate_near_ = 0;
    reach_asked_ = reach_near_ = reach_all_ = reach_built_ = 0;
    ring_used_ = 0;
}

int Safety::window_slot(vec2 p) const {
    const auto dx = static_cast<unsigned>(p.x - centre_.x + 3), dy = static_cast<unsigned>(p.y - centre_.y + 3);
    return dx < 7 && dy < 7 ? static_cast<int>(7 * dy + dx) : -1;
}

int Safety::slot_of(vec2 p) {
    if (const int s = window_slot(p); s >= 0) return s;
    for (int k = 0; k < 4; ++k)
        if ((ring_used_ >> k & 1) && ring_at_[static_cast<std::size_t>(k)] == p) return window_slots + k;
    return -1;
}

int Safety::claim_slot(vec2 p) {
    sync_table();
    if (const int s = slot_of(p); s >= 0) return s;
    const int k = ring_next_++ & 3;
    ring_used_ |= static_cast<std::uint8_t>(1u << k);
    ring_at_[static_cast<std::size_t>(k)] = p;
    const auto keep = ~(std::uint64_t{1} << (window_slots + k));
    threats_known_ &= keep, camps_known_ &= keep, chances_known_ &= keep, bounds_known_ &= keep;
    return window_slots + k;
}

int Safety::threat_slot(vec2 p) {
    const int s = claim_slot(p);
    if (const auto bit = std::uint64_t{1} << s; !(threats_known_ & bit)) {
        auto& row = rows_[static_cast<std::size_t>(s)];
        if (!(camps_known_ & bit)) fill_camps(p, row), camps_known_ |= bit;
        fill_threats(p, row);
        threats_known_ |= bit;
    }
    return s;
}

const TileDanger& Safety::tile(vec2 p) { return rows_[static_cast<std::size_t>(threat_slot(p))]; }

[[gnu::noinline]] void Safety::fill_threats(vec2 p, TileDanger& row) {
    Phase phase{"tile"};
    std::uint16_t vis_mask = 0, stun_mask = 0, unseen_mask = 0;
    float vis = 0, vis_unacted = 0, unseen = 0;
    each_threat(p, [&](const ChampionBelief& e, const Blow& b) {
        if (!b.hits) return;
        const auto bit = static_cast<std::uint16_t>(1u << e.index);
        if (b.stuns) stun_mask |= bit;
        if (e.visible) {
            vis_mask |= bit, vis += b.damage;
            if (!e.acted) vis_unacted += b.damage;
        } else {
            unseen_mask |= bit, unseen += b.damage;
        }
    });
    row.vis_mask = vis_mask, row.stun_mask = stun_mask, row.unseen_mask = unseen_mask;
    row.vis = vis, row.vis_unacted = vis_unacted, row.unseen = unseen;
}

void Safety::fill_camps(vec2 p, TileDanger& row) {
    float worst = 0, expected = 0;
    for (const auto& m : awake_members())
        if (in_square(p, m.pos, m.reach)) worst += m.strength, expected += m.strength * m.weight;
    row.camp_worst = worst, row.camp_exp = expected;
}

// Its field is capped at the radius, so only `possible` within the radius of p can hit p: within
// radius + 3 of the window's centre for any window tile. Only this enemy's threat is built.
Blow Safety::unseen_blow(const ChampionBelief& e, const Foe& x, vec2 p, bool window) {
    if (const auto bit = static_cast<std::uint16_t>(1u << e.index); !built_ && !(threat_mask_ & bit)) {
        const int radius = unseen_radius(x.strike.reach, x.tiles);
        if (window) {
            if (!(gate_asked_ & bit)) {
                gate_asked_ |= bit;
                if (any_within(e.possible, centre_, radius + 3)) gate_near_ |= bit;
            }
            if (!(gate_near_ & bit)) return {};
        } else if (!any_within(e.possible, p, radius)) {
            return {};
        }
        world_.throw_if_stale();
        build_threats(bit);
        build_cost_ = 0;
    }
    for (int i = 0; i < threat_count_; ++i)
        if (const auto& t = threats_[static_cast<std::size_t>(i)]; t.enemy == e.index) return t.at(p);
    return {};
}

// Window tiles lie within 3 of the centre. Out of the reach + 3 it is out of the radius + 3 too,
// which answers unseen_blow's gate.
int Safety::unseen_in_reach(const ChampionBelief& e, const Foe& x, vec2 p, bool window) {
    const auto bit = static_cast<std::uint16_t>(1u << e.index);
    const int reach = x.strike.reach;
    if (!window) return (reach_built_ & bit ? reach_field_hit(e, x, p) : any_within(e.possible, p, reach)) ? 1 : 0;
    if (!(reach_asked_ & bit)) {
        reach_asked_ |= bit;
        if (!any_within(e.possible, centre_, reach + 3)) {
            gate_asked_ |= bit;
        } else {
            reach_near_ |= bit;
            if (unseen_radius(reach, x.tiles) == reach) gate_asked_ |= bit, gate_near_ |= bit;
            if (reach >= 3 && any_within(e.possible, centre_, reach - 3)) reach_all_ |= bit;
        }
    }
    if (!(reach_near_ & bit)) return 0;
    return reach_all_ & bit ? 1 : -1;
}

namespace {

// One per enemy, reused between turns.
cambc::distance_field& reach_field(int i) {
    static std::array<std::unique_ptr<cambc::distance_field>, 16> fields;
    auto& field = fields[static_cast<std::size_t>(i)];
    if (!field) field = std::make_unique<cambc::distance_field>();
    return *field;
}

} // namespace

// Over no walls a king-step field is the Chebyshev distance.
bool Safety::reach_field_hit(const ChampionBelief& e, const Foe& x, vec2 p) {
    auto& field = reach_field(e.index);
    if (const auto bit = static_cast<std::uint16_t>(1u << e.index); !(reach_built_ & bit)) {
        reach_built_ |= bit;
        static bitboard reached{cambc::uninitialized};
        static const bitboard none;
        field.compute(none, e.possible, reached, static_cast<std::uint16_t>(x.strike.reach));
    }
    return steps_at(field, p) <= x.strike.reach;
}

float Safety::debug_old_unseen(vec2 p, bool* near) {
    float total = 0;
    for (auto left = live_enemies(); left; left &= left - 1) {
        const int i = std::countr_zero(left);
        const auto& e = world_.enemies[static_cast<std::size_t>(i)];
        if (e.visible || !(counted_ >> i & 1)) continue;
        const auto& x = foes_[static_cast<std::size_t>(i)];
        if (x.strike.reach < 0 || x.weight <= 0 || !debug_any_within(e.possible, p, x.strike.reach)) continue;
        total += x.strike.at(0);
        if (near) *near = true;
    }
    return total;
}

float Safety::strike_sum(vec2 p, std::uint16_t* mask) {
    float total = 0;
    std::uint16_t bits = 0;
    for (auto left = seen_enemies(); left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        if (gone(e)) continue;
        const auto& s = struck(e).strike;
        if (const int d = dist(p, e.pos); s.hits(d)) total += s.at(d), bits |= static_cast<std::uint16_t>(1u << e.index);
    }
    if (mask) *mask = bits;
    return total;
}

int Safety::exit_rounds(vec2 p) {
    if (camp_damage(p) <= 0) return 0;
    const int longest = world_.map().max_camp_reach;
    // Over no walls a king-step field is the Chebyshev distance to the nearest exit.
    static cambc::distance_field field;
    if (exits_generation_ != generation_) {
        exits_generation_ = generation_;
        static bitboard exits{cambc::uninitialized}, reached{cambc::uninitialized};
        static const bitboard none;
        or_into(world_.map().standable, camp_area(), exits);
        xor_into(exits, camp_area(), exits);
        field.compute(none, exits, reached, static_cast<std::uint16_t>(longest));
    }
    const int r = std::clamp(steps_at(field, p), 1, longest + 1);
    debug_block({
        // The old ring walk, tile by tile.
        const auto out = [&](vec2 q) {
            if (!in_bounds(q) || !test(world_.map().standable, q)) return false;
            TileDanger t;
            fill_camps(q, t);
            return t.camp_worst <= 0;
        };
        int old = longest + 1;
        for (int k = 1; k <= longest && old > longest; ++k)
            for (int i = -k; i <= k && old > longest; ++i)
                if (out({p.x + i, p.y - k}) || out({p.x + i, p.y + k}) || out({p.x - k, p.y + i}) || out({p.x + k, p.y + i})) old = k;
        static int last = -1;
        if (old != r && last != world_.round) {
            last = world_.round;
            std::printf("TABLE-MISMATCH %d exit %d %d %d %d\n", world_.round, p.x, p.y, old, r);
        }
    });
    return r;
}

float Safety::unseen_chance(vec2 p) {
    const int s = threat_slot(p);
    const auto bit = std::uint64_t{1} << s;
    auto& lazy = lazy_[static_cast<std::size_t>(s)];
    if (chances_known_ & bit) return lazy.chance;
    float safe = 1;
    for (unsigned left = rows_[static_cast<std::size_t>(s)].unseen_mask; left; left &= left - 1) {
        const auto& e = world_.enemies[static_cast<std::size_t>(std::countr_zero(left))];
        const auto& x = foe(e);
        const auto near = count_within(e.possible, p, x.strike.reach);
        safe *= 1 - std::min(1.0f, static_cast<float>(near) / static_cast<float>(x.tiles)) * hit_given_reach;
    }
    lazy.chance = 1 - safe;
    chances_known_ |= bit;
    return lazy.chance;
}

// The verdict section (W2-A).

int Safety::idle_turns(vec2 p, int horizon) { return turns_to_kill_idle(p, horizon); }

void Safety::set_claimed(int group) {
    if (group == claimed_) return;
    claimed_ = group;
    if (guarded_generation_ == generation_ && guard_asked_) guard_asked_ = guard_true_ = 0, guard_epoch_ = next_generation();
}

float Safety::stand_camp(vec2 p) {
    float charge = camp_damage(p, false);
    if (charge <= 0 || claimed_ < 0) return charge;
    for (const auto& m : awake_members())
        if (m.group == claimed_ && in_square(p, m.pos, m.reach)) charge -= m.strength * m.weight;
    return std::max(0.0f, charge);
}

Verdict Safety::verdict(vec2 q) {
    Phase phase{"verdict"};
    world_.throw_if_stale();
    FightKey k;
    if (shape(q, {}, k)) return judge(k);
    debug_block({ ++memo_stats.verdicts; });
    return {};
}

Verdict Safety::judge(const FightKey& k) {
    Trade t;
    const int how = recall(k, t);
    if (how == 0) t = run(k, k.who >> 16);
    debug_block({
        auto& m = memo_stats;
        ++m.verdicts;
        ++(how == 0 ? m.verdict_sims : how == 1 ? m.verdict_memo : m.verdict_dom);
    });
    return {t.lost, t.self_falls};
}

bool Safety::guard_rule(Verdict v, bool dies) const {
    return v.lost || (v.falls && (dies || linked_partner(world_, world_.me()) != nullptr));
}

void Safety::sync_guard() {
    if (guarded_generation_ == generation_) return;
    guarded_generation_ = guard_epoch_ = generation_;
    guard_asked_ = guard_true_ = 0;
}

// Its fight when a visible foe could make q worse than here: more of them, or more damage, by their
// strike bounds and then by the table.
bool Safety::exposed(vec2 q, FightKey& k, bool& dies) {
    if (!in_bounds(q)) return false;
    std::uint16_t near = 0;
    const float bound = strike_sum(q, &near);
    if (near == 0 || !test(world_.map().open_for_us, q)) return false;
    const auto& here = tile(centre_);
    const std::uint16_t here_mask = here.vis_mask;
    const float here_vis = here.vis;
    const auto no_worse = [&](std::uint16_t mask, float damage) { return (mask & ~here_mask) == 0 && damage <= here_vis; };
    if (no_worse(near, bound)) return false;
    const auto& row = tile(q);
    if (row.vis_mask == 0 || no_worse(row.vis_mask, row.vis)) return false;
    dies = row.worst() >= world_.me().health;
    return shape(q, {}, k);
}

bool Safety::guarded(vec2 q) {
    const int s = window_slot(q);
    if (s < 0 || q == centre_) return false;
    // Before the cache too: resumed after running out of fuel, its answers are a round old.
    world_.throw_if_stale();
    sync_guard();
    const auto bit = std::uint64_t{1} << s;
    if (guard_asked_ & bit) return (guard_true_ & bit) != 0;
    Phase phase{"guarded"};
    guard_asked_ |= bit;
    FightKey k;
    bool dies = false;
    if (!exposed(q, k, dies) || !guard_rule(judge(k), dies)) return false;
    guard_true_ |= bit;
    return true;
}

const bitboard* Safety::guarded_board() {
    sync_guard();
    if (!guard_true_) return nullptr;
    // One Safety lives at a time and generations are unique: a board from another is redrawn.
    static bitboard board{cambc::uninitialized};
    if (board_generation_ != guard_epoch_) board_generation_ = guard_epoch_, board_bits_ = 0, clear_board(board);
    for (auto left = guard_true_ & ~board_bits_; left; left &= left - 1) {
        const int s = std::countr_zero(left);
        set_tile(board, {centre_.x + s % 7 - 3, centre_.y + s / 7 - 3});
    }
    board_bits_ = guard_true_;
    return &board;
}

float Safety::exit_damage(vec2 p) {
    const float worst = camp_damage(p);
    return worst > 0 ? worst * static_cast<float>(exit_rounds(p)) : 0.0f;
}

float Safety::escape_cost(vec2 q) {
    const auto& t = tile(q);
    const float hit = t.worst(), camp = t.camp_worst;
    if (camp <= 0) return hit;
    return hit + camp * static_cast<float>(std::max(0, exit_rounds(q) - 1));
}

void Safety::note_unseen_hit(vec2 at, float damage) { ghost_at_ = at, ghost_ = damage; }

float Safety::unseen_hit(vec2) const { return 0; }

std::uint32_t Safety::guard_epoch() const { return guarded_generation_ == generation_ ? guard_epoch_ : generation_; }

// guard_true_ gains a bit once per tile an epoch: asking again changes nothing.
std::uint32_t Safety::guard_stamp() const {
    return guard_epoch() << 8 | (guarded_generation_ == generation_ ? static_cast<std::uint32_t>(std::popcount(guard_true_)) & 0xFFu : 0u);
}

} // namespace aph
