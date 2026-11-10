"""Trap deaths (killer no turn after P, lethal at O) with the RS0/RS1 trace of retreat_step at P and O.
Usage: rtrace.py ANA BATCH... ; batches give the stdout (team of our bot from the -12/-21 suffix)."""
import sys, os, glob, json, zipfile, collections
sys.path.insert(0, os.path.dirname(__file__)); import bl
ANA = sys.argv[1]; BATCHES = sys.argv[2:]
zips = {}
for b in BATCHES:
    for z in glob.glob(f'{b}/*.repl26a'): zips[os.path.basename(z).split('.')[0]] = z
L = lambda x: x[5] >= x[2]
nb = lambda p: [(p[0] + dx, p[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
def burst(q, near):
    t = 0.0
    for z in near:
        if not z[4]: continue
        d = max(abs(q[0] - z[10][0]), abs(q[1] - z[10][1]))
        t += bl.window_burst(z[0], z[13], z[14], d, (z[6], z[7]), z[5], z[15])[0]
    return t
C = collections.Counter(); ex = []; n = 0
for m in sorted(glob.glob(f'{ANA}/*/meta.json')):
    mm = json.load(open(m)); base = os.path.basename(mm['source']).split('.')[0]
    us = 0 if base.endswith('-12') else 1
    g = bl.analyse({'dir': os.path.dirname(m), 'us': us, 'mid': base, 'win': False}); n += 1
    txt = zipfile.ZipFile(zips[base]).read('team-a.stdout' if us == 0 else 'team-b.stdout').decode(errors='replace')
    rs0, rs1, D = {}, {}, {}
    for l in txt.split('\n'):
        f = l.split()
        if not f: continue
        try:
            if f[0] == 'RS0': rs0[(int(f[1]), int(f[2]))] = f[3:]
            elif f[0] == 'RS1': rs1[(int(f[1]), int(f[2]))] = f[3:]
            elif f[0] == 'D' and len(f) >= 4: D[(int(f[1]), int(f[2]))] = f[3]
        except ValueError: pass
    by = collections.defaultdict(dict)
    for x in g['rows']: by[x[12]][x[0]] = x
    for x in g['rows']:
        if not (x[7] and L(x)): continue
        v, r = x[12], x[0]; P = by[v].get(r - 1); Q = by[v].get(r - 2)
        if not P or L(P) or not Q: continue
        kz = max(x[11], key=lambda z: z[2]); kp = [z for z in P[11] if z[9] == kz[9]]
        if not kp or kp[0][5] != 0: continue
        hp = x[2]
        escP = any(any(burst(q, x[11]) < hp for q in nb(p)) for p in nb(Q[13]))
        good = [p for p in nb(Q[13]) if any(burst(q, x[11]) < hp for q in nb(p))]
        k = (r - 1, v)
        br = D.get(k, '?')
        if k not in rs0: C[(escP, br, 'no retreat_step')] += 1; continue
        a = rs0[k]; act, dead = a[2], a[3]
        cls = (escP, br, f'active {act} deadly {dead}', 'ranked' if k in rs1 else 'early exit')
        C[cls] += 1
        if escP and k in rs1 and len(ex) < 25:
            chosen = (P[13][0] - Q[13][0], P[13][1] - Q[13][1])
            ex.append((base, r - 1, x[1], hp, kz[0], kz[1], chosen, [(p[0] - Q[13][0], p[1] - Q[13][1]) for p in good], ' '.join(rs1[k])))
print(n, 'games')
for k, c in C.most_common(): print(f'  {c/n:.3f}/game  escapable-at-P {k[0]}  {k[1:]}')
for e in ex: print('  ', e)
