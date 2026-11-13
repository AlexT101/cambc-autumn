"""Team-fight coherence: rounds where 2+ of a team's bodies have an enemy within RADIUS; their branches (D lines:
R retreat, A/C attack/chase, other); whether the group mixes retreaters with fighters; deaths within 5 rounds by
role and mix. Mirror (winner W / loser L). Needs debug replays (D lines) and extract.mjs output.

    py research/mx-tethys/scripts/coherence.py ANALYSIS_ROOT BATCH_NAME [MAX_GAMES]
"""
import gzip, json, re, sys, zipfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

WT = Path('/home/ubuntu/wt/mx-tethys')
RADIUS = 6
D_RE = re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def role(b):
    if b == 'R': return 'R'
    if b in ('A', 'C'): return 'F'
    return 'O'


def one(dd):
    try:
        m = json.loads((dd / 'meta.json').read_text())
        R = json.load(gzip.open(dd / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
        z = zipfile.ZipFile(WT / m['source'])
    except Exception:
        return None
    br = {}
    for name in ('team-a.stdout', 'team-b.stdout'):
        try:
            data = z.read(name)
        except KeyError:
            continue
        for r, cid, b, _, _ in D_RE.findall(data):
            br[(int(r), int(cid))] = b.decode()
    w = m['result']['winner']
    team = {c['id']: c['team'] for c in m['champions']}
    deaths = defaultdict(list)
    for e in ev:
        if e['k'] == 'death': deaths[e['v']].append(e['r'])
    out = Counter()
    champs = R['champions']
    for i, r in enumerate(R['round']):
        pos = {c['id']: (c['x'][i], c['y'][i]) for c in champs if c['alive'][i] and c['x'][i] is not None}
        for t in (0, 1):
            side = 'W' if t == w else 'L'
            ours = [c for c in pos if team[c] == t]
            theirs = [c for c in pos if team[c] != t]
            S = [c for c in ours if any(cheb(pos[c], pos[e]) <= RADIUS for e in theirs)]
            if len(S) < 2: continue
            roles = {c: role(br.get((r, c), '?')) for c in S}
            kinds = set(roles.values())
            mix = 'mixed' if ('R' in kinds and 'F' in kinds) else 'allR' if kinds == {'R'} else 'noR'
            out[(side, 'rounds', mix)] += 1
            for c, ro in roles.items():
                out[(side, 'bodies', mix, ro)] += 1
                if any(r < d <= r + 5 for d in deaths[c]): out[(side, 'die5', mix, ro)] += 1
    return out


def main():
    root = Path(sys.argv[1]); bname = sys.argv[2]; mx = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
    dirs = []
    for dd in sorted(root.iterdir()):
        mf = dd / 'meta.json'
        if mf.exists() and bname in (json.loads(mf.read_text()).get('source') or ''):
            dirs.append(dd)
        if len(dirs) >= mx: break
    tot = Counter(); n = 0
    with ProcessPoolExecutor(40) as ex:
        for c in ex.map(one, dirs, chunksize=4):
            if c: tot.update(c); n += 1
    print('games', n)
    for s in 'WL':
        rr = {k[2]: v for k, v in tot.items() if k[0] == s and k[1] == 'rounds'}
        print(s, 'fight rounds/game (2+ bodies with an enemy within', RADIUS, '):', {k: round(v / n, 1) for k, v in rr.items()})
        for mix in ('mixed', 'allR', 'noR'):
            for ro in 'RFO':
                b = tot[(s, 'bodies', mix, ro)]
                if b: print(f'  {s} {mix:6s} {ro}: body-rounds/game {b / n:6.1f}  die within 5: {tot[(s, "die5", mix, ro)] / b * 100:5.2f}%')


if __name__ == '__main__':
    main()
