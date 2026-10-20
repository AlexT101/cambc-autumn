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

constexpr int max_fighters = 6; // one team's bodies
constexpr int never = std::numeric_limits<int>::max();

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
    // Own turns before `quiet_until` are only the basic attacks, `quiet_damage` from `quiet_hits`
    // hits, while nobody is stunned and `alive` stays `quiet_alive`.
    int quiet_until = 0, quiet_alive = -1, quiet_hits = 0;
    float quiet_damage = 0;
    int weak = -2; // weakest(), or -2 when it must be found again
    bool plain = true; // every kit plain and no arrivals

    Side() {}

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

// A champion's casts, from its type, Strength and Focus alone. A heal is valued even with no ally
// to take it: attack() then finds no target and moves on, as if it were worth nothing.
void make_kit(const ChampionBelief& c, Kit& kit) {
    const auto& facts = c.facts();
    for (int s = 0; s < 2; ++s) {
        const auto& a = facts.abilities[s];
        auto& e = kit.cast[s];
        e = {};
        e.value = a.stuns ? c.strength : 0;
        switch (a.kind) {
        case AbilityKind::attack_reset: e.value += c.strength; break;
        case AbilityKind::damage:
        case AbilityKind::shield:
        case AbilityKind::heal: e.value += a.multiplier * c.focus; break;
        default: break;
        }
        e.stuns = a.stuns;
        if (a.kind == AbilityKind::shield || a.kind == AbilityKind::heal) e.heal = a.multiplier * c.focus;
        e.heals_self = a.kind == AbilityKind::shield;
        e.heals_ally = e.heal != 0 && !e.heals_self;
        if (a.kind == AbilityKind::attack_reset) e.damage = c.strength;
        if (a.kind == AbilityKind::damage) e.damage = a.multiplier * c.focus;
        e.hits = a.kind == AbilityKind::attack_reset || a.kind == AbilityKind::damage ? 2 : 1;
        e.duration = a.duration;
    }
    kit.preference = kit.cast[1].value > kit.cast[0].value ? std::array<int, 2>{1, 0} : std::array<int, 2>{0, 1};
    kit.plain = exact(c.strength) && exact(kit.cast[0].damage) && exact(kit.cast[1].damage) && !kit.cast[0].heals_self
                && !kit.cast[1].heals_self;
}

// A champion as it enters a fight, with its kit made.
void make_fighter(const ChampionBelief& c, int turn_round, Fighter& f, Kit& kit) {
    const auto& facts = c.facts();
    f.kit = &kit;
    f.strength = c.strength;
    const bool uncertain = c.cooldowns_uncertain();
    for (int s = 0; s < 2; ++s)
        f.ready_at[s] = kit.cast[s].value <= 0 ? never : uncertain ? 0 : std::max(0, c.ready_round[s] - turn_round);
    f.next_cast = next_cast(f);
    f.arrives_at = 0;
    f.stun_immune = facts.passive == Passive::stun_immune;
    f.linked = facts.passive == Passive::linked_pair;
    f.health = c.health;
    f.max_health = c.max_health;
    f.shield = 0;
    f.shield_until = never;
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
    std::array<std::array<std::uint32_t, 3>, 32> kit_of;
    Fighters() {}
};

