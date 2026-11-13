## 2026-11-13 16:08 UTC: incremental first release

User explicitly accepts a partial book and wants incremental improvements, and now authorizes delegation. One worker (Hilbert, 01a1d5a9-f826-7e32-9a88-be2271ac138c) investigates slow source collection and opt-in winning-recording-only downloads; no descendants. Parent retains scheduler and book publication ownership.

Mite r13 baseline complete: 204/340 wins, 136 losses. Source v126 sweep has 28 groups, 26 created; remaining two await quota. Loss builder unit restarted with --minimum-source-fraction 0.7: a complete clean host baseline is still mandatory, but source downloads need not all finish. Selection is frozen in selection.json for both sizing and final build so subsequent collection cannot change drafts/entries mid-build. Foreign candidates fill only uncovered cells. 16 book regression tests pass.

NEETCoders 00crater side A (15:40, e3ce5d6fff3f) is a confirmed r13 host-loss cell and reproduced exactly locally with the fixed host. Added to loss-v128 foreign-extra/metadata, copied raw/ent and exact fp from same host. Target-pin live validation remains required. Together with six prior Fish extras, seven provisional foreign candidates; own winning sources take precedence.

Fish session reports no live-test candidate ready at16:00. Best preliminary phb-hub 51.3%/2720 debug games still needs larger held-out and normal-fuel evidence. Fish will coordinate rather than upload independently. Big-arm capture remains indefinitely paused.

# Codex takeover, 2026-11-13

Coordinator: Codex in prominence:0; teammate: fish:0. Claude in prominence:2 stopped on authentication at
10:47 UTC. User transferred ownership here, requested no new agents/research, then explicitly requested
immediate programmatic book refreshes to preserve ranked/seeding performance.

## Completed findings

oppwatch.py overwrote distinct Fish/Mite draft entries at the same map/side. Comparing all entries now gives
8/8 exact unpinned Fish wins (two checks of four cells, not eight independent cells), CURRENT == r8. Mite's
three covered cells retain their recorded drafts but differ in play: 00lanes b at round index 2 (loss),
03the_front a at index 3 (win), 03homonoliths b at index 272 (win). 03one_gem a has only a Fish entry.

All x2 sweep games played and won: Fish r8 26/26 forced/foreign + 182/182 ordinary, Mite r10 202/202.
These are book coverage results, not host strength. Ordinary Fish is downloaded and exact (old waiter counts
184 with duplicates/fillers, 182 requested cells). Downloads/comparisons for the other lists continue in
the existing runner/waiters. No new agent was launched.

rbuild.py now fails on bad exact verification or missing bundles; stage.sh propagates pipeline failures and
does not write DONE on failure; hostswap.sh refuses existing destinations. No main bot source changed.

## Current policy and queue (updated 15:44 UTC)

At 15:38 the 15:32 current-Mite check changed on all five cells (same picks; 3/5 wins versus 4/5 before).
The refreshed baseline now targets **Mite r13**, not r12. At 15:43, 41 uncreated r12 v128 tasks were dropped
with explicit reasons; all completed evidence is retained. `loss-book-r13-baseline` reuses v128 without an
upload, 69 groups on Mite only; `loss-book-r13-mite-rest` follows on host losses. Fish r8 work is preserved.
The r13 pin will be captured by its first group when quota frees. `r12-superseded.json` records the transition.
The existing loss-v128 waiter now runs --mite-pin r13 --after-step loss-book-r13-mite-rest. Its Fish cache
(100 exact fingerprints) and six provisional foreign candidates survive unchanged. No book publication yet.

This section supersedes the older active-refresh notes below. User requires entries only for confirmed
losses of the matching book-free host, separately by map, side, opponent and pin. Unknown cells and host
wins do not qualify. A book divergence followed by a host win is success; exact current replay is not
required. Masked v119 remains useful source data but differs in production fuel from the unmasked host.

- REST remains v126. Matching unmasked chy-525f uploaded as v128 and began its Fish r8 / Mite r12 sweep
  at 14:48 UTC. Mite r12 captured by group `01a1d561-a30d-7954-b85b-81ee8a4a348f`.
- After that sweep, `loss-book-r12-mite-rest` runs existing v126 only on v128's Mite r12 losses.
  No new upload. Winning games, including handover wins, provide current-pin source recordings.
- Fish's latest current check was created 14:32 UTC and found no change on five cells; this is not proof
  of no upload. Refresh Fish too if its behavior changes. The v128 sweep already includes Fish.
