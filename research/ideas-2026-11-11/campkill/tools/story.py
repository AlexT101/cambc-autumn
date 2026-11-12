"""One game's non-prompt clears of ours with the killer's turns around them.
usage: story.py EXTDIR GAME_INDEX|worst [--kinds gemcl] [--n 6]"""
import sys, json, gzip, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0]); import ck
ext, which = sys.argv[1], sys.argv[2]
kinds = sys.argv[sys.argv.index('--kinds') + 1].split(',') if '--kinds' in sys.argv else None
nshow = int(sys.argv[sys.argv.index('--n') + 1]) if '--n' in sys.argv else 6
idx = json.load(open(ext + '/index.json'))['games']
if which == 'worst':
    best = None
    for i, g in enumerate(idx):
        xs, _ = ck.game(ext, g, ck.side_of(g['source'], None), 8, None)
        n = sum(x['by'] == 'us' and x['cls'] != 'prompt' and (not kinds or x['kind'] in kinds) for x in xs)
        if best is None or n > best[0]: best = (n, i)
    which = best[1]
g = idx[int(which)]; us = ck.side_of(g['source'], None)
d = ext + '/' + g['dir']; meta = json.load(open(d + '/meta.json'))
name = {c['id']: c['name'][:5] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
R = json.load(gzip.open(d + '/rounds.json.gz')); ch = {c['id']: c for c in R['champions']}
print(g['source'], 'us', us, {k: v for k, v in name.items() if team[k] == us})
xs, _ = ck.game(ext, g, us, 8, None)
bad = [x for x in xs if x['by'] == 'us' and x['cls'] != 'prompt' and (not kinds or x['kind'] in kinds)]
for x in bad[:nshow]:
    clr = next(e for e in ev if e['k'] == 'group_clear' and e['g'] == x['g'] and e['r'] == x['clear'])
    k = clr['by']
    print(f"--- g{x['g']} {x['kind']} cleared r{x['clear']} by {name[k]}({k}) -> {x['cls']} gap {x['gap']} paid {x['paid']}")
    for r in range(x['clear'] - 3, x['clear'] + 12):
        i = r - 1
        if i >= len(R['round']): break
        acts = [(e['k'][:4], e.get('camp'), e.get('ab', '')[:3]) for e in ev if e['r'] == r and e.get('a') == k and e['k'] in ('attack', 'cast', 'move', 'capture_hold')]
        caps = [(e['k'][:7], e['g']) for e in ev if e['r'] == r and e['k'] in ('capture', 'group_clear', 'capture_hold') and e.get('team', us) == us]
        print(f"  r{r} {name[k]} ({ch[k]['x'][i]},{ch[k]['y'][i]}) {acts} {caps}")