Fighters& made_fighters() {
    static Fighters f;
    return f;
}

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
    const float camp = us.camp;
    for (; t < end; ++t) {
        if ((t % 2 == 0) == they_first) {
            if (them.turn >= them.quiet_until || them.alive != them.quiet_alive || them.stunned != 0) break;
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

// Turns each side needs to empty the other's pool, within `horizon` turns each, playing the fight
// out on the sides given. `self_falls`: whether our own fighter dies before their side does.
// `dealt`, for debug_fights: their first turn's damage, ours, then their first five turns', ours.
// {-1, -1} if the fuel left fell below `fuel_floor` first.
std::pair<int, int> simulate(Side& us, Side& them, bool they_first, bool* self_falls = nullptr, int horizon = 24,
                             std::array<float, 4>* dealt = nullptr, std::uint64_t fuel_floor = 0) {
    int ours = 0, theirs = 0;
    for (int t = 0; t < 2 * horizon; ++t) {
        if (!dealt && us.turn < us.quiet_until && them.turn < them.quiet_until) {
            t = play_quiet(us, them, t, 2 * horizon, they_first, ours, theirs);
            if (t == 2 * horizon) break;
        }
        if (fuel_floor && t % 8 == 7 && fuel() < fuel_floor) return {-1, -1};
        const bool their_turn = (t % 2 == 0) == they_first;
        if (their_turn) {
            const float d = act(them, us);
            if (dealt && theirs < 5) (*dealt)[2] += d, (*dealt)[0] += theirs == 0 ? d : 0;
            if (us.camp > 0) us.hurt(us.camp);
            ++theirs;
        } else {
            const float d = act(us, them);
            if (dealt && ours < 5) (*dealt)[3] += d, (*dealt)[1] += ours == 0 ? d : 0;
            ++ours;
        }
        // Ren's reflection can fell the side whose turn it is.
        if (self_falls && us.self >= 0 && us.fighters[us.self].health <= 0) *self_falls = true;
        if (us.alive == 0) return {0, std::max(1, theirs)};
        if (them.count > 0 && them.alive == 0) return {std::max(1, ours), 0};
    }
    return {0, 0};
}

// Only the order where they strike first: `lost` is all callers need.
// Plays the fight out on the sides given, which callers discard: copying them is costly.
Trade trade(Side& us, Side& them, std::uint64_t fuel_floor = 0, bool they_first = true) {
    Trade t;
    t.allies = us.count;
    t.enemies = them.count;
    if constexpr (debug_fights) t.our_health = us.health(), t.their_health = them.health();
    if (them.count == 0) return t;
    const auto [we_kill, they_kill] = simulate(us, them, they_first, &t.self_falls, 24, debug_fights ? &t.dealt : nullptr, fuel_floor);
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

// Us, and the allies we see within fight_ally_radius of p.
bool fights_with(const ChampionBelief& a, vec2 p) {
    return a.alive && (a.is_self || (a.visible && dist(p, a.pos) <= fight_ally_radius));
}

// `made`: bit i, Fighters::fighter[i] is this turn's.
const Fighter& fighter(const World& world, const ChampionBelief& c, std::uint32_t& made) {
    const int slot = (c.side == team::enemy ? 16 : 0) + c.index;
    auto& m = made_fighters();
    if (!(made >> slot & 1)) {
        made |= 1u << slot;
        const std::array<std::uint32_t, 3> from{static_cast<std::uint32_t>(c.type), std::bit_cast<std::uint32_t>(c.strength),
                                                std::bit_cast<std::uint32_t>(c.focus)};
        if (!(m.kits >> slot & 1) || m.kit_of[slot] != from) {
            m.kits |= 1u << slot;
            m.kit_of[slot] = from;
            make_kit(c, m.kit[slot]);
        }
        make_fighter(c, c.is_self ? world.round : next_turn_round(world, c), m.fighter[slot], m.kit[slot]);
    }
    return m.fighter[slot];
}

void join_allies(const World& world, Side& us, vec2 p, std::uint32_t& made) {
    for (const auto& a : world.allies) {
        if (!fights_with(a, p)) continue;
        if (a.is_self) us.self = us.count;
        us.add(fighter(world, a, made));
    }
}

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
    add(range + walk, s, false);
    for (int slot = 0; slot < 2; ++slot) {
        if (!(slots >> slot & 1)) continue;
        const auto& a = f.abilities[slot];
        switch (a.kind) {
        case AbilityKind::attack_reset:
            add(range + walk, 2 * s, a.stuns);
            if (f.ranged) add(range + 1, s, a.stuns); // walk, reset, attack
            break;
        case AbilityKind::dash: add(range + walk + 2, s, false); break;
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
    cambc::champion_type type;
    std::uint32_t strength, focus;
    unsigned slots = 4; // never a key
    Strike value;
    bool widened_known;
    Strike widened;
};

StrikeMemo& strike_memo(const ChampionBelief& c, int turn_round) {
    static std::array<StrikeMemo, 16> memo;
    const bool uncertain = c.cooldowns_uncertain();
    const unsigned slots =
        (uncertain || c.ability_ready(0, turn_round) ? 1u : 0u) | (uncertain || c.ability_ready(1, turn_round) ? 2u : 0u);
    const auto s = std::bit_cast<std::uint32_t>(c.strength), focus = std::bit_cast<std::uint32_t>(c.focus);
    auto& m = memo[(c.side == team::enemy ? 8u : 0u) + (static_cast<unsigned>(c.index) & 7u)];
    if (m.slots != slots || m.type != c.type || m.strength != s || m.focus != focus) {
        m.type = c.type;
        m.strength = s;
        m.focus = focus;
        m.slots = slots;
        m.value = compute_strike(c.facts(), c.strength, c.focus, slots);
        m.widened_known = false;
    }
    return m;
}

} // namespace

Strike strike(const ChampionBelief& c, int turn_round) { return strike_memo(c, turn_round).value; }

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
    const auto s = std::bit_cast<std::uint32_t>(c.strength), focus = std::bit_cast<std::uint32_t>(c.focus);
    auto& m = memo[static_cast<unsigned>(c.index) & 7u];
    if (!m.known || m.type != c.type || m.strength != s || m.focus != focus) {
        const auto k = compute_strike(c.facts(), c.strength, c.focus, 3u);
        m = {c.type, s, focus, true, k.hits(0) ? k.at(0) + c.strength : 0.0f};
    }
    return m.damage;
}

} // namespace

Strike threat_strike(const World& world, const ChampionBelief& c) {
    auto& m = strike_memo(c, next_turn_round(world, c));
    const auto& s = m.value;
    if (s.reach < 0 || turns_before_ours(world, c) < 2) return s;
    if (m.widened_known) return m.widened;
    m.widened_known = true;
    const auto& f = c.facts();
    const int basic_reach = f.attack_range() + (f.ranged ? 0 : 1);
    auto& out = m.widened;
    for (int d = 0; d <= Strike::max_reach; ++d) {
        const float walked = s.at(std::max(0, d - 1));
        const float twice = s.hits(d) ? s.at(d) + (d <= basic_reach ? c.strength : 0.0f) : 0.0f;
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
        return packed ? bit(b, p.x + p.y * width) : board.is_set(p);
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

const Terrain& terrain(const StaticMap& map) {
    static Terrain t;
    if (t.ready) return t;
    t.ready = true;
    t.map = &map;
    t.width = map.width;
    t.height = map.height;
    check_chunks(t);
    const std::size_t size = bitboard::linear_buffer_size();
    if (size + 8 > Terrain::bytes) return t;
    map.walls.export_linear_buffer({t.walls.data(), size});
    // Bits run from the low end of each byte; check on a set tile.
    if (!map.walls.is_empty()) {
        const vec2 probe = first_tile(map.walls);
        if (!Terrain::bit(t.walls, probe.x + probe.y * t.width)) return t;
    }
    map.blocked_for_them.export_linear_buffer({t.blocked.data(), size});
    map.bushes.export_linear_buffer({t.bushes.data(), size});
    map.camp_tiles.export_linear_buffer({t.camps.data(), size});
    t.packed = true;
    return t;
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
bool warded(const World& world, vec2 p) {
    static int round = -1;
    static bool any = false;
    static std::array<vec2, 64> cast_from; // the wards `seen` holds
    static std::uint32_t cast_count = 0;
    static std::array<std::uint8_t, Terrain::bytes> bits;
    static bitboard seen{cambc::uninitialized}, wards{cambc::uninitialized}, cast{cambc::uninitialized};
    const auto& t = terrain(world.map());
    if (round != world.round) {
        round = world.round;
        cambc::vision::ward_tiles_into(team::enemy, wards);
        any = !wards.is_empty();
        if (any) {
            const Tiles<64> tiles{wards};
            const auto count = static_cast<std::uint32_t>(tiles.end() - tiles.begin());
            if (count != cast_count || !std::equal(tiles.begin(), tiles.end(), cast_from.begin())) {
                cast_count = count;
                std::copy(tiles.begin(), tiles.end(), cast_from.begin());
                seen.clear();
                const auto r = static_cast<std::uint16_t>(cambc::constants::ward_vision_radius);
                for (const vec2 w : tiles) {
                    world.map().walls.shadow_cast_into(w, r, cast);
                    seen |= cast;
                }
                if (t.packed) seen.export_linear_buffer({bits.data(), bitboard::linear_buffer_size()});
            }
        }
    }
    return any && (t.packed ? Terrain::bit(bits, p.x + p.y * t.width) : seen.is_set(p));
}

std::array<Window, 100 * 100> sight_masks;
std::array<std::uint8_t, 100 * 100> sight_known;

// Who sees p, laid out around p: within 1 (`far` false) or within win_r. Far masks depend only on
// terrain, so they are kept for the game.
Window sight(const World& world, vec2 p, bool far) {
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
        map.walls.shadow_cast_into(p, static_cast<std::uint16_t>(win_r), viewers);
        if (!plain) {
            viewers &= map.bushes;
            if (!t.bush(p)) {
                map.walls_and_bushes.shadow_cast_into(p, static_cast<std::uint16_t>(win_r), outside);
                drop(outside, map.bushes);
                viewers |= outside;
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
    if (i < known.size()) masks[i] = m, known[i] = 1;
    return m;
}

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
                        if (!t.inside(p) || world.map().walls.is_set(p)) continue;
                        through |= 1u << k;
                        if (!world.map().blocked_for_them.is_set(p)) open |= 1u << k;
                        if (world.map().group_at(p) >= 0) camp |= 1u << k;
                    }
                }
                pass |= Window{through, 0}.shl(Row * win_n);
                land |= Window{open, 0}.shl(Row * win_n);
                camps |= Window{camp, 0}.shl(Row * win_n);
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
    const auto key = static_cast<std::uint8_t>(((from * 8 + range) * 2 + sight) * 2 + walked);
    for (int i = 0; i < count_; ++i) {
        auto& w = ways_[static_cast<std::size_t>(i)];
        if (w.key == key) {
            w.damage = std::max(w.damage, damage);
            w.stuns = w.stuns || stuns;
            return i;
        }
    }
    if (count_ == static_cast<int>(ways_.size())) return -1;
    ways_[static_cast<std::size_t>(count_)] = {damage, from, static_cast<std::int8_t>(range), key, sight, stuns, walked};
    return count_++;
}

void Reach::build(const World& world, const ChampionBelief& e, int turn_round, bool twice) {
    world_ = &world;
    origin_ = e.pos;
    static std::uint32_t builds = 0;
    stamp_ = ++builds;
    twice_ = twice;
    strength_ = e.strength;
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
            if (live_camp(world, {origin_.x - win_r + i % win_n, origin_.y - win_r + i / win_n}))
                pass &= ~tables.bits[static_cast<std::size_t>(i)], land &= ~tables.bits[static_cast<std::size_t>(i)];
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
    const Recipe recipe{e.type, std::bit_cast<std::uint32_t>(e.strength), std::bit_cast<std::uint32_t>(e.focus),
                        static_cast<std::uint8_t>(ready[0] | ready[1] << 1), twice, true};
    if (recipe == recipe_) {
        set_reach();
        return;
    }
    recipe_ = recipe;
    count_ = 0;
    basic_ = -1;
    const Tiles basic_from = f.ranged ? here : walked1;
    const int range = f.attack_range();
    const float s = e.strength;
    for (int turn = 0; turn < (twice ? 2 : 1); ++turn) {
        const bool walked = turn == 1;
        // A walk first, on the first of two turns.
        const auto from = [&](Tiles x) { return !walked ? x : x == here ? walked1 : x == walked1 ? walked2 : dashed_walked; };
        const int basic = add(from(basic_from), range, true, s, false, walked);
        if (!walked) basic_ = basic;
        for (std::size_t slot = 0; slot < 2; ++slot) {
            if (!ready[slot]) continue;
            const auto& a = f.abilities[slot];
            const float spell = a.multiplier * e.focus;
            switch (a.kind) {
            case AbilityKind::attack_reset:
                add(from(basic_from), range, true, 2 * s, a.stuns, walked);
                if (f.ranged) add(from(walked1), range, true, s, a.stuns, walked); // walk, reset, attack
                break;
            case AbilityKind::dash: add(from(dashed), range, true, s, false, walked); break;
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
    for (int i = 1; i < count_; ++i)
        for (int j = i; j > 0 && ways_[static_cast<std::size_t>(j)].damage > ways_[static_cast<std::size_t>(j - 1)].damage; --j) {
            std::swap(ways_[static_cast<std::size_t>(j)], ways_[static_cast<std::size_t>(j - 1)]);
            if (basic_ == j) basic_ = j - 1;
            else if (basic_ == j - 1) basic_ = j;
        }
    set_reach();
}

void Reach::set_reach() {
    reach_ = -1;
    for (int i = 0; i < count_; ++i) {
        auto& w = ways_[static_cast<std::size_t>(i)];
        w.bound = static_cast<std::int8_t>(extent_[w.from] + w.range);
        reach_ = std::max(reach_, static_cast<int>(w.bound));
    }
}

Blow Reach::at(vec2 p) const {
    auto& memo = memo_[static_cast<std::size_t>((p.x & 7) | (p.y & 7) << 3)];
    if (memo.stamp == stamp_ && memo.p == p) return memo.blow;
    Blow out;
    const int dx = p.x - origin_.x, dy = p.y - origin_.y;
    if (std::max(std::abs(dx), std::abs(dy)) <= reach_ && terrain(world_->map()).inside(p)) {
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
        for (int i = 0; i < count_; ++i) {
            const auto& w = ways_[static_cast<std::size_t>(i)];
            if (d > w.bound) continue;
            if (out.hits && w.damage <= (w.walked ? walked : single) && (!w.stuns || out.stuns) && !(twice_ && i == basic_)) continue;
            Window from = tiles_[w.from] & box(dx + win_r, dy + win_r, w.range);
            if (!from) continue;
            if (w.sight && !near_known && !far_known && warded(*world_, p)) near_known = far_known = true, near = far = win_full;
            if (w.sight) {
                if (w.range <= 1) {
                    if (!near_known) near = sight_from(*world_, p, false, dx, dy), near_known = true;
                    from &= near;
                } else {
                    if (!far_known) far = sight_from(*world_, p, true, dx, dy), far_known = true;
                    from &= far;
                }
                if (!from) continue;
            }
            if (w.walked) walked = std::max(walked, w.damage);
            else single = std::max(single, w.damage);
            basic |= i == basic_;
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
    return strike.blow(steps ? steps->get(p) : unreachable);
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

std::array<Reach, 16>& reach_pool() {
    static std::array<Reach, 16> pool;
    return pool;
}

} // namespace

std::vector<Safety::CampHit>& Safety::member_pool() {
    static std::vector<CampHit> pool;
    return pool;
}

Safety::Safety(const World& world) : world_{world}, threats_{threat_pool()}, members_{member_pool()} {}

const std::vector<Safety::CampHit>& Safety::awake_members() {
    if (!members_known_) {
        members_known_ = true;
        members_.clear();
        camp_memo_[0].valid = camp_memo_[1].valid = false;
        // Each monster attacks the nearest champion within range, ties to the one acting first in
        // the round of the next camp phase.
        struct Other {
            vec2 pos;
            bool first;
        };
        union Others { // the first n only: the engine charges for every byte written
            std::array<Other, 2 * max_fighters> at;
            Others() {}
        } others;
        int n = -1;
        const int next = world_.round + 1, self_slot = world_.slot(world_.me(), next);
        static bitboard seen{cambc::uninitialized}, camps{cambc::uninitialized};
        bool reread = false;
        const auto& groups = world_.map().groups;
        world_.each_stirring([&](int g) {
            const auto& c = world_.camps[g];
            if (n < 0) {
                n = 0;
                for (const auto* side : {&world_.allies, &world_.enemies})
                    for (const auto& o : *side)
                        if (n < static_cast<int>(others.at.size()) && o.alive && o.visible && !o.is_self && !gone(o))
                            others.at[n++] = {o.pos, world_.slot(o, next) < self_slot};
                if (refresh_) {
                    reread = true;
                    cambc::vision::visible_tiles_into(seen);
                    cambc::vision::camp_tiles_into(camps);
                }
            }
            const float w = c.awake == Awake::awake ? 1.0f : unknown_camp_weight;
            // Only others this near a group's box can bring a member's reach below camp_attack_range:
            // a big group leaves out the rest.
            const Others* near = &others;
            int k_near = n;
            Others kept;
            if (groups[g].members.size() >= 8) {
                const auto& box = member_boxes(world_.map())[static_cast<std::size_t>(g)];
                near = &kept;
                k_near = 0;
                for (int k = 0; k < n; ++k) {
                    const vec2 o = others.at[k].pos;
                    const int out = std::max({box[0] - o.x, o.x - box[1], box[2] - o.y, o.y - box[3], 0});
                    if (out - (others.at[k].first ? 1 : 0) < camp_attack_range) kept.at[k_near++] = others.at[k];
                }
            }
            for (std::size_t i = 0; i < groups[g].members.size(); ++i) {
                const auto& m = groups[g].members[i];
                if (c.health[i] <= 0 || m.strength <= 0 || (reread && seen.is_set(m.pos) && !camps.is_set(m.pos))) continue;
                int reach = camp_attack_range;
                for (int k = 0; k < k_near; ++k)
                    reach = std::min(reach, dist(near->at[k].pos, m.pos) - (near->at[k].first ? 1 : 0));
                if (reach >= 0) members_.push_back({m.pos, m.strength, w, reach});
            }
        });
    }
    return members_;
}

bool Safety::gone(const ChampionBelief& c) {
    if (!refresh_ || c.side != team::enemy || !c.visible || c.index >= static_cast<int>(gone_.size())) return false;
    auto& known = gone_[static_cast<std::size_t>(c.index)];
    if (known == 0) {
        std::int32_t alive{};
        cambc::detail::check(cambc::detail::sdk_champion_is_alive(static_cast<std::uint32_t>(c.handle), &alive));
        known = alive != 0 ? 1 : 2;
    }
    return known == 2;
}

void Safety::invalidate() {
    built_ = false;
    refresh_ = true;
    reached_ = 0;
    build_cost_ = 0;
    threat_count_ = 0;
    threat_mask_ = 0;
    members_known_ = false;
    camp_area_.reset();
    enemy_area_.reset();
    fight_count_ = 0;
    gone_.fill(0);
    reaches_for_ = -1;
}

void Safety::refresh() {
    refresh_ = true;
    gone_.fill(0);
    build_cost_ = 0;
    reaches_for_ = -1;
    if (!built_ && !members_known_) return;
    bool changed = false;
    for (const auto& e : world_.enemies) changed |= e.alive && gone(e);
    if (!changed && members_known_ && !members_.empty()) {
        static bitboard seen{cambc::uninitialized}, camps{cambc::uninitialized};
        cambc::vision::visible_tiles_into(seen);
        cambc::vision::camp_tiles_into(camps);
        for (std::size_t i = 0; i < members_.size() && !changed; ++i) changed = seen.is_set(members_[i].pos) && !camps.is_set(members_[i].pos);
    }
    if (changed) invalidate();
}

Safety::Foe& Safety::struck(const ChampionBelief& e) {
    auto& x = foes_[static_cast<std::size_t>(e.index)];
    if (!(known_ >> e.index & 1)) {
        known_ |= static_cast<std::uint16_t>(1u << e.index);
        x.strike = threat_strike(world_, e);
        x.asked = {-1, -1};
    }
    return x;
}

Safety::Foe& Safety::foe(const ChampionBelief& e) {
    auto& x = struck(e);
    if (!(counted_ >> e.index & 1)) {
        counted_ |= static_cast<std::uint16_t>(1u << e.index);
        x.tiles = 0;
        x.weight = 0;
        if (!e.visible && x.strike.reach >= 0) {
            x.tiles = static_cast<int>(e.possible.count());
            x.weight = unseen_weight(x.strike.reach, x.tiles);
        }
    }
    return x;
}

namespace {

Threat& next_threat(std::vector<Threat>& pool, int& count) {
    if (count == static_cast<int>(pool.size())) pool.emplace_back();
    return pool[static_cast<std::size_t>(count++)];
}

} // namespace

void Safety::build() {
    world_.throw_if_stale();
    if (built_) return;
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
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked) || gone(e)) continue;
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
        t.area.clear();
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
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked) || gone(e)) continue;
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

const Reach& Safety::reach_of(const ChampionBelief& e) {
    auto& r = reach_pool()[static_cast<std::size_t>(e.index)];
    if (!(reached_ >> e.index & 1)) {
        reached_ |= static_cast<std::uint16_t>(1u << e.index);
        r.build(world_, e, next_turn_round(world_, e), turns_before_ours(world_, e) >= 2);
    }
    return r;
}

Blow Safety::blow(const ChampionBelief& e, vec2 p) {
    const auto& s = struck(e).strike;
    if (s.reach < 0 || dist(p, e.pos) > s.reach) return {};
    return reach_of(e).at(p);
}

int Safety::approach(const ChampionBelief& e, vec2 p) {
    const int reach = struck(e).strike.reach;
    return blow(e, p).hits ? 0 : std::max(1, dist(p, e.pos) - reach);
}

int Safety::threats_at(vec2 p, std::array<ThreatAt, 16>& out) {
    int n = 0;
    if (built_) {
        for (const auto& t : threats())
            if (n < static_cast<int>(out.size())) out[n++] = {t.enemy, t.at(p)};
        return n;
    }
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked) || gone(e) || n == static_cast<int>(out.size())) continue;
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

bool Safety::any_threat() {
    if (built_) return threat_count_ > 0;
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked) || gone(e)) continue;
        const auto& x = foe(e);
        if (x.strike.reach >= 0 && (e.visible || x.weight > 0)) return true;
    }
    return false;
}

float Safety::damage_bound(vec2 p, bool double_unacted) {
    float total = camp_damage(p);
    each_threat(p, [&](const ChampionBelief& e, const Blow& b) {
        total += b.damage * (double_unacted && e.visible && !e.acted ? 2.0f : 1.0f);
    });
    return total;
}

float Safety::damage_ceiling(vec2 p, bool double_unacted) {
    float total = camp_damage(p);
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked) || gone(e)) continue;
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

