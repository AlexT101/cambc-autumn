import json,gzip,glob,os,collections,sys
S=os.environ.get('GEMZONE_DIR', 'replays/gemzone')  # holds ladder.jsonl (gemzone.mjs) and ana/ (extract.mjs --out)
R=os.path.join(os.path.dirname(os.path.abspath(__file__)),'../../../')
games={}
for l in open(R+'research/ladder-scrims-2026-11-06/data/games.jsonl'):
    x=json.loads(l)
    if x.get('result') in('win','loss'): games[x['replay']]=x
zones={}
for l in open(S+'/ladder.jsonl'):
    r=json.loads(l); zones[r['file'][5:-7]]=r['zones'][0]['bbox']
idx=json.load(open(S+'/ana/index.json'))['games']
agg=collections.defaultdict(lambda:collections.defaultdict(float))
for row in idx:
    src=row['source']; d=os.path.basename(os.path.dirname(src)); grp=d[:36]; base=d[37:]
    key=f'replays/ladder-scrims/{grp}/{base}.zip'
    if key not in games: continue
    gm=games[key]; us=0 if gm['side']=='a' else 1; m=gm['map']; bb=zones[m]
    adir=S+'/ana/'+row['dir']
    meta=json.load(open(adir+'/meta.json')); mp=json.load(open(os.path.join(adir,meta['mapFile'])))
    def inz(x,y,pad): return bb[0]-pad<=x<=bb[2]+pad and bb[1]-pad<=y<=bb[3]+pad
    zg={g['id'] for g in mp['groups'] if g['gems']>0 and any(inz(t[0],t[1],0) for t in g['tiles'])}
    allg={g['id']:g for g in mp['groups']}
    team={c['id']:c['team'] for c in meta['champions']}
    A=agg[m]; A['n']+=1; A['win']+=gm['result']=='win'
    for l in gzip.open(adir+'/events.jsonl.gz','rt'):
        e=json.loads(l); k=e['k']
        if k=='capture':
            gems=sum(s[1] for s in e['shares']); side='us' if e['team']==us else 'them'
            if e['g'] in zg: A['zone_gems_'+side]+=gems
            else: A['other_gems_'+side]+=gems
        elif k=='death' and e.get('by') is not None and e.get('at'):
            v=team[e['v']]; side='us' if v!=us else 'them'  # killer side
            if inz(e['at'][0],e['at'][1],4): A['zone_kills_'+side]+=1; A['zone_bag_taken_'+side]+=e.get('gems',0)
            else: A['far_kills_'+side]+=1
        elif k=='capture_reset' and e['g'] in zg and e.get('contested'):
            A['contested']+=1
    rd=json.load(gzip.open(adir+'/rounds.json.gz'))
    for c in rd['champions']:
        side='us' if c['team']==us else 'them'
        n=sum(1 for x,y,al in zip(c['x'],c['y'],c['alive']) if al and x is not None and inz(x,y,3))
        A['zone_presence_'+side]+=n/len(c['x'])
    A['trib_us']+=gm['our_gems']; A['trib_them']+=gm['opp_gems']
keys=['zone_gems','other_gems','zone_kills','zone_bag_taken','far_kills','zone_presence']
print(f"{'map':14s} {'n':>3s} {'win%':>5s} "+' '.join(f'{k:>18s}' for k in keys)+'  contested/g')
for m,A in sorted(agg.items()):
    n=A['n']; print(f"{m:14s} {n:3.0f} {100*A['win']/n:5.0f} "+' '.join(f"{A[k+'_us']/n:8.1f}/{A[k+'_them']/n:<8.1f}"[:18].rjust(18) for k in keys)+f"  {A['contested']/n:.1f}")
