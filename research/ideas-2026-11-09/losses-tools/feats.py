"""Per-game features of the oc32 line's games against the noise bodies (diverse agent, loss analysis).
    python3 feats.py BATCHES_TXT OUT.jsonl
BATCHES_TXT lines: k opp batch_dir. Our side is bot 1 (`-12`: team A). Every feature is (ours, theirs)."""
import sys, os, json, gzip, collections
from multiprocessing import Pool
R = '/home/ubuntu/cambc-autumn/'; A = R + 'replays/.analysis/'
CK = (150, 300, 600, 900, 1200)

def feats(arg):
    d, src, k, opp = arg
    meta = json.load(open(A + d + '/meta.json')); rd = json.load(gzip.open(A + d + '/rounds.json.gz'))
    us = 0 if src.endswith('-12.repl26a') else 1; th = 1 - us
    rr = rd['round']; idx = {r: i for i, r in enumerate(rr)}
    def at(r): return idx.get(r, len(rr) - 1)
    f = {'map': meta['map']['name'], 'side': 'a' if us == 0 else 'b', 'k': k, 'opp': opp,
         'win': meta['result']['winner'] == us, 'rounds': meta['result']['rounds']}
    team = {c['id']: c['team'] for c in meta['champions']}
    f['ours'] = sorted(c['name'] for c in meta['champions'] if c['team'] == us)
    f['theirs'] = sorted(c['name'] for c in meta['champions'] if c['team'] == th)
    for r in CK:
        i = at(r)
        f[f'trib{r}'] = (rd['gems'][us][i], rd['gems'][th][i])
        ch = rd['champions']
        f[f'earn{r}'] = tuple(sum(c['earned'][i] for c in ch if c['team'] == t) for t in (us, th))
        f[f'carry{r}'] = tuple(sum(c['gems'][i] for c in ch if c['team'] == t) for t in (us, th))
    ev = [json.loads(l) for l in gzip.open(A + d + '/events.jsonl.gz', 'rt')]
    cnt = collections.Counter()
    for e in ev:
        k_ = e['k']; r = e['r']; w = 'e' if r <= 600 else 'l'  # early (<=600) / late
        if k_ == 'death':
            t = 'u' if team[e['v']] == us else 't'
            cnt[f'death_{t}{w}'] += 1; cnt[f'baglost_{t}{w}'] += e.get('gems', 0)
            if 'camp' in e: cnt[f'campdeath_{t}{w}'] += 1
        elif k_ in ('tribute_cancel', 'recall_cancel'):
            t = 'u' if team[e['a']] == us else 't'
            if e.get('cause') != 'manual': cnt[f'{k_}_{t}{w}'] += 1; cnt[f'{k_}gems_{t}{w}'] += e.get('gems', 0)
        elif k_ == 'tribute_end':
            t = 'u' if team[e['a']] == us else 't'; cnt[f'tribs_{t}{w}'] += 1
        elif k_ == 'capture':
            t = 'u' if e['team'] == us else 't'; cnt[f'capt_{t}{w}'] += 1
        elif k_ == 'lock_place':
            t = 'u' if e['team'] == us else 't'; cnt[f'lock_{t}{w}'] += 1
        elif k_ == 'tribute_blocked':
            t = 'u' if team[e['a']] == us else 't'; cnt[f'blocked_{t}{w}'] += 1
    f['ev'] = dict(cnt)
    return f

if __name__ == '__main__':
    idxj = json.load(open(A + 'index.json'))['games']
    B = {}
    for l in open(sys.argv[1]):
        k, o, b = l.split(); B[os.path.relpath(R + b, R) if not b.startswith('/') else os.path.relpath(b, R)] = (int(k), o)
    args = []
    for g in idxj:
        b = os.path.dirname(g['source'])
        if b in B and g['ok']: args.append((g['dir'], g['source'], *B[b]))
    with Pool(32) as p, open(sys.argv[2], 'w') as out:
        for f in p.imap_unordered(feats, args, chunksize=8): out.write(json.dumps(f) + '\n')
    print(len(args), 'games')