float Safety::chance_in_reach(const Threat& t, vec2 p) {
    if (t.visible) return t.at(p).hits ? 1.0f : 0.0f;
    if (!t.area.is_set(p)) return 0.0f;
    const auto& possible = world_.enemies[t.enemy].possible;
    const auto near = count_within(possible, p, t.strike.reach);
    return std::min(1.0f, static_cast<float>(near) / static_cast<float>(t.tiles));
}

float Safety::camp_damage(vec2 p, bool worst) {
    const auto& members = awake_members();
    if (members.empty()) return 0;
    auto& memo = camp_memo_[worst ? 1 : 0];
    if (memo.valid && memo.p == p) return memo.damage;
    float total = 0;
    for (const auto& m : members)
        if (dist(p, m.pos) <= m.reach) total += worst ? m.strength : m.strength * m.weight;
    memo = {p, total, true};
    return total;
}

float Safety::worst_damage(vec2 p) {
    float total = camp_damage(p, true);
    for (const auto& t : threats())
        total += t.at(p).damage;
    return total;
}

float Safety::expected_damage(vec2 p) {
    float total = camp_damage(p, false);
    for (const auto& t : threats())
        if (const auto b = t.at(p); b.hits) total += chance_in_reach(t, p) * hit_given_reach * b.damage;
    return total;
}

