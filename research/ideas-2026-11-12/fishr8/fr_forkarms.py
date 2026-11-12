"""Live Fish r8 positions (v117/v118 games, forkcomp's livefork): from each fork, our side swapped for BASE or CAND
against a Fish r8 body (noise members 1-2), both cold-started.
    py fr_forkarms.py OUT_DIR BASE CAND [--body fr8-g25] [--members 1,2] [--versions v117,v118] [--forks 300,450,600]
Read with fr_forkread.py OUT_DIR."""
import sys, json, importlib.util
spec = importlib.util.spec_from_file_location('lf', '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/forkcomp/livefork_run.py')
lf = importlib.util.module_from_spec(spec); spec.loader.exec_module(lf)
out, base, cand = sys.argv[1:4]; rest = sys.argv[4:]
bd = 'fr8-g25'
if '--body' in rest: i = rest.index('--body'); bd = rest[i + 1]; del rest[i:i + 2]
lf.BODY = f'variants/{bd}'
members = (1, 2)
if '--members' in rest: i = rest.index('--members'); members = tuple(int(x) for x in rest[i + 1].split(',')); del rest[i:i + 2]
orig = lf.lines
def mine(exp, versions, forks, limit):
    keep = set()
    for v in versions:
        for g in json.load(open(lf.ROOT / f'replays/{v}/manifest.json'))['games']:
            if g['opponent'] == 'Intercontinental Fish' and g.get('refset') == 'r8': keep.add(f"{g['group'][:8]}-{g['position']}")
    real = json.load
    def load(f, *a, **k):  # livefork_run keeps Mite games only: relabel the r8 Fish ones
        x = real(f, *a, **k)
        if isinstance(x, list) and x and isinstance(x[0], dict) and 'opponent' in x[0]:
            for g in x:
                if g['opponent'] == 'Intercontinental Fish' and g['key'] in keep: g['opponent'] = 'Mite'
        return x
    lf.json.load = load
    try: gl = orig('live', versions, forks, limit)
    finally: lf.json.load = real
    for g in gl:
        ours = g['ours']; opp = 1 - ours
        g['arms'] = [{'label': f'{lab}+body{k}', f't{ours}': {'bot': bot}, f't{opp}': lf.body(k)}
                     for k in members for lab, bot in (('base', base), ('cand', cand))]
    return gl
lf.lines = mine
if '--versions' not in rest: rest += ['--versions', 'v117,v118']
if '--forks' not in rest: rest += ['--forks', '300,450,600']
sys.argv = [sys.argv[0], out] + rest
lf.main()
