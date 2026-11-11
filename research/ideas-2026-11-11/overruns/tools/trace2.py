import sys,json,gzip,pickle
ab={'Cassi':'Ca','Issac':'Is','Vesper Vale':'Ve','Heart of Ruin':'Ho','Marcella':'Ma','Vendetta':'Vd','Willow':'Wi','Prism':'Pr','Stellar':'St','Ryth':'Ry','Ren':'Re','Tavi':'Ta','Varg':'Va'}
def trace(d,us,r0,r1):
    meta=json.load(open(d+'/meta.json')); R=json.load(gzip.open(d+'/rounds.json.gz'))
    ch=R['champions']; nm={c['id']:('u' if c['team']==us else 't')+ab[c['name']] for c in meta['champions']}
    byr={}
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['r']>r1: break
        if r0<=e['r'] and e['k'] in('attack','cast','death','recall_end','teleport_end'): byr.setdefault(e['r'],[]).append(e)
    for r in range(r0,r1+1):
        i=r-1
        if i>=len(R['round']): break
        print('r%d'%r,' '.join('%s %d,%d %d%s'%(nm[c['id']],c['x'][i],c['y'][i],c['hp'][i],'S' if c['stun'][i] else '') if c['alive'][i] else nm[c['id']]+' dead' for c in ch))
        s=[]
        for e in byr.get(r,[]):
            k=e['k']
            if k in('attack','cast'):
                x=nm[e['a']]+('!' if k=='cast' else '')
                if e.get('dmg'): s.append(x+'>'+','.join('%s-%d'%(nm[t],dm) for t,dm in e['dmg'])+('S' if e.get('stun') else ''))
                elif e.get('heal'): s.append(x+'>'+','.join('%s+%d'%(nm[t],dm) for t,dm in e['heal']))
                elif e.get('stun'): s.append(x+'>stun '+','.join(nm[t] for t in e['stun']))
                elif 'cdmg' in e or 'camp' in e: s.append(x+'>camp')
                elif e.get('ab') in('Dash',): s.append(x+'dash')
            elif k=='death': s.append('DEATH '+nm[e['v']]+(' bycamp' if 'camp' in e else ''))
        print('     ','  '.join(s))
G=pickle.load(open(sys.argv[1],'rb'))
mp,opp,side=sys.argv[2:5]
g=[g for g in G if g['map']==mp and g['opp']==opp and g['side']==side][0]
print(g['our_picks'],g['opp_picks'],g['gems'])
trace(g['dir'],g['us'],int(sys.argv[5]),int(sys.argv[6]))
