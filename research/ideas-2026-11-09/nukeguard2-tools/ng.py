import zipfile, re, json, sys, collections
agg = collections.Counter(); tot = collections.Counter()
for b in sys.argv[1:]:
    for m in json.load(open(b + '/results.json'))['matches']:
        p = m.get('replay')
        if not p: continue
        t = 'ab'[0 if m['order'][0] == 0 else 1]
        o = zipfile.ZipFile(p).read(f'team-{t}.stdout').replace(b'\0', b'').decode('utf-8', 'replace')
        for mm in re.finditer(r'^NG (\d+) (\d+) (\S) (\S*) (\d) (\d) (-?\d+) (-?\d+) (\S+)$', o, re.M):
            dec, trail, lf, lt, nf, nt = mm[3], mm[4], int(mm[5]), int(mm[6]), int(mm[7]), int(mm[8])
            tot[dec] += 1
            kind = ('L' if lf else '-') + ('N' if nf >= 0 else '') + '>' + ('L' if lt else '-') + ('N' if nt >= 0 else '')
            if kind == '->-': continue
            agg[(kind, dec, trail)] += 1
G = 2 * 256
print('moving turns by branch:', dict(tot.most_common(12)))
for (k, d, t), n in sorted(agg.items(), key=lambda x: (x[0][0], -x[1])):
    if n >= 8: print(f'{k:8s} {d} {t:6s} {n:5d}  {n/G:.3f}/game')
