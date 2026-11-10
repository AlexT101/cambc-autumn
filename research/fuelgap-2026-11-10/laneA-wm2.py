"""wm2.py BATCHDIR: fga-meas WM + WT lines (bot 1's team): world parts, tracking near/far, rank, first turn."""
import sys, zipfile, glob, os
d = sys.argv[1]
F = 'round alive W vision prio allies evis nvis eun nun camps csettle cs cin_f cin cout_f cout altsc first dec t0 cuts farmcut ngroups'.split()
T = 'tnear ntnear tfar ntfar rank'.split()
rows, first = [], []
for f in glob.glob(os.path.join(d, '*.repl26a')):
    side = 'a' if f.endswith('-12.repl26a') else 'b'
    try:
        txt = zipfile.ZipFile(f).read(f'team-{side}.stdout').decode(errors='replace')
    except Exception:
        continue
    last = None
    for l in txt.splitlines():
        l = l.strip()
        if l.startswith('WM '):
            p = l.split()[1:]
            last = None
            if len(p) != len(F): continue
            r = dict(zip(F, map(int, p)))
            if r['first'] > 300000 or r['dec'] > 300000: continue
            last = r
        elif l.startswith('WT ') and last is not None:
            p = l.split()[1:]
            if len(p) == len(T):
                last.update(zip(T, map(int, p)))
                rows.append(last)
            last = None
        elif l.startswith('WF '):
            p = list(map(int, l.split()[1:]))
            if len(p) == 3 and p[0] < 1_000_000: first.append(p)
print(len(rows), 'turns;', len(first), 'first turns')
if first:
    n = len(first)
    print('first turn: world mean %.0f p50 %d max %d; first action at %.0f; decide end %.0f' % (
        sum(x[0] for x in first) / n, sorted(x[0] for x in first)[n // 2], max(x[0] for x in first),
        sum(x[1] for x in first) / n, sum(x[2] for x in first) / n))
def summ(name, rs):
    if not rs: return
    n = len(rs)
    m = lambda k: sum(r[k] for r in rs) / n
    print(f'== {name}: {n} turns')
    print('  world %.0f | track near %.0f (n %.2f) far %.0f (n %.2f) | rank %.0f | altars+scores %.0f | out-of-view camps %.0f' % (
        m('W'), m('tnear'), m('ntnear'), m('tfar'), m('ntfar'), m('rank'), m('altsc'), m('cout_f')))
    print('  upper bound not obviously read before acting (far tracking + altars/scores + out-of-view camps): %.0f' % (
        m('tfar') + m('altsc') + m('cout_f')))
alive = [r for r in rows if r['alive']]
summ('alive', alive)
summ('alive, any cut', [r for r in alive if r['cuts'] > 0])
summ('alive, farm cut', [r for r in alive if r['farmcut'] > 0])
