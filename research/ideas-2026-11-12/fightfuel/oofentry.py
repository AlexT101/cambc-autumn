"""Out-of-fuel turns by the step they ran out in, with the fuel left on entry to it: python3 oofentry.py BATCHGLOB"""
import sys, collections
import fzread
from instr_ids import IDS
ENTRY = {'farm': 82, 'search_strikes': 84, 'retreat': 86, 'turn_order': 85}
if __name__ == '__main__':
    R = fzread.rows(sys.argv[1:])
    games = len({r['game'] for r in R})
    O = [r for r in R if r['oof'] is not None and r['round'] > 2]
    q = lambda u, p: u[min(len(u) - 1, int(p * len(u)))] if u else 0
    print(f'{len(O) / games:.2f} out-of-fuel turns a game')
    by = collections.defaultdict(list)
    for r in O: by[IDS.get(r['oof'][1], str(r['oof'][1])) if len(r['oof']) > 1 else ('decide' if r['oof'] else 'outside')].append(r)
    for k, S in sorted(by.items(), key=lambda kv: -len(kv[1])):
        line = f'{k:20s} {len(S) / games:5.2f} a game ({100 * len(S) / len(O):4.1f}%)  enemy in sight {100 * sum(1 for r in S if r["seen"] > 0) / len(S):3.0f}%'
        if k in ENTRY:
            e = sorted(r['sc'][ENTRY[k]][0] for r in S if ENTRY[k] in r['sc'])
            line += f'  fuel on entry: p10 {q(e, .1)} p25 {q(e, .25)} p50 {q(e, .5)} p75 {q(e, .75)} p90 {q(e, .9)}; under 10k {100 * sum(1 for x in e if x < 10000) / max(1, len(e)):.0f}%, under 20k {100 * sum(1 for x in e if x < 20000) / max(1, len(e)):.0f}%'
        # what ran before: the biggest scopes
        tot = collections.Counter()
        for r in S:
            for i, (f, n) in r['sc'].items():
                if i < 80 and i != 2: tot[i] += f
        line += '\n      before it, mean: ' + ' '.join(f'{IDS.get(i, i)} {tot[i] / len(S):.0f}' for i in sorted(tot, key=lambda i: -tot[i])[:9])
        print(line)
