# Compact trace of an engagement row: tr.py live|local IDX [before] [after]   (IDX into the selection printed by --list)
import sys,json,gzip,pickle
ab={'Cassi':'Ca','Issac':'Is','Vesper Vale':'Ve','Heart of Ruin':'Ho','Marcella':'Ma','Vendetta':'Vd','Willow':'Wi','Prism':'Pr','Stellar':'St','Ryth':'Ry','Ren':'Re','Tavi':'Ta','Varg':'Va'}
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def trace(row,before=4,after=8,rad=10):
    d=row['dir']; us=row['us']
    meta=json.load(open(d+'/meta.json')); R=json.load(gzip.open(d+'/rounds.json.gz'))
    ch=R['champions']; nm={c['id']:('u' if c['team']==us else 't')+ab[c['name']] for c in meta['champions']}
    r0=row['r0']; ra,rb=max(1,r0-before),r0+after
    byr={}
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['r']>rb: break
        if ra<=e['r'] and e['k'] in('attack','cast','death','capture'): byr.setdefault(e['r'],[]).append(e)
    t0=[c for c in ch if nm[c['id']][1:]==ab[row['tgt']] and (c['team']==us)!=row['by_us']][0]
    i0=max(r0-2,0); c0=(t0['x'][i0],t0['y'][i0])
    keep=[c for c in ch if any(c['alive'][j] and cheb((c['x'][j],c['y'][j]),c0)<=rad for j in range(ra-1,min(rb,len(R['round']))))]
    print('%s %s side %s vs %s r0=%d tgt %s by_us=%s nA %d nD %d died %s kA %d kD %d; origin=target pos %s'%(row['map'],'WIN' if row['win'] else 'LOSS',row['side'],row['opp'],r0,row['tgt'],row['by_us'],row['nA'],row['nD'],row['died'],row['kA'],row['kD'],c0))
    for r in range(ra,rb+1):
        i=r-1
        if i>=len(R['round']): break
        print('r%d%s'%(r,'*' if r==r0 else ' '),' '.join('%s(%+d,%+d)%d%s'%(nm[c['id']],c['x'][i]-c0[0],c['y'][i]-c0[1],c['hp'][i],'S' if c['stun'][i] else '') if c['alive'][i] else nm[c['id']]+' dead' for c in keep))
        s=[]
        for e in byr.get(r,[]):
            k=e['k']
            if k in('attack','cast'):
                if e['a'] not in [c['id'] for c in keep]: continue
                x=nm[e['a']]+('!' if k=='cast' else '')
                if e.get('dmg'): s.append(x+'>'+','.join('%s-%d'%(nm[t],dm) for t,dm in e['dmg'])+('S' if e.get('stun') else '')+('+camp' if 'cdmg' in e else ''))
                elif e.get('heal'): s.append(x+'>'+','.join('%s+%d'%(nm[t],dm) for t,dm in e['heal']))
                elif e.get('stun'): s.append(x+'>stun '+','.join(nm[t] for t in e['stun']))
                elif 'cdmg' in e or 'camp' in e: s.append(x+'>camp')
                elif e.get('ab')=='Dash': s.append(x+'dash')
                elif e.get('ab')=='Shield': s.append(x+'shield')
            elif k=='death': s.append('DEATH '+nm[e['v']]+(' bycamp' if 'camp' in e else ''))
            elif k=='capture': s.append('cap:'+','.join(nm[x[0]] for x in e['shares']))
        print('       ','  '.join(s))
if __name__=='__main__':
    sys.path.insert(0,'/home/ubuntu/cambc-autumn/research/ideas-2026-11-11/fishfight/tools')
    rows=pickle.load(open('/home/ubuntu/tmp-offload/fishfight/%s.pkl'%sys.argv[1],'rb'))['rows']
    opp,by_us=sys.argv[2],sys.argv[3]=='us'
    x=[r for r in rows if r['opp']==opp and r['by_us']==by_us and r['nA']>r['nD']]
    if sys.argv[4]=='--list':
        for k,r in enumerate(x): print(k,r['map'],r['side'],r['r0'],r['tgt'],'nA',r['nA'],'nD',r['nD'],'w4',sum(1 for b in r['B'] if b['d'][0] is not None and b['d'][0]<=4),'died',r['died'],r['die_off'],'k',r['kA'],r['kD'])
    else:
        for k in sys.argv[4].split(','): trace(x[int(k)],*(int(v) for v in sys.argv[5:])); print()
