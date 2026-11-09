"""stop_game_ender episodes from gap-trace-sge's SGE lines (debug mirror), joined with the replay.
usage: sge.py ANA_DIR (extract of the debug batch; replays found through index sources)"""
import json, sys, os, re, zipfile, collections, statistics as st
from multiprocessing import Pool
import beh
ROOT = '/home/ubuntu/cambc-autumn/.claude/worktrees/ocean-removals/'
def run(job):
    d, src = job
    try:
        meta, rd, ev = beh.load(d); z = zipfile.ZipFile(src if os.path.isabs(src) else os.path.join(ROOT, src))
    except Exception as ex: return []
    cid = {(c['team'], c['type']): c['id'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    out = []
    for t, fn in ((0, 'team-a.stdout'), (1, 'team-b.stdout')):
        try: s = z.read(fn).decode(errors='replace')
        except KeyError: continue
        per = collections.defaultdict(list)
        for m in re.finditer(r'^SGE (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)$', s, re.M):
            r, ty, trib, gems, dist, locks, hp, ety = map(int, m.groups()); per[ty].append((r, trib, gems, dist, locks, hp, ety))
        for ty, L in per.items():
            me = cid.get((t, ty)); eps = []
            for x in L:
                if eps and x[0] - eps[-1][-1][0] <= 3: eps[-1].append(x)
                else: eps.append([x])
            for E in eps:
                r0, r1 = E[0][0], E[-1][0]; ender = cid.get((1 - t, E[0][6]))
                died = any(e['k'] == 'death' and e['v'] == me and r0 <= e['r'] <= r1 + 15 for e in ev)
                cut = any(e['k'] == 'tribute_cancel' and e['a'] == ender and e.get('cause') in ('lock', 'stun') and r0 <= e['r'] <= r1 + 1 for e in ev)
                kill = any(e['k'] == 'death' and e['v'] == ender and r0 <= e['r'] <= r1 + 15 and team.get(e.get('by')) == t for e in ev)
                landed = any(e['k'] == 'tribute_end' and e['a'] == ender and r0 <= e['r'] <= r1 + 60 for e in ev)
                out.append(dict(trib=E[0][1], anytrib=any(x[1] for x in E), gems=E[0][2], len=r1 - r0 + 1, died=died, cut=cut, kill=kill,
                                landed=landed, win=int(meta['result']['winner'] == t), locks=E[0][4], dist=E[0][3]))
    return out
if __name__ == '__main__':
    A = sys.argv[1]; idx = json.load(open(A + '/index.json'))['games']
    with Pool(32) as p: res = [x for r in p.map(run, [(A + '/' + g['dir'], g['source']) for g in idx], chunksize=4) for x in r]
    n = len(idx)
    for lab, X in (('all', res), ('channel seen at start', [x for x in res if x['trib']]), ('walking ender at start', [x for x in res if not x['trib']]),
                   ('walking, never a channel', [x for x in res if not x['anytrib']])):
        if not X: continue
        print(f"{lab:26} eps/g {len(X)/n:.2f} len~{st.mean(x['len'] for x in X):.1f} gems~{st.mean(x['gems'] for x in X):.0f} | we die<=15 {st.mean(x['died'] for x in X):.2f} "
              f"cut {st.mean(x['cut'] for x in X):.2f} kill ender {st.mean(x['kill'] for x in X):.2f} ender lands<=60 {st.mean(x['landed'] for x in X):.2f} we win {st.mean(x['win'] for x in X):.2f}")
