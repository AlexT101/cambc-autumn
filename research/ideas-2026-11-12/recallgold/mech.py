"""Recall-gold mechanism metrics from extracted replays (tools/replay/extract.mjs --out DIR) of a bot against the rt bodies.

    python3 mech.py EXTROOT REFTAG TAG [TAG ...]

Per game, for our side: kept recalls (lasting past their first turn end) that landed, the gold carried when they
started, gold spent in the shop, gold held while alive (mean over our champions' alive rounds), gold at death and
at the game's end. For the bodies: their kept recalls our champions cancelled, and the gold they carried then.
Games are paired by (body, map, side) against REFTAG: mean TAG - REF with a bootstrap 95% CI.
"""
import sys, os, json, gzip, random
from multiprocessing import Pool


def one(d):
    try:
        meta = json.load(open(d + '/meta.json')); R = json.load(gzip.open(d + '/rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    except Exception:
        return None
    names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
    src = os.path.basename(meta['source']); bdir = os.path.basename(os.path.dirname(meta['source']))
    opp = 'Flp4' if 'Flp4' in bdir else 'Mt3q'
    stem = src.rsplit('.', 1)[0]; mp, side = stem.split('-', 1)[1].rsplit('-', 1)
    team = {c['id']: c['team'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}; rounds = R['round']; idx = {r: i for i, r in enumerate(rounds)}
    at = lambda a, r, k: ch[a][k][idx.get(r - 1, idx.get(r, 0))]
    ours = [a for a in ch if team[a] == us]
    m = dict(win=float(meta['result']['winner'] == us), end=meta['result']['rounds'], land=0, land_gold=0.0, shop=0.0,
             cut=0, cut_gold=0.0, own_cut=0, own_cut_gold=0.0, death_gold=0.0, deaths=0, end_gold=0.0, held=0.0, earned=0.0)
    start = {}; prev = None
    for e in ev:
        k = e['k']
        if k == 'recall_start': start[e['a']] = e['r']
        elif k == 'recall_end' and team[e['a']] == us:
            m['land'] += 1; m['land_gold'] += at(e['a'], start.get(e['a'], e['r']), 'gold')
        elif k == 'shop' and e.get('a') in team and team[e['a']] == us:
            m['shop'] += -e.get('gold', 0) if e.get('gold', 0) < 0 else 0
        elif k == 'recall_cancel' and e.get('cause') in ('damage', 'stun') and e.get('left', 9) <= 3 and prev is not None \
                and prev['s'] == e['s'] and prev['k'] in ('attack', 'cast') and prev.get('a') in team and team[prev['a']] != team[e['a']]:
            if team[e['a']] != us: m['cut'] += 1; m['cut_gold'] += at(e['a'], e['r'], 'gold')
            else: m['own_cut'] += 1; m['own_cut_gold'] += at(e['a'], e['r'], 'gold')
        elif k == 'death' and team[e['v']] == us:
            m['deaths'] += 1; m['death_gold'] += at(e['v'], e['r'], 'gold')
        prev = e
    last = len(rounds) - 1
    alive_n = 0; held = 0.0
    for a in ours:
        c = ch[a]
        m['end_gold'] += c['gold'][last]; m['earned'] += c['earned'][last]
        for i in range(0, len(rounds), 5):
            if c['alive'][i]: held += c['gold'][i]; alive_n += 1
    m['held'] = held / max(1, alive_n)
    return (opp, mp, side), m


def load(root):
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(12) as pool: return dict(r for r in pool.map(one, dirs, chunksize=8) if r)


KEYS = ['win', 'end', 'land', 'land_gold', 'shop', 'held', 'end_gold', 'deaths', 'death_gold', 'earned', 'cut', 'cut_gold', 'own_cut', 'own_cut_gold']


def ci(xs):
    random.seed(1); n = len(xs); mu = sum(xs) / n
    bs = sorted(sum(random.choice(xs) for _ in range(n)) / n for _ in range(300))
    return mu, bs[7], bs[292]


def main():
    root, ref, tags = sys.argv[1], sys.argv[2], sys.argv[3:]
    R = load(os.path.join(root, ref))
    print(f'REF {ref}: {len(R)} games; per game:', ', '.join(f'{k} {sum(m[k] for m in R.values())/len(R):.2f}' for k in KEYS))
    print('  (land_gold, cut_gold, death_gold are sums per game; per event: land %.1f, cut %.1f, death %.1f)' % (
        sum(m['land_gold'] for m in R.values()) / max(1, sum(m['land'] for m in R.values())),
        sum(m['cut_gold'] for m in R.values()) / max(1, sum(m['cut'] for m in R.values())),
        sum(m['death_gold'] for m in R.values()) / max(1, sum(m['deaths'] for m in R.values()))))
    for t in tags:
        T = load(os.path.join(root, t)); keys = sorted(set(R) & set(T))
        print(f'{t} - {ref}: {len(keys)} paired games')
        for k in KEYS:
            mu, lo, hi = ci([T[g][k] - R[g][k] for g in keys])
            print(f'  {k:13s} {mu:+9.3f} ({lo:+.3f} .. {hi:+.3f})')
        print('  per event: land gold %.1f, cut gold %.1f, games differing %.1f%%' % (
            sum(T[g]['land_gold'] for g in keys) / max(1, sum(T[g]['land'] for g in keys)),
            sum(T[g]['cut_gold'] for g in keys) / max(1, sum(T[g]['cut'] for g in keys)),
            100 * sum(any(T[g][k] != R[g][k] for k in KEYS) for g in keys) / len(keys)))


if __name__ == '__main__': main()
