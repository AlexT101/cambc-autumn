"""Big bags in the open, both ways: per team, unit-rounds (alive, off own spawn, not channelling a tribute) carrying
B+ gems; the share seen by an enemy; the share with an enemy within 4; the share hit by an enemy champion that round;
and what became of each bag episode (tributed, killed by a champion, lost to a camp, game end).
    py carriers.py EXT ROWS.json [B] [TEAM]"""
import json, os, sys, collections
from multiprocessing import Pool
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
B = int(sys.argv[3]) if len(sys.argv) > 3 else 100
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
def game(job):
    ext, d, fish = job
    try: meta, R, ev, mp = load(ext, d)
    except Exception: return None
    ch = R['champions']; n = len(R['round']); team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    hit = set()
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('a') in team:
            for tgt in ([e['tgt']] if 'tgt' in e and e['tgt'] in team else []) + [x[0] for x in e.get('dmg', []) if x[0] in team]:
                if team[tgt] != team[e['a']]: hit.add((e['r'], tgt))
    S = collections.Counter(); ends = collections.Counter()
    for c in ch:
        lab = 'f' if c['team'] == fish else 'o'; sp = mp['spawn'][c['team']]
        inep = False
        for i in range(n):
            g = c['gems'][i] or 0
            if not c['alive'][i] or c['x'][i] is None or g < B:
                if inep:
                    inep = False
                    ends[(lab, 'killed' if not c['alive'][i] else 'banked/other')] += 1
                continue
            if not inep: inep = True; ends[(lab, 'episodes')] += 1
            p = (c['x'][i], c['y'][i])
            if sp['minX'] <= p[0] <= sp['maxX'] and sp['minY'] <= p[1] <= sp['maxY']: continue
            if c['chan'][i] == 2: continue
            S[(lab, 'rounds')] += 1
            if any(team.get(x) != c['team'] for x in (c['seenBy'][i] or [])): S[(lab, 'seen')] += 1
            near = [x for x in ch if x['team'] != c['team'] and x['alive'][i] and x['x'][i] is not None and cheb((x['x'][i], x['y'][i]), p) <= 4]
            if near: S[(lab, 'enemy<=4')] += 1
            if (i + 1, c['id']) in hit: S[(lab, 'hit')] += 1
        if inep: ends[(lab, 'game end')] += 1
    return meta['result'].get('winner') == fish, S, ends, n
def main():
    ext, rows_f = sys.argv[1:3]; team = sys.argv[4] if len(sys.argv) > 4 else None
    idx = json.load(open(ext + '/index.json'))['games']; rows = json.load(open(rows_f))
    jobs = [(ext, g['dir'], rows[m]['fish']) for g in idx for m in [os.path.basename(g['source'])[:-8]] if m in rows and (team is None or rows[m].get('opp') == team)]
    with Pool(12) as p: res = [x for x in p.map(game, jobs, chunksize=4) if x]
    for fw in (None, True, False):
        L = [x for x in res if fw is None or x[0] == fw]; n = len(L)
        S = sum((x[1] for x in L), collections.Counter()); E = sum((x[2] for x in L), collections.Counter())
        print({None: 'all', True: 'Fish wins', False: 'Fish loses'}[fw], n, f'games; bags of {B}+')
        for lab, who in (('f', 'Fish carrying'), ('o', 'opp carrying')):
            r = S[(lab, 'rounds')] or 1
            print(f"  {who}: {S[(lab, 'rounds')]/n:6.1f} rounds/game, seen {S[(lab, 'seen')]/r:.2f}, enemy<=4 {S[(lab, 'enemy<=4')]/r:.2f}, hit {S[(lab, 'hit')]/r:.3f}; episodes {E[(lab, 'episodes')]/n:.2f}/game: killed {E[(lab, 'killed')]/n:.2f}, banked/other {E[(lab, 'banked/other')]/n:.2f}, at game end {E[(lab, 'game end')]/n:.2f}")
if __name__ == '__main__': main()
