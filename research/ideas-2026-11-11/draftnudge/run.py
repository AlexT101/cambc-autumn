"""Play the draft-nudge arms: each arm is oc-dfuel-506 with only draft_model.h changed (nudge.py model + model.mjs cpp).
A draft change leaves every map whose team is unchanged byte-identical (local games are deterministic), so an arm plays
only the maps where its team differs from the base's; the base plays every map once.

    py run.py build STAGE            build the stage's arm bots, their teams on the stage's maps, and the suite dirs
    py run.py play STAGE [--jobs 6]  ab.py runs (both sides, Flp4 and Mt3q bodies, noise seed by suite), then STAGE.done
    py run.py read STAGE             paired table against the base
    py run.py pool STAGE STAGE..     the same over several stages' maps together

STAGE is a json in WORK/stages/: {feat, arms: {name: "dir:lam"}, fuel, noise: [k..], sub: {arm: n_suites}}."""
import json, os, subprocess, sys, time, math, collections, numpy as np
R = '/home/ubuntu/cambc-autumn/'; T = os.path.dirname(os.path.abspath(__file__))
D = os.path.expanduser('~/tmp-offload/draftnudge'); W = f'{D}/work'; BASE = 'variants/oc-dfuel-506'
BODY = {'F': 'Flp4', 'M': 'Mt3q'}

def stage(name): s = json.load(open(f'{W}/stages/{name}.json')); s['name'] = name; return s
def bot(arm): return BASE if arm == 'base' else f'variants/dn-{arm}'
def maps_of(s):
    """[(map name, path, suite index)] in file order, first row of a draft-lab key only."""
    out, seen, suites = [], set(), {}
    for l in open(s['feat']):
        r = json.loads(l)
        if r['key'] in seen or r['picks'] not in (3, 4, 5): continue
        seen.add(r['key']); su = suites.setdefault(r['set'], len(suites))
        out.append((r['name'], os.path.normpath(os.path.join(R, r['path'])), su, r['picks']))
    return out
def teams(s, arm):
    f = f'{W}/teams-{s["name"]}-{arm}.txt'
    return {l.split()[2]: l.split()[3] for l in open(f)}
def lab(arm): return f'{D}/labs/{arm}'
def group(s, su): return s['noise'][su % len(s['noise'])]
def sdir(s, arm, k): return f'{D}/suites/{s["name"]}-{arm}-k{k}'
def rname(s, arm, k, o): return f'dn-{s["name"]}-{arm}-dvn{k}{o}-fuel{s["fuel"]}'

def build(s):
    os.makedirs(f'{D}/labs', exist_ok=True); os.makedirs(f'{D}/suites', exist_ok=True)
    run = lambda *c: subprocess.run(c, cwd=R, check=True, capture_output=True, text=True).stdout
    open(f'{W}/teams-{s["name"]}-base.txt', 'w').write(run('node', 'tools/draftlab/model.mjs', 'teams', '--lab', 'replays/draftlab/draft10-f92', '--features', s['feat']))
    for arm, spec in s['arms'].items():
        if not os.path.exists(f'{lab(arm)}/model.json'): run(sys.executable, f'{T}/nudge.py', 'model', W, spec, lab(arm))
        if not os.path.isdir(f'{R}bots/{bot(arm)}'):
            run('./copybot', BASE, bot(arm))
            run('node', 'tools/draftlab/model.mjs', 'cpp', '--lab', lab(arm), '--out', f'{R}bots/{bot(arm)}/src/draft/draft_model.h')
            d = run('diff', '-rq', '-x', '.cambc', f'bots/{BASE}', f'bots/{bot(arm)}') if False else subprocess.run(['diff', '-rq', '-x', '.cambc', '-x', 'compile_commands.json', f'bots/{BASE}', f'bots/{bot(arm)}'], cwd=R, capture_output=True, text=True).stdout
            assert d.strip().splitlines() == [f'Files bots/{BASE}/src/draft/draft_model.h and bots/{bot(arm)}/src/draft/draft_model.h differ'], d
        open(f'{W}/teams-{s["name"]}-{arm}.txt', 'w').write(run('node', 'tools/draftlab/model.mjs', 'teams', '--lab', lab(arm), '--features', s['feat']))
    mp = maps_of(s); base = teams(s, 'base'); plan = {}
    for arm in ['base'] + list(s['arms']):
        tm = teams(s, arm); nsub = s.get('sub', {}).get(arm)
        for name, path, su, _ in mp:
            if nsub is not None and su >= nsub: continue
            if arm != 'base' and tm[name] == base[name]: continue
            k = group(s, su); d = sdir(s, arm, k); os.makedirs(d, exist_ok=True)
            link = f'{d}/{name}.map26a'
            if not os.path.lexists(link): os.symlink(path, link)
            plan.setdefault(arm, {}).setdefault(k, []).append(name)
    json.dump(plan, open(f'{W}/plan-{s["name"]}.json', 'w'))
    for arm, p in plan.items(): print(f'{arm}: {sum(map(len, p.values()))} maps ({100 * sum(map(len, p.values())) / len(mp):.1f}%), {4 * sum(map(len, p.values()))} games')
    print('total games', 4 * sum(len(v) for p in plan.values() for v in p.values()))

