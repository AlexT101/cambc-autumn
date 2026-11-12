"""Mechanism read of local runs (run_batched: bot 1 = ours, NNN-map-12 = ours team A) extracted by extract.mjs.
    py mech.py EXT [EXT...]
Per run, per game: the opponent's tribute starts of 100+ gems and their outcomes, our lock placements, the
opponent's tributed gems by r600, our deaths and gems lost, the opponent carrier's deaths with 100+ gems."""
import json, gzip, os, sys, collections, statistics as st

def run(ext):
    idx = json.load(open(f'{ext}/index.json'))['games']
    S = collections.Counter(); n = 0; won = 0
    for g in idx:
        src = os.path.basename(g['source'])
        ours = 0 if src.endswith('-12.repl26a') else 1; opp = 1 - ours
        d = f"{ext}/{g['dir']}"
        try:
            ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]; meta = json.load(open(d + '/meta.json'))
        except Exception: continue
        n += 1; won += meta['result']['winner'] == ours
        team = {c['id']: c['team'] for c in meta['champions']}
        open_start = {}
        for e in ev:
            k = e['k']
            if k == 'tribute_start' and team.get(e['a']) == opp:
                if e['gems'] >= 100: S['big_starts'] += 1; open_start[e['a']] = e
            elif k in ('tribute_end', 'tribute_cancel') and team.get(e.get('a')) == opp and e['a'] in open_start:
                del open_start[e['a']]
                S['big_' + ('end' if k == 'tribute_end' else e.get('cause', '?'))] += 1
            elif k == 'tribute_end' and team.get(e['a']) == opp and e['r'] <= 600: S['opp_gems600'] += e['gems']
            elif k == 'tribute_end' and team.get(e['a']) == ours and e['r'] <= 600: S['our_gems600'] += e['gems']
            elif k == 'lock_place' and team.get(e.get('a')) == ours: S['our_locks'] += 1
            elif k == 'death':
                t = team.get(e['v'])
                if t == ours: S['our_deaths'] += 1; S['our_gems_lost'] += e.get('gems', 0)
                elif t == opp:
                    S['opp_deaths'] += 1
                    if e.get('gems', 0) >= 100: S['opp_bag100_deaths'] += 1
                    if e['v'] in open_start: S['big_death'] += 1; del open_start[e['v']]
    return n, won, S

for ext in sys.argv[1:]:
    n, won, S = run(ext)
    print(f'{os.path.basename(ext.rstrip("/"))}: {n} games, win {100*won/n:.1f}%; a game: ' + ', '.join(f'{k} {v/n:.2f}' for k, v in sorted(S.items())))
