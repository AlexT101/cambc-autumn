"""The fresh-map gate (diverse-panel.md "Fresh-map gate", TEST-STANDARD rule 5): dgate's paired sequential test, with
opponents that draft from map features and a map pool of the 128 ladder maps plus 1024 fresh ladder-v2 maps.

    py fgate.py CAND REF [--max-seeds N] [--jobs 8] [--seed S] [--no-run] [--ci 0.25] [--fuel N]

- Opponents: noise block k plays v87 noise seed k (dgate's spar-dvnK bodies with Fish's locks or Mite's tribute habit),
  drafting with Fish's or Mite's pick model (fitgen.py, patch_fm.py: spar-dvnK-Flp / -Mt3p). There is no per-map
  table, so they play the same on every map. Body versions (VERSIONS; --fish-body, --mite-body): Flp2 adds Fish's
  banking rule and emblem orders (fishfid/patch_fish2.py; closer to live); Flp3 and Mt3q (the defaults) write Fish's
  and Mite's own priority encodings (fishfid/patch_prio.py), so the opponent classifier reads them as Fish and Mite;
  Flp4 (Fish's default) adds cohesion (fishfid/patch_coh.py: a group no ally is nearer to is worth 0.5x).
- Maps: each block plays the ladder maps and one 128-map slice of the fresh pool (slice (k - 1) mod 8), both sides,
  against both bodies.
- Decision: the SPRTs, the ZONE and the NARROWED stop read only the fresh units, so a gain that holds only on the
  ladder maps cannot pass. Ladder, fresh and pooled reads, and the ladder - fresh gap, are all reported.
- Fuel: --fuel N applies to both teams and uses separate run/result names and verified fuel metadata.
- Map class (one-site / multi-site) comes from the map's features (altars, altar_centre), not its name.
"""
import argparse, json, math, os, random, subprocess, sys, time, fcntl, numpy as np
T = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(T, '..', '..', 'ideas-2026-11-08', 'diverse-tools'))
import dgate  # noqa: E402
from dgate import R, LOCKS, LOGS, CAMBC, local, ab  # noqa: E402
FRESH = os.path.expanduser('~/tmp-offload/diverse/fresh')
POOL = [f'{FRESH}/pool/f{j}' for j in range(8)]
BODY = {'F': 'Flp', 'M': 'Mt3p'}
# Later body versions (--fish-body), each a patch on the one before; a run name carries its version past the first.
FF = '../fishfid'
# version: (the version it patches, [patch command after the bot dir]). Flp3/Mt3q write Fish's/Mite's own priorities.
VERSIONS = {'Flp2': ('Flp', [f'{FF}/patch_fish2.py']), 'Flp3': ('Flp2', [f'{FF}/patch_prio.py', 'F', 'order']),
            'Mt3q': ('Mt3p', [f'{FF}/patch_prio.py', 'M', 'near']),
            'Flp4': ('Flp3', [f'{FF}/patch_coh.py', '0.5'])}  # Flp4: cohesion, Fish's "joins, never partitions"
FISH_PATCHES = [v for v in VERSIONS if v.startswith('Fl')]
MITE_PATCHES = [v for v in VERSIONS if v.startswith('Mt')]
def tag(o): return '' if BODY[o] in ('Flp', 'Mt3p') else BODY[o].removeprefix('Fl').removeprefix('Mt3')
ENG = 'e' + CAMBC.replace('.', '')
FUEL = None
def fuel_tag(): return '' if FUEL is None else f'-fuel{FUEL}'

def feats():
    out = {}
    for f in ('feat-ladder.jsonl', 'feat-v2.jsonl'):
        for line in open(f'{FRESH}/{f}'):
            x = json.loads(line); out[x['name'].replace('_', '-')] = x['f']
    return out
FT = feats()
def one_site(m):
    f = FT.get(m.replace('_', '-'))
    if f is None: return None  # features.mjs could not measure it: in neither class
    return f['altars'] == 1 or (f['altars'] == 2 and (f['altar_centre'] or 0) < 0.06)

