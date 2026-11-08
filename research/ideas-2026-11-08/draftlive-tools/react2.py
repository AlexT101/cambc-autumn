import pickle, collections, datetime
g = pickle.load(open('/home/ubuntu/tmp-offload/counter/games.pkl', 'rb'))
M = 'ee83f5e5-bcad-4923-86b4-b79ea6083d2e'
CH = ['Ryth','Vesp','Vend','C&I','Stel','Pris','Marc','Will','Ren','Varg','HoR','Tavi']
rows = [r for r in g['rows'] if r['day'] == '2026-11-07' and M in (r['A'], r['B'])]
print('Mite 11-07 time range', datetime.datetime.utcfromtimestamp(min(r['t'] for r in rows)), datetime.datetime.utcfromtimestamp(max(r['t'] for r in rows)))
by = collections.defaultdict(list)
for r in rows:
    mine, opp, s = (r['pa'], r['pb'], 'a') if r['A'] == M else (r['pb'], r['pa'], 'b')
    by[(r['map'], s)].append((r['t'], tuple(CH[x] for x in mine), tuple(CH[x] for x in opp), g['names'][r['B'] if r['A']==M else r['A']]))
for k, v in by.items():
    if len(set(x[1] for x in v)) > 1:
        for x in sorted(v): print(k, datetime.datetime.utcfromtimestamp(x[0]).strftime('%H:%M'), x[1], 'vs', x[2], x[3][:15])
        print()
