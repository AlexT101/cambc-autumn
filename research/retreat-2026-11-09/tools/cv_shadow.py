"""Chase verdict shadow run: each CV line (a chase turn, P; the strike search's aim, A or T) joined with its outcome.

usage: cv_shadow.py EXTRACT_DIR BOT [--window W] [--procs N] [--json OUT]

CV fields: tag round chaser target dist range full slack now stun own_ground held bag steps hp x y engaged channel
  full/slack: the target's least hits running home from our pursuit (0, 1, 2 = many; -1 no plan); now: in our
  pursuers' first-turn reach.
Classes: clean (full or slack 0), one, doomed (2 on both), none (no plan).
Outcome: the target killed by our team (its death with `by` ours) within W rounds of the line; episodes are runs
of P lines by one chaser on one target with gaps of at most 2 rounds, a kill counted to the episode's end + 3.
"""
import argparse, gzip, json, zipfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

F = ['tag', 'round', 'chaser', 'target', 'dist', 'range', 'full', 'slack', 'now', 'stun', 'own', 'held', 'bag', 'steps', 'hp',
     'x', 'y', 'engaged', 'channel']


def klass(c):
    f, s = c['full'], c['slack']
    if f < 0: return 'none'
    if f == 0 or s == 0: return 'clean'
    if f == 1 or s == 1: return 'one'
    return 'doomed'


