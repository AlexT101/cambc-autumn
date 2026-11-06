"""Contact turns and walking disengagement (ENGAGE.md section 2).

Opportunity: a free Fish turn (alive, unstunned, off spawn, no tribute/teleport channel) that
completes alive with a visible enemy within 3 at its start. Causal features `x`: the actor's start
view, its own memory, and allied liveness (readable by Fish): ally deaths in the last 10 rounds.
COMBAT.md's acceptability (kill available, or hp > 0.49 and danger at the start tile <= 0.28) is
computed at the start tile as a baseline input.

Labels `y`: `retreat` = the actor's own end tile after its next 3 turns (this one included) is at
least 2 farther (Chebyshev) from the nearest enemy's start tile, it hit no champion in those turns,
and no recall arrived (spawn reached by walking counts). Retreat episodes are followed up to 40 turns
to the first of: camp hit (farm; same static group as its last camp hit before?), tribute start,
on spawn, death, champion hit (re-engage), or timeout, with the 3-turn direction measures.

  python3 tools/fish/engage_retreat.py replays/fish-engage/retreat-v2.jsonl.gz [--cohorts ...]
(v1 lacked the tiles p0, e0, p3 in `dir`.)
"""
import argparse
import gzip
import json
import multiprocessing as mp
from pathlib import Path

from breadth import static_groups
from combat_common import COHORTS, one_turn_damage
from engage_common import FIT, HELD, ROWS, free

CACHE = {c[0]: c[2] for c in COHORTS}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def champ(e):
    return dict(type=e['type'], strength=e['str'], focus=e['foc'], cd=e['cd'], hp=e['hp'], maxHp=e['mhp'])


def one(line):
    g = json.loads(line)
    with gzip.open(Path(CACHE[g['cohort']]) / f"{g['game']}.json.gz") as f:
        m = json.load(f)['map']
    altars = [tuple(a) for a in m['altars']]
    bush = set(map(tuple, m['bushes']))
    groups, at = static_groups(m)
    # Allied death rounds (liveness is readable for every champion).
    deaths = []
    for aid, rows in g['actors'].items():
        for p, q in zip(rows, rows[1:]):
            if p['alive'] and not q['alive']:
                deaths.append((q['r'], int(aid)))
    out = []
    for aid, rows in g['actors'].items():
        aid = int(aid)
        for i, r in enumerate(rows):
            x, y = r.get('x'), r.get('y')
            if not (x and y and free(x) and x['E']) or x['d1'] > 3:
                continue
            e = x['E'][0]; E0 = (e['x'], e['y']); p0 = (x['x'], x['y'])
            eh = x['hp'] + x['sh']
            danger = sum(0 if q['stn'] else one_turn_damage(champ(q), q['d']) for q in x['E']) / max(eh, 1)
            kill = any(q['mine'] >= q['hp'] + q['sh'] for q in x['E'])
            hpf = x['hp'] / x['mhp']
            acceptable = kill or (hpf > 0.49 and danger <= 0.28)
            allies8 = [a for a in x['A'] if a['d'] <= 8]
            near_e = [q for q in x['E'] if q['d'] <= 8]
            ratio = (eh + sum(a['hp'] + a['sh'] for a in allies8)) / max(1, sum(q['hp'] + q['sh'] for q in near_e))
            ad10 = sum(1 for dr, who in deaths if who != aid and 0 <= r['r'] - dr <= 10)
            prev = rows[i - 1] if i else None
            prev_ne = len(prev['x']['E']) if prev and prev.get('x') and prev['r'] == r['r'] - 1 else None
            feat = dict(type=x['type'], ranged=x['ranged'], hpf=round(hpf, 3), gems=x['gems'], gold=x['gold'],
                        d1=x['d1'], n_e=len(near_e), n_e3=sum(1 for q in x['E'] if q['d'] <= 3), n_a8=len(allies8),
                        n_a3=sum(1 for a in x['A'] if a['d'] <= 3), ratio=round(ratio, 3), danger=round(danger, 3),
                        kill=kill, acceptable=acceptable, ehpf=round(e['hp'] / e['mhp'], 3), egems=e['gems'],
                        ech=e['ch'], esp=e['esp'], ally_deaths10=ad10, new_enemies=(len(x['E']) - prev_ne) if prev_ne is not None else None,
                        capturing=x['gst'] == 2, aggro=x['aggro'], hw=x['hw'], ehw=x['ehw'], round=r['r'],
                        so=x['so'], sx=x['sx'], lc=x['lc'], ct=x['ct'] if x['ch'] == 1 else 0, ealive=x['ealive'])
            # 3-turn label.
            seq = rows[i:i + 3]
            ok = len(seq) == 3 and all(q.get('x') and q.get('y') and q['r'] == r['r'] + k for k, q in enumerate(seq))
            lab = dict(valid=ok)
            if ok:
                hit = any(q['y']['hitc'] for q in seq)
                p3 = (seq[-1]['y']['ex'], seq[-1]['y']['ey'])
                recall_arrival = any(seq[k]['x']['home'] and seq[k - 1]['y']['ehw'] != 0 for k in (1, 2))
                gain = cheb(p3, E0) - cheb(p0, E0)
                lab.update(gain=gain, hit3=hit, recall_arrival=recall_arrival,
                           retreat=gain >= 2 and not hit and not recall_arrival,
                           stay=not hit and gain <= 0, hit_now=bool(y['hitc']))
                if lab['retreat']:
                    # Direction over the 3 turns.
                    a0 = min(x['A'], key=lambda a: a['d']) if x['A'] else None
                    lab['dir'] = dict(
                        dhw=seq[-1]['y']['ehw'] - x['hw'],
                        dally=(cheb(p3, (a0['x'], a0['y'])) - a0['d']) if a0 else None, ally_d0=a0['d'] if a0 else None,
                        dehw=seq[-1]['y']['eehw'] - x['ehw'],
                        dalt=min((cheb(p3, a) for a in altars), default=None) - min((cheb(p0, a) for a in altars), default=0) if altars else None,
                        bush=p3 in bush, bush0=p0 in bush, p0=p0, e0=E0, p3=p3)
                    # Follow-up.
                    last_g = x['lcamp'][1] if x['lcamp'] else None
                    end = ('timeout', None, None)
                    for k, q in enumerate(rows[i + 1:i + 41]):
                        qx, qy = q.get('x'), q.get('y')
                        if not q['alive'] or not qx:
                            end = ('death', k + 1, None); break
                        if qx['home']:
                            end = ('home', k + 1, None); break
                        if not qy:
                            continue
                        if qy['hitc']:
                            end = ('reengage', k + 1, None); break
                        if qy['submit'] and qy['ech'] == 2:
                            end = ('tribute', k + 1, None); break
                        if qy['camp']:
                            end = ('farm', k + 1, dict(same=last_g in qy['camp'], last=last_g, grp=qy['camp'],
                                                       far=cheb((qy['ex'], qy['ey']), p0))); break
                    lab['end'] = end
            out.append(dict(cohort=g['cohort'], game=g['game'], group=g['group'], map=g['map'], round=r['r'],
                            actor=aid, type=x['type'], x=feat, y=lab))
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
