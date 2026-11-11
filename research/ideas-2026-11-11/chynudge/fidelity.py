"""Did the arms draft in-game what the offline plan says? The kept replays' drafts (24 a suite) against model.mjs
teams for that arm and map.   py fidelity.py STAGE"""
import sys, os, json, subprocess, tempfile, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run
R = run.R; s = run.stage(sys.argv[1]); plan = json.load(open(f'{run.W}/plan-{s["name"]}.json'))
enum = lambda n: n.lower().replace(' & ', '_and_').replace(' ', '_')
tot = collections.Counter()
for arm, p in plan.items():
    tm = run.teams(s, arm); idx = {}
    for o in p:
        f = f'{R}replays/ab/{run.rname(s, arm, o)}/summary.json'
        if not os.path.exists(f): continue
        for su in json.load(open(f))['suites']:
            for m in json.load(open(R + su['batch'] + '/results.json'))['matches']:
                if m.get('replay') and os.path.exists(m['replay']): idx[m['replay']] = (os.path.basename(m['map']).replace('.map26a', ''), m['order'][0])
    if not idx: continue
    with tempfile.NamedTemporaryFile('w', delete=False, dir=run.W) as fh: fh.write('\n'.join(idx)); lst = fh.name
    out = subprocess.run(['node', R + 'tools/replay/drafts.mjs', lst], capture_output=True, text=True, check=True).stdout; os.unlink(lst)
    ok = bad = 0
    for line in out.splitlines():
        pth, a, b = line.split('\t'); name, first = idx[pth]; ours = a if first == 0 else b
        got = sorted(enum(x.strip()) for x in ours.replace('|', ',').split(',')); want = sorted(tm[name].split(','))
        if got == want: ok += 1
        else:
            bad += 1
            if bad <= 3: print('  MISMATCH', arm, name, got, want)
    tot['ok'] += ok; tot['bad'] += bad
    print(f'{arm}: {ok} replays match the planned team, {bad} differ')
print(dict(tot))
