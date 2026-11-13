"""Early lead: at round T (default 100, 150), decompose the eventual winner's gem lead (tributed+carried) into
captures and kill transfers; how often the r-T leader wins, by source of its lead.
usage: py early.py EXTRACT_ROOT [T ...]"""
import json, gzip, glob, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
ROOT = sys.argv[1]
TS = [int(x) for x in sys.argv[2:]] or [100, 150, 250]
def one(d):
    meta = json.load(open(d + '/meta.json'))
    w = meta['result']['winner']
    team = {c['id']: c['team'] for c in meta['champions']}
    cap = {T: [0, 0] for T in TS}; kill = {T: [0, 0] for T in TS}; deaths = {T: [0, 0] for T in TS}
    capn = {T: [0, 0] for T in TS}
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l); r = e['r']
        for T in TS:
            if r > T: continue
            if e['k'] == 'capture':
                for cid, gm, gd in e['shares']:
                    cap[T][team[cid]] += gm
                capn[T][team[e['shares'][0][0]]] += 1
            elif e['k'] == 'death':
                tv = team[e['v']]; deaths[T][tv] += 1
                if e.get('by') is not None:
                    kill[T][1 - tv] += e.get('gems', 0); kill[T][tv] -= e.get('gems', 0)
    return w, cap, kill, deaths, capn
if __name__ == '__main__':
    ds = [os.path.dirname(p) for p in glob.glob(ROOT + '/*/meta.json')]
    with ProcessPoolExecutor(32) as ex:
        S = list(ex.map(one, ds, chunksize=8))
    for T in TS:
        n = len(S); lead_cap = []; agg = collections.Counter(); wins = collections.Counter()
        for w, cap, kill, deaths, capn in S:
            L = 1 - w
            c = cap[T][w] - cap[T][L]; k = kill[T][w] - kill[T][L]
            lead_cap.append((c, k, deaths[T][w] - deaths[T][L], capn[T][w] - capn[T][L]))
            tot = c + k
            key = 'tot>25' if tot > 25 else 'tot<-25' if tot < -25 else 'level'
            agg[key] += 1
            # who leads by captures alone, kills alone
            for nm, v in (('cap', c), ('kill', k)):
                if abs(v) > 15:
                    wins[nm + ('+' if v > 0 else '-')] += 1
        import statistics as st
        print('r%d: winner-minus-loser captures %.1f, kill transfers %.1f, deaths %.2f, capture count %.2f' % (
            T, st.mean(x[0] for x in lead_cap), st.mean(x[1] for x in lead_cap), st.mean(x[2] for x in lead_cap), st.mean(x[3] for x in lead_cap)))
        print('   leader wins (gem lead >25):', agg['tot>25'], 'loses', agg['tot<-25'], 'level', agg['level'])
        print('   by capture lead >15: winner had it %d, loser had it %d; by kill lead >15: winner %d, loser %d' % (
            wins['cap+'], wins['cap-'], wins['kill+'], wins['kill-']))
        anydeath = sum(1 for w, cap, kill, deaths, capn in S if deaths[T][0] + deaths[T][1] > 0)
        print('   games with any death by r%d: %d of %d' % (T, anydeath, n))
