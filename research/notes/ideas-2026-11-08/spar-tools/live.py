"""Live scrim cells against Fish and Mite: {(version, map, side, opp): win} for the era a set is stable in.
era 'r2': v86-v89 with Fish (deterministic across refsets) and r2 Mite (v86's r1 Mite games dropped).
era 'all': v78-v89, every refset (Mite changed at r2, so older Mite cells are a different bot)."""
import json, collections
R = '/home/ubuntu/cambc-autumn/'
OPP = {'Intercontinental Fish': 'F', 'Mite': 'M'}
VER_BOT = {86: 'oc-base23', 87: 'oc-base25', 88: 'oc-base26', 89: 'oc-base27'}

def games():
    for l in open(R + 'research/notes/ladder-scrims-2026-11-06/data/games.jsonl'):
        g = json.loads(l)
        g['map'] = g['map'].replace('_', '-')  # live names use _, maps/ files -
        if g.get('status') == 'finished' and g['opp_name'] in OPP and g['result'] in ('win', 'loss'): yield g

def cells(era='r2', vmin=86, vmax=89):
    c = collections.defaultdict(list)
    for g in games():
        v, o = g['version'], OPP[g['opp_name']]
        if era == 'r2':
            if not (vmin <= v <= vmax): continue
            if o == 'M' and g['refset'] != 'r2': continue
        elif not (78 <= v <= vmax): continue
        c[(v, g['map'], g['side'], o)].append(g['result'] == 'win')
    return {k: sum(x) / len(x) for k, x in c.items()}

def per_map(c, opp=None, versions=None):
    d = collections.defaultdict(list)
    for (v, m, s, o), w in c.items():
        if (opp is None or o == opp) and (versions is None or v in versions): d[m].append(w)
    return {m: sum(x) / len(x) for m, x in d.items()}

def drafts():
    """(map, our side, opp) -> (opp picks in pick order, our picks), stable since v86 (r2 Mite)."""
    out = {}
    for g in games():
        if g['version'] < 86 or (OPP[g['opp_name']] == 'M' and g['refset'] != 'r2'): continue
        k = (g['map'], g['side'], OPP[g['opp_name']]); v = (tuple(g['opp_picks']), tuple(g['our_picks']))
        assert out.setdefault(k, v) == v, k
    return out
