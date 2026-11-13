"""PDKG-STAND lines in a debug batch's replays: how often the feed term reaches a life where the base rule did not.
    python3 dbgread.py BATCH_DIR"""
import sys, zipfile, glob, collections, statistics as st
d = sys.argv[1]
games = 0; per_game = []; pg = []; ex = []; flips = 0; lines = 0; rounds = []
for z in glob.glob(f'{d}/**/*.repl26a', recursive=True) + glob.glob(f'{d}/**/*.zip', recursive=True):
    try: zf = zipfile.ZipFile(z)
    except Exception: continue
    games += 1; n = 0
    for name in zf.namelist():
        if not name.endswith('.stdout'): continue
        for l in zf.read(name).decode(errors='replace').splitlines():
            if not l.startswith('PDKG-STAND'): continue
            f = l.split(); lines += 1
            x = float(f[4]); p = float(f[6]); fl = int(f[10])
            ex.append(x); pg.append(p); rounds.append(int(f[1]))
            if fl: flips += 1; n += 1
    per_game.append(n)
print(f'games {games}, PDKG lines {lines}, flips (falls now true) {flips}, flips per game {flips/max(1,games):.2f}, games with a flip {sum(1 for n in per_game if n)}')
if pg:
    q = lambda v: [round(st.quantiles(v, n=10)[i], 3) for i in (0, 4, 8)]
    print('per_gold deciles 10/50/90', q(pg), ' extra deciles', q(ex), ' rounds deciles', q(rounds))
