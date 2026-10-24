#!/usr/bin/env python3
"""Generate and run a host fixture from source-hash-pinned production helpers."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "provenance/willow-astraeus-clock-recovery-20261024-v1/workspace/bots/willow-phased-solo-boss-4d08241-work/src"
PINS = {
    "phased_boss.inc": "d9c37f469613807dbaf355136152dd30c7a7d3ef30937b2dba0e597385331531",
    "champions.h": "2ef629ef356748dedff8180d848e98ffb489851f597a43c17e4a3a269c737103",
}


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    for name, expected in PINS.items():
        actual = sha(SRC / name)
        if actual != expected:
            raise SystemExit(f"source pin mismatch for {name}: {actual}")

    champions = (SRC / "champions.h").read_text()
    row = """{false, {1200, 100}, {45, 5}, {60, 15}, P::stun_immune,
         {AbilityFacts{K::attack_reset, T::self, 0, true}, damage(T::unit, 2)}},"""
    if row not in champions:
        raise SystemExit("production Marcella ability row no longer matches fixture facts")

    production = (SRC / "phased_boss.inc").read_text()
    start = production.index("struct BossSortie {")
    end = production.index("bool boss_price_work(", start)
    extracted = production[start:end].rstrip()
    if "BossSortie boss_sortie(" not in extracted or "void boss_age_cooldowns(" not in extracted:
        raise SystemExit("failed to extract the expected unchanged production helper bodies")

    harness = r'''#include <algorithm>
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
'''
    footer = r'''
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
'''
    generated = OUT / "boss-sortie-fixture.generated.cpp"
    generated.write_text(harness + extracted + "\n" + footer)
    binary = OUT / "boss-sortie-fixture"
    compile_result = subprocess.run(
        ["c++", "-std=c++17", "-O0", "-Wall", "-Wextra", "-Werror", str(generated), "-o", str(binary)],
        text=True, capture_output=True,
    )
    if compile_result.returncode:
        print(compile_result.stdout, end="")
        print(compile_result.stderr, end="")
        return compile_result.returncode
    run_result = subprocess.run([str(binary)], text=True, capture_output=True)
    print(run_result.stdout, end="")
    print(run_result.stderr, end="")
    receipt = {
        "schema": "boss-production-helper-fixture/v1",
        "scope": "host C++ unchanged BossSortie and boss_age_cooldowns bodies; no SDK/runtime/native integration coverage",
        "source_pins": {name: sha(SRC / name) for name in PINS},
        "production_helper_sha256": hashlib.sha256(extracted.encode()).hexdigest(),
        "generated_cpp_sha256": sha(generated),
        "compiler_argv": ["c++", "-std=c++17", "-O0", "-Wall", "-Wextra", "-Werror"],
        "compile_exit_code": compile_result.returncode,
        "run_exit_code": run_result.returncode,
        "stdout": run_result.stdout,
        "stderr": run_result.stderr,
        "tested": [
            "explicit independent schedule: 28 stationary actions, reset 0/8/16/24, Damage 1/9/17/25",
            "production sortie result: 8736 boss HP left, 572 player HP, cooldowns [4,5]",
            "production cooldown aging over 8 ticks then 22-action moved return kill at 950 HP",
            "first moved action excludes unit Damage while stationary action may cast",
            "strict health == reserve + 1 rejects work",
        ],
        "limits": ["mock World/facts/items/strength/record accessors", "does not test boss_price_work, routing, job selection, actual SDK calls, WASM fuel, native transitions, capture or competitiveness"],
    }
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return run_result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
