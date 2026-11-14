# 470's mechanism on one-site maps, paired by (member, map, side): opponent gems by round 600, our early locks and the
# opponent's lock hits, CAND run minus REF run (of-<tag>-<member> batches extracted into ANA_DIR).
#   py op600.py ANA_DIR CANDTAG REFTAG      (live: op600 +28 +-23, our early locks 3.1 -> 0.5)
import json, os, re, sys, math, collections
from pathlib import Path
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import episodes as E, fid
def main():
    ana, ct, rt = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    jobs = []
    for g in json.load(open(ana / 'index.json'))['games']:
        m = re.search(rf'of-({ct}|{rt})-(spar-[^/]+)-ladder/\d+-(.+)-(12|21)\.repl26a$', g['source'])
        if m and E.MC.get(m[3].replace('-', '_')) == 'one':
            jobs.append(((m[1], m[2], m[3], m[4]), str(ana / g['dir']), 0 if m[4] == '12' else 1))
    with Pool(int(os.environ.get('OMP_NUM_THREADS', 8))) as P: res = dict(P.map(fid.job, jobs, chunksize=2))
    d = collections.defaultdict(list)
    for (t, mem, mp, sd), r in res.items():
        if t != ct or 'err' in r: continue
        q = res.get((rt, mem, mp, sd))
        if not q or 'err' in q: continue
        kind = 'Fish' if mem.endswith(('-F', '-Fl')) else 'Mite'
        body = 'new' if mem.endswith(('-Fl', '-Mt3')) else 'old' if mem.endswith(('-F', '-M')) else mem
        for k in (f'{body} {kind}', f'{body} all'):
            d[(k, 'op600')].append(r['op600'] - q['op600']); d[(k, 'us600')].append(r['us600'] - q['us600'])
            d[(k, 'our locks')].append(r['locks']['lock_us'] - q['locks']['lock_us'])
            d[(k, 'win')].append(100 * (r['win'] - q['win']))
    for k in sorted(d):
        v = d[k]; n = len(v); mu = sum(v) / n; sd = (sum((a - mu) ** 2 for a in v) / n) ** .5
        print(f'{k[0]:9s} {k[1]:10s} n {n:4d}  {ct}-{rt} {mu:+7.2f} ±{1.96*sd/math.sqrt(n):.2f}')

if __name__ == '__main__':
    main()
