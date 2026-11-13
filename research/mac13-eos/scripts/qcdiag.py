"""Tabulate QC lines (qcast-dbg): turns a champion basic-hit a camp with a damaging/reset slot ready and did not use it.
usage: qcdiag.py BATCH_DIR [--branch F]"""
import sys, zipfile, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
NAMES = ['ryth','vesper','vendetta','cassi','issac','stellar','prism','marcella','willow','ren','varg','tavi','heart']
DMG = {'prism':(1,1),'stellar':(1,1),'ryth':(1,0),'cassi':(1,0),'marcella':(0,1),'ren':(1,0),'tavi':(0,1)}  # damaging slots
RESET = {'vendetta':0,'willow':1,'tavi':0,'marcella':0,'ryth':1,'varg':0,'vesper':0,'issac':0}

def one(f):
    out = collections.Counter(); champs = set()
    try: z = zipfile.ZipFile(f)
    except Exception: return out, champs
    for t in ('team-a.stdout','team-b.stdout'):
        try: lines = z.read(t).decode(errors='replace').splitlines()
        except KeyError: continue
        qx = {}; enemy_round = {}
        rows = []
        for l in lines:
            p = l.split()
            if not p: continue
            if p[0] == 'QX': qx[(int(p[1]),p[2])] = p
            elif p[0] == 'QC': rows.append(p)
        for p in rows:
            r, h = int(p[1]), p[2]
            x = qx.get((r,h))
            if not x: continue
            name = NAMES[int(x[3])] if int(x[3]) < len(NAMES) else x[3]
            champs.add((f.name, t, h, name))
            br, site = p[3], p[4]
            cd0s, cd1s, cd0e, cd1e = map(int, p[5:9]); moved, seen = int(p[9]), int(p[10])
            ghp, dm0, dm1, mono = float(x[5]), float(x[6]), float(x[7]), int(x[8])
            key = (t, h)
            last = enemy_round.get(key, -99)
            if seen: enemy_round[key] = r
            quiet = not seen and r - last > 8
            any_used = (cd0s == 0 and cd0e > 0) or (cd1s == 0 and cd1e > 0)
            for s in (0,1):
                if cd0s if s == 0 else cd1s: continue  # not ready at start
                used = (cd0e if s == 0 else cd1e) > 0
                dmg_slot = name in DMG and DMG[name][s]
                reset_slot = RESET.get(name, -1) == s
                if not (dmg_slot or reset_slot): continue
                kind = 'dmg' if dmg_slot else 'reset'
                dm = dm0 if s == 0 else dm1
                tag = (name, s, kind)
                out[tag + ('n',)] += 1
                if used: out[tag + ('used',)] += 1; continue
                if any_used: out[tag + ('unused-other-slot-cast',)] += 1; continue
                if br != 'F' or not quiet:
                    out[tag + ('unused-nonquiet' if br == 'F' else 'unused-other-branch',)] += 1
                    if br == 'F' and kind == 'dmg':
                        reason = p[12] if p[11] != '-' else 'uncalled@' + site
                        if moved: reason = 'moved@' + site
                        out[tag + ('N', ('seen-now ' if seen else 'recent ') + reason)] += 1
                    continue
                if kind == 'dmg':
                    if moved: out[tag + ('unused-moved',)] += 1; out[tag + ('M', site + ('/ok' if ghp > dm else '/overkill'))] += 1; continue
                    if ghp <= dm: out[tag + ('unused-overkill',)] += 1; continue
                    reason = p[12] if p[11] != '-' else 'uncalled@' + site
                    if reason in ('no_value','chosen','exec_failed'):
                        reason += '/' + (p[13] if s == 0 else p[14])
                    if mono: reason += '+mono'
                    out[tag + ('Q', reason)] += 1
                else:
                    rr = p[19]; rs = p[20]
                    out[tag + ('Q', rr + '@' + (rs if rr != 'uncalled' else site))] += 1
    return out, champs

if __name__ == '__main__':
    files = sorted(Path(sys.argv[1]).glob('*.repl26a'))
    T = collections.Counter(); C = collections.Counter()
    with ProcessPoolExecutor(16) as ex:
        for o, ch in ex.map(one, files, chunksize=4):
            T.update(o)
            for c in ch: C[c[3]] += 1
    print('games', len(files), 'champion-games with QC lines', dict(C))
    keys = sorted({k[:3] for k in T})
    for k in keys:
        n = T[k + ('n',)]; cg = max(1, C[k[0]])
        print(f'\n{k[0]} slot{k[1]} {k[2]}: ready-at-camp-hit {n} used {T[k+("used",)]}  per champ-game: '
              f'{n/cg:.1f} ready, {T[k+("used",)]/cg:.1f} used')
        for sub in ('unused-other-slot-cast','unused-other-branch','unused-nonquiet','unused-moved','unused-overkill'):
            if T[k+(sub,)]: print(f'   {sub:24s} {T[k+(sub,)]:6d} {T[k+(sub,)]/cg:5.2f}/cg')
        ms = [(kk[4], v) for kk, v in T.items() if kk[:3] == k and len(kk) == 5 and kk[3] == 'M']
        for r, v in sorted(ms, key=lambda x: -x[1]): print(f'      moved@{r:34s} {v:6d} {v/cg:5.2f}/cg')
        ns = [(kk[4], v) for kk, v in T.items() if kk[:3] == k and len(kk) == 5 and kk[3] == 'N']
        for r, v in sorted(ns, key=lambda x: -x[1]): print(f'      nonquiet {r:31s} {v:6d} {v/cg:5.2f}/cg')
        qs = [(kk[4], v) for kk, v in T.items() if kk[:3] == k and len(kk) == 5 and kk[3] == 'Q']
        tot = sum(v for _, v in qs)
        print(f'   QUIET-UNUSED total {tot} ({tot/cg:.2f}/cg)')
        for r, v in sorted(qs, key=lambda x: -x[1]):
            print(f'      {r:40s} {v:6d} {v/cg:5.2f}/cg {100*v/max(1,tot):5.1f}%')
