# Fuel campaign 7: merge agent procedure

Read [BRIEF.md](BRIEF.md) first (paths, env, benches, rules). MAIN = `/home/ubuntu/cambc-autumn`. You verify one
batch of worker branches and merge what passes into `main`. Never push.

1. **Worktree.** `git -C MAIN worktree add MAIN/.claude/worktrees/fc7-merge<N> -b fc7-merge<N> main`; link maps as in
   the brief. Merge (or cherry-pick) each worker branch in; resolve conflicts by keeping both changes' intent.
2. **Review every diff yourself** (don't trust the reports): for each change, is it exact? Check claims that a case
   is impossible against `cambc-rules.yaml`; check that a cache's key covers everything the cached work reads, that
   it is invalidated when any input changes (including within a turn, after a move or a kill), and that an early
   exit gives the same result. Look for UB, uninitialised state, stale state across rounds or across a `StaleTurn`
   / out-of-fuel resume, and Cassi/Issac (two bodies) or dead-champion turns. Drop or fix anything doubtful; say why.
3. **Identity.** Freeze `./copybot astraeus variants/fc7-m<N>` in your worktree, `cambc build` it once, then
   `ALL=1 MAIN/replays/fuel/fc7/bench.sh m<N> variants/fc7-m<N>`. Every 100M set (def, wide, pool, big, heavy, td)
   must be byte-identical to `MAIN/replays/fuel/fc7/base-*-100M.json` (`bench.py compare`). If not, bisect to the
   commit that breaks it and drop or fix it. Record mean/p90/p99/max/over-100k/round-1 deltas per set, and the real
   budget sets' OOF and shortcuts (`stats.py`).
4. **A/B.** `MAIN/replays/fuel/fc7/ab.sh m<N> variants/fc7-m<N> variants/astraeus-5166d1c m` (10,240 games on
   `fc7-m`, run in the background, wait on it). Read win % and CI, OOF cand/ref (`.log`, `.oof`), fuel per turn
   (`.fuel`: mean/p50/p90/p99, share over 100k), shortcuts (`.shortcuts`). Fuel-only changes should be level on win
   rate (a CI wholly below 50 is a regression to investigate) with OOF down. A fuel gate (any code reading the fuel left to take a
   cheaper path) merges only with its worker's 20k confirmation CI wholly above 50% (BRIEF.md); drop one that is
   only level, whatever its OOF. Also compare with earlier merges'
   numbers in NOTES.md (all merges are measured against the same base on the same suite, so they are cumulative).
5. **Commit to main** (MAIN has other sessions' uncommitted work in other files: leave it alone).
   - `git -C MAIN status --short bots/astraeus research/hyperion/fuel-campaign-7` must be clean, and
     `git -C MAIN diff --cached --stat` empty, before you start.
   - Bring the commits in with `git -C MAIN cherry-pick <shas>` (or a squashed commit per worker idea) touching only
     `bots/astraeus/`, `research/hyperion/fuel-campaign-7/`, and if a probe ran, `cambc-rules.yaml`,
     `tools/probes/` (check those are clean in MAIN first).
   - CHANGES.md and EXPERIMENTS.md hold other sessions' uncommitted edits: commit **only your entry**, through the
     index: `git -C MAIN show HEAD:research/hyperion/CHANGES.md > /tmp/fc7/c.md`, insert your entry at the end
     (next free number: the highest `## N:` in both HEAD's and the working copy's file, plus one), then
     `git -C MAIN update-index --cacheinfo 100644,$(git -C MAIN hash-object -w /tmp/fc7/c.md),research/hyperion/CHANGES.md`;
     same for EXPERIMENTS.md (an entry `## Fuel campaign 7, merge <N> (2026-11-06, astraeus <sha>)` at the end of
     the file); commit; then insert the same text into MAIN's working-copy files, so `git -C MAIN diff` on them
     shows only the other sessions' edits again (check it).
   - Entry title format: `## 424: <what> (astraeus, 2026-11-06)` — fuel only, the 100M identity and the A/B numbers.
   - Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
6. **NOTES.md**: append `## merge <N>` to `research/hyperion/fuel-campaign-7/NOTES.md` (in the same commit): what was
   merged and dropped, the bench and A/B tables, and the workers' open leads in one list (deduplicated).
7. **Report**: main's new sha(s), what merged and what was dropped (why), identity results, the A/B (win %, CI, OOF
   cand/ref and % change, p90/p99/mean, shortcuts top 6 cand vs ref), and the open leads list.
