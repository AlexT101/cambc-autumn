"""How often the retreat's escape plan is skipped for fuel (variants/pl-prof: ESC, ESCSKIP, PF, D lines), for the Prism
and for everyone: python3 escskip.py BATCHGLOB"""
import collections, glob, sys, zipfile
tot = collections.Counter(); fuels = []
for f in glob.glob(sys.argv[1] + '/*.repl26a'):
    side = 'b' if f.rsplit('.', 1)[0].endswith('-21') else 'a'
    esc = set(); skip = {}; dec = {}; prism = set()
    for line in zipfile.ZipFile(f).read(f'team-{side}.stdout').decode('utf-8', 'replace').replace('\x00', '').splitlines():
        v = line.split()
        try:
            if len(v) >= 3 and v[0] == 'ESC': esc.add((int(v[1]), int(v[2])))
            elif len(v) == 4 and v[0] == 'ESCSKIP': skip[(int(v[1]), int(v[2]))] = int(v[3])
            elif len(v) >= 4 and v[0] == 'D': dec[(int(v[1]), int(v[2]))] = v[3]
            elif len(v) == 11 and v[0] == 'PF': prism.add(int(v[2]))
        except ValueError: pass
    for k, d in dec.items():
        if d != 'R': continue
        who = 'prism' if k[1] in prism else 'other'
        tot[(who, 'R turns')] += 1
        if k in esc: tot[(who, 'planned')] += 1
        if k in skip: tot[(who, 'skipped for fuel')] += 1; fuels.append(skip[k])
for who in ('prism', 'other'):
    n = tot[(who, 'R turns')]
    print(f'{who}: {n} retreat turns; escape plan built {100 * tot[(who, "planned")] / max(1, n):.1f}%, skipped below 50k {100 * tot[(who, "skipped for fuel")] / max(1, n):.1f}%')
fuels.sort()
if fuels: print('fuel left at a skip: median', fuels[len(fuels) // 2], 'p10', fuels[len(fuels) // 10], 'p90', fuels[9 * len(fuels) // 10])
