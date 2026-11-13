# Aggregate TERR debug counters (ia-territory measure) from an ab.py --debug batch: our side's last line per champion.
import json, sys, zipfile, collections
B = sys.argv[1]
res = json.load(open(B + '/results.json'))
tot = collections.Counter(); champs = 0; games = 0
for m in res['matches']:
    team = 'a' if m['order'][0] == 0 else 'b'
    try: z = zipfile.ZipFile(m['replay'])
    except Exception: continue
    names = z.namelist()
    fn = [n for n in names if n.endswith('team-%s.stdout' % team)]
    if not fn: continue
    games += 1
    last = {}
    for line in z.read(fn[0]).decode(errors='replace').splitlines():
        if line.startswith('TERR '):
            p = line.split(); last[p[2]] = p
    for h, p in last.items():
        champs += 1
        kv = dict(zip(p[3::2], map(int, p[4::2])))
        tot.update(kv)
print('games', games, 'champion instances', champs)
t = tot['turns']
for k in ['disc', 'free_r', 'free_n', 'half_r', 'half_n', 'dead2']:
    print('%-7s %8d  %.1f%% of farm turns' % (k, tot[k], 100 * tot[k] / max(1, t)))
for k, d in [('gems_r', 'free_r'), ('gems_n', 'free_n'), ('gems_h', 'half_r')]:
    print('%s mean best gems when %s: %.1f' % (k, d, tot[k] / max(1, tot[d])))
print('farm turns', t, 'per game', t / max(1, games))
