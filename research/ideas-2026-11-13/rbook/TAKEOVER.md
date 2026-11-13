## 2026-11-13 17:21 UTC: live queue first; consolidated 529

User correction: live tests have first priority; fill available scrim quota in five-game groups, without switching to REST between artificial 50-game chunks. Consolidated the twelve still-unplanned 529 chunks into the active first-Mite campaign using the existing task_ids support (no scheduler code change). All 680 requested cells remain unique, 340 per opponent, Fish r8 / Mite r13 unchanged. First Fish50 already complete; current campaign contains remaining126 groups. Appended116 groups interleaved Fish/Mite; preserved the ten already-planned Mite groups and their created events. Marked merged after-steps consumed to prevent duplicates. Scheduler206728, runner3211816. Backup and reproducible validated consolidation script in /home/ubuntu/tmp-offload/live-chy529/. Runner filled quota100/100 at17:22:44:84/136 groups (420/680 games) submitted,52groups remain. Server next reset17:31:17.851. REST130 confirmed17:26:33; collection resumed. Progress snapshot /home/ubuntu/tmp-offload/live-chy529/progress.json compares only baseline128. Only return to latest book REST130 when quota exhausted or test fully submitted; do not insert book checks ahead of this live campaign.

v130 current-opponent checks completed Fish10/10 and Mite20/20; pinned checks Fish4/5, Mite7/12. Five distinct forced Fish entries failed live or caused collateral Mite losses, already sent to Hilbert for removal from increment2, alongside the local space-station conflict. v130 stays latest REST per user; no claim of full live qualification. Worker continues local inc2 build independently. At17:24 inc2 exact171/171 (97Fish74Mite), all13latewins retained; fallback/fuel gates still runningPID71402. Firstbook full47check provenance audit saved loss-v128/live-complete-audit.json;41wins6losses, qualification failed as expected. Fish teammate notified and normal-fuel candidate requested after529; its user wants fuel optimization first, so do not independently upload ia-prism.

## 2026-11-13 17:01 UTC: user policy — REST is latest uploaded book

Explicit user: "rest version should be latest book". This supersedes waiting for live qualification before ranked use. SetREST130, adoptedby scheduler17:00:23; platformselected130, activationpending17:00:59. Continue47livecheckswhilelatestbookrests. Recordactualqualificationresults honestly; do notmarkchecks passed merelybecausebookisREST. Onlaterlocallyverifiedbookuploads, moveRESTtolatestbookwhilecheckscontinue. Useracceptspartialcoverage. Firstbook164isv130 (alllocalchecks passed), separate receipt loss-v128/rest-user-request.json; loss-live-state retainsqualificationphase.

v129first50Fishcomplete24wins vs29forunmaskedv128 onsame50cells. Schedulerdefaultcontrol118prints27baselinewins; reportrealstrengthagainst128explicitly, not118. Full680 remainsqueued. BookchecksinsertedbetweenfirstFish50andfirstMite50. Firstbookdriver uploadcompleted; nosecondsubmit. Scheduler4027905, runner3211816.

OneworkerHilbert resumed(01a1d5a9-f826-7e32-9a88-be2271ac138c) preparing/building increment2 with13latecurrentRESTsourcewins; NEWwork loss-v128-r13-increment2, NEWbot samename. Parentretainsscheduler/APIownership. Workereditingloss_refresh.py/test_refresh.py fordistinct--bot-name; don'tstageuntilworkerready. Inc2 started16:56:20, preservingfirstwork/sourcehash. No129sources/newforeignunrankedextras inthisincrement. UserRESTlatestpolicysenttoworker.

## 2026-11-13 16:41 UTC: combined partial book passes exact replay

After excluding the3conflicting forcedFish entries,164/164combinedbookentries reproduceexactly.103Fish+61Mite,29forcedkeys; bundle3296250bytes. Builder3528047 continuingfallback/fuel/forcechecks; do not upload untilready_for_live_checks. Fullr13v126sourcepass finished136hostlosscells:74wins62losses.13winningcells arrived afterfrozenfirstselection; saved loss-v128/late-source-wins.json fornextincrement.

All3additionalunranked foreignMite candidates reproducedlocally:04gem_cavernsa(TrzyKwaterki),03one_gemb(ClaudusMaximus),01islandsa(Fish). State/entries in /home/ubuntu/tmp-offload/rbook-foreign/mite-r13-current/unranked-qualification-state.json, failed[]. Targetpinstillunproven; neverinsertintofrozenfirstbuild.

