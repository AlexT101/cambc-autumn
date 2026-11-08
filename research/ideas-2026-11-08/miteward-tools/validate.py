"""Check the Python vision: every enemy the actor sees at a turn start lies in its own sight or its current ward's."""
import sys, collections
from mw import Game, pos, cheb
C = collections.Counter()
for f in sys.argv[1:]:
    g = Game(f); ward = {}
    for t in g.turns:
        me = t['start']['me']
        if me['alive']:
            own = g.fov(pos(me)); w = ward.get(me['id']); wv = g.fov(w, 6) if w else frozenset()
            for e in t['start']['enemies']:
                p = pos(e)
                C['own' if p in own else 'ward' if p in wv else 'neither'] += 1
                if p not in own and p not in wv and C['neither'] < 5: print(f, t['round'], me['id'], pos(me), w, p)
        for a in t['actions']:
            if a['kind'] == 'Place ward': ward[me['id']] = tuple(a['to'])
print(C)
