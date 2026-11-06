"""aftercut.py A B part: after each of our locks that cancels an enemy channel, by turns left (<=2: timed, >=3: early):
rounds until that lock is broken, whether the enemy lands >= 80% of the cancelled bag within 60 rounds, placer death."""
import gzip, json, sys, collections
from pathlib import Path
ROOT = Path('/home/ubuntu/cambc-autumn')
G = Path(__import__('os').environ.get('GATE_DIR', '/tmp/gate'))  # scratch: raw/, analysis/, mapclass.json
a, b, part = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
rows = json.load(open(G / f'flips-{a}-{b}-{part}.json'))
idx = json.load(open(G / 'analysis/index.json'))['games']
by_src = {str((ROOT / g['source']).resolve()): g['dir'] for g in idx}
for v in (a, b):
    st = collections.defaultdict(lambda: collections.Counter())
    brk = collections.defaultdict(list)
    for r in rows:
        if r['v'] != v: continue
        k = r['key']; T = 0 if k[2] == 'a' else 1
        f = str((G / 'raw' / f'v{v}' / k[0] / f'{k[1]}-{k[2]}' / f'{k[1]}-{k[2]}.repl26a').resolve())
        d = G / 'analysis' / by_src[f]
        meta = json.load(open(d / 'meta.json'))
        team = {c['id']: c['team'] for c in meta['champions']}
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
        for i, e in enumerate(ev):
            if e['k'] != 'lock_place' or e['team'] != T: continue
            c = next((c for c in ev[i + 1:i + 12] if c['k'] == 'tribute_cancel' and c['cause'] == 'lock'
                      and team[c['a']] != T and c['r'] == e['r']), None)
            if not c or c['gems'] < 50: continue
            cls = 'timed' if c['left'] <= 2 else 'early'
            s = st[cls]; s['n'] += 1; s['gems'] += c['gems']
            alt = e['to']
            br = next((x['r'] for x in ev[i + 1:] if x['k'] == 'lock_destroyed' and x['team'] == T and x['at'] == alt), None)
            if br is not None: brk[cls].append(br - e['r'])
            s['broken<=10'] += br is not None and br - e['r'] <= 10
            land = sum(x['gems'] for x in ev[i + 1:] if x['k'] == 'tribute_end' and team[x['a']] != T and e['r'] < x['r'] <= e['r'] + 60)
            s['rebanked'] += land >= 0.8 * c['gems']
            s['died15'] += any(x['k'] == 'death' and x['v'] == e['a'] and e['r'] <= x['r'] <= e['r'] + 15 for x in ev[i + 1:])
            s['won'] += r['res'] == 'W'
    for cls in ('timed', 'early'):
        s = st[cls]; b_ = sorted(brk[cls])
        med = b_[len(b_) // 2] if b_ else None
        print(f"v{v} {cls}: {s['n']} cuts of 50+ gem channels ({s['gems']} gems), lock broken within 10 rounds {s['broken<=10']} "
              f"(median {med} rounds), enemy re-banked >=80% within 60 rounds {s['rebanked']}, placer died within 15 {s['died15']}, game won {s['won']}")
