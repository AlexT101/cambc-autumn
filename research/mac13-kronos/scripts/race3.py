import json,gzip,glob,zipfile,sys
n=0
for f in sorted(glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: continue
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}
    o=json.load(gzip.open(d+'/rounds.json.gz'))
    w=m['result']['winner']; T=len(o['round']); L=1-w; sc=o['gems']
    def bags(team,r): return sum(c['gems'][r] for c in o['champions'] if c['team']==team and c['alive'][r])
    R0=next((r for r in range(T) if sc[L][r]+bags(L,r)>=1000),None)
    if R0 is None or T-R0<60: continue
    pid=[c['id'] for c in o['champions'] if c['team']==L and names[c['id']]=='Prism']
    if not pid: continue
    pid=pid[0]; P=[c for c in o['champions'] if c['id']==pid][0]
    z=zipfile.ZipFile('/home/ubuntu/wt/mac13-kronos/'+m['source'])
    txt=z.read('team-%s.stdout'%('ab'[L])).decode('latin1')
    br={}
    for line in txt.splitlines():
        if line.startswith('D '):
            p=line.split()
            if int(p[2])==pid: br[int(p[1])]=p[3]
    print(m['source'].split('/')[-1], 'L team',L,'R0',R0,'T',T)
    for r in range(max(0,R0-5),min(T,R0+60),3):
        others=[(names[c['id']][:4],c['gems'][r]) for c in o['champions'] if c['team']==L and c['id']!=pid and c['alive'][r]]
        print(' r%d br=%s alive=%d gems=%d pos=(%d,%d) chan=%s score L=%d W=%d Wbags=%d others=%s'%(r,br.get(r,'?'),P['alive'][r],P['gems'][r],P['x'][r],P['y'][r],P['chan'][r],sc[L][r],sc[w][r],bags(w,r),others))
    n+=1
    if n>=3: break
