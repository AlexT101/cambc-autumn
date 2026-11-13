"""split.py AB_NAME MAPLIST : CAND win% on maps in MAPLIST vs the rest (results.json of each suite batch)."""
import sys, json, glob, os
name, lst = sys.argv[1], set(open(sys.argv[2]).read().split())
s = json.load(open(f'replays/ab/{name}/summary.json'))
tot = {True: [0, 0], False: [0, 0]}
for b in glob.glob(f'replays/batch-*-ab-{name}-*/results.json'):
    r = json.load(open(b))
    cand = 0  # bot index of CAND in 'bots'
    for m in r['matches']:
        if m.get('winner') is None: continue
        k = os.path.basename(m['map']) in lst
        # order maps sides to bots: order[0] is the bot playing side A; winner is side index? check
        tot[k][1] += 1
        tot[k][0] += (m['winner'] == 0)
for k, (w, n) in tot.items():
    print('in list' if k else 'others', n, round(100*w/max(1,n),1))
