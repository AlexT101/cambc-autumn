# Tribute episodes per game and side (opponent fidelity, EXPERIMENTS "Opponent tribute fidelity").
#   py episodes.py OUT.pkl  -- live r2 replays (v86-v95) and local liveforensic runs (lf-c2[78]-o29[FM])
#   import episodes; episodes.scan(dir, T) -> per-side rows
# Each row: side ('us'|'op'), champ type, start round, gems, nearest other-team champion at start (Chebyshev, any
# visibility), end ('done'|'manual'|'stun'|'lock'|'death'|'open'), rounds held, nearest at end, next start by the same
# champion (rounds later, or None). Plus per-game: altar-waiting rounds (within 1 of an altar, gems > 0, no channel)
# by nearest-enemy bin, and opponent tributed gems at 600.
import gzip, json, os, pickle, re, sys
from pathlib import Path
from multiprocessing import Pool

G = Path('/home/ubuntu/tmp-offload/handoff/gate'); LF = Path('/home/ubuntu/tmp-offload/liveforensic/ana')
ROOT = Path('/home/ubuntu/cambc-autumn')
MC = json.load(open(G / 'mapclass.json'))

def near(rd, i, me_team, x, y):
    ds = [max(abs(c['x'][i] - x), abs(c['y'][i] - y)) for c in rd['champions']
          if c['team'] != me_team and c['alive'][i] and c['x'][i] is not None]
    return min(ds) if ds else 99

def scan(d, T, until=None):
    d = Path(d); meta = json.load(open(d / 'meta.json'))
    mp = json.load(open(d / meta['mapFile']))
    alt = [tuple(a) for a in mp['altars']]
    team = {c['id']: c['team'] for c in meta['champions']}; name = {c['id']: c['name'] for c in meta['champions']}
    rd = json.load(gzip.open(d / 'rounds.json.gz')); R = rd['round']; ri = {r: i for i, r in enumerate(R)}
    ch = {c['id']: c for c in rd['champions']}
    def idx(r): return ri.get(r - 1, ri.get(r))
    eps, open_ = [], {}
    for l in gzip.open(d / 'events.jsonl.gz', 'rt'):
        e = json.loads(l); k = e['k']
        if k == 'tribute_start':
            a = e['a']; i = idx(e['r']); c = ch[a]
            x, y = e['at']
            row = dict(side='us' if team[a] == T else 'op', a=a, who=name[a], r=e['r'], gems=e['gems'],
                       d0=near(rd, i, team[a], x, y) if i is not None else 99, end='open', held=None, d1=None,
                       hp=(c['hp'][i] / c['maxHp'][i]) if i is not None and c['maxHp'][i] else None, nxt=None)
            if a in open_: pass
            open_[a] = row; eps.append(row)
        elif k in ('tribute_end', 'tribute_cancel') and e.get('a') in open_:
            row = open_.pop(e['a']); row['end'] = 'done' if k == 'tribute_end' else e.get('cause', '?')
            row['held'] = e['r'] - row['r']; i = idx(e['r']); c = ch[e['a']]
            if i is not None and c['x'][i] is not None: row['d1'] = near(rd, i, team[e['a']], c['x'][i], c['y'][i])
            if k == 'tribute_end': row['gems_end'] = e.get('gems', row['gems'])
        elif k == 'death' and e.get('v') in open_:
            row = open_.pop(e['v']); row['end'] = 'death'; row['held'] = e['r'] - row['r']
    by = {}
    for row in eps: by.setdefault(row['a'], []).append(row)
    for rows in by.values():
        for p, q in zip(rows, rows[1:]): p['nxt'] = q['r'] - p['r']
    # Altar waiting: rounds a champion sits within 1 of an altar with gems, alive, not channelling a tribute.
    wait = {}
    for c in rd['champions']:
        s = 'us' if c['team'] == T else 'op'
        for i, r in enumerate(R):
            if until and r > until: break
            if not c['alive'][i] or not c['gems'][i] or c['chan'][i] == 2 or c['x'][i] is None: continue
            x, y = c['x'][i], c['y'][i]
            if min(max(abs(ax - x), abs(ay - y)) for ax, ay in alt) > 1: continue
            dd = near(rd, i, c['team'], x, y); b = '<=3' if dd <= 3 else '4-5' if dd <= 5 else '6-8' if dd <= 8 else '9+'
            wait[(s, b)] = wait.get((s, b), 0) + 1
    def gem_at(t, r):
        j = min(range(len(R)), key=lambda j: abs(R[j] - r)) if R[-1] >= r else len(R) - 1
        return rd['gems'][t][j]
    return dict(eps=eps, wait=wait, rounds=R[-1], op600=gem_at(1 - T, 600), us600=gem_at(T, 600),
                win=meta['result']['winner'] == T, nalt=len(alt))

def live_jobs():
    idx = json.load(open(G / 'analysis/index.json'))['games']
    by = {str((ROOT / g['source']).resolve()): g['dir'] for g in idx}
    jobs = []
    for v in (86, 87, 89, 91, 93, 95):
        for o, opp in (('inte', 'fish'), ('mite', 'mite')):
            dd = G / 'raw' / f'v{v}-r2' / o
            for f in sorted(dd.glob('*.repl26a')):
                m = re.match(r'(.+)-([ab])\.repl26a$', f.name)
                p = str(f.resolve())
                if p in by: jobs.append((('live', v, opp, m.group(1), m.group(2)), str(G / 'analysis' / by[p]), 0 if m.group(2) == 'a' else 1))
    return jobs

def local_jobs(ana=LF, pat=r'lf-(c2[78])-o29([FM])'):
    out = []
    for g in json.load(open(Path(ana) / 'index.json'))['games']:
        m = re.search(pat + r'.*/\d+-(.+)-(12|21)\.repl26a$', g['source'])
        if m:
            mp = m.group(m.lastindex - 1).replace('-', '_')
            out.append((('local', m.group(1), m.group(2), mp, m.group(m.lastindex)), str(Path(ana) / g['dir']),
                        0 if m.group(m.lastindex) == '12' else 1))
    return out

def run(job):
    key, d, T = job
    try: return key, scan(d, T)
    except Exception as ex: return key, {'err': repr(ex)}

if __name__ == '__main__':
    jobs = live_jobs() + local_jobs()
    with Pool(int(os.environ.get("OMP_NUM_THREADS", 8))) as P: res = dict(P.map(run, jobs, chunksize=4))
    print(len(res), sum('err' in v for v in res.values()))
    pickle.dump(res, open(sys.argv[1], 'wb'))
