"""Fish's tributes: per game count, gems started and banked, channel length, cancels, and how often one of ours is
within 8 of the altar at the start, and our tribute-lock use. py ftrib.py EXT ROWS.json"""
import json, os, sys, collections, statistics as st
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
ext, rf = sys.argv[1:3]; rows = json.load(open(rf)); idx = json.load(open(ext + '/index.json'))['games']
N = 0; C = collections.Counter(); durs = []; gems = []; near = 0; big = collections.Counter()
for g in idx:
    mid = os.path.basename(g['source'])[:-8]
    if mid not in rows: continue
    fish = 1 if rows[mid]['side'] == 'a' else 0
    try: meta, R, ev, mp = load(ext, g['dir'])
    except Exception: continue
    N += 1; team = {c['id']: c['team'] for c in meta['champions']}; ch = {c['id']: c for c in R['champions']}
    rix = {r: i for i, r in enumerate(R['round'])}
    for e in ev:
        if e['k'] in ('tribute_start', 'tribute_end', 'tribute_cancel') and team.get(e.get('a')) == fish:
            C[e['k']] += 1
            if e['k'] == 'tribute_start':
                C['gems_started'] += e['gems']; durs.append(e['dur']); gems.append(e['gems'])
                i = rix.get(e['r'])
                if i is not None:
                    d = min((max(abs(c['x'][i] - e['altar'][0]), abs(c['y'][i] - e['altar'][1])) for c in R['champions'] if c['team'] != fish and c['alive'][i]), default=99)
                    if d <= 8: C['ours_within8'] += 1
                    if e['gems'] >= 100: big['n'] += 1; big['near'] += d <= 8
            if e['k'] == 'tribute_end': C['gems_banked'] += e.get('gems', 0)
        if e['k'] == 'lock_place' and team.get(e.get('a')) != fish: C['our_locks'] += 1
print(f'{N} games; a game:', {k: round(v / N, 2) for k, v in C.items()})
print(f'  channel turns median {st.median(durs)}, mean {st.mean(durs):.1f}; bag median {st.median(gems)}; 100+ bags {big["n"]/N:.2f} a game, ours within 8 at start {big["near"]/max(1,big["n"]):.2f}')
