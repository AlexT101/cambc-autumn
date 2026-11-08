import json,gzip,os,collections,sys
S=os.environ.get('GEMZONE_DIR', 'replays/gemzone')  # holds ladder.jsonl (gemzone.mjs) and ana/ (extract.mjs --out)
R=os.path.join(os.path.dirname(os.path.abspath(__file__)),'../../../')
MAP=sys.argv[1]
games={}
for l in open(R+'research/ladder-scrims-2026-11-06/data/games.jsonl'):
    x=json.loads(l)
    if x.get('result') in('win','loss'): games[x['replay']]=x
zones={json.loads(l)['file'][5:-7]:json.loads(l)['zones'][0]['bbox'] for l in open(S+'/ladder.jsonl')}
bb=zones[MAP]
idx=json.load(open(S+'/ana/index.json'))['games']
seen=set()
for row in idx:
    src=row['source']; d=os.path.basename(os.path.dirname(src)); key=f'replays/ladder-scrims/{d[:36]}/{d[37:]}.zip'
    if key not in games or games[key]['map']!=MAP or row['dir'] in seen: continue
    seen.add(row['dir'])
    gm=games[key]; us=0 if gm['side']=='a' else 1; adir=S+'/ana/'+row['dir']
    meta=json.load(open(adir+'/meta.json'))
    team={c['id']:c['team'] for c in meta['champions']}
    caps=[]; deaths=[]
    def zd(p): return max(bb[0]-p[0],p[0]-bb[2],bb[1]-p[1],p[1]-bb[3],0)
    for l in gzip.open(adir+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='capture' and sum(s[1] for s in e['shares'])>0: caps.append(('U' if e['team']==us else 'T')+str(e['r']))
        if e['k']=='death' and e.get('at'): deaths.append(('u' if team[e['v']]==us else 't')+f"{e['r']}@{zd(e['at'])}"+('c' if e.get('camp') is not None else ''))
    print(f"{gm['result']:4s} vs {gm['opp_name'][:6]} {gm['rounds']:4d}r {gm['our_gems']:.0f}-{gm['opp_gems']:.0f} us={','.join(p[:4] for p in gm['our_picks'])} them={','.join(p[:4] for p in gm['opp_picks'])}")
    print('   caps:',' '.join(caps[:14]))
    print('   deaths(r@zonedist):',' '.join(deaths[:18]))