Hour32checks(created16:32) complete:Fishunchanged16:36:11,Miteunchanged16:38:17 onfivecells;Catschanged(notbookfocus).No repinrequired.529v129full680queued/verified,firstFish50campaignphase restwaitingquota16:48:50. Helpercompleted; sharedpreparedworkspace free for book uploadoncechecksready. Driverguardsnowallowcurrentphase rest, matchinghelper'ssafeinter-batchboundary;14tests pass(commit4bad249ff).

## 2026-11-13 16:33 UTC: v129 full strength test + first book conflict repair

User explicitly requested Charybdis529 real strength test on ALL170laddermaps, BOTHsides, Fish ANDMite (680games). Frozen bots/variants/chy-529-live frombbc7cddb6, test_draftfalse, no book files or priority mask. Uploaded asv129 (601159bytes), smoke passed round1459. Helper completed and REST126restored. Exactly14 interleaved cells steps chy529-full-{fish,mite}-{1..7} queued,50cells each(last40); exact340unique/opponent,170eachsideverified againstv128. No200cap. Full replaycollection; neither outcome-only nor wins-only applies. Intended strength comparator is unmasked book-freev128, not schedulerdefault118. Work/intent/steps:/home/ubuntu/tmp-offload/live-chy529. Shared prepared.json belongs to529 until upload helper processfullyexits; no duplicateupload.

Scheduler3476047, runner3211816. r13source28thgroupcreated16:31:17; campaignallcreated16:33:02. Hour32opponentchecks3groupscreated16:32:44. Quota exhausted until16:48:50;529then runs. Capture remains indefinitelypaused. Local API limiter remainsremovedperuser; server429retryhandlingonly.

Bookfirst combinedverification164/167exact; failures were3naturalMite lines blocked by forcedFish drafts on02the_packa,04sunbursta,05nestb. Preserve current-pin naturalMite wins by excluding their3conflicting forcedFish entries (twoforeignprovisionals,onev125) for firstpartialrelease. Reasons and exact keys in loss-v128/excluded-keys.json; priorfailure evidence archived attempt1-conflicts/. Builder supports explicit audited exclusions; frozen selection/caches preserved. Restarted resume servicePID3528047; prospective164entries(103Fish61Mite), combinedverificationreruns. No publicationyet.

Delegated Hilbert completed loss_live.py + test_loss_live.py (13offline tests), parentreviewed/committeddec123b70; workerclosed toavoidusage. Driver prepare/upload/reconcile/validate/promote/confirm, nohardcoded410; preserves full provenance, accepts winsafterdivergence, requiresforcedcollateralwins. Runonly afterlocalready and529helperfinished, atidlecampaignboundary. Bookhelper insertschecks before remaining529steps, allowingfull529runafterwards. Do not rerun upload after interrupted attempt; reconcile.

## 2026-11-13 16:18 UTC: first partial book building

Frozen first selection:168 candidates (106 Fish,62 Mite),32 forced draft keys. Full clean v128 baseline remains340cells per opponent. The70% source threshold was met16:16; build failed before compilation because systemd PATH lacked cambc. Reconciled clone/selection unchanged, added explicit --resume preserving pins/host/selection, corrected unit PATH to include /home/ubuntu/venv/bin. Builder PID3268605 running after restart16:17.17offline book tests pass, including resume identity/selection preservation.

User explicitly requested removing our local API limiter. Commit02e0929a7 removes tokenbucket/callgap/collector reserve/priority waits, retains server retry-after handling.13runner/JITtests pass. Runner3211816 and scheduler3211839 active; canonical data/run.log restored. Winning-source task filter remains. Source26/28 groups collected16:17, group27created16:17:13; group28 waitsquota16:26:53.

Foreign recent unranked search capped at600rows/6pages:26foreign wins,8confirmed host-loss cells,7pass prospective Fish draft compatibility. Saved /home/ubuntu/tmp-offload/rbook-foreign/mite-r13-current/unranked-loss-candidates.json for a later increment; no delay to first build, no claims of opponentversion identity for unranked games.

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

## Increment 2 release ownership and reserved quota (2026-11-13, after 17:31 UTC)

The delegated book worker owns the 171-entry increment release end to end; parent owns the
book-free v129/Charybdis 529 full 680-game campaign. Do not alter its cur/task_ids/pins/priority.
Increment work: /home/ubuntu/tmp-offload/rbook/loss-v128-r13-increment2; variant of the same name.
Local gates and read-only release preflight passed; all 13 late Mite wins are exact, and the
shared 02guardians b Mite source also reproduces exactly. Coverage ledger records nine Fish
exclusions and the deliberate 01elk_arena a Fish REST126 tradeoff. All 69 first-book hashes
remain protected. Latest uploaded book becomes REST immediately while live checks continue.

