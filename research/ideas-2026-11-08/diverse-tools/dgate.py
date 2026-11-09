"""The diverse gate (diverse-panel.md "One gate"): screen, confirm and live bar in one sequential test.

    py dgate.py CAND REF [--stage screen|live] [--max-seeds 64] [--jobs 6] [--seed S]

CAND and REF are bot dirs under bots/ with params::test_draft off. Both play the 128 ladder maps, both sides, with
their own drafts, against Fish's and Mite's live picks (spar tables) played by:
  block 0: v87 (spar-o25-F/M) and v91 (spar-oc29-F/M), deterministic;
  block k: v87 noise seed k (spar-dvnk-F/M: knobs redrawn every 100 rounds, seeded per game), each a fresh draw.
A unit is a (block, map): 0.5 + CAND's mean minus REF's over the block's games on that map. Blocks are read in order
with two of ab.py's SPRTs (bounds ln(0.05/0.95), ln(0.95/0.05)): a low one at 0.4975/0.50 and a high one at
0.505/0.5075 (rule 0: pass only above 50.5%). REJECT when the low one reaches H0; ACCEPT (screen) when the high one
reaches H1; ZONE (the coordinator's call) once the low one has reached H1 and the high one H0; else it plays on.
After ACCEPT it continues to the live bar (99%) at ln(99) = 4.595, reached by continuing on fresh noise seeds the screen never saw, whose own mean must
not be negative. Runs (spar-c<tag>-<member><F|M>) are reused, so a changed bot needs a new dir; REF's runs serve every
candidate. Noise seeds past those built are built on demand (seed 1310000 + k)."""
import argparse, json, math, os, random, re, subprocess, sys, time, numpy as np
T = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(T, '..', 'spar-tools')); sys.path.insert(0, os.path.join(T, '..', '..', '..', 'tools'))
import local, spar_ab, ab  # noqa: E402
R = local.R; LOCKS = os.path.expanduser('~/tmp-offload/diverse/locks'); LOGS = os.path.expanduser('~/tmp-offload/diverse/gate-logs')
DIRS = {'o25': 'spar-o25', 'o29': 'spar-oc29'}

def block(k): return [('o25', 'F'), ('o25', 'M'), ('o29', 'F'), ('o29', 'M')] if k == 0 else [(f'dvn{k}', 'F'), (f'dvn{k}', 'M')]
def mdir(b, o): return f'variants/{DIRS.get(b, "spar-" + b)}-{o}'
def done(n): return os.path.exists(f'{R}replays/ab/{n}/summary.json')
def release(n): return json.load(open(f'{R}replays/ab/{n}/summary.json')).get('release') is True

def rname(bot, b, o):
    """The run of (bot vs member): an existing release run under spar_ab's names, else a new name. Runs from before
    ab.py played release builds (no 'release' key: legacy spar-c25-o29F and the like) are never paired with release ones."""
    tag = os.path.basename(bot.rstrip('/')).removeprefix('oc-')
    names = [f'spar-c{tag}-{b}{o}', f'spar-c{tag.removeprefix("base")}-{b}{o}', f'spar-c{tag}-{b}{o}-rel']
    for n in names:
        if done(n) and release(n): return n
    return names[2] if done(names[0]) else names[0]

def build_seed(k):
    if all(os.path.isdir(f'{R}bots/{mdir(f"dvn{k}", o)}') for o in 'FM'): return
    subprocess.run([sys.executable, f'{T}/bodies.py', f'n{1310000 + k}'], cwd=R, check=True, capture_output=True)
    subprocess.run([f'{R}research/ideas-2026-11-08/spar-tools/makespar.sh', f'variants/dvp-n{k}', f'dvn{k}'], cwd=R,
                   check=True, capture_output=True)

def running_elsewhere(n):
    ps = subprocess.run(['ps', '-eww', '-o', 'args'], capture_output=True, text=True).stdout
    return any('ab.py' in l and re.search(rf'--name {re.escape(n)}(\s|$)', l) for l in ps.splitlines())

