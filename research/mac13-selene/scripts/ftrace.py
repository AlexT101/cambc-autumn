"""sel-ftrace's FT lines (farm turns with an enemy in sight) joined with the replays' outcomes.

    python3 -I ftrace.py AN_DIR [--games N] [--dump FILE]

AN_DIR: extract.mjs output of the sel-ftrace batch. Each FT line is classified by the reason it hit no camp,
then scored by what followed: hit by an enemy champion within 5 rounds (after our turn), died within 10."""
import json, gzip, sys, os, re, zipfile, pickle
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

FT_RE = re.compile(rb'^[\s\0]*FT (\d+) (\d+) (\S) ([0-9a-f]+) (-?\d+) (\S) (\d+) (\d+) (-?\d+) (\d+) (\d+) (-?\d+) (\d+) ([0-9a-f]+) ([0-9a-f]+) ([0-9a-f]+) ([0-9a-f]+) ([0-9a-f]+) ([0-9a-f]+)\s*$', re.M)
D_RE = re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
ROOT = '/home/ubuntu/wt/mac13-selene'


def bits(f, i): return (f >> i) & 1


def reason(t):
    """t: dict of an FT line. The reason it hit no camp (or 'HIT')."""
    f = t['flags']
    if bits(f, 10): return 'HIT'
    site, st = t['site'], t['state']
    melee = bits(f, 15)
    rng = 1 if melee else 3
    if site == 'y': return 'willow-follow'
    if site in 'f0': return 'fuel/none'
    if site == 'P' or st == 'c': return 'cleared:capture-walk/hold'
    if st == 'r': return 'respawning-wait'
    if site == 'p': return 'pick-up'
    if bits(f, 1) or site in 'Bk': return 'banking'
    if site == 'q': return 'preheal-retreat'
    if site == 'o': return 'mono-stage'
    if site in 'jnx': return 'other-site-' + site
    if site == 's': return 'spell-path'
    if not bits(f, 2):
        if bits(f, 13): return 'search-walked(attack spent)'
        return 'attack-spent-before-farm'
    L0, L1 = t['L0'], t['L1']
    moved = bits(f, 12)
    if L0 <= rng:
        if bits(f, 7): return 'inrange:burning-spawn'
        if bits(f, 6): return 'inrange:holds-back-respawn'
        if bits(f, 5): return 'inrange:attack-refused'
        if st == 's' and not melee: return 'inrange:no-hit(asleep)'
        return 'inrange:no-hit'
    if not bits(f, 3):
        return 'walk-spent-before-farm' if not bits(f, 13) else 'search-walked(out of range)'
    if moved and L1 < L0:
        if L1 <= rng:
            return 'arrived-melee:no-hit-after-walk' if melee else 'arrived-ranged:walk-spent-attack'
        return 'approach-walk'
    imp = t['imp']
    if imp == 0:
        return 'sidestep:no-free-step' if moved else 'stand:no-free-step'
    final = t['final'] if bits(f, 14) else 0
    if imp & ~(final | t['zoned']) == 0:
        if imp & ~t['zoned'] == 0: kind = 'zone'
        elif imp & ~(t['kept'] | t['zoned']) == 0: kind = 'keep_out'
        elif imp & ~(t['avoid'] | t['kept'] | t['zoned']) == 0: kind = 'avoid(prism-hold/home-mono)'
        else: kind = 'step_guard'
        return ('sidestep' if moved else 'stand') + ':guard-' + kind
    return 'sidestep:other' if moved else 'stand:other'


