"""Our champion deaths to Fish r8 champions in live games: HP at the camp phase before the killing blow (end of round
D-1, then the phase's own camp hits), bag, and the camps that could have landed a blow at that phase.
py hoardhp.py EXT ROWS.json"""
import json, gzip, os, sys, collections, statistics as st
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
STR = {'Wolf': 20, 'Elk': 60, 'Golem': 120, 'Monolith': 200}
RNG = {'Wolf': 3, 'Elk': 4, 'Golem': 4, 'Monolith': 5}
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
ext, rf = sys.argv[1:3]; rows = json.load(open(rf)); idx = json.load(open(ext + '/index.json'))['games']
out = []
for g in idx:
    mid = os.path.basename(g['source'])[:-8]
    if mid not in rows: continue
    fish = 1 if rows[mid]['side'] == 'a' else 0
    try: meta, R, ev, mp = load(ext, g['dir'])
    except Exception: continue
    typ = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    camps = eval(mp['camps']) if isinstance(mp['camps'], str) else mp['camps']
    groups = eval(mp['groups']) if isinstance(mp['groups'], str) else mp['groups']
    ch = R['champions']; n = len(R['round'])
    # camp liveness and group awake state per round
    dead = set(); awake_g = set(); alive_at = {}; awake_at = {}
    evr = collections.defaultdict(list)
    for e in ev: evr[e['r']].append(e)
    win = meta['result'].get('winner') != fish
    for r in range(1, n + 1):
        for e in evr[r]:
            if e['k'] == 'camp_death': dead.add(e['camp'])
            elif e['k'] == 'group_respawn':
                for c in groups[e['g']]['camps']: dead.discard(c)
                awake_g.discard(e['g'])
            elif e['k'] == 'group_wake': awake_g.add(e['g'])
            elif e['k'] == 'group_sleep': awake_g.discard(e['g'])
            elif e['k'] == 'camp_attack': awake_g.add(e['g'])
        alive_at[r] = set(dead); awake_at[r] = set(awake_g)
    for e in ev:
        if e['k'] != 'death' or 'linked' in e: continue
        v = e['v']
        if team[v] == fish or team.get(e.get('by')) != fish or 'camp' in e: continue
        D = e['r']
        if D < 3: continue
        hpre = ch[v]['hp'][D - 2]; pos = (ch[v]['x'][D - 2], ch[v]['y'][D - 2])
        cdmg = sum(x['dmg'] for x in evr[D] if x['k'] == 'camp_attack' and x.get('tgt') == v)
        # camps alive at end of D-1 within their range of pos: (type, awake)
        near = []
        if None not in pos:
            for c in camps:
                if c['type'] not in STR or c['id'] in alive_at[D - 1]: continue
                if cheb((c['x'], c['y']), pos) <= RNG[c['type']]:
                    near.append((c['type'], c['group'] in awake_at[D - 1]))
        # victim's own events in round D before the kill
        acted = any(x.get('a') == v and x['t'] < e['t'] for x in evr[D] if x['t'] >= 0)
        out.append(dict(game=g['dir'], win=win, D=D, v=typ[v], by=typ[e['by']], gems=e['gems'], hpre=hpre,
                        hpk=e['hp'], cdmg=cdmg, maxhp=ch[v]['maxHp'][D - 2], near=near, acted=acted, gold=e.get('gold', 0)))
json.dump(out, open(os.path.expanduser('~/tmp-offload/camp-death-gem-denial/deaths.json'), 'w'))
def summ(lab, s):
    if not s: print(lab, 0); return
    h = sorted(x['hpre'] - x['cdmg'] for x in s)
    q = lambda p: h[min(len(h) - 1, int(p * len(h)))]
    print(f"{lab}: n={len(s)} gems={sum(x['gems'] for x in s)}  HP at camp phase (after its hits) p10/25/50/75 = {q(.1):.0f}/{q(.25):.0f}/{q(.5):.0f}/{q(.75):.0f}")
    for th in (20, 60, 120, 200, 320):
        k = [x for x in s if x['hpre'] - x['cdmg'] <= th]
        print(f"   <= {th}: {len(k)} ({len(k)/len(s):.0%}), gems {sum(x['gems'] for x in k)}")
    an = [x for x in s if any(a for _, a in x['near'])]; nn = [x for x in s if x['near']]
    print(f"   alive camp in range at D-1: {len(nn)}; awake: {len(an)}; acted in D before kill: {sum(x['acted'] for x in s)}")
    fe = []
    for x in s:
        hp = x['hpre'] - x['cdmg']
        tot = sum(STR[t] for t, a in x['near'])
        if x['near'] and tot >= hp: fe.append(x)
    print(f"   camp strength in range (awake or not) >= HP: {len(fe)}, gems {sum(x['gems'] for x in fe)}")
games = len({x['game'] for x in out})
print('games with a death to Fish:', games)
summ('hoard (>=100 gems)', [x for x in out if x['gems'] >= 100])
summ('Prism hoard', [x for x in out if x['gems'] >= 100 and x['v'] == 'Prism'])
summ('all deaths', out)
summ('bag >= 30', [x for x in out if x['gems'] >= 30])
