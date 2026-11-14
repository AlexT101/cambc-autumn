"""Diverse-panel gate (diverse-panel.md): CAND and REF each against panel members on the 128 ladder maps, both sides,
own drafts; members play Fish's / Mite's live picks there (spar-<body>-{F,M}). Units are per map: 0.5 + CAND's mean
minus REF's over every member and side, so members that repeat each other's games can't inflate the test. Members
are added in order until ab.py's SPRT on those units decides or the panel runs out.
    py dpanel_ab.py CAND REF [--panel dvn1,dvn2,...] [--sprt 0.50,0.5025] [--alpha 0.05] [--no-run]
CAND/REF are bot dirs under bots/ with params::test_draft off. Runs are named spar-c<tag>-<body><F|M> and reused."""
import argparse, os, subprocess, sys, collections, numpy as np
T = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(T, '..', 'spar-tools')); sys.path.insert(0, os.path.join(T, '..', '..', '..', '..', 'tools'))
import local, spar_ab, ab  # noqa: E402
R = local.R
# Noise members (dvp-nK: oc-base25 knobs redrawn every 100 rounds, seeded per game) then the tunings and styles.
PANEL = [f"dvn{i}" for i in range(1, 33)] + ['dvoc6', 'dvanti6', 'dvagg', 'dvpas', 'dvgreed']

def ensure(bot, b):
    env = dict(os.environ, CAMBC_BIN=f'{R}tools/fastengine/runner/fastrunner', FASTRUNNER_MODE='native')
    for o in 'FM':
        n = spar_ab.run_name(bot, b, o)
        if os.path.exists(f'{R}replays/ab/{n}/summary.json'): continue
        print('running', n, flush=True)
        subprocess.run([sys.executable, f'{R}tools/ab.py', bot, spar_ab.member_dir(b, o), '--no-test-draft', '--suites',
                        'ladder', '--name', n, '--keep-replays', '1'], cwd=R, env=env, check=True, stdout=subprocess.DEVNULL)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cand'); ap.add_argument('ref')
    ap.add_argument('--panel', default=','.join(PANEL)); ap.add_argument('--sprt', default='0.50,0.5025')
    ap.add_argument('--alpha', type=float, default=0.05); ap.add_argument('--no-run', action='store_true')
    a = ap.parse_args(); p0, p1 = map(float, a.sprt.split(',')); lo, hi = ab.sprt_bounds(a.alpha, a.alpha)
    diff = collections.defaultdict(list); outcome = None
    for i, b in enumerate(a.panel.split(','), 1):
        if not a.no_run:
            ensure(a.cand, b); ensure(a.ref, b)
        for o in 'FM':
            nx, ny = spar_ab.run_name(a.cand, b, o), spar_ab.run_name(a.ref, b, o)
            if not all(os.path.exists(f'{R}replays/ab/{n}/summary.json') for n in (nx, ny)): continue
            x, y = local.cells(nx), local.cells(ny)
            for c in x.keys() & y.keys(): diff[c[0]].append(x[c] - y[c])
        if not diff: continue
        units = [0.5 + np.mean(v) for v in diff.values()]; llr = ab.llr(units, p0, p1)
        d = np.array(units) - 0.5; games = sum(len(v) for v in diff.values())
        print(f'{i:2d} members ({b}): {100*d.mean():+.2f} pts ±{196*d.std()/np.sqrt(len(d)):.2f} (by map) over '
              f'{games} paired games, LLR {llr:+.2f} [{lo:.2f}, {hi:.2f}]', flush=True)
        if llr >= hi or llr <= lo:
            outcome = 'H1' if llr >= hi else 'H0'; break
    print(f'{a.cand} vs {a.ref}: {outcome or "undecided"} at {a.sprt} alpha {a.alpha}')

if __name__ == '__main__':
    main()
