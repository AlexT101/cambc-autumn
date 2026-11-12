"""Live r7 positions (v116 games against Mite, forkcomp's livefork): from each fork, our side swapped for BASE or CAND
against the mf-c2 body (noise members 1-2), both cold-started.
    py fork_arms.py OUT_DIR BASE CAND [--forks 100,300,600]"""
import sys, importlib.util
spec = importlib.util.spec_from_file_location('lf', '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/forkcomp/livefork_run.py')
lf = importlib.util.module_from_spec(spec); spec.loader.exec_module(lf)
out, base, cand = sys.argv[1], sys.argv[2], sys.argv[3]
lf.BODY = 'variants/mf-c2'
lines = lf.lines
def mine(exp, versions, forks, limit):
    gl = lines('live', versions, forks, limit)
    for g in gl:
        ours = g['ours']; opp = 1 - ours
        g['arms'] = [{'label': f'{lab}+body{k}', f't{ours}': {'bot': bot}, f't{opp}': lf.body(k)}
                     for k in (1, 2) for lab, bot in (('base', base), ('cand', cand))]
    return gl
lf.lines = mine
sys.argv = [sys.argv[0], out, '--versions', 'v116'] + sys.argv[4:]
lf.main()
