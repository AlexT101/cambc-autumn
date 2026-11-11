#!/usr/bin/env python3
"""Pack-engagement metrics from decoded replays: the overruns README's engagement table, per group of games.

    # live: versions' scrims against Fish and Mite from the scrim log (unzips and decodes what is new)
    python3 packmetrics.py live 115 116 [--opps Fish Mite] [--work ~/tmp-offload/packgive/live] [--since 2026-11-11T18:00]
    # local: extract.mjs output dirs, our bot by its team name in each index.json
    python3 packmetrics.py local base=~/tmp-offload/packgive/ext-base:oc-dfuel-506 z8=~/tmp-offload/packgive/ext-z8:pg-z8

Every group gets a column; with two or more, the last lines give each later group minus the first (95% interval,
games resampled). `--pair` restricts every group to the (map, side, opponent) cells all groups played.

Definitions (as research/ideas-2026-11-11/overruns/tools: engage.py, theyinit.py, flee.py):
- An engagement is a run of champion-on-champion damage with gaps of at most 6 rounds, started by round 250. Its
  bodies are the live champions within 8 of the first target at the end of the round before the first hit; "they
  had" means more of theirs than ours there. Its kills are champion deaths (not to camps) from its first round
  to one after its last; Cassi and Issac count once.
- "they did, they had": the enemy landed the first hit and had more bodies. For those: the share whose first
  target died, their attackers, the damage on the first target, and whether that target moved towards or away
  from the pack (its members' centroid four rounds before, target's distance to it then and at the hit).
- Outnumbered rounds (new here, needs no hit): a champion of ours, rounds 2-250, with more live enemies than allies
  (itself included) within 8; the share of those rounds in which it stepped towards the enemies' centroid.
"""
import argparse, collections, gzip, json, os, subprocess, sys, zipfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
GAMES = os.path.join(REPO, 'research/ladder-scrims-2026-11-06/data/games.jsonl')
MAXR, GAP, NEAR = 250, 6, 8


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def game_stats(d, us):
    """One game's counters (a dict of numbers), `us` our team index."""
    meta = json.load(open(d + '/meta.json'))
    R = json.load(gzip.open(d + '/rounds.json.gz'))
    ch = R['champions']
    n = len(R['round'])
    team = {c['id']: c['team'] for c in meta['champions']}
    typ = {c['id']: c['name'] for c in meta['champions']}
    P = lambda c, i: (c['x'][i], c['y'][i])
    spawn = []
    for t in (0, 1):
        xs = [P(c, 0) for c in ch if c['team'] == t]
        spawn.append((sum(p[0] for p in xs) / len(xs), sum(p[1] for p in xs) / len(xs)))
    hits, deaths, fell, caps = [], [], [], [0, 0]  # deaths: Cassi and Issac once; fell: every body killed by a champion
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['r'] > MAXR + 60:
            break
        k = e['k']
        if k in ('attack', 'cast'):
            for t, dm in e.get('dmg', []):
                hits.append((e['r'], e['a'], t, dm))
        elif k == 'death':
            if 'camp' not in e and e.get('by') is not None:
                fell.append((e['r'], e['v']))
            if typ[e['v']] != 'Issac':
                deaths.append((e['r'], e['v'], 'camp' in e or e.get('by') is None))
        elif k == 'capture' and e['r'] <= 300:
            caps[0 if e['team'] == us else 1] += 1
    S = collections.Counter(games=1)
    kills = [(r, v) for r, v, camp in deaths if not camp]
    # engagements
    E, cur = [], None
    for h in hits:
        if cur and h[0] - cur['r1'] <= GAP:
            cur['hits'].append(h); cur['r1'] = h[0]
        elif h[0] > MAXR:
            break
        else:
            cur = dict(r0=h[0], r1=h[0], hits=[h]); E.append(cur)
    for en in E:
        r0, r1 = en['r0'], en['r1']
        i = max(r0 - 2, 0)
        a0, t0 = en['hits'][0][1], en['hits'][0][2]
        T = ch[t0]
        c0 = P(T, i)
        if c0[0] is None:
            continue
        mine = [c for c in ch if c['team'] == us and c['alive'][i] and cheb(P(c, i), c0) <= NEAR]
        theirs = [c for c in ch if c['team'] != us and c['alive'][i] and cheb(P(c, i), c0) <= NEAR]
        k = [0, 0]  # kills by us, by them
        for r, v in kills:
            if r0 <= r <= r1 + 1:
                k[0 if team[v] != us else 1] += 1
        net = k[0] - k[1]
        first_us = team[a0] == us
        rel = 'they' if len(theirs) > len(mine) else 'we' if len(mine) > len(theirs) else 'level'
        cls = ('we' if first_us else 'they') + '_' + rel
        S['eng'] += 1; S['eng_net'] += net
        S['n_' + cls] += 1; S['net_' + cls] += net
        if rel == 'they':
            S['n_any_they'] += 1; S['net_any_they'] += net
        if cls != 'they_they':
            continue
        S['tt_theirs'] += len(theirs); S['tt_mine'] += len(mine)
        S['tt_first_died'] += any(v == t0 and r0 <= r <= r1 + 1 for r, v in fell)
        S['tt_lost'] += k[1]; S['tt_won'] += k[0]
        S['tt_attackers'] += len({h[1] for h in en['hits'] if team[h[1]] != us})
        S['tt_dmg_first'] += sum(h[3] for h in en['hits'] if h[2] == t0)
        S['tt_home'] += cheb(c0, spawn[us]) <= cheb(c0, spawn[1 - us])
        S['tt_soft'] += typ[t0] in ('Cassi', 'Issac')
        j4 = max(r0 - 5, 0)
        if T['x'][j4] is not None:
            ex = [P(c, j4) for c in theirs if c['x'][j4] is not None]
            if ex:
                cx = sum(p[0] for p in ex) / len(ex); cy = sum(p[1] for p in ex) / len(ex)
                before = max(abs(T['x'][j4] - cx), abs(T['y'][j4] - cy)); after = max(abs(c0[0] - cx), abs(c0[1] - cy))
                S['tt_m'] += 1
                S['tt_toward'] += after < before - 0.5; S['tt_away'] += after > before + 0.5
    # outnumbered rounds
    for i in range(1, min(n, MAXR)):
        live = [c for c in ch if c['alive'][i] and c['alive'][i - 1] and c['x'][i] is not None and c['x'][i - 1] is not None]
        ours = [c for c in live if c['team'] == us]; foes = [c for c in live if c['team'] != us]
        if not foes:
            continue
        for c in ours:
            p0 = P(c, i - 1)
            near = [P(f, i - 1) for f in foes if cheb(P(f, i - 1), p0) <= NEAR]
            if len(near) < 2 or len(near) <= sum(1 for a in ours if cheb(P(a, i - 1), p0) <= NEAR):
                continue
            cx = sum(p[0] for p in near) / len(near); cy = sum(p[1] for p in near) / len(near)
            p1 = P(c, i)
            before = max(abs(p0[0] - cx), abs(p0[1] - cy)); after = max(abs(p1[0] - cx), abs(p1[1] - cy))
            home = cheb(p0, spawn[us]) <= cheb(p0, spawn[1 - us])
            for tag in ('on', 'onh') if home else ('on',):
                S[tag] += 1; S[tag + '_toward'] += after < before - 0.5; S[tag + '_away'] += after > before + 0.5
    # deaths, gold, captures
    first = {0: None, 1: None}
    for r, v in kills:
        side = 0 if team[v] == us else 1
        if first[side] is None:
            first[side] = r
    f0, f1 = first[0] or 10**6, first[1] or 10**6
    S['ours_first150'] += f0 <= 150 and f0 < f1; S['theirs_first150'] += f1 <= 150 and f1 < f0
    for r, v, camp in deaths:
        if r <= MAXR:
            S[('our' if team[v] == us else 'their') + '_deaths250'] += 1
            if camp and team[v] == us:
                S['our_campdeaths250'] += 1
    i = min(300, n) - 1
    S['our_gold300'] += sum(c['earned'][i] for c in ch if c['team'] == us)
    S['their_gold300'] += sum(c['earned'][i] for c in ch if c['team'] != us)
    S['our_caps300'] += caps[0]; S['their_caps300'] += caps[1]
    S['our_gems300'] += R['gems'][us][i]; S['their_gems300'] += R['gems'][1 - us][i]
    return dict(S)


