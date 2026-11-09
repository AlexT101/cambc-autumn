"""Per-side priority dataset from extracted replays (tools/replay/extract.mjs output).

For each game side X: roster (types in pick order), the full priority change list, and every
(round, champion) where the other side saw that champion at a turn start, with the champion's
state at the end of the previous round (what it saw when it wrote the value it shows now).

usage: build_ds.py ANALYSIS_DIR MANIFEST.tsv OUT.pkl [--threads N]
MANIFEST columns: match_id created_at name_a name_b (extra columns ignored); header optional.
"""
import gzip, json, os, pickle, sys
from multiprocessing import Pool

import numpy as np

def load_manifest(p):
    out = {}
    for l in open(p):
        f = l.rstrip('\n').split('\t')
        if f[0] == 'match_id': continue
        out[f[0]] = f
    return out

def one(args):
    d, mid = args
    try:
        m = json.load(open(os.path.join(d, 'meta.json')))
        R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
    except Exception as e:
        return None
    rounds = R['round']
    ch = R['champions']
    ids = [c['id'] for c in ch]
    res = []
    for side in (0, 1):
        mine = [k for k, c in enumerate(ch) if c['team'] == side]
        theirs = [k for k, c in enumerate(ch) if c['team'] != side]
        roster = [m['champions'][k]['name'] for k in mine]
        types = [m['champions'][k]['type'] for k in mine]
        # prio[k][i]: value written in round rounds[i], used from rounds[i]+1
        changes = []
        for j, k in enumerate(mine):
            last = 0
            for i, v in enumerate(ch[k]['prio']):
                if v != last:
                    changes.append((rounds[i], j, v)); last = v
        obs = []
        idpos = {ids[k]: j for j, k in enumerate(mine)}
        for i in range(1, len(rounds)):
            r = rounds[i]
            seen = {}
            for o, k in enumerate(theirs):
                for e in ch[k]['sees'][i]:
                    if e in idpos: seen[idpos[e]] = seen.get(idpos[e], 0) | (1 << o)
            for j, mask in seen.items():
                k = mine[j]; p = i - 1  # state at end of round r-1
                c = ch[k]
                obs.append((r, j, c['prio'][p], mask, c['hp'][p], c['maxHp'][p], c['gems'][p], c['shield'][p],
                            c['alive'][p], c['chan'][p], c['chanT'][p], c['stun'][p]))
        res.append(dict(mid=mid, dir=os.path.basename(d.rstrip('/')), side=side, roster=roster, types=types,
                        opp_roster=[m['champions'][k]['name'] for k in theirs],
                        pickIds=m['draft']['pickIds'][side], opp_pickIds=m['draft']['pickIds'][1 - side],
                        map=m['map']['name'], rounds=rounds[-1], winner=m['result']['winner'],
                        changes=np.array(changes, dtype=np.int64).reshape(-1, 3),
                        obs=np.array(obs, dtype=np.float64).reshape(-1, 12)))
    return res

def main():
    an, man, out = sys.argv[1:4]
    th = int(sys.argv[sys.argv.index('--threads') + 1]) if '--threads' in sys.argv else 8
    M = load_manifest(man)
    jobs = {}
    for dd in os.listdir(an):
        p = os.path.join(an, dd, 'meta.json')
        if not os.path.exists(p) or not os.path.exists(os.path.join(an, dd, 'rounds.json.gz')): continue
        meta = json.load(open(p))
        for src in meta.get('sources', [{'source': meta['source']}]):
            mid = os.path.basename(src['source']).split('.')[0]
            if mid in M: jobs[mid] = os.path.join(an, dd)
    with Pool(th) as pool:
        rows = []
        for r in pool.imap_unordered(one, [(d, mid) for mid, d in jobs.items()], chunksize=8):
            if r is None: continue
            for s in r:
                f = M[s['mid']]
                s['created'] = f[1]
                s['team'] = f[2] if s['side'] == 0 else f[3]
                s['opp'] = f[3] if s['side'] == 0 else f[2]
                rows.append(s)
    pickle.dump(rows, open(out, 'wb'))
    print(len(rows), 'sides')

if __name__ == '__main__':
    main()