def done(s, arm, k, o, n):
    p = f'{R}replays/ab/{rname(s, arm, k, o)}/summary.json'
    if not os.path.exists(p): return False
    try: x = json.load(open(p))
    except ValueError: return False
    return x['games'] + x['errors'] >= 2 * n and x.get('release') is True and x.get('fuel') == s['fuel']
def save(s, arm, k, o):
    """Copy the run's per-game results out of replays/ (janitors thin batches): map, side, win, rounds."""
    x = json.load(open(f'{R}replays/ab/{rname(s, arm, k, o)}/summary.json')); rows = []
    for su in x['suites']:
        for m in json.load(open(R + su['batch'] + '/results.json'))['matches']:
            if m.get('winner') is None: continue
            rows.append([os.path.basename(m['map']).replace('.map26a', ''), 'a' if m['order'][0] == 0 else 'b', int(m['winner'] == 0), m.get('rounds')])
    meta = {k2: x.get(k2) for k2 in ('games', 'errors', 'oof', 'early_losses', 'handoff_failures', 'capped_drafts', 'wall_seconds', 'cambc', 'fuel', 'release')}
    os.makedirs(f'{D}/results', exist_ok=True)
    json.dump({'meta': meta, 'rows': rows}, open(f'{D}/results/{rname(s, arm, k, o)}.json', 'w'))

def play(s, jobs):
    plan = json.load(open(f'{W}/plan-{s["name"]}.json')); os.makedirs(f'{D}/logs', exist_ok=True)
    env = dict(os.environ, CAMBC_BIN=f'{R}tools/fastengine/runner/fastrunner', FASTRUNNER_MODE='native')
    todo = [(arm, int(k), o, len(v)) for arm, p in plan.items() for k, v in p.items() for o in 'FM']
    procs = {}; fails = 0
    while True:
        for key, p in list(procs.items()):
            if p.poll() is not None:
                del procs[key]
                if p.returncode or not done(s, *key): print('FAIL', key, flush=True); fails += 1
                else: save(s, *key[:3])
        left = [t for t in todo if not os.path.exists(f'{D}/results/{rname(s, *t[:3])}.json') and t not in procs]
        if not left and not procs: break
        if fails > 5: print('too many failures'); sys.exit(1)
        for t in left:
            if len(procs) >= jobs: break
            if done(s, *t): save(s, *t[:3]); continue
            arm, k, o, n = t; nm = rname(s, arm, k, o)
            cmd = [sys.executable, f'{R}tools/ab.py', bot(arm), f'variants/spar-dvn{k}-{BODY[o]}', '--no-test-draft', '--suites', sdir(s, arm, k),
                   '--name', nm, '--keep-replays', '60', '--fuel', str(s['fuel'])]
            procs[t] = subprocess.Popen(cmd, cwd=R, env=env, stdout=open(f'{D}/logs/{nm}.log', 'w'), stderr=subprocess.STDOUT)
        time.sleep(2)
    open(f'{W}/stages/{s["name"]}.done', 'w').write(time.strftime('%F %T') + f' fails {fails}\n')

def results(s, arm):
    """{(map, opp, side): (win, rounds)} over the arm's runs."""
    plan = json.load(open(f'{W}/plan-{s["name"]}.json')); out = {}; meta = []
    for k in plan.get(arm, {}):
        for o in 'FM':
            p = f'{D}/results/{rname(s, arm, int(k), o)}.json'
            if not os.path.exists(p): continue
            x = json.load(open(p)); meta.append(x['meta'])
            for mp, side, w, rounds in x['rows']: out[(mp, o, side)] = (w, rounds)
    return out, meta

