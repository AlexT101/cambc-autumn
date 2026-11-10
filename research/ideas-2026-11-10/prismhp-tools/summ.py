import sys, json, collections
G = [json.loads(l) for l in open(sys.argv[1])]
print('games', len(G), 'win', round(sum(g['win'] for g in G) / len(G), 3))
def d600(g): return [d for d in g['deaths'] if d['r'] <= 600]
S = [g for g in G if not d600(g)]; D = [g for g in G if d600(g)]
print(f"survive<=600: {len(S)} win {sum(g['win'] for g in S)/max(1,len(S)):.3f} | died<=600: {len(D)} ({len(D)/len(G):.2f}) win {sum(g['win'] for g in D)/max(1,len(D)):.3f}")
for lo, hi in [(0, 20), (20, 50), (50, 100), (100, 200), (200, 10000)]:
    X = [g for g in D if lo <= d600(g)[0]['gems'] < hi]
    if X: print(f"  first death<=600 gems {lo}-{hi}: n {len(X)} win {sum(g['win'] for g in X)/len(X):.3f}")
A = [d for g in G for d in g['deaths']]
print('all deaths', len(A), 'per game', round(len(A) / len(G), 2), 'camp', sum(d['camp'] for d in A))
B = [d for d in A if not d['camp']]
for lo, hi in [(0, 1), (1, 20), (20, 50), (50, 100), (100, 200), (200, 10000)]:
    X = [d for d in B if lo <= d['gems'] < hi]
    if not X: continue
    q = lambda k: sum(1 for d in X if d[k] is not None and d[k] >= .8) / len(X)
    print(f" gems {lo:>3}-{hi:<5} n {len(X):4} ep_hp0>=.8 {sum(1 for d in X if (d['ep_hp0'] or 0)>=.8)/len(X):.2f} f6>=.8 {q('f6'):.2f} f3>=.8 {q('f3'):.2f}"
          f" ep_len med {sorted(d['ep_len'] for d in X)[len(X)//2]} ep_att>=2 {sum(d['ep_att']>=2 for d in X)/len(X):.2f}"
          f" en med {sorted(len(d['en']) for d in X)[len(X)//2]} outnum {sum(len(d['en'])>len(d['al'])+1 for d in X)/len(X):.2f}"
          f" gold med {sorted(d['gold'] for d in X)[len(X)//2]} maxhp med {sorted(d['maxhp'] for d in X)[len(X)//2]} hsh med {sorted(d['hshards'] for d in X)[len(X)//2]}"
          f" recalling {sum(d['chan']==1 for d in X)/len(X):.2f} rec_cancel15 {sum(any(k=='recall_cancel' and c=='damage' for _,k,c in d['rec']) for d in X)/len(X):.2f}"
          f" epdmg/maxhp med {sorted(d['ep_dmg']/d['maxhp'] for d in X)[len(X)//2]:.2f} spawn_d med {sorted(d['spawn_d'] for d in X)[len(X)//2]}")
