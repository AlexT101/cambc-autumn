"""Paired forensics: CAND-vs-base games against the base mirror on the same map and side (debug builds, D traces).
fx.py CANDRUN BASERUN OUT.pkl"""
import json, gzip, os, sys, subprocess, collections, pickle, zipfile, re, numpy as np
R = '/home/ubuntu/cambc-autumn/'
X = os.environ.get('FXX', os.path.expanduser('~/tmp-offload/draftfarm/fx-x'))
RS = [50, 100, 150, 200, 300]


def matches(name):
    s = json.load(open(f'{R}replays/ab/{name}/summary.json'))
    for su in s['suites']:
        for m in json.load(open(R + su['batch'] + '/results.json'))['matches']:
            p = m.get('replay')
            if m.get('winner') is None or not p: continue
            p = p if p.startswith('/') else R + p
            if os.path.exists(p): m['replay'] = p; yield m


def extract(paths):
    os.makedirs(X, exist_ok=True)
    lst = [p for p in paths]
    subprocess.run(['python3', R + 'tools/pooled.py', '16', '--', 'node', R + 'tools/replay/extract.mjs', *lst, '--threads', '16', '--out', X],
                   check=False, stdout=subprocess.DEVNULL)
    dirs = {}
    for g in json.load(open(X + '/index.json'))['games']:
        if g.get('ok', True): dirs[os.path.realpath(g['source'] if g['source'].startswith('/') else os.path.join(R, g['source']))] = X + '/' + g['dir']
    return dirs


def dlines(replay, team):
    if not os.path.exists(replay): return {}, []
    with zipfile.ZipFile(replay) as z:
        out = z.read(f'team-{"ab"[team]}.stdout').replace(b'\0', b'').decode('utf-8', 'replace')
    d = collections.defaultdict(dict)
    for m in re.finditer(r'^D (\d+) (\d+) (\S) (-?\d+) (-?\d+)$', out, re.M):
        r = int(m[1])
        if r <= 200: d[int(m[2])][r] = (m[3], int(m[4]), int(m[5]))
    plan = [list(map(int, re.findall(r'g(\d+)', l))) for l in re.findall(r'^OPENPLAN body \d+(.*)$', out, re.M)]
    return d, plan


def game(m, d, us):
    Rd = json.load(gzip.open(d + '/rounds.json.gz'))
    meta = json.load(open(d + '/meta.json'))
    ch = {c['id']: c for c in meta['champions']}
    rr = np.array(Rd['round'])
    sp = {0: [], 1: []}
    for c in Rd['champions']: sp[c['team']].append((c['x'][0], c['y'][0]))
    spc = {t: np.mean(sp[t], axis=0) for t in sp}
    row = dict(win=None)
    for r in RS:
        i = min(np.searchsorted(rr, r), len(rr) - 1)
        for t, nm in ((us, 'u'), (1 - us, 'o')):
            row[f'gold{r}{nm}'] = sum(c['earned'][i] for c in Rd['champions'] if c['team'] == t)
            row[f'own{r}{nm}'] = Rd['gems'][t][i] + sum(c['gems'][i] for c in Rd['champions'] if c['team'] == t)
    # positions per champion per round index, for divergence
    row['pos'] = {c['id']: (np.array(c['x'][:400]), np.array(c['y'][:400])) for c in Rd['champions']}
    row['rounds'] = rr[:400]
    gpos = collections.defaultdict(list); cg = {}; caps = []; deaths = []
    for l in gzip.open(d + '/events.jsonl.gz'):
        e = json.loads(l)
        if e['r'] > 300: break
        k = e['k']
        if k == 'attack' and 'camp' in e: gpos[e['camp']].append(tuple(e['to']))
        if k in ('camp_death', 'camp_attack'): cg[e['camp']] = e['g']
        if k == 'capture': caps.append((e['r'], e['g'], e['team'] == us, sum(s[2] for s in e['shares']), sum(s[1] for s in e['shares']), len(e['shares'])))
        elif k == 'death' and 'linked' not in e:
            at = tuple(e['at'])
            near_v = sum(1 for c in Rd['champions'] if c['team'] == ch[e['v']]['team'] and c['id'] != e['v'] and _near(c, rr, e['r'], at))
            near_k = sum(1 for c in Rd['champions'] if c['team'] != ch[e['v']]['team'] and _near(c, rr, e['r'], at))
            deaths.append((e['r'], ch[e['v']]['team'] == us, at, e.get('by') in ch, e.get('gems', 0), near_v, near_k))
    gp = collections.defaultdict(list)
    for c, ps in gpos.items():
        if c in cg: gp[cg[c]].append(ps[0])

    def side(p):
        du = max(abs(p[0] - spc[us][0]), abs(p[1] - spc[us][1])); do = max(abs(p[0] - spc[1 - us][0]), abs(p[1] - spc[1 - us][1]))
        return (do - du) / max(1, du + do)
    row['gside'] = {g: side(np.mean(ps, axis=0)) for g, ps in gp.items()}
    row['caps'] = caps; row['deaths'] = [x + (side(x[2]),) for x in deaths]
    row['ids'] = {cid: c['team'] == us for cid, c in ch.items()}
    i2, i4 = (min(np.searchsorted(rr, r), len(rr) - 1) for r in (200, 400))
    row['earned_by'] = {c['id']: (ch[c['id']]['name'], c['team'] == us, c['earned'][i2], c['earned'][i4]) for c in Rd['champions']}
    return row


def _near(c, rr, r, at):
    i = min(np.searchsorted(rr, r), len(c['x']) - 1)
    return c['alive'][i] and max(abs(c['x'][i] - at[0]), abs(c['y'][i] - at[1])) <= 4


def main(cr, br, out):
    cm = list(matches(cr)); bm = list(matches(br))
    dirs = extract([m['replay'] for m in cm + bm])
    base = {}
    for m in bm:
        base.setdefault(os.path.basename(m['map']), m)
    rows = []
    for m in cm:
        mp = os.path.basename(m['map']); b = base.get(mp)
        if not b: continue
        dc, db = dirs.get(os.path.realpath(m['replay'])), dirs.get(os.path.realpath(b['replay']))
        if not dc or not db: continue
        us = m['order'].index(0)  # cand's team index
        bus = us  # base mirror: same side; its winner team
        btw = b['order'][b['winner']] if False else None
        # winner in results is the bot index (0 = CAND); map to team: order[team] = bot
        cwin = m['winner'] == 0
        bwin_team = b['order'].index(b['winner'])
        try:
            C = game(m, dc, us); B = game(b, db, bus)
        except Exception as ex:
            print('skip', mp, ex); continue
        C['D'], C['plan'] = dlines(m['replay'], us)
        B['D'], _ = dlines(b['replay'], bus)
        C['win'] = cwin; B['win'] = bwin_team == us
        # divergence: first round where any champion's position differs
        div = None
        for cid in C['pos']:
            if cid not in B['pos']: continue
            x1, y1 = C['pos'][cid]; x2, y2 = B['pos'][cid]; n = min(len(x1), len(x2))
            diff = np.nonzero((x1[:n] != x2[:n]) | (y1[:n] != y2[:n]))[0]
            if len(diff): div = diff[0] if div is None else min(div, diff[0])
        for G in (C, B): G.pop('pos'); G.pop('rounds')
        rows.append(dict(map=mp, side='ab'[us], C=C, B=B, div=None if div is None else int(div) + 1))
    pickle.dump(rows, open(out, 'wb'))
    print(len(rows), 'pairs')


if __name__ == '__main__':
    main(*sys.argv[1:4])
