"""Per-game behaviour statistics of both teams, for the Mite side ('m') and ours ('o'), from extract.mjs output.
    py mstats.py live EXT ROWS.json OUT.jsonl     (our live scrims: ROWS maps match id -> our side)
    py mstats.py local EXT OUT.jsonl              (ab.py replays NNN-map-12/21: bot 1 = ours, bot 2 = the body)
Measured per team: result, captures and capture gold/gems to r300, earned gold at checkpoints, tributes (count, bag
sizes, first round, big bags), deaths and kills (by r300 and all game), gems lost to deaths, attackers within 4 of
each champion it killed (convergence), teammates within 5 (cohesion), share of body-rounds on the enemy half,
locks, crystals, wards, casts on champions, recalls, Prism's largest bag, picks."""
import gzip, json, os, sys, math, collections
from multiprocessing import Pool
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
MAPS = {}

def load(ext, d):
    p = f'{ext}/{d}'
    meta = json.load(open(p + '/meta.json')); R = json.load(gzip.open(p + '/rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(p + '/events.jsonl.gz', 'rt')]
    mf = os.path.join(ext, 'maps', os.path.basename(meta['mapFile']))
    if mf not in MAPS: MAPS[mf] = json.load(open(mf))
    return meta, R, ev, MAPS[mf]

def game(job):
    ext, d, mite, extra = job
    try: meta, R, ev, mp = load(ext, d)
    except Exception as e: return None
    ch = R['champions']; team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    n = len(R['round'])
    spc = [((s['minX'] + s['maxX']) / 2, (s['minY'] + s['maxY']) / 2) for s in mp['spawn']]
    S = {t: collections.Counter() for t in (0, 1)}; L = {t: collections.defaultdict(list) for t in (0, 1)}
    for e in ev:
        k = e['k']; r = e['r']
        if k == 'capture':
            t = e['team']; S[t]['caps'] += 1
            if r <= 300:
                S[t]['caps300'] += 1
                for cid, gm, go in e['shares']: S[t]['capgems300'] += gm; S[t]['capgold300'] += go
            for cid, gm, go in e['shares']: S[t]['capgems'] += gm
        elif k == 'tribute_start':
            t = team[e['a']]; S[t]['trib_start'] += 1
        elif k == 'tribute_end':
            t = team[e['a']]; S[t]['trib'] += 1; S[t]['trib_gems'] += e['gems']; L[t]['bags'].append(e['gems'])
            L[t]['trib_r'].append(r)
            if e['gems'] >= 100: S[t]['trib100'] += 1
        elif k == 'death':
            v = e['v']; t = team[v]; S[t]['deaths'] += 1; S[t]['died_gems'] += e.get('gems', 0)
            if r <= 300: S[t]['deaths300'] += 1
            if e.get('by') is not None and 'camp' not in e and team.get(e['by']) == 1 - t:
                S[1 - t]['kills'] += 1
                if r <= 300: S[1 - t]['kills300'] += 1
                i = min(max(r - 2, 0), n - 1); at = tuple(e['at'])
                L[1 - t]['conv'].append(sum(1 for x in ch if x['team'] == 1 - t and x['alive'][i] and cheb((x['x'][i], x['y'][i]), at) <= 4))
                L[1 - t]['assists'].append(len(e.get('assists', [])))
            else: S[t]['camp_deaths'] += 1
        elif k == 'lock_place': S[team[e['a']]]['locks'] += 1
        elif k == 'teleport_start': S[team[e['a']]]['crystals'] += 1
        elif k == 'ward': S[team[e['a']]]['wards'] += 1
        elif k == 'recall_end': S[team[e['a']]]['recalls'] += 1
        elif k == 'cast':
            t = team[e['a']]; S[t]['casts'] += 1
            if 'tgt' in e and e['tgt'] in team and team[e['tgt']] != t or any(team.get(x[0]) == 1 - t for x in e.get('dmg', [])): S[t]['casts_champ'] += 1
        elif k == 'attack':
            t = team[e['a']]
            if 'camp' in e: S[t]['att_camp'] += 1
            else: S[t]['att_champ'] += 1
        elif k == 'shop':
            for it, c in e.get('items', {}).items():
                if 'Lock' in it: S[team[e['a']]]['buy_lock'] += c
                if 'Crystal' in it or 'Teleport' in it: S[team[e['a']]]['buy_crystal'] += c
    # Opening pack: bodies of the clearer's team within 4 of it at each group clear before r200; Vesper's share of
    # the team's capture gold by r100; mates within 5 at r20 and r60 (alive, off spawn).
    for e in ev:
        if e['k'] == 'group_clear' and e['r'] < 200 and e.get('by') in team:
            t = team[e['by']]; i = min(max(e['r'] - 1, 0), n - 1); c = ch[e['by']]; p = (c['x'][i], c['y'][i])
            if None in p: continue
            L[t]['clear_bodies'].append(sum(1 for x in ch if x['team'] == t and x['alive'][i] and x['x'][i] is not None and cheb((x['x'][i], x['y'][i]), p) <= 4))
        if e['k'] == 'capture' and e['r'] <= 100:
            if e['shares'] and not sum(go for _, _, go in e['shares']): L[team[e['shares'][0][0]]]['gemcap'].append(1)
            for cid, gm, go in e['shares']:
                L[team[cid]]['g100'].append((typ[cid] == 'Vesper Vale', go))
    for t in (0, 1):
        S[t]['clear_bodies200'] = sum(L[t]['clear_bodies']) / len(L[t]['clear_bodies']) if L[t]['clear_bodies'] else None
        has_v = any(typ[x['id']] == 'Vesper Vale' for x in ch if x['team'] == t); tot = sum(g for _, g in L[t]['g100'])
        S[t]['vesper_gold100'] = (sum(g for v, g in L[t]['g100'] if v) / tot) if has_v and tot else None
        S[t]['gemcap100'] = len(L[t]['gemcap'])
        if has_v and n >= 100: S[t]['earned100_v'] = sum(x['earned'][99] for x in ch if x['team'] == t)
        for rr in (20, 60):
            i = min(rr - 1, n - 1); pos = [(x['x'][i], x['y'][i]) for x in ch if x['team'] == t and x['alive'][i] and x['x'][i] is not None and cheb((x['x'][i], x['y'][i]), spc[t]) > 3]
            S[t][f'coh_r{rr}'] = sum(sum(1 for q in pos if q is not p and cheb(p, q) <= 5) for p in pos) / len(pos) if pos else None
    for t in (0, 1):
        for rr in (100, 200, 300, 600):
            if n >= rr: S[t][f'earned{rr}'] = sum(x['earned'][rr - 1] for x in ch if x['team'] == t)
        coh, half, cnt = 0, 0, 0
        for i in range(29, min(n, 300), 5):
            pos = [(x['x'][i], x['y'][i]) for x in ch if x['team'] == t and x['alive'][i]]
            for p in pos:
                if cheb(p, spc[t]) <= 3: continue
                cnt += 1; coh += sum(1 for q in pos if q != p and cheb(p, q) <= 5)
                if cheb(p, spc[1 - t]) < cheb(p, spc[t]): half += 1
        S[t]['coh5'] = coh / cnt if cnt else 0; S[t]['enemy_half'] = half / cnt if cnt else 0
        pr = [x for x in ch if x['team'] == t and typ[x['id']] == 'Prism']
        S[t]['prism'] = len(pr); S[t]['prism_maxbag'] = max(pr[0]['gems']) if pr else 0
        S[t]['gems_final'] = R['gems'][t][-1]
        b = sorted(L[t]['bags'])
        S[t]['bag_med'] = b[len(b) // 2] if b else 0; S[t]['bag_mean'] = sum(b) / len(b) if b else 0
        S[t]['first_trib'] = L[t]['trib_r'][0] if L[t]['trib_r'] else n
        S[t]['conv'] = sum(L[t]['conv']) / len(L[t]['conv']) if L[t]['conv'] else None
        S[t]['assist'] = sum(L[t]['assists']) / len(L[t]['assists']) if L[t]['assists'] else None
    w = meta['result'].get('winner') if isinstance(meta.get('result'), dict) else None
    o = 1 - mite
    out = {'dir': d, 'rounds': n, 'mite_team': mite, 'mite_win': (w == mite) if w is not None else None,
           'mite_picks': meta['draft']['picks'][mite], 'our_picks': meta['draft']['picks'][o],
           'm': dict(S[mite]), 'o': dict(S[o]), **extra}
    return out

def main():
    mode = sys.argv[1]; ext = sys.argv[2]
    idx = json.load(open(ext + '/index.json'))['games']; jobs = []
    if mode == 'live':
        rows = json.load(open(sys.argv[3])); out = sys.argv[4]
        for g in idx:
            mid = os.path.basename(g['source'])[:-8]
            if mid not in rows: continue
            r = rows[mid]; mite = 1 if r['side'] == 'a' else 0
            jobs.append((ext, g['dir'], mite, {'map': r['map'].replace('_', '-'), 'side': r['side'], 'version': r['version'], 'match': mid, 'win_g': g['winner']}))
    else:
        out = sys.argv[3]
        for g in idx:
            base = os.path.basename(g['source'])[:-8]; num, rest = base.split('-', 1); mname, o = rest.rsplit('-', 1)
            side = 'a' if o == '12' else 'b'; mite = 1 if side == 'a' else 0
            jobs.append((ext, g['dir'], mite, {'map': mname.replace('_', '-'), 'side': side, 'src': g['source'], 'win_g': g['winner']}))
    with Pool(int(os.environ.get('OMP_NUM_THREADS', '8'))) as p: res = [x for x in p.map(game, jobs, chunksize=4) if x]
    for x in res:
        if x['mite_win'] is None: x['mite_win'] = x['win_g'] == x['mite_team']
    with open(out, 'w') as fh:
        for x in res: fh.write(json.dumps(x) + '\n')
    print(len(res), 'games ->', out)

if __name__ == '__main__': main()
