"""Engagement holds (qcast-dbg): a damaging slot ready on an F-branch camp-hit turn, unused because engagement_near held it.
For each hold episode (first held turn of a run), the slot's next use: on an enemy within the cooldown (the hold paid),
on a camp, or later. usage: qchold.py BATCH_DIR"""
import sys, zipfile, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
NAMES = ['ryth','vesper','vendetta','cassi','issac','stellar','prism','marcella','willow','ren','varg','tavi','heart']
DMG = {'prism':(1,1),'stellar':(1,1),'ryth':(1,0),'cassi':(1,0),'marcella':(0,1),'ren':(1,0),'tavi':(0,1)}
CD = 8
def one(f):
    out = collections.Counter()
    try: z = zipfile.ZipFile(f)
    except Exception: return out
    for t in ('team-a.stdout','team-b.stdout'):
        try: lines = z.read(t).decode(errors='replace').splitlines()
        except KeyError: continue
        qx = {}; qc = []; uses = collections.defaultdict(list); dec = {}
        for l in lines:
            p = l.split()
            if not p: continue
            if p[0] == 'QX': qx[(int(p[1]),p[2])] = p
            elif p[0] == 'QC': qc.append(p)
            elif p[0] == 'D' and len(p) >= 4: dec[(int(p[1]), p[2])] = p[3]
            elif p[0] == 'QK': uses[(p[2], int(p[3]))].append((int(p[1]), p[4], p[5], int(p[6])))
        holds = collections.defaultdict(list)
        for p in qc:
            r, h = int(p[1]), p[2]; x = qx.get((r,h))
            if not x or p[3] != 'F' or p[12] != 'engagement': continue
            name = NAMES[int(x[3])]
            cd0s, cd1s, cd0e, cd1e = map(int, p[5:9])
            if (cd0s == 0 and cd0e > 0) or (cd1s == 0 and cd1e > 0): continue
            for s in (0,1):
                if (cd0s if s == 0 else cd1s) == 0 and name in DMG and DMG[name][s]:
                    holds[(h, s, name)].append((r, int(x[9]), float(x[5]), float(x[6] if s == 0 else x[7])))
        for (h, s, name), rs in holds.items():
            rs.sort(); prev = -99
            for r, ed, ghp, dm in rs:
                episode = r - prev > 1; prev = r
                if not episode: continue
                nxt = next((u for u in uses[(h, s)] if u[0] > r), None)
                k = (name, s)
                out[k + ('episodes',)] += 1
                window = [dec.get((rr, h), 'dead') for rr in range(r + 1, r + CD)]
                fight = any(w in ('A', 'C', 'R', 'm', 'E') for w in window)
                died = 'dead' in window
                out[k + ('window', 'died' if died else 'fight' if fight else 'quiet')] += 1
                out[k + ('bydist', min(ed, 9), 'n')] += 1
                out[k + ('edist', min(ed, 9))] += 1
                if nxt is None: out[k + ('next', 'none')] += 1; continue
                d = nxt[0] - r
                enemy = nxt[1] == 'e' or (nxt[1] == 'g' and nxt[3] > 0 and nxt[2] != 'F')
                where = 'enemy' if enemy else ('camp' if nxt[2] in 'FS' or nxt[1] == 'c' else 'other:' + nxt[2] + nxt[1])
                out[k + ('next', where + (' <cd' if d < CD else ' >=cd'))] += 1
                if (where == 'enemy' or where.startswith('other')) and d < CD: out[k + ('bydist', min(ed, 9), 'paid')] += 1
                out[k + ('delay_sum',)] += d
    return out
if __name__ == '__main__':
    files = sorted(Path(sys.argv[1]).glob('*.repl26a'))
    T = collections.Counter()
    with ProcessPoolExecutor(16) as ex:
        for o in ex.map(one, files, chunksize=4): T.update(o)
    for k in sorted({kk[:2] for kk in T}):
        n = T[k + ('episodes',)]
        print(f'{k[0]} slot{k[1]}: {n} hold episodes ({n/len(files):.2f}/game), mean delay to next use {T[k+("delay_sum",)]/max(1,n):.1f}')
        for kk, v in sorted(T.items()):
            if kk[:2] == k and kk[2] == 'next': print(f'    next use {kk[3]:20s} {v:5d} {100*v/n:5.1f}%')
        print('    window (next 7 rounds):', {kk[3]: v for kk, v in sorted(T.items()) if kk[:2] == k and kk[2] == 'window'})
        print('    by dist (n, used on enemy/other <cd):', {kk[3]: (T[k + ('bydist', kk[3], 'n')], T[k + ('bydist', kk[3], 'paid')]) for kk in sorted(T) if kk[:2] == k and kk[2] == 'bydist' and kk[4] == 'n'})
        print('    nearest visible enemy at hold:', {kk[3]: v for kk, v in sorted(T.items()) if kk[:2] == k and kk[2] == 'edist'})
