"""Calibration: live results against a Mite pin per (map, our side), against a body's local results on the same cells.
    py calread.py BODY [BODY...] [--ref r7]
For each live version (v115 oc-dfuel-506, v116 charybdis-p3, v117 c520-ps): live win%, body win% on the same cells
(mean over the body's noise members), per-cell agreement, and the Brier score / log-likelihood of the live outcomes
under the body's per-cell win rate (shrunk toward the body's overall rate with weight 1 game)."""
import json, glob, os, sys, math, collections
R = '/home/ubuntu/cambc-autumn/'
VER = {115: 'oc-dfuel-506', 116: 'charybdis-p3', 117: 'c520-ps'}
args = [a for a in sys.argv[1:] if not a.startswith('--')]
ref = sys.argv[sys.argv.index('--ref') + 1] if '--ref' in sys.argv else 'r7'
args = [a for a in args if a != ref]
norm = lambda m: m.replace('_', '-')

def live():
    out = collections.defaultdict(list)
    for l in open(R + 'research/ladder-scrims-2026-11-06/data/games.jsonl'):
        g = json.loads(l)
        if g.get('opp_name') == 'Mite' and g.get('refset') == ref and g.get('status') == 'finished':
            out[(g['version'], norm(g['map']), g['side'])].append(g['result'] == 'win')
    return out

def local(bot, body, suite='ladder'):
    cell = collections.defaultdict(list)
    for d in glob.glob(f'{R}replays/batch-*-ab-mf-{bot}-{body}-{suite}-k*-{suite}'):
        f = d + '/results.json'
        if not os.path.exists(f): continue
        for m in json.load(open(f))['matches']:
            if m.get('winner') is None: continue
            stem = norm(os.path.basename(m['map'])[:-7]); side = 'a' if m['order'][0] == 0 else 'b'
            us = 0 if side == 'a' else 1
            cell[(stem, side)].append(m['winner'] == 0)  # winner is the bot index, 0 = ours
    return cell

def ci(p, n): h = 1.96 * math.sqrt(max(p * (1 - p), 1e-9) / max(n, 1)); return f'{100*p:.1f} ({100*max(0,p-h):.1f}-{100*min(1,p+h):.1f}) of {n}'

L = live()
print(f'Mite {ref} live vs bodies')
for body in args:
    print(f'\n== {body}')
    print('| our version | live win % | body win %, same cells | body win %, all cells | cells | agree | Brier live|body | Brier live|const | loglik/game |')
    print('|---|---|---|---|---|---|---|---|---|')
    for v, bot in VER.items():
        C = local(bot, body)
        if not C: continue
        allg = [x for v_ in C.values() for x in v_]; pall = sum(allg) / len(allg)
        lv = [(k, x) for (vv, *k), xs in L.items() if vv == v for x in xs]
        lv = [(tuple(k), x) for k, x in lv if tuple(k) in C]
        if not lv: continue
        pl = sum(x for _, x in lv) / len(lv)
        pb = [(sum(C[k]) + pall) / (len(C[k]) + 1) for k, _ in lv]
        same = sum(pb) / len(pb)
        agree = sum((p > .5) == x for p, (_, x) in zip(pb, lv)) / len(lv)
        brier = sum((p - x) ** 2 for p, (_, x) in zip(pb, lv)) / len(lv)
        bconst = sum((pl - x) ** 2 for _, x in lv) / len(lv)
        ll = sum(math.log(min(max(p if x else 1 - p, .02), .98)) for p, (_, x) in zip(pb, lv)) / len(lv)
        print(f'| v{v} {bot} | {ci(pl, len(lv))} | {100*same:.1f} | {ci(pall, len(allg))} | {len(lv)} | {100*agree:.1f}% | {brier:.4f} | {bconst:.4f} | {ll:.4f} |')
