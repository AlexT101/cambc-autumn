"""Turning points of games: where the loser's gem position (tributed + carried) last stood level or ahead,
and what the gap is made of (captures, kill transfers, camp-death losses) by then and by the end.
usage: py turning.py EXTRACT_ROOT [--team NAME] [--json OUT]
With --team, only games that team lost (its view); else every game, loser's view."""
import json, gzip, glob, os, sys, collections
from concurrent.futures import ProcessPoolExecutor

ROOT = sys.argv[1]
TEAM = sys.argv[sys.argv.index('--team') + 1] if '--team' in sys.argv else None
OUT = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
EN = json.load(open(os.path.join(ROOT, 'enums.json')))
CH = EN['champions']
IDX = {g['dir']: g for g in json.load(open(os.path.join(ROOT, 'index.json')))['games']}


def one(d):
    g = IDX.get(os.path.basename(d))
    if not g or not g.get('ok', True):
        return None
    meta = json.load(open(d + '/meta.json'))
    w = meta['result']['winner']
    L = 1 - w
    if TEAM is not None:
        if TEAM not in g['teams']:
            return None
        us = g['teams'].index(TEAM)
        if us != L:
            return {'won': True}
    team = {c['id']: c['team'] for c in meta['champions']}
    typ = {c['id']: CH[c['type']] for c in meta['champions']}
    R = json.load(gzip.open(d + '/rounds.json.gz'))
    rounds = R['round']
    n = len(rounds)
    val = [[0] * n, [0] * n]
    for t in (0, 1):
        for i in range(n):
            val[t][i] = R['gems'][t][i]
    for c in R['champions']:
        t = c['team']
        for i in range(n):
            val[t][i] += c['gems'][i] or 0
    gap = [val[L][i] - val[w][i] for i in range(n)]
    swing = 0
    for i in range(n):
        if gap[i] >= 0:
            swing = i
    sr = rounds[swing] if n else 0
    # cumulative sources by round
    cap = [0, 0]; killg = [0, 0]; camplost = [0, 0]; deaths = [0, 0]; pdeath = [None, None]
    at_swing = None
    ev_window = []
    first_kill = None
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        r = e['r']
        if at_swing is None and r > sr:
            at_swing = dict(cap=list(cap), killg=list(killg), camplost=list(camplost), deaths=list(deaths))
        k = e['k']
        if k == 'capture':
            for cid, gm, gd in e['shares']:
                cap[team[cid]] += gm
        elif k == 'death':
            v = e['v']; tv = team[v]
            deaths[tv] += 1
            if typ[v] == 'Prism' and pdeath[tv] is None:
                pdeath[tv] = r
            if 'by' in e and e['by'] is not None:
                killg[1 - tv] += e.get('gems', 0)
                killg[tv] -= e.get('gems', 0)
                if first_kill is None:
                    first_kill = (r, tv, e.get('gems', 0))
            else:
                camplost[tv] += e.get('gems', 0)
            if sr - 30 <= r <= sr + 10:
                ev_window.append(('death', r, tv == L, typ[v], e.get('gems', 0), 'camp' if e.get('camp') is not None else 'champ'))
        elif k == 'capture' or k == 'capture_flip':
            pass
    if at_swing is None:
        at_swing = dict(cap=list(cap), killg=list(killg), camplost=list(camplost), deaths=list(deaths))
    final = dict(cap=cap, killg=killg, camplost=camplost, deaths=deaths)
    has_prism = [any(typ[c] == 'Prism' and team[c] == t for c in typ) for t in (0, 1)]
    return dict(map=meta['map']['name'], rounds=meta['result']['rounds'], swing=sr, L=L,
                at_swing={k: v[L] - v[w] for k, v in at_swing.items()},
                final={k: v[L] - v[w] for k, v in final.items()},
                window=ev_window, pdeath=[pdeath[L], pdeath[w]], prism=[has_prism[L], has_prism[w]],
                first_kill=first_kill and (first_kill[0], first_kill[1] == L, first_kill[2]),
                gapmin=min(gap) if gap else 0, n_champs=sum(1 for c in team.values() if c == L))


if __name__ == '__main__':
    ds = [os.path.dirname(p) for p in glob.glob(ROOT + '/*/meta.json')]
    with ProcessPoolExecutor(32) as ex:
        S = [s for s in ex.map(one, ds, chunksize=8) if s and not s.get('won')]
    if OUT:
        json.dump(S, open(OUT, 'w'))
    N = len(S)
    print('lost games', N)
    import statistics as st
    sw = sorted(s['swing'] for s in S)
    print('swing round quartiles', sw[N // 4], sw[N // 2], sw[3 * N // 4])
    for k in ('cap', 'killg', 'camplost', 'deaths'):
        print('%-9s at swing+: mean %.1f | final mean %.1f' % (k, st.mean(s['at_swing'][k] for s in S), st.mean(s['final'][k] for s in S)))
    # classify: what made the loser's final gap
    cls = collections.Counter()
    for s in S:
        f = s['final']
        econ = f['cap']; fight = f['killg'] - f['camplost']
        if econ < 0 and fight >= 0: c = 'economy only'
        elif econ >= 0 and fight < 0: c = 'fights only'
        elif econ < 0 and fight < 0: c = 'both (econ %s)' % ('larger' if econ < fight else 'smaller')
        else: c = 'neither'
        cls[c] += 1
    for c, v in cls.most_common():
        print('  %-26s %5d %.1f%%' % (c, v, 100 * v / N))
    # Prism-first death
    pf = collections.Counter()
    for s in S:
        if not s['prism'][0]: pf['loser has no Prism'] += 1; continue
        a, b = s['pdeath']
        if a is not None and (b is None or a < b): pf['loser Prism died first'] += 1
        elif b is not None: pf['winner Prism died first'] += 1
        else: pf['no Prism death'] += 1
    for c, v in pf.most_common():
        print('  %-26s %5d %.1f%%' % (c, v, 100 * v / N))
    # captures gap at r(swing) bins
    print('capture gap at swing by swing-round bin:')
    bins = collections.defaultdict(list)
    for s in S:
        b = min(s['swing'] // 150, 6)
        bins[b].append(s)
    for b in sorted(bins):
        xs = bins[b]
        print('  r%4d-%4d n=%4d cap %.0f killg %.0f camplost %.0f deaths %.2f' % (b * 150, b * 150 + 149, len(xs),
              st.mean(x['at_swing']['cap'] for x in xs), st.mean(x['at_swing']['killg'] for x in xs),
              st.mean(x['at_swing']['camplost'] for x in xs), st.mean(x['at_swing']['deaths'] for x in xs)))
