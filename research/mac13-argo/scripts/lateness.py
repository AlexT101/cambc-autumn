"""Stun/lock cancels of 300+ bag channels in an A/B extract, by the stopping side's bot: count a game, median turns
left at the cancel and the share with <= 3 left; and the stopper's death within 15 rounds. py lateness.py EXTRACT_DIR"""
import gzip, json, sys, statistics as st
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text()); R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception: return None
    C = R['champions']; team = {c['id']: c['team'] for c in C}
    bot = {i: t['name'] for i, t in enumerate(meta['teams'])}
    out = []
    for e in ev:
        if e['k'] == 'tribute_cancel' and e.get('gems', 0) >= 300 and e.get('cause') in ('stun', 'lock'):
            stopper = bot[1 - team[e['a']]]
            out.append((stopper, e.get('left', -1), e['cause']))
    return (list(bot.values()), out)
if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p / 'meta.json').exists()]
    left = defaultdict(list); games = 0
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(one, dirs, chunksize=8):
            if not r: continue
            games += 1
            for s, l, c in r[1]: left[s].append(l)
    for s, v in left.items():
        print(f'{s}: {len(v)/games:.2f} stops of 300+ channels a game, turns left median {st.median(v)}, <=3 left {100*sum(x<=3 for x in v)/len(v):.0f}%, <=10 left {100*sum(x<=10 for x in v)/len(v):.0f}%')