// The chance of being hit only grows with each factor, so the answer is settled as soon as it
// reaches the line: often by a camp, before the threats are built.
bool Safety::threatened(vec2 p) {
    float safe = 1;
    for (const auto& m : awake_members())
        if (dist(p, m.pos) <= m.reach && 1 - (safe *= 1 - m.weight) >= recall_risk) return true;
    if (!built_ && !may_be_hit(p)) return false;
    for (const auto& t : threats())
        if (t.at(p).hits && 1 - (safe *= 1 - chance_in_reach(t, p) * hit_given_reach) >= recall_risk)
            return true;
    return false;
}

const bitboard& Safety::camp_area() {
    if (!camp_area_) {
        bitboard b;
        for (const auto& m : awake_members())
            if (m.reach > 0) b.draw_chebyshev(m.pos, static_cast<float>(m.reach));
        camp_area_ = std::move(b);
    }
    return *camp_area_;
}

const bitboard& Safety::enemy_area() {
    if (!enemy_area_) {
        bitboard any;
        // A visible threat's: a superset, as a walls field per enemy each turn would cost ~3k.
        for (const auto& t : threats())
            if (!t.visible) any |= t.area;
            else if (const int r = reach_of(*t.belief).reach(); r >= 0) any.draw_chebyshev(t.pos, static_cast<float>(r));
        enemy_area_ = std::move(any);
    }
    return *enemy_area_;
}