ROWS = [  # label, numerator, denominator, format
    ('win %', 'win', 'games', '%.1f', 100),
    ('engagements a game', 'eng', 'games', '%.2f', 1),
    ('net kills an engagement, all', 'eng_net', 'eng', '%+.3f', 1),
    ('they did, they had: a game', 'n_they_they', 'games', '%.3f', 1),
    ('  net kills each', 'net_they_they', 'n_they_they', '%+.3f', 1),
    ('  net kills a game', 'net_they_they', 'games', '%+.3f', 1),
    ('  first target died %', 'tt_first_died', 'n_they_they', '%.1f', 100),
    ('  their attackers', 'tt_attackers', 'n_they_they', '%.2f', 1),
    ('  damage on the first target', 'tt_dmg_first', 'n_they_they', '%.0f', 1),
    ('  bodies theirs', 'tt_theirs', 'n_they_they', '%.2f', 1),
    ('  bodies ours', 'tt_mine', 'n_they_they', '%.2f', 1),
    ('  target moved towards the pack %', 'tt_toward', 'tt_m', '%.1f', 100),
    ('  target moved away %', 'tt_away', 'tt_m', '%.1f', 100),
    ('  on our half %', 'tt_home', 'n_they_they', '%.1f', 100),
    ('  target Cassi or Issac %', 'tt_soft', 'n_they_they', '%.1f', 100),
    ('they did, level: a game', 'n_they_level', 'games', '%.3f', 1),
    ('  net kills each', 'net_they_level', 'n_they_level', '%+.3f', 1),
    ('we did, they had: a game', 'n_we_they', 'games', '%.3f', 1),
    ('  net kills each', 'net_we_they', 'n_we_they', '%+.3f', 1),
    ('we did, we had: a game', 'n_we_we', 'games', '%.3f', 1),
    ('  net kills each', 'net_we_we', 'n_we_we', '%+.3f', 1),
    ('any, they had: a game', 'n_any_they', 'games', '%.3f', 1),
    ('  net kills each', 'net_any_they', 'n_any_they', '%+.3f', 1),
    ('  net kills a game', 'net_any_they', 'games', '%+.3f', 1),
    ('outnumbered rounds a game', 'on', 'games', '%.1f', 1),
    ('  stepped towards %', 'on_toward', 'on', '%.1f', 100),
    ('  stepped away %', 'on_away', 'on', '%.1f', 100),
    ('outnumbered rounds on our half a game', 'onh', 'games', '%.1f', 1),
    ('  stepped towards %', 'onh_toward', 'onh', '%.1f', 100),
    ('  stepped away %', 'onh_away', 'onh', '%.1f', 100),
    ('first death by 150 ours, % of games', 'ours_first150', 'games', '%.1f', 100),
    ('first death by 150 theirs, % of games', 'theirs_first150', 'games', '%.1f', 100),
    ('our deaths by 250 a game', 'our_deaths250', 'games', '%.2f', 1),
    ('  of them to camps', 'our_campdeaths250', 'games', '%.2f', 1),
    ('their deaths by 250 a game', 'their_deaths250', 'games', '%.2f', 1),
    ('our gold by 300', 'our_gold300', 'games', '%.0f', 1),
    ('their gold by 300', 'their_gold300', 'games', '%.0f', 1),
    ('our captures by 300', 'our_caps300', 'games', '%.2f', 1),
    ('their captures by 300', 'their_caps300', 'games', '%.2f', 1),
    ('our tributed gems by 300', 'our_gems300', 'games', '%.0f', 1),
    ('their tributed gems by 300', 'their_gems300', 'games', '%.0f', 1),
]