def one(args):
    ex, g, bot, W = args
    try:
        meta = json.load(open(f"{ex}/{g['dir']}/meta.json"))
        R = json.load(gzip.open(f"{ex}/{g['dir']}/rounds.json.gz"))
        ev = [json.loads(l) for l in gzip.open(f"{ex}/{g['dir']}/events.jsonl.gz", 'rt')]
        z = zipfile.ZipFile(g['source'])
    except Exception:
        return None
    team_of = {c['id']: c['team'] for c in meta['champions']}
    ridx = {r: i for i, r in enumerate(R['round'])}
    chi = {c['id']: c for c in R['champions']}
    out = []
    for t in (0, 1):
        if g['teams'][t] != bot: continue
        lines = z.read(f"team-{'ab'[t]}.stdout").decode(errors='replace').replace('\x00', '').splitlines()
        cv, dec = [], {}
        for l in lines:
            p = l.split()
            if len(p) == 20 and p[0] == 'CV':
                try:
                    c = dict(zip(F, [p[1]] + [float(x) if '.' in x else int(x) for x in p[2:]]))
                except ValueError:
                    continue
                cv.append(c)
            elif len(p) >= 4 and p[0] == 'D':
                try: dec[(int(p[1]), int(p[2]))] = p[3]
                except ValueError: pass
        # deaths of enemies (and their linked partners) by our team; our deaths
        kills = defaultdict(list)  # target id -> rounds killed by us
        mine = defaultdict(list)
        for e in ev:
            if e['k'] != 'death': continue
            v = e['v']
            if team_of.get(v) == t:
                mine[v].append(e['r'])
            elif e.get('by') is not None and team_of.get(e['by']) == t:
                kills[v].append(e['r'])
                if e.get('linked') is not None: kills[e['linked']].append(e['r'])
        # the target's steps home at its previous round's tile (running: fewer now)
        def prev_pos(v, r):
            k = ridx.get(r - 1)
            if k is None or v not in chi or not chi[v]['alive'][k]: return None
            return chi[v]['x'][k], chi[v]['y'][k]
        for c in cv:
            r, v = c['round'], c['target']
            c['kill'] = any(r <= q <= r + W for q in kills.get(v, []))
            c['died'] = any(r <= q <= r + W for q in mine.get(c['chaser'], []))
            pp = prev_pos(v, r)
            c['moved'] = None if pp is None else (pp != (c['x'], c['y']))
            c['k'] = klass(c)
            c['dec'] = dec.get((r, c['chaser']))
            c['game'] = g['dir']
            c['t'] = t
            c['kills'] = kills.get(v, [])
            c['mydeaths'] = mine.get(c['chaser'], [])
        out.extend(cv)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ex'); ap.add_argument('bot')
    ap.add_argument('--window', type=int, default=10)
    ap.add_argument('--procs', type=int, default=16)
    ap.add_argument('--json')
    a = ap.parse_args()
    ix = json.load(open(f'{a.ex}/index.json'))
    rows, games = [], 0
    with ProcessPoolExecutor(a.procs) as pool:
        for r in pool.map(one, [(a.ex, g, a.bot, a.window) for g in ix['games']], chunksize=8):
            if r is None: continue
            games += 1
            rows.extend(r)
    teamgames = sum(1 for g in ix['games'] for t in g['teams'] if t == a.bot)
    print(f'games {games} team-games {teamgames} CV lines {len(rows)}')
    for tag in ('P', 'A', 'T'):
        rs = [c for c in rows if c['tag'] == tag]
        if not rs: continue
        print(f'\n== {tag} lines: {len(rs)} ({len(rs) / teamgames:.1f} a team-game); kill = target killed by us within {a.window}')
        C = Counter(c['k'] for c in rs)
        K = Counter(c['k'] for c in rs if c['kill'])
        D = Counter(c['k'] for c in rs if c['died'])
        for k in ('clean', 'one', 'doomed', 'none'):
            n = C[k]
            if n: print(f'  {k:7s} {n:7d} ({n / len(rs):5.1%}, {n / teamgames:5.1f}/tg)  kill {K[k] / n:6.1%}  chaser died {D[k] / n:6.1%}')
        # clean split by situation
        cl = [c for c in rs if c['k'] == 'clean']
        if cl:
            print('  clean, by situation:')
            def show(name, f):
                s = [c for c in cl if f(c)]
                if s: print(f'    {name:28s} {len(s):7d} ({len(s) / len(cl):5.1%})  kill {sum(c["kill"] for c in s) / len(s):6.1%}')
            show('in range now', lambda c: c['dist'] <= c['range'])
            show('out of range', lambda c: c['dist'] > c['range'])
            show('target on our ground', lambda c: c['own'])
            show('target holds a capture', lambda c: c['held'] > 0)
            show('target carries gems', lambda c: c['bag'] > 0)
            show('target hurt (<47%)', lambda c: c['hp'] < 0.47)
            show('target channelling', lambda c: c['channel'] != 0)
            show('target stunned', lambda c: c['stun'])
            show('target moved last round', lambda c: c['moved'] is True)
            show('target stood last round', lambda c: c['moved'] is False)
            show('out of range, no capture/bag', lambda c: c['dist'] > c['range'] and not c['held'] and not c['bag'])
        oth = [c for c in rs if c['k'] in ('one', 'doomed')]
        if oth:
            print('  one/doomed, out of range:', sum(1 for c in oth if c['dist'] > c['range']),
                  'kill', f"{sum(c['kill'] for c in oth if c['dist'] > c['range']) / max(1, sum(1 for c in oth if c['dist'] > c['range'])):.1%}")
        # by distance
        print('  kill rate by dist - range (clean / one / doomed):')
        for gap in range(-1, 7):
            cells = []
            for k in ('clean', 'one', 'doomed'):
                s = [c for c in rs if c['k'] == k and max(-1, min(6, c['dist'] - c['range'])) == gap]
                cells.append(f'{len(s):6d} {sum(c["kill"] for c in s) / len(s) if s else 0:6.1%}')
            print(f'    gap {gap:2d}: ' + ' | '.join(cells))
    # episodes of P lines
    eps = []
    by = defaultdict(list)
    for c in rows:
        if c['tag'] == 'P': by[(c['game'], c['t'], c['chaser'], c['target'])].append(c)
    for key, cs in by.items():
        cs.sort(key=lambda c: c['round'])
        cur = []
        for c in cs:
            if cur and c['round'] - cur[-1]['round'] > 2:
                eps.append(cur); cur = []
            cur.append(c)
        if cur: eps.append(cur)
    print(f'\n== P episodes: {len(eps)} ({len(eps) / teamgames:.1f}/tg), turns {sum(len(e) for e in eps)}')
    def ek(e):
        r0, r1 = e[0]['round'], e[-1]['round']
        return any(r0 <= q <= r1 + 3 for q in e[0]['kills'])
    def ed(e):
        r0, r1 = e[0]['round'], e[-1]['round']
        return any(r0 <= q <= r1 + 3 for q in e[0]['mydeaths'])
    for name, f in (('first turn clean', lambda e: e[0]['k'] == 'clean'), ('first turn one', lambda e: e[0]['k'] == 'one'),
                    ('first turn doomed', lambda e: e[0]['k'] == 'doomed'), ('first turn none', lambda e: e[0]['k'] == 'none'),
                    ('every turn clean', lambda e: all(c['k'] == 'clean' for c in e)),
                    ('some turn doomed', lambda e: any(c['k'] == 'doomed' for c in e))):
        s = [e for e in eps if f(e)]
        if s:
            print(f'  {name:20s} eps {len(s):6d} turns {sum(len(e) for e in s):7d}  kill {sum(ek(e) for e in s) / len(s):6.1%}  '
                  f'chaser died {sum(ed(e) for e in s) / len(s):6.1%}  mean len {sum(len(e) for e in s) / len(s):.2f}')
    # turns that a futility rule would drop: clean P turns; of those, kill
    cl = [c for c in rows if c['tag'] == 'P' and c['k'] == 'clean']
    print(f'\nclean P turns {len(cl) / teamgames:.1f}/tg of P {sum(1 for c in rows if c["tag"] == "P") / teamgames:.1f}/tg; '
          f'no-kill clean turns {sum(1 for c in cl if not c["kill"]) / teamgames:.1f}/tg')
    if a.json:
        json.dump([{k: v for k, v in c.items() if k not in ('kills', 'mydeaths')} for c in rows], open(a.json, 'w'))


if __name__ == '__main__':
    main()
