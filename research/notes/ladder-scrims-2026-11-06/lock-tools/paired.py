#!/usr/bin/env python3
"""paired.py BASE_BATCH VAR_BATCH [--json OUT]: a gated variant against normal play, game by game.

Both batches play the same maps and sides against the same opponent, and a gate changes nothing before it first
fires, so each game is paired: its outcome in normal play (BASE, e.g. oc-lock-obs2) and with the variant (VAR).
For the games where VAR's hold gate fired (a PLG line with the hold bit): wins gained and lost, by the first
firing's round and lead. Games where it never fired should agree (a check on fuel noise)."""
import collections, json, sys, zipfile
from pathlib import Path

def outcomes(d, first=False):
    d = Path(d)
    res = json.loads((d / 'results.json').read_text())
    out = {}
    for m in res['matches']:
        if not m.get('replay'): continue
        name = Path(m['replay']).stem
        key = name.split('-', 1)[1]  # map stem and order, without the index
        row = dict(won=m['winner'] == 0, rounds=m['rounds'], map=Path(m['map']).stem, order=name.rsplit('-', 1)[1])
        if first:
            team = 'a' if row['order'] == '12' else 'b'
            with zipfile.ZipFile(m['replay']) as z:
                txt = z.read(f'team-{team}.stdout').replace(b'\0', b'').decode('utf-8', 'replace')
            row['fire'] = None; row['veto'] = 0
            for line in txt.splitlines():
                f = line.split()
                if not f: continue
                if f[0] == 'PLG' and len(f) > 7 and int(f[7]) >= 2 and row['fire'] is None:
                    row['fire'] = dict(r=int(f[1]), lead=int(f[3]), max_bag=int(f[4]), sum_bag=int(f[5]), enemy=int(f[6]))
                if f[0] == 'PLVETO': row['veto'] += 1
        out[key] = row
    return out

base, var = outcomes(sys.argv[1]), outcomes(sys.argv[2], first=True)
keys = sorted(set(base) & set(var))
fired = [k for k in keys if var[k]['fire']]
quiet = [k for k in keys if not var[k]['fire']]
agree = sum(base[k]['won'] == var[k]['won'] for k in quiet)
print(f'{len(keys)} paired games; gate fired in {len(fired)}; never fired: {len(quiet)}, outcomes agree in {agree} ({100 * agree / max(1, len(quiet)):.1f}%)')
gain = [k for k in fired if var[k]['won'] and not base[k]['won']]
loss = [k for k in fired if base[k]['won'] and not var[k]['won']]
print(f'fired: normal play won {sum(base[k]["won"] for k in fired)}, the variant {sum(var[k]["won"] for k in fired)}: +{len(gain)} -{len(loss)} (net {len(gain) - len(loss):+d}, '
      f'{100 * (len(gain) - len(loss)) / max(1, len(keys)):+.2f} points of all games)')
def bucket(f):
    rb = min(f['r'] // 250 * 250, 1750); lb = '1-49' if f['lead'] < 50 else '50-199' if f['lead'] < 200 else '200+'
    return rb, lb
tab = collections.defaultdict(lambda: [0, 0, 0])
for k in fired:
    b = bucket(var[k]['fire']); t = tab[b]; t[0] += 1; t[1] += k in gain; t[2] += k in loss
print('| first fired, round | lead 1-49 | lead 50-199 | lead 200+ |  (games: +gained -lost)')
print('|---|---|---|---|')
for rb in range(0, 2000, 250):
    cells = [tab.get((rb, lb)) for lb in ('1-49', '50-199', '200+')]
    if any(cells): print(f'| {rb} | ' + ' | '.join(f'{c[0]}: +{c[1]} -{c[2]}' if c else '-' for c in cells) + ' |')
if '--json' in sys.argv:
    json.dump([dict(key=k, base=base[k]['won'], var=var[k]['won'], **var[k]['fire'], map=var[k]['map'], order=var[k]['order']) for k in fired],
              open(sys.argv[sys.argv.index('--json') + 1], 'w'))
