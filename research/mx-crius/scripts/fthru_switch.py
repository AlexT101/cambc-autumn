"""Farm target switches from FT traces (f-thru debug solo): per champion, segments of turns with one farm target;
a segment that ends in another target with no camp hit on its group during it is an abandoned walk. Reports the
abandoned segments' turns, by the modes switched between, the old target's steps when dropped, and the value ratio
new/old at the switch. Needs the batch dir (stdout) and the solo extract (hits, by replay source).
usage: py fthru_switch.py BATCH_DIR EXTRACT [END]"""
import json, gzip, glob, os, sys, collections, zipfile, re
from concurrent.futures import ProcessPoolExecutor
B = sys.argv[1]; A = sys.argv[2]; END = int(sys.argv[3]) if len(sys.argv) > 3 else 600
FT = re.compile(r'^FT (\d+) (\d+) (-?\d+),(-?\d+) g(-?\d+) (\S) v(\S+) s(-?\d+) bag(\d+) bk(\d)')
src_of = {}
for p in glob.glob(A + '/*/meta.json'):
    m = json.load(open(p))
    for s in m['sources']:
        src_of[os.path.basename(s['source'])] = os.path.dirname(p)


def one(path):
    name = os.path.basename(path)
    d = src_of.get(name)
    if not d: return None
    m = json.load(open(d + '/meta.json'))
    mp = json.load(open(os.path.join(d, m['mapFile'])))
    cg = {c['id']: c['group'] for c in mp['camps']}
    team = 0 if m['teams'][0]['name'] != 'idle' else 1
    hits = collections.defaultdict(list)
    for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['r'] > END: break
        if e['k'] in ('attack', 'cast') and e.get('cdmg'):
            for cid, _ in e['cdmg']: hits[(e['a'], cg.get(cid))].append(e['r'])
    z = zipfile.ZipFile(path)
    txt = z.read('team-%s.stdout' % 'ab'[team]).decode(errors='replace')
    seq = collections.defaultdict(list)
    for line in txt.splitlines():
        mt = FT.match(line)
        if not mt: continue
        r = int(mt.group(1))
        if r > END: break
        seq[int(mt.group(2))].append((r, int(mt.group(5)), mt.group(6), float(mt.group(7)), int(mt.group(8)), int(mt.group(10))))
    out = collections.Counter()
    for h, s in seq.items():
        i = 0
        out['ft_turns'] += len(s)
        while i < len(s):
            g = s[i][1]; j = i
            while j + 1 < len(s) and s[j + 1][1] == g: j += 1
            if j + 1 < len(s) and g >= 0:
                r0, r1 = s[i][0], s[j + 1][0]
                hit = any(r0 <= x <= r1 for x in hits[(h, g)])
                if not hit:
                    nx = s[j + 1]
                    turns = r1 - r0
                    key = '%s->%s' % (s[j][2], nx[2])
                    out[('ab', key, 'n')] += 1; out[('ab', key, 't')] += turns
                    out['ab_n'] += 1; out['ab_t'] += turns
                    st = s[j][4]
                    b = 'near<=3' if st <= 3 else 'mid4-10' if st <= 10 else 'far>10'
                    out[('st', b, 'n')] += 1; out[('st', b, 't')] += turns
                    ratio = nx[3] / s[j][3] if s[j][3] > 0 else 99
                    rb = '<1' if ratio < 1 else '<1.2' if ratio < 1.2 else '<2' if ratio < 2 else '>=2'
                    out[('ratio', rb, 'n')] += 1; out[('ratio', rb, 't')] += turns
                    out[('bank', s[j][5], nx[5], 'n')] += 1; out[('bank', s[j][5], nx[5], 't')] += turns
                    if turns == 1: out['ab_1'] += 1
                else:
                    out['done_n'] += 1
            i = j + 1
    return out


if __name__ == '__main__':
    ps = sorted(glob.glob(B + '/*.repl26a'))
    tot = collections.Counter(); n = 0
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one, ps, chunksize=4):
            if o: tot.update(o); n += 1
    print('games', n, 'ft turns', tot['ft_turns'], 'segments done', tot['done_n'], 'abandoned', tot['ab_n'], 'turns', tot['ab_t'],
          '(%.1f%% of ft turns; %.1f a game) one-turn %d' % (100 * tot['ab_t'] / max(1, tot['ft_turns']), tot['ab_t'] / max(1, n), tot['ab_1']))
    for kind in ('ab', 'st', 'ratio', 'bank'):
        rows = [(k, tot[k[:-1] + ('t',)]) for k in tot if isinstance(k, tuple) and k[0] == kind and k[-1] == 'n']
        rows.sort(key=lambda x: -x[1])
        for k, t in rows[:14]:
            print('  %-6s %-14s n %6d turns %7d (%.1f/seg)' % (kind, ' '.join(map(str, k[1:-1])), tot[k], t, t / tot[k]))
