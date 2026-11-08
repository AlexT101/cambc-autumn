"""Position-sharing value from extracted local games (research/comms-positions-2026-11-07).

py analyse.py EXTRACT_DIR [--batch BATCH_DIR]

Per team of each game (both are ocean here):
- deaths to champions by what the victim and its team saw of the damagers before the first hit;
- enemy carriers (bag >= 40) seen by one of ours while another, unseeing, is within 10;
- turns where an enemy within 8 (true positions) is unseen by us but seen by a teammate this round or last;
- with --batch, Willow's WF markers (cm-probe's stdout): how its follow target was known, and the error.
"""
import gzip, json, os, sys, zipfile, collections, glob

def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

def game(d, tot):
    meta = json.load(open(os.path.join(d, 'meta.json')))
    R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
    ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
    champs = R['champions']
    team = {c['id']: c['team'] for c in champs}
    byid = {c['id']: c for c in champs}
    rounds = R['round']
    ri = {r: i for i, r in enumerate(rounds)}
    def sees(cid, r):
        i = ri.get(r)
        return set(byid[cid]['sees'][i]) if i is not None and byid[cid]['sees'][i] else set()
    def pos(cid, r):
        i = ri.get(r)
        if i is None or not byid[cid]['alive'][i]: return None
        return (byid[cid]['x'][i], byid[cid]['y'][i])
    def alive(cid, r):
        i = ri.get(r)
        return i is not None and byid[cid]['alive'][i]
    # Champion damage by victim: [(round, attacker)]
    hits = collections.defaultdict(list)
    for e in ev:
        if e['k'] in ('attack', 'cast') and 'dmg' in e and 'a' in e:
            for v, amt in e['dmg']:
                if v in team and team[v] != team.get(e['a']): hits[v].append((e['r'], e['a']))
    tot['games'] += 1
    for e in ev:
        if e['k'] != 'death' or 'by' not in e or e.get('linked') is not None and e['by'] is None: continue
        v, D = e['v'], e['r']
        if e['by'] not in team or team[e['by']] == team[v]: continue
        dam = [(r, a) for r, a in hits[v] if D - 6 <= r <= D]
        if not dam: dam = [(D, e['by'])]
        f = min(r for r, _ in dam)
        foes = {a for _, a in dam}
        mates = [c['id'] for c in champs if c['team'] == team[v] and c['id'] != v]
        vsaw = set().union(*(sees(v, r) for r in range(f - 3, f)))
        mate_near = False
        for r in range(f - 4, f):
            for m in mates:
                if not alive(m, r): continue
                pv = pos(v, r)
                if not pv: continue
                for k in (sees(m, r) - sees(v, r)) & foes:
                    pk = pos(k, r)
                    if pk and cheb(pk, pv) <= 12: mate_near = True
        if foes & vsaw: cat = 'victim-saw-before'
        elif mate_near: cat = 'mate-saw-first'
        elif foes & sees(v, f): cat = 'victim-saw-at-hit-round'
        else: cat = 'nobody'
        tot['death-' + cat] += 1
        tot['gems-' + cat] += e.get('gems', 0)
    # Carriers and knowledge gaps, sampled every 2 rounds.
    for i in range(0, len(rounds), 2):
        r = rounds[i]
        for side in (0, 1):
            ours = [c for c in champs if c['team'] == side and c['alive'][i]]
            foes = [c for c in champs if c['team'] != side and c['alive'][i]]
            seen_by = {c['id']: set(c['sees'][i] or []) | (set(c['sees'][i - 1] or []) if i else set()) for c in ours}
            team_seen = set().union(*seen_by.values()) if seen_by else set()
            for c in ours:
                p = (c['x'][i], c['y'][i])
                gap = False
                for f in foes:
                    if f['id'] in seen_by[c['id']]: continue
                    if f['id'] in team_seen and cheb(p, (f['x'][i], f['y'][i])) <= 8: gap = True
                tot['turns'] += 1
                tot['turns-gap8'] += gap
            for f in foes:
                if f['gems'][i] < 40 or f['id'] not in team_seen: continue
                tot['carrier-seen'] += 1
                fp = (f['x'][i], f['y'][i])
                if any(f['id'] not in seen_by[c['id']] and cheb((c['x'][i], c['y'][i]), fp) <= 10 for c in ours):
                    tot['carrier-seen-mate-unaware-10'] += 1

def willow(batch, tot):
    for z in glob.glob(os.path.join(batch, '*.repl26a')):
        try: zf = zipfile.ZipFile(z)
        except Exception: continue
        for n in zf.namelist():
            if not n.endswith('.stdout'): continue
            for line in zf.read(n).decode(errors='replace').splitlines():
                if line.startswith('WF '):
                    p = line.split()
                    tot['wf-' + p[4]] += 1
                    tot['wf-d>8-' + p[4]] += int(p[7]) > 8
                elif line.startswith('CL '):
                    p = line.split()
                    used = int(p[-1]); camp_on = int(p[-3])
                    tot['cl'] += 1
                    tot['cl-free-sum'] += 64 - used
                    tot['cl-camp-off'] += camp_on == 0
                    for b in (10, 13, 18):
                        tot[f'cl-free>={b}'] += 64 - used >= b

if __name__ == '__main__':
    tot = collections.Counter()
    root = sys.argv[1]
    dirs = [os.path.join(root, d) for d in os.listdir(root) if os.path.exists(os.path.join(root, d, 'rounds.json.gz'))]
    for d in dirs:
        try: game(d, tot)
        except Exception as ex: tot['err'] += 1
    if '--batch' in sys.argv: willow(sys.argv[sys.argv.index('--batch') + 1], tot)
    for k in sorted(tot): print(k, tot[k])
