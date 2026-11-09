"""The prey loop per team-game, from cg_instrument.py traces: chase builds, verdicts that escape, fight sims and lost ones.

usage: cg_preyloop.py BATCH_DIR"""
import sys, glob, zipfile
from collections import Counter
c = Counter()
g = 0
for f in glob.glob(sys.argv[1] + '/*.repl26a'):
    order = f.rsplit('-', 1)[1][:2]
    z = zipfile.ZipFile(f)
    team = 'a' if order == '12' else 'b'
    g += 1
    for l in z.read(f'team-{team}.stdout').decode(errors='replace').replace('\x00', '').splitlines():
        if not (l.startswith('CG ') or l.startswith('CGO ')): continue
        p = l.split()
        try:
            n = int(p[10]); b = [tuple(map(int, x.split(':'))) for x in p[11:11 + n]]
            pe, ps, pl, sc = int(p[16 + n]), int(p[17 + n]), int(p[18 + n]), int(p[19 + n])
        except (ValueError, IndexError):
            continue
        b3 = [x for x in b if x[0] in (3, 13)]
        c['turns'] += 1
        c['loop builds'] += len(b3)
        c['build cost'] += sum(x[2] for x in b3)
        c['escaped'] += pe
        c['sims'] += ps
        c['lost'] += pl
        c['sim cost'] += sc
        if b3:
            c['build turns'] += 1
            c['build turns sims'] += ps
            c['build turns lost'] += pl
            c['build turns esc'] += pe
for k, v in c.items(): print(f'{k:20s} {v / g:10.2f} a team-game')
print(f"mean build {c['build cost'] / max(1, c['loop builds']):.0f}, mean sim {c['sim cost'] / max(1, c['sims']):.0f}, lost share {c['lost'] / max(1, c['sims']):.3f}")
