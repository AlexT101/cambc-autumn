# Merge agent, phase 1: merge the KEEP queue into bots/charybdis

You own phase 1 of building `bots/charybdis`, a C++ Cambridge Battlecode bot. You merge the plan's KEEP changes one step at a time and test each step.

Read these first:
- `/home/ubuntu/wt/charybdis/AGENTS.md`
- `cambc-rules.yaml`
- `/home/ubuntu/wt/charybdis/research/charybdis/plan.md`, the final plan, already revised after an independent audit; the audit is `plan-audit.md` beside it
- `research/charybdis/results.md`

## Setup

- **Worktree:** `/home/ubuntu/wt/charybdis`, branch `charybdis-20261111`. Work only here.
  - Other worktrees (`/home/ubuntu/wt/macro1`..`macro6`, `/home/ubuntu/cambc-autumn`) are read-only sources. Read diffs from them; never edit, commit to, or build in them.
  - Don't push and don't touch main.
- **`bots/charybdis`** (tracked) is the working bot. It starts as macro1-hold6.
- **Frozen references** (gitignored; never edit them):
  - `bots/variants/ocean-main-b7c87cf`: ocean on main.
  - `bots/variants/charybdis-base`: charybdis before any merge.
  - The source bots: `bots/variants/macro{2..6}-*`.
- **Don't write to the user's Claude memory directory.**

## Per KEEP step

Follow the plan's KEEP queue in order. Big changes go one at a time; small ones in the plan's logical groups.

1. **Port** the change onto a candidate copy, `bots/variants/chy-<ID>` (`./copybot charybdis variants/chy-<ID>`). Each copy starts from the current accepted charybdis state.
   - Port it to fit the base's code rather than pasting blindly, following the plan's merge notes and spec.
   - Build it in release and debug.
   - Play a couple of quick local games to check it runs.
   - Where the plan asks for it (K3), count how often the change fires in a small debug batch against ocean-main.
2. **Audit.** Spawn a read-only auditor subagent (Explore or Plan type). Give it:
   - the source bot's diff;
   - the base;
   - your candidate's diff against the current charybdis;
   - the plan entry.

   It checks that the merge was completed correctly: nothing dropped, nothing silently changed, the base's behaviour preserved, and no bugs introduced. It runs no tests. Fix what it finds.
3. **Test.** Run two A/Bs at the same time, both at **normal fuel** (no `--fuel` flag), `--no-test-draft`:
   - the candidate against `variants/ocean-main-b7c87cf`;
   - the candidate against `variants/charybdis-base`.

   Run no other A/Bs and no gates, `fgate.py`, live tests or scrims.
4. **Decide.**
   - **A change increases WR** if, on the same suites:
     - its win rate against charybdis-base is above the last accepted state's win rate against charybdis-base (for the first step, above 50%);
     - and its win rate against ocean-main is not below the last accepted state's.

     The accepted states so far: charybdis-base itself is 56.8% against ocean-main on other suites. Measure it on your suites too (base against ocean-main) so later steps compare on identical maps.
   - **This brief's rule governs.** Where plan.md's gate wording differs (it says "CI above 50%"), use the rule above. Its test against charybdis-base and the last accepted state is what counts. Keep the plan's advice to run 40,960 games for small expected gains such as K2b.
   - **Mechanical bug fixes:** K2a (M2-d, the lethal camp flight) is the only piece that counts as one. It is accepted unless it is significantly negative.
   - **Within noise:** if the difference is inside about ±0.7 points, you may add another 20k fresh games before deciding. Games are cheap.
   - **If it increases WR:** copy the candidate into `bots/charybdis` and commit. One commit per accepted step, saying what was merged and the results.
   - **If it doesn't:**
     - It goes to the **end of the CONSIDER queue**. Record it in plan.md's queue and in the merge log.
     - **Exception:** a clear mechanical bug fix with no trade-off, as the plan marks them, is accepted at a level win rate.
     - **Fuel:** the source bots were measured at 2x fuel. If a change gained there but is level or negative at normal fuel, mark it "dropped at normal fuel: candidate for later fuel optimization".
5. **Pipeline.** You may start porting the next step while an A/B runs, on top of the candidate under test. If that candidate is rejected, rebase the next step onto the accepted state before testing it.

## Testing mechanics

Prefix, run from `/home/ubuntu/wt/charybdis`:
```
source /home/ubuntu/venv/bin/activate && export PATH=$HOME/.cargo/bin:$PATH CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
py tools/ab.py variants/chy-K1 variants/ocean-main-b7c87cf --no-test-draft --suites $SUITES --keep-replays 100 --name m1-K1-vs-ocean
```
- **Suites.** Use one fixed 20k-game suite set for every phase-1 A/B, so steps compare on identical maps: 40 ladder-v2 suites of 256 maps.
  - Make them with `node tools/mapgen/mapgen.mjs suite --mix ladder-v2 --seed 710001-710040 --out '/home/ubuntu/wt/charybdis-maps/s-{seed}'`. They don't exist yet.
  - Extensions, when you need more games: `710041-710080`.
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

Phase 1 ends once every KEEP item has been processed. Your final reply must give:
- the accepted state, its commit, and its win rates against ocean-main and charybdis-base;
- a table of every KEEP item: merged, or moved to CONSIDER (with why, including any "fuel-optimization candidate" notes);
- the updated CONSIDER queue, in order.

Freeze the final phase-1 state as `bots/variants/charybdis-p1`, so phase 2 can test against it.
