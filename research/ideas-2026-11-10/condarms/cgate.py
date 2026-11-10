"""The fresh-map gate for a per-opponent arm (fgate.py's runs and rules), read on the half the arm acts in.

    py cgate.py CAND REF --on F|M [--first-block 38] [--max-blocks 80] [--jobs 8] [--no-run]

- Same opponents, bodies (Flp4 / Mt3q), runs and SPRTs as fgate, but:
  - the fresh maps are a second 1,024-map ladder-v2 pool no gate had played (seeds 1510001-1510004, slices g0-g7
    in ~/tmp-offload/condarms/fresh/pool), so an arm picked on fgate's Fish / Mite split is read on new maps;
  - noise blocks start at --first-block (fgate's --seed only shuffles units: it never changes the games);
  - the SPRTs and the stop read the --on half's fresh units: the arm acts only there. The other half's fresh units
    are reported, and should read level (only the classifier's fuel and its misreads differ there).
- Stops at the low SPRT's H0 (REJECT) or H1 (above 50% on its half), the high SPRT's H1 (ACCEPT at the 50.5% bar),
  or --max-blocks.
"""
import argparse, json, math, os, random, sys, time, numpy as np
T = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(T, '..', '..', 'ideas-2026-11-09', 'freshgate-tools'))
import fgate  # noqa: E402
from fgate import ab, local, build_version  # noqa: E402
POOL = [os.path.expanduser(f'~/tmp-offload/condarms/fresh/pool/g{j}') for j in range(8)]
OUT = os.path.expanduser('~/tmp-offload/condarms/gate-logs')
for line in open(os.path.expanduser('~/tmp-offload/condarms/fresh/feat-g.jsonl')):
    x = json.loads(line); fgate.FT[x['name'].replace('_', '-')] = x['f']
fgate.BODY['F'], fgate.BODY['M'] = 'Flp4', 'Mt3q'  # fgate's defaults from 2026-11-10 ~01:00
FIRST = 38
def slice_of(k): return (k - FIRST) % len(POOL)
def suites(k): return [('L', 'ladder', 2 * 128), (f'g{slice_of(k)}', POOL[slice_of(k)], 2 * len(os.listdir(POOL[slice_of(k)])))]
fgate.slice_of, fgate.suites = slice_of, suites  # block_units and the runner read these

def main():
    global FIRST
    ap = argparse.ArgumentParser(); ap.add_argument('cand'); ap.add_argument('ref')
    ap.add_argument('--on', required=True, choices=['F', 'M', 'all'])
    ap.add_argument('--first-block', type=int, default=38); ap.add_argument('--max-blocks', type=int, default=80)
    ap.add_argument('--sprt', default='0.505,0.5075'); ap.add_argument('--low', default='0.4975,0.50')
    ap.add_argument('--jobs', type=int, default=8); ap.add_argument('--ahead', type=int, default=2)
    ap.add_argument('--no-run', action='store_true')
    a = ap.parse_args(); FIRST = a.first_block
    p0, p1 = map(float, a.sprt.split(',')); q0, q1 = map(float, a.low.split(','))
    lo, hi = math.log(0.05 / 0.95), math.log(0.95 / 0.05)
    run = fgate.Runner(a.jobs); U = {'L': {}, 'fresh': {}}; outcome = None
    last = FIRST + a.max_blocks - 1; k = FIRST
    est = fgate.est
    while k <= last:
        if not a.no_run:
            for j in range(k, min(k + a.ahead, last) + 1):
                build_version(j)
                for o in 'FM':
                    for s, suite, games in suites(j):
                        for bot in (a.ref, a.cand): run.want(bot, j, o, s, suite, games)
        if not all(fgate.done(fgate.rname(bot, k, o, s), g) for o in 'FM' for s, _, g in suites(k) for bot in (a.cand, a.ref)):
            if a.no_run: break
            time.sleep(20); continue
        for key, g in fgate.block_units(a.cand, a.ref, k, random.Random(k)).items():
            for gg, u in g.items(): U[key].setdefault(gg, []).extend(u)
        sc = U['fresh'][a.on]; hl, ll = ab.llr(sc, p0, p1), ab.llr(sc, q0, q1)
        d = np.array(sc) - 0.5; se = d.std() / math.sqrt(len(d))
        rd = lambda u: f'{100 * (np.mean(u) - 0.5):+.2f}' if u else 'n/a'
        print(f'block {k:3d} (fresh g{slice_of(k)}): {a.on} fresh {len(sc)} units {100*d.mean():+.2f} ±{196*se:.2f} '
              f'LLR high {hl:+.2f} low {ll:+.2f} [{lo:.2f} | {hi:.2f}] | fresh all {rd(U["fresh"]["all"])} F {rd(U["fresh"]["F"])} '
              f'M {rd(U["fresh"]["M"])} | ladder all {rd(U["L"]["all"])} F {rd(U["L"]["F"])} M {rd(U["L"]["M"])}', flush=True)
        if ll <= lo: outcome = 'REJECT (low H0)'; break
        if hl >= hi: outcome = 'ACCEPT (high H1)'; break
        if ll >= hi: outcome = 'above 50% on its half (low H1)'; break
        k += 1
    while run.procs: run.poll(); time.sleep(5)
    if outcome is None: outcome = 'undecided at max blocks' if k > last else 'undecided'
    res = {'cand': a.cand, 'ref': a.ref, 'on': a.on, 'outcome': outcome, 'first_block': FIRST, 'last_block': min(k, last),
           'bodies': f'{fgate.BODY["F"]}/{fgate.BODY["M"]}', 'pool': 'condarms g0-g7 (1510001-1510004)',
           'fresh_on': est(U['fresh'].get(a.on, [])), 'fresh_all': est(U['fresh'].get('all', [])),
           'fresh_fish': est(U['fresh'].get('F', [])), 'fresh_mite': est(U['fresh'].get('M', [])),
           'fresh_one_site': est(U['fresh'].get('one', [])), 'fresh_multi_site': est(U['fresh'].get('multi', [])),
           'ladder': est(U['L'].get('all', [])), 'ladder_fish': est(U['L'].get('F', [])), 'ladder_mite': est(U['L'].get('M', [])),
           'on_units': len(U['fresh'].get(a.on, [])),
           'llr_high': round(ab.llr(U['fresh'][a.on], p0, p1), 3) if U['fresh'].get(a.on) else None,
           'llr_low': round(ab.llr(U['fresh'][a.on], q0, q1), 3) if U['fresh'].get(a.on) else None}
    print(json.dumps(res))
    if not a.no_run:
        os.makedirs(OUT, exist_ok=True)
        json.dump(res, open(f'{OUT}/cgate-{os.path.basename(a.cand.rstrip("/"))}--{os.path.basename(a.ref.rstrip("/"))}.json', 'w'))

if __name__ == '__main__':
    main()
