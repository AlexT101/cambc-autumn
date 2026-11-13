"""Branch letters of the D trace lines per champion type (debug replays): share of a type's traced turns.
Usage: py branches.py BATCH_DIR [N]"""
import sys, zipfile, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

def one(f):
    z = zipfile.ZipFile(f)
    res = json.loads(z.read('replay.repl26a')[:0] or b'{}') if False else None
    out = collections.Counter(); rf = collections.Counter()
    for side in ('a', 'b'):
        try: s = z.read(f'team-{side}.stdout').decode(errors='replace').splitlines()
        except KeyError: continue
        for l in s:
            l = l.lstrip('\x00')
            if l.startswith('D '):
                p = l.split()
                if len(p) >= 4: out[(side, int(p[2]), p[3])] += 1
            elif l.startswith('RFKEEP'):
                p = l.split(); rf[(side, int(p[2]))] += 1
    return f.name, out, rf

def main():
    b = Path(sys.argv[1]); n = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    files = sorted(b.glob('*-12.repl26a'))[:n]
    # champion ids -> type: picks from results.json are not per-id; read the draft from the D-line ids via the
    # analysis index instead: here use the game's map of ids from the extracted meta when present.
    import gzip, hashlib
    idx = json.load(open('replays/ana-mirror/index.json'))['games']
    by_src = {Path(g['source']).name: g['dir'] for g in idx}
    T = collections.Counter(); TT = collections.Counter(); RF = collections.Counter()
    with ProcessPoolExecutor(24) as ex:
        for name, out, rf in ex.map(one, files, chunksize=4):
            d = by_src.get(name)
            if not d: continue
            meta = json.load(open(Path('replays/ana-mirror') / d / 'meta.json'))
            ch = meta['champions']
            for (side, cid, br), k in out.items():
                team = 0 if side == 'a' else 1
                tch = [c for c in ch if c['team'] == team]
                if cid < len(ch):
                    c = next((c for c in ch if c['id'] == cid), None)
                    if c is None: continue
                    T[(c['name'], br)] += k; TT[c['name']] += k
            for (side, cid), k in rf.items():
                c = next((c for c in ch if c['id'] == cid), None)
                if c: RF[c['name']] += k
    for n_ in sorted(TT, key=lambda x: -TT[x]):
        row = sorted(((br, k) for (nm, br), k in T.items() if nm == n_), key=lambda x: -x[1])
        print(f'{n_:13s} {TT[n_]:7d}', ' '.join(f'{br}:{100*k/TT[n_]:.1f}' for br, k in row[:12]), f' RFKEEP {RF[n_]}')

if __name__ == '__main__':
    main()