- `loss_refresh.py` waits for complete clean baseline/source coverage, builds from target-pin wins,
  applies `--host-losses-only`, and identifies forced drafts per recording. It runs the local stage and
  forced-draft check, then holds for target-pin live checks including forced-draft collateral cells.
  Work: `/home/ubuntu/tmp-offload/rbook/loss-v128`. It never uploads or changes pins.
  On success, loss_live_plan.py writes live-steps.json and live-expectations.json: provisional target-pin entry cells,
  forced/shared-draft collateral cells, and bounded current-opponent checks. Collateral host wins must remain
  wins; a current win after divergence counts. Same-pin source wins already verified exactly in the combined
  book are not replayed in another full live sweep. The plan does not upload or promote anything.
- The legacy r11 410-entry book passed the corrected local stage at 14:37 (4,834,462 bytes;
  410 exact, fallback invalid 0). HOLD-LIVE-CHECK prevents its superseded selection being uploaded.
- Foreign v127: requested r11 cells 3/3 exact wins; requested current cells 0/3 wins, all diverged.
  The old scheduler summary incorrectly reused pinned games; raw current game rows are correct.
  New task-scoped reports exclude fillers and cannot borrow another check's results.
- Runner PID1320730 writes canonical data/run.log again. Big-arm capture is paused indefinitely by user request at 14:56 UTC: service stopped/disabled,
  all resume timers canceled. Resume only on user instruction.
- v128 baseline collection uses outcomes and drafts only, explicitly marked in games.jsonl; no replay/summary
  downloads. Source versions and opponent checks retain full replay evidence. This avoids downloading host wins
  that cannot enter the book and does not weaken source replay verification.
- Fish v128 r8 baseline complete: 197/340 wins, 143 losses. Clean recorded wins from v117/118/119/125/126
  cover 100 of those losses before combined-book gates. v125 adds 00elkring b, 05nest b, 05space_station b
  beyond the initial source list. Source recording lookup must use exact match IDs, not per-cell deduplication.
- `ladder_scrims.games()` now excludes fillers before deduplication, so a filler cannot hide a requested cell.
  The earlier 335-cell Fish summary was a reporting artifact; corrected coverage is 340.
- 15:27 UTC: all 100 Fish loss-cell candidates have exact recorded fingerprints in loss-v128/fp.json
  (15 reused, 85 freshly recorded with four workers), bad.json empty. These are recording checks, not yet
  combined-book verification. Prime log/state: prime-fish.log / prime-fish-state.json. The build waiter resumed.
  Its service definition is now ~/.config/systemd/user/rbook-loss-v128.service (not enabled at boot).
- 15:35 UTC: six cached w4 foreign wins cover additional Fish host losses: 00interlock b, 01gold_rush a,
  02the_pack a, 03honeycomb b, 04sunburst a, 05nest a. foreign-extra.tsv / foreign-metadata.json in loss-v128
  feed them as provisional local-exact candidates (target pin r8, live validation pending). Their ent/raw files
  are copied; current-host fingerprints will be recorded anew. Fish candidate coverage is 106, not 106 live
  qualified wins. All six enter target-pin checks and cross-opponent collateral checks before any publication.
- Fish teammate was notified of live/book ownership and the host policy. Their six local macro jobs
  remain under their control. No agent was launched by this coordinator.

## Earlier active refresh (historical, superseded above)


14:21 update: the first build reproduced all 410 entries exactly (208 Fish + 202 Mite), bundle 4,834,404
bytes, but the fallback gate correctly held it for one invalid claim read in 03contours b. Diagnostic:
body 0 had world/cached priority round 167, but resumed in actual round 168 while preparing comms. It read
body 3's new plain-published bit with old priority 110; a fresh SDK read was 6029312. The new book-only
round guard after layout/shared-memory read prevents this mixed-round read. Patch: handover-stale-read.patch;
applied to the new variant only, and wired into future refresh copies and host swaps. Full stage rerunning.
The failed artifacts are preserved in refresh-r11/before-handover-fix; diagnostic.repl26a retains the trace.

The 100M bench is 48/52 identical versus plain chy-525f; all four differing cells are declared forced drafts,
as allowed by the original HANDOFF.md gate. The validator now checks that explicit exception, complete 52
coverage, and zero fallback invalid reads. Fresh fuel comparison: +0.07% on identical games, not a fuel gain.

Foreign v127: all three requested entries exactly reproduced against r11. Current-Mite group created at
14:20:39, pending collection. REST remains 126. The runner's new stdout is sched/runner.out (events/games
are still in the usual data files); restore run.log redirection at the next idle checkpoint.

Once the corrected local stage passes, a waiting continuation runs forcecheck, then refresh_live.py:
one upload, 20 current-Mite + 10 current-Fish cells; promote that same version through sched/REST only
on 30 exact wins with no suspect groups. Any divergence preserves v126 and writes live-check-error.json.
The live-check upload has not begun. No agent was launched. Big-arm oarena-capture.service is temporarily
stopped to free shared API/download budget; timer oarena-capture-resume-book-20261113 resumes it at 15:01 UTC.

