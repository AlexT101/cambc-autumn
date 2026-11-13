import json, os, sys, collections, math
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-08/spar-tools')
import local
cand, ref = sys.argv[1], sys.argv[2]; batches = [int(x) for x in sys.argv[3].split(',')]; fuel = sys.argv[4] if len(sys.argv) > 4 else '-fuel200000'
picks = {}
for line in open('/home/ubuntu/cambc-autumn/replays/ddov-drafts/b01/picks.tsv'):
    m, a, b = line.rstrip('\n').split('\t'); picks[m] = (a.split(','), b.split(','))
lad = {l.strip() for l in open('/home/ubuntu/cambc-autumn/tools/ladder128.txt') if l.strip()}
U = collections.defaultdict(dict)  # map -> body -> list of diffs
for j in batches:
    for o, body in (('F', 'fr8-g25'), ('M', 'mf-f9')):
        x = local.cells(f'fbe501-{cand}-{body}-m2560b{j:03d}{fuel}-Pv4'); y = local.cells(f'fbe501-{ref}-{body}-m2560b{j:03d}{fuel}-Pv4')
        for c in x.keys() & y.keys():
            U[c[0]].setdefault(o, []).append(x[c] - y[c])
def est(v):
    n = len(v); m = sum(v) / n; sd = math.sqrt(sum((a - m) ** 2 for a in v) / (n - 1)) if n > 1 else 0
    return f'{100*m:+.2f} ±{196*sd/math.sqrt(n):.2f} (n {n})'
rows = []
for m, d in U.items():
    p = picks.get(m)
    rows.append(dict(map=m, lad=m.replace('.map26a','') in lad or m in lad, refV=p and 'Vesper Vale' in p[0], ref=p and p[0], cand=p and p[1],
                     F=sum(d.get('F', [])) / max(1, len(d.get('F', []))), M=sum(d.get('M', [])) / max(1, len(d.get('M', []))),
                     all=sum(sum(v) for v in d.values()) / sum(len(v) for v in d.values())))
json.dump(rows, open(f'units-{cand}-{fuel}.json', 'w'))
fresh = [r for r in rows if not r['lad']]
print('fresh maps', len(fresh), 'with drafts', sum(r['ref'] is not None for r in fresh))
for k in (True, False):
    s = [r for r in fresh if r['refV'] == k]
    print(f"REF drafts Vesper={k}: {len(s)} maps; all {est([r['all'] for r in s])}; F {est([r['F'] for r in s])}; M {est([r['M'] for r in s])}")
s = [r for r in fresh if r['refV']]
slot = collections.Counter(r['ref'].index('Vesper Vale') for r in s); print('REF vesper slot', slot)
repl = collections.Counter()
for r in s:
    gone = set(r['ref']) - set(r['cand']); new = set(r['cand']) - set(r['ref'])
    repl[(tuple(sorted(gone)), tuple(sorted(new)))] += 1
print('swaps (out -> in):'); [print('  ', k, v) for k, v in repl.most_common(12)]
byin = collections.defaultdict(list)
for r in s:
    new = set(r['cand']) - set(r['ref']); byin[','.join(sorted(new))].append(r['all'])
print('by replacement:'); [print(f'   {k}: {est(v)}') for k, v in sorted(byin.items(), key=lambda kv: -len(kv[1]))[:10]]
lr = [r for r in rows if r['lad']]
print('ladder maps', len(lr), 'REF Vesper share', sum(bool(r['refV']) for r in lr) / max(1, len(lr)))
