"""Hits on victims standing in bushes: who could have targeted them (attacker inside the cluster, its own ward in
the cluster, or neither: ground spells, splash)? Plus, per team, the same split for its hits (by) and the hits it
took (on), and how many of its hits and hits taken were on bush-standing victims.

  py bushhits.py 1500                                         # the report: first 1500 ladder games since 10-16
  py bushhits.py --src replays/batch-20261017-091937-928141 --team nemesis rival
Selection options: gamesel.py.
"""
import json, gzip, os, collections, sys
from concurrent.futures import ProcessPoolExecutor
import gamesel
ROOT = gamesel.ROOT
GROUND = {'Ryth': {0}, 'Prism': {1}, 'Stellar': {1}}
_mapcache = {}
def clusters(m):
    b = set(map(tuple, m['bushes'])); cid = {}; k = 0
    for t in b:
        if t in cid: continue
        st = [t]; cid[t] = k
        while st:
            x, y = st.pop()
            for n in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if n in b and n not in cid: cid[n] = k; st.append(n)
        k += 1
    return cid
def game(args):
    d, names = args
    try:
        m = json.load(open(os.path.join(ROOT, d, 'meta.json'), encoding='utf-8'))
        ev = [json.loads(l) for l in gzip.open(os.path.join(ROOT, d, 'events.jsonl.gz'), 'rt')]
        R = json.load(gzip.open(os.path.join(ROOT, d, 'rounds.json.gz')))
        mp = json.load(open(os.path.join(ROOT, 'maps', m['map']['hash'] + '.json')))
    except Exception: return None
    cid = clusters(mp)
    name = {c['id']: c['name'] for c in m['champions']}; team = {c['id']: c['team'] for c in m['champions']}
    idx = {c['id']: i for i, c in enumerate(m['champions'])}
    rix = {r: i for i, r in enumerate(R['round'])}
    cur = {}; wards = {}
    ev.sort(key=lambda e: e['s'])
    for e in ev:
        if e['k'] == 'move' and e['a'] not in cur: cur[e['a']] = tuple(e['f'])
    lastr = 0; out = collections.Counter()
    for e in ev:
        r = e['r']
        if r != lastr:
            i = rix.get(r - 1)
            if i is not None:
                for c in idx:
                    ch = R['champions'][idx[c]]
                    cur[c] = (ch['x'][i], ch['y'][i]) if ch['alive'][i] else None
            lastr = r
        k = e['k']; a = e.get('a')
        if k == 'move': cur[a] = tuple(e['to'])
        elif k == 'cast' and e.get('moved'): cur[a] = tuple(e['moved'])
        elif k in ('recall_end', 'teleport_end'): cur[a] = tuple(e['to'])
        elif k == 'respawn': cur[a] = tuple(e['at'])
        elif k == 'death': cur[e['v']] = None
        elif k == 'ward': wards[a] = tuple(e['to'])
        if k in ('attack', 'cast'):
            ground = k == 'cast' and e.get('slot') in GROUND.get(name[a], set())
            for v, amt in (e.get('dmg') or []):
                if v not in team or team[v] == team[a] or amt <= 0: continue
                vp = cur.get(v)
                ta, tv = names[team[a]], names[team[v]]
                if vp is None or vp not in cid:
                    out['victim_not_in_bush', k, ground] += 1; out['by', ta, 'open'] += 1; out['on', tv, 'open'] += 1; continue
                c = cid[vp]
                ap = tuple(e['f'])
                inside = cid.get(ap) == c
                wardin = a in wards and cid.get(wards[a]) == c
                # any ally of attacker? personal vision only: attacker's own ward/body
                tag = 'attacker_in_cluster' if inside else 'own_ward_in_cluster' if wardin else 'NEITHER'
                out['victim_in_bush', k, ground, tag] += 1
                out['by', ta, tag] += 1; out['on', tv, tag] += 1
    return out
if __name__ == '__main__':
    p = gamesel.parser(__doc__)
    p.add_argument('n', nargs='?', type=int, help='first N games (as --limit)')
    a = p.parse_args()
    a.limit = a.n or a.limit
    games = gamesel.select(a)
    tot = collections.Counter()
    with ProcessPoolExecutor(a.threads) as ex:
        for r in ex.map(game, games, chunksize=8):
            if r: tot += r
    for k, v in sorted(tot.items(), key=lambda kv: str(kv[0])):
        if k[0] not in ('by', 'on'): print(k, v)
    tags = ('attacker_in_cluster', 'own_ward_in_cluster', 'NEITHER')
    for t in a.team or []:
        for side in ('by', 'on'):
            n = sum(tot[side, t, g] for g in tags)
            alln = n + tot[side, t, 'open']
            print(f"{t[:22]:22s} hits {side} {alln:7d}, on bush-standing victims {n / max(1, alln):.3f}: "
                  + '  '.join(f'{g} {tot[side, t, g] / max(1, n):.2f}' for g in tags))