def ratio(games, num, den):
    a = sum(g.get(num, 0) for g in games); b = sum(g.get(den, 0) for g in games)
    return a / b if b else float('nan')


def table(groups, reps=2000, seed=1):
    """groups: [(name, [game dicts])]. Intervals: games resampled within each group, independently."""
    for v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ.setdefault(v, '1')
    import numpy as np
    names = [n for n, _ in groups]
    keys = sorted({k for r in ROWS for k in r[1:3]})
    col = {k: i for i, k in enumerate(keys)}
    mats = [np.array([[g.get(k, 0) for k in keys] for g in gs], dtype=float) for _, gs in groups]
    tot = [m.sum(0) for m in mats]
    rng = np.random.default_rng(seed)
    boot = [np.stack([m[rng.integers(0, len(m), len(m))].sum(0) for _ in range(reps)]) for m in mats] if len(groups) > 1 else None
    w = max(len(r[0]) for r in ROWS) + 2
    print(' ' * w + ''.join('%16s' % n[:15] for n in names) + (''.join('%30s' % ('%s - %s' % (n[:10], names[0][:10])) for n in names[1:])))
    for label, num, den, fmt, scale in ROWS:
        vals = [t[col[num]] / t[col[den]] * scale if t[col[den]] else float('nan') for t in tot]
        line = label.ljust(w) + ''.join('%16s' % (fmt % v) for v in vals)
        if boot:
            with np.errstate(divide='ignore', invalid='ignore'):
                r = [b[:, col[num]] / b[:, col[den]] * scale for b in boot]
            f = fmt if fmt.startswith('%+') else fmt.replace('%.', '%+.')
            for k in range(1, len(groups)):
                d = r[k] - r[0]
                d = d[np.isfinite(d)]
                if len(d):
                    line += '%30s' % ((f + ' (' + f + ' to ' + f + ')') % (vals[k] - vals[0], np.percentile(d, 2.5), np.percentile(d, 97.5)))
        print(line + ('   n ' + '/'.join('%d' % t[col[den]] for t in tot) if den != 'games' else ''))
    print('games'.ljust(w) + ''.join('%16d' % len(g) for _, g in groups))


