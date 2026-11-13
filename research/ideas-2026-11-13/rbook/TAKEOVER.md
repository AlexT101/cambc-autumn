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

## Active refresh

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

fish:0 is idle after the overnight runs; CASTOR c11 remains unmerged. Shared coordination note:
`/home/ubuntu/tmp-offload/handoff/CODEX-TAKEOVER-20261113.md`. No new fuel/no-lock experiment started.
New host candidate and control must both be book-free (including forced draft), on identical pins/cells.
Choose the baseline explicitly: scheduler currently defaults to historical v118. Book REST results never
enter the host comparison. Port the book after selecting the host.

Five offline refresh tests and five existing live-batch tests pass. Failure injection confirms no stage DONE
on builder failure and refusal of existing host-swap destinations. Python/shell syntax and whitespace checks
pass. Corrected reporting was checked on actual downloaded v126 replays.
