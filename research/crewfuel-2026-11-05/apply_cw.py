"""crew_work: the crew table's claimers when it is read (or an operation will read it), else one pass over the allies."""
from pathlib import Path

p = Path(__file__).resolve().parents[2] / "bots/astraeus/src/economy/farm.cc"
s = p.read_text()
old = """    const auto crew_work = [&](const CrewAllies& allies, int g, int working, int waiting) __attribute__((always_inline)) {
        CrewWork total;
        for (int k = 0; k < allies.n_claiming; ++k) {
            const auto& x = allies.at[allies.claiming[static_cast<std::size_t>(k)]];
            if (x.claim != g) continue;
            const auto& a = *x.a;
            const float output = crew_output(x);
            total.output += output;
            if (working == 0) continue; // no rounds of ours for its delay to take
            const auto arrival = work_arrival(a, g);
            // Age the work round from the observation, never a guessed hidden position or turn order.
            const int delay = arrival.delay(world.round, waiting);
            total.delayed_damage += output * static_cast<float>(std::min(working, delay));
        }
        return total;
    };"""
new = """    // From the crew table's claimers (`allies`), or without one from the allies themselves: a table
    // costs more to read than one pass, so a group no plan prices does not read it.
    const auto crew_work = [&](const CrewAllies* allies, int g, int working, int waiting) __attribute__((always_inline)) {
        CrewWork total;
        const auto add = [&](const ChampionBelief& a, float output) __attribute__((always_inline)) {
            total.output += output;
            if (working == 0) return; // no rounds of ours for its delay to take
            const auto arrival = work_arrival(a, g);
            // Age the work round from the observation, never a guessed hidden position or turn order.
            const int delay = arrival.delay(world.round, waiting);
            total.delayed_damage += output * static_cast<float>(std::min(working, delay));
        };
        if (!allies) {
            for (const auto& a : world.allies)
                if (!a.is_self && a.alive && comms::claim_of(world, a.index) == g) add(a, camp_output(a));
            return total;
        }
        for (int k = 0; k < allies->n_claiming; ++k)
            if (const auto& x = allies->at[allies->claiming[static_cast<std::size_t>(k)]]; x.claim == g) add(*x.a, crew_output(x));
        return total;
    };"""
assert old in s
s = s.replace(old, new)
old = """            const auto crew = crew_work(crew_allies_now(), g, working, waiting);"""
assert old in s
s = s.replace(old, """            const auto crew = crew_work(op || crew_read ? &crew_allies_now() : nullptr, g, working, waiting);""")
p.write_text(s)
