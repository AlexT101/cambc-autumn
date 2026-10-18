import pickle
from collections import Counter, defaultdict
from statistics import mean, median
from common import TOP, US, SHORT, ref

F = pickle.load(open(__file__.replace('agg_moves.py', 'moves.pkl'), 'rb'))
TEAMS = TOP + [US]
pct = lambda a, b: f'{100*a/b:.0f}%' if b else '-'

print('## Openings (camp groups damaged in rounds 1-60)\n')
st = defaultdict(Counter)
for f in F:
    for t in (0, 1):
        n = f['names'][t]
        o = f['opening'].get(t) or f['opening'].get(str(t)) or []
        st[n]['g'] += 1
        st[n]['groups'] += len(o)
        if o:
            st[n]['first_r'] += o[0][4]
            st[n]['first_n'] += len(o[0][3])
            st[n]['first_' + o[0][2]] += 1
            st[n]['enemy_any'] += any(x[2] == 'enemy' for x in o)
print('| team | groups hit by r60 | first camp hit round | bodies on first camp | first camp own/mid/enemy | hit an enemy-side camp by r60 |')
print('|---|---|---|---|---|---|')
for n in TEAMS:
    s = st[n]
    G = s['g']
    if G:
        print(f"| {SHORT[n]} | {s['groups']/G:.1f} | {s['first_r']/G:.1f} | {s['first_n']/G:.1f} | {pct(s['first_own'],G)}/{pct(s['first_mid'],G)}/{pct(s['first_enemy'],G)} | {pct(s['enemy_any'],G)} |")
print()
print('## Territory (share of alive champion-rounds in the enemy half)\n')
tt = defaultdict(Counter)
for f in F:
    for (t, ph), d in f['terr'].items():
        n = f['names'][t]
        tt[n][(ph, 'n')] += d['n']
        tt[n][(ph, 'e')] += d.get(1, 0)
print('| team | r1-60 | r61-200 | r201+ |')
print('|---|---|---|---|')
for n in TEAMS:
    s = tt[n]
    print(f"| {SHORT[n]} | " + ' | '.join(pct(s[(ph, 'e')], s[(ph, 'n')]) for ph in (0, 1, 2)) + ' |')
print()
print('## Reaction when seeing >=3 enemies within 8 with <=1 ally within 4\n')
rs = defaultdict(Counter)
for f in F:
    T = f['team_of']
    for r in f['react']:
        n = f['names'][T[r['c']]]
        k = 'alone' if r['na'] == 0 else 'one'
        rs[n]['n'] += 1
        rs[n]['died10'] += r['died10']
        if r['d3'] is not None:
            rs[n]['away'] += r['d3'] > r['d0']
            rs[n]['closer'] += r['d3'] < r['d0']
        rs[n]['home'] += r['outcome'] == 'home'
        rs[n]['recall'] += r['chan'] == 1
        rs[n]['ownhalf'] += r['half'] == 0
        if r['half'] == 0:
            rs[n]['oh_died'] += r['died10']
        else:
            rs[n]['eh_died'] += r['died10']
print('| team | events/g | in own half | moved away within 3 rounds | moved closer | recalling | died within 10 (own half / enemy half) |')
print('|---|---|---|---|---|---|---|')
for n in TEAMS:
    s = rs[n]
    G = sum(1 for f in F if n in f['names'])
    if s['n']:
        oh = s['ownhalf']
        print(f"| {SHORT[n]} | {s['n']/G:.1f} | {pct(oh, s['n'])} | {pct(s['away'], s['n'])} | {pct(s['closer'], s['n'])} | {pct(s['recall'], s['n'])} | {pct(s['died10'], s['n'])} ({pct(s['oh_died'], oh)} / {pct(s['eh_died'], s['n']-oh)}) |")
print()
print('## Camp tanking (per team, group and 25-round window with >=200 camp damage)\n')
tk = defaultdict(lambda: defaultdict(list))
tanker = defaultdict(Counter)
for f in F:
    for t, ty, tot, share, name, nch in f['tank']:
        n = f['names'][t]
        tk[n]['share'].append(share)
        tk[n]['nch'].append(nch)
        tanker[n][name] += tot * share
print('| team | mean share of camp damage on the top tank | mean champions hit | top tanks (damage share) |')
print('|---|---|---|---|')
for n in TEAMS:
    s = tk[n]
    tot = sum(tanker[n].values())
    print(f"| {SHORT[n]} | {mean(s['share']):.2f} | {mean(s['nch']):.2f} | " + ', '.join(f'{k} {100*v/tot:.0f}%' for k, v in tanker[n].most_common(4)) + ' |')
