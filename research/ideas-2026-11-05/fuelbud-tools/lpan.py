"""lpan.py DIR: the farm loop probe (LP/LPE lines). Per loop: groups weighed, fuel per group, value vs the loop's best;
how much loop fuel goes to groups whose value (and last loop's value for them) is far below the best."""
import sys, zipfile, glob, collections
D = sys.argv[1]
tot = collections.Counter()
for z in glob.glob(D + '/**/*.repl26a', recursive=True):
    with zipfile.ZipFile(z) as f:
        for n in f.namelist():
            if not n.endswith('.stdout'): continue
            last = {}  # (handle, g) -> (round, value, best)
            cur = []
            for l in f.read(n).replace(b'\0', b'').decode('utf-8', 'replace').splitlines():
                if l.startswith('LP '):
                    _, r, h, g, fu, v, b = l.split(); cur.append((int(r), h, int(g), int(fu), float(v), int(b)))
                elif l.startswith('LPE '):
                    _, r, h, best, bv, k, ev, b = l.split(); bv = float(bv); r = int(r)
                    tot['loops'] += 1; tot['loops_bank'] += int(b)
                    for (rr, hh, g, fu, v, bb) in cur:
                        tot['fuel'] += fu; tot['groups'] += 1
                        if v < 0: tot['fuel_pruned'] += fu; tot['n_pruned'] += 1  # pruned or late before a value
                        cls = 'winner' if g == int(best) else ('far' if v >= 0 and v < 0.7 * bv else ('near' if v >= 0 else 'nov'))
                        tot['fuel_' + cls] += fu; tot['n_' + cls] += 1
                        p = last.get((h, g))
                        if p and r - p[0] <= 4 and v >= 0 and p[1] >= 0 and p[2] > 0:
                            ratio_then = p[1] / p[2]
                            if ratio_then < 0.7:
                                tot['n_stale_far'] += 1; tot['fuel_stale_far'] += fu
                                if v >= 0.95 * bv: tot['n_stale_far_now_top'] += 1
                        last[(h, g)] = (r, v, bv)
                    cur = []
f = tot['fuel'] or 1
print(dict(tot))
for k in ('winner', 'near', 'far', 'nov', 'stale_far'):
    print(f"{k}: groups {tot['n_'+k]} fuel share {tot['fuel_'+k]/f:.1%} per group {tot['fuel_'+k]/max(1,tot['n_'+k]):.0f}")
print(f"loops {tot['loops']} fuel per loop {f/tot['loops']:.0f} groups per loop {tot['groups']/tot['loops']:.1f}")
