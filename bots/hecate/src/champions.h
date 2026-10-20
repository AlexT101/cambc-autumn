// Transcribed from cambc-rules.yaml.
#pragma once
#include <cambc.h>
#include <array>
#include <cstdint>

namespace aph {

enum class AbilityKind : std::uint8_t {
    none,
    attack_reset, // restores a spent basic attack (never the walk); fails while the attack is unspent
    damage,       // multiplier x Focus damage, maybe with a stun
    stun,         // stun with no damage (Cassi)
    dash,         // move to a free tile by up to 2 king steps; crosses holes, altars and champions
    heal,         // multiplier x Focus heal on another ally
    shield,       // multiplier x Focus shield on self for `duration` turn ends
};

enum class Targeting : std::uint8_t {
    self,
    unit,   // a visible enemy champion or camp within range 4
    ground, // any tile within range 4; the 3x3 around it hits enemy champions (even unseen) and camps
    ally,   // another allied champion within range 4
};

enum class Passive : std::uint8_t {
    none,
    health_strength,   // Ryth: +1% of bonus max health as Strength
    bonus_gold,        // Vesper Vale: +33% gold
    gem_focus,         // Prism: +1 Focus per carried gem
    reset_on_kill,     // Vendetta: killing a champion or monster readies both abilities
    stun_immune,       // Marcella; also 2 gold per gem she tributes
    remote_shop,       // Tavi: buys shards anywhere, sells at full price on spawn
    retaliation,       // Ren: 0.2 x Focus back to whoever damages it, monsters included
    splash_attack,     // Varg: basic attacks also hit other enemies within 1 of the target
    linked_pair,       // Cassi and Issac: if either dies, both die
    missing_health,    // Heart of Ruin: up to +50% damage as health falls
};

inline constexpr float retaliation_share = cambc::constants::passive_abilities::ren_retaliation_focus_ratio; // of Ren's Focus, per hit taken

struct Stat {
    float base, growth; // growth is per shard
    constexpr float at(int shards) const { return base + growth * static_cast<float>(shards); }
};

struct AbilityFacts {
    AbilityKind kind = AbilityKind::none;
    Targeting target = Targeting::self;
    float multiplier = 0;          // x Focus, for damage, heal and shield
    bool stuns = false;            // stuns its target(s); for Marcella's reset, her next basic attack stuns
    bool excludes_walking = false; // cannot be cast after walking; walking is forbidden after it
    int duration = 0;              // shield turn ends

    constexpr int range() const {
        switch (kind) {
        case AbilityKind::none:
        case AbilityKind::attack_reset: return 0;
        case AbilityKind::dash: return 2;
        default: return target == Targeting::self ? 0 : 4;
        }
    }
    // Farthest tile from the caster this ability can affect (a ground cast hits a 3x3 area).
    constexpr int reach() const { return range() + (target == Targeting::ground ? 1 : 0); }
    constexpr bool hits_enemies() const {
        return kind == AbilityKind::damage || kind == AbilityKind::stun;
    }
};

struct ChampionFacts {
    cambc::champion_type type;
    const char* name;
    bool ranged;
    Stat health, strength, focus;
    Passive passive;
    std::array<AbilityFacts, 2> abilities;

    constexpr int attack_range() const { return ranged ? 3 : 1; }
    constexpr bool walk_and_attack_independent() const { return !ranged; }

    constexpr bool has(AbilityKind kind) const {
        return abilities[0].kind == kind || abilities[1].kind == kind;
    }
    constexpr bool has_dash() const { return has(AbilityKind::dash); }
    constexpr bool has_attack_reset() const { return has(AbilityKind::attack_reset); }
    constexpr int slot_of(AbilityKind kind) const {
        for (int s = 0; s < 2; ++s)
            if (abilities[s].kind == kind) return s;
        return -1;
    }
    // Farthest tile from which this slot can stun something this turn (the basic attack for
    // Marcella); -1 if it never stuns.
    constexpr int stun_reach(int slot) const {
        const auto& a = abilities[slot];
        if (!a.stuns) return -1;
        return a.kind == AbilityKind::attack_reset ? attack_range() : a.reach();
    }
};

namespace facts_detail {
using K = AbilityKind;
using T = Targeting;
inline constexpr AbilityFacts reset{K::attack_reset, T::self};
inline constexpr AbilityFacts dash{K::dash, T::self};
constexpr AbilityFacts damage(T target, float mult, bool stuns = false) { return {K::damage, target, mult, stuns, true}; }
} // namespace facts_detail

// Indexed by cambc::champion_type.
inline constexpr std::array<ChampionFacts, 13> champion_table = [] {
    using namespace facts_detail;
    using C = cambc::champion_type;
    using P = Passive;
    return std::array<ChampionFacts, 13>{{
        {C::ryth, "ryth", false, {1200, 100}, {45, 5}, {100, 10}, P::health_strength,
         {damage(T::ground, 1, true), reset}},
        {C::vesper_vale, "vesper_vale", true, {900, 100}, {50, 5}, {100, 10}, P::bonus_gold, {reset, dash}},
        {C::vendetta, "vendetta", false, {800, 100}, {70, 6}, {100, 10}, P::reset_on_kill, {reset, dash}},
        {C::cassi, "cassi", true, {600, 65}, {30, 3}, {70, 13}, P::linked_pair,
         {damage(T::unit, 2), AbilityFacts{K::stun, T::unit, 0, true, false}}},
        {C::issac, "issac", false, {900, 80}, {40, 3}, {100, 10}, P::linked_pair, {reset, dash}},
        {C::stellar, "stellar", true, {750, 75}, {30, 3.5f}, {85, 9}, P::none,
         {damage(T::unit, 2), damage(T::ground, 1.4f)}},
        {C::prism, "prism", true, {700, 60}, {35, 2.5f}, {80, 8}, P::gem_focus,
         {damage(T::unit, 1.5f, true), damage(T::ground, 1)}},
        {C::marcella, "marcella", false, {1200, 100}, {45, 5}, {60, 15}, P::stun_immune,
         {AbilityFacts{K::attack_reset, T::self, 0, true}, damage(T::unit, 2)}},
        {C::willow, "willow", true, {700, 50}, {55, 3}, {120, 5}, P::none,
         {AbilityFacts{K::heal, T::ally, 3}, reset}},
        {C::ren, "ren", false, {900, 100}, {35, 5}, {100, 9}, P::retaliation,
         {damage(T::unit, 1.25f, true), dash}},
        {C::varg, "varg", false, {1000, 100}, {40, 5}, {100, 10}, P::splash_attack,
         {reset, AbilityFacts{K::shield, T::self, 2.5f, false, false, 5}}},
        {C::tavi, "tavi", true, {750, 75}, {45, 5}, {100, 10}, P::remote_shop,
         {reset, damage(T::unit, 1.4f, true)}},
        {C::heart_of_ruin, "heart_of_ruin", false, {1000, 100}, {40, 5}, {100, 15}, P::missing_health,
         {AbilityFacts{K::shield, T::self, 1.5f, false, false, 5}, dash}},
    }};
}();

constexpr const ChampionFacts& facts(cambc::champion_type type) {
    return champion_table[static_cast<std::size_t>(type)];
}

} // namespace aph
