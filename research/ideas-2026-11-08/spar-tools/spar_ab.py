"""Spar A/B: CAND and REF each against the spar panel (live Fish/Mite drafts on the 128 ladder maps, both sides),
paired by (member, map, side). Runs missing games with ab.py (fast runner), reuses finished runs (deterministic).
    py spar_ab.py CAND REF [--panel o29,j1,...,j12] [--name TAG]
CAND/REF are bot dirs under bots/ (own drafts: params::test_draft off). Panel member B is bots/variants/spar-B-{F,M}."""
import argparse, os, subprocess, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import local
R = local.R
PANEL = ['o29'] + [f'j{i}' for i in range(1, 13)]
LEGACY = {'o29': 'oc29'}  # spar-oc29-F is the unjittered body

def member_dir(b, o): return f'variants/spar-{LEGACY.get(b, b)}-{o}'

def run_name(cand, b, o):
    tag = os.path.basename(cand.rstrip('/')).removeprefix('oc-')
    for n in (f'spar-c{tag}-{b}{o}', f'spar-c{tag.removeprefix("base")}-{b}{o}'):
        if os.path.exists(f'{R}replays/ab/{n}/summary.json'): return n
    return f'spar-c{tag}-{b}{o}'

def ensure(cand, panel):
    env = dict(os.environ, CAMBC_BIN=f'{R}tools/fastengine/runner/fastrunner', FASTRUNNER_MODE='native')
    for b in panel:
        for o in 'FM':
            n = run_name(cand, b, o)
            if os.path.exists(f'{R}replays/ab/{n}/summary.json'): continue
            print('running', n, flush=True)
            subprocess.run([sys.executable, f'{R}tools/ab.py', cand, member_dir(b, o), '--no-test-draft', '--suites', 'ladder',
                            '--name', n, '--keep-replays', '0'], cwd=R, env=env, check=True, stdout=subprocess.DEVNULL)

def scores(cand, panel):
    return {(b, o, m, s): w for b in panel for o in 'FM' for (m, s), w in local.cells(run_name(cand, b, o)).items()}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cand'); ap.add_argument('ref')
    ap.add_argument('--panel', default=','.join(PANEL)); ap.add_argument('--no-run', action='store_true')
    a = ap.parse_args(); panel = a.panel.split(',')
    for bot in (a.cand, a.ref):
        if not a.no_run: ensure(bot, panel)
    x, y = scores(a.cand, panel), scores(a.ref, panel); ks = [k for k in x if k in y]
    d = np.array([x[k] - y[k] for k in ks]); se = d.std() / np.sqrt(len(d))
    # Members' games in one (map, side, F/M) cell are correlated (jitter re-draws ~18% of them): cluster by cell for
    # the fixed ladder pool, by map for unseen maps.
    def clustered(key):
        g = {}
        for k, v in zip(ks, d): g.setdefault(key(k), []).append(v)
        mm = np.array([np.mean(v) for v in g.values()]); return mm.std() / np.sqrt(len(mm))
    sec, sem = clustered(lambda k: (k[1], k[2], k[3])), clustered(lambda k: k[2])
    print(f'{a.cand} vs {a.ref} on spar panel ({len(panel)} bodies x F/M, {len(ks)} paired games): '
          f'CAND {100*np.mean([x[k] for k in ks]):.1f}% REF {100*np.mean([y[k] for k in ks]):.1f}%  '
          f'delta {100*d.mean():+.2f} pts (95% CI ±{196*sec:.2f} by cell; ±{196*sem:.2f} by map), flips +{(d>0).sum()} -{(d<0).sum()}')

if __name__ == '__main__':
    main()
