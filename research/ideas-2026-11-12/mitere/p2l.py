"""Loader for pass2 rows. Field indices below."""
import gzip, json, os
P2 = os.path.expanduser('~/tmp-offload/mitere/p2.jsonl.gz')
F = 'r cid x0 y0 x1 y1 hp0 mhp g0 g1 prio dE nE5 nA5 dA0 dA1 dS0 dS1 dL0 dL1 hitC hitM trib recE tp cd0 cd1 eHp eG seen5 dmgPrev chan hitPrev near lockH dC0 dC1'.split()
I = {k: i for i, k in enumerate(F)}
def vgroup(g):
    if g['src'] == 'live': return 'r7'
    e = int(g['ver'][1:]); return 'v0' if e == 0 else ('v1' if e <= 7 else 'v2')
def load(filt=None):
    for l in gzip.open(P2, 'rt'):
        g = json.loads(l); g['vg'] = vgroup(g)
        g['team'] = {c[0]: c[1] for c in g['champs']}; g['name'] = {c[0]: c[2] for c in g['champs']}
        if filt is None or filt(g): yield g
