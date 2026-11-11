import json,gzip,glob,sys,collections,statistics as st
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def one(d):
    M=json.load(open(d+'/meta.json')); w=M['result']['winner']
    names={c['id']:c['name'] for c in M['champions']}
    team={c['id']:c['team'] for c in M['champions']}
    if not all(any(names[c]=='Prism' and team[c]==t for c in names) for t in (0,1)): return None
    out=collections.Counter()
    lastclear={}
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='group_clear': lastclear[e['g']]=e.get('by')
        if e['k']=='capture':
            t=e['team']; res='W' if t==w else 'L'
            by=lastclear.get(e['g']); byP = by is not None and names.get(by)=='Prism'
            for cid,gems,gold in e['shares']:
                out[res, 'clearP' if byP else 'clearO', 'toP' if names[cid]=='Prism' else 'toO']+=gems
    return out
def main():
    dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
    agg=collections.Counter(); n=0
    for o in ProcessPoolExecutor(32).map(one,dirs):
        if o: agg.update(o); n+=1
    for k,v in sorted(agg.items()): print(k, round(v/n,1))
if __name__=='__main__': main()
