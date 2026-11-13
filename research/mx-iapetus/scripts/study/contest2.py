"""Mid contested cycles: per-team strength near the group (hp, maxHp, Strength, Focus, gold earned), and branch mix of
near champions over the next 10 rounds; split by numbers."""
import json, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, '/home/ubuntu/wt/mx-iapetus/tools/replay')
sys.path.insert(0, '/tmp/mxi-study')
from analysis.data import Game, chebyshev  # noqa
from farmwin import read_trace  # noqa


def work(g):
    G = Game(g['dir'])
    R = G.rounds
    Wt = G.winner
    role = {Wt: 'W', 1 - Wt: 'L'}
    gm = {grp['id']: grp for grp in G.map.groups}
    tr = None
    out = []
    # team totals at window start
    i0 = max(0, g['w0'] - 2)
    team = {ro: {'earned': 0, 'maxHp': 0, 'str': 0} for ro in 'WL'}
    for ch in R['champions']:
        ro = role[ch['team']]
        team[ro]['earned'] += ch['earned'][i0] or 0
        team[ro]['maxHp'] += ch['maxHp'][i0] or 0
        team[ro]['str'] += ch['str'][i0] or 0
    for c in g['cycles']:
        if not (c['W_tgt'] and c['L_tgt'] and c['cap'] in 'WL' and g['w0'] <= c['z'] <= g['w1'] and c['side_L'] == 'mid'):
            continue
        if tr is None:
            tr = read_trace(G.meta['source'])
        rc = max(c['W_tgt_first'], c['L_tgt_first'])
        tiles = [tuple(t) for t in gm[c['g']]['tiles']]
        i = min(len(R['round']) - 1, max(0, rc - 1))
        res = {'cap': c['cap'], 'gems': c['gems'], 'rc': rc, 'dir': g['dir'], 'g': c['g'], 'types': c['types'], 'team': team}
        for ro in 'WL':
            res[ro] = {'n': 0, 'hp': 0, 'maxHp': 0, 'str': 0, 'foc': 0, 'br': Counter(), 'names': []}
        for ch in R['champions']:
            ro = role[ch['team']]
            if not ch['alive'][i] or ch['x'][i] is None: continue
            p = (ch['x'][i], ch['y'][i])
            if min(chebyshev(p, t) for t in tiles) <= 8:
                d = res[ro]
                d['n'] += 1; d['hp'] += ch['hp'][i]; d['maxHp'] += ch['maxHp'][i]; d['str'] += ch['str'][i]; d['foc'] += ch['foc'][i]
                d['names'].append(G.name_of[ch['id']])
                for r in range(rc, rc + 11):
                    b = tr.get((ch['id'], r))
                    if b: d['br'][b[0] if b[0] != 'F' else ('Fg' if b[1] == c['g'] else 'Fo')] += 1
        for ro in 'WL': res[ro]['br'] = dict(res[ro]['br'])
        out.append(res)
    return out


if __name__ == '__main__':
    C = [json.loads(l) for l in open('/tmp/mxi-study/cycles.jsonl')]
    with ProcessPoolExecutor(24) as ex:
        rows = [r for rs in ex.map(work, C, chunksize=4) for r in rs]
    json.dump(rows, open('/tmp/mxi-study/contest2.json', 'w'))
    N = len(C)
    for lab, sel in (('even numbers', lambda r: r['W']['n'] == r['L']['n'] and r['W']['n'] > 0), ('all', lambda r: True)):
        S = [r for r in rows if sel(r)]
        print(f'\n## mid contests, {lab}: {len(S)}; W captures {sum(r["cap"]=="W" for r in S)/len(S):.0%}')
        for ro in 'WL':
            k = sum(r[ro]['n'] for r in S) or 1
            br = Counter()
            for r in S: br.update(r[ro]['br'])
            tb = sum(br.values())
            print(f' {ro}: per body hp {sum(r[ro]["hp"] for r in S)/k:.0f} maxHp {sum(r[ro]["maxHp"] for r in S)/k:.0f} hp% {sum(r[ro]["hp"] for r in S)/max(1,sum(r[ro]["maxHp"] for r in S)):.0%} str {sum(r[ro]["str"] for r in S)/k:.1f} foc {sum(r[ro]["foc"] for r in S)/k:.0f}; '
                  f'team earned gold {sum(r["team"][ro]["earned"] for r in S)/len(S):.0f} team maxHp {sum(r["team"][ro]["maxHp"] for r in S)/len(S):.0f} team str {sum(r["team"][ro]["str"] for r in S)/len(S):.0f}')
            print('    near-body branches next 10 rounds:', ', '.join(f'{b} {v/tb:.0%}' for b, v in br.most_common(9)))
        # outcome by hp% advantage at even numbers
        if lab == 'even numbers':
            bucket = defaultdict(lambda: [0, 0])
            for r in S:
                fw = r['W']['hp'] / max(1, r['W']['maxHp']); fl = r['L']['hp'] / max(1, r['L']['maxHp'])
                k = 'W hp% higher by 15+' if fw - fl > 0.15 else 'L hp% higher by 15+' if fl - fw > 0.15 else 'within 15pt'
                bucket[k][0] += 1; bucket[k][1] += r['cap'] == 'W'
            print(' by hp% ->', {k: f'n {v[0]} W {v[1]/v[0]:.0%}' for k, v in bucket.items()})
            bucket = defaultdict(lambda: [0, 0])
            for r in S:
                k = 'W str higher 10%+' if r['W']['str'] > 1.1 * r['L']['str'] else 'L str higher 10%+' if r['L']['str'] > 1.1 * r['W']['str'] else 'within 10%'
                bucket[k][0] += 1; bucket[k][1] += r['cap'] == 'W'
            print(' by Strength ->', {k: f'n {v[0]} W {v[1]/v[0]:.0%}' for k, v in bucket.items()})
            bucket = defaultdict(lambda: [0, 0])
            for r in S:
                pw, pl = 'Prism' in r['W']['names'], 'Prism' in r['L']['names']
                k = f'Prism W{int(pw)} L{int(pl)}'
                bucket[k][0] += 1; bucket[k][1] += r['cap'] == 'W'
            print(' by Prism presence ->', {k: f'n {v[0]} W {v[1]/v[0]:.0%}' for k, v in sorted(bucket.items())})
