"""Cohesion, crews, tributes and deaths per team, from extracted replays (extract.mjs).

    py research/mx-tethys/scripts/cohesion.py ANALYSIS_ROOT BATCH_DIR [--by-bot CANDNAME] [--max N]

Rows per team-game: nearest-ally distance and largest-cluster share (alive, off own spawn, linked within 8),
crew size on cleared groups by kind (distinct team champions that damaged the group since its last respawn),
tributes (count, mean gems), deaths (with allies/enemies within 8 of the victim), captures and gems by phase.
Sides: winner/loser (mirror) or CAND/REF with --by-bot.
"""
import argparse
import gzip
import json
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def kind_of(types):
    t = set(types)
    if 'Monolith' in t: return 'Monolith'
    if 'Golem' in t: return 'Golem'
    if 'Elk' in t: return 'Elk'
    if 'Wolf' in t: return 'Wolf'
    return 'Cluster'


def game(d):
    d = Path(d)
    try:
        meta = json.loads((d / 'meta.json').read_text())
        mp = json.loads((d / meta['mapFile']).resolve().read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    winner = meta['result']['winner']
    champs = R['champions']
    n = len(R['round'])
    team_of = {c['id']: c['team'] for c in champs}
    types = {c['id']: c['name'] for c in meta['champions']}
    rix = {r: i for i, r in enumerate(R['round'])}
    cidx = {c['id']: j for j, c in enumerate(champs)}
    spawn = mp['spawn']
    def on_spawn(t, x, y):
        s = spawn[t]
        return s['minX'] <= x <= s['maxX'] and s['minY'] <= y <= s['maxY']
    gkind = {g['id']: kind_of(g['types']) for g in mp['groups']}
    out = {t: defaultdict(float) for t in (0, 1)}
    for t in (0, 1):
        out[t]['win'] = 1.0 if winner == t else 0.0
        out[t]['rounds'] = n
        out[t]['bodies'] = sum(1 for c in champs if c['team'] == t)
    # cohesion, sampled every 2 rounds
    for i in range(0, n, 2):
        r = R['round'][i]
        ph = 'e' if r <= 300 else 'l'
        pos = {0: [], 1: []}
        for c in champs:
            if c['alive'][i] and c['x'][i] is not None:
                pos[c['team']].append((c['id'], c['x'][i], c['y'][i]))
        for t in (0, 1):
            P = [(cid, x, y) for cid, x, y in pos[t] if not on_spawn(t, x, y)]
            if len(pos[t]) < 2:
                continue
            for cid, x, y in P:
                nd = min(cheb((x, y), (x2, y2)) for c2, x2, y2 in pos[t] if c2 != cid)
                out[t]['nd_' + ph] += nd
                out[t]['ndn_' + ph] += 1
                ne = sum(1 for _, x2, y2 in pos[1 - t] if cheb((x, y), (x2, y2)) <= 8)
                na = sum(1 for c2, x2, y2 in pos[t] if c2 != cid and cheb((x, y), (x2, y2)) <= 8)
                out[t]['alone_' + ph] += (na == 0)
                out[t]['outnum_' + ph] += (ne > na + 1)
            # largest cluster share among all alive (spawn included)
            Q = pos[t]
            seen = set(); best = 0
            for k in range(len(Q)):
                if k in seen: continue
                stack = [k]; comp = 0; seen.add(k)
                while stack:
                    j = stack.pop(); comp += 1
                    for m in range(len(Q)):
                        if m not in seen and cheb(Q[j][1:], Q[m][1:]) <= 8:
                            seen.add(m); stack.append(m)
                best = max(best, comp)
            out[t]['clus_' + ph] += best / len(Q)
            out[t]['clusn_' + ph] += 1
    # crews: damage by champion to group since respawn
    camp_group = {c['id']: c['group'] for c in mp['camps']}
    hitters = defaultdict(set)
    for e in ev:
        k = e['k']
        if k in ('attack', 'cast') and e.get('cdmg'):
            a = e.get('a')
            for cid, amt in e['cdmg']:
                g = camp_group.get(cid)
                if g is not None and a in team_of:
                    hitters[g].add(a)
        elif k == 'group_clear':
            g = e['g']
            hs = hitters.pop(g, set())
            if not hs: continue
            byt = defaultdict(int)
            for a in hs: byt[team_of[a]] += 1
            for t, c in byt.items():
                kd = gkind.get(g, 'Cluster')
                ph = 'e' if e['r'] <= 300 else 'l'
                out[t][f'crew_{kd}_{ph}'] += c
                out[t][f'crewn_{kd}_{ph}'] += 1
        elif k == 'group_respawn':
            hitters.pop(e['g'], None)
        elif k == 'tribute_end':
            t = team_of.get(e['a'])
            if t is not None:
                out[t]['trib_n'] += 1
                out[t]['trib_g'] += e['gems']
        elif k == 'death':
            v = e['v']; t = team_of.get(v)
            if t is None: continue
            out[t]['deaths'] += 1
            out[t]['death_' + str(types.get(v))] += 1
            out[t]['dgems'] += e.get('gems', 0) or 0
            if 'camp' in e and e.get('camp') is not None: out[t]['campdeaths'] += 1
            if types.get(v) == 'Prism': out[t]['prism_deaths'] += 1
            i = rix.get(e['r'] - 1)
            if i is not None and champs[cidx[v]]['x'][i] is not None:
                vp = (champs[cidx[v]]['x'][i], champs[cidx[v]]['y'][i])
                na = ne = 0
                for c in champs:
                    if c['id'] == v or not c['alive'][i] or c['x'][i] is None: continue
                    if cheb(vp, (c['x'][i], c['y'][i])) <= 8:
                        if c['team'] == t: na += 1
                        else: ne += 1
                out[t]['d_alone'] += (na == 0)
                out[t]['d_outnum'] += (ne > na + 1)
                out[t]['d_even'] += (ne <= na + 1 and ne >= na)
                out[t]['d_ahead'] += (ne < na)
                out[t]['d_na'] += na; out[t]['d_ne'] += ne
            if (e.get('gems') or 0) >= 50: out[t]['d_bag50'] += 1
        elif k == 'capture':
            for cid, gm, gd in e['shares']:
                t = team_of.get(cid)
                if t is None: continue
                ph = 'e' if e['r'] <= 300 else 'l'
                out[t]['capg_' + ph] += gm
                out[t]['capgold_' + ph] += gd
                out[t]['capshares'] += 1
    # tributed at 300/600
    for t in (0, 1):
        g = R['gems'][t]
        for rr in (150, 300, 600):
            out[t][f'trib@{rr}'] = g[min(rr, n) - 1]
    return {'teams': meta['teams'], 'rows': out, 'winner': winner}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('batch')
    ap.add_argument('--by-bot')
    ap.add_argument('--max', type=int, default=0)
    args = ap.parse_args()
    bname = Path(args.batch).name
    dirs = []
    rowteams = {}
    for dd in sorted(Path(args.root).iterdir()):
        mf = dd / 'meta.json'
        if not mf.exists(): continue
        try:
            m = json.loads(mf.read_text())
        except Exception:
            continue
        srcs = [s.get('source', '') for s in (m.get('sources') or [])] + [m.get('source') or '']
        if not any(bname in s for s in srcs): continue
        dirs.append(dd); rowteams[dd] = [t.get('name') for t in m.get('teams', [])]
    if args.max: dirs = dirs[:args.max]
    agg = defaultdict(lambda: defaultdict(float))
    cnt = defaultdict(int)
    with ProcessPoolExecutor(32) as ex:
        for d, res in zip(dirs, ex.map(game, dirs, chunksize=8)):
            if not res: continue
            for t in (0, 1):
                if args.by_bot:
                    names = rowteams[d] or [x.get('name') for x in res['teams']]
                    side = 'CAND' if args.by_bot in str(names[t]) else 'REF'
                else:
                    side = 'W' if res['winner'] == t else 'L'
                for k, v in res['rows'][t].items():
                    agg[side][k] += v
                cnt[side] += 1
    sides = sorted(agg)
    print('games per side', dict(cnt))
    keys = sorted(set(k for s in sides for k in agg[s]))
    def ratio(s, num, den):
        dn = agg[s].get(den, 0)
        return agg[s].get(num, 0) / dn if dn else float('nan')
    print('metric', *sides, sep='\t')
    for lab, num, den in [('nearest ally r<=300', 'nd_e', 'ndn_e'), ('nearest ally r>300', 'nd_l', 'ndn_l'),
                          ('alone(0 allies<=8) r<=300', 'alone_e', 'ndn_e'), ('alone r>300', 'alone_l', 'ndn_l'),
                          ('outnumbered r<=300', 'outnum_e', 'ndn_e'), ('outnumbered r>300', 'outnum_l', 'ndn_l'),
                          ('largest cluster r<=300', 'clus_e', 'clusn_e'), ('largest cluster r>300', 'clus_l', 'clusn_l'),
                          ('gems/tribute', 'trib_g', 'trib_n')]:
        print(lab, *[f'{ratio(s, num, den):.3f}' for s in sides], sep='\t')
    for kd in ('Monolith', 'Golem', 'Elk', 'Wolf', 'Cluster'):
        for ph in 'el':
            print(f'crew {kd} {ph}', *[f"{ratio(s, f'crew_{kd}_{ph}', f'crewn_{kd}_{ph}'):.2f} ({agg[s].get(f'crewn_{kd}_{ph}', 0) / max(1, cnt[s]):.1f}/g)" for s in sides], sep='\t')
    dk = sorted(set(k for s in sides for k in agg[s] if k.startswith('death_')))
    for k in dk:
        print(k, *[f'{agg[s].get(k, 0) / max(1, cnt[s]):.2f}' for s in sides], sep='\t')
    for k in ('win', 'rounds', 'bodies', 'trib_n', 'deaths', 'd_alone', 'd_outnum', 'd_even', 'd_ahead', 'd_na', 'd_ne', 'd_bag50', 'campdeaths', 'prism_deaths', 'dgems', 'capg_e', 'capg_l', 'capgold_e', 'capgold_l', 'capshares', 'trib@150', 'trib@300', 'trib@600'):
        print(k, *[f'{agg[s].get(k, 0) / max(1, cnt[s]):.2f}' for s in sides], sep='\t')


if __name__ == '__main__':
    main()
