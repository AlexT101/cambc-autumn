#!/usr/bin/env python3
"""Unattended live-gate scheduler (2026-11-08).

Loop: while the live version's r2 gate runs, prepare (build + smoke) the next candidate. When the gate reaches its
n (all its planned r2 groups finished; cut after core when a newer ocean oc-baseNN is waiting, except for the v86
baseline), and nothing is in flight, submit the candidate, activate (pin) it and plan its r2 core (priority 99) and
ext (90). Below 100, so the runner's quota reserve (10/hour for teammates) stays free.

Candidates, in order: the newest bots/ocean commit naming oc-baseNN with NN above the last ocean submitted, whose
committed bots/ocean equals bots/variants/oc-baseNN; else the highest-priority untested ~/tmp-offload/live-queue.txt
line (`prio | dir | base | result | agent | share`; ties: oldest), marked in live-queue.done. No candidate: the
live version stays up.

Outside submissions (2026-11-09): each loop reads `submissions list --json`. A version not in our history (a
teammate's upload) is logged and wakes the agent once; if live or selected is not our newest history version, the
scheduler writes PAUSE and submits nothing until an agent has checked and removed it (the runner itself creates
groups only while live == selected and marks groups in flight at a switch suspect). submit() activates only the
version whose note is ours, never the newest version blindly.

Each finished gate appends to gates.jsonl and touches ../parked/live-gate.ready (the coordinator respawns the
reporting agent). Log: sched.log. State: state.json. Stop: touch STOP in the state dir.

Run: setsid nohup py tools/live_sched.py >> ~/tmp-offload/handoff/sched/sched.out 2>&1 < /dev/null &
Its state dir (LIVE_SCHED_DIR, default ~/tmp-offload/handoff/sched) holds state.json, sched.log, gates.jsonl,
refsets.json, build/ and the STOP / PAUSE / HOLD files; wake files go to its parent's parked/.
"""
import datetime, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / 'tools'))
import ladder_scrims as ls  # noqa: E402
from ladder_version_check import VersionCheck  # noqa: E402
from ladder_opp_check import OpponentDetector  # noqa: E402

H = Path(os.environ.get('LIVE_SCHED_DIR', Path.home() / 'tmp-offload/handoff/sched'))
HAND = H.parent
Q, QDONE = Path('/home/ubuntu/tmp-offload/live-queue.txt'), Path('/home/ubuntu/tmp-offload/live-queue.done')
STATE, LOG = H / 'state.json', H / 'sched.log'
BASELINE = 86          # every candidate's gate pairs against v86's r2 games: never cut it
# 2026-11-10 (user): no v1 probes. Each one drained live testing ~10-15 min an hour to switch the selection to v1.
# Opponent changes use a rolling observation snapshot, separate from the fixed testing pins.
VERSION_CHECK = False
# 2026-11-12 (user): v115 rests on the book; candidates go live only in quota-sized batches (live_batches.py), which
# replaces the gate/submit flow below.
BATCH_MODE = True
CORE_GROUPS = 32       # r2 core = 16 groups x 2 opponents
NULL_A_REFS = {'fish': 'r2', 'mite': 'r3'}
NULL_A_MITE_SOURCE = '01a1bf36-e601-756a-8b37-a90ad3d84ae0'


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def log(msg):
    with LOG.open('a') as f:
        f.write(f'{now()} {msg}\n')


def sh(cmd, cwd=None, timeout=1800):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, errors='replace')
    return r.returncode, r.stdout + r.stderr


def load():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {'history': [{'version': 86, 'label': 'oc-base23', 'kind': 'ocean', 'commit': 'dd7002a8',
                         'base_version': 85}], 'ocean_nn': 23, 'prepared': None, 'reported': [], 'failed': []}


def save(st):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(st, indent=1))
    tmp.replace(STATE)


def submissions():
    out = ls.cambc('submissions', 'list')
    m = re.search(r'Live:\s*(\d+)\s+Selected:\s*(\d+)', out)
    rows = {int(v): s for v, s in re.findall(r'^v(\d+)\s+(\S+)', out, re.M)}
    return int(m.group(1)), int(m.group(2)), rows


def submissions_json():
    return json.loads(ls.cambc('submissions', 'list', '--json'))


