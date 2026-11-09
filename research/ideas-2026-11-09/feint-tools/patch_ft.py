"""After patch_mite.py --v3: drop the first-turn contact cancel (continue_tribute decides alone); --one keeps the habit
to channels that complete at our next turn start (tribute_turns == 1)."""
import sys, re
from pathlib import Path
bank = Path(sys.argv[1]) / 'src/economy/bank.cc'; s = bank.read_text()
i = s.index('    if (tribute_began == world.round - 1'); j = s.index('    if (tribute_ok(world, safety, memory, my_channel_time())) return true;', i)
s = s[:i] + s[j:]
i = s.index("// Mite's habit: the round"); j = s.index('// At an unlocked altar in reach. The caller judged')
s = s[:i] + s[j:]
s = s.replace('            tribute_began = world.round;\n', '').replace('        tribute_began = world.round;\n', '')
assert 'tribute_began' not in s and 'mite_contact' not in s
if '--one' in sys.argv:
    old = '    if (tribute_turns(world, my_gems()) > rounds_left(world)) return false;'
    assert s.count(old) == 1
    s = s.replace(old, old + '\n    // Started at the turn end, a one-turn channel completes at our next turn start: no turn is spent on it.\n'
                  '    if (tribute_turns(world, my_gems()) > 1) return false;')
s = s.replace("// Mite's turn-end channel: a tribute wherever one can start, else the caller's recall feint.",
              "// A turn-end tribute wherever one can start (Mite's habit), else the caller's recall feint: the turn has acted,\n"
              "// so standing in a channel costs nothing, and next turn continue_tribute keeps or cancels it.")
bank.write_text(s)
