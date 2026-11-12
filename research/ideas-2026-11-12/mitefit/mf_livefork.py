"""forkcomp's livefork_run.py with another Mite body: the live arm (puppet) and the body's continuation (two noise
members) from live positions.   py mf_livefork.py BODY OUT_DIR [--versions v116] [--forks 100,300,600]
The body's fidelity: our win rate from the fork against the body, minus the live outcome (0 is perfect)."""
import sys, importlib.util
spec = importlib.util.spec_from_file_location('lf', '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/forkcomp/livefork_run.py')
lf = importlib.util.module_from_spec(spec); spec.loader.exec_module(lf)
body = sys.argv.pop(1)
lf.BODY = body if body.startswith('variants/') else f'variants/{body}'
if '--arms' not in sys.argv: sys.argv += ['--arms', 'puppet,body1,body2']
if '--versions' not in sys.argv: sys.argv += ['--versions', 'v116']
lf.main()
