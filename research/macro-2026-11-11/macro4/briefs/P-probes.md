# Brief P: three diagnostic probe variants (small, exact changes)

You are an implementation subagent for the macro4 lead. Work ONLY in /home/ubuntu/wt/macro4 (git worktree, branch
macro4-20261111). Never touch other checkouts under /home/ubuntu/wt/ or /home/ubuntu/cambc-autumn, never edit
bots/variants/ocean-ref-b7c87cf or bots/ocean, never write to any Claude memory directory, never run ab.py / fgate /
A/B tests, commit nothing. Read /home/ubuntu/wt/macro4/AGENTS.md first. Another subagent is building
bots/variants/macro4-pact at the same time: do not touch it.

These are direction-finding probes for the lead, each a minimal, exact change on a fresh copy of ocean. Make each with
`cd /home/ubuntu/wt/macro4 && ./copybot ocean variants/<name>` and change only what is listed:

1. **variants/macro4-p-roster**: count farther allies in fights, without any commitment protocol.
   In bots/variants/macro4-p-roster/src/model/safety.h set `safety_params::fight_ally_radius` 4 -> 7 (equal to
   chasing_ally_radius), and in params.h `pack_ally_radius` 6 -> 9. Check every other use of these constants still
   makes sense (e.g. static tables sized by them, SIMD masks) and fix any size assumption.
2. **variants/macro4-p-prismbank**: Prism stops keeping its bag for Focus. In economy/bank.cc make
   `retaining_gems()` return false (so Prism banks like any other champion). Grep for other Prism-hoard special
   cases that depend on Passive::gem_focus for banking/tribute decisions (e.g. a Prism bag cap, recall lines by gems,
   capture routing to Prism) and list them in your report, but change only retaining_gems.
3. **variants/macro4-p-stick**: steadier farm targets. In economy/farm.cc `stickiness` 1.2f -> 2.0f.

Done when: each variant builds (`cambc build bots/variants/<name>` and with `--release`; check tools/README.md for the
exact build invocation) and one local game of each runs without errors (`cambc run ...` against
bots/variants/ocean-ref-b7c87cf; see `cambc run --help`). No auditor needed for these one-line probes, but do
re-read your diffs (`diff -ru bots/ocean/src bots/variants/<name>/src`). Report the three diffs (one line each) and
the list asked for in probe 2. Stop there.
