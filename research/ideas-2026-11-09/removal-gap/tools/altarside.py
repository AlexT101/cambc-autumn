"""Where each team tributes and locks: altar side by walking steps from each spawn (ocean's our_side: ours <= theirs + 2).
For victim V = 1-T: gems tributed before 600 at altars on T's side; T's lock placements before 600 on T's side; victim
lock hits; V tributes at altars T has locked (after the lock)."""
import beh, json, sys, os, collections, statistics as st
from collections import deque
from multiprocessing import Pool
import lockcut_run as L
_mc = {}
def mapinfo(d, meta):
    root = os.path.dirname(d.rstrip('/')); h = meta['map']['hash']
    if h in _mc: return _mc[h]
    m = json.load(open(f'{root}/maps/{h}.json')); W, H = m['width'], m['height']
    block = set(map(tuple, m['walls'])) | set(map(tuple, m['holes'])) | set(map(tuple, m['altars']))
    def bfs(sp):
        dist = {}; q = deque()
        for x in range(sp['minX'], sp['maxX'] + 1):
            for y in range(sp['minY'], sp['maxY'] + 1): dist[(x, y)] = 0; q.append((x, y))
        while q:
            p = q.popleft()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    t = (p[0] + dx, p[1] + dy)
                    if 0 <= t[0] < W and 0 <= t[1] < H and t not in block and t not in dist: dist[t] = dist[p] + 1; q.append(t)
        return dist
    D = [bfs(m['spawn'][0]), bfs(m['spawn'][1])]
    side = {}
    for a in map(tuple, m['altars']):
        best = [min((D[t].get((a[0] + dx, a[1] + dy), 10**6) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)) for t in (0, 1)]
        side[a] = [best[0] <= best[1] + 2, best[1] <= best[0] + 2]  # on team t's side (ocean's rule)
    _mc[h] = (side, len(m['altars']))
    return _mc[h]
def run(j):
    k, d, T = j
    try:
        meta, rd, ev = beh.load(d); side, na = mapinfo(d, meta)
    except Exception as ex: return (k, None)
    team = {c['id']: c['team'] for c in meta['champions']}; V = 1 - T
    f = collections.Counter(); f['one_site'] = int(na <= 2)
    locked = {}  # altar -> T lock present
    for e in ev:
        r = e['r']; kk = e['k']
        if kk == 'lock_place':
            a = tuple(e['to'])
            if e['team'] == T: locked[a] = True
            if r < 600:
                f[f"lock_e_{'T' if e['team']==T else 'V'}"] += 1
                if side.get(a, [0, 0])[e['team']]: f[f"lock_e_own_{'T' if e['team']==T else 'V'}"] += 1
        elif kk == 'lock_destroyed':
            if e['team'] == T: locked[tuple(e['at'])] = False
        elif kk == 'tribute_end' and r < 600:
            a = tuple(starts.get(e['a'], {}).get('altar', (-1, -1)))
            who = 'T' if team[e['a']] == T else 'V'; g = e.get('gems', 0)
            f[f'g600_{who}'] += g
            other = 1 - team[e['a']]
            if side.get(a, [0, 0])[other]: f[f'g600_atopp_{who}'] += g
        elif kk == 'tribute_start':
            starts[e['a']] = e
            if team[e['a']] == V and r < 600 and locked.get(tuple(e['altar'])): f['V_start_at_Tlock'] += 1
        elif kk == 'attack' and e.get('lock') and r < 600:
            f[f"lockhit_e_{'T' if team.get(e['a'])==T else 'V'}"] += 1
    f['win'] = int(meta['result']['winner'] == T)
    return (k, f)
starts = {}
if __name__ == '__main__':
    jobs = []
    if '--live' in sys.argv: jobs += L.jl()
    for a in sys.argv[1:]:
        if a.startswith('--'): continue
        p, b = a.rsplit(':', 1); jobs += [(os.path.basename(p) + f'-T{b}', d, T) for _, d, T in L.jloc(p, int(b))]
    with Pool(32) as pool: res = pool.map(run, jobs, chunksize=8)
    G = collections.defaultdict(list)
    for k, f in res:
        if f: G[(k, f['one_site'])].append(f)
    keys = ['win', 'lock_e_T', 'lock_e_own_T', 'lock_e_V', 'lockhit_e_T', 'lockhit_e_V', 'g600_T', 'g600_V', 'g600_atopp_T', 'g600_atopp_V', 'V_start_at_Tlock']
    print('group'.ljust(26) + 'n'.rjust(6) + ''.join(x[-14:].rjust(15) for x in keys))
    for g in sorted(G):
        X = G[g]; print(f'{g[0][:20]}/{"1site" if g[1] else "multi"}'.ljust(26) + f'{len(X):6}' + ''.join(f'{st.mean(x[k] for x in X):15.2f}' for k in keys))
