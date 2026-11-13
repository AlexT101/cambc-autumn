"""Aggregate /tmp/mxi-study/farmwin.jsonl: the loser-vs-winner farm gap in farm-break windows."""
import json, sys
from collections import Counter, defaultdict
G = [json.loads(l) for l in open('/tmp/mxi-study/farmwin.jsonl')]
N = len(G)
gap = sum(g['parts']['farm'] for g in G)
print(f'farm games {N}; farm gap total {gap}, per game {gap/N:.1f}; fight part {sum(g["parts"]["fight"] for g in G)/N:.1f}; gap_end {sum(g["gap_end"] for g in G)/N:.1f}')
import statistics
print('break median', statistics.median(g['brk'] for g in G), 'p25/p75', sorted(g['brk'] for g in G)[N//4], sorted(g['brk'] for g in G)[3*N//4])
print('window length mean', sum(g['w1']-g['w0']+1 for g in G)/N)

def sec(t): print('\n## ' + t)

# --- captures by location relative to the loser
sec('capture gems per game by group location (relative to loser), W vs L')
loc = defaultdict(lambda: [0, 0, 0, 0])  # gems W, gems L, n W, n L
for g in G:
    for c in g['caps']:
        k = (c['rel_L'], 'cluster' if c['cluster'] else 'monster')
        i = 0 if c['team'] == 'W' else 1
        loc[k][i] += c['gems']; loc[k][2 + i] += 1
tot = 0
for k in sorted(loc):
    w, l, nw, nl = loc[k]
    tot += w - l
    print(f'{k[0]:6s} {k[1]:8s} W {w/N:6.1f} ({nw/N:.2f} caps)  L {l/N:6.1f} ({nl/N:.2f} caps)  W-L {(w-l)/N:6.1f}  share of gap {(w-l)/gap:5.0%}')
print('check', tot / N)

sec('winner captures by whether the loser touched that cycle / loser captures by whether winner touched')
for team in 'WL':
    c2 = defaultdict(lambda: [0, 0])
    for g in G:
        for c in g['caps']:
            if c['team'] != team: continue
            ot = c['other_touched']
            kind = 'other hit' if 'hit' in ot else 'other held/contested' if ot else 'uncontested'
            if c['cleared_by'] not in (team, 'N'): kind += ' +other cleared'
            k = (c['rel_L'], kind)
            c2[k][0] += c['gems']; c2[k][1] += 1
    for k in sorted(c2):
        print(team, f'{k[0]:6s} {k[1]:32s} gems/game {c2[k][0]/N:6.1f} caps/game {c2[k][1]/N:.2f}')

# --- per type: capture gems, alive rounds, class mix
sec('per champion type (games containing it): capture gems/game, alive rounds/game, and the W-L class rounds/game')
types = Counter()
for g in G:
    for ty in g['time']['W']:
        types[ty] += 1
CL = ['dead', 'fight', 'camp', 'hold', 'tribute', 'recall', 'walk', 'walk_bag', 'wait_camp', 'wait_altar', 'idle', 'spawn', 'lost', 'teleport']
rows = []
for ty, ng in types.most_common():
    cw = sum(g['capgems']['W'].get(ty, 0) for g in G) / ng
    cl = sum(g['capgems']['L'].get(ty, 0) for g in G) / ng
    aw = sum(g['alive']['W'].get(ty, 0) for g in G) / ng
    al = sum(g['alive']['L'].get(ty, 0) for g in G) / ng
    diffs = {k: (sum(g['time']['W'].get(ty, {}).get(k, 0) for g in G) - sum(g['time']['L'].get(ty, {}).get(k, 0) for g in G)) / ng for k in CL}
    share_gap = (cw - cl) * ng / gap
    print(f'{ty:13s} n={ng:3d} capW {cw:5.1f} capL {cl:5.1f} (gap share {share_gap:4.0%}) aliveW {aw:5.1f} aliveL {al:5.1f} rateW {cw/max(aw,1):.3f} rateL {cl/max(al,1):.3f}')
    print('    W-L rounds: ' + ' '.join(f'{k} {v:+.1f}' for k, v in diffs.items() if abs(v) >= 0.3))
    # alive vs rate decomposition
    if aw and al:
        a_part = (aw - al) * cw / aw
        r_part = al * (cw / aw - cl / al)
        print(f'    decomposition per game: alive-time part {a_part:+.1f}  rate part {r_part:+.1f}')

# --- branch mix
sec('branch rounds per game (alive), W vs L, all types')
bw, bl = Counter(), Counter()
for g in G:
    for ty, d in g['br']['W'].items(): bw.update(d)
    for ty, d in g['br']['L'].items(): bl.update(d)
for k in sorted(set(bw) | set(bl), key=lambda k: -(bw[k] + bl[k])):
    print(f'{k} W {bw[k]/N:6.1f} L {bl[k]/N:6.1f} W-L {(bw[k]-bl[k])/N:+6.1f}')

sec('walk rounds per game by (branch, led-to), W vs L (top differences)')
ww, wl = Counter(), Counter()
for g in G:
    for k, v in g['walk_br']['W'].items():
        ty, b, kk, led = k.split('|'); ww[(b, led)] += v
    for k, v in g['walk_br']['L'].items():
        ty, b, kk, led = k.split('|'); wl[(b, led)] += v
for k in sorted(set(ww) | set(wl), key=lambda k: -abs(ww[k] - wl[k]))[:20]:
    print(k, f'W {ww[k]/N:6.1f} L {wl[k]/N:6.1f} L-W {(wl[k]-ww[k])/N:+6.1f}')

sec('F-branch walk rounds per game by farm-group side relative to the walker')
fw, fl = Counter(), Counter()
for g in G:
    for k, v in g['farm_target']['W'].items(): fw[k] += v
    for k, v in g['farm_target']['L'].items(): fl[k] += v
for k in sorted(set(fw) | set(fl)):
    print(k, f'W {fw[k]/N:6.1f} L {fl[k]/N:6.1f} L-W {(fl[k]-fw[k])/N:+6.1f}')

sec('idle capacity per game (value-rounds: gems+gold/4 per (respawn+6) round, summed over rounds a group sat asleep/unheld), by side relative to each team')
iw, il = Counter(), Counter()
for g in G:
    for k, v in g['idle']['W'].items(): iw[k] += v
    for k, v in g['idle']['L'].items(): il[k] += v
for k in sorted(set(iw) | set(il)):
    print(k, f'W-own-frame {iw[k]/N:6.1f} L-own-frame {il[k]/N:6.1f} L-W {(il[k]-iw[k])/N:+6.1f}')

sec('deaths overlapping the window')
for team in 'WL':
    ds = [d for g in G for d in g['deaths'] if d['team'] == team]
    lr = sum(d['lost_rounds'] for d in ds)
    print(team, f'deaths/game {len(ds)/N:.2f} (in window {sum(d["in_window"] for d in ds)/N:.2f}); champion-rounds dead in window/game {lr/N:.1f}; bag lost/game {sum(d["bag"] for d in ds if d["in_window"])/N:.1f}')
    for key in ('type', 'killer', 'branch', 'prev'):
        c = Counter(); cr = Counter()
        for d in ds:
            c[d[key]] += 1; cr[d[key]] += d['lost_rounds']
        print('   by', key, ', '.join(f'{k} {c[k]/N:.2f} ({cr[k]/N:.1f} rnds)' for k, _ in c.most_common(8)))
    bags = Counter('0' if d['bag'] == 0 else '<20' if d['bag'] < 20 else '<50' if d['bag'] < 50 else '50+' for d in ds)
    print('   bags', dict(bags))
