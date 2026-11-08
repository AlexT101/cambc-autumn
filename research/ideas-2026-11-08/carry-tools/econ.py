"""Per-type economy: live Fish/Mite team vs spar body (same picks/map/side vs same ocean v89), by round window."""
import json, gzip, os, sys, collections, numpy as np, pickle
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools')
import live, local
H = os.path.expanduser('~/tmp-offload/')
def load(ana, full=True):
    idx = json.load(open(ana + '/index.json'))['games']; out = {}
    for g in idx:
        if not g.get('ok', True): continue
        for s in [g['source']] + [x['source'] for x in g.get('sources', [])]: out[(os.path.basename(os.path.dirname(s)) + '/' if full else '') + os.path.basename(s).split('.')[0]] = g['dir']
    return out
RW = int(os.environ.get('RW', 200))
def feats(d, team):
    meta = json.load(open(d + '/meta.json'))
    ch = {c['id']: c for c in meta['champions']}
    name = {i: c['name'] for i, c in ch.items()}
    f = collections.defaultdict(float)
    mine = [i for i, c in ch.items() if c['team'] == team]
    for l in gzip.open(d + '/events.jsonl.gz'):
        e = json.loads(l)
        if e['r'] > RW: break
        k = e['k']
        if k == 'capture' and e['team'] == team:
            sh = e['shares']; n = len(sh)
            tg = sum(s[2] for s in sh); tm = sum(s[1] for s in sh)
            f['caps'] += 1; f['cap_gold'] += tg; f['cap_gems'] += tm
            f[f'caps_n{min(n,3)}'] += 1
            for cid, gm, gd in sh:
                nm = name[cid]; f['capgold_' + nm] += gd; f['capgems_' + nm] += gm; f['capcnt_' + nm] += 1
                if n == 1: f['solo_' + nm] += 1
        elif k == 'death':
            v = e['v']; by = e.get('by')
            if by is not None and by in ch and ch[by]['team'] == team and 'gold' in e:
                f['killgold_' + name[by]] += e['gold']; f['kills'] += 1
            if ch[v]['team'] == team and 'linked' not in e: f['deaths'] += 1; f['death_' + name[v]] += 1
        elif k == 'attack' and e['a'] in mine:
            nm = name[e['a']]
            if 'camp' in e: f['campatk_' + nm] += 1; f['campatk'] += 1
            elif 'tgt' in e: f['champatk_' + nm] += 1; f['champatk'] += 1
        elif k == 'cast' and e['a'] in mine:
            nm = name[e['a']]
            if 'dmg' in e: f['champcast_' + nm] += 1
            if 'cdmg' in e: f['campcast_' + nm] += 1
    R = json.load(gzip.open(d + '/rounds.json.gz')); rr = np.array(R['round'])
    i = min(np.searchsorted(rr, RW), len(rr) - 1)
    for c in R['champions']:
        if c['team'] != team: continue
        nm = name[c['id']]; f['earned_' + nm] += c['earned'][i]; f['earned'] += c['earned'][i]
        f['alive_' + nm] += np.mean(c['alive'][:i+1])
    f['win'] = float(meta['result']['winner'] == team)
    return f
if __name__ == '__main__':
    BODY = sys.argv[1] if len(sys.argv) > 1 else 'o29'; ANA = sys.argv[2] if len(sys.argv) > 2 else 'spar/ana'
    L = load(H + 'bigl/ana', False); S = load(H + ANA)
    games = json.load(open(H + 'bigl/games.json'))
    liveg = {}
    for mid, g in games.items():
        if g['version'] != 89 or mid not in L: continue
        liveg[(g['map'].replace('_', '-'), g['side'], live.OPP[g['opp_name']])] = (L[mid], g)
    rows = []
    for o in 'FM':
        for mp, side, m in local.matches(f'spar-c27-{BODY}{o}'):
            k = os.path.basename(os.path.dirname(m['replay'])) + '/' + os.path.basename(m['replay']).split('.')[0]
            if k not in S or (mp, side, o) not in liveg: continue
            ot = 1 if side == 'a' else 0
            ld, g = liveg[(mp, side, o)]
            rows.append(dict(map=mp, side=side, opp=o, picks=tuple(g['opp_picks']), live_opp=feats(H + 'bigl/ana/' + ld, ot), spar_opp=feats(H + ANA + '/' + S[k], ot),
                             live_us=feats(H + 'bigl/ana/' + ld, 1 - ot), spar_us=feats(H + ANA + '/' + S[k], 1 - ot)))
    pickle.dump(rows, open(H + f'carry/econ-{BODY}-r{RW}.pkl', 'wb'))
    print(len(rows))
