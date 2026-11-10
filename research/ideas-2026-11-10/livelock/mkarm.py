"""mkarm.py DIR DENY_BAG DENY_NEED: add the big-tribute deny to an oc-wdash-494 copy."""
import sys, re
d, bag, need = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
S = d + '/src/'
def sub(path, old, new):
    s = open(S + path).read(); assert s.count(old) == 1, (path, old[:60]); open(S + path, 'w').write(s.replace(old, new))
sub('params.h', "inline constexpr int brake_bag = 19;\n",
    "inline constexpr int brake_bag = 19;\n"
    "// A visible enemy tribute that does not end the game is stopped (lock or stun) from this bag, or from this share of\n"
    "// the gems they still need (0: off), by a body whose own bag is under max(40, its bag / 3) (fight.cc tribute_to_deny).\n"
    f"inline constexpr int deny_bag = {bag};\ninline constexpr float deny_need = {need}f;\n")
sub('bot_parts.h', "bool holds_hard_stop(const World& world, const ChampionBelief& e);\n",
    "bool holds_hard_stop(const World& world, const ChampionBelief& e);\nconst ChampionBelief* tribute_to_deny(const World& world);\n")
sub('combat/fight.cc', "// Into reach of the enemy whose bag ends the game, whatever the risk:",
"""// A visible enemy tribute too big to let land though it does not end the game (params::deny_bag, deny_need), that we
// hold a hard stop for and reach before it lands; none while our death would hand over max(40, its bag / 3). Without
// it, a body that cannot stand by a channeller (its Focus is the bag's) steps in to bank or farm and back each turn.
const ChampionBelief* tribute_to_deny(const World& world) {
    if (!enemy_seen(world)) return nullptr;
    const int need = static_cast<int>(cambc::constants::winning_gems) - world.score.enemy;
    const ChampionBelief* best = nullptr;
    int best_steps = unreachable, ours = -1;
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible || e.channel != Channel::tribute) continue;
        const bool big = (params::deny_bag > 0 && e.gems >= params::deny_bag)
                         || (params::deny_need > 0 && static_cast<float>(e.gems) >= params::deny_need * static_cast<float>(need));
        if (!big || !holds_hard_stop(world, e)) continue;
        if (ours < 0) ours = bag_at_stake(world);
        if (ours >= std::max(40, e.gems / 3)) return nullptr;
        if (const int steps = intercept_steps(world, e, my_position()); steps < best_steps) best = &e, best_steps = steps;
    }
    return best;
}

// Into reach of the enemy whose bag ends the game, whatever the risk:""")
sub('bot.cc', """        stop_game_ender(world, pathing, memory, *ender);
        return;
    }
""", """        stop_game_ender(world, pathing, memory, *ender);
        return;
    }
    if (const auto* deny = tribute_to_deny(world)) {
        stop_game_ender(world, pathing, memory, *deny);
        return;
    }
""")
print('ok', d)
