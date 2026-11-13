"""escort counters from a debug batch's stdout (ESC and D lines). Usage: esccount.py BATCH_DIR
Per game (both sides' CAND-and-REF stdout are mixed: only the escort variant prints ESC):
  P  Prism turns posting an encounter;  S escort steps (each a farm step given up);  I ally turns already within
  the radius (farm kept inside);  f too far for the horizon;  l linked partner blocks;  n search failed.
Farm turns: D lines with branch F (escort sides only), and Y (escort) turns."""
import sys, zipfile, collections
from pathlib import Path
games = 0
c = collections.Counter(); hz = collections.Counter(); br = collections.Counter(); enc_games = 0; sides = 0
for f in sorted(Path(sys.argv[1]).glob('*.repl26a')):
    z = zipfile.ZipFile(f); games += 1
    for t in ('team-a.stdout', 'team-b.stdout'):
        lines = z.read(t).decode(errors='replace').splitlines()
        if not any(l.startswith('ESCBITS') for l in lines): continue
        sides += 1; any_p = False
        for l in lines:
            if l.startswith('ESC '):
                p = l.split(); c[p[3]] += 1
                if p[3] == 'P': hz[min(int(p[4]), 20)] += 1; any_p = True
            elif l.startswith('D '):
                br[l.split()[3]] += 1
        enc_games += any_p
print(f'games {games}, escort sides {sides}, sides with an encounter {enc_games}')
print('per escort side:', {k: round(v / sides, 2) for k, v in sorted(c.items())})
print('farm (F) turns per side', round(br['F'] / sides, 1), 'escort (Y) turns per side', round(br['Y'] / sides, 2))
print('posted horizon', sorted(hz.items()))
