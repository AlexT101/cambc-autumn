"""Fight statistics per game for the Mite side ('m') and ours ('o'), from extract.mjs output (as mstats.py).
    py fstats.py live EXT ROWS.json OUT.jsonl  |  py fstats.py local EXT OUT.jsonl
- Kills and deaths by Vesper and by Prism; deaths with a bag of 11+; champion damage done and taken.
- Engagements: champion-on-champion damage clustered in time (a gap of GAP rounds starts a new one). For each, the
  kills each side made up to 2 rounds after its last hit, and which side hit first.
- Retreat: each time a champion takes champion damage and lives, did it open its distance to the nearest enemy by
  2+ within 3 rounds? Rates are binned by health after the hit (<0.4, 0.4-0.7, >=0.7) and by a bag of 11+."""
import gzip, json, os, sys, collections
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(__file__))
from mstats import load
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
GAP = 6

def game(job):
    ext, d, mite, extra = job
    try: meta, R, ev, mp = load(ext, d)
    except Exception: return None
    ch = R['champions']; team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    C = {c['id']: c for c in ch}; n = len(R['round'])
    S = {t: collections.Counter() for t in (0, 1)}
    for c in meta['champions']:
        t = c['team']; S[t]['dmg_done'] += c['stats']['championDamageDone']; S[t]['dmg_taken'] += c['stats']['championDamageTaken']
        if c['name'] == 'Vesper Vale': S[t]['has_vesper'] = 1
        if c['name'] == 'Prism': S[t]['has_prism'] = 1
    hits = []  # (round, attacker team, victim id)
    for e in ev:
        k = e['k']; r = e['r']
        if k in ('attack', 'cast') and e.get('a') in team:
            for v, amt in e.get('dmg', []):
                if v in team and team[v] != team[e['a']] and amt > 0: hits.append((r, team[e['a']], v))
        elif k == 'death':
            v = e['v']; t = team[v]; i = min(max(r - 2, 0), n - 1); bag = C[v]['gems'][i]
            S[t]['deaths'] += 1; S[t]['deaths_bag11'] += bag >= 11
            if typ[v] == 'Vesper Vale': S[t]['vesper_deaths'] += 1
            if typ[v] == 'Prism': S[t]['prism_deaths'] += 1
            by = e.get('by')
            if by is not None and team.get(by) == 1 - t:
                S[1 - t]['kills'] += 1
                if typ[by] == 'Vesper Vale': S[1 - t]['vesper_kills'] += 1
                if typ[by] == 'Prism': S[1 - t]['prism_kills'] += 1
    # Engagements.
    deaths = [(e['r'], team[e['v']]) for e in ev if e['k'] == 'death' and e.get('by') is not None and team.get(e['by']) == 1 - team[e['v']]]
    hits.sort(); eng = []
    for r, t, v in hits:
        if eng and r - eng[-1]['end'] < GAP: eng[-1]['end'] = r
        else: eng.append({'start': r, 'end': r, 'first': t})
    for t in (0, 1):
        S[t]['eng'] = len(eng); S[t]['eng_first'] = sum(1 for x in eng if x['first'] == t)
    for x in eng:
        k = [sum(1 for r, dt in deaths if x['start'] <= r <= x['end'] + 2 and dt == 1 - t) for t in (0, 1)]
        for t in (0, 1):
            S[t]['eng_kills'] += k[t]; S[t]['eng_won'] += k[t] > k[1 - t]; S[t]['eng_bloody'] += (k[0] + k[1]) > 0
            if x['first'] == t: S[t]['first_kills'] += k[t]; S[t]['first_lost'] += k[1 - t]
    # Retreat after a hit.
    done = set()
    for r, t, v in hits:
        i = r - 1
        if (v, r) in done or i + 3 >= n or not C[v]['alive'][i] or not C[v]['alive'][i + 3]: continue
        done.add((v, r)); vt = team[v]
        def near(j):
            p = (C[v]['x'][j], C[v]['y'][j])
            if None in p: return None
            ds = [cheb(p, (x['x'][j], x['y'][j])) for x in ch if x['team'] != vt and x['alive'][j] and x['x'][j] is not None]
            return min(ds) if ds else None
        a, b = near(i), near(i + 3)
        if a is None or b is None or a > 6: continue
        h = C[v]['hp'][i] / max(1, C[v]['maxHp'][i]); bag = C[v]['gems'][i]
        key = 'lo' if h < 0.4 else 'mid' if h < 0.7 else 'hi'
        if bag >= 11: key += '_bag'
        S[vt]['hit_' + key] += 1; S[vt]['ret_' + key] += (b - a) >= 2
    w = meta['result'].get('winner') if isinstance(meta.get('result'), dict) else None
    return {'dir': d, 'rounds': n, 'mite_team': mite, 'mite_win': (w == mite) if w is not None else None,
            'm': dict(S[mite]), 'o': dict(S[1 - mite]), **extra}

def main():
    mode = sys.argv[1]; ext = sys.argv[2]
    idx = json.load(open(ext + '/index.json'))['games']; jobs = []
    if mode == 'live':
        rows = json.load(open(sys.argv[3])); out = sys.argv[4]
        for g in idx:
            mid = os.path.basename(g['source'])[:-8]
            if mid not in rows: continue
            r = rows[mid]; mite = 1 if r['side'] == 'a' else 0
            jobs.append((ext, g['dir'], mite, {'map': r['map'].replace('_', '-'), 'side': r['side'], 'version': r['version'], 'win_g': g['winner']}))
    else:
        out = sys.argv[3]
        for g in idx:
            base = os.path.basename(g['source'])[:-8]; num, rest = base.split('-', 1); mname, o = rest.rsplit('-', 1)
            side = 'a' if o == '12' else 'b'; mite = 1 if side == 'a' else 0
            jobs.append((ext, g['dir'], mite, {'map': mname.replace('_', '-'), 'side': side, 'win_g': g['winner']}))
    with Pool(int(os.environ.get('OMP_NUM_THREADS', '8'))) as p: res = [x for x in p.map(game, jobs, chunksize=4) if x]
    for x in res:
        if x['mite_win'] is None: x['mite_win'] = x['win_g'] == x['mite_team']
    with open(out, 'w') as fh:
        for x in res: fh.write(json.dumps(x) + '\n')
    print(len(res), 'games ->', out)

if __name__ == '__main__': main()
