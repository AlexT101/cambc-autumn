# E8 "window": bank the Prism's hoard while the enemy Prism is dead (bots/variants/window)

Read /home/ubuntu/wt/macro-o4/research/macro-delphi/briefs/common.md first and follow it (TMPDIR rule; all output
under /home/ubuntu/wt/macro-o4/replays/delphi-smoke/window/). Candidate dir: `bots/variants/window` (create:
`./copybot charybdis variants/window`). Reference: `bots/variants/charybdis-ref`. Small change, ~30 minutes.

## Why (charybdis mirror)
- Our Prism keeps every gem (`keeps_gems` in economy/bank.cc: until `winning_bag` or `closing`), so the game ends on
  one long Prism tribute: median 647 gems, a 47-turn channel, and 4.5 attempts before one completes. A stun cancels
  a tribute, a lock at the altar cancels it, and 78% of Prism deaths are kills by the enemy Prism.
- Prism-on-Prism kills happen 1.24 times a game. The dead Prism stays out for ~60 rounds (rules: respawn D+60/61),
  with no gems, and the killer has just taken its bag. While the enemy Prism is dead, its Focus-scaled stun, the
  main threat to a long channel, is absent. The gem's Focus value (`carried_bonus`) also matters less then: there is
  no enemy Prism duel to win.

## Design
In `keeps_gems` / `retaining_gems` (bank.cc), a keeping Prism stops keeping (so its bag goes to an altar through the
existing bank path) when all of these hold:
1. Every enemy Prism is dead. World beliefs know enemy liveness always (rules: "only whether it is alive can be read").
   The rounds until the earliest one respawns can be read from its death round, if World tracks it. If not, track
   the round we first see it dead and assume a respawn 60 rounds later.
2. Our walk to an altar (the bank code's `to_any_altar` field, or the recall-and-walk as `closing_now` measures it)
   plus `tribute_turns(world, my_gems())` fits within the rounds left before that respawn.
3. The bag is worth a trip: at least the existing bank floor (`bank_floor` / `bankable_bag` logic). Do not invent a
   new threshold.

Keep it simple and in one place. When the enemy Prism respawns, or the condition fails before the tribute starts, it
keeps again: `continue_tribute` already decides about channels under way, so leave that alone.
- Debug traces (debug_block): window opened (bag, rounds to respawn, walk + channel), tribute started and completed
  in the window.

## Done when
It builds, three local games against charybdis-ref finish without bot errors, and traces show a window bank
happening in at least one. Report as common.md asks. Skip the auditor if the diff is under ~40 lines; otherwise run it.
