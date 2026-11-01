import gzip, json, glob, os
from collections import defaultdict, Counter
ROOT='replays/v66/runs/batch'
def keys(ok_only=True):
    out=[]
    for f in sorted(glob.glob(ROOT+'/*/trace_validation.json')):
        v=json.load(open(f))
        if v.get('status')=='ok' and v.get('exact_vs_rec'): out.append((os.path.basename(os.path.dirname(f)),v))
    return out
def parse_line(l):
    p=l.rstrip('\n').split(' ')
    d={'tag':p[0]}
    for x in p[1:]:
        if '=' in x:
            k,v=x.split('=',1); d[k]=v
    return d
def xy(s):
    try: a,b=s.split(','); return (int(a),int(b))
    except Exception: return None
def load(key):
    """returns dict (r,c)-> {'TT':rec,'TB':[...],'TA':[...],'TE':[...],'TS':[...]}, plus TV by c"""
    T=defaultdict(lambda: defaultdict(list)); TV={}
    v=json.load(open(f'{ROOT}/{key}/trace_validation.json')); trust=v.get('ladder_trusted_through') or 0
    with gzip.open(f'{ROOT}/{key}/trace.stdout.gz','rt',errors='replace') as f:
        for l in f:
            tag=l[:2]
            if tag not in ('TT','TB','TA','TE','TS','TV'): continue
            d=parse_line(l)
            if d['tag']=='TV': TV[int(d['c'])]=d; continue
            if 'r' not in d or 'c' not in d: continue
            try: r=int(d['r']); c=int(d['c'])
            except: continue
            if r>trust: continue
            T[(r,c)][d['tag']].append(d)
    return T,TV
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
