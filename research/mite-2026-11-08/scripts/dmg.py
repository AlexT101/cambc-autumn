# One-turn damage reach, after FISH_MODEL section 2 (cambc-rules.yaml kits).
MELEE={'Ryth','Vendetta','Marcella','Ren','Varg','Heart of Ruin','Issac'}
RESET={'Vesper Vale':0,'Vendetta':0,'Marcella':0,'Tavi':0,'Willow':1,'Varg':0,'Issac':0,'Ryth':1}
DASH={'Vesper Vale':1,'Vendetta':1,'Ren':1,'Issac':1,'Heart of Ruin':1}
# (slot, mult, kind) damage spells
SPELL={'Ryth':[(0,1,'g')],'Prism':[(0,1.5,'u'),(1,1,'g')],'Stellar':[(0,2,'u'),(1,1.4,'g')],'Marcella':[(1,2,'u')],
       'Tavi':[(1,1.6,'u')],'Ren':[(0,1.1,'u')],'Cassi':[(0,2,'u')],'Heart of Ruin':[(1,1.5,'d')]}
def reach_damage(e,d,cd_ok=lambda e,s: e['cd'][s]==0):
    n=e['name']; S=e['strength']; F=e['focus']
    melee=n in MELEE; rng=1 if melee else 3
    walk=1 if melee else 0
    dash=2 if (n in DASH and cd_ok(e,DASH[n])) else 0
    reset= n in RESET and cd_ok(e,RESET[n])
    best=0
    if d<=rng+walk+dash: best=S*(2 if reset else 1)
    for s,m,k in SPELL.get(n,[]):
        if not cd_ok(e,s): continue
        if k=='u' and d<=4: best=max(best,m*F)
        if k=='g' and d<=5: best=max(best,m*F)
        if k=='d' and d<=3: best=max(best,m*F+S)   # HoR dash lands within 1 of a tile 2 away
    if n=='Heart of Ruin': best*=1+0.5*(1-e['hp']/e['maxHp'])
    return best
