import sys, collections, statistics
sys.path.insert(0, 'tools/fuel/census')
import census
rows = census.load(sys.argv[1:2])
sel = sys.argv[2] if len(sys.argv) > 2 else 'oof'
def pick(r):
    if sel == 'oof': return r['oof'] and not r['late']
    if sel == 'ooflate': return r['oof'] and r['late']
    if sel == 'heavy': return not r['oof'] and r['spent'] - r['c'].get('queue', (0,0,0))[0] >= 65000
    if sel == 'all': return True
R = [r for r in rows if pick(r)]
print(len(rows), 'rows;', len(R), sel)
inc = collections.defaultdict(list); slf = collections.defaultdict(int); cnt = collections.defaultdict(int)
for r in R:
    for k, (i, s, n) in r['c'].items():
        inc[k].append(i); slf[k] += s; cnt[k] += n
tot = sum(slf.values())
print(f"{'label':28s} {'present%':>8s} {'incl mean(present)':>18s} {'incl mean(all)':>14s} {'self%':>6s} {'calls/turn':>10s}")
for k in sorted(inc, key=lambda k: -sum(inc[k])):
    v = inc[k]
    print(f"{k:28s} {len(v)/len(R)*100:8.1f} {statistics.mean(v):18.0f} {sum(v)/len(R):14.0f} {slf[k]/tot*100:6.1f} {cnt[k]/len(R):10.2f}")
