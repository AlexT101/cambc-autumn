#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <iostream>

namespace aph {
enum class AbilityKind { attack_reset, damage };
enum class Targeting { self, unit };
struct AbilityFacts { AbilityKind kind; Targeting target; float multiplier; bool stuns; bool excludes_walking; };
struct ChampionFacts { AbilityFacts abilities[2]; };
inline constexpr int ability_cooldown = 8;
enum class Family { monster, jungle, durability };
inline constexpr Family monster = Family::monster;
struct Items { bool monster = true, jungle = true, durability = true; };
bool has_family(const Items& items, Family family) {
    if (family == Family::monster) return items.monster;
    if (family == Family::jungle) return items.jungle;
    return items.durability;
}
struct Record { float focus = 120; };
struct Unit { const ChampionFacts& facts() const; };
const ChampionFacts marcella_facts{{
    {AbilityKind::attack_reset, Targeting::self, 0, true, false},
    {AbilityKind::damage, Targeting::unit, 2, false, true},
}};
const ChampionFacts& Unit::facts() const { return marcella_facts; }
struct World { Unit me() const { return {}; } };
Items owned_items{};
float strength = 290;
Record record{};
const Items& my_items() { return owned_items; }
float my_strength() { return strength; }
const Record& my_record() { return record; }
struct BossSortie { float left, health; int turns = 0; std::array<int, 2> cd; };
BossSortie boss_sortie(const World& world, float hp, float health, float hit, float reserve,
                      std::array<int, 2> cd, bool moved, bool attack, bool cast) {
    BossSortie out{hp, health, 0, cd};
    const auto& f = world.me().facts();
    const float scale = has_family(my_items(), monster) ? 1.1f : 1.0f;
    const float basic = my_strength() * scale, focus = my_record().focus * scale;
    for (int t = 0; t < 128 && out.left > 0; ++t) {
        if (!(out.health > reserve + 1.0f)) break;
        const bool first = t == 0;
        const bool can_attack = !first || attack;
        const bool can_cast = !first || cast;
        float damage = can_attack ? basic : 0;
        int slot = -1;
        float added = 0;
        if (can_cast && out.left > damage)
            for (int s = 0; s < 2; ++s) {
                const auto& a = f.abilities[s];
                if (out.cd[s] > 0 || (first && moved && a.excludes_walking)) continue;
                const float extra = a.kind == AbilityKind::attack_reset ? (can_attack ? basic : 0)
                                    : a.kind == AbilityKind::damage && a.target == Targeting::unit ? a.multiplier * focus : 0;
                if (extra > added) slot = s, added = extra;
            }
        damage += added;
        if (slot >= 0) out.cd[slot] = ability_cooldown;
        out.left = std::max(0.0f, out.left - damage);
        ++out.turns;
        for (auto& cooldown : out.cd) cooldown = std::max(0, cooldown - 1);
        // Awake charging ignores deterministic reset stuns and sleeping entry savings.
        if (out.left > 0) out.health -= hit;
    }
    return out;
}

void boss_age_cooldowns(std::array<int, 2>& cd, int turns) {
    for (auto& n : cd) n = std::max(0, n - turns);
}

} // namespace aph

int main() {
    using namespace aph;
    const World world{};
    const float hit = 200.0f * 0.7f * 0.9f;
    const float reserve = hit * 5.0f;
    const float basic = my_strength() * 1.1f;
    const float damage_cast = my_record().focus * 1.1f * 2.0f;

    // Independent explicit legal activation schedule: reset at 0/8/16/24,
    // unit Damage at 1/9/17/25, and one basic every activation.
    const float scheduled = 28 * basic + 4 * basic + 4 * damage_cast;
    assert(std::abs(scheduled - 11264.0f) < 0.01f);

    const auto first = boss_sortie(world, 20000.0f, 4100.0f, hit, reserve,
                                   {0, 0}, false, true, true);
    assert(first.turns == 28);
    assert(std::abs(first.left - 8736.0f) < 0.01f);
    assert(std::abs(first.health - 572.0f) < 0.01f);
    assert(first.cd[0] == 4 && first.cd[1] == 5);

    auto return_cd = first.cd;
    boss_age_cooldowns(return_cd, 8);
    assert(return_cd[0] == 0 && return_cd[1] == 0);
    const float return_health = 4100.0f - 4.0f * hit;
    assert(std::abs(return_health - 3596.0f) < 0.01f);
    const auto second = boss_sortie(world, first.left, return_health, hit, reserve,
                                    return_cd, true, true, true);
    assert(second.turns == 22);
    assert(second.left == 0.0f);
    assert(std::abs(second.health - 950.0f) < 0.01f);

    // One affordable activation: a moving first action cannot use Marcella's
    // walking-excluded Damage cast; a stationary first action can.
    const auto moved_one = boss_sortie(world, 5000.0f, 757.0f, hit, reserve,
                                       {8, 0}, true, true, true);
    const auto still_one = boss_sortie(world, 5000.0f, 757.0f, hit, reserve,
                                       {8, 0}, false, true, true);
    assert(moved_one.turns == 1 && still_one.turns == 1);
    assert(std::abs(moved_one.left - (5000.0f - basic)) < 0.01f);
    assert(std::abs(still_one.left - (5000.0f - basic - damage_cast)) < 0.01f);

    // Strict escape boundary: health equal to reserve+1 is rejected before work.
    const auto boundary = boss_sortie(world, 5000.0f, reserve + 1.0f, hit, reserve,
                                      {0, 0}, false, true, true);
    assert(boundary.turns == 0 && boundary.left == 5000.0f);
    std::cout << "PASS: unchanged production BossSortie / boss_age_cooldowns; "
                 "28-turn first sortie, paid return, moved/stationary first-action boundary, escape reserve boundary\n";
}
