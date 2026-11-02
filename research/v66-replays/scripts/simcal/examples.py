# Example stand_ok verdicts (engaged, ladder, r<=260) followed by our champion's death within 10 rounds, by cause flag.
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import cf as CF
K = 5
rs = [x for x in CF.load('ladder') if not x['lost'] and x['self_death'] is not None and x['self_death'] <= 10]
seen = set()
def show(tag, pred, n=4):
    out = []
    for x in sorted(rs, key=lambda x: (x['key'], x['r'])):
        if (x['key'], x['c'], x['r'] + x['self_death']) in seen or not pred(x): continue
        seen.add((x['key'], x['c'], x['r'] + x['self_death']))
        us = ','.join('%s%s:%d%s' % (f['typ'], '*' if i == x['self_i'] else '', f['hp'], '' if sum(f['a_any'][:K]) else '(idle)') for i, f in enumerate(x['us']))
        th = ','.join('%s:%d' % (f['typ'], f['hp']) for f in x['them'])
        ex = ','.join('%s+%d' % (e['typ'], sum(e['dmg'][:K])) for e in x['extra'])
        out.append('  %s r%d c%d %s (%s) margin %.2f falls %d | us %s | them %s | joined %s | died r%d' % (
            x['key'], x['r'], x['c'], x['t'], x['opp'], x['margin'], x['falls'], us, th, ex or '-', x['r'] + x['self_death']))
        if len(out) >= n: break
    print(tag); print('\n'.join(out))
show('ok but our champion falls in the play-out:', lambda x: x['falls'] and not x['extra'])
show('ally in the sim that dealt nothing:', lambda x: any(i != x['self_i'] and sum(f['a_any'][:K]) == 0 for i, f in enumerate(x['us'])) and not x['falls'])
show('enemies joined from outside the sim:', lambda x: x['extra'] and not x['falls'])
show('Cassi their weakest, Issac in front:', lambda x: any(f['typ'] == 'issac' for f in x['them']) and min(x['them'], key=lambda f: f['hp'] + f['sh'])['typ'] == 'cassi')
