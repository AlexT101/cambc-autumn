import sys, collections
d = sys.argv[1]
src = open(__file__.replace('rep.py', 'an.py')).read().split('main(sys.argv[1])')[0]
exec(src)
c = collections.Counter(); f = collections.Counter()
for t in list(turns(d)):
    if t['simfuel'] < 8000: continue
    seen = []
    for s in t['sims']:
        full = (s['tf'], s['camp'], tuple(s['us']), tuple(s['them']))
        for o in seen:
            if o[0] == full:
                c[(TAG[o[1]], TAG[s['tag']])] += 1; f[(TAG[o[1]], TAG[s['tag']])] += s['fuel']; break
        seen.append((full, s['tag']))
print(sum(c.values()))
for k, v in c.most_common(): print(k, v, f[k])
