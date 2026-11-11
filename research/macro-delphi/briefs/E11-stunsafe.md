# E11 "stunsafe": a long winning tribute starts only when no enemy can cancel it soon (bots/variants/stunsafe)

Read research/macro-delphi/briefs/common.md (TMPDIR rule; output under replays/delphi-smoke/stunsafe/). Candidate dir
bots/variants/stunsafe (already a copy of bots/charybdis). HARD DEADLINE 22:30 UTC. Small change, no auditor.

Why: a game-ending Prism tribute is a median 47-turn channel and takes 4.5 attempts; up to 20 cancellations seen.
Rules: a stun cancels a tribute (gems stay carried); placing an altar lock cancels every tribute at that altar.
economy/bank.cc `tribute_safe` judges only whether we could be *killed* in the window (`turns_to_kill_idle`); a
cancel needs only a stun. So a channel starts beside an enemy whose stun is ready, and is cancelled at once.

Design: in `tribute_safe` (or `tribute_ok`'s caller for a winning or `> tribute_window` channel only), also return
false when a visible enemy with a stun ability (AbilityKind with stun, or Marcella's reset-stun; check champions.h
facts) whose stun slot is ready, or ready within the window, can bring us within its cast range (ability range 4)
within min(turns, tribute_window) rounds: its walking distance or Chebyshev distance minus 4, counting dash range if
its dash is ready. Use existing Safety/World helpers for enemy reach if there are any (e.g. Strike reach). Do not
change short (non-winning, <= window) tributes. Debug trace: tributes refused for a stun threat.
Done: builds, 2 smoke games finish without errors. Report in 5 lines.
