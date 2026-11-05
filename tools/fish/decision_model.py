"""Explicit causal features and executable, approximate decision predictors.

The fitted shallow trees are surrogate policies, not recovered Fish source code.
No label, future event, whole-turn action or omniscient state is accepted here.
"""
from breadth import RANGED
from holder_model import RANK


def features(kind, x):
    f = dict(hp_fraction=x['hp']/x['maxhp'], gold=x['gold'], gems=x['gems'],
             missing_hp=x['maxhp']-x['hp'], home_distance=x['home_distance'],
             enemies=x['enemies'], enemy_distance=x['enemy_distance'],
             timer=x['timer'] if x['channel']==1 else 0, type=x['type'])
    if kind == 'holder':
        hs=x['holders']; best=min(hs, key=lambda c:RANK.get(c['type'],99), default=None)
        f.update(exits=x['exits'], capture_timer=x['own_state'][3], holders=len(hs),
                 own_rank=RANK.get(x['type'],99), best_rank=RANK.get(best['type'],99) if best else 99,
                 best_hp=best['hp']/best['maxHp'] if best else 1,
                 best_timer=best['channelTimer'] if best and best['channelType']==1 else 0,
                 best_gems=best['gems'] if best else 0,
                 group_tiles=len(x['group']['tiles']),
                 next_ready=min((max(c['distance'], c['state'][4]-c['age'] if c['state'][1]==3 else 0)
                                 for c in x['alternatives']),default=999))
    elif kind == 'heal':
        f.update(missing=max(c['maxHp']-c['hp'] for c in x['allies']),
                 missing_fraction=max((c['maxHp']-c['hp'])/c['maxHp'] for c in x['allies']),
                 injured=sum(c['maxHp']>c['hp'] for c in x['allies']), reset_cd=x['cd'][1])
    elif kind == 'recall_final':
        f.update(on_capture=int(bool(x['own_state'] and x['own_state'][1]==2)),
                 capture_timer=x['own_state'][3] if x['own_state'] and x['own_state'][1]==2 else 99,
                 respawn_soon=min((max(0,c['state'][4]-c['age']) for c in x['groups'] if c['state'][1]==3),default=999))
    elif kind in ('enemy_attack','damage_spell'):
        ts=x['targets']
        f.update(target_hp=min(c['hp'] for c in ts),
                 target_health_ratio=min(c['hp'] for c in ts)/max(x['strength'],1),
                 target_focus_ratio=min(c['hp'] for c in ts)/max(x['focus'],1),
                 target_enemies=sum('maxHp' in c for c in ts),
                 # Coordinates of self are intentionally not required by these trees.
                 targets=len(ts), cd0=x['cd'][0], cd1=x['cd'][1])
    return f


def lower_holder(x):
    return (x['holders'] and x['type'] in RANK and all(c['type'] in RANK for c in x['holders'])
            and any(RANK[c['type']] < RANK[x['type']] for c in x['holders']))


def predict_tree(tree, f):
    while 'feature' in tree:
        tree=tree['left' if f[tree['feature']] <= tree['threshold'] else 'right']
    return tree['prediction']


def destination(x, parameters):
    gem, dps, ally, bonus = parameters
    def score(c):
        fighting = 0 if c['state']==2 else c['hp'] / (dps * (1 + ally*c['allies']))
        reward = c['gold'] + gem*c['gems']
        return (reward / (4 + max(c['walk'],c['respawn']) + fighting) + bonus*c['allies'], -c['id'])
    return max(x['candidates'],key=score)['id']


def predict(kind, x, fitted):
    if kind == 'melee_attack':
        return True if x['type'] not in RANGED else None
    if kind == 'heal_any_injury':
        return any(c['hp'] < c['maxHp'] for c in x['allies'])
    if kind == 'holder_wait':
        if not lower_holder(x) or x['channel'] != 1 or not 1 <= x['timer'] <= 3:
            return None
        best=min(x['holders'], key=lambda c:RANK[c['type']])
        return False if best['channelType']==1 and 1 <= best['channelTimer'] <= 3 else None
    if kind == 'recall_capture':
        return False if x['own_state'] and x['own_state'][1]==2 and x['hp']/x['maxhp'] > 0.4 else None
    if kind == 'recall_lowhp':
        return True if not (x['own_state'] and x['own_state'][1]==2) and x['hp']/x['maxhp'] <= 0.4 else None
    if kind == 'holder':
        return predict_tree(fitted['holder'],features(kind,x)) if lower_holder(x) else None
    if kind == 'destination':
        return destination(x,fitted['destination'])
    if kind == 'destination_ready':
        return min(x['candidates'],key=lambda c:(max(c['walk'],c['respawn']),c['id']))['id']
    if kind == 'enemy_attack' and x['type'] not in RANGED:
        return None
    return predict_tree(fitted[kind],features(kind,x))