def wake(rec):
    (HAND / 'parked').mkdir(exist_ok=True)
    f = HAND / 'parked/live-gate.ready'
    if rec.get('event_id') and any(e.get('event_id') == rec['event_id'] for e in ls.read_jsonl(f)):
        return
    ls.append_jsonl(f, rec)


def outside_check(st, allowed=None):
    """Logs versions we did not submit, and pauses when live/selected is not our newest version (in batch mode: not
    one of `allowed`). Returns the submissions listing to go on, else False."""
    d = submissions_json()
    ours = {h['version'] for h in st['history']}
    seen = set(st.setdefault('outside', []))
    for x in d.get('submissions', []):
        v = x['version']
        if v > max(ours) and v not in seen:
            log(f"OUTSIDE submission v{v} (uploader {x.get('uploadedBy', '?')[:8]}, created {x.get('createdAt')}, "
                f"status {x.get('status')}): {x.get('note', '')[:90]}")
            st['outside'].append(v)
            save(st)
            wake({'outside': v, 'note': x.get('note'), 'uploader': x.get('uploadedBy'), 'at': now()})
    live, sel, exp = d['active']['version'], d['selected']['version'], max(ours)
    allowed = allowed or {exp}
    if live not in allowed or sel not in allowed:
        why = f'live v{live} selected v{sel}, expected our v{"/v".join(map(str, sorted(allowed)))}'
        if not (H / 'PAUSE').exists():
            log(f'PAUSE: {why}; not submitting until an agent checks and removes sched/PAUSE')
            (H / 'PAUSE').write_text(why + '\n')
            wake({'pause': why, 'at': now()})
        return False
    return d


# ---------------------------------------------------------------- gate progress

def refsets():
    """Opponent -> ref set new gates play (refsets.json here; read each time, so a repin needs no restart)."""
    f = H / 'refsets.json'
    return json.loads(f.read_text()) if f.exists() else {'fish': 'r2', 'mite': 'r2'}


def gate_refsets(candidate):
    """Null-a pairs with historical v98; ordinary arms keep the global testing pins."""
    if candidate.get('required_refsets'):
        required = candidate['required_refsets']
        if refsets() != required:
            raise ValueError('candidate required testing pins are not active; no fallback')
        _, _, finished, _, refs = ls.state()
        for opp, source in candidate['required_sources'].items():
            if refs.get((required[opp], ls.TEAMS[opp][0])) != source or source not in finished:
                raise ValueError(f'candidate requires completed exact {opp} snapshot {source}')
        return {opp: required[opp] for opp in candidate.get('opponents', required)}
    if candidate.get('kind') == 'queue' and candidate.get('label') == 'v87-null-a':
        _, _, finished, _, refs = ls.state()
        for opp, refset in NULL_A_REFS.items():
            source = refs.get((refset, ls.TEAMS[opp][0]))
            if source not in finished or (opp == 'mite' and source != NULL_A_MITE_SOURCE):
                raise ValueError(f'null-a requires the existing completed {opp} {refset} source; no repin or fallback')
        return dict(NULL_A_REFS)
    return dict(refsets())


def plan_gate(version, rsets):
    for part, prio in (('core', 99), ('ext', 90)):
        for opp in rsets:
            rc, out = sh([sys.executable, 'tools/ladder_scrims.py', 'plan', '--version', str(version), '--sets', part,
                          '--opps', opp, '--refset', rsets[opp], '--priority', str(prio)], cwd=R)
            log(f'plan v{version} {part} {opp} {rsets[opp]}: rc {rc} {out.strip()[-120:]}')
            if rc:
                raise RuntimeError(f'failed planning v{version} {part} {opp}')


def gate(v):
    tasks, created, finished, dropped, _ = ls.state()
    names = {'fish': 'Intercontinental Fish', 'mite': 'Mite'}
    # A version's gate is its set tasks on its planned ref set per opponent (r2 before any repin).
    planned = {}
    for t in tasks:
        if t['version'] == v and t['purpose'] == 'set' and t.get('refset'):
            planned.setdefault(t['opp_name'], set()).add(t['refset'])
    want = {n: (rs - {'r1'} if len(rs) > 1 else rs) for n, rs in planned.items()}
    mine = [t for t in tasks if t['version'] == v and t['purpose'] == 'set' and t.get('refset') in want.get(t['opp_name'], ())
            and t.get('refset') != 'r1']
    done = [t for t in mine if t['id'] in created and created[t['id']]['group'] in finished]
    infl = [t for t in mine if t['id'] in created and created[t['id']]['group'] not in finished]
    pend = [t for t in mine if t['id'] not in created and t['id'] not in dropped]
    any_inflight = sum(1 for e in created.values() if e['group'] not in finished)
    return dict(planned=len(mine), done=len(done), inflight=len(infl), pending=pend, any_inflight=any_inflight,
                core_done=sum(t['part'] == 'core' for t in done))


