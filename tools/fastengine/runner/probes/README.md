# fastrunner probes

Bots that check fastrunner against stock cambc where ordinary games don't reach. Play each against any bot (or
itself) with `cambc run-batch` and with `fastrunner run-batch` in both modes, and compare every bundle member but
`.debug`: all matched on 2026-11-01.

- `wasi`: every stdio, clock, random and path call's result, on the first play turn.
- `wasi-fuel`: the fuel each of those calls costs.
- `fprobe`: float min/max and arithmetic on NaN, zero, infinity and denormal operands, scalar and SIMD; out-of-bounds
  traps from huge constant offsets and from loads whose value is dropped. Release builds too.
- `leprobe`: the engine's last error message where a bot can read it without a call setting it (instance start, after
  yields, restarts, WASI writes, a debug_block overrun), in draft and play. Run it 60 rounds.
