# Death-episode categories from episodes_<src>.json: what the stand sim said when the episode began, and
# whether the champions that hurt and killed us were in it.
import sys, json
from collections import Counter, defaultdict
for src in sys.argv[1:] or ['ladder', 'selfplay']:
    E = json.load(open(f'replays/v66-analysis/simcal/episodes_{src}.json'))
    cat = Counter(); share = defaultdict(list); first_lost = []; dmg_after = []
    byopp = defaultdict(Counter)
    for e in E:
        V = [v for v in e['verdicts'] if v['why'] and v['why'].startswith('stand') and v['t'] and v['t'].split(':')[5] != '0']
        tot = sum(e['dmgers'].values())
        if not V:
            k = 'no stand sim with an enemy in the episode'
        else:
            v0 = V[0]
            ros = set(v0['roster'] or [])
            if v0['why'] == 'stand_ok':
                if v0['roster'] is None: k = 'first sim stand_ok (roster unknown)'
                else:
                    ins = sum(a for h, a in e['dmgers'].items() if int(h) in ros) / max(1, tot)
                    share['ok_in'].append(ins)
                    kin = e['killer'] in ros
                    k = 'first sim stand_ok, killer %s sim' % ('in' if kin else 'NOT in')
            else:
                k = 'first sim ' + v0['why']
            # first lost verdict and the damage taken from then on
        cat[k] += 1; byopp[e['opp']][k] += 1
    n = len(E)
    print('\n## %s: %d death episodes (r<=260)' % (src, n))
    for k, v in cat.most_common(): print('  %-48s %4d %5.1f%%' % (k, v, 100 * v / n))
    if share['ok_in']:
        s = share['ok_in']; print('  stand_ok-first episodes with a roster: share of episode damage from sim members: mean %.2f, <0.5 in %.0f%%' % (sum(s) / len(s), 100 * sum(x < 0.5 for x in s) / len(s)))
    if src == 'ladder':
        for o, c in sorted(byopp.items()):
            print('  ' + o + ': ' + ', '.join('%s %d' % (k.replace('first sim ', ''), v) for k, v in c.most_common()))
