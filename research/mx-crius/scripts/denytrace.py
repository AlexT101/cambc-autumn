"""DENY trace lines (e-denial debug builds): deny_of's d = p K by the group's side s (home_side: 1 at our spawn;
own s>0.6, middle 0.4-0.6, enemy <0.4) and round band; p = d / (ratio (1 + premium)) when no Prism premium.
usage: py denytrace.py BATCH_DIR"""
import zipfile, glob, sys, re, collections
from concurrent.futures import ProcessPoolExecutor
LINE = re.compile(rb'DENY (\d+) \d+ g\d+ s=([\d.]+) d=([\d.]+) ratio=([\d.]+) prem=([\d.]+)(?: P=([\d.]+))?')


def one(f):
    out = []
    try:
        z = zipfile.ZipFile(f)
        for n in ('team-a.stdout', 'team-b.stdout'):
            for m in LINE.finditer(z.read(n)):
                r, s, d, ratio, prem = int(m[1]), float(m[2]), float(m[3]), float(m[4]), float(m[5])
                out.append((r, s, d, ratio, prem, float(m[6]) if m[6] else -1))
    except Exception:
        pass
    return out


if __name__ == '__main__':
    fs = glob.glob(sys.argv[1] + '/*.repl26a')
    S = []
    with ProcessPoolExecutor(48) as ex:
        for o in ex.map(one, fs, chunksize=16): S.extend(o)
    print('lines', len(S))
    zone = lambda s: 'own' if s > 0.6 else 'mid' if s >= 0.4 else 'enemy'
    by = collections.defaultdict(list)
    for r, s, d, ratio, prem, P in S:
        band = 'r<=150' if r <= 150 else 'r<=400' if r <= 400 else 'r>400'
        by[(band, zone(s))].append(d / (ratio * (1 + prem)) if ratio > 0 else 0)
        by[('all', zone(s))].append(d / (ratio * (1 + prem)) if ratio > 0 else 0)
        by[('d', zone(s))].append(d)
        if P >= 0: by[('P', zone(s))].append(P)
    for k in sorted(by):
        v = sorted(by[k]); n = len(v)
        print('%-7s %-6s n=%7d mean %.3f  q10 %.3f q25 %.3f q50 %.3f q75 %.3f q90 %.3f' % (
            k[0], k[1], n, sum(v) / n, v[n // 10], v[n // 4], v[n // 2], v[3 * n // 4], v[9 * n // 10]))
    rs = sorted(x[3] for x in S); ps = sorted(x[4] for x in S); n = len(S)
    print('ratio q10/50/90 %.3f %.3f %.3f; premium q50/90 %.3f %.3f' % (rs[n // 10], rs[n // 2], rs[9 * n // 10], ps[n // 2], ps[9 * n // 10]))
