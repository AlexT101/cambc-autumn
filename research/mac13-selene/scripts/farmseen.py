import json, gzip, sys, os, re, zipfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
AN='/home/ubuntu/wt/mac13-selene/replays/.analysis'
D_RE=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        mp=json.load(open(os.path.join(d,meta['mapFile'])))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
        z=zipfile.ZipFile(os.path.join('/home/ubuntu/wt/mac13-selene',meta['source']) if not os.path.isabs(meta['source']) else meta['source'])
    except Exception as ex: return None
    Dl={}
    for nm in z.namelist():
        if nm.endswith('.stdout'):
            for m in D_RE.finditer(z.read(nm)): Dl[(int(m.group(1)),int(m.group(2)))]=(m.group(3).decode(),int(m.group(4)))
    tiles=defaultdict(list)
    for c in mp['camps']: tiles[c['group']].append((c['x'],c['y']))
    hit=set(); hold=set()
    for e in ev:
        if e['k'] in('attack','cast') and e.get('camp') is not None: hit.add((e['a'],e['r']))
    res=Counter(); n=len(R['round'])
    for c in R['champions']:
        for i in range(1,n):
            if not c['alive'][i] or c['x'][i] is None: continue
            r=R['round'][i]; b=Dl.get((r,c['id']))
            if b is None or b[0]!='F': continue
            s='seen' if c['sees'][i] else 'quiet'
            g=b[1]; x,y=c['x'][i],c['y'][i]
            if g<0 or g not in tiles: res[(s,'nogroup')]+=1; continue
            dd=min(max(abs(x-a),abs(y-bb)) for a,bb in tiles[g])
            on=dd==0
            if (c['id'],r) in hit: k='hit'
            elif on: k='on-tile'
            elif dd<=3: k='near<=3'
            elif dd<=8: k='4-8'
            else: k='>8'
            res[(s,k)]+=1; res[(s,'all')]+=1
    return res
def main():
    idx=json.load(open(os.path.join(AN,'index.json')))
    dirs=[os.path.join(AN,g['dir']) for g in idx['games'] if 'mirdbg' in g['source']]
    tot=Counter(); ng=0
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs[:400],chunksize=4):
            if r: tot.update(r); ng+=1
    print('games',ng)
    for s in ('seen','quiet'):
        a=tot[(s,'all')]+tot[(s,'nogroup')]
        print(s,'F turns/game',round(a/ng,1),' '.join(f"{k} {tot[(s,k)]/a:.3f}" for k in ('hit','on-tile','near<=3','4-8','>8','nogroup')))
if __name__=='__main__': main()
