"""Drop the team pre-bound from the may_beat block (it cost more than it saved)."""
from pathlib import Path

root = Path(__file__).resolve().parents[2] / "bots/astraeus/src"
p = root / "economy/farm.cc"
s = p.read_text()
old = """            bool may_beat = true;
            // The bound below over every crew the team could make (k in [1, team / S]): one that loses
            // to the alone value, or with no altar cycle to beat to the best, needs no reading of who
            // claims or is free.
            const bool altar_way = banks_bag && walk_out != unreachable;
            if (worth > 0 && g != memory.mono_group) {
                const float team = crew_team_output(crew_allies_now(), strength) / strength;
                const float most = (wins ? rate(world, worth, trip + cap_rounds + fastest / team) : crew_rate(world, worth, trip + cap_rounds, fastest, 1.0f, team))
                                   * (memory.claim == g ? crew_hold(g) : 1.0f) * 1.0001f;
                if (most < value || (!altar_way && ((best >= 0 && most < best_value) || most < floor_value))) may_beat = false;
            }
            if (may_beat && worth > 0 && g != memory.mono_group) {"""
assert old in s
s = s.replace(old, """            bool may_beat = true;
            if (worth > 0 && g != memory.mono_group) {""")
old = """                if (!may_beat && most >= value && altar_way) {"""
assert old in s
s = s.replace(old, """                if (!may_beat && most >= value && banks_bag && walk_out != unreachable) {""")
p.write_text(s)
h = root / "bot_parts.h"
t = h.read_text()
old = """    mutable std::uint32_t avail_bits = 0;
    mutable float team = -1; // crew_team_output's sum, -1 until read
};"""
assert old in t
t = t.replace(old, """    mutable std::uint32_t avail_bits = 0;
};""")
old = """
// `mine` plus every living ally's camp output, in ally order: no crew's sum exceeds it.
float crew_team_output(const CrewAllies& allies, float mine);"""
assert old in t
t = t.replace(old, "")
h.write_text(t)
c = root / "economy/crew.cc"
u = c.read_text()
a = u.index("float crew_team_output(")
b = u.index("std::uint32_t crew_available_bits(const World& world, const CrewAllies& allies, int g) {")
u = u[:a] + u[b:]
old = """    out.n_joinable = -1, out.avail_group = -1, out.team = -1;"""
assert old in u
u = u.replace(old, """    out.n_joinable = -1, out.avail_group = -1;""")
c.write_text(u)
