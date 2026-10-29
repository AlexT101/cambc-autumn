import sys, collections
d = sys.argv[1]
exec(open(__file__.replace('sides.py', 'an.py')).read().split('main(sys.argv[1])')[0])
T = [t for t in list(turns(d)) if t['simfuel'] >= 8000]
n = same_them = same_us = same_either = 0
fuel = f_them = f_us = 0
distinct_them = []
end_kind = collections.Counter()
for t in T:
    th, us = set(), set()
    for s in t['sims']:
        a, b = tuple(s['them']), (tuple(s['us']), s['camp'])
        n += 1; fuel += s['fuel']
        if a in th: same_them += 1; f_them += s['fuel']
        if b in us: same_us += 1; f_us += s['fuel']
        if a in th or b in us: same_either += 1
        th.add(a); us.add(b)
        # did anyone die? acts+quiet near 34 means the horizon
        end_kind['horizon' if s['acts'] + s['quiet'] >= 30 else 'early'] += 1
    distinct_them.append(len(th) / max(1, len(t['sims'])))
print(f'heavy turns {len(T)}, sims {n}, sims/turn {n/len(T):.2f}')
print(f'their side identical to an earlier sim this turn: {same_them} ({100*same_them/n:.1f}%, {100*f_them/fuel:.1f}% of fuel)')
print(f'our side (with camp) identical: {same_us} ({100*same_us/n:.1f}%, {100*f_us/fuel:.1f}% of fuel); either: {same_either}')
print('sims played to (near) the horizon:', end_kind)
