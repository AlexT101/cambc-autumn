"""Where the Focus gap comes from: in Prism games at round M, the leading vs trailing Prism's capture gems, kill gems,
tributed (banked) gems and gems lost by its own deaths, up to M. Usage: py focus_src.py DIR [M]"""
import gzip, json, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
M = int(sys.argv[2]) if len(sys.argv) > 2 else 200

def game(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text())
        R = json.load(gzip.open(d/'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    pid = [m['id'] for m in meta['champions'] if m['name'] == 'Prism']
    if len(pid) != 2: return None
    rix = {r: i for i, r in enumerate(R['round'])}
    i = rix.get(M)
    if i is None: return None
    idx = {c['id']: k for k, c in enumerate(R['champions'])}
    foc = {p: R['champions'][idx[p]]['foc'][i] for p in pid}
    s = {p: defaultdict(float) for p in pid}
    for e in ev:
        if e['r'] > M: break
        if e['k'] == 'capture':
            for cid, gems, gold in e['shares']:
                if cid in s: s[cid]['capture'] += gems; s[cid]['caps'] += 1
        elif e['k'] == 'death':
            if e.get('by') in s and not e.get('linked'): s[e['by']]['kill'] += e.get('gems', 0)
            if e['v'] in s: s[e['v']]['lost'] += e.get('gems', 0); s[e['v']]['deaths'] += 1
        elif e['k'] == 'tribute_end' and e['a'] in s:
            s[e['a']]['banked'] += e.get('gems', 0)
    hi, lo = sorted(pid, key=lambda p: -foc[p])
    ratio = foc[hi] / max(1, foc[lo])
    return ratio, dict(s[hi]), dict(s[lo])

def main():
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]
    B = defaultdict(lambda: [0, defaultdict(float), defaultdict(float)])
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(game, dirs, chunksize=4):
            if not o: continue
            r, h, l = o
            b = '1-1.2' if r < 1.2 else '1.2-1.5' if r < 1.5 else '1.5+'
            B[b][0] += 1
            for k, v in h.items(): B[b][1][k] += v
            for k, v in l.items(): B[b][2][k] += v
    for b in ('1-1.2', '1.2-1.5', '1.5+'):
        n, h, l = B[b]
        if not n: continue
        keys = ('capture', 'caps', 'kill', 'lost', 'deaths', 'banked')
        print(f'r{M} ratio {b} n={n}: lead', ' '.join(f'{k} {h[k]/n:.1f}' for k in keys), '| trail', ' '.join(f'{k} {l[k]/n:.1f}' for k in keys))

if __name__ == '__main__':
    main()
