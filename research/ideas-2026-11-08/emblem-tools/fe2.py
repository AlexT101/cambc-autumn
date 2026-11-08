"""Owns family F by round T (vs not), at fixed emblem count by T and team/opp gold at T, within (day,map,side) cell."""
import sys; sys.path.insert(0,'/home/ubuntu/tmp-offload/emblem/tools'); from arch import *; from fe import within, CI
FI = {f: i for i, f in enumerate(FAM)}
def run(days, team, ty, F, T, post=(400, 600)):
    acc = []
    for d in days:
        S, U, m = day(d)
        s = (U['team'] == team) & (U['type'] == ty); row = U['row'][s]; e = U['e'][s]; r = U['r'][s]
        by = (r <= T); owns = ((e // 6 == FI[F]) & by & (e != 255)).any(1); nemb = by.sum(1)
        acc.append(dict(owns=owns, nemb=nemb, gold=S['gold'][row], ogold=S['ogold'][row], win=S['win'][row], orat=S['orating'][row],
                        cell=np.array([f'{d[-2:]}:{a}:{b}' for a, b in zip(S['map'][row], S['side'][row])])))
    D = {k: np.concatenate([a[k] for a in acc]) for k in acc[0]}
    tc = CI[min(CP, key=lambda c: abs(c - T))]
    X = np.stack([D['owns'], D['nemb'], D['gold'][:, tc], D['ogold'][:, tc], D['orat']], 1).astype(float)
    ok = np.isfinite(X).all(1)
    out = f'{team[:6]:6s} {ty[:8]:8s} {F[:4]}<=r{T} share {D["owns"][ok].mean():.2f} n={ok.sum()}:'
    for p in post:
        y = D['gold'][:, CI[p]]; k = ok & np.isfinite(y)
        b, se = within(y[k], X[k], D['cell'][k]); out += f'  gold{p} {b[0]:+.0f}±{se[0]:.0f}'
    b, se = within(D['win'][ok], X[ok], D['cell'][ok]); out += f'  win {b[0]:+.3f}±{se[0]:.3f}'
    print(out)
if __name__ == '__main__':
    days = ['2026-11-06', '2026-11-07']
    for team in ('Intercontinental Fish', 'Mite', 'stellar best girl'):
        for ty in ('Vesper Vale', 'Vendetta', 'Marcella', 'Heart of Ruin'):
            for F, T in (('Capture', 200), ('Capture', 300)):
                try: run(days, team, ty, F, T)
                except Exception as ex: print(team, ty, F, 'fail', ex)