def mdir(k, o): return f'variants/spar-dvn{k}-{BODY[o]}'
def slice_of(k): return (k - 1) % len(POOL)
def suites(k): return [('L', 'ladder', 2 * 128), (f'f{slice_of(k)}', POOL[slice_of(k)], 2 * len(os.listdir(POOL[slice_of(k)])))]
def rname(bot, k, o, s): return f'fg{ENG}-{os.path.basename(bot.rstrip("/")).removeprefix("oc-")}-dvn{k}{o}{tag(o)}-{s}{fuel_tag()}'
def done(n, games):
    p = f'{R}replays/ab/{n}/summary.json'
    if not os.path.exists(p): return False
    try:
        with open(p) as fh: s = json.load(fh)
    except ValueError: return False
    return s['games'] + s['errors'] >= games and s.get('release') is True and s.get('cambc') == CAMBC and s.get('fuel') == FUEL

def build_seed(k):
    dgate.NEW = True; dgate.build_seed(k)  # spar-dvnK-Fl / -Mt3 (hash-table bodies), the bases
    mark = f'{LOCKS}/built-dvn{k}-fm'
    if os.path.exists(mark): return
    with open(f'{LOCKS}/build-dvn{k}-fm', 'w') as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        if os.path.exists(mark): return
        for o, base in (('F', 'Fl'), ('M', 'Mt3')):
            d = f'{R}bots/{mdir(k, o)}'
            p = 'Flp' if o == 'F' else 'Mt3p'
            if not os.path.isdir(f'{R}bots/variants/spar-dvn{k}-{p}'):
                subprocess.run([f'{R}copybot', f'variants/spar-dvn{k}-{base}', f'variants/spar-dvn{k}-{p}'], cwd=R, check=True, capture_output=True)
                subprocess.run([sys.executable, f'{T}/patch_fm.py', f'{R}bots/variants/spar-dvn{k}-{p}', o, str(k)], cwd=R, check=True, capture_output=True)
        open(mark, 'w').close()

def build_body(k, v):
    if v not in VERSIONS: return
    base, cmd = VERSIONS[v]
    build_body(k, base)
    mark = f'{LOCKS}/built-dvn{k}-{v}'
    if os.path.exists(mark): return
    with open(f'{LOCKS}/build-dvn{k}-{v}', 'w') as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        if os.path.exists(mark): return
        d = f'{R}bots/variants/spar-dvn{k}-{v}'
        if not os.path.isdir(d):
            subprocess.run([f'{R}copybot', f'variants/spar-dvn{k}-{base}', f'variants/spar-dvn{k}-{v}'], cwd=R, check=True, capture_output=True)
            subprocess.run([sys.executable, f'{T}/{cmd[0]}', d] + cmd[1:], cwd=R, check=True, capture_output=True)
        open(mark, 'w').close()

def build_version(k):
    build_seed(k)
    build_body(k, BODY['F']); build_body(k, BODY['M'])

class Runner(dgate.Runner):
    def want(self, bot, k, o, s, suite, games):
        n = rname(bot, k, o, s)
        if done(n, games): return True
        self.poll()
        if n in self.procs or len(self.procs) >= self.jobs or dgate.running_elsewhere(n): return False
        lock = f'{LOCKS}/{n}'
        try: os.close(os.open(lock, os.O_CREAT | os.O_EXCL))
        except FileExistsError:
            if time.time() - os.path.getmtime(lock) < 4 * 3600: return False
            os.unlink(lock); os.close(os.open(lock, os.O_CREAT | os.O_EXCL))
        cmd = [sys.executable, f'{R}tools/ab.py', bot, mdir(k, o), '--no-test-draft', '--suites', suite, '--name', n, '--keep-replays', '1']
        if FUEL is not None: cmd += ['--fuel', str(FUEL)]
        self.procs[n] = (subprocess.Popen(cmd, cwd=R, env=self.env, stdout=open(f'{LOGS}/{n}.log', 'w'), stderr=subprocess.STDOUT), lock)
        return False

