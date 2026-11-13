"""Farm-choice switches (C13): FS / D / DP lines of the candidate's team in a debug A/B's replays.
usage: dither.py BATCH_DIR CAND_NAME [max_round]"""
import zipfile, glob, re, collections, sys, os
from concurrent.futures import ProcessPoolExecutor

TYPES = 'Ryth Vesper Vendetta Cassi Issac Stellar Prism Marcella Willow Ren Varg Tavi HoR'.split()
D = re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
DP = re.compile(rb'^[\s\0]*DP (\d+) (\d+) (\d+) (-?\d+) (-?\d+)\s*$', re.M)
FS = re.compile(rb'^[\s\0]*FS (\d+) (\d+) (-?\d+) (-?\d+) (\S) (\d+) (\S+) (-?\d+) (-?\d+) (\d) (-?\d+) (\d+)\s*$', re.M)
MAXR = int(sys.argv[3]) if len(sys.argv) > 3 else 2000

CLASSES = [(1024, 'prev not alive'), (1, 'camp state (sighting/wake/respawn)'), (4, 'ally claim changed'), (8, 'plan choice changed'),
           (16, 'bag changed'), (2, 'camp health seen'), (32, 'own health'), (64, 'enemy sighting'), (0, 'nothing visible')]


def cls(mask):
    for bit, name in CLASSES:
        if bit == 0 or mask & bit: return name


def one(args):
    path, team = args
    c = collections.Counter()
    try:
        z = zipfile.ZipFile(path)
        out = z.read(f'team-{team}.stdout')
    except Exception:
        return c
    typ = {}
    pos = {}
    for m in DP.finditer(out):
        r, h, t, x, y = map(int, m.groups())
        typ[h] = TYPES[t]
        pos[(h, r)] = (x, y)
    last = {}
    seg = {}  # h -> [walk rounds, switches] current walk segment
    for m in D.finditer(out):
        r, h = int(m.group(1)), int(m.group(2))
        if r > MAXR: continue
        b, fg = m.group(3).decode(), int(m.group(4))
        t = typ.get(h, '?')
        p = pos.get((h, r)); pp = pos.get((h, r - 1))
        moved = p is not None and pp is not None and p != pp and max(abs(p[0] - pp[0]), abs(p[1] - pp[1])) <= 2
        c[(t, 'turns')] += 1
        if b == 'F': c[(t, 'farm')] += 1
        L = last.get(h)
        if b == 'F' and moved:
            c[(t, 'walk')] += 1
            s = seg.setdefault(h, [0, 0])
            s[0] += 1
            if L and L[0] == r - 1 and L[1] == 'F' and L[2] >= 0 and fg >= 0 and L[2] != fg: s[1] += 1
        else:
            if h in seg:
                s = seg.pop(h)
                c[(t, 'segs')] += 1
                c[(t, 'seg_sw')] += s[1]
                if s[1] > 0: c[(t, 'segs_sw')] += 1
        if L and L[0] == r - 1 and L[1] == 'F' and b == 'F' and L[2] >= 0 and fg >= 0 and L[2] != fg:
            c[(t, 'switch')] += 1
            if moved: c[(t, 'switch_walk')] += 1
        last[h] = (r, b, fg)
    hist = collections.defaultdict(list)
    for m in FS.finditer(out):
        g = m.groups()
        r, h, prev, best = int(g[0]), int(g[1]), int(g[2]), int(g[3])
        if r > MAXR: continue
        mode, mask, t = g[4].decode(), int(g[5]), TYPES[int(g[11])]
        k = cls(mask)
        c[(t, 'fs')] += 1
        c[(t, 'cls', k)] += 1
        c[(t, 'mode', mode)] += 1
        if mask & 128: c[(t, 'prev claimed by ally')] += 1
        if mask & 256: c[(t, 'best claimed by ally')] += 1
        if mask & 512: c[(t, 'prev was plan')] += 1
        if int(g[9]): c[(t, 'banking')] += 1
        hist[h].append((r, prev, best, k))
    for h, L in hist.items():
        t = typ.get(h, '?')
        for i, (r, prev, best, k) in enumerate(L):
            back = any(r2 - r <= 10 and p2 == best and b2 == prev for (r2, p2, b2, _) in L[i + 1:i + 4])
            if back:
                c[(t, 'flipback')] += 1
                c[(t, 'flipback_cls', k)] += 1
    return c


if __name__ == '__main__':
    d, cand = sys.argv[1], sys.argv[2]
    jobs = []
    for line in open(os.path.join(d, 'manifest.txt')):
        a, b, _, rp = line.split()
        if cand in os.path.basename(a): jobs.append((rp, 'a'))
        elif cand in os.path.basename(b): jobs.append((rp, 'b'))
    tot = collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for c in ex.map(one, jobs, chunksize=8): tot += c
    types = sorted({k[0] for k in tot}, key=lambda t: -tot[(t, 'turns')])
    print(f'{len(jobs)} games, rounds <= {MAXR}')
    for t in types + ['ALL']:
        g = (lambda *k: sum(v for kk, v in tot.items() if kk[1:] == k)) if t == 'ALL' else (lambda *k: tot[(t,) + k])
        if g('turns') == 0: continue
        fs = g('fs') or 1
        print(f"\n{t}: turns {g('turns')} farm {g('farm')} walk {g('walk')} ({100 * g('walk') / g('turns'):.0f}%); "
              f"walk segs {g('segs')}, with a switch {100 * g('segs_sw') / max(1, g('segs')):.0f}%, switches/seg {g('seg_sw') / max(1, g('segs')):.2f}; "
              f"farm switches {g('switch')} (walking {g('switch_walk')}); FS {g('fs')}")
        print('  causes: ' + ', '.join(f"{name} {100 * g('cls', name) / fs:.1f}%" for _, name in CLASSES))
        print('  modes: ' + ', '.join(f"{m} {100 * g('mode', m) / fs:.0f}%" for m in 'SKCJGLQTHPr' if g('mode', m)))
        print(f"  prev claimed by ally {100 * g('prev claimed by ally') / fs:.1f}%, best claimed by ally {100 * g('best claimed by ally') / fs:.1f}%, "
              f"prev was plan {100 * g('prev was plan') / fs:.1f}%, banking {100 * g('banking') / fs:.1f}%; flip back within 10 {100 * g('flipback') / fs:.1f}%: "
              + ', '.join(f"{name} {g('flipback_cls', name)}" for _, name in CLASSES if g('flipback_cls', name)))
