"""Ward placements per team: wards per 100 alive champion-rounds, share placed on a bush tile, and how often a
champion's bush ward is replaced by an off-bush ward (one ward per champion, so the new one removes it); per
champion type too. Definitions as subreports/replay.md section 5 (whole game, every ward event).

  py wards.py                                                 # ladder games of the top six and us since 10-16
  py wards.py --src replays/batch-20261017-091937-928141 --team nemesis rival
Selection options: gamesel.py.
"""
import json, gzip, os, collections
from concurrent.futures import ProcessPoolExecutor
import gamesel
ROOT = gamesel.ROOT


def game(args):
    d, names = args
    m = json.load(open(os.path.join(ROOT, d, 'meta.json'), encoding='utf-8'))
    R = json.load(gzip.open(os.path.join(ROOT, d, 'rounds.json.gz')))
    mp = json.load(open(os.path.join(ROOT, 'maps', m['map']['hash'] + '.json')))
    bushes = set(map(tuple, mp['bushes']))
    name = {c['id']: c['name'] for c in m['champions']}
    team = {c['id']: c['team'] for c in m['champions']}
    out = collections.Counter()
    last = {}
    for l in gzip.open(os.path.join(ROOT, d, 'events.jsonl.gz'), 'rt'):
        e = json.loads(l)
        if e['k'] != 'ward':
            continue
        a = e['a']; t = names[team[a]]; bush = tuple(e['to']) in bushes
        for key in (t, (t, name[a])):
            out[key, 'wards'] += 1
            out[key, 'bush'] += bush
            if a in last and last[a]:
                out[key, 'replaced_bush'] += 1
                out[key, 'bush_to_open'] += not bush
        last[a] = bush
    for c in R['champions']:
        t = names[c['team']]
        out[t, 'alive'] += sum(c['alive'])
        out[(t, name[c['id']]), 'alive'] += sum(c['alive'])
    return out


if __name__ == '__main__':
    p = gamesel.parser(__doc__, team=gamesel.TOPS)
    a = p.parse_args()
    games = gamesel.select(a)
    tot = collections.Counter()
    with ProcessPoolExecutor(a.threads) as ex:
        for r in ex.map(game, games, chunksize=8):
            tot += r
    print(f'{len(games)} games. wards, per 100 alive champion-rounds, share on a bush, share of bush wards replaced by an off-bush ward')
    for t in a.team:
        keys = [t] + sorted(k[0] for k in tot if isinstance(k[0], tuple) and k[0][0] == t and k[1] == 'alive')
        for key in keys:
            n = tot[key, 'wards']
            if not tot[key, 'alive']:
                continue
            label = t[:22] if key == t else f'  {key[1]}'
            print(f"  {label:24s} wards {n:6d}  per 100 {100 * n / tot[key, 'alive']:5.2f}  on bush {tot[key, 'bush'] / max(1, n):.2f}  "
                  f"bush ward -> off-bush {tot[key, 'bush_to_open'] / max(1, tot[key, 'replaced_bush']):.2f} (n {tot[key, 'replaced_bush']})")
