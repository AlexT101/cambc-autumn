"""Per capture: capturer type, group value, who damaged the group's camps in its clear (since its last respawn)."""
import json, gzip, os, sys, collections, numpy as np, pickle
sys.path.insert(0, os.path.expanduser('~/tmp-offload/carry'))
from econ import load, H
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools'); import live, local
def caps(d, team):
    meta = json.load(open(d + '/meta.json')); ch = {c['id']: c for c in meta['champions']}; name = {i: c['name'] for i, c in ch.items()}
    ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz')]
    c2g = {}
    for e in ev:
        if 'camp' in e and 'g' in e: c2g[e['camp']] = e['g']
    dmg = collections.defaultdict(lambda: collections.defaultdict(float))  # g -> champ -> dmg
    first = {}; out = []
    for e in ev:
        k = e['k']
        if k == 'group_respawn': dmg.pop(e['g'], None); first.pop(e['g'], None)
        cd = e.get('cdmg')
        if cd and 'a' in e:
            for camp, x in cd:
                g = c2g.get(camp)
                if g is None: continue
                dmg[g][e['a']] += x; first.setdefault(g, e['r'])
        if k == 'capture':
            g = e['g']; D = dmg.get(g, {}); tot = sum(D.values())
            ours = sum(v for a, v in D.items() if ch[a]['team'] == e['team'])
            sh = e['shares']
            rec = dict(r=e['r'], team=e['team'], gold=sum(s[2] for s in sh), gems=sum(s[1] for s in sh), n=len(sh),
                       holders=[name[s[0]] for s in sh], tot=tot, ours=ours, start=first.get(g, e['r']),
                       dealers={name[a]: v for a, v in D.items() if ch[a]['team'] == e['team']})
            if e['team'] == team: out.append(rec)
            dmg.pop(g, None); first.pop(g, None)
    return out
if __name__ == '__main__':
    BODY = sys.argv[1] if len(sys.argv) > 1 else 'o29'; ANA = sys.argv[2] if len(sys.argv) > 2 else 'spar/ana'
    L = load(H + 'bigl/ana', False); S = load(H + ANA)
    games = json.load(open(H + 'bigl/games.json')); liveg = {}
    for mid, g in games.items():
        if g['version'] != 89 or mid not in L: continue
        liveg[(g['map'].replace('_', '-'), g['side'], live.OPP[g['opp_name']])] = (L[mid], g)
    rows = []
    for o in 'FM':
        for mp, side, m in local.matches(f'spar-c27-{BODY}{o}'):
            k = os.path.basename(os.path.dirname(m['replay'])) + '/' + os.path.basename(m['replay']).split('.')[0]
            if k not in S or (mp, side, o) not in liveg: continue
            ot = 1 if side == 'a' else 0; ld, g = liveg[(mp, side, o)]
            rows.append(dict(map=mp, side=side, opp=o, picks=tuple(g['opp_picks']), live=caps(H + 'bigl/ana/' + ld, ot), spar=caps(H + ANA + '/' + S[k], ot),
                             live_us=caps(H + 'bigl/ana/' + ld, 1 - ot)))
    pickle.dump(rows, open(H + f'carry/caps-{BODY}.pkl', 'wb')); print(len(rows))
