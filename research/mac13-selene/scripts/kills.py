import json, gzip, sys, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    names={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    ch=R['champions']; idx={c['id']:i for i,c in enumerate(ch)}; rix={r:i for i,r in enumerate(R['round'])}
    out=[]
    for e in ev:
        if e['k']!='death': continue
        v=e['v']; by=e.get('by'); g=e.get('gems',0); r=e['r']; i=rix.get(r-1,0)
        vt=team[v]; c=ch[idx[v]]; x,y=c['x'][i],c['y'][i]
        kt=names.get(by,'camp') if by in names else 'camp'
        prism_near=None
        if x is not None:
            for cc in ch:
                if cc['team']!=vt and names[cc['id']]=='Prism' and cc['alive'][i] and cc['x'][i] is not None:
                    prism_near=max(abs(cc['x'][i]-x),abs(cc['y'][i]-y))
        out.append(dict(v=names[v],k=kt,g=g,pn=prism_near,kself=(by in names and team.get(by)==vt)))
    return out
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    rows=[];n=0
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r is not None: n+=1; rows+=r
    print('games',n,'deaths',len(rows),'per game',len(rows)/n)
    print('killer',Counter(r['k'] for r in rows).most_common())
    print('gems moved by killer type', sorted(((k,sum(r['g'] for r in rows if r['k']==k)/n) for k in set(r['k'] for r in rows)),key=lambda t:-t[1]))
    big=[r for r in rows if r['g']>=20 and r['k']!='camp']
    print('bag>=20 champion kills',len(big)/n,'gems',sum(r['g'] for r in big)/n)
    nonp=[r for r in big if r['k']!='Prism' and r['pn'] is not None]
    print('  by non-Prism with killer-side Prism within 4:',sum(1 for r in nonp if r['pn']<=4)/n,'gems',sum(r['g'] for r in nonp if r['pn']<=4)/n,' within 6:',sum(1 for r in nonp if r['pn']<=6)/n)
    print('camp kills gems lost',sum(r['g'] for r in rows if r['k']=='camp')/n, 'count',sum(1 for r in rows if r['k']=='camp')/n)
    print('victims',Counter(r['v'] for r in rows).most_common())
if __name__=='__main__': main()
