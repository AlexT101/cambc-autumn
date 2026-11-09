"""segan.py GAMESDIR [--top N] [--kind t|g|c] : aggregate SEG tables (last dump per instance) over all games."""
import sys, zipfile, collections, glob, os, pickle
d = sys.argv[1]
ANY = '--any' in sys.argv
OOFS = '--oof' in sys.argv
TAG = 'OOF' if OOFS else 'ANY' if ANY else 'SEG'
top = int(sys.argv[sys.argv.index('--top') + 1]) if '--top' in sys.argv else 40
agg = {}
turns = oof = 0
for f in glob.glob(f"{d}/**/*.repl26a", recursive=True):
    z = zipfile.ZipFile(f)
    for side in 'ab':
        try: s = z.read(f'team-{side}.stdout').decode(errors='replace')
        except KeyError: continue
        last = {}
        cur = collections.defaultdict(list)
        for line in s.replace('\x00', '').splitlines():
            i = line.find(TAG)
            if i < 0: i = line.find('SEGEND')
            if i < 0: continue
            w = line[i:].split()
            try:
                if w[0] == TAG and len(w) == 11:
                    int(w[6]), int(w[7]), int(w[8]), int(w[9]); cur[w[1]].append(w)
                elif w[0] == 'SEGEND' and len(w) == 5:
                    last[w[1]] = (cur[w[1]], int(w[3]), int(w[4])); cur[w[1]] = []
            except ValueError: pass
        for rows, t, o in last.values():
            turns += t; oof += o
            for w in rows:
                k = (w[3], w[4], w[5])
                n, mx, ex, sm = int(w[6]), int(w[7]), int(w[8]), int(w[9])
                a = agg.get(k)
                if a is None: agg[k] = [n, mx, ex, sm, os.path.basename(os.path.dirname(f)) + f":r{w[10]}"]
                else:
                    a[0] += n; a[3] += sm
                    if mx > a[1]: a[1] = mx; a[4] = os.path.basename(os.path.dirname(f)) + f":r{w[10]}"
                    a[2] = max(a[2], ex)
pickle.dump((agg, turns, oof), open(f"{d}.{TAG.lower()}.pkl", "wb"))
print(f"turns {turns} oof {oof}")
def show(title, items):
    print(title)
    for k, a in items[:top]:
        print(f"{a[1]:>7} ex{a[2]:>8} n{a[0]:>9} mean{a[3]//max(1,a[0]):>6}  {k[2]} {k[0]} -> {k[1]}  @{a[4]}")
if OOFS: show("== OOF turns by (last reset -> last mark): max = fuel left at that reset", sorted(agg.items(), key=lambda x: -x[1][0])); sys.exit()
if ANY: show("== consecutive marks by max", sorted(agg.items(), key=lambda x: -x[1][1])); sys.exit()
show("== in the deadline (from a 'd' checkpoint) by excess over its need", sorted([x for x in agg.items() if x[0][2] == 'd'], key=lambda x: -x[1][2]))
show("== by max cost, checkpoint/turn-start segments", sorted([x for x in agg.items() if x[0][2] in 'ct'], key=lambda x: -x[1][1]))
show("== by excess over gate floor", sorted([x for x in agg.items() if x[0][2] == 'g'], key=lambda x: -x[1][2]))
