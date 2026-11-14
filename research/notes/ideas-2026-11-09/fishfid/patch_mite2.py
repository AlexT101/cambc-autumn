"""Mt3p2: Mite body fidelity on top of patch_fm (spar-dvnK-Mt3p -> -Mt3p2), from mite-re's comparison (Mite since
2026-11-09 12:00 kills our champions ~1.8x as often as Mt3p and fights while carrying).
- fight: a bag at stake never brakes: it counts as hurt in no retreat test, and no bag breaks off a pack fight sooner.
- bank: FISH_MODEL 8.3's banking rule (a bag held while gems < 8 * (altar_walk - 2)) in place of the 25-gem floor.
  Rejected by mite-re's fit: real Mite banks smaller bags than the body.
- trip: on one-altar maps no trip to bank (Mite holds gems in the field and tributes what it has when at the altar,
  the habit), but for a winning bag or a closing game. Multi-site trips already match.
Usage: patch_mite2.py BOT_DIR [all|fight|bank|trip|fight+trip]"""
import sys, pathlib
d = pathlib.Path(sys.argv[1]) / 'src'
part = sys.argv[2] if len(sys.argv) > 2 else 'all'
def sub(f, old, new):
    p = d / f; s = p.read_text(); assert s.count(old) == 1, (f, old); p.write_text(s.replace(old, new))
if part in ('all', 'fight', 'fight+trip'):
    sub('params.h', 'inline const int& brake_bag = diana_tune.i[3];', 'inline constexpr int brake_bag = 1 << 30; // Mite: never')
    sub('params.h', 'inline const int& bag_big = diana_tune.i[6];', 'inline constexpr int bag_big = 1 << 30; // Mite: never')
if part in ('all', 'bank'):
    sub('economy/bank.cc', '    if (bag < params::min_bank && !winning_bag(world) && !closing(world, pathing)) return 0;\n',
        '    if (!winning_bag(world) && !closing(world, pathing)) {\n'
        '        const int walk = altar_steps(world, pathing, my_position(), -1);\n'
        '        if (walk == unreachable ? bag < params::min_bank : bag < 8 * (walk - 2)) return 0;\n'
        '    }\n')
if part in ('trip', 'fight+trip'):
    sub('economy/bank.cc', '    if (bag < params::min_bank && !winning_bag(world) && !closing(world, pathing)) return 0;\n',
        '    if (bag < params::min_bank && !winning_bag(world) && !closing(world, pathing)) return 0;\n'
        '    if (world.map().altars.size() == 1 && !winning_bag(world) && !closing(world, pathing)) return 0; // Mite: no trips on one-site\n')
