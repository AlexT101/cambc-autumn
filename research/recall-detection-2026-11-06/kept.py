"""Kept recalls only (a 2nd round-end window exists): real or abandoned by health, gems and spawn distance at that window,
and how many turns were left when abandoned ones were cancelled.

py research/recall-detection-2026-11-06/kept.py > kept.txt
"""
import collections, gzip, json, os, sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(__file__))
import collect as C


def game(row):
    d = os.path.join(C.CACHE, row['dir'])
    meta = json.load(open(os.path.join(d, 'meta.json')))
    lab, _ = C.labels(row['source'], meta)
    if not any(lab):
        return {}
    mp = json.load(open(os.path.normpath(os.path.join(d, meta['mapFile']))))
    R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
    rix = {r: i for i, r in enumerate(R['round'])}
    ch = {c['id']: c for c in R['champions']}
    out, st = collections.Counter(), {}
    for line in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt'):
        e = json.loads(line)
        if e['k'] == 'recall_start':
            st[e['a']] = e
        elif e['k'] in ('recall_end', 'recall_cancel') and e['a'] in st:
            s = st.pop(e['a']); c = ch[e['a']]; t = lab[c['team']]
            i = rix.get(s['r'] + 1)
            if t is None or i is None or e['r'] <= s['r'] + 1 or c['chan'][i] != 1:
                continue  # no 2nd window
            team = t.split('-v')[0] if t.startswith('ocean') else t
            if e['k'] == 'recall_end': cls = 'real'
            elif e['cause'] == 'manual': cls = 'abandoned'
            else: cls = 'real'
            hp = c['hp'][i] / c['maxHp'][i]
            hpb = 'hp<33' if hp < .33 else 'hp<50' if hp < .5 else 'hp<100' if hp < 1 else 'full'
            gb = 'gems0' if c['gems'][i] == 0 else 'gems>0'
            dist = C.spawn_dist(mp['spawn'][c['team']], c['x'][i], c['y'][i])
            db = 'd<=10' if dist <= 10 else 'd>10'
            out[(team, cls, hpb, gb, db, e['left'] if cls == 'abandoned' else -1)] += 1
    return out


if __name__ == '__main__':
    ix = json.load(open(os.path.join(C.CACHE, 'index.json')))
    seen, rows = set(), []
    for g in ix['games']:
        if g['dir'] not in seen:
            seen.add(g['dir']); rows.append(g)
    tot = collections.Counter()
    with Pool(8) as p:
        for c in p.imap_unordered(game, rows, chunksize=4):
            tot.update(c)
    teams = sorted({k[0] for k in tot})
    for t in teams:
        S = lambda f: sum(v for k, v in tot.items() if k[0] == t and f(k))
        print(f'== {t}: kept {S(lambda k: True)}, real {S(lambda k: k[1] == "real")}, abandoned {S(lambda k: k[1] == "abandoned")}')
        print('  abandoned by turns left at cancel:', sorted(collections.Counter({k[5]: v for k, v in tot.items() if False}).items()),
              {l: S(lambda k, l=l: k[1] == 'abandoned' and k[5] == l) for l in range(0, 5)})
        for f, vals in ((2, ['hp<33', 'hp<50', 'hp<100', 'full']), (3, ['gems0', 'gems>0']), (4, ['d<=10', 'd>10'])):
            cells = []
            for v in vals:
                r = S(lambda k: k[1] == 'real' and k[f] == v); n = S(lambda k: k[f] == v)
                cells.append(f'{v}: {100 * r / n:.1f}% real of {n}' if n else f'{v}: -')
            print('  ' + '; '.join(cells))
        for rule, f in (('hp<100 or gems>0', lambda k: k[2] != 'full' or k[3] == 'gems>0'),
                        ('hp<50 or gems>0', lambda k: k[2] in ('hp<33', 'hp<50') or k[3] == 'gems>0'),
                        ('gems>0', lambda k: k[3] == 'gems>0')):
            r = S(lambda k: k[1] == 'real' and f(k)); n = S(f); R = S(lambda k: k[1] == 'real')
            print(f'  (c) and {rule}: precision {100 * r / n:.1f}%, recall of kept-real {100 * r / R:.1f}%')
