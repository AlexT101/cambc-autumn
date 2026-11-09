"""Escape-plan diagnostics: hit layers (ESH) against the damage actually taken in each interval.
usage: esc_diag.py EXTRACT_DIR BOTNAME   (games of a bot built with esc_diag_trace.patch, debug build)"""
import sys, json, gzip, zipfile, os
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

NAMES = ['Ryth', 'Vesper', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HoR']
RANGED = {1, 3, 5, 6, 8, 11}
SIDE = 15


def parse_stdout(src, letter):
    z = zipfile.ZipFile(src)
    lines = z.read(f'team-{letter}.stdout').decode(errors='replace').replace('\x00', '').splitlines()
    esh, esk, ese, esr, esd = [], defaultdict(list), defaultdict(list), [], []
    for l in lines:
        p = l.split()
        if not p: continue
        if p[0] == 'ESH' and len(p) == 6 + 5:
            try:
                r, h, ox, oy, steps = map(int, p[1:6])
                layers = []
                for k in range(5):
                    hx = p[6 + k]
                    layers.append([int(hx[4 * y:4 * y + 4], 16) for y in range(SIDE)])
            except ValueError:
                continue
            esh.append((r, h, ox, oy, steps, layers))
        else:
          try:
            if p[0] == 'ESK':
                esk[(int(p[1]), int(p[2]))].append(list(map(int, p[3:])))
            elif p[0] == 'ESE':
                ese[(int(p[1]), int(p[2]))].append(list(map(int, p[3:])))
            elif p[0] == 'ESR':
                q = p[1:]; int(q[0]); int(q[1])
                if q[2] == 'C': [int(x) for x in q[3:11]]
                esr.append(q)
            elif p[0] == 'ESD':
                esd.append(p[1:])
          except (ValueError, IndexError):
            pass
    return esh, esk, ese, esr, esd


def one(args):
    ex, g, bot = args
    meta = json.load(open(f"{ex}/{g['dir']}/meta.json"))
    R = json.load(gzip.open(f"{ex}/{g['dir']}/rounds.json.gz"))
    ev = [json.loads(l) for l in gzip.open(f"{ex}/{g['dir']}/events.jsonl.gz", 'rt')]
    M = json.load(open(f"{ex}/maps/{g['mapHash']}.json"))
    ridx = {r: i for i, r in enumerate(R['round'])}
    ch = {c['id']: c for c in R['champions']}
    type_of = {c['id']: c['type'] for c in meta['champions']}
    team_of = {c['id']: c['team'] for c in meta['champions']}
    out = Counter()
    miss = Counter()
    rows = []
    for t in (0, 1):
        if g['teams'][t] != bot: continue
        try:
            esh, esk, ese, esr, esd = parse_stdout(g['source'], 'ab'[t])
        except KeyError:
            continue
        sp = M['spawn'][t]
        mine = {c for c in team_of if team_of[c] == t}
        tus = defaultdict(dict)  # h -> r -> t
        dmg = defaultdict(list)  # h -> [(r, t, amount, src)]
        stuns = defaultdict(list)
        for e in ev:
            a = e.get('a')
            if a in mine and e['t'] >= 0:
                tus[a].setdefault(e['r'], e['t'])
            k = e['k']
            if k in ('attack', 'cast'):
                for v in e.get('stun', []) or []:
                    if v in mine: stuns[v].append((e['r'], e['t'], NAMES[type_of[a]] + '-' + e.get('ab', 'attack')))
                for v, amt in e.get('dmg', []) or []:
                    if v in mine and amt > 0:
                        src = (('ranged-' if type_of[a] in RANGED else 'melee-') + NAMES[type_of[a]]) if k == 'attack' else e.get('ab', 'cast') + '-' + NAMES[type_of[a]]
                        dmg[v].append((e['r'], e['t'], amt, src, a))
            elif k == 'camp_attack':
                if e.get('tgt') in mine and e.get('dmg', 0) > 0: dmg[e['tgt']].append((e['r'], -1, e['dmg'], 'camp', None))
                for v, amt in e.get('xdmg', []) or []:
                    if v in mine: dmg[v].append((e['r'], -1, amt, 'camp', None))
        for c in mine:
            for r in list(tus[c]):
                pass
        for e in esr:
            out['esr_' + e[2]] += 1
            r, h = int(e[0]), int(e[1])
            tot = 0
            for rk in range(r, r + 3):
                t0 = tus[h].get(rk); t1 = tus[h].get(rk + 1)
                if t0 is None or t1 is None: break
                tot += sum(d[2] for d in dmg[h] if (d[0] == rk and d[1] > t0) or (d[0] == rk + 1 and d[1] < t1))
            out['esr_' + e[2] + '_dmg3'] += tot
            out['esr_' + e[2] + '_hit3'] += 1 if tot > 0 else 0
            if e[2] == 'C' and e[5] == '1':
                key = f'Cn_now{e[8]}_full{e[9]}_slack{e[10]}'
                out[key] += 1; out[key + '_dmg3'] += tot
            if e[2] == 'C':
                rank, now, full, slack = int(e[7]), int(e[8]), int(e[9]), int(e[10])
                out[f'C_now{now}_full{full}'] += 1
        for e in esd:
            out['esd'] += 1
        for (r, h, ox, oy, steps, layers) in esh:
            out['builds'] += 1
            info = ese.get((r, h), [])
            modelled = {x[0] for x in info}
            stunned = sum(1 for x in info if x[3] == 1 and x[1] == 1)
            if stunned: out['builds_with_stunned_pursuer'] += 1
            kinds = esk.get((r, h), [])
            if any(k[0] == 1 for k in kinds): out['builds_ranged'] += 1
            resets = [x for x in info if x[1] == 1 and x[4] == 1 and 1 <= x[5] <= 5]
            if resets: out['builds_ranged_reset_ready'] += 1
            nvis = sum(1 for x in info if x[1] == 1)
            out[f'builds_nvis{min(nvis, 3)}'] += 1
            for k in range(1, 6):
                rk = r + k - 1
                i = ridx.get(rk)
                if i is None: break
                A = ch[h]
                if not A['alive'][i] or A['x'][i] is None or A['x'][i] < 0: break
                x, y = A['x'][i], A['y'][i]
                if sp['minX'] <= x <= sp['maxX'] and sp['minY'] <= y <= sp['maxY']: break
                wx, wy = x - ox, y - oy
                if not (0 <= wx < SIDE and 0 <= wy < SIDE): break
                pred = layers[k - 1][wy] >> wx & 1
                t0 = tus[h].get(rk); t1 = tus[h].get(rk + 1)
                if t0 is None or t1 is None: break
                got = [d for d in dmg[h] if (d[0] == rk and d[1] > t0) or (d[0] == rk + 1 and d[1] < t1)]
                st = [d for d in stuns[h] if (d[0] == rk and d[1] > t0) or (d[0] == rk + 1 and d[1] < t1)]
                if st:
                    out[f'k{k}_stunned'] += 1
                    for d in st: miss[('stun', k, d[2])] += 1
                if len({d[4] for d in got if d[4] is not None}) >= 2: out[f'k{k}_multi_hit'] += 1
                if got: out[f'k{k}_any_hit'] += 1
                hit = 1 if got else 0
                out[f'k{k}_p{pred}_h{hit}'] += 1
                if hit and not pred:
                    for d in got:
                        miss[('mdmg', k, 'camp' if d[4] is None else 'champ')] += d[2]
                        src = d[3]
                        who = 'camp' if d[4] is None else ('modelled' if d[4] in modelled else 'unmodelled')
                        miss[(k, src, who)] += 1
                        miss[('dmg', k)] += d[2]
                if hit and pred:
                    out[f'k{k}_dmg_pred'] += sum(d[2] for d in got)
    return out, miss


def main():
    ex, bot = sys.argv[1], sys.argv[2]
    idx = json.load(open(f'{ex}/index.json'))
    games = [g for g in idx['games'] if bot in g['teams'] and g.get('ok', True)]
    tot, miss = Counter(), Counter()
    with ProcessPoolExecutor(16) as pool:
        for o, m in pool.map(one, [(ex, g, bot) for g in games]):
            tot.update(o); miss.update(m)
    print('games', len(games))
    for k in sorted(tot): print(k, tot[k])
    print('--- misses (k, source, attacker)')
    for k, v in sorted(miss.items(), key=lambda kv: -kv[1])[:60]: print(k, v)


if __name__ == '__main__':
    main()