bitboard Safety::avoid() { return camp_area() | enemy_area(); }

// Every unseen threat is credible: unseen_weight() drops the rest. Its area is `possible` grown by
// its radius, so it comes within r of p exactly when `possible` comes within radius + r.
bool Safety::avoid_within(vec2 p, int r) {
    for (const auto& m : awake_members())
        if (m.reach > 0 && dist(p, m.pos) <= m.reach + r) return true;
    if (built_) return any_within(enemy_area(), p, r);
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked) || gone(e)) continue;
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

std::uint32_t Safety::fight_key(vec2 p, int exclude) {
    std::uint32_t key = 0;
    bool hit = false;
    for (const auto& t : threats()) {
        if (t.enemy == exclude || !t.at(p).hits) continue;
        hit = true;
        key |= 1u << (16 + t.enemy);
    }
    if (!hit) return no_fight;
    for (std::size_t i = 0; i < world_.allies.size(); ++i)
        if (fights_with(world_.allies[i], p)) key |= 1u << i;
    return key;
}

std::uint32_t Safety::fight_key_with(vec2 p, std::uint32_t visible) {
    std::uint32_t key = visible;
    for (const auto& t : threats())
        if (!t.visible && t.at(p).hits) key |= 1u << (16 + t.enemy);
    for (std::size_t i = 0; i < world_.allies.size(); ++i)
        if (fights_with(world_.allies[i], p)) key |= 1u << i;
    return key;
}

