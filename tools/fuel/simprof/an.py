"""Fight-simulation profile: every simulate() of a turn, by caller, on turns whose sims cost >= 8k.

    mkdir -p bots/variants/astraeus-simprof && cp -r bots/astraeus/src bots/variants/astraeus-simprof/
    py tools/fuel/simprof/patch_prof.py bots/variants/astraeus-simprof/src   # fails loudly once the code moved
    py tools/fuel/bench.py run bots/variants/astraeus-simprof --opp ... --maps ... --games DIR --out x.json
    py tools/fuel/simprof/an.py DIR      # by caller, outcomes, guard settles/memo hits, exact repeats
    py tools/fuel/simprof/rep.py DIR     # which callers repeat an identical fight in a turn
    py tools/fuel/simprof/sides.py DIR   # sims sharing one whole side with an earlier sim of the turn

The copy prints `PT round champ decide n simfuel C tag:settled/memo/simulated/other...` per turn with sims, and
`PS tag fuel acts quiet we they falls tf plain camp | ours | theirs` per sim (fighter id:arrival:ready0:ready1:
health:shield:strength). Tags: 1 stand's own sim, 2 stand via fight_of, 3/4 step guard unions U1/U2, 5 guard
tile, 6 chase_trade's own, 7 chase via fight_of, 8 fight(), 9 turns_to_kill_idle.
"""
import sys, zipfile, glob, collections, os
TAG = {1: 'stand', 2: 'stand-fo', 3: 'U1', 4: 'U2', 5: 'tile', 6: 'chase', 7: 'chase-fo', 8: 'fight', 9: 'idle', 0: '?'}

def turns(d):
    for z in glob.glob(os.path.join(d, '**', '*.repl26a'), recursive=True):
        with zipfile.ZipFile(z) as zf:
            for side in 'ab':
                try:
                    s = zf.read(f'team-{side}.stdout').decode('utf-8', 'replace').replace('\x00', '')
                except KeyError:
                    continue
                if 'PT ' not in s:
                    continue  # the opponent
                cur = None
                for line in s.splitlines():
                    if line.startswith('PT '):
                        p = line.split()
                        if len(p) < 7 or p[6] != 'C' or not all(x.lstrip('-').isdigit() for x in p[1:6]):
                            cur = None
                            continue
                        counts = {}
                        for c in p[7:]:
                            if c.count(':') != 1 or c.split(':')[1].count('/') != 3: continue
                            t, v = c.split(':')
                            counts[int(t)] = list(map(int, v.split('/')))
                        cur = dict(map=os.path.basename(z), round=int(p[1]), champ=int(p[2]), decide=int(p[3]), n=int(p[4]), simfuel=int(p[5]), counts=counts, sims=[])
                        yield cur
                    elif line.startswith('PS ') and cur is not None and line.count('|') >= 1 and len(line.split('|')[0].split()) == 11:
                        head, *sides = line.split('|')
                        h = head.split()
                        us = [tuple(x.split(':')) for x in sides[0].split()]
                        them = [tuple(x.split(':')) for x in sides[1].split()] if len(sides) > 1 else []
                        cur['sims'].append(dict(tag=int(h[1]), fuel=int(h[2]), acts=int(h[3]), quiet=int(h[4]), we=int(h[5]), they=int(h[6]), falls=int(h[7]), tf=int(h[8]), plain=h[9], camp=float(h[10]), us=us, them=them))

