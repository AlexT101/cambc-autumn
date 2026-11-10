import json, sys, collections, statistics
rows = json.load(open(sys.argv[1]))
names = ['world','comms','pre-act','approach','decide-head','want_home','guard_steps','strikes','guard_work','pre-farm-rest','farm-call','farm-preloop','loop','postloop']
def segs(r):
    v = r['v']; out = {}
    last = 0; lastv = v[0]
    for i in range(1, 15):
        if v[i] == 0: continue
        nm = names[i-1]
        out[nm] = lastv - v[i]; lastv = v[i]
    return out
def pct(xs,q):
    xs=sorted(xs); return xs[min(len(xs)-1,int(q*len(xs)))] if xs else 0
late = [r for r in rows if r['round0'] > 1 and r['round0']==r['round1']]
cut = [r for r in late if r['k'] < r['ev']]
print('loop turns r>1', len(late), 'cut', len(cut), f'{len(cut)/len(late):.3f}', 'resumed-late rows', sum(1 for r in rows if r['round0']!=r['round1']))
by_dec = collections.Counter(r['dec'] for r in cut); print('cut by decision', by_dec.most_common())
for label, S in (('cut', cut), ('uncut', [r for r in late if r['k']>=r['ev']])):
    print('==', label, len(S))
    acc = collections.defaultdict(list)
    for r in S:
        s = segs(r)
        for n in names: acc[n].append(s.get(n, 0))
        acc['start'].append(r['v'][0])
        acc['at_farm_entry'].append(r['v'][11])
        acc['at_loop'].append(r['v'][12])
        acc['end_left'].append(r['end'])
        acc['queue'].append(r['v'][18]-r['v'][19] if r['v'][18] and r['v'][19] else 0)
        acc['act_tail'].append(r['v'][15]-r['v'][16] if r['v'][16] else 0)
        acc['turnorder+comms'].append(r['v'][17]-r['v'][18] if r['v'][18] else 0)
        acc['prev_left'].append(r['prev_left'] if r['prevq_round']==r['round0']-1 else -1)
    for n,xs in acc.items():
        print(f'{n:16s} mean {statistics.mean(xs):8.0f} p50 {pct(xs,.5):7d} p90 {pct(xs,.9):7d} nz {sum(1 for x in xs if x)/len(xs):.2f}')
