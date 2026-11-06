"""Range opportunities (ENGAGE.md section 1): a visible enemy at Chebyshev 4-8, none nearer, no contact.

One row per opportunity turn: free (alive, unstunned, off spawn, no tribute/teleport channel), the
turn completes alive, no camp hit this turn, not standing on an empty group. Causal features `x` come
from the engage rows' x (own start perspective and own memory); labels `y` from this turn's end and the
actor's next turns (hindsight farm goal: the end tile of its next camp-hit turn within 40 turns).

  python3 tools/fish/engage_range.py OUT.jsonl.gz [--cohorts ...]
"""
import argparse
import gzip
import json
import multiprocessing as mp
from pathlib import Path

from engage_common import FIT, HELD, RANGED, REACH, ROWS, THREAT_REACH, free


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def sgn(v):
    return (v > 0) - (v < 0)


def ehp(q):
    return q['hp'] + q['sh']


def one(line):
    g = json.loads(line)
    out = []
    for aid, rows in g['actors'].items():
        nxt = [None] * len(rows); cur = None
        for i in range(len(rows) - 1, -1, -1):
            r = rows[i]
            if not r['alive']:
                cur = None
            y = r.get('y')
            if y and y['camp']:
                cur = (r['r'], (y['ex'], y['ey']))
            nxt[i] = cur
        for i, r in enumerate(rows):
            x, y = r.get('x'), r.get('y')
            if not (x and y and free(x) and x['E']) or not 4 <= x['d1'] <= 8:
                continue
            if y['camp'] or x['gst'] == 2:
                continue
            e = x['E'][0]
            p0 = (x['x'], x['y']); p1 = (y['ex'], y['ey'])
            prev = rows[i - 1] if i else None
            px, py = (prev.get('x'), prev.get('y')) if prev else (None, None)
            mom = None; e_prev_d = None; prev_dd = None
            if px and py and prev['r'] == r['r'] - 1:
                v = (py['ex'] - px['x'], py['ey'] - px['y'])
                if max(abs(v[0]), abs(v[1])) == 1 and (py['ex'], py['ey']) == p0:
                    mom = sgn(cheb((p0[0] + v[0], p0[1] + v[1]), (e['x'], e['y'])) - e['d'])
                elif v == (0, 0):
                    mom = 0
                pe = next((q for q in px['E'] if q['id'] == e['id']), None)
                if pe is not None:
                    e_prev_d = pe['d']
                    prev_dd = py['ed'][str(e['id'])] - pe['d']
            near_e = [q for q in x['E'] if q['d'] <= 8]
            allies8 = [a for a in x['A'] if a['d'] <= 8]
            own = ehp(x)
            ratio = (own + sum(ehp(a) for a in allies8)) / max(1, sum(ehp(q) for q in near_e))
            gh = x['hp'] / x['mhp'] * (0.65 if x['gems'] else 1)
            feat = dict(
                type=x['type'], ranged=x['ranged'], hpf=round(x['hp'] / x['mhp'], 3), gh=round(gh, 3), gems=x['gems'],
                gold=x['gold'], d1=e['d'], wd0=x['wd0'], etype=e['type'], eranged=e['type'] in RANGED,
                ereach=REACH[e['type']], ethreat_reach=THREAT_REACH[e['type']], my_threat_reach=THREAT_REACH[x['type']],
                ehpf=round(e['hp'] / e['mhp'], 3), egems=e['gems'], ech=e['ch'], esp=e['esp'], ebush=e['bush'],
                n_e=len(near_e), n_a8=len(allies8), n_a4=sum(1 for a in x['A'] if a['d'] <= 4),
                ratio=round(ratio, 3), e_ehp=sum(ehp(q) for q in near_e), a_ehp=own + sum(ehp(a) for a in allies8),
                ally_closer=sum(1 for a in x['A'] if a['ed'] < e['d']), ally_ed=min([a['ed'] for a in x['A']] or [99]),
                thr=sum(q['thr'] for q in x['E']), mom=mom, e_prev_d=e_prev_d, prev_dd=prev_dd,
                e_moved=(e['d'] - e_prev_d) if e_prev_d is not None else None,
                ct=x['ct'] if x['ch'] == 1 else 0, aggro=x['aggro'], camps_near=x['camps_near'],
                hw=x['hw'], ehw=x['ehw'], so=x['so'], sx=x['sx'], round=r['r'], lc=x['lc'],
                lhit=x['lhit'][0] if x['lhit'] else None, ealive=x['ealive'], bush=x['bush'],
                dash_ready=x['cd'][1] == 0 if x['type'] in (1, 2, 4, 9, 12) else None,
                cd=x['cd'], mem_n=sum(1 for m in x['M'] if m.get('alive')))
            nf = nxt[i + 1] if i + 1 < len(rows) else None
            if nf is not None and nf[0] - r['r'] > 40:
                nf = None
            fut = rows[i + 1:i + 6]
            hit3 = next((k + 1 for k, q in enumerate(fut[:3]) if q.get('y') and q['y']['hitc']), None)
            died5 = any(not q['alive'] for q in fut)
            lab = dict(edd=y['ed'][str(e['id'])] - e['d'], moved=p0 != p1, dash=y['dash'], hit_now=bool(y['hitc']),
                       hit3=hit3, died5=died5, recall_keep=y['recall'] and x['ch'] == 1 and not y['cancel'],
                       gdd=(cheb(p1, nf[1]) - cheb(p0, nf[1])) if nf else None, goal_wait=(nf[0] - r['r']) if nf else None,
                       hdd=y['ehw'] - x['hw'], L=y['L'], wd1=y['wd1'])
            out.append(dict(cohort=g['cohort'], game=g['game'], group=g['group'], map=g['map'], round=r['r'],
                            actor=int(aid), type=x['type'], x=feat, y=lab))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    p.add_argument('--cohorts', nargs='+', default=FIT + HELD)
    p.add_argument('--jobs', type=int, default=6)
    a = p.parse_args()
    if Path(a.out).exists():
        raise SystemExit(f'refusing to overwrite {a.out}')
    n = 0
    with gzip.open(a.out, 'wt') as f, mp.Pool(a.jobs) as pool:
        for c in a.cohorts:
            with gzip.open(ROWS / f'{c}-rows-v1.jsonl.gz', 'rt') as fh:
                for res in pool.imap_unordered(one, fh, chunksize=2):
                    for row in res:
                        f.write(json.dumps(row, separators=(',', ':')) + '\n'); n += 1
            print(c, n, flush=True)


if __name__ == '__main__':
    main()