def drop(tasks, why):
    for t in tasks:
        ls.append_jsonl(ls.DATA / 'events.jsonl', {'ev': 'dropped', 'task': t['id'], 'at': now(), 'why': why})


# ---------------------------------------------------------------- candidates

def ocean_candidate(st):
    _, out = sh(['git', 'log', '-40', '--format=%H %s', '--', 'bots/ocean'], cwd=R)
    for line in out.splitlines():
        sha, subj = line.split(' ', 1)
        m = re.search(r'\boc-base(\d+)\b', subj)
        if not m:
            continue
        nn = int(m.group(1))
        if nn <= st['ocean_nn'] or f'oc-base{nn}' in st['failed']:
            return None
        src = R / 'bots/variants' / f'oc-base{nn}'
        if not src.is_dir():
            log(f'ocean commit {sha[:8]} names oc-base{nn} but the variant dir is missing')
            return None
        tmp = H / 'tmp-archive'
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir()
        subprocess.run(f'git archive {sha} bots/ocean | tar -x -C {tmp}', shell=True, cwd=R, check=True)
        rc, d = sh(['diff', '-rq', '-x', '.cambc', '-x', 'compile_commands.json', str(tmp / 'bots/ocean'), str(src)])
        shutil.rmtree(tmp, ignore_errors=True)
        if rc != 0:
            log(f'oc-base{nn} differs from bots/ocean at {sha[:8]}: {d[:300]}')
            return None
        return dict(kind='ocean', label=f'oc-base{nn}', nn=nn, dir=str(src), commit=sha[:8],
                    note=f'ocean oc-base{nn}: {subj.removeprefix("ocean: ")[:52]} ({sha[:8]})'[:80])
    return None


def queue_lines():
    if not Q.exists():
        return []
    done = QDONE.read_text().splitlines() if QDONE.exists() else []
    out = []
    for i, raw in enumerate(Q.read_text().splitlines()):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if any(d.startswith(line + ' | live') or d.startswith(line + ' | skipped') for d in done):
            continue
        f = [x.strip() for x in line.split('|')]
        # Agents edit queue lines after submission: a dir that already went live is done whatever its line says now.
        if len(f) > 1 and any(' | live v' in d and [x.strip() for x in d.split('|')][1:2] == [f[1]] for d in done):
            continue
        try:
            prio = float(f[0])
        except (ValueError, IndexError):
            continue
        out.append((prio, i, line, f))
    return out


def queue_candidate(st):
    lines = queue_lines()
    if not lines:
        return None
    prio, _, line, f = max(lines, key=lambda x: (x[0], -x[1]))
    d = f[1]
    cands = [Path(d), R / d, R / 'bots' / d, R / 'bots/variants' / d]
    src = next((p for p in cands if p.is_absolute() and p.is_dir()), None)
    if src is None or not (src / 'src').is_dir():
        log(f'queue line skipped (no bot dir): {line}')
        with QDONE.open('a') as fh:
            fh.write(f'{line} | skipped (no bot dir) {now()}\n')
        return queue_candidate(st)
    base = f[2] if len(f) > 2 else '?'
    return dict(kind='queue', label=src.name, dir=str(src), base=base, line=line, prio=prio,
                note=f'arm {src.name} on {base} (live queue p{prio:g})'[:80])


def pick(st):
    return ocean_candidate(st) or queue_candidate(st)


# ---------------------------------------------------------------- build

MASK = R / 'tools/livemask'
# 2026-11-09 ~08:50: per-round stream mask (stream_patch.py, prioxor bb91acd9a) from v87-reup on; v93-v97 used mask_patch.py.
MASK_PATCH, MASK_HEADER = 'stream_patch.py', 'prio_stream.h'
MASK_FILES = (MASK_HEADER, MASK_PATCH)
UNMASKED = {R / 'bots/variants/oc-base23'}   # the v86 control, already prepared: submitted uncoded