def main(d):
    T = list(turns(d))
    heavy = [t for t in T if t['simfuel'] >= 8000]
    allsims = sum(t['n'] for t in T)
    print(f'turns with sims {len(T)}, sims {allsims}, heavy-sim turns {len(heavy)} (decide mean {sum(t["decide"] for t in heavy)/max(1,len(heavy)):.0f}, sim fuel mean {sum(t["simfuel"] for t in heavy)/max(1,len(heavy)):.0f})')
    dec = [t for t in T if t['decide'] >= 70000]
    print(f'decide>=70k turns {len(dec)}: sim fuel mean {sum(t["simfuel"] for t in dec)/max(1,len(dec)):.0f}, sims/turn {sum(t["n"] for t in dec)/max(1,len(dec)):.2f}')
    # per tag in heavy turns
    by = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
    for t in heavy:
        for s in t['sims']:
            b = by[s['tag']]; b[0] += 1; b[1] += s['fuel']; b[2] += s['acts']; b[3] += s['quiet']
    print('heavy turns, by caller: n, fuel/sim, acts/sim, quiet half-turns/sim, share of sim fuel')
    tot = sum(b[1] for b in by.values())
    for k, b in sorted(by.items(), key=lambda kv: -kv[1][1]):
        print(f'  {TAG[k]:9s} {b[0]:6d} {b[1]/b[0]:7.0f} {b[2]/b[0]:5.1f} {b[3]/b[0]:5.1f} {100*b[1]/tot:5.1f}%')
    cnt = collections.defaultdict(lambda: [0, 0, 0, 0])
    for t in T:
        for k, v in t['counts'].items():
            for i in range(4): cnt[k][i] += v[i]
    print('guard outcome() calls: settled-by-cover / memo / simulated / k==2', dict((TAG[k], v) for k, v in cnt.items()))
    # sims per heavy turn, and duplicate / near-duplicate structure
    same_all = same_roster = same_roster_tf = 0; dup_fuel = 0; roster_fuel = 0
    pair_prefix = []
    for t in heavy:
        seen = []
        for s in t['sims']:
            ids = (tuple(sorted(f[0] for f in s['us'])), tuple(sorted(f[0] for f in s['them'])))
            full = (s['tf'], s['camp'], tuple(s['us']), tuple(s['them']))
            if any(full == o[1] for o in seen):
                same_all += 1; dup_fuel += s['fuel']
            elif any(ids == o[0] for o in seen):
                same_roster += 1; roster_fuel += s['fuel']
                # shared prefix in half-turns: first fighter whose state differs, by its arrival
                best = 0
                for o in seen:
                    if o[0] != ids or o[2]['tf'] != s['tf'] or o[2]['camp'] != s['camp']:
                        continue
                    a = {f[0]: f for f in o[2]['us'] + o[2]['them']}
                    b = {f[0]: f for f in s['us'] + s['them']}
                    diff = [k for k in a if a[k] != b[k]]
                    # only arrival differences can share a prefix; the earlier arrival bounds it
                    if all(a[k][2:] == b[k][2:] for k in diff):
                        first = min(min(int(a[k][1]), int(b[k][1])) for k in diff)
                        best = max(best, first)
                pair_prefix.append((best, s['fuel'], s['acts'] + s['quiet']))
            seen.append((ids, full, s))
    print(f'heavy-turn sims repeated exactly in the turn: {same_all} ({dup_fuel} fuel); same roster other inputs: {same_roster} ({roster_fuel} fuel)')
    pp = collections.Counter(p[0] for p in pair_prefix)
    print('  of those, shareable prefix in own turns (same tf/camp, arrival-only diff):', sorted(pp.items()))
    # U1 outcomes
    u1 = [s for t in heavy for s in t['sims'] if s['tag'] == 3]
    res = collections.Counter(('lost' if s['they'] > 0 else 'won' if s['we'] > 0 else 'none') + ('/falls' if s['falls'] else '') for s in u1)
    print('U1 outcomes (heavy turns):', res)
    for tag in (1, 3, 4, 5, 6):
        ss = [s for t in heavy for s in t['sims'] if s['tag'] == tag]
        if not ss: continue
        r = collections.Counter(('lost' if s['they'] > 0 else 'won' if s['we'] > 0 else 'none') + ('/falls' if s['falls'] else '') for s in ss)
        fz = collections.defaultdict(int)
        for s in ss:
            fz[('lost' if s['they'] > 0 else 'won' if s['we'] > 0 else 'none') + ('/falls' if s['falls'] else '')] += s['fuel']
        print(f'  {TAG[tag]}: ' + ', '.join(f'{k} {v} ({fz[k]/v:.0f})' for k, v in r.most_common()))
    sizes = collections.Counter((len(s['us']), len(s['them'])) for t in heavy for s in t['sims'])
    print('roster sizes (us,them):', sizes.most_common(10))
    plains = collections.Counter(s['plain'] for t in heavy for s in t['sims'])
    print('plain us/them:', plains)

main(sys.argv[1])
