"""wm.py BATCHDIR [PREFIX]: tabulate fga-meas's WM lines (bot 1's team) by turn class."""
import sys, zipfile, glob, os, statistics as st, collections
d = sys.argv[1]
pref = sys.argv[2] if len(sys.argv) > 2 else 'WM'
F = 'round alive W vision prio allies evis nvis eun nun camps csettle cs cin_f cin cout_f cout altsc first dec t0 cuts farmcut ngroups'.split()
rows = []
for f in glob.glob(os.path.join(d, '*.repl26a')):
    side = 'a' if f.endswith('-12.repl26a') else 'b'
    try:
        z = zipfile.ZipFile(f)
        txt = z.read(f'team-{side}.stdout').decode(errors='replace')
    except Exception as e:
        continue
    for l in txt.splitlines():
        if l.startswith(pref + ' '):
            p = l.split()[1:]
            if len(p) != len(F): continue
            r = dict(zip(F, map(int, p)))
            if r["first"] > 300000 or r["dec"] > 300000: continue
            rows.append(r)
print(len(rows), 'turns')
def summ(name, rs):
    if not rs: return
    n = len(rs)
    def m(k): return sum(r[k] for r in rs) / n
    acted = [r for r in rs if r['first'] > 0]
    print(f'== {name}: {n} turns ({100*n/len(rows):.1f}%)')
    print('  world %.0f  vision %.0f prio %.0f allies %.0f  enemies vis %.0f (n %.2f) unseen %.0f (n %.2f)  camps %.0f [settle %.0f n %.2f, upd-in %.0f n %.2f, upd-out %.0f n %.2f]  alt+sc %.0f' % (
        m('W'), m('vision'), m('prio'), m('allies'), m('evis'), m('nvis'), m('eun'), m('nun'), m('camps'), m('csettle'), m('cs'), m('cin_f'), m('cin'), m('cout_f'), m('cout'), m('altsc')))
    rest = m('W') - m('vision') - m('prio') - m('allies') - m('evis') - m('eun') - m('camps') - m('altsc')
    print('  other inside world run %.0f' % rest)
    Ws = sorted(r['W'] for r in rs)
    print('  world p50 %d p90 %d p99 %d' % (Ws[n // 2], Ws[int(n * .9)], Ws[int(n * .99)]))
    print('  acted in decide %.1f%%; spent to first action mean %.0f (p50 %d); decide end spent %.0f' % (
        100 * len(acted) / n, sum(r['first'] for r in acted) / max(1, len(acted)),
        sorted(r['first'] for r in acted)[len(acted) // 2] if acted else 0, m('dec')))
alive = [r for r in rows if r['alive']]
summ('all', rows)
summ('alive', alive)
summ('dead', [r for r in rows if not r['alive']])
summ('alive, any cut', [r for r in alive if r['cuts'] > 0])
summ('alive, farm cut', [r for r in alive if r['farmcut'] > 0])
summ('alive, no cut', [r for r in alive if r['cuts'] == 0])
summ('alive, vis enemy', [r for r in alive if r['nvis'] > 0])
