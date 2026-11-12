"""Fuel shortcuts on the Prism's turns, with an enemy in sight or not (variants/pl-prof: PF and SHORTCUT lines).
python3 shortcuts.py BATCHGLOB"""
import collections, glob, sys, zipfile
near = collections.Counter(); far = collections.Counter(); nn = nf = 0; nd = collections.Counter()
for f in glob.glob(sys.argv[1] + '/*.repl26a'):
    side = 'b' if f.rsplit('.', 1)[0].endswith('-21') else 'a'
    sc = collections.defaultdict(set); pf = {}
    for line in zipfile.ZipFile(f).read(f'team-{side}.stdout').decode('utf-8', 'replace').replace('\x00', '').splitlines():
        v = line.split()
        if len(v) >= 4 and v[0] == 'SHORTCUT':
            try: sc[(int(v[1]), int(v[2]))].add(v[3])
            except ValueError: pass
        elif len(v) == 11 and v[0] == 'PF':
            try: pf[(int(v[1]), int(v[2]))] = (v[3], int(v[4]))
            except ValueError: pass
    for k, (dec, d) in pf.items():
        if d <= 8:
            nn += 1; near.update(sc.get(k, ())); nd[dec] += 1
        else:
            nf += 1; far.update(sc.get(k, ()))
print(f'Prism turns that finished: enemy in sight within 8: {nn}; none: {nf}')
print('per 1000 turns, enemy within 8 | none:')
for k in sorted(set(near) | set(far), key=lambda k: -near[k]):
    print(f'  {k:28s} {1000 * near[k] / nn:7.1f} | {1000 * far[k] / nf:7.1f}')
