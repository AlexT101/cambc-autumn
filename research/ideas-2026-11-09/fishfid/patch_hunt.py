"""Hunt: a body chases a visible enemy whatever its health or half (FISH_MODEL 10.1: Fish engages healthy, low-danger
targets; real Fish and Mite kill our full-health bodies ~1.7x as often as the bodies do). prey's other tests stay:
not near its spawn, not a teleport it can't catch, and not where every tile in its reach makes us retreat.
Usage: patch_hunt.py BOT_DIR"""
import sys, pathlib
p = pathlib.Path(sys.argv[1]) / 'src/combat/fight.cc'; s = p.read_text()
old = '''    if (!(comeback::cooked(world) && pair_gems(world, e) >= params::comeback::bar_bag) && dist(here, e.pos) > range && !own_ground(world, e.pos) && e.health >= params::hurt_health_fraction * e.max_health && held == 0
        && (pair_gems(world, e) == 0 || intercept_steps(world, e, here) == unreachable))
        return false;
'''
assert s.count(old) == 1
p.write_text(s.replace(old, ''))
