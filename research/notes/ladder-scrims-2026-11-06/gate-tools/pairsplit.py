"""pairsplit.py A B [part]: paired flips of version B against A by opponent and map class (one-site or other)."""
import json, sys
sys.path.insert(0, '/home/ubuntu/cambc-autumn/tools')
import ladder_scrims as ls
S = __import__('os').environ.get('GATE_DIR', '/tmp/gate')
cls = json.load(open(f'{S}/mapclass.json'))
a, b = int(sys.argv[1]), int(sys.argv[2])
part = sys.argv[3] if len(sys.argv) > 3 else None
key = lambda r: (r['opp_name'][:12], r.get('refset'), r['map'], r['side'])
ra = {key(r): r for r in ls.games(a) if r['purpose'] == 'set' and (not part or r['part'] == part)}
rb = {key(r): r for r in ls.games(b) if r['purpose'] == 'set' and (not part or r['part'] == part)}
both = sorted(set(ra) & set(rb))
agg = {}
flips = []
for k in both:
    wa, wb = ra[k]['result'] == 'win', rb[k]['result'] == 'win'
    c = cls[k[2]]
    for g in ((k[0], c), (k[0], 'all'), ('total', c), ('total', 'all')):
        s = agg.setdefault(g, [0, 0, 0, 0, 0])
        s[0] += 1; s[1] += wa; s[2] += wb; s[3] += wb and not wa; s[4] += wa and not wb
    if wa != wb:
        flips.append((k[0], k[2], k[3], c, f'v{b} ' + ('won' if wb else 'lost'),
                      f"v{a} {ra[k].get('our_gems')}-{ra[k].get('opp_gems')} r{ra[k].get('rounds')}",
                      f"v{b} {rb[k].get('our_gems')}-{rb[k].get('opp_gems')} r{rb[k].get('rounds')}"))
print(f'v{b} against v{a}: {len(both)} paired games' + (f' ({part})' if part else ''))
print(f"{'opp':<13}{'class':<7}{'n':>4} {'v'+str(a):>6} {'v'+str(b):>6} {'+':>4} {'-':>4} {'net':>5}")
for g, (n, wa, wb, up, dn) in sorted(agg.items()):
    print(f'{g[0]:<13}{g[1]:<7}{n:>4} {wa:>6} {wb:>6} {up:>4} {dn:>4} {up - dn:>+5}')
print('\nflips:')
for f in flips:
    print('  ', *f)
