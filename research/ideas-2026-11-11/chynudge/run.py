"""Play the charybdis draft-nudge arms against the run-time Fish / Mite bodies (fgate's rt-Flp4 / rt-Mt3q, unmetered,
a noise seed per map). An arm is chy-draft18 with only draft_model.h changed; local games are deterministic, so an arm
plays only the maps where its team differs from chy-draft18's, against the opponent it is meant for, and chy-draft18's
games on the same maps and noise are the counterfactual.

    py run.py build STAGE            arm bots, teams, suite dirs and the opponent config
    py run.py play STAGE [--jobs 3]  ab.py runs, then WORK/stages/STAGE.done
    py run.py read STAGE [STAGE..]   the paired table (several stages: pooled over their maps)

STAGE is WORK/stages/STAGE.json: {feat, fuel, noise0, check, arms: {name: {spec: "DIR:lam", opp: "F" | "M" | "FM"}}}."""
import json, os, subprocess, sys, time, math, collections, numpy as np
R = '/home/ubuntu/cambc-autumn/'; T = os.path.dirname(os.path.abspath(__file__))
D = os.path.expanduser('~/tmp-offload/chynudge'); W = f'{D}/work'; BASE = 'variants/chy-draft18'; BASELAB = 'replays/draftlab/draft18-start'
BODY = {'F': 'variants/rt-Flp4', 'M': 'variants/rt-Mt3q'}; NOISE0 = 1310000; PART = 320; MAXPARTS = 12
LIB = f'{R}tools/fastengine/runner/target-rt/release/libfastrunner.so'

def stage(name): s = json.load(open(f'{W}/stages/{name}.json')); s['name'] = name; return s
def bot(arm): return BASE if arm == 'base' else f'variants/cn-{arm}'
def lab(arm): return f'{D}/labs/{arm}'
def maps_of(s):
    out, seen = [], set()
    for l in open(s['feat']):
        r = json.loads(l)
        if r['key'] in seen or r['picks'] not in (3, 4, 5): continue
        seen.add(r['key']); out.append((r['name'], os.path.normpath(os.path.join(R, r['path'])), r['picks']))
    return out
def teams(s, arm): return {l.split()[2]: l.split()[3] for l in open(f'{W}/teams-{s["name"]}-{arm}.txt')}
def rname(s, arm, o): return f'cn-{s["name"]}-{arm}-{o}-fuel{s["fuel"]}'
def sdir(s, arm, o): return f'{D}/suites/{s["name"]}-{arm}-{o}'

