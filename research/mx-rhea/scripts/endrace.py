"""Endgame races: games where both teams held a winning bag (bag + score >= 1000) at once. For each side, its winning
tribute attempts (tribute_start whose gems + score reach 1000): count, how they ended (end, cancel cause, death), the
channel length, and how the race was decided. Usage: py endrace.py ANALYSIS_DIR"""
import gzip, json, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def game(d):
    try:
        meta = json.loads((d/'meta.json').read_text())
        R = json.load(gzip.open(d/'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    team = {c['id']: c['team'] for c in meta['champions']}
    name = {c['id']: c['name'] for c in meta['champions']}
    w = meta['result']['winner']
    # rounds each team holds a winning bag
    hold = [set(), set()]
    for c in R['champions']:
        t = c['team']
        for i, g in enumerate(c['gems']):
            if g is not None and c['alive'][i] and g + R['gems'][t][i] >= 1000: hold[t].add(i + 1)
    both = hold[0] & hold[1]
    if not both: return None
    b0 = min(both)
    att = [[], []]
    open_ = {}
    for e in ev:
        k = e['k']
        if k == 'tribute_start':
            t = team[e['a']]; sc = R['gems'][t][max(0, e['r'] - 2)]
            if e['gems'] + sc >= 1000: open_[e['a']] = dict(r=e['r'], dur=e['dur'], gems=e['gems'], who=name[e['a']])
        elif k in ('tribute_end', 'tribute_cancel') and e['a'] in open_:
            a = open_.pop(e['a']); a['end'] = 'end' if k == 'tribute_end' else e.get('cause', '?')
            a['left'] = e.get('left', 0); att[team[e['a']]].append(a)
        elif k == 'death' and e.get('v', e.get('a')) in open_:
            a = open_.pop(e.get('v', e.get('a'))); a['end'] = 'death'; att[team[e.get('v', e.get('a'))]].append(a)
    return dict(w=w, b0=b0, att=att, n=meta['result']['rounds'], holdstart=[min(h) if h else None for h in hold])


if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(game, dirs, chunksize=8):
            if o: rows.append(o)
    print(f'{len(rows)} games with both sides holding a winning bag at once')
    first_holder_won = sum(1 for r in rows if r['holdstart'][r['w']] <= r['holdstart'][1 - r['w']])
    print(f'first to hold won {first_holder_won}/{len(rows)}')
    for side in ('winner', 'loser'):
        A = [a for r in rows for a in r['att'][r['w'] if side == 'winner' else 1 - r['w']]]
        print(f'{side}: winning-tribute attempts {len(A)} ({len(A)/len(rows):.1f}/game); ends', Counter(a['end'] for a in A).most_common(),
              '; holder', Counter(a['who'] for a in A).most_common(4))
        ds = sorted(a['dur'] for a in A)
        if ds: print('   channel turns p25/50/75', [ds[int(q*(len(ds)-1))] for q in (.25, .5, .75)])
    # how the winner's successful channel compares
    fin = [next((a for a in r['att'][r['w']] if a['end'] == 'end'), None) for r in rows]
    print('winner completed a winning tribute in', sum(1 for f in fin if f), 'games; others won by round limit or score')
    lose_none = sum(1 for r in rows if not r['att'][1 - r['w']]); print('loser never started a winning tribute:', lose_none)
