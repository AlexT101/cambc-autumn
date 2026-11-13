"""Abandoned clears with FT traces: a champion's run of hits on a group (no hit elsewhere between) that its team does
not capture within 30 rounds of the run's last hit. Per run: the hits, whether the group was harmless, the FT mode
and target in the run's last round with a trace and in the first traced round after it, the champion's HP fraction
at the end, and whether the run's hits were all of one round (a hit in passing).
usage: py fthru_abandon.py BATCH_DIR EXTRACT [END]"""
import json, gzip, glob, os, sys, collections, zipfile, re
from concurrent.futures import ProcessPoolExecutor
B = sys.argv[1]; A = sys.argv[2]; END = int(sys.argv[3]) if len(sys.argv) > 3 else 600
FT = re.compile(r'^FT (\d+) (\d+) (-?\d+),(-?\d+) g(-?\d+) (\S) v(\S+) s(-?\d+)')
E = json.load(open(A + '/enums.json'))
src_of = {}
for p in glob.glob(A + '/*/meta.json'):
    m = json.load(open(p))
    for s in m['sources']:
        if '-cand' in s['source']: src_of[os.path.basename(s['source'])] = os.path.dirname(p)


def one(path):
    d = src_of.get(os.path.basename(path))
    if not d: return None
    m = json.load(open(d + '/meta.json'))
    typ = {c['id']: E['champions'][c['type']] for c in m['champions']}
    mp = json.load(open(os.path.join(d, m['mapFile'])))
    team = 0 if m['teams'][0]['name'] != 'idle' else 1
    cg = {c['id']: c['group'] for c in mp['camps']}
    harmless = {g['id']: all(t in ('Gem cluster', 'Gold cluster') for t in g['types']) for g in mp['groups']}
    R = json.load(gzip.open(d + '/rounds.json.gz')); rr = R['round']; ri = {r: i for i, r in enumerate(rr)}
    ch = {c['id']: c for c in R['champions'] if c['team'] == team}
    hits = collections.defaultdict(list); caps = collections.defaultdict(list)
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['r'] > END + 40: break
        if e['k'] in ('attack', 'cast') and e.get('cdmg') and e.get('a') in ch:
            hits[e['a']].append((e['r'], cg.get(e['cdmg'][0][0]), sum(x[1] for x in e['cdmg'])))
        elif e['k'] == 'capture': caps[e['g']].append(e['r'])
    txt = zipfile.ZipFile(path).read('team-%s.stdout' % 'ab'[team]).decode(errors='replace')
    ft = collections.defaultdict(dict)
    for line in txt.splitlines():
        mt = FT.match(line)
        if mt: ft[int(mt.group(2))][int(mt.group(1))] = (int(mt.group(5)), mt.group(6))
    out = collections.Counter()
    for a, hs in hits.items():
        i = 0
        while i < len(hs):
            g = hs[i][1]; j = i
            while j + 1 < len(hs) and hs[j + 1][1] == g: j += 1
            r0, r1 = hs[i][0], hs[j][0]
            if r1 <= END:
                dmg = sum(h[2] for h in hs[i:j + 1])
                captured = any(r1 - 1 <= c <= r1 + 30 for c in caps[g])
                out['runs'] += 1; out['rounds'] += r1 - r0 + 1
                if not captured:
                    f = ft[a]
                    before = next((f[r] for r in range(r1, r0 - 30, -1) if r in f), None)
                    after = next((f[r] for r in range(r1 + 1, r1 + 15) if r in f), None)
                    ii = ri.get(r1)
                    hp = ch[a]['hp'][ii] / ch[a]['maxHp'][ii] if ii is not None else 1
                    kind = ('passing' if r0 == r1 else 'run') + ('-harmless' if harmless[g] else '-striker')
                    if before is None: why = 'no-ft'
                    elif before[0] != g: why = 'aimed-elsewhere:' + before[1]
                    elif after is None: why = 'then-other-branch' + ('-lowhp' if hp < 0.5 else '')
                    elif after[0] != g: why = 'switched:%s->%s' % (before[1], after[1])
                    else: why = 'kept-target'
                    out[('ab', kind)] += 1; out[('abr', kind)] += r1 - r0 + 1
                    out[('why', why)] += 1; out[('whyr', why)] += r1 - r0 + 1
                    out[('type', typ[a])] += r1 - r0 + 1
                    out['ab'] += 1; out['abr'] += r1 - r0 + 1
            i = j + 1
    return out


if __name__ == '__main__':
    ps = sorted(glob.glob(B + '/*.repl26a'))
    tot = collections.Counter(); n = 0
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one, ps, chunksize=4):
            if o: tot.update(o); n += 1
    print('games', n, 'hit runs %.1f a game, abandoned %.1f a game (%.1f%%), abandoned run rounds %.1f a game' % (
        tot['runs'] / n, tot['ab'] / n, 100 * tot['ab'] / tot['runs'], tot['abr'] / n))
    for pre in ('ab', 'why', 'type'):
        rows = sorted(((k[1], v) for k, v in tot.items() if isinstance(k, tuple) and k[0] == pre), key=lambda x: -x[1])
        for k, v in rows[:12]:
            extra = '  rounds %.1f a game' % (tot[(pre + 'r', k)] / n) if (pre + 'r', k) in tot else ''
            print('  %-5s %-28s %6d%s' % (pre, k, v, extra))