const Trade* Safety::memo(std::uint32_t key) const {
    for (int i = 0; i < std::min(fight_count_, max_fights); ++i)
        if (fights_[i].key == key) return &fights_[i].trade;
    return nullptr;
}

const Trade* Safety::known_fight(vec2 p) {
    const auto key = fight_key(p, -1);
    if (key == no_fight) {
        static const Trade none{};
        return &none;
    }
    return memo(key);
}

Trade Safety::fight(vec2 p, int exclude) {
    world_.throw_if_stale();
    const auto key = fight_key(p, exclude);
    return key == no_fight ? Trade{} : fight_of(key);
}

Trade Safety::fight_of(std::uint32_t key) {
    if (const auto* t = memo(key)) return *t;
    Side us, them;
    for (unsigned left = key & 0xFFFFu; left; left &= left - 1) {
        const auto& a = world_.allies[static_cast<std::size_t>(std::countr_zero(left))];
        if (a.is_self) us.self = us.count;
        us.add(fighter(world_, a, made_));
    }
    build();
    for (unsigned left = key >> 16 & threat_mask_; left; left &= left - 1)
        them.add(fighter(world_, world_.enemies[static_cast<std::size_t>(std::countr_zero(left))], made_));
    const auto before = fuel();
    auto& slot = fights_[fight_count_++ % max_fights];
    slot = {key, trade(us, them, end_reserve)};
    if (const auto after = fuel(); after < before) costliest_fight_ = std::max(costliest_fight_, before - after);
    return slot.trade;
}

