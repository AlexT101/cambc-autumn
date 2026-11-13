"""Late (r>=300) contribution by our champion type in local runs: champion damage dealt, stuns landed on champions,
capture gold/gems shares, kills. python3 contrib.py EXT"""
import gzip, json, os, sys, collections
ext = sys.argv[1]
idx = json.load(open(ext + '/index.json'))['games']
A = collections.defaultdict(collections.Counter); G = collections.Counter()
for g in idx:
    us = 0 if g['source'].endswith('-12.repl26a') else 1
    d = ext + '/' + g['dir']; m = json.load(open(d + '/meta.json'))
    ch = {c['id']: c for c in m['champions']}
    ours = {c['id']: c['name'] for c in m['champions'] if c['team'] == us}
    if 'Cassi' not in ours.values(): continue
    G['games'] += 1
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['r'] < 300: continue
        a = e.get('a')
        if a in ours:
            if isinstance(e.get('dmg'), list):
                A[ours[a]]['champ_dmg'] += sum(v for t, v in e['dmg'] if t in ch and ch[t]['team'] != us)
            if e['k'] == 'cast' and e.get('ab') in ('CC', 'Stun') and e.get('tgt') in ch and ch[e['tgt']]['team'] != us:
                A[ours[a]]['stuns'] += 1
        if e['k'] == 'capture' and e.get('team') == us:
            for s in e.get('shares', []):
                if s[0] in ours: A[ours[s[0]]]['cap_gold'] += s[2] if len(s) > 2 else 0; A[ours[s[0]]]['cap_gems'] += s[1]
        if e['k'] == 'death' and 'linked' not in e and e.get('by') in ours and ch[e['v']]['team'] != us:
            A[ours[e['by']]]['kills'] += 1
n = G['games']
tot = collections.Counter()
for k, v in A.items(): tot.update(v)
print('C&I games', n)
for name in sorted(A, key=lambda k: -A[k]['champ_dmg']):
    v = A[name]
    print(f'{name:14s} ' + ' '.join(f'{f} {v[f]/n:8.1f} ({v[f]/max(tot[f],1)*100:4.1f}%)' for f in ('champ_dmg', 'stuns', 'kills', 'cap_gems', 'cap_gold')))
