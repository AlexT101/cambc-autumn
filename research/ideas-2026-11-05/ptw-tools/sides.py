"""Per-side totals (cand = games.jsonl's `us`) from meta.json champion stats. python3 sides.py GAMES.jsonl"""
import json, sys, collections
keys = ['kills', 'deaths', 'earnedGold', 'collectedGems', 'submittedGems', 'championDamageDone', 'championDamageTaken', 'monsterDamageDone']
tot = {True: collections.Counter(), False: collections.Counter()}; wins = collections.Counter(); n = 0
for l in open(sys.argv[1]):
    g = json.loads(l); m = json.load(open(g['dir'] + '/meta.json')); n += 1
    for c in m['champions']:
        for k in keys: tot[c['team'] == g['us']][k] += c['stats'][k]
    wins[m['result']['winner'] == g['us']] += 1
print(f"games {n}, cand wins {wins[True]} ({100*wins[True]/n:.1f}%)")
for k in keys: print(f"  {k:22} cand {tot[True][k]/n:10.1f}  ref {tot[False][k]/n:10.1f}  ratio {tot[True][k]/max(1,tot[False][k]):.3f}")
