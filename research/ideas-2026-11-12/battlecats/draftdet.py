"""Is BattleCats' pick k a function of (map, side, own earlier picks) or also of the opponent's earlier picks?
Leave-one-out modal accuracy on a time window; keys with too few games skipped."""
import meta, collections, sys
lo = sys.argv[1] if len(sys.argv) > 1 else "2026-11-10T06"
hi = sys.argv[3] if len(sys.argv) > 3 else "9999"
kinds = sys.argv[2].split(',') if len(sys.argv) > 2 else ['ranked', 'unranked']
R = [r for r in meta.rows() if r["created_at"] >= lo and r["created_at"] < hi and r['kind'] in kinds]
print(len(R), 'games from', lo, kinds)
def loo(keyf, k):
    tab = collections.defaultdict(collections.Counter)
    S = [r for r in R if len(r['bc_picks']) > k]
    for r in S: tab[keyf(r, k)][r['bc_picks'][k]] += 1
    hit = n = 0
    for r in S:
        c = tab[keyf(r, k)].copy(); c[r['bc_picks'][k]] -= 1
        if sum(c.values()) < 1: continue
        n += 1; hit += c.most_common(1)[0][0] == r['bc_picks'][k]
    return hit / max(n, 1), n
A = lambda r, k: (r['map'], r['bc_side'], tuple(r['bc_picks'][:k]))
B = lambda r, k: (r['map'], r['bc_side'], tuple(r['bc_picks'][:k]), tuple(r['op_picks'][:k]))
Bset = lambda r, k: (r['map'], r['bc_side'], tuple(r['bc_picks'][:k]), frozenset(r['op_picks'][:k]))
# restrict to keys where B has data: compare on the same games
for k in range(5):
    S = [r for r in R if len(r['bc_picks']) > k]
    tabB = collections.Counter(B(r, k) for r in S)
    keep = [r for r in S if tabB[B(r, k)] >= 2]
    global_R = R
    R2 = R; R = keep
    a = loo(A, k); b = loo(B, k)
    R = R2
    print(f'pick {k}: n={len(S)} sameB-n={len(keep)}  modal acc own-only {a[0]:.3f} ({a[1]})  +opp {b[0]:.3f} ({b[1]})')
