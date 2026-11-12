"""Loader for feats.jsonl.gz (feat.py). FEATS env overrides the path."""
import os, json, gzip, collections
FEATS = os.environ.get('FEATS', os.path.expanduser('~/tmp-offload/battlecats/feats.jsonl.gz'))
US = 'stellar best girl'
TOP = {'stellar best girl': 'us', 'Intercontinental Fish': 'Fish', 'Mite': 'Mite'}
def oppclass(o): return TOP.get(o, 'other')
def load(filt=None):
    out = []
    for l in gzip.open(FEATS, 'rt'):
        g = json.loads(l)
        g['team'] = {c[0]: c[1] for c in g['champs']}
        g['name'] = {c[0]: c[2] for c in g['champs']}
        g['oc'] = oppclass(g['opp'])
        if filt is None or filt(g): out.append(g)
    return out
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
def spawn_c(g, t):
    s = g['spawn'][t]; return ((s['minX'] + s['maxX']) / 2, (s['minY'] + s['maxY']) / 2)
def gtype(types):
    s = set(types)
    for big in ('Monolith', 'Golem', 'Elk', 'Wolf'):
        if big in s: return big + ('+' if len(s) > 1 else '')
    if s == {'Gem cluster'}: return 'Gem cl'
    if s == {'Gold cluster'}: return 'Gold cl'
    return 'Clusters mix'
def pct(a, b): return f'{100 * a / b:.1f}%' if b else '-'
def mean(x): x = list(x); return sum(x) / len(x) if x else float('nan')
def med(x):
    x = sorted(x); return x[len(x) // 2] if x else float('nan')
