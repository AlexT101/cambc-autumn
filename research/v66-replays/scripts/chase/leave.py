# Our pursuer's decisions during chases of hurt targets (pursuer healthy), from v66 traces.
import json, sys, os, re
sys.path.insert(0, 'research/v66-replays/scripts/trace')
from tlib import *
from concurrent.futures import ProcessPoolExecutor
EP = json.load(open(sys.argv[1]))
NAME = {'Ryth':'ryth','Vesper Vale':'vesper','Prism':'prism','Stellar':'stellar','Vendetta':'vendetta','Marcella':'marcella','Tavi':'tavi','Willow':'willow','Ren':'ren','Varg':'varg','Heart of Ruin':'hor','Cassi':'cassi','Issac':'issac'}
def key_of(src):
    m = re.search(r'-([0-9a-f]{8})/(\d+)-', src); return f'{m.group(1)}-{m.group(2)}'
by = defaultdict(list)
for x in EP:
    if x['side'] == 'us' and x['Php'] > x['Thp'] + float(os.environ.get('M','0')): by[key_of(x['src'])].append(x)
def one(k):
    if not os.path.exists(f'{ROOT}/{k}/trace.stdout.gz'): return []
    T, _ = load(k)
    # (r, type) -> decision, home why; trace c is our champion id
    D = {}
    for (r, c), rec in T.items():
        tt = rec['TT'][0] if rec['TT'] else None
        if not tt: continue
        why = next((e.get('why') for e in rec['TE'] if e.get('k') == 'home'), None)
        D[(r, tt['t'])] = (tt.get('d'), why)
    out = []
    for x in by[k]:
        seq = [D.get((r, NAME.get(x['P'], '?'))) for r in range(x['r'] + 1, x['r'] + x['len'] + 1)]
        if any(s is None for s in seq) or not seq: continue
        out.append((x['end'], x['Thp'], seq, x))
    return out
if __name__ == '__main__':
    with ProcessPoolExecutor(60) as ex: res = [y for o in ex.map(one, list(by)) for y in o]
    print('episodes with traces', len(res))
    for end in ('quit', 'kill', 'stand', 'home'):
        Y = [r for r in res if r[0] == end]
        if not Y: continue
        allc = Counter(s[0] for _, _, seq, _ in Y for s in seq)
        last = Counter(seq[-1][0] for _, _, seq, _ in Y)
        why = Counter(s[1] for _, _, seq, _ in Y for s in seq if s[0] == 'R')
        n = sum(allc.values())
        print(end, len(Y), 'rounds by decision:', ' '.join('%s %.2f' % (k, v / n) for k, v in allc.most_common(8)))
        print('    last round decision:', ' '.join('%s %d' % kv for kv in last.most_common(8)), ' | retreat why:', dict(why.most_common(6)))
    print()
    for lab, f in (('left (stand_lost/outmatched/stand_falls)', lambda seq: any(s[0]=='R' and s[1] in ('stand_lost','outmatched','stand_falls') for s in seq)),
                   ('left (low)', lambda seq: any(s[0]=='R' and s[1]=='low' for s in seq) and not any(s[0]=='R' and s[1] in ('stand_lost','outmatched','stand_falls') for s in seq)),
                   ('never retreated', lambda seq: not any(s[0]=='R' for s in seq))):
        Z=[r for r in res if f(r[2])]
        x=[r[3] for r in Z]
        print('%-44s n=%4d  P dies<=20r %.3f  T dies<=20r %.3f  allyP-allyT %.2f  P hp %.2f T hp %.2f' % (lab, len(Z), sum(e['Pdied20'] for e in x)/len(x), sum(e['Tdied20'] for e in x)/len(x),
              sum(e['allyP']-e['allyT'] for e in x)/len(x), sum(e['Php'] for e in x)/len(x), sum(e['Thp'] for e in x)/len(x)))
    EP2=[e for e in EP if e['side']=='them' and e['Php']>e['Thp']+float(os.environ.get('M','0'))]
    print('their pursuers, same filter: n=%d P dies %.3f T dies %.3f allyP-allyT %.2f' % (len(EP2), sum(e['Pdied20'] for e in EP2)/len(EP2), sum(e['Tdied20'] for e in EP2)/len(EP2), sum(e['allyP']-e['allyT'] for e in EP2)/len(EP2)))
    for dlt in (-2,-1,0,1,2):
        A=[r[3] for r in res if r[3]['allyP']-r[3]['allyT']==dlt and any(s[0]=='R' and s[1] in ('stand_lost','outmatched','stand_falls') for s in r[2])]
        B=[r[3] for r in res if r[3]['allyP']-r[3]['allyT']==dlt and not any(s[0]=='R' for s in r[2])]
        C=[e for e in EP2 if e['allyP']-e['allyT']==dlt]
        g=lambda L,k: '%.2f' % (sum(e[k] for e in L)/len(L)) if L else '-'
        print('  numbers %+d: we left n=%4d P dies %s T dies %s | we stayed n=%4d P dies %s T dies %s | them n=%4d P dies %s T dies %s' % (dlt, len(A), g(A,'Pdied20'), g(A,'Tdied20'), len(B), g(B,'Pdied20'), g(B,'Tdied20'), len(C), g(C,'Pdied20'), g(C,'Tdied20')))
