# Planner brief: what to merge into bots/charybdis

You are planning a merge. You don't write bot code and you don't run A/Bs. Your output is a plan document.

## Background

Six independent efforts each refactored the macro of our Cambridge Battlecode bot `bots/ocean` (C++) on their own branch. "Macro" here means farm and camp targeting, coordination, economy and banking, positioning, and fight-level decisions. Each effort's best bot then played 40,960 games at normal fuel against `bots/ocean` on main, and the highest scorer became the base of a new bot, `bots/charybdis`.

Your job is to decide which changes from the other five bots, and from the leftover untested variants, we will merge into charybdis, and how.

Read `/home/ubuntu/wt/charybdis/AGENTS.md` and `cambc-rules.yaml` first for the game and codebase conventions.

**Read-only:** every path outside `/home/ubuntu/wt/charybdis/research/charybdis/`. Don't edit any bot, branch or worktree, and don't commit.

## The bots

The working copies are in `/home/ubuntu/wt/charybdis/bots/variants/`:
- `ocean-main-b7c87cf` is ocean on main, the common ancestor of all six.
- `charybdis-base` is the base, identical to `bots/charybdis` and to `macro1-hold6`.

Win rates against ocean-main, 40,960 games each, normal fuel:

| Rank | Bot | Win % (95% CI) | Write-up |
|---|---|---|---|
| 1 | **macro1-hold6** (the BASE) | 56.8 (56.3-57.3) | `/home/ubuntu/wt/macro1/research/macro-2026-11-11/macro1.md` |
| 2 | macro5-hold-sole2 | 56.2 (55.7-56.7) | `/home/ubuntu/wt/macro5/research/macro-2026-11-11/macro5.md` |
| 3 | macro4-handfc | 55.9 (55.5-56.4) | `/home/ubuntu/wt/macro4/research/macro-2026-11-11/macro4.md` |
| 4 | macro6-carry3 | 55.3 (54.9-55.8) | `/home/ubuntu/wt/macro6/research/macro-2026-11-11/macro6.md` |
| 5 | macro3-eoq2 | 52.3 (51.8-52.8) | `/home/ubuntu/wt/macro3/research/macro-2026-11-11/macro3.md` |
| 6 | macro2-lstep | 50.7 (50.2-51.2) | `/home/ubuntu/wt/macro2/research/macro-2026-11-11/macro2.md` |

The orchestrators' own A/Bs ran at 2x fuel (`--fuel 200000`) against the same ocean. Each worktree `/home/ubuntu/wt/macroN` (branch `macroN-20261111`) also holds:
- a running log `research/macro-2026-11-11/macroN-log.md`, which has the per-step A/B results;
- intermediate variants under `bots/variants/macroN-*`, the steps that built up each bot;
- in some worktrees, `research/macro-2026-11-11/patches/`.

Use the intermediate steps to attribute win rate to the pieces of each bot.

**Leftover untested or level variants.** These are "consider" items at most, unless the diff shows something clearly worth more:
- `/home/ubuntu/wt/macro6/bots/variants/macro6-mono`: carry3 extended to the Monolith. Diff: `/home/ubuntu/wt/macro6-work/mono/mono.diff`. In 80 debug games it was near-identical to carry3, so it rarely fires.
- `/home/ubuntu/wt/macro5/bots/variants/macro5-hold-sole3`: hold-sole2 plus more dilution-leak fixes. Diff: `/tmp/claude-1000/-home-ubuntu-cambc-autumn/b6215605-83f5-4219-85ac-eb40528dec74/scratchpad/hold-sole/hold-sole3.diff`. A 512-game smoke gave 51.8% against sole2, which is noise-level.
- `/home/ubuntu/wt/macro3/bots/variants/macro3-eoq5`: eoq2 with a holding cost in place of `chain_bag_limit`. It scored 53.1% at 2x fuel on a set where eoq2 got 53.4, so it is level.

Note: macro1, macro4, macro5 and macro6 all arrived independently at the same lever. Gems carried by the Prism become Focus (+1.5 per gem), and Focus wins fights. So expect heavy overlap with the base.

## What to do

Go in descending order of win rate: macro5, then macro4, macro6, macro3 and macro2, then the leftovers.

1. **Read the diffs themselves.** For each bot, diff it against `ocean-main-b7c87cf` and against the base. Don't rely on summaries or write-ups. Verify from the code how each change behaves: when it fires, what it changes, and for which champions.
2. **Split each bot into its distinct changes.** A change is a logical unit, for example macro5's stun_lock Prism safety, or one of macro2's four fixes. For each one, identify:
   - what it does;
   - its evidence, meaning its isolated or incremental A/B where the logs have one, and whether that was at 2x fuel;
   - whether it overlaps something the base already does, or something an earlier-ranked bot's kept change does.
3. **Resolve overlaps.** Where two changes address the same thing (for example, several ways of putting capture gems on the Prism, or of keeping allies off its holds), decide one of three things: take one, take the other, or combine them. If you combine, give a concrete specification of how. Note the case where the base's mechanism already covers a change, so the change isn't needed.
4. **Classify every change:**
   - **KEEP:** merge it.
   - **CONSIDER:** hold it back until every KEEP is merged and tested. Reasons include potential drawbacks, possible unexpected interactions with kept changes, and overfit risk: magic numbers, a solution with no strategic or mechanical logic, or a workaround that is tacked on rather than integrated.
   - **DROP:** reasons include a lower win rate, overlap with an existing or better feature, or being unneeded given the changes we take.

   **No change is too small to keep.** Never drop a change just because it is small or low-impact.

   Mechanical bug fixes with no trade-off deserve special note, since they can be merged even at a level win rate.
5. **Order the KEEP queue for merging.**
   - Big changes are merged one at a time.
   - Small related changes can go in logical groups.
   - Order them so each merge is testable, independent changes first where sensible, and say which group each change belongs to.
   - Order the CONSIDER queue too.

## Output

Write the plan to `/home/ubuntu/wt/charybdis/research/charybdis/plan.md`. Its sections:
- **Summary.** The KEEP, CONSIDER and DROP lists.
- **Per-change entries:** an ID such as `M5-a`; the source bot and the exact files and functions or hunks; the behaviour, verified from the diff; the evidence; the overlap analysis; the classification and its rationale; and merge notes, meaning how to port it onto charybdis's code, including conflicts with the base's edits to the same functions.
- **The ordered KEEP merge queue,** with groups.
- **The ordered CONSIDER queue.**

Your final reply should summarise the plan and give its path.
