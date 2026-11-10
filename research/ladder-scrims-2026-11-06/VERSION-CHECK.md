# Hourly opponent version checks

User authorized 2026-11-10: temporarily activate the original platform v1, play
current Mite and Fish on fixed maps/sides, restore the live bot, log changes and
notify the user. Never repin an opponent or queue a repin.

`live_sched.py` calls `tools/ladder_version_check.py` before normal gate work.
`tools/ladder_coordination.py` supplies the lock also used by `ladder_scrims.py`.
The cycle persists in `version-check.json`; `version-check-active.json` in the
scrim data directory blocks new ordinary groups while existing groups drain.
The scheduler waits for every recorded in-flight group to finish, snapshots the
exact active/selected/pinned selection, activates v1 UUID
`cd7eedca-dfbf-4832-aab1-b75ca30e7704`, creates two groups without source-group,
waits for completion and restores that selection. Pending gate tasks stay intact.
Normal group creation resumes before evidence downloads. The next check is due
one hour after the previous check's last group was created; scheduler/API delays
can make it later. Missed hours are not caught up with extra groups.

The API requires five distinct maps per group. Frozen fixture (our sides):
04sunburst A, 03homonoliths B, 03the_front A, 00lanes B, 03one_gem A.
Both opponents use exactly this fixture, costing two groups per cycle. Existing
v1 is activated without a new upload, keeping its submitted source fixed. The
platform may queue/rebuild that historical submission before it becomes active.

Evidence: `version-check-evidence/CYCLE/` has raw group JSON, binary summaries and
decoded summaries. The comparison hashes game trajectories, roster, events,
heatmaps and final game state, excluding runtime diagnostics. Engine, map and
seed metadata are compared separately. The first observation is calibration;
subsequent changed evidence is a **possible opponent version/behaviour change**,
not definitive version metadata (the CLI does not expose the opponent version).
Engine/seed changes and nondeterminism remain possible causes. Identical probes
cannot detect a new version that behaves identically on these five games.

Events append to `version-check-events.jsonl` and `sched.log`. Changes, failed
games and blocked recovery also append to persistent `version-check.ready` and
wake the existing coordinator through `../parked/live-gate.ready`. The coordinator
should report these to the user, without changing pins. Do not discard the
persistent ready file until the user has been notified. No probe results enter
ordinary gate tasks/games/events or `refsets.json`.

Recovery: state is saved before every activation/create. Activations reconcile
on restart. A terminal v1 build failure restores the saved selection, records an
incomplete check and waits until the next hourly check; queued/building is not a
failure. A terminal failure of the saved bot during restoration alerts and blocks
for manual review. A create is attempted once with no HTTP retry; an ambiguous response
blocks further creation, alerts the coordinator and leaves the exclusion marker.
Reconcile the actual group ID from the platform before filling in `groups[opp]`
and clearing `attempting`; then set phase back to `probing`. Never blindly retry
an ambiguous create. An outside upload or selection change blocks the cycle and
is never overwritten. Inspect its selection before any manual recovery. The
`blocked_phase` and `error` fields explain where it stopped. HOLD/PAUSE prevent
starting a new cycle, but an already active cycle completes restoration.

Disable by setting `enabled: false`; an active cycle still restores safely.
Do not delete the marker during an active switch. Graceful service restarts use
the scheduler STOP file and `../restart-runner.sh`; start only one scheduler.

Validation: `python -m unittest discover -s tools/tests -p test_ladder_version_check.py -v`.
Backups of original scheduler/runner: `~/tmp-offload/version-check/backups/`.

## First live calibration, 2026-11-10

Cycle `1794299390939594326`: drain began 08:29:50 UTC; v1 selected at
08:31:07 and observed active at 08:36:27. Mite group
`01a1c49a-343a-7429-b549-d5a979c53cd6` was created at 08:36:42 and Fish group
`01a1c49a-70b6-7738-96b9-3e90e2c95ac0` at 08:36:58. All ten games finished.
v106 was restored active/selected/pinned at 08:39:15; ordinary v106 Mite ext14
was created at 08:39:27. Baselines completed 08:39:37, with no change alert.
All ten games ran 412–2000 rounds, with zero bot faults on either team.
Fish r2 and Mite r5 pins remained unchanged. Next check due 09:36:58 UTC.

The measured drain-to-restored pause was **9m25s**, including platform preparation
in both directions; v1 preparation alone took about 5m20s. This is separate from
the exact two-group quota cost. Later-switch overhead has not yet been measured.
The current CLI and local docs expose historical opponent selection only, with
no supported own-version override or background preparation command. The user's
hourly cadence remains enabled. Queue ops owns ongoing alert relay.

Deployment handles at calibration: scheduler 3614012, runner 3541984. The new
scheduler checks `VersionCheck(ls, H, log, wake).tick(st)` before `outside_check`;
a true return skips ordinary scheduler work and waits 15s. The ordinary runner
holds `live_lock(DATA)` across its final marker check, group creation and event
append. Both components must be loaded before enabling version-check.json.
Validation: 14 unit/recovery tests passed, including a real cross-process lock,
terminal/slow builds, outside submissions, ambiguous creation and crash recovery.