def unmasked(c):
    return Path(c['dir']).resolve() in UNMASKED


def mask_rev():
    import hashlib
    return hashlib.sha256(b''.join((MASK / f).read_bytes() for f in (MASK_FILES))).hexdigest()[:12]


def build(c):
    W = H / 'build' / f"{c['label']}-{int(time.time())}"
    W.mkdir(parents=True)
    steps = [['cambc', 'init', '--yes', '.']]
    for s in steps:
        rc, out = sh(s, cwd=W)
        if rc:
            return None, f'init failed: {out[-300:]}'
    for p in (W / 'bots').glob('starter-*'):
        shutil.rmtree(p)
    (W / 'bots/ocean').mkdir(parents=True)
    rc, out = sh(['rsync', '-a', '--exclude', '.cambc', '--exclude', 'compile_commands.json', c['dir'] + '/',
                  str(W / 'bots/ocean') + '/'])
    rc2, d = sh(['diff', '-rq', '-x', '.cambc', '-x', 'compile_commands.json', c['dir'], str(W / 'bots/ocean')])
    if rc or rc2:
        return None, f'copy differs: {d[:300]}'
    if list(W.rglob('cambc_local.h')):
        return None, 'cambc_local.h present in the scratch workspace'
    params = W / 'bots/ocean/src/params.h'
    txt = params.read_text()
    if not re.search(r'constexpr bool test_draft = false;', txt):
        # Queue arms should already be off; a live submission must play its own draft.
        txt = re.sub(r'constexpr bool test_draft = true;', 'constexpr bool test_draft = false;', txt)
        if 'constexpr bool test_draft = false;' not in txt:
            return None, 'cannot find test_draft in params.h'
        params.write_text(txt)
        c['note_td'] = 'test_draft turned off in the build copy'
    # Code our priorities per game (prio_mask/; the key stays in ~/.config/cambc-secret). Only the v86 control goes
    # up uncoded, to check that live replays repeat. No patch, no build: never submit uncoded by accident.
    c['masked'] = not unmasked(c)
    if c['masked']:
        c['mask_rev'] = mask_rev()
        rc, out = sh([sys.executable, str(MASK / MASK_PATCH), str(W / 'bots/ocean')])
        if rc:
            return None, f'priority mask patch failed: {out.strip()[-200:]}'
    rc, out = sh(['cambc', 'build', '--release', 'ocean'], cwd=W)
    if rc:
        return None, f'build failed: {out[-400:]}'
    rc, out = sh(['cambc', 'run', '--release', 'ocean', 'ocean', '--map', '03twisty', '-o', 'rep'], cwd=W)
    rows = re.findall(r'^\s+[AB]\s+ocean\s+[\d.]+\s+\d+\s+\d+\s+[\d.]+\s+(\d+)', out, re.M)
    if rc or len(rows) != 2 or any(int(x) for x in rows) or 'finished:' not in out:
        return None, f'smoke game failed: {out[-400:]}'
    c['workspace'] = str(W)
    c['smoke'] = [l for l in out.splitlines() if l.startswith('finished:')][0]
    return c, None


def prepare(st):
    c = pick(st)
    if c is None:
        return None
    p = st.get('prepared')
    if (p and p['label'] == c['label'] and p['dir'] == c['dir'] and p.get('line') == c.get('line')
            and p.get('masked') == (not unmasked(c)) and (unmasked(c) or p.get('mask_rev') == mask_rev())):
        return p
    log(f"building candidate {c['label']} ({c['kind']})")
    b, err = build(c)
    if err:
        log(f"candidate {c['label']} failed: {err}")
        st['failed'].append(c['label'])
        if c['kind'] == 'queue':
            with QDONE.open('a') as fh:
                fh.write(f"{c['line']} | skipped ({err[:60]}) {now()}\n")
        save(st)
        return None
    st['prepared'] = b
    save(st)
    log(f"prepared {b['label']}: {b['smoke']}")
    return b


# ---------------------------------------------------------------- submit