User reserved 50 of the 100 rolling scrim groups for teammate bursts. Restart confirmed:
runner PID458161 with --reserve50; scheduler PID458183; live_batches.RESERVE=50. Ordinary
529/book tasks are priority99 and cannot consume the reserve; only explicitly urgent
priority>=100 tasks may bypass it. Already-used quota100 must drain before ordinary work
can resume. The book helper waits for a resting campaign and used>=limit-RESERVE, checks
again after the coordinated scheduler stop, and queues book checks after the active529
campaign. Never upload while that campaign has usable quota. Helper boundary tests cover
reserve0/50/100, below/at threshold and active activation/creation phases without API calls.

### Superseding correction: no fixed idle reserve

User corrected the reserve interpretation: use ALL quota unless the teammate actually
requests a burst, then coordinate priority/yield. Restart confirmed with reserve0:
runner PID494561, scheduler PID494583, live_batches.RESERVE=0. Fish currently requests
NO burst and will ask after its 530 fuel pass. The helper reads limit-RESERVE dynamically;
it therefore requires full quota exhaustion before interrupting an active campaign now.
The earlier fixed50 policy and PID458161/458183 note above are superseded.

### v131 release, 2026-11-13 17:47 UTC

Increment2 uploaded exactly once as v131 and became live/REST at17:47:04, before live
qualification as instructed. Helper stopped/restarted the scheduler only at a full-quota
resting boundary; new scheduler PID746536, runner494561 unchanged. Release service
rbook-increment2-release completed successfully; state waiting_for_live_checks. Its39
requested check cells are queued after the active129campaign, whose126task_ids and pins
were preserved exactly. Six uncreated v130hourly opponent checks were retired under the
live lock; detector snapshots remain unchanged. 529 now waits only for quota (48groups
remaining at17:47). All69protected first-book hashes remain unchanged. The worker owns
following checks through validation/fixes; no repeat upload should be launched.

### Scheduler lifetime correction after v131 upload

The release service exited17:48:11 and its cgroup cleaned up scheduler746536 despite
nohup/setsid. Parent recovered it outside the worker unit; current lock PID803582.
The worker did NOT launch a competing restart. Future live_test.sh restarts use their
own systemd user service (unique unit, --collect), with explicit working directory,
PATH and append logs; startup failure propagates. Mocked launch/failure cases plus
quota-boundary tests pass (18 release-driver tests). Current529campaign remains parent-owned.

### Parent runner pacing restart, after 17:56 UTC

Current runner PID924258, scheduler PID924283, reserve0. Parent fixed the 120s unchanged-task
backoff during a fresh BATCH: runner now polls at normal --pace20 while live. Parent reports
5runner and10JIT tests pass;490/680 requested529games submitted. REST remains131; book
worker made no restart. Local finish_release.py watches the39 inc2 check cells and validates
provenance/results only after529creation completes; it cannot upload or mutate the queue.

### Follow-through after 529 and inc2 checks

User additionally requires fresh Fish/Mite current-opponent detection on131 at the first
spare quota AFTER current529 and inc2 checks, without blocking529slots or changing its
fixed Fishr8/Miter13 pins. Droppedhour33 left the last clean rolling observation at16:36.
The worker prepared opponent-detection-plan.json in inc2 work: the existing five core
map/sides, same-version target-pin/current comparisons. It has NOT queued those extra
observations yet. Reuse equivalent completed131 evidence where available; otherwise queue
only the needed detection groups after priority work. If a real behavior change is proved,
continue loss-only repin/book updates, not speculative bot experiments.

Parent's subsequent scheduler-only restart: PID1185343; runner924258 unchanged, reserve0.
Its <=180s imminent-refill grace keeps529 active for near-term quota rather than switching
through REST;12JIT tests pass. Book worker did not restart or alter this campaign.

### 2026-11-13 18:50 UTC: increment2 release qualification complete

v131 remains REST under the explicit latest-book policy, but is NOT fully qualified:
31/39 requested wins, all11 groups collected. Pinned Fish r8 2/2 and Mite r13 7/7;
current Fish2/10 and Mite20/20. All39 requested replay ZIPs pass CRC; strict group,
map/side, own-version and source-pin provenance passed;69 first-work hashes unchanged.
Durable evidence: increment2-live-results.json; full runtime audits in
/home/ubuntu/tmp-offload/rbook/loss-v128-r13-increment2. The release watcher exited on
Required win failed for current Fish00elkring/a; no duplicate upload or REST rollback.

