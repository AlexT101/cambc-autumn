import sys; sys.path.insert(0,sys.argv[1])
from common import *
src=sys.argv[2]; r0=int(sys.argv[3]); r1=int(sys.argv[4]); who=sys.argv[5].split(',') if len(sys.argv)>5 else None
G=[g for g in games(distinct=False) if g['source']==src][0]; d=G['dir']; m=meta(d); R=rounds(d); mp=mapj(m)
NM={c['id']:c['name'][:6]+('*' if c['team']==G['us'] else '') for c in m['champions']}
F=[spawn_field(mp,0),spawn_field(mp,1)]
ev=[e for e in events(d) if r0<=e['r']<=r1]
print('map',G['map'],'us team',G['us'],'(* = ours)')
for rn in range(r0,r1+1):
    i=rn-1
    row=[]
    for c in R['champions']:
        if who and NM[c['id']].rstrip('*') not in who and NM[c['id']] not in who: continue
        if c['alive'][i]: row.append('%s(%d,%d)hp%.0f g%d sd%s cd%d/%d'%(NM[c['id']],c['x'][i],c['y'][i],c['hp'][i],c['gems'][i],F[c['team']].get((c['x'][i],c['y'][i])),c['cd0'][i],c['cd1'][i]))
        else: row.append('%s dead'%NM[c['id']])
    print('R%d END: '%rn+' | '.join(row))
    for e in ev:
        if e['r']!=rn or e['k'] in('recall_start','recall_cancel'): continue
        if e['k'] in('move',): print('    t%d %s move %s->%s'%(e['t'],NM[e['a']],e['f'],e['to']))
        elif e['k'] in('attack','cast'): print('    t%d %s %s %s %s->%s dmg=%s stun=%s moved=%s camp=%s'%(e['t'],NM[e['a']],e['k'],e.get('ab',''),e['f'],e['to'],[(NM.get(a,a),round(b)) for a,b in (e.get('dmg') or [])],e.get('stun'),e.get('moved'),e.get('camp')))
        elif e['k']=='camp_attack': print('    camp %s hits %s %s'%(e['camp'],NM.get(e.get('tgt')),e.get('dmg')))
        elif e['k']=='death': print('    DEATH %s by %s gems %s'%(NM[e['v']],NM.get(e.get('by'),'camp'),e['gems']))
        else: print('    t%s %s %s'%(e['t'],e['k'],{k:v for k,v in e.items() if k not in('s','r','t','k')}))