def est(u, n_all=None):
    """Mean and 95% half-width in points of per-map units; with n_all, over n_all maps of which the rest are 0."""
    u = np.array(u, float)
    if n_all is not None: u = np.concatenate([u, np.zeros(n_all - len(u))])
    return (100 * u.mean(), 196 * u.std(ddof=1) / math.sqrt(len(u))) if len(u) > 1 else (float('nan'), float('nan'))

def read(s, quiet=False):
    mp = maps_of(s); base, bmeta = results(s, 'base'); bt = teams(s, 'base'); N = len(mp); picks = {m[0]: m[3] for m in mp}; out = {}
    bw = np.mean([v[0] for v in base.values()]) if base else float('nan')
    if not quiet:
        print(f'Results against oc-dfuel-506 ({s["name"]}: {N} fresh ladder-v2 maps, {s["fuel"]} fuel, bodies Flp4 / Mt3q, both sides). Base: {100 * bw:.1f}% of {len(base)} games '
              f'(Fish {100 * np.mean([v[0] for k, v in base.items() if k[1] == "F"]):.1f}, Mite {100 * np.mean([v[0] for k, v in base.items() if k[1] == "M"]):.1f}).')
        print(f'{"arm":6s} {"lam":>8s} {"maps changed":>12s} {"paired games":>12s} {"on changed maps":>18s} {"all maps: win% equiv (95% CI)":>32s} {"vs Fish":>14s} {"vs Mite":>14s} {"3 / 4 / 5 picks (all maps)":>30s}')
    for arm, spec in s['arms'].items():
        res, meta = results(s, arm); tm = teams(s, arm); nsub = s.get('sub', {}).get(arm)
        pool = [m for m in mp if nsub is None or m[2] < nsub]; ch = [m[0] for m in pool if tm[m[0]] != bt[m[0]]]
        unit = {g: {} for g in ('all', 'F', 'M')}; games = 0
        for m in ch:
            d = {o: [res[(m, o, sd)][0] - base[(m, o, sd)][0] for sd in 'ab' if (m, o, sd) in res and (m, o, sd) in base] for o in 'FM'}
            games += sum(map(len, d.values()))
            if d['F'] or d['M']: unit['all'][m] = float(np.mean(d['F'] + d['M']))
            for o in 'FM':
                if d[o]: unit[o][m] = float(np.mean(d[o]))
        n_all = len(pool); miss = len(ch) - len(unit['all'])
        e_ch = est(list(unit['all'].values())); e = {g: est(list(unit[g].values()), n_all - miss) for g in unit}
        ep = {p: est([v for m, v in unit['all'].items() if picks[m] == p], sum(1 for m in pool if m[3] == p)) for p in (3, 4, 5)}
        out[arm] = {'spec': spec, 'changed_pct': 100 * len(ch) / n_all, 'games': games, 'changed': e_ch, 'all': e['all'], 'F': e['F'], 'M': e['M'], 'picks': ep, 'missing_maps': miss,
                    'early': [m_.get('early_losses') for m_ in meta][:1], 'capped': sum((m_.get('capped_drafts') or {}).get('cand', 0) for m_ in meta), 'errors': sum(m_.get('errors') or 0 for m_ in meta)}
        if not quiet:
            f = lambda x: f'{x[0]:+.2f} ±{x[1]:.2f}'
            print(f'{arm:6s} {spec.split(":")[1]:>8s} {100 * len(ch) / n_all:11.1f}% {games:12d} {f(e_ch):>18s} {50 + e["all"][0]:13.2f}% ({50 + e["all"][0] - e["all"][1]:.2f}-{50 + e["all"][0] + e["all"][1]:.2f}) '
                  f'{f(e["F"]):>14s} {f(e["M"]):>14s}   {" / ".join(f(ep[p]) for p in (3, 4, 5))}' + (f'  [{miss} maps missing]' if miss else ''))
    json.dump(out, open(f'{W}/read-{s["name"]}.json', 'w'), indent=1)
    return out

