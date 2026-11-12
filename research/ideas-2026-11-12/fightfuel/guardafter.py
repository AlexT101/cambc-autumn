"""What a turn spends after its step guard, and what the guard's parts cost: python3 guardafter.py BATCHGLOB
(profile v3: @guard_entry 89, @guard_exit 88, guard_sims 72, step_guard 25)."""
import sys, collections
import fzread
if __name__ == '__main__':
    R = fzread.rows(sys.argv[1:])
    R = [r for r in R if r['round'] > 2 and r['hp'] >= 0 and r['seen'] > 0]
    q = lambda u, p: u[min(len(u) - 1, int(p * len(u)))] if u else 0
    pct = lambda u: f'p50 {q(u, .5)} p75 {q(u, .75)} p90 {q(u, .9)} p95 {q(u, .95)} p99 {q(u, .99)}'
    G = [r for r in R if 88 in r['sc']]
    print(f'{len(G)} fight turns that asked for the step guard ({100 * len(G) / len(R):.1f}% of fight turns)')
    for name, S in (('guard placed (no entry cut)', [r for r in G if 'step-guard-entry' not in r['cuts']]), ('entry cut', [r for r in G if 'step-guard-entry' in r['cuts']])):
        fin = [r for r in S if r['oof'] is None]
        print(f'\n{name}: {len(S)}; out of fuel {100 * (len(S) - len(fin)) / max(1, len(S)):.2f}%')
        after_decide = sorted(r['sc'][88][0] - r['left_decide'] for r in fin)
        after_all = sorted(r['sc'][88][0] - r['left_queue'] for r in fin if r['left_queue'])
        print(f'  spent after the guard to the end of decide: {pct(after_decide)}')
        print(f'  spent after the guard to the turn-end queue: {pct(after_all)}')
        entry = sorted(r['sc'][89][0] for r in fin if 89 in r['sc'])
        print(f'  fuel left on the guard\'s first entry: p10 {q(entry, .1)} p25 {q(entry, .25)} p50 {q(entry, .5)} p75 {q(entry, .75)}')
        if name.startswith('guard'):
            cost = sorted(r['sc'][25][0] for r in fin if 25 in r['sc']); sims = sorted(r['sc'].get(72, (0, 0))[0] for r in fin); ns = sorted(r['sc'].get(72, (0, 0))[1] for r in fin)
            st1 = sorted(r['sc'][25][0] - r['sc'].get(72, (0, 0))[0] for r in fin if 25 in r['sc'])
            print(f'  the guard: {pct(cost)}')
            print(f'    its new sims: {pct(sims)}; count p90 {q(ns, .9)} p99 {q(ns, .99)}; turns with a new sim {100 * sum(1 for x in ns if x) / len(ns):.1f}%')
            one = sorted(r['sc'][72][0] / r['sc'][72][1] for r in fin if 72 in r['sc'])
            print(f'    one new sim: {pct([int(x) for x in one])}')
            print(f'    the rest (covers, exposures, looks): {pct(st1)}')
        # by what follows
        for d in 'FCB':
            T = sorted(r['sc'][88][0] - r['left_queue'] for r in fin if r['dec'] == d and r['left_queue'])
            if T: print(f'    decision {d}: {len(T)}; after the guard to the queue: {pct(T)}')
