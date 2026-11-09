import pickle, collections, sys
KEYS=['rounds','win','tstart','trib','tribg','tstart100','trib100','trib100g','tribsmall','restart10','tcan_lock','tcan_stun','tcan_manual','lockcut','lockcut_ran','lockcut100','lockcut_late','lock_e','lock_l','lockhit','death','dgems','death40','death100','carry40','carry100','carry150','maxbag']
def table(rows, label):
    # rows: list of metric dicts
    n=len(rows); out={}
    for k in KEYS:
        for side in ('us','op'):
            kk = k if k in ('rounds','win') else f'{k}_{side}'
            if k in ('rounds','win') and side=='op': continue
            out[kk]=sum(r.get(kk,0) for r in rows)/n
    return n,out
def show(groups):
    labels=list(groups)
    stats={l:table(groups[l],l) for l in labels}
    print('metric'.ljust(18)+''.join(f'{l[:14]:>15}' for l in labels))
    print('n'.ljust(18)+''.join(f'{stats[l][0]:>15}' for l in labels))
    for kk in stats[labels[0]][1]:
        print(kk.ljust(18)+''.join(f'{stats[l][1].get(kk,0):>15.2f}' for l in labels))
if __name__=='__main__':
    res=pickle.load(open(sys.argv[1],'rb'))
    g=collections.defaultdict(list)
    for v,opp,m,f in res:
        if f: g[opp].append(f)
    show(g)
