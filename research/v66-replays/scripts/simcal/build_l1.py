# Level-1 calibration rows: every stand (TE home stand_*), start-tile fight sim (TT fs) and chase sim
# (TE prey_fight) with at least one enemy, joined with what happened next in the ladder extract.
# Output: replays/v66-analysis/simcal/l1.jsonl.gz (one row per prediction).
import sys, os, json, gzip
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'trace'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'extract'))
from tlib import *
import common as C
from concurrent.futures import ProcessPoolExecutor

OUT = 'replays/v66-analysis/simcal'
MAN = {g['group'][:8] + '-' + str(g['position']): g['replay'] for g in json.load(open('replays/v66/manifest.json'))['games']}
SRC = {g['source']: g for g in C.games(distinct=False)}
H = 20  # rounds of outcome kept


def ptrade(s):
    p = s.split(':')
    if len(p) != 6: return None
    return dict(lost=int(p[0]), tku=int(p[1]), tkt=int(p[2]), falls=p[3], al=int(p[4]), en=int(p[5]))


def outcome_tables(g):
    m = C.meta(g['dir']); team = {c['id']: c['team'] for c in m['champions']}
    ctype = {c['id']: c['type'] for c in m['champions']}
    R = C.rounds(g['dir'])
    rix = {r: i for i, r in enumerate(R['round'])}
    taken = defaultdict(float); dealt = defaultdict(float); deaths = defaultdict(list); killer = {}
    heal = defaultdict(float)
    for e in C.events(g['dir']):
        k = e['k']
        if k in ('attack', 'cast'):
            a = e['a']
            for v, amt in (e.get('dmg') or []):
                if v in team and team[v] != team.get(a):
                    taken[(e['r'], v)] += amt; dealt[(e['r'], a)] += amt
            for v, amt in (e.get('heal') or []) if isinstance(e.get('heal'), list) else []:
                heal[(e['r'], v)] += amt
        elif k == 'death':
            deaths[e['v']].append(e['r']); killer[(e['v'], e['r'])] = e.get('by')
    return team, ctype, R, rix, taken, dealt, deaths, killer


def one(key):
    try:
        g = SRC[MAN[key]]
    except KeyError:
        return []
    T, TV = load(key)
    team, ctype, R, rix, taken, dealt, deaths, killer = outcome_tables(g)
    us = g['us']
    ch = R['champions']
    idx = {c['id']: i for i, c in enumerate(ch)}

    def pos(cid, r):  # state at end of round r-1 = start of r
        i = rix.get(r - 1)
        if i is None: return None
        c = ch[idx[cid]]
        if not c['alive'][i]: return None
        return (c['x'][i], c['y'][i])

    def outcome(cid, r):
        o = {}
        dr = [d for d in deaths.get(cid, []) if d >= r]
        o['death_in'] = (dr[0] - r) if dr and dr[0] - r <= H else None
        o['taken'] = [round(taken.get((r + k, cid), 0)) for k in range(H + 1)]
        o['dealt'] = [round(dealt.get((r + k, cid), 0)) for k in range(H + 1)]
        p = pos(cid, r)
        if p:
            near_us, near_them = [], []
            for c in ch:
                q = pos(c['id'], r)
                if q is None or cheb(p, q) > 8: continue
                (near_us if c['team'] == us else near_them).append(c['id'])
            o['near_us'] = len(near_us); o['near_them'] = len(near_them)
            ud = sum(1 for x in near_us for d in deaths.get(x, []) if r <= d <= r + 15)
            td = sum(1 for x in near_them for d in deaths.get(x, []) if r <= d <= r + 15)
            o['us_dead15'] = ud; o['them_dead15'] = td
            # damage over the next 10 rounds between the near groups
            o['us_taken10'] = round(sum(taken.get((r + k, x), 0) for k in range(10) for x in near_us))
            o['them_taken10'] = round(sum(taken.get((r + k, x), 0) for k in range(10) for x in near_them))
            i = rix.get(r - 1)
            o['us_hp'] = round(sum(ch[idx[x]]['hp'][i] for x in near_us)); o['them_hp'] = round(sum(ch[idx[x]]['hp'][i] for x in near_them))
            o['us_str'] = round(sum(ch[idx[x]]['str'][i] for x in near_us), 1); o['them_str'] = round(sum(ch[idx[x]]['str'][i] for x in near_them), 1)
        return o

    rows = []
    for (r, c), rec in T.items():
        tt = rec['TT'][0] if rec['TT'] else None
        if not tt or tt.get('a') != '1': continue
        base = dict(key=key, r=r, c=c, t=tt['t'], opp=g['opp'], hp=float(tt['hp']), mh=float(tt['mh']), d=tt.get('d'),
                    p=tt.get('p'), q=tt.get('q'))
        outc = None
        for te in rec['TE']:
            kd = te.get('k')
            if kd == 'home' and te.get('why', '').startswith('stand'):
                tr = ptrade(te.get('t', ''))
                if not tr or tr['en'] == 0: continue
                outc = outc or outcome(c, r)
                rows.append(dict(base, kind='stand', why=te['why'], lethal=int(te.get('lethal', 0)), pursued=int(te.get('pursued', 0)),
                                 linked=int(te.get('linked', 0)), **tr, **outc))
            elif kd == 'prey_fight':
                tr = ptrade(te.get('t', ''))
                if not tr or tr['en'] == 0: continue
                outc = outc or outcome(c, r)
                rows.append(dict(base, kind='chase', e=int(te['e']), take=int(te.get('take', 0)), delayed=te.get('delayed'),
                                 late=te.get('late'), **tr, **outc))
        fs = tt.get('fs')
        if fs and fs not in ('?', 'none'):
            tr = ptrade(fs)
            if tr and tr['en'] > 0:
                outc = outc or outcome(c, r)
                rows.append(dict(base, kind='fs', **tr, **outc))
    return rows


if __name__ == '__main__':
    ks = [k for k, v in keys()]
    os.makedirs(OUT, exist_ok=True)
    n = 0
    with ProcessPoolExecutor(20) as ex, gzip.open(OUT + '/l1.jsonl.gz', 'wt') as f:
        for rows in ex.map(one, ks, chunksize=4):
            for x in rows: f.write(json.dumps(x) + '\n'); n += 1
    print('rows', n, 'games', len(ks))