Fish's change is not a host-version comparison artifact: pinned and current
00interlock/b both use v131, the same seed and engine/hash. Pinned r8 wins and exactly
replays its recording; current Fish loses after first divergence at round index2.
All10 current Fish samples diverge early (indices0–13):8 losses,2 handover wins.
Hour34 detector comparisons also differ on all5 cells for both Fish and Mite using
v131 on both sides of each comparison. HOWEVER all20 current Mite book wins are
byte-identical to their r13 recordings. A change versus Mite's older rolling snapshot
is not enough to call the r13 book stale; a direct r13/core check is queued first.
No worker-created detection groups were needed for hour34; existing hourly checks resumed.

### Deferred refresh behind Charybdis531

Parent owns v132 Charybdis531 full680 on fixed Fishr8/Miter13 versus529, scheduler
PID1871727 and runner924258, reserve0. The worker has not changed this campaign.
Appended ahead=false steps before hold-control: loss-book-mite-r13-snapshot-check
(one same-v131 pinned group, compare to saved hour34 current after checking original
row positions and aligning by map/side); loss-book-fish-r9-host-v128 (340 distinct
cells/69 groups, existing unmasked host); loss-book-fish-r9-rest-v131 (latest book on
confirmed matching host losses only). They start after531 and yield to queued candidates.
Fishr9 is captured by the first future baseline group, not fabricated from observations.

Work /home/ubuntu/tmp-offload/rbook/loss-v128-fish-r9 contains refresh-plan.json and
advance_refresh.py. Independent copies of181 raw/ent caches plus fp.json; no shared
mutable directories/JSON, no foreign candidates from old Fish pins. One bounded
rbook-fish-r9-cycle.service waits on the scheduler, conditionally refreshes Mite only
if the direct r13 check differs, builds at70% source collection after complete matching
host baselines, then uses loss_live's single-upload/REST helper and full live checks.
It preserves all13 late natural Mite wins when retaining r13, checks the prior artifacts,
and stops on failed gates, ownership changes or duplicate/restart ambiguity. It never
clears control markers or activates/uploads directly. No agents or big-arm capture.
Current phase and failures: cycle-state.json; output: cycle.log. Restart requires explicit
state reconciliation; do not blindly rerun it. Existing parked/live-gate.ready receives
only a final published/held event. The parent has not been handed the routine book work.

loss_refresh.py now accepts --source-versions, default unchanged117,118,119,125,126;
next cycle adds131. Selection freezes this list and rejects resume drift.22 refresh
tests pass; four offline comparator checks preserve reordered-cell identity and reject
seed/own-version mismatches. The old frozen selections remain valid with defaults.

## 2026-11-13 20:05 UTC: latest531 host, partial Fish r9 + Mite r13

This supersedes the old v128/Fishr9 cycle. User requires latest book-free host132
(Charybdis531, c451e3387), with Fish priority and useful partial coverage before the
00:00UTC14Nov submission deadline. Final tournament maps are unseen; the book is
for seeding. This clarification does **not** authorize stripping/activating a separate
final bot. The exact book-free531 artifact remains preserved.

- Parent owns queue/API activation: runner2787885, scheduler2788186, REST131,
  reserve0 (all quota available; teammate priority as slots return). Original500
  v132 games are fully collected/CRC audited; unfinished old ablation90Mite cells
  remain parked, without duplicates. No old128/r9 game was created.
- Fishr9 captured as `01a1d67e-e307-7f33-9412-90716c3b4ad9`. New work
  `/home/ubuntu/tmp-offload/rbook/loss-v132-fish-r9`. Worker cycle
  `rbook-host132-partial-cycle-final.service`, PID3046811, waits on matching baseline and
  sources. Prior cycles2708154,2932446 and2983787 stopped at prebuild checkpoints and archived.
- Both opponents may be partial, with explicit minimum60% known cells **each**;
  70% of planned source groups suffices. Only confirmed132 losses are candidates.
  Unknown collateral cells are deferred. FullFish340 and missingMite90 do not gate
  first release. Cycle refreshes `first-source-fish-known-losses.json` and
  `first-source-fish-actionable-losses.json` every30s; parent owns source scheduling.
  Source step remains `loss-book-fish-r9-rest-v131`, lost_by132.
