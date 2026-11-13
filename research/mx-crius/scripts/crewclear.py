"""Elk/Golem clears from wake to clear, by kind and striker count (>=10% of the damage): rounds, team camp damage,
striker utilisation (hit rounds / rounds from its first hit to the clear), idle rounds (no hit by the clearing team),
group sleeps mid-clear, strikers' recalls mid-clear, and the damage share the first-arriving striker took.
Usage: crewclear.py EXTRACT_DIR [team_name]   (team_name: only clears by that team)."""
import json, gzip, glob, os, sys, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
ROOT = sys.argv[1]; ONLY = sys.argv[2] if len(sys.argv) > 2 else None
def kind(G, camps):
    ts = [camps[c]['type'] for c in G['camps']]
    for k in ('Golem', 'Elk'):
        if k in ts: return k
    return None
def one(d):
    meta = json.load(open(d + '/meta.json'))
    mp = json.load(open(os.path.join(d, meta['mapFile']))); camps = {c['id']: c for c in mp['camps']}
    team = {c['id']: c['team'] for c in meta['champions']}; ctype = {c['id']: c['name'] for c in meta['champions']}
    names = [t['name'] for t in meta['teams']]
    cg = {c['id']: c['group'] for c in mp['camps']}
    K = {G['id']: kind(G, camps) for G in mp['groups']}
    open_ = {}; out = []
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l); k = e['k']
        if k in ('attack', 'cast') and e.get('cdmg'):
            for cid, amt in e['cdmg']:
                g = cg.get(cid)
                if g is None or not K.get(g): continue
                o = open_.setdefault(g, {'r0': e['r'], 'dmg': collections.Counter(), 'first': {}, 'hitr': collections.defaultdict(set),
                                         'taken': collections.Counter(), 'sleeps': 0, 'recalls': collections.Counter(), 'takenr': []})
                o['dmg'][e['a']] += amt; o['first'].setdefault(e['a'], e['r']); o['hitr'][e['a']].add(e['r'])
        elif k == 'camp_attack' and e.get('g') in open_:
            o = open_[e['g']]; o['taken'][e['tgt']] += e['dmg']; o['takenr'].append((e['r'], e['tgt'], e['dmg']))
        elif k == 'group_sleep' and e.get('g') in open_:
            open_[e['g']]['sleeps'] += 1
        elif k == 'recall_end':
            for o in open_.values():
                if e['a'] in o['first']: o['recalls'][e['a']] += 1
        elif k == 'group_clear' and e['g'] in open_:
            o = open_.pop(e['g']); tot = sum(o['dmg'].values())
            t = team[max(o['dmg'], key=o['dmg'].get)]
            enemy = sum(v for a, v in o['dmg'].items() if team[a] != t) / max(1, tot)
            if enemy > 0.0: continue  # contested clears left out
            sts = [a for a, v in o['dmg'].items() if v >= 0.1 * tot and team[a] == t]
            if ONLY and names[t] != ONLY: continue
            R = e['r']; r0 = o['r0']
            util = [len(o['hitr'][a]) / (R - o['first'][a] + 1) for a in sts]
            anyhit = set().union(*[o['hitr'][a] for a in o['dmg'] if team[a] == t])
            idle = (R - r0 + 1) - len(anyhit)
            taken_team = sum(v for a, v in o['taken'].items() if team[a] == t)
            first = min(sts, key=lambda a: o['first'][a])
            share_first = o['taken'][first] / max(1, taken_team)
            # damage on non-strikers of our team (bystanders) and on enemies
            by = sum(v for a, v in o['taken'].items() if team[a] == t and a not in sts)
            rec = sum(o['recalls'][a] for a in sts)
            lag = sorted(o['first'][a] for a in sts); lag = lag[1] - lag[0] if len(lag) > 1 else 0
            out.append(dict(kind=K[e['g']], n=min(len(sts), 3), dur=R - r0, taken=taken_team, util=st.mean(util), idle=idle,
                            sleeps=o['sleeps'], rec=rec, share_first=share_first, by=by, lag=lag, r0=r0,
                            types='+'.join(sorted(ctype[a] for a in sts)), hp=tot,
                            dpr=sum(o['dmg'][a] / len(o['hitr'][a]) for a in sts),
                            ideal=tot / sum(o['dmg'][a] / len(o['hitr'][a]) for a in sts)))
    return out
if __name__ == '__main__':
    ds = [os.path.dirname(p) for p in glob.glob(ROOT + '/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: S = [x for o in ex.map(one, ds, chunksize=8) for x in o]
    tab = collections.defaultdict(list)
    for s in S: tab[(s['kind'], 'r<250' if s['r0'] < 250 else 'r250-600' if s['r0'] < 600 else 'r600+', s['n'])].append(s)
    print('%-6s %-9s %s %6s %5s %6s %5s %5s %5s %5s %5s %5s %5s' % ('kind', 'phase', 'n', 'clears', 'dur', 'taken', 'util', 'idle', 'sleep', 'recal', 'shr1', 'bystd', 'lag'), '   hp   dpr ideal tk/hp')
    for key in sorted(tab):
        xs = tab[key]
        if len(xs) < 50: continue
        m = lambda f: st.mean(x[f] for x in xs)
        print('%-6s %-9s %d %6d %5.1f %6.0f %5.2f %5.1f %5.2f %5.2f %5.2f %5.0f %5.1f' % (key[0], key[1], key[2], len(xs), m('dur'), m('taken'), m('util'), m('idle'),
              m('sleeps'), m('rec'), m('share_first'), m('by'), m('lag')), '%5.0f %5.0f %5.1f %5.3f' % (m('hp'), m('dpr'), m('ideal'), st.mean(x['taken']/x['hp'] for x in xs)))
    if len(sys.argv) > 3:
        ty = collections.defaultdict(list)
        for s in S:
            if s['kind'] == 'Elk' and 250 <= s['r0'] < 600: ty[s['types']].append(s)
        for t, xs in sorted(ty.items(), key=lambda kv: -len(kv[1]))[:25]:
            m = lambda f: st.mean(x[f] for x in xs)
            print('%-40s %5d dur %5.1f taken %5.0f dpr %5.0f ideal %5.1f lag %4.1f idle %4.1f' % (t, len(xs), m('dur'), m('taken'), m('dpr'), m('ideal'), m('lag'), m('idle')))
