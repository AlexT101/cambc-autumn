"""Champion time by activity, rounds <= END, solo extracts (the non-idle team): dead, recall (real recalls: the
channel rounds before a recall_end), tribute, hold (on a camp tile of a group our team is capturing), clear (dealt
camp damage), walk, still. Holds are split by whether a live camp of another rewarded group was within the holder's
attack range (overlap potential) and whether another ally was also on the group's tiles (redundant holder).
usage: py fthru_time.py EXTRACT [END]"""
import json, gzip, glob, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
A = sys.argv[1]; END = int(sys.argv[2]) if len(sys.argv) > 2 else 600
E = json.load(open(A + '/enums.json')); CH = E['champions']
MELEE = {'Ryth', 'Vendetta', 'Marcella', 'Ren', 'Varg', 'Heart of Ruin', 'Issac'}


def one(d):
    m = json.load(open(d + '/meta.json'))
    mp = json.load(open(os.path.join(d, m['mapFile'])))
    typ = {c['id']: CH[c['type']] for c in m['champions']}
    R = json.load(gzip.open(d + '/rounds.json.gz')); rr = R['round']; ri = {r: i for i, r in enumerate(rr)}
    team = None
    for t in m['teams']:
        pass
    team = 0 if m['teams'][0]['name'] != 'idle' else 1
    groups = mp['groups']; camps = mp['camps']
    tile_group = {}
    for g in groups:
        for t in g['tiles']: tile_group[tuple(t)] = g['id']
    camp_pos = {c['id']: (c['x'], c['y'], c['group']) for c in camps}
    reward = {g['id']: g['gems'] + g['gold'] for g in groups}
    # group state per round: rows only on change
    gs = collections.defaultdict(dict)
    for row in R['groups']:
        gs[row[1]][row[0]] = row
    n = len(rr)
    state = {}
    for g in gs:
        cur = None; arr = []
        rows = gs[g]
        for r in rr:
            if r in rows: cur = rows[r]
            arr.append(cur)
        state[g] = arr
    # per-camp alive: from camp_death/group_respawn events
    dmg = collections.defaultdict(set)
    recall_rounds = collections.defaultdict(set)
    camp_dead_round = {}
    alive_camp = {c['id']: True for c in camps}
    camp_alive_at = collections.defaultdict(list)  # rounds when camp dies / respawns
    ev = []
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['r'] > END: break
        ev.append(e)
        k = e['k']
        if k in ('attack', 'cast') and e.get('cdmg'): dmg[e['a']].add(e['r'])
        elif k == 'recall_end':
            for q in range(e['r'] - 5, e['r']): recall_rounds[e['a']].add(q)
    # camp liveness per round
    deaths = collections.defaultdict(list)
    for e in ev:
        if e['k'] == 'camp_death': deaths[e['camp']].append(e['r'])
    out = collections.Counter()
    ours = [c for c in R['champions'] if c['team'] == team]
    for c in ours:
        ty = typ[c['id']]; rng = 1 if ty in MELEE else 3
        for i, r in enumerate(rr):
            if r > END: break
            if not c['alive'][i]: k = 'dead'
            elif r in recall_rounds[c['id']]: k = 'recall'
            elif c['chan'][i] == 2: k = 'tribute'
            else:
                p = (c['x'][i], c['y'][i])
                g = tile_group.get(p)
                row = state[g][i] if g is not None and g in state else None
                if row and row[2] == 2 and row[3] == team:
                    k = 'hold'
                    others = sum(1 for o in ours if o is not c and o['alive'][i] and tile_group.get((o['x'][i], o['y'][i])) == g)
                    # a live camp of another rewarded group in range
                    near = False
                    for cid, (x, y, h) in camp_pos.items():
                        if h == g or reward[h] <= 0: continue
                        if max(abs(x - p[0]), abs(y - p[1])) > rng: continue
                        hr = state[h][i] if h in state else None
                        if hr and hr[2] == 1 and hr[7] > 0: near = True; break
                    out[(ty, 'hold-near' if near else 'hold')] += 1
                    out[('all', 'hold-near' if near else 'hold')] += 1
                    if others: out[(ty, 'hold-redundant')] += 1; out[('all', 'hold-redundant')] += 1
                    continue
                elif r in dmg[c['id']]: k = 'clear'
                elif i > 0 and c['x'][i - 1] is not None and p != (c['x'][i - 1], c['y'][i - 1]): k = 'walk'
                else: k = 'still'
            out[(ty, k)] += 1; out[('all', k)] += 1
    return out


if __name__ == '__main__':
    ds = [os.path.dirname(p) for p in glob.glob(A + '/*/meta.json')]
    tot = collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one, ds, chunksize=8): tot.update(o)
    K = ('walk', 'clear', 'hold', 'hold-near', 'still', 'recall', 'tribute', 'dead')
    for ty in ['all', 'Prism', 'Vesper Vale', 'Cassi', 'Issac', 'Willow', 'Ryth', 'Vendetta', 'Marcella', 'Varg', 'Stellar', 'Tavi', 'Ren', 'Heart of Ruin']:
        s = sum(tot[(ty, k)] for k in K)
        if s: print('%-12s' % ty, ' '.join('%s %.1f%%' % (k, 100 * tot[(ty, k)] / s) for k in K), ' redundant-hold %.1f%%' % (100 * tot[(ty, 'hold-redundant')] / s))
