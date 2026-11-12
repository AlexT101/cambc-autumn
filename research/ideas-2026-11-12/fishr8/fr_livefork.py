"""forkcomp's livefork over our live games against Fish r8: the live arm (puppet) and a Fish body's continuation
(two noise members) from live positions.   py fr_livefork.py BODY OUT_DIR [--versions v117] [--forks 100,300,600]
Fidelity: our win rate from the fork against the body minus the live outcome (0 is perfect)."""
import sys, json, importlib.util
spec = importlib.util.spec_from_file_location('lf', '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/forkcomp/livefork_run.py')
lf = importlib.util.module_from_spec(spec); spec.loader.exec_module(lf)
body = sys.argv.pop(1)
lf.BODY = body if body.startswith('variants/') else f'variants/{body}'
orig = lf.lines
def lines(exp, versions, forks, limit):
    keep = set()
    for v in versions:
        for g in json.load(open(lf.ROOT / f'replays/{v}/manifest.json'))['games']:
            if g['opponent'] == 'Intercontinental Fish' and g.get('refset') == 'r8': keep.add(f"{g['group'][:8]}-{g['position']}")
    # livefork_run keeps Mite only: relabel our r8 Fish games so its filter passes them
    real = json.load; 
    def load(f, *a, **k):
        x = real(f, *a, **k)
        if isinstance(x, list) and x and isinstance(x[0], dict) and 'opponent' in x[0]:
            for g in x:
                if g['opponent'] == 'Intercontinental Fish' and g['key'] in keep: g['opponent'] = 'Mite'
        return x
    lf.json.load = load
    try: return orig(exp, versions, forks, limit)
    finally: lf.json.load = real
lf.lines = lines
if '--arms' not in sys.argv: sys.argv += ['--arms', 'puppet,body1,body2']
if '--versions' not in sys.argv: sys.argv += ['--versions', 'v117']
lf.main()
