"""flipgames.py A B [part]: extracts the replays of games where versions A and B differ, both versions, then
prints lock and channel facts for each. Output dirs under SCRATCH/gate/raw and SCRATCH/gate/analysis."""
import collections, gzip, json, subprocess, sys, zipfile
from pathlib import Path
sys.path.insert(0, '/home/ubuntu/cambc-autumn/tools')
import ladder_scrims as ls
ROOT = Path('/home/ubuntu/cambc-autumn')
G = Path(__import__('os').environ.get('GATE_DIR', '/tmp/gate'))  # scratch: raw/, analysis/, mapclass.json
cls = json.load(open(G / 'mapclass.json'))
sites = {}
for l in open(G / 'ladder_sites.jsonl'):
    r = json.loads(l); sites[r['name'].lower().replace('-', '_')] = r
a, b = int(sys.argv[1]), int(sys.argv[2])
part = sys.argv[3] if len(sys.argv) > 3 else None
only = sys.argv[4] if len(sys.argv) > 4 else None  # 'flips' (default) or 'all'
key = lambda r: (r['opp_name'][:4].lower(), r['map'], r['side'])
sel = lambda r: r['purpose'] == 'set' and (not part or r['part'] == part)
ra = {key(r): r for r in ls.games(a) if sel(r)}
rb = {key(r): r for r in ls.games(b) if sel(r)}
both = sorted(set(ra) & set(rb))
pick = [k for k in both if only == 'all' or (ra[k]['result'] != rb[k]['result'])]
files = []
for k in pick:
    for v, rr in ((a, ra), (b, rb)):
        r = rr[k]
        d = G / 'raw' / f'v{v}' / k[0] / f'{k[1]}-{k[2]}'
        f = d / f'{k[1]}-{k[2]}.repl26a'
        if not f.exists():
            d.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(ROOT / r['replay']) as z:
                f.write_bytes(z.read('replay.repl26a'))
        files.append(str(f))
if files:
    subprocess.run(['node', str(ROOT / 'tools/replay/extract.mjs'), *files, '--out', str(G / 'analysis'), '--threads', '8'],
                   check=True, stdout=subprocess.DEVNULL)
idx = json.load(open(G / 'analysis/index.json'))['games']
by_src = {str((ROOT / g['source']).resolve()): g['dir'] for g in idx}


def facts(v, k, r):
    f = str((G / 'raw' / f'v{v}' / k[0] / f'{k[1]}-{k[2]}' / f'{k[1]}-{k[2]}.repl26a').resolve())
    d = G / 'analysis' / by_src[f]
    meta = json.load(open(d / 'meta.json'))
    rd = json.load(gzip.open(d / 'rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    T = 0 if k[2] == 'a' else 1
    team = {c['id']: c['team'] for c in meta['champions']}
    name = {c['id']: c['name'] for c in meta['champions']}
    n = len(rd['round'])
    ours = theirs = 0
    for L in rd['locks']:
        ours += any(t == T for t, *_ in L); theirs += any(t != T for t, *_ in L)
    o = collections.Counter()
    cancels = []
    big_done = []
    for e in ev:
        kk = e['k']
        if kk == 'lock_place':
            o['lk_us' if e['team'] == T else 'lk_op'] += 1
        elif kk == 'lock_destroyed':
            o['lkx_us' if e['team'] == T else 'lkx_op'] += 1
        elif kk == 'tribute_end':
            s = 'us' if team[e['a']] == T else 'op'
            o['trib_' + s] += 1
            if s == 'op' and e['gems'] >= 100: big_done.append((e['r'], e['gems']))
        elif kk == 'tribute_cancel':
            s = 'us' if team[e['a']] == T else 'op'
            o[f'tc_{s}'] += 1; o[f'tcg_{s}'] += e['gems']
            if s == 'op' and e['gems'] >= 50: cancels.append((e['r'], e['gems'], e['cause']))
        elif kk == 'death':
            s = 'us' if team[e['v']] == T else 'op'
            o['d_' + s] += 1; o['dg_' + s] += e['gems']
    # our lock placements that cancelled an enemy channel: (round, placer, gems, turns left, placer died within 15)
    deaths = [(e['r'], e['v']) for e in ev if e['k'] == 'death']
    lock_cuts = []
    for i, e in enumerate(ev):
        if e['k'] == 'lock_place' and e['team'] == T:
            for c in ev[i + 1:i + 12]:
                if c['k'] == 'tribute_cancel' and c['cause'] == 'lock' and team[c['a']] != T and c['r'] == e['r']:
                    died = any(dv == e['a'] and e['r'] <= dr <= e['r'] + 15 for dr, dv in deaths)
                    lock_cuts.append((e['r'], name[e['a']][:4], c['gems'], c['left'], 'died' if died else 'lived'))
    # deaths of ours within 3 of a site tile (holder proxy)
    alts = [tuple(x) for x in json.load(open(d / meta['mapFile']))['altars']]
    near = [(e['r'], name[e['v']], e['gems']) for e in ev if e['k'] == 'death' and team[e['v']] == T
            and min(max(abs(e['at'][0] - x), abs(e['at'][1] - y)) for x, y in alts) <= 3]
    return dict(res=r['result'][0].upper(), gems=f"{r.get('our_gems')}-{r.get('opp_gems')}", rounds=r.get('rounds'),
                lockshare=f'{100 * ours // max(n, 1)}/{100 * theirs // max(n, 1)}', o=o, cancels=cancels,
                big_done=big_done, near_deaths=near, lock_cuts=lock_cuts,
                picks=f"{'/'.join(p[:4] for p in r['our_picks'])} v {'/'.join(p[:4] for p in r['opp_picks'])}")


out = []
for k in pick:
    print(f"\n== {k[0]} {k[1]}-{k[2]} ({cls[k[1]]}, altars {sites[k[1].lower()]['altars']}, sites {sites[k[1].lower()]['sites']})")
    for v, rr in ((a, ra), (b, rb)):
        F = facts(v, k, rr[k]); o = F['o']
        print(f"  v{v} {F['res']} {F['gems']} r{F['rounds']} {F['picks']}")
        print(f"     lock share us/op {F['lockshare']}%  placed {o['lk_us']}/{o['lk_op']}  broken {o['lkx_us']}/{o['lkx_op']}"
              f"  tributes {o['trib_us']}/{o['trib_op']}  channels cancelled us {o['tc_us']} ({o['tcg_us']}g) op {o['tc_op']} ({o['tcg_op']}g)"
              f"  deaths {o['d_us']}/{o['d_op']} bag gems {o['dg_us']}/{o['dg_op']}")
        if F['cancels']: print(f"     op channels >=50 cancelled (r, gems, cause): {F['cancels']}")
        if F['lock_cuts']: print(f"     our locks cancelling an op channel (r, placer, gems, left, placer within 15r): {F['lock_cuts']}")
        if F['big_done']: print(f"     op tributes >=100 landed (r, gems): {F['big_done']}")
        if F['near_deaths']: print(f"     our deaths within 3 of an altar (r, champ, gems): {F['near_deaths']}")
        out.append(dict(v=v, key=k, **{x: y for x, y in F.items() if x != 'o'}, o=dict(o)))
json.dump(out, open(G / f'flips-{a}-{b}-{part}.json', 'w'))
