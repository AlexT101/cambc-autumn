"""Loader for feats.jsonl.gz (feat.py). Groups: r7 = our live scrims against the r7 pin; ranked games by version
window: v0 (11-10 12:00 to 11-11 04:00, old encoding), v1 (11-11 04:00 to 23:09), v2 (from 23:09; r7 is in it)."""
import os, json, gzip, collections
FEATS = os.environ.get('FEATS', os.path.expanduser('~/tmp-offload/mitere/feats.jsonl.gz'))
def vgroup(g):
    if g['src'] == 'live': return 'r7'
    e = int(g['ver'][1:])
    return 'v0' if e == 0 else ('v1' if e <= 7 else 'v2')
def load(filt=None):
    out = []
    for l in gzip.open(FEATS, 'rt'):
        g = json.loads(l)
        g['team'] = {int(c[0]): c[1] for c in g['champs']}
        g['name'] = {int(c[0]): c[2] for c in g['champs']}
        g['vg'] = vgroup(g)
        for k in ('stats', 'pri'):
            g[k] = {int(a): b for a, b in g[k].items()}
        if filt is None or filt(g): out.append(g)
    return out
GROUPS = ('v0', 'v1', 'v2', 'r7')
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
def gtype(types):
    s = set(types or [])
    for big in ('Monolith', 'Golem', 'Elk', 'Wolf'):
        if big in s: return big + ('+' if len(s) > 1 else '')
    if s == {'Gem cluster'}: return 'Gem cl'
    if s == {'Gold cluster'}: return 'Gold cl'
    return 'Clusters mix'
def pct(a, b): return f'{100 * a / b:.1f}%' if b else '-'
def mean(x): x = list(x); return sum(x) / len(x) if x else float('nan')
def med(x):
    x = sorted(x); return x[len(x) // 2] if x else float('nan')
def q(x, p):
    x = sorted(x); return x[min(len(x) - 1, int(p * len(x)))] if x else float('nan')
