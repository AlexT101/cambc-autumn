#!/usr/bin/env python3
"""Turn a copy of the teammate's macro2-heavy source (506 + team clears of Golem and Monolith groups) into a
Golem-only arm: Monolith groups keep 506's farm_monolith behaviour, and a Golem group is a team clear only when
its gem clusters pay at least RATIO times its strikers' gems (0: every Golem group).

    mkarm.py bots/variants/bg-golem 0      # every Golem group
    mkarm.py bots/variants/bg-rich 1       # clusters pay at least as much as the strikers
"""
import sys, pathlib
bot, ratio = pathlib.Path(sys.argv[1]), sys.argv[2]
def sub(path, old, new, count=1):
    p = bot / 'src' / path
    s = p.read_text()
    assert s.count(old) == count, (path, old[:60], s.count(old))
    p.write_text(s.replace(old, new))
sub('params.h', "inline constexpr int heavy_clear_rounds = siege_rounds;",
    "inline constexpr int heavy_clear_rounds = siege_rounds;\n"
    "// A Golem group is a team clear only when its gem clusters pay at least this many times its strikers' gems:\n"
    "// below that one clear pays about what its champion-rounds earn at solo camps, and the gathering decides.\n"
    f"inline constexpr int heavy_rich_ratio = {ratio};")
sub('economy/crew.cc', "    return G.has_monolith ? !map.monolith_only : !(map.shared_gems && big_group(G));",
    "    // Monoliths stay farm_monolith's, as they were.\n"
    "    if (G.has_monolith) return false;\n"
    "    return !(map.shared_gems && big_group(G)) && G.cluster_gems >= params::heavy_rich_ratio * (G.gems - G.cluster_gems);")
sub('economy/farm.cc', "        if (c.state != CampState::alive) memory.mono_staged = -1;\n        else if (memory.mono_staged == -2 && c.awake == Awake::asleep) {",
    "        if (groups[g].has_monolith) {\n        } else if (c.state != CampState::alive) memory.mono_staged = -1;\n        else if (memory.mono_staged == -2 && c.awake == Awake::asleep) {")
sub('economy/farm.cc', "        if (c.state != CampState::alive || c.awake == Awake::awake || (memory.mono_group == g && memory.mono_staged == -2)) return true;",
    "        if (c.state != CampState::alive || c.awake == Awake::awake || (memory.mono_group == g && memory.mono_staged == -2 && !groups[g].has_monolith)) return true;")
sub('economy/farm.cc', "        return staged >= params::mono_gather_share * output;\n    };",
    "        if (staged >= params::mono_gather_share * output) return true;\n"
    "        return G.has_monolith && memory.mono_group == g && memory.mono_staged >= 0 && world.round - memory.mono_staged >= params::mono_max_wait;\n    };")
sub('economy/farm.cc', "        if (!(memory.mono_group == g && memory.mono_staged >= 0 && round - memory.mono_staged >= params::mono_max_wait && round >= memory.mono_ready))",
    "        if (groups[g].has_monolith || !(memory.mono_group == g && memory.mono_staged >= 0 && round - memory.mono_staged >= params::mono_max_wait && round >= memory.mono_ready))")
sub('economy/farm.cc', "            if (farm_heavy(world, g)) return true;\n        return false;\n    }();",
    "            if (farm_monolith(world, g) || farm_heavy(world, g)) return true;\n        return false;\n    }();")
sub('bot.cc', "        memory.mono_staged = -1, memory.mono_ready = -1; // a heavy operation's gather is planned afresh",
    "        if (memory.mono_group >= 0 && !world.map().groups[memory.mono_group].has_monolith)\n"
    "            memory.mono_staged = -1, memory.mono_ready = -1; // a Golem operation's gather is planned afresh")
print('ok', bot, ratio)
