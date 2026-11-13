"""Why winning tributes are cancelled manually in endgame races. For each manual cancel of a winning tribute (endrace.py's
attempts), the canceller's D-line branch that turn ('t' = continue_tribute's unsafe path; anything else = the turn went on,
i.e. the enemy-stop path), the turns the channel had run and had left, and whether any enemy could stop it before its end:
a stunner whose stun is ready by the time it walks within its stun reach, a lock carrier walking within 2 of the altar, by
straight Chebyshev walks (no dashes, no terrain), or none (a cancel no stun / lock forced; lethal damage not modelled).
Usage: py c5_cancel.py ANALYSIS_DIR [TEAM_NAME]   (TEAM_NAME: only that team's cancels, e.g. c5-race)"""
import gzip, json, sys, zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from endrace import game as race

# name -> (stun slot, reach from the caster to the channeller)
STUN = {'Prism': (0, 4), 'Ryth': (0, 5), 'Tavi': (1, 4), 'Ren': (0, 4), 'Cassi': (1, 4), 'Heart of Ruin': (1, 3), 'Marcella': (0, 1)}
ONLY = sys.argv[2] if len(sys.argv) > 2 else None


def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def game(d):
    r = race(d)
    if not r: return None
    meta = json.loads((d/'meta.json').read_text())
    R = json.load(gzip.open(d/'rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz', 'rt')]
    team = {c['id']: c['team'] for c in meta['champions']}
    name = {c['id']: c['name'] for c in meta['champions']}
    ch = {int(c['id']): c for c in R['champions']}
    rix = {x: i for i, x in enumerate(R['round'])}
    try:
        z = zipfile.ZipFile(meta['source'])
        out = [z.read(f'team-{s}.stdout').decode(errors='replace') for s in 'ab']
    except Exception:
        return None
    dl = [{}, {}]
    for t in (0, 1):
        for l in out[t].splitlines():
            if l.startswith('D '):
                p = l.split()
                dl[t][(int(p[1]), int(p[2]))] = p[3]
    tnames = [t['name'] for t in meta['teams']]
    starts = {}
    rows = []
    w = r['w']
    for e in ev:
        if e['k'] == 'tribute_start':
            t = team[e['a']]
            sc = R['gems'][t][max(0, e['r'] - 2)]
            if e['gems'] + sc >= 1000: starts[e['a']] = e
            else: starts.pop(e['a'], None)
        elif e['k'] in ('tribute_end', 'death'):
            starts.pop(e.get('a', e.get('v')), None)
        elif e['k'] == 'tribute_cancel' and e['a'] in starts:
            s = starts.pop(e['a'])
            a = e['a']; t = team[a]
            if ONLY and tnames[t] != ONLY: continue
            if e.get('cause') != 'manual': continue
            rnd = e['r']; i = rix.get(rnd)
            if i is None: continue
            me = ch[a]; pos = (me['x'][i], me['y'][i])
            if pos[0] is None: continue
            alt = tuple(s['altar'])
            left = e.get('left', 0)
            ran = rnd - s['r']
            dmg = (me['hp'][i - 1] - me['hp'][i]) if i > 0 and me['hp'][i - 1] is not None and me['hp'][i] is not None else 0
            near, stopper = 99, None
            for j, c in ch.items():
                if team[j] == t or not c['alive'][i] or c['x'][i] is None: continue
                ep = (c['x'][i], c['y'][i])
                dd = cheb(ep, pos)
                near = min(near, dd)
                nm = name[j]
                if nm in STUN:
                    slot, reach = STUN[nm]
                    cd = c[f'cd{slot}'][i] or 0
                    arrive = max(0, dd - reach)
                    if max(arrive, cd) < left:
                        stopper = min(stopper or 99, max(arrive, cd))
                cons = c['cons'][i] or [0, 0]
                if len(cons) > 2 and cons[2] > 0 and max(0, cheb(ep, alt) - 2) < left:
                    stopper = min(stopper or 99, max(0, cheb(ep, alt) - 2))
            rows.append(dict(side='winner' if t == w else 'loser', br=dl[t].get((rnd, a), '?'), ran=ran, left=left, near=near,
                             stop=stopper, dmg=dmg > 0, who=name[a], gems=s['gems']))
    return rows


if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(game, dirs, chunksize=8):
            if o: rows.extend(o)
    print(f'{len(rows)} manual cancels of winning tributes in races')
    for side in ('winner', 'loser', None):
        S = [x for x in rows if side is None or x['side'] == side]
        if not S: continue
        print(f'== {side or "all"}: {len(S)}')
        print('  branch at the cancel (t = unsafe path; other = enemy-stop path):', Counter(x['br'] for x in S).most_common(8))
        print('  channel turns run before the cancel:', Counter(min(x['ran'], 5) for x in S).most_common())
        for br in ('t', 'other'):
            B = [x for x in S if (x['br'] == 't') == (br == 't')]
            if not B: continue
            nostop = [x for x in B if x['stop'] is None]
            print(f'  [{br}] {len(B)}: damaged this round {sum(x["dmg"] for x in B)}; no enemy could stun/lock it in time '
                  f'{len(nostop)} ({len(nostop)/len(B):.0%}), of those damaged {sum(x["dmg"] for x in nostop)}')
            print('     nearest enemy:', sorted(Counter(min(x['near'], 12) for x in B).items()))
            print('     turns left:', [sorted(x['left'] for x in B)[int(q*(len(B)-1))] for q in (.25, .5, .75)],
                  'holder', Counter(x['who'] for x in B).most_common(4))
            print('     stopper arrives in (turns):', sorted(Counter(x['stop'] for x in B if x['stop'] is not None).items())[:12])
