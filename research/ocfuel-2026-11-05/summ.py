"""summ.py REF TAG...: per tag, 100M fuel (default/wide/fresh: identical replays vs REF, mean, p99, total play fuel)
and real-budget farm-partial-evaluation and OOF (rwide/rfresh), against REF."""
import json, sys, ast
D = '/home/ubuntu/cambc-autumn/.claude/worktrees/agent-abfd641d0547466f5/replays/fuel/oc'
def load(t, s):
    try: return json.load(open(f'{D}/{t}-{s}.json'))
    except FileNotFoundError: return None
def total(d):
    n = 0
    for g in d['games']:
        p = g['play'] if isinstance(g['play'], list) else ast.literal_eval(g['play'])
        n += sum(p[g['bodies']:])
    return n
def sc(d, k):
    t = 0
    for g in d['games']:
        s = g['shortcuts'] if isinstance(g['shortcuts'], dict) else ast.literal_eval(g['shortcuts'])
        t += s.get(k, 0)
    return t
ref = sys.argv[1]
for t in sys.argv[1:]:
    row = [t]
    for s in ('default', 'wide', 'fresh'):
        d, r = load(t, s), load(ref, s)
        if not d: row.append(f'{s}: -'); continue
        same = sum(a['replay'] == b['replay'] for a, b in zip(d['games'], r['games']))
        tt, tr = total(d), total(r)
        row.append(f"{s}: {same}/{len(d['games'])} mean {d['all']['mean']} p99 {d['all']['p99']} tot {100*(tt-tr)/tr:+.2f}%")
    for s in ('rwide', 'rfresh'):
        d, r = load(t, s), load(ref, s)
        if not d: row.append(f'{s}: -'); continue
        f, fr = sc(d, 'farm-partial-evaluation'), sc(r, 'farm-partial-evaluation')
        o, orr = sum(g['out_of_fuel'] for g in d['games']), sum(g['out_of_fuel'] for g in r['games'])
        row.append(f"{s}: fpe {f} ({100*(f-fr)/max(fr,1):+.1f}%) oof {o} ({100*(o-orr)/max(orr,1):+.1f}%)")
    print('\n   '.join(row))
