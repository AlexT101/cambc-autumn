"""Print a game's ward placements with a local map. python3 show.py CACHE [champion-name] [max]"""
import sys
from mw import Game, pos, cheb
g = Game(sys.argv[1]); who = sys.argv[2] if len(sys.argv) > 2 else None; mx = int(sys.argv[3]) if len(sys.argv) > 3 else 20
camps = {c[1]: c[0] for c in g.camps}
ward = {}; n = 0
print(g.d['map'].get('name', ''), g.W, g.H, 'side', g.side, [r['name'] for r in g.d['roster']])
for t in g.turns:
    me = t['start']['me']; cid = me['id']
    if not me['alive']: continue
    p = pos(me); pl = None; acts = []
    for a in t['actions']:
        if a['kind'] == 'Move' and pl is None: p = tuple(a['to'])
        if a['kind'] == 'Place ward': pl = tuple(a['to'])
        if a['kind'] not in ('Set priority',): acts.append(a['kind'][:6] + str(tuple(a['to'])))
    if pl is None or (who and g.name(cid) != who): continue
    n += 1
    if n > mx: break
    ow = ward.get(cid)
    en = {pos(e): e for e in t['start']['enemies']}; al = {pos(a) for a in t['start']['allies']}
    vis = g.fov(p); wv = g.fov(pl, 6)
    lc = [c for c in t['start']['camps']]
    alive_c = {(c['x'], c['y']) for c in lc}
    print(f"\nr{t['round']} {g.name(cid)} at {p} hp {me['hp']}/{me['maxHp']} gems {me['gems']} ward->{pl} old {ow} acts {acts}")
    for y in range(min(g.H - 1, p[1] + 8), max(-1, p[1] - 9), -1):
        row = ''
        for x in range(max(0, p[0] - 10), min(g.W, p[0] + 11)):
            q = (x, y)
            ch = '#' if q in g.walls else 'o' if q in g.holes else '"' if q in g.bushes else 'A' if q in g.altars else ('c' if q in alive_c else 'x') if q in camps else 's' if q in g.own_spawn else 'S' if q in g.foe_spawn else '.'
            if q == ow[0] if ow else False: ch = 'w'
            if q in al: ch = 'a'
            if q in en: ch = 'E'
            if q == pl: ch = 'W'
            if q == p: ch = '@'
            if ch in '."' and q not in vis: ch = ' ' if ch == '.' else ':'
            row += ch
        print('   ' + row)
    ward[cid] = (pl, t['round'])
