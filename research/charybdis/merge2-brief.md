# Merge agent, phase 2: the CONSIDER queue for bots/charybdis

You own phase 2 of building `bots/charybdis`, a C++ Cambridge Battlecode bot.

Phase 1, done by another agent, merged the KEEP queue. K1 (macro3's EOQ bank floor) and K2a (no lethal camp flight) were accepted; K2b and K3 were level and moved to CONSIDER (C8, C9). The phase-1 state is frozen as `bots/variants/charybdis-p1` (commit 3c9b6c294). Over 40,960 games it scores 58.37% against ocean-main and 51.65% against charybdis-base. Read `research/charybdis/merge-log.md` for phase 1's record.

Your job is to work through the CONSIDER queue (C1-C9 in plan.md). These changes reached CONSIDER because they are ambiguous, carry trade-offs or interaction risk, or might overfit. **Merge one only on a clear win-rate improvement.**

Read these first:
- `/home/ubuntu/wt/charybdis/AGENTS.md`
- `cambc-rules.yaml`
- `/home/ubuntu/wt/charybdis/research/charybdis/plan.md`, the final plan, already revised after an independent audit; the audit is `plan-audit.md` beside it
- `research/charybdis/results.md`

## Setup

- **Worktree:** `/home/ubuntu/wt/charybdis`, branch `charybdis-20261111`. Work only here.
  - Other worktrees (`/home/ubuntu/wt/macro1`..`macro6`, `/home/ubuntu/cambc-autumn`) are read-only sources. Read diffs from them; never edit, commit to, or build in them.
  - Don't push and don't touch main.
- **`bots/charybdis`** (tracked) is the working bot. It starts as charybdis-p1.
- **Frozen references** (gitignored; never edit them):
  - `bots/variants/ocean-main-b7c87cf`: ocean on main.
  - `bots/variants/charybdis-base`: charybdis before any merge.
  - `bots/variants/charybdis-p1`: charybdis after phase 1.
  - `bots/variants/chy-K3`: the K3 candidate, kept for C9.
  - The source bots: `bots/variants/macro{2..6}-*`.
- **Don't write to the user's Claude memory directory.**

## Per CONSIDER item

Follow the plan's CONSIDER queue in order (C1-C9), respecting its conditions: C6 only if a shared-payout trace justifies it; C7 only if C3 is kept; C8's pieces tested separately; C9 retested after C1 if C1 is kept. Where the plan offers alternatives (C3 as a swap for `gold_part`, one Focus premium for every Prism pick if C1 and C3 are both kept), follow its spec. Big changes go one at a time.

1. **Port** the change onto a candidate copy, `bots/variants/chy2-<ID>` (`./copybot charybdis variants/chy2-<ID>`). Each copy starts from the current accepted charybdis state.
   - Port it to fit the base's code rather than pasting blindly, following the plan's merge notes and spec.
   - Build it in release and debug.
   - Play a couple of quick local games to check it runs.
   - Count how often the change fires in a small debug batch against ocean-main. A change that rarely fires can't show a clear gain, so note it.
2. **Audit.** Spawn a read-only auditor subagent (Explore or Plan type). Give it:
   - the source bot's diff;
   - the base;
   - your candidate's diff against the current charybdis;
   - the plan entry.

   It checks that the merge was completed correctly: nothing dropped, nothing silently changed, the base's behaviour preserved, and no bugs introduced. It runs no tests. Fix what it finds.
3. **Test.** Run three A/Bs at the same time, all at **normal fuel** (no `--fuel` flag), `--no-test-draft`, each 40,960 games on the same fixed suites:
   - the candidate against `variants/ocean-main-b7c87cf`;
   - the candidate against `variants/charybdis-base`;
   - the candidate against `variants/charybdis-p1`.

   Run no other A/Bs and no gates, `fgate.py`, live tests or scrims.
4. **Decide.** Merge only on a clear improvement.
   - **First accepted phase-2 change:** its win rate against charybdis-p1 must have a 95% CI lower bound above 50% at 40,960 games. Its win rates against ocean-main and charybdis-base must not fall below p1's (58.37% and 51.65%; measure p1 against both on your suites as well, so comparisons use identical maps).
   - **Later changes:** each must beat the last accepted phase-2 state on the same suites, in three ways:
     - against charybdis-p1, by more than noise: a paired comparison on the same maps showing significance, or at least about 0.7 points at 40k;
     - against ocean-main: not lower;
     - against charybdis-base: not lower.
   - **Within noise:** you may extend to 81,920 games before deciding.
   - **If it improves clearly:** copy the candidate into `bots/charybdis` and commit, one commit per accepted change, giving the results.
   - **If it doesn't:** drop it, and record why.
     - **Fuel:** if a change gained at 2x fuel in its source A/B but is level or negative here, mark it "dropped at normal fuel: candidate for later fuel optimization".
     - **Overall:** if it won on its source branch but not here, note the likely reason (overlap with the base, interaction, fuel) and the next step you would suggest.
5. **Pipeline.** You may start porting the next step while an A/B runs, on top of the candidate under test. If that candidate is rejected, rebase the next step onto the accepted state before testing it.

## Testing mechanics

Prefix, run from `/home/ubuntu/wt/charybdis`:
```
source /home/ubuntu/venv/bin/activate && export PATH=$HOME/.cargo/bin:$PATH CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
py tools/ab.py variants/chy2-C1 variants/ocean-main-b7c87cf --no-test-draft --suites $SUITES --keep-replays 100 --name m2-C1-vs-ocean
```
- **Suites.** Use one fixed 40k-game suite set for every phase-2 A/B, so steps compare on identical maps: 80 ladder-v2 suites of 256 maps. Phase 1's suites (710001-710080) are used up; don't reuse them.
  - Make them with `node tools/mapgen/mapgen.mjs suite --mix ladder-v2 --seed 720001-720080 --out '/home/ubuntu/wt/charybdis-maps/s-{seed}'`. They don't exist yet.
  - Extensions, when you need more games: `720081-720160`.
  - Keep each mapgen call to at most 30k maps.
- **Running.**
  - Run A/Bs in tmux and tee them to a log. Wait with a `run_in_background` loop on `tmux has-session`, not foreground sleeps.
  - `ab.py` takes the machine-wide CPU slot pool on its own: leave `--threads` off.
  - A 40k-game A/B takes about 15 minutes on the shared box.
- **Disk.** Delete your old `replays/` dirs once their results are recorded.

## Records

- **Merge log:** `research/charybdis/merge-log.md`. For every step:
  - what was merged, in which files;
  - the audit's findings and fixes;
  - both A/B results, with games, win rate and 95% CI;
  - the decision and why.
- **Results:** add a row to `research/charybdis/results.md` for each step.
- Commit the docs with each step.

## Finishing

Phase 2 ends once every CONSIDER item has been processed. Freeze the final state as `bots/variants/charybdis-p2`.

Then write `research/charybdis/final.md`, the final list of every change from every source bot (including the planner's DROPs, from plan.md). For each change give:
- **Status:** merged (phase 1 or 2), or dropped.
- **Why:** with A/B numbers.
- **Flags:**
  - changes dropped "at normal fuel: candidate for later fuel optimization";
  - for every unexpected drop, meaning a change that raised win rate on its own branch but didn't help charybdis, the likely reason and suggested next steps.

Also give the final charybdis win rates against ocean-main, charybdis-base and charybdis-p1.

Your final reply must summarise all of this and give the final commit.
