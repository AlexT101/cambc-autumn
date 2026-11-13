"""qcast-dbgB: camp casts fired that the old engagement_near gate would have held (QK ... released=1), per champion-game.
usage: qcreleased.py BATCH_DIR"""
import sys, zipfile, collections
from pathlib import Path
NAMES = ['ryth','vesper','vendetta','cassi','issac','stellar','prism','marcella','willow','ren','varg','tavi','heart']
T = collections.Counter(); G = collections.Counter(); casts = collections.Counter()
files = sorted(Path(sys.argv[1]).glob('*.repl26a'))
for f in files:
    z = zipfile.ZipFile(f)
    for t in ('team-a.stdout', 'team-b.stdout'):
        try: lines = z.read(t).decode(errors='replace').splitlines()
        except KeyError: continue
        seen = set()
        for l in lines:
            p = l.split()
            if not p or p[0] != 'QK' or len(p) < 9: continue
            name = NAMES[int(p[7])]
            if (p[2], name) not in seen: seen.add((p[2], name)); G[name] += 1
            if p[4] in 'cg': casts[name] += 1
            if p[8] == '1' and p[4] in 'cg': T[(name, int(p[3]))] += 1
print('games', len(files))
for (name, s), v in sorted(T.items()):
    print(f'{name:9s} slot{s}: {v:5d} released camp casts, {v / G[name]:.2f} per champion-game (all camp casts {casts[name] / G[name]:.1f}/cg)')
