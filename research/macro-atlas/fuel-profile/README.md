# Fuel profile of ATLAS's remaining parts (2026-11-11)

Scripts behind EXPERIMENTS.md "The rest of ATLAS (fixes 3, 5, the press) at the real budget".

- `prof_instr.py SRC`: adds per-turn fuel scopes to a debug copy of charybdis 517 (+ `../patches/remaining-after-517.diff`):
  `lethal`, `stunner_near`, `stun_follow_up`, `coming_casts`, `retreat_step`, `press` (computed, not memo hits),
  `press_taken`, `press_avoid`, `step_guard`, `decide`. Prints `PROF` lines for OOF turns and turns with decide >= 50k,
  and cumulative `PCUM` lines. Hooks that do not match (517 lacks the new functions) are skipped and listed.
  Key 13 (the press's fight sim) was added by hand: a `PROF_SCOPE(13);` at the top of press()'s `if (dealt < hp || linked)` block,
  and main.cc's two `k < 12` loops raised to 16.
- Play: `CAMBC_BIN=... FASTRUNNER_MODE=native py tools/fuel/bench.py run variants/COPY --opp charybdis --fuel 0 --maps ... --games DIR`.
- `prof_parse.py DIR...`: fuel and calls a game per key, their means on heavy and OOF turns.
- `dist.py DIR`: press/sim/lethal fuel percentiles on heavy and OOF turns, sims per turn.
- `oofphase.py DIR...`: OOF turns by phase and SHORTCUT counts a game.

Debug builds replay every trade() in full, so sim costs read high against release.