class Runner:
    def __init__(self, jobs):
        self.jobs, self.procs = jobs, {}
        os.makedirs(LOCKS, exist_ok=True); os.makedirs(LOGS, exist_ok=True)
        self.env = dict(os.environ, CAMBC_BIN=f'{R}tools/fastengine/runner/fastrunner', FASTRUNNER_MODE='native')
    def poll(self):
        for n, (p, lock) in list(self.procs.items()):
            if p.poll() is not None:
                os.unlink(lock) if os.path.exists(lock) else None; del self.procs[n]
                if p.returncode: print(f'FAIL {n} (exit {p.returncode}; log {LOGS}/{n}.log)', flush=True)
    def want(self, bot, b, o):
        """Start (bot vs member) unless finished, running here or elsewhere; True once it is finished."""
        n = rname(bot, b, o)
        if done(n): return True
        self.poll()
        if n in self.procs or len(self.procs) >= self.jobs or running_elsewhere(n): return False
        lock = f'{LOCKS}/{n}'
        try: os.close(os.open(lock, os.O_CREAT | os.O_EXCL))
        except FileExistsError:
            if time.time() - os.path.getmtime(lock) < 4 * 3600: return False
            os.unlink(lock); os.close(os.open(lock, os.O_CREAT | os.O_EXCL))
        cmd = [sys.executable, f'{R}tools/ab.py', bot, mdir(b, o), '--no-test-draft', '--suites', 'ladder', '--name', n,
               '--keep-replays', '1']
        self.procs[n] = (subprocess.Popen(cmd, cwd=R, env=self.env, stdout=open(f'{LOGS}/{n}.log', 'w'),
                                          stderr=subprocess.STDOUT), lock)
        return False

def units_opp(cand, ref, k, order):
    """{F|M: units}: as units(), but each opponent's picks apart."""
    out = {}
    for o in 'FM':
        diff = {}
        for b, oo in block(k):
            if oo != o: continue
            x, y = local.cells(rname(cand, b, o)), local.cells(rname(ref, b, o))
            for c in x.keys() & y.keys(): diff.setdefault(c[0], []).append(x[c] - y[c])
        out[o] = [0.5 + float(np.mean(diff[m])) for m in order if m in diff]
    return out