def block_units(cand, ref, k, rng):
    """{'L'|'fresh': {group: [units]}}: a unit is a map's 0.5 + CAND's mean minus REF's over the block's games on it."""
    out = {}
    for s, _, _ in suites(k):
        key = 'L' if s == 'L' else 'fresh'
        diff = {}
        for o in 'FM':
            x, y = local.cells(rname(cand, k, o, s)), local.cells(rname(ref, k, o, s))
            for c in x.keys() & y.keys(): diff.setdefault(c[0], {}).setdefault(o, []).append(x[c] - y[c])
        order = sorted(diff); rng.shuffle(order)
        g = {'all': [], 'F': [], 'M': [], 'one': [], 'multi': []}
        for m in order:
            v = [d for o in diff[m] for d in diff[m][o]]
            g['all'].append(0.5 + float(np.mean(v)))
            for o in diff[m]: g[o].append(0.5 + float(np.mean(diff[m][o])))
            cls = one_site(m)
            if cls is not None: g['one' if cls else 'multi'].append(0.5 + float(np.mean(v)))
        out[key] = g
    return out

def est(u):
    u = np.array(u) - 0.5
    return [round(100 * u.mean(), 3), round(196 * u.std() / math.sqrt(len(u)), 3)] if len(u) > 1 else None

