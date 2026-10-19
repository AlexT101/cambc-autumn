// probe-facts: hecate's champion table (bots/hecate/src/champions.h, transcribed from cambc-rules.yaml)
// against the engine's champion designs. On its first play turn it prints "facts mismatch <name>: ..."
// for each champion that differs, then "facts checked: N mismatches". Its draft picks are left random.
//   cambc run rules-verification/probes/probe-facts rules-verification/probes/probe-facts --map corners --rounds 1 -o <dir>
#include <cambc.h>
#include <cmath>
#include <cstdio>
#include <string>
#include <variant>
#include "../../../../bots/hecate/src/champions.h"

namespace aph {

namespace {

bool close(float a, float b) { return std::fabs(a - b) < 1e-3f; }

std::string compare_ability(const AbilityFacts& want, const cambc::ability& slot) {
    const auto& info = slot.info();
    if (!info) return want.kind == AbilityKind::none ? "" : "engine slot empty";
    return std::visit(
        [&](const auto& a) -> std::string {
            using A = std::decay_t<decltype(a)>;
            std::string why;
            if (a.exclusive_with_movement != want.excludes_walking) why += " excludes_walking";
            if (a.max_cooldown != 8) why += " cooldown=" + std::to_string(a.max_cooldown);
            if constexpr (std::is_same_v<A, cambc::ability_attack_reset>) {
                if (want.kind != AbilityKind::attack_reset || a.enhanced_attack != want.stuns) why += " kind/enhanced";
            } else if constexpr (std::is_same_v<A, cambc::ability_dash>) {
                if (want.kind != AbilityKind::dash || !close(a.range, 2)) why += " kind/range";
            } else if constexpr (std::is_same_v<A, cambc::ability_cc>) {
                if (!want.stuns || !close(a.modifier, want.multiplier) || !close(a.range, want.range()))
                    why += " cc modifier=" + std::to_string(a.modifier) + " range=" + std::to_string(a.range);
            } else if constexpr (std::is_same_v<A, cambc::ability_shield>) {
                // The engine gives the self-shield a range of 4; it only ever targets the caster.
                if (want.kind != AbilityKind::shield || !close(a.modifier, want.multiplier) || a.duration != want.duration)
                    why += " shield modifier=" + std::to_string(a.modifier) + " duration=" + std::to_string(a.duration);
            } else if constexpr (std::is_same_v<A, cambc::ability_aoe_damage>) {
                if (want.target != Targeting::ground || !close(a.modifier, want.multiplier) || a.radius != 1)
                    why += " aoe modifier=" + std::to_string(a.modifier) + " stun_duration=" + std::to_string(a.duration);
            } else {
                if (!close(a.modifier, want.multiplier) || !close(a.range, want.range()))
                    why += " modifier=" + std::to_string(a.modifier) + " range=" + std::to_string(a.range);
            }
            return why;
        },
        *info);
}

} // namespace

int check_facts() {
    int mismatches = 0;
    for (const auto& design : cambc::champion_designs) {
        const auto& f = facts(design.champion_name());
        const auto s = design.base_stats();
        std::string why;
        if (s.base_attack_range != f.attack_range()) why += " attack_range";
        if (!close(s.base_health, f.health.base) || !close(s.health_growth, f.health.growth)) why += " health";
        if (!close(s.base_strength, f.strength.base) || !close(s.strength_growth, f.strength.growth)) why += " strength";
        if (!close(s.base_focus, f.focus.base) || !close(s.focus_growth, f.focus.growth)) why += " focus";
        for (int slot = 0; slot < 2; ++slot) {
            const auto slot_why = compare_ability(f.abilities[slot], design.abilities()[slot]);
            if (!slot_why.empty()) why += " slot" + std::to_string(slot) + ":" + slot_why;
        }
        if (!why.empty()) {
            ++mismatches;
            std::printf("facts mismatch %s:%s\n", f.name, why.c_str());
        }
    }
    return mismatches;
}

} // namespace aph

int main() {
    bool checked = false;
    while (true) {
        if (!cambc::is_draft() && !checked) {
            checked = true;
            std::printf("facts checked: %d mismatches\n", aph::check_facts());
        }
        cambc::end_turn();
    }
}
