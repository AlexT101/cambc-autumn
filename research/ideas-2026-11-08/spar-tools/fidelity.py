"""Behaviour fidelity: the live opponent (v89 games, decoded in ~/tmp-offload/bigl/ana) against the spar body in the
same (map, side, draft) locally (decoded in ~/tmp-offload/spar/ana): per opponent champion type and per team."""
import json, gzip, os, sys, collections, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); import live, local
H = os.path.expanduser('~/tmp-offload/')
def load(ana):
    idx = json.load(open(ana + '/index.json'))['games']; out = {}
    for g in idx:
        if not g.get('ok', True): continue
        for s in [g['source']] + [x['source'] for x in g.get('sources', [])]: out[os.path.basename(s).split('.')[0]] = g['dir']
    return out
def feats(d, opp_team):
    meta = json.load(open(d + '/meta.json')); R = json.load(gzip.open(d + '/rounds.json.gz')); rr = np.array(R['round'])
    f = {'win': float(meta['result']['winner'] == opp_team), 'rounds': meta['result']['rounds']}
    for t, side in ((opp_team, 'opp'), (1 - opp_team, 'us')):
        ch = [c for c in meta['champions'] if c['team'] == t]
        f[side + '_gold'] = sum(c['stats']['earnedGold'] for c in ch)
        f[side + '_gems_coll'] = sum(c['stats']['collectedGems'] for c in ch)
        f[side + '_kills'] = sum(c['stats']['kills'] for c in ch)
        f[side + '_dmg_champ'] = sum(c['stats']['championDamageDone'] for c in ch)
        f[side + '_dmg_mon'] = sum(c['stats']['monsterDamageDone'] for c in ch)
        rc = [c for c in R['champions'] if c['team'] == t]
        for r in (200, 400, 600):
            i = min(np.searchsorted(rr, r), len(rr) - 1)
            f[f'{side}_earned{r}'] = sum(c['earned'][i] for c in rc); f[f'{side}_trib{r}'] = R['gems'][t][i]
        if side == 'opp':
            for c in ch: f['type_gold_' + c['name']] = c['stats']['earnedGold']; f['type_gems_' + c['name']] = c['stats']['collectedGems']; f['type_deaths_' + c['name']] = c['stats']['deaths']
    return f
BODY = sys.argv[1] if len(sys.argv) > 1 else 'o29'; ANA = sys.argv[2] if len(sys.argv) > 2 else 'spar/ana'
L = load(H + 'bigl/ana'); S = load(H + ANA)
games = json.load(open(H + 'bigl/games.json'))
liveg = {}
for mid, g in games.items():
    if g['version'] != 89 or mid not in L: continue
    liveg[(g['map'].replace('_', '-'), g['side'], live.OPP[g['opp_name']])] = L[mid]
rows = []
for o in ('FM' if __name__ == '__main__' else ''):
    for mp, side, m in local.matches(f'spar-c27-{BODY}{o}'):
        k = os.path.basename(m['replay']).split('.')[0]
        if k not in S or (mp, side, o) not in liveg: continue
        opp_team = 1 if side == 'a' else 0
        a = feats(H + 'bigl/ana/' + liveg[(mp, side, o)], opp_team); b = feats(H + ANA + '/' + S[k], opp_team)
        rows.append((mp, side, o, a, b))
if __name__ == '__main__':
    print(len(rows), 'matched games')
    keys = sorted(set(k for r in rows for k in r[3]) & set(k for r in rows for k in r[4]))
    print(f'{"feature":28s} {"live opp":>10s} {"spar opp":>10s} {"n":>4s}  (live us / local us where team-level)')
    for k in keys:
        a = [r[3][k] for r in rows if k in r[3] and k in r[4]]; b = [r[4][k] for r in rows if k in r[3] and k in r[4]]
        if len(a) < 20: continue
        print(f'{k:28s} {np.mean(a):10.1f} {np.mean(b):10.1f} {len(a):4d}')
    import pickle; pickle.dump(rows, open(H + f'spar/fidelity-{BODY}.pkl', 'wb'))
