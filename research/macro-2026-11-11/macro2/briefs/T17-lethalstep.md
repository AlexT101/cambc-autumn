# T17: when every step is lethal, step where the enemy must commit most (candidate `bots/variants/macro2-lstep`)

Read /home/ubuntu/wt/macro2/research/macro-2026-11-11/briefs/common.md first and follow it. Base: copy
`variants/macro2-combo` (`./copybot variants/macro2-combo variants/macro2-lstep`). Never edit macro2-combo or bots/ocean.

## Evidence
In the mut-yin-yang game (map `mut-yin-yang-20000117018` in /home/ubuntu/wt/macro2-maps/s-200001):
- A's Prism (228 gems) was on branch R at r262, already on a lethal tile at (20,10).
- `retreat()` (combat/fight.cc) stepped it to (19,11), from 4 to 3 tiles of B's Prism, although tiles at distance 5,
  (19,9) and (20,9), were open.
- B's Prism then killed it. Reproduce with ref in both seats or combo as A vs ref as B, at `--fuel 200000`, debug
  build. The T14 implementer reran it with macro2-exits (combo-based) as A, and A's Prism still died at r264.

## Principle
When the worst-case model rates every reachable tile lethal (for example, against an enemy with two turns before
ours: walk then cast), the tiles still differ in what the enemy must do to kill us. Where it can strike without
walking, the kill is certain. Where it must walk first, it must commit, and it often doesn't (mirror data: a
double-turn enemy commits about 10% of the time). Farther away is also closer to our support and our spawn. So among
tiles equally lethal under the worst case, prefer one outside every visible enemy's no-walk strike reach, then the
one farthest from the threats.

## What to build (bounded)
1. Reproduce r262, and find how `retreat()` ranks steps when every option is lethal or hit. What decided (19,11)?
   Report it.
2. If the ranking falls back to home direction, path cost or similar when all options are lethal, add the tie-break
   above. It runs only in that case. It uses the existing `Safety` strike data for no-walk reach (the enemy's
   standing reach, as in `compute_strike` or `StrikeMemo::standing`), then Chebyshev distance to the nearest
   threatening enemy.
3. If something else decided the step, report it and make the smallest rule-grounded fix only if it is clear.
   Otherwise stop: that is a valid result.
4. No new tuned constants. Leave everything else alone.

## Check
Trace `LSTEP round handle old_tile new_tile`. Rerun the yin-yang game and report whether the Prism survives r263-264.
Play 2 more games. Audit and report as common.md says. Scope: about 40 minutes of work.
