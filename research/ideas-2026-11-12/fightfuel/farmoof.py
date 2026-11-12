"""Fuel on entry to the farm step and its loop, and where turns that run out inside farm stand: python3 farmoof.py BATCHGLOB"""
import sys, collections
import fzread
from instr_ids import IDS
if __name__ == '__main__':
    R = fzread.rows(sys.argv[1:])
    R = [r for r in R if r['round'] > 2 and r['hp'] >= 0 and r['seen'] > 0]
    q = lambda u, p: u[min(len(u) - 1, int(p * len(u)))] if u else 0
    for who in (True, False):
        S = [r for r in R if r['prism'] == who and 82 in r['sc']]
        print(f'\n{"Prism" if who else "others"}: fight turns that reach farm: {len(S)}')
        a = sorted(r['sc'][82][0] for r in S); print(f'  fuel left on entry: p10 {q(a,.1)} p50 {q(a,.5)} p90 {q(a,.9)}')
        b = sorted(r['sc'][82][0] - r['sc'][87][0] for r in S if 87 in r['sc']); print(f'  farm before its loop: p50 {q(b,.5)} p90 {q(b,.9)} p99 {q(b,.99)}  (n {len(b)})')
        noloop = [r for r in S if 87 not in r['sc']]
        print(f'  never reached the loop: {len(noloop)} ({100*len(noloop)/len(S):.1f}%), out of fuel among them {sum(1 for r in noloop if r["oof"] is not None)}')
        O = [r for r in S if r['oof'] is not None and len(r['oof']) >= 2 and r['oof'][1] == 21]
        print(f'  ran out inside farm: {len(O)}; stacks: ' + ', '.join(f'{".".join(IDS.get(i, str(i)) for i in k[1:])} {n}' for k, n in collections.Counter(r['oof'] for r in O).most_common(6)))
        e = sorted(r['sc'][82][0] for r in O); print(f'    their fuel on farm entry: p10 {q(e,.1)} p50 {q(e,.5)} p90 {q(e,.9)}')
        e2 = sorted(r['sc'][87][0] for r in O if 87 in r['sc']); print(f'    reached the loop: {len(e2)}, fuel then: p10 {q(e2,.1)} p50 {q(e2,.5)} p90 {q(e2,.9)}')
        cl = sorted(r['sc'].get(44, (0, 0))[0] for r in O if 44 in r['sc']); print(f'    loop done ({len(cl)}): cost p50 {q(cl,.5)} p90 {q(cl,.9)}; with farm-partial: {sum(1 for r in O if "farm-partial-evaluation" in r["cuts"])}')
