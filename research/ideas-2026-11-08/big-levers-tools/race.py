# Race losses: our owned/tributed when they finish; games where our owned crossed 1000 (or 900) before their finish.
import pickle,os,numpy as np,collections
F=pickle.load(open(os.path.expanduser('~/tmp-offload/bigl/feats.pkl'),'rb'))
L=[r for r in F if not r['win'] and r['rounds']<2000]; W=[r for r in F if r['win'] and r['rounds']<2000]
print('race losses',len(L),'race wins',len(W))
def first(a,th):
    i=np.where(a>=th)[0]; return int(i[0])+1 if len(i) else None
for th in (1000,950,900,850):
    c=0; lead=[]
    for r in L:
        f=first(r['own_me'],th)
        if f is not None and f<r['rounds']: c+=1; lead.append(r['rounds']-f)
    print(f'own_me >= {th} before they finished: {c} ({100*c/len(L):.1f}% of race losses), rounds before their finish median {np.median(lead) if lead else 0}')
# owned peak lead in losses: max(own_me-own_op)
pk=np.array([max(r['own_me']-r['own_op']) for r in L]); print('race losses: peak owned lead pct',np.percentile(pk,[25,50,75,90]))
# their trib at our peak owned lead round
# the final 150 rounds of race losses: our trib rate vs theirs, our carried
for r in L[:0]: pass
fin=[]
for r in L:
    n=r['rounds']; a=max(0,n-150)
    fin.append((r['trib_me'][-1]-r['trib_me'][a], r['trib_op'][-1]-r['trib_op'][a], r['own_me'][-1]-r['trib_me'][-1], r['own_me'][a]-r['trib_me'][a], r['own_op'][a]-r['trib_op'][a], r['trib_op'][a]))
fin=np.array(fin); print('last 150 rounds of race losses: tributed me',fin[:,0].mean().round(),'op',fin[:,1].mean().round(),'| our carry at start',fin[:,3].mean().round(),'at end',fin[:,2].mean().round(),'| their carry at start',fin[:,4].mean().round(), '| their trib at start', fin[:,5].mean().round())
# close race losses: our owned within 100 of 1000 at the end
close=[r for r in L if r['own_me'][-1]>=900]; print('close race losses (own_me>=900 at end):',len(close), f'{100*len(close)/len(L):.1f}%', 'mean our trib',np.mean([r['trib_me'][-1] for r in close]).round(),'carried',np.mean([r['own_me'][-1]-r['trib_me'][-1] for r in close]).round())
# tributes cancelled by their stuns/locks in close losses
print('  close: our tribute gems cancelled by lock',np.mean([r['lockcancel'][0] for r in close]).round(),'stun',np.mean([r['stuncancel'][0] for r in close]).round(), '| opp lock',np.mean([r['lockcancel'][1] for r in close]).round(),'stun',np.mean([r['stuncancel'][1] for r in close]).round())
print('  close by opp:',collections.Counter(r['opp'][:4] for r in close), 'maps', collections.Counter(r['map'] for r in close).most_common(12))
