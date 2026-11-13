"""Tribute completion by starting bag (all tributes, mirror): starts, completion %, enemies within 8 at start.
py tribbins.py ANALYSIS_DIR"""
import gzip, json, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))
BINS = [1, 30, 60, 100, 200, 300, 500, 800, 5000]
def one(d):
    try:
        R = json.load(gzip.open(d / 'rounds.json.gz')); ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception: return []
    rid = {r: i for i, r in enumerate(R['round'])}; C = R['champions']; team = {c['id']: c['team'] for c in C}
    out, open_ = [], {}
    for e in ev:
        if e['k'] == 'tribute_start':
            i = rid.get(e['r'] - 1, 0); a = e['a']; c = next(c for c in C if c['id'] == a)
            p = tuple(e['at']) if e.get('at') else (c['x'][i], c['y'][i])
            en = sum(1 for q in C if q['team'] != team[a] and q['alive'][i] and q['x'][i] is not None and cheb((q['x'][i], q['y'][i]), p) <= 8)
            open_[a] = (e['gems'], en)
        elif e['k'] in ('tribute_end', 'tribute_cancel') and e.get('a') in open_:
            g, en = open_.pop(e['a']); out.append((g, en, e['k'] == 'tribute_end'))
    return out
if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p / 'meta.json').exists()]
    agg = defaultdict(lambda: [0, 0, 0, 0, 0])
    with ProcessPoolExecutor(24) as ex:
        for rows in ex.map(one, dirs, chunksize=8):
            for g, en, done in rows:
                b = max(k for k in range(len(BINS) - 1) if g >= BINS[k]); s = agg[b]
                s[0] += 1; s[1] += done; s[2] += en > 0; s[3] += done and en == 0; s[4] += en == 0
    for b in range(len(BINS) - 1):
        s = agg[b]; n = max(1, s[0])
        print(f'bag {BINS[b]}-{BINS[b+1]-1}: starts {s[0]}, done {100*s[1]/n:.0f}%, enemy within 8 at start {100*s[2]/n:.0f}%, done when none {100*s[3]/max(1,s[4]):.0f}%')
