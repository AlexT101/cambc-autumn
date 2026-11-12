"""Focus over time, per team: does a team keep striking the target it struck before, and does its damage in an
engagement go to enemies that die?

- Persistence: for a team's striking round r' following its striking round r (r' - r <= 2), with r's most-hit
  target X still alive and an option (seen, within conv.OPT at the previous round's end) of some striker at r'
  together with another enemy: the share of r' where X is again the most-hit target.
- Engagements: a team's striking rounds with gaps of at most GAP rounds. Per engagement with 2+ strikers in all:
  top-target share of its champion damage, the share on enemies that died during it (+W rounds), kills.

py persist.py live | EXTRACT_DIR...
"""
import gzip, json, os, sys
from collections import Counter, defaultdict
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conv import OPT, W, cheb, live_jobs, batch_jobs

GAP = 4


def one(job):
    d, labels = job
    try:
        meta = json.load(open(d + '/meta.json'))
        R = json.load(gzip.open(d + '/rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    except Exception:
        return None
    team = {c['id']: c['team'] for c in meta['champions']}
    names = {c['id']: c['name'] for c in meta['champions']}
    pick = {c['id']: c['id'] for c in meta['champions']}
    for t in (0, 1):
        cass = [c for c in team if team[c] == t and names[c] in ('Cassi', 'Issac')]
        if len(cass) == 2: pick[max(cass)] = min(cass)
    idx = {r: i for i, r in enumerate(R['round'])}
    ch = {c['id']: c for c in R['champions']}
    hits = defaultdict(lambda: defaultdict(Counter))
    deaths = defaultdict(set)
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('dmg'):
            a = e['a']
            for v, amt in e['dmg']:
                if v in team and team[v] != team[a] and amt > 0: hits[e['r']][a][pick[v]] += amt
        elif e['k'] == 'death' and e.get('linked') is None:
            deaths[e['r']].add(pick[e['v']])
    out = {}
    for t in (0, 1):
        lab = labels[t]
        if lab is None: continue
        C = Counter()
        rounds = sorted(r for r, by in hits.items() if any(team[a] == t for a in by))
        modal = {}
        for r in rounds:
            tot = Counter()
            for a, tg in hits[r].items():
                if team[a] == t: tot.update(tg)
            modal[r] = (max(tot, key=tot.get), tot)
        prev = None
        for r in rounds:
            if prev is not None and r - prev <= 2:
                X = modal[prev][0]
                i = idx.get(r - 1); ri = idx.get(r)
                alive = i is not None and any(ch[c]['alive'][i] for c in ch if pick[c] == X)
                if alive and ri is not None:
                    ok = False
                    for a in hits[r]:
                        if team[a] != t or ch[a]['x'][i] is None or ch[a]['x'][i] < 0: continue
                        p = (ch[a]['x'][i], ch[a]['y'][i])
                        o = {pick[v] for v in (ch[a]['sees'][ri] or []) if ch[v]['alive'][i] and ch[v]['x'][i] is not None and cheb(p, (ch[v]['x'][i], ch[v]['y'][i])) <= OPT}
                        if X in o and len(o) >= 2: ok = True
                    if ok:
                        C['pp'] += 1; C['pp_same'] += modal[r][0] == X
            prev = r
        # engagements
        eng = []
        for r in rounds:
            if eng and r - eng[-1][-1] <= GAP: eng[-1].append(r)
            else: eng.append([r])
        for E in eng:
            strikers = {a for r in E for a in hits[r] if team[a] == t}
            if len(strikers) < 2: continue
            dmg = Counter()
            for r in E: dmg.update(modal[r][1])
            dead = set().union(*(deaths.get(rr, set()) for rr in range(E[0], E[-1] + W + 1)))
            dead = {x for x in dead if x in dmg}
            total = sum(dmg.values())
            C['e'] += 1; C['e_top'] += max(dmg.values()) / total
            C['e_use'] += sum(v for k, v in dmg.items() if k in dead) / total
            C['e_kills'] += len(dead); C['e_targets'] += len(dmg)
            C['e_rounds'] += len(E)
        out[lab] = C
    return out


def main():
    jobs = live_jobs() if sys.argv[1:] == ['live'] else [j for ex in sys.argv[1:] for j in batch_jobs(ex)]
    with Pool(int(os.environ.get('NPROC', 8))) as p: res = [x for x in p.map(one, jobs, chunksize=4) if x]
    tot = defaultdict(Counter)
    for o in res:
        for lab, C in o.items(): tot[lab].update(C)
    print(f'GAP={GAP} OPT={OPT} W={W}')
    for lab, C in sorted(tot.items()):
        e = C['e'] or 1
        print(f"{lab:18s} persistence {100 * C['pp_same'] / max(1, C['pp']):.1f}% of {C['pp']} | engagements {C['e']}: top-target share {100 * C['e_top'] / e:.1f}%, "
              f"damage on enemies that died {100 * C['e_use'] / e:.1f}%, targets {C['e_targets'] / e:.2f}, kills {C['e_kills'] / e:.3f}, striking rounds {C['e_rounds'] / e:.1f}")


if __name__ == '__main__':
    main()
