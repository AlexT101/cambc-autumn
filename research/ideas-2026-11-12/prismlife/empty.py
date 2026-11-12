"""Exposure the Prism takes with nothing to cast: python3 empty.py EXTROOT/TAG   (variants/pl-trace)
Every Prism turn that ended in an enemy's reach (PLE worst > 0), by whether a spell was ready then or would be on its
next turn (cooldowns from the extraction at the round's end), whether a step out of every reach was open at the turn's
start (PLS least == 0), and its decision. Health lost before its next turn start is summed per cell: the share of all
the damage it takes that falls in turns where it had nothing to cast and could have stood out of reach."""
import collections, gzip, json, os, sys, zipfile
from multiprocessing import Pool
import trace as T
ROOT = '/home/ubuntu/cambc-autumn'


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json'))); R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
        names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
        out = zipfile.ZipFile(os.path.join(ROOT, meta['source'])).read(f"team-{'ab'[us]}.stdout").decode('utf-8', 'replace')
    except Exception: return None
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    pr = [c for c in team if typ[c] == 'Prism' and team[c] == us]
    if not pr: return None
    p = pr[0]; S = {}; E = {}; D = {}
    for line in out.replace('\x00', '').splitlines():
        try: T.parse(line.strip(), p, S, E, D)
        except (ValueError, IndexError): pass
    P = next(c for c in R['champions'] if c['id'] == p); idx = {q: i for i, q in enumerate(R['round'])}
    deaths = {x['r'] for x in ev if x['k'] == 'death' and x['v'] == p}
    cast = collections.defaultdict(bool)
    for x in ev:
        if x['k'] == 'cast' and x.get('a') == p: cast[x['r']] = True
    rows = []
    for q, e in E.items():
        if q not in S or q not in idx: continue
        i = idx[q]
        if q + 1 in S: lost = max(0, e['hp'] - S[q + 1]['hp'])
        elif q + 1 in deaths or q in deaths: lost = e['hp']
        else: lost = 0
        cd = min(P['cd0'][i], P['cd1'][i])  # at the round's end: 0 or 1 means ready on its next turn
        j = idx.get(q - 1, i)
        c0, c1 = P['cd0'][j], P['cd1'][j]  # during its turn in q: the value at the end of q - 1
        rows.append((e['dec'], e['worst'] > 0, cd, S[q]['least'] == 0 and S[q]['open'] > 0, cast[q], lost, e['worst'], (e['x'], e['y']) != (S[q]['x'], S[q]['y']), S[q]['stunned'], q + 1 in deaths or q in deaths, c0, c1, S[q]['least'] / max(1, S[q]['hp']), e['worst'] / max(1, e['hp'])))
    return rows


if __name__ == '__main__':
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool: R = [r for g in pool.map(one, dirs, chunksize=8) if g for r in g]
    tot = sum(r[5] for r in R); n = len(R)
    print(f'{n} traced Prism turns; health lost before the next turn, all: {tot:.0f} ({tot / 1104:.0f} a Prism game)')

    def line(name, S):
        if not S: return
        l = sum(r[5] for r in S)
        print(f'  {name:64s} {len(S):6d} turns ({100 * len(S) / n:5.2f}%)  health lost {100 * l / tot:5.1f}% of all  ({l / len(S):5.1f} a turn)  deaths {sum(r[9] for r in S)}')
    X = [r for r in R if r[1]]
    line('ended in reach', X)
    line('ended out of reach', [r for r in R if not r[1]])
    for dec in ('F', 'C', 'R', 'B', 'T', 'P'):
        line(f'  in reach, decision {dec}', [r for r in X if r[0] == dec])
    print()
    line('in reach, cast this turn', [r for r in X if r[4]])
    line('in reach, no cast, a spell ready next turn (cooldown <= 1)', [r for r in X if not r[4] and r[2] <= 1])
    line('in reach, no cast, both spells cooling 2+ more turns', [r for r in X if not r[4] and r[2] >= 2])
    for dec in ('F', 'C', 'R', 'B', 'T', 'P'):
        Y = [r for r in X if not r[4] and r[2] >= 2 and r[0] == dec and not r[8]]
        line(f'  ... decision {dec}: a step out of reach was open', [r for r in Y if r[3]])
        line(f'  ... decision {dec}: none was', [r for r in Y if not r[3]])
    Y = [r for r in X if not r[4] and r[2] <= 1 and not r[8]]
    for dec in ('F', 'C', 'R'):
        line(f'  spell ready next turn, decision {dec}: a step out was open', [r for r in Y if r[0] == dec and r[3]])
    print()
    RR = [r for r in X if r[0] == 'R' and not r[8]]
    line('R turns ending in reach (not stunned)', RR)
    line('  cast', [r for r in RR if r[4]])
    for nm, f in (('stun ready, not cast', lambda r: r[10] == 0), ('area ready, not cast', lambda r: r[11] == 0), ('nothing ready', lambda r: r[10] > 0 and r[11] > 0)):
        Y = [r for r in RR if not r[4] and f(r)]
        line(f'  {nm}', Y)
        line(f'    a step out of reach was open', [r for r in Y if r[3]])
        line(f'    the least step still took 25%+ of health', [r for r in Y if not r[3] and r[12] >= 0.25])
        line(f'    the least step took under 25%', [r for r in Y if not r[3] and r[12] < 0.25])
