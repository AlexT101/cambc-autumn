"""Wards on the turn after losing sight of every enemy: toward where they were last seen?"""
import sys, os, collections
from mw import Game, pos, cheb
C = collections.Counter(); n = 0
for f in sys.argv[1:]:
    g = Game(f); prev = {}
    for t in g.turns:
        st = t['start']; me = st['me']; cid = me['id']
        if not me['alive']: prev.pop(cid, None); continue
        en = [pos(e) for e in st['enemies']]
        p = pos(me); pl = None; pw = None
        for a in t['actions']:
            if a['kind'] == 'Move' and pl is None: p = tuple(a['to'])
            if a['kind'] == 'Place ward' and pl is None: pl = tuple(a['to']); pw = p
        if not en and prev.get(cid) and pl:
            last = min(prev[cid], key=lambda q: cheb(q, pw))
            dd = cheb(pl, last) - cheb(pw, last)
            C[('toward' if dd < 0 else 'same' if dd == 0 else 'away', pl in g.bushes)] += 1
            # baseline: mean over legal tiles within 2
            L = [(pw[0] + dx, pw[1] + dy) for dx in range(-2, 3) for dy in range(-2, 3) if g.legal_ward((pw[0] + dx, pw[1] + dy))]
            C['base_toward'] += sum(cheb(q, last) < cheb(pw, last) for q in L) / len(L)
            C['n'] += 1
        prev[cid] = en
print(C, 'base toward share', C['base_toward'] / C['n'])
