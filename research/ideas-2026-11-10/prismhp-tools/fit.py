import json, sys, numpy as np
R=np.array(json.load(open(sys.argv[1])),dtype=float)
h,ha,g,ne,n4,a5,d,mh,r=R.T
def fit(X,y,it=60):
    X=np.c_[np.ones(len(y)),X]; w=np.zeros(X.shape[1])
    for _ in range(it):
        p=1/(1+np.exp(-X@w)); W=p*(1-p); H=X.T@(X*W[:,None])+1e-6*np.eye(len(w)); w+=np.linalg.solve(H,X.T@(y-p))
    p=1/(1+np.exp(-X@w)); ll=np.sum(d*np.log(p)+(1-d)*np.log(1-p)) if len(y)==len(d) else 0
    return w, ll
lg=np.log1p(g)
for name,X in [('h,lg,hlg',np.c_[h,lg,h*lg]),('h,lg,hlg,n5,a5',np.c_[h,lg,h*lg,n4,a5])]:
    w,ll=fit(X,d); print(name, np.round(w,3), round(ll,1))
w,_=fit(np.c_[h,lg,h*lg,n4,a5],d)
L=lambda hh,gg,n,a: 1/(1+np.exp(-(w[0]+w[1]*hh+w[2]*np.log1p(gg)+w[3]*hh*np.log1p(gg)+w[4]*n+w[5]*a)))
for gg in (0,30,100,200,300):
    print(gg, ' '.join(f'{L(hh,gg,1,0):.3f}' for hh in (0.2,0.3,0.4,0.5,0.6,0.7,0.8)), '| n2', ' '.join(f'{L(hh,gg,2,0):.3f}' for hh in (0.3,0.5,0.7)))