def game(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json')))
        mp = json.load(open(os.path.join(d, meta['mapFile'])))
        R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
        src = meta['source'] if os.path.isabs(meta['source']) else os.path.join(ROOT, meta['source'])
        z = zipfile.ZipFile(src)
    except Exception as ex:
        return None
    FT = []
    D = {}
    for nm in z.namelist():
        if not nm.endswith('.stdout'): continue
        b = z.read(nm)
        for m in FT_RE.finditer(b):
            g = m.groups()
            FT.append(dict(r=int(g[0]), id=int(g[1]), site=g[2].decode(), flags=int(g[3], 16), g=int(g[4]), state=g[5].decode(),
                           L0=int(g[6]), L1=int(g[7]), hp=int(g[8]), bag=int(g[9]), ne=int(g[10]), et=int(g[11]), n8=int(g[12]),
                           imp=int(g[13], 16), strikes=int(g[14], 16), final=int(g[15], 16), kept=int(g[16], 16), avoid=int(g[17], 16),
                           zoned=int(g[18], 16), file=os.path.basename(src)))
        if FT and not D:
            for m in D_RE.finditer(b): D[(int(m.group(1)), int(m.group(2)))] = (m.group(3).decode(), int(m.group(4)))
    if not FT: return None
    tiles = defaultdict(list)
    for c in mp['camps']: tiles[c['group']].append((c['x'], c['y']))
    idx = {r: i for i, r in enumerate(R['round'])}
    champs = {c['id']: c for c in R['champions']}
    team = {c['id']: c['team'] for c in R['champions']}
    hits = defaultdict(list)  # victim -> [(round, turn slot)]
    deaths = defaultdict(list)
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('dmg'):
            for v, amt in e['dmg']:
                if v in team and team.get(e['a']) is not None and team[e['a']] != team[v] and amt > 0: hits[v].append((e['r'], e['t']))
        elif e['k'] == 'death': deaths[e['v']].append(e['r'])
    out = []
    for t in FT:
        i = idx.get(t['r'])
        c = champs.get(t['id'])
        if i is None or c is None or c['x'][i] is None: continue
        x, y = c['x'][i], c['y'][i]
        g = t['g']
        t['dd'] = min(max(abs(x - a), abs(y - b)) for a, b in tiles[g]) if g in tiles else -1
        myturn = c['turn'][i] if isinstance(c['turn'][i], int) else 0
        r = t['r']
        t['hit5'] = any((rr == r and tt > myturn) or r < rr <= r + 5 for rr, tt in hits[t['id']])
        t['died10'] = any(r <= rr <= r + 10 for rr in deaths[t['id']])
        # The farm target a few turns back: re-targeting churn.
        prev = [D.get((r - k, t['id'])) for k in (1, 2, 3)]
        t['churn'] = any(p is not None and p[1] != g for p in prev)
        t['why'] = reason(t)
        out.append(t)
    return out


def main():
    an = sys.argv[1]
    n = int(sys.argv[sys.argv.index('--games') + 1]) if '--games' in sys.argv else 10 ** 9
    idx = json.load(open(os.path.join(an, 'index.json')))
    dirs = [os.path.join(an, g['dir']) for g in idx['games']][:n]
    rows = []
    ng = 0
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game, dirs, chunksize=4):
            if r: rows += r; ng += 1
    if '--dump' in sys.argv: pickle.dump(rows, open(sys.argv[sys.argv.index('--dump') + 1], 'wb'))
    print('games', ng, 'FT rows', len(rows))
    cat = lambda t: 'hit' if t['why'] == 'HIT' else 'on' if t['dd'] == 0 else '<=3' if 0 <= t['dd'] <= 3 else '4-8' if 0 <= t['dd'] <= 8 else '>8'
    cc = Counter(cat(t) for t in rows)
    print('farmseen categories:', {k: f"{v / len(rows):.3f}" for k, v in cc.items()})
    def line(name, ts):
        n = len(ts)
        if not n: return
        full = sum(t['hp'] >= 99 for t in ts) / n
        h5 = sum(t['hit5'] for t in ts) / n
        d10 = sum(t['died10'] for t in ts) / n
        fh = [t for t in ts if t['hp'] >= 99]
        fh5 = sum(t['hit5'] for t in fh) / len(fh) if fh else float('nan')
        ne = sorted(t['ne'] for t in ts)[n // 2]
        bag = sorted(t['bag'] for t in ts)[n // 2]
        print(f"{name:42s} {n / ng:7.1f} {full:6.0%} {h5:7.1%} {fh5:8.1%} {d10:7.1%} {ne:5d} {bag:5d}")
    print(f"{'reason':42s} {'/game':>7s} {'full':>6s} {'hit<=5':>7s} {'fullhit5':>8s} {'died10':>7s} {'nearE':>5s} {'bag':>5s}")
    line('BASELINE: hit a camp in sight', [t for t in rows if t['why'] == 'HIT'])
    near = [t for t in rows if t['why'] != 'HIT' and 0 < t['dd'] <= 3]
    line('ALL near<=3 not hitting', near)
    for k, _ in Counter(t['why'] for t in near).most_common(): line(k, [t for t in near if t['why'] == k])
    far = [t for t in rows if t['dd'] > 8 and t['why'] != 'HIT']
    print('\n>8 away, not hitting:', len(far) / ng, 'a game; target changed within 3 turns', f"{sum(t['churn'] for t in far) / max(1, len(far)):.1%}")
    for k, _ in Counter(t['why'] for t in far).most_common(8): print('   ', k, f"{sum(t['why'] == k for t in far) / len(far):.1%}")


if __name__ == '__main__':
    main()
