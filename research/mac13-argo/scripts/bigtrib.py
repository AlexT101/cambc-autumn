"""Big tributes (100+ gems): outcome, progress at cancel, allies/enemies near at start and at the end, the canceller,
altar distance to each spawn. Split by whether the team had reached 1000 wealth (team tributed + carried) at start.
    py bigtrib.py ANALYSIS_DIR"""
import gzip, json, sys, statistics as st
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))

def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        mp = json.loads((d / meta['mapFile']).resolve().read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return []
    w = meta['result']['winner']
    rid = {r: i for i, r in enumerate(R['round'])}
    C = R['champions']; team = {c['id']: c['team'] for c in C}; idx = {c['id']: i for i, c in enumerate(C)}
    name = {c['id']: c['name'] for c in meta['champions']}
    sp = mp['spawn']
    def spc(t): s = sp[t]; return ((s['minX']+s['maxX'])/2, (s['minY']+s['maxY'])/2)
    def pos(cid, i):
        c = C[idx[cid]]
        if i < 0 or not c['alive'][i] or c['x'][i] is None: return None
        return (c['x'][i], c['y'][i])
    def wealth(t, i):
        v = R['gems'][t][i]
        for c in C:
            if c['team'] == t and c['alive'][i]: v += c['gems'][i]
        return v
    out = []; open_ = {}
    last_stun = {}  # victim -> (round, attacker)
    for e in ev:
        k = e['k']
        if k in ('cast', 'attack') and e.get('stun'):
            for v in e['stun']: last_stun[v] = (e['r'], e.get('a'))
        if k == 'tribute_start' and e['gems'] >= 100:
            a = e['a']; t = team[a]; i = rid.get(e['r'] - 1, 0)
            p = tuple(e['at']) if e.get('at') else pos(a, i)
            if p is None: continue
            al = sum(1 for c in C if c['team'] == t and c['id'] != a and pos(c['id'], i) and cheb(pos(c['id'], i), p) <= 6)
            en = sum(1 for c in C if c['team'] != t and pos(c['id'], i) and cheb(pos(c['id'], i), p) <= 8)
            alt = min(mp['altars'], key=lambda q: cheb(q, p))
            open_[a] = dict(won=(t == w), name=name[a], gems=e['gems'], dur=e['dur'], r=e['r'], allies6=al, enemies8=en,
                            rich=wealth(t, i) >= 1000, d_own=cheb(alt, spc(t)), d_en=cheb(alt, spc(1-t)), altars=len(mp['altars']))
        elif k in ('tribute_end', 'tribute_cancel') and e.get('a') in open_:
            o = open_.pop(e['a'])
            o['done'] = k == 'tribute_end'
            o['cause'] = e.get('cause') if k != 'tribute_end' else None
            o['ran'] = e['r'] - o['r']
            if o['cause'] == 'stun':
                s = last_stun.get(e['a'])
                o['by'] = name.get(s[1]) if s and s[0] == e['r'] else None
            i = rid.get(e['r'] - 1, 0)
            out.append(o)
    return out

if __name__ == '__main__':
    root = Path(sys.argv[1])
    dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(one, dirs, chunksize=16): rows += r
    json.dump(rows, open('/home/ubuntu/wt/mac13-argo/research/mac13-argo/data/bigtrib.json', 'w'))
    for rich in (True, False):
        for won in (True, False):
            S = [r for r in rows if r['rich'] == rich and r['won'] == won]
            if not S: continue
            done = [r for r in S if r['done']]
            print(f"rich={rich} winner={won}: {len(S)} starts, {100*len(done)/len(S):.0f}% complete; median gems {st.median(r['gems'] for r in S)}, dur {st.median(r['dur'] for r in S)}")
            print('   causes', Counter(r['cause'] for r in S if not r['done']).most_common())
            canc = [r for r in S if not r['done']]
            if canc: print('   cancelled after median', st.median(r['ran'] for r in canc), 'rounds; progress share', round(st.median(r['ran']/r['dur'] for r in canc), 2))
            print('   stunners', Counter(r.get('by') for r in S if r['cause'] == 'stun').most_common(6))
            for key in ('allies6', 'enemies8'):
                c = Counter(min(r[key], 3) for r in S)
                print(f'   {key}:', {k: f"{c[k]} ({100*sum(1 for r in S if min(r[key],3)==k and r['done'])/max(1,c[k]):.0f}% done)" for k in sorted(c)})
            print('   altar nearer own spawn', sum(1 for r in S if r['d_own'] < r['d_en']), 'of', len(S), '; done there', sum(1 for r in S if r['d_own'] < r['d_en'] and r['done']))
