import sys, zipfile, os, collections, glob
B = sys.argv[1]
rows = []
for f in glob.glob(os.path.join(B, '*.repl26a')):
    z = zipfile.ZipFile(f)
    side = 0 if f.endswith('-12.repl26a') else 1  # bot 1 (camphp-dbg) is team A in -12
    for line in z.read(f'team-{"ab"[side]}.stdout').decode('latin1').splitlines():
        if line.startswith('FSW '):
            p = line.split()
            rows.append(dict(f=os.path.basename(f), r=int(p[1]), h=int(p[2]), g=int(p[3]), hp=float(p[4]), H=float(p[5]), where=p[6],
                             fv=float(p[7]), best=int(p[8]), bv=float(p[9]), steps=int(p[10]), k=int(p[11])))
ng = len(glob.glob(os.path.join(B, '*.repl26a')))
print(ng, 'games', len(rows), 'FSW lines', len(rows) / ng, '/game')
for lo, hi in ((0, .1), (.1, .25), (.25, .5), (.5, .75), (.75, 1)):
    b = [x for x in rows if lo <= x['hp'] / x['H'] < hi]
    c = collections.Counter(x['where'] for x in b)
    rat = sorted(x['bv'] / x['fv'] for x in b if x['fv'] > 0)
    q = lambda a, t: a[int(t * (len(a) - 1))] if a else None
    print(f"left {lo}-{hi}: {len(b)/ng:.2f}/game where {dict(c)}  best/fg ratio q25 {q(rat,.25)} med {q(rat,.5)} q75 {q(rat,.75)}  best=-1 {sum(1 for x in b if x['best']<0)}")
