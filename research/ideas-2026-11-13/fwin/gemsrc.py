"""Where each team's gems come from (capture shares vs kills), and where they go (tributed, lost to deaths), per game.
    py gemsrc.py EXT ROWS.json   (ROWS: match -> {fish})"""
import json, os, sys, collections
from multiprocessing import Pool
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
def game(job):
    ext, d, fish = job
    try: meta, R, ev, mp = load(ext, d)
    except Exception: return None
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    S = collections.Counter()
    for e in ev:
        if e['k'] == 'capture':
            lab = 'f' if e['team'] == fish else 'o'
            S[lab + '_capgems'] += sum(x[1] for x in e['shares'])
        elif e['k'] == 'death':
            vt = team[e['v']]; lab = 'f' if vt == fish else 'o'; g = e.get('gems', 0)
            S[lab + '_lost'] += g
            if e.get('by') is not None and 'camp' not in e and team.get(e['by']) == 1 - vt:
                S[('o' if lab == 'f' else 'f') + '_killgems'] += g
                if typ[e['by']] == 'Vesper Vale': S[('o' if lab == 'f' else 'f') + '_vkillgems'] += g
            else: S[lab + '_camplost'] += g
        elif e['k'] == 'tribute_end':
            S[('f' if team[e['a']] == fish else 'o') + '_trib'] += e['gems']
    w = meta['result'].get('winner')
    return dict(S, fish_win=w == fish, rounds=len(R['round']))
def main():
    ext, rows_f = sys.argv[1:3]
    team = sys.argv[3] if len(sys.argv) > 3 else None
    idx = json.load(open(ext + '/index.json'))['games']; rows = json.load(open(rows_f))
    jobs = [(ext, g['dir'], rows[os.path.basename(g['source'])[:-8]]['fish']) for g in idx if os.path.basename(g['source'])[:-8] in rows and (team is None or rows[os.path.basename(g['source'])[:-8]].get('opp') == team)]
    with Pool(8) as p: res = [x for x in p.map(game, jobs, chunksize=4) if x]
    for fw in (True, False):
        L = [x for x in res if x['fish_win'] == fw]; n = len(L)
        print('Fish wins' if fw else 'Fish loses', n)
        for k in ('f_capgems', 'f_killgems', 'f_vkillgems', 'f_lost', 'f_camplost', 'f_trib', 'o_capgems', 'o_killgems', 'o_lost', 'o_camplost', 'o_trib'):
            print(f'  {k:12s} {sum(x.get(k, 0) for x in L) / n:7.1f}')

if __name__ == '__main__': main()