def units(cand, ref, k, order):
    diff = {}
    for b, o in block(k):
        nx, ny = rname(cand, b, o), rname(ref, b, o)
        assert release(nx) and release(ny), f'refusing to pair non-release runs: {nx}, {ny}'
        x, y = local.cells(nx), local.cells(ny)
        for c in x.keys() & y.keys(): diff.setdefault(c[0], []).append(x[c] - y[c])
    return [0.5 + float(np.mean(diff[m])) for m in order if m in diff]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cand'); ap.add_argument('ref')
    ap.add_argument('--stage', choices=['screen', 'live'], default='live'); ap.add_argument('--sprt', default='0.505,0.5075')
    ap.add_argument('--max-seeds', type=int, default=1000); ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--ahead', type=int, default=3, help='blocks played ahead of the one read'); ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--low', default='0.4975,0.50', help='the reject SPRT (three-way decision)')
    ap.add_argument('--single', action='store_true', help='the old single SPRT at --sprt: its H0 ends the test')
    ap.add_argument('--no-run', action='store_true', help='decide from cached games only; launch nothing')
    ap.add_argument('--zone-stop', action='store_true', help='stop at a ZONE crossing (default: play on)')
    ap.add_argument('--ci', type=float, default=0.25, help='stop as NARROWED once the 95%% CI half-width is this many '
                    'points: 0.25 tells +0.25 from 0 and leaves each opponent half at ~0.35')
    a = ap.parse_args(); p0, p1 = map(float, a.sprt.split(',')); q0, q1 = map(float, a.low.split(','))
    lo, screen_hi, live_hi = math.log(0.05 / 0.95), math.log(0.95 / 0.05), math.log(99)
    maps = None
    run = Runner(a.jobs); scores, screen_at, outcome, k = [], None, None, 0
    low_at = high_h0_at = zone_at = None  # first crossings: the low SPRT's H1, the high SPRT's H0
    opp = {'F': [], 'M': []}
    while k <= a.max_seeds:
        if not a.no_run:
            for j in range(k, min(k + a.ahead, a.max_seeds) + 1):  # keep the next blocks playing
                if j: build_seed(j)
                for b, o in block(j):
                    for bot in (a.ref, a.cand): run.want(bot, b, o)
        if not all(done(rname(bot, b, o)) for b, o in block(k) for bot in (a.cand, a.ref)):
            if a.no_run: break
            time.sleep(20); continue
        if maps is None: maps = sorted({m for m, _ in local.cells(rname(a.ref, 'o29', 'F'))})
        order = list(maps); random.Random(a.seed * 1000 + k).shuffle(order)
        for o, u in units_opp(a.cand, a.ref, k, order).items(): opp[o] += u
        scores += units(a.cand, a.ref, k, order); hl, ll = ab.llr(scores, p0, p1), ab.llr(scores, q0, q1)
        d = np.array(scores) - 0.5; se = d.std() / math.sqrt(len(d))
        tag = 'v87+v91' if k == 0 else f'noise {k}'
        print(f'block {k:2d} ({tag}): {len(scores)} units, {100*d.mean():+.2f} pts ±{196*se:.2f}, '
              f'LLR high {hl:+.2f}' + ('' if a.single else f' low {ll:+.2f}') +
              f' [{lo:.2f} | {screen_hi:.2f} | live {live_hi:.2f}]', flush=True)
        if a.single:
            if hl <= lo: outcome = 'H0'; break
        else:
            # REJECT: the low SPRT reaches H0. ACCEPT: the high SPRT reaches H1 (then on to the live bar).
            # ZONE: the low SPRT has reached H1 (not below ~50) and the high one H0 (not above ~50.75).
            if screen_at is None and ll <= lo: outcome = 'REJECT'; break
            if low_at is None and ll >= screen_hi: low_at = len(scores)
            if high_h0_at is None and screen_at is None and hl <= lo: high_h0_at = len(scores)
            if zone_at is None and low_at is not None and high_h0_at is not None:
                zone_at = len(scores); print(f'ZONE at block {k} ({len(scores)} units)', flush=True)
                if a.zone_stop: outcome = 'ZONE'; break
            if screen_at is None and len(d) > 1000 and 196 * se <= a.ci:
                outcome = 'NARROWED' + (' (ZONE crossed)' if zone_at else ''); break
        if screen_at is None and high_h0_at is None and hl >= screen_hi:
            screen_at = len(scores); print(f'ACCEPT (screen H1) at block {k} ({len(scores)} units)', flush=True)
            if a.stage == 'screen': outcome = 'ACCEPT (screen)'; break
        if screen_at is not None and hl >= live_hi:
            post = d[screen_at:]
            ok = len(post) == 0 or post.mean() >= 0
            outcome = 'LIVE BAR H1' if ok else 'H1 but the post-screen seeds read negative: not live'
            break
        k += 1
    while run.procs: run.poll(); time.sleep(5)
    post = (np.array(scores[screen_at:]) - 0.5) if screen_at is not None else np.array([])
    if outcome is None: outcome = 'ACCEPT (screen), live bar undecided' if screen_at is not None else 'undecided'
    games = sum(len(block(j)) for j in range(min(k, a.max_seeds) + 1)) * 256
    d = np.array(scores) - 0.5
    def est(u):
        u = np.array(u) - 0.5
        return [round(100 * u.mean(), 3), round(196 * u.std() / math.sqrt(len(u)), 3)] if len(u) else None
    res = {'cand': a.cand, 'ref': a.ref, 'outcome': outcome, 'blocks': k + 1 if outcome != 'undecided' else k,
           'units': len(scores), 'pts': round(100 * d.mean(), 3) if len(d) else None,
           'ci95': round(196 * d.std() / math.sqrt(len(d)), 3) if len(d) else None,
           'llr_high': round(ab.llr(scores, p0, p1), 3), 'llr_low': round(ab.llr(scores, q0, q1), 3),
           'fish': est(opp['F']), 'mite': est(opp['M']), 'zone_at_units': zone_at,
           'screen_at_units': screen_at, 'low_h1_at_units': low_at, 'high_h0_at_units': high_h0_at,
           'post_screen_pts': round(100 * post.mean(), 3) if len(post) else None, 'cand_games': len(scores) * 4 + (512 if scores else 0)}
    print(json.dumps(res))
    if not a.no_run: json.dump(res, open(f'{LOGS}/dgate-{os.path.basename(a.cand.rstrip("/"))}.json', 'w'))

if __name__ == '__main__':
    main()
