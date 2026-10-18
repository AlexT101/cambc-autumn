import pickle
from collections import Counter, defaultdict
from common import TOP, US, SHORT
F = pickle.load(open('features.pkl', 'rb'))
items = defaultdict(lambda: defaultdict(Counter))
first3 = defaultdict(lambda: defaultdict(Counter))
for f in F:
    T = f['team_of']
    seq = defaultdict(list)
    for x in f['shops']:
        if 'items' not in x:
            continue
        ty = f['types'][x['a']]
        n = f['names'][T[x['a']]]
        for k, v in x['items'].items():
            if v > 0 and 'Shard' in k:
                items[n][ty][k.replace(' Shard of ', ':')] += v
                seq[x['a']] += [k.replace(' Shard of ', ':')] * v
    for a, s in seq.items():
        first3[f['names'][T[a]]][f['types'][a]][' '.join(s[:3])] += 1
for n in ['Intercontinental Fish', 'Mite', 'procless', 'Univardisty of Shingtonwash', 'Sneaky Bush Campers', US]:
    print('###', SHORT[n])
    for ty in ('Stellar', 'Ren', 'Ryth', 'Varg', 'Cassi', 'Issac', 'Tavi'):
        c = items[n][ty]
        tot = sum(c.values())
        if tot < 30:
            continue
        print(f'- {ty}: ' + ', '.join(f'{k} {100*v/tot:.0f}%' for k, v in c.most_common(3)) + f' | first: {first3[n][ty].most_common(1)}')
