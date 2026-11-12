"""The Prism's economy and combat totals of arms against a reference on the same games: python3 econ.py REF ARM..."""
import json, os, sys
O = os.path.expanduser('~/tmp-offload/prismlife/out')


def load(name):
    rows = {}
    for opp in ('Flp4', 'Mt3q'):
        for line in open(f'{O}/{name}-{opp}.jsonl'):
            g = json.loads(line); f = g['file']; us = 0 if f.rsplit('.', 1)[0].endswith('-12') else 1
            ours = [c for c in g['champions'] if c['team'] == us]; pr = [c for c in ours if c['type'] == 6]
            if not pr: continue
            rows[(opp, f)] = dict(win=g['winner'] == us, deaths=pr[0]['deaths'], gems=pr[0]['collectedGems'], gold=pr[0]['earnedGold'], kills=pr[0]['kills'],
                                  taken=pr[0]['championDamageTaken'], monster=pr[0]['monsterDamageDone'], team_gems=sum(c['collectedGems'] for c in ours), rounds=g['rounds'])
    return rows


names = sys.argv[1:]
A = {n: load(n) for n in names}
keys = [k for k in A[names[0]] if all(k in A[n] for n in names)]
print(len(keys), 'paired Prism games')
cols = ('win', 'deaths', 'gems', 'gold', 'kills', 'taken', 'monster', 'team_gems', 'rounds')
print(f'{"":14s}' + ''.join(f'{c:>12s}' for c in cols))
base = {c: sum(A[names[0]][k][c] for k in keys) / len(keys) for c in cols}
for n in names:
    m = {c: sum(A[n][k][c] for k in keys) / len(keys) for c in cols}
    print(f'{n:14s}' + ''.join(f'{m[c]:12.2f}' if n == names[0] else f'{100 * (m[c] / base[c] - 1):+11.1f}%' for c in cols))
