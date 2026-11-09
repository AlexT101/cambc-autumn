"""Channel-start stop_game_ender episodes that go on against a non-channelling ender (after the cut), and deaths."""
import sge, json, sys, statistics as st, re, zipfile, os, collections
from multiprocessing import Pool
import beh
def run(job):
    d, src = job
    try: meta, rd, ev = beh.load(d); z = zipfile.ZipFile(os.path.join(sge.ROOT, src))
    except Exception: return []
    cid = {(c['team'], c['type']): c['id'] for c in meta['champions']}
    out = []
    for t, fn in ((0, 'team-a.stdout'), (1, 'team-b.stdout')):
        s = z.read(fn).decode(errors='replace'); per = collections.defaultdict(list)
        for m in re.finditer(r'^SGE (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)$', s, re.M):
            r, ty, trib, *_ = map(int, m.groups()); per[ty].append((r, trib))
        deaths = collections.defaultdict(list)
        for e in ev:
            if e['k'] == 'death': deaths[e['v']].append(e['r'])
        for ty, L in per.items():
            me = cid.get((t, ty)); eps = []
            for x in L:
                if eps and x[0] - eps[-1][-1][0] <= 3: eps[-1].append(x)
                else: eps.append([x])
            for E in eps:
                if not E[0][1]: continue
                after = [x for x in E if not x[1]]
                died = [r for r in deaths[me] if E[0][0] <= r <= E[-1][0] + 15]
                out.append((bool(after), bool(died), bool(died and after and died[0] >= after[0][0])))
    return out
if __name__ == '__main__':
    A = sys.argv[1]; idx = json.load(open(A + '/index.json'))['games']
    with Pool(32) as p: res = [x for r in p.map(run, [(A + '/' + g['dir'], g['source']) for g in idx], chunksize=4) for x in r]
    F = [x for x in res if x[0]]
    print('channel-start episodes', len(res), 'continuing against a non-channelling ender', round(len(F) / len(res), 2), 'of which died', round(st.mean(x[1] for x in F), 2),
          'died after the channel ended', round(st.mean(x[2] for x in F), 2), '| episodes ending with the channel: died', round(st.mean(x[1] for x in res if not x[0]), 2))
