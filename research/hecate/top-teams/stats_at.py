"""Median Focus/Strength/max hp per champion type at rounds 200/400 by team."""
from collections import defaultdict
from statistics import median
from multiprocessing import Pool
from common import games, load, TOP, US, SHORT


def feat(rec):
    g = load(rec)
    out = []
    for c in g.champs:
        ch = g.ch(c['id'])
        row = {}
        for r in (150, 300, 450):
            if r - 1 < len(ch['foc']):
                row[r] = (ch['foc'][r - 1], ch['str'][r - 1], ch['maxHp'][r - 1], ch['earned'][r - 1])
        out.append((g.names[c['team']], c['name'], row))
    return out


if __name__ == '__main__':
    with Pool(14) as p:
        res = p.map(feat, games(since='2026-10-16T21:18'), chunksize=4)
    S = defaultdict(list)
    for rr in res:
        for n, ty, row in rr:
            for r, v in row.items():
                S[(n, ty, r)].append(v)
    for ty in ('Stellar', 'Ren', 'Cassi', 'Varg', 'Ryth', 'Tavi'):
        print('###', ty, '(Focus / Strength / maxHp / lifetime gold) at r150, r300, r450')
        for n in TOP + [US]:
            cells = []
            for r in (150, 300, 450):
                v = S.get((n, ty, r))
                if v and len(v) >= 5:
                    cells.append(f"{median(x[0] for x in v):.0f}/{median(x[1] for x in v):.0f}/{median(x[2] for x in v):.0f}/{median(x[3] for x in v):.0f}")
            if cells:
                print(f'- {SHORT[n]}: ' + ' | '.join(cells))