def hold(why):
    # After an upload, a retry could submit twice: stop submitting and wake the reporting agent instead.
    log(f'HOLD: {why}')
    (H / 'HOLD').write_text(why + '\n')
    (HAND / 'parked').mkdir(exist_ok=True)
    wake({'hold': why, 'at': now()})
    return False


def submit(st, c, base_live, plan=True):
    if not unmasked(c) and not (Path(c['workspace']) / 'bots/ocean/src/model' / MASK_HEADER).is_file():
        log(f"{c['label']}: workspace has no priority mask; rebuilding before any submit")
        st['prepared'] = None
        save(st)
        return False
    rsets = gate_refsets(c)  # Validate the historical override before any upload or activation.
    c['note'] = c['note'].strip()  # the platform strips notes
    rc, out = sh(['cambc', 'submit', 'ocean', '-n', c['note']], cwd=c['workspace'], timeout=600)
    log(f'submit rc {rc}: {out.strip()[-200:]}')
    if rc:
        return False
    deadline = time.time() + 3600
    v = None
    while time.time() < deadline:
        time.sleep(30)
        try:
            live, _, rows = submissions()
        except ls.CambcError as e:
            log(f'submissions list: {e}')
            continue
        try:
            mine = [x for x in submissions_json()['submissions'] if x['version'] > base_live
                    and x.get('note', '').strip() == c['note'].strip() and x['version'] not in st.get('outside', [])]
        except (ls.CambcError, ValueError, KeyError) as e:
            log(f'submissions list --json: {e}')
            continue
        if not mine:
            continue
        v = max(x['version'] for x in mine)
        status = rows.get(v, mine[0].get('status', '?'))
        if status.lower() in ('queued', 'building', 'pending', 'compiling', 'processing', 'uploading', 'uploaded'):
            continue
        if 'fail' in status.lower() or 'error' in status.lower():
            log(f'v{v} build failed on the platform: {status}')
            st['failed'].append(c['label'])
            st['prepared'] = None
            save(st)
            return hold(f'v{v} ({c["label"]}) failed to build on the platform: {status}')
        break
    if v is None:
        return hold('submission uploaded but never appeared ready in an hour')
    for _ in range(10):
        rc, out = sh(['cambc', 'submissions', 'activate', str(v)])
        live, sel, _ = submissions()
        log(f'activate v{v} rc {rc}: live v{live} selected v{sel} {out.strip()[-120:]}')
        if live == v:
            break
        time.sleep(60)
    if live != v:
        return hold(f'v{v} uploaded but not live after 10 activations')
    if plan:   # batch mode plans its own gate, a batch at a time
        plan_gate(v, rsets)
    base_version = BASELINE
    if c['kind'] == 'queue':
        base_version = base_of(st, c['base'])
        with QDONE.open('a') as fh:
            fh.write(f"{c['line']} | live v{v} {now()}\n")
    else:
        st['ocean_nn'] = c['nn']
    st['history'].append(dict(version=v, label=c['label'], kind=c['kind'], dir=c['dir'], commit=c.get('commit'),
                              base=c.get('base'), base_version=base_version, note=c['note'], live_at=now(),
                              smoke=c['smoke'], workspace=c['workspace'], note_td=c.get('note_td'), masked=c.get('masked'),
                              mask_rev=c.get('mask_rev'), testing_refsets=rsets))
    st['prepared'] = None
    save(st)
    return True


# ---------------------------------------------------------------- main loop

def base_of(st, base):
    """Queue line's base field -> the live version it pairs against: an explicit '(= vNN)' / '(vNN)', else the
    newest history entry whose label is the oc-baseNN named there."""
    m = re.search(r'\(=?\s*v(\d+)\)', base)
    if m:
        return int(m.group(1))
    m = re.search(r'\boc-base\d+\b', base)
    lab = m.group(0) if m else base.split(';')[0].removeprefix('base ').strip()
    return next((h['version'] for h in reversed(st['history']) if h['label'] == lab), BASELINE)


CONTROL_OF = {'oc-base23': 86}   # control resubmissions: cut after core when core repeats the original exactly
FIELDS = ('result', 'rounds', 'our_gems', 'opp_gems', 'our_kills', 'opp_kills', 'our_gold', 'opp_gold')


