import json,gzip,glob,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def one(d):
    M=json.load(open(d+'/meta.json')); team={c['id']:c['team'] for c in M['champions']}
    out=collections.Counter(); clr={}; first={}
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='group_clear': clr[e['g']]=(team.get(e.get('by')),e['r'])
        if e['k']=='capture_hold': first.setdefault(e['g'],(e['team'],e['r']))
        if e['k']=='capture':
            ct,cr=clr.get(e['g'],(None,0)); gems=sum(s[1] for s in e['shares'])
            out['caps']+=1; out['gems']+=gems
            if ct is not None and ct!=e['team']: out['stolen']+=1; out['stolen_gems']+=gems
            out['delay',min((e['r']-cr-6)//3*3,30)]+=1
            first.pop(e['g'],None)
    return out
def main():
    agg=collections.Counter(); n=0
    for o in ProcessPoolExecutor(32).map(one,[x[:-10] for x in glob.glob(A+'/*/meta.json')]): agg.update(o); n+=1
    print('per game:',{k:round(v/n,2) for k,v in agg.items() if not isinstance(k,tuple)})
    print('capture delay after clear (rounds beyond 6):',sorted((k[1],v) for k,v in agg.items() if isinstance(k,tuple)))
if __name__=='__main__': main()
