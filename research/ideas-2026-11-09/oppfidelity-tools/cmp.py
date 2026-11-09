# Paired CAND - REF by member and site class, over ab.py runs named of-<tag>-<member> (runs.sh) or dgate's runs.
#   py cmp.py CANDTAG REFTAG MEMBER...      e.g. cmp.py lk600 c25 spar-o25-Mt spar-oc29-Mt
#   a member 'dgate:o25M' reads dgate's cached runs of variants/v87-lk-600 / variants/oc-base25 (cand/ref = dirs then)
import json, math, sys, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools')
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/diverse-tools')
import local
MC = json.load(open('/home/ubuntu/tmp-offload/handoff/gate/mapclass.json'))
DIRS = {'skfw': 'variants/v87-sk-fw', 'sktb': 'variants/v87-sk-tb', 'skcc': 'variants/v87-sk-cc', 'sk': 'variants/v87-soupk', 'lk600': 'variants/v87-lk-600', 'c25': 'variants/oc-base25', 'nh63': 'variants/v87-nh-6-3'}
def cls(m): return MC.get(m.replace('-', '_'), MC.get(m, '?'))
def run(tag, m):
    if m.startswith('dgate:'):
        import dgate
        b, o = m[6:-1], m[-1]; return dgate.rname(DIRS[tag], b, o)
    import os, re, dgate
    n = f'of-{tag}-{m}'
    if os.path.exists(f'{local.R}replays/ab/{n}/summary.json'): return n
    # an old dgate member (spar-o25-F, spar-oc29-M, spar-dvnK-F) falls back on dgate's cached run of that bot
    mm = re.fullmatch(r'spar-(o25|oc29|dvn\d+)-([FM])', m)
    return dgate.rname(DIRS[tag], mm[1].replace('oc29', 'o29'), mm[2]) if mm else n
def table(cand, ref, members):
    agg = collections.defaultdict(list); lev = collections.defaultdict(list)
    for m in members:
        x, y = local.cells(run(cand, m)), local.cells(run(ref, m))
        for c in x.keys() & y.keys():
            for g in ((m, cls(c[0])), (m, 'all'), ('ALL', cls(c[0])), ('ALL', 'all')):
                agg[g].append(x[c] - y[c]); lev[g].append(y[c])
    for g in sorted(agg):
        d = agg[g]; n = len(d); mu = sum(d) / n; sd = (sum((v - mu) ** 2 for v in d) / n) ** .5
        print(f'  {g[0]:16s} {g[1]:5s} n {n:5d}  ref win {100*sum(lev[g])/n:5.1f}  cand-ref {100*mu:+6.2f} ±{196*sd/math.sqrt(n):.2f} pts  flips {100*sum(v != 0 for v in d)/n:.0f}%')
if __name__ == '__main__':
    table(sys.argv[1], sys.argv[2], sys.argv[3:])
