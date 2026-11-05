"""Second-pass detectors that need other champions' state: channel snipes (locks and stuns on channelling enemies),
teleport and ward destinations, kiting, and what each priority value means (state at the set).

    python3 -I research/micro-2026-11-05/detect2.py replays/micro/ladder --out research/micro-2026-11-05/out [--procs 24]
"""
import argparse
import collections
import glob
import gzip
import json
import multiprocessing as mp
import os

CH = ['Ryth', 'Vesper', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HoR']
# (type, slot) of stun abilities (Marcella's reset makes her next attack stun: counted on the attack).
STUN = {(0, 0), (6, 0), (11, 1), (9, 0), (12, 1), (3, 1)}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def analyse(path):
    d = json.load(gzip.open(path))
    teams, roster, gk = d['teams'], {c['id']: c for c in d['roster']}, d['key']
    W, H = d['map']['w'], d['map']['h']
    bush = None
    altars = [tuple(a) for a in d['map']['altars']]
    st = {(row[0], row[1]): row for rows in d['rounds'] for row in rows}
    C = collections.defaultdict(collections.Counter)
    EX = collections.defaultdict(list)
    PV = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))  # team -> value -> stats

    def ex(team, tag, r, note=''):
        if len(EX[(team, tag)]) < 6:
            EX[(team, tag)].append(f'{gk} r{r} {note}'.strip())

    # Live channel state from acts: id -> channel type (1 recall, 2 tribute, 3 teleport) as of the current step.
    chan = {}
    pos = {}
    for rows in d['rounds'][:1]:
        for row in rows:
            pos[row[1]] = (row[2], row[3])
    last_r = 0
    for a in d['acts']:
        r, cid = a['r'], a['a']
        if r != last_r:
            last_r = r
            for c in roster:
                s = st.get((r, c))
                if s:
                    pos[c] = (s[2], s[3])
                    chan[c] = s[14] if s[15] > 0 else 0
        c = roster[cid]
        side = c['team']
        team = teams[side]
        typ = CH[c['type']]
        if 'af' in a:
            pos[cid] = (a['af'][0], a['af'][1])
            chan[cid] = a['af'][7] if a['af'][8] > 0 else 0
        foes = [o for o, oc in roster.items() if oc['team'] != side]
        if a['k'] == 20:  # lock place
            t = tuple(a['to'])
            tributing = [o for o in foes if chan.get(o) == 2 and pos.get(o, (-9, -9))[0] >= 0 and cheb(pos[o], t) <= 1]
            C[team]['lock'] += 1
            if tributing:
                C[team]['lock_on_enemy_tribute'] += 1
                bag = sum(st.get((r, o), [0] * 9)[8] for o in tributing)
                C[team]['lock_snipe_gems'] += bag
                ex(team, 'lock_snipe', r, f'{typ} bag {bag}')
        if a['k'] in (5, 6) and a.get('hits'):
            stun = a['k'] == 6 and (c['type'], a.get('slot')) in STUN
            for hid, dmg, ally in a['hits']:
                if ally:
                    continue
                ch = chan.get(hid, 0)
                if ch:
                    C[team][f'hit_channel{ch}'] += 1
                    if stun:
                        C[team][f'stun_channel{ch}'] += 1
                        if ch == 2:
                            ex(team, 'stun_tribute', r, f'{typ} -> {CH[roster[hid]["type"]]}')
        if a['k'] == 6 and (c['type'], a.get('slot')) in STUN:
            C[team]['stun_casts'] += 1
        if a['k'] == 21:  # teleport channel start: destination
            t = tuple(a['to'])
            C[team]['tp'] += 1
            near_foe = min((cheb(pos[o], t) for o in foes if pos.get(o, (-1, -1))[0] >= 0), default=99)
            near_alt = min((cheb(x, t) for x in altars), default=99)
            spawn = d['map']['spawn'][side]
            home = cheb(t, ((spawn['minX'] + spawn['maxX']) // 2, (spawn['minY'] + spawn['maxY']) // 2))
            C[team]['tp_foe<=3'] += near_foe <= 3
            C[team]['tp_altar<=1'] += near_alt <= 1
            gems = a['b'][6]
            C[team]['tp_gems'] += gems
            hp = a['b'][2] / max(1, a['b'][3])
            C[team]['tp_lowhp'] += hp < 0.4
            ex(team, 'tp', r, f'{typ} gems {gems} hp {hp:.2f} foe {near_foe} altar {near_alt}')
        if a['k'] == 14:  # ward
            C[team]['ward'] += 1
            near_foe = min((cheb(pos[o], tuple(a['to'])) for o in foes if pos.get(o, (-1, -1))[0] >= 0), default=99)
            C[team]['ward_foe<=8'] += near_foe <= 8
        if a['k'] == 9:
            s = st.get((r, cid))
            if s:
                v = a['pr']
                me = (s[2], s[3])
                nf = min((cheb(pos[o], me) for o in foes if pos.get(o, (-1, -1))[0] >= 0 and st.get((r, o), [0] * 7)[6]), default=99)
                P = PV[team][v]
                P['n'] += 1
                P['hp%'] += 100 * s[4] / max(1, s[5])
                P['gems'] += s[8]
                P['foe<=4'] += nf <= 4
                P['foe<=8'] += nf <= 8
                P['dead'] += 1 - s[6]
                P['chan'] += s[14] > 0
        # Kiting: a ranged champion attacks a champion then walks away from it in the same turn.
    return dict(C=C, EX=EX, PV={t: {v: dict(c) for v, c in m.items()} for t, m in PV.items()}, teams=teams)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--out', required=True)
    ap.add_argument('--procs', type=int, default=24)
    o = ap.parse_args()
    files = sorted(glob.glob(os.path.join(o.dir, '*.json.gz')))
    C = collections.defaultdict(collections.Counter)
    EX = collections.defaultdict(list)
    PV = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    G = collections.Counter()
    with mp.Pool(o.procs) as pool:
        for res in pool.imap_unordered(analyse, files, chunksize=8):
            for t in res['teams']:
                G[t] += 1
            for t, c in res['C'].items():
                C[t].update(c)
            for k, L in res['EX'].items():
                if len(EX[k]) < 8:
                    EX[k].extend(L[:8 - len(EX[k])])
            for t, m in res['PV'].items():
                for v, c in m.items():
                    PV[t][v].update(c)
    # Priority-value tables: top 12 values per team with >= 2000 sets and few distinct values.
    lines = []
    for t in sorted(PV, key=lambda t: -G[t]):
        tot = sum(c['n'] for c in PV[t].values())
        if tot < 2000 or len(PV[t]) > 60:
            continue
        lines.append(f'### {t} ({tot} sets, {len(PV[t])} values)\n')
        lines.append('| value | share | hp% | gems | foe<=4 | foe<=8 | dead | channelling |')
        lines.append('|---|---|---|---|---|---|---|---|')
        for v, c in sorted(PV[t].items(), key=lambda kv: -kv[1]['n'])[:12]:
            n = c['n']
            lines.append(f"| {v} | {n / tot:.2f} | {c['hp%'] / n:.0f} | {c['gems'] / n:.1f} | {c['foe<=4'] / n:.2f} | {c['foe<=8'] / n:.2f} | {c['dead'] / n:.2f} | {c['chan'] / n:.2f} |")
        lines.append('')
    os.makedirs(o.out, exist_ok=True)
    open(os.path.join(o.out, 'priority_values.md'), 'w').write('\n'.join(lines))
    json.dump({'games': G, 'C': C, 'EX': {f'{k[0]}|{k[1]}': v for k, v in EX.items()}},
              open(os.path.join(o.out, 'summary2.json'), 'w'), indent=0)
    print(len(files), 'games')


if __name__ == '__main__':
    main()
