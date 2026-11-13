"""Warning time before early first Prism deaths: rounds the victim was outnumbered within 8 before the first hit, and
where its allies were when that began.  py prism_warning.py ROWS.jsonl"""
import json, sys, statistics as st
from collections import Counter
rows = [json.loads(l) for l in open(sys.argv[1])]
W = []; 
for x in rows:
    if x['killer'] == 'camp' or not x['first_hit']: continue
    tr = {row['r']: row for row in x['trace']}; r0 = x['first_hit'][0]
    r = r0; start = None
    while r in tr and tr[r]['en8'] > tr[r]['al8']:
        start = r; r -= 1
    if start is None:
        W.append(dict(out=False)); continue
    s = tr[start]
    al16 = sum(1 for d in s['ald'] if d <= 16)
    W.append(dict(out=True, warn=r0 - start, ald=s['ald'][0] if s['ald'] else 99, al16=al16, al8=s['al8'], en8=s['en8'],
                  albr=Counter(s['albr']), home=s['home'], vbr=s['br'], en8_fh=tr.get(r0, s)['en8']))
n = len(W); O = [w for w in W if w['out']]
print('non-camp', n, 'outnumbered at first hit', len(O))
print('warning rounds (outnumbered before first hit) quartiles', st.quantiles([w['warn'] for w in O], n=4))
for k in (0, 1, 3, 5, 8):
    print(f' warning >= {k}', sum(w['warn'] >= k for w in O), f"{sum(w['warn'] >= k for w in O) / len(O) * 100:.0f}%")
print('nearest ally at outnumbered start quartiles', st.quantiles([w['ald'] for w in O], n=4))
print('allies within 16 at outnumbered start: mean', sum(w['al16'] for w in O) / len(O), 'within 8 mean', sum(w['al8'] for w in O) / len(O), 'enemies within 8 mean', sum(w['en8'] for w in O) / len(O))
print('allies within 16 >= enemies within 8 (could have been matched)', sum(w['al16'] + 1 >= w['en8'] for w in O), 'of', len(O))
c = Counter(); [c.update(w['albr']) for w in O]; tot = sum(c.values())
print('ally branches at outnumbered start', {k: f'{v / tot * 100:.0f}%' for k, v in c.most_common(8)})
print('victim branch at outnumbered start', {k: f'{v / len(O) * 100:.0f}%' for k, v in Counter(w['vbr'] for w in O).most_common(6)})
print('victim walk dist home at outnumbered start quartiles', st.quantiles([w['home'] for w in O], n=4))
