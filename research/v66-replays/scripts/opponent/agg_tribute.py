# Q3 aggregation: tribute sizes/timing, cancels, locks, teleports, consumables.
import json, glob, statistics as st
from collections import defaultdict, Counter
S = 'replays/v66-analysis'
F = [json.load(open(p)) for p in glob.glob(S + '/opp/feat/*.json')]
OPP = ['Fish', 'Mite', 'UoS', 'PBG']
by = defaultdict(list)
for f in F: by[f['opp']].append(f)
mean = lambda a: sum(a) / len(a) if a else float('nan')
def q(a, p):
    a = sorted(a); return a[int(p * (len(a) - 1))] if a else None
for o in OPP:
    for who in ('us', 'them'):
        tr = []; canc = Counter(); lk = []; tb = 0; tele = 0; cons = Counter(); first = []; gstart = []
        lock_cancel_victims = 0; per_game = []
        for f in by[o]:
            t = f['us'] if who == 'us' else 1 - f['us']
            ts = [x for x in f['trib'] if x['t'] == t]
            per_game.append(len(ts))
            tr += ts
            if ts: first.append(min(x['r'] for x in ts))
            for x in f['tcancel']:
                if x['t'] == t: canc[x['cause']] += 1
            lk += [x for x in f['locks'] if x['t'] == t]
            tb += sum(1 for x in f['tblocked'] if x['t'] == t)
            tele += sum(1 for x in f['tele'] if x['t'] == t)
            for x in f['cons']:
                if x['t'] == t: cons[x['name']] += x['n']
        g = [x['gems'] for x in tr]
        done = [x for x in tr if 'end' in x]
        n = len(by[o])
        print(f"{o:5}{who:5} tributes/game {len(tr)/n:5.1f} gems p25/50/75 {q(g,.25)}/{q(g,.5)}/{q(g,.75)} mean {mean(g):.0f} | completed {len(done)/max(1,len(tr))*100:.0f}% | cancels {dict(canc)} | first trib med r{st.median(first) if first else '-'}")
        print(f"            locks/game {len(lk)/n:.2f} by {Counter(x['a'] for x in lk).most_common(3)} | tribute_blocked {tb/n:.2f}/game | teleports {tele/n:.2f}/game | consumables {dict(cons)}")
