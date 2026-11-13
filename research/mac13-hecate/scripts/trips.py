"""Farm trips from debug D lines: streaks of F turns with one farm_group; abandoned = no hit on and no stand on that group."""
import sys, re, json, gzip, zipfile, collections, hashlib
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
D_RE = re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
AN = Path(sys.argv[2])
INDEX = {}
for dd in AN.iterdir():
    if (dd/'meta.json').exists():
        INDEX[Path(json.loads((dd/'meta.json').read_text())['source']).name] = dd
def one(f):
    f = Path(f)
    try:
        z = zipfile.ZipFile(f)
    except Exception: return None
    d = INDEX.get(f.name)
    if d is None: return None
    meta = json.loads((d/'meta.json').read_text()); mp = json.loads((d/meta['mapFile']).read_text())
    gt = {g['id']: set(map(tuple, g['tiles'])) for g in mp['groups']}
    camp_group = {c['id']: c['group'] for c in mp['camps']}
    R = json.load(gzip.open(d/'rounds.json.gz')); r0 = R['round'][0]
    ch = {c['id']: c for c in R['champions']}
    hits = collections.defaultdict(set)
    import bisect
    gtl = collections.defaultdict(list)
    for row in R['groups']:
        gtl[row[1]].append((row[0], row[2], row[3]))
    def state_at(g, r):
        L = gtl.get(g, [])
        i = bisect.bisect_right(L, (r, 99, 99)) - 1
        return L[i][1:] if i >= 0 else (None, None)
    caps = collections.defaultdict(list)
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e = json.loads(l)
        if e.get('k') == 'capture': caps[e['g']].append((e['r'], e['team']))
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e = json.loads(l)
        if e.get('k') in ('attack','cast') and 'a' in e:
            for cd in e.get('cdmg') or []: hits[(e['a'], camp_group.get(cd[0]))].add(e['r'])
    # stdout of both teams; ids are global
    rows = collections.defaultdict(list)
    for side in ('team-a.stdout', 'team-b.stdout'):
        for m in D_RE.finditer(z.read(side)):
            r, cid, br, fg, cl = int(m[1]), int(m[2]), m[3].decode(), int(m[4]), int(m[5])
            rows[cid].append((r, br, fg))
    st = collections.Counter()
    for cid, L in rows.items():
        if cid not in ch: continue
        C = ch[cid]
        streak = None
        def close(s):
            if not s: return
            g, start, end, n = s
            worked = any(start <= r <= end + 40 for r in hits[(cid, g)]) or any(
                0 <= r - r0 < len(C['x']) and (C['x'][r - r0], C['y'][r - r0]) in gt.get(g, ()) for r in range(start, end + 41))
            st['streaks'] += 1; st['turns'] += n
            if not worked:
                st['abandoned'] += 1; st['ab_turns'] += n
                b = 'len1-2' if n <= 2 else 'len3-5' if n <= 5 else 'len6-10' if n <= 10 else 'len11+'
                st['abt_' + b] += n
                # was the group alive (state 1?) at the streak start? groups rows: [round, group, state, team, timer, respawn, awake, hp]
                s0 = state_at(g, start)[0]; s1 = state_at(g, end + 1)[0]
                st[f'abt_start{s0}_end{s1}'] += n
                # captured by someone during or right after the streak?
                tk = [t for (r, t) in caps.get(g, []) if start <= r <= end + 6]
                st['abt_taken_' + ('own' if tk and tk[0] == C['team'] else 'enemy' if tk else 'none')] += n
        for r, br, fg in L:
            if br == 'F' and fg >= 0:
                if streak and streak[0] == fg and r - streak[2] <= 2: streak = (fg, streak[1], r, streak[3] + 1)
                else: close(streak); streak = (fg, r, r, 1)
            else:
                close(streak); streak = None
            st['D'] += 1; st['F'] += br == 'F'
        close(streak)
        # oscillation: consecutive distinct farm groups sequence
        seq = []
        for r, br, fg in L:
            if br == 'F' and fg >= 0 and (not seq or seq[-1][0] != fg): seq.append((fg, r))
        for i in range(2, len(seq)):
            if seq[i][0] == seq[i-2][0] and seq[i][1] - seq[i-2][1] <= 30: st['ABA30'] += 1
        st['switches'] += max(0, len(seq) - 1)
    return st
if __name__ == '__main__':
    files = sorted(Path(sys.argv[1]).glob('*.repl26a'))
    tot = collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one, files, chunksize=8):
            if o: tot.update(o)
    print(tot)
    print('F share of turns', tot['F']/tot['D'], 'abandoned share of F turns', tot['ab_turns']/tot['turns'], 'abandoned streaks', tot['abandoned']/tot['streaks'])
