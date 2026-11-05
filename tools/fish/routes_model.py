"""Causal route and economic-departure surrogates; labels never enter predictors."""


def route(x, mode='ready', pars=(0,0,0,0)):
    cs=x['candidates']
    if mode=='visited':cs=[c for c in cs if c['visits']] or cs
    if mode=='known':cs=[c for c in cs if c['age'] is not None] or cs
    if mode=='home_side':cs=[c for c in cs if c['territory']<=0] or cs
    if mode=='repeat' and any(c['route_count'] for c in cs):
        return min(cs,key=lambda c:(-c['route_count'],max(c['walk'],c['respawn']),c['id']))['id']
    def score(c):
        value=max(c['walk'],c['respawn'])
        if mode=='fitted':
            new,territory,repeat,occupied=pars
            value += new*(not c['visits']) + territory*max(0,c['territory'])
            value -= repeat*bool(c['route_count'])
            value += occupied*(c['ally_age'] is not None and c['ally_age']<=10)
        return value,c['id']
    return min(cs,key=score)['id']


def features(kind,x):
    f=dict(health=x['hp']/x['maxhp'],gems=x['gems'],gold=x['gold'],
           altar=x['altar'],home=x['home_distance'],score=x['score'],
           allies=x['allies'],ally_gems=x['ally_gems'],enemies=x['enemies'],
           own_empty=int(x['own_empty']),capture_timer=x['capture_timer'])
    if kind=='incoming':
        f.update(rank_delta=x['self_rank']-x['best_rank'],best_timer=x['best_timer'],
                 self_timer=x['timer'] if x['channel']==1 else 0,
                 free=x['free'],group_capture=x['group_capture'],holders=len(x['holders']))
    if kind=='trip':
        f.update(spawn=int(x['reason']=='spawn'),
                 ready=min(max(c['walk'],c['respawn']) for c in x['candidates']),
                 prism=int(x['type']==6),marcella=int(x['type']==7))
    return f


def tree(node,x):
    while 'feature' in node:
        node=node['left' if x[node['feature']]<=node['threshold'] else 'right']
    return node['prediction']


def predict(kind,x,fit):
    f=features(kind,x)
    if kind=='trip':
        return 'home' if tree(fit['trip_home'],f) else 'tribute' if tree(fit['trip_tribute'],f) else 'farm'
    return tree(fit[kind],f)
