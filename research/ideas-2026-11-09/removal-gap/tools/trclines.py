"""Trace lines of bot 0 (CAND) per game of a batch: {stem: [line...]}, for each prefix. usage: trclines.py BATCH PREFIX OUT.json"""
import zipfile, json, sys, os
from multiprocessing import Pool
B, P, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
def run(f):
    stem = f.split('-', 1)[1].rsplit('.', 1)[0]; team = 'a' if stem.endswith('-12') else 'b'
    try:
        with zipfile.ZipFile(os.path.join(B, f)) as z:
            name = [n for n in z.namelist() if n.endswith(f'team-{team}.stdout')]
            txt = z.read(name[0]).decode(errors='replace') if name else ''
    except Exception: return (stem, None)
    return (stem, [l for l in txt.splitlines() if any(l.startswith(q) for q in P.split(','))])
if __name__ == '__main__':
    fs = [f for f in os.listdir(B) if f.endswith('.repl26a')]
    with Pool(32) as p: res = dict(p.map(run, fs, chunksize=8))
    json.dump(res, open(OUT, 'w'))
    n = sum(len(v) for v in res.values() if v); g = sum(1 for v in res.values() if v)
    print(f'{len(fs)} games, {g} with {P}, {n} lines, {n/len(fs):.2f}/game')