13:49 UTC update: r11 was pinned after two stable checks; v119 won 224/340 book-free. All follow-up games
have played. v117 has all 24 groups collected; v118 has 17/24 collected. At 13:46 the clean union was 252
winning map/sides, before size selection. Nine v117 groups were marked suspect at the switch back to REST;
rbuild now excludes suspect groups before selecting recordings, and refresh_build records them in
excluded-groups.json rather than rejecting the entire clean sweep. Six offline regression checks pass.

Mite current checks changed again at 12:40 and 13:37. `HOLD-PUBLISH` in the refresh work directory allows
build/verification but holds publication for current-Mite validation. The refresh service was restarted with
the corrected selection at 13:48, build stage only, three-hour cap (16:48 UTC). No extra games or agents.
fish:0 is now active on charybdis 528 following committed 527; a coordination message was sent about live
ownership, book-free host tests, suspect groups and the publication hold. Preserve their source edits.
All old x2 sweep comparisons finished: forced Fish 26 exact; ordinary Fish 182 unique exact; Mite 202 unique
exact (waiter reports 204 including duplicates/fillers). Foreign Mite candidates still await live validation.

13:59 update: all replays collected; 259 clean Mite candidate cells are being recorded and checked. Foreign
02harvest a is now an own-sweep win, but 04yin_yang a and 05space_station b still have no clean r11 own win.
A bounded foreign validation upload is running (`mite-refresh-r11/live-upload.log`): one five-game group
against r11 and one against current Mite, including fillers. The qualification bot must not become REST.
Explicit scheduler cells steps now accept pin=none; source cells still come from refset r11, but the actual
task uses no source pin and records refset=null. Seven scheduler tests pass. The old live runner was cleanly
reloaded after all downloads completed to load the current create/activation coordination code.

Systemd user service: `rbook-refresh-r11.service`. Artifacts/state:
`/home/ubuntu/tmp-offload/rbook/refresh-r11/` (queue-state.json, build-state.json); journal via journalctl.
A STOP file there yields before new phases/publication. The one refresh has a six-hour service cap.

refresh_queue.py queued a five-cell current-Mite check using v126: created 11:06:29, played 11:06:46,
collected 11:08:08. Four cells differ from 10:37. Next check >=11:23:54; at most six checks 15 minutes apart
until successive observations agree. This establishes stability only on those cells, not an upload guarantee.

When stable and no candidate is queued/in flight, insert before hold-control: book-free v119 on r11 (340
cells), then book-free v118/v117 on v119 losses. Preserve old pins and held controls. v126 stays REST between
batches. Games must finish playing, but old replay downloads need not finish before the new sweep starts.

refresh_build.py waits for these specific sweeps (not the held full v118 control), copies x2 into a fresh
variant and reuses replay/extraction caches. Preserve all 208 Fish entries; replace Mite with r11 wins.
Exclude old forced Mite games and fresh Mite entries conflicting with forced Fish cells. Select by measured
lost-cell value per byte within the established blob budget; fewer than 170 new Mite entries holds for review.

Publish through existing new_rest.sh only after exact verification, all 24 fallback games with zero invalid
reads, forced-draft checks, existing bench/fresh-map checks, and bundle <=4.9 MB. REST must remain v126 with
no newly queued candidate. One persisted publication attempt; reconcile failures rather than retrying.
Shared-pool weight 0.25 yields capacity to teammate work. This is one bounded refresh, not a perpetual daemon;
opponent observations remain active, and another refresh needs a new refset/work directory.

## Teammate and host strength

User also requested other teams' Mite wins. `../rbook-foreign/mine_mite.py` found three cached ranked
recordings compatible with the Fish draft screen; all three reproduce exactly locally. 02harvest a is
uncovered by x2; 04yin_yang a and 05space_station b have old-pin entries. All force their drafts. Work:
`/home/ubuntu/tmp-offload/rbook-foreign/mite-refresh-r11/`. These remain provisional until target-pin live
validation and combined-book checks; refresh_build.py intentionally does not consume provisional.tsv.
The three-entry qualification variant must never replace ranked REST. See the foreign README for evidence.

fish:0 is idle after the overnight runs; CASTOR c11 remains unmerged. Shared coordination note:
`/home/ubuntu/tmp-offload/handoff/CODEX-TAKEOVER-20261113.md`. No new fuel/no-lock experiment started.
New host candidate and control must both be book-free (including forced draft), on identical pins/cells.
Choose the baseline explicitly: scheduler currently defaults to historical v118. Book REST results never
enter the host comparison. Port the book after selecting the host.

Five offline refresh tests and five existing live-batch tests pass. Failure injection confirms no stage DONE
on builder failure and refusal of existing host-swap destinations. Python/shell syntax and whitespace checks
pass. Corrected reporting was checked on actual downloaded v126 replays.