def units(s, arm, skip=()):
    """Per-map units of an arm against the base in a stage: ({group: [unit per changed map]}, maps in the pool, games)."""
    mp = [m for m in maps_of(s) if m[0] not in skip]; base, _ = results(s, 'base'); bt = teams(s, 'base'); res, _ = results(s, arm); tm = teams(s, arm)
    u = {g: [] for g in ('all', 'F', 'M', 3, 4, 5)}; games = 0; npick = collections.Counter(m[3] for m in mp); nb = [0, 0]
    for name, _, _, p in mp:
        if tm[name] == bt[name]: continue
        d = {o: [res[(name, o, sd)][0] - base[(name, o, sd)][0] for sd in 'ab'] for o in 'FM'}; games += 4
        u['all'].append(float(np.mean(d['F'] + d['M']))); u['F'].append(float(np.mean(d['F']))); u['M'].append(float(np.mean(d['M']))); u[p].append(u['all'][-1])
    return u, len(mp), games, npick

def pool(stages):
    """One table over several stages' maps (a map key seen in an earlier stage is dropped from the later one)."""
    seen = set(); S = []
    for s in stages:
        keys = {}
        for l in open(s['feat']):
            r = json.loads(l); keys.setdefault(r['key'], r['name'])
        S.append((s, {n for k, n in keys.items() if k in seen})); seen |= set(keys)
    arms = [a for a in S[0][0]['arms'] if all(a in s['arms'] for s, _ in S)]
    bw = [v[0] for s, skip in S for k, v in results(s, 'base')[0].items() if k[0] not in skip]
    bo = {o: [v[0] for s, skip in S for k, v in results(s, 'base')[0].items() if k[0] not in skip and k[1] == o] for o in 'FM'}
    N = sum(len([m for m in maps_of(s) if m[0] not in skip]) for s, skip in S)
    print(f'Results against oc-dfuel-506 ({" + ".join(s["name"] for s, _ in S)}: {N} fresh ladder-v2 maps, {S[0][0]["fuel"]} fuel, bodies Flp4 / Mt3q, both sides). '
          f'Base: {100 * np.mean(bw):.1f}% of {len(bw)} games (Fish {100 * np.mean(bo["F"]):.1f}, Mite {100 * np.mean(bo["M"]):.1f}).')
    print(f'{"arm":6s} {"maps changed":>12s} {"paired games":>12s} {"on changed maps":>16s} {"all maps: win% equiv (95% CI)":>30s} {"vs Fish":>12s} {"vs Mite":>12s} {"3 / 4 / 5 picks (all maps)":>36s}')
    f = lambda x: f'{x[0]:+.2f} ±{x[1]:.2f}'; out = {}
    for arm in arms:
        U = {g: [] for g in ('all', 'F', 'M', 3, 4, 5)}; games = 0; npick = collections.Counter()
        try:
            for s, skip in S:
                u, n, g, npk = units(s, arm, skip); games += g; npick += npk
                for k in U: U[k] += u[k]
        except KeyError: print(f'{arm:6s} (games still missing)'); continue
        e = {g: est(U[g], N) for g in ('all', 'F', 'M')}; ep = {p: est(U[p], npick[p]) for p in (3, 4, 5)}; ec = est(U['all'])
        out[arm] = {'changed_pct': 100 * len(U['all']) / N, 'games': games, 'changed': ec, 'all': e['all'], 'F': e['F'], 'M': e['M'], 'picks': ep}
        print(f'{arm:6s} {100 * len(U["all"]) / N:11.1f}% {games:12d} {f(ec):>16s} {50 + e["all"][0]:11.2f}% ({50 + e["all"][0] - e["all"][1]:.2f}-{50 + e["all"][0] + e["all"][1]:.2f}) '
              f'{f(e["F"]):>12s} {f(e["M"]):>12s}   {" / ".join(f(ep[p]) for p in (3, 4, 5))}')
    json.dump(out, open(f'{W}/pool-{"-".join(s["name"] for s, _ in S)}.json', 'w'), indent=1)

if __name__ == '__main__':
    if sys.argv[1] == 'pool': pool([stage(n) for n in sys.argv[2:]]); sys.exit(0)
    cmd, s = sys.argv[1], stage(sys.argv[2])
    if cmd == 'build': build(s)
    elif cmd == 'play': play(s, int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 6)
    elif cmd == 'read': read(s)
