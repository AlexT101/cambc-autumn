"""Deaths in local ab runs decoded by extract.mjs: python3 profstats.py EXT [EXT...]
Our side: replay name ...-12 = team A, ...-21 = team B. The pair's body hit = its death event without 'linked'."""
import gzip, json, os, sys, collections

def stats(ext):
    idx = json.load(open(ext + '/index.json'))['games']
    S = collections.Counter(); games = 0; cig = 0; wins = 0
    for g in idx:
        base = os.path.basename(g['source'])
        us = 0 if base.endswith('-12.repl26a') else 1
        d = ext + '/' + g['dir']
        if not os.path.exists(d + '/meta.json'): continue
        m = json.load(open(d + '/meta.json'))
        games += 1; wins += g.get('winner') == us
        ch = {c['id']: c for c in m['champions']}
        ours = {c['name']: c['id'] for c in m['champions'] if c['team'] == us}
        ci = 'Cassi' in ours; cig += ci
        for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
            e = json.loads(l)
            if e['k'] != 'death' or ch[e['v']]['team'] != us or 'linked' in e: continue
            killer = ch[e['by']]['name'] if e.get('by') in ch else 'camp'
            late = e['r'] >= 300
            S['deaths'] += 1
            S['deaths_vesper'] += killer == 'Vesper Vale'
            v = ch[e['v']]['name']
            if v in ('Cassi', 'Issac'):
                S[f'pair_{v}'] += 1
                S[f'pair_{v}_vesper'] += killer == 'Vesper Vale'
                S[f'pair_{v}_vesper_late'] += killer == 'Vesper Vale' and late
            if v == 'Prism': S['prism'] += 1; S['prism_vesper'] += killer == 'Vesper Vale'
    return games, wins, cig, S

for ext in sys.argv[1:]:
    games, wins, cig, S = stats(ext)
    print(f'{os.path.basename(ext)}: games {games}, win {wins/max(games,1)*100:.1f}%, C&I games {cig}; deaths/game {S["deaths"]/games:.2f} (to Vesper {S["deaths_vesper"]/games:.2f})')
    if cig:
        print('  per C&I game: ' + ', '.join(f'{k} {S[k]/cig:.3f}' for k in ('pair_Cassi', 'pair_Cassi_vesper', 'pair_Cassi_vesper_late', 'pair_Issac', 'pair_Issac_vesper', 'pair_Issac_vesper_late')))
    print(f'  prism deaths/game {S["prism"]/games:.3f} (to Vesper {S["prism_vesper"]/games:.3f})')