def load_cached(d, us):
    f = '%s/packmetrics-%d.json' % (d, us)
    if os.path.exists(f) and os.path.getmtime(f) >= os.path.getmtime(__file__):
        return json.load(open(f))
    s = game_stats(d, us)
    json.dump(s, open(f, 'w'))
    return s


def live(args):
    work = os.path.expanduser(args.work)
    rep, ext = work + '/rep', work + '/ext'
    os.makedirs(rep, exist_ok=True)
    rows = []
    for l in open(GAMES):
        try:
            r = json.loads(l)
        except ValueError:
            continue
        if r.get('version') in args.versions and r.get('status') == 'finished' and r.get('replay') and any(r.get('opp_name', '').startswith(o) or o in r.get('opp_name', '') for o in args.opps):
            if args.since and r.get('created', '') < args.since:
                continue
            if args.refset and r.get('refset') != args.refset:
                continue
            rows.append(r)
    seen, new = set(), []
    for r in rows:
        if r['match'] in seen:
            continue
        seen.add(r['match'])
        out = '%s/%s.repl26a' % (rep, r['match'])
        if not os.path.exists(out):
            try:
                with zipfile.ZipFile(os.path.join(REPO, r['replay'])) as z:
                    open(out, 'wb').write(z.read('replay.repl26a'))
                new.append(out)
            except Exception as e:
                print('missing replay', r['replay'], e, file=sys.stderr)
    if new:
        lst = work + '/new.txt'
        for k in range(0, len(new), 400):
            subprocess.run(['node', os.path.join(REPO, 'tools/replay/extract.mjs'), *new[k:k + 400], '--out', ext, '--threads', str(args.threads)], check=False, stdout=subprocess.DEVNULL)
    by_match = {os.path.basename(g['source']).split('.')[0]: g for g in json.load(open(ext + '/index.json'))['games']}
    groups = collections.defaultdict(dict)
    for r in rows:
        g = by_match.get(r['match'])
        if not g or not g.get('ok'):
            continue
        us = 0 if r['side'] == 'a' else 1
        s = load_cached(ext + '/' + g['dir'], us)
        s['win'] = int(r['result'] == 'win')
        opp = next(o for o in args.opps if r['opp_name'].startswith(o) or o in r['opp_name'])
        groups[(opp, r['version'])][(r['map'], r['side'], opp)] = s  # a cell played twice counts once (deterministic)
    for opp in args.opps + (['all'] if len(args.opps) > 1 else []):
        gs = []
        for v in args.versions:
            cells = {}
            for (o, ver), c in groups.items():
                if ver == v and (opp == 'all' or o == opp):
                    cells.update(c)
            gs.append(('v%d' % v, cells))
        if args.pair:
            common = set.intersection(*[set(c) for _, c in gs])
            gs = [(n, {k: c[k] for k in common}) for n, c in gs]
        print('\n== live, against %s ==' % opp)
        if all(c for _, c in gs):
            table([(n, list(c.values())) for n, c in gs])
        else:
            print('no games for', [n for n, c in gs if not c])


def local(args):
    gs = []
    for spec in args.groups:
        name, rest = spec.split('=', 1)
        d, us_name = rest.rsplit(':', 1)
        d = os.path.expanduser(d)
        cells = {}
        for g in json.load(open(d + '/index.json'))['games']:
            if not g.get('ok') or us_name not in g['teams']:
                continue
            us = g['teams'].index(us_name)
            opp = g['teams'][1 - us]
            if args.opp and args.opp not in opp:
                continue
            s = load_cached(d + '/' + g['dir'], us)
            s['win'] = int(g['winner'] == us)
            cells[(g['map'], us, opp)] = s
        gs.append((name, cells))
    if args.pair:
        common = set.intersection(*[set(c) for _, c in gs])
        gs = [(n, {k: c[k] for k in common}) for n, c in gs]
    print('\n== local%s ==' % (', against ' + args.opp if args.opp else ''))
    table([(n, list(c.values())) for n, c in gs])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='mode', required=True)
    a = sub.add_parser('live')
    a.add_argument('versions', nargs='+', type=int)
    a.add_argument('--opps', nargs='+', default=['Intercontinental Fish', 'Mite'])
    a.add_argument('--work', default='~/tmp-offload/packgive/live')
    a.add_argument('--since', help='only games created at or after this ISO time')
    a.add_argument('--refset')
    a.add_argument('--threads', type=int, default=8)
    a.add_argument('--pair', action='store_true')
    b = sub.add_parser('local')
    b.add_argument('groups', nargs='+', help='NAME=EXTDIR:OURTEAM')
    b.add_argument('--opp', help='only opponents whose team name contains this')
    b.add_argument('--pair', action='store_true')
    args = ap.parse_args()
    (live if args.mode == 'live' else local)(args)


if __name__ == '__main__':
    main()
