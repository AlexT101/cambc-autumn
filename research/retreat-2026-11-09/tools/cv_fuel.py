"""OOF trace lines by phase, and chase-plan builds (ESCC lines: count, mean fuel), for one bot in debug batches.

usage: cv_fuel.py BOT BATCH_DIR [BATCH_DIR ...]
"""
import sys, json, zipfile, glob
from collections import Counter

bot, dirs = sys.argv[1], sys.argv[2:]
oof, n, builds, fuel, kinds = Counter(), 0, 0, 0, Counter()
for d in dirs:
    res = json.load(open(f'{d}/results.json'))
    names = res.get('bots') or res.get('names')
    for f in glob.glob(f'{d}/*.repl26a'):
        side = f.rsplit('-', 1)[1][:2]  # 12: bot 1 is team A
        z = zipfile.ZipFile(f)
        # bot 1 is the A/B's CAND; with 12 it is team a
        team = 'a' if side == '12' else 'b'
        lines = z.read(f'team-{team}.stdout').decode(errors='replace').replace('\x00', '').splitlines()
        n += 1
        for l in lines:
            if l.startswith('OOF '):
                p = l.split()
                oof[p[2] if len(p) > 2 else '?'] += 1
            elif l.startswith('ESCC '):
                p = l.split()
                if len(p) != 8 or not p[-1].isdigit(): continue  # cut by the 1 MiB stdout cap
                builds += 1
                fuel += int(p[-1])
                kinds[p[5]] += 1
print(f'{bot}: {n} team-games; OOF lines {sum(oof.values()) / n:.2f} a game')
for k, v in oof.most_common(15): print(f'  {k:30s} {v / n:6.3f}')
if builds: print(f'chase builds {builds / n:.1f} a game, mean {fuel / builds:.0f} fuel; kinds {dict(kinds)}')
