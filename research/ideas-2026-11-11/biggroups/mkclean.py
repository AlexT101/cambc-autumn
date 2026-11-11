#!/usr/bin/env python3
"""bg-rich -> bg-clean: a Golem team clear is launched only clean (the planned crew absorbs the clear's hits in its
spare health, with no trip home); with no clean crew the group is priced as 506 prices it (near allies' crew).
    mkclean.py bots/variants/bg-clean"""
import sys, pathlib
bot = pathlib.Path(sys.argv[1])
def sub(path, old, new):
    p = bot / 'src' / path; s = p.read_text()
    assert s.count(old) == 1, (path, old[:60], s.count(old))
    p.write_text(s.replace(old, new))
sub('economy/crew.cc', "        share_damage(members.data(), k + 1, p);\n",
    "        share_damage(members.data(), k + 1, p);\n"
    "        // Launched only clean: the hits fit the crew's spare health and send nobody home. Mite's and Fish's\n"
    "        // clears that pay take ~22 rounds and no trip; ours launched short of that lost a champion in half.\n"
    "        if (!(under_way && k < at_work)) {\n"
    "            float spare = 0;\n"
    "            for (int j = 0; j <= k; ++j) spare += members[static_cast<std::size_t>(j)]->budget * params::crew_trip_risk;\n"
    "            if (p.trips > 0 || damage > spare) continue;\n"
    "        }\n")
sub('economy/farm.cc', "                if (!h.plan.me) continue;\n",
    "                if (h.plan.n > 1) {\n                if (!h.plan.me) continue;\n")
sub('economy/farm.cc', "                shared_priced = {'J', h.trips, -1, h.plan.expected, h.plan.output, h.damage, h.plan.start, h.plan.rounds};\n                continue;\n",
    "                shared_priced = {'J', h.trips, -1, h.plan.expected, h.plan.output, h.damage, h.plan.start, h.plan.rounds};\n                continue;\n                }\n")
sub('economy/farm.cc', "        if (crewable && heavy(g)) {\n",
    "        bool team_priced = false; // a clean team plan exists: else the near allies' crew, as before\n        if (crewable && heavy(g)) {\n")
sub('economy/farm.cc', "            const auto h = heavy_share(g, steps, reach, trip, budget);\n            // A crew planned without us",
    "            const auto h = heavy_share(g, steps, reach, trip, budget);\n            team_priced = h.plan.n > 1;\n            // A crew planned without us")
sub('economy/farm.cc', "        } else if (crewable) {\n", "        }\n        if (crewable && !team_priced) {\n")
print('ok')
