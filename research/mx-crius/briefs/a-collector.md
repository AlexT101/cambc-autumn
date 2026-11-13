# Brief A: the Prism as the team's collector (implementation subagent)

You implement one macro change to our Cambridge Battlecode bot charybdis, in C++, and measure it. Work only in
`/home/ubuntu/wt/mx-crius` (a git worktree on branch `mx-crius-20261113`). Do not commit, push or touch any other
worktree or `/home/ubuntu/cambc-autumn`. Do not edit `bots/variants/chy-ref` (the frozen reference) or `bots/charybdis`.

## Read first
- `AGENTS.md` (repo rules: fuel, debug_block tracing, testing), `cambc-rules.yaml` (engine-verified rules; capture,
  camps, tribute sections especially), `docs/api/cpp.md` as needed.
- Source: `bots/variants/chy-ref/src`. `bot.cc` `decide()` is the turn; `economy/capture.cc` (holder_value,
  value_holder, outvalues_holders, prism_premium, leave-for-Prism / worth_wait, handoffs, yield_capture,
  take_capture_handoff), `economy/farm.cc` (farm_turn: the group choice, claims, crew pricing, pick_up),
  `economy/crew.cc`, `model/comms.{h,cc}` (8 shared bytes: claims, bags, ally positions), `bot_parts.h`.
- `research/hyperion/CHANGES.md` entry 527 (CASTOR's Prism gem premium), `research/mac13-castor/NOTES.md`.

## Why
- A Prism gem is worth ~2 gems through r300 (Focus +1.5 a gem compounds into farm and the Prism duel, which decides
  86-90% of games). CASTOR's 527 made every "who gets this group's gems" choice price that premium and won +3
  points, all through the Prism's share of team gems (0.51 -> 0.57 at equal totals). A 10-point higher Prism share at
  equal totals wins 58-61% (logistic over mirror games).
- Mirror games now (chy-ref vs itself, 1,700 games): the Prism takes 54% of captured gems. Allies make 21.5 captures a
  team-game without the Prism (396 gems). In 5.9 of them (111 gems) the Prism was within 8 tiles of the group 6
  rounds before payout, 9.0 (165 gems) within 12. The Prism stands ~4 rounds on each sole capture it makes.
- The capture rules make a relay possible: a hold's timer runs while any ally stands on any camp tile, so an ally can
  clear and hold a group, the Prism step on before the payout, and the ally step off; at payout only those on the
  tiles split the gems. The Prism needs to be on a tile only for the end of the hold, and nobody else on it then.
  Careful: the tiles must never be empty in between (progress resets), and payout is at the capture phase of round
  R+6, before any champion turn, so the hand-over must be complete by the end of round R+5 under the real turn
  order (an ally acting before the Prism in that round cannot step off unless the Prism already stands on a tile).

## Design (the macro, not a bolt-on)
Make the Prism the team's gem collector and its allies the crew that clears and pre-holds for it, through one
consistent valuation, with no summons, no fixed roles, and no one waiting idle for anyone:
1. **Collect jobs in the Prism's farm choice.** Besides its own groups, the Prism prices collecting an ally's capture:
   a group an ally holds (capture_state readable while any of its tiles is in sight; else the ally's posted claim and
   what we know of it) or is about to clear. Value = the gems' premium the team gains (gems x premium: the gems come to
   the team either way), time = the Prism's walk to a free tile before the payout, and the job is feasible only if it
   can be on a tile before the hand-over deadline. Priced on the same basis as its own jobs (`rate`), so it collects
   only when that beats farming. While it waits on the tile it may still hit what is in reach.
2. **The hand-over.** An ally holding a group the Prism has claimed (its posted claim) keeps holding until the Prism
   stands on a tile, then steps off and goes on to its next job; if the Prism cannot make the deadline (it turned
   away, died, was delayed), the ally keeps the hold and takes the payout. Check what the existing handoff /
   leave-for-Prism / yield code already does and extend it rather than adding a second mechanism.
3. **Allies farm where the collector can reach.** In an ally's group choice, a group whose payout the Prism can reach
   in time (its ETA from its posted/seen position, or its claim's end) carries the premium on its gems, scaled by how
   likely the Prism is to come (a derived quantity, e.g. whether the Prism's own best alternative beats collecting).
   This pulls allies to work near the Prism, which also covers it in fights, without anyone walking to anyone.
4. Whatever information the Prism and allies need (the Prism's position and target, an ally's hold timer) should come
   from what already exists (claims, posted positions, capture_state) or a compact extension of the 8 shared bytes
   (`model/comms.cc` layout; check it still fits on 5-6 body teams). Every ally must derive the same answer from the
   same shared information, so they agree.
Leave alone: `draft/` (draft and its choices), which emblems champions build (`economy/shop.cc` emblem choice), and
fuel optimisation (we test at 2x fuel; a guard against runaway loops is fine). Keep every quantity derived from the
rules or measured; no magic numbers or map-specific cases.

## How to work
- `./copybot variants/chy-ref variants/a-collect` (never copy `.cambc/`) and work in `bots/variants/a-collect`.
  `unity.cpp` includes every `.cc`: a new one goes there. Build: `cambc build bots/variants/a-collect` (or let ab.py).
- Measure with A/Bs against the reference, from the worktree root:
  `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-crius && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/a-collect variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx/train --name mx-crius-a-<tag>`
  (10,200 games, ~3-8 min; results in `replays/ab/mx-crius-a-<tag>/summary.md`). Run long commands in the
  background (`run_in_background`), never a foreground sleep loop. Use only the `train` suite (and `study` for
  `--debug` traces: `debug_block({ printf(...); })`, output in the replays' `team-?.stdout`); never `dev`, `hold`, `x1`,
  `x2` or `fin`. Delete replay batches you no longer need (`replays/batch-*-mx-crius-a-*`).
- Check it does what it should: count collects, hand-overs and resets (debug traces on `study`), and the Prism share
  of team captured gems: `py research/mx-crius/scripts/collector.py EXTRACT_DIR` after
  `node tools/replay/extract.mjs BATCH_DIR --out EXTRACT_DIR` (reference: 0.544 in the mirror).
- Iterate at most ~4 full train A/Bs on the design (fix bugs and missing companion pieces; do not sweep constants).
- Before returning: spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) to check the
  change against this design and the rules for bugs (turn order at the hand-over, reset risks, split payouts,
  consistency between allies, comms layout fit); fix what it finds; make sure the bot builds; play a smoke
  `py tools/ab.py variants/a-collect variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games: no failed
  games, no DRAFT-UNFINISHED / PLAN-CHECK).
- Stop when: the design is built, audited and smoked, and you have its best train A/B; or after ~4 train A/Bs; or if
  it is clearly broken beyond repair (then say why).

## Report back (concisely)
The variant path; what you built (design, files touched); each train A/B (win %, CI, OOF both sides) and what changed
between them; mechanism counts (collects a game, hand-overs, resets, Prism share before/after); the auditor's
findings and fixes; the smoke result; what you would try next. Save the final diff:
`diff -ruN bots/variants/chy-ref/src bots/variants/a-collect/src > research/mx-crius/patches/a-collect.diff`.
