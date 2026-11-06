"""flipsum.py A B part: per flipped game, the first diverging event and a lock/channel summary for each version."""
import gzip, json, sys
from pathlib import Path
ROOT = Path('/home/ubuntu/cambc-autumn')
G = Path(__import__('os').environ.get('GATE_DIR', '/tmp/gate'))  # scratch: raw/, analysis/, mapclass.json
a, b, part = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
rows = json.load(open(G / f'flips-{a}-{b}-{part}.json'))
idx = json.load(open(G / 'analysis/index.json'))['games']
by_src = {str((ROOT / g['source']).resolve()): g['dir'] for g in idx}
cls = json.load(open(G / 'mapclass.json'))
def load(v, k):
    f = str((G / 'raw' / f'v{v}' / k[0] / f'{k[1]}-{k[2]}' / f'{k[1]}-{k[2]}.repl26a').resolve())
    d = G / 'analysis' / by_src[f]
    meta = json.load(open(d / 'meta.json'))
    ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    return meta, ev
pairs = {}
for r in rows: pairs.setdefault(tuple(r['key']), {})[r['v']] = r
tot = {}
for k, p in pairs.items():
    T = 0 if k[2] == 'a' else 1
    ma, ea = load(a, k); mb, eb = load(b, k)
    name = {c['id']: c['name'][:5] for c in mb['champions']}
    team = {c['id']: c['team'] for c in mb['champions']}
    strip = lambda e: {x: y for x, y in e.items() if x != 's'}
    i = next((i for i, (x, y) in enumerate(zip(ea, eb)) if strip(x) != strip(y)), None)
    if i is None: div = 'no divergence'
    else:
        x, y = ea[i], eb[i]
        who = y.get('a', y.get('v'))
        side = 'us' if who is not None and team.get(who) == T else ('op' if who is not None else '-')
        div = f"r{y['r']} {side} {name.get(who, '')}: v{a} {x['k']} {x.get('to', x.get('at', ''))} / v{b} {y['k']} {y.get('to', y.get('at', ''))}"
    won = p[b]['res'] == 'W'
    def lk(r):
        cuts = r['lock_cuts']
        timed = [c for c in cuts if c[3] <= 2]
        return f"cuts {len(cuts)} ({sum(c[2] for c in cuts)}g; timed<=2 left {len(timed)}: {[(c[0], c[1], c[2], c[4]) for c in timed]})"
    print(f"{'+' if won else '-'} {k[0]} {k[1]}-{k[2]} [{cls[k[1]]}] v{a} {p[a]['res']} {p[a]['gems']} | v{b} {p[b]['res']} {p[b]['gems']}")
    print(f"    diverge: {div}")
    for v in (a, b):
        r = p[v]; o = r['o']
        print(f"    v{v}: {lk(r)}; locks placed/broken us {o.get('lk_us',0)}/{o.get('lkx_us',0)} op {o.get('lk_op',0)}/{o.get('lkx_op',0)}; "
              f"deaths {o.get('d_us',0)}/{o.get('d_op',0)}; op big landed {r['big_done']}")
