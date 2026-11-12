"""Lateral value split of our half per (map, side), over the extracted games' maps. Usage: maps.py EXT_DIR"""
import sys, json, glob, os, math, collections
seen = {}
for mp in glob.glob(f'{sys.argv[1]}/**/meta.json', recursive=True):
    g = os.path.dirname(mp); m = json.load(open(mp))
    mf = os.path.normpath(os.path.join(g, m['mapFile']))
    if mf in seen: continue
    J = json.load(open(mf)); sp = J['spawn']
    out = []
    for t in (0, 1):
        s = sp[t]; o = ((s['minX']+s['maxX'])/2, (s['minY']+s['maxY'])/2); s2 = sp[1-t]; e = ((s2['minX']+s2['maxX'])/2, (s2['minY']+s2['maxY'])/2)
        ux, uy = e[0]-o[0], e[1]-o[1]; L = math.hypot(ux, uy); nx, ny = -uy/L, ux/L
        band = (abs(nx)*(s['maxX']-s['minX']) + abs(ny)*(s['maxY']-s['minY']))/2 + 0.5
        side = {1: [0, 0, 0], -1: [0, 0, 0]}; cv = 0
        for q in J['groups']:
            if 'Monolith' in q.get('types', []): continue
            cx = sum(p[0] for p in q['tiles'])/len(q['tiles']); cy = sum(p[1] for p in q['tiles'])/len(q['tiles'])
            if math.hypot(cx-o[0], cy-o[1]) >= math.hypot(cx-e[0], cy-e[1]): continue
            la = (cx-o[0])*nx + (cy-o[1])*ny; v = q['gems'] + 0.3*q['gold']
            if abs(la) <= band: cv += v; continue
            k = 1 if la > 0 else -1; side[k][0] += v; side[k][1] += q['gold']; side[k][2] += q['gems']
        a, b = side[1][0], side[-1][0]
        out.append((min(a, b)/max(a, b, 1e-9), (a+b)/(a+b+cv) if a+b+cv else 0, side[1][1], side[-1][1], side[1][2], side[-1][2]))
    seen[mf] = (J['width'], J['height'], J['symmetry'], out)
r = [o[0] for v in seen.values() for o in v[3]]
print(len(seen), 'maps')
for lo, hi in ((0, .25), (.25, .5), (.5, .75), (.75, 1.01)):
    print(f'ratio {lo}-{hi}: {sum(lo <= x < hi for x in r)}')
lat = [o[1] for v in seen.values() for o in v[3]]
print('lateral share of value (mean):', sum(lat)/len(lat))
gd = [abs(o[2]-o[3])/max(1, o[2]+o[3]) for v in seen.values() for o in v[3]]
print('gold asymmetry |gL-gR|/(gL+gR) quartiles', sorted(gd)[len(gd)//4], sorted(gd)[len(gd)//2], sorted(gd)[3*len(gd)//4])
