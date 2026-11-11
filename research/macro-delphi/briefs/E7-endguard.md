# E7 "endguard": escort the winning tribute on every map (bots/variants/endguard)

Read /home/ubuntu/wt/macro-o4/research/macro-delphi/briefs/common.md first and follow it (TMPDIR rule; all output
under /home/ubuntu/wt/macro-o4/replays/delphi-smoke/endguard/). Candidate dir: `bots/variants/endguard` (create:
`./copybot charybdis variants/endguard`). Reference: `bots/variants/charybdis-ref`.

## Why (512 charybdis mirror games)
- The first team whose score plus carried gems reaches 1000 wins 87%, but conversion takes a median of 58 rounds
  (mean 147). After reaching it, a team makes 4.2 tributes of 150+ gems on average: about three of them are
  cancelled before one completes. Rules: a stun cancels a tribute (the gems stay carried), and placing an altar lock
  cancels every tribute at that altar. The enemy throws its bodies at a game-ending bag (its 'E' branch).
- Once a carrier holds a winning bag, more farming adds almost nothing: the next gems do not change the result.
  Protecting the channel decides the game.
- economy/altar_guard.cc already does this, but only on maps whose altars form a single site (`guarded_altar` returns
  -1 otherwise). There, while a body of ours carries a winning bag (`escorting`), the strongest `params::altar_guards`
  bodies (keeping `altar_farmers_min` farming) hold stand tiles by the altar and fight enemies within
  `altar_leash` (`guard_turn`).

## Design
Extend the escort to every map, reusing altar_guard.cc. Do not write a parallel mechanism.
1. While `escorting(world)` holds on a multi-site map, the guarded altar is the **carrier's altar**:
   - The carrier is the ally (or us) whose bag wins: the largest bag, as seen or posted, ties by index, so every
     teammate picks the same one.
   - If the carrier is visible and channelling a tribute (`Channel::tribute`), its altar is the altar within
     `submit_gems_range` of it.
   - Otherwise it is the altar the carrier will bank at. If the bank code exposes the carrier's chosen altar for
     ourselves, use it when we are the carrier. For other carriers, use the altar nearest the carrier's seen or
     posted tile (`recent_tile` in capture.cc) by Chebyshev distance, then by walking distance from our spawn.
   - Recompute each turn: it may move as the carrier walks.
   - Keep the single-site behaviour (and the `guarding()` enemy-lead trigger) unchanged on single-site maps.
2. `stands()` is cached by altar index already; make sure it rebuilds when the altar changes. Do the same for
   `guard_turn`'s per-stand fields (they are indexed by stand number only: key them by altar too).
3. `keep_guard_lock` should apply to the carrier's altar while escorting, so our lock stays up there.
4. The carrier itself is not a guard: it banks as now. Guards are chosen with `guard_rank` among the others.
5. Debug traces: escort turns per game, guards on station when the winning tribute starts and completes, and
   tributes cancelled while escorted.

## Done when
It builds, and three local games against charybdis-ref finish without bot errors. At least two must be on maps with
several altars that reach an escort; most macro-dev maps have 2-10 altars. Traces show guards at the carrier's
altar. Report as common.md asks.
