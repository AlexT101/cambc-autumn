"""What the freed work cost and the fuel left when its gate fired (FREE lines of a logging free-gate arm):
python3 freed.py BATCHGLOB"""
import glob, sys, zipfile, collections
from multiprocessing import Pool


def one(f):
    side = 'b' if f.rsplit('.', 1)[0].endswith('-21') else 'a'
    out = []
    try: text = zipfile.ZipFile(f).read(f'team-{side}.stdout').decode('utf-8', 'replace').replace('\x00', '')
    except Exception: return out
    for line in text.splitlines():
        if line.startswith('FREE '):
            v = line.split()
            try: out.append((v[1], int(v[4]), int(v[5])))
            except (ValueError, IndexError): pass
    return out


if __name__ == '__main__':
    files = sorted(f for g in sys.argv[1:] for f in glob.glob(g + '/*.repl26a'))
    with Pool(32) as pool: R = [r for g in pool.map(one, files, chunksize=16) for r in g]
    q = lambda u, p: u[min(len(u) - 1, int(p * len(u)))] if u else 0
    by = collections.defaultdict(list)
    for t, at, w in R: by[t].append((at, w))
    print(f'{len(files)} games')
    print('gate          a game   fuel left at the gate: p10 p50 p90    freed work: p50 p75 p90 p99    left - work: p10 p25 p50   work under 5k %, left-work over 10k %')
    for t, S in sorted(by.items(), key=lambda kv: -len(kv[1])):
        a = sorted(x for x, _ in S); w = sorted(y for _, y in S); d = sorted(x - y for x, y in S)
        print(f'{t:12s} {len(S) / len(files):7.2f}   {q(a, .1):6d} {q(a, .5):6d} {q(a, .9):6d}    {q(w, .5):6d} {q(w, .75):6d} {q(w, .9):6d} {q(w, .99):6d}    {q(d, .1):6d} {q(d, .25):6d} {q(d, .5):6d}   '
              f'{100 * sum(1 for y in w if y < 5000) / len(w):5.1f}  {100 * sum(1 for x in d if x > 10000) / len(d):5.1f}')
