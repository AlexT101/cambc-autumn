"""The strike search's fuel by phase (SRCH lines of debug games): python3 srch.py BATCHGLOB"""
import glob, sys, zipfile, collections
from multiprocessing import Pool


def one(f):
    side = 'b' if f.rsplit('.', 1)[0].endswith('-21') else 'a'
    out = []
    try: text = zipfile.ZipFile(f).read(f'team-{side}.stdout').decode('utf-8', 'replace').replace('\x00', '')
    except Exception: return out
    for line in text.splitlines():
        if not line.startswith('SRCH '): continue
        v = line.split()
        try:
            d = {v[i]: v[i + 1] for i in range(3, len(v) - 1, 2)}
            out.append({k: int(d[k]) for k in ('fuel', 'nodes', 'offers', 'tiles', 'priced', 'queries', 'capped', 'read', 'grow', 'price', 'act', 'foes', 'units', 'leaves', 'left')})
        except (ValueError, KeyError, IndexError): pass
    return out


if __name__ == '__main__':
    files = sorted(f for g in sys.argv[1:] for f in glob.glob(g + '/*.repl26a'))
    with Pool(32) as pool: R = [r for g in pool.map(one, files, chunksize=16) for r in g]
    q = lambda u, p: u[min(len(u) - 1, int(p * len(u)))] if u else 0
    print(len(R), 'searches in', len(files), 'games')
    for name, S in (('all', R), ('fuel 20k+', [r for r in R if r['fuel'] >= 20000]), ('fuel 35k+', [r for r in R if r['fuel'] >= 35000]), ('foes 3+', [r for r in R if r['foes'] >= 3])):
        if not S: continue
        print(f'\n{name}: {len(S)} ({100 * len(S) / len(R):.1f}%)')
        for k in ('fuel', 'read', 'grow', 'price', 'act', 'nodes', 'tiles', 'priced', 'queries', 'foes', 'units', 'leaves', 'left'):
            u = sorted(r[k] for r in S)
            print(f'  {k:8s} mean {sum(u) / len(u):9.0f}  p50 {q(u, .5):7d} p90 {q(u, .9):7d} p99 {q(u, .99):7d}')
        print(f'  capped (nodes at the cap): {100 * sum(1 for r in S if r["capped"]) / len(S):.1f}%;  left under 40k at the start: {100 * sum(1 for r in S if r["left"] < 40000) / len(S):.1f}%')
