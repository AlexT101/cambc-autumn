"""The gem race: per game, first round each team's hold (tributed + carried by living bodies) reaches 1000, the
round the winner's tribute reaches 1000, and the loser's carried bag at the end.

    python3 race.py EXTRACT_DIR [--by-bot NAME]
"""
import argparse, gzip, json, statistics
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def one(args):
    d, bot = args
    d = Path(d)
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
    except Exception:
        return None
    res = meta['result']
    w = res['winner']
    names = [t['name'] for t in meta['teams']]
    ch = R['champions']
    nR = len(R['round'])
    out = {'rounds': res['rounds'], 'w': w}
    for t in (0, 1):
        ids = [c for c in ch if c['team'] == t]
        first = None
        for ix in range(nR):
            h = R['gems'][t][ix] + sum(c['gems'][ix] for c in ids if c['alive'][ix])
            if h >= 1000 and first is None:
                first = ix + 1
        out[t] = {'hold1000': first, 'trib_end': R['gems'][t][nR - 1],
                  'carried_end': sum(c['gems'][nR - 1] for c in ids if c['alive'][nR - 1]),
                  'prism_end': sum(c['gems'][nR - 1] for c in ids if c['alive'][nR - 1] and c['id'] in
                                   {m['id'] for m in meta['champions'] if m['name'] == 'Prism'})}
    out['names'] = names
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    a = ap.parse_args()
    dirs = [str(p.parent) for p in Path(a.dir).glob('*/meta.json')]
    with ProcessPoolExecutor(16) as ex:
        rs = [r for r in ex.map(one, [(x, None) for x in dirs], chunksize=8) if r]
    c = Counter()
    lc, lp, lt, rounds = [], [], [], []
    for r in rs:
        w = r['w']
        L = 1 - w
        rounds.append(r['rounds'])
        lc.append(r[L]['carried_end'])
        lp.append(r[L]['prism_end'])
        lt.append(r[L]['trib_end'])
        if r['rounds'] >= 2000:
            c['to_2000'] += 1
        if r[L]['hold1000'] is not None and (r[w]['hold1000'] is None or r[L]['hold1000'] < r[w]['hold1000']):
            c['loser_held_1000_first'] += 1
        if r[L]['hold1000'] is not None:
            c['loser_held_1000'] += 1
        if r[L]['trib_end'] + r[L]['carried_end'] >= 1000:
            c['loser_end_hold_1000'] += 1
    n = len(rs)
    print(n, 'games; rounds median', statistics.median(rounds), 'mean', statistics.mean(rounds))
    print('loser end: tributed mean', statistics.mean(lt), 'carried', statistics.mean(lc), 'by Prism', statistics.mean(lp))
    for k, v in c.items():
        print(f'{k:24s} {v} ({100 * v / n:.1f}%)')
    q = sorted(lc)
    print('loser carried quantiles', [q[int(n * f)] for f in (0.1, 0.25, 0.5, 0.75, 0.9)])


if __name__ == '__main__':
    main()
