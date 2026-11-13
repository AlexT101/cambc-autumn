"""Per bot, while its opponent finishes (an opponent body holds a bag that, with the score, wins): its capture gems
and deaths a 100 rounds (games with 50+ such rounds, as defender.py), and the opponent's winning tributes started,
completed and stopped (by cause). py onestop_check.py EXTRACT_DIR"""
import gzip, json, sys, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text()); R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception: return None
    names = [t['name'] for t in meta['teams']]; C = R['champions']; n = len(R['round']); team = {c['id']: c['team'] for c in C}
    out = []
    for T in (0, 1):
        O = 1 - T; W = [c for c in C if c['team'] == O]
        t1 = next((i for i in range(n) if any(c['alive'][i] and R['gems'][O][i] + c['gems'][i] >= 1000 for c in W)), None)
        row = {'bot': names[T], 'won': meta['result']['winner'] == T}
        if t1 is not None:
            r1, rend = R['round'][t1], R['round'][-1]
            row['span'] = rend - r1
            row['cap'] = sum(s[1] for e in ev if e['k'] == 'capture' and e['team'] == T and r1 <= e['r'] < rend for s in e['shares'])
            row['dth'] = sum(1 for e in ev if e['k'] == 'death' and team.get(e['v']) == T and r1 <= e['r'] < rend)
        # The opponent's winning tributes: started with bag + its score at 1000+.
        score = {0: 0, 1: 0}; started = completed = 0; stopped = collections.Counter(); live = {}
        for e in ev:
            if e['k'] == 'tribute_start' and team.get(e['a']) == O and score[O] + e['gems'] >= 1000: started += 1; live[e['a']] = True
            elif e['k'] == 'tribute_end':
                if live.pop(e['a'], False): completed += 1
                score[team[e['a']]] = e.get('total', score[team[e['a']]] + e['gems'])
            elif e['k'] == 'tribute_cancel' and live.pop(e['a'], False): stopped[e.get('cause', '?')] += 1
        row.update(started=started, completed=completed, stopped=dict(stopped))
        out.append(row)
    return out
if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p / 'meta.json').exists()]
    with ProcessPoolExecutor(16) as ex: rows = [r for g in ex.map(one, dirs, chunksize=8) if g for r in g]
    for bot in sorted({r['bot'] for r in rows}):
        B = [r for r in rows if r['bot'] == bot]; F = [r for r in B if r.get('span', 0) >= 50]
        stopped = collections.Counter()
        for r in B: stopped.update(r['stopped'])
        print(f"{bot}: {len(B)} games, wins {sum(r['won'] for r in B)}")
        print(f"  opponent finishing 50+ rounds: {len(F)} games, {sum(r['span'] for r in F)} rounds")
        if F:
            print(f"  capture gems /100r: pooled {100*sum(r['cap'] for r in F)/sum(r['span'] for r in F):.1f}, median {st.median(100*r['cap']/r['span'] for r in F):.1f}")
            print(f"  deaths /100r: pooled {100*sum(r['dth'] for r in F)/sum(r['span'] for r in F):.2f}, median {st.median(100*r['dth']/r['span'] for r in F):.2f}")
        print(f"  opponent winning tributes: started {sum(r['started'] for r in B)}, completed {sum(r['completed'] for r in B)}, stopped {dict(stopped)}")
