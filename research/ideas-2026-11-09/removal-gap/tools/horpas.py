"""Damage-weighted passive of HoR champion damage, and the share dealt below half health; by side."""
import beh, json, os, sys, collections
from multiprocessing import Pool
def hp(d,T):
    meta,rd,ev=beh.load(d)
    team={c['id']:c['team'] for c in meta['champions']}
    hor={c['id'] for c in meta['champions'] if c['name']=='Heart of Ruin'}
    if not hor: return {}
    ch={c['id']:c for c in rd['champions']}; n=len(rd['round'])
    acc=collections.Counter()
    for e in ev:
        if e['k'] in ('attack','cast') and e.get('a') in hor and e.get('dmg'):
            a=e['a']; i=max(0,min(n-1,e['r']-2)); c=ch[a]; fr=c['hp'][i]/max(1,c['maxHp'][i])
            dm=sum(x[1] for x in e['dmg'] if team.get(x[0])!=team[a])
            s='us' if team[a]==T else 'op'
            acc['w_'+s]+=dm; acc['p_'+s]+=dm*(1+0.5*(1-fr)); acc['lo_'+s]+=dm*(fr<0.5)
    # HoR deaths and kills
    for c in meta['champions']:
        if c['id'] in hor:
            s='us' if c['team']==T else 'op'; acc['deaths_'+s]+=c['stats']['deaths']; acc['kills_'+s]+=c['stats']['kills']; acc['n_'+s]+=1
    return acc
