"""One-off overfit check on more_maps/autogen/* (user, 2026-11-09: diverse, not the ladder distribution; informative only).
    py autogen.py run [--seeds 3] [--jobs 8]      play every bot below against the pick-model bodies on each folder
    py autogen.py read CAND REF                   paired per folder: CAND's mean minus REF's per map, 95% CI over maps"""
import sys, os, json, math, subprocess, time, numpy as np
T = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, T)
import fgate  # noqa: E402
from fgate import R, local, CAMBC, LOGS, ENG  # noqa: E402
A = f'{R}more_maps/autogen'; FOLDERS = ['bc26', 'cambc1', 'fcode', 'vae']
BOTS = ['oc-base23', 'oc32s-bsk', 'oc32s-spy2', 'oc32-cg-fs-nh', 'oc-base25', 'oc-base31']
def rn(bot, k, o, f): return f'fga{ENG}-{bot.removeprefix("oc-")}-dvn{k}{o}-{f}'
def nmaps(f): return len([x for x in os.listdir(f'{A}/{f}') if x.endswith('.map26a')])
def main():
    if sys.argv[1] == 'run':
        seeds = int(sys.argv[sys.argv.index('--seeds') + 1]) if '--seeds' in sys.argv else 3
        jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 8
        run = fgate.Runner(jobs)
        todo = [(b, k, o, f) for k in range(1, seeds + 1) for f in FOLDERS for b in BOTS for o in 'FM']
        for k in range(1, seeds + 1): fgate.build_seed(k)
        while True:
            left = [t for t in todo if not fgate.done(rn(*t), 2 * nmaps(t[3]))]
            if not left: break
            for b, k, o, f in left:
                n = rn(b, k, o, f)
                if n not in run.procs and len(run.procs) < jobs:
                    run.procs[n] = (subprocess.Popen([sys.executable, f'{R}tools/ab.py', f'variants/{b}', fgate.mdir(k, o), '--no-test-draft',
                                                      '--suites', f'{A}/{f}', '--name', n, '--keep-replays', '1'], cwd=R, env=run.env,
                                                     stdout=open(f'{LOGS}/{n}.log', 'w'), stderr=subprocess.STDOUT), f'{fgate.LOCKS}/{n}')
                    open(f'{fgate.LOCKS}/{n}', 'w').close()
            time.sleep(30); run.poll()
            if all(rn(*t) in run.procs or fgate.done(rn(*t), 2 * nmaps(t[3])) for t in left) and not run.procs: break
        print('done')
    else:
        cand, ref = sys.argv[2], sys.argv[3]
        for f in FOLDERS:
            diff = {}
            for k in range(1, 100):
                if not os.path.exists(f'{R}replays/ab/{rn(cand, k, "F", f)}/summary.json'): break
                for o in 'FM':
                    x, y = local.cells(rn(cand, k, o, f)), local.cells(rn(ref, k, o, f))
                    for c in x.keys() & y.keys(): diff.setdefault(c[0], []).append(x[c] - y[c])
            u = np.array([np.mean(v) for v in diff.values()])
            if len(u) > 1: print(f'{f:7s} {cand} vs {ref}: {100 * u.mean():+.2f} pts ±{196 * u.std() / math.sqrt(len(u)):.2f} over {len(u)} maps')
if __name__ == '__main__':
    main()