std::uint64_t Safety::fight_cost_estimate() {
    if (champions_ < 0) {
        champions_ = 0;
        for (const auto& a : world_.allies) champions_ += a.alive && (a.is_self || a.visible);
        for (const auto& e : world_.enemies) champions_ += e.alive && e.visible;
    }
    const auto champions = static_cast<std::uint64_t>(champions_);
    const auto simulation = std::max({std::uint64_t{10000}, 2000 + 2000 * champions, costliest_fight_ + costliest_fight_ / 4});
    return simulation + query_cost_estimate();
}

std::uint64_t Safety::query_cost_estimate() {
    // Once listed, a visible threat's Reach is still built on its first query.
    if (built_ && reaches_for_ != reached_) {
        reaches_for_ = reached_;
        reaches_ = 0;
        for (const auto& e : world_.enemies)
            if (e.alive && e.visible && !(reached_ >> e.index & 1) && !gone(e) && struck(e).strike.reach >= 0) reaches_ += 2000;
    }
    return (built_ ? reaches_ : 0) + build_cost_estimate();
}

std::uint64_t Safety::build_cost_estimate() {
    if (built_) return 0;
    if (build_cost_) return build_cost_;
    std::uint64_t cost = 2000;
    for (const auto& e : world_.enemies) {
        if (!e.alive || (!e.visible && !e.tracked) || gone(e)) continue;
        if (e.visible) cost += 4000; // with its Reach
        else cost += foe(e).weight > 0 ? (costliest_unseen() ? costliest_unseen() + costliest_unseen() / 4 : 3000 + 25 * search_chunks()) : 500;
    }
    build_cost_ = cost;
    return cost;
}

