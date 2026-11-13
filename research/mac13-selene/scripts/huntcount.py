# sel-hunt debug smoke: hunt turns, episodes, sight, kills of the target and hunter deaths.
# usage: python3 huntcount.py BATCH_DIR EXTRACT_DIR   (EXTRACT_DIR from tools/replay/extract.mjs --out)
import json, gzip, sys, os, re, zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
BATCH, EX = sys.argv[1], sys.argv[2]
idx = {os.path.basename(g['source']): g for g in json.load(open(os.path.join(EX, 'index.json')))['games']}
H = re.compile(r'^HUNT (\d+) (\d+) e(\d+) at (-?\d+),(-?\d+) d (\d+) vis (\d)')
C = re.compile(r'^HUNT-CAND (\d+) (\d+) e(\d+) d (\d+) clean (\d)')
P = re.compile(r'^HUNT-PRICE (\d+) (\d+) e(\d+) .* (hunt|farm)$')
def game(f):
    g = idx.get(f)
    if not g or not g.get('ok'): return None
    z = zipfile.ZipFile(os.path.join(BATCH, f))
    turns, cand, price = [], Counter(), Counter()
    side = None
    for t in ('a', 'b'):
        txt = z.read(f'team-{t}.stdout').decode(errors='replace')
        for line in txt.splitlines():
            if m := H.match(line): turns.append((int(m[1]), int(m[2]), int(m[3]), int(m[6]), int(m[7]))); side = t
            elif m := C.match(line): cand['verdicts'] += 1; cand['clean'] += m[5] == '1'; side = t
            elif m := P.match(line): price[m[4]] += 1
    ev = [json.loads(l) for l in gzip.open(os.path.join(EX, g['dir'], 'events.jsonl.gz'), 'rt')]
    deaths = [(e['r'], e['v'], e.get('by')) for e in ev if e['k'] == 'death']
    # episodes: same hunter and target, gaps of 2 rounds or less
    eps = []
    for r, h, tgt, d, vis in sorted(turns):
        if eps and eps[-1]['h'] == h and eps[-1]['t'] == tgt and r - eps[-1]['end'] <= 2:
            e = eps[-1]; e['end'] = r; e['n'] += 1; e['vis'] |= vis; e['dmin'] = min(e['dmin'], d)
        else: eps.append(dict(h=h, t=tgt, start=r, end=r, n=1, vis=vis, dmin=d))
    for e in eps:
        w = range(e['start'], e['end'] + 4)
        e['kill'] = any(r in w and v == e['t'] and by == e['h'] for r, v, by in deaths)
        e['teamkill'] = any(r in w and v == e['t'] for r, v, by in deaths)
        e['died'] = any(r in w and v == e['h'] for r, v, by in deaths)
    return dict(turns=len(turns), eps=eps, cand=cand, price=price, side=side)
def main():
    files = sorted(f for f in os.listdir(BATCH) if f.endswith('.repl26a'))
    with ProcessPoolExecutor(24) as ex: res = [r for r in ex.map(game, files, chunksize=8) if r]
    n = len(res); eps = [e for r in res for e in r['eps']]
    print('games', n, 'hunt turns/game', round(sum(r['turns'] for r in res) / n, 2), 'games with a hunt', sum(1 for r in res if r['turns']))
    print('episodes', len(eps), 'per game', round(len(eps) / n, 3))
    if eps:
        print('mean turns/episode', round(sum(e['n'] for e in eps) / len(eps), 2))
        print('reach sight', sum(e['vis'] for e in eps), 'min dist <=4', sum(e['dmin'] <= 4 for e in eps))
        print('target killed by hunter', sum(e['kill'] for e in eps), 'by anyone', sum(e['teamkill'] for e in eps), 'hunter died', sum(e['died'] for e in eps))
    cand = sum((r['cand'] for r in res), Counter()); price = sum((r['price'] for r in res), Counter())
    print('candidates', dict(cand), 'priced', dict(price))
if __name__ == '__main__': main()
