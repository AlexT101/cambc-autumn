"""The step guard's gates as a staged test: python3 mksg.py SRC AFTER [--entry-sim]

AFTER: the fuel kept for the rest of the turn after the guard (was act_reserve, 20k, plus at the entry a fight's
estimate and the costliest placing lately). The entry keeps AFTER and an exact look's price a foe; each new fight keeps
its own estimate and AFTER; the looks keep AFTER and their own price. --entry-sim: the entry also keeps one fight's
estimate unless the union fight is known (not implemented: the union is not known before the exposures)."""
import sys
from pathlib import Path

src = Path(sys.argv[1]); after = int(sys.argv[2])
p = src / 'combat/guard.cc'
s = p.read_text()
subs = [
    ('''    const auto floor = safety.fight_cost_estimate() + act_reserve;
    if (!fuel_ok(floor + costliest)) {''', f'''    // What the turn spends after its step guard (the walk's search, the turn's end): measured, see guard_after.
    const std::uint64_t floor = guard_after;
    if (!fuel_ok(floor + 1000 * static_cast<std::uint64_t>(n))) {{'''),
    ('''        if (!known && !fuel_ok(safety.fight_cost_estimate() + act_reserve)) {''', '''        if (!known && !fuel_ok(safety.fight_cost_estimate() + floor)) {'''),
    ('''const bitboard* step_guard(const World& world, Safety& safety, vec2 here, int radius) {''', f'''inline constexpr std::uint64_t guard_after = {after};
const bitboard* step_guard(const World& world, Safety& safety, vec2 here, int radius) {{'''),
]
for a, b in subs:
    assert s.count(a) == 1, a
    s = s.replace(a, b)
p.write_text(s)
print('step guard staged, after', after)
