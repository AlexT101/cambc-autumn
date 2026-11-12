import math, os
BAL = float(os.environ.get("BAL", "0.5"))
def ctile(ts):
    mx = int(sum(p[0] for p in ts) / len(ts)); my = int(sum(p[1] for p in ts) / len(ts))
    return min(ts, key=lambda p: (p[0]-mx)**2 + (p[1]-my)**2)
def split_of(J, t):
    box = lambda s: [(x, y) for y in range(s['minY'], s['maxY']+1) for x in range(s['minX'], s['maxX']+1)]
    s = J['spawn'][t]; o = ctile(box(s)); e = ctile(box(J['spawn'][1-t]))
    dx, dy = e[0]-o[0], e[1]-o[1]; L = math.hypot(dx, dy)
    band = math.ceil((abs(dy)*(s['maxX']-s['minX']) + abs(dx)*(s['maxY']-s['minY']))/(2*L))
    def side(c):
        ox, oy, ex, ey = c[0]-o[0], c[1]-o[1], c[0]-e[0], c[1]-e[1]
        if ox*ox+oy*oy >= ex*ex+ey*ey: return 0
        off = (oy*dx - ox*dy)/L
        return 1 if off > band else -1 if off < -band else 0
    val = {1: 0, -1: 0}; gold = {1: 0, -1: 0}; gems = {1: 0, -1: 0}; sides = {}
    for q in J['groups']:
        if 'Monolith' in q.get('types', []): sides[q['id']] = 0; continue
        sd = side(ctile([tuple(p) for p in q['tiles']])); sides[q['id']] = sd
        if sd: val[sd] += q['gems'] + 0.3*q['gold']; gold[sd] += q['gold']; gems[sd] += q['gems']
    on = max(val.values()) > 0 and min(val.values()) >= BAL*max(val.values())
    v = (1 if gold[1] > gold[-1] else -1) if gold[1] != gold[-1] else (1 if gems[1] <= gems[-1] else -1)
    return on, {g: sd*v for g, sd in sides.items()}, o, (dx/L, dy/L)
