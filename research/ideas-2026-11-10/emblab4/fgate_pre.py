"""Play fgate's runs of one bot ahead of a gate (its blocks' games against the Fish and Mite bodies), so that
fgate.py finds them finished: the reference's half of every block does not depend on the candidate.

    py fgate_pre.py variants/ocean-b0eeff1 --blocks 1-40 [--jobs 8] [--fish-body Flp4] [--mite-body Mt3qro]
"""
import argparse, os, sys, time
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'ideas-2026-11-09', 'freshgate-tools')
sys.path.insert(0, T)
ap = argparse.ArgumentParser(); ap.add_argument('bot'); ap.add_argument('--blocks', default='1-40'); ap.add_argument('--jobs', type=int, default=8)
ap.add_argument('--fish-body', default='Flp4'); ap.add_argument('--mite-body', default='Mt3qro')
a = ap.parse_args()
sys.argv = sys.argv[:1]
import fgate  # noqa: E402
fgate.BODY['F'], fgate.BODY['M'] = a.fish_body, a.mite_body
lo, hi = map(int, a.blocks.split('-'))
run = fgate.Runner(a.jobs)
todo = [(k, o, s, suite, games) for k in range(lo, hi + 1) for o in 'FM' for s, suite, games in fgate.suites(k)]
built = set()
while todo:
    left = []
    for k, o, s, suite, games in todo:
        if k not in built and len(run.procs) < run.jobs:
            fgate.build_version(k); built.add(k)
        if k not in built or not run.want(a.bot, k, o, s, suite, games):
            left.append((k, o, s, suite, games))
    if len(left) < len(todo):
        print(f'{time.strftime("%H:%M:%S")} {len(left)} runs left', flush=True)
    todo = left
    time.sleep(10)
while run.procs:
    run.poll(); time.sleep(5)
print('done')
