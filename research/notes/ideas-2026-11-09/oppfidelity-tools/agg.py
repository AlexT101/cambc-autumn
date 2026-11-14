# Aggregate episodes.py's pickle: opponent (and our) tribute policy by source, one-site vs other maps.
#   py agg.py EP.pkl [--until 600]
import collections, pickle, sys, json
P = pickle.load(open(sys.argv[1], 'rb'))
UNTIL = int(sys.argv[sys.argv.index('--until') + 1]) if '--until' in sys.argv else 10 ** 9
MC = json.load(open('/home/ubuntu/tmp-offload/handoff/gate/mapclass.json'))
def group(k):
    if k[0] == 'live': return f"live-{'A' if k[1] in (86, 87, 89, 95) else 'B'}"
    return f"loc-{k[1]}"
def b(d): return '<=3' if d <= 3 else '4-5' if d <= 5 else '6-8' if d <= 8 else '9+'
S = collections.defaultdict(lambda: collections.Counter())
for k, r in P.items():
    if 'err' in r: continue
    cls = MC.get(k[3], '?'); g = (group(k), cls)
    s = S[g]; s['games'] += 1; s['op600'] += r['op600']; s['us600'] += r['us600']; s['win'] += r['win']
    for e in r['eps']:
        if e['r'] > UNTIL: continue
        side = e['side']
        s[f'{side}:starts'] += 1; s[f'{side}:end:{e["end"]}'] += 1; s[f'{side}:d0:{b(e["d0"])}'] += 1
        if e['end'] == 'done': s[f'{side}:done_d0:{b(e["d0"])}'] += 1; s[f'{side}:gems_done'] += e.get('gems_end', e['gems'])
        if e['end'] == 'manual':
            s[f'{side}:man_d1<=5'] += (e['d1'] or 99) <= 5; s[f'{side}:man_fast'] += (e['held'] or 0) <= 1
            s[f'{side}:man_retry20'] += e['nxt'] is not None and e['nxt'] <= 20
    for (side, bb), n in r['wait'].items(): s[f'{side}:wait:{bb}'] += n
for g in sorted(S):
    s = S[g]; n = s['games']
    print(f"== {g[0]:8s} {g[1]:5s} games {n}  win {100*s['win']/n:.1f}  op600 {s['op600']/n:.0f}  us600 {s['us600']/n:.0f}")
    for side in ('op', 'us'):
        st = s[f'{side}:starts']
        if not st: continue
        ends = ' '.join(f"{e}:{s[f'{side}:end:{e}']/n:.2f}" for e in ('done', 'manual', 'stun', 'lock', 'death', 'open'))
        d0 = ' '.join(f"{bb}:{s[f'{side}:d0:{bb}']/n:.2f}" for bb in ('<=3', '4-5', '6-8', '9+'))
        dd = ' '.join(f"{bb}:{s[f'{side}:done_d0:{bb}']/n:.2f}" for bb in ('<=3', '4-5', '6-8', '9+'))
        wt = ' '.join(f"{bb}:{s[f'{side}:wait:{bb}']/n:.1f}" for bb in ('<=3', '4-5', '6-8', '9+'))
        m = s[f'{side}:end:manual']
        print(f"   {side}: starts/g {st/n:.2f}  ends/g {ends}  gems done/g {s[f'{side}:gems_done']/n:.0f}")
        print(f"       start d0/g {d0}   done by d0/g {dd}")
        if m: print(f"       manual: d1<=5 {100*s[f'{side}:man_d1<=5']/m:.0f}%  held<=1 {100*s[f'{side}:man_fast']/m:.0f}%  retry<=20r {100*s[f'{side}:man_retry20']/m:.0f}%")
        print(f"       altar-wait rounds/g {wt}")
