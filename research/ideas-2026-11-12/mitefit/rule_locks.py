"""Rule layer (mitere 'Locks'): Mite buys no lock before about round 350, then about half its bodies carry one.
    py rule_locks.py BODY_DIR"""
import sys
from pathlib import Path
f = Path(sys.argv[1]) / 'src/bot.cc'; s = f.read_text()
old = '    if (consumables) buy_lock();\n'
assert s.count(old) == 1
f.write_text(s.replace(old, '    // Mite (mitere): no lock before about r350, then about half the bodies carry one.\n'
                            '    if (consumables && world.round >= 350 && world.me().index % 2 == 0) buy_lock();\n'))
print('patched', f)
