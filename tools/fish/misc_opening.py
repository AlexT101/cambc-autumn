"""Fish's opening: are its inputs a function of the map? (MISC.md section 5)

    python3 tools/fish/misc_opening.py OUT.json

Games are grouped by (map, Fish side, Fish roster). For each pair in a group, every actor's input
sequence (kind, target; priority writes included, recall preparation included) is compared round
by round; the pair's divergence round is the first round in which any actor's inputs differ.
Each divergence is classified by what is first seen: an enemy champion visible at the turn start
of any Fish actor in either game, before or at that round. Pairs whose opponents drafted the same
champions (item-log cohorts) are reported apart. Also the first camp group each actor attacks.
"""
import argparse, gzip, itertools, json, sys
from collections import Counter, defaultdict
sys.path.insert(0, 'tools/fish')
from misc_common import *

CAP = 300  # rounds compared; a pair identical through CAP counts as 'never' diverging


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('out'); a = ap.parse_args()
    with gzip.open(ITEMS) as f: opp = {g['sha256'][:16]: tuple(g['oppPicks']) for g in json.load(f)['games']}
    G = defaultdict(list)
    for g in games():
        rows = g['rows']; roster = tuple(sorted({(r['id'], r['name']) for r in rows}))
        seq = defaultdict(lambda: defaultdict(list)); seen = 10 ** 9; first_camp = {}
        for r in rows:
            if r['ne']: seen = min(seen, r['r'])
            if r['r'] > CAP: continue
            seq[r['id']][r['r']] = [(x['k'], tuple(x['to']), x.get('v')) for x in r['a']]
            for x in r['a']:
                if x['k'] == 'Attack' and r['id'] not in first_camp:
                    hit = [c for c in r.get('cps', []) if (c[3], c[4]) == tuple(x['to'])]
                    if hit: first_camp[r['id']] = (r['r'], hit[0][1])
        G[(g['map'], g['side'], roster)].append({'game': g['game'], 'cohort': g['cohort'], 'seq': seq, 'seen': seen, 'opp': opp.get(g['game']), 'camp': first_camp})
    pairs = []; C = Counter()
    for k, v in G.items():
        for x, y in itertools.combinations(v, 2):
            rounds = sorted({r for s in (x['seq'], y['seq']) for aid in s for r in s[aid]})
            d = None; who = None
            for r in rounds:
                for aid in sorted(set(x['seq']) | set(y['seq'])):
                    if x['seq'][aid].get(r) != y['seq'][aid].get(r): d, who = r, aid; break
                if d is not None: break
            seen = min(x['seen'], y['seen'])
            same_opp = x['opp'] is not None and x['opp'] == y['opp']
            cls = 'never' if d is None else 'before-enemy-seen' if d < seen else 'at-or-after-enemy-seen'
            C[(cls,)] += 1; C[(cls, 'same-opp-draft' if same_opp else 'other')] += 1
            camp_same = all(x['camp'].get(i) == y['camp'].get(i) for i in set(x['camp']) | set(y['camp']))
            C[('first-camp-group-and-round-identical', camp_same)] += 1
            pairs.append({'map': k[0], 'side': k[1], 'a': x['game'], 'b': y['game'], 'diverge': d, 'actor': who, 'first_enemy_seen': seen,
                          'same_opp_draft': same_opp, 'first_camp_same': camp_same,
                          'a_inputs': x['seq'][who].get(d) if who is not None else None, 'b_inputs': y['seq'][who].get(d) if who is not None else None})
    n = len(pairs)
    div = [p['diverge'] for p in pairs if p['diverge'] is not None]
    pre = [p for p in pairs if p['diverge'] is not None and p['diverge'] < p['first_enemy_seen']]
    summary = {'groups_with_pairs': sum(1 for v in G.values() if len(v) > 1), 'pairs': n,
               'classes': {' '.join(map(str, k)): v for k, v in C.items()},
               'identical_through_round': {'cap': CAP, **{str(R): sum(1 for p in pairs if p['diverge'] is None or p['diverge'] > R) for R in (1, 5, 10, 20, 50, 100, 200)}},
               'median_divergence': sorted(div)[len(div) // 2] if div else None,
               'pre_sighting_divergence_examples': sorted(pre, key=lambda p: p['diverge'])[:15]}
    print(json.dumps({k: v for k, v in summary.items() if k != 'pre_sighting_divergence_examples'}, indent=1))
    for p in summary['pre_sighting_divergence_examples'][:8]:
        print(p['map'], p['a'], p['b'], 'r', p['diverge'], 'actor', p['actor'], 'seen', p['first_enemy_seen'], p['a_inputs'], '|', p['b_inputs'])
    write_result(a.out, {'doc': __doc__, 'summary': summary, 'pairs': pairs})


if __name__ == '__main__':
    main()