Trade Safety::pursuit(vec2 p, int approach) {
    world_.throw_if_stale();
    Side us, them;
    const auto& spawn = world_.map().near_enemy_spawn;
    for (const auto& e : world_.enemies) {
        if (!e.alive || !e.visible || gone(e) || spawn.is_set(e.pos)) continue;
        const auto& s = struck(e).strike;
        if (s.reach < 0 || dist(p, e.pos) - s.reach > approach) continue;
        const int walk = this->approach(e, p);
        if (walk > approach) continue;
        const int k = them.count;
        them.add(fighter(world_, e, made_));
        if (them.count > k && walk != 0) them.fighters[k].arrives_at = walk, them.plain = false;
    }
    if (them.count == 0) return {};
    join_allies(world_, us, p, made_);
    us.camp = camp_damage(p, false);
    return trade(us, them, end_reserve, false);
}

int Safety::turns_to_kill_idle(vec2 p, int horizon) {
    Side us, them;
    us.add(fighter(world_, world_.me(), made_));
    us.fighters[0].arrives_at = never;
    us.plain = false;
    us.camp = camp_damage(p, false);
    for (const auto& e : world_.enemies) {
        if (!e.alive || !e.visible || gone(e)) continue;
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
    const float health = world_.me().health;
    // Most turns no enemy is near enough; skip the threat build then.
    if (!built_ && (damage_ceiling(p) < health || damage_bound(p) < health)) return false;
    return worst_damage(p) >= health;
}

} // namespace aph
