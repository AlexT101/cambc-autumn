# Brief A: the Prism hub (gems valued by who will end up holding them)

You are an implementation agent for PHOEBE, who owns a macro refactor of our Cambridge Battlecode bot `charybdis`
(C++, compiled to WASM). Work only in the worktree `/home/ubuntu/wt/mx-phoebe` (branch `mx-phoebe-20261113`); never
touch `/home/ubuntu/cambc-autumn` (read-only reference) or any other worktree, never push, never commit (PHOEBE commits).

## Read first
- `/home/ubuntu/wt/mx-phoebe/AGENTS.md`, `cambc-rules.yaml` (engine-verified rules: capture, camps, Prism), `docs/api/cpp.md`
  as needed.
- The bot: `bots/variants/chy-ref/src` (= charybdis 529). `bot.cc` is the turn (`decide`); `economy/farm.cc`
  (`farm_turn`: the farm choice, ~2,000 lines), `economy/capture.cc` (`prism_premium`, `holder_value`,
  `leave_for_prism`, `prism_eta`, `prism_takeover`, `left_for_prism`, `carry_reach`), `economy/crew.cc`,
  `model/comms.h` (claims, bags, told positions), `bot_parts.h` (declarations).
- History of this line: `research/hyperion/CHANGES.md` entries 507, 510, 512 and 527 (the Prism carry 'G'/'L'/'Q',
  the Prism gem premium priced consistently by every ally), and `research/mac13-castor/NOTES.md` (C7: the gain came
  from *consistency*, the allies valuing the Prism's gems as the Prism does; its feeder part alone was ~+1.8).

## Why
A Prism gains 1.5 Focus per carried gem; its spells scale with Focus, so Prism duels go to the larger bag, and the
team whose Prism dies first loses ~87%. `prism_premium(a, gems)` prices a kept Prism gem at 1 + premium gems
(median ~3 early, ~1 at r300). Mirror data (1,360 games): the Prism holds 61% of captured gems by r150 and ~55% by
r300; allies still capture ~27 gems (r1-150) and ~31 (r151-300) per team-game on groups within 12 tiles of the Prism
at payout, and many more further away. Allies price the premium only on groups a Prism ally *claims*
(`keep_bonus` in `farm_turn`: `fed_claim`), and leave cleared groups to the Prism only under `leave_for_prism`'s
narrow tests. So an ally choosing between two groups ignores that the gems of one near the Prism will (or could) end
in the Prism's bag, while the Prism's own farm counts it. That is the same inconsistency C7 fixed for claimed groups.

## The design: one valuation of a group's gems by their expected holder
1. **Collectable groups.** For a non-Prism ally choosing group g in `farm_turn`, g's gems carry the premium of a
   keeping Prism ally P (`prism_premium(world, P, G.gems)`) when P can collect g's capture: P can stand on g's tiles
   before the payout of a hold we would begin when our clear ends. Concretely: P's ETA to g (`prism_eta`-style:
   its free walk from its seen or told tile, or its current task first; crow-distance bound before any field) is at
   most our rounds to finish g (our walk + clear, as the loop already prices it) + `capture_rounds` - 1. Then either
   we begin the count and P takes it over ('G', `prism_takeover`), or we leave it to P ('L'). A group P claims keeps
   today's rule. Use the same `keeps_bag`/premium gates as today (none past the win, none for a Monolith, P healthy,
   no enemy in sight of the group where `leave_for_prism` refuses for that reason). Make sure the prune bounds
   (`keep_most`, `bound_tribute`) still bound every group's value, or the loop's prunes become wrong.
2. **Holds that P will take over are begun, not left empty**, where the rules make that strictly better: a hold begun
   now pays at R+6 and P joining any time before the payout takes the whole share if we step off (capture.reward: the
   allies on the tiles *at payout* split). Leaving the tiles empty instead delays the payout and the group's respawn
   (camps.respawn: the timer starts at payout). Check what `leave_for_prism` / `yield_capture` / `take_capture_handoff`
   do today and change only what contradicts this (e.g. leaving a group empty for a Prism whose ETA is inside the
   hold window). Allies must step off before the payout once P stands on a tile (existing `yield_capture` logic).
3. **The Prism's side stays consistent**: its 'G'/'L'/'Q' picks already value collecting; check they still agree with
   (1) (the Prism must actually come for groups allies priced as collectable: if P's farm would not pick it, the ally's
   premium is a promise nobody keeps). Prefer reusing P's existing pick logic to decide what P will collect.

Keep it general (every map, every team with a Prism): no map- or matchup-specific cases, no new magic constants —
derive bounds from the rules (capture time, walking) and existing measured quantities. Leave draft (`draft/`) and
emblem choices alone. Fuel: 2x fuel is used in testing, so correctness first, but add the cheap bounds (crow steps
before fields, one ETA per group per turn as `prism_eta` caches) so the farm loop does not blow up; the loop runs
every turn for every body.

## How to work
1. `./copybot variants/chy-ref variants/phb-hub` (from the worktree root; never copy `.cambc/`), edit only
   `bots/variants/phb-hub/src`.
2. Build check: `cd /home/ubuntu/wt/mx-phoebe && source ~/venv/bin/activate && cambc build bots/variants/phb-hub`
   (or let ab.py build it).
3. Iterate with A/Bs on the `train` suite only (fresh maps reserved for your loops):
   `bash research/mx-phoebe/ab.sh hubN phb-hub maps/suites/mx-phoebe/train` (10,200 games, ~5-15 min; run it in
   tmux: `tmux new -d -s mx-phoebe-hubN 'bash research/mx-phoebe/ab.sh hubN phb-hub maps/suites/mx-phoebe/train'`,
   and wait on `replays/ab/mx-phoebe-hubN/summary.json` with a background until-loop; never a foreground sleep).
   Results in `replays/ab/mx-phoebe-hubN/summary.md`. At most 3 such A/Bs. A debug study, if you need traces:
   add `--debug` and use `maps/suites/mx-phoebe/study` (2,720 games). Noise is about +-1 point at 10k games.
   `python3 research/mx-phoebe/scripts/prismdist.py EXTRACT_DIR` (after `node tools/replay/extract.mjs BATCH --out DIR`)
   measures where non-Prism captures happen relative to the Prism; use it to check the mechanism moved gems.
4. Before returning: spawn a **read-only** auditor subagent (tell it explicitly not to edit any file) to check your
   diff against this design and the rules for bugs (wrong ETAs, prune bounds, promises the Prism does not keep, ally
   pairs both stepping off, fuel blow-ups); fix what it finds; make sure the bot builds; play the smoke
   `source ~/venv/bin/activate && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/phb-hub variants/chy-ref --no-test-draft --fuel 200000 --name mx-phoebe-hub-smoke`
   (256 ladder games): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK`.
5. Kill every tmux session you started (`tmux ls | grep mx-phoebe-hub`). Delete replay batches of your A/Bs once read
   (`replays/batch-*mx-phoebe-hub*`) except the last one.

## Stop condition and report
Stop when the design is implemented, audited, smoke-clean, and you have at most 3 train A/B reads (or earlier if a
read shows a clear bug you cannot fix). Report: what you changed (files, functions, as a design), each train read
(win %, CI, OOF CAND/REF), what the mechanism measurably moved (Prism share of captured gems, ally captures near the
Prism), anything the auditor found, and open doubts. Leave the final version in `bots/variants/phb-hub` and write
its diff to `research/mx-phoebe/patches/phb-hub.diff` (`diff -ruN bots/variants/chy-ref/src bots/variants/phb-hub/src`).
