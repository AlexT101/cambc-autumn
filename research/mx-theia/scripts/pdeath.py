# Prism deaths: who dies first and the win rate after; gems carried at death; where; cause; killer; allies and
# enemies within 8; last tribute before death. Args: ANALYSIS_DIR [CANDNAME] (CANDNAME: split by bot, not W/L).
import json,gzip,sys,os,collections,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; CAND=sys.argv[2] if len(sys.argv)>2 else None
en=json.load(open(ROOT+'/enums.json'))['champions']
idx=json.load(open(ROOT+'/index.json'))
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    d=os.path.join(ROOT,d)
    try:
        meta=json.load(open(d+'/meta.json')); mp=json.load(open(os.path.join(d,meta['mapFile'])))
        R=json.load(gzip.open(d+'/rounds.json.gz')); ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    except Exception: return None
    CH=R['champions']; names={c['id']:c['name'] for c in meta['champions']}
    team_of={c['id']:c['team'] for c in meta['champions']}
    win=meta['result']['winner']; win=0 if win in (0,'A','a') else 1
    tnames=[t['name'] for t in meta['teams']]
    sp=mp['spawn']; cen=[((s['minX']+s['maxX'])/2,(s['minY']+s['maxY'])/2) for s in sp]
    prism={i for i,n in names.items() if n=='Prism'}
    rows=[]; last_trib={}
    for e in ev:
        if e['k']=='tribute_end': last_trib[e['a']]=e['r']
        if e['k']=='death' and e['v'] in prism:
            t=team_of[e['v']]; p=e['at']
            da=cheb(p,cen[t]); de=cheb(p,cen[1-t]); s=de/(da+de) if da+de else .5
            side='own' if s>0.6 else ('enemy' if s<0.4 else 'mid')
            by=e.get('by'); killer=names.get(by,'camp') if by is not None else 'camp'
            rows.append(dict(team=t,r=e['r'],gems=e.get('gems',0),gemsTo=e.get('gemsTo',0),side=side,cause=e.get('cause'),killer=killer,assists=len(e.get('assists') or []),since_trib=e['r']-last_trib.get(e['v'],0),won=(t==win)))
    return dict(win=win,rows=rows,names=tnames)
def main():
    dirs=[g['dir'] for g in idx['games']]
    with ProcessPoolExecutor(32) as ex: res=[x for x in ex.map(one,dirs,chunksize=8) if x]
    print('games',len(res))
    first=collections.Counter(); 
    for g in res:
        if g['rows']:
            f=min(g['rows'],key=lambda r:r['r']); first['first_dier_won' if f['won'] else 'first_dier_lost']+=1
            first['r<300' if f['r']<300 else ('r<600' if f['r']<600 else 'r>=600')]+=1
        else: first['no_prism_death']+=1
    print('first prism death:',dict(first))
    for lab,keep in (('WIN',True),('LOSE',False)):
        rr=[r for g in res for r in g['rows'] if r['won']==keep]
        if not rr: continue
        print(lab,'prism deaths',len(rr),'per game %.2f'%(len(rr)/len(res)))
        print('  gems carried mean %.1f median %d; gems to killer mean %.1f'%(statistics.mean(r['gems'] for r in rr),statistics.median(r['gems'] for r in rr),statistics.mean(r['gemsTo'] for r in rr)))
        print('  gems buckets',sorted(collections.Counter(min(r['gems']//25*25,200) for r in rr).items()))
        print('  side',collections.Counter(r['side'] for r in rr)); print('  killer',collections.Counter(r['killer'] for r in rr).most_common(8))
        print('  cause',collections.Counter(r['cause'] for r in rr).most_common(5)); print('  assists',sorted(collections.Counter(r['assists'] for r in rr).items()))
        print('  rounds since last tribute: median',statistics.median(r['since_trib'] for r in rr),'phase',collections.Counter(('<300' if r['r']<300 else '<600' if r['r']<600 else '600+') for r in rr))
if __name__=='__main__': main()
