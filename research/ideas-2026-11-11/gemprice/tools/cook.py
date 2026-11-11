"""How often the score-gap triggers (and cook_stand, the same cook on tributed plus carried gems) (comeback cook: enemy >= 400 and lead >= 150, off below 100; altar guard: enemy >= 600,
lead >= 200, off below 100) fire while our carried bags put us level or ahead in tributed + carried gems.
usage: python3 cook.py EXTDIR [MAPSUBSTR]"""
import gzip, json, os, sys, collections
sys.path.insert(0, os.path.dirname(__file__))
from mech import games
ext = sys.argv[1]; sub = sys.argv[2] if len(sys.argv) > 2 else ''
S = collections.defaultdict(collections.Counter)
for g, us, body in games(ext):
    if sub not in g['map']: continue
    d = ext + '/' + g['dir']
    meta = json.load(open(d + '/meta.json')); R = json.load(gzip.open(d + '/rounds.json.gz'))
    sc = R['gems']; n = len(R['round'])
    bag = [[0] * n, [0] * n]
    for c in R['champions']:
        for i, x in enumerate(c['gems']): bag[c['team']][i] += x
    win = meta['result']['winner'] == us
    key = (body, 'win' if win else 'loss')
    S[key]['games'] += 1
    for name, emin, gap, off, bags in (('cook', 400, 150, 100, 0), ('guard', 600, 200, 100, 0), ('cook_stand', 400, 150, 100, 1)):
        on = False; fired = False; rounds = false_rounds = 0
        for i in range(n):
            them = sc[1 - us][i] + bags * bag[1 - us][i]; mine = sc[us][i] + bags * bag[us][i]
            lead = them - mine
            on = lead >= off if on else (them >= emin and lead >= gap)
            if on:
                fired = True; rounds += 1
                if sc[us][i] + bag[us][i] >= sc[1 - us][i] + bag[1 - us][i]: false_rounds += 1
        S[key][name + '_games'] += fired; S[key][name + '_rounds'] += rounds; S[key][name + '_false'] += false_rounds
        S[key][name + '_false_games'] += false_rounds > 0
for k in sorted(S):
    a = S[k]; n = a['games']
    print(k, n, ' | '.join(f"{nm}: fires in {100*a[nm+'_games']/n:.0f}% of games, {a[nm+'_rounds']/n:.0f} rounds a game, "
                          f"{a[nm+'_false']/max(1,a[nm+'_rounds'])*100:.0f}% of them level or ahead counting bags, false in {100*a[nm+'_false_games']/n:.0f}% of games" for nm in ('cook', 'guard', 'cook_stand')))
