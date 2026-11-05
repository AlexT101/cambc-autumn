"""Conditional-logit camp-destination score: causal candidate features, frozen weights.

Fish picks the candidate with the highest weights . features; ties go to the lower group id.
"""
import math

from breadth import dist

FIGHTER_HP = {0: 1350, 1: 2400, 4: 20000, 5: 5000}
FIGHTER_STRENGTH = {0: 20, 1: 60, 4: 200, 5: 120}


def candidates(x):
    own = x['own_group'] if x['reason'] == 'payout' else None
    return [c for c in x['candidates'] if c['walk'] < 999 and c['id'] != own]


def base_features(x, c):
    types = c['types']
    fighters = [t for t in types if t in FIGHTER_HP]
    alive = c['state'] in (0, 1)
    wait = max(c['walk'], c['respawn'])
    tiles = [tuple(p) for p in c['tiles']]
    mine = min(dist(x['me_xy'], p) for p in tiles)
    closer = any(min(dist((a['x'], a['y']), p) for p in tiles) < mine for a in x['visible_allies'] if not a['home'])
    return dict(
        wait=wait / 10, logwait=math.log1p(wait),
        respawn_part=max(0, c['respawn'] - c['walk']) / 10,
        alive_fight=alive * sum(FIGHTER_HP[t] for t in fighters) / max(x['strength'], 1) / 100,
        alive_dps=alive * sum(FIGHTER_STRENGTH[t] for t in fighters) / 100,
        monolith=float(alive and 4 in types), golem=float(alive and 5 in types),
        clusters_only=float(not fighters),
        unknown=float(c['state'] == 0), empty=float(c['state'] == 2), respawning=float(c['state'] == 3),
        gold=c['gold'] / 100, gems=c['gems'] / 10,
        allies_near=c['allies'],
        ally_recent=float(c['ally_age'] is not None and c['ally_age'] <= 10),
        visited=float(c['visits'] > 0), route=float(c['route_count'] > 0),
        terr=max(0, c['territory']) / 10, terr_neg=max(0, -c['territory']) / 10,
        last=float(c['last_group']), ally_closer=float(closer))


def features(x, c):
    f = base_features(x, c)
    spawn = float(x['reason'] == 'spawn')
    return f | {'spawn*' + k: spawn * v for k, v in f.items()}


def scores(x, fit):
    w = fit['weights']
    return {c['id']: sum(w[k] * v for k, v in features(x, c).items()) for c in candidates(x)}


def predict(x, fit):
    s = scores(x, fit)
    return min(s, key=lambda k: (-s[k], k)) if s else None
