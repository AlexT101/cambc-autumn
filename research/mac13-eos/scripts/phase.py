"""Phase/tempo study of extracted games: per team at checkpoints, score, carried, gold earned, deaths; winner vs loser.
py phase.py EXTRACT_DIR"""
import gzip, json, sys
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

CK = [50, 100, 150, 200, 300, 400, 500, 600, 800, 1000]


def game(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
    except Exception:
        return None
    n = len(R['round'])
    sc = R['gems']
    fin = [sc[0][-1], sc[1][-1]]
    ch = R['champions']
    # winner: from meta if present
    w = meta.get('winner')
    if w is None:
        res = meta.get('result') or {}
        w = res.get('winner')
    if w is None:
        w = 0 if fin[0] > fin[1] else 1 if fin[1] > fin[0] else None
    if isinstance(w, str):
        w = 0 if w in ('A', 'a', '0') else 1
    out = {'n': n, 'w': w, 'ck': {}, 'map': meta['map']['name'], 'picks': meta['draft']['picks']}
    for c in CK:
        if c > n:
            break
        i = c - 1
        row = []
        for t in (0, 1):
            carried = sum(x['gems'][i] for x in ch if int(x['team']) == t and x['alive'][i])
            earned = sum(x['earned'][i] for x in ch if int(x['team']) == t)
            deaths = sum(x['deaths'][i] for x in ch if int(x['team']) == t)
            dead = sum(1 for x in ch if int(x['team']) == t and not x['alive'][i])
            prism = max([x['gems'][i] for x in ch if int(x['team']) == t and x.get('name', '') == 'Prism'] or [-1])
            row.append((sc[t][i], carried, earned, deaths, dead, prism))
        out['ck'][c] = row
    # first to score+carried >= 1000
    first = None
    for i in range(n):
        for t in (0, 1):
            carried = sum(x['gems'][i] for x in ch if int(x['team']) == t and x['alive'][i])
            if sc[t][i] + carried >= 1000 and first is None:
                first = (t, i + 1)
        if first:
            break
    out['first1000'] = first
    return out


def main():
    root = Path(sys.argv[1])
    dirs = [d for d in root.iterdir() if (d / 'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex:
        games = [g for g in ex.map(game, dirs, chunksize=8) if g and g['w'] is not None]
    print('games', len(games), 'mean rounds', sum(g['n'] for g in games) / len(games))
    print('round2000 share', sum(g['n'] >= 2000 for g in games) / len(games))
    print('ck  | W score carr gold deaths | L score carr gold deaths | P(win | ahead in score+carried) P(win|ahead gold) P(win|fewer deaths)')
    for c in CK:
        rows = [g for g in games if c in g['ck']]
        if not rows:
            continue
        agg = defaultdict(float)
        ah = [0, 0]; gd = [0, 0]; dd = [0, 0]
        for g in rows:
            W, L = g['ck'][c][g['w']], g['ck'][c][1 - g['w']]
            for k in range(4):
                agg['W%d' % k] += W[k]; agg['L%d' % k] += L[k]
            sw, sl = W[0] + W[1], L[0] + L[1]
            if sw != sl:
                ah[0] += sw > sl; ah[1] += 1
            if abs(W[2] - L[2]) > 1:
                gd[0] += W[2] > L[2]; gd[1] += 1
            if W[3] != L[3]:
                dd[0] += W[3] < L[3]; dd[1] += 1
        m = len(rows)
        print(f"{c:4d} {m:5d} | {agg['W0']/m:6.0f} {agg['W1']/m:5.0f} {agg['W2']/m:6.0f} {agg['W3']/m:4.2f} | {agg['L0']/m:6.0f} {agg['L1']/m:5.0f} {agg['L2']/m:6.0f} {agg['L3']/m:4.2f} | {ah[0]/max(1,ah[1]):.3f} ({ah[1]}) {gd[0]/max(1,gd[1]):.3f} {dd[0]/max(1,dd[1]):.3f} ({dd[1]})")
    f = [g for g in games if g['first1000']]
    print('first to 1000 wins', sum(g['first1000'][0] == g['w'] for g in f) / len(f), 'of', len(f),
          'median round', sorted(g['first1000'][1] for g in f)[len(f) // 2])
    # tempo: gold-lead and gem-lead combos at 200
    for c in (150, 300):
        both = [0, 0]; gem_only = [0, 0]; gold_only = [0, 0]
        for g in games:
            if c not in g['ck']:
                continue
            a, b = g['ck'][c]
            ga, gb = a[0] + a[1], b[0] + b[1]
            lead = 0 if (ga > gb) else 1
            glead = 0 if a[2] > b[2] else 1
            if ga == gb:
                continue
            if lead == glead:
                both[0] += lead == g['w']; both[1] += 1
            elif True:
                gem_only[0] += lead == g['w']; gem_only[1] += 1
        print(c, 'gem&gold lead wins', both[0] / max(1, both[1]), both[1], '| gem lead but gold behind wins', gem_only[0] / max(1, gem_only[1]), gem_only[1])


if __name__ == '__main__':
    main()
