"""Per champion, per side (M = opponent team, O = us): stats/earned at checkpoints, shards by family+stat to R, kills/deaths.
env: MA decoded dir, MF feats.jsonl, LO start time, OPP our name, MSIDE key."""
import gzip, json, os, collections, sys, re
from multiprocessing import Pool
A = os.environ['MA']; F = os.environ['MF']; R = int(os.environ.get('RCUT', 600))
G = [json.loads(l) for l in open(F)]
G = list({g['mid']: g for g in G if 'err' not in g}.values())
CP = (200, 400, 600, 800)
def parse(it):
    m = re.match(r'(.*) (Shard|Emblem) of (Strength|Focus|Health)', it)
    if not m: return None
    fam, kind, st = m.groups(); n = 1 if kind == 'Shard' else (25 if fam == 'Greed' else 5)
    return fam, st[0], n
def one(g):
    d = g['dir']; meta = json.load(open(f'{A}/{d}/meta.json'))
    ms = g[os.environ.get('MSIDE', 'ms')]
    rd = json.load(gzip.open(f'{A}/{d}/rounds.json.gz')); Rr = rd['round']; idx = {r: i for i, r in enumerate(Rr)}
    nm = {c['id']: c['name'] for c in meta['champions']}; tm = {c['id']: c['team'] for c in meta['champions']}
    C = collections.Counter()
    side = lambda cid: 'M' if tm[cid] == ms else 'O'
    for c in meta['champions']:
        k = (side(c['id']), c['name']); C[k + ('n',)] += 1
        C[k + ('kills',)] += c['stats']['kills']; C[k + ('deaths',)] += c['stats']['deaths']
    for c in rd['champions']:
        k = (side(c['id']), nm[c['id']])
        for r in CP:
            i = idx.get(r)
            if i is None or c['foc'][i] is None: continue
            kk = k + (r,); C[kk + ('n',)] += 1
            for f in ('str', 'foc', 'maxHp', 'earned'): C[kk + (f,)] += c[f][i]
    for l in gzip.open(f'{A}/{d}/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] == 'death' and e['r'] <= R:
            C[(side(e['a']) if 'a' in e else '?', nm.get(e.get('a'), '?'), 'dR')] += 1
        if e['k'] != 'shop' or e['r'] > R: continue
        k = (side(e['a']), nm[e['a']])
        for it, n in (e.get('items') or {}).items():
            p = parse(it)
            if p: C[k + ('sh', p[0], p[1])] += n * p[2]; C[k + ('st', p[1])] += n * p[2]
    return C
if __name__ == '__main__':
    L = [g for g in G if g['cr'] >= os.environ.get('LO', '2026-11-09T12') and g.get(os.environ.get('OPPK', 'opp')) == os.environ.get('OPP', 'stellar best girl')]
    if os.environ.get('HI'): L = [g for g in L if g['cr'] < os.environ['HI']]
    T = collections.Counter()
    with Pool(int(os.environ.get('NP', 8))) as p:
        for c in p.imap_unordered(one, L, chunksize=4): T.update(c)
    json.dump({'|'.join(map(str, k)): v for k, v in T.items()}, open(os.environ.get('OUT', '/dev/null'), 'w'))
    print('games', len(L))
    champs = sorted({k[1] for k in T if k[0] in 'MO'})
    for ch in champs:
        for s in 'MO':
            n = T[(s, ch, 'n')]
            if n < 30: continue
            row = [f"{s} {ch:14s} n={n:5d} K/D {T[(s,ch,'kills')]/n:.2f}/{T[(s,ch,'deaths')]/n:.2f}"]
            for r in CP:
                m = T[(s, ch, r, 'n')]
                if m >= 20: row.append(f"r{r}: S{T[(s,ch,r,'str')]/m:.0f} F{T[(s,ch,r,'foc')]/m:.0f} H{T[(s,ch,r,'maxHp')]/m:.0f} g{T[(s,ch,r,'earned')]/m:.0f}")
            print(' | '.join(row))
            st = {x: T[(s, ch, 'st', x)] / n for x in 'SFH'}
            fams = sorted(((v / n, k[3] + '-' + k[4]) for k, v in T.items() if k[:3] == (s, ch, 'sh') and v / n >= 1.0), reverse=True)
            print(f"    shards<=r{R} S/F/H {st['S']:.1f}/{st['F']:.1f}/{st['H']:.1f}  " + ' '.join(f'{f}:{v:.1f}' for v, f in fams))