- Outcome-only132 enabled only after original500 archive audit passed. Existing
  archives untouched. Future pinned132 host rows retain outcomes/drafts/provenance;
  source131 full winning recordings remain full. Recording versions117,118,119,125,
  126,131 only. No old foreignr8 entries or old exclusions copied into r9.
- `loss_host.py` prepared variants/rbook-host531-base and -template from all61
  source files identical to actual132 upload and bots/charybdis at c451e3387.
  Only the template receives replay integration plus stale-round handover guard;
  no extra fuel patches. Main bot untouched. Profile freezes source hashes and is
  checked on build/resume. Raw/ent181 caches copied; fingerprint/bad caches fresh.
- Reference-only benchmarks completed52wide100M and300fresh normalfuel, native
  runner/jobs8. These are **not yet populated-book comparison results**. Populated
  build still requires exact recordings, fallback24, wide identity except forced
  cells, fresh comparison, forcecheck, bundle limit and live collateral/source
  checks. New upload name identifies531; generation IDs are unique.
- Book lookup on no-match returns to normal531 play; it has startup filtering and
  comms guards, not zero overhead. Old131 evidence:186/300fresh realfuel replays
  identical, +0.08% fuel on identical games; do not extrapolate to531. New populated
  book measurements pending. Generated fresh-map corpus can reproduce ladder
  terrain/layout (old131 matched6/25,600); filename novelty alone is not a no-match proof.
- First partial releases as soon as gates finish; helper remains coordinated at
  quota-exhausted REST boundary. Optional23:00UTC upload cutoff preserves an hour
  for essential qualification; no automatic final activation scheduled. Latest
  uploaded book becomes REST while checks run. Repeated/ambiguous uploads require
  reconciliation. Stop via this work's STOP marker; do not blindly restart a cycle.

Validation:53 offline book tests passed; shell syntax clean. Full populated-book
validation is pending source collection, not claimed complete. Big-arm stays paused.

## 2026-11-13 20:12 UTC: immediate531 starter, provisional Fish handover lines

User now prioritizes replacing525-basedREST131 quickly, so the first531 book does
not wait for the new Fish source campaign. Existing-sources-only mode still applies
known-host-loss and collateral guards. Current frozen selection51:20 proven Miter13
sources plus31 oldFishr8 winning recordings, all on confirmed132/r9losses with known
Mite collateral. Eleven Fish entries force a draft change. The31Fish lines explicitly
retain r8 refset/source-group provenance, are **unverified against r9**, and require
r9 target live checks plus all forced/shared-draft collateral checks. No oldr8 source
is relabeled as an r9-proved win; divergence followed by a531 win qualifies.

Current work `/home/ubuntu/tmp-offload/rbook/loss-v132-starter-expanded`, bot
`variants/rbook-loss-v132-starter-expanded`, cycle3107636 in
`rbook-host132-expanded-v2-cycle.service`; building at20:11:39. The20-entry Mite-only
local build was superseded before any upload, and a partially prepared intermediate
work was stopped before upload and preserved. Only this current cycle runs. Parent
owns queue and will change `loss-book-fish-r9-rest-v131`'s version to the new531 book
once uploaded, retaining lost_by132; thereafter user wants only531book/531book-free
toggles. Do not independently run the old131source campaign.

54offline tests pass. Small books now require every available distinct fallback
case above450rounds, up to24; zero cases/zerohandovers/invalidreads still fail. Full
populated exact replay,352benchmarks,forced checks and coordinated upload remain
mandatory. Final unknown-map activation policy is unchanged.

20:17 clarification: the oldFish fallback strategy is **coordinator-proposed**, in
support of the user's531book goal, not a literal user request. Parent approved the
single51-entry starter. Its essential validation is37pinned cells (31Fishr9 target,
6Miter13 collateral), with explicit `validation-policy.json`; redundant current
samples are omitted for this work only. Full winning qualification replays supply
the next increment; no generic119-loss source sweep. Parent deferred old131source
and Mite probe behind hold-control. Latest upload becomes REST immediately.

All51 source lines recorded exactly on531, bad0; combined verification in progress.
A temporary work HOLD-PUBLISH allows the completed local artifacts to be reconciled
under the new pinned-only validator before upload; it does not stop local gates.
Worker will replan locally and use explicit `loss_cycle.py --resume-local` only
from held+ready with **no** release-state/upload attempt. Existing upload attempts
cannot be resumed this way. New-host release digests additionally freeze selection,
profile, foreign provenance and validation policy; oldv131digest remains unchanged.
56offline tests pass, including originalr8 provenance retained with r9target check,
small-partial fallback completeness, source-provenance digest drift and no retry
of any prior upload attempt.
