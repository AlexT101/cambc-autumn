# For each champion-on-champion damage event, distance from attacker to victim at the end of the
# victim's previous turn, and the number of attacker turns in between. Tests whether a single-turn
# reach model (as in morgana Safety) misses hits from enemies that get two turns (same rank).
import json, gzip, sys, os, collections
from concurrent.futures import ProcessPoolExecutor
ROOT = r'C:\Users\alext\Github\cambc-autumn\replays\.analysis'
MELEE = {'Ryth','Vendetta','Marcella','Ren','Varg','Issac'}
DASH = {'Vesper Vale','Vendetta','Ren','Issac'}

def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))

def game(d):
    try:
        m = json.load(open(os.path.join(ROOT, d, 'meta.json'), encoding='utf-8'))
        ev = [json.loads(l) for l in gzip.open(os.path.join(ROOT, d, 'events.jsonl.gz'), 'rt')]
        R = json.load(gzip.open(os.path.join(ROOT, d, 'rounds.json.gz')))
    except Exception as e:
        return None
    champs = m['champions']; ids = [c['id'] for c in champs]
    name = {c['id']: c['name'] for c in champs}; team = {c['id']: c['team'] for c in champs}
    idx = {c['id']: i for i, c in enumerate(champs)}
    rounds = R['round']; rix = {r: i for i, r in enumerate(rounds)}
    nA = sum(1 for c in champs if c['team'] == 0); nB = len(champs) - nA
    # slot of each champion per round from priorities (end of previous round), checked against events
    def order(r):
        pi = rix.get(r - 1)
        def key(c):
            p = R['champions'][idx[c]]['prio'][pi] if pi is not None else 0
            return (-p, c)
        A = sorted([c for c in ids if team[c] == 0], key=key); B = sorted([c for c in ids if team[c] == 1], key=key)
        first, second = (A, B) if r % 2 == 1 else (B, A)
        seq = []
        for i in range(max(len(A), len(B))):
            if i < len(first): seq.append(first[i])
            if i < len(second): seq.append(second[i])
        return {c: k for k, c in enumerate(seq)}, {c: (A.index(c) if team[c]==0 else B.index(c)) for c in ids}
    slots = {}; ranks = {}
    ok = bad = 0
    for e in ev:
        r = e['r']
        if r not in slots: slots[r], ranks[r] = order(r)
        if e['t'] >= 0 and 'a' in e and e['k'] in ('move','attack','cast','ward','recall_start'):
            if slots[r].get(e['a']) == e['t']: ok += 1
            else: bad += 1
    # positions at the end of each (round, slot)
    pos = {}
    for c in ids:
        i = idx[c]; ch = R['champions'][i]
    snaps = {}
    cur = {}
    def sync(r):  # end of round r state
        i = rix.get(r)
        if i is None: return
        for c in ids:
            ch = R['champions'][idx[c]]
            cur[c] = (ch['x'][i], ch['y'][i]) if ch['alive'][i] else None
    evs = sorted(ev, key=lambda e: e['s'])
    k = 0; out = []
    maxr = rounds[-1]
    dashes = collections.defaultdict(list)
    for e in evs:
        if e['k'] == 'cast' and e.get('ab') == 'Dash': dashes[e['a']].append((e['r'], e['t']))
    # first-round positions: from first move 'f'
    for e in evs:
        if e['k'] == 'move' and e['a'] not in cur: cur[e['a']] = tuple(e['f'])
    n = len(ids)
    byround = collections.defaultdict(list)
    for e in evs: byround[e['r']].append(e)
    hits = []
    for r in range(1, maxr + 1):
        if r > 1: sync(r - 1)
        if r not in slots: slots[r], ranks[r] = order(r)
        es = byround.get(r, [])
        j = 0
        for t in range(-1, n):
            while j < len(es) and es[j]['t'] <= t:
                e = es[j]; j += 1
                kk = e['k']; a = e.get('a')
                if kk == 'move': cur[a] = tuple(e['to'])
                elif kk == 'cast' and e.get('moved'): cur[a] = tuple(e['moved'])
                elif kk in ('recall_end', 'teleport_end'): cur[a] = tuple(e['to'])
                elif kk == 'respawn': cur[a] = tuple(e['at'])
                elif kk == 'death': cur[e['v']] = None
                if kk in ('attack', 'cast') and (e.get('dmg') or e.get('tgt') is not None):
                    for v, amt in (e.get('dmg') or []):
                        if v in team and team[v] != team[a] and amt > 0:
                            hits.append((r, t, a, v, kk, e.get('ab'), tuple(e['f'])))
            snaps[(r, t)] = dict(cur)
    res = []
    for (r, t, a, v, kk, ab, af) in hits:
        sv = slots[r][v]
        if sv < t: prev = (r, sv)
        else:
            if r - 1 not in slots: continue
            prev = (r - 1, slots[r - 1][v])
        s = snaps.get(prev)
        if not s or s.get(a) is None or s.get(v) is None: continue
        d0 = cheb(s[a], s[v])
        # attacker turns in (prev, (r,t)]
        cnt = 0
        for rr in range(prev[0], r + 1):
            sa = slots[rr][a]
            if (rr, sa) > prev and (rr, sa) <= (r, t): cnt += 1
        dashed = any(prev < x <= (r, t) for x in dashes[a])
        same_rank = ranks[r][a] == ranks[r][v]
        res.append((name[a], kk, ab, d0, cnt, dashed, same_rank, m["teams"][team[a]]["name"], m["teams"][team[v]]["name"], name[v]))
    return ok, bad, res

if __name__ == '__main__':
    idxj = json.load(open(os.path.join(ROOT, 'index.json'), encoding='utf-8'))
    dirs = sorted({g['dir'] for g in idxj['games'] if g['kind'] == 'ladder' and g['ok'] and '20261016' <= g['source'].split('/')[2][:8]})
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    dirs = dirs[:lim]
    tot_ok = tot_bad = 0; allres = []
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(game, dirs, chunksize=4):
            if not r: continue
            tot_ok += r[0]; tot_bad += r[1]; allres += r[2]
    print('slot model check: ok', tot_ok, 'bad', tot_bad)
    import pickle; pickle.dump(allres, open('turnreach.pkl', 'wb'))
    print('hits', len(allres))
