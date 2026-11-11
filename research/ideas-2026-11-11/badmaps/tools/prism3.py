"""Mechanism table for local batches: big-bag Prism deaths a game beside the win rate. usage: prism3.py EXTROOT ARM..."""
import json, gzip, os, sys, collections
from multiprocessing import Pool
BAG = 40

def one(arg):
    ext, g = arg
    d = ext + '/' + g['dir']
    try:
        meta = json.load(open(d + '/meta.json'))
        ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    except Exception:
        return None
    src = g['source']; us = 0 if os.path.basename(src).endswith('-12.repl26a') else 1
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    a = collections.Counter()
    a['n'] = 1; a['win'] = int(g['winner'] == us); a['rounds'] = g['rounds']
    a['prism_game'] = int(any(typ[c] == 'Prism' and team[c] == us for c in typ))
    for e in ev:
        k = e['k']
        if k == 'death':
            mine = team[e['v']] == us; gems = e.get('gems', 0) or 0
            if mine:
                a['deaths'] += 1
                if typ[e['v']] == 'Prism':
                    a['prism_deaths'] += 1; a['prism_lost'] += gems
                    if gems >= BAG: a['prism_big'] += 1
                else:
                    a['np_lost'] += gems
                    if gems >= BAG: a['np_big'] += 1
            else:
                a['kills'] += 1; a['kill_gems'] += gems
        elif k == 'capture':
            for cid, gm, go in e['shares']: a['cap' if team[cid] == us else 'them_cap'] += gm
    opp = 'Mite' if 'Mt3q' in src else 'Fish'
    return opp, a

if __name__ == '__main__':
    root = sys.argv[1]
    print('| arm | body | games | win% | big-bag Prism deaths /game | Prism gems lost /game | non-Prism gems lost /game | our deaths /game | kills /game | captured us vs them |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    for arm in sys.argv[2:]:
        ext = root + '/' + arm
        games = json.load(open(ext + '/index.json'))['games']
        with Pool(32) as p: res = [r for r in p.map(one, [(ext, g) for g in games], chunksize=16) if r]
        agg = collections.defaultdict(collections.Counter)
        for opp, a in res: agg[opp].update(a); agg['both'].update(a)
        for opp in ('both', 'Fish', 'Mite'):
            a = agg[opp]; n = max(1, a['n'])
            print('| %s | %s | %d | %.2f | %.3f (%d; %.3f per Prism game) | %.1f | %.1f | %.2f | %.2f | %.0f vs %.0f |' % (
                arm, opp, a['n'], 100 * a['win'] / n, a['prism_big'] / n, a['prism_big'], a['prism_big'] / max(1, a['prism_game']), a['prism_lost'] / n, a['np_lost'] / n,
                a['deaths'] / n, a['kills'] / n, a['cap'] / n, a['them_cap'] / n))
