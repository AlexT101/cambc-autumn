"""Live r7, our bodies near Mite's Vesper. Two row kinds to ~/tmp-offload/mitere/vdeath2.jsonl.gz:
- 'death' (her kills): the victim's last 5 rounds as actions (attack target, step toward/away from her, still,
  channel), her tile a bush or not, the victim's distance to its spawn;
- 'near' (every other round, each of our bodies within 6 of her at the round's start): health (absolute), her
  Strength, range, sight, numbers within 5, bag; outcome: she kills it within 5 rounds / it dies within 5.
Index i of rounds.json = end of round i+1, so round r starts at index r-2."""
import sys, os, json, gzip, collections
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ml
OUT = os.path.expanduser('~/tmp-offload/mitere/vdeath2.jsonl.gz')
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

def one(sd):
    g = ml.load(sd)
    if g is None: return []
    m = g['mite']; o = 1 - m; meta = g['meta']; rd = g['rd']; mp = g['map']
    name = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    C = {c['id']: c for c in rd['champions']}
    V = [c for c in name if team[c] == m and name[c] == 'Vesper Vale']
    if not V: return []
    v = V[0]; nR = len(rd['round'])
    bush = {tuple(b) for b in mp['bushes']}
    sp = mp['spawn'][o]; spc = ((sp['minX'] + sp['maxX']) / 2, (sp['minY'] + sp['maxY']) / 2)
    ours = [c for c in name if team[c] == o]; theirs = [c for c in name if team[c] == m]
    def at(c, i):
        cc = C[c]
        return (cc['x'][i], cc['y'][i]) if 0 <= i < nR and cc['alive'][i] and cc['x'][i] is not None else None
    act = collections.defaultdict(list)  # (unit, round) -> labels
    killed = {}  # victim -> rounds she killed it
    for e in g['ev']:
        a = e.get('a')
        if e['k'] == 'attack' and a in team: act[(a, e['r'])].append('atk:' + ('V' if e.get('tgt') == v else name.get(e.get('tgt'), 'camp')))
        elif e['k'] == 'cast' and a in team: act[(a, e['r'])].append('cast:' + e.get('ab', '?'))
        elif e['k'] in ('recall_start', 'tribute_start', 'teleport_start') and a in team: act[(a, e['r'])].append(e['k'])
        elif e['k'] == 'death' and e.get('by') == v and team.get(e.get('v')) == o: killed.setdefault(e['v'], []).append(e['r'])
    rows = []
    for vic, rs in killed.items():
        for r in rs:
            i0 = r - 2
            if i0 < 8: continue
            steps = []
            for k in range(5, -1, -1):
                i = i0 - k; a, b = at(vic, i - 1), at(vic, i); pV = at(v, i - 1)
                mv = 'gone' if not (a and b) else ('still' if a == b else ('?' if not pV else ('away' if cheb(b, pV) > cheb(a, pV) else 'toward' if cheb(b, pV) < cheb(a, pV) else 'side')))
                steps.append([mv] + act.get((vic, r - k - 1), []))
            pV = at(v, i0); pv = at(vic, i0)
            rows.append({'kind': 'death', 'mid': g['mid'], 'r': r, 'vic': name[vic], 'steps': steps,
                         'v_bush': bool(pV and pV in bush), 'v_bush3': [bool(at(v, i0 - k) and at(v, i0 - k) in bush) for k in range(4)],
                         'spawn_d': cheb(pv, spc) if pv else None, 'vdist': cheb(pv, pV) if pv and pV else None,
                         'seen': [v in (C[vic]['sees'][i0 - k] or []) for k in range(4)]})
    for i in range(10, nR - 6, 2):
        pV = at(v, i)
        if not pV: continue
        for c in ours:
            p = at(c, i)
            if not p or cheb(p, pV) > 6: continue
            cc = C[c]; r = i + 2
            kill5 = any(r <= x <= r + 4 for x in killed.get(c, []))
            die5 = any(not cc['alive'][i + k] for k in range(1, 6))
            rows.append({'kind': 'near', 'vic': name[c], 'hp': cc['hp'][i], 'hpf': cc['hp'][i] / cc['maxHp'][i], 'vstr': C[v]['str'][i],
                         'vhpf': C[v]['hp'][i] / C[v]['maxHp'][i], 'd': cheb(p, pV), 'seen': v in (cc['sees'][i] or []),
                         'm5': sum(1 for x in theirs if at(x, i) and cheb(at(x, i), p) <= 5),
                         'o5': sum(1 for x in ours if x != c and at(x, i) and cheb(at(x, i), p) <= 5),
                         'gems': cc['gems'][i], 'vbush': pV in bush, 'cd0': C[v]['cd0'][i], 'cd1': C[v]['cd1'][i],
                         'kill5': kill5, 'die5': die5, 'r': r})
    return rows

if __name__ == '__main__':
    n = collections.Counter()
    with Pool(8) as P, gzip.open(OUT, 'wt') as f:
        for rr in P.imap_unordered(one, ml.dirs('live'), chunksize=4):
            for x in rr: f.write(json.dumps(x) + '\n'); n[x['kind']] += 1
    print(dict(n), OUT)
