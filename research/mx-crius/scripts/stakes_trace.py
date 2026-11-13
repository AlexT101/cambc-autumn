"""STK trace lines of d-stakes (debug builds): life_gems and bag_gems distribution, by side and round band.
usage: py stakes_trace.py BATCH_DIR  (replay zips under it)"""
import sys, glob, zipfile, collections, statistics
from concurrent.futures import ProcessPoolExecutor


def one(z):
    out = []
    try:
        with zipfile.ZipFile(z) as f:
            for n in f.namelist():
                if not n.endswith('.stdout'): continue
                for l in f.read(n).decode('utf8', 'replace').splitlines():
                    if l.startswith('STK '):
                        p = l.split()
                        out.append((int(p[1]), p[3], int(p[4]), int(p[5]), float(p[6]), float(p[7]), float(p[8]), int(p[9]), float(p[10]) if len(p) > 10 else 0.0))
    except Exception:
        pass
    return out


if __name__ == '__main__':
    zs = glob.glob(sys.argv[1] + '/*.repl26a')
    with ProcessPoolExecutor(32) as ex: S = [x for o in ex.map(one, zs, chunksize=16) for x in o]
    print('games', len(zs), 'lines', len(S))
    def q(v):
        v = sorted(v); n = len(v)
        return 'mean %6.1f  p10 %6.1f p50 %6.1f p90 %6.1f (n %d)' % (statistics.fmean(v), v[n // 10], v[n // 2], v[9 * n // 10], n)
    for tag in 'ae':
        print('side', tag, 'life_gems', q([s[4] for s in S if s[1] == tag]))
        for lo, hi in ((0, 150), (150, 400), (400, 800), (800, 2001)):
            v = [s[4] for s in S if s[1] == tag and lo <= s[0] < hi]
            if v: print('   r%4d-%4d' % (lo, hi), q(v))
        for ty in sorted(set(s[2] for s in S)):
            v = [s[4] for s in S if s[1] == tag and s[2] == ty]
            if v: print('   type %2d' % ty, q(v))
        b = [(s[3], s[5], s[6]) for s in S if s[1] == tag and s[3] > 0]
        if b:
            print('  carriers: bag', q([x[0] for x in b]))
            print('   bag_gems(no killer)', q([x[1] for x in b]), ' with killer', q([x[2] for x in b]))
            print('   killer/no-killer ratio', q([x[2] / max(1e-6, x[1]) for x in b if x[1] > 0]))

    if S and S[0][8] > 0:
        print('tuned kill beyond the bag, (max_health + life_value) / gem_value, against life_gems, by side and type')
        for tag in 'ae':
            for ty in sorted(set(s[2] for s in S)):
                v = [s for s in S if s[1] == tag and s[2] == ty]
                if not v: continue
                t = [(x[8] + 276.6) / 17.52 for x in v]
                print('  %s type %2d full %6.0f  tuned %6.1f  derived %6.1f  derived-full/gem %6.1f  neg %4.1f%%' % (
                    tag, ty, statistics.fmean(x[8] for x in v), statistics.fmean(t), statistics.fmean(x[4] for x in v),
                    statistics.fmean(x[4] - x[8] / 17.52 for x in v), 100 * sum(x[4] * 17.52 < x[8] for x in v) / len(v)))
            v = [s for s in S if s[1] == tag]
            print('  %s all: tuned %6.1f derived %6.1f' % (tag, statistics.fmean((x[8] + 276.6) / 17.52 for x in v), statistics.fmean(x[4] for x in v)))