def main():
    global FUEL
    ap = argparse.ArgumentParser(); ap.add_argument('cand'); ap.add_argument('ref')
    ap.add_argument('--sprt', default='0.505,0.5075'); ap.add_argument('--low', default='0.4975,0.50')
    ap.add_argument('--max-seeds', type=int, default=1000); ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--ahead', type=int, default=2); ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--fuel', type=int, help='matched fuel per turn for both teams; separate run/cache namespace')
    ap.add_argument('--no-run', action='store_true'); ap.add_argument('--zone-stop', action='store_true')
    ap.add_argument('--ci', type=float, default=0.25, help='NARROWED once the fresh 95%% CI half-width is this many points')
    ap.add_argument('--fish-body', default='Flp4', choices=['Flp'] + FISH_PATCHES, help='Fish body version (Flp4 from 2026-11-10 ~01:00, Flp3 from ~00:30, Flp2 from 2026-11-09 23:40, Flp before)')
    ap.add_argument('--mite-body', default='Mt3q', choices=['Mt3p'] + MITE_PATCHES, help='Mite body version (Mt3q from 2026-11-10 ~00:30, Mt3p before)')
    ap.add_argument('--min-blocks', type=int, default=8, help='blocks before NARROWED can stop (every fresh slice played once)')
    a = ap.parse_args(); p0, p1 = map(float, a.sprt.split(',')); q0, q1 = map(float, a.low.split(','))
    if a.fuel is not None and a.fuel <= 0: ap.error('--fuel must be positive')
    FUEL = a.fuel
    BODY["F"], BODY["M"] = a.fish_body, a.mite_body
    lo, screen_hi, live_hi = math.log(0.05 / 0.95), math.log(0.95 / 0.05), math.log(99)
    run = Runner(a.jobs); U = {'L': {}, 'fresh': {}}; k = 1; outcome = None
    screen_at = low_at = high_h0_at = zone_at = None
    while k <= a.max_seeds:
        if not a.no_run:
            for j in range(k, min(k + a.ahead, a.max_seeds) + 1):
                build_version(j)
                for o in 'FM':
                    for s, suite, games in suites(j):
                        for bot in (a.ref, a.cand): run.want(bot, j, o, s, suite, games)
        if not all(done(rname(bot, k, o, s), g) for o in 'FM' for s, _, g in suites(k) for bot in (a.cand, a.ref)):
            if a.no_run: break
            time.sleep(20); continue
        for key, g in block_units(a.cand, a.ref, k, random.Random(a.seed * 1000 + k)).items():
            for gg, u in g.items(): U[key].setdefault(gg, []).extend(u)
        sc = U['fresh']['all']; hl, ll = ab.llr(sc, p0, p1), ab.llr(sc, q0, q1)
        d = np.array(sc) - 0.5; se = d.std() / math.sqrt(len(d))
        rd = lambda u: f'{100 * (np.mean(u) - 0.5):+.2f}' if u else 'n/a'
        print(f'block {k:3d} (noise {k}, fresh f{slice_of(k)}): fresh {len(sc)} units {100*d.mean():+.2f} ±{196*se:.2f} '
              f'LLR high {hl:+.2f} low {ll:+.2f} [{lo:.2f} | {screen_hi:.2f} | live {live_hi:.2f}] | ladder {rd(U["L"]["all"])} '
              f'pooled {rd(U["L"]["all"] + sc)} | fresh F {rd(U["fresh"]["F"])} M {rd(U["fresh"]["M"])} '
              f'one {rd(U["fresh"]["one"])} multi {rd(U["fresh"]["multi"])}', flush=True)
        if screen_at is None and ll <= lo: outcome = 'REJECT'; break
        if low_at is None and ll >= screen_hi: low_at = len(sc)
        if high_h0_at is None and screen_at is None and hl <= lo: high_h0_at = len(sc)
        if zone_at is None and low_at is not None and high_h0_at is not None:
            zone_at = len(sc); print(f'ZONE at block {k}', flush=True)
            if a.zone_stop: outcome = 'ZONE'; break
        if screen_at is None and k >= a.min_blocks and 196 * se <= a.ci:
            outcome = 'NARROWED' + (' (ZONE crossed)' if zone_at else ''); break
        if screen_at is None and high_h0_at is None and hl >= screen_hi:
            screen_at = len(sc); print(f'ACCEPT (screen H1) at block {k}', flush=True)
        if screen_at is not None and hl >= live_hi:
            post = d[screen_at:]
            outcome = 'LIVE BAR H1' if len(post) == 0 or post.mean() >= 0 else 'H1 but the post-screen blocks read negative: not live'
            break
        k += 1
    while run.procs: run.poll(); time.sleep(5)
    if outcome is None: outcome = 'ACCEPT (screen), live bar undecided' if screen_at is not None else 'undecided'
    Lu, Fu = U['L'].get('all', []), U['fresh'].get('all', [])
    n = min(len(Lu), len(Fu))
    gap = est(list(0.5 + np.array(Lu[:n]) - np.array(Fu[:n]))) if n > 1 else None  # paired by block position
    res = {'cand': a.cand, 'ref': a.ref, 'outcome': outcome, 'blocks': k if outcome != 'undecided' else k - 1, 'cambc': CAMBC,
           'fuel': FUEL, 'bodies': f'pick-model ({BODY["F"]}/{BODY["M"]})', 'fresh': est(Fu), 'ladder': est(Lu), 'pooled': est(Lu + Fu), 'ladder_minus_fresh': gap,
           'fresh_fish': est(U['fresh'].get('F', [])), 'fresh_mite': est(U['fresh'].get('M', [])),
           'fresh_one_site': est(U['fresh'].get('one', [])), 'fresh_multi_site': est(U['fresh'].get('multi', [])),
           'ladder_fish': est(U['L'].get('F', [])), 'ladder_mite': est(U['L'].get('M', [])),
           'fresh_units': len(Fu), 'llr_high': round(ab.llr(Fu, p0, p1), 3) if Fu else None, 'llr_low': round(ab.llr(Fu, q0, q1), 3) if Fu else None,
           'zone_at_units': zone_at, 'screen_at_units': screen_at, 'low_h1_at_units': low_at, 'high_h0_at_units': high_h0_at}
    print(json.dumps(res))
    if not a.no_run: json.dump(res, open(f'{LOGS}/fgate-{os.path.basename(a.cand.rstrip("/"))}--{os.path.basename(a.ref.rstrip("/"))}{tag("F")}{tag("M")}{fuel_tag()}.json', 'w'))

if __name__ == '__main__':
    main()
