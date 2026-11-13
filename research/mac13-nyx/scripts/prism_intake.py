# Prism intake in mirror games: capture gems by holder type before r300, winner vs loser.
import json, gzip, glob, sys, collections
root = sys.argv[1]
names = json.load(open(f'{root}/enums.json'))['champions']
acc = collections.defaultdict(lambda: collections.Counter())
for m in glob.glob(f'{root}/*/meta.json'):
    j = json.load(open(m)); d = m[:-10]
    win = j['result']['winner']; typ = {c['id']: names[c['type']] for c in j['champions']}; team = {c['id']: c['team'] for c in j['champions']}
    if 'Prism' not in typ.values(): continue
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] == 'capture':
            for cid, gems, gold in e['shares']:
                side = 'W' if team[cid] == win else 'L'
                for cut in (150, 300, 600):
                    if e['r'] <= cut:
                        acc[(side, cut)][typ[cid] == 'Prism'] += gems
                        acc[(side, cut, 'n')][typ[cid] == 'Prism'] += 1
for side in 'WL':
    for cut in (150, 300, 600):
        c = acc[(side, cut)]; n = acc[(side, cut, 'n')]
        tot = c[True] + c[False]
        print(side, cut, 'prism gems', c[True], 'others', c[False], 'prism share %.2f' % (c[True] / max(1, tot)), 'captures prism/others', n[True], n[False])