def build(s):
    for d in ('labs', 'suites', 'logs', 'results'): os.makedirs(f'{D}/{d}', exist_ok=True)
    run = lambda *c: subprocess.run(c, cwd=R, check=True, capture_output=True, text=True).stdout
    open(f'{W}/teams-{s["name"]}-base.txt', 'w').write(run('node', 'tools/draftlab/model.mjs', 'teams', '--lab', BASELAB, '--features', s['feat']))
    for arm, a in s['arms'].items():
        if not os.path.exists(f'{lab(arm)}/model.json'): run(sys.executable, f'{T}/nudge.py', 'model', a['spec'], lab(arm))
        if not os.path.isdir(f'{R}bots/{bot(arm)}'):
            run('./copybot', BASE, bot(arm))
            run('node', 'tools/draftlab/model.mjs', 'cpp', '--lab', lab(arm), '--out', f'{R}bots/{bot(arm)}/src/draft/draft_model.h')
            d = subprocess.run(['diff', '-rq', '-x', '.cambc', '-x', 'compile_commands.json', f'bots/{BASE}', f'bots/{bot(arm)}'], cwd=R, capture_output=True, text=True).stdout
            assert d.strip().splitlines() == [f'Files bots/{BASE}/src/draft/draft_model.h and bots/{bot(arm)}/src/draft/draft_model.h differ'], d
        open(f'{W}/teams-{s["name"]}-{arm}.txt', 'w').write(run('node', 'tools/draftlab/model.mjs', 'teams', '--lab', lab(arm), '--features', s['feat']))
    mp = maps_of(s); base = teams(s, 'base'); plan = {}; rng = np.random.default_rng(1); owner = {}
    for arm, a in s['arms'].items():
        tm = teams(s, arm); ch = [m[0] for m in mp if tm[m[0]] != base[m[0]]]; same = [m[0] for m in mp if tm[m[0]] == base[m[0]]]
        chk = sorted(rng.choice(same, min(s.get('check', 0), len(same)), replace=False).tolist()) if same else []
        for o in a['opp']:
            # A map where an earlier arm drafts this arm's team against this opponent is that arm's game: reuse it.
            reuse = {m: owner[(o, m, tm[m])] for m in ch if (o, m, tm[m]) in owner}
            for m in ch: owner.setdefault((o, m, tm[m]), arm)
            plan.setdefault(arm, {})[o] = {'changed': ch, 'check': chk, 'play': [m for m in ch if m not in reuse], 'reuse': reuse}
            plan.setdefault('base', {}).setdefault(o, {'changed': set(), 'check': [], 'reuse': {}})['changed'] |= set(ch) | set(chk)
    for o in plan['base']: plan['base'][o]['changed'] = sorted(plan['base'][o]['changed']); plan['base'][o]['play'] = plan['base'][o]['changed']
    path = {m[0]: m[1] for m in mp}
    for arm, p in plan.items():
        for o, v in p.items():
            names = v['play'] + v['check']; size = max(PART, -(-len(names) // MAXPARTS))
            for k in range(-(-len(names) // size)):
                d = f'{sdir(s, arm, o)}/p{k}'; os.makedirs(d, exist_ok=True)
                for n in names[k * size:(k + 1) * size]:
                    if not os.path.lexists(f'{d}/{n}.map26a'): os.symlink(path[n], f'{d}/{n}.map26a')
            v['parts'] = -(-len(names) // size)
    json.dump(plan, open(f'{W}/plan-{s["name"]}.json', 'w'))
    cfg = {'schema': 1, 'opponent_index': 1, 'maps': {m[0]: {'seed': NOISE0 + s['noise0'] + i, 'salt': s['noise0'] + i, 'unmetered': True} for i, m in enumerate(mp)}}
    json.dump(cfg, open(f'{W}/config-{s["name"]}.json', 'w'))
    tot = 0
    for arm, p in plan.items():
        for o, v in p.items():
            n = len(v['play']) + len(v['check']); tot += 2 * n
            print(f'{arm:8s} {o}: {len(v["changed"])} maps ({100 * len(v["changed"]) / len(mp):.1f}% of {len(mp)}), {len(v["reuse"])} reused + {len(v["check"])} check, {2 * n} games, {v["parts"]} suites')
    print('total games', tot)

def ngames(v): return 2 * (len(v['play']) + len(v['check']))
def done(s, arm, o, n):
    try: x = json.load(open(f'{R}replays/ab/{rname(s, arm, o)}/summary.json'))
    except (OSError, ValueError): return False
    return x['games'] + x['errors'] >= n and x.get('release') is True and x.get('fuel') == s['fuel']
def save(s, arm, o):
    """Copy the run's per-game results out of replays/ (janitors thin batches): map, side, win, rounds."""
    x = json.load(open(f'{R}replays/ab/{rname(s, arm, o)}/summary.json')); rows = []
    for su in x['suites']:
        for m in json.load(open(R + su['batch'] + '/results.json'))['matches']:
            if m.get('winner') is None: continue
            rows.append([os.path.basename(m['map']).replace('.map26a', ''), 'a' if m['order'][0] == 0 else 'b', int(m['winner'] == 0), m.get('rounds')])
    meta = {k: x.get(k) for k in ('games', 'errors', 'oof', 'early_losses', 'handoff_failures', 'capped_drafts', 'wall_seconds', 'cambc', 'fuel', 'release')}
    json.dump({'meta': meta, 'rows': rows}, open(f'{D}/results/{rname(s, arm, o)}.json', 'w'))

def play(s, jobs, threads):
    plan = json.load(open(f'{W}/plan-{s["name"]}.json'))
    env = dict(os.environ, CAMBC_BIN=f'{R}tools/fastengine/runner/fastrunner', FASTRUNNER_MODE='native', FASTRUNNER_LIB=LIB)
    env.setdefault('CAMBC_SLOTS', '86')
    todo = [(arm, o, ngames(v), v['parts']) for arm, p in plan.items() for o, v in p.items()]
    todo.sort(key=lambda t: -t[2]); procs = {}; fails = 0
    while True:
        for key, p in list(procs.items()):
            if p.poll() is not None:
                del procs[key]
                if p.returncode or not done(s, *key[:3]): print('FAIL', key, flush=True); fails += 1
                else: save(s, *key[:2]); print('done', key, time.strftime('%T'), flush=True)
        left = [t for t in todo if not os.path.exists(f'{D}/results/{rname(s, *t[:2])}.json') and t not in procs]
        if not left and not procs: break
        if fails > 3: print('too many failures'); break
        for t in left:
            if len(procs) >= jobs: break
            if done(s, *t[:3]): save(s, *t[:2]); continue
            arm, o, n, parts = t; nm = rname(s, arm, o)
            cmd = [sys.executable, f'{R}tools/ab.py', bot(arm), BODY[o], '--no-test-draft', '--suites', ','.join(f'{sdir(s, arm, o)}/p{k}' for k in range(parts)),
                   '--name', nm, '--keep-replays', '24', '--fuel', str(s['fuel']), '--experiment-config', f'{W}/config-{s["name"]}.json', '--game-timeout', '600', '--threads', str(threads)]
            procs[t] = subprocess.Popen(cmd, cwd=R, env=env, stdout=open(f'{D}/logs/{nm}.log', 'w'), stderr=subprocess.STDOUT)
        time.sleep(3)
    open(f'{W}/stages/{s["name"]}.done', 'w').write(time.strftime('%F %T') + f' fails {fails}\n')

def results(s, arm, o):
    p = f'{D}/results/{rname(s, arm, o)}.json'
    if not os.path.exists(p): return {}, None
    x = json.load(open(p)); return {(mp, side): (w, rounds) for mp, side, w, rounds in x['rows']}, x['meta']
def est(u):
    u = np.array(u, float)
    return (100 * u.mean(), 196 * u.std(ddof=1) / math.sqrt(len(u))) if len(u) > 1 else (float('nan'), float('nan'))

def read(stages):
    """Per arm and opponent, over the stages' maps (a map key seen in an earlier stage is dropped from the later)."""
    arms = list(stages[0]['arms']); rows = []; seen = set(); skip = {}
    for s in stages:
        keys = {}
        for l in open(s['feat']):
            r = json.loads(l); keys.setdefault(r['key'], r['name'])
        skip[s['name']] = {n for k, n in keys.items() if k in seen}; seen |= set(keys)
    print(f'Results against chy-draft18 ({" + ".join(s["name"] for s in stages)}; fresh ladder-v2 maps, our fuel {stages[0]["fuel"]}, bodies rt-Flp4 / rt-Mt3q unmetered, both sides)')
    print(f'{"arm":8s} {"spec":>12s} {"opp":>4s} {"cells changed":>14s} {"games":>7s} {"base win% there":>15s} {"changed cells (95% CI)":>24s} {"overall":>14s} {"3 / 4 / 5 picks, changed cells":>40s}  identical-check')
    out = {}
    for arm in arms:
        for o in stages[0]['arms'][arm]['opp']:
            u = []; bywin = []; N = 0; games = 0; byp = {3: [], 4: [], 5: []}; chk = [0, 0]; miss = 0; errs = 0
            for s in stages:
                if arm not in s['arms']: continue
                mp = [m for m in maps_of(s) if m[0] not in skip[s['name']]]; N += len(mp); picks = {m[0]: m[2] for m in mp}
                plan = json.load(open(f'{W}/plan-{s["name"]}.json')); res, meta = results(s, arm, o); base, _ = results(s, 'base', o)
                errs += (meta or {}).get('errors') or 0; reuse = plan[arm][o]['reuse']; other = {a2: results(s, a2, o)[0] for a2 in set(reuse.values())}
                for m in plan[arm][o]['changed']:
                    if m not in picks: continue
                    rs = other[reuse[m]] if m in reuse else res
                    d = [rs[(m, sd)][0] - base[(m, sd)][0] for sd in 'ab' if (m, sd) in rs and (m, sd) in base]
                    if len(d) < 2: miss += 1; continue
                    u.append(float(np.mean(d))); byp[picks[m]].append(u[-1]); games += 2; bywin.append(np.mean([base[(m, sd)][0] for sd in 'ab']))
                for m in plan[arm][o]['check']:
                    for sd in 'ab':
                        if (m, sd) in res and (m, sd) in base: chk[0] += 1; chk[1] += res[(m, sd)] == base[(m, sd)]
            if not u: print(f'{arm:8s} {o}: no games yet'); continue
            e = est(u); share = (len(u) + miss) / N; f = lambda x: f'{x[0]:+.2f} ±{x[1]:.2f}'
            out[f'{arm}-{o}'] = {'spec': stages[0]['arms'][arm]['spec'], 'opp': o, 'maps': N, 'changed_maps': len(u) + miss, 'share': share, 'games': games, 'changed': e,
                                 'overall': (e[0] * share, e[1] * share), 'base_win_changed': 100 * float(np.mean(bywin)), 'picks': {p: est(v) for p, v in byp.items()}, 'check': chk, 'missing': miss, 'errors': errs}
            print(f'{arm:8s} {stages[0]["arms"][arm]["spec"]:>12s} {o:>4s} {100 * share:6.1f}% ({len(u)}) {games:7d} {100 * np.mean(bywin):15.1f} {f(e):>24s} {e[0] * share:+7.2f} ±{e[1] * share:.2f} '
                  f'{" / ".join(f(est(byp[p])) for p in (3, 4, 5)):>40s}  {chk[1]}/{chk[0]}' + (f' [{miss} maps missing]' if miss else '') + (f' [{errs} errors]' if errs else ''))
    json.dump(out, open(f'{W}/read-{"-".join(s["name"] for s in stages)}.json', 'w'), indent=1)

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'read': read([stage(n) for n in sys.argv[2:]]); sys.exit(0)
    s = stage(sys.argv[2])
    if cmd == 'build': build(s)
    elif cmd == 'play':
        arg = lambda k, d: int(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
        play(s, arg('--jobs', 3), arg('--threads', 30))
