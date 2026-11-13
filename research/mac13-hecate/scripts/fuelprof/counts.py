"""counts.py BOTDIR PROFDIR: sum the counts-*.txt of the profiled bot's libs (turns fuel heavy heavyfuel episodes episodefuel)."""
import sys, glob, struct, os
from wbodies import bodies
bot, D = sys.argv[1], sys.argv[2]
b2, c2, o2 = bodies(bot + '/.cambc/build-release/bot-injected.wasm'); tag = sum(e - s for s, e in o2)
tot = [0] * 6; n = 0
for f in glob.glob(D + '/prof-*.bin'):
    b = open(f, 'rb').read(); nf, t, k = struct.unpack_from('<III', b, 4)
    if t != tag: continue
    c = os.path.join(os.path.dirname(f), os.path.basename(f).replace('prof-', 'counts-').replace('.bin', '.txt'))
    v = [int(x) for x in open(c).read().split()]
    tot = [a + x for a, x in zip(tot, v)]; n += 1
print(n, 'libs; turns', tot[0], 'mean', tot[1] // max(1, tot[0]), '; heavy', tot[2], 'mean', tot[3] // max(1, tot[2]), '; oof episodes', tot[4], 'fuel', tot[5])