def control_repeats(v, orig):
    key = lambda r: (r['opp_id'], r['map'], r['side'], r['position'])
    a = {key(r): r for r in ls.games(orig) if r.get('refset') == 'r2' and r.get('part') == 'core'}
    b = {key(r): r for r in ls.games(v) if r.get('refset') == 'r2' and r.get('part') == 'core'}
    common = set(a) & set(b)
    diff = sum(any(a[k].get(f) != b[k].get(f) for f in FIELDS) for k in common)
    log(f'control v{v} vs v{orig} core: {len(common)} paired games, {diff} differ')
    return len(common) >= 150 and diff == 0


def runner_alive():
    try:
        pid = int((ls.DATA / 'run.lock').read_text().strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False



def main():
    from live_r6_campaign import Campaign
    from live_opponent_campaign import Panel
    from live_batches import Batches
    log(f'scheduler start pid {os.getpid()}')
    version_check = VersionCheck(ls, H, log, wake)
    opponent_detector = OpponentDetector(ls, save, log, wake, now)
    campaign = Campaign(sys.modules[__name__], opponent_detector)
    panel = Panel(sys.modules[__name__], opponent_detector)
    batches = Batches(sys.modules[__name__], opponent_detector)
    while not (H / 'STOP').exists():
        try:
            st = load()
            if not runner_alive():
                log('runner dead: restarting')
                sh([str(R / 'tools/live_restart_runner.sh')])
            if VERSION_CHECK and version_check.tick(st):
                time.sleep(15)
                continue
            if campaign.tick(st):
                time.sleep(30)
                continue
            if panel.tick(st):
                time.sleep(30)
                continue
            if BATCH_MODE:
                batches.tick(st)
                time.sleep(30)
                continue
            if not outside_check(st):   # live is not ours: neither report nor submit
                time.sleep(120)
                continue
            live, _, _ = submissions()
            detector_pending = opponent_detector.tick(st, live, refsets())
            g = gate(live)
            c = prepare(st)
            reached = g['planned'] > 0 and not g['pending'] and g['inflight'] == 0
            ent = next((h for h in st['history'] if h['version'] == live), {})
            ctl = CONTROL_OF.get(ent.get('label')) if ent.get('kind') == 'queue' else None
            if not reached and ctl and g['core_done'] >= CORE_GROUPS and g['pending'] and control_repeats(live, ctl):
                log(f"cutting control v{live}'s gate at {g['done']} groups: core repeats v{ctl} exactly")
                drop(g['pending'], f"scheduler: control v{live} repeats v{ctl} on core")
                g = gate(live)
                reached = not g['pending'] and g['inflight'] == 0
            # queue arms (v87-line) always get the full 104-group gate; only ocean versions are cut for a newer ocean
            if (not reached and live != BASELINE and ent.get('kind') == 'ocean' and c and c['kind'] == 'ocean'
                    and g['core_done'] >= CORE_GROUPS):
                log(f"cutting v{live}'s gate at {g['done']} groups: {c['label']} is waiting")
                drop(g['pending'], f"scheduler: gate cut for {c['label']}")
                g = gate(live)
                reached = not g['pending'] and g['inflight'] == 0
            if reached and live not in st['reported']:
                rec = dict(version=live, groups=g['done'], at=now(),
                           entry=next((h for h in st['history'] if h['version'] == live), None))
                ls.append_jsonl(H / 'gates.jsonl', rec)
                (HAND / 'parked').mkdir(exist_ok=True)
                wake(rec)
                st['reported'].append(live)
                save(st)
                log(f'gate v{live} done: {g["done"]} groups')
            if reached and c and g['any_inflight'] == 0 and not (H / 'HOLD').exists() and (H / 'PAUSE').exists():
                if st.get('pause_logged') != live:
                    log(f"gate v{live} reached, {c['label']} waiting: PAUSE present ({(H / 'PAUSE').read_text().strip()})")
                    st['pause_logged'] = live
                    save(st)
            elif reached and c and g['any_inflight'] == 0 and not detector_pending and not (H / 'HOLD').exists():
                log(f"submitting {c['label']} after v{live}")
                if not submit(st, c, live):
                    log('submit did not complete; retrying next loop')
        except Exception as e:  # keep running: every step is re-checked next loop
            log(f'error: {type(e).__name__}: {e}')
        time.sleep(120)
    log('STOP: exiting')


if __name__ == '__main__':
    main()
