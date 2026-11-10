#include "champions.h"
#include <bit>
#include <cstdio>
#include <random>

int main() {
    std::mt19937 random(1001);
    std::uniform_real_distribution<float> stat(0, 1000000);
    unsigned checks = 0;
    for (const auto& f : aph::champion_table) {
        for (int i = 0; i < 100000; ++i) {
            const float strength = i == 0 ? 0 : stat(random), focus = i == 0 ? 0 : stat(random);
            float old = strength;
            for (const auto& a : f.abilities) {
                if (a.kind == aph::AbilityKind::damage || a.lands()) old += a.multiplier * focus / static_cast<float>(aph::ability_cooldown);
                if (a.kind == aph::AbilityKind::attack_reset) old += strength / static_cast<float>(aph::ability_cooldown);
            }
            if (std::bit_cast<unsigned>(old) != std::bit_cast<unsigned>(f.raw_output(strength, focus))) return 1;
            ++checks;
        }
    }
    std::printf("%u bit-identical output calculations, all 13 champion bodies\n", checks);
}
