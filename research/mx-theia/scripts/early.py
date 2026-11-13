# Capture gems by champion type by round T (default 150), W vs L, and deaths by then.
import json,gzip,sys,os,collections
ROOT=sys.argv[1]; T=int(sys.argv[2]) if len(sys.argv)>2 else 150
idx=json.load(open(ROOT+'/index.json')); dirs=sorted({g['dir'] for g in idx['games']})
C=collections.Counter(); n=0
for dn in dirs:
    d=os.path.join(ROOT,dn); meta=json.load(open(d+'/meta.json')); names={x['id']:x['name'] for x in meta['champions']}; team={x['id']:x['team'] for x in meta['champions']}
    w=meta['result']['winner']; n+=1
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['r']>T: break
        if e['k']=='capture':
            for s in e['shares']: C[('W' if team[s[0]]==w else 'L',names[s[0]],'gems')]+=s[1]; C[('W' if team[s[0]]==w else 'L',names[s[0]],'gold')]+=s[2]
        if e['k']=='death': C[('W' if team[e['v']]==w else 'L',names[e['v']],'deaths')]+=1
for nm in sorted({k[1] for k in C}):
    print('%-14s gems W %6.1f L %6.1f | gold W %6.1f L %6.1f | deaths W %.3f L %.3f'%(nm,C[('W',nm,'gems')]/n,C[('L',nm,'gems')]/n,C[('W',nm,'gold')]/n,C[('L',nm,'gold')]/n,C[('W',nm,'deaths')]/n,C[('L',nm,'deaths')]/n))
