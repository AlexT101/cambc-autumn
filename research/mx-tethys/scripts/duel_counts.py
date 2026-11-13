"""Line C mechanism counts for an A/B batch, CAND side vs REF side: wins, deaths, Prism deaths and kills a game, first
Prism death split (games with both Prisms), Cassi/Issac pair deaths to the enemy Prism, captures and captured gems by
side of the map (own/mid/enemy by the group's distance to the two spawns), Prism gems collected.

    py research/mx-tethys/scripts/duel_counts.py ANALYSIS_ROOT BATCH_NAME CAND_TEAM_NAME
"""
import gzip, json, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(arg):
    dd, cand = arg
    try:
        m = json.loads((dd / 'meta.json').read_text())
        mp = json.loads((dd / m['mapFile']).resolve().read_text())
        ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    names = {c['id']: c['name'] for c in m['champions']}
    team = {c['id']: c['team'] for c in m['champions']}
    side = lambda t: 'C' if t == cand else 'R'
    out = Counter()
    out['games'] = 1
    out[side(m['result']['winner']) + ' wins'] += 1
    prism = {team[i]: i for i in names if names[i] == 'Prism'}
    sp = mp['spawn']
    cen = lambda s: ((s['minX'] + s['maxX']) / 2, (s['minY'] + s['maxY']) / 2)
    gside = {}
    for g in mp['groups']:
        xs = [t[0] for t in g['tiles']]; ys = [t[1] for t in g['tiles']]
        c = (sum(xs) / len(xs), sum(ys) / len(ys))
        gside[g['id']] = [cheb(c, cen(sp[0])), cheb(c, cen(sp[1]))]
    first = None
    pair_seen = set()
    for e in ev:
        if e['k'] == 'death':
            v = e['v']; t = team[v]; s = side(t)
            killer = e.get('by')
            out[s + ' deaths'] += 1
            if names[v] == 'Prism':
                out[s + ' prism deaths'] += 1
                if first is None and len(prism) == 2: first = s
                if e['r'] <= 300: out[s + ' prism deaths r<=300'] += 1
            if names[v] in ('Cassi', 'Issac'):
                if (e['r'], t) not in pair_seen:
                    pair_seen.add((e['r'], t))
                    out[s + ' pair deaths'] += 1
                    if killer in names and names[killer] == 'Prism': out[s + ' pair deaths to Prism'] += 1
            if killer in names and team[killer] != t:
                ks = side(team[killer])
                if names[killer] == 'Prism': out[ks + ' prism kills'] += 1
            out[s + ' gems lost dying'] += e.get('gems') or 0
        elif e['k'] == 'capture':
            t = e['team']
            if t not in (0, 1): continue
            da, de = gside[e['g']][t], gside[e['g']][1 - t]
            share = da / max(1e-9, da + de)
            where = 'own' if share < 0.4 else 'enemy' if share > 0.6 else 'mid'
            gems = sum(x[1] for x in e.get('shares', []))
            out[f'{side(t)} captures {where}'] += 1
            out[f'{side(t)} capture gems {where}'] += gems
    if len(prism) == 2:
        out['both prisms'] += 1
        out['first prism death ' + (first or 'none')] += 1
        for c in m['champions']:
            if c['name'] == 'Prism': out[side(c['team']) + ' prism gems collected'] += c['stats']['collectedGems']
    return out


def main():
    root = Path(sys.argv[1]); bname = sys.argv[2]; cand_name = sys.argv[3]
    ix = json.loads((root / 'index.json').read_text())
    args = []
    for row in ix['games']:
        if bname in row['source'] and cand_name in row['teams']:
            args.append((root / row['dir'], row['teams'].index(cand_name)))
    tot = Counter()
    with ProcessPoolExecutor(40) as ex:
        for x in ex.map(one, args, chunksize=8):
            if x: tot += x
    g = tot['games']
    print('games', g, 'both prisms', tot['both prisms'])
    keys = sorted({k[2:] for k in tot if k[:2] in ('C ', 'R ')})
    print(f"{'metric':28s} {'CAND':>9s} {'REF':>9s}  (per game)")
    for k in keys:
        print(f"{k:28s} {tot['C ' + k] / g:9.3f} {tot['R ' + k] / g:9.3f}")
    b = max(1, tot['both prisms'])
    print('first prism death (of games with both): CAND %.1f%%  REF %.1f%%  none %.1f%%' % (
        100 * tot['first prism death C'] / b, 100 * tot['first prism death R'] / b, 100 * tot['first prism death none'] / b))


if __name__ == '__main__':
    main()
